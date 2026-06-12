from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import heapq
from typing import Iterable
import zlib

from . import deflate_header


LENGTH_BASES = (
    3,
    4,
    5,
    6,
    7,
    8,
    9,
    10,
    11,
    13,
    15,
    17,
    19,
    23,
    27,
    31,
    35,
    43,
    51,
    59,
    67,
    83,
    99,
    115,
    131,
    163,
    195,
    227,
    258,
)
LENGTH_EXTRAS = (
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    0,
    1,
    1,
    1,
    1,
    2,
    2,
    2,
    2,
    3,
    3,
    3,
    3,
    4,
    4,
    4,
    4,
    5,
    5,
    5,
    5,
    0,
)
DISTANCE_BASES = (
    1,
    2,
    3,
    4,
    5,
    7,
    9,
    13,
    17,
    25,
    33,
    49,
    65,
    97,
    129,
    193,
    257,
    385,
    513,
    769,
    1025,
    1537,
    2049,
    3073,
    4097,
    6145,
    8193,
    12289,
    16385,
    24577,
)
DISTANCE_EXTRAS = (
    0,
    0,
    0,
    0,
    1,
    1,
    2,
    2,
    3,
    3,
    4,
    4,
    5,
    5,
    6,
    6,
    7,
    7,
    8,
    8,
    9,
    9,
    10,
    10,
    11,
    11,
    12,
    12,
    13,
    13,
)


@dataclass(frozen=True)
class DeflateCheckpoint:
    byte_offset: int
    bit_offset: int
    output_offset: int
    block_index: int
    block_type: int
    reason: str = "checkpoint"


@dataclass(frozen=True)
class DeflateHuffmanState:
    byte_offset: int
    bit_offset: int
    output_offset: int
    block_index: int
    block_type: int
    literal_table: dict[tuple[int, int], int]
    literal_max_bits: int
    distance_table: dict[tuple[int, int], int]
    distance_max_bits: int


@dataclass(frozen=True)
class DeflateHistoryState:
    huffman: DeflateHuffmanState
    output_tail: bytes
    tail_start: int
    history_size: int


@dataclass(frozen=True)
class DeflateTrace:
    status: str
    compressed_size: int
    decompressed_size: int = 0
    checkpoints: tuple[DeflateCheckpoint, ...] = ()
    huffman_states: tuple[DeflateHuffmanState, ...] = ()
    error_byte_offset: int | None = None
    error_bit_offset: int | None = None
    reason: str = ""
    zlib_wrapped: bool = True

    @property
    def ok(self) -> bool:
        return self.status == "complete"


@dataclass(frozen=True)
class DeflateWindowScore:
    window: object
    output_offset: int
    distance: int
    rank: int


@dataclass(frozen=True)
class DeflateLocalEditResult:
    accepted: bool
    trace: DeflateTrace


@dataclass(frozen=True)
class DeflatePrefixCandidate:
    prefix: bytes
    symbol_count: int
    output_delta: int = 0


class _ReachedTarget(Exception):
    def __init__(self, output_size: int):
        super().__init__("target output reached")
        self.output_size = int(output_size)


def _check_stop_after_output(output_size: int, stop_after_output: int | None) -> None:
    if stop_after_output is not None and int(output_size) >= int(stop_after_output):
        raise _ReachedTarget(output_size)


def _fixed_tables() -> tuple[dict[tuple[int, int], int], int, dict[tuple[int, int], int], int]:
    literal_lengths = [0] * 288
    for symbol in range(0, 144):
        literal_lengths[symbol] = 8
    for symbol in range(144, 256):
        literal_lengths[symbol] = 9
    for symbol in range(256, 280):
        literal_lengths[symbol] = 7
    for symbol in range(280, 288):
        literal_lengths[symbol] = 8
    distance_lengths = [5] * 32
    literal_table, literal_max = deflate_header._build_huffman_table(literal_lengths)
    distance_table, distance_max = deflate_header._build_huffman_table(distance_lengths)
    return literal_table, literal_max, distance_table, distance_max


_FIXED_TABLES = _fixed_tables()


def _symbol_codes(table: dict[tuple[int, int], int]) -> dict[int, tuple[int, int]]:
    return {
        symbol: (code, width)
        for (code, width), symbol in table.items()
    }


def _bits_for_code(code: int, width: int) -> tuple[int, ...]:
    return tuple((int(code) >> index) & 1 for index in range(int(width)))


def _pack_candidate_bits(
    payload: bytes,
    byte_offset: int,
    bit_offset: int,
    bits: tuple[int, ...],
    byte_count: int,
) -> bytes | None:
    byte_count = int(byte_count)
    if byte_count <= 0:
        return b""
    byte_offset = int(byte_offset)
    if byte_offset < 0 or byte_offset >= len(payload):
        return None
    bit_mod = int(bit_offset) % 8
    output = bytearray()
    current = int(payload[byte_offset]) & ((1 << bit_mod) - 1 if bit_mod else 0)
    current_bits = bit_mod
    for bit in bits:
        current |= (int(bit) & 1) << current_bits
        current_bits += 1
        if current_bits == 8:
            output.append(current)
            if len(output) >= byte_count:
                return bytes(output[:byte_count])
            current = 0
            current_bits = 0
    if current_bits and len(output) + 1 >= byte_count:
        output.append(current)
        return bytes(output[:byte_count])
    return None


