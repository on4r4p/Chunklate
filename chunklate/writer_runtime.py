from __future__ import annotations

import hashlib
import os
from collections.abc import MutableSequence
from dataclasses import dataclass
from typing import Any, Callable

from . import idat, output, png, writer


LegacyCall = Callable[..., Any]


@dataclass(frozen=True)
class WriteCloneContext:
    file_origin: str
    file_dir: str
    save_count: int
    max_saves: int | None
    have_a_kitkat: bool = False
    pause_enabled: bool = False


@dataclass(frozen=True)
class WriteCloneRuntime:
    remember_current_sample: LegacyCall
    prepare_clone_write: LegacyCall
    write_prepared_clone: LegacyCall
    betterror: LegacyCall
    end: LegacyCall
    candy: LegacyCall
    emit: LegacyCall
    pause: LegacyCall
    summarise: LegacyCall
    exit_process: Callable[[int], Any]
    set_sample: Callable[[str], Any]
    set_save_count: Callable[[int], Any]
    set_have_a_kitkat: Callable[[bool], Any]
    side_notes: MutableSequence[str]
    record_clone_validation: Callable[[dict[str, Any]], Any] = lambda validation: None


@dataclass(frozen=True)
class ClonePatchRuntime:
    data_hex: str
    candy: LegacyCall
    emit: LegacyCall
    betterror: LegacyCall
    write_clone: LegacyCall
    set_show_must_go_on: Callable[[bool], Any]
    remove_hex_range: LegacyCall = writer.remove_hex_range
    replace_hex_range: LegacyCall = writer.replace_hex_range
    save_debug_payloads: LegacyCall | None = None
    side_notes: MutableSequence[str] | None = None


def build_write_clone_runtime(
    *,
    namespace: dict[str, Any],
    remember_current_sample: LegacyCall,
    betterror: LegacyCall,
    end: LegacyCall,
    candy: LegacyCall,
    emit: LegacyCall,
    pause: LegacyCall,
    summarise: LegacyCall,
    exit_process: Callable[[int], Any],
    side_notes: MutableSequence[str],
    prepare_clone_write: LegacyCall = writer.prepare_clone_write,
    write_prepared_clone: LegacyCall = writer.write_prepared_clone,
) -> WriteCloneRuntime:
    return WriteCloneRuntime(
        remember_current_sample=remember_current_sample,
        prepare_clone_write=prepare_clone_write,
        write_prepared_clone=write_prepared_clone,
        betterror=betterror,
        end=end,
        candy=candy,
        emit=emit,
        pause=pause,
        summarise=summarise,
        exit_process=exit_process,
        set_sample=lambda value: namespace.__setitem__("Sample", value),
        set_save_count=lambda value: namespace.__setitem__("SAVE_COUNT", value),
        set_have_a_kitkat=lambda value: namespace.__setitem__("Have_A_KitKat", value),
        side_notes=side_notes,
        record_clone_validation=lambda validation: namespace.__setitem__(
            "LAST_CLONE_VALIDATION", validation
        ),
    )


def build_write_clone_runtime_from_namespace(namespace: dict[str, Any]) -> WriteCloneRuntime:
    return build_write_clone_runtime(
        namespace=namespace,
        remember_current_sample=namespace["Pandemonium_Remember_Current_Sample"],
        betterror=namespace["Betterror"],
        end=namespace["TheEnd"],
        candy=namespace["Candy"],
        emit=namespace["PRINT"],
        pause=namespace["Pause"],
        summarise=namespace["Summarise"],
        exit_process=namespace["sys"].exit,
        side_notes=namespace["SideNotes"],
    )


def build_write_clone_context(namespace: dict[str, Any]) -> WriteCloneContext:
    return WriteCloneContext(
        file_origin=namespace["FILE_Origin"],
        file_dir=namespace["FILE_DIR"],
        save_count=namespace["SAVE_COUNT"],
        max_saves=namespace["MAX_SAVES"],
        have_a_kitkat=namespace["Have_A_KitKat"],
        pause_enabled=namespace["PAUSE"],
    )


