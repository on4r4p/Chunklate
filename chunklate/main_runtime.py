from __future__ import annotations

import builtins
from dataclasses import dataclass
import json
from types import SimpleNamespace
from typing import Any, Callable

from . import cli, gpu_runtime, messages, output, runtime_state, smash_checkpoint
from .png import repair_idat_marker_chain_from_visible_headers, repair_linefeed_conversion


CLONE_STUDY_PHRASES = (
    "Fresh clone on the bench. I am checking its alibi.",
    "New clone, new pass. I am reading it byte by byte.",
    "This clone gets a full inspection before I trust it.",
    "Round two: same mystery, sharper notes.",
    "I picked up the new clone. Let me see what changed.",
)
ULTIMATE_LINEFEED_CHECKPOINT_NAME = "_ULF.checkpoint.jsonl"
ULTIMATE_LINEFEED_PROGRESS_NAME = "_ULF.progress.json"
ULTIMATE_LINEFEED_SOURCE_NAME = "_ULF.Source.png"
ULTIMATE_LINEFEED_SOURCE_RAW_NAME = "_ULF.Source.raw"
LEGACY_ULTIMATE_LINEFEED_CHECKPOINT_NAMES = (
    "_UltimateMegaSuperLineFeedBruteForce.checkpoint.jsonl",
)
LEGACY_ULTIMATE_LINEFEED_PROGRESS_NAMES = (
    "_UltimateMegaSuperLineFeedBruteForce.progress.json",
)
LEGACY_ULTIMATE_LINEFEED_SOURCE_NAMES = (
    "_UltimateMegaSuperLineFeedBruteForce.Source.png",
)
ULTIMATE_LINEFEED_RESUME_MODES = ("ask", "auto", "never", "reset")
SMASH_BRUTE_BRAWL_PROGRESS_NAME = smash_checkpoint.SMASH_PROGRESS_NAME
SMASH_BRUTE_BRAWL_SOURCE_RAW_NAME = smash_checkpoint.SMASH_SOURCE_RAW_NAME
SMASH_BRUTE_BRAWL_SOURCE_NAME = smash_checkpoint.SMASH_SOURCE_NAME
SMASH_BRUTE_BRAWL_RESUME_MODES = smash_checkpoint.SMASH_RESUME_MODES
SMASH_BRUTE_BRAWL_TERMINAL_PROGRESS_STATUSES = {
    "accepted_blackfill",
    "exhausted",
    "rejected_hit",
    "success",
    "targeted_retry_requested",
}
IDAT_DEEP_BEAM_DEBUG_FOLDER_NAME = "Debug_Payloads"
IDAT_DEEP_BEAM_CHECKPOINT_SUFFIX = "_deep_beam.checkpoint.jsonl"
IDAT_DEEP_BEAM_PROGRESS_SUFFIX = "_deep_beam.progress.json"


@dataclass(frozen=True)
class MainCliOptionsRuntime:
    print_error: Callable[[str], Any]
    exit_process: Callable[[int], Any]
    make_dirs: Callable[..., Any]
    path_exists: Callable[[str], bool]
    path_is_dir: Callable[[str], bool]
    list_dir: Callable[[str], list[str]]
    remove_tree: Callable[[str], Any]
    remove_file: Callable[[str], Any]
    abspath: Callable[[str], str]
    join: Callable[..., str]
    stderr: Any
    asker: Callable[[str], str] = builtins.input
    candy: Callable[..., Any] = lambda *args, **kwargs: None
    emit: Callable[[str], Any] = print
    clear_dialogue_pause: Callable[[], Any] = lambda: None
    parse_legacy_unknown_options: Callable = cli.parse_legacy_unknown_options
    max_saves_error: Callable = cli.max_saves_error
    ultimate_linefeed_budget_error: Callable = cli.ultimate_linefeed_budget_error
    ultimate_linefeed_preview_timeout_error: Callable = cli.ultimate_linefeed_preview_timeout_error
    ultimate_linefeed_reference_mode_error: Callable = cli.ultimate_linefeed_reference_mode_error
    ultimate_linefeed_visual_gallery_limit_error: Callable = cli.ultimate_linefeed_visual_gallery_limit_error
    ultimate_linefeed_visual_min_coverage_error: Callable = cli.ultimate_linefeed_visual_min_coverage_error
    ultimate_linefeed_workers_error: Callable = cli.ultimate_linefeed_workers_error
    smash_brute_brawl_resume_error: Callable = cli.smash_brute_brawl_resume_error
    smash_brute_brawl_workers_error: Callable = cli.smash_brute_brawl_workers_error
    idat_huffman_kraft_workers_error: Callable = cli.idat_huffman_kraft_workers_error
    smash_brute_brawl_level_error: Callable = cli.smash_brute_brawl_level_error
    smash_brute_brawl_crc_forge_bytes_error: Callable = cli.smash_brute_brawl_crc_forge_bytes_error
    smash_brute_brawl_crc_forge_window_error: Callable = cli.smash_brute_brawl_crc_forge_window_error
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
    ultimate_linefeed_reference: str | None = None
    ultimate_linefeed_reference_mode: str = "exact"
    ultimate_linefeed_reference_regions: str | None = None
    ultimate_linefeed_reference_region_editor: bool = False
    ultimate_linefeed_preview_timeout: float = 5.0
    ultimate_linefeed_show_previews: bool = False
    ultimate_linefeed_visual_gallery_limit: int = 100
    ultimate_linefeed_visual_min_coverage: float = 0.95
    ultimate_linefeed_resume: str = "ask"
    ultimate_linefeed_workers: str | int | None = None
    smash_brute_brawl_resume: str = "ask"
    smash_brute_brawl_workers: str | int | None = None
    smash_brute_brawl_force_level: int | None = None
    smash_brute_brawl_crc_forge: str = "auto"
    smash_brute_brawl_crc_forge_bytes: int | None = None
    smash_brute_brawl_crc_forge_window: str | None = None
    idat_huffman_kraft_workers: str | int | None = None
    gpu_config: gpu_runtime.GpuRuntimeConfig = gpu_runtime.GpuRuntimeConfig()


@dataclass(frozen=True)
class MainLoopResetRuntime:
    namespace: dict[str, Any]
    reset_chunk_info_idat: Callable[[], Any]
    sync_chunk_info_legacy_state: Callable[[str], Any]
    banner: Callable[[int], Any]
    reset_chunk_info_splt: Callable[[], Any] | None = None
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
    remove_file: Callable[[str], Any],
    abspath: Callable[[str], str],
    join: Callable[..., str],
    stderr: Any,
    asker: Callable[[str], str] = builtins.input,
    candy: Callable[..., Any] = lambda *args, **kwargs: None,
    emit: Callable[[str], Any] = print,
    clear_dialogue_pause: Callable[[], Any] = lambda: None,
) -> MainCliOptionsRuntime:
    return MainCliOptionsRuntime(
        print_error=print_error,
        exit_process=exit_process,
        make_dirs=make_dirs,
        path_exists=path_exists,
        path_is_dir=path_is_dir,
        list_dir=list_dir,
        remove_tree=remove_tree,
        remove_file=remove_file,
        abspath=abspath,
        join=join,
        stderr=stderr,
        asker=asker,
        candy=candy,
        emit=emit,
        clear_dialogue_pause=clear_dialogue_pause,
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
        remove_file=getattr(namespace["os"], "remove", lambda path: None),
        abspath=namespace["os"].path.abspath,
        join=namespace["os"].path.join,
        stderr=namespace["sys"].stderr,
        asker=builtins.input,
        candy=namespace["Candy"],
        emit=namespace["PRINT"],
        clear_dialogue_pause=namespace.get("Clear_Terminal_Dialogue_Pause", lambda: None),
    )


