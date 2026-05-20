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
    chunk_at,
    complete_iend_tail,
    chunk_type_crc_matches,
    find_signature_offset,
    infer_png_dimensions,
    iter_chunks,
    read_chunks,
    repair_ihdr,
    repair_ihdr_from_idat,
    repair_ihdr_preserving_crc,
)


FIXTURE = ROOT / "schaik-javapng-samples" / "basn0g01.png"
REPAIR_FIXTURES = ROOT / "Png_Errors_handled_by_Chunklate_So_Far"


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


def test_chunk_at_reads_one_chunk_without_stream_context():
    data = FIXTURE.read_bytes()

    chunk = chunk_at(data, len(PNG_SIGNATURE))

    assert chunk is not None
    assert chunk.chunk_type == b"IHDR"
    assert chunk.length == 13
    assert chunk.crc_ok


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


def test_infer_png_dimensions_from_scanline_size():
    dimensions = infer_png_dimensions(
        decompressed_size=857768,
        bit_depth=8,
        color_type=2,
        current_width=493,
        current_height=65367,
    )

    assert dimensions == (477, 599)


def test_repair_ihdr_from_idat_rebuilds_strict_header():
    repaired = repair_ihdr_from_idat((REPAIR_FIXTURES / "IHDR_Messed_Up_Crc_Valid.png").read_bytes())

    assert repaired is not None
    first = next(iter_chunks(repaired))
    assert first.chunk_type == b"IHDR"
    assert first.data[:8] == b"\x00\x00\x00 \x00\x00\x00 "
    assert first.crc_ok


def test_repair_ihdr_preserving_crc_keeps_original_checksum():
    original = (REPAIR_FIXTURES / "IHDR-Wrong-Width-Bad-Crc.png").read_bytes()
    original_ihdr = chunk_at(original, len(PNG_SIGNATURE))

    repaired = repair_ihdr_preserving_crc(original)

    assert original_ihdr is not None
    assert repaired is not None
    first = next(iter_chunks(repaired))
    assert first.data[:8] == b"\x00\x00\x01\xdd\x00\x00\x02W"
    assert first.crc == original_ihdr.crc
    assert first.crc_ok


def test_repair_ihdr_uses_crc_preserving_strategy_first():
    original = (REPAIR_FIXTURES / "IHDR-Messed-Up-Bad-Crc.png").read_bytes()
    original_ihdr = chunk_at(original, len(PNG_SIGNATURE))

    repaired = repair_ihdr(original)

    assert original_ihdr is not None
    assert repaired is not None
    assert repaired.preserved_crc is True
    first = next(iter_chunks(repaired.data))
    assert first.data[:8] == b"\x00\x00\x01\x04\x00\x00\x00\xc3"
    assert first.data[10:11] == b"\x00"
    assert first.crc == original_ihdr.crc
    assert first.crc_ok


def test_repair_ihdr_falls_back_to_rebuild_when_stored_crc_is_not_original():
    original = (REPAIR_FIXTURES / "IHDR_Messed_Up_Crc_Valid.png").read_bytes()
    original_ihdr = chunk_at(original, len(PNG_SIGNATURE))

    repaired = repair_ihdr(original)

    assert original_ihdr is not None
    assert repaired is not None
    assert repaired.preserved_crc is False
    first = next(iter_chunks(repaired.data))
    assert first.data[:8] == b"\x00\x00\x00 \x00\x00\x00 "
    assert first.crc != original_ihdr.crc
    assert first.crc_ok


def main():
    checks = [
        ("Read valid PNG chunks from fixture", test_read_valid_png_chunks_from_fixture),
        ("Find PNG signature inside prefixed data", test_find_signature_inside_prefixed_data),
        ("Expose CRC mismatch without stopping parse", test_crc_mismatch_is_exposed_without_stopping_parse),
        ("Missing PNG signature raises PngFormatError", test_missing_signature_raises_format_error),
        ("Read one chunk at an explicit offset", test_chunk_at_reads_one_chunk_without_stream_context),
        ("Find original chunk name from CRC", test_chunk_type_crc_matches_finds_original_name),
        ("Append complete IEND chunk", test_complete_iend_tail_appends_full_iend_chunk),
        ("Reuse existing IEND suffix", test_complete_iend_tail_reuses_existing_iend_suffix),
        ("Infer dimensions from scanline size", test_infer_png_dimensions_from_scanline_size),
        ("Rebuild IHDR from IDAT", test_repair_ihdr_from_idat_rebuilds_strict_header),
        ("Repair IHDR while preserving stored CRC", test_repair_ihdr_preserving_crc_keeps_original_checksum),
        ("Prefer CRC-preserving IHDR repair", test_repair_ihdr_uses_crc_preserving_strategy_first),
        (
            "Fallback to rebuilt IHDR when stored CRC is not original",
            test_repair_ihdr_falls_back_to_rebuild_when_stored_crc_is_not_original,
        ),
    ]

    print("Running PNG parser tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"png parser tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
