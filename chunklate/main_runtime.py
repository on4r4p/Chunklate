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
class MainClearScreenRuntime:
    stderr_write: Callable[[str], Any]
    system: Callable[[str], Any]
    os_name: str
    clear_screen_decision: Callable = cli.clear_screen_decision


@dataclass(frozen=True)
class MainClearScreenContext:
    clear: bool
    fir_start: bool


@dataclass(frozen=True)
class MainClearScreenState:
    fir_start: bool


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


@dataclass(frozen=True)
class MainChunkWalkRuntime:
    namespace: dict[str, Any]
    chunk_by_chunk: Callable[[int], Any]
    check_length: Callable[..., Any]
    check_chunk_name: Callable[..., Any]
    get_info: Callable[..., Any]
    checksum: Callable[..., Any]
    fix_it_felix: Callable[[Any], Any]
    next_chunk_offset: Callable = runtime_state.next_chunk_offset
    kitkat_break_decision: Callable = runtime_state.kitkat_break_decision


@dataclass(frozen=True)
class MainChunkWalkContext:
    offset: Any
    data_hex: str


@dataclass(frozen=True)
class MainChunkWalkState:
    offset: Any


def build_cli_options_runtime(
    *,
    print_error: Callable[[str], Any],
    exit_process: Callable[[int], Any],
    make_dirs: Callable[..., Any],
    abspath: Callable[[str], str],
    join: Callable[..., str],
    stderr: Any,
) -> MainCliOptionsRuntime:
    return MainCliOptionsRuntime(
        print_error=print_error,
        exit_process=exit_process,
        make_dirs=make_dirs,
        abspath=abspath,
        join=join,
        stderr=stderr,
    )


def build_loop_reset_runtime(
    *,
    namespace: dict[str, Any],
    reset_chunk_info_idat: Callable[[], Any],
    sync_chunk_info_legacy_state: Callable[[str], Any],
    banner: Callable[[int], Any],
) -> MainLoopResetRuntime:
    return MainLoopResetRuntime(
        namespace=namespace,
        reset_chunk_info_idat=reset_chunk_info_idat,
        sync_chunk_info_legacy_state=sync_chunk_info_legacy_state,
        banner=banner,
    )


def build_clear_screen_runtime(
    *,
    stderr_write: Callable[[str], Any],
    system: Callable[[str], Any],
    os_name: str,
) -> MainClearScreenRuntime:
    return MainClearScreenRuntime(
        stderr_write=stderr_write,
        system=system,
        os_name=os_name,
    )


def build_sample_runtime(
    *,
    basename: Callable[[Any], str],
    load_sample_data: Callable,
    raw_print: Callable[..., Any],
    candy: Callable[..., Any],
    emit: Callable[[str], Any],
    betterror: Callable[[Exception, str], Any],
    exit_process: Callable[[int], Any],
) -> MainSampleRuntime:
    return MainSampleRuntime(
        basename=basename,
        load_sample_data=load_sample_data,
        raw_print=raw_print,
        candy=candy,
        emit=emit,
        betterror=betterror,
        exit_process=exit_process,
    )


def build_chunk_walk_runtime(
    *,
    namespace: dict[str, Any],
    chunk_by_chunk: Callable[[int], Any],
    check_length: Callable[..., Any],
    check_chunk_name: Callable[..., Any],
    get_info: Callable[..., Any],
    checksum: Callable[..., Any],
    fix_it_felix: Callable[[Any], Any],
) -> MainChunkWalkRuntime:
    return MainChunkWalkRuntime(
        namespace=namespace,
        chunk_by_chunk=chunk_by_chunk,
        check_length=check_length,
        check_chunk_name=check_chunk_name,
        get_info=get_info,
        checksum=checksum,
        fix_it_felix=fix_it_felix,
    )


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


def run_main_clear_screen(
    runtime: MainClearScreenRuntime,
    context: MainClearScreenContext,
) -> MainClearScreenState:
    decision = runtime.clear_screen_decision(
        clear=context.clear,
        fir_start=context.fir_start,
        os_name=runtime.os_name,
    )
    if decision.action == "ansi_reset":
        runtime.stderr_write("\033c")
    elif decision.action == "cls":
        runtime.system("cls")
    return MainClearScreenState(fir_start=decision.fir_start)


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


def run_main_chunk_walk(
    runtime: MainChunkWalkRuntime,
    context: MainChunkWalkContext,
) -> MainChunkWalkState:
    offset = context.offset
    if offset is None:
        return MainChunkWalkState(offset=offset)

    while offset < len(context.data_hex):
        runtime.chunk_by_chunk(offset)
        namespace = runtime.namespace

        runtime.check_length(
            namespace["Orig_CD"],
            namespace["Orig_CL"],
            namespace["Orig_CT"],
        )
        runtime.check_chunk_name(
            namespace["Orig_CT"],
            namespace["Orig_CL"],
            namespace["Chunks_History"][-1],
        )
        runtime.get_info(namespace["Orig_CT"], namespace["Raw_Data"])
        runtime.checksum(
            namespace["Raw_Type"],
            namespace["Raw_Data"],
            namespace["Raw_Crc"],
        )

        while True:
            runtime.fix_it_felix(namespace["Orig_CT"])
            if namespace["Show_Must_Go_On"] is True:
                break

        offset = runtime.next_chunk_offset(
            offset,
            namespace["Raw_Length"],
            namespace["Raw_Type"],
            namespace["Raw_Data"],
            namespace["Raw_Crc"],
        )

        break_loop, have_a_kitkat = runtime.kitkat_break_decision(
            namespace["Have_A_KitKat"]
        )
        namespace["Have_A_KitKat"] = have_a_kitkat
        if break_loop is True:
            break

    return MainChunkWalkState(offset=offset)
