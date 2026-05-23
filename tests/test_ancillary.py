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


def test_semantic_labels_preserve_legacy_report_order():
    assert ancillary.semantic_labels(ancillary.chunk_name_semantics("IHDR")) == (
        ("I", "Critical"),
        ("H", "Private"),
        ("D", "Conform to PNG specifications"),
        ("R", "Unsafe to Copy"),
    )
    assert ancillary.semantic_labels(ancillary.chunk_name_semantics("gAMa")) == (
        ("g", "Not Critical"),
        ("A", "Private"),
        ("M", "Conform to PNG specifications"),
        ("a", "Safe to Copy"),
    )


def test_semantic_labels_returns_empty_for_invalid_name():
    assert ancillary.semantic_labels(ancillary.chunk_name_semantics("AB1D")) == ()


def main():
    checks = [
        ("case bits", test_chunk_name_semantics_preserves_legacy_case_bits),
        ("mixed case bits", test_chunk_name_semantics_handles_mixed_case_bits),
        ("stop on non-letter", test_chunk_name_semantics_stops_on_non_letter),
        ("semantic report labels", test_semantic_labels_preserve_legacy_report_order),
        ("semantic labels invalid", test_semantic_labels_returns_empty_for_invalid_name),
    ]

    print("Running ancillary tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"ancillary tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
