from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from typing import Literal

from . import relics


CheckpointStore = Literal["pandora_box", "cornucopia"]


@dataclass(frozen=True)
class CheckPointRegistration:
    should_record: bool
    store: CheckpointStore | None
    function: Any
    info: Any
    tools: Mapping[str, Any]
    store_key: Any = None
    side_note: str | None = None


def finding_registration(
    *,
    error: bool,
    fixed: bool,
    function: Any,
    chunk: Any,
    info: Any,
    toolkit: tuple[Any, ...],
) -> CheckPointRegistration:
    if error is not True:
        return CheckPointRegistration(False, None, function, info, {})

    tools = relics.build_tools(relics.chunk_label(chunk), toolkit)
    if fixed is False:
        return CheckPointRegistration(
            should_record=True,
            store="pandora_box",
            function=function,
            info=info,
            tools=tools,
            side_note="Error:" + str(info),
        )

    return CheckPointRegistration(
        should_record=True,
        store="cornucopia",
        function=function,
        info=info,
        tools=tools,
        store_key=toolkit[-1],
        side_note="Error Fixed:" + str(info),
    )
