#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import history


def test_append_byte_history_preserves_legacy_append():
    bytes_history = []

    history.append_byte_history(bytes_history, 12)
    history.append_byte_history(bytes_history, "ff")

    assert bytes_history == [12, "ff"]


def main():
    checks = [
        ("Append byte history", test_append_byte_history_preserves_legacy_append),
    ]

    print("Running history tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"history tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
