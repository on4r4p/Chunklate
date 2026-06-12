from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from . import deflate_probe


@dataclass(frozen=True)
class ReverseHuffmanCode:
    symbol: int
    width: int
    forward_bits: tuple[int, ...]
    backward_bits: tuple[int, ...]


@dataclass(frozen=True)
class ReverseTailPath:
    start_relative_bit: int
    bits: tuple[int | None, ...]
    token_count: int
    output_delta: int
    score: int
    reason: str = "reverse-tail"


class ReverseBitCursor:
    def __init__(self, data: bytes, bit_offset: int):
        self.data = data
        self.bit_offset = int(bit_offset)

    def read_bits(self, width: int) -> tuple[int, ...]:
        if int(width) < 0:
            raise ValueError("width must be non-negative")
        bits: list[int] = []
        for _index in range(int(width)):
            if self.bit_offset <= 0:
                raise EOFError("not enough bits before reverse cursor")
            self.bit_offset -= 1
            byte_offset = self.bit_offset // 8
            bits.append((self.data[byte_offset] >> (self.bit_offset % 8)) & 1)
        return tuple(bits)

    def read(self, width: int) -> int:
        value = 0
        for index, bit in enumerate(self.read_bits(width)):
            value |= int(bit) << index
        return value


class ReverseHuffmanIndex:
    def __init__(self, codes: Iterable[ReverseHuffmanCode]):
        self.codes = tuple(
            sorted(
                codes,
                key=lambda item: (
                    item.width,
                    item.symbol,
                    item.forward_bits,
                ),
            )
        )

    @classmethod
    def from_table(cls, table: dict[tuple[int, int], int]) -> "ReverseHuffmanIndex":
        codes = []
        for (code, width), symbol in table.items():
            forward_bits = deflate_probe._bits_for_code(int(code), int(width))
            codes.append(
                ReverseHuffmanCode(
                    int(symbol),
                    int(width),
                    forward_bits,
                    tuple(reversed(forward_bits)),
                )
            )
        return cls(codes)

    def matches_backward_bits(
        self,
        bits: tuple[int | None, ...],
        *,
        limit: int | None = None,
    ) -> tuple[ReverseHuffmanCode, ...]:
        matches: list[ReverseHuffmanCode] = []
        for code in self.codes:
            if len(bits) < code.width:
                continue
            ok = True
            for index, bit in enumerate(code.backward_bits):
                known = bits[index]
                if known is not None and int(known) != int(bit):
                    ok = False
                    break
            if ok:
                matches.append(code)
                if limit is not None and len(matches) >= int(limit):
                    break
        return tuple(matches)


def _distance_hint_penalty(distance: int, distance_hints: tuple[int, ...]) -> int:
    if not distance_hints:
        return 0
    distance = int(distance)
    best = min(abs(distance - int(hint)) for hint in distance_hints if int(hint) > 0)
    return min(4096, best)


def _reverse_token_options(
    state: deflate_probe.DeflateHuffmanState,
    *,
    distance_hints: tuple[int, ...] = (),
    max_options: int = 128,
) -> tuple[ReverseTailPath, ...]:
    literal_index = ReverseHuffmanIndex.from_table(state.literal_table)
    distance_index = ReverseHuffmanIndex.from_table(state.distance_table)
    options: list[ReverseTailPath] = []

    for code in literal_index.codes:
        symbol = int(code.symbol)
        if symbol < 256:
            options.append(
                ReverseTailPath(
                    0,
                    code.forward_bits,
                    1,
                    1,
                    int(code.width) * 8 + 64,
                    "literal",
                )
            )
            continue
        if not (257 <= symbol <= 285):
            continue
        length_index = symbol - 257
        length_base = deflate_probe.LENGTH_BASES[length_index]
        length_extra = deflate_probe.LENGTH_EXTRAS[length_index]
        for distance_code in distance_index.codes:
            distance_symbol = int(distance_code.symbol)
            if distance_symbol >= len(deflate_probe.DISTANCE_BASES):
                continue
            distance_base = deflate_probe.DISTANCE_BASES[distance_symbol]
            if distance_base > int(state.output_offset) + length_base:
                continue
            distance_extra = deflate_probe.DISTANCE_EXTRAS[distance_symbol]
            token_bits: tuple[int | None, ...] = (
                code.forward_bits
                + (None,) * int(length_extra)
                + distance_code.forward_bits
                + (None,) * int(distance_extra)
            )
            score = (
                (int(code.width) + int(distance_code.width)) * 5
                + (int(length_extra) + int(distance_extra)) * 2
                + min(128, _distance_hint_penalty(distance_base, distance_hints) // 16)
                - min(96, int(length_base) * 4)
            )
            options.append(
                ReverseTailPath(
                    0,
                    token_bits,
                    1,
                    int(length_base),
                    score,
                    "length-distance",
                )
            )
    return tuple(
        sorted(
            options,
            key=lambda item: (
                item.score,
                len(item.bits),
                -item.output_delta,
                item.bits,
            ),
        )[: max(1, int(max_options))]
    )


def iter_reverse_tail_paths(
    state: deflate_probe.DeflateHuffmanState,
    *,
    candidate_start_relative_bit: int,
    candidate_end_relative_bit: int,
    max_paths: int = 128,
    max_tokens: int = 4,
    max_token_options: int = 128,
    distance_hints: tuple[int, ...] = (),
    target_output_delta: int | None = None,
) -> tuple[ReverseTailPath, ...]:
    start_limit = int(candidate_start_relative_bit)
    end_bit = int(candidate_end_relative_bit)
    if end_bit <= start_limit or max_paths <= 0 or max_tokens <= 0:
        return ()
    token_options = _reverse_token_options(
        state,
        distance_hints=tuple(int(item) for item in distance_hints if int(item) > 0),
        max_options=max_token_options,
    )
    if not token_options:
        return ()

    beam: list[ReverseTailPath] = [
        ReverseTailPath(end_bit, (), 0, 0, 0, "empty"),
    ]
    completed: list[ReverseTailPath] = []
    seen: set[tuple[int, tuple[int | None, ...]]] = set()

    def score_path(path: ReverseTailPath) -> int:
        penalty = 0
        if target_output_delta is not None:
            penalty = min(1024, abs(int(target_output_delta) - int(path.output_delta)) * 4)
        return int(path.score) + penalty + max(0, int(path.start_relative_bit) - start_limit)

    for _depth in range(int(max_tokens)):
        next_beam: list[ReverseTailPath] = []
        for path in beam:
            for token in token_options:
                token_len = len(token.bits)
                next_start = int(path.start_relative_bit) - token_len
                if next_start < start_limit:
                    continue
                bits = token.bits + path.bits
                key = (next_start, bits)
                if key in seen:
                    continue
                seen.add(key)
                next_path = ReverseTailPath(
                    next_start,
                    bits,
                    int(path.token_count) + 1,
                    int(path.output_delta) + int(token.output_delta),
                    int(path.score) + int(token.score),
                    token.reason,
                )
                completed.append(next_path)
                next_beam.append(next_path)
        if not next_beam:
            break
        beam = sorted(next_beam, key=score_path)[: max(16, int(max_paths))]
    return tuple(sorted(completed, key=score_path)[: max(1, int(max_paths))])
