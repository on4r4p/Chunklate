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
    remember_later_iend: LegacyCall
    side_notes: MutableSequence[Any]


@dataclass(frozen=True)
class DoubleCheckContext:
    data_hex: str
    sample_name: str


@dataclass(frozen=True)
class DoubleCheckRuntime:
    candy: LegacyCall
    emit: LegacyCall
    end: LegacyCall
    nearby_chunk: LegacyCall


@dataclass(frozen=True)
class RemoveExtraBytesContext:
    data_hex: str
    current_length_offset: int
    known_chunks: tuple[bytes, ...]
    all_chunks: tuple[bytes, ...]


@dataclass(frozen=True)
class RemoveExtraBytesRuntime:
    save_clone: LegacyCall
    side_notes: MutableSequence[Any]


@dataclass(frozen=True)
class NearbyHandled:
    action: str


@dataclass
class NearbyScanFinds:
    counts: dict[bytes, int]

    @property
    def has_candidates(self) -> bool:
        return bool(self.counts)

    @property
    def idat_count(self) -> int:
        return self.counts.get(b"IDAT", 0)

    @property
    def found_iend(self) -> bool:
        return self.counts.get(b"IEND", 0) > 0

    def record(self, chunk: bytes) -> None:
        self.counts[chunk] = self.counts.get(chunk, 0) + 1


def _color(runtime: NearbyChunkRuntime, color: str, value: Any) -> Any:
    return runtime.candy("Color", color, value)


