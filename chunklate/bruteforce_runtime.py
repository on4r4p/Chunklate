from __future__ import annotations

from collections.abc import Callable, MutableSequence
from dataclasses import dataclass
from datetime import datetime, timedelta
import shutil
import time
from typing import Any

from . import bruteforce, smash_checkpoint


LegacyCall = Callable[..., Any]


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


def _candidate_space_payload(
    context: SmashBruteBrawlContext,
    runtime_plan: bruteforce.BruteForceRuntimePlan,
    *,
    source_hash: str,
) -> dict[str, Any]:
    return {
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
    recorded_level = _record_int(invocation, "brute_level", int(context.brute_level))
    current_level = int(context.brute_level)
    recorded_hash = str(plan.get("candidate_space_hash") or "")
    if current_level < recorded_level:
        return None, (
            "SmashBruteBrawl checkpoint was made at BruteLevel %s; current level %s is lower, so I will not resume it."
            % (recorded_level, current_level)
        )
    if recorded_hash == candidate_space_hash:
        return record, ""
    if current_level > recorded_level:
        return None, (
            "BruteLevel increased from %s to %s. The search space changed, so SmashBruteBrawl restarts from zero."
            % (recorded_level, current_level)
        )
    return None, "SmashBruteBrawl search space changed; starting fresh."


def _smash_progress_record(
    context: SmashBruteBrawlContext,
    runtime: SmashBruteBrawlRuntime,
    runtime_plan: bruteforce.BruteForceRuntimePlan,
    scan_state: SmashBruteBrawlScanState,
    *,
    candidate_space_hash: str,
) -> dict[str, Any]:
    return {
        "version": smash_checkpoint.SMASH_PROGRESS_VERSION,
        "source_hash": runtime.source_hash,
        "source_size": int(runtime.source_size),
        "source_path": runtime.source_path,
        "timestamp": time.time(),
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
        )
        raise smash_checkpoint.SmashBruteBrawlInterrupted(runtime.progress_path) from exc

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
