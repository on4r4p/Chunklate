#!/usr/bin/env python3
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import output, writer


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


def test_prepare_clone_write_reuses_existing_clone_with_same_sha(tmp_path):
    first = writer.write_clone(
        "sample.png",
        str(tmp_path),
        b"same",
        save_count=0,
        max_saves=None,
    )

    second = writer.prepare_clone_write(
        "sample.png",
        str(tmp_path),
        b"same",
        save_count=first.save_count,
        max_saves=None,
    )

    assert second.target == first.target
    assert second.save_count == first.save_count
    assert second.max_saves_reached is False
    assert second.already_exists is True
    assert second.sha256 == writer.clone_sha256(b"same")


def test_prepare_clone_write_increments_when_existing_name_has_different_sha(tmp_path):
    writer.write_clone(
        "sample.png",
        str(tmp_path),
        b"old",
        save_count=0,
        max_saves=None,
    )

    plan = writer.prepare_clone_write(
        "sample.png",
        str(tmp_path),
        b"new",
        save_count=1,
        max_saves=None,
    )

    assert plan.target.name == "sample.1_Fixed.png"
    assert plan.already_exists is False


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


def test_write_clone_skips_existing_clone_with_same_sha(tmp_path):
    first = writer.write_clone(
        "sample.png",
        str(tmp_path),
        b"same",
        save_count=0,
        max_saves=None,
    )
    second = writer.write_clone(
        "sample.png",
        str(tmp_path),
        b"same",
        save_count=first.save_count,
        max_saves=None,
    )

    assert second.target == first.target
    assert second.save_count == first.save_count
    assert second.already_exists is True
    assert Path(first.target.path).read_bytes() == b"same"
    assert not (tmp_path / "Folder_sample" / "sample.1_Fixed.png").exists()


def test_write_prepared_clone_noops_when_target_has_same_sha(tmp_path):
    target = output.next_clone_target("sample.png", str(tmp_path))
    Path(target.path).write_bytes(b"same")
    plan = writer.CloneWritePlan(
        target=target,
        data=b"same",
        save_count=1,
        sha256=writer.clone_sha256(b"same"),
    )

    writer.write_prepared_clone(plan)

    assert Path(target.path).read_bytes() == b"same"


def test_write_prepared_clone_refuses_to_overwrite_different_sha(tmp_path):
    target = output.next_clone_target("sample.png", str(tmp_path))
    Path(target.path).write_bytes(b"old")
    plan = writer.CloneWritePlan(
        target=target,
        data=b"new",
        save_count=1,
        sha256=writer.clone_sha256(b"new"),
    )

    try:
        writer.write_prepared_clone(plan)
    except FileExistsError as exc:
        assert "different SHA" in str(exc)
    else:
        raise AssertionError("write_prepared_clone should not overwrite a different clone")

    assert Path(target.path).read_bytes() == b"old"


def test_remove_hex_range_preserves_legacy_removechunk_slice():
    assert writer.remove_hex_range("aaaabbbbcccc", 4, 8) == "aaaacccc"


def test_replace_hex_range_preserves_legacy_saveclone_slice():
    assert writer.replace_hex_range("aaaabbbbcccc", "XXXX", 4, 8) == "aaaaXXXXcccc"


def main():
    def with_tmp_path(check):
        with tempfile.TemporaryDirectory() as tmpdir:
            check(Path(tmpdir))

    checks = [
        ("Prepare clone write", lambda: with_tmp_path(test_prepare_clone_write_uses_legacy_target_and_next_count)),
        ("Max saves reached", lambda: with_tmp_path(test_prepare_clone_write_marks_max_saves_reached)),
        ("Reuse same SHA clone", lambda: with_tmp_path(test_prepare_clone_write_reuses_existing_clone_with_same_sha)),
        ("Increment different SHA clone", lambda: with_tmp_path(test_prepare_clone_write_increments_when_existing_name_has_different_sha)),
        ("Write clone", lambda: with_tmp_path(test_write_clone_writes_to_next_available_target)),
        ("Skip same SHA clone", lambda: with_tmp_path(test_write_clone_skips_existing_clone_with_same_sha)),
        ("Prepared same SHA no-op", lambda: with_tmp_path(test_write_prepared_clone_noops_when_target_has_same_sha)),
        ("Prepared different SHA refusal", lambda: with_tmp_path(test_write_prepared_clone_refuses_to_overwrite_different_sha)),
        ("Remove hex range", test_remove_hex_range_preserves_legacy_removechunk_slice),
        ("Replace hex range", test_replace_hex_range_preserves_legacy_saveclone_slice),
    ]

    print("Running writer tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"writer tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
