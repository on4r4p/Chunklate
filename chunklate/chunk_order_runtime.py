from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from . import chunk_order, nearby, runtime_state


LegacyCall = Callable[..., Any]


@dataclass(frozen=True)
class CheckChunkOrderContext:
    chunk_order_context: runtime_state.ChunkOrderRuntimeContext
    minimal_chunks: tuple[bytes, ...]
    pandora_box: Any
    before_plte: tuple[bytes, ...]
    before_idat2: tuple[bytes, ...]
    chunks: tuple[bytes, ...]
    after_plte: tuple[bytes, ...]
    before_idat: tuple[bytes, ...]
    ihdr_color: Any
    no_order_chunks: tuple[bytes, ...]
    debug: bool = False
    pause_debug: bool = False


@dataclass(frozen=True)
class CheckChunkOrderRuntime:
    candy: LegacyCall
    emit: LegacyCall
    checkpoint: LegacyCall
    pause: LegacyCall
    end: LegacyCall
    betterror: LegacyCall
    get_warning: Callable[[], bool]
    set_warning: Callable[[bool], Any]
    raw_print: LegacyCall = print


@dataclass(frozen=True)
class TheGoodPlaceContext:
    data_hex: str
    chunks_history: tuple[bytes, ...]
    chunks_history_index: tuple[str, ...]
    pandora_box: Any
    debug: bool = False
    pause_debug: bool = False


@dataclass(frozen=True)
class TheGoodPlaceRuntime:
    candy: LegacyCall
    emit: LegacyCall
    checkpoint: LegacyCall
    pause: LegacyCall
    end: LegacyCall


def _color(runtime: Any, color: str, value: Any) -> Any:
    return runtime.candy("Color", color, value)


def _emoj(runtime: Any, value: str) -> Any:
    return runtime.candy("Emoj", value)


def _title(runtime: Any, value: str) -> Any:
    return runtime.candy("Title", value)


def _cowsay(runtime: Any, message: str, mood: str) -> Any:
    return runtime.candy("Cowsay", message, mood)


def run_the_good_place(
    runtime: TheGoodPlaceRuntime,
    context: TheGoodPlaceContext,
    missplaced_chunk_name: bytes,
    missplaced_chunk_pos: int,
    to_fix_chunk_name: bytes,
) -> Any:
    _title(runtime, "TheGoodPlace :")
    _cowsay(runtime, "Mkay, so what do we have here ..", "com")

    bad_position = nearby.parse_history_index(
        context.chunks_history_index[missplaced_chunk_pos]
    )
    bad_pos = bad_position.position
    bad_start = bad_position.start
    bad_end = bad_position.end

    for key in context.pandora_box:
        if "Missplaced" in str(key):
            runtime.emit("\n-\033[1;31;49mCriticalHit\033[m: %s" % key)

    fix_position = nearby.find_history_chunk_position(
        context.chunks_history,
        context.chunks_history_index,
        to_fix_chunk_name,
    )

    if fix_position is None:
        runtime.emit(
            "-Missing Data %s %s"
            % (_color(runtime, "red", "Has Not Been Found"), _emoj(runtime, "bad"))
        )
        _cowsay(runtime, "This is not good..", "bad")
        return runtime.checkpoint(
            *chunk_order.the_good_place_missing_checkpoint_args(
                to_fix_chunk_name,
                bad_pos,
                bad_start,
                bad_end,
            )
        )

    runtime.emit(
        "\n-Found %s:[%s] at Chunk Position:%s Starting at:%s Ending at:%s %s"
        % (
            _color(runtime, "green", "Missing Data"),
            to_fix_chunk_name,
            fix_position.position,
            fix_position.start,
            fix_position.end,
            _emoj(runtime, "good"),
        )
    )
    _cowsay(runtime, "Sounds good to me , where's my rubber tape already ?", "good")
    rubber_tape = nearby.relocate_missing_chunk(
        context.data_hex,
        source_start=fix_position.start,
        source_end=fix_position.end,
        target_start=bad_start,
    )
    return runtime.checkpoint(
        *chunk_order.the_good_place_found_checkpoint_args(
            to_fix_chunk_name,
            fix_position,
            rubber_tape,
        )
    )


def _build_context(context: CheckChunkOrderContext):
    chunk_order_context = chunk_order.build_chunk_order_context(
        context.chunk_order_context.chunks_history,
        context.chunk_order_context.unique_chunks,
    )
    return list(chunk_order_context.used_chunks), list(chunk_order_context.excluded_chunks)


def _emit_failed_or_ok(
    runtime: CheckChunkOrderRuntime,
    to_fix: Sequence[str],
) -> None:
    if chunk_order.has_findings(to_fix):
        runtime.checkpoint(*chunk_order.missplaced_checkpoint_args(to_fix))
        runtime.emit(
            chunk_order.missplaced_failed_print_line(
                _color(runtime, "red", " FAILED "),
                _emoj(runtime, "bad"),
            )
        )
    else:
        runtime.emit(
            chunk_order.missplaced_ok_print_line(
                _color(runtime, "green", " OK "),
                _emoj(runtime, "good"),
            )
        )


