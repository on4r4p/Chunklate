from __future__ import annotations

import builtins
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from . import prompts, sorting


LegacyCall = Callable[..., Any]


@dataclass(frozen=True)
class ChunkNameContext:
    chunks: tuple[bytes, ...]
    all_chunks: tuple[bytes, ...]
    chunks_history: tuple[bytes, ...]
    original_chunk_type: bytes
    original_chunk_length: str
    current_type_offset: int
    current_type_offset_hex: str
    idat_average_length: Any
    original_next_chunk: Any
    next_chunk_offset: Any
    debug: bool = False
    pause_debug: bool = False


@dataclass(frozen=True)
class ChunkNameRuntime:
    candy: LegacyCall
    emit: LegacyCall
    checkpoint: LegacyCall
    pause: LegacyCall
    end: LegacyCall
    betterror: LegacyCall
    name_shift: LegacyCall
    check_chunk_order: LegacyCall
    nearby_chunk: LegacyCall
    save_clone: LegacyCall
    crc_matches: LegacyCall
    save_auto_name: LegacyCall
    unknown_private_critical_removal: LegacyCall
    ask_pokemon_choice: LegacyCall


def _color(runtime: ChunkNameRuntime, color: str, value: Any) -> Any:
    return runtime.candy("Color", color, value)


def _emoj(runtime: ChunkNameRuntime, value: str) -> Any:
    return runtime.candy("Emoj", value)


def _ctype_bytes(runtime: ChunkNameRuntime, chunk_type: Any) -> bytes:
    if type(chunk_type) == bytes:
        return chunk_type
    try:
        return bytes.fromhex(chunk_type)
    except Exception as exc:
        runtime.betterror(exc, "CheckChunkName")
        return chunk_type.encode(errors="ignore")


def _ctype_letters(chunk_type: Any) -> list[str]:
    if type(chunk_type) == bytes:
        return [item.lower() for item in chunk_type.decode(errors="ignore")]
    return [item.lower() for item in chunk_type]


def _scrabble_candidates(chunk_type: Any, candidates: list[bytes]) -> list[str]:
    ctype_letters = _ctype_letters(chunk_type)
    bingo_list: list[str] = []
    for name in candidates:
        bingo = 0
        chunk_letters = [item.lower() for item in name.decode(errors="ignore")]
        for left, right in zip(ctype_letters, chunk_letters):
            if left == right:
                bingo += 1
        bingo_list.append(str(bingo) + " " + name.decode(errors="ignore"))

    bingo_list.sort(key=sorting.natural_sort_key)
    return bingo_list[::-1]


def _best_bingo_count(bingo_list: list[str], best_score: str) -> int:
    return len([item.count(best_score) for item in bingo_list if int(item.count(best_score)) > 0])


def _run_name_shift_probe(
    runtime: ChunkNameRuntime,
    context: ChunkNameContext,
    from_error: Any,
) -> Any:
    shifted_bit = runtime.name_shift()
    if not shifted_bit:
        return None

    solved_msg = "-Chunk length has been corrupted due to some missing bytes."
    fixed = shifted_bit[0]
    fixed_length = shifted_bit[1]
    fixed_offset = shifted_bit[2]
    return runtime.checkpoint(
        True,
        True,
        "CheckChunkName",
        context.original_chunk_type,
        [solved_msg],
        fixed,
        fixed_length,
        fixed_offset,
        solved_msg,
        from_error,
    )


