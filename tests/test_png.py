#!/usr/bin/env python3
import sys
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate.png import (
    IEND_CHUNK,
    PNG_SIGNATURE,
    PngFormatError,
    build_png_chunk,
    chunk_at,
    complete_iend_tail,
    chunk_type_crc_matches,
    find_signature_offset,
    infer_png_dimensions,
    iter_chunks,
    read_chunks,
    repair_color_profile_chunks,
    repair_empty_plte,
    repair_ihdr,
    repair_ihdr_from_idat,
    repair_ihdr_preserving_crc,
    repair_known_chunk_type_case,
    repair_missing_chunk_data_byte,
    repair_unknown_private_critical_chunks,
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


def test_infer_png_dimensions_prefers_largest_balanced_candidate():
    dimensions = infer_png_dimensions(
        decompressed_size=1056,
        bit_depth=8,
        color_type=3,
        current_width=0xFFFFFFE0,
        current_height=0xFFFFFFE0,
    )

    assert dimensions == (32, 32)


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


def test_repair_color_profile_chunks_removes_zero_gama():
    original = (REPAIR_FIXTURES / "gama_zero.png").read_bytes()

    repaired = repair_color_profile_chunks(original)

    assert repaired is not None
    chunks = list(iter_chunks(repaired.data))
    assert b"gAMA" not in {chunk.chunk_type for chunk in chunks}
    assert chunks[-1].chunk_type == b"IEND"
    assert all(chunk.crc_ok for chunk in chunks)


def test_repair_color_profile_chunks_keeps_iccp_without_explicit_signal():
    original = (REPAIR_FIXTURES / "IncorrectSrgbProfile.png").read_bytes()

    repaired = repair_color_profile_chunks(original)

    assert repaired is None


def test_repair_color_profile_chunks_can_remove_known_bad_srgb_iccp_when_requested():
    original = (REPAIR_FIXTURES / "IncorrectSrgbProfile.png").read_bytes()

    repaired = repair_color_profile_chunks(original, remove_known_bad_srgb_iccp=True)

    assert repaired is not None
    chunk_types = [chunk.chunk_type for chunk in iter_chunks(repaired.data)]
    assert b"iCCP" not in chunk_types
    assert b"gAMA" in chunk_types
    assert b"cHRM" in chunk_types
    assert chunk_types[-1] == b"IEND"


def test_repair_empty_plte_removes_optional_truecolor_palette():
    original = (REPAIR_FIXTURES / "PLTE_Empty_Bad_Crc.png").read_bytes()

    repaired = repair_empty_plte(original)

    assert repaired is not None
    chunks = list(iter_chunks(repaired.data))
    assert b"PLTE" not in {chunk.chunk_type for chunk in chunks}
    assert chunks[-1].chunk_type == b"IEND"
    assert all(chunk.crc_ok for chunk in chunks)


def test_repair_empty_plte_rebuilds_indexed_palette():
    original = (REPAIR_FIXTURES / "PLTE_Empty_Good_Crc.png").read_bytes()

    repaired = repair_empty_plte(original)

    assert repaired is not None
    chunks = list(iter_chunks(repaired.data))
    plte = next(chunk for chunk in chunks if chunk.chunk_type == b"PLTE")
    assert plte.length == 768
    assert plte.data[:3] == b"\x00\x00\x00"
    assert plte.data[-3:] == b"\xff\xff\xff"
    assert plte.crc_ok
    assert chunks[-1].chunk_type == b"IEND"


def test_repair_missing_chunk_data_byte_uses_shifted_crc():
    original = (REPAIR_FIXTURES / "Good-Chunk-lenght-Missing-Bit.png").read_bytes()

    repaired = repair_missing_chunk_data_byte(original)

    assert repaired is not None
    assert repaired.chunk_name == "PLTE"
    assert repaired.inserted_offset in (99, 100)
    assert repaired.inserted_value == 0xED
    chunks = list(iter_chunks(repaired.data))
    assert [chunk.chunk_type for chunk in chunks] == [b"IHDR", b"gAMA", b"PLTE", b"IDAT", b"IEND"]
    assert all(chunk.crc_ok for chunk in chunks)


def test_repair_known_chunk_type_case_rebuilds_crc():
    original = (REPAIR_FIXTURES / "chunk_private_critical.png").read_bytes()

    repaired = repair_known_chunk_type_case(original, [b"gAMA"])

    assert repaired is not None
    assert repaired.original_name == "GaMA"
    assert repaired.repaired_name == "gAMA"
    chunks = list(iter_chunks(repaired.data))
    assert [chunk.chunk_type for chunk in chunks] == [b"IHDR", b"gAMA", b"PLTE", b"IDAT", b"IEND"]
    assert all(chunk.crc_ok for chunk in chunks)


def minimal_gray_png_with_chunk(chunk_type, chunk_data):
    ihdr = build_png_chunk(b"IHDR", b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x00\x00\x00\x00")
    idat = build_png_chunk(b"IDAT", zlib.compress(b"\x00\x00"))
    return PNG_SIGNATURE + ihdr + build_png_chunk(chunk_type, chunk_data) + idat + IEND_CHUNK


def test_repair_known_chunk_type_case_requires_coherent_data():
    broken = minimal_gray_png_with_chunk(b"GaMA", b"\x00\x00\x00\x00")

    repaired = repair_known_chunk_type_case(broken, [b"gAMA"])

    assert repaired is None


def test_repair_known_chunk_type_case_accepts_other_coherent_chunks():
    broken = minimal_gray_png_with_chunk(b"SrGB", b"\x00")

    repaired = repair_known_chunk_type_case(broken, [b"sRGB"])

    assert repaired is not None
    assert repaired.original_name == "SrGB"
    assert repaired.repaired_name == "sRGB"
    chunks = list(iter_chunks(repaired.data))
    assert [chunk.chunk_type for chunk in chunks] == [b"IHDR", b"sRGB", b"IDAT", b"IEND"]
    assert all(chunk.crc_ok for chunk in chunks)


def test_repair_known_chunk_type_case_ignores_true_unknown_private_critical_chunk():
    original = (REPAIR_FIXTURES / "Unhandled-Critical-Chunk.png").read_bytes()

    repaired = repair_known_chunk_type_case(original, [b"gAMA"])

    assert repaired is None


def test_repair_unknown_private_critical_chunks_removes_unsafe_chunk():
    original = (REPAIR_FIXTURES / "Unhandled-Critical-Chunk.png").read_bytes()

    repaired = repair_unknown_private_critical_chunks(original, [b"IHDR", b"gAMA", b"PLTE", b"IDAT", b"IEND"])

    assert repaired is not None
    assert repaired.removed_chunks == ("QpZZ",)
    chunks = list(iter_chunks(repaired.data))
    assert [chunk.chunk_type for chunk in chunks] == [b"IHDR", b"PLTE", b"IDAT", b"IEND"]
    assert all(chunk.crc_ok for chunk in chunks)


def test_repair_unknown_private_critical_chunks_keeps_known_case_candidate():
    original = (REPAIR_FIXTURES / "chunk_private_critical.png").read_bytes()

    repaired = repair_unknown_private_critical_chunks(original, [b"gAMA"])

    assert repaired is None


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
        ("Prefer largest balanced inferred dimensions", test_infer_png_dimensions_prefers_largest_balanced_candidate),
        ("Rebuild IHDR from IDAT", test_repair_ihdr_from_idat_rebuilds_strict_header),
        ("Repair IHDR while preserving stored CRC", test_repair_ihdr_preserving_crc_keeps_original_checksum),
        ("Prefer CRC-preserving IHDR repair", test_repair_ihdr_uses_crc_preserving_strategy_first),
        (
            "Fallback to rebuilt IHDR when stored CRC is not original",
            test_repair_ihdr_falls_back_to_rebuild_when_stored_crc_is_not_original,
        ),
        ("Remove zero gAMA chunk", test_repair_color_profile_chunks_removes_zero_gama),
        (
            "Keep iCCP profile without explicit signal",
            test_repair_color_profile_chunks_keeps_iccp_without_explicit_signal,
        ),
        (
            "Remove known bad sRGB iCCP profile when requested",
            test_repair_color_profile_chunks_can_remove_known_bad_srgb_iccp_when_requested,
        ),
        ("Remove empty optional truecolor PLTE", test_repair_empty_plte_removes_optional_truecolor_palette),
        ("Rebuild empty indexed PLTE", test_repair_empty_plte_rebuilds_indexed_palette),
        ("Repair missing data byte using shifted CRC", test_repair_missing_chunk_data_byte_uses_shifted_crc),
        ("Repair known chunk type case and CRC", test_repair_known_chunk_type_case_rebuilds_crc),
        ("Reject known chunk type case with incoherent data", test_repair_known_chunk_type_case_requires_coherent_data),
        ("Repair coherent sRGB chunk type case", test_repair_known_chunk_type_case_accepts_other_coherent_chunks),
        (
            "Ignore true unknown private critical chunk",
            test_repair_known_chunk_type_case_ignores_true_unknown_private_critical_chunk,
        ),
        (
            "Remove unknown private critical unsafe-to-copy chunk",
            test_repair_unknown_private_critical_chunks_removes_unsafe_chunk,
        ),
        (
            "Keep known chunk type case candidate during unknown critical removal",
            test_repair_unknown_private_critical_chunks_keeps_known_case_candidate,
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