def _prefix_token_bits(state: DeflateHuffmanState) -> tuple[tuple[int, ...], ...]:
    literal_codes = _symbol_codes(state.literal_table)
    distance_codes = _symbol_codes(state.distance_table)
    tokens: list[tuple[int, ...]] = []
    for symbol, (code, width) in literal_codes.items():
        if symbol < 256:
            tokens.append(_bits_for_code(code, width))
            continue
        if 257 <= symbol <= 285 and state.output_offset > 0:
            distance_code = distance_codes.get(0)
            if distance_code is None:
                continue
            length_index = symbol - 257
            length_extra = (0,) * LENGTH_EXTRAS[length_index]
            distance_extra = (0,) * DISTANCE_EXTRAS[0]
            tokens.append(
                _bits_for_code(code, width)
                + length_extra
                + _bits_for_code(distance_code[0], distance_code[1])
                + distance_extra
            )
    return tuple(sorted(tokens, key=lambda item: (len(item), item)))


def _payload_bit(payload: bytes, bit_offset: int) -> int | None:
    byte_offset = int(bit_offset) // 8
    if byte_offset < 0 or byte_offset >= len(payload):
        return None
    return (payload[byte_offset] >> (int(bit_offset) % 8)) & 1


def _pack_bits_to_bytes(bits: tuple[int, ...], byte_count: int) -> bytes | None:
    byte_count = int(byte_count)
    if byte_count <= 0:
        return b""
    if len(bits) < byte_count * 8:
        return None
    output = bytearray()
    for byte_index in range(byte_count):
        value = 0
        for bit_index in range(8):
            value |= (int(bits[byte_index * 8 + bit_index]) & 1) << bit_index
        output.append(value)
    return bytes(output)


def _bits_match_payload_prefix(
    payload: bytes,
    start_bit_offset: int,
    bits: tuple[int, ...],
    fixed_bit_count: int,
) -> bool:
    for index, bit in enumerate(bits[: max(0, int(fixed_bit_count))]):
        payload_bit = _payload_bit(payload, int(start_bit_offset) + index)
        if payload_bit is None or payload_bit != bit:
            return False
    return True


def _record_checkpoint(
    checkpoints: list[DeflateCheckpoint],
    reader: deflate_header.BitReader,
    output_size: int,
    block_index: int,
    block_type: int,
    reason: str,
) -> None:
    checkpoint = DeflateCheckpoint(
        byte_offset=reader.byte_offset,
        bit_offset=reader.bit_offset,
        output_offset=int(output_size),
        block_index=int(block_index),
        block_type=int(block_type),
        reason=reason,
    )
    if checkpoints and checkpoints[-1] == checkpoint:
        return
    checkpoints.append(checkpoint)


def _record_huffman_state(
    states: list[DeflateHuffmanState],
    reader: deflate_header.BitReader,
    output_size: int,
    block_index: int,
    block_type: int,
    literal_table: dict[tuple[int, int], int],
    literal_max: int,
    distance_table: dict[tuple[int, int], int],
    distance_max: int,
) -> None:
    state = _make_huffman_state(
        reader,
        output_size,
        block_index,
        block_type,
        literal_table,
        literal_max,
        distance_table,
        distance_max,
    )
    if states and states[-1].bit_offset == state.bit_offset:
        return
    states.append(state)


def _make_huffman_state(
    reader: deflate_header.BitReader,
    output_size: int,
    block_index: int,
    block_type: int,
    literal_table: dict[tuple[int, int], int],
    literal_max: int,
    distance_table: dict[tuple[int, int], int],
    distance_max: int,
) -> DeflateHuffmanState:
    return DeflateHuffmanState(
        byte_offset=reader.byte_offset,
        bit_offset=reader.bit_offset,
        output_offset=int(output_size),
        block_index=int(block_index),
        block_type=int(block_type),
        literal_table=literal_table,
        literal_max_bits=int(literal_max),
        distance_table=distance_table,
        distance_max_bits=int(distance_max),
    )


def _bad_trace(
    status: str,
    stream: bytes,
    reader: deflate_header.BitReader | None,
    output_size: int,
    checkpoints: list[DeflateCheckpoint],
    states: list[DeflateHuffmanState],
    *,
    reason: str,
    zlib_wrapped: bool,
) -> DeflateTrace:
    bit_offset = reader.bit_offset if reader is not None else None
    byte_offset = reader.byte_offset if reader is not None else None
    return DeflateTrace(
        status=status,
        compressed_size=len(stream),
        decompressed_size=int(output_size),
        checkpoints=tuple(checkpoints),
        huffman_states=tuple(states),
        error_byte_offset=byte_offset,
        error_bit_offset=bit_offset,
        reason=reason,
        zlib_wrapped=zlib_wrapped,
    )


def _align_to_byte(reader: deflate_header.BitReader) -> None:
    remainder = reader.bit_offset % 8
    if remainder:
        reader.bit_offset += 8 - remainder


def _history_append_byte(tail: bytearray, value: int, history_size: int) -> None:
    tail.append(int(value) & 0xFF)
    overflow = len(tail) - max(1, int(history_size))
    if overflow > 0:
        del tail[:overflow]


def _history_copy(tail: bytearray, distance: int, length: int, history_size: int) -> None:
    distance = int(distance)
    if distance <= 0 or distance > len(tail):
        raise deflate_header._InvalidHuffman("distance exceeds retained history")
    for _ in range(int(length)):
        _history_append_byte(tail, tail[-distance], history_size)


def _read_dynamic_tables(
    reader: deflate_header.BitReader,
) -> tuple[dict[tuple[int, int], int], int, dict[tuple[int, int], int], int]:
    hlit = reader.read(5) + 257
    hdist = reader.read(5) + 1
    hclen = reader.read(4) + 4
    code_length_lengths = [0] * 19
    for index in range(hclen):
        code_length_lengths[deflate_header.CODE_LENGTH_ORDER[index]] = reader.read(3)
    code_table, code_max = deflate_header._build_huffman_table(
        code_length_lengths,
        allow_single=True,
        allow_incomplete=True,
    )
    lengths = deflate_header._read_code_lengths(reader, code_table, code_max, hlit + hdist)
    literal_lengths = lengths[:hlit]
    distance_lengths = lengths[hlit:]
    literal_table, literal_max = deflate_header._build_huffman_table(literal_lengths)
    distance_table, distance_max = deflate_header._build_huffman_table(
        distance_lengths,
        allow_single=True,
    )
    return literal_table, literal_max, distance_table, distance_max


