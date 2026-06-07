from __future__ import annotations

from collections.abc import Callable, MutableSequence
import concurrent.futures
from dataclasses import dataclass
from datetime import datetime, timedelta
import multiprocessing
import signal
import shutil
import time
from typing import Any

from . import bruteforce, smash_backend, smash_checkpoint


LegacyCall = Callable[..., Any]
SBB_CANDIDATE_ALGORITHM_VERSION = 2


@dataclass(frozen=True)
class SmashBruteBrawlContext:
    file: Any
    chunk_name: bytes
    chunk_length: int
    data_offset: int
    from_error: Any
    data_hex: str
    pandora_box: Any
    edit_mode: str = "Replace"
    bf_mode: str = "Brutus"
    brute_crc: bool = True
    brute_length: bool = True
    old_crc: Any = False
    brute_level: int = 0
    crash: Any = False
    debug: bool = False
    pause_debug: bool = False


@dataclass(frozen=True)
class SmashBruteBrawlRuntime:
    load_spec: LegacyCall
    product: LegacyCall
    loadingbar: LegacyCall
    minibar: LegacyCall
    show_candidate: LegacyCall
    emit: LegacyCall
    pause: LegacyCall
    side_notes: MutableSequence[Any]
    raw_print: LegacyCall = print
    now: LegacyCall = datetime.now
    progress_path: str = ""
    source_hash: str = ""
    source_size: int = 0
    source_path: str = ""
    resume_record: dict[str, Any] | None = None
    smash_workers: str | int | None = 0


@dataclass(frozen=True)
class SmashBruteBrawlScanResult:
    state: bruteforce.BruteForceMatchState
    old_crc: Any
    bf_mode: str
    full_new_data: bytes
    png_bytes: bytes
    to_brute: str
    diff: str
    crash: Any
    eta_seconds: int


@dataclass
class SmashBruteBrawlScanState:
    state: bruteforce.BruteForceMatchState
    full_new_data: bytes = b""
    png_bytes: bytes = b""
    to_brute: str = ""
    diff: str = ""
    crash: Any = False
    eta_seconds: int = 0
    tested_candidates: int = 0
    accepted_candidates: int = 0
    outer_index: int = 0
    length: int = 0
    inner_index: int = 0
    byte_position: int = 0
    edit_kind_index: int = 0
    stage: str = ""
    bonus_offset: int = 0
    bonus_value: int = 0
    last_progress_write_at: float = 0.0


TWOBYTES_PROGRESS_DOT_STEP = 1024


