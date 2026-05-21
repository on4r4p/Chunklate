#!/usr/bin/env python3
import binascii
import struct
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import palette_ui


class FakeSlider:
    def __init__(self):
        self.var = self
        self.value = None

    def set(self, value):
        self.value = value


def test_palette_values_to_bytes_skips_empty_legacy_entries():
    assert palette_ui.palette_values_to_bytes(["empty", 0, 0x112233]) == bytes.fromhex("000000112233")


def test_build_plte_chunk_adds_length_type_and_crc():
    data = bytes.fromhex("000000ffffff")
    chunk = palette_ui.build_plte_chunk(data)

    assert chunk[:4] == len(data).to_bytes(4, "big")
    assert chunk[4:8] == b"PLTE"
    assert chunk[8:-4] == data
    assert chunk[-4:] == struct.pack("!I", binascii.crc32(b"PLTE" + data))


def test_build_palette_png_combines_before_palette_after():
    png = palette_ui.build_palette_png(
        bytes.fromhex("aaaa"),
        [0],
        bytes.fromhex("bbbb"),
    )

    assert png.startswith(bytes.fromhex("aaaa00000003504c5445000000"))
    assert png.endswith(bytes.fromhex("bbbb"))


def test_set_palette_value_preserves_empty_sentinel():
    values = ["empty", "empty"]

    palette_ui.set_palette_value(values, 0, "123")
    palette_ui.set_palette_value(values, 1, "-1")

    assert values == ["123", "empty"]


def test_apply_color_table_updates_values_and_sliders():
    values = ["empty", "empty"]
    sliders = [FakeSlider(), FakeSlider()]

    palette_ui.apply_color_table(values, sliders, ["000001", "0000ff"])

    assert values == [1, 255]
    assert [slider.value for slider in sliders] == [1, 255]


def test_random_palette_values_uses_injected_random_source():
    values = ["empty", "empty"]
    sliders = [FakeSlider(), FakeSlider()]
    generated = iter([7, 9])

    palette_ui.random_palette_values(values, sliders, lambda start, end: next(generated))

    assert values == [7, 9]
    assert [slider.value for slider in sliders] == [7, 9]


def test_save_checkpoint_preserves_legacy_cancel_and_save_payloads():
    cancel = palette_ui.save_checkpoint(
        cancel=True,
        palette_values=["empty"],
        wanabyte=b"png",
        chunk_length=12,
        data_offset=4,
        from_error="source",
    )
    saved = palette_ui.save_checkpoint(
        cancel=False,
        palette_values=["empty", 0, 1],
        wanabyte=b"png",
        chunk_length=12,
        data_offset=4,
        from_error="source",
    )

    assert cancel.error is True
    assert cancel.fixed is False
    assert cancel.function == "Tk_Save_Plte"
    assert cancel.chunk == b"PLTE"
    assert cancel.infos == ("-Manually modify PLTE datas has been canceled by user.",)
    assert cancel.toolkit == (
        "706e67",
        4,
        16,
        "-Manually modify PLTE datas has been canceled by user.",
        b"PLTE",
        "source",
    )

    assert saved.error is True
    assert saved.fixed is True
    assert saved.infos == ("-PLTE Data has been replaced manually.",)
    assert saved.toolkit == (
        "706e67",
        4,
        16,
        "-PLTE Data has been modified with 255 new palettes.",
        b"PLTE",
        "source",
    )


def main():
    checks = [
        ("Palette bytes skip empty entries", test_palette_values_to_bytes_skips_empty_legacy_entries),
        ("PLTE chunk builder", test_build_plte_chunk_adds_length_type_and_crc),
        ("Palette PNG builder", test_build_palette_png_combines_before_palette_after),
        ("Set palette value", test_set_palette_value_preserves_empty_sentinel),
        ("Apply color table", test_apply_color_table_updates_values_and_sliders),
        ("Random palette values", test_random_palette_values_uses_injected_random_source),
        ("Save CheckPoint payload", test_save_checkpoint_preserves_legacy_cancel_and_save_payloads),
    ]

    print("Running palette UI helper tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"palette UI helper tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
