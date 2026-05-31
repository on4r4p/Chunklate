#!/usr/bin/env python3
import struct
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
    extract_png_segment,
    find_signature_offset,
    infer_png_dimensions,
    iter_chunks,
    is_complete_png_with_valid_crc,
    known_bad_srgb_profile_warning,
    legacy_crc_checkpoint_args,
    legacy_crc_debug_lines,
    legacy_crc_decision,
    legacy_crc_monkey_lines,
    legacy_find_magic_checkpoint_args,
    legacy_chunk_window,
    legacy_length_checkpoint_args,
    legacy_length_decision,
    legacy_length_status,
    read_chunks,
    repair_bkgd_length,
    repair_chrm_length,
    repair_color_profile_chunks,
    repair_duplicate_singleton_chunks,
    repair_empty_plte,
    repair_gama_length,
    repair_gifg_length,
    repair_hist_out_of_place,
    repair_hist_length,
    repair_ihdr,
    repair_ihdr_from_idat,
    repair_ihdr_preserving_crc,
    repair_iend_length,
    repair_indexed_plte,
    repair_itxt_compression_flag,
    repair_itxt_keyword_length,
    repair_itxt_compression_method,
    repair_known_chunk_type_case,
    repair_linefeed_conversion,
    repair_missing_ihdr_from_idat,
    repair_missing_chunk_data_byte,
    repair_offs_length,
    repair_phys_length,
    repair_overlong_chunk_length_to_next_header,
    repair_sbit_length,
    repair_srgb_length,
    repair_ster_length,
    repair_time_length,
    repair_trns_length,
    repair_unknown_private_critical_chunks,
    SRGB_CHRM_PAYLOAD,
    validate_png_structure,
)


FIXTURE = ROOT / "schaik-javapng-samples" / "basn0g01.png"
REPAIR_FIXTURES = ROOT / "Png_Errors_handled_by_Chunklate_So_Far"
BROKEN_FIXTURES = ROOT / "schaik-javapng-samples" / "brokenjavapngsuite"


def repair_fixture(name: str) -> Path:
    for directory in (REPAIR_FIXTURES, BROKEN_FIXTURES, ROOT / "brokenjavapngsuite"):
        candidate = directory / name
        if candidate.exists():
            return candidate
    return REPAIR_FIXTURES / name


def tiny_rgb_png(*, filtered_scanlines: bytes | None = None, width: int = 1, height: int = 1) -> bytes:
    if filtered_scanlines is None:
        filtered_scanlines = b"\x00\x00\x00\x00"
    ihdr = width.to_bytes(4, "big") + height.to_bytes(4, "big") + b"\x08\x02\x00\x00\x00"
    return PNG_SIGNATURE + build_png_chunk(b"IHDR", ihdr) + build_png_chunk(
        b"IDAT",
        zlib.compress(filtered_scanlines, level=0),
    ) + IEND_CHUNK


def tiny_indexed_png_without_plte() -> bytes:
    ihdr = (1).to_bytes(4, "big") + (1).to_bytes(4, "big") + b"\x08\x03\x00\x00\x00"
    return PNG_SIGNATURE + build_png_chunk(b"IHDR", ihdr) + build_png_chunk(
        b"IDAT",
        zlib.compress(b"\x00\x00", level=0),
    ) + IEND_CHUNK


def test_read_valid_png_chunks_from_fixture():
    chunks = read_chunks(FIXTURE)

    assert chunks[0].chunk_type == b"IHDR"
    assert chunks[0].length == 13
    assert chunks[-1].chunk_type == b"IEND"
    assert all(chunk.crc_ok for chunk in chunks)


def test_repair_indexed_plte_rebuilds_malformed_palette():
    repaired = repair_indexed_plte((BROKEN_FIXTURES / "plte_length_mod_three.png").read_bytes())

    assert repaired is not None
    assert repaired.strategy == "rebuilt malformed indexed PLTE as grayscale palette"
    assert validate_png_structure(repaired.data).errors == ()
    plte = next(chunk for chunk in iter_chunks(repaired.data) if chunk.chunk_type == b"PLTE")
    assert plte.length == 768


def test_repair_indexed_plte_truncates_palette_with_too_many_entries():
    repaired = repair_indexed_plte((BROKEN_FIXTURES / "plte_too_many_entries.png").read_bytes())

    assert repaired is not None
    assert repaired.strategy == "truncated indexed PLTE to bit depth entry count"
    assert validate_png_structure(repaired.data).errors == ()
    plte = next(chunk for chunk in iter_chunks(repaired.data) if chunk.chunk_type == b"PLTE")
    assert plte.length == 48


def test_repair_indexed_plte_inserts_missing_palette():
    original = tiny_indexed_png_without_plte()

    assert validate_png_structure(original).errors == ("Indexed-color PNG requires a PLTE chunk",)

    repaired = repair_indexed_plte(original)

    assert repaired is not None
    assert repaired.strategy == "inserted missing indexed PLTE as grayscale palette"
    assert validate_png_structure(repaired.data).ok
    plte = next(chunk for chunk in iter_chunks(repaired.data) if chunk.chunk_type == b"PLTE")
    assert plte.length == 768


def test_repair_indexed_plte_inserts_missing_palette_before_trns():
    ihdr = (1).to_bytes(4, "big") + (1).to_bytes(4, "big") + b"\x08\x03\x00\x00\x00"
    original = (
        PNG_SIGNATURE
        + build_png_chunk(b"IHDR", ihdr)
        + build_png_chunk(b"gAMA", b"\x00\x01\x86\xa0")
        + build_png_chunk(b"tRNS", b"\xff")
        + build_png_chunk(b"bKGD", b"\x00")
        + build_png_chunk(b"IDAT", zlib.compress(b"\x00\x00", level=0))
        + IEND_CHUNK
    )

    assert validate_png_structure(original).errors == (
        "Indexed-color PNG requires a PLTE chunk",
    )

    repaired = repair_indexed_plte(original)

    assert repaired is not None
    assert validate_png_structure(repaired.data).ok
    assert [chunk.chunk_type for chunk in iter_chunks(repaired.data)] == [
        b"IHDR",
        b"gAMA",
        b"PLTE",
        b"tRNS",
        b"bKGD",
        b"IDAT",
        b"IEND",
    ]


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


