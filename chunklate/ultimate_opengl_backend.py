from __future__ import annotations

from dataclasses import dataclass, replace
import math
import struct
import time
from typing import Any, Callable

from . import gpu_opengl, gpu_runtime, idat, png


ULTIMATE_OPENGL_OFFSET_MAX_RESULTS = 4096
ULTIMATE_OPENGL_OFFSET_BATCH_SIZE = 1_048_576
ULTIMATE_OPENGL_ANALYSIS_MAX_HITS = 64
ULTIMATE_OPENGL_ANALYSIS_SHARD_SIZE = 50_000
ULTIMATE_OPENGL_ANALYSIS_BATCH_SIZE = ULTIMATE_OPENGL_ANALYSIS_SHARD_SIZE
ULTIMATE_OPENGL_ANALYSIS_OP_WORDS = 11
ULTIMATE_OPENGL_ANALYSIS_HIT_WORDS = 16
ULTIMATE_OPENGL_ANALYSIS_STATUS = {
    "unsupported": 0,
    "complete": 1,
    "bad_adler": 2,
    "partial": 3,
    "incomplete_stream": 4,
    "corrupt_deflate": 5,
    "bad_zlib_header": 6,
    "trailing_data": 7,
    "host_deflate_required": 8,
}
ULTIMATE_OPENGL_ANALYSIS_STATUS_BY_CODE = {
    code: status for status, code in ULTIMATE_OPENGL_ANALYSIS_STATUS.items()
}
ULTIMATE_OPENGL_ANALYSIS_PROOF_ZLIB_EOF = 1 << 0
ULTIMATE_OPENGL_ANALYSIS_PROOF_SIZE_MATCH = 1 << 1
ULTIMATE_OPENGL_ANALYSIS_PROOF_SCANLINES_COMPLETE = 1 << 2
ULTIMATE_OPENGL_ANALYSIS_PROOF_ADLER_MATCH = 1 << 3
ULTIMATE_OPENGL_ANALYSIS_PROOF_TERMINAL = 1 << 4
ULTIMATE_OPENGL_ANALYSIS_PROOF_HOST_DEFLATE_REQUIRED = 1 << 5
ULTIMATE_OPENGL_ANALYSIS_PROOF_OP_VALID = 1 << 6
ULTIMATE_OPENGL_OFFSET_SHADER = """
#version 430
layout(local_size_x = 128) in;

layout(std430, binding = 0) readonly buffer StreamBuffer {
    uint stream_values[];
};

layout(std430, binding = 1) buffer OutputBuffer {
    uint output_values[];
};

uniform uint stream_len;
uniform uint base_offset;
uniform uint batch_count;
uniform uint max_results;

void main() {
    uint local_index = gl_GlobalInvocationID.x;
    if (local_index >= batch_count) {
        return;
    }

    uint offset = base_offset + local_index;
    if (offset >= stream_len) {
        return;
    }

    uint value = stream_values[offset] & 0xffu;
    bool interesting = value == 0x0au || value == 0x0du;
    if (stream_len >= 4u && offset == stream_len - 4u) {
        interesting = true;
    }
    if (!interesting) {
        return;
    }

    uint slot = atomicAdd(output_values[0], 1u);
    if (slot < max_results) {
        output_values[slot + 1u] = offset;
    }
}
"""
ULTIMATE_OPENGL_ANALYSIS_SHADER = """
#version 430
layout(local_size_x = 128) in;

layout(std430, binding = 0) readonly buffer StreamBuffer {
    uint stream_values[];
};

layout(std430, binding = 1) readonly buffer OperationBuffer {
    uint operation_values[];
};

layout(std430, binding = 2) buffer OutputBuffer {
    uint output_values[];
};

uniform uint stream_len;
uniform uint operation_count;
uniform uint pool_index;
uniform uint depth;
uniform uint base_rank_low;
uniform uint base_rank_high;
uniform uint batch_count;
uniform uint max_results;
uniform uint scanline_size;
uniform uint image_height;
uniform uint expected_size;
uniform uint target_adler;
uniform uint has_target_adler;

const uint OP_WORDS = 11u;
const uint HIT_WORDS = 16u;
const uint STATUS_COMPLETE = 1u;
const uint STATUS_BAD_ADLER = 2u;
const uint STATUS_PARTIAL = 3u;
const uint STATUS_CORRUPT_DEFLATE = 5u;
const uint STATUS_BAD_ZLIB_HEADER = 6u;
const uint STATUS_HOST_DEFLATE_REQUIRED = 8u;
const uint PROOF_ZLIB_EOF = 1u << 0;
const uint PROOF_SIZE_MATCH = 1u << 1;
const uint PROOF_SCANLINES_COMPLETE = 1u << 2;
const uint PROOF_ADLER_MATCH = 1u << 3;
const uint PROOF_TERMINAL = 1u << 4;
const uint PROOF_HOST_DEFLATE_REQUIRED = 1u << 5;
const uint PROOF_OP_VALID = 1u << 6;
const uint ADLER_MOD = 65521u;

uint op_word(uint op_index, uint word_index) {
    return operation_values[op_index * OP_WORDS + word_index];
}

uint old_byte(uint op_index, uint byte_index) {
    return op_word(op_index, 3u + byte_index) & 0xffu;
}

uint new_byte(uint op_index, uint byte_index) {
    return op_word(op_index, 7u + byte_index) & 0xffu;
}

bool zlib_header_valid(uint cmf, uint flg) {
    uint compression_method = cmf & 15u;
    uint cinfo = cmf >> 4;
    return compression_method == 8u && cinfo <= 7u && (((cmf << 8u) + flg) % 31u) == 0u;
}

uint virtual_length(uint op_index) {
    uint old_len = op_word(op_index, 1u);
    uint new_len = op_word(op_index, 2u);
    return stream_len - old_len + new_len;
}

uint virtual_byte(uint op_index, uint position) {
    uint offset = op_word(op_index, 0u);
    uint old_len = op_word(op_index, 1u);
    uint new_len = op_word(op_index, 2u);
    if (position < offset) {
        return stream_values[position] & 0xffu;
    }
    if (position < offset + new_len) {
        return new_byte(op_index, position - offset);
    }
    uint source_position = position + old_len - new_len;
    if (source_position >= stream_len) {
        return 0u;
    }
    return stream_values[source_position] & 0xffu;
}

bool operation_valid(uint op_index) {
    uint offset = op_word(op_index, 0u);
    uint old_len = op_word(op_index, 1u);
    uint new_len = op_word(op_index, 2u);
    if (old_len > 4u || new_len > 4u) {
        return false;
    }
    if (offset > stream_len || offset + old_len > stream_len) {
        return false;
    }
    for (uint index = 0u; index < 4u; index++) {
        if (index >= old_len) {
            break;
        }
        if ((stream_values[offset + index] & 0xffu) != old_byte(op_index, index)) {
            return false;
        }
    }
    return true;
}

uint read_u16_le_virtual(uint op_index, uint position) {
    return virtual_byte(op_index, position) | (virtual_byte(op_index, position + 1u) << 8u);
}

uint read_u32_be_virtual(uint op_index, uint position) {
    return (
        (virtual_byte(op_index, position) << 24u)
        | (virtual_byte(op_index, position + 1u) << 16u)
        | (virtual_byte(op_index, position + 2u) << 8u)
        | virtual_byte(op_index, position + 3u)
    );
}

uint usable_scanlines_for_stored(uint op_index, uint data_offset, uint decompressed_size) {
    if (scanline_size == 0u || image_height == 0u) {
        return 0u;
    }
    uint complete_scanlines = decompressed_size / scanline_size;
    if (complete_scanlines > image_height) {
        complete_scanlines = image_height;
    }
    uint usable = 0u;
    for (uint row = 0u; row < complete_scanlines; row++) {
        uint filter_byte = virtual_byte(op_index, data_offset + row * scanline_size);
        if (filter_byte > 4u) {
            break;
        }
        usable++;
    }
    return usable;
}

uint adler32_stored_payload(uint op_index, uint data_offset, uint decompressed_size) {
    uint a = 1u;
    uint b = 0u;
    for (uint index = 0u; index < decompressed_size; index++) {
        a += virtual_byte(op_index, data_offset + index);
        a %= ADLER_MOD;
        b += a;
        b %= ADLER_MOD;
    }
    return (b << 16u) | a;
}

void write_hit(
    uint slot,
    uint rank_low,
    uint rank_high,
    uint op_index,
    uint status,
    uint decompressed_size,
    uint usable_scanlines,
    uint error_offset,
    uint stored_adler,
    uint computed_adler,
    uint adler_status,
    uint proof_flags
) {
    uint base = 3u + slot * HIT_WORDS;
    output_values[base + 0u] = rank_low;
    output_values[base + 1u] = rank_high;
    output_values[base + 2u] = pool_index;
    output_values[base + 3u] = depth;
    output_values[base + 4u] = op_index;
    output_values[base + 5u] = status;
    output_values[base + 6u] = decompressed_size;
    output_values[base + 7u] = usable_scanlines;
    output_values[base + 8u] = error_offset;
    output_values[base + 9u] = stored_adler;
    output_values[base + 10u] = computed_adler;
    output_values[base + 11u] = adler_status;
    output_values[base + 12u] = proof_flags;
    output_values[base + 13u] = 0u;
    output_values[base + 14u] = 0u;
    output_values[base + 15u] = 0u;
}

void main() {
    uint local_index = gl_GlobalInvocationID.x;
    if (local_index >= batch_count) {
        return;
    }

    atomicAdd(output_values[1], 1u);
    if (depth != 1u) {
        return;
    }

    uint op_index = local_index + base_rank_low;
    if (base_rank_high != 0u || op_index >= operation_count) {
        return;
    }
    if (!operation_valid(op_index)) {
        atomicAdd(output_values[2], 1u);
        return;
    }

    uint vlen = virtual_length(op_index);
    if (vlen < 6u) {
        return;
    }

    uint cmf = virtual_byte(op_index, 0u);
    uint flg = virtual_byte(op_index, 1u);
    uint stored_adler = read_u32_be_virtual(op_index, vlen - 4u);
    uint status = STATUS_BAD_ZLIB_HEADER;
    uint decompressed_size = 0u;
    uint usable = 0u;
    uint error_offset = 0xffffffffu;
    uint computed_adler = 0u;
    uint adler_status = 2u;
    uint proof_flags = PROOF_OP_VALID;

    if (!zlib_header_valid(cmf, flg)) {
        status = STATUS_BAD_ZLIB_HEADER;
    } else {
        uint first_deflate = virtual_byte(op_index, 2u);
        uint btype = (first_deflate >> 1u) & 3u;
        if (btype == 0u && vlen >= 11u) {
            uint len_value = read_u16_le_virtual(op_index, 3u);
            uint nlen_value = read_u16_le_virtual(op_index, 5u);
            uint data_offset = 7u;
            if (((len_value ^ nlen_value) & 0xffffu) != 0xffffu || data_offset + len_value + 4u > vlen) {
                status = STATUS_CORRUPT_DEFLATE;
                error_offset = 3u;
            } else {
                decompressed_size = len_value;
                usable = usable_scanlines_for_stored(op_index, data_offset, decompressed_size);
                computed_adler = adler32_stored_payload(op_index, data_offset, decompressed_size);
                bool size_match = decompressed_size == expected_size;
                bool scanlines_complete = usable == image_height;
                bool adler_match = (
                    (has_target_adler != 0u && computed_adler == target_adler)
                    || (has_target_adler == 0u && computed_adler == stored_adler)
                );
                proof_flags |= PROOF_ZLIB_EOF;
                if (size_match) {
                    proof_flags |= PROOF_SIZE_MATCH;
                }
                if (scanlines_complete) {
                    proof_flags |= PROOF_SCANLINES_COMPLETE;
                }
                if (adler_match) {
                    proof_flags |= PROOF_ADLER_MATCH;
                }
                adler_status = adler_match ? 4u : 1u;
                status = size_match && scanlines_complete ? STATUS_COMPLETE : STATUS_PARTIAL;
                if (computed_adler != stored_adler && has_target_adler == 0u) {
                    status = STATUS_BAD_ADLER;
                }
                if (size_match && scanlines_complete && adler_match) {
                    proof_flags |= PROOF_TERMINAL;
                }
            }
        } else if (btype == 1u || btype == 2u) {
            status = STATUS_HOST_DEFLATE_REQUIRED;
            proof_flags |= PROOF_HOST_DEFLATE_REQUIRED;
        } else {
            status = STATUS_CORRUPT_DEFLATE;
            error_offset = 2u;
        }
    }

    bool nominate = (
        (proof_flags & PROOF_TERMINAL) != 0u
        || (proof_flags & PROOF_HOST_DEFLATE_REQUIRED) != 0u
        || status == STATUS_COMPLETE
        || status == STATUS_BAD_ADLER
        || (status == STATUS_PARTIAL && usable > 0u)
    );
    if (!nominate) {
        return;
    }
    uint slot = atomicAdd(output_values[0], 1u);
    if (slot < max_results) {
        write_hit(
            slot,
            op_index,
            base_rank_high,
            op_index,
            status,
            decompressed_size,
            usable,
            error_offset,
            stored_adler,
            computed_adler,
            adler_status,
            proof_flags
        );
    }
}
"""


