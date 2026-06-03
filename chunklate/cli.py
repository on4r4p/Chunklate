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
    parser.add_argument(
        "--ultimate-linefeed-reference",
        dest="ULTIMATE_LINEFEED_REFERENCE",
        help="Optional local PNG reference used to rank ultimate line-feed candidates.",
        default=None,
        metavar="PATH",
    )
    parser.add_argument(
        "--ultimate-linefeed-preview-timeout",
        dest="ULTIMATE_LINEFEED_PREVIEW_TIMEOUT",
        help="Seconds to keep each opened live ultimate preview visible when --ultimate-linefeed-show-previews is set.",
        type=float,
        default=5.0,
        metavar="SECONDS",
    )
    parser.add_argument(
        "--ultimate-linefeed-show-previews",
        dest="ULTIMATE_LINEFEED_SHOW_PREVIEWS",
        help="Open live valid ultimate line-feed candidate previews during brute force; files are still saved without this.",
        action="store_true",
    )
    parser.add_argument(
        "--ultimate-linefeed-visual-gallery-limit",
        dest="ULTIMATE_LINEFEED_VISUAL_GALLERY_LIMIT",
        help="Maximum rebuilt visual candidates kept by UltimateMegaSuperLineFeedBruteForce.",
        type=int,
        default=100,
        metavar="N",
    )
    parser.add_argument(
        "--ultimate-linefeed-visual-min-coverage",
        dest="ULTIMATE_LINEFEED_VISUAL_MIN_COVERAGE",
        help="Minimum usable scanline coverage for rebuilt visual gallery candidates.",
        type=float,
        default=0.95,
        metavar="FLOAT",
    )
    parser.add_argument(
        "--ultimate-linefeed-resume",
        dest="ULTIMATE_LINEFEED_RESUME",
        help="How UltimateMegaSuperLineFeedBruteForce handles an existing progress checkpoint.",
        choices=("ask", "auto", "never", "reset"),
        default="ask",
        metavar="MODE",
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


def ultimate_linefeed_preview_timeout_error(timeout: float | int | None) -> str | None:
    if timeout is not None and float(timeout) < 0:
        return "--ultimate-linefeed-preview-timeout arguments must be zero or greater."
    return None


def ultimate_linefeed_visual_gallery_limit_error(limit: int | None) -> str | None:
    if limit is not None and int(limit) < 0:
        return "--ultimate-linefeed-visual-gallery-limit arguments must be zero or greater."
    return None


def ultimate_linefeed_visual_min_coverage_error(coverage: float | int | None) -> str | None:
    if coverage is not None and not 0.0 <= float(coverage) <= 1.0:
        return "--ultimate-linefeed-visual-min-coverage arguments must be between 0 and 1."
    return None


def ultimate_linefeed_resume_error(mode: str | None) -> str | None:
    if str(mode or "ask").strip().lower() not in ("ask", "auto", "never", "reset"):
        return "--ultimate-linefeed-resume must be one of: ask, auto, never, reset."
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