def test_extract_png_segment_cuts_trailing_container_bytes():
    embedded = tiny_rgb_png()
    data = b"RIFF" + embedded + b"%PDF-tailPK"

    assert extract_png_segment(data, signature_offset=4) == embedded

    recovery = detect_png_signature_recovery(data)

    assert recovery.action == "cut_at_signature"
    assert recovery.signature_offset == 4
    assert recovery.fixed_data == embedded


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


def test_repair_linefeed_conversion_restores_signature_cr():
    original = tiny_rgb_png()
    corrupted = original[:4] + original[5:]

    repaired = repair_linefeed_conversion(corrupted)

    assert repaired is not None
    assert repaired.inserted_signature_cr is True
    assert repaired.payload_patches == ()
    assert repaired.data == original
    assert validate_png_structure(repaired.data).ok


def test_repair_linefeed_conversion_restores_missing_idat_cr_from_crc():
    filtered = b"".join(b"\x00" + bytes((13, row, 255 - row)) for row in range(5))
    original = tiny_rgb_png(filtered_scanlines=filtered, height=5)
    idat = next(chunk for chunk in iter_chunks(original) if chunk.chunk_type == b"IDAT")
    cr_relative = idat.data.index(b"\r")
    cr_absolute = idat.offset + 8 + cr_relative
    corrupted = original[:4] + original[5:cr_absolute] + original[cr_absolute + 1 :]

    repaired = repair_linefeed_conversion(corrupted)

    assert repaired is not None
    assert repaired.inserted_signature_cr is True
    assert len(repaired.payload_patches) == 1
    assert repaired.payload_patches[0].chunk_type == b"IDAT"
    assert repaired.payload_patches[0].inserted_value == 0x0D
    assert repaired.data == original
    assert validate_png_structure(repaired.data).ok


def test_repair_linefeed_conversion_can_return_partial_signature_repair():
    corrupted = (ROOT / "David" / "6.bad.png").read_bytes()
    expected = (ROOT / "David" / "6.output.png").read_bytes()

    assert repair_linefeed_conversion(corrupted) is None

    repaired = repair_linefeed_conversion(corrupted, allow_partial=True)

    assert repaired is not None
    assert repaired.inserted_signature_cr is True
    assert repaired.payload_patches == ()
    assert repaired.validation_errors
    assert repaired.data == expected


def test_repair_overlong_chunk_length_to_next_header_realigns_idat():
    corrupted = (ROOT / "David" / "6.bad.png").read_bytes()
    linefeed = repair_linefeed_conversion(corrupted, allow_partial=True)
    assert linefeed is not None

    realigned = repair_overlong_chunk_length_to_next_header(linefeed.data)

    assert realigned is not None
    assert realigned.chunk_name == "IDAT"
    assert realigned.old_length == 8192
    assert realigned.new_length == 8188
    assert realigned.chunk_offset == 8237
    assert all(chunk.crc_ok for chunk in iter_chunks(realigned.data))
    assert validate_png_structure(realigned.data).errors == ("IDAT zlib stream is invalid",)


def test_detect_png_signature_recovery_falls_back_to_deep_search():
    recovery = detect_png_signature_recovery(b"not a png")

    assert recovery.action == "search_deeper"
    assert recovery.signature_offset is None
    assert recovery.fixed_data is None


def test_legacy_find_magic_checkpoint_args_preserve_found_signature_call_shape():
    recovery = detect_png_signature_recovery(PNG_SIGNATURE + b"tail")

    assert legacy_find_magic_checkpoint_args(recovery, len(PNG_SIGNATURE.hex())) == (
        False,
        False,
        "FindMagic",
        "PngSig",
        ["-Found Magic"],
        len(PNG_SIGNATURE.hex()),
    )


def test_legacy_find_magic_checkpoint_args_preserve_cut_signature_call_shape():
    recovery = detect_png_signature_recovery(b"junk" + PNG_SIGNATURE + b"tail")

    assert legacy_find_magic_checkpoint_args(recovery, len(PNG_SIGNATURE.hex())) == (
        False,
        False,
        "FindMagic",
        "PngSig",
        ["Cutting at Magic"],
        (PNG_SIGNATURE + b"tail").hex(),
        "0x4",
    )


def test_legacy_find_magic_checkpoint_args_preserve_deep_search_call_shape():
    recovery = detect_png_signature_recovery(b"not a png")

    assert legacy_find_magic_checkpoint_args(recovery, len(PNG_SIGNATURE.hex())) == (
        False,
        False,
        "FindMagic",
        "PngSig",
        ["-dig a little bit deeper"],
    )


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


def test_legacy_length_checkpoint_args_preserve_found_next_chunk_call_shape():
    decision = legacy_length_decision(
        FIXTURE.read_bytes(),
        len(PNG_SIGNATURE) * 2,
        previous_chunk=b"IHDR",
        idat_average_length=0,
    )

    assert legacy_length_checkpoint_args(decision, b"IHDR", "0000000d", b"PNG") == (
        False,
        False,
        "CheckLength",
        b"IHDR",
        ["-Found NextChunk"],
        "0000000d",
    )


