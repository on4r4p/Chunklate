#!/usr/bin/env python3
import binascii
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import name_shift


KNOWN_CHUNKS = (b"IHDR", b"IDAT")


def test_find_shifted_chunk_name_detects_current_offset():
    data_hex = ("00" * 10) + b"IHDR".hex() + ("00" * 10)
    type_offset = 20

    candidate = name_shift.find_shifted_chunk_name(data_hex, type_offset, KNOWN_CHUNKS)

    assert candidate == name_shift.NameShiftCandidate(
        search_index=8,
        type_offset=20,
        chunk_name=b"IHDR",
        good_offset=0,
    )
    assert candidate.is_before is False
    assert candidate.is_after is False
    assert candidate.expected_type_offset == type_offset
    assert name_shift.current_chunk_value(data_hex, type_offset) == b"IHDR"
    assert name_shift.current_chunk_value_line(type_offset, b"IHDR") == (
        "\n-Current value of chunkname at offset 20 : b'IHDR'"
    )
    assert name_shift.found_chunk_note(8, 20, b"IHDR") == (
        "-NameShift: Found correct chunkname i:8 Offset:20 data: b'IHDR'"
    )
    assert name_shift.valid_chunk_before_line(b"IHDR", 4) == (
        "-Found valid chunkname b'IHDR' at exactly 2 bytes before."
    )
    assert name_shift.valid_chunk_after_line(b"IHDR", 6) == (
        "-Found valid chunkname b'IHDR' at exactly 3 bytes after."
    )


def test_find_shifted_chunk_name_detects_chunk_before_expected_offset():
    data_hex = ("00" * 8) + b"IHDR".hex() + ("00" * 10)
    type_offset = 20

    candidate = name_shift.find_shifted_chunk_name(data_hex, type_offset, KNOWN_CHUNKS)

    assert candidate == name_shift.NameShiftCandidate(
        search_index=4,
        type_offset=16,
        chunk_name=b"IHDR",
        good_offset=4,
    )
    assert candidate.is_before is True
    assert candidate.is_after is False
    assert candidate.expected_type_offset == type_offset


def test_find_shifted_chunk_name_detects_chunk_after_expected_offset():
    data_hex = ("00" * 8) + b"IHDR".hex() + ("00" * 10)
    type_offset = 12

    candidate = name_shift.find_shifted_chunk_name(data_hex, type_offset, KNOWN_CHUNKS)

    assert candidate == name_shift.NameShiftCandidate(
        search_index=12,
        type_offset=16,
        chunk_name=b"IHDR",
        good_offset=4,
    )
    assert candidate.is_before is False
    assert candidate.is_after is True
    assert candidate.expected_type_offset == type_offset


def test_find_shifted_chunk_name_returns_none_without_known_chunk():
    data_hex = "00" * 40

    assert name_shift.find_shifted_chunk_name(data_hex, 20, KNOWN_CHUNKS) is None


def test_parse_history_chunk_index_preserves_legacy_fields():
    assert name_shift.parse_history_chunk_index("3:20:44:16") == (
        name_shift.HistoryChunkIndex(number="3", start=20, end=44, length=16)
    )


def test_last_history_chunk_before_offset_stops_at_first_non_previous_chunk():
    indexes = [
        "0:0:16:8",
        "1:16:40:16",
        "2:40:60:12",
    ]

    assert name_shift.last_history_chunk_before_offset(indexes, 42) == (
        name_shift.HistoryChunkIndex(number="1", start=16, end=40, length=16)
    )
    assert name_shift.last_history_chunk_before_offset(indexes, 16) is None


def test_shifted_chunk_crc_view_builds_legacy_crc_values_and_fixed_hex():
    chunk_type = b"tEXt"
    chunk_data = b"abc"
    real_length = "00000003"
    crc = binascii.crc32(chunk_type + chunk_data).to_bytes(4, byteorder="big").hex()
    data_hex = real_length + chunk_type.hex() + chunk_data.hex() + crc

    view = name_shift.shifted_chunk_crc_view(data_hex, 8, chunk_type, real_length)

    assert view.data_hex_length == 6
    assert view.chunk_data == chunk_data
    assert view.file_crc == hex(int.from_bytes(bytes.fromhex(crc), byteorder="big"))
    assert view.checksum == hex(binascii.crc32(chunk_type + chunk_data))
    assert view.crc_matches is True
    assert view.fixed_hex == data_hex
    assert name_shift.crc_ok_line(" OK ", ":)") == "-Crc Check : OK :)\n"
    assert name_shift.crc_failed_line(" FAILED! ", ":(") == "-Crc Check : FAILED! :("
    assert name_shift.monkey_wanted_line("0x1234") == "\nMonkey wanted Banana :0x1234"
    assert name_shift.monkey_got_line("0x5678") == "Monkey got Pullover :0x5678"
    assert name_shift.missed_something_message() == (
        " Hold on a sec ... Must have missed something..."
    )


def test_shifted_chunk_crc_view_detects_crc_mismatch():
    chunk_type = b"tEXt"
    chunk_data = b"abc"
    real_length = "00000003"
    data_hex = real_length + chunk_type.hex() + chunk_data.hex() + "00000000"

    view = name_shift.shifted_chunk_crc_view(data_hex, 8, chunk_type, real_length)

    assert view.crc_matches is False


def test_name_shift_extra_and_missing_byte_repair_helpers_preserve_legacy_lists():
    assert name_shift.extra_bytes_align_with_previous_chunk(68, previous_chunk_end=56, good_offset=4)
    assert not name_shift.extra_bytes_align_with_previous_chunk(70, previous_chunk_end=56, good_offset=4)
    assert name_shift.extra_bytes_expected_offset(previous_chunk_end=56, good_offset=4) == 68
    assert name_shift.extra_bytes_repair_result("abcd", good_offset=4, current_type_offset=20) == [
        "abcd",
        8,
        12,
    ]
    assert name_shift.missing_bytes_repair_result("abcd", good_offset=2, current_type_offset=20) == [
        "abcd",
        2,
        12,
    ]
    assert name_shift.crc_valid_note() == "-NameShift:Crc check is valid."
    assert name_shift.extra_bytes_found_note() == "-NameShift: Extra bytes has been found."
    assert name_shift.missing_bytes_found_note() == "-NameShift: Missing bytes found."
    assert name_shift.corrupted_length_note(b"IHDR") == (
        "-NameShift: Length part of b'IHDR' was corrupted"
    )


def main():
    checks = [
        ("Current offset", test_find_shifted_chunk_name_detects_current_offset),
        ("Before expected offset", test_find_shifted_chunk_name_detects_chunk_before_expected_offset),
        ("After expected offset", test_find_shifted_chunk_name_detects_chunk_after_expected_offset),
        ("Unknown chunk", test_find_shifted_chunk_name_returns_none_without_known_chunk),
        ("Parse history chunk index", test_parse_history_chunk_index_preserves_legacy_fields),
        ("Last chunk before offset", test_last_history_chunk_before_offset_stops_at_first_non_previous_chunk),
        ("Shifted chunk CRC view", test_shifted_chunk_crc_view_builds_legacy_crc_values_and_fixed_hex),
        ("Shifted chunk CRC mismatch", test_shifted_chunk_crc_view_detects_crc_mismatch),
        ("Repair result helpers", test_name_shift_extra_and_missing_byte_repair_helpers_preserve_legacy_lists),
    ]

    print("Running name shift tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"name shift tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
