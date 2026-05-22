#!/usr/bin/env python3
import sys
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import idat


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


def main():
    checks = [
        ("Dummy scanline", test_dummy_scanline_preserves_legacy_sample_width),
        ("Zlib header", test_idat_zlib_header_skips_interlaced_streams_like_legacy_todo),
        ("Zlib header info", test_zlib_header_info_reads_window_and_legacy_compression_level),
        ("Dummy probe", test_build_dummy_idat_probe_decompresses_debug_stream_and_idat_stream),
        ("Invalid stream", test_build_dummy_idat_probe_reports_invalid_stream_without_raising),
    ]

    print("Running IDAT tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"IDAT tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
