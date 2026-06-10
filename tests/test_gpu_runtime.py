#!/usr/bin/env python3
import struct
from types import SimpleNamespace
import zlib

from chunklate import (
    bruteforce,
    gpu_opengl,
    gpu_runtime,
    idat,
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


def _rgb_png_with_idat_stream(width: int, height: int, stream: bytes) -> bytes:
    ihdr = struct.pack("!IIBBBBB", width, height, 8, 2, 0, 0, 0)
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


def _ultimate_gpu_stream_analysis(stream, *, height=1, expected_size=None):
    expected = 4 * height if expected_size is None else expected_size
    return ultimate_opengl_backend.analyze_zlib_stream_for_gpu(
        stream,
        scanline_size=4,
        height=height,
        expected_size=expected,
        target_adler=zlib.adler32(b"\x00abc") & 0xFFFFFFFF,
    )


def test_ultimate_opengl_zlib_analysis_matches_idat_statuses():
    filtered = b"\x00abc"
    complete_stream = zlib.compress(filtered)
    complete = _ultimate_gpu_stream_analysis(complete_stream)
    complete_cpu = idat.analyze_idat_stream(_rgb_png_with_idat_stream(1, 1, complete_stream))
    assert complete.status == complete_cpu.status == "complete"
    assert complete.complete is True
    assert complete.usable_scanlines == complete_cpu.usable_scanlines == 1
    assert complete.computed_adler == complete_cpu.computed_adler
    assert "terminal" in complete.proof_flags

    bad_adler_stream = bytearray(complete_stream)
    bad_adler_stream[-1] ^= 0xFF
    bad_adler = _ultimate_gpu_stream_analysis(bytes(bad_adler_stream))
    bad_adler_cpu = idat.analyze_idat_stream(_rgb_png_with_idat_stream(1, 1, bytes(bad_adler_stream)))
    assert bad_adler.status == bad_adler_cpu.status == "bad_adler"
    assert bad_adler.usable_scanlines == bad_adler_cpu.usable_scanlines == 1
    assert bad_adler.computed_adler == bad_adler_cpu.computed_adler

    partial = ultimate_opengl_backend.analyze_zlib_stream_for_gpu(
        complete_stream,
        scanline_size=4,
        height=2,
        expected_size=8,
    )
    assert partial.status == "partial"
    assert partial.usable_scanlines == 1

    corrupt = _ultimate_gpu_stream_analysis(b"\x78\x9c\xff\xff")
    assert corrupt.status == "corrupt_deflate"
    assert corrupt.error_offset is not None

    bad_header = _ultimate_gpu_stream_analysis(b"\x00\x00abc")
    assert bad_header.status == "bad_zlib_header"

    trailing = _ultimate_gpu_stream_analysis(complete_stream + b"tail")
    assert trailing.status == "trailing_data"
    assert trailing.usable_scanlines == 1


def test_ultimate_opengl_analysis_plan_replays_ranked_operations_and_nominates_terminal():
    filtered = b"\x00abc"
    good_stream = zlib.compress(filtered)
    corrupt_stream = bytearray(good_stream)
    corrupt_stream[-1] ^= 0xFF
    invalid_operation = SimpleNamespace(
        kind="invalid",
        stream_offset=0,
        old_bytes=b"not-there",
        new_bytes=b"",
    )
    repair_operation = SimpleNamespace(
        kind="restore-adler-byte",
        stream_offset=len(corrupt_stream) - 1,
        old_bytes=bytes((corrupt_stream[-1],)),
        new_bytes=bytes((good_stream[-1],)),
    )
    plan = ultimate_opengl_backend.build_analysis_plan(
        bytes(corrupt_stream),
        width=1,
        height=1,
        bit_depth=8,
        color_type=2,
        scanline_size=4,
        expected_size=4,
        operation_pool=(invalid_operation, repair_operation),
        pool_index=1,
        depth=1,
        start_rank=0,
        end_rank=2,
        target_adler=zlib.adler32(filtered) & 0xFFFFFFFF,
    )
    decision = ultimate_opengl_backend.explain_analysis(
        plan,
        gpu_runtime.GpuRuntimeConfig(enabled=True),
        availability_probe=lambda **kwargs: gpu_opengl.GpuAvailability(True, "opengl", "mock ready"),
    )
    result = ultimate_opengl_backend.run_analysis_gpu(
        plan,
        gpu_runtime.GpuRuntimeConfig(enabled=True, install_missing=False),
    )

    assert decision.runnable is True
    assert result.pruned == 1
    assert result.tested == 1
    assert len(result.hits) == 1
    hit = result.hits[0]
    assert hit.pool_index == 1
    assert hit.rank == 1
    assert hit.operation_indices == (1,)
    assert hit.status == "complete"
    assert hit.adler_status == "adler_match"
    assert "terminal" in hit.proof_flags


def test_ultimate_opengl_analysis_shader_dispatch_reads_back_hits():
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
            operation_buffer = self.context.bindings[1]
            output_buffer = self.context.bindings[2]
            stream = bytes(value[0] & 0xFF for value in struct.iter_unpack("<I", stream_buffer.data))
            operations = [value[0] for value in struct.iter_unpack("<I", operation_buffer.data)]
            base_rank = self.uniforms["base_rank_low"].value
            batch_count = self.uniforms["batch_count"].value
            target_adler = self.uniforms["target_adler"].value
            hit_words = []
            tested = 0
            pruned = 0
            for local_index in range(batch_count):
                op_index = base_rank + local_index
                base = op_index * ultimate_opengl_backend.ULTIMATE_OPENGL_ANALYSIS_OP_WORDS
                offset, old_len, new_len = operations[base : base + 3]
                old = bytes(operations[base + 3 + index] & 0xFF for index in range(old_len))
                new = bytes(operations[base + 7 + index] & 0xFF for index in range(new_len))
                if offset + len(old) > len(stream) or stream[offset : offset + len(old)] != old:
                    pruned += 1
                    continue
                tested += 1
                candidate = stream[:offset] + new + stream[offset + len(old) :]
                btype = ((candidate[2] >> 1) & 3) if len(candidate) > 2 else 3
                if btype == 0:
                    analysis = ultimate_opengl_backend.analyze_zlib_stream_for_gpu(
                        candidate,
                        scanline_size=4,
                        height=1,
                        expected_size=4,
                        target_adler=target_adler,
                    )
                    status = ultimate_opengl_backend.ULTIMATE_OPENGL_ANALYSIS_STATUS[analysis.status]
                    proof_mask = ultimate_opengl_backend.ULTIMATE_OPENGL_ANALYSIS_PROOF_OP_VALID
                    for name, bit in (
                        ("zlib_eof", ultimate_opengl_backend.ULTIMATE_OPENGL_ANALYSIS_PROOF_ZLIB_EOF),
                        ("size_match", ultimate_opengl_backend.ULTIMATE_OPENGL_ANALYSIS_PROOF_SIZE_MATCH),
                        (
                            "scanlines_complete",
                            ultimate_opengl_backend.ULTIMATE_OPENGL_ANALYSIS_PROOF_SCANLINES_COMPLETE,
                        ),
                        ("adler_match", ultimate_opengl_backend.ULTIMATE_OPENGL_ANALYSIS_PROOF_ADLER_MATCH),
                        ("terminal", ultimate_opengl_backend.ULTIMATE_OPENGL_ANALYSIS_PROOF_TERMINAL),
                    ):
                        if name in analysis.proof_flags:
                            proof_mask |= bit
                    computed_adler = analysis.computed_adler or 0
                    stored_adler = analysis.stored_adler or 0
                    usable_scanlines = analysis.usable_scanlines
                    decompressed_size = analysis.decompressed_size
                    adler_status = 4 if analysis.adler_status == "adler_match" else 1
                else:
                    status = ultimate_opengl_backend.ULTIMATE_OPENGL_ANALYSIS_STATUS["host_deflate_required"]
                    proof_mask = (
                        ultimate_opengl_backend.ULTIMATE_OPENGL_ANALYSIS_PROOF_OP_VALID
                        | ultimate_opengl_backend.ULTIMATE_OPENGL_ANALYSIS_PROOF_HOST_DEFLATE_REQUIRED
                    )
                    computed_adler = 0
                    stored_adler = int.from_bytes(candidate[-4:], "big")
                    usable_scanlines = 0
                    decompressed_size = 0
                    adler_status = 2
                hit_words.extend(
                    [
                        op_index,
                        0,
                        self.uniforms["pool_index"].value,
                        self.uniforms["depth"].value,
                        op_index,
                        status,
                        decompressed_size,
                        usable_scanlines,
                        0xFFFFFFFF,
                        stored_adler,
                        computed_adler,
                        adler_status,
                        proof_mask,
                        0,
                        0,
                        0,
                    ]
                )
            packed = [len(hit_words) // ultimate_opengl_backend.ULTIMATE_OPENGL_ANALYSIS_HIT_WORDS, tested, pruned]
            packed.extend(hit_words)
            output_buffer.data = struct.pack("<%sI" % len(packed), *packed)

        def release(self):
            calls.append(("shader_release",))

    class FakeContext:
        def __init__(self):
            self.bindings = {}

        def compute_shader(self, source):
            assert "STATUS_HOST_DEFLATE_REQUIRED" in source
            return FakeShader(self)

        def buffer(self, data=None, *, reserve=None):
            return FakeBuffer(self, data or b"", reserve)

        def memory_barrier(self):
            calls.append(("barrier",))

        def release(self):
            calls.append(("context_release",))

    filtered = b"\x00abc"
    stored_stream = zlib.compress(filtered, level=0)
    corrupt_stream = bytearray(stored_stream)
    corrupt_stream[-1] ^= 0xFF
    repair_operation = SimpleNamespace(
        kind="restore-adler-byte",
        stream_offset=len(corrupt_stream) - 1,
        old_bytes=bytes((corrupt_stream[-1],)),
        new_bytes=bytes((stored_stream[-1],)),
    )
    stored_plan = ultimate_opengl_backend.build_analysis_plan(
        bytes(corrupt_stream),
        width=1,
        height=1,
        bit_depth=8,
        color_type=2,
        scanline_size=4,
        expected_size=4,
        operation_pool=(repair_operation,),
        target_adler=zlib.adler32(filtered) & 0xFFFFFFFF,
    )
    stored_result = ultimate_opengl_backend.run_analysis_gpu(
        stored_plan,
        gpu_runtime.GpuRuntimeConfig(enabled=True, install_missing=False),
        harness_factory=lambda *, auto_install: gpu_opengl.OpenGLComputeHarness(FakeContext()),
        allow_host_fallback=False,
    )

    assert stored_result.shader_used is True
    assert stored_result.covered_rank_count == 1
    assert stored_result.hits[0].status == "complete"
    assert "terminal" in stored_result.hits[0].proof_flags
    assert ("barrier",) in calls

    dynamic_filtered = b"".join(b"\x00" + bytes((row, row * 3 % 256, row * 7 % 256)) for row in range(20))
    dynamic_stream = zlib.compress(dynamic_filtered, level=9)
    noop_operation = SimpleNamespace(
        kind="noop",
        stream_offset=0,
        old_bytes=bytes((dynamic_stream[0],)),
        new_bytes=bytes((dynamic_stream[0],)),
    )
    dynamic_plan = ultimate_opengl_backend.build_analysis_plan(
        dynamic_stream,
        width=1,
        height=20,
        bit_depth=8,
        color_type=2,
        scanline_size=4,
        expected_size=len(dynamic_filtered),
        operation_pool=(noop_operation,),
    )
    dynamic_result = ultimate_opengl_backend.run_analysis_gpu(
        dynamic_plan,
        gpu_runtime.GpuRuntimeConfig(enabled=True, install_missing=False),
        harness_factory=lambda *, auto_install: gpu_opengl.OpenGLComputeHarness(FakeContext()),
        allow_host_fallback=False,
    )

    assert dynamic_result.shader_used is True
    assert dynamic_result.hits[0].status == "host_deflate_required"
    assert "host_deflate_required" in dynamic_result.hits[0].proof_flags


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
    assert [
        (cursor.inner_index, cursor.byte_position, cursor.edit_kind_index, cursor.stage)
        for cursor in cursors
    ] == [
        (0, 0, 0, "direct"),
        (0, 0, 1, "direct"),
        (0, 0, 2, "direct"),
        (0, 1, 0, "direct"),
        (0, 1, 1, "direct"),
        (0, 1, 2, "direct"),
    ]
    assert smash_opengl_backend.replace1_rank_for_cursor(plan, 1, 2) == 15
    assert smash_opengl_backend.replace1_rank_for_cursor(plan, 1, 2, 2) == 17


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
            if int(self.uniforms["edit_kind"].value) == smash_opengl_backend.OPENGL_HERMES1_EDIT_KIND_INDEX["replace"]:
                output.data = struct.pack("<II", 1, 3) + b"\x00" * 252
            else:
                output.data = struct.pack("<I", 0) + b"\x00" * 256

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

    support = smash_opengl_backend._replace1_support_details(plan)
    assert support is not None
    assert result.tested == support.total_candidates
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
        harness_factory=lambda **_kwargs: _fake_rank_harness_for_plan(plan, (rank,)),
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
            if int(self.uniforms["edit_kind"].value) == smash_opengl_backend.OPENGL_HERMES1_EDIT_KIND_INDEX["replace"]:
                output.data = struct.pack("<III", 2, 3, 1) + b"\x00" * 248
            else:
                output.data = struct.pack("<I", 0) + b"\x00" * 256

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

    support = smash_opengl_backend._replace1_support_details(plan)
    assert support is not None
    assert result.tested == support.total_candidates
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
        harness_factory=lambda **_kwargs: _fake_rank_harness_for_plan(plan, ()),
        batch_size=2,
        progress_callback=lambda tested, total: progress.append((tested, total)),
    )

    support = smash_opengl_backend._replace1_support_details(plan)
    assert support is not None
    assert result.tested == support.total_candidates
    assert result.hits == ()
    assert progress == [(2, 12), (4, 12), (6, 12), (8, 12), (10, 12), (12, 12)]


def test_replace1_kernel_resumes_from_direct_cursor_rank():
    progress = []
    plan = _plan_for_payload(payload=b"\x10\x20", repaired_payload=b"\x10\x42", values=(0x41, 0x42))
    cursor = smash_opengl_backend.OpenGLReplace1Cursor(
        inner_index=1,
        byte_position=0,
        edit_kind_index=0,
        stage="direct",
    )
    start_rank = smash_opengl_backend.replace1_rank_for_cursor(
        plan,
        cursor.inner_index,
        cursor.byte_position,
        cursor.edit_kind_index,
    )

    result = smash_opengl_backend.run_replace1_crc_kernel(
        plan,
        gpu_runtime.GpuRuntimeConfig(enabled=True),
        harness_factory=lambda **_kwargs: _fake_rank_harness_for_plan(plan, ()),
        resume_cursor=cursor,
        progress_callback=lambda tested, total, **kwargs: progress.append(
            (tested, total, getattr(kwargs.get("cursor"), "inner_index", None))
        ),
    )

    support = smash_opengl_backend._replace1_support_details(plan)
    assert support is not None
    assert start_rank == 6
    assert result.tested == support.total_candidates - start_rank
    assert result.next_cursor is None
    assert progress[-1] == (6, 6, None)


def test_insert1_kernel_result_reconstructs_cpu_hit_from_gpu_rank():
    plan = _plan_for_payload(
        payload=b"\x10\x20",
        repaired_payload=b"\x10\x42\x20",
        values=(0, 0x42),
        edit_mode="Insert",
    )
    rank = smash_opengl_backend.replace1_rank_for_cursor(plan, 1, 1)
    result = smash_opengl_backend.run_replace1_crc_kernel(
        plan,
        gpu_runtime.GpuRuntimeConfig(enabled=True),
        harness_factory=lambda **_kwargs: _fake_rank_harness_for_plan(plan, (rank,)),
    )

    support = smash_opengl_backend._replace1_support_details(plan)
    assert support is not None
    assert result.tested == support.total_candidates
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
    rank = smash_opengl_backend.replace1_rank_for_cursor(plan, 0, 1)
    result = smash_opengl_backend.run_replace1_crc_kernel(
        plan,
        gpu_runtime.GpuRuntimeConfig(enabled=True),
        harness_factory=lambda **_kwargs: _fake_rank_harness_for_plan(plan, (rank,)),
    )

    support = smash_opengl_backend._replace1_support_details(plan)
    assert support is not None
    assert result.tested == support.total_candidates
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
        harness_factory=lambda **_kwargs: _fake_rank_harness_for_plan(plan, (rank,)),
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
        harness_factory=lambda **_kwargs: _fake_rank_harness_for_plan(plan, (rank,)),
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
        harness_factory=lambda **_kwargs: _fake_rank_harness_for_plan(plan, (rank,)),
    )

    support = smash_opengl_backend._replace1_support_details(plan)
    assert support is not None
    assert result.tested == support.total_candidates
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
        harness_factory=lambda **_kwargs: _fake_rank_harness_for_plan(plan, (rank,)),
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


