from __future__ import annotations

from collections.abc import Callable, MutableSequence
from dataclasses import dataclass
import os
from typing import Any

from . import (
    bruteforce,
    bruteforce_result,
    bruteforce_runtime,
    bruteforce_viewer,
    output,
    platform_runtime,
    smash_checkpoint,
)


LegacyCall = Callable[..., Any]


@dataclass(frozen=True)
class SmashBruteBrawlLegacyContext:
    file: Any
    chunk_name: bytes
    chunk_length: int
    data_offset: int
    from_error: Any
    data_hex: str
    pandora_box: Any
    libpng_errors: tuple[str, ...]
    tmp_image_paths: MutableSequence[str]
    file_origin: str
    current_diff: str
    edit_mode: str = "Replace"
    bf_mode: str = "Brutus"
    brute_crc: bool = True
    brute_length: bool = True
    old_crc: Any = False
    brute_level: int = 0
    campaign_focus: str = ""
    crash: Any = False
    debug: bool = False
    pause_debug: bool = False


@dataclass(frozen=True)
class SmashBruteBrawlLegacyRuntime:
    load_spec: LegacyCall
    product: LegacyCall
    loadingbar: LegacyCall
    minibar: LegacyCall
    image_show: Any
    cv2: Any
    numpy: Any
    image: Any
    psutil: Any
    stderr_redirector: LegacyCall
    sleep: LegacyCall
    ask_timeout: LegacyCall
    naming: LegacyCall
    emit: LegacyCall
    candy: LegacyCall
    summarise: LegacyCall
    save_error: LegacyCall
    end: LegacyCall
    checkpoint: LegacyCall
    side_notes: MutableSequence[Any]
    pause: LegacyCall
    sync_state: LegacyCall
    raw_print: LegacyCall = print
    register_image_viewers: LegacyCall = bruteforce.register_image_viewers
    run_scan: LegacyCall = bruteforce_runtime.run_scan
    show_candidate: LegacyCall = bruteforce_viewer.show_candidate
    run_result: LegacyCall = bruteforce_result.run_result
    progress_path: str = ""
    source_hash: str = ""
    source_size: int = 0
    source_path: str = ""
    resume_record: dict[str, Any] | None = None
    smash_workers: str | int | None = 0


def _smash_worker_profile_counts() -> dict[str, int]:
    cpu_count = platform_runtime.detected_cpu_count()
    return {
        "cpu": cpu_count,
        "min": platform_runtime.recommended_worker_count(cpu_count, profile="min"),
        "normal": platform_runtime.recommended_worker_count(cpu_count, profile="normal"),
        "max": platform_runtime.recommended_worker_count(cpu_count, profile="max"),
    }


