from __future__ import annotations

import builtins
from dataclasses import dataclass
from typing import Any, Callable

from . import cli, messages, output, runtime_state


@dataclass(frozen=True)
class MainCliOptionsRuntime:
    print_error: Callable[[str], Any]
    exit_process: Callable[[int], Any]
    make_dirs: Callable[..., Any]
    path_exists: Callable[[str], bool]
    path_is_dir: Callable[[str], bool]
    list_dir: Callable[[str], list[str]]
    remove_tree: Callable[[str], Any]
    abspath: Callable[[str], str]
    join: Callable[..., str]
    stderr: Any
    asker: Callable[[str], str] = builtins.input
    candy: Callable[..., Any] = lambda *args, **kwargs: None
    emit: Callable[[str], Any] = print
    parse_legacy_unknown_options: Callable = cli.parse_legacy_unknown_options
    max_saves_error: Callable = cli.max_saves_error
    ultimate_linefeed_budget_error: Callable = cli.ultimate_linefeed_budget_error
    output_file_dir: Callable = cli.output_file_dir
    runtime_flags_from_args: Callable = cli.runtime_flags_from_args
    clone_folder: Callable[[str, str], str] = output.clone_folder


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
    ultimate_linefeed_budget: int | None = None
    ultimate_linefeed_unbounded: bool = False


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
    cleared: bool = False


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


@dataclass(frozen=True)
class MainLoopIterationState:
    should_return: bool = False


def build_cli_options_runtime(
    *,
    print_error: Callable[[str], Any],
    exit_process: Callable[[int], Any],
    make_dirs: Callable[..., Any],
    path_exists: Callable[[str], bool],
    path_is_dir: Callable[[str], bool],
    list_dir: Callable[[str], list[str]],
    remove_tree: Callable[[str], Any],
    abspath: Callable[[str], str],
    join: Callable[..., str],
    stderr: Any,
    asker: Callable[[str], str] = builtins.input,
    candy: Callable[..., Any] = lambda *args, **kwargs: None,
    emit: Callable[[str], Any] = print,
) -> MainCliOptionsRuntime:
    return MainCliOptionsRuntime(
        print_error=print_error,
        exit_process=exit_process,
        make_dirs=make_dirs,
        path_exists=path_exists,
        path_is_dir=path_is_dir,
        list_dir=list_dir,
        remove_tree=remove_tree,
        abspath=abspath,
        join=join,
        stderr=stderr,
        asker=asker,
        candy=candy,
        emit=emit,
    )


