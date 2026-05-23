from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .png import chunk_at


@dataclass(frozen=True)
class ExtraBytesCandidate:
    extra_bytes: int
    chunk_type: bytes
    current_offset: int


@dataclass(frozen=True)
class HistoryChunkPosition:
    position: int
    start: int
    end: int


def parse_history_index(index: str) -> HistoryChunkPosition:
    position, start, end = (
        int(part.replace(" ", ""))
        for part in index.split(":")[:3]
    )
    return HistoryChunkPosition(position, start, end)


def find_history_chunk_position(
    chunks_history: Iterable[bytes],
    chunks_history_index: Iterable[str],
    chunk_name: bytes,
) -> HistoryChunkPosition | None:
    for chunk, index in zip(chunks_history, chunks_history_index):
        if chunk == chunk_name:
            return parse_history_index(index)
    return None


def initial_search_needle(
    *,
    chunk_type: bytes,
    known_chunks: Iterable[bytes],
    current_length_offset: int,
    chunks_history: Iterable[bytes],
    chunks_history_index: Iterable[str],
    last_chunk_type: bytes,
) -> int:
    if any(chunk == chunk_type for chunk in known_chunks):
        return current_length_offset + 16

    previous = find_history_chunk_position(
        chunks_history,
        chunks_history_index,
        last_chunk_type,
    )
    if previous is None:
        return current_length_offset + 16
    return previous.start + 16


def find_extra_bytes_before_chunk(
    data: bytes,
    *,
    current_offset: int,
    candidates: Iterable[bytes],
    max_extra_bytes: int = 8,
) -> ExtraBytesCandidate | None:
    candidate_set = set(candidates)
    for extra_bytes in range(1, max_extra_bytes + 1):
        candidate_offset = current_offset + extra_bytes
        candidate = chunk_at(data, candidate_offset)
        if candidate is None:
            continue
        if candidate.chunk_type not in candidate_set:
            continue
        if not candidate.crc_ok:
            continue
        return ExtraBytesCandidate(
            extra_bytes=extra_bytes,
            chunk_type=candidate.chunk_type,
            current_offset=current_offset,
        )
    return None


def extra_bytes_solved_message(candidate: ExtraBytesCandidate, last_chunk_type: bytes) -> str:
    return "-Found %s extra byte(s) before Chunk[%s] after Chunk[%s] at offset: %s" % (
        candidate.extra_bytes,
        candidate.chunk_type.decode(errors="ignore"),
        last_chunk_type.decode(errors="ignore"),
        hex(candidate.current_offset),
    )


def relocate_missing_chunk(data_hex: str, *, source_start: int, source_end: int, target_start: int) -> str:
    source = data_hex[source_start:source_end]
    without_source = data_hex[:source_start] + data_hex[source_end:]
    return without_source[:target_start] + source + without_source[target_start:]
