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
    detect_png_signature_recovery,
    find_signature_offset,
    infer_png_dimensions,
    iter_chunks,
    is_complete_png_with_valid_crc,
    known_bad_srgb_profile_warning,
    legacy_crc_decision,
    legacy_chunk_window,
    legacy_length_decision,
    legacy_length_status,
    read_chunks,
    repair_color_profile_chunks,
    repair_empty_plte,
    repair_ihdr,
    repair_ihdr_from_idat,
    repair_ihdr_preserving_crc,
    repair_known_chunk_type_case,
    repair_missing_ihdr_from_idat,
    repair_missing_chunk_data_byte,
    repair_unknown_private_critical_chunks,
    validate_png_structure,
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


def test_detect_png_signature_recovery_accepts_signature_at_start():
    recovery = detect_png_signature_recovery(PNG_SIGNATURE + b"tail")

    assert recovery.action == "found_at_start"
    assert recovery.signature_offset == 0
    assert recovery.signature_hex_offset == 0
    assert recovery.fixed_data is None


def test_detect_png_signature_recovery_cuts_prefixed_data():
    recovery = detect_png_signature_recovery(b"junk" + PNG_SIGNATURE + b"tail")

    assert recovery.action == "cut_at_signature"
    assert recovery.signature_offset == 4
    assert recovery.signature_hex_offset == 8
    assert recovery.fixed_data == PNG_SIGNATURE + b"tail"


def test_detect_png_signature_recovery_classifies_linefeed_candidates():
    minor = bytes.fromhex("89504e470a1a0a0000000d4948445200")
    major = bytes.fromhex("89504e470a1a0a000000049484452000")

    minor_recovery = detect_png_signature_recovery(b"xx" + minor)
    major_recovery = detect_png_signature_recovery(b"xx" + major)

    assert minor_recovery.action == "linefeed_signature_candidate"
    assert minor_recovery.signature_offset == 2
    assert minor_recovery.linefeed_pattern == "minor_linefeed_corruption"
    assert major_recovery.action == "linefeed_signature_candidate"
    assert major_recovery.signature_offset == 2
    assert major_recovery.linefeed_pattern == "major_linefeed_corruption"


def test_detect_png_signature_recovery_falls_back_to_deep_search():
    recovery = detect_png_signature_recovery(b"not a png")

    assert recovery.action == "search_deeper"
    assert recovery.signature_offset is None
    assert recovery.fixed_data is None


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


def test_legacy_chunk_window_matches_chunkbychunk_offsets():
    data = FIXTURE.read_bytes()
    window = legacy_chunk_window(data, len(PNG_SIGNATURE) * 2)

    assert window.raw_length == "0000000d"
    assert window.raw_type == "49484452"
    assert window.raw_crc == "5b014759"
    assert window.raw_next_chunk == "67414d41"
    assert window.chunk_type == b"IHDR"
    assert window.next_chunk_type == b"gAMA"
    assert window.length_offset_hex == "0x8"
    assert window.length_offset_byte == 8
    assert window.length_offset_index == 16
    assert window.type_offset_hex == "0xc"
    assert window.type_offset_byte == 12
    assert window.type_offset_index == 24
    assert window.data_offset_hex == "0x10"
    assert window.data_offset_byte == 16
    assert window.data_offset_index == 32
    assert window.crc_offset_hex == "0x1d"
    assert window.crc_offset_byte == 29
    assert window.crc_offset_index == 58


def test_legacy_chunk_window_falls_back_to_slices_for_incomplete_chunk():
    data = PNG_SIGNATURE + b"\x00\x00\x00\x04IDATab"
    window = legacy_chunk_window(data, len(PNG_SIGNATURE) * 2)

    assert window.raw_length == "00000004"
    assert window.raw_type == "49444154"
    assert window.raw_data == "6162"
    assert window.raw_crc == ""
    assert window.chunk_type == b"IDAT"


def test_legacy_length_status_reports_declared_next_chunk():
    status = legacy_length_status(FIXTURE.read_bytes(), len(PNG_SIGNATURE) * 2)

    assert status.declared_length == 13
    assert status.has_next_chunk is True
    assert status.next_chunk_type == b"gAMA"


def test_legacy_length_status_reports_missing_next_chunk():
    data = PNG_SIGNATURE + b"\x00\x00\x00\x04IDATab"
    status = legacy_length_status(data, len(PNG_SIGNATURE) * 2)

    assert status.declared_length == 4
    assert status.has_next_chunk is False
    assert status.next_chunk_type == b""


def test_legacy_length_decision_reports_found_next_chunk():
    decision = legacy_length_decision(
        FIXTURE.read_bytes(),
        len(PNG_SIGNATURE) * 2,
        previous_chunk=b"IHDR",
        idat_average_length=0,
    )

    assert decision.declared_length == 13
    assert decision.has_next_chunk is True
    assert decision.next_chunk_type == b"gAMA"
    assert decision.checkpoint_error is False
    assert decision.checkpoint_info == "-Found NextChunk"


