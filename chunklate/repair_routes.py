from __future__ import annotations

from typing import Any, Literal


RepairRouteState = Literal["tried", "deferred", "blocked_no_progress", "skipped_duplicate"]
RepairRouteKey = tuple[str, str, str, str, str, str, str, str]


def _route_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("latin1", errors="replace")
    return str(value)


def _route_offset(value: Any) -> str:
    if value is None:
        return ""
    try:
        return "0x%x" % int(value)
    except (TypeError, ValueError):
        return str(value)


def route_key(
    family: str,
    *,
    chunk: Any = None,
    file_offset: Any = None,
    stream_offset: Any = None,
    source: Any = None,
    target: Any = None,
    start: Any = None,
    end: Any = None,
) -> RepairRouteKey:
    return (
        str(family),
        _route_value(chunk),
        _route_offset(file_offset),
        _route_offset(stream_offset),
        _route_value(source),
        _route_value(target),
        _route_offset(start),
        _route_offset(end),
    )


def remember_route(
    namespace: dict[str, Any],
    key: RepairRouteKey,
    state: RepairRouteState,
) -> RepairRouteState | None:
    states = namespace.setdefault("REPAIR_ROUTE_STATES", {})
    previous = states.get(key)
    states[key] = state
    return previous


def route_state(namespace: dict[str, Any], key: RepairRouteKey) -> RepairRouteState | None:
    states = namespace.setdefault("REPAIR_ROUTE_STATES", {})
    return states.get(key)


def is_exhausted(namespace: dict[str, Any], key: RepairRouteKey) -> bool:
    return route_state(namespace, key) in {
        "tried",
        "deferred",
        "blocked_no_progress",
        "skipped_duplicate",
    }
