#!/usr/bin/env python3
import json
import sys
import struct
import zlib
import math
from pathlib import Path
from types import SimpleNamespace


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
    repair_idat_marker_chain_from_visible_headers,
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


def visual_scope_png(width=96, height=64, *, variant="scope"):
    from io import BytesIO
    from PIL import Image, ImageDraw

    image = Image.new("RGBA", (width, height), (0, 0, 0, 255))
    draw = ImageDraw.Draw(image)
    if variant == "scope":
        for x in range(0, width, max(1, width // 8)):
            draw.line((x, 0, x, height), fill=(55, 55, 55, 255))
        for y in range(0, height, max(1, height // 6)):
            draw.line((0, y, width, y), fill=(45, 45, 45, 255))
        draw.rectangle((width * 3 // 4, 4, width - 4, height * 3 // 4), outline=(180, 180, 180, 255))
        draw.line((0, height * 3 // 4, width, height * 3 // 4), fill=(255, 180, 0, 255))
        draw.line(
            (
                width // 6,
                height * 2 // 3,
                width // 4,
                height // 4,
                width // 2,
                height // 4,
                width * 5 // 8,
                height * 2 // 3,
            ),
            fill=(210, 210, 0, 255),
            width=2,
        )
        draw.line((width // 9, height // 3, width // 9, height * 5 // 6), fill=(0, 220, 220, 255), width=2)
        draw.line((width * 4 // 5, height // 5, width * 4 // 5, height * 5 // 6), fill=(220, 0, 220, 255), width=2)
    else:
        for index in range(0, min(width, height), 7):
            draw.line((0, index, width, height - index), fill=(180, 20, 20, 255), width=2)
        draw.ellipse((width // 3, height // 3, width * 2 // 3, height * 2 // 3), outline=(20, 180, 20, 255), width=3)
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def split_bytes(data, *sizes):
    parts = []
    offset = 0
    for size in sizes:
        parts.append(data[offset:offset + size])
        offset += size
    parts.append(data[offset:])
    return tuple(parts)


def truncate_idat_1_fixture_bytes():
    for path in (
        ROOT / "brokenjavapngsuite" / "truncate_idat_1.png",
        ROOT / "schaik-javapng-samples" / "brokenjavapngsuite" / "truncate_idat_1.png",
        ROOT / "Png_Errors_handled_by_Chunklate_So_Far" / "truncate_idat_1.png",
    ):
        if path.exists():
            return path.read_bytes()
    raise FileNotFoundError("truncate_idat_1.png fixture not found")


def truncate_zlib_fixture_bytes():
    for path in (
        ROOT / "brokenjavapngsuite" / "truncate_zlib.png",
        ROOT / "schaik-javapng-samples" / "brokenjavapngsuite" / "truncate_zlib.png",
        ROOT / "Png_Errors_handled_by_Chunklate_So_Far" / "truncate_zlib.png",
    ):
        if path.exists():
            return path.read_bytes()
    raise FileNotFoundError("truncate_zlib.png fixture not found")


def truncate_zlib_2_fixture_bytes():
    for path in (
        ROOT / "brokenjavapngsuite" / "truncate_zlib_2.png",
        ROOT / "schaik-javapng-samples" / "brokenjavapngsuite" / "truncate_zlib_2.png",
        ROOT / "Png_Errors_handled_by_Chunklate_So_Far" / "truncate_zlib_2.png",
    ):
        if path.exists():
            return path.read_bytes()
    raise FileNotFoundError("truncate_zlib_2.png fixture not found")


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


def test_analyze_partial_idat_repairs_interlaced_stream_with_adam7_blackfill():
    filtered = b"\x00abc"
    compressed = zlib.compress(filtered)
    candidate = build_rgb_png(1, 1, filtered, idat_data=compressed[:-1], interlace=1)
    analysis = idat.analyze_partial_idat(candidate)
    repair = idat.rebuild_partial_idat_blackfill(candidate)

    assert analysis.supported is True
    assert analysis.complete is False
    assert analysis.usable_scanlines == 1
    assert repair is not None
    assert repair.recovered_scanlines == 1
    assert repair.total_scanlines == 1
    assert validate_png_structure(repair.data).ok


def test_rebuild_partial_idat_blackfill_repairs_truncated_adam7_fixture():
    candidate = truncate_zlib_2_fixture_bytes()
    normalized = idat.normalize_truncated_idat_at_eof(candidate)

    assert normalized is not None
    repair = idat.rebuild_partial_idat_blackfill(normalized.data)

    assert repair is not None
    assert repair.strategy == "partial-idat-blackfill recovered 113/131 scanlines"
    assert repair.width == 91
    assert repair.height == 69
    assert repair.recovered_scanlines == 113
    assert repair.total_scanlines == 131
    assert validate_png_structure(repair.data).ok


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


def test_rebuild_idat_from_donor_replaces_zero_scanline_idat():
    broken = truncate_idat_1_fixture_bytes()
    donor = (ROOT / "schaik-javapng-samples" / "basn0g01.png").read_bytes()

    repair = idat.rebuild_idat_from_donor(
        broken,
        donor,
        donor_label="basn0g01.png",
        donor_path="schaik-javapng-samples/basn0g01.png",
    )

    assert repair is not None
    assert repair.strategy == "idat-donor-basn0g01"
    assert repair.width == 32
    assert repair.height == 32
    assert validate_png_structure(repair.data).ok

    fixed_stream = b"".join(
        chunk.data for chunk in iter_chunks(repair.data) if chunk.chunk_type == b"IDAT"
    )
    donor_stream = b"".join(
        chunk.data for chunk in iter_chunks(donor) if chunk.chunk_type == b"IDAT"
    )
    assert zlib.decompress(fixed_stream) == zlib.decompress(donor_stream)


def test_rebuild_idat_from_donor_rejects_incompatible_shape():
    broken = truncate_idat_1_fixture_bytes()
    incompatible = build_rgb_png(1, 1, b"\x00abc")

    assert idat.rebuild_idat_from_donor(broken, incompatible) is None


def test_rebuild_synthetic_idat_builds_diagnostic_image_from_ihdr():
    broken = truncate_idat_1_fixture_bytes()

    repair = idat.rebuild_synthetic_idat(broken)

    assert repair is not None
    assert repair.strategy == "idat-synthetic-diagnostic"
    assert repair.width == 32
    assert repair.height == 32
    assert validate_png_structure(repair.data).ok

    stream = b"".join(chunk.data for chunk in iter_chunks(repair.data) if chunk.chunk_type == b"IDAT")
    raw = zlib.decompress(stream)
    assert len(raw) == 160
    assert raw != b"\x00" * 160


def test_normalize_truncated_idat_at_eof_rebuilds_analyzable_png():
    broken = truncate_zlib_fixture_bytes()

    normalized = idat.normalize_truncated_idat_at_eof(broken)

    assert normalized is not None
    assert normalized.declared_length == 433
    assert normalized.available_length == 24
    assert normalized.missing_bytes == 409
    assert validate_png_structure(normalized.data, require_decodable_idat=False).ok
    assert not validate_png_structure(normalized.data).ok
    analysis = idat.analyze_partial_idat(normalized.data)
    assert analysis.supported is True
    assert analysis.usable_scanlines == 0


def test_rebuild_zero_scanline_placeholder_handles_truncated_zlib_normalization():
    broken = truncate_zlib_fixture_bytes()
    normalized = idat.normalize_truncated_idat_at_eof(broken)
    assert normalized is not None

    repair = idat.rebuild_zero_scanline_placeholder(normalized.data)

    assert repair is not None
    assert repair.strategy == "zero-scanline-placeholder recovered 0/32 scanlines"
    assert validate_png_structure(repair.data).ok
    stream = b"".join(chunk.data for chunk in iter_chunks(repair.data) if chunk.chunk_type == b"IDAT")
    raw = zlib.decompress(stream)
    assert raw == b"\x00" * 1056


def test_rebuild_tolerant_idat_salvage_keeps_rows_after_bad_filters():
    linefeed = repair_linefeed_conversion(
        (ROOT / "Png_Errors_handled_by_Chunklate_So_Far" / "linefeedcorruption3.png").read_bytes(),
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


def test_idat_marker_chain_repair_preserves_valid_idat_chunks_byte_for_byte():
    linefeed = repair_linefeed_conversion(
        (ROOT / "Png_Errors_handled_by_Chunklate_So_Far" / "linefeedcorruption3.png").read_bytes(),
        allow_partial=True,
    )
    assert linefeed is not None

    repairs = repair_idat_marker_chain_from_visible_headers(linefeed.data)

    assert repairs
    best = repairs[0]
    assert "IDAT@0x21" in best.preserved_chunks
    assert "IDAT@0x202d" in best.rebuilt_chunks
    assert validate_png_structure(best.data, require_decodable_idat=False).ok

    repaired_first_idat = next(chunk for chunk in iter_chunks(best.data) if chunk.chunk_type == b"IDAT")
    original_first_idat = linefeed.data[
        repaired_first_idat.offset : repaired_first_idat.offset + 12 + repaired_first_idat.length
    ]
    rebuilt_first_idat = best.data[
        repaired_first_idat.offset : repaired_first_idat.offset + 12 + repaired_first_idat.length
    ]

    assert rebuilt_first_idat == original_first_idat


def test_idat_marker_chain_repair_generates_declared_payload_and_shorten_variants():
    linefeed = repair_linefeed_conversion(
        (ROOT / "Png_Errors_handled_by_Chunklate_So_Far" / "linefeedcorruption3.png").read_bytes(),
        allow_partial=True,
    )
    assert linefeed is not None

    repairs = repair_idat_marker_chain_from_visible_headers(linefeed.data)

    assert len(repairs) == 2
    assert any(repair.declared_payload_chunks == ("IDAT@0x202d",) for repair in repairs)
    assert any(repair.shortened_chunks == ("IDAT@0x202d",) for repair in repairs)
    assert all("XBt" not in ",".join(repair.rebuilt_chunks) for repair in repairs)
    assert all(validate_png_structure(repair.data, require_decodable_idat=False).ok for repair in repairs)


def test_idat_marker_chain_fixture_prefers_declared_payload_visual_salvage():
    linefeed = repair_linefeed_conversion(
        (ROOT / "Png_Errors_handled_by_Chunklate_So_Far" / "linefeedcorruption3.png").read_bytes(),
        allow_partial=True,
    )
    assert linefeed is not None

    repairs = repair_idat_marker_chain_from_visible_headers(linefeed.data)
    declared = next(repair for repair in repairs if repair.declared_payload_chunks)
    shortened = next(repair for repair in repairs if repair.shortened_chunks)
    declared_salvage = idat.rebuild_tolerant_idat_salvage(declared.data)
    shortened_salvage = idat.rebuild_tolerant_idat_salvage(shortened.data)

    assert declared_salvage is not None
    assert shortened_salvage is not None
    assert declared_salvage.recovered_scanlines == 498
    assert shortened_salvage.recovered_scanlines == 495


def test_idat_linefeed_cr_insert_probe_improves_salvage_candidate():
    linefeed = repair_linefeed_conversion(
        (ROOT / "Png_Errors_handled_by_Chunklate_So_Far" / "linefeedcorruption3.png").read_bytes(),
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


def test_ultimate_linefeed_estimate_counts_theoretical_combinations():
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

    estimate = idat_bruteforce.estimate_ultimate_linefeed_search(
        corrupt,
        start_offset=start_offset,
        max_depth=4,
        max_offsets=8,
    )

    assert estimate.operation_count > 0
    assert estimate.suspect_offsets
    assert estimate.total_combinations == sum(
        math.comb(estimate.operation_count, depth)
        for depth in range(1, min(estimate.operation_count, 4) + 1)
    )


def test_ultimate_linefeed_budget_modes_apply_divisors_without_upper_cap():
    total = 7_012_540_641

    assert idat_bruteforce.ultimate_linefeed_combination_count(5, 4) == 30
    assert idat_bruteforce.ultimate_linefeed_budget_decision(total, "quick").budget == 70_126
    assert idat_bruteforce.ultimate_linefeed_budget_decision(total, "normal").budget == 140_251
    assert idat_bruteforce.ultimate_linefeed_budget_decision(total, "deep").budget == 701_255
    assert idat_bruteforce.ultimate_linefeed_budget_decision(total, "very deep").budget == 7_012_541
    assert idat_bruteforce.ultimate_linefeed_budget_decision(total, "very_deep").budget == 7_012_541
    assert idat_bruteforce.ultimate_linefeed_budget_decision(total, "deeeeeeep").budget == 70_125_407
    assert idat_bruteforce.ultimate_linefeed_budget_decision(total, "abyssal").budget == 701_254_065
    assert idat_bruteforce.ultimate_linefeed_budget_decision(total, "inception").budget == 3_506_270_321
    assert idat_bruteforce.ultimate_linefeed_budget_decision(100, "normal").budget == 100
    assert idat_bruteforce.ultimate_linefeed_budget_decision(10**15, "deep").budget == 100_000_000_000

    manual = idat_bruteforce.ultimate_linefeed_budget_decision(total, "manual", manual_budget=1234)
    unbounded = idat_bruteforce.ultimate_linefeed_budget_decision(total, "unbounded")
    aborted = idat_bruteforce.ultimate_linefeed_budget_decision(total, "abort")

    assert manual.budget == 1234
    assert unbounded.budget is None
    assert unbounded.coverage == 100.0
    assert aborted.aborted is True
    try:
        idat_bruteforce.ultimate_linefeed_budget_decision(total, "manual", manual_budget=0)
    except ValueError:
        pass
    else:
        raise AssertionError("manual budget zero should be rejected")


def test_ultimate_linefeed_preview_callback_only_receives_valid_complete_candidates():
    calls = []
    valid = SimpleNamespace(after=SimpleNamespace(supported=True, complete=True))
    incomplete = SimpleNamespace(after=SimpleNamespace(supported=True, complete=False))
    unsupported = SimpleNamespace(after=SimpleNamespace(supported=False, complete=True))

    idat_bruteforce._preview_ultimate_candidate_if_valid(
        valid,
        12,
        100,
        lambda *args: calls.append(args),
    )
    idat_bruteforce._preview_ultimate_candidate_if_valid(
        incomplete,
        13,
        100,
        lambda *args: calls.append(args),
    )
    idat_bruteforce._preview_ultimate_candidate_if_valid(
        unsupported,
        14,
        100,
        lambda *args: calls.append(args),
    )
    idat_bruteforce._preview_ultimate_candidate_if_valid(
        valid,
        15,
        100,
        lambda *args: (_ for _ in ()).throw(RuntimeError("preview failed")),
    )

    assert calls == [(valid, 12, 100)]


def test_rebuild_visual_idat_preview_recompresses_full_bad_adler_candidate():
    filtered = b"\x00abc" + b"\x00def" + b"\x00ghi"
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF
    corrupt = build_rgb_png(1, 3, filtered, idat_data=bytes(compressed))

    before = idat.analyze_idat_stream(corrupt)
    repair = idat.rebuild_visual_idat_preview(corrupt)

    assert before.status == "bad_adler"
    assert before.usable_scanlines == 3
    assert repair is not None
    assert repair.strategy.startswith("rebuilt_adler_preview")
    assert validate_png_structure(repair.data).ok
    rebuilt = idat.analyze_idat_stream(repair.data)
    assert rebuilt.complete is True
    assert rebuilt.adler_status == "adler_match"
    assert zlib.decompress(
        b"".join(chunk.data for chunk in iter_chunks(repair.data) if chunk.chunk_type == b"IDAT")
    ) == filtered


def test_ultimate_visual_gallery_keeps_equal_score_distinct_operations():
    filtered = b"\x00abc" + b"\x00def"
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF
    corrupt = build_rgb_png(1, 2, filtered, idat_data=bytes(compressed))
    analysis = idat.analyze_idat_stream(corrupt)
    first = idat_bruteforce.SuperMegaLinefeedCandidate(
        corrupt,
        (idat_bruteforce.SuperMegaLinefeedOperation("ultimate-insert-cr-before-lf", 4, b"", b"\r"),),
        analysis,
        analysis,
        state_id=1,
        score=idat_bruteforce.super_mega_linefeed_score(analysis, 1),
    )
    second = idat_bruteforce.SuperMegaLinefeedCandidate(
        corrupt,
        (idat_bruteforce.SuperMegaLinefeedOperation("ultimate-remove-cr", 8, b"\r", b""),),
        analysis,
        analysis,
        state_id=2,
        score=idat_bruteforce.super_mega_linefeed_score(analysis, 1),
    )

    gallery = idat_bruteforce._remember_ultimate_visual_candidate(
        (),
        first,
        tested=10,
        reference_image=None,
        min_coverage=0.95,
        limit=100,
    )
    gallery = idat_bruteforce._remember_ultimate_visual_candidate(
        gallery,
        second,
        tested=11,
        reference_image=None,
        min_coverage=0.95,
        limit=100,
    )

    assert len(gallery) == 2
    assert {item.operation_hash for item in gallery} == {
        idat_bruteforce._ultimate_operation_hash(first.operations),
        idat_bruteforce._ultimate_operation_hash(second.operations),
    }


def test_ultimate_visual_gallery_limit_evicts_worst_candidate():
    filtered = b"\x00abc" + b"\x00def" + b"\x00ghi"
    partial = build_rgb_png(1, 3, filtered, idat_data=zlib.compress(filtered[:8]))
    partial_analysis = idat.analyze_idat_stream(partial)
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF
    full = build_rgb_png(1, 3, filtered, idat_data=bytes(compressed))
    full_analysis = idat.analyze_idat_stream(full)
    worse = idat_bruteforce.SuperMegaLinefeedCandidate(
        partial,
        (idat_bruteforce.SuperMegaLinefeedOperation("ultimate-insert-cr-before-lf", 4, b"", b"\r"),),
        partial_analysis,
        partial_analysis,
        state_id=1,
        score=idat_bruteforce.super_mega_linefeed_score(partial_analysis, 1),
    )
    better = idat_bruteforce.SuperMegaLinefeedCandidate(
        full,
        (idat_bruteforce.SuperMegaLinefeedOperation("ultimate-insert-cr-before-lf", 8, b"", b"\r"),),
        full_analysis,
        full_analysis,
        state_id=2,
        score=idat_bruteforce.super_mega_linefeed_score(full_analysis, 1),
    )

    gallery = idat_bruteforce._remember_ultimate_visual_candidate(
        (),
        worse,
        tested=10,
        reference_image=None,
        min_coverage=0.0,
        limit=1,
    )
    gallery = idat_bruteforce._remember_ultimate_visual_candidate(
        gallery,
        better,
        tested=11,
        reference_image=None,
        min_coverage=0.0,
        limit=1,
    )

    assert len(gallery) == 1
    assert gallery[0].candidate.state_id == 2
    assert gallery[0].candidate.after.usable_scanlines == 3


def test_ultimate_visual_gallery_skips_structural_downgrade_before_limit(monkeypatch):
    filtered = b"\x00abc" + b"\x00def" + b"\x00ghi"
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF
    full = build_rgb_png(1, 3, filtered, idat_data=bytes(compressed))
    full_analysis = idat.analyze_idat_stream(full)
    partial = build_rgb_png(1, 3, filtered, idat_data=zlib.compress(filtered[:8]))
    partial_analysis = idat.analyze_idat_stream(partial)
    better = idat_bruteforce.SuperMegaLinefeedCandidate(
        full,
        (idat_bruteforce.SuperMegaLinefeedOperation("ultimate-insert-cr-before-lf", 8, b"", b"\r"),),
        full_analysis,
        full_analysis,
        state_id=2,
        score=idat_bruteforce.super_mega_linefeed_score(full_analysis, 1),
    )
    worse = idat_bruteforce.SuperMegaLinefeedCandidate(
        partial,
        (idat_bruteforce.SuperMegaLinefeedOperation("ultimate-insert-cr-before-lf", 4, b"", b"\r"),),
        partial_analysis,
        partial_analysis,
        state_id=1,
        score=idat_bruteforce.super_mega_linefeed_score(partial_analysis, 1),
    )
    gallery = idat_bruteforce._remember_ultimate_visual_candidate(
        (),
        better,
        tested=10,
        reference_image=None,
        min_coverage=0.0,
        limit=100,
    )
    calls = []

    def fail_if_scored(*args, **kwargs):
        calls.append((args, kwargs))
        return None

    monkeypatch.setattr(
        idat_bruteforce,
        "_ultimate_visual_candidate_from_candidate",
        fail_if_scored,
    )

    updated = idat_bruteforce._remember_ultimate_visual_candidate(
        gallery,
        worse,
        tested=11,
        reference_image=None,
        min_coverage=0.0,
        limit=100,
    )

    assert updated == gallery
    assert calls == []


def test_ultimate_visual_gallery_structure_beats_reference_rank():
    filtered = b"\x00abc" + b"\x00def" + b"\x00ghi"
    partial = build_rgb_png(1, 3, filtered, idat_data=zlib.compress(filtered[:8]))
    partial_analysis = idat.analyze_idat_stream(partial)
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF
    full = build_rgb_png(1, 3, filtered, idat_data=bytes(compressed))
    full_analysis = idat.analyze_idat_stream(full)
    visually_close = idat_bruteforce.SuperMegaLinefeedCandidate(
        partial,
        (idat_bruteforce.SuperMegaLinefeedOperation("ultimate-insert-cr-before-lf", 4, b"", b"\r"),),
        partial_analysis,
        partial_analysis,
        state_id=1,
        score=idat_bruteforce.super_mega_linefeed_score(partial_analysis, 1),
        visual_score=0.0,
    )
    visually_bad_full = idat_bruteforce.SuperMegaLinefeedCandidate(
        full,
        (idat_bruteforce.SuperMegaLinefeedOperation("ultimate-insert-cr-before-lf", 8, b"", b"\r"),),
        full_analysis,
        full_analysis,
        state_id=2,
        score=idat_bruteforce.super_mega_linefeed_score(full_analysis, 1),
        visual_score=100.0,
    )

    close_rank = idat_bruteforce._ultimate_visual_candidate_rank(
        visually_close,
        coverage=visually_close.after.usable_scanlines / visually_close.after.height,
        visual_score=visually_close.visual_score,
    )
    bad_full_rank = idat_bruteforce._ultimate_visual_candidate_rank(
        visually_bad_full,
        coverage=visually_bad_full.after.usable_scanlines / visually_bad_full.after.height,
        visual_score=visually_bad_full.visual_score,
    )

    assert bad_full_rank < close_rank


def test_ultimate_top_candidates_structure_beats_reference_rank():
    filtered = b"\x00abc" + b"\x00def" + b"\x00ghi"
    partial = build_rgb_png(1, 3, filtered, idat_data=zlib.compress(filtered[:8]))
    partial_analysis = idat.analyze_idat_stream(partial)
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF
    full = build_rgb_png(1, 3, filtered, idat_data=bytes(compressed))
    full_analysis = idat.analyze_idat_stream(full)
    visually_close = idat_bruteforce.SuperMegaLinefeedCandidate(
        partial,
        (idat_bruteforce.SuperMegaLinefeedOperation("ultimate-insert-cr-before-lf", 4, b"", b"\r"),),
        partial_analysis,
        partial_analysis,
        state_id=1,
        score=idat_bruteforce.super_mega_linefeed_score(partial_analysis, 1),
        visual_score=0.0,
    )
    visually_bad_full = idat_bruteforce.SuperMegaLinefeedCandidate(
        full,
        (idat_bruteforce.SuperMegaLinefeedOperation("ultimate-insert-cr-before-lf", 8, b"", b"\r"),),
        full_analysis,
        full_analysis,
        state_id=2,
        score=idat_bruteforce.super_mega_linefeed_score(full_analysis, 1),
        visual_score=100.0,
    )

    top = idat_bruteforce._remember_ultimate_top_candidate((), visually_bad_full, limit=1)
    top = idat_bruteforce._remember_ultimate_top_candidate(top, visually_close, limit=1)

    assert top[0].state_id == 2


def test_ultimate_top_candidates_reference_rank_breaks_structural_ties():
    filtered = b"\x00abc" + b"\x00def" + b"\x00ghi"
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF
    corrupt = build_rgb_png(1, 3, filtered, idat_data=bytes(compressed))
    analysis = idat.analyze_idat_stream(corrupt)
    visually_close = idat_bruteforce.SuperMegaLinefeedCandidate(
        corrupt,
        (idat_bruteforce.SuperMegaLinefeedOperation("ultimate-insert-cr-before-lf", 4, b"", b"\r"),),
        analysis,
        analysis,
        state_id=1,
        score=idat_bruteforce.super_mega_linefeed_score(analysis, 1),
        visual_score=0.0,
    )
    visually_bad = idat_bruteforce.SuperMegaLinefeedCandidate(
        corrupt,
        (idat_bruteforce.SuperMegaLinefeedOperation("ultimate-insert-cr-before-lf", 8, b"", b"\r"),),
        analysis,
        analysis,
        state_id=2,
        score=idat_bruteforce.super_mega_linefeed_score(analysis, 1),
        visual_score=100.0,
    )

    top = idat_bruteforce._remember_ultimate_top_candidate((), visually_bad, limit=1)
    top = idat_bruteforce._remember_ultimate_top_candidate(top, visually_close, limit=1)

    assert top[0].state_id == 1


def test_ultimate_checkpoint_seed_candidates_ignore_gallery_limit_on_resume():
    filtered = b"\x00abc"
    png_data = build_rgb_png(1, 1, filtered)
    analysis = idat.analyze_idat_stream(png_data)
    candidates = tuple(
        idat_bruteforce.SuperMegaLinefeedCandidate(
            png_data,
            (),
            analysis,
            analysis,
            state_id=index,
            score=(0, 400 - index, 1, 1, 1, 0, 0, 0),
        )
        for index in range(400)
    )

    seeds = idat_bruteforce._ultimate_checkpoint_seed_candidates(
        candidates,
        beam_width=8,
        visual_gallery_limit=1000,
    )
    seed_ids = {candidate.state_id for candidate in seeds}

    assert len(seeds) == 16
    assert set(range(8)).issubset(seed_ids)
    assert set(range(392, 400)).issubset(seed_ids)
    assert 300 not in seed_ids


def test_ultimate_visual_gallery_write_removes_obsolete_previews(tmp_path):
    filtered = b"\x00abc" + b"\x00def"
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF
    corrupt = build_rgb_png(1, 2, filtered, idat_data=bytes(compressed))
    analysis = idat.analyze_idat_stream(corrupt)
    candidate = idat_bruteforce.SuperMegaLinefeedCandidate(
        corrupt,
        (idat_bruteforce.SuperMegaLinefeedOperation("ultimate-insert-cr-before-lf", 4, b"", b"\r"),),
        analysis,
        analysis,
        state_id=1,
        score=idat_bruteforce.super_mega_linefeed_score(analysis, 1),
    )
    gallery = idat_bruteforce._remember_ultimate_visual_candidate(
        (),
        candidate,
        tested=10,
        reference_image=None,
        min_coverage=0.95,
        limit=100,
    )
    gallery_path = tmp_path / "_UltimateMegaSuperLineFeedBruteForce.visual.json"
    preview_dir = tmp_path / "Bruteforce_Previews" / "VisualCandidates"
    preview_dir.mkdir(parents=True)
    stale = preview_dir / "_VisualCandidate_999_stale.png"
    stale.write_bytes(b"stale")

    written, count = idat_bruteforce._write_ultimate_visual_gallery(
        str(gallery_path),
        gallery,
        limit=1,
        reference_mode="similar",
        reference_regions_path="Folder_x.bad/_ULF.reference_regions.json",
        source_hash="source",
        phase="complete",
        depth=1,
        tested_candidates=10,
        state_count=2,
    )

    previews = list(preview_dir.glob("_VisualCandidate_*.png"))
    assert count == 1
    assert len(written) == 1
    assert not stale.exists()
    assert len(previews) == 1
    assert validate_png_structure(previews[0].read_bytes()).ok
    record = json.loads(gallery_path.read_text(encoding="utf-8"))
    assert record["preview_count"] == 1
    assert record["reference_mode"] == "similar"
    assert record["reference_regions_path"] == "Folder_x.bad/_ULF.reference_regions.json"
    assert record["candidates"][0]["preview_kind"] == "rebuilt_adler_preview"
    assert "visual_score_kind" in record["candidates"][0]
    assert "matched_patch_count" in record["candidates"][0]


def test_ultimate_linefeed_progress_checkpoint_round_trips(tmp_path):
    progress = tmp_path / "_UltimateMegaSuperLineFeedBruteForce.progress.json"
    operation_pool = (
        idat_bruteforce.SuperMegaLinefeedOperation("ultimate-remove-cr", 4, b"\r", b""),
    )
    pool_hash = idat_bruteforce._ultimate_operation_pool_hash(operation_pool)

    idat_bruteforce._write_ultimate_progress(
        str(progress),
        source_hash="source",
        target_adler=123,
        start_offset=7,
        max_depth=4,
        max_offsets=128,
        operation_pool_hash=pool_hash,
        focused_operation_pool_hash=pool_hash,
        broad_operation_pool_hash=pool_hash,
        phase="exhaustive",
        depth=2,
        pool_index=1,
        combination_rank=42,
        combination_indices=(4, 9),
        tested_candidates=100,
        pruned_candidates=12,
        state_count=44,
        budget=1000,
    )

    loaded, warning = idat_bruteforce._load_ultimate_progress(
        str(progress),
        source_hash="source",
        target_adler=123,
        start_offset=7,
        max_depth=4,
        max_offsets=128,
        operation_pool_hash=pool_hash,
        focused_operation_pool_hash=pool_hash,
        broad_operation_pool_hash=pool_hash,
    )
    mismatched, mismatch_warning = idat_bruteforce._load_ultimate_progress(
        str(progress),
        source_hash="other",
        target_adler=123,
        start_offset=7,
        max_depth=4,
        max_offsets=128,
        operation_pool_hash=pool_hash,
        focused_operation_pool_hash=pool_hash,
        broad_operation_pool_hash=pool_hash,
    )

    assert warning == ""
    assert loaded is not None
    assert loaded.phase == "exhaustive"
    assert loaded.combination_rank == 42
    assert loaded.combination_indices == (4, 9)
    assert loaded.tested_candidates == 100
    assert mismatched is None
    assert "source_hash mismatch" in mismatch_warning


def test_ultimate_linefeed_combination_indices_resume_without_restarting():
    indices = list(idat_bruteforce._combination_indices_from(5, 2, (1, 3)))

    assert indices == [(1, 3), (1, 4), (2, 3), (2, 4), (3, 4)]
    assert idat_bruteforce._next_combination_indices((3, 4), 5, 2) is None
    assert idat_bruteforce._combination_rank((1, 3), 5, 2) == 5


def test_ultimate_linefeed_bruteforce_resumes_progress_checkpoint(tmp_path):
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
    checkpoint = tmp_path / "_UltimateMegaSuperLineFeedBruteForce.checkpoint.jsonl"
    progress = tmp_path / "_UltimateMegaSuperLineFeedBruteForce.progress.json"
    before = idat.analyze_idat_stream(corrupt)
    _chunks, root_stream = idat_bruteforce._all_chunks_and_idat_stream(corrupt)
    suspect_offsets = idat_bruteforce.ultimate_linefeed_suspect_offsets(
        corrupt,
        start_offset=start_offset,
        max_offsets=64,
    )
    focused_pool = idat_bruteforce._ultimate_operation_pool(
        root_stream,
        suspect_offsets,
        target_adler=before.stored_adler,
        computed_adler=before.computed_adler,
    )
    broad_offsets = idat_bruteforce._ultimate_exhaustive_linefeed_offsets(
        root_stream,
        suspect_offsets=suspect_offsets,
        anchor=start_offset,
        max_offsets=max(64, min(len(root_stream), 64 * 8, 2048)),
    )
    broad_pool = idat_bruteforce._ultimate_operation_pool(
        root_stream,
        broad_offsets,
        target_adler=before.stored_adler,
        computed_adler=before.computed_adler,
    )
    merged_pool = idat_bruteforce._merge_ultimate_operations(focused_pool, broad_pool)
    idat_bruteforce._write_ultimate_progress(
        str(progress),
        source_hash=idat_bruteforce._stream_state_key(root_stream),
        target_adler=before.stored_adler,
        start_offset=start_offset,
        max_depth=2,
        max_offsets=64,
        operation_pool_hash=idat_bruteforce._ultimate_operation_pool_hash(merged_pool),
        focused_operation_pool_hash=idat_bruteforce._ultimate_operation_pool_hash(focused_pool),
        broad_operation_pool_hash=idat_bruteforce._ultimate_operation_pool_hash(broad_pool),
        phase="exhaustive",
        depth=1,
        pool_index=1,
        combination_rank=10,
        combination_indices=(10,),
        tested_candidates=50,
        pruned_candidates=5,
        state_count=7,
        budget=60,
    )

    progress_calls = []
    probe = idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce(
        corrupt,
        start_offset=start_offset,
        checkpoint_path=str(checkpoint),
        progress_path=str(progress),
        max_depth=2,
        max_offsets=64,
        budget=60,
        beam_width=1,
        progress=lambda *args: progress_calls.append(args),
    )

    assert probe.progress_resumed is True
    assert probe.progress_path == str(progress)
    assert probe.tested_candidates == 60
    assert probe.budget_exhausted is True
    assert progress_calls[0] == ("UltimateMegaSuperLineFeedBruteForce", 50, 60)
    assert ("UltimateMegaSuperLineFeedBruteForce", 0, 60) not in progress_calls


def test_ultimate_linefeed_probe_draws_progress_before_checkpoint_load(tmp_path):
    filtered = b"".join(b"\x00" + bytes((13, 10, row)) for row in range(8))
    compressed = bytearray(zlib.compress(filtered, level=0))
    crlf_offsets = [
        offset
        for offset in range(2, len(compressed) - 1)
        if compressed[offset] == 0x0D and compressed[offset + 1] == 0x0A
    ]
    del compressed[crlf_offsets[0]]
    corrupt = build_rgb_png(1, 8, filtered, idat_data=bytes(compressed))
    start_offset = idat_bruteforce.first_idat_problem_stream_offset(corrupt)
    calls = []
    original_load = idat_bruteforce._load_ultimate_checkpoint

    def fake_load(*args, **kwargs):
        assert calls == [("UltimateMegaSuperLineFeedBruteForce", 0, 1)]
        return [], set(), 1, 0

    try:
        idat_bruteforce._load_ultimate_checkpoint = fake_load
        idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce(
            corrupt,
            start_offset=start_offset,
            checkpoint_path=str(tmp_path / "_UltimateMegaSuperLineFeedBruteForce.checkpoint.jsonl"),
            max_depth=1,
            max_offsets=2,
            budget=0,
            progress=lambda *args: calls.append(args),
        )
    finally:
        idat_bruteforce._load_ultimate_checkpoint = original_load


def test_load_ultimate_checkpoint_emits_resume_progress(tmp_path):
    clean = build_rgb_png(1, 1, b"\x00abc")
    before = idat.analyze_idat_stream(clean)
    chunks, root_stream = idat_bruteforce._all_chunks_and_idat_stream(clean)
    source_hash = idat_bruteforce._stream_state_key(root_stream)
    checkpoint = tmp_path / "_UltimateMegaSuperLineFeedBruteForce.checkpoint.jsonl"
    operations = (
        idat_bruteforce.SuperMegaLinefeedOperation("ultimate-insert-cr-before-lf", 0, b"", b"\r"),
        idat_bruteforce.SuperMegaLinefeedOperation("ultimate-insert-cr-before-lf", 1, b"", b"\r"),
    )
    with open(checkpoint, "w", encoding="utf-8") as file:
        for state_id, operation in enumerate(operations, start=1):
            file.write(
                json.dumps(
                    {
                        "source_hash": source_hash,
                        "state_id": state_id,
                        "operations": [idat_bruteforce._operation_to_json(operation)],
                    }
                )
                + "\n"
            )

    calls = []
    original_monotonic = idat_bruteforce.time.monotonic
    ticks = iter((0.0, 3.0, 6.0, 9.0))
    try:
        idat_bruteforce.time.monotonic = lambda: next(ticks, 9.0)
        loaded, _visited, _next_state_id, resumed = idat_bruteforce._load_ultimate_checkpoint(
            str(checkpoint),
            source_hash=source_hash,
            root_stream=root_stream,
            chunks=chunks,
            before=before,
            target_adler=before.stored_adler,
            progress=lambda *args: calls.append(args),
            progress_total=100,
        )
    finally:
        idat_bruteforce.time.monotonic = original_monotonic

    assert len(loaded) == 2
    assert resumed == 2
    assert calls[0] == ("UltimateMegaSuperLineFeedBruteForce", 1, 100)
    assert calls[-1] == ("UltimateMegaSuperLineFeedBruteForce", 2, 100)


def test_load_ultimate_checkpoint_limits_candidate_rebuild(tmp_path, monkeypatch):
    filtered = dynamic_filtered_rows(100)
    clean = build_rgb_png(1, 100, filtered)
    before = idat.analyze_idat_stream(clean)
    chunks, root_stream = idat_bruteforce._all_chunks_and_idat_stream(clean)
    source_hash = idat_bruteforce._stream_state_key(root_stream)
    checkpoint = tmp_path / "_UltimateMegaSuperLineFeedBruteForce.checkpoint.jsonl"
    with open(checkpoint, "w", encoding="utf-8") as file:
        for state_id in range(20):
            old_byte = root_stream[state_id : state_id + 1]
            new_byte = bytes((old_byte[0] ^ 0x01,))
            operation = idat_bruteforce.SuperMegaLinefeedOperation(
                "bit-flip",
                state_id,
                old_byte,
                new_byte,
            )
            stream = idat_bruteforce._replay_operations(root_stream, (operation,))
            assert stream is not None
            file.write(
                json.dumps(
                    {
                        "source_hash": source_hash,
                        "stream_hash": idat_bruteforce._stream_state_key(stream),
                        "state_id": state_id,
                        "operations": [idat_bruteforce._operation_to_json(operation)],
                        "score": [0, 20 - state_id, state_id, state_id, 1, 0, 0, 0],
                        "status": "bad_adler",
                        "adler_status": "adler_mismatch",
                        "usable_scanlines": 20 - state_id,
                    }
                )
                + "\n"
            )

    calls = []
    replay_calls = []
    real_analyze = idat_bruteforce.idat.analyze_idat_stream
    real_replay = idat_bruteforce._replay_operations

    def counting_analyze(*args, **kwargs):
        calls.append(args)
        return real_analyze(*args, **kwargs)

    def counting_replay(*args, **kwargs):
        replay_calls.append(args)
        return real_replay(*args, **kwargs)

    monkeypatch.setattr(idat_bruteforce.idat, "analyze_idat_stream", counting_analyze)
    monkeypatch.setattr(idat_bruteforce, "_replay_operations", counting_replay)
    loaded, visited, next_state_id, resumed = idat_bruteforce._load_ultimate_checkpoint(
        str(checkpoint),
        source_hash=source_hash,
        root_stream=root_stream,
        chunks=chunks,
        before=before,
        target_adler=before.stored_adler,
        candidate_limit=3,
        beam_width=2,
    )

    loaded_ids = {candidate.state_id for candidate in loaded}
    assert resumed == 20
    assert len(visited) == 20
    assert next_state_id == 20
    assert len(loaded) == 5
    assert len(calls) == 5
    assert len(replay_calls) == 5
    assert {18, 19}.issubset(loaded_ids)
    assert {0, 1, 2}.issubset(loaded_ids)
    assert 10 not in loaded_ids


def test_ultimate_linefeed_eta_uses_twenty_humor_buckets():
    assert len(idat_bruteforce.ULTIMATE_LINEFEED_ETA_PHRASES) == 20
    assert idat_bruteforce.ultimate_linefeed_eta(200, candidates_per_second=100) == (
        idat_bruteforce.UltimateLinefeedEta(
            candidates_per_second=100,
            seconds=2.0,
            duration="2s",
            phrase="Barely enough time to look dramatic.",
        )
    )
    assert idat_bruteforce.ultimate_linefeed_eta_duration(3_506_270_321 / 100) == "1y 40d"
    assert idat_bruteforce.ultimate_linefeed_eta_phrase(10**19) == (
        "We will be dead before this finishes... but who cares."
    )
    assert idat_bruteforce.ultimate_linefeed_eta(None).phrase == (
        "No finish line. The fish has entered mythology."
    )


def test_ultimate_linefeed_universe_atom_comparison_lines():
    lines = idat_bruteforce.ultimate_linefeed_universe_atom_comparison_lines(
        7_012_540_641
    )

    assert lines == (
        "known universe atoms: about 10^80",
        "combination scale: about 1.43e70 times smaller",
    )
    assert idat_bruteforce.ultimate_linefeed_universe_atom_comparison_lines(0)[1] == (
        "combination scale: no candidates estimated"
    )
    assert idat_bruteforce.ultimate_linefeed_universe_atom_comparison_lines(10**81)[1] == (
        "combination scale: about 1e1 times larger"
    )


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
    assert probe.top_candidates
    assert probe.visual_candidates
    assert probe.visual_preview_count <= probe.visual_gallery_limit
    assert probe.visual_gallery_path.endswith(".visual.json")
    assert validate_png_structure(probe.visual_candidates[0].preview_data).ok
    assert "original Adler target was not recovered" in idat_bruteforce.ultimate_linefeed_probe_summary_line(probe)


def test_ultimate_linefeed_visual_gallery_limit_zero_disables_gallery(tmp_path):
    filtered = b"\x00abc" + b"\x00def"
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF
    corrupt = build_rgb_png(1, 2, filtered, idat_data=bytes(compressed))
    checkpoint = tmp_path / "_UltimateMegaSuperLineFeedBruteForce.checkpoint.jsonl"

    probe = idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce(
        corrupt,
        start_offset=len(compressed) - 4,
        checkpoint_path=str(checkpoint),
        max_depth=1,
        max_offsets=16,
        budget=256,
        beam_width=4,
        visual_gallery_limit=0,
    )

    assert probe.best is not None
    assert probe.visual_gallery_limit == 0
    assert probe.visual_gallery_path == ""
    assert probe.visual_candidates == ()
    assert probe.visual_preview_count == 0
    assert not (tmp_path / "_UltimateMegaSuperLineFeedBruteForce.visual.json").exists()


def test_ultimate_linefeed_sigint_flushes_visual_gallery(tmp_path):
    import signal

    filtered = b"\x00abc" + b"\x00def"
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF
    corrupt = build_rgb_png(1, 2, filtered, idat_data=bytes(compressed))
    checkpoint = tmp_path / "_UltimateMegaSuperLineFeedBruteForce.checkpoint.jsonl"
    progress_path = tmp_path / "_UltimateMegaSuperLineFeedBruteForce.progress.json"
    visual_path = tmp_path / "_UltimateMegaSuperLineFeedBruteForce.visual.json"
    _chunks, root_stream = idat_bruteforce._all_chunks_and_idat_stream(corrupt)
    checkpoint.write_text(
        json.dumps(
            {
                "source_hash": idat_bruteforce._stream_state_key(root_stream),
                "state_id": 1,
                "parent_id": 0,
                "operations": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    sent = False
    positive_progress_calls = 0
    captured_handler = {"handler": None}

    def progress(_stage, tested, _budget):
        nonlocal positive_progress_calls, sent
        if tested >= 1:
            positive_progress_calls += 1
        if (
            positive_progress_calls >= 2
            and captured_handler["handler"] is not None
            and not sent
        ):
            sent = True
            captured_handler["handler"](signal.SIGINT, None)

    original_signal = idat_bruteforce.signal.signal
    original_getsignal = idat_bruteforce.signal.getsignal

    def fake_getsignal(signum):
        if signum == signal.SIGINT:
            return original_getsignal(signum)
        return original_getsignal(signum)

    def fake_signal(signum, handler):
        if signum == signal.SIGINT:
            captured_handler["handler"] = handler
            return original_getsignal(signum)
        return original_signal(signum, handler)

    interrupted = False
    try:
        idat_bruteforce.signal.getsignal = fake_getsignal
        idat_bruteforce.signal.signal = fake_signal
        idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce(
            corrupt,
            start_offset=idat_bruteforce.first_idat_problem_stream_offset(corrupt),
            checkpoint_path=str(checkpoint),
            progress_path=str(progress_path),
            max_depth=2,
            max_offsets=16,
            budget=4,
            beam_width=1,
            progress=progress,
        )
    except KeyboardInterrupt:
        interrupted = True
    finally:
        idat_bruteforce.signal.getsignal = original_getsignal
        idat_bruteforce.signal.signal = original_signal

    assert interrupted is True
    assert progress_path.exists()
    assert visual_path.exists()
    record = json.loads(visual_path.read_text(encoding="utf-8"))
    assert record["preview_count"] > 0
    preview_dir = tmp_path / "Bruteforce_Previews" / "VisualCandidates"
    previews = list(preview_dir.glob("_VisualCandidate_*.png"))
    assert previews
    assert validate_png_structure(previews[0].read_bytes()).ok


def test_ultimate_linefeed_visual_reference_scores_local_png(tmp_path):
    clean = build_rgb_png(1, 1, b"\x00abc")
    analysis = idat.analyze_idat_stream(clean)
    candidate = idat_bruteforce.SuperMegaLinefeedCandidate(
        clean,
        (),
        analysis,
        analysis,
    )
    reference_path = tmp_path / "reference.png"
    reference_path.write_bytes(clean)

    reference_image, warning = idat_bruteforce._load_ultimate_reference_image(str(reference_path))
    scored = idat_bruteforce._attach_ultimate_visual_score(candidate, reference_image)
    missing_image, missing_warning = idat_bruteforce._load_ultimate_reference_image(
        str(tmp_path / "missing.png")
    )

    assert warning == ""
    assert scored.visual_score == 0.0
    assert scored.visual_score_kind == "exact_rgba"
    assert scored.matched_patch_count == 0
    assert missing_image is None
    assert "could not load visual reference" in missing_warning


def test_ultimate_linefeed_similar_reference_scores_different_sizes(tmp_path):
    reference_path = tmp_path / "reference.png"
    reference_path.write_bytes(visual_scope_png(96, 64, variant="scope"))
    reference_image, warning = idat_bruteforce._load_ultimate_reference_image(str(reference_path))

    similar = visual_scope_png(160, 96, variant="scope")
    unrelated = visual_scope_png(160, 96, variant="unrelated")
    similar_score = idat_bruteforce._ultimate_visual_score(
        similar,
        reference_image,
        reference_mode="similar",
    )
    unrelated_score = idat_bruteforce._ultimate_visual_score(
        unrelated,
        reference_image,
        reference_mode="similar",
    )
    exact_score = idat_bruteforce._ultimate_visual_score(
        similar,
        reference_image,
        reference_mode="exact",
    )

    assert warning == ""
    assert similar_score.kind == "similar_auto_patch"
    assert similar_score.matched_patch_count > 0
    assert similar_score.score is not None
    assert unrelated_score.score is not None
    assert similar_score.score < unrelated_score.score
    assert exact_score.kind == "exact_rgba"
    assert math.isinf(exact_score.score)


def test_ultimate_reference_regions_loads_clamped_schema(tmp_path):
    reference_path = tmp_path / "reference.png"
    source = visual_scope_png(96, 64, variant="scope")
    reference_path.write_bytes(source)
    reference_image, _warning = idat_bruteforce._load_ultimate_reference_image(str(reference_path))
    record = {
        "version": idat_bruteforce.ULTIMATE_LINEFEED_REFERENCE_REGION_VERSION,
        "candidate": {
            "size": [96, 64],
            "hash": idat_bruteforce._ultimate_image_hash_from_bytes(source),
        },
        "reference": {
            "size": [96, 64],
            "hash": idat_bruteforce._ultimate_image_hash_from_image(reference_image),
        },
        "regions": [
            {
                "candidate_region": [-1.0, 0.1, 0.7, 1.5],
                "reference_region": [0.0, 0.0, 1.0, 1.0],
                "weight": 2,
                "label": "scope",
                "match_mode": "search_candidate",
            }
        ],
    }
    regions_path = tmp_path / "_ULF.reference_regions.json"
    regions_path.write_text(json.dumps(record), encoding="utf-8")

    mapping, warning = idat_bruteforce.load_ultimate_reference_regions(
        str(regions_path),
        candidate_data=source,
        reference_image=reference_image,
    )

    assert warning == ""
    assert mapping is not None
    assert mapping.regions[0].candidate_region == (0.0, 0.1, 0.7, 1.0)
    assert mapping.regions[0].reference_region == (0.0, 0.0, 1.0, 1.0)
    assert mapping.regions[0].weight == 2.0
    assert mapping.regions[0].match_mode == "search_candidate"


def test_ultimate_linefeed_similar_manual_roi_scores_region_pairs(tmp_path):
    reference = visual_scope_png(96, 64, variant="scope")
    similar = visual_scope_png(160, 96, variant="scope")
    unrelated = visual_scope_png(160, 96, variant="unrelated")
    reference_path = tmp_path / "reference.png"
    reference_path.write_bytes(reference)
    reference_image, _warning = idat_bruteforce._load_ultimate_reference_image(str(reference_path))
    regions = idat_bruteforce.UltimateReferenceRegions(
        path=str(tmp_path / "_ULF.reference_regions.json"),
        regions=(
            idat_bruteforce.UltimateReferenceRegion(
                candidate_region=(0.0, 0.0, 1.0, 1.0),
                reference_region=(0.0, 0.0, 1.0, 1.0),
                weight=1.0,
                label="scope",
            ),
        ),
    )
    context = idat_bruteforce._ultimate_visual_reference(
        reference_image,
        reference_mode="similar",
        reference_regions=regions,
    )

    similar_score = idat_bruteforce._ultimate_visual_score(
        similar,
        context,
        reference_mode="similar",
    )
    unrelated_score = idat_bruteforce._ultimate_visual_score(
        unrelated,
        context,
        reference_mode="similar",
    )

    assert similar_score.kind == "similar_manual_roi"
    assert similar_score.matched_patch_count == 1
    assert similar_score.score is not None
    assert unrelated_score.score is not None
    assert similar_score.score < unrelated_score.score


def test_ultimate_linefeed_similar_manual_roi_searches_single_reference_region(tmp_path):
    from io import BytesIO
    from PIL import Image, ImageDraw

    def band_png(width, height, *, band_top, noise=False):
        image = Image.new("RGBA", (width, height), (0, 0, 0, 255))
        draw = ImageDraw.Draw(image)
        if noise:
            for index in range(0, max(width, height), 5):
                draw.line((0, index, width, height - index), fill=(180, 20, 20, 255), width=2)
        else:
            top = int(height * band_top)
            bottom = min(height - 1, top + max(4, height // 8))
            draw.rectangle((0, top, width - 1, bottom), fill=(230, 230, 0, 255))
            for x in range(0, width, max(1, width // 8)):
                draw.line((x, top, x, bottom), fill=(90, 90, 0, 255), width=1)
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return buffer.getvalue()

    reference = band_png(96, 64, band_top=0.78)
    similar = band_png(160, 96, band_top=0.24)
    unrelated = band_png(160, 96, band_top=0.24, noise=True)
    reference_path = tmp_path / "reference.png"
    reference_path.write_bytes(reference)
    reference_image, _warning = idat_bruteforce._load_ultimate_reference_image(str(reference_path))
    regions = idat_bruteforce.UltimateReferenceRegions(
        path=str(tmp_path / "_ULF.reference_regions.json"),
        regions=(
            idat_bruteforce.UltimateReferenceRegion(
                candidate_region=(0.0, 0.0, 1.0, 1.0),
                reference_region=(0.0, 0.72, 1.0, 0.95),
                weight=1.0,
                label="single reference band",
                match_mode="search_candidate",
            ),
        ),
    )
    context = idat_bruteforce._ultimate_visual_reference(
        reference_image,
        reference_mode="similar",
        reference_regions=regions,
    )

    similar_score = idat_bruteforce._ultimate_visual_score(
        similar,
        context,
        reference_mode="similar",
    )
    unrelated_score = idat_bruteforce._ultimate_visual_score(
        unrelated,
        context,
        reference_mode="similar",
    )

    assert similar_score.kind == "similar_manual_roi"
    assert similar_score.matched_patch_count == 1
    assert similar_score.score is not None
    assert unrelated_score.score is not None
    assert similar_score.score < unrelated_score.score


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
    progress_calls = []

    probe = idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce(
        corrupt,
        start_offset=start_offset,
        checkpoint_path=str(tmp_path / "_UltimateMegaSuperLineFeedBruteForce.checkpoint.jsonl"),
        max_depth=2,
        max_offsets=128,
        budget=300,
        beam_width=1,
        progress=lambda stage, tested, budget: progress_calls.append((stage, tested, budget)),
    )

    assert probe.tested_candidates == 300
    assert probe.budget_exhausted is True
    assert probe.best is not None
    assert probe.best.after.adler_status != "adler_match"
    assert ("UltimateMegaSuperLineFeedBruteForce", 100, 300) in progress_calls
    assert ("UltimateMegaSuperLineFeedBruteForce", 200, 300) in progress_calls
    assert ("UltimateMegaSuperLineFeedBruteForce", 300, 300) in progress_calls


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
            "Partial IDAT Adam7 blackfill",
            test_analyze_partial_idat_repairs_interlaced_stream_with_adam7_blackfill,
        ),
        (
            "Partial IDAT truncate_zlib_2 Adam7 fixture",
            test_rebuild_partial_idat_blackfill_repairs_truncated_adam7_fixture,
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
            "IDAT donor repair",
            test_rebuild_idat_from_donor_replaces_zero_scanline_idat,
        ),
        (
            "IDAT donor incompatible shape",
            test_rebuild_idat_from_donor_rejects_incompatible_shape,
        ),
        (
            "IDAT synthetic diagnostic",
            test_rebuild_synthetic_idat_builds_diagnostic_image_from_ihdr,
        ),
        (
            "Truncated IDAT normalization",
            test_normalize_truncated_idat_at_eof_rebuilds_analyzable_png,
        ),
        (
            "Zero-scanline placeholder",
            test_rebuild_zero_scanline_placeholder_handles_truncated_zlib_normalization,
        ),
        (
            "Partial IDAT tolerant salvage",
            test_rebuild_tolerant_idat_salvage_keeps_rows_after_bad_filters,
        ),
        (
            "IDAT marker-chain preserves chunks",
            test_idat_marker_chain_repair_preserves_valid_idat_chunks_byte_for_byte,
        ),
        (
            "IDAT marker-chain variants",
            test_idat_marker_chain_repair_generates_declared_payload_and_shorten_variants,
        ),
        (
            "IDAT marker-chain fixture ranking",
            test_idat_marker_chain_fixture_prefers_declared_payload_visual_salvage,
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
            "Ultimate live preview callback",
            test_ultimate_linefeed_preview_callback_only_receives_valid_complete_candidates,
        ),
        (
            "Ultimate progress checkpoint",
            test_ultimate_linefeed_progress_checkpoint_round_trips,
        ),
        (
            "Ultimate combination resume indices",
            test_ultimate_linefeed_combination_indices_resume_without_restarting,
        ),
        (
            "Ultimate progress resume",
            test_ultimate_linefeed_bruteforce_resumes_progress_checkpoint,
        ),
        (
            "Ultimate visual reference rank",
            test_ultimate_visual_gallery_structure_beats_reference_rank,
        ),
        (
            "Ultimate top reference rank",
            test_ultimate_top_candidates_structure_beats_reference_rank,
            test_ultimate_top_candidates_reference_rank_breaks_structural_ties,
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
