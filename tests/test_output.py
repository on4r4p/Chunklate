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


def test_realpng_names_use_inner_png_stem(tmp_path):
    source = "/somewhere/length_ihdr.png.realpng"

    assert output.clone_folder(source, str(tmp_path)) == str(tmp_path / "Folder_length_ihdr")
    assert output.clone_basename(source) == "length_ihdr."
    assert output.summary_path(source, str(tmp_path)) == str(
        tmp_path / "Folder_length_ihdr" / "Summary_Of_length_ihdr"
    )


def test_lockdown_folder_lines_preserve_legacy_printed_paths(tmp_path):
    assert output.lockdown_folder_lines("/somewhere/sample.png", str(tmp_path)) == (
        str(tmp_path / "Folder_sample"),
        str(tmp_path / "Folder_sample") + "/",
    )


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


def test_summary_path_uses_clone_folder(tmp_path):
    path = output.summary_path("/somewhere/sample.png", str(tmp_path))

    assert path == str(tmp_path / "Folder_sample" / "Summary_Of_sample")
    assert Path(path).parent.is_dir()


def test_summary_body_preserves_legacy_note_layout():
    assert output.summary_body("fixed", []) == "\nfixed\n"
    assert output.summary_body("fixed", ["note-a", "note-b"]) == "\nnote-a\n\nnote-b\nfixed\n"
    assert output.summary_body(None, ["note-a"]) == "\nnote-a\n"
    assert output.summary_body(None, []) is None


def test_render_summary_footer_preserves_legacy_sections():
    state = {
        "IHDR_Height": 10,
        "IHDR_Width": 20,
        "IHDR_Depht": "8",
        "IHDR_Color": "2",
        "IHDR_Method": "0",
        "IHDR_Interlace": "0",
        "pHYs_X": "100",
        "pHYs_Y": "200",
        "pHYs_Unit": "1",
        "bKGD_Gray": "3",
        "bKGD_Red": "4",
        "bKGD_Green": "5",
        "bKGD_Blue": "6",
        "bKGD_Index": "7",
        "gAMA": "45455",
        "PLTE_R": ["00", "01"],
        "PLTE_G": ["02"],
        "PLTE_B": ["03"],
        "sPLT_Red": ["r"],
        "sPLT_Green": ["g"],
        "sPLT_Blue": ["b"],
        "sPLT_Alpha": ["a"],
        "sPLT_Freq": ["f"],
        "hIST": ["1", "2"],
        "tRNS_Gray": "8",
        "tRNS_TrueR": "9",
        "tRNS_TrueG": "10",
        "tRNS_TrueB": "11",
        "tRNS_Index": ["00", "01"],
        "sTER": "1",
        "cHRM_WhiteX": "12",
        "cHRM_WhiteY": "13",
        "cHRM_Redx": "14",
        "cHRM_Redy": "15",
        "cHRM_Greenx": "16",
        "cHRM_Greeny": "17",
        "cHRM_Bluex": "18",
        "cHRM_Bluey": "19",
        "sBIT_Gray": "8",
        "sBIT_TrueR": "8",
        "sBIT_TrueG": "8",
        "sBIT_TrueB": "8",
        "sBIT_GrayScale": "8",
        "sBIT_GrayAlpha": "8",
        "sBIT_TrueAlphaR": "8",
        "sBIT_TrueAlphaG": "8",
        "sBIT_TrueAlphaB": "8",
        "sBIT_TrueAlpha": "8",
        "pCAL_Key": "43616c",
        "pCAL_Zero": "0",
        "pCAL_Max": "255",
        "pCAL_Eq": "1",
        "pCAL_PNBR": "2",
        "iCCP_Name": "ICC",
        "iCCP_Method": 0,
        "sRGB": "2",
        "tIME_Yr": "2026",
        "tIME_Mth": "05",
        "tIME_Day": "22",
        "tIME_Hr": "12",
        "tIME_Min": "34",
        "tIME_Sec": "56",
        "tEXt_Key_List": ["Title"],
        "tEXt_Str_List": ["Hello"],
        "iTXt_Key_List": ["Comment"],
        "iTXt_String_List": ["Bonjour"],
        "zTXt_Key_List": ["Zip"],
        "zTXt_Str_List": ["Compressed"],
    }

    footer = output.render_summary_footer(state, "<EOF>")

    assert footer.startswith("\n\n『File Informations: 』\n")
    assert "\n-IHDR Width    :10" in footer
    assert "\n-IHDR Height   :20" in footer
    assert "\n-pHYs Pixels per unit, X axis: 100" in footer
    assert "\n-PLTE Red Palettes    :2" in footer
    assert "\n-sPLT Suggested Frequencies palettes stored:1" in footer
    assert "\n-tRNS Alpha indexes stored:2" in footer
    assert "\n-cHRM chromaticities BlueY   :19" in footer
    assert "\n-sBIT significant bits Alpha        :8" in footer
    assert "\n-pCAL Calibration name    :Cal" in footer
    assert "\n-iCCP Profile Method :0" in footer
    assert "\n-Year     :2026" in footer
    assert "\n-tEXt Title :\nHello\n" in footer
    assert "\n-iTXt Comment :\nBonjour\n" in footer
    assert "\n-zTXt Zip :\nCompressed\n" in footer
    assert footer.endswith("<EOF>")