def _decode_compressed_block(
    reader: deflate_header.BitReader,
    literal_table: dict[tuple[int, int], int],
    literal_max: int,
    distance_table: dict[tuple[int, int], int],
    distance_max: int,
    output_size: int,
    checkpoints: list[DeflateCheckpoint],
    *,
    block_index: int,
    block_type: int,
    checkpoint_stride: int,
    stop_after_output: int | None,
) -> int:
    next_checkpoint = reader.byte_offset + max(1, int(checkpoint_stride))
    while True:
        symbol = deflate_header._decode_symbol(reader, literal_table, literal_max)
        if symbol < 256:
            output_size += 1
            _check_stop_after_output(output_size, stop_after_output)
        elif symbol == 256:
            _record_checkpoint(
                checkpoints,
                reader,
                output_size,
                block_index,
                block_type,
                "end-of-block",
            )
            return output_size
        elif 257 <= symbol <= 285:
            length_index = symbol - 257
            length = LENGTH_BASES[length_index]
            extra_bits = LENGTH_EXTRAS[length_index]
            if extra_bits:
                length += reader.read(extra_bits)
            distance_symbol = deflate_header._decode_symbol(reader, distance_table, distance_max)
            if distance_symbol >= len(DISTANCE_BASES):
                raise deflate_header._InvalidHuffman("invalid distance symbol")
            distance = DISTANCE_BASES[distance_symbol]
            distance_extra = DISTANCE_EXTRAS[distance_symbol]
            if distance_extra:
                distance += reader.read(distance_extra)
            if distance > output_size:
                raise deflate_header._InvalidHuffman("distance exceeds produced output")
            output_size += length
            _check_stop_after_output(output_size, stop_after_output)
        else:
            raise deflate_header._InvalidHuffman("invalid literal/length symbol")

        if reader.byte_offset >= next_checkpoint:
            _record_checkpoint(
                checkpoints,
                reader,
                output_size,
                block_index,
                block_type,
                "symbol",
            )
            next_checkpoint = reader.byte_offset + max(1, int(checkpoint_stride))


def analyze_deflate_stream(
    stream: bytes,
    *,
    zlib_wrapped: bool = True,
    checkpoint_stride: int = 256,
    stop_after_output: int | None = None,
) -> DeflateTrace:
    if zlib_wrapped and not deflate_header.zlib_header_is_valid(stream):
        return DeflateTrace(
            status="bad_zlib_header",
            compressed_size=len(stream),
            reason="bad zlib header",
            zlib_wrapped=zlib_wrapped,
        )
    reader = deflate_header.BitReader(stream, start_byte=2 if zlib_wrapped else 0)
    checkpoints: list[DeflateCheckpoint] = []
    states: list[DeflateHuffmanState] = []
    output_size = 0
    block_index = 0
    try:
        while True:
            bfinal = reader.read(1)
            btype = reader.read(2)
            _record_checkpoint(
                checkpoints,
                reader,
                output_size,
                block_index,
                btype,
                "block-header",
            )
            if btype == 0:
                _align_to_byte(reader)
                if reader.byte_offset + 4 > len(stream):
                    raise deflate_header._NeedBits
                len_value = stream[reader.byte_offset] | (stream[reader.byte_offset + 1] << 8)
                nlen_value = stream[reader.byte_offset + 2] | (stream[reader.byte_offset + 3] << 8)
                if (len_value ^ 0xFFFF) != nlen_value:
                    return _bad_trace(
                        "bad_stored_length",
                        stream,
                        reader,
                        output_size,
                        checkpoints,
                        states,
                        reason="stored block length complement mismatch",
                        zlib_wrapped=zlib_wrapped,
                    )
                reader.bit_offset += 32
                data_start = reader.byte_offset
                data_end = data_start + len_value
                if data_end > len(stream):
                    raise deflate_header._NeedBits
                stride = max(1, int(checkpoint_stride))
                while reader.byte_offset + stride < data_end:
                    reader.bit_offset += stride * 8
                    output_size += stride
                    _check_stop_after_output(output_size, stop_after_output)
                    _record_checkpoint(
                        checkpoints,
                        reader,
                        output_size,
                        block_index,
                        btype,
                        "stored-data",
                    )
                output_size += data_end - reader.byte_offset
                _check_stop_after_output(output_size, stop_after_output)
                reader.bit_offset = data_end * 8
                _record_checkpoint(
                    checkpoints,
                    reader,
                    output_size,
                    block_index,
                    btype,
                    "stored-end",
                )
            elif btype == 1:
                literal_table, literal_max, distance_table, distance_max = _FIXED_TABLES
                _record_huffman_state(
                    states,
                    reader,
                    output_size,
                    block_index,
                    btype,
                    literal_table,
                    literal_max,
                    distance_table,
                    distance_max,
                )
                output_size = _decode_compressed_block(
                    reader,
                    literal_table,
                    literal_max,
                    distance_table,
                    distance_max,
                    output_size,
                    checkpoints,
                    block_index=block_index,
                    block_type=btype,
                    checkpoint_stride=checkpoint_stride,
                    stop_after_output=stop_after_output,
                )
            elif btype == 2:
                literal_table, literal_max, distance_table, distance_max = _read_dynamic_tables(reader)
                _record_huffman_state(
                    states,
                    reader,
                    output_size,
                    block_index,
                    btype,
                    literal_table,
                    literal_max,
                    distance_table,
                    distance_max,
                )
                _record_checkpoint(
                    checkpoints,
                    reader,
                    output_size,
                    block_index,
                    btype,
                    "dynamic-header",
                )
                output_size = _decode_compressed_block(
                    reader,
                    literal_table,
                    literal_max,
                    distance_table,
                    distance_max,
                    output_size,
                    checkpoints,
                    block_index=block_index,
                    block_type=btype,
                    checkpoint_stride=checkpoint_stride,
                    stop_after_output=stop_after_output,
                )
            else:
                return _bad_trace(
                    "reserved_block_type",
                    stream,
                    reader,
                    output_size,
                    checkpoints,
                    states,
                    reason="reserved deflate block type",
                    zlib_wrapped=zlib_wrapped,
                )
            block_index += 1
            if bfinal:
                _record_checkpoint(
                    checkpoints,
                    reader,
                    output_size,
                    block_index - 1,
                    btype,
                    "final-block",
                )
                return DeflateTrace(
                    status="complete",
                    compressed_size=len(stream),
                    decompressed_size=output_size,
                    checkpoints=tuple(checkpoints),
                    huffman_states=tuple(states),
                    zlib_wrapped=zlib_wrapped,
                )
    except deflate_header._NeedBits:
        return _bad_trace(
            "truncated",
            stream,
            reader,
            output_size,
            checkpoints,
            states,
            reason="truncated deflate stream",
            zlib_wrapped=zlib_wrapped,
        )
    except deflate_header._InvalidHuffman as exc:
        return _bad_trace(
            "invalid_huffman",
            stream,
            reader,
            output_size,
            checkpoints,
            states,
            reason=str(exc),
            zlib_wrapped=zlib_wrapped,
        )
    except _ReachedTarget as exc:
        _record_checkpoint(
            checkpoints,
            reader,
            exc.output_size,
            max(0, block_index),
            -1,
            "target-output",
        )
        return DeflateTrace(
            status="prefix_ok",
            compressed_size=len(stream),
            decompressed_size=exc.output_size,
            checkpoints=tuple(checkpoints),
            huffman_states=tuple(states),
            zlib_wrapped=zlib_wrapped,
        )


