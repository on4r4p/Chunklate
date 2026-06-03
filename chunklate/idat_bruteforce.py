from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
import hashlib
import itertools
import json
import math
import os
import signal
import time
import zlib
from typing import Callable, Iterable

from . import deflate_header
from . import idat
from . import png


ProgressCallback = Callable[[int, int, bool], None]
QueueProgressCallback = Callable[[str, int, int], None]
UltimateCandidatePreviewCallback = Callable[["SuperMegaLinefeedCandidate", int, int], None]
UNBOUNDED_PROGRESS_TOTAL = 10**12
ULTIMATE_LINEFEED_PROGRESS_STEP = 100
ULTIMATE_LINEFEED_PROGRESS_INTERVAL_SECONDS = 2.0
ULTIMATE_LINEFEED_MIN_BUDGET = 50_000
ULTIMATE_LINEFEED_ETA_CANDIDATES_PER_SECOND = 100
ULTIMATE_LINEFEED_BUDGET_DIVISORS = {
    "quick": 100_000,
    "normal": 50_000,
    "deep": 10_000,
    "very_deep": 1_000,
    "deeeeeeep": 100,
    "abyssal": 10,
    "inception": 2,
}
ULTIMATE_LINEFEED_TOP_CANDIDATES = 5
KNOWN_UNIVERSE_ATOM_ESTIMATE = 10**80
KNOWN_UNIVERSE_ATOM_ESTIMATE_LABEL = "10^80"
ULTIMATE_LINEFEED_PROGRESS_VERSION = 1


@dataclass(frozen=True)
class IdatDeflateCandidate:
    data: bytes
    stream_offset: int
    file_offset: int
    idat_index: int
    idat_offset: int
    old_byte: int
    new_byte: int
    before: idat.IdatStreamAnalysis
    after: idat.IdatStreamAnalysis


@dataclass(frozen=True)
class IdatDeflateProbeResult:
    before: idat.IdatStreamAnalysis
    best: IdatDeflateCandidate | None
    window_start: int
    window_end: int
    tested_candidates: int
    budget_exhausted: bool
    strategy: str = "strict-byte"
    reason: str = ""
    chain: tuple[IdatDeflateCandidate, ...] = ()

    @property
    def improved(self) -> bool:
        return self.best is not None


@dataclass(frozen=True)
class IdatLinefeedInsertCandidate:
    data: bytes
    stream_offset: int
    inserted_byte: int
    before: idat.IdatStreamAnalysis
    after: idat.IdatStreamAnalysis


@dataclass(frozen=True)
class IdatLinefeedInsertProbeResult:
    before: idat.IdatStreamAnalysis
    best: IdatLinefeedInsertCandidate | None
    window_start: int
    window_end: int
    tested_candidates: int
    budget_exhausted: bool
    strategy: str = "linefeed-cr-insert"
    reason: str = ""

    @property
    def improved(self) -> bool:
        return self.best is not None


@dataclass(frozen=True)
class SuperMegaLinefeedOperation:
    kind: str
    stream_offset: int
    old_bytes: bytes = b""
    new_bytes: bytes = b""


@dataclass(frozen=True)
class SuperMegaLinefeedCandidate:
    data: bytes
    operations: tuple[SuperMegaLinefeedOperation, ...]
    before: idat.IdatStreamAnalysis
    after: idat.IdatStreamAnalysis
    state_id: int = 0
    parent_id: int | None = None
    source_offsets: tuple[int, ...] = ()
    score: tuple[int, ...] = ()
    visual_score: float | None = None


@dataclass(frozen=True)
class SuperMegaLinefeedState:
    state_id: int
    parent_id: int | None
    stream: bytes
    operations: tuple[SuperMegaLinefeedOperation, ...]
    analysis: idat.IdatStreamAnalysis
    source_offsets: tuple[int, ...]
    score: tuple[int, ...]


@dataclass(frozen=True)
class SuperMegaLinefeedPhaseSummary:
    name: str
    depth: int
    window_start: int
    window_end: int
    tested_candidates: int
    accepted_candidates: int
    budget_exhausted: bool = False


@dataclass(frozen=True)
class SuperMegaLinefeedProbeResult:
    before: idat.IdatStreamAnalysis
    best: SuperMegaLinefeedCandidate | None
    error_anchor_offset: int | None
    search_start_offset: int
    window_start: int
    window_end: int
    tested_candidates: int
    budget_exhausted: bool
    phases: tuple[SuperMegaLinefeedPhaseSummary, ...] = ()
    strategy: str = "SuperMegaLineFeedForceOfDeath"
    reason: str = ""
    pre_error_backtrack: int = 0
    target_adler: int | None = None
    state_count: int = 0
    visited_count: int = 0
    states: tuple[SuperMegaLinefeedState, ...] = ()

    @property
    def improved(self) -> bool:
        return self.best is not None


@dataclass(frozen=True)
class UltimateLinefeedProbeResult:
    before: idat.IdatStreamAnalysis
    best: SuperMegaLinefeedCandidate | None
    target_adler: int | None
    start_offset: int | None
    reached_depth: int
    max_depth: int
    suspect_offsets: tuple[int, ...]
    tested_candidates: int
    state_count: int
    visited_count: int
    pruned_candidates: int
    resumed_states: int
    checkpoint_path: str
    budget_exhausted: bool
    strategy: str = "UltimateMegaSuperLineFeedBruteForce"
    reason: str = ""
    top_candidates: tuple[SuperMegaLinefeedCandidate, ...] = ()
    reference_path: str = ""
    reference_warning: str = ""
    progress_path: str = ""
    progress_resumed: bool = False
    progress_warning: str = ""

    @property
    def improved(self) -> bool:
        return self.best is not None


@dataclass(frozen=True)
class UltimateLinefeedSearchEstimate:
    before: idat.IdatStreamAnalysis
    target_adler: int | None
    start_offset: int | None
    max_depth: int
    max_offsets: int
    suspect_offsets: tuple[int, ...]
    focused_operation_count: int
    broad_operation_count: int
    operation_count: int
    total_combinations: int
    reason: str = ""


@dataclass(frozen=True)
class UltimateLinefeedBudgetDecision:
    mode: str
    budget: int | None
    divisor: int | None = None
    coverage: float = 0.0
    aborted: bool = False


@dataclass(frozen=True)
class UltimateLinefeedEta:
    candidates_per_second: int
    seconds: float | None
    duration: str
    phrase: str


@dataclass(frozen=True)
class UltimateLinefeedProgress:
    path: str
    source_hash: str
    target_adler: int | None
    start_offset: int | None
    max_depth: int
    max_offsets: int
    operation_pool_hash: str
    focused_operation_pool_hash: str
    broad_operation_pool_hash: str
    phase: str
    depth: int
    pool_index: int
    combination_rank: int
    combination_indices: tuple[int, ...] | None
    tested_candidates: int
    pruned_candidates: int
    state_count: int
    budget: int | None
    timestamp: float


class UltimateLinefeedInterrupted(Exception):
    def __init__(self, progress_path: str):
        self.progress_path = progress_path
        super().__init__("UltimateMegaSuperLineFeedBruteForce interrupted; progress saved to %s" % progress_path)


def analysis_score(analysis: idat.IdatStreamAnalysis) -> tuple[int, int, int, int, int]:
    return (
        1 if analysis.complete else 0,
        analysis.usable_scanlines,
        analysis.complete_scanlines,
        analysis.decompressed_size,
        analysis.error_offset if analysis.error_offset is not None else -1,
    )


def linefeed_insert_score(analysis: idat.IdatStreamAnalysis) -> tuple[int, int, int, int, int]:
    expected_delta = abs(analysis.decompressed_size - analysis.expected_size)
    return (
        1 if analysis.complete else 0,
        analysis.usable_scanlines,
        analysis.complete_scanlines,
        -expected_delta,
        analysis.error_offset if analysis.error_offset is not None else -1,
    )


def super_mega_linefeed_score(
    analysis: idat.IdatStreamAnalysis,
    operation_count: int = 0,
) -> tuple[int, ...]:
    status_rank = {
        "complete": 6,
        "bad_adler": 5,
        "partial": 4,
        "incomplete_stream": 3,
        "corrupt_deflate": 2,
        "bad_zlib_header": 1,
    }.get(analysis.status, 0)
    adler_rank = {
        "adler_match": 4,
        "adler_rebuilt": 3,
        "adler_unknown": 2,
        "adler_mismatch": 1,
    }.get(analysis.adler_status, 0)
    expected_delta = abs(analysis.decompressed_size - analysis.expected_size)
    error_offset = analysis.error_offset if analysis.error_offset is not None else -1
    return (
        1 if analysis.complete else 0,
        status_rank,
        analysis.usable_scanlines,
        analysis.complete_scanlines,
        adler_rank,
        -expected_delta,
        error_offset,
        -operation_count,
    )


def is_material_improvement(before: idat.IdatStreamAnalysis, after: idat.IdatStreamAnalysis) -> bool:
    if not after.supported:
        return False
    if after.complete and not before.complete:
        return True
    if after.usable_scanlines > before.usable_scanlines:
        return True
    return False


def _idat_chunks_and_stream(data: bytes) -> tuple[tuple[png.PngChunk, ...], bytes]:
    chunks = tuple(png.iter_chunks(data))
    idat_chunks = tuple(chunk for chunk in chunks if chunk.chunk_type == b"IDAT")
    return idat_chunks, b"".join(chunk.data for chunk in idat_chunks)


def _all_chunks_and_idat_stream(data: bytes) -> tuple[tuple[png.PngChunk, ...], bytes]:
    chunks = tuple(png.iter_chunks(data))
    idat_stream = b"".join(chunk.data for chunk in chunks if chunk.chunk_type == b"IDAT")
    return chunks, idat_stream


def _locate_idat_stream_offset(
    idat_chunks: tuple[png.PngChunk, ...],
    stream_offset: int,
) -> tuple[png.PngChunk, int, int] | None:
    remaining = stream_offset
    for index, chunk in enumerate(idat_chunks, start=1):
        if remaining < chunk.length:
            return chunk, index, remaining
        remaining -= chunk.length
    return None


def _idat_stream_range_for_chunk_offset(
    chunks: tuple[png.PngChunk, ...],
    chunk_offset: int,
) -> tuple[int, int] | None:
    stream_offset = 0
    for chunk in chunks:
        if chunk.chunk_type != b"IDAT":
            continue
        start = stream_offset
        end = start + chunk.length
        if chunk.offset == chunk_offset:
            return start, end
        stream_offset = end
    return None


def _rebuild_with_single_idat_stream(chunks: tuple[png.PngChunk, ...], idat_stream: bytes) -> bytes:
    rebuilt = bytearray(png.PNG_SIGNATURE)
    idat_written = False
    for chunk in chunks:
        if chunk.chunk_type == b"IDAT":
            if not idat_written:
                rebuilt.extend(png.build_png_chunk(b"IDAT", idat_stream))
                idat_written = True
            continue
        rebuilt.extend(png.build_png_chunk(chunk.chunk_type, chunk.data))
    return bytes(rebuilt)


def _candidate_from_stream(
    parent: SuperMegaLinefeedCandidate,
    chunks: tuple[png.PngChunk, ...],
    new_stream: bytes,
    operation: SuperMegaLinefeedOperation,
    *,
    target_adler: int | None,
    state_id: int,
) -> SuperMegaLinefeedCandidate:
    candidate_data = _rebuild_with_single_idat_stream(chunks, new_stream)
    operations = parent.operations + (operation,)
    source_offsets = parent.source_offsets + (operation.stream_offset,)
    analysis = idat.analyze_idat_stream(
        candidate_data,
        source_kind="candidate_from_original",
        crc_provenance="rebuilt_by_chunklate",
        target_adler=target_adler,
    )
    score = super_mega_linefeed_score(analysis, len(operations))
    return SuperMegaLinefeedCandidate(
        data=candidate_data,
        operations=operations,
        before=parent.before,
        after=analysis,
        state_id=state_id,
        parent_id=parent.state_id,
        source_offsets=source_offsets,
        score=score,
    )


def _stream_offset_for_decompressed_size(idat_stream: bytes, target_size: int) -> int | None:
    if not idat_stream:
        return None
    if target_size <= 0:
        return 0

    decompressor = zlib.decompressobj()
    decompressed_size = 0
    for offset, value in enumerate(idat_stream):
        try:
            decompressed_size += len(decompressor.decompress(bytes((value,))))
        except zlib.error:
            return offset
        if decompressed_size >= target_size:
            return offset

    return len(idat_stream) - 1


def _problem_stream_offset_for_analysis(
    analysis: idat.IdatStreamAnalysis,
    idat_stream: bytes,
) -> int | None:
    if analysis.scanline_size > 0 and analysis.usable_scanlines < analysis.height:
        target_size = analysis.usable_scanlines * analysis.scanline_size + 1
        offset = _stream_offset_for_decompressed_size(idat_stream, target_size)
        if offset is not None:
            return offset
    if analysis.error_offset is not None:
        return min(max(0, analysis.error_offset), max(0, len(idat_stream) - 1))
    if idat_stream:
        return len(idat_stream) - 1
    return None


def first_idat_problem_stream_offset(data: bytes) -> int | None:
    analysis = idat.analyze_idat_stream(data)
    if not analysis.supported:
        return None
    try:
        chunks, idat_stream = _all_chunks_and_idat_stream(data)
    except png.PngFormatError:
        return None
    return _problem_stream_offset_for_analysis(analysis, idat_stream)


def _linefeed_probe_center(before: idat.IdatStreamAnalysis, idat_stream: bytes) -> int | None:
    return _problem_stream_offset_for_analysis(before, idat_stream)


