#!/usr/bin/env python3
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import error_log


def test_error_log_path_uses_legacy_filename(tmp_path):
    assert error_log.error_log_path(str(tmp_path)) == str(tmp_path / "Chunklate_Errors.log")


def test_format_error_log_entry_preserves_legacy_layout():
    now = datetime(2026, 5, 22, 10, 11, 12)

    assert error_log.format_error_log_entry("boom", now=now) == "2026-05-22 10:11:12\nboom\n"


def test_format_exception_message_preserves_legacy_layout():
    assert error_log.format_exception_message(
        "Chunklate.py",
        ValueError,
        "CheckLength",
        123,
        "bad length",
    ) == (
        "!!\n"
        "File: Chunklate.py has encounter a <class 'ValueError'> error in CheckLength() at line 123\n"
        "Error Message:bad length\n"
        "!!"
    )


def test_append_error_log_writes_and_appends(tmp_path):
    first = datetime(2026, 5, 22, 10, 11, 12)
    second = datetime(2026, 5, 22, 10, 11, 13)

    path = error_log.append_error_log("first", str(tmp_path), now=first)
    error_log.append_error_log("second", str(tmp_path), now=second)

    assert path == str(tmp_path / "Chunklate_Errors.log")
    assert Path(path).read_text() == (
        "2026-05-22 10:11:12\nfirst\n"
        "2026-05-22 10:11:13\nsecond\n"
    )


def main():
    tmp = __import__("tempfile").TemporaryDirectory()
    tmpdir = Path(tmp.name)
    checks = [
        ("Log path", lambda: test_error_log_path_uses_legacy_filename(tmpdir)),
        ("Entry format", test_format_error_log_entry_preserves_legacy_layout),
        ("Exception format", test_format_exception_message_preserves_legacy_layout),
        ("Append log", lambda: test_append_error_log_writes_and_appends(tmpdir)),
    ]

    try:
        print("Running error log tests")
        for label, check in checks:
            print(f"  - {label} ... ", end="", flush=True)
            check()
            print("ok")

        print(f"error log tests passed ({len(checks)} checks)")
    finally:
        tmp.cleanup()


if __name__ == "__main__":
    main()
