#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate.png import (
    IEND_CHUNK,
    PNG_SIGNATURE,
    PngFormatError,
    complete_iend_tail,
    chunk_type_crc_matches,
    find_signature_offset,
    iter_chunks,
    read_chunks,
)


FIXTURE = ROOT / "schaik-javapng-samples" / "basn0g01.png"


def test_read_valid_png_chunks_from_fixture():
    chunks = read_chunks(FIXTURE)

    assert chunks[0].chunk_type == b"IHDR"
    assert chunks[0].length == 13
    assert chunks[-1].chunk_type == b"IEND"
    assert all(chunk.crc_ok for chunk in chunks)


def test_find_signature_inside_prefixed_data():
    data = b"junk" + PNG_SIGNATURE + b"tail"

    assert find_signature_offset(data) == 4


def test_crc_mismatch_is_exposed_without_stopping_parse():
    data = bytearray(FIXTURE.read_bytes())
    chunks = list(iter_chunks(data))
    first_data_offset = chunks[0].offset + 8
    data[first_data_offset] ^= 0x01

    reparsed = list(iter_chunks(bytes(data)))

    assert reparsed[0].crc_ok is False


def test_missing_signature_raises_format_error():
    try:
        list(iter_chunks(b"not a png"))
    except PngFormatError:
        return

    raise AssertionError("Expected PngFormatError")


def test_chunk_type_crc_matches_finds_original_name():
    chunk_data = b"payload"
    stored_crc = 0x96166E4F

    matches = chunk_type_crc_matches(chunk_data, stored_crc, [b"IDAT", b"tEXt", b"pHYs"])

    assert matches == [b"IDAT"]


def test_complete_iend_tail_appends_full_iend_chunk():
    data = b"prefix"

    repaired = complete_iend_tail(data, len(data))

    assert repaired == b"prefix" + IEND_CHUNK


def test_complete_iend_tail_reuses_existing_iend_suffix():
    data = b"prefix" + IEND_CHUNK[-1:]

    repaired = complete_iend_tail(data, len(b"prefix"))

    assert repaired == b"prefix" + IEND_CHUNK


def main():
    checks = [
        ("Read valid PNG chunks from fixture", test_read_valid_png_chunks_from_fixture),
        ("Find PNG signature inside prefixed data", test_find_signature_inside_prefixed_data),
        ("Expose CRC mismatch without stopping parse", test_crc_mismatch_is_exposed_without_stopping_parse),
        ("Missing PNG signature raises PngFormatError", test_missing_signature_raises_format_error),
        ("Find original chunk name from CRC", test_chunk_type_crc_matches_finds_original_name),
        ("Append complete IEND chunk", test_complete_iend_tail_appends_full_iend_chunk),
        ("Reuse existing IEND suffix", test_complete_iend_tail_reuses_existing_iend_suffix),
    ]

    print("Running PNG parser tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"png parser tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
