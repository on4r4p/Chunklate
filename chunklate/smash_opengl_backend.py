from __future__ import annotations

from dataclasses import dataclass
import struct
from typing import Any, Callable
import zlib

from . import bruteforce, gpu_opengl, gpu_runtime, smash_backend


OPENGL_SBB_KERNEL_READY = True
OPENGL_SMOKE_MARKER = 0x53424247
OPENGL_REPLACE1_MAX_HITS = 1_048_576
OPENGL_REPLACE1_BATCH_SIZE = 8_388_480
OPENGL_REPLACE1_LARGE_PAYLOAD_BATCH_SIZE = 4_194_304
OPENGL_REPLACE1_HUGE_PAYLOAD_BATCH_SIZE = 2_097_152
OPENGL_HERMES_WIDE_BATCH_SIZE = 1_048_576
OPENGL_HERMES_MAX_CANDIDATE_BYTES = 16
OPENGL_HERMES_UINT_MAX = 0xFFFFFFFF
CRC32_POLY = 0xEDB88320


def _build_crc32_table() -> tuple[int, ...]:
    table: list[int] = []
    for value in range(256):
        crc = value
        for _bit in range(8):
            crc = (crc >> 1) ^ (CRC32_POLY if crc & 1 else 0)
        table.append(crc & 0xFFFFFFFF)
    return tuple(table)


CRC32_TABLE = _build_crc32_table()
OPENGL_HERMES1_EDIT_KINDS = {
    "Replace": "replace",
    "Insert": "insert",
    "Remove": "remove",
}
OPENGL_HERMES1_EDIT_KIND_INDEX = {
    "replace": 0,
    "insert": 1,
    "remove": 2,
}
OPENGL_SMOKE_SHADER = """
#version 430
layout(local_size_x = 1) in;
layout(std430, binding = 0) buffer OutputBuffer {
    uint values[];
};
void main() {
    values[0] = 0x53424247u;
}
"""
OPENGL_REPLACE1_CRC_SHADER = """
#version 430
layout(local_size_x = 128) in;

layout(std430, binding = 0) readonly buffer PrefixCrcBuffer {
    uint prefix_crcs[];
};

layout(std430, binding = 1) readonly buffer CandidateValueBuffer {
    uint candidate_values[];
};

layout(std430, binding = 2) buffer OutputBuffer {
    uint output_values[];
};

layout(std430, binding = 3) readonly buffer CandidatePrefixBuffer {
    uint candidate_prefix_values[];
};

uniform uint payload_len;
uniform uint position_count;
uniform uint value_count;
uniform uint target_crc;
uniform uint base_local_rank;
uniform uint batch_count;
uniform uint max_hits;
uniform uint edit_kind;
uniform uint candidate_len;
uniform uint candidate_low_len;
uniform uint candidate_prefix_len;
uniform uint candidate_low_base;
uniform uint generated_values;
uniform uint original_full_crc;

uint crc32_update(uint crc, uint byte_value) {
    crc = crc ^ (byte_value & 0xffu);
    for (int bit_index = 0; bit_index < 8; bit_index++) {
        uint mask = 0u - (crc & 1u);
        crc = (crc >> 1) ^ (0xedb88320u & mask);
    }
    return crc;
}

uint candidate_byte(uint inner_index, uint offset) {
    if (generated_values == 0u) {
        return candidate_values[inner_index] & 0xffu;
    }
    if (offset < candidate_prefix_len) {
        return candidate_prefix_values[offset] & 0xffu;
    }
    uint low_offset = offset - candidate_prefix_len;
    uint shift = 8u * (candidate_low_len - 1u - low_offset);
    return (inner_index >> shift) & 0xffu;
}

uint crc32_extend_byte(uint final_crc, uint byte_value) {
    uint crc = final_crc ^ 0xffffffffu;
    crc = crc32_update(crc, byte_value);
    return crc ^ 0xffffffffu;
}

uint gf2_matrix_times(uint mat[32], uint vec) {
    uint sum = 0u;
    for (uint index = 0u; index < 32u; index++) {
        if ((vec & 1u) != 0u) {
            sum ^= mat[index];
        }
        vec >>= 1u;
    }
    return sum;
}

void gf2_matrix_square(out uint square[32], uint mat[32]) {
    for (uint index = 0u; index < 32u; index++) {
        square[index] = gf2_matrix_times(mat, mat[index]);
    }
}

uint crc32_shift(uint crc, uint byte_len) {
    if (byte_len == 0u) {
        return crc;
    }

    uint odd[32];
    uint even[32];
    odd[0] = 0xedb88320u;
    uint row = 1u;
    for (uint index = 1u; index < 32u; index++) {
        odd[index] = row;
        row <<= 1u;
    }
    gf2_matrix_square(even, odd);
    gf2_matrix_square(odd, even);

    while (byte_len != 0u) {
        gf2_matrix_square(even, odd);
        if ((byte_len & 1u) != 0u) {
            crc = gf2_matrix_times(even, crc);
        }
        byte_len >>= 1u;
        if (byte_len == 0u) {
            break;
        }
        gf2_matrix_square(odd, even);
        if ((byte_len & 1u) != 0u) {
            crc = gf2_matrix_times(odd, crc);
        }
        byte_len >>= 1u;
    }
    return crc;
}

void main() {
    uint local_rank = gl_GlobalInvocationID.x;
    if (local_rank >= batch_count) {
        return;
    }

    uint rank = base_local_rank + local_rank;
    uint local_inner_index = rank / position_count;
    uint position = rank - (local_inner_index * position_count);
    uint inner_index = candidate_low_base + local_inner_index;
    if ((generated_values == 0u && inner_index >= value_count) || position >= position_count) {
        return;
    }

    uint suffix_start = position;
    uint candidate_crc = prefix_crcs[position];
    if (edit_kind == 0u) {
        suffix_start = position + candidate_len;
    } else if (edit_kind == 1u) {
        suffix_start = position;
    } else {
        suffix_start = position + candidate_len;
    }

    if (suffix_start > payload_len) {
        return;
    }

    if (edit_kind != 2u) {
        for (uint offset = 0u; offset < candidate_len; offset++) {
            candidate_crc = crc32_extend_byte(candidate_crc, candidate_byte(inner_index, offset));
        }
    }

    uint suffix_len = payload_len - suffix_start;
    uint original_suffix_crc = original_full_crc ^ crc32_shift(prefix_crcs[suffix_start], suffix_len);
    uint candidate_full_crc = crc32_shift(candidate_crc, suffix_len) ^ original_suffix_crc;

    if (candidate_full_crc == target_crc) {
        uint slot = atomicAdd(output_values[0], 1u);
        if (slot < max_hits) {
            output_values[slot + 1u] = rank;
        }
    }
}
"""


