#!/usr/bin/env python3
import binascii
import struct
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import palette


def test_palette_values_to_bytes_skips_empty_legacy_entries():
    assert palette.palette_values_to_bytes(["empty", 0, 0x112233]) == bytes.fromhex("000000112233")


def test_build_plte_chunk_adds_length_type_and_crc():
    data = bytes.fromhex("000000ffffff")
    chunk = palette.build_plte_chunk(data)

    assert chunk[:4] == len(data).to_bytes(4, "big")
    assert chunk[4:8] == b"PLTE"
    assert chunk[8:-4] == data
    assert chunk[-4:] == struct.pack("!I", binascii.crc32(b"PLTE" + data))


def test_build_palette_png_combines_before_palette_after():
    png = palette.build_palette_png(
        bytes.fromhex("aaaa"),
        [0],
        bytes.fromhex("bbbb"),
    )

    assert png.startswith(bytes.fromhex("aaaa00000003504c5445000000"))
    assert png.endswith(bytes.fromhex("bbbb"))


def test_set_palette_value_preserves_empty_sentinel():
    values = ["empty", "empty"]

    palette.set_palette_value(values, 0, "123")
    palette.set_palette_value(values, 1, "-1")

    assert values == ["123", "empty"]


def test_initial_manual_palette_png_adds_one_black_palette_entry():
    png = palette.initial_manual_palette_png(
        before=bytes.fromhex("aaaa"),
        chunk_name=b"PLTE",
        after=bytes.fromhex("bbbb"),
    )

    assert png.startswith(bytes.fromhex("aaaa00000003504c5445000000"))
    assert png.endswith(bytes.fromhex("bbbb"))


def test_legacy_palette_count_preserves_256_based_counting():
    assert palette.legacy_palette_count(["empty", 0, 1]) == 255


def main():
    checks = [
        ("Palette bytes skip empty entries", test_palette_values_to_bytes_skips_empty_legacy_entries),
        ("PLTE chunk builder", test_build_plte_chunk_adds_length_type_and_crc),
        ("Palette PNG builder", test_build_palette_png_combines_before_palette_after),
        ("Set palette value", test_set_palette_value_preserves_empty_sentinel),
        ("Initial manual palette PNG", test_initial_manual_palette_png_adds_one_black_palette_entry),
        ("Legacy palette count", test_legacy_palette_count_preserves_256_based_counting),
    ]

    print("Running palette core tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"palette core tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