def test_legacy_length_checkpoint_args_preserve_missing_next_chunk_call_shape():
    data = PNG_SIGNATURE + b"\x00\x00\x00\x04IDATab"
    decision = legacy_length_decision(
        data,
        len(PNG_SIGNATURE) * 2,
        previous_chunk=b"IDAT",
        idat_average_length=12,
    )

    assert legacy_length_checkpoint_args(decision, b"IDAT", "00000004", b"IHDR") == (
        True,
        False,
        "CheckLength",
        b"IDAT",
        ["-No NextChunk"],
        b"IDAT",
        "00000004",
        b"IHDR",
    )


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


def test_legacy_crc_debug_lines_preserve_checksum_debug_output():
    decision = legacy_crc_decision("49444154", "616263", "00000000")

    assert legacy_crc_debug_lines(decision) == (
        "-Crc from file: %s" % decision.computed_crc_hex,
        "-Actual Crc: 0x0\n",
    )


def test_legacy_crc_monkey_lines_preserve_checksum_mismatch_output():
    assert legacy_crc_monkey_lines("<green:0x1234>", "<red:0x0>") == (
        "\nMonkey wanted Banana :<green:0x1234>",
        "Monkey got Pullover :<red:0x0>",
    )


def test_legacy_crc_checkpoint_args_preserve_valid_crc_call_shape():
    stored_crc = zlib.crc32(b"IDAT" + b"abc").to_bytes(4, "big").hex()
    decision = legacy_crc_decision("49444154", "616263", stored_crc)

    assert legacy_crc_checkpoint_args(
        decision,
        crc_offset=40,
        original_chunk_type=b"IDAT",
        crc_offset_hex="0x28",
        original_crc=stored_crc,
        original_length="00000003",
        data_offset=16,
    ) == (
        False,
        False,
        "Checksum",
        b"IDAT",
        ["-Crc is correct"],
    )


def test_legacy_crc_checkpoint_args_preserve_invalid_crc_call_shape():
    decision = legacy_crc_decision("49444154", "616263", "00000000")

    assert legacy_crc_checkpoint_args(
        decision,
        crc_offset=40,
        original_chunk_type=b"IDAT",
        crc_offset_hex="0x28",
        original_crc="00000000",
        original_length="00000003",
        data_offset=16,
    ) == (
        True,
        False,
        "Checksum",
        b"IDAT",
        ["-Wrong Crc b'IDAT'"],
        decision.normalized_computed_crc_no_prefix,
        40,
        48,
        b"IDAT",
        "0x28",
        "00000000",
        3,
        16,
    )


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


def test_repair_ihdr_rebuilds_invalid_rgba_bit_depth_from_idat():
    original = (BROKEN_FIXTURES / "ihdr_1bit_alpha.png").read_bytes()

    repaired = repair_ihdr(original)

    assert repaired is not None
    assert repaired.preserved_crc is False
    assert repaired.width == 32
    assert repaired.height == 32
    assert repaired.bit_depth == 8
    assert repaired.color_type == 6
    assert validate_png_structure(repaired.data).ok
    first = next(iter_chunks(repaired.data))
    assert first.data[8:10] == b"\x08\x06"
    assert first.crc_ok


def test_repair_ihdr_rebuilds_invalid_indexed_bit_depth_from_idat():
    original = (BROKEN_FIXTURES / "ihdr_16bit_palette.png").read_bytes()

    repaired = repair_ihdr(original)

    assert repaired is not None
    assert repaired.preserved_crc is False
    assert repaired.width == 32
    assert repaired.height == 32
    assert repaired.bit_depth == 8
    assert repaired.color_type == 3
    assert validate_png_structure(repaired.data).ok
    first = next(iter_chunks(repaired.data))
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


def minimal_png_with_color_and_chunk(color_type, chunk_type, chunk_data):
    ihdr = build_png_chunk(b"IHDR", struct.pack("!IIBBBBB", 1, 1, 8, color_type, 0, 0, 0))
    prefix = b""
    if color_type == 3:
        prefix = build_png_chunk(b"PLTE", bytes(range(60)))
        scanline = b"\x00\x00"
    elif color_type == 4:
        scanline = b"\x00\x00\xff"
    elif color_type == 6:
        scanline = b"\x00\x00\x00\x00\xff"
    elif color_type == 2:
        scanline = b"\x00\x00\x00\x00"
    else:
        scanline = b"\x00\x00"
    idat = build_png_chunk(b"IDAT", zlib.compress(scanline))
    return PNG_SIGNATURE + ihdr + prefix + build_png_chunk(chunk_type, chunk_data) + idat + IEND_CHUNK


def test_repair_bkgd_length_truncates_gray_alpha_payload():
    broken = minimal_png_with_color_and_chunk(4, b"bKGD", b"\x00\x00\x00\x00\x00\x00")

    repaired = repair_bkgd_length(broken)

    assert repaired is not None
    assert repaired.old_length == 6
    assert repaired.new_length == 2
    assert repaired.removed is False
    bkgd = next(chunk for chunk in iter_chunks(repaired.data) if chunk.chunk_type == b"bKGD")
    assert bkgd.data == b"\x00\x00"
    assert bkgd.crc_ok
    assert validate_png_structure(repaired.data).ok


def test_repair_bkgd_length_truncates_palette_payload():
    broken = minimal_png_with_color_and_chunk(3, b"bKGD", b"\x13\x00\x00\x00\x00\x00")

    repaired = repair_bkgd_length(broken)

    assert repaired is not None
    assert repaired.old_length == 6
    assert repaired.new_length == 1
    bkgd = next(chunk for chunk in iter_chunks(repaired.data) if chunk.chunk_type == b"bKGD")
    assert bkgd.data == b"\x13"
    assert bkgd.crc_ok
    assert validate_png_structure(repaired.data).ok


def test_repair_bkgd_length_removes_short_truecolor_alpha_payload():
    broken = minimal_png_with_color_and_chunk(6, b"bKGD", b"\x00\xff")

    repaired = repair_bkgd_length(broken)

    assert repaired is not None
    assert repaired.old_length == 2
    assert repaired.new_length == 0
    assert repaired.removed is True
    assert b"bKGD" not in {chunk.chunk_type for chunk in iter_chunks(repaired.data)}
    assert validate_png_structure(repaired.data).ok