@dataclass(frozen=True)
class SmashOpenGLDecision:
    runnable: bool
    reason: str
    availability: gpu_opengl.GpuAvailability | None = None


@dataclass(frozen=True)
class OpenGLReplace1Result:
    hits: tuple[smash_backend.SmashCandidateHit, ...]
    tested: int
    truncated: bool = False


@dataclass(frozen=True)
class OpenGLReplace1Cursor:
    inner_index: int
    byte_position: int


@dataclass(frozen=True)
class OpenGLHermesSupport:
    length_plan: smash_backend.SmashLengthPlan
    edit_window: bruteforce.BruteForceEditWindow
    values: tuple[int, ...]
    edit_kind: str
    candidate_len: int
    generated_values: bool
    candidate_count: int
    position_count: int
    total_candidates: int


def _release_resource(resource: Any) -> None:
    release = getattr(resource, "release", None)
    if callable(release):
        try:
            release()
        except Exception:
            pass


def run_harness_smoke_test(
    gpu_config: gpu_runtime.GpuRuntimeConfig,
    *,
    harness_factory: Callable[..., gpu_opengl.OpenGLComputeHarness] = gpu_opengl.create_compute_harness,
) -> gpu_opengl.GpuAvailability:
    if not gpu_config.enabled:
        return gpu_opengl.GpuAvailability(False, "opengl", "GPU was not requested")

    harness = None
    shader = None
    output_buffer = None
    try:
        harness = harness_factory(auto_install=gpu_config.install_missing)
        shader = harness.compile_compute_shader(OPENGL_SMOKE_SHADER)
        output_buffer = harness.buffer(reserve=4)
        binder = getattr(output_buffer, "bind_to_storage_buffer", None)
        if not callable(binder):
            return gpu_opengl.GpuAvailability(False, "opengl", "OpenGL buffer cannot bind as storage buffer")
        binder(0)
        harness.dispatch(shader, group_x=1)
        harness.memory_barrier()
        reader = getattr(output_buffer, "read", None)
        if not callable(reader):
            return gpu_opengl.GpuAvailability(False, "opengl", "OpenGL buffer cannot be read back")
        data = reader()
        if len(data) < 4 or int.from_bytes(data[:4], "little") != OPENGL_SMOKE_MARKER:
            return gpu_opengl.GpuAvailability(False, "opengl", "OpenGL compute smoke test returned unexpected data")
    except gpu_opengl.OpenGLComputeUnavailable as exc:
        return gpu_opengl.GpuAvailability(False, "opengl", exc.reason)
    except Exception as exc:
        return gpu_opengl.GpuAvailability(False, "opengl", "OpenGL compute smoke test failed: %s" % exc)
    finally:
        _release_resource(output_buffer)
        _release_resource(shader)
        if harness is not None:
            harness.release()

    return gpu_opengl.GpuAvailability(True, "opengl", "OpenGL compute harness ready")


