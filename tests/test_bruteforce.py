#!/usr/bin/env python3
import struct
import sys
from datetime import timedelta
from pathlib import Path
from itertools import islice


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


def test_crash_iteration_decision_preserves_resume_skip_and_reset():
    assert bruteforce.crash_iteration_decision(3, 10) == bruteforce.BruteForceCrashDecision(
        skip=True,
        crash_value=10,
    )
    assert bruteforce.crash_iteration_decision(10, 10) == bruteforce.BruteForceCrashDecision(
        skip=False,
        crash_value=False,
    )
    assert bruteforce.crash_iteration_decision(3, False) == bruteforce.BruteForceCrashDecision(
        skip=False,
        crash_value=False,
    )


def test_eta_seconds_after_sample_preserves_legacy_seconds_math():
    assert bruteforce.eta_seconds_after_sample(timedelta(seconds=2), 100) == 20
    assert bruteforce.eta_seconds_after_sample(timedelta(milliseconds=500), 100) == 5


def test_initial_spec_request_preserves_custom_full_and_noncustom_short_specs():
    assert bruteforce.initial_spec_request("Custom", [0, 1]) == bruteforce.BruteForceSpecRequest(
        mode="Custom",
        struct_indexes=(0, 1),
    )
    assert bruteforce.initial_spec_request("Brutus", [0, 1]) == bruteforce.BruteForceSpecRequest(
        mode="Brutus",
        fields=("Length", "Format"),
    )


def test_iteration_spec_request_preserves_struct_indexes_and_iter_nbr():
    assert bruteforce.iteration_spec_request("Custom", [0, 1], 3) == bruteforce.BruteForceSpecRequest(
        mode="Custom",
        struct_indexes=(0, 1),
        iter_nbr=3,
    )
    assert bruteforce.iteration_spec_request("Brutus", [0, 1], 3) == bruteforce.BruteForceSpecRequest(
        mode="Brutus",
        iter_nbr=3,
    )


def test_spec_request_kwargs_matches_legacy_getspec_keyword_shape():
    assert bruteforce.spec_request_kwargs(
        bruteforce.BruteForceSpecRequest(
            mode="Custom",
            fields=("Length", "Format"),
            struct_indexes=(0, 1),
            iter_nbr=3,
        )
    ) == {
        "Fields": ["Length", "Format"],
        "StructIndex": [0, 1],
        "IterNbr": 3,
    }
    assert bruteforce.spec_request_kwargs(bruteforce.BruteForceSpecRequest(mode="Brutus")) == {}


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


def test_chunk_crc_matches_legacy_struct_crc32():
    assert bruteforce.chunk_crc(b"gAMA", b"\x00\x01\x86\xa0") == bytes.fromhex("31e8965f")


def test_assemble_candidate_png_preserves_legacy_concatenation():
    assert bruteforce.assemble_candidate_png(b"before", b"chunk", b"after") == b"beforechunkafter"


def test_prepare_candidate_attempt_builds_crc_full_data_and_png_bytes():
    attempt = bruteforce.prepare_candidate_attempt(
        b"gAMA",
        b"\x00\x00\x00\x04",
        b"\x00\x01\x86\xa0",
        b"\x00\x01\x86\xa0",
        b"before",
        b"after",
        brute_length=True,
        brute_crc=True,
        old_crc=False,
    )

    assert attempt.checksum == bytes.fromhex("31e8965f")
    assert attempt.full_new_data == bytes.fromhex("0000000467414d41000186a031e8965f")
    assert attempt.png_bytes == b"before" + attempt.full_new_data + b"after"
    assert attempt.old_crc_match is False


def test_prepare_candidate_attempt_preserves_separate_payload_and_crc_data():
    old_crc = bruteforce.chunk_crc(b"gAMA", b"\x00\x01\x86\xa0")

    attempt = bruteforce.prepare_candidate_attempt(
        b"gAMA",
        b"\x00\x00\x00\x04",
        payload_data=b"\xaa",
        crc_data=b"\x00\x01\x86\xa0",
        before=b"",
        after=b"",
        brute_length=True,
        brute_crc=True,
        old_crc=old_crc,
    )

    assert attempt.checksum == old_crc
    assert attempt.full_new_data == b"\x00\x00\x00\x04" + b"gAMA" + b"\xaa" + old_crc
    assert attempt.png_bytes == attempt.full_new_data
    assert attempt.old_crc_match is True