def test_repair_duplicate_singleton_chunks_removes_second_bkgd():
    ihdr = build_png_chunk(b"IHDR", b"\x00\x00\x00\x01\x00\x00\x00\x01\x10\x04\x00\x00\x00")
    original = (
        PNG_SIGNATURE
        + ihdr
        + build_png_chunk(b"gAMA", b"\x00\x01\x86\xa0")
        + build_png_chunk(b"bKGD", b"\x00\x01")
        + build_png_chunk(b"bKGD", b"\x00\x02")
        + build_png_chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\xff\xff"))
        + IEND_CHUNK
    )

    assert validate_png_structure(original).errors == (
        "PNG must not contain multiple bKGD chunks",
    )

    repaired = repair_duplicate_singleton_chunks(original)

    assert repaired is not None
    assert repaired.strategy == "removed duplicate singleton chunk(s): bKGD"
    assert repaired.removed_chunks == ("bKGD",)
    assert validate_png_structure(repaired.data).ok
    assert [chunk.chunk_type for chunk in iter_chunks(repaired.data)] == [
        b"IHDR",
        b"gAMA",
        b"bKGD",
        b"IDAT",
        b"IEND",
    ]
    bkgd = next(chunk for chunk in iter_chunks(repaired.data) if chunk.chunk_type == b"bKGD")
    assert bkgd.data == b"\x00\x01"


def test_repair_hist_out_of_place_removes_optional_hist_chunk():
    ihdr = build_png_chunk(b"IHDR", b"\x00\x00\x00\x01\x00\x00\x00\x01\x01\x03\x00\x00\x00")
    original = (
        PNG_SIGNATURE
        + ihdr
        + build_png_chunk(b"PLTE", b"\x00\x00\x00\xff\xff\xff")
        + build_png_chunk(b"hIST", b"\x00\x01\x00\x02")
        + build_png_chunk(b"IDAT", zlib.compress(b"\x00\x00"))
        + IEND_CHUNK
    )

    repaired = repair_hist_out_of_place(original)

    assert repaired is not None
    assert repaired.strategy == "removed optional hIST chunk(s) after duplicate/out-of-place finding"
    assert repaired.removed_chunks == ("hIST",)
    assert validate_png_structure(repaired.data).ok
    assert [chunk.chunk_type for chunk in iter_chunks(repaired.data)] == [
        b"IHDR",
        b"PLTE",
        b"IDAT",
        b"IEND",
    ]


def test_repair_hist_out_of_place_can_require_duplicate_hist_chunks():
    ihdr = build_png_chunk(b"IHDR", b"\x00\x00\x00\x01\x00\x00\x00\x01\x01\x03\x00\x00\x00")
    prefix = PNG_SIGNATURE + ihdr + build_png_chunk(b"PLTE", b"\x00\x00\x00\xff\xff\xff")
    suffix = build_png_chunk(b"IDAT", zlib.compress(b"\x00\x00")) + IEND_CHUNK
    hist = build_png_chunk(b"hIST", b"\x00\x01\x00\x02")
    single = prefix + hist + suffix
    duplicate = prefix + hist + hist + suffix

    assert repair_hist_out_of_place(single, require_multiple=True) is None

    repaired = repair_hist_out_of_place(duplicate, require_multiple=True)

    assert repaired is not None
    assert repaired.removed_chunks == ("hIST", "hIST")
    assert b"hIST" not in {chunk.chunk_type for chunk in iter_chunks(repaired.data)}


def test_validate_png_structure_rejects_hist_after_idat():
    ihdr = build_png_chunk(b"IHDR", b"\x00\x00\x00\x01\x00\x00\x00\x01\x01\x03\x00\x00\x00")
    broken = (
        PNG_SIGNATURE
        + ihdr
        + build_png_chunk(b"PLTE", b"\x00\x00\x00\xff\xff\xff")
        + build_png_chunk(b"IDAT", zlib.compress(b"\x00\x00"))
        + build_png_chunk(b"hIST", b"\x00\x01\x00\x02")
        + IEND_CHUNK
    )

    assert "hIST chunk must appear before the first IDAT chunk" in validate_png_structure(broken).errors


def test_repair_gama_length_infers_common_missing_byte():
    broken = repair_fixture("length_gama.png").read_bytes()

    assert "gAMA chunk length must be 4" in validate_png_structure(broken).errors

    repaired = repair_gama_length(broken)

    assert repaired is not None
    assert repaired.old_length == 3
    assert repaired.new_length == 4
    assert repaired.missing_bytes == 1
    assert repaired.inferred_payload == (100000).to_bytes(4, "big")
    gama = next(chunk for chunk in iter_chunks(repaired.data) if chunk.chunk_type == b"gAMA")
    assert gama.data == (100000).to_bytes(4, "big")
    assert gama.crc_ok
    assert validate_png_structure(repaired.data).ok


def test_repair_gama_length_removes_uninferrable_short_payload():
    broken = minimal_png_with_color_and_chunk(2, b"gAMA", b"\xff")

    repaired = repair_gama_length(broken)

    assert repaired is not None
    assert repaired.removed is True
    assert repaired.new_length == 0
    assert b"gAMA" not in {chunk.chunk_type for chunk in iter_chunks(repaired.data)}
    assert validate_png_structure(repaired.data).ok


def test_repair_gifg_length_truncates_legacy_payload():
    broken = repair_fixture("length_gifg.png").read_bytes()

    assert "gIFg chunk length must be 4" in validate_png_structure(broken).errors

    repaired = repair_gifg_length(broken)

    assert repaired is not None
    assert repaired.old_length == 5
    assert repaired.new_length == 4
    gifg = next(chunk for chunk in iter_chunks(repaired.data) if chunk.chunk_type == b"gIFg")
    assert gifg.data == bytes.fromhex("0200000a")
    assert gifg.crc_ok
    assert validate_png_structure(repaired.data).ok


