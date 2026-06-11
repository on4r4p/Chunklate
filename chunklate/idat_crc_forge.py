from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable
import zlib

from . import bruteforce, crc32_forge, deflate_probe, idat, png, smash_backend


SEED_BYTE_COUNTS = (1, 2, 3)
FORGE_BYTE_COUNTS = (4, 5, 6, 7, 8, 9, 10)
DIRECT_CRC_BYTE_COUNTS = SEED_BYTE_COUNTS + (4,)
SMALL_AUTO_EDIT_BYTE_COUNTS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
TARGET_BYTE_COUNTS = SEED_BYTE_COUNTS + FORGE_BYTE_COUNTS
DEFAULT_WINDOW_RADIUS = 8192
DEFAULT_MAX_CANDIDATES = 2_000_000
FORCE_MAX_CANDIDATES = 50_000_000
SCANLINE_ANOMALY_BACKTRACK_ROWS = (4, 3, 2, 1)
SCANLINE_ANOMALY_HALF_WINDOW = 32
SCANLINE_ANOMALY_INTERVAL_DIVISOR = 6
AUTO_FOCUSED_BYTE_COUNTS = (7, 8, 9, 10, 6, 5, 4, 3, 2, 1)
AUTO_FREE_INDEX_LIMITS = {
    6: 4096,
    7: 4096,
    8: 4096,
    9: 390_000,
    10: 0,
}
AUTO_LIMITED_FREE_INDEX_MAX_POSITIONS = 30
REPLACE_SEED_TRANSFORM_COUNT = 1
INSERT_SEED_TRANSFORM_COUNT = 5
LOCAL_ZLIB_PREFILTER_SCANLINES = 8
LOCAL_ZLIB_PREFILTER_CHUNK_SIZE = 2048
STRICT_ZLIB_PREFILTER_MIN_PAYLOAD = 64 * 1024
DEFLATE_TRACE_CHECKPOINT_STRIDE = 2048
DEFLATE_WINDOW_TARGET_BACKTRACK_ROWS = 2
DEFLATE_GUIDED_PREFIX_CANDIDATES = 32
DEFLATE_GUIDED_FULL_CANDIDATES = 32
DEFLATE_GUIDED_BRANCH_TOKENS = 64
DEFLATE_GUIDED_EXPANSION_BUDGET = 8_192
DEFLATE_GUIDED_FREE_INDEX_MARKER = -2
DEFLATE_GUIDED_FULL_INDEX_MARKER = -3


@dataclass(frozen=True)
class ForgeWindow:
    start: int
    end: int
    source: str = "diagnostic"

    @property
    def length(self) -> int:
        return max(0, int(self.end) - int(self.start))


@dataclass(frozen=True)
class ForgeCandidate:
    hit: smash_backend.SmashCandidateHit
    byte_count: int
    free_index: int


@dataclass(frozen=True)
class ForgeScanSummary:
    runnable: bool
    reason: str
    estimated_candidates: int = 0
    windows: tuple[ForgeWindow, ...] = ()
    byte_counts: tuple[int, ...] = ()


@dataclass(frozen=True)
class ForgeAutoPlan:
    edit_order: tuple[str, ...]
    byte_counts: tuple[int, ...]
    reason: str = ""
    reset_resume: bool = False


@dataclass(frozen=True)
class _ZlibProbeSettings:
    expected_size: int
    scanline_size: int
    height: int


@dataclass(frozen=True)
class _ZlibProbeCheckpoint:
    position: int
    decompressor: zlib.Decompress
    output_size: int


def normalize_old_crc(old_crc: object) -> bytes | None:
    if not old_crc:
        return None
    if isinstance(old_crc, bytes) and len(old_crc) == 4:
        return old_crc
    if isinstance(old_crc, bytearray) and len(old_crc) == 4:
        return bytes(old_crc)
    if isinstance(old_crc, str):
        text = old_crc.strip()
        try:
            value = bytes.fromhex(text)
        except ValueError:
            return None
        return value if len(value) == 4 else None
    return None


def parse_window_spec(spec: str | None, payload_len: int) -> tuple[ForgeWindow, ...]:
    if spec is None or str(spec).strip() == "":
        return ()
    windows: list[ForgeWindow] = []
    for raw_part in str(spec).split(","):
        part = raw_part.strip()
        if not part:
            continue
        if ":" not in part:
            center = int(part, 0)
            start = center
            end = center + 1
        else:
            raw_start, raw_end = part.split(":", 1)
            start = int(raw_start, 0) if raw_start.strip() else 0
            end = int(raw_end, 0) if raw_end.strip() else payload_len + 1
        start = max(0, min(int(start), payload_len + 1))
        end = max(start, min(int(end), payload_len + 1))
        if end > start:
            windows.append(ForgeWindow(start, end, "cli"))
    return tuple(_merge_windows(windows))


def _merge_windows(windows: Iterable[ForgeWindow]) -> tuple[ForgeWindow, ...]:
    ordered = sorted(windows, key=lambda item: (item.start, item.end))
    merged: list[ForgeWindow] = []
    for window in ordered:
        if not merged or window.start > merged[-1].end:
            merged.append(window)
            continue
        previous = merged[-1]
        merged[-1] = ForgeWindow(
            previous.start,
            max(previous.end, window.end),
            previous.source if previous.source == window.source else "merged",
        )
    return tuple(merged)


def diagnostic_windows(source_data: bytes, payload_len: int, *, radius: int = DEFAULT_WINDOW_RADIUS) -> tuple[ForgeWindow, ...]:
    analysis = idat.analyze_idat_stream(source_data)
    centers: list[int] = []
    if analysis.error_idat_offset is not None:
        centers.append(int(analysis.error_idat_offset))
    if analysis.error_offset is not None:
        centers.append(int(analysis.error_offset))
    if analysis.status in {"bad_adler", "partial"} and payload_len > 0:
        centers.append(payload_len)
    windows: list[ForgeWindow] = []
    for center in centers:
        start = max(0, int(center) - int(radius))
        end = min(payload_len + 1, int(center) + int(radius) + 1)
        if end > start:
            windows.append(ForgeWindow(start, end, "diagnostic"))
    return tuple(_merge_windows(windows))


def _idat_stream_and_target_start(
    source_data: bytes,
    target_chunk: png.PngChunk,
) -> tuple[bytes, int]:
    try:
        chunks = tuple(chunk for chunk in png.iter_chunks(source_data) if chunk.chunk_type == b"IDAT")
    except png.PngFormatError:
        return target_chunk.data, 0
    if not chunks:
        return target_chunk.data, 0

    stream_parts: list[bytes] = []
    stream_offset = 0
    target_start: int | None = None
    for chunk in chunks:
        if chunk.offset == target_chunk.offset and chunk.length == target_chunk.length:
            target_start = stream_offset
        stream_parts.append(chunk.data)
        stream_offset += chunk.length
    return b"".join(stream_parts), int(target_start or 0)