def test_match_state_from_edit_window_preserves_legacy_initial_flags():
    replace_window = bruteforce.BruteForceEditWindow(
        before=b"",
        to_brute="",
        to_bryte=b"",
        after=b"",
        replace_flag=True,
    )
    insert_window = bruteforce.BruteForceEditWindow(
        before=b"",
        to_brute="",
        to_bryte=b"",
        after=b"",
        insert_flag=True,
    )

    assert bruteforce.match_state_from_edit_window(replace_window) == bruteforce.BruteForceMatchState(
        replace_flag=True,
    )
    assert bruteforce.match_state_from_edit_window(insert_window) == bruteforce.BruteForceMatchState(
        insert_flag=True,
    )


def test_mark_candidate_match_sets_bingo_and_preserves_existing_flags():
    state = bruteforce.BruteForceMatchState(replace_flag=True)

    matched = bruteforce.mark_candidate_match(state, "insert", bonus=True)

    assert matched == bruteforce.BruteForceMatchState(
        bingo=True,
        replace_flag=True,
        insert_flag=True,
        bonus=True,
    )


def test_mark_candidate_match_can_preserve_legacy_unflagged_bonus_match():
    state = bruteforce.mark_candidate_match(
        bruteforce.BruteForceMatchState(),
        bonus=True,
    )

    assert state == bruteforce.BruteForceMatchState(
        bingo=True,
        bonus=True,
    )


def test_apply_candidate_attempt_match_returns_state_and_attempt_bytes():
    attempt = bruteforce.BruteForceCandidateAttempt(
        checksum=b"crc",
        full_new_data=b"full",
        png_bytes=b"png",
        old_crc_match=True,
    )

    applied = bruteforce.apply_candidate_attempt_match(
        bruteforce.BruteForceMatchState(insert_flag=True),
        attempt,
        "remove",
        bonus=True,
    )

    assert applied == bruteforce.BruteForceAppliedAttempt(
        state=bruteforce.BruteForceMatchState(
            bingo=True,
            insert_flag=True,
            remove_flag=True,
            bonus=True,
        ),
        full_new_data=b"full",
        png_bytes=b"png",
    )


def test_apply_validated_candidate_attempt_preserves_viewer_acceptance_gate():
    attempt = bruteforce.BruteForceCandidateAttempt(
        checksum=b"crc",
        full_new_data=b"full",
        png_bytes=b"png",
        old_crc_match=False,
    )

    assert (
        bruteforce.apply_validated_candidate_attempt(
            bruteforce.BruteForceMatchState(),
            attempt,
            "insert",
            viewer_ok=False,
        )
        is None
    )
    assert bruteforce.apply_validated_candidate_attempt(
        bruteforce.BruteForceMatchState(),
        attempt,
        "insert",
        viewer_ok=True,
    ) == bruteforce.BruteForceAppliedAttempt(
        state=bruteforce.BruteForceMatchState(
            bingo=True,
            insert_flag=True,
        ),
        full_new_data=b"full",
        png_bytes=b"png",
    )


def test_apply_validated_candidate_attempt_preserves_old_crc_gate():
    mismatch = bruteforce.BruteForceCandidateAttempt(
        checksum=b"crc",
        full_new_data=b"full",
        png_bytes=b"png",
        old_crc_match=False,
    )
    match = bruteforce.BruteForceCandidateAttempt(
        checksum=b"crc",
        full_new_data=b"full",
        png_bytes=b"png",
        old_crc_match=True,
    )

    assert (
        bruteforce.apply_validated_candidate_attempt(
            bruteforce.BruteForceMatchState(),
            mismatch,
            "replace",
            old_crc=b"crc",
            viewer_ok=True,
        )
        is None
    )
    assert bruteforce.apply_validated_candidate_attempt(
        bruteforce.BruteForceMatchState(),
        match,
        "replace",
        bonus=True,
        old_crc=b"crc",
        viewer_ok=False,
    ) == bruteforce.BruteForceAppliedAttempt(
        state=bruteforce.BruteForceMatchState(
            bingo=True,
            replace_flag=True,
            bonus=True,
        ),
        full_new_data=b"full",
        png_bytes=b"png",
    )


