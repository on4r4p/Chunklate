from __future__ import annotations

from collections.abc import Callable, MutableSequence
import concurrent.futures
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
import hashlib
import math
import multiprocessing
from pathlib import Path
import signal
import shutil
import time
from typing import Any
import zlib

from . import (
    bruteforce,
    gpu_runtime,
    idat_crc_forge,
    idat,
    png,
    smash_backend,
    smash_checkpoint,
    smash_opengl_backend,
)


LegacyCall = Callable[..., Any]
SBB_CANDIDATE_ALGORITHM_VERSION = 5
CRC_FORGE_WINDOW_DISPLAY_LIMIT = 4
CRC_FORGE_BYTE_COUNT_DISPLAY_LIMIT = 5
CRC_FORGE_BOUNDED_NO_TIMEOUT_CANDIDATES = 10_000_000
SBB_DANGEROUS_LEVEL_WARNING = 15
SBB_ETA_REFERENCE_RATE = 1_000_000.0
SBB_LONG_FALLBACK_SECONDS = 24 * 60 * 60
SECONDS_PER_YEAR = 365.25 * 24 * 60 * 60


@dataclass(frozen=True)
class CrcForgeScanOutcome:
    found: bool
    budget_stopped: bool = False
    tested_candidates: int = 0
    estimated_candidates: int = 0
    last_byte_count: int = 0

    def __bool__(self) -> bool:
        return bool(self.found)


@dataclass(frozen=True)
class SbbFallbackDecision:
    action: str = "trust"
    brute_level: int | None = None
    byte_count: int | None = None


@dataclass(frozen=True)
class SmashBruteBrawlContext:
    file: Any
    chunk_name: bytes
    chunk_length: int
    data_offset: int
    from_error: Any
    data_hex: str
    pandora_box: Any
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


def _format_crc_forge_windows(
    windows: tuple[idat_crc_forge.ForgeWindow, ...],
    *,
    limit: int = CRC_FORGE_WINDOW_DISPLAY_LIMIT,
) -> str:
    if not windows:
        return "auto"
    shown = list(windows[: max(1, int(limit))])
    parts = ["%s:%s" % (window.start, window.end) for window in shown]
    remaining = len(windows) - len(shown)
    if remaining > 0:
        parts.append("+%s more" % remaining)
    return ", ".join(parts)


def _format_crc_forge_byte_counts(
    byte_counts: tuple[int, ...],
    *,
    limit: int = CRC_FORGE_BYTE_COUNT_DISPLAY_LIMIT,
) -> str:
    if not byte_counts:
        return "auto"
    shown = list(byte_counts[: max(1, int(limit))])
    text = "/".join(str(count) for count in shown)
    remaining = len(byte_counts) - len(shown)
    if remaining > 0:
        text += " (+%s more)" % remaining
    return text


def _crc_forge_auto_max_seconds(summary: idat_crc_forge.ForgeScanSummary, mode: str) -> float:
    if str(mode or "auto").strip().lower() == "force":
        return 0.0
    if 0 < int(summary.estimated_candidates) <= CRC_FORGE_BOUNDED_NO_TIMEOUT_CANDIDATES:
        return 0.0
    return float(idat_crc_forge.HERMESPROBE_AUTO_MAX_SECONDS)


@dataclass(frozen=True)
class SmashBruteBrawlRuntime:
    load_spec: LegacyCall
    product: LegacyCall
    loadingbar: LegacyCall
    minibar: LegacyCall
    show_candidate: LegacyCall
    emit: LegacyCall
    pause: LegacyCall
    side_notes: MutableSequence[Any]
    raw_print: LegacyCall = print
    now: LegacyCall = datetime.now
    progress_path: str = ""
    source_hash: str = ""
    source_size: int = 0
    source_path: str = ""
    resume_record: dict[str, Any] | None = None
    smash_workers: str | int | None = 0
    suppress_candidate_viewer: bool = False
    gpu_config: gpu_runtime.GpuRuntimeConfig = gpu_runtime.GpuRuntimeConfig()
    crc_forge_mode: str = "auto"
    crc_forge_bytes: int | None = None
    crc_forge_window: str | None = None
    input_func: LegacyCall | None = None


@dataclass(frozen=True)
class SmashBruteBrawlScanResult:
    state: bruteforce.BruteForceMatchState
    old_crc: Any
    bf_mode: str
    full_new_data: bytes
    png_bytes: bytes
    to_brute: str
    diff: str
    crash: Any
    eta_seconds: int


@dataclass
class SmashBruteBrawlScanState:
    state: bruteforce.BruteForceMatchState
    full_new_data: bytes = b""
    png_bytes: bytes = b""
    to_brute: str = ""
    diff: str = ""
    crash: Any = False
    eta_seconds: int = 0
    tested_candidates: int = 0
    accepted_candidates: int = 0
    rejected_candidates: int = 0
    outer_index: int = 0
    length: int = 0
    inner_index: int = 0
    byte_position: int = 0
    edit_kind_index: int = 0
    stage: str = ""
    bonus_offset: int = 0
    bonus_value: int = 0
    last_progress_write_at: float = 0.0
    rejected_reasons: dict[str, int] = field(default_factory=dict)
    first_rejection_reason: str = ""
    last_rejection_emit_at: float = 0.0
    last_rejection_emit_count: int = 0
    untrusted_preview_count: int = 0
    untrusted_preview_hashes: set[str] = field(default_factory=set)


@dataclass(frozen=True)
class SbbCandidateValidation:
    ok: bool
    reason: str = ""
    category: str = "valid_structural"


TWOBYTES_PROGRESS_DOT_STEP = 1024