def _run_pokemon_prompt(
    runtime: ChunkNameRuntime,
    context: ChunkNameContext,
    chunk_type: Any,
    last_chunk_type: bytes,
    chunk_length: Any,
    bingo_list: list[str],
) -> tuple[()] | None:
    runtime.candy("Title", "WHO'S THAT POKEMON !?:")
    runtime.candy("Cowsay", " Arg that's all gibberish ...", "com")
    runtime.emit(
        "\nI need you to choose something looking a like [%s] that is actually a real chunk name can you help ?\nOk Please select the right name for the chunk:\n"
        % _color(runtime, "purple", str(chunk_type))
    )

    for index, candidate in enumerate(bingo_list):
        runtime.emit(
            "Score %s ,if you choose this name enter number: %s"
            % (_color(runtime, "green", candidate), _color(runtime, "yellow", index))
        )

    runtime.emit("\nIf you feel as lost as me then this might be a Length Problem type : wtf")
    runtime.emit("\nOr Type quit to ...quit.\n")
    pokemon_choice = runtime.ask_pokemon_choice(
        len(bingo_list),
        lambda choice: runtime.emit("choice:%s" % choice),
    )

    if pokemon_choice.action == "select":
        answer = bingo_list[pokemon_choice.index].split(" ")[1]
        runtime.save_clone(
            answer.encode().hex(),
            context.current_type_offset,
            context.current_type_offset + 8,
            "-Found Chunk[%s] has wrong name at offset: %s\n-Chunk seems corrupted user has decided to choose Chunk[%s] as a replacement."
            % (
                context.original_chunk_type,
                context.current_type_offset_hex,
                bingo_list[pokemon_choice.index].encode(),
            ),
        )
        return ()

    if pokemon_choice.action == "quit":
        runtime.candy("Cowsay", " Take Care Bye !", "good")
        runtime.end()
        return None

    if pokemon_choice.action == "length":
        runtime.candy("Cowsay", " Fine , time to investigate that length..", "com")
        runtime.nearby_chunk(chunk_type, chunk_length, last_chunk_type, False)
        return ()

    return None


def run_brute_chunk(
    runtime: ChunkNameRuntime,
    context: ChunkNameContext,
    chunk_type: Any,
    last_chunk_type: bytes,
    chunk_length: Any,
    from_error: Any,
) -> Any:
    runtime.candy("Title", "Chunk Scrabble Solver:")
    if context.debug is True:
        runtime.emit(chunk_type)
        runtime.emit(last_chunk_type)
        runtime.emit(chunk_length)
        runtime.emit(from_error)
        if context.pause_debug is True:
            runtime.pause("Pause:Debug")

    runtime.candy(
        "Cowsay",
        "Before going any further i need to check something real quick...",
        "com",
    )
    shifted_result = _run_name_shift_probe(runtime, context, from_error)
    if shifted_result is not None:
        return shifted_result

    runtime.candy("Cowsay", " Maybe it's name got corrupted somehow. Let's see about that.", "com")
    excluded = runtime.check_chunk_order(last_chunk_type, "Fix")
    candidates = [name for name in context.chunks if name not in excluded]

    crc_matches = runtime.crc_matches(candidates)
    if len(crc_matches) == 1:
        chunk_name = crc_matches[0]
        runtime.emit("-" + str(_color(runtime, "green", "CRC Solved.")) + str(_emoj(runtime, "good")))
        runtime.candy(
            "Cowsay",
            " Stored CRC matches chunk name: %s"
            % _color(runtime, "green", chunk_name.decode(errors="ignore")),
            "good",
        )
        return runtime.save_auto_name(
            chunk_type,
            from_error,
            chunk_name,
            "stored CRC matched candidate chunk name",
        )

    bingo_list = _scrabble_candidates(chunk_type, candidates)
    best_bingo_score = bingo_list[0].split(" ")[0]
    best_bingo_name = bingo_list[0].split(" ")[1]
    best_bingo_count = _best_bingo_count(bingo_list, best_bingo_score)

    if best_bingo_count <= 2 and int(best_bingo_score) >= 2:
        runtime.emit("-" + str(_color(runtime, "green", "Scrabble Solved.")) + str(_emoj(runtime, "good")))
        runtime.candy(
            "Cowsay",
            " Ah looks like we've got a winner! :%s"
            % _color(runtime, "green", best_bingo_name),
            "good",
        )

        changed = str(len(chunk_type) - int(best_bingo_score))
        solved_msg = (
            "-Found Chunk[%s] has wrong name at offset: %s but BruteChunk changed %s bytes turning it into a valid Chunk name: %s"
            % (context.original_chunk_type, context.current_type_offset_hex, changed, best_bingo_name)
        )

        return runtime.checkpoint(
            True,
            True,
            "CheckChunkName",
            context.original_chunk_type,
            [solved_msg],
            best_bingo_name.encode().hex(),
            context.current_type_offset,
            context.current_type_offset + 8,
            context.original_chunk_type,
            solved_msg,
            from_error,
        )

    removal = runtime.unknown_private_critical_removal()
    if removal is not None:
        return removal

    return _run_pokemon_prompt(
        runtime,
        context,
        chunk_type,
        last_chunk_type,
        chunk_length,
        bingo_list,
    )


