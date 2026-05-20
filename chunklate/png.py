from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator
import zlib


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
IEND_CHUNK = b"\x00\x00\x00\x00IEND\xaeB`\x82"


class PngFormatError(ValueError):
    """Raised when bytes cannot be parsed as a complete PNG chunk stream."""


@dataclass(frozen=True)
class PngChunk:
    offset: int
    length: int
    chunk_type: bytes
    data: bytes
    crc: int

    @property
    def name(self) -> str:
        return self.chunk_type.decode("ascii", errors="replace")

    @property
    def computed_crc(self) -> int:
        return zlib.crc32(self.chunk_type + self.data) & 0xFFFFFFFF

    @property
    def crc_ok(self) -> bool:
        return self.crc == self.computed_crc


def find_signature_offset(data: bytes) -> int:
    return data.find(PNG_SIGNATURE)


def iter_chunks(data: bytes, *, signature_offset: int | None = None) -> Iterator[PngChunk]:
    if signature_offset is None:
        signature_offset = find_signature_offset(data)

    if signature_offset < 0:
        raise PngFormatError("PNG signature not found")

    stream_start = signature_offset + len(PNG_SIGNATURE)
    if len(data) < stream_start:
        raise PngFormatError("Incomplete PNG signature")

    offset = stream_start
    while offset < len(data):
        if len(data) - offset < 12:
            raise PngFormatError(f"Incomplete chunk header at offset {offset}")

        length = int.from_bytes(data[offset : offset + 4], "big")
        chunk_type = data[offset + 4 : offset + 8]
        data_start = offset + 8
        data_end = data_start + length
        crc_end = data_end + 4

        if crc_end > len(data):
            raise PngFormatError(
                f"Incomplete {chunk_type.decode('ascii', errors='replace')} chunk at offset {offset}"
            )

        yield PngChunk(
            offset=offset,
            length=length,
            chunk_type=chunk_type,
            data=data[data_start:data_end],
            crc=int.from_bytes(data[data_end:crc_end], "big"),
        )

        offset = crc_end
        if chunk_type == b"IEND":
            return


def read_chunks(path: str | Path) -> list[PngChunk]:
    return list(iter_chunks(Path(path).read_bytes()))


def chunk_at(data: bytes, offset: int) -> PngChunk | None:
    if offset < 0 or len(data) - offset < 12:
        return None

    length = int.from_bytes(data[offset : offset + 4], "big")
    data_start = offset + 8
    data_end = data_start + length
    crc_end = data_end + 4

    if crc_end > len(data):
        return None

    return PngChunk(
        offset=offset,
        length=length,
        chunk_type=data[offset + 4 : offset + 8],
        data=data[data_start:data_end],
        crc=int.from_bytes(data[data_end:crc_end], "big"),
    )


def chunk_type_crc_matches(chunk_data: bytes, stored_crc: int, candidates: Iterable[bytes]) -> list[bytes]:
    return [
        chunk_type
        for chunk_type in candidates
        if zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF == stored_crc
    ]


def complete_iend_tail(data: bytes, insert_offset: int) -> bytes:
    tail = data[insert_offset:]

    if not tail:
        return data + IEND_CHUNK

    if tail.startswith(IEND_CHUNK):
        return data[: insert_offset + len(IEND_CHUNK)]

    if IEND_CHUNK in tail:
        return data[:insert_offset] + IEND_CHUNK

    if len(tail) < len(IEND_CHUNK) and IEND_CHUNK.endswith(tail):
        return data[:insert_offset] + IEND_CHUNK[: -len(tail)] + tail

    return data[:insert_offset] + IEND_CHUNK
