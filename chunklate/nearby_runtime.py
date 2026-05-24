from __future__ import annotations

from collections.abc import Callable, MutableSequence
from dataclasses import dataclass
from typing import Any

from . import nearby


LegacyCall = Callable[..., Any]


@dataclass(frozen=True)
class NearbyChunkContext:
    data_hex: str
    chunks: tuple[bytes, ...]
    all_chunks: tuple[bytes, ...]
    current_length_offset: int
    current_length_offset_hex: str
    current_data_offset_byte: int
    chunks_history: tuple[bytes, ...]
    chunks_history_index: tuple[str, ...]
    original_chunk_type: bytes
    original_chunk_length: str
    sample_name: str
    debug: bool = False
    pause_debug: bool = False
    pause_error: bool = False


@dataclass(frozen=True)
class NearbyChunkRuntime:
    candy: LegacyCall
    emit: LegacyCall
    checkpoint: LegacyCall
    check_chunk_order: LegacyCall
    clean_extra_bytes: LegacyCall
    double_check: LegacyCall
    fix_it_felix: LegacyCall
    betterror: LegacyCall
    pause: LegacyCall
    end: LegacyCall
    get_bad_critical: Callable[[], Any]
    side_notes: MutableSequence[Any]


def _color(runtime: NearbyChunkRuntime, color: str, value: Any) -> Any:
    return runtime.candy("Color", color, value)


def _emoj(runtime: NearbyChunkRuntime, value: str) -> Any:
    return runtime.candy("Emoj", value)


def _emit_decode_error(
    runtime: NearbyChunkRuntime,
    context: NearbyChunkContext,
    error: Exception,
    scope_hex: str,
) -> None:
    runtime.betterror(error, "NearbyChunk")
    if context.debug is True:
        runtime.emit(_color(runtime, "red", "Error:%s") % _color(runtime, "yellow", error))
        runtime.emit(_color(runtime, "red", "Scopex:%s") % _color(runtime, "yellow", scope_hex))
        if context.pause_debug is True or context.pause_error is True:
            runtime.pause("Pause Debug")
    runtime.end()


def _emit_excluded_trap(
    runtime: NearbyChunkRuntime,
    context: NearbyChunkContext,
    found_chunk: bytes,
) -> None:
    runtime.emit(
        "\n-Chunk position is %s %s\n"
        % (_color(runtime, "red", "Not Valid "), _emoj(runtime, "bad"))
    )
    runtime.candy(
        "Cowsay",
        " But that chunk [%s] is not supposed to be here .."
        % _color(runtime, "red", found_chunk),
        "com",
    )
    runtime.candy("Cowsay", " ITS A TRAP !! RUN !!!!!!!", "bad")
    runtime.candy(
        "Cowsay",
        " I seriously doubt that i could be of any uses with this one ..",
        "com",
    )
    runtime.candy(
        "Cowsay",
        " If you are sure %s is a png i can try to fill the gap but i cannot guarantee any result.."
        % _color(runtime, "white", context.sample_name),
        "com",
    )
    if b"IHDR" not in context.chunks_history:
        runtime.candy("Cowsay", " Especially without IHDR chunk..", "bad")
    runtime.emit(_color(runtime, "yellow", "\n-ToDo"))
    runtime.side_notes.append("-NearbyChunk:Missplaced Chunk")
    runtime.end()


def _build_length_repair(
    context: NearbyChunkContext,
    chunk_type: bytes,
    last_chunk_type: bytes,
    found_chunk: bytes,
    found_chunk_type_offset: int,
):
    if not any(candidate == chunk_type for candidate in context.chunks):
        return nearby.unknown_chunk_length_repair(
            data_hex=context.data_hex,
            display_chunk=chunk_type,
            checkpoint_length_offset=context.current_length_offset,
            chunks_history=context.chunks_history,
            chunks_history_index=context.chunks_history_index,
            last_chunk_type=last_chunk_type,
            found_chunk=found_chunk,
            found_chunk_type_offset=found_chunk_type_offset,
        )

    return nearby.known_chunk_length_repair(
        display_chunk=context.original_chunk_type,
        old_length=context.original_chunk_length,
        current_length_offset=context.current_length_offset,
        current_length_offset_hex=context.current_length_offset_hex,
        current_data_offset_byte=context.current_data_offset_byte,
        found_chunk=found_chunk,
        found_chunk_type_offset=found_chunk_type_offset,
    )


