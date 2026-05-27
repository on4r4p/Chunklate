from __future__ import annotations

from collections.abc import Callable, MutableSequence
from dataclasses import dataclass
from typing import Any

from . import name_shift, runtime_state


LegacyCall = Callable[..., Any]


@dataclass(frozen=True)
class NameShiftRuntime:
    candy: LegacyCall
    emit: LegacyCall
    pause: LegacyCall
    end: LegacyCall
    spec_length: LegacyCall
    side_notes: MutableSequence[Any]
    raw_print: LegacyCall = print


@dataclass(frozen=True)
class NameShiftContext:
    name_shift_context: runtime_state.NameShiftRuntimeContext
    chunks_history: tuple[bytes, ...]
    debug: bool = False
    pause_debug: bool = False


def _color(runtime: NameShiftRuntime, color: str, value: Any) -> Any:
    return runtime.candy("Color", color, value)


def _chunky(runtime: NameShiftRuntime, value: str) -> Any:
    return runtime.candy("Chunky", value)


def _todo(runtime: NameShiftRuntime) -> Any:
    return _color(runtime, "yellow", "\n-ToDo")


def _debug_history(runtime: NameShiftRuntime, context: NameShiftContext) -> None:
    if context.debug is not True:
        return

    for chunk, index in zip(
        context.chunks_history,
        context.name_shift_context.chunks_history_index,
    ):
        runtime.emit("\nCame accross that chunk: %s" % chunk)
        runtime.emit("With those index: %s" % index)
    if context.pause_debug is True:
        runtime.pause("-Debug Pause Press Return to continue:")


def _emit_candidate(
    runtime: NameShiftRuntime,
    context: NameShiftContext,
    candidate: name_shift.NameShiftCandidate,
) -> None:
    runtime.emit(
        name_shift.current_chunk_value_line(
            context.name_shift_context.current_type_offset,
            name_shift.current_chunk_value(
                context.name_shift_context.data_hex,
                context.name_shift_context.current_type_offset,
            ),
        )
    )
    runtime.side_notes.append(
        name_shift.found_chunk_note(
            candidate.search_index,
            candidate.type_offset,
            candidate.chunk_name,
        )
    )
    if candidate.is_before:
        runtime.emit(
            _color(
                runtime,
                "green",
                name_shift.valid_chunk_before_line(
                    candidate.chunk_name,
                    candidate.good_offset,
                ),
            )
        )
    elif candidate.is_after:
        runtime.emit(
            _color(
                runtime,
                "green",
                name_shift.valid_chunk_after_line(
                    candidate.chunk_name,
                    candidate.good_offset,
                ),
            )
        )


def _handle_crc_failure(
    runtime: NameShiftRuntime,
    crc: str,
    checksum: str,
) -> None:
    runtime.emit(
        name_shift.crc_failed_line(
            _color(runtime, "red", " FAILED! "),
            _chunky(runtime, "bad"),
        )
    )
    if name_shift.crc_value_is_empty(crc, checksum):
        runtime.emit(name_shift.monkey_wanted_line(_color(runtime, "green", checksum)))
        runtime.emit(name_shift.monkey_got_line(_color(runtime, "red", crc)))
        runtime.candy("Cowsay", name_shift.missed_something_message(), "com")
        runtime.emit(_todo(runtime))
        runtime.end()

    if name_shift.checksum_needs_legacy_padding(checksum):
        checksum = name_shift.legacy_pad_checksum(checksum)
        runtime.emit(name_shift.monkey_wanted_line(_color(runtime, "green", checksum)))
        runtime.emit(name_shift.monkey_got_line(_color(runtime, "red", crc)))
        runtime.emit(_todo(runtime))
        runtime.end()


