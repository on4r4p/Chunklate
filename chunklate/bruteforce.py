from __future__ import annotations

import binascii
import struct
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


@dataclass(frozen=True)
class TwoBytesCandidateData:
    data: bytes
    bonus_hex: str
    length_bytes: bytes


@dataclass(frozen=True)
class BruteForceCandidateAttempt:
    checksum: bytes
    full_new_data: bytes
    png_bytes: bytes
    old_crc_match: bool = False


@dataclass(frozen=True)
class BruteForceMatchState:
    bingo: bool = False
    replace_flag: bool = False
    insert_flag: bool = False
    remove_flag: bool = False
    bonus: bool = False


@dataclass(frozen=True)
class BruteForceAppliedAttempt:
    state: BruteForceMatchState
    full_new_data: bytes
    png_bytes: bytes


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


def chunk_crc(chunk_name: bytes, chunk_data: bytes) -> bytes:
    return struct.pack("!I", binascii.crc32(chunk_name + chunk_data))


def assemble_candidate_png(before: bytes, full_new_data: bytes, after: bytes) -> bytes:
    return before + full_new_data + after


def prepare_candidate_attempt(
    chunk_name: bytes,
    length_bytes: bytes,
    payload_data: bytes,
    crc_data: bytes,
    before: bytes,
    after: bytes,
    *,
    brute_length: bool,
    brute_crc: bool,
    old_crc: Any,
) -> BruteForceCandidateAttempt:
    checksum = chunk_crc(chunk_name, crc_data)
    full_new_data = build_full_new_data(
        chunk_name,
        length_bytes,
        payload_data,
        checksum,
        brute_length=brute_length,
        brute_crc=brute_crc,
        old_crc=old_crc,
    )
    png_bytes = assemble_candidate_png(before, full_new_data, after)

    return BruteForceCandidateAttempt(
        checksum=checksum,
        full_new_data=full_new_data,
        png_bytes=png_bytes,
        old_crc_match=bool(old_crc and checksum == old_crc),
    )


def match_state_from_edit_window(edit_window: BruteForceEditWindow) -> BruteForceMatchState:
    return BruteForceMatchState(
        replace_flag=edit_window.replace_flag,
        insert_flag=edit_window.insert_flag,
    )


def mark_candidate_match(
    state: BruteForceMatchState,
    edit_kind: str | None = None,
    *,
    bonus: bool = False,
) -> BruteForceMatchState:
    if edit_kind not in (None, "replace", "insert", "remove"):
        raise ValueError("Unknown candidate match edit kind: %s" % edit_kind)

    return BruteForceMatchState(
        bingo=True,
        replace_flag=state.replace_flag or edit_kind == "replace",
        insert_flag=state.insert_flag or edit_kind == "insert",
        remove_flag=state.remove_flag or edit_kind == "remove",
        bonus=state.bonus or bonus,
    )


def apply_candidate_attempt_match(
    state: BruteForceMatchState,
    attempt: BruteForceCandidateAttempt,
    edit_kind: str | None = None,
    *,
    bonus: bool = False,
) -> BruteForceAppliedAttempt:
    return BruteForceAppliedAttempt(
        state=mark_candidate_match(state, edit_kind, bonus=bonus),
        full_new_data=attempt.full_new_data,
        png_bytes=attempt.png_bytes,
    )


def twobytes_candidate_data(
    to_brute: str,
    brute_bytes: bytes,
    needle: int,
    edit_kind: str,
) -> TwoBytesCandidateData:
    brute_hex = brute_bytes.hex()
    needle2 = len(brute_hex)

    if edit_kind == "replace":
        data = bytes.fromhex(to_brute[:needle]) + brute_bytes + bytes.fromhex(to_brute[needle + needle2 :])
        bonus_hex = to_brute[:needle] + brute_hex + to_brute[needle + needle2 :]
    elif edit_kind == "insert":
        data = bytes.fromhex(to_brute[:needle]) + brute_bytes + bytes.fromhex(to_brute[needle:])
        bonus_hex = to_brute[:needle] + brute_hex + to_brute[needle:]
    elif edit_kind == "remove":
        data = bytes.fromhex(to_brute[:needle]) + brute_bytes + bytes.fromhex(to_brute[needle + needle2 + 2 :])
        bonus_hex = to_brute[:needle] + brute_hex + to_brute[needle + needle2 + 2 :]
    else:
        raise ValueError("Unknown TwoBytes edit kind: %s" % edit_kind)

    return TwoBytesCandidateData(
        data=data,
        bonus_hex=bonus_hex,
        length_bytes=len(data).to_bytes(4, "big"),
    )


def twobytes_bonus_candidate_data(
    bonus_hex: str,
    hex_offset: int,
    replacement_byte: bytes,
) -> bytes:
    return bytes.fromhex(bonus_hex[:hex_offset]) + replacement_byte + bytes.fromhex(bonus_hex[hex_offset + 2 :])


def iter_twobytes_bonus_data(
    bonus_hex: str,
    new_data_len: int,
    skipped_hex_offset: int,
    skipped_hex_len: int,
):
    n1 = 0
    n2 = 2
    while n1 <= new_data_len - (n2 - 1):
        if n1 == skipped_hex_offset:
            n1 += skipped_hex_len
            continue

        for hexa in range(0, 16**2):
            bonus_byte = int(hexa).to_bytes(1, "big")
            yield twobytes_bonus_candidate_data(bonus_hex, n1, bonus_byte)

        n1 += 2


def build_candidate_bytes(
    candidate: Any,
    chunk_format: list[str] | tuple[str, ...],
    bf_mode: str,
    *,
    struct_indexes: tuple[int, ...] = (),
    to_bryte: bytes = b"",
) -> bytes:
    if bf_mode == "Custom":
        frm = "!" + "".join(chunk_format).replace("!", "")
        unpacked_to_brute = struct.unpack(frm, to_bryte)
        brute_bytes = b""
        for enum, (unpacked_value, chunk_field_format) in enumerate(zip(unpacked_to_brute, chunk_format)):
            if enum in struct_indexes:
                for struct_index in struct_indexes:
                    if struct_index == enum:
                        try:
                            replacement = int(candidate[struct_indexes.index(struct_index)])
                        except TypeError:
                            replacement = int(candidate)
                        brute_bytes += struct.pack(chunk_field_format, replacement)
                        break
            else:
                brute_bytes += struct.pack(chunk_field_format, unpacked_value)
        return brute_bytes

    brute_bytes = b""
    format_index = 0
    last_format_index = len(chunk_format) - 1
    for value in candidate:
        brute_bytes += struct.pack(chunk_format[format_index], int(value))
        if format_index < last_format_index:
            format_index += 1
        else:
            format_index = 0
    return brute_bytes


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
