from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from typing import Any


LEGACY_BAD_CHUNK_LABEL = "johnnybytesme"


@dataclass(frozen=True)
class WrongCrcTools:
    replacement_crc: Any
    start: Any
    end: Any
    chunk: Any
    offset: Any
    old_crc: Any
    chunk_length: Any = None
    data_offset: Any = None


@dataclass(frozen=True)
class WrongChunkNameTools:
    chunk_type: Any
    chunk_length: Any
    chunk_type_offset: Any
    previous_chunk: Any
    next_marker: Any = None


@dataclass(frozen=True)
class NoNextChunkTools:
    chunk_type: Any
    chunk_length: Any
    previous_chunk: Any


@dataclass(frozen=True)
class DummyChunkTools:
    fixed_data: Any
    dummy_data_length: Any
    bad_position: Any
    bad_start: Any
    bad_end: Any
    from_error: Any


def chunk_label(chunk: Any) -> Any:
    if type(chunk) != bytes:
        return chunk
    try:
        return chunk.decode(errors="ignore")
    except Exception:
        return LEGACY_BAD_CHUNK_LABEL


def tool_prefix(chunk: Any) -> str:
    return str(chunk_label(chunk)) + "_Tool_"


def build_tools(chunk: Any, toolkit: tuple[Any, ...]) -> dict[str, Any]:
    prefix = tool_prefix(chunk)
    return {prefix + str(index): tool for index, tool in enumerate(toolkit)}


def tool_key(prefix: str, index: int | str) -> str:
    return prefix + str(index)


def tool_value(tools: Mapping[str, Any], prefix: str, index: int | str) -> Any:
    return tools[tool_key(prefix, index)]


def optional_tool_value(
    tools: Mapping[str, Any],
    prefix: str,
    index: int | str,
    default: Any = None,
) -> Any:
    return tools.get(tool_key(prefix, index), default)


def wrong_crc_tools(tools: Mapping[str, Any], prefix: str) -> WrongCrcTools:
    return WrongCrcTools(
        replacement_crc=tool_value(tools, prefix, 0),
        start=tool_value(tools, prefix, 1),
        end=tool_value(tools, prefix, 2),
        chunk=tool_value(tools, prefix, 3),
        offset=tool_value(tools, prefix, 4),
        old_crc=tool_value(tools, prefix, 5),
        chunk_length=optional_tool_value(tools, prefix, 6),
        data_offset=optional_tool_value(tools, prefix, 7),
    )


def wrong_chunk_name_tools(tools: Mapping[str, Any], prefix: str) -> WrongChunkNameTools:
    return WrongChunkNameTools(
        chunk_type=tool_value(tools, prefix, 0),
        chunk_length=tool_value(tools, prefix, 1),
        chunk_type_offset=tool_value(tools, prefix, 2),
        previous_chunk=tool_value(tools, prefix, 3),
        next_marker=optional_tool_value(tools, prefix, 4),
    )


def no_next_chunk_tools(tools: Mapping[str, Any], prefix: str) -> NoNextChunkTools:
    return NoNextChunkTools(
        chunk_type=tool_value(tools, prefix, 0),
        chunk_length=tool_value(tools, prefix, 1),
        previous_chunk=tool_value(tools, prefix, 2),
    )


def dummy_chunk_tools(tools: Mapping[str, Any], prefix: str) -> DummyChunkTools:
    return DummyChunkTools(
        fixed_data=tool_value(tools, prefix, 0),
        dummy_data_length=tool_value(tools, prefix, 1),
        bad_position=tool_value(tools, prefix, 2),
        bad_start=tool_value(tools, prefix, 3),
        bad_end=tool_value(tools, prefix, 4),
        from_error=tool_value(tools, prefix, 5),
    )


def chunk_name_from_text(text: Any, known_chunks: list[bytes] | tuple[bytes, ...]) -> str:
    text = str(text)
    return "".join(
        chunk.decode(errors="ignore")
        for chunk in known_chunks
        if chunk.decode(errors="ignore") in text
    )


def chunk_name_from_tool_keys(tools: Mapping[str, Any], known_chunks: list[bytes] | tuple[bytes, ...]) -> str:
    return chunk_name_from_text(" ".join(str(tool) for tool in tools), known_chunks)


def next_error_number(pandora_box: Mapping[str, Any], function: Any) -> int:
    number = 0
    for key in pandora_box:
        while key.startswith(str(function) + "_Error_" + str(number)):
            number += 1
    return number


def add_pandora_error(
    pandora_box: MutableMapping[str, Any],
    function: Any,
    info: Any,
    tools: Mapping[str, Any],
) -> str:
    number = next_error_number(pandora_box, function)
    key = str(function) + "_Error_" + str(number) + ":" + str(info)
    pandora_box[key] = tools
    return key


def add_cornucopia_fix(
    cornucopia: MutableMapping[Any, Any],
    key: Any,
    tools: Mapping[str, Any],
) -> Any:
    cornucopia[key] = tools
    return key


def remember_sample(
    pandemonium: MutableMapping[Any, Any],
    ark_of_covenant: MutableMapping[Any, Any],
    sample: Any,
    pandora_box: MutableMapping[str, Any],
    cornucopia: MutableMapping[Any, Any],
) -> None:
    # Preserve the legacy shared-reference snapshot. Relics relies on the same
    # dict objects for now; switching to a copy is a separate behavior change.
    pandemonium[sample] = pandora_box
    ark_of_covenant[sample] = cornucopia


def question_hash(store: Mapping[Any, Mapping[str, Any]], key: Any, prefix: str) -> int:
    try:
        return hash(
            str(store[key][prefix + "0"])
            + str(store[key][prefix + "1"])
            + str(store[key][prefix + "2"])
        )
    except Exception:
        return hash(key)
