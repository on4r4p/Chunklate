#!/usr/bin/env python3
import struct
from types import SimpleNamespace
import zlib

from chunklate import (
    bruteforce,
    gpu_opengl,
    gpu_runtime,
    png,
    smash_backend,
    smash_opengl_backend,
    ultimate_opengl_backend,
)


def test_gpu_runtime_config_from_namespace():
    disabled = gpu_runtime.build_gpu_config(SimpleNamespace(GPU=False))
    enabled = gpu_runtime.build_gpu_config({"GPU": True})

    assert disabled == gpu_runtime.GpuRuntimeConfig()
    assert enabled == gpu_runtime.GpuRuntimeConfig(enabled=True)


def _tiny_png_with_idat_stream(stream: bytes) -> bytes:
    ihdr = struct.pack("!IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    return (
        png.PNG_SIGNATURE
        + png.build_png_chunk(b"IHDR", ihdr)
        + png.build_png_chunk(b"IDAT", stream)
        + png.IEND_CHUNK
    )


def test_ultimate_opengl_backend_offset_preflight_supports_idat_plan():
    source = _tiny_png_with_idat_stream(b"x\nabc\rdef\nzzzz")
    plan = ultimate_opengl_backend.build_plan(
        source,
        start_offset=12,
        target_adler=0x12345678,
        super_result=object(),
    )

    assert plan.source_length == len(source)
    assert plan.idat_stream == b"x\nabc\rdef\nzzzz"
    assert plan.start_offset == 12
    assert plan.target_adler == 0x12345678
    assert plan.has_super_result is True

    disabled = ultimate_opengl_backend.explain(plan, gpu_runtime.GpuRuntimeConfig())
    enabled = ultimate_opengl_backend.explain(
        plan,
        gpu_runtime.GpuRuntimeConfig(enabled=True),
        availability_probe=lambda **kwargs: gpu_opengl.GpuAvailability(True, "opengl", "mock ready"),
    )

    assert disabled.runnable is False
    assert disabled.reason == "GPU was not requested."
    assert enabled.runnable is True
    assert "offset preflight active" in enabled.reason


def test_ultimate_opengl_backend_rejects_missing_idat_before_probe():
    plan = ultimate_opengl_backend.build_plan(b"not a png", start_offset=0)

    decision = ultimate_opengl_backend.explain(
        plan,
        gpu_runtime.GpuRuntimeConfig(enabled=True),
        availability_probe=lambda **kwargs: (_ for _ in ()).throw(AssertionError("probe should not run")),
    )

    assert decision.runnable is False
    assert "needs an IDAT stream" in decision.reason


def test_ultimate_opengl_backend_offset_preflight_returns_cr_lf_and_trailer_offsets():
    source = _tiny_png_with_idat_stream(b"x\nabc\rdef\nzzzz")
    plan = ultimate_opengl_backend.build_plan(source, start_offset=5, max_offsets=8)
    calls = []

    class FakeUniform:
        def __init__(self):
            self.value = 0

    class FakeBuffer:
        def __init__(self, context, data=b"", reserve=None):
            self.context = context
            self.data = data if data else b"\x00" * int(reserve or 0)

        def bind_to_storage_buffer(self, binding):
            self.context.bindings[int(binding)] = self

        def orphan(self, size):
            self.data = b"\x00" * int(size)

        def write(self, data):
            self.data = bytes(data)

        def read(self):
            return self.data

        def release(self):
            calls.append(("buffer_release",))

    class FakeShader:
        def __init__(self, context):
            self.context = context
            self.uniforms = {}

        def __getitem__(self, name):
            self.uniforms.setdefault(name, FakeUniform())
            return self.uniforms[name]

        def run(self, group_x, group_y, group_z):
            stream_buffer = self.context.bindings[0]
            output_buffer = self.context.bindings[1]
            stream = [
                value[0]
                for value in struct.iter_unpack("<I", stream_buffer.data)
            ]
            stream_len = self.uniforms["stream_len"].value
            base_offset = self.uniforms["base_offset"].value
            batch_count = self.uniforms["batch_count"].value
            max_results = self.uniforms["max_results"].value
            offsets = []
            for local_index in range(batch_count):
                offset = base_offset + local_index
                if offset >= stream_len:
                    continue
                value = stream[offset] & 0xFF
                if value in (0x0A, 0x0D) or (stream_len >= 4 and offset == stream_len - 4):
                    offsets.append(offset)
            packed = [len(offsets), *offsets[:max_results]]
            output_buffer.data = struct.pack("<%sI" % len(packed), *packed)

        def release(self):
            calls.append(("shader_release",))

    class FakeContext:
        def __init__(self):
            self.bindings = {}

        def compute_shader(self, source):
            assert "ULTIMATE" not in source
            return FakeShader(self)

        def buffer(self, data=None, *, reserve=None):
            return FakeBuffer(self, data or b"", reserve)

        def memory_barrier(self):
            calls.append(("barrier",))

        def release(self):
            calls.append(("context_release",))

    result = ultimate_opengl_backend.run_gpu(
        plan,
        gpu_runtime.GpuRuntimeConfig(enabled=True, install_missing=False),
        harness_factory=lambda *, auto_install: gpu_opengl.OpenGLComputeHarness(FakeContext()),
    )

    assert set(result.offsets) == {1, 5, 9, 10}
    assert result.tested == len(plan.idat_stream)
    assert result.truncated is False
    assert ("barrier",) in calls
    assert ("context_release",) in calls