def twobytes_progress_dots_line(
    prefix: str,
    *,
    position: int,
    terminal_width: int | None = None,
) -> str:
    width = terminal_width or shutil.get_terminal_size((80, 20)).columns
    available = max(0, width - len(prefix) - 1)
    if available <= 0:
        return "%s\033[K" % prefix
    cycle = available * 2
    phase = (max(position, 0) // TWOBYTES_PROGRESS_DOT_STEP) % cycle
    dot_count = phase + 1 if phase < available else cycle - phase
    return "%s%s\033[K" % (prefix, "." * max(1, dot_count))


def emit_debug_report(
    runtime: SmashBruteBrawlRuntime,
    context: SmashBruteBrawlContext,
    *,
    chunklen_spec: Any,
    chunk_format: Any,
    chunk_data: Any,
    max_iter: int,
    maxchunklen: int,
    minchunklen: int,
    step: int,
) -> None:
    runtime.emit("File:%s" % context.file)
    runtime.emit("ChunkName:%s" % context.chunk_name)
    runtime.emit("DataOffset:%s" % context.data_offset)
    runtime.emit("ChunkLength:%s" % context.chunk_length)
    runtime.emit("Brute_LvL:%s" % context.brute_level)
    runtime.emit("BruteCrc:%s" % context.brute_crc)
    runtime.emit("BruteLength:%s" % context.brute_length)
    runtime.emit("EditMode:%s" % context.edit_mode)
    runtime.emit("FromError:%s" % context.from_error)
    runtime.emit("chunklen_spec:%s" % str(chunklen_spec))
    runtime.emit("chunk_format:%s" % str(chunk_format))
    runtime.emit("chunk_data:%s" % str(chunk_data))
    runtime.emit("max_iter:%s" % max_iter)
    runtime.emit("maxchunklen:%s" % maxchunklen)
    runtime.emit("minchunklen:%s" % minchunklen)
    runtime.emit("step:%s" % step)
    if context.pause_debug is True:
        runtime.pause("Pause:SmashBruteBrawl")


def build_attempt(
    context: SmashBruteBrawlContext,
    old_crc: Any,
    length_bytes: bytes,
    payload_data: bytes,
    crc_data: bytes,
    before: bytes,
    after: bytes,
) -> bruteforce.BruteForceCandidateAttempt:
    return bruteforce.prepare_candidate_attempt(
        context.chunk_name,
        length_bytes,
        payload_data,
        crc_data,
        before,
        after,
        brute_length=context.brute_length,
        brute_crc=context.brute_crc,
        old_crc=old_crc,
    )


def prepare_runtime_plan(
    runtime: SmashBruteBrawlRuntime,
    context: SmashBruteBrawlContext,
) -> bruteforce.BruteForceRuntimePlan:
    runtime_plan = bruteforce.prepare_runtime_plan(
        context.bf_mode,
        context.chunk_name,
        context.pandora_box,
        runtime.load_spec,
    )
    runtime_plan = bruteforce.apply_idat_brutus_level(
        runtime_plan,
        context.chunk_name,
        context.brute_level,
    )
    if runtime_plan.side_note is not None:
        runtime.side_notes.append(runtime_plan.side_note)
    return runtime_plan


def emit_debug_report_if_needed(
    runtime: SmashBruteBrawlRuntime,
    context: SmashBruteBrawlContext,
    runtime_plan: bruteforce.BruteForceRuntimePlan,
) -> None:
    if context.debug is True:
        length_range = runtime_plan.length_range
        max_iter, _len_iter, chunklen_spec, chunk_format, chunk_data, color_type = (
            bruteforce.load_iteration_spec(
                runtime_plan.mode,
                runtime_plan.struct_indexes,
                None,
                runtime.load_spec,
            )
        )
        emit_debug_report(
            runtime,
            context,
            chunklen_spec=chunklen_spec,
            chunk_format=chunk_format,
            chunk_data=chunk_data,
            max_iter=max_iter,
            maxchunklen=length_range.max_length,
            minchunklen=length_range.min_length,
            step=length_range.step,
        )


def validate_candidate_attempt(
    runtime: SmashBruteBrawlRuntime,
    scan_state: SmashBruteBrawlScanState,
    old_crc: Any,
    attempt: bruteforce.BruteForceCandidateAttempt,
    *,
    loop_index: int,
    brute_bytes: bytes,
    edit_kind: str | None = None,
    bonus: bool = False,
) -> bool:
    scan_state.tested_candidates += 1
    viewer_ok = True
    if not old_crc:
        scan_state.full_new_data = attempt.full_new_data
        scan_state.png_bytes = attempt.png_bytes
        viewer_result = runtime.show_candidate(
            scan_state.png_bytes,
            scan_state.full_new_data,
            loop_index,
            brute_bytes,
        )
        viewer_ok = viewer_result.accepted
        if viewer_result.accepted:
            scan_state.diff = viewer_result.diff

    applied_attempt = bruteforce.apply_validated_candidate_attempt(
        scan_state.state,
        attempt,
        edit_kind,
        bonus=bonus,
        old_crc=old_crc,
        viewer_ok=viewer_ok,
    )
    if applied_attempt is None:
        return False

    scan_state.accepted_candidates += 1
    scan_state.state = applied_attempt.state
    scan_state.full_new_data = applied_attempt.full_new_data
    scan_state.png_bytes = applied_attempt.png_bytes
    return True


def _record_value(record: dict[str, Any], key: str, default: Any = None) -> Any:
    try:
        return record.get(key, default)
    except AttributeError:
        return default


def _record_int(record: dict[str, Any], key: str, default: int = 0) -> int:
    try:
        value = _record_value(record, key, default)
        if value in (None, ""):
            value = default
        return int(value)
    except (TypeError, ValueError):
        return default


def _length_range_record(length_range: bruteforce.BruteForceLengthRange) -> dict[str, int]:
    return {
        "min_length": int(length_range.min_length),
        "max_length": int(length_range.max_length),
        "step": int(length_range.step),
    }


def _smash_parallel_shard_kind(
    context: SmashBruteBrawlContext,
    runtime_plan: bruteforce.BruteForceRuntimePlan,
) -> str:
    if runtime_plan.mode == "TwoBytes":
        return "twobytes"
    if runtime_plan.mode == "Brutus" and context.edit_mode == "Remove" and context.chunk_name == b"IDAT":
        return "remove"
    return "standard"


def _candidate_space_payload(
    context: SmashBruteBrawlContext,
    runtime_plan: bruteforce.BruteForceRuntimePlan,
    *,
    source_hash: str,
) -> dict[str, Any]:
    twobytes_edit_order: list[str] = []
    if runtime_plan.mode == "TwoBytes":
        twobytes_edit_order = list(bruteforce.iter_twobytes_edit_kinds(context.edit_mode, context.chunk_name))
    return {
        "algorithm_version": SBB_CANDIDATE_ALGORITHM_VERSION,
        "source_hash": source_hash,
        "chunk_name_hex": context.chunk_name.hex(),
        "chunk_length": int(context.chunk_length),
        "data_offset": int(context.data_offset),
        "edit_mode": context.edit_mode,
        "bf_mode": context.bf_mode,
        "resolved_mode": runtime_plan.mode,
        "struct_indexes": list(runtime_plan.struct_indexes),
        "length_range": _length_range_record(runtime_plan.length_range),
        "brute_crc": bool(context.brute_crc),
        "brute_length": bool(context.brute_length),
        "old_crc": smash_checkpoint.normalize_old_crc(context.old_crc),
        "brute_level": int(context.brute_level),
        "scan_kind": _smash_parallel_shard_kind(context, runtime_plan),
        "twobytes_edit_order": twobytes_edit_order,
    }


def _progress_invocation_matches(context: SmashBruteBrawlContext, invocation: dict[str, Any]) -> bool:
    expected = smash_checkpoint.invocation_record(
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
    )
    comparable_keys = (
        "chunk_name_hex",
        "chunk_length",
        "data_offset",
        "edit_mode",
        "bf_mode",
        "brute_crc",
        "brute_length",
        "old_crc",
    )
    return all(invocation.get(key) == expected.get(key) for key in comparable_keys)


def _resolve_resume_record(
    runtime: SmashBruteBrawlRuntime,
    context: SmashBruteBrawlContext,
    runtime_plan: bruteforce.BruteForceRuntimePlan,
    candidate_space_hash: str,
) -> tuple[dict[str, Any] | None, str]:
    record = runtime.resume_record
    if not isinstance(record, dict):
        return None, ""
    if runtime.source_hash and record.get("source_hash") != runtime.source_hash:
        return None, "SmashBruteBrawl checkpoint belongs to another source; starting fresh."
    invocation = record.get("invocation")
    if not isinstance(invocation, dict) or not _progress_invocation_matches(context, invocation):
        return None, "SmashBruteBrawl checkpoint does not match this chunk run; starting fresh."
    plan = record.get("plan")
    if not isinstance(plan, dict):
        return None, "SmashBruteBrawl checkpoint has no search plan; starting fresh."
    checkpoint_status = str(record.get("status") or plan.get("status") or "")
    if checkpoint_status in {"exhausted", "success", "accepted_blackfill"}:
        return None, (
            "SmashBruteBrawl checkpoint already marked %s for this pass; trying the next campaign pass."
            % checkpoint_status
        )
    recorded_level = _record_int(invocation, "brute_level", int(context.brute_level))
    current_level = int(context.brute_level)
    recorded_hash = str(plan.get("candidate_space_hash") or "")
    if current_level < recorded_level:
        return None, (
            "SmashBruteBrawl checkpoint was made at BruteLevel %s; current level %s is lower, so I will not resume it."
            % (recorded_level, current_level)
        )
    if recorded_hash == candidate_space_hash:
        if _smash_parallel_progress_is_empty_stale(record):
            return None, "SmashBruteBrawl checkpoint has no confirmed worker progress; starting this pass fresh."
        if _smash_parallel_progress_is_exhausted(record):
            return None, "SmashBruteBrawl checkpoint has already exhausted this worker pass; trying the next campaign pass."
        return record, ""
    if current_level > recorded_level:
        return None, (
            "BruteLevel increased from %s to %s. The search space changed, so SmashBruteBrawl restarts from zero."
            % (recorded_level, current_level)
        )
    return None, "SmashBruteBrawl search space changed; starting fresh."


def _smash_parallel_progress_is_exhausted(record: dict[str, Any]) -> bool:
    plan_record = record.get("plan")
    plan_backend = plan_record.get("backend") if isinstance(plan_record, dict) else ""
    backend = str(record.get("backend") or plan_backend or "")
    if backend != "cpu-parallel":
        return False
    shards = record.get("shards")
    if not isinstance(shards, list) or not shards:
        return False
    accepted = _record_int(record.get("counters") if isinstance(record.get("counters"), dict) else {}, "accepted_candidates", 0)
    if accepted > 0:
        return False
    saw_done = False
    for shard in shards:
        if not isinstance(shard, dict):
            continue
        if str(shard.get("status") or "pending") != "done":
            return False
        saw_done = True
    return saw_done


def _smash_parallel_progress_is_empty_stale(record: dict[str, Any]) -> bool:
    plan_record = record.get("plan")
    plan_backend = plan_record.get("backend") if isinstance(plan_record, dict) else ""
    backend = str(record.get("backend") or plan_backend or "")
    if backend != "cpu-parallel":
        return False
    counters = record.get("counters")
    if isinstance(counters, dict) and _record_int(counters, "tested_candidates", 0) > 0:
        return False
    shards = record.get("shards")
    if not isinstance(shards, list) or not shards:
        return False
    for shard in shards:
        if not isinstance(shard, dict):
            continue
        if str(shard.get("status") or "pending") != "pending":
            return False
        if _record_int(shard, "tested", 0) > 0:
            return False
        if str(shard.get("kind") or "standard") == "twobytes":
            if _record_int(shard, "next_byte_position", _record_int(shard, "byte_start", 0)) != _record_int(shard, "byte_start", 0):
                return False
            if _record_int(shard, "edit_kind_index", 0) != 0:
                return False
            if str(shard.get("stage") or ""):
                return False
            continue
        if _record_int(shard, "next_inner_index", _record_int(shard, "start_inner_index", 0)) != _record_int(shard, "start_inner_index", 0):
            return False
    return True


def _smash_progress_record(
    context: SmashBruteBrawlContext,
    runtime: SmashBruteBrawlRuntime,
    runtime_plan: bruteforce.BruteForceRuntimePlan,
    scan_state: SmashBruteBrawlScanState,
    *,
    candidate_space_hash: str,
    backend: str = "cpu-serial",
    workers: int = 0,
    shard_size: int = 0,
    shards: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None = None,
    crc_trusted: bool | None = None,
    status: str = "running",
) -> dict[str, Any]:
    return {
        "version": smash_checkpoint.SMASH_PROGRESS_VERSION,
        "status": status,
        "source_hash": runtime.source_hash,
        "source_size": int(runtime.source_size),
        "source_path": runtime.source_path,
        "timestamp": time.time(),
        "backend": backend,
        "workers": int(workers),
        "shard_size": int(shard_size),
        "shards": list(shards or ()),
        "candidate_space_hash": candidate_space_hash,
        "crc_trusted": bool(context.old_crc) if crc_trusted is None else bool(crc_trusted),
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
        ),
        "plan": {
            "resolved_mode": runtime_plan.mode,
            "struct_indexes": list(runtime_plan.struct_indexes),
            "length_range": _length_range_record(runtime_plan.length_range),
            "candidate_space_hash": candidate_space_hash,
            "backend": backend,
            "workers": int(workers),
            "shard_size": int(shard_size),
            "crc_trusted": bool(context.old_crc) if crc_trusted is None else bool(crc_trusted),
            "status": status,
        },
        "cursor": {
            "outer_index": int(scan_state.outer_index),
            "length": int(scan_state.length),
            "inner_index": int(scan_state.inner_index),
            "byte_position": int(scan_state.byte_position),
            "edit_kind_index": int(scan_state.edit_kind_index),
            "stage": scan_state.stage,
            "bonus_offset": int(scan_state.bonus_offset),
            "bonus_value": int(scan_state.bonus_value),
        },
        "counters": {
            "tested_candidates": int(scan_state.tested_candidates),
            "accepted_candidates": int(scan_state.accepted_candidates),
            "last_displayed_counter": int(scan_state.inner_index),
        },
    }


