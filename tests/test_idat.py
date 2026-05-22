#!/usr/bin/env python3
import sys
import struct
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import idat
from chunklate.png import IEND_CHUNK, PNG_SIGNATURE, build_png_chunk, iter_chunks, validate_png_structure


def build_rgb_png(width, height, filtered_scanlines, *, idat_data=None, interlace=0):
    ihdr = struct.pack("!IIBBBBB", width, height, 8, 2, 0, 0, interlace)
    if idat_data is None:
        idat_data = zlib.compress(filtered_scanlines)
    return (
        PNG_SIGNATURE
        + build_png_chunk(b"IHDR", ihdr)
        + build_png_chunk(b"IDAT", idat_data)
        + IEND_CHUNK
    )


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


def test_analyze_partial_idat_keeps_good_scanlines_until_truncated_stream_error():
    filtered = b"".join(b"\x00" + bytes((row, row, row)) for row in range(10))
    compressed = zlib.compress(filtered)
    truncated = None
    for cut in range(2, len(compressed)):
        candidate = build_rgb_png(1, 10, filtered, idat_data=compressed[:cut])
        analysis = idat.analyze_partial_idat(candidate)
        if analysis.usable_scanlines > 0 and analysis.decompression_error:
            truncated = analysis
            break

    assert truncated is not None
    assert truncated.supported is True
    assert truncated.complete is False
    assert truncated.partial is True
    assert truncated.usable_scanlines >= 1
    assert truncated.recovered_scanlines.startswith(filtered[:4])
    assert truncated.decompression_error == "incomplete zlib stream"


def test_analyze_partial_idat_rejects_unsupported_interlace_before_repair_logic():
    filtered = b"\x00abc"
    analysis = idat.analyze_partial_idat(build_rgb_png(1, 1, filtered, interlace=1))

    assert analysis.supported is False
    assert analysis.complete is False
    assert analysis.reason == "interlaced PNG is not supported"


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


def test_rebuild_partial_idat_blackfill_ignores_complete_or_unusable_streams():
    complete = build_rgb_png(1, 1, b"\x00abc")
    invalid = build_rgb_png(1, 1, b"\x00abc", idat_data=b"bad")

    assert idat.rebuild_partial_idat_blackfill(complete) is None
    assert idat.rebuild_partial_idat_blackfill(invalid) is None


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
            "Partial IDAT truncated stream",
            test_analyze_partial_idat_keeps_good_scanlines_until_truncated_stream_error,
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
            "Partial IDAT blackfill ignored cases",
            test_rebuild_partial_idat_blackfill_ignores_complete_or_unusable_streams,
        ),
    ]

    print("Running IDAT tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"IDAT tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
