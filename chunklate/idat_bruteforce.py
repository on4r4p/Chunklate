from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import dataclass, replace
from decimal import Decimal
import hashlib
import heapq
import itertools
import json
import math
import multiprocessing
import os
import queue
import signal
import time
import zlib
from typing import Any, Callable, Iterable

from . import deflate_header
from . import idat
from . import png


ProgressCallback = Callable[[int, int, bool], None]
QueueProgressCallback = Callable[[str, int, int], None]
UltimateCandidatePreviewCallback = Callable[["SuperMegaLinefeedCandidate", int, int], None]
UltimateInterruptFlushProgressCallback = Callable[[int, int], None]
UltimateInterruptRepeatCallback = Callable[[int], None]
UltimateResumeStatusCallback = Callable[[dict[str, Any]], None]
UNBOUNDED_PROGRESS_TOTAL = 10**12
ULTIMATE_LINEFEED_PROGRESS_STEP = 100
ULTIMATE_LINEFEED_PROGRESS_INTERVAL_SECONDS = 2.0
ULTIMATE_LINEFEED_PARALLEL_PROGRESS_STEP = 100
ULTIMATE_LINEFEED_PARALLEL_PROGRESS_POLL_SECONDS = 0.25
ULTIMATE_LINEFEED_MIN_BUDGET = 50_000
ULTIMATE_LINEFEED_ETA_CANDIDATES_PER_SECOND = 100
ULTIMATE_LINEFEED_VISUAL_GALLERY_LIMIT = 100
ULTIMATE_LINEFEED_VISUAL_MIN_COVERAGE = 0.95
ULTIMATE_LINEFEED_VISUAL_PROGRESS_VERSION = 1
ULTIMATE_LINEFEED_VISUAL_PREVIEW_FOLDER = ("Bruteforce_Previews", "VisualCandidates")
ULTIMATE_LINEFEED_VISUAL_WRITE_STEP = 1000
ULTIMATE_LINEFEED_REFERENCE_MODES = ("exact", "similar")
ULTIMATE_LINEFEED_REFERENCE_REGION_NAME = "_ULF.reference_regions.json"
ULTIMATE_LINEFEED_REFERENCE_REGION_VERSION = 2
ULTIMATE_LINEFEED_CHECKPOINT_REHYDRATE_LIMIT = 256
ULTIMATE_LINEFEED_ROI_LOCAL_RADIUS_PX = 6
ULTIMATE_LINEFEED_ROI_LOCAL_STEP_PX = 3
ULTIMATE_LINEFEED_ROI_SEARCH_SCALES = (0.75, 1.0, 1.25, 1.5)
ULTIMATE_LINEFEED_ROI_MODES = ("paired", "search", "single", "negative")
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
ULTIMATE_LINEFEED_PROGRESS_VERSION = 2
ULTIMATE_LINEFEED_LEGACY_PROGRESS_VERSION = 1
ULTIMATE_LINEFEED_PARALLEL_SHARD_SIZE = 50_000
ULTIMATE_LINEFEED_PARALLEL_SHUTDOWN_GRACE_SECONDS = 5.0


def _hidden_tmp_path(path: str) -> str:
    directory, filename = os.path.split(path)
    tmp_name = ".%s.%s.%s.tmp" % (
        filename or "chunklate",
        os.getpid(),
        time.monotonic_ns(),
    )
    return os.path.join(directory, tmp_name) if directory else tmp_name


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
    visual_score_kind: str = ""
    matched_patch_count: int = 0
    visual_raw_score: float | None = None
    visual_confidence: float | None = None
    visual_effective_score: float | None = None


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
class UltimateVisualCandidate:
    candidate: SuperMegaLinefeedCandidate
    preview_data: bytes
    preview_strategy: str
    visual_hash: str
    scanline_hash: str
    operation_hash: str
    diversity_key: str
    rank: tuple[object, ...]
    coverage: float
    tested_candidates: int
    preview_path: str = ""


@dataclass(frozen=True)
class UltimateVisualBackfillCandidate:
    candidate: SuperMegaLinefeedCandidate
    tested_candidates: int
    structural_rank: tuple[object, ...]
    coverage: float


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
    reference_mode: str = "exact"
    reference_regions_path: str = ""
    reference_warning: str = ""
    progress_path: str = ""
    progress_resumed: bool = False
    progress_warning: str = ""
    visual_candidates: tuple[UltimateVisualCandidate, ...] = ()
    visual_gallery_path: str = ""
    visual_preview_count: int = 0
    visual_gallery_limit: int = ULTIMATE_LINEFEED_VISUAL_GALLERY_LIMIT
    fast_resume_used: bool = False
    fast_resume_rejected_reason: str = ""
    attempted_floor: int = 0
    committed_count: int = 0
    matched_shards: int = 0
    pending_shards: int = 0
    current_workers: int = 0
    saved_workers: int = 0

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
class UltimateVisualScore:
    score: float | None
    kind: str = ""
    matched_patch_count: int = 0
    raw_score: float | None = None
    confidence: float = 1.0
    effective_score: float | None = None


@dataclass(frozen=True)
class UltimatePatchFeature:
    index: int
    edge_density: float
    contrast: float
    ahash: tuple[bool, ...]
    dhash: tuple[bool, ...]
    info: float


@dataclass(frozen=True)
class UltimateRoiQuickFeature:
    edge_density: float
    contrast: float
    ahash: tuple[bool, ...]
    dhash: tuple[bool, ...]


@dataclass(frozen=True)
class UltimateRoiDescriptor:
    gray: object
    edges: object
    edge_density: float
    contrast: float
    ahash: tuple[bool, ...]
    dhash: tuple[bool, ...]
    phash: tuple[bool, ...]


@dataclass(frozen=True)
class UltimateReferenceRegion:
    candidate_region: tuple[float, float, float, float]
    reference_region: tuple[float, float, float, float]
    weight: float = 1.0
    label: str = ""
    match_mode: str = "paired"


@dataclass(frozen=True)
class UltimateReferenceRegions:
    path: str = ""
    candidate_size: tuple[int, int] = (0, 0)
    reference_size: tuple[int, int] = (0, 0)
    candidate_hash: str = ""
    reference_hash: str = ""
    regions: tuple[UltimateReferenceRegion, ...] = ()
    warning: str = ""


@dataclass(frozen=True)
class UltimateVisualReference:
    image: object | None
    mode: str
    gray: object | None = None
    edges: object | None = None
    patches: tuple[UltimatePatchFeature, ...] = ()
    regions: UltimateReferenceRegions | None = None
    source_image: object | None = None


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
    parallel_workers: int = 0
    shard_size: int = 0
    shards: tuple[dict[str, Any], ...] = ()
    version: int = ULTIMATE_LINEFEED_LEGACY_PROGRESS_VERSION
    attempted_candidates: int = 0


class UltimateLinefeedInterrupted(Exception):
    def __init__(self, progress_path: str):
        self.progress_path = progress_path
        super().__init__("UltimateMegaSuperLineFeedBruteForce interrupted; progress saved to %s" % progress_path)


def _ultimate_progress_shard_attempted(shard: dict[str, Any]) -> int:
    try:
        start_rank = int(shard.get("start_rank", 0) or 0)
        end_rank = int(shard.get("end_rank", start_rank) or start_rank)
        next_rank = int(shard.get("next_rank", start_rank) or start_rank)
    except (TypeError, ValueError):
        return 0
    if str(shard.get("status", "")) == "done":
        next_rank = end_rank
    next_rank = min(max(start_rank, next_rank), max(start_rank, end_rank))
    return max(0, next_rank - start_rank)


def ultimate_progress_attempted_floor(progress: UltimateLinefeedProgress | None) -> int:
    if progress is None:
        return 0
    shard_attempted = sum(
        _ultimate_progress_shard_attempted(shard)
        for shard in getattr(progress, "shards", ())
        if isinstance(shard, dict)
    )
    combination_rank = (
        max(0, int(getattr(progress, "combination_rank", 0) or 0))
        if getattr(progress, "phase", "") == "exhaustive"
        else 0
    )
    return max(
        0,
        int(getattr(progress, "attempted_candidates", 0) or 0),
        int(getattr(progress, "tested_candidates", 0) or 0),
        combination_rank,
        shard_attempted,
    )


def _ultimate_progress_shard_audit(
    progress: UltimateLinefeedProgress | None,
    operation_pools: tuple[tuple[SuperMegaLinefeedOperation, ...], ...],
    *,
    max_depth: int,
    shard_size: int = ULTIMATE_LINEFEED_PARALLEL_SHARD_SIZE,
) -> dict[str, int]:
    if progress is None:
        return {"saved": 0, "matched": 0, "pending": 0, "done": 0}
    saved = 0
    matched = 0
    pending = 0
    done = 0
    for item in getattr(progress, "shards", ()):
        if not isinstance(item, dict):
            continue
        saved += 1
        status = str(item.get("status", "")).strip().lower()
        if status == "done":
            done += 1
        else:
            pending += 1
        try:
            pool_index = int(item.get("pool_index", 0) or 0)
            depth = int(item.get("depth", 0) or 0)
            start_rank = int(item.get("start_rank", 0) or 0)
            end_rank = int(item.get("end_rank", 0) or 0)
        except (TypeError, ValueError):
            continue
        if pool_index < 0 or pool_index >= len(operation_pools):
            continue
        if depth < 1 or depth > max(1, max_depth):
            continue
        operation_pool = operation_pools[pool_index]
        if depth > len(operation_pool):
            continue
        total_ranks = math.comb(len(operation_pool), depth)
        expected_end = min(total_ranks, start_rank + max(1, int(shard_size or 1)))
        if start_rank < 0 or start_rank >= total_ranks:
            continue
        if end_rank == expected_end:
            matched += 1
    return {"saved": saved, "matched": matched, "pending": pending, "done": done}


@dataclass(frozen=True)
class UltimateParallelShardResult:
    shard: dict[str, Any]
    tested: int
    pruned: int
    state_count: int
    next_rank: int
    candidates: tuple[SuperMegaLinefeedCandidate, ...]
    terminal: bool = False
    error: str = ""


_ULTIMATE_PARALLEL_WORKER_CONTEXT: dict[str, Any] = {}


def _ultimate_parallel_worker_init(context: dict[str, Any]) -> None:
    global _ULTIMATE_PARALLEL_WORKER_CONTEXT
    _ULTIMATE_PARALLEL_WORKER_CONTEXT = dict(context)


def _ultimate_parallel_worker_run(shard: dict[str, Any]) -> UltimateParallelShardResult:
    context = _ULTIMATE_PARALLEL_WORKER_CONTEXT
    try:
        chunks = context["chunks"]
        root_stream = context["root_stream"]
        before = context["before"]
        operation_pool = context["operation_pools"][int(shard["pool_index"])]
        target_adler = context["target_adler"]
        progress_queue = context.get("progress_queue")
        stop_event = context.get("stop_event")
        root_parent_score = tuple(context["root_parent_score"])
        visual_min_coverage = float(context["visual_min_coverage"])
        visual_gallery_limit = int(context["visual_gallery_limit"])
        depth = int(shard["depth"])
        rank = int(shard["next_rank"])
        end_rank = int(shard["end_rank"])
        local_seen: set[str] = set()
        local_top: tuple[SuperMegaLinefeedCandidate, ...] = ()
        local_backfill: tuple[UltimateVisualBackfillCandidate, ...] = ()
        tested = 0
        pruned = 0
        state_count = 0
        terminal = False
        start_rank = int(shard.get("next_rank", shard.get("start_rank", 0)) or 0)
        shard_progress_key = "%s:%s:%s:%s" % (
            int(shard.get("pool_index", 0) or 0),
            int(shard.get("depth", 0) or 0),
            int(shard.get("start_rank", 0) or 0),
            int(shard.get("end_rank", 0) or 0),
        )
        last_progress_tested = 0
        last_progress_rank = start_rank

        def stop_requested() -> bool:
            is_set = getattr(stop_event, "is_set", None)
            if not callable(is_set):
                return False
            try:
                return bool(is_set())
            except (OSError, RuntimeError, ValueError):
                return False

        def report_progress(next_rank: int, *, force: bool = False) -> None:
            nonlocal last_progress_tested, last_progress_rank
            if progress_queue is None:
                return
            rank_delta = int(next_rank) - last_progress_rank
            tested_delta = tested - last_progress_tested
            if (
                not force
                and rank_delta < ULTIMATE_LINEFEED_PARALLEL_PROGRESS_STEP
                and tested_delta < ULTIMATE_LINEFEED_PARALLEL_PROGRESS_STEP
            ):
                return
            last_progress_tested = tested
            last_progress_rank = int(next_rank)
            try:
                progress_queue.put_nowait(
                    {
                        "key": shard_progress_key,
                        "next_rank": int(next_rank),
                        "tested": int(tested),
                        "pruned": int(pruned),
                        "attempted": max(0, int(next_rank) - start_rank),
                    }
                )
            except (AttributeError, OSError, ValueError):
                pass

        indices = _combination_indices_at_rank(len(operation_pool), depth, rank)
        while indices is not None and rank < end_rank:
            if (
                rank == start_rank
                or (rank - start_rank) % ULTIMATE_LINEFEED_PARALLEL_PROGRESS_STEP == 0
            ) and stop_requested():
                report_progress(rank, force=True)
                break
            combination = tuple(operation_pool[index] for index in indices)
            operations = _normalize_ultimate_operation_sequence(combination)
            candidate_stream = _replay_operations(root_stream, operations)
            next_indices = _next_combination_indices(indices, len(operation_pool), depth)
            if candidate_stream is None:
                pruned += 1
                rank += 1
                report_progress(rank)
                indices = next_indices
                continue
            stream_hash = _stream_state_key(candidate_stream)
            if stream_hash in local_seen:
                pruned += 1
                rank += 1
                report_progress(rank)
                indices = next_indices
                continue
            local_seen.add(stream_hash)
            tested += 1

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
                state_id=0,
                parent_id=0,
                source_offsets=tuple(operation.stream_offset for operation in operations),
                score=candidate_score,
            )
            state_count += 1
            local_top = _remember_ultimate_top_candidate(
                local_top,
                candidate,
                limit=max(ULTIMATE_LINEFEED_TOP_CANDIDATES, min(25, max(5, visual_gallery_limit))),
            )
            if visual_gallery_limit > 0:
                local_backfill = _remember_ultimate_visual_backfill_candidate(
                    local_backfill,
                    candidate,
                    tested=tested,
                    min_coverage=visual_min_coverage,
                    limit=max(1, min(visual_gallery_limit, 25)),
                )

            prune_reason = _ultimate_prune_reason(before, candidate.after)
            if (
                _ultimate_prune_is_fatal(prune_reason, depth)
                and candidate.after.adler_status != "adler_match"
            ):
                pruned += 1
            elif depth > 2 and candidate_score <= root_parent_score:
                pruned += 1
            if candidate.after.complete and (
                target_adler is None or candidate.after.adler_status == "adler_match"
            ):
                terminal = True
                rank += 1
                report_progress(rank)
                break
            rank += 1
            report_progress(rank)
            indices = next_indices

        report_progress(rank, force=True)
        by_hash: dict[str, SuperMegaLinefeedCandidate] = {}
        for candidate in local_top:
            by_hash[hashlib.blake2b(candidate.data, digest_size=16).hexdigest()] = candidate
        for item in local_backfill:
            by_hash.setdefault(
                hashlib.blake2b(item.candidate.data, digest_size=16).hexdigest(),
                item.candidate,
            )
        return UltimateParallelShardResult(
            shard=dict(shard),
            tested=tested,
            pruned=pruned,
            state_count=state_count,
            next_rank=rank,
            candidates=tuple(by_hash.values()),
            terminal=terminal,
        )
    except BaseException as exc:
        failed = dict(shard)
        return UltimateParallelShardResult(
            shard=failed,
            tested=0,
            pruned=0,
            state_count=0,
            next_rank=int(failed.get("next_rank", failed.get("start_rank", 0)) or 0),
            candidates=(),
            error="%s: %s" % (type(exc).__name__, exc),
        )