def _probe_linefeed_cr_insertions_in_offsets(
    data: bytes,
    *,
    strategy: str,
    offsets: list[int],
    window_start: int,
    window_end: int,
    budget: int,
    progress: QueueProgressCallback | None = None,
) -> IdatLinefeedInsertProbeResult:
    before = idat.analyze_idat_stream(data)
    try:
        chunks, idat_stream = _all_chunks_and_idat_stream(data)
    except png.PngFormatError as exc:
        return IdatLinefeedInsertProbeResult(before, None, 0, 0, 0, False, strategy, str(exc))

    best: IdatLinefeedInsertCandidate | None = None
    best_score = linefeed_insert_score(before)
    tested = 0
    budget_exhausted = False

    if progress is not None:
        progress(strategy, 0, min(budget, len(offsets)))

    for stream_offset in offsets:
        if tested >= budget:
            budget_exhausted = True
            break

        candidate_stream = idat_stream[:stream_offset] + b"\r" + idat_stream[stream_offset:]
        candidate_data = _rebuild_with_single_idat_stream(chunks, candidate_stream)
        after = idat.analyze_idat_stream(candidate_data)
        tested += 1

        if progress is not None and tested % 100 == 0:
            progress(strategy, tested, min(budget, len(offsets)))

        candidate_score = linefeed_insert_score(after)
        if candidate_score <= best_score:
            continue

        best = IdatLinefeedInsertCandidate(
            data=candidate_data,
            stream_offset=stream_offset,
            inserted_byte=0x0D,
            before=before,
            after=after,
        )
        best_score = candidate_score
        if after.complete:
            break

    if progress is not None:
        progress(strategy, tested, min(budget, len(offsets)))

    return IdatLinefeedInsertProbeResult(
        before,
        best,
        window_start,
        window_end,
        tested,
        budget_exhausted,
        strategy,
    )


def mutate_idat_stream_byte(data: bytes, stream_offset: int, new_byte: int) -> IdatDeflateCandidate | None:
    before = idat.analyze_idat_stream(data)
    if stream_offset < 0:
        return None

    try:
        idat_chunks, idat_stream = _idat_chunks_and_stream(data)
    except png.PngFormatError:
        return None

    if stream_offset >= len(idat_stream):
        return None

    location = _locate_idat_stream_offset(idat_chunks, stream_offset)
    if location is None:
        return None

    chunk, idat_index, idat_offset = location
    old_byte = idat_stream[stream_offset]
    if old_byte == new_byte:
        return None

    file_offset = chunk.offset + 8 + idat_offset
    candidate = bytearray(data)
    candidate[file_offset] = new_byte

    payload_start = chunk.offset + 8
    payload_end = payload_start + chunk.length
    crc_offset = payload_end
    repaired_crc = zlib.crc32(chunk.chunk_type + bytes(candidate[payload_start:payload_end])) & 0xFFFFFFFF
    candidate[crc_offset : crc_offset + 4] = repaired_crc.to_bytes(4, "big")

    candidate_data = bytes(candidate)
    return IdatDeflateCandidate(
        data=candidate_data,
        stream_offset=stream_offset,
        file_offset=file_offset,
        idat_index=idat_index,
        idat_offset=idat_offset,
        old_byte=old_byte,
        new_byte=new_byte,
        before=before,
        after=idat.analyze_idat_stream(candidate_data),
    )


def probe_idat_linefeed_cr_insertions(
    data: bytes,
    *,
    window_radius: int = 4096,
    budget: int = 4096,
    progress: QueueProgressCallback | None = None,
) -> IdatLinefeedInsertProbeResult:
    strategy = "linefeed-cr-insert"
    before = idat.analyze_idat_stream(data)
    if not before.supported:
        return IdatLinefeedInsertProbeResult(before, None, 0, 0, 0, False, strategy, before.reason)
    if before.complete:
        return IdatLinefeedInsertProbeResult(
            before,
            None,
            0,
            0,
            0,
            False,
            strategy,
            "IDAT stream is already complete",
        )

    try:
        _chunks, idat_stream = _all_chunks_and_idat_stream(data)
    except png.PngFormatError as exc:
        return IdatLinefeedInsertProbeResult(before, None, 0, 0, 0, False, strategy, str(exc))

    center = _linefeed_probe_center(before, idat_stream)
    if center is None:
        return IdatLinefeedInsertProbeResult(
            before,
            None,
            0,
            0,
            0,
            False,
            strategy,
            "IDAT stream is missing",
        )

    window_start = max(0, center - window_radius)
    window_end = min(len(idat_stream), center + window_radius + 1)
    offsets = [
        offset
        for offset in range(window_start, window_end)
        if idat_stream[offset] == 0x0A
    ]
    offsets.sort(key=lambda offset: (abs(offset - center), offset))

    return _probe_linefeed_cr_insertions_in_offsets(
        data,
        strategy=strategy,
        offsets=offsets,
        window_start=window_start,
        window_end=window_end,
        budget=budget,
        progress=progress,
    )


def probe_idat_linefeed_cr_insertions_full(
    data: bytes,
    *,
    start_offset: int | None = None,
    budget: int = 1000000,
    progress: QueueProgressCallback | None = None,
) -> IdatLinefeedInsertProbeResult:
    strategy = "linefeed-cr-insert-full"

    def legacy_progress(_stage: str, tested: int, total: int) -> None:
        if progress is not None:
            progress(strategy, tested, total)

    result = probe_super_mega_linefeed_force_of_death(
        data,
        start_offset=start_offset,
        pre_error_backtrack=0,
        beam_width=1,
        max_depth=1,
        linefeed_budget=budget,
        structural_budget=0,
        local_bit_budget=0,
        local_byte_budget=0,
        heavy_byte_budget=0,
        adler_budget=0,
        progress=legacy_progress if progress is not None else None,
    )

    best = None
    if result.best is not None and result.best.operations:
        operation = result.best.operations[-1]
        inserted_byte = operation.new_bytes[0] if operation.new_bytes else 0x0D
        best = IdatLinefeedInsertCandidate(
            data=result.best.data,
            stream_offset=operation.stream_offset,
            inserted_byte=inserted_byte,
            before=result.before,
            after=result.best.after,
        )

    return IdatLinefeedInsertProbeResult(
        result.before,
        best,
        result.search_start_offset,
        result.window_end,
        result.tested_candidates,
        result.budget_exhausted,
        strategy,
        result.reason,
    )


def _analysis_or_anchor_offset(
    analysis: idat.IdatStreamAnalysis,
    idat_stream: bytes,
    anchor: int | None,
) -> int:
    center = _problem_stream_offset_for_analysis(analysis, idat_stream)
    if center is None:
        center = anchor
    if center is None:
        center = 0
    if not idat_stream:
        return 0
    return min(max(0, center), max(0, len(idat_stream) - 1))


