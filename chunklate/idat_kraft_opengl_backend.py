from __future__ import annotations

from dataclasses import dataclass
import math
import struct
from typing import Any, Callable

from . import gpu_opengl, gpu_runtime


KRAFT_OPENGL_MAX_HITS = 131_072
KRAFT_OPENGL_BATCH_SIZE = 262_144
KRAFT_OPENGL_SHADER = """
#version 430
layout(local_size_x = 128) in;

layout(std430, binding = 0) readonly buffer FlagBuffer {
    uint flag_values[];
};

layout(std430, binding = 1) buffer OutputBuffer {
    uint output_values[];
};

uniform uint start_rank;
uniform uint batch_count;
uniform uint max_results;

void main() {
    uint local_rank = gl_GlobalInvocationID.x;
    if (local_rank >= batch_count) {
        return;
    }
    uint rank = start_rank + local_rank;
    if (flag_values[rank] == 0u) {
        return;
    }
    uint slot = atomicAdd(output_values[0], 1u);
    if (slot < max_results) {
        output_values[slot + 1u] = rank;
    }
}
"""


@dataclass(frozen=True)
class KraftOpenGLDecision:
    runnable: bool
    reason: str
    availability: gpu_opengl.GpuAvailability | None = None


@dataclass(frozen=True)
class KraftOpenGLPlan:
    prefilter_flags: tuple[int, ...]
    start_rank: int = 0
    end_rank: int | None = None

    @property
    def operation_count(self) -> int:
        return len(self.prefilter_flags)


@dataclass(frozen=True)
class KraftOpenGLResult:
    hit_indices: tuple[int, ...]
    tested: int
    shards: int
    status: str
    reason: str


def explain(
    plan: KraftOpenGLPlan,
    config: gpu_runtime.GpuRuntimeConfig,
    *,
    availability_probe: Callable[..., gpu_opengl.GpuAvailability] = gpu_opengl.detect_opengl_compute,
) -> KraftOpenGLDecision:
    if not config.enabled:
        return KraftOpenGLDecision(False, "GPU was not requested.")
    if plan.operation_count <= 0:
        return KraftOpenGLDecision(False, "Kraft GPU prefilter needs at least one operation.")
    availability = availability_probe(auto_install=config.install_missing)
    if not availability.available:
        return KraftOpenGLDecision(False, "OpenGL unavailable: %s" % availability.reason, availability)
    return KraftOpenGLDecision(True, "OpenGL Kraft prefilter active.", availability)


class KraftOpenGLSession:
    def __init__(
        self,
        config: gpu_runtime.GpuRuntimeConfig,
        *,
        harness_factory: Callable[..., gpu_opengl.OpenGLComputeHarness] | None = None,
    ) -> None:
        self.config = config
        self.harness_factory = harness_factory or gpu_opengl.create_compute_harness
        self.harness: gpu_opengl.OpenGLComputeHarness | None = None
        self.shader: Any = None

    def _ensure(self) -> tuple[gpu_opengl.OpenGLComputeHarness, Any]:
        if self.harness is None:
            self.harness = self.harness_factory(auto_install=self.config.install_missing)
        if self.shader is None:
            self.shader = self.harness.compile_compute_shader(KRAFT_OPENGL_SHADER)
        return self.harness, self.shader

    def run(
        self,
        plan: KraftOpenGLPlan,
        *,
        max_hits: int = KRAFT_OPENGL_MAX_HITS,
        shard_size: int = KRAFT_OPENGL_BATCH_SIZE,
    ) -> KraftOpenGLResult:
        if not self.config.enabled:
            return KraftOpenGLResult((), 0, 0, "off", "GPU was not requested.")
        if plan.operation_count <= 0:
            return KraftOpenGLResult((), 0, 0, "off", "No Kraft operations to prefilter.")
        try:
            harness, shader = self._ensure()
            return _run_plan(
                harness,
                shader,
                plan,
                max_hits=max_hits,
                shard_size=shard_size,
            )
        except gpu_opengl.OpenGLComputeUnavailable as exc:
            return KraftOpenGLResult((), 0, 0, "fallback-cpu", exc.reason)
        except Exception as exc:
            return KraftOpenGLResult((), 0, 0, "fallback-cpu", str(exc))

    def close(self) -> None:
        shader = self.shader
        self.shader = None
        release = getattr(shader, "release", None)
        if callable(release):
            try:
                release()
            except Exception:
                pass
        harness = self.harness
        self.harness = None
        if harness is not None:
            harness.release()


def run_gpu(
    plan: KraftOpenGLPlan,
    config: gpu_runtime.GpuRuntimeConfig,
    *,
    harness_factory: Callable[..., gpu_opengl.OpenGLComputeHarness] | None = None,
    max_hits: int = KRAFT_OPENGL_MAX_HITS,
    shard_size: int = KRAFT_OPENGL_BATCH_SIZE,
) -> KraftOpenGLResult:
    session = KraftOpenGLSession(config, harness_factory=harness_factory)
    try:
        return session.run(plan, max_hits=max_hits, shard_size=shard_size)
    finally:
        session.close()


def _set_uniform(shader: Any, name: str, value: int) -> None:
    uniform = shader[name]
    uniform.value = int(value)


def _release_buffer(buffer: Any) -> None:
    release = getattr(buffer, "release", None)
    if callable(release):
        try:
            release()
        except Exception:
            pass


def _run_plan(
    harness: gpu_opengl.OpenGLComputeHarness,
    shader: Any,
    plan: KraftOpenGLPlan,
    *,
    max_hits: int,
    shard_size: int,
) -> KraftOpenGLResult:
    start = max(0, int(plan.start_rank))
    end = plan.operation_count if plan.end_rank is None else min(plan.operation_count, int(plan.end_rank))
    if end <= start:
        return KraftOpenGLResult((), 0, 0, "opengl-active", "No ranks in Kraft GPU shard.")
    flags = struct.pack("<%dI" % plan.operation_count, *(1 if int(flag) else 0 for flag in plan.prefilter_flags))
    flag_buffer = harness.buffer(flags)
    output_buffer = harness.buffer(reserve=(max(1, int(max_hits)) + 1) * 4)
    hit_indices: list[int] = []
    tested = 0
    shards = 0
    try:
        flag_buffer.bind_to_storage_buffer(0)
        output_buffer.bind_to_storage_buffer(1)
        cursor = start
        while cursor < end and len(hit_indices) < int(max_hits):
            batch_count = min(max(1, int(shard_size)), end - cursor)
            output_buffer.write(b"\x00" * ((max(1, int(max_hits)) + 1) * 4))
            _set_uniform(shader, "start_rank", cursor)
            _set_uniform(shader, "batch_count", batch_count)
            _set_uniform(shader, "max_results", max(1, int(max_hits)))
            groups = max(1, math.ceil(batch_count / 128))
            harness.dispatch(shader, group_x=groups)
            harness.memory_barrier()
            data = output_buffer.read()
            words = struct.unpack("<%dI" % (len(data) // 4), data)
            count = min(int(words[0]), max(0, int(max_hits) - len(hit_indices)))
            hit_indices.extend(int(value) for value in words[1 : 1 + count])
            tested += batch_count
            shards += 1
            cursor += batch_count
    finally:
        _release_buffer(flag_buffer)
        _release_buffer(output_buffer)
    return KraftOpenGLResult(
        tuple(hit_indices),
        tested,
        shards,
        "opengl-active",
        "OpenGL Kraft prefilter completed.",
    )
