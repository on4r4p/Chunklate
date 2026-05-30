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
SRGB_CHRM_PAYLOAD = struct.pack(
    "!IIIIIIII",
    31270,
    32900,
    64000,
    33000,
    30000,
    60000,
    15000,
    6000,
)


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
class PngSignatureRecovery:
    action: str
    signature_offset: int | None = None
    fixed_data: bytes | None = None
    linefeed_pattern: str | None = None

    @property
    def signature_hex_offset(self) -> int | None:
        if self.signature_offset is None:
            return None
        return self.signature_offset * 2


@dataclass(frozen=True)
class LegacyLengthStatus:
    declared_length: int
    has_next_chunk: bool
    next_chunk_type: bytes


@dataclass(frozen=True)
class LegacyLengthDecision:
    declared_length: int
    has_next_chunk: bool
    next_chunk_type: bytes
    is_huge: bool
    idat_length_differs: bool
    checkpoint_error: bool
    checkpoint_info: str


@dataclass(frozen=True)
class LegacyCrcDecision:
    chunk_type: bytes
    chunk_data: bytes
    stored_crc_hex: str
    computed_crc_hex: str

    @property
    def ok(self) -> bool:
        return self.computed_crc_hex == self.stored_crc_hex

    @property
    def normalized_computed_crc(self) -> str:
        if len(self.computed_crc_hex) < 10:
            return "0x" + self.computed_crc_hex[2:].zfill(8)
        return self.computed_crc_hex

    @property
    def normalized_computed_crc_no_prefix(self) -> str:
        return self.normalized_computed_crc[2:]


@dataclass(frozen=True)
class IhdrRepair:
    data: bytes
    strategy: str
    preserved_crc: bool
    width: int | None = None
    height: int | None = None
    bit_depth: int | None = None
    color_type: int | None = None
    strict_candidate_count: int = 0
    selection_score: tuple[int, ...] | None = None


@dataclass(frozen=True)
class IhdrRebuildCandidate:
    data: bytes
    ihdr_data: bytes
    width: int
    height: int
    bit_depth: int
    color_type: int
    score: tuple[int, int, int, int, int]


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
class ItxtRepair:
    data: bytes
    strategy: str
    chunk_offset: int
    old_keyword_length: int | None = None
    new_keyword: bytes | None = None
    old_flag: int | None = None
    new_flag: int | None = None
    old_method: int | None = None
    new_method: int | None = None


@dataclass(frozen=True)
class BkgdRepair:
    data: bytes
    strategy: str
    chunk_offset: int
    old_length: int
    new_length: int
    removed: bool = False


@dataclass(frozen=True)
class GamaRepair:
    data: bytes
    strategy: str
    chunk_offset: int
    old_length: int
    new_length: int
    removed: bool = False
    inferred_payload: bytes | None = None
    missing_bytes: int = 0


@dataclass(frozen=True)
class ChunkDataLengthRepair:
    data: bytes
    strategy: str
    chunk_name: str
    chunk_offset: int
    old_length: int
    new_length: int
    removed: bool = False


@dataclass(frozen=True)
class ChrmRepair:
    data: bytes
    strategy: str
    chunk_offset: int
    old_length: int
    new_length: int
    removed: bool = False
    missing_bytes: int = 0
    inferred_payload: bytes | None = None
    removal_data: bytes | None = None
    preserved_crc: bool = False
    crc_bruteforce_attempted: bool = False
    crc_candidates_tested: int = 0


@dataclass(frozen=True)
class MissingChunkByteRepair:
    data: bytes
    strategy: str
    chunk_name: str
    inserted_offset: int
    inserted_value: int


@dataclass(frozen=True)
class ChunkLengthRealignmentRepair:
    data: bytes
    strategy: str
    chunk_name: str
    chunk_offset: int
    old_length: int
    new_length: int
    next_chunk_offset: int
    rebuilt_crc: int


@dataclass(frozen=True)
class LinefeedPayloadPatch:
    chunk_type: bytes
    chunk_offset: int
    payload_offset: int
    insert_offset: int
    inserted_value: int
    stored_crc: int


@dataclass(frozen=True)
class LinefeedConversionRepair:
    data: bytes
    strategy: str
    linefeed_pattern: str
    removed_prefix_bytes: int
    inserted_signature_cr: bool
    payload_patches: tuple[LinefeedPayloadPatch, ...]
    validation_errors: tuple[str, ...] = ()


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


def extract_png_segment(data: bytes, *, signature_offset: int | None = None) -> bytes | None:
    if signature_offset is None:
        signature_offset = find_signature_offset(data)
    if signature_offset < 0:
        return None

    offset = signature_offset + len(PNG_SIGNATURE)
    while offset < len(data):
        if len(data) - offset < 12:
            return None

        length = int.from_bytes(data[offset : offset + 4], "big")
        chunk_type = data[offset + 4 : offset + 8]
        chunk_end = offset + 12 + length
        if chunk_end > len(data):
            return None

        offset = chunk_end
        if chunk_type == b"IEND":
            return data[signature_offset:offset]

    return None


def detect_png_signature_recovery(data: bytes) -> PngSignatureRecovery:
    signature_offset = find_signature_offset(data)
    if signature_offset == 0:
        return PngSignatureRecovery("found_at_start", signature_offset=0)
    if signature_offset > 0:
        fixed_data = extract_png_segment(data, signature_offset=signature_offset)
        return PngSignatureRecovery(
            "cut_at_signature",
            signature_offset=signature_offset,
            fixed_data=fixed_data if fixed_data is not None else data[signature_offset:],
        )

    data_hex = data.hex()
    linefeed_patterns = (
        ("major_linefeed_corruption", "89504e470a1a0a00000004948445200"),
        ("minor_linefeed_corruption", "89504e470a1a0a0000000d4948445200"),
    )
    for name, pattern in linefeed_patterns:
        pattern_hex_offset = data_hex.find(pattern)
        if pattern_hex_offset >= 0:
            return PngSignatureRecovery(
                "linefeed_signature_candidate",
                signature_offset=pattern_hex_offset // 2,
                linefeed_pattern=name,
            )

    return PngSignatureRecovery("search_deeper")


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


def legacy_length_decision(
    data: bytes,
    hex_offset: int,
    *,
    previous_chunk: bytes,
    idat_average_length: int,
    huge_threshold: int = 26736,
) -> LegacyLengthDecision:
    status = legacy_length_status(data, hex_offset)
    idat_length_differs = (
        previous_chunk == b"IDAT"
        and idat_average_length != status.declared_length
    )
    checkpoint_error = not status.has_next_chunk

    return LegacyLengthDecision(
        declared_length=status.declared_length,
        has_next_chunk=status.has_next_chunk,
        next_chunk_type=status.next_chunk_type,
        is_huge=status.declared_length > huge_threshold,
        idat_length_differs=idat_length_differs,
        checkpoint_error=checkpoint_error,
        checkpoint_info="-No NextChunk" if checkpoint_error else "-Found NextChunk",
    )


def legacy_length_checkpoint_args(
    decision: LegacyLengthDecision,
    chunk_type: bytes,
    chunk_length: str,
    previous_chunk: bytes,
) -> tuple[object, ...]:
    if decision.checkpoint_error:
        return (
            True,
            False,
            "CheckLength",
            chunk_type,
            [decision.checkpoint_info],
            chunk_type,
            chunk_length,
            previous_chunk,
        )

    return (
        False,
        False,
        "CheckLength",
        chunk_type,
        [decision.checkpoint_info],
        chunk_length,
    )