@lru_cache(maxsize=8)
def cached_analyze_deflate_stream(
    stream: bytes,
    *,
    zlib_wrapped: bool = True,
    checkpoint_stride: int = 2048,
) -> DeflateTrace:
    return analyze_deflate_stream(
        stream,
        zlib_wrapped=zlib_wrapped,
        checkpoint_stride=checkpoint_stride,
    )


def output_offset_before_byte(trace: DeflateTrace, byte_offset: int) -> int:
    if not trace.checkpoints:
        return 0
    target = int(byte_offset)
    best = trace.checkpoints[0]
    for checkpoint in trace.checkpoints:
        if checkpoint.byte_offset > target:
            break
        best = checkpoint
    return int(best.output_offset)


def huffman_state_before_byte(trace: DeflateTrace, byte_offset: int) -> DeflateHuffmanState | None:
    target = int(byte_offset)
    best: DeflateHuffmanState | None = None
    for state in trace.huffman_states:
        if state.byte_offset > target:
            break
        best = state
    return best


def _seek_huffman_state_in_block(
    reader: deflate_header.BitReader,
    literal_table: dict[tuple[int, int], int],
    literal_max: int,
    distance_table: dict[tuple[int, int], int],
    distance_max: int,
    output_size: int,
    *,
    target_byte_offset: int,
    block_index: int,
    block_type: int,
) -> tuple[int, DeflateHuffmanState | None, bool]:
    while True:
        if reader.byte_offset == int(target_byte_offset):
            return (
                output_size,
                _make_huffman_state(
                    reader,
                    output_size,
                    block_index,
                    block_type,
                    literal_table,
                    literal_max,
                    distance_table,
                    distance_max,
                ),
                False,
            )
        if reader.byte_offset > int(target_byte_offset):
            return output_size, None, False
        symbol = deflate_header._decode_symbol(reader, literal_table, literal_max)
        if symbol < 256:
            output_size += 1
        elif symbol == 256:
            return output_size, None, True
        elif 257 <= symbol <= 285:
            length_index = symbol - 257
            length = LENGTH_BASES[length_index]
            extra_bits = LENGTH_EXTRAS[length_index]
            if extra_bits:
                length += reader.read(extra_bits)
            distance_symbol = deflate_header._decode_symbol(reader, distance_table, distance_max)
            if distance_symbol >= len(DISTANCE_BASES):
                raise deflate_header._InvalidHuffman("invalid distance symbol")
            distance = DISTANCE_BASES[distance_symbol]
            distance_extra = DISTANCE_EXTRAS[distance_symbol]
            if distance_extra:
                distance += reader.read(distance_extra)
            if distance > output_size:
                raise deflate_header._InvalidHuffman("distance exceeds produced output")
            output_size += length
        else:
            raise deflate_header._InvalidHuffman("invalid literal/length symbol")
        if reader.byte_offset == int(target_byte_offset):
            return (
                output_size,
                _make_huffman_state(
                    reader,
                    output_size,
                    block_index,
                    block_type,
                    literal_table,
                    literal_max,
                    distance_table,
                    distance_max,
                ),
                False,
            )