def test_opengl_probe_handles_missing_moderngl():
    availability = gpu_opengl.detect_opengl_compute(
        import_module=lambda name: (_ for _ in ()).throw(ModuleNotFoundError(name))
    )

    assert availability.available is False
    assert availability.backend == "opengl"
    assert "moderngl" in availability.reason


def test_opengl_probe_reports_failed_moderngl_install():
    availability = gpu_opengl.detect_opengl_compute(
        import_module=lambda name: (_ for _ in ()).throw(ModuleNotFoundError(name)),
        auto_install=True,
        installer=lambda requirement: gpu_opengl.GpuInstallResult(False, "pip failed"),
    )

    assert availability.available is False
    assert "automatic install failed" in availability.reason
    assert "pip failed" in availability.reason


def test_opengl_probe_retries_after_moderngl_install():
    calls = {"imports": 0}

    class FakeModerngl:
        @staticmethod
        def create_standalone_context(require):
            class FakeContext:
                version_code = 430

                @staticmethod
                def release():
                    pass

            return FakeContext()

    def import_module(name):
        calls["imports"] += 1
        if calls["imports"] == 1:
            raise ModuleNotFoundError(name)
        return FakeModerngl

    availability = gpu_opengl.detect_opengl_compute(
        import_module=import_module,
        auto_install=True,
        installer=lambda requirement: gpu_opengl.GpuInstallResult(True, "installed"),
    )

    assert availability.available is True
    assert calls["imports"] == 2


def test_opengl_harness_smoke_test_dispatches_compute_shader():
    calls = []

    class FakeBuffer:
        def __init__(self):
            self.data = b"\x00\x00\x00\x00"

        def bind_to_storage_buffer(self, binding):
            calls.append(("bind", binding))

        def read(self):
            calls.append(("read",))
            return self.data

        def release(self):
            calls.append(("buffer_release",))

    class FakeShader:
        def __init__(self, context):
            self.context = context

        def run(self, group_x, group_y, group_z):
            calls.append(("run", group_x, group_y, group_z))
            self.context.output.data = smash_opengl_backend.OPENGL_SMOKE_MARKER.to_bytes(4, "little")

        def release(self):
            calls.append(("shader_release",))

    class FakeContext:
        def __init__(self):
            self.output = FakeBuffer()

        def compute_shader(self, source):
            calls.append(("compile", "#version 430" in source))
            return FakeShader(self)

        def buffer(self, data=None, *, reserve=None):
            calls.append(("buffer", data, reserve))
            return self.output

        def memory_barrier(self):
            calls.append(("barrier",))

        def release(self):
            calls.append(("context_release",))

    def harness_factory(*, auto_install):
        calls.append(("factory", auto_install))
        return gpu_opengl.OpenGLComputeHarness(FakeContext())

    availability = smash_opengl_backend.run_harness_smoke_test(
        gpu_runtime.GpuRuntimeConfig(enabled=True, install_missing=False),
        harness_factory=harness_factory,
    )

    assert availability.available is True
    assert availability.reason == "OpenGL compute harness ready"
    assert ("factory", False) in calls
    assert ("compile", True) in calls
    assert ("bind", 0) in calls
    assert ("run", 1, 1, 1) in calls
    assert ("read",) in calls
    assert ("buffer_release",) in calls
    assert ("shader_release",) in calls
    assert ("context_release",) in calls


