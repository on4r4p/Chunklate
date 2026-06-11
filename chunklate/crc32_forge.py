from __future__ import annotations

from functools import lru_cache
import zlib


CRC32_POLY_REFLECTED = 0xEDB88320
CRC32_MASK = 0xFFFFFFFF
CRC32_FOUR_ZERO_BYTES = b"\x00\x00\x00\x00"


def _crc32_table() -> tuple[int, ...]:
    table: list[int] = []
    for value in range(256):
        crc = value
        for _bit in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ CRC32_POLY_REFLECTED
            else:
                crc >>= 1
        table.append(crc & CRC32_MASK)
    return tuple(table)


CRC32_TABLE = _crc32_table()


def _reverse_crc32_table() -> dict[int, int]:
    reverse: dict[int, int] = {}
    for index, value in enumerate(CRC32_TABLE):
        high = (value >> 24) & 0xFF
        if high in reverse:
            raise RuntimeError("CRC32 reverse table is ambiguous")
        reverse[high] = index
    if len(reverse) != 256:
        raise RuntimeError("CRC32 reverse table is incomplete")
    return reverse


CRC32_REVERSE_TABLE = _reverse_crc32_table()


def _reverse_crc32_byte_internal(next_crc: int, byte: int) -> int:
    table_index = CRC32_REVERSE_TABLE[(next_crc >> 24) & 0xFF]
    previous_high = (next_crc ^ CRC32_TABLE[table_index]) << 8
    previous_low = table_index ^ int(byte)
    return (previous_high | previous_low) & CRC32_MASK


def _reverse_crc32_byte(next_crc: int, byte: int) -> int:
    internal = _reverse_crc32_byte_internal(int(next_crc) ^ CRC32_MASK, int(byte))
    return internal ^ CRC32_MASK


def crc32_prefixes(chunk_type: bytes, payload: bytes) -> tuple[int, ...]:
    """Return visible zlib.crc32 states before each payload suffix."""

    crc = zlib.crc32(bytes(chunk_type)) & CRC32_MASK
    prefixes = [crc]
    for value in bytes(payload):
        crc = zlib.crc32(bytes((value,)), crc) & CRC32_MASK
        prefixes.append(crc)
    return tuple(prefixes)


def crc32_required_before_suffixes(payload: bytes, target_crc: int) -> tuple[int, ...]:
    """Return CRC states that become target_crc after payload[index:] is appended."""

    required = [0] * (len(payload) + 1)
    crc = int(target_crc) & CRC32_MASK
    required[len(payload)] = crc
    for index in range(len(payload) - 1, -1, -1):
        crc = _reverse_crc32_byte(crc, payload[index])
        required[index] = crc
    return tuple(required)


def _patch_delta_columns(byte_count: int) -> tuple[int, ...]:
    byte_count = int(byte_count)
    zero = zlib.crc32(b"\x00" * byte_count, 0) & CRC32_MASK
    columns: list[int] = []
    for bit in range(8 * byte_count):
        patch = (1 << bit).to_bytes(byte_count, "little")
        columns.append((zlib.crc32(patch, 0) & CRC32_MASK) ^ zero)
    return tuple(columns)


@lru_cache(maxsize=None)
def _patch_solver_basis(byte_count: int) -> tuple[tuple[int, int] | None, ...]:
    byte_count = int(byte_count)
    basis: list[tuple[int, int] | None] = [None] * 32
    for bit, column in enumerate(_patch_delta_columns(byte_count)):
        vector = column
        coeff = 1 << bit
        while vector:
            pivot = vector.bit_length() - 1
            existing = basis[pivot]
            if existing is None:
                basis[pivot] = (vector, coeff)
                break
            vector ^= existing[0]
            coeff ^= existing[1]
    if byte_count == 4 and any(item is None for item in basis):
        raise RuntimeError("CRC32 patch matrix is not invertible")
    return tuple(basis)


def _solve_patch_delta(delta: int, byte_count: int) -> int:
    vector = int(delta) & CRC32_MASK
    coeff = 0
    basis = _patch_solver_basis(int(byte_count))
    for bit in range(31, -1, -1):
        if not (vector & (1 << bit)):
            continue
        item = basis[bit]
        if item is None:
            raise ValueError("CRC32 patch delta is not representable")
        basis_vector, basis_coeff = item
        vector ^= basis_vector
        coeff ^= basis_coeff
    if vector:
        raise ValueError("CRC32 patch delta is not representable")
    return coeff & ((1 << (8 * int(byte_count))) - 1)


@lru_cache(maxsize=1)
def _patch_delta_4byte_solution_tables() -> tuple[tuple[int, ...], ...]:
    bit_solutions = tuple(_solve_patch_delta(1 << bit, 4) for bit in range(32))
    tables: list[tuple[int, ...]] = []
    for byte_index in range(4):
        table: list[int] = []
        bit_offset = byte_index * 8
        for value in range(256):
            coeff = 0
            for bit in range(8):
                if value & (1 << bit):
                    coeff ^= bit_solutions[bit_offset + bit]
            table.append(coeff & CRC32_MASK)
        tables.append(tuple(table))
    return tuple(tables)


def _solve_patch_delta_4byte_fast(delta: int) -> int:
    delta = int(delta) & CRC32_MASK
    tables = _patch_delta_4byte_solution_tables()
    return (
        tables[0][delta & 0xFF]
        ^ tables[1][(delta >> 8) & 0xFF]
        ^ tables[2][(delta >> 16) & 0xFF]
        ^ tables[3][(delta >> 24) & 0xFF]
    ) & CRC32_MASK


def solve_crc32_nbyte_transition(start_crc: int, end_crc: int, byte_count: int) -> bytes | None:
    """Return a byte_count patch if that short CRC transition is representable."""

    byte_count = int(byte_count)
    if byte_count <= 0:
        return b"" if (int(start_crc) & CRC32_MASK) == (int(end_crc) & CRC32_MASK) else None
    if byte_count > 4:
        raise ValueError("CRC32 short transition solver supports at most 4 bytes")
    start_crc = int(start_crc) & CRC32_MASK
    end_crc = int(end_crc) & CRC32_MASK
    zero_end = zlib.crc32(b"\x00" * byte_count, start_crc) & CRC32_MASK
    try:
        patch_value = _solve_patch_delta(end_crc ^ zero_end, byte_count)
    except ValueError:
        return None
    patch = patch_value.to_bytes(byte_count, "little")
    if zlib.crc32(patch, start_crc) & CRC32_MASK != end_crc:
        return None
    return patch


def forge_crc32_4byte_transition(start_crc: int, end_crc: int) -> bytes:
    """Return 4 bytes that transform visible CRC start_crc into end_crc."""

    start_crc = int(start_crc) & CRC32_MASK
    end_crc = int(end_crc) & CRC32_MASK
    zero_end = zlib.crc32(CRC32_FOUR_ZERO_BYTES, start_crc) & CRC32_MASK
    patch_value = _solve_patch_delta_4byte_fast(end_crc ^ zero_end)
    return patch_value.to_bytes(4, "little")