@dataclass(frozen=True)
class UltimateLinefeedGpuPlan:
    source_length: int
    idat_stream: bytes
    start_offset: int | None = None
    target_adler: int | None = None
    has_super_result: bool = False
    max_offsets: int = 128

    @property
    def idat_stream_length(self) -> int:
        return len(self.idat_stream)


@dataclass(frozen=True)
class UltimateOpenGLDecision:
    runnable: bool
    reason: str
    availability: gpu_opengl.GpuAvailability | None = None


@dataclass(frozen=True)
class UltimateOpenGLOffsetResult:
    offsets: tuple[int, ...]
    tested: int
    truncated: bool = False


@dataclass(frozen=True)
class UltimateOpenGLAnalysisPlan:
    root_stream: bytes
    width: int
    height: int
    bit_depth: int
    color_type: int
    scanline_size: int
    expected_size: int
    operation_pool: tuple[Any, ...]
    pool_index: int = 0
    depth: int = 1
    start_rank: int = 0
    end_rank: int | None = None
    target_adler: int | None = None
    max_hits: int = ULTIMATE_OPENGL_ANALYSIS_MAX_HITS

    @property
    def total_ranks(self) -> int:
        if self.depth <= 0 or self.depth > len(self.operation_pool):
            return 0
        return math.comb(len(self.operation_pool), self.depth)

    @property
    def bounded_end_rank(self) -> int:
        total = self.total_ranks
        if self.end_rank is None:
            return total
        return min(max(0, int(self.end_rank)), total)


