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
        "AUTO": False,
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
    assert "--pause-debug" in help_text
    assert "--pause-error" in help_text
    assert "--pause-dialogue" in help_text
    assert "--shut-the-fuck-up" in help_text
    assert "--auto" in help_text
    assert "--output-dir DIR" in help_text
    assert "--max-saves N" in help_text


def test_configure_parser_parses_runtime_arguments():
    parser = cli.configure_parser(ArgumentParser())

    parsed = parser.parse_args(
        [
            "-f",
            "sample.png",
            "--clear",
            "-p",
            "-d",
            "-dp",
            "-ep",
            "-sp",
            "-stfu",
            "-a",
            "--output-dir",
            "out",
            "--max-saves",
            "2",
        ]
    )

    assert parsed.FILENAME == "sample.png"
    assert parsed.CLEAR is True
    assert parsed.PAUSE is True
    assert parsed.DEBUG is True
    assert parsed.PAUSEDEBUG is True
    assert parsed.PAUSEERROR is True
    assert parsed.PAUSEDIALOGUE is True
    assert parsed.NODIALOGUE is True
    assert parsed.AUTO is True
    assert parsed.OUTPUT_DIR == "out"
    assert parsed.MAX_SAVES == 2


def test_output_file_dir_preserves_empty_default_and_trailing_separator():
    assert cli.output_file_dir(None, abspath=lambda value: "/abs/" + value, join=lambda *parts: "/".join(parts)) == ""
    assert (
        cli.output_file_dir("out", abspath=lambda value: "/abs/" + value, join=lambda *parts: "/".join(parts))
        == "/abs/out/"
    )


def test_runtime_flags_pause_debug_enables_debug():
    flags = cli.runtime_flags_from_args(args(PAUSEDEBUG=True))

    assert flags.debug is True
    assert flags.pause_debug is True
    assert flags.auto is False


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
        auto=True,
    )


def main():
    checks = [
        ("parser options", test_configure_parser_preserves_legacy_options),
        ("parser arguments", test_configure_parser_parses_runtime_arguments),
        ("max-saves validation", test_max_saves_error_preserves_legacy_validation),
        ("output dir prefix", test_output_file_dir_preserves_empty_default_and_trailing_separator),
        ("pause-debug flags", test_runtime_flags_pause_debug_enables_debug),
        ("stfu flags", test_runtime_flags_nodialogue_preserves_stfu_side_effects),
    ]

    print("Running CLI config tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"CLI config tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