def run_critical_mode(
    runtime: CheckChunkOrderRuntime,
    context: CheckChunkOrderContext,
) -> None:
    _title(runtime, "Critical Chunks Check :")
    missing = chunk_order.missing_critical_chunks(
        context.chunk_order_context.chunks_history,
        context.minimal_chunks,
    )
    for chunk in missing:
        runtime.emit(
            chunk_order.critical_missing_print_line(
                chunk,
                _color(runtime, "red", "Missing"),
            )
        )

    to_fix = list(chunk_order.missing_critical_infos(missing))
    if chunk_order.has_findings(to_fix):
        runtime.checkpoint(*chunk_order.critical_checkpoint_args(to_fix))
        return

    runtime.emit(
        chunk_order.errors_ok_print_line(
            _color(runtime, "green", " OK "),
            _emoj(runtime, "good"),
        )
    )


def run_the_good_place_mode(
    runtime: CheckChunkOrderRuntime,
    context: CheckChunkOrderContext,
    lastchunk: bytes,
) -> Any:
    _title(runtime, "Missplaced Chunks Check:")
    to_fix: list[str] = []
    used_chunks, excluded = _build_context(context)

    _cowsay(
        runtime,
        chunk_order.seen_chunks_message(
            context.chunk_order_context.sample_name,
            used_chunks,
            "\n ",
        ),
        "good",
    )

    if chunk_order.legacy_flags_unique_chunk_as_multiple(
        lastchunk,
        excluded,
        context.chunk_order_context.unique_chunks,
    ):
        runtime.emit(
            chunk_order.multiple_chunk_print_line(
                _color(runtime, "red", chunk_order.decode_chunk_name(lastchunk)),
                _color(runtime, "red", "cannot"),
            )
        )
        to_fix.append(chunk_order.multiple_chunk_info())

    if chunk_order.png_signature_is_misplaced(context.chunk_order_context.chunks_history):
        runtime.emit(
            chunk_order.png_signature_misplaced_print_line(
                _color(runtime, "red", "Before"),
                _emoj(runtime, "bad"),
            )
        )
        to_fix.append(chunk_order.missplaced_info())

    if chunk_order.ihdr_is_misplaced(context.chunk_order_context.chunks_history):
        done = chunk_order.ihdr_misplacement_already_recorded(context.pandora_box)
        if done is False:
            runtime.emit(
                chunk_order.ihdr_misplaced_print_line(
                    _color(runtime, "red", "Before all the other chunks"),
                    _emoj(runtime, "bad"),
                )
            )
            return runtime.checkpoint(
                *chunk_order.ihdr_misplacement_checkpoint_args(
                    context.chunk_order_context.chunks_history
                )
            )

        if context.debug is True:
            runtime.emit(
                "-Already Saved : Missplaced [%s]:Should be IHDR Instead At Chunk Number:%s"
                % (
                    context.chunk_order_context.chunks_history[-1],
                    str(len(context.chunk_order_context.chunks_history) - 1),
                )
            )
            if context.pause_debug is True:
                runtime.pause("Pause Debug")

    if chunk_order.must_appear_before_plte(lastchunk, used_chunks, context.before_plte):
        runtime.emit(
            chunk_order.before_plte_print_line(
                _color(
                    runtime,
                    "red",
                    chunk_order.decode_chunk_name(lastchunk) + " is missplaced",
                ),
                chunk_order.decode_chunk_name(lastchunk),
                _emoj(runtime, "bad"),
            )
        )
        to_fix.append(chunk_order.missplaced_before_plte_info(lastchunk))

    if chunk_order.must_appear_before_idat(lastchunk, used_chunks, excluded, context.before_idat2):
        runtime.emit(
            chunk_order.before_idat_print_line(
                _color(
                    runtime,
                    "red",
                    chunk_order.decode_chunk_name(lastchunk) + " is missplaced",
                ),
                chunk_order.decode_chunk_name(lastchunk),
                _emoj(runtime, "bad"),
            )
        )
        to_fix.append(chunk_order.missplaced_info())

    _emit_failed_or_ok(runtime, to_fix)
    return None