def test_legacy_length_decision_reports_no_next_chunk_and_idat_delta():
    data = PNG_SIGNATURE + b"\x00\x00\x00\x04IDATab"
    decision = legacy_length_decision(
        data,
        len(PNG_SIGNATURE) * 2,
        previous_chunk=b"IDAT",
        idat_average_length=12,
    )

    assert decision.declared_length == 4
    assert decision.has_next_chunk is False
    assert decision.next_chunk_type == b""
    assert decision.idat_length_differs is True
    assert decision.checkpoint_error is True
    assert decision.checkpoint_info == "-No NextChunk"


def test_legacy_crc_decision_matches_checksum_wrapper_values():
    stored_crc = zlib.crc32(b"IDAT" + b"abc").to_bytes(4, "big").hex()
    valid = legacy_crc_decision("49444154", "616263", stored_crc)
    invalid = legacy_crc_decision("49444154", "616263", "00000000")

    assert valid.chunk_type == b"IDAT"
    assert valid.chunk_data == b"abc"
    assert valid.ok is True
    assert valid.stored_crc_hex == valid.computed_crc_hex
    assert invalid.ok is False
    assert invalid.normalized_computed_crc.startswith("0x")
    assert len(invalid.normalized_computed_crc_no_prefix) == 8


def test_chunk_type_crc_matches_finds_original_name():
    chunk_data = b"payload"
    stored_crc = 0x96166E4F

    matches = chunk_type_crc_matches(chunk_data, stored_crc, [b"IDAT", b"tEXt", b"pHYs"])

    assert matches == [b"IDAT"]


def test_validate_png_structure_accepts_valid_fixture():
    validation = validate_png_structure(FIXTURE.read_bytes())

    assert validation.ok
    assert validation.errors == ()


def test_validate_png_structure_rejects_prefixed_png_output():
    validation = validate_png_structure(b"junk" + FIXTURE.read_bytes())

    assert not validation.ok
    assert validation.errors == ("PNG signature is not at offset 0",)


