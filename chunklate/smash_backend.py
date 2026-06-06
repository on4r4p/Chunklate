from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import io
import os
import sys
from typing import Any

from . import bruteforce, specs


SMASH_PARALLEL_SHARD_SIZE = 50_000
SMASH_TWOBYTES_SHARD_BYTE_SIZE = 4096


@dataclass(frozen=True)
class SmashLengthPlan:
    outer_index: int
    length: int
    iter_nbr: int | None
    max_iter: int
    len_iter: int
    chunk_format: tuple[str, ...]
    chunk_data: tuple[tuple[Any, ...], ...]
    color_type: str


@dataclass(frozen=True)
class SmashCandidatePlan:
    chunk_name: bytes
    chunk_length: int
    data_offset: int
    data_hex: str
    edit_mode: str
    bf_mode: str
    brute_level: int
    brute_crc: bool
    brute_length: bool
    old_crc: Any
    struct_indexes: tuple[int, ...]
    candidate_space_hash: str
    crc_trusted: bool
    lengths: tuple[SmashLengthPlan, ...]


@dataclass(frozen=True)
class SmashShard:
    shard_id: int
    length_plan_index: int
    start_inner_index: int
    end_inner_index: int
    kind: str = "standard"
    inner_index: int | None = None
    byte_start: int = 0
    byte_end: int = 0
    next_byte_position: int = 0
    edit_kind_index: int = 0
    stage: str = ""
    bonus_offset: int = 0
    bonus_value: int = 0


@dataclass(frozen=True)
class SmashCandidateHit:
    outer_index: int
    length: int
    inner_index: int
    brute_bytes: bytes
    checksum: bytes
    full_new_data: bytes
    png_bytes: bytes
    old_crc_match: bool
    edit_kind: str | None = None
    bonus: bool = False


@dataclass(frozen=True)
class SmashShardResult:
    shard: SmashShard
    tested: int
    next_inner_index: int
    hits: tuple[SmashCandidateHit, ...] = ()
    stopped: bool = False
    error: str = ""
    next_byte_position: int = 0
    edit_kind_index: int = 0
    stage: str = ""
    bonus_offset: int = 0
    bonus_value: int = 0