def _bytes_preview(raw: bytes, *, limit: int = 16) -> str:
    if len(raw) <= limit:
        return repr(raw)
    return "%r... (%s bytes total)" % (raw[:limit], len(raw))


def _patch_bytes_preview(data_fix: str) -> str | None:
    try:
        return _bytes_preview(bytes.fromhex(data_fix))
    except Exception:
        return None


def _source_bytes_preview(infos: Any) -> str | None:
    if isinstance(infos, bytes):
        return _bytes_preview(infos)
    return None


def _clone_patch_preview(data_fix: str, infos: Any) -> str:
    patch_bytes = _patch_bytes_preview(data_fix)
    source_bytes = _source_bytes_preview(infos)

    if patch_bytes is None:
        return "I am about to write a clone with bytes I cannot print cleanly. That is already a mood."

    if source_bytes is not None:
        return "Patch: I am replacing %s with %s in the clone." % (source_bytes, patch_bytes)

    return "Patch bytes ready: %s" % patch_bytes


def _clone_debug_payloads(data_fix: str, infos: Any, *, limit: int = 16) -> dict[str, bytes]:
    payloads: dict[str, bytes] = {}
    try:
        patch_bytes = bytes.fromhex(data_fix)
    except Exception:
        patch_bytes = None

    if isinstance(infos, bytes) and len(infos) > limit:
        payloads["source"] = infos
    if patch_bytes is not None and len(patch_bytes) > limit:
        payloads["replacement"] = patch_bytes
    return payloads


def save_clone_debug_payloads(
    file_origin: str,
    file_dir: str,
    label: str,
    start: int,
    end: int,
    payloads: dict[str, bytes],
) -> list[str]:
    clone_folder = output.ensure_clone_folder(file_origin, file_dir)
    payload_folder = os.path.join(clone_folder, "Debug_Payloads")
    os.makedirs(payload_folder, exist_ok=True)

    saved_paths: list[str] = []
    for name, raw in sorted(payloads.items()):
        digest = hashlib.sha1(raw).hexdigest()[:8]
        filename = "%s_%06d_%06d_%s_%s.bin" % (label, start, end, name, digest)
        path = os.path.join(payload_folder, filename)
        with open(path, "wb") as file:
            file.write(raw)
        saved_paths.append(os.path.relpath(path, clone_folder).replace("\\", "/"))
    return saved_paths


def _summary_with_clone_patch_note(
    infos: Any,
    patch_preview: str,
    debug_payload_paths: list[str] | None = None,
) -> str:
    notes = ["-Clone patch note: %s" % patch_preview]
    for path in debug_payload_paths or []:
        notes.append("-Clone debug payload: %s" % path)
    note = "\n".join(notes)
    if infos is None or infos == "":
        return note
    return "%s\n%s" % (str(infos).rstrip(), note)


def _append_side_note(runtime: ClonePatchRuntime, note: str) -> None:
    if runtime.side_notes is not None:
        runtime.side_notes.append(note)


def _crc_range_targets_idat(data_hex: str, start: int, end: int) -> bool:
    if end - start != 8 or start % 2 != 0 or end % 2 != 0:
        return False

    try:
        data = bytes.fromhex(data_hex)
    except ValueError:
        return False

    crc_byte_offset = start // 2
    try:
        for chunk in png.iter_chunks(data):
            if chunk.chunk_type != b"IDAT":
                continue
            if chunk.offset + 8 + chunk.length == crc_byte_offset:
                return True
    except png.PngFormatError:
        return False
    return False


def _idat_crc_only_guard_note(analysis: idat.IdatStreamAnalysis) -> str:
    reason = analysis.reason or analysis.zlib_error or analysis.status or "IDAT stream is still invalid"
    return "-Deferred IDAT CRC-only patch: zlib stream still invalid: %s." % reason


