from __future__ import annotations

import binascii
import difflib
import struct
from dataclasses import dataclass
from typing import Any
from typing import Mapping


CUSTOM_TO_BRUTUS_NOTE = "-SmashBruteBrawl error: Sti empty switched to Brutus mode"
BRUTE_FORCE_BONUS_NOTE = "-At least 2 bytes has been corrupted."
BRUTE_FORCE_FAILURE_NOTE = "\n-Launched Data Chunk Bruteforcer.\n-Bruteforce has Failed!"
TWOBYTES_EDIT_KIND_BY_MODE = {
    "Replace": "replace",
    "Insert": "insert",
    "Remove": "remove",
}


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
class BruteForceSpecRequest:
    mode: str
    fields: tuple[str, ...] = ()
    struct_indexes: tuple[int, ...] = ()
    iter_nbr: int | None = None


@dataclass(frozen=True)
class BruteForceCrashDecision:
    skip: bool
    crash_value: Any


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


@dataclass(frozen=True)
class BruteForceRepairMessage:
    line_template: str
    side_note: str


@dataclass(frozen=True)
class BruteForceCheckpointRequest:
    error: bool
    fixed: bool
    function: str
    chunk: str
    infos: tuple[str, ...]
    toolkit: tuple[Any, ...]

    def as_args(self) -> tuple[Any, ...]:
        return (
            self.error,
            self.fixed,
            self.function,
            self.chunk,
            list(self.infos),
            *self.toolkit,
        )


@dataclass(frozen=True)
class BruteForceViewerWaitState:
    found: bool
    count: int
    done: bool


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


def crash_iteration_decision(loop_index: int, crash_value: Any) -> BruteForceCrashDecision:
    if crash_value:
        if loop_index < crash_value:
            return BruteForceCrashDecision(True, crash_value)
        return BruteForceCrashDecision(False, False)
    return BruteForceCrashDecision(False, crash_value)


def eta_seconds_after_sample(elapsed: Any, max_iter: int, sample_count: int = 10) -> int:
    if elapsed.seconds != 0:
        return int((elapsed.seconds * max_iter) / sample_count)

    eta = (elapsed * max_iter) / sample_count
    return eta.seconds


def spec_request(
    mode: str,
    struct_indexes: tuple[int, ...] | list[int] = (),
    *,
    fields: tuple[str, ...] | list[str] = (),
    iter_nbr: int | None = None,
) -> BruteForceSpecRequest:
    request_struct_indexes = tuple(struct_indexes) if mode == "Custom" else ()
    return BruteForceSpecRequest(
        mode=mode,
        fields=tuple(fields),
        struct_indexes=request_struct_indexes,
        iter_nbr=iter_nbr,
    )


def initial_spec_request(mode: str, struct_indexes: tuple[int, ...] | list[int] = ()) -> BruteForceSpecRequest:
    if mode == "Custom":
        return spec_request(mode, struct_indexes)
    return spec_request(mode, fields=("Length", "Format"))


def iteration_spec_request(
    mode: str,
    struct_indexes: tuple[int, ...] | list[int] = (),
    iter_nbr: int | None = None,
) -> BruteForceSpecRequest:
    return spec_request(mode, struct_indexes, iter_nbr=iter_nbr)


def spec_request_kwargs(request: BruteForceSpecRequest) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    if request.fields:
        kwargs["Fields"] = list(request.fields)
    if request.struct_indexes:
        kwargs["StructIndex"] = list(request.struct_indexes)
    if request.iter_nbr is not None:
        kwargs["IterNbr"] = request.iter_nbr
    return kwargs


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


def apply_validated_candidate_attempt(
    state: BruteForceMatchState,
    attempt: BruteForceCandidateAttempt,
    edit_kind: str | None = None,
    *,
    bonus: bool = False,
    old_crc: Any = False,
    viewer_ok: bool = True,
) -> BruteForceAppliedAttempt | None:
    if old_crc:
        if not attempt.old_crc_match:
            return None
    elif not viewer_ok:
        return None

    return apply_candidate_attempt_match(
        state,
        attempt,
        edit_kind,
        bonus=bonus,
    )


