from __future__ import annotations

from argparse import Action, HelpFormatter, SUPPRESS
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


class ChunklateHelpFormatter(HelpFormatter):
    def __init__(self, prog: str):
        super().__init__(prog, max_help_position=72, width=140)

    def _format_action_invocation(self, action):
        if (
            getattr(action, "dest", None) == "ULTIMATE_LINEFEED_REFERENCE"
            and action.option_strings == ["-ulfr"]
        ):
            return "-ulfr exact|similar PATH"
        return super()._format_action_invocation(action)

    def _format_args(self, action, default_metavar):
        if (
            getattr(action, "dest", None) == "ULTIMATE_LINEFEED_REFERENCE"
            and action.option_strings == ["-ulfr"]
        ):
            return "exact|similar PATH"
        return super()._format_args(action, default_metavar)

    def _format_action(self, action):
        if action.help is SUPPRESS:
            return ""
        invocation = self._format_action_invocation(action)
        if not action.help:
            return "%*s%s\n" % (self._current_indent, "", invocation)

        help_text = self._expand_help(action)
        available_width = max(
            40,
            self._width - self._current_indent - len(invocation) - 4,
        )
        help_lines = self._split_lines(help_text, available_width)
        if not help_lines:
            return "%*s%s\n" % (self._current_indent, "", invocation)

        lines = [
            "%*s%s    %s\n"
            % (self._current_indent, "", invocation, help_lines[0])
        ]
        continuation = " " * (self._current_indent + len(invocation) + 4)
        lines.extend("%s%s\n" % (continuation, line) for line in help_lines[1:])

        for subaction in self._iter_indented_subactions(action):
            lines.append(self._format_action(subaction))
        return "".join(lines)