def build_loop_reset_runtime(
    *,
    namespace: dict[str, Any],
    reset_chunk_info_idat: Callable[[], Any],
    sync_chunk_info_legacy_state: Callable[[str], Any],
    banner: Callable[[int], Any],
    reset_chunk_info_splt: Callable[[], Any] | None = None,
) -> MainLoopResetRuntime:
    return MainLoopResetRuntime(
        namespace=namespace,
        reset_chunk_info_idat=reset_chunk_info_idat,
        sync_chunk_info_legacy_state=sync_chunk_info_legacy_state,
        banner=banner,
        reset_chunk_info_splt=reset_chunk_info_splt,
    )


def build_loop_reset_runtime_from_namespace(namespace: dict[str, Any]) -> MainLoopResetRuntime:
    return build_loop_reset_runtime(
        namespace=namespace,
        reset_chunk_info_idat=namespace["CHUNK_INFO_STATE"].reset_idat,
        sync_chunk_info_legacy_state=namespace["Sync_Chunk_Info_Legacy_State"],
        banner=namespace["Chunklate"],
        reset_chunk_info_splt=getattr(namespace["CHUNK_INFO_STATE"], "reset_splt", None),
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


def _existing_output_folder_entries(runtime: MainCliOptionsRuntime, folder: str) -> list[str]:
    if not runtime.path_exists(folder):
        return []
    if not runtime.path_is_dir(folder):
        return []
    return list(runtime.list_dir(folder))


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
    warning: str = "",
) -> None:
    folder = runtime.clone_folder(file_origin, file_dir)
    entries = _existing_output_folder_entries(runtime, folder)
    if not entries:
        return
    runtime.emit("-Existing output folder has %s file(s)." % len(entries))

    runtime.candy(
        "Cowsay",
        "Ok, the output folder already exists and there is stuff in it. I can wipe it, but I am asking first because this smells like evidence.",
        "com",
    )
    if warning:
        runtime.candy("Cowsay", warning, "bad")
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
        "Fine, I am not touching it. We keep the old folder and any resume state inside it.",
        "com",
    )


def ultimate_linefeed_folder_paths(
    runtime: MainCliOptionsRuntime,
    *,
    file_origin: str,
    file_dir: str,
) -> tuple[str, str, str, str]:
    folder = runtime.clone_folder(file_origin, file_dir)
    checkpoint_path = _preferred_ultimate_resume_path(
        runtime,
        folder,
        ULTIMATE_LINEFEED_CHECKPOINT_NAME,
        LEGACY_ULTIMATE_LINEFEED_CHECKPOINT_NAMES,
    )
    progress_path = _preferred_ultimate_resume_path(
        runtime,
        folder,
        ULTIMATE_LINEFEED_PROGRESS_NAME,
        LEGACY_ULTIMATE_LINEFEED_PROGRESS_NAMES,
    )
    source_path = _preferred_ultimate_resume_path(
        runtime,
        folder,
        ULTIMATE_LINEFEED_SOURCE_NAME,
        LEGACY_ULTIMATE_LINEFEED_SOURCE_NAMES,
    )
    return (
        folder,
        checkpoint_path,
        progress_path,
        source_path,
    )


def _preferred_ultimate_resume_path(
    runtime: MainCliOptionsRuntime,
    folder: str,
    preferred_name: str,
    legacy_names: tuple[str, ...],
) -> str:
    preferred_path = runtime.join(folder, preferred_name)
    if runtime.path_exists(preferred_path):
        return preferred_path
    for name in legacy_names:
        legacy_path = runtime.join(folder, name)
        if runtime.path_exists(legacy_path):
            return legacy_path
    return preferred_path


def _remove_existing_file(runtime: MainCliOptionsRuntime, path: str) -> None:
    if not runtime.path_exists(path):
        return
    try:
        runtime.remove_file(path)
    except OSError:
        return


def reset_ultimate_linefeed_resume_files(
    runtime: MainCliOptionsRuntime,
    *,
    file_origin: str,
    file_dir: str,
) -> None:
    for path in _ultimate_linefeed_resume_paths(
        runtime,
        file_origin=file_origin,
        file_dir=file_dir,
    ):
        _remove_existing_file(runtime, path)


def _ultimate_linefeed_resume_names() -> tuple[str, ...]:
    return (
        ULTIMATE_LINEFEED_PROGRESS_NAME,
        ULTIMATE_LINEFEED_CHECKPOINT_NAME,
        ULTIMATE_LINEFEED_SOURCE_RAW_NAME,
        ULTIMATE_LINEFEED_SOURCE_NAME,
        *LEGACY_ULTIMATE_LINEFEED_PROGRESS_NAMES,
        *LEGACY_ULTIMATE_LINEFEED_CHECKPOINT_NAMES,
        *LEGACY_ULTIMATE_LINEFEED_SOURCE_NAMES,
    )


def _ultimate_linefeed_resume_paths(
    runtime: MainCliOptionsRuntime,
    *,
    file_origin: str,
    file_dir: str,
) -> tuple[str, ...]:
    folder = runtime.clone_folder(file_origin, file_dir)
    return tuple(runtime.join(folder, name) for name in _ultimate_linefeed_resume_names())


def _ultimate_linefeed_resume_evidence_exists(
    runtime: MainCliOptionsRuntime,
    folder: str,
    checkpoint_path: str,
    progress_path: str,
    source_path: str,
) -> bool:
    if runtime.path_exists(folder) and runtime.path_is_dir(folder):
        try:
            names = set(runtime.list_dir(folder))
            return any(name in names for name in _ultimate_linefeed_resume_names())
        except OSError:
            return False
    return (
        runtime.path_exists(progress_path)
        or runtime.path_exists(checkpoint_path)
        or runtime.path_exists(source_path)
    )


def _resume_answer(value: Any) -> str | None:
    normalized = str(value).strip().lower()
    if normalized in ("1", "resume", "r", "yes", "y"):
        return "resume"
    if normalized in ("2", "ignore", "i", "no", "n"):
        return "ignore"
    if normalized in ("3", "reset"):
        return "reset"
    if normalized in ("4", "abort", "quit", "q"):
        return "abort"
    return None


def ask_ultimate_linefeed_resume(runtime: MainCliOptionsRuntime, progress_path: str) -> str:
    runtime.candy(
        "Cowsay",
        "I found an UltimateMegaSuperLineFeedBruteForce checkpoint in this folder. I can resume from it instead of wiping the output.",
        "good",
    )
    runtime.candy(
        "Cowsay",
        "If a clean Ultimate source snapshot exists, I can jump straight back; otherwise I will finish the file tour first.",
        "com",
    )
    runtime.candy(
        "Cowsay",
        "1. resume\n2. ignore once\n3. reset checkpoints\n4. abort",
        "com",
    )
    prompt = "-Ultimate line-feed resume choice [1 resume]: "
    while True:
        try:
            answer = runtime.asker(prompt)
        except EOFError:
            runtime.clear_dialogue_pause()
            return "resume"
        if str(answer).strip() == "":
            runtime.clear_dialogue_pause()
            return "resume"
        decision = _resume_answer(answer)
        if decision is not None:
            runtime.clear_dialogue_pause()
            return decision
        runtime.emit("-Enter 1, 2, 3, or 4.")