def adaptive_pre_error_backtrack(idat_stream_size: int) -> int:
    if idat_stream_size <= 0:
        return 0
    if idat_stream_size < 2048:
        return max(32, idat_stream_size // 4)
    return min(8192, max(512, idat_stream_size // 16))


def _offsets_by_distance(window_start: int, window_end: int, center: int) -> list[int]:
    return sorted(range(window_start, window_end), key=lambda offset: (abs(offset - center), offset))


def _format_optional_offset(offset: int | None) -> str:
    if offset is None:
        return "unknown"
    return "0x%x" % offset


def _format_operation(operation: SuperMegaLinefeedOperation) -> str:
    if operation.old_bytes or operation.new_bytes:
        old_hex = operation.old_bytes.hex() if operation.old_bytes else "-"
        new_hex = operation.new_bytes.hex() if operation.new_bytes else "-"
        return "%s@0x%x:%s>%s" % (operation.kind, operation.stream_offset, old_hex, new_hex)
    return "%s@0x%x" % (operation.kind, operation.stream_offset)


def _stream_state_key(stream: bytes) -> str:
    return hashlib.blake2b(stream, digest_size=16).hexdigest()


def ultimate_linefeed_combination_count(operation_count: int, max_depth: int = 4) -> int:
    operation_count = max(0, int(operation_count))
    max_depth = max(0, int(max_depth))
    return sum(
        math.comb(operation_count, depth)
        for depth in range(1, min(operation_count, max_depth) + 1)
    )


def _format_decimal_scientific(value: Decimal) -> str:
    if value <= 0:
        return "0"
    exponent = value.adjusted()
    mantissa = value.scaleb(-exponent)
    mantissa_text = format(mantissa, ".3g")
    if "." in mantissa_text:
        mantissa_text = mantissa_text.rstrip("0").rstrip(".")
    return "%se%s" % (mantissa_text, exponent)


def ultimate_linefeed_universe_atom_comparison_lines(
    total_combinations: int,
) -> tuple[str, str]:
    total = max(0, int(total_combinations))
    atom_label = KNOWN_UNIVERSE_ATOM_ESTIMATE_LABEL
    atom_line = "known universe atoms: about %s" % atom_label
    if total == 0:
        return atom_line, "combination scale: no candidates estimated"
    if total == KNOWN_UNIVERSE_ATOM_ESTIMATE:
        return atom_line, "combination scale: roughly equal to that"
    if total < KNOWN_UNIVERSE_ATOM_ESTIMATE:
        factor = Decimal(KNOWN_UNIVERSE_ATOM_ESTIMATE) / Decimal(total)
        return (
            atom_line,
            "combination scale: about %s times smaller"
            % _format_decimal_scientific(factor),
        )
    factor = Decimal(total) / Decimal(KNOWN_UNIVERSE_ATOM_ESTIMATE)
    return (
        atom_line,
        "combination scale: about %s times larger" % _format_decimal_scientific(factor),
    )


def ultimate_linefeed_budget_coverage(
    total_combinations: int,
    budget: int | None,
) -> float:
    total = max(0, int(total_combinations))
    if total == 0:
        return 0.0
    if budget is None:
        return 100.0
    return min(100.0, max(0, int(budget)) * 100.0 / total)


ULTIMATE_LINEFEED_ETA_PHRASES: tuple[tuple[int, str], ...] = (
    (1, "Blink and it is gone. Pretend you suffered."),
    (5, "Barely enough time to look dramatic."),
    (15, "Fast enough to keep the coffee untouched."),
    (30, "A tiny detour through the byte swamp."),
    (60, "One minute-ish. The fish is stretching."),
    (300, "A snack-sized brute force."),
    (900, "Long enough to question your choices once."),
    (1_800, "The terminal gets a small monologue."),
    (3_600, "Coffee run territory."),
    (7_200, "Two-hour anime arc, maybe shorter."),
    (21_600, "Half-day dungeon crawl."),
    (43_200, "This is a workday wearing a trench coat."),
    (86_400, "Sleep might happen before the answer."),
    (259_200, "Weekend plans are now negotiable."),
    (604_800, "The fish filed a weekly report."),
    (2_592_000, "Calendar damage detected."),
    (31_536_000, "Seasonal brute force. Bring weather."),
    (315_360_000, "Multi-year archaeology, but with pixels."),
    (3_153_600_000, "We may be older, wiser, and still waiting."),
    (10**18, "We will be dead before this finishes... but who cares."),
)


def ultimate_linefeed_eta_phrase(seconds: float | int | None) -> str:
    if seconds is None:
        return "No finish line. The fish has entered mythology."
    value = max(0.0, float(seconds))
    for threshold, phrase in ULTIMATE_LINEFEED_ETA_PHRASES:
        if value <= threshold:
            return phrase
    return ULTIMATE_LINEFEED_ETA_PHRASES[-1][1]


def ultimate_linefeed_eta_duration(seconds: float | int | None) -> str:
    if seconds is None:
        return "unbounded"
    remaining = int(math.ceil(max(0.0, float(seconds))))
    if remaining == 0:
        return "0s"
    units = (
        ("y", 365 * 24 * 60 * 60),
        ("d", 24 * 60 * 60),
        ("h", 60 * 60),
        ("m", 60),
        ("s", 1),
    )
    parts: list[str] = []
    for suffix, unit_seconds in units:
        if remaining >= unit_seconds:
            value = remaining // unit_seconds
            remaining %= unit_seconds
            parts.append("%s%s" % (value, suffix))
        if len(parts) == 2:
            break
    return " ".join(parts) if parts else "<1s"


def ultimate_linefeed_eta(
    budget: int | None,
    *,
    candidates_per_second: int = ULTIMATE_LINEFEED_ETA_CANDIDATES_PER_SECOND,
) -> UltimateLinefeedEta:
    rate = max(1, int(candidates_per_second))
    seconds = None if budget is None else max(0, int(budget)) / float(rate)
    return UltimateLinefeedEta(
        candidates_per_second=rate,
        seconds=seconds,
        duration=ultimate_linefeed_eta_duration(seconds),
        phrase=ultimate_linefeed_eta_phrase(seconds),
    )


def ultimate_linefeed_budget_from_divisor(
    total_combinations: int,
    divisor: int,
    *,
    min_budget: int = ULTIMATE_LINEFEED_MIN_BUDGET,
) -> int:
    total = max(0, int(total_combinations))
    if total == 0:
        return 0
    budget = math.ceil(total / max(1, int(divisor)))
    return min(total, max(int(min_budget), budget))


def ultimate_linefeed_budget_decision(
    total_combinations: int,
    mode: str = "normal",
    *,
    manual_budget: int | None = None,
) -> UltimateLinefeedBudgetDecision:
    normalized = str(mode or "normal").strip().lower().replace(" ", "_")
    total = max(0, int(total_combinations))
    if normalized in ("abort", "abandon", "quit"):
        return UltimateLinefeedBudgetDecision("abort", None, aborted=True)
    if normalized == "unbounded":
        return UltimateLinefeedBudgetDecision(
            "unbounded",
            None,
            coverage=ultimate_linefeed_budget_coverage(total, None),
        )
    if normalized == "manual":
        if manual_budget is None or int(manual_budget) < 1:
            raise ValueError("manual ultimate linefeed budget must be greater than zero")
        budget = int(manual_budget)
        return UltimateLinefeedBudgetDecision(
            "manual",
            budget,
            coverage=ultimate_linefeed_budget_coverage(total, budget),
        )
    if normalized not in ULTIMATE_LINEFEED_BUDGET_DIVISORS:
        raise ValueError("unknown ultimate linefeed budget mode: %s" % mode)
    divisor = ULTIMATE_LINEFEED_BUDGET_DIVISORS[normalized]
    budget = ultimate_linefeed_budget_from_divisor(total, divisor)
    return UltimateLinefeedBudgetDecision(
        normalized,
        budget,
        divisor=divisor,
        coverage=ultimate_linefeed_budget_coverage(total, budget),
    )


def _weighted_offset(offsets: dict[int, int], stream: bytes, offset: int, weight: int) -> None:
    if not stream:
        return
    clamped = min(max(0, int(offset)), max(0, len(stream) - 1))
    offsets[clamped] = max(offsets.get(clamped, 0), weight)


def ultimate_linefeed_suspect_offsets(
    data: bytes,
    *,
    start_offset: int | None = None,
    super_result: SuperMegaLinefeedProbeResult | None = None,
    max_offsets: int = 128,
    linefeed_window: int | None = None,
) -> tuple[int, ...]:
    before = idat.analyze_idat_stream(data)
    try:
        _chunks, stream = _all_chunks_and_idat_stream(data)
    except png.PngFormatError:
        return ()
    if not stream:
        return ()

    anchor = start_offset
    if anchor is None:
        anchor = _problem_stream_offset_for_analysis(before, stream)
    if anchor is None:
        anchor = 0
    anchor = min(max(0, anchor), max(0, len(stream) - 1))
    backtrack = linefeed_window
    if backtrack is None:
        backtrack = adaptive_pre_error_backtrack(len(stream))
    search_start = max(0, anchor - max(0, int(backtrack)))
    weighted: dict[int, int] = {}

    _weighted_offset(weighted, stream, anchor, 1000)
    if before.error_offset is not None:
        _weighted_offset(weighted, stream, before.error_offset, 950)

    for offset in range(search_start, len(stream)):
        if stream[offset] == 0x0A and not (offset > 0 and stream[offset - 1] == 0x0D):
            distance = abs(offset - anchor)
            _weighted_offset(weighted, stream, offset, max(100, 900 - min(distance, 800)))

    if len(stream) >= 4:
        _weighted_offset(weighted, stream, len(stream) - 4, 850)

    if super_result is not None:
        if super_result.error_anchor_offset is not None:
            _weighted_offset(weighted, stream, super_result.error_anchor_offset, 980)
        if super_result.best is not None:
            for operation in super_result.best.operations:
                _weighted_offset(weighted, stream, operation.stream_offset, 970)
        for state in super_result.states:
            if state.analysis.error_offset is not None:
                _weighted_offset(weighted, stream, state.analysis.error_offset, 780)
            for source_offset in state.source_offsets:
                _weighted_offset(weighted, stream, source_offset, 740)

    return tuple(
        offset
        for offset, _weight in sorted(
            weighted.items(),
            key=lambda item: (-item[1], abs(item[0] - anchor), item[0]),
        )[: max(1, max_offsets)]
    )


def _linefeed_global_mutations(
    stream: bytes,
    *,
    search_start: int,
) -> Iterable[tuple[bytes, SuperMegaLinefeedOperation]]:
    for offset in range(search_start, len(stream)):
        if stream[offset] != 0x0A:
            continue
        if offset > 0 and stream[offset - 1] == 0x0D:
            continue
        yield (
            stream[:offset] + b"\r" + stream[offset:],
            SuperMegaLinefeedOperation("insert-cr-before-lf", offset, b"", b"\r"),
        )


def _count_linefeed_global_mutations(stream: bytes, *, search_start: int) -> int:
    return sum(
        1
        for offset in range(search_start, len(stream))
        if stream[offset] == 0x0A and not (offset > 0 and stream[offset - 1] == 0x0D)
    )


def _known_gap_linefeed_positions(
    stream: bytes,
    *,
    window_start: int,
    window_end: int,
    center: int,
) -> tuple[int, ...]:
    start = min(max(0, window_start), len(stream))
    end = min(max(start, window_end), len(stream))
    positions = [
        offset
        for offset in range(start, end)
        if stream[offset] == 0x0A and not (offset > 0 and stream[offset - 1] == 0x0D)
    ]
    return tuple(sorted(positions, key=lambda offset: (abs(offset - center), offset)))


def _linefeed_known_gap_mutations(
    stream: bytes,
    *,
    gap_size: int,
    window_start: int,
    window_end: int,
    center: int,
) -> Iterable[tuple[bytes, SuperMegaLinefeedOperation]]:
    if gap_size <= 0:
        return
    positions = _known_gap_linefeed_positions(
        stream,
        window_start=window_start,
        window_end=window_end,
        center=center,
    )
    if len(positions) < gap_size:
        return

    operation_kind = "known-gap-insert-%s-crs-before-lfs" % gap_size
    for offsets in itertools.combinations(positions, gap_size):
        candidate = bytearray(stream)
        for offset in sorted(offsets, reverse=True):
            candidate[offset:offset] = b"\r"
        yield (
            bytes(candidate),
            SuperMegaLinefeedOperation(
                operation_kind,
                offsets[0],
                b"",
                b"\r" * gap_size,
            ),
        )


def _count_linefeed_known_gap_mutations(
    stream: bytes,
    *,
    gap_size: int,
    window_start: int,
    window_end: int,
    center: int,
) -> int:
    if gap_size <= 0:
        return 0
    positions = _known_gap_linefeed_positions(
        stream,
        window_start=window_start,
        window_end=window_end,
        center=center,
    )
    if len(positions) < gap_size:
        return 0
    return math.comb(len(positions), gap_size)


def _linefeed_structural_mutations(
    stream: bytes,
    *,
    center: int,
    search_start: int,
    backtrack: int,
    forward: int,
    insert_radius: int,
) -> Iterable[tuple[bytes, SuperMegaLinefeedOperation]]:
    window_start = max(search_start, center - backtrack)
    window_end = min(len(stream), center + forward + 1)
    insert_start = max(search_start, center - insert_radius)
    insert_end = min(len(stream) + 1, center + insert_radius + 1)

    for offset in _offsets_by_distance(insert_start, insert_end, center):
        if offset > 0 and stream[offset - 1] == 0x0D:
            continue
        yield (
            stream[:offset] + b"\r" + stream[offset:],
            SuperMegaLinefeedOperation("insert-cr-near-error", offset, b"", b"\r"),
        )

    for offset in _offsets_by_distance(window_start, window_end, center):
        value = stream[offset]
        if value == 0x0D:
            yield (
                stream[:offset] + stream[offset + 1 :],
                SuperMegaLinefeedOperation("remove-cr", offset, b"\r", b""),
            )
            yield (
                stream[:offset] + b"\n" + stream[offset + 1 :],
                SuperMegaLinefeedOperation("replace-cr-with-lf", offset, b"\r", b"\n"),
            )
        elif value == 0x0A:
            yield (
                stream[:offset] + b"\r" + stream[offset + 1 :],
                SuperMegaLinefeedOperation("replace-lf-with-cr", offset, b"\n", b"\r"),
            )


def _count_linefeed_structural_mutations(
    stream: bytes,
    *,
    center: int,
    search_start: int,
    backtrack: int,
    forward: int,
    insert_radius: int,
) -> int:
    window_start = max(search_start, center - backtrack)
    window_end = min(len(stream), center + forward + 1)
    insert_start = max(search_start, center - insert_radius)
    insert_end = min(len(stream) + 1, center + insert_radius + 1)
    count = sum(1 for offset in range(insert_start, insert_end) if not (offset > 0 and stream[offset - 1] == 0x0D))
    for offset in range(window_start, window_end):
        if stream[offset] == 0x0D:
            count += 2
        elif stream[offset] == 0x0A:
            count += 1
    return count


def _bit_flip_mutations(
    stream: bytes,
    *,
    center: int,
    backtrack: int,
    forward: int,
) -> Iterable[tuple[bytes, SuperMegaLinefeedOperation]]:
    window_start = max(0, center - backtrack)
    window_end = min(len(stream), center + forward + 1)
    for offset in _offsets_by_distance(window_start, window_end, center):
        old_byte = stream[offset]
        for bit in range(8):
            new_byte = old_byte ^ (1 << bit)
            yield (
                stream[:offset] + bytes((new_byte,)) + stream[offset + 1 :],
                SuperMegaLinefeedOperation("bit-flip", offset, bytes((old_byte,)), bytes((new_byte,))),
            )


def _byte_replace_mutations(
    stream: bytes,
    *,
    center: int,
    backtrack: int,
    forward: int,
    kind: str,
) -> Iterable[tuple[bytes, SuperMegaLinefeedOperation]]:
    window_start = max(0, center - backtrack)
    window_end = min(len(stream), center + forward + 1)
    for offset in _offsets_by_distance(window_start, window_end, center):
        old_byte = stream[offset]
        for new_byte in range(256):
            if new_byte == old_byte:
                continue
            yield (
                stream[:offset] + bytes((new_byte,)) + stream[offset + 1 :],
                SuperMegaLinefeedOperation(kind, offset, bytes((old_byte,)), bytes((new_byte,))),
            )


def _adler_target_mutations(
    stream: bytes,
    *,
    target_adler: int | None,
    computed_adler: int | None,
) -> Iterable[tuple[bytes, SuperMegaLinefeedOperation]]:
    if len(stream) < 4:
        return

    current = stream[-4:]
    if target_adler is not None:
        target = target_adler.to_bytes(4, "big")
        if target != current:
            yield (
                stream[:-4] + target,
                SuperMegaLinefeedOperation(
                    "set-zlib-trailer-to-target-adler",
                    len(stream) - 4,
                    current,
                    target,
                ),
            )

    if computed_adler is not None:
        computed = computed_adler.to_bytes(4, "big")
        if computed != current and (target_adler is None or computed_adler != target_adler):
            yield (
                stream[:-4] + computed,
                SuperMegaLinefeedOperation(
                    "set-zlib-trailer-to-computed-adler",
                    len(stream) - 4,
                    current,
                    computed,
                ),
            )


def _count_adler_target_mutations(
    stream: bytes,
    *,
    target_adler: int | None,
    computed_adler: int | None,
) -> int:
    return sum(
        1
        for _stream, _operation in _adler_target_mutations(
            stream,
            target_adler=target_adler,
            computed_adler=computed_adler,
        )
    )


def _operation_to_json(operation: SuperMegaLinefeedOperation) -> dict[str, object]:
    return {
        "kind": operation.kind,
        "stream_offset": operation.stream_offset,
        "old": operation.old_bytes.hex(),
        "new": operation.new_bytes.hex(),
    }


def _operation_from_json(record: object) -> SuperMegaLinefeedOperation | None:
    if not isinstance(record, dict):
        return None
    try:
        return SuperMegaLinefeedOperation(
            str(record["kind"]),
            int(record["stream_offset"]),
            bytes.fromhex(str(record.get("old", ""))),
            bytes.fromhex(str(record.get("new", ""))),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _apply_linefeed_operation(stream: bytes, operation: SuperMegaLinefeedOperation) -> bytes | None:
    offset = operation.stream_offset
    if offset < 0 or offset > len(stream):
        return None
    old = operation.old_bytes
    new = operation.new_bytes
    if old:
        if offset + len(old) > len(stream) or stream[offset : offset + len(old)] != old:
            return None
        return stream[:offset] + new + stream[offset + len(old) :]
    return stream[:offset] + new + stream[offset:]


def _replay_operations(stream: bytes, operations: tuple[SuperMegaLinefeedOperation, ...]) -> bytes | None:
    current = stream
    for operation in operations:
        current = _apply_linefeed_operation(current, operation)
        if current is None:
            return None
    return current


def _append_ultimate_checkpoint(
    checkpoint_path: str,
    *,
    source_hash: str,
    candidate: SuperMegaLinefeedCandidate,
    depth: int,
) -> None:
    if not checkpoint_path:
        return
    try:
        directory = os.path.dirname(checkpoint_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(checkpoint_path, "a", encoding="utf-8") as file:
            file.write(
                json.dumps(
                    {
                        "source_hash": source_hash,
                        "stream_hash": _stream_state_key(
                            b"".join(
                                chunk.data
                                for chunk in png.iter_chunks(candidate.data)
                                if chunk.chunk_type == b"IDAT"
                            )
                        ),
                        "state_id": candidate.state_id,
                        "parent_id": candidate.parent_id,
                        "depth": depth,
                        "operations": [
                            _operation_to_json(operation)
                            for operation in candidate.operations
                        ],
                        "score": list(candidate.score),
                        "status": candidate.after.status,
                        "adler_status": candidate.after.adler_status,
                        "usable_scanlines": candidate.after.usable_scanlines,
                        "error_offset": candidate.after.error_offset,
                    },
                    sort_keys=True,
                )
                + "\n"
            )
    except OSError:
        return


def _load_ultimate_checkpoint(
    checkpoint_path: str,
    *,
    source_hash: str,
    root_stream: bytes,
    chunks: tuple[png.PngChunk, ...],
    before: idat.IdatStreamAnalysis,
    target_adler: int | None,
    progress: QueueProgressCallback | None = None,
    progress_total: int = 0,
    progress_stage: str = "UltimateMegaSuperLineFeedBruteForce",
) -> tuple[list[SuperMegaLinefeedCandidate], set[str], int, int]:
    if not checkpoint_path or not os.path.exists(checkpoint_path):
        return [], set(), 1, 0

    loaded: list[SuperMegaLinefeedCandidate] = []
    visited: set[str] = set()
    next_state_id = 1
    last_progress_at = time.monotonic()

    def emit_load_progress(force: bool = False) -> None:
        nonlocal last_progress_at
        if progress is None:
            return
        now = time.monotonic()
        if not force and now - last_progress_at < ULTIMATE_LINEFEED_PROGRESS_INTERVAL_SECONDS:
            return
        last_progress_at = now
        progress(
            progress_stage,
            min(len(loaded), max(1, int(progress_total))),
            max(1, int(progress_total)),
        )

    try:
        with open(checkpoint_path, "r", encoding="utf-8") as file:
            for line in file:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if record.get("source_hash") != source_hash:
                    continue
                operations = tuple(
                    operation
                    for operation in (
                        _operation_from_json(item)
                        for item in record.get("operations", [])
                    )
                    if operation is not None
                )
                stream = _replay_operations(root_stream, operations)
                if stream is None:
                    continue
                stream_hash = _stream_state_key(stream)
                if stream_hash in visited:
                    continue
                visited.add(stream_hash)
                state_id = int(record.get("state_id", next_state_id))
                next_state_id = max(next_state_id, state_id + 1)
                candidate_data = _rebuild_with_single_idat_stream(chunks, stream)
                analysis = idat.analyze_idat_stream(
                    candidate_data,
                    source_kind="candidate_from_original",
                    crc_provenance="rebuilt_by_chunklate",
                    target_adler=target_adler,
                )
                score = super_mega_linefeed_score(analysis, len(operations))
                loaded.append(
                    SuperMegaLinefeedCandidate(
                        candidate_data,
                        operations,
                        before,
                        analysis,
                        state_id=state_id,
                        parent_id=record.get("parent_id"),
                        source_offsets=tuple(operation.stream_offset for operation in operations),
                        score=score,
                    )
                )
                emit_load_progress()
    except OSError:
        return [], set(), 1, 0

    emit_load_progress(force=bool(loaded))
    return loaded, visited, next_state_id, len(loaded)


def ultimate_linefeed_progress_path_from_checkpoint(checkpoint_path: str) -> str:
    if not checkpoint_path:
        return ""
    if checkpoint_path.endswith(".checkpoint.jsonl"):
        return checkpoint_path[: -len(".checkpoint.jsonl")] + ".progress.json"
    return checkpoint_path + ".progress.json"


def _ultimate_operation_pool_hash(operation_pool: tuple[SuperMegaLinefeedOperation, ...]) -> str:
    payload = json.dumps(
        [_operation_to_json(operation) for operation in operation_pool],
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.blake2b(payload, digest_size=16).hexdigest()


def _progress_target_matches(record: dict[str, object], key: str, expected: object) -> bool:
    return record.get(key) == expected


def _coerce_progress_indices(value: object) -> tuple[int, ...] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        return None
    try:
        return tuple(int(item) for item in value)
    except (TypeError, ValueError):
        return None


def _load_ultimate_progress(
    progress_path: str,
    *,
    source_hash: str,
    target_adler: int | None,
    start_offset: int | None,
    max_depth: int,
    max_offsets: int,
    operation_pool_hash: str,
    focused_operation_pool_hash: str,
    broad_operation_pool_hash: str,
) -> tuple[UltimateLinefeedProgress | None, str]:
    if not progress_path or not os.path.exists(progress_path):
        return None, ""
    try:
        with open(progress_path, "r", encoding="utf-8") as file:
            record = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        return None, "could not load ultimate progress checkpoint %s: %s" % (progress_path, exc)
    if not isinstance(record, dict):
        return None, "ultimate progress checkpoint %s is not a JSON object" % progress_path
    expected = {
        "version": ULTIMATE_LINEFEED_PROGRESS_VERSION,
        "source_hash": source_hash,
        "target_adler": target_adler,
        "start_offset": start_offset,
        "max_depth": max_depth,
        "max_offsets": max_offsets,
        "operation_pool_hash": operation_pool_hash,
        "focused_operation_pool_hash": focused_operation_pool_hash,
        "broad_operation_pool_hash": broad_operation_pool_hash,
    }
    for key, value in expected.items():
        if not _progress_target_matches(record, key, value):
            return None, "ultimate progress checkpoint %s does not match this run (%s mismatch)" % (progress_path, key)
    try:
        return (
            UltimateLinefeedProgress(
                progress_path,
                source_hash,
                target_adler,
                start_offset,
                max_depth,
                max_offsets,
                operation_pool_hash,
                focused_operation_pool_hash,
                broad_operation_pool_hash,
                str(record.get("phase", "")),
                int(record.get("depth", 0)),
                int(record.get("pool_index", 0)),
                int(record.get("combination_rank", 0)),
                _coerce_progress_indices(record.get("combination_indices")),
                int(record.get("tested_candidates", 0)),
                int(record.get("pruned_candidates", 0)),
                int(record.get("state_count", 1)),
                None if record.get("budget") is None else int(record.get("budget", 0)),
                float(record.get("timestamp", 0.0)),
            ),
            "",
        )
    except (TypeError, ValueError) as exc:
        return None, "ultimate progress checkpoint %s has invalid fields: %s" % (progress_path, exc)


def _write_ultimate_progress(
    progress_path: str,
    *,
    source_hash: str,
    target_adler: int | None,
    start_offset: int | None,
    max_depth: int,
    max_offsets: int,
    operation_pool_hash: str,
    focused_operation_pool_hash: str,
    broad_operation_pool_hash: str,
    phase: str,
    depth: int,
    pool_index: int,
    combination_rank: int,
    combination_indices: tuple[int, ...] | None,
    tested_candidates: int,
    pruned_candidates: int,
    state_count: int,
    budget: int | None,
) -> None:
    if not progress_path:
        return
    try:
        directory = os.path.dirname(progress_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        tmp_path = progress_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as file:
            json.dump(
                {
                    "version": ULTIMATE_LINEFEED_PROGRESS_VERSION,
                    "source_hash": source_hash,
                    "target_adler": target_adler,
                    "start_offset": start_offset,
                    "max_depth": max_depth,
                    "max_offsets": max_offsets,
                    "operation_pool_hash": operation_pool_hash,
                    "focused_operation_pool_hash": focused_operation_pool_hash,
                    "broad_operation_pool_hash": broad_operation_pool_hash,
                    "phase": phase,
                    "depth": depth,
                    "pool_index": pool_index,
                    "combination_rank": combination_rank,
                    "combination_indices": None if combination_indices is None else list(combination_indices),
                    "tested_candidates": tested_candidates,
                    "pruned_candidates": pruned_candidates,
                    "state_count": state_count,
                    "budget": budget,
                    "timestamp": time.time(),
                },
                file,
                sort_keys=True,
            )
            file.write("\n")
        os.replace(tmp_path, progress_path)
    except OSError:
        return


def _next_combination_indices(indices: tuple[int, ...], n: int, r: int) -> tuple[int, ...] | None:
    if r <= 0 or n < r:
        return None
    values = list(indices)
    for position in range(r - 1, -1, -1):
        if values[position] != position + n - r:
            values[position] += 1
            for next_position in range(position + 1, r):
                values[next_position] = values[next_position - 1] + 1
            return tuple(values)
    return None


def _combination_rank(indices: tuple[int, ...], n: int, r: int) -> int:
    rank = 0
    previous = -1
    for position, value in enumerate(indices):
        for candidate in range(previous + 1, value):
            rank += math.comb(n - candidate - 1, r - position - 1)
        previous = value
    return rank


def _combination_indices_from(
    n: int,
    r: int,
    start_indices: tuple[int, ...] | None = None,
) -> Iterable[tuple[int, ...]]:
    if r <= 0 or n < r:
        return
    indices = tuple(range(r)) if start_indices is None else tuple(start_indices)
    if len(indices) != r or any(index < 0 or index >= n for index in indices):
        indices = tuple(range(r))
    while indices is not None:
        yield indices
        indices = _next_combination_indices(indices, n, r)


def _ultimate_mutations_for_offset(
    stream: bytes,
    offset: int,
    *,
    target_adler: int | None = None,
    computed_adler: int | None = None,
) -> Iterable[tuple[bytes, SuperMegaLinefeedOperation]]:
    if offset < 0 or offset >= len(stream):
        return

    if offset == max(0, len(stream) - 4):
        yield from _adler_target_mutations(
            stream,
            target_adler=target_adler,
            computed_adler=computed_adler,
        )

    value = stream[offset]
    if value == 0x0A and not (offset > 0 and stream[offset - 1] == 0x0D):
        yield (
            stream[:offset] + b"\r" + stream[offset:],
            SuperMegaLinefeedOperation("ultimate-insert-cr-before-lf", offset, b"", b"\r"),
        )
        yield (
            stream[:offset] + b"\r" + stream[offset + 1 :],
            SuperMegaLinefeedOperation("ultimate-replace-lf-with-cr", offset, b"\n", b"\r"),
        )
    elif value == 0x0D:
        yield (
            stream[:offset] + stream[offset + 1 :],
            SuperMegaLinefeedOperation("ultimate-remove-cr", offset, b"\r", b""),
        )
        yield (
            stream[:offset] + b"\n" + stream[offset + 1 :],
            SuperMegaLinefeedOperation("ultimate-replace-cr-with-lf", offset, b"\r", b"\n"),
        )


def _ultimate_operation_pool(
    stream: bytes,
    suspect_offsets: tuple[int, ...],
    *,
    target_adler: int | None,
    computed_adler: int | None,
) -> tuple[SuperMegaLinefeedOperation, ...]:
    operations: list[SuperMegaLinefeedOperation] = []
    seen: set[tuple[str, int, bytes, bytes]] = set()
    for offset in suspect_offsets:
        for _candidate_stream, operation in _ultimate_mutations_for_offset(
            stream,
            offset,
            target_adler=target_adler,
            computed_adler=computed_adler,
        ):
            key = (
                operation.kind,
                operation.stream_offset,
                operation.old_bytes,
                operation.new_bytes,
            )
            if key in seen:
                continue
            seen.add(key)
            operations.append(operation)
    return tuple(operations)


def _ultimate_exhaustive_linefeed_offsets(
    stream: bytes,
    *,
    suspect_offsets: tuple[int, ...],
    anchor: int | None,
    max_offsets: int,
) -> tuple[int, ...]:
    if not stream or max_offsets <= 0:
        return ()
    if anchor is None:
        anchor = suspect_offsets[0] if suspect_offsets else 0
    anchor = min(max(0, int(anchor)), max(0, len(stream) - 1))

    weighted: dict[int, int] = {}
    for index, offset in enumerate(suspect_offsets):
        if 0 <= offset < len(stream):
            weighted[offset] = max(weighted.get(offset, 0), 100000 - index)

    for offset, value in enumerate(stream):
        if value not in (0x0A, 0x0D):
            continue
        distance = abs(offset - anchor)
        after_anchor_bonus = 4000 if offset >= anchor else 0
        crlf_bonus = 2000 if value == 0x0A and not (offset > 0 and stream[offset - 1] == 0x0D) else 0
        weighted[offset] = max(
            weighted.get(offset, 0),
            10000 + after_anchor_bonus + crlf_bonus - min(distance, 9000),
        )

    if len(stream) >= 4:
        weighted[len(stream) - 4] = max(weighted.get(len(stream) - 4, 0), 95000)

    return tuple(
        offset
        for offset, _weight in sorted(
            weighted.items(),
            key=lambda item: (-item[1], abs(item[0] - anchor), item[0]),
        )[:max_offsets]
    )


def _merge_ultimate_operations(
    *operation_groups: tuple[SuperMegaLinefeedOperation, ...],
) -> tuple[SuperMegaLinefeedOperation, ...]:
    merged: list[SuperMegaLinefeedOperation] = []
    seen: set[tuple[str, int, bytes, bytes]] = set()
    for operations in operation_groups:
        for operation in operations:
            key = (
                operation.kind,
                operation.stream_offset,
                operation.old_bytes,
                operation.new_bytes,
            )
            if key in seen:
                continue
            seen.add(key)
            merged.append(operation)
    return tuple(merged)


def estimate_ultimate_linefeed_search(
    data: bytes,
    *,
    start_offset: int | None = None,
    target_adler: int | None = None,
    super_result: SuperMegaLinefeedProbeResult | None = None,
    max_depth: int = 4,
    max_offsets: int = 128,
) -> UltimateLinefeedSearchEstimate:
    before = idat.analyze_idat_stream(data)
    if target_adler is None:
        target_adler = before.stored_adler
    empty = UltimateLinefeedSearchEstimate(
        before,
        target_adler,
        start_offset,
        max_depth,
        max_offsets,
        (),
        0,
        0,
        0,
        0,
    )
    if not before.supported:
        return replace(empty, reason=before.reason)
    try:
        _chunks, root_stream = _all_chunks_and_idat_stream(data)
    except png.PngFormatError as exc:
        return replace(empty, reason=str(exc))
    if not root_stream:
        return replace(empty, reason="IDAT stream is missing")

    suspect_offsets = ultimate_linefeed_suspect_offsets(
        data,
        start_offset=start_offset,
        super_result=super_result,
        max_offsets=max_offsets,
    )
    focused_operation_pool = _ultimate_operation_pool(
        root_stream,
        suspect_offsets,
        target_adler=target_adler,
        computed_adler=before.computed_adler,
    )
    broad_offsets = _ultimate_exhaustive_linefeed_offsets(
        root_stream,
        suspect_offsets=suspect_offsets,
        anchor=start_offset,
        max_offsets=max(max_offsets, min(len(root_stream), max_offsets * 8, 2048)),
    )
    broad_operation_pool = _ultimate_operation_pool(
        root_stream,
        broad_offsets,
        target_adler=target_adler,
        computed_adler=before.computed_adler,
    )
    operation_pool = _merge_ultimate_operations(focused_operation_pool, broad_operation_pool)
    total = ultimate_linefeed_combination_count(len(operation_pool), max_depth)
    return UltimateLinefeedSearchEstimate(
        before,
        target_adler,
        start_offset,
        max_depth,
        max_offsets,
        suspect_offsets,
        len(focused_operation_pool),
        len(broad_operation_pool),
        len(operation_pool),
        total,
    )


def _normalize_ultimate_operation_sequence(
    operations: tuple[SuperMegaLinefeedOperation, ...],
) -> tuple[SuperMegaLinefeedOperation, ...]:
    return tuple(
        sorted(
            operations,
            key=lambda operation: (
                operation.stream_offset,
                len(operation.old_bytes),
                operation.kind,
            ),
            reverse=True,
        )
    )


def _ultimate_prune_reason(
    parent: idat.IdatStreamAnalysis,
    candidate: idat.IdatStreamAnalysis,
) -> str | None:
    if not candidate.supported:
        return "unsupported"
    if parent.status != "bad_zlib_header" and candidate.status == "bad_zlib_header":
        return "bad_zlib_header"
    if candidate.usable_scanlines + 1 < parent.usable_scanlines:
        return "scanline_regression"
    if (
        parent.error_offset is not None
        and candidate.error_offset is not None
        and candidate.error_offset + 256 < parent.error_offset
    ):
        return "error_offset_regression"
    if (
        parent.expected_size
        and candidate.decompressed_size
        and parent.decompressed_size
        and abs(candidate.decompressed_size - parent.expected_size)
        > abs(parent.decompressed_size - parent.expected_size) + parent.scanline_size
    ):
        return "decompressed_size_regression"
    return None


def _ultimate_prune_is_fatal(reason: str | None, depth: int) -> bool:
    if reason is None:
        return False
    if reason in ("unsupported", "bad_zlib_header"):
        return True
    return depth > 2


def _load_ultimate_reference_image(reference_path: str):
    if not reference_path:
        return None, ""
    try:
        from PIL import Image

        image = Image.open(reference_path).convert("RGBA")
        image.load()
        return image, ""
    except Exception as exc:  # pragma: no cover - exact Pillow failures vary.
        return None, "could not load visual reference %s: %s" % (reference_path, exc)


def _ultimate_visual_distance(candidate_data: bytes, reference_image) -> float | None:
    if reference_image is None:
        return None
    try:
        from io import BytesIO
        from PIL import Image, ImageChops, ImageStat

        candidate = Image.open(BytesIO(candidate_data)).convert("RGBA")
        candidate.load()
        if candidate.size != reference_image.size:
            return float("inf")
        diff = ImageChops.difference(candidate, reference_image)
        return float(sum(ImageStat.Stat(diff).mean))
    except Exception:
        return None


def _attach_ultimate_visual_score(
    candidate: SuperMegaLinefeedCandidate,
    reference_image,
) -> SuperMegaLinefeedCandidate:
    score = _ultimate_visual_distance(candidate.data, reference_image)
    if score is None:
        return candidate
    return replace(candidate, visual_score=score)


def _preview_ultimate_candidate_if_valid(
    candidate: SuperMegaLinefeedCandidate,
    tested: int,
    progress_total: int,
    candidate_preview: UltimateCandidatePreviewCallback | None,
) -> None:
    if candidate_preview is None:
        return
    if not candidate.after.supported or not candidate.after.complete:
        return
    try:
        candidate_preview(candidate, tested, progress_total)
    except Exception:
        return


def _ultimate_top_candidate_key(candidate: SuperMegaLinefeedCandidate) -> str:
    return hashlib.blake2b(candidate.data, digest_size=16).hexdigest()


def _ultimate_top_candidate_rank(candidate: SuperMegaLinefeedCandidate) -> tuple[object, ...]:
    visual_score = candidate.visual_score
    return (
        0 if candidate.after.adler_status == "adler_match" else 1,
        0 if candidate.after.complete else 1,
        -candidate.after.usable_scanlines,
        -candidate.after.complete_scanlines,
        visual_score is None,
        float("inf") if visual_score is None else visual_score,
        -(candidate.score or super_mega_linefeed_score(candidate.after, len(candidate.operations)))[0],
        len(candidate.operations),
        candidate.state_id,
    )


def _remember_ultimate_top_candidate(
    candidates: tuple[SuperMegaLinefeedCandidate, ...],
    candidate: SuperMegaLinefeedCandidate,
    *,
    limit: int = ULTIMATE_LINEFEED_TOP_CANDIDATES,
) -> tuple[SuperMegaLinefeedCandidate, ...]:
    if not candidate.after.supported:
        return candidates
    if not candidate.after.complete and candidate.after.usable_scanlines <= 0:
        return candidates
    by_key = {_ultimate_top_candidate_key(item): item for item in candidates}
    key = _ultimate_top_candidate_key(candidate)
    existing = by_key.get(key)
    if existing is None or _ultimate_top_candidate_rank(candidate) < _ultimate_top_candidate_rank(existing):
        by_key[key] = candidate
    return tuple(sorted(by_key.values(), key=_ultimate_top_candidate_rank)[:limit])


def probe_ultimate_mega_super_linefeed_bruteforce(
    data: bytes,
    *,
    start_offset: int | None = None,
    target_adler: int | None = None,
    super_result: SuperMegaLinefeedProbeResult | None = None,
    checkpoint_path: str = "",
    max_depth: int = 4,
    beam_width: int = 32,
    max_offsets: int = 128,
    budget: int | None = 50000,
    reference_path: str = "",
    progress: QueueProgressCallback | None = None,
    candidate_preview: UltimateCandidatePreviewCallback | None = None,
    progress_path: str = "",
    resume_progress: bool = True,
) -> UltimateLinefeedProbeResult:
    strategy = "UltimateMegaSuperLineFeedBruteForce"
    reference_image, reference_warning = _load_ultimate_reference_image(reference_path)
    budget_limit = None if budget is None else max(0, int(budget))
    progress_total = UNBOUNDED_PROGRESS_TOTAL if budget_limit is None else max(1, budget_limit)
    before = idat.analyze_idat_stream(data)
    if not before.supported:
        return UltimateLinefeedProbeResult(
            before,
            None,
            target_adler,
            start_offset,
            0,
            max_depth,
            (),
            0,
            0,
            0,
            0,
            0,
            checkpoint_path,
            False,
            strategy,
            before.reason,
        )
    if target_adler is None:
        target_adler = before.stored_adler
    if before.complete:
        targeted_before = before
        if target_adler is not None and before.computed_adler is not None:
            targeted_before = idat.analyze_idat_stream(data, target_adler=target_adler)
        if target_adler is None or targeted_before.adler_status == "adler_match":
            return UltimateLinefeedProbeResult(
                targeted_before,
                None,
                target_adler,
                start_offset,
                0,
                max_depth,
                (),
                0,
                1,
                1,
                0,
                0,
                checkpoint_path,
                False,
                strategy,
                "IDAT stream is already complete with matching Adler",
            )

    try:
        chunks, root_stream = _all_chunks_and_idat_stream(data)
    except png.PngFormatError as exc:
        return UltimateLinefeedProbeResult(
            before,
            None,
            target_adler,
            start_offset,
            0,
            max_depth,
            (),
            0,
            0,
            0,
            0,
            0,
            checkpoint_path,
            False,
            strategy,
            str(exc),
        )

    suspect_offsets = ultimate_linefeed_suspect_offsets(
        data,
        start_offset=start_offset,
        super_result=super_result,
        max_offsets=max_offsets,
    )
    source_hash = _stream_state_key(root_stream)
    focused_operation_pool = _ultimate_operation_pool(
        root_stream,
        suspect_offsets,
        target_adler=target_adler,
        computed_adler=before.computed_adler,
    )
    broad_offsets = _ultimate_exhaustive_linefeed_offsets(
        root_stream,
        suspect_offsets=suspect_offsets,
        anchor=start_offset,
        max_offsets=max(max_offsets, min(len(root_stream), max_offsets * 8, 2048)),
    )
    broad_operation_pool = _ultimate_operation_pool(
        root_stream,
        broad_offsets,
        target_adler=target_adler,
        computed_adler=before.computed_adler,
    )
    merged_operation_pool = _merge_ultimate_operations(focused_operation_pool, broad_operation_pool)
    operation_pool_hash = _ultimate_operation_pool_hash(merged_operation_pool)
    focused_operation_pool_hash = _ultimate_operation_pool_hash(focused_operation_pool)
    broad_operation_pool_hash = _ultimate_operation_pool_hash(broad_operation_pool)
    if not progress_path:
        progress_path = ultimate_linefeed_progress_path_from_checkpoint(checkpoint_path)
    root_score = super_mega_linefeed_score(before, 0)
    root = SuperMegaLinefeedCandidate(
        data,
        (),
        before,
        before,
        state_id=0,
        parent_id=None,
        source_offsets=(),
        score=root_score,
    )
    if progress is not None:
        progress(strategy, 0, progress_total)
    checkpoint_candidates, checkpoint_visited, next_state_id, resumed_states = _load_ultimate_checkpoint(
        checkpoint_path,
        source_hash=source_hash,
        root_stream=root_stream,
        chunks=chunks,
        before=before,
        target_adler=target_adler,
        progress=progress,
        progress_total=progress_total,
        progress_stage=strategy,
    )
    checkpoint_candidates = [
        _attach_ultimate_visual_score(candidate, reference_image)
        for candidate in checkpoint_candidates
    ]
    visited = {_stream_state_key(root_stream), *checkpoint_visited}
    frontier = checkpoint_candidates[-beam_width:] if checkpoint_candidates else [root]
    best: SuperMegaLinefeedCandidate | None = None
    best_score = root_score
    top_candidates: tuple[SuperMegaLinefeedCandidate, ...] = ()
    for candidate in checkpoint_candidates:
        top_candidates = _remember_ultimate_top_candidate(top_candidates, candidate)
        candidate_score = candidate.score or super_mega_linefeed_score(candidate.after, len(candidate.operations))
        if candidate_score > best_score:
            best = candidate
            best_score = candidate_score

    tested = 0
    pruned = 0
    budget_exhausted = False
    reached_depth = 0
    progress_warning = ""
    progress_resume = None
    if resume_progress:
        progress_resume, progress_warning = _load_ultimate_progress(
            progress_path,
            source_hash=source_hash,
            target_adler=target_adler,
            start_offset=start_offset,
            max_depth=max_depth,
            max_offsets=max_offsets,
            operation_pool_hash=operation_pool_hash,
            focused_operation_pool_hash=focused_operation_pool_hash,
            broad_operation_pool_hash=broad_operation_pool_hash,
        )
    if progress_resume is not None:
        tested = max(tested, progress_resume.tested_candidates)
        pruned = max(pruned, progress_resume.pruned_candidates)
        next_state_id = max(next_state_id, progress_resume.state_count)
        reached_depth = max(reached_depth, progress_resume.depth)
        resumed_states += 1
    current_phase = "frontier"
    current_depth = reached_depth
    current_pool_index = 0
    current_combination_rank = 0
    current_combination_indices: tuple[int, ...] | None = None
    last_progress_at = time.monotonic()

    def save_progress_snapshot(
        *,
        phase: str | None = None,
        depth: int | None = None,
        pool_index: int | None = None,
        combination_rank: int | None = None,
        combination_indices: tuple[int, ...] | None = None,
    ) -> None:
        _write_ultimate_progress(
            progress_path,
            source_hash=source_hash,
            target_adler=target_adler,
            start_offset=start_offset,
            max_depth=max_depth,
            max_offsets=max_offsets,
            operation_pool_hash=operation_pool_hash,
            focused_operation_pool_hash=focused_operation_pool_hash,
            broad_operation_pool_hash=broad_operation_pool_hash,
            phase=current_phase if phase is None else phase,
            depth=current_depth if depth is None else depth,
            pool_index=current_pool_index if pool_index is None else pool_index,
            combination_rank=current_combination_rank if combination_rank is None else combination_rank,
            combination_indices=current_combination_indices if combination_indices is None else combination_indices,
            tested_candidates=tested,
            pruned_candidates=pruned,
            state_count=next_state_id,
            budget=budget_limit,
        )

    previous_sigint_handler = None
    sigint_handler_installed = False

    def save_then_interrupt(signum, frame):
        save_progress_snapshot()
        raise KeyboardInterrupt

    try:
        previous_sigint_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, save_then_interrupt)
        sigint_handler_installed = True
    except (OSError, ValueError):
        sigint_handler_installed = False

    def budget_reached() -> bool:
        return budget_limit is not None and tested >= budget_limit

    def progress_snapshot_due() -> bool:
        nonlocal last_progress_at
        if tested == 1 or tested % ULTIMATE_LINEFEED_PROGRESS_STEP == 0:
            last_progress_at = time.monotonic()
            return True
        now = time.monotonic()
        if now - last_progress_at >= ULTIMATE_LINEFEED_PROGRESS_INTERVAL_SECONDS:
            last_progress_at = now
            return True
        return False

    def terminal(candidate: SuperMegaLinefeedCandidate | None) -> bool:
        if candidate is None or not candidate.after.complete:
            return False
        if target_adler is None:
            return True
        return candidate.after.adler_status == "adler_match"

    if progress is not None and tested > 0:
        progress(strategy, min(tested, progress_total), progress_total)

    for depth in range(1, max(1, max_depth) + 1):
        reached_depth = depth
        current_phase = "frontier"
        current_depth = depth
        next_frontier: list[SuperMegaLinefeedCandidate] = []
        for parent in frontier:
            try:
                _parent_chunks, parent_stream = _all_chunks_and_idat_stream(parent.data)
            except png.PngFormatError:
                continue

            for offset in suspect_offsets:
                for candidate_stream, operation in _ultimate_mutations_for_offset(
                    parent_stream,
                    offset,
                    target_adler=target_adler,
                    computed_adler=parent.after.computed_adler,
                ):
                    if budget_reached():
                        budget_exhausted = True
                        break
                    stream_hash = _stream_state_key(candidate_stream)
                    if stream_hash in visited:
                        pruned += 1
                        continue
                    visited.add(stream_hash)
                    tested += 1

                    emit_progress = progress_snapshot_due()
                    if progress is not None and emit_progress:
                        progress(strategy, tested, progress_total)
                    if emit_progress:
                        save_progress_snapshot(phase="frontier", depth=depth)

                    candidate = _candidate_from_stream(
                        parent,
                        chunks,
                        candidate_stream,
                        operation,
                        target_adler=target_adler,
                        state_id=next_state_id,
                    )
                    candidate = _attach_ultimate_visual_score(candidate, reference_image)
                    next_state_id += 1
                    top_candidates = _remember_ultimate_top_candidate(top_candidates, candidate)
                    _preview_ultimate_candidate_if_valid(
                        candidate,
                        tested,
                        progress_total,
                        candidate_preview,
                    )
                    prune_reason = _ultimate_prune_reason(parent.after, candidate.after)
                    candidate_score = candidate.score or super_mega_linefeed_score(candidate.after, len(candidate.operations))
                    if (
                        _ultimate_prune_is_fatal(prune_reason, depth)
                        and candidate.after.adler_status != "adler_match"
                    ):
                        pruned += 1
                        continue
                    if (
                        depth > 2
                        and candidate_score <= (parent.score or super_mega_linefeed_score(parent.after, len(parent.operations)))
                    ):
                        pruned += 1
                        continue

                    _append_ultimate_checkpoint(
                        checkpoint_path,
                        source_hash=source_hash,
                        candidate=candidate,
                        depth=depth,
                    )
                    next_frontier.append(candidate)
                    if candidate_score > best_score:
                        best = candidate
                        best_score = candidate_score
                    if terminal(best):
                        break
                if budget_exhausted or terminal(best):
                    break
            if budget_exhausted or terminal(best):
                break

        if terminal(best):
            break
        if budget_exhausted or not next_frontier:
            break
        next_frontier.sort(
            key=lambda candidate: candidate.score or super_mega_linefeed_score(candidate.after, len(candidate.operations)),
            reverse=True,
        )
        frontier = next_frontier[: max(1, beam_width)]

    if not terminal(best) and not budget_exhausted and (budget_limit is None or tested < budget_limit):
        root_parent_score = root.score or super_mega_linefeed_score(root.after, 0)
        operation_pools = (
            focused_operation_pool,
            merged_operation_pool,
        )
        for pool_index, operation_pool in enumerate(operation_pools):
            if progress_resume is not None and progress_resume.phase == "exhaustive" and pool_index < progress_resume.pool_index:
                continue
            if not operation_pool:
                continue
            for depth in range(1, max(1, max_depth) + 1):
                if (
                    progress_resume is not None
                    and progress_resume.phase == "exhaustive"
                    and pool_index == progress_resume.pool_index
                    and depth < progress_resume.depth
                ):
                    continue
                reached_depth = max(reached_depth, depth)
                current_phase = "exhaustive"
                current_depth = depth
                current_pool_index = pool_index
                start_indices = None
                if (
                    progress_resume is not None
                    and progress_resume.phase == "exhaustive"
                    and pool_index == progress_resume.pool_index
                    and depth == progress_resume.depth
                ):
                    start_indices = progress_resume.combination_indices
                for indices in _combination_indices_from(len(operation_pool), depth, start_indices):
                    current_combination_indices = indices
                    current_combination_rank = _combination_rank(indices, len(operation_pool), depth)
                    combination = tuple(operation_pool[index] for index in indices)
                    if budget_reached():
                        budget_exhausted = True
                        break

                    operations = _normalize_ultimate_operation_sequence(combination)
                    candidate_stream = _replay_operations(root_stream, operations)
                    if candidate_stream is None:
                        pruned += 1
                        continue
                    stream_hash = _stream_state_key(candidate_stream)
                    if stream_hash in visited:
                        pruned += 1
                        continue

                    visited.add(stream_hash)
                    tested += 1
                    emit_progress = progress_snapshot_due()
                    if progress is not None and emit_progress:
                        progress(strategy, tested, progress_total)
                    next_indices = _next_combination_indices(indices, len(operation_pool), depth)
                    if emit_progress:
                        save_progress_snapshot(
                            phase="exhaustive",
                            depth=depth,
                            pool_index=pool_index,
                            combination_rank=current_combination_rank + 1,
                            combination_indices=next_indices,
                        )

                    candidate_data = _rebuild_with_single_idat_stream(chunks, candidate_stream)
                    candidate_analysis = idat.analyze_idat_stream(
                        candidate_data,
                        source_kind="candidate_from_original",
                        crc_provenance="rebuilt_by_chunklate",
                        target_adler=target_adler,
                    )
                    candidate_score = super_mega_linefeed_score(candidate_analysis, len(operations))
                    candidate = SuperMegaLinefeedCandidate(
                        candidate_data,
                        operations,
                        before,
                        candidate_analysis,
                        state_id=next_state_id,
                        parent_id=0,
                        source_offsets=tuple(operation.stream_offset for operation in operations),
                        score=candidate_score,
                    )
                    candidate = _attach_ultimate_visual_score(candidate, reference_image)
                    next_state_id += 1
                    top_candidates = _remember_ultimate_top_candidate(top_candidates, candidate)
                    _preview_ultimate_candidate_if_valid(
                        candidate,
                        tested,
                        progress_total,
                        candidate_preview,
                    )

                    prune_reason = _ultimate_prune_reason(before, candidate.after)
                    if (
                        _ultimate_prune_is_fatal(prune_reason, depth)
                        and candidate.after.adler_status != "adler_match"
                    ):
                        pruned += 1
                        continue

                    if candidate_score > best_score:
                        best = candidate
                        best_score = candidate_score
                        _append_ultimate_checkpoint(
                            checkpoint_path,
                            source_hash=source_hash,
                            candidate=candidate,
                            depth=depth,
                        )
                    elif depth > 2 and candidate_score <= root_parent_score:
                        pruned += 1

                    if terminal(best):
                        break

                if budget_exhausted or terminal(best):
                    break
            if budget_exhausted or terminal(best):
                break

    if progress is not None:
        progress(strategy, min(tested, progress_total), progress_total)
    save_progress_snapshot(phase="complete", depth=reached_depth)
    if sigint_handler_installed:
        signal.signal(signal.SIGINT, previous_sigint_handler)

    reason = ""
    if best is None:
        reason = "no candidate survived pruning"
    elif target_adler is not None and best.after.adler_status != "adler_match":
        reason = "original Adler target was not recovered"
    elif budget_exhausted:
        reason = "budget exhausted"

    return UltimateLinefeedProbeResult(
        before,
        best,
        target_adler,
        start_offset,
        reached_depth,
        max_depth,
        suspect_offsets,
        tested,
        next_state_id,
        len(visited),
        pruned,
        resumed_states,
        checkpoint_path,
        budget_exhausted,
        strategy,
        reason,
        top_candidates=top_candidates,
        reference_path=reference_path,
        reference_warning=reference_warning,
        progress_path=progress_path,
        progress_resumed=progress_resume is not None,
        progress_warning=progress_warning,
    )


def _evaluate_super_mega_phase(
    parent: SuperMegaLinefeedCandidate,
    *,
    phase_name: str,
    depth: int,
    mutations: Iterable[tuple[bytes, SuperMegaLinefeedOperation]],
    window_start: int,
    window_end: int,
    budget: int,
    progress_total: int,
    seen_streams: set[str],
    target_adler: int | None,
    next_state_id: int,
    progress: QueueProgressCallback | None,
) -> tuple[list[SuperMegaLinefeedCandidate], SuperMegaLinefeedPhaseSummary, int]:
    try:
        chunks, _idat_stream = _all_chunks_and_idat_stream(parent.data)
    except png.PngFormatError:
        return [], SuperMegaLinefeedPhaseSummary(phase_name, depth, 0, 0, 0, 0, False), next_state_id

    parent_score = super_mega_linefeed_score(parent.after, len(parent.operations))
    candidates: list[SuperMegaLinefeedCandidate] = []
    tested = 0
    accepted = 0
    budget_exhausted = False
    display_total = max(1, min(max(1, budget), max(1, progress_total)))

    if progress is not None:
        progress(phase_name, 0, display_total)
    progress_step = max(1, display_total // 100)

    for candidate_stream, operation in mutations:
        if tested >= budget:
            budget_exhausted = True
            break
        candidate_key = _stream_state_key(candidate_stream)
        if candidate_key in seen_streams:
            continue

        seen_streams.add(candidate_key)
        candidate = _candidate_from_stream(
            parent,
            chunks,
            candidate_stream,
            operation,
            target_adler=target_adler,
            state_id=next_state_id,
        )
        next_state_id += 1
        tested += 1

        if progress is not None and tested % progress_step == 0:
            progress(phase_name, min(tested, display_total), display_total)

        candidate_score = candidate.score or super_mega_linefeed_score(candidate.after, len(candidate.operations))
        if not candidate.after.supported or candidate_score <= parent_score:
            continue

        candidates.append(candidate)
        accepted += 1
        if candidate.after.complete:
            break

    if progress is not None:
        progress(phase_name, min(tested, display_total), display_total)

    return (
        candidates,
        SuperMegaLinefeedPhaseSummary(
            phase_name,
            depth,
            window_start,
            window_end,
            tested,
            accepted,
            budget_exhausted,
        ),
        next_state_id,
    )


def probe_super_mega_linefeed_force_of_death(
    data: bytes,
    *,
    start_offset: int | None = None,
    pre_error_backtrack: int | None = None,
    beam_width: int = 8,
    max_depth: int = 4,
    known_gap_bytes: int = 0,
    known_gap_chunk_offset: int | None = None,
    known_gap_window_start: int | None = None,
    known_gap_window_end: int | None = None,
    known_gap_budget: int = 8192,
    linefeed_budget: int = 1000000,
    structural_budget: int = 1024,
    local_bit_budget: int = 512,
    local_byte_budget: int = 1024,
    heavy_byte_budget: int = 1024,
    adler_budget: int = 16,
    structural_forward: int = 256,
    structural_insert_radius: int = 96,
    local_bit_backtrack: int = 128,
    local_bit_forward: int = 8,
    local_byte_backtrack: int = 32,
    local_byte_forward: int = 16,
    heavy_backtrack: int = 2048,
    heavy_forward: int = 256,
    progress: QueueProgressCallback | None = None,
) -> SuperMegaLinefeedProbeResult:
    strategy = "SuperMegaLineFeedForceOfDeath"
    before = idat.analyze_idat_stream(data)
    if not before.supported:
        return SuperMegaLinefeedProbeResult(before, None, start_offset, 0, 0, 0, 0, False, (), strategy, before.reason)
    if before.complete:
        return SuperMegaLinefeedProbeResult(
            before,
            None,
            start_offset,
            0,
            0,
            0,
            0,
            False,
            (),
            strategy,
            "IDAT stream is already complete",
        )

    try:
        chunks, idat_stream = _all_chunks_and_idat_stream(data)
    except png.PngFormatError as exc:
        return SuperMegaLinefeedProbeResult(before, None, start_offset, 0, 0, 0, 0, False, (), strategy, str(exc))

    if not idat_stream:
        return SuperMegaLinefeedProbeResult(
            before,
            None,
            start_offset,
            0,
            0,
            0,
            0,
            False,
            (),
            strategy,
            "IDAT stream is missing",
        )

    error_anchor = start_offset
    if error_anchor is None:
        error_anchor = _problem_stream_offset_for_analysis(before, idat_stream)
    if error_anchor is None:
        error_anchor = 0
    error_anchor = min(max(0, error_anchor), max(0, len(idat_stream) - 1))
    resolved_pre_error_backtrack = (
        adaptive_pre_error_backtrack(len(idat_stream))
        if pre_error_backtrack is None
        else max(0, int(pre_error_backtrack))
    )
    search_start = max(0, error_anchor - resolved_pre_error_backtrack)
    target_adler = before.stored_adler
    gap_size = max(0, int(known_gap_bytes))
    gap_window_start = known_gap_window_start
    gap_window_end = known_gap_window_end
    if known_gap_chunk_offset is not None:
        gap_range = _idat_stream_range_for_chunk_offset(chunks, int(known_gap_chunk_offset))
        if gap_range is not None:
            gap_window_start, gap_window_end = gap_range
    if gap_window_start is None:
        gap_window_start = search_start
    if gap_window_end is None:
        gap_window_end = len(idat_stream)
    gap_window_start = min(max(0, int(gap_window_start)), len(idat_stream))
    gap_window_end = min(max(gap_window_start, int(gap_window_end)), len(idat_stream))

    root_score = super_mega_linefeed_score(before, 0)
    root = SuperMegaLinefeedCandidate(
        data,
        (),
        before,
        before,
        state_id=0,
        parent_id=None,
        source_offsets=(),
        score=root_score,
    )
    beam = [root]
    best: SuperMegaLinefeedCandidate | None = None
    best_score = root_score
    phases: list[SuperMegaLinefeedPhaseSummary] = []
    states: list[SuperMegaLinefeedState] = [
        SuperMegaLinefeedState(
            0,
            None,
            idat_stream,
            (),
            before,
            (),
            root_score,
        )
    ]
    next_state_id = 1
    total_tested = 0
    budget_exhausted = False
    seen_streams: set[str] = {_stream_state_key(idat_stream)}
    remaining_budgets = {
        "phase0-known-gap-linefeed": max(0, known_gap_budget),
        "phase1-linefeed-global": max(0, linefeed_budget),
        "phase2-crlf-structural": max(0, structural_budget),
        "phase3-deflate-bit": max(0, local_bit_budget),
        "phase3-deflate-byte": max(0, local_byte_budget),
        "phase4-heavy-byte-window": max(0, heavy_byte_budget),
        "phase5-adler-target": max(0, adler_budget),
    }

    def terminal(candidate: SuperMegaLinefeedCandidate | None) -> bool:
        if candidate is None or not candidate.after.complete:
            return False
        if target_adler is None:
            return True
        return candidate.after.adler_status == "adler_match"

    for depth in range(max(1, max_depth)):
        next_candidates: list[SuperMegaLinefeedCandidate] = []

        for parent in beam:
            try:
                _parent_chunks, parent_stream = _all_chunks_and_idat_stream(parent.data)
            except png.PngFormatError:
                continue

            center = _analysis_or_anchor_offset(parent.after, parent_stream, error_anchor)
            structural_window_start = max(search_start, center - resolved_pre_error_backtrack)
            structural_window_end = min(len(parent_stream), center + structural_forward + 1)
            bit_window_start = max(0, center - local_bit_backtrack)
            bit_window_end = min(len(parent_stream), center + local_bit_forward + 1)
            byte_window_start = max(0, center - local_byte_backtrack)
            byte_window_end = min(len(parent_stream), center + local_byte_forward + 1)
            heavy_window_start = max(0, center - heavy_backtrack)
            heavy_window_end = min(len(parent_stream), center + heavy_forward + 1)
            adler_window_start = max(0, len(parent_stream) - 4)
            adler_window_end = len(parent_stream)
            phase_specs = []
            if depth == 0 and gap_size > 0:
                phase_specs.append(
                    (
                        "phase0-known-gap-linefeed",
                        _linefeed_known_gap_mutations(
                            parent_stream,
                            gap_size=gap_size,
                            window_start=gap_window_start,
                            window_end=gap_window_end,
                            center=center,
                        ),
                        gap_window_start,
                        gap_window_end,
                        known_gap_budget,
                        _count_linefeed_known_gap_mutations(
                            parent_stream,
                            gap_size=gap_size,
                            window_start=gap_window_start,
                            window_end=gap_window_end,
                            center=center,
                        ),
                    )
                )
            phase_specs.extend(
                (
                (
                    "phase1-linefeed-global",
                    _linefeed_global_mutations(parent_stream, search_start=search_start),
                    search_start,
                    len(parent_stream),
                    linefeed_budget,
                    _count_linefeed_global_mutations(parent_stream, search_start=search_start),
                ),
                (
                    "phase2-crlf-structural",
                    _linefeed_structural_mutations(
                        parent_stream,
                        center=center,
                        search_start=search_start,
                        backtrack=resolved_pre_error_backtrack,
                        forward=structural_forward,
                        insert_radius=structural_insert_radius,
                    ),
                    structural_window_start,
                    structural_window_end,
                    structural_budget,
                    _count_linefeed_structural_mutations(
                        parent_stream,
                        center=center,
                        search_start=search_start,
                        backtrack=resolved_pre_error_backtrack,
                        forward=structural_forward,
                        insert_radius=structural_insert_radius,
                    ),
                ),
                (
                    "phase3-deflate-bit",
                    _bit_flip_mutations(
                        parent_stream,
                        center=center,
                        backtrack=local_bit_backtrack,
                        forward=local_bit_forward,
                    ),
                    bit_window_start,
                    bit_window_end,
                    local_bit_budget,
                    max(0, bit_window_end - bit_window_start) * 8,
                ),
                (
                    "phase3-deflate-byte",
                    _byte_replace_mutations(
                        parent_stream,
                        center=center,
                        backtrack=local_byte_backtrack,
                        forward=local_byte_forward,
                        kind="byte-replace-local",
                    ),
                    byte_window_start,
                    byte_window_end,
                    local_byte_budget,
                    max(0, byte_window_end - byte_window_start) * 255,
                ),
                (
                    "phase4-heavy-byte-window",
                    _byte_replace_mutations(
                        parent_stream,
                        center=center,
                        backtrack=heavy_backtrack,
                        forward=heavy_forward,
                        kind="byte-replace-heavy",
                    ),
                    heavy_window_start,
                    heavy_window_end,
                    heavy_byte_budget,
                    max(0, heavy_window_end - heavy_window_start) * 255,
                ),
                (
                    "phase5-adler-target",
                    _adler_target_mutations(
                        parent_stream,
                        target_adler=target_adler,
                        computed_adler=parent.after.computed_adler,
                    ),
                    adler_window_start,
                    adler_window_end,
                    adler_budget,
                    _count_adler_target_mutations(
                        parent_stream,
                        target_adler=target_adler,
                        computed_adler=parent.after.computed_adler,
                    ),
                ),
                )
            )

            for phase_name, mutations, window_start, window_end, budget, progress_total in phase_specs:
                if budget <= 0:
                    continue
                phase_budget = min(max(0, budget), remaining_budgets.get(phase_name, 0))
                if phase_budget <= 0:
                    phases.append(
                        SuperMegaLinefeedPhaseSummary(
                            phase_name,
                            depth,
                            window_start,
                            window_end,
                            0,
                            0,
                            True,
                        )
                    )
                    budget_exhausted = True
                    continue

                candidates, phase, next_state_id = _evaluate_super_mega_phase(
                    parent,
                    phase_name=phase_name,
                    depth=depth,
                    mutations=mutations,
                    window_start=window_start,
                    window_end=window_end,
                    budget=phase_budget,
                    progress_total=progress_total,
                    seen_streams=seen_streams,
                    target_adler=target_adler,
                    next_state_id=next_state_id,
                    progress=progress,
                )
                phases.append(phase)
                total_tested += phase.tested_candidates
                remaining_budgets[phase_name] = max(
                    0,
                    remaining_budgets.get(phase_name, 0) - phase.tested_candidates,
                )
                budget_exhausted = budget_exhausted or phase.budget_exhausted

                for candidate in candidates:
                    next_candidates.append(candidate)
                    states.append(
                        SuperMegaLinefeedState(
                            candidate.state_id,
                            candidate.parent_id,
                            b"".join(
                                chunk.data
                                for chunk in png.iter_chunks(candidate.data)
                                if chunk.chunk_type == b"IDAT"
                            ),
                            candidate.operations,
                            candidate.after,
                            candidate.source_offsets,
                            candidate.score,
                        )
                    )
                    candidate_score = candidate.score or super_mega_linefeed_score(candidate.after, len(candidate.operations))
                    if candidate_score > best_score:
                        best = candidate
                        best_score = candidate_score

                if terminal(best):
                    break

            if terminal(best):
                break

        if terminal(best):
            break
        if not next_candidates:
            break

        next_candidates.sort(
            key=lambda candidate: candidate.score or super_mega_linefeed_score(candidate.after, len(candidate.operations)),
            reverse=True,
        )
        beam = next_candidates[: max(1, beam_width)]

    reason = ""
    if best is None:
        reason = "no phase improved score"
    elif target_adler is not None and best.after.adler_status != "adler_match":
        reason = "original Adler target was not recovered"
    elif budget_exhausted and not best.after.complete:
        reason = "budget exhausted before complete IDAT"

    return SuperMegaLinefeedProbeResult(
        before,
        best,
        error_anchor,
        search_start,
        search_start,
        len(idat_stream),
        total_tested,
        budget_exhausted,
        tuple(phases),
        strategy,
        reason,
        resolved_pre_error_backtrack,
        target_adler,
        next_state_id,
        len(seen_streams),
        tuple(states),
    )


def probe_idat_deflate_byte_candidates(
    data: bytes,
    *,
    window_radius: int = 16,
    budget: int = 10000,
    strategy: str = "strict-byte",
    progress: QueueProgressCallback | None = None,
) -> IdatDeflateProbeResult:
    before = idat.analyze_idat_stream(data)
    if not before.supported:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, before.reason)
    if before.complete:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, "IDAT stream is already complete")
    if before.error_offset is None:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, "IDAT error offset is unknown")

    try:
        _idat_chunks, idat_stream = _idat_chunks_and_stream(data)
    except png.PngFormatError as exc:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, str(exc))

    center = min(max(0, before.error_offset), max(0, len(idat_stream) - 1))
    window_start = max(0, center - window_radius)
    window_end = min(len(idat_stream), center + window_radius + 1)
    before_score = analysis_score(before)
    best: IdatDeflateCandidate | None = None
    best_score = before_score
    tested = 0
    budget_exhausted = False

    if progress is not None:
        progress(strategy, 0, budget)

    for stream_offset in range(window_start, window_end):
        old_byte = idat_stream[stream_offset]
        for new_byte in range(256):
            if new_byte == old_byte:
                continue
            if tested >= budget:
                budget_exhausted = True
                return IdatDeflateProbeResult(
                    before,
                    best,
                    window_start,
                    window_end,
                    tested,
                    budget_exhausted,
                    strategy,
                )

            tested += 1
            if progress is not None and tested % 100 == 0:
                progress(strategy, tested, budget)
            candidate = mutate_idat_stream_byte(data, stream_offset, new_byte)
            if candidate is None:
                continue

            if not is_material_improvement(before, candidate.after):
                continue

            candidate_score = analysis_score(candidate.after)
            if candidate_score > best_score:
                best = candidate
                best_score = candidate_score
                if candidate.after.complete:
                    if progress is not None:
                        progress(strategy, tested, budget)
                    return IdatDeflateProbeResult(
                        before,
                        best,
                        window_start,
                        window_end,
                        tested,
                        budget_exhausted,
                        strategy,
                    )

    if progress is not None:
        progress(strategy, tested, budget)
    return IdatDeflateProbeResult(before, best, window_start, window_end, tested, budget_exhausted, strategy)


def probe_idat_deflate_bit_candidates(
    data: bytes,
    *,
    backtrack: int = 128,
    forward: int = 8,
    budget: int = 4096,
    strategy: str = "pre-error-bit",
    progress: QueueProgressCallback | None = None,
) -> IdatDeflateProbeResult:
    before = idat.analyze_idat_stream(data)
    if not before.supported:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, before.reason)
    if before.complete:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, "IDAT stream is already complete")
    if before.error_offset is None:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, "IDAT error offset is unknown")

    try:
        _idat_chunks, idat_stream = _idat_chunks_and_stream(data)
    except png.PngFormatError as exc:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, str(exc))

    center = min(max(0, before.error_offset), max(0, len(idat_stream) - 1))
    window_start = max(0, center - backtrack)
    window_end = min(len(idat_stream), center + forward + 1)
    before_score = analysis_score(before)
    best: IdatDeflateCandidate | None = None
    best_score = before_score
    tested = 0
    budget_exhausted = False

    if progress is not None:
        progress(strategy, 0, budget)

    for stream_offset in range(window_start, window_end):
        old_byte = idat_stream[stream_offset]
        for bit in range(8):
            if tested >= budget:
                budget_exhausted = True
                return IdatDeflateProbeResult(
                    before,
                    best,
                    window_start,
                    window_end,
                    tested,
                    budget_exhausted,
                    strategy,
                )

            tested += 1
            if progress is not None and tested % 100 == 0:
                progress(strategy, tested, budget)
            candidate = mutate_idat_stream_byte(data, stream_offset, old_byte ^ (1 << bit))
            if candidate is None:
                continue
            if not is_material_improvement(before, candidate.after):
                continue

            candidate_score = analysis_score(candidate.after)
            if candidate_score > best_score:
                best = candidate
                best_score = candidate_score
                if candidate.after.complete:
                    if progress is not None:
                        progress(strategy, tested, budget)
                    return IdatDeflateProbeResult(
                        before,
                        best,
                        window_start,
                        window_end,
                        tested,
                        budget_exhausted,
                        strategy,
                    )

    if progress is not None:
        progress(strategy, tested, budget)
    return IdatDeflateProbeResult(before, best, window_start, window_end, tested, budget_exhausted, strategy)


