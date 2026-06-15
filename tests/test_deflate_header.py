#!/usr/bin/env python3
import sys
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import deflate_header


def dynamic_payload():
    return (b"hello world this is a long text with many words and punctuation " * 100)


def dynamic_stream():
    compressed = zlib.compress(dynamic_payload(), 1)
    analysis = deflate_header.analyze_deflate_header(compressed)
    assert analysis.status == "ok"
    assert analysis.btype == 2
    return compressed


def natural_order_base_stream():
    filtered = b"".join(
        b"\x00" + bytes(((row * 3) % 256, (row * 7) % 256, (row * 11) % 256))
        for row in range(100)
    )
    compressed = zlib.compress(filtered, 1)
    analysis = deflate_header.analyze_deflate_header(compressed)
    assert analysis.status == "ok"
    assert analysis.btype == 2
    return compressed


def replace_bits_preserve_length(stream, bit_start, bit_end, bits):
    value = int.from_bytes(stream, "little")
    replacement = 0
    for index, bit in enumerate(bits):
        replacement |= (int(bit) & 1) << index
    low = value & ((1 << bit_start) - 1)
    high = value >> bit_end
    shifted = low | (replacement << bit_start) | (high << (bit_start + len(bits)))
    mask = (1 << (len(stream) * 8)) - 1
    return (shifted & mask).to_bytes(len(stream), "little")


def bits_for(value, width):
    return tuple((int(value) >> index) & 1 for index in range(width))


def stream_bits_value(stream, bit_start, bit_end):
    value = 0
    for index, bit_offset in enumerate(range(bit_start, bit_end)):
        value |= ((stream[bit_offset // 8] >> (bit_offset % 8)) & 1) << index
    return value


def natural_code_length_order_stream():
    compressed = natural_order_base_stream()
    trace = deflate_header.trace_dynamic_header(compressed)
    assert trace.status == "ok"
    values_by_symbol = {symbol: value for symbol, value in enumerate(trace.code_length_lengths)}
    corrupted = compressed
    for index, (_standard_symbol, bit_start, bit_end) in enumerate(trace.code_length_bits):
        natural_symbol = index
        new_value = values_by_symbol.get(natural_symbol, 0)
        old_value = stream_bits_value(corrupted, bit_start, bit_end)
        if new_value != old_value:
            corrupted = replace_bits_preserve_length(
                corrupted,
                bit_start,
                bit_end,
                bits_for(new_value, bit_end - bit_start),
            )
    return corrupted


def test_analyze_deflate_header_reports_dynamic_header():
    analysis = deflate_header.analyze_deflate_header(dynamic_stream())

    assert analysis.status == "ok"
    assert analysis.btype == 2
    assert analysis.hlit is not None
    assert analysis.hdist is not None
    assert analysis.hclen is not None
    assert analysis.header_end_bit is not None
    assert "dynamic Huffman header" in analysis.summary


def test_trace_dynamic_header_reports_valid_tokens_and_lengths():
    trace = deflate_header.trace_dynamic_header(dynamic_stream())

    assert trace.status == "ok"
    assert trace.btype == 2
    assert trace.hlit is not None
    assert trace.hdist is not None
    assert trace.hclen is not None
    assert len(trace.literal_lengths) == trace.hlit
    assert len(trace.distance_lengths) == trace.hdist
    assert trace.tokens
    assert trace.header_end_bit is not None
    assert "tokens=" in trace.summary


def test_trace_dynamic_header_can_use_natural_code_length_order():
    stream = natural_code_length_order_stream()
    standard_trace = deflate_header.trace_dynamic_header(stream)
    natural_trace = deflate_header.trace_dynamic_header(
        stream,
        code_length_order=tuple(range(19)),
    )

    assert standard_trace.status != "ok"
    assert natural_trace.status == "ok"
    assert natural_trace.btype == 2
    assert natural_trace.header_end_bit is not None


def test_analyze_deflate_header_reports_bad_code_length_tree():
    compressed = bytearray(dynamic_stream())
    compressed[3] ^= 1 << 5

    analysis = deflate_header.analyze_deflate_header(bytes(compressed))

    assert analysis.status == "bad_code_length_tree"
    assert analysis.byte_offset >= 2
    assert analysis.context_hex
    assert "oversubscribed Huffman tree" in analysis.reason


def test_trace_dynamic_header_keeps_invalid_length_tokens():
    compressed = bytearray(dynamic_stream())
    compressed[2] ^= 1 << 3

    trace = deflate_header.trace_dynamic_header(bytes(compressed))

    assert trace.status == "invalid_huffman_lengths"
    assert trace.hlit is not None
    assert trace.hdist is not None
    assert trace.hclen is not None
    assert trace.tokens
    assert len(trace.literal_lengths) == trace.hlit
    assert len(trace.distance_lengths) == trace.hdist
    assert trace.literal_error or trace.distance_error


def test_trace_dynamic_header_reports_unrepairable_truncated_or_code_length_tree():
    truncated = deflate_header.trace_dynamic_header(dynamic_stream()[:4])
    assert truncated.status == "truncated_header"
    assert truncated.reason

    compressed = bytearray(dynamic_stream())
    compressed[3] ^= 1 << 5
    bad_tree = deflate_header.trace_dynamic_header(bytes(compressed))
    assert bad_tree.status == "bad_code_length_tree"
    assert bad_tree.tokens == ()
    assert bad_tree.reason


def test_analyze_deflate_header_reports_invalid_huffman_lengths():
    compressed = bytearray(dynamic_stream())
    compressed[2] ^= 1 << 3

    analysis = deflate_header.analyze_deflate_header(bytes(compressed))

    assert analysis.status == "invalid_huffman_lengths"
    assert "tree" in analysis.reason


def test_analyze_deflate_header_reports_truncated_header():
    analysis = deflate_header.analyze_deflate_header(dynamic_stream()[:4])

    assert analysis.status == "truncated_header"
    assert analysis.context_hex


def test_analyze_deflate_header_accepts_fixed_or_stored_headers():
    fixed = deflate_header.analyze_deflate_header(zlib.compress(b"abc"))
    stored = deflate_header.analyze_deflate_header(zlib.compress(b"abc", 0))

    assert fixed.status == "ok"
    assert fixed.btype == 1
    assert stored.status == "ok"
    assert stored.btype == 0


def test_analyze_deflate_header_reports_bad_zlib_header():
    analysis = deflate_header.analyze_deflate_header(b"\x00\x00abc")

    assert analysis.status == "bad_zlib_header"
    assert analysis.reason == "bad zlib header"


def main():
    checks = [
        ("dynamic header", test_analyze_deflate_header_reports_dynamic_header),
        ("dynamic trace", test_trace_dynamic_header_reports_valid_tokens_and_lengths),
        ("natural code length order trace", test_trace_dynamic_header_can_use_natural_code_length_order),
        ("bad code length tree", test_analyze_deflate_header_reports_bad_code_length_tree),
        ("invalid dynamic trace", test_trace_dynamic_header_keeps_invalid_length_tokens),
        (
            "unrepairable dynamic trace",
            test_trace_dynamic_header_reports_unrepairable_truncated_or_code_length_tree,
        ),
        ("invalid Huffman lengths", test_analyze_deflate_header_reports_invalid_huffman_lengths),
        ("truncated header", test_analyze_deflate_header_reports_truncated_header),
        ("fixed/stored headers", test_analyze_deflate_header_accepts_fixed_or_stored_headers),
        ("bad zlib header", test_analyze_deflate_header_reports_bad_zlib_header),
    ]

    print("Running deflate header tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"Deflate header tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