def _ultimate_parallel_mp_context():
    try:
        methods = multiprocessing.get_all_start_methods()
        method = "fork" if "fork" in methods else "spawn"
        return multiprocessing.get_context(method)
    except (RuntimeError, ValueError):
        return None


def _ultimate_close_parallel_progress_queue(progress_queue: Any) -> None:
    if progress_queue is None:
        return
    try:
        while True:
            progress_queue.get_nowait()
    except (queue.Empty, EOFError, OSError, ValueError, AttributeError):
        pass
    cancel_join_thread = getattr(progress_queue, "cancel_join_thread", None)
    if callable(cancel_join_thread):
        try:
            cancel_join_thread()
        except (OSError, RuntimeError, ValueError):
            pass
    close = getattr(progress_queue, "close", None)
    if callable(close):
        try:
            close()
        except (OSError, RuntimeError, ValueError):
            pass


def _ultimate_shutdown_parallel_executor(
    executor: ProcessPoolExecutor,
    *,
    futures: dict[Any, dict[str, Any]] | None = None,
    progress_queue: Any = None,
    stop_event: Any = None,
    grace_seconds: float = ULTIMATE_LINEFEED_PARALLEL_SHUTDOWN_GRACE_SECONDS,
) -> None:
    set_stop = getattr(stop_event, "set", None)
    if callable(set_stop):
        try:
            set_stop()
        except (OSError, RuntimeError, ValueError):
            pass
    pending_futures = tuple(futures) if futures else ()
    if pending_futures:
        try:
            _done, pending = wait(pending_futures, timeout=max(0.0, float(grace_seconds)))
        except (OSError, RuntimeError, ValueError):
            pending = pending_futures
        for future in pending:
            cancel = getattr(future, "cancel", None)
            if callable(cancel):
                try:
                    cancel()
                except (OSError, RuntimeError, ValueError):
                    pass
    processes = getattr(executor, "_processes", None)
    try:
        executor.shutdown(wait=False, cancel_futures=True)
    except TypeError:
        executor.shutdown(wait=False)
    if isinstance(processes, dict):
        deadline = time.monotonic() + max(0.0, float(grace_seconds))
        for process in tuple(processes.values()):
            poll = getattr(process, "poll", None)
            is_alive = getattr(process, "is_alive", None)
            alive = True
            if callable(poll):
                try:
                    alive = poll() is None
                except (OSError, RuntimeError, ValueError):
                    alive = True
            elif callable(is_alive):
                try:
                    alive = bool(is_alive())
                except (OSError, RuntimeError, ValueError):
                    alive = True
            if alive:
                terminate = getattr(process, "terminate", None)
                if callable(terminate):
                    try:
                        terminate()
                    except (OSError, RuntimeError, ValueError):
                        pass
        for process in tuple(processes.values()):
            join = getattr(process, "join", None)
            if callable(join):
                try:
                    join(max(0.0, deadline - time.monotonic()))
                except (OSError, RuntimeError, ValueError):
                    pass
    _ultimate_close_parallel_progress_queue(progress_queue)


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
    candidate_limit: int | None = None,
    beam_width: int = 8,
) -> tuple[list[SuperMegaLinefeedCandidate], set[str], int, int]:
    if not checkpoint_path or not os.path.exists(checkpoint_path):
        return [], set(), 1, 0

    entries: list[dict[str, object]] = []
    visited: set[str] = set()
    next_state_id = 1
    last_progress_at = time.monotonic()
    processed = 0
    rebuilt = 0

    def emit_load_progress(force: bool = False) -> None:
        nonlocal last_progress_at
        if progress is None:
            return
        now = time.monotonic()
        current = processed + rebuilt
        if (
            not force
            and current % ULTIMATE_LINEFEED_PROGRESS_STEP != 0
            and now - last_progress_at < ULTIMATE_LINEFEED_PROGRESS_INTERVAL_SECONDS
        ):
            return
        last_progress_at = now
        progress(
            progress_stage,
            min(current, max(1, int(progress_total))),
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
                raw_stream_hash = record.get("stream_hash")
                stream_hash = str(raw_stream_hash) if raw_stream_hash else ""
                if stream_hash and stream_hash in visited:
                    continue
                if stream_hash:
                    visited.add(stream_hash)
                state_id = int(record.get("state_id", next_state_id))
                next_state_id = max(next_state_id, state_id + 1)
                entries.append(
                    {
                        "index": len(entries),
                        "record": record,
                        "state_id": state_id,
                        "stream_hash": stream_hash,
                    }
                )
                processed += 1
                emit_load_progress()
    except OSError:
        return [], set(), 1, 0

    def record_rank(entry: dict[str, object]) -> tuple[object, ...]:
        record = entry["record"]
        if not isinstance(record, dict):
            return (9, 9, 0, 0, (), int(entry.get("state_id", 0)))
        raw_score = record.get("score", ())
        try:
            score = tuple(int(value) for value in raw_score) if isinstance(raw_score, list) else ()
        except (TypeError, ValueError):
            score = ()
        try:
            usable_scanlines = int(record.get("usable_scanlines", 0) or 0)
        except (TypeError, ValueError):
            usable_scanlines = 0
        try:
            error_offset = int(record.get("error_offset", -1) or -1)
        except (TypeError, ValueError):
            error_offset = -1
        return (
            0 if record.get("adler_status") == "adler_match" else 1,
            0 if record.get("status") in ("complete", "bad_adler") else 1,
            -usable_scanlines,
            -error_offset,
            tuple(-value for value in score),
            int(entry.get("state_id", 0)),
        )

    selected_entries = entries
    if candidate_limit is not None and int(candidate_limit) >= 0 and int(candidate_limit) < len(entries):
        selected: dict[int, dict[str, object]] = {}
        beam_count = max(1, int(beam_width))
        for entry in entries[-beam_count:]:
            selected[int(entry["index"])] = entry
        for entry in heapq.nsmallest(int(candidate_limit), entries, key=record_rank):
            selected[int(entry["index"])] = entry
        selected_entries = [
            entry
            for entry in entries
            if int(entry["index"]) in selected
        ]

    loaded: list[SuperMegaLinefeedCandidate] = []
    for entry in selected_entries:
        record = entry["record"]
        if not isinstance(record, dict):
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
        if stream_hash:
            visited.add(stream_hash)
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
                state_id=int(entry["state_id"]),
                parent_id=record.get("parent_id"),
                source_offsets=tuple(operation.stream_offset for operation in operations),
                score=score,
            )
        )
        rebuilt += 1
        emit_load_progress()

    emit_load_progress(force=bool(entries))
    return loaded, visited, next_state_id, len(entries)


def ultimate_linefeed_progress_path_from_checkpoint(checkpoint_path: str) -> str:
    if not checkpoint_path:
        return ""
    if checkpoint_path.endswith(".checkpoint.jsonl"):
        return checkpoint_path[: -len(".checkpoint.jsonl")] + ".progress.json"
    return checkpoint_path + ".progress.json"


def ultimate_linefeed_visual_gallery_path_from_progress(progress_path: str) -> str:
    if not progress_path:
        return ""
    if progress_path.endswith(".progress.json"):
        return progress_path[: -len(".progress.json")] + ".visual.json"
    if progress_path.endswith(".checkpoint.jsonl"):
        return progress_path[: -len(".checkpoint.jsonl")] + ".visual.json"
    return progress_path + ".visual.json"


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
    version = int(record.get("version", ULTIMATE_LINEFEED_LEGACY_PROGRESS_VERSION) or 0)
    if version not in (ULTIMATE_LINEFEED_LEGACY_PROGRESS_VERSION, ULTIMATE_LINEFEED_PROGRESS_VERSION):
        return None, "ultimate progress checkpoint %s has unsupported version %s" % (progress_path, version)
    expected = {
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
                int(record.get("parallel_workers", 0) or 0),
                int(record.get("shard_size", 0) or 0),
                tuple(
                    item
                    for item in record.get("shards", ())
                    if isinstance(item, dict)
                ),
                version,
                int(record.get("attempted_candidates", 0) or 0),
            ),
            "",
        )
    except (TypeError, ValueError) as exc:
        return None, "ultimate progress checkpoint %s has invalid fields: %s" % (progress_path, exc)


