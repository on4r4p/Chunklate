from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from . import ancillary


LegacyCall = Callable[..., Any]


@dataclass(frozen=True)
class AncillaryRuntime:
    candy: LegacyCall
    emit: LegacyCall
    betterror: LegacyCall


def run_ancillary_check(runtime: AncillaryRuntime, chunk: Any) -> bool:
    runtime.candy("Title", "Ancillary Check:", runtime.candy("Color", "white", chunk))
    try:
        chunk = chunk.decode(errors="ignore")
    except Exception as exc:
        runtime.betterror(exc, "Ancillary")

    semantics_result = ancillary.chunk_name_semantics(chunk)
    chunk = semantics_result.name

    if not semantics_result.follows_naming:
        runtime.emit(
            "-[%s] is %s Chunks's naming conventions"
            % (chunk, runtime.candy("Color", "red", "Not Following"))
        )
        runtime.candy(
            "Cowsay",
            "Meaning that could be an unknown private chunk that got corrupt .....Or a Known chunk that got corrupt ...",
            "com",
        )
        runtime.candy("Cowsay", "..Or Not even a chunk's name at all ...", "bad")
        return False

    runtime.emit(
        "-[%s] %s Chunks's naming conventions"
        % (chunk, runtime.candy("Color", "green", "Seems to be Following"))
    )
    runtime.candy(
        "Cowsay", "If this is a real Chunk this means that %s is :" % chunk, "good"
    )
    for letter, label in ancillary.semantic_labels(semantics_result):
        runtime.emit(
            "-"
            + runtime.candy("Color", "green", letter)
            + ":"
            + runtime.candy("Color", "yellow", label)
        )
    return True
