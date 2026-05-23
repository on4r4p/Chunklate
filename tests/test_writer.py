#!/usr/bin/env python3
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import writer


def test_prepare_clone_write_uses_legacy_target_and_next_count(tmp_path):
    plan = writer.prepare_clone_write(
        "sample.png",
        str(tmp_path),
        "89504e47",
        save_count=2,
        max_saves=4,
    )

    assert plan.target.name == "sample.0_Fixed.png"
    assert plan.target.directory == str(tmp_path / "Folder_sample")
    assert plan.target.path == str(tmp_path / "Folder_sample" / "sample.0_Fixed.png")
    assert plan.data == b"\x89PNG"
    assert plan.save_count == 3
    assert plan.max_saves_reached is False


def test_prepare_clone_write_marks_max_saves_reached(tmp_path):
    plan = writer.prepare_clone_write(
        "sample.png",
        str(tmp_path),
        b"\x89PNG",
        save_count=1,
        max_saves=2,
    )

    assert plan.save_count == 2
    assert plan.max_saves_reached is True


def test_write_clone_writes_to_next_available_target(tmp_path):
    first = writer.write_clone(
        "sample.png",
        str(tmp_path),
        b"first",
        save_count=0,
        max_saves=None,
    )
    second = writer.write_clone(
        "sample.png",
        str(tmp_path),
        b"second",
        save_count=first.save_count,
        max_saves=None,
    )

    assert Path(first.target.path).read_bytes() == b"first"
    assert Path(second.target.path).read_bytes() == b"second"
    assert first.target.name == "sample.0_Fixed.png"
    assert second.target.name == "sample.1_Fixed.png"
    assert second.save_count == 2


def test_remove_hex_range_preserves_legacy_removechunk_slice():
    assert writer.remove_hex_range("aaaabbbbcccc", 4, 8) == "aaaacccc"


def test_replace_hex_range_preserves_legacy_saveclone_slice():
    assert writer.replace_hex_range("aaaabbbbcccc", "XXXX", 4, 8) == "aaaaXXXXcccc"


def main():
    tmpdir = tempfile.TemporaryDirectory()
    tmp_path = Path(tmpdir.name)
    checks = [
        ("Prepare clone write", lambda: test_prepare_clone_write_uses_legacy_target_and_next_count(tmp_path)),
        ("Max saves reached", lambda: test_prepare_clone_write_marks_max_saves_reached(tmp_path)),
        ("Write clone", lambda: test_write_clone_writes_to_next_available_target(tmp_path)),
        ("Remove hex range", test_remove_hex_range_preserves_legacy_removechunk_slice),
        ("Replace hex range", test_replace_hex_range_preserves_legacy_saveclone_slice),
    ]

    try:
        print("Running writer tests")
        for label, check in checks:
            print(f"  - {label} ... ", end="", flush=True)
            check()
            print("ok")

        print(f"writer tests passed ({len(checks)} checks)")
    finally:
        tmpdir.cleanup()


if __name__ == "__main__":
    main()
