#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate.png import PNG_SIGNATURE, PngFormatError, find_signature_offset, iter_chunks, read_chunks


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


def main():
    checks = [
        ("Read valid PNG chunks from fixture", test_read_valid_png_chunks_from_fixture),
        ("Find PNG signature inside prefixed data", test_find_signature_inside_prefixed_data),
        ("Expose CRC mismatch without stopping parse", test_crc_mismatch_is_exposed_without_stopping_parse),
        ("Missing PNG signature raises PngFormatError", test_missing_signature_raises_format_error),
    ]

    print("Running PNG parser tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"png parser tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
