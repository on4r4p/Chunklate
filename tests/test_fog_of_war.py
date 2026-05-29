#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import fog_of_war


def color(name, value):
    return f"<{name}:{value}>"


def test_fog_of_war_keeps_clean_idat_compaction():
    fog_map = fog_of_war.build_map(
        [b"PNG", b"IHDR", b"IDAT", b"IDAT"],
        b"IDAT",
        data_hex="00" * 128,
        current_offset=32,
        error=False,
    )

    rendered = fog_of_war.render(fog_map, color=color)

    assert "<green:[IDATx2]>" in rendered
    assert "<yellow:[>IDAT<]>" in rendered
    assert "<red:" not in rendered


def test_fog_of_war_merges_current_idat_error_with_seen_idats():
    fog_map = fog_of_war.build_map(
        [b"PNG", b"IHDR", b"bKGD", b"IDAT", b"IDAT"],
        b"IDAT",
        data_hex="00" * 128,
        current_offset=32,
        error=True,
        idat_wrong_crc_count=2,
    )

    rendered = fog_of_war.render(fog_map, color=color)

    assert "<green:[IDAT><white::><red:2><green:/><yellow:3><green:]>" in rendered
    assert "<green:[IDATx2]>" not in rendered
    assert "<red:[!IDAT!]>" not in rendered


def test_fog_of_war_uses_green_total_when_idat_is_not_current():
    fog_map = fog_of_war.build_map(
        [b"PNG", b"IHDR", b"IDAT", b"IDAT", b"IDAT"],
        b"tEXt",
        data_hex="00" * 128,
        current_offset=32,
        error=False,
        idat_wrong_crc_count=2,
    )

    rendered = fog_of_war.render(fog_map, color=color)

    assert "<green:[IDAT><white::><red:2><green:/><green:3><green:]>" in rendered
    assert "<yellow:3>" not in rendered


def test_fog_of_war_marks_first_current_idat_error():
    fog_map = fog_of_war.build_map(
        [b"PNG", b"IHDR"],
        b"IDAT",
        data_hex="00" * 128,
        current_offset=32,
        error=True,
        idat_wrong_crc_count=1,
    )

    rendered = fog_of_war.render(fog_map, color=color)

    assert "<green:[IDAT><white::><red:1><green:/><yellow:1><green:]>" in rendered
    assert "<red:[!IDAT!]>" not in rendered


def test_fog_of_war_keeps_unrepaired_seen_chunk_red():
    fog_map = fog_of_war.build_map(
        [b"PNG", b"IHDR", b"gAMA", b"IDAT", b"bKGD"],
        b"IEND",
        data_hex="00" * 128,
        current_offset=64,
        error=False,
        bad_chunk_labels=("bKGD",),
    )

    rendered = fog_of_war.render(fog_map, color=color)

    assert "<red:[!bKGD!]>" in rendered
    assert "<green:[bKGD]>" not in rendered
    assert "<yellow:[>IEND<]>" in rendered


def test_fog_of_war_renders_pending_next_chunk_after_current():
    fog_map = fog_of_war.build_map(
        [b"PNG", b"IHDR", b"gAMA"],
        b"IDAT",
        data_hex="00" * 128,
        current_offset=64,
        error=False,
        preview_chunk=b"bKGD",
    )

    rendered = fog_of_war.render(fog_map, color=color)

    assert rendered.index("<yellow:[>IDAT<]>") < rendered.index("<blue:[bKGD?]>")
    assert "<yellow:[>bKGD<]>" not in rendered
    assert "<red:[!bKGD!]>" not in rendered


def test_fog_of_war_renders_bad_pending_next_chunk_red():
    fog_map = fog_of_war.build_map(
        [b"PNG", b"IHDR", b"gAMA"],
        b"IDAT",
        data_hex="00" * 128,
        current_offset=64,
        error=False,
        preview_chunk=b"bKGG",
        preview_error=True,
    )

    rendered = fog_of_war.render(fog_map, color=color)

    assert rendered.index("<yellow:[>IDAT<]>") < rendered.index("<red:[!bKGG!]>")
    assert "<blue:[bKGG?]>" not in rendered


def main():
    checks = [
        ("clean IDAT compaction", test_fog_of_war_keeps_clean_idat_compaction),
        ("current IDAT error merge", test_fog_of_war_merges_current_idat_error_with_seen_idats),
        ("non-current IDAT total", test_fog_of_war_uses_green_total_when_idat_is_not_current),
        ("first current IDAT error", test_fog_of_war_marks_first_current_idat_error),
        ("unrepaired chunk stays red", test_fog_of_war_keeps_unrepaired_seen_chunk_red),
        ("pending next chunk", test_fog_of_war_renders_pending_next_chunk_after_current),
        ("bad pending next chunk", test_fog_of_war_renders_bad_pending_next_chunk_red),
    ]

    print("Running FogOfWar tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"FogOfWar tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
