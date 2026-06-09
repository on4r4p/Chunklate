#!/usr/bin/env python3
import json
import inspect
import struct
import sys
import tempfile
import zlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import (
    bruteforce,
    bruteforce_runtime,
    bruteforce_viewer,
    gpu_runtime,
    smash_backend,
    smash_checkpoint,
    smash_opengl_backend,
)
from chunklate.png import IEND_CHUNK, PNG_SIGNATURE, build_png_chunk, iter_chunks
from pytest import MonkeyPatch


@dataclass
class FakeClock:
    value: datetime = datetime(2026, 5, 25, 10, 0, 0)

    def __call__(self):
        current = self.value
        self.value = self.value + timedelta(seconds=1)
        return current


def build_runtime(
    calls,
    *,
    specs,
    product_values,
    viewer_results=None,
    side_notes=None,
    progress_path="",
    source_hash="",
    source_size=0,
    source_path="",
    resume_record=None,
    smash_workers=0,
    suppress_candidate_viewer=False,
    gpu_config=None,
):
    side_notes = [] if side_notes is None else side_notes
    viewer_results = [] if viewer_results is None else list(viewer_results)

    def load_spec(request):
        calls.append(("load_spec", request))
        return specs(request)

    def product(chunk_data, color_type):
        calls.append(("product", tuple(chunk_data), color_type))
        return list(product_values)

    def loadingbar(max_iter, len_iter, current, start):
        calls.append(("loadingbar", max_iter, len_iter, current, start))

    def minibar(**kwargs):
        calls.append(("minibar", kwargs))

    def show_candidate(png_bytes, full_new_data, loop_index, debug_bytes):
        calls.append(("show_candidate", png_bytes, full_new_data, loop_index, debug_bytes))
        if viewer_results:
            return viewer_results.pop(0)
        return bruteforce_viewer.BruteForceViewerResult(False)

    def emit(message):
        calls.append(("emit", message))

    def pause(message):
        calls.append(("pause", message))

    return bruteforce_runtime.SmashBruteBrawlRuntime(
        load_spec=load_spec,
        product=product,
        loadingbar=loadingbar,
        minibar=minibar,
        show_candidate=show_candidate,
        emit=emit,
        pause=pause,
        side_notes=side_notes,
        raw_print=lambda *args, **kwargs: calls.append(("raw_print", args, kwargs)),
        now=FakeClock(),
        progress_path=progress_path,
        source_hash=source_hash,
        source_size=source_size,
        source_path=source_path,
        resume_record=resume_record,
        smash_workers=smash_workers,
        suppress_candidate_viewer=suppress_candidate_viewer,
        gpu_config=gpu_config or gpu_runtime.GpuRuntimeConfig(),
    )


def base_context(**updates):
    context = {
        "file": "broken.png",
        "chunk_name": b"gAMA",
        "chunk_length": 1,
        "data_offset": 8,
        "from_error": "Relics",
        "data_hex": "00112233445566778899aabbccddeeff00112233445566778899",
        "pandora_box": {},
        "edit_mode": "Replace",
        "bf_mode": "Brutus",
        "brute_crc": True,
        "brute_length": True,
        "old_crc": False,
        "brute_level": 0,
        "crash": False,
        "debug": False,
        "pause_debug": False,
    }
    context.update(updates)
    return bruteforce_runtime.SmashBruteBrawlContext(**context)


def simple_specs(request):
    if request.fields:
        return (2, ("B",))
    return (2, 1, 2, ("B",), [(7,)], "color")


def small_rgba_png(raw_pixel=b"\x01\x02\x03\xff") -> bytes:
    ihdr = struct.pack("!IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    filtered = b"\x00" + raw_pixel
    return (
        PNG_SIGNATURE
        + build_png_chunk(b"IHDR", ihdr)
        + build_png_chunk(b"IDAT", zlib.compress(filtered))
        + IEND_CHUNK
    )


def invalid_idat_png() -> bytes:
    ihdr = struct.pack("!IIBBBBB", 1, 1, 8, 6, 0, 0, 0)
    return (
        PNG_SIGNATURE
        + build_png_chunk(b"IHDR", ihdr)
        + build_png_chunk(b"IDAT", b"\x78\x9c\x00")
        + IEND_CHUNK
    )


def accept_fake_sbb_candidates(monkeypatch) -> None:
    monkeypatch.setattr(
        bruteforce_runtime,
        "validate_sbb_candidate",
        lambda _png_bytes: bruteforce_runtime.SbbCandidateValidation(True),
    )


def test_run_scan_gpu_crc_useless_falls_back_to_cpu(monkeypatch):
    calls = []

    def cpu_parallel(*_args, **_kwargs):
        calls.append(("cpu_parallel",))
        return True

    monkeypatch.setattr(bruteforce_runtime, "_run_parallel_scan", cpu_parallel)
    runtime = build_runtime(
        calls,
        specs=simple_specs,
        product_values=[],
        gpu_config=gpu_runtime.GpuRuntimeConfig(enabled=True),
    )
    context = base_context(chunk_name=b"IDAT", bf_mode="TwoBytes", old_crc=False)

    bruteforce_runtime.run_scan(runtime, context)

    assert ("cpu_parallel",) in calls
    assert any(
        call[0] == "emit" and "GPU requested: SBB pass has no CRC target" in call[1]
        for call in calls
    )


def test_hermes_idat_direct_window_length_plans_follow_brute_level():
    expected = {
        0: (1, 256),
        1: (2, 256**2),
        2: (4, 256**4),
    }

    for brute_level, (candidate_bytes, max_iter) in expected.items():
        calls = []
        runtime = build_runtime(
            calls,
            specs=simple_specs,
            product_values=[],
        )
        context = base_context(
            chunk_name=b"IDAT",
            bf_mode="TwoBytes",
            brute_level=brute_level,
        )
        runtime_plan = bruteforce_runtime.prepare_runtime_plan(runtime, context)

        length_plans = bruteforce_runtime._build_smash_length_plans(
            runtime,
            context,
            runtime_plan,
        )

        assert len(length_plans) == 1
        length_plan = length_plans[0]
        assert length_plan.length == candidate_bytes * 2
        assert length_plan.max_iter == max_iter
        assert length_plan.chunk_format == tuple("B" for _ in range(candidate_bytes))
        assert len(length_plan.chunk_data) == candidate_bytes
        assert all(tuple(values) == tuple(range(256)) for values in length_plan.chunk_data)


def test_hermes_window_width_is_part_of_candidate_space_hash():
    runtime = build_runtime(
        [],
        specs=simple_specs,
        product_values=[],
        source_hash="source-hash",
    )
    context_1 = base_context(chunk_name=b"IDAT", bf_mode="TwoBytes", brute_level=0)
    context_2 = base_context(chunk_name=b"IDAT", bf_mode="TwoBytes", brute_level=1)
    runtime_plan_1 = bruteforce_runtime.prepare_runtime_plan(runtime, context_1)
    runtime_plan_2 = bruteforce_runtime.prepare_runtime_plan(runtime, context_2)

    payload_1 = bruteforce_runtime._candidate_space_payload(
        context_1,
        runtime_plan_1,
        source_hash="source-hash",
    )
    payload_2 = bruteforce_runtime._candidate_space_payload(
        context_2,
        runtime_plan_2,
        source_hash="source-hash",
    )

    assert payload_1["hermes_window_bytes"] == 1
    assert payload_2["hermes_window_bytes"] == 2
    assert (
        smash_checkpoint.candidate_space_hash(payload_1)
        != smash_checkpoint.candidate_space_hash(payload_2)
    )


def test_run_scan_gpu_mock_backend_short_circuits_cpu(monkeypatch):
    calls = []

    def gpu_explain(plan, config):
        calls.append(("gpu_explain", plan, config))
        return smash_opengl_backend.SmashOpenGLDecision(True, "OpenGL SBB path active.")

    def gpu_run(*args, **kwargs):
        calls.append(("gpu_run", args, kwargs))
        return True

    monkeypatch.setattr(smash_opengl_backend, "explain", gpu_explain)
    monkeypatch.setattr(smash_opengl_backend, "run_scan", gpu_run)
    monkeypatch.setattr(
        bruteforce_runtime,
        "_run_parallel_scan",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("CPU fallback should not run")),
    )
    runtime = build_runtime(
        calls,
        specs=simple_specs,
        product_values=[],
        gpu_config=gpu_runtime.GpuRuntimeConfig(enabled=True),
    )
    context = base_context(
        chunk_name=b"IDAT",
        bf_mode="TwoBytes",
        old_crc=b"\x00\x00\x00\x00",
    )

    bruteforce_runtime.run_scan(runtime, context)

    assert any(call[0] == "gpu_explain" for call in calls)
    assert any(call[0] == "gpu_run" for call in calls)
    assert ("emit", "-GPU requested: OpenGL SBB path active.") in calls