def predecide_ultimate_linefeed_resume_from_namespace(namespace: dict[str, Any]) -> None:
    if "os" not in namespace or "shutil" not in namespace:
        return
    mode = str(namespace.get("ULTIMATE_LINEFEED_RESUME", "ask") or "ask").strip().lower()
    if mode not in ULTIMATE_LINEFEED_RESUME_MODES:
        mode = "ask"
    runtime = build_cli_options_runtime_from_namespace(namespace)
    folder, checkpoint_path, progress_path, source_path = ultimate_linefeed_folder_paths(
        runtime,
        file_origin=namespace["FILE_Origin"],
        file_dir=namespace["FILE_DIR"],
    )
    namespace["ULTIMATE_LINEFEED_CHECKPOINT_PATH"] = checkpoint_path
    namespace["ULTIMATE_LINEFEED_PROGRESS_PATH"] = progress_path
    namespace["ULTIMATE_LINEFEED_SOURCE_PATH"] = source_path

    if mode == "reset":
        reset_ultimate_linefeed_resume_files(
            runtime,
            file_origin=namespace["FILE_Origin"],
            file_dir=namespace["FILE_DIR"],
        )
        namespace["ULTIMATE_LINEFEED_RESUME_DECISION"] = "reset"
        return
    if mode == "never":
        namespace["ULTIMATE_LINEFEED_RESUME_DECISION"] = "never"
        return
    if not _ultimate_linefeed_resume_evidence_exists(
        runtime,
        folder,
        checkpoint_path,
        progress_path,
        source_path,
    ):
        namespace["ULTIMATE_LINEFEED_RESUME_DECISION"] = "missing"
        return

    if mode == "auto":
        namespace["ULTIMATE_LINEFEED_RESUME_DECISION"] = "resume"
        namespace["OUTPUT_FOLDER_CLEANUP_PENDING"] = False
        runtime.candy(
            "Cowsay",
            "Ultimate checkpoint found. Auto-resume is enabled, so I am keeping the output folder intact.",
            "good",
        )
        return

    decision = ask_ultimate_linefeed_resume(runtime, progress_path)
    namespace["ULTIMATE_LINEFEED_RESUME_DECISION"] = decision
    if decision == "resume":
        namespace["OUTPUT_FOLDER_CLEANUP_PENDING"] = False
        return
    if decision == "reset":
        reset_ultimate_linefeed_resume_files(
            runtime,
            file_origin=namespace["FILE_Origin"],
            file_dir=namespace["FILE_DIR"],
        )
        return
    if decision == "abort":
        runtime.exit_process(130)


def smash_brute_brawl_folder_paths(
    runtime: MainCliOptionsRuntime,
    *,
    file_origin: str,
    file_dir: str,
) -> tuple[str, str, str, str]:
    folder = runtime.clone_folder(file_origin, file_dir)
    return (
        folder,
        runtime.join(folder, SMASH_BRUTE_BRAWL_PROGRESS_NAME),
        runtime.join(folder, SMASH_BRUTE_BRAWL_SOURCE_RAW_NAME),
        runtime.join(folder, SMASH_BRUTE_BRAWL_SOURCE_NAME),
    )


def _smash_brute_brawl_resume_names() -> tuple[str, ...]:
    return (
        SMASH_BRUTE_BRAWL_PROGRESS_NAME,
        SMASH_BRUTE_BRAWL_SOURCE_RAW_NAME,
        SMASH_BRUTE_BRAWL_SOURCE_NAME,
    )


def _smash_brute_brawl_resume_paths(
    runtime: MainCliOptionsRuntime,
    *,
    file_origin: str,
    file_dir: str,
) -> tuple[str, ...]:
    folder = runtime.clone_folder(file_origin, file_dir)
    return tuple(runtime.join(folder, name) for name in _smash_brute_brawl_resume_names())


def reset_smash_brute_brawl_resume_files(
    runtime: MainCliOptionsRuntime,
    *,
    file_origin: str,
    file_dir: str,
) -> None:
    for path in _smash_brute_brawl_resume_paths(
        runtime,
        file_origin=file_origin,
        file_dir=file_dir,
    ):
        _remove_existing_file(runtime, path)


def _smash_brute_brawl_resume_evidence_exists(
    runtime: MainCliOptionsRuntime,
    folder: str,
    progress_path: str,
    source_raw_path: str,
    source_path: str,
) -> bool:
    if _smash_brute_brawl_progress_is_terminal(progress_path):
        return False
    if runtime.path_exists(folder) and runtime.path_is_dir(folder):
        try:
            names = set(runtime.list_dir(folder))
            return any(name in names for name in _smash_brute_brawl_resume_names())
        except OSError:
            return False
    return (
        runtime.path_exists(progress_path)
        or runtime.path_exists(source_raw_path)
        or runtime.path_exists(source_path)
    )


def _smash_brute_brawl_progress_is_terminal(progress_path: str) -> bool:
    try:
        with open(progress_path, "r", encoding="utf-8") as handle:
            progress = json.load(handle)
    except (OSError, TypeError, ValueError):
        return False
    if not isinstance(progress, dict):
        return False
    status = str(progress.get("status") or "").strip().lower()
    plan = progress.get("plan")
    if not status and isinstance(plan, dict):
        status = str(plan.get("status") or "").strip().lower()
    return status in SMASH_BRUTE_BRAWL_TERMINAL_PROGRESS_STATUSES


def ask_smash_brute_brawl_resume(runtime: MainCliOptionsRuntime, progress_path: str) -> str:
    runtime.candy(
        "Cowsay",
        "I found a DaedalusForce checkpoint in this folder. I can resume from it instead of wiping the output.",
        "good",
    )
    runtime.candy(
        "Cowsay",
        "If a clean DaedalusForce source snapshot exists, I can jump straight back; otherwise I will finish the file tour first.",
        "com",
    )
    runtime.candy(
        "Cowsay",
        "1. resume\n2. ignore once\n3. reset checkpoints\n4. abort",
        "com",
    )
    prompt = "-DaedalusForce resume choice [1 resume]: "
    while True:
        try:
            answer = runtime.asker(prompt)
        except EOFError:
            runtime.clear_dialogue_pause()
            return "resume"
        if str(answer).strip() == "":
            runtime.clear_dialogue_pause()
            return "resume"
        decision = _resume_answer(answer)
        if decision is not None:
            runtime.clear_dialogue_pause()
            return decision
        runtime.emit("-Enter 1, 2, 3, or 4.")


