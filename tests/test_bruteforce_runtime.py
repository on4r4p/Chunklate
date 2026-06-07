#!/usr/bin/env python3
import json
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import bruteforce, bruteforce_runtime, bruteforce_viewer, smash_backend, smash_checkpoint
from chunklate.png import iter_chunks


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


def test_run_scan_preserves_oldcrc_path_without_viewer():
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


def test_run_scan_parallel_oldcrc_matches_serial_result():
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


def test_run_scan_parallel_custom_oldcrc_matches_serial_result():
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


def test_run_scan_parallel_twobytes_uses_workers():
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

        def shutdown(self):
            calls.append(("manager_shutdown",))

    class FakeExecutor:
        def __init__(self, *, max_workers):
            calls.append(("executor_start", max_workers))

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
    assert ("executor_shutdown", True, True) in calls
    assert ("manager_shutdown",) in calls
    assert record["backend"] == "cpu-parallel"
    assert record["counters"]["tested_candidates"] == 0


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


def test_run_scan_preserves_viewer_acceptance_gate_and_diff():
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


def test_run_scan_preserves_twobytes_oldcrc_path():
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


def test_run_scan_preserves_crash_resume_skip_and_reset():
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


def test_run_scan_supports_idat_brutus_remove_with_old_crc():
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


def test_run_scan_resumes_from_saved_inner_index_when_space_matches():
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
        ("Parallel stale empty checkpoint", test_empty_pending_parallel_checkpoint_is_rejected_as_stale),
        ("Crash resume", test_run_scan_preserves_crash_resume_skip_and_reset),
        ("IDAT Brutus Remove", test_run_scan_supports_idat_brutus_remove_with_old_crc),
        ("Smash progress checkpoint", test_run_scan_writes_smash_progress_checkpoint),
        ("Smash resume inner cursor", test_run_scan_resumes_from_saved_inner_index_when_space_matches),
        ("Smash higher BruteLevel restart", test_run_scan_restarts_when_brute_level_increases_search_space),
        ("Parallel exhausted checkpoint", test_parallel_exhausted_checkpoint_is_not_resumed),
    ]

    print("Running bruteforce runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"bruteforce runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
