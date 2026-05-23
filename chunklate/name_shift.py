from __future__ import annotations

import binascii
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


@dataclass(frozen=True)
class ShiftedChunkCrcView:
    real_length: str
    data_hex_length: int
    chunk_type: bytes
    chunk_data: bytes
    file_crc: str
    checksum: str

    @property
    def crc_matches(self) -> bool:
        return self.checksum == self.file_crc

    @property
    def fixed_hex(self) -> str:
        return (
            self.real_length
            + self.chunk_type.hex()
            + self.chunk_data.hex()
            + self.file_crc.replace("0x", "")
        )


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


def shifted_chunk_crc_view(
    data_hex: str,
    chunk_type_offset: int,
    chunk_type: bytes,
    real_length: str,
) -> ShiftedChunkCrcView:
    data_hex_length = int.from_bytes(bytes.fromhex(real_length), byteorder="big") * 2
    data_start = chunk_type_offset + 8
    data_end = data_start + data_hex_length
    crc_start = data_end
    crc_end = crc_start + 8
    chunk_data = bytes.fromhex(data_hex[data_start:data_end])
    file_crc = hex(int.from_bytes(bytes.fromhex(data_hex[crc_start:crc_end]), byteorder="big"))
    checksum = hex(binascii.crc32(chunk_type + chunk_data))
    return ShiftedChunkCrcView(
        real_length=real_length,
        data_hex_length=data_hex_length,
        chunk_type=chunk_type,
        chunk_data=chunk_data,
        file_crc=file_crc,
        checksum=checksum,
    )
