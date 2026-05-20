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


@dataclass(frozen=True)
class ColorProfileRepair:
    data: bytes
    strategy: str
    removed_chunks: tuple[str, ...]


@dataclass(frozen=True)
class PlteRepair:
    data: bytes
    strategy: str


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


def build_png_chunk(chunk_type: bytes, chunk_data: bytes) -> bytes:
    crc = zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF
    return len(chunk_data).to_bytes(4, "big") + chunk_type + chunk_data + crc.to_bytes(4, "big")


def replace_png_chunk(data: bytes, chunk: PngChunk, replacement: bytes) -> bytes:
    chunk_end = chunk.offset + 12 + chunk.length
    return data[: chunk.offset] + replacement + data[chunk_end:]


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


def _paeth_predictor(left: int, up: int, up_left: int) -> int:
    estimate = left + up - up_left
    distance_left = abs(estimate - left)
    distance_up = abs(estimate - up)
    distance_up_left = abs(estimate - up_left)

    if distance_left <= distance_up and distance_left <= distance_up_left:
        return left
    if distance_up <= distance_up_left:
        return up
    return up_left


def unfilter_scanlines(
    filtered: bytes,
    *,
    width: int,
    height: int,
    bit_depth: int,
    color_type: int,
) -> bytes | None:
    row_size = png_scanline_size(width, bit_depth, color_type)
    if row_size is None:
        return None
    if len(filtered) != row_size * height:
        return None

    row_data_size = row_size - 1
    bits_per_pixel = PNG_COLOR_SAMPLES[color_type] * bit_depth
    bytes_per_pixel = max(1, (bits_per_pixel + 7) // 8)
    previous = bytearray(row_data_size)
    raw_rows = bytearray()

    for row_index in range(height):
        row_start = row_index * row_size
        filter_type = filtered[row_start]
        filtered_row = filtered[row_start + 1 : row_start + row_size]
        row = bytearray(row_data_size)

        for index, value in enumerate(filtered_row):
            left = row[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
            up = previous[index]
            up_left = previous[index - bytes_per_pixel] if index >= bytes_per_pixel else 0

            if filter_type == 0:
                repaired = value
            elif filter_type == 1:
                repaired = value + left
            elif filter_type == 2:
                repaired = value + up
            elif filter_type == 3:
                repaired = value + ((left + up) // 2)
            elif filter_type == 4:
                repaired = value + _paeth_predictor(left, up, up_left)
            else:
                return None

            row[index] = repaired & 0xFF

        raw_rows.extend(row)
        previous = row

    return bytes(raw_rows)


def unpack_indexed_scanlines(raw_rows: bytes, *, width: int, height: int, bit_depth: int) -> list[int] | None:
    if bit_depth not in (1, 2, 4, 8):
        return None

    row_data_size = (width * bit_depth + 7) // 8
    if len(raw_rows) != row_data_size * height:
        return None

    indices = []
    mask = (1 << bit_depth) - 1
    for row_index in range(height):
        row = raw_rows[row_index * row_data_size : (row_index + 1) * row_data_size]
        row_indices = []

        if bit_depth == 8:
            row_indices = list(row[:width])
        else:
            for value in row:
                for shift in range(8 - bit_depth, -1, -bit_depth):
                    row_indices.append((value >> shift) & mask)
                    if len(row_indices) == width:
                        break
                if len(row_indices) == width:
                    break

        if len(row_indices) != width:
            return None
        indices.extend(row_indices)

    return indices


def remove_png_chunks(data: bytes, should_remove) -> tuple[bytes, tuple[PngChunk, ...]] | None:
    signature_offset = find_signature_offset(data)
    if signature_offset < 0:
        return None

    output = bytearray(data[: signature_offset + len(PNG_SIGNATURE)])
    removed = []
    offset = signature_offset + len(PNG_SIGNATURE)

    while offset < len(data):
        chunk = chunk_at(data, offset)
        if chunk is None:
            return None

        chunk_end = offset + 12 + chunk.length
        if should_remove(chunk):
            removed.append(chunk)
        else:
            output.extend(data[offset:chunk_end])

        offset = chunk_end
        if chunk.chunk_type == b"IEND":
            break

    if not removed:
        return None

    return bytes(output), tuple(removed)


def iccp_profile_name(chunk: PngChunk) -> bytes | None:
    if chunk.chunk_type != b"iCCP":
        return None

    try:
        return chunk.data[: chunk.data.index(0)]
    except ValueError:
        return None


def iccp_decompressed_profile(chunk: PngChunk) -> bytes | None:
    if chunk.chunk_type != b"iCCP":
        return None

    try:
        null_pos = chunk.data.index(0)
    except ValueError:
        return None

    if null_pos + 2 > len(chunk.data):
        return None
    if chunk.data[null_pos + 1] != 0:
        return None

    try:
        return zlib.decompress(chunk.data[null_pos + 2 :])
    except zlib.error:
        return None


def is_zero_gama_chunk(chunk: PngChunk) -> bool:
    return chunk.chunk_type == b"gAMA" and chunk.length == 4 and chunk.data == b"\x00\x00\x00\x00"


def is_known_bad_srgb_iccp_chunk(chunk: PngChunk) -> bool:
    if iccp_profile_name(chunk) != b"Photoshop ICC profile":
        return False

    profile = iccp_decompressed_profile(chunk)
    if profile is None:
        return False

    return b"IEC sRGB" in profile and b"acsp" in profile[:64]


def repair_color_profile_chunks(
    data: bytes,
    *,
    remove_zero_gama: bool = True,
    remove_known_bad_srgb_iccp: bool = False,
) -> ColorProfileRepair | None:
    def should_remove(chunk: PngChunk) -> bool:
        return (
            remove_zero_gama
            and is_zero_gama_chunk(chunk)
        ) or (
            remove_known_bad_srgb_iccp
            and is_known_bad_srgb_iccp_chunk(chunk)
        )

    if not remove_zero_gama and not remove_known_bad_srgb_iccp:
        return None

    result = remove_png_chunks(data, should_remove)
    if result is None:
        return None

    repaired, removed = result
    removed_names = tuple(chunk.name for chunk in removed)
    reasons = []
    if any(chunk.chunk_type == b"gAMA" for chunk in removed):
        reasons.append("removed zero gAMA chunk")
    if any(chunk.chunk_type == b"iCCP" for chunk in removed):
        reasons.append("removed known bad sRGB iCCP profile")

    return ColorProfileRepair(
        data=repaired,
        strategy=", ".join(reasons),
        removed_chunks=removed_names,
    )


def _parse_ihdr_data(ihdr: PngChunk) -> tuple[int, int, int, int, int, int, int] | None:
    if ihdr.chunk_type != b"IHDR" or ihdr.length != 13:
        return None
    return struct.unpack("!IIBBBBB", ihdr.data)


def indexed_png_indices(data: bytes) -> list[int] | None:
    try:
        chunks = list(iter_chunks(data))
    except PngFormatError:
        return None

    ihdr = next((chunk for chunk in chunks if chunk.chunk_type == b"IHDR"), None)
    if ihdr is None:
        return None

    ihdr_values = _parse_ihdr_data(ihdr)
    if ihdr_values is None:
        return None

    width, height, bit_depth, color_type, _method, _filter_method, interlace = ihdr_values
    if color_type != 3 or bit_depth not in (1, 2, 4, 8) or interlace != 0:
        return None

    idat_data = b"".join(chunk.data for chunk in chunks if chunk.chunk_type == b"IDAT")
    if not idat_data:
        return None

    try:
        filtered = zlib.decompress(idat_data)
    except zlib.error:
        return None

    raw_rows = unfilter_scanlines(
        filtered,
        width=width,
        height=height,
        bit_depth=bit_depth,
        color_type=color_type,
    )
    if raw_rows is None:
        return None

    return unpack_indexed_scanlines(raw_rows, width=width, height=height, bit_depth=bit_depth)


def grayscale_palette(entry_count: int) -> bytes | None:
    if not 1 <= entry_count <= 256:
        return None

    palette = bytearray()
    for index in range(entry_count):
        value = 0 if entry_count == 1 else round(index * 255 / (entry_count - 1))
        palette.extend((value, value, value))
    return bytes(palette)


def repair_empty_plte(data: bytes) -> PlteRepair | None:
    try:
        chunks = list(iter_chunks(data))
    except PngFormatError:
        return None

    ihdr = next((chunk for chunk in chunks if chunk.chunk_type == b"IHDR"), None)
    plte = next((chunk for chunk in chunks if chunk.chunk_type == b"PLTE"), None)
    if ihdr is None or plte is None or plte.length != 0:
        return None

    ihdr_values = _parse_ihdr_data(ihdr)
    if ihdr_values is None:
        return None

    _width, _height, bit_depth, color_type, _method, _filter_method, _interlace = ihdr_values
    if color_type in (0, 2, 4, 6):
        return PlteRepair(
            data=replace_png_chunk(data, plte, b""),
            strategy="removed empty non-indexed PLTE chunk",
        )

    if color_type != 3 or bit_depth not in (1, 2, 4, 8):
        return None

    indices = indexed_png_indices(data)
    if indices is None:
        return None

    max_entries = 2 ** bit_depth
    entry_count = max(indices, default=0) + 1
    if entry_count > max_entries:
        return None

    palette = grayscale_palette(entry_count)
    if palette is None:
        return None

    return PlteRepair(
        data=replace_png_chunk(data, plte, build_png_chunk(b"PLTE", palette)),
        strategy="rebuilt empty indexed PLTE as grayscale palette",
    )


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


def _dimension_area(dimensions: tuple[int, int]) -> int:
    width, height = dimensions
    return width * height


def _dimension_aspect_ratio(dimensions: tuple[int, int]) -> float:
    width, height = dimensions
    return max(width, height) / min(width, height)


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

    preferred = None
    signed_width = signed_32bit_abs(current_width)
    signed_height = signed_32bit_abs(current_height)
    if signed_width and signed_height and valid(signed_width, signed_height):
        preferred = (signed_width, signed_height)

    if preferred is None and current_width > 0:
        row_size = png_scanline_size(current_width, bit_depth, color_type)
        if row_size and decompressed_size % row_size == 0:
            inferred_height = decompressed_size // row_size
            if valid(current_width, inferred_height):
                preferred = (current_width, inferred_height)

    if preferred is None and 0 < current_height <= decompressed_size and decompressed_size % current_height == 0:
        row_data_size = decompressed_size // current_height
        samples = PNG_COLOR_SAMPLES.get(color_type)
        if samples and row_data_size > 1:
            bits = (row_data_size - 1) * 8
            denominator = samples * bit_depth
            if denominator and bits % denominator == 0:
                inferred_width = bits // denominator
                if valid(inferred_width, current_height):
                    preferred = (inferred_width, current_height)

    if len(candidates) == 1:
        return candidates[0]

    balanced_candidates = [
        dimensions
        for dimensions in candidates
        if min(dimensions) > 0 and _dimension_aspect_ratio(dimensions) <= 2
    ]

    if preferred is None and 0 < current_width <= 0x7FFFFFFF:
        candidates.sort(key=lambda dimensions: abs(dimensions[0] - current_width))
        if len(candidates) == 1 or abs(candidates[0][0] - current_width) < abs(candidates[1][0] - current_width):
            preferred = candidates[0]

    if preferred is not None:
        larger_balanced = [
            dimensions
            for dimensions in balanced_candidates
            if dimensions[0] >= preferred[0]
            and dimensions[1] >= preferred[1]
            and _dimension_area(dimensions) > _dimension_area(preferred)
        ]
        if larger_balanced:
            larger_balanced.sort(key=_dimension_area, reverse=True)
            return larger_balanced[0]
        return preferred

    if balanced_candidates:
        balanced_candidates.sort(
            key=lambda dimensions: (
                _dimension_area(dimensions),
                -abs(dimensions[0] - dimensions[1]),
            ),
            reverse=True,
        )
        return balanced_candidates[0]

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