def test_validate_png_structure_rejects_crc_valid_bad_idat_stream():
    ihdr = build_png_chunk(b"IHDR", b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x00\x00\x00\x00")
    idat = build_png_chunk(b"IDAT", b"not-zlib-data")
    data = PNG_SIGNATURE + ihdr + idat + IEND_CHUNK

    assert is_complete_png_with_valid_crc(data)

    validation = validate_png_structure(data)

    assert not validation.ok
    assert "IDAT zlib stream is invalid" in validation.errors


def test_validate_png_structure_rejects_invalid_scanline_filter():
    ihdr = build_png_chunk(b"IHDR", b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x00\x00\x00\x00")
    idat = build_png_chunk(b"IDAT", zlib.compress(b"\x05\x00"))
    data = PNG_SIGNATURE + ihdr + idat + IEND_CHUNK

    validation = validate_png_structure(data)

    assert not validation.ok
    assert "IDAT scanline filter type is invalid" in validation.errors


def test_validate_png_structure_rejects_unknown_critical_chunk():
    ihdr = build_png_chunk(b"IHDR", b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x00\x00\x00\x00")
    idat = build_png_chunk(b"IDAT", zlib.compress(b"\x00\x00"))
    data = PNG_SIGNATURE + ihdr + build_png_chunk(b"QpZZ", b"") + idat + IEND_CHUNK

    validation = validate_png_structure(data)

    assert not validation.ok
    assert "Unknown critical chunk QpZZ" in validation.errors


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
    assert validate_png_structure(repaired).ok
    first = next(iter_chunks(repaired))
    assert first.chunk_type == b"IHDR"
    assert first.data[8:10] == b"\x08\x03"
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
    assert validate_png_structure(repaired.data).ok
    assert first.data[8:10] == b"\x08\x03"
    assert first.crc != original_ihdr.crc
    assert first.crc_ok


def test_repair_ihdr_rebuilds_indexed_header_when_plte_and_idat_disagree():
    bad_ihdr = build_png_chunk(
        b"IHDR",
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x01\x03\x00\x00\x00",
    )
    palette = bytes(range(256)) * 3
    scanlines = b"".join(b"\x00" + bytes([row]) * 32 for row in range(32))
    original = (
        PNG_SIGNATURE
        + bad_ihdr
        + build_png_chunk(b"PLTE", palette)
        + build_png_chunk(b"IDAT", zlib.compress(scanlines))
        + IEND_CHUNK
    )

    repaired = repair_ihdr_from_idat(original)
    described = repair_ihdr(original)

    assert repaired is not None
    assert described is not None
    assert described.width == 32
    assert described.height == 32
    assert described.bit_depth == 8
    assert described.color_type == 3
    assert described.strict_candidate_count > 1
    assert described.selection_score is not None
    assert validate_png_structure(repaired).ok
    first = next(iter_chunks(repaired))
    width = int.from_bytes(first.data[:4], "big")
    height = int.from_bytes(first.data[4:8], "big")
    assert (width, height) == (32, 32)
    assert first.data[8:10] == b"\x08\x03"
    assert first.crc_ok


def test_repair_missing_ihdr_from_idat_inserts_strict_indexed_header():
    original = (REPAIR_FIXTURES / "No_Png_Header_Missing_Chunk_Corrupted.png").read_bytes()
    with_signature = PNG_SIGNATURE + b"\x00" + original

    repaired = repair_missing_ihdr_from_idat(with_signature)

    assert repaired is not None
    assert repaired.width == 32
    assert repaired.height == 32
    assert repaired.bit_depth == 8
    assert repaired.color_type == 3
    assert repaired.strict_candidate_count > 1
    assert repaired.selection_score is not None
    assert validate_png_structure(repaired.data).ok
    first = next(iter_chunks(repaired.data))
    assert first.chunk_type == b"IHDR"
    assert first.data[:8] == b"\x00\x00\x00 \x00\x00\x00 "
    assert first.data[8:10] == b"\x08\x03"
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


def test_known_bad_srgb_profile_warning_detects_photoshop_iccp_profile():
    profile = b"\x00\x00\x00\x00acsp" + b"\x00" * 12 + b"IEC sRGB profile"
    iccp_data = b"Photoshop ICC profile\x00\x00" + zlib.compress(profile)
    png = minimal_gray_png_with_chunk(b"iCCP", iccp_data)

    assert known_bad_srgb_profile_warning(png) == (
        "libpng warning: iCCP: known incorrect sRGB profile"
    )


def test_known_bad_srgb_profile_warning_ignores_invalid_png():
    assert known_bad_srgb_profile_warning(b"not a png") == ""


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
        (
            "Detect PNG signature recovery accepts signature at start",
            test_detect_png_signature_recovery_accepts_signature_at_start,
        ),
        (
            "Detect PNG signature recovery cuts prefixed data",
            test_detect_png_signature_recovery_cuts_prefixed_data,
        ),
        (
            "Detect PNG signature recovery classifies linefeed candidates",
            test_detect_png_signature_recovery_classifies_linefeed_candidates,
        ),
        (
            "Detect PNG signature recovery falls back to deep search",
            test_detect_png_signature_recovery_falls_back_to_deep_search,
        ),
        ("Expose CRC mismatch without stopping parse", test_crc_mismatch_is_exposed_without_stopping_parse),
        ("Missing PNG signature raises PngFormatError", test_missing_signature_raises_format_error),
        ("Read one chunk at an explicit offset", test_chunk_at_reads_one_chunk_without_stream_context),
        ("Legacy chunk window matches ChunkbyChunk offsets", test_legacy_chunk_window_matches_chunkbychunk_offsets),
        (
            "Legacy chunk window falls back to slices for incomplete chunk",
            test_legacy_chunk_window_falls_back_to_slices_for_incomplete_chunk,
        ),
        ("Legacy length status reports declared next chunk", test_legacy_length_status_reports_declared_next_chunk),
        ("Legacy length status reports missing next chunk", test_legacy_length_status_reports_missing_next_chunk),
        ("Legacy length decision reports found next chunk", test_legacy_length_decision_reports_found_next_chunk),
        (
            "Legacy length decision reports missing next chunk and IDAT delta",
            test_legacy_length_decision_reports_no_next_chunk_and_idat_delta,
        ),
        ("Legacy CRC decision matches checksum wrapper values", test_legacy_crc_decision_matches_checksum_wrapper_values),
        ("Find original chunk name from CRC", test_chunk_type_crc_matches_finds_original_name),
        ("Validate PNG structure accepts valid fixture", test_validate_png_structure_accepts_valid_fixture),
        ("Validate PNG structure rejects prefixed PNG output", test_validate_png_structure_rejects_prefixed_png_output),
        (
            "Validate PNG structure rejects CRC-valid bad IDAT stream",
            test_validate_png_structure_rejects_crc_valid_bad_idat_stream,
        ),
        (
            "Validate PNG structure rejects invalid scanline filter",
            test_validate_png_structure_rejects_invalid_scanline_filter,
        ),
        (
            "Validate PNG structure rejects unknown critical chunk",
            test_validate_png_structure_rejects_unknown_critical_chunk,
        ),
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
        (
            "Rebuild indexed IHDR when PLTE and IDAT disagree",
            test_repair_ihdr_rebuilds_indexed_header_when_plte_and_idat_disagree,
        ),
        (
            "Insert strict indexed IHDR when missing",
            test_repair_missing_ihdr_from_idat_inserts_strict_indexed_header,
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
            "Detect known bad sRGB iCCP warning",
            test_known_bad_srgb_profile_warning_detects_photoshop_iccp_profile,
        ),
        (
            "Ignore invalid PNG for known bad sRGB warning",
            test_known_bad_srgb_profile_warning_ignores_invalid_png,
        ),
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
