#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import nearby
from chunklate.png import PNG_SIGNATURE, build_png_chunk


def test_parse_history_index_strips_legacy_spaces():
    assert nearby.parse_history_index(" 1 : 16 : 42 ") == nearby.HistoryChunkPosition(
        1,
        16,
        42,
    )


def test_find_history_chunk_position_returns_first_matching_chunk():
    position = nearby.find_history_chunk_position(
        [b"IHDR", b"IDAT"],
        ["0:16:42", "1:42:90"],
        b"IDAT",
    )

    assert position == nearby.HistoryChunkPosition(1, 42, 90)
    assert nearby.find_history_chunk_position([b"IHDR"], ["0:16:42"], b"PLTE") is None


def test_initial_search_needle_preserves_known_and_unknown_chunk_paths():
    assert nearby.initial_search_needle(
        chunk_type=b"IDAT",
        known_chunks=(b"IHDR", b"IDAT"),
        current_length_offset=100,
        chunks_history=[],
        chunks_history_index=[],
        last_chunk_type=b"IHDR",
    ) == 116

    assert nearby.initial_search_needle(
        chunk_type=b"fake",
        known_chunks=(b"IHDR", b"IDAT"),
        current_length_offset=100,
        chunks_history=[b"IHDR"],
        chunks_history_index=["0:24:60"],
        last_chunk_type=b"IHDR",
    ) == 40

    assert nearby.initial_search_needle(
        chunk_type=b"fake",
        known_chunks=(b"IHDR", b"IDAT"),
        current_length_offset=100,
        chunks_history=[],
        chunks_history_index=[],
        last_chunk_type=b"IHDR",
    ) == 116


def test_find_extra_bytes_before_chunk_uses_crc_checked_candidate():
    data = PNG_SIGNATURE + b"XX" + build_png_chunk(b"IHDR", b"\x00" * 13)
    candidate = nearby.find_extra_bytes_before_chunk(
        data,
        current_offset=len(PNG_SIGNATURE),
        candidates=(b"IHDR",),
    )

    assert candidate == nearby.ExtraBytesCandidate(
        extra_bytes=2,
        chunk_type=b"IHDR",
        current_offset=len(PNG_SIGNATURE),
    )
    assert nearby.extra_bytes_solved_message(candidate, b"PNG") == (
        "-Found 2 extra byte(s) before Chunk[IHDR] after Chunk[PNG] at offset: 0x8"
    )


def test_find_extra_bytes_before_chunk_ignores_unknown_or_bad_crc_candidates():
    good_data = PNG_SIGNATURE + b"X" + build_png_chunk(b"IHDR", b"\x00" * 13)
    bad_crc = bytearray(good_data)
    bad_crc[-1] ^= 1

    assert nearby.find_extra_bytes_before_chunk(
        good_data,
        current_offset=len(PNG_SIGNATURE),
        candidates=(b"IDAT",),
    ) is None
    assert nearby.find_extra_bytes_before_chunk(
        bytes(bad_crc),
        current_offset=len(PNG_SIGNATURE),
        candidates=(b"IHDR",),
    ) is None


def test_relocate_missing_chunk_matches_legacy_rubber_tape():
    assert nearby.relocate_missing_chunk(
        "aaaabbbbccccdddd",
        source_start=4,
        source_end=8,
        target_start=12,
    ) == "aaaaccccddddbbbb"


def test_null_find_preserves_legacy_default_search():
    assert nearby.null_find("aabb00cc") == 4
    assert nearby.null_find("aabbcc") is False


def test_null_find_preserves_custom_step_search():
    assert nearby.null_find("aabbccdd", "cc") == 4
    assert nearby.null_find("aabbccdd", "bb") == 2
    assert nearby.null_find("aabbccdd", "bbcc") is False


def test_known_chunk_length_repair_matches_legacy_offsets_and_messages():
    repair = nearby.known_chunk_length_repair(
        display_chunk=b"IDAT",
        old_length="ffffffff",
        current_length_offset=32,
        current_length_offset_hex="0x10",
        current_data_offset_byte=24,
        found_chunk=b"IEND",
        found_chunk_type_offset=80,
    )

    assert repair.fixed_length == "00000008"
    assert repair.replace_start == 32
    assert repair.replace_end == 40
    assert repair.print_message == (
        "-Found Chunk[b'IDAT'] has Wrong length at offset: 0x10\n"
        "-Replaced with: 00000008 old value was: ffffffff"
    )
    assert repair.solved_message == (
        "-Found Chunk[b'IDAT'] has Wrong length at offset: 0x10\n"
        "-Found next chunk: b'IEND' at: 0x28\n"
        "-Replaced with: 00000008 old value was: ffffffff"
    )


def test_unknown_chunk_length_repair_uses_previous_history_chunk():
    repair = nearby.unknown_chunk_length_repair(
        data_hex="00" * 40 + "0000000d" + "11" * 80,
        display_chunk=b"fake",
        checkpoint_length_offset=12,
        chunks_history=[b"IHDR"],
        chunks_history_index=["0:80:120"],
        last_chunk_type=b"IHDR",
        found_chunk=b"IDAT",
        found_chunk_type_offset=160,
    )

    assert repair is not None
    assert repair.display_chunk == b"IHDR"
    assert repair.print_offset == 152
    assert repair.length_offset == 80
    assert repair.old_length == "0000000d"
    assert repair.fixed_length == "00000018"
    assert repair.replace_start == 80
    assert repair.replace_end == 88


def test_length_repair_clamps_negative_lengths_to_zero():
    repair = nearby.known_chunk_length_repair(
        display_chunk=b"IDAT",
        old_length="ffffffff",
        current_length_offset=32,
        current_length_offset_hex="0x10",
        current_data_offset_byte=80,
        found_chunk=b"IEND",
        found_chunk_type_offset=64,
    )

    assert repair.fixed_length == "00000000"


def test_unknown_chunk_length_repair_returns_none_without_previous_history():
    assert nearby.unknown_chunk_length_repair(
        data_hex="00" * 20,
        display_chunk=b"fake",
        checkpoint_length_offset=12,
        chunks_history=[],
        chunks_history_index=[],
        last_chunk_type=b"IHDR",
        found_chunk=b"IDAT",
        found_chunk_type_offset=160,
    ) is None


def main():
    checks = [
        ("history index parse", test_parse_history_index_strips_legacy_spaces),
        ("history position lookup", test_find_history_chunk_position_returns_first_matching_chunk),
        ("initial search needle", test_initial_search_needle_preserves_known_and_unknown_chunk_paths),
        ("extra bytes candidate", test_find_extra_bytes_before_chunk_uses_crc_checked_candidate),
        ("extra bytes ignored candidates", test_find_extra_bytes_before_chunk_ignores_unknown_or_bad_crc_candidates),
        ("relocate missing chunk", test_relocate_missing_chunk_matches_legacy_rubber_tape),
        ("null find default", test_null_find_preserves_legacy_default_search),
        ("null find custom", test_null_find_preserves_custom_step_search),
        ("known chunk length repair", test_known_chunk_length_repair_matches_legacy_offsets_and_messages),
        ("unknown chunk length repair", test_unknown_chunk_length_repair_uses_previous_history_chunk),
        ("negative length clamp", test_length_repair_clamps_negative_lengths_to_zero),
        ("missing previous history", test_unknown_chunk_length_repair_returns_none_without_previous_history),
    ]

    print("Running nearby chunk tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"nearby chunk tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
