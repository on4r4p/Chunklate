from __future__ import annotations

import binascii
import struct
from typing import Any
from typing import Iterable


EMPTY_PALETTE_ENTRY = "empty"


def palette_values_to_bytes(values: Iterable[Any]) -> bytes:
    palette_data = b""
    for value in values:
        if value != EMPTY_PALETTE_ENTRY:
            palette_data += int(value).to_bytes(3, "big")
    return palette_data


def build_plte_chunk(palette_data: bytes) -> bytes:
    length = len(palette_data).to_bytes(4, "big")
    checksum = struct.pack("!I", binascii.crc32(b"PLTE" + palette_data))
    return length + b"PLTE" + palette_data + checksum


def build_palette_png(before: bytes, palette_values: Iterable[Any], after: bytes) -> bytes:
    return before + build_plte_chunk(palette_values_to_bytes(palette_values)) + after


def set_palette_value(values: list[Any], index: int, raw_value: Any) -> None:
    if raw_value == "-1":
        values[index] = EMPTY_PALETTE_ENTRY
    else:
        values[index] = raw_value


def legacy_palette_count(values: Iterable[Any]) -> int:
    return 256 - list(values).count(EMPTY_PALETTE_ENTRY)


def initial_manual_palette_png(before: bytes, chunk_name: bytes, after: bytes) -> bytes:
    palette_data = bytes.fromhex("000000")
    length = int(3).to_bytes(4, "big")
    checksum = struct.pack("!I", binascii.crc32(chunk_name + palette_data))
    return before + length + chunk_name + palette_data + checksum + after
