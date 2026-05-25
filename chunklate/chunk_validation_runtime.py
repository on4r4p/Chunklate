from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .png import (
    legacy_crc_checkpoint_args,
    legacy_crc_debug_lines,
    legacy_crc_decision,
    legacy_crc_monkey_lines,
    legacy_length_checkpoint_args,
    legacy_length_decision,
)


LegacyCall = Callable[..., Any]


@dataclass(frozen=True)
class CheckLengthContext:
    data_bytes: bytes
    current_length_offset: int
    previous_chunk: bytes
    idat_average_length: int


@dataclass(frozen=True)
class ChecksumContext:
    current_length_offset: int
    crc_offset: int
    crc_offset_hex: str
    original_chunk_type: bytes
    original_crc: str
    original_length: str
    current_data_offset: int
    chunks_history: Any
    chunks_history_index: Any
    debug: bool = False


@dataclass(frozen=True)
class ChunkValidationRuntime:
    candy: LegacyCall
    emit: LegacyCall
    checkpoint: LegacyCall
    end: LegacyCall
    chunk_story_add_if_no_next: LegacyCall


def build_chunk_validation_runtime_from_namespace(namespace: dict[str, Any]) -> ChunkValidationRuntime:
    return ChunkValidationRuntime(
        candy=namespace["Candy"],
        emit=namespace["PRINT"],
        checkpoint=namespace["CheckPoint"],
        end=namespace["TheEnd"],
        chunk_story_add_if_no_next=namespace["chunk_story"].add_if_no_next,
    )


def build_check_length_context_from_namespace(namespace: dict[str, Any]) -> CheckLengthContext:
    return CheckLengthContext(
        data_bytes=namespace["DATA_BYTES"],
        current_length_offset=namespace["CLoffI"],
        previous_chunk=namespace["Chunks_History"][-1],
        idat_average_length=namespace["IDAT_Avg_Len"],
    )


def build_checksum_context_from_namespace(namespace: dict[str, Any]) -> ChecksumContext:
    return ChecksumContext(
        current_length_offset=namespace["CLoffI"],
        crc_offset=namespace["CrcoffI"],
        crc_offset_hex=namespace["CrcoffX"],
        original_chunk_type=namespace["Orig_CT"],
        original_crc=namespace["Orig_CRC"],
        original_length=namespace["Orig_CL"],
        current_data_offset=namespace["CDoffI"],
        chunks_history=namespace["Chunks_History"],
        chunks_history_index=namespace["Chunks_History_Index"],
        debug=namespace["DEBUG"],
    )


def _color(runtime: ChunkValidationRuntime, color: str, value: Any) -> Any:
    return runtime.candy("Color", color, value)


def _emoj(runtime: ChunkValidationRuntime, value: str) -> Any:
    return runtime.candy("Emoj", value)


def run_check_length(
    runtime: ChunkValidationRuntime,
    context: CheckLengthContext,
    chunk_data: Any,
    chunk_length: str,
    chunk_type: bytes,
) -> Any:
    runtime.candy("Title", "Checking Data Length:", _color(runtime, "white", str(chunk_length)))
    decision = legacy_length_decision(
        context.data_bytes,
        context.current_length_offset,
        previous_chunk=context.previous_chunk,
        idat_average_length=context.idat_average_length,
    )

    runtime.candy(
        "Cowsay",
        " So ..The length part is saying that data is %s bytes long."
        % _color(runtime, "yellow", decision.declared_length),
        "com",
    )

    if decision.is_huge:
        runtime.candy("Cowsay", " Really!? That much ?", "com")

    if decision.idat_length_differs:
        runtime.candy("Cowsay", "Weird why does the length is not the same as before ?", "com")

    if decision.checkpoint_error:
        runtime.candy(
            "Cowsay",
            " ..And this is what iv found there ... : " + _color(runtime, "red", "[NOTHING]"),
            "com",
        )
    else:
        runtime.candy(
            "Cowsay",
            " ..So depending on that the next chunk seems to be : "
            + _color(runtime, "yellow", decision.next_chunk_type),
            "com",
        )

    return runtime.checkpoint(
        *legacy_length_checkpoint_args(
            decision,
            chunk_type,
            chunk_length,
            context.previous_chunk,
        )
    )