@dataclass(frozen=True)
class UltimateOpenGLStreamAnalysis:
    supported: bool
    complete: bool
    status: str
    decompressed_size: int = 0
    complete_scanlines: int = 0
    usable_scanlines: int = 0
    error_offset: int | None = None
    zlib_error: str = ""
    stored_adler: int | None = None
    computed_adler: int | None = None
    adler_status: str = "adler_unknown"
    proof_flags: tuple[str, ...] = ()
    score: tuple[int, ...] = ()


@dataclass(frozen=True)
class UltimateOpenGLAnalysisHit:
    pool_index: int
    depth: int
    rank: int
    operation_indices: tuple[int, ...]
    status: str
    decompressed_size: int
    usable_scanlines: int
    error_offset: int | None
    stored_adler: int | None
    computed_adler: int | None
    adler_status: str
    score: tuple[int, ...]
    proof_flags: tuple[str, ...] = ()


@dataclass(frozen=True)
class UltimateOpenGLAnalysisResult:
    hits: tuple[UltimateOpenGLAnalysisHit, ...]
    tested: int
    pruned: int
    start_rank: int
    next_rank: int
    end_rank: int
    truncated: bool = False
    backend: str = "opengl"
    reason: str = ""
    covered_rank_count: int = 0
    fallback_reason: str = ""
    shader_used: bool = False
    setup_ms: float = 0.0
    dispatch_ms: float = 0.0


@dataclass
class UltimateOpenGLAnalysisSession:
    gpu_config: gpu_runtime.GpuRuntimeConfig
    harness_factory: Callable[..., gpu_opengl.OpenGLComputeHarness] = gpu_opengl.create_compute_harness
    harness: Any = None
    shader: Any = None
    setup_ms: float = 0.0
    dispatch_ms: float = 0.0
    shards: int = 0

    def ensure(self) -> float:
        setup_started = time.perf_counter()
        if self.harness is None:
            self.harness = self.harness_factory(auto_install=self.gpu_config.install_missing)
        if self.shader is None:
            self.shader = self.harness.compile_compute_shader(ULTIMATE_OPENGL_ANALYSIS_SHADER)
        elapsed = (time.perf_counter() - setup_started) * 1000.0
        self.setup_ms += elapsed
        return elapsed

    def run(
        self,
        plan: UltimateOpenGLAnalysisPlan,
        *,
        max_ranks: int | None = ULTIMATE_OPENGL_ANALYSIS_BATCH_SIZE,
    ) -> UltimateOpenGLAnalysisResult:
        setup_delta = self.ensure()
        result = _run_analysis_shader_with_resources(
            plan,
            self.harness,
            self.shader,
            max_ranks=max_ranks,
        )
        self.dispatch_ms += result.dispatch_ms
        self.shards += 1
        return replace(result, setup_ms=setup_delta)

    def close(self) -> None:
        _release_resource(self.shader)
        self.shader = None
        if self.harness is not None:
            try:
                self.harness.release()
            except Exception:
                pass
        self.harness = None


def _idat_stream_from_png(data: bytes) -> bytes:
    try:
        return b"".join(chunk.data for chunk in png.iter_chunks(data) if chunk.chunk_type == b"IDAT")
    except png.PngFormatError:
        return b""