def test_replace4_kernel_can_stop_after_large_kagebushin_style_hit():
    payload = bytearray(b"\x00" * 1_455_182)
    repaired_payload = bytearray(payload)
    corruption_offset = 1_061_222
    restored = b"\x00\x00\x05\x7f"
    payload[corruption_offset : corruption_offset + 4] = b"\xff\xff\xfa\x80"
    repaired_payload[corruption_offset : corruption_offset + 4] = restored
    plan = _plan_for_payload(
        payload=bytes(payload),
        repaired_payload=bytes(repaired_payload),
        values=None,
        candidate_len=4,
    )
    inner_index = int.from_bytes(restored, "big")
    cursor = smash_opengl_backend.OpenGLReplace1Cursor(
        inner_index=inner_index,
        byte_position=corruption_offset,
        edit_kind_index=0,
        stage="direct",
    )
    rank = smash_opengl_backend.replace1_rank_for_cursor(
        plan,
        cursor.inner_index,
        cursor.byte_position,
        cursor.edit_kind_index,
    )

    result = smash_opengl_backend.run_replace1_crc_kernel(
        plan,
        gpu_runtime.GpuRuntimeConfig(enabled=True),
        harness_factory=lambda **_kwargs: _fake_rank_harness_for_plan(plan, (rank,)),
        batch_size=64,
        resume_cursor=cursor,
        stop_after_first_hit=True,
    )

    support = smash_opengl_backend._replace1_support_details(plan)
    assert support is not None
    assert rank == 6_145_494_225
    assert result.tested < support.total_candidates - rank
    assert result.covered_full_cpu_space is False
    assert result.next_cursor is not None
    assert (
        smash_opengl_backend.replace1_rank_for_cursor(
            plan,
            result.next_cursor.inner_index,
            result.next_cursor.byte_position,
            result.next_cursor.edit_kind_index,
        )
        == rank + 1
    )
    assert len(result.hits) == 1
    hit = result.hits[0]
    assert hit.inner_index == inner_index
    assert hit.byte_position == corruption_offset
    assert hit.edit_kind_index == 0
    assert hit.stage == "direct"
    assert hit.brute_bytes == restored
    assert hit.edit_kind == "replace"
    assert hit.old_crc_match is True