def _deflate_header_window(
    stream: bytes,
    before: idat.IdatStreamAnalysis,
    header: deflate_header.DeflateHeaderAnalysis,
) -> tuple[int, int]:
    if not stream:
        return 0, 0
    if before.error_offset is not None:
        hard_end = min(len(stream), before.error_offset + 1)
    else:
        hard_end = min(len(stream), max(2, header.byte_offset + 1))
    if header.header_end_byte is not None:
        hard_end = min(hard_end, max(2, header.header_end_byte + 1))
    else:
        hard_end = min(hard_end, max(2, header.byte_offset + 8))
    return 0, max(0, hard_end)


def _candidate_header_is_fixed(
    before: idat.IdatStreamAnalysis,
    candidate: IdatDeflateCandidate,
) -> bool:
    before_header = before.deflate_header
    after_header = candidate.after.deflate_header
    if before_header is None:
        return False
    if before_header.ok:
        return False
    if after_header is None:
        return candidate.after.complete
    return after_header.ok


def probe_deflate_header_candidates(
    data: bytes,
    *,
    budget: int = 4096,
    progress: QueueProgressCallback | None = None,
) -> IdatDeflateProbeResult:
    before = idat.analyze_idat_stream(data)
    strategy = "deflate-header"
    if not before.supported:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, before.reason)
    if before.complete:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, "IDAT stream is already complete")
    if before.decompressed_size != 0:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, "deflate already produced bytes")

    try:
        _idat_chunks, idat_stream = _idat_chunks_and_stream(data)
    except png.PngFormatError as exc:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, str(exc))

    before_header = before.deflate_header or deflate_header.analyze_deflate_header(idat_stream)
    if before_header.ok:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, "deflate header already parses")

    window_start, window_end = _deflate_header_window(idat_stream, before, before_header)
    best: IdatDeflateCandidate | None = None
    best_score = analysis_score(before)
    tested = 0
    budget_exhausted = False

    if progress is not None:
        progress("deflate-header-bit", 0, budget)

    for stream_offset in range(window_start, window_end):
        old_byte = idat_stream[stream_offset]
        for bit in range(8):
            if tested >= budget:
                budget_exhausted = True
                return IdatDeflateProbeResult(
                    before,
                    best,
                    window_start,
                    window_end,
                    tested,
                    budget_exhausted,
                    strategy,
                    before_header.summary,
                )
            tested += 1
            if progress is not None and tested % 100 == 0:
                progress("deflate-header-bit", tested, budget)
            candidate = mutate_idat_stream_byte(data, stream_offset, old_byte ^ (1 << bit))
            if candidate is None:
                continue
            if not _candidate_header_is_fixed(before, candidate):
                continue
            if not is_material_improvement(before, candidate.after):
                continue
            candidate_score = analysis_score(candidate.after)
            if candidate_score > best_score:
                best = candidate
                best_score = candidate_score
                if candidate.after.complete:
                    if progress is not None:
                        progress("deflate-header-bit", tested, budget)
                    return IdatDeflateProbeResult(
                        before,
                        best,
                        window_start,
                        window_end,
                        tested,
                        budget_exhausted,
                        strategy,
                        before_header.summary,
                    )

    if progress is not None:
        progress("deflate-header-byte", tested, budget)

    for stream_offset in range(window_start, window_end):
        old_byte = idat_stream[stream_offset]
        for new_byte in range(256):
            if new_byte == old_byte:
                continue
            if tested >= budget:
                budget_exhausted = True
                return IdatDeflateProbeResult(
                    before,
                    best,
                    window_start,
                    window_end,
                    tested,
                    budget_exhausted,
                    strategy,
                    before_header.summary,
                )
            tested += 1
            if progress is not None and tested % 100 == 0:
                progress("deflate-header-byte", tested, budget)
            candidate = mutate_idat_stream_byte(data, stream_offset, new_byte)
            if candidate is None:
                continue
            if not _candidate_header_is_fixed(before, candidate):
                continue
            if not is_material_improvement(before, candidate.after):
                continue
            candidate_score = analysis_score(candidate.after)
            if candidate_score > best_score:
                best = candidate
                best_score = candidate_score
                if candidate.after.complete:
                    if progress is not None:
                        progress("deflate-header-byte", tested, budget)
                    return IdatDeflateProbeResult(
                        before,
                        best,
                        window_start,
                        window_end,
                        tested,
                        budget_exhausted,
                        strategy,
                        before_header.summary,
                    )

    if progress is not None:
        progress("deflate-header-byte", tested, budget)
    return IdatDeflateProbeResult(
        before,
        best,
        window_start,
        window_end,
        tested,
        budget_exhausted,
        strategy,
        before_header.summary,
    )


