#!/usr/bin/env python3
import sys
import struct
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import idat
from chunklate import idat_bruteforce
from chunklate.png import (
    IEND_CHUNK,
    PNG_SIGNATURE,
    build_png_chunk,
    iter_chunks,
    repair_linefeed_conversion,
    repair_overlong_chunk_length_to_next_header,
    validate_png_structure,
)


def build_rgb_png(width, height, filtered_scanlines, *, idat_data=None, idat_parts=None, interlace=0):
    ihdr = struct.pack("!IIBBBBB", width, height, 8, 2, 0, 0, interlace)
    if idat_data is None:
        idat_data = zlib.compress(filtered_scanlines)
    if idat_parts is None:
        idat_parts = (idat_data,)
    return (
        PNG_SIGNATURE
        + build_png_chunk(b"IHDR", ihdr)
        + b"".join(build_png_chunk(b"IDAT", part) for part in idat_parts)
        + IEND_CHUNK
    )


def dynamic_filtered_rows(height=100):
    return b"".join(
        b"\x00" + bytes(((row * 3) % 256, (row * 7) % 256, (row * 11) % 256))
        for row in range(height)
    )


def dynamic_header_corrupt_png():
    filtered = dynamic_filtered_rows()
    compressed = bytearray(zlib.compress(filtered, 1))
    original = compressed[3]
    compressed[3] ^= 1 << 5
    return build_rgb_png(1, 100, filtered, idat_data=bytes(compressed)), 3, original


def split_bytes(data, *sizes):
    parts = []
    offset = 0
    for size in sizes:
        parts.append(data[offset:offset + size])
        offset += size
    parts.append(data[offset:])
    return tuple(parts)


def find_truncated_candidate(filtered, predicate, *, width=1, height=10):
    compressed = zlib.compress(filtered, level=0)
    for cut in range(2, len(compressed)):
        candidate = build_rgb_png(width, height, filtered, idat_data=compressed[:cut])
        analysis = idat.analyze_partial_idat(candidate)
        if predicate(analysis):
            return candidate, analysis
    raise AssertionError("could not build truncated IDAT candidate")


def test_dummy_scanline_preserves_legacy_sample_width():
    assert idat.dummy_scanline("8") == (
        b"\x01",
        b"\x00",
        b"\x00\x01\x01\x01",
    )
    assert idat.dummy_scanline("16") == (
        b"\x01\x00",
        b"\x00",
        b"\x00\x01\x00\x01\x00\x01\x00",
    )


def test_idat_zlib_header_skips_interlaced_streams_like_legacy_todo():
    assert idat.idat_zlib_header("789cabcd", "0") == "789c"
    assert idat.idat_zlib_header("789cabcd", "1") == ""


def test_zlib_header_info_reads_window_and_legacy_compression_level():
    best = idat.zlib_header_info("78da")
    default = idat.zlib_header_info("789c")
    invalid = idat.zlib_header_info("bad")

    assert best.valid is True
    assert best.cinfo == 7
    assert best.window_kb == 32
    assert best.flevel == 3
    assert best.compression_level == 9
    assert default.valid is True
    assert default.window_kb == 32
    assert default.compression_level == -1
    assert invalid.valid is False


def test_build_dummy_idat_probe_decompresses_debug_stream_and_idat_stream():
    stream_payload = b"\x00abc"
    probe = idat.build_dummy_idat_probe(
        zlib.compress(stream_payload).hex(),
        bit_depth="8",
        interlace="0",
    )

    assert probe.header == "789c"
    assert probe.scanline == b"\x00\x01\x01\x01"
    assert probe.decompressed == probe.scanline
    assert probe.idat_decompressed == stream_payload
    assert probe.idat_decompressed_error == ""


def test_build_dummy_idat_probe_reports_invalid_stream_without_raising():
    probe = idat.build_dummy_idat_probe("not-hex", bit_depth="8", interlace="0")

    assert probe.header == "not-"
    assert probe.decompressed == probe.scanline
    assert probe.idat_decompressed == b""
    assert probe.idat_decompressed_error != ""


def test_analyze_partial_idat_reports_complete_non_interlaced_stream():
    filtered = b"\x00abc" + b"\x00def"
    analysis = idat.analyze_partial_idat(build_rgb_png(1, 2, filtered))

    assert analysis.supported is True
    assert analysis.complete is True
    assert analysis.partial is False
    assert analysis.width == 1
    assert analysis.height == 2
    assert analysis.scanline_size == 4
    assert analysis.complete_scanlines == 2
    assert analysis.usable_scanlines == 2
    assert analysis.recovered_scanlines == filtered
    assert analysis.decompression_error == ""


def test_analyze_partial_idat_concatenates_complete_multi_idat_stream():
    filtered = b"\x00abc" + b"\x00def" + b"\x00ghi"
    compressed = zlib.compress(filtered)
    candidate = build_rgb_png(
        1,
        3,
        filtered,
        idat_data=compressed,
        idat_parts=split_bytes(compressed, 2, 4),
    )

    analysis = idat.analyze_partial_idat(candidate)

    assert analysis.supported is True
    assert analysis.complete is True
    assert analysis.partial is False
    assert analysis.usable_scanlines == 3
    assert analysis.recovered_scanlines == filtered
    assert analysis.idat_stream_size == len(compressed)


def test_analyze_partial_idat_keeps_good_scanlines_until_truncated_stream_error():
    filtered = b"".join(b"\x00" + bytes((row, row, row)) for row in range(10))
    _candidate, truncated = find_truncated_candidate(
        filtered,
        lambda analysis: analysis.usable_scanlines > 0 and analysis.decompression_error,
    )

    assert truncated.supported is True
    assert truncated.complete is False
    assert truncated.partial is True
    assert truncated.usable_scanlines >= 1
    assert truncated.recovered_scanlines.startswith(filtered[:4])
    assert truncated.decompression_error == "incomplete zlib stream"


