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


@dataclass(frozen=True)
class NearbyLengthRepair:
    display_chunk: bytes
    found_chunk: bytes
    print_offset: int | str
    length_offset: int | str
    found_chunk_offset: str
    fixed_length: str
    old_length: str
    replace_start: int
    replace_end: int

    @property
    def print_message(self) -> str:
        return "-Found Chunk[%s] has Wrong length at offset: %s\n-Replaced with: %s old value was: %s" % (
            self.display_chunk,
            self.print_offset,
            self.fixed_length,
            self.old_length,
        )

    @property
    def solved_message(self) -> str:
        return "-Found Chunk[%s] has Wrong length at offset: %s\n-Found next chunk: %s at: %s\n-Replaced with: %s old value was: %s" % (
            self.display_chunk,
            self.length_offset,
            self.found_chunk,
            self.found_chunk_offset,
            self.fixed_length,
            self.old_length,
        )


@dataclass(frozen=True)
class DoubleCheckFileLength:
    byte_length: int
    is_too_short: bool


def double_check_file_length(data_hex: str, minimum_png_size: int = 67) -> DoubleCheckFileLength:
    raw_byte_length = len(data_hex) / 2
    return DoubleCheckFileLength(
        byte_length=int(raw_byte_length),
        is_too_short=raw_byte_length < minimum_png_size,
    )


def clamp_length(length: int) -> int:
    if length < 0:
        return 0
    return length


def format_png_length(length: int) -> str:
    return str("0x%08X" % clamp_length(length))[2::]


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


def known_chunk_length_repair(
    *,
    display_chunk: bytes,
    old_length: str,
    current_length_offset: int,
    current_length_offset_hex: str,
    current_data_offset_byte: int,
    found_chunk: bytes,
    found_chunk_type_offset: int,
) -> NearbyLengthRepair:
    found_chunk_type_byte_offset = int(found_chunk_type_offset / 2)
    data_end_offset = found_chunk_type_byte_offset - 8
    fixed_length = format_png_length(data_end_offset - current_data_offset_byte)
    return NearbyLengthRepair(
        display_chunk=display_chunk,
        found_chunk=found_chunk,
        print_offset=current_length_offset_hex,
        length_offset=current_length_offset_hex,
        found_chunk_offset=hex(found_chunk_type_byte_offset),
        fixed_length=fixed_length,
        old_length=old_length,
        replace_start=current_length_offset,
        replace_end=current_length_offset + 8,
    )


def unknown_chunk_length_repair(
    *,
    data_hex: str,
    display_chunk: bytes,
    checkpoint_length_offset: int,
    chunks_history: Iterable[bytes],
    chunks_history_index: Iterable[str],
    last_chunk_type: bytes,
    found_chunk: bytes,
    found_chunk_type_offset: int,
) -> NearbyLengthRepair | None:
    previous = find_history_chunk_position(
        chunks_history,
        chunks_history_index,
        last_chunk_type,
    )
    if previous is None:
        return None

    found_chunk_type_byte_offset = int(found_chunk_type_offset / 2)
    data_end_offset = found_chunk_type_byte_offset - 8
    previous_data_offset = int(previous.start / 2) + 8
    fixed_length = format_png_length(data_end_offset - previous_data_offset)
    old_length = data_hex[previous.start:previous.start + 8]
    return NearbyLengthRepair(
        display_chunk=last_chunk_type,
        found_chunk=found_chunk,
        print_offset=found_chunk_type_offset - 8,
        length_offset=previous.start,
        found_chunk_offset=hex(found_chunk_type_byte_offset),
        fixed_length=fixed_length,
        old_length=old_length,
        replace_start=previous.start,
        replace_end=previous.start + 8,
    )


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


def extra_bytes_before_chunk_candidate(
    data_hex: str,
    *,
    current_length_offset: int,
    chunk_type: bytes,
    known_chunks: Iterable[bytes],
    all_chunks: Iterable[bytes],
    excluded_chunks: Iterable[bytes],
) -> ExtraBytesCandidate | None:
    if any(candidate == chunk_type for candidate in known_chunks):
        return None

    return find_extra_bytes_before_chunk(
        bytes.fromhex(data_hex),
        current_offset=int(current_length_offset / 2),
        candidates=set(all_chunks) - set(excluded_chunks),
    )


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


def null_find(data: str, search4: str | None = None) -> int | bool:
    null_pos = ""
    if search4 is None:
        search4 = "00"
    for index in range(0, len(data), len(search4)):
        if data[index : index + len(search4)] == search4:
            null_pos = index
            break
    if len(str(null_pos)) > 0:
        return null_pos
    return False
