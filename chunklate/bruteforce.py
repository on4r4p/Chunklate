from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Mapping


CUSTOM_TO_BRUTUS_NOTE = "-SmashBruteBrawl error: Sti empty switched to Brutus mode"


@dataclass(frozen=True)
class BruteForceModePlan:
    mode: str
    struct_indexes: tuple[int, ...] = ()
    side_note: str | None = None


@dataclass(frozen=True)
class BruteForceLengthRange:
    min_length: int
    max_length: int
    step: int


@dataclass(frozen=True)
class BruteForceEditWindow:
    before: bytes
    to_brute: str
    to_bryte: bytes
    after: bytes
    length_bytes: bytes | None = None
    replace_flag: bool = False
    insert_flag: bool = False


def normalize_old_crc(old_crc: Any) -> Any:
    if old_crc:
        try:
            return bytes.fromhex(old_crc)
        except TypeError:
            return old_crc
    return old_crc


def custom_struct_indexes(pandora_box: Mapping[Any, Any], chunk_name: bytes) -> tuple[int, ...]:
    chunk_label = chunk_name.decode()
    return tuple(
        sorted(
            set(
                int(str(key).split("StructIndex:")[1])
                for key in pandora_box
                if chunk_label in str(key) and "StructIndex:" in str(key)
            )
        )
    )


def resolve_mode(mode: str, chunk_name: bytes, pandora_box: Mapping[Any, Any]) -> BruteForceModePlan:
    if mode != "Custom":
        return BruteForceModePlan(mode)

    struct_indexes = custom_struct_indexes(pandora_box, chunk_name)
    if struct_indexes:
        return BruteForceModePlan(mode, struct_indexes)

    return BruteForceModePlan("Brutus", (), CUSTOM_TO_BRUTUS_NOTE)


def length_range(chunk_length_spec: int | tuple[int, int]) -> BruteForceLengthRange:
    if type(chunk_length_spec) == tuple:
        max_length = max(chunk_length_spec)
        min_length = min(chunk_length_spec)
    else:
        max_length = chunk_length_spec
        min_length = chunk_length_spec

    if max_length == min_length:
        return BruteForceLengthRange(min_length, max_length + 1, 1)

    return BruteForceLengthRange(min_length, max_length, min_length)


def iter_nbr_for_length(length: int, step: int, loop_index: int) -> int | None:
    if length > step:
        return loop_index + 1
    return None


def build_full_new_data(
    chunk_name: bytes,
    length_bytes: bytes,
    brute_bytes: bytes,
    checksum: bytes,
    *,
    brute_length: bool,
    brute_crc: bool,
    old_crc: Any,
) -> bytes:
    if old_crc:
        if brute_length and brute_crc:
            return length_bytes + chunk_name + brute_bytes + checksum
        if not brute_length and brute_crc:
            return brute_bytes + checksum
        if not brute_crc and brute_length:
            return length_bytes + chunk_name + brute_bytes
        return chunk_name + brute_bytes

    if brute_length and brute_crc:
        return length_bytes + chunk_name + brute_bytes + checksum
    if not brute_length and brute_crc:
        return chunk_name + brute_bytes + checksum
    if not brute_crc and brute_length:
        return length_bytes + chunk_name + brute_bytes
    return chunk_name + brute_bytes


def edit_window(
    data_hex: str,
    data_offset: int,
    chunk_length: int,
    edit_mode: str,
    bf_mode: str,
    length: int,
) -> BruteForceEditWindow:
    if bf_mode == "TwoBytes":
        to_brute = data_hex[data_offset : data_offset + chunk_length * 2]
        return BruteForceEditWindow(
            before=bytes.fromhex(data_hex[:data_offset]),
            to_brute=to_brute,
            to_bryte=bytes.fromhex(to_brute),
            after=bytes.fromhex(data_hex[data_offset + chunk_length * 2 + 8 :]),
        )

    if edit_mode == "Replace":
        to_brute = data_hex[data_offset + 16 : data_offset + 16 + length]
        return BruteForceEditWindow(
            before=bytes.fromhex(data_hex[:data_offset]),
            to_brute=to_brute,
            to_bryte=bytes.fromhex(to_brute),
            after=bytes.fromhex(data_hex[data_offset + length + 24 :]),
            length_bytes=int(int(length / 2)).to_bytes(4, "big"),
            replace_flag=True,
        )

    if edit_mode == "Insert":
        to_brute = ""
        return BruteForceEditWindow(
            before=bytes.fromhex(data_hex[:data_offset]),
            to_brute=to_brute,
            to_bryte=bytes.fromhex(to_brute),
            after=bytes.fromhex(data_hex[data_offset + 24 :]),
            length_bytes=int(int(length / 2)).to_bytes(4, "big"),
            insert_flag=True,
        )

    raise ValueError("Unknown SmashBruteBrawl edit mode: %s" % edit_mode)
