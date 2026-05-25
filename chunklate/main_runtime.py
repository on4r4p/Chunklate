from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from . import cli


@dataclass(frozen=True)
class MainCliOptionsRuntime:
    print_error: Callable[[str], Any]
    exit_process: Callable[[int], Any]
    make_dirs: Callable[..., Any]
    abspath: Callable[[str], str]
    join: Callable[..., str]
    stderr: Any
    parse_legacy_unknown_options: Callable = cli.parse_legacy_unknown_options
    max_saves_error: Callable = cli.max_saves_error
    output_file_dir: Callable = cli.output_file_dir
    runtime_flags_from_args: Callable = cli.runtime_flags_from_args


@dataclass(frozen=True)
class MainCliOptionsState:
    file_origin: str
    file_dir: str
    runtime_flags: cli.RuntimeFlags
    max_saves: int | None
    save_count: int
    sample: str
    cloneswar: Any
    crash: Any


def apply_main_cli_options(
    runtime: MainCliOptionsRuntime,
    args: Any,
    unknown: list[str] | tuple[str, ...],
    *,
    argv_len: int,
    parser: Any,
    current_cloneswar: Any,
    current_crash: Any,
) -> MainCliOptionsState | None:
    cloneswar = current_cloneswar
    crash = current_crash

    legacy_unknown = runtime.parse_legacy_unknown_options(unknown)
    if legacy_unknown.cloneswar is not None:
        cloneswar = legacy_unknown.cloneswar
    if legacy_unknown.crash_error is not None:
        runtime.print_error(legacy_unknown.crash_error)
        runtime.exit_process(1)
        return None
    if legacy_unknown.crash is not None:
        crash = legacy_unknown.crash

    if argv_len == 1:
        parser.print_help(runtime.stderr)
        runtime.exit_process(1)
        return None
    if args.FILENAME is None:
        runtime.print_error("-f,--filename arguments is missing.")
        runtime.exit_process(1)
        return None

    max_saves_error = runtime.max_saves_error(args.MAX_SAVES)
    if max_saves_error is not None:
        runtime.print_error(max_saves_error)
        runtime.exit_process(1)
        return None

    file_origin = args.FILENAME
    file_dir = runtime.output_file_dir(
        args.OUTPUT_DIR,
        abspath=runtime.abspath,
        join=runtime.join,
    )
    if file_dir:
        runtime.make_dirs(file_dir, exist_ok=True)

    return MainCliOptionsState(
        file_origin=file_origin,
        file_dir=file_dir,
        runtime_flags=runtime.runtime_flags_from_args(args),
        max_saves=args.MAX_SAVES,
        save_count=0,
        sample=file_origin,
        cloneswar=cloneswar,
        crash=crash,
    )


def legacy_globals_from_main_cli_options(options: MainCliOptionsState) -> dict[str, Any]:
    flags = options.runtime_flags
    return {
        "FILE_Origin": options.file_origin,
        "FILE_DIR": options.file_dir,
        "CLEAR": flags.clear,
        "PAUSE": flags.pause,
        "PAUSEDEBUG": flags.pause_debug,
        "PAUSEERROR": flags.pause_error,
        "PAUSEDIALOGUE": flags.pause_dialogue,
        "NODIALOGUE": flags.nodialogue,
        "DEBUG": flags.debug,
        "AUTO": flags.auto,
        "MAX_SAVES": options.max_saves,
        "SAVE_COUNT": options.save_count,
        "Sample": options.sample,
        "CLONESWAR": options.cloneswar,
        "CRASH": options.crash,
    }