def run_check_chunk_name(
    runtime: ChunkNameRuntime,
    context: ChunkNameContext,
    chunk_type: Any,
    chunk_length: Any,
    last_chunk_type: bytes,
    next_chunk: Any = None,
) -> Any:
    ctype = _ctype_bytes(runtime, chunk_type)

    if next_chunk is not None:
        runtime.candy("Title", "Checking Next Chunk Type:", _color(runtime, "white", ctype))
    else:
        runtime.candy("Title", "Checking Current Chunk Type:", _color(runtime, "white", ctype))

    for name in context.all_chunks:
        if name.lower() == ctype.lower():
            if name == ctype:
                runtime.emit("\n-Chunk name:" + _color(runtime, "green", " OK! ") + _emoj(runtime, "good"))
                if next_chunk is None:
                    return runtime.checkpoint(
                        False,
                        False,
                        "CheckChunkName",
                        ctype,
                        ["-Name is valid for Chunk[%s]." % ctype],
                        next_chunk,
                    )
                return runtime.checkpoint(
                    False,
                    False,
                    "CheckChunkName",
                    ctype,
                    ["-Name is valid for next Chunk[%s]." % ctype],
                    next_chunk,
                )

            runtime.emit("\n-Chunk name:" + _color(runtime, "red", " FAILED! ") + _emoj(runtime, "bad"))
            runtime.emit("\nMonkey wanted Banana :%s" % _color(runtime, "green", name))
            runtime.emit("Monkey got Pullover :%s" % _color(runtime, "red", ctype))
            runtime.emit("")
            if next_chunk is None:
                return runtime.checkpoint(
                    True,
                    False,
                    "CheckChunkName",
                    ctype,
                    [
                        "-Found Chunk[%s] Wrong Ancillary in known Chunk name at offset: %s"
                        % (context.original_chunk_type, context.current_type_offset_hex)
                    ],
                    context.current_type_offset_hex,
                    context.current_type_offset,
                    context.current_type_offset + 8,
                    context.original_chunk_type,
                    name,
                    next_chunk,
                )
            return runtime.checkpoint(
                True,
                False,
                "CheckChunkName",
                ctype,
                [
                    "-Found Next Chunk[%s] Wrong Ancillary in known Chunk name at offset: %s"
                    % (context.original_chunk_type, context.current_type_offset_hex)
                ],
                context.current_type_offset_hex,
                context.current_type_offset,
                context.current_type_offset + 8,
                context.original_chunk_type,
                name,
                next_chunk,
            )

    runtime.emit("\n-Chunk name:" + _color(runtime, "red", " FAILED! ") + _emoj(runtime, "bad"))
    if next_chunk is None:
        runtime.candy("Cowsay", "Mokay That could explain all this mess...", "com")
        if (
            (context.chunks_history[-1] == b"IDAT")
            and (context.idat_average_length != int(chunk_length, 16))
            and context.original_next_chunk != b"IEND"
        ):
            return runtime.checkpoint(
                True,
                False,
                "CheckChunkName",
                ctype,
                [
                    "-Found Chunk[%s] has Wrong Chunk name at offset: %s and length is not the same than before."
                    % (ctype, context.current_type_offset_hex)
                ],
                ctype,
                chunk_length,
                context.current_type_offset,
                last_chunk_type,
                next_chunk,
            )
        return runtime.checkpoint(
            True,
            False,
            "CheckChunkName",
            ctype,
            ["-Found Chunk[%s] has Wrong Chunk name at offset: %s" % (ctype, context.current_type_offset_hex)],
            ctype,
            chunk_length,
            context.current_type_offset,
            last_chunk_type,
            next_chunk,
        )

    runtime.candy(
        "Cowsay",
        "But let's ignore it for now we will see about that later ...",
        "com",
    )
    return runtime.checkpoint(
        True,
        False,
        "CheckChunkName",
        ctype,
        [
            "-Found Next Chunk[%s] has Wrong Chunk name after Chunk[%s] "
            % (context.original_next_chunk, last_chunk_type)
        ],
        context.original_next_chunk,
        chunk_length,
        context.next_chunk_offset,
        last_chunk_type,
        next_chunk,
    )