def save_smash_progress_snapshot(
    runtime: SmashBruteBrawlRuntime,
    context: SmashBruteBrawlContext,
    runtime_plan: bruteforce.BruteForceRuntimePlan,
    scan_state: SmashBruteBrawlScanState,
    *,
    candidate_space_hash: str,
    force: bool = False,
    backend: str = "cpu-serial",
    workers: int = 0,
    shard_size: int = 0,
    shards: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None = None,
    crc_trusted: bool | None = None,
    status: str = "running",
) -> None:
    if not runtime.progress_path:
        return
    if not force and not smash_checkpoint.progress_due(
        scan_state.tested_candidates,
        scan_state.last_progress_write_at,
    ):
        return
    smash_checkpoint.atomic_write_json(
        runtime.progress_path,
        _smash_progress_record(
            context,
            runtime,
            runtime_plan,
            scan_state,
            candidate_space_hash=candidate_space_hash,
            backend=backend,
            workers=workers,
            shard_size=shard_size,
            shards=shards,
            crc_trusted=crc_trusted,
            status=status,
        ),
    )
    scan_state.last_progress_write_at = time.monotonic()


def maybe_emit_eta_sample(
    runtime: SmashBruteBrawlRuntime,
    started_at: Any,
    loop_index: int,
    max_iter: int,
) -> None:
    if loop_index != 10:
        return

    runtime.emit("\n\n-BruteForce started at: %s" % started_at)
    elapsed = runtime.now() - started_at
    eta = bruteforce.eta_seconds_after_sample(elapsed, max_iter)
    eta_delta = timedelta(seconds=eta)
    runtime.emit("-Bruteforce can last a max of %s" % str(eta_delta))
    guess = runtime.now() + eta_delta
    runtime.emit("-Bruteforce ending date time is estimated around %s\n" % str(guess))


def apply_crash_decision(scan_state: SmashBruteBrawlScanState, loop_index: int) -> bool:
    if scan_state.crash:
        crash_decision = bruteforce.crash_iteration_decision(loop_index, scan_state.crash)
        scan_state.crash = crash_decision.crash_value
        return crash_decision.skip
    return False


def run_twobytes_scan_step(
    runtime: SmashBruteBrawlRuntime,
    context: SmashBruteBrawlContext,
    scan_state: SmashBruteBrawlScanState,
    old_crc: Any,
    edit_window: bruteforce.BruteForceEditWindow,
    brute_bytes: bytes,
    max_iter: int,
    loop_index: int,
    resume_cursor: dict[str, Any] | None,
    runtime_plan: bruteforce.BruteForceRuntimePlan,
    candidate_space_hash: str,
) -> None:
    def cursor_callback(
        *,
        byte_position: int,
        edit_kind_index: int,
        stage: str,
        bonus_offset: int,
        bonus_value: int,
    ) -> None:
        scan_state.byte_position = int(byte_position)
        scan_state.edit_kind_index = int(edit_kind_index)
        scan_state.stage = stage
        scan_state.bonus_offset = int(bonus_offset)
        scan_state.bonus_value = int(bonus_value)
        save_smash_progress_snapshot(
            runtime,
            context,
            runtime_plan,
            scan_state,
            candidate_space_hash=candidate_space_hash,
        )

    def progress(*, position: int = 0, total: int = 0, bonus: bool = False) -> None:
        if total <= 0:
            runtime.raw_print(
                twobytes_progress_dots_line(
                    "%s/%s " % (loop_index, max_iter),
                    position=position,
                ),
                end="\r",
                flush=True,
            )
            return
        if position not in (0, total - 1) and position % 1024 != 0:
            return
        suffix = " bonus" if bonus else ""
        runtime.raw_print(
            twobytes_progress_dots_line(
                "%s/%s byte %s/%s%s " % (loop_index, max_iter, position + 1, total, suffix),
                position=position,
            ),
            end="\r",
            flush=True,
        )

    bruteforce.run_twobytes_candidate_scan(
        to_brute=scan_state.to_brute,
        brute_bytes=brute_bytes,
        edit_mode=context.edit_mode,
        chunk_name=context.chunk_name,
        brute_level=context.brute_level,
        old_crc=old_crc,
        before=edit_window.before,
        after=edit_window.after,
        get_state=lambda: scan_state.state,
        build_attempt=lambda length_bytes, payload_data, crc_data, before, after: build_attempt(
            context,
            old_crc,
            length_bytes,
            payload_data,
            crc_data,
            before,
            after,
        ),
        validate_attempt=lambda attempt, edit_kind=None, bonus=False: validate_candidate_attempt(
            runtime,
            scan_state,
            old_crc,
            attempt,
            loop_index=loop_index,
            brute_bytes=brute_bytes,
            edit_kind=edit_kind,
            bonus=bonus,
        ),
        progress=progress,
        bonus_message=lambda: runtime.raw_print("-Bingo replace bonus stage"),
        resume_position=_record_int(resume_cursor or {}, "byte_position", 0),
        resume_edit_kind_index=_record_int(resume_cursor or {}, "edit_kind_index", 0),
        resume_stage=str(_record_value(resume_cursor or {}, "stage", "") or ""),
        resume_bonus_offset=_record_int(resume_cursor or {}, "bonus_offset", 0),
        resume_bonus_value=_record_int(resume_cursor or {}, "bonus_value", 0),
        cursor_callback=cursor_callback,
    )


