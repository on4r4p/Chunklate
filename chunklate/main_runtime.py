from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from . import cli, runtime_state


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


@dataclass(frozen=True)
class MainLoopResetRuntime:
    namespace: dict[str, Any]
    reset_chunk_info_idat: Callable[[], Any]
    sync_chunk_info_legacy_state: Callable[[str], Any]
    banner: Callable[[int], Any]
    scan_reset_values: Callable = runtime_state.main_loop_scan_reset_values
    error_reset_values: Callable = runtime_state.main_loop_error_reset_values
    history_reset_values: Callable = runtime_state.main_loop_history_reset_values


@dataclass(frozen=True)
class MainLoopResetState:
    tmp_fix_ihdr: bool


@dataclass(frozen=True)
class MainSampleRuntime:
    basename: Callable[[Any], str]
    load_sample_data: Callable = runtime_state.load_sample_data
    select_sample: Callable = runtime_state.select_sample
    raw_print: Callable[..., Any] = print
    candy: Callable[..., Any] = lambda *args, **kwargs: ""
    emit: Callable[[str], Any] = print
    betterror: Callable[[Exception, str], Any] = lambda error, name: None
    exit_process: Callable[[int], Any] = lambda code: None


@dataclass(frozen=True)
class MainSampleContext:
    sample: Any
    cloneswar: Any


@dataclass(frozen=True)
class MainSampleState:
    sample: Any
    sample_name: str
    cloneswar: Any
    data_bytes: bytes
    data_hex: str


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


def reset_main_loop_state(runtime: MainLoopResetRuntime) -> MainLoopResetState:
    runtime.namespace.update(runtime.scan_reset_values())
    runtime.reset_chunk_info_idat()
    runtime.sync_chunk_info_legacy_state("idat")

    runtime.namespace.update(runtime.error_reset_values())
    tmp_fix_ihdr = False

    runtime.namespace.update(runtime.history_reset_values())
    runtime.reset_chunk_info_idat()
    runtime.sync_chunk_info_legacy_state("idat")
    runtime.banner(1)

    return MainLoopResetState(tmp_fix_ihdr=tmp_fix_ihdr)


def load_main_sample(
    runtime: MainSampleRuntime,
    context: MainSampleContext,
) -> MainSampleState | None:
    sample_selection = runtime.select_sample(
        context.sample,
        context.cloneswar,
        basename=runtime.basename,
    )

    runtime.raw_print(
        "-Proceeding with: %s"
        % runtime.candy("Color", "white", sample_selection.sample_name)
    )
    try:
        loaded_sample = runtime.load_sample_data(sample_selection.sample)
    except Exception as exc:
        runtime.betterror(exc, "main")
        runtime.emit(
            runtime.candy("Color", "red", "Error:%s")
            % runtime.candy("Color", "yellow", exc)
        )
        runtime.exit_process(1)
        return None

    runtime.candy(
        "Cowsay",
        " %s is loaded!" % runtime.candy("Color", "green", sample_selection.sample_name),
        "good",
    )
    return MainSampleState(
        sample=sample_selection.sample,
        sample_name=sample_selection.sample_name,
        cloneswar=sample_selection.cloneswar,
        data_bytes=loaded_sample.data_bytes,
        data_hex=loaded_sample.data_hex,
    )