def test_repair_offs_length_infers_missing_unit_byte():
    broken = repair_fixture("length_offs.png").read_bytes()

    assert "oFFs chunk length must be 9" in validate_png_structure(broken).errors

    repaired = repair_offs_length(broken)

    assert repaired is not None
    assert repaired.old_length == 8
    assert repaired.new_length == 9
    assert repaired.strategy == "inferred missing oFFs unit byte 0 and rebuilt CRC"
    offs = next(chunk for chunk in iter_chunks(repaired.data) if chunk.chunk_type == b"oFFs")
    assert offs.data == b"\x00" * 9
    assert offs.crc_ok
    assert validate_png_structure(repaired.data).ok


def test_repair_phys_length_infers_missing_unit_byte():
    broken = repair_fixture("length_phys.png").read_bytes()

    assert "pHYs chunk length must be 9" in validate_png_structure(broken).errors

    repaired = repair_phys_length(broken)

    assert repaired is not None
    assert repaired.old_length == 8
    assert repaired.new_length == 9
    assert repaired.strategy == "inferred missing pHYs unit byte 0 and rebuilt CRC"
    phys = next(chunk for chunk in iter_chunks(repaired.data) if chunk.chunk_type == b"pHYs")
    assert phys.data == bytes.fromhex("000003e8000003e800")
    assert phys.crc_ok
    assert validate_png_structure(repaired.data).ok


def test_repair_sbit_length_trims_indexed_payload():
    broken = repair_fixture("length_sbit.png").read_bytes()

    assert "sBIT chunk length must be 3 for IHDR color type 3" in validate_png_structure(broken).errors

    repaired = repair_sbit_length(broken)

    assert repaired is not None
    assert repaired.old_length == 4
    assert repaired.new_length == 3
    assert repaired.strategy == "trimmed sBIT length from 4 to 3 and rebuilt CRC"
    sbit = next(chunk for chunk in iter_chunks(repaired.data) if chunk.chunk_type == b"sBIT")
    assert sbit.data == bytes.fromhex("010101")
    assert sbit.crc_ok
    assert validate_png_structure(repaired.data).ok


def test_repair_sbit_length_trims_grayscale_payload():
    broken = repair_fixture("length_sbit_2.png").read_bytes()

    assert "sBIT chunk length must be 1 for IHDR color type 0" in validate_png_structure(broken).errors

    repaired = repair_sbit_length(broken)

    assert repaired is not None
    assert repaired.old_length == 3
    assert repaired.new_length == 1
    assert repaired.strategy == "trimmed sBIT length from 3 to 1 and rebuilt CRC"
    sbit = next(chunk for chunk in iter_chunks(repaired.data) if chunk.chunk_type == b"sBIT")
    assert sbit.data == b"\x01"
    assert sbit.crc_ok
    assert validate_png_structure(repaired.data).ok


def test_repair_srgb_length_trims_rendering_intent_payload():
    broken = repair_fixture("length_srgb.png").read_bytes()

    assert "sRGB chunk length must be 1" in validate_png_structure(broken).errors

    repaired = repair_srgb_length(broken)

    assert repaired is not None
    assert repaired.old_length == 2
    assert repaired.new_length == 1
    assert repaired.strategy == "trimmed sRGB length from 2 to 1 and rebuilt CRC"
    srgb = next(chunk for chunk in iter_chunks(repaired.data) if chunk.chunk_type == b"sRGB")
    assert srgb.data == b"\x03"
    assert srgb.crc_ok
    assert validate_png_structure(repaired.data).ok


def test_repair_ster_length_trims_stereo_mode_payload():
    broken = repair_fixture("length_ster.png").read_bytes()

    assert "sTER chunk length must be 1" in validate_png_structure(broken).errors

    repaired = repair_ster_length(broken)

    assert repaired is not None
    assert repaired.old_length == 2
    assert repaired.new_length == 1
    assert repaired.strategy == "trimmed sTER length from 2 to 1 and rebuilt CRC"
    ster = next(chunk for chunk in iter_chunks(repaired.data) if chunk.chunk_type == b"sTER")
    assert ster.data == b"\x00"
    assert ster.crc_ok
    assert validate_png_structure(repaired.data).ok


def test_repair_time_length_infers_missing_second_byte():
    broken = repair_fixture("length_time.png").read_bytes()

    assert "tIME chunk length must be 7" in validate_png_structure(broken).errors

    repaired = repair_time_length(broken)

    assert repaired is not None
    assert repaired.old_length == 6
    assert repaired.new_length == 7
    assert repaired.strategy == "inferred missing tIME second byte 0 and rebuilt CRC"
    time = next(chunk for chunk in iter_chunks(repaired.data) if chunk.chunk_type == b"tIME")
    assert time.data == bytes.fromhex("07d001010c2200")
    assert time.crc_ok
    assert validate_png_structure(repaired.data).ok


def test_repair_trns_length_pads_empty_grayscale_sample():
    broken = repair_fixture("length_trns_gray.png").read_bytes()

    assert "tRNS chunk length must be 2 for IHDR color type 0" in validate_png_structure(broken).errors

    repaired = repair_trns_length(broken)

    assert repaired is not None
    assert repaired.old_length == 0
    assert repaired.new_length == 2
    assert repaired.strategy == "padded tRNS length from 0 to 2 with zero bytes and rebuilt CRC"
    trns = next(chunk for chunk in iter_chunks(repaired.data) if chunk.chunk_type == b"tRNS")
    assert trns.data == b"\x00\x00"
    assert trns.crc_ok
    assert validate_png_structure(repaired.data).ok