def run_standard_scan_step(
    runtime: SmashBruteBrawlRuntime,
    context: SmashBruteBrawlContext,
    scan_state: SmashBruteBrawlScanState,
    old_crc: Any,
    edit_window: bruteforce.BruteForceEditWindow,
    length_bytes: bytes,
    brute_bytes: bytes,
    max_iter: int,
    len_iter: int,
    loop_index: int,
) -> bool:
    attempt = build_attempt(
        context,
        old_crc,
        length_bytes,
        brute_bytes,
        brute_bytes,
        edit_window.before,
        edit_window.after,
    )
    runtime.loadingbar(max_iter, len_iter, loop_index, False)

    return validate_candidate_attempt(
        runtime,
        scan_state,
        old_crc,
        attempt,
        loop_index=loop_index,
        brute_bytes=brute_bytes,
    )


def run_remove_scan_length(
    runtime: SmashBruteBrawlRuntime,
    context: SmashBruteBrawlContext,
    scan_state: SmashBruteBrawlScanState,
    old_crc: Any,
    runtime_plan: bruteforce.BruteForceRuntimePlan,
    length: int,
    outer_index: int,
    *,
    resume_inner_index: int = 0,
    candidate_space_hash: str,
) -> None:
    started_at = runtime.now()
    edit_window = bruteforce.edit_window(
        context.data_hex,
        context.data_offset,
        context.chunk_length,
        context.edit_mode,
        runtime_plan.mode,
        length,
    )
    scan_state.to_brute = edit_window.to_brute
    scan_state.state = bruteforce.match_state_from_edit_window(edit_window)

    max_iter = bruteforce.remove_candidate_count(edit_window.to_brute, length)
    len_iter = max(1, len(str(max_iter)))
    runtime.loadingbar(max(max_iter, 1), len_iter, None, True)
    if max_iter <= 0:
        return

    for remove_position in range(max(0, int(resume_inner_index)), max_iter):
        scan_state.outer_index = int(outer_index)
        scan_state.length = int(length)
        scan_state.inner_index = int(remove_position)
        scan_state.byte_position = 0
        scan_state.edit_kind_index = 0
        scan_state.stage = ""
        scan_state.bonus_offset = 0
        scan_state.bonus_value = 0
        if apply_crash_decision(scan_state, remove_position):
            continue

        maybe_emit_eta_sample(runtime, started_at, remove_position, max_iter)
        candidate_data = bruteforce.remove_candidate_data(
            edit_window.to_brute,
            remove_position,
            length,
        )
        attempt = build_attempt(
            context,
            old_crc,
            candidate_data.length_bytes,
            candidate_data.data,
            candidate_data.data,
            edit_window.before,
            edit_window.after,
        )
        runtime.loadingbar(max_iter, len_iter, remove_position, False)
        if validate_candidate_attempt(
            runtime,
            scan_state,
            old_crc,
            attempt,
            loop_index=remove_position,
            brute_bytes=candidate_data.removed_bytes,
            edit_kind="remove",
        ):
            save_smash_progress_snapshot(
                runtime,
                context,
                runtime_plan,
                scan_state,
                candidate_space_hash=candidate_space_hash,
                force=True,
                status="success" if scan_state.accepted_candidates > 0 else "running",
            )
            break
        save_smash_progress_snapshot(
            runtime,
            context,
            runtime_plan,
            scan_state,
            candidate_space_hash=candidate_space_hash,
        )

    scan_state.eta_seconds = (runtime.now() - started_at).seconds


def run_scan_length(
    runtime: SmashBruteBrawlRuntime,
    context: SmashBruteBrawlContext,
    scan_state: SmashBruteBrawlScanState,
    old_crc: Any,
    bf_mode: str,
    struct_indexes: tuple[int, ...],
    length: int,
    step: int,
    outer_index: int,
    *,
    resume_inner_index: int = 0,
    resume_cursor: dict[str, Any] | None = None,
    runtime_plan: bruteforce.BruteForceRuntimePlan,
    candidate_space_hash: str,
) -> None:
    if runtime_plan.mode == "Brutus" and context.edit_mode == "Remove" and context.chunk_name == b"IDAT":
        run_remove_scan_length(
            runtime,
            context,
            scan_state,
            old_crc,
            runtime_plan,
            length,
            outer_index,
            resume_inner_index=resume_inner_index,
            candidate_space_hash=candidate_space_hash,
        )
        return

    started_at = runtime.now()
    iter_nbr = bruteforce.iter_nbr_for_length(length, step, outer_index)

    max_iter, len_iter, chunklen_spec, chunk_format, chunk_data, color_type = (
        bruteforce.load_iteration_spec(bf_mode, struct_indexes, iter_nbr, runtime.load_spec)
    )

    runtime.loadingbar(max_iter, len_iter, None, True)

    edit_window = bruteforce.edit_window(
        context.data_hex,
        context.data_offset,
        context.chunk_length,
        context.edit_mode,
        bf_mode,
        length,
    )
    scan_state.to_brute = edit_window.to_brute

    if edit_window.replace_flag or edit_window.insert_flag:
        scan_state.state = bruteforce.match_state_from_edit_window(edit_window)
        length_bytes = edit_window.length_bytes
    else:
        length_bytes = None

    shuffle = runtime.product(chunk_data, color_type)
    for inner_index, candidate in enumerate(shuffle):
        if inner_index < resume_inner_index:
            continue
        scan_state.outer_index = int(outer_index)
        scan_state.length = int(length)
        scan_state.inner_index = int(inner_index)
        scan_state.byte_position = 0
        scan_state.edit_kind_index = 0
        scan_state.stage = ""
        scan_state.bonus_offset = 0
        scan_state.bonus_value = 0
        if apply_crash_decision(scan_state, inner_index):
            continue

        maybe_emit_eta_sample(runtime, started_at, inner_index, max_iter)

        brute_bytes = bruteforce.build_candidate_bytes(
            candidate,
            chunk_format,
            bf_mode,
            struct_indexes=tuple(struct_indexes),
            to_bryte=edit_window.to_bryte,
        )

        if bf_mode == "TwoBytes":
            run_twobytes_scan_step(
                runtime,
                context,
                scan_state,
                old_crc,
                edit_window,
                brute_bytes,
                max_iter,
                inner_index,
                resume_cursor if inner_index == resume_inner_index else None,
                runtime_plan,
                candidate_space_hash,
            )
        elif run_standard_scan_step(
            runtime,
            context,
            scan_state,
            old_crc,
            edit_window,
            length_bytes,
            brute_bytes,
            max_iter,
            len_iter,
            inner_index,
        ):
            save_smash_progress_snapshot(
                runtime,
                context,
                runtime_plan,
                scan_state,
                candidate_space_hash=candidate_space_hash,
                force=True,
            )
            break
        save_smash_progress_snapshot(
            runtime,
            context,
            runtime_plan,
            scan_state,
            candidate_space_hash=candidate_space_hash,
        )

    scan_state.eta_seconds = (runtime.now() - started_at).seconds