def test_opengl_harness_smoke_test_reports_unexpected_data():
    class BadBuffer:
        def bind_to_storage_buffer(self, _binding):
            pass

        def read(self):
            return b"\x00\x00\x00\x00"

    class BadShader:
        def run(self, *_groups):
            pass

    class BadContext:
        def compute_shader(self, _source):
            return BadShader()

        def buffer(self, data=None, *, reserve=None):
            return BadBuffer()

    availability = smash_opengl_backend.run_harness_smoke_test(
        gpu_runtime.GpuRuntimeConfig(enabled=True),
        harness_factory=lambda **_kwargs: gpu_opengl.OpenGLComputeHarness(BadContext()),
    )

    assert availability.available is False
    assert "unexpected data" in availability.reason


def test_smash_opengl_backend_passes_auto_install_flag_to_probe():
    seen = []

    def probe(*, auto_install):
        seen.append(auto_install)
        return gpu_opengl.GpuAvailability(False, "opengl", "no driver")

    smash_opengl_backend.explain(
        _plan(),
        gpu_runtime.GpuRuntimeConfig(enabled=True, install_missing=False),
        availability_probe=probe,
    )

    assert seen == [False]


def _plan(**updates):
    length_plan = smash_backend.SmashLengthPlan(
        outer_index=0,
        length=1,
        iter_nbr=0,
        max_iter=1,
        len_iter=1,
        chunk_format=("B",),
        chunk_data=((0,),),
        color_type="color",
    )
    values = {
        "chunk_name": b"IDAT",
        "chunk_length": 1,
        "data_offset": 8,
        "data_hex": "00000001494441540000000000000000",
        "edit_mode": "Replace",
        "bf_mode": "TwoBytes",
        "brute_level": 0,
        "brute_crc": True,
        "brute_length": True,
        "old_crc": b"\x00\x00\x00\x00",
        "struct_indexes": (),
        "candidate_space_hash": "hash",
        "crc_trusted": True,
        "lengths": (length_plan,),
    }
    values.update(updates)
    return smash_backend.SmashCandidatePlan(**values)


def test_smash_opengl_backend_rejects_missing_crc_target_before_probe():
    called = False

    def probe():
        nonlocal called
        called = True
        return gpu_opengl.GpuAvailability(True, "opengl", "available")

    decision = smash_opengl_backend.explain(
        _plan(old_crc=False, crc_trusted=False),
        gpu_runtime.GpuRuntimeConfig(enabled=True),
        availability_probe=probe,
    )

    assert decision.runnable is False
    assert "no CRC target" in decision.reason
    assert called is False


def test_smash_opengl_backend_allows_untrusted_crc_hint():
    decision = smash_opengl_backend.explain(
        _plan(old_crc=b"\x00\x00\x00\x00", crc_trusted=False),
        gpu_runtime.GpuRuntimeConfig(enabled=True),
        availability_probe=lambda: gpu_opengl.GpuAvailability(True, "opengl", "available"),
    )

    assert decision.runnable is True
    assert "untrusted CRC hint" in decision.reason


def test_smash_opengl_backend_handles_opengl_unavailable():
    decision = smash_opengl_backend.explain(
        _plan(),
        gpu_runtime.GpuRuntimeConfig(enabled=True),
        availability_probe=lambda: gpu_opengl.GpuAvailability(False, "opengl", "no driver"),
    )

    assert decision.runnable is False
    assert "OpenGL unavailable" in decision.reason
    assert "no driver" in decision.reason


def test_smash_opengl_backend_accepts_hermes_replace1_plan_when_opengl_available():
    decision = smash_opengl_backend.explain(
        _plan(),
        gpu_runtime.GpuRuntimeConfig(enabled=True),
        availability_probe=lambda **_kwargs: gpu_opengl.GpuAvailability(True, "opengl", "available"),
    )

    assert decision.runnable is True
    assert decision.reason == "OpenGL SBB path active."


def test_smash_opengl_backend_accepts_insert_remove_level0_after_opengl_probe():
    availability = lambda **_kwargs: gpu_opengl.GpuAvailability(True, "opengl", "available")

    insert = smash_opengl_backend.explain(
        _plan(edit_mode="Insert"),
        gpu_runtime.GpuRuntimeConfig(enabled=True),
        availability_probe=availability,
    )
    remove = smash_opengl_backend.explain(
        _plan(edit_mode="Remove", chunk_length=2, data_hex="000000024944415400000000000000000000"),
        gpu_runtime.GpuRuntimeConfig(enabled=True),
        availability_probe=availability,
    )

    assert insert.runnable is True
    assert remove.runnable is True


