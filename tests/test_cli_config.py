#!/usr/bin/env python3
import sys
from argparse import ArgumentParser
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import cli


def args(**overrides):
    values = {
        "CLEAR": False,
        "PAUSE": False,
        "PAUSEDEBUG": False,
        "PAUSEERROR": False,
        "PAUSEDIALOGUE": False,
        "NODIALOGUE": False,
        "DEBUG": False,
        "DEBUGFILE": False,
        "AUTO": False,
        "NO_COLOR": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_max_saves_error_preserves_legacy_validation():
    assert cli.max_saves_error(None) is None
    assert cli.max_saves_error(1) is None
    assert cli.max_saves_error(0) == "--max-saves arguments must be greater than zero."


def test_configure_parser_preserves_legacy_options():
    parser = cli.configure_parser(ArgumentParser())
    help_text = parser.format_help()

    assert "--file FILE" in help_text
    assert "--CLEAR" in help_text
    assert "--clear" in help_text
    assert "--pause" in help_text
    assert "--debug" in help_text
    assert "--debug-file" in help_text
    assert "--pause-debug" in help_text
    assert "--pause-error" in help_text
    assert "--pause-dialogue" in help_text
    assert "--shut-the-fuck-up" in help_text
    assert "--auto" in help_text
    assert "--no-color" in help_text
    assert "--output-dir DIR" in help_text
    assert "--max-saves N" in help_text
    assert "-workers min|normal|max|auto|N" in help_text
    assert "CPU workers for heavy repair routes" in help_text
    assert "--idat-huffman-kraft-workers" not in help_text
    assert "\n\nultimate line-feed:\n" in help_text
    assert "--max-saves N    Exit successfully after writing N repaired files." in help_text
    assert "Ultimate candidate limit." not in help_text
    assert "-ulfb N" not in help_text
    assert "--ultimate-linefeed-budget N" not in help_text
    assert "-ulfu" not in help_text
    assert "--ultimate-linefeed-unbounded" not in help_text
    assert "-ulfr exact|similar PATH" in help_text
    assert "--ultimate-linefeed-reference PATH" not in help_text
    assert "-ulfrm {exact,similar}" not in help_text
    assert "--ultimate-linefeed-reference-mode {exact,similar}" not in help_text
    assert "-ulfroi PATH" not in help_text
    assert "--ultimate-linefeed-reference-regions PATH" not in help_text
    assert "-ulfroi-edit" in help_text
    assert "--ultimate-linefeed-reference-region-editor" not in help_text
    assert "-ulfpt SECONDS" not in help_text
    assert "--ultimate-linefeed-preview-timeout SECONDS" not in help_text
    assert "-ulfsp" in help_text
    assert "--ultimate-linefeed-show-previews" not in help_text
    assert "-ulfgl N" in help_text
    assert "--ultimate-linefeed-visual-gallery-limit N" not in help_text
    assert "-ulfmc FLOAT" in help_text
    assert "--ultimate-linefeed-visual-min-coverage FLOAT" not in help_text
    assert "Resume policy for Ultimate checkpoints." not in help_text
    assert "-ulf-resume MODE" not in help_text
    assert "--ultimate-linefeed-resume MODE" not in help_text
    assert "-ulf-resume {ask,auto,never,reset}" not in help_text
    assert "--ultimate-linefeed-resume {ask,auto,never,reset}" not in help_text
    assert "-ulfw" not in help_text
    assert "--ultimate-linefeed-workers" not in help_text
    assert "-sbbw" not in help_text
    assert "--smashbrutebrawl-workers" not in help_text
    assert "-sbb-resume" not in help_text
    assert "--smashbrutebrawl-resume" not in help_text
    assert "--ultimate-linefeed" not in help_text
    assert "--ulf-budget" not in help_text
    assert "--ulf-unbounded" not in help_text
    assert "--ulf-reference " not in help_text
    assert "--ulf-reference-mode" not in help_text
    assert "--ulf-reference-regions" not in help_text
    assert "--ulf-reference-region-editor" not in help_text
    assert "--ulf-preview-timeout" not in help_text
    assert "--ulf-show-previews" not in help_text
    assert "--ulf-gallery-limit" not in help_text
    assert "--ulf-min-coverage" not in help_text
    assert "--ulfb" not in help_text
    assert "--ulfu" not in help_text
    assert "--ulfr" not in help_text
    assert "--ulfrm" not in help_text
    assert "--ulfroi" not in help_text
    assert "--ulfroi-edit" not in help_text
    assert "--ulfpt" not in help_text
    assert "--ulfsp" not in help_text
    assert "--ulfgl" not in help_text
    assert "--ulfmc" not in help_text


def test_configure_parser_parses_runtime_arguments():
    parser = cli.configure_parser(ArgumentParser())

    parsed = parser.parse_args(
        [
            "-f",
            "sample.png",
            "--clear",
            "-p",
            "-d",
            "-df",
            "-dp",
            "-ep",
            "-sp",
            "-stfu",
            "-a",
            "--no-color",
            "--output-dir",
            "out",
            "--max-saves",
            "2",
            "-workers",
            "normal",
            "--idat-huffman-kraft-workers",
            "7",
            "-ulfb",
            "1234",
            "-ulfu",
            "-ulfr",
            "similar",
            "ref.png",
            "-ulfpt",
            "1.5",
            "-ulfsp",
            "-ulfgl",
            "100",
            "-ulfmc",
            "0.9",
            "-ulf-resume",
            "auto",
        ]
    )

    assert parsed.FILENAME == "sample.png"
    assert parsed.CLEAR is True
    assert parsed.PAUSE is True
    assert parsed.DEBUG is True
    assert parsed.DEBUGFILE is True
    assert parsed.PAUSEDEBUG is True
    assert parsed.PAUSEERROR is True
    assert parsed.PAUSEDIALOGUE is True
    assert parsed.NODIALOGUE is True
    assert parsed.AUTO is True
    assert parsed.NO_COLOR is True
    assert parsed.OUTPUT_DIR == "out"
    assert parsed.MAX_SAVES == 2
    assert parsed.GLOBAL_WORKERS == "normal"
    assert parsed.IDAT_HUFFMAN_KRAFT_WORKERS == "7"
    assert parsed.ULTIMATE_LINEFEED_BUDGET == 1234
    assert parsed.ULTIMATE_LINEFEED_UNBOUNDED is True
    assert parsed.ULTIMATE_LINEFEED_REFERENCE == "ref.png"
    assert parsed.ULTIMATE_LINEFEED_REFERENCE_MODE == "similar"
    assert parsed.ULTIMATE_LINEFEED_PREVIEW_TIMEOUT == 1.5
    assert parsed.ULTIMATE_LINEFEED_SHOW_PREVIEWS is True
    assert parsed.ULTIMATE_LINEFEED_VISUAL_GALLERY_LIMIT == 100
    assert parsed.ULTIMATE_LINEFEED_VISUAL_MIN_COVERAGE == 0.9
    assert parsed.ULTIMATE_LINEFEED_RESUME == "auto"


def test_hidden_legacy_ulf_aliases_still_parse():
    parser = cli.configure_parser(ArgumentParser())

    parsed = parser.parse_args(
        [
            "--ulf-budget",
            "1234",
            "--ulf-unbounded",
            "--ulf-reference",
            "ref.png",
            "--ulf-reference-mode",
            "similar",
            "--ulf-preview-timeout",
            "1.5",
            "--ulf-show-previews",
            "--ulf-gallery-limit",
            "100",
            "--ulf-min-coverage",
            "0.9",
        ]
    )

    assert parsed.ULTIMATE_LINEFEED_BUDGET == 1234
    assert parsed.ULTIMATE_LINEFEED_UNBOUNDED is True
    assert parsed.ULTIMATE_LINEFEED_REFERENCE == "ref.png"
    assert parsed.ULTIMATE_LINEFEED_REFERENCE_MODE == "similar"
    assert parsed.ULTIMATE_LINEFEED_PREVIEW_TIMEOUT == 1.5
    assert parsed.ULTIMATE_LINEFEED_SHOW_PREVIEWS is True
    assert parsed.ULTIMATE_LINEFEED_VISUAL_GALLERY_LIMIT == 100
    assert parsed.ULTIMATE_LINEFEED_VISUAL_MIN_COVERAGE == 0.9


def test_legacy_short_reference_mode_flag_still_parses():
    parser = cli.configure_parser(ArgumentParser())

    parsed = parser.parse_args(["-ulfr", "ref.png", "-ulfrm", "similar"])

    assert parsed.ULTIMATE_LINEFEED_REFERENCE == "ref.png"
    assert parsed.ULTIMATE_LINEFEED_REFERENCE_MODE == "similar"


def test_ultimate_linefeed_budget_error_preserves_guardrail():
    assert cli.ultimate_linefeed_budget_error(None) is None
    assert cli.ultimate_linefeed_budget_error(1) is None
    assert cli.ultimate_linefeed_budget_error(0) == "--ultimate-linefeed-budget arguments must be greater than zero."
    assert cli.ultimate_linefeed_budget_error(0, ultimate_linefeed_unbounded=True) is None


def test_ultimate_linefeed_preview_timeout_error_preserves_guardrail():
    assert cli.ultimate_linefeed_preview_timeout_error(None) is None
    assert cli.ultimate_linefeed_preview_timeout_error(0) is None
    assert cli.ultimate_linefeed_preview_timeout_error(1.5) is None
    assert (
        cli.ultimate_linefeed_preview_timeout_error(-1)
        == "--ultimate-linefeed-preview-timeout arguments must be zero or greater."
    )


def test_ultimate_linefeed_visual_gallery_errors_preserve_guardrails():
    assert cli.ultimate_linefeed_visual_gallery_limit_error(None) is None
    assert cli.ultimate_linefeed_visual_gallery_limit_error(0) is None
    assert cli.ultimate_linefeed_visual_gallery_limit_error(100) is None
    assert (
        cli.ultimate_linefeed_visual_gallery_limit_error(-1)
        == "--ultimate-linefeed-visual-gallery-limit arguments must be zero or greater."
    )
    assert cli.ultimate_linefeed_visual_min_coverage_error(None) is None
    assert cli.ultimate_linefeed_visual_min_coverage_error(0) is None
    assert cli.ultimate_linefeed_visual_min_coverage_error(1) is None
    assert cli.ultimate_linefeed_visual_min_coverage_error(0.95) is None
    assert (
        cli.ultimate_linefeed_visual_min_coverage_error(1.1)
        == "--ultimate-linefeed-visual-min-coverage arguments must be between 0 and 1."
    )


def test_ultimate_linefeed_reference_mode_error_preserves_guardrail():
    assert cli.ultimate_linefeed_reference_mode_error(None) is None
    assert cli.ultimate_linefeed_reference_mode_error("exact") is None
    assert cli.ultimate_linefeed_reference_mode_error("similar") is None
    assert (
        cli.ultimate_linefeed_reference_mode_error("bad")
        == "--ultimate-linefeed-reference-mode must be one of: exact, similar."
    )


def test_ultimate_linefeed_resume_error_preserves_guardrail():
    assert cli.ultimate_linefeed_resume_error(None) is None
    assert cli.ultimate_linefeed_resume_error("ask") is None
    assert cli.ultimate_linefeed_resume_error("auto") is None
    assert cli.ultimate_linefeed_resume_error("never") is None
    assert cli.ultimate_linefeed_resume_error("reset") is None
    assert (
        cli.ultimate_linefeed_resume_error("bad")
        == "--ultimate-linefeed-resume must be one of: ask, auto, never, reset."
    )


def test_parse_legacy_unknown_options_preserves_clone_and_crash():
    options = cli.parse_legacy_unknown_options(["--CLONE", "Folder_1/sample.png", "--crash", "42"])

    assert options == cli.LegacyUnknownOptions(
        cloneswar="Folder_1/sample.png --crash 42",
        crash=42,
    )


def test_parse_legacy_unknown_options_reports_invalid_crash():
    options = cli.parse_legacy_unknown_options("--crash nope")

    assert options == cli.LegacyUnknownOptions(
        crash_error="--crash arguments must be a number.",
    )


def test_parse_legacy_unknown_options_ignores_missing_legacy_values():
    assert cli.parse_legacy_unknown_options([]) == cli.LegacyUnknownOptions()


def test_clear_screen_decision_preserves_legacy_startup_skip():
    assert cli.clear_screen_decision(clear=False, fir_start=True, os_name="posix") == (
        cli.ClearScreenDecision(None, True)
    )
    assert cli.clear_screen_decision(clear=True, fir_start=True, os_name="posix") == (
        cli.ClearScreenDecision(None, False)
    )


def test_clear_screen_decision_preserves_posix_and_windows_actions():
    assert cli.clear_screen_decision(clear=True, fir_start=False, os_name="posix") == (
        cli.ClearScreenDecision("ansi_reset", False)
    )
    assert cli.clear_screen_decision(clear=True, fir_start=False, os_name="nt") == (
        cli.ClearScreenDecision("cls", False)
    )
    assert cli.clear_screen_decision(clear=True, fir_start=False, os_name="weird") == (
        cli.ClearScreenDecision(None, False)
    )


def test_output_file_dir_preserves_empty_default_and_trailing_separator():
    assert cli.output_file_dir(None, abspath=lambda value: "/abs/" + value, join=lambda *parts: "/".join(parts)) == ""
    assert (
        cli.output_file_dir("out", abspath=lambda value: "/abs/" + value, join=lambda *parts: "/".join(parts))
        == "/abs/out/"
    )


def test_runtime_flags_pause_debug_enables_debug():
    flags = cli.runtime_flags_from_args(args(PAUSEDEBUG=True))

    assert flags.debug is True
    assert flags.debug_file is False
    assert flags.pause_debug is True
    assert flags.auto is False


def test_runtime_flags_debug_file_does_not_enable_terminal_debug_without_debug_arg():
    flags = cli.runtime_flags_from_args(args(DEBUGFILE=True))

    assert flags.debug is False
    assert flags.debug_file is True
    assert flags.pause_debug is False
    assert flags.auto is False


def test_runtime_flags_preserves_no_color_mode():
    assert cli.runtime_flags_from_args(args(NO_COLOR=True)).color_mode == "never"
    assert cli.runtime_flags_from_args(args()).color_mode == "auto"


def test_runtime_flags_stfu_keeps_debug_file_without_terminal_debug():
    flags = cli.runtime_flags_from_args(args(NODIALOGUE=True, DEBUGFILE=True))

    assert flags.debug is False
    assert flags.debug_file is True
    assert flags.nodialogue is True
    assert flags.pause_debug is False
    assert flags.auto is True


def test_runtime_flags_nodialogue_preserves_stfu_side_effects():
    flags = cli.runtime_flags_from_args(
        args(
            CLEAR=True,
            PAUSE=True,
            PAUSEDEBUG=True,
            PAUSEERROR=True,
            PAUSEDIALOGUE=True,
            NODIALOGUE=True,
            DEBUG=True,
            AUTO=False,
        )
    )

    assert flags == cli.RuntimeFlags(
        clear=False,
        pause=False,
        pause_debug=False,
        pause_error=False,
        pause_dialogue=False,
        nodialogue=True,
        debug=False,
        debug_file=False,
        auto=True,
        color_mode="auto",
    )


def main():
    checks = [
        ("parser options", test_configure_parser_preserves_legacy_options),
        ("parser arguments", test_configure_parser_parses_runtime_arguments),
        ("legacy unknown clone/crash", test_parse_legacy_unknown_options_preserves_clone_and_crash),
        ("legacy unknown invalid crash", test_parse_legacy_unknown_options_reports_invalid_crash),
        ("legacy unknown empty", test_parse_legacy_unknown_options_ignores_missing_legacy_values),
        ("clear screen startup skip", test_clear_screen_decision_preserves_legacy_startup_skip),
        ("clear screen actions", test_clear_screen_decision_preserves_posix_and_windows_actions),
        ("max-saves validation", test_max_saves_error_preserves_legacy_validation),
        ("output dir prefix", test_output_file_dir_preserves_empty_default_and_trailing_separator),
        ("pause-debug flags", test_runtime_flags_pause_debug_enables_debug),
        ("debug-file flags", test_runtime_flags_debug_file_does_not_enable_terminal_debug_without_debug_arg),
        ("no-color flags", test_runtime_flags_preserves_no_color_mode),
        ("stfu debug-file flags", test_runtime_flags_stfu_keeps_debug_file_without_terminal_debug),
        ("stfu flags", test_runtime_flags_nodialogue_preserves_stfu_side_effects),
        ("ultimate preview timeout validation", test_ultimate_linefeed_preview_timeout_error_preserves_guardrail),
        ("ultimate resume validation", test_ultimate_linefeed_resume_error_preserves_guardrail),
    ]

    print("Running CLI config tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"CLI config tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