def test_success_repair_messages_preserves_legacy_order_and_text():
    messages = bruteforce.success_repair_messages(
        bruteforce.BruteForceMatchState(
            replace_flag=True,
            insert_flag=True,
            remove_flag=True,
        ),
        b"IDAT",
        "aa\033[1;32;49mbb\033[m",
    )

    assert messages == (
        bruteforce.BruteForceRepairMessage(
            line_template="-Chunk %s has been repaired by changing those bytes:\n",
            side_note=(
                "\n-Launched Data Chunk Bruteforcer.\n-Bruteforce was successfull."
                "\n-Chunk b'IDAT' has been repaired by changing those bytes:\n"
                "aa\033[1;32;49mbb\033[m"
            ),
        ),
        bruteforce.BruteForceRepairMessage(
            line_template="-Chunk %s has been repaired by adding those bytes:\n",
            side_note=(
                "\n-Launched Data Chunk Bruteforcer.\n-Bruteforce was successfull."
                "\n-Chunk b'IDAT' has been repaired by adding those bytes:\n"
                "aa\033[1;32;49mbb\033[m"
            ),
        ),
        bruteforce.BruteForceRepairMessage(
            line_template="-Chunk %s has been repaired by removing those bytes:\n",
            side_note=(
                "\n-Launched Data Chunk Bruteforcer.\n-Bruteforce was successfull."
                "\n-Chunk b'IDAT' has been repaired by removing those bytes:\n"
                "aa\033[1;32;49mbb\033[m"
            ),
        ),
    )


def test_success_checkpoint_request_preserves_oldcrc_and_regular_toolkits():
    old_crc_request = bruteforce.success_checkpoint_request(
        old_crc=b"crc",
        chunk_name=b"IDAT",
        full_new_data_hex="001122",
        png_bytes_hex="8899",
        data_offset=10,
        chunk_length=99,
        to_brute="aabb",
        from_error="LibpngCheck",
    )

    assert old_crc_request.as_args() == (
        True,
        True,
        "SmashBruteBrawl",
        "IDAT",
        ["-Previous Crc checksum found by replacing datas"],
        "001122",
        10,
        16,
        "-Replacing Corrupted IDAT Data:\naabb\n-With:\n001122",
        "IDAT",
        "LibpngCheck",
    )

    regular_request = bruteforce.success_checkpoint_request(
        old_crc=False,
        chunk_name=b"gAMA",
        full_new_data_hex="001122",
        png_bytes_hex="8899",
        data_offset=10,
        chunk_length=99,
        to_brute="aabb",
        from_error="Relics",
    )

    assert regular_request.as_args() == (
        True,
        True,
        "SmashBruteBrawl",
        "gAMA",
        ["-Corrupted Data has been replaced"],
        "8899",
        10,
        109,
        "-Replacing Corrupted gAMA Data:\naabb\n-With:\n001122",
        "gAMA",
        "Relics",
    )


def test_failure_checkpoint_request_preserves_oldcrc_and_regular_toolkits():
    old_crc_request = bruteforce.failure_checkpoint_request(
        old_crc=b"crc",
        file="broken.png",
        chunk_name=b"IDAT",
        chunk_length=12,
        data_offset=34,
        edit_mode="Replace",
        bf_mode="TwoBytes",
        brute_crc=True,
        brute_length=False,
        from_error="LibpngCheck",
    )

    assert old_crc_request.as_args() == (
        True,
        False,
        "SmashBruteBrawl",
        "IDAT",
        ["-Bruteforcer has Failed OldCrc"],
        "broken.png",
        b"IDAT",
        12,
        34,
        "Replace",
        "TwoBytes",
        True,
        False,
        b"crc",
        "LibpngCheck",
    )

    regular_request = bruteforce.failure_checkpoint_request(
        old_crc=False,
        file="broken.png",
        chunk_name=b"gAMA",
        chunk_length=12,
        data_offset=34,
        edit_mode="Insert",
        bf_mode="Brutus",
        brute_crc=False,
        brute_length=True,
        from_error="Relics",
    )

    assert regular_request.as_args() == (
        True,
        False,
        "SmashBruteBrawl",
        "gAMA",
        ["-Bruteforcer has Failed"],
        "broken.png",
        b"gAMA",
        12,
        34,
        "Insert",
        "Brutus",
        False,
        True,
        "Relics",
    )


