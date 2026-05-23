#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import ancillary


def test_chunk_name_semantics_preserves_legacy_case_bits():
    semantics = ancillary.chunk_name_semantics("IHDR")

    assert semantics.name == "IHDR"
    assert semantics.letters == ("I", "H", "D", "R")
    assert semantics.follows_naming is True
    assert semantics.is_critical is True
    assert semantics.is_private is True
    assert semantics.is_reserved_valid is True
    assert semantics.is_unsafe_to_copy is True


def test_chunk_name_semantics_handles_mixed_case_bits():
    semantics = ancillary.chunk_name_semantics("gAMA")

    assert semantics.follows_naming is True
    assert semantics.is_critical is False
    assert semantics.is_private is True
    assert semantics.is_reserved_valid is True
    assert semantics.is_unsafe_to_copy is True


def test_chunk_name_semantics_stops_on_non_letter():
    semantics = ancillary.chunk_name_semantics("AB1D")

    assert semantics.name == "AB1D"
    assert semantics.letters == ("A", "B")
    assert semantics.follows_naming is False


def main():
    checks = [
        ("case bits", test_chunk_name_semantics_preserves_legacy_case_bits),
        ("mixed case bits", test_chunk_name_semantics_handles_mixed_case_bits),
        ("stop on non-letter", test_chunk_name_semantics_stops_on_non_letter),
    ]

    print("Running ancillary tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"ancillary tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
