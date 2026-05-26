from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable

from . import ui


Colorizer = Callable[[str, Any], Any]

COFFEE_ART = (
    "   ( (",
    "    ) )",
    "  ........",
    "  |      |]",
    "  \\      /",
    "   `----'",
)


@dataclass(frozen=True)
class FogSegment:
    label: str
    state: str = "seen"


@dataclass(frozen=True)
class FogOfWarMap:
    segments: tuple[FogSegment, ...]
    current_label: str
    current_state: str
    data_left_bytes: int | None
    reached_iend: bool
    sample_name: str = ""


def _chunk_label(chunk: Any) -> str:
    if isinstance(chunk, bytes):
        return chunk.decode("ascii", errors="replace")
    return str(chunk)


def _compact_seen_chunks(chunks: Iterable[Any]) -> tuple[FogSegment, ...]:
    labels = [
        _chunk_label(chunk)
        for chunk in chunks
        if _chunk_label(chunk) != "PNG"
    ]
    segments: list[FogSegment] = []
    index = 0
    while index < len(labels):
        label = labels[index]
        count = 1
        while index + count < len(labels) and labels[index + count] == label:
            count += 1
        display = "%sx%s" % (label, count) if count > 1 else label
        segments.append(FogSegment(display, "seen"))
        index += count
    return tuple(segments)


def _data_left_bytes(data_hex: str, offset: Any) -> int | None:
    try:
        offset_index = int(offset)
    except (TypeError, ValueError):
        return None
    return max(0, int((len(data_hex) - offset_index) / 2))


def build_map(
    chunks_history: Iterable[Any],
    current_chunk: Any,
    *,
    data_hex: str,
    current_offset: Any,
    error: bool,
    sample_name: str = "",
) -> FogOfWarMap:
    history = tuple(chunks_history)
    current_label = _chunk_label(current_chunk)
    reached_iend = bool(history and _chunk_label(history[-1]) == "IEND")
    return FogOfWarMap(
        segments=_compact_seen_chunks(history),
        current_label=current_label,
        current_state="error" if error else "current",
        data_left_bytes=None if reached_iend else _data_left_bytes(data_hex, current_offset),
        reached_iend=reached_iend,
        sample_name=sample_name,
    )


def _segment_text(segment: FogSegment, color: Colorizer) -> str:
    return str(color("green", "[%s]" % segment.label))


def _current_text(fog_map: FogOfWarMap, color: Colorizer) -> str:
    if fog_map.current_state == "error":
        return str(color("red", "[!%s!]" % fog_map.current_label))
    return str(color("yellow", "[>%s<]" % fog_map.current_label))


def _tail_text(fog_map: FogOfWarMap, color: Colorizer) -> str:
    if fog_map.reached_iend:
        return str(color("green", " done"))
    if fog_map.data_left_bytes is None:
        return str(color("blue", "........ data left"))
    return str(color("blue", "........ %s bytes left" % fog_map.data_left_bytes))


def _render_line(fog_map: FogOfWarMap, *, color: Colorizer) -> str:
    pieces = [str(color("purple", "[PNG]"))]
    pieces.extend(_segment_text(segment, color) for segment in fog_map.segments)
    if not fog_map.reached_iend:
        pieces.append(_current_text(fog_map, color))
    pieces.append(_tail_text(fog_map, color))
    return "".join(pieces)


def _border(visible_length: int, left: str, right: str, color: Colorizer) -> str:
    return str(color("white", left + ("━" * visible_length) + right))


def _center_line(text: str, width: int, color: Colorizer) -> str:
    centered = str(text).center(width)
    return str(color("white", centered))


def _center_block(lines: tuple[str, ...], width: int, color: Colorizer) -> str:
    block_width = max(ui.legacy_visible_length(line) for line in lines)
    padding = " " * max(0, int((width - block_width) / 2))
    return "\n".join(str(color("white", "%s%s" % (padding, line))) for line in lines)


def _center_header(fog_map: FogOfWarMap, width: int, color: Colorizer) -> str:
    lines: list[str] = []
    if fog_map.sample_name:
        lines.append(_center_line(fog_map.sample_name, width, color))
    lines.append(_center_block(COFFEE_ART, width, color))
    return "\n".join(lines)


def _body_line(fog_map: FogOfWarMap, *, color: Colorizer) -> str:
    inner_line = _render_line(fog_map, color=color)
    right_tail = "" if fog_map.reached_iend else str(color("blue", "...."))
    return "%s%s" % (inner_line, right_tail)


def visible_body_width(fog_map: FogOfWarMap, *, color: Colorizer) -> int:
    return ui.legacy_visible_length(_body_line(fog_map, color=color))


def render_header(fog_map: FogOfWarMap, *, color: Colorizer, width: int | None = None) -> str:
    body_width = width or visible_body_width(fog_map, color=color)
    border_width = body_width + 4
    return "\n%s" % _center_header(fog_map, border_width, color)


def render(fog_map: FogOfWarMap, *, color: Colorizer) -> str:
    body_line = _body_line(fog_map, color=color)
    body_width = ui.legacy_visible_length(body_line)
    header = render_header(fog_map, color=color, width=body_width)
    top = _border(body_width, "╭─", "─╮", color)
    bottom = _border(body_width, "╰─", "─╯", color)
    line = "  %s" % body_line
    return "%s\n%s\n%s\n%s" % (header, top, line, bottom)