def test_twobytes_candidate_data_preserves_replace_insert_remove_slices():
    to_brute = "0011223344"
    brute_bytes = b"\xaa"
    needle = 2

    replace = bruteforce.twobytes_candidate_data(to_brute, brute_bytes, needle, "replace")
    insert = bruteforce.twobytes_candidate_data(to_brute, brute_bytes, needle, "insert")
    remove = bruteforce.twobytes_candidate_data(to_brute, brute_bytes, needle, "remove")

    assert replace.data == bytes.fromhex("00aa223344")
    assert replace.bonus_hex == "00aa223344"
    assert replace.length_bytes == b"\x00\x00\x00\x05"

    assert insert.data == bytes.fromhex("00aa11223344")
    assert insert.bonus_hex == "00aa11223344"
    assert insert.length_bytes == b"\x00\x00\x00\x06"

    assert remove.data == bytes.fromhex("00aa3344")
    assert remove.bonus_hex == "00aa3344"
    assert remove.length_bytes == b"\x00\x00\x00\x04"


def test_iter_twobytes_edit_kinds_preserves_idat_all_modes():
    assert bruteforce.iter_twobytes_edit_kinds("Replace", b"IDAT") == (
        "replace",
        "insert",
        "remove",
    )
    assert bruteforce.iter_twobytes_edit_kinds("Insert", b"IDAT") == (
        "replace",
        "insert",
        "remove",
    )


def test_iter_twobytes_edit_kinds_preserves_non_idat_requested_mode():
    assert bruteforce.iter_twobytes_edit_kinds("Replace", b"gAMA") == ("replace",)
    assert bruteforce.iter_twobytes_edit_kinds("Insert", b"gAMA") == ("insert",)
    assert bruteforce.iter_twobytes_edit_kinds("Remove", b"gAMA") == ("remove",)


def test_iter_twobytes_bonus_data_preserves_legacy_skip_and_byte_range():
    candidates = list(
        islice(
            bruteforce.iter_twobytes_bonus_data(
                "00aa223344",
                new_data_len=5,
                skipped_hex_offset=2,
                skipped_hex_len=2,
            ),
            3,
        )
    )

    assert candidates == [
        bytes.fromhex("00aa223344"),
        bytes.fromhex("01aa223344"),
        bytes.fromhex("02aa223344"),
    ]

    skipped_first_byte = list(
        islice(
            bruteforce.iter_twobytes_bonus_data(
                "00aa223344",
                new_data_len=5,
                skipped_hex_offset=0,
                skipped_hex_len=2,
            ),
            3,
        )
    )

    assert skipped_first_byte == [
        bytes.fromhex("0000223344"),
        bytes.fromhex("0001223344"),
        bytes.fromhex("0002223344"),
    ]


def test_twobytes_bonus_edit_kind_preserves_oldcrc_replace_bonus_quirk():
    assert bruteforce.twobytes_bonus_edit_kind(b"crc", "replace") is None
    assert bruteforce.twobytes_bonus_edit_kind(b"crc", "insert") == "insert"
    assert bruteforce.twobytes_bonus_edit_kind(False, "replace") == "replace"


def test_twobytes_scan_has_window_preserves_legacy_loop_bounds():
    state = bruteforce.BruteForceMatchState()
    matched = bruteforce.BruteForceMatchState(bingo=True)

    assert bruteforce.twobytes_scan_has_window("0011223344", 2, 0, state) is True
    assert bruteforce.twobytes_scan_has_window("0011223344", 2, 8, state) is True
    assert bruteforce.twobytes_scan_has_window("0011223344", 2, 10, state) is False
    assert bruteforce.twobytes_scan_has_window("00", 4, 0, state) is False
    assert bruteforce.twobytes_scan_has_window("0011223344", 2, 0, matched) is False


def test_twobytes_bonus_candidate_data_preserves_legacy_hex_replacement():
    assert bruteforce.twobytes_bonus_candidate_data(
        "00aa223344",
        hex_offset=4,
        replacement_byte=b"\xff",
    ) == bytes.fromhex("00aaff3344")


