#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import bruteforce


def test_normalize_old_crc_preserves_legacy_values():
    assert bruteforce.normalize_old_crc(False) is False
    assert bruteforce.normalize_old_crc("1234abcd") == bytes.fromhex("1234abcd")
    assert bruteforce.normalize_old_crc(bytes.fromhex("1234abcd")) == bytes.fromhex("1234abcd")


def test_resolve_mode_keeps_custom_when_struct_indexes_exist():
    pandora_box = {
        "Check_Error_0:IHDR Width StructIndex:0": {},
        "Check_Error_1:IHDR Height StructIndex:1": {},
        "Check_Error_2:IDAT StructIndex:9": {},
    }

    plan = bruteforce.resolve_mode("Custom", b"IHDR", pandora_box)

    assert plan.mode == "Custom"
    assert plan.struct_indexes == (0, 1)
    assert plan.side_note is None


def test_resolve_mode_falls_back_to_brutus_when_custom_has_no_indexes():
    plan = bruteforce.resolve_mode("Custom", b"IHDR", {})

    assert plan.mode == "Brutus"
    assert plan.struct_indexes == ()
    assert plan.side_note == bruteforce.CUSTOM_TO_BRUTUS_NOTE


def test_length_range_preserves_legacy_single_and_tuple_specs():
    assert bruteforce.length_range(8) == bruteforce.BruteForceLengthRange(8, 9, 1)
    assert bruteforce.length_range((2, 4)) == bruteforce.BruteForceLengthRange(2, 4, 2)


def test_iter_nbr_for_length_preserves_legacy_threshold():
    assert bruteforce.iter_nbr_for_length(2, 2, 0) is None
    assert bruteforce.iter_nbr_for_length(4, 2, 1) == 2


def test_build_full_new_data_preserves_brutecfg_combinations():
    chunk_name = b"gAMA"
    length = b"\x00\x00\x00\x04"
    brute = b"\x00\x01\x86\xa0"
    crc = b"\x12\x34\x56\x78"

    assert bruteforce.build_full_new_data(
        chunk_name,
        length,
        brute,
        crc,
        brute_length=True,
        brute_crc=True,
        old_crc=False,
    ) == length + chunk_name + brute + crc
    assert bruteforce.build_full_new_data(
        chunk_name,
        length,
        brute,
        crc,
        brute_length=False,
        brute_crc=True,
        old_crc=False,
    ) == chunk_name + brute + crc
    assert bruteforce.build_full_new_data(
        chunk_name,
        length,
        brute,
        crc,
        brute_length=False,
        brute_crc=True,
        old_crc=crc,
    ) == brute + crc


def test_edit_window_preserves_twobytes_slicing():
    data_hex = "aabbccddeeff00112233445566778899"

    window = bruteforce.edit_window(
        data_hex,
        data_offset=4,
        chunk_length=4,
        edit_mode="Replace",
        bf_mode="TwoBytes",
        length=8,
    )

    assert window.before == bytes.fromhex("aabb")
    assert window.to_brute == "ccddeeff"
    assert window.to_bryte == bytes.fromhex("ccddeeff")
    assert window.after == bytes.fromhex("445566778899")
    assert window.length_bytes is None
    assert window.replace_flag is False
    assert window.insert_flag is False


def test_edit_window_preserves_replace_and_insert_slicing():
    data_hex = "aabbccddeeff00112233445566778899"

    replace = bruteforce.edit_window(
        data_hex,
        data_offset=4,
        chunk_length=4,
        edit_mode="Replace",
        bf_mode="Brutus",
        length=4,
    )
    insert = bruteforce.edit_window(
        data_hex,
        data_offset=4,
        chunk_length=4,
        edit_mode="Insert",
        bf_mode="Brutus",
        length=4,
    )

    assert replace.before == bytes.fromhex("aabb")
    assert replace.to_brute == "4455"
    assert replace.after == b""
    assert replace.length_bytes == b"\x00\x00\x00\x02"
    assert replace.replace_flag is True

    assert insert.before == bytes.fromhex("aabb")
    assert insert.to_brute == ""
    assert insert.after == bytes.fromhex("8899")
    assert insert.length_bytes == b"\x00\x00\x00\x02"
    assert insert.insert_flag is True


def main():
    checks = [
        ("Normalize old CRC", test_normalize_old_crc_preserves_legacy_values),
        ("Resolve custom mode", test_resolve_mode_keeps_custom_when_struct_indexes_exist),
        ("Fallback Custom to Brutus", test_resolve_mode_falls_back_to_brutus_when_custom_has_no_indexes),
        ("Length ranges", test_length_range_preserves_legacy_single_and_tuple_specs),
        ("IterNbr threshold", test_iter_nbr_for_length_preserves_legacy_threshold),
        ("Build full new data", test_build_full_new_data_preserves_brutecfg_combinations),
        ("TwoBytes edit window", test_edit_window_preserves_twobytes_slicing),
        ("Replace/Insert edit windows", test_edit_window_preserves_replace_and_insert_slicing),
    ]

    print("Running SmashBruteBrawl helper tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"SmashBruteBrawl helper tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