def _decode_one_huffman_token(
    reader: deflate_header.BitReader,
    state: DeflateHuffmanState,
    output_size: int,
) -> tuple[int, bool]:
    symbol = deflate_header._decode_symbol(reader, state.literal_table, state.literal_max_bits)
    if symbol < 256:
        return output_size + 1, False
    if symbol == 256:
        return output_size, True
    if 257 <= symbol <= 285:
        length_index = symbol - 257
        length = LENGTH_BASES[length_index]
        extra_bits = LENGTH_EXTRAS[length_index]
        if extra_bits:
            length += reader.read(extra_bits)
        distance_symbol = deflate_header._decode_symbol(
            reader,
            state.distance_table,
            state.distance_max_bits,
        )
        if distance_symbol >= len(DISTANCE_BASES):
            raise deflate_header._InvalidHuffman("invalid distance symbol")
        distance = DISTANCE_BASES[distance_symbol]
        distance_extra = DISTANCE_EXTRAS[distance_symbol]
        if distance_extra:
            distance += reader.read(distance_extra)
        if distance > output_size:
            raise deflate_header._InvalidHuffman("distance exceeds produced output")
        return output_size + length, False
    raise deflate_header._InvalidHuffman("invalid literal/length symbol")


def _seek_huffman_state_before_bit_from_state(
    stream: bytes,
    state: DeflateHuffmanState,
    target_bit_offset: int,
) -> DeflateHuffmanState | None:
    if int(state.bit_offset) > int(target_bit_offset):
        return None
    reader = deflate_header.BitReader(stream)
    reader.bit_offset = int(state.bit_offset)
    output_size = int(state.output_offset)
    best = state
    try:
        while reader.bit_offset < int(target_bit_offset):
            symbol_start = _make_huffman_state(
                reader,
                output_size,
                state.block_index,
                state.block_type,
                state.literal_table,
                state.literal_max_bits,
                state.distance_table,
                state.distance_max_bits,
            )
            output_size, ended = _decode_one_huffman_token(reader, state, output_size)
            if reader.bit_offset >= int(target_bit_offset):
                return symbol_start
            best = _make_huffman_state(
                reader,
                output_size,
                state.block_index,
                state.block_type,
                state.literal_table,
                state.literal_max_bits,
                state.distance_table,
                state.distance_max_bits,
            )
            if ended:
                return None
    except (deflate_header._NeedBits, deflate_header._InvalidHuffman):
        return None
    return best


def _history_result(
    state: DeflateHuffmanState,
    output_size: int,
    tail: bytearray,
    history_size: int,
) -> DeflateHistoryState:
    output_size = int(output_size)
    return DeflateHistoryState(
        huffman=state,
        output_tail=bytes(tail),
        tail_start=max(0, output_size - len(tail)),
        history_size=max(1, int(history_size)),
    )


def _replay_history_to_state(
    stream: bytes,
    target_state: DeflateHuffmanState,
    *,
    zlib_wrapped: bool,
    history_size: int,
) -> DeflateHistoryState | None:
    fast = _zlib_history_to_state(
        stream,
        target_state,
        zlib_wrapped=zlib_wrapped,
        history_size=history_size,
    )
    if fast is not None:
        return fast
    if zlib_wrapped and not deflate_header.zlib_header_is_valid(stream):
        return None
    target_bit_offset = int(target_state.bit_offset)
    reader = deflate_header.BitReader(stream, start_byte=2 if zlib_wrapped else 0)
    output_size = 0
    block_index = 0
    tail = bytearray()
    try:
        while reader.bit_offset <= target_bit_offset:
            if reader.bit_offset == target_bit_offset:
                return _history_result(target_state, output_size, tail, history_size)
            bfinal = reader.read(1)
            btype = reader.read(2)
            if btype == 0:
                _align_to_byte(reader)
                if reader.byte_offset + 4 > len(stream):
                    raise deflate_header._NeedBits
                len_value = stream[reader.byte_offset] | (stream[reader.byte_offset + 1] << 8)
                nlen_value = stream[reader.byte_offset + 2] | (stream[reader.byte_offset + 3] << 8)
                if (len_value ^ 0xFFFF) != nlen_value:
                    raise deflate_header._InvalidHuffman("stored block length complement mismatch")
                reader.bit_offset += 32
                data_start = reader.byte_offset
                data_end = data_start + len_value
                if data_end > len(stream):
                    raise deflate_header._NeedBits
                if reader.bit_offset <= target_bit_offset < data_end * 8:
                    return None
                for value in stream[data_start:data_end]:
                    _history_append_byte(tail, value, history_size)
                output_size += len_value
                reader.bit_offset = data_end * 8
            elif btype == 1:
                literal_table, literal_max, distance_table, distance_max = _FIXED_TABLES
                if reader.bit_offset == target_bit_offset:
                    return _history_result(target_state, output_size, tail, history_size)
                while True:
                    if reader.bit_offset == target_bit_offset:
                        return _history_result(target_state, output_size, tail, history_size)
                    if reader.bit_offset > target_bit_offset:
                        return None
                    symbol = deflate_header._decode_symbol(reader, literal_table, literal_max)
                    if symbol < 256:
                        _history_append_byte(tail, symbol, history_size)
                        output_size += 1
                    elif symbol == 256:
                        break
                    elif 257 <= symbol <= 285:
                        length_index = symbol - 257
                        length = LENGTH_BASES[length_index]
                        extra_bits = LENGTH_EXTRAS[length_index]
                        if extra_bits:
                            length += reader.read(extra_bits)
                        distance_symbol = deflate_header._decode_symbol(reader, distance_table, distance_max)
                        if distance_symbol >= len(DISTANCE_BASES):
                            raise deflate_header._InvalidHuffman("invalid distance symbol")
                        distance = DISTANCE_BASES[distance_symbol]
                        distance_extra = DISTANCE_EXTRAS[distance_symbol]
                        if distance_extra:
                            distance += reader.read(distance_extra)
                        if distance > output_size:
                            raise deflate_header._InvalidHuffman("distance exceeds produced output")
                        _history_copy(tail, distance, length, history_size)
                        output_size += length
                    else:
                        raise deflate_header._InvalidHuffman("invalid literal/length symbol")
            elif btype == 2:
                literal_table, literal_max, distance_table, distance_max = _read_dynamic_tables(reader)
                if reader.bit_offset == target_bit_offset:
                    return _history_result(target_state, output_size, tail, history_size)
                while True:
                    if reader.bit_offset == target_bit_offset:
                        return _history_result(target_state, output_size, tail, history_size)
                    if reader.bit_offset > target_bit_offset:
                        return None
                    symbol = deflate_header._decode_symbol(reader, literal_table, literal_max)
                    if symbol < 256:
                        _history_append_byte(tail, symbol, history_size)
                        output_size += 1
                    elif symbol == 256:
                        break
                    elif 257 <= symbol <= 285:
                        length_index = symbol - 257
                        length = LENGTH_BASES[length_index]
                        extra_bits = LENGTH_EXTRAS[length_index]
                        if extra_bits:
                            length += reader.read(extra_bits)
                        distance_symbol = deflate_header._decode_symbol(reader, distance_table, distance_max)
                        if distance_symbol >= len(DISTANCE_BASES):
                            raise deflate_header._InvalidHuffman("invalid distance symbol")
                        distance = DISTANCE_BASES[distance_symbol]
                        distance_extra = DISTANCE_EXTRAS[distance_symbol]
                        if distance_extra:
                            distance += reader.read(distance_extra)
                        if distance > output_size:
                            raise deflate_header._InvalidHuffman("distance exceeds produced output")
                        _history_copy(tail, distance, length, history_size)
                        output_size += length
                    else:
                        raise deflate_header._InvalidHuffman("invalid literal/length symbol")
            else:
                return None
            block_index += 1
            if bfinal and reader.bit_offset <= target_bit_offset:
                return None
    except (deflate_header._NeedBits, deflate_header._InvalidHuffman):
        return None
    return None


