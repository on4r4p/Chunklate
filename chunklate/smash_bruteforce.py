from __future__ import annotations

from collections.abc import Callable, MutableSequence
from dataclasses import dataclass
from typing import Any

from . import bruteforce, bruteforce_result, bruteforce_runtime, bruteforce_viewer


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
            crash=namespace["CRASH"],
            debug=namespace["DEBUG"],
            pause_debug=namespace["PAUSEDEBUG"],
        ),
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
            crash=context.crash,
            debug=context.debug,
            pause_debug=context.pause_debug,
        ),
    )

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
        ),
    )