def _has_crc_target(plan: smash_backend.SmashCandidatePlan) -> bool:
    return bool(plan.old_crc)


def _is_indexable(plan: smash_backend.SmashCandidatePlan) -> bool:
    return bool(plan.lengths)


def _length_plan_values(length_plan: smash_backend.SmashLengthPlan) -> tuple[int, ...]:
    if len(length_plan.chunk_format) != 1:
        return ()
    if str(length_plan.chunk_format[0]).replace("!", "") != "B":
        return ()
    if len(length_plan.chunk_data) != 1:
        return ()
    values: list[int] = []
    for value in length_plan.chunk_data[0]:
        try:
            int_value = int(value)
        except (TypeError, ValueError):
            return ()
        if int_value < 0 or int_value > 255:
            return ()
        values.append(int_value)
    return tuple(values)


def _is_full_byte_range(values: tuple[Any, ...]) -> bool:
    if len(values) != 256:
        return False
    try:
        return all(int(value) == index for index, value in enumerate(values))
    except (TypeError, ValueError):
        return False


def _length_plan_candidate_layout(
    length_plan: smash_backend.SmashLengthPlan,
) -> tuple[int, tuple[int, ...], bool, int] | None:
    formats = tuple(str(item).replace("!", "") for item in length_plan.chunk_format)
    if not formats or any(item != "B" for item in formats):
        return None
    candidate_len = len(formats)
    if candidate_len < 1 or candidate_len > OPENGL_HERMES_MAX_CANDIDATE_BYTES:
        return None
    if len(length_plan.chunk_data) != candidate_len:
        return None

    if candidate_len == 1:
        values = _length_plan_values(length_plan)
        if not values:
            return None
        return 1, values, False, len(values)

    if not all(_is_full_byte_range(tuple(values)) for values in length_plan.chunk_data):
        return None
    candidate_count = 256**candidate_len
    if int(length_plan.max_iter) != candidate_count:
        return None
    return candidate_len, (), True, candidate_count


def _hermes1_edit_kind(plan: smash_backend.SmashCandidatePlan) -> str:
    return OPENGL_HERMES1_EDIT_KINDS.get(str(plan.edit_mode), "")


def _hermes1_position_count(
    edit_window: bruteforce.BruteForceEditWindow,
    edit_kind: str,
    candidate_len: int,
) -> int:
    if edit_kind in {"replace", "insert", "remove"}:
        return bruteforce.twobytes_scan_position_count(edit_window.to_brute, candidate_len * 2)
    return 0