def _build_smash_length_plans(
    runtime: SmashBruteBrawlRuntime,
    runtime_plan: bruteforce.BruteForceRuntimePlan,
) -> tuple[smash_backend.SmashLengthPlan, ...]:
    plans: list[smash_backend.SmashLengthPlan] = []
    length_range = runtime_plan.length_range
    for outer_index, length in enumerate(
        range(length_range.min_length, length_range.max_length, length_range.step)
    ):
        iter_nbr = bruteforce.iter_nbr_for_length(length, length_range.step, outer_index)
        iteration_spec = bruteforce.load_iteration_spec(
            runtime_plan.mode,
            runtime_plan.struct_indexes,
            iter_nbr,
            runtime.load_spec,
        )
        plans.append(
            smash_backend.length_plan_from_iteration_spec(
                outer_index=outer_index,
                length=length,
                iter_nbr=iter_nbr,
                iteration_spec=iteration_spec,
            )
        )
    return tuple(plans)


def _build_smash_candidate_plan(
    context: SmashBruteBrawlContext,
    runtime_plan: bruteforce.BruteForceRuntimePlan,
    old_crc: Any,
    candidate_space_hash: str,
    length_plans: tuple[smash_backend.SmashLengthPlan, ...],
) -> smash_backend.SmashCandidatePlan:
    return smash_backend.SmashCandidatePlan(
        chunk_name=context.chunk_name,
        chunk_length=int(context.chunk_length),
        data_offset=int(context.data_offset),
        data_hex=context.data_hex,
        edit_mode=context.edit_mode,
        bf_mode=runtime_plan.mode,
        brute_level=int(context.brute_level),
        brute_crc=bool(context.brute_crc),
        brute_length=bool(context.brute_length),
        old_crc=old_crc,
        struct_indexes=tuple(runtime_plan.struct_indexes),
        candidate_space_hash=candidate_space_hash,
        crc_trusted=bool(old_crc),
        lengths=length_plans,
    )


def _initial_parallel_shards(
    length_plans: tuple[smash_backend.SmashLengthPlan, ...],
    *,
    shard_size: int,
    resume_outer_index: int,
    resume_inner_index: int,
) -> list[smash_backend.SmashShard]:
    shards: list[smash_backend.SmashShard] = []
    shard_id = 0
    for length_index, length_plan in enumerate(length_plans):
        if length_plan.outer_index < resume_outer_index:
            continue
        start = resume_inner_index if length_plan.outer_index == resume_outer_index else 0
        while start < length_plan.max_iter:
            end = min(length_plan.max_iter, start + shard_size)
            shards.append(
                smash_backend.SmashShard(
                    shard_id=shard_id,
                    length_plan_index=length_index,
                    start_inner_index=start,
                    end_inner_index=end,
                )
            )
            shard_id += 1
            start = end
    return shards


def _resume_parallel_shards(
    progress_resume: dict[str, Any] | None,
    length_plans: tuple[smash_backend.SmashLengthPlan, ...],
    *,
    shard_size: int,
    resume_outer_index: int,
    resume_inner_index: int,
    plan: smash_backend.SmashCandidatePlan | None = None,
    resume_cursor: dict[str, Any] | None = None,
    kind: str = "standard",
) -> list[smash_backend.SmashShard]:
    if isinstance(progress_resume, dict):
        saved_shards = progress_resume.get("shards")
        if isinstance(saved_shards, list) and saved_shards:
            shards = []
            saw_matching_shard = False
            for saved in saved_shards:
                if not isinstance(saved, dict):
                    continue
                saved_kind = str(saved.get("kind") or "standard")
                if saved_kind != kind:
                    continue
                saw_matching_shard = True
                if saved.get("status") == "done":
                    continue
                try:
                    shard = smash_backend.shard_from_record(saved)
                except (TypeError, ValueError):
                    continue
                if (
                    0 <= shard.length_plan_index < len(length_plans)
                    and shard.start_inner_index < shard.end_inner_index
                ):
                    shards.append(shard)
            if saw_matching_shard:
                return sorted(shards, key=lambda shard: shard.shard_id)
    if kind == "twobytes" and plan is not None:
        cursor = resume_cursor or {}
        return smash_backend.build_twobytes_shards(
            plan,
            shard_size=shard_size,
            resume_outer_index=resume_outer_index,
            resume_inner_index=resume_inner_index,
            resume_byte_position=_record_int(cursor, "byte_position", 0),
            resume_edit_kind_index=_record_int(cursor, "edit_kind_index", 0),
            resume_stage=str(_record_value(cursor, "stage", "") or ""),
            resume_bonus_offset=_record_int(cursor, "bonus_offset", 0),
            resume_bonus_value=_record_int(cursor, "bonus_value", 0),
        )
    if kind == "remove" and plan is not None:
        return smash_backend.build_remove_shards(
            plan,
            shard_size=shard_size,
            resume_outer_index=resume_outer_index,
            resume_inner_index=resume_inner_index,
        )
    return _initial_parallel_shards(
        length_plans,
        shard_size=shard_size,
        resume_outer_index=resume_outer_index,
        resume_inner_index=resume_inner_index,
    )


