#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import palette, palette_runtime


def test_manual_palette_after_index_preserves_legacy_expression():
    assert palette_runtime.manual_palette_after_index(8, 20) == 20
    assert palette_runtime.manual_palette_after_index(0, 20) == 20


def test_manual_palette_slices_preserve_legacy_before_after_cut():
    before, after = palette_runtime.manual_palette_slices("0011223344556677", 4, 10)

    assert before == bytes.fromhex("0011")
    assert after == bytes.fromhex("556677")


def test_create_manual_palette_session_builds_initial_png_and_state():
    calls = []

    def guess_palette_count(before, after):
        calls.append((before, after))
        return 3

    session = palette_runtime.create_manual_palette_session(
        data_hex="0011223344556677",
        data_offset=4,
        chunk_length=10,
        chunk_name=b"PLTE",
        guess_palette_count=guess_palette_count,
    )

    assert calls == [(bytes.fromhex("0011"), bytes.fromhex("556677"))]
    assert session.before == bytes.fromhex("0011")
    assert session.after == bytes.fromhex("556677")
    assert session.wanabyte == palette.initial_manual_palette_png(session.before, b"PLTE", session.after)
    assert session.palette_count == 3
    assert session.state.values == ["empty", "empty", "empty"]
    assert session.state.wanabyte == session.wanabyte


def test_manual_palette_full_new_data_returns_chunk_bytes_between_slices():
    session = palette_runtime.ManualPaletteSession(
        before=b"aa",
        after=b"zz",
        wanabyte=b"aaPLTEzz",
        palette_count=1,
        state=None,
    )
    no_after = palette_runtime.ManualPaletteSession(
        before=b"aa",
        after=b"",
        wanabyte=b"aaPLTE",
        palette_count=1,
        state=None,
    )

    assert palette_runtime.manual_palette_full_new_data(session) == b"PLTE"
    assert palette_runtime.manual_palette_full_new_data(no_after) == b"PLTE"


def main():
    checks = [
        ("After index", test_manual_palette_after_index_preserves_legacy_expression),
        ("Before/after slices", test_manual_palette_slices_preserve_legacy_before_after_cut),
        ("Manual palette session", test_create_manual_palette_session_builds_initial_png_and_state),
        ("Full new data", test_manual_palette_full_new_data_returns_chunk_bytes_between_slices),
    ]

    print("Running palette runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"palette runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