def test_insert4_kernel_can_stop_after_large_kagebushin_missing_hit():
    repaired_payload = bytearray(b"\x00" * 1_455_182)
    corruption_offset = 1_061_222
    restored = b"\x00\x00\x05\x7f"
    repaired_payload[corruption_offset : corruption_offset + 4] = restored
    payload = repaired_payload[:corruption_offset] + repaired_payload[corruption_offset + 4 :]
    plan = _plan_for_payload(
        payload=bytes(payload),
        repaired_payload=bytes(repaired_payload),
        values=None,
        candidate_len=4,
    )
    inner_index = int.from_bytes(restored, "big")
    cursor = smash_opengl_backend.OpenGLReplace1Cursor(
        inner_index=inner_index,
        byte_position=corruption_offset,
        edit_kind_index=1,
        stage="direct",
    )
    rank = smash_opengl_backend.replace1_rank_for_cursor(
        plan,
        cursor.inner_index,
        cursor.byte_position,
        cursor.edit_kind_index,
    )

    result = smash_opengl_backend.run_replace1_crc_kernel(
        plan,
        gpu_runtime.GpuRuntimeConfig(enabled=True),
        harness_factory=lambda **_kwargs: _fake_rank_harness_for_plan(plan, (rank,)),
        batch_size=64,
        resume_cursor=cursor,
        stop_after_first_hit=True,
    )

    support = smash_opengl_backend._replace1_support_details(plan)
    assert support is not None
    assert rank == 6_145_477_342
    assert result.tested < support.total_candidates - rank
    assert result.covered_full_cpu_space is False
    assert result.next_cursor is not None
    assert (
        smash_opengl_backend.replace1_rank_for_cursor(
            plan,
            result.next_cursor.inner_index,
            result.next_cursor.byte_position,
            result.next_cursor.edit_kind_index,
        )
        == rank + 1
    )
    assert len(result.hits) == 1
    hit = result.hits[0]
    assert hit.inner_index == inner_index
    assert hit.byte_position == corruption_offset
    assert hit.edit_kind_index == 1
    assert hit.stage == "direct"
    assert hit.brute_bytes == restored
    assert hit.edit_kind == "insert"
    assert hit.old_crc_match is True