class UltimateLinefeedReferenceAction(Action):
    def __call__(self, parser, namespace, values, option_string=None):
        parts = values if isinstance(values, list) else [values]
        if len(parts) == 1:
            setattr(namespace, "ULTIMATE_LINEFEED_REFERENCE", parts[0])
            return
        if len(parts) == 2 and str(parts[0]).strip().lower() in ("exact", "similar"):
            setattr(namespace, "ULTIMATE_LINEFEED_REFERENCE_MODE", str(parts[0]).strip().lower())
            setattr(namespace, "ULTIMATE_LINEFEED_REFERENCE", parts[1])
            return
        parser.error(f"{option_string or '-ulfr'} expects PATH or exact|similar PATH.")


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
    parser.formatter_class = ChunklateHelpFormatter
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
        "-workers",
        dest="GLOBAL_WORKERS",
        help="CPU workers for Ultimate and Smash: min, normal, max, or exact N.",
        default=None,
        metavar="min|normal|max|N",
    )
    parser.add_argument(
        "-gpu",
        dest="GPU",
        help="Allow GPU acceleration when supported.",
        action="store_true",
    )
    ultimate = parser.add_argument_group("ultimate line-feed")
    ultimate.add_argument(
        "-ulfb",
        "--ultimate-linefeed-budget",
        dest="ULTIMATE_LINEFEED_BUDGET",
        help=SUPPRESS,
        type=int,
        default=None,
        metavar="N",
    )
    ultimate.add_argument(
        "-ulfu",
        "--ultimate-linefeed-unbounded",
        dest="ULTIMATE_LINEFEED_UNBOUNDED",
        help=SUPPRESS,
        action="store_true",
    )
    ultimate.add_argument(
        "-ulfr",
        action=UltimateLinefeedReferenceAction,
        dest="ULTIMATE_LINEFEED_REFERENCE",
        help="Reference PNG and scoring mode for Ultimate candidates.",
        nargs="+",
        default=None,
        metavar="exact|similar PATH",
    )
    ultimate.add_argument(
        "-ulfrm",
        dest="ULTIMATE_LINEFEED_REFERENCE_MODE",
        help=SUPPRESS,
        choices=("exact", "similar"),
        default="exact",
        metavar="{exact,similar}",
    )
    ultimate.add_argument(
        "-ulfroi",
        "--ultimate-linefeed-reference-regions",
        dest="ULTIMATE_LINEFEED_REFERENCE_REGIONS",
        help=SUPPRESS,
        default=None,
        metavar="PATH",
    )
    ultimate.add_argument(
        "-ulfroi-edit",
        dest="ULTIMATE_LINEFEED_REFERENCE_REGION_EDITOR",
        help="Open the ROI editor before Ultimate.",
        action="store_true",
    )
    ultimate.add_argument(
        "-ulfpt",
        "--ultimate-linefeed-preview-timeout",
        dest="ULTIMATE_LINEFEED_PREVIEW_TIMEOUT",
        help=SUPPRESS,
        type=float,
        default=5.0,
        metavar="SECONDS",
    )
    ultimate.add_argument(
        "-ulfsp",
        dest="ULTIMATE_LINEFEED_SHOW_PREVIEWS",
        help="Open live Ultimate candidate previews.",
        action="store_true",
    )
    ultimate.add_argument(
        "-ulfgl",
        dest="ULTIMATE_LINEFEED_VISUAL_GALLERY_LIMIT",
        help="Saved visual candidate count.",
        type=int,
        default=100,
        metavar="N",
    )
    ultimate.add_argument(
        "-ulfmc",
        dest="ULTIMATE_LINEFEED_VISUAL_MIN_COVERAGE",
        help="Minimum gallery scanline coverage, 0..1.",
        type=float,
        default=0.95,
        metavar="FLOAT",
    )
    ultimate.add_argument(
        "-ulf-resume",
        "--ultimate-linefeed-resume",
        dest="ULTIMATE_LINEFEED_RESUME",
        help=SUPPRESS,
        choices=("ask", "auto", "never", "reset"),
        default="ask",
        metavar="MODE",
    )
    ultimate.add_argument(
        "-ulfw",
        "--ultimate-linefeed-workers",
        dest="ULTIMATE_LINEFEED_WORKERS",
        help=SUPPRESS,
        default=None,
        metavar="N|min|normal|max",
    )
    smash = parser.add_argument_group("smash brute brawl")
    smash.add_argument(
        "-sbb-resume",
        "--smashbrutebrawl-resume",
        dest="SMASH_BRUTE_BRAWL_RESUME",
        help=SUPPRESS,
        choices=("ask", "auto", "never", "reset"),
        default="ask",
        metavar="{ask,auto,never,reset}",
    )
    smash.add_argument(
        "-sbbw",
        "--smashbrutebrawl-workers",
        dest="SMASH_BRUTE_BRAWL_WORKERS",
        help=SUPPRESS,
        default=None,
        metavar="N|min|normal|max|auto",
    )
    smash.add_argument(
        "-sbbl",
        dest="SMASH_BRUTE_BRAWL_FORCE_LEVEL",
        help="Start SmashBruteBrawl at brute-force level N.",
        default=None,
        metavar="N",
    )
    parser.add_argument(
        "--ultimate-linefeed-reference",
        dest="ULTIMATE_LINEFEED_REFERENCE",
        default=SUPPRESS,
        help=SUPPRESS,
        metavar="PATH",
    )
    parser.add_argument(
        "--ultimate-linefeed-reference-mode",
        dest="ULTIMATE_LINEFEED_REFERENCE_MODE",
        choices=("exact", "similar"),
        default=SUPPRESS,
        help=SUPPRESS,
        metavar="{exact,similar}",
    )
    parser.add_argument(
        "--ultimate-linefeed-reference-region-editor",
        dest="ULTIMATE_LINEFEED_REFERENCE_REGION_EDITOR",
        action="store_true",
        default=SUPPRESS,
        help=SUPPRESS,
    )
    parser.add_argument(
        "--ultimate-linefeed-show-previews",
        dest="ULTIMATE_LINEFEED_SHOW_PREVIEWS",
        action="store_true",
        default=SUPPRESS,
        help=SUPPRESS,
    )
    parser.add_argument(
        "--ultimate-linefeed-visual-gallery-limit",
        dest="ULTIMATE_LINEFEED_VISUAL_GALLERY_LIMIT",
        type=int,
        default=SUPPRESS,
        help=SUPPRESS,
        metavar="N",
    )
    parser.add_argument(
        "--ultimate-linefeed-visual-min-coverage",
        dest="ULTIMATE_LINEFEED_VISUAL_MIN_COVERAGE",
        type=float,
        default=SUPPRESS,
        help=SUPPRESS,
        metavar="FLOAT",
    )
    parser.add_argument(
        "--ulfb",
        dest="ULTIMATE_LINEFEED_BUDGET",
        type=int,
        default=SUPPRESS,
        help=SUPPRESS,
        metavar="N",
    )
    parser.add_argument(
        "--ulfu",
        dest="ULTIMATE_LINEFEED_UNBOUNDED",
        action="store_true",
        default=SUPPRESS,
        help=SUPPRESS,
    )
    parser.add_argument(
        "--ulfr",
        dest="ULTIMATE_LINEFEED_REFERENCE",
        default=SUPPRESS,
        help=SUPPRESS,
        metavar="PATH",
    )
    parser.add_argument(
        "--ulfrm",
        dest="ULTIMATE_LINEFEED_REFERENCE_MODE",
        choices=("exact", "similar"),
        default=SUPPRESS,
        help=SUPPRESS,
        metavar="{exact,similar}",
    )
    parser.add_argument(
        "--ulfroi",
        dest="ULTIMATE_LINEFEED_REFERENCE_REGIONS",
        default=SUPPRESS,
        help=SUPPRESS,
        metavar="PATH",
    )
    parser.add_argument(
        "--ulfroi-edit",
        dest="ULTIMATE_LINEFEED_REFERENCE_REGION_EDITOR",
        action="store_true",
        default=SUPPRESS,
        help=SUPPRESS,
    )
    parser.add_argument(
        "--ulfpt",
        dest="ULTIMATE_LINEFEED_PREVIEW_TIMEOUT",
        type=float,
        default=SUPPRESS,
        help=SUPPRESS,
        metavar="SECONDS",
    )
    parser.add_argument(
        "--ulfsp",
        dest="ULTIMATE_LINEFEED_SHOW_PREVIEWS",
        action="store_true",
        default=SUPPRESS,
        help=SUPPRESS,
    )
    parser.add_argument(
        "--ulfgl",
        dest="ULTIMATE_LINEFEED_VISUAL_GALLERY_LIMIT",
        type=int,
        default=SUPPRESS,
        help=SUPPRESS,
        metavar="N",
    )
    parser.add_argument(
        "--ulfmc",
        dest="ULTIMATE_LINEFEED_VISUAL_MIN_COVERAGE",
        type=float,
        default=SUPPRESS,
        help=SUPPRESS,
        metavar="FLOAT",
    )
    parser.add_argument(
        "--ulf-resume",
        dest="ULTIMATE_LINEFEED_RESUME",
        choices=("ask", "auto", "never", "reset"),
        default=SUPPRESS,
        help=SUPPRESS,
        metavar="{ask,auto,never,reset}",
    )
    parser.add_argument(
        "--ulfw",
        dest="ULTIMATE_LINEFEED_WORKERS",
        default=SUPPRESS,
        help=SUPPRESS,
        metavar="N|min|normal|max",
    )
    parser.add_argument(
        "--ulf-budget",
        dest="ULTIMATE_LINEFEED_BUDGET",
        type=int,
        default=SUPPRESS,
        help=SUPPRESS,
        metavar="N",
    )
    parser.add_argument(
        "--ulf-unbounded",
        dest="ULTIMATE_LINEFEED_UNBOUNDED",
        action="store_true",
        default=SUPPRESS,
        help=SUPPRESS,
    )
    parser.add_argument(
        "--ulf-reference",
        dest="ULTIMATE_LINEFEED_REFERENCE",
        default=SUPPRESS,
        help=SUPPRESS,
        metavar="PATH",
    )
    parser.add_argument(
        "--ulf-reference-mode",
        dest="ULTIMATE_LINEFEED_REFERENCE_MODE",
        choices=("exact", "similar"),
        default=SUPPRESS,
        help=SUPPRESS,
        metavar="{exact,similar}",
    )
    parser.add_argument(
        "--ulf-reference-regions",
        dest="ULTIMATE_LINEFEED_REFERENCE_REGIONS",
        default=SUPPRESS,
        help=SUPPRESS,
        metavar="PATH",
    )
    parser.add_argument(
        "--ulf-reference-region-editor",
        dest="ULTIMATE_LINEFEED_REFERENCE_REGION_EDITOR",
        action="store_true",
        default=SUPPRESS,
        help=SUPPRESS,
    )
    parser.add_argument(
        "--ulf-preview-timeout",
        dest="ULTIMATE_LINEFEED_PREVIEW_TIMEOUT",
        type=float,
        default=SUPPRESS,
        help=SUPPRESS,
        metavar="SECONDS",
    )
    parser.add_argument(
        "--ulf-show-previews",
        dest="ULTIMATE_LINEFEED_SHOW_PREVIEWS",
        action="store_true",
        default=SUPPRESS,
        help=SUPPRESS,
    )
    parser.add_argument(
        "--ulf-gallery-limit",
        dest="ULTIMATE_LINEFEED_VISUAL_GALLERY_LIMIT",
        type=int,
        default=SUPPRESS,
        help=SUPPRESS,
        metavar="N",
    )
    parser.add_argument(
        "--ulf-min-coverage",
        dest="ULTIMATE_LINEFEED_VISUAL_MIN_COVERAGE",
        type=float,
        default=SUPPRESS,
        help=SUPPRESS,
        metavar="FLOAT",
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


def ultimate_linefeed_reference_mode_error(mode: str | None) -> str | None:
    if str(mode or "exact").strip().lower() not in ("exact", "similar"):
        return "--ultimate-linefeed-reference-mode must be one of: exact, similar."
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


def ultimate_linefeed_workers_error(workers: object) -> str | None:
    if workers is None:
        return None
    text = str(workers).strip().lower()
    if text in ("auto", "min", "normal", "max"):
        return None
    try:
        value = int(text)
    except (TypeError, ValueError):
        return "--ultimate-linefeed-workers must be a non-negative integer, min, normal, or max."
    if value < 0:
        return "--ultimate-linefeed-workers must be a non-negative integer, min, normal, or max."
    return None


def smash_brute_brawl_resume_error(mode: str | None) -> str | None:
    if str(mode or "ask").strip().lower() not in ("ask", "auto", "never", "reset"):
        return "--smashbrutebrawl-resume must be one of: ask, auto, never, reset."
    return None


def smash_brute_brawl_workers_error(workers: object) -> str | None:
    if workers is None:
        return None
    text = str(workers).strip().lower()
    if text in ("auto", "min", "normal", "max"):
        return None
    try:
        value = int(text)
    except (TypeError, ValueError):
        return "--smashbrutebrawl-workers must be a non-negative integer, min, normal, max, or auto."
    if value < 0:
        return "--smashbrutebrawl-workers must be a non-negative integer, min, normal, max, or auto."
    return None


def smash_brute_brawl_level_error(level: object) -> str | None:
    if level is None:
        return None
    try:
        value = int(str(level).strip())
    except (TypeError, ValueError):
        return "-sbbl must be a non-negative integer."
    if value < 0:
        return "-sbbl must be a non-negative integer."
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