def test_build_candidate_bytes_preserves_brutus_format_wrapping():
    candidate = (1, 0x0203, 4, 0x0506)

    brute_bytes = bruteforce.build_candidate_bytes(
        candidate,
        ["B", "H"],
        "Brutus",
    )

    assert brute_bytes == (
        struct.pack("B", 1)
        + struct.pack("H", 0x0203)
        + struct.pack("B", 4)
        + struct.pack("H", 0x0506)
    )


def test_build_candidate_bytes_preserves_custom_struct_replacement():
    brute_bytes = bruteforce.build_candidate_bytes(
        (9,),
        ["B", "B", "B"],
        "Custom",
        struct_indexes=(1,),
        to_bryte=bytes([1, 2, 3]),
    )

    assert brute_bytes == bytes([1, 9, 3])


def test_build_candidate_bytes_preserves_custom_scalar_candidate_fallback():
    brute_bytes = bruteforce.build_candidate_bytes(
        7,
        ["B", "B"],
        "Custom",
        struct_indexes=(0,),
        to_bryte=bytes([1, 2]),
    )

    assert brute_bytes == bytes([7, 2])


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
        ("Crash resume decision", test_crash_iteration_decision_preserves_resume_skip_and_reset),
        ("ETA seconds", test_eta_seconds_after_sample_preserves_legacy_seconds_math),
        ("Initial spec request", test_initial_spec_request_preserves_custom_full_and_noncustom_short_specs),
        ("Iteration spec request", test_iteration_spec_request_preserves_struct_indexes_and_iter_nbr),
        ("Spec request kwargs", test_spec_request_kwargs_matches_legacy_getspec_keyword_shape),
        ("Build full new data", test_build_full_new_data_preserves_brutecfg_combinations),
        ("Chunk CRC", test_chunk_crc_matches_legacy_struct_crc32),
        ("Assemble candidate PNG", test_assemble_candidate_png_preserves_legacy_concatenation),
        ("Prepare candidate attempt", test_prepare_candidate_attempt_builds_crc_full_data_and_png_bytes),
        ("Prepare candidate attempt separate payload/crc", test_prepare_candidate_attempt_preserves_separate_payload_and_crc_data),
        ("Initial match state", test_match_state_from_edit_window_preserves_legacy_initial_flags),
        ("Mark candidate match", test_mark_candidate_match_sets_bingo_and_preserves_existing_flags),
        ("Mark unflagged bonus match", test_mark_candidate_match_can_preserve_legacy_unflagged_bonus_match),
        ("Apply candidate attempt match", test_apply_candidate_attempt_match_returns_state_and_attempt_bytes),
        ("Validated attempt viewer gate", test_apply_validated_candidate_attempt_preserves_viewer_acceptance_gate),
        ("Validated attempt old CRC gate", test_apply_validated_candidate_attempt_preserves_old_crc_gate),
        ("Success repair messages", test_success_repair_messages_preserves_legacy_order_and_text),
        ("Success checkpoint request", test_success_checkpoint_request_preserves_oldcrc_and_regular_toolkits),
        ("Failure checkpoint request", test_failure_checkpoint_request_preserves_oldcrc_and_regular_toolkits),
        ("TwoBytes candidate data", test_twobytes_candidate_data_preserves_replace_insert_remove_slices),
        ("TwoBytes IDAT edit kind dispatch", test_iter_twobytes_edit_kinds_preserves_idat_all_modes),
        ("TwoBytes non-IDAT edit kind dispatch", test_iter_twobytes_edit_kinds_preserves_non_idat_requested_mode),
        ("TwoBytes bonus candidates", test_iter_twobytes_bonus_data_preserves_legacy_skip_and_byte_range),
        ("TwoBytes bonus edit kind", test_twobytes_bonus_edit_kind_preserves_oldcrc_replace_bonus_quirk),
        ("TwoBytes scan window", test_twobytes_scan_has_window_preserves_legacy_loop_bounds),
        ("TwoBytes bonus candidate data", test_twobytes_bonus_candidate_data_preserves_legacy_hex_replacement),
        ("Build Brutus candidate bytes", test_build_candidate_bytes_preserves_brutus_format_wrapping),
        ("Build Custom candidate bytes", test_build_candidate_bytes_preserves_custom_struct_replacement),
        ("Build Custom scalar candidate", test_build_candidate_bytes_preserves_custom_scalar_candidate_fallback),
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