def probe_idat_deflate_heavy_candidates(
    data: bytes,
    *,
    backtrack: int = 2048,
    forward: int = 256,
    budget: int = 250000,
    strategy: str = "heavy-byte",
    progress: ProgressCallback | None = None,
) -> IdatDeflateProbeResult:
    before = idat.analyze_idat_stream(data)
    if not before.supported:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, before.reason)
    if before.complete:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, "IDAT stream is already complete")
    if before.error_offset is None:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, "IDAT error offset is unknown")

    try:
        _idat_chunks, idat_stream = _idat_chunks_and_stream(data)
    except png.PngFormatError as exc:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, str(exc))

    center = min(max(0, before.error_offset), max(0, len(idat_stream) - 1))
    window_start = max(0, center - backtrack)
    window_end = min(len(idat_stream), center + forward + 1)
    before_score = analysis_score(before)
    best: IdatDeflateCandidate | None = None
    best_score = before_score
    tested = 0
    budget_exhausted = False

    if progress is not None:
        progress(0, budget, True)

    for stream_offset in range(window_start, window_end):
        old_byte = idat_stream[stream_offset]
        for new_byte in range(256):
            if new_byte == old_byte:
                continue
            if tested >= budget:
                budget_exhausted = True
                if progress is not None:
                    progress(tested, budget, False)
                return IdatDeflateProbeResult(
                    before,
                    best,
                    window_start,
                    window_end,
                    tested,
                    budget_exhausted,
                    strategy,
                )

            tested += 1
            if progress is not None and tested % 100 == 0:
                progress(tested, budget, False)

            candidate = mutate_idat_stream_byte(data, stream_offset, new_byte)
            if candidate is None:
                continue
            if not is_material_improvement(before, candidate.after):
                continue

            candidate_score = analysis_score(candidate.after)
            if candidate_score > best_score:
                best = candidate
                best_score = candidate_score
                if candidate.after.complete:
                    if progress is not None:
                        progress(tested, budget, False)
                    return IdatDeflateProbeResult(
                        before,
                        best,
                        window_start,
                        window_end,
                        tested,
                        budget_exhausted,
                        strategy,
                    )

    if progress is not None:
        progress(tested, budget, False)
    return IdatDeflateProbeResult(before, best, window_start, window_end, tested, budget_exhausted, strategy)