def ask_pokemon_choice_with_input(asker, candidate_count: int, on_invalid):
    return prompts.ask_pokemon_choice(asker, candidate_count, on_invalid=on_invalid)


def build_chunk_name_runtime_from_namespace(namespace: dict[str, Any]) -> ChunkNameRuntime:
    return ChunkNameRuntime(
        candy=namespace["Candy"],
        emit=namespace["PRINT"],
        checkpoint=namespace["CheckPoint"],
        pause=namespace["Pause"],
        end=namespace["TheEnd"],
        betterror=namespace["Betterror"],
        name_shift=namespace["NameShift"],
        check_chunk_order=namespace["CheckChunkOrder"],
        nearby_chunk=namespace["NearbyChunk"],
        save_clone=namespace["SaveClone"],
        crc_matches=namespace["BruteChunk_Crc_Matches"],
        save_auto_name=namespace["BruteChunk_Save_Auto_Name"],
        unknown_private_critical_removal=lambda: namespace["FixItFelix_Try_Automatic_Repair"](
            "unknown_private_critical_removal"
        ),
        ask_pokemon_choice=lambda count, on_invalid: prompts.ask_pokemon_choice(
            builtins.input,
            count,
            on_invalid=on_invalid,
        ),
    )


def build_chunk_name_context_from_namespace(namespace: dict[str, Any]) -> ChunkNameContext:
    return ChunkNameContext(
        chunks=tuple(namespace["CHUNKS"]),
        all_chunks=tuple(namespace["ALLCHUNKS"]),
        chunks_history=tuple(namespace["Chunks_History"]),
        original_chunk_type=namespace["Orig_CT"],
        original_chunk_length=namespace["Orig_CL"],
        current_type_offset=namespace["CToffI"],
        current_type_offset_hex=namespace["CToffX"],
        idat_average_length=namespace["IDAT_Avg_Len"],
        original_next_chunk=namespace["Orig_NC"],
        next_chunk_offset=namespace["NCoffI"],
        debug=namespace["DEBUG"],
        pause_debug=namespace["PAUSEDEBUG"],
    )


def save_auto_name_from_namespace(
    namespace: dict[str, Any],
    chunk_type: Any,
    from_error: Any,
    chunk_name: bytes,
    reason: str,
) -> Any:
    if type(chunk_type) == bytes:
        chunk_type_bytes = chunk_type
    else:
        chunk_type_bytes = str(chunk_type).encode(errors="ignore")

    changed = sum(1 for old, new in zip(chunk_type_bytes, chunk_name) if old != new)
    chunk_name_text = chunk_name.decode(errors="ignore")
    solved_msg = (
        "-Found Chunk[%s] has wrong name at offset: %s but BruteChunk changed %s bytes "
        "turning it into a valid Chunk name: %s (%s)"
        % (
            namespace["Orig_CT"],
            namespace["CToffX"],
            changed,
            chunk_name_text,
            reason,
        )
    )

    return namespace["CheckPoint"](
        True,
        True,
        "CheckChunkName",
        namespace["Orig_CT"],
        [solved_msg],
        chunk_name.hex(),
        namespace["CToffI"],
        namespace["CToffI"] + 8,
        namespace["Orig_CT"],
        solved_msg,
        from_error,
    )


def run_brute_chunk_from_namespace(
    namespace: dict[str, Any],
    chunk_type: Any,
    last_chunk_type: bytes,
    chunk_length: Any,
    from_error: Any,
    *,
    runner: LegacyCall = run_brute_chunk,
) -> Any:
    return runner(
        build_chunk_name_runtime_from_namespace(namespace),
        build_chunk_name_context_from_namespace(namespace),
        chunk_type,
        last_chunk_type,
        chunk_length,
        from_error,
    )


def run_check_chunk_name_from_namespace(
    namespace: dict[str, Any],
    chunk_type: Any,
    chunk_length: Any,
    last_chunk_type: bytes,
    next_chunk: Any = None,
    *,
    runner: LegacyCall = run_check_chunk_name,
) -> Any:
    return runner(
        build_chunk_name_runtime_from_namespace(namespace),
        build_chunk_name_context_from_namespace(namespace),
        chunk_type,
        chunk_length,
        last_chunk_type,
        next_chunk,
    )