def success_repair_messages(
    state: BruteForceMatchState,
    chunk_name: Any,
    diff: str,
) -> tuple[BruteForceRepairMessage, ...]:
    messages: list[BruteForceRepairMessage] = []

    if state.replace_flag:
        messages.append(
            BruteForceRepairMessage(
                line_template="-Chunk %s has been repaired by changing those bytes:\n",
                side_note=(
                    "\n-Launched Data Chunk Bruteforcer.\n-Bruteforce was successfull."
                    "\n-Chunk %s has been repaired by changing those bytes:\n%s"
                    % (chunk_name, diff)
                ),
            )
        )

    if state.insert_flag:
        messages.append(
            BruteForceRepairMessage(
                line_template="-Chunk %s has been repaired by adding those bytes:\n",
                side_note=(
                    "\n-Launched Data Chunk Bruteforcer.\n-Bruteforce was successfull."
                    "\n-Chunk %s has been repaired by adding those bytes:\n%s"
                    % (chunk_name, diff)
                ),
            )
        )

    if state.remove_flag:
        messages.append(
            BruteForceRepairMessage(
                line_template="-Chunk %s has been repaired by removing those bytes:\n",
                side_note=(
                    "\n-Launched Data Chunk Bruteforcer.\n-Bruteforce was successfull."
                    "\n-Chunk %s has been repaired by removing those bytes:\n%s"
                    % (chunk_name, diff)
                ),
            )
        )

    return tuple(messages)


def checkpoint_chunk_label(chunk_name: Any) -> str:
    if isinstance(chunk_name, bytes):
        return chunk_name.decode(errors="ignore")
    return str(chunk_name)


def success_checkpoint_request(
    *,
    old_crc: Any,
    chunk_name: Any,
    full_new_data_hex: str,
    png_bytes_hex: str,
    data_offset: int,
    chunk_length: int,
    to_brute: str,
    from_error: Any,
) -> BruteForceCheckpointRequest:
    chunk_label = checkpoint_chunk_label(chunk_name)
    replacement_summary = "-Replacing Corrupted %s Data:\n%s\n-With:\n%s" % (
        chunk_label,
        to_brute,
        full_new_data_hex,
    )

    if old_crc:
        return BruteForceCheckpointRequest(
            error=True,
            fixed=True,
            function="SmashBruteBrawl",
            chunk=chunk_label,
            infos=("-Previous Crc checksum found by replacing datas",),
            toolkit=(
                full_new_data_hex,
                data_offset,
                data_offset + len(full_new_data_hex),
                replacement_summary,
                chunk_label,
                from_error,
            ),
        )

    return BruteForceCheckpointRequest(
        error=True,
        fixed=True,
        function="SmashBruteBrawl",
        chunk=chunk_label,
        infos=("-Corrupted Data has been replaced",),
        toolkit=(
            png_bytes_hex,
            data_offset,
            data_offset + chunk_length,
            replacement_summary,
            chunk_label,
            from_error,
        ),
    )


def failure_checkpoint_request(
    *,
    old_crc: Any,
    file: Any,
    chunk_name: Any,
    chunk_length: int,
    data_offset: int,
    edit_mode: str,
    bf_mode: str,
    brute_crc: bool,
    brute_length: bool,
    from_error: Any,
) -> BruteForceCheckpointRequest:
    chunk_label = checkpoint_chunk_label(chunk_name)

    if old_crc:
        return BruteForceCheckpointRequest(
            error=True,
            fixed=False,
            function="SmashBruteBrawl",
            chunk=chunk_label,
            infos=("-Bruteforcer has Failed OldCrc",),
            toolkit=(
                file,
                chunk_name,
                chunk_length,
                data_offset,
                edit_mode,
                bf_mode,
                brute_crc,
                brute_length,
                old_crc,
                from_error,
            ),
        )

    return BruteForceCheckpointRequest(
        error=True,
        fixed=False,
        function="SmashBruteBrawl",
        chunk=chunk_label,
        infos=("-Bruteforcer has Failed",),
        toolkit=(
            file,
            chunk_name,
            chunk_length,
            data_offset,
            edit_mode,
            bf_mode,
            brute_crc,
            brute_length,
            from_error,
        ),
    )