def _zlib_history_to_state(
    stream: bytes,
    target_state: DeflateHuffmanState,
    *,
    zlib_wrapped: bool,
    history_size: int,
) -> DeflateHistoryState | None:
    output_target = int(target_state.output_offset)
    if output_target < 0:
        return None
    if output_target == 0:
        return DeflateHistoryState(
            huffman=target_state,
            output_tail=b"",
            tail_start=0,
            history_size=max(1, int(history_size)),
        )
    try:
        decompressor = zlib.decompressobj(15 if zlib_wrapped else -15)
        output = decompressor.decompress(stream, output_target)
    except zlib.error:
        return None
    if len(output) < output_target:
        return None
    tail = output[-max(1, int(history_size)) :]
    return DeflateHistoryState(
        huffman=target_state,
        output_tail=tail,
        tail_start=max(0, output_target - len(tail)),
        history_size=max(1, int(history_size)),
    )


def huffman_state_before_byte_boundary(
    stream: bytes,
    byte_offset: int,
    *,
    trace: DeflateTrace | None = None,
    zlib_wrapped: bool = True,
    checkpoint_stride: int = 2048,
) -> DeflateHuffmanState | None:
    target_bit_offset = int(byte_offset) * 8
    if trace is None:
        trace = analyze_deflate_stream(
            stream,
            zlib_wrapped=zlib_wrapped,
            checkpoint_stride=checkpoint_stride,
        )
    base_state = huffman_state_before_byte(trace, int(byte_offset))
    if base_state is None:
        return None
    return _seek_huffman_state_before_bit_from_state(stream, base_state, target_bit_offset)


def huffman_history_state_before_byte_boundary(
    stream: bytes,
    byte_offset: int,
    *,
    trace: DeflateTrace | None = None,
    zlib_wrapped: bool = True,
    checkpoint_stride: int = 2048,
    history_size: int = 32768,
) -> DeflateHistoryState | None:
    state = huffman_state_before_byte_boundary(
        stream,
        byte_offset,
        trace=trace,
        zlib_wrapped=zlib_wrapped,
        checkpoint_stride=checkpoint_stride,
    )
    if state is None:
        return None
    return _replay_history_to_state(
        stream,
        state,
        zlib_wrapped=zlib_wrapped,
        history_size=history_size,
    )


def huffman_state_at_byte(
    stream: bytes,
    byte_offset: int,
    *,
    zlib_wrapped: bool = True,
) -> DeflateHuffmanState | None:
    if zlib_wrapped and not deflate_header.zlib_header_is_valid(stream):
        return None
    target = int(byte_offset)
    reader = deflate_header.BitReader(stream, start_byte=2 if zlib_wrapped else 0)
    output_size = 0
    block_index = 0
    try:
        while reader.byte_offset <= target:
            bfinal = reader.read(1)
            btype = reader.read(2)
            if btype == 0:
                _align_to_byte(reader)
                if reader.byte_offset + 4 > len(stream):
                    return None
                len_value = stream[reader.byte_offset] | (stream[reader.byte_offset + 1] << 8)
                nlen_value = stream[reader.byte_offset + 2] | (stream[reader.byte_offset + 3] << 8)
                if (len_value ^ 0xFFFF) != nlen_value:
                    return None
                reader.bit_offset += 32
                data_end = reader.byte_offset + len_value
                if target < data_end:
                    return None
                output_size += len_value
                reader.bit_offset = data_end * 8
            elif btype == 1:
                literal_table, literal_max, distance_table, distance_max = _FIXED_TABLES
                output_size, state, ended = _seek_huffman_state_in_block(
                    reader,
                    literal_table,
                    literal_max,
                    distance_table,
                    distance_max,
                    output_size,
                    target_byte_offset=target,
                    block_index=block_index,
                    block_type=btype,
                )
                if state is not None or not ended:
                    return state
            elif btype == 2:
                literal_table, literal_max, distance_table, distance_max = _read_dynamic_tables(reader)
                output_size, state, ended = _seek_huffman_state_in_block(
                    reader,
                    literal_table,
                    literal_max,
                    distance_table,
                    distance_max,
                    output_size,
                    target_byte_offset=target,
                    block_index=block_index,
                    block_type=btype,
                )
                if state is not None or not ended:
                    return state
            else:
                return None
            if bfinal:
                return None
            block_index += 1
    except (deflate_header._NeedBits, deflate_header._InvalidHuffman):
        return None
    return None