def test_smash_opengl_backend_accepts_level1_after_opengl_probe():
    level_one = smash_opengl_backend.explain(
        _plan(brute_level=1),
        gpu_runtime.GpuRuntimeConfig(enabled=True),
        availability_probe=lambda **_kwargs: gpu_opengl.GpuAvailability(True, "opengl", "available"),
    )

    assert level_one.runnable is True


def test_smash_opengl_backend_accepts_indexable_hermes_replace2_plan():
    decision = smash_opengl_backend.explain(
        _plan_for_payload(
            payload=b"\x10\x20\x30",
            repaired_payload=b"\xab\xcd\x30",
            values=None,
            candidate_len=2,
        ),
        gpu_runtime.GpuRuntimeConfig(enabled=True),
        availability_probe=lambda **_kwargs: gpu_opengl.GpuAvailability(True, "opengl", "available"),
    )

    assert decision.runnable is True


def test_smash_opengl_backend_accepts_single_position_replace4_plan():
    decision = smash_opengl_backend.explain(
        _plan_for_payload(
            payload=b"\x10\x20\x30\x40",
            repaired_payload=b"\x01\x02\x03\x04",
            values=None,
            candidate_len=4,
        ),
        gpu_runtime.GpuRuntimeConfig(enabled=True),
        availability_probe=lambda **_kwargs: gpu_opengl.GpuAvailability(True, "opengl", "available"),
    )

    assert decision.runnable is True


def test_smash_opengl_backend_accepts_generated_window_beyond_four_bytes():
    decision = smash_opengl_backend.explain(
        _plan_for_payload(
            payload=b"\x10\x20\x30\x40\x50",
            repaired_payload=b"\x01\x02\x03\x04\x05",
            values=None,
            candidate_len=5,
        ),
        gpu_runtime.GpuRuntimeConfig(enabled=True),
        availability_probe=lambda **_kwargs: gpu_opengl.GpuAvailability(True, "opengl", "available"),
    )

    assert decision.runnable is True


def test_smash_opengl_backend_accepts_tiled_rank_space_for_replace4_plan():
    decision = smash_opengl_backend.explain(
        _plan_for_payload(
            payload=b"\x10\x20\x30\x40\x50",
            repaired_payload=b"\x01\x02\x03\x04\x50",
            values=None,
            candidate_len=4,
        ),
        gpu_runtime.GpuRuntimeConfig(enabled=True),
        availability_probe=lambda **_kwargs: gpu_opengl.GpuAvailability(True, "opengl", "available"),
    )

    assert decision.runnable is True


def test_replace1_rank_order_matches_cpu_inner_then_position():
    plan = _plan_for_payload(payload=b"\x10\x20\x30", repaired_payload=b"\x10\x42\x30", values=(0x41, 0x42))

    cursors = [
        smash_opengl_backend.replace1_cursor_from_rank(plan, rank)
        for rank in range(6)
    ]
    assert [(cursor.inner_index, cursor.byte_position) for cursor in cursors] == [
        (0, 0),
        (0, 1),
        (0, 2),
        (1, 0),
        (1, 1),
        (1, 2),
    ]
    assert smash_opengl_backend.replace1_rank_for_cursor(plan, 1, 2) == 5


def test_replace_rank_cursor_supports_python_int_space_above_uint32():
    plan = _plan_for_payload(
        payload=b"\x10\x20\x30\x40\x50",
        repaired_payload=b"\x01\x02\x03\x04\x50",
        values=None,
        candidate_len=4,
    )
    rank = smash_opengl_backend.replace1_rank_for_cursor(plan, 0xFFFFFFFF, 1)
    cursor = smash_opengl_backend.replace1_cursor_from_rank(plan, rank)

    assert rank > 2**32
    assert cursor.inner_index == 0xFFFFFFFF
    assert cursor.byte_position == 1


def test_crc32_combine_matches_zlib_crc32_append():
    first = b"IDAT" + bytes(range(32))
    second = b"tail-data"

    combined = smash_opengl_backend.crc32_combine(
        zlib.crc32(first) & 0xFFFFFFFF,
        zlib.crc32(second) & 0xFFFFFFFF,
        len(second),
    )

    assert combined == zlib.crc32(first + second) & 0xFFFFFFFF