def test_remove4_kernel_can_stop_after_large_kagebushin_extra_hit():
    repaired_payload = bytearray(b"\x00" * 1_455_182)
    corruption_offset = 1_061_222
    extra_bytes = b"\x00\x00\x00\x00"
    payload = (
        repaired_payload[:corruption_offset]
        + extra_bytes
        + repaired_payload[corruption_offset:]
    )
    plan = _plan_for_payload(
        payload=bytes(payload),
        repaired_payload=bytes(repaired_payload),
        values=None,
        candidate_len=4,
    )
    cursor = smash_opengl_backend.OpenGLReplace1Cursor(
        inner_index=0,
        byte_position=corruption_offset,
        edit_kind_index=2,
        stage="direct",
    )
    rank = smash_opengl_backend.replace1_rank_for_cursor(
        plan,
        cursor.inner_index,
        cursor.byte_position,
        cursor.edit_kind_index,
    )

    result = smash_opengl_backend.run_replace1_crc_kernel(
        plan,
        gpu_runtime.GpuRuntimeConfig(enabled=True),
        harness_factory=lambda **_kwargs: _fake_rank_harness_for_plan(plan, (rank,)),
        batch_size=64,
        resume_cursor=cursor,
        stop_after_first_hit=True,
    )

    support = smash_opengl_backend._replace1_support_details(plan)
    assert support is not None
    assert rank == 3_183_668
    assert result.tested < support.total_candidates - rank
    assert result.covered_full_cpu_space is False
    assert result.next_cursor is not None
    assert (
        smash_opengl_backend.replace1_rank_for_cursor(
            plan,
            result.next_cursor.inner_index,
            result.next_cursor.byte_position,
            result.next_cursor.edit_kind_index,
        )
        == rank + 1
    )
    assert len(result.hits) == 1
    hit = result.hits[0]
    assert hit.inner_index == 0
    assert hit.byte_position == corruption_offset
    assert hit.edit_kind_index == 2
    assert hit.stage == "direct"
    assert hit.brute_bytes == extra_bytes
    assert hit.edit_kind == "remove"
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
        uniforms = self.uniforms
        edit_kind = int(uniforms["edit_kind"].value)
        try:
            edit_kind_index = self.harness.edit_kind_codes.index(edit_kind)
        except ValueError:
            edit_kind_index = -1
        edit_kind_count = len(self.harness.edit_kind_codes)
        position_count = int(uniforms["position_count"].value)
        candidate_low_base = int(uniforms["candidate_low_base"].value)
        base_local_rank = int(uniforms["base_local_rank"].value)
        batch_count = int(uniforms["batch_count"].value)
        tile_rank_base = candidate_low_base * position_count
        full_local_start = tile_rank_base + base_local_rank
        full_local_end = full_local_start + batch_count
        local_ranks = []
        for rank in self.harness.ranks:
            if edit_kind_index < 0 or int(rank) % edit_kind_count != edit_kind_index:
                continue
            full_local_rank = int(rank) // edit_kind_count
            if full_local_start <= full_local_rank < full_local_end:
                local_ranks.append(full_local_rank - tile_rank_base)
        output.data = struct.pack("<I", len(local_ranks)) + b"".join(
            struct.pack("<I", rank) for rank in local_ranks
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
    def __init__(self, ranks, *, edit_order=("replace", "insert", "remove")):
        self.ranks = tuple(ranks)
        self.edit_kind_codes = tuple(
            smash_opengl_backend.OPENGL_HERMES1_EDIT_KIND_INDEX[item]
            for item in edit_order
        )
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


def _fake_rank_harness_for_plan(plan, ranks):
    return _FakeRankHarness(
        ranks,
        edit_order=bruteforce.iter_twobytes_edit_kinds(plan.edit_mode, plan.chunk_name),
    )


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