def _compressed_offsets_for_decompressed_targets(
    compressed: bytes,
    targets: Iterable[int],
) -> dict[int, int]:
    ordered = sorted({max(0, int(target)) for target in targets})
    if not ordered:
        return {}

    offsets: dict[int, int] = {}
    target_index = 0
    decompressed_size = 0
    decompressor = zlib.decompressobj()
    for compressed_offset, value in enumerate(compressed):
        try:
            decompressed_size += len(decompressor.decompress(bytes((value,))))
        except zlib.error:
            break
        while target_index < len(ordered) and decompressed_size >= ordered[target_index]:
            offsets[ordered[target_index]] = compressed_offset
            target_index += 1
        if target_index >= len(ordered):
            break
    return offsets


def scanline_anomaly_windows(
    source_data: bytes,
    target_chunk: png.PngChunk,
    *,
    half_window: int = SCANLINE_ANOMALY_HALF_WINDOW,
) -> tuple[ForgeWindow, ...]:
    analysis = idat.analyze_idat_stream(source_data)
    if (
        not analysis.supported
        or analysis.scanline_size <= 0
        or analysis.height <= 0
        or analysis.status not in {"bad_adler", "partial"}
        or analysis.usable_scanlines <= 0
        or analysis.usable_scanlines >= analysis.height
    ):
        return ()

    idat_stream, target_stream_start = _idat_stream_and_target_start(source_data, target_chunk)
    if not idat_stream:
        return ()

    rows: list[int] = []
    for backtrack in SCANLINE_ANOMALY_BACKTRACK_ROWS:
        row = max(0, int(analysis.usable_scanlines) - int(backtrack))
        if 0 <= row < analysis.height:
            rows.append(row)
    if not rows:
        return ()

    targets = tuple(
        target_row * int(analysis.scanline_size)
        for row in rows
        for target_row in (row, row + 1)
        if target_row < analysis.height
    )
    compressed_offsets = _compressed_offsets_for_decompressed_targets(idat_stream, targets)
    windows: list[ForgeWindow] = []
    for row in rows:
        current_target = row * int(analysis.scanline_size)
        next_target = (row + 1) * int(analysis.scanline_size)
        current_offset = compressed_offsets.get(current_target)
        next_offset = compressed_offsets.get(next_target)
        if current_offset is None:
            continue
        start_offset = current_offset
        end_offset = next_offset if next_offset is not None else current_offset + 1
        if end_offset < start_offset:
            start_offset, end_offset = end_offset, start_offset
        interval_length = max(1, int(end_offset) - int(start_offset))
        center_offset = int(start_offset) + max(0, interval_length // SCANLINE_ANOMALY_INTERVAL_DIVISOR)
        local_start = max(0, int(center_offset) - int(target_stream_start) - int(half_window))
        local_end = min(
            len(target_chunk.data) + 1,
            int(center_offset) - int(target_stream_start) + int(half_window) + 1,
        )
        if local_end > local_start:
            windows.append(ForgeWindow(local_start, local_end, "scanline-anomaly"))
    return tuple(_merge_windows(windows))


def _center_out_windows(windows: tuple[ForgeWindow, ...]) -> tuple[ForgeWindow, ...]:
    if len(windows) < 3:
        return windows
    center = len(windows) // 2
    ordered_indexes: list[int] = []
    for distance in range(0, len(windows)):
        for candidate_index in (center - distance, center + distance):
            if 0 <= candidate_index < len(windows) and candidate_index not in ordered_indexes:
                ordered_indexes.append(candidate_index)
    return tuple(windows[index] for index in ordered_indexes)


def _rank_scanline_windows_by_deflate(
    source_data: bytes,
    target_chunk: png.PngChunk,
    windows: tuple[ForgeWindow, ...],
) -> tuple[ForgeWindow, ...]:
    if len(windows) < 2:
        return windows
    try:
        analysis = idat.analyze_idat_stream(source_data)
    except Exception:
        return _center_out_windows(windows)
    if (
        not analysis.supported
        or analysis.scanline_size <= 0
        or analysis.usable_scanlines <= 0
        or analysis.height <= 0
    ):
        return _center_out_windows(windows)
    try:
        trace = deflate_probe.cached_analyze_deflate_stream(
            target_chunk.data,
            checkpoint_stride=DEFLATE_TRACE_CHECKPOINT_STRIDE,
        )
    except Exception:
        return _center_out_windows(windows)
    if not trace.checkpoints:
        return _center_out_windows(windows)
    target_row = max(
        0,
        min(
            int(analysis.height) - 1,
            int(analysis.usable_scanlines) - DEFLATE_WINDOW_TARGET_BACKTRACK_ROWS,
        ),
    )
    target_output = int(target_row) * int(analysis.scanline_size)
    scores = deflate_probe.score_windows_by_output_offset(trace, windows, target_output)
    ranked = tuple(score.window for score in scores)
    return ranked or _center_out_windows(windows)


def ranked_auto_windows(
    source_data: bytes,
    target_chunk: png.PngChunk,
    *,
    radius: int = DEFAULT_WINDOW_RADIUS,
) -> tuple[ForgeWindow, ...]:
    payload_len = len(target_chunk.data)
    scanline_windows = scanline_anomaly_windows(source_data, target_chunk)
    if scanline_windows:
        return _rank_scanline_windows_by_deflate(source_data, target_chunk, scanline_windows)
    return diagnostic_windows(source_data, payload_len, radius=radius)


def _auto_focused_byte_counts(source_data: bytes, byte_counts: tuple[int, ...]) -> tuple[int, ...]:
    try:
        analysis = idat.analyze_idat_stream(source_data)
    except Exception:
        analysis = None
    if (
        analysis is not None
        and int(getattr(analysis, "expected_size", 0)) > 0
        and 0 < abs(int(getattr(analysis, "decompressed_size", 0)) - int(analysis.expected_size)) <= 30
    ):
        gap = abs(int(getattr(analysis, "decompressed_size", 0)) - int(analysis.expected_size))
        preferred = max(1, min(10, (gap + 1) // 2))
        order = tuple(
            count
            for distance in range(0, 10)
            for count in (preferred - distance, preferred + distance)
            if 1 <= count <= 10
        )
    else:
        order = AUTO_FOCUSED_BYTE_COUNTS
    return tuple(dict.fromkeys(count for count in order if count in byte_counts))


def _expanded_edit_order(
    source_data: bytes,
    edit_order: tuple[str, ...],
    byte_count: int,
) -> tuple[str, ...]:
    clean_order = tuple(
        dict.fromkeys(edit_kind for edit_kind in edit_order if edit_kind in {"insert", "replace", "remove"})
    )
    if int(byte_count) not in SMALL_AUTO_EDIT_BYTE_COUNTS:
        return clean_order
    try:
        analysis = idat.analyze_idat_stream(source_data)
    except Exception:
        analysis = None
    priority: tuple[str, ...] = ()
    if analysis is not None and int(getattr(analysis, "expected_size", 0)) > 0:
        decompressed_gap = int(analysis.expected_size) - int(getattr(analysis, "decompressed_size", 0))
        if decompressed_gap > 0:
            priority = ("insert", "replace", "remove")
        elif decompressed_gap < 0:
            priority = ("remove", "replace", "insert")
    if not priority:
        return clean_order
    return tuple(
        dict.fromkeys(
            edit_kind
            for edit_kind in priority + clean_order + ("replace", "insert", "remove")
            if edit_kind in {"insert", "replace", "remove"}
        )
    )


def _explicit_window_edit_order(edit_order: tuple[str, ...], byte_count: int) -> tuple[str, ...]:
    if int(byte_count) not in DIRECT_CRC_BYTE_COUNTS:
        return edit_order
    return tuple(
        dict.fromkeys(
            edit_kind
            for edit_kind in tuple(edit_order) + ("replace", "insert", "remove")
            if edit_kind in {"insert", "replace", "remove"}
        )
    )


def focused_auto_plan(
    source_data: bytes,
    target_chunk: png.PngChunk,
    *,
    edit_order: tuple[str, ...],
    byte_counts: tuple[int, ...],
    explicit_byte_count: bool = False,
    explicit_window: bool = False,
    focus: str = "",
    edit_mode: str = "",
) -> ForgeAutoPlan:
    if explicit_byte_count or explicit_window:
        return ForgeAutoPlan(edit_order=edit_order, byte_counts=byte_counts)

    focused_available_counts = _auto_focused_byte_counts(source_data, byte_counts)
    if not focused_available_counts:
        return ForgeAutoPlan(edit_order=edit_order, byte_counts=byte_counts)
    if not scanline_anomaly_windows(source_data, target_chunk):
        return ForgeAutoPlan(edit_order=edit_order, byte_counts=byte_counts)

    clean_focus = str(focus or "").strip().lower()
    edit_kind_by_mode = {
        "insert": "insert",
        "remove": "remove",
        "replace": "replace",
    }
    requested_edit = edit_kind_by_mode.get(clean_focus)
    if requested_edit is None and clean_focus == "progressive":
        requested_edit = edit_kind_by_mode.get(str(edit_mode or "").strip().lower())
    if requested_edit is not None and requested_edit in edit_order:
        short_edit_order = _expanded_edit_order(source_data, (requested_edit,), focused_available_counts[0])
        if short_edit_order != (requested_edit,):
            return ForgeAutoPlan(
                edit_order=short_edit_order,
                byte_counts=focused_available_counts,
                reason="scanline-anomaly %s focus with short IDAT gap: trying %s %s first"
                % (
                    clean_focus or requested_edit,
                    "/".join(edit.title() for edit in short_edit_order),
                    "/".join(str(count) for count in focused_available_counts),
                ),
                reset_resume=True,
            )
        return ForgeAutoPlan(
            edit_order=(requested_edit,),
            byte_counts=focused_available_counts,
            reason="scanline-anomaly %s focus: trying %s %s first"
            % (
                clean_focus or requested_edit,
                requested_edit.title(),
                "/".join(str(count) for count in focused_available_counts),
            ),
            reset_resume=True,
        )

    analysis = idat.analyze_idat_stream(source_data)
    decompressed_gap = abs(int(analysis.decompressed_size) - int(analysis.expected_size))
    if 0 < decompressed_gap < 9:
        focused_count = 4
    else:
        focused_count = 5
    if focused_count not in byte_counts and (
        not focused_available_counts or decompressed_gap <= focused_count + 4
    ):
        return ForgeAutoPlan(
            edit_order=(),
            byte_counts=(),
            reason=(
                "scanline-anomaly bad_adler points to %s bytes outside the requested CRC-forge range; "
                "leaving this pass to SmashBruteBrawl"
            )
            % focused_count,
            reset_resume=True,
        )
    if analysis.expected_size > 0 and analysis.decompressed_size > analysis.expected_size:
        focused_edit = "remove"
        focused_counts = focused_available_counts
    elif analysis.expected_size > 0 and analysis.decompressed_size < analysis.expected_size:
        if decompressed_gap <= focused_count + 4:
            focused_edit = "insert"
            focused_counts = (focused_count,)
        else:
            focused_edit = "replace"
            focused_counts = focused_available_counts
    else:
        focused_edit = "replace"
        focused_counts = focused_available_counts
    if focused_edit not in edit_order:
        return ForgeAutoPlan(edit_order=edit_order, byte_counts=byte_counts)
    if not focused_counts:
        return ForgeAutoPlan(
            edit_order=(),
            byte_counts=(),
            reason=(
                "scanline-anomaly bad_adler points to %s bytes outside the requested CRC-forge range; "
                "leaving this pass to SmashBruteBrawl"
            )
            % focused_count,
            reset_resume=True,
        )

    return ForgeAutoPlan(
        edit_order=(focused_edit,),
        byte_counts=focused_counts,
        reason="scanline-anomaly bad_adler fast path: trying %s %s first"
        % (focused_edit.title(), "/".join(str(count) for count in focused_counts)),
        reset_resume=True,
    )


def _zlib_probe_settings(source_data: bytes) -> _ZlibProbeSettings | None:
    analysis = idat.analyze_idat_stream(source_data)
    if not analysis.supported or analysis.expected_size <= 0:
        return None
    if analysis.scanline_size <= 0 or analysis.height <= 0:
        return None
    return _ZlibProbeSettings(
        expected_size=int(analysis.expected_size),
        scanline_size=int(analysis.scanline_size),
        height=int(analysis.height),
    )


def _scanline_filter_offsets_between(
    start_size: int,
    end_size: int,
    settings: _ZlibProbeSettings,
) -> Iterable[int]:
    if end_size <= start_size or settings.scanline_size <= 0:
        return ()
    first_row = max(0, int(start_size) // int(settings.scanline_size))
    if first_row * int(settings.scanline_size) < int(start_size):
        first_row += 1
    last_row = min(
        int(settings.height) - 1,
        max(0, (int(end_size) - 1) // int(settings.scanline_size)),
    )
    return (
        row * int(settings.scanline_size)
        for row in range(first_row, last_row + 1)
    )


def _zlib_probe_feed(
    decompressor: zlib.Decompress,
    data: object,
    output_size: int,
    settings: _ZlibProbeSettings,
) -> tuple[bool, int]:
    try:
        chunk = decompressor.decompress(data)
    except zlib.error:
        return False, output_size
    if not chunk:
        return True, output_size
    start_size = output_size
    end_size = output_size + len(chunk)
    for filter_offset in _scanline_filter_offsets_between(start_size, end_size, settings):
        filter_index = int(filter_offset) - start_size
        if 0 <= filter_index < len(chunk) and chunk[filter_index] > 4:
            return False, end_size
    return True, end_size


def _build_zlib_probe_checkpoint(
    payload: bytes,
    position: int,
    settings: _ZlibProbeSettings,
    heartbeat_callback: Callable[[], object] | None = None,
) -> _ZlibProbeCheckpoint | None:
    decompressor = zlib.decompressobj()
    output_size = 0
    if position > 0:
        payload_view = memoryview(payload)
        chunk_size = 64 * 1024
        for start in range(0, position, chunk_size):
            ok, output_size = _zlib_probe_feed(
                decompressor,
                payload_view[start : min(position, start + chunk_size)],
                output_size,
                settings,
            )
            if heartbeat_callback is not None:
                heartbeat_callback()
            if not ok:
                return None
    return _ZlibProbeCheckpoint(position=position, decompressor=decompressor, output_size=output_size)


def _zlib_probe_accepts_candidate(
    checkpoint: _ZlibProbeCheckpoint,
    payload: bytes,
    position: int,
    edit_kind: str,
    byte_count: int,
    brute_bytes: bytes,
    settings: _ZlibProbeSettings,
    *,
    require_complete: bool = True,
) -> bool:
    decompressor = checkpoint.decompressor.copy()
    output_size = int(checkpoint.output_size)
    payload_view = memoryview(payload)
    parts: list[object] = []
    if position > checkpoint.position:
        parts.append(payload_view[checkpoint.position:position])
    if edit_kind == "insert":
        parts.append(brute_bytes)
        parts.append(payload_view[position:])
    elif edit_kind == "replace":
        parts.append(brute_bytes)
        parts.append(payload_view[position + byte_count :])
    elif edit_kind == "remove":
        parts.append(payload_view[position + byte_count :])
    else:
        return False

    local_target = min(
        int(settings.expected_size),
        int(checkpoint.output_size) + int(settings.scanline_size) * LOCAL_ZLIB_PREFILTER_SCANLINES,
    )
    for part in parts:
        if len(part) == 0:
            continue
        offset = 0
        while offset < len(part):
            if not require_complete and output_size >= local_target:
                return True
            next_offset = min(len(part), offset + LOCAL_ZLIB_PREFILTER_CHUNK_SIZE)
            ok, output_size = _zlib_probe_feed(decompressor, part[offset:next_offset], output_size, settings)
            if not ok:
                return False
            if output_size > settings.expected_size:
                return False
            offset = next_offset
    if not require_complete:
        return output_size >= local_target
    try:
        tail = decompressor.flush()
    except zlib.error:
        return False
    if tail:
        start_size = output_size
        output_size += len(tail)
        for filter_offset in _scanline_filter_offsets_between(start_size, output_size, settings):
            filter_index = int(filter_offset) - start_size
            if 0 <= filter_index < len(tail) and tail[filter_index] > 4:
                return False
    return bool(decompressor.eof and output_size == settings.expected_size)


def _zlib_probe_accepts_candidate_before_yield(
    checkpoint: _ZlibProbeCheckpoint,
    payload: bytes,
    position: int,
    edit_kind: str,
    byte_count: int,
    brute_bytes: bytes,
    settings: _ZlibProbeSettings,
) -> bool:
    if not _zlib_probe_accepts_candidate(
        checkpoint,
        payload,
        position,
        edit_kind,
        byte_count,
        brute_bytes,
        settings,
        require_complete=False,
    ):
        return False
    if len(payload) < STRICT_ZLIB_PREFILTER_MIN_PAYLOAD:
        return True
    return _zlib_probe_accepts_candidate(
        checkpoint,
        payload,
        position,
        edit_kind,
        byte_count,
        brute_bytes,
        settings,
        require_complete=True,
    )


def operation_position_limit(payload_len: int, edit_kind: str, byte_count: int) -> int:
    if edit_kind == "insert":
        return payload_len + 1
    return max(0, payload_len - int(byte_count) + 1)


def clamp_windows_for_operation(
    windows: Iterable[ForgeWindow],
    payload_len: int,
    edit_kind: str,
    byte_count: int,
) -> tuple[ForgeWindow, ...]:
    limit = operation_position_limit(payload_len, edit_kind, byte_count)
    clamped: list[ForgeWindow] = []
    for window in windows:
        start = max(0, min(window.start, limit))
        end = max(start, min(window.end, limit))
        if end > start:
            clamped.append(ForgeWindow(start, end, window.source))
    return tuple(clamped)


def _free_index_total(byte_count: int, free_index_limit: int | None = None) -> int:
    free_len = max(0, int(byte_count) - 4)
    total = 256**free_len
    if free_index_limit is None:
        return total
    return min(total, max(0, int(free_index_limit)))


def _auto_free_index_limit(
    byte_count: int,
    *,
    mode: str,
    explicit_windows: bool,
) -> int | None:
    del explicit_windows
    if mode == "force":
        return None
    return AUTO_FREE_INDEX_LIMITS.get(int(byte_count))


def candidate_count(
    windows: Iterable[ForgeWindow],
    edit_kind: str,
    byte_count: int,
    *,
    free_index_limit: int | None = None,
) -> int:
    positions = sum(window.length for window in windows)
    if int(byte_count) in DIRECT_CRC_BYTE_COUNTS:
        return positions
    if edit_kind == "remove":
        return positions
    if edit_kind == "insert":
        seed_count = positions * INSERT_SEED_TRANSFORM_COUNT
    elif edit_kind == "replace":
        seed_count = positions * REPLACE_SEED_TRANSFORM_COUNT
    else:
        seed_count = 0
    if int(byte_count) not in FORGE_BYTE_COUNTS:
        return seed_count
    return seed_count + positions * _free_index_total(byte_count, free_index_limit)


def _seed_candidate_count(windows: Iterable[ForgeWindow], edit_kind: str, byte_count: int) -> int:
    positions = sum(window.length for window in windows)
    if int(byte_count) in DIRECT_CRC_BYTE_COUNTS:
        return positions
    if edit_kind == "insert":
        return positions * INSERT_SEED_TRANSFORM_COUNT
    if edit_kind == "replace":
        return positions * REPLACE_SEED_TRANSFORM_COUNT
    if edit_kind == "remove":
        return positions
    return 0


def _unique_seed_candidates(candidates: Iterable[bytes], byte_count: int) -> tuple[bytes, ...]:
    seen: set[bytes] = set()
    unique: list[bytes] = []
    for candidate in candidates:
        if len(candidate) != int(byte_count) or candidate in seen:
            continue
        seen.add(candidate)
        unique.append(candidate)
    return tuple(unique)


def _insert_seed_candidates(payload: bytes, position: int, byte_count: int) -> tuple[bytes, ...]:
    byte_count = int(byte_count)
    previous_start = max(0, int(position) - byte_count)
    previous = payload[previous_start:position]
    following = payload[position : position + byte_count]
    candidates: list[bytes] = [b"\x00" * byte_count]
    if len(previous) == byte_count:
        candidates.append(previous)
        candidates.append(bytes(value ^ 0xFF for value in previous))
    if len(following) == byte_count:
        candidates.append(following)
        candidates.append(bytes(value ^ 0xFF for value in following))
    return _unique_seed_candidates(candidates, byte_count)


def _replace_seed_candidates(payload: bytes, position: int, byte_count: int) -> tuple[bytes, ...]:
    current = payload[position : position + byte_count]
    if len(current) != int(byte_count):
        return ()
    inverted = bytes(value ^ 0xFF for value in current)
    return _unique_seed_candidates((inverted,), byte_count)


def _seed_candidates(payload: bytes, position: int, byte_count: int, edit_kind: str) -> tuple[bytes, ...]:
    if edit_kind == "insert":
        return _insert_seed_candidates(payload, position, byte_count)
    if edit_kind == "replace":
        return _replace_seed_candidates(payload, position, byte_count)
    return ()


def _guided_free_prefix_candidates(
    payload: bytes,
    position: int,
    free_len: int,
    trace: deflate_probe.DeflateTrace | None,
    target_output_delta: int | None = None,
) -> tuple[bytes, ...]:
    free_len = int(free_len)
    if free_len <= 0 or trace is None or not trace.ok:
        return ()
    state = deflate_probe.huffman_state_before_byte_boundary(
        payload,
        position,
        trace=trace,
    )
    if state is None:
        return ()
    candidates = deflate_probe.iter_huffman_byte_prefix_candidates(
        payload,
        state,
        position,
        free_len,
        max_candidates=DEFLATE_GUIDED_PREFIX_CANDIDATES,
        max_branch_tokens=DEFLATE_GUIDED_BRANCH_TOKENS,
        target_output_delta=target_output_delta,
        max_expansions=DEFLATE_GUIDED_EXPANSION_BUDGET,
    )
    return tuple(dict.fromkeys(candidate.prefix for candidate in candidates))


def _guided_full_byte_candidates(
    payload: bytes,
    position: int,
    byte_count: int,
    trace: deflate_probe.DeflateTrace | None,
    target_output_delta: int | None = None,
) -> tuple[bytes, ...]:
    byte_count = int(byte_count)
    if byte_count <= 0 or trace is None or not trace.ok:
        return ()
    state = deflate_probe.huffman_state_before_byte_boundary(
        payload,
        position,
        trace=trace,
    )
    if state is None:
        return ()
    candidates = deflate_probe.iter_huffman_byte_prefix_candidates(
        payload,
        state,
        position,
        byte_count,
        max_candidates=DEFLATE_GUIDED_FULL_CANDIDATES,
        max_branch_tokens=DEFLATE_GUIDED_BRANCH_TOKENS,
        target_output_delta=target_output_delta,
        max_expansions=DEFLATE_GUIDED_EXPANSION_BUDGET,
    )
    return tuple(dict.fromkeys(candidate.prefix for candidate in candidates))


def _guided_target_output_delta(
    source_data: bytes,
    edit_kind: str,
    byte_count: int,
) -> int | None:
    if edit_kind not in {"insert", "replace"}:
        return None
    try:
        analysis = idat.analyze_idat_stream(source_data)
    except Exception:
        return None
    if not getattr(analysis, "supported", False) or int(getattr(analysis, "expected_size", 0)) <= 0:
        return None
    gap = int(getattr(analysis, "expected_size", 0)) - int(getattr(analysis, "decompressed_size", 0))
    if gap <= 0:
        return None
    max_local_delta = max(64, int(byte_count) * 16)
    if gap > max_local_delta:
        return None
    return gap


def _clip_windows_to_candidate_budget(
    windows: tuple[ForgeWindow, ...],
    edit_kind: str,
    byte_count: int,
    max_candidates: int,
    free_index_limit: int | None = None,
) -> tuple[ForgeWindow, ...]:
    if (
        free_index_limit is None
        and candidate_count(windows, edit_kind, byte_count, free_index_limit=free_index_limit) <= max_candidates
    ):
        return windows
    seed_per_position = 0
    if edit_kind == "insert":
        seed_per_position = INSERT_SEED_TRANSFORM_COUNT
    elif edit_kind == "replace":
        seed_per_position = REPLACE_SEED_TRANSFORM_COUNT
    if int(byte_count) not in FORGE_BYTE_COUNTS:
        if int(byte_count) in DIRECT_CRC_BYTE_COUNTS:
            per_position = 1
        elif edit_kind == "insert":
            per_position = INSERT_SEED_TRANSFORM_COUNT
        elif edit_kind == "replace":
            per_position = REPLACE_SEED_TRANSFORM_COUNT
        else:
            per_position = 1
    else:
        per_position = (
            1
            if edit_kind == "remove"
            else _free_index_total(byte_count, free_index_limit) + seed_per_position
        )
    max_positions = max(0, int(max_candidates) // max(1, per_position))
    if free_index_limit is not None:
        max_positions = min(
            sum(window.length for window in windows),
            max_positions,
            AUTO_LIMITED_FREE_INDEX_MAX_POSITIONS,
        )
    if max_positions <= 0:
        return ()
    clipped: list[ForgeWindow] = []
    active_windows = tuple(window for window in windows if window.length > 0)
    if not active_windows:
        return ()
    base_take = max(1, max_positions // len(active_windows))
    remaining = max_positions
    for index, window in enumerate(active_windows):
        if remaining <= 0:
            break
        remaining_windows = len(active_windows) - index
        take = min(window.length, max(base_take, remaining // max(1, remaining_windows)))
        take = min(take, remaining)
        if window.source == "scanline-anomaly":
            if free_index_limit is not None and int(free_index_limit) > 65_536:
                anchor = window.start + min(max(0, int(byte_count)), max(0, window.length - 1))
                start = max(window.start, min(anchor - max(0, take // 2), window.end - take))
            else:
                start = window.start + min(2, max(0, window.length - take))
        else:
            anchor = window.start + max(0, window.length // 2)
            start = max(window.start, min(anchor - max(0, take // 2), window.end - take))
        end = min(window.end, start + take)
        if end > start:
            clipped.append(ForgeWindow(start, end, window.source))
            remaining -= end - start
    return tuple(clipped)


def explain_scan(
    source_data: bytes,
    target_chunk: png.PngChunk,
    *,
    edit_order: tuple[str, ...],
    byte_counts: tuple[int, ...] = TARGET_BYTE_COUNTS,
    window_spec: str | None = None,
    mode: str = "auto",
    max_candidates: int | None = None,
) -> ForgeScanSummary:
    if mode == "off":
        return ForgeScanSummary(False, "CRC-forge disabled.")
    if target_chunk.chunk_type != b"IDAT":
        return ForgeScanSummary(False, "CRC-forge only supports IDAT.")
    if target_chunk.crc == target_chunk.computed_crc:
        return ForgeScanSummary(False, "Stored IDAT CRC already matches current bytes.")
    payload_len = len(target_chunk.data)
    explicit_windows = parse_window_spec(window_spec, payload_len)
    windows = explicit_windows or ranked_auto_windows(source_data, target_chunk)
    if not windows:
        return ForgeScanSummary(False, "No bounded CRC-forge window is available.")
    clean_counts = tuple(count for count in byte_counts if count in TARGET_BYTE_COUNTS)
    if not clean_counts:
        return ForgeScanSummary(False, "No CRC-forge byte count in 1..10 was requested.")
    budget = max_candidates
    if budget is None:
        budget = FORCE_MAX_CANDIDATES if mode == "force" else DEFAULT_MAX_CANDIDATES
    total = 0
    runnable_counts: list[int] = []
    runnable_windows = windows
    for byte_count in clean_counts:
        active_edit_order = (
            _explicit_window_edit_order(edit_order, byte_count)
            if explicit_windows
            else _expanded_edit_order(source_data, edit_order, byte_count)
        )
        for edit_kind in active_edit_order:
            op_windows = clamp_windows_for_operation(windows, payload_len, edit_kind, byte_count)
            if mode != "force":
                free_limit = _auto_free_index_limit(
                    byte_count,
                    mode=mode,
                    explicit_windows=bool(explicit_windows),
                )
                op_windows = _clip_windows_to_candidate_budget(
                    op_windows,
                    edit_kind,
                    byte_count,
                    int(budget),
                    free_index_limit=free_limit,
                )
            else:
                free_limit = None
            count = candidate_count(op_windows, edit_kind, byte_count, free_index_limit=free_limit)
            if count <= 0 or count > int(budget):
                continue
            total += count
            runnable_counts.append(byte_count)
            runnable_windows = op_windows
    if total <= 0:
        return ForgeScanSummary(
            False,
            "CRC-forge candidate budget is too small for the available windows.",
            windows=windows,
            byte_counts=clean_counts,
        )
    return ForgeScanSummary(
        True,
        "CRC-forge targeted pass can run.",
        estimated_candidates=total,
        windows=tuple(_merge_windows(runnable_windows)),
        byte_counts=tuple(dict.fromkeys(runnable_counts)),
    )


def iter_forge_candidates(
    source_data: bytes,
    target_chunk: png.PngChunk,
    old_crc: bytes,
    *,
    edit_order: tuple[str, ...],
    byte_counts: tuple[int, ...] = TARGET_BYTE_COUNTS,
    window_spec: str | None = None,
    mode: str = "auto",
    max_candidates: int | None = None,
    zlib_prefilter: bool = False,
    progress_callback: Callable[[str, int, int, int, int], object] | None = None,
    resume_byte_count: int = 0,
    resume_window_index: int = 0,
    resume_byte_position: int = 0,
    resume_free_index: int = 0,
    resume_edit_kind_index: int = 0,
) -> Iterable[ForgeCandidate]:
    if target_chunk.chunk_type != b"IDAT":
        return
    target_crc = int.from_bytes(old_crc, "big")
    payload = target_chunk.data
    payload_len = len(payload)
    explicit_windows = parse_window_spec(window_spec, payload_len)
    base_windows = explicit_windows or ranked_auto_windows(source_data, target_chunk)
    budget = max_candidates
    if budget is None:
        budget = FORCE_MAX_CANDIDATES if mode == "force" else DEFAULT_MAX_CANDIDATES
    before = source_data[: target_chunk.offset]
    after = source_data[target_chunk.offset + 12 + target_chunk.length :]
    prefixes = crc32_forge.crc32_prefixes(target_chunk.chunk_type, payload)
    required = crc32_forge.crc32_required_before_suffixes(payload, target_crc)
    probe_settings = _zlib_probe_settings(source_data) if zlib_prefilter else None
    tested = 0
    clean_byte_counts = tuple(count for count in byte_counts if count in TARGET_BYTE_COUNTS)
    guided_trace: deflate_probe.DeflateTrace | None = None
    guided_trace_loaded = False

    def get_guided_trace() -> deflate_probe.DeflateTrace | None:
        nonlocal guided_trace, guided_trace_loaded
        if not guided_trace_loaded:
            guided_trace_loaded = True
            try:
                guided_trace = deflate_probe.cached_analyze_deflate_stream(
                    payload,
                    checkpoint_stride=DEFLATE_TRACE_CHECKPOINT_STRIDE,
                )
            except Exception:
                guided_trace = None
        return guided_trace

    for byte_count in clean_byte_counts:
        seed_edit_kinds = (
            _explicit_window_edit_order(edit_order, byte_count)
            if explicit_windows
            else _expanded_edit_order(source_data, edit_order, byte_count)
        )
        for seed_edit_kind_index, seed_edit_kind in enumerate(seed_edit_kinds):
            op_windows = clamp_windows_for_operation(base_windows, payload_len, seed_edit_kind, byte_count)
            estimated = _seed_candidate_count(op_windows, seed_edit_kind, byte_count)
            if estimated <= 0 or estimated > int(budget):
                continue
            for window_index, window in enumerate(op_windows):
                def seed_heartbeat() -> None:
                    if progress_callback is not None:
                        progress_callback(seed_edit_kind, byte_count, window.start, -1, tested)

                probe_checkpoint = (
                    _build_zlib_probe_checkpoint(
                        payload,
                        window.start,
                        probe_settings,
                        heartbeat_callback=seed_heartbeat,
                    )
                    if probe_settings is not None
                    else None
                )
                for position in range(window.start, window.end):
                    suffix_index = position if seed_edit_kind == "insert" else position + byte_count
                    if suffix_index >= len(required):
                        continue
                    if seed_edit_kind == "remove":
                        tested += 1
                        if progress_callback is not None:
                            progress_callback(seed_edit_kind, byte_count, position, 0, tested)
                        if prefixes[position] != required[suffix_index]:
                            continue
                        brute_bytes = payload[position : position + byte_count]
                        if probe_checkpoint is not None and not _zlib_probe_accepts_candidate_before_yield(
                            probe_checkpoint,
                            payload,
                            position,
                            seed_edit_kind,
                            byte_count,
                            brute_bytes,
                            probe_settings,
                        ):
                            continue
                        repaired = payload[:position] + payload[position + byte_count :]
                        yield ForgeCandidate(
                            _candidate_hit(
                                target_chunk,
                                before,
                                after,
                                repaired,
                                old_crc,
                                brute_bytes,
                                seed_edit_kind,
                                seed_edit_kind_index,
                                byte_count,
                                position,
                                window_index,
                            ),
                            byte_count,
                            0,
                        )
                        continue
                    if seed_edit_kind in {"insert", "replace"} and byte_count in DIRECT_CRC_BYTE_COUNTS:
                        tested += 1
                        if progress_callback is not None:
                            progress_callback(seed_edit_kind, byte_count, position, -1, tested)
                        brute_bytes = crc32_forge.solve_crc32_nbyte_transition(
                            prefixes[position],
                            required[suffix_index],
                            byte_count,
                        )
                        if brute_bytes is None:
                            continue
                        if probe_checkpoint is not None and not _zlib_probe_accepts_candidate_before_yield(
                            probe_checkpoint,
                            payload,
                            position,
                            seed_edit_kind,
                            byte_count,
                            brute_bytes,
                            probe_settings,
                        ):
                            continue
                        if seed_edit_kind == "insert":
                            repaired = payload[:position] + brute_bytes + payload[position:]
                        else:
                            repaired = payload[:position] + brute_bytes + payload[position + byte_count :]
                        yield ForgeCandidate(
                            _candidate_hit(
                                target_chunk,
                                before,
                                after,
                                repaired,
                                old_crc,
                                brute_bytes,
                                seed_edit_kind,
                                seed_edit_kind_index,
                                byte_count,
                                position,
                                window_index,
                            ),
                            byte_count,
                            -1,
                        )
                        continue
                    for brute_bytes in _seed_candidates(payload, position, byte_count, seed_edit_kind):
                        tested += 1
                        if progress_callback is not None:
                            progress_callback(seed_edit_kind, byte_count, position, -1, tested)
                        if zlib.crc32(brute_bytes, prefixes[position]) & 0xFFFFFFFF != required[suffix_index]:
                            continue
                        if probe_checkpoint is not None and not _zlib_probe_accepts_candidate_before_yield(
                            probe_checkpoint,
                            payload,
                            position,
                            seed_edit_kind,
                            byte_count,
                            brute_bytes,
                            probe_settings,
                        ):
                            continue
                        if seed_edit_kind == "insert":
                            repaired = payload[:position] + brute_bytes + payload[position:]
                        else:
                            repaired = payload[:position] + brute_bytes + payload[position + byte_count :]
                        yield ForgeCandidate(
                            _candidate_hit(
                                target_chunk,
                                before,
                                after,
                                repaired,
                                old_crc,
                                brute_bytes,
                                seed_edit_kind,
                                seed_edit_kind_index,
                                byte_count,
                                position,
                                window_index,
                            ),
                            byte_count,
                            -1,
                        )

    for byte_count in tuple(
        count for count in clean_byte_counts
        if count in FORGE_BYTE_COUNTS and count not in DIRECT_CRC_BYTE_COUNTS
    ):
        if resume_byte_count and byte_count < resume_byte_count:
            continue
        expanded_edit_order = (
            _explicit_window_edit_order(edit_order, byte_count)
            if explicit_windows
            else _expanded_edit_order(source_data, edit_order, byte_count)
        )
        for edit_kind_index, edit_kind in enumerate(expanded_edit_order):
            if byte_count == resume_byte_count and edit_kind_index < resume_edit_kind_index:
                continue
            if edit_kind == "remove":
                continue
            op_windows = clamp_windows_for_operation(base_windows, payload_len, edit_kind, byte_count)
            if mode != "force":
                free_limit = _auto_free_index_limit(
                    byte_count,
                    mode=mode,
                    explicit_windows=bool(explicit_windows),
                )
                op_windows = _clip_windows_to_candidate_budget(
                    op_windows,
                    edit_kind,
                    byte_count,
                    int(budget),
                    free_index_limit=free_limit,
                )
            else:
                free_limit = None
            estimated = candidate_count(op_windows, edit_kind, byte_count, free_index_limit=free_limit)
            if estimated <= 0 or estimated > int(budget):
                continue
            for window_index, window in enumerate(op_windows):
                def heartbeat() -> None:
                    if progress_callback is not None:
                        progress_callback(edit_kind, byte_count, window.start, 0, tested)

                probe_checkpoint = (
                    _build_zlib_probe_checkpoint(
                        payload,
                        window.start,
                        probe_settings,
                        heartbeat_callback=heartbeat,
                    )
                    if probe_settings is not None
                    else None
                )
                if byte_count == resume_byte_count and edit_kind_index == resume_edit_kind_index and window_index < resume_window_index:
                    continue
                start_position = window.start
                if (
                    byte_count == resume_byte_count
                    and edit_kind_index == resume_edit_kind_index
                    and window_index == resume_window_index
                ):
                    start_position = max(start_position, int(resume_byte_position))
                if edit_kind == "remove":
                    for position in range(start_position, window.end):
                        if (
                            byte_count == resume_byte_count
                            and edit_kind_index == resume_edit_kind_index
                            and window_index == resume_window_index
                            and position == resume_byte_position
                            and resume_free_index > 0
                        ):
                            continue
                        suffix_index = position + byte_count
                        if suffix_index >= len(required):
                            continue
                        tested += 1
                        if progress_callback is not None:
                            progress_callback(edit_kind, byte_count, position, 0, tested)
                        if prefixes[position] != required[suffix_index]:
                            continue
                        removed = payload[position : position + byte_count]
                        if probe_checkpoint is not None and not _zlib_probe_accepts_candidate_before_yield(
                            probe_checkpoint,
                            payload,
                            position,
                            edit_kind,
                            byte_count,
                            removed,
                            probe_settings,
                        ):
                            continue
                        repaired = payload[:position] + payload[position + byte_count :]
                        yield ForgeCandidate(
                            _candidate_hit(
                                target_chunk,
                                before,
                                after,
                                repaired,
                                old_crc,
                                removed,
                                edit_kind,
                                edit_kind_index,
                                byte_count,
                                position,
                                window_index,
                            ),
                            byte_count,
                            0,
                        )
                    continue

                free_len = byte_count - 4
                free_total = _free_index_total(byte_count, free_limit)
                start_free_index = 0
                if (
                    byte_count == resume_byte_count
                    and edit_kind_index == resume_edit_kind_index
                    and window_index == resume_window_index
                ):
                    start_free_index = max(0, int(resume_free_index))
                guided_free_indexes_by_position: dict[int, set[int]] = {}
                guided_full_bytes_by_position: dict[int, set[bytes]] = {}
                run_guided_prefixes = start_free_index <= 0
                if run_guided_prefixes:
                    trace = get_guided_trace()
                    target_output_delta = _guided_target_output_delta(source_data, edit_kind, byte_count)
                    for position in range(start_position, window.end):
                        suffix_index = position if edit_kind == "insert" else position + byte_count
                        if suffix_index >= len(required):
                            continue
                        full_seen = guided_full_bytes_by_position.setdefault(position, set())
                        for brute_bytes in _guided_full_byte_candidates(
                            payload,
                            position,
                            byte_count,
                            trace,
                            target_output_delta,
                        ):
                            if len(brute_bytes) != byte_count or brute_bytes in full_seen:
                                continue
                            full_seen.add(brute_bytes)
                            tested += 1
                            if progress_callback is not None:
                                progress_callback(
                                    edit_kind,
                                    byte_count,
                                    position,
                                    DEFLATE_GUIDED_FULL_INDEX_MARKER,
                                    tested,
                                )
                            if zlib.crc32(brute_bytes, prefixes[position]) & 0xFFFFFFFF != required[suffix_index]:
                                continue
                            if probe_checkpoint is not None and not _zlib_probe_accepts_candidate_before_yield(
                                probe_checkpoint,
                                payload,
                                position,
                                edit_kind,
                                byte_count,
                                brute_bytes,
                                probe_settings,
                            ):
                                continue
                            if edit_kind == "insert":
                                repaired = payload[:position] + brute_bytes + payload[position:]
                            else:
                                repaired = payload[:position] + brute_bytes + payload[position + byte_count :]
                            yield ForgeCandidate(
                                _candidate_hit(
                                    target_chunk,
                                    before,
                                    after,
                                    repaired,
                                    old_crc,
                                    brute_bytes,
                                    edit_kind,
                                    edit_kind_index,
                                    byte_count,
                                    position,
                                    window_index,
                                ),
                                byte_count,
                                DEFLATE_GUIDED_FULL_INDEX_MARKER,
                            )
                        position_seen = guided_free_indexes_by_position.setdefault(position, set())
                        for free_bytes in _guided_free_prefix_candidates(
                            payload,
                            position,
                            free_len,
                            trace,
                            target_output_delta,
                        ):
                            if len(free_bytes) != free_len:
                                continue
                            free_index = int.from_bytes(free_bytes, "big")
                            if free_index in position_seen:
                                continue
                            position_seen.add(free_index)
                            end_crc = required[suffix_index]
                            start_crc = zlib.crc32(free_bytes, prefixes[position]) & 0xFFFFFFFF
                            patch = crc32_forge.forge_crc32_4byte_transition(start_crc, end_crc)
                            brute_bytes = free_bytes + patch
                            tested += 1
                            if progress_callback is not None:
                                progress_callback(
                                    edit_kind,
                                    byte_count,
                                    position,
                                    DEFLATE_GUIDED_FREE_INDEX_MARKER,
                                    tested,
                                )
                            if probe_checkpoint is not None and not _zlib_probe_accepts_candidate_before_yield(
                                probe_checkpoint,
                                payload,
                                position,
                                edit_kind,
                                byte_count,
                                brute_bytes,
                                probe_settings,
                            ):
                                continue
                            if edit_kind == "insert":
                                repaired = payload[:position] + brute_bytes + payload[position:]
                            else:
                                repaired = payload[:position] + brute_bytes + payload[position + byte_count :]
                            yield ForgeCandidate(
                                _candidate_hit(
                                    target_chunk,
                                    before,
                                    after,
                                    repaired,
                                    old_crc,
                                    brute_bytes,
                                    edit_kind,
                                    edit_kind_index,
                                    byte_count,
                                    position,
                                    window_index,
                                ),
                                byte_count,
                                free_index,
                            )
                for free_index in range(start_free_index, free_total):
                    free_bytes = free_index.to_bytes(free_len, "big")
                    for position in range(start_position, window.end):
                        if free_index in guided_free_indexes_by_position.get(position, set()):
                            continue
                        if (
                            byte_count == resume_byte_count
                            and edit_kind_index == resume_edit_kind_index
                            and window_index == resume_window_index
                            and free_index == resume_free_index
                            and position < resume_byte_position
                        ):
                            continue
                        suffix_index = position if edit_kind == "insert" else position + byte_count
                        end_crc = required[suffix_index]
                        start_crc = zlib.crc32(free_bytes, prefixes[position]) & 0xFFFFFFFF
                        patch = crc32_forge.forge_crc32_4byte_transition(start_crc, end_crc)
                        brute_bytes = free_bytes + patch
                        if brute_bytes in guided_full_bytes_by_position.get(position, set()):
                            continue
                        tested += 1
                        if progress_callback is not None:
                            progress_callback(edit_kind, byte_count, position, free_index, tested)
                        if probe_checkpoint is not None and not _zlib_probe_accepts_candidate_before_yield(
                            probe_checkpoint,
                            payload,
                            position,
                            edit_kind,
                            byte_count,
                            brute_bytes,
                            probe_settings,
                        ):
                            continue
                        if edit_kind == "insert":
                            repaired = payload[:position] + brute_bytes + payload[position:]
                        else:
                            repaired = payload[:position] + brute_bytes + payload[position + byte_count :]
                        yield ForgeCandidate(
                            _candidate_hit(
                                target_chunk,
                                before,
                                after,
                                repaired,
                                old_crc,
                                brute_bytes,
                                edit_kind,
                                edit_kind_index,
                                byte_count,
                                position,
                                window_index,
                            ),
                            byte_count,
                            free_index,
                        )


def _candidate_hit(
    target_chunk: png.PngChunk,
    before: bytes,
    after: bytes,
    repaired_payload: bytes,
    old_crc: bytes,
    brute_bytes: bytes,
    edit_kind: str,
    edit_kind_index: int,
    byte_count: int,
    position: int,
    window_index: int,
) -> smash_backend.SmashCandidateHit:
    attempt = bruteforce.prepare_candidate_attempt(
        target_chunk.chunk_type,
        len(repaired_payload).to_bytes(4, "big"),
        repaired_payload,
        repaired_payload,
        before,
        after,
        brute_length=True,
        brute_crc=True,
        old_crc=old_crc,
    )
    return smash_backend.SmashCandidateHit(
        outer_index=window_index,
        length=byte_count * 2,
        inner_index=0,
        brute_bytes=brute_bytes,
        checksum=attempt.checksum,
        full_new_data=attempt.full_new_data,
        png_bytes=attempt.png_bytes,
        old_crc_match=attempt.old_crc_match,
        edit_kind=edit_kind,
        bonus=False,
        byte_position=position,
        edit_kind_index=edit_kind_index,
        stage="crc_forge",
    )