def test_patched_candidate_crc_matches_full_crc_for_hermes_modes():
    payload = tuple(b"\x10\x20\x30\x40")
    prefix_crcs = smash_opengl_backend._prefix_crc_values(payload)
    original_full_crc = prefix_crcs[-1]

    replace_crc = smash_opengl_backend._patched_candidate_crc(
        prefix_crcs=prefix_crcs,
        original_full_crc=original_full_crc,
        payload_len=len(payload),
        position=1,
        candidate_bytes=b"\x99",
        edit_kind="replace",
    )
    insert_crc = smash_opengl_backend._patched_candidate_crc(
        prefix_crcs=prefix_crcs,
        original_full_crc=original_full_crc,
        payload_len=len(payload),
        position=1,
        candidate_bytes=b"\x99",
        edit_kind="insert",
    )
    remove_crc = smash_opengl_backend._patched_candidate_crc(
        prefix_crcs=prefix_crcs,
        original_full_crc=original_full_crc,
        payload_len=len(payload),
        position=1,
        candidate_bytes=b"\x20",
        edit_kind="remove",
    )

    assert replace_crc == zlib.crc32(b"IDAT" + b"\x10\x99\x30\x40") & 0xFFFFFFFF
    assert insert_crc == zlib.crc32(b"IDAT" + b"\x10\x99\x20\x30\x40") & 0xFFFFFFFF
    assert remove_crc == zlib.crc32(b"IDAT" + b"\x10\x30\x40") & 0xFFFFFFFF


def test_replace1_kernel_result_reconstructs_cpu_hit_from_gpu_rank():
    calls = []

    class FakeUniform:
        def __init__(self):
            self.value = 0

    class FakeShader:
        def __init__(self, harness):
            self.harness = harness
            self.uniforms = {}

        def __getitem__(self, name):
            return self.uniforms.setdefault(name, FakeUniform())

        def run(self, group_x, group_y, group_z):
            calls.append(("run", group_x, group_y, group_z))
            output = self.harness.storage_buffers[2]
            output.data = struct.pack("<II", 1, 3) + b"\x00" * 252

        def release(self):
            calls.append(("shader_release",))

    class FakeBuffer:
        def __init__(self, harness, data=b""):
            self.harness = harness
            self.data = data

        def bind_to_storage_buffer(self, binding):
            self.harness.storage_buffers[binding] = self

        def write(self, data):
            self.data = data

        def read(self):
            return self.data

        def release(self):
            calls.append(("buffer_release",))

    class FakeHarness:
        def __init__(self):
            self.storage_buffers = {}

        def compile_compute_shader(self, source):
            assert "crc32_update" in source
            return FakeShader(self)

        def buffer(self, data=None, *, reserve=None):
            if data is None:
                data = b"\x00" * int(reserve)
            return FakeBuffer(self, data)

        def dispatch(self, shader, *, group_x, group_y=1, group_z=1):
            shader.run(group_x, group_y, group_z)

        def memory_barrier(self):
            calls.append(("barrier",))

        def release(self):
            calls.append(("harness_release",))

    plan = _plan_for_payload(payload=b"\x10\x20", repaired_payload=b"\x10\x42", values=(0, 0x42))
    result = smash_opengl_backend.run_replace1_crc_kernel(
        plan,
        gpu_runtime.GpuRuntimeConfig(enabled=True),
        harness_factory=lambda **_kwargs: FakeHarness(),
    )

    assert result.tested == 4
    assert len(result.hits) == 1
    hit = result.hits[0]
    assert hit.inner_index == 1
    assert hit.brute_bytes == b"\x42"
    assert hit.edit_kind == "replace"
    assert hit.old_crc_match is True
    assert hit.full_new_data == b"\x00\x00\x00\x02IDAT\x10\x42" + plan.old_crc
    assert ("barrier",) in calls