def predecide_smash_brute_brawl_resume_from_namespace(namespace: dict[str, Any]) -> None:
    if "os" not in namespace or "shutil" not in namespace:
        return
    mode = str(namespace.get("SMASH_BRUTE_BRAWL_RESUME", "ask") or "ask").strip().lower()
    if mode not in SMASH_BRUTE_BRAWL_RESUME_MODES:
        mode = "ask"
    runtime = build_cli_options_runtime_from_namespace(namespace)
    folder, progress_path, source_raw_path, source_path = smash_brute_brawl_folder_paths(
        runtime,
        file_origin=namespace["FILE_Origin"],
        file_dir=namespace["FILE_DIR"],
    )
    namespace["SMASH_BRUTE_BRAWL_FOLDER"] = folder
    namespace["SMASH_BRUTE_BRAWL_PROGRESS_PATH"] = progress_path
    namespace["SMASH_BRUTE_BRAWL_SOURCE_RAW_PATH"] = source_raw_path
    namespace["SMASH_BRUTE_BRAWL_SOURCE_PATH"] = source_path

    if mode == "reset":
        reset_smash_brute_brawl_resume_files(
            runtime,
            file_origin=namespace["FILE_Origin"],
            file_dir=namespace["FILE_DIR"],
        )
        namespace["SMASH_BRUTE_BRAWL_RESUME_DECISION"] = "reset"
        return
    if mode == "never":
        namespace["SMASH_BRUTE_BRAWL_RESUME_DECISION"] = "never"
        return
    if not _smash_brute_brawl_resume_evidence_exists(
        runtime,
        folder,
        progress_path,
        source_raw_path,
        source_path,
    ):
        namespace["SMASH_BRUTE_BRAWL_RESUME_DECISION"] = "missing"
        return

    if mode == "auto":
        namespace["SMASH_BRUTE_BRAWL_RESUME_DECISION"] = "resume"
        namespace["OUTPUT_FOLDER_CLEANUP_PENDING"] = False
        runtime.candy(
            "Cowsay",
            "DaedalusForce checkpoint found. Auto-resume is enabled, so I am keeping the output folder intact.",
            "good",
        )
        return

    decision = ask_smash_brute_brawl_resume(runtime, progress_path)
    namespace["SMASH_BRUTE_BRAWL_RESUME_DECISION"] = decision
    if decision == "resume":
        namespace["OUTPUT_FOLDER_CLEANUP_PENDING"] = False
        return
    if decision == "reset":
        reset_smash_brute_brawl_resume_files(
            runtime,
            file_origin=namespace["FILE_Origin"],
            file_dir=namespace["FILE_DIR"],
        )
        return
    if decision == "abort":
        runtime.exit_process(130)


def idat_deep_beam_folder_paths(
    runtime: MainCliOptionsRuntime,
    *,
    file_origin: str,
    file_dir: str,
) -> tuple[str, str, str, str]:
    folder = runtime.clone_folder(file_origin, file_dir)
    source_stem = output.source_stem(file_origin)
    payload_folder = runtime.join(folder, IDAT_DEEP_BEAM_DEBUG_FOLDER_NAME)
    return (
        folder,
        payload_folder,
        runtime.join(payload_folder, source_stem + IDAT_DEEP_BEAM_CHECKPOINT_SUFFIX),
        runtime.join(payload_folder, source_stem + IDAT_DEEP_BEAM_PROGRESS_SUFFIX),
    )


def _runtime_dir_entries(runtime: MainCliOptionsRuntime, folder: str) -> set[str]:
    if not runtime.path_exists(folder):
        return set()
    if not runtime.path_is_dir(folder):
        return set()
    try:
        return set(runtime.list_dir(folder))
    except OSError:
        return set()


def _idat_deep_beam_resume_evidence_exists(
    runtime: MainCliOptionsRuntime,
    folder: str,
    payload_folder: str,
    checkpoint_path: str,
    progress_path: str,
) -> bool:
    folder_entries = _runtime_dir_entries(runtime, folder)
    checkpoint_name = checkpoint_path.rsplit("/", 1)[-1]
    progress_name = progress_path.rsplit("/", 1)[-1]
    if checkpoint_name in folder_entries or progress_name in folder_entries:
        return True
    if IDAT_DEEP_BEAM_DEBUG_FOLDER_NAME not in folder_entries:
        return False

    payload_entries = _runtime_dir_entries(runtime, payload_folder)
    if checkpoint_name in payload_entries or progress_name in payload_entries:
        return True
    return runtime.path_exists(checkpoint_path) or runtime.path_exists(progress_path)


