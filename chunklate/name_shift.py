from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class NameShiftCandidate:
    search_index: int
    type_offset: int
    chunk_name: bytes
    good_offset: int

    @property
    def is_before(self) -> bool:
        return self.type_offset < self.expected_type_offset

    @property
    def is_after(self) -> bool:
        return self.type_offset > self.expected_type_offset

    @property
    def expected_type_offset(self) -> int:
        return self.type_offset - self.search_index + 8


@dataclass(frozen=True)
class HistoryChunkIndex:
    number: str
    start: int
    end: int
    length: int


def current_chunk_value(data_hex: str, type_offset: int) -> bytes:
    return bytes.fromhex(data_hex[type_offset:type_offset + 8])


def find_shifted_chunk_name(
    data_hex: str,
    type_offset: int,
    known_chunks: Iterable[bytes],
    search_width: int = 32,
) -> NameShiftCandidate | None:
    known_chunk_set = set(known_chunks)
    for search_index in range(0, search_width):
        candidate_offset = type_offset - 8 + search_index
        candidate = bytes.fromhex(data_hex[candidate_offset:type_offset + search_index])
        if candidate in known_chunk_set:
            return NameShiftCandidate(
                search_index=search_index,
                type_offset=candidate_offset,
                chunk_name=candidate,
                good_offset=abs(type_offset - candidate_offset),
            )
    return None


def parse_history_chunk_index(history_index: str) -> HistoryChunkIndex:
    number, start, end, length = history_index.split(":")[:4]
    return HistoryChunkIndex(
        number=number,
        start=int(start),
        end=int(end),
        length=int(length),
    )


def last_history_chunk_before_offset(
    chunks_history_index: Iterable[str],
    type_offset: int,
) -> HistoryChunkIndex | None:
    last_chunk = None
    for history_index in chunks_history_index:
        current = parse_history_chunk_index(history_index)
        if current.end < type_offset:
            last_chunk = current
        else:
            break
    return last_chunk