def test_replace1_kernel_reconstructs_real_chunk_from_payload_offset():
    payload = b"\x10\xff\x30"
    repaired_payload = b"\x10\x20\x30"
    before = png.PNG_SIGNATURE
    after = png.IEND_CHUNK
    stored_crc = bruteforce.chunk_crc(b"IDAT", repaired_payload)
    data_hex = (
        before.hex()
        + len(payload).to_bytes(4, "big").hex()
        + b"IDAT".hex()
        + payload.hex()
        + stored_crc.hex()
        + after.hex()
    )
    length_plan = smash_backend.SmashLengthPlan(
        outer_index=0,
        length=2,
        iter_nbr=0,
        max_iter=256,
        len_iter=3,
        chunk_format=("B",),
        chunk_data=(tuple(range(256)),),
        color_type="color",
    )
    plan = smash_backend.SmashCandidatePlan(
        chunk_name=b"IDAT",
        chunk_length=len(payload),
        data_offset=len(before.hex()) + 16,
        data_hex=data_hex,
        edit_mode="Replace",
        bf_mode="TwoBytes",
        brute_level=0,
        brute_crc=True,
        brute_length=True,
        old_crc=stored_crc,
        struct_indexes=(),
        candidate_space_hash="hash",
        crc_trusted=True,
        lengths=(length_plan,),
    )

    rank = smash_opengl_backend.replace1_rank_for_cursor(plan, 0x20, 1)
    result = smash_opengl_backend.run_replace1_crc_kernel(
        plan,
        gpu_runtime.GpuRuntimeConfig(enabled=True),
        harness_factory=lambda **_kwargs: _FakeRankHarness((rank,)),
    )

    assert len(result.hits) == 1
    hit = result.hits[0]
    assert hit.png_bytes == before + png.build_png_chunk(b"IDAT", repaired_payload) + after


def test_replace1_kernel_sorts_gpu_hits_by_cpu_rank_order():
    class FakeUniform:
        value = 0

    class FakeShader:
        def __init__(self, harness):
            self.harness = harness
            self.uniforms = {}

        def __getitem__(self, name):
            uniform = FakeUniform()
            self.uniforms[name] = uniform
            return uniform

        def run(self, *_groups):
            output = self.harness.storage_buffers[2]
            output.data = struct.pack("<III", 2, 3, 1) + b"\x00" * 248

        def release(self):
            pass

    class FakeBuffer:
        def __init__(self, harness, data=b""):
            self.harness = harness
            self.data = data

        def bind_to_storage_buffer(self, binding):
            self.harness.storage_buffers[binding] = self

        def write(self, data):
            self.data = data

        def read(self):
            return self.data

        def release(self):
            pass

    class FakeHarness:
        def __init__(self):
            self.storage_buffers = {}

        def compile_compute_shader(self, _source):
            return FakeShader(self)

        def buffer(self, data=None, *, reserve=None):
            return FakeBuffer(self, data or (b"\x00" * int(reserve)))

        def dispatch(self, shader, *, group_x, group_y=1, group_z=1):
            shader.run(group_x, group_y, group_z)

        def memory_barrier(self):
            pass

        def release(self):
            pass

    plan = _plan_for_payload(payload=b"\x10\x20", repaired_payload=b"\x10\x42", values=(0x42, 0x42))
    result = smash_opengl_backend.run_replace1_crc_kernel(
        plan,
        gpu_runtime.GpuRuntimeConfig(enabled=True),
        harness_factory=lambda **_kwargs: FakeHarness(),
    )

    assert [hit.inner_index for hit in result.hits] == [0, 1]
    assert [hit.full_new_data for hit in result.hits] == [
        b"\x00\x00\x00\x02IDAT\x10\x42" + plan.old_crc,
        b"\x00\x00\x00\x02IDAT\x10\x42" + plan.old_crc,
    ]


def test_replace1_kernel_reports_progress_per_batch():
    progress = []
    plan = _plan_for_payload(payload=b"\x10\x20", repaired_payload=b"\x10\x42", values=(0x41, 0x42))

    result = smash_opengl_backend.run_replace1_crc_kernel(
        plan,
        gpu_runtime.GpuRuntimeConfig(enabled=True),
        harness_factory=lambda **_kwargs: _FakeRankHarness(()),
        batch_size=2,
        progress_callback=lambda tested, total: progress.append((tested, total)),
    )

    assert result.tested == 4
    assert result.hits == ()
    assert progress == [(2, 4), (4, 4)]