def test_analyze_partial_idat_recovers_truncated_multi_idat_stream():
    filtered = b"".join(b"\x00" + bytes((row, row, row)) for row in range(10))
    compressed = zlib.compress(filtered, level=0)
    split = max(3, len(compressed) // 3)
    truncated_stream = compressed[:-3]
    candidate = build_rgb_png(
        1,
        10,
        filtered,
        idat_data=truncated_stream,
        idat_parts=split_bytes(truncated_stream, split, split),
    )

    analysis = idat.analyze_partial_idat(candidate)
    repair = idat.rebuild_partial_idat_blackfill(candidate)

    assert analysis.supported is True
    assert analysis.complete is False
    assert analysis.partial is True
    assert analysis.usable_scanlines > 0
    assert analysis.recovered_scanlines.startswith(filtered[:4])
    assert analysis.decompression_error == "incomplete zlib stream"
    assert repair is not None
    assert validate_png_structure(repair.data).ok


def test_analyze_partial_idat_reports_bad_adler_with_recovered_scanlines():
    filtered = b"".join(b"\x00" + bytes((row, row, row)) for row in range(3))
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF

    analysis = idat.analyze_partial_idat(build_rgb_png(1, 3, filtered, idat_data=bytes(compressed)))

    assert analysis.supported is True
    assert analysis.complete is False
    assert analysis.partial is True
    assert analysis.usable_scanlines == 3
    assert analysis.recovered_scanlines == filtered
    assert analysis.decompression_error


def test_analyze_partial_idat_rejects_broken_zlib_header_without_scanlines():
    filtered = b"\x00abc"
    compressed = bytearray(zlib.compress(filtered))
    compressed[0] = 0
    compressed[1] = 0

    analysis = idat.analyze_partial_idat(build_rgb_png(1, 1, filtered, idat_data=bytes(compressed)))

    assert analysis.supported is True
    assert analysis.complete is False
    assert analysis.partial is False
    assert analysis.usable_scanlines == 0
    assert analysis.recovered_scanlines == b""
    assert analysis.decompression_error
    assert idat.rebuild_partial_idat_blackfill(build_rgb_png(1, 1, filtered, idat_data=bytes(compressed))) is None


def test_analyze_partial_idat_discards_partial_scanline_tail():
    scanline_size = 7
    filtered = b"".join(
        b"\x00" + bytes((row, row, row, row, row, row))
        for row in range(4)
    )
    _candidate, analysis = find_truncated_candidate(
        filtered,
        lambda analysis: (
            analysis.usable_scanlines >= 1
            and analysis.decompression_error
            and analysis.decompressed_size % scanline_size != 0
        ),
        width=2,
        height=4,
    )

    assert analysis.complete is False
    assert analysis.partial is True
    assert analysis.complete_scanlines == analysis.usable_scanlines
    assert len(analysis.recovered_scanlines) == analysis.usable_scanlines * scanline_size
    assert analysis.recovered_scanlines == filtered[:len(analysis.recovered_scanlines)]


def test_analyze_partial_idat_rejects_unsupported_interlace_before_repair_logic():
    filtered = b"\x00abc"
    candidate = build_rgb_png(1, 1, filtered, interlace=1)
    analysis = idat.analyze_partial_idat(candidate)

    assert analysis.supported is False
    assert analysis.complete is False
    assert analysis.reason == "interlaced PNG is not supported"
    assert idat.rebuild_partial_idat_blackfill(candidate) is None


def test_analyze_partial_idat_reports_invalid_stream_without_scanlines():
    analysis = idat.analyze_partial_idat(build_rgb_png(1, 1, b"\x00abc", idat_data=b"bad"))

    assert analysis.supported is True
    assert analysis.complete is False
    assert analysis.partial is False
    assert analysis.usable_scanlines == 0
    assert analysis.recovered_scanlines == b""
    assert analysis.decompression_error != ""


def test_rebuild_partial_idat_blackfill_keeps_prefix_and_fills_remaining_rows():
    filtered = b"".join(b"\x00" + bytes((row, row, row)) for row in range(10))
    compressed = zlib.compress(filtered)
    repair = None
    for cut in range(2, len(compressed)):
        candidate = build_rgb_png(1, 10, filtered, idat_data=compressed[:cut])
        repair = idat.rebuild_partial_idat_blackfill(candidate)
        if repair is not None:
            break

    assert repair is not None
    assert "partial-idat-blackfill" in repair.strategy
    assert repair.recovered_scanlines >= 1
    assert repair.total_scanlines == 10
    assert validate_png_structure(repair.data).ok

    chunks = list(iter_chunks(repair.data))
    rebuilt_stream = b"".join(chunk.data for chunk in chunks if chunk.chunk_type == b"IDAT")
    rebuilt_filtered = zlib.decompress(rebuilt_stream)
    recovered_size = repair.recovered_scanlines * 4

    assert rebuilt_filtered[:recovered_size] == filtered[:recovered_size]
    assert rebuilt_filtered[recovered_size:] == b"\x00\x00\x00\x00" * (
        10 - repair.recovered_scanlines
    )


def test_rebuild_partial_idat_blackfill_handles_valid_empty_stream():
    empty_stream_png = build_rgb_png(1, 2, b"\x00abc\x00def", idat_data=zlib.compress(b""))

    repair = idat.rebuild_partial_idat_blackfill(empty_stream_png)

    assert repair is not None
    assert repair.strategy == "partial-idat-blackfill recovered 0/2 scanlines"
    assert repair.recovered_scanlines == 0
    assert repair.total_scanlines == 2
    assert validate_png_structure(repair.data).ok

    chunks = list(iter_chunks(repair.data))
    rebuilt_stream = b"".join(chunk.data for chunk in chunks if chunk.chunk_type == b"IDAT")
    assert zlib.decompress(rebuilt_stream) == b"\x00\x00\x00\x00" * 2


def test_rebuild_tolerant_idat_salvage_keeps_rows_after_bad_filters():
    linefeed = repair_linefeed_conversion(
        (ROOT / "David" / "6.bad.png").read_bytes(),
        allow_partial=True,
    )
    assert linefeed is not None
    realigned = repair_overlong_chunk_length_to_next_header(linefeed.data)
    assert realigned is not None

    blackfill = idat.rebuild_partial_idat_blackfill(realigned.data)
    repair = idat.rebuild_tolerant_idat_salvage(realigned.data)

    assert blackfill is not None
    assert blackfill.recovered_scanlines == 145
    assert repair is not None
    assert repair.recovered_scanlines == 495
    assert repair.total_scanlines == 503
    assert "reused previous row for 8 bad filter rows" in repair.strategy
    assert validate_png_structure(repair.data).ok

    chunks = list(iter_chunks(repair.data))
    rebuilt_stream = b"".join(chunk.data for chunk in chunks if chunk.chunk_type == b"IDAT")
    rebuilt_filtered = zlib.decompress(rebuilt_stream)

    assert len(rebuilt_filtered) == 503 * 2401
    assert {rebuilt_filtered[row * 2401] for row in range(503)} == {0}
    assert rebuilt_filtered[145 * 2401 : 146 * 2401] == rebuilt_filtered[144 * 2401 : 145 * 2401]


def test_idat_linefeed_cr_insert_probe_improves_salvage_candidate():
    linefeed = repair_linefeed_conversion(
        (ROOT / "David" / "6.bad.png").read_bytes(),
        allow_partial=True,
    )
    assert linefeed is not None
    realigned = repair_overlong_chunk_length_to_next_header(linefeed.data)
    assert realigned is not None
    first_error_offset = idat_bruteforce.first_idat_problem_stream_offset(realigned.data)
    assert first_error_offset == 0x3EE9

    result = idat_bruteforce.probe_idat_linefeed_cr_insertions(
        realigned.data,
        window_radius=4096,
    )

    assert result.best is not None
    assert result.strategy == "linefeed-cr-insert"
    assert result.before.usable_scanlines == 145
    assert result.best.after.usable_scanlines == 503

    repair = idat.rebuild_partial_idat_blackfill(result.best.data)
    assert repair is not None
    assert repair.recovered_scanlines == 503
    assert repair.total_scanlines == 503
    assert validate_png_structure(repair.data).ok

    full = idat_bruteforce.probe_idat_linefeed_cr_insertions_full(
        result.best.data,
        start_offset=first_error_offset,
    )
    assert full.strategy == "linefeed-cr-insert-full"
    assert full.window_start == first_error_offset
    assert full.tested_candidates > 0

    super_probe = idat_bruteforce.probe_super_mega_linefeed_force_of_death(
        result.best.data,
        start_offset=first_error_offset,
        linefeed_budget=100,
        structural_budget=100,
        local_bit_budget=32,
        local_byte_budget=64,
        heavy_byte_budget=64,
        beam_width=2,
        max_depth=1,
    )
    assert super_probe.strategy == "SuperMegaLineFeedForceOfDeath"
    assert super_probe.error_anchor_offset == first_error_offset
    assert super_probe.pre_error_backtrack == idat_bruteforce.adaptive_pre_error_backtrack(super_probe.window_end)
    assert super_probe.search_start_offset == max(0, first_error_offset - super_probe.pre_error_backtrack)
    assert super_probe.tested_candidates > full.tested_candidates
    assert super_probe.target_adler is not None
    assert super_probe.state_count >= 1
    assert super_probe.visited_count >= super_probe.state_count
    assert {phase.name for phase in super_probe.phases} >= {
        "phase1-linefeed-global",
        "phase2-crlf-structural",
        "phase3-deflate-bit",
        "phase3-deflate-byte",
        "phase4-heavy-byte-window",
        "phase5-adler-target",
    }
    summary = idat_bruteforce.super_mega_linefeed_probe_summary_line(super_probe)
    assert "SuperMegaLineFeedForceOfDeath" in summary
    assert "target_adler=0x" in summary
    assert "source_crc=" in summary


def test_super_mega_linefeed_force_recovers_multiple_crlf_deletions():
    filtered = b"".join(b"\x00" + bytes((13, 10, row)) for row in range(20))
    compressed = bytearray(zlib.compress(filtered, level=0))
    crlf_offsets = [
        offset
        for offset in range(2, len(compressed) - 1)
        if compressed[offset] == 0x0D and compressed[offset + 1] == 0x0A
    ]
    assert len(crlf_offsets) >= 2
    for offset in reversed(crlf_offsets[:2]):
        del compressed[offset]

    corrupt = build_rgb_png(1, 20, filtered, idat_data=bytes(compressed))
    start_offset = idat_bruteforce.first_idat_problem_stream_offset(corrupt)
    assert start_offset is not None

    probe = idat_bruteforce.probe_super_mega_linefeed_force_of_death(
        corrupt,
        start_offset=start_offset,
        pre_error_backtrack=64,
        linefeed_budget=100,
        structural_budget=0,
        local_bit_budget=0,
        local_byte_budget=0,
        heavy_byte_budget=0,
        beam_width=4,
        max_depth=4,
    )

    assert probe.best is not None
    assert probe.best.after.complete is True
    assert probe.best.after.adler_status == "adler_match"
    assert len(probe.best.operations) == 2
    assert [operation.kind for operation in probe.best.operations] == [
        "insert-cr-before-lf",
        "insert-cr-before-lf",
    ]
    assert probe.states[0].state_id == 0
    assert probe.best.parent_id is not None
    assert probe.best.source_offsets == tuple(operation.stream_offset for operation in probe.best.operations)
    assert probe.visited_count <= probe.tested_candidates + 1
    assert zlib.decompress(b"".join(chunk.data for chunk in iter_chunks(probe.best.data) if chunk.chunk_type == b"IDAT")) == filtered


def test_super_mega_linefeed_force_uses_known_gap_phase_before_broad_search():
    filtered = b"".join(b"\x00" + bytes((13, 10, row)) for row in range(20))
    compressed = bytearray(zlib.compress(filtered, level=0))
    crlf_offsets = [
        offset
        for offset in range(2, len(compressed) - 1)
        if compressed[offset] == 0x0D and compressed[offset + 1] == 0x0A
    ]
    assert len(crlf_offsets) >= 2
    for offset in reversed(crlf_offsets[:2]):
        del compressed[offset]

    corrupt = build_rgb_png(1, 20, filtered, idat_data=bytes(compressed))
    start_offset = idat_bruteforce.first_idat_problem_stream_offset(corrupt)

    probe = idat_bruteforce.probe_super_mega_linefeed_force_of_death(
        corrupt,
        start_offset=start_offset,
        known_gap_bytes=2,
        known_gap_window_start=0,
        known_gap_window_end=len(compressed),
        known_gap_budget=256,
        linefeed_budget=0,
        structural_budget=0,
        local_bit_budget=0,
        local_byte_budget=0,
        heavy_byte_budget=0,
        adler_budget=0,
        beam_width=1,
        max_depth=1,
    )

    assert probe.best is not None
    assert probe.best.after.complete is True
    assert probe.best.after.adler_status == "adler_match"
    assert probe.phases[0].name == "phase0-known-gap-linefeed"
    assert probe.best.operations[0].kind == "known-gap-insert-2-crs-before-lfs"


def test_super_mega_linefeed_force_reports_budget_exhausted_but_keeps_best_candidate():
    filtered = b"".join(b"\x00" + bytes((13, 10, row)) for row in range(20))
    compressed = bytearray(zlib.compress(filtered, level=0))
    crlf_offsets = [
        offset
        for offset in range(2, len(compressed) - 1)
        if compressed[offset] == 0x0D and compressed[offset + 1] == 0x0A
    ]
    for offset in reversed(crlf_offsets[:2]):
        del compressed[offset]

    corrupt = build_rgb_png(1, 20, filtered, idat_data=bytes(compressed))
    start_offset = idat_bruteforce.first_idat_problem_stream_offset(corrupt)

    probe = idat_bruteforce.probe_super_mega_linefeed_force_of_death(
        corrupt,
        start_offset=start_offset,
        pre_error_backtrack=64,
        linefeed_budget=1,
        structural_budget=0,
        local_bit_budget=0,
        local_byte_budget=0,
        heavy_byte_budget=0,
        beam_width=1,
        max_depth=4,
    )

    assert probe.budget_exhausted is True
    assert probe.best is not None
    assert probe.best.after.usable_scanlines >= probe.before.usable_scanlines


def test_super_mega_linefeed_force_keeps_best_when_original_adler_target_is_wrong():
    filtered = b"\x00abc" + b"\x00def"
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF
    corrupt = build_rgb_png(1, 2, filtered, idat_data=bytes(compressed))

    probe = idat_bruteforce.probe_super_mega_linefeed_force_of_death(
        corrupt,
        start_offset=len(compressed) - 4,
        linefeed_budget=0,
        structural_budget=0,
        local_bit_budget=0,
        local_byte_budget=0,
        heavy_byte_budget=0,
        adler_budget=4,
        beam_width=1,
        max_depth=1,
    )

    assert probe.target_adler is not None
    assert probe.best is not None
    assert probe.best.after.complete is True
    assert probe.best.after.adler_status == "adler_mismatch"
    assert probe.best.after.crc_provenance == "rebuilt_by_chunklate"
    assert "set-zlib-trailer-to-computed-adler" in idat_bruteforce.super_mega_linefeed_candidate_summary_line(probe.best)
    assert "original Adler target was not recovered" in idat_bruteforce.super_mega_linefeed_probe_summary_line(probe)


def test_ultimate_linefeed_suspect_offsets_prioritize_error_and_linefeeds():
    filtered = b"".join(b"\x00" + bytes((13, 10, row)) for row in range(20))
    compressed = bytearray(zlib.compress(filtered, level=0))
    crlf_offsets = [
        offset
        for offset in range(2, len(compressed) - 1)
        if compressed[offset] == 0x0D and compressed[offset + 1] == 0x0A
    ]
    for offset in reversed(crlf_offsets[:2]):
        del compressed[offset]

    corrupt = build_rgb_png(1, 20, filtered, idat_data=bytes(compressed))
    start_offset = idat_bruteforce.first_idat_problem_stream_offset(corrupt)
    offsets = idat_bruteforce.ultimate_linefeed_suspect_offsets(
        corrupt,
        start_offset=start_offset,
        max_offsets=8,
    )

    assert start_offset in offsets
    assert any(bytes(compressed)[offset] == 0x0A for offset in offsets if offset < len(compressed))


def test_ultimate_linefeed_bruteforce_recovers_multi_step_original_adler(tmp_path):
    filtered = b"".join(b"\x00" + bytes((13, 10, row)) for row in range(20))
    compressed = bytearray(zlib.compress(filtered, level=0))
    crlf_offsets = [
        offset
        for offset in range(2, len(compressed) - 1)
        if compressed[offset] == 0x0D and compressed[offset + 1] == 0x0A
    ]
    for offset in reversed(crlf_offsets[:2]):
        del compressed[offset]

    corrupt = build_rgb_png(1, 20, filtered, idat_data=bytes(compressed))
    start_offset = idat_bruteforce.first_idat_problem_stream_offset(corrupt)
    checkpoint = tmp_path / "_UltimateMegaSuperLineFeedBruteForce.checkpoint.jsonl"

    probe = idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce(
        corrupt,
        start_offset=start_offset,
        checkpoint_path=str(checkpoint),
        max_depth=3,
        max_offsets=64,
        budget=2000,
        beam_width=8,
    )

    assert probe.strategy == "UltimateMegaSuperLineFeedBruteForce"
    assert probe.best is not None
    assert probe.best.after.complete is True
    assert probe.best.after.adler_status == "adler_match"
    assert probe.reached_depth == 2
    assert probe.visited_count <= probe.tested_candidates + 1
    assert checkpoint.exists()
    assert "target_adler=0x" in idat_bruteforce.ultimate_linefeed_probe_summary_line(probe)
    assert "UltimateMegaSuperLineFeedBruteForce candidate" in idat_bruteforce.ultimate_linefeed_candidate_summary_line(probe.best)
    assert zlib.decompress(b"".join(chunk.data for chunk in iter_chunks(probe.best.data) if chunk.chunk_type == b"IDAT")) == filtered


def test_ultimate_linefeed_bruteforce_recovers_four_step_original_adler(tmp_path):
    filtered = b"".join(b"\x00" + bytes((13, 10, row)) for row in range(20))
    compressed = bytearray(zlib.compress(filtered, level=0))
    crlf_offsets = [
        offset
        for offset in range(2, len(compressed) - 1)
        if compressed[offset] == 0x0D and compressed[offset + 1] == 0x0A
    ]
    for offset in reversed(crlf_offsets[:4]):
        del compressed[offset]

    corrupt = build_rgb_png(1, 20, filtered, idat_data=bytes(compressed))
    start_offset = idat_bruteforce.first_idat_problem_stream_offset(corrupt)

    probe = idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce(
        corrupt,
        start_offset=start_offset,
        checkpoint_path=str(tmp_path / "_UltimateMegaSuperLineFeedBruteForce.checkpoint.jsonl"),
        max_depth=4,
        max_offsets=16,
        budget=10000,
        beam_width=4,
    )

    assert probe.best is not None
    assert probe.best.after.complete is True
    assert probe.best.after.adler_status == "adler_match"
    assert len(probe.best.operations) == 4
    assert probe.reached_depth == 4


def test_ultimate_linefeed_bruteforce_resumes_checkpoint(tmp_path):
    filtered = b"".join(b"\x00" + bytes((13, 10, row)) for row in range(20))
    compressed = bytearray(zlib.compress(filtered, level=0))
    crlf_offsets = [
        offset
        for offset in range(2, len(compressed) - 1)
        if compressed[offset] == 0x0D and compressed[offset + 1] == 0x0A
    ]
    for offset in reversed(crlf_offsets[:2]):
        del compressed[offset]

    corrupt = build_rgb_png(1, 20, filtered, idat_data=bytes(compressed))
    start_offset = idat_bruteforce.first_idat_problem_stream_offset(corrupt)
    checkpoint = tmp_path / "_UltimateMegaSuperLineFeedBruteForce.checkpoint.jsonl"

    first = idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce(
        corrupt,
        start_offset=start_offset,
        checkpoint_path=str(checkpoint),
        max_depth=1,
        max_offsets=64,
        budget=32,
        beam_width=8,
    )
    second = idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce(
        corrupt,
        start_offset=start_offset,
        checkpoint_path=str(checkpoint),
        max_depth=2,
        max_offsets=64,
        budget=2000,
        beam_width=8,
    )

    assert first.best is not None
    assert second.resumed_states > 0
    assert second.best is not None
    assert second.best.after.adler_status == "adler_match"


def test_ultimate_linefeed_bruteforce_keeps_plausible_result_without_original_adler(tmp_path):
    filtered = b"\x00abc" + b"\x00def"
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF
    corrupt = build_rgb_png(1, 2, filtered, idat_data=bytes(compressed))

    probe = idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce(
        corrupt,
        start_offset=len(compressed) - 4,
        checkpoint_path=str(tmp_path / "_UltimateMegaSuperLineFeedBruteForce.checkpoint.jsonl"),
        max_depth=1,
        max_offsets=16,
        budget=256,
        beam_width=4,
    )

    assert probe.best is not None
    assert probe.best.after.complete is True
    assert probe.best.after.adler_status == "adler_mismatch"
    assert "original Adler target was not recovered" in idat_bruteforce.ultimate_linefeed_probe_summary_line(probe)


def test_ultimate_linefeed_bruteforce_spends_budget_when_no_terminal_match(tmp_path):
    filtered = b"".join(b"\x00" + bytes((13, 10, row % 256)) for row in range(120))
    compressed = bytearray(zlib.compress(filtered, level=0))
    crlf_offsets = [
        offset
        for offset in range(2, len(compressed) - 1)
        if compressed[offset] == 0x0D and compressed[offset + 1] == 0x0A
    ]
    for offset in reversed(crlf_offsets):
        del compressed[offset]

    corrupt = build_rgb_png(1, 120, filtered, idat_data=bytes(compressed))
    start_offset = idat_bruteforce.first_idat_problem_stream_offset(corrupt)

    probe = idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce(
        corrupt,
        start_offset=start_offset,
        checkpoint_path=str(tmp_path / "_UltimateMegaSuperLineFeedBruteForce.checkpoint.jsonl"),
        max_depth=2,
        max_offsets=128,
        budget=300,
        beam_width=1,
    )

    assert probe.tested_candidates == 300
    assert probe.budget_exhausted is True
    assert probe.best is not None
    assert probe.best.after.adler_status != "adler_match"


def test_ultimate_linefeed_bruteforce_broadens_small_focused_space(tmp_path):
    filtered = b"".join(b"\x00" + bytes((13, 10, row % 256)) for row in range(120))
    compressed = bytearray(zlib.compress(filtered, level=0))
    crlf_offsets = [
        offset
        for offset in range(2, len(compressed) - 1)
        if compressed[offset] == 0x0D and compressed[offset + 1] == 0x0A
    ]
    for offset in reversed(crlf_offsets[:4]):
        del compressed[offset]

    corrupt = build_rgb_png(1, 120, filtered, idat_data=bytes(compressed))
    start_offset = idat_bruteforce.first_idat_problem_stream_offset(corrupt)

    probe = idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce(
        corrupt,
        start_offset=start_offset,
        checkpoint_path=str(tmp_path / "_UltimateMegaSuperLineFeedBruteForce.checkpoint.jsonl"),
        max_depth=2,
        max_offsets=8,
        budget=250,
        beam_width=1,
    )

    assert probe.tested_candidates == 250
    assert probe.budget_exhausted is True
    assert probe.best is not None
    assert probe.best.after.adler_status != "adler_match"


def test_ultimate_linefeed_bruteforce_skips_clean_complete_idat(tmp_path):
    filtered = b"".join(b"\x00" + bytes((row, row, row)) for row in range(8))
    clean = build_rgb_png(1, 8, filtered)

    probe = idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce(
        clean,
        checkpoint_path=str(tmp_path / "_UltimateMegaSuperLineFeedBruteForce.checkpoint.jsonl"),
        budget=500,
    )

    assert probe.best is None
    assert probe.tested_candidates == 0
    assert probe.budget_exhausted is False
    assert probe.reason == "IDAT stream is already complete with matching Adler"


def test_ultimate_linefeed_bruteforce_accepts_unbounded_budget(tmp_path):
    filtered = b"".join(b"\x00" + bytes((13, 10, row % 256)) for row in range(8))
    compressed = bytearray(zlib.compress(filtered, level=0))
    crlf_offsets = [
        offset
        for offset in range(2, len(compressed) - 1)
        if compressed[offset] == 0x0D and compressed[offset + 1] == 0x0A
    ]
    del compressed[crlf_offsets[0]]

    corrupt = build_rgb_png(1, 8, filtered, idat_data=bytes(compressed))

    probe = idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce(
        corrupt,
        checkpoint_path=str(tmp_path / "_UltimateMegaSuperLineFeedBruteForce.checkpoint.jsonl"),
        max_depth=1,
        max_offsets=2,
        budget=None,
        beam_width=1,
    )

    assert probe.tested_candidates > 0
    assert probe.budget_exhausted is False


def test_rebuild_partial_idat_blackfill_ignores_complete_or_unusable_streams():
    complete = build_rgb_png(1, 1, b"\x00abc")
    invalid = build_rgb_png(1, 1, b"\x00abc", idat_data=b"bad")

    assert idat.rebuild_partial_idat_blackfill(complete) is None
    assert idat.rebuild_partial_idat_blackfill(invalid) is None
    assert idat.rebuild_tolerant_idat_salvage(complete) is None
    assert idat.rebuild_tolerant_idat_salvage(invalid) is None


def test_analyze_idat_stream_reports_complete_stream():
    filtered = b"\x00abc" + b"\x00def"
    analysis = idat.analyze_idat_stream(build_rgb_png(1, 2, filtered))

    assert analysis.supported is True
    assert analysis.complete is True
    assert analysis.status == "complete"
    assert analysis.idat_chunk_count == 1
    assert analysis.compressed_size > 0
    assert analysis.decompressed_size == 8
    assert analysis.expected_size == 8
    assert analysis.complete_scanlines == 2
    assert analysis.usable_scanlines == 2
    assert analysis.zlib_error == ""
    assert analysis.error_offset is None
    assert analysis.stored_adler == zlib.adler32(filtered)
    assert analysis.computed_adler == zlib.adler32(filtered)
    assert analysis.adler_status == "adler_match"
    assert analysis.crc_provenance == "original_crc_ok"
    assert analysis.source_kind == "original"


def test_zlib_trailer_adler_extracts_target_from_idat_stream():
    filtered = b"\x00abc"
    compressed = zlib.compress(filtered)

    assert idat.zlib_trailer_adler(compressed) == zlib.adler32(filtered)
    assert idat.format_adler(zlib.adler32(filtered)).startswith("0x")
    assert idat.zlib_trailer_adler(b"bad") is None


def test_analyze_idat_stream_marks_rebuilt_adler_provenance():
    filtered = b"\x00abc"
    analysis = idat.analyze_idat_stream(
        build_rgb_png(1, 1, filtered),
        source_kind="clone",
        crc_provenance="rebuilt_by_chunklate",
    )

    assert analysis.complete is True
    assert analysis.adler_status == "adler_rebuilt"
    assert analysis.crc_provenance == "rebuilt_by_chunklate"
    assert analysis.source_kind == "clone"


def test_analyze_idat_stream_reports_corrupt_deflate():
    filtered = b"\x00abc"
    analysis = idat.analyze_idat_stream(build_rgb_png(1, 1, filtered, idat_data=b"\x78\x9c\xff\xff"))

    assert analysis.supported is True
    assert analysis.complete is False
    assert analysis.status == "corrupt_deflate"
    assert analysis.zlib_error
    assert analysis.error_offset is not None
    assert analysis.error_context_hex


def test_analyze_idat_stream_attaches_deflate_header_diagnosis():
    candidate, _offset, _original = dynamic_header_corrupt_png()

    analysis = idat.analyze_idat_stream(candidate)

    assert analysis.status == "corrupt_deflate"
    assert analysis.decompressed_size == 0
    assert analysis.usable_scanlines == 0
    assert analysis.deflate_header is not None
    assert analysis.deflate_header.status == "bad_code_length_tree"


def test_analyze_idat_stream_maps_error_to_multi_idat_file_offset():
    filtered = b"\x00abc" + b"\x00def"
    compressed = bytearray(zlib.compress(filtered))
    compressed[2] ^= 0xFF
    candidate = build_rgb_png(
        1,
        2,
        filtered,
        idat_data=bytes(compressed),
        idat_parts=split_bytes(bytes(compressed), 5),
    )

    analysis = idat.analyze_idat_stream(candidate)
    chunks = list(iter_chunks(candidate))
    idat_chunks = [chunk for chunk in chunks if chunk.chunk_type == b"IDAT"]

    assert analysis.status == "corrupt_deflate"
    assert analysis.error_offset is not None
    assert analysis.error_idat_index == 2
    assert analysis.error_idat_offset == analysis.error_offset - len(idat_chunks[0].data)
    assert analysis.error_file_offset == idat_chunks[1].offset + 8 + analysis.error_idat_offset


def test_idat_deflate_probe_repairs_single_byte_corruption():
    filtered = b"\x00abc" + b"\x00def"
    compressed = bytearray(zlib.compress(filtered))
    original = compressed[2]
    compressed[2] ^= 0xFF
    candidate = build_rgb_png(
        1,
        2,
        filtered,
        idat_data=bytes(compressed),
        idat_parts=split_bytes(bytes(compressed), 5),
    )

    result = idat_bruteforce.probe_idat_deflate_byte_candidates(candidate, window_radius=8)

    assert result.best is not None
    assert result.best.stream_offset == 2
    assert result.best.new_byte == original
    assert result.best.after.complete is True
    assert idat.analyze_idat_stream(result.best.data).complete is True


def test_deflate_header_probe_repairs_header_corruption():
    candidate, stream_offset, original = dynamic_header_corrupt_png()

    result = idat_bruteforce.probe_deflate_header_candidates(candidate, budget=1000)

    assert result.best is not None
    assert result.strategy == "deflate-header"
    assert result.best.stream_offset == stream_offset
    assert result.best.new_byte == original
    assert result.best.after.usable_scanlines == 100
    assert result.best.after.complete is True


def test_deflate_header_probe_does_not_accept_header_only_progress_without_scanlines():
    candidate = build_rgb_png(1, 1, b"\x00abc", idat_data=b"\x78\x9c\xff\xff")

    result = idat_bruteforce.probe_deflate_header_candidates(candidate, budget=128)

    assert result.best is None
    assert result.strategy == "deflate-header"


def test_idat_deflate_strategy_queue_uses_material_progress_only():
    filtered = b"\x00abc" + b"\x00def"
    compressed = bytearray(zlib.compress(filtered))
    compressed[2] ^= 0xFF
    candidate = build_rgb_png(
        1,
        2,
        filtered,
        idat_data=bytes(compressed),
        idat_parts=split_bytes(bytes(compressed), 5),
    )

    result = idat_bruteforce.probe_idat_deflate_strategy_queue(candidate)

    assert result.best is not None
    assert result.strategy in {"strict-byte", "pre-error-bit", "wide-byte"}
    assert result.best.after.complete is True


def test_idat_deflate_strategy_queue_chases_multiple_material_steps():
    filtered = b"\x00\x00\x00\x00" + b"\x00\x01\x01\x01"
    compressed = bytearray(zlib.compress(filtered))
    original_deflate_byte = compressed[2]
    original_adler_byte = compressed[-4]
    compressed[2] ^= 0xFF
    compressed[-4] ^= 0xFF
    candidate = build_rgb_png(1, 2, filtered, idat_data=bytes(compressed))

    result = idat_bruteforce.probe_idat_deflate_strategy_queue(candidate, max_steps=4)

    assert result.best is not None
    assert result.strategy == "chase"
    assert len(result.chain) == 2
    assert [(step.stream_offset, step.new_byte) for step in result.chain] == [
        (2, original_deflate_byte),
        (len(compressed) - 4, original_adler_byte),
    ]
    assert result.best.after.complete is True
    assert idat.analyze_idat_stream(result.best.data).complete is True


def test_idat_deflate_heavy_probe_reports_progress_and_repairs_candidate():
    calls = []
    filtered = b"\x00abc" + b"\x00def"
    compressed = bytearray(zlib.compress(filtered))
    original = compressed[2]
    compressed[2] ^= 0xFF
    candidate = build_rgb_png(1, 2, filtered, idat_data=bytes(compressed))

    result = idat_bruteforce.probe_idat_deflate_heavy_candidates(
        candidate,
        backtrack=8,
        forward=8,
        budget=5000,
        progress=lambda loop, budget, build: calls.append((loop, budget, build)),
    )

    assert result.best is not None
    assert result.best.stream_offset == 2
    assert result.best.new_byte == original
    assert result.best.after.complete is True
    assert calls[0] == (0, 5000, True)
    assert calls[-1][2] is False


def test_idat_deflate_probe_ignores_candidates_without_progress():
    candidate = build_rgb_png(1, 1, b"\x00abc", idat_data=b"\x78\x9c\xff\xff")

    result = idat_bruteforce.probe_idat_deflate_byte_candidates(candidate, window_radius=1, budget=4)

    assert result.best is None
    assert result.budget_exhausted is True


def test_idat_deflate_strategy_queue_reports_no_candidate_without_progress():
    compressed = bytearray(zlib.compress(b"\x00abc"))
    compressed[0] = 0
    compressed[1] = 0
    candidate = build_rgb_png(1, 1, b"\x00abc", idat_data=bytes(compressed))

    result = idat_bruteforce.probe_idat_deflate_strategy_queue(candidate)

    assert result.best is None
    assert result.strategy == "strategy-queue"
    assert result.reason == "IDAT error offset is unknown"


def test_idat_deflate_probe_does_not_treat_error_offset_drift_as_progress():
    before = idat.IdatStreamAnalysis(
        True,
        False,
        "corrupt_deflate",
        height=10,
        error_offset=114,
    )
    after = idat.IdatStreamAnalysis(
        True,
        False,
        "corrupt_deflate",
        height=10,
        error_offset=115,
    )

    assert idat_bruteforce.is_material_improvement(before, after) is False


def test_idat_deflate_probe_does_not_treat_decompressed_bytes_without_scanlines_as_progress():
    before = idat.IdatStreamAnalysis(
        True,
        False,
        "corrupt_deflate",
        height=10,
        decompressed_size=0,
        usable_scanlines=0,
        error_offset=28,
    )
    after = idat.IdatStreamAnalysis(
        True,
        False,
        "corrupt_deflate",
        height=10,
        decompressed_size=2048,
        complete_scanlines=3,
        usable_scanlines=0,
        error_offset=740,
    )

    assert idat_bruteforce.is_material_improvement(before, after) is False


def test_idat_deflate_probe_treats_new_usable_scanline_as_progress():
    before = idat.IdatStreamAnalysis(
        True,
        False,
        "corrupt_deflate",
        height=10,
        usable_scanlines=0,
    )
    after = idat.IdatStreamAnalysis(
        True,
        False,
        "corrupt_deflate",
        height=10,
        usable_scanlines=1,
    )

    assert idat_bruteforce.is_material_improvement(before, after) is True


def test_analyze_idat_stream_reports_bad_zlib_header():
    filtered = b"\x00abc"
    compressed = bytearray(zlib.compress(filtered))
    compressed[0] = 0
    compressed[1] = 0

    analysis = idat.analyze_idat_stream(build_rgb_png(1, 1, filtered, idat_data=bytes(compressed)))

    assert analysis.supported is True
    assert analysis.complete is False
    assert analysis.status == "bad_zlib_header"
    assert analysis.reason == "bad zlib header"
    assert analysis.error_offset is None


def test_analyze_idat_stream_reports_bad_adler():
    filtered = b"".join(b"\x00" + bytes((row, row, row)) for row in range(3))
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF

    analysis = idat.analyze_idat_stream(build_rgb_png(1, 3, filtered, idat_data=bytes(compressed)))

    assert analysis.supported is True
    assert analysis.complete is False
    assert analysis.status == "bad_adler"
    assert analysis.partial is True
    assert analysis.usable_scanlines == 3
    assert analysis.recovered_scanlines == filtered
    assert analysis.error_offset is not None
    assert analysis.stored_adler != zlib.adler32(filtered)
    assert analysis.computed_adler == zlib.adler32(filtered)
    assert analysis.adler_status == "adler_mismatch"


def test_analyze_idat_stream_reports_incomplete_stream():
    filtered = b"".join(b"\x00" + bytes((row, row, row)) for row in range(10))
    _candidate, partial = find_truncated_candidate(
        filtered,
        lambda analysis: analysis.usable_scanlines > 0 and analysis.decompression_error,
    )

    analysis = idat.analyze_idat_stream(_candidate)

    assert analysis.supported is True
    assert analysis.complete is False
    assert analysis.status == "incomplete_stream"
    assert analysis.partial is True
    assert analysis.usable_scanlines == partial.usable_scanlines
    assert analysis.error_offset == analysis.compressed_size


def test_analyze_idat_stream_reports_unsupported_interlace():
    filtered = b"\x00abc"
    analysis = idat.analyze_idat_stream(build_rgb_png(1, 1, filtered, interlace=1))

    assert analysis.supported is False
    assert analysis.complete is False
    assert analysis.status == "unsupported_interlace"
    assert analysis.reason == "interlaced PNG is not supported"


def main():
    checks = [
        ("Dummy scanline", test_dummy_scanline_preserves_legacy_sample_width),
        ("Zlib header", test_idat_zlib_header_skips_interlaced_streams_like_legacy_todo),
        ("Zlib header info", test_zlib_header_info_reads_window_and_legacy_compression_level),
        ("Dummy probe", test_build_dummy_idat_probe_decompresses_debug_stream_and_idat_stream),
        ("Invalid stream", test_build_dummy_idat_probe_reports_invalid_stream_without_raising),
        (
            "Partial IDAT complete stream",
            test_analyze_partial_idat_reports_complete_non_interlaced_stream,
        ),
        (
            "Partial IDAT complete multi-IDAT stream",
            test_analyze_partial_idat_concatenates_complete_multi_idat_stream,
        ),
        (
            "Partial IDAT truncated stream",
            test_analyze_partial_idat_keeps_good_scanlines_until_truncated_stream_error,
        ),
        (
            "Partial IDAT truncated multi-IDAT stream",
            test_analyze_partial_idat_recovers_truncated_multi_idat_stream,
        ),
        (
            "Partial IDAT bad Adler",
            test_analyze_partial_idat_reports_bad_adler_with_recovered_scanlines,
        ),
        (
            "Partial IDAT broken zlib header",
            test_analyze_partial_idat_rejects_broken_zlib_header_without_scanlines,
        ),
        (
            "Partial IDAT scanline tail",
            test_analyze_partial_idat_discards_partial_scanline_tail,
        ),
        (
            "Partial IDAT unsupported interlace",
            test_analyze_partial_idat_rejects_unsupported_interlace_before_repair_logic,
        ),
        (
            "Partial IDAT invalid stream",
            test_analyze_partial_idat_reports_invalid_stream_without_scanlines,
        ),
        (
            "Partial IDAT blackfill repair",
            test_rebuild_partial_idat_blackfill_keeps_prefix_and_fills_remaining_rows,
        ),
        (
            "Partial IDAT blackfill empty valid stream",
            test_rebuild_partial_idat_blackfill_handles_valid_empty_stream,
        ),
        (
            "Partial IDAT tolerant salvage",
            test_rebuild_tolerant_idat_salvage_keeps_rows_after_bad_filters,
        ),
        (
            "IDAT linefeed CR insert probe",
            test_idat_linefeed_cr_insert_probe_improves_salvage_candidate,
        ),
        (
            "SuperMega multi CRLF",
            test_super_mega_linefeed_force_recovers_multiple_crlf_deletions,
        ),
        (
            "SuperMega known gap",
            test_super_mega_linefeed_force_uses_known_gap_phase_before_broad_search,
        ),
        (
            "SuperMega budget exhausted",
            test_super_mega_linefeed_force_reports_budget_exhausted_but_keeps_best_candidate,
        ),
        (
            "SuperMega wrong Adler target",
            test_super_mega_linefeed_force_keeps_best_when_original_adler_target_is_wrong,
        ),
        (
            "Ultimate suspect offsets",
            test_ultimate_linefeed_suspect_offsets_prioritize_error_and_linefeeds,
        ),
        (
            "Partial IDAT blackfill ignored cases",
            test_rebuild_partial_idat_blackfill_ignores_complete_or_unusable_streams,
        ),
        ("IDAT stream complete", test_analyze_idat_stream_reports_complete_stream),
        ("IDAT stream target Adler", test_zlib_trailer_adler_extracts_target_from_idat_stream),
        ("IDAT stream rebuilt Adler", test_analyze_idat_stream_marks_rebuilt_adler_provenance),
        ("IDAT stream corrupt deflate", test_analyze_idat_stream_reports_corrupt_deflate),
        (
            "IDAT stream deflate header diagnosis",
            test_analyze_idat_stream_attaches_deflate_header_diagnosis,
        ),
        ("IDAT stream error mapping", test_analyze_idat_stream_maps_error_to_multi_idat_file_offset),
        ("IDAT deflate byte probe repair", test_idat_deflate_probe_repairs_single_byte_corruption),
        ("IDAT deflate header probe repair", test_deflate_header_probe_repairs_header_corruption),
        (
            "IDAT deflate header probe no scanlines",
            test_deflate_header_probe_does_not_accept_header_only_progress_without_scanlines,
        ),
        ("IDAT deflate strategy queue repair", test_idat_deflate_strategy_queue_uses_material_progress_only),
        (
            "IDAT deflate strategy queue chase",
            test_idat_deflate_strategy_queue_chases_multiple_material_steps,
        ),
        (
            "IDAT deflate heavy probe repair",
            test_idat_deflate_heavy_probe_reports_progress_and_repairs_candidate,
        ),
        ("IDAT deflate byte probe no progress", test_idat_deflate_probe_ignores_candidates_without_progress),
        (
            "IDAT deflate strategy queue no progress",
            test_idat_deflate_strategy_queue_reports_no_candidate_without_progress,
        ),
        (
            "IDAT deflate byte probe ignores offset-only drift",
            test_idat_deflate_probe_does_not_treat_error_offset_drift_as_progress,
        ),
        (
            "IDAT deflate byte probe ignores bytes without scanlines",
            test_idat_deflate_probe_does_not_treat_decompressed_bytes_without_scanlines_as_progress,
        ),
        (
            "IDAT deflate byte probe accepts usable scanline",
            test_idat_deflate_probe_treats_new_usable_scanline_as_progress,
        ),
        ("IDAT stream bad zlib header", test_analyze_idat_stream_reports_bad_zlib_header),
        ("IDAT stream bad Adler", test_analyze_idat_stream_reports_bad_adler),
        ("IDAT stream incomplete", test_analyze_idat_stream_reports_incomplete_stream),
        ("IDAT stream unsupported interlace", test_analyze_idat_stream_reports_unsupported_interlace),
    ]

    print("Running IDAT tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"IDAT tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