def build_plan(
    source_data: bytes,
    *,
    start_offset: int | None = None,
    target_adler: int | None = None,
    super_result: Any = None,
    max_offsets: int = 128,
) -> UltimateLinefeedGpuPlan:
    return UltimateLinefeedGpuPlan(
        source_length=len(source_data),
        idat_stream=_idat_stream_from_png(source_data),
        start_offset=start_offset,
        target_adler=target_adler,
        has_super_result=super_result is not None,
        max_offsets=max(1, int(max_offsets or 1)),
    )


def explain(
    plan: UltimateLinefeedGpuPlan,
    gpu_config: gpu_runtime.GpuRuntimeConfig,
    *,
    availability_probe: Callable[..., gpu_opengl.GpuAvailability] = gpu_opengl.detect_opengl_compute,
) -> UltimateOpenGLDecision:
    if not gpu_config.enabled:
        return UltimateOpenGLDecision(False, "GPU was not requested.")
    if gpu_config.backend != "opengl":
        return UltimateOpenGLDecision(
            False,
            "GPU backend %s is not supported for Ultimate; using CPU workers." % gpu_config.backend,
        )
    if not plan.idat_stream:
        return UltimateOpenGLDecision(False, "Ultimate GPU preflight needs an IDAT stream; using CPU workers.")

    try:
        availability = availability_probe(auto_install=gpu_config.install_missing)
    except TypeError:
        availability = availability_probe()
    if not availability.available:
        return UltimateOpenGLDecision(
            False,
            "OpenGL unavailable (%s); using CPU workers." % availability.reason,
            availability,
        )
    return UltimateOpenGLDecision(
        True,
        "OpenGL Ultimate offset preflight active; CPU still runs the repair search.",
        availability,
    )


def supports_gpu(
    plan: UltimateLinefeedGpuPlan,
    gpu_config: gpu_runtime.GpuRuntimeConfig,
) -> bool:
    return explain(plan, gpu_config).runnable


def supports(
    plan: UltimateLinefeedGpuPlan,
    gpu_config: gpu_runtime.GpuRuntimeConfig,
) -> bool:
    return supports_gpu(plan, gpu_config)


def build_analysis_plan(
    root_stream: bytes,
    *,
    width: int,
    height: int,
    bit_depth: int,
    color_type: int,
    scanline_size: int,
    expected_size: int,
    operation_pool: tuple[Any, ...],
    pool_index: int = 0,
    depth: int = 1,
    start_rank: int = 0,
    end_rank: int | None = None,
    target_adler: int | None = None,
    max_hits: int = ULTIMATE_OPENGL_ANALYSIS_MAX_HITS,
) -> UltimateOpenGLAnalysisPlan:
    return UltimateOpenGLAnalysisPlan(
        root_stream=bytes(root_stream),
        width=int(width),
        height=int(height),
        bit_depth=int(bit_depth),
        color_type=int(color_type),
        scanline_size=int(scanline_size),
        expected_size=int(expected_size),
        operation_pool=tuple(operation_pool),
        pool_index=int(pool_index),
        depth=max(1, int(depth)),
        start_rank=max(0, int(start_rank)),
        end_rank=None if end_rank is None else max(0, int(end_rank)),
        target_adler=target_adler,
        max_hits=max(1, int(max_hits or 1)),
    )


def explain_analysis(
    plan: UltimateOpenGLAnalysisPlan,
    gpu_config: gpu_runtime.GpuRuntimeConfig,
    *,
    availability_probe: Callable[..., gpu_opengl.GpuAvailability] = gpu_opengl.detect_opengl_compute,
) -> UltimateOpenGLDecision:
    if not gpu_config.enabled:
        return UltimateOpenGLDecision(False, "GPU was not requested.")
    if gpu_config.backend != "opengl":
        return UltimateOpenGLDecision(
            False,
            "GPU backend %s is not supported for Ultimate analysis; using CPU workers."
            % gpu_config.backend,
        )
    if not plan.root_stream:
        return UltimateOpenGLDecision(False, "Ultimate GPU zlib analysis needs an IDAT stream; using CPU workers.")
    if plan.depth <= 0 or plan.depth > len(plan.operation_pool):
        return UltimateOpenGLDecision(False, "Ultimate GPU zlib analysis has no operation ranks to scan.")
    if plan.bounded_end_rank <= plan.start_rank:
        return UltimateOpenGLDecision(False, "Ultimate GPU zlib analysis shard is already exhausted.")
    if plan.scanline_size <= 0 or plan.height <= 0 or plan.expected_size <= 0:
        return UltimateOpenGLDecision(False, "Ultimate GPU zlib analysis needs non-interlaced scanline metadata.")

    try:
        availability = availability_probe(auto_install=gpu_config.install_missing)
    except TypeError:
        availability = availability_probe()
    if not availability.available:
        return UltimateOpenGLDecision(
            False,
            "OpenGL unavailable (%s); using CPU workers." % availability.reason,
            availability,
        )
    return UltimateOpenGLDecision(
        True,
        "OpenGL Ultimate zlib analysis active; CPU will confirm nominated repairs.",
        availability,
    )


def _combination_indices_at_rank(n: int, r: int, rank: int) -> tuple[int, ...] | None:
    if r <= 0 or n < r:
        return None
    total = math.comb(n, r)
    rank = max(0, int(rank))
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
    return tuple(indices)


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


def _operation_field(operation: Any, name: str, default: Any = None) -> Any:
    if isinstance(operation, dict):
        return operation.get(name, default)
    return getattr(operation, name, default)


def _operation_sort_key(operation: Any) -> tuple[int, int, str]:
    return (
        int(_operation_field(operation, "stream_offset", 0) or 0),
        len(bytes(_operation_field(operation, "old_bytes", b"") or b"")),
        str(_operation_field(operation, "kind", "")),
    )


def _normalize_operations(operations: tuple[Any, ...]) -> tuple[Any, ...]:
    return tuple(sorted(operations, key=_operation_sort_key, reverse=True))