def _replace1_support_details(plan: smash_backend.SmashCandidatePlan) -> OpenGLHermesSupport | None:
    if len(plan.lengths) != 1:
        return None
    edit_kind = _hermes1_edit_kind(plan)
    if not edit_kind:
        return None
    length_plan = plan.lengths[0]
    layout = _length_plan_candidate_layout(length_plan)
    if layout is None:
        return None
    candidate_len, values, generated_values, candidate_count = layout
    edit_window = bruteforce.edit_window(
        plan.data_hex,
        plan.data_offset,
        plan.chunk_length,
        plan.edit_mode,
        plan.bf_mode,
        length_plan.length,
    )
    payload_len = len(edit_window.to_brute) // 2
    if payload_len <= 0:
        return None
    if candidate_len > payload_len:
        return None
    if edit_kind == "remove":
        values = (0,)
        generated_values = False
        candidate_count = 1
    position_count = _hermes1_position_count(edit_window, edit_kind, candidate_len)
    if position_count <= 0:
        return None
    total_candidates = int(position_count) * int(candidate_count)
    if total_candidates <= 0:
        return None
    return OpenGLHermesSupport(
        length_plan=length_plan,
        edit_window=edit_window,
        values=values,
        edit_kind=edit_kind,
        candidate_len=candidate_len,
        generated_values=generated_values,
        candidate_count=candidate_count,
        position_count=position_count,
        total_candidates=total_candidates,
    )


def _kernel_supports_plan(plan: smash_backend.SmashCandidatePlan) -> bool:
    return (
        OPENGL_SBB_KERNEL_READY
        and plan.bf_mode == "TwoBytes"
        and plan.edit_mode in OPENGL_HERMES1_EDIT_KINDS
        and _replace1_support_details(plan) is not None
    )


def _candidate_bytes_from_inner_index(support: OpenGLHermesSupport, inner_index: int) -> bytes | None:
    safe_inner = int(inner_index)
    if safe_inner < 0 or safe_inner >= support.candidate_count:
        return None
    if not support.generated_values:
        return bytes((support.values[safe_inner],))
    return safe_inner.to_bytes(support.candidate_len, "big")


def _crc32_extend_byte(final_crc: int, byte_value: int) -> int:
    raw_crc = (int(final_crc) ^ 0xFFFFFFFF) & 0xFFFFFFFF
    raw_crc = CRC32_TABLE[(raw_crc ^ int(byte_value)) & 0xFF] ^ (raw_crc >> 8)
    return (raw_crc ^ 0xFFFFFFFF) & 0xFFFFFFFF


def _gf2_matrix_times(matrix: tuple[int, ...] | list[int], vector: int) -> int:
    safe_vector = int(vector) & 0xFFFFFFFF
    total = 0
    index = 0
    while safe_vector:
        if safe_vector & 1:
            total ^= int(matrix[index])
        safe_vector >>= 1
        index += 1
    return total & 0xFFFFFFFF


def _gf2_matrix_square(matrix: tuple[int, ...] | list[int]) -> tuple[int, ...]:
    return tuple(_gf2_matrix_times(matrix, int(matrix[index])) for index in range(32))


def _crc32_shift(final_crc: int, byte_len: int) -> int:
    safe_crc = int(final_crc) & 0xFFFFFFFF
    safe_len = max(0, int(byte_len))
    if safe_len == 0:
        return safe_crc

    odd = [0] * 32
    odd[0] = CRC32_POLY
    row = 1
    for index in range(1, 32):
        odd[index] = row
        row <<= 1
    even = _gf2_matrix_square(odd)
    odd = _gf2_matrix_square(even)

    while safe_len:
        even = _gf2_matrix_square(odd)
        if safe_len & 1:
            safe_crc = _gf2_matrix_times(even, safe_crc)
        safe_len >>= 1
        if not safe_len:
            break
        odd = _gf2_matrix_square(even)
        if safe_len & 1:
            safe_crc = _gf2_matrix_times(odd, safe_crc)
        safe_len >>= 1
    return safe_crc & 0xFFFFFFFF


def crc32_combine(first_crc: int, second_crc: int, second_len: int) -> int:
    return (_crc32_shift(first_crc, second_len) ^ int(second_crc)) & 0xFFFFFFFF


def _prefix_crc_values(payload: tuple[int, ...]) -> tuple[int, ...]:
    crc = zlib.crc32(b"IDAT") & 0xFFFFFFFF
    values = [crc]
    for byte_value in payload:
        crc = _crc32_extend_byte(crc, int(byte_value))
        values.append(crc)
    return tuple(values)


