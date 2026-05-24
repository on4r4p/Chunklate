from __future__ import annotations

from collections.abc import Callable, MutableSequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from . import bruteforce


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

    scan_state.state = applied_attempt.state
    scan_state.full_new_data = applied_attempt.full_new_data
    scan_state.png_bytes = applied_attempt.png_bytes
    return True


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
) -> None:
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
        progress=lambda: runtime.minibar(Indication="%s/%s" % (loop_index, max_iter)),
        bonus_message=lambda: runtime.raw_print("-Bingo replace bonus stage"),
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
            break

    scan_state.eta_seconds = (runtime.now() - started_at).seconds


def run_scan(runtime: SmashBruteBrawlRuntime, context: SmashBruteBrawlContext) -> SmashBruteBrawlScanResult:
    old_crc = bruteforce.normalize_old_crc(context.old_crc)
    scan_state = SmashBruteBrawlScanState(
        state=bruteforce.BruteForceMatchState(),
        crash=context.crash,
    )

    runtime_plan = prepare_runtime_plan(runtime, context)
    emit_debug_report_if_needed(runtime, context, runtime_plan)

    length_range = runtime_plan.length_range

    for outer_index, length in enumerate(
        range(length_range.min_length, length_range.max_length, length_range.step)
    ):
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