def test_repair_trns_length_removes_fully_transparent_palette_alpha_entries():
    broken = repair_fixture("length_trns_palette.png").read_bytes()

    assert "tRNS chunk length must not exceed PLTE entry count" in validate_png_structure(broken).errors

    repaired = repair_trns_length(broken)

    assert repaired is not None
    assert repaired.old_length == 174
    assert repaired.new_length == 0
    assert repaired.removed is True
    assert repaired.strategy == "removed indexed tRNS because repaired alpha table would be fully transparent"
    assert not any(chunk.chunk_type == b"tRNS" for chunk in iter_chunks(repaired.data))
    assert validate_png_structure(repaired.data).ok


def test_repair_hist_length_pads_missing_frequency():
    broken = repair_fixture("length_hist.png").read_bytes()

    assert "hIST chunk length must match PLTE entry count" in validate_png_structure(broken).errors

    repaired = repair_hist_length(broken)

    assert repaired is not None
    assert repaired.old_length == 28
    assert repaired.new_length == 30
    hist = next(chunk for chunk in iter_chunks(repaired.data) if chunk.chunk_type == b"hIST")
    assert hist.length == 30
    assert hist.data.endswith(b"\x00\x00")
    assert hist.crc_ok
    assert validate_png_structure(repaired.data).ok


