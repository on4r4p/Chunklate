from __future__ import annotations

from typing import Any


def chunk_bytes(chunk: Any) -> bytes:
    if type(chunk) is not bytes:
        return str(chunk).encode(errors="ignore")
    return chunk


def index_record(history_length: int, start: Any, end: Any, chunk_length: Any) -> str:
    return (
        str(history_length - 1)
        + ":"
        + str(start)
        + ":"
        + str(end)
        + ":"
        + str(chunk_length)
    )


def duplicate_marker(start: Any, end: Any, chunk_length: Any) -> str:
    return str(start) + ":" + str(end) + ":" + str(chunk_length)


def add(history: list[bytes], indexes: list[str], chunk: Any, start: Any, end: Any, chunk_length: Any) -> bool:
    chunk = chunk_bytes(chunk)
    marker = duplicate_marker(start, end, chunk_length)
    if any(marker in item for item in indexes):
        return False
    history.append(chunk)
    indexes.append(index_record(len(history) - 1, start, end, chunk_length))
    return True


def add_if_no_next(
    history: list[bytes],
    indexes: list[str],
    next_marker: Any,
    chunk: Any,
    start: Any,
    end: Any,
    chunk_length: Any,
) -> bool:
    if next_marker == None:
        return add(history, indexes, chunk, start, end, chunk_length)
    return False


def delete_legacy(history: list[bytes], indexes: list[str], chunk: Any) -> None:
    chunk = chunk_bytes(chunk)
    del history[history.index(chunk)]
    del indexes[history.index(chunk)]
