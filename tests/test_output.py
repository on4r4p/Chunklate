#!/usr/bin/env python3
import sys
import tempfile
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import output


def test_clone_folder_matches_legacy_folder_name(tmp_path):
    folder = output.clone_folder("/somewhere/sample.png", str(tmp_path))

    assert folder == str(tmp_path / "Folder_sample")


def test_empty_origin_never_creates_folder_underscore(tmp_path):
    for helper in (
        output.clone_folder,
        output.ensure_clone_folder,
        output.summary_path,
        output.next_clone_target,
    ):
        with pytest.raises(ValueError):
            helper("", str(tmp_path))

    assert not (tmp_path / "Folder_").exists()


def test_summary_helpers_skip_empty_origin(tmp_path):
    namespace = {
        "Sample_Name": "sample.png",
        "MAXCHAR": 80,
        "SideNotes": [],
        "FILE_Origin": "",
        "FILE_DIR": str(tmp_path),
        "Candy": lambda kind, color, value: "<%s:%s>" % (color, value),
        "Summary_Header": True,
    }

    notes = output.ensure_immediate_summary_notes(namespace)
    notes.append("no-origin-note")
    output.run_summarise_from_namespace(namespace, "no-origin-result", False)

    assert not (tmp_path / "Folder_").exists()
    assert list(notes) == ["no-origin-note"]


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
    assert output.summary_body("\033[1;37;49mfixed\033[m", ["\033[1;31;49mnote\033[m"]) == "\nnote\nfixed\n"
    assert output.summary_body(None, ["note-a"]) == "\nnote-a\n"
    assert output.summary_body(None, []) is None


def test_immediate_summary_notes_flushes_each_append_and_summarise_does_not_duplicate(tmp_path):
    namespace = {
        "Sample_Name": "sample.png",
        "MAXCHAR": 80,
        "SideNotes": [],
        "FILE_Origin": "sample.png",
        "FILE_DIR": str(tmp_path),
        "Candy": lambda kind, color, value: "<%s:%s>" % (color, value),
        "Summary_Header": True,
    }

    notes = output.ensure_immediate_summary_notes(namespace)
    notes.append("\033[1;31;49mearly-note\033[m")
    notes.append("second-note")

    summary = tmp_path / "Folder_sample" / "Summary_Of_sample"
    text = summary.read_text(encoding="utf-8")
    assert "C|h|u|n|k|l|a|t|e" in text
    assert "『Summary: sample.png』" in text
    assert text.count("『Summary: sample.png』") == 1
    assert "001. Note: early-note" in text
    assert "002. Note: second-note" in text
    assert "\033[" not in text

    output.run_summarise_from_namespace(namespace, "final-info", False)
    text = summary.read_text(encoding="utf-8")
    assert text.count("early-note") == 1
    assert text.count("『Summary: sample.png』") == 1
    assert "003. Result: final-info" in text
    assert namespace["SideNotes"] is notes
    assert list(notes) == []


def test_summary_reset_truncates_stale_existing_summary(tmp_path):
    summary = tmp_path / "Folder_sample" / "Summary_Of_sample"
    summary.parent.mkdir(exist_ok=True)
    summary.write_text("old summary text that must disappear\n" * 5, encoding="utf-8")
    namespace = {
        "Sample_Name": "sample.png",
        "MAXCHAR": 80,
        "SideNotes": [],
        "FILE_Origin": "sample.png",
        "FILE_DIR": str(tmp_path),
        "Candy": lambda kind, color, value: "<%s:%s>" % (color, value),
        "Summary_Header": True,
    }

    notes = output.ensure_immediate_summary_notes(namespace)
    notes.append("fresh-note")
    output.run_summarise_from_namespace(namespace, "fresh-result", False)

    text = summary.read_text(encoding="utf-8")
    assert "old summary text" not in text
    assert "001. Note: fresh-note" in text
    assert "002. Result: fresh-result" in text
    assert namespace["Summary_File_Reset"] is True


def test_strip_ansi_removes_terminal_color_artifacts():
    assert output.strip_ansi("\033[1;37;49mwhite\033[m") == "white"