def _apply_operation(stream: bytes, operation: Any) -> bytes | None:
    try:
        offset = int(_operation_field(operation, "stream_offset", 0) or 0)
        old = bytes(_operation_field(operation, "old_bytes", b"") or b"")
        new = bytes(_operation_field(operation, "new_bytes", b"") or b"")
    except (TypeError, ValueError):
        return None
    if offset < 0 or offset > len(stream):
        return None
    if old:
        if offset + len(old) > len(stream) or stream[offset : offset + len(old)] != old:
            return None
        return stream[:offset] + new + stream[offset + len(old) :]
    return stream[:offset] + new + stream[offset:]


def _replay_operations(stream: bytes, operations: tuple[Any, ...]) -> bytes | None:
    current = stream
    for operation in _normalize_operations(operations):
        current = _apply_operation(current, operation)
        if current is None:
            return None
    return current


def _stream_adler_status(
    *,
    stored_adler: int | None,
    computed_adler: int | None,
    target_adler: int | None,
) -> str:
    if computed_adler is None:
        return "adler_unknown"
    if target_adler is not None:
        return "adler_match" if computed_adler == target_adler else "adler_mismatch"
    if stored_adler is None:
        return "adler_unknown"
    return "adler_match" if computed_adler == stored_adler else "adler_mismatch"


