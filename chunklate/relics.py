from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from typing import Any


LEGACY_BAD_CHUNK_LABEL = "johnnybytesme"


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