def _chunky(runtime: NearbyChunkRuntime, value: str) -> Any:
    return runtime.candy("Chunky", value)


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
        % (_color(runtime, "red", "Not Valid "), _chunky(runtime, "bad"))
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
        % (_color(runtime, "green", "Valid "), _chunky(runtime, "good"))
    )
    runtime.emit(repair.print_message)
    result = runtime.checkpoint(
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
    if result is None:
        return NearbyHandled("length_repair")
    return result


def _display_chunk_name(chunk_type: bytes) -> str:
    return chunk_type.decode("ascii", errors="replace")


def _emit_found_chunk(
    runtime: NearbyChunkRuntime,
    found_chunk: bytes,
    needle_hex: str,
    needle_byte: int,
) -> None:
    runtime.candy("Cowsay", " Bingo!!!", "good")
    runtime.emit(
        "-Found the closest Chunk to our position:%s at offset %s %s"
        % (
            _color(runtime, "green", found_chunk),
            _color(runtime, "blue", needle_hex),
            _color(runtime, "yellow", needle_byte),
        )
    )


def _idat_find_summary(finds: NearbyScanFinds) -> str:
    idat_count = finds.idat_count
    idat_label = "chunk" if idat_count == 1 else "chunks"
    if idat_count > 0 and finds.found_iend:
        return "I found %s possible IDAT %s and an IEND later." % (idat_count, idat_label)
    if idat_count > 0:
        return "I found %s possible IDAT %s, but no IEND later." % (idat_count, idat_label)
    return "I found an IEND later."


def _emit_scan_misalignment_summary(
    runtime: NearbyChunkRuntime,
    context: NearbyChunkContext,
    chunk_type: bytes,
    finds: NearbyScanFinds,
    double_check: bool,
) -> bool:
    if context.debug or not finds.has_candidates:
        return False
    if finds.idat_count < 1 and not finds.found_iend:
        return False

    runtime.candy("Cowsay", _idat_find_summary(finds), "good")
    if double_check:
        runtime.candy(
            "Cowsay",
            "Even with safety off, the current position still does not line up.",
            "bad",
        )
        runtime.candy(
            "Cowsay",
            "So %s is probably a symptom, not the crime scene. The bad length before it is still my prime suspect."
            % _display_chunk_name(chunk_type),
            "bad",
        )
        return True

    runtime.candy("Cowsay", "But the current position still does not line up.", "bad")
    runtime.candy(
        "Cowsay",
        "This smells more like a bad length before %s than a chunk-name-only problem."
        % _display_chunk_name(chunk_type),
        "bad",
    )
    return True


def _scan_for_nearby_chunk(
    runtime: NearbyChunkRuntime,
    context: NearbyChunkContext,
    chunk_type: bytes,
    chunk_length: Any,
    last_chunk_type: bytes,
    excluded: list[bytes],
    from_error: Any,
    double_check: bool,
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

    finds = NearbyScanFinds(counts={})

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

            finds.record(found_chunk)
            if context.debug:
                _emit_found_chunk(runtime, found_chunk, needle_hex, needle_byte)

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

    if finds.found_iend:
        runtime.remember_later_iend(context.sample_name, finds.idat_count, double_check)

    if _emit_scan_misalignment_summary(runtime, context, chunk_type, finds, double_check):
        return NearbyHandled("scan_summary")

    return None


def run_remove_extra_bytes_before_chunk(
    runtime: RemoveExtraBytesRuntime,
    context: RemoveExtraBytesContext,
    chunk_type: bytes,
    last_chunk_type: bytes,
    excluded: list[bytes],
) -> Any:
    candidate = nearby.extra_bytes_before_chunk_candidate(
        context.data_hex,
        current_length_offset=context.current_length_offset,
        chunk_type=chunk_type,
        known_chunks=context.known_chunks,
        all_chunks=context.all_chunks,
        excluded_chunks=excluded,
    )
    if candidate is None:
        return None

    solved_message = nearby.extra_bytes_solved_message(candidate, last_chunk_type)
    runtime.side_notes.append("-Remove_Extra_Bytes_Before_Chunk:%s" % solved_message)
    result = runtime.save_clone(
        "",
        context.current_length_offset,
        context.current_length_offset + (candidate.extra_bytes * 2),
        solved_message,
    )
    if result is None:
        return NearbyHandled("remove_extra_bytes")
    return result


def run_double_check(
    runtime: DoubleCheckRuntime,
    context: DoubleCheckContext,
    chunk_type: bytes,
    chunk_length: Any,
    last_chunk_type: bytes,
) -> Any:
    runtime.candy("Title", "Double Check:")
    runtime.candy(
        "Cowsay",
        "Or maybe am i missing something ? Just let me double check again just to be sure...",
        "com",
    )

    double_check_file_length = nearby.double_check_file_length(context.data_hex)
    if double_check_file_length.is_too_short:
        runtime.emit(
            "%s: %s is %s bytes long Png minimum size is 67 bytes ."
            % (
                runtime.candy("Color", "red", "-Wrong File Length"),
                runtime.candy("Color", "white", context.sample_name),
                runtime.candy("Color", "red", str(double_check_file_length.byte_length)),
            )
        )
        runtime.candy(
            "Cowsay",
            "ERrr...There are not enought byte in %s to be a valid png." % (context.sample_name),
            "bad",
        )
        runtime.candy("Cowsay", "I can't help you much further sorry.", "com")
        runtime.end()

    runtime.candy(
        "Cowsay",
        " But this time let's forget about the usual specifications of png format so This way i will be able to know if a chunk is missing somewhere.",
        "good",
    )

    return runtime.nearby_chunk(chunk_type, chunk_length, last_chunk_type, DoubleCheck=True)


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
        double_check,
    )
    scan_summary = isinstance(result, NearbyHandled) and result.action == "scan_summary"
    if result is not None and not scan_summary:
        return result

    if double_check is True:
        if not scan_summary:
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
        if not scan_summary:
            runtime.candy(
                "Cowsay",
                " ...??Just Reach the EOF and found nothing!!Can't do much about that sorry ...",
                "com",
            )

    if chunk_length is not None and chunk_type is not None:
        runtime.double_check(chunk_type, chunk_length, last_chunk_type)

    return ()


def build_remove_extra_bytes_runtime_from_namespace(namespace: dict[str, Any]) -> RemoveExtraBytesRuntime:
    return RemoveExtraBytesRuntime(
        save_clone=namespace["SaveClone"],
        side_notes=namespace["SideNotes"],
    )


def build_remove_extra_bytes_context_from_namespace(namespace: dict[str, Any]) -> RemoveExtraBytesContext:
    return RemoveExtraBytesContext(
        data_hex=namespace["DATAX"],
        current_length_offset=namespace["CLoffI"],
        known_chunks=tuple(namespace["CHUNKS"]),
        all_chunks=tuple(namespace["ALLCHUNKS"]),
    )


def run_remove_extra_bytes_before_chunk_from_namespace(
    namespace: dict[str, Any],
    chunk_type: bytes,
    last_chunk_type: bytes,
    excluded: list[bytes],
    *,
    runner: LegacyCall = run_remove_extra_bytes_before_chunk,
) -> Any:
    return runner(
        build_remove_extra_bytes_runtime_from_namespace(namespace),
        build_remove_extra_bytes_context_from_namespace(namespace),
        chunk_type,
        last_chunk_type,
        excluded,
    )


def build_double_check_runtime_from_namespace(namespace: dict[str, Any]) -> DoubleCheckRuntime:
    return DoubleCheckRuntime(
        candy=namespace["Candy"],
        emit=namespace["PRINT"],
        end=namespace["TheEnd"],
        nearby_chunk=namespace["NearbyChunk"],
    )


def build_double_check_context_from_namespace(namespace: dict[str, Any]) -> DoubleCheckContext:
    return DoubleCheckContext(
        data_hex=namespace["DATAX"],
        sample_name=namespace["Sample_Name"],
    )


def run_double_check_from_namespace(
    namespace: dict[str, Any],
    chunk_type: bytes,
    chunk_length: Any,
    last_chunk_type: bytes,
    *,
    runner: LegacyCall = run_double_check,
) -> Any:
    return runner(
        build_double_check_runtime_from_namespace(namespace),
        build_double_check_context_from_namespace(namespace),
        chunk_type,
        chunk_length,
        last_chunk_type,
    )


def build_nearby_chunk_runtime_from_namespace(namespace: dict[str, Any]) -> NearbyChunkRuntime:
    return NearbyChunkRuntime(
        candy=namespace["Candy"],
        emit=namespace["PRINT"],
        checkpoint=namespace["CheckPoint"],
        check_chunk_order=namespace["CheckChunkOrder"],
        clean_extra_bytes=namespace["Remove_Extra_Bytes_Before_Chunk"],
        double_check=namespace["Double_Check"],
        fix_it_felix=namespace["FixItFelix"],
        betterror=namespace["Betterror"],
        pause=namespace["Pause"],
        end=namespace["TheEnd"],
        get_bad_critical=lambda: namespace["Bad_Critical"],
        remember_later_iend=lambda sample_name, idat_count, double_check: namespace.__setitem__(
            "NEARBY_FOUND_LATER_IEND",
            {
                "sample_name": sample_name,
                "idat_count": idat_count,
                "double_check": double_check,
            },
        ),
        side_notes=namespace["SideNotes"],
    )


def build_nearby_chunk_context_from_namespace(namespace: dict[str, Any]) -> NearbyChunkContext:
    return NearbyChunkContext(
        data_hex=namespace["DATAX"],
        chunks=tuple(namespace["CHUNKS"]),
        all_chunks=tuple(namespace["ALLCHUNKS"]),
        current_length_offset=namespace["CLoffI"],
        current_length_offset_hex=namespace["CLoffX"],
        current_data_offset_byte=namespace["CDoffB"],
        chunks_history=tuple(namespace["Chunks_History"]),
        chunks_history_index=tuple(namespace["Chunks_History_Index"]),
        original_chunk_type=namespace["Orig_CT"],
        original_chunk_length=namespace["Orig_CL"],
        sample_name=namespace["Sample_Name"],
        debug=namespace["DEBUG"],
        pause_debug=namespace["PAUSEDEBUG"],
        pause_error=namespace["PAUSEERROR"],
    )


def run_nearby_chunk_from_namespace(
    namespace: dict[str, Any],
    chunk_type: bytes,
    chunk_length: Any,
    last_chunk_type: bytes,
    double_check: bool,
    from_error: Any = None,
    *,
    runner: LegacyCall = run_nearby_chunk,
) -> Any:
    return runner(
        build_nearby_chunk_runtime_from_namespace(namespace),
        build_nearby_chunk_context_from_namespace(namespace),
        chunk_type,
        chunk_length,
        last_chunk_type,
        double_check,
        from_error,
    )