def _should_block_idat_crc_only_clone(
    runtime: ClonePatchRuntime,
    data_fix: str,
    start: int,
    end: int,
) -> tuple[bool, idat.IdatStreamAnalysis | None, str]:
    if len(data_fix) != 8:
        return False, None, ""
    if not _crc_range_targets_idat(runtime.data_hex, start, end):
        return False, None, ""

    try:
        fixed_hex = runtime.replace_hex_range(runtime.data_hex, data_fix, start, end)
        fixed_data = bytes.fromhex(fixed_hex)
    except Exception as exc:
        return True, None, "I could not even build the IDAT CRC-only candidate: %s" % exc

    analysis = idat.analyze_idat_stream(fixed_data)
    if analysis.complete:
        return False, analysis, ""

    reason = analysis.reason or analysis.zlib_error or analysis.status or "IDAT stream is still invalid"
    return True, analysis, reason


def announce_clone_write(
    runtime: WriteCloneRuntime,
    context: WriteCloneContext,
    clone_plan: writer.CloneWritePlan,
    infos: Any,
) -> None:
    runtime.candy(
        "Cowsay",
        "I am about to write a clone: %s" % clone_plan.target.name,
        "good",
    )
    if context.pause_enabled is True:
        runtime.pause("-Clone ready. Press Return to write it:")


def clone_validation_summary(data: bytes) -> dict[str, Any]:
    try:
        structure = png.validate_png_structure(data, require_decodable_idat=True)
    except Exception as exc:
        return {
            "png_ok": False,
            "idat_complete": False,
            "errors": ("validation crashed: %s" % exc,),
            "idat_status": "validation_error",
            "idat_reason": str(exc),
        }

    try:
        analysis = idat.analyze_idat_stream(data)
    except Exception as exc:
        idat_complete = False
        idat_status = "analysis_error"
        idat_reason = str(exc)
    else:
        idat_complete = bool(analysis.complete)
        idat_status = analysis.status
        idat_reason = analysis.reason or analysis.zlib_error or ""

    return {
        "png_ok": bool(structure.ok),
        "idat_complete": idat_complete,
        "errors": tuple(structure.errors),
        "idat_status": idat_status,
        "idat_reason": idat_reason,
    }


def clone_validation_is_final(validation: dict[str, Any]) -> bool:
    return bool(validation.get("png_ok") and validation.get("idat_complete"))


def clone_validation_is_artifact_only(validation: dict[str, Any]) -> bool:
    if clone_validation_is_final(validation):
        return False

    errors = tuple(str(error) for error in (validation.get("errors") or ()))
    marker_text = "\n".join(
        errors
        + (
            str(validation.get("idat_reason") or ""),
            str(validation.get("idat_status") or ""),
        )
    )
    blocking_markers = (
        "PNG signature is not at offset 0",
        "PNG has trailing bytes after IEND",
        "IEND is not the last chunk",
        "Chunk IDAT has invalid CRC",
        "IDAT zlib stream is invalid",
        "IDAT decompressed size does not match IHDR dimensions",
        "IDAT scanline filter type is invalid",
        "BadZlibHeader",
        "bad_adler",
        "Not enough image data",
        "zlib",
        "scanline",
        "decompressed",
    )
    return any(marker in marker_text for marker in blocking_markers)


def _clone_validation_failure_reason(validation: dict[str, Any]) -> str:
    errors = tuple(validation.get("errors") or ())
    if errors:
        return "; ".join(str(error) for error in errors)
    reason = str(validation.get("idat_reason") or "").strip()
    if reason:
        return reason
    status = str(validation.get("idat_status") or "").strip()
    if status:
        return status
    return "PNG/IDAT validation failed"