def _parallel_shard_records(
    shards: list[smash_backend.SmashShard],
    results: dict[int, smash_backend.SmashShardResult],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for shard in shards:
        result = results.get(shard.shard_id)
        records.append(smash_backend.shard_record(shard, result))
    return records


def _estimate_parallel_remaining_candidates(
    plan: smash_backend.SmashCandidatePlan,
    shards: list[smash_backend.SmashShard],
) -> int:
    remaining = 0
    edit_kind_counts: dict[tuple[int, int], int] = {}
    for shard in shards:
        if shard.kind != "twobytes":
            remaining += max(0, int(shard.end_inner_index) - int(shard.start_inner_index))
            continue
        length_plan = plan.lengths[shard.length_plan_index]
        cache_key = (shard.length_plan_index, int(shard.inner_index or shard.start_inner_index))
        edit_kind_count = edit_kind_counts.get(cache_key)
        if edit_kind_count is None:
            edit_kinds = bruteforce.iter_twobytes_edit_kinds(plan.edit_mode, plan.chunk_name)
            edit_kind_count = max(1, len(edit_kinds))
            edit_kind_counts[cache_key] = edit_kind_count
        first_position = max(int(shard.byte_start), int(shard.next_byte_position or shard.byte_start))
        position_count = max(0, int(shard.byte_end) - first_position)
        shard_remaining = position_count * edit_kind_count
        if first_position == int(shard.next_byte_position or shard.byte_start):
            shard_remaining = max(0, shard_remaining - int(shard.edit_kind_index or 0))
        remaining += shard_remaining
    return max(0, remaining)


def _apply_parallel_hit(
    runtime: SmashBruteBrawlRuntime,
    scan_state: SmashBruteBrawlScanState,
    old_crc: Any,
    hit: smash_backend.SmashCandidateHit,
) -> bool:
    attempt = bruteforce.BruteForceCandidateAttempt(
        checksum=hit.checksum,
        full_new_data=hit.full_new_data,
        png_bytes=hit.png_bytes,
        old_crc_match=hit.old_crc_match,
    )
    viewer_ok = True
    if not old_crc:
        scan_state.full_new_data = attempt.full_new_data
        scan_state.png_bytes = attempt.png_bytes
        viewer_result = runtime.show_candidate(
            scan_state.png_bytes,
            scan_state.full_new_data,
            hit.inner_index,
            hit.brute_bytes,
        )
        viewer_ok = viewer_result.accepted
        if viewer_result.accepted:
            scan_state.diff = viewer_result.diff
    applied_attempt = bruteforce.apply_validated_candidate_attempt(
        scan_state.state,
        attempt,
        hit.edit_kind,
        bonus=hit.bonus,
        old_crc=old_crc,
        viewer_ok=viewer_ok,
    )
    if applied_attempt is None:
        return False
    scan_state.accepted_candidates += 1
    scan_state.state = applied_attempt.state
    scan_state.full_new_data = applied_attempt.full_new_data
    scan_state.png_bytes = applied_attempt.png_bytes
    return True


def _save_parallel_progress(
    runtime: SmashBruteBrawlRuntime,
    context: SmashBruteBrawlContext,
    runtime_plan: bruteforce.BruteForceRuntimePlan,
    scan_state: SmashBruteBrawlScanState,
    *,
    candidate_space_hash: str,
    worker_count: int,
    shard_size: int,
    shards: list[smash_backend.SmashShard],
    results: dict[int, smash_backend.SmashShardResult],
    tested_floor: int = 0,
    force: bool = False,
    status: str = "running",
) -> None:
    if results:
        confirmed_tested = int(tested_floor) + sum(int(result.tested) for result in results.values())
        if confirmed_tested > scan_state.tested_candidates:
            scan_state.tested_candidates = confirmed_tested
    save_smash_progress_snapshot(
        runtime,
        context,
        runtime_plan,
        scan_state,
        candidate_space_hash=candidate_space_hash,
        force=force,
        backend="cpu-parallel",
        workers=worker_count,
        shard_size=shard_size,
        shards=_parallel_shard_records(shards, results),
        crc_trusted=bool(context.old_crc),
        status=status,
    )


def _run_parallel_scan(
    runtime: SmashBruteBrawlRuntime,
    context: SmashBruteBrawlContext,
    scan_state: SmashBruteBrawlScanState,
    old_crc: Any,
    runtime_plan: bruteforce.BruteForceRuntimePlan,
    candidate_space_hash: str,
    progress_resume: dict[str, Any] | None,
    resume_outer_index: int,
    resume_inner_index: int,
) -> bool:
    worker_count = smash_backend.resolve_smash_worker_count(runtime.smash_workers)
    if worker_count <= 1:
        return False
    length_plans = _build_smash_length_plans(runtime, runtime_plan)
    plan = _build_smash_candidate_plan(
        context,
        runtime_plan,
        old_crc,
        candidate_space_hash,
        length_plans,
    )
    backend = smash_backend.SmashParallelBackend()
    if not backend.supports(plan):
        return False
    shard_kind = _smash_parallel_shard_kind(context, runtime_plan)
    shard_size = (
        smash_backend.SMASH_TWOBYTES_SHARD_BYTE_SIZE
        if shard_kind == "twobytes"
        else smash_backend.SMASH_PARALLEL_SHARD_SIZE
    )
    shards = _resume_parallel_shards(
        progress_resume,
        length_plans,
        shard_size=shard_size,
        resume_outer_index=resume_outer_index,
        resume_inner_index=resume_inner_index,
        plan=plan,
        resume_cursor=progress_resume.get("cursor") if isinstance(progress_resume, dict) else None,
        kind=shard_kind,
    )
    if not shards:
        _save_parallel_progress(
            runtime,
            context,
            runtime_plan,
            scan_state,
            candidate_space_hash=candidate_space_hash,
            worker_count=worker_count,
            shard_size=shard_size,
            shards=[],
            results={},
            force=True,
            status="exhausted",
        )
        return True

    runtime.emit("-SmashBruteBrawl will use %s CPU workers." % worker_count)
    scan_state.last_progress_write_at = time.monotonic()
    started_at = runtime.now()
    remaining_candidates = _estimate_parallel_remaining_candidates(plan, shards)
    progress_total = max(scan_state.tested_candidates + remaining_candidates, 1)
    progress_width = max(1, len(str(progress_total)))
    runtime.loadingbar(progress_total, progress_width, None, True)
    completed_results: dict[int, smash_backend.SmashShardResult] = {}
    finished_results: dict[int, smash_backend.SmashShardResult] = {}
    result_buffer: dict[int, smash_backend.SmashShardResult] = {}
    worker_error_counts: dict[str, int] = {}
    shard_by_id = {shard.shard_id: shard for shard in shards}
    shard_order = [shard.shard_id for shard in shards]
    next_order_index = 0
    accepted = False
    manager = multiprocessing.Manager()
    stop_event = manager.Event()
    last_worker_heartbeat_at = 0.0
    pending: dict[concurrent.futures.Future, smash_backend.SmashShard] = {}
    executor: concurrent.futures.ProcessPoolExecutor | None = None
    executor_shutdown = False
    manager_shutdown = False
    previous_sigint_handler: Any = None
    sigint_handler_installed = False
    interrupt_requested = False
    interrupt_announced = False
    parallel_tested_floor = int(scan_state.tested_candidates)

    def emit_worker_heartbeat(*, force: bool = False) -> None:
        nonlocal last_worker_heartbeat_at
        now = time.monotonic()
        if not force and now - last_worker_heartbeat_at < 0.5:
            return
        finished_tested = sum(result.tested for result in finished_results.values())
        current = min(progress_total, parallel_tested_floor + finished_tested)
        runtime.loadingbar(progress_total, progress_width, current, False)
        last_worker_heartbeat_at = now

    def handle_ready_results() -> bool:
        nonlocal next_order_index, accepted
        advanced = False
        while next_order_index < len(shard_order):
            shard_id = shard_order[next_order_index]
            result = result_buffer.get(shard_id)
            if result is None:
                break
            advanced = True
            result_buffer.pop(shard_id)
            completed_results[shard_id] = result
            shard = shard_by_id[shard_id]
            length_plan = length_plans[shard.length_plan_index]
            edit_window = bruteforce.edit_window(
                context.data_hex,
                context.data_offset,
                context.chunk_length,
                context.edit_mode,
                runtime_plan.mode,
                length_plan.length,
            )
            scan_state.to_brute = edit_window.to_brute
            if shard.kind != "twobytes" and (
                edit_window.replace_flag or edit_window.insert_flag or edit_window.remove_flag
            ):
                scan_state.state = bruteforce.match_state_from_edit_window(edit_window)
            scan_state.outer_index = length_plan.outer_index
            scan_state.length = length_plan.length
            scan_state.inner_index = max(shard.start_inner_index, result.next_inner_index - 1)
            if shard.kind == "twobytes":
                scan_state.inner_index = int(shard.inner_index if shard.inner_index is not None else shard.start_inner_index)
                scan_state.byte_position = int(result.next_byte_position)
                scan_state.edit_kind_index = int(result.edit_kind_index)
                scan_state.stage = result.stage
                scan_state.bonus_offset = int(result.bonus_offset)
                scan_state.bonus_value = int(result.bonus_value)
            scan_state.tested_candidates += result.tested
            if result.error:
                previous_error_count = worker_error_counts.get(result.error, 0)
                worker_error_counts[result.error] = previous_error_count + 1
                if previous_error_count == 0:
                    runtime.emit("-SmashBruteBrawl worker shard %s failed: %s" % (shard_id, result.error))
            emit_worker_heartbeat(force=True)
            for hit in result.hits:
                if _apply_parallel_hit(runtime, scan_state, old_crc, hit):
                    accepted = True
                    stop_event.set()
                    break
            _save_parallel_progress(
                runtime,
                context,
                runtime_plan,
                scan_state,
                candidate_space_hash=candidate_space_hash,
                worker_count=worker_count,
                shard_size=shard_size,
                shards=shards,
                results=finished_results,
                tested_floor=parallel_tested_floor,
            )
            next_order_index += 1
            if accepted:
                break
        return advanced

    def harvest_finished_futures() -> None:
        for future in list(pending):
            if not future.done():
                continue
            shard = pending.pop(future)
            try:
                result = future.result()
            except Exception as exc:
                result = smash_backend.SmashShardResult(
                    shard=shard,
                    tested=0,
                    next_inner_index=shard.start_inner_index,
                    error=str(exc),
                    next_byte_position=shard.next_byte_position,
                    edit_kind_index=shard.edit_kind_index,
                    stage=shard.stage,
                    bonus_offset=shard.bonus_offset,
                    bonus_value=shard.bonus_value,
                )
            finished_results[shard.shard_id] = result
            result_buffer[shard.shard_id] = result

    def mark_missing_ordered_shards_pending() -> None:
        if not result_buffer:
            return
        missing: list[int] = []
        buffered_ids = set(result_buffer)
        completed_ids = set(completed_results)
        for shard_id in shard_order[next_order_index:]:
            if shard_id in buffered_ids:
                break
            if shard_id not in completed_ids:
                missing.append(shard_id)
                if len(missing) >= 5:
                    break
        if missing:
            runtime.emit(
                "-SmashBruteBrawl kept %s unordered worker result(s) for resume; missing earlier shard(s): %s."
                % (len(result_buffer), ", ".join(str(item) for item in missing))
            )

    def shutdown_executor(*, wait: bool) -> None:
        nonlocal executor_shutdown
        if executor is not None and not executor_shutdown:
            executor.shutdown(wait=wait, cancel_futures=True)
            executor_shutdown = True

    def shutdown_manager() -> None:
        nonlocal manager_shutdown
        if not manager_shutdown:
            manager.shutdown()
            manager_shutdown = True

    def request_interrupt(_signum: int, _frame: Any) -> None:
        nonlocal interrupt_requested
        interrupt_requested = True

    def install_sigint_handler() -> None:
        nonlocal previous_sigint_handler, sigint_handler_installed
        if sigint_handler_installed:
            return
        previous_sigint_handler = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGINT, request_interrupt)
        sigint_handler_installed = True

    def restore_sigint_handler() -> None:
        nonlocal sigint_handler_installed
        if sigint_handler_installed:
            signal.signal(signal.SIGINT, previous_sigint_handler)
            sigint_handler_installed = False

    def ignore_sigint_until_exit() -> None:
        nonlocal previous_sigint_handler, sigint_handler_installed
        if not sigint_handler_installed:
            previous_sigint_handler = signal.getsignal(signal.SIGINT)
            sigint_handler_installed = True
        signal.signal(signal.SIGINT, signal.SIG_IGN)

    def finish_interrupted(exc: BaseException | None = None) -> None:
        nonlocal interrupt_announced
        ignore_sigint_until_exit()
        if not interrupt_announced:
            runtime.emit(
                "-SmashBruteBrawl is stopping cleanly. Workers are parking; saving %s."
                % (runtime.progress_path or "the progress checkpoint")
            )
            interrupt_announced = True
        stop_event.set()
        harvest_finished_futures()
        for future in pending:
            future.cancel()
        _save_parallel_progress(
            runtime,
            context,
            runtime_plan,
            scan_state,
            candidate_space_hash=candidate_space_hash,
            worker_count=worker_count,
            shard_size=shard_size,
            shards=shards,
            results=finished_results,
            tested_floor=parallel_tested_floor,
            force=True,
            status="interrupted",
        )
        try:
            shutdown_executor(wait=True)
        finally:
            try:
                shutdown_manager()
            finally:
                restore_sigint_handler()
        interruption = smash_checkpoint.SmashBruteBrawlInterrupted(runtime.progress_path)
        if exc is not None:
            raise interruption from exc
        raise interruption

    try:
        emit_worker_heartbeat(force=True)
        executor = concurrent.futures.ProcessPoolExecutor(max_workers=worker_count)
        shard_iter = iter(shards)

        def fill_pending() -> None:
            while len(pending) < worker_count * 2 and not accepted:
                try:
                    shard = next(shard_iter)
                except StopIteration:
                    break
                if shard.kind == "twobytes":
                    shard_runner = smash_backend.run_twobytes_shard
                elif shard.kind == "remove":
                    shard_runner = smash_backend.run_remove_shard
                else:
                    shard_runner = smash_backend.run_standard_shard
                future = executor.submit(shard_runner, plan, shard, stop_event)
                pending[future] = shard

        fill_pending()
        install_sigint_handler()
        while pending:
            if interrupt_requested:
                finish_interrupted()
            done, _not_done = concurrent.futures.wait(
                pending,
                timeout=0.2,
                return_when=concurrent.futures.FIRST_COMPLETED,
            )
            if interrupt_requested:
                finish_interrupted()
            if not done:
                emit_worker_heartbeat()
                continue
            harvest_finished_futures()
            emit_worker_heartbeat(force=True)
            handle_ready_results()
            if accepted:
                break
            fill_pending()
        while handle_ready_results() and not accepted:
            pass
        if result_buffer and not accepted:
            mark_missing_ordered_shards_pending()
        if accepted:
            for future in pending:
                future.cancel()
        shutdown_executor(wait=True)
    except KeyboardInterrupt as exc:
        finish_interrupted(exc)
    finally:
        try:
            shutdown_executor(wait=True)
        except Exception:
            pass
        try:
            shutdown_manager()
        except Exception:
            pass
        restore_sigint_handler()

    if finished_results:
        scan_state.tested_candidates = max(
            scan_state.tested_candidates,
            parallel_tested_floor + sum(result.tested for result in finished_results.values()),
        )
    scan_state.eta_seconds = (runtime.now() - started_at).seconds
    _save_parallel_progress(
        runtime,
        context,
        runtime_plan,
        scan_state,
        candidate_space_hash=candidate_space_hash,
        worker_count=worker_count,
        shard_size=shard_size,
        shards=shards,
        results=finished_results,
        tested_floor=parallel_tested_floor,
        force=True,
        status="success" if accepted else "exhausted",
    )
    for error, count in sorted(worker_error_counts.items(), key=lambda item: item[0]):
        if count > 1:
            runtime.emit(
                "-SmashBruteBrawl suppressed %s repeated worker shard errors: %s"
                % (count - 1, error)
            )
    return True