def build_cli_options_runtime_from_namespace(namespace: dict[str, Any]) -> MainCliOptionsRuntime:
    return build_cli_options_runtime(
        print_error=builtins.print,
        exit_process=namespace["sys"].exit,
        make_dirs=namespace["os"].makedirs,
        path_exists=namespace["os"].path.exists,
        path_is_dir=namespace["os"].path.isdir,
        list_dir=namespace["os"].listdir,
        remove_tree=namespace["shutil"].rmtree,
        abspath=namespace["os"].path.abspath,
        join=namespace["os"].path.join,
        stderr=namespace["sys"].stderr,
        asker=builtins.input,
        candy=namespace["Candy"],
        emit=namespace["PRINT"],
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


def build_loop_reset_runtime_from_namespace(namespace: dict[str, Any]) -> MainLoopResetRuntime:
    return build_loop_reset_runtime(
        namespace=namespace,
        reset_chunk_info_idat=namespace["CHUNK_INFO_STATE"].reset_idat,
        sync_chunk_info_legacy_state=namespace["Sync_Chunk_Info_Legacy_State"],
        banner=namespace["Chunklate"],
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


def build_clear_screen_runtime_from_namespace(namespace: dict[str, Any]) -> MainClearScreenRuntime:
    return build_clear_screen_runtime(
        stderr_write=lambda value: builtins.print(value, end="", flush=True),
        system=namespace["os"].system,
        os_name=namespace["os"].name,
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


def build_sample_runtime_from_namespace(namespace: dict[str, Any]) -> MainSampleRuntime:
    return build_sample_runtime(
        basename=namespace["os"].path.basename,
        load_sample_data=lambda sample: runtime_state.load_sample_data(sample, opener=builtins.open),
        raw_print=builtins.print,
        candy=namespace["Candy"],
        emit=namespace["PRINT"],
        betterror=namespace["Betterror"],
        exit_process=namespace["sys"].exit,
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


def build_chunk_walk_runtime_from_namespace(namespace: dict[str, Any]) -> MainChunkWalkRuntime:
    return build_chunk_walk_runtime(
        namespace=namespace,
        chunk_by_chunk=namespace["ChunkbyChunk"],
        check_length=namespace["CheckLength"],
        check_chunk_name=namespace["CheckChunkName"],
        get_info=namespace["GetInfo"],
        checksum=namespace["Checksum"],
        fix_it_felix=namespace["FixItFelix"],
    )


def _existing_output_folder_has_content(runtime: MainCliOptionsRuntime, folder: str) -> bool:
    if not runtime.path_exists(folder):
        return False
    if not runtime.path_is_dir(folder):
        return False
    return len(runtime.list_dir(folder)) > 0


def _cleanup_answer(value: Any) -> bool | None:
    normalized = str(value).strip().lower()
    if normalized in ("yes", "y"):
        return True
    if normalized in ("no", "n"):
        return False
    return None


def ask_existing_output_folder_cleanup(runtime: MainCliOptionsRuntime, folder: str) -> bool:
    prompt = "-Delete existing output folder '%s'? (yes/no): " % folder
    while True:
        try:
            answer = runtime.asker(prompt)
        except EOFError:
            return False

        decision = _cleanup_answer(answer)
        if decision is not None:
            return decision

        runtime.emit("-Answer yes/no. I know, paperwork, awful.")


def offer_existing_output_folder_cleanup(
    runtime: MainCliOptionsRuntime,
    *,
    file_origin: str,
    file_dir: str,
) -> None:
    folder = runtime.clone_folder(file_origin, file_dir)
    if not _existing_output_folder_has_content(runtime, folder):
        return

    runtime.candy(
        "Cowsay",
        "Ok, the output folder already exists and there is stuff in it. I can wipe it, but I am asking first because this smells like evidence.",
        "com",
    )
    if ask_existing_output_folder_cleanup(runtime, folder):
        runtime.remove_tree(folder)
        runtime.candy(
            "Cowsay",
            "Ok, I am clearing the mess. Nobody touch the PNG, I am coming back with a shovel and an excuse.",
            "good",
        )
        return

    runtime.candy(
        "Cowsay",
        "Fine, I am not touching it. We keep the old folder, but I am keeping one eyebrow up.",
        "com",
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
    ultimate_linefeed_budget = getattr(args, "ULTIMATE_LINEFEED_BUDGET", None)
    ultimate_linefeed_unbounded = bool(getattr(args, "ULTIMATE_LINEFEED_UNBOUNDED", False))
    ultimate_linefeed_budget_error = runtime.ultimate_linefeed_budget_error(
        ultimate_linefeed_budget,
        ultimate_linefeed_unbounded,
    )
    if ultimate_linefeed_budget_error is not None:
        runtime.print_error(ultimate_linefeed_budget_error)
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
        ultimate_linefeed_budget=ultimate_linefeed_budget,
        ultimate_linefeed_unbounded=ultimate_linefeed_unbounded,
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
        "DEBUGFILE": flags.debug_file,
        "AUTO": flags.auto,
        "MAX_SAVES": options.max_saves,
        "SAVE_COUNT": options.save_count,
        "Sample": options.sample,
        "CLONESWAR": options.cloneswar,
        "CRASH": options.crash,
        "ULTIMATE_LINEFEED_BUDGET": options.ultimate_linefeed_budget,
        "ULTIMATE_LINEFEED_UNBOUNDED": options.ultimate_linefeed_unbounded,
        "OUTPUT_FOLDER_CLEANUP_PENDING": True,
    }


def apply_main_cli_options_from_namespace(
    namespace: dict[str, Any],
    args: Any,
    unknown: list[str] | tuple[str, ...],
    *,
    argv_len: int,
    parser: Any,
) -> MainCliOptionsState | None:
    options = apply_main_cli_options(
        build_cli_options_runtime_from_namespace(namespace),
        args,
        unknown,
        argv_len=argv_len,
        parser=parser,
        current_cloneswar=namespace["CLONESWAR"],
        current_crash=namespace["CRASH"],
    )
    if options is None:
        return None
    namespace.update(legacy_globals_from_main_cli_options(options))
    return options


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


def run_pending_output_folder_cleanup_from_namespace(namespace: dict[str, Any]) -> None:
    if namespace.get("OUTPUT_FOLDER_CLEANUP_PENDING") is not True:
        return
    namespace["OUTPUT_FOLDER_CLEANUP_PENDING"] = False
    offer_existing_output_folder_cleanup(
        build_cli_options_runtime_from_namespace(namespace),
        file_origin=namespace["FILE_Origin"],
        file_dir=namespace["FILE_DIR"],
    )


def run_main_clear_screen(
    runtime: MainClearScreenRuntime,
    context: MainClearScreenContext,
) -> MainClearScreenState:
    cleared = False
    decision = runtime.clear_screen_decision(
        clear=context.clear,
        fir_start=context.fir_start,
        os_name=runtime.os_name,
    )
    if decision.action == "ansi_reset":
        runtime.stderr_write("\033c")
        cleared = True
    elif decision.action == "cls":
        runtime.system("cls")
        cleared = True
    return MainClearScreenState(fir_start=decision.fir_start, cleared=cleared)


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


def sync_loaded_sample_to_namespace(namespace: dict[str, Any], state: MainSampleState) -> None:
    namespace.update(
        {
            "Sample": state.sample,
            "Sample_Name": state.sample_name,
            "CLONESWAR": state.cloneswar,
            "DATA_BYTES": state.data_bytes,
            "DATAX": state.data_hex,
        }
    )


def stop_chunk_walk_after_clone(runtime: MainChunkWalkRuntime) -> bool:
    namespace = runtime.namespace
    break_loop, have_a_kitkat = runtime.kitkat_break_decision(
        namespace["Have_A_KitKat"]
    )
    namespace["Have_A_KitKat"] = have_a_kitkat
    return break_loop is True


def _is_iend_chunk(value: Any) -> bool:
    if isinstance(value, bytes):
        return value == b"IEND"
    return str(value) == "IEND"


def _has_deferred_ihdr_value_finding(pandora_box: Any) -> bool:
    for finding in pandora_box:
        text = str(finding)
        if "GetInfo" not in text or "IHDR" not in text:
            continue
        if "Wrong bit depht" in text or "Wrong bit depth" in text:
            return True
        if "IHDR Color" in text or "IHDR Depht" in text:
            return True
    return False


def _has_immediate_repair_flags(namespace: dict[str, Any]) -> bool:
    immediate_flags = (
        "Bad_Crc",
        "Bad_Libpng",
        "Bad_Current_Name",
        "Bad_Next_Name",
        "Bad_Ancillary",
        "Bad_Next_Ancillary",
        "Bad_No_Next_Chunk",
        "Bad_Critical",
        "Bad_Missplaced",
    )
    return any(bool(namespace.get(flag, False)) for flag in immediate_flags)


def should_defer_fix_it_felix_until_file_tour(namespace: dict[str, Any]) -> bool:
    if _is_iend_chunk(namespace.get("Orig_CT")):
        return False
    if not _has_deferred_ihdr_value_finding(namespace.get("PandoraBox", ())):
        return False
    return not _has_immediate_repair_flags(namespace)


def maybe_explain_deferred_fix_it_felix(namespace: dict[str, Any]) -> None:
    if namespace.get("DEFERRED_FIXIT_NOTICE_SHOWN") is True:
        return
    candy = namespace.get("Candy")
    if callable(candy):
        candy(
            "Cowsay",
            "I found an IHDR value problem, but the chunk road is still walkable. I am finishing the file tour before Felix touches it.",
            "com",
        )
    namespace["DEFERRED_FIXIT_NOTICE_SHOWN"] = True


def has_unresolved_findings(namespace: dict[str, Any]) -> bool:
    return bool(namespace.get("PandoraBox", {}))


def explain_unimplemented_repair_route(namespace: dict[str, Any]) -> None:
    namespace["Candy"](
        "Cowsay",
        messages.UNIMPLEMENTED_REPAIR_ROUTE_MESSAGE,
        "bad",
    )
    namespace["PRINT"]("-No repair route implemented for remaining findings.")


def run_main_loop_once_from_namespace(namespace: dict[str, Any]) -> MainLoopIterationState:
    clear_screen_state = run_main_clear_screen(
        build_clear_screen_runtime_from_namespace(namespace),
        MainClearScreenContext(
            clear=namespace["CLEAR"],
            fir_start=namespace["FirStart"],
        ),
    )
    namespace["FirStart"] = clear_screen_state.fir_start
    namespace["CLEAR_SCREEN_ACTIVE_THIS_PASS"] = clear_screen_state.cleared

    reset_main_loop_state(build_loop_reset_runtime_from_namespace(namespace))
    namespace.get("Prepare_Immediate_Summary", lambda: None)()
    run_pending_output_folder_cleanup_from_namespace(namespace)

    loaded_sample = load_main_sample(
        build_sample_runtime_from_namespace(namespace),
        MainSampleContext(
            sample=namespace["Sample"],
            cloneswar=namespace["CLONESWAR"],
        ),
    )
    if loaded_sample is None:
        return MainLoopIterationState(should_return=True)

    sync_loaded_sample_to_namespace(namespace, loaded_sample)
    save_count_before = namespace["SAVE_COUNT"]
    offset = namespace["FindMagic"]()
    run_main_chunk_walk(
        build_chunk_walk_runtime_from_namespace(namespace),
        MainChunkWalkContext(
            offset=offset,
            data_hex=namespace["DATAX"],
        ),
    )
    if namespace["SAVE_COUNT"] == save_count_before:
        if has_unresolved_findings(namespace):
            explain_unimplemented_repair_route(namespace)
        else:
            namespace.get("Open_Current_Final_Image_If_Valid", lambda: None)()
            namespace["Candy"](
                "Cowsay",
                "Alright. I did not save anything this round. If I chew the same file again, that is not bravery, that is a loop.",
                "good",
            )
        namespace["PRINT"]("-No new clone produced, stopping main loop.")
        return MainLoopIterationState(should_return=True)

    return MainLoopIterationState()


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
        if stop_chunk_walk_after_clone(runtime):
            break

        runtime.check_chunk_name(
            namespace["Orig_CT"],
            namespace["Orig_CL"],
            namespace["Chunks_History"][-1],
        )
        if stop_chunk_walk_after_clone(runtime):
            break

        runtime.get_info(namespace["Orig_CT"], namespace["Raw_Data"])
        if stop_chunk_walk_after_clone(runtime):
            break

        runtime.checksum(
            namespace["Raw_Type"],
            namespace["Raw_Data"],
            namespace["Raw_Crc"],
        )
        if stop_chunk_walk_after_clone(runtime):
            break

        if should_defer_fix_it_felix_until_file_tour(namespace):
            maybe_explain_deferred_fix_it_felix(namespace)
            offset = runtime.next_chunk_offset(
                offset,
                namespace["Raw_Length"],
                namespace["Raw_Type"],
                namespace["Raw_Data"],
                namespace["Raw_Crc"],
            )
            if stop_chunk_walk_after_clone(runtime):
                break
            continue

        while True:
            runtime.fix_it_felix(namespace["Orig_CT"])
            if namespace["Show_Must_Go_On"] is True or namespace["Have_A_KitKat"] is True:
                break

        offset = runtime.next_chunk_offset(
            offset,
            namespace["Raw_Length"],
            namespace["Raw_Type"],
            namespace["Raw_Data"],
            namespace["Raw_Crc"],
        )

        if stop_chunk_walk_after_clone(runtime):
            break

    return MainChunkWalkState(offset=offset)