def resolve_smash_worker_count(workers: object, *, cpu_count: int | None = None) -> int:
    if workers in (None, ""):
        return 0
    detected = cpu_count if cpu_count is not None else (os.cpu_count() or 1)
    detected = max(1, int(detected))
    text = str(workers).strip().lower()
    if text == "min":
        return max(1, detected // 4)
    if text in ("normal", "auto"):
        return max(1, detected // 2)
    if text == "max":
        return max(1, detected - 1)
    return max(0, int(text))


def _tuple_chunk_data(chunk_data: Any) -> tuple[tuple[Any, ...], ...]:
    return tuple(tuple(item) for item in chunk_data)


def length_plan_from_iteration_spec(
    *,
    outer_index: int,
    length: int,
    iter_nbr: int | None,
    iteration_spec: tuple[Any, Any, Any, Any, Any, Any],
) -> SmashLengthPlan:
    max_iter, len_iter, _chunklen_spec, chunk_format, chunk_data, color_type = iteration_spec
    return SmashLengthPlan(
        outer_index=int(outer_index),
        length=int(length),
        iter_nbr=iter_nbr,
        max_iter=int(max_iter),
        len_iter=int(len_iter),
        chunk_format=tuple(chunk_format),
        chunk_data=_tuple_chunk_data(chunk_data),
        color_type=str(color_type),
    )


def shard_record(shard: SmashShard, result: SmashShardResult | None = None, *, status: str = "pending") -> dict[str, Any]:
    next_inner = shard.start_inner_index
    next_byte_position = shard.next_byte_position
    edit_kind_index = shard.edit_kind_index
    stage = shard.stage
    bonus_offset = shard.bonus_offset
    bonus_value = shard.bonus_value
    tested = 0
    if result is not None:
        next_inner = result.next_inner_index
        next_byte_position = result.next_byte_position
        edit_kind_index = result.edit_kind_index
        stage = result.stage
        bonus_offset = result.bonus_offset
        bonus_value = result.bonus_value
        tested = result.tested
        status = "pending" if result.stopped else "done"
        if result.error:
            status = "error"
    record = {
        "kind": shard.kind,
        "shard_id": int(shard.shard_id),
        "length_plan_index": int(shard.length_plan_index),
        "start_inner_index": int(shard.start_inner_index),
        "end_inner_index": int(shard.end_inner_index),
        "next_inner_index": int(next_inner),
        "tested": int(tested),
        "status": status,
    }
    if shard.kind == "twobytes":
        record.update(
            {
                "inner_index": int(shard.inner_index if shard.inner_index is not None else shard.start_inner_index),
                "byte_start": int(shard.byte_start),
                "byte_end": int(shard.byte_end),
                "next_byte_position": int(next_byte_position),
                "edit_kind_index": int(edit_kind_index),
                "stage": stage,
                "bonus_offset": int(bonus_offset),
                "bonus_value": int(bonus_value),
            }
        )
    return record


def shard_from_record(record: dict[str, Any]) -> SmashShard:
    kind = str(record.get("kind") or "standard")
    if kind == "twobytes":
        inner_index = int(record.get("inner_index", record.get("start_inner_index", 0)) or 0)
        return SmashShard(
            shard_id=int(record.get("shard_id", 0) or 0),
            length_plan_index=int(record.get("length_plan_index", 0) or 0),
            start_inner_index=inner_index,
            end_inner_index=inner_index + 1,
            kind="twobytes",
            inner_index=inner_index,
            byte_start=int(record.get("byte_start", 0) or 0),
            byte_end=int(record.get("byte_end", 0) or 0),
            next_byte_position=int(record.get("next_byte_position", record.get("byte_start", 0)) or 0),
            edit_kind_index=int(record.get("edit_kind_index", 0) or 0),
            stage=str(record.get("stage") or ""),
            bonus_offset=int(record.get("bonus_offset", 0) or 0),
            bonus_value=int(record.get("bonus_value", 0) or 0),
        )
    return SmashShard(
        shard_id=int(record.get("shard_id", 0) or 0),
        length_plan_index=int(record.get("length_plan_index", 0) or 0),
        start_inner_index=int(record.get("next_inner_index", record.get("start_inner_index", 0)) or 0),
        end_inner_index=int(record.get("end_inner_index", 0) or 0),
    )


@contextmanager
def _worker_stderr_silenced():
    try:
        stderr_fd = sys.stderr.fileno()
    except Exception:
        yield
        return

    saved_fd = None
    try:
        saved_fd = os.dup(stderr_fd)
        with open(os.devnull, "w", encoding="utf-8") as devnull:
            os.dup2(devnull.fileno(), stderr_fd)
            yield
    finally:
        if saved_fd is not None:
            try:
                os.dup2(saved_fd, stderr_fd)
            finally:
                os.close(saved_fd)


def _candidate_png_looks_valid(png_bytes: bytes) -> bool:
    try:
        import cv2
        import numpy as np

        data = np.frombuffer(png_bytes, dtype=np.uint8)
        return cv2.imdecode(data, cv2.IMREAD_UNCHANGED) is not None
    except Exception:
        pass
    try:
        from PIL import Image

        with Image.open(io.BytesIO(png_bytes)) as image:
            image.load()
        return True
    except Exception:
        return False


def _stop_is_set(stop_event: Any) -> bool:
    if stop_event is None:
        return False
    try:
        return bool(stop_event.is_set())
    except Exception:
        return False


def _candidate_at_inner_index(length_plan: SmashLengthPlan, inner_index: int) -> tuple[Any, ...] | None:
    for index, candidate in enumerate(specs.iter_product_values(length_plan.chunk_data, length_plan.color_type)):
        if index == inner_index:
            return tuple(candidate)
    return None


def _twobytes_candidate_bytes(
    plan: SmashCandidatePlan,
    length_plan: SmashLengthPlan,
    inner_index: int,
    edit_window: bruteforce.BruteForceEditWindow,
) -> bytes | None:
    candidate = _candidate_at_inner_index(length_plan, inner_index)
    if candidate is None:
        return None
    return bruteforce.build_candidate_bytes(
        candidate,
        length_plan.chunk_format,
        plan.bf_mode,
        struct_indexes=plan.struct_indexes,
        to_bryte=edit_window.to_bryte,
    )


def build_twobytes_shards(
    plan: SmashCandidatePlan,
    *,
    shard_size: int = SMASH_TWOBYTES_SHARD_BYTE_SIZE,
    resume_outer_index: int = 0,
    resume_inner_index: int = 0,
    resume_byte_position: int = 0,
    resume_edit_kind_index: int = 0,
    resume_stage: str = "",
    resume_bonus_offset: int = 0,
    resume_bonus_value: int = 0,
) -> list[SmashShard]:
    shards: list[SmashShard] = []
    shard_id = 0
    safe_shard_size = max(1, int(shard_size))
    for length_index, length_plan in enumerate(plan.lengths):
        if length_plan.outer_index < resume_outer_index:
            continue
        first_inner = resume_inner_index if length_plan.outer_index == resume_outer_index else 0
        edit_window = bruteforce.edit_window(
            plan.data_hex,
            plan.data_offset,
            plan.chunk_length,
            plan.edit_mode,
            plan.bf_mode,
            length_plan.length,
        )
        for inner_index in range(first_inner, length_plan.max_iter):
            brute_bytes = _twobytes_candidate_bytes(plan, length_plan, inner_index, edit_window)
            if brute_bytes is None:
                continue
            total_positions = bruteforce.twobytes_scan_position_count(
                edit_window.to_brute,
                len(brute_bytes.hex()),
            )
            start = resume_byte_position if (
                length_plan.outer_index == resume_outer_index and inner_index == resume_inner_index
            ) else 0
            while start < total_positions:
                end = min(total_positions, start + safe_shard_size)
                initial_cursor = start == resume_byte_position and (
                    length_plan.outer_index == resume_outer_index and inner_index == resume_inner_index
                )
                shards.append(
                    SmashShard(
                        shard_id=shard_id,
                        length_plan_index=length_index,
                        start_inner_index=inner_index,
                        end_inner_index=inner_index + 1,
                        kind="twobytes",
                        inner_index=inner_index,
                        byte_start=start,
                        byte_end=end,
                        next_byte_position=start,
                        edit_kind_index=resume_edit_kind_index if initial_cursor else 0,
                        stage=resume_stage if initial_cursor else "",
                        bonus_offset=resume_bonus_offset if initial_cursor else 0,
                        bonus_value=resume_bonus_value if initial_cursor else 0,
                    )
                )
                shard_id += 1
                start = end
    return shards


def _run_standard_shard(plan: SmashCandidatePlan, shard: SmashShard, stop_event: Any = None) -> SmashShardResult:
    try:
        length_plan = plan.lengths[shard.length_plan_index]
        edit_window = bruteforce.edit_window(
            plan.data_hex,
            plan.data_offset,
            plan.chunk_length,
            plan.edit_mode,
            plan.bf_mode,
            length_plan.length,
        )
        if edit_window.replace_flag or edit_window.insert_flag:
            length_bytes = edit_window.length_bytes
        else:
            length_bytes = None

        hits: list[SmashCandidateHit] = []
        tested = 0
        next_inner_index = int(shard.start_inner_index)
        for inner_index, candidate in enumerate(
            specs.iter_product_values(length_plan.chunk_data, length_plan.color_type)
        ):
            if inner_index < shard.start_inner_index:
                continue
            if inner_index >= shard.end_inner_index:
                break
            if _stop_is_set(stop_event):
                return SmashShardResult(
                    shard=shard,
                    tested=tested,
                    next_inner_index=next_inner_index,
                    hits=tuple(hits),
                    stopped=True,
                )
            brute_bytes = bruteforce.build_candidate_bytes(
                candidate,
                length_plan.chunk_format,
                plan.bf_mode,
                struct_indexes=plan.struct_indexes,
                to_bryte=edit_window.to_bryte,
            )
            attempt = bruteforce.prepare_candidate_attempt(
                plan.chunk_name,
                length_bytes,
                brute_bytes,
                brute_bytes,
                edit_window.before,
                edit_window.after,
                brute_length=plan.brute_length,
                brute_crc=plan.brute_crc,
                old_crc=plan.old_crc,
            )
            tested += 1
            next_inner_index = inner_index + 1
            if plan.old_crc:
                if not attempt.old_crc_match:
                    continue
            elif not _candidate_png_looks_valid(attempt.png_bytes):
                continue
            hits.append(
                SmashCandidateHit(
                    outer_index=length_plan.outer_index,
                    length=length_plan.length,
                    inner_index=inner_index,
                    brute_bytes=brute_bytes,
                    checksum=attempt.checksum,
                    full_new_data=attempt.full_new_data,
                    png_bytes=attempt.png_bytes,
                    old_crc_match=attempt.old_crc_match,
                )
            )
            if plan.old_crc:
                break
            if len(hits) >= 8:
                break
        return SmashShardResult(
            shard=shard,
            tested=tested,
            next_inner_index=next_inner_index,
            hits=tuple(hits),
        )
    except Exception as exc:
        return SmashShardResult(
            shard=shard,
            tested=0,
            next_inner_index=shard.start_inner_index,
            error=str(exc),
        )


def run_standard_shard(plan: SmashCandidatePlan, shard: SmashShard, stop_event: Any = None) -> SmashShardResult:
    with _worker_stderr_silenced():
        return _run_standard_shard(plan, shard, stop_event)


def _twobytes_result(
    shard: SmashShard,
    *,
    tested: int,
    next_byte_position: int,
    edit_kind_index: int = 0,
    stage: str = "",
    bonus_offset: int = 0,
    bonus_value: int = 0,
    hits: tuple[SmashCandidateHit, ...] = (),
    stopped: bool = False,
    error: str = "",
) -> SmashShardResult:
    inner_index = int(shard.inner_index if shard.inner_index is not None else shard.start_inner_index)
    return SmashShardResult(
        shard=shard,
        tested=tested,
        next_inner_index=inner_index + (0 if stopped else 1),
        hits=hits,
        stopped=stopped,
        error=error,
        next_byte_position=next_byte_position,
        edit_kind_index=edit_kind_index,
        stage=stage,
        bonus_offset=bonus_offset,
        bonus_value=bonus_value,
    )


def _twobytes_attempt_is_hit(plan: SmashCandidatePlan, attempt: bruteforce.BruteForceCandidateAttempt) -> bool:
    if plan.old_crc:
        return bool(attempt.old_crc_match)
    return _candidate_png_looks_valid(attempt.png_bytes)


def _run_twobytes_shard(plan: SmashCandidatePlan, shard: SmashShard, stop_event: Any = None) -> SmashShardResult:
    tested = 0
    hits: list[SmashCandidateHit] = []
    inner_index = int(shard.inner_index if shard.inner_index is not None else shard.start_inner_index)
    next_byte_position = int(shard.next_byte_position or shard.byte_start)
    edit_kind_cursor = int(shard.edit_kind_index)
    stage_cursor = str(shard.stage or "")
    bonus_offset_cursor = int(shard.bonus_offset)
    bonus_value_cursor = int(shard.bonus_value)

    try:
        length_plan = plan.lengths[shard.length_plan_index]
        edit_window = bruteforce.edit_window(
            plan.data_hex,
            plan.data_offset,
            plan.chunk_length,
            plan.edit_mode,
            plan.bf_mode,
            length_plan.length,
        )
        brute_bytes = _twobytes_candidate_bytes(plan, length_plan, inner_index, edit_window)
        if brute_bytes is None:
            return _twobytes_result(
                shard,
                tested=0,
                next_byte_position=shard.byte_end,
                error="TwoBytes candidate index %s is outside the search space." % inner_index,
            )

        brute_hex_len = len(brute_bytes.hex())
        total_positions = bruteforce.twobytes_scan_position_count(edit_window.to_brute, brute_hex_len)
        byte_start = max(0, int(shard.byte_start))
        byte_end = min(max(byte_start, int(shard.byte_end)), total_positions)
        position = max(byte_start, next_byte_position)
        edit_kinds = bruteforce.iter_twobytes_edit_kinds(plan.edit_mode, plan.chunk_name)

        while position < byte_end:
            needle = position * 2
            start_edit_kind = edit_kind_cursor if position == next_byte_position else 0
            for edit_kind_index, edit_kind in enumerate(edit_kinds):
                if edit_kind_index < start_edit_kind:
                    continue
                if _stop_is_set(stop_event):
                    return _twobytes_result(
                        shard,
                        tested=tested,
                        next_byte_position=position,
                        edit_kind_index=edit_kind_index,
                        stage="direct",
                        hits=tuple(hits),
                        stopped=True,
                    )

                candidate_data = bruteforce.twobytes_candidate_data(
                    edit_window.to_brute,
                    brute_bytes,
                    needle,
                    edit_kind,
                )
                attempt = bruteforce.prepare_candidate_attempt(
                    plan.chunk_name,
                    candidate_data.length_bytes,
                    brute_bytes,
                    candidate_data.data,
                    edit_window.before,
                    edit_window.after,
                    brute_length=plan.brute_length,
                    brute_crc=plan.brute_crc,
                    old_crc=plan.old_crc,
                )
                tested += 1
                if _twobytes_attempt_is_hit(plan, attempt):
                    hits.append(
                        SmashCandidateHit(
                            outer_index=length_plan.outer_index,
                            length=length_plan.length,
                            inner_index=inner_index,
                            brute_bytes=brute_bytes,
                            checksum=attempt.checksum,
                            full_new_data=attempt.full_new_data,
                            png_bytes=attempt.png_bytes,
                            old_crc_match=attempt.old_crc_match,
                            edit_kind=edit_kind,
                            bonus=False,
                        )
                    )
                    if plan.old_crc or len(hits) >= 8:
                        return _twobytes_result(
                            shard,
                            tested=tested,
                            next_byte_position=position,
                            edit_kind_index=edit_kind_index,
                            stage="direct",
                            hits=tuple(hits),
                        )

                if plan.brute_level <= 0:
                    continue

                start_bonus_offset = 0
                start_bonus_value = 0
                if (
                    position == next_byte_position
                    and edit_kind_index == edit_kind_cursor
                    and stage_cursor == "bonus"
                ):
                    start_bonus_offset = max(0, bonus_offset_cursor)
                    start_bonus_value = max(0, bonus_value_cursor)
                for bonus_offset, bonus_value, bonus_data in bruteforce.iter_twobytes_bonus_data_with_cursor(
                    candidate_data.bonus_hex,
                    new_data_len=len(candidate_data.data),
                    skipped_hex_offset=needle,
                    skipped_hex_len=brute_hex_len,
                    start_hex_offset=start_bonus_offset,
                    start_value=start_bonus_value,
                ):
                    if _stop_is_set(stop_event):
                        return _twobytes_result(
                            shard,
                            tested=tested,
                            next_byte_position=position,
                            edit_kind_index=edit_kind_index,
                            stage="bonus",
                            bonus_offset=bonus_offset,
                            bonus_value=bonus_value,
                            hits=tuple(hits),
                            stopped=True,
                        )
                    length_bytes = len(bonus_data).to_bytes(4, "big")
                    attempt = bruteforce.prepare_candidate_attempt(
                        plan.chunk_name,
                        length_bytes,
                        bonus_data,
                        bonus_data,
                        edit_window.before,
                        edit_window.after,
                        brute_length=plan.brute_length,
                        brute_crc=plan.brute_crc,
                        old_crc=plan.old_crc,
                    )
                    tested += 1
                    if not _twobytes_attempt_is_hit(plan, attempt):
                        continue
                    hits.append(
                        SmashCandidateHit(
                            outer_index=length_plan.outer_index,
                            length=length_plan.length,
                            inner_index=inner_index,
                            brute_bytes=brute_bytes,
                            checksum=attempt.checksum,
                            full_new_data=attempt.full_new_data,
                            png_bytes=attempt.png_bytes,
                            old_crc_match=attempt.old_crc_match,
                            edit_kind=bruteforce.twobytes_bonus_edit_kind(plan.old_crc, edit_kind),
                            bonus=True,
                        )
                    )
                    if plan.old_crc or len(hits) >= 8:
                        return _twobytes_result(
                            shard,
                            tested=tested,
                            next_byte_position=position,
                            edit_kind_index=edit_kind_index,
                            stage="bonus",
                            bonus_offset=bonus_offset,
                            bonus_value=bonus_value,
                            hits=tuple(hits),
                        )
            position += 1
            edit_kind_cursor = 0
            stage_cursor = ""
            bonus_offset_cursor = 0
            bonus_value_cursor = 0

        return _twobytes_result(
            shard,
            tested=tested,
            next_byte_position=byte_end,
            hits=tuple(hits),
        )
    except Exception as exc:
        return _twobytes_result(
            shard,
            tested=tested,
            next_byte_position=next_byte_position,
            edit_kind_index=edit_kind_cursor,
            stage=stage_cursor,
            bonus_offset=bonus_offset_cursor,
            bonus_value=bonus_value_cursor,
            error=str(exc),
        )


def run_twobytes_shard(plan: SmashCandidatePlan, shard: SmashShard, stop_event: Any = None) -> SmashShardResult:
    with _worker_stderr_silenced():
        return _run_twobytes_shard(plan, shard, stop_event)


class SmashBackend:
    name = "base"

    def supports(self, plan: SmashCandidatePlan) -> bool:
        return False

    def run_shard(self, plan: SmashCandidatePlan, shard: SmashShard, stop_event: Any = None) -> SmashShardResult:
        raise NotImplementedError


class SmashSerialBackend(SmashBackend):
    name = "cpu-serial"

    def supports(self, plan: SmashCandidatePlan) -> bool:
        return True

    def run_shard(self, plan: SmashCandidatePlan, shard: SmashShard, stop_event: Any = None) -> SmashShardResult:
        if shard.kind == "twobytes":
            return run_twobytes_shard(plan, shard, stop_event)
        return run_standard_shard(plan, shard, stop_event)


class SmashParallelBackend(SmashBackend):
    name = "cpu-parallel"

    def supports(self, plan: SmashCandidatePlan) -> bool:
        return True

    def run_shard(self, plan: SmashCandidatePlan, shard: SmashShard, stop_event: Any = None) -> SmashShardResult:
        if shard.kind == "twobytes":
            return run_twobytes_shard(plan, shard, stop_event)
        return run_standard_shard(plan, shard, stop_event)


class SmashOpenCLBackend(SmashBackend):
    name = "opencl"

    def supports(self, plan: SmashCandidatePlan) -> bool:
        return False

    def run_shard(self, plan: SmashCandidatePlan, shard: SmashShard, stop_event: Any = None) -> SmashShardResult:
        return SmashShardResult(
            shard=shard,
            tested=0,
            next_inner_index=shard.start_inner_index,
            error="OpenCL backend is not implemented yet.",
        )