def has_libpng_error(output: str, libpng_errors: tuple[str, ...] | list[str]) -> bool:
    return any(error in output for error in libpng_errors)


def process_command_is_tmp_png(cmdline: tuple[str, ...] | list[str]) -> bool:
    command = " ".join(cmdline)
    return "/tmp/tmp" in command and ".PNG" in command


def viewer_wait_step(found_tmp_png: bool, count: int, limit: int = 60) -> BruteForceViewerWaitState:
    next_count = count + 1
    return BruteForceViewerWaitState(
        found=found_tmp_png,
        count=next_count,
        done=found_tmp_png or next_count > limit,
    )


def highlighted_candidate_diff(source_hex: str, candidate_hex: str) -> str:
    diff = ""
    diffobj = difflib.SequenceMatcher(None, source_hex, candidate_hex)
    for block in diffobj.get_opcodes():
        if block[0] != "equal":
            diff += "\033[1;32;49m%s\033[m" % candidate_hex[block[1] : block[2]]
        else:
            diff += candidate_hex[block[1] : block[2]]
    return diff


def viewer_try_number(loop_index: int) -> int:
    return loop_index - 2


def viewer_found_summary(
    try_number: int,
    width: int,
    height: int,
    timestamp: str,
) -> str:
    return "-SmashBruteBrawl:Tries nbr %s Found a width:%s height:%s picture at %s" % (
        try_number,
        width,
        height,
        timestamp,
    )


def viewer_user_choice_summary(answer: bool, try_number: int) -> str:
    if answer is True:
        return "-SmashBruteBrawl:User chose yes at tries nbr:%s" % try_number
    return "-SmashBruteBrawl:User chose no at tries nbr:%s" % try_number


def viewer_timeout_save_path(
    original_dir: str,
    original_name: str,
    width: int,
    height: int,
    timestamp: str,
) -> str:
    return original_dir + "/" + "BF-W" + str(width) + "-H" + str(height) + timestamp + original_name


def viewer_timeout_saved_summary(try_number: int, tmpname: str) -> str:
    return (
        "-SmashBruteBrawl:Image nbr %s Skipped due to user input timeout.\n"
        "-SmashBruteBrawl:Image saved at %s ."
        % (str(try_number), tmpname)
    )


def viewer_timeout_save_failed_summary(tmpname: str, error: Any, crash_index: int) -> str:
    return (
        "-SmashBruteBrawl:Saving image %s failed due to %s.\n"
        "-SmashBruteBrawl:Use ./chunklate.py -f yourfile.png --crash %s to try again"
        % (tmpname, str(error), str(crash_index))
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


def iter_twobytes_edit_kinds(edit_mode: str, chunk_name: bytes) -> tuple[str, ...]:
    if chunk_name == b"IDAT":
        return ("replace", "insert", "remove")

    try:
        return (TWOBYTES_EDIT_KIND_BY_MODE[edit_mode],)
    except KeyError as exc:
        raise ValueError("Unknown TwoBytes edit mode: %s" % edit_mode) from exc


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


def twobytes_bonus_edit_kind(old_crc: Any, edit_kind: str) -> str | None:
    if old_crc and edit_kind == "replace":
        return None
    return edit_kind


def twobytes_scan_has_window(
    to_brute: str,
    brute_hex_len: int,
    needle: int,
    state: BruteForceMatchState,
) -> bool:
    return (
        brute_hex_len <= len(to_brute)
        and needle < len(to_brute) - (brute_hex_len - 1)
        and state.bingo is False
    )


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
