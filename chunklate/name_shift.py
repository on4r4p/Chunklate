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


def current_chunk_value_line(type_offset: int, current_value: bytes) -> str:
    return "\n-Current value of chunkname at offset %s : %s" % (
        str(type_offset),
        current_value,
    )


def found_chunk_note(search_index: int, type_offset: int, chunk_name: bytes) -> str:
    return "-NameShift: Found correct chunkname i:%s Offset:%s data: %s" % (
        str(search_index),
        str(type_offset),
        chunk_name,
    )


def valid_chunk_before_line(chunk_name: bytes, good_offset: int) -> str:
    return "-Found valid chunkname %s at exactly %s bytes before." % (
        chunk_name,
        str(int(good_offset / 2)),
    )


def valid_chunk_after_line(chunk_name: bytes, good_offset: int) -> str:
    return "-Found valid chunkname %s at exactly %s bytes after." % (
        chunk_name,
        str(int(good_offset / 2)),
    )


def crc_ok_line(ok_label: str, good_emoj: str) -> str:
    return "-Crc Check :" + ok_label + good_emoj + "\n"


def crc_failed_line(failed_label: str, bad_emoj: str) -> str:
    return "-Crc Check :" + failed_label + bad_emoj


def monkey_wanted_line(green_checksum: str) -> str:
    return "\nMonkey wanted Banana :%s" % green_checksum


def monkey_got_line(red_crc: str) -> str:
    return "Monkey got Pullover :%s" % red_crc


def missed_something_message() -> str:
    return " Hold on a sec ... Must have missed something..."


def length_part_is_corrupted(file_length: str, spec_length: str) -> bool:
    return file_length != spec_length


def crc_value_is_empty(file_crc: str, checksum: str) -> bool:
    return len(file_crc) == 0 or len(checksum) == 0


def checksum_needs_legacy_padding(checksum: str) -> bool:
    return len(checksum) < 10


def legacy_pad_checksum(checksum: str) -> str:
    return "0x" + checksum[2::].zfill(8)


def crc_valid_note() -> str:
    return "-NameShift:Crc check is valid."


def extra_bytes_found_note() -> str:
    return "-NameShift: Extra bytes has been found."


def missing_bytes_found_note() -> str:
    return "-NameShift: Missing bytes found."


def corrupted_length_note(chunk_name: bytes) -> str:
    return "-NameShift: Length part of %s was corrupted" % chunk_name


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


def extra_bytes_align_with_previous_chunk(
    shifted_type_offset: int,
    previous_chunk_end: int,
    good_offset: int,
) -> bool:
    return shifted_type_offset == previous_chunk_end + 8 + good_offset


def extra_bytes_expected_offset(previous_chunk_end: int, good_offset: int) -> int:
    return previous_chunk_end + 8 + good_offset


def extra_bytes_repair_result(
    fixed_hex: str,
    good_offset: int,
    current_type_offset: int,
) -> list[object]:
    return [fixed_hex, len(fixed_hex) + good_offset, current_type_offset - 8]


def missing_bytes_repair_result(
    fixed_hex: str,
    good_offset: int,
    current_type_offset: int,
) -> list[object]:
    return [fixed_hex, len(fixed_hex) - good_offset, current_type_offset - 8]
