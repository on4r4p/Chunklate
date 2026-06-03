#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import chunk_info, chunk_report
from chunklate.png import PNG_SIGNATURE, build_png_chunk, legacy_chunk_window


def collect(render, *args):
    lines = []

    def emit(line):
        lines.append(line)

    def color(name, value):
        return f"<{name}>{value}</{name}>"

    render(*args, emit, color)
    return lines


def collect_with_chunky(render, *args):
    lines = []

    def emit(line):
        lines.append(line)

    def color(name, value):
        return f"<{name}>{value}</{name}>"

    def chunky(name):
        return f":{name}:"

    render(*args, emit, color, chunky)
    return lines


def test_render_legacy_chunk_window_keeps_chunkbychunk_lines():
    png_data = (
        PNG_SIGNATURE
        + build_png_chunk(
            b"IHDR",
            b"\x00\x00\x00\x20\x00\x00\x00\x10\x08\x02\x00\x00\x00",
        )
        + build_png_chunk(b"IDAT", b"abc")
    )
    window = legacy_chunk_window(png_data, len(PNG_SIGNATURE) * 2)

    assert collect(chunk_report.render_legacy_chunk_window, window) == [
        "-Found at offset            "
        "(<yellow>Hex</yellow>/<blue>Bytes</blue>/<purple>Index</purple>): "
        "(<yellow>0x8</yellow>/<blue>8</blue>/<purple>16</purple>) ",
        "-Chunk Length:              (<yellow>0xd</yellow>/<blue>13</blue>)",
        "",
        "-Found at offset            "
        "(<yellow>Hex</yellow>/<blue>Bytes</blue>/<purple>Index</purple>): "
        "(<yellow>0xc</yellow>/<blue>12</blue>/<purple>24</purple>) ",
        "-Chunk Type :               (<yellow>49484452</yellow>/<blue>b'IHDR'</blue>)",
        "",
        "-Found Chunk Data at offset "
        "(<yellow>Hex</yellow>/<blue>Bytes</blue>/<purple>Index</purple>): "
        "(<yellow>0x10</yellow>/<blue>16</blue>/<purple>32</purple>) ",
        "",
        "-Found at offset            "
        "(<yellow>Hex</yellow>/<blue>Bytes</blue>/<purple>Index</purple>): "
        "(<yellow>0x1d</yellow>/<blue>29</blue>/<purple>58</purple>) ",
        "-Chunk Crc:                 (<yellow>f862ea0e</yellow>/offset :  <yellow>0x1d</yellow>)",
        "",
        "-Found at offset            "
        "(<yellow>Hex</yellow>/<blue>Bytes</blue>/<purple>Index</purple>): "
        "(<yellow>0x37</yellow>/<blue>45</blue>/<purple>90</purple>) ",
        "-Raw_NextChunk Type :       (<yellow>49444154</yellow>/<blue>b'IDAT'</blue>)",
    ]


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
    info = chunk_info.parse_splt("70616c0008" + ("01" * 6))

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

    assert collect_with_chunky(chunk_report.render_phys, valid) == [
        "-Pixels per unit, Y axis: <yellow>1</yellow>",
        "-Pixels per unit, X axis: <yellow>2</yellow>",
        "-Unit specifier         :<yellow>1</yellow>",
    ]
    assert collect_with_chunky(chunk_report.render_phys, invalid) == [
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

    assert collect_with_chunky(chunk_report.render_time, valid, 2026) == [
        "-Last Modified: <white>21</white>/<white>5</white>/<white>2024</white> "
        "<white>17</white>:<white>34</white>:<white>51</white>",
    ]
    assert collect_with_chunky(chunk_report.render_time, invalid, 2026) == [
        "-Last Modified: <white>32</white>/<white>13</white>/<white>2047</white> "
        "<white>36</white>:<white>61</white>:<white>61</white>",
        "-Year is > than current year    : <red>2047</red> :bad:",
        "-Month value is not valid   : <red>13</red> :bad:",
        "-Day value is not valid      : <red>32</red> :bad:",
        "-Hour value is not valid     : <red>36</red> :bad:",
        "-Minute value is not valid  : <red>61</red> :bad:",
        "-Second  value is not valid : <red>61</red> :bad:",
    ]
    assert collect_with_chunky(chunk_report.render_time, short, 2026) == [
        "-tIME <red>Not enough bytes</red> inside tIME data.:bad:",
    ]


def test_render_srgb_reports_intent_and_chrm_override():
    valid = chunk_info.parse_srgb("02")
    invalid = chunk_info.parse_srgb("04")

    assert collect_with_chunky(chunk_report.render_srgb, valid, False) == [
        "-Rendering Saturation :<yellow>2</yellow>",
    ]
    assert collect_with_chunky(chunk_report.render_srgb, invalid, True) == [
        "-<red>Wrong</red> sRGB value must be between 0 to 3. :bad:",
        "-<red>cHRM</red> already present cHRM will be <red>overide</red> "
        "if reconized by decoders :bad:",
    ]


def test_render_gama_reports_zero_as_useless():
    info = chunk_info.parse_gama("00000000")
    short = chunk_info.parse_gama("000186")

    assert collect(chunk_report.render_gama, info) == [
        "-Gama   :<white>0</white>",
        "-A gAMA Chunk of <red>0</red> is Useless.",
    ]
    assert collect(chunk_report.render_gama, short) == [
        "-gAMA length is <red>not Valid</red>",
        "-Gama   :<white>390</white>",
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


def test_render_chrm_reports_fields_and_override_warning():
    info = chunk_info.parse_chrm(
        "0000000100000002000000030000000400000005000000060000000700000008",
        has_srgb_or_iccp=True,
    )

    assert collect_with_chunky(chunk_report.render_chrm, info, True) == [
        "-WhiteX   :<white>1</white>",
        "-WhiteY   :<white>2</white>",
        "-RedX     :<red>3</red>",
        "-RedY     :<red>4</red>",
        "-GreenX   :<green>5</green>",
        "-GreenY   :<green>6</green>",
        "-BlueX    :<blue>7</blue>",
        "-BlueY    :<blue>8</blue>",
        "-<red>sRGB</red> or <red>iCCP</red> already present cHRM will be overide "
        "if reconized by decoders :bad:",
    ]


def test_render_iccp_reports_name_method_profile_and_override_warnings():
    info = chunk_info.parse_iccp("0143430001abcd", raw_length_hex="00000008", has_chrm=True)

    assert collect_with_chunky(chunk_report.render_iccp, info, True) == [
        "-Character <red>not allowed [\x01]</red> at index <red>0</red> in iCCP_Name\n"
        "-Replaced by [€]",
        "-Compression method is supposed to be <green>0</green> but is <red>1</red> instead .",
        "-iCCP Profile length is <red>not Valid</red>",
        "-<red>cHRM</red> already present cHRM will be <red>overide</red> "
        "if reconized by decoders :bad:",
        "-iCCP Profile Name :<yellow>€CC</yellow>",
        "-iCCP Profile Method :<yellow>1</yellow>",
    ]


def test_render_sbit_reports_color_dependent_fields():
    gray = chunk_info.parse_sbit("08", ihdr_color="0", ihdr_depth="8")
    truecolor = chunk_info.parse_sbit("080706", ihdr_color="2", ihdr_depth="8")
    gray_alpha = chunk_info.parse_sbit("0807", ihdr_color="4", ihdr_depth="8")
    true_alpha = chunk_info.parse_sbit("08070605", ihdr_color="6", ihdr_depth="8")

    assert collect(chunk_report.render_sbit, gray) == [
        "-Significant greyscale bits    :<yellow>8</yellow>",
    ]
    assert collect(chunk_report.render_sbit, truecolor) == [
        "-significant bits Red    :<red>8</red>",
        "-significant bits Green  :<green>7</green>",
        "-significant bits Blue   :<blue>6</blue>",
    ]
    assert collect(chunk_report.render_sbit, gray_alpha) == [
        "-Gray scale significant bit:<white>8</white>",
        "-Gray alpha significant bit:<white>7</white>",
    ]
    assert collect(chunk_report.render_sbit, true_alpha) == [
        "-significant bits Alpha Red    :<red>8</red>",
        "-significant bits Alpha Green  :<green>7</green>",
        "-significant bits Alpha Blue   :<blue>6</blue>",
        "-significant bits Alpha        :<white>5</white>",
    ]


def test_render_offs_reports_fields_and_legacy_validation_messages():
    valid = chunk_info.parse_offs("00000001ffffffff01")
    invalid = chunk_info.parse_offs("800000007fffffff02")

    assert collect_with_chunky(chunk_report.render_offs, valid) == [
        "-Offset position X    :<blue>1</blue>",
        "-Offset position Y  :<purple>-1</purple>",
        "-Offset Unit   :<white>1</white>",
    ]
    assert collect_with_chunky(chunk_report.render_offs, invalid) == [
        "-Offset position X    :<blue>-2147483648</blue>",
        "-Offset position Y  :<purple>2147483647</purple>",
        "-Offset Unit   :<white>2</white>",
        "-<red>Wrong</red> Offset position X must be between -2,147,483,647 to +2,147,483,647 :bad:",
        "-<red>Wrong</red> Offset unit must be between 0 or 1 :bad:",
    ]


def test_render_gif_and_ster_reports_legacy_labels():
    gifg = chunk_info.parse_gifg("01020003")
    long_gifg = chunk_info.parse_gifg("0200000a00")
    gifx = chunk_info.parse_gifx("0000000000000001000002ff")
    ster = chunk_info.parse_ster("01")

    assert collect(chunk_report.render_gifg, gifg) == [
        "-Disposal Method    :<yellow>1</yellow>",
        "-User Input Flag    :<yellow>2</yellow>",
        "-Delay Time    :<yellow>3</yellow>",
    ]
    assert collect(chunk_report.render_gifg, long_gifg) == [
        "-gIFg length is <red>not Valid</red>",
        "-Disposal Method    :<yellow>2</yellow>",
        "-User Input Flag    :<yellow>0</yellow>",
        "-Delay Time    :<yellow>10</yellow>",
    ]
    assert collect(chunk_report.render_gifx, gifx) == [
        "-Application Identifier    :<yellow>1</yellow>",
        "-Authentication Code    :<yellow>2</yellow>",
        "-Application Data    :<yellow>255</yellow>",
    ]
    assert collect(chunk_report.render_ster, ster) == [
        "-Subimage mode    :<yellow>1</yellow>",
    ]


def test_render_text_chunks_report_decoded_fields():
    text = chunk_info.parse_text("5469746c650048656c6c6f")
    ztxt = chunk_info.parse_ztxt("4b65790000789cf348cdc9c90700058c01f5")
    itxt = chunk_info.parse_itxt("4b6579000000000048656c6c6f")

    assert collect(chunk_report.render_text, text) == [
        "-Keyword : <green>Title</green>",
        "-String  : <green>Hello</green>",
    ]
    assert collect(chunk_report.render_ztxt, ztxt) == [
        "-Keyword : <green>Key</green>",
        "-String  : <green>Hello</green>",
    ]
    assert collect(chunk_report.render_itxt, itxt) == [
        "-Keyword             : <green>Key</green>",
        "-Compression Flag    : <green>00</green>",
        "-Compression Method  : <green>00</green>",
        "-Language            : <green></green>",
        "-Keyword Traduction  : <green></green>",
        "-String              : <green>Hello</green>",
    ]


def test_render_exif_and_spal_report_legacy_lines():
    exif = chunk_info.ExifInfo(endian="II", raw_values=("41424300000000", "ff" * 151))
    spal = chunk_info.parse_spal("")

    assert collect(chunk_report.render_exif, exif) == [
        "-eXif endianess is little-endian : II",
        "\nRaw values from eXIf data :\n\n",
        "- ABC\x00\x00\x00\x00",
        "-Raw data is too long to be displayed",
    ]
    assert collect(chunk_report.render_spal, spal) == [
        "-intermediate sPLT test version",
    ]


def main():
    checks = [
        ("legacy chunk window", test_render_legacy_chunk_window_keeps_chunkbychunk_lines),
        ("IHDR labels", test_render_ihdr_keeps_legacy_labels),
        ("PLTE counts", test_render_palette_groups_report_counts),
        ("sPLT counts", test_render_splt_reports_name_and_component_counts),
        ("tRNS fields", test_render_trns_reports_truecolor_and_indexes),
        ("pHYs fields", test_render_phys_reports_fields_and_legacy_validation_messages),
        ("tIME fields", test_render_time_reports_timestamp_and_invalid_values),
        ("sRGB fields", test_render_srgb_reports_intent_and_chrm_override),
        ("gAMA fields", test_render_gama_reports_zero_as_useless),
        ("pCAL fields", test_render_pcal_reports_legacy_fields),
        ("cHRM fields", test_render_chrm_reports_fields_and_override_warning),
        ("iCCP fields", test_render_iccp_reports_name_method_profile_and_override_warnings),
        ("sBIT fields", test_render_sbit_reports_color_dependent_fields),
        ("oFFs fields", test_render_offs_reports_fields_and_legacy_validation_messages),
        ("gif/ster fields", test_render_gif_and_ster_reports_legacy_labels),
        ("text fields", test_render_text_chunks_report_decoded_fields),
        ("eXIf/spAL fields", test_render_exif_and_spal_report_legacy_lines),
    ]

    print("Running chunk report tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"chunk report tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