def iter_huffman_byte_prefix_candidates(
    payload: bytes,
    state: DeflateHuffmanState,
    byte_position: int,
    byte_count: int,
    *,
    max_candidates: int = 128,
    max_symbols: int | None = None,
    max_branch_tokens: int = 64,
    max_fixed_bits: int = 64,
    target_output_delta: int | None = None,
    max_expansions: int | None = 100_000,
    suffix_payload_bit_offset: int | None = None,
    suffix_bit_count: int = 0,
) -> tuple[DeflatePrefixCandidate, ...]:
    byte_count = int(byte_count)
    if byte_count <= 0 or max_candidates <= 0:
        return ()
    target_bit = int(byte_position) * 8
    fixed_bit_count = target_bit - int(state.bit_offset)
    if fixed_bit_count < 0 or fixed_bit_count > int(max_fixed_bits):
        return ()
    suffix_bit_count = max(0, int(suffix_bit_count))
    suffix_start_bit = fixed_bit_count + byte_count * 8
    required_bits = suffix_start_bit + suffix_bit_count
    literal_codes = _symbol_codes(state.literal_table)
    distance_codes = _symbol_codes(state.distance_table)
    templates: list[tuple[int, int, tuple[object, ...]]] = []
    match_bias = int(state.output_offset) > 1024
    for symbol, (code, width) in literal_codes.items():
        if symbol < 256:
            template = (_bits_for_code(code, width),)
            literal_score = int(width) * 8 + (32 if match_bias else 0)
            templates.append((literal_score, 1, template))
        elif 257 <= symbol <= 285 and state.output_offset > 0:
            length_index = symbol - 257
            length_bits = _bits_for_code(code, width)
            output_delta = LENGTH_BASES[length_index]
            for distance_symbol, (distance_code, distance_width) in distance_codes.items():
                if distance_symbol >= len(DISTANCE_BASES):
                    continue
                if DISTANCE_BASES[distance_symbol] > state.output_offset:
                    continue
                extra_bits = LENGTH_EXTRAS[length_index] + DISTANCE_EXTRAS[distance_symbol]
                template = (
                    length_bits,
                    ("extra", LENGTH_EXTRAS[length_index]),
                    _bits_for_code(distance_code, distance_width),
                    ("extra", DISTANCE_EXTRAS[distance_symbol]),
                )
                code_cost = int(width) + int(distance_width)
                match_score = code_cost * 8 + min(8, extra_bits)
                if not match_bias:
                    match_score += 16
                templates.append((match_score, output_delta, template))
    templates.sort(
        key=lambda item: (
            item[0],
            sum(part[1] if isinstance(part, tuple) and part and part[0] == "extra" else len(part) for part in item[2]),
            repr(item[2]),
        )
    )
    templates = templates[: max(1, int(max_branch_tokens))]
    if not templates:
        return ()
    if max_symbols is None:
        max_symbols = max(2, byte_count * 3)
    queue_limit = max(64, int(max_candidates) * 8)
    branch_limit = max(32, int(max_candidates) * 4)
    expansion_budget = None if max_expansions is None else max(0, int(max_expansions))
    expansions = 0

    def output_delta_penalty(bits: tuple[int, ...], output_delta: int) -> int:
        if target_output_delta is None or required_bits <= 0:
            return 0
        progress = min(1.0, max(0.0, len(bits) / float(required_bits)))
        expected = int(target_output_delta) * progress
        return int(abs(int(output_delta) - expected) * 12)

    def append_bit(bits: tuple[int, ...], bit: int) -> tuple[tuple[int, ...], ...]:
        nonlocal expansions
        if len(bits) >= required_bits:
            return (bits,)
        absolute_bit = int(state.bit_offset) + len(bits)
        if absolute_bit < target_bit:
            payload_bit = _payload_bit(payload, absolute_bit)
            if payload_bit is None or payload_bit != int(bit):
                return ()
        elif suffix_payload_bit_offset is not None and len(bits) >= suffix_start_bit:
            suffix_index = len(bits) - suffix_start_bit
            if suffix_index < suffix_bit_count:
                payload_bit = _payload_bit(payload, int(suffix_payload_bit_offset) + suffix_index)
                if payload_bit is None or payload_bit != int(bit):
                    return ()
        expansions += 1
        return (bits + (int(bit) & 1,),)

    def append_known_bits(bits: tuple[int, ...], known_bits: tuple[int, ...]) -> tuple[tuple[int, ...], ...]:
        partials = (bits,)
        for known_bit in known_bits:
            next_partials: list[tuple[int, ...]] = []
            for partial in partials:
                next_partials.extend(append_bit(partial, known_bit))
            partials = tuple(next_partials)
            if not partials:
                return ()
        return partials

    def append_extra_bits(bits: tuple[int, ...], width: int) -> tuple[tuple[int, ...], ...]:
        partials = (bits,)
        for _ in range(int(width)):
            next_partials: list[tuple[int, ...]] = []
            for partial in partials:
                if len(partial) >= required_bits:
                    next_partials.append(partial)
                    continue
                absolute_bit = int(state.bit_offset) + len(partial)
                if absolute_bit < target_bit:
                    payload_bit = _payload_bit(payload, absolute_bit)
                    if payload_bit is not None:
                        next_partials.extend(append_bit(partial, payload_bit))
                    continue
                next_partials.extend(append_bit(partial, 0))
                next_partials.extend(append_bit(partial, 1))
            if len(next_partials) > branch_limit:
                next_partials = next_partials[:branch_limit]
            partials = tuple(next_partials)
            if not partials:
                return ()
        return partials

    def append_template(bits: tuple[int, ...], template: tuple[object, ...]) -> tuple[tuple[int, ...], ...]:
        partials = (bits,)
        for part in template:
            next_partials: list[tuple[int, ...]] = []
            for partial in partials:
                if isinstance(part, tuple) and part and part[0] == "extra":
                    next_partials.extend(append_extra_bits(partial, int(part[1])))
                else:
                    next_partials.extend(append_known_bits(partial, part))  # type: ignore[arg-type]
            partials = tuple(next_partials)
            if not partials:
                return ()
        return partials

    queue: list[tuple[int, int, int, int, int, tuple[int, ...]]] = [(0, 0, 0, 0, 0, ())]
    queue_order = 1
    seen: set[bytes] = set()
    results: list[DeflatePrefixCandidate] = []
    while queue and len(results) < int(max_candidates):
        _priority, code_score, symbol_count, output_delta, _order, bits = heapq.heappop(queue)
        if len(bits) >= required_bits:
            candidate = _pack_bits_to_bytes(
                bits[fixed_bit_count : fixed_bit_count + byte_count * 8],
                byte_count,
            )
            if candidate is not None and candidate not in seen:
                seen.add(candidate)
                results.append(DeflatePrefixCandidate(candidate, symbol_count, output_delta))
            continue
        if expansion_budget is not None and expansions >= expansion_budget:
            continue
        if symbol_count >= int(max_symbols):
            continue
        for template_score, template_output_delta, template in templates:
            for next_bits in append_template(bits, template):
                next_code_score = code_score + int(template_score)
                completed_delta = int(template_output_delta) if len(next_bits) <= required_bits else 0
                next_output_delta = output_delta + completed_delta
                priority = next_code_score + output_delta_penalty(next_bits, next_output_delta)
                heapq.heappush(
                    queue,
                    (
                        priority,
                        next_code_score,
                        symbol_count + 1,
                        next_output_delta,
                        queue_order,
                        next_bits,
                    ),
                )
                queue_order += 1
                if len(queue) > queue_limit:
                    break
            if len(queue) > queue_limit:
                break
    return tuple(results)