def _patched_candidate_crc(
    *,
    prefix_crcs: tuple[int, ...],
    original_full_crc: int,
    payload_len: int,
    position: int,
    candidate_bytes: bytes,
    edit_kind: str,
) -> int:
    safe_position = int(position)
    candidate_len = len(candidate_bytes)
    suffix_start = safe_position if edit_kind == "insert" else safe_position + candidate_len
    if suffix_start < 0 or suffix_start > int(payload_len):
        raise IndexError("suffix start is outside payload")

    candidate_crc = int(prefix_crcs[safe_position])
    if edit_kind != "remove":
        for byte_value in candidate_bytes:
            candidate_crc = _crc32_extend_byte(candidate_crc, byte_value)

    suffix_len = int(payload_len) - suffix_start
    suffix_crc = int(original_full_crc) ^ _crc32_shift(int(prefix_crcs[suffix_start]), suffix_len)
    return (_crc32_shift(candidate_crc, suffix_len) ^ suffix_crc) & 0xFFFFFFFF


def _dynamic_batch_size(support: OpenGLHermesSupport) -> int:
    payload_len = len(support.edit_window.to_brute) // 2
    if payload_len >= 1_000_000:
        base = OPENGL_REPLACE1_HUGE_PAYLOAD_BATCH_SIZE
    elif payload_len >= 250_000:
        base = OPENGL_REPLACE1_LARGE_PAYLOAD_BATCH_SIZE
    else:
        base = OPENGL_REPLACE1_BATCH_SIZE
    if support.candidate_len > 4:
        base = min(base, OPENGL_HERMES_WIDE_BATCH_SIZE)
    return max(1, int(base))


def explain(
    plan: smash_backend.SmashCandidatePlan,
    gpu_config: gpu_runtime.GpuRuntimeConfig,
    *,
    availability_probe: Callable[..., gpu_opengl.GpuAvailability] = gpu_opengl.detect_opengl_compute,
) -> SmashOpenGLDecision:
    if not gpu_config.enabled:
        return SmashOpenGLDecision(False, "GPU was not requested.")
    if gpu_config.backend != "opengl":
        return SmashOpenGLDecision(False, "GPU backend %s is not supported; using CPU workers." % gpu_config.backend)
    if plan.chunk_name != b"IDAT":
        return SmashOpenGLDecision(False, "SBB GPU path only supports IDAT plans for now; using CPU workers.")
    if not _has_crc_target(plan):
        return SmashOpenGLDecision(False, "SBB pass has no CRC target; using CPU workers.")
    if not _is_indexable(plan):
        return SmashOpenGLDecision(False, "SBB pass is not indexable; using CPU workers.")

    try:
        availability = availability_probe(auto_install=gpu_config.install_missing)
    except TypeError:
        availability = availability_probe()
    if not availability.available:
        return SmashOpenGLDecision(
            False,
            "OpenGL unavailable (%s); using CPU workers." % availability.reason,
            availability,
        )
    if not _kernel_supports_plan(plan):
        return SmashOpenGLDecision(
            False,
            "SBB OpenGL kernel is not implemented for this pass yet; using CPU workers.",
            availability,
        )
    if not plan.crc_trusted:
        return SmashOpenGLDecision(
            True,
            "OpenGL SBB path active with an untrusted CRC hint; CPU validation remains mandatory.",
            availability,
        )
    return SmashOpenGLDecision(True, "OpenGL SBB path active.", availability)


def supports(
    plan: smash_backend.SmashCandidatePlan,
    gpu_config: gpu_runtime.GpuRuntimeConfig,
) -> bool:
    return explain(plan, gpu_config).runnable


def supports_gpu(
    plan: smash_backend.SmashCandidatePlan,
    gpu_config: gpu_runtime.GpuRuntimeConfig,
) -> bool:
    return supports(plan, gpu_config)


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
    uniforms = getattr(shader, "uniforms", None)
    if isinstance(uniforms, dict):
        uniforms[name] = int(value)
        return
    setter = getattr(shader, "set_uniform", None)
    if callable(setter):
        setter(name, int(value))
        return
    raise gpu_opengl.OpenGLComputeUnavailable("OpenGL shader uniform %s cannot be set" % name)