def test_summary_separator_preserves_legacy_spacing():
    assert output.summary_separator("Title", True, 80) == (
        "\n"
        + (" " * 22)
        + " ▁ ▂ ▄ ▅ ▆ ▇ █ "
        + "Title"
        + " █ ▇ ▆ ▅ ▄ ▂ ▁ "
        + "\n\n"
    )
    assert output.summary_separator("End", False, 80) == (
        "\n"
        + (" " * 12)
        + " ▁ ▂ ▄ ▅ ▆ ▇ █ █ ▇ ▆ ▅ ▄ ▂ ▁"
        + "End"
        + "▁ ▂ ▄ ▅ ▆ ▇ █ ▇ ▆ ▅ ▄ ▂ ▁"
        + "\n\n"
    )


def test_the_end_debug_lines_preserve_legacy_values():
    lines = output.the_end_debug_lines(
        ["-1:0:8:13", "0:8:20:4"],
        3,
        [b"IHDR", b"IDAT"],
        123,
    )

    assert lines == [
        "Chnks nbr:2",
        "idacounter:3",
        [b"IHDR", b"IDAT"],
        "IDAT_Bytes_Len:123",
    ]


def test_run_summarise_from_namespace_writes_summary_and_resets_notes(tmp_path):
    namespace = {
        "Sample_Name": "sample.png",
        "MAXCHAR": 80,
        "SideNotes": ["note"],
        "FILE_Origin": "sample.png",
        "FILE_DIR": str(tmp_path),
        "Candy": lambda kind, color, value: "<%s:%s>" % (color, value),
        "Summary_Header": True,
    }

    output.run_summarise_from_namespace(namespace, "fixed", False)

    summary = tmp_path / "Folder_sample" / "Summary_Of_sample"
    text = summary.read_text()
    assert "C|h|u|n|k|l|a|t|e" in text
    assert "『sample.png :』" in text
    assert "\nnote\nfixed\n" in text
    assert namespace["Summary_Header"] is False
    assert namespace["SideNotes"] == []


def main():
    tmpdir = tempfile.TemporaryDirectory()
    tmp_path = Path(tmpdir.name)
    checks = [
        ("Clone folder matches legacy folder name", lambda: test_clone_folder_matches_legacy_folder_name(tmp_path)),
        ("realpng names use inner PNG stem", lambda: test_realpng_names_use_inner_png_stem(tmp_path)),
        ("LockDown folder lines", lambda: test_lockdown_folder_lines_preserve_legacy_printed_paths(tmp_path)),
        ("Clone target uses next fixed name", lambda: test_next_clone_target_uses_next_available_fixed_name(tmp_path)),
        ("Clone bytes accepts hex and bytes", test_clone_bytes_accepts_hex_and_bytes),
        ("Write clone writes PNG bytes", lambda: test_write_clone_writes_png_bytes(tmp_path)),
        ("Summary path uses clone folder", lambda: test_summary_path_uses_clone_folder(tmp_path)),
        ("Summary body preserves notes", test_summary_body_preserves_legacy_note_layout),
        ("Summary footer preserves sections", test_render_summary_footer_preserves_legacy_sections),
        ("Summary separator preserves spacing", test_summary_separator_preserves_legacy_spacing),
        ("TheEnd debug lines", test_the_end_debug_lines_preserve_legacy_values),
        ("Summarise namespace bridge", lambda: test_run_summarise_from_namespace_writes_summary_and_resets_notes(tmp_path)),
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
