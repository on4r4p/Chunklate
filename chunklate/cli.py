from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RuntimeFlags:
    clear: bool
    pause: bool
    pause_debug: bool
    pause_error: bool
    pause_dialogue: bool
    nodialogue: bool
    debug: bool
    debug_file: bool
    auto: bool
    color_mode: str


@dataclass(frozen=True)
class LegacyUnknownOptions:
    cloneswar: str | bool | None = None
    crash: int | bool | None = None
    crash_error: str | None = None


@dataclass(frozen=True)
class ClearScreenDecision:
    action: str | None
    fir_start: bool


def clear_screen_decision(*, clear: bool, fir_start: bool, os_name: str) -> ClearScreenDecision:
    if clear is not True:
        return ClearScreenDecision(None, fir_start)
    if fir_start is False:
        if os_name == "posix":
            return ClearScreenDecision("ansi_reset", fir_start)
        if os_name == "nt":
            return ClearScreenDecision("cls", fir_start)
        return ClearScreenDecision(None, fir_start)
    return ClearScreenDecision(None, False)


def configure_parser(parser: Any) -> Any:
    parser.add_argument(
        "-f", "--file", dest="FILENAME", help="File path.", default=None, metavar="FILE"
    )
    parser.add_argument(
        "-c",
        "--CLEAR",
        "--clear",
        dest="CLEAR",
        help="CLEAR screen at each saves.",
        action="store_true",
    )
    parser.add_argument(
        "-p", "--pause", dest="PAUSE", help="Pause at each saves.", action="store_true"
    )
    parser.add_argument(
        "-d", "--debug", dest="DEBUG", help="Debug stuffs.", action="store_true"
    )
    parser.add_argument(
        "-df",
        "--debug-file",
        dest="DEBUGFILE",
        help="Append debug output to the normal summary file.",
        action="store_true",
    )
    parser.add_argument(
        "-dp",
        "--pause-debug",
        dest="PAUSEDEBUG",
        help="Pause at Debug stuffs.",
        action="store_true",
    )
    parser.add_argument(
        "-ep",
        "--pause-error",
        dest="PAUSEERROR",
        help="Pause at errors.",
        action="store_true",
    )
    parser.add_argument(
        "-sp",
        "--pause-dialogue",
        dest="PAUSEDIALOGUE",
        help="Pause at dialogues.",
        action="store_true",
    )

    parser.add_argument(
        "-stfu",
        "--shut-the-fuck-up",
        dest="NODIALOGUE",
        help="Show minimal output.",
        action="store_true",
    )
    parser.add_argument(
        "-a", "--auto", dest="AUTO", help="Auto Choose action.", action="store_true"
    )
    parser.add_argument(
        "--no-color",
        dest="NO_COLOR",
        help="Disable terminal colors.",
        action="store_true",
    )
    parser.add_argument(
        "--output-dir",
        dest="OUTPUT_DIR",
        help="Directory where Folder_* repair outputs are written.",
        default=None,
        metavar="DIR",
    )
    parser.add_argument(
        "--max-saves",
        dest="MAX_SAVES",
        help="Exit successfully after writing N repaired files.",
        type=int,
        default=None,
        metavar="N",
    )
    parser.add_argument(
        "--ultimate-linefeed-budget",
        dest="ULTIMATE_LINEFEED_BUDGET",
        help="Maximum candidates for UltimateMegaSuperLineFeedBruteForce.",
        type=int,
        default=None,
        metavar="N",
    )
    parser.add_argument(
        "--ultimate-linefeed-unbounded",
        dest="ULTIMATE_LINEFEED_UNBOUNDED",
        help="Run UltimateMegaSuperLineFeedBruteForce without a candidate budget.",
        action="store_true",
    )
    return parser


def parse_legacy_unknown_options(unknown: list[str] | tuple[str, ...] | str) -> LegacyUnknownOptions:
    unknown_text = unknown if isinstance(unknown, str) else " ".join([item for item in unknown])
    cloneswar: str | bool | None = None
    crash: int | bool | None = None
    crash_error: str | None = None

    if "--CLONE" in unknown_text:
        cloneswar = unknown_text.split("--CLONE ")[1]

    if "--crash" in unknown_text:
        crash_value = unknown_text.split("--crash ")[1]
        if not str(crash_value).isdigit():
            crash_error = "--crash arguments must be a number."
        else:
            crash = int(crash_value)

    return LegacyUnknownOptions(cloneswar=cloneswar, crash=crash, crash_error=crash_error)


def max_saves_error(max_saves: int | None) -> str | None:
    if max_saves is not None and max_saves < 1:
        return "--max-saves arguments must be greater than zero."
    return None


def ultimate_linefeed_budget_error(
    ultimate_linefeed_budget: int | None,
    ultimate_linefeed_unbounded: bool = False,
) -> str | None:
    if ultimate_linefeed_unbounded:
        return None
    if ultimate_linefeed_budget is not None and ultimate_linefeed_budget < 1:
        return "--ultimate-linefeed-budget arguments must be greater than zero."
    return None


def output_file_dir(output_dir: str | None, *, abspath, join) -> str:
    if output_dir is None:
        return ""
    return join(abspath(output_dir), "")


def runtime_flags_from_args(args: Any) -> RuntimeFlags:
    clear = args.CLEAR
    pause = args.PAUSE
    pause_debug = args.PAUSEDEBUG
    pause_error = args.PAUSEERROR
    pause_dialogue = args.PAUSEDIALOGUE
    nodialogue = args.NODIALOGUE
    debug_file = bool(getattr(args, "DEBUGFILE", False))
    debug = args.DEBUG
    auto = args.AUTO
    color_mode = "never" if bool(getattr(args, "NO_COLOR", False)) else "auto"

    if pause_debug is True:
        debug = True

    if nodialogue:
        auto = True
        debug = False
        pause_debug = False
        pause_dialogue = False
        pause_error = False
        pause = False
        clear = False

    return RuntimeFlags(
        clear=clear,
        pause=pause,
        pause_debug=pause_debug,
        pause_error=pause_error,
        pause_dialogue=pause_dialogue,
        nodialogue=nodialogue,
        debug=debug,
        debug_file=debug_file,
        auto=auto,
        color_mode=color_mode,
    )