def _uint_buffer_data(values: tuple[int, ...] | list[int]) -> bytes:
    return b"".join(struct.pack("<I", int(value) & 0xFFFFFFFF) for value in values)


def _read_hit_ranks(output_buffer: Any, *, max_hits: int) -> tuple[tuple[int, ...], bool]:
    reader = getattr(output_buffer, "read", None)
    if not callable(reader):
        raise gpu_opengl.OpenGLComputeUnavailable("OpenGL output buffer cannot be read back")
    raw = reader()
    if len(raw) < 4:
        return (), False
    count = struct.unpack_from("<I", raw, 0)[0]
    usable = min(int(count), int(max_hits))
    ranks: list[int] = []
    for index in range(usable):
        offset = 4 * (index + 1)
        if offset + 4 > len(raw):
            break
        ranks.append(struct.unpack_from("<I", raw, offset)[0])
    return tuple(ranks), count > max_hits


def _generated_prefix_bytes(candidate_len: int, base_inner_index: int) -> bytes:
    prefix_len = max(0, int(candidate_len) - 4)
    if prefix_len <= 0:
        return b""
    return (int(base_inner_index) >> 32).to_bytes(prefix_len, "big")


def _generated_low_base(candidate_len: int, base_inner_index: int) -> int:
    if int(candidate_len) <= 4:
        return int(base_inner_index)
    return int(base_inner_index) & OPENGL_HERMES_UINT_MAX


def _generated_low_len(candidate_len: int) -> int:
    return min(4, int(candidate_len))


def replace1_rank_for_cursor(
    plan: smash_backend.SmashCandidatePlan,
    inner_index: int,
    byte_position: int,
) -> int:
    support = _replace1_support_details(plan)
    if support is None:
        raise NotImplementedError("SBB OpenGL kernel only supports direct HermesProbe byte-window passes for now")
    safe_inner = int(inner_index)
    safe_position = int(byte_position)
    if safe_inner < 0 or safe_inner >= support.candidate_count:
        raise IndexError("HermesProbe inner index is outside the OpenGL search space")
    if safe_position < 0 or safe_position >= support.position_count:
        raise IndexError("HermesProbe byte position is outside the OpenGL search space")
    return safe_inner * support.position_count + safe_position


def replace1_cursor_from_rank(
    plan: smash_backend.SmashCandidatePlan,
    rank: int,
) -> OpenGLReplace1Cursor:
    support = _replace1_support_details(plan)
    if support is None:
        raise NotImplementedError("SBB OpenGL kernel only supports direct HermesProbe byte-window passes for now")
    safe_rank = int(rank)
    if safe_rank < 0 or safe_rank >= support.total_candidates:
        raise IndexError("HermesProbe OpenGL rank is outside the search space")
    return OpenGLReplace1Cursor(
        inner_index=safe_rank // support.position_count,
        byte_position=safe_rank % support.position_count,
    )


def _hit_from_replace1_rank(
    plan: smash_backend.SmashCandidatePlan,
    length_plan: smash_backend.SmashLengthPlan,
    edit_window: bruteforce.BruteForceEditWindow,
    rank: int,
) -> smash_backend.SmashCandidateHit | None:
    try:
        cursor = replace1_cursor_from_rank(plan, rank)
    except (IndexError, NotImplementedError):
        return None
    inner_index = cursor.inner_index
    position = cursor.byte_position
    support = _replace1_support_details(plan)
    if support is None:
        return None
    edit_kind = support.edit_kind
    if edit_kind == "remove":
        remove_start = position
        remove_end = position + support.candidate_len
        brute_bytes = bytes.fromhex(edit_window.to_brute)[remove_start:remove_end]
    else:
        brute_bytes = _candidate_bytes_from_inner_index(support, inner_index)
        if brute_bytes is None or len(brute_bytes) != support.candidate_len:
            return None
    candidate_data = bruteforce.twobytes_candidate_data(
        edit_window.to_brute,
        brute_bytes,
        position * 2,
        edit_kind,
    )
    hit_brute_bytes = brute_bytes
    before = edit_window.before
    if plan.bf_mode == "TwoBytes" and plan.data_offset >= 16:
        type_start = int(plan.data_offset) - 8
        length_start = int(plan.data_offset) - 16
        try:
            chunk_type_before_payload = bytes.fromhex(plan.data_hex[type_start : int(plan.data_offset)])
        except ValueError:
            chunk_type_before_payload = b""
        if chunk_type_before_payload == plan.chunk_name:
            before = bytes.fromhex(plan.data_hex[:length_start])
    attempt = bruteforce.prepare_candidate_attempt(
        plan.chunk_name,
        candidate_data.length_bytes,
        candidate_data.data,
        candidate_data.data,
        before,
        edit_window.after,
        brute_length=plan.brute_length,
        brute_crc=plan.brute_crc,
        old_crc=plan.old_crc,
    )
    return smash_backend.SmashCandidateHit(
        outer_index=length_plan.outer_index,
        length=length_plan.length,
        inner_index=inner_index,
        brute_bytes=hit_brute_bytes,
        checksum=attempt.checksum,
        full_new_data=attempt.full_new_data,
        png_bytes=attempt.png_bytes,
        old_crc_match=attempt.old_crc_match,
        edit_kind=edit_kind,
    )