def legacy_find_magic_checkpoint_args(
    recovery: PngSignatureRecovery,
    magic_hex_length: int,
) -> tuple[object, ...]:
    if recovery.action == "found_at_start":
        return (
            False,
            False,
            "FindMagic",
            "PngSig",
            ["-Found Magic"],
            recovery.signature_hex_offset + magic_hex_length,
        )

    if recovery.action == "cut_at_signature":
        return (
            False,
            False,
            "FindMagic",
            "PngSig",
            ["Cutting at Magic"],
            recovery.fixed_data.hex(),
            hex(int(recovery.signature_hex_offset / 2)),
        )

    return (
        False,
        False,
        "FindMagic",
        "PngSig",
        ["-dig a little bit deeper"],
    )


def legacy_crc_decision(raw_type_hex: str, raw_data_hex: str, raw_crc_hex: str) -> LegacyCrcDecision:
    chunk_type = bytes.fromhex(raw_type_hex)
    chunk_data = bytes.fromhex(raw_data_hex)
    stored_crc = hex(int.from_bytes(bytes.fromhex(raw_crc_hex), byteorder="big"))
    computed_crc = hex(zlib.crc32(chunk_type + chunk_data))
    return LegacyCrcDecision(
        chunk_type=chunk_type,
        chunk_data=chunk_data,
        stored_crc_hex=stored_crc,
        computed_crc_hex=computed_crc,
    )


def legacy_crc_debug_lines(decision: LegacyCrcDecision) -> tuple[str, str]:
    return (
        "-Crc from file: %s" % str(decision.computed_crc_hex),
        "-Actual Crc: %s\n" % str(decision.stored_crc_hex),
    )


def legacy_crc_monkey_lines(wanted: str, got: str) -> tuple[str, str]:
    return (
        "\nMonkey wanted Banana :%s" % wanted,
        "Monkey got Pullover :%s" % got,
    )


