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
class LegacyChunkWindow:
    raw_length: str
    raw_type: str
    raw_data: str
    raw_crc: str
    raw_next_chunk: str
    chunk_type: bytes
    next_chunk_type: bytes
    length_offset_hex: str
    length_offset_byte: int
    length_offset_index: int
    type_offset_hex: str
    type_offset_byte: int
    type_offset_index: int
    data_offset_hex: str
    data_offset_byte: int
    data_offset_index: int
    crc_offset_hex: str
    crc_offset_byte: int
    crc_offset_index: int
    next_chunk_offset_hex: str
    next_chunk_offset_byte: int
    next_chunk_offset_index: int


@dataclass(frozen=True)
class PngValidationResult:
    errors: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0


@dataclass(frozen=True)
class LegacyLengthStatus:
    declared_length: int
    has_next_chunk: bool
    next_chunk_type: bytes


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


@dataclass(frozen=True)
class MissingChunkByteRepair:
    data: bytes
    strategy: str
    chunk_name: str
    inserted_offset: int
    inserted_value: int


@dataclass(frozen=True)
class ChunkTypeRepair:
    data: bytes
    strategy: str
    original_name: str
    repaired_name: str


@dataclass(frozen=True)
class ChunkRemovalRepair:
    data: bytes
    strategy: str
    removed_chunks: tuple[str, ...]


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


def legacy_chunk_window(data: bytes, hex_offset: int) -> LegacyChunkWindow:
    data_hex = data.hex()
    byte_offset = hex_offset // 2
    chunk = chunk_at(data, byte_offset)

    if chunk is None:
        raw_length = data_hex[hex_offset : hex_offset + 8]
        length = int(raw_length, 16) if raw_length else 0
        raw_type = data_hex[hex_offset + 8 : hex_offset + 16]
        raw_data = data_hex[hex_offset + 16 : hex_offset + 16 + (length * 2)]
        raw_crc = data_hex[hex_offset + 16 + len(raw_data) : hex_offset + 16 + len(raw_data) + 8]
        chunk_type = bytes.fromhex(raw_type) if raw_type else b""
    else:
        length = chunk.length
        raw_length = chunk.length.to_bytes(4, "big").hex()
        raw_type = chunk.chunk_type.hex()
        raw_data = chunk.data.hex()
        raw_crc = chunk.crc.to_bytes(4, "big").hex()
        chunk_type = chunk.chunk_type

    raw_next_chunk = data_hex[hex_offset + 32 + len(raw_data) : hex_offset + 32 + len(raw_data) + 8]
    next_chunk_type = bytes.fromhex(raw_next_chunk) if raw_next_chunk else b""

    crc_byte_offset = byte_offset + length + len(raw_type)
    next_chunk_offset_byte = byte_offset + length + len(raw_type) + 16

    return LegacyChunkWindow(
        raw_length=raw_length,
        raw_type=raw_type,
        raw_data=raw_data,
        raw_crc=raw_crc,
        raw_next_chunk=raw_next_chunk,
        chunk_type=chunk_type,
        next_chunk_type=next_chunk_type,
        length_offset_hex=hex(byte_offset),
        length_offset_byte=byte_offset,
        length_offset_index=hex_offset,
        type_offset_hex=hex(byte_offset + 4),
        type_offset_byte=byte_offset + 4,
        type_offset_index=hex_offset + 8,
        data_offset_hex=hex(byte_offset + 8),
        data_offset_byte=byte_offset + 8,
        data_offset_index=hex_offset + 16,
        crc_offset_hex=hex(crc_byte_offset),
        crc_offset_byte=crc_byte_offset,
        crc_offset_index=crc_byte_offset * 2,
        next_chunk_offset_hex=hex(byte_offset + length + len(raw_type) + len(raw_data)),
        next_chunk_offset_byte=next_chunk_offset_byte,
        next_chunk_offset_index=next_chunk_offset_byte * 2,
    )


