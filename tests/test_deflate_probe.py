#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
import zlib

from chunklate import deflate_probe


@dataclass(frozen=True)
class _Window:
    start: int
    end: int


def _compress_fixed(data: bytes) -> bytes:
    compressor = zlib.compressobj(level=6, strategy=zlib.Z_FIXED)
    return compressor.compress(data) + compressor.flush()


def test_analyze_deflate_stream_traces_stored_blocks():
    raw = bytes(range(64)) * 4
    stream = zlib.compress(raw, level=0)

    trace = deflate_probe.analyze_deflate_stream(stream, checkpoint_stride=32)

    assert trace.status == "complete"
    assert trace.decompressed_size == len(raw)
    assert any(checkpoint.reason == "stored-data" for checkpoint in trace.checkpoints)
    assert deflate_probe.output_offset_before_byte(trace, len(stream)) == len(raw)


def test_analyze_deflate_stream_traces_fixed_huffman_blocks():
    raw = (b"fixed-huffman-" * 80) + bytes(range(32))
    stream = _compress_fixed(raw)

    trace = deflate_probe.analyze_deflate_stream(stream, checkpoint_stride=16)

    assert trace.status == "complete"
    assert trace.decompressed_size == len(raw)
    assert any(checkpoint.block_type == 1 for checkpoint in trace.checkpoints)
    assert any(state.block_type == 1 for state in trace.huffman_states)


def test_analyze_deflate_stream_traces_dynamic_huffman_blocks():
    raw = (b"The quick brown fox jumps over the lazy dog. " * 500) + bytes(range(128))
    stream = zlib.compress(raw, level=9)

    trace = deflate_probe.analyze_deflate_stream(stream, checkpoint_stride=32)

    assert trace.status == "complete"
    assert trace.decompressed_size == len(raw)
    assert any(checkpoint.reason == "dynamic-header" for checkpoint in trace.checkpoints)
    assert any(state.block_type == 2 for state in trace.huffman_states)


def test_huffman_state_before_byte_returns_nearest_state():
    raw = (b"state-before-byte-" * 300) + bytes(range(128))
    stream = zlib.compress(raw, level=9)
    trace = deflate_probe.analyze_deflate_stream(stream, checkpoint_stride=32)

    state = deflate_probe.huffman_state_before_byte(trace, len(stream) // 2)

    assert state is not None
    assert state.byte_offset <= len(stream) // 2
    assert state.literal_table
    assert state.distance_table


def test_iter_huffman_prefix_candidates_is_bounded_and_byte_sized():
    raw = (b"prefix-candidates-" * 200) + bytes(range(128))
    stream = zlib.compress(raw, level=9)
    trace = deflate_probe.analyze_deflate_stream(stream, checkpoint_stride=32)
    state = deflate_probe.huffman_state_before_byte(trace, len(stream) // 2)
    assert state is not None

    candidates = deflate_probe.iter_huffman_prefix_candidates(
        stream,
        state,
        3,
        max_candidates=12,
    )

    assert 0 < len(candidates) <= 12
    assert all(len(candidate.prefix) == 3 for candidate in candidates)
    assert len({candidate.prefix for candidate in candidates}) == len(candidates)


def test_huffman_state_before_byte_boundary_returns_nearby_symbol_state():
    raw = (b"boundary-state-" * 400) + bytes(range(128))
    stream = zlib.compress(raw, level=9)
    trace = deflate_probe.analyze_deflate_stream(stream, checkpoint_stride=32)
    byte_offset = len(stream) // 2

    state = deflate_probe.huffman_state_before_byte_boundary(
        stream,
        byte_offset,
        trace=trace,
    )

    assert state is not None
    assert state.bit_offset <= byte_offset * 8
    assert byte_offset * 8 - state.bit_offset <= 64
    assert state.literal_table
    assert state.distance_table


def test_iter_huffman_byte_prefix_candidates_uses_known_prefix_bits():
    raw = (b"byte-prefix-candidates-" * 400) + bytes(range(128))
    stream = zlib.compress(raw, level=9)
    trace = deflate_probe.analyze_deflate_stream(stream, checkpoint_stride=32)
    byte_offset = len(stream) // 2
    state = deflate_probe.huffman_state_before_byte_boundary(
        stream,
        byte_offset,
        trace=trace,
    )
    assert state is not None

    candidates = deflate_probe.iter_huffman_byte_prefix_candidates(
        stream,
        state,
        byte_offset,
        2,
        max_candidates=16,
    )

    assert 0 < len(candidates) <= 16
    assert all(len(candidate.prefix) == 2 for candidate in candidates)
    fixed_bit_count = byte_offset * 8 - state.bit_offset
    assert fixed_bit_count <= 64


def test_analyze_deflate_stream_reports_corrupt_deflate():
    raw = b"corrupt-me" * 100
    stream = bytearray(zlib.compress(raw, level=9))
    stream[len(stream) // 2] ^= 0xFF

    trace = deflate_probe.analyze_deflate_stream(bytes(stream), checkpoint_stride=16)

    assert trace.status != "complete"
    assert trace.error_byte_offset is not None
    assert trace.reason


def test_score_windows_by_output_offset_orders_nearest_window_first():
    raw = bytes(range(251)) * 20
    stream = zlib.compress(raw, level=0)
    trace = deflate_probe.analyze_deflate_stream(stream, checkpoint_stride=16)
    windows = (_Window(10, 20), _Window(80, 90), _Window(160, 170))

    scores = deflate_probe.score_windows_by_output_offset(trace, windows, 80)

    assert scores[0].window == windows[1]
    assert [score.window for score in scores] == [windows[1], windows[2], windows[0]]


def test_validate_local_edit_accepts_correct_insert_prefix():
    raw = (b"local-edit-" * 200) + bytes(range(64))
    payload = zlib.compress(raw, level=9)
    offset = 12
    missing = payload[offset : offset + 5]
    broken = payload[:offset] + payload[offset + 5 :]

    result = deflate_probe.validate_local_edit(
        broken,
        offset,
        "insert",
        5,
        missing,
        stop_after_output=len(raw) // 2,
        checkpoint_stride=16,
    )

    assert result.accepted is True
    assert result.trace.status in {"prefix_ok", "complete"}


def test_validate_local_edit_rejects_wrong_insert_prefix():
    raw = (b"local-edit-" * 200) + bytes(range(64))
    payload = zlib.compress(raw, level=9)
    offset = 12
    broken = payload[:offset] + payload[offset + 5 :]

    result = deflate_probe.validate_local_edit(
        broken,
        offset,
        "insert",
        5,
        b"\xff" * 5,
        stop_after_output=len(raw) // 2,
        checkpoint_stride=16,
    )

    assert result.accepted is False


def main():
    test_analyze_deflate_stream_traces_stored_blocks()
    test_analyze_deflate_stream_traces_fixed_huffman_blocks()
    test_analyze_deflate_stream_traces_dynamic_huffman_blocks()
    test_huffman_state_before_byte_returns_nearest_state()
    test_iter_huffman_prefix_candidates_is_bounded_and_byte_sized()
    test_huffman_state_before_byte_boundary_returns_nearby_symbol_state()
    test_iter_huffman_byte_prefix_candidates_uses_known_prefix_bits()
    test_analyze_deflate_stream_reports_corrupt_deflate()
    test_score_windows_by_output_offset_orders_nearest_window_first()
    test_validate_local_edit_accepts_correct_insert_prefix()
    test_validate_local_edit_rejects_wrong_insert_prefix()


if __name__ == "__main__":
    main()
