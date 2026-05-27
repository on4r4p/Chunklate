from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .png import IEND_CHUNK, PNG_SIGNATURE


IDAT = b"IDAT"
IEND = b"IEND"
PNG_IEND_CRC = IEND_CHUNK[-4:]


@dataclass(frozen=True)
class IdatHeaderPatch:
    header_offset: int
    old_length: int
    new_length: int
    old_type: bytes
    new_type: bytes = IDAT

    @property
    def changed(self) -> bool:
        return self.old_length != self.new_length or self.old_type != self.new_type


@dataclass(frozen=True)
class IdatChainAnalysis:
    status: str
    patches: tuple[IdatHeaderPatch, ...] = ()
    idat_count: int = 0
    iend_offset: int | None = None
    expected_length: int | None = None
    fixed_data: bytes | None = None
    reason: str = ""

    @property
    def repairable(self) -> bool:
        return self.status == "repairable" and bool(self.patches) and self.fixed_data is not None


def _chunk_length(data: bytes, header_offset: int) -> int:
    return int.from_bytes(data[header_offset : header_offset + 4], "big")


def _chunk_type(data: bytes, header_offset: int) -> bytes:
    return data[header_offset + 4 : header_offset + 8]


def _one_byte_apart(left: bytes, right: bytes) -> bool:
    return len(left) == len(right) and sum(a != b for a, b in zip(left, right)) <= 1


def _looks_like_idat(chunk_type: bytes) -> bool:
    return _one_byte_apart(chunk_type, IDAT)


def _first_idat_header(data: bytes) -> int | None:
    if not data.startswith(PNG_SIGNATURE):
        return None

    offset = len(PNG_SIGNATURE)
    while offset + 8 <= len(data):
        chunk_length = _chunk_length(data, offset)
        chunk_type = _chunk_type(data, offset)
        if chunk_type == IDAT:
            return offset
        next_offset = offset + 12 + chunk_length
        if next_offset <= offset or next_offset > len(data):
            return None
        offset = next_offset
    return None


def _dominant_initial_idat_length(data: bytes, first_idat: int) -> tuple[int | None, int]:
    lengths: list[int] = []
    offset = first_idat
    while offset + 8 <= len(data):
        chunk_length = _chunk_length(data, offset)
        chunk_type = _chunk_type(data, offset)
        if chunk_type != IDAT:
            break
        if chunk_length <= 0 or offset + 12 + chunk_length > len(data):
            break
        lengths.append(chunk_length)
        offset += 12 + chunk_length

    if not lengths:
        return None, 0

    expected, _count = Counter(lengths).most_common(1)[0]
    return expected, len(lengths)


def _valid_iend_header(data: bytes, header_offset: int) -> bool:
    return (
        header_offset >= len(PNG_SIGNATURE)
        and header_offset + len(IEND_CHUNK) <= len(data)
        and data[header_offset : header_offset + 4] == b"\x00\x00\x00\x00"
        and data[header_offset + 4 : header_offset + 8] == IEND
        and data[header_offset + 8 : header_offset + 12] == PNG_IEND_CRC
    )


def _candidate_iend_headers(data: bytes, first_idat: int) -> tuple[int, ...]:
    headers: list[int] = []
    start = first_idat
    while True:
        type_offset = data.find(IEND, start)
        if type_offset < 0:
            break
        header_offset = type_offset - 4
        if _valid_iend_header(data, header_offset):
            headers.append(header_offset)
        start = type_offset + 1
    return tuple(headers)


def _build_patches_to_iend(
    data: bytes,
    *,
    first_idat: int,
    expected_length: int,
    iend_offset: int,
) -> tuple[IdatHeaderPatch, ...] | None:
    patches: list[IdatHeaderPatch] = []
    offset = first_idat

    while offset < iend_offset:
        if offset + 8 > len(data):
            return None

        old_length = _chunk_length(data, offset)
        old_type = _chunk_type(data, offset)
        if not _looks_like_idat(old_type):
            return None

        new_length = expected_length
        full_end = offset + 12 + expected_length
        if full_end > iend_offset:
            new_length = iend_offset - offset - 12
            if new_length < 0:
                return None

        old_length_bytes = old_length.to_bytes(4, "big", signed=False)
        new_length_bytes = new_length.to_bytes(4, "big", signed=False)
        if old_length != new_length and not _one_byte_apart(old_length_bytes, new_length_bytes):
            return None

        patch = IdatHeaderPatch(
            header_offset=offset,
            old_length=old_length,
            new_length=new_length,
            old_type=old_type,
        )
        if patch.changed:
            patches.append(patch)

        offset += 12 + new_length

    if offset != iend_offset:
        return None

    return tuple(patches)


def apply_idat_chain_patches(data: bytes, patches: tuple[IdatHeaderPatch, ...]) -> bytes:
    fixed = bytearray(data)
    for patch in patches:
        fixed[patch.header_offset : patch.header_offset + 4] = patch.new_length.to_bytes(4, "big")
        fixed[patch.header_offset + 4 : patch.header_offset + 8] = patch.new_type
    return bytes(fixed)


def analyze_idat_chain_headers(data: bytes) -> IdatChainAnalysis:
    first_idat = _first_idat_header(data)
    if first_idat is None:
        return IdatChainAnalysis("unsupported", reason="first IDAT chunk was not found")

    expected_length, initial_count = _dominant_initial_idat_length(data, first_idat)
    if expected_length is None or initial_count < 2:
        return IdatChainAnalysis("unsupported", reason="not enough aligned IDAT chunks")

    iend_headers = _candidate_iend_headers(data, first_idat)
    if not iend_headers:
        return IdatChainAnalysis(
            "candidate_without_iend",
            idat_count=initial_count,
            expected_length=expected_length,
            reason="IDAT chain exists but no reliable IEND was found",
        )

    for iend_offset in reversed(iend_headers):
        patches = _build_patches_to_iend(
            data,
            first_idat=first_idat,
            expected_length=expected_length,
            iend_offset=iend_offset,
        )
        if patches is None:
            continue

        idat_count = (iend_offset - first_idat) // (expected_length + 12)
        if (iend_offset - first_idat) % (expected_length + 12):
            idat_count += 1

        if not patches:
            return IdatChainAnalysis(
                "ok",
                idat_count=idat_count,
                iend_offset=iend_offset,
                expected_length=expected_length,
                reason="IDAT chain already reaches IEND",
            )

        fixed_data = apply_idat_chain_patches(data, patches)
        return IdatChainAnalysis(
            "repairable",
            patches=patches,
            idat_count=idat_count,
            iend_offset=iend_offset,
            expected_length=expected_length,
            fixed_data=fixed_data,
            reason="IDAT chain headers can be realigned before IEND",
        )

    return IdatChainAnalysis(
        "unsupported",
        idat_count=initial_count,
        expected_length=expected_length,
        reason="IDAT chain did not line up with a reliable IEND",
    )


def chunk_type_label(chunk_type: bytes) -> str:
    try:
        return chunk_type.decode("ascii")
    except UnicodeDecodeError:
        return repr(chunk_type)


def patch_summary_lines(patches: tuple[IdatHeaderPatch, ...]) -> tuple[str, ...]:
    lines = []
    for patch in patches:
        lines.append(
            "-Patched IDAT header at 0x%x: length %08x -> %08x, type %s -> IDAT."
            % (
                patch.header_offset,
                patch.old_length,
                patch.new_length,
                chunk_type_label(patch.old_type),
            )
        )
    return tuple(lines)
