from __future__ import annotations

import os
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


@dataclass(frozen=True)
class WrongCrcRoute:
    source: Any
    error: Any
    chunk_name: str
    tool_prefix: str

    @property
    def is_current_file(self) -> bool:
        return self.source is None


@dataclass(frozen=True)
class DummyChunkRoute:
    source: Any
    error: Any
    chunk_name: str
    tool_prefix: str
    is_critical: bool


@dataclass(frozen=True)
class RelicErrorSummary:
    error: Any
    tools: tuple[tuple[str, Any], ...]


@dataclass(frozen=True)
class RelicSampleSummary:
    sample: Any
    errors: tuple[RelicErrorSummary, ...]


@dataclass(frozen=True)
class WrongCrcBrawlPlan:
    target_file: Any
    chunk: Any
    chunk_length: Any
    data_offset: Any
    from_error: Any
    old_crc: Any
    bf_mode: str | None = None
    brute_length: bool | None = None


@dataclass(frozen=True)
class DummyChunkBrawlPlan:
    target_file: Any
    chunk: Any
    chunk_length: Any
    data_offset: Any
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


def current_wrong_crc_routes(
    pandora_box: Mapping[Any, Mapping[str, Any]],
    cornucopia: Mapping[Any, Any],
    known_chunks: list[bytes] | tuple[bytes, ...],
) -> list[WrongCrcRoute]:
    routes = []
    for key in pandora_box:
        if "Wrong Crc" not in str(key):
            continue
        if str(key) in cornucopia:
            continue

        chunk_name = chunk_name_from_text(key, known_chunks)
        if not chunk_name:
            continue
        routes.append(
            WrongCrcRoute(
                source=None,
                error=key,
                chunk_name=chunk_name,
                tool_prefix=chunk_name + "_Tool_",
            )
        )
    return routes


def remembered_wrong_crc_routes(
    pandemonium: Mapping[Any, Mapping[Any, Mapping[str, Any]]],
    known_chunks: list[bytes] | tuple[bytes, ...],
) -> list[WrongCrcRoute]:
    routes = []
    for sample, sample_errors in pandemonium.items():
        for error, tools in sample_errors.items():
            if "Wrong Crc" not in str(error):
                continue

            chunk_name = chunk_name_from_tool_keys(tools, known_chunks)
            if not chunk_name:
                continue
            routes.append(
                WrongCrcRoute(
                    source=sample,
                    error=error,
                    chunk_name=chunk_name,
                    tool_prefix=chunk_name + "_Tool_",
                )
            )
    return routes


def remembered_dummy_chunk_routes(
    pandemonium: Mapping[Any, Mapping[Any, Mapping[str, Any]]],
    known_chunks: list[bytes] | tuple[bytes, ...],
    critical_chunks: list[bytes] | tuple[bytes, ...],
) -> list[DummyChunkRoute]:
    routes = []
    for sample, sample_errors in pandemonium.items():
        for error, tools in sample_errors.items():
            if "Filling with a dummy chunk" not in str(error):
                continue

            chunk_name = chunk_name_from_tool_keys(tools, known_chunks)
            if not chunk_name:
                continue
            routes.append(
                DummyChunkRoute(
                    source=sample,
                    error=error,
                    chunk_name=chunk_name,
                    tool_prefix=chunk_name + "_Tool_",
                    is_critical=chunk_name.encode() in critical_chunks,
                )
            )
    return routes


def idat_wrong_crc_routes(routes: list[WrongCrcRoute] | tuple[WrongCrcRoute, ...]) -> tuple[WrongCrcRoute, ...]:
    return tuple(route for route in routes if route.chunk_name == "IDAT")


def pandemonium_summary(
    pandemonium: Mapping[Any, Mapping[Any, Mapping[str, Any]]],
) -> tuple[RelicSampleSummary, ...]:
    return tuple(
        RelicSampleSummary(
            sample=sample,
            errors=tuple(
                RelicErrorSummary(error=error, tools=tuple(tools.items()))
                for error, tools in sample_errors.items()
            ),
        )
        for sample, sample_errors in pandemonium.items()
    )


def plte_repair_choices(has_bad_crc: bool) -> tuple[str, ...]:
    if has_bad_crc:
        return ("manually", "bruteforce", "remove", "quit")
    return ("manually", "remove", "quit")


def remembered_sample_target(
    sample_index: int,
    remembered_sample: Any,
    *,
    file_origin: Any,
    current_sample: Any,
) -> Any:
    if sample_index == 0:
        return file_origin
    return os.path.dirname(current_sample) + "/" + str(remembered_sample)


def wrong_crc_brawl_plan(
    route: WrongCrcRoute,
    tools: WrongCrcTools,
    *,
    target_file: Any,
    from_error: Any,
) -> WrongCrcBrawlPlan:
    if route.chunk_name == "IDAT":
        return WrongCrcBrawlPlan(
            target_file=target_file,
            chunk=tools.chunk,
            chunk_length=tools.chunk_length,
            data_offset=tools.data_offset,
            from_error=from_error,
            old_crc=tools.old_crc,
            bf_mode="TwoBytes",
        )

    return WrongCrcBrawlPlan(
        target_file=target_file,
        chunk=tools.chunk,
        chunk_length=tools.chunk_length,
        data_offset=tools.data_offset,
        from_error=from_error,
        old_crc=tools.old_crc,
        brute_length=False,
    )


def dummy_chunk_brawl_plan(
    route: DummyChunkRoute,
    tools: DummyChunkTools,
    *,
    from_error: Any,
) -> DummyChunkBrawlPlan:
    return DummyChunkBrawlPlan(
        target_file=route.source,
        chunk=route.chunk_name,
        chunk_length=tools.dummy_data_length,
        data_offset=tools.bad_start,
        from_error=from_error,
    )


def dummy_chunk_decline_action(route: DummyChunkRoute) -> str:
    if route.is_critical:
        return "end"
    return "todo_end"


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


def record_checkpoint_registration(
    pandora_box: MutableMapping[str, Any],
    cornucopia: MutableMapping[Any, Any],
    registration: Any,
) -> Any:
    if not registration.should_record:
        return None
    if registration.store == "pandora_box":
        return add_pandora_error(
            pandora_box,
            registration.function,
            registration.info,
            registration.tools,
        )
    if registration.store == "cornucopia":
        return add_cornucopia_fix(cornucopia, registration.store_key, registration.tools)
    raise ValueError("Unknown CheckPoint registration store: %s" % registration.store)


def discard_pandora_error(
    pandora_box: MutableMapping[str, Any],
    key: Any,
    default: Any = "key_not_found",
) -> Any:
    return pandora_box.pop(key, default)


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
