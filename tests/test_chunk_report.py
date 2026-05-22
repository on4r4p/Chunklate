#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import chunk_info, chunk_report


def collect(render, *args):
    lines = []

    def emit(line):
        lines.append(line)

    def color(name, value):
        return f"<{name}>{value}</{name}>"

    render(*args, emit, color)
    return lines


def test_render_ihdr_keeps_legacy_labels():
    info = chunk_info.parse_ihdr("00000020000000100802000000")

    assert collect(chunk_report.render_ihdr, info) == [
        "-Width    :<yellow>32</yellow>",
        "-Height   :<yellow>16</yellow>",
        "-Depht    :<yellow>8</yellow>",
        "-Color    :<yellow>2</yellow>",
        "-Method   :<yellow>0</yellow>",
        "-Filter   :<yellow>0</yellow>",
        "-Interlace:<yellow>0</yellow>",
    ]


def test_render_palette_groups_report_counts():
    assert collect(chunk_report.render_plte, ["00", "03"], ["01", "04"], ["02", "05"]) == [
        "-<yellow>2</yellow> Red palettes are stored.",
        "-<yellow>2</yellow> Green palettes are stored.",
        "-<yellow>2</yellow> Blue palettes are stored.",
        "-<yellow>6</yellow> RGB palettes are stored.",
    ]


def test_render_splt_reports_name_and_component_counts():
    info = chunk_info.parse_splt("70616c0008" + ("01" * 13))

    assert collect(
        chunk_report.render_splt,
        info,
        ["r"],
        ["g"],
        ["b"],
        ["a"],
        ["f"],
    ) == [
        "-sPLT name : <white>pal</white>",
        "-<yellow>1</yellow> Suggested Red palettes are stored.",
        "-<yellow>1</yellow> Suggested Green palettes are stored.",
        "-<yellow>1</yellow> Suggested Blue palettes are stored.",
        "-<yellow>1</yellow> Suggested Alpha palettes are stored.",
        "-<yellow>1</yellow> Suggested Frequency values are stored.",
    ]


def test_render_trns_reports_truecolor_and_indexes():
    truecolor = chunk_info.parse_trns("000100020003", ihdr_color="2")
    indexed = chunk_info.parse_trns("0001", ihdr_color="3", has_plte=True, plte_entries=2)

    assert collect(chunk_report.render_trns, truecolor) == [
        "-Red    :<red>1</red>",
        "-Green  :<green>2</green>",
        "-Blue   :<blue>3</blue>",
    ]
    assert collect(chunk_report.render_trns, indexed) == [
        "-<yellow>2</yellow> Alpha indexes are stored.",
    ]


def test_render_pcal_reports_legacy_fields():
    info = chunk_info.parse_pcal(
        "43616c00"
        "00000001"
        "00000002"
        "00"
        "02"
        "703100"
        "703200"
    )

    assert collect(chunk_report.render_pcal, info) == [
        "-Calibration name    :<yellow>Cal</yellow>",
        "-Original zero       :<yellow>1</yellow>",
        "-Original max        :<yellow>2</yellow>",
        "-Equation type       :<yellow>0</yellow>",
        "-Number of parameters:<yellow>2</yellow>",
    ]


def main():
    checks = [
        ("IHDR labels", test_render_ihdr_keeps_legacy_labels),
        ("PLTE counts", test_render_palette_groups_report_counts),
        ("sPLT counts", test_render_splt_reports_name_and_component_counts),
        ("tRNS fields", test_render_trns_reports_truecolor_and_indexes),
        ("pCAL fields", test_render_pcal_reports_legacy_fields),
    ]

    print("Running chunk report tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"chunk report tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
