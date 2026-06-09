from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from . import gpu_opengl, gpu_runtime, png


ULTIMATE_OPENGL_OFFSET_MAX_RESULTS = 4096
ULTIMATE_OPENGL_OFFSET_BATCH_SIZE = 1_048_576
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