def test_insert1_kernel_result_reconstructs_cpu_hit_from_gpu_rank():
    plan = _plan_for_payload(
        payload=b"\x10\x20",
        repaired_payload=b"\x10\x42\x20",
        values=(0, 0x42),
        edit_mode="Insert",
    )
    result = smash_opengl_backend.run_replace1_crc_kernel(
        plan,
        gpu_runtime.GpuRuntimeConfig(enabled=True),
        harness_factory=lambda **_kwargs: _FakeRankHarness((3,)),
    )

    assert result.tested == 4
    assert len(result.hits) == 1
    hit = result.hits[0]
    assert hit.inner_index == 1
    assert hit.brute_bytes == b"\x42"
    assert hit.edit_kind == "insert"
    assert hit.old_crc_match is True
    assert hit.full_new_data == b"\x00\x00\x00\x03IDAT\x10\x42\x20" + plan.old_crc


def test_remove1_kernel_result_reconstructs_cpu_hit_from_gpu_rank():
    plan = _plan_for_payload(
        payload=b"\x10\x99\x20",
        repaired_payload=b"\x10\x20",
        values=(0,),
        edit_mode="Remove",
    )
    result = smash_opengl_backend.run_replace1_crc_kernel(
        plan,
        gpu_runtime.GpuRuntimeConfig(enabled=True),
        harness_factory=lambda **_kwargs: _FakeRankHarness((1,)),
    )

    assert result.tested == 3
    assert len(result.hits) == 1
    hit = result.hits[0]
    assert hit.inner_index == 0
    assert hit.brute_bytes == b"\x99"
    assert hit.edit_kind == "remove"
    assert hit.old_crc_match is True
    assert hit.full_new_data == b"\x00\x00\x00\x02IDAT\x10\x20" + plan.old_crc


def test_replace2_kernel_result_reconstructs_cpu_hit_from_gpu_rank():
    plan = _plan_for_payload(
        payload=b"\x10\x20\x30",
        repaired_payload=b"\xab\xcd\x30",
        values=None,
        candidate_len=2,
    )
    inner_index = 0xABCD
    rank = smash_opengl_backend.replace1_rank_for_cursor(plan, inner_index, 0)
    result = smash_opengl_backend.run_replace1_crc_kernel(
        plan,
        gpu_runtime.GpuRuntimeConfig(enabled=True),
        harness_factory=lambda **_kwargs: _FakeRankHarness((rank,)),
    )

    support = smash_opengl_backend._replace1_support_details(plan)
    assert support is not None
    assert result.tested == support.total_candidates
    assert result.truncated is False
    assert len(result.hits) == 1
    hit = result.hits[0]
    assert hit.inner_index == inner_index
    assert hit.brute_bytes == b"\xab\xcd"
    assert hit.edit_kind == "replace"
    assert hit.old_crc_match is True
    assert hit.full_new_data == b"\x00\x00\x00\x03IDAT\xab\xcd\x30" + plan.old_crc


def test_insert2_kernel_result_reconstructs_cpu_hit_from_gpu_rank():
    plan = _plan_for_payload(
        payload=b"\x10\x20\x30",
        repaired_payload=b"\x10\xab\xcd\x20\x30",
        values=None,
        edit_mode="Insert",
        candidate_len=2,
    )
    inner_index = 0xABCD
    rank = smash_opengl_backend.replace1_rank_for_cursor(plan, inner_index, 1)
    result = smash_opengl_backend.run_replace1_crc_kernel(
        plan,
        gpu_runtime.GpuRuntimeConfig(enabled=True),
        harness_factory=lambda **_kwargs: _FakeRankHarness((rank,)),
    )

    support = smash_opengl_backend._replace1_support_details(plan)
    assert support is not None
    assert result.tested == support.total_candidates
    assert result.truncated is False
    assert len(result.hits) == 1
    hit = result.hits[0]
    assert hit.inner_index == inner_index
    assert hit.brute_bytes == b"\xab\xcd"
    assert hit.edit_kind == "insert"
    assert hit.old_crc_match is True
    assert hit.full_new_data == b"\x00\x00\x00\x05IDAT\x10\xab\xcd\x20\x30" + plan.old_crc


def test_remove2_kernel_result_reconstructs_cpu_hit_from_gpu_rank():
    plan = _plan_for_payload(
        payload=b"\x10\xab\xcd\x20",
        repaired_payload=b"\x10\x20",
        values=None,
        edit_mode="Remove",
        candidate_len=2,
    )
    rank = smash_opengl_backend.replace1_rank_for_cursor(plan, 0, 1)
    result = smash_opengl_backend.run_replace1_crc_kernel(
        plan,
        gpu_runtime.GpuRuntimeConfig(enabled=True),
        harness_factory=lambda **_kwargs: _FakeRankHarness((rank,)),
    )

    assert result.tested == 3
    assert len(result.hits) == 1
    hit = result.hits[0]
    assert hit.inner_index == 0
    assert hit.brute_bytes == b"\xab\xcd"
    assert hit.edit_kind == "remove"
    assert hit.old_crc_match is True
    assert hit.full_new_data == b"\x00\x00\x00\x02IDAT\x10\x20" + plan.old_crc


