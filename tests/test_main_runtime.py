#!/usr/bin/env python3
import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import cli, main_runtime


class ExitReached(Exception):
    def __init__(self, code):
        self.code = code


class FakeParser:
    def __init__(self, calls):
        self.calls = calls

    def print_help(self, stream):
        self.calls.append(("print_help", stream))


def args(**updates):
    values = {
        "FILENAME": "sample.png",
        "OUTPUT_DIR": None,
        "MAX_SAVES": None,
        "CLEAR": False,
        "PAUSE": False,
        "PAUSEDEBUG": False,
        "PAUSEERROR": False,
        "PAUSEDIALOGUE": False,
        "NODIALOGUE": False,
        "DEBUG": False,
        "AUTO": False,
    }
    values.update(updates)
    return SimpleNamespace(**values)


def build_runtime(calls, *, exit_raises=True):
    def exit_process(code):
        calls.append(("exit", code))
        if exit_raises:
            raise ExitReached(code)

    return main_runtime.MainCliOptionsRuntime(
        print_error=lambda message: calls.append(("print", message)),
        exit_process=exit_process,
        make_dirs=lambda path, **kwargs: calls.append(("makedirs", path, kwargs)),
        abspath=lambda path: "/abs/" + path,
        join=lambda *parts: "/".join(parts),
        stderr="stderr",
    )


def apply_options(calls, parsed_args=None, unknown=(), argv_len=2):
    if parsed_args is None:
        parsed_args = args()
    return main_runtime.apply_main_cli_options(
        build_runtime(calls),
        parsed_args,
        unknown,
        argv_len=argv_len,
        parser=FakeParser(calls),
        current_cloneswar=False,
        current_crash=False,
    )


def test_apply_main_cli_options_builds_initial_state():
    calls = []

    state = apply_options(
        calls,
        args(OUTPUT_DIR="out", MAX_SAVES=2, PAUSEDEBUG=True),
    )

    assert state == main_runtime.MainCliOptionsState(
        file_origin="sample.png",
        file_dir="/abs/out/",
        runtime_flags=cli.RuntimeFlags(
            clear=False,
            pause=False,
            pause_debug=True,
            pause_error=False,
            pause_dialogue=False,
            nodialogue=False,
            debug=True,
            auto=False,
        ),
        max_saves=2,
        save_count=0,
        sample="sample.png",
        cloneswar=False,
        crash=False,
    )
    assert ("makedirs", "/abs/out/", {"exist_ok": True}) in calls


def test_apply_main_cli_options_preserves_legacy_unknown_clone_and_crash():
    calls = []

    state = apply_options(calls, unknown=["--CLONE", "Folder/sample.png", "--crash", "3"])

    assert state.cloneswar == "Folder/sample.png --crash 3"
    assert state.crash == 3


def test_apply_main_cli_options_exits_on_invalid_crash():
    calls = []

    try:
        apply_options(calls, unknown=["--crash", "nope"])
    except ExitReached as exc:
        assert exc.code == 1
    else:
        raise AssertionError("invalid crash should exit")

    assert ("print", "--crash arguments must be a number.") in calls
    assert ("exit", 1) in calls


def test_apply_main_cli_options_prints_help_without_args():
    calls = []

    try:
        apply_options(calls, argv_len=1)
    except ExitReached as exc:
        assert exc.code == 1
    else:
        raise AssertionError("missing argv should exit")

    assert ("print_help", "stderr") in calls
    assert ("exit", 1) in calls


def test_apply_main_cli_options_exits_without_filename():
    calls = []

    try:
        apply_options(calls, args(FILENAME=None))
    except ExitReached as exc:
        assert exc.code == 1
    else:
        raise AssertionError("missing filename should exit")

    assert ("print", "-f,--filename arguments is missing.") in calls
    assert ("exit", 1) in calls


def test_apply_main_cli_options_exits_on_bad_max_saves():
    calls = []

    try:
        apply_options(calls, args(MAX_SAVES=0))
    except ExitReached as exc:
        assert exc.code == 1
    else:
        raise AssertionError("bad max saves should exit")

    assert ("print", "--max-saves arguments must be greater than zero.") in calls
    assert ("exit", 1) in calls


def test_legacy_globals_from_main_cli_options_maps_runtime_flags():
    state = main_runtime.MainCliOptionsState(
        file_origin="sample.png",
        file_dir="/tmp/",
        runtime_flags=cli.RuntimeFlags(
            clear=True,
            pause=True,
            pause_debug=False,
            pause_error=True,
            pause_dialogue=False,
            nodialogue=False,
            debug=True,
            auto=False,
        ),
        max_saves=4,
        save_count=0,
        sample="sample.png",
        cloneswar="clone.png",
        crash=9,
    )

    assert main_runtime.legacy_globals_from_main_cli_options(state) == {
        "FILE_Origin": "sample.png",
        "FILE_DIR": "/tmp/",
        "CLEAR": True,
        "PAUSE": True,
        "PAUSEDEBUG": False,
        "PAUSEERROR": True,
        "PAUSEDIALOGUE": False,
        "NODIALOGUE": False,
        "DEBUG": True,
        "AUTO": False,
        "MAX_SAVES": 4,
        "SAVE_COUNT": 0,
        "Sample": "sample.png",
        "CLONESWAR": "clone.png",
        "CRASH": 9,
    }


def main():
    checks = [
        ("main options state", test_apply_main_cli_options_builds_initial_state),
        ("legacy clone/crash", test_apply_main_cli_options_preserves_legacy_unknown_clone_and_crash),
        ("invalid crash", test_apply_main_cli_options_exits_on_invalid_crash),
        ("help without args", test_apply_main_cli_options_prints_help_without_args),
        ("missing filename", test_apply_main_cli_options_exits_without_filename),
        ("bad max saves", test_apply_main_cli_options_exits_on_bad_max_saves),
        ("legacy globals", test_legacy_globals_from_main_cli_options_maps_runtime_flags),
    ]

    print("Running main runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"main runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