def _route_length_repair(
    runtime: NearbyChunkRuntime,
    context: NearbyChunkContext,
    repair,
    from_error: Any,
) -> Any:
    runtime.emit(
        "-Chunk position is %s %s\n"
        % (_color(runtime, "green", "Valid "), _emoj(runtime, "good"))
    )
    runtime.emit(repair.print_message)
    return runtime.checkpoint(
        True,
        True,
        "NearbyChunk",
        context.original_chunk_type,
        [repair.solved_message],
        repair.fixed_length,
        repair.replace_start,
        repair.replace_end,
        context.original_chunk_type,
        from_error,
    )


def _scan_for_nearby_chunk(
    runtime: NearbyChunkRuntime,
    context: NearbyChunkContext,
    chunk_type: bytes,
    chunk_length: Any,
    last_chunk_type: bytes,
    excluded: list[bytes],
    from_error: Any,
) -> Any:
    needle = nearby.initial_search_needle(
        chunk_type=chunk_type,
        known_chunks=context.chunks,
        current_length_offset=context.current_length_offset,
        chunks_history=context.chunks_history,
        chunks_history_index=context.chunks_history_index,
        last_chunk_type=last_chunk_type,
    )

    if context.debug:
        for line in nearby.nearby_debug_lines(
            chunk_type,
            last_chunk_type,
            chunk_length,
            context.original_chunk_type,
            needle,
            context.data_hex,
        ):
            runtime.emit(line)

    while needle < len(context.data_hex):
        if needle + 8 > len(context.data_hex):
            runtime.emit(_color(runtime, "yellow", "-End of File"))
            break

        scope_hex = context.data_hex[needle : needle + 8]
        try:
            scope = nearby.decode_scope(scope_hex)
        except Exception as exc:
            _emit_decode_error(runtime, context, exc, scope_hex)
            break

        needle_byte = int(needle / 2)
        needle_hex = hex(needle_byte)

        for found_chunk in context.chunks:
            if not nearby.scope_matches_chunk(scope, found_chunk):
                continue

            runtime.candy("Cowsay", " Bingo!!!", "good")
            runtime.emit(
                "-Found the closest Chunk to our position:%s at offset %s %s"
                % (
                    _color(runtime, "green", found_chunk),
                    _color(runtime, "blue", needle_hex),
                    _color(runtime, "yellow", needle_byte),
                )
            )
            if found_chunk in excluded:
                _emit_excluded_trap(runtime, context, found_chunk)
                return None

            repair = _build_length_repair(
                context,
                chunk_type,
                last_chunk_type,
                found_chunk,
                needle,
            )
            if repair is None:
                continue
            return _route_length_repair(runtime, context, repair, from_error)

        needle += 1

    return None


def run_nearby_chunk(
    runtime: NearbyChunkRuntime,
    context: NearbyChunkContext,
    chunk_type: bytes,
    chunk_length: Any,
    last_chunk_type: bytes,
    double_check: bool,
    from_error: Any = None,
) -> Any:
    runtime.candy("Title", "Chunk N Destroy:")
    runtime.candy("Cowsay", "Now where shall i start..?", "com")

    if double_check is False:
        excluded = runtime.check_chunk_order(last_chunk_type, "Fix")
    else:
        runtime.candy("Cowsay", " ==Safety Off==", "com")
        excluded = []

    clean_extra_bytes = runtime.clean_extra_bytes(chunk_type, last_chunk_type, excluded)
    if clean_extra_bytes is not None:
        return clean_extra_bytes

    result = _scan_for_nearby_chunk(
        runtime,
        context,
        chunk_type,
        chunk_length,
        last_chunk_type,
        list(excluded),
        from_error,
    )
    if result is not None:
        return result

    if double_check is True:
        runtime.candy("Cowsay", " ...??NOTHING AGAIN!?!?!?!?", "bad")
        runtime.check_chunk_order(last_chunk_type, "Critical")
        bad_critical = runtime.get_bad_critical()
        if not bad_critical:
            runtime.candy("Cowsay", "THEY PLAYED US LIKE A DAMN FIDDLE !!!", "bad")
            runtime.candy(
                "Cowsay",
                " ...??Just Reach the EOF and found nothing!!Can't do much about that sorry ...",
                "com",
            )
            runtime.end()
        else:
            runtime.side_notes.append("-NearbyChunk:Critical Chunk Missing: %s" % bad_critical)
            return runtime.fix_it_felix(chunk_type)
    else:
        runtime.candy(
            "Cowsay",
            " ...??Just Reach the EOF and found nothing!!Can't do much about that sorry ...",
            "com",
        )

    if chunk_length is not None and chunk_type is not None:
        runtime.double_check(chunk_type, chunk_length, last_chunk_type)

    return ()