def _handle_matching_crc(
    runtime: NameShiftRuntime,
    context: NameShiftContext,
    candidate: name_shift.NameShiftCandidate,
    crc_view: name_shift.ShiftedChunkCrcView,
) -> list[object] | None:
    runtime.emit(name_shift.crc_ok_line(_color(runtime, "green", " OK "), _chunky(runtime, "good")))
    runtime.candy("Cowsay", "Found the culprit!", "good")
    runtime.side_notes.append(name_shift.crc_valid_note())

    fixed = crc_view.fixed_hex
    if candidate.type_offset > context.name_shift_context.current_type_offset:
        last_chunk = name_shift.last_history_chunk_before_offset(
            context.name_shift_context.chunks_history_index,
            context.name_shift_context.current_type_offset,
        )
        if last_chunk is not None:
            if name_shift.extra_bytes_align_with_previous_chunk(
                candidate.type_offset,
                last_chunk.end,
                candidate.good_offset,
            ):
                runtime.side_notes.append(name_shift.extra_bytes_found_note())
                runtime.candy(
                    "Cowsay",
                    "Found some extra bytes for some reason.. let's fix this now .",
                    "good",
                )
                return name_shift.extra_bytes_repair_result(
                    fixed,
                    candidate.good_offset,
                    context.name_shift_context.current_type_offset,
                )

            runtime.raw_print("bad")
            runtime.raw_print(
                name_shift.extra_bytes_expected_offset(
                    last_chunk.end,
                    candidate.good_offset,
                )
            )
            runtime.emit(_todo(runtime))
            runtime.end()
            return None

    else:
        runtime.candy(
            "Cowsay",
            "So there was some missing bytes after all let's fix this now .",
            "good",
        )
        runtime.side_notes.append(name_shift.missing_bytes_found_note())
        return name_shift.missing_bytes_repair_result(
            fixed,
            candidate.good_offset,
            context.name_shift_context.current_type_offset,
        )

    return None


def run_name_shift(runtime: NameShiftRuntime, context: NameShiftContext) -> Any:
    runtime.candy("Title", "Checking around Chunk's position:")
    _debug_history(runtime, context)

    candidate = name_shift.find_shifted_chunk_name(
        context.name_shift_context.data_hex,
        context.name_shift_context.current_type_offset,
        context.name_shift_context.known_chunks,
    )
    if candidate is None:
        return False

    _emit_candidate(runtime, context, candidate)
    runtime.candy("Cowsay", "Mokay ..Maybe some bytes are missing somewhere ..", "com")

    file_length = context.name_shift_context.data_hex[
        candidate.type_offset - 8 : candidate.type_offset
    ]
    real_length = runtime.spec_length(candidate.chunk_name, file_length)

    if name_shift.length_part_is_corrupted(file_length, real_length):
        runtime.candy("Cowsay", "I knew there was something odd..", "bad")
        runtime.candy("Cowsay", "That error seems to come from the length part .", "good")
        crc_view = name_shift.shifted_chunk_crc_view(
            context.name_shift_context.data_hex,
            candidate.type_offset,
            candidate.chunk_name,
            real_length,
        )

        if context.debug:
            runtime.emit("-Crc from file: %s" % (str(crc_view.checksum)))
            runtime.emit("-Actual Crc: %s\n" % (str(crc_view.file_crc)))

        if crc_view.crc_matches:
            result = _handle_matching_crc(runtime, context, candidate, crc_view)
            if result is not None:
                return result
        else:
            _handle_crc_failure(runtime, crc_view.file_crc, crc_view.checksum)

        runtime.side_notes.append(name_shift.corrupted_length_note(candidate.chunk_name))
    else:
        runtime.emit(_todo(runtime))
        runtime.end()

    runtime.end()
    return None


def build_name_shift_runtime_from_namespace(namespace: dict[str, Any]) -> NameShiftRuntime:
    return NameShiftRuntime(
        candy=namespace["Candy"],
        emit=namespace["PRINT"],
        pause=namespace["Pause"],
        end=namespace["TheEnd"],
        spec_length=namespace["SpecLength"],
        side_notes=namespace["SideNotes"],
        raw_print=namespace.get("print", print),
    )


def build_name_shift_context_from_namespace(namespace: dict[str, Any]) -> NameShiftContext:
    return NameShiftContext(
        name_shift_context=runtime_state.name_shift_runtime_context(
            namespace["DATAX"],
            namespace["CToffI"],
            namespace["Chunks_History_Index"],
            namespace["ALLCHUNKS"],
        ),
        chunks_history=tuple(namespace["Chunks_History"]),
        debug=namespace["DEBUG"],
        pause_debug=namespace["PAUSEDEBUG"],
    )


def run_name_shift_from_namespace(
    namespace: dict[str, Any],
    *,
    runner: LegacyCall = run_name_shift,
) -> Any:
    return runner(
        build_name_shift_runtime_from_namespace(namespace),
        build_name_shift_context_from_namespace(namespace),
    )
