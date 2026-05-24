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


def run_scan(runtime: SmashBruteBrawlRuntime, context: SmashBruteBrawlContext) -> SmashBruteBrawlScanResult:
    state = bruteforce.BruteForceMatchState()
    full_new_data = b""
    png_bytes = b""
    to_brute = ""
    diff = ""
    eta_seconds = 0
    crash = context.crash
    old_crc = bruteforce.normalize_old_crc(context.old_crc)

    runtime_plan = bruteforce.prepare_runtime_plan(
        context.bf_mode,
        context.chunk_name,
        context.pandora_box,
        runtime.load_spec,
    )
    bf_mode = runtime_plan.mode
    struct_indexes = runtime_plan.struct_indexes
    if runtime_plan.side_note is not None:
        runtime.side_notes.append(runtime_plan.side_note)

    length_range = runtime_plan.length_range
    maxchunklen = length_range.max_length
    minchunklen = length_range.min_length
    step = length_range.step

    if context.debug is True:
        max_iter, _len_iter, chunklen_spec, chunk_format, chunk_data, color_type = (
            bruteforce.load_iteration_spec(bf_mode, struct_indexes, None, runtime.load_spec)
        )
        emit_debug_report(
            runtime,
            context,
            chunklen_spec=chunklen_spec,
            chunk_format=chunk_format,
            chunk_data=chunk_data,
            max_iter=max_iter,
            maxchunklen=maxchunklen,
            minchunklen=minchunklen,
            step=step,
        )

    def validate_attempt(attempt, edit_kind=None, bonus=False):
        nonlocal state, full_new_data, png_bytes, diff

        viewer_ok = True
        if not old_crc:
            full_new_data = attempt.full_new_data
            png_bytes = attempt.png_bytes
            viewer_result = runtime.show_candidate(
                png_bytes,
                full_new_data,
                inner_index,
                brute_bytes,
            )
            viewer_ok = viewer_result.accepted
            if viewer_result.accepted:
                diff = viewer_result.diff

        applied_attempt = bruteforce.apply_validated_candidate_attempt(
            state,
            attempt,
            edit_kind,
            bonus=bonus,
            old_crc=old_crc,
            viewer_ok=viewer_ok,
        )
        if applied_attempt is None:
            return False

        state = applied_attempt.state
        full_new_data = applied_attempt.full_new_data
        png_bytes = applied_attempt.png_bytes
        return True

    for outer_index, length in enumerate(range(minchunklen, maxchunklen, step)):
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
        before_new = edit_window.before
        to_brute = edit_window.to_brute
        to_bryte = edit_window.to_bryte
        after_new = edit_window.after

        if edit_window.replace_flag or edit_window.insert_flag:
            state = bruteforce.match_state_from_edit_window(edit_window)
            length_bytes = edit_window.length_bytes
        else:
            length_bytes = None

        shuffle = runtime.product(chunk_data, color_type)
        for inner_index, candidate in enumerate(shuffle):
            if crash:
                crash_decision = bruteforce.crash_iteration_decision(inner_index, crash)
                crash = crash_decision.crash_value
                if crash_decision.skip:
                    continue

            if inner_index == 10:
                runtime.emit("\n\n-BruteForce started at: %s" % started_at)
                elapsed = runtime.now() - started_at
                eta = bruteforce.eta_seconds_after_sample(elapsed, max_iter)
                eta_delta = timedelta(seconds=eta)
                runtime.emit("-Bruteforce can last a max of %s" % str(eta_delta))
                guess = runtime.now() + eta_delta
                runtime.emit("-Bruteforce ending date time is estimated around %s\n" % str(guess))

            brute_bytes = bruteforce.build_candidate_bytes(
                candidate,
                chunk_format,
                bf_mode,
                struct_indexes=tuple(struct_indexes),
                to_bryte=to_bryte,
            )

            if bf_mode == "TwoBytes":
                bruteforce.run_twobytes_candidate_scan(
                    to_brute=to_brute,
                    brute_bytes=brute_bytes,
                    edit_mode=context.edit_mode,
                    chunk_name=context.chunk_name,
                    brute_level=context.brute_level,
                    old_crc=old_crc,
                    before=before_new,
                    after=after_new,
                    get_state=lambda: state,
                    build_attempt=lambda length_bytes, payload_data, crc_data, before, after: build_attempt(
                        context,
                        old_crc,
                        length_bytes,
                        payload_data,
                        crc_data,
                        before,
                        after,
                    ),
                    validate_attempt=validate_attempt,
                    progress=lambda: runtime.minibar(Indication="%s/%s" % (inner_index, max_iter)),
                    bonus_message=lambda: runtime.raw_print("-Bingo replace bonus stage"),
                )
            else:
                attempt = build_attempt(
                    context,
                    old_crc,
                    length_bytes,
                    brute_bytes,
                    brute_bytes,
                    before_new,
                    after_new,
                )
                runtime.loadingbar(max_iter, len_iter, inner_index, False)

                if validate_attempt(attempt):
                    break
                continue

        eta_seconds = (runtime.now() - started_at).seconds

    return SmashBruteBrawlScanResult(
        state=state,
        old_crc=old_crc,
        bf_mode=bf_mode,
        full_new_data=full_new_data,
        png_bytes=png_bytes,
        to_brute=to_brute,
        diff=diff,
        crash=crash,
        eta_seconds=eta_seconds,
    )