def _analysis_score(analysis: UltimateOpenGLStreamAnalysis, operation_count: int) -> tuple[int, ...]:
    status_rank = {
        "complete": 6,
        "bad_adler": 5,
        "partial": 4,
        "host_deflate_required": 4,
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
    error_offset = analysis.error_offset if analysis.error_offset is not None else -1
    return (
        1 if analysis.complete else 0,
        status_rank,
        analysis.usable_scanlines,
        analysis.complete_scanlines,
        adler_rank,
        -operation_count,
        error_offset,
    )


def analyze_zlib_stream_for_gpu(
    stream: bytes,
    *,
    scanline_size: int,
    height: int,
    expected_size: int,
    target_adler: int | None = None,
) -> UltimateOpenGLStreamAnalysis:
    stored_adler = idat.zlib_trailer_adler(stream)
    if len(stream) < 2 or not idat.zlib_header_info(stream[:2].hex()).valid:
        analysis = UltimateOpenGLStreamAnalysis(
            True,
            False,
            "bad_zlib_header",
            stored_adler=stored_adler,
            proof_flags=("bad_zlib_header",),
        )
        return replace(analysis, score=_analysis_score(analysis, 0))

    decompressed, zlib_complete, error, error_offset = idat._decompress_until_error_details(stream)
    complete_scanlines, usable_scanlines = idat._count_usable_scanlines(
        decompressed,
        max(1, int(scanline_size)),
        max(0, int(height)),
    )
    status = idat._idat_stream_status(
        error,
        complete=zlib_complete,
        decompressed_size=len(decompressed),
        expected_size=max(0, int(expected_size)),
    )
    complete = status == "complete" and usable_scanlines == int(height)
    computed_adler = idat._computed_adler_for_status(status, decompressed)
    adler_status = _stream_adler_status(
        stored_adler=stored_adler,
        computed_adler=computed_adler,
        target_adler=target_adler,
    )
    proof_flags: list[str] = []
    if zlib_complete:
        proof_flags.append("zlib_eof")
    if status == "complete":
        proof_flags.append("size_match")
    if usable_scanlines == int(height):
        proof_flags.append("scanlines_complete")
    if adler_status == "adler_match":
        proof_flags.append("adler_match")
    if complete and (target_adler is None or adler_status == "adler_match"):
        proof_flags.append("terminal")
    analysis = UltimateOpenGLStreamAnalysis(
        True,
        complete,
        "complete" if complete else status,
        decompressed_size=len(decompressed),
        complete_scanlines=complete_scanlines,
        usable_scanlines=usable_scanlines,
        error_offset=error_offset,
        zlib_error=error,
        stored_adler=stored_adler,
        computed_adler=computed_adler,
        adler_status=adler_status,
        proof_flags=tuple(proof_flags),
    )
    return replace(analysis, score=_analysis_score(analysis, 0))


def _analysis_is_nomination(analysis: UltimateOpenGLStreamAnalysis) -> bool:
    if "terminal" in analysis.proof_flags:
        return True
    if "host_deflate_required" in analysis.proof_flags:
        return True
    if analysis.adler_status == "adler_match":
        return True
    if analysis.status in ("complete", "bad_adler", "partial") and analysis.usable_scanlines > 0:
        return True
    return analysis.status == "trailing_data" and analysis.usable_scanlines > 0


def _remember_analysis_hit(
    hits: tuple[UltimateOpenGLAnalysisHit, ...],
    hit: UltimateOpenGLAnalysisHit,
    *,
    limit: int,
) -> tuple[tuple[UltimateOpenGLAnalysisHit, ...], bool]:
    ranked = sorted((*hits, hit), key=lambda item: item.score, reverse=True)
    truncated = len(ranked) > limit
    return tuple(ranked[:limit]), truncated


def _proof_flags_from_mask(mask: int) -> tuple[str, ...]:
    flags: list[str] = []
    if mask & ULTIMATE_OPENGL_ANALYSIS_PROOF_ZLIB_EOF:
        flags.append("zlib_eof")
    if mask & ULTIMATE_OPENGL_ANALYSIS_PROOF_SIZE_MATCH:
        flags.append("size_match")
    if mask & ULTIMATE_OPENGL_ANALYSIS_PROOF_SCANLINES_COMPLETE:
        flags.append("scanlines_complete")
    if mask & ULTIMATE_OPENGL_ANALYSIS_PROOF_ADLER_MATCH:
        flags.append("adler_match")
    if mask & ULTIMATE_OPENGL_ANALYSIS_PROOF_TERMINAL:
        flags.append("terminal")
    if mask & ULTIMATE_OPENGL_ANALYSIS_PROOF_HOST_DEFLATE_REQUIRED:
        flags.append("host_deflate_required")
    if mask & ULTIMATE_OPENGL_ANALYSIS_PROOF_OP_VALID:
        flags.append("op_valid")
    return tuple(flags)


def _adler_status_from_code(code: int) -> str:
    return {
        1: "adler_mismatch",
        2: "adler_unknown",
        3: "adler_rebuilt",
        4: "adler_match",
    }.get(int(code), "adler_unknown")


def _encode_analysis_operations(operation_pool: tuple[Any, ...]) -> bytes:
    values: list[int] = []
    for operation in operation_pool:
        offset = int(_operation_field(operation, "stream_offset", 0) or 0)
        old = bytes(_operation_field(operation, "old_bytes", b"") or b"")
        new = bytes(_operation_field(operation, "new_bytes", b"") or b"")
        if len(old) > 4 or len(new) > 4:
            raise gpu_opengl.OpenGLComputeUnavailable(
                "Ultimate OpenGL analysis supports operations up to 4 bytes"
            )
        values.extend(
            [
                offset,
                len(old),
                len(new),
                *(old + b"\x00" * 4)[:4],
                *(new + b"\x00" * 4)[:4],
            ]
        )
    if not values:
        values = [0] * ULTIMATE_OPENGL_ANALYSIS_OP_WORDS
    return _uint_buffer_data(values)


def _read_analysis_hits(
    buffer: Any,
    *,
    max_results: int,
    default_end_rank: int,
) -> tuple[tuple[UltimateOpenGLAnalysisHit, ...], int, int, bool]:
    reader = getattr(buffer, "read", None)
    if not callable(reader):
        raise gpu_opengl.OpenGLComputeUnavailable("OpenGL analysis buffer cannot be read back")
    raw = reader()
    if len(raw) < 12:
        return (), 0, 0, False
    count, tested, pruned = struct.unpack_from("<III", raw, 0)
    capped_count = min(int(count), int(max_results))
    hits: list[UltimateOpenGLAnalysisHit] = []
    for index in range(capped_count):
        offset = 12 + index * ULTIMATE_OPENGL_ANALYSIS_HIT_WORDS * 4
        if offset + ULTIMATE_OPENGL_ANALYSIS_HIT_WORDS * 4 > len(raw):
            break
        words = struct.unpack_from("<%sI" % ULTIMATE_OPENGL_ANALYSIS_HIT_WORDS, raw, offset)
        rank = int(words[0]) | (int(words[1]) << 32)
        status = ULTIMATE_OPENGL_ANALYSIS_STATUS_BY_CODE.get(int(words[5]), "unsupported")
        proof_flags = _proof_flags_from_mask(int(words[12]))
        analysis = UltimateOpenGLStreamAnalysis(
            True,
            "terminal" in proof_flags or status == "complete",
            status,
            decompressed_size=int(words[6]),
            complete_scanlines=int(words[7]),
            usable_scanlines=int(words[7]),
            error_offset=None if int(words[8]) == 0xFFFFFFFF else int(words[8]),
            stored_adler=int(words[9]),
            computed_adler=None if int(words[10]) == 0 else int(words[10]),
            adler_status=_adler_status_from_code(int(words[11])),
            proof_flags=proof_flags,
        )
        hit = UltimateOpenGLAnalysisHit(
            pool_index=int(words[2]),
            depth=int(words[3]),
            rank=rank,
            operation_indices=(int(words[4]),),
            status=status,
            decompressed_size=int(words[6]),
            usable_scanlines=int(words[7]),
            error_offset=None if int(words[8]) == 0xFFFFFFFF else int(words[8]),
            stored_adler=int(words[9]),
            computed_adler=None if int(words[10]) == 0 else int(words[10]),
            adler_status=_adler_status_from_code(int(words[11])),
            score=_analysis_score(analysis, int(words[3])),
            proof_flags=proof_flags,
        )
        hits.append(hit)
    ranked = tuple(sorted(hits, key=lambda item: item.score, reverse=True))
    return ranked, int(tested), int(pruned), int(count) > int(max_results)


def _run_analysis_shader_with_resources(
    plan: UltimateOpenGLAnalysisPlan,
    harness: Any,
    shader: Any,
    *,
    max_ranks: int | None = ULTIMATE_OPENGL_ANALYSIS_BATCH_SIZE,
) -> UltimateOpenGLAnalysisResult:
    if plan.depth != 1:
        raise gpu_opengl.OpenGLComputeUnavailable(
            "Ultimate OpenGL shader currently supports depth-1 shards; using host analysis for this shard."
        )
    start_rank = max(0, min(int(plan.start_rank), plan.total_ranks))
    end_rank = plan.bounded_end_rank
    if max_ranks is not None:
        end_rank = min(end_rank, start_rank + max(0, int(max_ranks)))
    if end_rank <= start_rank:
        return UltimateOpenGLAnalysisResult(
            (),
            0,
            0,
            start_rank,
            start_rank,
            end_rank,
            covered_rank_count=0,
            shader_used=True,
        )
    if start_rank >> 32:
        raise gpu_opengl.OpenGLComputeUnavailable(
            "Ultimate OpenGL shader cannot start a shard above 32-bit operation rank yet."
        )

    stream_buffer = None
    operation_buffer = None
    output_buffer = None
    dispatch_ms = 0.0
    try:
        stream_buffer = harness.buffer(_uint_buffer_data(list(plan.root_stream)))
        operation_buffer = harness.buffer(_encode_analysis_operations(plan.operation_pool))
        output_words = 3 + (int(plan.max_hits) * ULTIMATE_OPENGL_ANALYSIS_HIT_WORDS)
        output_buffer = harness.buffer(reserve=output_words * 4)
        _bind_storage_buffer(stream_buffer, 0)
        _bind_storage_buffer(operation_buffer, 1)
        _bind_storage_buffer(output_buffer, 2)
        writer = getattr(output_buffer, "write", None)
        if callable(writer):
            writer(b"\x00" * (output_words * 4))

        batch_count = max(0, int(end_rank) - int(start_rank))
        _set_uniform(shader, "stream_len", len(plan.root_stream))
        _set_uniform(shader, "operation_count", len(plan.operation_pool))
        _set_uniform(shader, "pool_index", plan.pool_index)
        _set_uniform(shader, "depth", plan.depth)
        _set_uniform(shader, "base_rank_low", int(start_rank) & 0xFFFFFFFF)
        _set_uniform(shader, "base_rank_high", (int(start_rank) >> 32) & 0xFFFFFFFF)
        _set_uniform(shader, "batch_count", batch_count)
        _set_uniform(shader, "max_results", plan.max_hits)
        _set_uniform(shader, "scanline_size", plan.scanline_size)
        _set_uniform(shader, "image_height", plan.height)
        _set_uniform(shader, "expected_size", plan.expected_size)
        _set_uniform(shader, "target_adler", 0 if plan.target_adler is None else int(plan.target_adler))
        _set_uniform(shader, "has_target_adler", 0 if plan.target_adler is None else 1)
        dispatch_started = time.perf_counter()
        harness.dispatch(shader, group_x=max(1, (batch_count + 127) // 128))
        harness.memory_barrier()
        hits, tested, pruned, truncated = _read_analysis_hits(
            output_buffer,
            max_results=plan.max_hits,
            default_end_rank=end_rank,
        )
        dispatch_ms = (time.perf_counter() - dispatch_started) * 1000.0
    finally:
        _release_resource(output_buffer)
        _release_resource(operation_buffer)
        _release_resource(stream_buffer)

    return UltimateOpenGLAnalysisResult(
        hits,
        tested,
        pruned,
        start_rank,
        end_rank,
        end_rank,
        truncated=truncated,
        reason="" if end_rank >= plan.bounded_end_rank else "rank cap reached",
        covered_rank_count=max(0, end_rank - start_rank),
        shader_used=True,
        dispatch_ms=dispatch_ms,
    )


def _run_analysis_shader(
    plan: UltimateOpenGLAnalysisPlan,
    gpu_config: gpu_runtime.GpuRuntimeConfig,
    *,
    harness_factory: Callable[..., gpu_opengl.OpenGLComputeHarness] = gpu_opengl.create_compute_harness,
    max_ranks: int | None = ULTIMATE_OPENGL_ANALYSIS_BATCH_SIZE,
) -> UltimateOpenGLAnalysisResult:
    harness = None
    shader = None
    setup_ms = 0.0
    try:
        setup_started = time.perf_counter()
        harness = harness_factory(auto_install=gpu_config.install_missing)
        shader = harness.compile_compute_shader(ULTIMATE_OPENGL_ANALYSIS_SHADER)
        setup_ms = (time.perf_counter() - setup_started) * 1000.0
        result = _run_analysis_shader_with_resources(
            plan,
            harness,
            shader,
            max_ranks=max_ranks,
        )
        return replace(result, setup_ms=setup_ms)
    finally:
        _release_resource(shader)
        if harness is not None:
            harness.release()


def _run_analysis_host(
    plan: UltimateOpenGLAnalysisPlan,
    *,
    max_ranks: int | None = ULTIMATE_OPENGL_ANALYSIS_BATCH_SIZE,
    fallback_reason: str = "",
) -> UltimateOpenGLAnalysisResult:
    start_rank = max(0, min(int(plan.start_rank), plan.total_ranks))
    end_rank = plan.bounded_end_rank
    if max_ranks is not None:
        end_rank = min(end_rank, start_rank + max(0, int(max_ranks)))
    if end_rank <= start_rank:
        return UltimateOpenGLAnalysisResult(
            (),
            0,
            0,
            start_rank,
            start_rank,
            end_rank,
            covered_rank_count=0,
            fallback_reason=fallback_reason,
        )

    indices = _combination_indices_at_rank(len(plan.operation_pool), plan.depth, start_rank)
    rank = start_rank
    tested = 0
    pruned = 0
    hits: tuple[UltimateOpenGLAnalysisHit, ...] = ()
    truncated = False
    while indices is not None and rank < end_rank:
        operations = tuple(plan.operation_pool[index] for index in indices)
        candidate_stream = _replay_operations(plan.root_stream, operations)
        if candidate_stream is None:
            pruned += 1
        else:
            tested += 1
            analysis = analyze_zlib_stream_for_gpu(
                candidate_stream,
                scanline_size=plan.scanline_size,
                height=plan.height,
                expected_size=plan.expected_size,
                target_adler=plan.target_adler,
            )
            score = _analysis_score(analysis, plan.depth)
            if _analysis_is_nomination(analysis):
                hit = UltimateOpenGLAnalysisHit(
                    pool_index=plan.pool_index,
                    depth=plan.depth,
                    rank=rank,
                    operation_indices=tuple(int(index) for index in indices),
                    status=analysis.status,
                    decompressed_size=analysis.decompressed_size,
                    usable_scanlines=analysis.usable_scanlines,
                    error_offset=analysis.error_offset,
                    stored_adler=analysis.stored_adler,
                    computed_adler=analysis.computed_adler,
                    adler_status=analysis.adler_status,
                    score=score,
                    proof_flags=analysis.proof_flags,
                )
                hits, hit_truncated = _remember_analysis_hit(
                    hits,
                    hit,
                    limit=plan.max_hits,
                )
                truncated = truncated or hit_truncated
        rank += 1
        indices = _next_combination_indices(indices, len(plan.operation_pool), plan.depth)

    reason = "rank cap reached" if end_rank < plan.bounded_end_rank else ""
    return UltimateOpenGLAnalysisResult(
        hits,
        tested,
        pruned,
        start_rank,
        rank,
        end_rank,
        truncated=truncated,
        reason=reason,
        covered_rank_count=max(0, rank - start_rank),
        fallback_reason=fallback_reason,
        shader_used=False,
    )


def run_analysis_gpu(
    plan: UltimateOpenGLAnalysisPlan,
    gpu_config: gpu_runtime.GpuRuntimeConfig,
    *,
    harness_factory: Callable[..., gpu_opengl.OpenGLComputeHarness] = gpu_opengl.create_compute_harness,
    max_ranks: int | None = ULTIMATE_OPENGL_ANALYSIS_BATCH_SIZE,
    allow_host_fallback: bool = True,
) -> UltimateOpenGLAnalysisResult:
    try:
        return _run_analysis_shader(
            plan,
            gpu_config,
            harness_factory=harness_factory,
            max_ranks=max_ranks,
        )
    except Exception as exc:
        if not allow_host_fallback:
            raise
        return _run_analysis_host(
            plan,
            max_ranks=max_ranks,
            fallback_reason=str(exc),
        )


def _release_resource(resource: Any) -> None:
    release = getattr(resource, "release", None)
    if callable(release):
        try:
            release()
        except Exception:
            pass


def _bind_storage_buffer(buffer: Any, binding: int) -> None:
    binder = getattr(buffer, "bind_to_storage_buffer", None)
    if not callable(binder):
        raise gpu_opengl.OpenGLComputeUnavailable("OpenGL buffer cannot bind as storage buffer")
    binder(binding)


def _set_uniform(shader: Any, name: str, value: int) -> None:
    try:
        shader[name].value = int(value)
        return
    except Exception:
        pass
    setter = getattr(shader, "__setitem__", None)
    if callable(setter):
        try:
            shader[name] = int(value)
            return
        except Exception:
            pass


def _uint_buffer_data(values: list[int]) -> bytes:
    import struct

    return struct.pack("<%sI" % len(values), *[int(value) & 0xFFFFFFFF for value in values])


def _read_offsets(buffer: Any, *, max_results: int) -> tuple[tuple[int, ...], bool]:
    reader = getattr(buffer, "read", None)
    if not callable(reader):
        raise gpu_opengl.OpenGLComputeUnavailable("OpenGL buffer cannot be read back")
    raw = reader()
    if len(raw) < 4:
        return (), False
    import struct

    count = struct.unpack_from("<I", raw, 0)[0]
    capped_count = min(int(count), int(max_results))
    offsets: list[int] = []
    for index in range(capped_count):
        offset_at = 4 + index * 4
        if offset_at + 4 > len(raw):
            break
        offsets.append(struct.unpack_from("<I", raw, offset_at)[0])
    return tuple(offsets), int(count) > int(max_results)


def _sort_offsets_for_ultimate(plan: UltimateLinefeedGpuPlan, offsets: tuple[int, ...]) -> tuple[int, ...]:
    stream = plan.idat_stream
    if not stream:
        return ()
    anchor = plan.start_offset
    if anchor is None:
        anchor = 0
    anchor = min(max(0, int(anchor)), max(0, len(stream) - 1))
    trailer = max(0, len(stream) - 4)

    def rank(offset: int) -> tuple[int, int, int]:
        value = stream[offset] if 0 <= offset < len(stream) else 0
        weight = 0
        if offset == trailer:
            weight += 100000
        if value == 0x0A and not (offset > 0 and stream[offset - 1] == 0x0D):
            weight += 10000
        elif value == 0x0D:
            weight += 6000
        if offset >= anchor:
            weight += 2000
        weight -= min(abs(offset - anchor), 9000)
        return (-weight, abs(offset - anchor), offset)

    unique = tuple(dict.fromkeys(int(offset) for offset in offsets if 0 <= int(offset) < len(stream)))
    return tuple(sorted(unique, key=rank)[: plan.max_offsets])


def run_offset_preflight(
    plan: UltimateLinefeedGpuPlan,
    gpu_config: gpu_runtime.GpuRuntimeConfig,
    *,
    harness_factory: Callable[..., gpu_opengl.OpenGLComputeHarness] = gpu_opengl.create_compute_harness,
    max_results: int = ULTIMATE_OPENGL_OFFSET_MAX_RESULTS,
    batch_size: int = ULTIMATE_OPENGL_OFFSET_BATCH_SIZE,
) -> UltimateOpenGLOffsetResult:
    stream = plan.idat_stream
    if not stream:
        return UltimateOpenGLOffsetResult((), 0)

    harness = None
    shader = None
    stream_buffer = None
    output_buffer = None
    offsets: list[int] = []
    truncated = False
    try:
        harness = harness_factory(auto_install=gpu_config.install_missing)
        shader = harness.compile_compute_shader(ULTIMATE_OPENGL_OFFSET_SHADER)
        stream_buffer = harness.buffer(_uint_buffer_data(list(stream)))
        output_buffer = harness.buffer(reserve=(int(max_results) + 1) * 4)
        _bind_storage_buffer(stream_buffer, 0)
        _bind_storage_buffer(output_buffer, 1)

        safe_batch_size = max(1, int(batch_size))
        for base_offset in range(0, len(stream), safe_batch_size):
            batch_count = min(safe_batch_size, len(stream) - base_offset)
            output_buffer.orphan((int(max_results) + 1) * 4) if hasattr(output_buffer, "orphan") else None
            writer = getattr(output_buffer, "write", None)
            if callable(writer):
                writer(b"\x00" * ((int(max_results) + 1) * 4))
            _set_uniform(shader, "stream_len", len(stream))
            _set_uniform(shader, "base_offset", base_offset)
            _set_uniform(shader, "batch_count", batch_count)
            _set_uniform(shader, "max_results", max_results)
            harness.dispatch(shader, group_x=max(1, (batch_count + 127) // 128))
            harness.memory_barrier()
            batch_offsets, batch_truncated = _read_offsets(output_buffer, max_results=max_results)
            offsets.extend(batch_offsets)
            truncated = truncated or batch_truncated
            if len(offsets) >= max_results:
                truncated = True
                break
    finally:
        _release_resource(output_buffer)
        _release_resource(stream_buffer)
        _release_resource(shader)
        if harness is not None:
            harness.release()

    ranked = _sort_offsets_for_ultimate(plan, tuple(offsets))
    return UltimateOpenGLOffsetResult(ranked, len(stream), truncated=truncated)


def run_gpu(
    plan: UltimateLinefeedGpuPlan,
    gpu_config: gpu_runtime.GpuRuntimeConfig,
    **kwargs: Any,
) -> UltimateOpenGLOffsetResult:
    return run_offset_preflight(plan, gpu_config, **kwargs)