def _smash_workers_from_value(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in ("auto", "normal"):
        return platform_runtime.recommended_worker_count(profile="normal")
    if text in ("min", "max"):
        return platform_runtime.recommended_worker_count(profile=text)
    return max(0, int(text))


def _smash_prompt_candy(namespace: dict[str, Any], text: str, mood: str = "com") -> None:
    prompt_candy = namespace.get("Prompt_Candy")
    if callable(prompt_candy):
        prompt_candy("Cowsay", text, mood)
        return
    namespace.get("Candy", lambda *args, **kwargs: None)("Cowsay", text, mood)


def _smash_print_error(namespace: dict[str, Any], text: str) -> None:
    print_func = namespace.get("PRINT")
    if not callable(print_func):
        return
    candy = namespace.get("Candy")
    if callable(candy):
        text = candy("Color", "red", text)
    print_func(text)


def _smash_input(namespace: dict[str, Any], prompt: str) -> str:
    input_func = namespace.get("input", input)
    try:
        return str(input_func(prompt)).strip().lower()
    except EOFError:
        return ""


def _smash_print_worker_menu(namespace: dict[str, Any]) -> None:
    counts = _smash_worker_profile_counts()
    lines = [
        "SmashBruteBrawl CPU worker no jutsu:",
        "CPU detected: %s" % counts["cpu"],
        "min workers: %s" % counts["min"],
        "normal workers: %s" % counts["normal"],
        "max workers: %s" % counts["max"],
        "",
        "0. disabled",
        "min. CPU / 4",
        "normal. CPU / 2",
        "max. CPU - 1",
        "custom. enter an exact worker count",
        "",
        "Empty keeps SmashBruteBrawl single-process.",
    ]
    _smash_prompt_candy(namespace, "\n".join(lines), "com")


def resolve_smash_workers_from_namespace(
    namespace: dict[str, Any],
    *,
    bf_mode: str = "",
) -> str | int | None:
    configured = namespace.get("SMASH_BRUTE_BRAWL_WORKERS")
    if configured is not None:
        return configured
    cached = namespace.get("_SMASH_BRUTE_BRAWL_SESSION_WORKERS")
    if cached is not None:
        return cached
    if namespace.get("AUTO", False) or namespace.get("NODIALOGUE", False):
        return 0
    if "AUTO" not in namespace and "NODIALOGUE" not in namespace:
        return 0

    while True:
        _smash_print_worker_menu(namespace)
        choice = _smash_input(namespace, "SmashBruteBrawl worker profile [0 disabled] > ")
        if choice == "":
            namespace["_SMASH_BRUTE_BRAWL_SESSION_WORKERS"] = 0
            return 0
        if choice in ("min", "normal", "max", "auto"):
            workers = _smash_workers_from_value(choice)
            namespace["_SMASH_BRUTE_BRAWL_SESSION_WORKERS"] = workers
            return workers
        if choice == "custom":
            choice = _smash_input(namespace, "Custom SmashBruteBrawl worker count > ")
        try:
            workers = int(choice)
        except ValueError:
            _smash_print_error(namespace, "-Enter 0, min, normal, max, custom, or a worker count.")
            continue
        if workers >= 0:
            namespace["_SMASH_BRUTE_BRAWL_SESSION_WORKERS"] = workers
            return workers
        _smash_print_error(namespace, "-Worker count must be zero or higher.")


def run_legacy_smash_brute_brawl_from_namespace(
    namespace: dict[str, Any],
    file: Any,
    chunk_name: Any,
    chunk_length: int,
    data_offset: int,
    from_error: Any,
    edit_mode: str = "Replace",
    bf_mode: str = "Brutus",
    brute_crc: bool = True,
    brute_length: bool = True,
    old_crc: Any = False,
    brute_level: int | None = None,
    *,
    bridge: LegacyCall | None = None,
) -> Any:
    if bridge is None:
        bridge = run_legacy_smash_brute_brawl

    namespace["Candy"]("Title", "SmashBruteBrawl")
    namespace["Candy"]("Title", "Attempting Bruteforce To Repair Corrupted Chunk Data:")
    if isinstance(chunk_name, bytes):
        pass
    else:
        try:
            chunk_name = chunk_name.encode(errors="ignore")
        except Exception as exc:
            namespace["Betterror"](exc, "SmashBruteBrawl")
            if namespace["DEBUG"] is True:
                namespace["PRINT"](
                    namespace["Candy"]("Color", "red", "Error:%s")
                    % namespace["Candy"]("Color", "yellow", exc)
                )

    namespace["TmpImgLst"] = []
    progress_paths = smash_brute_brawl_progress_paths_from_namespace(namespace)
    source_data = smash_brute_brawl_source_data_from_namespace(namespace)
    source_hash = smash_checkpoint.source_hash(source_data) if source_data else ""
    if source_data:
        try:
            smash_checkpoint.write_source_snapshot(progress_paths, source_data)
        except OSError as exc:
            namespace["PRINT"]("-SmashBruteBrawl checkpoint snapshot warning: %s" % exc)
    resume_record = None
    resume_decision = str(namespace.get("SMASH_BRUTE_BRAWL_RESUME_DECISION", "") or "").strip().lower()
    retry_state = namespace.get("_SBB_BLACKFILL_RETRY_STATE")
    retry_starts_fresh = False
    campaign_focus = ""
    if isinstance(retry_state, dict):
        retry_starts_fresh = bool(retry_state.pop("disable_resume_once", False))
        campaign_focus = str(retry_state.get("campaign_focus") or "")
    if resume_decision == "resume" and not retry_starts_fresh:
        resume_record, progress_warning = smash_checkpoint.load_json(progress_paths.progress_path)
        if progress_warning:
            namespace["PRINT"]("-%s" % progress_warning)
    elif resume_decision == "resume" and retry_starts_fresh:
        namespace["PRINT"]("-SmashBruteBrawl retry starts fresh for this pass.")

    def load_spec(request):
        return namespace["GetSpec"](
            chunk_name,
            request.mode,
            **bruteforce.spec_request_kwargs(request),
        )

    def save_viewer_error(error, def_name):
        return namespace["Betterror"](error, def_name)

    def sync_legacy_state(crash, eta_seconds, diff):
        namespace["CRASH"] = crash
        namespace["ETA"] = eta_seconds
        if diff:
            namespace["DIFF"] = diff

    smash_workers = resolve_smash_workers_from_namespace(namespace, bf_mode=bf_mode)

    return bridge(
        SmashBruteBrawlLegacyRuntime(
            load_spec=load_spec,
            product=namespace["Product"],
            loadingbar=namespace["Loadingbar"],
            minibar=namespace["Minibar"],
            image_show=namespace.get("ImageShow"),
            cv2=namespace.get("cv2"),
            numpy=namespace.get("np"),
            image=namespace.get("Image"),
            psutil=namespace.get("psutil"),
            stderr_redirector=namespace["stderr_redirector"],
            sleep=namespace["time"].sleep,
            ask_timeout=namespace["inputimeout"],
            naming=namespace["Naming"],
            emit=namespace["PRINT"],
            candy=namespace["Candy"],
            summarise=namespace["Summarise"],
            save_error=save_viewer_error,
            end=namespace["TheEnd"],
            checkpoint=namespace["CheckPoint"],
            side_notes=namespace["SideNotes"],
            pause=namespace["Pause"],
            sync_state=sync_legacy_state,
            progress_path=progress_paths.progress_path,
            source_hash=source_hash,
            source_size=len(source_data),
            source_path=progress_paths.source_raw_path,
            resume_record=resume_record,
            smash_workers=smash_workers,
        ),
        SmashBruteBrawlLegacyContext(
            file=file,
            chunk_name=chunk_name,
            chunk_length=chunk_length,
            data_offset=data_offset,
            from_error=from_error,
            data_hex=namespace["DATAX"],
            pandora_box=namespace["PandoraBox"],
            libpng_errors=tuple(namespace["LIBPNG_ERR"]),
            tmp_image_paths=namespace["TmpImgLst"],
            file_origin=namespace["FILE_Origin"],
            current_diff=namespace.get("DIFF", ""),
            edit_mode=edit_mode,
            bf_mode=bf_mode,
            brute_crc=brute_crc,
            brute_length=brute_length,
            old_crc=old_crc,
            brute_level=namespace["Brute_LvL"] if brute_level is None else brute_level,
            campaign_focus=campaign_focus,
            crash=namespace["CRASH"],
            debug=namespace["DEBUG"],
            pause_debug=namespace["PAUSEDEBUG"],
        ),
    )


def smash_brute_brawl_progress_paths_from_namespace(namespace: dict[str, Any]) -> smash_checkpoint.SmashProgressPaths:
    folder = namespace.get("SMASH_BRUTE_BRAWL_FOLDER")
    if not folder:
        folder = output.clone_folder(namespace.get("FILE_Origin", ""), namespace.get("FILE_DIR", ""))
    os_module = namespace.get("os", os)
    progress_path = namespace.get("SMASH_BRUTE_BRAWL_PROGRESS_PATH") or os_module.path.join(
        folder,
        smash_checkpoint.SMASH_PROGRESS_NAME,
    )
    source_raw_path = namespace.get("SMASH_BRUTE_BRAWL_SOURCE_RAW_PATH") or os_module.path.join(
        folder,
        smash_checkpoint.SMASH_SOURCE_RAW_NAME,
    )
    source_png_path = namespace.get("SMASH_BRUTE_BRAWL_SOURCE_PATH") or os_module.path.join(
        folder,
        smash_checkpoint.SMASH_SOURCE_NAME,
    )
    return smash_checkpoint.SmashProgressPaths(
        folder=folder,
        progress_path=progress_path,
        source_raw_path=source_raw_path,
        source_png_path=source_png_path,
    )


def smash_brute_brawl_source_data_from_namespace(namespace: dict[str, Any]) -> bytes:
    data = namespace.get("DATA_BYTES", b"")
    if isinstance(data, bytes):
        return data
    if isinstance(data, bytearray):
        return bytes(data)
    data_hex = namespace.get("DATAX", "")
    if isinstance(data_hex, str) and data_hex:
        try:
            return bytes.fromhex(data_hex)
        except ValueError:
            return b""
    return b""


def _cowsay(namespace: dict[str, Any], text: str, mood: str = "com") -> None:
    namespace.get("Candy", lambda *args, **kwargs: None)("Cowsay", text, mood)


def run_smash_brute_brawl_direct_resume_from_namespace(namespace: dict[str, Any]) -> Any:
    paths = smash_brute_brawl_progress_paths_from_namespace(namespace)
    record, warning = smash_checkpoint.load_json(paths.progress_path)
    if warning:
        _cowsay(namespace, warning, "com")
        return None
    if not record:
        return None
    source_data = smash_checkpoint.load_source_snapshot(paths)
    if source_data is None:
        _cowsay(
            namespace,
            "I found a SmashBruteBrawl checkpoint, but no clean Smash source snapshot yet.",
            "bad",
        )
        _cowsay(namespace, "I will finish the file tour before resuming SmashBruteBrawl.", "com")
        return None
    if record.get("source_hash") != smash_checkpoint.source_hash(source_data):
        _cowsay(
            namespace,
            "The SmashBruteBrawl source snapshot does not match the progress checkpoint. I will finish the file tour first.",
            "com",
        )
        return None
    invocation = record.get("invocation")
    if not isinstance(invocation, dict):
        _cowsay(namespace, "The SmashBruteBrawl checkpoint has no runnable invocation.", "com")
        return None

    namespace["DATA_BYTES"] = source_data
    namespace["DATAX"] = source_data.hex()
    namespace["SMASH_BRUTE_BRAWL_RESUME_DECISION"] = "resume"
    campaign_focus = str(invocation.get("campaign_focus") or "")
    if campaign_focus:
        namespace.setdefault("_SBB_BLACKFILL_RETRY_STATE", {})["campaign_focus"] = campaign_focus
    namespace["Candy"]("Title", "SmashBruteBrawl resume:")
    _cowsay(
        namespace,
        "Resume accepted. I loaded the clean Smash source snapshot and I am jumping straight back to SmashBruteBrawl.",
        "good",
    )
    chunk_name = bytes.fromhex(str(invocation.get("chunk_name_hex") or "")) or str(
        invocation.get("chunk_name") or ""
    ).encode(errors="ignore")
    chunk_name_text = chunk_name.decode(errors="ignore")
    return run_legacy_smash_brute_brawl_from_namespace(
        namespace,
        invocation.get("file") or namespace.get("FILE_Origin", ""),
        chunk_name_text,
        int(invocation.get("chunk_length") or 0),
        int(invocation.get("data_offset") or 0),
        invocation.get("from_error") or "SmashBruteBrawl resume",
        str(invocation.get("edit_mode") or "Replace"),
        str(invocation.get("bf_mode") or "Brutus"),
        bool(invocation.get("brute_crc", True)),
        bool(invocation.get("brute_length", True)),
        invocation.get("old_crc") or False,
        brute_level=int(invocation.get("brute_level") or 0),
    )


def build_viewer_runtime(
    runtime: SmashBruteBrawlLegacyRuntime,
    context: SmashBruteBrawlLegacyContext,
) -> bruteforce_viewer.BruteForceViewerRuntime:
    return bruteforce_viewer.BruteForceViewerRuntime(
        data_hex=context.data_hex,
        data_offset=context.data_offset,
        libpng_errors=context.libpng_errors,
        tmp_image_paths=context.tmp_image_paths,
        cv2=runtime.cv2,
        numpy=runtime.numpy,
        image=runtime.image,
        psutil=runtime.psutil,
        stderr_redirector=runtime.stderr_redirector,
        sleep=runtime.sleep,
        ask_timeout=runtime.ask_timeout,
        naming=runtime.naming,
        file_origin=context.file_origin,
        emit=runtime.emit,
        candy=runtime.candy,
        summarise=runtime.summarise,
        save_error=runtime.save_error,
        end=runtime.end,
        raw_print=runtime.raw_print,
        debug=context.debug,
    )


def run_legacy_smash_brute_brawl(
    runtime: SmashBruteBrawlLegacyRuntime,
    context: SmashBruteBrawlLegacyContext,
) -> Any:
    def show_png(png_bytes, candidate_bytes, loop_index, debug_bytes):
        return runtime.show_candidate(
            build_viewer_runtime(runtime, context),
            png_bytes,
            candidate_bytes,
            loop_index,
            debug_bytes=debug_bytes,
        )

    runtime.register_image_viewers(runtime.image_show)
    suppress_candidate_viewer = "FixItFelix partial IDAT blackfill" in str(
        context.from_error
    )

    try:
        scan_result = runtime.run_scan(
            bruteforce_runtime.SmashBruteBrawlRuntime(
                load_spec=runtime.load_spec,
                product=runtime.product,
                loadingbar=runtime.loadingbar,
                minibar=runtime.minibar,
                show_candidate=show_png,
                emit=runtime.emit,
                pause=runtime.pause,
                side_notes=runtime.side_notes,
                progress_path=runtime.progress_path,
                source_hash=runtime.source_hash,
                source_size=runtime.source_size,
                source_path=runtime.source_path,
                resume_record=runtime.resume_record,
                smash_workers=runtime.smash_workers,
                suppress_candidate_viewer=suppress_candidate_viewer,
            ),
            bruteforce_runtime.SmashBruteBrawlContext(
                file=context.file,
                chunk_name=context.chunk_name,
                chunk_length=context.chunk_length,
                data_offset=context.data_offset,
                from_error=context.from_error,
                data_hex=context.data_hex,
                pandora_box=context.pandora_box,
                edit_mode=context.edit_mode,
                bf_mode=context.bf_mode,
                brute_crc=context.brute_crc,
                brute_length=context.brute_length,
                old_crc=context.old_crc,
                brute_level=context.brute_level,
                campaign_focus=context.campaign_focus,
                crash=context.crash,
                debug=context.debug,
                pause_debug=context.pause_debug,
            ),
        )
    except smash_checkpoint.SmashBruteBrawlInterrupted as exc:
        runtime.candy(
            "Cowsay",
            "SmashBruteBrawl stopped. I kept the progress checkpoint so the next run can resume: %s"
            % exc.progress_path,
            "com",
        )
        raise SystemExit(130)

    runtime.sync_state(
        scan_result.crash,
        scan_result.eta_seconds,
        scan_result.diff or None,
    )
    final_diff = scan_result.diff or context.current_diff

    return runtime.run_result(
        bruteforce_result.BruteForceResultRuntime(
            emit=runtime.emit,
            candy=runtime.candy,
            checkpoint=runtime.checkpoint,
            side_notes=runtime.side_notes,
            suppress_failure_theatre=(
                "FixItFelix partial IDAT blackfill" in str(context.from_error)
            ),
        ),
        bruteforce_result.BruteForceResultContext(
            state=scan_result.state,
            old_crc=scan_result.old_crc,
            file=context.file,
            chunk_name=context.chunk_name,
            full_new_data_hex=scan_result.full_new_data.hex(),
            png_bytes_hex=scan_result.png_bytes.hex(),
            data_offset=context.data_offset,
            chunk_length=context.chunk_length,
            to_brute=scan_result.to_brute,
            edit_mode=context.edit_mode,
            bf_mode=scan_result.bf_mode,
            brute_crc=context.brute_crc,
            brute_length=context.brute_length,
            from_error=context.from_error,
            diff=final_diff,
            tmp_image_paths=tuple(context.tmp_image_paths),
            brute_level=context.brute_level,
        ),
    )