def probe_idat_deflate_single_pass(
    data: bytes,
    *,
    progress: QueueProgressCallback | None = None,
) -> IdatDeflateProbeResult:
    strict = probe_idat_deflate_byte_candidates(
        data,
        window_radius=16,
        budget=10000,
        strategy="strict-byte",
        progress=progress,
    )
    if strict.best is not None:
        return strict

    bit = probe_idat_deflate_bit_candidates(data, progress=progress)
    if bit.best is not None:
        return bit

    wider = probe_idat_deflate_byte_candidates(
        data,
        window_radius=64,
        budget=32768,
        strategy="wide-byte",
        progress=progress,
    )
    if wider.best is not None:
        return wider

    return IdatDeflateProbeResult(
        strict.before,
        None,
        min(strict.window_start, wider.window_start),
        max(strict.window_end, wider.window_end),
        strict.tested_candidates + bit.tested_candidates + wider.tested_candidates,
        strict.budget_exhausted or bit.budget_exhausted or wider.budget_exhausted,
        "strategy-queue",
        wider.reason or bit.reason or strict.reason,
    )


def probe_idat_deflate_strategy_queue(
    data: bytes,
    *,
    max_steps: int = 4,
    progress: QueueProgressCallback | None = None,
) -> IdatDeflateProbeResult:
    original = idat.analyze_idat_stream(data)
    current_data = data
    chain: list[IdatDeflateCandidate] = []
    total_tested = 0
    budget_exhausted = False
    last_result: IdatDeflateProbeResult | None = None

    for _step in range(max_steps):
        result = probe_idat_deflate_single_pass(current_data, progress=progress)
        last_result = result
        total_tested += result.tested_candidates
        budget_exhausted = budget_exhausted or result.budget_exhausted
        if result.best is None:
            break

        chain.append(result.best)
        current_data = result.best.data
        if result.best.after.complete:
            break

    if chain:
        best = chain[-1]
        if len(chain) == 1:
            return IdatDeflateProbeResult(
                original,
                best,
                last_result.window_start if last_result else 0,
                last_result.window_end if last_result else 0,
                total_tested,
                budget_exhausted,
                last_result.strategy if last_result else "strategy-queue",
                last_result.reason if last_result else "",
                tuple(chain),
            )
        return IdatDeflateProbeResult(
            original,
            best,
            0,
            best.stream_offset + 1,
            total_tested,
            budget_exhausted,
            "chase",
            "",
            tuple(chain),
        )

    if last_result is None:
        return IdatDeflateProbeResult(original, None, 0, 0, 0, False, "strategy-queue", "IDAT strategy queue did not run")
    return IdatDeflateProbeResult(
        original,
        None,
        last_result.window_start,
        last_result.window_end,
        total_tested,
        budget_exhausted,
        "strategy-queue",
        last_result.reason,
    )