def load_ultimate_progress_for_source(
    data: bytes,
    progress_path: str,
    *,
    start_offset: int | None = None,
    target_adler: int | None = None,
    super_result: SuperMegaLinefeedProbeResult | None = None,
    max_depth: int = 4,
    max_offsets: int = 128,
) -> tuple[UltimateLinefeedProgress | None, str]:
    if not progress_path:
        return None, ""
    before = idat.analyze_idat_stream(data)
    if not before.supported:
        return None, before.reason
    if target_adler is None:
        target_adler = before.stored_adler
    try:
        _chunks, root_stream = _all_chunks_and_idat_stream(data)
    except png.PngFormatError as exc:
        return None, str(exc)
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
    return _load_ultimate_progress(
        progress_path,
        source_hash=source_hash,
        target_adler=target_adler,
        start_offset=start_offset,
        max_depth=max_depth,
        max_offsets=max_offsets,
        operation_pool_hash=_ultimate_operation_pool_hash(merged_operation_pool),
        focused_operation_pool_hash=_ultimate_operation_pool_hash(focused_operation_pool),
        broad_operation_pool_hash=_ultimate_operation_pool_hash(broad_operation_pool),
    )


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
    parallel_workers: int = 0,
    shard_size: int = 0,
    shards: tuple[dict[str, Any], ...] | list[dict[str, Any]] = (),
    attempted_candidates: int = 0,
) -> None:
    if not progress_path:
        return
    try:
        directory = os.path.dirname(progress_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        tmp_path = _hidden_tmp_path(progress_path)
        with open(tmp_path, "w", encoding="utf-8") as file:
            record = {
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
                    "attempted_candidates": max(
                        int(tested_candidates or 0),
                        int(attempted_candidates or 0),
                    ),
                    "pruned_candidates": pruned_candidates,
                    "state_count": state_count,
                    "budget": budget,
                    "timestamp": time.time(),
            }
            if int(parallel_workers or 0) > 1 or shards:
                record["parallel_workers"] = max(0, int(parallel_workers or 0))
                record["shard_size"] = max(0, int(shard_size or 0))
                record["shards"] = list(shards)
            json.dump(record, file, sort_keys=True)
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


def _combination_indices_at_rank(n: int, r: int, rank: int) -> tuple[int, ...] | None:
    if r <= 0 or n < r:
        return None
    total = math.comb(n, r)
    rank = int(rank)
    if rank < 0:
        rank = 0
    if rank >= total:
        return None
    indices: list[int] = []
    previous = -1
    remaining = rank
    for position in range(r):
        choices_left = r - position - 1
        last_candidate = n - choices_left
        for candidate in range(previous + 1, last_candidate):
            count = math.comb(n - candidate - 1, choices_left)
            if remaining < count:
                indices.append(candidate)
                previous = candidate
                break
            remaining -= count
    if len(indices) != r:
        return None
    return tuple(indices)


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


def _coerce_ultimate_reference_mode(reference_mode: object) -> str:
    mode = str(reference_mode or "exact").strip().lower()
    return mode if mode in ULTIMATE_LINEFEED_REFERENCE_MODES else "exact"


def _ultimate_image_hash_from_bytes(data: bytes) -> str:
    return hashlib.blake2b(data, digest_size=16).hexdigest()


def _ultimate_image_hash_from_image(image) -> str:
    try:
        rgba = image.convert("RGBA")
        payload = json.dumps(
            {"mode": "RGBA", "size": list(rgba.size)},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8") + rgba.tobytes()
        return hashlib.blake2b(payload, digest_size=16).hexdigest()
    except Exception:
        return ""


def _ultimate_png_size_from_bytes(data: bytes) -> tuple[int, int]:
    if not data:
        return (0, 0)
    try:
        from io import BytesIO
        from PIL import Image

        with Image.open(BytesIO(data)) as image:
            return tuple(int(value) for value in image.size)
    except Exception:
        return (0, 0)


def _ultimate_ihdr_size_from_data(data: bytes) -> tuple[int, int]:
    if not data:
        return (0, 0)
    offsets: list[int] = []
    if len(data) >= 24 and data[12:16] == b"IHDR":
        offsets.append(12)
    found = data.find(b"IHDR", 0, min(len(data), 128))
    if found >= 0 and found not in offsets:
        offsets.append(found)
    for offset in offsets:
        if offset < 4 or offset + 12 > len(data):
            continue
        width = int.from_bytes(data[offset + 4 : offset + 8], "big")
        height = int.from_bytes(data[offset + 8 : offset + 12], "big")
        if width > 0 and height > 0:
            return (width, height)
    return (0, 0)


def _ultimate_resize_rgba_to_size(image, size: tuple[int, int]):
    width, height = (int(size[0]), int(size[1]))
    if width <= 0 or height <= 0:
        return image
    try:
        if tuple(int(value) for value in image.size) == (width, height):
            return image
        return image.convert("RGBA").resize((width, height), _pil_lanczos_filter())
    except Exception:
        return image


def _coerce_ultimate_region(values: object) -> tuple[float, float, float, float] | None:
    if not isinstance(values, (list, tuple)) or len(values) != 4:
        return None
    try:
        x0, y0, x1, y1 = (float(value) for value in values)
    except (TypeError, ValueError):
        return None
    left = min(x0, x1)
    right = max(x0, x1)
    top = min(y0, y1)
    bottom = max(y0, y1)
    left = min(1.0, max(0.0, left))
    right = min(1.0, max(0.0, right))
    top = min(1.0, max(0.0, top))
    bottom = min(1.0, max(0.0, bottom))
    if right - left <= 0.001 or bottom - top <= 0.001:
        return None
    return (left, top, right, bottom)


def _coerce_ultimate_region_size(values: object) -> tuple[int, int]:
    if not isinstance(values, (list, tuple)) or len(values) != 2:
        return (0, 0)
    try:
        width, height = (int(value) for value in values)
    except (TypeError, ValueError):
        return (0, 0)
    return (max(0, width), max(0, height))


def _ultimate_reference_hash_from_record(record: dict[str, object], key: str) -> str:
    section = record.get(key)
    if isinstance(section, dict):
        return str(section.get("hash", "") or "")
    return str(record.get("%s_hash" % key, "") or "")


def _ultimate_reference_size_from_record(record: dict[str, object], key: str) -> tuple[int, int]:
    section = record.get(key)
    if isinstance(section, dict):
        return _coerce_ultimate_region_size(section.get("size"))
    return _coerce_ultimate_region_size(record.get("%s_size" % key))


def _coerce_ultimate_roi_match_mode(value: object) -> str:
    mode = str(value or "paired").strip().lower().replace("-", "_")
    if mode in {"paired", "pair"}:
        return "paired"
    if mode in {"search", "search_candidate", "search_reference"}:
        return "search"
    if mode in {"single", "source", "snapshot"}:
        return "single"
    if mode in {"negative", "anti_noise", "anti_noise_candidate"}:
        return "negative"
    return "paired"


def _ultimate_reference_regions_from_record(
    record: dict[str, object],
    *,
    path: str = "",
) -> tuple[UltimateReferenceRegions | None, str]:
    try:
        version = int(record.get("version", 0) or 0)
    except (TypeError, ValueError):
        version = 0
    if version not in (1, ULTIMATE_LINEFEED_REFERENCE_REGION_VERSION):
        return None, "reference region mapping has unsupported version %s" % version

    items = record.get("regions", ())
    if not isinstance(items, list):
        return None, "reference region mapping has no valid regions list"

    regions: list[UltimateReferenceRegion] = []
    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        candidate_region = _coerce_ultimate_region(item.get("candidate_region"))
        reference_region = _coerce_ultimate_region(item.get("reference_region"))
        if candidate_region is None or reference_region is None:
            continue
        try:
            weight = float(item.get("weight", 1.0))
        except (TypeError, ValueError):
            weight = 1.0
        if weight <= 0:
            weight = 1.0
        label = str(item.get("label", "") or "ROI %s" % index)
        match_mode = _coerce_ultimate_roi_match_mode(item.get("match_mode", "paired"))
        regions.append(
            UltimateReferenceRegion(
                candidate_region=candidate_region,
                reference_region=reference_region,
                weight=weight,
                label=label,
                match_mode=match_mode,
            )
        )
    if not regions:
        return None, "reference region mapping is empty"

    mapping = UltimateReferenceRegions(
        path=path,
        candidate_size=_ultimate_reference_size_from_record(record, "candidate"),
        reference_size=_ultimate_reference_size_from_record(record, "reference"),
        candidate_hash=_ultimate_reference_hash_from_record(record, "candidate"),
        reference_hash=_ultimate_reference_hash_from_record(record, "reference"),
        regions=tuple(regions),
    )
    return mapping, ""


def load_ultimate_reference_regions(
    path: str,
    *,
    candidate_data: bytes = b"",
    reference_image=None,
) -> tuple[UltimateReferenceRegions | None, str]:
    if not path:
        return None, ""
    try:
        with open(path, "r", encoding="utf-8") as file:
            record = json.load(file)
    except OSError as exc:
        return None, "could not load reference regions %s: %s" % (path, exc)
    except json.JSONDecodeError as exc:
        return None, "reference region mapping is not valid JSON: %s" % exc
    if not isinstance(record, dict):
        return None, "reference region mapping is not an object"

    mapping, warning = _ultimate_reference_regions_from_record(record, path=path)
    if mapping is None:
        return None, warning

    warnings: list[str] = []
    if candidate_data:
        actual_hash = _ultimate_image_hash_from_bytes(candidate_data)
        actual_size = _ultimate_png_size_from_bytes(candidate_data)
        if mapping.candidate_hash and mapping.candidate_hash != actual_hash:
            warnings.append("candidate snapshot hash differs from the ROI mapping")
        if mapping.candidate_size != (0, 0) and actual_size != (0, 0) and mapping.candidate_size != actual_size:
            warnings.append("candidate snapshot size differs from the ROI mapping")
    if reference_image is not None:
        actual_hash = _ultimate_image_hash_from_image(reference_image)
        actual_size = tuple(int(value) for value in getattr(reference_image, "size", (0, 0)))
        if mapping.reference_hash and actual_hash and mapping.reference_hash != actual_hash:
            warnings.append("reference image hash differs from the ROI mapping")
        if mapping.reference_size != (0, 0) and actual_size != (0, 0) and mapping.reference_size != actual_size:
            warnings.append("reference image size differs from the ROI mapping")

    return replace(mapping, warning="; ".join(warnings)), "; ".join(warnings)


def build_ultimate_reference_regions_record(
    *,
    candidate_size: tuple[int, int],
    reference_size: tuple[int, int],
    candidate_hash: str,
    reference_hash: str,
    regions: tuple[UltimateReferenceRegion, ...],
) -> dict[str, object]:
    return {
        "version": ULTIMATE_LINEFEED_REFERENCE_REGION_VERSION,
        "candidate": {
            "size": [int(candidate_size[0]), int(candidate_size[1])],
            "hash": str(candidate_hash or ""),
        },
        "reference": {
            "size": [int(reference_size[0]), int(reference_size[1])],
            "hash": str(reference_hash or ""),
        },
        "regions": [
            {
                "candidate_region": [float(value) for value in region.candidate_region],
                "reference_region": [float(value) for value in region.reference_region],
                "weight": float(region.weight),
                "label": region.label,
                "match_mode": region.match_mode,
            }
            for region in regions
        ],
    }


def _pil_lanczos_filter():
    try:
        from PIL import Image

        return getattr(getattr(Image, "Resampling", Image), "LANCZOS")
    except Exception:
        return 1


def _decode_ultimate_rgba_image(candidate_data: bytes):
    from io import BytesIO
    from PIL import Image

    image = Image.open(BytesIO(candidate_data)).convert("RGBA")
    image.load()
    return image


def _ultimate_exact_visual_score(candidate_data: bytes, reference_image) -> UltimateVisualScore:
    if isinstance(reference_image, UltimateVisualReference):
        reference_image = reference_image.image
    if reference_image is None:
        return UltimateVisualScore(None)
    try:
        from PIL import ImageChops, ImageStat

        candidate = _decode_ultimate_rgba_image(candidate_data)
        if candidate.size != reference_image.size:
            return UltimateVisualScore(
                float("inf"),
                "exact_rgba",
                0,
                raw_score=float("inf"),
                confidence=1.0,
                effective_score=float("inf"),
            )
        diff = ImageChops.difference(candidate, reference_image)
        score = float(sum(ImageStat.Stat(diff).mean))
        return UltimateVisualScore(score, "exact_rgba", 0, raw_score=score, confidence=1.0, effective_score=score)
    except Exception:
        return UltimateVisualScore(None)


def _resize_ultimate_gray(image, *, max_size: int = 256):
    width, height = image.size
    if width <= 0 or height <= 0:
        return image.convert("L")
    scale = min(1.0, float(max_size) / float(max(width, height)))
    new_size = (max(1, int(round(width * scale))), max(1, int(round(height * scale))))
    return image.convert("L").resize(new_size, _pil_lanczos_filter())


def _ultimate_hash_bits(values: list[int]) -> tuple[bool, ...]:
    if not values:
        return ()
    average = sum(values) / len(values)
    return tuple(value >= average for value in values)


def _ultimate_image_values(image) -> list[int]:
    if hasattr(image, "get_flattened_data"):
        return list(image.get_flattened_data())
    return list(image.getdata())


def _ultimate_ahash_bits(image, *, size: int = 8) -> tuple[bool, ...]:
    small = image.convert("L").resize((size, size), _pil_lanczos_filter())
    return _ultimate_hash_bits(_ultimate_image_values(small))


def _ultimate_dhash_bits(image, *, size: int = 8) -> tuple[bool, ...]:
    small = image.convert("L").resize((size + 1, size), _pil_lanczos_filter())
    pixels = _ultimate_image_values(small)
    bits: list[bool] = []
    for y in range(size):
        row = y * (size + 1)
        for x in range(size):
            bits.append(pixels[row + x] > pixels[row + x + 1])
    return tuple(bits)


def _ultimate_hamming_ratio(left: tuple[bool, ...], right: tuple[bool, ...]) -> float:
    if not left or not right:
        return 1.0
    count = min(len(left), len(right))
    if count <= 0:
        return 1.0
    distance = sum(1 for index in range(count) if left[index] != right[index])
    return distance / count


def _ultimate_edge_image(gray):
    from PIL import ImageFilter, ImageOps

    return ImageOps.autocontrast(gray.filter(ImageFilter.FIND_EDGES))


def _ultimate_patch_features(gray, *, grid: int = 8) -> tuple[UltimatePatchFeature, ...]:
    from PIL import ImageStat

    width, height = gray.size
    if width <= 0 or height <= 0:
        return ()
    features: list[UltimatePatchFeature] = []
    index = 0
    for row in range(grid):
        top = row * height // grid
        bottom = max(top + 1, (row + 1) * height // grid)
        for column in range(grid):
            left = column * width // grid
            right = max(left + 1, (column + 1) * width // grid)
            patch = gray.crop((left, top, min(width, right), min(height, bottom)))
            edge = _ultimate_edge_image(patch)
            edge_density = min(1.0, max(0.0, ImageStat.Stat(edge).mean[0] / 255.0))
            contrast = min(1.0, max(0.0, ImageStat.Stat(patch).stddev[0] / 128.0))
            info = min(1.0, max(0.0, edge_density * 0.6 + contrast * 0.4))
            features.append(
                UltimatePatchFeature(
                    index=index,
                    edge_density=edge_density,
                    contrast=contrast,
                    ahash=_ultimate_ahash_bits(patch),
                    dhash=_ultimate_dhash_bits(patch),
                    info=info,
                )
            )
            index += 1
    return tuple(features)


def _ultimate_patch_distance(
    candidate: UltimatePatchFeature,
    reference: UltimatePatchFeature,
) -> float:
    return (
        0.45 * _ultimate_hamming_ratio(candidate.dhash, reference.dhash)
        + 0.35 * _ultimate_hamming_ratio(candidate.ahash, reference.ahash)
        + 0.10 * abs(candidate.edge_density - reference.edge_density)
        + 0.10 * abs(candidate.contrast - reference.contrast)
    )


def _ultimate_auto_patch_score(
    candidate_features: tuple[UltimatePatchFeature, ...],
    reference_features: tuple[UltimatePatchFeature, ...],
    *,
    limit: int = 12,
) -> tuple[float, int]:
    pairs: list[tuple[float, float, int, int]] = []
    informative_candidates = [feature for feature in candidate_features if feature.info >= 0.02]
    informative_references = [feature for feature in reference_features if feature.info >= 0.02]
    for candidate in informative_candidates:
        for reference in informative_references:
            distance = _ultimate_patch_distance(candidate, reference)
            min_info = min(candidate.info, reference.info)
            pairs.append((distance - 0.08 * min_info, distance, candidate.index, reference.index))
    pairs.sort()

    used_candidates: set[int] = set()
    used_references: set[int] = set()
    selected_distances: list[float] = []
    for _rank, distance, candidate_index, reference_index in pairs:
        if candidate_index in used_candidates or reference_index in used_references:
            continue
        used_candidates.add(candidate_index)
        used_references.add(reference_index)
        selected_distances.append(distance)
        if len(selected_distances) >= limit:
            break
    if not selected_distances:
        return 100.0, 0
    return 100.0 * (sum(selected_distances) / len(selected_distances)), len(selected_distances)


def _ultimate_projection_score(candidate_edges, reference_edges) -> float:
    size = 64
    left = candidate_edges.resize((size, size), _pil_lanczos_filter())
    right = reference_edges.resize((size, size), _pil_lanczos_filter())
    left_values = _ultimate_image_values(left)
    right_values = _ultimate_image_values(right)

    def rows(values: list[int]) -> list[float]:
        return [
            sum(values[row * size : (row + 1) * size]) / float(size * 255)
            for row in range(size)
        ]

    def columns(values: list[int]) -> list[float]:
        return [
            sum(values[column + row * size] for row in range(size)) / float(size * 255)
            for column in range(size)
        ]

    row_distance = sum(abs(a - b) for a, b in zip(rows(left_values), rows(right_values))) / size
    column_distance = sum(abs(a - b) for a, b in zip(columns(left_values), columns(right_values))) / size
    return 100.0 * ((row_distance + column_distance) / 2.0)


def _ultimate_global_layout_score(candidate_edges, reference_edges) -> float:
    return 100.0 * (
        0.5
        * _ultimate_hamming_ratio(
            _ultimate_ahash_bits(candidate_edges, size=16),
            _ultimate_ahash_bits(reference_edges, size=16),
        )
        + 0.5
        * _ultimate_hamming_ratio(
            _ultimate_dhash_bits(candidate_edges, size=16),
            _ultimate_dhash_bits(reference_edges, size=16),
        )
    )


def _ultimate_global_hash_score(candidate_gray, reference_gray) -> float:
    try:
        import imagehash

        left = imagehash.phash(candidate_gray.resize((64, 64), _pil_lanczos_filter()))
        right = imagehash.phash(reference_gray.resize((64, 64), _pil_lanczos_filter()))
        hash_bits = getattr(getattr(left, "hash", None), "size", 64) or 64
        return 100.0 * float(left - right) / float(hash_bits)
    except Exception:
        return 100.0 * _ultimate_hamming_ratio(
            _ultimate_ahash_bits(candidate_gray, size=16),
            _ultimate_ahash_bits(reference_gray, size=16),
        )


def _ultimate_phash_bits(gray) -> tuple[bool, ...]:
    try:
        import imagehash

        value = imagehash.phash(gray.resize((64, 64), _pil_lanczos_filter()))
        raw_hash = getattr(value, "hash", None)
        if raw_hash is None:
            raise ValueError("missing phash payload")
        return tuple(bool(item) for row in raw_hash for item in row)
    except Exception:
        return _ultimate_ahash_bits(gray, size=16)


def _ultimate_fast_gray_hash_score(candidate_gray, reference_gray) -> float:
    return 100.0 * (
        0.5
        * _ultimate_hamming_ratio(
            _ultimate_ahash_bits(candidate_gray, size=16),
            _ultimate_ahash_bits(reference_gray, size=16),
        )
        + 0.5
        * _ultimate_hamming_ratio(
            _ultimate_dhash_bits(candidate_gray, size=16),
            _ultimate_dhash_bits(reference_gray, size=16),
        )
    )


def _ultimate_crop_region(image, region: tuple[float, float, float, float]):
    width, height = image.size
    left = max(0, min(width - 1, int(round(region[0] * width))))
    top = max(0, min(height - 1, int(round(region[1] * height))))
    right = max(left + 1, min(width, int(round(region[2] * width))))
    bottom = max(top + 1, min(height, int(round(region[3] * height))))
    return image.crop((left, top, right, bottom))


def _ultimate_region_area(region: tuple[float, float, float, float]) -> float:
    return max(0.0, region[2] - region[0]) * max(0.0, region[3] - region[1])


def _ultimate_shift_region_pixels(
    image,
    region: tuple[float, float, float, float],
    *,
    dx: int = 0,
    dy: int = 0,
) -> tuple[float, float, float, float]:
    width, height = image.size
    if width <= 0 or height <= 0:
        return region
    shift_x = float(dx) / float(width)
    shift_y = float(dy) / float(height)
    region_width = max(0.001, region[2] - region[0])
    region_height = max(0.001, region[3] - region[1])
    left = min(1.0 - region_width, max(0.0, region[0] + shift_x))
    top = min(1.0 - region_height, max(0.0, region[1] + shift_y))
    return (left, top, left + region_width, top + region_height)


def _ultimate_roi_descriptor(crop, *, size: tuple[int, int] = (96, 96)) -> UltimateRoiDescriptor:
    from PIL import ImageStat

    gray = crop.convert("L").resize(size, _pil_lanczos_filter())
    edges = _ultimate_edge_image(gray)
    return UltimateRoiDescriptor(
        gray=gray,
        edges=edges,
        edge_density=min(1.0, max(0.0, ImageStat.Stat(edges).mean[0] / 255.0)),
        contrast=min(1.0, max(0.0, ImageStat.Stat(gray).stddev[0] / 128.0)),
        ahash=_ultimate_ahash_bits(gray, size=16),
        dhash=_ultimate_dhash_bits(gray, size=16),
        phash=_ultimate_phash_bits(gray),
    )


def _ultimate_roi_descriptor_score(
    candidate: UltimateRoiDescriptor,
    reference: UltimateRoiDescriptor,
) -> float:
    layout_score = _ultimate_global_layout_score(candidate.edges, reference.edges)
    projection_score = _ultimate_projection_score(candidate.edges, reference.edges)
    hash_score = 100.0 * (
        0.50 * _ultimate_hamming_ratio(candidate.ahash, reference.ahash)
        + 0.50 * _ultimate_hamming_ratio(candidate.dhash, reference.dhash)
    )
    texture_score = 100.0 * (
        0.50 * abs(candidate.edge_density - reference.edge_density)
        + 0.50 * abs(candidate.contrast - reference.contrast)
    )
    phash_score = 100.0 * _ultimate_hamming_ratio(candidate.phash, reference.phash)
    return float(
        0.35 * layout_score
        + 0.25 * projection_score
        + 0.20 * hash_score
        + 0.10 * phash_score
        + 0.10 * texture_score
    )


def _ultimate_roi_pair_score(candidate_crop, reference_crop) -> float:
    return _ultimate_roi_descriptor_score(
        _ultimate_roi_descriptor(candidate_crop),
        _ultimate_roi_descriptor(reference_crop),
    )


def _ultimate_paired_region_score(
    candidate_image,
    candidate_region: tuple[float, float, float, float],
    reference_crop,
) -> float:
    best_score: float | None = None
    radius = ULTIMATE_LINEFEED_ROI_LOCAL_RADIUS_PX
    step = max(1, ULTIMATE_LINEFEED_ROI_LOCAL_STEP_PX)
    offsets = range(-radius, radius + 1, step)
    reference_feature = _ultimate_roi_descriptor(reference_crop)
    for dy in offsets:
        for dx in offsets:
            shifted = _ultimate_shift_region_pixels(
                candidate_image,
                candidate_region,
                dx=dx,
                dy=dy,
            )
            candidate_crop = _ultimate_crop_region(candidate_image, shifted)
            score = _ultimate_roi_descriptor_score(
                _ultimate_roi_descriptor(candidate_crop),
                reference_feature,
            )
            if best_score is None or score < best_score:
                best_score = score
    return float(best_score if best_score is not None else 100.0)


def _ultimate_roi_quick_feature(crop) -> UltimateRoiQuickFeature:
    from PIL import ImageStat

    gray = crop.convert("L").resize((48, 48), _pil_lanczos_filter())
    edge = _ultimate_edge_image(gray)
    return UltimateRoiQuickFeature(
        edge_density=min(1.0, max(0.0, ImageStat.Stat(edge).mean[0] / 255.0)),
        contrast=min(1.0, max(0.0, ImageStat.Stat(gray).stddev[0] / 128.0)),
        ahash=_ultimate_ahash_bits(gray),
        dhash=_ultimate_dhash_bits(gray),
    )


def _ultimate_roi_quick_distance(
    candidate: UltimateRoiQuickFeature,
    reference: UltimateRoiQuickFeature,
) -> float:
    return (
        0.45 * _ultimate_hamming_ratio(candidate.dhash, reference.dhash)
        + 0.35 * _ultimate_hamming_ratio(candidate.ahash, reference.ahash)
        + 0.10 * abs(candidate.edge_density - reference.edge_density)
        + 0.10 * abs(candidate.contrast - reference.contrast)
    )


def _ultimate_search_regions(
    window: tuple[float, float],
    *,
    steps: int = 5,
) -> tuple[tuple[float, float, float, float], ...]:
    width = min(1.0, max(0.02, float(window[0])))
    height = min(1.0, max(0.02, float(window[1])))
    x_span = max(0.0, 1.0 - width)
    y_span = max(0.0, 1.0 - height)
    x_steps = 1 if x_span <= 0.0001 else max(2, steps)
    y_steps = 1 if y_span <= 0.0001 else max(2, steps)
    xs = [0.0] if x_steps == 1 else [x_span * index / float(x_steps - 1) for index in range(x_steps)]
    ys = [0.0] if y_steps == 1 else [y_span * index / float(y_steps - 1) for index in range(y_steps)]
    return tuple((x, y, x + width, y + height) for y in ys for x in xs)


def _ultimate_refined_search_regions(
    image,
    region: tuple[float, float, float, float],
) -> tuple[tuple[float, float, float, float], ...]:
    radius = ULTIMATE_LINEFEED_ROI_LOCAL_RADIUS_PX
    step = max(1, ULTIMATE_LINEFEED_ROI_LOCAL_STEP_PX)
    offsets = range(-radius, radius + 1, step)
    refined: list[tuple[float, float, float, float]] = []
    seen: set[tuple[float, float, float, float]] = set()
    for dy in offsets:
        for dx in offsets:
            shifted = _ultimate_shift_region_pixels(image, region, dx=dx, dy=dy)
            key = tuple(round(value, 5) for value in shifted)
            if key in seen:
                continue
            seen.add(key)
            refined.append(shifted)
    return tuple(refined)


def _ultimate_best_region_search_score(
    target_image,
    probe_crop,
    probe_region: tuple[float, float, float, float],
) -> float:
    base_window = (
        max(0.02, probe_region[2] - probe_region[0]),
        max(0.02, probe_region[3] - probe_region[1]),
    )
    quick_probe = _ultimate_roi_quick_feature(probe_crop)
    quick_candidates: list[tuple[float, tuple[float, float, float, float]]] = []
    seen: set[tuple[float, float, float, float]] = set()
    for scale in ULTIMATE_LINEFEED_ROI_SEARCH_SCALES:
        window = (
            max(0.02, min(1.0, base_window[0] * float(scale))),
            max(0.02, min(1.0, base_window[1] * float(scale))),
        )
        for target_region in _ultimate_search_regions(window):
            key = tuple(round(value, 5) for value in target_region)
            if key in seen:
                continue
            seen.add(key)
            target_crop = _ultimate_crop_region(target_image, target_region)
            quick_score = _ultimate_roi_quick_distance(
                _ultimate_roi_quick_feature(target_crop),
                quick_probe,
            )
            quick_candidates.append((quick_score, target_region))
    quick_candidates.sort(key=lambda item: item[0])

    best_score: float | None = None
    probe_feature = _ultimate_roi_descriptor(probe_crop)
    for _quick_score, target_region in quick_candidates[: min(4, len(quick_candidates))]:
        for refined_region in _ultimate_refined_search_regions(target_image, target_region):
            target_crop = _ultimate_crop_region(target_image, refined_region)
            score = _ultimate_roi_descriptor_score(
                _ultimate_roi_descriptor(target_crop),
                probe_feature,
            )
            if best_score is None or score < best_score:
                best_score = score
    return float(best_score if best_score is not None else 100.0)


def _ultimate_negative_region_score(candidate_crop) -> float:
    feature = _ultimate_roi_descriptor(candidate_crop)
    return float(100.0 * (0.65 * feature.edge_density + 0.35 * feature.contrast))


def _ultimate_manual_roi_confidence(
    *,
    weighted_area: float,
    matched_count: int,
) -> float:
    if matched_count <= 0:
        return 0.0
    area_score = min(1.0, max(0.0, weighted_area) / 0.12)
    count_score = min(1.0, matched_count / 3.0)
    return min(1.0, max(0.35, 0.60 * area_score + 0.40 * count_score))


def _ultimate_effective_roi_score(raw_score: float, confidence: float) -> float:
    confidence = min(1.0, max(0.0, float(confidence)))
    return float(raw_score * confidence + 100.0 * (1.0 - confidence))


def _ultimate_manual_roi_visual_score(
    candidate_data: bytes,
    reference_image: UltimateVisualReference,
) -> UltimateVisualScore:
    reference = reference_image.image
    regions = reference_image.regions
    source = reference_image.source_image
    if regions is None or not regions.regions:
        return UltimateVisualScore(None)
    try:
        candidate = _decode_ultimate_rgba_image(candidate_data)
        weighted_total = 0.0
        weight_total = 0.0
        weighted_area = 0.0
        matched_count = 0
        for region in regions.regions:
            weight = max(0.0, float(region.weight))
            if weight <= 0:
                continue
            mode = _coerce_ultimate_roi_match_mode(region.match_mode)
            candidate_crop = _ultimate_crop_region(candidate, region.candidate_region)
            reference_crop = (
                _ultimate_crop_region(reference, region.reference_region)
                if reference is not None
                else None
            )
            if mode == "negative":
                score = _ultimate_negative_region_score(candidate_crop)
                area = _ultimate_region_area(region.candidate_region)
            elif mode == "single":
                if source is None:
                    continue
                source_crop = _ultimate_crop_region(source, region.candidate_region)
                score = _ultimate_paired_region_score(
                    candidate,
                    region.candidate_region,
                    source_crop,
                )
                area = _ultimate_region_area(region.candidate_region)
            elif mode == "search":
                if reference is None or reference_crop is None:
                    continue
                if region.candidate_region == (0.0, 0.0, 1.0, 1.0):
                    score = _ultimate_best_region_search_score(
                        candidate,
                        reference_crop,
                        region.reference_region,
                    )
                    area = _ultimate_region_area(region.reference_region)
                else:
                    score = _ultimate_best_region_search_score(
                        reference,
                        candidate_crop,
                        region.candidate_region,
                    )
                    area = _ultimate_region_area(region.candidate_region)
            else:
                if reference_crop is None:
                    continue
                score = _ultimate_paired_region_score(
                    candidate,
                    region.candidate_region,
                    reference_crop,
                )
                area = _ultimate_region_area(region.candidate_region)
            weighted_total += score * weight
            weight_total += weight
            weighted_area += area * weight
            matched_count += 1
        if matched_count <= 0 or weight_total <= 0:
            return UltimateVisualScore(None)
        raw_score = weighted_total / weight_total
        confidence = _ultimate_manual_roi_confidence(
            weighted_area=weighted_area / weight_total,
            matched_count=matched_count,
        )
        effective_score = _ultimate_effective_roi_score(raw_score, confidence)
        return UltimateVisualScore(
            effective_score,
            "similar_manual_roi",
            matched_count,
            raw_score=raw_score,
            confidence=confidence,
            effective_score=effective_score,
        )
    except Exception:
        return UltimateVisualScore(None)


def _ultimate_similar_visual_score(candidate_data: bytes, reference_image) -> UltimateVisualScore:
    reference = reference_image
    if isinstance(reference_image, UltimateVisualReference):
        if reference_image.regions is not None and reference_image.regions.regions:
            return _ultimate_manual_roi_visual_score(candidate_data, reference_image)
        reference = reference_image.image
    if reference is None:
        return UltimateVisualScore(None)
    try:
        candidate = _decode_ultimate_rgba_image(candidate_data)
        candidate_gray = _resize_ultimate_gray(candidate)
        if isinstance(reference_image, UltimateVisualReference) and reference_image.gray is not None:
            reference_gray = reference_image.gray
            reference_edges = reference_image.edges or _ultimate_edge_image(reference_gray)
            reference_patches = reference_image.patches
        else:
            reference_gray = _resize_ultimate_gray(reference)
            reference_edges = _ultimate_edge_image(reference_gray)
            reference_patches = _ultimate_patch_features(reference_gray)
        candidate_edges = _ultimate_edge_image(candidate_gray)
        patch_score, matched_count = _ultimate_auto_patch_score(
            _ultimate_patch_features(candidate_gray),
            reference_patches,
        )
        layout_score = _ultimate_global_layout_score(candidate_edges, reference_edges)
        projection_score = _ultimate_projection_score(candidate_edges, reference_edges)
        hash_score = _ultimate_global_hash_score(candidate_gray, reference_gray)
        score = (
            0.50 * patch_score
            + 0.25 * layout_score
            + 0.15 * projection_score
            + 0.10 * hash_score
        )
        score = float(score)
        return UltimateVisualScore(
            score,
            "similar_auto_patch",
            matched_count,
            raw_score=score,
            confidence=1.0,
            effective_score=score,
        )
    except Exception:
        return UltimateVisualScore(None)


def _ultimate_source_visual_image(source_data: bytes):
    if not source_data:
        return None
    try:
        return _decode_ultimate_rgba_image(source_data)
    except Exception:
        pass
    for repairer in (
        idat.rebuild_visual_idat_preview,
        idat.rebuild_tolerant_idat_salvage,
        idat.rebuild_partial_idat_blackfill,
    ):
        try:
            repair = repairer(source_data)
        except Exception:
            repair = None
        if repair is None:
            continue
        try:
            return _decode_ultimate_rgba_image(repair.data)
        except Exception:
            continue
    return None


def _ultimate_visual_reference(
    reference_image,
    *,
    reference_mode: str,
    reference_regions: UltimateReferenceRegions | None = None,
    source_data: bytes = b"",
) -> UltimateVisualReference:
    mode = _coerce_ultimate_reference_mode(reference_mode)
    source_image = _ultimate_source_visual_image(source_data) if source_data else None
    if reference_image is None:
        return UltimateVisualReference(None, mode, source_image=source_image)
    if mode != "similar":
        return UltimateVisualReference(reference_image, mode, source_image=source_image)
    target_size = _ultimate_ihdr_size_from_data(source_data)
    if target_size == (0, 0) and source_image is not None:
        target_size = tuple(int(value) for value in getattr(source_image, "size", (0, 0)))
    reference_image = _ultimate_resize_rgba_to_size(reference_image, target_size)
    try:
        gray = _resize_ultimate_gray(reference_image)
        edges = _ultimate_edge_image(gray)
        patches = _ultimate_patch_features(gray)
        return UltimateVisualReference(
            reference_image,
            mode,
            gray=gray,
            edges=edges,
            patches=patches,
            regions=reference_regions,
            source_image=source_image,
        )
    except Exception:
        return UltimateVisualReference(
            reference_image,
            mode,
            regions=reference_regions,
            source_image=source_image,
        )


def _ultimate_visual_score(
    candidate_data: bytes,
    reference_image,
    *,
    reference_mode: str = "exact",
) -> UltimateVisualScore:
    if isinstance(reference_image, UltimateVisualReference):
        reference_mode = reference_image.mode
    if _coerce_ultimate_reference_mode(reference_mode) == "similar":
        return _ultimate_similar_visual_score(candidate_data, reference_image)
    return _ultimate_exact_visual_score(candidate_data, reference_image)


def _ultimate_visual_distance(candidate_data: bytes, reference_image) -> float | None:
    return _ultimate_exact_visual_score(candidate_data, reference_image).score


def _attach_ultimate_visual_score(
    candidate: SuperMegaLinefeedCandidate,
    reference_image,
    *,
    reference_mode: str = "exact",
) -> SuperMegaLinefeedCandidate:
    score = _ultimate_visual_score(
        candidate.data,
        reference_image,
        reference_mode=reference_mode,
    )
    if score.score is None:
        return candidate
    return replace(
        candidate,
        visual_score=score.score,
        visual_score_kind=score.kind,
        matched_patch_count=score.matched_patch_count,
        visual_raw_score=score.raw_score,
        visual_confidence=score.confidence,
        visual_effective_score=score.effective_score,
    )


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
    candidate_score = candidate.score or super_mega_linefeed_score(candidate.after, len(candidate.operations))
    return (
        0 if candidate.after.adler_status == "adler_match" else 1,
        0 if candidate.after.complete else 1,
        -candidate.after.usable_scanlines,
        -candidate.after.complete_scanlines,
        -candidate_score[1] if len(candidate_score) > 1 else 0,
        -candidate_score[4] if len(candidate_score) > 4 else 0,
        abs(candidate.after.decompressed_size - candidate.after.expected_size),
        -(candidate.after.error_offset if candidate.after.error_offset is not None else -1),
        visual_score is None,
        float("inf") if visual_score is None else visual_score,
        -candidate_score[0],
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


def _ultimate_checkpoint_rehydrate_limit(*, beam_width: int, visual_gallery_limit: int) -> int:
    beam_count = max(1, int(beam_width))
    _gallery_count = max(0, int(visual_gallery_limit))
    return max(
        beam_count,
        ULTIMATE_LINEFEED_TOP_CANDIDATES,
    )


def _ultimate_checkpoint_seed_candidates(
    candidates: tuple[SuperMegaLinefeedCandidate, ...],
    *,
    beam_width: int,
    visual_gallery_limit: int,
) -> tuple[SuperMegaLinefeedCandidate, ...]:
    if not candidates:
        return ()
    beam_count = max(1, int(beam_width))
    seed_limit = min(
        len(candidates),
        _ultimate_checkpoint_rehydrate_limit(
            beam_width=beam_width,
            visual_gallery_limit=visual_gallery_limit,
        ),
    )
    selected: dict[int, SuperMegaLinefeedCandidate] = {}
    for candidate in candidates[-beam_count:]:
        selected[candidate.state_id] = candidate
    for candidate in sorted(candidates, key=_ultimate_top_candidate_rank)[:seed_limit]:
        selected[candidate.state_id] = candidate
    return tuple(sorted(selected.values(), key=lambda candidate: candidate.state_id))


def _coerce_ultimate_visual_gallery_limit(value: object) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return ULTIMATE_LINEFEED_VISUAL_GALLERY_LIMIT


def _coerce_ultimate_visual_min_coverage(value: object) -> float:
    try:
        coverage = float(value)
    except (TypeError, ValueError):
        return ULTIMATE_LINEFEED_VISUAL_MIN_COVERAGE
    return min(1.0, max(0.0, coverage))


def _ultimate_operation_hash(operations: tuple[SuperMegaLinefeedOperation, ...]) -> str:
    payload = json.dumps(
        [_operation_to_json(operation) for operation in operations],
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.blake2b(payload, digest_size=12).hexdigest()


def _ultimate_visual_candidate_rank(
    candidate: SuperMegaLinefeedCandidate,
    *,
    coverage: float,
    visual_score: float | None,
) -> tuple[object, ...]:
    status_rank = {
        "complete": 0,
        "bad_adler": 1,
        "partial": 2,
    }.get(candidate.after.status, 9)
    adler_rank = {
        "adler_match": 0,
        "adler_rebuilt": 1,
        "adler_mismatch": 2,
        "adler_unknown": 3,
    }.get(candidate.after.adler_status, 9)
    expected_delta = abs(candidate.after.decompressed_size - candidate.after.expected_size)
    error_offset = candidate.after.error_offset if candidate.after.error_offset is not None else -1
    visual_rank = 1_000_000_000_000.0 if visual_score is None else float(visual_score)
    score = candidate.score or super_mega_linefeed_score(candidate.after, len(candidate.operations))
    return (
        0 if candidate.after.adler_status == "adler_match" else 1,
        -candidate.after.usable_scanlines,
        -candidate.after.complete_scanlines,
        -coverage,
        status_rank,
        adler_rank,
        expected_delta,
        -error_offset,
        visual_score is None,
        visual_rank,
        len(candidate.operations),
        tuple(-value for value in score),
        candidate.state_id,
    )


def _ultimate_visual_candidate_structural_rank(
    candidate: SuperMegaLinefeedCandidate,
    *,
    coverage: float,
) -> tuple[object, ...]:
    status_rank = {
        "complete": 0,
        "bad_adler": 1,
        "partial": 2,
    }.get(candidate.after.status, 9)
    adler_rank = {
        "adler_match": 0,
        "adler_rebuilt": 1,
        "adler_mismatch": 2,
        "adler_unknown": 3,
    }.get(candidate.after.adler_status, 9)
    expected_delta = abs(candidate.after.decompressed_size - candidate.after.expected_size)
    error_offset = candidate.after.error_offset if candidate.after.error_offset is not None else -1
    return (
        0 if candidate.after.adler_status == "adler_match" else 1,
        -candidate.after.usable_scanlines,
        -candidate.after.complete_scanlines,
        -coverage,
        status_rank,
        adler_rank,
        expected_delta,
        -error_offset,
    )


def _ultimate_visual_candidate_from_candidate(
    candidate: SuperMegaLinefeedCandidate,
    *,
    tested: int,
    reference_image,
    reference_mode: str,
    min_coverage: float,
) -> UltimateVisualCandidate | None:
    if not candidate.after.supported:
        return None
    if candidate.after.status not in ("complete", "bad_adler", "partial"):
        return None
    if candidate.after.height <= 0:
        return None
    coverage = candidate.after.usable_scanlines / candidate.after.height
    if coverage < min_coverage:
        return None

    repair = idat.rebuild_visual_idat_preview(candidate.data)
    if repair is None:
        return None

    visual_score = _ultimate_visual_score(
        repair.data,
        reference_image,
        reference_mode=reference_mode,
    )
    scored_candidate = (
        replace(
            candidate,
            visual_score=visual_score.score,
            visual_score_kind=visual_score.kind,
            matched_patch_count=visual_score.matched_patch_count,
            visual_raw_score=visual_score.raw_score,
            visual_confidence=visual_score.confidence,
            visual_effective_score=visual_score.effective_score,
        )
        if visual_score.score is not None
        else candidate
    )
    preview_hash = hashlib.blake2b(repair.data, digest_size=16).hexdigest()
    scanline_source = candidate.after.recovered_scanlines or repair.data
    scanline_hash = hashlib.blake2b(scanline_source, digest_size=16).hexdigest()
    operation_hash = _ultimate_operation_hash(candidate.operations)
    diversity_key = "%s:%s" % (scanline_hash, operation_hash)
    return UltimateVisualCandidate(
        candidate=scored_candidate,
        preview_data=repair.data,
        preview_strategy=repair.strategy,
        visual_hash=preview_hash,
        scanline_hash=scanline_hash,
        operation_hash=operation_hash,
        diversity_key=diversity_key,
        rank=_ultimate_visual_candidate_rank(
            scored_candidate,
            coverage=coverage,
            visual_score=visual_score.score,
        ),
        coverage=coverage,
        tested_candidates=max(0, int(tested)),
    )


def _ultimate_visual_candidate_basic_coverage(
    candidate: SuperMegaLinefeedCandidate,
    *,
    min_coverage: float,
) -> float | None:
    if not candidate.after.supported:
        return None
    if candidate.after.status not in ("complete", "bad_adler", "partial"):
        return None
    if candidate.after.height <= 0:
        return None
    coverage = candidate.after.usable_scanlines / candidate.after.height
    if coverage < min_coverage:
        return None
    return coverage


def _ultimate_visual_backfill_key(candidate: SuperMegaLinefeedCandidate) -> str:
    return hashlib.blake2b(candidate.data, digest_size=16).hexdigest()


def _ultimate_visual_backfill_rank(item: UltimateVisualBackfillCandidate) -> tuple[object, ...]:
    return (
        item.structural_rank,
        item.tested_candidates,
        item.candidate.state_id,
    )


def _remember_ultimate_visual_backfill_candidate(
    candidates: tuple[UltimateVisualBackfillCandidate, ...],
    candidate: SuperMegaLinefeedCandidate,
    *,
    tested: int,
    min_coverage: float,
    limit: int,
) -> tuple[UltimateVisualBackfillCandidate, ...]:
    by_key = {_ultimate_visual_backfill_key(item.candidate): item for item in candidates}
    _remember_ultimate_visual_backfill_candidate_inplace(
        by_key,
        candidate,
        tested=tested,
        min_coverage=min_coverage,
        limit=limit,
    )
    return tuple(sorted(by_key.values(), key=_ultimate_visual_backfill_rank))


def _remember_ultimate_visual_backfill_candidate_inplace(
    candidates_by_key: dict[str, UltimateVisualBackfillCandidate],
    candidate: SuperMegaLinefeedCandidate,
    *,
    tested: int,
    min_coverage: float,
    limit: int,
) -> bool:
    if limit <= 0:
        return False
    coverage = _ultimate_visual_candidate_basic_coverage(
        candidate,
        min_coverage=min_coverage,
    )
    if coverage is None:
        return False
    structural_rank = _ultimate_visual_candidate_structural_rank(
        candidate,
        coverage=coverage,
    )
    backfill = UltimateVisualBackfillCandidate(
        candidate=candidate,
        tested_candidates=max(0, int(tested)),
        structural_rank=structural_rank,
        coverage=coverage,
    )
    key = _ultimate_visual_backfill_key(candidate)
    existing = candidates_by_key.get(key)
    updated = False
    if existing is None or _ultimate_visual_backfill_rank(backfill) < _ultimate_visual_backfill_rank(existing):
        candidates_by_key[key] = backfill
        updated = True
    pool_limit = max(1, int(limit)) * 4
    if len(candidates_by_key) > pool_limit:
        kept = sorted(candidates_by_key.items(), key=lambda item: _ultimate_visual_backfill_rank(item[1]))[
            :pool_limit
        ]
        candidates_by_key.clear()
        candidates_by_key.update(kept)
        updated = True
    return updated


def _fill_ultimate_visual_gallery_from_backfill(
    candidates: tuple[UltimateVisualCandidate, ...],
    backfill_candidates: tuple[UltimateVisualBackfillCandidate, ...],
    *,
    reference_image,
    reference_mode: str,
    min_coverage: float,
    limit: int,
    progress: UltimateInterruptFlushProgressCallback | None = None,
) -> tuple[UltimateVisualCandidate, ...]:
    if limit <= 0 or len(candidates) >= max(1, int(limit)):
        return candidates
    by_key = {item.diversity_key: item for item in candidates}
    seen_data = {_ultimate_visual_backfill_key(item.candidate) for item in candidates}
    for backfill in sorted(backfill_candidates, key=_ultimate_visual_backfill_rank):
        if len(by_key) >= max(1, int(limit)):
            break
        if _ultimate_visual_backfill_key(backfill.candidate) in seen_data:
            continue
        visual_candidate = _ultimate_visual_candidate_from_candidate(
            backfill.candidate,
            tested=backfill.tested_candidates,
            reference_image=reference_image,
            reference_mode=reference_mode,
            min_coverage=min_coverage,
        )
        seen_data.add(_ultimate_visual_backfill_key(backfill.candidate))
        if visual_candidate is None:
            continue
        existing = by_key.get(visual_candidate.diversity_key)
        if existing is None or visual_candidate.rank < existing.rank:
            previous_count = len(by_key)
            by_key[visual_candidate.diversity_key] = visual_candidate
            if progress is not None and len(by_key) > previous_count:
                progress(len(by_key), max(1, int(limit)))
    return tuple(sorted(by_key.values(), key=lambda item: item.rank)[:limit])


def _remember_ultimate_visual_candidate(
    candidates: tuple[UltimateVisualCandidate, ...],
    candidate: SuperMegaLinefeedCandidate,
    *,
    tested: int,
    reference_image,
    min_coverage: float,
    limit: int,
    reference_mode: str = "exact",
) -> tuple[UltimateVisualCandidate, ...]:
    if limit <= 0:
        return candidates
    coverage = _ultimate_visual_candidate_basic_coverage(
        candidate,
        min_coverage=min_coverage,
    )
    if coverage is None:
        return candidates
    candidate_structural_rank = _ultimate_visual_candidate_structural_rank(
        candidate,
        coverage=coverage,
    )
    if candidates:
        best_structural_rank = min(
            _ultimate_visual_candidate_structural_rank(
                item.candidate,
                coverage=item.coverage,
            )
            for item in candidates
        )
        if candidate_structural_rank > best_structural_rank:
            return candidates
    if len(candidates) >= max(1, int(limit)):
        candidate_structural_rank = _ultimate_visual_candidate_rank(
            candidate,
            coverage=coverage,
            visual_score=None,
        )
        worst_structural_rank = max(
            _ultimate_visual_candidate_rank(
                item.candidate,
                coverage=item.coverage,
                visual_score=None,
            )
            for item in candidates
        )
        if candidate_structural_rank > worst_structural_rank:
            return candidates
    visual_candidate = _ultimate_visual_candidate_from_candidate(
        candidate,
        tested=tested,
        reference_image=reference_image,
        reference_mode=reference_mode,
        min_coverage=min_coverage,
    )
    if visual_candidate is None:
        return candidates

    by_key = {item.diversity_key: item for item in candidates}
    existing = by_key.get(visual_candidate.diversity_key)
    if existing is None or visual_candidate.rank < existing.rank:
        by_key[visual_candidate.diversity_key] = visual_candidate
    return tuple(sorted(by_key.values(), key=lambda item: item.rank)[:limit])


def _ultimate_visual_preview_dir(gallery_path: str) -> str:
    return os.path.join(os.path.dirname(gallery_path), *ULTIMATE_LINEFEED_VISUAL_PREVIEW_FOLDER)


def _safe_ultimate_visual_filename_part(value: object) -> str:
    safe = "".join(
        char if char.isalnum() or char in ("-", "_", ".") else "_"
        for char in str(value)
    )
    safe = safe.strip("._-")
    return safe[:96] or "candidate"


def _ultimate_visual_preview_name(index: int, candidate: UltimateVisualCandidate) -> str:
    after = candidate.candidate.after
    return (
        "_VisualCandidate_%03d_tested_%09d_state_%09d_%s_of_%s_%s_%s.png"
        % (
            index,
            candidate.tested_candidates,
            candidate.candidate.state_id,
            after.usable_scanlines,
            after.height,
            _safe_ultimate_visual_filename_part(after.status),
            "rebuilt_adler_preview",
        )
    )


def _jsonable_rank_value(value: object) -> object:
    if isinstance(value, tuple):
        return [_jsonable_rank_value(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _ultimate_visual_candidate_to_json(
    candidate: UltimateVisualCandidate,
    *,
    base_dir: str,
) -> dict[str, object]:
    preview_path = candidate.preview_path
    preview_label = preview_path
    if preview_path:
        try:
            preview_label = os.path.relpath(preview_path, base_dir)
        except ValueError:
            preview_label = preview_path
    after = candidate.candidate.after
    return {
        "state_id": candidate.candidate.state_id,
        "parent_id": candidate.candidate.parent_id,
        "tested_candidates": candidate.tested_candidates,
        "status": after.status,
        "adler_status": after.adler_status,
        "preview_kind": "rebuilt_adler_preview",
        "preview_strategy": candidate.preview_strategy,
        "preview_path": preview_label,
        "usable_scanlines": after.usable_scanlines,
        "complete_scanlines": after.complete_scanlines,
        "total_scanlines": after.height,
        "coverage": candidate.coverage,
        "decompressed_size": after.decompressed_size,
        "expected_size": after.expected_size,
        "error_offset": after.error_offset,
        "operation_count": len(candidate.candidate.operations),
        "operations": [
            _operation_to_json(operation)
            for operation in candidate.candidate.operations
        ],
        "score": list(candidate.candidate.score),
        "rank": [_jsonable_rank_value(value) for value in candidate.rank],
        "visual_score": candidate.candidate.visual_score,
        "visual_score_kind": candidate.candidate.visual_score_kind,
        "visual_raw_score": candidate.candidate.visual_raw_score,
        "visual_confidence": candidate.candidate.visual_confidence,
        "visual_effective_score": candidate.candidate.visual_effective_score,
        "matched_patch_count": candidate.candidate.matched_patch_count,
        "visual_hash": candidate.visual_hash,
        "scanline_hash": candidate.scanline_hash,
        "operation_hash": candidate.operation_hash,
        "diversity_key": candidate.diversity_key,
    }


def _json_rank_tuple(value: object) -> tuple[object, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(_json_rank_tuple(item) if isinstance(item, list) else item for item in value)


def _json_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _json_float(value: object, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _json_optional_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _load_ultimate_visual_gallery(
    gallery_path: str,
    *,
    source_hash: str,
    limit: int,
) -> tuple[UltimateVisualCandidate, ...]:
    if limit <= 0 or not gallery_path or not os.path.exists(gallery_path):
        return ()
    try:
        with open(gallery_path, "r", encoding="utf-8") as file:
            record = json.load(file)
    except (OSError, json.JSONDecodeError):
        return ()
    if not isinstance(record, dict):
        return ()
    if str(record.get("source_hash", "")) != str(source_hash):
        return ()

    base_dir = os.path.dirname(gallery_path)
    loaded: list[UltimateVisualCandidate] = []
    raw_candidates = record.get("candidates", ())
    if not isinstance(raw_candidates, list):
        return ()

    for item in raw_candidates:
        if not isinstance(item, dict):
            continue
        preview_path = str(item.get("preview_path", ""))
        if not preview_path:
            continue
        if not os.path.isabs(preview_path):
            preview_path = os.path.join(base_dir, preview_path)
        try:
            with open(preview_path, "rb") as file:
                preview_data = file.read()
        except OSError:
            continue

        operations = tuple(
            operation
            for operation in (
                _operation_from_json(operation_record)
                for operation_record in item.get("operations", ())
            )
            if operation is not None
        )
        status = str(item.get("status", "partial"))
        total_scanlines = _json_int(item.get("total_scanlines"), 0)
        usable_scanlines = _json_int(item.get("usable_scanlines"), 0)
        complete_scanlines = _json_int(item.get("complete_scanlines"), usable_scanlines)
        analysis = idat.IdatStreamAnalysis(
            supported=True,
            complete=status in ("complete", "bad_adler"),
            status=status,
            height=total_scanlines,
            expected_size=_json_int(item.get("expected_size"), 0),
            decompressed_size=_json_int(item.get("decompressed_size"), 0),
            complete_scanlines=complete_scanlines,
            usable_scanlines=usable_scanlines,
            error_offset=(
                _json_int(item.get("error_offset"), -1)
                if item.get("error_offset") is not None
                else None
            ),
            adler_status=str(item.get("adler_status", "adler_unknown")),
            source_kind="restored_visual_gallery",
        )
        raw_score = item.get("score", ())
        score = tuple(_json_int(value) for value in raw_score) if isinstance(raw_score, list) else ()
        candidate = SuperMegaLinefeedCandidate(
            preview_data,
            operations,
            analysis,
            analysis,
            state_id=_json_int(item.get("state_id"), 0),
            parent_id=(
                _json_int(item.get("parent_id"), 0)
                if item.get("parent_id") is not None
                else None
            ),
            source_offsets=tuple(operation.stream_offset for operation in operations),
            score=score,
            visual_score=_json_optional_float(item.get("visual_score")),
            visual_score_kind=str(item.get("visual_score_kind", "")),
            matched_patch_count=_json_int(item.get("matched_patch_count"), 0),
            visual_raw_score=_json_optional_float(item.get("visual_raw_score")),
            visual_confidence=_json_optional_float(item.get("visual_confidence")),
            visual_effective_score=_json_optional_float(item.get("visual_effective_score")),
        )
        preview_hash = hashlib.blake2b(preview_data, digest_size=16).hexdigest()
        rank = _json_rank_tuple(item.get("rank"))
        if not rank:
            rank = _ultimate_visual_candidate_rank(
                candidate,
                coverage=_json_float(item.get("coverage"), 0.0),
                visual_score=candidate.visual_score,
            )
        loaded.append(
            UltimateVisualCandidate(
                candidate=candidate,
                preview_data=preview_data,
                preview_strategy=str(item.get("preview_strategy", "")),
                visual_hash=str(item.get("visual_hash") or preview_hash),
                scanline_hash=str(item.get("scanline_hash") or preview_hash),
                operation_hash=str(item.get("operation_hash") or _ultimate_operation_hash(operations)),
                diversity_key=str(item.get("diversity_key") or preview_hash),
                rank=rank,
                coverage=_json_float(item.get("coverage"), 0.0),
                tested_candidates=_json_int(item.get("tested_candidates"), 0),
                preview_path=preview_path,
            )
        )

    return tuple(sorted(loaded, key=lambda candidate: candidate.rank)[:limit])


def _remove_stale_ultimate_visual_previews(preview_dir: str) -> None:
    try:
        names = os.listdir(preview_dir)
    except OSError:
        return
    for name in names:
        if not name.startswith("_VisualCandidate_") or not name.endswith(".png"):
            continue
        try:
            os.remove(os.path.join(preview_dir, name))
        except OSError:
            continue


def _write_ultimate_visual_gallery(
    gallery_path: str,
    candidates: tuple[UltimateVisualCandidate, ...],
    *,
    limit: int,
    reference_mode: str = "exact",
    reference_regions_path: str = "",
    source_hash: str = "",
    phase: str = "",
    depth: int = 0,
    tested_candidates: int = 0,
    state_count: int = 0,
) -> tuple[tuple[UltimateVisualCandidate, ...], int]:
    if limit <= 0 or not gallery_path:
        return candidates, 0
    try:
        base_dir = os.path.dirname(gallery_path)
        if base_dir:
            os.makedirs(base_dir, exist_ok=True)
        preview_dir = _ultimate_visual_preview_dir(gallery_path)
        os.makedirs(preview_dir, exist_ok=True)
        _remove_stale_ultimate_visual_previews(preview_dir)

        written: list[UltimateVisualCandidate] = []
        for index, candidate in enumerate(candidates[:limit], start=1):
            preview_path = os.path.join(
                preview_dir,
                _ultimate_visual_preview_name(index, candidate),
            )
            with open(preview_path, "wb") as file:
                file.write(candidate.preview_data)
            written.append(replace(candidate, preview_path=preview_path))

        record = {
            "version": ULTIMATE_LINEFEED_VISUAL_PROGRESS_VERSION,
            "source_hash": source_hash,
            "reference_mode": _coerce_ultimate_reference_mode(reference_mode),
            "reference_regions_path": reference_regions_path,
            "phase": phase,
            "depth": depth,
            "tested_candidates": tested_candidates,
            "state_count": state_count,
            "limit": limit,
            "visual_gallery_limit": limit,
            "preview_count": len(written),
            "preview_kind": "rebuilt_adler_preview",
            "preview_directory": os.path.relpath(preview_dir, base_dir) if base_dir else preview_dir,
            "timestamp": time.time(),
            "candidates": [
                _ultimate_visual_candidate_to_json(candidate, base_dir=base_dir)
                for candidate in written
            ],
        }
        tmp_path = _hidden_tmp_path(gallery_path)
        with open(tmp_path, "w", encoding="utf-8") as file:
            json.dump(record, file, sort_keys=True, indent=2)
            file.write("\n")
        os.replace(tmp_path, gallery_path)
        return tuple(written), len(written)
    except OSError:
        return candidates, 0


def _touch_ultimate_visual_gallery_progress(
    gallery_path: str,
    *,
    source_hash: str = "",
    reference_mode: str = "exact",
    reference_regions_path: str = "",
    phase: str = "",
    depth: int = 0,
    tested_candidates: int = 0,
    state_count: int = 0,
    limit: int = ULTIMATE_LINEFEED_VISUAL_GALLERY_LIMIT,
) -> bool:
    if limit <= 0 or not gallery_path or not os.path.exists(gallery_path):
        return False
    try:
        with open(gallery_path, "r", encoding="utf-8") as file:
            record = json.load(file)
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(record, dict):
        return False
    if source_hash and str(record.get("source_hash", "")) != str(source_hash):
        return False

    record["reference_mode"] = _coerce_ultimate_reference_mode(reference_mode)
    record["reference_regions_path"] = reference_regions_path
    record["phase"] = phase
    record["depth"] = depth
    record["tested_candidates"] = tested_candidates
    record["state_count"] = state_count
    record["limit"] = limit
    record["visual_gallery_limit"] = limit
    record["timestamp"] = time.time()

    try:
        tmp_path = _hidden_tmp_path(gallery_path)
        with open(tmp_path, "w", encoding="utf-8") as file:
            json.dump(record, file, sort_keys=True, indent=2)
            file.write("\n")
        os.replace(tmp_path, gallery_path)
    except OSError:
        return False
    return True


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
    reference_mode: str = "exact",
    reference_regions_path: str = "",
    progress: QueueProgressCallback | None = None,
    candidate_preview: UltimateCandidatePreviewCallback | None = None,
    interrupt_flush_progress: UltimateInterruptFlushProgressCallback | None = None,
    interrupt_repeat_warning: UltimateInterruptRepeatCallback | None = None,
    resume_status: UltimateResumeStatusCallback | None = None,
    progress_path: str = "",
    resume_progress: bool = True,
    visual_gallery_limit: int = ULTIMATE_LINEFEED_VISUAL_GALLERY_LIMIT,
    visual_min_coverage: float = ULTIMATE_LINEFEED_VISUAL_MIN_COVERAGE,
    visual_gallery_path: str = "",
    ultimate_workers: int = 0,
) -> UltimateLinefeedProbeResult:
    strategy = "UltimateMegaSuperLineFeedBruteForce"
    reference_mode = _coerce_ultimate_reference_mode(reference_mode)
    visual_gallery_limit = _coerce_ultimate_visual_gallery_limit(visual_gallery_limit)
    visual_min_coverage = _coerce_ultimate_visual_min_coverage(visual_min_coverage)
    ultimate_workers = max(0, int(ultimate_workers or 0))
    reference_image, reference_warning = _load_ultimate_reference_image(reference_path)
    reference_regions = None
    if reference_mode == "similar" and reference_image is not None and reference_regions_path:
        reference_regions, regions_warning = load_ultimate_reference_regions(
            reference_regions_path,
            candidate_data=data,
            reference_image=reference_image,
        )
        if regions_warning:
            reference_warning = "; ".join(item for item in (reference_warning, regions_warning) if item)
    reference_context = _ultimate_visual_reference(
        reference_image,
        reference_mode=reference_mode,
        reference_regions=reference_regions,
        source_data=data,
    )
    budget_limit = None if budget is None else max(0, int(budget))
    progress_total = UNBOUNDED_PROGRESS_TOTAL if budget_limit is None else max(1, budget_limit)
    displayed_progress = 0
    progress_started = False
    attempted_candidates = 0
    resume_attempted_floor = 0
    resume_committed_count = 0
    resume_matched_shards = 0
    resume_pending_shards = 0
    resume_saved_workers = 0
    resume_fast_used = False
    resume_rejected_reason = ""

    def emit_ultimate_progress(count: int, *, force: bool = False) -> None:
        nonlocal displayed_progress, progress_started, attempted_candidates
        try:
            value = int(count)
        except (TypeError, ValueError):
            value = 0
        value = min(max(0, value), progress_total)
        attempted_candidates = max(attempted_candidates, value)
        if progress is None:
            return
        if progress_started and value < displayed_progress:
            value = displayed_progress
        if progress_started and value == displayed_progress and not force:
            return
        displayed_progress = value
        progress_started = True
        progress(strategy, value, progress_total)

    if not progress_path:
        progress_path = ultimate_linefeed_progress_path_from_checkpoint(checkpoint_path)
    if not visual_gallery_path and visual_gallery_limit > 0:
        visual_gallery_path = ultimate_linefeed_visual_gallery_path_from_progress(progress_path)
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
            reference_mode=reference_mode,
            reference_regions_path=reference_regions_path,
            progress_path=progress_path,
            visual_gallery_path=visual_gallery_path,
            visual_gallery_limit=visual_gallery_limit,
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
                reference_mode=reference_mode,
                reference_regions_path=reference_regions_path,
                progress_path=progress_path,
                visual_gallery_path=visual_gallery_path,
                visual_gallery_limit=visual_gallery_limit,
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
            reference_mode=reference_mode,
            reference_regions_path=reference_regions_path,
            progress_path=progress_path,
            visual_gallery_path=visual_gallery_path,
            visual_gallery_limit=visual_gallery_limit,
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
    operation_pools = (
        focused_operation_pool,
        merged_operation_pool,
    )
    if not progress_path:
        progress_path = ultimate_linefeed_progress_path_from_checkpoint(checkpoint_path)
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
        resume_attempted_floor = ultimate_progress_attempted_floor(progress_resume)
        resume_committed_count = int(progress_resume.tested_candidates or 0)
        resume_saved_workers = int(progress_resume.parallel_workers or 0)
        shard_audit = _ultimate_progress_shard_audit(
            progress_resume,
            operation_pools,
            max_depth=max_depth,
        )
        resume_matched_shards = int(shard_audit.get("matched", 0) or 0)
        resume_pending_shards = int(shard_audit.get("pending", 0) or 0)
        if (
            progress_resume.version >= ULTIMATE_LINEFEED_PROGRESS_VERSION
            and progress_resume.phase == "exhaustive"
            and int(shard_audit.get("saved", 0) or 0) > 0
            and resume_attempted_floor > 0
            and resume_matched_shards == 0
        ):
            resume_rejected_reason = "cursor shards do not match the current operation pool"
            if progress_warning:
                progress_warning = "%s; %s" % (progress_warning, resume_rejected_reason)
            else:
                progress_warning = resume_rejected_reason
            progress_resume = None
        elif (
            progress_resume.version >= ULTIMATE_LINEFEED_PROGRESS_VERSION
            and progress_resume.phase == "exhaustive"
        ):
            resume_fast_used = True
            if progress is not None:
                emit_ultimate_progress(resume_attempted_floor, force=True)
    if resume_status is not None:
        if resume_fast_used:
            resume_status(
                {
                    "fast_resume_used": True,
                    "attempted_floor": resume_attempted_floor,
                    "committed_count": resume_committed_count,
                    "matched_shards": resume_matched_shards,
                    "pending_shards": resume_pending_shards,
                    "current_workers": ultimate_workers,
                    "saved_workers": resume_saved_workers,
                }
            )
        elif resume_rejected_reason:
            resume_status(
                {
                    "fast_resume_used": False,
                    "fast_resume_rejected_reason": resume_rejected_reason,
                    "attempted_floor": resume_attempted_floor,
                    "committed_count": resume_committed_count,
                    "matched_shards": resume_matched_shards,
                    "pending_shards": resume_pending_shards,
                    "current_workers": ultimate_workers,
                    "saved_workers": resume_saved_workers,
                }
            )
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
    fast_resume_exhaustive = (
        progress_resume is not None
        and progress_resume.version >= ULTIMATE_LINEFEED_PROGRESS_VERSION
        and progress_resume.phase == "exhaustive"
    )
    fast_resume_complete = (
        progress_resume is not None
        and progress_resume.version >= ULTIMATE_LINEFEED_PROGRESS_VERSION
        and progress_resume.phase == "complete"
    )
    if fast_resume_exhaustive or fast_resume_complete:
        checkpoint_candidates = []
        checkpoint_visited = set()
        next_state_id = 1
        resumed_states = 0
    else:
        checkpoint_rehydrate_limit = _ultimate_checkpoint_rehydrate_limit(
            beam_width=beam_width,
            visual_gallery_limit=visual_gallery_limit,
        )
        emit_ultimate_progress(0, force=True)
        checkpoint_candidates, checkpoint_visited, next_state_id, resumed_states = _load_ultimate_checkpoint(
            checkpoint_path,
            source_hash=source_hash,
            root_stream=root_stream,
            chunks=chunks,
            before=before,
            target_adler=target_adler,
            progress=(
                (lambda _stage, loaded, _total: emit_ultimate_progress(loaded))
                if progress is not None
                else None
            ),
            progress_total=progress_total,
            progress_stage=strategy,
            candidate_limit=checkpoint_rehydrate_limit,
            beam_width=beam_width,
        )
    checkpoint_candidates = tuple(checkpoint_candidates)
    checkpoint_seed_candidates = _ultimate_checkpoint_seed_candidates(
        checkpoint_candidates,
        beam_width=beam_width,
        visual_gallery_limit=visual_gallery_limit,
    )
    visited = {_stream_state_key(root_stream), *checkpoint_visited}
    frontier = (
        list(checkpoint_candidates[-max(1, beam_width) :])
        if checkpoint_candidates
        else [root]
    )
    best: SuperMegaLinefeedCandidate | None = None
    best_score = root_score
    top_candidates: tuple[SuperMegaLinefeedCandidate, ...] = ()
    visual_candidates: tuple[UltimateVisualCandidate, ...] = _load_ultimate_visual_gallery(
        visual_gallery_path,
        source_hash=source_hash,
        limit=visual_gallery_limit,
    )
    visual_backfill_candidates: dict[str, UltimateVisualBackfillCandidate] = {}
    visual_preview_count = len(visual_candidates)
    visual_gallery_dirty = False

    def remember_visual_candidate(candidate: SuperMegaLinefeedCandidate, tested_count: int) -> None:
        nonlocal visual_backfill_candidates, visual_candidates, visual_gallery_dirty
        updated = _remember_ultimate_visual_candidate(
            visual_candidates,
            candidate,
            tested=tested_count,
            reference_image=reference_context,
            reference_mode=reference_mode,
            min_coverage=visual_min_coverage,
            limit=visual_gallery_limit,
        )
        if updated != visual_candidates:
            visual_candidates = updated
            visual_gallery_dirty = True
        elif len(visual_candidates) < max(1, visual_gallery_limit):
            _remember_ultimate_visual_backfill_candidate_inplace(
                visual_backfill_candidates,
                candidate,
                tested=tested_count,
                min_coverage=visual_min_coverage,
                limit=visual_gallery_limit,
            )

    for candidate in checkpoint_seed_candidates:
        top_candidates = _remember_ultimate_top_candidate(top_candidates, candidate)
        if progress_resume is None:
            remember_visual_candidate(candidate, 0)
        candidate_score = candidate.score or super_mega_linefeed_score(candidate.after, len(candidate.operations))
        if candidate_score > best_score:
            best = candidate
            best_score = candidate_score

    tested = 0
    pruned = 0
    budget_exhausted = False
    reached_depth = 0
    if progress_resume is not None:
        tested = max(tested, progress_resume.tested_candidates)
        attempted_candidates = max(attempted_candidates, ultimate_progress_attempted_floor(progress_resume))
        pruned = max(pruned, progress_resume.pruned_candidates)
        next_state_id = max(next_state_id, progress_resume.state_count)
        reached_depth = max(reached_depth, progress_resume.depth)
        resumed_states += 1
        if visual_candidates and visual_gallery_path:
            _touch_ultimate_visual_gallery_progress(
                visual_gallery_path,
                source_hash=source_hash,
                reference_mode=reference_mode,
                reference_regions_path=reference_regions_path,
                phase=progress_resume.phase,
                depth=progress_resume.depth,
                tested_candidates=tested,
                state_count=next_state_id,
                limit=visual_gallery_limit,
            )
    current_phase = "frontier"
    current_depth = reached_depth
    current_pool_index = 0
    current_combination_rank = 0
    current_combination_indices: tuple[int, ...] | None = None
    current_shards: dict[str, dict[str, Any]] = {}
    last_progress_at = time.monotonic()

    def save_progress_snapshot(
        *,
        phase: str | None = None,
        depth: int | None = None,
        pool_index: int | None = None,
        combination_rank: int | None = None,
        combination_indices: tuple[int, ...] | None = None,
        force_visual: bool = False,
        interrupt_progress: UltimateInterruptFlushProgressCallback | None = None,
    ) -> None:
        nonlocal visual_candidates, visual_preview_count, visual_gallery_dirty
        snapshot_phase = current_phase if phase is None else phase
        snapshot_depth = current_depth if depth is None else depth
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
            phase=snapshot_phase,
            depth=snapshot_depth,
            pool_index=current_pool_index if pool_index is None else pool_index,
            combination_rank=current_combination_rank if combination_rank is None else combination_rank,
            combination_indices=current_combination_indices if combination_indices is None else combination_indices,
            tested_candidates=tested,
            pruned_candidates=pruned,
            state_count=next_state_id,
            budget=budget_limit,
            parallel_workers=ultimate_workers,
            shard_size=ULTIMATE_LINEFEED_PARALLEL_SHARD_SIZE if ultimate_workers >= 2 else 0,
            shards=tuple(
                sorted(
                    current_shards.values(),
                    key=lambda item: (
                        int(item.get("pool_index", 0) or 0),
                        int(item.get("depth", 0) or 0),
                        int(item.get("start_rank", 0) or 0),
                    ),
                )
            ),
            attempted_candidates=max(attempted_candidates, displayed_progress, tested),
        )
        if (
            visual_gallery_limit > 0
            and visual_gallery_path
            and (snapshot_phase == "complete" or force_visual)
            and visual_backfill_candidates
            and len(visual_candidates) < visual_gallery_limit
        ):
            filled = _fill_ultimate_visual_gallery_from_backfill(
                visual_candidates,
                tuple(visual_backfill_candidates.values()),
                reference_image=reference_context,
                reference_mode=reference_mode,
                min_coverage=visual_min_coverage,
                limit=visual_gallery_limit,
                progress=interrupt_progress,
            )
            if filled != visual_candidates:
                visual_candidates = filled
                visual_gallery_dirty = True
        if (
            visual_gallery_limit > 0
            and visual_gallery_path
            and (
                snapshot_phase == "complete"
                or force_visual
                or (
                    visual_gallery_dirty
                    and tested % ULTIMATE_LINEFEED_VISUAL_WRITE_STEP == 0
                )
            )
        ):
            visual_candidates, visual_preview_count = _write_ultimate_visual_gallery(
                visual_gallery_path,
                visual_candidates,
                limit=visual_gallery_limit,
                reference_mode=reference_mode,
                reference_regions_path=reference_regions_path,
                source_hash=source_hash,
                phase=snapshot_phase,
                depth=snapshot_depth,
                tested_candidates=tested,
                state_count=next_state_id,
            )
            visual_gallery_dirty = False
        elif (
            visual_gallery_limit > 0
            and visual_gallery_path
            and visual_candidates
            and not visual_gallery_dirty
        ):
            _touch_ultimate_visual_gallery_progress(
                visual_gallery_path,
                source_hash=source_hash,
                reference_mode=reference_mode,
                reference_regions_path=reference_regions_path,
                phase=snapshot_phase,
                depth=snapshot_depth,
                tested_candidates=tested,
                state_count=next_state_id,
                limit=visual_gallery_limit,
            )

    previous_sigint_handler = None
    sigint_handler_installed = False
    interrupt_requested = False
    repeated_interrupts = 0
    reported_repeated_interrupts = 0
    parallel_stop_event: Any = None

    def repeat_interrupt_warning(signum, frame):
        nonlocal repeated_interrupts
        repeated_interrupts += 1

    def report_pending_interrupt_warning() -> None:
        nonlocal reported_repeated_interrupts
        if (
            repeated_interrupts <= reported_repeated_interrupts
            or interrupt_repeat_warning is None
        ):
            return
        reported_repeated_interrupts = repeated_interrupts
        interrupt_repeat_warning(repeated_interrupts)

    def request_parallel_stop() -> None:
        event = parallel_stop_event
        set_stop = getattr(event, "set", None)
        if callable(set_stop):
            try:
                set_stop()
            except (OSError, RuntimeError, ValueError):
                pass

    def restore_sigint_handler() -> None:
        nonlocal sigint_handler_installed
        if not sigint_handler_installed:
            return
        try:
            signal.signal(signal.SIGINT, previous_sigint_handler)
        except (OSError, ValueError):
            pass
        sigint_handler_installed = False

    def mark_running_shards_pending() -> None:
        for shard in current_shards.values():
            if str(shard.get("status", "")) == "running":
                shard["status"] = "pending"

    def finalize_interrupted_run(*, restore_handler: bool = True) -> None:
        mark_running_shards_pending()
        try:
            save_progress_snapshot(
                force_visual=True,
                interrupt_progress=interrupt_flush_progress,
            )
        finally:
            if restore_handler:
                restore_sigint_handler()

    def raise_if_interrupt_requested(*, restore_handler: bool = True) -> None:
        if not interrupt_requested:
            return
        report_pending_interrupt_warning()
        request_parallel_stop()
        finalize_interrupted_run(restore_handler=restore_handler)
        raise UltimateLinefeedInterrupted(progress_path)

    def request_interrupt(signum, frame):
        nonlocal interrupt_requested
        if interrupt_requested:
            repeat_interrupt_warning(signum, frame)
            return
        interrupt_requested = True
        request_parallel_stop()
        try:
            signal.signal(signal.SIGINT, repeat_interrupt_warning)
        except (OSError, ValueError):
            pass

    try:
        previous_sigint_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, request_interrupt)
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
        emit_ultimate_progress(tested)

    frontier_start_depth = 1
    if progress_resume is not None:
        if progress_resume.phase == "frontier":
            frontier_start_depth = max(1, min(max(1, max_depth), progress_resume.depth))
        elif progress_resume.phase in ("exhaustive", "complete"):
            frontier_start_depth = max(1, max_depth) + 1

    for depth in range(frontier_start_depth, max(1, max_depth) + 1):
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
                        emit_ultimate_progress(tested)
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
                    next_state_id += 1
                    top_candidates = _remember_ultimate_top_candidate(top_candidates, candidate)
                    remember_visual_candidate(candidate, tested)
                    _preview_ultimate_candidate_if_valid(
                        candidate,
                        tested,
                        progress_total,
                        candidate_preview,
                    )
                    raise_if_interrupt_requested()
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

    def run_parallel_exhaustive(operation_pools: tuple[tuple[SuperMegaLinefeedOperation, ...], ...]) -> bool:
        nonlocal best, best_score, tested, pruned, next_state_id, budget_exhausted
        nonlocal top_candidates
        nonlocal reached_depth, current_phase, current_depth, current_pool_index
        nonlocal current_combination_rank, current_combination_indices
        nonlocal parallel_stop_event
        if ultimate_workers < 2:
            return False

        root_parent_score = root.score or super_mega_linefeed_score(root.after, 0)
        resumed_by_shard: dict[tuple[int, int, int, int], dict[str, Any]] = {}
        if progress_resume is not None:
            for item in progress_resume.shards:
                try:
                    key = (
                        int(item.get("pool_index", 0)),
                        int(item.get("depth", 0)),
                        int(item.get("start_rank", 0)),
                        int(item.get("end_rank", 0)),
                    )
                except (TypeError, ValueError):
                    continue
                resumed_by_shard[key] = dict(item)

        def shard_key(shard: dict[str, Any]) -> str:
            return "%s:%s:%s:%s" % (
                int(shard.get("pool_index", 0) or 0),
                int(shard.get("depth", 0) or 0),
                int(shard.get("start_rank", 0) or 0),
                int(shard.get("end_rank", 0) or 0),
            )

        def shard_specs() -> Iterable[dict[str, Any]]:
            for pool_index, operation_pool in enumerate(operation_pools):
                if progress_resume is not None and not resumed_by_shard:
                    if progress_resume.phase == "exhaustive" and pool_index < progress_resume.pool_index:
                        continue
                    if progress_resume.phase == "complete":
                        continue
                if not operation_pool:
                    continue
                for depth in range(1, max(1, max_depth) + 1):
                    if progress_resume is not None and not resumed_by_shard:
                        if (
                            progress_resume.phase == "exhaustive"
                            and pool_index == progress_resume.pool_index
                            and depth < progress_resume.depth
                        ):
                            continue
                    total_ranks = math.comb(len(operation_pool), depth)
                    rank = 0
                    if (
                        progress_resume is not None
                        and not resumed_by_shard
                        and progress_resume.phase == "exhaustive"
                        and pool_index == progress_resume.pool_index
                        and depth == progress_resume.depth
                    ):
                        rank = max(0, int(progress_resume.combination_rank or 0))
                    while rank < total_ranks:
                        end_rank = min(total_ranks, rank + ULTIMATE_LINEFEED_PARALLEL_SHARD_SIZE)
                        resume_key = (pool_index, depth, rank, end_rank)
                        previous = resumed_by_shard.get(resume_key)
                        next_rank = rank
                        if previous is not None:
                            status = str(previous.get("status", "pending"))
                            if status == "done":
                                rank = end_rank
                                continue
                            try:
                                next_rank = max(rank, int(previous.get("next_rank", rank)))
                            except (TypeError, ValueError):
                                next_rank = rank
                        if next_rank < end_rank:
                            yield {
                                "pool_index": pool_index,
                                "depth": depth,
                                "start_rank": rank,
                                "end_rank": end_rank,
                                "next_rank": next_rank,
                                "tested": int(previous.get("tested", 0)) if previous else 0,
                                "pruned": int(previous.get("pruned", 0)) if previous else 0,
                                "status": "pending",
                            }
                        rank = end_rank

        mp_context = _ultimate_parallel_mp_context()
        progress_queue = None
        stop_event = None
        try:
            progress_queue = (
                mp_context.Queue()
                if mp_context is not None
                else multiprocessing.Queue()
            )
        except (OSError, RuntimeError, ValueError):
            progress_queue = None
        try:
            stop_event = (
                mp_context.Event()
                if mp_context is not None
                else multiprocessing.Event()
            )
        except (OSError, RuntimeError, ValueError):
            stop_event = None
        parallel_stop_event = stop_event
        if interrupt_requested:
            request_parallel_stop()
        context = {
            "chunks": chunks,
            "root_stream": root_stream,
            "before": before,
            "operation_pools": operation_pools,
            "target_adler": target_adler,
            "progress_queue": progress_queue,
            "stop_event": stop_event,
            "root_parent_score": root_parent_score,
            "visual_min_coverage": visual_min_coverage,
            "visual_gallery_limit": visual_gallery_limit,
        }
        executor_kwargs: dict[str, Any] = {
            "max_workers": max(2, ultimate_workers),
            "initializer": _ultimate_parallel_worker_init,
            "initargs": (context,),
        }
        if mp_context is not None:
            executor_kwargs["mp_context"] = mp_context
        try:
            executor = ProcessPoolExecutor(**executor_kwargs)
        except (OSError, RuntimeError, ValueError):
            return False
        futures: dict[Any, dict[str, Any]] = {}
        specs = iter(shard_specs())
        reserved_ranks = 0
        exhausted_specs = False
        seen_returned_candidates: set[str] = set()
        inflight_progress: dict[str, tuple[int, int, int, int]] = {}
        parallel_progress_floor = ultimate_progress_attempted_floor(progress_resume)
        parallel_attempted_since_floor = 0

        def parallel_display_total() -> int:
            return max(
                tested,
                parallel_progress_floor
                + parallel_attempted_since_floor
                + sum(max(item[0], item[3]) for item in inflight_progress.values()),
            )

        def remaining_budget() -> int | None:
            if budget_limit is None:
                return None
            return max(0, int(budget_limit) - parallel_display_total() - reserved_ranks)

        def submit_more() -> None:
            nonlocal reserved_ranks, exhausted_specs, budget_exhausted
            while len(futures) < max(2, ultimate_workers) and not exhausted_specs:
                remaining = remaining_budget()
                if remaining is not None and remaining <= 0:
                    budget_exhausted = parallel_display_total() >= int(budget_limit or 0)
                    break
                try:
                    shard = next(specs)
                except StopIteration:
                    exhausted_specs = True
                    break
                shard = dict(shard)
                if remaining is not None:
                    shard["end_rank"] = min(
                        int(shard["end_rank"]),
                        int(shard["next_rank"]) + remaining,
                    )
                if int(shard["next_rank"]) >= int(shard["end_rank"]):
                    continue
                key = shard_key(shard)
                current_shards[key] = dict(shard, status="running")
                reserved_ranks += int(shard["end_rank"]) - int(shard["next_rank"])
                futures[executor.submit(_ultimate_parallel_worker_run, shard)] = shard

        def drain_worker_progress() -> bool:
            if progress_queue is None:
                return False
            changed = False
            while True:
                try:
                    message = progress_queue.get_nowait()
                except queue.Empty:
                    break
                except (EOFError, OSError, ValueError):
                    break
                if not isinstance(message, dict):
                    continue
                key = str(message.get("key", ""))
                if not key:
                    continue
                try:
                    next_rank = int(message.get("next_rank", 0) or 0)
                    live_tested = int(message.get("tested", 0) or 0)
                    live_pruned = int(message.get("pruned", 0) or 0)
                    live_attempted = int(message.get("attempted", live_tested) or 0)
                except (TypeError, ValueError):
                    continue
                inflight_progress[key] = (live_tested, live_pruned, next_rank, live_attempted)
                shard = current_shards.get(key)
                if shard is not None:
                    try:
                        shard["next_rank"] = max(
                            int(shard.get("next_rank", 0) or 0),
                            next_rank,
                        )
                    except (TypeError, ValueError):
                        shard["next_rank"] = next_rank
                    shard["tested_live"] = live_tested
                    shard["pruned_live"] = live_pruned
                    shard["attempted_live"] = live_attempted
                changed = True
            if not changed:
                return False
            if progress is not None:
                emit_ultimate_progress(parallel_display_total())
            return True

        try:
            if progress is not None and parallel_progress_floor > 0:
                emit_ultimate_progress(parallel_display_total(), force=True)
            submit_more()
            while futures and not terminal(best):
                raise_if_interrupt_requested(restore_handler=False)
                done, _pending = wait(
                    tuple(futures),
                    timeout=ULTIMATE_LINEFEED_PARALLEL_PROGRESS_POLL_SECONDS,
                    return_when=FIRST_COMPLETED,
                )
                raise_if_interrupt_requested(restore_handler=False)
                if not done:
                    drain_worker_progress()
                    raise_if_interrupt_requested(restore_handler=False)
                    continue
                drain_worker_progress()
                raise_if_interrupt_requested(restore_handler=False)
                for future in done:
                    shard = futures.pop(future)
                    inflight_progress.pop(shard_key(shard), None)
                    try:
                        submitted_next_rank = int(
                            shard.get("next_rank", shard.get("start_rank", 0)) or 0
                        )
                    except (TypeError, ValueError):
                        submitted_next_rank = 0
                    reserved_ranks = max(
                        0,
                        reserved_ranks - (int(shard["end_rank"]) - int(shard["next_rank"])),
                    )
                    try:
                        result = future.result()
                    except BaseException as exc:
                        result = UltimateParallelShardResult(
                            shard=shard,
                            tested=0,
                            pruned=0,
                            state_count=0,
                            next_rank=int(shard.get("next_rank", shard.get("start_rank", 0)) or 0),
                            candidates=(),
                            error="%s: %s" % (type(exc).__name__, exc),
                        )
                    result_shard = dict(result.shard)
                    result_shard["next_rank"] = int(result.next_rank)
                    parallel_attempted_since_floor += max(
                        0,
                        int(result.next_rank) - submitted_next_rank,
                    )
                    result_shard["tested"] = int(result_shard.get("tested", 0) or 0) + int(result.tested)
                    result_shard["pruned"] = int(result_shard.get("pruned", 0) or 0) + int(result.pruned)
                    result_shard["status"] = (
                        "error"
                        if result.error
                        else (
                            "done"
                            if int(result.next_rank) >= int(result_shard.get("end_rank", 0) or 0)
                            else "pending"
                        )
                    )
                    if result.error:
                        result_shard["error"] = result.error
                    current_shards[shard_key(result_shard)] = result_shard
                    current_phase = "exhaustive"
                    current_depth = int(result_shard.get("depth", current_depth) or current_depth)
                    current_pool_index = int(result_shard.get("pool_index", current_pool_index) or current_pool_index)
                    current_combination_rank = int(result.next_rank)
                    current_combination_indices = _combination_indices_at_rank(
                        len(operation_pools[current_pool_index]),
                        current_depth,
                        current_combination_rank,
                    )
                    reached_depth = max(reached_depth, current_depth)
                    tested += int(result.tested)
                    pruned += int(result.pruned)
                    base_state_id = next_state_id
                    next_state_id += max(int(result.state_count), len(result.candidates))
                    for index, candidate in enumerate(result.candidates):
                        candidate_key = hashlib.blake2b(candidate.data, digest_size=16).hexdigest()
                        if candidate_key in seen_returned_candidates:
                            continue
                        seen_returned_candidates.add(candidate_key)
                        candidate = replace(candidate, state_id=base_state_id + index, parent_id=0)
                        top_candidates = _remember_ultimate_top_candidate(top_candidates, candidate)
                        remember_visual_candidate(candidate, tested)
                        _preview_ultimate_candidate_if_valid(
                            candidate,
                            tested,
                            progress_total,
                            candidate_preview,
                        )
                        raise_if_interrupt_requested(restore_handler=False)
                        candidate_score = candidate.score or super_mega_linefeed_score(
                            candidate.after,
                            len(candidate.operations),
                        )
                        if candidate_score > best_score:
                            best = candidate
                            best_score = candidate_score
                            _append_ultimate_checkpoint(
                                checkpoint_path,
                                source_hash=source_hash,
                                candidate=candidate,
                                depth=current_depth,
                            )
                        if terminal(candidate):
                            best = candidate
                            best_score = candidate_score
                            _append_ultimate_checkpoint(
                                checkpoint_path,
                                source_hash=source_hash,
                                candidate=candidate,
                                depth=current_depth,
                            )
                            break
                    if progress is not None and progress_snapshot_due():
                        emit_ultimate_progress(parallel_display_total())
                    save_progress_snapshot()
                    if budget_limit is not None and parallel_display_total() >= int(budget_limit):
                        budget_exhausted = True
                    if terminal(best) or budget_exhausted:
                        break
                if terminal(best) or budget_exhausted:
                    break
                submit_more()
        except UltimateLinefeedInterrupted:
            _ultimate_shutdown_parallel_executor(
                executor,
                futures=futures,
                progress_queue=progress_queue,
                stop_event=stop_event,
            )
            raise
        except KeyboardInterrupt:
            request_parallel_stop()
            _ultimate_shutdown_parallel_executor(
                executor,
                futures=futures,
                progress_queue=progress_queue,
                stop_event=stop_event,
            )
            finalize_interrupted_run(restore_handler=False)
            raise UltimateLinefeedInterrupted(progress_path)
        finally:
            _ultimate_shutdown_parallel_executor(
                executor,
                futures=futures,
                progress_queue=progress_queue,
                stop_event=stop_event,
            )
            parallel_stop_event = None
            restore_sigint_handler()
        return True

    if not terminal(best) and not budget_exhausted and (budget_limit is None or tested < budget_limit):
        root_parent_score = root.score or super_mega_linefeed_score(root.after, 0)
        if fast_resume_complete:
            pass
        elif not (ultimate_workers >= 2 and run_parallel_exhaustive(operation_pools)):
            for pool_index, operation_pool in enumerate(operation_pools):
                if (
                    progress_resume is not None
                    and progress_resume.phase == "exhaustive"
                    and pool_index < progress_resume.pool_index
                ):
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
                            emit_ultimate_progress(tested)
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
                        next_state_id += 1
                        top_candidates = _remember_ultimate_top_candidate(top_candidates, candidate)
                        remember_visual_candidate(candidate, tested)
                        _preview_ultimate_candidate_if_valid(
                            candidate,
                            tested,
                            progress_total,
                            candidate_preview,
                        )
                        raise_if_interrupt_requested()

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
        emit_ultimate_progress(tested)
    save_progress_snapshot(phase="complete", depth=reached_depth, force_visual=True)
    restore_sigint_handler()

    reason = ""
    if fast_resume_complete:
        reason = "previous Ultimate run already marked this search complete"
    elif best is None:
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
        reference_mode=reference_mode,
        reference_regions_path=reference_regions_path,
        reference_warning=reference_warning,
        progress_path=progress_path,
        progress_resumed=progress_resume is not None,
        progress_warning=progress_warning,
        visual_candidates=visual_candidates,
        visual_gallery_path=visual_gallery_path,
        visual_preview_count=visual_preview_count,
        visual_gallery_limit=visual_gallery_limit,
        fast_resume_used=resume_fast_used,
        fast_resume_rejected_reason=resume_rejected_reason,
        attempted_floor=resume_attempted_floor if resume_fast_used else 0,
        committed_count=resume_committed_count,
        matched_shards=resume_matched_shards,
        pending_shards=resume_pending_shards,
        current_workers=ultimate_workers,
        saved_workers=resume_saved_workers,
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
    if result.reference_path:
        line += "; reference_mode=%s" % result.reference_mode
    if result.reference_regions_path:
        line += "; reference_regions=%s" % result.reference_regions_path
    if result.best is not None:
        line += "; best_score=%s" % (
            result.best.score or super_mega_linefeed_score(result.best.after, len(result.best.operations)),
        )
    if result.top_candidates:
        line += "; top_candidates=%s" % len(result.top_candidates)
    if result.visual_gallery_limit > 0:
        line += "; visual_candidates=%s/%s" % (
            len(result.visual_candidates),
            result.visual_gallery_limit,
        )
        if result.visual_preview_count:
            line += "; visual_previews=%s" % result.visual_preview_count
        if result.visual_gallery_path:
            line += "; visual_gallery=%s" % result.visual_gallery_path
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
        visual_note = "; visual_score=%.4f" % candidate.visual_score
        if candidate.visual_score_kind:
            visual_note += " kind=%s" % candidate.visual_score_kind
        if candidate.matched_patch_count:
            visual_note += " matched_patches=%s" % candidate.matched_patch_count
        line = line[:-1] + visual_note + "."
    return line


def ultimate_visual_candidate_summary_line(candidate: UltimateVisualCandidate) -> str:
    after = candidate.candidate.after
    line = (
        "-%s best visual candidate: %s/%s %s rebuilt_adler_preview; "
        "adler=%s; state=%s; tested=%s; hash=%s"
        % (
            "UltimateMegaSuperLineFeedBruteForce",
            after.usable_scanlines,
            after.height,
            after.status,
            after.adler_status,
            candidate.candidate.state_id,
            candidate.tested_candidates,
            candidate.visual_hash,
        )
    )
    if candidate.candidate.visual_score is not None:
        line += "; visual_score=%.4f" % candidate.candidate.visual_score
        if candidate.candidate.visual_score_kind:
            line += "; visual_score_kind=%s" % candidate.candidate.visual_score_kind
        if candidate.candidate.matched_patch_count:
            line += "; matched_patches=%s" % candidate.candidate.matched_patch_count
    if candidate.preview_path:
        line += "; preview=%s" % candidate.preview_path
    return line + "."


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