def run_replace1_crc_kernel(
    plan: smash_backend.SmashCandidatePlan,
    gpu_config: gpu_runtime.GpuRuntimeConfig,
    *,
    harness_factory: Callable[..., gpu_opengl.OpenGLComputeHarness] = gpu_opengl.create_compute_harness,
    max_hits: int = OPENGL_REPLACE1_MAX_HITS,
    batch_size: int = OPENGL_REPLACE1_BATCH_SIZE,
    progress_callback: Callable[[int, int], Any] | None = None,
) -> OpenGLReplace1Result:
    support = _replace1_support_details(plan)
    if support is None:
        raise NotImplementedError("SBB OpenGL kernel only supports direct HermesProbe byte-window passes for now")
    length_plan = support.length_plan
    edit_window = support.edit_window
    payload = tuple(bytes.fromhex(edit_window.to_brute))
    total_candidates = support.total_candidates
    if total_candidates <= 0:
        return OpenGLReplace1Result((), 0)

    harness = None
    shader = None
    prefix_buffer = None
    values_buffer = None
    candidate_prefix_buffer = None
    output_buffer = None
    hit_ranks: list[int] = []
    truncated = False
    tested_count = 0
    try:
        harness = harness_factory(auto_install=gpu_config.install_missing)
        shader = harness.compile_compute_shader(OPENGL_REPLACE1_CRC_SHADER)
        prefix_crcs = _prefix_crc_values(payload)
        original_full_crc = prefix_crcs[-1]
        prefix_buffer = harness.buffer(_uint_buffer_data(list(prefix_crcs)))
        value_payload = support.values if not support.generated_values else (0,)
        values_buffer = harness.buffer(_uint_buffer_data(list(value_payload)))
        candidate_prefix_buffer = harness.buffer(_uint_buffer_data([0] * max(1, support.candidate_len)))
        output_buffer = harness.buffer(reserve=(int(max_hits) + 1) * 4)
        _bind_storage_buffer(prefix_buffer, 0)
        _bind_storage_buffer(values_buffer, 1)
        _bind_storage_buffer(output_buffer, 2)
        _bind_storage_buffer(candidate_prefix_buffer, 3)

        target_crc = int.from_bytes(bytes(plan.old_crc), "big")
        safe_batch_size = min(max(1, int(batch_size)), _dynamic_batch_size(support))
        max_rank_tile_inner = max(1, OPENGL_HERMES_UINT_MAX // max(1, support.position_count))
        base_inner_index = 0
        while base_inner_index < support.candidate_count:
            remaining_inner = support.candidate_count - base_inner_index
            if support.generated_values and support.candidate_len > 4:
                low_remaining = (OPENGL_HERMES_UINT_MAX + 1) - _generated_low_base(
                    support.candidate_len,
                    base_inner_index,
                )
            else:
                low_remaining = remaining_inner
            tile_inner_count = max(
                1,
                min(
                    int(remaining_inner),
                    int(low_remaining),
                    int(max_rank_tile_inner),
                ),
            )
            tile_total = int(tile_inner_count) * int(support.position_count)
            candidate_prefix = _generated_prefix_bytes(support.candidate_len, base_inner_index)
            prefix_writer = getattr(candidate_prefix_buffer, "write", None)
            if callable(prefix_writer):
                prefix_writer(_uint_buffer_data(list(candidate_prefix) or [0]))
            base_local_rank = 0
            while base_local_rank < tile_total:
                batch_count = min(safe_batch_size, tile_total - base_local_rank)
                output_buffer.orphan((int(max_hits) + 1) * 4) if hasattr(output_buffer, "orphan") else None
                writer = getattr(output_buffer, "write", None)
                if callable(writer):
                    writer(b"\x00" * ((int(max_hits) + 1) * 4))
                _set_uniform(shader, "payload_len", len(payload))
                _set_uniform(shader, "position_count", support.position_count)
                _set_uniform(shader, "value_count", 0 if support.generated_values else support.candidate_count)
                _set_uniform(shader, "target_crc", target_crc)
                _set_uniform(shader, "base_local_rank", base_local_rank)
                _set_uniform(shader, "batch_count", batch_count)
                _set_uniform(shader, "max_hits", max_hits)
                _set_uniform(shader, "edit_kind", OPENGL_HERMES1_EDIT_KIND_INDEX[support.edit_kind])
                _set_uniform(shader, "candidate_len", support.candidate_len)
                _set_uniform(shader, "candidate_low_len", _generated_low_len(support.candidate_len))
                _set_uniform(shader, "candidate_prefix_len", len(candidate_prefix))
                _set_uniform(
                    shader,
                    "candidate_low_base",
                    _generated_low_base(support.candidate_len, base_inner_index),
                )
                _set_uniform(shader, "generated_values", 1 if support.generated_values else 0)
                _set_uniform(shader, "original_full_crc", original_full_crc)
                group_x = max(1, (int(batch_count) + 127) // 128)
                harness.dispatch(shader, group_x=group_x)
                harness.memory_barrier()
                ranks, batch_truncated = _read_hit_ranks(output_buffer, max_hits=max_hits)
                for tile_rank in ranks:
                    local_inner = int(tile_rank) // int(support.position_count)
                    position = int(tile_rank) % int(support.position_count)
                    global_inner = int(base_inner_index) + local_inner
                    hit_ranks.append(global_inner * int(support.position_count) + position)
                truncated = truncated or batch_truncated
                tested_count += int(batch_count)
                if progress_callback is not None:
                    progress_callback(tested_count, total_candidates)
                if len(hit_ranks) >= max_hits:
                    truncated = True
                    break
                base_local_rank += int(batch_count)
            if len(hit_ranks) >= max_hits:
                break
            base_inner_index += int(tile_inner_count)
    finally:
        _release_resource(output_buffer)
        _release_resource(candidate_prefix_buffer)
        _release_resource(values_buffer)
        _release_resource(prefix_buffer)
        _release_resource(shader)
        if harness is not None:
            harness.release()

    deduped_ranks = tuple(dict.fromkeys(sorted(hit_ranks)))
    hits: list[smash_backend.SmashCandidateHit] = []
    for rank in deduped_ranks[:max_hits]:
        hit = _hit_from_replace1_rank(plan, length_plan, edit_window, rank)
        if hit is not None:
            hits.append(hit)
    return OpenGLReplace1Result(tuple(hits), tested_count or total_candidates, truncated=truncated)


def run_scan(
    _runtime: Any,
    _context: Any,
    _scan_state: Any,
    _old_crc: Any,
    _runtime_plan: Any,
    plan: smash_backend.SmashCandidatePlan,
    _candidate_space_hash: str,
    _progress_resume: dict[str, Any] | None,
    resume_outer_index: int,
    resume_inner_index: int,
    *,
    progress_callback: Callable[[int, int], Any] | None = None,
) -> OpenGLReplace1Result:
    if resume_outer_index or resume_inner_index:
        raise NotImplementedError("SBB OpenGL resume is not implemented for this pass yet")
    return run_replace1_crc_kernel(plan, _runtime.gpu_config, progress_callback=progress_callback)


def run_gpu(*args: Any, **kwargs: Any) -> Any:
    return run_scan(*args, **kwargs)
