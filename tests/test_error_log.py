#!/usr/bin/env python3
import sys
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace


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


def test_format_exception_from_exc_info_uses_traceback_location():
    try:
        raise ValueError("bad length")
    except ValueError as exc:
        rendered = error_log.format_exception_from_exc_info(
            sys.exc_info(),
            "CheckLength",
            exc,
        )

    assert "File: test_error_log.py has encounter a <class 'ValueError'> error in CheckLength()" in rendered
    assert "Error Message:bad length" in rendered


def test_format_exception_from_exc_info_requires_traceback():
    try:
        error_log.format_exception_from_exc_info((ValueError, ValueError("x"), None), "fn", "x")
    except ValueError as exc:
        assert str(exc) == "exc_info traceback is required"
    else:
        raise AssertionError("traceback-less exc_info should fail")


def test_append_error_log_writes_and_appends(tmp_path):
    first = datetime(2026, 5, 22, 10, 11, 12)
    second = datetime(2026, 5, 22, 10, 11, 13)

    path = error_log.append_error_log("first", str(tmp_path), now=first)
    error_log.append_error_log("second", str(tmp_path), now=second)

    assert path == str(tmp_path / "Chunklate_Errors.log")
    assert Path(path).read_text(encoding="utf-8") == (
        "2026-05-22 10:11:12\nfirst\n"
        "2026-05-22 10:11:13\nsecond\n"
    )


def test_append_repair_folder_error_log_writes_inside_clone_folder(tmp_path):
    path = error_log.append_repair_folder_error_log(
        "boom",
        "Flag.png",
        str(tmp_path),
        now=datetime(2026, 5, 22, 10, 11, 12),
    )

    assert path == str(tmp_path / "Folder_Flag" / "Chunklate_Errors.log")
    assert Path(path).read_text(encoding="utf-8") == "2026-05-22 10:11:12\nboom\n"


def test_append_error_log_from_namespace_writes_and_records_side_note(tmp_path):
    side_notes = []
    namespace = {
        "sys": SimpleNamespace(path=[str(tmp_path)]),
        "FILE_Origin": "Flag.png",
        "FILE_DIR": str(tmp_path),
        "SideNotes": side_notes,
        "Betterror": lambda error, name: None,
        "inspect": SimpleNamespace(stack=lambda: [SimpleNamespace(function="test")]),
    }

    error_log.append_error_log_from_namespace(namespace, "boom")

    assert side_notes == ["boom"]
    assert (tmp_path / "Chunklate_Errors.log").read_text(encoding="utf-8").endswith("boom\n")
    assert (
        tmp_path / "Folder_Flag" / "Chunklate_Errors.log"
    ).read_text(encoding="utf-8").endswith("boom\n")


def test_betterror_from_namespace_formats_prints_and_delegates_to_error_log():
    calls = []
    namespace = {
        "sys": sys,
        "inspect": SimpleNamespace(stack=lambda: [SimpleNamespace(function="test")]),
        "DEBUG": True,
        "PRINT": lambda message: calls.append(("print", message)),
        "Error_Log": lambda message: calls.append(("error_log", message)) or "logged",
        "Betterror": lambda error, name: calls.append(("betterror", str(error), name)),
    }

    try:
        raise RuntimeError("bad")
    except RuntimeError as exc:
        result = error_log.betterror_from_namespace(namespace, exc, "Fn")

    assert result == "logged"
    assert calls[0][0] == "print"
    assert "File: test_error_log.py has encounter a <class 'RuntimeError'> error in Fn()" in calls[0][1]
    assert calls[1][0] == "error_log"


def main():
    tmp = __import__("tempfile").TemporaryDirectory()
    tmpdir = Path(tmp.name)
    checks = [
        ("Log path", lambda: test_error_log_path_uses_legacy_filename(tmpdir)),
        ("Entry format", test_format_error_log_entry_preserves_legacy_layout),
        ("Exception format", test_format_exception_message_preserves_legacy_layout),
        ("Exception from exc_info", test_format_exception_from_exc_info_uses_traceback_location),
        ("Exception from exc_info requires traceback", test_format_exception_from_exc_info_requires_traceback),
        ("Append log", lambda: test_append_error_log_writes_and_appends(tmpdir)),
        ("Append repair folder log", lambda: test_append_repair_folder_error_log_writes_inside_clone_folder(tmpdir)),
        ("Append log namespace", lambda: test_append_error_log_from_namespace_writes_and_records_side_note(tmpdir)),
        ("Betterror namespace", test_betterror_from_namespace_formats_prints_and_delegates_to_error_log),
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