def probe_summary_line(result: IdatDeflateProbeResult) -> str:
    line = (
        "-IDAT deflate probe: strategy=%s; window=0x%x..0x%x; tested=%s"
        % (result.strategy, result.window_start, result.window_end, result.tested_candidates)
    )
    if result.budget_exhausted:
        line += "; budget exhausted"
    if result.reason:
        line += "; reason=%s" % result.reason
    return line + "."


def linefeed_insert_probe_summary_line(result: IdatLinefeedInsertProbeResult) -> str:
    line = (
        "-IDAT line-feed probe: strategy=%s; window=0x%x..0x%x; tested=%s"
        % (result.strategy, result.window_start, result.window_end, result.tested_candidates)
    )
    if result.budget_exhausted:
        line += "; budget exhausted"
    if result.reason:
        line += "; reason=%s" % result.reason
    return line + "."


def super_mega_linefeed_probe_summary_line(result: SuperMegaLinefeedProbeResult) -> str:
    line = (
        "-%s: anchor=%s; search=0x%x..0x%x; pre_error_backtrack=0x%x; tested=%s; phases=%s; states=%s; visited=%s; target_adler=%s; source_crc=%s"
        % (
            result.strategy,
            _format_optional_offset(result.error_anchor_offset),
            result.search_start_offset,
            result.window_end,
            result.pre_error_backtrack,
            result.tested_candidates,
            len(result.phases),
            result.state_count,
            result.visited_count,
            idat.format_adler(result.target_adler),
            result.before.crc_provenance,
        )
    )
    if result.best is not None:
        line += "; best_score=%s" % (
            super_mega_linefeed_score(result.best.after, len(result.best.operations)),
        )
    if result.budget_exhausted:
        line += "; budget exhausted"
    if result.reason:
        line += "; reason=%s" % result.reason
    return line + "."


