from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator
import struct
import zlib


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
IEND_CHUNK = b"\x00\x00\x00\x00IEND\xaeB`\x82"
PNG_COLOR_SAMPLES = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
PNG_COLOR_BIT_DEPTHS = {
    0: (1, 2, 4, 8, 16),
    2: (8, 16),
    3: (1, 2, 4, 8),
    4: (8, 16),
    6: (8, 16),
}


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


@dataclass(frozen=True)
class IhdrRepair:
    data: bytes
    strategy: str
    preserved_crc: bool


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


def png_scanline_size(width: int, bit_depth: int, color_type: int) -> int | None:
    samples = PNG_COLOR_SAMPLES.get(color_type)
    if samples is None or width < 1:
        return None

    return ((width * samples * bit_depth + 7) // 8) + 1


def signed_32bit_abs(value: int) -> int | None:
    if value <= 0x7FFFFFFF:
        return None

    signed = value - 0x100000000
    if signed >= 0:
        return None
    return abs(signed)


def valid_png_color_depth(bit_depth: int, color_type: int) -> bool:
    return bit_depth in PNG_COLOR_BIT_DEPTHS.get(color_type, ())


def _unique_dimensions(dimensions: Iterable[tuple[int, int]]) -> list[tuple[int, int]]:
    seen = set()
    unique = []
    for width, height in dimensions:
        key = (width, height)
        if key not in seen:
            seen.add(key)
            unique.append(key)
    return unique


def infer_png_dimension_candidates(
    decompressed_size: int,
    bit_depth: int,
    color_type: int,
    current_width: int,
    current_height: int,
) -> list[tuple[int, int]]:
    def valid(width: int, height: int) -> bool:
        row_size = png_scanline_size(width, bit_depth, color_type)
        return row_size is not None and height > 0 and row_size * height == decompressed_size

    candidates = []
    signed_width = signed_32bit_abs(current_width)
    signed_height = signed_32bit_abs(current_height)
    if signed_width and signed_height and valid(signed_width, signed_height):
        candidates.append((signed_width, signed_height))

    if current_width > 0:
        row_size = png_scanline_size(current_width, bit_depth, color_type)
        if row_size and decompressed_size % row_size == 0:
            inferred_height = decompressed_size // row_size
            if valid(current_width, inferred_height):
                candidates.append((current_width, inferred_height))

    if 0 < current_height <= decompressed_size:
        row_data_size = decompressed_size // current_height
        if decompressed_size % current_height == 0 and row_data_size > 1:
            samples = PNG_COLOR_SAMPLES.get(color_type)
            if samples:
                bits = (row_data_size - 1) * 8
                denominator = samples * bit_depth
                if denominator and bits % denominator == 0:
                    inferred_width = bits // denominator
                    if valid(inferred_width, current_height):
                        candidates.append((inferred_width, current_height))

    samples = PNG_COLOR_SAMPLES.get(color_type)
    if not samples:
        return _unique_dimensions(candidates)

    for height in range(1, min(decompressed_size, 10000) + 1):
        if decompressed_size % height:
            continue
        row_data_size = decompressed_size // height
        if row_data_size <= 1:
            continue
        bits = (row_data_size - 1) * 8
        denominator = samples * bit_depth
        if denominator and bits % denominator == 0:
            width = bits // denominator
            if valid(width, height):
                candidates.append((width, height))

    return _unique_dimensions(candidates)


def infer_png_dimensions(
    decompressed_size: int,
    bit_depth: int,
    color_type: int,
    current_width: int,
    current_height: int,
) -> tuple[int, int] | None:
    def valid(width: int, height: int) -> bool:
        row_size = png_scanline_size(width, bit_depth, color_type)
        return row_size is not None and height > 0 and row_size * height == decompressed_size

    candidates = infer_png_dimension_candidates(
        decompressed_size,
        bit_depth,
        color_type,
        current_width,
        current_height,
    )

    signed_width = signed_32bit_abs(current_width)
    signed_height = signed_32bit_abs(current_height)
    if signed_width and signed_height and valid(signed_width, signed_height):
        return signed_width, signed_height

    if current_width > 0:
        row_size = png_scanline_size(current_width, bit_depth, color_type)
        if row_size and decompressed_size % row_size == 0:
            inferred_height = decompressed_size // row_size
            if valid(current_width, inferred_height):
                return current_width, inferred_height

    if 0 < current_height <= decompressed_size and decompressed_size % current_height == 0:
        row_data_size = decompressed_size // current_height
        samples = PNG_COLOR_SAMPLES.get(color_type)
        if samples and row_data_size > 1:
            bits = (row_data_size - 1) * 8
            denominator = samples * bit_depth
            if denominator and bits % denominator == 0:
                inferred_width = bits // denominator
                if valid(inferred_width, current_height):
                    return inferred_width, current_height

    if len(candidates) == 1:
        return candidates[0]
    if candidates and 0 < current_width <= 0x7FFFFFFF:
        candidates.sort(key=lambda dimensions: abs(dimensions[0] - current_width))
        if len(candidates) == 1 or abs(candidates[0][0] - current_width) < abs(candidates[1][0] - current_width):
            return candidates[0]

    return None


def _ordered_values(preferred: int, allowed: Iterable[int]) -> list[int]:
    values = list(allowed)
    if preferred in values:
        values.remove(preferred)
        return [preferred] + values
    return values


def _ihdr_and_idat_data(data: bytes) -> tuple[PngChunk, bytes] | None:
    signature_offset = find_signature_offset(data)
    if signature_offset < 0:
        return None

    ihdr_offset = signature_offset + len(PNG_SIGNATURE)
    ihdr = chunk_at(data, ihdr_offset)
    if ihdr is None or ihdr.chunk_type != b"IHDR" or ihdr.length != 13:
        return None

    idat_data = b""
    offset = ihdr_offset
    while True:
        chunk = chunk_at(data, offset)
        if chunk is None:
            return None
        if chunk.chunk_type == b"IDAT":
            idat_data += chunk.data
        offset += 12 + chunk.length
        if chunk.chunk_type == b"IEND":
            break

    if not idat_data:
        return None

    return ihdr, idat_data


def _replace_ihdr_chunk(data: bytes, ihdr: PngChunk, ihdr_data: bytes, crc: int) -> bytes | None:
    fixed_chunk = (
        len(ihdr_data).to_bytes(4, "big")
        + b"IHDR"
        + ihdr_data
        + crc.to_bytes(4, "big")
    )

    original_chunk = data[ihdr.offset : ihdr.offset + 12 + ihdr.length]
    if fixed_chunk == original_chunk:
        return None

    return data[: ihdr.offset] + fixed_chunk + data[ihdr.offset + 12 + ihdr.length :]


def _ihdr_candidate_data_from_idat(
    decompressed_size: int,
    current_width: int,
    current_height: int,
    current_bit_depth: int,
    current_color_type: int,
) -> Iterator[bytes]:
    color_types = _ordered_values(current_color_type, PNG_COLOR_BIT_DEPTHS.keys())
    for color_type in color_types:
        bit_depths = _ordered_values(current_bit_depth, PNG_COLOR_BIT_DEPTHS[color_type])
        for bit_depth in bit_depths:
            dimensions = infer_png_dimension_candidates(
                decompressed_size,
                bit_depth,
                color_type,
                current_width,
                current_height,
            )
            for width, height in dimensions:
                yield struct.pack("!IIBBBBB", width, height, bit_depth, color_type, 0, 0, 0)


def repair_ihdr_preserving_crc(data: bytes) -> bytes | None:
    context = _ihdr_and_idat_data(data)
    if context is None:
        return None

    ihdr, idat_data = context
    width, height, bit_depth, color_type, method, filter_method, interlace = struct.unpack(
        "!IIBBBBB", ihdr.data
    )

    try:
        decompressed = zlib.decompress(idat_data)
    except zlib.error:
        return None

    for ihdr_data in _ihdr_candidate_data_from_idat(
        len(decompressed),
        width,
        height,
        bit_depth,
        color_type,
    ):
        if zlib.crc32(b"IHDR" + ihdr_data) & 0xFFFFFFFF != ihdr.crc:
            continue
        return _replace_ihdr_chunk(data, ihdr, ihdr_data, ihdr.crc)

    return None


def rebuild_ihdr_from_idat(data: bytes) -> bytes | None:
    context = _ihdr_and_idat_data(data)
    if context is None:
        return None

    ihdr, idat_data = context
    width, height, bit_depth, color_type, method, filter_method, interlace = struct.unpack(
        "!IIBBBBB", ihdr.data
    )
    if not valid_png_color_depth(bit_depth, color_type):
        return None
    if interlace not in (0, 1):
        interlace = 0
    if interlace != 0:
        return None

    try:
        decompressed = zlib.decompress(idat_data)
    except zlib.error:
        return None

    dimensions = infer_png_dimensions(len(decompressed), bit_depth, color_type, width, height)
    if dimensions is None:
        return None

    fixed_width, fixed_height = dimensions
    fixed_ihdr_data = struct.pack(
        "!IIBBBBB",
        fixed_width,
        fixed_height,
        bit_depth,
        color_type,
        0,
        0,
        interlace,
    )
    fixed_crc = zlib.crc32(b"IHDR" + fixed_ihdr_data) & 0xFFFFFFFF
    return _replace_ihdr_chunk(data, ihdr, fixed_ihdr_data, fixed_crc)


def repair_ihdr(data: bytes) -> IhdrRepair | None:
    fixed = repair_ihdr_preserving_crc(data)
    if fixed is not None:
        return IhdrRepair(
            data=fixed,
            strategy="restored IHDR values matching stored CRC",
            preserved_crc=True,
        )

    fixed = rebuild_ihdr_from_idat(data)
    if fixed is not None:
        return IhdrRepair(
            data=fixed,
            strategy="rebuilt IHDR from IDAT scanline size",
            preserved_crc=False,
        )

    return None


def repair_ihdr_from_idat(data: bytes) -> bytes | None:
    result = repair_ihdr(data)
    if result is None:
        return None
    return result.data