def test_debug_trace_body_keeps_only_relevant_clean_debug_lines():
    assert output.debug_trace_body([]) is None
    assert output.debug_trace_body(["first", "second"]) is None
    trace = output.debug_trace_body(
        [
            "error:True\n"
            "fixed:False\n"
            "╭─━━━━━━━━━━─╮\n"
            "function:CheckLength\n"
            "infos:-No NextChunk\n"
            "chunk:b'IEND'\n"
            "          /\n"
            "(ಠ_ಠ)\n"
            "Arg0:00000000 type:<class 'str'>\n"
            "Pandora:\n"
            "key:CheckLength_Error_0:-No NextChunk\n"
            "\033[1;31;49m-CriticalHit\033[m: boom\n"
            "Patch bytes ready: b'abc'... (3 bytes total)\n"
        ]
    )

    assert trace == (
        "\n\n『Debug Trace』\n\n"
        "  001. CheckLength [b'IEND']: ERROR\n"
        "       info: -No NextChunk\n"
        "       tool: Arg0:00000000 type:<class 'str'>\n"
        "       pandora: CheckLength_Error_0:-No NextChunk\n"
        "  002. CriticalHit: boom\n"
        "  003. Patch: b'abc'... (3 bytes total)\n"
        "\n"
    )


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
    text = summary.read_text(encoding="utf-8")
    assert "C|h|u|n|k|l|a|t|e" in text
    assert "『Summary: sample.png』" in text
    assert "001. Note: note" in text
    assert "002. Result: fixed" in text
    assert namespace["Summary_Header"] is False
    assert namespace["SideNotes"] == []


def test_run_summarise_from_namespace_appends_debug_trace_to_normal_summary(tmp_path):
    namespace = {
        "Sample_Name": "sample.png",
        "MAXCHAR": 80,
        "SideNotes": ["\033[1;31;49mnote\033[m"],
        "DebugNotes": [
            "\033[1;31;49m-CriticalHit\033[m: broken",
            "╭─━━━━━━━━━━─╮",
            "function:LibpngCheck",
            "this terminal narration should stay out",
            "Arg0:payload",
        ],
        "FILE_Origin": "sample.png",
        "FILE_DIR": str(tmp_path),
        "Candy": lambda kind, color, value: "<%s:%s>" % (color, value),
        "Summary_Header": True,
        "DEBUGFILE": True,
    }

    output.run_summarise_from_namespace(namespace, "fixed", False)

    summary = tmp_path / "Folder_sample" / "Summary_Of_sample"
    debug_summary = tmp_path / "Folder_sample" / "Summary_Of_sample.Debug"
    text = summary.read_text(encoding="utf-8")
    assert summary.exists()
    assert not debug_summary.exists()
    assert "C|h|u|n|k|l|a|t|e" in text
    assert "『Summary: sample.png』" in text
    assert "001. Note: note" in text
    assert "002. Result: fixed" in text
    assert "『Debug Trace』" in text
    assert "\033[" not in text
    assert "CriticalHit: broken" in text
    assert "LibpngCheck" in text
    assert "Tool: Arg0:payload" in text
    assert "terminal narration" not in text
    assert "╭─" not in text
    assert namespace["DebugNotes"] == []
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
        (
            "Immediate summary notes",
            lambda: test_immediate_summary_notes_flushes_each_append_and_summarise_does_not_duplicate(tmp_path),
        ),
        (
            "Summary reset truncates stale file",
            lambda: test_summary_reset_truncates_stale_existing_summary(tmp_path),
        ),
        ("Strip ANSI", test_strip_ansi_removes_terminal_color_artifacts),
        ("Debug trace body keeps relevant lines", test_debug_trace_body_keeps_only_relevant_clean_debug_lines),
        ("Summary footer preserves sections", test_render_summary_footer_preserves_legacy_sections),
        ("Summary separator preserves spacing", test_summary_separator_preserves_legacy_spacing),
        ("TheEnd debug lines", test_the_end_debug_lines_preserve_legacy_values),
        ("Summarise namespace bridge", lambda: test_run_summarise_from_namespace_writes_summary_and_resets_notes(tmp_path)),
        (
            "Summarise debug namespace bridge",
            lambda: test_run_summarise_from_namespace_appends_debug_trace_to_normal_summary(tmp_path),
        ),
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