def test_run_scan_gpu_hits_are_validated_before_short_circuit(monkeypatch):
    calls = []
    accept_fake_sbb_candidates(monkeypatch)

    def gpu_explain(plan, config):
        calls.append(("gpu_explain", plan, config))
        return smash_opengl_backend.SmashOpenGLDecision(True, "OpenGL SBB path active.")

    hit = smash_backend.SmashCandidateHit(
        outer_index=0,
        length=2,
        inner_index=7,
        checksum=b"\x00\x00\x00\x00",
        full_new_data=b"chunk",
        png_bytes=small_rgba_png(),
        brute_bytes=b"\x07",
        old_crc_match=True,
        edit_kind="replace",
    )

    def gpu_run(*args, **kwargs):
        calls.append(("gpu_run", args, kwargs))
        return smash_opengl_backend.OpenGLReplace1Result((hit,), tested=64)

    monkeypatch.setattr(smash_opengl_backend, "explain", gpu_explain)
    monkeypatch.setattr(smash_opengl_backend, "run_scan", gpu_run)
    monkeypatch.setattr(
        bruteforce_runtime,
        "_run_parallel_scan",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("CPU fallback should not run")),
    )
    runtime = build_runtime(
        calls,
        specs=simple_specs,
        product_values=[],
        gpu_config=gpu_runtime.GpuRuntimeConfig(enabled=True),
    )
    context = base_context(
        chunk_name=b"IDAT",
        bf_mode="TwoBytes",
        old_crc=b"\x00\x00\x00\x00",
    )

    result = bruteforce_runtime.run_scan(runtime, context)

    assert result.state.bingo is True
    assert result.full_new_data == b"chunk"
    assert any(call[0] == "gpu_run" for call in calls)
    assert not [call for call in calls if call[0] == "show_candidate"]


def test_run_scan_gpu_truncated_invalid_hits_do_not_fall_back_to_cpu(monkeypatch):
    calls = []

    monkeypatch.setattr(
        bruteforce_runtime,
        "validate_sbb_candidate",
        lambda _png_bytes: bruteforce_runtime.SbbCandidateValidation(
            False,
            "IDAT zlib stream is invalid",
            "invalid_structural",
        ),
    )

    def gpu_explain(plan, config):
        calls.append(("gpu_explain", plan, config))
        return smash_opengl_backend.SmashOpenGLDecision(True, "OpenGL SBB path active.")

    hit = smash_backend.SmashCandidateHit(
        outer_index=0,
        length=2,
        inner_index=7,
        checksum=b"\x00\x00\x00\x00",
        full_new_data=b"chunk",
        png_bytes=invalid_idat_png(),
        brute_bytes=b"\x07",
        old_crc_match=True,
        edit_kind="replace",
    )

    def gpu_run(*args, **kwargs):
        calls.append(("gpu_run", args, kwargs))
        progress_callback = kwargs.get("progress_callback")
        if progress_callback is not None:
            progress_callback(64, 128)
        return smash_opengl_backend.OpenGLReplace1Result((hit,), tested=64, truncated=True)

    monkeypatch.setattr(smash_opengl_backend, "explain", gpu_explain)
    monkeypatch.setattr(smash_opengl_backend, "run_scan", gpu_run)
    monkeypatch.setattr(
        bruteforce_runtime,
        "_run_parallel_scan",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("CPU fallback should not run")),
    )
    with tempfile.TemporaryDirectory() as directory:
        progress_path = str(Path(directory) / "_SBB.progress.json")
        runtime = build_runtime(
            calls,
            specs=simple_specs,
            product_values=[],
            progress_path=progress_path,
            source_hash="source-hash",
            gpu_config=gpu_runtime.GpuRuntimeConfig(enabled=True),
        )
        context = base_context(
            chunk_name=b"IDAT",
            bf_mode="TwoBytes",
            old_crc=b"\x00\x00\x00\x00",
        )

        result = bruteforce_runtime.run_scan(runtime, context)
        record = json.loads(Path(progress_path).read_text(encoding="utf-8"))

    assert result.state.bingo is False
    assert record["status"] == "rejected_hit"
    assert record["backend"] == "opengl"
    assert any(call[0] == "gpu_run" for call in calls)
    assert not [
        call for call in calls
        if call[0] == "emit" and "using CPU workers" in call[1]
    ]


def test_validate_sbb_candidate_accepts_complete_png():
    assert bruteforce_runtime.validate_sbb_candidate(small_rgba_png()).ok is True


def test_validate_sbb_candidate_rejects_crc_only_bad_idat():
    validation = bruteforce_runtime.validate_sbb_candidate(invalid_idat_png())

    assert validation.ok is False
    assert "IDAT zlib stream is invalid" in validation.reason
    assert validation.category == "invalid_structural"


def test_validate_sbb_candidate_rejects_almost_transparent_output():
    validation = bruteforce_runtime.validate_sbb_candidate(small_rgba_png(b"\x00\x00\x00\x03"))

    assert validation.ok is False
    assert validation.category == "valid_but_visual_untrusted"
    assert "almost fully transparent" in validation.reason


def test_apply_parallel_hit_rejects_oldcrc_match_before_saving_invalid_png():
    calls = []
    runtime = build_runtime(calls, specs=simple_specs, product_values=[(7,)])
    scan_state = bruteforce_runtime.SmashBruteBrawlScanState(
        state=bruteforce.BruteForceMatchState()
    )
    hit = smash_backend.SmashCandidateHit(
        outer_index=0,
        length=1,
        inner_index=0,
        checksum=b"\x00\x00\x00\x00",
        full_new_data=b"chunk",
        png_bytes=invalid_idat_png(),
        brute_bytes=b"",
        old_crc_match=True,
    )

    accepted = bruteforce_runtime._apply_parallel_hit(
        runtime,
        scan_state,
        b"\x00\x00\x00\x00",
        hit,
    )

    assert accepted is False
    assert scan_state.accepted_candidates == 0
    assert scan_state.rejected_candidates == 1
    assert not [call for call in calls if call[0] == "show_candidate"]
    assert scan_state.rejected_reasons
    assert not [
        call for call in calls
        if call[0] == "emit" and "SBB rejected" in call[1]
    ]


def test_apply_parallel_hit_accepts_oldcrc_match_after_full_png_validation():
    calls = []
    runtime = build_runtime(calls, specs=simple_specs, product_values=[(7,)])
    scan_state = bruteforce_runtime.SmashBruteBrawlScanState(
        state=bruteforce.BruteForceMatchState()
    )
    hit = smash_backend.SmashCandidateHit(
        outer_index=0,
        length=1,
        inner_index=0,
        checksum=b"\x00\x00\x00\x00",
        full_new_data=b"chunk",
        png_bytes=small_rgba_png(),
        brute_bytes=b"",
        old_crc_match=True,
    )

    accepted = bruteforce_runtime._apply_parallel_hit(
        runtime,
        scan_state,
        b"\x00\x00\x00\x00",
        hit,
    )

    assert accepted is True
    assert scan_state.accepted_candidates == 1
    assert scan_state.state.bingo is True
    assert not [call for call in calls if call[0] == "show_candidate"]


def test_sbb_rejection_messages_are_summary_only():
    calls = []
    side_notes = []
    runtime = build_runtime(calls, specs=simple_specs, product_values=[(7,)], side_notes=side_notes)
    scan_state = bruteforce_runtime.SmashBruteBrawlScanState(
        state=bruteforce.BruteForceMatchState()
    )

    for _index in range(1000):
        bruteforce_runtime._record_sbb_candidate_rejected(
            runtime,
            scan_state,
            "Incomplete chunk at offset 8351",
        )
    bruteforce_runtime._emit_sbb_rejection_progress(runtime, scan_state, force=True)

    emit_calls = [
        call for call in calls
        if call[0] == "emit" and "SBB rejected" in call[1]
    ]
    assert scan_state.rejected_candidates == 1000
    assert scan_state.rejected_reasons["Incomplete chunk at offset 8351"] == 1000
    assert emit_calls == []
    assert any("rejected 1000 candidate" in note for note in side_notes)


def test_apply_parallel_hit_without_crc_uses_viewer_outside_internal_campaign():
    calls = []
    runtime = build_runtime(
        calls,
        specs=simple_specs,
        product_values=[(7,)],
        viewer_results=[bruteforce_viewer.BruteForceViewerResult(True, "looks-good")],
    )
    scan_state = bruteforce_runtime.SmashBruteBrawlScanState(
        state=bruteforce.BruteForceMatchState()
    )
    hit = smash_backend.SmashCandidateHit(
        outer_index=0,
        length=1,
        inner_index=0,
        checksum=b"\x00\x00\x00\x00",
        full_new_data=b"chunk",
        png_bytes=small_rgba_png(),
        brute_bytes=b"",
        old_crc_match=False,
    )

    accepted = bruteforce_runtime._apply_parallel_hit(runtime, scan_state, False, hit)

    assert accepted is True
    assert scan_state.state.bingo is True
    assert scan_state.diff == "looks-good"
    assert [call[0] for call in calls].count("show_candidate") == 1