def predecide_idat_deep_beam_resume_from_namespace(namespace: dict[str, Any]) -> None:
    if "os" not in namespace or "shutil" not in namespace:
        return
    runtime = build_cli_options_runtime_from_namespace(namespace)
    folder, payload_folder, checkpoint_path, progress_path = idat_deep_beam_folder_paths(
        runtime,
        file_origin=namespace["FILE_Origin"],
        file_dir=namespace["FILE_DIR"],
    )
    namespace["IDAT_DEEP_BEAM_FOLDER"] = folder
    namespace["IDAT_DEEP_BEAM_PAYLOAD_FOLDER"] = payload_folder
    namespace["IDAT_DEEP_BEAM_CHECKPOINT_PATH"] = checkpoint_path
    namespace["IDAT_DEEP_BEAM_PROGRESS_PATH"] = progress_path

    if not _idat_deep_beam_resume_evidence_exists(
        runtime,
        folder,
        payload_folder,
        checkpoint_path,
        progress_path,
    ):
        namespace["IDAT_DEEP_BEAM_RESUME_DECISION"] = "missing"
        return

    namespace["IDAT_DEEP_BEAM_RESUME_DECISION"] = "available"
    namespace["OUTPUT_FOLDER_CLEANUP_WARNING"] = (
        "IDAT deep-beam checkpoint/progress were found in this output folder. "
        "If you delete it, that beam cannot resume and the run will restart from fresh diagnostics. "
        "Answer no to keep the checkpoints/progress and allow resume after the IDAT convoy clone is rebuilt."
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
    ultimate_linefeed_reference = getattr(args, "ULTIMATE_LINEFEED_REFERENCE", None)
    ultimate_linefeed_reference_mode = str(
        getattr(args, "ULTIMATE_LINEFEED_REFERENCE_MODE", "exact") or "exact"
    ).strip().lower()
    ultimate_linefeed_reference_regions = getattr(
        args,
        "ULTIMATE_LINEFEED_REFERENCE_REGIONS",
        None,
    )
    ultimate_linefeed_reference_region_editor = bool(
        getattr(args, "ULTIMATE_LINEFEED_REFERENCE_REGION_EDITOR", False)
    )
    ultimate_linefeed_preview_timeout = float(
        getattr(args, "ULTIMATE_LINEFEED_PREVIEW_TIMEOUT", 5.0)
    )
    ultimate_linefeed_show_previews = bool(
        getattr(args, "ULTIMATE_LINEFEED_SHOW_PREVIEWS", False)
    )
    ultimate_linefeed_visual_gallery_limit = int(
        getattr(args, "ULTIMATE_LINEFEED_VISUAL_GALLERY_LIMIT", 100)
    )
    ultimate_linefeed_visual_min_coverage = float(
        getattr(args, "ULTIMATE_LINEFEED_VISUAL_MIN_COVERAGE", 0.95)
    )
    ultimate_linefeed_resume = str(
        getattr(args, "ULTIMATE_LINEFEED_RESUME", "ask") or "ask"
    ).strip().lower()
    resume_error = cli.ultimate_linefeed_resume_error(
        ultimate_linefeed_resume
    )
    if resume_error is not None:
        runtime.print_error(resume_error)
        runtime.exit_process(1)
        return None
    global_workers = getattr(args, "GLOBAL_WORKERS", None)
    ultimate_linefeed_workers = getattr(args, "ULTIMATE_LINEFEED_WORKERS", None)
    if ultimate_linefeed_workers is None and global_workers is not None:
        ultimate_linefeed_workers = global_workers
    workers_error = runtime.ultimate_linefeed_workers_error(
        ultimate_linefeed_workers
    )
    if workers_error is not None:
        runtime.print_error(workers_error)
        runtime.exit_process(1)
        return None
    smash_brute_brawl_resume = str(
        getattr(args, "SMASH_BRUTE_BRAWL_RESUME", "ask") or "ask"
    ).strip().lower()
    smash_resume_error = runtime.smash_brute_brawl_resume_error(
        smash_brute_brawl_resume
    )
    if smash_resume_error is not None:
        runtime.print_error(smash_resume_error)
        runtime.exit_process(1)
        return None
    smash_brute_brawl_workers = getattr(args, "SMASH_BRUTE_BRAWL_WORKERS", None)
    if smash_brute_brawl_workers is None and global_workers is not None:
        smash_brute_brawl_workers = global_workers
    smash_workers_error = runtime.smash_brute_brawl_workers_error(
        smash_brute_brawl_workers
    )
    if smash_workers_error is not None:
        runtime.print_error(smash_workers_error)
        runtime.exit_process(1)
        return None
    idat_huffman_kraft_workers = getattr(args, "IDAT_HUFFMAN_KRAFT_WORKERS", None)
    if idat_huffman_kraft_workers is None and global_workers is not None:
        idat_huffman_kraft_workers = global_workers
    idat_huffman_kraft_workers_error = runtime.idat_huffman_kraft_workers_error(
        idat_huffman_kraft_workers
    )
    if idat_huffman_kraft_workers_error is not None:
        runtime.print_error(idat_huffman_kraft_workers_error)
        runtime.exit_process(1)
        return None
    smash_brute_brawl_force_level_arg = getattr(args, "SMASH_BRUTE_BRAWL_FORCE_LEVEL", None)
    smash_level_error = runtime.smash_brute_brawl_level_error(
        smash_brute_brawl_force_level_arg
    )
    if smash_level_error is not None:
        runtime.print_error(smash_level_error)
        runtime.exit_process(1)
        return None
    smash_brute_brawl_force_level = (
        None
        if smash_brute_brawl_force_level_arg is None
        else int(str(smash_brute_brawl_force_level_arg).strip())
    )
    smash_brute_brawl_crc_forge = str(
        getattr(args, "SMASH_BRUTE_BRAWL_CRC_FORGE", "auto") or "auto"
    ).strip().lower()
    smash_crc_forge_bytes_arg = getattr(args, "SMASH_BRUTE_BRAWL_CRC_FORGE_BYTES", None)
    smash_crc_forge_bytes_error = runtime.smash_brute_brawl_crc_forge_bytes_error(
        smash_crc_forge_bytes_arg
    )
    if smash_crc_forge_bytes_error is not None:
        runtime.print_error(smash_crc_forge_bytes_error)
        runtime.exit_process(1)
        return None
    smash_brute_brawl_crc_forge_bytes = (
        None
        if smash_crc_forge_bytes_arg is None
        else int(str(smash_crc_forge_bytes_arg).strip())
    )
    smash_brute_brawl_crc_forge_window = getattr(
        args,
        "SMASH_BRUTE_BRAWL_CRC_FORGE_WINDOW",
        None,
    )
    smash_crc_forge_window_error = runtime.smash_brute_brawl_crc_forge_window_error(
        smash_brute_brawl_crc_forge_window
    )
    if smash_crc_forge_window_error is not None:
        runtime.print_error(smash_crc_forge_window_error)
        runtime.exit_process(1)
        return None
    ultimate_linefeed_budget_error = runtime.ultimate_linefeed_budget_error(
        ultimate_linefeed_budget,
        ultimate_linefeed_unbounded,
    )
    if ultimate_linefeed_budget_error is not None:
        runtime.print_error(ultimate_linefeed_budget_error)
        runtime.exit_process(1)
        return None
    reference_mode_error = runtime.ultimate_linefeed_reference_mode_error(
        ultimate_linefeed_reference_mode
    )
    if reference_mode_error is not None:
        runtime.print_error(reference_mode_error)
        runtime.exit_process(1)
        return None
    preview_timeout_error = runtime.ultimate_linefeed_preview_timeout_error(
        ultimate_linefeed_preview_timeout
    )
    if preview_timeout_error is not None:
        runtime.print_error(preview_timeout_error)
        runtime.exit_process(1)
        return None
    visual_limit_error = runtime.ultimate_linefeed_visual_gallery_limit_error(
        ultimate_linefeed_visual_gallery_limit
    )
    if visual_limit_error is not None:
        runtime.print_error(visual_limit_error)
        runtime.exit_process(1)
        return None
    visual_min_coverage_error = runtime.ultimate_linefeed_visual_min_coverage_error(
        ultimate_linefeed_visual_min_coverage
    )
    if visual_min_coverage_error is not None:
        runtime.print_error(visual_min_coverage_error)
        runtime.exit_process(1)
        return None
    gpu_config = gpu_runtime.build_gpu_config(args)

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
        ultimate_linefeed_reference=ultimate_linefeed_reference,
        ultimate_linefeed_reference_mode=ultimate_linefeed_reference_mode,
        ultimate_linefeed_reference_regions=ultimate_linefeed_reference_regions,
        ultimate_linefeed_reference_region_editor=ultimate_linefeed_reference_region_editor,
        ultimate_linefeed_preview_timeout=ultimate_linefeed_preview_timeout,
        ultimate_linefeed_show_previews=ultimate_linefeed_show_previews,
        ultimate_linefeed_visual_gallery_limit=ultimate_linefeed_visual_gallery_limit,
        ultimate_linefeed_visual_min_coverage=ultimate_linefeed_visual_min_coverage,
        ultimate_linefeed_resume=ultimate_linefeed_resume,
        ultimate_linefeed_workers=ultimate_linefeed_workers,
        smash_brute_brawl_resume=smash_brute_brawl_resume,
        smash_brute_brawl_workers=smash_brute_brawl_workers,
        smash_brute_brawl_force_level=smash_brute_brawl_force_level,
        smash_brute_brawl_crc_forge=smash_brute_brawl_crc_forge,
        smash_brute_brawl_crc_forge_bytes=smash_brute_brawl_crc_forge_bytes,
        smash_brute_brawl_crc_forge_window=smash_brute_brawl_crc_forge_window,
        idat_huffman_kraft_workers=idat_huffman_kraft_workers,
        gpu_config=gpu_config,
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
        "COLOR_MODE": flags.color_mode,
        "MAX_SAVES": options.max_saves,
        "SAVE_COUNT": options.save_count,
        "Sample": options.sample,
        "CLONESWAR": options.cloneswar,
        "CRASH": options.crash,
        "ULTIMATE_LINEFEED_BUDGET": options.ultimate_linefeed_budget,
        "ULTIMATE_LINEFEED_UNBOUNDED": options.ultimate_linefeed_unbounded,
        "ULTIMATE_LINEFEED_REFERENCE": options.ultimate_linefeed_reference,
        "ULTIMATE_LINEFEED_REFERENCE_MODE": options.ultimate_linefeed_reference_mode,
        "ULTIMATE_LINEFEED_REFERENCE_REGIONS": options.ultimate_linefeed_reference_regions,
        "ULTIMATE_LINEFEED_REFERENCE_REGION_EDITOR": options.ultimate_linefeed_reference_region_editor,
        "ULTIMATE_LINEFEED_PREVIEW_TIMEOUT": options.ultimate_linefeed_preview_timeout,
        "ULTIMATE_LINEFEED_SHOW_PREVIEWS": options.ultimate_linefeed_show_previews,
        "ULTIMATE_LINEFEED_VISUAL_GALLERY_LIMIT": options.ultimate_linefeed_visual_gallery_limit,
        "ULTIMATE_LINEFEED_VISUAL_MIN_COVERAGE": options.ultimate_linefeed_visual_min_coverage,
        "ULTIMATE_LINEFEED_RESUME": options.ultimate_linefeed_resume,
        "ULTIMATE_LINEFEED_WORKERS": options.ultimate_linefeed_workers,
        "SMASH_BRUTE_BRAWL_RESUME": options.smash_brute_brawl_resume,
        "SMASH_BRUTE_BRAWL_WORKERS": options.smash_brute_brawl_workers,
        "SMASH_BRUTE_BRAWL_FORCE_LEVEL": options.smash_brute_brawl_force_level,
        "SMASH_BRUTE_BRAWL_CRC_FORGE": options.smash_brute_brawl_crc_forge,
        "SMASH_BRUTE_BRAWL_CRC_FORGE_BYTES": options.smash_brute_brawl_crc_forge_bytes,
        "SMASH_BRUTE_BRAWL_CRC_FORGE_WINDOW": options.smash_brute_brawl_crc_forge_window,
        "IDAT_DEEP_BEAM_WORKERS": options.idat_huffman_kraft_workers,
        "IDAT_HUFFMAN_KRAFT_WORKERS": options.idat_huffman_kraft_workers,
        "GPU": options.gpu_config.enabled,
        "GPU_CONFIG": options.gpu_config,
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
    if options.smash_brute_brawl_force_level is not None:
        namespace["Brute_LvL"] = options.smash_brute_brawl_force_level
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
    if runtime.reset_chunk_info_splt is not None:
        runtime.reset_chunk_info_splt()
        runtime.sync_chunk_info_legacy_state("splt")
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
        warning=str(namespace.get("OUTPUT_FOLDER_CLEANUP_WARNING") or ""),
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
    if context.cloneswar is not False or is_clone_sample_name(sample_selection.sample_name):
        runtime.candy(
            "Cowsay",
            clone_study_phrase(sample_selection.sample_name),
            "com",
        )
    return MainSampleState(
        sample=sample_selection.sample,
        sample_name=sample_selection.sample_name,
        cloneswar=sample_selection.cloneswar,
        data_bytes=loaded_sample.data_bytes,
        data_hex=loaded_sample.data_hex,
    )


def clone_study_phrase(sample_name: Any) -> str:
    index = sum(ord(char) for char in str(sample_name)) % len(CLONE_STUDY_PHRASES)
    return CLONE_STUDY_PHRASES[index]


def is_clone_sample_name(sample_name: Any) -> bool:
    return "_Fixed" in str(sample_name)


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


def _fix_it_felix_repair_boundary_reached(namespace: dict[str, Any]) -> bool:
    if _is_iend_chunk(namespace.get("Orig_CT")):
        return True
    return bool(namespace.get("Bad_No_Next_Chunk", False))


def _deferred_linefeed_repair_boundary_reached(namespace: dict[str, Any]) -> bool:
    if _is_iend_chunk(namespace.get("Orig_CT")) or bool(namespace.get("EOF", False)):
        return True
    return any(
        str(note).strip() == "-Reached the end of file."
        for note in namespace.get("SideNotes", ())
    )


def _deferred_linefeed_visible_marker_tour_reached_iend(namespace: dict[str, Any]) -> bool:
    deferred = namespace.get("DEFERRED_LINEFEED_SIGNATURE_REPAIR")
    if not isinstance(deferred, dict):
        return False
    data_bytes = deferred.get("data_bytes") or namespace.get("DATA_BYTES")
    if not isinstance(data_bytes, bytes):
        return False
    try:
        repair = repair_linefeed_conversion(data_bytes, allow_partial=True)
    except Exception:
        return False
    if repair is None:
        return False
    try:
        marker_repairs = repair_idat_marker_chain_from_visible_headers(repair.data)
    except Exception:
        return False
    if not marker_repairs:
        return False
    if namespace.get("DEFERRED_LINEFEED_VISIBLE_TOUR_SHOWN") is not True:
        candy = namespace.get("Candy")
        if callable(candy):
            candy(
                "Cowsay",
                "The normal chunk walk hit line-feed drift, so I checked the visible marker road before repairing.",
                "com",
            )
            candy(
                "Cowsay",
                "Visible marker tour reached IEND. Now the deferred line-feed repair is allowed.",
                "good",
            )
        namespace.setdefault("SideNotes", []).append(
            "-FindMagic: visible line-feed marker tour reached IEND before deferred repair."
        )
        namespace["DEFERRED_LINEFEED_VISIBLE_TOUR_SHOWN"] = True
    return True


def _joined_findings(namespace: dict[str, Any]) -> str:
    parts: list[str] = []
    pandora = namespace.get("PandoraBox", {})
    if hasattr(pandora, "items"):
        for key, value in pandora.items():
            parts.append(str(key))
            parts.append(str(value))
    else:
        for value in pandora:
            parts.append(str(value))
    for note in namespace.get("SideNotes", ()):
        parts.append(str(note))
    return "\n".join(parts)


def _has_internal_idat_linefeed_drift_evidence(namespace: dict[str, Any]) -> bool:
    findings = _joined_findings(namespace)
    if not findings:
        return False
    lower_findings = findings.lower()
    if "wrong crc b'idat'" not in lower_findings and 'wrong crc b"idat"' not in lower_findings:
        return False
    wrong_next_after_idat = (
        "Wrong Chunk name after Chunk[b'IDAT']" in findings
        or 'Wrong Chunk name after Chunk[b"IDAT"]' in findings
        or "Wrong Chunk Name after Chunk[b'IDAT']" in findings
        or "wrong next chunk after idat" in lower_findings
        or ("wrong chunk name" in lower_findings and "after chunk[b'idat']" in lower_findings)
        or ('wrong chunk name' in lower_findings and 'after chunk[b"idat"]' in lower_findings)
    )
    if not wrong_next_after_idat:
        return False
    terminal_damage = (
        bool(namespace.get("Bad_No_Next_Chunk", False))
        or "no nextchunk" in lower_findings
        or "iend chunk is missing" in lower_findings
        or "iend is missing" in lower_findings
        or bool(namespace.get("EOF", False))
    )
    if not terminal_damage:
        return False
    return any(chunk == b"IDAT" or str(chunk) == "IDAT" for chunk in namespace.get("Chunks_History", ()))


def _internal_idat_linefeed_repair_is_confirmed(namespace: dict[str, Any]) -> bool:
    data_bytes = namespace.get("DATA_BYTES")
    if not isinstance(data_bytes, bytes):
        return False
    try:
        if repair_idat_marker_chain_from_visible_headers(data_bytes):
            return True
    except Exception:
        pass
    try:
        repair = repair_linefeed_conversion(data_bytes, allow_partial=True)
    except Exception:
        return False
    if repair is None:
        return False
    try:
        marker_repairs = repair_idat_marker_chain_from_visible_headers(repair.data)
    except Exception:
        return False
    return bool(marker_repairs)


def maybe_seed_internal_idat_linefeed_repair(namespace: dict[str, Any]) -> bool:
    if namespace.get("DEFERRED_LINEFEED_SIGNATURE_REPAIR"):
        return True
    if namespace.get("DEFERRED_INTERNAL_LINEFEED_CHECKED") is True:
        return False
    if not _has_internal_idat_linefeed_drift_evidence(namespace):
        return False
    namespace["DEFERRED_INTERNAL_LINEFEED_CHECKED"] = True
    if not _internal_idat_linefeed_repair_is_confirmed(namespace):
        return False

    data_bytes = namespace.get("DATA_BYTES", b"")
    namespace["DEFERRED_LINEFEED_SIGNATURE_REPAIR"] = {
        "data_bytes": data_bytes,
        "sample_name": namespace.get("Sample_Name") or namespace.get("Sample", ""),
        "linefeed_pattern": "internal-idat-marker-chain",
        "source": "internal-idat-marker-chain",
    }
    namespace["DEFERRED_REPAIR_STILL_REQUIRED"] = True
    namespace.setdefault("SideNotes", []).append(
        "-FindMagic: internal IDAT marker-chain line-feed repair deferred until the file tour finishes."
    )
    candy = namespace.get("Candy")
    if callable(candy):
        candy(
            "Cowsay",
            "I found line-feed drift inside the IDAT marker chain. I am queuing the deferred line-feed repair.",
            "com",
        )
    return True


def deferred_linefeed_repair_is_ready(namespace: dict[str, Any]) -> bool:
    if _deferred_linefeed_repair_boundary_reached(namespace):
        return True
    return _deferred_linefeed_visible_marker_tour_reached_iend(namespace)


def should_defer_fix_it_felix_until_file_tour(namespace: dict[str, Any]) -> bool:
    maybe_seed_internal_idat_linefeed_repair(namespace)
    if namespace.get("DEFERRED_LINEFEED_SIGNATURE_REPAIR"):
        return True
    if not namespace.get("PandoraBox", {}):
        return False
    return True


def should_run_fix_it_felix_after_file_tour(namespace: dict[str, Any]) -> bool:
    if not has_unresolved_findings(namespace):
        return False
    if namespace.get("DEFERRED_LINEFEED_SIGNATURE_REPAIR") and deferred_linefeed_repair_is_ready(namespace):
        return False
    return True


def maybe_explain_deferred_fix_it_felix(namespace: dict[str, Any]) -> None:
    if namespace.get("DEFERRED_FIXIT_NOTICE_SHOWN") is True:
        return
    candy = namespace.get("Candy")
    if callable(candy):
        candy(
            "Cowsay",
            "I found repairable problems. I am finishing the file tour before Felix touches it.",
            "com",
        )
    namespace["DEFERRED_FIXIT_NOTICE_SHOWN"] = True


def has_unresolved_findings(namespace: dict[str, Any]) -> bool:
    return bool(namespace.get("PandoraBox", {}))


def chunk_walk_reached_end(state: MainChunkWalkState, data_hex: str) -> bool:
    try:
        return state.offset is not None and int(state.offset) >= len(data_hex)
    except (TypeError, ValueError):
        return False


def explain_unimplemented_repair_route(namespace: dict[str, Any]) -> None:
    namespace["Candy"](
        "Cowsay",
        messages.UNIMPLEMENTED_REPAIR_ROUTE_MESSAGE,
        "bad",
    )
    namespace["PRINT"]("-No repair route implemented for remaining findings.")


def _remaining_findings_are_idat_wrong_crc(namespace: dict[str, Any]) -> bool:
    pandora = namespace.get("PandoraBox", {})
    if not pandora:
        return False
    if hasattr(pandora, "keys"):
        findings = tuple(pandora.keys())
    else:
        findings = tuple(pandora)
    if not findings:
        return False
    for finding in findings:
        text = str(finding).lower()
        if "no nextchunk" in text:
            continue
        if "wrong crc" not in text or "idat" not in text:
            return False
    return True


def _try_unresolved_idat_deflate_route(namespace: dict[str, Any]) -> bool:
    namespace.pop("IDAT_DEFLATE_ROUTE_CONSUMED", None)
    if not _remaining_findings_are_idat_wrong_crc(namespace):
        return False
    data_hex = namespace.get("DATAX")
    if not isinstance(data_hex, str) or not data_hex:
        return False
    write_clone = namespace.get("WriteClone")
    if not callable(write_clone):
        return False

    try:
        data = bytes.fromhex(data_hex)
    except (TypeError, ValueError):
        return False

    from . import fixit_felix_runtime, idat

    analysis = idat.analyze_idat_stream(data)
    if analysis.complete or not analysis.supported:
        return False
    if analysis.status not in ("corrupt_deflate", "incomplete_stream", "bad_adler"):
        return False

    candy = namespace.get("Candy")
    emit = namespace.get("PRINT")
    question = namespace.get("Question")
    runtime = SimpleNamespace(
        emit=emit if callable(emit) else (lambda _message: None),
        candy=candy if callable(candy) else (lambda *_args, **_kwargs: None),
        question=question if callable(question) else (lambda *_args, **_kwargs: False),
        write_clone=write_clone,
        side_notes=namespace.setdefault("SideNotes", []),
        data_hex=data_hex,
        remember_idat_deflate_probe=lambda probe_analysis: fixit_felix_runtime.remember_idat_deflate_probe(
            namespace,
            probe_analysis,
        ),
        loadingbar=namespace.get("Loadingbar"),
        minibar=namespace.get("Minibar"),
        preview_repair_image=namespace.get("Preview_Repair_Image"),
        file_origin=namespace.get("FILE_Origin") or namespace.get("Sample") or "",
        file_dir=namespace.get("FILE_DIR") or "",
        interactive=fixit_felix_runtime.namespace_interactive_prompts(namespace),
        input_func=namespace.get("Transcript_Input") or namespace.get("input") or input,
        deep_beam_workers=fixit_felix_runtime._namespace_idat_deep_beam_workers(namespace),
        deep_beam_gpu=namespace.get("IDAT_DEEP_BEAM_GPU"),
        deep_beam_gpu_config=namespace.get("GPU_CONFIG"),
        deep_beam_budget=namespace.get("IDAT_DEEP_BEAM_BUDGET"),
        deep_beam_max_depth=namespace.get("IDAT_DEEP_BEAM_MAX_DEPTH"),
        deep_beam_gpu_shard_size=namespace.get("IDAT_DEEP_BEAM_GPU_SHARD_SIZE"),
        deep_beam_cpu_batch_size=namespace.get("IDAT_DEEP_BEAM_CPU_BATCH_SIZE"),
        deep_beam_prompt_cache=namespace.setdefault("IDAT_DEEP_BEAM_PROMPT_CACHE", {}),
        huffman_oracle_budget=namespace.get("IDAT_HUFFMAN_ORACLE_BUDGET"),
        crc_periodic_budget=namespace.get("IDAT_CRC_PERIODIC_BUDGET"),
        huffman_kraft_budget=namespace.get("IDAT_HUFFMAN_KRAFT_BUDGET"),
        huffman_kraft_workers=fixit_felix_runtime._namespace_idat_huffman_kraft_workers(namespace),
        huffman_kraft_gpu_config=namespace.get("GPU_CONFIG"),
        kraft_backref_budget=namespace.get("IDAT_KRAFT_BACKREF_BUDGET"),
        stored_block_budget=namespace.get("IDAT_STORED_BLOCK_BUDGET"),
        global_crc_residue_budget=namespace.get("IDAT_GLOBAL_CRC_RESIDUE_BUDGET"),
        affine_corruption_budget=namespace.get("IDAT_AFFINE_CORRUPTION_BUDGET"),
        deflate_salvage_budget=namespace.get("IDAT_DEFLATE_SALVAGE_BUDGET"),
        set_idat_deflate_route_consumed=lambda value: namespace.__setitem__(
            "IDAT_DEFLATE_ROUTE_CONSUMED",
            value,
        ),
    )
    result = fixit_felix_runtime.try_idat_deflate_bruteforce(runtime, analysis)
    if result is None:
        return False
    return True


def _last_clone_is_valid_final(namespace: dict[str, Any]) -> bool:
    validation = namespace.get("LAST_CLONE_VALIDATION")
    if not isinstance(validation, dict):
        return True
    return bool(validation.get("png_ok") and validation.get("idat_complete"))


def _apply_deferred_after_weak_clone(namespace: dict[str, Any]) -> bool:
    if _last_clone_is_valid_final(namespace):
        return False
    if not namespace.get("DEFERRED_LINEFEED_SIGNATURE_REPAIR"):
        maybe_seed_internal_idat_linefeed_repair(namespace)
    if not namespace.get("DEFERRED_LINEFEED_SIGNATURE_REPAIR"):
        return False

    namespace["DEFERRED_REPAIR_STILL_REQUIRED"] = True
    namespace.setdefault("SideNotes", []).append(
        "-NearbyChunk produced a structural candidate, but IDAT validation still fails; deferred line-feed repair remains active."
    )
    sample = namespace.get("FILE_Origin")
    if sample:
        namespace["Sample"] = sample
        namespace["CLONESWAR"] = False
    candy = namespace.get("Candy")
    if callable(candy):
        candy(
            "Cowsay",
            "The quick structure patch still fails PNG validation. I am going back to the deferred line-feed repair.",
            "com",
        )
    namespace.get("Apply_Deferred_FindMagic_Repair", lambda: None)()
    return True


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
    predecide_ultimate_linefeed_resume_from_namespace(namespace)
    predecide_smash_brute_brawl_resume_from_namespace(namespace)
    predecide_idat_deep_beam_resume_from_namespace(namespace)
    run_pending_output_folder_cleanup_from_namespace(namespace)
    namespace.get("Prepare_Immediate_Summary", lambda: None)()
    if namespace.get("ULTIMATE_LINEFEED_RESUME_DECISION") == "resume":
        direct_resume = namespace.get("Run_Ultimate_Linefeed_Direct_Resume", lambda: None)
        direct_resume_result = direct_resume()
        if direct_resume_result is not None:
            return MainLoopIterationState()
    if namespace.get("SMASH_BRUTE_BRAWL_RESUME_DECISION") == "resume":
        direct_resume = namespace.get("Run_Smash_Brute_Brawl_Direct_Resume", lambda: None)
        direct_resume_result = direct_resume()
        if direct_resume_result is not None:
            return MainLoopIterationState()
    save_count_before = namespace["SAVE_COUNT"]
    offset = namespace["FindMagic"]()
    walk_state = run_main_chunk_walk(
        build_chunk_walk_runtime_from_namespace(namespace),
        MainChunkWalkContext(
            offset=offset,
            data_hex=namespace["DATAX"],
        ),
    )
    walk_finished = chunk_walk_reached_end(walk_state, namespace["DATAX"])
    clone_progress = (
        namespace["SAVE_COUNT"] != save_count_before
        or bool(namespace.get("CLONE_HANDOFF_PENDING"))
    )
    if not clone_progress:
        deferred_ready = bool(
            namespace.get("DEFERRED_LINEFEED_SIGNATURE_REPAIR")
            and deferred_linefeed_repair_is_ready(namespace)
        )
        if deferred_ready or (
            walk_finished and not namespace.get("DEFERRED_LINEFEED_SIGNATURE_REPAIR")
        ):
            namespace.get("Apply_Deferred_FindMagic_Repair", lambda: None)()
    else:
        if not _apply_deferred_after_weak_clone(namespace):
            namespace.get("Clear_Deferred_FindMagic_Repair", lambda: None)()
    clone_progress = (
        namespace["SAVE_COUNT"] != save_count_before
        or bool(namespace.get("CLONE_HANDOFF_PENDING"))
    )
    if not clone_progress:
        if namespace.pop("IDAT_DEFLATE_ROUTE_CONSUMED", False):
            namespace["PRINT"](
                "-IDAT deflate route consumed without clone; stopping this sample pass."
            )
            namespace["PRINT"]("-No new clone produced, stopping main loop.")
            return MainLoopIterationState(should_return=True)
        if has_unresolved_findings(namespace):
            if _try_unresolved_idat_deflate_route(namespace):
                if namespace.pop("IDAT_DEFLATE_ROUTE_CONSUMED", False):
                    namespace["PRINT"](
                        "-IDAT deflate route consumed without clone; stopping this sample pass."
                    )
                    namespace["PRINT"]("-No new clone produced, stopping main loop.")
                    return MainLoopIterationState(should_return=True)
                return MainLoopIterationState()
            explain_unimplemented_repair_route(namespace)
        else:
            namespace.get("Open_Current_Final_Image_If_Valid", lambda: None)()
            namespace["Candy"](
                "Cowsay",
                "Alright. I did not save anything this round. If I chew the same file again, that is not bravery, that is a loop.",
                "good",
            )
        namespace["PRINT"]("-No new clone produced, stopping main loop.")
        if not has_unresolved_findings(namespace):
            namespace["Candy"]("Cowsay", "See you Space Cowboy...", "good")
        return MainLoopIterationState(should_return=True)

    return MainLoopIterationState()


def run_main_chunk_walk(
    runtime: MainChunkWalkRuntime,
    context: MainChunkWalkContext,
) -> MainChunkWalkState:
    offset = context.offset
    if offset is None:
        return MainChunkWalkState(offset=offset)

    stopped_early = False
    while offset < len(context.data_hex):
        runtime.chunk_by_chunk(offset)
        namespace = runtime.namespace

        runtime.check_length(
            namespace["Orig_CD"],
            namespace["Orig_CL"],
            namespace["Orig_CT"],
        )
        if stop_chunk_walk_after_clone(runtime):
            stopped_early = True
            break

        runtime.check_chunk_name(
            namespace["Orig_CT"],
            namespace["Orig_CL"],
            namespace["Chunks_History"][-1],
        )
        if stop_chunk_walk_after_clone(runtime):
            stopped_early = True
            break

        runtime.get_info(namespace["Orig_CT"], namespace["Raw_Data"])
        if stop_chunk_walk_after_clone(runtime):
            stopped_early = True
            break

        runtime.checksum(
            namespace["Raw_Type"],
            namespace["Raw_Data"],
            namespace["Raw_Crc"],
        )
        if stop_chunk_walk_after_clone(runtime):
            stopped_early = True
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
            stopped_early = True
            break

    namespace = runtime.namespace
    if not stopped_early and should_run_fix_it_felix_after_file_tour(namespace):
        while True:
            runtime.fix_it_felix(namespace["Orig_CT"])
            if namespace["Show_Must_Go_On"] is True or namespace["Have_A_KitKat"] is True:
                break

    return MainChunkWalkState(offset=offset)