def test_repair_hist_length_trims_extra_frequency():
    plte = build_png_chunk(b"PLTE", bytes(range(6)))
    hist = build_png_chunk(b"hIST", b"\x00\x01\x00\x02\x00\x03")
    broken = (
        PNG_SIGNATURE
        + build_png_chunk(b"IHDR", b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x03\x00\x00\x00")
        + plte
        + hist
        + build_png_chunk(b"IDAT", zlib.compress(b"\x00\x00"))
        + IEND_CHUNK
    )

    repaired = repair_hist_length(broken)

    assert repaired is not None
    assert repaired.old_length == 6
    assert repaired.new_length == 4
    hist = next(chunk for chunk in iter_chunks(repaired.data) if chunk.chunk_type == b"hIST")
    assert hist.data == b"\x00\x01\x00\x02"
    assert validate_png_structure(repaired.data).ok


def test_repair_iend_length_rebuilds_canonical_iend():
    broken = repair_fixture("length_iend.png").read_bytes()

    assert "IEND chunk length must be zero" in validate_png_structure(broken).errors

    repaired = repair_iend_length(broken)

    assert repaired is not None
    assert repaired.old_length == 1
    assert repaired.new_length == 0
    assert repaired.data.endswith(IEND_CHUNK)
    chunks = list(iter_chunks(repaired.data))
    assert chunks[-1].chunk_type == b"IEND"
    assert chunks[-1].length == 0
    assert chunks[-1].crc_ok
    assert validate_png_structure(repaired.data).ok


def test_validate_png_structure_catches_known_length_fixtures():
    expected_errors = {
        "length_gama.png": "gAMA chunk length must be 4",
        "length_gifg.png": "gIFg chunk length must be 4",
        "length_hist.png": "hIST chunk length must match PLTE entry count",
        "length_iend.png": "IEND chunk length must be zero",
        "length_ihdr.png": "IHDR chunk is missing or malformed",
        "length_offs.png": "oFFs chunk length must be 9",
        "length_phys.png": "pHYs chunk length must be 9",
        "length_sbit.png": "sBIT chunk length must be 3 for IHDR color type 3",
        "length_sbit_2.png": "sBIT chunk length must be 1 for IHDR color type 0",
        "length_srgb.png": "sRGB chunk length must be 1",
        "length_ster.png": "sTER chunk length must be 1",
        "length_time.png": "tIME chunk length must be 7",
        "length_trns_gray.png": "tRNS chunk length must be 2 for IHDR color type 0",
        "length_trns_palette.png": "tRNS chunk length must not exceed PLTE entry count",
        "length_trns_rgb.png": "tRNS chunk length must be 6 for IHDR color type 2",
    }

    for fixture, expected_error in expected_errors.items():
        errors = validate_png_structure(repair_fixture(fixture).read_bytes()).errors
        assert expected_error in errors


def test_repair_chrm_length_uses_crc_proven_missing_byte():
    chrm_chunk = (
        (len(SRGB_CHRM_PAYLOAD) - 1).to_bytes(4, "big")
        + b"cHRM"
        + SRGB_CHRM_PAYLOAD[:-1]
        + (zlib.crc32(b"cHRM" + SRGB_CHRM_PAYLOAD) & 0xFFFFFFFF).to_bytes(4, "big")
    )
    broken = (
        PNG_SIGNATURE
        + build_png_chunk(b"IHDR", b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x00\x00\x00\x00")
        + chrm_chunk
        + build_png_chunk(b"IDAT", zlib.compress(b"\x00\x00"))
        + IEND_CHUNK
    )

    repaired = repair_chrm_length(broken)

    assert repaired is not None
    assert repaired.preserved_crc is True
    assert repaired.crc_bruteforce_attempted is True
    assert repaired.crc_candidates_tested == 113
    chrm = next(chunk for chunk in iter_chunks(repaired.data) if chunk.chunk_type == b"cHRM")
    assert chrm.length == 32
    assert chrm.data == SRGB_CHRM_PAYLOAD
    assert chrm.crc_ok
    assert validate_png_structure(repaired.data).ok


def test_repair_chrm_length_infers_when_crc_does_not_match():
    broken = (BROKEN_FIXTURES / "length_chrm.png").read_bytes()

    repaired = repair_chrm_length(broken)

    assert repaired is not None
    assert repaired.preserved_crc is False
    assert repaired.crc_bruteforce_attempted is True
    assert repaired.crc_candidates_tested == 256
    assert repaired.missing_bytes == 1
    assert repaired.inferred_payload == SRGB_CHRM_PAYLOAD
    assert repaired.removal_data is not None
    chrm = next(chunk for chunk in iter_chunks(repaired.data) if chunk.chunk_type == b"cHRM")
    assert chrm.length == 32
    assert chrm.data == SRGB_CHRM_PAYLOAD
    assert validate_png_structure(repaired.data).ok


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


def test_repair_itxt_compression_flag_to_uncompressed_text():
    itxt = b"Vegetable\x00\x02\x00en-us\x00\x00Cucumber"
    broken = minimal_gray_png_with_chunk(b"iTXt", itxt)

    repaired = repair_itxt_compression_flag(broken)

    assert repaired is not None
    assert repaired.old_flag == 2
    assert repaired.new_flag == 0
    chunk = next(chunk for chunk in iter_chunks(repaired.data) if chunk.chunk_type == b"iTXt")
    assert chunk.data == b"Vegetable\x00\x00\x00en-us\x00\x00Cucumber"
    assert chunk.crc_ok
    assert is_complete_png_with_valid_crc(repaired.data)


def test_repair_itxt_compression_flag_to_compressed_text():
    compressed_text = zlib.compress("Cucumber".encode())
    itxt = b"Vegetable\x00\x02\x00en-us\x00\x00" + compressed_text
    broken = minimal_gray_png_with_chunk(b"iTXt", itxt)

    repaired = repair_itxt_compression_flag(broken)

    assert repaired is not None
    assert repaired.old_flag == 2
    assert repaired.new_flag == 1
    chunk = next(chunk for chunk in iter_chunks(repaired.data) if chunk.chunk_type == b"iTXt")
    assert chunk.data == b"Vegetable\x00\x01\x00en-us\x00\x00" + compressed_text
    assert chunk.crc_ok
    assert is_complete_png_with_valid_crc(repaired.data)


def test_repair_itxt_compression_method_with_compressed_text():
    compressed_text = zlib.compress("Cucumber".encode())
    itxt = b"Vegetable\x00\x01\x01en-us\x00\x00" + compressed_text
    broken = minimal_gray_png_with_chunk(b"iTXt", itxt)

    repaired = repair_itxt_compression_method(broken)

    assert repaired is not None
    assert repaired.old_method == 1
    assert repaired.new_method == 0
    chunk = next(chunk for chunk in iter_chunks(repaired.data) if chunk.chunk_type == b"iTXt")
    assert chunk.data == b"Vegetable\x00\x01\x00en-us\x00\x00" + compressed_text
    assert chunk.crc_ok
    assert is_complete_png_with_valid_crc(repaired.data)


def test_repair_itxt_compression_method_with_uncompressed_text():
    itxt = b"Vegetable\x00\x00\x01en-us\x00\x00Cucumber"
    broken = minimal_gray_png_with_chunk(b"iTXt", itxt)

    repaired = repair_itxt_compression_method(broken)

    assert repaired is not None
    assert repaired.old_method == 1
    assert repaired.new_method == 0
    chunk = next(chunk for chunk in iter_chunks(repaired.data) if chunk.chunk_type == b"iTXt")
    assert chunk.data == b"Vegetable\x00\x00\x00en-us\x00\x00Cucumber"
    assert chunk.crc_ok
    assert is_complete_png_with_valid_crc(repaired.data)


def test_repair_itxt_keyword_length_replaces_empty_keyword():
    itxt = b"\x00\x00\x00en-us\x00\x00Cucumber"
    broken = minimal_gray_png_with_chunk(b"iTXt", itxt)

    repaired = repair_itxt_keyword_length(broken)

    assert repaired is not None
    assert repaired.old_keyword_length == 0
    assert repaired.new_keyword == b"Comment"
    chunk = next(chunk for chunk in iter_chunks(repaired.data) if chunk.chunk_type == b"iTXt")
    assert chunk.data == b"Comment\x00\x00\x00en-us\x00\x00Cucumber"
    assert chunk.crc_ok
    assert is_complete_png_with_valid_crc(repaired.data)


def test_repair_itxt_keyword_length_truncates_long_keyword():
    keyword = b"0123456789" * 8
    itxt = keyword + b"\x00\x00\x00en-us\x00\x00Cucumber"
    broken = minimal_gray_png_with_chunk(b"iTXt", itxt)

    repaired = repair_itxt_keyword_length(broken)

    assert repaired is not None
    assert repaired.old_keyword_length == 80
    assert repaired.new_keyword == keyword[:79]
    chunk = next(chunk for chunk in iter_chunks(repaired.data) if chunk.chunk_type == b"iTXt")
    assert chunk.data == keyword[:79] + b"\x00\x00\x00en-us\x00\x00Cucumber"
    assert chunk.crc_ok
    assert is_complete_png_with_valid_crc(repaired.data)


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
            "Extract PNG segment cuts trailing container bytes",
            test_extract_png_segment_cuts_trailing_container_bytes,
        ),
        (
            "Detect PNG signature recovery classifies linefeed candidates",
            test_detect_png_signature_recovery_classifies_linefeed_candidates,
        ),
        ("Repair linefeed signature CR", test_repair_linefeed_conversion_restores_signature_cr),
        (
            "Repair linefeed IDAT CR",
            test_repair_linefeed_conversion_restores_missing_idat_cr_from_crc,
        ),
        (
            "Repair linefeed partial signature CR",
            test_repair_linefeed_conversion_can_return_partial_signature_repair,
        ),
        (
            "Repair overlong chunk length to next header",
            test_repair_overlong_chunk_length_to_next_header_realigns_idat,
        ),
        (
            "Detect PNG signature recovery falls back to deep search",
            test_detect_png_signature_recovery_falls_back_to_deep_search,
        ),
        (
            "Legacy FindMagic checkpoint args for found signature",
            test_legacy_find_magic_checkpoint_args_preserve_found_signature_call_shape,
        ),
        (
            "Legacy FindMagic checkpoint args for cut signature",
            test_legacy_find_magic_checkpoint_args_preserve_cut_signature_call_shape,
        ),
        (
            "Legacy FindMagic checkpoint args for deep search",
            test_legacy_find_magic_checkpoint_args_preserve_deep_search_call_shape,
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
        (
            "Legacy length checkpoint args for found next chunk",
            test_legacy_length_checkpoint_args_preserve_found_next_chunk_call_shape,
        ),
        (
            "Legacy length checkpoint args for missing next chunk",
            test_legacy_length_checkpoint_args_preserve_missing_next_chunk_call_shape,
        ),
        ("Legacy CRC decision matches checksum wrapper values", test_legacy_crc_decision_matches_checksum_wrapper_values),
        ("Legacy CRC debug lines", test_legacy_crc_debug_lines_preserve_checksum_debug_output),
        ("Legacy CRC monkey lines", test_legacy_crc_monkey_lines_preserve_checksum_mismatch_output),
        (
            "Legacy CRC checkpoint args for valid CRC",
            test_legacy_crc_checkpoint_args_preserve_valid_crc_call_shape,
        ),
        (
            "Legacy CRC checkpoint args for invalid CRC",
            test_legacy_crc_checkpoint_args_preserve_invalid_crc_call_shape,
        ),
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
            "Rebuild invalid RGBA IHDR bit depth",
            test_repair_ihdr_rebuilds_invalid_rgba_bit_depth_from_idat,
        ),
        (
            "Rebuild invalid indexed IHDR bit depth",
            test_repair_ihdr_rebuilds_invalid_indexed_bit_depth_from_idat,
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
        ("Rebuild malformed indexed PLTE", test_repair_indexed_plte_rebuilds_malformed_palette),
        ("Truncate oversized indexed PLTE", test_repair_indexed_plte_truncates_palette_with_too_many_entries),
        ("Insert missing indexed PLTE", test_repair_indexed_plte_inserts_missing_palette),
        ("Insert missing indexed PLTE before tRNS", test_repair_indexed_plte_inserts_missing_palette_before_trns),
        ("Truncate long gray-alpha bKGD", test_repair_bkgd_length_truncates_gray_alpha_payload),
        ("Truncate long palette bKGD", test_repair_bkgd_length_truncates_palette_payload),
        ("Remove short truecolor-alpha bKGD", test_repair_bkgd_length_removes_short_truecolor_alpha_payload),
        ("Remove duplicate singleton bKGD", test_repair_duplicate_singleton_chunks_removes_second_bkgd),
        ("Remove out-of-place hIST", test_repair_hist_out_of_place_removes_optional_hist_chunk),
        (
            "Require duplicate hIST for multiple finding cleanup",
            test_repair_hist_out_of_place_can_require_duplicate_hist_chunks,
        ),
        ("Reject hIST after IDAT", test_validate_png_structure_rejects_hist_after_idat),
        ("Infer common short gAMA", test_repair_gama_length_infers_common_missing_byte),
        ("Remove unknown short gAMA", test_repair_gama_length_removes_uninferrable_short_payload),
        ("Truncate long gIFg", test_repair_gifg_length_truncates_legacy_payload),
        ("Infer missing oFFs unit", test_repair_offs_length_infers_missing_unit_byte),
        ("Infer missing pHYs unit", test_repair_phys_length_infers_missing_unit_byte),
        ("Trim indexed sBIT", test_repair_sbit_length_trims_indexed_payload),
        ("Trim grayscale sBIT", test_repair_sbit_length_trims_grayscale_payload),
        ("Trim long sRGB", test_repair_srgb_length_trims_rendering_intent_payload),
        ("Trim long sTER", test_repair_ster_length_trims_stereo_mode_payload),
        ("Infer short tIME", test_repair_time_length_infers_missing_second_byte),
        ("Pad empty grayscale tRNS", test_repair_trns_length_pads_empty_grayscale_sample),
        ("Remove fully transparent indexed tRNS", test_repair_trns_length_removes_fully_transparent_palette_alpha_entries),
        ("Pad short hIST", test_repair_hist_length_pads_missing_frequency),
        ("Trim long hIST", test_repair_hist_length_trims_extra_frequency),
        ("Rebuild wrong-length IEND", test_repair_iend_length_rebuilds_canonical_iend),
        ("Catch known length fixtures", test_validate_png_structure_catches_known_length_fixtures),
        ("Recover short cHRM from stored CRC", test_repair_chrm_length_uses_crc_proven_missing_byte),
        ("Infer short cHRM after CRC miss", test_repair_chrm_length_infers_when_crc_does_not_match),
        ("Repair missing data byte using shifted CRC", test_repair_missing_chunk_data_byte_uses_shifted_crc),
        ("Repair known chunk type case and CRC", test_repair_known_chunk_type_case_rebuilds_crc),
        ("Reject known chunk type case with incoherent data", test_repair_known_chunk_type_case_requires_coherent_data),
        ("Repair coherent sRGB chunk type case", test_repair_known_chunk_type_case_accepts_other_coherent_chunks),
        ("Repair iTXt compression flag to 00", test_repair_itxt_compression_flag_to_uncompressed_text),
        ("Repair iTXt compression flag to 01", test_repair_itxt_compression_flag_to_compressed_text),
        (
            "Repair compressed iTXt compression method",
            test_repair_itxt_compression_method_with_compressed_text,
        ),
        (
            "Repair uncompressed iTXt compression method",
            test_repair_itxt_compression_method_with_uncompressed_text,
        ),
        ("Repair empty iTXt keyword", test_repair_itxt_keyword_length_replaces_empty_keyword),
        ("Repair long iTXt keyword", test_repair_itxt_keyword_length_truncates_long_keyword),
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