def twobytes_progress_dots_line(
    prefix: str,
    *,
    position: int,
    terminal_width: int | None = None,
) -> str:
    width = terminal_width or shutil.get_terminal_size((80, 20)).columns
    available = max(0, width - len(prefix) - 1)
    if available <= 0:
        return "%s\033[K" % prefix
    cycle = available * 2
    phase = (max(position, 0) // TWOBYTES_PROGRESS_DOT_STEP) % cycle
    dot_count = phase + 1 if phase < available else cycle - phase
    return "%s%s\033[K" % (prefix, "." * max(1, dot_count))


def emit_debug_report(
    runtime: SmashBruteBrawlRuntime,
    context: SmashBruteBrawlContext,
    *,
    chunklen_spec: Any,
    chunk_format: Any,
    chunk_data: Any,
    max_iter: int,
    maxchunklen: int,
    minchunklen: int,
    step: int,
) -> None:
    runtime.emit("File:%s" % context.file)
    runtime.emit("ChunkName:%s" % context.chunk_name)
    runtime.emit("DataOffset:%s" % context.data_offset)
    runtime.emit("ChunkLength:%s" % context.chunk_length)
    runtime.emit("Brute_LvL:%s" % context.brute_level)
    runtime.emit("BruteCrc:%s" % context.brute_crc)
    runtime.emit("BruteLength:%s" % context.brute_length)
    runtime.emit("EditMode:%s" % context.edit_mode)
    runtime.emit("FromError:%s" % context.from_error)
    runtime.emit("chunklen_spec:%s" % str(chunklen_spec))
    runtime.emit("chunk_format:%s" % str(chunk_format))
    runtime.emit("chunk_data:%s" % str(chunk_data))
    runtime.emit("max_iter:%s" % max_iter)
    runtime.emit("maxchunklen:%s" % maxchunklen)
    runtime.emit("minchunklen:%s" % minchunklen)
    runtime.emit("step:%s" % step)
    if context.pause_debug is True:
        runtime.pause("Pause:SmashBruteBrawl")


def build_attempt(
    context: SmashBruteBrawlContext,
    old_crc: Any,
    length_bytes: bytes,
    payload_data: bytes,
    crc_data: bytes,
    before: bytes,
    after: bytes,
) -> bruteforce.BruteForceCandidateAttempt:
    return bruteforce.prepare_candidate_attempt(
        context.chunk_name,
        length_bytes,
        payload_data,
        crc_data,
        before,
        after,
        brute_length=context.brute_length,
        brute_crc=context.brute_crc,
        old_crc=old_crc,
    )


def _sbb_idat_stream(data: bytes) -> bytes:
    try:
        return b"".join(chunk.data for chunk in png.iter_chunks(data) if chunk.chunk_type == b"IDAT")
    except png.PngFormatError:
        return b""


def _sbb_parse_ihdr(data: bytes) -> tuple[int, int, int, int] | None:
    try:
        ihdr = next((chunk for chunk in png.iter_chunks(data) if chunk.chunk_type == b"IHDR"), None)
    except png.PngFormatError:
        return None
    if ihdr is None or ihdr.length != 13:
        return None
    try:
        width = int.from_bytes(ihdr.data[0:4], "big")
        height = int.from_bytes(ihdr.data[4:8], "big")
        bit_depth = ihdr.data[8]
        color_type = ihdr.data[9]
    except (IndexError, TypeError):
        return None
    return width, height, bit_depth, color_type


def _sbb_visual_sanity_failure(data: bytes) -> str:
    ihdr = _sbb_parse_ihdr(data)
    if ihdr is None:
        return "IHDR is missing or malformed"
    width, height, bit_depth, color_type = ihdr
    idat_stream = _sbb_idat_stream(data)
    if not idat_stream:
        return "IDAT stream is missing"
    try:
        filtered_scanlines = zlib.decompress(idat_stream)
    except zlib.error as exc:
        return "IDAT zlib stream is invalid: %s" % exc

    raw_rows = png.unfilter_scanlines(
        filtered_scanlines,
        width=width,
        height=height,
        bit_depth=bit_depth,
        color_type=color_type,
    )
    if raw_rows is None:
        return "IDAT scanlines cannot be unfiltered"
    if raw_rows and all(value == 0 for value in raw_rows):
        return "decoded pixels are all zero"

    if bit_depth == 8 and color_type == 6 and len(raw_rows) >= 4:
        alpha = raw_rows[3::4]
        if alpha and all(value == 0 for value in alpha):
            return "decoded RGBA pixels are fully transparent"
        if alpha:
            mean_alpha = sum(alpha) / float(len(alpha))
            near_transparent = sum(1 for value in alpha if value <= 2)
            if mean_alpha < 8.0 or near_transparent / float(len(alpha)) > 0.98:
                return "decoded RGBA pixels are almost fully transparent"
    if bit_depth == 8 and color_type == 4 and len(raw_rows) >= 2:
        alpha = raw_rows[1::2]
        if alpha and all(value == 0 for value in alpha):
            return "decoded grayscale-alpha pixels are fully transparent"
        if alpha:
            mean_alpha = sum(alpha) / float(len(alpha))
            near_transparent = sum(1 for value in alpha if value <= 2)
            if mean_alpha < 8.0 or near_transparent / float(len(alpha)) > 0.98:
                return "decoded grayscale-alpha pixels are almost fully transparent"
    return ""


def validate_sbb_candidate(png_bytes: bytes) -> SbbCandidateValidation:
    """Validate an SBB candidate before treating a checksum hit as a repair."""

    validation = png.validate_png_structure(png_bytes, require_decodable_idat=True)
    if not validation.ok:
        return SbbCandidateValidation(False, "; ".join(validation.errors), "invalid_structural")

    analysis = idat.analyze_idat_stream(png_bytes, source_kind="candidate")
    if not analysis.supported:
        return SbbCandidateValidation(
            False,
            analysis.reason or "IDAT stream is unsupported",
            "invalid_structural",
        )
    if not analysis.complete or analysis.status != "complete":
        details = analysis.reason or analysis.zlib_error or analysis.status
        return SbbCandidateValidation(
            False,
            "IDAT is not complete: %s" % details,
            "invalid_structural",
        )
    if analysis.expected_size and analysis.decompressed_size != analysis.expected_size:
        return SbbCandidateValidation(
            False,
            "IDAT decompressed size %s does not match expected %s"
            % (analysis.decompressed_size, analysis.expected_size),
            "invalid_structural",
        )
    if analysis.adler_status == "adler_mismatch":
        return SbbCandidateValidation(False, "IDAT Adler32 does not match", "invalid_structural")

    visual_failure = _sbb_visual_sanity_failure(png_bytes)
    if visual_failure:
        return SbbCandidateValidation(False, visual_failure, "valid_but_visual_untrusted")
    return SbbCandidateValidation(True, "")


def _normalize_sbb_rejection_reason(reason: str) -> str:
    text = " ".join(str(reason or "unknown").split())
    return text or "unknown"


def _top_sbb_rejection_reason(scan_state: SmashBruteBrawlScanState) -> str:
    if not scan_state.rejected_reasons:
        return "unknown"
    reason, count = max(
        scan_state.rejected_reasons.items(),
        key=lambda item: (item[1], item[0]),
    )
    return "%s x%s" % (reason, count)


def _sbb_preview_candidate_path(
    runtime: SmashBruteBrawlRuntime,
    png_bytes: bytes,
) -> Path | None:
    if not runtime.progress_path:
        return None
    digest = hashlib.blake2b(png_bytes, digest_size=8).hexdigest()
    folder = Path(runtime.progress_path).parent / "Bruteforce_Previews" / "SBB_Candidates"
    return folder / ("SBB_visual_untrusted_%s.png" % digest)


def _save_sbb_untrusted_preview(
    runtime: SmashBruteBrawlRuntime,
    scan_state: SmashBruteBrawlScanState,
    png_bytes: bytes,
    reason: str,
) -> None:
    if scan_state.untrusted_preview_count >= 32:
        return
    digest = hashlib.blake2b(png_bytes, digest_size=8).hexdigest()
    if digest in scan_state.untrusted_preview_hashes:
        return
    preview_path = _sbb_preview_candidate_path(runtime, png_bytes)
    if preview_path is None:
        return
    try:
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        preview_path.write_bytes(png_bytes)
    except OSError:
        return
    scan_state.untrusted_preview_hashes.add(digest)
    scan_state.untrusted_preview_count += 1
    runtime.side_notes.append(
        "-SmashBruteBrawl preview-only candidate saved: %s (%s)"
        % (preview_path, _normalize_sbb_rejection_reason(reason))
    )


def _emit_sbb_rejection_progress(
    runtime: SmashBruteBrawlRuntime,
    scan_state: SmashBruteBrawlScanState,
    *,
    force: bool = False,
) -> None:
    if scan_state.rejected_candidates <= 0:
        return
    if not force:
        return
    top_reason = _top_sbb_rejection_reason(scan_state)
    reasons = sorted(
        scan_state.rejected_reasons.items(),
        key=lambda item: (-item[1], item[0]),
    )[:3]
    reason_text = ", ".join("%s x%s" % (reason, count) for reason, count in reasons)
    note = (
        "-SmashBruteBrawl rejected %s candidate(s) after strict validation; top reasons: %s."
        % (scan_state.rejected_candidates, reason_text or top_reason)
    )
    if note not in runtime.side_notes:
        runtime.side_notes.append(note)
    scan_state.last_rejection_emit_at = time.monotonic()
    scan_state.last_rejection_emit_count = scan_state.rejected_candidates


def _record_sbb_candidate_rejected(
    runtime: SmashBruteBrawlRuntime,
    scan_state: SmashBruteBrawlScanState,
    reason: str,
    *,
    category: str = "invalid_structural",
    png_bytes: bytes | None = None,
) -> None:
    reason = _normalize_sbb_rejection_reason(reason)
    scan_state.rejected_candidates += 1
    scan_state.rejected_reasons[reason] = scan_state.rejected_reasons.get(reason, 0) + 1
    if not scan_state.first_rejection_reason:
        scan_state.first_rejection_reason = reason
    if category == "valid_but_visual_untrusted" and png_bytes is not None:
        _save_sbb_untrusted_preview(runtime, scan_state, png_bytes, reason)


def _reject_untrusted_internal_sbb_hit(runtime: SmashBruteBrawlRuntime) -> bool:
    if not runtime.suppress_candidate_viewer:
        return False
    return True


def _sbb_scan_terminal_status(scan_state: SmashBruteBrawlScanState) -> str:
    if scan_state.accepted_candidates > 0:
        return "success"
    if scan_state.rejected_candidates > 0:
        return "rejected_hit"
    return "exhausted"


def _reset_scan_state_for_next_sbb_pass(scan_state: SmashBruteBrawlScanState) -> None:
    scan_state.full_new_data = b""
    scan_state.png_bytes = b""
    scan_state.to_brute = ""
    scan_state.diff = ""
    scan_state.eta_seconds = 0
    scan_state.tested_candidates = 0
    scan_state.accepted_candidates = 0
    scan_state.rejected_candidates = 0
    scan_state.outer_index = 0
    scan_state.length = 0
    scan_state.inner_index = 0
    scan_state.byte_position = 0
    scan_state.edit_kind_index = 0
    scan_state.stage = ""
    scan_state.bonus_offset = 0
    scan_state.bonus_value = 0
    scan_state.last_progress_write_at = 0.0
    scan_state.rejected_reasons.clear()
    scan_state.first_rejection_reason = ""
    scan_state.last_rejection_emit_at = 0.0
    scan_state.last_rejection_emit_count = 0
    scan_state.untrusted_preview_count = 0
    scan_state.untrusted_preview_hashes.clear()


def _crc_forge_byte_counts(runtime: SmashBruteBrawlRuntime) -> tuple[int, ...]:
    requested = runtime.crc_forge_bytes
    if requested is None:
        return idat_crc_forge.TARGET_BYTE_COUNTS
    try:
        byte_count = int(requested)
    except (TypeError, ValueError):
        return ()
    return (byte_count,) if byte_count in idat_crc_forge.TARGET_BYTE_COUNTS else ()


def _target_idat_chunk_for_crc_forge(
    context: SmashBruteBrawlContext,
) -> tuple[bytes, png.PngChunk] | None:
    if context.chunk_name != b"IDAT":
        return None
    try:
        source_data = bytes.fromhex(context.data_hex)
    except ValueError:
        return None
    try:
        chunks = [chunk for chunk in png.iter_chunks(source_data) if chunk.chunk_type == b"IDAT"]
    except png.PngFormatError:
        return None
    if not chunks:
        return None

    data_offset = int(context.data_offset)
    data_offset_bytes = data_offset // 2
    for chunk in chunks:
        if chunk.offset + 8 == data_offset_bytes and chunk.length == int(context.chunk_length):
            return source_data, chunk
        if chunk.offset == data_offset_bytes and chunk.length == int(context.chunk_length):
            return source_data, chunk

    bad_crc_chunks = [chunk for chunk in chunks if not chunk.crc_ok]
    if len(bad_crc_chunks) == 1:
        return source_data, bad_crc_chunks[0]
    return source_data, chunks[0]


def _crc_forge_resume_cursor(progress_resume: dict[str, Any] | None) -> dict[str, int] | None:
    if not isinstance(progress_resume, dict):
        return None
    if str(progress_resume.get("backend") or "") != "crc_forge":
        return None
    cursor = progress_resume.get("cursor")
    if not isinstance(cursor, dict):
        return None
    length = _record_int(cursor, "length", 0)
    return {
        "byte_count": length // 2 if length > 0 else 0,
        "window_index": _record_int(cursor, "outer_index", 0),
        "free_index": _record_int(cursor, "inner_index", 0),
        "byte_position": _record_int(cursor, "byte_position", 0),
        "edit_kind_index": _record_int(cursor, "edit_kind_index", 0),
    }


def _sbb_level_for_idat_byte_count(byte_count: int) -> int:
    count = max(1, int(byte_count))
    if count <= 1:
        return 0
    if count <= 2:
        return 1
    if count <= 4:
        return 2
    if count <= 8:
        return 3
    return 4


def _windows_cover_position_space(
    windows: tuple[idat_crc_forge.ForgeWindow, ...],
    position_limit: int,
) -> bool:
    limit = max(0, int(position_limit))
    if limit <= 0:
        return True
    merged = idat_crc_forge._merge_windows(windows)
    cursor = 0
    for window in merged:
        if int(window.start) > cursor:
            return False
        cursor = max(cursor, int(window.end))
        if cursor >= limit:
            return True
    return False


def _crc_forge_covers_broad_sbb_space(
    source_data: bytes,
    target_chunk: png.PngChunk,
    *,
    edit_order: tuple[str, ...],
    byte_counts: tuple[int, ...],
    window_spec: str | None,
) -> bool:
    payload_len = len(target_chunk.data)
    base_windows = (
        idat_crc_forge.parse_window_spec(window_spec, payload_len)
        if str(window_spec or "").strip()
        else idat_crc_forge.ranked_auto_windows(source_data, target_chunk)
    )
    if not base_windows:
        return False
    for byte_count in byte_counts:
        if str(window_spec or "").strip():
            active_edit_order = idat_crc_forge._explicit_window_edit_order(edit_order, byte_count)
        else:
            active_edit_order = idat_crc_forge._expanded_edit_order(source_data, edit_order, byte_count)
        if not active_edit_order:
            return False
        for edit_kind in active_edit_order:
            position_limit = idat_crc_forge.operation_position_limit(payload_len, edit_kind, byte_count)
            op_windows = idat_crc_forge.clamp_windows_for_operation(
                base_windows,
                payload_len,
                edit_kind,
                byte_count,
            )
            if not _windows_cover_position_space(op_windows, position_limit):
                return False
    return True


def _recommended_sbb_level_after_crc_forge(
    runtime: SmashBruteBrawlRuntime,
    context: SmashBruteBrawlContext,
    old_crc: Any,
) -> tuple[int, int] | None:
    if context.chunk_name != b"IDAT":
        return None
    mode = str(runtime.crc_forge_mode or "auto").strip().lower()
    if mode == "off":
        return None
    old_crc_bytes = idat_crc_forge.normalize_old_crc(old_crc)
    if old_crc_bytes is None:
        return None
    target = _target_idat_chunk_for_crc_forge(context)
    if target is None:
        return None
    source_data, target_chunk = target
    edit_order = bruteforce.iter_twobytes_edit_kinds(context.edit_mode, context.chunk_name)
    byte_counts = _crc_forge_byte_counts(runtime)
    auto_plan = idat_crc_forge.focused_auto_plan(
        source_data,
        target_chunk,
        edit_order=edit_order,
        byte_counts=byte_counts,
        explicit_byte_count=runtime.crc_forge_bytes is not None,
        explicit_window=bool(str(runtime.crc_forge_window or "").strip()),
        focus=context.campaign_focus,
        edit_mode=context.edit_mode,
    )
    summary = idat_crc_forge.explain_scan(
        source_data,
        target_chunk,
        edit_order=auto_plan.edit_order,
        byte_counts=auto_plan.byte_counts,
        window_spec=runtime.crc_forge_window,
        mode=mode,
    )
    if not summary.runnable or not summary.byte_counts:
        return None
    if not _crc_forge_covers_broad_sbb_space(
        source_data,
        target_chunk,
        edit_order=auto_plan.edit_order,
        byte_counts=summary.byte_counts,
        window_spec=runtime.crc_forge_window,
    ):
        return None
    byte_count = max(int(value) for value in summary.byte_counts)
    return _sbb_level_for_idat_byte_count(byte_count), byte_count


def _ints_from_text(text: str, *, include_zero: bool) -> tuple[int, ...]:
    values: list[int] = []
    current = ""
    for char in str(text):
        if char.isdigit():
            current += char
            continue
        if current:
            values.append(int(current))
            current = ""
    if current:
        values.append(int(current))
    return tuple(value for value in values if value > 0 or (include_zero and value == 0))


def _positive_ints_from_text(text: str) -> tuple[int, ...]:
    return _ints_from_text(text, include_zero=False)


def _nonnegative_ints_from_text(text: str) -> tuple[int, ...]:
    return _ints_from_text(text, include_zero=True)


def _fallback_input(runtime: SmashBruteBrawlRuntime, prompt: str) -> str:
    if runtime.input_func is None:
        return ""
    try:
        return str(runtime.input_func(prompt)).strip().lower()
    except EOFError:
        runtime.emit("-SBB fallback prompt reached EOF; trusting the detected level.")
        return ""


def _blackfill_fallback_available(context: SmashBruteBrawlContext) -> bool:
    return "FixItFelix partial IDAT blackfill" in str(context.from_error)


def _format_log10_count(log10_count: float) -> str:
    if not math.isfinite(log10_count) or log10_count < 0:
        return "unknown"
    if log10_count < 12:
        return f"{int(10 ** log10_count):,}"
    return "about 1e%s" % int(math.floor(log10_count))


def _format_log10_eta(log10_candidates: float, *, rate: float = SBB_ETA_REFERENCE_RATE) -> str:
    if not math.isfinite(log10_candidates) or log10_candidates < 0:
        return "unknown"
    rate = max(0.001, float(rate))
    log10_seconds = log10_candidates - math.log10(rate)
    if log10_seconds < 8:
        return str(timedelta(seconds=int(10 ** log10_seconds)))
    log10_years = log10_seconds - math.log10(SECONDS_PER_YEAR)
    if log10_years < 6:
        return "about %.0f years" % (10 ** log10_years)
    return "over 1e%s years" % int(math.floor(log10_years))


def _sbb_log10_candidate_estimate(
    context: SmashBruteBrawlContext,
    runtime_plan: bruteforce.BruteForceRuntimePlan,
) -> tuple[float | None, str]:
    if _uses_hermes_direct_window(context, runtime_plan):
        candidate_bytes = _hermes_direct_window_bytes_for_level(context)
        log10_per_position = float(candidate_bytes) * math.log10(256)
        positions = max(1, int(context.chunk_length) - int(candidate_bytes) + 1)
        log10_total = log10_per_position + math.log10(max(1, positions))
        detail = "%s-byte SBB direct window across about %s position(s)" % (
            candidate_bytes,
            f"{positions:,}",
        )
        return log10_total, detail
    length_range = runtime_plan.length_range
    lengths = tuple(range(length_range.min_length, length_range.max_length, length_range.step))
    if not lengths:
        return None, "unknown candidate space"
    max_bytes = max(1, max(lengths) // 2)
    log10_candidates = math.log10(max(1, len(lengths))) + float(max_bytes) * math.log10(256)
    detail = "rough %s length plan(s), up to %s byte(s)" % (len(lengths), max_bytes)
    return log10_candidates, detail


def _emit_sbb_level_warning(
    runtime: SmashBruteBrawlRuntime,
    context: SmashBruteBrawlContext,
    runtime_plan: bruteforce.BruteForceRuntimePlan,
) -> None:
    log10_candidates, detail = _sbb_log10_candidate_estimate(context, runtime_plan)
    if log10_candidates is None:
        if int(context.brute_level) >= SBB_DANGEROUS_LEVEL_WARNING:
            runtime.emit(
                "-WARNING: SBB level %s is unusually deep; ETA will be sampled after the pass starts."
                % int(context.brute_level)
            )
        return
    log10_seconds = log10_candidates - math.log10(max(0.001, SBB_ETA_REFERENCE_RATE))
    is_long = log10_seconds >= math.log10(SBB_LONG_FALLBACK_SECONDS)
    if not is_long and int(context.brute_level) < SBB_DANGEROUS_LEVEL_WARNING:
        return
    runtime.emit(
        "-WARNING: SBB fallback level %s is estimated above one day (%s)."
        % (int(context.brute_level), detail)
    )
    runtime.emit(
        "-SBB fallback ETA estimate: %s candidate combinations; at %.0f candidates/s -> %s."
        % (
            _format_log10_count(log10_candidates),
            SBB_ETA_REFERENCE_RATE,
            _format_log10_eta(log10_candidates),
        )
    )


def _ask_sbb_fallback_decision(
    runtime: SmashBruteBrawlRuntime,
    context: SmashBruteBrawlContext,
    *,
    detected_level: int,
    detected_byte_count: int | None,
) -> SbbFallbackDecision:
    if runtime.input_func is None:
        return SbbFallbackDecision("trust", int(detected_level), detected_byte_count)

    blackfill_available = _blackfill_fallback_available(context)
    runtime.emit("")
    runtime.emit(
        "-Targeted repair pass is handing off to broad SBB at detected level %s."
        % int(detected_level)
    )
    if detected_byte_count:
        runtime.emit("-Detected byte scope: up to %s byte(s)." % int(detected_byte_count))
    if blackfill_available:
        runtime.emit(
            "-SBB fallback choices: 1 trust detection, 2 choose level/bytes, 3 keep blackfill fallback."
        )
    else:
        runtime.emit("-SBB fallback choices: 1 trust detection, 2 choose level/bytes.")
    answer = _fallback_input(runtime, "SBB fallback [1 trust / 2 custom / 3 blackfill] > ")
    if answer in {"", "1", "trust", "auto", "yes", "y", "oui", "o"}:
        return SbbFallbackDecision("trust", int(detected_level), detected_byte_count)
    if answer in {"3", "blackfill", "fallback", "no", "n", "non"}:
        if blackfill_available:
            return SbbFallbackDecision("blackfill")
        runtime.emit("-No blackfill fallback is available here; trusting the detected SBB level.")
        return SbbFallbackDecision("trust", int(detected_level), detected_byte_count)
    if answer not in {"2", "custom", "manual", "manuel", "level", "bytes"}:
        runtime.emit("-Unknown SBB fallback answer; trusting the detected level.")
        return SbbFallbackDecision("trust", int(detected_level), detected_byte_count)

    level_text = _fallback_input(runtime, "Custom SBB level [empty keeps detected] > ")
    byte_text = _fallback_input(runtime, "Bytes concerned [optional, e.g. 1, 1-2, 10] > ")
    level_values = _nonnegative_ints_from_text(level_text)
    byte_values = _positive_ints_from_text(byte_text)
    level = int(level_values[0]) if level_values else int(detected_level)
    byte_count = max(byte_values) if byte_values else detected_byte_count
    if byte_count is not None:
        safe_level = _sbb_level_for_idat_byte_count(int(byte_count))
        if safe_level > level:
            runtime.emit(
                "-Custom byte scope %s needs at least SBB level %s; raising the requested level from %s."
                % (int(byte_count), safe_level, level)
            )
            level = safe_level
    return SbbFallbackDecision("manual", max(0, int(level)), byte_count)


def _run_crc_forge_scan(
    runtime: SmashBruteBrawlRuntime,
    context: SmashBruteBrawlContext,
    scan_state: SmashBruteBrawlScanState,
    old_crc: Any,
    runtime_plan: bruteforce.BruteForceRuntimePlan,
    candidate_space_hash: str,
    progress_resume: dict[str, Any] | None,
) -> CrcForgeScanOutcome | bool:
    mode = str(runtime.crc_forge_mode or "auto").strip().lower()
    if mode == "off":
        return False
    old_crc_bytes = idat_crc_forge.normalize_old_crc(old_crc)
    if old_crc_bytes is None:
        return False
    target = _target_idat_chunk_for_crc_forge(context)
    if target is None:
        return False
    source_data, target_chunk = target
    edit_order = bruteforce.iter_twobytes_edit_kinds(context.edit_mode, context.chunk_name)
    byte_counts = _crc_forge_byte_counts(runtime)
    auto_plan = idat_crc_forge.focused_auto_plan(
        source_data,
        target_chunk,
        edit_order=edit_order,
        byte_counts=byte_counts,
        explicit_byte_count=runtime.crc_forge_bytes is not None,
        explicit_window=bool(str(runtime.crc_forge_window or "").strip()),
        focus=context.campaign_focus,
        edit_mode=context.edit_mode,
    )
    edit_order = auto_plan.edit_order
    byte_counts = auto_plan.byte_counts
    if auto_plan.reason:
        runtime.emit("-HermesProbe CRC-forge auto focus: %s." % auto_plan.reason)
    summary = idat_crc_forge.explain_scan(
        source_data,
        target_chunk,
        edit_order=edit_order,
        byte_counts=byte_counts,
        window_spec=runtime.crc_forge_window,
        mode=mode,
    )
    if not summary.runnable:
        runtime.emit("-HermesProbe CRC-forge targeted IDAT pass skipped: %s" % summary.reason)
        return False

    window_text = _format_crc_forge_windows(summary.windows)
    runtime.emit(
        "-HermesProbe CRC-forge targeted IDAT pass active: windows %s; bytes %s; %s candidate(s)."
        % (
            window_text or "auto",
            _format_crc_forge_byte_counts(summary.byte_counts),
            summary.estimated_candidates,
        )
    )
    resume_cursor = _crc_forge_resume_cursor(progress_resume)
    if auto_plan.reset_resume and resume_cursor is not None:
        runtime.emit(
            "-HermesProbe CRC-forge auto focus changed; ignoring the old CRC-forge cursor for this targeted pass."
        )
        resume_cursor = None
    resume_byte_count = int((resume_cursor or {}).get("byte_count") or 0)
    resume_window_index = int((resume_cursor or {}).get("window_index") or 0)
    resume_free_index = int((resume_cursor or {}).get("free_index") or 0)
    if resume_cursor is not None:
        resume_free_index += 1
    resume_byte_position = int((resume_cursor or {}).get("byte_position") or 0)
    resume_edit_kind_index = int((resume_cursor or {}).get("edit_kind_index") or 0)
    started_at = runtime.now()
    forge_progress_total = max(1, int(summary.estimated_candidates))
    forge_progress_width = max(1, len(str(forge_progress_total)))
    forge_progress = {"last_emit": 0.0}
    runtime.loadingbar(forge_progress_total, forge_progress_width, None, True)
    for _frame in range(12):
        runtime.loadingbar(forge_progress_total, forge_progress_width, 0, False)
        time.sleep(0.08)
    auto_max_seconds = _crc_forge_auto_max_seconds(summary, mode)
    if mode != "force" and auto_max_seconds <= 0:
        runtime.emit(
            "-HermesProbe CRC-forge targeted pass is bounded; no 300s wall-clock cutoff for this pass."
        )

    def crc_forge_progress_callback(
        edit_kind: str,
        byte_count: int,
        _position: int,
        _free_index: int,
        tested: int,
    ) -> None:
        del edit_kind
        scan_state.length = max(scan_state.length, int(byte_count) * 2)
        safe_current = min(forge_progress_total, max(0, int(tested)))
        scan_state.tested_candidates = max(scan_state.tested_candidates, safe_current)
        now = time.monotonic()
        if safe_current < forge_progress_total and now - float(forge_progress["last_emit"]) < 0.12:
            return
        runtime.loadingbar(forge_progress_total, forge_progress_width, safe_current, False)
        forge_progress["last_emit"] = now

    budget_stop_reason = ""
    try:
        for candidate in idat_crc_forge.iter_forge_candidates(
            source_data,
            target_chunk,
            old_crc_bytes,
            edit_order=edit_order,
            byte_counts=byte_counts,
            window_spec=runtime.crc_forge_window,
            mode=mode,
            zlib_prefilter=True,
            progress_callback=crc_forge_progress_callback,
            resume_byte_count=resume_byte_count,
            resume_window_index=resume_window_index,
            resume_free_index=resume_free_index,
            resume_byte_position=resume_byte_position,
            resume_edit_kind_index=resume_edit_kind_index,
            auto_max_seconds=auto_max_seconds,
        ):
            hit = candidate.hit
            scan_state.outer_index = int(hit.outer_index)
            scan_state.length = int(hit.length)
            scan_state.inner_index = int(candidate.free_index)
            scan_state.byte_position = int(hit.byte_position)
            scan_state.edit_kind_index = int(hit.edit_kind_index)
            scan_state.stage = "crc_forge"
            scan_state.bonus_offset = 0
            scan_state.bonus_value = 0
            scan_state.tested_candidates += 1
            runtime.loadingbar(
                forge_progress_total,
                forge_progress_width,
                min(forge_progress_total, max(1, int(scan_state.tested_candidates))),
                False,
            )
            if _apply_parallel_hit(runtime, scan_state, old_crc_bytes, hit):
                save_smash_progress_snapshot(
                    runtime,
                    context,
                    runtime_plan,
                    scan_state,
                    candidate_space_hash=candidate_space_hash,
                    force=True,
                    backend="crc_forge",
                    crc_trusted=True,
                    status="success",
                )
                return CrcForgeScanOutcome(
                    True,
                    tested_candidates=int(scan_state.tested_candidates),
                    estimated_candidates=int(summary.estimated_candidates),
                    last_byte_count=max(0, int(scan_state.length) // 2),
                )
            save_smash_progress_snapshot(
                runtime,
                context,
                runtime_plan,
                scan_state,
                candidate_space_hash=candidate_space_hash,
                backend="crc_forge",
                crc_trusted=True,
                status="running",
            )
    except idat_crc_forge.HermesProbeBudgetExpired as exc:
        budget_stop_reason = exc.reason

    scan_state.eta_seconds = (runtime.now() - started_at).seconds
    save_smash_progress_snapshot(
        runtime,
        context,
        runtime_plan,
        scan_state,
        candidate_space_hash=candidate_space_hash,
        force=True,
        backend="crc_forge",
        crc_trusted=True,
        status=_sbb_scan_terminal_status(scan_state),
    )
    _emit_sbb_rejection_progress(runtime, scan_state, force=True)
    if budget_stop_reason:
        runtime.emit("-HermesProbe CRC-forge targeted IDAT pass stopped: %s" % budget_stop_reason)
    else:
        runtime.emit("-HermesProbe CRC-forge targeted IDAT pass finished without a validated PNG.")
    outcome_tested = int(scan_state.tested_candidates)
    outcome_last_byte_count = max(0, int(scan_state.length) // 2)
    _reset_scan_state_for_next_sbb_pass(scan_state)
    return CrcForgeScanOutcome(
        False,
        budget_stopped=bool(budget_stop_reason),
        tested_candidates=outcome_tested,
        estimated_candidates=int(summary.estimated_candidates),
        last_byte_count=outcome_last_byte_count,
    )


def prepare_runtime_plan(
    runtime: SmashBruteBrawlRuntime,
    context: SmashBruteBrawlContext,
) -> bruteforce.BruteForceRuntimePlan:
    runtime_plan = bruteforce.prepare_runtime_plan(
        context.bf_mode,
        context.chunk_name,
        context.pandora_box,
        runtime.load_spec,
    )
    runtime_plan = bruteforce.apply_idat_brutus_level(
        runtime_plan,
        context.chunk_name,
        context.brute_level,
    )
    if runtime_plan.side_note is not None:
        runtime.side_notes.append(runtime_plan.side_note)
    return runtime_plan


def emit_debug_report_if_needed(
    runtime: SmashBruteBrawlRuntime,
    context: SmashBruteBrawlContext,
    runtime_plan: bruteforce.BruteForceRuntimePlan,
) -> None:
    if context.debug is True:
        length_range = runtime_plan.length_range
        max_iter, _len_iter, chunklen_spec, chunk_format, chunk_data, color_type = (
            bruteforce.load_iteration_spec(
                runtime_plan.mode,
                runtime_plan.struct_indexes,
                None,
                runtime.load_spec,
            )
        )
        emit_debug_report(
            runtime,
            context,
            chunklen_spec=chunklen_spec,
            chunk_format=chunk_format,
            chunk_data=chunk_data,
            max_iter=max_iter,
            maxchunklen=length_range.max_length,
            minchunklen=length_range.min_length,
            step=length_range.step,
        )


def validate_candidate_attempt(
    runtime: SmashBruteBrawlRuntime,
    scan_state: SmashBruteBrawlScanState,
    old_crc: Any,
    attempt: bruteforce.BruteForceCandidateAttempt,
    *,
    loop_index: int,
    brute_bytes: bytes,
    edit_kind: str | None = None,
    bonus: bool = False,
) -> bool:
    scan_state.tested_candidates += 1
    if old_crc and not attempt.old_crc_match:
        return False

    candidate_validation = validate_sbb_candidate(attempt.png_bytes)
    if not candidate_validation.ok:
        _record_sbb_candidate_rejected(
            runtime,
            scan_state,
            candidate_validation.reason,
            category=candidate_validation.category,
            png_bytes=attempt.png_bytes,
        )
        return False
    if not old_crc and _reject_untrusted_internal_sbb_hit(runtime):
        _record_sbb_candidate_rejected(
            runtime,
            scan_state,
            "PNG is structurally valid; visual repair needs a reference/ROI",
            category="valid_but_visual_untrusted",
            png_bytes=attempt.png_bytes,
        )
        return False

    viewer_ok = True
    if not old_crc:
        scan_state.full_new_data = attempt.full_new_data
        scan_state.png_bytes = attempt.png_bytes
        viewer_result = runtime.show_candidate(
            scan_state.png_bytes,
            scan_state.full_new_data,
            loop_index,
            brute_bytes,
        )
        viewer_ok = viewer_result.accepted
        if viewer_result.accepted:
            scan_state.diff = viewer_result.diff

    applied_attempt = bruteforce.apply_validated_candidate_attempt(
        scan_state.state,
        attempt,
        edit_kind,
        bonus=bonus,
        old_crc=old_crc,
        viewer_ok=viewer_ok,
    )
    if applied_attempt is None:
        return False

    scan_state.accepted_candidates += 1
    scan_state.state = applied_attempt.state
    scan_state.full_new_data = applied_attempt.full_new_data
    scan_state.png_bytes = applied_attempt.png_bytes
    return True


def _record_value(record: dict[str, Any], key: str, default: Any = None) -> Any:
    try:
        return record.get(key, default)
    except AttributeError:
        return default


def _record_int(record: dict[str, Any], key: str, default: int = 0) -> int:
    try:
        value = _record_value(record, key, default)
        if value in (None, ""):
            value = default
        return int(value)
    except (TypeError, ValueError):
        return default


def _length_range_record(length_range: bruteforce.BruteForceLengthRange) -> dict[str, int]:
    return {
        "min_length": int(length_range.min_length),
        "max_length": int(length_range.max_length),
        "step": int(length_range.step),
    }


def _smash_parallel_shard_kind(
    context: SmashBruteBrawlContext,
    runtime_plan: bruteforce.BruteForceRuntimePlan,
) -> str:
    if runtime_plan.mode == "TwoBytes":
        return "twobytes"
    if runtime_plan.mode == "Brutus" and context.edit_mode == "Remove" and context.chunk_name == b"IDAT":
        return "remove"
    return "standard"


def _smash_parallel_shard_size(context: SmashBruteBrawlContext, kind: str) -> int:
    level = max(0, int(context.brute_level))
    if kind == "twobytes":
        if level <= 0:
            return smash_backend.SMASH_TWOBYTES_SHARD_BYTE_SIZE
        # Bonus TwoBytes levels can be very expensive per byte position. Worker
        # heartbeats now carry a live cursor, so keep shards small but avoid
        # building millions of one-byte shards before the pass can even run.
        return 64
    if context.bf_mode == "Brutus" and context.chunk_name == b"IDAT":
        return max(512, smash_backend.SMASH_PARALLEL_SHARD_SIZE // (4 ** level))
    return smash_backend.SMASH_PARALLEL_SHARD_SIZE


def _hermes_direct_window_bytes_for_level(context: SmashBruteBrawlContext) -> int:
    level = max(0, int(context.brute_level))
    if level <= 0:
        return 1
    if level == 1:
        return 2
    if level == 2:
        return 4
    return 2**level


def _uses_hermes_direct_window(
    context: SmashBruteBrawlContext,
    runtime_plan: bruteforce.BruteForceRuntimePlan,
) -> bool:
    return runtime_plan.mode == "TwoBytes" and context.chunk_name == b"IDAT"


def _candidate_space_payload(
    context: SmashBruteBrawlContext,
    runtime_plan: bruteforce.BruteForceRuntimePlan,
    *,
    source_hash: str,
) -> dict[str, Any]:
    twobytes_edit_order: list[str] = []
    hermes_window_bytes = 0
    if runtime_plan.mode == "TwoBytes":
        twobytes_edit_order = list(bruteforce.iter_twobytes_edit_kinds(context.edit_mode, context.chunk_name))
        if _uses_hermes_direct_window(context, runtime_plan):
            hermes_window_bytes = _hermes_direct_window_bytes_for_level(context)
    return {
        "algorithm_version": SBB_CANDIDATE_ALGORITHM_VERSION,
        "source_hash": source_hash,
        "chunk_name_hex": context.chunk_name.hex(),
        "chunk_length": int(context.chunk_length),
        "data_offset": int(context.data_offset),
        "edit_mode": context.edit_mode,
        "bf_mode": context.bf_mode,
        "resolved_mode": runtime_plan.mode,
        "struct_indexes": list(runtime_plan.struct_indexes),
        "length_range": _length_range_record(runtime_plan.length_range),
        "brute_crc": bool(context.brute_crc),
        "brute_length": bool(context.brute_length),
        "old_crc": smash_checkpoint.normalize_old_crc(context.old_crc),
        "brute_level": int(context.brute_level),
        "campaign_focus": str(context.campaign_focus or ""),
        "scan_kind": _smash_parallel_shard_kind(context, runtime_plan),
        "twobytes_edit_order": twobytes_edit_order,
        "hermes_window_bytes": hermes_window_bytes,
    }


def _progress_invocation_matches(context: SmashBruteBrawlContext, invocation: dict[str, Any]) -> bool:
    expected = smash_checkpoint.invocation_record(
        file=context.file,
        chunk_name=context.chunk_name,
        chunk_length=context.chunk_length,
        data_offset=context.data_offset,
        from_error=context.from_error,
        edit_mode=context.edit_mode,
        bf_mode=context.bf_mode,
        brute_crc=context.brute_crc,
        brute_length=context.brute_length,
        old_crc=context.old_crc,
        brute_level=context.brute_level,
        campaign_focus=context.campaign_focus,
    )
    comparable_keys = (
        "chunk_name_hex",
        "chunk_length",
        "data_offset",
        "edit_mode",
        "bf_mode",
        "brute_crc",
        "brute_length",
        "old_crc",
        "campaign_focus",
    )
    return all(invocation.get(key, "") == expected.get(key, "") for key in comparable_keys)


def _resolve_resume_record(
    runtime: SmashBruteBrawlRuntime,
    context: SmashBruteBrawlContext,
    runtime_plan: bruteforce.BruteForceRuntimePlan,
    candidate_space_hash: str,
) -> tuple[dict[str, Any] | None, str]:
    record = runtime.resume_record
    if not isinstance(record, dict):
        return None, ""
    if runtime.source_hash and record.get("source_hash") != runtime.source_hash:
        return None, "SmashBruteBrawl checkpoint belongs to another source; starting fresh."
    invocation = record.get("invocation")
    if not isinstance(invocation, dict) or not _progress_invocation_matches(context, invocation):
        return None, "SmashBruteBrawl checkpoint does not match this chunk run; starting fresh."
    plan = record.get("plan")
    if not isinstance(plan, dict):
        return None, "SmashBruteBrawl checkpoint has no search plan; starting fresh."
    checkpoint_status = str(record.get("status") or plan.get("status") or "")
    if checkpoint_status in {"exhausted", "success", "accepted_blackfill", "rejected_hit"}:
        return None, (
            "SmashBruteBrawl checkpoint already marked %s for this pass; trying the next campaign pass."
            % checkpoint_status
        )
    recorded_level = _record_int(invocation, "brute_level", int(context.brute_level))
    current_level = int(context.brute_level)
    recorded_hash = str(plan.get("candidate_space_hash") or "")
    if current_level < recorded_level:
        return None, (
            "SmashBruteBrawl checkpoint was made at BruteLevel %s; current level %s is lower, so I will not resume it."
            % (recorded_level, current_level)
        )
    if recorded_hash == candidate_space_hash:
        if _smash_progress_is_empty_stale(record):
            return None, (
                "SBB fresh pass: %s level %s; stale checkpoint ignored."
                % (context.edit_mode, current_level)
            )
        if _smash_progress_is_exhausted(record):
            return None, (
                "SBB pass already exhausted: %s level %s; trying next planned pass."
                % (context.edit_mode, current_level)
            )
        return record, ""
    if current_level > recorded_level:
        return None, (
            "BruteLevel increased from %s to %s. The search space changed, so SmashBruteBrawl restarts from zero."
            % (recorded_level, current_level)
        )
    return None, "SmashBruteBrawl search space changed; starting fresh."


def _smash_parallel_progress_is_exhausted(record: dict[str, Any]) -> bool:
    plan_record = record.get("plan")
    plan_backend = plan_record.get("backend") if isinstance(plan_record, dict) else ""
    backend = str(record.get("backend") or plan_backend or "")
    if backend != "cpu-parallel":
        return False
    shards = record.get("shards")
    if not isinstance(shards, list) or not shards:
        return False
    counters = record.get("counters") if isinstance(record.get("counters"), dict) else {}
    accepted = _record_int(counters, "accepted_candidates", 0)
    rejected = _record_int(counters, "rejected_candidates", 0)
    if accepted > 0 or rejected > 0:
        return False
    saw_done = False
    for shard in shards:
        if not isinstance(shard, dict):
            continue
        if str(shard.get("status") or "pending") != "done":
            return False
        saw_done = True
    return saw_done


def _smash_progress_is_exhausted(record: dict[str, Any]) -> bool:
    if str(record.get("status") or "") == "exhausted":
        return True
    return _smash_parallel_progress_is_exhausted(record)


def _smash_parallel_progress_is_empty_stale(record: dict[str, Any]) -> bool:
    plan_record = record.get("plan")
    plan_backend = plan_record.get("backend") if isinstance(plan_record, dict) else ""
    backend = str(record.get("backend") or plan_backend or "")
    if backend != "cpu-parallel":
        return False
    counters = record.get("counters")
    if isinstance(counters, dict) and _record_int(counters, "tested_candidates", 0) > 0:
        return False
    shards = record.get("shards")
    if not isinstance(shards, list) or not shards:
        return False
    for shard in shards:
        if not isinstance(shard, dict):
            continue
        if str(shard.get("status") or "pending") != "pending":
            return False
        if _record_int(shard, "tested", 0) > 0:
            return False
        if str(shard.get("kind") or "standard") == "twobytes":
            if _record_int(shard, "next_byte_position", _record_int(shard, "byte_start", 0)) != _record_int(shard, "byte_start", 0):
                return False
            if _record_int(shard, "edit_kind_index", 0) != 0:
                return False
            if str(shard.get("stage") or ""):
                return False
            continue
        if _record_int(shard, "next_inner_index", _record_int(shard, "start_inner_index", 0)) != _record_int(shard, "start_inner_index", 0):
            return False
    return True


def _smash_progress_is_empty_stale(record: dict[str, Any]) -> bool:
    counters = record.get("counters")
    tested = _record_int(counters if isinstance(counters, dict) else {}, "tested_candidates", 0)
    accepted = _record_int(counters if isinstance(counters, dict) else {}, "accepted_candidates", 0)
    rejected = _record_int(counters if isinstance(counters, dict) else {}, "rejected_candidates", 0)
    if tested > 0 or accepted > 0 or rejected > 0:
        return False
    shards = record.get("shards")
    if isinstance(shards, list) and shards:
        return _smash_parallel_progress_is_empty_stale(record)
    cursor = record.get("cursor")
    if isinstance(cursor, dict):
        cursor_keys = (
            "outer_index",
            "inner_index",
            "byte_position",
            "edit_kind_index",
            "bonus_offset",
            "bonus_value",
        )
        if any(_record_int(cursor, key, 0) > 0 for key in cursor_keys):
            return False
        if str(cursor.get("stage") or ""):
            return False
    return str(record.get("status") or "") in {"interrupted", "running", ""}


def _smash_progress_record(
    context: SmashBruteBrawlContext,
    runtime: SmashBruteBrawlRuntime,
    runtime_plan: bruteforce.BruteForceRuntimePlan,
    scan_state: SmashBruteBrawlScanState,
    *,
    candidate_space_hash: str,
    backend: str = "cpu-serial",
    workers: int = 0,
    shard_size: int = 0,
    shards: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None = None,
    crc_trusted: bool | None = None,
    status: str = "running",
) -> dict[str, Any]:
    return {
        "version": smash_checkpoint.SMASH_PROGRESS_VERSION,
        "status": status,
        "source_hash": runtime.source_hash,
        "source_size": int(runtime.source_size),
        "source_path": runtime.source_path,
        "timestamp": time.time(),
        "backend": backend,
        "workers": int(workers),
        "shard_size": int(shard_size),
        "shards": list(shards or ()),
        "candidate_space_hash": candidate_space_hash,
        "crc_trusted": bool(context.old_crc) if crc_trusted is None else bool(crc_trusted),
        "invocation": smash_checkpoint.invocation_record(
            file=context.file,
            chunk_name=context.chunk_name,
            chunk_length=context.chunk_length,
            data_offset=context.data_offset,
            from_error=context.from_error,
            edit_mode=context.edit_mode,
            bf_mode=context.bf_mode,
            brute_crc=context.brute_crc,
            brute_length=context.brute_length,
            old_crc=context.old_crc,
            brute_level=context.brute_level,
            campaign_focus=context.campaign_focus,
        ),
        "plan": {
            "resolved_mode": runtime_plan.mode,
            "struct_indexes": list(runtime_plan.struct_indexes),
            "length_range": _length_range_record(runtime_plan.length_range),
            "candidate_space_hash": candidate_space_hash,
            "backend": backend,
            "workers": int(workers),
            "shard_size": int(shard_size),
            "crc_trusted": bool(context.old_crc) if crc_trusted is None else bool(crc_trusted),
            "status": status,
            "campaign_focus": str(context.campaign_focus or ""),
        },
        "cursor": {
            "outer_index": int(scan_state.outer_index),
            "length": int(scan_state.length),
            "inner_index": int(scan_state.inner_index),
            "byte_position": int(scan_state.byte_position),
            "edit_kind_index": int(scan_state.edit_kind_index),
            "stage": scan_state.stage,
            "bonus_offset": int(scan_state.bonus_offset),
            "bonus_value": int(scan_state.bonus_value),
        },
        "counters": {
            "tested_candidates": int(scan_state.tested_candidates),
            "accepted_candidates": int(scan_state.accepted_candidates),
            "rejected_candidates": int(scan_state.rejected_candidates),
            "rejection_reasons": dict(scan_state.rejected_reasons),
            "first_rejection_reason": scan_state.first_rejection_reason,
            "preview_only_candidates": int(scan_state.untrusted_preview_count),
            "last_displayed_counter": int(scan_state.inner_index),
            "elapsed_seconds": int(scan_state.eta_seconds),
        },
    }


def save_smash_progress_snapshot(
    runtime: SmashBruteBrawlRuntime,
    context: SmashBruteBrawlContext,
    runtime_plan: bruteforce.BruteForceRuntimePlan,
    scan_state: SmashBruteBrawlScanState,
    *,
    candidate_space_hash: str,
    force: bool = False,
    backend: str = "cpu-serial",
    workers: int = 0,
    shard_size: int = 0,
    shards: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None = None,
    crc_trusted: bool | None = None,
    status: str = "running",
) -> None:
    if not runtime.progress_path:
        return
    if not force and not smash_checkpoint.progress_due(
        scan_state.tested_candidates,
        scan_state.last_progress_write_at,
    ):
        return
    smash_checkpoint.atomic_write_json(
        runtime.progress_path,
        _smash_progress_record(
            context,
            runtime,
            runtime_plan,
            scan_state,
            candidate_space_hash=candidate_space_hash,
            backend=backend,
            workers=workers,
            shard_size=shard_size,
            shards=shards,
            crc_trusted=crc_trusted,
            status=status,
        ),
    )
    scan_state.last_progress_write_at = time.monotonic()


def maybe_emit_eta_sample(
    runtime: SmashBruteBrawlRuntime,
    started_at: Any,
    loop_index: int,
    max_iter: int,
) -> None:
    if loop_index != 10:
        return

    runtime.emit("\n\n-BruteForce started at: %s" % started_at)
    elapsed = runtime.now() - started_at
    eta = bruteforce.eta_seconds_after_sample(elapsed, max_iter)
    eta_delta = timedelta(seconds=eta)
    runtime.emit("-Bruteforce can last a max of %s" % str(eta_delta))
    guess = runtime.now() + eta_delta
    runtime.emit("-Bruteforce ending date time is estimated around %s\n" % str(guess))


def apply_crash_decision(scan_state: SmashBruteBrawlScanState, loop_index: int) -> bool:
    if scan_state.crash:
        crash_decision = bruteforce.crash_iteration_decision(loop_index, scan_state.crash)
        scan_state.crash = crash_decision.crash_value
        return crash_decision.skip
    return False


def run_twobytes_scan_step(
    runtime: SmashBruteBrawlRuntime,
    context: SmashBruteBrawlContext,
    scan_state: SmashBruteBrawlScanState,
    old_crc: Any,
    edit_window: bruteforce.BruteForceEditWindow,
    brute_bytes: bytes,
    max_iter: int,
    loop_index: int,
    resume_cursor: dict[str, Any] | None,
    runtime_plan: bruteforce.BruteForceRuntimePlan,
    candidate_space_hash: str,
) -> None:
    def cursor_callback(
        *,
        byte_position: int,
        edit_kind_index: int,
        stage: str,
        bonus_offset: int,
        bonus_value: int,
    ) -> None:
        scan_state.byte_position = int(byte_position)
        scan_state.edit_kind_index = int(edit_kind_index)
        scan_state.stage = stage
        scan_state.bonus_offset = int(bonus_offset)
        scan_state.bonus_value = int(bonus_value)
        save_smash_progress_snapshot(
            runtime,
            context,
            runtime_plan,
            scan_state,
            candidate_space_hash=candidate_space_hash,
        )

    def progress(*, position: int = 0, total: int = 0, bonus: bool = False) -> None:
        if total <= 0:
            runtime.raw_print(
                twobytes_progress_dots_line(
                    "%s/%s " % (loop_index, max_iter),
                    position=position,
                ),
                end="\r",
                flush=True,
            )
            return
        if position not in (0, total - 1) and position % 1024 != 0:
            return
        suffix = " bonus" if bonus else ""
        runtime.raw_print(
            twobytes_progress_dots_line(
                "%s/%s byte %s/%s%s " % (loop_index, max_iter, position + 1, total, suffix),
                position=position,
            ),
            end="\r",
            flush=True,
        )

    bruteforce.run_twobytes_candidate_scan(
        to_brute=scan_state.to_brute,
        brute_bytes=brute_bytes,
        edit_mode=context.edit_mode,
        chunk_name=context.chunk_name,
        brute_level=context.brute_level,
        old_crc=old_crc,
        before=edit_window.before,
        after=edit_window.after,
        get_state=lambda: scan_state.state,
        build_attempt=lambda length_bytes, payload_data, crc_data, before, after: build_attempt(
            context,
            old_crc,
            length_bytes,
            payload_data,
            crc_data,
            before,
            after,
        ),
        validate_attempt=lambda attempt, edit_kind=None, bonus=False: validate_candidate_attempt(
            runtime,
            scan_state,
            old_crc,
            attempt,
            loop_index=loop_index,
            brute_bytes=brute_bytes,
            edit_kind=edit_kind,
            bonus=bonus,
        ),
        progress=progress,
        bonus_message=lambda: runtime.raw_print("-Bingo replace bonus stage"),
        resume_position=_record_int(resume_cursor or {}, "byte_position", 0),
        resume_edit_kind_index=_record_int(resume_cursor or {}, "edit_kind_index", 0),
        resume_stage=str(_record_value(resume_cursor or {}, "stage", "") or ""),
        resume_bonus_offset=_record_int(resume_cursor or {}, "bonus_offset", 0),
        resume_bonus_value=_record_int(resume_cursor or {}, "bonus_value", 0),
        cursor_callback=cursor_callback,
    )


def run_standard_scan_step(
    runtime: SmashBruteBrawlRuntime,
    context: SmashBruteBrawlContext,
    scan_state: SmashBruteBrawlScanState,
    old_crc: Any,
    edit_window: bruteforce.BruteForceEditWindow,
    length_bytes: bytes,
    brute_bytes: bytes,
    max_iter: int,
    len_iter: int,
    loop_index: int,
) -> bool:
    attempt = build_attempt(
        context,
        old_crc,
        length_bytes,
        brute_bytes,
        brute_bytes,
        edit_window.before,
        edit_window.after,
    )
    runtime.loadingbar(max_iter, len_iter, loop_index, False)

    return validate_candidate_attempt(
        runtime,
        scan_state,
        old_crc,
        attempt,
        loop_index=loop_index,
        brute_bytes=brute_bytes,
    )


def run_remove_scan_length(
    runtime: SmashBruteBrawlRuntime,
    context: SmashBruteBrawlContext,
    scan_state: SmashBruteBrawlScanState,
    old_crc: Any,
    runtime_plan: bruteforce.BruteForceRuntimePlan,
    length: int,
    outer_index: int,
    *,
    resume_inner_index: int = 0,
    candidate_space_hash: str,
) -> None:
    started_at = runtime.now()
    edit_window = bruteforce.edit_window(
        context.data_hex,
        context.data_offset,
        context.chunk_length,
        context.edit_mode,
        runtime_plan.mode,
        length,
    )
    scan_state.to_brute = edit_window.to_brute
    scan_state.state = bruteforce.match_state_from_edit_window(edit_window)

    max_iter = bruteforce.remove_candidate_count(edit_window.to_brute, length)
    len_iter = max(1, len(str(max_iter)))
    runtime.loadingbar(max(max_iter, 1), len_iter, None, True)
    if max_iter <= 0:
        return

    for remove_position in range(max(0, int(resume_inner_index)), max_iter):
        scan_state.outer_index = int(outer_index)
        scan_state.length = int(length)
        scan_state.inner_index = int(remove_position)
        scan_state.byte_position = 0
        scan_state.edit_kind_index = 0
        scan_state.stage = ""
        scan_state.bonus_offset = 0
        scan_state.bonus_value = 0
        if apply_crash_decision(scan_state, remove_position):
            continue

        maybe_emit_eta_sample(runtime, started_at, remove_position, max_iter)
        candidate_data = bruteforce.remove_candidate_data(
            edit_window.to_brute,
            remove_position,
            length,
        )
        attempt = build_attempt(
            context,
            old_crc,
            candidate_data.length_bytes,
            candidate_data.data,
            candidate_data.data,
            edit_window.before,
            edit_window.after,
        )
        runtime.loadingbar(max_iter, len_iter, remove_position, False)
        if validate_candidate_attempt(
            runtime,
            scan_state,
            old_crc,
            attempt,
            loop_index=remove_position,
            brute_bytes=candidate_data.removed_bytes,
            edit_kind="remove",
        ):
            save_smash_progress_snapshot(
                runtime,
                context,
                runtime_plan,
                scan_state,
                candidate_space_hash=candidate_space_hash,
                force=True,
                status="success" if scan_state.accepted_candidates > 0 else "running",
            )
            break
        save_smash_progress_snapshot(
            runtime,
            context,
            runtime_plan,
            scan_state,
            candidate_space_hash=candidate_space_hash,
        )

    scan_state.eta_seconds = (runtime.now() - started_at).seconds


def run_scan_length(
    runtime: SmashBruteBrawlRuntime,
    context: SmashBruteBrawlContext,
    scan_state: SmashBruteBrawlScanState,
    old_crc: Any,
    bf_mode: str,
    struct_indexes: tuple[int, ...],
    length: int,
    step: int,
    outer_index: int,
    *,
    resume_inner_index: int = 0,
    resume_cursor: dict[str, Any] | None = None,
    runtime_plan: bruteforce.BruteForceRuntimePlan,
    candidate_space_hash: str,
    length_plan: smash_backend.SmashLengthPlan | None = None,
) -> None:
    if runtime_plan.mode == "Brutus" and context.edit_mode == "Remove" and context.chunk_name == b"IDAT":
        run_remove_scan_length(
            runtime,
            context,
            scan_state,
            old_crc,
            runtime_plan,
            length,
            outer_index,
            resume_inner_index=resume_inner_index,
            candidate_space_hash=candidate_space_hash,
        )
        return

    started_at = runtime.now()
    if length_plan is None:
        iter_nbr = bruteforce.iter_nbr_for_length(length, step, outer_index)
        max_iter, len_iter, _chunklen_spec, chunk_format, chunk_data, color_type = (
            bruteforce.load_iteration_spec(bf_mode, struct_indexes, iter_nbr, runtime.load_spec)
        )
    else:
        length = int(length_plan.length)
        max_iter = int(length_plan.max_iter)
        len_iter = int(length_plan.len_iter)
        chunk_format = tuple(length_plan.chunk_format)
        chunk_data = tuple(length_plan.chunk_data)
        color_type = str(length_plan.color_type)

    runtime.loadingbar(max_iter, len_iter, None, True)

    edit_window = bruteforce.edit_window(
        context.data_hex,
        context.data_offset,
        context.chunk_length,
        context.edit_mode,
        bf_mode,
        length,
    )
    scan_state.to_brute = edit_window.to_brute

    if edit_window.replace_flag or edit_window.insert_flag:
        scan_state.state = bruteforce.match_state_from_edit_window(edit_window)
        length_bytes = edit_window.length_bytes
    else:
        length_bytes = None

    shuffle = runtime.product(chunk_data, color_type)
    for inner_index, candidate in enumerate(shuffle):
        if inner_index < resume_inner_index:
            continue
        scan_state.outer_index = int(outer_index)
        scan_state.length = int(length)
        scan_state.inner_index = int(inner_index)
        scan_state.byte_position = 0
        scan_state.edit_kind_index = 0
        scan_state.stage = ""
        scan_state.bonus_offset = 0
        scan_state.bonus_value = 0
        if apply_crash_decision(scan_state, inner_index):
            continue

        maybe_emit_eta_sample(runtime, started_at, inner_index, max_iter)

        brute_bytes = bruteforce.build_candidate_bytes(
            candidate,
            chunk_format,
            bf_mode,
            struct_indexes=tuple(struct_indexes),
            to_bryte=edit_window.to_bryte,
        )

        if bf_mode == "TwoBytes":
            run_twobytes_scan_step(
                runtime,
                context,
                scan_state,
                old_crc,
                edit_window,
                brute_bytes,
                max_iter,
                inner_index,
                resume_cursor if inner_index == resume_inner_index else None,
                runtime_plan,
                candidate_space_hash,
            )
        elif run_standard_scan_step(
            runtime,
            context,
            scan_state,
            old_crc,
            edit_window,
            length_bytes,
            brute_bytes,
            max_iter,
            len_iter,
            inner_index,
        ):
            save_smash_progress_snapshot(
                runtime,
                context,
                runtime_plan,
                scan_state,
                candidate_space_hash=candidate_space_hash,
                force=True,
            )
            break
        save_smash_progress_snapshot(
            runtime,
            context,
            runtime_plan,
            scan_state,
            candidate_space_hash=candidate_space_hash,
        )

    scan_state.eta_seconds = (runtime.now() - started_at).seconds


def _build_smash_length_plans(
    runtime: SmashBruteBrawlRuntime,
    context: SmashBruteBrawlContext,
    runtime_plan: bruteforce.BruteForceRuntimePlan,
) -> tuple[smash_backend.SmashLengthPlan, ...]:
    if _uses_hermes_direct_window(context, runtime_plan):
        candidate_bytes = _hermes_direct_window_bytes_for_level(context)
        max_iter = 256**candidate_bytes
        byte_values = tuple(range(256))
        return (
            smash_backend.SmashLengthPlan(
                outer_index=0,
                length=candidate_bytes * 2,
                iter_nbr=0,
                max_iter=max_iter,
                len_iter=len(str(max_iter)),
                chunk_format=tuple("B" for _ in range(candidate_bytes)),
                chunk_data=tuple(byte_values for _ in range(candidate_bytes)),
                color_type="color",
            ),
        )

    plans: list[smash_backend.SmashLengthPlan] = []
    length_range = runtime_plan.length_range
    for outer_index, length in enumerate(
        range(length_range.min_length, length_range.max_length, length_range.step)
    ):
        iter_nbr = bruteforce.iter_nbr_for_length(length, length_range.step, outer_index)
        iteration_spec = bruteforce.load_iteration_spec(
            runtime_plan.mode,
            runtime_plan.struct_indexes,
            iter_nbr,
            runtime.load_spec,
        )
        plans.append(
            smash_backend.length_plan_from_iteration_spec(
                outer_index=outer_index,
                length=length,
                iter_nbr=iter_nbr,
                iteration_spec=iteration_spec,
            )
        )
    return tuple(plans)


def _build_smash_candidate_plan(
    context: SmashBruteBrawlContext,
    runtime_plan: bruteforce.BruteForceRuntimePlan,
    old_crc: Any,
    candidate_space_hash: str,
    length_plans: tuple[smash_backend.SmashLengthPlan, ...],
) -> smash_backend.SmashCandidatePlan:
    return smash_backend.SmashCandidatePlan(
        chunk_name=context.chunk_name,
        chunk_length=int(context.chunk_length),
        data_offset=int(context.data_offset),
        data_hex=context.data_hex,
        edit_mode=context.edit_mode,
        bf_mode=runtime_plan.mode,
        brute_level=int(context.brute_level),
        brute_crc=bool(context.brute_crc),
        brute_length=bool(context.brute_length),
        old_crc=old_crc,
        struct_indexes=tuple(runtime_plan.struct_indexes),
        candidate_space_hash=candidate_space_hash,
        crc_trusted=bool(old_crc),
        lengths=length_plans,
    )


def _initial_parallel_shards(
    length_plans: tuple[smash_backend.SmashLengthPlan, ...],
    *,
    shard_size: int,
    resume_outer_index: int,
    resume_inner_index: int,
) -> list[smash_backend.SmashShard]:
    shards: list[smash_backend.SmashShard] = []
    shard_id = 0
    for length_index, length_plan in enumerate(length_plans):
        if length_plan.outer_index < resume_outer_index:
            continue
        start = resume_inner_index if length_plan.outer_index == resume_outer_index else 0
        while start < length_plan.max_iter:
            end = min(length_plan.max_iter, start + shard_size)
            shards.append(
                smash_backend.SmashShard(
                    shard_id=shard_id,
                    length_plan_index=length_index,
                    start_inner_index=start,
                    end_inner_index=end,
                )
            )
            shard_id += 1
            start = end
    return shards


def _resume_parallel_shards(
    progress_resume: dict[str, Any] | None,
    length_plans: tuple[smash_backend.SmashLengthPlan, ...],
    *,
    shard_size: int,
    resume_outer_index: int,
    resume_inner_index: int,
    plan: smash_backend.SmashCandidatePlan | None = None,
    resume_cursor: dict[str, Any] | None = None,
    kind: str = "standard",
) -> list[smash_backend.SmashShard]:
    if isinstance(progress_resume, dict):
        saved_shards = progress_resume.get("shards")
        if isinstance(saved_shards, list) and saved_shards:
            shards = []
            saw_matching_shard = False
            for saved in saved_shards:
                if not isinstance(saved, dict):
                    continue
                saved_kind = str(saved.get("kind") or "standard")
                if saved_kind != kind:
                    continue
                saw_matching_shard = True
                if saved.get("status") == "done":
                    continue
                try:
                    shard = smash_backend.shard_from_record(saved)
                except (TypeError, ValueError):
                    continue
                if (
                    0 <= shard.length_plan_index < len(length_plans)
                    and shard.start_inner_index < shard.end_inner_index
                ):
                    shards.append(shard)
            if saw_matching_shard:
                return sorted(shards, key=lambda shard: shard.shard_id)
    if kind == "twobytes" and plan is not None:
        cursor = resume_cursor or {}
        return smash_backend.build_twobytes_shards(
            plan,
            shard_size=shard_size,
            resume_outer_index=resume_outer_index,
            resume_inner_index=resume_inner_index,
            resume_byte_position=_record_int(cursor, "byte_position", 0),
            resume_edit_kind_index=_record_int(cursor, "edit_kind_index", 0),
            resume_stage=str(_record_value(cursor, "stage", "") or ""),
            resume_bonus_offset=_record_int(cursor, "bonus_offset", 0),
            resume_bonus_value=_record_int(cursor, "bonus_value", 0),
        )
    if kind == "remove" and plan is not None:
        return smash_backend.build_remove_shards(
            plan,
            shard_size=shard_size,
            resume_outer_index=resume_outer_index,
            resume_inner_index=resume_inner_index,
        )
    return _initial_parallel_shards(
        length_plans,
        shard_size=shard_size,
        resume_outer_index=resume_outer_index,
        resume_inner_index=resume_inner_index,
    )


def _parallel_shard_records(
    shards: list[smash_backend.SmashShard],
    results: dict[int, smash_backend.SmashShardResult],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for shard in shards:
        result = results.get(shard.shard_id)
        records.append(smash_backend.shard_record(shard, result))
    return records


def _estimate_parallel_remaining_candidates(
    plan: smash_backend.SmashCandidatePlan,
    shards: list[smash_backend.SmashShard],
) -> int:
    remaining = 0
    edit_kind_counts: dict[tuple[int, int], tuple[str, ...]] = {}

    def bonus_count_for_edit(edit_kind: str, *, payload_bytes: int, brute_bytes_len: int) -> int:
        if plan.brute_level <= 0:
            return 0
        if edit_kind == "insert":
            candidate_len = payload_bytes + brute_bytes_len
        elif edit_kind == "remove":
            candidate_len = payload_bytes - brute_bytes_len
        else:
            candidate_len = payload_bytes
        return max(0, candidate_len - brute_bytes_len) * 256

    def remaining_bonus_from_cursor(
        total_bonus: int,
        *,
        bonus_offset: int,
        bonus_value: int,
    ) -> int:
        consumed = max(0, int(bonus_offset) // 2) * 256 + max(0, int(bonus_value))
        return max(0, total_bonus - consumed)

    for shard in shards:
        if shard.kind != "twobytes":
            remaining += max(0, int(shard.end_inner_index) - int(shard.start_inner_index))
            continue
        length_plan = plan.lengths[shard.length_plan_index]
        cache_key = (shard.length_plan_index, int(shard.inner_index or shard.start_inner_index))
        edit_kinds = edit_kind_counts.get(cache_key)
        if edit_kinds is None:
            edit_kinds = bruteforce.iter_twobytes_edit_kinds(plan.edit_mode, plan.chunk_name)
            edit_kind_counts[cache_key] = edit_kinds
        edit_window = bruteforce.edit_window(
            plan.data_hex,
            plan.data_offset,
            plan.chunk_length,
            plan.edit_mode,
            plan.bf_mode,
            length_plan.length,
        )
        brute_bytes = smash_backend._twobytes_candidate_bytes(plan, length_plan, int(shard.inner_index or shard.start_inner_index), edit_window)
        brute_bytes_len = len(brute_bytes or b"")
        payload_bytes = len(edit_window.to_brute) // 2
        first_position = max(int(shard.byte_start), int(shard.next_byte_position or shard.byte_start))
        shard_remaining = 0
        for position in range(first_position, int(shard.byte_end)):
            start_edit_kind_index = int(shard.edit_kind_index or 0) if position == first_position else 0
            for edit_kind_index, edit_kind in enumerate(edit_kinds):
                if edit_kind_index < start_edit_kind_index:
                    continue
                shard_remaining += 1
                bonus_remaining = bonus_count_for_edit(
                    edit_kind,
                    payload_bytes=payload_bytes,
                    brute_bytes_len=brute_bytes_len,
                )
                if (
                    position == first_position
                    and edit_kind_index == start_edit_kind_index
                    and str(shard.stage or "") == "bonus"
                ):
                    bonus_remaining = remaining_bonus_from_cursor(
                        bonus_remaining,
                        bonus_offset=int(shard.bonus_offset),
                        bonus_value=int(shard.bonus_value),
                    )
                shard_remaining += bonus_remaining
        remaining += shard_remaining
    return max(0, remaining)


def _apply_parallel_hit(
    runtime: SmashBruteBrawlRuntime,
    scan_state: SmashBruteBrawlScanState,
    old_crc: Any,
    hit: smash_backend.SmashCandidateHit,
) -> bool:
    attempt = bruteforce.BruteForceCandidateAttempt(
        checksum=hit.checksum,
        full_new_data=hit.full_new_data,
        png_bytes=hit.png_bytes,
        old_crc_match=hit.old_crc_match,
    )
    if old_crc and not attempt.old_crc_match:
        return False
    candidate_validation = validate_sbb_candidate(attempt.png_bytes)
    if not candidate_validation.ok:
        _record_sbb_candidate_rejected(
            runtime,
            scan_state,
            candidate_validation.reason,
            category=candidate_validation.category,
            png_bytes=attempt.png_bytes,
        )
        return False
    if not old_crc and _reject_untrusted_internal_sbb_hit(runtime):
        _record_sbb_candidate_rejected(
            runtime,
            scan_state,
            "PNG is structurally valid; visual repair needs a reference/ROI",
            category="valid_but_visual_untrusted",
            png_bytes=attempt.png_bytes,
        )
        return False

    viewer_ok = True
    if not old_crc:
        scan_state.full_new_data = attempt.full_new_data
        scan_state.png_bytes = attempt.png_bytes
        viewer_result = runtime.show_candidate(
            scan_state.png_bytes,
            scan_state.full_new_data,
            hit.inner_index,
            hit.brute_bytes,
        )
        viewer_ok = viewer_result.accepted
        if viewer_result.accepted:
            scan_state.diff = viewer_result.diff
    applied_attempt = bruteforce.apply_validated_candidate_attempt(
        scan_state.state,
        attempt,
        hit.edit_kind,
        bonus=hit.bonus,
        old_crc=old_crc,
        viewer_ok=viewer_ok,
    )
    if applied_attempt is None:
        return False
    scan_state.accepted_candidates += 1
    scan_state.state = applied_attempt.state
    scan_state.full_new_data = applied_attempt.full_new_data
    scan_state.png_bytes = applied_attempt.png_bytes
    return True


def _save_parallel_progress(
    runtime: SmashBruteBrawlRuntime,
    context: SmashBruteBrawlContext,
    runtime_plan: bruteforce.BruteForceRuntimePlan,
    scan_state: SmashBruteBrawlScanState,
    *,
    candidate_space_hash: str,
    worker_count: int,
    shard_size: int,
    shards: list[smash_backend.SmashShard],
    results: dict[int, smash_backend.SmashShardResult],
    tested_floor: int = 0,
    force: bool = False,
    status: str = "running",
) -> None:
    if results:
        confirmed_tested = int(tested_floor) + sum(int(result.tested) for result in results.values())
        if confirmed_tested > scan_state.tested_candidates:
            scan_state.tested_candidates = confirmed_tested
    save_smash_progress_snapshot(
        runtime,
        context,
        runtime_plan,
        scan_state,
        candidate_space_hash=candidate_space_hash,
        force=force,
        backend="cpu-parallel",
        workers=worker_count,
        shard_size=shard_size,
        shards=_parallel_shard_records(shards, results),
        crc_trusted=bool(context.old_crc),
        status=status,
    )


def _close_smash_parallel_progress_queue(progress_queue: Any) -> None:
    if progress_queue is None:
        return
    try:
        while True:
            progress_queue.get_nowait()
    except Exception:
        pass
    cancel_join_thread = getattr(progress_queue, "cancel_join_thread", None)
    if callable(cancel_join_thread):
        try:
            cancel_join_thread()
        except Exception:
            pass
    close = getattr(progress_queue, "close", None)
    if callable(close):
        try:
            close()
        except Exception:
            pass


def _shutdown_smash_parallel_executor(
    executor: concurrent.futures.ProcessPoolExecutor,
    *,
    futures: dict[concurrent.futures.Future, Any] | None = None,
    progress_queue: Any = None,
    stop_event: Any = None,
    grace_seconds: float = 2.0,
) -> None:
    set_stop = getattr(stop_event, "set", None)
    if callable(set_stop):
        try:
            set_stop()
        except Exception:
            pass
    pending_futures = tuple(futures) if futures else ()
    if pending_futures:
        try:
            _done, pending = concurrent.futures.wait(
                pending_futures,
                timeout=max(0.0, float(grace_seconds)),
            )
        except Exception:
            pending = pending_futures
        for future in pending:
            cancel = getattr(future, "cancel", None)
            if callable(cancel):
                try:
                    cancel()
                except Exception:
                    pass
    processes = getattr(executor, "_processes", None)
    try:
        executor.shutdown(wait=False, cancel_futures=True)
    except TypeError:
        executor.shutdown(wait=False)
    if isinstance(processes, dict):
        deadline = time.monotonic() + max(0.0, float(grace_seconds))
        for process in tuple(processes.values()):
            alive = True
            poll = getattr(process, "poll", None)
            is_alive = getattr(process, "is_alive", None)
            if callable(poll):
                try:
                    alive = poll() is None
                except Exception:
                    alive = True
            elif callable(is_alive):
                try:
                    alive = bool(is_alive())
                except Exception:
                    alive = True
            if alive:
                terminate = getattr(process, "terminate", None)
                if callable(terminate):
                    try:
                        terminate()
                    except Exception:
                        pass
        for process in tuple(processes.values()):
            join = getattr(process, "join", None)
            if callable(join):
                try:
                    join(max(0.0, deadline - time.monotonic()))
                except Exception:
                    pass
    _close_smash_parallel_progress_queue(progress_queue)


def _run_gpu_scan(
    runtime: SmashBruteBrawlRuntime,
    context: SmashBruteBrawlContext,
    scan_state: SmashBruteBrawlScanState,
    old_crc: Any,
    runtime_plan: bruteforce.BruteForceRuntimePlan,
    candidate_space_hash: str,
    progress_resume: dict[str, Any] | None,
    resume_outer_index: int,
    resume_inner_index: int,
) -> bool:
    if not runtime.gpu_config.enabled:
        return False
    length_plans = _build_smash_length_plans(runtime, context, runtime_plan)
    plan = _build_smash_candidate_plan(
        context,
        runtime_plan,
        old_crc,
        candidate_space_hash,
        length_plans,
    )
    gpu_tested_floor = max(0, int(scan_state.tested_candidates))
    gpu_progress = {
        "started": False,
        "last_emit": 0.0,
        "total": 0,
        "width": 1,
        "status_width": 0,
    }

    def emit_gpu_status(reason: str) -> None:
        line = "-GPU requested: %s" % reason
        if not gpu_progress["started"]:
            runtime.emit(line)
            return
        width = max(int(gpu_progress["status_width"]), len(line))
        gpu_progress["status_width"] = width
        runtime.raw_print("\r%s%s" % (line, " " * max(0, width - len(line))), end="\r", flush=True)

    decision = smash_opengl_backend.explain(plan, runtime.gpu_config)
    if not decision.runnable:
        emit_gpu_status(decision.reason)
        return False
    emit_gpu_status(decision.reason)

    def apply_gpu_cursor(cursor: Any) -> None:
        scan_state.outer_index = 0
        scan_state.inner_index = int(getattr(cursor, "inner_index", scan_state.inner_index))
        scan_state.byte_position = int(getattr(cursor, "byte_position", scan_state.byte_position))
        scan_state.edit_kind_index = int(getattr(cursor, "edit_kind_index", scan_state.edit_kind_index))
        scan_state.stage = str(getattr(cursor, "stage", "direct") or "direct")
        scan_state.bonus_offset = 0
        scan_state.bonus_value = 0

    def progress_resume_with_cursor(
        base_resume: dict[str, Any] | None,
        cursor: Any,
    ) -> dict[str, Any]:
        record = dict(base_resume or {})
        record["cursor"] = {
            "outer_index": 0,
            "inner_index": int(getattr(cursor, "inner_index", 0)),
            "byte_position": int(getattr(cursor, "byte_position", 0)),
            "edit_kind_index": int(getattr(cursor, "edit_kind_index", 0)),
            "stage": str(getattr(cursor, "stage", "direct") or "direct"),
            "bonus_offset": 0,
            "bonus_value": 0,
        }
        return record

    def gpu_progress_callback(tested: int, total: int, *, cursor: Any = None) -> None:
        if cursor is not None:
            apply_gpu_cursor(cursor)
        safe_total = max(1, gpu_tested_floor + max(0, int(total)))
        safe_current = min(safe_total, gpu_tested_floor + max(0, int(tested)))
        scan_state.tested_candidates = max(scan_state.tested_candidates, safe_current)
        if not gpu_progress["started"]:
            gpu_progress["total"] = safe_total
            gpu_progress["width"] = max(1, len(str(safe_total)))
            runtime.loadingbar(safe_total, int(gpu_progress["width"]), None, True)
            gpu_progress["started"] = True
        now = time.monotonic()
        if safe_current < safe_total and now - float(gpu_progress["last_emit"]) < 0.5:
            return
        runtime.loadingbar(
            int(gpu_progress["total"]) or safe_total,
            int(gpu_progress["width"]),
            safe_current,
            False,
        )
        gpu_progress["last_emit"] = now
        save_smash_progress_snapshot(
            runtime,
            context,
            runtime_plan,
            scan_state,
            candidate_space_hash=candidate_space_hash,
            backend="opengl",
            workers=0,
            shard_size=0,
            shards=[],
            crc_trusted=bool(context.old_crc),
            status="running",
        )

    current_progress_resume = progress_resume
    current_resume_outer_index = resume_outer_index
    current_resume_inner_index = resume_inner_index

    while True:
        gpu_tested_floor = max(0, int(scan_state.tested_candidates))
        try:
            gpu_result = smash_opengl_backend.run_scan(
                runtime,
                context,
                scan_state,
                old_crc,
                runtime_plan,
                plan,
                candidate_space_hash,
                current_progress_resume,
                current_resume_outer_index,
                current_resume_inner_index,
                progress_callback=gpu_progress_callback,
            )
        except KeyboardInterrupt as exc:
            save_smash_progress_snapshot(
                runtime,
                context,
                runtime_plan,
                scan_state,
                candidate_space_hash=candidate_space_hash,
                force=True,
                backend="opengl",
                workers=0,
                shard_size=0,
                shards=[],
                crc_trusted=bool(context.old_crc),
                status="interrupted",
            )
            raise smash_checkpoint.SmashBruteBrawlInterrupted(runtime.progress_path) from exc
        except NotImplementedError as exc:
            reason = str(exc) or "SBB OpenGL kernel is not implemented yet"
            emit_gpu_status("%s; using CPU workers." % reason)
            return False
        except Exception as exc:
            emit_gpu_status("OpenGL SBB path failed (%s); using CPU workers." % exc)
            return False

        if isinstance(gpu_result, bool):
            return gpu_result

        hits = tuple(getattr(gpu_result, "hits", ()) or ())
        tested = int(getattr(gpu_result, "tested", 0) or 0)
        truncated = bool(getattr(gpu_result, "truncated", False))
        covered_full_cpu_space = bool(getattr(gpu_result, "covered_full_cpu_space", True))
        next_cursor = getattr(gpu_result, "next_cursor", None)
        if next_cursor is not None:
            apply_gpu_cursor(next_cursor)
        if tested > 0:
            scan_state.tested_candidates = max(scan_state.tested_candidates, gpu_tested_floor + tested)
        if not hits:
            if truncated:
                scan_state.tested_candidates = gpu_tested_floor
                emit_gpu_status("OpenGL pass stopped before completion; using CPU workers.")
                save_smash_progress_snapshot(
                    runtime,
                    context,
                    runtime_plan,
                    scan_state,
                    candidate_space_hash=candidate_space_hash,
                    force=True,
                    backend="opengl",
                    workers=0,
                    shard_size=0,
                    shards=[],
                    crc_trusted=bool(context.old_crc),
                    status="running",
                )
                return False
            if not covered_full_cpu_space:
                emit_gpu_status("OpenGL direct pass exhausted; continuing with CPU bonus stages.")
                save_smash_progress_snapshot(
                    runtime,
                    context,
                    runtime_plan,
                    scan_state,
                    candidate_space_hash=candidate_space_hash,
                    force=True,
                    backend="opengl",
                    workers=0,
                    shard_size=0,
                    shards=[],
                    crc_trusted=bool(context.old_crc),
                    status="running",
                )
                return False
            save_smash_progress_snapshot(
                runtime,
                context,
                runtime_plan,
                scan_state,
                candidate_space_hash=candidate_space_hash,
                force=True,
                backend="opengl",
                workers=0,
                shard_size=0,
                shards=[],
                crc_trusted=bool(context.old_crc),
                status="exhausted",
            )
            return True

        accepted = False
        for hit in hits:
            scan_state.outer_index = int(hit.outer_index)
            scan_state.length = int(hit.length)
            scan_state.inner_index = int(hit.inner_index)
            scan_state.byte_position = int(getattr(hit, "byte_position", 0))
            scan_state.edit_kind_index = int(getattr(hit, "edit_kind_index", 0))
            scan_state.stage = str(getattr(hit, "stage", "") or "")
            scan_state.bonus_offset = 0
            scan_state.bonus_value = 0
            if _apply_parallel_hit(runtime, scan_state, old_crc, hit):
                accepted = True
                break

        if accepted:
            save_smash_progress_snapshot(
                runtime,
                context,
                runtime_plan,
                scan_state,
                candidate_space_hash=candidate_space_hash,
                force=True,
                backend="opengl",
                workers=0,
                shard_size=0,
                shards=[],
                crc_trusted=bool(context.old_crc),
                status="success",
            )
            return True
        if truncated:
            emit_gpu_status("OpenGL hit cap reached before a valid candidate; continuing the campaign.")
            save_smash_progress_snapshot(
                runtime,
                context,
                runtime_plan,
                scan_state,
                candidate_space_hash=candidate_space_hash,
                force=True,
                backend="opengl",
                workers=0,
                shard_size=0,
                shards=[],
                crc_trusted=bool(context.old_crc),
                status=_sbb_scan_terminal_status(scan_state),
            )
            return True
        if next_cursor is not None:
            apply_gpu_cursor(next_cursor)
            save_smash_progress_snapshot(
                runtime,
                context,
                runtime_plan,
                scan_state,
                candidate_space_hash=candidate_space_hash,
                force=True,
                backend="opengl",
                workers=0,
                shard_size=0,
                shards=[],
                crc_trusted=bool(context.old_crc),
                status="running",
            )
            current_progress_resume = progress_resume_with_cursor(current_progress_resume, next_cursor)
            current_resume_outer_index = 0
            current_resume_inner_index = int(getattr(next_cursor, "inner_index", 0))
            emit_gpu_status("OpenGL CRC hit rejected by validation; resuming direct scan.")
            continue
        save_smash_progress_snapshot(
            runtime,
            context,
            runtime_plan,
            scan_state,
            candidate_space_hash=candidate_space_hash,
            force=True,
            backend="opengl",
            workers=0,
            shard_size=0,
            shards=[],
            crc_trusted=bool(context.old_crc),
            status=_sbb_scan_terminal_status(scan_state),
        )
        return True


def _run_parallel_scan(
    runtime: SmashBruteBrawlRuntime,
    context: SmashBruteBrawlContext,
    scan_state: SmashBruteBrawlScanState,
    old_crc: Any,
    runtime_plan: bruteforce.BruteForceRuntimePlan,
    candidate_space_hash: str,
    progress_resume: dict[str, Any] | None,
    resume_outer_index: int,
    resume_inner_index: int,
) -> bool:
    worker_count = smash_backend.resolve_smash_worker_count(runtime.smash_workers)
    if worker_count <= 1:
        return False
    length_plans = _build_smash_length_plans(runtime, context, runtime_plan)
    plan = _build_smash_candidate_plan(
        context,
        runtime_plan,
        old_crc,
        candidate_space_hash,
        length_plans,
    )
    backend = smash_backend.SmashParallelBackend()
    if not backend.supports(plan):
        return False
    shard_kind = _smash_parallel_shard_kind(context, runtime_plan)
    shard_size = _smash_parallel_shard_size(context, shard_kind)
    shards = _resume_parallel_shards(
        progress_resume,
        length_plans,
        shard_size=shard_size,
        resume_outer_index=resume_outer_index,
        resume_inner_index=resume_inner_index,
        plan=plan,
        resume_cursor=progress_resume.get("cursor") if isinstance(progress_resume, dict) else None,
        kind=shard_kind,
    )
    if not shards:
        _save_parallel_progress(
            runtime,
            context,
            runtime_plan,
            scan_state,
            candidate_space_hash=candidate_space_hash,
            worker_count=worker_count,
            shard_size=shard_size,
            shards=[],
            results={},
            force=True,
            status="exhausted",
        )
        return True

    runtime.emit("-SmashBruteBrawl will use %s CPU workers." % worker_count)
    scan_state.last_progress_write_at = time.monotonic()
    started_at = runtime.now()
    remaining_candidates = _estimate_parallel_remaining_candidates(plan, shards)
    progress_total = max(scan_state.tested_candidates + remaining_candidates, 1)
    progress_width = max(1, len(str(progress_total)))
    runtime.loadingbar(progress_total, progress_width, None, True)
    completed_results: dict[int, smash_backend.SmashShardResult] = {}
    finished_results: dict[int, smash_backend.SmashShardResult] = {}
    result_buffer: dict[int, smash_backend.SmashShardResult] = {}
    worker_error_counts: dict[str, int] = {}
    shard_by_id = {shard.shard_id: shard for shard in shards}
    shard_order = [shard.shard_id for shard in shards]
    next_order_index = 0
    accepted = False
    manager = multiprocessing.Manager()
    stop_event = manager.Event()
    progress_queue = manager.Queue()
    last_worker_heartbeat_at = 0.0
    pending: dict[concurrent.futures.Future, smash_backend.SmashShard] = {}
    live_results: dict[int, smash_backend.SmashShardResult] = {}
    executor: concurrent.futures.ProcessPoolExecutor | None = None
    executor_shutdown = False
    manager_shutdown = False
    previous_sigint_handler: Any = None
    sigint_handler_installed = False
    interrupt_requested = False
    interrupt_announced = False
    parallel_tested_floor = int(scan_state.tested_candidates)

    def live_checkpoint_results() -> dict[int, smash_backend.SmashShardResult]:
        merged = dict(finished_results)
        for shard_id, result in live_results.items():
            if shard_id not in merged:
                merged[shard_id] = result
        return merged

    def drain_worker_progress() -> bool:
        drained = False
        while True:
            try:
                item = progress_queue.get_nowait()
            except Exception:
                break
            if not isinstance(item, dict):
                continue
            shard_id = _record_int(item, "shard_id", -1)
            shard = shard_by_id.get(shard_id)
            if shard is None or shard_id in finished_results:
                continue
            tested = _record_int(item, "tested", 0)
            previous = live_results.get(shard_id)
            if previous is not None and tested <= previous.tested:
                continue
            live_results[shard_id] = smash_backend.SmashShardResult(
                shard=shard,
                tested=tested,
                next_inner_index=_record_int(item, "next_inner_index", shard.start_inner_index),
                hits=(),
                stopped=True,
                next_byte_position=_record_int(item, "next_byte_position", shard.next_byte_position),
                edit_kind_index=_record_int(item, "edit_kind_index", shard.edit_kind_index),
                stage=str(item.get("stage") or ""),
                bonus_offset=_record_int(item, "bonus_offset", 0),
                bonus_value=_record_int(item, "bonus_value", 0),
            )
            drained = True
        return drained

    def emit_worker_heartbeat(*, force: bool = False) -> None:
        nonlocal last_worker_heartbeat_at
        now = time.monotonic()
        if not force and now - last_worker_heartbeat_at < 0.5:
            return
        drain_worker_progress()
        finished_tested = sum(result.tested for result in finished_results.values())
        live_tested = sum(
            result.tested
            for shard_id, result in live_results.items()
            if shard_id not in finished_results
        )
        current = min(progress_total, parallel_tested_floor + finished_tested + live_tested)
        runtime.loadingbar(progress_total, progress_width, current, False)
        last_worker_heartbeat_at = now

    def handle_ready_results() -> bool:
        nonlocal next_order_index, accepted
        advanced = False
        while next_order_index < len(shard_order):
            shard_id = shard_order[next_order_index]
            result = result_buffer.get(shard_id)
            if result is None:
                break
            advanced = True
            result_buffer.pop(shard_id)
            completed_results[shard_id] = result
            shard = shard_by_id[shard_id]
            length_plan = length_plans[shard.length_plan_index]
            edit_window = bruteforce.edit_window(
                context.data_hex,
                context.data_offset,
                context.chunk_length,
                context.edit_mode,
                runtime_plan.mode,
                length_plan.length,
            )
            scan_state.to_brute = edit_window.to_brute
            if shard.kind != "twobytes" and (
                edit_window.replace_flag or edit_window.insert_flag or edit_window.remove_flag
            ):
                scan_state.state = bruteforce.match_state_from_edit_window(edit_window)
            scan_state.outer_index = length_plan.outer_index
            scan_state.length = length_plan.length
            scan_state.inner_index = max(shard.start_inner_index, result.next_inner_index - 1)
            if shard.kind == "twobytes":
                scan_state.inner_index = int(shard.inner_index if shard.inner_index is not None else shard.start_inner_index)
                scan_state.byte_position = int(result.next_byte_position)
                scan_state.edit_kind_index = int(result.edit_kind_index)
                scan_state.stage = result.stage
                scan_state.bonus_offset = int(result.bonus_offset)
                scan_state.bonus_value = int(result.bonus_value)
            scan_state.tested_candidates += result.tested
            if result.error:
                previous_error_count = worker_error_counts.get(result.error, 0)
                worker_error_counts[result.error] = previous_error_count + 1
                if previous_error_count == 0:
                    runtime.emit("-SmashBruteBrawl worker shard %s failed: %s" % (shard_id, result.error))
            emit_worker_heartbeat(force=True)
            for hit in result.hits:
                if _apply_parallel_hit(runtime, scan_state, old_crc, hit):
                    accepted = True
                    stop_event.set()
                    break
            _save_parallel_progress(
                runtime,
                context,
                runtime_plan,
                scan_state,
                candidate_space_hash=candidate_space_hash,
                worker_count=worker_count,
                shard_size=shard_size,
                shards=shards,
                results=finished_results,
                tested_floor=parallel_tested_floor,
            )
            next_order_index += 1
            if accepted:
                break
        return advanced

    def harvest_finished_futures() -> None:
        for future in list(pending):
            if not future.done():
                continue
            shard = pending.pop(future)
            try:
                result = future.result()
            except Exception as exc:
                result = smash_backend.SmashShardResult(
                    shard=shard,
                    tested=0,
                    next_inner_index=shard.start_inner_index,
                    error=str(exc),
                    next_byte_position=shard.next_byte_position,
                    edit_kind_index=shard.edit_kind_index,
                    stage=shard.stage,
                    bonus_offset=shard.bonus_offset,
                    bonus_value=shard.bonus_value,
                )
            finished_results[shard.shard_id] = result
            live_results.pop(shard.shard_id, None)
            result_buffer[shard.shard_id] = result

    def mark_missing_ordered_shards_pending() -> None:
        if not result_buffer:
            return
        missing: list[int] = []
        buffered_ids = set(result_buffer)
        completed_ids = set(completed_results)
        for shard_id in shard_order[next_order_index:]:
            if shard_id in buffered_ids:
                break
            if shard_id not in completed_ids:
                missing.append(shard_id)
                if len(missing) >= 5:
                    break
        if missing:
            runtime.emit(
                "-SmashBruteBrawl kept %s unordered worker result(s) for resume; missing earlier shard(s): %s."
                % (len(result_buffer), ", ".join(str(item) for item in missing))
            )

    def shutdown_executor(*, wait: bool) -> None:
        nonlocal executor_shutdown
        if executor is not None and not executor_shutdown:
            if wait:
                executor.shutdown(wait=True, cancel_futures=True)
            else:
                _shutdown_smash_parallel_executor(
                    executor,
                    futures=pending,
                    progress_queue=progress_queue,
                    stop_event=stop_event,
                )
            executor_shutdown = True

    def shutdown_manager() -> None:
        nonlocal manager_shutdown
        if not manager_shutdown:
            manager.shutdown()
            manager_shutdown = True

    def request_interrupt(_signum: int, _frame: Any) -> None:
        nonlocal interrupt_requested
        interrupt_requested = True

    def install_sigint_handler() -> None:
        nonlocal previous_sigint_handler, sigint_handler_installed
        if sigint_handler_installed:
            return
        previous_sigint_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, request_interrupt)
        sigint_handler_installed = True

    def restore_sigint_handler() -> None:
        nonlocal sigint_handler_installed
        if sigint_handler_installed:
            signal.signal(signal.SIGINT, previous_sigint_handler)
            sigint_handler_installed = False

    def ignore_sigint_until_exit() -> None:
        nonlocal previous_sigint_handler, sigint_handler_installed
        if not sigint_handler_installed:
            previous_sigint_handler = signal.getsignal(signal.SIGINT)
            sigint_handler_installed = True
        signal.signal(signal.SIGINT, signal.SIG_IGN)

    def finish_interrupted(exc: BaseException | None = None) -> None:
        nonlocal interrupt_announced
        ignore_sigint_until_exit()
        if not interrupt_announced:
            runtime.emit(
                "-SmashBruteBrawl is stopping cleanly. Workers are parking; saving %s."
                % (runtime.progress_path or "the progress checkpoint")
            )
            interrupt_announced = True
        stop_event.set()
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            drain_worker_progress()
            harvest_finished_futures()
            if not pending:
                break
            if any(future.done() for future in pending):
                continue
            time.sleep(0.05)
        for future in pending:
            future.cancel()
        drain_worker_progress()
        harvest_finished_futures()
        _save_parallel_progress(
            runtime,
            context,
            runtime_plan,
            scan_state,
            candidate_space_hash=candidate_space_hash,
            worker_count=worker_count,
            shard_size=shard_size,
            shards=shards,
            results=live_checkpoint_results(),
            tested_floor=parallel_tested_floor,
            force=True,
            status="interrupted",
        )
        try:
            shutdown_executor(wait=False)
        finally:
            try:
                shutdown_manager()
            finally:
                restore_sigint_handler()
        interruption = smash_checkpoint.SmashBruteBrawlInterrupted(runtime.progress_path)
        if exc is not None:
            raise interruption from exc
        raise interruption

    try:
        install_sigint_handler()
        executor = concurrent.futures.ProcessPoolExecutor(
            max_workers=worker_count,
            initializer=smash_backend.ignore_worker_sigint,
        )
        shard_iter = iter(shards)

        def fill_pending() -> None:
            while len(pending) < worker_count * 2 and not accepted:
                if interrupt_requested:
                    break
                try:
                    shard = next(shard_iter)
                except StopIteration:
                    break
                if shard.kind == "twobytes":
                    shard_runner = smash_backend.run_twobytes_shard
                elif shard.kind == "remove":
                    shard_runner = smash_backend.run_remove_shard
                else:
                    shard_runner = smash_backend.run_standard_shard
                future = executor.submit(shard_runner, plan, shard, stop_event, progress_queue)
                pending[future] = shard
                if interrupt_requested:
                    break

        fill_pending()
        if interrupt_requested:
            finish_interrupted()
        while pending:
            if interrupt_requested:
                finish_interrupted()
            done, _not_done = concurrent.futures.wait(
                pending,
                timeout=0.2,
                return_when=concurrent.futures.FIRST_COMPLETED,
            )
            if interrupt_requested:
                finish_interrupted()
            if not done:
                emit_worker_heartbeat()
                continue
            harvest_finished_futures()
            emit_worker_heartbeat(force=True)
            handle_ready_results()
            if accepted:
                break
            fill_pending()
        while handle_ready_results() and not accepted:
            pass
        if result_buffer and not accepted:
            mark_missing_ordered_shards_pending()
        if accepted:
            for future in pending:
                future.cancel()
        shutdown_executor(wait=True)
    except KeyboardInterrupt as exc:
        finish_interrupted(exc)
    finally:
        try:
            shutdown_executor(wait=True)
        except Exception:
            pass
        try:
            shutdown_manager()
        except Exception:
            pass
        restore_sigint_handler()

    if finished_results:
        scan_state.tested_candidates = max(
            scan_state.tested_candidates,
            parallel_tested_floor + sum(result.tested for result in finished_results.values()),
        )
    scan_state.eta_seconds = (runtime.now() - started_at).seconds
    _emit_sbb_rejection_progress(runtime, scan_state, force=True)
    _save_parallel_progress(
        runtime,
        context,
        runtime_plan,
        scan_state,
        candidate_space_hash=candidate_space_hash,
        worker_count=worker_count,
        shard_size=shard_size,
        shards=shards,
        results=finished_results,
        tested_floor=parallel_tested_floor,
        force=True,
        status=_sbb_scan_terminal_status(scan_state),
    )
    for error, count in sorted(worker_error_counts.items(), key=lambda item: item[0]):
        if count > 1:
            runtime.emit(
                "-SmashBruteBrawl suppressed %s repeated worker shard errors: %s"
                % (count - 1, error)
            )
    return True


def run_scan(runtime: SmashBruteBrawlRuntime, context: SmashBruteBrawlContext) -> SmashBruteBrawlScanResult:
    old_crc = bruteforce.normalize_old_crc(context.old_crc)
    scan_state = SmashBruteBrawlScanState(
        state=bruteforce.BruteForceMatchState(),
        crash=context.crash,
    )

    runtime_plan = prepare_runtime_plan(runtime, context)
    emit_debug_report_if_needed(runtime, context, runtime_plan)
    candidate_space_payload = _candidate_space_payload(
        context,
        runtime_plan,
        source_hash=runtime.source_hash,
    )
    candidate_space_hash = smash_checkpoint.candidate_space_hash(candidate_space_payload)
    progress_resume, progress_warning = _resolve_resume_record(
        runtime,
        context,
        runtime_plan,
        candidate_space_hash,
    )
    if progress_warning:
        runtime.emit("-%s" % progress_warning)

    length_range = runtime_plan.length_range
    resume_outer_index = 0
    resume_inner_index = 0
    resume_cursor: dict[str, Any] | None = None
    if progress_resume is not None:
        cursor = progress_resume.get("cursor")
        counters = progress_resume.get("counters")
        if isinstance(cursor, dict):
            resume_cursor = cursor
            resume_outer_index = _record_int(cursor, "outer_index", 0)
            resume_inner_index = _record_int(cursor, "inner_index", 0)
            scan_state.outer_index = resume_outer_index
            scan_state.inner_index = resume_inner_index
            scan_state.length = _record_int(cursor, "length", 0)
            scan_state.byte_position = _record_int(cursor, "byte_position", 0)
            scan_state.edit_kind_index = _record_int(cursor, "edit_kind_index", 0)
            scan_state.stage = str(cursor.get("stage") or "")
            scan_state.bonus_offset = _record_int(cursor, "bonus_offset", 0)
            scan_state.bonus_value = _record_int(cursor, "bonus_value", 0)
        if isinstance(counters, dict):
            scan_state.tested_candidates = _record_int(counters, "tested_candidates", 0)
            scan_state.accepted_candidates = _record_int(counters, "accepted_candidates", 0)
            scan_state.rejected_candidates = _record_int(counters, "rejected_candidates", 0)
            reasons = counters.get("rejection_reasons")
            if isinstance(reasons, dict):
                scan_state.rejected_reasons = {
                    str(reason): int(count)
                    for reason, count in reasons.items()
                    if str(reason)
                }
            scan_state.first_rejection_reason = str(counters.get("first_rejection_reason") or "")
            scan_state.untrusted_preview_count = _record_int(counters, "preview_only_candidates", 0)
        scan_state.crash = False
        runtime.emit(
            "-SmashBruteBrawl resume checkpoint accepted at outer %s, inner %s."
            % (resume_outer_index, resume_inner_index)
        )

    try:
        resume_backend = str((progress_resume or {}).get("backend") or "")
        if resume_backend in {"", "crc_forge"}:
            crc_forge_outcome = _run_crc_forge_scan(
                runtime,
                context,
                scan_state,
                old_crc,
                runtime_plan,
                candidate_space_hash,
                progress_resume,
            )
            if crc_forge_outcome:
                return SmashBruteBrawlScanResult(
                    state=scan_state.state,
                    old_crc=old_crc,
                    bf_mode=runtime_plan.mode,
                    full_new_data=scan_state.full_new_data,
                    png_bytes=scan_state.png_bytes,
                    to_brute=scan_state.to_brute,
                    diff=scan_state.diff,
                    crash=scan_state.crash,
                    eta_seconds=scan_state.eta_seconds,
                )
            crc_forge_budget_stopped = (
                isinstance(crc_forge_outcome, CrcForgeScanOutcome)
                and bool(crc_forge_outcome.budget_stopped)
            )
            crc_forge_handed_to_sbb = isinstance(crc_forge_outcome, CrcForgeScanOutcome)
            if resume_backend == "crc_forge":
                progress_resume = None
                resume_outer_index = 0
                resume_inner_index = 0
                resume_cursor = None
                _reset_scan_state_for_next_sbb_pass(scan_state)
                runtime.emit(
                    "-HermesProbe CRC-forge checkpoint is not reused for broad SBB; starting the SBB pass from zero."
                )
            recommended_sbb = (
                None
                if crc_forge_budget_stopped
                else _recommended_sbb_level_after_crc_forge(runtime, context, old_crc)
            )
            fallback_byte_count = (
                max(0, int(crc_forge_outcome.last_byte_count))
                if isinstance(crc_forge_outcome, CrcForgeScanOutcome)
                else None
            )
            if crc_forge_budget_stopped:
                runtime.emit(
                    "-HermesProbe CRC-forge did not finish its targeted pass; broad SBB keeps level %s."
                    % int(context.brute_level)
                )
            elif recommended_sbb is not None and int(recommended_sbb[0]) > int(context.brute_level):
                recommended_level, recommended_byte_count = recommended_sbb
                fallback_byte_count = int(recommended_byte_count)
                context = replace(context, brute_level=int(recommended_level))
                runtime_plan = prepare_runtime_plan(runtime, context)
                candidate_space_payload = _candidate_space_payload(
                    context,
                    runtime_plan,
                    source_hash=runtime.source_hash,
                )
                candidate_space_hash = smash_checkpoint.candidate_space_hash(candidate_space_payload)
                length_range = runtime_plan.length_range
                progress_resume = None
                resume_outer_index = 0
                resume_inner_index = 0
                resume_cursor = None
                _reset_scan_state_for_next_sbb_pass(scan_state)
                runtime.emit(
                    "-HermesProbe CRC-forge exhausted targeted passes up to %s bytes; broad SBB will resume at level %s."
                    % (recommended_byte_count, recommended_level)
                )
            if crc_forge_handed_to_sbb:
                decision = _ask_sbb_fallback_decision(
                    runtime,
                    context,
                    detected_level=int(context.brute_level),
                    detected_byte_count=fallback_byte_count if fallback_byte_count else None,
                )
                if decision.action == "blackfill":
                    runtime.emit("-SBB fallback decision: keeping the blackfill fallback; broad SBB skipped.")
                    runtime.side_notes.append(
                        "-SmashBruteBrawl broad SBB skipped by user; keeping blackfill fallback."
                    )
                    save_smash_progress_snapshot(
                        runtime,
                        context,
                        runtime_plan,
                        scan_state,
                        candidate_space_hash=candidate_space_hash,
                        force=True,
                        status="accepted_blackfill",
                    )
                    return SmashBruteBrawlScanResult(
                        state=scan_state.state,
                        old_crc=old_crc,
                        bf_mode=runtime_plan.mode,
                        full_new_data=scan_state.full_new_data,
                        png_bytes=scan_state.png_bytes,
                        to_brute=scan_state.to_brute,
                        diff=scan_state.diff,
                        crash=scan_state.crash,
                        eta_seconds=scan_state.eta_seconds,
                    )
                if decision.action == "manual" and decision.brute_level is not None:
                    if int(decision.brute_level) != int(context.brute_level):
                        context = replace(context, brute_level=int(decision.brute_level))
                        runtime_plan = prepare_runtime_plan(runtime, context)
                        candidate_space_payload = _candidate_space_payload(
                            context,
                            runtime_plan,
                            source_hash=runtime.source_hash,
                        )
                        candidate_space_hash = smash_checkpoint.candidate_space_hash(
                            candidate_space_payload
                        )
                        length_range = runtime_plan.length_range
                        progress_resume = None
                        resume_outer_index = 0
                        resume_inner_index = 0
                        resume_cursor = None
                        _reset_scan_state_for_next_sbb_pass(scan_state)
                    if decision.byte_count:
                        runtime.emit(
                            "-SBB fallback manual override: level %s for declared byte scope %s."
                            % (int(context.brute_level), int(decision.byte_count))
                        )
                    else:
                        runtime.emit(
                            "-SBB fallback manual override: level %s."
                            % int(context.brute_level)
                        )
        _emit_sbb_level_warning(runtime, context, runtime_plan)
        if _run_gpu_scan(
            runtime,
            context,
            scan_state,
            old_crc,
            runtime_plan,
            candidate_space_hash,
            progress_resume,
            resume_outer_index,
            resume_inner_index,
        ):
            return SmashBruteBrawlScanResult(
                state=scan_state.state,
                old_crc=old_crc,
                bf_mode=runtime_plan.mode,
                full_new_data=scan_state.full_new_data,
                png_bytes=scan_state.png_bytes,
                to_brute=scan_state.to_brute,
                diff=scan_state.diff,
                crash=scan_state.crash,
                eta_seconds=scan_state.eta_seconds,
            )
        if _run_parallel_scan(
            runtime,
            context,
            scan_state,
            old_crc,
            runtime_plan,
            candidate_space_hash,
            progress_resume,
            resume_outer_index,
            resume_inner_index,
        ):
            return SmashBruteBrawlScanResult(
                state=scan_state.state,
                old_crc=old_crc,
                bf_mode=runtime_plan.mode,
                full_new_data=scan_state.full_new_data,
                png_bytes=scan_state.png_bytes,
                to_brute=scan_state.to_brute,
                diff=scan_state.diff,
                crash=scan_state.crash,
                eta_seconds=scan_state.eta_seconds,
            )
        length_plans = _build_smash_length_plans(runtime, context, runtime_plan)
        for length_plan in length_plans:
            if length_plan.outer_index < resume_outer_index:
                continue
            run_scan_length(
                runtime,
                context,
                scan_state,
                old_crc,
                runtime_plan.mode,
                runtime_plan.struct_indexes,
                length_plan.length,
                length_range.step,
                length_plan.outer_index,
                resume_inner_index=resume_inner_index if length_plan.outer_index == resume_outer_index else 0,
                resume_cursor=resume_cursor if length_plan.outer_index == resume_outer_index else None,
                runtime_plan=runtime_plan,
                candidate_space_hash=candidate_space_hash,
                length_plan=length_plan,
            )
            save_smash_progress_snapshot(
                runtime,
                context,
                runtime_plan,
                scan_state,
                candidate_space_hash=candidate_space_hash,
                force=True,
            )
    except KeyboardInterrupt as exc:
        save_smash_progress_snapshot(
            runtime,
            context,
            runtime_plan,
            scan_state,
            candidate_space_hash=candidate_space_hash,
            force=True,
            status="interrupted",
        )
        raise smash_checkpoint.SmashBruteBrawlInterrupted(runtime.progress_path) from exc

    save_smash_progress_snapshot(
        runtime,
        context,
        runtime_plan,
        scan_state,
        candidate_space_hash=candidate_space_hash,
        force=True,
        status=_sbb_scan_terminal_status(scan_state),
    )
    _emit_sbb_rejection_progress(runtime, scan_state, force=True)

    return SmashBruteBrawlScanResult(
        state=scan_state.state,
        old_crc=old_crc,
        bf_mode=runtime_plan.mode,
        full_new_data=scan_state.full_new_data,
        png_bytes=scan_state.png_bytes,
        to_brute=scan_state.to_brute,
        diff=scan_state.diff,
        crash=scan_state.crash,
        eta_seconds=scan_state.eta_seconds,
    )