def test_replace4_kernel_result_reconstructs_single_position_cpu_hit():
    plan = _plan_for_payload(
        payload=b"\x10\x20\x30\x40",
        repaired_payload=b"\x01\x02\x03\x04",
        values=None,
        candidate_len=4,
    )
    inner_index = 0x01020304
    rank = smash_opengl_backend.replace1_rank_for_cursor(plan, inner_index, 0)
    result = smash_opengl_backend.run_replace1_crc_kernel(
        plan,
        gpu_runtime.GpuRuntimeConfig(enabled=True),
        harness_factory=lambda **_kwargs: _FakeRankHarness((rank,)),
    )

    support = smash_opengl_backend._replace1_support_details(plan)
    assert support is not None
    assert result.tested == support.total_candidates
    assert result.truncated is False
    assert len(result.hits) == 1
    hit = result.hits[0]
    assert hit.inner_index == inner_index
    assert hit.brute_bytes == b"\x01\x02\x03\x04"
    assert hit.edit_kind == "replace"
    assert hit.old_crc_match is True


class _FakeUniform:
    def __init__(self):
        self.value = 0


class _FakeRankShader:
    def __init__(self, harness):
        self.harness = harness
        self.uniforms = {}

    def __getitem__(self, name):
        return self.uniforms.setdefault(name, _FakeUniform())

    def run(self, *_groups):
        output = self.harness.storage_buffers[2]
        output.data = struct.pack("<I", len(self.harness.ranks)) + b"".join(
            struct.pack("<I", rank) for rank in self.harness.ranks
        ) + b"\x00" * 256

    def release(self):
        pass


class _FakeRankBuffer:
    def __init__(self, harness, data=b""):
        self.harness = harness
        self.data = data

    def bind_to_storage_buffer(self, binding):
        self.harness.storage_buffers[binding] = self

    def write(self, data):
        self.data = data

    def read(self):
        return self.data

    def release(self):
        pass


class _FakeRankHarness:
    def __init__(self, ranks):
        self.ranks = tuple(ranks)
        self.storage_buffers = {}

    def compile_compute_shader(self, _source):
        return _FakeRankShader(self)

    def buffer(self, data=None, *, reserve=None):
        return _FakeRankBuffer(self, data or (b"\x00" * int(reserve)))

    def dispatch(self, shader, *, group_x, group_y=1, group_z=1):
        shader.run(group_x, group_y, group_z)

    def memory_barrier(self):
        pass

    def release(self):
        pass


def _plan_for_payload(
    payload: bytes,
    repaired_payload: bytes,
    values=(0,),
    edit_mode="Replace",
    candidate_len=1,
):
    old_crc = bruteforce.chunk_crc(b"IDAT", repaired_payload)
    before = b"\x89PNG\r\n\x1a\n"
    after = b"tail"
    data_hex = before.hex() + payload.hex() + b"\x00\x00\x00\x00".hex() + after.hex()
    if values is None:
        chunk_format = tuple("B" for _ in range(candidate_len))
        chunk_data = tuple(tuple(range(256)) for _ in range(candidate_len))
        max_iter = 256**candidate_len
    else:
        chunk_format = ("B",)
        chunk_data = (tuple(values),)
        max_iter = len(values)
    length_plan = smash_backend.SmashLengthPlan(
        outer_index=0,
        length=int(candidate_len) * 2,
        iter_nbr=0,
        max_iter=max_iter,
        len_iter=len(str(max_iter)),
        chunk_format=chunk_format,
        chunk_data=chunk_data,
        color_type="color",
    )
    return smash_backend.SmashCandidatePlan(
        chunk_name=b"IDAT",
        chunk_length=len(payload),
        data_offset=len(before.hex()),
        data_hex=data_hex,
        edit_mode=edit_mode,
        bf_mode="TwoBytes",
        brute_level=0,
        brute_crc=True,
        brute_length=True,
        old_crc=old_crc,
        struct_indexes=(),
        candidate_space_hash="hash",
        crc_trusted=True,
        lengths=(length_plan,),
    )