def super_mega_linefeed_phase_summary_lines(result: SuperMegaLinefeedProbeResult) -> tuple[str, ...]:
    aggregates: dict[str, dict[str, object]] = {}
    order: list[str] = []
    for phase in result.phases:
        if phase.name not in aggregates:
            order.append(phase.name)
            aggregates[phase.name] = {
                "runs": 0,
                "min_depth": phase.depth,
                "max_depth": phase.depth,
                "window_start": phase.window_start,
                "window_end": phase.window_end,
                "tested": 0,
                "accepted": 0,
                "budget_exhausted": False,
            }
        aggregate = aggregates[phase.name]
        aggregate["runs"] = int(aggregate["runs"]) + 1
        aggregate["min_depth"] = min(int(aggregate["min_depth"]), phase.depth)
        aggregate["max_depth"] = max(int(aggregate["max_depth"]), phase.depth)
        aggregate["window_start"] = min(int(aggregate["window_start"]), phase.window_start)
        aggregate["window_end"] = max(int(aggregate["window_end"]), phase.window_end)
        aggregate["tested"] = int(aggregate["tested"]) + phase.tested_candidates
        aggregate["accepted"] = int(aggregate["accepted"]) + phase.accepted_candidates
        aggregate["budget_exhausted"] = bool(aggregate["budget_exhausted"]) or phase.budget_exhausted

    lines = []
    for name in order:
        aggregate = aggregates[name]
        min_depth = int(aggregate["min_depth"])
        max_depth = int(aggregate["max_depth"])
        depth_label = str(min_depth) if min_depth == max_depth else "%s..%s" % (min_depth, max_depth)
        lines.append(
            "-%s phase: runs=%s; depth=%s; window=0x%x..0x%x; tested=%s; accepted=%s%s."
            % (
                name,
                aggregate["runs"],
                depth_label,
                int(aggregate["window_start"]),
                int(aggregate["window_end"]),
                aggregate["tested"],
                aggregate["accepted"],
                "; budget exhausted" if aggregate["budget_exhausted"] else "",
            )
        )
    return tuple(lines)


def ultimate_linefeed_probe_summary_line(result: UltimateLinefeedProbeResult) -> str:
    line = (
        "-%s: start=%s; depth=%s/%s; suspects=%s; tested=%s; states=%s; visited=%s; pruned=%s; resumed=%s; target_adler=%s"
        % (
            result.strategy,
            _format_optional_offset(result.start_offset),
            result.reached_depth,
            result.max_depth,
            len(result.suspect_offsets),
            result.tested_candidates,
            result.state_count,
            result.visited_count,
            result.pruned_candidates,
            result.resumed_states,
            idat.format_adler(result.target_adler),
        )
    )
    if result.checkpoint_path:
        line += "; checkpoint=%s" % result.checkpoint_path
    if result.progress_path:
        line += "; progress=%s" % result.progress_path
    if result.progress_resumed:
        line += "; progress resumed"
    if result.best is not None:
        line += "; best_score=%s" % (
            result.best.score or super_mega_linefeed_score(result.best.after, len(result.best.operations)),
        )
    if result.top_candidates:
        line += "; top_candidates=%s" % len(result.top_candidates)
    if result.reference_warning:
        line += "; reference_warning=%s" % result.reference_warning
    if result.progress_warning:
        line += "; progress_warning=%s" % result.progress_warning
    if result.budget_exhausted:
        line += "; budget exhausted"
    if result.reason:
        line += "; reason=%s" % result.reason
    return line + "."


def ultimate_linefeed_offsets_summary_line(result: UltimateLinefeedProbeResult, *, limit: int = 16) -> str:
    offsets = ", ".join("0x%x" % offset for offset in result.suspect_offsets[:limit])
    if len(result.suspect_offsets) > limit:
        offsets += ", ..."
    return "-%s offsets: %s." % (result.strategy, offsets or "none")


def ultimate_linefeed_candidate_summary_line(candidate: SuperMegaLinefeedCandidate) -> str:
    operations = ", ".join(_format_operation(operation) for operation in candidate.operations)
    if len(operations) > 240:
        operations = operations[:237] + "..."
    line = (
        "-UltimateMegaSuperLineFeedBruteForce candidate: state=%s parent=%s; operations=%s; "
        "status %s -> %s; adler %s -> %s (stored=%s computed=%s); crc=%s; "
        "scanlines %s/%s -> %s/%s; decompressed %s/%s -> %s/%s; error_offset %s -> %s."
        % (
            candidate.state_id,
            "root" if candidate.parent_id is None else candidate.parent_id,
            operations or "none",
            candidate.before.status,
            candidate.after.status,
            candidate.before.adler_status,
            candidate.after.adler_status,
            idat.format_adler(candidate.after.stored_adler),
            idat.format_adler(candidate.after.computed_adler),
            candidate.after.crc_provenance,
            candidate.before.usable_scanlines,
            candidate.before.height,
            candidate.after.usable_scanlines,
            candidate.after.height,
            candidate.before.decompressed_size,
            candidate.before.expected_size,
            candidate.after.decompressed_size,
            candidate.after.expected_size,
            candidate.before.error_offset,
            candidate.after.error_offset,
        )
    )
    if candidate.visual_score is not None:
        line = line[:-1] + "; visual_score=%.4f." % candidate.visual_score
    return line


def candidate_summary_line(candidate: IdatDeflateCandidate) -> str:
    return (
        "-IDAT deflate candidate: stream=0x%x; file=0x%x; IDAT=%s; byte %02x -> %02x; "
        "status %s -> %s; scanlines %s/%s -> %s/%s; error_offset %s -> %s."
        % (
            candidate.stream_offset,
            candidate.file_offset,
            candidate.idat_index,
            candidate.old_byte,
            candidate.new_byte,
            candidate.before.status,
            candidate.after.status,
            candidate.before.usable_scanlines,
            candidate.before.height,
            candidate.after.usable_scanlines,
            candidate.after.height,
            candidate.before.error_offset,
            candidate.after.error_offset,
        )
    )


def linefeed_insert_candidate_summary_line(candidate: IdatLinefeedInsertCandidate) -> str:
    return (
        "-IDAT line-feed candidate: stream=0x%x; inserted %02x; "
        "status %s -> %s; scanlines %s/%s -> %s/%s; decompressed %s -> %s."
        % (
            candidate.stream_offset,
            candidate.inserted_byte,
            candidate.before.status,
            candidate.after.status,
            candidate.before.usable_scanlines,
            candidate.before.height,
            candidate.after.usable_scanlines,
            candidate.after.height,
            candidate.before.decompressed_size,
            candidate.after.decompressed_size,
        )
    )


def super_mega_linefeed_candidate_summary_line(candidate: SuperMegaLinefeedCandidate) -> str:
    operations = ", ".join(_format_operation(operation) for operation in candidate.operations)
    if len(operations) > 240:
        operations = operations[:237] + "..."
    return (
        "-%s candidate: state=%s parent=%s; operations=%s; status %s -> %s; adler %s -> %s "
        "(stored=%s computed=%s); crc=%s; scanlines %s/%s -> %s/%s; "
        "decompressed %s/%s -> %s/%s; error_offset %s -> %s."
        % (
            "SuperMegaLineFeedForceOfDeath",
            candidate.state_id,
            "root" if candidate.parent_id is None else candidate.parent_id,
            operations or "none",
            candidate.before.status,
            candidate.after.status,
            candidate.before.adler_status,
            candidate.after.adler_status,
            idat.format_adler(candidate.after.stored_adler),
            idat.format_adler(candidate.after.computed_adler),
            candidate.after.crc_provenance,
            candidate.before.usable_scanlines,
            candidate.before.height,
            candidate.after.usable_scanlines,
            candidate.after.height,
            candidate.before.decompressed_size,
            candidate.before.expected_size,
            candidate.after.decompressed_size,
            candidate.after.expected_size,
            candidate.before.error_offset,
            candidate.after.error_offset,
        )
    )


def candidate_summary_lines(result: IdatDeflateProbeResult) -> tuple[str, ...]:
    if result.chain:
        return tuple(candidate_summary_line(candidate) for candidate in result.chain)
    if result.best is not None:
        return (candidate_summary_line(result.best),)
    return ()