def run_fix_mode(
    runtime: CheckChunkOrderRuntime,
    context: CheckChunkOrderContext,
    lastchunk: bytes,
) -> list[bytes] | tuple[bytes, ...]:
    _title(runtime, "Checking Already Used Chunks :")
    header_exclusions = chunk_order.only_ihdr_allowed_after_png_header(
        context.chunk_order_context.chunks_history,
        context.chunks,
    )
    if header_exclusions is not None:
        _cowsay(runtime, chunk_order.only_ihdr_after_png_header_message(), "com")
        return list(header_exclusions)

    used_chunks, excluded = _build_context(context)
    _cowsay(
        runtime,
        chunk_order.seen_chunks_message(
            context.chunk_order_context.sample_name,
            used_chunks,
        ),
        "good",
    )

    to_fix: list[str] = []
    if not chunk_order.has_idat(used_chunks):
        if chunk_order.must_stay_before_plte_without_ihdr(
            lastchunk,
            used_chunks,
            context.before_plte,
        ):
            excluded = list(
                chunk_order.extend_exclusions_not_in(
                    excluded,
                    context.chunks,
                    context.before_plte,
                )
            )
            _cowsay(
                runtime,
                chunk_order.before_plte_forget_message(
                    _color(runtime, "green", chunk_order.decode_chunk_name(lastchunk)),
                    chunk_order.decode_chunk_names(excluded),
                ),
                "bad",
            )

        if chunk_order.must_follow_plte(lastchunk, context.after_plte):
            excluded = list(
                chunk_order.extend_exclusions_in(
                    excluded,
                    context.chunks,
                    context.before_plte,
                )
            )
            _cowsay(
                runtime,
                chunk_order.after_plte_forget_message(
                    lastchunk,
                    chunk_order.decode_chunk_names(excluded),
                ),
                "bad",
            )

        excluded = list(chunk_order.add_iend_exclusion(excluded))

    elif chunk_order.has_idat(used_chunks):
        excluded = list(
            chunk_order.extend_exclusions_before_idat_after_idat(
                excluded,
                context.chunks,
                context.before_idat,
            )
        )

        if chunk_order.is_indexed_color(context.ihdr_color):
            runtime.raw_print("excluded:\n", excluded)
            if not chunk_order.indexed_idat_previous_chunk_is_plte(used_chunks):
                indexed_message, plte_message, todo_message = (
                    chunk_order.indexed_idat_without_plte_messages()
                )
                _cowsay(runtime, indexed_message, "com")
                _cowsay(runtime, plte_message, "com")
                _cowsay(runtime, todo_message, "bad")
                runtime.emit(_color(runtime, "yellow", chunk_order.todo_info()))
                runtime.end()

        elif chunk_order.may_have_missing_critical_palette(
            context.ihdr_color,
            context.chunk_order_context.chunks_history,
        ):
            if runtime.get_warning() is False:
                runtime.set_warning(True)
                to_fix.append(chunk_order.missing_critical_palette_info())
                _cowsay(
                    runtime,
                    chunk_order.missing_critical_palette_warning_message(
                        _color(runtime, "red", "Critical Palette"),
                        _color(runtime, "yellow", "Missing"),
                    ),
                    "com",
                )

        if chunk_order.is_idat_chunk(lastchunk):
            _cowsay(
                runtime,
                chunk_order.idat_next_candidates_message(context.no_order_chunks),
                "com",
            )

    return excluded


def run_check_chunk_order(
    runtime: CheckChunkOrderRuntime,
    context: CheckChunkOrderContext,
    lastchunk: bytes | str,
    mode: str,
) -> Any:
    try:
        lastchunk = chunk_order.as_chunk_bytes(lastchunk)
    except AttributeError as exc:
        runtime.betterror(exc, "CheckChunkOrder")

    if mode == "Critical":
        return run_critical_mode(runtime, context)
    if mode == "TheGoodPlace":
        return run_the_good_place_mode(runtime, context, lastchunk)
    if mode == "Fix":
        return run_fix_mode(runtime, context, lastchunk)
    return None


def build_check_chunk_order_context_from_namespace(namespace: dict[str, Any]) -> CheckChunkOrderContext:
    return CheckChunkOrderContext(
        chunk_order_context=runtime_state.chunk_order_runtime_context(
            namespace["Sample_Name"],
            namespace["Chunks_History"],
            namespace["UNIQUE_CHUNK"],
        ),
        minimal_chunks=tuple(namespace["MINIMAL_CHUNKS"]),
        pandora_box=namespace["PandoraBox"],
        before_plte=tuple(namespace["BEFORE_PLTE"]),
        before_idat2=tuple(namespace["BEFORE_IDAT2"]),
        chunks=tuple(namespace["CHUNKS"]),
        after_plte=tuple(namespace["AFTER_PLTE"]),
        before_idat=tuple(namespace["BEFORE_IDAT"]),
        ihdr_color=namespace["IHDR_Color"],
        no_order_chunks=tuple(namespace["NO_ORDER_CHUNKS"]),
        debug=namespace["DEBUG"],
        pause_debug=namespace["PAUSEDEBUG"],
    )


def build_check_chunk_order_runtime_from_namespace(namespace: dict[str, Any]) -> CheckChunkOrderRuntime:
    def set_warning(value):
        namespace["Warning"] = value

    return CheckChunkOrderRuntime(
        candy=namespace["Candy"],
        emit=namespace["PRINT"],
        checkpoint=namespace["CheckPoint"],
        pause=namespace["Pause"],
        end=namespace["TheEnd"],
        betterror=namespace["Betterror"],
        get_warning=lambda: namespace["Warning"],
        set_warning=set_warning,
        raw_print=print,
    )


def run_check_chunk_order_from_namespace(
    namespace: dict[str, Any],
    lastchunk: bytes | str,
    mode: str,
    *,
    runner: LegacyCall = run_check_chunk_order,
) -> Any:
    return runner(
        build_check_chunk_order_runtime_from_namespace(namespace),
        build_check_chunk_order_context_from_namespace(namespace),
        lastchunk,
        mode,
    )