def iter_huffman_prefix_candidates(
    payload: bytes,
    state: DeflateHuffmanState,
    byte_count: int,
    *,
    max_candidates: int = 128,
    max_symbols: int | None = None,
    max_branch_tokens: int = 48,
) -> tuple[DeflatePrefixCandidate, ...]:
    byte_count = int(byte_count)
    if byte_count <= 0 or max_candidates <= 0:
        return ()
    tokens = _prefix_token_bits(state)[: max(1, int(max_branch_tokens))]
    if not tokens:
        return ()
    if max_symbols is None:
        max_symbols = max(2, byte_count * 3)
    max_bit_count = byte_count * 8 + (int(state.bit_offset) % 8)
    queue: list[tuple[tuple[int, ...], int]] = [((), 0)]
    seen: set[bytes] = set()
    results: list[DeflatePrefixCandidate] = []
    while queue and len(results) < int(max_candidates):
        bits, symbol_count = queue.pop(0)
        prefix = _pack_candidate_bits(
            payload,
            state.byte_offset,
            state.bit_offset,
            bits,
            byte_count,
        )
        if prefix is not None:
            if prefix not in seen:
                seen.add(prefix)
                results.append(DeflatePrefixCandidate(prefix, symbol_count))
            continue
        if symbol_count >= int(max_symbols) or len(bits) >= max_bit_count:
            continue
        for token in tokens:
            queue.append((bits + token, symbol_count + 1))
            if len(queue) > int(max_candidates) * max(4, int(max_branch_tokens)):
                break
    return tuple(results)


def score_windows_by_output_offset(
    trace: DeflateTrace,
    windows: Iterable[object],
    target_output_offset: int,
) -> tuple[DeflateWindowScore, ...]:
    scores: list[DeflateWindowScore] = []
    for rank, window in enumerate(windows):
        start = int(getattr(window, "start"))
        end = int(getattr(window, "end"))
        center = start + max(0, (end - start) // 2)
        output_offset = output_offset_before_byte(trace, center)
        scores.append(
            DeflateWindowScore(
                window=window,
                output_offset=output_offset,
                distance=abs(output_offset - int(target_output_offset)),
                rank=rank,
            )
        )
    return tuple(sorted(scores, key=lambda item: (item.distance, item.rank)))


def apply_local_edit(
    payload: bytes,
    position: int,
    edit_kind: str,
    byte_count: int,
    brute_bytes: bytes,
) -> bytes:
    position = int(position)
    byte_count = int(byte_count)
    if edit_kind == "insert":
        return payload[:position] + brute_bytes + payload[position:]
    if edit_kind == "replace":
        return payload[:position] + brute_bytes + payload[position + byte_count :]
    if edit_kind == "remove":
        return payload[:position] + payload[position + byte_count :]
    raise ValueError("unsupported edit kind: %s" % edit_kind)


def validate_local_edit(
    payload: bytes,
    position: int,
    edit_kind: str,
    byte_count: int,
    brute_bytes: bytes,
    *,
    stop_after_output: int | None = None,
    zlib_wrapped: bool = True,
    checkpoint_stride: int = 256,
) -> DeflateLocalEditResult:
    repaired = apply_local_edit(payload, position, edit_kind, byte_count, brute_bytes)
    trace = analyze_deflate_stream(
        repaired,
        zlib_wrapped=zlib_wrapped,
        checkpoint_stride=checkpoint_stride,
        stop_after_output=stop_after_output,
    )
    return DeflateLocalEditResult(
        accepted=trace.status in {"complete", "prefix_ok"},
        trace=trace,
    )
