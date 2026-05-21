#!/usr/bin/env python3
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import output


def test_clone_folder_matches_legacy_folder_name(tmp_path):
    folder = output.clone_folder("/somewhere/sample.png", str(tmp_path))

    assert folder == str(tmp_path / "Folder_sample")


def test_next_clone_target_uses_next_available_fixed_name(tmp_path):
    first = output.next_clone_target("sample.png", str(tmp_path))
    Path(first.path).write_bytes(b"first")

    second = output.next_clone_target("sample.png", str(tmp_path))

    assert first.name == "sample.0_Fixed.png"
    assert second.name == "sample.1_Fixed.png"
    assert Path(second.directory).is_dir()


def test_clone_bytes_accepts_hex_and_bytes():
    assert output.clone_bytes("89504e47") == b"\x89PNG"
    assert output.clone_bytes(b"\x89PNG") == b"\x89PNG"
    assert output.clone_bytes(bytearray(b"\x89PNG")) == b"\x89PNG"


def test_write_clone_writes_png_bytes(tmp_path):
    target = output.next_clone_target("sample.png", str(tmp_path))

    output.write_clone(target, "89504e47")

    assert Path(target.path).read_bytes() == b"\x89PNG"


def main():
    tmpdir = tempfile.TemporaryDirectory()
    tmp_path = Path(tmpdir.name)
    checks = [
        ("Clone folder matches legacy folder name", lambda: test_clone_folder_matches_legacy_folder_name(tmp_path)),
        ("Clone target uses next fixed name", lambda: test_next_clone_target_uses_next_available_fixed_name(tmp_path)),
        ("Clone bytes accepts hex and bytes", test_clone_bytes_accepts_hex_and_bytes),
        ("Write clone writes PNG bytes", lambda: test_write_clone_writes_png_bytes(tmp_path)),
    ]

    try:
        print("Running output tests")
        for label, check in checks:
            print(f"  - {label} ... ", end="", flush=True)
            check()
            print("ok")

        print(f"output tests passed ({len(checks)} checks)")
    finally:
        tmpdir.cleanup()


if __name__ == "__main__":
    main()