def run_scan(runtime: SmashBruteBrawlRuntime, context: SmashBruteBrawlContext) -> SmashBruteBrawlScanResult:
    old_crc = bruteforce.normalize_old_crc(context.old_crc)
    scan_state = SmashBruteBrawlScanState(
        state=bruteforce.BruteForceMatchState(),
        crash=context.crash,
    )

    runtime_plan = prepare_runtime_plan(runtime, context)
    emit_debug_report_if_needed(runtime, context, runtime_plan)
    candidate_space_payload = _candidate_space_payload(
        context,
        runtime_plan,
        source_hash=runtime.source_hash,
    )
    candidate_space_hash = smash_checkpoint.candidate_space_hash(candidate_space_payload)
    progress_resume, progress_warning = _resolve_resume_record(
        runtime,
        context,
        runtime_plan,
        candidate_space_hash,
    )
    if progress_warning:
        runtime.emit("-%s" % progress_warning)

    length_range = runtime_plan.length_range
    resume_outer_index = 0
    resume_inner_index = 0
    resume_cursor: dict[str, Any] | None = None
    if progress_resume is not None:
        cursor = progress_resume.get("cursor")
        counters = progress_resume.get("counters")
        if isinstance(cursor, dict):
            resume_cursor = cursor
            resume_outer_index = _record_int(cursor, "outer_index", 0)
            resume_inner_index = _record_int(cursor, "inner_index", 0)
            scan_state.outer_index = resume_outer_index
            scan_state.inner_index = resume_inner_index
            scan_state.length = _record_int(cursor, "length", 0)
            scan_state.byte_position = _record_int(cursor, "byte_position", 0)
            scan_state.edit_kind_index = _record_int(cursor, "edit_kind_index", 0)
            scan_state.stage = str(cursor.get("stage") or "")
            scan_state.bonus_offset = _record_int(cursor, "bonus_offset", 0)
            scan_state.bonus_value = _record_int(cursor, "bonus_value", 0)
        if isinstance(counters, dict):
            scan_state.tested_candidates = _record_int(counters, "tested_candidates", 0)
            scan_state.accepted_candidates = _record_int(counters, "accepted_candidates", 0)
        scan_state.crash = False
        runtime.emit(
            "-SmashBruteBrawl resume checkpoint accepted at outer %s, inner %s."
            % (resume_outer_index, resume_inner_index)
        )

    try:
        if _run_parallel_scan(
            runtime,
            context,
            scan_state,
            old_crc,
            runtime_plan,
            candidate_space_hash,
            progress_resume,
            resume_outer_index,
            resume_inner_index,
        ):
            return SmashBruteBrawlScanResult(
                state=scan_state.state,
                old_crc=old_crc,
                bf_mode=runtime_plan.mode,
                full_new_data=scan_state.full_new_data,
                png_bytes=scan_state.png_bytes,
                to_brute=scan_state.to_brute,
                diff=scan_state.diff,
                crash=scan_state.crash,
                eta_seconds=scan_state.eta_seconds,
            )
        for outer_index, length in enumerate(
            range(length_range.min_length, length_range.max_length, length_range.step)
        ):
            if outer_index < resume_outer_index:
                continue
            run_scan_length(
                runtime,
                context,
                scan_state,
                old_crc,
                runtime_plan.mode,
                runtime_plan.struct_indexes,
                length,
                length_range.step,
                outer_index,
                resume_inner_index=resume_inner_index if outer_index == resume_outer_index else 0,
                resume_cursor=resume_cursor if outer_index == resume_outer_index else None,
                runtime_plan=runtime_plan,
                candidate_space_hash=candidate_space_hash,
            )
            save_smash_progress_snapshot(
                runtime,
                context,
                runtime_plan,
                scan_state,
                candidate_space_hash=candidate_space_hash,
                force=True,
            )
    except KeyboardInterrupt as exc:
        save_smash_progress_snapshot(
            runtime,
            context,
            runtime_plan,
            scan_state,
            candidate_space_hash=candidate_space_hash,
            force=True,
            status="interrupted",
        )
        raise smash_checkpoint.SmashBruteBrawlInterrupted(runtime.progress_path) from exc

    save_smash_progress_snapshot(
        runtime,
        context,
        runtime_plan,
        scan_state,
        candidate_space_hash=candidate_space_hash,
        force=True,
        status="success" if scan_state.accepted_candidates > 0 else "exhausted",
    )

    return SmashBruteBrawlScanResult(
        state=scan_state.state,
        old_crc=old_crc,
        bf_mode=runtime_plan.mode,
        full_new_data=scan_state.full_new_data,
        png_bytes=scan_state.png_bytes,
        to_brute=scan_state.to_brute,
        diff=scan_state.diff,
        crash=scan_state.crash,
        eta_seconds=scan_state.eta_seconds,
    )