def run_check_length_from_namespace(
    namespace: dict[str, Any],
    chunk_data: Any,
    chunk_length: str,
    chunk_type: bytes,
    *,
    runner: LegacyCall = run_check_length,
) -> Any:
    return runner(
        build_chunk_validation_runtime_from_namespace(namespace),
        build_check_length_context_from_namespace(namespace),
        chunk_data,
        chunk_length,
        chunk_type,
    )


def _record_crc_chunk_story(
    runtime: ChunkValidationRuntime,
    context: ChecksumContext,
    next_chunk: Any,
    chunk_type: bytes,
) -> None:
    runtime.chunk_story_add_if_no_next(
        context.chunks_history,
        context.chunks_history_index,
        next_chunk,
        chunk_type,
        context.current_length_offset,
        context.crc_offset + 8,
        int(context.original_length, 16),
    )


def run_checksum(
    runtime: ChunkValidationRuntime,
    context: ChecksumContext,
    chunk_type_hex: str,
    chunk_data_hex: str,
    crc_hex: str,
    next_chunk: Any = None,
) -> Any:
    runtime.candy("Title", "Check Crc Validity:")
    decision = legacy_crc_decision(chunk_type_hex, chunk_data_hex, crc_hex)
    chunk_type = decision.chunk_type
    stored_crc = decision.stored_crc_hex
    checksum = decision.computed_crc_hex

    if context.debug:
        for line in legacy_crc_debug_lines(decision):
            runtime.emit(line)

    if decision.ok:
        runtime.emit("-Crc Check :" + _color(runtime, "green", " OK ") + _emoj(runtime, "good") + "\n")
        _record_crc_chunk_story(runtime, context, next_chunk, chunk_type)
        return runtime.checkpoint(
            *legacy_crc_checkpoint_args(
                decision,
                context.crc_offset,
                context.original_chunk_type,
                context.crc_offset_hex,
                context.original_crc,
                context.original_length,
                context.current_data_offset,
            )
        )

    runtime.emit("-Crc Check :" + _color(runtime, "red", " FAILED! ") + _emoj(runtime, "bad"))
    if len(stored_crc) == 0 or len(checksum) == 0:
        wanted, got = legacy_crc_monkey_lines(
            _color(runtime, "green", checksum),
            _color(runtime, "red", stored_crc),
        )
        runtime.emit(wanted)
        runtime.emit(got)
        runtime.candy("Cowsay", " Hold on a sec ... Must have missed something...", "com")
        runtime.emit("")
        runtime.end()

    checksum = decision.normalized_computed_crc
    wanted, got = legacy_crc_monkey_lines(
        _color(runtime, "green", checksum),
        _color(runtime, "red", stored_crc),
    )
    runtime.emit(wanted)
    runtime.emit(got)
    _record_crc_chunk_story(runtime, context, next_chunk, chunk_type)
    return runtime.checkpoint(
        *legacy_crc_checkpoint_args(
            decision,
            context.crc_offset,
            context.original_chunk_type,
            context.crc_offset_hex,
            context.original_crc,
            context.original_length,
            context.current_data_offset,
        )
    )


def run_checksum_from_namespace(
    namespace: dict[str, Any],
    chunk_type_hex: str,
    chunk_data_hex: str,
    crc_hex: str,
    next_chunk: Any = None,
    *,
    runner: LegacyCall = run_checksum,
) -> Any:
    return runner(
        build_chunk_validation_runtime_from_namespace(namespace),
        build_checksum_context_from_namespace(namespace),
        chunk_type_hex,
        chunk_data_hex,
        crc_hex,
        next_chunk,
    )