def test_apply_parallel_hit_without_crc_is_not_auto_accepted_in_internal_campaign():
    calls = []
    with tempfile.TemporaryDirectory() as directory:
        progress_path = str(Path(directory) / "_SBB.progress.json")
        runtime = build_runtime(
            calls,
            specs=simple_specs,
            product_values=[(7,)],
            viewer_results=[bruteforce_viewer.BruteForceViewerResult(True, "ignored")],
            progress_path=progress_path,
            suppress_candidate_viewer=True,
        )
        scan_state = bruteforce_runtime.SmashBruteBrawlScanState(
            state=bruteforce.BruteForceMatchState()
        )
        hit = smash_backend.SmashCandidateHit(
            outer_index=0,
            length=1,
            inner_index=0,
            checksum=b"\x00\x00\x00\x00",
            full_new_data=b"chunk",
            png_bytes=small_rgba_png(),
            brute_bytes=b"",
            old_crc_match=False,
        )

        accepted = bruteforce_runtime._apply_parallel_hit(runtime, scan_state, False, hit)
        previews = list((Path(directory) / "Bruteforce_Previews" / "SBB_Candidates").glob("*.png"))

    assert accepted is False
    assert scan_state.state.bingo is False
    assert scan_state.accepted_candidates == 0
    assert scan_state.rejected_candidates == 1
    assert scan_state.untrusted_preview_count == 1
    assert len(previews) == 1
    assert not [call for call in calls if call[0] == "show_candidate"]
    assert not [
        call for call in calls
        if call[0] == "emit" and "SBB rejected" in call[1]
    ]


def test_run_scan_preserves_oldcrc_path_without_viewer(monkeypatch):
    accept_fake_sbb_candidates(monkeypatch)
    calls = []
    chunk_name = b"gAMA"
    old_crc = bruteforce.chunk_crc(chunk_name, b"\x07").hex()
    runtime = build_runtime(calls, specs=simple_specs, product_values=[(7,)])

    result = bruteforce_runtime.run_scan(
        runtime,
        base_context(chunk_name=chunk_name, old_crc=old_crc),
    )

    assert result.state == bruteforce.BruteForceMatchState(
        bingo=True,
        replace_flag=True,
    )
    assert result.old_crc == bytes.fromhex(old_crc)
    assert result.full_new_data == (
        b"\x00\x00\x00\x01" + chunk_name + b"\x07" + bytes.fromhex(old_crc)
    )
    assert result.to_brute == "cc"
    assert result.bf_mode == "Brutus"
    assert result.crash is False
    assert not [call for call in calls if call[0] == "show_candidate"]
    assert ("loadingbar", 2, 1, None, True) in calls
    assert ("loadingbar", 2, 1, 0, False) in calls


def test_resolve_smash_worker_profiles():
    assert smash_backend.resolve_smash_worker_count(None, cpu_count=16) == 0
    assert smash_backend.resolve_smash_worker_count("0", cpu_count=16) == 0
    assert smash_backend.resolve_smash_worker_count("min", cpu_count=16) == 4
    assert smash_backend.resolve_smash_worker_count("normal", cpu_count=16) == 8
    assert smash_backend.resolve_smash_worker_count("auto", cpu_count=16) == 8
    assert smash_backend.resolve_smash_worker_count("max", cpu_count=16) == 15
    assert smash_backend.resolve_smash_worker_count("3", cpu_count=16) == 3


def test_smash_parallel_worker_initializer_ignores_sigint(monkeypatch):
    calls = []

    def fake_signal(signum, handler):
        calls.append((signum, handler))

    monkeypatch.setattr(smash_backend.signal, "signal", fake_signal)

    smash_backend.ignore_worker_sigint()

    assert calls == [(smash_backend.signal.SIGINT, smash_backend.signal.SIG_IGN)]


def test_parallel_progress_records_finished_out_of_order_shards():
    calls = []
    with tempfile.TemporaryDirectory() as directory:
        progress_path = str(Path(directory) / "_SBB.progress.json")
        runtime = build_runtime(
            calls,
            specs=simple_specs,
            product_values=[(1,)],
            progress_path=progress_path,
            source_hash="source-hash",
        )
        context = base_context()
        runtime_plan = bruteforce_runtime.prepare_runtime_plan(runtime, context)
        scan_state = bruteforce_runtime.SmashBruteBrawlScanState(
            state=bruteforce.BruteForceMatchState(),
        )
        shards = [
            smash_backend.SmashShard(
                shard_id=0,
                length_plan_index=0,
                start_inner_index=0,
                end_inner_index=10,
            ),
            smash_backend.SmashShard(
                shard_id=1,
                length_plan_index=0,
                start_inner_index=10,
                end_inner_index=20,
            ),
        ]
        results = {
            1: smash_backend.SmashShardResult(
                shard=shards[1],
                tested=10,
                next_inner_index=20,
            )
        }

        bruteforce_runtime._save_parallel_progress(
            runtime,
            context,
            runtime_plan,
            scan_state,
            candidate_space_hash="hash",
            worker_count=2,
            shard_size=10,
            shards=shards,
            results=results,
            tested_floor=5,
            force=True,
        )

        record = json.loads(Path(progress_path).read_text(encoding="utf-8"))

    assert record["counters"]["tested_candidates"] == 15
    assert record["shards"][0]["status"] == "pending"
    assert record["shards"][0]["tested"] == 0
    assert record["shards"][1]["status"] == "done"
    assert record["shards"][1]["tested"] == 10


def test_empty_pending_parallel_checkpoint_is_rejected_as_stale():
    record = {
        "backend": "cpu-parallel",
        "counters": {"tested_candidates": 0},
        "shards": [
            {
                "kind": "twobytes",
                "status": "pending",
                "tested": 0,
                "byte_start": 0,
                "byte_end": 10,
                "next_byte_position": 0,
                "edit_kind_index": 0,
                "stage": "",
            }
        ],
    }

    assert bruteforce_runtime._smash_parallel_progress_is_empty_stale(record) is True

    record["shards"][0]["tested"] = 1
    assert bruteforce_runtime._smash_parallel_progress_is_empty_stale(record) is False


def test_empty_serial_interrupted_checkpoint_is_rejected_as_stale():
    context = base_context(chunk_name=b"gAMA", old_crc="00000000", campaign_focus="remove")
    runtime = build_runtime(
        [],
        specs=simple_specs,
        product_values=[(7,), (8,)],
        source_hash="source-hash",
    )
    runtime_plan = bruteforce_runtime.prepare_runtime_plan(runtime, context)
    candidate_hash = smash_checkpoint.candidate_space_hash(
        bruteforce_runtime._candidate_space_payload(
            context,
            runtime_plan,
            source_hash="source-hash",
        )
    )
    record = {
        "status": "interrupted",
        "source_hash": "source-hash",
        "invocation": smash_checkpoint.invocation_record(
            file=context.file,
            chunk_name=context.chunk_name,
            chunk_length=context.chunk_length,
            data_offset=context.data_offset,
            from_error=context.from_error,
            edit_mode=context.edit_mode,
            bf_mode=context.bf_mode,
            brute_crc=context.brute_crc,
            brute_length=context.brute_length,
            old_crc=context.old_crc,
            brute_level=context.brute_level,
            campaign_focus=context.campaign_focus,
        ),
        "plan": {"candidate_space_hash": candidate_hash},
        "cursor": {
            "outer_index": 0,
            "inner_index": 0,
            "byte_position": 0,
            "edit_kind_index": 0,
            "stage": "",
            "bonus_offset": 0,
            "bonus_value": 0,
        },
        "counters": {"tested_candidates": 0, "accepted_candidates": 0},
        "shards": [],
    }

    resolved, warning = bruteforce_runtime._resolve_resume_record(
        runtime,
        context,
        runtime_plan,
        candidate_hash,
    )
    assert resolved is None
    assert warning == ""

    runtime = build_runtime(
        [],
        specs=simple_specs,
        product_values=[(7,), (8,)],
        source_hash="source-hash",
        resume_record=record,
    )
    resolved, warning = bruteforce_runtime._resolve_resume_record(
        runtime,
        context,
        runtime_plan,
        candidate_hash,
    )
    assert resolved is None
    assert "stale checkpoint ignored" in warning


def test_opengl_checkpoint_can_resume_on_cpu_when_hash_matches():
    context = base_context(chunk_name=b"IDAT", bf_mode="TwoBytes", old_crc="00000000")
    runtime = build_runtime(
        [],
        specs=simple_specs,
        product_values=[(7,), (8,)],
        source_hash="source-hash",
    )
    runtime_plan = bruteforce_runtime.prepare_runtime_plan(runtime, context)
    candidate_hash = smash_checkpoint.candidate_space_hash(
        bruteforce_runtime._candidate_space_payload(
            context,
            runtime_plan,
            source_hash="source-hash",
        )
    )
    record = {
        "status": "running",
        "backend": "opengl",
        "source_hash": "source-hash",
        "invocation": smash_checkpoint.invocation_record(
            file=context.file,
            chunk_name=context.chunk_name,
            chunk_length=context.chunk_length,
            data_offset=context.data_offset,
            from_error=context.from_error,
            edit_mode=context.edit_mode,
            bf_mode=context.bf_mode,
            brute_crc=context.brute_crc,
            brute_length=context.brute_length,
            old_crc=context.old_crc,
            brute_level=context.brute_level,
            campaign_focus=context.campaign_focus,
        ),
        "plan": {
            "candidate_space_hash": candidate_hash,
            "backend": "opengl",
        },
        "cursor": {
            "outer_index": 0,
            "length": 2,
            "inner_index": 1,
            "byte_position": 0,
            "edit_kind_index": 0,
            "stage": "",
            "bonus_offset": 0,
            "bonus_value": 0,
        },
        "counters": {"tested_candidates": 17, "accepted_candidates": 0},
        "shards": [],
    }
    cpu_runtime = build_runtime(
        [],
        specs=simple_specs,
        product_values=[(7,), (8,)],
        source_hash="source-hash",
        resume_record=record,
        gpu_config=gpu_runtime.GpuRuntimeConfig(enabled=False),
    )

    resolved, warning = bruteforce_runtime._resolve_resume_record(
        cpu_runtime,
        context,
        runtime_plan,
        candidate_hash,
    )

    assert warning == ""
    assert resolved is record