def run_write_clone(
    runtime: WriteCloneRuntime,
    context: WriteCloneContext,
    data: Any,
    infos: Any,
) -> None:
    if context.have_a_kitkat is True:
        runtime.emit("-Clone already queued")
        runtime.candy("Color", "yellow", "Skipping alternate repair branch before this becomes a mille-feuille.")  #
        runtime.side_notes.append("-Clone already queued; skipping alternate repair branch before this becomes a mille-feuille.")
        return None

    runtime.remember_current_sample()

    try:
        clone_plan = runtime.prepare_clone_write(
            context.file_origin,
            context.file_dir,
            data,
            context.save_count,
            context.max_saves,
        )
    except Exception as exc:
        runtime.betterror(exc, "WriteClone")
        runtime.end()
        return None

    target = clone_plan.target
    clone_validation = clone_validation_summary(clone_plan.data)
    runtime.record_clone_validation(clone_validation)
    announce_clone_write(runtime, context, clone_plan, infos)
    runtime.emit(runtime.candy("Color", "green", "-Saving to : %s") % target.path)
    runtime.side_notes.append("-Saving to : %s" % target.path)

    try:
        runtime.write_prepared_clone(clone_plan)
    except Exception as exc:
        runtime.betterror(exc, "WriteClone")
        runtime.emit(
            runtime.candy("Color", "red", "Error WriteClone:%s")
            % runtime.candy("Color", "yellow", exc)
        )
        runtime.end()
        return None

    if clone_validation_is_artifact_only(clone_validation):
        reason = _clone_validation_failure_reason(clone_validation)
        artifact_note = (
            "-Clone written as artifact only; PNG/IDAT validation failed: %s"
            % reason
        )
        runtime.emit(runtime.candy("Color", "yellow", artifact_note))
        runtime.side_notes.append(artifact_note)
        artifact_summary = artifact_note if infos is None or infos == "" else "%s\n%s" % (
            str(infos).rstrip(),
            artifact_note,
        )
        runtime.summarise(artifact_summary)
        return None

    runtime.set_sample(target.path)
    runtime.set_save_count(clone_plan.save_count)
    runtime.set_have_a_kitkat(True)

    runtime.summarise(infos)

    if clone_plan.max_saves_reached:
        runtime.emit("-Max saves reached: %s" % context.max_saves)
        runtime.exit_process(0)

    return None


def run_write_clone_from_namespace(
    namespace: dict[str, Any],
    data: Any,
    infos: Any,
    *,
    runner: LegacyCall = run_write_clone,
) -> None:
    return runner(
        build_write_clone_runtime_from_namespace(namespace),
        build_write_clone_context(namespace),
        data,
        infos,
    )


def run_remove_chunk(
    runtime: ClonePatchRuntime,
    start: int,
    length: int,
    infos: Any,
) -> Any:
    runtime.candy("Title", "Removing Chunk")
    fix = runtime.remove_hex_range(runtime.data_hex, start, length)
    return runtime.write_clone(fix, infos)


def run_save_clone(
    runtime: ClonePatchRuntime,
    data_fix: str,
    start: int,
    end: int,
    infos: Any,
) -> Any:
    runtime.candy("Title", "Saving Clone")
    try:
        runtime.emit("-Data : %s\n" % bytes.fromhex(data_fix))
    except Exception as exc:
        runtime.betterror(exc, "SaveClone")

    patch_preview = _clone_patch_preview(data_fix, infos)
    runtime.candy("Cowsay", patch_preview, "com")
    block_idat_crc, analysis, reason = _should_block_idat_crc_only_clone(runtime, data_fix, start, end)
    if block_idat_crc:
        runtime.candy(
            "Cowsay",
            "That would only repaint an IDAT CRC label while the compressed stream still falls apart.",
            "bad",
        )
        runtime.candy(
            "Cowsay",
            "No clone for this one. I am keeping the note, not making another fake checkpoint.",
            "com",
        )
        note = _idat_crc_only_guard_note(analysis) if analysis is not None else "-Deferred IDAT CRC-only patch: %s." % reason
        _append_side_note(runtime, note)
        return None

    debug_payload_paths: list[str] = []
    debug_payloads = _clone_debug_payloads(data_fix, infos)
    if debug_payloads and runtime.save_debug_payloads is not None:
        try:
            debug_payload_paths = runtime.save_debug_payloads(
                "clone_patch",
                start,
                end,
                debug_payloads,
            )
        except Exception as exc:
            runtime.betterror(exc, "SaveCloneDebugPayload")
    fix = runtime.replace_hex_range(runtime.data_hex, data_fix, start, end)
    runtime.set_show_must_go_on(True)
    return runtime.write_clone(
        fix,
        _summary_with_clone_patch_note(infos, patch_preview, debug_payload_paths),
    )
