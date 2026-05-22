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


def collect_with_emoji(render, *args):
    lines = []

    def emit(line):
        lines.append(line)

    def color(name, value):
        return f"<{name}>{value}</{name}>"

    def emoji(name):
        return f":{name}:"

    render(*args, emit, color, emoji)
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


def test_render_phys_reports_fields_and_legacy_validation_messages():
    valid = chunk_info.parse_phys("000000010000000201")
    invalid = chunk_info.parse_phys("800000008000000002")

    assert collect_with_emoji(chunk_report.render_phys, valid) == [
        "-Pixels per unit, Y axis: <yellow>1</yellow>",
        "-Pixels per unit, X axis: <yellow>2</yellow>",
        "-Unit specifier         :<yellow>1</yellow>",
    ]
    assert collect_with_emoji(chunk_report.render_phys, invalid) == [
        "-Pixels per unit, Y axis: <yellow>2147483648</yellow>",
        "-Pixels per unit, Y axis:<red> Wrong size (Too high)</red> "
        "Must be between 1 to 2147483647.:bad:",
        "-Pixels per unit, X axis: <yellow>2147483648</yellow>",
        "Pixels per unit, X axis<red> Wrong size (Too high)</red> "
        "Must be between 1 to 2147483647.:bad:",
        "-Unit specifier         :<yellow>2</yellow>",
        "-Unit specifier :<red> Wrong value</red> Must be between 0 (unknown) or 1(meter).:bad:",
    ]


def test_render_time_reports_timestamp_and_invalid_values():
    valid = chunk_info.parse_time("07e80515112233", current_year=2026)
    invalid = chunk_info.parse_time("07ff0d20243d3d", current_year=2026)
    short = chunk_info.parse_time("00", current_year=2026)

    assert collect_with_emoji(chunk_report.render_time, valid, 2026) == [
        "-Last Modified: <white>21</white>/<white>5</white>/<white>2024</white> "
        "<white>17</white>:<white>34</white>:<white>51</white>",
    ]
    assert collect_with_emoji(chunk_report.render_time, invalid, 2026) == [
        "-Last Modified: <white>32</white>/<white>13</white>/<white>2047</white> "
        "<white>36</white>:<white>61</white>:<white>61</white>",
        "-Year is > than current year    : <red>2047</red> :bad:",
        "-Month value is not valid   : <red>13</red> :bad:",
        "-Day value is not valid      : <red>32</red> :bad:",
        "-Hour value is not valid     : <red>36</red> :bad:",
        "-Minute value is not valid  : <red>61</red> :bad:",
        "-Second  value is not valid : <red>61</red> :bad:",
    ]
    assert collect_with_emoji(chunk_report.render_time, short, 2026) == [
        "-tIME <red>Not enough bytes</red> inside tIME data.:bad:",
    ]


def test_render_srgb_reports_intent_and_chrm_override():
    valid = chunk_info.parse_srgb("02")
    invalid = chunk_info.parse_srgb("04")

    assert collect_with_emoji(chunk_report.render_srgb, valid, False) == [
        "-Rendering Saturation :<yellow>2</yellow>",
    ]
    assert collect_with_emoji(chunk_report.render_srgb, invalid, True) == [
        "-<red>Wrong</red> sRGB value must be between 0 to 3. :bad:",
        "-<red>cHRM</red> already present cHRM will be <red>overide</red> "
        "if reconized by decoders :bad:",
    ]


def test_render_gama_reports_zero_as_useless():
    info = chunk_info.parse_gama("00000000")

    assert collect(chunk_report.render_gama, info) == [
        "-Gama   :<white>0</white>",
        "-A gAMA Chunk of <red>0</red> is Useless.",
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
        ("pHYs fields", test_render_phys_reports_fields_and_legacy_validation_messages),
        ("tIME fields", test_render_time_reports_timestamp_and_invalid_values),
        ("sRGB fields", test_render_srgb_reports_intent_and_chrm_override),
        ("gAMA fields", test_render_gama_reports_zero_as_useless),
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