def legacy_crc_checkpoint_args(
    decision: LegacyCrcDecision,
    crc_offset: int,
    original_chunk_type: bytes,
    crc_offset_hex: str,
    original_crc: str,
    original_length: str,
    data_offset: int,
) -> tuple[object, ...]:
    if decision.ok:
        return (
            False,
            False,
            "Checksum",
            decision.chunk_type,
            ["-Crc is correct"],
        )

    return (
        True,
        False,
        "Checksum",
        decision.chunk_type,
        ["-Wrong Crc %s" % str(decision.chunk_type)],
        decision.normalized_computed_crc_no_prefix,
        crc_offset,
        crc_offset + 8,
        original_chunk_type,
        crc_offset_hex,
        original_crc,
        int(original_length, 16),
        data_offset,
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


def _itxt_text_offset(chunk_data: bytes) -> int | None:
    try:
        keyword_end = chunk_data.index(0)
    except ValueError:
        return None

    if keyword_end == 0 or keyword_end > 79 or keyword_end + 3 > len(chunk_data):
        return None

    language_start = keyword_end + 3
    try:
        language_end = chunk_data.index(0, language_start)
    except ValueError:
        return None

    translated_start = language_end + 1
    try:
        translated_end = chunk_data.index(0, translated_start)
    except ValueError:
        return None

    return translated_end + 1


def _itxt_best_repaired_compression_flag(chunk_data: bytes, flag_offset: int) -> int | None:
    old_flag = chunk_data[flag_offset]
    if old_flag in (0, 1):
        return None

    text_offset = _itxt_text_offset(chunk_data)
    if text_offset is None:
        return None

    method = chunk_data[flag_offset + 1]
    text = chunk_data[text_offset:]
    if method == 0:
        try:
            zlib.decompress(text).decode("utf-8")
        except (UnicodeDecodeError, zlib.error):
            return 0
        return 1

    return 0


def _itxt_compression_method_offset(chunk_data: bytes) -> int | None:
    try:
        keyword_end = chunk_data.index(0)
    except ValueError:
        return None

    method_offset = keyword_end + 2
    if keyword_end == 0 or keyword_end > 79 or method_offset >= len(chunk_data):
        return None
    return method_offset


def _bkgd_expected_length_for_color_type(color_type: int) -> int | None:
    return {
        0: 2,
        4: 2,
        2: 6,
        6: 6,
        3: 1,
    }.get(color_type)


def _sbit_expected_length_for_color_type(color_type: int) -> int | None:
    return {
        0: 1,
        2: 3,
        3: 3,
        4: 2,
        6: 4,
    }.get(color_type)


COMMON_GAMA_PAYLOADS: tuple[bytes, ...] = (
    (100000).to_bytes(4, "big"),
    (45455).to_bytes(4, "big"),
    (50000).to_bytes(4, "big"),
    (220000).to_bytes(4, "big"),
)


def _complete_short_gama_payload(payload: bytes) -> bytes | None:
    if len(payload) >= 4:
        return None

    matches = [candidate for candidate in COMMON_GAMA_PAYLOADS if candidate.startswith(payload)]
    if len(matches) == 1:
        return matches[0]

    return None


def _chrm_payload_values(payload: bytes) -> tuple[int, ...] | None:
    if len(payload) != 32:
        return None
    return struct.unpack("!IIIIIIII", payload)


def _chrm_payload_score(payload: bytes) -> tuple[int, int, int] | None:
    values = _chrm_payload_values(payload)
    standard = _chrm_payload_values(SRGB_CHRM_PAYLOAD)
    if values is None or standard is None:
        return None
    if any(value > 100000 for value in values):
        return None

    pairs = tuple(zip(values[::2], values[1::2], strict=True))
    pair_overflow = sum(max(0, x + y - 100000) for x, y in pairs)
    zero_count = sum(1 for value in values if value == 0)
    standard_distance = sum(abs(value - expected) for value, expected in zip(values, standard, strict=True))
    return (-pair_overflow, -zero_count, -standard_distance)


def _complete_short_chrm_payload(payload: bytes) -> bytes | None:
    deficit = 32 - len(payload)
    if deficit <= 0:
        return None

    candidates: list[bytes] = []
    if SRGB_CHRM_PAYLOAD.startswith(payload):
        candidates.append(SRGB_CHRM_PAYLOAD)

    if deficit == 1:
        candidates.extend(payload + bytes((value,)) for value in range(256))
    elif deficit == 2:
        candidates.extend(
            payload + high.to_bytes(1, "big") + low.to_bytes(1, "big")
            for high in range(256)
            for low in range(256)
        )
    elif not candidates:
        return None

    scored = [
        (score, candidate)
        for candidate in candidates
        if (score := _chrm_payload_score(candidate)) is not None
    ]
    if not scored:
        return None
    return max(scored, key=lambda item: item[0])[1]


def _complete_short_chrm_payload_by_crc(
    payload: bytes,
    stored_crc: int,
) -> tuple[bytes | None, int]:
    deficit = 32 - len(payload)
    if deficit <= 0:
        return None, 0

    if deficit == 1:
        tested = 0
        for value in range(256):
            tested += 1
            candidate = payload + bytes((value,))
            if zlib.crc32(b"cHRM" + candidate) & 0xFFFFFFFF == stored_crc:
                return candidate, tested
        return None, tested

    if deficit == 2:
        tested = 0
        for value in range(65536):
            tested += 1
            candidate = payload + value.to_bytes(2, "big")
            if zlib.crc32(b"cHRM" + candidate) & 0xFFFFFFFF == stored_crc:
                return candidate, tested
        return None, tested

    return None, 0


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
    """Validate a final repaired PNG, not a corrupted input candidate."""

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

    gama_indices = [index for index, chunk_type in enumerate(chunk_types) if chunk_type == b"gAMA"]
    if len(gama_indices) > 1:
        errors.append("PNG must not contain multiple gAMA chunks")
    if gama_indices:
        gama = chunks[gama_indices[0]]
        if gama.length != 4:
            errors.append("gAMA chunk length must be 4")
        elif int.from_bytes(gama.data, "big") == 0:
            errors.append("gAMA value must be greater than zero")

    srgb_indices = [index for index, chunk_type in enumerate(chunk_types) if chunk_type == b"sRGB"]
    if len(srgb_indices) > 1:
        errors.append("PNG must not contain multiple sRGB chunks")
    if srgb_indices:
        srgb = chunks[srgb_indices[0]]
        if srgb.length != 1:
            errors.append("sRGB chunk length must be 1")
        elif srgb.data[0] not in (0, 1, 2, 3):
            errors.append("sRGB rendering intent must be 0, 1, 2, or 3")

    sbit_indices = [index for index, chunk_type in enumerate(chunk_types) if chunk_type == b"sBIT"]
    if len(sbit_indices) > 1:
        errors.append("PNG must not contain multiple sBIT chunks")
    if sbit_indices:
        sbit = chunks[sbit_indices[0]]
        expected_sbit_length = _sbit_expected_length_for_color_type(color_type)
        if expected_sbit_length is not None and sbit.length != expected_sbit_length:
            errors.append(
                "sBIT chunk length must be %s for IHDR color type %s"
                % (expected_sbit_length, color_type)
            )

    phys_indices = [index for index, chunk_type in enumerate(chunk_types) if chunk_type == b"pHYs"]
    if len(phys_indices) > 1:
        errors.append("PNG must not contain multiple pHYs chunks")
    if phys_indices:
        phys = chunks[phys_indices[0]]
        if phys.length != 9:
            errors.append("pHYs chunk length must be 9")
        elif phys.data[8] not in (0, 1):
            errors.append("pHYs unit specifier must be 0 or 1")

    offs_indices = [index for index, chunk_type in enumerate(chunk_types) if chunk_type == b"oFFs"]
    if len(offs_indices) > 1:
        errors.append("PNG must not contain multiple oFFs chunks")
    if offs_indices:
        offs = chunks[offs_indices[0]]
        if offs.length != 9:
            errors.append("oFFs chunk length must be 9")
        elif offs.data[8] not in (0, 1):
            errors.append("oFFs unit specifier must be 0 or 1")

    time_indices = [index for index, chunk_type in enumerate(chunk_types) if chunk_type == b"tIME"]
    if len(time_indices) > 1:
        errors.append("PNG must not contain multiple tIME chunks")
    if time_indices:
        time = chunks[time_indices[0]]
        if time.length != 7:
            errors.append("tIME chunk length must be 7")

    ster_indices = [index for index, chunk_type in enumerate(chunk_types) if chunk_type == b"sTER"]
    if len(ster_indices) > 1:
        errors.append("PNG must not contain multiple sTER chunks")
    if ster_indices:
        ster = chunks[ster_indices[0]]
        if ster.length != 1:
            errors.append("sTER chunk length must be 1")
        elif ster.data[0] not in (0, 1):
            errors.append("sTER mode must be 0 or 1")

    gifg_indices = [index for index, chunk_type in enumerate(chunk_types) if chunk_type == b"gIFg"]
    if len(gifg_indices) > 1:
        errors.append("PNG must not contain multiple gIFg chunks")
    if gifg_indices:
        gifg = chunks[gifg_indices[0]]
        if gifg.length != 4:
            errors.append("gIFg chunk length must be 4")

    hist_indices = [index for index, chunk_type in enumerate(chunk_types) if chunk_type == b"hIST"]
    if len(hist_indices) > 1:
        errors.append("PNG must not contain multiple hIST chunks")
    if hist_indices:
        hist = chunks[hist_indices[0]]
        if hist.length == 0 or hist.length % 2 != 0:
            errors.append("hIST chunk length must be a non-zero multiple of 2")
        if plte_indices:
            expected_hist_length = chunks[plte_indices[0]].length // 3 * 2
            if hist.length != expected_hist_length:
                errors.append("hIST chunk length must match PLTE entry count")
        else:
            errors.append("hIST chunk requires a PLTE chunk")

    trns_indices = [index for index, chunk_type in enumerate(chunk_types) if chunk_type == b"tRNS"]
    if len(trns_indices) > 1:
        errors.append("PNG must not contain multiple tRNS chunks")
    if trns_indices:
        trns = chunks[trns_indices[0]]
        if color_type == 0 and trns.length != 2:
            errors.append("tRNS chunk length must be 2 for IHDR color type 0")
        elif color_type == 2 and trns.length != 6:
            errors.append("tRNS chunk length must be 6 for IHDR color type 2")
        elif color_type == 3:
            if trns.length == 0:
                errors.append("tRNS chunk length must not be zero for IHDR color type 3")
            if plte_indices and trns.length > chunks[plte_indices[0]].length // 3:
                errors.append("tRNS chunk length must not exceed PLTE entry count")
        elif color_type in (4, 6):
            errors.append("tRNS chunk is not allowed for alpha color types")

    bkgd_indices = [index for index, chunk_type in enumerate(chunk_types) if chunk_type == b"bKGD"]
    if len(bkgd_indices) > 1:
        errors.append("PNG must not contain multiple bKGD chunks")
    if bkgd_indices:
        bkgd = chunks[bkgd_indices[0]]
        expected_bkgd_length = _bkgd_expected_length_for_color_type(color_type)
        if expected_bkgd_length is not None and bkgd.length != expected_bkgd_length:
            errors.append(
                "bKGD chunk length must be %s for IHDR color type %s"
                % (expected_bkgd_length, color_type)
            )

    chrm_indices = [index for index, chunk_type in enumerate(chunk_types) if chunk_type == b"cHRM"]
    if len(chrm_indices) > 1:
        errors.append("PNG must not contain multiple cHRM chunks")
    if chrm_indices:
        chrm = chunks[chrm_indices[0]]
        if chrm.length != 32:
            errors.append("cHRM chunk length must be 32")

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
                else:
                    invalid_filter_row = next(
                        (
                            row
                            for row in range(height)
                            if decompressed[row * row_size] not in range(5)
                        ),
                        None,
                    )
                    if invalid_filter_row is not None:
                        errors.append("IDAT scanline filter type is invalid")

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


def _insert_png_signature_cr(data: bytes) -> tuple[bytes, bool] | None:
    if data.startswith(PNG_SIGNATURE):
        return data, False
    if data.startswith(b"\x89PNG\n\x1a\n"):
        return data[:4] + b"\r" + data[4:], True
    return None


def _linefeed_candidate_next_chunk_start(
    data: bytes,
    *,
    expected_next: int,
    max_missing: int,
) -> tuple[int, int] | None:
    for missing in range(1, max_missing + 1):
        candidate_next = expected_next - missing
        if candidate_next < len(PNG_SIGNATURE):
            continue
        if candidate_next + 8 > len(data):
            continue
        chunk_type = data[candidate_next + 4 : candidate_next + 8]
        if _is_ascii_chunk_type(chunk_type):
            return candidate_next, missing
    return None


def _restore_missing_linefeed_cr(
    *,
    chunk_type: bytes,
    payload: bytes,
    stored_crc: int,
    missing_count: int,
) -> tuple[bytes, int] | None:
    if missing_count != 1:
        return None

    for insert_offset in range(len(payload) + 1):
        candidate = payload[:insert_offset] + b"\r" + payload[insert_offset:]
        if zlib.crc32(chunk_type + candidate) & 0xFFFFFFFF == stored_crc:
            return candidate, insert_offset
    return None


def repair_linefeed_conversion(
    data: bytes,
    *,
    max_missing_per_chunk: int = 4,
    allow_partial: bool = False,
) -> LinefeedConversionRepair | None:
    recovery = detect_png_signature_recovery(data)
    if recovery.action != "linefeed_signature_candidate" or recovery.signature_offset is None:
        return None

    source = data[recovery.signature_offset:]
    signature_result = _insert_png_signature_cr(source)
    if signature_result is None:
        return None

    repaired, inserted_signature_cr = signature_result
    patches: list[LinefeedPayloadPatch] = []
    offset = len(PNG_SIGNATURE)
    valid_chunk_count = 0

    def partial_repair() -> LinefeedConversionRepair | None:
        if not allow_partial:
            return None
        if not inserted_signature_cr and not patches:
            return None
        if valid_chunk_count < 1:
            return None

        validation_errors = validate_png_structure(repaired).errors
        if not validation_errors:
            validation_errors = ("Line feed conversion repair is incomplete.",)

        return LinefeedConversionRepair(
            data=repaired,
            strategy="partially restored carriage returns removed by line feed conversion",
            linefeed_pattern=recovery.linefeed_pattern or "",
            removed_prefix_bytes=recovery.signature_offset,
            inserted_signature_cr=inserted_signature_cr,
            payload_patches=tuple(patches),
            validation_errors=validation_errors,
        )

    while offset < len(repaired):
        if len(repaired) - offset < 12:
            return partial_repair()

        length = int.from_bytes(repaired[offset : offset + 4], "big")
        chunk_type = repaired[offset + 4 : offset + 8]
        if not _is_ascii_chunk_type(chunk_type):
            return partial_repair()

        data_start = offset + 8
        data_end = data_start + length
        crc_end = data_end + 4

        if crc_end <= len(repaired):
            stored_crc = int.from_bytes(repaired[data_end:crc_end], "big")
            payload = repaired[data_start:data_end]
            if zlib.crc32(chunk_type + payload) & 0xFFFFFFFF == stored_crc:
                valid_chunk_count += 1
                offset = crc_end
                if chunk_type == b"IEND":
                    repaired = repaired[:crc_end]
                    break
                continue

        candidate = _linefeed_candidate_next_chunk_start(
            repaired,
            expected_next=offset + 12 + length,
            max_missing=max_missing_per_chunk,
        )
        if candidate is None:
            return partial_repair()

        next_chunk_start, missing_count = candidate
        crc_start = next_chunk_start - 4
        if crc_start < data_start:
            return partial_repair()

        shifted_payload = repaired[data_start:crc_start]
        stored_crc = int.from_bytes(repaired[crc_start:next_chunk_start], "big")
        restored = _restore_missing_linefeed_cr(
            chunk_type=chunk_type,
            payload=shifted_payload,
            stored_crc=stored_crc,
            missing_count=missing_count,
        )
        if restored is None:
            return partial_repair()

        fixed_payload, insert_offset = restored
        repaired = repaired[:data_start] + fixed_payload + repaired[crc_start:]
        patches.append(
            LinefeedPayloadPatch(
                chunk_type=chunk_type,
                chunk_offset=offset,
                payload_offset=insert_offset,
                insert_offset=data_start + insert_offset,
                inserted_value=0x0D,
                stored_crc=stored_crc,
            )
        )
        valid_chunk_count += 1
        offset = data_start + length + 4
        if chunk_type == b"IEND":
            repaired = repaired[:offset]
            break

    validation_errors = validate_png_structure(repaired).errors
    if validation_errors:
        partial = partial_repair()
        if partial is not None:
            return partial
        return None

    return LinefeedConversionRepair(
        data=repaired,
        strategy="restored carriage returns removed by line feed conversion",
        linefeed_pattern=recovery.linefeed_pattern or "",
        removed_prefix_bytes=recovery.signature_offset,
        inserted_signature_cr=inserted_signature_cr,
        payload_patches=tuple(patches),
        validation_errors=(),
    )


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


def repair_overlong_chunk_length_to_next_header(
    data: bytes,
    *,
    max_overrun: int = 16,
    chunk_types: tuple[bytes, ...] = (b"IDAT",),
) -> ChunkLengthRealignmentRepair | None:
    signature_offset = find_signature_offset(data)
    if signature_offset < 0:
        return None

    repaired = bytearray(data)
    offset = signature_offset + len(PNG_SIGNATURE)
    while offset < len(repaired):
        if len(repaired) - offset < 12:
            return None

        length = int.from_bytes(repaired[offset : offset + 4], "big")
        chunk_type = bytes(repaired[offset + 4 : offset + 8])
        if not _is_ascii_chunk_type(chunk_type):
            return None

        data_start = offset + 8
        data_end = data_start + length
        crc_end = data_end + 4
        if crc_end <= len(repaired):
            stored_crc = int.from_bytes(repaired[data_end:crc_end], "big")
            payload = bytes(repaired[data_start:data_end])
            if zlib.crc32(chunk_type + payload) & 0xFFFFFFFF == stored_crc:
                offset = crc_end
                if chunk_type == b"IEND":
                    return None
                continue

        if chunk_types and chunk_type not in chunk_types:
            return None

        expected_next = offset + 12 + length
        for overrun in range(1, max_overrun + 1):
            next_chunk_offset = expected_next - overrun
            if next_chunk_offset <= data_start + 4:
                continue
            if next_chunk_offset + 8 > len(repaired):
                continue

            next_chunk_type = bytes(repaired[next_chunk_offset + 4 : next_chunk_offset + 8])
            if not _is_ascii_chunk_type(next_chunk_type):
                continue

            new_data_end = next_chunk_offset - 4
            new_length = new_data_end - data_start
            if new_length < 0 or new_length >= length:
                continue

            payload = bytes(repaired[data_start:new_data_end])
            rebuilt_crc = zlib.crc32(chunk_type + payload) & 0xFFFFFFFF
            candidate_data = bytearray(repaired)
            candidate_data[offset : offset + 4] = new_length.to_bytes(4, "big")
            candidate_data[new_data_end:next_chunk_offset] = rebuilt_crc.to_bytes(4, "big")

            try:
                candidate = bytes(candidate_data)
                chunks = list(iter_chunks(candidate, signature_offset=signature_offset))
            except PngFormatError:
                continue

            if any(not chunk.crc_ok for chunk in chunks):
                continue
            if not chunks or chunks[-1].chunk_type != b"IEND":
                continue
            iend_end = chunks[-1].offset + 12 + chunks[-1].length
            if iend_end != len(candidate):
                continue

            return ChunkLengthRealignmentRepair(
                data=candidate,
                strategy=(
                    "realigned overlong %s chunk length from %s to %s and rebuilt CRC"
                    % (chunk_type.decode("ascii", errors="replace"), length, new_length)
                ),
                chunk_name=chunk_type.decode("ascii", errors="replace"),
                chunk_offset=offset,
                old_length=length,
                new_length=new_length,
                next_chunk_offset=next_chunk_offset,
                rebuilt_crc=rebuilt_crc,
            )

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

    if chunk_type == b"gIFg":
        return length == 4

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


def known_bad_srgb_profile_warning(data: bytes) -> str:
    try:
        chunks = list(iter_chunks(data))
    except PngFormatError:
        return ""

    if any(is_known_bad_srgb_iccp_chunk(chunk) for chunk in chunks):
        return "libpng warning: iCCP: known incorrect sRGB profile"

    return ""


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


def repair_bkgd_length(data: bytes) -> BkgdRepair | None:
    try:
        chunks = list(iter_chunks(data))
    except PngFormatError:
        return None

    ihdr = next((chunk for chunk in chunks if chunk.chunk_type == b"IHDR"), None)
    bkgd = next((chunk for chunk in chunks if chunk.chunk_type == b"bKGD"), None)
    if ihdr is None or bkgd is None:
        return None

    ihdr_values = _parse_ihdr_data(ihdr)
    if ihdr_values is None:
        return None

    _width, _height, _bit_depth, color_type, _method, _filter_method, _interlace = ihdr_values
    expected_length = _bkgd_expected_length_for_color_type(color_type)
    if expected_length is None or bkgd.length == expected_length:
        return None

    if bkgd.length > expected_length:
        repaired_chunk = build_png_chunk(b"bKGD", bkgd.data[:expected_length])
        repaired = replace_png_chunk(data, bkgd, repaired_chunk)
        if not is_complete_png_with_valid_crc(repaired):
            return None
        return BkgdRepair(
            data=repaired,
            strategy=(
                "trimmed bKGD length from %s to %s and rebuilt CRC"
                % (bkgd.length, expected_length)
            ),
            chunk_offset=bkgd.offset,
            old_length=bkgd.length,
            new_length=expected_length,
        )

    repaired = replace_png_chunk(data, bkgd, b"")
    if not is_complete_png_with_valid_crc(repaired):
        return None
    return BkgdRepair(
        data=repaired,
        strategy=(
            "removed short bKGD chunk length %s below required %s"
            % (bkgd.length, expected_length)
        ),
        chunk_offset=bkgd.offset,
        old_length=bkgd.length,
        new_length=0,
        removed=True,
    )


def repair_gama_length(data: bytes) -> GamaRepair | None:
    try:
        chunks = list(iter_chunks(data))
    except PngFormatError:
        return None

    gama = next((chunk for chunk in chunks if chunk.chunk_type == b"gAMA"), None)
    if gama is None or gama.length == 4:
        return None

    if gama.length > 4:
        payload = gama.data[:4]
        if int.from_bytes(payload, "big") == 0:
            return None
        repaired_chunk = build_png_chunk(b"gAMA", payload)
        repaired = replace_png_chunk(data, gama, repaired_chunk)
        if not is_complete_png_with_valid_crc(repaired):
            return None
        return GamaRepair(
            data=repaired,
            strategy="trimmed gAMA length from %s to 4 and rebuilt CRC" % gama.length,
            chunk_offset=gama.offset,
            old_length=gama.length,
            new_length=4,
        )

    inferred_payload = _complete_short_gama_payload(gama.data)
    if inferred_payload is not None and int.from_bytes(inferred_payload, "big") > 0:
        repaired_chunk = build_png_chunk(b"gAMA", inferred_payload)
        repaired = replace_png_chunk(data, gama, repaired_chunk)
        if is_complete_png_with_valid_crc(repaired):
            return GamaRepair(
                data=repaired,
                strategy=(
                    "inferred %s missing gAMA byte(s) from common gamma value and rebuilt CRC"
                    % (4 - gama.length)
                ),
                chunk_offset=gama.offset,
                old_length=gama.length,
                new_length=4,
                inferred_payload=inferred_payload,
                missing_bytes=4 - gama.length,
            )

    repaired = replace_png_chunk(data, gama, b"")
    if not is_complete_png_with_valid_crc(repaired):
        return None
    return GamaRepair(
        data=repaired,
        strategy="removed short gAMA chunk length %s below required 4" % gama.length,
        chunk_offset=gama.offset,
        old_length=gama.length,
        new_length=0,
        removed=True,
        missing_bytes=4 - gama.length,
    )


def _repair_fixed_length_chunk(
    data: bytes,
    chunk_type: bytes,
    expected_length: int,
) -> ChunkDataLengthRepair | None:
    try:
        chunks = list(iter_chunks(data))
    except PngFormatError:
        return None

    chunk = next((item for item in chunks if item.chunk_type == chunk_type), None)
    if chunk is None or chunk.length == expected_length:
        return None

    chunk_name = chunk_type.decode("ascii", errors="replace")
    if chunk.length > expected_length:
        repaired_chunk = build_png_chunk(chunk_type, chunk.data[:expected_length])
        repaired = replace_png_chunk(data, chunk, repaired_chunk)
        if not is_complete_png_with_valid_crc(repaired):
            return None
        return ChunkDataLengthRepair(
            data=repaired,
            strategy=(
                "trimmed %s length from %s to %s and rebuilt CRC"
                % (chunk_name, chunk.length, expected_length)
            ),
            chunk_name=chunk_name,
            chunk_offset=chunk.offset,
            old_length=chunk.length,
            new_length=expected_length,
        )

    repaired = replace_png_chunk(data, chunk, b"")
    if not is_complete_png_with_valid_crc(repaired):
        return None
    return ChunkDataLengthRepair(
        data=repaired,
        strategy=(
            "removed short %s chunk length %s below required %s"
            % (chunk_name, chunk.length, expected_length)
        ),
        chunk_name=chunk_name,
        chunk_offset=chunk.offset,
        old_length=chunk.length,
        new_length=0,
        removed=True,
    )


def repair_gifg_length(data: bytes) -> ChunkDataLengthRepair | None:
    return _repair_fixed_length_chunk(data, b"gIFg", 4)


def repair_offs_length(data: bytes) -> ChunkDataLengthRepair | None:
    try:
        chunks = list(iter_chunks(data))
    except PngFormatError:
        return None

    offs = next((chunk for chunk in chunks if chunk.chunk_type == b"oFFs"), None)
    if offs is None or offs.length == 9:
        return None

    if offs.length > 9:
        payload = offs.data[:9]
        strategy = "trimmed oFFs length from %s to 9 and rebuilt CRC" % offs.length
        new_length = 9
        removed = False
    elif offs.length == 8:
        payload = offs.data + b"\x00"
        strategy = "inferred missing oFFs unit byte 0 and rebuilt CRC"
        new_length = 9
        removed = False
    else:
        repaired = replace_png_chunk(data, offs, b"")
        if not is_complete_png_with_valid_crc(repaired):
            return None
        return ChunkDataLengthRepair(
            data=repaired,
            strategy="removed short oFFs chunk length %s below required 9" % offs.length,
            chunk_name="oFFs",
            chunk_offset=offs.offset,
            old_length=offs.length,
            new_length=0,
            removed=True,
        )

    repaired = replace_png_chunk(data, offs, build_png_chunk(b"oFFs", payload))
    if not validate_png_structure(repaired).ok:
        return None
    return ChunkDataLengthRepair(
        data=repaired,
        strategy=strategy,
        chunk_name="oFFs",
        chunk_offset=offs.offset,
        old_length=offs.length,
        new_length=new_length,
        removed=removed,
    )


def repair_phys_length(data: bytes) -> ChunkDataLengthRepair | None:
    try:
        chunks = list(iter_chunks(data))
    except PngFormatError:
        return None

    phys = next((chunk for chunk in chunks if chunk.chunk_type == b"pHYs"), None)
    if phys is None or phys.length == 9:
        return None

    if phys.length > 9:
        payload = phys.data[:9]
        strategy = "trimmed pHYs length from %s to 9 and rebuilt CRC" % phys.length
        new_length = 9
        removed = False
    elif phys.length == 8:
        payload = phys.data + b"\x00"
        strategy = "inferred missing pHYs unit byte 0 and rebuilt CRC"
        new_length = 9
        removed = False
    else:
        repaired = replace_png_chunk(data, phys, b"")
        if not is_complete_png_with_valid_crc(repaired):
            return None
        return ChunkDataLengthRepair(
            data=repaired,
            strategy="removed short pHYs chunk length %s below required 9" % phys.length,
            chunk_name="pHYs",
            chunk_offset=phys.offset,
            old_length=phys.length,
            new_length=0,
            removed=True,
        )

    repaired = replace_png_chunk(data, phys, build_png_chunk(b"pHYs", payload))
    if not validate_png_structure(repaired).ok:
        return None
    return ChunkDataLengthRepair(
        data=repaired,
        strategy=strategy,
        chunk_name="pHYs",
        chunk_offset=phys.offset,
        old_length=phys.length,
        new_length=new_length,
        removed=removed,
    )


def repair_sbit_length(data: bytes) -> ChunkDataLengthRepair | None:
    try:
        chunks = list(iter_chunks(data))
    except PngFormatError:
        return None

    ihdr = next((chunk for chunk in chunks if chunk.chunk_type == b"IHDR"), None)
    sbit = next((chunk for chunk in chunks if chunk.chunk_type == b"sBIT"), None)
    ihdr_values = _parse_ihdr_data(ihdr) if ihdr is not None else None
    if sbit is None or ihdr_values is None:
        return None

    color_type = ihdr_values[3]
    expected_length = _sbit_expected_length_for_color_type(color_type)
    if expected_length is None or sbit.length == expected_length:
        return None

    if sbit.length > expected_length:
        repaired_chunk = build_png_chunk(b"sBIT", sbit.data[:expected_length])
        repaired = replace_png_chunk(data, sbit, repaired_chunk)
        if not validate_png_structure(repaired).ok:
            return None
        return ChunkDataLengthRepair(
            data=repaired,
            strategy=(
                "trimmed sBIT length from %s to %s and rebuilt CRC"
                % (sbit.length, expected_length)
            ),
            chunk_name="sBIT",
            chunk_offset=sbit.offset,
            old_length=sbit.length,
            new_length=expected_length,
        )

    repaired = replace_png_chunk(data, sbit, b"")
    if not validate_png_structure(repaired).ok:
        return None
    return ChunkDataLengthRepair(
        data=repaired,
        strategy=(
            "removed short sBIT chunk length %s below required %s"
            % (sbit.length, expected_length)
        ),
        chunk_name="sBIT",
        chunk_offset=sbit.offset,
        old_length=sbit.length,
        new_length=0,
        removed=True,
    )


def repair_hist_length(data: bytes) -> ChunkDataLengthRepair | None:
    try:
        chunks = list(iter_chunks(data))
    except PngFormatError:
        return None

    hist = next((chunk for chunk in chunks if chunk.chunk_type == b"hIST"), None)
    if hist is None:
        return None

    plte = next((chunk for chunk in chunks if chunk.chunk_type == b"PLTE"), None)
    if plte is None:
        repaired = replace_png_chunk(data, hist, b"")
        if not is_complete_png_with_valid_crc(repaired):
            return None
        return ChunkDataLengthRepair(
            data=repaired,
            strategy="removed hIST chunk because no PLTE chunk is available",
            chunk_name="hIST",
            chunk_offset=hist.offset,
            old_length=hist.length,
            new_length=0,
            removed=True,
        )

    expected_length = (plte.length // 3) * 2
    if hist.length == expected_length and hist.length > 0 and hist.length % 2 == 0:
        return None

    if expected_length <= 0:
        repaired = replace_png_chunk(data, hist, b"")
        if not is_complete_png_with_valid_crc(repaired):
            return None
        return ChunkDataLengthRepair(
            data=repaired,
            strategy="removed hIST chunk because PLTE has no usable entries",
            chunk_name="hIST",
            chunk_offset=hist.offset,
            old_length=hist.length,
            new_length=0,
            removed=True,
        )

    if hist.length > expected_length:
        payload = hist.data[:expected_length]
        strategy = "trimmed hIST length from %s to %s and rebuilt CRC" % (
            hist.length,
            expected_length,
        )
    else:
        payload = hist.data + (b"\x00" * (expected_length - hist.length))
        strategy = "padded hIST length from %s to %s with zero frequencies and rebuilt CRC" % (
            hist.length,
            expected_length,
        )

    repaired_chunk = build_png_chunk(b"hIST", payload)
    repaired = replace_png_chunk(data, hist, repaired_chunk)
    if not is_complete_png_with_valid_crc(repaired):
        return None
    return ChunkDataLengthRepair(
        data=repaired,
        strategy=strategy,
        chunk_name="hIST",
        chunk_offset=hist.offset,
        old_length=hist.length,
        new_length=expected_length,
    )


def repair_iend_length(data: bytes) -> ChunkDataLengthRepair | None:
    try:
        chunks = list(iter_chunks(data))
    except PngFormatError:
        return None

    if not chunks:
        return None

    iend = chunks[-1]
    if iend.chunk_type != b"IEND" or iend.length == 0:
        return None

    repaired = data[: iend.offset] + IEND_CHUNK
    if not is_complete_png_with_valid_crc(repaired):
        return None
    return ChunkDataLengthRepair(
        data=repaired,
        strategy="rebuilt IEND with zero length and canonical CRC",
        chunk_name="IEND",
        chunk_offset=iend.offset,
        old_length=iend.length,
        new_length=0,
    )


def repair_chrm_length(data: bytes) -> ChrmRepair | None:
    try:
        chunks = list(iter_chunks(data))
    except PngFormatError:
        return None

    chrm = next((chunk for chunk in chunks if chunk.chunk_type == b"cHRM"), None)
    if chrm is None or chrm.length == 32:
        return None

    if chrm.length > 32:
        repaired_chunk = build_png_chunk(b"cHRM", chrm.data[:32])
        repaired = replace_png_chunk(data, chrm, repaired_chunk)
        if not is_complete_png_with_valid_crc(repaired):
            return None
        return ChrmRepair(
            data=repaired,
            strategy="trimmed cHRM length from %s to 32 and rebuilt CRC" % chrm.length,
            chunk_offset=chrm.offset,
            old_length=chrm.length,
            new_length=32,
        )

    removal = replace_png_chunk(data, chrm, b"")
    if not is_complete_png_with_valid_crc(removal):
        return None

    crc_payload, candidates_tested = _complete_short_chrm_payload_by_crc(chrm.data, chrm.crc)
    if crc_payload is not None:
        repaired_chunk = build_png_chunk(b"cHRM", crc_payload)
        repaired = replace_png_chunk(data, chrm, repaired_chunk)
        if is_complete_png_with_valid_crc(repaired):
            return ChrmRepair(
                data=repaired,
                strategy=(
                    "recovered %s missing cHRM byte(s) by stored CRC brute force"
                    % (32 - chrm.length)
                ),
                chunk_offset=chrm.offset,
                old_length=chrm.length,
                new_length=32,
                missing_bytes=32 - chrm.length,
                inferred_payload=crc_payload,
                removal_data=removal,
                preserved_crc=True,
                crc_bruteforce_attempted=True,
                crc_candidates_tested=candidates_tested,
            )

    inferred_payload = _complete_short_chrm_payload(chrm.data)
    if inferred_payload is not None:
        repaired_chunk = build_png_chunk(b"cHRM", inferred_payload)
        repaired = replace_png_chunk(data, chrm, repaired_chunk)
        if is_complete_png_with_valid_crc(repaired):
            return ChrmRepair(
                data=repaired,
                strategy=(
                    "inferred %s missing cHRM byte(s) and rebuilt CRC"
                    % (32 - chrm.length)
                ),
                chunk_offset=chrm.offset,
                old_length=chrm.length,
                new_length=32,
                missing_bytes=32 - chrm.length,
                inferred_payload=inferred_payload,
                removal_data=removal,
                crc_bruteforce_attempted=candidates_tested > 0,
                crc_candidates_tested=candidates_tested,
            )

    return ChrmRepair(
        data=removal,
        strategy="removed short cHRM chunk length %s below required 32" % chrm.length,
        chunk_offset=chrm.offset,
        old_length=chrm.length,
        new_length=0,
        removed=True,
        missing_bytes=32 - chrm.length,
        crc_bruteforce_attempted=candidates_tested > 0,
        crc_candidates_tested=candidates_tested,
    )


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


def repair_indexed_plte(data: bytes) -> PlteRepair | None:
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

    _width, _height, bit_depth, color_type, _method, _filter_method, _interlace = ihdr_values
    if color_type != 3 or bit_depth not in (1, 2, 4, 8):
        return None

    indices = indexed_png_indices(data)
    if indices is None:
        return None

    max_entries = 2 ** bit_depth
    required_entries = max(indices, default=0) + 1
    if required_entries > max_entries:
        return None

    plte = next((chunk for chunk in chunks if chunk.chunk_type == b"PLTE"), None)
    if plte is None:
        first_idat = next((chunk for chunk in chunks if chunk.chunk_type == b"IDAT"), None)
        palette = grayscale_palette(max_entries)
        if first_idat is None or palette is None:
            return None
        return PlteRepair(
            data=data[: first_idat.offset] + build_png_chunk(b"PLTE", palette) + data[first_idat.offset :],
            strategy="inserted missing indexed PLTE as grayscale palette",
        )

    if plte.length % 3 != 0:
        palette = grayscale_palette(max_entries)
        if palette is None:
            return None
        return PlteRepair(
            data=replace_png_chunk(data, plte, build_png_chunk(b"PLTE", palette)),
            strategy="rebuilt malformed indexed PLTE as grayscale palette",
        )

    entry_count = plte.length // 3
    if entry_count > max_entries:
        palette = plte.data[: max_entries * 3]
        return PlteRepair(
            data=replace_png_chunk(data, plte, build_png_chunk(b"PLTE", palette)),
            strategy="truncated indexed PLTE to bit depth entry count",
        )

    if entry_count < required_entries:
        palette = grayscale_palette(max_entries)
        if palette is None:
            return None
        return PlteRepair(
            data=replace_png_chunk(data, plte, build_png_chunk(b"PLTE", palette)),
            strategy="rebuilt undersized indexed PLTE as grayscale palette",
        )

    return None


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


def repair_itxt_compression_flag(data: bytes) -> ItxtRepair | None:
    try:
        chunks = list(iter_chunks(data))
    except PngFormatError:
        return None

    for chunk in chunks:
        if chunk.chunk_type != b"iTXt":
            continue

        try:
            keyword_end = chunk.data.index(0)
        except ValueError:
            continue

        flag_offset = keyword_end + 1
        if flag_offset >= len(chunk.data):
            continue

        new_flag = _itxt_best_repaired_compression_flag(chunk.data, flag_offset)
        if new_flag is None:
            continue

        repaired_payload = bytearray(chunk.data)
        old_flag = repaired_payload[flag_offset]
        repaired_payload[flag_offset] = new_flag
        repaired_chunk = build_png_chunk(b"iTXt", bytes(repaired_payload))
        repaired = replace_png_chunk(data, chunk, repaired_chunk)
        if not is_complete_png_with_valid_crc(repaired):
            continue

        return ItxtRepair(
            data=repaired,
            strategy=(
                "fixed iTXt compression flag 0x%02x to 0x%02x and rebuilt CRC"
                % (old_flag, new_flag)
            ),
            chunk_offset=chunk.offset,
            old_flag=old_flag,
            new_flag=new_flag,
        )

    return None


def repair_itxt_compression_method(data: bytes) -> ItxtRepair | None:
    try:
        chunks = list(iter_chunks(data))
    except PngFormatError:
        return None

    for chunk in chunks:
        if chunk.chunk_type != b"iTXt":
            continue

        method_offset = _itxt_compression_method_offset(chunk.data)
        if method_offset is None or chunk.data[method_offset] == 0:
            continue

        repaired_payload = bytearray(chunk.data)
        old_method = repaired_payload[method_offset]
        repaired_payload[method_offset] = 0
        repaired_chunk = build_png_chunk(b"iTXt", bytes(repaired_payload))
        repaired = replace_png_chunk(data, chunk, repaired_chunk)
        if not is_complete_png_with_valid_crc(repaired):
            continue

        return ItxtRepair(
            data=repaired,
            strategy=(
                "fixed iTXt compression method 0x%02x to 0x00 and rebuilt CRC"
                % old_method
            ),
            chunk_offset=chunk.offset,
            old_method=old_method,
            new_method=0,
        )

    return None


def repair_itxt_keyword_length(data: bytes) -> ItxtRepair | None:
    try:
        chunks = list(iter_chunks(data))
    except PngFormatError:
        return None

    for chunk in chunks:
        if chunk.chunk_type != b"iTXt":
            continue

        try:
            keyword_end = chunk.data.index(0)
        except ValueError:
            continue

        if 1 <= keyword_end <= 79:
            continue

        if keyword_end == 0:
            new_keyword = b"Comment"
        else:
            new_keyword = chunk.data[:79]

        repaired_payload = new_keyword + chunk.data[keyword_end:]
        repaired_chunk = build_png_chunk(b"iTXt", repaired_payload)
        repaired = replace_png_chunk(data, chunk, repaired_chunk)
        if not is_complete_png_with_valid_crc(repaired):
            continue

        return ItxtRepair(
            data=repaired,
            strategy=(
                "fixed iTXt keyword length %s to %s and rebuilt CRC"
                % (keyword_end, len(new_keyword))
            ),
            chunk_offset=chunk.offset,
            old_keyword_length=keyword_end,
            new_keyword=new_keyword,
        )

    return None


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

    if candidates and preferred is None and 0 < current_width <= 0x7FFFFFFF:
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


def repair_ihdr_length(data: bytes) -> IhdrRepair | None:
    signature_offset = find_signature_offset(data)
    if signature_offset < 0:
        return None

    ihdr = chunk_at(data, signature_offset + len(PNG_SIGNATURE))
    if ihdr is None or ihdr.chunk_type != b"IHDR" or ihdr.length == 13:
        return None
    if ihdr.length < 13:
        return None

    ihdr_data = ihdr.data[:13]
    if not png_chunk_data_is_coherent(b"IHDR", ihdr_data):
        return None

    fixed = replace_png_chunk(data, ihdr, build_png_chunk(b"IHDR", ihdr_data))
    validation = validate_png_structure(fixed)
    if not validation.ok:
        return None

    width, height, bit_depth, color_type, _method, _filter_method, _interlace = struct.unpack(
        "!IIBBBBB",
        ihdr_data,
    )
    return IhdrRepair(
        data=fixed,
        strategy="trimmed IHDR length from %s to 13 and rebuilt CRC" % ihdr.length,
        preserved_crc=False,
        width=width,
        height=height,
        bit_depth=bit_depth,
        color_type=color_type,
    )


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


def _has_plte_chunk(data: bytes) -> bool:
    try:
        return any(chunk.chunk_type == b"PLTE" for chunk in iter_chunks(data))
    except PngFormatError:
        return False


def _ihdr_rebuild_score(
    ihdr_data: bytes,
    *,
    has_plte: bool,
    current_bit_depth: int,
    current_color_type: int,
) -> tuple[int, ...]:
    width, height, bit_depth, color_type, _method, _filter_method, _interlace = struct.unpack(
        "!IIBBBBB",
        ihdr_data,
    )
    area = width * height
    aspect_penalty = abs(width - height)
    plte_coherent = (has_plte and color_type == 3) or (not has_plte and color_type != 3)
    preserves_color_type = color_type == current_color_type
    preserves_mode = bit_depth == current_bit_depth and color_type == current_color_type
    balanced = min(width, height) > 0 and _dimension_aspect_ratio((width, height)) <= 2

    return (
        int(plte_coherent),
        int(preserves_color_type),
        int(preserves_mode),
        int(balanced),
        area,
        -aspect_penalty,
    )


def _ihdr_repair_from_candidate(
    candidate: IhdrRebuildCandidate,
    *,
    strategy: str,
    candidate_count: int,
) -> IhdrRepair:
    return IhdrRepair(
        data=candidate.data,
        strategy=strategy,
        preserved_crc=False,
        width=candidate.width,
        height=candidate.height,
        bit_depth=candidate.bit_depth,
        color_type=candidate.color_type,
        strict_candidate_count=candidate_count,
        selection_score=candidate.score,
    )


def _rebuilt_ihdr_candidates(
    data: bytes,
    *,
    insert_offset: int | None,
    replace_ihdr: PngChunk | None,
    decompressed_size: int,
    current_width: int,
    current_height: int,
    current_bit_depth: int,
    current_color_type: int,
) -> list[IhdrRebuildCandidate]:
    has_plte = _has_plte_chunk(data)
    strict_candidates: list[IhdrRebuildCandidate] = []
    seen_candidates: set[bytes] = set()

    for fixed_ihdr_data in _ihdr_candidate_data_from_idat(
        decompressed_size,
        current_width,
        current_height,
        current_bit_depth,
        current_color_type,
    ):
        if fixed_ihdr_data in seen_candidates:
            continue
        seen_candidates.add(fixed_ihdr_data)

        replacement = build_png_chunk(b"IHDR", fixed_ihdr_data)
        if replace_ihdr is not None:
            fixed = replace_png_chunk(data, replace_ihdr, replacement)
            original_chunk = data[replace_ihdr.offset : replace_ihdr.offset + 12 + replace_ihdr.length]
            if replacement == original_chunk:
                continue
        elif insert_offset is not None:
            fixed = data[:insert_offset] + replacement + data[insert_offset:]
        else:
            continue

        if not validate_png_structure(fixed).ok:
            continue

        width, height, bit_depth, color_type, _method, _filter_method, _interlace = struct.unpack(
            "!IIBBBBB",
            fixed_ihdr_data,
        )
        score = _ihdr_rebuild_score(
            fixed_ihdr_data,
            has_plte=has_plte,
            current_bit_depth=current_bit_depth,
            current_color_type=current_color_type,
        )
        strict_candidates.append(
            IhdrRebuildCandidate(
                data=fixed,
                ihdr_data=fixed_ihdr_data,
                width=width,
                height=height,
                bit_depth=bit_depth,
                color_type=color_type,
                score=score,
            )
        )

    strict_candidates.sort(key=lambda candidate: candidate.score, reverse=True)
    return strict_candidates


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


def _best_rebuild_ihdr_candidate_from_idat(data: bytes) -> tuple[IhdrRebuildCandidate, int] | None:
    context = _ihdr_and_idat_data(data)
    if context is None:
        return None

    ihdr, idat_data = context
    width, height, bit_depth, color_type, method, filter_method, interlace = struct.unpack(
        "!IIBBBBB", ihdr.data
    )
    if interlace not in (0, 1):
        interlace = 0
    if interlace != 0:
        return None

    try:
        decompressed = zlib.decompress(idat_data)
    except zlib.error:
        return None

    strict_candidates = _rebuilt_ihdr_candidates(
        data,
        insert_offset=None,
        replace_ihdr=ihdr,
        decompressed_size=len(decompressed),
        current_width=width,
        current_height=height,
        current_bit_depth=bit_depth,
        current_color_type=color_type,
    )
    if not strict_candidates:
        return None

    return strict_candidates[0], len(strict_candidates)


def rebuild_ihdr_from_idat(data: bytes) -> bytes | None:
    candidate = _best_rebuild_ihdr_candidate_from_idat(data)
    if candidate is None:
        return None

    return candidate[0].data


def repair_ihdr(data: bytes) -> IhdrRepair | None:
    fixed_length = repair_ihdr_length(data)
    if fixed_length is not None:
        return fixed_length

    fixed = repair_ihdr_preserving_crc(data)
    if fixed is not None:
        return IhdrRepair(
            data=fixed,
            strategy="restored IHDR values matching stored CRC",
            preserved_crc=True,
        )

    rebuilt = _best_rebuild_ihdr_candidate_from_idat(data)
    if rebuilt is not None:
        candidate, candidate_count = rebuilt
        return _ihdr_repair_from_candidate(
            candidate,
            strategy="rebuilt IHDR from IDAT scanline size",
            candidate_count=candidate_count,
        )

    return None


def repair_ihdr_from_idat(data: bytes) -> bytes | None:
    result = repair_ihdr(data)
    if result is None:
        return None
    return result.data


def repair_missing_ihdr_from_idat(data: bytes) -> IhdrRepair | None:
    signature_offset = find_signature_offset(data)
    if signature_offset != 0:
        return None

    try:
        chunks = list(iter_chunks(data, signature_offset=0))
    except PngFormatError:
        return None

    if not chunks or chunks[0].chunk_type == b"IHDR":
        return None

    idat_data = b"".join(chunk.data for chunk in chunks if chunk.chunk_type == b"IDAT")
    if not idat_data:
        return None

    try:
        decompressed = zlib.decompress(idat_data)
    except zlib.error:
        return None

    preferred_color_type = 3 if any(chunk.chunk_type == b"PLTE" for chunk in chunks) else 2
    preferred_bit_depth = 8
    strict_candidates = _rebuilt_ihdr_candidates(
        data,
        insert_offset=len(PNG_SIGNATURE),
        replace_ihdr=None,
        decompressed_size=len(decompressed),
        current_width=0,
        current_height=0,
        current_bit_depth=preferred_bit_depth,
        current_color_type=preferred_color_type,
    )
    if not strict_candidates:
        return None

    return _ihdr_repair_from_candidate(
        strict_candidates[0],
        strategy="rebuilt missing IHDR from IDAT scanline size",
        candidate_count=len(strict_candidates),
    )