def legacy_length_status(data: bytes, hex_offset: int) -> LegacyLengthStatus:
    window = legacy_chunk_window(data, hex_offset)
    return LegacyLengthStatus(
        declared_length=int(window.raw_length, 16) if window.raw_length else 0,
        has_next_chunk=len(window.next_chunk_type) == 4,
        next_chunk_type=window.next_chunk_type,
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


def is_complete_png_with_valid_crc(data: bytes) -> bool:
    try:
        chunks = list(iter_chunks(data))
    except PngFormatError:
        return False

    if not chunks or chunks[-1].chunk_type != b"IEND":
        return False

    iend_end = chunks[-1].offset + 12 + chunks[-1].length
    return iend_end == len(data) and all(chunk.crc_ok for chunk in chunks)


def validate_png_structure(data: bytes, *, require_decodable_idat: bool = True) -> PngValidationResult:
    errors: list[str] = []

    if not data.startswith(PNG_SIGNATURE):
        return PngValidationResult(("PNG signature is not at offset 0",))

    try:
        chunks = list(iter_chunks(data, signature_offset=0))
    except PngFormatError as error:
        return PngValidationResult((str(error),))

    if not chunks:
        return PngValidationResult(("PNG has no chunks",))

    iend_end = chunks[-1].offset + 12 + chunks[-1].length
    if iend_end != len(data):
        errors.append("PNG has trailing bytes after IEND")

    for chunk in chunks:
        if not _is_ascii_chunk_type(chunk.chunk_type):
            errors.append("Chunk type %r is not ASCII alphabetic" % chunk.chunk_type)
            continue
        if chunk.chunk_type[2] & 0x20:
            errors.append("Chunk %s has invalid reserved lowercase bit" % chunk.name)
        if not chunk.crc_ok:
            errors.append("Chunk %s has invalid CRC" % chunk.name)
        if _is_critical_chunk(chunk.chunk_type) and chunk.chunk_type not in {b"IHDR", b"PLTE", b"IDAT", b"IEND"}:
            errors.append("Unknown critical chunk %s" % chunk.name)

    chunk_types = [chunk.chunk_type for chunk in chunks]
    if chunk_types[0] != b"IHDR":
        errors.append("IHDR is not the first chunk")
    if chunk_types[-1] != b"IEND":
        errors.append("IEND is not the last chunk")
    if chunk_types.count(b"IHDR") != 1:
        errors.append("PNG must contain exactly one IHDR chunk")
    if chunk_types.count(b"IEND") != 1:
        errors.append("PNG must contain exactly one IEND chunk")
    if b"IDAT" not in chunk_types:
        errors.append("PNG must contain at least one IDAT chunk")

    ihdr = chunks[0] if chunks[0].chunk_type == b"IHDR" else next(
        (chunk for chunk in chunks if chunk.chunk_type == b"IHDR"),
        None,
    )
    ihdr_values = _parse_ihdr_data(ihdr) if ihdr is not None else None
    if ihdr is None or ihdr_values is None:
        errors.append("IHDR chunk is missing or malformed")
        return PngValidationResult(tuple(errors))

    width, height, bit_depth, color_type, compression, filter_method, interlace = ihdr_values
    if width <= 0 or height <= 0:
        errors.append("IHDR width and height must be greater than zero")
    if not valid_png_color_depth(bit_depth, color_type):
        errors.append("IHDR bit depth/color type combination is invalid")
    if compression != 0:
        errors.append("IHDR compression method must be 0")
    if filter_method != 0:
        errors.append("IHDR filter method must be 0")
    if interlace not in (0, 1):
        errors.append("IHDR interlace method must be 0 or 1")

    idat_indices = [index for index, chunk_type in enumerate(chunk_types) if chunk_type == b"IDAT"]
    plte_indices = [index for index, chunk_type in enumerate(chunk_types) if chunk_type == b"PLTE"]

    if idat_indices:
        first_idat = idat_indices[0]
        last_idat = idat_indices[-1]
        if idat_indices != list(range(first_idat, last_idat + 1)):
            errors.append("IDAT chunks must be consecutive")
        if plte_indices and plte_indices[0] > first_idat:
            errors.append("PLTE chunk must appear before the first IDAT chunk")

    if len(plte_indices) > 1:
        errors.append("PNG must not contain multiple PLTE chunks")
    if plte_indices:
        plte = chunks[plte_indices[0]]
        if not png_chunk_data_is_coherent(b"PLTE", plte.data):
            errors.append("PLTE chunk is malformed")
        if color_type in (0, 4):
            errors.append("PLTE chunk is not allowed for grayscale color types")
        if color_type == 3 and (plte.length // 3) > (2 ** bit_depth):
            errors.append("PLTE has too many entries for indexed bit depth")
    elif color_type == 3:
        errors.append("Indexed-color PNG requires a PLTE chunk")

    iend = chunks[-1]
    if iend.chunk_type == b"IEND" and iend.length != 0:
        errors.append("IEND chunk length must be zero")

    if require_decodable_idat and idat_indices:
        idat_data = b"".join(chunks[index].data for index in idat_indices)
        try:
            decompressed = zlib.decompress(idat_data)
        except zlib.error:
            errors.append("IDAT zlib stream is invalid")
        else:
            if interlace == 0:
                row_size = png_scanline_size(width, bit_depth, color_type)
                if row_size is None:
                    errors.append("Could not compute expected scanline size")
                elif len(decompressed) != row_size * height:
                    errors.append("IDAT decompressed size does not match IHDR dimensions")

    return PngValidationResult(tuple(errors))


def _is_critical_chunk(chunk_type: bytes) -> bool:
    return len(chunk_type) == 4 and not bool(chunk_type[0] & 0x20)


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


def _is_ascii_chunk_type(chunk_type: bytes) -> bool:
    return len(chunk_type) == 4 and all(65 <= value <= 90 or 97 <= value <= 122 for value in chunk_type)


def _repair_missing_data_byte_for_chunk(data: bytes, chunk: PngChunk) -> MissingChunkByteRepair | None:
    if not _is_ascii_chunk_type(chunk.chunk_type):
        return None
    if chunk.length < 1:
        return None

    data_start = chunk.offset + 8
    expected_data_end = data_start + chunk.length
    shifted_crc_start = expected_data_end - 1
    shifted_crc_end = shifted_crc_start + 4
    if shifted_crc_start < data_start or shifted_crc_end > len(data):
        return None

    observed = data[data_start:expected_data_end]
    if len(observed) != chunk.length:
        return None

    shifted_crc = int.from_bytes(data[shifted_crc_start:shifted_crc_end], "big")
    observed_without_crc_leak = observed[:-1]

    for insert_index in range(chunk.length):
        before = observed_without_crc_leak[:insert_index]
        after = observed_without_crc_leak[insert_index:]
        for value in range(256):
            candidate_chunk_data = before + bytes((value,)) + after
            if zlib.crc32(chunk.chunk_type + candidate_chunk_data) & 0xFFFFFFFF != shifted_crc:
                continue

            repaired = data[:data_start] + candidate_chunk_data + data[shifted_crc_start:]
            if is_complete_png_with_valid_crc(repaired):
                return MissingChunkByteRepair(
                    data=repaired,
                    strategy=(
                        "recovered missing data byte in %s chunk at relative offset %s"
                        % (chunk.name, insert_index)
                    ),
                    chunk_name=chunk.name,
                    inserted_offset=insert_index,
                    inserted_value=value,
                )

    return None


def repair_missing_chunk_data_byte(data: bytes, *, max_chunk_length: int = 65536) -> MissingChunkByteRepair | None:
    signature_offset = find_signature_offset(data)
    if signature_offset < 0:
        return None

    offset = signature_offset + len(PNG_SIGNATURE)
    while offset < len(data):
        chunk = chunk_at(data, offset)
        if chunk is None:
            return None

        if not chunk.crc_ok:
            if chunk.length > max_chunk_length:
                return None
            return _repair_missing_data_byte_for_chunk(data, chunk)

        offset = chunk.offset + 12 + chunk.length
        if chunk.chunk_type == b"IEND":
            return None

    return None


def png_chunk_data_is_coherent(chunk_type: bytes, chunk_data: bytes) -> bool:
    length = len(chunk_data)

    if chunk_type == b"IHDR":
        if length != 13:
            return False
        width, height, bit_depth, color_type, compression, filter_method, interlace = struct.unpack(
            "!IIBBBBB", chunk_data
        )
        return (
            width > 0
            and height > 0
            and valid_png_color_depth(bit_depth, color_type)
            and compression == 0
            and filter_method == 0
            and interlace in (0, 1)
        )

    if chunk_type == b"IEND":
        return length == 0

    if chunk_type == b"PLTE":
        entries = length // 3
        return length % 3 == 0 and 1 <= entries <= 256

    if chunk_type == b"gAMA":
        return length == 4 and int.from_bytes(chunk_data, "big") > 0

    if chunk_type == b"cHRM":
        return length == 32

    if chunk_type == b"sRGB":
        return length == 1 and chunk_data[0] in (0, 1, 2, 3)

    if chunk_type == b"pHYs":
        return length == 9 and chunk_data[8] in (0, 1)

    if chunk_type == b"tIME":
        if length != 7:
            return False
        year = int.from_bytes(chunk_data[:2], "big")
        month, day, hour, minute, second = chunk_data[2:]
        return year > 0 and 1 <= month <= 12 and 1 <= day <= 31 and hour <= 23 and minute <= 59 and second <= 60

    if chunk_type == b"iCCP":
        return iccp_decompressed_profile(PngChunk(0, length, chunk_type, chunk_data, 0)) is not None

    if chunk_type == b"zTXt":
        try:
            null_pos = chunk_data.index(0)
        except ValueError:
            return False
        if not 1 <= null_pos <= 79 or null_pos + 2 > length or chunk_data[null_pos + 1] != 0:
            return False
        try:
            zlib.decompress(chunk_data[null_pos + 2 :])
        except zlib.error:
            return False
        return True

    if chunk_type == b"sPLT":
        try:
            null_pos = chunk_data.index(0)
        except ValueError:
            return False
        if not 1 <= null_pos <= 79 or null_pos + 1 >= length:
            return False
        sample_depth = chunk_data[null_pos + 1]
        entries_length = length - null_pos - 2
        return (sample_depth == 8 and entries_length % 6 == 0) or (sample_depth == 16 and entries_length % 10 == 0)

    if chunk_type == b"IDAT":
        return length > 0

    return False


def repair_known_chunk_type_case(data: bytes, known_chunk_types: Iterable[bytes]) -> ChunkTypeRepair | None:
    canonical_by_lower = {chunk_type.lower(): chunk_type for chunk_type in known_chunk_types}

    try:
        chunks = list(iter_chunks(data))
    except PngFormatError:
        return None

    for chunk in chunks:
        canonical = canonical_by_lower.get(chunk.chunk_type.lower())
        if canonical is None or canonical == chunk.chunk_type:
            continue
        if not png_chunk_data_is_coherent(canonical, chunk.data):
            continue

        repaired_chunk = build_png_chunk(canonical, chunk.data)
        repaired = replace_png_chunk(data, chunk, repaired_chunk)
        if not is_complete_png_with_valid_crc(repaired):
            continue

        return ChunkTypeRepair(
            data=repaired,
            strategy="renamed known chunk %s to %s and rebuilt CRC" % (chunk.name, canonical.decode("ascii")),
            original_name=chunk.name,
            repaired_name=canonical.decode("ascii"),
        )

    return None


def is_unknown_private_critical_unsafe_chunk(chunk: PngChunk, known_chunk_types: Iterable[bytes]) -> bool:
    if not _is_ascii_chunk_type(chunk.chunk_type):
        return False

    canonical_by_lower = {chunk_type.lower(): chunk_type for chunk_type in known_chunk_types}
    if chunk.chunk_type.lower() in canonical_by_lower:
        return False

    critical = not bool(chunk.chunk_type[0] & 0x20)
    private = bool(chunk.chunk_type[1] & 0x20)
    reserved_ok = not bool(chunk.chunk_type[2] & 0x20)
    unsafe_to_copy = not bool(chunk.chunk_type[3] & 0x20)
    return critical and private and reserved_ok and unsafe_to_copy


def repair_unknown_private_critical_chunks(
    data: bytes,
    known_chunk_types: Iterable[bytes],
) -> ChunkRemovalRepair | None:
    known_chunk_types = tuple(known_chunk_types)
    result = remove_png_chunks(data, lambda chunk: is_unknown_private_critical_unsafe_chunk(chunk, known_chunk_types))
    if result is None:
        return None

    repaired, removed = result
    if not is_complete_png_with_valid_crc(repaired):
        return None

    removed_names = tuple(chunk.name for chunk in removed)
    return ChunkRemovalRepair(
        data=repaired,
        strategy="removed unknown private critical unsafe-to-copy chunk(s): %s" % ", ".join(removed_names),
        removed_chunks=removed_names,
    )


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