def test_run_scan_gpu_no_hits_marks_pass_exhausted_without_cpu_fallback(monkeypatch):
    calls = []

    def gpu_explain(plan, config):
        calls.append(("gpu_explain", plan, config))
        return smash_opengl_backend.SmashOpenGLDecision(True, "OpenGL SBB path active.")

    def gpu_run(*args, **kwargs):
        calls.append(("gpu_run", args, kwargs))
        progress_callback = kwargs.get("progress_callback")
        if progress_callback is not None:
            progress_callback(64, 64)
        return smash_opengl_backend.OpenGLReplace1Result((), tested=64)

    monkeypatch.setattr(smash_opengl_backend, "explain", gpu_explain)
    monkeypatch.setattr(smash_opengl_backend, "run_scan", gpu_run)
    monkeypatch.setattr(
        bruteforce_runtime,
        "_run_parallel_scan",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("CPU fallback should not run")),
    )
    with tempfile.TemporaryDirectory() as directory:
        progress_path = str(Path(directory) / "_SBB.progress.json")
        runtime = build_runtime(
            calls,
            specs=simple_specs,
            product_values=[],
            progress_path=progress_path,
            source_hash="source-hash",
            gpu_config=gpu_runtime.GpuRuntimeConfig(enabled=True),
        )
        context = base_context(
            chunk_name=b"IDAT",
            bf_mode="TwoBytes",
            old_crc=b"\x00\x00\x00\x00",
        )

        result = bruteforce_runtime.run_scan(runtime, context)
        record = json.loads(Path(progress_path).read_text(encoding="utf-8"))

    assert result.state.bingo is False
    assert record["status"] == "exhausted"
    assert record["backend"] == "opengl"
    assert any(call[0] == "gpu_run" for call in calls)
    assert any(call[0] == "loadingbar" and call[3] == 64 for call in calls)


def test_run_scan_gpu_no_hits_at_deep_level_continues_to_cpu_bonus(monkeypatch):
    calls = []

    def gpu_explain(plan, config):
        calls.append(("gpu_explain", plan, config))
        return smash_opengl_backend.SmashOpenGLDecision(True, "OpenGL SBB path active.")

    def gpu_run(*args, **kwargs):
        calls.append(("gpu_run", args, kwargs))
        return smash_opengl_backend.OpenGLReplace1Result(
            (),
            tested=64,
            covered_stage="direct",
            covered_full_cpu_space=False,
        )

    def cpu_parallel(*_args, **_kwargs):
        calls.append(("cpu_parallel",))
        return True

    monkeypatch.setattr(smash_opengl_backend, "explain", gpu_explain)
    monkeypatch.setattr(smash_opengl_backend, "run_scan", gpu_run)
    monkeypatch.setattr(bruteforce_runtime, "_run_parallel_scan", cpu_parallel)
    with tempfile.TemporaryDirectory() as directory:
        progress_path = str(Path(directory) / "_SBB.progress.json")
        runtime = build_runtime(
            calls,
            specs=simple_specs,
            product_values=[],
            progress_path=progress_path,
            source_hash="source-hash",
            gpu_config=gpu_runtime.GpuRuntimeConfig(enabled=True),
        )
        context = base_context(
            chunk_name=b"IDAT",
            bf_mode="TwoBytes",
            old_crc=b"\x00\x00\x00\x00",
            brute_level=1,
        )

        bruteforce_runtime.run_scan(runtime, context)
        record = json.loads(Path(progress_path).read_text(encoding="utf-8"))

    assert ("cpu_parallel",) in calls
    assert record["status"] == "running"
    assert record["backend"] == "opengl"
    assert any(
        call[0] == "emit" and "OpenGL direct pass exhausted; continuing with CPU bonus stages" in call[1]
        for call in calls
    )


def test_run_scan_gpu_direct_resume_passes_saved_cursor(monkeypatch):
    calls = []
    context = base_context(chunk_name=b"IDAT", bf_mode="TwoBytes", old_crc="00000000")
    setup_runtime = build_runtime(
        [],
        specs=simple_specs,
        product_values=[],
        source_hash="source-hash",
    )
    runtime_plan = bruteforce_runtime.prepare_runtime_plan(setup_runtime, context)
    candidate_hash = smash_checkpoint.candidate_space_hash(
        bruteforce_runtime._candidate_space_payload(
            context,
            runtime_plan,
            source_hash="source-hash",
        )
    )
    record = {
        "status": "running",
        "backend": "opengl",
        "source_hash": "source-hash",
        "invocation": smash_checkpoint.invocation_record(
            file=context.file,
            chunk_name=context.chunk_name,
            chunk_length=context.chunk_length,
            data_offset=context.data_offset,
            from_error=context.from_error,
            edit_mode=context.edit_mode,
            bf_mode=context.bf_mode,
            brute_crc=context.brute_crc,
            brute_length=context.brute_length,
            old_crc=context.old_crc,
            brute_level=context.brute_level,
            campaign_focus=context.campaign_focus,
        ),
        "plan": {"candidate_space_hash": candidate_hash, "backend": "opengl"},
        "cursor": {
            "outer_index": 0,
            "length": 2,
            "inner_index": 3,
            "byte_position": 4,
            "edit_kind_index": 1,
            "stage": "direct",
            "bonus_offset": 0,
            "bonus_value": 0,
        },
        "counters": {"tested_candidates": 99, "accepted_candidates": 0},
        "shards": [],
    }

    def gpu_explain(plan, config):
        calls.append(("gpu_explain", plan, config))
        return smash_opengl_backend.SmashOpenGLDecision(True, "OpenGL SBB path active.")

    def gpu_run(*args, **kwargs):
        calls.append(("gpu_run", args, kwargs))
        return True

    monkeypatch.setattr(smash_opengl_backend, "explain", gpu_explain)
    monkeypatch.setattr(smash_opengl_backend, "run_scan", gpu_run)
    runtime = build_runtime(
        calls,
        specs=simple_specs,
        product_values=[],
        source_hash="source-hash",
        resume_record=record,
        gpu_config=gpu_runtime.GpuRuntimeConfig(enabled=True),
    )

    bruteforce_runtime.run_scan(runtime, context)

    gpu_call = next(call for call in calls if call[0] == "gpu_run")
    assert gpu_call[1][7] is record
    assert gpu_call[1][8] == 0
    assert gpu_call[1][9] == 3


def test_run_scan_gpu_bonus_resume_falls_back_to_cpu(monkeypatch):
    calls = []
    context = base_context(chunk_name=b"IDAT", bf_mode="TwoBytes", old_crc="00000000", brute_level=1)
    setup_runtime = build_runtime(
        [],
        specs=simple_specs,
        product_values=[],
        source_hash="source-hash",
    )
    runtime_plan = bruteforce_runtime.prepare_runtime_plan(setup_runtime, context)
    candidate_hash = smash_checkpoint.candidate_space_hash(
        bruteforce_runtime._candidate_space_payload(
            context,
            runtime_plan,
            source_hash="source-hash",
        )
    )
    record = {
        "status": "running",
        "backend": "opengl",
        "source_hash": "source-hash",
        "invocation": smash_checkpoint.invocation_record(
            file=context.file,
            chunk_name=context.chunk_name,
            chunk_length=context.chunk_length,
            data_offset=context.data_offset,
            from_error=context.from_error,
            edit_mode=context.edit_mode,
            bf_mode=context.bf_mode,
            brute_crc=context.brute_crc,
            brute_length=context.brute_length,
            old_crc=context.old_crc,
            brute_level=context.brute_level,
            campaign_focus=context.campaign_focus,
        ),
        "plan": {"candidate_space_hash": candidate_hash, "backend": "opengl"},
        "cursor": {
            "outer_index": 0,
            "length": 4,
            "inner_index": 0,
            "byte_position": 2,
            "edit_kind_index": 1,
            "stage": "bonus",
            "bonus_offset": 8,
            "bonus_value": 12,
        },
        "counters": {"tested_candidates": 99, "accepted_candidates": 0},
        "shards": [],
    }

    def gpu_explain(plan, config):
        calls.append(("gpu_explain", plan, config))
        return smash_opengl_backend.SmashOpenGLDecision(True, "OpenGL SBB path active.")

    def cpu_parallel(*_args, **_kwargs):
        calls.append(("cpu_parallel",))
        return True

    monkeypatch.setattr(smash_opengl_backend, "explain", gpu_explain)
    monkeypatch.setattr(bruteforce_runtime, "_run_parallel_scan", cpu_parallel)
    runtime = build_runtime(
        calls,
        specs=simple_specs,
        product_values=[],
        source_hash="source-hash",
        resume_record=record,
        gpu_config=gpu_runtime.GpuRuntimeConfig(enabled=True),
    )

    bruteforce_runtime.run_scan(runtime, context)

    assert ("cpu_parallel",) in calls
    assert any(
        call[0] == "emit" and "resume only direct stage" in call[1]
        for call in calls
    )


