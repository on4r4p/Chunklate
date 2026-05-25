from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from . import specs


LegacyCall = Callable[..., Any]


@dataclass(frozen=True)
class GetSpecRuntime:
    emit: LegacyCall
    candy: LegacyCall
    betterror: LegacyCall
    pause: LegacyCall
    end: LegacyCall
    max_resolution: Callable[[], int]
    refresh_idat_byte_count: Callable[[], int]
    current_year: Callable[[], int]


@dataclass(frozen=True)
class GetSpecContext:
    idat_byte_count: int
    brute_level: int
    ihdr_color: Any
    ihdr_height: Any
    ihdr_width: Any
    pandora_box: dict[Any, Any]
    cornucopia: dict[Any, Any]
    pandemonium: dict[Any, Any]
    allchunks: tuple[bytes, ...]
    skip_bad_crc: bool
    debug: bool = False
    pause_debug: bool = False
    pause_error: bool = False


def _emit_debug_header(
    runtime: GetSpecRuntime,
    get_chunk: bytes,
    mode: str,
    fields: list[str] | tuple[str, ...],
) -> None:
    runtime.emit("GetChunk:%s" % get_chunk)
    runtime.emit("Mode:%s" % mode)
    runtime.emit("Fields:%s" % fields)


def _emit_debug_context(
    runtime: GetSpecRuntime,
    spec_context: specs.GetSpecContext,
    get_chunk: bytes,
) -> None:
    if get_chunk in specs.GETSPEC_COLOR_CHUNKS:
        runtime.emit("-ColorType set to:%s" % spec_context.color_type)
    runtime.emit(
        "-Smalest resolution estimation based on file size: %s*%s"
        % (spec_context.min_resolution, spec_context.min_resolution)
    )


def run_getspec(
    runtime: GetSpecRuntime,
    context: GetSpecContext,
    get_chunk: bytes,
    mode: str,
    fields: list[str] | tuple[str, ...] = ("All",),
    struct_index: Any = None,
    iter_count: int = 1,
) -> Any:
    if context.debug:
        _emit_debug_header(runtime, get_chunk, mode, fields)

    idat_byte_count = context.idat_byte_count
    if idat_byte_count == 0:
        idat_byte_count = runtime.refresh_idat_byte_count()

    spec_context = specs.build_getspec_context(
        current_year=runtime.current_year(),
        chunk_name=get_chunk,
        mode=mode,
        idat_byte_count=idat_byte_count,
        max_resolution=runtime.max_resolution(),
        brute_level=context.brute_level,
        ihdr_color=context.ihdr_color,
        ihdr_height=context.ihdr_height,
        ihdr_width=context.ihdr_width,
        pandora_box=context.pandora_box,
        cornucopia=context.cornucopia,
        pandemonium=context.pandemonium,
        allchunks=context.allchunks,
        skip_bad_crc=context.skip_bad_crc,
    )

    if context.debug:
        _emit_debug_context(runtime, spec_context, get_chunk)

    try:
        result = specs.resolve_getspec(
            spec_context,
            get_chunk,
            fields,
            mode,
            struct_index,
            iter_count,
        )
    except (NameError, ValueError) as exc:
        runtime.betterror(exc, "GetSpec")
        if context.debug is True:
            runtime.emit(runtime.candy("Color", "red", "Error:%s") % runtime.candy("Color", "yellow", exc))
        if context.pause_debug is True or context.pause_error is True:
            runtime.pause("Pause Debug")
        runtime.end()
        return None

    if result is not None:
        return result

    runtime.emit("-Error in GetSpec: Didnt Found matching result")
    runtime.emit("GetColor:%s" % spec_context.color_type)
    runtime.emit("GetChunk:%s" % get_chunk)
    runtime.emit(runtime.candy("Color", "yellow", "\n-ToDo"))
    return None
