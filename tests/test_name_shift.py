#!/usr/bin/env python3
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


def main():
    checks = [
        ("Current offset", test_find_shifted_chunk_name_detects_current_offset),
        ("Before expected offset", test_find_shifted_chunk_name_detects_chunk_before_expected_offset),
        ("After expected offset", test_find_shifted_chunk_name_detects_chunk_after_expected_offset),
        ("Unknown chunk", test_find_shifted_chunk_name_returns_none_without_known_chunk),
    ]

    print("Running name shift tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"name shift tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
