from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import dataclass, field, replace
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
import uuid
import zlib
from typing import Any, Callable, Iterable

from . import deflate_header
from . import deflate_probe
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
        uuid.uuid4().hex,
    )
    return os.path.join(directory, tmp_name) if directory else tmp_name


def _bounded_route_stop_reason(
    *,
    tested: int,
    budget: int,
    budget_exhausted: bool,
    candidate_pool_exhausted: bool = False,
    frontier_exhausted: bool = False,
    depth_limit_reached: bool = False,
) -> str:
    if budget_exhausted or int(tested) >= int(budget):
        return "budget_exhausted"
    if candidate_pool_exhausted:
        return "candidate_pool_exhausted"
    if frontier_exhausted:
        return "frontier_exhausted"
    if depth_limit_reached:
        return "depth_limit_reached"
    return "completed"


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
    edit_kind: str = "replace"
    old_bytes: bytes = b""
    new_bytes: bytes = b""
    bit_offsets: tuple[int, ...] = ()


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
    diagnostic_best: IdatDeflateCandidate | None = None
    subprobes: tuple["IdatDeflateProbeResult", ...] = ()

    @property
    def improved(self) -> bool:
        return self.best is not None


@dataclass(frozen=True)
class IdatLocalDeflateDiagnostic:
    before: idat.IdatStreamAnalysis
    trace: deflate_header.DynamicHeaderTrace
    stream_size: int
    stream_offset: int
    file_offset: int | None
    idat_index: int | None
    idat_offset: int | None
    window_start: int
    window_end: int
    context_hex: str
    suspect_bits: tuple[int, ...] = ()
    suspect_byte_offsets: tuple[int, ...] = ()


@dataclass(frozen=True)
class IdatRawPrefix:
    raw: bytes
    error_offset: int | None = None
    zlib_error: str = ""
    complete: bool = False


@dataclass(frozen=True)
class PngRawPrefixScore:
    raw_size: int
    first_filter: int | None
    first_filter_ok: bool
    checked_filter_rows: int
    valid_filter_rows: int
    alpha_checked: int = 0
    alpha_plausible: int = 0

    @property
    def first_filter_rank(self) -> int:
        return 1 if self.first_filter_ok else 0

    @property
    def alpha_rank(self) -> int:
        if self.alpha_checked <= 0:
            return 0
        return int((self.alpha_plausible * 1000) / self.alpha_checked)

    @property
    def rank(self) -> tuple[int, int, int, int]:
        return (
            self.first_filter_rank,
            int(self.valid_filter_rows),
            int(self.alpha_rank),
            int(self.raw_size),
        )


@dataclass(frozen=True)
class RawPngOracleDecision:
    raw_prefix: IdatRawPrefix
    raw_score: PngRawPrefixScore
    rejected: bool
    reject_reason: str = ""

    @property
    def first_filter(self) -> int | None:
        return self.raw_score.first_filter

    @property
    def first_filter_ok(self) -> bool:
        return self.raw_score.first_filter_ok

    @property
    def valid_filter_rows(self) -> int:
        return self.raw_score.valid_filter_rows

    @property
    def raw_len(self) -> int:
        return self.raw_score.raw_size

    @property
    def zlib_error(self) -> str:
        return self.raw_prefix.zlib_error

    @property
    def png_plausible(self) -> bool:
        return bool(self.raw_score.first_filter_ok and not self.rejected)

    @property
    def rank(self) -> tuple[int, int, int, int, int]:
        return (
            0 if self.rejected else 1,
            self.raw_score.first_filter_rank,
            int(self.raw_score.valid_filter_rows),
            int(self.raw_score.alpha_rank),
            int(self.raw_score.raw_size),
        )


@dataclass(frozen=True)
class IdatDeepBeamOperation:
    kind: str
    stream_offset: int
    old_bytes: bytes = b""
    new_bytes: bytes = b""
    bit_offsets: tuple[int, ...] = ()


@dataclass(frozen=True)
class IdatDeepBeamCandidate:
    data: bytes
    stream: bytes
    operations: tuple[IdatDeepBeamOperation, ...]
    before: idat.IdatStreamAnalysis
    after: idat.IdatStreamAnalysis
    state_id: int = 0
    parent_id: int | None = None
    source_offsets: tuple[int, ...] = ()
    score: tuple[int, ...] = ()


@dataclass
class IdatDeepBeamRuntimeStats:
    gpu_setup_ms: float = 0.0
    gpu_dispatch_ms: float = 0.0
    gpu_hits: int = 0
    gpu_shards: int = 0
    gpu_skipped_resume: int = 0
    cpu_batches: int = 0
    cpu_validate_ms: float = 0.0
    wall_ms: float = 0.0


@dataclass(frozen=True)
class IdatDeepBeamProgressResume:
    gpu_done_shards: set[str]
    resumed: bool = False
    tested_candidates: int = 0
    depth: int = 0
    state_count: int = 0
    visited_count: int = 0


@dataclass(frozen=True)
class IdatDeepBeamResumeState:
    available: bool
    source_matches: bool
    interrupted: bool = False
    tested: int = 0
    depth: int = 0
    reason: str = ""


@dataclass(frozen=True)
class IdatDeepBeamProbeResult:
    before: idat.IdatStreamAnalysis
    best: IdatDeepBeamCandidate | None
    top_candidates: tuple[IdatDeepBeamCandidate, ...]
    window_start: int
    window_end: int
    tested_candidates: int
    budget_exhausted: bool
    reached_depth: int
    state_count: int
    visited_count: int
    checkpoint_path: str = ""
    progress_path: str = ""
    progress_resumed: bool = False
    workers: int = 1
    gpu_requested: bool = False
    gpu_backend: str = "none"
    strategy: str = "deep-beam"
    reason: str = ""
    gpu_warning: str = ""
    gpu_shards_done: int = 0
    interrupted: bool = False
    timing: IdatDeepBeamRuntimeStats = field(default_factory=IdatDeepBeamRuntimeStats)

    @property
    def improved(self) -> bool:
        return self.best is not None


@dataclass(frozen=True)
class IdatPeriodicProgressState:
    available: bool
    source_matches: bool
    exhausted: bool = False
    tested: int = 0
    budget: int = 0
    reason: str = ""


@dataclass(frozen=True)
class IdatPeriodicCorruptionModelResult:
    before: idat.IdatStreamAnalysis
    best: IdatDeepBeamCandidate | None
    top_candidates: tuple[IdatDeepBeamCandidate, ...]
    tested_candidates: int
    budget_exhausted: bool
    checkpoint_path: str = ""
    progress_path: str = ""
    model_path: str = ""
    strategy: str = "periodic-corruption-model"
    reason: str = ""
    source_hash: str = ""

    @property
    def improved(self) -> bool:
        return self.best is not None


@dataclass(frozen=True)
class IdatFrontierProgressState:
    available: bool
    source_matches: bool
    exhausted: bool = False
    tested: int = 0
    budget: int = 0
    reason: str = ""


@dataclass(frozen=True)
class IdatHuffmanOracleSolverResult:
    before: idat.IdatStreamAnalysis
    best: IdatDeepBeamCandidate | None
    top_candidates: tuple[IdatDeepBeamCandidate, ...]
    tested_candidates: int
    budget_exhausted: bool
    checkpoint_path: str = ""
    progress_path: str = ""
    valid_headers: int = 0
    png_plausible: int = 0
    reached_depth: int = 0
    seed_count: int = 0
    strategy: str = "dynamic-huffman-png-oracle"
    reason: str = ""
    source_hash: str = ""

    @property
    def improved(self) -> bool:
        return self.best is not None


@dataclass(frozen=True)
class IdatCrcPeriodicPayloadSolverResult:
    before: idat.IdatStreamAnalysis
    best: IdatDeepBeamCandidate | None
    top_candidates: tuple[IdatDeepBeamCandidate, ...]
    tested_candidates: int
    budget_exhausted: bool
    checkpoint_path: str = ""
    progress_path: str = ""
    model_path: str = ""
    crc_hits: int = 0
    png_plausible: int = 0
    strategy: str = "crc-periodic-payload"
    reason: str = ""
    source_hash: str = ""

    @property
    def improved(self) -> bool:
        return self.best is not None


@dataclass(frozen=True)
class IdatHuffmanKraftSolverResult:
    before: idat.IdatStreamAnalysis
    best: IdatDeepBeamCandidate | None
    top_candidates: tuple[IdatDeepBeamCandidate, ...]
    tested_candidates: int
    budget_exhausted: bool
    checkpoint_path: str = ""
    progress_path: str = ""
    valid_headers: int = 0
    complete_trees: int = 0
    first_symbol_ok: int = 0
    best_literal_debt: int = 0
    best_distance_debt: int = 0
    reached_depth: int = 0
    workers: int = 1
    gpu_status: str = "off"
    gpu_hits: int = 0
    gpu_shards: int = 0
    cpu_batches: int = 0
    kraft_prefilter_hits: int = 0
    memory_mode: str = "normal"
    memory_available_bytes: int | None = None
    memory_throttle_events: int = 0
    strategy: str = "huffman-kraft"
    reason: str = ""
    source_hash: str = ""

    @property
    def improved(self) -> bool:
        return self.best is not None


@dataclass(frozen=True)
class IdatFirstFilterLiteralResult:
    before: idat.IdatStreamAnalysis
    best: IdatDeepBeamCandidate | None
    top_candidates: tuple[IdatDeepBeamCandidate, ...]
    tested_candidates: int
    budget_exhausted: bool
    checkpoint_path: str = ""
    progress_path: str = ""
    seed_count: int = 0
    closure_hits: int = 0
    first_filter_hits: int = 0
    png_plausible: int = 0
    strategy: str = "first-filter-literal"
    reason: str = ""
    source_hash: str = ""

    @property
    def improved(self) -> bool:
        return self.best is not None


@dataclass(frozen=True)
class IdatKraftBackrefRepairResult:
    before: idat.IdatStreamAnalysis
    best: IdatDeepBeamCandidate | None
    top_candidates: tuple[IdatDeepBeamCandidate, ...]
    tested_candidates: int
    budget_exhausted: bool
    checkpoint_path: str = ""
    progress_path: str = ""
    seed_checkpoint_path: str = ""
    repaired_backrefs: int = 0
    png_prefix_hits: int = 0
    best_prefix_rows: int = 0
    reached_depth: int = 0
    strategy: str = "kraft-backref-repair"
    reason: str = ""
    source_hash: str = ""

    @property
    def improved(self) -> bool:
        return self.best is not None


@dataclass(frozen=True)
class IdatGlobalCrcResidueSolverResult:
    before: idat.IdatStreamAnalysis
    best: IdatDeepBeamCandidate | None
    top_candidates: tuple[IdatDeepBeamCandidate, ...]
    tested_candidates: int
    budget_exhausted: bool
    checkpoint_path: str = ""
    progress_path: str = ""
    model_path: str = ""
    rules: int = 0
    explained_chunks: int = 0
    crc_hits: int = 0
    png_plausible: int = 0
    strategy: str = "global-crc-residue"
    reason: str = ""
    source_hash: str = ""

    @property
    def improved(self) -> bool:
        return self.best is not None


@dataclass(frozen=True)
class IdatAffineCorruptionModelResult:
    before: idat.IdatStreamAnalysis
    best: IdatDeepBeamCandidate | None
    top_candidates: tuple[IdatDeepBeamCandidate, ...]
    tested_candidates: int
    budget_exhausted: bool
    checkpoint_path: str = ""
    progress_path: str = ""
    model_path: str = ""
    rules: int = 0
    projected_hits: int = 0
    png_plausible: int = 0
    workers: int = 1
    gpu_status: str = "off"
    gpu_hits: int = 0
    gpu_shards: int = 0
    cpu_batches: int = 0
    strategy: str = "affine-corruption-model"
    reason: str = ""
    source_hash: str = ""

    @property
    def improved(self) -> bool:
        return self.best is not None


@dataclass(frozen=True)
class DeflateResyncSalvageResult:
    before: idat.IdatStreamAnalysis
    anchors: tuple[int, ...]
    partial_rows: int = 0
    known_pixels: int = 0
    preview_path: str = ""
    tested_candidates: int = 0
    budget_exhausted: bool = False
    progress_path: str = ""
    strategy: str = "deflate-resync-salvage"
    reason: str = ""
    source_hash: str = ""


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


def _normalize_ultimate_progress_shard(shard: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(shard)
    try:
        start_rank = int(normalized.get("start_rank", 0) or 0)
    except (TypeError, ValueError):
        start_rank = 0
    try:
        end_rank = int(normalized.get("end_rank", start_rank) or start_rank)
    except (TypeError, ValueError):
        end_rank = start_rank
    end_rank = max(start_rank, end_rank)
    try:
        next_rank = int(normalized.get("next_rank", start_rank) or start_rank)
    except (TypeError, ValueError):
        next_rank = start_rank
    if str(normalized.get("status", "")) == "done":
        next_rank = end_rank
    next_rank = min(max(start_rank, next_rank), end_rank)
    confirmed = max(0, next_rank - start_rank)
    normalized["start_rank"] = start_rank
    normalized["end_rank"] = end_rank
    normalized["next_rank"] = next_rank
    try:
        normalized["tested"] = max(int(normalized.get("tested", 0) or 0), confirmed)
    except (TypeError, ValueError):
        normalized["tested"] = confirmed
    return normalized


def _ultimate_progress_shards_attempted(shards: Iterable[dict[str, Any]]) -> int:
    return sum(
        _ultimate_progress_shard_attempted(_normalize_ultimate_progress_shard(shard))
        for shard in shards
        if isinstance(shard, dict)
    )


def ultimate_progress_attempted_floor(progress: UltimateLinefeedProgress | None) -> int:
    if progress is None:
        return 0
    shard_records = tuple(
        shard for shard in getattr(progress, "shards", ()) if isinstance(shard, dict)
    )
    shard_attempted = _ultimate_progress_shards_attempted(shard_records)
    combination_rank = (
        max(0, int(getattr(progress, "combination_rank", 0) or 0))
        if getattr(progress, "phase", "") == "exhaustive"
        else 0
    )
    if shard_records:
        return max(
            0,
            int(getattr(progress, "tested_candidates", 0) or 0),
            shard_attempted,
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
        try:
            item_shard_size = int(item.get("shard_size", shard_size) or shard_size or 1)
        except (TypeError, ValueError):
            item_shard_size = int(shard_size or 1)
        expected_end = min(total_ranks, start_rank + max(1, item_shard_size))
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


def _idat_chunk_index(idat_chunks: tuple[png.PngChunk, ...], target_chunk: png.PngChunk) -> int:
    for index, chunk in enumerate(idat_chunks, start=1):
        if chunk.offset == target_chunk.offset:
            return index
    return 0


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


def _probe_linefeed_insertions_in_offsets(
    data: bytes,
    *,
    strategy: str,
    offsets: list[int],
    inserted_byte: int,
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

        insertion = bytes((int(inserted_byte) & 0xFF,))
        candidate_stream = idat_stream[:stream_offset] + insertion + idat_stream[stream_offset:]
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
            inserted_byte=int(inserted_byte) & 0xFF,
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
    return _probe_linefeed_insertions_in_offsets(
        data,
        strategy=strategy,
        offsets=offsets,
        inserted_byte=0x0D,
        window_start=window_start,
        window_end=window_end,
        budget=budget,
        progress=progress,
    )


def mutate_idat_stream_byte(
    data: bytes,
    stream_offset: int,
    new_byte: int,
    *,
    before_analysis: idat.IdatStreamAnalysis | None = None,
) -> IdatDeflateCandidate | None:
    before = before_analysis or idat.analyze_idat_stream(data)
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
        edit_kind="replace",
        old_bytes=bytes((old_byte,)),
        new_bytes=bytes((new_byte,)),
    )


def mutate_idat_stream_bit_flips(
    data: bytes,
    bit_offsets: Iterable[int],
    *,
    before_analysis: idat.IdatStreamAnalysis | None = None,
) -> IdatDeflateCandidate | None:
    bits = tuple(sorted(dict.fromkeys(int(bit) for bit in bit_offsets)))
    if not bits:
        return None

    before = before_analysis or idat.analyze_idat_stream(data)
    try:
        idat_chunks, idat_stream = _idat_chunks_and_stream(data)
    except png.PngFormatError:
        return None

    if not idat_stream:
        return None
    if bits[0] < 0 or bits[-1] >= len(idat_stream) * 8:
        return None

    candidate = bytearray(data)
    locations: dict[int, tuple[png.PngChunk, int, int, int]] = {}
    touched_chunks: dict[int, png.PngChunk] = {}
    for bit_offset in bits:
        stream_offset = bit_offset // 8
        bit_index = bit_offset % 8
        location = locations.get(stream_offset)
        if location is None:
            located = _locate_idat_stream_offset(idat_chunks, stream_offset)
            if located is None:
                return None
            chunk, idat_index, idat_offset = located
            file_offset = chunk.offset + 8 + idat_offset
            location = (chunk, idat_index, idat_offset, file_offset)
            locations[stream_offset] = location
        chunk, _idat_index, _idat_offset, file_offset = location
        candidate[file_offset] ^= 1 << bit_index
        touched_chunks[chunk.offset] = chunk

    if not touched_chunks:
        return None

    for chunk in touched_chunks.values():
        payload_start = chunk.offset + 8
        payload_end = payload_start + chunk.length
        crc_offset = payload_end
        repaired_crc = zlib.crc32(chunk.chunk_type + bytes(candidate[payload_start:payload_end])) & 0xFFFFFFFF
        candidate[crc_offset : crc_offset + 4] = repaired_crc.to_bytes(4, "big")

    byte_offsets = tuple(sorted(locations))
    first_stream_offset = byte_offsets[0]
    first_chunk, first_idat_index, first_idat_offset, first_file_offset = locations[first_stream_offset]
    old_bytes = bytes(idat_stream[offset] for offset in byte_offsets)
    new_bytes = bytes(candidate[locations[offset][3]] for offset in byte_offsets)
    if old_bytes == new_bytes:
        return None

    candidate_data = bytes(candidate)
    return IdatDeflateCandidate(
        data=candidate_data,
        stream_offset=first_stream_offset,
        file_offset=first_file_offset,
        idat_index=first_idat_index,
        idat_offset=first_idat_offset,
        old_byte=idat_stream[first_stream_offset],
        new_byte=candidate[first_file_offset],
        before=before,
        after=idat.analyze_idat_stream(candidate_data),
        edit_kind="bit-flip-set",
        old_bytes=old_bytes,
        new_bytes=new_bytes,
        bit_offsets=bits,
    )


def mutate_idat_stream_edit(
    data: bytes,
    stream_offset: int,
    edit_kind: str,
    *,
    new_bytes: bytes = b"",
    remove_count: int = 0,
    before_analysis: idat.IdatStreamAnalysis | None = None,
) -> IdatDeflateCandidate | None:
    before = before_analysis or idat.analyze_idat_stream(data)
    if stream_offset < 0:
        return None

    edit = str(edit_kind).strip().lower()
    try:
        idat_chunks, idat_stream = _idat_chunks_and_stream(data)
    except png.PngFormatError:
        return None

    if edit == "insert":
        if stream_offset > len(idat_stream):
            return None
        if stream_offset == len(idat_stream) and idat_chunks:
            chunk = idat_chunks[-1]
            location = (chunk, len(idat_chunks), chunk.length)
        else:
            locate_offset = min(stream_offset, max(0, len(idat_stream) - 1))
            location = _locate_idat_stream_offset(idat_chunks, locate_offset)
    else:
        if stream_offset >= len(idat_stream):
            return None
        location = _locate_idat_stream_offset(idat_chunks, stream_offset)
    if location is None:
        return None

    chunk, idat_index, idat_offset = location
    payload_start = chunk.offset + 8
    payload_end = payload_start + chunk.length
    chunk_payload = data[payload_start:payload_end]
    old_byte = chunk_payload[idat_offset] if idat_offset < len(chunk_payload) else 0
    new_byte = new_bytes[0] if new_bytes else old_byte

    if edit == "replace":
        if not new_bytes:
            return None
        old_bytes = chunk_payload[idat_offset : idat_offset + len(new_bytes)]
        if len(old_bytes) != len(new_bytes) or old_bytes == new_bytes:
            return None
        repaired_payload = chunk_payload[:idat_offset] + new_bytes + chunk_payload[idat_offset + len(new_bytes) :]
    elif edit == "insert":
        if not new_bytes:
            return None
        old_bytes = b""
        repaired_payload = chunk_payload[:idat_offset] + new_bytes + chunk_payload[idat_offset:]
    elif edit == "remove":
        count = max(1, int(remove_count))
        old_bytes = chunk_payload[idat_offset : idat_offset + count]
        if len(old_bytes) != count:
            return None
        repaired_payload = chunk_payload[:idat_offset] + chunk_payload[idat_offset + count :]
        new_bytes = b""
    else:
        return None

    repaired_chunk = png.build_png_chunk(chunk.chunk_type, repaired_payload)
    candidate_data = data[: chunk.offset] + repaired_chunk + data[payload_end + 4 :]
    return IdatDeflateCandidate(
        data=candidate_data,
        stream_offset=stream_offset,
        file_offset=payload_start + idat_offset,
        idat_index=idat_index,
        idat_offset=idat_offset,
        old_byte=old_byte,
        new_byte=new_byte,
        before=before,
        after=idat.analyze_idat_stream(candidate_data),
        edit_kind=edit,
        old_bytes=old_bytes,
        new_bytes=new_bytes,
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


def probe_idat_linefeed_lf_insertions(
    data: bytes,
    *,
    window_radius: int = 512,
    budget: int = 1024,
    progress: QueueProgressCallback | None = None,
) -> IdatLinefeedInsertProbeResult:
    strategy = "linefeed-lf-insert"
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
    window_end = min(len(idat_stream) + 1, center + window_radius + 1)
    offsets = list(range(window_start, window_end))
    offsets.sort(key=lambda offset: (abs(offset - center), offset))

    return _probe_linefeed_insertions_in_offsets(
        data,
        strategy=strategy,
        offsets=offsets,
        inserted_byte=0x0A,
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


def _linefeed_lf_insert_mutations(
    stream: bytes,
    *,
    center: int,
    search_start: int,
    backtrack: int,
    forward: int,
) -> Iterable[tuple[bytes, SuperMegaLinefeedOperation]]:
    insert_start = max(search_start, center - backtrack)
    insert_end = min(len(stream) + 1, center + forward + 1)

    for offset in _offsets_by_distance(insert_start, insert_end, center):
        yield (
            stream[:offset] + b"\n" + stream[offset:],
            SuperMegaLinefeedOperation("insert-lf-near-error", offset, b"", b"\n"),
        )


def _count_linefeed_lf_insert_mutations(
    stream: bytes,
    *,
    center: int,
    search_start: int,
    backtrack: int,
    forward: int,
) -> int:
    insert_start = max(search_start, center - backtrack)
    insert_end = min(len(stream) + 1, center + forward + 1)
    return max(0, insert_end - insert_start)


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
        normalized_shards = tuple(
            _normalize_ultimate_progress_shard(shard)
            for shard in shards
            if isinstance(shard, dict)
        )
        confirmed_attempted = _ultimate_progress_shards_attempted(normalized_shards)
        safe_attempted = max(
            int(tested_candidates or 0),
            confirmed_attempted if normalized_shards else int(attempted_candidates or 0),
        )
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
                    "attempted_candidates": safe_attempted,
                    "pruned_candidates": pruned_candidates,
                    "state_count": state_count,
                    "budget": budget,
                    "timestamp": time.time(),
            }
            if int(parallel_workers or 0) > 1 or shards:
                record["parallel_workers"] = max(0, int(parallel_workers or 0))
                record["shard_size"] = max(0, int(shard_size or 0))
                record["shards"] = list(normalized_shards)
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
    yield (
        stream[:offset] + b"\n" + stream[offset:],
        SuperMegaLinefeedOperation("ultimate-insert-lf", offset, b"", b"\n"),
    )
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


def _merge_ultimate_offsets(
    *offset_groups: tuple[int, ...],
    max_offsets: int | None = None,
) -> tuple[int, ...]:
    merged: list[int] = []
    seen: set[int] = set()
    for offsets in offset_groups:
        for offset in offsets:
            try:
                safe_offset = int(offset)
            except (TypeError, ValueError):
                continue
            if safe_offset < 0 or safe_offset in seen:
                continue
            seen.add(safe_offset)
            merged.append(safe_offset)
            if max_offsets is not None and len(merged) >= int(max_offsets):
                return tuple(merged)
    return tuple(merged)


def estimate_ultimate_linefeed_search(
    data: bytes,
    *,
    start_offset: int | None = None,
    target_adler: int | None = None,
    super_result: SuperMegaLinefeedProbeResult | None = None,
    max_depth: int = 4,
    max_offsets: int = 128,
    gpu_suspect_offsets: tuple[int, ...] = (),
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
    suspect_offsets = _merge_ultimate_offsets(
        tuple(gpu_suspect_offsets or ()),
        suspect_offsets,
        max_offsets=max(max_offsets, len(tuple(gpu_suspect_offsets or ())) + max_offsets),
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


def _ultimate_gpu_analysis_candidates(
    *,
    chunks: tuple[png.PngChunk, ...],
    root_stream: bytes,
    before: idat.IdatStreamAnalysis,
    operation_pools: tuple[tuple[SuperMegaLinefeedOperation, ...], ...],
    target_adler: int | None,
    gpu_config: Any,
    max_depth: int,
    progress_resume: UltimateLinefeedProgress | None = None,
    candidate_limit: int = ULTIMATE_LINEFEED_TOP_CANDIDATES,
    budget_limit: int | None = None,
    shard_callback: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[tuple[SuperMegaLinefeedCandidate, ...], str]:
    if not bool(getattr(gpu_config, "enabled", False)):
        return (), ""
    try:
        from . import ultimate_opengl_backend
    except Exception as exc:
        return (), "Ultimate OpenGL analysis unavailable: %s" % exc

    nominations: tuple[SuperMegaLinefeedCandidate, ...] = ()
    warning = ""
    parent_score = super_mega_linefeed_score(before, 0)
    max_depth = max(1, int(max_depth or 1))
    max_hits = max(1, int(candidate_limit or 1))
    shard_size = max(1, int(ultimate_opengl_backend.ULTIMATE_OPENGL_ANALYSIS_SHARD_SIZE))
    remaining_rank_budget = None if budget_limit is None else max(0, int(budget_limit))
    saved_by_key: dict[tuple[int, int, int, int], dict[str, Any]] = {}
    if progress_resume is not None:
        for item in progress_resume.shards:
            if not isinstance(item, dict) or str(item.get("backend", "")) != "opengl":
                continue
            try:
                key = (
                    int(item.get("pool_index", 0) or 0),
                    int(item.get("depth", 0) or 0),
                    int(item.get("start_rank", 0) or 0),
                    int(item.get("end_rank", 0) or 0),
                )
            except (TypeError, ValueError):
                continue
            saved_by_key[key] = dict(item)

    def publish_shard(shard: dict[str, Any]) -> None:
        if shard_callback is None:
            return
        shard_callback(dict(shard))

    def shard_specs() -> Iterable[dict[str, Any]]:
        ordered: list[tuple[int, int]] = []
        if max_depth >= 1:
            ordered.extend((pool_index, 1) for pool_index in range(len(operation_pools)))
        for depth in range(2, max_depth + 1):
            ordered.extend((pool_index, depth) for pool_index in range(len(operation_pools)))

        for pool_index, depth in ordered:
            operation_pool = operation_pools[pool_index]
            if not operation_pool or depth > len(operation_pool):
                continue
            total_ranks = math.comb(len(operation_pool), depth)
            rank = 0
            while rank < total_ranks:
                end_rank = min(total_ranks, rank + shard_size)
                key = (pool_index, depth, rank, end_rank)
                previous = saved_by_key.get(key)
                if previous is not None and str(previous.get("status", "")) == "done":
                    rank = end_rank
                    continue
                next_rank = rank
                tested = 0
                pruned = 0
                if previous is not None:
                    try:
                        next_rank = max(rank, min(end_rank, int(previous.get("next_rank", rank) or rank)))
                    except (TypeError, ValueError):
                        next_rank = rank
                    try:
                        tested = int(previous.get("tested", 0) or 0)
                    except (TypeError, ValueError):
                        tested = 0
                    try:
                        pruned = int(previous.get("pruned", 0) or 0)
                    except (TypeError, ValueError):
                        pruned = 0
                if next_rank < end_rank:
                    yield {
                        "backend": "opengl",
                        "pool_index": pool_index,
                        "depth": depth,
                        "start_rank": rank,
                        "end_rank": end_rank,
                        "next_rank": next_rank,
                        "tested": tested,
                        "pruned": pruned,
                        "status": "pending",
                        "shard_size": shard_size,
                    }
                rank = end_rank

    for shard in shard_specs():
        if remaining_rank_budget is not None:
            available = max(0, remaining_rank_budget)
            if available <= 0:
                break
            shard = dict(shard)
            shard["end_rank"] = min(
                int(shard["end_rank"]),
                int(shard["next_rank"]) + available,
            )
            if int(shard["next_rank"]) >= int(shard["end_rank"]):
                break
        pool_index = int(shard["pool_index"])
        depth = int(shard["depth"])
        operation_pool = operation_pools[pool_index]
        start_rank = int(shard["next_rank"])
        end_rank = int(shard["end_rank"])
        running_shard = dict(shard, status="running")
        publish_shard(running_shard)
        try:
            plan = ultimate_opengl_backend.build_analysis_plan(
                root_stream,
                width=before.width,
                height=before.height,
                bit_depth=before.bit_depth,
                color_type=before.color_type,
                scanline_size=before.scanline_size,
                expected_size=before.expected_size,
                operation_pool=operation_pool,
                pool_index=pool_index,
                depth=depth,
                start_rank=start_rank,
                end_rank=end_rank,
                target_adler=target_adler,
                max_hits=max_hits,
            )
            decision = ultimate_opengl_backend.explain_analysis(plan, gpu_config)
            if not decision.runnable:
                publish_shard(dict(running_shard, status="pending"))
                return nominations, decision.reason
            result = ultimate_opengl_backend.run_analysis_gpu(plan, gpu_config)
        except Exception as exc:
            publish_shard(dict(running_shard, status="pending", error=str(exc)))
            return nominations, "Ultimate OpenGL analysis failed: %s" % exc
        next_rank = max(start_rank, min(end_rank, int(result.next_rank)))
        completed_shard = dict(
            running_shard,
            next_rank=next_rank,
            tested=int(running_shard.get("tested", 0) or 0) + int(result.tested),
            pruned=int(running_shard.get("pruned", 0) or 0) + int(result.pruned),
            status="done" if next_rank >= end_rank else "pending",
        )
        if result.fallback_reason:
            completed_shard["fallback_reason"] = result.fallback_reason
            if not warning:
                warning = "OpenGL shader fallback: %s" % result.fallback_reason
        if result.reason and not warning:
            warning = result.reason
        publish_shard(completed_shard)
        if remaining_rank_budget is not None:
            remaining_rank_budget = max(0, remaining_rank_budget - max(0, next_rank - start_rank))
        for hit in result.hits:
            try:
                operations = _normalize_ultimate_operation_sequence(
                    tuple(operation_pool[index] for index in hit.operation_indices)
                )
            except (IndexError, TypeError):
                continue
            candidate_stream = _replay_operations(root_stream, operations)
            if candidate_stream is None:
                continue
            candidate_data = _rebuild_with_single_idat_stream(chunks, candidate_stream)
            candidate_analysis = idat.analyze_idat_stream(
                candidate_data,
                source_kind="candidate_from_original",
                crc_provenance="rebuilt_by_chunklate",
                target_adler=target_adler,
            )
            candidate_score = super_mega_linefeed_score(candidate_analysis, len(operations))
            if candidate_score <= parent_score and candidate_analysis.adler_status != "adler_match":
                continue
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
            nominations = _remember_ultimate_top_candidate(
                nominations,
                candidate,
                limit=max_hits,
            )
        if nominations and any(candidate.after.adler_status == "adler_match" for candidate in nominations):
            return nominations, warning
    return nominations, warning


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
    gpu_suspect_offsets: tuple[int, ...] = (),
    gpu_config: Any = None,
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
    gpu_analysis_warning = ""

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
    suspect_offsets = _merge_ultimate_offsets(
        tuple(gpu_suspect_offsets or ()),
        suspect_offsets,
        max_offsets=max(max_offsets, len(tuple(gpu_suspect_offsets or ())) + max_offsets),
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
        snapshot_shards = tuple(
            sorted(
                (
                    _normalize_ultimate_progress_shard(shard)
                    for shard in current_shards.values()
                    if isinstance(shard, dict)
                ),
                key=lambda item: (
                    int(item.get("pool_index", 0) or 0),
                    int(item.get("depth", 0) or 0),
                    int(item.get("start_rank", 0) or 0),
                ),
            )
        )
        confirmed_attempted = max(
            tested,
            _ultimate_progress_shards_attempted(snapshot_shards),
            attempted_candidates if not snapshot_shards else 0,
        )
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
            shards=snapshot_shards,
            attempted_candidates=confirmed_attempted,
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
                normalized = _normalize_ultimate_progress_shard(shard)
                shard.update(normalized)
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

    def raise_if_interrupt_requested(
        *,
        restore_handler: bool = True,
        before_finalize: Callable[[], None] | None = None,
    ) -> None:
        if not interrupt_requested:
            return
        report_pending_interrupt_warning()
        request_parallel_stop()
        if before_finalize is not None:
            before_finalize()
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

    def gpu_shard_key(shard: dict[str, Any]) -> str:
        return "opengl:%s:%s:%s:%s" % (
            int(shard.get("pool_index", 0) or 0),
            int(shard.get("depth", 0) or 0),
            int(shard.get("start_rank", 0) or 0),
            int(shard.get("end_rank", 0) or 0),
        )

    def record_gpu_shard(shard: dict[str, Any]) -> None:
        normalized = _normalize_ultimate_progress_shard(dict(shard, backend="opengl"))
        current_shards[gpu_shard_key(normalized)] = normalized
        save_progress_snapshot(
            phase="exhaustive",
            depth=int(normalized.get("depth", current_depth) or current_depth or 1),
            pool_index=int(normalized.get("pool_index", current_pool_index) or current_pool_index),
            combination_rank=int(normalized.get("next_rank", current_combination_rank) or 0),
            combination_indices=None,
        )

    def gpu_done_shard_covers(pool_index: int, depth: int, rank: int) -> bool:
        shard_sources: list[dict[str, Any]] = [
            shard for shard in current_shards.values() if isinstance(shard, dict)
        ]
        if progress_resume is not None:
            shard_sources.extend(
                shard for shard in progress_resume.shards if isinstance(shard, dict)
            )
        for shard in shard_sources:
            if str(shard.get("backend", "")) != "opengl" or str(shard.get("status", "")) != "done":
                continue
            try:
                if int(shard.get("pool_index", 0) or 0) != int(pool_index):
                    continue
                if int(shard.get("depth", 0) or 0) != int(depth):
                    continue
                start_rank = int(shard.get("start_rank", 0) or 0)
                end_rank = int(shard.get("end_rank", 0) or 0)
            except (TypeError, ValueError):
                continue
            if start_rank <= int(rank) < end_rank:
                return True
        return False

    if not terminal(best) and not fast_resume_complete:
        gpu_candidates, gpu_analysis_warning = _ultimate_gpu_analysis_candidates(
            chunks=chunks,
            root_stream=root_stream,
            before=before,
            operation_pools=operation_pools,
            target_adler=target_adler,
            gpu_config=gpu_config,
            max_depth=max_depth,
            progress_resume=progress_resume,
            candidate_limit=max(ULTIMATE_LINEFEED_TOP_CANDIDATES, min(25, max(5, visual_gallery_limit))),
            budget_limit=budget_limit,
            shard_callback=record_gpu_shard,
        )
        for candidate in gpu_candidates:
            stream_hash = _stream_state_key(
                b"".join(chunk.data for chunk in png.iter_chunks(candidate.data) if chunk.chunk_type == b"IDAT")
            )
            if stream_hash in visited:
                continue
            visited.add(stream_hash)
            candidate = replace(candidate, state_id=next_state_id, parent_id=0)
            next_state_id += 1
            top_candidates = _remember_ultimate_top_candidate(top_candidates, candidate)
            remember_visual_candidate(candidate, tested)
            _preview_ultimate_candidate_if_valid(
                candidate,
                tested,
                progress_total,
                candidate_preview,
            )
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
                    depth=max(1, len(candidate.operations)),
                )
            if terminal(best):
                break

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
        for item in current_shards.values():
            if not isinstance(item, dict) or str(item.get("backend", "")) != "opengl":
                continue
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

        for item in resumed_by_shard.values():
            current_shards[shard_key(item)] = _normalize_ultimate_progress_shard(item)

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

        def parallel_display_total() -> int:
            return max(
                tested,
                parallel_progress_floor,
                _ultimate_progress_shards_attempted(current_shards.values()),
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
                original_next_rank = int(shard.get("next_rank", shard.get("start_rank", 0)) or 0)
                if remaining is not None:
                    shard["end_rank"] = min(
                        int(shard["end_rank"]),
                        original_next_rank + remaining,
                    )
                if int(shard["next_rank"]) >= int(shard["end_rank"]):
                    continue
                key = shard_key(shard)
                running_shard = _normalize_ultimate_progress_shard(dict(shard, status="running"))
                current_shards[key] = running_shard
                reserved_ranks += int(running_shard["end_rank"]) - int(running_shard["next_rank"])
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
                    confirmed = _ultimate_progress_shard_attempted(shard)
                    try:
                        shard["tested"] = max(int(shard.get("tested", 0) or 0), confirmed, live_tested)
                    except (TypeError, ValueError):
                        shard["tested"] = max(confirmed, live_tested)
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
                raise_if_interrupt_requested(
                    restore_handler=False,
                    before_finalize=drain_worker_progress,
                )
                done, _pending = wait(
                    tuple(futures),
                    timeout=ULTIMATE_LINEFEED_PARALLEL_PROGRESS_POLL_SECONDS,
                    return_when=FIRST_COMPLETED,
                )
                raise_if_interrupt_requested(
                    restore_handler=False,
                    before_finalize=drain_worker_progress,
                )
                if not done:
                    drain_worker_progress()
                    raise_if_interrupt_requested(
                        restore_handler=False,
                        before_finalize=drain_worker_progress,
                    )
                    continue
                drain_worker_progress()
                raise_if_interrupt_requested(
                    restore_handler=False,
                    before_finalize=drain_worker_progress,
                )
                for future in done:
                    shard = futures.pop(future)
                    inflight_progress.pop(shard_key(shard), None)
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
                    confirmed = _ultimate_progress_shard_attempted(result_shard)
                    result_shard["tested"] = max(
                        int(result_shard.get("tested", 0) or 0) + int(result.tested),
                        confirmed,
                    )
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
                        raise_if_interrupt_requested(
                            restore_handler=False,
                            before_finalize=drain_worker_progress,
                        )
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
            drain_worker_progress()
            _ultimate_shutdown_parallel_executor(
                executor,
                futures=futures,
                progress_queue=progress_queue,
                stop_event=stop_event,
            )
            raise
        except KeyboardInterrupt:
            request_parallel_stop()
            drain_worker_progress()
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
                        if gpu_done_shard_covers(pool_index, depth, current_combination_rank):
                            continue
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
    combined_progress_warning = "; ".join(
        item for item in (progress_warning, gpu_analysis_warning) if item
    )

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
        progress_warning=combined_progress_warning,
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
    lf_insert_budget: int = 1024,
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
        "phase2-lf-insert": max(0, lf_insert_budget),
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
                    "phase2-lf-insert",
                    _linefeed_lf_insert_mutations(
                        parent_stream,
                        center=center,
                        search_start=search_start,
                        backtrack=resolved_pre_error_backtrack,
                        forward=structural_forward,
                    ),
                    structural_window_start,
                    structural_window_end,
                    lf_insert_budget,
                    _count_linefeed_lf_insert_mutations(
                        parent_stream,
                        center=center,
                        search_start=search_start,
                        backtrack=resolved_pre_error_backtrack,
                        forward=structural_forward,
                    ),
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


def _deflate_header_priority_offsets(
    window_start: int,
    window_end: int,
    before: idat.IdatStreamAnalysis,
    header: deflate_header.DeflateHeaderAnalysis,
) -> tuple[int, ...]:
    if window_end <= window_start:
        return ()
    offsets: list[int] = []

    def add(offset: int) -> None:
        if window_start <= offset < window_end:
            offsets.append(offset)

    # Keep the zlib and deflate block preamble early for small synthetic cases.
    for offset in range(window_start, min(window_end, window_start + 16)):
        add(offset)

    anchors = []
    for value in (
        getattr(header, "byte_offset", None),
        getattr(header, "header_end_byte", None),
        before.error_offset,
    ):
        if value is None:
            continue
        anchors.append(int(value))
    for anchor in anchors:
        for radius in range(0, 33):
            add(anchor - radius)
            if radius:
                add(anchor + radius)

    for offset in range(window_start, window_end):
        add(offset)
    return tuple(dict.fromkeys(offsets))


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
    if after_header is None and before_header.btype == 2:
        try:
            _idat_chunks, candidate_stream = _idat_chunks_and_stream(candidate.data)
            after_header = deflate_header.analyze_deflate_header(candidate_stream)
        except Exception:
            after_header = None
    if after_header is None:
        return candidate.after.complete or candidate.after.decompressed_size > before.decompressed_size
    if (
        before_header.btype == 2
        and after_header.ok
        and after_header.btype != before_header.btype
        and not is_material_improvement(before, candidate.after)
    ):
        return False
    return after_header.ok


def _range_bits(start: int | None, end: int | None, *, limit: int) -> tuple[int, ...]:
    if start is None or end is None:
        return ()
    start = max(0, int(start))
    end = min(int(end), limit)
    if end <= start:
        return ()
    return tuple(range(start, end))


def _dynamic_token_bits(
    token: deflate_header.DynamicLengthToken,
    *,
    bit_limit: int,
) -> tuple[int, ...]:
    bits = list(_range_bits(token.bit_start, token.bit_end, limit=bit_limit))
    bits.extend(_range_bits(token.extra_bit_start, token.extra_bit_end, limit=bit_limit))
    return tuple(bits)


def _dynamic_huffman_suspect_bits(
    trace: deflate_header.DynamicHeaderTrace,
    stream: bytes,
    *,
    max_bits: int,
) -> tuple[int, ...]:
    bit_limit = len(stream) * 8
    if bit_limit <= 0 or max_bits <= 0:
        return ()

    bits: list[int] = []

    def add_many(values: Iterable[int]) -> None:
        for bit in values:
            if 0 <= bit < bit_limit:
                bits.append(int(bit))

    if trace.hlit is not None:
        eob_index = 256
        for token in trace.tokens:
            if token.length_start <= eob_index < token.length_end:
                add_many(_dynamic_token_bits(token, bit_limit=bit_limit))
        boundary = int(trace.hlit)
        for token in trace.tokens:
            if (
                token.length_start <= boundary <= token.length_end
                or abs(token.length_start - boundary) <= 8
                or abs(token.length_end - boundary) <= 8
            ):
                add_many(_dynamic_token_bits(token, bit_limit=bit_limit))

    for _name, start, end in trace.count_bits:
        add_many(_range_bits(start, end, limit=bit_limit))

    for _symbol, start, end in trace.code_length_bits:
        add_many(_range_bits(start, end, limit=bit_limit))

    header_start = 16
    header_end = trace.header_end_bit or trace.bit_offset or min(bit_limit, header_start + max_bits)
    header_end = min(bit_limit, max(header_start, header_end))
    add_many(range(header_start, min(header_end, header_start + max_bits)))

    return tuple(dict.fromkeys(bits))[:max_bits]


def _stream_context_hex(stream: bytes, stream_offset: int, *, radius: int = 16) -> str:
    if not stream:
        return ""
    center = min(max(0, int(stream_offset)), max(0, len(stream) - 1))
    start = max(0, center - int(radius))
    end = min(len(stream), center + int(radius) + 1)
    return stream[start:end].hex()


def idat_local_deflate_diagnostic(
    data: bytes,
    *,
    analysis: idat.IdatStreamAnalysis | None = None,
    window_limit: int = 0x120,
    context_radius: int = 24,
    max_suspect_bits: int = 192,
) -> IdatLocalDeflateDiagnostic | None:
    before = analysis or idat.analyze_idat_stream(data)
    if not before.supported:
        return None

    try:
        idat_chunks, idat_stream = _idat_chunks_and_stream(data)
    except png.PngFormatError:
        return None
    if not idat_stream:
        return None

    trace = deflate_header.trace_dynamic_header(idat_stream)
    anchors = [
        before.error_offset,
        before.error_idat_offset,
        getattr(before.deflate_header, "byte_offset", None) if before.deflate_header is not None else None,
        trace.byte_offset,
    ]
    stream_offset = next((int(anchor) for anchor in anchors if anchor is not None), 0)
    stream_offset = min(max(0, stream_offset), max(0, len(idat_stream) - 1))

    location = _locate_idat_stream_offset(idat_chunks, stream_offset)
    if location is None:
        file_offset = None
        idat_index = None
        idat_offset = None
    else:
        chunk, idat_index, idat_offset = location
        file_offset = chunk.offset + 8 + idat_offset

    if before.decompressed_size == 0:
        window_start = 0
    else:
        window_start = max(0, stream_offset - int(context_radius))
    hard_end = max(
        stream_offset + int(context_radius) + 1,
        int(before.error_offset or 0) + int(context_radius) + 1,
        int(trace.byte_offset or 0) + int(context_radius) + 1,
    )
    if before.decompressed_size == 0:
        hard_end = max(hard_end, int(window_limit))
    window_end = min(len(idat_stream), max(window_start + 1, hard_end))
    if window_limit > 0 and before.decompressed_size == 0:
        window_end = min(window_end, int(window_limit))

    suspect_bits = _dynamic_huffman_suspect_bits(
        trace,
        idat_stream,
        max_bits=max_suspect_bits,
    )
    suspect_bytes = tuple(
        dict.fromkeys(
            bit // 8
            for bit in suspect_bits
            if window_start <= bit // 8 < window_end
        )
    )

    return IdatLocalDeflateDiagnostic(
        before=before,
        trace=trace,
        stream_size=len(idat_stream),
        stream_offset=stream_offset,
        file_offset=file_offset,
        idat_index=idat_index,
        idat_offset=idat_offset,
        window_start=window_start,
        window_end=window_end,
        context_hex=_stream_context_hex(idat_stream, stream_offset, radius=context_radius),
        suspect_bits=suspect_bits,
        suspect_byte_offsets=suspect_bytes,
    )


def _fmt_optional_hex(value: int | None) -> str:
    return "?" if value is None else "0x%x" % int(value)


def _format_bit_range(start: int | None, end: int | None) -> str:
    if start is None or end is None:
        return "?"
    return "%s..%s" % (int(start), int(end))


def _dynamic_token_summary(
    trace: deflate_header.DynamicHeaderTrace,
    *,
    limit: int = 8,
) -> str:
    if not trace.tokens:
        return "none"
    priority = _dynamic_semantic_priority_tokens(trace, limit=limit)
    parts = []
    for token in priority:
        label = (
            "sym=%s bits=%s lengths=%s..%s repeat=%s"
            % (
                token.symbol,
                _format_bit_range(token.bit_start, _dynamic_length_token_bit_end(token)),
                token.length_start,
                token.length_end,
                token.repeat,
            )
        )
        if token.error:
            label += " error=%s" % token.error
        parts.append(label)
    return "; ".join(parts)


def _limited_csv(values: Iterable[int], *, formatter: Callable[[int], str], limit: int = 24) -> str:
    items = tuple(values)
    if not items:
        return "none"
    shown = ", ".join(formatter(value) for value in items[:limit])
    if len(items) > limit:
        shown += ", ..."
    return shown


def idat_local_deflate_diagnostic_summary_lines(
    data: bytes,
    *,
    analysis: idat.IdatStreamAnalysis | None = None,
) -> tuple[str, ...]:
    diagnostic = idat_local_deflate_diagnostic(data, analysis=analysis)
    if diagnostic is None:
        return ("-IDAT local deflate diagnostic: unavailable.",)

    trace = diagnostic.trace
    lines = [
        (
            "-IDAT local deflate diagnostic: status=%s; stream=0x%x/%s; file=%s; "
            "IDAT=%s; idat_offset=%s; window=0x%x..0x%x; context=%s."
            % (
                trace.status,
                diagnostic.stream_offset,
                diagnostic.stream_size,
                _fmt_optional_hex(diagnostic.file_offset),
                "?" if diagnostic.idat_index is None else diagnostic.idat_index,
                _fmt_optional_hex(diagnostic.idat_offset),
                diagnostic.window_start,
                diagnostic.window_end,
                diagnostic.context_hex or "none",
            )
        ),
        (
            "-IDAT dynamic Huffman fields: bfinal=%s; btype=%s; HLIT=%s; HDIST=%s; HCLEN=%s; "
            "count_bits=%s; code_length_lengths=%s."
            % (
                trace.bfinal,
                trace.btype,
                trace.hlit,
                trace.hdist,
                trace.hclen,
                ", ".join("%s:%s" % (name, _format_bit_range(start, end)) for name, start, end in trace.count_bits)
                or "none",
                ",".join(str(value) for value in trace.code_length_lengths) or "none",
            )
        ),
        (
            "-IDAT dynamic Huffman failure: tokens=%s; lengths=%s; literal_error=%s; "
            "distance_error=%s; reason=%s."
            % (
                len(trace.tokens),
                trace.length_count,
                trace.literal_error or "none",
                trace.distance_error or "none",
                trace.reason or "none",
            )
        ),
        (
            "-IDAT dynamic Huffman suspect bytes: %s; suspect_bits=%s."
            % (
                _limited_csv(diagnostic.suspect_byte_offsets, formatter=lambda value: "0x%x" % value),
                _limited_csv(diagnostic.suspect_bits, formatter=lambda value: "0x%x.%s" % (value // 8, value % 8)),
            )
        ),
        "-IDAT dynamic Huffman token suspects: %s." % _dynamic_token_summary(trace),
    ]
    return tuple(lines)


def _local_deflate_score(analysis: idat.IdatStreamAnalysis) -> tuple[int, int, int, int, int, int, int]:
    status_rank = {
        "complete": 6,
        "bad_adler": 5,
        "partial": 4,
        "incomplete_stream": 3,
        "corrupt_deflate": 2,
        "bad_zlib_header": 1,
    }.get(analysis.status, 0)
    header = analysis.deflate_header
    header_rank = {
        "ok": 4,
        "invalid_huffman_lengths": 3,
        "bad_code_length_tree": 2,
        "truncated_header": 1,
    }.get(header.status if header is not None else "", 0)
    return (
        1 if analysis.complete else 0,
        analysis.usable_scanlines,
        analysis.complete_scanlines,
        analysis.decompressed_size,
        status_rank,
        header_rank,
        analysis.error_offset if analysis.error_offset is not None else -1,
    )


def _local_deflate_priority_offsets(
    diagnostic: IdatLocalDeflateDiagnostic,
    *,
    max_offsets: int,
) -> tuple[int, ...]:
    offsets: list[int] = []
    start = diagnostic.window_start
    end = diagnostic.window_end

    def add(offset: int) -> None:
        if start <= offset < end:
            offsets.append(int(offset))

    for offset in range(start, min(end, start + 16)):
        add(offset)
    for offset in diagnostic.suspect_byte_offsets:
        add(offset)
    for anchor in (diagnostic.stream_offset, diagnostic.trace.byte_offset):
        for radius in range(0, 33):
            add(anchor - radius)
            if radius:
                add(anchor + radius)
    for offset in range(start, end):
        add(offset)
    return tuple(dict.fromkeys(offsets))[: max(1, int(max_offsets))]


def probe_idat_deflate_local_candidates(
    data: bytes,
    *,
    budget: int = 2048,
    max_offsets: int = 96,
    max_bits: int = 160,
    progress: QueueProgressCallback | None = None,
) -> IdatDeflateProbeResult:
    before = idat.analyze_idat_stream(data)
    strategy = "deflate-local"
    diagnostic = idat_local_deflate_diagnostic(data, analysis=before)
    if diagnostic is None:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, "local diagnostic unavailable")
    if before.complete:
        return IdatDeflateProbeResult(before, None, diagnostic.window_start, diagnostic.window_end, 0, False, strategy, "IDAT stream is already complete")

    offsets = _local_deflate_priority_offsets(diagnostic, max_offsets=max_offsets)
    bits = tuple(
        bit
        for bit in diagnostic.suspect_bits
        if diagnostic.window_start * 8 <= bit < diagnostic.window_end * 8
    )[: max(1, int(max_bits))]
    common_bytes = (0x00, 0x0A, 0x0D, 0xFF)
    best: IdatDeflateCandidate | None = None
    best_score = analysis_score(before)
    diagnostic_best: IdatDeflateCandidate | None = None
    diagnostic_score = _local_deflate_score(before)
    tested = 0
    budget_exhausted = False
    seen_candidates: set[bytes] = set()

    def consider(candidate: IdatDeflateCandidate | None) -> bool:
        nonlocal best, best_score, diagnostic_best, diagnostic_score, tested, budget_exhausted
        if tested >= budget:
            budget_exhausted = True
            return True
        tested += 1
        if progress is not None and tested % 100 == 0:
            progress(strategy, tested, budget)
        if candidate is None:
            return False
        digest = hashlib.sha1(candidate.data).digest()
        if digest in seen_candidates:
            return False
        seen_candidates.add(digest)

        candidate_diagnostic_score = _local_deflate_score(candidate.after)
        if candidate_diagnostic_score > diagnostic_score:
            diagnostic_best = candidate
            diagnostic_score = candidate_diagnostic_score

        if not is_material_improvement(before, candidate.after):
            return False
        candidate_score = analysis_score(candidate.after)
        if candidate_score <= best_score:
            return False
        best = candidate
        best_score = candidate_score
        return bool(candidate.after.complete)

    if progress is not None:
        progress(strategy, 0, budget)

    for offset in offsets:
        if consider(mutate_idat_stream_edit(data, offset, "remove", remove_count=1, before_analysis=before)):
            break
        for value in common_bytes:
            if consider(mutate_idat_stream_edit(data, offset, "insert", new_bytes=bytes((value,)), before_analysis=before)):
                break
            if consider(mutate_idat_stream_byte(data, offset, value, before_analysis=before)):
                break
        if budget_exhausted or (best is not None and best.after.complete):
            break

    if not budget_exhausted and not (best is not None and best.after.complete):
        for bit in bits:
            if consider(mutate_idat_stream_bit_flips(data, (bit,), before_analysis=before)):
                break
            if consider(mutate_idat_stream_bit_shift(data, bit, "bit-delete", before_analysis=before)):
                break
            for value in (0, 1):
                if consider(mutate_idat_stream_bit_shift(data, bit, "bit-insert", bit_value=value, before_analysis=before)):
                    break
            if budget_exhausted or (best is not None and best.after.complete):
                break

    if progress is not None:
        progress(strategy, tested, budget)

    reason = (
        "offsets=%s; bits=%s; %s"
        % (
            len(offsets),
            len(bits),
            diagnostic.trace.summary,
        )
    )
    return IdatDeflateProbeResult(
        before,
        best,
        diagnostic.window_start,
        diagnostic.window_end,
        tested,
        budget_exhausted,
        strategy,
        reason,
        diagnostic_best=diagnostic_best,
    )


DEEP_BEAM_DEFAULT_BUDGET = 10_000_000
DEEP_BEAM_DEFAULT_MAX_DEPTH = 5
DEEP_BEAM_DEFAULT_WIDTH = 256
DEEP_BEAM_DEFAULT_TOP_CANDIDATES = 25
DEEP_BEAM_DEFAULT_CHECKPOINT_EVERY = 25_000
DEEP_BEAM_DEFAULT_GPU_SHARD_SIZE = 262_144
DEEP_BEAM_DEFAULT_CPU_BATCH_SIZE = 128
DEEP_BEAM_SUCCESSOR_KEEP_LIMIT = 512
DEEP_BEAM_WORKER_IN_FLIGHT_LIMIT = 16
DEEP_BEAM_AUTO_WORKER_LIMIT = 4
DEEP_BEAM_MIN_AVAILABLE_MEMORY_BYTES = 1024 * 1024 * 1024
HUFFMAN_KRAFT_MEMORY_SOFT_BYTES = 2 * 1024 * 1024 * 1024
HUFFMAN_KRAFT_MEMORY_HARD_BYTES = DEEP_BEAM_MIN_AVAILABLE_MEMORY_BYTES
HUFFMAN_KRAFT_MEMORY_EMERGENCY_BYTES = 512 * 1024 * 1024
HUFFMAN_KRAFT_THROTTLE_WORKER_LIMIT = 4
HUFFMAN_KRAFT_THROTTLE_BATCH_SIZE = 128
HUFFMAN_KRAFT_HARD_THROTTLE_BATCH_SIZE = 64
DEEP_BEAM_GPU_MAX_HITS = 128
PERIODIC_MODEL_DEFAULT_BUDGET = 250_000
PERIODIC_MODEL_DEFAULT_MAX_DEPTH = 3
PERIODIC_MODEL_DEFAULT_TOP_CANDIDATES = 25
PERIODIC_MODEL_CHECKPOINT_EVERY = 25_000
AFFINE_CORRUPTION_DEFAULT_BUDGET = 250_000
AFFINE_CORRUPTION_DEFAULT_TOP_CANDIDATES = 25
AFFINE_CORRUPTION_CHECKPOINT_EVERY = 25_000
HUFFMAN_KRAFT_DEFAULT_BUDGET = 1_000_000
HUFFMAN_KRAFT_DEFAULT_MAX_DEPTH = 4
HUFFMAN_KRAFT_DEFAULT_WIDTH = 128
HUFFMAN_KRAFT_DEFAULT_TOP_CANDIDATES = 25
HUFFMAN_KRAFT_CHECKPOINT_EVERY = 25_000
HUFFMAN_KRAFT_PROGRESS_EVERY = 5_000
HUFFMAN_KRAFT_GPU_HIT_LIMIT = DEEP_BEAM_GPU_MAX_HITS
HUFFMAN_KRAFT_SUCCESSOR_KEEP_LIMIT = DEEP_BEAM_SUCCESSOR_KEEP_LIMIT
FIRST_FILTER_LITERAL_DEFAULT_BUDGET = 10_000
FIRST_FILTER_LITERAL_DEFAULT_TOP_CANDIDATES = 25
FIRST_FILTER_LITERAL_ROUTE_VERSION = 2
KRAFT_BACKREF_DEFAULT_BUDGET = 200_000
KRAFT_BACKREF_DEFAULT_TOP_CANDIDATES = 25
KRAFT_BACKREF_CHECKPOINT_EVERY = 25_000
KRAFT_BACKREF_DEFAULT_MAX_DEPTH = 3
KRAFT_BACKREF_MAX_OPERATIONS_PER_SEED = 25_000
KRAFT_BACKREF_ROUTE_VERSION = 2
HUFFMAN_ORACLE_DEFAULT_BUDGET = 750_000
HUFFMAN_ORACLE_DEFAULT_MAX_DEPTH = 3
HUFFMAN_ORACLE_DEFAULT_WIDTH = 96
HUFFMAN_ORACLE_DEFAULT_TOP_CANDIDATES = 25
HUFFMAN_ORACLE_CHECKPOINT_EVERY = 25_000
GLOBAL_CRC_RESIDUE_DEFAULT_BUDGET = 750_000
GLOBAL_CRC_RESIDUE_DEFAULT_MAX_RULES = 4
GLOBAL_CRC_RESIDUE_DEFAULT_TOP_CANDIDATES = 25
GLOBAL_CRC_RESIDUE_CHECKPOINT_EVERY = 25_000
CRC_PERIODIC_DEFAULT_BUDGET = 500_000
CRC_PERIODIC_DEFAULT_MAX_EDITS = 4
CRC_PERIODIC_DEFAULT_TOP_CANDIDATES = 25
CRC_PERIODIC_CHECKPOINT_EVERY = 25_000
DEFLATE_SALVAGE_DEFAULT_BUDGET = 250_000
DEEP_BEAM_COMMON_BYTES = (0x00, 0x0A, 0x0D, 0xFF)
DEEP_BEAM_FOCUS_OFFSETS = (0x02, 0x56, 0x5E, 0x5F, 0x60, 0x61, 0x62, 0x63, 0x6E)
DEEP_BEAM_FOCUS_BIT_RANGES = (
    (19, 33),
    (101, 166),
    (689, 695),
    (764, 774),
)


def idat_partial_raw_prefix(stream: bytes, *, max_output: int = 8192) -> IdatRawPrefix:
    limit = max(0, int(max_output))
    if not stream or limit <= 0:
        return IdatRawPrefix(b"")
    decompressor = zlib.decompressobj()
    raw = bytearray()
    for offset, value in enumerate(stream):
        try:
            chunk = decompressor.decompress(bytes((value,)), max(0, limit - len(raw)))
        except zlib.error as exc:
            return IdatRawPrefix(bytes(raw), offset, str(exc), False)
        if chunk:
            raw.extend(chunk)
            if len(raw) >= limit:
                return IdatRawPrefix(bytes(raw[:limit]), offset, "", bool(decompressor.eof))
    try:
        if len(raw) < limit:
            raw.extend(decompressor.flush(max(0, limit - len(raw))))
    except zlib.error as exc:
        return IdatRawPrefix(bytes(raw[:limit]), len(stream), str(exc), False)
    return IdatRawPrefix(bytes(raw[:limit]), None, "", bool(decompressor.eof))


def score_png_raw_prefix(raw: bytes, analysis: idat.IdatStreamAnalysis) -> PngRawPrefixScore:
    first_filter = raw[0] if raw else None
    first_filter_ok = first_filter in (0, 1, 2, 3, 4)
    scanline_size = max(0, int(getattr(analysis, "scanline_size", 0) or 0))
    checked_rows = 0
    valid_rows = 0
    if scanline_size > 0 and raw:
        max_rows = min(int(getattr(analysis, "height", 0) or 0) or 1, len(raw) // scanline_size + 1)
        for row in range(max_rows):
            row_start = row * scanline_size
            if row_start >= len(raw):
                break
            checked_rows += 1
            if raw[row_start] in (0, 1, 2, 3, 4):
                valid_rows += 1

    alpha_checked = 0
    alpha_plausible = 0
    if (
        first_filter_ok
        and int(getattr(analysis, "color_type", -1) or -1) == 6
        and int(getattr(analysis, "bit_depth", 0) or 0) == 8
        and scanline_size > 1
    ):
        row_payload = raw[1 : min(len(raw), scanline_size)]
        for alpha in row_payload[3::4][:64]:
            alpha_checked += 1
            if alpha in (0, 255):
                alpha_plausible += 1

    return PngRawPrefixScore(
        raw_size=len(raw),
        first_filter=first_filter,
        first_filter_ok=bool(first_filter_ok),
        checked_filter_rows=checked_rows,
        valid_filter_rows=valid_rows,
        alpha_checked=alpha_checked,
        alpha_plausible=alpha_plausible,
    )


def raw_png_oracle_decision(
    stream: bytes,
    analysis: idat.IdatStreamAnalysis,
    *,
    min_rows: int = 0,
    max_output: int = 8192,
) -> RawPngOracleDecision:
    raw_prefix = idat_partial_raw_prefix(stream, max_output=max_output)
    raw_score = score_png_raw_prefix(raw_prefix.raw, analysis)
    reject_reason = ""
    if not raw_prefix.raw:
        reject_reason = "no raw prefix"
    elif not raw_score.first_filter_ok:
        reject_reason = "first raw byte is not a PNG filter"
    elif int(min_rows) > 0 and raw_score.valid_filter_rows < int(min_rows):
        reject_reason = "not enough valid PNG filter rows"
    return RawPngOracleDecision(
        raw_prefix=raw_prefix,
        raw_score=raw_score,
        rejected=bool(reject_reason),
        reject_reason=reject_reason,
    )


def _deep_beam_workers(workers: str | int | None) -> int:
    if workers is None or str(workers).strip().lower() == "auto":
        return max(1, min(DEEP_BEAM_AUTO_WORKER_LIMIT, multiprocessing.cpu_count()))
    try:
        return max(1, int(workers))
    except (TypeError, ValueError):
        return 1


def _deep_beam_gpu_requested(gpu: bool | str | int | None) -> bool:
    if isinstance(gpu, str):
        value = gpu.strip().lower()
        return value in ("1", "true", "yes", "y", "on", "gpu", "cuda", "opencl")
    return bool(gpu)


def _deep_beam_gpu_config(gpu: bool | str | int | None, gpu_config: Any = None) -> Any:
    if gpu_config is not None:
        return gpu_config
    from . import gpu_runtime

    return gpu_runtime.GpuRuntimeConfig(enabled=_deep_beam_gpu_requested(gpu))


def _huffman_balance(lengths: tuple[int, ...] | list[int]) -> tuple[int, int, int, int]:
    used = [int(length) for length in lengths if int(length) > 0]
    if not used:
        return 0, 999, 0, 0
    max_bits = max(used)
    counts = [0] * (max_bits + 1)
    for length in used:
        counts[length] += 1
    left = 1
    worst_oversubscribe = 0
    for bits in range(1, max_bits + 1):
        left <<= 1
        left -= counts[bits]
        if left < 0:
            worst_oversubscribe = max(worst_oversubscribe, abs(left))
    debt = abs(left) + (worst_oversubscribe * 4)
    return left, debt, len(used), max_bits


def _deep_beam_huffman_score(stream: bytes) -> tuple[int, int, int, int, int, int]:
    trace = deflate_header.trace_dynamic_header(stream)
    if trace.status == "ok":
        return 5, 1, 0, 0, trace.length_count, int(trace.header_end_bit or 0)
    if trace.btype != 2:
        return (2 if trace.status == "ok" else 0), 0, 999, 999, trace.length_count, int(trace.bit_offset or 0)
    literal_left, literal_debt, literal_used, _literal_bits = _huffman_balance(trace.literal_lengths)
    distance_left, distance_debt, distance_used, _distance_bits = _huffman_balance(trace.distance_lengths)
    has_eob = 1 if len(trace.literal_lengths) > 256 and trace.literal_lengths[256] > 0 else 0
    header_rank = {
        "ok": 5,
        "invalid_huffman_lengths": 4,
        "bad_code_length_tree": 2,
        "truncated_header": 1,
    }.get(trace.status, 0)
    return (
        header_rank,
        has_eob,
        literal_debt + (0 if literal_left == 0 else 1),
        distance_debt + (0 if distance_left == 0 else 1),
        literal_used + distance_used,
        int(trace.bit_offset or 0),
    )


def _idat_crc_match_count_for_original_shape(data: bytes, original_idat_count: int) -> int:
    try:
        idat_chunks = tuple(chunk for chunk in png.iter_chunks(data) if chunk.chunk_type == b"IDAT")
    except png.PngFormatError:
        return 0
    if len(idat_chunks) != int(original_idat_count):
        return 0
    return sum(1 for chunk in idat_chunks if chunk.crc == chunk.computed_crc)


def _deep_beam_score(
    analysis: idat.IdatStreamAnalysis,
    stream: bytes,
    operation_count: int,
    *,
    data: bytes,
    original_idat_count: int,
) -> tuple[int, ...]:
    status_rank = {
        "complete": 8,
        "bad_adler": 7,
        "partial": 6,
        "incomplete_stream": 5,
        "corrupt_deflate": 4,
        "bad_zlib_header": 1,
    }.get(analysis.status, 0)
    header_rank, has_eob, literal_debt, distance_debt, length_count, bit_offset = _deep_beam_huffman_score(stream)
    expected_delta = abs(int(analysis.expected_size or 0) - int(analysis.decompressed_size or 0))
    raw_prefix = idat_partial_raw_prefix(stream)
    raw_score = score_png_raw_prefix(raw_prefix.raw, analysis)
    return (
        1 if analysis.complete else 0,
        int(analysis.usable_scanlines),
        int(analysis.complete_scanlines),
        int(raw_score.first_filter_rank),
        int(raw_score.valid_filter_rows),
        int(raw_score.alpha_rank),
        int(raw_score.raw_size),
        int(analysis.decompressed_size),
        status_rank,
        header_rank,
        has_eob,
        -int(literal_debt),
        -int(distance_debt),
        int(length_count),
        int(analysis.error_offset if analysis.error_offset is not None else -1),
        -expected_delta,
        _idat_crc_match_count_for_original_shape(data, original_idat_count),
        -int(operation_count),
        int(bit_offset),
    )


def _deep_beam_operation_to_json(operation: IdatDeepBeamOperation) -> dict[str, object]:
    return {
        "kind": operation.kind,
        "stream_offset": int(operation.stream_offset),
        "old": operation.old_bytes.hex(),
        "new": operation.new_bytes.hex(),
        "bits": list(operation.bit_offsets),
    }


def _deep_beam_operation_from_json(record: object) -> IdatDeepBeamOperation | None:
    if not isinstance(record, dict):
        return None
    try:
        return IdatDeepBeamOperation(
            str(record["kind"]),
            int(record.get("stream_offset", 0)),
            bytes.fromhex(str(record.get("old", ""))),
            bytes.fromhex(str(record.get("new", ""))),
            tuple(int(bit) for bit in record.get("bits", ()) if isinstance(bit, int) or str(bit).isdigit()),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _deep_beam_record_operations(record: dict[str, object]) -> tuple[IdatDeepBeamOperation, ...]:
    raw_operations = record.get("operations", ())
    if not isinstance(raw_operations, (list, tuple)):
        raw_operations = ()
    return tuple(
        operation
        for operation in (_deep_beam_operation_from_json(item) for item in raw_operations)
        if operation is not None
    )


def _deep_beam_context_start_candidates(stream: bytes, offset: int, expected: bytes) -> tuple[int, ...]:
    if not expected:
        return (max(0, min(int(offset), len(stream))),)
    start_min = max(0, int(offset) - 8)
    start_max = min(len(stream), int(offset) + 1)
    starts = [int(offset), *range(start_min, start_max)]
    return tuple(dict.fromkeys(start for start in starts if 0 <= start <= len(stream) - len(expected)))


def _deep_beam_context_matches_near(stream: bytes, offset: int, expected: bytes) -> bool:
    if not expected:
        return True
    return any(
        stream[start : start + len(expected)] == expected
        for start in _deep_beam_context_start_candidates(stream, offset, expected)
    )


def _deep_beam_apply_byte_context_operation(stream: bytes, operation: IdatDeepBeamOperation) -> bytes | None:
    offset = int(operation.stream_offset)
    if offset < 0 or offset > len(stream):
        return None
    old = operation.old_bytes
    new = operation.new_bytes
    kind = operation.kind.strip().lower()

    if "remove" in kind:
        if not old or offset + len(old) > len(stream) or stream[offset : offset + len(old)] != old:
            return None
        return stream[:offset] + stream[offset + len(old) :]
    if "insert" in kind and "bit-insert" not in kind:
        return stream[:offset] + new + stream[offset:]
    if "replace" in kind and "bit-range" not in kind:
        if not old or offset + len(old) > len(stream) or stream[offset : offset + len(old)] != old:
            return None
        return stream[:offset] + new + stream[offset + len(old) :]

    if old or new:
        for start in _deep_beam_context_start_candidates(stream, offset, old):
            if old and stream[start : start + len(old)] != old:
                continue
            return stream[:start] + new + stream[start + len(old) :]
    return None


def _deep_beam_apply_operation_to_stream(stream: bytes, operation: IdatDeepBeamOperation) -> bytes | None:
    kind = operation.kind.strip().lower()
    if "huffman-kraft-token" in kind and operation.bit_offsets:
        replacement_bits = tuple(int(value) & 1 for value in operation.new_bytes)
        bit_start = min(operation.bit_offsets)
        bit_end = max(operation.bit_offsets) + 1
        return _replace_stream_bits_preserve_length(stream, bit_start, bit_end, replacement_bits)
    if "bit-delete" in kind and operation.bit_offsets:
        shifted = _shift_stream_delete_bit(stream, int(operation.bit_offsets[0]))
        if shifted is not None and _deep_beam_context_matches_near(shifted, operation.stream_offset, operation.new_bytes):
            return shifted
        return None
    if "bit-insert" in kind and operation.bit_offsets:
        for bit_value in (0, 1):
            shifted = _shift_stream_insert_bit(stream, int(operation.bit_offsets[0]), bit_value)
            if shifted is not None and _deep_beam_context_matches_near(shifted, operation.stream_offset, operation.new_bytes):
                return shifted
        return None
    if "bit-flip" in kind and operation.bit_offsets:
        return _flip_stream_bits(stream, operation.bit_offsets)
    return _deep_beam_apply_byte_context_operation(stream, operation)


def _deep_beam_replay_operations(
    source_stream: bytes,
    operations: tuple[IdatDeepBeamOperation, ...],
) -> bytes | None:
    stream = source_stream
    for operation in operations:
        stream = _deep_beam_apply_operation_to_stream(stream, operation)
        if stream is None:
            return None
    return stream


def _deep_beam_stream_from_record(
    record: dict[str, object],
    *,
    source_stream: bytes,
) -> tuple[bytes | None, tuple[IdatDeepBeamOperation, ...]]:
    operations = _deep_beam_record_operations(record)
    expected_hash = str(record.get("stream_hash") or "")
    if operations or expected_hash == _stream_state_key(source_stream):
        replayed = _deep_beam_replay_operations(source_stream, operations)
        if replayed is not None and (not expected_hash or _stream_state_key(replayed) == expected_hash):
            return replayed, operations
    try:
        return bytes.fromhex(str(record["stream"])), operations
    except (KeyError, TypeError, ValueError):
        return None, operations


def _deep_beam_candidate_to_record(
    candidate: IdatDeepBeamCandidate,
    *,
    source_hash: str,
    source_stream: bytes = b"",
    depth: int,
) -> dict[str, object]:
    stream_hash = _stream_state_key(candidate.stream)
    operations = tuple(candidate.operations)
    record = {
        "version": 3,
        "source_hash": source_hash,
        "stream_hash": stream_hash,
        "state_id": candidate.state_id,
        "parent_id": candidate.parent_id,
        "depth": int(depth),
        "operations": [_deep_beam_operation_to_json(operation) for operation in operations],
        "score": list(candidate.score),
        "status": candidate.after.status,
        "usable_scanlines": candidate.after.usable_scanlines,
        "decompressed": candidate.after.decompressed_size,
        "error_offset": candidate.after.error_offset,
    }
    replayed = _deep_beam_replay_operations(source_stream, operations) if source_stream else None
    if replayed is None or _stream_state_key(replayed) != stream_hash:
        record["stream"] = candidate.stream.hex()
    return record


def _compact_deep_beam_record(
    record: dict[str, object],
    *,
    source_hash: str,
    source_stream: bytes,
) -> tuple[dict[str, object], bool]:
    if record.get("source_hash") != source_hash:
        return record, False
    stream, operations = _deep_beam_stream_from_record(record, source_stream=source_stream)
    if stream is None:
        return record, False
    stream_hash = _stream_state_key(stream)
    expected_hash = str(record.get("stream_hash") or "")
    if expected_hash and expected_hash != stream_hash:
        return record, False

    compact = dict(record)
    compact["version"] = 3
    compact["stream_hash"] = stream_hash
    compact["operations"] = [_deep_beam_operation_to_json(operation) for operation in operations]
    had_stream = "stream" in compact
    compact.pop("stream", None)
    return compact, had_stream


def _compact_deep_beam_checkpoint_file(
    checkpoint_path: str,
    *,
    source_hash: str,
    source_stream: bytes,
) -> bool:
    if not checkpoint_path or not os.path.exists(checkpoint_path):
        return False
    tmp_path = _hidden_tmp_path(checkpoint_path)
    changed = False
    try:
        with open(checkpoint_path, "r", encoding="utf-8") as source, open(tmp_path, "w", encoding="utf-8") as target:
            for line in source:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    target.write(line)
                    continue
                if not isinstance(record, dict):
                    target.write(line)
                    continue
                compact, compacted = _compact_deep_beam_record(
                    record,
                    source_hash=source_hash,
                    source_stream=source_stream,
                )
                changed = changed or compacted
                target.write(json.dumps(compact, sort_keys=True) + "\n")
        if changed:
            os.replace(tmp_path, checkpoint_path)
        else:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        return changed
    except OSError:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        return False


def _append_deep_beam_checkpoint(
    checkpoint_path: str,
    candidate: IdatDeepBeamCandidate,
    *,
    source_hash: str,
    source_stream: bytes = b"",
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
                    _deep_beam_candidate_to_record(
                        candidate,
                        source_hash=source_hash,
                        source_stream=source_stream,
                        depth=depth,
                    ),
                    sort_keys=True,
                )
                + "\n"
            )
    except OSError:
        return


def _deep_beam_timing_record(timing: IdatDeepBeamRuntimeStats | None) -> dict[str, object]:
    if timing is None:
        return {}
    return {
        "gpu_setup_ms": round(float(timing.gpu_setup_ms), 3),
        "gpu_dispatch_ms": round(float(timing.gpu_dispatch_ms), 3),
        "gpu_hits": int(timing.gpu_hits),
        "gpu_shards": int(timing.gpu_shards),
        "gpu_skipped_resume": int(timing.gpu_skipped_resume),
        "cpu_batches": int(timing.cpu_batches),
        "cpu_validate_ms": round(float(timing.cpu_validate_ms), 3),
        "wall_ms": round(float(timing.wall_ms), 3),
    }


def _write_deep_beam_progress(
    progress_path: str,
    *,
    source_hash: str,
    tested: int,
    depth: int,
    max_depth: int,
    budget: int,
    hard_depth_limit: int | None = None,
    state_count: int,
    visited_count: int,
    best: IdatDeepBeamCandidate | None,
    workers: int,
    gpu_backend: str = "none",
    gpu_warning: str = "",
    gpu_done_shards: Iterable[str] = (),
    gpu_shard_size: int = DEEP_BEAM_DEFAULT_GPU_SHARD_SIZE,
    timing: IdatDeepBeamRuntimeStats | None = None,
    current_gpu_shard: str = "",
    interrupted: bool = False,
) -> None:
    if not progress_path:
        return
    try:
        directory = os.path.dirname(progress_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        payload = {
            "version": 2,
            "source_hash": source_hash,
            "tested_candidates": int(tested),
            "depth": int(depth),
            "max_depth": int(max_depth),
            "hard_depth_limit": int(hard_depth_limit if hard_depth_limit is not None else int(max_depth) + 1),
            "budget": int(budget),
            "state_count": int(state_count),
            "visited_count": int(visited_count),
            "workers": int(workers),
            "gpu_backend": str(gpu_backend or "none"),
            "gpu_warning": str(gpu_warning or ""),
            "gpu_done_shards": sorted(str(item) for item in gpu_done_shards),
            "gpu_shard_size": int(gpu_shard_size or 0),
            "gpu_stats": _deep_beam_timing_record(timing),
            "current_gpu_shard": str(current_gpu_shard or ""),
            "interrupted": bool(interrupted),
            "best_score": list(best.score) if best is not None else None,
            "best_status": best.after.status if best is not None else "",
            "timestamp": time.time(),
        }
        tmp_path = _hidden_tmp_path(progress_path)
        with open(tmp_path, "w", encoding="utf-8") as file:
            json.dump(payload, file, sort_keys=True)
        os.replace(tmp_path, progress_path)
    except OSError:
        return


def _load_deep_beam_progress(
    progress_path: str,
    *,
    source_hash: str,
    gpu_shard_size: int = DEEP_BEAM_DEFAULT_GPU_SHARD_SIZE,
) -> IdatDeepBeamProgressResume:
    if not progress_path or not os.path.exists(progress_path):
        return IdatDeepBeamProgressResume(set(), False)
    try:
        with open(progress_path, "r", encoding="utf-8") as file:
            record = json.load(file)
    except (OSError, json.JSONDecodeError):
        return IdatDeepBeamProgressResume(set(), False)
    if not isinstance(record, dict) or record.get("source_hash") != source_hash:
        return IdatDeepBeamProgressResume(set(), False)
    try:
        tested_candidates = max(0, int(record.get("tested_candidates", 0) or 0))
    except (TypeError, ValueError):
        tested_candidates = 0
    try:
        depth = max(0, int(record.get("depth", 0) or 0))
    except (TypeError, ValueError):
        depth = 0
    try:
        state_count = max(0, int(record.get("state_count", 0) or 0))
    except (TypeError, ValueError):
        state_count = 0
    try:
        visited_count = max(0, int(record.get("visited_count", 0) or 0))
    except (TypeError, ValueError):
        visited_count = 0
    stored_gpu_shard_size = record.get("gpu_shard_size")
    if stored_gpu_shard_size is not None:
        try:
            if int(stored_gpu_shard_size) != int(gpu_shard_size):
                return IdatDeepBeamProgressResume(
                    set(),
                    bool(record),
                    tested_candidates=tested_candidates,
                    depth=depth,
                    state_count=state_count,
                    visited_count=visited_count,
                )
        except (TypeError, ValueError):
            return IdatDeepBeamProgressResume(
                set(),
                bool(record),
                tested_candidates=tested_candidates,
                depth=depth,
                state_count=state_count,
                visited_count=visited_count,
            )
    done = record.get("gpu_done_shards", ())
    if not isinstance(done, list):
        done = ()
    return IdatDeepBeamProgressResume(
        {str(item) for item in done},
        bool(record),
        tested_candidates=tested_candidates,
        depth=depth,
        state_count=state_count,
        visited_count=visited_count,
    )


def deep_beam_resume_state(
    data: bytes,
    checkpoint_path: str = "",
    progress_path: str = "",
) -> IdatDeepBeamResumeState:
    try:
        _chunks, root_stream = _all_chunks_and_idat_stream(data)
    except png.PngFormatError as exc:
        return IdatDeepBeamResumeState(False, False, reason="source PNG is not parseable for IDAT resume: %s" % exc)
    if not root_stream:
        return IdatDeepBeamResumeState(False, False, reason="source IDAT stream is missing")

    source_hash = _stream_state_key(root_stream)
    if progress_path and os.path.exists(progress_path):
        try:
            with open(progress_path, "r", encoding="utf-8") as file:
                record = json.load(file)
        except (OSError, json.JSONDecodeError) as exc:
            return IdatDeepBeamResumeState(True, False, reason="deep-beam progress is unreadable: %s" % exc)
        if not isinstance(record, dict):
            return IdatDeepBeamResumeState(True, False, reason="deep-beam progress is not a JSON object")
        record_hash = str(record.get("source_hash") or "")
        matches = record_hash == source_hash
        return IdatDeepBeamResumeState(
            True,
            matches,
            interrupted=bool(record.get("interrupted", False)),
            tested=int(record.get("tested_candidates", 0) or 0),
            depth=int(record.get("depth", 0) or 0),
            reason="deep-beam progress %s source hash" % ("matches" if matches else "does not match"),
        )

    if checkpoint_path and os.path.exists(checkpoint_path):
        try:
            with open(checkpoint_path, "r", encoding="utf-8") as file:
                for line in file:
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(record, dict):
                        continue
                    record_hash = str(record.get("source_hash") or "")
                    matches = record_hash == source_hash
                    return IdatDeepBeamResumeState(
                        True,
                        matches,
                        tested=0,
                        depth=int(record.get("depth", 0) or 0),
                        reason="deep-beam checkpoint %s source hash" % ("matches" if matches else "does not match"),
                    )
        except OSError as exc:
            return IdatDeepBeamResumeState(True, False, reason="deep-beam checkpoint is unreadable: %s" % exc)
        return IdatDeepBeamResumeState(True, False, reason="deep-beam checkpoint has no readable records")

    return IdatDeepBeamResumeState(False, False, reason="no deep-beam checkpoint/progress")


def _load_deep_beam_checkpoint(
    checkpoint_path: str,
    *,
    source_hash: str,
    source_stream: bytes,
    chunks: tuple[png.PngChunk, ...],
    before: idat.IdatStreamAnalysis,
    original_idat_count: int,
    candidate_limit: int,
    max_operation_depth: int | None = None,
) -> tuple[list[IdatDeepBeamCandidate], set[str], int, int]:
    if not checkpoint_path or not os.path.exists(checkpoint_path):
        return [], set(), 1, 0
    recent_records: list[dict[str, object]] = []
    visited: set[str] = set()
    next_state_id = 1
    limit = max(1, int(candidate_limit))
    max_depth = None if max_operation_depth is None else max(0, int(max_operation_depth))
    matched_records = 0
    try:
        with open(checkpoint_path, "r", encoding="utf-8") as file:
            for line in file:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(record, dict):
                    continue
                if record.get("source_hash") != source_hash:
                    continue
                matched_records += 1
                stream_hash = str(record.get("stream_hash") or "")
                if stream_hash and stream_hash in visited:
                    continue
                if stream_hash:
                    visited.add(stream_hash)
                try:
                    next_state_id = max(next_state_id, int(record.get("state_id", 0)) + 1)
                except (TypeError, ValueError):
                    pass
                operations = _deep_beam_record_operations(record)
                if max_depth is not None and len(operations) > max_depth:
                    continue
                recent_records.append(record)
                if len(recent_records) > limit:
                    recent_records.pop(0)
    except OSError:
        return [], set(), 1, 0

    candidates: list[IdatDeepBeamCandidate] = []
    for record in recent_records:
        stream, operations = _deep_beam_stream_from_record(record, source_stream=source_stream)
        if stream is None:
            continue
        data = _rebuild_with_single_idat_stream(chunks, stream)
        analysis = idat.analyze_idat_stream(
            data,
            crc_provenance="rebuilt_by_chunklate",
            source_kind="candidate_from_checkpoint",
        )
        try:
            state_id = int(record.get("state_id", next_state_id))
            parent_id = None if record.get("parent_id") is None else int(record.get("parent_id"))
        except (TypeError, ValueError):
            state_id = next_state_id
            parent_id = None
        candidates.append(
            IdatDeepBeamCandidate(
                data=data,
                stream=stream,
                operations=operations,
                before=before,
                after=analysis,
                state_id=state_id,
                parent_id=parent_id,
                source_offsets=tuple(operation.stream_offset for operation in operations),
                score=_deep_beam_score(
                    analysis,
                    stream,
                    len(operations),
                    data=data,
                    original_idat_count=original_idat_count,
                ),
            )
        )
    return candidates, visited, next_state_id, matched_records


def _deep_beam_progress_path_from_checkpoint(checkpoint_path: str) -> str:
    if not checkpoint_path:
        return ""
    if checkpoint_path.endswith(".checkpoint.jsonl"):
        return checkpoint_path[: -len(".checkpoint.jsonl")] + ".progress.json"
    return checkpoint_path + ".progress.json"


def idat_convoy_model_payload(
    original_data: bytes,
    fixed_data: bytes,
    chain_analysis: Any,
) -> dict[str, object]:
    try:
        chunks, convoy_stream = _all_chunks_and_idat_stream(fixed_data)
    except png.PngFormatError:
        chunks, convoy_stream = (), b""
    idat_chunks = tuple(chunk for chunk in chunks if chunk.chunk_type == b"IDAT")
    idat_index_by_offset = {chunk.offset: index for index, chunk in enumerate(idat_chunks)}
    byte_repairs: list[dict[str, object]] = []
    patch_records: list[dict[str, object]] = []
    for patch in tuple(getattr(chain_analysis, "patches", ()) or ()):
        header_offset = int(getattr(patch, "header_offset", 0) or 0)
        old_length = int(getattr(patch, "old_length", 0) or 0)
        new_length = int(getattr(patch, "new_length", 0) or 0)
        old_type = bytes(getattr(patch, "old_type", b"") or b"")
        new_type = bytes(getattr(patch, "new_type", b"IDAT") or b"IDAT")
        idat_index = idat_index_by_offset.get(header_offset)
        patch_records.append(
            {
                "header_offset": header_offset,
                "idat_index": idat_index,
                "idat_class_mod8": None if idat_index is None else idat_index % 8,
                "old_length": old_length,
                "new_length": new_length,
                "old_type_hex": old_type.hex(),
                "new_type_hex": new_type.hex(),
            }
        )
        old_length_bytes = old_length.to_bytes(4, "big", signed=False)
        new_length_bytes = new_length.to_bytes(4, "big", signed=False)
        for index, (old, new) in enumerate(zip(old_length_bytes, new_length_bytes)):
            if old == new:
                continue
            byte_repairs.append(
                {
                    "file_offset": header_offset + index,
                    "header_offset": header_offset,
                    "field": "length",
                    "field_index": index,
                    "idat_index": idat_index,
                    "idat_class_mod8": None if idat_index is None else idat_index % 8,
                    "old": old,
                    "new": new,
                    "xor": old ^ new,
                    "delta": (new - old) & 0xFF,
                }
            )
        for index, (old, new) in enumerate(zip(old_type, new_type)):
            if old == new:
                continue
            byte_repairs.append(
                {
                    "file_offset": header_offset + 4 + index,
                    "header_offset": header_offset,
                    "field": "type",
                    "field_index": index,
                    "idat_index": idat_index,
                    "idat_class_mod8": None if idat_index is None else idat_index % 8,
                    "old": old,
                    "new": new,
                    "xor": old ^ new,
                    "delta": (new - old) & 0xFF,
                }
            )

    xors = sorted({int(item["xor"]) for item in byte_repairs if int(item["xor"])})
    deltas = sorted({int(item["delta"]) for item in byte_repairs if int(item["delta"])})
    idat_classes = sorted(
        {
            int(item["idat_class_mod8"])
            for item in byte_repairs
            if item.get("idat_class_mod8") is not None
        }
    )
    return {
        "version": 1,
        "original_hash": hashlib.blake2b(original_data, digest_size=16).hexdigest(),
        "fixed_hash": hashlib.blake2b(fixed_data, digest_size=16).hexdigest(),
        "convoy_stream_hash": _stream_state_key(convoy_stream),
        "chunk_count": len(chunks),
        "idat_count": len(idat_chunks),
        "expected_idat_length": getattr(chain_analysis, "expected_length", None),
        "iend_offset": getattr(chain_analysis, "iend_offset", None),
        "idat_chunks": [
            {
                "index": index,
                "offset": chunk.offset,
                "length": chunk.length,
                "crc": chunk.crc,
                "computed_crc": chunk.computed_crc,
                "crc_ok": chunk.crc_ok,
            }
            for index, chunk in enumerate(idat_chunks)
        ],
        "patches": patch_records,
        "byte_repairs": byte_repairs,
        "xors": xors,
        "deltas": deltas,
        "idat_classes_mod8": idat_classes,
    }


def write_idat_convoy_model(
    path: str,
    original_data: bytes,
    fixed_data: bytes,
    chain_analysis: Any,
) -> bool:
    if not path:
        return False
    payload = idat_convoy_model_payload(original_data, fixed_data, chain_analysis)
    encoded = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    try:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        if os.path.exists(path):
            try:
                with open(path, "rb") as existing:
                    if existing.read() == encoded:
                        return False
            except OSError:
                pass
        tmp_path = _hidden_tmp_path(path)
        with open(tmp_path, "wb") as file:
            file.write(encoded)
        os.replace(tmp_path, path)
        return True
    except OSError:
        return False


def _load_idat_convoy_model(path: str) -> tuple[dict[str, object] | None, str]:
    if not path:
        return None, "convoy model path is empty"
    if not os.path.exists(path):
        return None, "convoy model is missing"
    try:
        with open(path, "r", encoding="utf-8") as file:
            payload = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        return None, "convoy model is unreadable: %s" % exc
    if not isinstance(payload, dict):
        return None, "convoy model is not a JSON object"
    return payload, ""


def periodic_model_progress_state(data: bytes, progress_path: str = "") -> IdatPeriodicProgressState:
    if not progress_path or not os.path.exists(progress_path):
        return IdatPeriodicProgressState(False, False, reason="no periodic model progress")
    try:
        _chunks, stream = _all_chunks_and_idat_stream(data)
    except png.PngFormatError as exc:
        return IdatPeriodicProgressState(True, False, reason="source PNG is not parseable: %s" % exc)
    source_hash = _stream_state_key(stream)
    try:
        with open(progress_path, "r", encoding="utf-8") as file:
            payload = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        return IdatPeriodicProgressState(True, False, reason="periodic model progress is unreadable: %s" % exc)
    if not isinstance(payload, dict):
        return IdatPeriodicProgressState(True, False, reason="periodic model progress is not a JSON object")
    matches = str(payload.get("source_hash") or "") == source_hash
    return IdatPeriodicProgressState(
        True,
        matches,
        exhausted=bool(payload.get("exhausted", False)),
        tested=int(payload.get("tested_candidates", 0) or 0),
        budget=int(payload.get("budget", 0) or 0),
        reason="periodic model progress %s source hash" % ("matches" if matches else "does not match"),
    )


def _frontier_progress_state(data: bytes, progress_path: str = "", *, label: str = "frontier") -> IdatFrontierProgressState:
    if not progress_path or not os.path.exists(progress_path):
        return IdatFrontierProgressState(False, False, reason="no %s progress" % label)
    try:
        _chunks, stream = _all_chunks_and_idat_stream(data)
    except png.PngFormatError as exc:
        return IdatFrontierProgressState(True, False, reason="source PNG is not parseable: %s" % exc)
    source_hash = _stream_state_key(stream)
    try:
        with open(progress_path, "r", encoding="utf-8") as file:
            payload = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        return IdatFrontierProgressState(True, False, reason="%s progress is unreadable: %s" % (label, exc))
    if not isinstance(payload, dict):
        return IdatFrontierProgressState(True, False, reason="%s progress is not a JSON object" % label)
    matches = str(payload.get("source_hash") or "") == source_hash
    return IdatFrontierProgressState(
        True,
        matches,
        exhausted=bool(payload.get("exhausted", False)),
        tested=int(payload.get("tested_candidates", 0) or 0),
        budget=int(payload.get("budget", 0) or 0),
        reason=str(payload.get("reason") or "%s progress %s source hash" % (label, "matches" if matches else "does not match")),
    )


def frontier_progress_route_version(progress_path: str = "") -> int:
    if not progress_path or not os.path.exists(progress_path):
        return 0
    try:
        with open(progress_path, "r", encoding="utf-8") as file:
            payload = json.load(file)
    except (OSError, json.JSONDecodeError, TypeError):
        return 0
    if not isinstance(payload, dict):
        return 0
    try:
        return int(payload.get("route_version", 0) or 0)
    except (TypeError, ValueError):
        return 0


def huffman_oracle_progress_state(data: bytes, progress_path: str = "") -> IdatFrontierProgressState:
    return _frontier_progress_state(data, progress_path, label="huffman oracle")


def crc_periodic_progress_state(data: bytes, progress_path: str = "") -> IdatFrontierProgressState:
    return _frontier_progress_state(data, progress_path, label="crc-periodic")


def huffman_kraft_progress_state(data: bytes, progress_path: str = "") -> IdatFrontierProgressState:
    return _frontier_progress_state(data, progress_path, label="huffman kraft")


def first_filter_literal_progress_state(data: bytes, progress_path: str = "") -> IdatFrontierProgressState:
    return _frontier_progress_state(data, progress_path, label="first-filter-literal")


def kraft_backref_progress_state(data: bytes, progress_path: str = "") -> IdatFrontierProgressState:
    return _frontier_progress_state(data, progress_path, label="kraft-backref")


def global_crc_residue_progress_state(data: bytes, progress_path: str = "") -> IdatFrontierProgressState:
    return _frontier_progress_state(data, progress_path, label="global-crc-residue")


def affine_corruption_progress_state(data: bytes, progress_path: str = "") -> IdatFrontierProgressState:
    return _frontier_progress_state(data, progress_path, label="affine-corruption")


def deflate_salvage_progress_state(data: bytes, progress_path: str = "") -> IdatFrontierProgressState:
    return _frontier_progress_state(data, progress_path, label="deflate-salvage")


def _write_periodic_model_progress(
    progress_path: str,
    *,
    source_hash: str,
    model_path: str,
    tested: int,
    budget: int,
    best: IdatDeepBeamCandidate | None,
    top_count: int,
    exhausted: bool,
    reason: str,
) -> None:
    if not progress_path:
        return
    try:
        directory = os.path.dirname(progress_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        payload = {
            "version": 1,
            "source_hash": source_hash,
            "model_path": model_path,
            "tested_candidates": int(tested),
            "budget": int(budget),
            "exhausted": bool(exhausted),
            "best_score": list(best.score) if best is not None else None,
            "top_count": int(top_count),
            "reason": reason,
            "timestamp": time.time(),
        }
        tmp_path = _hidden_tmp_path(progress_path)
        with open(tmp_path, "w", encoding="utf-8") as file:
            json.dump(payload, file, sort_keys=True)
        os.replace(tmp_path, progress_path)
    except OSError:
        return


def _write_frontier_progress(
    progress_path: str,
    *,
    source_hash: str,
    tested: int,
    budget: int,
    best: IdatDeepBeamCandidate | None,
    top_count: int,
    exhausted: bool,
    reason: str,
    strategy: str,
    extra: dict[str, object] | None = None,
) -> None:
    if not progress_path:
        return
    try:
        directory = os.path.dirname(progress_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        payload = {
            "version": 1,
            "source_hash": source_hash,
            "strategy": strategy,
            "tested_candidates": int(tested),
            "budget": int(budget),
            "exhausted": bool(exhausted),
            "best_score": list(best.score) if best is not None else None,
            "top_count": int(top_count),
            "reason": reason,
            "timestamp": time.time(),
        }
        if extra:
            payload.update(extra)
        tmp_path = _hidden_tmp_path(progress_path)
        with open(tmp_path, "w", encoding="utf-8") as file:
            json.dump(payload, file, sort_keys=True)
        os.replace(tmp_path, progress_path)
    except OSError:
        return


def _append_periodic_model_checkpoint(
    checkpoint_path: str,
    candidate: IdatDeepBeamCandidate,
    *,
    source_hash: str,
    source_stream: bytes,
) -> None:
    _append_deep_beam_checkpoint(
        checkpoint_path,
        candidate,
        source_hash=source_hash,
        source_stream=source_stream,
        depth=len(candidate.operations),
    )


def _append_frontier_checkpoint(
    checkpoint_path: str,
    candidate: IdatDeepBeamCandidate,
    *,
    source_hash: str,
    source_stream: bytes,
) -> None:
    _append_deep_beam_checkpoint(
        checkpoint_path,
        candidate,
        source_hash=source_hash,
        source_stream=source_stream,
        depth=len(candidate.operations),
    )


def _periodic_model_ints(model: dict[str, object], key: str) -> tuple[int, ...]:
    values = model.get(key, ())
    if not isinstance(values, list | tuple):
        return ()
    normalized: list[int] = []
    for value in values:
        try:
            integer = int(value) & 0xFF
        except (TypeError, ValueError):
            continue
        if integer:
            normalized.append(integer)
    return tuple(dict.fromkeys(normalized))


def _periodic_model_offsets(diagnostic: IdatLocalDeflateDiagnostic | None, stream_size: int) -> tuple[int, ...]:
    if diagnostic is None:
        base = list(DEEP_BEAM_FOCUS_OFFSETS)
        base.extend(range(0, min(stream_size, 0x120)))
        return tuple(dict.fromkeys(offset for offset in base if 0 <= offset < stream_size))
    offsets = list(
        _deep_beam_offsets(
            diagnostic,
            max_offsets=min(512, max(1, stream_size)),
            widened_limit=0x120,
        )
    )
    for start, end in DEEP_BEAM_FOCUS_BIT_RANGES:
        offsets.extend(bit // 8 for bit in range(start, end))
    return tuple(dict.fromkeys(offset for offset in offsets if 0 <= offset < stream_size))


def _periodic_operation_pool(stream: bytes, model: dict[str, object], offsets: tuple[int, ...]) -> tuple[IdatDeepBeamOperation, ...]:
    xors = sorted(_periodic_model_ints(model, "xors"), key=lambda value: (int(value).bit_count(), int(value)))
    deltas = _periodic_model_ints(model, "deltas")
    operations: list[IdatDeepBeamOperation] = []
    seen: set[tuple[object, ...]] = set()

    def add(operation: IdatDeepBeamOperation) -> None:
        key = (
            operation.kind,
            int(operation.stream_offset),
            operation.old_bytes,
            operation.new_bytes,
            operation.bit_offsets,
        )
        if key in seen:
            return
        seen.add(key)
        operations.append(operation)

    for offset in offsets:
        old = stream[offset]
        for xor in xors:
            if xor.bit_count() <= 4:
                bits = tuple(offset * 8 + bit for bit in range(8) if xor & (1 << bit))
                add(
                    IdatDeepBeamOperation(
                        "periodic-bit-flip",
                        offset,
                        bytes((old,)),
                        bytes((old ^ xor,)),
                        bits,
                    )
                )
            add(
                IdatDeepBeamOperation(
                    "periodic-replace-xor",
                    offset,
                    bytes((old,)),
                    bytes((old ^ xor,)),
                )
            )
        for delta in deltas:
            for signed_delta in (delta, (-delta) & 0xFF):
                add(
                    IdatDeepBeamOperation(
                        "periodic-replace-delta",
                        offset,
                        bytes((old,)),
                        bytes(((old + signed_delta) & 0xFF,)),
                    )
                )
        add(IdatDeepBeamOperation("periodic-remove", offset, bytes((old,)), b""))
        for value in DEEP_BEAM_COMMON_BYTES:
            add(IdatDeepBeamOperation("periodic-insert", offset, b"", bytes((value,))))
    return tuple(operations)


def _periodic_candidate_from_operation(
    parent: IdatDeepBeamCandidate,
    operation: IdatDeepBeamOperation,
    *,
    chunks: tuple[png.PngChunk, ...],
    before: idat.IdatStreamAnalysis,
    state_id: int,
    original_idat_count: int,
) -> IdatDeepBeamCandidate | None:
    stream = _deep_beam_apply_operation_to_stream(parent.stream, operation)
    if stream is None:
        return None
    data = _rebuild_with_single_idat_stream(chunks, stream)
    analysis = idat.analyze_idat_stream(
        data,
        source_kind="candidate_from_periodic_model",
        crc_provenance="rebuilt_by_chunklate",
    )
    operations = parent.operations + (operation,)
    return IdatDeepBeamCandidate(
        data=data,
        stream=stream,
        operations=operations,
        before=before,
        after=analysis,
        state_id=state_id,
        parent_id=parent.state_id,
        source_offsets=parent.source_offsets + (operation.stream_offset,),
        score=_deep_beam_score(
            analysis,
            stream,
            len(operations),
            data=data,
            original_idat_count=original_idat_count,
        ),
    )


def _frontier_candidate_from_stream(
    parent: IdatDeepBeamCandidate,
    stream: bytes,
    operation: IdatDeepBeamOperation,
    *,
    chunks: tuple[png.PngChunk, ...],
    before: idat.IdatStreamAnalysis,
    state_id: int,
    original_idat_count: int,
    source_kind: str,
) -> IdatDeepBeamCandidate | None:
    if not stream or stream == parent.stream:
        return None
    data = _rebuild_with_single_idat_stream(chunks, stream)
    analysis = idat.analyze_idat_stream(
        data,
        source_kind=source_kind,
        crc_provenance="rebuilt_by_chunklate",
    )
    operations = parent.operations + (operation,)
    return IdatDeepBeamCandidate(
        data=data,
        stream=stream,
        operations=operations,
        before=before,
        after=analysis,
        state_id=state_id,
        parent_id=parent.state_id,
        source_offsets=parent.source_offsets + (operation.stream_offset,),
        score=_deep_beam_score(
            analysis,
            stream,
            len(operations),
            data=data,
            original_idat_count=original_idat_count,
        ),
    )


def _frontier_root_candidate(
    *,
    data: bytes,
    stream: bytes,
    before: idat.IdatStreamAnalysis,
    original_idat_count: int,
) -> IdatDeepBeamCandidate:
    return IdatDeepBeamCandidate(
        data=data,
        stream=stream,
        operations=(),
        before=before,
        after=before,
        state_id=0,
        parent_id=None,
        source_offsets=(),
        score=_deep_beam_score(
            before,
            stream,
            0,
            data=data,
            original_idat_count=original_idat_count,
        ),
    )


def _huffman_oracle_rank(stream: bytes, analysis: idat.IdatStreamAnalysis) -> tuple[int, ...]:
    oracle = raw_png_oracle_decision(stream, analysis)
    header_rank, has_eob, literal_debt, distance_debt, length_count, bit_offset = _deep_beam_huffman_score(stream)
    return (
        int(oracle.raw_score.first_filter_rank),
        int(oracle.raw_score.valid_filter_rows),
        int(oracle.raw_score.alpha_rank),
        int(analysis.usable_scanlines),
        int(analysis.complete_scanlines),
        int(header_rank),
        int(has_eob),
        -int(literal_debt),
        -int(distance_debt),
        int(length_count),
        int(analysis.decompressed_size),
        int(analysis.error_offset if analysis.error_offset is not None else -1),
        int(bit_offset),
    )


def _huffman_oracle_accepts(parent: IdatDeepBeamCandidate, candidate: IdatDeepBeamCandidate) -> bool:
    if candidate.after.complete or candidate.after.usable_scanlines > parent.after.usable_scanlines:
        return True
    return _huffman_oracle_rank(candidate.stream, candidate.after) > _huffman_oracle_rank(parent.stream, parent.after)


def _candidate_png_plausible(candidate: IdatDeepBeamCandidate) -> bool:
    return raw_png_oracle_decision(candidate.stream, candidate.after).png_plausible


def _candidate_dynamic_header_valid(candidate: IdatDeepBeamCandidate) -> bool:
    try:
        header = deflate_header.analyze_deflate_header(candidate.stream)
    except Exception:
        return False
    return bool(header.ok and header.btype == 2)


def _frontier_best_candidate(
    before: idat.IdatStreamAnalysis,
    candidates: Iterable[IdatDeepBeamCandidate],
) -> IdatDeepBeamCandidate | None:
    best: IdatDeepBeamCandidate | None = None
    for candidate in candidates:
        if not is_material_improvement(before, candidate.after):
            continue
        if best is None or candidate.score > best.score:
            best = candidate
    return best


def _load_frontier_candidates_for_progress(
    data: bytes,
    checkpoint_path: str,
    *,
    top_candidates: int,
    max_operation_depth: int | None,
) -> tuple[
    idat.IdatStreamAnalysis,
    tuple[png.PngChunk, ...],
    bytes,
    str,
    int,
    tuple[IdatDeepBeamCandidate, ...],
]:
    before = idat.analyze_idat_stream(data)
    chunks, root_stream = _all_chunks_and_idat_stream(data)
    source_hash = _stream_state_key(root_stream)
    original_idat_count = sum(1 for chunk in chunks if chunk.chunk_type == b"IDAT")
    load_limit = max(1, min(5000, int(top_candidates) * 64))
    checkpoint_candidates, _visited, _next_state_id, _records = _load_deep_beam_checkpoint(
        checkpoint_path,
        source_hash=source_hash,
        source_stream=root_stream,
        chunks=chunks,
        before=before,
        original_idat_count=original_idat_count,
        candidate_limit=load_limit,
        max_operation_depth=max_operation_depth,
    )
    return (
        before,
        chunks,
        root_stream,
        source_hash,
        original_idat_count,
        _deep_beam_ranked_unique(checkpoint_candidates, limit=top_candidates),
    )


def _huffman_oracle_subprobes(
    data: bytes,
    *,
    budget_left: int,
) -> tuple[tuple[tuple[IdatDeflateCandidate | None, str], ...], int]:
    if budget_left <= 0:
        return (), 0
    probes: list[tuple[IdatDeflateProbeResult, str]] = []
    remaining = int(budget_left)
    tested = 0

    def run(label: str, call: Callable[[int], IdatDeflateProbeResult], cap: int) -> None:
        nonlocal remaining, tested
        if remaining <= 0:
            return
        probe = call(min(cap, remaining))
        probes.append((probe, label))
        consumed = max(0, int(probe.tested_candidates))
        tested += consumed
        remaining = max(0, remaining - consumed)

    run(
        "huffman-oracle-bitshift",
        lambda budget: probe_dynamic_huffman_bitshift_candidates(data, budget=budget),
        4096,
    )
    run(
        "huffman-oracle-header",
        lambda budget: probe_dynamic_huffman_header_candidates(data, budget=budget, max_bits=192, max_bit_flips=2),
        32768,
    )
    run(
        "huffman-oracle-semantic",
        lambda budget: probe_dynamic_huffman_semantic_candidates(data, budget=budget, max_tokens=96),
        12000,
    )
    run(
        "huffman-oracle-alphabet",
        lambda budget: probe_dynamic_huffman_alphabet_candidates(data, budget=budget, max_fields=12),
        8192,
    )
    run(
        "huffman-oracle-crc-guided",
        lambda budget: probe_dynamic_huffman_crc_guided_candidates(
            data,
            budget=budget,
            max_group_bits=24,
            max_solutions_per_group=32,
        ),
        8192,
    )

    items: list[tuple[IdatDeflateCandidate | None, str]] = []
    for probe, label in probes:
        items.append((probe.best, label))
        if probe.diagnostic_best is not probe.best:
            items.append((probe.diagnostic_best, "%s-diagnostic" % label))
    return tuple(items), tested


def _huffman_kraft_metrics(stream: bytes) -> tuple[int, int, int, int, int, int, int]:
    trace = deflate_header.trace_dynamic_header(stream)
    literal_left, literal_debt, literal_used, _literal_bits = _huffman_balance(trace.literal_lengths)
    distance_left, distance_debt, distance_used, _distance_bits = _huffman_balance(trace.distance_lengths)
    has_eob = 1 if len(trace.literal_lengths) > 256 and trace.literal_lengths[256] > 0 else 0
    literal_complete = 1 if literal_left == 0 and not trace.literal_error else 0
    distance_complete = 1 if distance_left == 0 and not trace.distance_error else 0
    return (
        int(literal_debt),
        int(distance_debt),
        int(has_eob),
        int(literal_complete),
        int(distance_complete),
        int(literal_used),
        int(distance_used),
    )


def _huffman_kraft_rank(stream: bytes, analysis: idat.IdatStreamAnalysis) -> tuple[int, ...]:
    literal_debt, distance_debt, has_eob, literal_complete, distance_complete, literal_used, distance_used = _huffman_kraft_metrics(stream)
    oracle = raw_png_oracle_decision(stream, analysis, max_output=max(1, min(8192, int(analysis.scanline_size or 8192))))
    header_rank, _eob, _lit, _dist, length_count, bit_offset = _deep_beam_huffman_score(stream)
    return (
        int(analysis.usable_scanlines),
        int(analysis.complete_scanlines),
        int(literal_complete and distance_complete),
        int(oracle.raw_score.first_filter_rank),
        int(oracle.raw_score.valid_filter_rows),
        int(oracle.raw_score.alpha_rank),
        int(header_rank),
        int(has_eob),
        -int(literal_debt),
        -int(distance_debt),
        int(length_count),
        int(literal_used + distance_used),
        int(analysis.decompressed_size),
        int(analysis.error_offset if analysis.error_offset is not None else -1),
        int(bit_offset),
    )


def _huffman_kraft_ranked_unique(
    candidates: Iterable[IdatDeepBeamCandidate],
    *,
    limit: int,
) -> tuple[IdatDeepBeamCandidate, ...]:
    unique: dict[str, IdatDeepBeamCandidate] = {}
    for candidate in candidates:
        key = _stream_state_key(candidate.stream)
        current = unique.get(key)
        if current is None or _huffman_kraft_rank(candidate.stream, candidate.after) > _huffman_kraft_rank(current.stream, current.after):
            unique[key] = candidate
    ranked = sorted(
        unique.values(),
        key=lambda item: _huffman_kraft_rank(item.stream, item.after),
        reverse=True,
    )
    return tuple(ranked[: max(1, int(limit))])


def _huffman_kraft_accepts(parent: IdatDeepBeamCandidate, candidate: IdatDeepBeamCandidate) -> bool:
    parent_metrics = _huffman_kraft_metrics(parent.stream)
    candidate_metrics = _huffman_kraft_metrics(candidate.stream)
    parent_literal_debt, parent_distance_debt, parent_eob, parent_literal_complete, parent_distance_complete, _plu, _pdu = parent_metrics
    literal_debt, distance_debt, has_eob, literal_complete, distance_complete, _lu, _du = candidate_metrics
    if literal_complete and distance_complete:
        oracle = raw_png_oracle_decision(candidate.stream, candidate.after, max_output=1)
        if oracle.raw_prefix.raw and not oracle.first_filter_ok:
            return False
        return True
    if literal_debt < parent_literal_debt or distance_debt < parent_distance_debt:
        return True
    if has_eob and not parent_eob:
        return True
    if literal_complete > parent_literal_complete or distance_complete > parent_distance_complete:
        return True
    return _huffman_kraft_rank(candidate.stream, candidate.after) > _huffman_kraft_rank(parent.stream, parent.after)


def _huffman_kraft_token_operations(
    stream: bytes,
    trace: deflate_header.DynamicHeaderTrace,
    *,
    max_tokens: int,
) -> tuple[IdatDeepBeamOperation, ...]:
    try:
        symbol_codes = _dynamic_code_length_symbol_codes(trace)
    except Exception:
        return ()
    operations: list[IdatDeepBeamOperation] = []
    seen: set[tuple[int, int, tuple[int, ...]]] = set()
    tokens = _dynamic_semantic_priority_tokens(trace, limit=max_tokens)
    for token in tokens:
        bit_start = int(token.bit_start)
        bit_end = _dynamic_length_token_bit_end(token)
        old_context = _stream_bit_range_to_bytes(stream, bit_start, bit_end)
        for replacement_bits in _dynamic_semantic_token_options(token, symbol_codes):
            key = (bit_start, bit_end, tuple(int(bit) for bit in replacement_bits))
            if key in seen:
                continue
            seen.add(key)
            if len(replacement_bits) > 48:
                continue
            operations.append(
                IdatDeepBeamOperation(
                    "huffman-kraft-token",
                    bit_start // 8,
                    old_context,
                    bytes(int(bit) & 1 for bit in replacement_bits),
                    tuple(range(bit_start, bit_end)),
                )
            )
    return tuple(operations)


def _huffman_kraft_candidate_from_operation(
    parent: IdatDeepBeamCandidate,
    operation: IdatDeepBeamOperation,
    *,
    chunks: tuple[png.PngChunk, ...],
    before: idat.IdatStreamAnalysis,
    state_id: int,
    original_idat_count: int,
) -> IdatDeepBeamCandidate | None:
    if not operation.bit_offsets:
        return None
    replacement_bits = tuple(int(value) & 1 for value in operation.new_bytes)
    bit_start = min(operation.bit_offsets)
    bit_end = max(operation.bit_offsets) + 1
    stream = _replace_stream_bits_preserve_length(parent.stream, bit_start, bit_end, replacement_bits)
    if stream is None:
        return None
    return _frontier_candidate_from_stream(
        parent,
        stream,
        operation,
        chunks=chunks,
        before=before,
        state_id=state_id,
        original_idat_count=original_idat_count,
        source_kind="candidate_from_huffman_kraft",
    )


HuffmanKraftCompactOperation = tuple[int, int, int, tuple[int, ...], int, bytes, bytes]


def _huffman_kraft_compact_operation(
    state_id: int,
    operation: IdatDeepBeamOperation,
) -> HuffmanKraftCompactOperation | None:
    if not operation.bit_offsets:
        return None
    bit_start = min(operation.bit_offsets)
    bit_end = max(operation.bit_offsets) + 1
    return (
        int(state_id),
        int(bit_start),
        int(bit_end),
        tuple(int(value) & 1 for value in operation.new_bytes),
        int(operation.stream_offset),
        bytes(operation.old_bytes),
        bytes(operation.new_bytes),
    )


def _huffman_kraft_operation_from_compact(compact: HuffmanKraftCompactOperation) -> IdatDeepBeamOperation:
    _state_id, bit_start, bit_end, _replacement_bits, stream_offset, old_bytes, new_bytes = compact
    return IdatDeepBeamOperation(
        "huffman-kraft-token",
        int(stream_offset),
        bytes(old_bytes),
        bytes(new_bytes),
        tuple(range(int(bit_start), int(bit_end))),
    )


def _huffman_kraft_apply_compact_operation(
    stream: bytes,
    compact: HuffmanKraftCompactOperation,
) -> bytes | None:
    _state_id, bit_start, bit_end, replacement_bits, _stream_offset, _old_bytes, _new_bytes = compact
    return _replace_stream_bits_preserve_length(
        stream,
        int(bit_start),
        int(bit_end),
        tuple(int(value) & 1 for value in replacement_bits),
    )


def _huffman_kraft_prefilter_accepts_metrics(
    parent_metrics: tuple[int, int, int, int, int, int, int],
    stream: bytes,
) -> bool:
    literal_debt, distance_debt, has_eob, literal_complete, distance_complete, _lu, _du = _huffman_kraft_metrics(stream)
    parent_literal_debt, parent_distance_debt, parent_eob, parent_literal_complete, parent_distance_complete, _plu, _pdu = parent_metrics
    if literal_complete and distance_complete:
        return True
    if literal_debt < parent_literal_debt or distance_debt < parent_distance_debt:
        return True
    if has_eob and not parent_eob:
        return True
    if literal_complete > parent_literal_complete or distance_complete > parent_distance_complete:
        return True
    return False


def _huffman_kraft_candidate_from_compact_operation(
    parent_stream: bytes,
    parent_operations: tuple[IdatDeepBeamOperation, ...],
    parent_state_id: int,
    parent_source_offsets: tuple[int, ...],
    compact: HuffmanKraftCompactOperation,
    *,
    chunks: tuple[png.PngChunk, ...],
    before: idat.IdatStreamAnalysis,
    original_idat_count: int,
) -> IdatDeepBeamCandidate | None:
    state_id, _bit_start, _bit_end, _replacement_bits, _stream_offset, _old_bytes, _new_bytes = compact
    stream = _huffman_kraft_apply_compact_operation(parent_stream, compact)
    if stream is None:
        return None
    parent = IdatDeepBeamCandidate(
        data=b"",
        stream=parent_stream,
        operations=parent_operations,
        before=before,
        after=before,
        state_id=int(parent_state_id),
        parent_id=None,
        source_offsets=parent_source_offsets,
        score=(),
    )
    operation = _huffman_kraft_operation_from_compact(compact)
    return _frontier_candidate_from_stream(
        parent,
        stream,
        operation,
        chunks=chunks,
        before=before,
        state_id=int(state_id),
        original_idat_count=original_idat_count,
        source_kind="candidate_from_huffman_kraft",
    )


def _huffman_kraft_apply_compact_operation_batch(
    args: tuple[
        bytes,
        tuple[IdatDeepBeamOperation, ...],
        int,
        tuple[int, ...],
        tuple[HuffmanKraftCompactOperation, ...],
        tuple[png.PngChunk, ...],
        idat.IdatStreamAnalysis,
        int,
    ],
) -> tuple[tuple[IdatDeepBeamCandidate, ...], int]:
    parent_stream, parent_operations, parent_state_id, parent_source_offsets, compact_operations, chunks, before, original_idat_count = args
    parent_metrics = _huffman_kraft_metrics(parent_stream)
    candidates: list[IdatDeepBeamCandidate] = []
    prefilter_hits = 0
    for compact in compact_operations:
        stream = _huffman_kraft_apply_compact_operation(parent_stream, compact)
        if stream is None:
            continue
        if not _huffman_kraft_prefilter_accepts_metrics(parent_metrics, stream):
            continue
        prefilter_hits += 1
        candidate = _huffman_kraft_candidate_from_compact_operation(
            parent_stream,
            parent_operations,
            parent_state_id,
            parent_source_offsets,
            compact,
            chunks=chunks,
            before=before,
            original_idat_count=original_idat_count,
        )
        if candidate is not None:
            candidates.append(candidate)
    return tuple(candidates), prefilter_hits


def _huffman_kraft_operation_batches(
    compact_operations: tuple[HuffmanKraftCompactOperation, ...],
    *,
    workers: int,
    cpu_batch_size: int | None = None,
) -> tuple[tuple[HuffmanKraftCompactOperation, ...], ...]:
    if not compact_operations:
        return ()
    batch_size = _deep_beam_cpu_batch_size(
        len(compact_operations),
        max(1, int(workers)),
        int(cpu_batch_size or DEEP_BEAM_DEFAULT_CPU_BATCH_SIZE),
    )
    return tuple(
        tuple(compact_operations[index : index + batch_size])
        for index in range(0, len(compact_operations), batch_size)
    )


def _huffman_kraft_gpu_prefilter_compact_operations(
    parent_stream: bytes,
    compact_operations: tuple[HuffmanKraftCompactOperation, ...],
    *,
    gpu_session: Any = None,
    hit_limit: int = HUFFMAN_KRAFT_GPU_HIT_LIMIT,
) -> tuple[tuple[HuffmanKraftCompactOperation, ...], int, int, str]:
    if gpu_session is None or not compact_operations:
        return compact_operations, 0, 0, "off"
    try:
        from . import idat_kraft_opengl_backend

        parent_metrics = _huffman_kraft_metrics(parent_stream)
        flags = []
        for compact in compact_operations:
            stream = _huffman_kraft_apply_compact_operation(parent_stream, compact)
            flags.append(
                1
                if stream is not None and _huffman_kraft_prefilter_accepts_metrics(parent_metrics, stream)
                else 0
            )
        plan = idat_kraft_opengl_backend.KraftOpenGLPlan(tuple(flags))
        result = gpu_session.run(plan)
    except Exception:
        return compact_operations, 0, 0, "fallback-cpu"
    if result.status != "opengl-active":
        return compact_operations, int(result.shards), 0, result.status
    indices = tuple(index for index in result.hit_indices if 0 <= int(index) < len(compact_operations))
    indices = indices[: max(1, int(hit_limit))]
    if not indices:
        return (), int(result.shards), 0, result.status
    return tuple(compact_operations[int(index)] for index in indices), int(result.shards), len(indices), result.status


def _huffman_kraft_validate_operations(
    parent: IdatDeepBeamCandidate,
    operations: tuple[IdatDeepBeamOperation, ...],
    *,
    chunks: tuple[png.PngChunk, ...],
    before: idat.IdatStreamAnalysis,
    state_id_start: int,
    original_idat_count: int,
    workers: int,
    worker_executor: ProcessPoolExecutor | None,
    gpu_session: Any = None,
    cpu_batch_size: int | None = None,
    in_flight_limit: int | None = None,
    successor_limit: int | None = None,
) -> tuple[tuple[IdatDeepBeamCandidate, ...], int, int, int, int, str]:
    compact_operations = tuple(
        compact
        for compact in (
            _huffman_kraft_compact_operation(int(state_id_start) + index, operation)
            for index, operation in enumerate(operations)
        )
        if compact is not None
    )
    compact_operations, gpu_shards, gpu_hits, gpu_status = _huffman_kraft_gpu_prefilter_compact_operations(
        parent.stream,
        compact_operations,
        gpu_session=gpu_session,
    )
    batches = _huffman_kraft_operation_batches(
        compact_operations,
        workers=workers,
        cpu_batch_size=cpu_batch_size,
    )
    if not batches:
        return (), 0, 0, gpu_shards, gpu_hits, gpu_status
    successor_limit = max(1, int(successor_limit or HUFFMAN_KRAFT_SUCCESSOR_KEEP_LIMIT))

    def prune_candidates(candidates: list[IdatDeepBeamCandidate]) -> list[IdatDeepBeamCandidate]:
        if len(candidates) <= successor_limit * 2:
            return candidates
        return list(_huffman_kraft_ranked_unique(candidates, limit=successor_limit))

    def run_local() -> tuple[tuple[IdatDeepBeamCandidate, ...], int, int, int, int, str]:
        candidates: list[IdatDeepBeamCandidate] = []
        prefilter_hits = 0
        cpu_batches = 0
        for batch in batches:
            batch_candidates, batch_hits = _huffman_kraft_apply_compact_operation_batch(
                (
                    parent.stream,
                    parent.operations,
                    parent.state_id,
                    parent.source_offsets,
                    batch,
                    chunks,
                    before,
                    original_idat_count,
                )
            )
            candidates.extend(batch_candidates)
            candidates = prune_candidates(candidates)
            prefilter_hits += int(batch_hits)
            cpu_batches += 1
        return _huffman_kraft_ranked_unique(candidates, limit=successor_limit), prefilter_hits, cpu_batches, gpu_shards, gpu_hits, gpu_status

    if worker_executor is None or len(batches) <= 1:
        return run_local()

    candidates: list[IdatDeepBeamCandidate] = []
    prefilter_hits = 0
    submitted = 0
    completed = 0
    in_flight_limit = max(
        1,
        min(
            int(in_flight_limit or _deep_beam_worker_in_flight_limit(workers, len(batches))),
            len(batches),
        ),
    )
    pending: dict[Any, int] = {}

    def submit_next() -> None:
        nonlocal submitted
        if submitted >= len(batches):
            return
        future = worker_executor.submit(
            _huffman_kraft_apply_compact_operation_batch,
            (
                parent.stream,
                parent.operations,
                parent.state_id,
                parent.source_offsets,
                batches[submitted],
                chunks,
                before,
                original_idat_count,
            ),
        )
        pending[future] = submitted
        submitted += 1

    try:
        for _ in range(in_flight_limit):
            submit_next()
    except Exception:
        for future in pending:
            future.cancel()
        return run_local()

    try:
        while pending:
            done, _not_done = wait(tuple(pending), return_when=FIRST_COMPLETED)
            for future in done:
                pending.pop(future, None)
                batch_candidates, batch_hits = future.result()
                candidates.extend(batch_candidates)
                candidates = prune_candidates(candidates)
                prefilter_hits += int(batch_hits)
                completed += 1
                submit_next()
        return (
            _huffman_kraft_ranked_unique(candidates, limit=successor_limit),
            prefilter_hits,
            completed,
            gpu_shards,
            gpu_hits,
            gpu_status,
        )
    except KeyboardInterrupt:
        for future in pending:
            future.cancel()
        raise
    except Exception:
        for future in pending:
            future.cancel()
        return run_local()


def probe_idat_huffman_kraft_solver(
    data: bytes,
    *,
    budget: int = HUFFMAN_KRAFT_DEFAULT_BUDGET,
    max_depth: int = HUFFMAN_KRAFT_DEFAULT_MAX_DEPTH,
    beam_width: int = HUFFMAN_KRAFT_DEFAULT_WIDTH,
    top_candidates: int = HUFFMAN_KRAFT_DEFAULT_TOP_CANDIDATES,
    workers: str | int | None = "auto",
    gpu: bool | str | int | None = False,
    gpu_config: Any = None,
    checkpoint_path: str = "",
    progress_path: str = "",
    seed_candidates: Iterable[IdatDeepBeamCandidate] = (),
    progress: QueueProgressCallback | None = None,
) -> IdatHuffmanKraftSolverResult:
    strategy = "huffman-kraft"
    budget_int = max(0, int(budget))
    worker_count = _deep_beam_workers(workers)
    gpu_requested = _deep_beam_gpu_requested(gpu)
    resolved_gpu_config = _deep_beam_gpu_config(gpu, gpu_config)
    if gpu_requested and not bool(getattr(resolved_gpu_config, "enabled", False)):
        try:
            resolved_gpu_config = replace(resolved_gpu_config, enabled=True)
        except Exception:
            pass
    before = idat.analyze_idat_stream(data)
    if not before.supported or before.complete:
        return IdatHuffmanKraftSolverResult(before, None, (), 0, False, strategy=strategy, reason=before.reason)
    try:
        chunks, root_stream = _all_chunks_and_idat_stream(data)
    except png.PngFormatError as exc:
        return IdatHuffmanKraftSolverResult(before, None, (), 0, False, strategy=strategy, reason=str(exc))
    source_hash = _stream_state_key(root_stream)
    original_idat_count = sum(1 for chunk in chunks if chunk.chunk_type == b"IDAT")
    if checkpoint_path:
        _compact_deep_beam_checkpoint_file(
            checkpoint_path,
            source_hash=source_hash,
            source_stream=root_stream,
        )
    progress_state = huffman_kraft_progress_state(data, progress_path)
    if (
        progress_state.available
        and progress_state.source_matches
        and progress_state.exhausted
        and progress_state.budget >= budget_int
    ):
        _before, _chunks, _stream, _source_hash, _count, top = _load_frontier_candidates_for_progress(
            data,
            checkpoint_path,
            top_candidates=top_candidates,
            max_operation_depth=None,
        )
        best = _frontier_best_candidate(before, top)
        literal_debt, distance_debt, _eob, _lc, _dc, _lu, _du = _huffman_kraft_metrics(top[0].stream if top else root_stream)
        return IdatHuffmanKraftSolverResult(
            before,
            best,
            top,
            progress_state.tested,
            True,
            checkpoint_path=checkpoint_path,
            progress_path=progress_path,
            best_literal_debt=literal_debt,
            best_distance_debt=distance_debt,
            workers=worker_count,
            gpu_status="fallback-cpu" if gpu_requested else "off",
            strategy=strategy,
            reason="huffman kraft already exhausted for this source/budget",
            source_hash=source_hash,
        )

    root = _frontier_root_candidate(
        data=data,
        stream=root_stream,
        before=before,
        original_idat_count=original_idat_count,
    )
    frontier = [root]
    top: list[IdatDeepBeamCandidate] = []
    visited = {_stream_state_key(root_stream)}
    checkpointed_hashes: set[str] = set()
    next_state_id = 1
    tested = 0
    valid_headers = 0
    complete_trees = 0
    first_symbol_ok = 0
    budget_exhausted = False
    reached_depth = 0
    last_checkpoint_at = 0
    last_progress_snapshot_at = 0
    gpu_status = "off"
    gpu_hits = 0
    gpu_shards = 0
    cpu_batches = 0
    kraft_prefilter_hits = 0
    memory_guard_hit = False
    memory_mode = "normal"
    memory_available_bytes: int | None = _deep_beam_memory_available_bytes()
    memory_throttle_events = 0
    effective_cpu_batch_size = DEEP_BEAM_DEFAULT_CPU_BATCH_SIZE
    effective_in_flight_limit: int | None = None
    effective_successor_limit = HUFFMAN_KRAFT_SUCCESSOR_KEEP_LIMIT
    worker_executor: ProcessPoolExecutor | None = None
    gpu_session: Any = None

    checkpoint_candidates: tuple[IdatDeepBeamCandidate, ...] = ()
    checkpoint_matched_records = 0
    if checkpoint_path and os.path.exists(checkpoint_path):
        checkpoint_candidate_list, checkpoint_visited, checkpoint_next_state_id, checkpoint_matched_records = _load_deep_beam_checkpoint(
            checkpoint_path,
            source_hash=source_hash,
            source_stream=root_stream,
            chunks=chunks,
            before=before,
            original_idat_count=original_idat_count,
            candidate_limit=max(1, int(top_candidates)),
            max_operation_depth=None,
        )
        checkpoint_candidates = tuple(checkpoint_candidate_list)
        checkpointed_hashes = set(checkpoint_visited)
        visited.update(checkpoint_visited)
        visited.add(source_hash)
        next_state_id = max(next_state_id, int(checkpoint_next_state_id))
        if progress_state.available and progress_state.source_matches:
            tested = max(tested, int(progress_state.tested))
        elif checkpoint_matched_records:
            checkpoint_groups = max(1, int(top_candidates))
            inferred_tested = (int(checkpoint_matched_records) // checkpoint_groups) * int(HUFFMAN_KRAFT_CHECKPOINT_EVERY)
            tested = max(tested, min(budget_int, inferred_tested))
        last_checkpoint_at = tested
        last_progress_snapshot_at = tested

    if (
        progress_state.available
        and progress_state.source_matches
        and "memory_guard" in str(progress_state.reason)
    ):
        worker_count = min(max(1, int(worker_count)), int(HUFFMAN_KRAFT_THROTTLE_WORKER_LIMIT))
        gpu_requested = False
        memory_mode = "resume-degraded"
        effective_cpu_batch_size = HUFFMAN_KRAFT_HARD_THROTTLE_BATCH_SIZE
        effective_in_flight_limit = 1
        effective_successor_limit = max(1, min(HUFFMAN_KRAFT_SUCCESSOR_KEEP_LIMIT, max(int(top_candidates), 64)))

    for seed in seed_candidates:
        if seed.stream and _stream_state_key(seed.stream) not in visited:
            visited.add(_stream_state_key(seed.stream))
            top.append(seed)
            if _huffman_kraft_accepts(root, seed):
                frontier.append(seed)

    for seed in checkpoint_candidates:
        if not seed.stream:
            continue
        top.append(seed)
        if _huffman_kraft_accepts(root, seed):
            frontier.append(seed)

    top = list(
        sorted(
            _deep_beam_ranked_unique(top, limit=max(1, int(top_candidates))),
            key=lambda item: _huffman_kraft_rank(item.stream, item.after),
            reverse=True,
        )
    )[: max(1, int(top_candidates))]
    frontier = list(
        sorted(
            _deep_beam_ranked_unique(frontier, limit=max(1, int(beam_width))),
            key=lambda item: _huffman_kraft_rank(item.stream, item.after),
            reverse=True,
        )
    )[: max(1, int(beam_width))]

    def write_checkpoint_items() -> None:
        nonlocal checkpointed_hashes
        if not checkpoint_path:
            return
        for item in top:
            key = _stream_state_key(item.stream)
            if key in checkpointed_hashes:
                continue
            _append_frontier_checkpoint(
                checkpoint_path,
                item,
                source_hash=source_hash,
                source_stream=root_stream,
            )
            checkpointed_hashes.add(key)

    def write_progress_snapshot(*, exhausted: bool, reason: str) -> None:
        snapshot_best = _frontier_best_candidate(before, top)
        snapshot_literal_debt, snapshot_distance_debt, _eob, _lc, _dc, _lu, _du = _huffman_kraft_metrics(
            top[0].stream if top else root_stream
        )
        _write_frontier_progress(
            progress_path,
            source_hash=source_hash,
            tested=tested,
            budget=budget_int,
            best=snapshot_best,
            top_count=len(top),
            exhausted=exhausted,
            reason=reason,
            strategy=strategy,
            extra={
                "valid_headers": int(valid_headers),
                "complete_trees": int(complete_trees),
                "first_symbol_ok": int(first_symbol_ok),
                "literal_debt": int(snapshot_literal_debt),
                "distance_debt": int(snapshot_distance_debt),
                "reached_depth": int(reached_depth),
                "checkpoint_records": int(checkpoint_matched_records),
                "workers": int(worker_count),
                "gpu_status": str(gpu_status),
                "gpu_shards": int(gpu_shards),
                "gpu_hits": int(gpu_hits),
                "cpu_batches": int(cpu_batches),
                "kraft_prefilter_hits": int(kraft_prefilter_hits),
                "memory_mode": str(memory_mode),
                "memory_available_bytes": memory_available_bytes,
                "memory_throttle_events": int(memory_throttle_events),
                "effective_batch_size": int(effective_cpu_batch_size),
                "effective_in_flight": int(effective_in_flight_limit or 0),
                "effective_successor_limit": int(effective_successor_limit),
                "resumable": True,
            },
        )

    def write_abort_snapshot(reason: str) -> None:
        try:
            write_checkpoint_items()
        except Exception:
            pass
        try:
            write_progress_snapshot(exhausted=False, reason=reason)
        except Exception:
            pass

    def remember(parent: IdatDeepBeamCandidate, candidate: IdatDeepBeamCandidate) -> bool:
        nonlocal top, valid_headers, complete_trees, first_symbol_ok
        key = _stream_state_key(candidate.stream)
        if key in visited:
            return False
        if not _huffman_kraft_accepts(parent, candidate):
            return False
        visited.add(key)
        trace = deflate_header.trace_dynamic_header(candidate.stream)
        if trace.status == "ok":
            valid_headers += 1
        literal_debt, distance_debt, _eob, literal_complete, distance_complete, _lu, _du = _huffman_kraft_metrics(candidate.stream)
        if literal_complete and distance_complete:
            complete_trees += 1
            oracle = raw_png_oracle_decision(candidate.stream, candidate.after, max_output=1)
            if oracle.first_filter_ok:
                first_symbol_ok += 1
        top = list(_deep_beam_ranked_unique(itertools.chain(top, (candidate,)), limit=top_candidates))
        return True

    def shutdown_worker_executor() -> None:
        nonlocal worker_executor
        if worker_executor is None:
            return
        try:
            worker_executor.shutdown(cancel_futures=True)
        except Exception:
            pass
        worker_executor = None

    def ensure_worker_executor() -> None:
        nonlocal worker_executor, worker_count
        if int(worker_count) <= 1 or worker_executor is not None:
            return
        try:
            worker_executor = ProcessPoolExecutor(max_workers=worker_count, initializer=_deep_beam_worker_init)
        except (OSError, RuntimeError, ValueError):
            worker_executor = None
            worker_count = 1

    def close_gpu_session(status: str = "disabled-memory-pressure") -> None:
        nonlocal gpu_session, gpu_status
        if gpu_session is not None:
            try:
                gpu_session.close()
            except Exception:
                pass
        gpu_session = None
        if gpu_requested:
            gpu_status = status

    def apply_memory_policy() -> bool:
        nonlocal worker_count, memory_mode, memory_available_bytes, memory_throttle_events
        nonlocal effective_cpu_batch_size, effective_in_flight_limit, effective_successor_limit
        memory_available_bytes = _deep_beam_memory_available_bytes()
        level = _huffman_kraft_memory_level(memory_available_bytes)
        if level == "normal" and _deep_beam_memory_guard_tripped():
            level = "hard"
        if level == "normal":
            return True
        if level != memory_mode:
            memory_throttle_events += 1
        memory_mode = level
        if level == "soft":
            effective_cpu_batch_size = min(effective_cpu_batch_size, HUFFMAN_KRAFT_THROTTLE_BATCH_SIZE)
            effective_in_flight_limit = 2
            effective_successor_limit = max(1, min(effective_successor_limit, max(int(top_candidates), 128)))
            if worker_count > HUFFMAN_KRAFT_THROTTLE_WORKER_LIMIT:
                shutdown_worker_executor()
                worker_count = HUFFMAN_KRAFT_THROTTLE_WORKER_LIMIT
                ensure_worker_executor()
            return True
        effective_cpu_batch_size = min(effective_cpu_batch_size, HUFFMAN_KRAFT_HARD_THROTTLE_BATCH_SIZE)
        effective_in_flight_limit = 1
        effective_successor_limit = max(1, min(effective_successor_limit, max(int(top_candidates), 64)))
        close_gpu_session()
        if worker_count > 2:
            shutdown_worker_executor()
            worker_count = 2
            ensure_worker_executor()
        if level == "hard":
            return True
        shutdown_worker_executor()
        worker_count = 1
        return False

    if progress is not None:
        progress(strategy, min(tested, budget_int), budget_int)
    if checkpoint_candidates or (progress_state.available and progress_state.source_matches and not progress_state.exhausted):
        write_checkpoint_items()
        write_progress_snapshot(exhausted=False, reason="huffman kraft resumed from checkpoint/progress")

    ensure_worker_executor()
    if gpu_requested:
        try:
            from . import idat_kraft_opengl_backend

            gpu_session = idat_kraft_opengl_backend.KraftOpenGLSession(resolved_gpu_config)
            gpu_status = "fallback-cpu"
        except Exception as exc:
            gpu_session = None
            gpu_status = "fallback-cpu"

    try:
        for depth in range(1, max(1, int(max_depth)) + 1):
            reached_depth = depth
            next_frontier: list[IdatDeepBeamCandidate] = []
            for parent in frontier:
                if not apply_memory_policy():
                    memory_guard_hit = True
                    write_abort_snapshot("huffman kraft memory guard")
                    break
                if tested >= budget_int:
                    budget_exhausted = True
                    break
                trace = deflate_header.trace_dynamic_header(parent.stream)
                if trace.btype != 2 or not trace.tokens:
                    continue
                operations = _huffman_kraft_token_operations(parent.stream, trace, max_tokens=96 if depth == 1 else 48)
                remaining = max(0, budget_int - tested)
                if remaining <= 0:
                    budget_exhausted = True
                    break
                operations = tuple(operations[:remaining])
                candidates, batch_prefilter_hits, batch_cpu_batches, batch_gpu_shards, batch_gpu_hits, batch_gpu_status = _huffman_kraft_validate_operations(
                    parent,
                    operations,
                    chunks=chunks,
                    before=before,
                    state_id_start=next_state_id,
                    original_idat_count=original_idat_count,
                    workers=worker_count,
                    worker_executor=worker_executor,
                    gpu_session=gpu_session if depth <= 2 else None,
                    cpu_batch_size=effective_cpu_batch_size,
                    in_flight_limit=effective_in_flight_limit,
                    successor_limit=effective_successor_limit,
                )
                if not apply_memory_policy():
                    memory_guard_hit = True
                cpu_batches += int(batch_cpu_batches)
                kraft_prefilter_hits += int(batch_prefilter_hits)
                gpu_shards += int(batch_gpu_shards)
                gpu_hits += int(batch_gpu_hits)
                if batch_gpu_status != "off":
                    gpu_status = batch_gpu_status
                tested += len(operations)
                next_state_id += len(operations)
                for candidate in candidates:
                    if remember(parent, candidate):
                        next_frontier.append(candidate)
                if memory_guard_hit:
                    write_abort_snapshot("huffman kraft memory guard")
                    break
                if progress is not None and (tested == len(operations) or tested % 100 == 0 or len(operations) >= 100):
                    progress(strategy, min(tested, budget_int), budget_int)
                if checkpoint_path and top and tested - last_checkpoint_at >= HUFFMAN_KRAFT_CHECKPOINT_EVERY:
                    write_checkpoint_items()
                    write_progress_snapshot(exhausted=False, reason="huffman kraft checkpoint")
                    last_checkpoint_at = tested
                    last_progress_snapshot_at = tested
                elif progress_path and tested - last_progress_snapshot_at >= HUFFMAN_KRAFT_PROGRESS_EVERY:
                    write_progress_snapshot(exhausted=False, reason="huffman kraft progress")
                    last_progress_snapshot_at = tested
                if tested >= budget_int:
                    budget_exhausted = True
                    break
            if memory_guard_hit:
                break
            frontier = list(
                sorted(
                    _deep_beam_ranked_unique(next_frontier, limit=max(1, int(beam_width))),
                    key=lambda item: _huffman_kraft_rank(item.stream, item.after),
                    reverse=True,
                )
            )[: max(1, int(beam_width))]
            if budget_exhausted or not frontier:
                break
    except KeyboardInterrupt:
        write_abort_snapshot("huffman kraft interrupted")
        raise
    except BaseException as exc:
        write_abort_snapshot("huffman kraft aborted: %s: %s" % (type(exc).__name__, exc))
        raise
    finally:
        if gpu_session is not None:
            try:
                gpu_session.close()
            except Exception:
                pass
        if worker_executor is not None:
            worker_executor.shutdown(cancel_futures=True)

    if checkpoint_path:
        write_checkpoint_items()
    top = list(
        sorted(
            _deep_beam_ranked_unique(top, limit=top_candidates),
            key=lambda item: _huffman_kraft_rank(item.stream, item.after),
            reverse=True,
        )
    )[: max(1, int(top_candidates))]
    best = _frontier_best_candidate(before, top)
    best_literal_debt, best_distance_debt, _eob, _lc, _dc, _lu, _du = _huffman_kraft_metrics(top[0].stream if top else root_stream)
    stop_reason = "memory_guard" if memory_guard_hit else _bounded_route_stop_reason(
        tested=tested,
        budget=budget_int,
        budget_exhausted=budget_exhausted or tested >= budget_int,
        frontier_exhausted=not frontier,
        depth_limit_reached=not (budget_exhausted or tested >= budget_int),
    )
    reason = (
        "stop=%s; depth=%s; states=%s; valid_headers=%s; complete_trees=%s; first_symbol_ok=%s; "
        "literal_debt=%s; distance_debt=%s; top=%s; memory_mode=%s; throttle_events=%s"
        % (
            stop_reason,
            reached_depth,
            len(visited),
            valid_headers,
            complete_trees,
            first_symbol_ok,
            best_literal_debt,
            best_distance_debt,
            len(top),
            memory_mode,
            memory_throttle_events,
        )
    )
    _write_frontier_progress(
        progress_path,
        source_hash=source_hash,
        tested=tested,
        budget=budget_int,
        best=best,
        top_count=len(top),
        exhausted=not memory_guard_hit,
        reason=reason,
        strategy=strategy,
        extra={
            "valid_headers": int(valid_headers),
            "complete_trees": int(complete_trees),
            "first_symbol_ok": int(first_symbol_ok),
            "literal_debt": int(best_literal_debt),
            "distance_debt": int(best_distance_debt),
            "reached_depth": int(reached_depth),
            "workers": int(worker_count),
            "gpu_status": str(gpu_status),
            "gpu_shards": int(gpu_shards),
            "gpu_hits": int(gpu_hits),
            "cpu_batches": int(cpu_batches),
            "kraft_prefilter_hits": int(kraft_prefilter_hits),
            "memory_mode": str(memory_mode),
            "memory_available_bytes": memory_available_bytes,
            "memory_throttle_events": int(memory_throttle_events),
            "effective_batch_size": int(effective_cpu_batch_size),
            "effective_in_flight": int(effective_in_flight_limit or 0),
            "effective_successor_limit": int(effective_successor_limit),
            "resumable": True,
        },
    )
    if progress is not None:
        progress(strategy, min(tested, budget_int), budget_int)
    return IdatHuffmanKraftSolverResult(
        before,
        best,
        tuple(top),
        tested,
        budget_exhausted or tested >= budget_int,
        checkpoint_path=checkpoint_path,
        progress_path=progress_path,
        valid_headers=valid_headers,
        complete_trees=complete_trees,
        first_symbol_ok=first_symbol_ok,
        best_literal_debt=best_literal_debt,
        best_distance_debt=best_distance_debt,
        reached_depth=reached_depth,
        workers=worker_count,
        gpu_status=gpu_status,
        gpu_hits=gpu_hits,
        gpu_shards=gpu_shards,
        cpu_batches=cpu_batches,
        kraft_prefilter_hits=kraft_prefilter_hits,
        memory_mode=memory_mode,
        memory_available_bytes=memory_available_bytes,
        memory_throttle_events=memory_throttle_events,
        strategy=strategy,
        reason=reason,
        source_hash=source_hash,
    )


def _dynamic_first_literal_symbol(
    stream: bytes,
) -> tuple[int, int, int, dict[tuple[int, int], int], int] | None:
    try:
        reader = deflate_header.BitReader(stream, start_byte=2)
        reader.read(1)
        btype = reader.read(2)
        if btype != 2:
            return None
        literal_table, literal_max, _distance_table, _distance_max = deflate_probe._read_dynamic_tables(reader)
        symbol, bit_start, bit_end = deflate_header._decode_symbol_with_bits(
            reader,
            literal_table,
            literal_max,
        )
    except Exception:
        return None
    return int(symbol), int(bit_start), int(bit_end), literal_table, int(literal_max)


def _huffman_symbol_codes(table: dict[tuple[int, int], int]) -> dict[int, tuple[int, int]]:
    return {
        int(symbol): (int(code), int(width))
        for (code, width), symbol in table.items()
    }


def _single_symbol_closure_length(left: int, max_bits: int) -> int | None:
    left = int(left)
    max_bits = int(max_bits)
    if left <= 0 or max_bits <= 0:
        return None
    if left & (left - 1):
        return None
    shift = left.bit_length() - 1
    target = max_bits - shift
    if target < 1 or target > 15:
        return None
    return int(target)


def _huffman_kraft_closure_operations(
    stream: bytes,
    trace: deflate_header.DynamicHeaderTrace,
    *,
    max_operations: int = 32,
) -> tuple[IdatDeepBeamOperation, ...]:
    if max_operations <= 0 or trace.btype != 2 or not trace.tokens:
        return ()
    try:
        symbol_codes = _dynamic_code_length_symbol_codes(trace)
    except Exception:
        return ()
    try:
        hlit = int(trace.hlit or 0)
    except (TypeError, ValueError):
        hlit = 0
    if hlit <= 0:
        return ()

    operations: list[IdatDeepBeamOperation] = []
    seen: set[tuple[int, int, tuple[int, ...]]] = set()

    def token_for_length_index(global_index: int) -> deflate_header.DynamicLengthToken | None:
        for token in trace.tokens:
            if int(token.length_start) <= int(global_index) < int(token.length_end):
                if int(token.length_end) - int(token.length_start) != 1:
                    return None
                return token
        return None

    targets = (
        ("literal", tuple(int(value) for value in trace.literal_lengths), 0),
        ("distance", tuple(int(value) for value in trace.distance_lengths), hlit),
    )
    for label, lengths, global_start in targets:
        left, _debt, _used, max_bits = _huffman_balance(lengths)
        target_length = _single_symbol_closure_length(left, max_bits)
        if target_length is None:
            continue
        encoded = _encode_dynamic_length_token(symbol_codes, target_length)
        if encoded is None:
            continue

        zero_indexes = tuple(index for index, value in enumerate(lengths) if int(value) == 0)
        if label == "distance":
            zero_indexes = tuple(sorted(zero_indexes, key=lambda index: (abs(index - 10), index)))
        else:
            zero_indexes = tuple(sorted(zero_indexes, key=lambda index: (abs(index - 256), index)))

        for index in zero_indexes:
            if len(operations) >= max_operations:
                return tuple(operations)
            token = token_for_length_index(int(global_start) + int(index))
            if token is None:
                continue
            bit_start = int(token.bit_start)
            bit_end = _dynamic_length_token_bit_end(token)
            key = (bit_start, bit_end, tuple(int(bit) & 1 for bit in encoded))
            if key in seen:
                continue
            seen.add(key)
            operations.append(
                IdatDeepBeamOperation(
                    "huffman-kraft-closure-%s" % label,
                    bit_start // 8,
                    _stream_bit_range_to_bytes(stream, bit_start, bit_end),
                    bytes(int(bit) & 1 for bit in encoded),
                    tuple(range(bit_start, bit_end)),
                )
            )
    return tuple(operations)


def _first_filter_literal_candidate(
    parent: IdatDeepBeamCandidate,
    target_filter: int,
    *,
    chunks: tuple[png.PngChunk, ...],
    before: idat.IdatStreamAnalysis,
    state_id: int,
    original_idat_count: int,
) -> IdatDeepBeamCandidate | None:
    first = _dynamic_first_literal_symbol(parent.stream)
    if first is None:
        return None
    symbol, bit_start, bit_end, literal_table, _literal_max = first
    codes = _huffman_symbol_codes(literal_table)
    target_code = codes.get(int(target_filter))
    if target_code is None:
        return None
    code, width = target_code
    replacement_bits = tuple((int(code) >> index) & 1 for index in range(int(width)))
    stream = _replace_stream_bits_preserve_length(parent.stream, bit_start, bit_end, replacement_bits)
    if stream is None or stream == parent.stream:
        return None
    operation = IdatDeepBeamOperation(
        "first-filter-literal",
        int(bit_start) // 8,
        _stream_bit_range_to_bytes(parent.stream, bit_start, bit_end),
        bytes(int(bit) & 1 for bit in replacement_bits),
        tuple(range(int(bit_start), int(bit_end))),
    )
    candidate = _frontier_candidate_from_stream(
        parent,
        stream,
        operation,
        chunks=chunks,
        before=before,
        state_id=int(state_id),
        original_idat_count=original_idat_count,
        source_kind="candidate_from_first_filter_literal",
    )
    if candidate is None:
        return None
    oracle = raw_png_oracle_decision(
        candidate.stream,
        candidate.after,
        max_output=max(8192, int(getattr(before, "scanline_size", 0) or 0) * 2),
    )
    if not oracle.first_filter_ok:
        return None
    return candidate


def probe_idat_first_filter_literal_solver(
    data: bytes,
    *,
    budget: int = FIRST_FILTER_LITERAL_DEFAULT_BUDGET,
    top_candidates: int = FIRST_FILTER_LITERAL_DEFAULT_TOP_CANDIDATES,
    checkpoint_path: str = "",
    progress_path: str = "",
    seed_candidates: Iterable[IdatDeepBeamCandidate] = (),
    progress: QueueProgressCallback | None = None,
) -> IdatFirstFilterLiteralResult:
    strategy = "first-filter-literal"
    budget_int = max(0, int(budget))
    before = idat.analyze_idat_stream(data)
    if not before.supported or before.complete:
        return IdatFirstFilterLiteralResult(before, None, (), 0, False, strategy=strategy, reason=before.reason)
    try:
        chunks, root_stream = _all_chunks_and_idat_stream(data)
    except png.PngFormatError as exc:
        return IdatFirstFilterLiteralResult(before, None, (), 0, False, strategy=strategy, reason=str(exc))
    source_hash = _stream_state_key(root_stream)
    original_idat_count = sum(1 for chunk in chunks if chunk.chunk_type == b"IDAT")
    seed_candidates_tuple = tuple(seed_candidates)
    progress_state = first_filter_literal_progress_state(data, progress_path)
    progress_route_version = frontier_progress_route_version(progress_path)
    if (
        progress_state.available
        and progress_state.source_matches
        and progress_state.exhausted
        and progress_state.budget >= budget_int
        and progress_route_version >= FIRST_FILTER_LITERAL_ROUTE_VERSION
    ):
        _before, _chunks, _stream, _source_hash, _count, top = _load_frontier_candidates_for_progress(
            data,
            checkpoint_path,
            top_candidates=top_candidates,
            max_operation_depth=None,
        )
        if top or not seed_candidates_tuple:
            best = _frontier_best_candidate(before, top)
            return IdatFirstFilterLiteralResult(
                before,
                best,
                top,
                progress_state.tested,
                progress_state.tested >= budget_int,
                checkpoint_path=checkpoint_path,
                progress_path=progress_path,
                seed_count=0,
                closure_hits=0,
                first_filter_hits=len(top),
                png_plausible=len(top),
                strategy=strategy,
                reason="first-filter-literal already exhausted for this source/budget",
                source_hash=source_hash,
            )

    root = _frontier_root_candidate(
        data=data,
        stream=root_stream,
        before=before,
        original_idat_count=original_idat_count,
    )
    parents: list[IdatDeepBeamCandidate] = [root]
    seen_parent_hashes = {_stream_state_key(root.stream)}
    seed_count = 0
    for seed in seed_candidates_tuple:
        if not getattr(seed, "stream", b""):
            continue
        key = _stream_state_key(seed.stream)
        if key in seen_parent_hashes:
            continue
        seen_parent_hashes.add(key)
        seed_count += 1
        parents.append(seed)

    tested = 0
    next_state_id = 1
    closure_hits = 0
    top: list[IdatDeepBeamCandidate] = []
    visited = {_stream_state_key(root.stream)}
    first_filter_hits = 0
    png_plausible = 0
    budget_exhausted = False

    expanded_parents = list(parents)
    for parent in tuple(parents):
        if tested >= budget_int:
            budget_exhausted = True
            break
        trace = deflate_header.trace_dynamic_header(parent.stream)
        for operation in _huffman_kraft_closure_operations(parent.stream, trace):
            if tested >= budget_int:
                budget_exhausted = True
                break
            tested += 1
            candidate = _huffman_kraft_candidate_from_operation(
                parent,
                operation,
                chunks=chunks,
                before=before,
                state_id=next_state_id,
                original_idat_count=original_idat_count,
            )
            next_state_id += 1
            if candidate is None:
                continue
            key = _stream_state_key(candidate.stream)
            if key in seen_parent_hashes:
                continue
            closure_trace = deflate_header.trace_dynamic_header(candidate.stream)
            if closure_trace.status != "ok":
                continue
            seen_parent_hashes.add(key)
            closure_hits += 1
            expanded_parents.append(candidate)
    parents = expanded_parents

    for parent in parents:
        if tested >= budget_int:
            budget_exhausted = True
            break
        for target_filter in (0, 1, 2, 3, 4):
            if tested >= budget_int:
                budget_exhausted = True
                break
            tested += 1
            candidate = _first_filter_literal_candidate(
                parent,
                target_filter,
                chunks=chunks,
                before=before,
                state_id=next_state_id,
                original_idat_count=original_idat_count,
            )
            next_state_id += 1
            if candidate is None:
                continue
            key = _stream_state_key(candidate.stream)
            if key in visited:
                continue
            visited.add(key)
            first_filter_hits += 1
            oracle = raw_png_oracle_decision(candidate.stream, candidate.after)
            if oracle.first_filter_ok:
                png_plausible += 1
            top = list(_deep_beam_ranked_unique(itertools.chain(top, (candidate,)), limit=top_candidates))
        if progress is not None:
            progress(strategy, min(tested, budget_int), budget_int)

    top = list(_deep_beam_ranked_unique(top, limit=max(1, int(top_candidates))))
    best = _frontier_best_candidate(before, top)
    if checkpoint_path:
        for candidate in top:
            _append_frontier_checkpoint(
                checkpoint_path,
                candidate,
                source_hash=source_hash,
                source_stream=root_stream,
            )
    reason = (
        "seeds=%s; closure_hits=%s; tested=%s; first_filter_hits=%s; png_plausible=%s; top=%s"
        % (seed_count, closure_hits, tested, first_filter_hits, png_plausible, len(top))
    )
    _write_frontier_progress(
        progress_path,
        source_hash=source_hash,
        tested=tested,
        budget=budget_int,
        best=best,
        top_count=len(top),
        exhausted=True,
        reason=reason,
        strategy=strategy,
        extra={
            "route_version": int(FIRST_FILTER_LITERAL_ROUTE_VERSION),
            "seed_count": int(seed_count),
            "closure_hits": int(closure_hits),
            "first_filter_hits": int(first_filter_hits),
            "png_plausible": int(png_plausible),
        },
    )
    if progress is not None:
        progress(strategy, min(tested, budget_int), budget_int)
    return IdatFirstFilterLiteralResult(
        before,
        best,
        tuple(top),
        tested,
        budget_exhausted or tested >= budget_int,
        checkpoint_path=checkpoint_path,
        progress_path=progress_path,
        seed_count=seed_count,
        closure_hits=closure_hits,
        first_filter_hits=first_filter_hits,
        png_plausible=png_plausible,
        strategy=strategy,
        reason=reason,
        source_hash=source_hash,
    )


@dataclass(frozen=True)
class _InvalidDistanceBackref:
    token_index: int
    bit_start: int
    bit_end: int
    output_before: int
    length: int
    distance_symbol: int
    distance: int
    distance_table: dict[tuple[int, int], int]
    length_bit_start: int = 0
    length_bit_end: int = 0
    length_symbol: int = 0
    literal_table: dict[tuple[int, int], int] = field(default_factory=dict)


def _png_valid_prefix_rows(raw: bytes, analysis: idat.IdatStreamAnalysis) -> int:
    scanline_size = int(getattr(analysis, "scanline_size", 0) or 0)
    if not raw or scanline_size <= 0:
        return 0
    rows = len(raw) // scanline_size
    valid = 0
    for row in range(rows):
        if raw[row * scanline_size] not in (0, 1, 2, 3, 4):
            break
        valid += 1
    return valid


def _locate_first_invalid_distance_backref(
    stream: bytes,
    *,
    max_tokens: int = 8192,
) -> _InvalidDistanceBackref | None:
    if not deflate_header.zlib_header_is_valid(stream):
        return None
    reader = deflate_header.BitReader(stream, start_byte=2)
    output_size = 0
    try:
        reader.read(1)
        btype = reader.read(2)
        if btype == 0:
            return None
        if btype == 1:
            literal_table, literal_max, distance_table, distance_max = deflate_probe._FIXED_TABLES
        elif btype == 2:
            literal_table, literal_max, distance_table, distance_max = deflate_probe._read_dynamic_tables(reader)
        else:
            return None
        for token_index in range(max(1, int(max_tokens))):
            symbol, length_bit_start, length_bit_end = deflate_header._decode_symbol_with_bits(
                reader,
                literal_table,
                literal_max,
            )
            if symbol < 256:
                output_size += 1
                continue
            if symbol == 256:
                return None
            if not (257 <= symbol <= 285):
                return None
            length_index = symbol - 257
            length = deflate_probe.LENGTH_BASES[length_index]
            extra_bits = deflate_probe.LENGTH_EXTRAS[length_index]
            if extra_bits:
                length += reader.read(extra_bits)
            distance_symbol, distance_bit_start, _distance_bit_end = deflate_header._decode_symbol_with_bits(
                reader,
                distance_table,
                distance_max,
            )
            if distance_symbol >= len(deflate_probe.DISTANCE_BASES):
                return None
            distance = deflate_probe.DISTANCE_BASES[distance_symbol]
            distance_extra_bits = deflate_probe.DISTANCE_EXTRAS[distance_symbol]
            if distance_extra_bits:
                distance += reader.read(distance_extra_bits)
            distance_bit_end = reader.bit_offset
            if distance > output_size:
                return _InvalidDistanceBackref(
                    token_index=int(token_index),
                    bit_start=int(distance_bit_start),
                    bit_end=int(distance_bit_end),
                    output_before=int(output_size),
                    length=int(length),
                    distance_symbol=int(distance_symbol),
                    distance=int(distance),
                    distance_table=dict(distance_table),
                    length_bit_start=int(length_bit_start),
                    length_bit_end=int(length_bit_end),
                    length_symbol=int(symbol),
                    literal_table=dict(literal_table),
                )
            output_size += length
    except (deflate_header._NeedBits, deflate_header._InvalidHuffman, IndexError):
        return None
    return None


def _kraft_backref_bits_for_code(code: int, width: int) -> tuple[int, ...]:
    return tuple((int(code) >> index) & 1 for index in range(int(width)))


def _kraft_backref_distance_operations(
    stream: bytes,
    invalid: _InvalidDistanceBackref,
    *,
    max_operations: int,
) -> tuple[IdatDeepBeamOperation, ...]:
    if max_operations <= 0 or invalid.output_before <= 0:
        return ()
    distance_codes = {
        int(symbol): (int(code), int(width))
        for (code, width), symbol in invalid.distance_table.items()
    }
    choices: list[tuple[int, int, int, tuple[int, ...]]] = []
    for distance_symbol in range(len(deflate_probe.DISTANCE_BASES)):
        if distance_symbol not in distance_codes:
            continue
        base = int(deflate_probe.DISTANCE_BASES[distance_symbol])
        extra_width = int(deflate_probe.DISTANCE_EXTRAS[distance_symbol])
        max_extra = 1 << extra_width
        code, width = distance_codes[distance_symbol]
        for extra_value in range(max_extra):
            distance = base + extra_value
            if distance <= 0 or distance > int(invalid.output_before):
                continue
            replacement_bits = (
                _kraft_backref_bits_for_code(code, width)
                + _kraft_backref_bits_for_code(extra_value, extra_width)
            )
            choices.append((distance, distance_symbol, extra_value, replacement_bits))
    choices.sort(key=lambda item: (-item[0], item[1], item[2], item[3]))
    old_bytes = _stream_bit_range_to_bytes(stream, invalid.bit_start, invalid.bit_end)
    operations: list[IdatDeepBeamOperation] = []
    seen: set[tuple[int, tuple[int, ...]]] = set()
    for distance, distance_symbol, _extra_value, replacement_bits in choices:
        key = (distance, replacement_bits)
        if key in seen:
            continue
        seen.add(key)
        operations.append(
            IdatDeepBeamOperation(
                "kraft-backref-distance",
                int(invalid.bit_start) // 8,
                old_bytes,
                bytes(int(bit) & 1 for bit in replacement_bits),
                tuple(range(int(invalid.bit_start), int(invalid.bit_end))),
            )
        )
        if len(operations) >= int(max_operations):
            break
    return tuple(operations)


def _kraft_backref_literal_operations(
    stream: bytes,
    invalid: _InvalidDistanceBackref,
    *,
    max_operations: int,
) -> tuple[IdatDeepBeamOperation, ...]:
    if max_operations <= 0 or not invalid.literal_table:
        return ()
    bit_start = int(invalid.length_bit_start)
    bit_end = int(invalid.length_bit_end)
    width = bit_end - bit_start
    if width <= 0:
        return ()
    literal_codes = _huffman_symbol_codes(invalid.literal_table)
    old_bytes = _stream_bit_range_to_bytes(stream, bit_start, bit_end)
    common_literals = (0, 1, 2, 3, 4, 255, 32, 10, 13)
    choices: list[tuple[int, int, tuple[int, ...]]] = []
    for literal, (code, code_width) in literal_codes.items():
        if not (0 <= int(literal) <= 255):
            continue
        if int(code_width) != width:
            continue
        priority = 0 if int(literal) in common_literals else 1
        bits = _kraft_backref_bits_for_code(code, code_width)
        choices.append((priority, int(literal), bits))
    choices.sort(key=lambda item: (item[0], item[1], item[2]))
    operations: list[IdatDeepBeamOperation] = []
    seen: set[tuple[int, ...]] = set()
    for _priority, _literal, replacement_bits in choices:
        if replacement_bits in seen:
            continue
        seen.add(replacement_bits)
        operations.append(
            IdatDeepBeamOperation(
                "kraft-backref-literal",
                bit_start // 8,
                old_bytes,
                bytes(int(bit) & 1 for bit in replacement_bits),
                tuple(range(bit_start, bit_end)),
            )
        )
        if len(operations) >= int(max_operations):
            break
    return tuple(operations)


def _kraft_backref_candidate_from_operation(
    parent: IdatDeepBeamCandidate,
    operation: IdatDeepBeamOperation,
    *,
    chunks: tuple[png.PngChunk, ...],
    before: idat.IdatStreamAnalysis,
    state_id: int,
    original_idat_count: int,
) -> IdatDeepBeamCandidate | None:
    if not operation.bit_offsets:
        return None
    stream = _replace_stream_bits_preserve_length(
        parent.stream,
        min(operation.bit_offsets),
        max(operation.bit_offsets) + 1,
        tuple(int(value) & 1 for value in operation.new_bytes),
    )
    if stream is None:
        return None
    candidate = _frontier_candidate_from_stream(
        parent,
        stream,
        operation,
        chunks=chunks,
        before=before,
        state_id=int(state_id),
        original_idat_count=original_idat_count,
        source_kind="candidate_from_kraft_backref_repair",
    )
    if candidate is None:
        return None
    raw_limit = max(8192, int(getattr(before, "scanline_size", 0) or 0) * 64)
    raw_prefix = idat_partial_raw_prefix(stream, max_output=raw_limit)
    raw_score = score_png_raw_prefix(raw_prefix.raw, before)
    prefix_rows = _png_valid_prefix_rows(raw_prefix.raw, before)
    score = (
        int(candidate.after.usable_scanlines),
        int(prefix_rows),
        int(raw_score.valid_filter_rows),
        int(raw_score.first_filter_rank),
        int(raw_score.alpha_rank),
        int(raw_score.raw_size),
        int(candidate.after.decompressed_size),
        int(candidate.after.error_offset if candidate.after.error_offset is not None else -1),
        -len(candidate.operations),
        -int(candidate.state_id),
    )
    return replace(candidate, score=score)


def probe_idat_kraft_backref_repair(
    data: bytes,
    *,
    budget: int = KRAFT_BACKREF_DEFAULT_BUDGET,
    max_depth: int = KRAFT_BACKREF_DEFAULT_MAX_DEPTH,
    top_candidates: int = KRAFT_BACKREF_DEFAULT_TOP_CANDIDATES,
    checkpoint_path: str = "",
    progress_path: str = "",
    seed_candidates: Iterable[IdatDeepBeamCandidate] = (),
    seed_checkpoint_path: str = "",
    progress: QueueProgressCallback | None = None,
) -> IdatKraftBackrefRepairResult:
    strategy = "kraft-backref-repair"
    budget_int = max(0, int(budget))
    before = idat.analyze_idat_stream(data)
    if not before.supported or before.complete:
        return IdatKraftBackrefRepairResult(before, None, (), 0, False, strategy=strategy, reason=before.reason)
    try:
        chunks, root_stream = _all_chunks_and_idat_stream(data)
    except png.PngFormatError as exc:
        return IdatKraftBackrefRepairResult(before, None, (), 0, False, strategy=strategy, reason=str(exc))
    source_hash = _stream_state_key(root_stream)
    original_idat_count = sum(1 for chunk in chunks if chunk.chunk_type == b"IDAT")
    progress_state = kraft_backref_progress_state(data, progress_path)
    progress_route_version = frontier_progress_route_version(progress_path)
    progress_reason = str(progress_state.reason or "")
    if (
        progress_state.available
        and progress_state.source_matches
        and progress_state.exhausted
        and progress_state.budget >= budget_int
        and progress_route_version >= KRAFT_BACKREF_ROUTE_VERSION
        and "no Kraft seed candidates" not in progress_reason
    ):
        _before, _chunks, _stream, _source_hash, _count, top = _load_frontier_candidates_for_progress(
            data,
            checkpoint_path,
            top_candidates=top_candidates,
            max_operation_depth=None,
        )
        best = _frontier_best_candidate(before, top)
        best_prefix = 0
        if top:
            best_prefix = _png_valid_prefix_rows(
                idat_partial_raw_prefix(top[0].stream, max_output=max(8192, int(before.scanline_size or 0) * 64)).raw,
                before,
            )
        return IdatKraftBackrefRepairResult(
            before,
            best,
            top,
            progress_state.tested,
            True,
            checkpoint_path=checkpoint_path,
            progress_path=progress_path,
            seed_checkpoint_path=seed_checkpoint_path,
            best_prefix_rows=best_prefix,
            strategy=strategy,
            reason="kraft backref already exhausted for this source/budget",
            source_hash=source_hash,
        )

    seeds: list[IdatDeepBeamCandidate] = [
        seed for seed in seed_candidates if getattr(seed, "stream", b"")
    ]
    if seed_checkpoint_path:
        try:
            _before, _chunks, _stream, _source_hash, _count, checkpoint_seeds = _load_frontier_candidates_for_progress(
                data,
                seed_checkpoint_path,
                top_candidates=max(1, int(top_candidates)),
                max_operation_depth=None,
            )
            seeds.extend(checkpoint_seeds)
        except Exception:
            pass
    seeds = list(_deep_beam_ranked_unique(seeds, limit=max(1, int(top_candidates))))
    if not seeds:
        _write_frontier_progress(
            progress_path,
            source_hash=source_hash,
            tested=0,
            budget=budget_int,
            best=None,
            top_count=0,
            exhausted=False,
            reason="no Kraft seed candidates available",
            strategy=strategy,
            extra={"route_version": int(KRAFT_BACKREF_ROUTE_VERSION)},
        )
        return IdatKraftBackrefRepairResult(
            before,
            None,
            (),
            0,
            False,
            checkpoint_path=checkpoint_path,
            progress_path=progress_path,
            seed_checkpoint_path=seed_checkpoint_path,
            strategy=strategy,
            reason="no Kraft seed candidates available",
            source_hash=source_hash,
        )

    if progress is not None:
        progress(strategy, 0, budget_int)

    top: list[IdatDeepBeamCandidate] = []
    visited: set[str] = {_stream_state_key(root_stream)}
    visited.update(_stream_state_key(seed.stream) for seed in seeds)
    tested = 0
    repaired_backrefs = 0
    png_prefix_hits = 0
    reached_depth = 0
    next_state_id = 1
    last_checkpoint_at = 0
    checkpointed_hashes: set[str] = set()

    frontier = list(seeds)
    for depth in range(1, max(1, int(max_depth)) + 1):
        if tested >= budget_int or not frontier:
            break
        reached_depth = depth
        next_frontier: list[IdatDeepBeamCandidate] = []
        for seed in frontier:
            if tested >= budget_int:
                break
            invalid = _locate_first_invalid_distance_backref(seed.stream)
            if invalid is None:
                continue
            seed_operation_budget = min(
                max(0, budget_int - tested),
                KRAFT_BACKREF_MAX_OPERATIONS_PER_SEED,
            )
            literal_operations = _kraft_backref_literal_operations(
                seed.stream,
                invalid,
                max_operations=seed_operation_budget,
            )
            remaining_after_literals = max(0, seed_operation_budget - len(literal_operations))
            distance_operations = _kraft_backref_distance_operations(
                seed.stream,
                invalid,
                max_operations=remaining_after_literals,
            )
            operations = literal_operations + distance_operations
            if not operations:
                continue
            repaired_backrefs += 1
            for operation in operations:
                if tested >= budget_int:
                    break
                candidate = _kraft_backref_candidate_from_operation(
                    seed,
                    operation,
                    chunks=chunks,
                    before=before,
                    state_id=next_state_id,
                    original_idat_count=original_idat_count,
                )
                tested += 1
                next_state_id += 1
                if candidate is None:
                    continue
                key = _stream_state_key(candidate.stream)
                if key in visited:
                    continue
                visited.add(key)
                raw_prefix = idat_partial_raw_prefix(
                    candidate.stream,
                    max_output=max(8192, int(before.scanline_size or 0) * 64),
                )
                prefix_rows = _png_valid_prefix_rows(raw_prefix.raw, before)
                if prefix_rows > 0:
                    png_prefix_hits += 1
                top = list(_deep_beam_ranked_unique(itertools.chain(top, (candidate,)), limit=top_candidates))
                if _locate_first_invalid_distance_backref(candidate.stream) is not None:
                    next_frontier.append(candidate)
                if progress is not None and (tested % 1000 == 0 or tested == budget_int):
                    progress(strategy, min(tested, budget_int), budget_int)
                if checkpoint_path and top and tested - last_checkpoint_at >= KRAFT_BACKREF_CHECKPOINT_EVERY:
                    for item in top:
                        item_key = _stream_state_key(item.stream)
                        if item_key in checkpointed_hashes:
                            continue
                        _append_frontier_checkpoint(checkpoint_path, item, source_hash=source_hash, source_stream=root_stream)
                        checkpointed_hashes.add(item_key)
                    _write_frontier_progress(
                        progress_path,
                        source_hash=source_hash,
                        tested=tested,
                        budget=budget_int,
                        best=_frontier_best_candidate(before, top),
                        top_count=len(top),
                        exhausted=False,
                        reason="kraft backref checkpoint",
                        strategy=strategy,
                        extra={
                            "route_version": int(KRAFT_BACKREF_ROUTE_VERSION),
                            "repaired_backrefs": int(repaired_backrefs),
                            "png_prefix_hits": int(png_prefix_hits),
                            "reached_depth": int(reached_depth),
                        },
                    )
                    last_checkpoint_at = tested
        frontier = list(_deep_beam_ranked_unique(next_frontier, limit=max(1, int(top_candidates))))

    top = list(_deep_beam_ranked_unique(top, limit=top_candidates))
    best = _frontier_best_candidate(before, top)
    best_prefix_rows = 0
    if top:
        best_prefix_rows = _png_valid_prefix_rows(
            idat_partial_raw_prefix(top[0].stream, max_output=max(8192, int(before.scanline_size or 0) * 64)).raw,
            before,
        )
    if checkpoint_path:
        for item in top:
            key = _stream_state_key(item.stream)
            if key in checkpointed_hashes:
                continue
            _append_frontier_checkpoint(checkpoint_path, item, source_hash=source_hash, source_stream=root_stream)
            checkpointed_hashes.add(key)
    reason = "seeds=%s; depth=%s; per_seed_limit=%s; repaired_backrefs=%s; png_prefix_hits=%s; best_prefix_rows=%s; top=%s" % (
        len(seeds),
        reached_depth,
        KRAFT_BACKREF_MAX_OPERATIONS_PER_SEED,
        repaired_backrefs,
        png_prefix_hits,
        best_prefix_rows,
        len(top),
    )
    _write_frontier_progress(
        progress_path,
        source_hash=source_hash,
        tested=tested,
        budget=budget_int,
        best=best,
        top_count=len(top),
        exhausted=True,
        reason=reason,
        strategy=strategy,
        extra={
            "route_version": int(KRAFT_BACKREF_ROUTE_VERSION),
            "seed_checkpoint_path": seed_checkpoint_path,
            "repaired_backrefs": int(repaired_backrefs),
            "png_prefix_hits": int(png_prefix_hits),
            "best_prefix_rows": int(best_prefix_rows),
            "reached_depth": int(reached_depth),
        },
    )
    if progress is not None:
        progress(strategy, min(tested, budget_int), budget_int)
    return IdatKraftBackrefRepairResult(
        before,
        best,
        tuple(top),
        tested,
        tested >= budget_int,
        checkpoint_path=checkpoint_path,
        progress_path=progress_path,
        seed_checkpoint_path=seed_checkpoint_path,
        repaired_backrefs=repaired_backrefs,
        png_prefix_hits=png_prefix_hits,
        best_prefix_rows=best_prefix_rows,
        reached_depth=reached_depth,
        strategy=strategy,
        reason=reason,
        source_hash=source_hash,
    )


def probe_idat_dynamic_huffman_png_oracle_solver(
    data: bytes,
    *,
    budget: int = HUFFMAN_ORACLE_DEFAULT_BUDGET,
    max_depth: int = HUFFMAN_ORACLE_DEFAULT_MAX_DEPTH,
    beam_width: int = HUFFMAN_ORACLE_DEFAULT_WIDTH,
    top_candidates: int = HUFFMAN_ORACLE_DEFAULT_TOP_CANDIDATES,
    checkpoint_path: str = "",
    progress_path: str = "",
    seed_candidates: Iterable[IdatDeepBeamCandidate] = (),
    progress: QueueProgressCallback | None = None,
) -> IdatHuffmanOracleSolverResult:
    strategy = "dynamic-huffman-png-oracle"
    before = idat.analyze_idat_stream(data)
    if not before.supported or before.complete:
        return IdatHuffmanOracleSolverResult(before, None, (), 0, False, strategy=strategy, reason=before.reason)
    try:
        chunks, root_stream = _all_chunks_and_idat_stream(data)
    except png.PngFormatError as exc:
        return IdatHuffmanOracleSolverResult(before, None, (), 0, False, strategy=strategy, reason=str(exc))
    source_hash = _stream_state_key(root_stream)
    original_idat_count = sum(1 for chunk in chunks if chunk.chunk_type == b"IDAT")
    progress_state = huffman_oracle_progress_state(data, progress_path)
    if (
        progress_state.available
        and progress_state.source_matches
        and progress_state.exhausted
        and progress_state.budget >= int(budget)
    ):
        _before, _chunks, _stream, _source_hash, _count, top = _load_frontier_candidates_for_progress(
            data,
            checkpoint_path,
            top_candidates=top_candidates,
            max_operation_depth=max_depth,
        )
        best = _frontier_best_candidate(before, top)
        return IdatHuffmanOracleSolverResult(
            before,
            best,
            top,
            progress_state.tested,
            True,
            checkpoint_path=checkpoint_path,
            progress_path=progress_path,
            seed_count=0,
            strategy=strategy,
            reason="huffman oracle already exhausted for this source/budget",
            source_hash=source_hash,
        )

    root = _frontier_root_candidate(
        data=data,
        stream=root_stream,
        before=before,
        original_idat_count=original_idat_count,
    )
    frontier: list[IdatDeepBeamCandidate] = [root]
    top: list[IdatDeepBeamCandidate] = []
    visited = {_stream_state_key(root_stream)}
    tested = 0
    next_state_id = 1
    valid_headers = 0
    png_plausible = 0
    budget_exhausted = False
    last_checkpoint_at = 0
    reached_depth = 0

    def remember(candidate: IdatDeepBeamCandidate) -> None:
        nonlocal top, valid_headers, png_plausible
        key = _stream_state_key(candidate.stream)
        if key in visited:
            return
        visited.add(key)
        if _candidate_dynamic_header_valid(candidate):
            valid_headers += 1
        if _candidate_png_plausible(candidate):
            png_plausible += 1
        top = list(_deep_beam_ranked_unique(itertools.chain(top, (candidate,)), limit=top_candidates))

    seed_count = 0
    for seed in seed_candidates:
        if not getattr(seed, "stream", b""):
            continue
        key = _stream_state_key(seed.stream)
        if key in visited:
            continue
        visited.add(key)
        seed_count += 1
        top = list(_deep_beam_ranked_unique(itertools.chain(top, (seed,)), limit=top_candidates))
        if _huffman_oracle_accepts(root, seed):
            frontier.append(seed)

    frontier = list(
        sorted(
            _deep_beam_ranked_unique(frontier, limit=max(1, int(beam_width))),
            key=lambda item: _huffman_oracle_rank(item.stream, item.after),
            reverse=True,
        )
    )[: max(1, int(beam_width))]

    if progress is not None:
        progress(strategy, 0, int(budget))

    for depth in range(1, max(1, int(max_depth)) + 1):
        reached_depth = depth
        next_frontier: list[IdatDeepBeamCandidate] = []
        for parent in frontier:
            if tested >= int(budget):
                budget_exhausted = True
                break
            sub_items, sub_tested = _huffman_oracle_subprobes(parent.data, budget_left=max(0, int(budget) - tested))
            tested = min(int(budget), tested + sub_tested)
            for deflate_candidate, kind in sub_items:
                if tested >= int(budget):
                    budget_exhausted = True
                successor = _deep_beam_candidate_from_deflate_candidate(
                    parent,
                    deflate_candidate,
                    before=before,
                    state_id=next_state_id,
                    original_idat_count=original_idat_count,
                    kind=kind,
                )
                if successor is None:
                    continue
                next_state_id += 1
                if not _huffman_oracle_accepts(parent, successor):
                    continue
                remember(successor)
                next_frontier.append(successor)
            if progress is not None:
                progress(strategy, tested, int(budget))
            if checkpoint_path and top and tested - last_checkpoint_at >= HUFFMAN_ORACLE_CHECKPOINT_EVERY:
                for item in top:
                    _append_frontier_checkpoint(
                        checkpoint_path,
                        item,
                        source_hash=source_hash,
                        source_stream=root_stream,
                    )
                last_checkpoint_at = tested
        if budget_exhausted:
            break
        frontier = list(_deep_beam_ranked_unique(next_frontier, limit=beam_width))
        if not frontier:
            break

    if checkpoint_path:
        for item in top:
            _append_frontier_checkpoint(
                checkpoint_path,
                item,
                source_hash=source_hash,
                source_stream=root_stream,
            )
    best = _frontier_best_candidate(before, top)
    budget_limit_hit = budget_exhausted or tested >= int(budget)
    frontier_exhausted = not frontier
    stop_reason = _bounded_route_stop_reason(
        tested=tested,
        budget=int(budget),
        budget_exhausted=budget_limit_hit,
        frontier_exhausted=frontier_exhausted,
        depth_limit_reached=not budget_limit_hit and not frontier_exhausted,
    )
    reason = (
        "stop=%s; depth=%s; states=%s; valid_headers=%s; png_plausible=%s; top=%s"
        % (stop_reason, reached_depth, len(visited), valid_headers, png_plausible, len(top))
    )
    _write_frontier_progress(
        progress_path,
        source_hash=source_hash,
        tested=tested,
        budget=budget,
        best=best,
        top_count=len(top),
        exhausted=True,
        reason=reason,
        strategy=strategy,
        extra={
            "valid_headers": int(valid_headers),
            "png_plausible": int(png_plausible),
            "reached_depth": int(reached_depth),
            "seed_count": int(seed_count),
        },
    )
    if progress is not None:
        progress(strategy, min(tested, int(budget)), int(budget))
    return IdatHuffmanOracleSolverResult(
        before,
        best,
        tuple(top),
        tested,
        budget_limit_hit,
        checkpoint_path=checkpoint_path,
        progress_path=progress_path,
        valid_headers=valid_headers,
        png_plausible=png_plausible,
        reached_depth=reached_depth,
        seed_count=seed_count,
        strategy=strategy,
        reason=reason,
        source_hash=source_hash,
    )


def _periodic_model_classes(model: dict[str, object]) -> tuple[int, ...]:
    raw = model.get("idat_classes_mod8", ())
    if not isinstance(raw, list | tuple):
        return ()
    classes: list[int] = []
    for item in raw:
        try:
            classes.append(int(item) % 8)
        except (TypeError, ValueError):
            continue
    return tuple(dict.fromkeys(classes))


def _crc_periodic_target_chunks(
    chunks: tuple[png.PngChunk, ...],
    before: idat.IdatStreamAnalysis,
    model: dict[str, object],
) -> tuple[png.PngChunk, ...]:
    idat_chunks = tuple(chunk for chunk in chunks if chunk.chunk_type == b"IDAT")
    classes = set(_periodic_model_classes(model))
    preferred = _dynamic_crc_guided_target_chunk(chunks, before)

    def priority(item: tuple[int, png.PngChunk]) -> tuple[int, int]:
        index, chunk = item
        if preferred is not None and chunk.offset == preferred.offset:
            return (0, index)
        if classes and (index % 8) in classes and chunk.crc != chunk.computed_crc:
            return (1, index)
        if chunk.crc != chunk.computed_crc:
            return (2, index)
        return (3, index)

    return tuple(chunk for _index, chunk in sorted(enumerate(idat_chunks), key=priority) if chunk.crc != chunk.computed_crc)


def _crc_periodic_stream_offsets(
    root_stream: bytes,
    model: dict[str, object],
    diagnostic: IdatLocalDeflateDiagnostic | None,
    *,
    target_stream_start: int,
    target_stream_end: int,
) -> tuple[int, ...]:
    offsets = list(_periodic_model_offsets(diagnostic, len(root_stream)))
    for focus in DEEP_BEAM_FOCUS_OFFSETS:
        offsets.append(int(target_stream_start) + int(focus))
    if diagnostic is not None and diagnostic.stream_offset is not None:
        center = int(diagnostic.stream_offset)
        offsets.extend(range(max(0, center - 64), min(len(root_stream), center + 65)))

    model_chunks = model.get("idat_chunks", ())
    classes = set(_periodic_model_classes(model))
    if isinstance(model_chunks, list | tuple) and classes:
        for item in model_chunks:
            if not isinstance(item, dict):
                continue
            try:
                index = int(item.get("index", -1))
                length = int(item.get("length", 0))
            except (TypeError, ValueError):
                continue
            if index % 8 not in classes:
                continue
            for focus in DEEP_BEAM_FOCUS_OFFSETS:
                if focus < length:
                    offsets.append(int(target_stream_start) + int(focus))

    return tuple(
        dict.fromkeys(
            int(offset)
            for offset in offsets
            if int(target_stream_start) <= int(offset) < int(target_stream_end)
        )
    )


def _crc_periodic_payload_bit_groups(
    payload: bytes,
    stream_offsets: tuple[int, ...],
    *,
    target_stream_start: int,
    xors: tuple[int, ...],
    max_group_bits: int,
) -> tuple[tuple[str, tuple[int, ...]], ...]:
    xor_bits = tuple(
        dict.fromkeys(
            bit
            for xor in sorted(xors, key=lambda value: (int(value).bit_count(), int(value)))
            if 0 < int(xor).bit_count() <= 4
            for bit in range(8)
            if int(xor) & (1 << bit)
        )
    )
    if not xor_bits:
        xor_bits = tuple(range(8))
    groups: list[tuple[str, tuple[int, ...]]] = []
    seen: set[tuple[int, ...]] = set()
    group_width = max(8, min(32, int(max_group_bits)))
    for offset in stream_offsets:
        local = int(offset) - int(target_stream_start)
        if local < 0 or local >= len(payload):
            continue
        bits = tuple(local * 8 + bit for bit in xor_bits if local * 8 + bit < len(payload) * 8)
        if not bits or bits in seen:
            continue
        seen.add(bits)
        groups.append(("offset-0x%x" % offset, bits[:group_width]))

    for index in range(0, len(stream_offsets), 4):
        window = stream_offsets[index : index + 4]
        bits: list[int] = []
        for offset in window:
            local = int(offset) - int(target_stream_start)
            if local < 0 or local >= len(payload):
                continue
            bits.extend(local * 8 + bit for bit in xor_bits)
        key = tuple(dict.fromkeys(bit for bit in bits if 0 <= bit < len(payload) * 8))[:group_width]
        if key and key not in seen:
            seen.add(key)
            groups.append(("window-%s" % (index // 4), key))
    return tuple(groups)


def probe_idat_crc_periodic_payload_solver(
    data: bytes,
    *,
    convoy_model_path: str = "",
    budget: int = CRC_PERIODIC_DEFAULT_BUDGET,
    max_edits: int = CRC_PERIODIC_DEFAULT_MAX_EDITS,
    top_candidates: int = CRC_PERIODIC_DEFAULT_TOP_CANDIDATES,
    checkpoint_path: str = "",
    progress_path: str = "",
    progress: QueueProgressCallback | None = None,
) -> IdatCrcPeriodicPayloadSolverResult:
    strategy = "crc-periodic-payload"
    before = idat.analyze_idat_stream(data)
    if not before.supported or before.complete:
        return IdatCrcPeriodicPayloadSolverResult(before, None, (), 0, False, strategy=strategy, reason=before.reason)
    try:
        chunks, root_stream = _all_chunks_and_idat_stream(data)
    except png.PngFormatError as exc:
        return IdatCrcPeriodicPayloadSolverResult(before, None, (), 0, False, strategy=strategy, reason=str(exc))
    source_hash = _stream_state_key(root_stream)
    original_idat_count = sum(1 for chunk in chunks if chunk.chunk_type == b"IDAT")
    model, model_error = _load_idat_convoy_model(convoy_model_path)
    if model is None:
        return IdatCrcPeriodicPayloadSolverResult(
            before,
            None,
            (),
            0,
            False,
            model_path=convoy_model_path,
            strategy=strategy,
            reason=model_error,
            source_hash=source_hash,
        )
    if str(model.get("convoy_stream_hash") or "") != source_hash:
        return IdatCrcPeriodicPayloadSolverResult(
            before,
            None,
            (),
            0,
            False,
            model_path=convoy_model_path,
            strategy=strategy,
            reason="convoy model hash does not match current IDAT stream",
            source_hash=source_hash,
        )

    progress_state = crc_periodic_progress_state(data, progress_path)
    if (
        progress_state.available
        and progress_state.source_matches
        and progress_state.exhausted
        and progress_state.budget >= int(budget)
    ):
        _before, _chunks, _stream, _source_hash, _count, top = _load_frontier_candidates_for_progress(
            data,
            checkpoint_path,
            top_candidates=top_candidates,
            max_operation_depth=max(1, int(max_edits)),
        )
        best = _frontier_best_candidate(before, top)
        return IdatCrcPeriodicPayloadSolverResult(
            before,
            best,
            top,
            progress_state.tested,
            True,
            checkpoint_path=checkpoint_path,
            progress_path=progress_path,
            model_path=convoy_model_path,
            strategy=strategy,
            reason="crc-periodic solver already exhausted for this source/budget",
            source_hash=source_hash,
        )

    diagnostic = idat_local_deflate_diagnostic(data, analysis=before)
    idat_chunks = tuple(chunk for chunk in chunks if chunk.chunk_type == b"IDAT")
    targets = _crc_periodic_target_chunks(chunks, before, model)
    root = _frontier_root_candidate(
        data=data,
        stream=root_stream,
        before=before,
        original_idat_count=original_idat_count,
    )
    xors = _periodic_model_ints(model, "xors")
    max_group_bits = max(8, min(32, int(max_edits) * 8))
    tested = 0
    next_state_id = 1
    crc_hits = 0
    png_plausible = 0
    budget_exhausted = False
    top: list[IdatDeepBeamCandidate] = []
    visited = {_stream_state_key(root_stream)}
    last_checkpoint_at = 0

    if progress is not None:
        progress(strategy, 0, int(budget))

    def remember(candidate: IdatDeepBeamCandidate) -> None:
        nonlocal top, png_plausible
        key = _stream_state_key(candidate.stream)
        if key in visited:
            return
        visited.add(key)
        if _candidate_png_plausible(candidate):
            png_plausible += 1
        top = list(_deep_beam_ranked_unique(itertools.chain(top, (candidate,)), limit=top_candidates))

    for target in targets:
        if tested >= int(budget):
            budget_exhausted = True
            break
        target_range = _idat_stream_range_for_chunk_offset(chunks, target.offset)
        if target_range is None:
            continue
        target_stream_start, target_stream_end = target_range
        payload = bytes(target.data)
        offsets = _crc_periodic_stream_offsets(
            root_stream,
            model,
            diagnostic,
            target_stream_start=target_stream_start,
            target_stream_end=target_stream_end,
        )
        groups = _crc_periodic_payload_bit_groups(
            payload,
            offsets,
            target_stream_start=target_stream_start,
            xors=xors,
            max_group_bits=max_group_bits,
        )
        for label, payload_bits in groups:
            if tested >= int(budget):
                budget_exhausted = True
                break
            solutions = _crc_guided_solutions_for_payload_bits(
                payload,
                payload_bits,
                int(target.crc),
                max_solutions=16,
            )
            tested += 1
            if progress is not None and (tested == 1 or tested % 100 == 0):
                progress(strategy, min(tested, int(budget)), int(budget))
            for solution_payload_bits in solutions:
                if tested >= int(budget):
                    budget_exhausted = True
                    break
                if len(solution_payload_bits) > max(1, int(max_edits)) * 8:
                    continue
                fixed_payload = _flip_payload_bits(payload, solution_payload_bits)
                if fixed_payload is None or fixed_payload == payload:
                    continue
                global_bits = tuple(int(target_stream_start) * 8 + bit for bit in solution_payload_bits)
                deflate_candidate = _crc_guided_candidate_from_payload(
                    data,
                    before=before,
                    chunks=chunks,
                    idat_chunks=idat_chunks,
                    target_chunk=target,
                    target_stream_start=target_stream_start,
                    original_payload=payload,
                    payload=fixed_payload,
                    global_bit_offsets=global_bits,
                    edit_kind="crc-periodic-%s" % label,
                )
                tested += 1
                if deflate_candidate is None:
                    continue
                crc_hits += 1
                successor = _deep_beam_candidate_from_deflate_candidate(
                    root,
                    deflate_candidate,
                    before=before,
                    state_id=next_state_id,
                    original_idat_count=original_idat_count,
                    kind="crc-periodic-%s" % label,
                )
                if successor is None:
                    continue
                next_state_id += 1
                remember(successor)
                if checkpoint_path and top and tested - last_checkpoint_at >= CRC_PERIODIC_CHECKPOINT_EVERY:
                    for item in top:
                        _append_frontier_checkpoint(
                            checkpoint_path,
                            item,
                            source_hash=source_hash,
                            source_stream=root_stream,
                        )
                    last_checkpoint_at = tested
            if budget_exhausted:
                break

    if checkpoint_path:
        for item in top:
            _append_frontier_checkpoint(
                checkpoint_path,
                item,
                source_hash=source_hash,
                source_stream=root_stream,
            )
    best = _frontier_best_candidate(before, top)
    budget_limit_hit = budget_exhausted or tested >= int(budget)
    candidate_pool_exhausted = not budget_limit_hit
    stop_reason = _bounded_route_stop_reason(
        tested=tested,
        budget=int(budget),
        budget_exhausted=budget_limit_hit,
        candidate_pool_exhausted=candidate_pool_exhausted,
    )
    reason = "stop=%s; targets=%s; tested=%s; crc_hits=%s; png_plausible=%s; top=%s" % (
        stop_reason,
        len(targets),
        tested,
        crc_hits,
        png_plausible,
        len(top),
    )
    _write_frontier_progress(
        progress_path,
        source_hash=source_hash,
        tested=tested,
        budget=budget,
        best=best,
        top_count=len(top),
        exhausted=True,
        reason=reason,
        strategy=strategy,
        extra={
            "model_path": convoy_model_path,
            "crc_hits": int(crc_hits),
            "png_plausible": int(png_plausible),
        },
    )
    if progress is not None:
        progress(strategy, min(tested, int(budget)), int(budget))
    return IdatCrcPeriodicPayloadSolverResult(
        before,
        best,
        tuple(top),
        tested,
        budget_limit_hit,
        checkpoint_path=checkpoint_path,
        progress_path=progress_path,
        model_path=convoy_model_path,
        crc_hits=crc_hits,
        png_plausible=png_plausible,
        strategy=strategy,
        reason=reason,
        source_hash=source_hash,
    )


def _crc32_idat_payload(payload: bytes) -> int:
    return zlib.crc32(b"IDAT" + payload) & 0xFFFFFFFF


def _crc_match_count_for_stream(
    stream: bytes,
    ranges: tuple[tuple[int, png.PngChunk, int, int], ...],
) -> int:
    matches = 0
    for _index, chunk, start, end in ranges:
        payload = stream[start:end]
        if len(payload) == chunk.length and _crc32_idat_payload(payload) == int(chunk.crc):
            matches += 1
    return matches


def _global_crc_residue_rules(
    root_stream: bytes,
    chunks: tuple[png.PngChunk, ...],
    model: dict[str, object],
    diagnostic: IdatLocalDeflateDiagnostic | None,
    *,
    max_rules: int,
) -> tuple[dict[str, object], ...]:
    xors = sorted(_periodic_model_ints(model, "xors"), key=lambda value: (int(value).bit_count(), int(value)))
    if not xors:
        xors = tuple(1 << bit for bit in range(8))
    ranges = _idat_stream_ranges_by_index(chunks)
    base_offsets = _periodic_model_offsets(diagnostic, len(root_stream))
    base_offsets = tuple(dict.fromkeys(tuple(DEEP_BEAM_FOCUS_OFFSETS) + base_offsets + tuple(range(0, min(0x120, len(root_stream))))))
    classes = _periodic_model_classes(model) or tuple(range(8))
    rules: list[dict[str, object]] = []
    seen: set[tuple[int, int, int]] = set()
    for class_mod8 in classes:
        for local_offset in base_offsets:
            affected = [
                (index, chunk, start, end)
                for index, chunk, start, end in ranges
                if index % 8 == int(class_mod8) % 8 and 0 <= int(local_offset) < chunk.length
            ]
            if len(affected) < 2:
                continue
            for xor in xors:
                key = (int(class_mod8) % 8, int(local_offset), int(xor) & 0xFF)
                if key in seen:
                    continue
                seen.add(key)
                before_matches = sum(
                    1
                    for _index, chunk, start, end in affected
                    if _crc32_idat_payload(root_stream[start:end]) == int(chunk.crc)
                )
                after_matches = 0
                for _index, chunk, start, end in affected:
                    stream_offset = start + int(local_offset)
                    payload = bytearray(root_stream[start:end])
                    payload[int(local_offset)] ^= int(xor) & 0xFF
                    if _crc32_idat_payload(bytes(payload)) == int(chunk.crc):
                        after_matches += 1
                explained = after_matches - before_matches
                residue_votes = 0
                for _index, chunk, start, end in affected:
                    computed = _crc32_idat_payload(root_stream[start:end])
                    if (computed ^ int(chunk.crc)) & int(xor):
                        residue_votes += 1
                rules.append(
                    {
                        "class_mod8": int(class_mod8) % 8,
                        "local_offset": int(local_offset),
                        "xor": int(xor) & 0xFF,
                        "affected": len(affected),
                        "crc_hits": int(after_matches),
                        "explained": int(max(0, explained)),
                        "residue_votes": int(residue_votes),
                    }
                )
    rules.sort(
        key=lambda item: (
            int(item.get("crc_hits", 0)),
            int(item.get("explained", 0)),
            int(item.get("residue_votes", 0)),
            int(item.get("affected", 0)),
            -int(item.get("local_offset", 0)),
        ),
        reverse=True,
    )
    return tuple(rules[: max(1, int(max_rules)) * 256])


def _apply_global_crc_rule(
    stream: bytes,
    chunks: tuple[png.PngChunk, ...],
    rule: dict[str, object],
) -> tuple[bytes | None, IdatDeepBeamOperation | None, int]:
    try:
        class_mod8 = int(rule.get("class_mod8", 0)) % 8
        local_offset = int(rule.get("local_offset", -1))
        xor = int(rule.get("xor", 0)) & 0xFF
    except (TypeError, ValueError):
        return None, None, 0
    if local_offset < 0 or not xor:
        return None, None, 0
    mutated = bytearray(stream)
    bit_offsets: list[int] = []
    first_offset: int | None = None
    affected = 0
    for index, chunk, start, _end in _idat_stream_ranges_by_index(chunks):
        if index % 8 != class_mod8 or local_offset >= chunk.length:
            continue
        stream_offset = start + local_offset
        if stream_offset >= len(mutated):
            continue
        if first_offset is None:
            first_offset = stream_offset
        mutated[stream_offset] ^= xor
        affected += 1
        bit_offsets.extend(stream_offset * 8 + bit for bit in range(8) if xor & (1 << bit))
    if affected <= 0 or bytes(mutated) == stream:
        return None, None, 0
    operation = IdatDeepBeamOperation(
        "global-crc-residue-xor",
        int(first_offset or 0),
        b"",
        bytes((xor,)),
        tuple(bit_offsets),
    )
    return bytes(mutated), operation, affected


def probe_idat_global_crc_residue_solver(
    data: bytes,
    *,
    convoy_model_path: str = "",
    budget: int = GLOBAL_CRC_RESIDUE_DEFAULT_BUDGET,
    max_rules: int = GLOBAL_CRC_RESIDUE_DEFAULT_MAX_RULES,
    top_candidates: int = GLOBAL_CRC_RESIDUE_DEFAULT_TOP_CANDIDATES,
    checkpoint_path: str = "",
    progress_path: str = "",
    progress: QueueProgressCallback | None = None,
) -> IdatGlobalCrcResidueSolverResult:
    strategy = "global-crc-residue"
    before = idat.analyze_idat_stream(data)
    if not before.supported or before.complete:
        return IdatGlobalCrcResidueSolverResult(before, None, (), 0, False, strategy=strategy, reason=before.reason)
    try:
        chunks, root_stream = _all_chunks_and_idat_stream(data)
    except png.PngFormatError as exc:
        return IdatGlobalCrcResidueSolverResult(before, None, (), 0, False, strategy=strategy, reason=str(exc))
    source_hash = _stream_state_key(root_stream)
    original_idat_count = sum(1 for chunk in chunks if chunk.chunk_type == b"IDAT")
    model, model_error = _load_idat_convoy_model(convoy_model_path)
    if model is None:
        return IdatGlobalCrcResidueSolverResult(before, None, (), 0, False, model_path=convoy_model_path, strategy=strategy, reason=model_error, source_hash=source_hash)
    if str(model.get("convoy_stream_hash") or "") != source_hash:
        return IdatGlobalCrcResidueSolverResult(
            before,
            None,
            (),
            0,
            False,
            model_path=convoy_model_path,
            strategy=strategy,
            reason="convoy model hash does not match current IDAT stream",
            source_hash=source_hash,
        )
    progress_state = global_crc_residue_progress_state(data, progress_path)
    if progress_state.available and progress_state.source_matches and progress_state.exhausted and progress_state.budget >= int(budget):
        _before, _chunks, _stream, _source_hash, _count, top = _load_frontier_candidates_for_progress(
            data,
            checkpoint_path,
            top_candidates=top_candidates,
            max_operation_depth=max(1, int(max_rules)),
        )
        best = _frontier_best_candidate(before, top)
        return IdatGlobalCrcResidueSolverResult(
            before,
            best,
            top,
            progress_state.tested,
            True,
            checkpoint_path=checkpoint_path,
            progress_path=progress_path,
            model_path=convoy_model_path,
            strategy=strategy,
            reason="global CRC residue solver already exhausted for this source/budget",
            source_hash=source_hash,
        )

    diagnostic = idat_local_deflate_diagnostic(data, analysis=before)
    rules = _global_crc_residue_rules(root_stream, chunks, model, diagnostic, max_rules=max_rules)
    root = _frontier_root_candidate(data=data, stream=root_stream, before=before, original_idat_count=original_idat_count)
    ranges = _idat_stream_ranges_by_index(chunks)
    top: list[IdatDeepBeamCandidate] = []
    visited = {_stream_state_key(root_stream)}
    tested = 0
    next_state_id = 1
    crc_hits = 0
    explained_chunks = 0
    png_plausible = 0
    budget_exhausted = False
    last_checkpoint_at = 0

    if progress is not None:
        progress(strategy, 0, int(budget))

    for rule in rules:
        if tested >= int(budget):
            budget_exhausted = True
            break
        stream, operation, affected = _apply_global_crc_rule(root_stream, chunks, rule)
        tested += 1
        if stream is None or operation is None:
            continue
        matches = _crc_match_count_for_stream(stream, ranges)
        crc_hits = max(crc_hits, matches)
        explained_chunks = max(explained_chunks, int(rule.get("explained", 0) or 0), matches)
        candidate = _frontier_candidate_from_stream(
            root,
            stream,
            operation,
            chunks=chunks,
            before=before,
            state_id=next_state_id,
            original_idat_count=original_idat_count,
            source_kind="candidate_from_global_crc_residue",
        )
        if candidate is None:
            continue
        next_state_id += 1
        key = _stream_state_key(candidate.stream)
        if key in visited:
            continue
        visited.add(key)
        if _candidate_png_plausible(candidate):
            png_plausible += 1
        top = list(_deep_beam_ranked_unique(itertools.chain(top, (candidate,)), limit=top_candidates))
        if checkpoint_path and top and tested - last_checkpoint_at >= GLOBAL_CRC_RESIDUE_CHECKPOINT_EVERY:
            for item in top:
                _append_frontier_checkpoint(checkpoint_path, item, source_hash=source_hash, source_stream=root_stream)
            last_checkpoint_at = tested
        if progress is not None and (tested == 1 or tested % 1000 == 0):
            progress(strategy, min(tested, int(budget)), int(budget))

    if checkpoint_path:
        for item in top:
            _append_frontier_checkpoint(checkpoint_path, item, source_hash=source_hash, source_stream=root_stream)
    best = _frontier_best_candidate(before, top)
    budget_limit_hit = budget_exhausted or tested >= int(budget)
    candidate_pool_exhausted = not budget_limit_hit
    stop_reason = _bounded_route_stop_reason(
        tested=tested,
        budget=int(budget),
        budget_exhausted=budget_limit_hit,
        candidate_pool_exhausted=candidate_pool_exhausted,
    )
    reason = "stop=%s; rules=%s; tested=%s; crc_hits=%s; explained_chunks=%s; png_plausible=%s; top=%s" % (
        stop_reason,
        len(rules),
        tested,
        crc_hits,
        explained_chunks,
        png_plausible,
        len(top),
    )
    _write_frontier_progress(
        progress_path,
        source_hash=source_hash,
        tested=tested,
        budget=budget,
        best=best,
        top_count=len(top),
        exhausted=True,
        reason=reason,
        strategy=strategy,
        extra={
            "model_path": convoy_model_path,
            "rules": int(len(rules)),
            "explained_chunks": int(explained_chunks),
            "crc_hits": int(crc_hits),
            "png_plausible": int(png_plausible),
        },
    )
    if progress is not None:
        progress(strategy, min(tested, int(budget)), int(budget))
    return IdatGlobalCrcResidueSolverResult(
        before,
        best,
        tuple(top),
        tested,
        budget_limit_hit,
        checkpoint_path=checkpoint_path,
        progress_path=progress_path,
        model_path=convoy_model_path,
        rules=len(rules),
        explained_chunks=explained_chunks,
        crc_hits=crc_hits,
        png_plausible=png_plausible,
        strategy=strategy,
        reason=reason,
        source_hash=source_hash,
    )


def _read_lsb_bit_window(stream: bytes, bit_offset: int, width: int) -> int | None:
    bit_offset = int(bit_offset)
    width = int(width)
    if bit_offset < 0 or width < 0 or bit_offset + width > len(stream) * 8:
        return None
    value = 0
    for index in range(width):
        absolute = bit_offset + index
        value |= ((stream[absolute // 8] >> (absolute % 8)) & 1) << index
    return value


def png_erasure_unfilter_preview(
    raw: bytes,
    analysis: idat.IdatStreamAnalysis,
    path: str,
    *,
    max_rows: int = 64,
) -> tuple[int, int]:
    if not path or not raw:
        return 0, 0
    width = int(getattr(analysis, "width", 0) or 0)
    height = int(getattr(analysis, "height", 0) or 0)
    bit_depth = int(getattr(analysis, "bit_depth", 0) or 0)
    color_type = int(getattr(analysis, "color_type", -1) or -1)
    scanline_size = int(getattr(analysis, "scanline_size", 0) or 0)
    if width <= 0 or height <= 0 or bit_depth != 8 or color_type not in (2, 6) or scanline_size <= 1:
        return 0, 0
    channels = 4 if color_type == 6 else 3
    row_bytes = width * channels
    rows = min(max_rows, height, len(raw) // scanline_size)
    if rows <= 0:
        return 0, 0
    previous = bytearray(row_bytes)
    pixels = bytearray()
    known_pixels = 0

    for row in range(rows):
        start = row * scanline_size
        filter_type = raw[start]
        encoded = bytearray(raw[start + 1 : start + 1 + row_bytes])
        if len(encoded) < row_bytes or filter_type not in (0, 1, 2, 3, 4):
            break
        decoded = bytearray(row_bytes)
        for index, value in enumerate(encoded):
            left = decoded[index - channels] if index >= channels else 0
            up = previous[index]
            up_left = previous[index - channels] if index >= channels else 0
            if filter_type == 0:
                predictor = 0
            elif filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = up
            elif filter_type == 3:
                predictor = (left + up) // 2
            else:
                p = left + up - up_left
                pa = abs(p - left)
                pb = abs(p - up)
                pc = abs(p - up_left)
                predictor = left if pa <= pb and pa <= pc else up if pb <= pc else up_left
            decoded[index] = (value + predictor) & 0xFF
        if channels == 4:
            pixels.extend(decoded[index] for index in range(row_bytes) if index % 4 != 3)
        else:
            pixels.extend(decoded)
        known_pixels += width
        previous = decoded

    if known_pixels <= 0:
        return 0, 0
    try:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        header = ("P6\n%s %s\n255\n" % (width, known_pixels // width)).encode("ascii")
        tmp_path = _hidden_tmp_path(path)
        with open(tmp_path, "wb") as file:
            file.write(header)
            file.write(bytes(pixels))
        os.replace(tmp_path, path)
    except OSError:
        return known_pixels // width, known_pixels
    return known_pixels // width, known_pixels


def probe_deflate_resync_salvage(
    data: bytes,
    *,
    budget: int = DEFLATE_SALVAGE_DEFAULT_BUDGET,
    progress_path: str = "",
    preview_path: str = "",
    progress: QueueProgressCallback | None = None,
) -> DeflateResyncSalvageResult:
    strategy = "deflate-resync-salvage"
    before = idat.analyze_idat_stream(data)
    if not before.supported or before.complete:
        return DeflateResyncSalvageResult(before, (), strategy=strategy, reason=before.reason)
    try:
        _chunks, root_stream = _all_chunks_and_idat_stream(data)
    except png.PngFormatError as exc:
        return DeflateResyncSalvageResult(before, (), strategy=strategy, reason=str(exc))
    source_hash = _stream_state_key(root_stream)
    progress_state = deflate_salvage_progress_state(data, progress_path)
    if progress_state.available and progress_state.source_matches and progress_state.exhausted and progress_state.budget >= int(budget):
        return DeflateResyncSalvageResult(
            before,
            (),
            tested_candidates=progress_state.tested,
            budget_exhausted=True,
            progress_path=progress_path,
            strategy=strategy,
            reason="deflate salvage already exhausted for this source/budget",
            source_hash=source_hash,
        )
    start_bit = max(0, int(before.error_offset or 0) * 8)
    tested = 0
    anchors: list[int] = []
    if progress is not None:
        progress(strategy, 0, int(budget))
    for bit_offset in range(start_bit, len(root_stream) * 8 - 3):
        if tested >= int(budget):
            break
        tested += 1
        header = _read_lsb_bit_window(root_stream, bit_offset, 3)
        if header is None:
            continue
        btype = (header >> 1) & 0x03
        if btype in (1, 2):
            anchors.append(bit_offset)
            if len(anchors) >= 256:
                break
        if progress is not None and tested % 10_000 == 0:
            progress(strategy, min(tested, int(budget)), int(budget))

    raw_prefix = idat_partial_raw_prefix(root_stream, max_output=max(8192, int(before.scanline_size or 0) * 8))
    partial_rows = 0
    known_pixels = 0
    if raw_prefix.raw and preview_path:
        partial_rows, known_pixels = png_erasure_unfilter_preview(raw_prefix.raw, before, preview_path)
    reason = "anchors=%s; raw=%s; partial_rows=%s; known_pixels=%s" % (
        len(anchors),
        len(raw_prefix.raw),
        partial_rows,
        known_pixels,
    )
    _write_frontier_progress(
        progress_path,
        source_hash=source_hash,
        tested=tested,
        budget=budget,
        best=None,
        top_count=0,
        exhausted=True,
        reason=reason,
        strategy=strategy,
        extra={
            "anchors": [int(anchor) for anchor in anchors[:256]],
            "partial_rows": int(partial_rows),
            "known_pixels": int(known_pixels),
            "preview_path": preview_path if known_pixels else "",
        },
    )
    if progress is not None:
        progress(strategy, min(tested, int(budget)), int(budget))
    return DeflateResyncSalvageResult(
        before,
        tuple(anchors),
        partial_rows=partial_rows,
        known_pixels=known_pixels,
        preview_path=preview_path if known_pixels else "",
        tested_candidates=tested,
        budget_exhausted=tested >= int(budget),
        progress_path=progress_path,
        strategy=strategy,
        reason=reason,
        source_hash=source_hash,
    )


def _periodic_dynamic_successors(
    parent: IdatDeepBeamCandidate,
    *,
    before: idat.IdatStreamAnalysis,
    state_id_start: int,
    original_idat_count: int,
    budget_left: int,
) -> tuple[list[IdatDeepBeamCandidate], int]:
    successors: list[IdatDeepBeamCandidate] = []
    tested = 0
    next_state_id = int(state_id_start)
    if budget_left <= 0:
        return successors, tested

    semantic = probe_dynamic_huffman_semantic_candidates(
        parent.data,
        budget=min(4096, max(1, int(budget_left))),
        max_tokens=64,
    )
    tested += semantic.tested_candidates
    for candidate, kind in ((semantic.best, "periodic-semantic-token"), (semantic.diagnostic_best, "periodic-semantic-token-diagnostic")):
        successor = _deep_beam_candidate_from_deflate_candidate(
            parent,
            candidate,
            before=before,
            state_id=next_state_id,
            original_idat_count=original_idat_count,
            kind=kind,
        )
        if successor is not None:
            successors.append(successor)
            next_state_id += 1

    remaining = max(0, int(budget_left) - tested)
    if remaining <= 0:
        return successors, tested
    alphabet = probe_dynamic_huffman_alphabet_candidates(
        parent.data,
        budget=min(2048, remaining),
        max_fields=12,
    )
    tested += alphabet.tested_candidates
    for candidate, kind in ((alphabet.best, "periodic-alphabet"), (alphabet.diagnostic_best, "periodic-alphabet-diagnostic")):
        successor = _deep_beam_candidate_from_deflate_candidate(
            parent,
            candidate,
            before=before,
            state_id=next_state_id,
            original_idat_count=original_idat_count,
            kind=kind,
        )
        if successor is not None:
            successors.append(successor)
            next_state_id += 1
    return successors, tested


def probe_idat_periodic_corruption_model(
    data: bytes,
    *,
    convoy_model_path: str = "",
    budget: int = PERIODIC_MODEL_DEFAULT_BUDGET,
    max_depth: int = PERIODIC_MODEL_DEFAULT_MAX_DEPTH,
    top_candidates: int = PERIODIC_MODEL_DEFAULT_TOP_CANDIDATES,
    checkpoint_path: str = "",
    progress_path: str = "",
    progress: QueueProgressCallback | None = None,
) -> IdatPeriodicCorruptionModelResult:
    before = idat.analyze_idat_stream(data)
    strategy = "periodic-corruption-model"
    if not before.supported or before.complete:
        return IdatPeriodicCorruptionModelResult(before, None, (), 0, False, strategy=strategy, reason=before.reason)
    try:
        chunks, root_stream = _all_chunks_and_idat_stream(data)
    except png.PngFormatError as exc:
        return IdatPeriodicCorruptionModelResult(before, None, (), 0, False, strategy=strategy, reason=str(exc))
    source_hash = _stream_state_key(root_stream)
    original_idat_count = sum(1 for chunk in chunks if chunk.chunk_type == b"IDAT")
    model, model_error = _load_idat_convoy_model(convoy_model_path)
    if model is None:
        return IdatPeriodicCorruptionModelResult(
            before,
            None,
            (),
            0,
            False,
            checkpoint_path=checkpoint_path,
            progress_path=progress_path,
            model_path=convoy_model_path,
            strategy=strategy,
            reason=model_error,
            source_hash=source_hash,
        )
    if str(model.get("convoy_stream_hash") or "") != source_hash:
        return IdatPeriodicCorruptionModelResult(
            before,
            None,
            (),
            0,
            False,
            checkpoint_path=checkpoint_path,
            progress_path=progress_path,
            model_path=convoy_model_path,
            strategy=strategy,
            reason="convoy model hash does not match current IDAT stream",
            source_hash=source_hash,
        )

    progress_state = periodic_model_progress_state(data, progress_path)
    if progress_state.available and progress_state.source_matches and progress_state.exhausted:
        checkpoint_candidates, _visited, _next_state_id, _records = _load_deep_beam_checkpoint(
            checkpoint_path,
            source_hash=source_hash,
            source_stream=root_stream,
            chunks=chunks,
            before=before,
            original_idat_count=original_idat_count,
            candidate_limit=top_candidates,
            max_operation_depth=max_depth,
        )
        top = _deep_beam_ranked_unique(checkpoint_candidates, limit=top_candidates)
        best = next((candidate for candidate in top if is_material_improvement(before, candidate.after)), None)
        return IdatPeriodicCorruptionModelResult(
            before,
            best,
            tuple(top),
            progress_state.tested,
            True,
            checkpoint_path=checkpoint_path,
            progress_path=progress_path,
            model_path=convoy_model_path,
            strategy=strategy,
            reason="periodic model already exhausted for this source",
            source_hash=source_hash,
        )

    diagnostic = idat_local_deflate_diagnostic(data, analysis=before)
    offsets = _periodic_model_offsets(diagnostic, len(root_stream))
    operations = _periodic_operation_pool(root_stream, model, offsets)
    root = IdatDeepBeamCandidate(
        data=data,
        stream=root_stream,
        operations=(),
        before=before,
        after=before,
        state_id=0,
        parent_id=None,
        source_offsets=(),
        score=_deep_beam_score(
            before,
            root_stream,
            0,
            data=data,
            original_idat_count=original_idat_count,
        ),
    )
    tested = 0
    next_state_id = 1
    visited = {_stream_state_key(root_stream)}
    top: list[IdatDeepBeamCandidate] = []
    best: IdatDeepBeamCandidate | None = None
    frontier: list[IdatDeepBeamCandidate] = []
    budget_exhausted = False
    last_checkpoint_at = 0

    def remember(candidate: IdatDeepBeamCandidate) -> None:
        nonlocal best, top
        key = _stream_state_key(candidate.stream)
        if key in visited:
            return
        visited.add(key)
        top = list(_deep_beam_ranked_unique(itertools.chain(top, (candidate,)), limit=top_candidates))
        if is_material_improvement(before, candidate.after):
            if best is None or candidate.score > best.score:
                best = candidate

    for operation in operations:
        if tested >= int(budget):
            budget_exhausted = True
            break
        candidate = _periodic_candidate_from_operation(
            root,
            operation,
            chunks=chunks,
            before=before,
            state_id=next_state_id,
            original_idat_count=original_idat_count,
        )
        tested += 1
        if candidate is None:
            continue
        next_state_id += 1
        remember(candidate)
        frontier.append(candidate)
        if checkpoint_path and tested - last_checkpoint_at >= PERIODIC_MODEL_CHECKPOINT_EVERY:
            for item in top:
                _append_periodic_model_checkpoint(
                    checkpoint_path,
                    item,
                    source_hash=source_hash,
                    source_stream=root_stream,
                )
            last_checkpoint_at = tested
        if progress is not None and (tested == 1 or tested % 1000 == 0):
            progress(strategy, min(tested, int(budget)), int(budget))
        if best is not None and best.after.complete:
            break

    depth = 2
    frontier = list(_deep_beam_ranked_unique(frontier, limit=min(top_candidates, 16)))
    while depth <= max(1, int(max_depth)) and frontier and tested < int(budget):
        next_frontier: list[IdatDeepBeamCandidate] = []
        for parent in frontier:
            if tested >= int(budget):
                budget_exhausted = True
                break
            successors, sub_tested = _periodic_dynamic_successors(
                parent,
                before=before,
                state_id_start=next_state_id,
                original_idat_count=original_idat_count,
                budget_left=max(0, int(budget) - tested),
            )
            tested += min(sub_tested, max(0, int(budget) - tested))
            next_state_id += len(successors)
            for candidate in successors:
                key = _stream_state_key(candidate.stream)
                if key in visited:
                    continue
                next_frontier.append(candidate)
                remember(candidate)
            if progress is not None:
                progress(strategy, min(tested, int(budget)), int(budget))
            if best is not None and best.after.complete:
                break
        if best is not None and best.after.complete:
            break
        frontier = list(_deep_beam_ranked_unique(next_frontier, limit=min(top_candidates, 16)))
        depth += 1

    if checkpoint_path:
        for item in top:
            _append_periodic_model_checkpoint(
                checkpoint_path,
                item,
                source_hash=source_hash,
                source_stream=root_stream,
            )
    exhausted = budget_exhausted or tested >= int(budget) or not operations
    if progress_path:
        _write_periodic_model_progress(
            progress_path,
            source_hash=source_hash,
            model_path=convoy_model_path,
            tested=tested,
            budget=budget,
            best=best,
            top_count=len(top),
            exhausted=True,
            reason="model_offsets=%s; operations=%s; top=%s" % (len(offsets), len(operations), len(top)),
        )
    if progress is not None:
        progress(strategy, min(tested, int(budget)), int(budget))
    reason = (
        "model_offsets=%s; operations=%s; tested=%s; top=%s; best=%s; source=%s"
        % (len(offsets), len(operations), tested, len(top), "yes" if best is not None else "no", source_hash)
    )
    return IdatPeriodicCorruptionModelResult(
        before,
        best,
        tuple(top),
        tested,
        exhausted,
        checkpoint_path=checkpoint_path,
        progress_path=progress_path,
        model_path=convoy_model_path,
        strategy=strategy,
        reason=reason,
        source_hash=source_hash,
    )


def _idat_stream_ranges_by_index(chunks: tuple[png.PngChunk, ...]) -> tuple[tuple[int, png.PngChunk, int, int], ...]:
    ranges: list[tuple[int, png.PngChunk, int, int]] = []
    stream_offset = 0
    index = 0
    for chunk in chunks:
        if chunk.chunk_type != b"IDAT":
            continue
        start = stream_offset
        end = start + chunk.length
        ranges.append((index, chunk, start, end))
        stream_offset = end
        index += 1
    return tuple(ranges)


def _idat_local_offset_for_stream_offset(
    chunks: tuple[png.PngChunk, ...],
    stream_offset: int | None,
) -> int | None:
    if stream_offset is None:
        return None
    offset = int(stream_offset)
    for _index, _chunk, start, end in _idat_stream_ranges_by_index(chunks):
        if start <= offset < end:
            return offset - start
    return None


def _model_repair_records(model: dict[str, object]) -> tuple[dict[str, object], ...]:
    records = model.get("byte_repairs", ())
    if not isinstance(records, list | tuple):
        return ()
    return tuple(item for item in records if isinstance(item, dict))


def _affine_rules_from_model(model: dict[str, object]) -> tuple[dict[str, object], ...]:
    groups: dict[tuple[object, ...], list[tuple[int, int, int]]] = {}
    for record in _model_repair_records(model):
        try:
            idat_index = int(record.get("idat_index"))
            xor_value = int(record.get("xor", 0)) & 0xFF
            delta_value = int(record.get("delta", 0)) & 0xFF
        except (TypeError, ValueError):
            continue
        key = (
            record.get("field"),
            record.get("field_index"),
            record.get("idat_class_mod8"),
        )
        groups.setdefault(key, []).append((idat_index, xor_value, delta_value))

    rules: list[dict[str, object]] = []
    seen: set[tuple[object, ...]] = set()
    for key, observations in groups.items():
        observations = sorted(observations)
        for mode, value_index in (("xor", 1), ("delta", 2)):
            values = [(obs[0], obs[value_index]) for obs in observations]
            values = [(index, value) for index, value in values if value]
            if not values:
                continue
            if len(values) >= 2:
                first_index, first_value = values[0]
                second_index, second_value = values[1]
                denominator = max(1, second_index - first_index)
                stride = ((second_value - first_value) // denominator) & 0xFF
                base = (first_value - stride * first_index) & 0xFF
            else:
                first_index, first_value = values[0]
                stride = 0
                base = first_value & 0xFF
            rule_key = key + (mode, base, stride)
            if rule_key in seen:
                continue
            seen.add(rule_key)
            rules.append(
                {
                    "field": key[0],
                    "field_index": key[1],
                    "idat_class_mod8": key[2],
                    "mode": mode,
                    "base": int(base) & 0xFF,
                    "stride": int(stride) & 0xFF,
                    "observations": len(values),
                }
            )

    for mode, key_name in (("xor", "xors"), ("delta", "deltas")):
        for value in _periodic_model_ints(model, key_name):
            rule_key = ("global", mode, value)
            if rule_key in seen:
                continue
            seen.add(rule_key)
            rules.append(
                {
                    "field": "global",
                    "field_index": None,
                    "idat_class_mod8": None,
                    "mode": mode,
                    "base": int(value) & 0xFF,
                    "stride": 0,
                    "observations": 1,
                }
            )
    return tuple(rules)


def _affine_rule_value(rule: dict[str, object], occurrence: int) -> int:
    try:
        base = int(rule.get("base", 0)) & 0xFF
        stride = int(rule.get("stride", 0)) & 0xFF
    except (TypeError, ValueError):
        return 0
    return (base + stride * int(occurrence)) & 0xFF


def _projected_model_offsets(
    root_stream: bytes,
    chunks: tuple[png.PngChunk, ...],
    diagnostic: IdatLocalDeflateDiagnostic | None,
    *,
    early_floor: int = 0x120,
    local_radius: int = 64,
) -> tuple[tuple[int, int, int], ...]:
    ranges = _idat_stream_ranges_by_index(chunks)
    max_chunk_length = max((chunk.length for _index, chunk, _start, _end in ranges), default=0)
    focus_offsets = list(DEEP_BEAM_FOCUS_OFFSETS)
    for start, end in DEEP_BEAM_FOCUS_BIT_RANGES:
        focus_offsets.extend(range(max(0, start // 8), max(0, (end + 7) // 8) + 1))
    early_limit = min(
        max_chunk_length,
        max(
            max(0, int(early_floor)),
            max(focus_offsets, default=0) + 1,
        ),
    )

    local_offsets: list[int] = list(range(0, max(0, early_limit)))
    local_offsets.extend(focus_offsets)
    if diagnostic is not None:
        diagnostic_globals = [
            diagnostic.stream_offset,
            diagnostic.window_start,
            max(0, diagnostic.window_end - 1),
            *diagnostic.suspect_byte_offsets,
            *_local_deflate_priority_offsets(diagnostic, max_offsets=256),
        ]
        for global_offset in diagnostic_globals:
            local_offset = _idat_local_offset_for_stream_offset(chunks, global_offset)
            if local_offset is None:
                continue
            local_offsets.extend(
                range(
                    max(0, local_offset - int(local_radius)),
                    min(max_chunk_length, local_offset + int(local_radius) + 1),
                )
            )

    projected: list[tuple[int, int, int]] = []
    for idat_index, chunk, start, _end in ranges:
        for local in dict.fromkeys(offset for offset in local_offsets if 0 <= int(offset) < chunk.length):
            projected.append((idat_index, start + int(local), int(local)))
    return tuple(dict.fromkeys(projected))


def _affine_apply_rule_to_offset(stream: bytes, offset: int, rule: dict[str, object], occurrence: int) -> tuple[bytes | None, IdatDeepBeamOperation | None]:
    if offset < 0 or offset >= len(stream):
        return None, None
    value = _affine_rule_value(rule, occurrence)
    if not value:
        return None, None
    old = stream[offset]
    mode = str(rule.get("mode") or "xor")
    if mode == "delta":
        new = (old + value) & 0xFF
    else:
        new = old ^ value
    if new == old:
        return None, None
    mutated = stream[:offset] + bytes((new,)) + stream[offset + 1 :]
    operation = IdatDeepBeamOperation(
        "affine-%s" % mode,
        int(offset),
        bytes((old,)),
        bytes((new,)),
    )
    return mutated, operation


def probe_idat_affine_corruption_model(
    data: bytes,
    *,
    convoy_model_path: str = "",
    budget: int = AFFINE_CORRUPTION_DEFAULT_BUDGET,
    top_candidates: int = AFFINE_CORRUPTION_DEFAULT_TOP_CANDIDATES,
    workers: str | int | None = "auto",
    gpu: bool | str | int | None = False,
    gpu_config: Any = None,
    cpu_batch_size: int = DEEP_BEAM_DEFAULT_CPU_BATCH_SIZE,
    gpu_shard_size: int = DEEP_BEAM_DEFAULT_GPU_SHARD_SIZE,
    checkpoint_path: str = "",
    progress_path: str = "",
    progress: QueueProgressCallback | None = None,
) -> IdatAffineCorruptionModelResult:
    strategy = "affine-corruption-model"
    budget_int = max(0, int(budget))
    worker_count = _deep_beam_workers(workers)
    gpu_requested = _deep_beam_gpu_requested(gpu)
    resolved_gpu_config = _deep_beam_gpu_config(gpu, gpu_config)
    if gpu_requested and not bool(getattr(resolved_gpu_config, "enabled", False)):
        try:
            resolved_gpu_config = replace(resolved_gpu_config, enabled=True)
        except Exception:
            pass
    before = idat.analyze_idat_stream(data)
    if not before.supported or before.complete:
        return IdatAffineCorruptionModelResult(before, None, (), 0, False, strategy=strategy, reason=before.reason)
    try:
        chunks, root_stream = _all_chunks_and_idat_stream(data)
    except png.PngFormatError as exc:
        return IdatAffineCorruptionModelResult(before, None, (), 0, False, strategy=strategy, reason=str(exc))
    source_hash = _stream_state_key(root_stream)
    original_idat_count = sum(1 for chunk in chunks if chunk.chunk_type == b"IDAT")
    model, model_error = _load_idat_convoy_model(convoy_model_path)
    if model is None:
        return IdatAffineCorruptionModelResult(
            before,
            None,
            (),
            0,
            False,
            model_path=convoy_model_path,
            workers=worker_count,
            gpu_status="fallback-cpu" if gpu_requested else "off",
            strategy=strategy,
            reason=model_error,
            source_hash=source_hash,
        )
    if str(model.get("convoy_stream_hash") or "") != source_hash:
        return IdatAffineCorruptionModelResult(
            before,
            None,
            (),
            0,
            False,
            model_path=convoy_model_path,
            workers=worker_count,
            gpu_status="fallback-cpu" if gpu_requested else "off",
            strategy=strategy,
            reason="convoy model hash does not match current IDAT stream",
            source_hash=source_hash,
        )
    progress_state = affine_corruption_progress_state(data, progress_path)
    if progress_state.available and progress_state.source_matches and progress_state.exhausted and progress_state.budget >= budget_int:
        _before, _chunks, _stream, _source_hash, _count, top = _load_frontier_candidates_for_progress(
            data,
            checkpoint_path,
            top_candidates=top_candidates,
            max_operation_depth=1,
        )
        best = _frontier_best_candidate(before, top)
        return IdatAffineCorruptionModelResult(
            before,
            best,
            top,
            progress_state.tested,
            True,
            checkpoint_path=checkpoint_path,
            progress_path=progress_path,
            model_path=convoy_model_path,
            workers=worker_count,
            gpu_status="fallback-cpu" if gpu_requested else "off",
            strategy=strategy,
            reason="affine corruption model already exhausted for this source/budget",
            source_hash=source_hash,
        )

    rules = _affine_rules_from_model(model)
    diagnostic = idat_local_deflate_diagnostic(data, analysis=before)
    projections = _projected_model_offsets(root_stream, chunks, diagnostic)
    root = _frontier_root_candidate(data=data, stream=root_stream, before=before, original_idat_count=original_idat_count)
    top: list[IdatDeepBeamCandidate] = []
    visited = {_stream_state_key(root_stream)}
    tested = 0
    next_state_id = 1
    png_plausible = 0
    projected_hits = 0
    budget_exhausted = False
    last_checkpoint_at = 0
    gpu_status = "off"
    gpu_hits = 0
    gpu_shards = 0
    cpu_batches = 0
    checkpointed_hashes: set[str] = set()

    if progress is not None:
        progress(strategy, 0, budget_int)

    specs: list[tuple[str, int, int]] = []
    seen_specs: set[tuple[str, int, int]] = set()
    for rule in rules:
        rule_class = rule.get("idat_class_mod8")
        for idat_index, offset, _local in projections:
            if rule_class is not None:
                try:
                    if idat_index % 8 != int(rule_class) % 8:
                        continue
                except (TypeError, ValueError):
                    pass
            _stream, operation = _affine_apply_rule_to_offset(root_stream, offset, rule, idat_index)
            if operation is None or not operation.new_bytes:
                continue
            spec = ("replace", int(operation.stream_offset), int(operation.new_bytes[0]))
            if spec in seen_specs:
                continue
            seen_specs.add(spec)
            specs.append(spec)
            if len(specs) >= budget_int:
                budget_exhausted = True
                break
        if budget_exhausted:
            break

    projected_hits = len(specs)
    worker_executor: ProcessPoolExecutor | None = None
    if worker_count > 1:
        try:
            worker_executor = ProcessPoolExecutor(max_workers=worker_count, initializer=_deep_beam_worker_init)
        except (OSError, RuntimeError, ValueError):
            worker_executor = None
            worker_count = 1

    gpu_session: Any = None
    if gpu_requested:
        try:
            from . import ultimate_opengl_backend

            gpu_session = ultimate_opengl_backend.UltimateOpenGLAnalysisSession(resolved_gpu_config)
            gpu_status = "fallback-cpu"
        except Exception:
            gpu_session = None
            gpu_status = "fallback-cpu"

    def remember(candidate: IdatDeepBeamCandidate | None) -> None:
        nonlocal top, png_plausible, next_state_id
        if candidate is None:
            return
        key = _stream_state_key(candidate.stream)
        if key in visited:
            return
        visited.add(key)
        if _candidate_png_plausible(candidate):
            png_plausible += 1
        top = list(_deep_beam_ranked_unique(itertools.chain(top, (candidate,)), limit=top_candidates))
        next_state_id = max(next_state_id, int(candidate.state_id) + 1)

    try:
        gpu_indices: set[int] = set()
        if specs and gpu_requested:
            gpu_successors, gpu_tested, gpu_used, batch_gpu_status, _gpu_warning, covered_indices = _deep_beam_gpu_byte_successors(
                root,
                before=before,
                state_id_start=next_state_id,
                original_idat_count=original_idat_count,
                depth=1,
                specs=tuple(specs),
                budget_left=max(0, budget_int - tested),
                checkpoint_every=AFFINE_CORRUPTION_CHECKPOINT_EVERY,
                gpu_config=resolved_gpu_config,
                gpu_done_shards=set(),
                workers=worker_count,
                worker_executor=worker_executor,
                cpu_batch_size=cpu_batch_size,
                gpu_shard_size=gpu_shard_size,
                gpu_session=gpu_session,
            )
            tested += gpu_tested
            if batch_gpu_status != "off":
                gpu_status = batch_gpu_status
            if gpu_used:
                gpu_indices = set(covered_indices)
                gpu_hits += len(gpu_successors)
                gpu_shards += 1
            for successor in gpu_successors:
                remember(successor)

        cpu_specs = tuple(
            spec for index, spec in enumerate(specs) if index not in gpu_indices
        )
        cpu_specs = cpu_specs[: max(0, budget_int - tested)]
        cpu_candidates = _deep_beam_validate_specs(
            data,
            before,
            cpu_specs,
            workers=worker_count,
            worker_executor=worker_executor,
            cpu_batch_size=cpu_batch_size,
            timing=None,
        )
        cpu_batches += len(
            _deep_beam_spec_batches(
                cpu_specs,
                workers=worker_count,
                cpu_batch_size=cpu_batch_size,
            )
        )
        tested += len(cpu_specs)
        for candidate in cpu_candidates:
            successor = _deep_beam_candidate_from_deflate_candidate(
                root,
                candidate,
                before=before,
                state_id=next_state_id,
                original_idat_count=original_idat_count,
                kind="affine-cpu",
            )
            remember(successor)
            if progress is not None and (tested == 1 or tested % 1000 == 0):
                progress(strategy, min(tested, budget_int), budget_int)
            if checkpoint_path and top and tested - last_checkpoint_at >= AFFINE_CORRUPTION_CHECKPOINT_EVERY:
                for item in top:
                    key = _stream_state_key(item.stream)
                    if key in checkpointed_hashes:
                        continue
                    _append_frontier_checkpoint(checkpoint_path, item, source_hash=source_hash, source_stream=root_stream)
                    checkpointed_hashes.add(key)
                last_checkpoint_at = tested
    finally:
        if gpu_session is not None:
            try:
                gpu_session.close()
            except Exception:
                pass
        if worker_executor is not None:
            worker_executor.shutdown(cancel_futures=True)

    if checkpoint_path:
        for item in top:
            key = _stream_state_key(item.stream)
            if key in checkpointed_hashes:
                continue
            _append_frontier_checkpoint(checkpoint_path, item, source_hash=source_hash, source_stream=root_stream)
            checkpointed_hashes.add(key)
    best = _frontier_best_candidate(before, top)
    reason = "rules=%s; projections=%s; projected_hits=%s; png_plausible=%s; top=%s" % (
        len(rules),
        len(projections),
        projected_hits,
        png_plausible,
        len(top),
    )
    _write_frontier_progress(
        progress_path,
        source_hash=source_hash,
        tested=tested,
        budget=budget_int,
        best=best,
        top_count=len(top),
        exhausted=True,
        reason=reason,
        strategy=strategy,
        extra={
            "model_path": convoy_model_path,
            "rules": int(len(rules)),
            "projected_hits": int(projected_hits),
            "png_plausible": int(png_plausible),
            "workers": int(worker_count),
            "gpu_status": str(gpu_status),
            "gpu_hits": int(gpu_hits),
            "gpu_shards": int(gpu_shards),
            "cpu_batches": int(cpu_batches),
        },
    )
    if progress is not None:
        progress(strategy, min(tested, budget_int), budget_int)
    return IdatAffineCorruptionModelResult(
        before,
        best,
        tuple(top),
        tested,
        budget_exhausted or tested >= budget_int,
        checkpoint_path=checkpoint_path,
        progress_path=progress_path,
        model_path=convoy_model_path,
        rules=len(rules),
        projected_hits=projected_hits,
        png_plausible=png_plausible,
        workers=worker_count,
        gpu_status=gpu_status,
        gpu_hits=gpu_hits,
        gpu_shards=gpu_shards,
        cpu_batches=cpu_batches,
        strategy=strategy,
        reason=reason,
        source_hash=source_hash,
    )


def _deep_beam_bit_offsets(diagnostic: IdatLocalDeflateDiagnostic, *, max_bits: int) -> tuple[int, ...]:
    bits: list[int] = []
    for start, end in DEEP_BEAM_FOCUS_BIT_RANGES:
        bits.extend(range(start, end))
    bits.extend(diagnostic.suspect_bits)
    start_bit = diagnostic.window_start * 8
    end_bit = diagnostic.window_end * 8
    return tuple(dict.fromkeys(bit for bit in bits if start_bit <= bit < end_bit))[: max(1, int(max_bits))]


def _deep_beam_offsets(
    diagnostic: IdatLocalDeflateDiagnostic,
    *,
    max_offsets: int,
    widened_limit: int,
) -> tuple[int, ...]:
    offsets: list[int] = []

    def add(offset: int) -> None:
        if 0 <= int(offset) < diagnostic.stream_size:
            offsets.append(int(offset))

    for offset in DEEP_BEAM_FOCUS_OFFSETS:
        add(offset)
    for offset in diagnostic.suspect_byte_offsets:
        add(offset)
    for offset in _local_deflate_priority_offsets(diagnostic, max_offsets=max_offsets):
        add(offset)
    for offset in range(0, min(diagnostic.stream_size, int(widened_limit))):
        add(offset)
    return tuple(dict.fromkeys(offsets))[: max(1, int(max_offsets))]


def _deep_beam_operation_from_candidate(candidate: IdatDeflateCandidate, kind: str | None = None) -> IdatDeepBeamOperation:
    return IdatDeepBeamOperation(
        kind or candidate.edit_kind,
        int(candidate.stream_offset),
        candidate.old_bytes or bytes((candidate.old_byte & 0xFF,)),
        candidate.new_bytes or (b"" if candidate.edit_kind == "remove" else bytes((candidate.new_byte & 0xFF,))),
        tuple(candidate.bit_offsets),
    )


def _deep_beam_candidate_from_deflate_candidate(
    parent: IdatDeepBeamCandidate,
    candidate: IdatDeflateCandidate | None,
    *,
    before: idat.IdatStreamAnalysis,
    state_id: int,
    original_idat_count: int,
    kind: str | None = None,
) -> IdatDeepBeamCandidate | None:
    if candidate is None:
        return None
    try:
        _chunks, stream = _all_chunks_and_idat_stream(candidate.data)
    except png.PngFormatError:
        return None
    operation = _deep_beam_operation_from_candidate(candidate, kind=kind)
    operations = parent.operations + (operation,)
    return IdatDeepBeamCandidate(
        data=candidate.data,
        stream=stream,
        operations=operations,
        before=before,
        after=candidate.after,
        state_id=state_id,
        parent_id=parent.state_id,
        source_offsets=parent.source_offsets + (operation.stream_offset,),
        score=_deep_beam_score(
            candidate.after,
            stream,
            len(operations),
            data=candidate.data,
            original_idat_count=original_idat_count,
        ),
    )


def _deep_beam_subprobe_successors(
    parent: IdatDeepBeamCandidate,
    *,
    before: idat.IdatStreamAnalysis,
    state_id_start: int,
    original_idat_count: int,
    depth: int,
) -> tuple[list[IdatDeepBeamCandidate], int]:
    successors: list[IdatDeepBeamCandidate] = []
    tested = 0
    next_state_id = int(state_id_start)
    if depth >= 1:
        semantic = probe_dynamic_huffman_semantic_candidates(parent.data, budget=4096, max_tokens=64)
        tested += semantic.tested_candidates
        for candidate, kind in ((semantic.best, "semantic-token"), (semantic.diagnostic_best, "semantic-token-diagnostic")):
            successor = _deep_beam_candidate_from_deflate_candidate(
                parent,
                candidate,
                before=before,
                state_id=next_state_id,
                original_idat_count=original_idat_count,
                kind=kind,
            )
            if successor is not None:
                successors.append(successor)
                next_state_id += 1

        alphabet = probe_dynamic_huffman_alphabet_candidates(parent.data, budget=2048, max_fields=12)
        tested += alphabet.tested_candidates
        for candidate, kind in ((alphabet.best, "alphabet"), (alphabet.diagnostic_best, "alphabet-diagnostic")):
            successor = _deep_beam_candidate_from_deflate_candidate(
                parent,
                candidate,
                before=before,
                state_id=next_state_id,
                original_idat_count=original_idat_count,
                kind=kind,
            )
            if successor is not None:
                successors.append(successor)
                next_state_id += 1
    if depth >= 2:
        crc_guided = probe_dynamic_huffman_crc_guided_candidates(
            parent.data,
            budget=4096,
            max_group_bits=24,
            max_solutions_per_group=32,
        )
        tested += crc_guided.tested_candidates
        for candidate, kind in ((crc_guided.best, "crc-guided"), (crc_guided.diagnostic_best, "crc-guided-diagnostic")):
            successor = _deep_beam_candidate_from_deflate_candidate(
                parent,
                candidate,
                before=before,
                state_id=next_state_id,
                original_idat_count=original_idat_count,
                kind=kind,
            )
            if successor is not None:
                successors.append(successor)
                next_state_id += 1
    return successors, tested


def _deep_beam_mutation_specs(
    offsets: Iterable[int],
    bits: Iterable[int],
    *,
    budget_left: int,
) -> tuple[tuple[str, int, int], ...]:
    specs: list[tuple[str, int, int]] = []

    def add(kind: str, offset: int, value: int = 0) -> bool:
        if len(specs) >= int(budget_left):
            return True
        specs.append((kind, int(offset), int(value)))
        return False

    for offset in offsets:
        if add("remove", offset):
            return tuple(specs)
        for value in DEEP_BEAM_COMMON_BYTES:
            if add("insert", offset, value):
                return tuple(specs)
            if add("replace", offset, value):
                return tuple(specs)
    for bit in bits:
        if add("bit-flip", bit):
            return tuple(specs)
        if add("bit-delete", bit):
            return tuple(specs)
        for value in (0, 1):
            if add("bit-insert", bit, value):
                return tuple(specs)
    return tuple(specs)


def _deep_beam_apply_mutation_spec(
    args: tuple[bytes, idat.IdatStreamAnalysis, tuple[str, int, int]],
) -> IdatDeflateCandidate | None:
    data, before_analysis, spec = args
    kind, offset, value = spec
    if kind == "remove":
        return mutate_idat_stream_edit(data, offset, "remove", remove_count=1, before_analysis=before_analysis)
    if kind == "insert":
        return mutate_idat_stream_edit(data, offset, "insert", new_bytes=bytes((value & 0xFF,)), before_analysis=before_analysis)
    if kind == "replace":
        return mutate_idat_stream_byte(data, offset, value & 0xFF, before_analysis=before_analysis)
    if kind == "bit-flip":
        return mutate_idat_stream_bit_flips(data, (offset,), before_analysis=before_analysis)
    if kind == "bit-delete":
        return mutate_idat_stream_bit_shift(data, offset, "bit-delete", before_analysis=before_analysis)
    if kind == "bit-insert":
        return mutate_idat_stream_bit_shift(data, offset, "bit-insert", bit_value=value & 1, before_analysis=before_analysis)
    return None


def _deep_beam_apply_mutation_batch(
    args: tuple[bytes, idat.IdatStreamAnalysis, tuple[tuple[str, int, int], ...]],
) -> tuple[IdatDeflateCandidate | None, ...]:
    data, before_analysis, specs = args
    return tuple(
        _deep_beam_apply_mutation_spec((data, before_analysis, spec))
        for spec in specs
    )


def _deep_beam_worker_init() -> None:
    try:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
    except (OSError, ValueError):
        pass
    if os.name == "posix":
        try:
            import ctypes

            libc = ctypes.CDLL("libc.so.6", use_errno=True)
            pr_set_pdeathsig = 1
            libc.prctl(pr_set_pdeathsig, signal.SIGTERM)
            if os.getppid() == 1:
                os._exit(130)
        except Exception:
            pass


def _deep_beam_cpu_batch_size(spec_count: int, workers: int, cpu_batch_size: int) -> int:
    configured = max(1, int(cpu_batch_size or DEEP_BEAM_DEFAULT_CPU_BATCH_SIZE))
    if int(workers) <= 1 or int(spec_count) <= 0:
        return min(configured, 256)
    adaptive = max(32, min(256, max(1, int(spec_count) // max(1, int(workers) * 4))))
    if configured == DEEP_BEAM_DEFAULT_CPU_BATCH_SIZE:
        return adaptive
    return min(configured, 256)


def _deep_beam_worker_in_flight_limit(workers: int, batch_count: int) -> int:
    batch_count = max(0, int(batch_count))
    if batch_count <= 0:
        return 0
    worker_count = max(1, int(workers))
    return max(1, min(worker_count, DEEP_BEAM_WORKER_IN_FLIGHT_LIMIT, batch_count))


def _deep_beam_spec_batches(
    specs: tuple[tuple[str, int, int], ...],
    *,
    workers: int,
    cpu_batch_size: int,
) -> tuple[tuple[tuple[str, int, int], ...], ...]:
    if not specs:
        return ()
    batch_size = _deep_beam_cpu_batch_size(len(specs), workers, cpu_batch_size)
    return tuple(
        tuple(specs[index : index + batch_size])
        for index in range(0, len(specs), batch_size)
    )


def _deep_beam_collect_batch_futures(
    futures: tuple[Any, ...],
    *,
    fallback_data: bytes,
    fallback_before: idat.IdatStreamAnalysis,
    fallback_batches: tuple[tuple[tuple[str, int, int], ...], ...],
    timing: IdatDeepBeamRuntimeStats | None,
    started_at: float,
) -> tuple[IdatDeflateCandidate | None, ...]:
    try:
        results: list[IdatDeflateCandidate | None] = []
        for future in futures:
            results.extend(future.result())
        if timing is not None:
            timing.cpu_batches += len(fallback_batches)
            timing.cpu_validate_ms += (time.perf_counter() - started_at) * 1000.0
        return tuple(results)
    except (OSError, RuntimeError, ValueError, KeyboardInterrupt):
        for future in futures:
            canceller = getattr(future, "cancel", None)
            if callable(canceller):
                canceller()
        raise
    except Exception:
        if timing is not None:
            timing.cpu_batches += len(fallback_batches)
            timing.cpu_validate_ms += (time.perf_counter() - started_at) * 1000.0
        fallback_results: list[IdatDeflateCandidate | None] = []
        for batch in fallback_batches:
            fallback_results.extend(_deep_beam_apply_mutation_batch((fallback_data, fallback_before, batch)))
        return tuple(fallback_results)


def _deep_beam_validate_specs(
    data: bytes,
    before_analysis: idat.IdatStreamAnalysis,
    specs: tuple[tuple[str, int, int], ...],
    *,
    workers: int,
    worker_executor: ProcessPoolExecutor | None,
    cpu_batch_size: int,
    timing: IdatDeepBeamRuntimeStats | None,
) -> tuple[IdatDeflateCandidate | None, ...]:
    if not specs:
        return ()
    batches = _deep_beam_spec_batches(
        specs,
        workers=workers,
        cpu_batch_size=cpu_batch_size,
    )
    started_at = time.perf_counter()
    if worker_executor is not None and len(batches) > 1:
        try:
            futures = tuple(
                worker_executor.submit(
                    _deep_beam_apply_mutation_batch,
                    (data, before_analysis, batch),
                )
                for batch in batches
            )
            return _deep_beam_collect_batch_futures(
                futures,
                fallback_data=data,
                fallback_before=before_analysis,
                fallback_batches=batches,
                timing=timing,
                started_at=started_at,
            )
        except KeyboardInterrupt:
            raise
        except Exception:
            pass

    results: list[IdatDeflateCandidate | None] = []
    for batch in batches:
        results.extend(_deep_beam_apply_mutation_batch((data, before_analysis, batch)))
    if timing is not None:
        timing.cpu_batches += len(batches)
        timing.cpu_validate_ms += (time.perf_counter() - started_at) * 1000.0
    return tuple(results)


def _deep_beam_consume_validated_specs(
    data: bytes,
    before_analysis: idat.IdatStreamAnalysis,
    specs: tuple[tuple[str, int, int], ...],
    *,
    workers: int,
    worker_executor: ProcessPoolExecutor | None,
    cpu_batch_size: int,
    timing: IdatDeepBeamRuntimeStats | None,
    consume: Callable[[tuple[IdatDeflateCandidate | None, ...]], None],
) -> None:
    if not specs:
        return
    batches = _deep_beam_spec_batches(
        specs,
        workers=workers,
        cpu_batch_size=cpu_batch_size,
    )
    if not batches:
        return
    started_at = time.perf_counter()
    completed_batches = 0

    def consume_batch(batch: tuple[tuple[str, int, int], ...]) -> None:
        nonlocal completed_batches
        results = _deep_beam_apply_mutation_batch((data, before_analysis, batch))
        try:
            consume(results)
        finally:
            completed_batches += 1

    if worker_executor is not None and len(batches) > 1:
        pending: dict[Any, tuple[tuple[str, int, int], ...]] = {}
        iterator = iter(batches)
        max_in_flight = _deep_beam_worker_in_flight_limit(workers, len(batches))

        def submit_next() -> bool:
            try:
                batch = next(iterator)
            except StopIteration:
                return False
            pending[
                worker_executor.submit(
                    _deep_beam_apply_mutation_batch,
                    (data, before_analysis, batch),
                )
            ] = batch
            return True

        try:
            for _index in range(max_in_flight):
                submit_next()
            while pending:
                done, _pending = wait(tuple(pending), return_when=FIRST_COMPLETED)
                for future in done:
                    batch = pending.pop(future)
                    try:
                        results = future.result()
                    except KeyboardInterrupt:
                        for waiting in pending:
                            canceller = getattr(waiting, "cancel", None)
                            if callable(canceller):
                                canceller()
                        raise
                    except (OSError, RuntimeError, ValueError):
                        for waiting in pending:
                            canceller = getattr(waiting, "cancel", None)
                            if callable(canceller):
                                canceller()
                        raise
                    except Exception:
                        results = _deep_beam_apply_mutation_batch((data, before_analysis, batch))
                    try:
                        consume(tuple(results))
                    finally:
                        completed_batches += 1
                    submit_next()
            return
        except KeyboardInterrupt:
            for waiting in pending:
                canceller = getattr(waiting, "cancel", None)
                if callable(canceller):
                    canceller()
            raise
        except (OSError, RuntimeError, ValueError):
            for waiting in pending:
                canceller = getattr(waiting, "cancel", None)
                if callable(canceller):
                    canceller()
            raise
        finally:
            if timing is not None:
                timing.cpu_batches += completed_batches
                timing.cpu_validate_ms += (time.perf_counter() - started_at) * 1000.0

    try:
        for batch in batches:
            consume_batch(batch)
    finally:
        if timing is not None:
            timing.cpu_batches += completed_batches
            timing.cpu_validate_ms += (time.perf_counter() - started_at) * 1000.0


def _deep_beam_spec_to_operation(stream: bytes, spec: tuple[str, int, int]) -> IdatDeepBeamOperation | None:
    kind, offset, value = spec
    offset = int(offset)
    if offset < 0:
        return None
    if kind == "remove":
        if offset >= len(stream):
            return None
        return IdatDeepBeamOperation(kind, offset, stream[offset : offset + 1], b"")
    if kind == "insert":
        if offset > len(stream):
            return None
        return IdatDeepBeamOperation(kind, offset, b"", bytes((int(value) & 0xFF,)))
    if kind == "replace":
        if offset >= len(stream) or stream[offset] == (int(value) & 0xFF):
            return None
        return IdatDeepBeamOperation(kind, offset, stream[offset : offset + 1], bytes((int(value) & 0xFF,)))
    return None


def _deep_beam_gpu_compatible_specs(
    stream: bytes,
    specs: tuple[tuple[str, int, int], ...],
) -> tuple[tuple[int, tuple[str, int, int], IdatDeepBeamOperation], ...]:
    compatible: list[tuple[int, tuple[str, int, int], IdatDeepBeamOperation]] = []
    for index, spec in enumerate(specs):
        operation = _deep_beam_spec_to_operation(stream, spec)
        if operation is not None:
            compatible.append((index, spec, operation))
    return tuple(compatible)


def _deep_beam_gpu_shard_key(parent: IdatDeepBeamCandidate, *, depth: int, start_rank: int, end_rank: int) -> str:
    return "%s:%s:%s:%s:%s" % (
        _stream_state_key(parent.stream),
        int(parent.state_id),
        int(depth),
        int(start_rank),
        int(end_rank),
    )


def _deep_beam_gpu_byte_successors(
    parent: IdatDeepBeamCandidate,
    *,
    before: idat.IdatStreamAnalysis,
    state_id_start: int,
    original_idat_count: int,
    depth: int,
    specs: tuple[tuple[str, int, int], ...],
    budget_left: int,
    checkpoint_every: int,
    gpu_config: Any,
    gpu_done_shards: set[str],
    workers: int,
    worker_executor: ProcessPoolExecutor | None = None,
    cpu_batch_size: int = DEEP_BEAM_DEFAULT_CPU_BATCH_SIZE,
    gpu_shard_size: int = DEEP_BEAM_DEFAULT_GPU_SHARD_SIZE,
    gpu_session: Any = None,
    timing: IdatDeepBeamRuntimeStats | None = None,
    compatible: tuple[tuple[int, tuple[str, int, int], IdatDeepBeamOperation], ...] | None = None,
) -> tuple[list[IdatDeepBeamCandidate], int, bool, str, str, set[int]]:
    enabled = bool(getattr(gpu_config, "enabled", False))
    if not enabled or depth != 1 or not specs:
        return [], 0, False, "off", "", set()

    compatible = compatible if compatible is not None else _deep_beam_gpu_compatible_specs(parent.stream, specs)
    if not compatible:
        return [], 0, False, "opengl-requested", "", set()

    try:
        from . import ultimate_opengl_backend
    except Exception as exc:
        return [], 0, False, "unavailable:%s" % exc, str(exc), set()

    operation_pool = tuple(operation for _index, _spec, operation in compatible)
    base_plan = ultimate_opengl_backend.build_analysis_plan(
        parent.stream,
        width=before.width,
        height=before.height,
        bit_depth=before.bit_depth,
        color_type=before.color_type,
        scanline_size=before.scanline_size,
        expected_size=before.expected_size,
        operation_pool=operation_pool,
        depth=1,
        max_hits=min(DEEP_BEAM_GPU_MAX_HITS, max(1, len(operation_pool))),
    )
    decision = ultimate_opengl_backend.explain_analysis(base_plan, gpu_config)
    if not decision.runnable:
        return [], 0, False, "unavailable:%s" % decision.reason, decision.reason, set()

    successors: list[IdatDeepBeamCandidate] = []
    next_state_id = int(state_id_start)
    tested = 0
    covered_spec_indices: set[int] = set()
    hit_specs: list[tuple[int, tuple[str, int, int]]] = []
    shard_size = max(1, min(int(gpu_shard_size or DEEP_BEAM_DEFAULT_GPU_SHARD_SIZE), max(1, int(budget_left))))
    start_rank = 0
    backend = "opengl-active"
    warning = ""

    def add(candidate: IdatDeflateCandidate | None, kind: str | None = None) -> None:
        nonlocal next_state_id
        successor = _deep_beam_candidate_from_deflate_candidate(
            parent,
            candidate,
            before=before,
            state_id=next_state_id,
            original_idat_count=original_idat_count,
            kind=kind,
        )
        if successor is not None:
            successors.append(successor)
            next_state_id += 1

    while start_rank < len(operation_pool) and tested < int(budget_left):
        end_rank = min(len(operation_pool), start_rank + shard_size, start_rank + max(0, int(budget_left) - tested))
        if end_rank <= start_rank:
            break
        shard_key = _deep_beam_gpu_shard_key(parent, depth=depth, start_rank=start_rank, end_rank=end_rank)
        if shard_key in gpu_done_shards:
            covered_spec_indices.update(int(compatible[index][0]) for index in range(start_rank, end_rank))
            if timing is not None:
                timing.gpu_skipped_resume += 1
            start_rank = end_rank
            continue
        plan = ultimate_opengl_backend.build_analysis_plan(
            parent.stream,
            width=before.width,
            height=before.height,
            bit_depth=before.bit_depth,
            color_type=before.color_type,
            scanline_size=before.scanline_size,
            expected_size=before.expected_size,
            operation_pool=operation_pool,
            depth=1,
            start_rank=start_rank,
            end_rank=end_rank,
            max_hits=min(DEEP_BEAM_GPU_MAX_HITS, max(1, end_rank - start_rank)),
        )
        try:
            if gpu_session is not None and hasattr(gpu_session, "run"):
                result = gpu_session.run(plan, max_ranks=end_rank - start_rank)
            else:
                result = ultimate_opengl_backend.run_analysis_gpu(
                    plan,
                    gpu_config,
                    max_ranks=end_rank - start_rank,
                    allow_host_fallback=False,
                )
        except Exception as exc:
            return [], tested, False, "fallback-cpu", str(exc), set()

        tested += max(0, int(result.covered_rank_count or (end_rank - start_rank)))
        gpu_done_shards.add(shard_key)
        if timing is not None:
            timing.gpu_shards += 1
            timing.gpu_hits += len(result.hits)
            timing.gpu_setup_ms += float(getattr(result, "setup_ms", 0.0) or 0.0)
            timing.gpu_dispatch_ms += float(getattr(result, "dispatch_ms", 0.0) or 0.0)
        covered_spec_indices.update(int(compatible[index][0]) for index in range(start_rank, end_rank))
        if result.fallback_reason:
            backend = "fallback-cpu"
            warning = result.fallback_reason
        for hit in result.hits:
            if not hit.operation_indices:
                continue
            pool_index = int(hit.operation_indices[0])
            if pool_index < 0 or pool_index >= len(compatible):
                continue
            original_index, spec, _operation = compatible[pool_index]
            covered_spec_indices.add(original_index)
            hit_specs.append((original_index, spec))
        start_rank = end_rank

    hit_candidates = _deep_beam_validate_specs(
        parent.data,
        parent.after,
        tuple(spec for _original_index, spec in hit_specs),
        workers=workers,
        worker_executor=worker_executor,
        cpu_batch_size=cpu_batch_size,
        timing=timing,
    )
    for (_original_index, spec), candidate in zip(hit_specs, hit_candidates):
        add(candidate, kind="gpu-%s" % spec[0])

    return successors, tested, True, backend, warning, covered_spec_indices


def _deep_beam_byte_bit_successors(
    parent: IdatDeepBeamCandidate,
    *,
    before: idat.IdatStreamAnalysis,
    state_id_start: int,
    original_idat_count: int,
    max_offsets: int,
    max_bits: int,
    widened_limit: int,
    budget_left: int,
    workers: int,
    depth: int = 1,
    gpu_config: Any = None,
    gpu_done_shards: set[str] | None = None,
    checkpoint_every: int = DEEP_BEAM_DEFAULT_CHECKPOINT_EVERY,
    worker_executor: ProcessPoolExecutor | None = None,
    cpu_batch_size: int = DEEP_BEAM_DEFAULT_CPU_BATCH_SIZE,
    gpu_shard_size: int = DEEP_BEAM_DEFAULT_GPU_SHARD_SIZE,
    overlap_gpu_cpu: bool = False,
    gpu_session: Any = None,
    timing: IdatDeepBeamRuntimeStats | None = None,
    successor_limit: int = DEEP_BEAM_SUCCESSOR_KEEP_LIMIT,
) -> tuple[list[IdatDeepBeamCandidate], int, str, str]:
    diagnostic = idat_local_deflate_diagnostic(parent.data, analysis=parent.after)
    if diagnostic is None:
        return [], 0, "off", ""
    offsets = _deep_beam_offsets(diagnostic, max_offsets=max_offsets, widened_limit=widened_limit)
    bits = _deep_beam_bit_offsets(diagnostic, max_bits=max_bits)
    specs = _deep_beam_mutation_specs(offsets, bits, budget_left=budget_left)
    successor_map: dict[str, IdatDeepBeamCandidate] = {}
    next_state_id = int(state_id_start)
    keep_limit = max(1, int(successor_limit or DEEP_BEAM_SUCCESSOR_KEEP_LIMIT))
    gpu_done_shards = gpu_done_shards if gpu_done_shards is not None else set()
    compatible = (
        _deep_beam_gpu_compatible_specs(parent.stream, specs)
        if bool(getattr(gpu_config, "enabled", False)) and depth == 1
        else ()
    )
    compatible_indices = {int(index) for index, _spec, _operation in compatible}
    overlapped_specs: tuple[tuple[str, int, int], ...] = ()
    overlapped_batches: tuple[tuple[tuple[str, int, int], ...], ...] = ()
    overlapped_futures: tuple[Any, ...] = ()
    overlapped_started = 0.0
    if (
        overlap_gpu_cpu
        and worker_executor is not None
        and compatible_indices
        and len(compatible_indices) < len(specs)
    ):
        overlapped_specs = tuple(
            spec
            for index, spec in enumerate(specs)
            if index not in compatible_indices
        )
        overlapped_batches = _deep_beam_spec_batches(
            overlapped_specs,
            workers=workers,
            cpu_batch_size=cpu_batch_size,
        )
        if overlapped_batches:
            overlapped_started = time.perf_counter()
            try:
                overlapped_futures = tuple(
                    worker_executor.submit(
                        _deep_beam_apply_mutation_batch,
                        (parent.data, parent.after, batch),
                    )
                    for batch in overlapped_batches
                )
            except Exception:
                overlapped_futures = ()

    gpu_successors, gpu_tested, gpu_used, gpu_backend, gpu_warning, gpu_indices = _deep_beam_gpu_byte_successors(
        parent,
        before=before,
        state_id_start=next_state_id,
        original_idat_count=original_idat_count,
        depth=depth,
        specs=specs,
        budget_left=budget_left,
        checkpoint_every=checkpoint_every,
        gpu_config=gpu_config,
        gpu_done_shards=gpu_done_shards,
        workers=workers,
        worker_executor=worker_executor,
        cpu_batch_size=cpu_batch_size,
        gpu_shard_size=gpu_shard_size,
        gpu_session=gpu_session,
        timing=timing,
        compatible=compatible,
    )
    for successor in gpu_successors:
        successor_map[_stream_state_key(successor.stream)] = successor
    if len(successor_map) > keep_limit:
        _deep_beam_prune_candidate_map(successor_map, limit=keep_limit)
    next_state_id += len(gpu_successors)

    def add(candidate: IdatDeflateCandidate | None, kind: str | None = None) -> None:
        nonlocal next_state_id
        successor = _deep_beam_candidate_from_deflate_candidate(
            parent,
            candidate,
            before=before,
            state_id=next_state_id,
            original_idat_count=original_idat_count,
            kind=kind,
        )
        if successor is not None:
            key = _stream_state_key(successor.stream)
            previous = successor_map.get(key)
            if previous is None or successor.score > previous.score:
                successor_map[key] = successor
            if len(successor_map) > keep_limit * 2:
                _deep_beam_prune_candidate_map(successor_map, limit=keep_limit)
            next_state_id += 1

    def consume_candidates(candidates: tuple[IdatDeflateCandidate | None, ...]) -> None:
        for candidate in candidates:
            add(candidate)

    cpu_tested = 0
    if overlapped_futures:
        cpu_candidates = _deep_beam_collect_batch_futures(
            overlapped_futures,
            fallback_data=parent.data,
            fallback_before=parent.after,
            fallback_batches=overlapped_batches,
            timing=timing,
            started_at=overlapped_started,
        )
        for candidate in cpu_candidates:
            add(candidate)
        cpu_tested += len(overlapped_specs)
        if gpu_used:
            specs_for_cpu = ()
        else:
            specs_for_cpu = tuple(
                spec
                for index, spec in enumerate(specs)
                if index in compatible_indices
            )
    else:
        specs_for_cpu = tuple(
            spec
            for index, spec in enumerate(specs)
            if not gpu_used or index not in gpu_indices
        )

    _deep_beam_consume_validated_specs(
        parent.data,
        parent.after,
        specs_for_cpu,
        workers=workers,
        worker_executor=worker_executor,
        cpu_batch_size=cpu_batch_size,
        timing=timing,
        consume=consume_candidates,
    )
    cpu_tested += len(specs_for_cpu)
    if len(successor_map) > keep_limit:
        _deep_beam_prune_candidate_map(successor_map, limit=keep_limit)
    ranked = _deep_beam_ranked_unique(successor_map.values(), limit=keep_limit)
    successors = [
        replace(candidate, state_id=int(state_id_start) + index)
        for index, candidate in enumerate(ranked)
    ]
    return successors, gpu_tested + cpu_tested, gpu_backend, gpu_warning


def _deep_beam_ranked_unique(
    candidates: Iterable[IdatDeepBeamCandidate],
    *,
    limit: int,
) -> tuple[IdatDeepBeamCandidate, ...]:
    best_by_stream: dict[str, IdatDeepBeamCandidate] = {}
    for candidate in candidates:
        key = _stream_state_key(candidate.stream)
        previous = best_by_stream.get(key)
        if previous is None or candidate.score > previous.score:
            best_by_stream[key] = candidate
    return tuple(
        sorted(
            best_by_stream.values(),
            key=lambda candidate: (candidate.score, -len(candidate.operations), -candidate.state_id),
            reverse=True,
        )[: max(1, int(limit))]
    )


def _deep_beam_prune_candidate_map(
    candidates: dict[str, IdatDeepBeamCandidate],
    *,
    limit: int,
) -> None:
    keep = _deep_beam_ranked_unique(candidates.values(), limit=limit)
    candidates.clear()
    candidates.update((_stream_state_key(candidate.stream), candidate) for candidate in keep)


def _deep_beam_memory_available_bytes() -> int | None:
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as file:
            for line in file:
                if line.startswith("MemAvailable:"):
                    parts = line.split()
                    if len(parts) >= 2:
                        return int(parts[1]) * 1024
    except (OSError, ValueError):
        return None
    return None


def _huffman_kraft_memory_level(available: int | None = None) -> str:
    if available is None:
        available = _deep_beam_memory_available_bytes()
    if available is None:
        return "normal"
    if available < HUFFMAN_KRAFT_MEMORY_EMERGENCY_BYTES:
        return "emergency"
    if available < HUFFMAN_KRAFT_MEMORY_HARD_BYTES:
        return "hard"
    if available < HUFFMAN_KRAFT_MEMORY_SOFT_BYTES:
        return "soft"
    return "normal"


def _deep_beam_memory_guard_tripped() -> bool:
    available = _deep_beam_memory_available_bytes()
    return available is not None and available < DEEP_BEAM_MIN_AVAILABLE_MEMORY_BYTES


def probe_idat_deflate_deep_beam(
    data: bytes,
    *,
    budget: int = DEEP_BEAM_DEFAULT_BUDGET,
    max_depth: int = DEEP_BEAM_DEFAULT_MAX_DEPTH,
    beam_width: int = DEEP_BEAM_DEFAULT_WIDTH,
    top_candidates: int = DEEP_BEAM_DEFAULT_TOP_CANDIDATES,
    workers: str | int | None = "auto",
    gpu: bool | str | int | None = None,
    gpu_config: Any = None,
    checkpoint_every: int = DEEP_BEAM_DEFAULT_CHECKPOINT_EVERY,
    gpu_shard_size: int = DEEP_BEAM_DEFAULT_GPU_SHARD_SIZE,
    cpu_batch_size: int = DEEP_BEAM_DEFAULT_CPU_BATCH_SIZE,
    overlap_gpu_cpu: bool = False,
    profile_timing: bool = True,
    checkpoint_path: str = "",
    progress_path: str = "",
    seed_candidates: Iterable[IdatDeepBeamCandidate] | None = None,
    progress: QueueProgressCallback | None = None,
) -> IdatDeepBeamProbeResult:
    before = idat.analyze_idat_stream(data)
    strategy = "deep-beam"
    if not before.supported:
        return IdatDeepBeamProbeResult(before, None, (), 0, 0, 0, False, 0, 0, 0, strategy=strategy, reason=before.reason)
    if before.complete:
        return IdatDeepBeamProbeResult(before, None, (), 0, 0, 0, False, 0, 0, 0, strategy=strategy, reason="IDAT stream is already complete")
    try:
        chunks, root_stream = _all_chunks_and_idat_stream(data)
    except png.PngFormatError as exc:
        return IdatDeepBeamProbeResult(before, None, (), 0, 0, 0, False, 0, 0, 0, strategy=strategy, reason=str(exc))
    if not root_stream:
        return IdatDeepBeamProbeResult(before, None, (), 0, 0, 0, False, 0, 0, 0, strategy=strategy, reason="IDAT stream is missing")

    worker_count = _deep_beam_workers(workers)
    resolved_gpu_config = _deep_beam_gpu_config(gpu, gpu_config)
    gpu_requested = bool(getattr(resolved_gpu_config, "enabled", False))
    gpu_backend = "off" if not gpu_requested else "opengl-requested"
    gpu_warning = ""
    if not progress_path and checkpoint_path:
        progress_path = _deep_beam_progress_path_from_checkpoint(checkpoint_path)
    source_hash = _stream_state_key(root_stream)
    soft_max_depth = max(0, int(max_depth))
    hard_depth_limit = soft_max_depth + 1
    original_idat_count = sum(1 for chunk in chunks if chunk.chunk_type == b"IDAT")
    diagnostic = idat_local_deflate_diagnostic(data, analysis=before)
    window_start = diagnostic.window_start if diagnostic is not None else 0
    window_end = diagnostic.window_end if diagnostic is not None else min(len(root_stream), 0x120)

    root = IdatDeepBeamCandidate(
        data=data,
        stream=root_stream,
        operations=(),
        before=before,
        after=before,
        state_id=0,
        parent_id=None,
        source_offsets=(),
        score=_deep_beam_score(
            before,
            root_stream,
            0,
            data=data,
            original_idat_count=original_idat_count,
        ),
    )

    checkpoint_candidates, checkpoint_visited, next_state_id, resumed_states = _load_deep_beam_checkpoint(
        checkpoint_path,
        source_hash=source_hash,
        source_stream=root_stream,
        chunks=chunks,
        before=before,
        original_idat_count=original_idat_count,
        candidate_limit=max(int(beam_width), int(top_candidates), 1),
        max_operation_depth=hard_depth_limit,
    )
    if checkpoint_candidates:
        _compact_deep_beam_checkpoint_file(
            checkpoint_path,
            source_hash=source_hash,
            source_stream=root_stream,
        )
    seed_list: list[IdatDeepBeamCandidate] = []
    for seed in tuple(seed_candidates or ()):
        try:
            seed_stream = bytes(seed.stream)
        except (TypeError, ValueError):
            continue
        seed_hash = _stream_state_key(seed_stream)
        if seed_hash == _stream_state_key(root_stream):
            continue
        seed_data = _rebuild_with_single_idat_stream(chunks, seed_stream)
        seed_analysis = idat.analyze_idat_stream(
            seed_data,
            crc_provenance="rebuilt_by_chunklate",
            source_kind="candidate_from_periodic_seed",
        )
        operations = tuple(seed.operations)
        seed_list.append(
            IdatDeepBeamCandidate(
                data=seed_data,
                stream=seed_stream,
                operations=operations,
                before=before,
                after=seed_analysis,
                state_id=next_state_id,
                parent_id=seed.parent_id,
                source_offsets=tuple(operation.stream_offset for operation in operations),
                score=_deep_beam_score(
                    seed_analysis,
                    seed_stream,
                    len(operations),
                    data=seed_data,
                    original_idat_count=original_idat_count,
                ),
            )
        )
        next_state_id += 1
    progress_resume = _load_deep_beam_progress(
        progress_path,
        source_hash=source_hash,
        gpu_shard_size=gpu_shard_size,
    )
    gpu_done_shards = progress_resume.gpu_done_shards
    progress_resumed = bool(checkpoint_candidates) or progress_resume.resumed
    visited = {_stream_state_key(root_stream), *checkpoint_visited}
    initial_candidates = [*checkpoint_candidates, *seed_list]
    frontier = list(
        _deep_beam_ranked_unique(initial_candidates, limit=beam_width)
    ) if initial_candidates else [root]
    top = _deep_beam_ranked_unique([root, *initial_candidates], limit=top_candidates)
    best = next((candidate for candidate in top if is_material_improvement(before, candidate.after)), None)
    resume_floor = max(
        0,
        int(progress_resume.tested_candidates or 0),
        int(progress_resume.state_count or 0),
        int(progress_resume.visited_count or 0),
        int(next_state_id) - 1,
    )
    tested = resume_floor
    state_count = max(1, next_state_id, int(progress_resume.state_count or 0))
    reached_depth = max(
        min(int(progress_resume.depth or 0), hard_depth_limit),
        max((len(candidate.operations) for candidate in frontier), default=0),
    )
    budget_exhausted = False
    last_checkpoint_at = tested
    interrupted = False
    timing = IdatDeepBeamRuntimeStats()
    active_timing = timing if profile_timing else None
    checkpoint_written: set[str] = set(checkpoint_visited)

    def append_checkpoint_once(candidate: IdatDeepBeamCandidate, depth_value: int) -> None:
        if not checkpoint_path:
            return
        key = _stream_state_key(candidate.stream)
        if key in checkpoint_written:
            return
        _append_deep_beam_checkpoint(
            checkpoint_path,
            candidate,
            source_hash=source_hash,
            source_stream=root_stream,
            depth=depth_value,
        )
        checkpoint_written.add(key)

    wall_started_at = time.perf_counter()
    if checkpoint_path:
        for seed in seed_list:
            append_checkpoint_once(seed, len(seed.operations))
    worker_executor: ProcessPoolExecutor | None = None
    gpu_session: Any = None
    if worker_count > 1:
        try:
            worker_executor = ProcessPoolExecutor(max_workers=worker_count, initializer=_deep_beam_worker_init)
        except (OSError, RuntimeError, ValueError) as exc:
            worker_executor = None
            gpu_warning = gpu_warning or "worker pool unavailable: %s" % exc
    if gpu_requested:
        try:
            from . import ultimate_opengl_backend

            gpu_session = ultimate_opengl_backend.UltimateOpenGLAnalysisSession(resolved_gpu_config)
        except Exception as exc:
            gpu_session = None
            gpu_warning = gpu_warning or str(exc)

    widened_limits = (0x120, 0x400, 0x1000)
    stop_reason = ""
    hard_depth_limit_hit = False
    frontier_pool_limit = max(1, min(DEEP_BEAM_SUCCESSOR_KEEP_LIMIT, max(int(beam_width), int(top_candidates), 16)))
    successor_keep_limit = max(1, min(DEEP_BEAM_SUCCESSOR_KEEP_LIMIT, max(int(beam_width), int(top_candidates) * 4, 16)))

    def prune_working_frontiers() -> None:
        nonlocal next_frontier, fallback_frontier
        if len(next_frontier) > frontier_pool_limit * 2:
            next_frontier = list(_deep_beam_ranked_unique(next_frontier, limit=frontier_pool_limit))
        if len(fallback_frontier) > frontier_pool_limit * 2:
            fallback_frontier = list(_deep_beam_ranked_unique(fallback_frontier, limit=frontier_pool_limit))

    try:
        if progress is not None and progress_resumed:
            progress(strategy, min(tested, int(budget)), int(budget))
        while frontier:
            if tested >= int(budget):
                budget_exhausted = True
                stop_reason = "budget exhausted"
                break
            next_frontier: list[IdatDeepBeamCandidate] = []
            fallback_frontier: list[IdatDeepBeamCandidate] = []
            for parent in frontier:
                if _deep_beam_memory_guard_tripped():
                    stop_reason = "memory guard"
                    break
                if tested >= int(budget):
                    budget_exhausted = True
                    stop_reason = "budget exhausted"
                    break
                effective_depth = len(parent.operations) + 1
                if effective_depth > hard_depth_limit:
                    hard_depth_limit_hit = True
                    continue
                reached_depth = max(reached_depth, effective_depth)
                widened_limit = widened_limits[min(effective_depth - 1, len(widened_limits) - 1)]
                byte_bit_successors, byte_bit_tested, byte_gpu_backend, byte_gpu_warning = _deep_beam_byte_bit_successors(
                    parent,
                    before=before,
                    state_id_start=next_state_id,
                    original_idat_count=original_idat_count,
                    max_offsets=128 if effective_depth <= 2 else 256,
                    max_bits=192 if effective_depth <= 2 else 384,
                    widened_limit=widened_limit,
                    budget_left=max(0, int(budget) - tested),
                    workers=worker_count,
                    depth=effective_depth,
                    gpu_config=resolved_gpu_config,
                    gpu_done_shards=gpu_done_shards,
                    checkpoint_every=checkpoint_every,
                    worker_executor=worker_executor,
                    cpu_batch_size=cpu_batch_size,
                    gpu_shard_size=gpu_shard_size,
                    overlap_gpu_cpu=overlap_gpu_cpu,
                    gpu_session=gpu_session,
                    timing=active_timing,
                    successor_limit=successor_keep_limit,
                )
                tested += byte_bit_tested
                next_state_id += len(byte_bit_successors)
                if byte_gpu_backend != "off":
                    gpu_backend = byte_gpu_backend
                if byte_gpu_warning:
                    gpu_warning = byte_gpu_warning
                if tested < int(budget):
                    subprobe_successors, subprobe_tested = _deep_beam_subprobe_successors(
                        parent,
                        before=before,
                        state_id_start=next_state_id,
                        original_idat_count=original_idat_count,
                        depth=effective_depth,
                    )
                    tested += min(subprobe_tested, max(0, int(budget) - tested))
                    next_state_id += len(subprobe_successors)
                else:
                    subprobe_successors = []
                    subprobe_tested = 0
                state_count = max(state_count, next_state_id)

                for candidate in itertools.chain(byte_bit_successors, subprobe_successors):
                    key = _stream_state_key(candidate.stream)
                    if key in visited:
                        continue
                    visited.add(key)
                    if candidate.score <= parent.score and not is_material_improvement(before, candidate.after):
                        fallback_frontier.append(candidate)
                        prune_working_frontiers()
                        continue
                    next_frontier.append(candidate)
                    prune_working_frontiers()
                    if is_material_improvement(before, candidate.after):
                        if best is None or candidate.score > best.score:
                            best = candidate

                next_frontier = list(_deep_beam_ranked_unique(next_frontier, limit=frontier_pool_limit))
                fallback_frontier = list(_deep_beam_ranked_unique(fallback_frontier, limit=frontier_pool_limit))
                top = _deep_beam_ranked_unique(itertools.chain(top, next_frontier), limit=top_candidates)
                if checkpoint_path and next_frontier and tested - last_checkpoint_at >= int(checkpoint_every):
                    for candidate in top:
                        append_checkpoint_once(candidate, effective_depth)
                    last_checkpoint_at = tested
                if progress_path and (tested == 0 or tested % max(1, int(checkpoint_every)) < byte_bit_tested + subprobe_tested):
                    _write_deep_beam_progress(
                        progress_path,
                        source_hash=source_hash,
                        tested=tested,
                        depth=reached_depth,
                        max_depth=soft_max_depth,
                        budget=budget,
                        hard_depth_limit=hard_depth_limit,
                        state_count=state_count,
                        visited_count=len(visited),
                        best=best,
                        workers=worker_count,
                        gpu_backend=gpu_backend,
                        gpu_warning=gpu_warning,
                        gpu_done_shards=gpu_done_shards,
                        gpu_shard_size=gpu_shard_size,
                        timing=active_timing,
                    )
                if progress is not None:
                    progress(strategy, min(tested, int(budget)), int(budget))
                if best is not None and best.after.complete:
                    stop_reason = "complete candidate"
                    break
            if stop_reason == "memory guard":
                break
            if not next_frontier:
                if fallback_frontier and tested < int(budget):
                    next_frontier = list(
                        _deep_beam_ranked_unique(fallback_frontier, limit=beam_width)
                    )
                elif not stop_reason:
                    stop_reason = "hard depth limit reached" if hard_depth_limit_hit else "frontier exhausted"
                    break
            frontier = list(_deep_beam_ranked_unique(next_frontier, limit=beam_width))
            top = _deep_beam_ranked_unique(itertools.chain(top, frontier), limit=top_candidates)
            if best is not None and best.after.complete:
                stop_reason = "complete candidate"
                break
    except KeyboardInterrupt:
        interrupted = True
        gpu_warning = gpu_warning or "interrupted"
    finally:
        timing.wall_ms = (time.perf_counter() - wall_started_at) * 1000.0
        if gpu_session is not None:
            closer = getattr(gpu_session, "close", None)
            if callable(closer):
                closer()
        if worker_executor is not None:
            if interrupted:
                _ultimate_shutdown_parallel_executor(
                    worker_executor,
                    grace_seconds=0.05,
                )
            else:
                try:
                    worker_executor.shutdown()
                except TypeError:
                    worker_executor.shutdown()

    if checkpoint_path:
        for candidate in top:
            append_checkpoint_once(candidate, len(candidate.operations))
    if progress_path:
        _write_deep_beam_progress(
            progress_path,
            source_hash=source_hash,
            tested=tested,
            depth=reached_depth,
            max_depth=soft_max_depth,
            budget=budget,
            hard_depth_limit=hard_depth_limit,
            state_count=state_count,
            visited_count=len(visited),
            best=best,
            workers=worker_count,
            gpu_backend=gpu_backend,
            gpu_warning=gpu_warning,
            gpu_done_shards=gpu_done_shards,
            gpu_shard_size=gpu_shard_size,
            timing=active_timing,
            interrupted=interrupted,
        )
    if not stop_reason and budget_exhausted:
        stop_reason = "budget exhausted"
    reason = (
        "beam_width=%s; soft_max_depth=%s; hard_depth_limit=%s; reached_depth=%s; top=%s; workers=%s; resumed=%s; stop=%s; source=%s"
        % (beam_width, soft_max_depth, hard_depth_limit, reached_depth, len(top), worker_count, resumed_states, stop_reason or "unknown", source_hash)
    )
    return IdatDeepBeamProbeResult(
        before,
        best,
        tuple(top),
        window_start,
        window_end,
        tested,
        budget_exhausted,
        reached_depth,
        state_count,
        len(visited),
        checkpoint_path=checkpoint_path,
        progress_path=progress_path,
        progress_resumed=progress_resumed,
        workers=worker_count,
        gpu_requested=gpu_requested,
        gpu_backend=gpu_backend,
        strategy=strategy,
        reason=reason,
        gpu_warning=gpu_warning,
        gpu_shards_done=len(gpu_done_shards),
        interrupted=interrupted,
        timing=timing,
    )


def _flip_stream_bits(stream: bytes, bit_offsets: Iterable[int]) -> bytes | None:
    candidate = bytearray(stream)
    for bit_offset in bit_offsets:
        bit_offset = int(bit_offset)
        if bit_offset < 0 or bit_offset >= len(candidate) * 8:
            return None
        candidate[bit_offset // 8] ^= 1 << (bit_offset % 8)
    return bytes(candidate)


def _stream_bit_range_to_bytes(stream: bytes, bit_start: int, bit_end: int) -> bytes:
    bit_start = max(0, int(bit_start))
    bit_end = max(bit_start, min(int(bit_end), len(stream) * 8))
    start = bit_start // 8
    end = (bit_end + 7) // 8
    return stream[start:end]


def _replace_stream_bits_preserve_length(
    stream: bytes,
    bit_start: int,
    bit_end: int,
    bits: tuple[int, ...],
) -> bytes | None:
    bit_count = len(stream) * 8
    bit_start = int(bit_start)
    bit_end = int(bit_end)
    if bit_start < 0 or bit_end < bit_start or bit_end > bit_count:
        return None
    if not bits and bit_start == bit_end:
        return stream
    replacement_width = len(bits)
    replacement = 0
    for index, bit in enumerate(bits):
        replacement |= (int(bit) & 1) << index
    value = int.from_bytes(stream, "little")
    low = value & ((1 << bit_start) - 1)
    high = value >> bit_end
    shifted = low | (replacement << bit_start) | (high << (bit_start + replacement_width))
    mask = (1 << bit_count) - 1 if bit_count else 0
    return (shifted & mask).to_bytes(len(stream), "little")


def _shift_stream_delete_bit(stream: bytes, bit_offset: int) -> bytes | None:
    bit_count = len(stream) * 8
    bit_offset = int(bit_offset)
    if bit_offset < 0 or bit_offset >= bit_count:
        return None
    value = int.from_bytes(stream, "little")
    low = value & ((1 << bit_offset) - 1)
    high = value >> (bit_offset + 1)
    shifted = low | (high << bit_offset)
    return shifted.to_bytes(len(stream), "little")


def _shift_stream_insert_bit(stream: bytes, bit_offset: int, bit_value: int) -> bytes | None:
    bit_count = len(stream) * 8
    bit_offset = int(bit_offset)
    if bit_offset < 0 or bit_offset >= bit_count:
        return None
    value = int.from_bytes(stream, "little")
    low = value & ((1 << bit_offset) - 1)
    high = value >> bit_offset
    mask = (1 << bit_count) - 1
    shifted = low | ((int(bit_value) & 1) << bit_offset) | (high << (bit_offset + 1))
    return (shifted & mask).to_bytes(len(stream), "little")


def mutate_idat_stream_bit_shift(
    data: bytes,
    bit_offset: int,
    edit_kind: str,
    *,
    bit_value: int = 0,
    before_analysis: idat.IdatStreamAnalysis | None = None,
) -> IdatDeflateCandidate | None:
    bit_offset = int(bit_offset)
    before = before_analysis or idat.analyze_idat_stream(data)
    try:
        chunks, idat_stream = _all_chunks_and_idat_stream(data)
    except png.PngFormatError:
        return None
    if not idat_stream or bit_offset < 0 or bit_offset >= len(idat_stream) * 8:
        return None

    edit = str(edit_kind).strip().lower()
    if edit == "bit-delete":
        shifted_stream = _shift_stream_delete_bit(idat_stream, bit_offset)
        old_bit = (idat_stream[bit_offset // 8] >> (bit_offset % 8)) & 1
        new_bit = 0
    elif edit == "bit-insert":
        shifted_stream = _shift_stream_insert_bit(idat_stream, bit_offset, bit_value)
        old_bit = 0
        new_bit = int(bit_value) & 1
    else:
        return None
    if shifted_stream is None or shifted_stream == idat_stream:
        return None

    location = _locate_idat_stream_offset(
        tuple(chunk for chunk in chunks if chunk.chunk_type == b"IDAT"),
        bit_offset // 8,
    )
    if location is None:
        return None
    chunk, idat_index, idat_offset = location
    file_offset = chunk.offset + 8 + idat_offset

    stream_offset = bit_offset // 8
    context_start = max(0, stream_offset - 4)
    context_end = min(len(idat_stream), stream_offset + 5)
    candidate_data = _rebuild_with_single_idat_stream(chunks, shifted_stream)
    return IdatDeflateCandidate(
        data=candidate_data,
        stream_offset=stream_offset,
        file_offset=file_offset,
        idat_index=idat_index,
        idat_offset=idat_offset,
        old_byte=old_bit,
        new_byte=new_bit,
        before=before,
        after=idat.analyze_idat_stream(
            candidate_data,
            crc_provenance="rebuilt_by_chunklate",
            source_kind="candidate_from_original",
        ),
        edit_kind=edit,
        old_bytes=idat_stream[context_start:context_end],
        new_bytes=shifted_stream[context_start:context_end],
        bit_offsets=(bit_offset,),
    )


def mutate_idat_stream_bit_range_replace(
    data: bytes,
    bit_start: int,
    bit_end: int,
    bits: tuple[int, ...],
    *,
    before_analysis: idat.IdatStreamAnalysis | None = None,
) -> IdatDeflateCandidate | None:
    bit_start = int(bit_start)
    bit_end = int(bit_end)
    before = before_analysis or idat.analyze_idat_stream(data)
    try:
        chunks, idat_stream = _all_chunks_and_idat_stream(data)
    except png.PngFormatError:
        return None
    if not idat_stream or bit_start < 0 or bit_end < bit_start or bit_end > len(idat_stream) * 8:
        return None

    candidate_stream = _replace_stream_bits_preserve_length(idat_stream, bit_start, bit_end, bits)
    if candidate_stream is None or candidate_stream == idat_stream:
        return None

    idat_chunks = tuple(chunk for chunk in chunks if chunk.chunk_type == b"IDAT")
    location = _locate_idat_stream_offset(idat_chunks, bit_start // 8)
    if location is None:
        return None
    chunk, idat_index, idat_offset = location
    file_offset = chunk.offset + 8 + idat_offset

    stream_offset = bit_start // 8
    context_start = max(0, stream_offset - 4)
    context_end = min(len(idat_stream), max(stream_offset + 5, (bit_end + 7) // 8 + 4))
    candidate_data = _rebuild_with_single_idat_stream(chunks, candidate_stream)
    return IdatDeflateCandidate(
        data=candidate_data,
        stream_offset=stream_offset,
        file_offset=file_offset,
        idat_index=idat_index,
        idat_offset=idat_offset,
        old_byte=idat_stream[stream_offset],
        new_byte=candidate_stream[stream_offset],
        before=before,
        after=idat.analyze_idat_stream(
            candidate_data,
            crc_provenance="rebuilt_by_chunklate",
            source_kind="candidate_from_original",
        ),
        edit_kind="semantic-token",
        old_bytes=idat_stream[context_start:context_end],
        new_bytes=candidate_stream[context_start:context_end],
        bit_offsets=(bit_start,),
    )


def mutate_idat_stream_bit_range_replacements(
    data: bytes,
    replacements: Iterable[tuple[int, int, tuple[int, ...]]],
    *,
    edit_kind: str,
    before_analysis: idat.IdatStreamAnalysis | None = None,
) -> IdatDeflateCandidate | None:
    edits = tuple(
        (int(bit_start), int(bit_end), tuple(int(bit) & 1 for bit in bits))
        for bit_start, bit_end, bits in replacements
    )
    if not edits:
        return None

    before = before_analysis or idat.analyze_idat_stream(data)
    try:
        chunks, idat_stream = _all_chunks_and_idat_stream(data)
    except png.PngFormatError:
        return None
    if not idat_stream:
        return None

    candidate_stream = idat_stream
    for bit_start, bit_end, bits in sorted(edits, key=lambda item: item[0], reverse=True):
        if bit_start < 0 or bit_end < bit_start or bit_end > len(candidate_stream) * 8:
            return None
        candidate_stream = _replace_stream_bits_preserve_length(candidate_stream, bit_start, bit_end, bits)
        if candidate_stream is None:
            return None
    if candidate_stream == idat_stream:
        return None

    first_bit = min(bit_start for bit_start, _bit_end, _bits in edits)
    last_bit = max(bit_end for _bit_start, bit_end, _bits in edits)
    idat_chunks = tuple(chunk for chunk in chunks if chunk.chunk_type == b"IDAT")
    location = _locate_idat_stream_offset(idat_chunks, first_bit // 8)
    if location is None:
        return None
    chunk, idat_index, idat_offset = location
    file_offset = chunk.offset + 8 + idat_offset

    stream_offset = first_bit // 8
    context_start = max(0, stream_offset - 4)
    context_end = min(len(idat_stream), max(stream_offset + 5, (last_bit + 7) // 8 + 4))
    candidate_data = _rebuild_with_single_idat_stream(chunks, candidate_stream)
    return IdatDeflateCandidate(
        data=candidate_data,
        stream_offset=stream_offset,
        file_offset=file_offset,
        idat_index=idat_index,
        idat_offset=idat_offset,
        old_byte=idat_stream[stream_offset],
        new_byte=candidate_stream[stream_offset],
        before=before,
        after=idat.analyze_idat_stream(
            candidate_data,
            crc_provenance="rebuilt_by_chunklate",
            source_kind="candidate_from_original",
        ),
        edit_kind=edit_kind,
        old_bytes=idat_stream[context_start:context_end],
        new_bytes=candidate_stream[context_start:context_end],
        bit_offsets=tuple(bit_start for bit_start, _bit_end, _bits in edits),
    )


def _bits_for_lsb_code(code: int, width: int) -> tuple[int, ...]:
    return tuple((int(code) >> index) & 1 for index in range(int(width)))


def _dynamic_code_length_symbol_codes(
    trace: deflate_header.DynamicHeaderTrace,
) -> dict[int, tuple[int, int]]:
    table, _max_bits = deflate_header._build_huffman_table(
        list(trace.code_length_lengths),
        allow_single=True,
        allow_incomplete=True,
    )
    return {int(symbol): (int(code), int(width)) for (code, width), symbol in table.items()}


def _stream_bits_value(stream: bytes, bit_start: int, bit_end: int) -> int:
    value = 0
    for index, bit_offset in enumerate(range(int(bit_start), int(bit_end))):
        value |= ((stream[bit_offset // 8] >> (bit_offset % 8)) & 1) << index
    return value


def _dynamic_code_length_alphabet_orders() -> tuple[tuple[str, tuple[int, ...]], ...]:
    natural = tuple(range(19))
    repeat_first_linear = (16, 17, 18) + tuple(range(16))
    literal_repeat_tail = tuple(range(16)) + (16, 17, 18)
    return (
        ("natural-default", natural),
        ("repeat-first-linear", repeat_first_linear),
        ("literal-repeat-tail", literal_repeat_tail),
    )


def _dynamic_alphabet_rewrite_replacements(
    stream: bytes,
    trace: deflate_header.DynamicHeaderTrace,
    source_order: tuple[int, ...],
) -> tuple[tuple[int, int, tuple[int, ...]], ...]:
    entries = tuple(trace.code_length_bits)
    if not entries:
        return ()
    values_by_source_symbol: dict[int, int] = {}
    for index, (_standard_symbol, bit_start, bit_end) in enumerate(entries):
        if index >= len(source_order):
            break
        values_by_source_symbol[int(source_order[index])] = _stream_bits_value(stream, bit_start, bit_end)

    replacements: list[tuple[int, int, tuple[int, ...]]] = []
    for standard_symbol, bit_start, bit_end in entries:
        old_value = _stream_bits_value(stream, bit_start, bit_end)
        new_value = values_by_source_symbol.get(int(standard_symbol), 0)
        if new_value != old_value:
            replacements.append((bit_start, bit_end, _bits_for_lsb_code(new_value, bit_end - bit_start)))
    return tuple(replacements)


def _apply_stream_bit_replacements(
    stream: bytes,
    replacements: Iterable[tuple[int, int, tuple[int, ...]]],
) -> bytes | None:
    candidate_stream = stream
    for bit_start, bit_end, bits in sorted(replacements, key=lambda item: item[0], reverse=True):
        candidate_stream = _replace_stream_bits_preserve_length(candidate_stream, bit_start, bit_end, bits)
        if candidate_stream is None:
            return None
    return candidate_stream


def _apply_payload_bit_replacements(
    payload: bytes,
    replacements: Iterable[tuple[int, int, tuple[int, ...]]],
) -> bytes | None:
    candidate = bytes(payload)
    for bit_start, bit_end, bits in sorted(replacements, key=lambda item: item[0], reverse=True):
        candidate = _replace_stream_bits_preserve_length(candidate, bit_start, bit_end, bits)
        if candidate is None:
            return None
    return candidate


def _stream_with_target_payload(
    idat_stream: bytes,
    target_stream_start: int,
    target_stream_end: int,
    payload: bytes,
) -> bytes:
    return (
        idat_stream[:target_stream_start]
        + bytes(payload)
        + idat_stream[target_stream_end:]
    )


def _crc32_idat_payload(payload: bytes) -> int:
    return zlib.crc32(b"IDAT" + bytes(payload)) & 0xFFFFFFFF


def _gf2_low_weight_solutions(
    columns: tuple[int, ...],
    target_delta: int,
    *,
    max_solutions: int,
) -> tuple[int, ...]:
    variable_count = len(columns)
    if variable_count <= 0 or max_solutions <= 0:
        return ()
    mask_limit = (1 << variable_count) - 1
    equations: list[tuple[int, int]] = []
    for crc_bit in range(32):
        row = 0
        for variable_index, column in enumerate(columns):
            if int(column) & (1 << crc_bit):
                row |= 1 << variable_index
        equations.append((row, (int(target_delta) >> crc_bit) & 1))

    basis: dict[int, tuple[int, int]] = {}
    for row, value in equations:
        row &= mask_limit
        value &= 1
        while row:
            pivot = row.bit_length() - 1
            existing = basis.get(pivot)
            if existing is None:
                basis[pivot] = (row, value)
                break
            row ^= existing[0]
            value ^= existing[1]
        else:
            if value:
                return ()

    pivots = set(basis)
    free_vars = [index for index in range(variable_count) if index not in pivots]

    def complete_solution(free_value: int) -> int:
        solution = 0
        for bit_index, variable_index in enumerate(free_vars):
            if free_value & (1 << bit_index):
                solution |= 1 << variable_index
        for pivot in sorted(pivots):
            row, value = basis[pivot]
            known = (row & ~(1 << pivot)) & solution
            if (known.bit_count() & 1) ^ value:
                solution |= 1 << pivot
            else:
                solution &= ~(1 << pivot)
        return solution & mask_limit

    solutions: list[int] = []
    if not free_vars:
        solution = complete_solution(0)
        return (solution,) if solution else ()
    free_count = len(free_vars)
    for weight in range(free_count + 1):
        for combination in itertools.combinations(range(free_count), weight):
            free_value = 0
            for bit_index in combination:
                free_value |= 1 << bit_index
            solution = complete_solution(free_value)
            if solution:
                solutions.append(solution)
            if len(solutions) >= int(max_solutions):
                return tuple(sorted(dict.fromkeys(solutions), key=lambda item: (item.bit_count(), item)))
    return tuple(sorted(dict.fromkeys(solutions), key=lambda item: (item.bit_count(), item)))


def _crc_guided_solutions_for_payload_bits(
    payload: bytes,
    payload_bits: tuple[int, ...],
    target_crc: int,
    *,
    max_solutions: int,
) -> tuple[tuple[int, ...], ...]:
    bits = tuple(dict.fromkeys(int(bit) for bit in payload_bits if 0 <= int(bit) < len(payload) * 8))
    if not bits:
        return ()
    current_crc = _crc32_idat_payload(payload)
    target_crc = int(target_crc) & 0xFFFFFFFF
    target_delta = current_crc ^ target_crc
    if target_delta == 0:
        return ()
    columns: list[int] = []
    for bit_offset in bits:
        candidate = bytearray(payload)
        candidate[bit_offset // 8] ^= 1 << (bit_offset % 8)
        columns.append(_crc32_idat_payload(candidate) ^ current_crc)
    solutions: list[tuple[int, ...]] = []
    for mask in _gf2_low_weight_solutions(
        tuple(columns),
        target_delta,
        max_solutions=max_solutions,
    ):
        solution = tuple(bits[index] for index in range(len(bits)) if mask & (1 << index))
        if solution:
            solutions.append(solution)
    return tuple(solutions)


def _flip_payload_bits(payload: bytes, payload_bits: Iterable[int]) -> bytes | None:
    candidate = bytearray(payload)
    for bit_offset in payload_bits:
        bit_offset = int(bit_offset)
        if bit_offset < 0 or bit_offset >= len(candidate) * 8:
            return None
        candidate[bit_offset // 8] ^= 1 << (bit_offset % 8)
    return bytes(candidate)


def _dynamic_crc_guided_target_chunk(
    chunks: tuple[png.PngChunk, ...],
    before: idat.IdatStreamAnalysis,
) -> png.PngChunk | None:
    idat_chunks = tuple(chunk for chunk in chunks if chunk.chunk_type == b"IDAT")
    if before.error_file_offset is not None:
        error_file_offset = int(before.error_file_offset)
        for chunk in idat_chunks:
            payload_start = chunk.offset + 8
            payload_end = payload_start + chunk.length
            if payload_start <= error_file_offset < payload_end and chunk.crc != chunk.computed_crc:
                return chunk
    return next((chunk for chunk in idat_chunks if chunk.crc != chunk.computed_crc), None)


def _stream_bits_for_target_payload(
    bits: Iterable[int],
    *,
    target_stream_start: int,
    target_stream_end: int,
) -> tuple[int, ...]:
    start_bit = int(target_stream_start) * 8
    end_bit = int(target_stream_end) * 8
    return tuple(
        dict.fromkeys(
            int(bit) - start_bit
            for bit in bits
            if start_bit <= int(bit) < end_bit
        )
    )


def _dynamic_crc_guided_bit_groups(
    trace: deflate_header.DynamicHeaderTrace,
    idat_stream: bytes,
    *,
    target_stream_start: int,
    target_stream_end: int,
    max_group_bits: int,
) -> tuple[tuple[str, tuple[int, ...]], ...]:
    stream_bit_limit = len(idat_stream) * 8
    groups: list[tuple[str, tuple[int, ...]]] = []

    def add_group(label: str, stream_bits: Iterable[int]) -> None:
        payload_bits = _stream_bits_for_target_payload(
            tuple(dict.fromkeys(int(bit) for bit in stream_bits if 0 <= int(bit) < stream_bit_limit)),
            target_stream_start=target_stream_start,
            target_stream_end=target_stream_end,
        )
        if not payload_bits:
            return
        for index in range(0, len(payload_bits), max_group_bits):
            chunk = payload_bits[index : index + max_group_bits]
            if chunk:
                groups.append(("%s%s" % (label, "" if index == 0 else ":%s" % (index // max_group_bits)), chunk))

    add_group(
        "counts",
        itertools.chain.from_iterable(
            range(start, end) for _name, start, end in trace.count_bits
        ),
    )
    add_group(
        "alphabet",
        itertools.chain.from_iterable(
            range(start, end) for _symbol, start, end in trace.code_length_bits
        ),
    )

    eob_index = 256
    boundary = int(trace.hlit) if trace.hlit is not None else eob_index
    eob_bits: list[int] = []
    boundary_bits: list[int] = []
    repeat_bits: list[int] = []
    tail_bits: list[int] = []
    tail_start = max(0, len(trace.tokens) - 32)
    for token_index, token in enumerate(trace.tokens):
        token_bits = _dynamic_token_bits(token, bit_limit=stream_bit_limit)
        if token.length_start <= eob_index < token.length_end:
            eob_bits.extend(token_bits)
        if (
            token.length_start <= boundary <= token.length_end
            or abs(token.length_start - boundary) <= 8
            or abs(token.length_end - boundary) <= 8
        ):
            boundary_bits.extend(token_bits)
        if token.symbol in (16, 17, 18):
            repeat_bits.extend(token_bits)
        if token_index >= tail_start:
            tail_bits.extend(token_bits)
    add_group("eob", eob_bits)
    add_group("boundary", boundary_bits)
    add_group("repeat", repeat_bits)
    add_group("tail", tail_bits)
    add_group(
        "priority",
        _dynamic_huffman_suspect_bits(
            trace,
            idat_stream,
            max_bits=max(1, max_group_bits * 4),
        ),
    )

    deduped: list[tuple[str, tuple[int, ...]]] = []
    seen: set[tuple[int, ...]] = set()
    for label, bits in groups:
        key = tuple(bits)
        if key in seen:
            continue
        seen.add(key)
        deduped.append((label, key))
    return tuple(deduped)


def _payload_after_stream_replacements(
    idat_stream: bytes,
    payload: bytes,
    replacements: Iterable[tuple[int, int, tuple[int, ...]]],
    *,
    target_stream_start: int,
    target_stream_end: int,
) -> bytes | None:
    target_start_bit = int(target_stream_start) * 8
    target_end_bit = int(target_stream_end) * 8
    payload_replacements: list[tuple[int, int, tuple[int, ...]]] = []
    for bit_start, bit_end, bits in replacements:
        if bit_start < target_start_bit or bit_end > target_end_bit:
            return None
        payload_replacements.append((bit_start - target_start_bit, bit_end - target_start_bit, bits))
    if not payload_replacements:
        return None
    return _apply_payload_bit_replacements(payload, payload_replacements)


def _dynamic_crc_guided_fixed_payloads(
    idat_stream: bytes,
    payload: bytes,
    trace: deflate_header.DynamicHeaderTrace,
    *,
    target_stream_start: int,
    target_stream_end: int,
    max_items: int,
) -> tuple[tuple[str, bytes, tuple[int, ...]], ...]:
    items: list[tuple[str, bytes, tuple[int, ...]]] = []
    seen_payloads: set[bytes] = set()

    def add_payload(edit_kind: str, replacements: tuple[tuple[int, int, tuple[int, ...]], ...]) -> None:
        if len(items) >= int(max_items):
            return
        fixed_payload = _payload_after_stream_replacements(
            idat_stream,
            payload,
            replacements,
            target_stream_start=target_stream_start,
            target_stream_end=target_stream_end,
        )
        if fixed_payload is None or fixed_payload == payload or fixed_payload in seen_payloads:
            return
        seen_payloads.add(fixed_payload)
        items.append(
            (
                edit_kind,
                fixed_payload,
                tuple(bit_start for bit_start, _bit_end, _bits in replacements),
            )
        )

    try:
        symbol_codes = _dynamic_code_length_symbol_codes(trace)
    except Exception:
        symbol_codes = {}
    if symbol_codes:
        for token in _dynamic_semantic_priority_tokens(trace, limit=32):
            bit_start = int(token.bit_start)
            bit_end = _dynamic_length_token_bit_end(token)
            for replacement_bits in _dynamic_semantic_token_options(token, symbol_codes):
                add_payload(
                    "crc-guided-semantic",
                    ((bit_start, bit_end, replacement_bits),),
                )
                if len(items) >= int(max_items):
                    return tuple(items)

    for _label, source_order in _dynamic_code_length_alphabet_orders():
        replacements = _dynamic_alphabet_rewrite_replacements(idat_stream, trace, source_order)
        add_payload("crc-guided-alphabet", replacements)
        if len(items) >= int(max_items):
            return tuple(items)
    return tuple(items)


def _crc_guided_candidate_from_payload(
    data: bytes,
    *,
    before: idat.IdatStreamAnalysis,
    chunks: tuple[png.PngChunk, ...],
    idat_chunks: tuple[png.PngChunk, ...],
    target_chunk: png.PngChunk,
    target_stream_start: int,
    original_payload: bytes,
    payload: bytes,
    global_bit_offsets: tuple[int, ...],
    edit_kind: str,
) -> IdatDeflateCandidate | None:
    if payload == original_payload:
        return None
    if _crc32_idat_payload(payload) != int(target_chunk.crc):
        return None
    target_start_bit = int(target_stream_start) * 8
    touched_bytes = tuple(
        sorted(
            {
                (int(bit) - target_start_bit) // 8
                for bit in global_bit_offsets
                if target_start_bit <= int(bit) < target_start_bit + len(payload) * 8
            }
        )
    )
    if not touched_bytes:
        touched_bytes = tuple(
            index
            for index, (old, new) in enumerate(zip(original_payload, payload))
            if old != new
        )
    if not touched_bytes:
        return None

    candidate = bytearray(data)
    payload_start = target_chunk.offset + 8
    payload_end = payload_start + target_chunk.length
    candidate[payload_start:payload_end] = payload
    candidate_data = bytes(candidate)

    first_payload_offset = touched_bytes[0]
    first_file_offset = payload_start + first_payload_offset
    first_stream_offset = target_stream_start + first_payload_offset
    idat_index = _idat_chunk_index(idat_chunks, target_chunk)
    old_bytes = bytes(original_payload[offset] for offset in touched_bytes)
    new_bytes = bytes(payload[offset] for offset in touched_bytes)
    return IdatDeflateCandidate(
        data=candidate_data,
        stream_offset=first_stream_offset,
        file_offset=first_file_offset,
        idat_index=idat_index,
        idat_offset=first_payload_offset,
        old_byte=original_payload[first_payload_offset],
        new_byte=payload[first_payload_offset],
        before=before,
        after=idat.analyze_idat_stream(candidate_data),
        edit_kind=edit_kind,
        old_bytes=old_bytes,
        new_bytes=new_bytes,
        bit_offsets=tuple(sorted(global_bit_offsets)),
    )


def _dynamic_alphabet_field_priority(
    entry: tuple[int, int, int],
) -> tuple[int, int, int]:
    symbol, bit_start, _bit_end = entry
    if symbol in (16, 17, 18):
        rank = 0
    elif symbol == 0:
        rank = 1
    elif symbol in (7, 8, 9, 6, 10):
        rank = 2
    else:
        rank = 3
    return rank, int(symbol), int(bit_start)


def probe_dynamic_huffman_alphabet_candidates(
    data: bytes,
    *,
    budget: int = 8192,
    max_fields: int = 17,
    max_field_edits: int = 2,
    progress: QueueProgressCallback | None = None,
) -> IdatDeflateProbeResult:
    before = idat.analyze_idat_stream(data)
    strategy = "dynamic-huffman-alphabet"
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
    if before_header.status not in ("invalid_huffman_lengths", "bad_code_length_tree") or before_header.btype != 2:
        return IdatDeflateProbeResult(
            before,
            None,
            0,
            0,
            0,
            False,
            strategy,
            "unsupported header status: %s" % before_header.status,
        )

    trace = deflate_header.trace_dynamic_header(idat_stream)
    entries = tuple(sorted(trace.code_length_bits, key=_dynamic_alphabet_field_priority))[:max_fields]
    if trace.btype != 2 or not entries:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, trace.summary)

    window_start = min(bit_start for _symbol, bit_start, _bit_end in entries) // 8
    window_end = (max(bit_end for _symbol, _bit_start, bit_end in entries) + 7) // 8
    best: IdatDeflateCandidate | None = None
    best_score = analysis_score(before)
    diagnostic_best: IdatDeflateCandidate | None = None
    diagnostic_score = analysis_score(before)
    tested = 0
    order_headers = 0
    alphabet_headers = 0
    valid_headers = 0
    best_scanlines = before.usable_scanlines
    budget_exhausted = False
    seen: set[tuple[tuple[int, int, tuple[int, ...]], ...]] = set()

    def result() -> IdatDeflateProbeResult:
        reason = (
            "orders=%s; fields=%s; alphabet_headers=%s; valid_headers=%s; best_scanlines=%s; %s"
            % (
                order_headers,
                len(entries),
                alphabet_headers,
                valid_headers,
                best_scanlines,
                trace.summary,
            )
        )
        return IdatDeflateProbeResult(
            before,
            best,
            window_start,
            window_end,
            tested,
            budget_exhausted,
            strategy,
            reason,
            diagnostic_best=diagnostic_best,
        )

    def consider_replacements(
        replacements: tuple[tuple[int, int, tuple[int, ...]], ...],
        *,
        edit_kind: str,
    ) -> bool:
        nonlocal best, best_score, diagnostic_best, diagnostic_score
        nonlocal tested, order_headers, alphabet_headers, valid_headers, best_scanlines, budget_exhausted
        if not replacements:
            return False
        key = tuple(sorted(replacements))
        if key in seen:
            return False
        seen.add(key)
        if tested >= budget:
            budget_exhausted = True
            return False
        tested += 1
        if progress is not None and tested % 100 == 0:
            progress(strategy, tested, budget)

        candidate_stream = _apply_stream_bit_replacements(idat_stream, replacements)
        if candidate_stream is None or candidate_stream == idat_stream:
            return False
        candidate_trace = deflate_header.trace_dynamic_header(candidate_stream)
        if candidate_trace.btype != 2:
            return False
        if (
            candidate_trace.hlit is not None
            and candidate_trace.hdist is not None
            and candidate_trace.length_count == int(candidate_trace.hlit) + int(candidate_trace.hdist)
        ):
            alphabet_headers += 1
        try:
            header = deflate_header.analyze_deflate_header(candidate_stream)
        except Exception:
            return False
        if not header.ok or header.btype != before_header.btype:
            return False
        valid_headers += 1
        candidate = mutate_idat_stream_bit_range_replacements(
            data,
            replacements,
            edit_kind=edit_kind,
            before_analysis=before,
        )
        if candidate is None:
            return False

        candidate_score = analysis_score(candidate.after)
        best_scanlines = max(best_scanlines, candidate.after.usable_scanlines)
        if candidate_score > diagnostic_score:
            diagnostic_best = candidate
            diagnostic_score = candidate_score
        if not is_material_improvement(before, candidate.after):
            return False
        if candidate_score <= best_score:
            return False
        best = candidate
        best_score = candidate_score
        return bool(candidate.after.complete)

    if progress is not None:
        progress(strategy, 0, max(0, budget))

    for _label, source_order in _dynamic_code_length_alphabet_orders():
        if tested >= budget:
            budget_exhausted = True
            if progress is not None:
                progress(strategy, tested, budget)
            return result()
        try:
            alternate_trace = deflate_header.trace_dynamic_header(
                idat_stream,
                code_length_order=source_order,
            )
        except Exception:
            alternate_trace = None
        if (
            alternate_trace is not None
            and alternate_trace.hlit is not None
            and alternate_trace.hdist is not None
            and alternate_trace.length_count == int(alternate_trace.hlit) + int(alternate_trace.hdist)
        ):
            order_headers += 1
        replacements = _dynamic_alphabet_rewrite_replacements(idat_stream, trace, source_order)
        if consider_replacements(replacements, edit_kind="alphabet-order"):
            if progress is not None:
                progress(strategy, tested, budget)
            return result()

    fields = entries[:max(1, max_fields)]
    max_width = max(1, int(max_field_edits))
    for width in range(1, max_width + 1):
        for field_group in itertools.combinations(fields, width):
            old_values = tuple(
                _stream_bits_value(idat_stream, bit_start, bit_end)
                for _symbol, bit_start, bit_end in field_group
            )
            for values in itertools.product(range(8), repeat=width):
                if values == old_values:
                    continue
                if tested >= budget:
                    budget_exhausted = True
                    if progress is not None:
                        progress(strategy, tested, budget)
                    return result()
                replacements = tuple(
                    (
                        bit_start,
                        bit_end,
                        _bits_for_lsb_code(value, bit_end - bit_start),
                    )
                    for value, (_symbol, bit_start, bit_end) in zip(values, field_group)
                )
                if consider_replacements(replacements, edit_kind="alphabet-field"):
                    if progress is not None:
                        progress(strategy, tested, budget)
                    return result()

    if progress is not None:
        progress(strategy, tested, budget)
    return result()


def probe_dynamic_huffman_crc_guided_candidates(
    data: bytes,
    *,
    budget: int = 65536,
    max_group_bits: int = 48,
    max_solutions_per_group: int = 256,
    max_fixed_payloads: int = 256,
    progress: QueueProgressCallback | None = None,
) -> IdatDeflateProbeResult:
    before = idat.analyze_idat_stream(data)
    strategy = "dynamic-huffman-crc-guided"
    if not before.supported:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, before.reason)
    if before.complete:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, "IDAT stream is already complete")
    if before.decompressed_size != 0:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, "deflate already produced bytes")

    try:
        chunks, idat_stream = _all_chunks_and_idat_stream(data)
    except png.PngFormatError as exc:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, str(exc))
    idat_chunks = tuple(chunk for chunk in chunks if chunk.chunk_type == b"IDAT")
    target_chunk = _dynamic_crc_guided_target_chunk(chunks, before)
    if target_chunk is None:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, "no mismatching IDAT CRC target")
    target_range = _idat_stream_range_for_chunk_offset(chunks, target_chunk.offset)
    if target_range is None:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, "target IDAT stream range unavailable")
    target_stream_start, target_stream_end = target_range

    before_header = before.deflate_header or deflate_header.analyze_deflate_header(idat_stream)
    if before_header.status not in ("invalid_huffman_lengths", "bad_code_length_tree") or before_header.btype != 2:
        return IdatDeflateProbeResult(
            before,
            None,
            target_stream_start,
            target_stream_end,
            0,
            False,
            strategy,
            "unsupported header status: %s" % before_header.status,
        )

    trace = deflate_header.trace_dynamic_header(idat_stream)
    if trace.btype != 2:
        return IdatDeflateProbeResult(before, None, target_stream_start, target_stream_end, 0, False, strategy, trace.summary)

    groups = _dynamic_crc_guided_bit_groups(
        trace,
        idat_stream,
        target_stream_start=target_stream_start,
        target_stream_end=target_stream_end,
        max_group_bits=max_group_bits,
    )
    if not groups:
        return IdatDeflateProbeResult(before, None, target_stream_start, target_stream_end, 0, False, strategy, "no CRC-guided bit groups")

    original_payload = bytes(target_chunk.data)
    target_crc = int(target_chunk.crc)
    best: IdatDeflateCandidate | None = None
    best_score = analysis_score(before)
    diagnostic_best: IdatDeflateCandidate | None = None
    diagnostic_score = analysis_score(before)
    tested = 0
    crc_solutions = 0
    valid_headers = 0
    best_scanlines = before.usable_scanlines
    budget_exhausted = False
    seen_payloads: set[bytes] = set()

    def result() -> IdatDeflateProbeResult:
        reason = (
            "groups=%s; crc_solutions=%s; valid_headers=%s; best_scanlines=%s; target_idat=%s; %s"
            % (
                len(groups),
                crc_solutions,
                valid_headers,
                best_scanlines,
                _idat_chunk_index(idat_chunks, target_chunk),
                trace.summary,
            )
        )
        return IdatDeflateProbeResult(
            before,
            best,
            target_stream_start,
            target_stream_end,
            tested,
            budget_exhausted,
            strategy,
            reason,
            diagnostic_best=diagnostic_best,
        )

    def consider_payload(payload: bytes, edit_kind: str, global_bits: tuple[int, ...]) -> bool:
        nonlocal best, best_score, diagnostic_best, diagnostic_score
        nonlocal tested, crc_solutions, valid_headers, best_scanlines, budget_exhausted
        if payload in seen_payloads:
            return False
        seen_payloads.add(payload)
        if _crc32_idat_payload(payload) != target_crc:
            return False
        if tested >= budget:
            budget_exhausted = True
            return False
        tested += 1
        crc_solutions += 1
        if progress is not None and tested % 100 == 0:
            progress(strategy, tested, budget)

        candidate_stream = _stream_with_target_payload(
            idat_stream,
            target_stream_start,
            target_stream_end,
            payload,
        )
        try:
            header = deflate_header.analyze_deflate_header(candidate_stream)
        except Exception:
            return False
        if not header.ok or header.btype != before_header.btype:
            return False
        valid_headers += 1

        candidate = _crc_guided_candidate_from_payload(
            data,
            before=before,
            chunks=chunks,
            idat_chunks=idat_chunks,
            target_chunk=target_chunk,
            target_stream_start=target_stream_start,
            original_payload=original_payload,
            payload=payload,
            global_bit_offsets=global_bits,
            edit_kind=edit_kind,
        )
        if candidate is None:
            return False

        candidate_score = analysis_score(candidate.after)
        best_scanlines = max(best_scanlines, candidate.after.usable_scanlines)
        if candidate_score > diagnostic_score:
            diagnostic_best = candidate
            diagnostic_score = candidate_score
        if not is_material_improvement(before, candidate.after):
            return False
        if candidate_score <= best_score:
            return False
        best = candidate
        best_score = candidate_score
        return bool(candidate.after.complete)

    if progress is not None:
        progress(strategy, 0, max(0, budget))

    payload_variants: list[tuple[str, bytes, tuple[int, ...]]] = [
        ("crc-guided-bitset", original_payload, ()),
    ]
    payload_variants.extend(
        _dynamic_crc_guided_fixed_payloads(
            idat_stream,
            original_payload,
            trace,
            target_stream_start=target_stream_start,
            target_stream_end=target_stream_end,
            max_items=max_fixed_payloads,
        )
    )

    target_start_bit = target_stream_start * 8
    for edit_kind, base_payload, fixed_stream_bits in payload_variants:
        if budget_exhausted:
            break
        if _crc32_idat_payload(base_payload) == target_crc:
            if consider_payload(base_payload, edit_kind, tuple(fixed_stream_bits)):
                if progress is not None:
                    progress(strategy, tested, budget)
                return result()
            if budget_exhausted:
                break

        for _group_label, payload_bits in groups:
            if tested >= budget:
                budget_exhausted = True
                break
            solutions = _crc_guided_solutions_for_payload_bits(
                base_payload,
                payload_bits,
                target_crc,
                max_solutions=max_solutions_per_group,
            )
            for solution_payload_bits in solutions:
                if tested >= budget:
                    budget_exhausted = True
                    break
                payload = _flip_payload_bits(base_payload, solution_payload_bits)
                if payload is None:
                    continue
                solution_stream_bits = tuple(target_start_bit + bit for bit in solution_payload_bits)
                global_bits = tuple(sorted(tuple(fixed_stream_bits) + solution_stream_bits))
                if consider_payload(payload, edit_kind, global_bits):
                    if progress is not None:
                        progress(strategy, tested, budget)
                    return result()
            if budget_exhausted:
                break

    if progress is not None:
        progress(strategy, tested, budget)
    return result()


def _dynamic_length_token_bit_end(token: deflate_header.DynamicLengthToken) -> int:
    return int(token.extra_bit_end if token.extra_bit_end is not None else token.bit_end)


def _dynamic_length_token_bit_width(token: deflate_header.DynamicLengthToken) -> int:
    return _dynamic_length_token_bit_end(token) - int(token.bit_start)


def _encode_dynamic_length_token(
    symbol_codes: dict[int, tuple[int, int]],
    symbol: int,
    *,
    repeat: int = 1,
) -> tuple[int, ...] | None:
    symbol = int(symbol)
    code = symbol_codes.get(symbol)
    if code is None:
        return None
    code_bits = _bits_for_lsb_code(code[0], code[1])
    if symbol <= 15:
        return code_bits
    if symbol == 16:
        if repeat < 3 or repeat > 6:
            return None
        return code_bits + _bits_for_lsb_code(int(repeat) - 3, 2)
    if symbol == 17:
        if repeat < 3 or repeat > 10:
            return None
        return code_bits + _bits_for_lsb_code(int(repeat) - 3, 3)
    if symbol == 18:
        if repeat < 11 or repeat > 138:
            return None
        return code_bits + _bits_for_lsb_code(int(repeat) - 11, 7)
    return None


def _semantic_repeat_values(current: int, low: int, high: int) -> tuple[int, ...]:
    values = {
        low,
        high,
        int(current),
        int(current) - 8,
        int(current) - 4,
        int(current) - 2,
        int(current) - 1,
        int(current) + 1,
        int(current) + 2,
        int(current) + 4,
        int(current) + 8,
    }
    return tuple(sorted(value for value in values if int(low) <= value <= int(high)))


def _dynamic_semantic_token_options(
    token: deflate_header.DynamicLengthToken,
    symbol_codes: dict[int, tuple[int, int]],
) -> tuple[tuple[int, ...], ...]:
    options: list[tuple[int, ...]] = []
    for symbol in range(0, 16):
        encoded = _encode_dynamic_length_token(symbol_codes, symbol)
        if encoded is not None:
            options.append(encoded)
    if int(token.length_start) > 0:
        for repeat in range(3, 7):
            encoded = _encode_dynamic_length_token(symbol_codes, 16, repeat=repeat)
            if encoded is not None:
                options.append(encoded)
    for repeat in range(3, 11):
        encoded = _encode_dynamic_length_token(symbol_codes, 17, repeat=repeat)
        if encoded is not None:
            options.append(encoded)
    for repeat in _semantic_repeat_values(int(token.repeat), 11, 138):
        encoded = _encode_dynamic_length_token(symbol_codes, 18, repeat=repeat)
        if encoded is not None:
            options.append(encoded)
    original_width = _dynamic_length_token_bit_width(token)
    return tuple(
        dict.fromkeys(
            sorted(
                options,
                key=lambda bits: (
                    abs(len(bits) - original_width),
                    len(bits),
                    bits,
                ),
            )
        )
    )


def _dynamic_semantic_priority_tokens(
    trace: deflate_header.DynamicHeaderTrace,
    *,
    limit: int,
) -> tuple[deflate_header.DynamicLengthToken, ...]:
    if limit <= 0:
        return ()
    eob_index = 256
    boundary = int(trace.hlit) if trace.hlit is not None else eob_index
    tail_start = max(0, len(trace.tokens) - 32)

    def priority(item: tuple[int, deflate_header.DynamicLengthToken]) -> tuple[int, int, int]:
        index, token = item
        if token.length_start <= eob_index < token.length_end:
            rank = 0
        elif token.length_start <= boundary <= token.length_end:
            rank = 1
        elif token.symbol in (16, 17, 18):
            rank = 2
        elif abs(token.length_start - eob_index) <= 16 or abs(token.length_end - eob_index) <= 16:
            rank = 3
        elif abs(token.length_start - boundary) <= 16 or abs(token.length_end - boundary) <= 16:
            rank = 4
        elif index >= tail_start:
            rank = 5
        else:
            rank = 6
        return rank, int(token.length_start), int(token.bit_start)

    return tuple(token for _index, token in sorted(enumerate(trace.tokens), key=priority)[:limit])


def probe_dynamic_huffman_semantic_candidates(
    data: bytes,
    *,
    budget: int = 12000,
    max_tokens: int = 96,
    progress: QueueProgressCallback | None = None,
) -> IdatDeflateProbeResult:
    before = idat.analyze_idat_stream(data)
    strategy = "dynamic-huffman-semantic"
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
    if before_header.status != "invalid_huffman_lengths" or before_header.btype != 2:
        return IdatDeflateProbeResult(
            before,
            None,
            0,
            0,
            0,
            False,
            strategy,
            "unsupported header status: %s" % before_header.status,
        )

    trace = deflate_header.trace_dynamic_header(idat_stream)
    if trace.status != "invalid_huffman_lengths" or trace.btype != 2 or not trace.tokens:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, trace.summary)
    try:
        symbol_codes = _dynamic_code_length_symbol_codes(trace)
    except Exception as exc:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, str(exc))

    tokens = _dynamic_semantic_priority_tokens(trace, limit=max_tokens)
    if not tokens:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, "no semantic tokens")

    window_start = min(int(token.bit_start) for token in tokens) // 8
    window_end = (max(_dynamic_length_token_bit_end(token) for token in tokens) // 8) + 1
    best: IdatDeflateCandidate | None = None
    best_score = analysis_score(before)
    diagnostic_best: IdatDeflateCandidate | None = None
    diagnostic_score = analysis_score(before)
    tested = 0
    semantic_headers = 0
    valid_headers = 0
    best_scanlines = before.usable_scanlines
    budget_exhausted = False
    seen: set[tuple[int, int, tuple[int, ...]]] = set()

    def result() -> IdatDeflateProbeResult:
        reason = (
            "tokens=%s; semantic_headers=%s; valid_headers=%s; best_scanlines=%s; %s"
            % (
                len(tokens),
                semantic_headers,
                valid_headers,
                best_scanlines,
                trace.summary,
            )
        )
        return IdatDeflateProbeResult(
            before,
            best,
            window_start,
            window_end,
            tested,
            budget_exhausted,
            strategy,
            reason,
            diagnostic_best=diagnostic_best,
        )

    if progress is not None:
        progress(strategy, 0, max(0, budget))

    for token in tokens:
        bit_start = int(token.bit_start)
        bit_end = _dynamic_length_token_bit_end(token)
        for replacement_bits in _dynamic_semantic_token_options(token, symbol_codes):
            key = (bit_start, bit_end, replacement_bits)
            if key in seen:
                continue
            seen.add(key)
            if tested >= budget:
                budget_exhausted = True
                if progress is not None:
                    progress(strategy, tested, budget)
                return result()
            tested += 1
            if progress is not None and tested % 100 == 0:
                progress(strategy, tested, budget)

            candidate_stream = _replace_stream_bits_preserve_length(
                idat_stream,
                bit_start,
                bit_end,
                replacement_bits,
            )
            if candidate_stream is None or candidate_stream == idat_stream:
                continue
            candidate_trace = deflate_header.trace_dynamic_header(candidate_stream)
            if candidate_trace.btype != 2:
                continue
            if (
                candidate_trace.hlit is not None
                and candidate_trace.hdist is not None
                and candidate_trace.length_count == int(candidate_trace.hlit) + int(candidate_trace.hdist)
            ):
                semantic_headers += 1
            try:
                header = deflate_header.analyze_deflate_header(candidate_stream)
            except Exception:
                continue
            if not header.ok or header.btype != before_header.btype:
                continue
            valid_headers += 1
            candidate = mutate_idat_stream_bit_range_replace(
                data,
                bit_start,
                bit_end,
                replacement_bits,
                before_analysis=before,
            )
            if candidate is None:
                continue

            candidate_score = analysis_score(candidate.after)
            best_scanlines = max(best_scanlines, candidate.after.usable_scanlines)
            if candidate_score > diagnostic_score:
                diagnostic_best = candidate
                diagnostic_score = candidate_score
            if not is_material_improvement(before, candidate.after):
                continue
            if candidate_score <= best_score:
                continue
            best = candidate
            best_score = candidate_score
            if candidate.after.complete:
                if progress is not None:
                    progress(strategy, tested, budget)
                return result()

    if progress is not None:
        progress(strategy, tested, budget)
    return result()


def probe_dynamic_huffman_header_candidates(
    data: bytes,
    *,
    budget: int = 32768,
    max_bits: int = 192,
    max_bit_flips: int = 2,
    progress: QueueProgressCallback | None = None,
) -> IdatDeflateProbeResult:
    before = idat.analyze_idat_stream(data)
    strategy = "dynamic-huffman-header"
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
    if before_header.status != "invalid_huffman_lengths":
        return IdatDeflateProbeResult(
            before,
            None,
            0,
            0,
            0,
            False,
            strategy,
            "unsupported header status: %s" % before_header.status,
        )

    trace = deflate_header.trace_dynamic_header(idat_stream)
    if trace.status not in ("invalid_huffman_lengths", "ok"):
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, trace.summary)

    suspect_bits = _dynamic_huffman_suspect_bits(trace, idat_stream, max_bits=max_bits)
    if not suspect_bits:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, "no dynamic header suspect bits")

    window_start = min(suspect_bits) // 8
    window_end = (max(suspect_bits) // 8) + 1
    best: IdatDeflateCandidate | None = None
    best_score = analysis_score(before)
    diagnostic_best: IdatDeflateCandidate | None = None
    diagnostic_score = analysis_score(before)
    tested = 0
    valid_headers = 0
    budget_exhausted = False

    def result() -> IdatDeflateProbeResult:
        reason = "bits=%s; valid_headers=%s; %s" % (
            len(suspect_bits),
            valid_headers,
            trace.summary,
        )
        return IdatDeflateProbeResult(
            before,
            best,
            window_start,
            window_end,
            tested,
            budget_exhausted,
            strategy,
            reason,
            diagnostic_best=diagnostic_best,
        )

    if progress is not None:
        progress(strategy, 0, max(0, budget))

    max_width = max(1, int(max_bit_flips))
    for width in range(1, max_width + 1):
        for bit_offsets in itertools.combinations(suspect_bits, width):
            if tested >= budget:
                budget_exhausted = True
                if progress is not None:
                    progress(strategy, tested, budget)
                return result()
            tested += 1
            if progress is not None and tested % 100 == 0:
                progress(strategy, tested, budget)

            candidate_stream = _flip_stream_bits(idat_stream, bit_offsets)
            if candidate_stream is None:
                continue
            try:
                header = deflate_header.analyze_deflate_header(candidate_stream)
            except Exception:
                continue
            if not header.ok or header.btype != before_header.btype:
                continue
            valid_headers += 1

            candidate = mutate_idat_stream_bit_flips(
                data,
                bit_offsets,
                before_analysis=before,
            )
            if candidate is None:
                continue

            candidate_score = analysis_score(candidate.after)
            if candidate_score > diagnostic_score:
                diagnostic_best = candidate
                diagnostic_score = candidate_score
            if not is_material_improvement(before, candidate.after):
                continue
            if candidate_score <= best_score:
                continue
            best = candidate
            best_score = candidate_score
            if candidate.after.complete:
                if progress is not None:
                    progress(strategy, tested, budget)
                return result()

    if progress is not None:
        progress(strategy, tested, budget)
    return result()


def probe_dynamic_huffman_bitshift_candidates(
    data: bytes,
    *,
    budget: int = 4096,
    max_bits: int = 1024,
    progress: QueueProgressCallback | None = None,
) -> IdatDeflateProbeResult:
    before = idat.analyze_idat_stream(data)
    strategy = "dynamic-huffman-bitshift"
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
    if before_header.status != "invalid_huffman_lengths" or before_header.btype != 2:
        return IdatDeflateProbeResult(
            before,
            None,
            0,
            0,
            0,
            False,
            strategy,
            "unsupported header status: %s" % before_header.status,
        )

    trace = deflate_header.trace_dynamic_header(idat_stream)
    header_start_bit = 16
    header_end_bit = trace.header_end_bit or trace.bit_offset or before_header.bit_offset
    if header_end_bit is None:
        header_end_bit = min(len(idat_stream) * 8, header_start_bit + max_bits)
    header_end_bit = min(
        len(idat_stream) * 8,
        max(header_start_bit, int(header_end_bit)),
        header_start_bit + max(1, int(max_bits)),
    )
    bit_offsets = tuple(range(header_start_bit, header_end_bit))
    if not bit_offsets:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, "no dynamic header bits")

    window_start = min(bit_offsets) // 8
    window_end = (max(bit_offsets) // 8) + 1
    best: IdatDeflateCandidate | None = None
    best_score = analysis_score(before)
    diagnostic_best: IdatDeflateCandidate | None = None
    diagnostic_score = analysis_score(before)
    tested = 0
    valid_headers = 0
    budget_exhausted = False

    def result() -> IdatDeflateProbeResult:
        reason = "bits=%s; valid_dynamic_headers=%s; %s" % (
            len(bit_offsets),
            valid_headers,
            trace.summary,
        )
        return IdatDeflateProbeResult(
            before,
            best,
            window_start,
            window_end,
            tested,
            budget_exhausted,
            strategy,
            reason,
            diagnostic_best=diagnostic_best,
        )

    def consider(candidate: IdatDeflateCandidate | None) -> bool:
        nonlocal best, best_score, diagnostic_best, diagnostic_score
        if candidate is None:
            return False
        candidate_score = analysis_score(candidate.after)
        if candidate_score > diagnostic_score:
            diagnostic_best = candidate
            diagnostic_score = candidate_score
        if not is_material_improvement(before, candidate.after):
            return False
        if candidate_score <= best_score:
            return False
        best = candidate
        best_score = candidate_score
        return bool(candidate.after.complete)

    if progress is not None:
        progress(strategy, 0, max(0, budget))

    operations: tuple[tuple[str, int], ...] = (
        ("bit-delete", 0),
        ("bit-insert", 0),
        ("bit-insert", 1),
    )
    for bit_offset in bit_offsets:
        for edit_kind, bit_value in operations:
            if tested >= budget:
                budget_exhausted = True
                if progress is not None:
                    progress(strategy, tested, budget)
                return result()
            tested += 1
            if progress is not None and tested % 100 == 0:
                progress(strategy, tested, budget)

            if edit_kind == "bit-delete":
                candidate_stream = _shift_stream_delete_bit(idat_stream, bit_offset)
            else:
                candidate_stream = _shift_stream_insert_bit(idat_stream, bit_offset, bit_value)
            if candidate_stream is None:
                continue
            try:
                header = deflate_header.analyze_deflate_header(candidate_stream)
            except Exception:
                continue
            if not header.ok or header.btype != before_header.btype:
                continue
            valid_headers += 1
            if consider(
                mutate_idat_stream_bit_shift(
                    data,
                    bit_offset,
                    edit_kind,
                    bit_value=bit_value,
                    before_analysis=before,
                )
            ):
                if progress is not None:
                    progress(strategy, tested, budget)
                return result()

    if progress is not None:
        progress(strategy, tested, budget)
    return result()


def probe_deflate_header_candidates(
    data: bytes,
    *,
    budget: int = 100000,
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
    offsets = _deflate_header_priority_offsets(window_start, window_end, before, before_header)
    best: IdatDeflateCandidate | None = None
    best_score = analysis_score(before)
    diagnostic_best: IdatDeflateCandidate | None = None
    diagnostic_score = analysis_score(before)
    tested = 0
    budget_exhausted = False
    subprobes: list[IdatDeflateProbeResult] = []

    def result(*, exhausted_budget: bool | None = None) -> IdatDeflateProbeResult:
        return IdatDeflateProbeResult(
            before,
            best,
            window_start,
            window_end,
            tested,
            budget_exhausted if exhausted_budget is None else exhausted_budget,
            strategy,
            before_header.summary,
            diagnostic_best=diagnostic_best,
            subprobes=tuple(subprobes),
        )

    def exhausted() -> IdatDeflateProbeResult:
        return result(exhausted_budget=True)

    def consider(candidate: IdatDeflateCandidate | None) -> bool:
        nonlocal best, best_score, diagnostic_best, diagnostic_score
        if candidate is None:
            return False
        if not _candidate_header_is_fixed(before, candidate):
            return False
        candidate_score = analysis_score(candidate.after)
        if candidate_score > diagnostic_score:
            diagnostic_best = candidate
            diagnostic_score = candidate_score
        if not is_material_improvement(before, candidate.after):
            return False
        if candidate_score <= best_score:
            return False
        best = candidate
        best_score = candidate_score
        return bool(candidate.after.complete)

    def header_prefilter(stream_offset: int, edit: str, payload: bytes = b"", remove_count: int = 0) -> bool:
        if edit == "replace":
            end = stream_offset + len(payload)
            if not payload or stream_offset < 0 or end > len(idat_stream):
                return False
            candidate_stream = idat_stream[:stream_offset] + payload + idat_stream[end:]
        elif edit == "insert":
            if not payload or stream_offset < 0 or stream_offset > len(idat_stream):
                return False
            candidate_stream = idat_stream[:stream_offset] + payload + idat_stream[stream_offset:]
        elif edit == "remove":
            end = stream_offset + max(1, int(remove_count))
            if stream_offset < 0 or end > len(idat_stream):
                return False
            candidate_stream = idat_stream[:stream_offset] + idat_stream[end:]
        else:
            return False
        try:
            return bool(deflate_header.analyze_deflate_header(candidate_stream).ok)
        except Exception:
            return False

    if progress is not None:
        progress("deflate-header-bit", 0, budget)

    for stream_offset in offsets:
        old_byte = idat_stream[stream_offset]
        for bit in range(8):
            if tested >= budget:
                budget_exhausted = True
                return exhausted()
            tested += 1
            if progress is not None and tested % 100 == 0:
                progress("deflate-header-bit", tested, budget)
            new_byte = old_byte ^ (1 << bit)
            if not header_prefilter(stream_offset, "replace", bytes((new_byte,))):
                continue
            if consider(
                mutate_idat_stream_byte(
                    data,
                    stream_offset,
                    new_byte,
                    before_analysis=before,
                )
            ):
                if progress is not None:
                    progress("deflate-header-bit", tested, budget)
                return result()

    if progress is not None:
        progress("deflate-header-remove", tested, budget)

    for remove_count in (1, 2):
        for stream_offset in offsets:
            if tested >= budget:
                budget_exhausted = True
                return exhausted()
            tested += 1
            if progress is not None and tested % 100 == 0:
                progress("deflate-header-remove", tested, budget)
            if not header_prefilter(stream_offset, "remove", remove_count=remove_count):
                continue
            if consider(
                mutate_idat_stream_edit(
                    data,
                    stream_offset,
                    "remove",
                    remove_count=remove_count,
                    before_analysis=before,
                )
            ):
                if progress is not None:
                    progress("deflate-header-remove", tested, budget)
                return result()

    if before_header.status == "invalid_huffman_lengths" and tested < budget:
        remaining_budget = max(0, budget - tested)
        bitshift_base = tested

        def bitshift_progress(label: str, done: int, _total: int) -> None:
            if progress is not None:
                progress(label, min(budget, bitshift_base + done), budget)

        bitshift_probe = probe_dynamic_huffman_bitshift_candidates(
            data,
            budget=remaining_budget,
            progress=bitshift_progress if progress is not None else None,
        )
        subprobes.append(bitshift_probe)
        tested += bitshift_probe.tested_candidates
        if bitshift_probe.best is not None and consider(bitshift_probe.best):
            return result()
        if bitshift_probe.diagnostic_best is not None and bitshift_probe.diagnostic_best is not bitshift_probe.best:
            consider(bitshift_probe.diagnostic_best)
        if bitshift_probe.budget_exhausted:
            budget_exhausted = True
            return exhausted()

    if before_header.status == "invalid_huffman_lengths" and tested < budget:
        remaining_budget = max(0, budget - tested)
        dynamic_base = tested

        def dynamic_progress(label: str, done: int, _total: int) -> None:
            if progress is not None:
                progress(label, min(budget, dynamic_base + done), budget)

        semantic_reserve = 12000 if remaining_budget > 16000 else 0
        dynamic_budget = min(32768, max(0, remaining_budget - semantic_reserve))
        if dynamic_budget:
            dynamic_probe = probe_dynamic_huffman_header_candidates(
                data,
                budget=dynamic_budget,
                progress=dynamic_progress if progress is not None else None,
            )
            subprobes.append(dynamic_probe)
            tested += dynamic_probe.tested_candidates
            if dynamic_probe.best is not None and consider(dynamic_probe.best):
                return result()
            if dynamic_probe.diagnostic_best is not None and dynamic_probe.diagnostic_best is not dynamic_probe.best:
                consider(dynamic_probe.diagnostic_best)
            if dynamic_probe.budget_exhausted and tested >= budget:
                budget_exhausted = True
                return exhausted()

    if before_header.status == "invalid_huffman_lengths" and tested < budget:
        remaining_budget = max(0, budget - tested)
        semantic_base = tested

        def semantic_progress(label: str, done: int, _total: int) -> None:
            if progress is not None:
                progress(label, min(budget, semantic_base + done), budget)

        semantic_probe = probe_dynamic_huffman_semantic_candidates(
            data,
            budget=min(12000, remaining_budget),
            progress=semantic_progress if progress is not None else None,
        )
        subprobes.append(semantic_probe)
        tested += semantic_probe.tested_candidates
        if semantic_probe.best is not None and consider(semantic_probe.best):
            return result()
        if semantic_probe.diagnostic_best is not None and semantic_probe.diagnostic_best is not semantic_probe.best:
            consider(semantic_probe.diagnostic_best)
        if semantic_probe.budget_exhausted and tested >= budget:
            budget_exhausted = True
            return exhausted()

    if before_header.status in ("invalid_huffman_lengths", "bad_code_length_tree") and tested < budget:
        remaining_budget = max(0, budget - tested)
        alphabet_base = tested

        def alphabet_progress(label: str, done: int, _total: int) -> None:
            if progress is not None:
                progress(label, min(budget, alphabet_base + done), budget)

        alphabet_probe = probe_dynamic_huffman_alphabet_candidates(
            data,
            budget=min(8192, remaining_budget),
            progress=alphabet_progress if progress is not None else None,
        )
        subprobes.append(alphabet_probe)
        tested += alphabet_probe.tested_candidates
        if alphabet_probe.best is not None and consider(alphabet_probe.best):
            return result()
        if alphabet_probe.diagnostic_best is not None and alphabet_probe.diagnostic_best is not alphabet_probe.best:
            consider(alphabet_probe.diagnostic_best)
        if alphabet_probe.budget_exhausted and tested >= budget:
            budget_exhausted = True
            return exhausted()

    if before_header.status in ("invalid_huffman_lengths", "bad_code_length_tree") and tested < budget:
        remaining_budget = max(0, budget - tested)
        crc_guided_base = tested

        def crc_guided_progress(label: str, done: int, _total: int) -> None:
            if progress is not None:
                progress(label, min(budget, crc_guided_base + done), budget)

        crc_guided_probe = probe_dynamic_huffman_crc_guided_candidates(
            data,
            budget=min(65536, remaining_budget),
            progress=crc_guided_progress if progress is not None else None,
        )
        subprobes.append(crc_guided_probe)
        tested += crc_guided_probe.tested_candidates
        if crc_guided_probe.best is not None and consider(crc_guided_probe.best):
            return result()
        if crc_guided_probe.diagnostic_best is not None and crc_guided_probe.diagnostic_best is not crc_guided_probe.best:
            consider(crc_guided_probe.diagnostic_best)
        if crc_guided_probe.budget_exhausted and tested >= budget:
            budget_exhausted = True
            return exhausted()

    if progress is not None:
        progress("deflate-header-byte", tested, budget)

    for stream_offset in offsets:
        old_byte = idat_stream[stream_offset]
        for new_byte in range(256):
            if new_byte == old_byte:
                continue
            if tested >= budget:
                budget_exhausted = True
                return exhausted()
            tested += 1
            if progress is not None and tested % 100 == 0:
                progress("deflate-header-byte", tested, budget)
            if not header_prefilter(stream_offset, "replace", bytes((new_byte,))):
                continue
            if consider(
                mutate_idat_stream_byte(
                    data,
                    stream_offset,
                    new_byte,
                    before_analysis=before,
                )
            ):
                if progress is not None:
                    progress("deflate-header-byte", tested, budget)
                return result()

    if progress is not None:
        progress("deflate-header-insert", tested, budget)

    insert_offsets = tuple(dict.fromkeys(offsets + (window_end,)))
    for stream_offset in insert_offsets:
        for new_byte in range(256):
            if tested >= budget:
                budget_exhausted = True
                return exhausted()
            tested += 1
            if progress is not None and tested % 100 == 0:
                progress("deflate-header-insert", tested, budget)
            payload = bytes((new_byte,))
            if not header_prefilter(stream_offset, "insert", payload):
                continue
            if consider(
                mutate_idat_stream_edit(
                    data,
                    stream_offset,
                    "insert",
                    new_bytes=payload,
                    before_analysis=before,
                )
            ):
                if progress is not None:
                    progress("deflate-header-insert", tested, budget)
                return result()

    if progress is not None:
        progress("deflate-header-byte", tested, budget)
    return result()


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


def idat_crc_evidence_summary_lines(data: bytes, *, limit: int = 8) -> tuple[str, ...]:
    try:
        chunks = tuple(png.iter_chunks(data))
    except png.PngFormatError as exc:
        return ("-IDAT CRC evidence unavailable: %s." % exc,)

    idat_chunks = tuple(chunk for chunk in chunks if chunk.chunk_type == b"IDAT")
    if not idat_chunks:
        return ("-IDAT CRC evidence: no IDAT chunks.",)

    bad_indexes = tuple(
        index
        for index, chunk in enumerate(idat_chunks)
        if chunk.crc != chunk.computed_crc
    )
    ok_count = len(idat_chunks) - len(bad_indexes)
    bad_label = ",".join(str(index) for index in bad_indexes[:limit])
    if len(bad_indexes) > limit:
        bad_label += ",..."
    lines = [
        "-IDAT CRC evidence: chunks=%s; current_crc_ok=%s; stored_crc_mismatch=%s; mismatch_indexes=%s."
        % (
            len(idat_chunks),
            ok_count,
            len(bad_indexes),
            bad_label or "none",
        )
    ]
    detail_parts = []
    for index, chunk in enumerate(idat_chunks[:limit]):
        detail_parts.append(
            "#%02d len=%s stored=%08x computed=%08x %s"
            % (
                index,
                chunk.length,
                chunk.crc,
                chunk.computed_crc,
                "ok" if chunk.crc == chunk.computed_crc else "stored-original?",
            )
        )
    if detail_parts:
        if len(idat_chunks) > limit:
            detail_parts.append("...")
        lines.append("-IDAT CRC evidence detail: %s." % "; ".join(detail_parts))
    return tuple(lines)


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


def _format_deep_beam_operation(operation: IdatDeepBeamOperation) -> str:
    if operation.bit_offsets:
        bits = ",".join("0x%x.%s" % (bit // 8, bit % 8) for bit in operation.bit_offsets[:8])
        if len(operation.bit_offsets) > 8:
            bits += ",..."
        return "%s@bits[%s]" % (operation.kind, bits)
    old_hex = operation.old_bytes.hex() if operation.old_bytes else "-"
    new_hex = operation.new_bytes.hex() if operation.new_bytes else "-"
    return "%s@0x%x:%s>%s" % (operation.kind, operation.stream_offset, old_hex, new_hex)


def deep_beam_summary_line(result: IdatDeepBeamProbeResult) -> str:
    line = (
        "-IDAT deflate deep beam: strategy=%s; window=0x%x..0x%x; tested=%s; "
        "depth=%s; states=%s; visited=%s; top=%s; workers=%s"
        % (
            result.strategy,
            result.window_start,
            result.window_end,
            result.tested_candidates,
            result.reached_depth,
            result.state_count,
            result.visited_count,
            len(result.top_candidates),
            result.workers,
        )
    )
    if result.gpu_requested:
        line += "; gpu=%s" % (result.gpu_backend or "opengl-requested")
    else:
        line += "; gpu=off"
    if result.gpu_warning:
        warning = result.gpu_warning
        if len(warning) > 160:
            warning = warning[:157] + "..."
        line += "; gpu_warning=%s" % warning
    if result.gpu_shards_done:
        line += "; gpu_shards=%s" % result.gpu_shards_done
    timing = result.timing
    if any(
        (
            timing.gpu_shards,
            timing.gpu_hits,
            timing.cpu_batches,
            timing.gpu_setup_ms,
            timing.gpu_dispatch_ms,
            timing.cpu_validate_ms,
            timing.wall_ms,
        )
    ):
        line += (
            "; gpu_runtime_shards=%s; gpu_hits=%s; cpu_batches=%s; "
            "gpu_setup_ms=%.1f; gpu_dispatch_ms=%.1f; cpu_validate_ms=%.1f; wall_ms=%.1f"
            % (
                timing.gpu_shards,
                timing.gpu_hits,
                timing.cpu_batches,
                timing.gpu_setup_ms,
                timing.gpu_dispatch_ms,
                timing.cpu_validate_ms,
                timing.wall_ms,
            )
        )
    if timing.gpu_skipped_resume:
        line += "; gpu_skipped_resume=%s" % timing.gpu_skipped_resume
    if result.interrupted:
        line += "; interrupted"
    if result.checkpoint_path:
        line += "; checkpoint=%s" % result.checkpoint_path
    if result.progress_path:
        line += "; progress=%s" % result.progress_path
    if result.progress_resumed:
        line += "; progress resumed"
    if result.best is not None:
        line += "; best_score=%s" % (result.best.score,)
    if result.budget_exhausted:
        line += "; budget exhausted"
    if result.reason:
        line += "; reason=%s" % result.reason
    return line + "."


def periodic_corruption_model_summary_line(result: IdatPeriodicCorruptionModelResult) -> str:
    line = (
        "-IDAT periodic corruption model: strategy=%s; tested=%s; top=%s"
        % (result.strategy, result.tested_candidates, len(result.top_candidates))
    )
    if result.best is not None:
        line += "; best_score=%s" % (result.best.score,)
    if result.budget_exhausted:
        line += "; budget exhausted/consumed"
    if result.model_path:
        line += "; model=%s" % result.model_path
    if result.checkpoint_path:
        line += "; checkpoint=%s" % result.checkpoint_path
    if result.progress_path:
        line += "; progress=%s" % result.progress_path
    if result.reason:
        line += "; reason=%s" % result.reason
    return line + "."


def periodic_corruption_model_candidate_summary_lines(
    result: IdatPeriodicCorruptionModelResult,
    *,
    limit: int = 5,
) -> tuple[str, ...]:
    return tuple(
        deep_beam_candidate_summary_line(candidate)
        for candidate in result.top_candidates[: max(1, int(limit))]
    )


def affine_corruption_model_summary_line(result: IdatAffineCorruptionModelResult) -> str:
    line = (
        "-IDAT affine-corruption: tested=%s; budget_exhausted=%s; workers=%s; gpu=%s; "
        "cpu_batches=%s; gpu_shards=%s; gpu_hits=%s; rules=%s; projected_hits=%s; png_plausible=%s; top=%s"
        % (
            result.tested_candidates,
            "yes" if result.budget_exhausted else "no",
            result.workers,
            result.gpu_status,
            result.cpu_batches,
            result.gpu_shards,
            result.gpu_hits,
            result.rules,
            result.projected_hits,
            result.png_plausible,
            len(result.top_candidates),
        )
    )
    if result.best is not None:
        line += "; best_score=%s" % (result.best.score,)
    if result.model_path:
        line += "; model=%s" % result.model_path
    if result.checkpoint_path:
        line += "; checkpoint=%s" % result.checkpoint_path
    if result.progress_path:
        line += "; progress=%s" % result.progress_path
    if result.reason:
        line += "; reason=%s" % result.reason
    return line + "."


def affine_corruption_model_candidate_summary_lines(
    result: IdatAffineCorruptionModelResult,
    *,
    limit: int = 5,
) -> tuple[str, ...]:
    return tuple(
        deep_beam_candidate_summary_line(candidate)
        for candidate in result.top_candidates[: max(1, int(limit))]
    )


def huffman_kraft_summary_line(result: IdatHuffmanKraftSolverResult) -> str:
    line = (
        "-IDAT huffman-kraft: tested=%s; budget_exhausted=%s; depth=%s; workers=%s; gpu=%s; "
        "cpu_batches=%s; gpu_shards=%s; gpu_hits=%s; prefilter_hits=%s; literal_debt=%s; distance_debt=%s; "
        "complete_trees=%s; first_symbol_ok=%s; valid_headers=%s; top=%s; memory=%s; throttle_events=%s"
        % (
            result.tested_candidates,
            "yes" if result.budget_exhausted else "no",
            result.reached_depth,
            result.workers,
            result.gpu_status,
            result.cpu_batches,
            result.gpu_shards,
            result.gpu_hits,
            result.kraft_prefilter_hits,
            result.best_literal_debt,
            result.best_distance_debt,
            result.complete_trees,
            result.first_symbol_ok,
            result.valid_headers,
            len(result.top_candidates),
            result.memory_mode,
            result.memory_throttle_events,
        )
    )
    if result.best is not None:
        line += "; best_score=%s" % (result.best.score,)
    if result.checkpoint_path:
        line += "; checkpoint=%s" % result.checkpoint_path
    if result.progress_path:
        line += "; progress=%s" % result.progress_path
    if result.reason:
        line += "; reason=%s" % result.reason
    return line + "."


def huffman_kraft_candidate_summary_lines(
    result: IdatHuffmanKraftSolverResult,
    *,
    limit: int = 5,
) -> tuple[str, ...]:
    return tuple(
        deep_beam_candidate_summary_line(candidate)
        for candidate in result.top_candidates[: max(1, int(limit))]
    )


def first_filter_literal_summary_line(result: IdatFirstFilterLiteralResult) -> str:
    line = (
        "-IDAT first-filter-literal: tested=%s; budget_exhausted=%s; seeds=%s; "
        "closure_hits=%s; first_filter_hits=%s; png_plausible=%s; top=%s"
        % (
            result.tested_candidates,
            "yes" if result.budget_exhausted else "no",
            result.seed_count,
            result.closure_hits,
            result.first_filter_hits,
            result.png_plausible,
            len(result.top_candidates),
        )
    )
    if result.best is not None:
        line += "; best_score=%s" % (result.best.score,)
    if result.checkpoint_path:
        line += "; checkpoint=%s" % result.checkpoint_path
    if result.progress_path:
        line += "; progress=%s" % result.progress_path
    if result.reason:
        line += "; reason=%s" % result.reason
    return line + "."


def first_filter_literal_candidate_summary_lines(
    result: IdatFirstFilterLiteralResult,
    *,
    limit: int = 5,
) -> tuple[str, ...]:
    return tuple(
        deep_beam_candidate_summary_line(candidate)
        for candidate in result.top_candidates[: max(1, int(limit))]
    )


def kraft_backref_repair_summary_line(result: IdatKraftBackrefRepairResult) -> str:
    line = (
        "-IDAT kraft-backref: tested=%s; budget_exhausted=%s; depth=%s; repaired_backrefs=%s; "
        "png_prefix_hits=%s; best_prefix_rows=%s; top=%s"
        % (
            result.tested_candidates,
            "yes" if result.budget_exhausted else "no",
            result.reached_depth,
            result.repaired_backrefs,
            result.png_prefix_hits,
            result.best_prefix_rows,
            len(result.top_candidates),
        )
    )
    if result.best is not None:
        line += "; best_score=%s" % (result.best.score,)
    if result.seed_checkpoint_path:
        line += "; seed_checkpoint=%s" % result.seed_checkpoint_path
    if result.checkpoint_path:
        line += "; checkpoint=%s" % result.checkpoint_path
    if result.progress_path:
        line += "; progress=%s" % result.progress_path
    if result.reason:
        line += "; reason=%s" % result.reason
    return line + "."


def kraft_backref_repair_candidate_summary_lines(
    result: IdatKraftBackrefRepairResult,
    *,
    limit: int = 5,
) -> tuple[str, ...]:
    return tuple(
        deep_beam_candidate_summary_line(candidate)
        for candidate in result.top_candidates[: max(1, int(limit))]
    )


def huffman_oracle_summary_line(result: IdatHuffmanOracleSolverResult) -> str:
    line = (
        "-IDAT huffman-oracle: tested=%s; budget_exhausted=%s; depth=%s; seeds=%s; valid_headers=%s; png_plausible=%s; top=%s"
        % (
            result.tested_candidates,
            "yes" if result.budget_exhausted else "no",
            result.reached_depth,
            result.seed_count,
            result.valid_headers,
            result.png_plausible,
            len(result.top_candidates),
        )
    )
    if result.best is not None:
        line += "; best_score=%s" % (result.best.score,)
    if result.checkpoint_path:
        line += "; checkpoint=%s" % result.checkpoint_path
    if result.progress_path:
        line += "; progress=%s" % result.progress_path
    if result.reason:
        line += "; reason=%s" % result.reason
    return line + "."


def huffman_oracle_candidate_summary_lines(
    result: IdatHuffmanOracleSolverResult,
    *,
    limit: int = 5,
) -> tuple[str, ...]:
    return tuple(
        deep_beam_candidate_summary_line(candidate)
        for candidate in result.top_candidates[: max(1, int(limit))]
    )


def crc_periodic_payload_summary_line(result: IdatCrcPeriodicPayloadSolverResult) -> str:
    line = (
        "-IDAT crc-periodic: tested=%s; budget_exhausted=%s; crc_hits=%s; png_plausible=%s; top=%s"
        % (
            result.tested_candidates,
            "yes" if result.budget_exhausted else "no",
            result.crc_hits,
            result.png_plausible,
            len(result.top_candidates),
        )
    )
    if result.best is not None:
        line += "; best_score=%s" % (result.best.score,)
    if result.model_path:
        line += "; model=%s" % result.model_path
    if result.checkpoint_path:
        line += "; checkpoint=%s" % result.checkpoint_path
    if result.progress_path:
        line += "; progress=%s" % result.progress_path
    if result.reason:
        line += "; reason=%s" % result.reason
    return line + "."


def crc_periodic_payload_candidate_summary_lines(
    result: IdatCrcPeriodicPayloadSolverResult,
    *,
    limit: int = 5,
) -> tuple[str, ...]:
    return tuple(
        deep_beam_candidate_summary_line(candidate)
        for candidate in result.top_candidates[: max(1, int(limit))]
    )


def global_crc_residue_summary_line(result: IdatGlobalCrcResidueSolverResult) -> str:
    line = (
        "-IDAT global-crc-residue: tested=%s; budget_exhausted=%s; rules=%s; explained_chunks=%s; crc_hits=%s; png_plausible=%s; top=%s"
        % (
            result.tested_candidates,
            "yes" if result.budget_exhausted else "no",
            result.rules,
            result.explained_chunks,
            result.crc_hits,
            result.png_plausible,
            len(result.top_candidates),
        )
    )
    if result.best is not None:
        line += "; best_score=%s" % (result.best.score,)
    if result.model_path:
        line += "; model=%s" % result.model_path
    if result.checkpoint_path:
        line += "; checkpoint=%s" % result.checkpoint_path
    if result.progress_path:
        line += "; progress=%s" % result.progress_path
    if result.reason:
        line += "; reason=%s" % result.reason
    return line + "."


def global_crc_residue_candidate_summary_lines(
    result: IdatGlobalCrcResidueSolverResult,
    *,
    limit: int = 5,
) -> tuple[str, ...]:
    return tuple(
        deep_beam_candidate_summary_line(candidate)
        for candidate in result.top_candidates[: max(1, int(limit))]
    )


def deflate_resync_salvage_summary_line(result: DeflateResyncSalvageResult) -> str:
    line = (
        "-IDAT deflate-salvage: tested=%s; budget_exhausted=%s; anchors=%s; partial_rows=%s; known_pixels=%s"
        % (
            result.tested_candidates,
            "yes" if result.budget_exhausted else "no",
            len(result.anchors),
            result.partial_rows,
            result.known_pixels,
        )
    )
    if result.preview_path:
        line += "; preview=%s" % result.preview_path
    if result.progress_path:
        line += "; progress=%s" % result.progress_path
    if result.reason:
        line += "; reason=%s" % result.reason
    return line + "."


def deep_beam_candidate_summary_line(candidate: IdatDeepBeamCandidate) -> str:
    operations = ", ".join(_format_deep_beam_operation(operation) for operation in candidate.operations)
    if len(operations) > 240:
        operations = operations[:237] + "..."
    return (
        "-IDAT deep beam candidate: state=%s parent=%s; operations=%s; score=%s; "
        "status %s -> %s; scanlines %s/%s -> %s/%s; decompressed %s/%s -> %s/%s; "
        "error_offset %s -> %s."
        % (
            candidate.state_id,
            "root" if candidate.parent_id is None else candidate.parent_id,
            operations or "none",
            candidate.score,
            candidate.before.status,
            candidate.after.status,
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


def deep_beam_candidate_summary_lines(
    result: IdatDeepBeamProbeResult,
    *,
    limit: int = 5,
) -> tuple[str, ...]:
    if not result.top_candidates:
        return ()
    return tuple(
        deep_beam_candidate_summary_line(candidate)
        for candidate in result.top_candidates[: max(1, int(limit))]
    )


def probe_detail_summary_lines(result: IdatDeflateProbeResult) -> tuple[str, ...]:
    return tuple(probe_summary_line(subprobe) for subprobe in result.subprobes)


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


def _format_candidate_bit_offsets(candidate: IdatDeflateCandidate, *, limit: int = 8) -> str:
    offsets = tuple(candidate.bit_offsets)
    if not offsets:
        return ""
    parts = ["0x%x.%s" % (bit // 8, bit % 8) for bit in offsets[:limit]]
    if len(offsets) > limit:
        parts.append("...")
    return ",".join(parts)


def _candidate_operation(candidate: IdatDeflateCandidate) -> str:
    if candidate.edit_kind == "insert":
        return "insert %s" % (candidate.new_bytes.hex() or "%02x" % candidate.new_byte)
    if candidate.edit_kind == "remove":
        return "remove %s" % (candidate.old_bytes.hex() or "%02x" % candidate.old_byte)
    if candidate.edit_kind == "bit-flip-set":
        return "flip bits %s" % (_format_candidate_bit_offsets(candidate) or "unknown")
    if candidate.edit_kind == "bit-delete":
        return "delete bit %s" % (_format_candidate_bit_offsets(candidate) or "unknown")
    if candidate.edit_kind == "bit-insert":
        return "insert bit %s=%s" % (
            _format_candidate_bit_offsets(candidate) or "unknown",
            candidate.new_byte & 1,
        )
    if candidate.edit_kind == "semantic-token":
        return "rewrite Huffman length token at %s" % (
            _format_candidate_bit_offsets(candidate) or "unknown"
        )
    if candidate.edit_kind == "alphabet-order":
        return "rewrite Huffman code-length alphabet order at %s" % (
            _format_candidate_bit_offsets(candidate) or "unknown"
        )
    if candidate.edit_kind == "alphabet-field":
        return "rewrite Huffman code-length alphabet field at %s" % (
            _format_candidate_bit_offsets(candidate) or "unknown"
        )
    if candidate.edit_kind == "crc-guided-bitset":
        return "CRC-guided Huffman bit flips %s" % (
            _format_candidate_bit_offsets(candidate) or "unknown"
        )
    if candidate.edit_kind == "crc-guided-semantic":
        return "CRC-guided Huffman semantic rewrite at %s" % (
            _format_candidate_bit_offsets(candidate) or "unknown"
        )
    if candidate.edit_kind == "crc-guided-alphabet":
        return "CRC-guided Huffman alphabet rewrite at %s" % (
            _format_candidate_bit_offsets(candidate) or "unknown"
        )
    return "byte %02x -> %02x" % (candidate.old_byte, candidate.new_byte)


def candidate_summary_line(candidate: IdatDeflateCandidate) -> str:
    operation = _candidate_operation(candidate)
    return (
        "-IDAT deflate candidate: stream=0x%x; file=0x%x; IDAT=%s; %s; "
        "status %s -> %s; scanlines %s/%s -> %s/%s; error_offset %s -> %s."
        % (
            candidate.stream_offset,
            candidate.file_offset,
            candidate.idat_index,
            operation,
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


def diagnostic_candidate_summary_line(candidate: IdatDeflateCandidate) -> str:
    operation = _candidate_operation(candidate)
    return (
        "-IDAT deflate diagnostic candidate rejected: stream=0x%x; file=0x%x; IDAT=%s; %s; "
        "scanlines %s/%s -> %s/%s; decompressed %s -> %s; error_offset %s -> %s."
        % (
            candidate.stream_offset,
            candidate.file_offset,
            candidate.idat_index,
            operation,
            candidate.before.usable_scanlines,
            candidate.before.height,
            candidate.after.usable_scanlines,
            candidate.after.height,
            candidate.before.decompressed_size,
            candidate.after.decompressed_size,
            candidate.before.error_offset,
            candidate.after.error_offset,
        )
    )


def candidate_patch_note(candidate: IdatDeflateCandidate) -> str:
    if candidate.edit_kind == "insert":
        return "Patch: insert %s at IDAT stream offset 0x%x." % (
            candidate.new_bytes.hex() or "%02x" % candidate.new_byte,
            candidate.stream_offset,
        )
    if candidate.edit_kind == "remove":
        return "Patch: remove %s at IDAT stream offset 0x%x." % (
            candidate.old_bytes.hex() or "%02x" % candidate.old_byte,
            candidate.stream_offset,
        )
    if candidate.edit_kind == "bit-flip-set":
        return "Patch: flip IDAT stream bits %s." % (
            _format_candidate_bit_offsets(candidate) or "unknown",
        )
    if candidate.edit_kind == "bit-delete":
        return "Patch: delete IDAT stream bit %s." % (
            _format_candidate_bit_offsets(candidate) or "unknown",
        )
    if candidate.edit_kind == "bit-insert":
        return "Patch: insert bit %s at IDAT stream bit %s." % (
            candidate.new_byte & 1,
            _format_candidate_bit_offsets(candidate) or "unknown",
        )
    if candidate.edit_kind == "semantic-token":
        return "Patch: rewrite dynamic Huffman length token at IDAT stream bit %s." % (
            _format_candidate_bit_offsets(candidate) or "unknown",
        )
    if candidate.edit_kind == "alphabet-order":
        return "Patch: rewrite dynamic Huffman code-length alphabet order at IDAT stream bits %s." % (
            _format_candidate_bit_offsets(candidate) or "unknown",
        )
    if candidate.edit_kind == "alphabet-field":
        return "Patch: rewrite dynamic Huffman code-length alphabet fields at IDAT stream bits %s." % (
            _format_candidate_bit_offsets(candidate) or "unknown",
        )
    if candidate.edit_kind == "crc-guided-bitset":
        return "Patch: CRC-guided dynamic Huffman bit flips at IDAT stream bits %s." % (
            _format_candidate_bit_offsets(candidate) or "unknown",
        )
    if candidate.edit_kind == "crc-guided-semantic":
        return "Patch: CRC-guided dynamic Huffman semantic rewrite at IDAT stream bits %s." % (
            _format_candidate_bit_offsets(candidate) or "unknown",
        )
    if candidate.edit_kind == "crc-guided-alphabet":
        return "Patch: CRC-guided dynamic Huffman alphabet rewrite at IDAT stream bits %s." % (
            _format_candidate_bit_offsets(candidate) or "unknown",
        )
    return "Patch: IDAT stream offset 0x%x, byte %02x -> %02x." % (
        candidate.stream_offset,
        candidate.old_byte,
        candidate.new_byte,
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


def diagnostic_candidate_summary_lines(result: IdatDeflateProbeResult) -> tuple[str, ...]:
    if result.best is not None or result.diagnostic_best is None:
        return ()
    return (diagnostic_candidate_summary_line(result.diagnostic_best),)
