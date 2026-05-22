#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import sorting


def test_digit_or_text_preserves_legacy_conversion():
    assert sorting.digit_or_text("12") == 12
    assert sorting.digit_or_text("001") == 1
    assert sorting.digit_or_text("IHDR") == "IHDR"
    assert sorting.digit_or_text("") == ""


def test_natural_sort_key_preserves_legacy_split_digits():
    assert sorting.natural_sort_key("IDAT12abc3") == ["IDAT", 12, "abc", 3, ""]
    assert sorting.natural_sort_key("abc") == ["abc"]


def test_natural_sort_orders_numbered_names():
    names = ["chunk10", "chunk2", "chunk1", "chunk01"]

    assert sorted(names, key=sorting.natural_sort_key) == [
        "chunk1",
        "chunk01",
        "chunk2",
        "chunk10",
    ]


def main():
    checks = [
        ("Digit conversion", test_digit_or_text_preserves_legacy_conversion),
        ("Natural sort key", test_natural_sort_key_preserves_legacy_split_digits),
        ("Natural sort ordering", test_natural_sort_orders_numbered_names),
    ]

    print("Running sorting tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"sorting tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