def test_gpu_keyboard_interrupt_writes_opengl_checkpoint(monkeypatch):
    calls = []

    def gpu_explain(plan, config):
        calls.append(("gpu_explain", plan, config))
        return smash_opengl_backend.SmashOpenGLDecision(True, "OpenGL SBB path active.")

    def gpu_run(*_args, **_kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(smash_opengl_backend, "explain", gpu_explain)
    monkeypatch.setattr(smash_opengl_backend, "run_scan", gpu_run)
    with tempfile.TemporaryDirectory() as directory:
        progress_path = str(Path(directory) / "_SBB.progress.json")
        runtime = build_runtime(
            calls,
            specs=simple_specs,
            product_values=[],
            progress_path=progress_path,
            source_hash="source-hash",
            gpu_config=gpu_runtime.GpuRuntimeConfig(enabled=True),
        )
        context = base_context(
            chunk_name=b"IDAT",
            bf_mode="TwoBytes",
            old_crc=b"\x00\x00\x00\x00",
        )

        try:
            bruteforce_runtime.run_scan(runtime, context)
        except smash_checkpoint.SmashBruteBrawlInterrupted:
            pass
        else:
            raise AssertionError("GPU interrupt should raise SmashBruteBrawlInterrupted")

        record = json.loads(Path(progress_path).read_text(encoding="utf-8"))

    assert record["status"] == "interrupted"
    assert record["backend"] == "opengl"
    assert record["plan"]["backend"] == "opengl"
    assert record["plan"]["candidate_space_hash"]


def test_deep_sbb_parallel_shards_stay_small_enough_for_heartbeat():
    twobytes_level_0 = base_context(chunk_name=b"IDAT", bf_mode="TwoBytes", brute_level=0)
    twobytes_level_1 = base_context(chunk_name=b"IDAT", bf_mode="TwoBytes", brute_level=1)
    brutus_level_0 = base_context(chunk_name=b"IDAT", bf_mode="Brutus", brute_level=0)
    brutus_level_7 = base_context(chunk_name=b"IDAT", bf_mode="Brutus", brute_level=7)

    assert (
        bruteforce_runtime._smash_parallel_shard_size(twobytes_level_0, "twobytes")
        == smash_backend.SMASH_TWOBYTES_SHARD_BYTE_SIZE
    )
    assert bruteforce_runtime._smash_parallel_shard_size(twobytes_level_1, "twobytes") == 64
    assert (
        bruteforce_runtime._smash_parallel_shard_size(brutus_level_0, "standard")
        == smash_backend.SMASH_PARALLEL_SHARD_SIZE
    )
    assert bruteforce_runtime._smash_parallel_shard_size(brutus_level_7, "standard") == 512


def test_run_scan_parallel_oldcrc_matches_serial_result(monkeypatch):
    accept_fake_sbb_candidates(monkeypatch)
    calls = []
    chunk_name = b"gAMA"
    old_crc = bruteforce.chunk_crc(chunk_name, b"\x07").hex()
    runtime = build_runtime(
        calls,
        specs=simple_specs,
        product_values=[(7,)],
        smash_workers=2,
    )

    result = bruteforce_runtime.run_scan(
        runtime,
        base_context(chunk_name=chunk_name, old_crc=old_crc),
    )

    assert result.state == bruteforce.BruteForceMatchState(
        bingo=True,
        replace_flag=True,
    )
    assert result.old_crc == bytes.fromhex(old_crc)
    assert result.full_new_data == (
        b"\x00\x00\x00\x01" + chunk_name + b"\x07" + bytes.fromhex(old_crc)
    )
    assert result.bf_mode == "Brutus"
    assert not [call for call in calls if call[0] == "show_candidate"]
    assert ("emit", "-SmashBruteBrawl will use 2 CPU workers.") in calls


def test_run_scan_parallel_custom_oldcrc_matches_serial_result(monkeypatch):
    accept_fake_sbb_candidates(monkeypatch)
    calls = []
    chunk_name = b"gAMA"
    old_crc = bruteforce.chunk_crc(chunk_name, b"\x07").hex()
    runtime = build_runtime(
        calls,
        specs=simple_specs,
        product_values=[(7,)],
        smash_workers=2,
    )

    result = bruteforce_runtime.run_scan(
        runtime,
        base_context(
            chunk_name=chunk_name,
            bf_mode="Custom",
            pandora_box={"gAMA StructIndex:0": True},
            old_crc=old_crc,
        ),
    )

    assert result.state == bruteforce.BruteForceMatchState(
        bingo=True,
        replace_flag=True,
    )
    assert result.full_new_data == (
        b"\x00\x00\x00\x01" + chunk_name + b"\x07" + bytes.fromhex(old_crc)
    )
    assert result.bf_mode == "Custom"
    assert ("emit", "-SmashBruteBrawl will use 2 CPU workers.") in calls


def test_run_scan_parallel_twobytes_uses_workers(monkeypatch):
    accept_fake_sbb_candidates(monkeypatch)
    calls = []
    chunk_name = b"gAMA"
    old_crc = bruteforce.chunk_crc(chunk_name, b"\x07").hex()
    runtime = build_runtime(
        calls,
        specs=simple_specs,
        product_values=[(7,)],
        smash_workers=2,
    )

    result = bruteforce_runtime.run_scan(
        runtime,
        base_context(
            chunk_name=chunk_name,
            chunk_length=1,
            data_hex="0011223300aabbccddeeff",
            bf_mode="TwoBytes",
            old_crc=old_crc,
        ),
    )

    assert result.state == bruteforce.BruteForceMatchState(
        bingo=True,
        replace_flag=True,
    )
    assert ("emit", "-SmashBruteBrawl will use 2 CPU workers.") in calls
    assert ("loadingbar", 1, 1, None, True) in calls
    assert not [call for call in calls if call[0] == "raw_print"]


def test_run_scan_parallel_twobytes_writes_twobytes_shards():
    calls = []
    chunk_name = b"gAMA"
    old_crc = bruteforce.chunk_crc(chunk_name, b"\x07").hex()
    with tempfile.TemporaryDirectory() as directory:
        progress_path = str(Path(directory) / "_SBB.progress.json")
        runtime = build_runtime(
            calls,
            specs=simple_specs,
            product_values=[(7,)],
            progress_path=progress_path,
            source_hash="source-hash",
            source_size=123,
            source_path="/tmp/_SBB.Source.raw",
            smash_workers=2,
        )

        bruteforce_runtime.run_scan(
            runtime,
            base_context(
                chunk_name=chunk_name,
                chunk_length=1,
                data_hex="0011223300aabbccddeeff",
                bf_mode="TwoBytes",
                old_crc=old_crc,
            ),
        )

        record = json.loads(Path(progress_path).read_text(encoding="utf-8"))

    assert record["backend"] == "cpu-parallel"
    assert record["shard_size"] == smash_backend.SMASH_TWOBYTES_SHARD_BYTE_SIZE
    twobytes_shards = [shard for shard in record["shards"] if shard["kind"] == "twobytes"]
    assert twobytes_shards
    assert {
        "inner_index",
        "byte_start",
        "byte_end",
        "next_byte_position",
        "edit_kind_index",
        "stage",
        "bonus_offset",
        "bonus_value",
    }.issubset(twobytes_shards[0])


def test_run_scan_parallel_first_sigint_announces_and_saves(monkeypatch):
    calls = []
    signal_state = {"current": "original", "handler": None}

    class FakeEvent:
        def __init__(self):
            self.was_set = False

        def set(self):
            self.was_set = True

        def is_set(self):
            return self.was_set

    class FakeManager:
        def __init__(self):
            self.event = FakeEvent()

        def Event(self):
            return self.event

        def Queue(self):
            class FakeQueue:
                def get_nowait(self):
                    raise RuntimeError("empty")

            return FakeQueue()

        def shutdown(self):
            calls.append(("manager_shutdown",))

    class FakeExecutor:
        def __init__(self, *, max_workers, initializer=None):
            calls.append(("executor_start", max_workers, initializer))

        def submit(self, *_args):
            future = bruteforce_runtime.concurrent.futures.Future()
            calls.append(("executor_submit",))
            return future

        def shutdown(self, *, wait, cancel_futures):
            calls.append(("executor_shutdown", wait, cancel_futures))

    def fake_getsignal(signum):
        assert signum == bruteforce_runtime.signal.SIGINT
        return signal_state["current"]

    def fake_signal(signum, handler):
        assert signum == bruteforce_runtime.signal.SIGINT
        calls.append(("signal", handler))
        signal_state["current"] = handler
        if handler not in (bruteforce_runtime.signal.SIG_IGN, "original"):
            signal_state["handler"] = handler

    def fake_wait(_pending, **_kwargs):
        signal_state["handler"](bruteforce_runtime.signal.SIGINT, None)
        return set(), set(_pending)

    monkeypatch.setattr(bruteforce_runtime.multiprocessing, "Manager", FakeManager)
    monkeypatch.setattr(bruteforce_runtime.concurrent.futures, "ProcessPoolExecutor", FakeExecutor)
    monkeypatch.setattr(bruteforce_runtime.concurrent.futures, "wait", fake_wait)
    monkeypatch.setattr(bruteforce_runtime.signal, "getsignal", fake_getsignal)
    monkeypatch.setattr(bruteforce_runtime.signal, "signal", fake_signal)

    chunk_name = b"gAMA"
    old_crc = bruteforce.chunk_crc(chunk_name, b"\x07").hex()
    with tempfile.TemporaryDirectory() as directory:
        progress_path = str(Path(directory) / "_SBB.progress.json")
        runtime = build_runtime(
            calls,
            specs=simple_specs,
            product_values=[(7,)],
            progress_path=progress_path,
            source_hash="source-hash",
            source_size=123,
            source_path="/tmp/_SBB.Source.raw",
            smash_workers=2,
        )

        try:
            bruteforce_runtime.run_scan(
                runtime,
                base_context(chunk_name=chunk_name, old_crc=old_crc),
            )
        except smash_checkpoint.SmashBruteBrawlInterrupted as exc:
            assert exc.progress_path == progress_path
        else:
            raise AssertionError("expected SmashBruteBrawlInterrupted")

        record = json.loads(Path(progress_path).read_text(encoding="utf-8"))

    assert any(
        call[0] == "emit" and "SmashBruteBrawl is stopping cleanly" in call[1]
        for call in calls
    )
    assert ("signal", bruteforce_runtime.signal.SIG_IGN) in calls
    assert ("signal", "original") in calls
    assert ("executor_start", 2, smash_backend.ignore_worker_sigint) in calls
    assert ("executor_shutdown", False, True) in calls
    assert ("manager_shutdown",) in calls
    assert record["backend"] == "cpu-parallel"
    assert record["counters"]["tested_candidates"] == 0


def test_smash_parallel_shutdown_terminates_processes_and_queue():
    class FakeStopEvent:
        def __init__(self):
            self.set_called = False

        def set(self):
            self.set_called = True

    class FakeProcess:
        def __init__(self):
            self.terminated = False
            self.join_timeout = None

        def poll(self):
            return None

        def terminate(self):
            self.terminated = True

        def join(self, timeout):
            self.join_timeout = timeout

    class FakeExecutor:
        def __init__(self, process):
            self._processes = {1: process}
            self.shutdown_args = None

        def shutdown(self, **kwargs):
            self.shutdown_args = kwargs

    class FakeQueue:
        def __init__(self):
            self.cancelled = False
            self.closed = False

        def get_nowait(self):
            raise RuntimeError("empty")

        def cancel_join_thread(self):
            self.cancelled = True

        def close(self):
            self.closed = True

    stop_event = FakeStopEvent()
    process = FakeProcess()
    executor = FakeExecutor(process)
    progress_queue = FakeQueue()

    bruteforce_runtime._shutdown_smash_parallel_executor(
        executor,
        progress_queue=progress_queue,
        stop_event=stop_event,
        grace_seconds=0.01,
    )

    assert stop_event.set_called is True
    assert executor.shutdown_args == {"wait": False, "cancel_futures": True}
    assert process.terminated is True
    assert process.join_timeout is not None
    assert progress_queue.cancelled is True
    assert progress_queue.closed is True


def test_twobytes_worker_bonus_path_has_brute_level(monkeypatch):
    monkeypatch.setattr(smash_backend, "_candidate_png_looks_valid", lambda _png_bytes: False)
    length_plan = smash_backend.SmashLengthPlan(
        outer_index=0,
        length=1,
        iter_nbr=None,
        max_iter=1,
        len_iter=1,
        chunk_format=("B",),
        chunk_data=((7,),),
        color_type="color",
    )
    plan = smash_backend.SmashCandidatePlan(
        chunk_name=b"gAMA",
        chunk_length=1,
        data_offset=8,
        data_hex="000000000700000000",
        edit_mode="Replace",
        bf_mode="TwoBytes",
        brute_level=1,
        brute_crc=True,
        brute_length=True,
        old_crc=False,
        struct_indexes=(),
        candidate_space_hash="hash",
        crc_trusted=False,
        lengths=(length_plan,),
    )
    shard = smash_backend.SmashShard(
        shard_id=0,
        length_plan_index=0,
        start_inner_index=0,
        end_inner_index=1,
        kind="twobytes",
        inner_index=0,
        byte_start=0,
        byte_end=1,
    )

    result = smash_backend.run_twobytes_shard(plan, shard)

    assert result.error == ""
    assert result.tested == 1
    assert result.hits == ()


def test_remove_worker_shard_matches_old_crc():
    chunk_name = b"IDAT"
    repaired_payload = bytes.fromhex("aacc")
    old_crc = bruteforce.chunk_crc(chunk_name, repaired_payload)
    length_plan = smash_backend.SmashLengthPlan(
        outer_index=0,
        length=2,
        iter_nbr=None,
        max_iter=3,
        len_iter=1,
        chunk_format=("B",),
        chunk_data=((0,),),
        color_type="color",
    )
    plan = smash_backend.SmashCandidatePlan(
        chunk_name=chunk_name,
        chunk_length=3,
        data_offset=0,
        data_hex="0000000349444154aabbccdeadbeef",
        edit_mode="Remove",
        bf_mode="Brutus",
        brute_level=0,
        brute_crc=True,
        brute_length=True,
        old_crc=old_crc,
        struct_indexes=(),
        candidate_space_hash="hash",
        crc_trusted=True,
        lengths=(length_plan,),
    )
    shard = smash_backend.SmashShard(
        shard_id=0,
        length_plan_index=0,
        start_inner_index=0,
        end_inner_index=3,
        kind="remove",
    )

    result = smash_backend.run_remove_shard(plan, shard)

    assert result.error == ""
    assert result.hits
    assert result.hits[0].inner_index == 1
    assert result.hits[0].edit_kind == "remove"
    assert result.hits[0].full_new_data == (
        b"\x00\x00\x00\x02" + chunk_name + repaired_payload + old_crc
    )


def test_twobytes_remove_worker_repairs_extra_idat_byte_fixture():
    data = (ROOT / "Png_Errors_handled_by_Chunklate_So_Far" / "SBB_IDAT_1Byte_Extra.png").read_bytes()
    idat_chunk = next(chunk for chunk in iter_chunks(data) if chunk.chunk_type == b"IDAT")
    old_crc = idat_chunk.crc.to_bytes(4, "big")
    length_plan = smash_backend.SmashLengthPlan(
        outer_index=0,
        length=1,
        iter_nbr=None,
        max_iter=1,
        len_iter=1,
        chunk_format=("B",),
        chunk_data=((0,),),
        color_type="color",
    )
    plan = smash_backend.SmashCandidatePlan(
        chunk_name=b"IDAT",
        chunk_length=idat_chunk.length,
        data_offset=(idat_chunk.offset + 8) * 2,
        data_hex=data.hex(),
        edit_mode="Remove",
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
    shard = smash_backend.SmashShard(
        shard_id=0,
        length_plan_index=0,
        start_inner_index=0,
        end_inner_index=1,
        kind="twobytes",
        inner_index=0,
        byte_start=0,
        byte_end=idat_chunk.length,
    )

    result = smash_backend.run_twobytes_shard(plan, shard)

    assert result.error == ""
    assert result.hits
    assert result.hits[0].edit_kind == "remove"
    assert result.hits[0].old_crc_match is True
    assert result.hits[0].full_new_data[:8] == b"\x00\x00\x00\xd3IDAT"


def test_twobytes_shard_record_round_trips_resume_cursor():
    shard = smash_backend.SmashShard(
        shard_id=7,
        length_plan_index=2,
        start_inner_index=5,
        end_inner_index=6,
        kind="twobytes",
        inner_index=5,
        byte_start=12,
        byte_end=24,
        next_byte_position=16,
        edit_kind_index=1,
        stage="bonus",
        bonus_offset=8,
        bonus_value=42,
    )
    result = smash_backend.SmashShardResult(
        shard=shard,
        tested=123,
        next_inner_index=5,
        stopped=True,
        next_byte_position=18,
        edit_kind_index=2,
        stage="direct",
        bonus_offset=10,
        bonus_value=99,
    )

    record = smash_backend.shard_record(shard, result)
    restored = smash_backend.shard_from_record(record)

    assert record["kind"] == "twobytes"
    assert record["status"] == "pending"
    assert record["tested"] == 123
    assert restored.kind == "twobytes"
    assert restored.inner_index == 5
    assert restored.byte_start == 12
    assert restored.byte_end == 24
    assert restored.next_byte_position == 18
    assert restored.edit_kind_index == 2
    assert restored.stage == "direct"
    assert restored.bonus_offset == 10
    assert restored.bonus_value == 99


def test_parallel_twobytes_remaining_estimate_counts_edit_kinds_after_resume():
    length_plan = smash_backend.SmashLengthPlan(
        outer_index=0,
        length=1,
        iter_nbr=None,
        max_iter=1,
        len_iter=1,
        chunk_format=("B",),
        chunk_data=((7,),),
        color_type="color",
    )
    plan = smash_backend.SmashCandidatePlan(
        chunk_name=b"IDAT",
        chunk_length=1,
        data_offset=8,
        data_hex="000000000700000000",
        edit_mode="Replace",
        bf_mode="TwoBytes",
        brute_level=0,
        brute_crc=True,
        brute_length=True,
        old_crc=False,
        struct_indexes=(),
        candidate_space_hash="hash",
        crc_trusted=False,
        lengths=(length_plan,),
    )
    shard = smash_backend.SmashShard(
        shard_id=0,
        length_plan_index=0,
        start_inner_index=0,
        end_inner_index=1,
        kind="twobytes",
        inner_index=0,
        byte_start=0,
        byte_end=10,
        next_byte_position=2,
        edit_kind_index=1,
    )

    remaining = bruteforce_runtime._estimate_parallel_remaining_candidates(plan, [shard])

    assert remaining == 23


def test_run_scan_preserves_viewer_acceptance_gate_and_diff(monkeypatch):
    accept_fake_sbb_candidates(monkeypatch)
    calls = []

    def specs(request):
        if request.fields:
            return (2, ("B",))
        return (2, 2, 2, ("B",), [(1,), (2,)], "color")

    runtime = build_runtime(
        calls,
        specs=specs,
        product_values=[(1,), (2,)],
        viewer_results=[
            bruteforce_viewer.BruteForceViewerResult(False),
            bruteforce_viewer.BruteForceViewerResult(True, "accepted-diff"),
        ],
    )

    result = bruteforce_runtime.run_scan(runtime, base_context())

    assert result.state == bruteforce.BruteForceMatchState(
        bingo=True,
        replace_flag=True,
    )
    assert result.diff == "accepted-diff"
    assert result.full_new_data.startswith(b"\x00\x00\x00\x01gAMA\x02")
    assert [call[0] for call in calls].count("show_candidate") == 2
    assert ("loadingbar", 2, 2, 0, False) in calls
    assert ("loadingbar", 2, 2, 1, False) in calls


def test_run_scan_preserves_twobytes_oldcrc_path(monkeypatch):
    accept_fake_sbb_candidates(monkeypatch)
    calls = []
    chunk_name = b"gAMA"
    old_crc = bruteforce.chunk_crc(chunk_name, b"\x07").hex()
    runtime = build_runtime(calls, specs=simple_specs, product_values=[(7,)])

    result = bruteforce_runtime.run_scan(
        runtime,
        base_context(
            chunk_name=chunk_name,
            chunk_length=1,
            data_hex="0011223300aabbccddeeff",
            bf_mode="TwoBytes",
            old_crc=old_crc,
        ),
    )

    assert result.state == bruteforce.BruteForceMatchState(
        bingo=True,
        replace_flag=True,
    )
    assert result.full_new_data == (
        b"\x00\x00\x00\x01" + chunk_name + b"\x07" + bytes.fromhex(old_crc)
    )
    assert result.to_brute == "00"
    assert [call[0] for call in calls].count("show_candidate") == 0
    assert ("minibar", {"Indication": "0/2"}) not in calls
    assert (
        "raw_print",
        ("0/2 byte 1/1 .\033[K",),
        {"end": "\r", "flush": True},
    ) in calls


def test_run_scan_records_rejected_hit_for_crc_match_with_invalid_png():
    calls = []
    chunk_name = b"gAMA"
    old_crc = bruteforce.chunk_crc(chunk_name, b"\x07").hex()
    with tempfile.TemporaryDirectory() as directory:
        progress_path = str(Path(directory) / "_SBB.progress.json")
        runtime = build_runtime(
            calls,
            specs=simple_specs,
            product_values=[(7,)],
            progress_path=progress_path,
            source_hash="source-hash",
            source_size=123,
            source_path="/tmp/_SBB.Source.raw",
        )

        result = bruteforce_runtime.run_scan(
            runtime,
            base_context(chunk_name=chunk_name, old_crc=old_crc),
        )

        record = json.loads(Path(progress_path).read_text(encoding="utf-8"))

    assert result.state.bingo is False
    assert record["status"] == "rejected_hit"
    assert record["plan"]["status"] == "rejected_hit"
    assert record["counters"]["accepted_candidates"] == 0
    assert record["counters"]["rejected_candidates"] == 1
    assert not [call for call in calls if call[0] == "show_candidate"]
    assert record["counters"]["first_rejection_reason"]
    assert record["counters"]["rejection_reasons"]
    assert not [
        call for call in calls
        if call[0] == "emit" and "SBB rejected" in call[1]
    ]


def test_twobytes_progress_dots_line_fills_and_returns():
    prefix = "0/256 byte 1/149210 "
    start = bruteforce_runtime.twobytes_progress_dots_line(
        prefix,
        position=0,
        terminal_width=len(prefix) + 6,
    )
    filled = bruteforce_runtime.twobytes_progress_dots_line(
        prefix,
        position=4 * 1024,
        terminal_width=len(prefix) + 6,
    )
    returning = bruteforce_runtime.twobytes_progress_dots_line(
        prefix,
        position=7 * 1024,
        terminal_width=len(prefix) + 6,
    )

    assert start == prefix + ".\033[K"
    assert filled == prefix + ".....\033[K"
    assert returning == prefix + "...\033[K"


def test_twobytes_progress_dots_line_clamps_to_short_terminal_width():
    assert bruteforce_runtime.twobytes_progress_dots_line(
        "0/256 byte 1/149210 ",
        position=0,
        terminal_width=5,
    ) == "0/256 byte 1/149210 \033[K"


def test_run_scan_preserves_crash_resume_skip_and_reset(monkeypatch):
    accept_fake_sbb_candidates(monkeypatch)
    calls = []
    chunk_name = b"gAMA"
    old_crc = bruteforce.chunk_crc(chunk_name, b"\x08").hex()
    runtime = build_runtime(calls, specs=simple_specs, product_values=[(7,), (8,)])

    result = bruteforce_runtime.run_scan(
        runtime,
        base_context(chunk_name=chunk_name, old_crc=old_crc, crash=1),
    )

    assert result.state == bruteforce.BruteForceMatchState(
        bingo=True,
        replace_flag=True,
    )
    assert result.crash is False
    assert result.full_new_data == (
        b"\x00\x00\x00\x01" + chunk_name + b"\x08" + bytes.fromhex(old_crc)
    )
    assert ("loadingbar", 2, 1, 0, False) not in calls
    assert ("loadingbar", 2, 1, 1, False) in calls


def test_run_scan_supports_idat_brutus_remove_with_old_crc(monkeypatch):
    accept_fake_sbb_candidates(monkeypatch)
    calls = []
    chunk_name = b"IDAT"
    repaired_payload = bytes.fromhex("aacc")
    old_crc = bruteforce.chunk_crc(chunk_name, repaired_payload).hex()
    runtime = build_runtime(calls, specs=simple_specs, product_values=[])

    result = bruteforce_runtime.run_scan(
        runtime,
        base_context(
            chunk_name=chunk_name,
            chunk_length=3,
            data_offset=0,
            data_hex="0000000349444154aabbccdeadbeef",
            edit_mode="Remove",
            bf_mode="Brutus",
            old_crc=old_crc,
        ),
    )

    assert result.state == bruteforce.BruteForceMatchState(
        bingo=True,
        remove_flag=True,
    )
    assert result.full_new_data == (
        b"\x00\x00\x00\x02" + chunk_name + repaired_payload + bytes.fromhex(old_crc)
    )
    assert result.to_brute == "aabbcc"


def test_run_scan_writes_smash_progress_checkpoint():
    calls = []
    chunk_name = b"gAMA"
    old_crc = bruteforce.chunk_crc(chunk_name, b"\x08").hex()
    with tempfile.TemporaryDirectory() as directory:
        progress_path = str(Path(directory) / "_SBB.progress.json")
        runtime = build_runtime(
            calls,
            specs=simple_specs,
            product_values=[(7,), (8,)],
            progress_path=progress_path,
            source_hash="source-hash",
            source_size=123,
            source_path="/tmp/_SBB.Source.raw",
        )

        bruteforce_runtime.run_scan(
            runtime,
            base_context(chunk_name=chunk_name, old_crc=old_crc),
        )

        record = json.loads(Path(progress_path).read_text(encoding="utf-8"))

    assert record["source_hash"] == "source-hash"
    assert record["source_size"] == 123
    assert record["invocation"]["chunk_name_hex"] == chunk_name.hex()
    assert record["invocation"]["old_crc"] == old_crc
    assert record["cursor"]["outer_index"] == 0
    assert record["cursor"]["inner_index"] == 1
    assert record["counters"]["tested_candidates"] == 2
    assert record["plan"]["candidate_space_hash"]


def test_run_scan_resumes_from_saved_inner_index_when_space_matches(monkeypatch):
    accept_fake_sbb_candidates(monkeypatch)
    calls = []
    chunk_name = b"gAMA"
    old_crc = bruteforce.chunk_crc(chunk_name, b"\x08").hex()
    with tempfile.TemporaryDirectory() as directory:
        progress_path = str(Path(directory) / "_SBB.progress.json")
        first_runtime = build_runtime(
            calls,
            specs=simple_specs,
            product_values=[(7,), (8,)],
            progress_path=progress_path,
            source_hash="source-hash",
            source_size=123,
            source_path="/tmp/_SBB.Source.raw",
        )
        context = base_context(chunk_name=chunk_name, old_crc=old_crc)

        bruteforce_runtime.run_scan(first_runtime, context)
        resume_record = json.loads(Path(progress_path).read_text(encoding="utf-8"))
        resume_record["status"] = "running"
        resume_record["plan"]["status"] = "running"

        calls.clear()
        second_runtime = build_runtime(
            calls,
            specs=simple_specs,
            product_values=[(7,), (8,)],
            progress_path=progress_path,
            source_hash="source-hash",
            source_size=123,
            source_path="/tmp/_SBB.Source.raw",
            resume_record=resume_record,
        )

        result = bruteforce_runtime.run_scan(second_runtime, context)

    assert result.state == bruteforce.BruteForceMatchState(
        bingo=True,
        replace_flag=True,
    )
    assert ("loadingbar", 2, 1, 0, False) not in calls
    assert ("loadingbar", 2, 1, 1, False) in calls
    assert any(
        call == ("emit", "-SmashBruteBrawl resume checkpoint accepted at outer 0, inner 1.")
        for call in calls
    )


def test_run_scan_restarts_when_campaign_focus_changes():
    calls = []
    chunk_name = b"gAMA"
    old_crc = bruteforce.chunk_crc(chunk_name, b"\x08").hex()
    with tempfile.TemporaryDirectory() as directory:
        progress_path = str(Path(directory) / "_SBB.progress.json")
        first_runtime = build_runtime(
            calls,
            specs=simple_specs,
            product_values=[(7,), (8,)],
            progress_path=progress_path,
            source_hash="source-hash",
        )
        first_context = base_context(
            chunk_name=chunk_name,
            old_crc=old_crc,
            campaign_focus="remove",
        )
        bruteforce_runtime.run_scan(first_runtime, first_context)
        resume_record = json.loads(Path(progress_path).read_text(encoding="utf-8"))
        resume_record["status"] = "running"
        resume_record["plan"]["status"] = "running"

        calls.clear()
        next_runtime = build_runtime(
            calls,
            specs=simple_specs,
            product_values=[(7,), (8,)],
            progress_path=progress_path,
            source_hash="source-hash",
            resume_record=resume_record,
        )
        next_context = base_context(
            chunk_name=chunk_name,
            old_crc=old_crc,
            campaign_focus="replace",
        )
        bruteforce_runtime.run_scan(next_runtime, next_context)

    assert any(
        call[0] == "emit" and "does not match this chunk run" in call[1]
        for call in calls
    )
    assert ("loadingbar", 2, 1, 0, False) in calls


def test_run_scan_restarts_when_brute_level_increases_search_space():
    calls = []
    chunk_name = b"gAMA"
    old_crc = bruteforce.chunk_crc(chunk_name, b"\x08").hex()
    with tempfile.TemporaryDirectory() as directory:
        progress_path = str(Path(directory) / "_SBB.progress.json")
        runtime = build_runtime(
            calls,
            specs=simple_specs,
            product_values=[(7,), (8,)],
            progress_path=progress_path,
            source_hash="source-hash",
        )
        bruteforce_runtime.run_scan(
            runtime,
            base_context(chunk_name=chunk_name, old_crc=old_crc, brute_level=0),
        )
        resume_record = json.loads(Path(progress_path).read_text(encoding="utf-8"))
        resume_record["status"] = "running"
        resume_record["plan"]["status"] = "running"

        calls.clear()
        next_runtime = build_runtime(
            calls,
            specs=simple_specs,
            product_values=[(7,), (8,)],
            progress_path=progress_path,
            source_hash="source-hash",
            resume_record=resume_record,
        )
        bruteforce_runtime.run_scan(
            next_runtime,
            base_context(chunk_name=chunk_name, old_crc=old_crc, brute_level=1),
        )

    assert ("loadingbar", 2, 1, 0, False) in calls
    assert any(
        call[0] == "emit"
        and "BruteLevel increased from 0 to 1" in call[1]
        for call in calls
    )


def test_parallel_exhausted_checkpoint_is_not_resumed():
    calls = []
    chunk_name = b"gAMA"
    with tempfile.TemporaryDirectory() as directory:
        progress_path = str(Path(directory) / "_SBB.progress.json")
        runtime = build_runtime(
            calls,
            specs=simple_specs,
            product_values=[(7,), (8,)],
            progress_path=progress_path,
            source_hash="source-hash",
            source_size=123,
            source_path="/tmp/_SBB.Source.raw",
            smash_workers=2,
        )
        context = base_context(chunk_name=chunk_name, old_crc="00000000")

        bruteforce_runtime.run_scan(runtime, context)
        resume_record = json.loads(Path(progress_path).read_text(encoding="utf-8"))

        assert resume_record["status"] == "exhausted"

        calls.clear()
        next_runtime = build_runtime(
            calls,
            specs=simple_specs,
            product_values=[(7,), (8,)],
            progress_path=progress_path,
            source_hash="source-hash",
            source_size=123,
            source_path="/tmp/_SBB.Source.raw",
            resume_record=resume_record,
            smash_workers=2,
        )
        bruteforce_runtime.run_scan(next_runtime, context)

    assert any(
        call[0] == "emit" and "already marked exhausted" in call[1]
        for call in calls
    )


def test_rejected_hit_checkpoint_is_not_resumed():
    calls = []
    chunk_name = b"gAMA"
    old_crc = bruteforce.chunk_crc(chunk_name, b"\x07").hex()
    with tempfile.TemporaryDirectory() as directory:
        progress_path = str(Path(directory) / "_SBB.progress.json")
        runtime = build_runtime(
            calls,
            specs=simple_specs,
            product_values=[(7,)],
            progress_path=progress_path,
            source_hash="source-hash",
            source_size=123,
            source_path="/tmp/_SBB.Source.raw",
        )
        context = base_context(chunk_name=chunk_name, old_crc=old_crc)

        bruteforce_runtime.run_scan(runtime, context)
        resume_record = json.loads(Path(progress_path).read_text(encoding="utf-8"))
        assert resume_record["status"] == "rejected_hit"

        calls.clear()
        accept_runtime = build_runtime(
            calls,
            specs=simple_specs,
            product_values=[(7,)],
            progress_path=progress_path,
            source_hash="source-hash",
            source_size=123,
            source_path="/tmp/_SBB.Source.raw",
            resume_record=resume_record,
        )
        bruteforce_runtime.run_scan(accept_runtime, context)

    assert any(
        call[0] == "emit" and "already marked rejected_hit" in call[1]
        for call in calls
    )


def main():
    checks = [
        ("OldCrc scan", test_run_scan_preserves_oldcrc_path_without_viewer),
        ("Viewer scan", test_run_scan_preserves_viewer_acceptance_gate_and_diff),
        ("TwoBytes scan", test_run_scan_preserves_twobytes_oldcrc_path),
        ("TwoBytes dots", test_twobytes_progress_dots_line_fills_and_returns),
        ("TwoBytes short terminal", test_twobytes_progress_dots_line_clamps_to_short_terminal_width),
        ("Remove worker shard", test_remove_worker_shard_matches_old_crc),
        ("TwoBytes Remove extra IDAT fixture", test_twobytes_remove_worker_repairs_extra_idat_byte_fixture),
        ("Worker profiles", test_resolve_smash_worker_profiles),
        ("Parallel progress finished shard records", test_parallel_progress_records_finished_out_of_order_shards),
        ("Parallel Ctrl+C shutdown", test_run_scan_parallel_first_sigint_announces_and_saves),
        ("Parallel shutdown terminates", test_smash_parallel_shutdown_terminates_processes_and_queue),
        ("Parallel stale empty checkpoint", test_empty_pending_parallel_checkpoint_is_rejected_as_stale),
        ("Serial stale empty checkpoint", test_empty_serial_interrupted_checkpoint_is_rejected_as_stale),
        ("Deep SBB shard sizing", test_deep_sbb_parallel_shards_stay_small_enough_for_heartbeat),
        ("Crash resume", test_run_scan_preserves_crash_resume_skip_and_reset),
        ("IDAT Brutus Remove", test_run_scan_supports_idat_brutus_remove_with_old_crc),
        ("Smash progress checkpoint", test_run_scan_writes_smash_progress_checkpoint),
        ("Smash resume inner cursor", test_run_scan_resumes_from_saved_inner_index_when_space_matches),
        ("Smash resume focus mismatch", test_run_scan_restarts_when_campaign_focus_changes),
        ("Smash higher BruteLevel restart", test_run_scan_restarts_when_brute_level_increases_search_space),
        ("Parallel exhausted checkpoint", test_parallel_exhausted_checkpoint_is_not_resumed),
        ("Rejected hit checkpoint", test_rejected_hit_checkpoint_is_not_resumed),
    ]

    print("Running bruteforce runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        if "monkeypatch" in inspect.signature(check).parameters:
            monkeypatch = MonkeyPatch()
            try:
                check(monkeypatch)
            finally:
                monkeypatch.undo()
        else:
            check()
        print("ok")

    print(f"bruteforce runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
