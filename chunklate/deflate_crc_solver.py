from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import itertools
import zlib
from typing import Callable, Iterable

from . import deflate_probe


CRC32_MASK = 0xFFFFFFFF
DEFAULT_MAX_SKELETONS_PER_POSITION = 2048
DEFAULT_MAX_SOLUTIONS = 128
DEFAULT_SUFFIX_BITS = 128
DEFAULT_MAX_BRANCH_TOKENS = 256
DEFAULT_MAX_EXPANSIONS = 1_000
DEFAULT_SEMANTIC_EXTRA_ASSIGNMENTS = 16
DEFAULT_SEMANTIC_BEAM_WIDTH = 512
DEFAULT_SEMANTIC_EXPANSIONS = 1_500
DEFAULT_SEMANTIC_MAX_SKELETONS = 16
DEFAULT_SEMANTIC_SOLUTIONS_PER_SKELETON = 16
DEFLATE_HISTORY_SIZE = 32768
_HISTORY_CACHE_LIMIT = 512
_HISTORY_CACHE: dict[tuple[int, int, int, int, int, str], deflate_probe.DeflateHistoryState | None] = {}


@dataclass(frozen=True)
class _TokenTemplate:
    score: int
    output_delta: int
    bits: tuple[int | None, ...]


@dataclass(frozen=True)
class _SemanticPath:
    score: int
    symbol_count: int
    output_delta: int
    order: int
    bits: tuple[int | None, ...]
    output_tail: bytes
    tail_start: int
    output_offset: int


def _cached_history_state(
    payload: bytes,
    position: int,
    trace: deflate_probe.DeflateTrace,
) -> deflate_probe.DeflateHistoryState | None:
    key = (
        hash(payload),
        len(payload),
        int(position),
        int(trace.compressed_size),
        int(trace.decompressed_size),
        trace.status,
    )
    if key not in _HISTORY_CACHE:
        if len(_HISTORY_CACHE) >= _HISTORY_CACHE_LIMIT:
            _HISTORY_CACHE.clear()
        _HISTORY_CACHE[key] = deflate_probe.huffman_history_state_before_byte_boundary(
            payload,
            int(position),
            trace=trace,
        )
    return _HISTORY_CACHE[key]


def crc32_affine_rows(start_crc: int, end_crc: int, byte_count: int) -> tuple[tuple[int, int], ...]:
    byte_count = int(byte_count)
    if byte_count < 0:
        raise ValueError("byte_count must be non-negative")
    variable_count = byte_count * 8
    start_crc = int(start_crc) & CRC32_MASK
    end_crc = int(end_crc) & CRC32_MASK
    zero = b"\x00" * byte_count
    zero_end = zlib.crc32(zero, start_crc) & CRC32_MASK
    delta = end_crc ^ zero_end
    columns: list[int] = []
    for bit_index in range(variable_count):
        patch = (1 << bit_index).to_bytes(byte_count, "little")
        columns.append((zlib.crc32(patch, start_crc) & CRC32_MASK) ^ zero_end)

    rows: list[tuple[int, int]] = []
    for crc_bit in range(32):
        row = 0
        for variable_index, column in enumerate(columns):
            if column & (1 << crc_bit):
                row |= 1 << variable_index
        rows.append((row, (delta >> crc_bit) & 1))
    return tuple(rows)


def solve_gf2(
    rows: Iterable[int] | Iterable[tuple[int, int]],
    rhs: Iterable[int] | None,
    variable_count: int,
    *,
    max_solutions: int = DEFAULT_MAX_SOLUTIONS,
) -> tuple[int, ...]:
    variable_count = int(variable_count)
    if variable_count < 0:
        raise ValueError("variable_count must be non-negative")
    if max_solutions <= 0:
        return ()

    if rhs is None:
        equations = [(int(row), int(value) & 1) for row, value in rows]  # type: ignore[misc]
    else:
        equations = [(int(row), int(value) & 1) for row, value in zip(rows, rhs)]  # type: ignore[arg-type]

    mask_limit = (1 << variable_count) - 1 if variable_count else 0
    basis: dict[int, tuple[int, int]] = {}
    for row, value in equations:
        row &= mask_limit
        value &= 1
        while row:
            pivot = row.bit_length() - 1
            existing = basis.get(pivot)
            if existing is None:
                basis[pivot] = (row, value)
                break
            row ^= existing[0]
            value ^= existing[1]
        else:
            if value:
                return ()

    pivots = set(basis)
    free_vars = [index for index in range(variable_count) if index not in pivots]

    def complete_solution(free_value: int) -> int:
        solution = 0
        for bit_index, variable_index in enumerate(free_vars):
            if free_value & (1 << bit_index):
                solution |= 1 << variable_index
        for pivot in sorted(pivots):
            row, value = basis[pivot]
            known = (row & ~(1 << pivot)) & solution
            if (known.bit_count() & 1) ^ value:
                solution |= 1 << pivot
            else:
                solution &= ~(1 << pivot)
        return solution & mask_limit

    if not free_vars:
        return (complete_solution(0),)

    solutions: list[int] = []
    free_count = len(free_vars)
    for weight in range(free_count + 1):
        for combination in itertools.combinations(range(free_count), weight):
            free_value = 0
            for bit_index in combination:
                free_value |= 1 << bit_index
            solutions.append(complete_solution(free_value))
            if len(solutions) >= int(max_solutions):
                return tuple(solutions)
    return tuple(solutions)


def _payload_bit(payload: bytes, bit_offset: int) -> int | None:
    byte_offset = int(bit_offset) // 8
    if byte_offset < 0 or byte_offset >= len(payload):
        return None
    return (payload[byte_offset] >> (int(bit_offset) % 8)) & 1


def _template_bits(parts: Iterable[tuple[int, ...] | int]) -> tuple[int | None, ...]:
    bits: list[int | None] = []
    for part in parts:
        if isinstance(part, int):
            bits.extend([None] * int(part))
        else:
            bits.extend(int(bit) & 1 for bit in part)
    return tuple(bits)


def _token_templates(state: deflate_probe.DeflateHuffmanState) -> tuple[_TokenTemplate, ...]:
    literal_codes = deflate_probe._symbol_codes(state.literal_table)
    distance_codes = deflate_probe._symbol_codes(state.distance_table)
    templates: list[_TokenTemplate] = []
    match_bias = int(state.output_offset) > 1024
    for symbol, (code, width) in literal_codes.items():
        if symbol < 256:
            bits = _template_bits((deflate_probe._bits_for_code(code, width),))
            score = int(width) * 8 + (32 if match_bias else 0)
            templates.append(_TokenTemplate(score, 1, bits))
            continue
        if not (257 <= symbol <= 285) or state.output_offset <= 0:
            continue
        length_index = symbol - 257
        length_bits = deflate_probe._bits_for_code(code, width)
        output_delta = deflate_probe.LENGTH_BASES[length_index]
        length_extra = deflate_probe.LENGTH_EXTRAS[length_index]
        for distance_symbol, (distance_code, distance_width) in distance_codes.items():
            if distance_symbol >= len(deflate_probe.DISTANCE_BASES):
                continue
            if deflate_probe.DISTANCE_BASES[distance_symbol] > state.output_offset:
                continue
            distance_extra = deflate_probe.DISTANCE_EXTRAS[distance_symbol]
            bits = _template_bits(
                (
                    length_bits,
                    length_extra,
                    deflate_probe._bits_for_code(distance_code, distance_width),
                    distance_extra,
                )
            )
            extra_bits = length_extra + distance_extra
            score = (int(width) + int(distance_width)) * 8 + min(8, extra_bits)
            if not match_bias:
                score += 16
            templates.append(_TokenTemplate(score, output_delta, bits))
    return tuple(
        sorted(
            templates,
            key=lambda item: (
                item.score,
                len(item.bits),
                sum(1 for bit in item.bits if bit is None),
                item.bits,
            ),
        )
    )


def _known_relative_bit(
    payload: bytes,
    state_bit_offset: int,
    relative_bit: int,
    fixed_bit_count: int,
    candidate_bit_count: int,
    suffix_payload_bit_offset: int | None,
    suffix_bit_count: int,
) -> int | None:
    relative_bit = int(relative_bit)
    fixed_bit_count = int(fixed_bit_count)
    candidate_bit_count = int(candidate_bit_count)
    if relative_bit < fixed_bit_count:
        return _payload_bit(payload, int(state_bit_offset) + relative_bit)
    suffix_start = fixed_bit_count + candidate_bit_count
    if relative_bit < suffix_start:
        return None
    if suffix_payload_bit_offset is None:
        return None
    suffix_index = relative_bit - suffix_start
    if suffix_index >= max(0, int(suffix_bit_count)):
        return None
    return _payload_bit(payload, int(suffix_payload_bit_offset) + suffix_index)


def _candidate_fixed_bit_count(
    start_relative_bit: int,
    bits: tuple[int | None, ...],
    fixed_bit_count: int,
    candidate_bit_count: int,
) -> int:
    count = 0
    candidate_start = int(fixed_bit_count)
    candidate_end = candidate_start + int(candidate_bit_count)
    for offset, bit in enumerate(bits):
        absolute = int(start_relative_bit) + offset
        if bit is not None and candidate_start <= absolute < candidate_end:
            count += 1
    return count


@lru_cache(maxsize=128)
def _huffman_prefixes_cached(items: tuple[tuple[tuple[int, int], int], ...]) -> frozenset[tuple[int, int]]:
    prefixes: set[tuple[int, int]] = set()
    for (code, width), _symbol in items:
        for prefix_width in range(1, int(width)):
            prefixes.add((int(code) & ((1 << prefix_width) - 1), prefix_width))
    return frozenset(prefixes)


def _huffman_prefixes(table: dict[tuple[int, int], int]) -> frozenset[tuple[int, int]]:
    return _huffman_prefixes_cached(tuple(sorted(table.items())))


def _decode_symbol_options(
    payload: bytes,
    state_bit_offset: int,
    start_relative_bit: int,
    table: dict[tuple[int, int], int],
    max_bits: int,
    fixed_bit_count: int,
    candidate_bit_count: int,
    suffix_payload_bit_offset: int | None,
    suffix_bit_count: int,
    max_results: int | None = None,
) -> tuple[tuple[int, tuple[int, ...]], ...]:
    prefixes = _huffman_prefixes(table)
    partials: tuple[tuple[int, tuple[int, ...]], ...] = ((0, ()),)
    results: list[tuple[int, tuple[int, ...]]] = []
    for width in range(1, int(max_bits) + 1):
        next_partials: list[tuple[int, tuple[int, ...]]] = []
        for code, bits in partials:
            known = _known_relative_bit(
                payload,
                state_bit_offset,
                int(start_relative_bit) + width - 1,
                fixed_bit_count,
                candidate_bit_count,
                suffix_payload_bit_offset,
                suffix_bit_count,
            )
            choices = (0, 1) if known is None else (known,)
            for bit in choices:
                next_code = int(code) | ((int(bit) & 1) << (width - 1))
                next_bits = bits + (int(bit) & 1,)
                symbol = table.get((next_code, width))
                if symbol is not None:
                    results.append((symbol, next_bits))
                    if max_results is not None and len(results) >= int(max_results):
                        return tuple(results)
                elif (next_code, width) in prefixes:
                    next_partials.append((next_code, next_bits))
        partials = tuple(next_partials)
        if not partials:
            break
    return tuple(results)


def _extra_bits_template(
    payload: bytes,
    state_bit_offset: int,
    start_relative_bit: int,
    width: int,
    fixed_bit_count: int,
    candidate_bit_count: int,
    suffix_payload_bit_offset: int | None,
    suffix_bit_count: int,
) -> tuple[int | None, ...]:
    bits: list[int | None] = []
    for offset in range(int(width)):
        bits.append(
            _known_relative_bit(
                payload,
                state_bit_offset,
                int(start_relative_bit) + offset,
                fixed_bit_count,
                candidate_bit_count,
                suffix_payload_bit_offset,
                suffix_bit_count,
            )
        )
    return tuple(bits)


def _known_extra_min_value(bits: tuple[int | None, ...]) -> int:
    value = 0
    for index, bit in enumerate(bits):
        if bit is not None and int(bit):
            value |= 1 << index
    return value


def _extra_bits_for_value(value: int, width: int) -> tuple[int, ...]:
    return tuple((int(value) >> index) & 1 for index in range(int(width)))


def _extra_bits_match(value: int, bits: tuple[int | None, ...]) -> bool:
    for index, bit in enumerate(bits):
        if bit is not None and ((int(value) >> index) & 1) != int(bit):
            return False
    return True


def _extra_assignment_options(
    bits: tuple[int | None, ...],
    *,
    preferred_values: Iterable[int] = (),
    limit: int = DEFAULT_SEMANTIC_EXTRA_ASSIGNMENTS,
) -> tuple[tuple[int, tuple[int, ...], int], ...]:
    width = len(bits)
    if width <= 0:
        return ((0, (), 0),)
    max_value = (1 << width) - 1
    candidates: list[int] = []
    for value in preferred_values:
        value = int(value)
        if 0 <= value <= max_value:
            candidates.extend((value, value - 1, value + 1))
    candidates.extend((0, _known_extra_min_value(bits), max_value))
    if width <= 8:
        candidates.extend(range(max_value + 1))
    else:
        low = _known_extra_min_value(bits)
        candidates.extend(range(low, min(max_value + 1, low + max(32, int(limit) * 4))))
    seen: set[int] = set()
    options: list[tuple[int, tuple[int, ...], int]] = []
    for value in candidates:
        value = int(value)
        if value < 0 or value > max_value or value in seen:
            continue
        seen.add(value)
        if not _extra_bits_match(value, bits):
            continue
        options.append((value, _extra_bits_for_value(value, width), len(options)))
        if len(options) >= max(1, int(limit)):
            break
    return tuple(options)


def _distance_range(symbol: int) -> tuple[int, int] | None:
    if int(symbol) >= len(deflate_probe.DISTANCE_BASES):
        return None
    base = deflate_probe.DISTANCE_BASES[int(symbol)]
    extra_bits = deflate_probe.DISTANCE_EXTRAS[int(symbol)]
    return base, base + ((1 << extra_bits) - 1 if extra_bits else 0)


def _distance_hint_penalty(symbol: int, distance_hints: tuple[int, ...]) -> int:
    value_range = _distance_range(int(symbol))
    if value_range is None or not distance_hints:
        return 0
    start, end = value_range
    best = 1 << 30
    for hint in distance_hints:
        hint = int(hint)
        if hint <= 0:
            continue
        if start <= hint <= end:
            return 0
        best = min(best, abs(start - hint), abs(end - hint))
    return min(best, 4096)


def _distance_value_penalty(distance: int, distance_hints: tuple[int, ...], tail_length: int) -> int:
    distance = int(distance)
    penalty = 0 if distance <= int(tail_length) else 4096
    hints = tuple(int(item) for item in distance_hints if int(item) > 0)
    if not hints:
        return penalty
    best = min(abs(distance - hint) for hint in hints)
    return penalty + min(1024, best // 8)


def _select_contextual_templates(
    templates: Iterable[_TokenTemplate],
    *,
    limit: int,
) -> tuple[_TokenTemplate, ...]:
    limit = max(1, int(limit))
    ordered = tuple(templates)
    if len(ordered) <= limit:
        return tuple(ordered)

    selected: list[_TokenTemplate] = []
    seen: set[tuple[int, int, tuple[int | None, ...]]] = set()

    def add(template: _TokenTemplate) -> None:
        key = (int(template.score), int(template.output_delta), template.bits)
        if key in seen or len(selected) >= limit:
            return
        seen.add(key)
        selected.append(template)

    for template in ordered[: max(1, limit // 2)]:
        add(template)

    literal_quota = max(4, min(limit // 3, limit - len(selected)))
    literal_added = 0
    for template in ordered:
        if int(template.output_delta) != 1:
            continue
        before = len(selected)
        add(template)
        if len(selected) != before:
            literal_added += 1
        if literal_added >= literal_quota or len(selected) >= limit:
            break

    for template in ordered:
        add(template)
        if len(selected) >= limit:
            break
    return tuple(selected)


def _select_semantic_paths(
    paths: Iterable[_SemanticPath],
    *,
    limit: int,
    literal_output_delta: int,
) -> tuple[_SemanticPath, ...]:
    limit = max(1, int(limit))
    ordered = tuple(paths)
    if len(ordered) <= limit:
        return ordered

    selected: list[_SemanticPath] = []
    selected_orders: set[int] = set()

    def add(path: _SemanticPath) -> None:
        if int(path.order) in selected_orders or len(selected) >= limit:
            return
        selected_orders.add(int(path.order))
        selected.append(path)

    for path in ordered[: max(1, limit // 2)]:
        add(path)

    literal_quota = max(4, min(limit // 3, limit - len(selected)))
    literal_added = 0
    for path in ordered:
        if int(path.output_delta) != int(literal_output_delta):
            continue
        before = len(selected)
        add(path)
        if len(selected) != before:
            literal_added += 1
        if literal_added >= literal_quota or len(selected) >= limit:
            break

    for path in ordered:
        add(path)
        if len(selected) >= limit:
            break
    return tuple(selected)


def _target_output_penalty(
    bit_length: int,
    output_delta: int,
    *,
    target_output_delta: int | None,
    target_bit_count: int,
    scale: int,
    cap: int,
) -> int:
    if target_output_delta is None or int(target_bit_count) <= 0:
        return 0
    bit_length = int(bit_length)
    output_delta = int(output_delta)
    target_output_delta = int(target_output_delta)
    if bit_length >= int(target_bit_count):
        return min(int(cap), max(0, target_output_delta - output_delta) * int(scale))
    progress = min(1.0, max(0.0, bit_length / float(target_bit_count)))
    expected = target_output_delta * progress
    return min(int(cap), int(abs(output_delta - expected) * int(scale)))


def _append_output_tail(
    output_tail: bytes,
    tail_start: int,
    output_offset: int,
    values: bytes,
    *,
    history_size: int = DEFLATE_HISTORY_SIZE,
) -> tuple[bytes, int, int]:
    if not values:
        return output_tail, int(tail_start), int(output_offset)
    next_output_offset = int(output_offset) + len(values)
    combined = output_tail + values
    if len(combined) > int(history_size):
        combined = combined[-int(history_size) :]
    return combined, max(0, next_output_offset - len(combined)), next_output_offset


def _copy_from_output_tail(
    output_tail: bytes,
    tail_start: int,
    output_offset: int,
    distance: int,
    length: int,
    *,
    history_size: int = DEFLATE_HISTORY_SIZE,
) -> tuple[bytes, bytes, int, int] | None:
    distance = int(distance)
    length = int(length)
    if distance <= 0 or length < 0 or distance > int(output_offset):
        return None
    current = bytearray(output_tail)
    current_start = int(tail_start)
    current_output_offset = int(output_offset)
    source_offset = int(output_offset) - distance
    copied = bytearray()
    for _ in range(length):
        source_index = source_offset - current_start
        if source_index < 0 or source_index >= len(current):
            return None
        value = current[source_index]
        copied.append(value)
        current.append(value)
        current_output_offset += 1
        source_offset += 1
        overflow = len(current) - int(history_size)
        if overflow > 0:
            del current[:overflow]
            current_start += overflow
    return bytes(copied), bytes(current), current_start, current_output_offset


def _contextual_token_templates(
    payload: bytes,
    state: deflate_probe.DeflateHuffmanState,
    start_relative_bit: int,
    fixed_bit_count: int,
    candidate_bit_count: int,
    suffix_payload_bit_offset: int | None,
    suffix_bit_count: int,
    output_delta: int,
    *,
    max_branch_tokens: int,
    distance_hints: tuple[int, ...] = (),
    target_output_delta: int | None = None,
    target_bit_count: int | None = None,
) -> tuple[_TokenTemplate, ...]:
    max_symbol_options = max(8, int(max_branch_tokens) * 4)
    match_bias = int(state.output_offset) + int(output_delta) > 1024
    literal_options = _decode_symbol_options(
        payload,
        int(state.bit_offset),
        int(start_relative_bit),
        state.literal_table,
        state.literal_max_bits,
        fixed_bit_count,
        candidate_bit_count,
        suffix_payload_bit_offset,
        suffix_bit_count,
        max_results=max_symbol_options,
    )
    literal_options = tuple(
        sorted(
            literal_options,
            key=lambda item: (
                0 if match_bias and 257 <= int(item[0]) <= 285 else 1,
                len(item[1]),
                int(item[0]),
            ),
        )[: max(1, int(max_branch_tokens))]
    )
    templates: list[_TokenTemplate] = []

    def output_penalty(bits: tuple[int | None, ...], next_output_delta: int) -> int:
        return _target_output_penalty(
            int(start_relative_bit) + len(bits),
            int(next_output_delta),
            target_output_delta=target_output_delta,
            target_bit_count=int(target_bit_count or 0),
            scale=8,
            cap=512,
        )

    for symbol, literal_bits in literal_options:
        if symbol < 256:
            bits: tuple[int | None, ...] = literal_bits
            fixed_inside = _candidate_fixed_bit_count(
                start_relative_bit,
                bits,
                fixed_bit_count,
                candidate_bit_count,
            )
            score = (
                len(bits) * 8
                - fixed_inside * 3
                + (96 if match_bias else 0)
                + output_penalty(bits, int(output_delta) + 1)
            )
            templates.append(_TokenTemplate(score, 1, bits))
            continue
        if not (257 <= symbol <= 285):
            continue
        length_index = int(symbol) - 257
        length_extra = _extra_bits_template(
            payload,
            int(state.bit_offset),
            int(start_relative_bit) + len(literal_bits),
            deflate_probe.LENGTH_EXTRAS[length_index],
            fixed_bit_count,
            candidate_bit_count,
            suffix_payload_bit_offset,
            suffix_bit_count,
        )
        distance_start = int(start_relative_bit) + len(literal_bits) + len(length_extra)
        distance_options = _decode_symbol_options(
            payload,
            int(state.bit_offset),
            distance_start,
            state.distance_table,
            state.distance_max_bits,
            fixed_bit_count,
            candidate_bit_count,
            suffix_payload_bit_offset,
            suffix_bit_count,
            max_results=max_symbol_options,
        )
        distance_options = tuple(
            sorted(
                distance_options,
                key=lambda item: (
                    len(item[1]),
                    _distance_hint_penalty(int(item[0]), distance_hints),
                    (
                        deflate_probe.DISTANCE_BASES[item[0]]
                        if int(item[0]) < len(deflate_probe.DISTANCE_BASES)
                        else 1 << 30
                    ),
                    int(item[0]),
                ),
            )[: max(1, int(max_branch_tokens))]
        )
        length_delta = deflate_probe.LENGTH_BASES[length_index] + _known_extra_min_value(length_extra)
        produced_output = int(state.output_offset) + int(output_delta)
        for distance_symbol, distance_bits in distance_options:
            if distance_symbol >= len(deflate_probe.DISTANCE_BASES):
                continue
            distance_extra = _extra_bits_template(
                payload,
                int(state.bit_offset),
                distance_start + len(distance_bits),
                deflate_probe.DISTANCE_EXTRAS[distance_symbol],
                fixed_bit_count,
                candidate_bit_count,
                suffix_payload_bit_offset,
                suffix_bit_count,
            )
            min_distance = deflate_probe.DISTANCE_BASES[distance_symbol] + _known_extra_min_value(distance_extra)
            if min_distance > produced_output:
                continue
            bits = literal_bits + length_extra + distance_bits + distance_extra
            fixed_inside = _candidate_fixed_bit_count(
                start_relative_bit,
                bits,
                fixed_bit_count,
                candidate_bit_count,
            )
            unknown_extras = sum(1 for bit in length_extra + distance_extra if bit is None)
            hint_penalty = _distance_hint_penalty(int(distance_symbol), distance_hints)
            output_bonus = min(40, int(length_delta) * 2)
            score = (
                len(bits) * 6
                + min(24, unknown_extras * 2)
                - fixed_inside * 3
                + min(24, hint_penalty // 256)
                - output_bonus
                + output_penalty(bits, int(output_delta) + int(length_delta))
            )
            if not match_bias:
                score += 24
            templates.append(_TokenTemplate(score, length_delta, bits))
    ordered = sorted(
        templates,
        key=lambda item: (
            item.score,
            len(item.bits),
            -_candidate_fixed_bit_count(
                start_relative_bit,
                item.bits,
                fixed_bit_count,
                candidate_bit_count,
            ),
            item.bits,
        ),
    )
    return _select_contextual_templates(ordered, limit=max_branch_tokens)


def _bit_is_compatible(
    payload: bytes,
    state_bit_offset: int,
    relative_bit: int,
    fixed_bit_count: int,
    candidate_bit_count: int,
    suffix_payload_bit_offset: int | None,
    bit: int | None,
) -> bool:
    if bit is None:
        return True
    candidate_index = int(relative_bit) - int(fixed_bit_count)
    if 0 <= candidate_index < int(candidate_bit_count):
        return True
    if relative_bit < fixed_bit_count:
        payload_bit = _payload_bit(payload, int(state_bit_offset) + int(relative_bit))
    elif suffix_payload_bit_offset is not None:
        suffix_index = int(relative_bit) - int(fixed_bit_count) - int(candidate_bit_count)
        payload_bit = _payload_bit(payload, int(suffix_payload_bit_offset) + suffix_index)
    else:
        payload_bit = None
    return payload_bit is not None and payload_bit == int(bit)


def _bits_compatible(
    payload: bytes,
    state: deflate_probe.DeflateHuffmanState,
    bits: tuple[int | None, ...],
    fixed_bit_count: int,
    candidate_bit_count: int,
    suffix_payload_bit_offset: int | None,
) -> bool:
    for index, bit in enumerate(bits):
        if not _bit_is_compatible(
            payload,
            int(state.bit_offset),
            index,
            fixed_bit_count,
            candidate_bit_count,
            suffix_payload_bit_offset,
            bit,
        ):
            return False
    return True


def _appended_bits_compatible(
    payload: bytes,
    state: deflate_probe.DeflateHuffmanState,
    start_relative_bit: int,
    bits: tuple[int | None, ...],
    fixed_bit_count: int,
    candidate_bit_count: int,
    suffix_payload_bit_offset: int | None,
) -> bool:
    for offset, bit in enumerate(bits):
        if not _bit_is_compatible(
            payload,
            int(state.bit_offset),
            int(start_relative_bit) + offset,
            fixed_bit_count,
            candidate_bit_count,
            suffix_payload_bit_offset,
            bit,
        ):
            return False
    return True


def _iter_symbol_skeletons(
    payload: bytes,
    state: deflate_probe.DeflateHuffmanState,
    fixed_bit_count: int,
    candidate_bit_count: int,
    suffix_payload_bit_offset: int | None,
    suffix_bit_count: int,
    *,
    max_skeletons: int,
    max_branch_tokens: int,
    max_symbols: int,
    target_output_delta: int | None = None,
    max_expansions: int = DEFAULT_MAX_EXPANSIONS,
    distance_hints: tuple[int, ...] = (),
) -> Iterable[tuple[int | None, ...]]:
    required_bits = int(fixed_bit_count) + int(candidate_bit_count) + max(0, int(suffix_bit_count))
    target_bit_count = max(1, int(fixed_bit_count) + int(candidate_bit_count))
    beam: list[tuple[int, int, int, int, tuple[int | None, ...]]] = [(0, 0, 0, 0, ())]
    beam_width = max(32, min(512, max(32, int(max_expansions) // 8)))
    order = 1
    yielded = 0
    expansions = 0

    def priority(score: int, bits: tuple[int | None, ...], output_delta: int) -> int:
        return int(score) + output_closeness(bits, output_delta) + max(0, target_bit_count - min(len(bits), target_bit_count))

    def output_closeness(bits: tuple[int | None, ...], output_delta: int) -> int:
        return _target_output_penalty(
            len(bits),
            output_delta,
            target_output_delta=target_output_delta,
            target_bit_count=target_bit_count,
            scale=8,
            cap=512,
        )

    def prune_next_states(
        states: list[tuple[int, int, int, int, int, tuple[int | None, ...]]],
    ) -> list[tuple[int, int, int, int, int, tuple[int | None, ...]]]:
        max_pending = max(64, beam_width * 8)
        if len(states) <= max_pending:
            return states
        by_priority = sorted(states, key=lambda item: (item[0], item[4]))
        by_output = sorted(
            states,
            key=lambda item: (
                output_closeness(item[5], item[3]),
                abs(len(item[5]) - target_bit_count),
                item[1],
                item[4],
            ),
        )
        selected: list[tuple[int, int, int, int, int, tuple[int | None, ...]]] = []
        selected_orders: set[int] = set()

        def add(item: tuple[int, int, int, int, int, tuple[int | None, ...]]) -> None:
            if item[4] in selected_orders or len(selected) >= max(64, beam_width * 4):
                return
            selected_orders.add(item[4])
            selected.append(item)

        for item in by_priority:
            add(item)
            if len(selected) >= max(64, beam_width * 2):
                break
        for item in by_output:
            add(item)
            if len(selected) >= max(64, beam_width * 4):
                break
        return selected

    while beam and yielded < int(max_skeletons) and expansions < int(max_expansions):
        completed: list[tuple[int, int, tuple[int | None, ...]]] = []
        next_states: list[tuple[int, int, int, int, int, tuple[int | None, ...]]] = []
        for score, symbol_count, output_delta, _order, bits in beam:
            if len(bits) >= required_bits:
                completed.append((priority(score, bits, output_delta), order, bits[:required_bits]))
                order += 1
                continue
            if symbol_count >= int(max_symbols):
                continue
            expansions += 1
            templates = _contextual_token_templates(
                payload,
                state,
                len(bits),
                fixed_bit_count,
                candidate_bit_count,
                suffix_payload_bit_offset,
                suffix_bit_count,
                output_delta,
                max_branch_tokens=max_branch_tokens,
                distance_hints=distance_hints,
                target_output_delta=target_output_delta,
                target_bit_count=target_bit_count,
            )
            for template in templates:
                next_bits = bits + template.bits
                next_score = score + int(template.score)
                next_output_delta = output_delta + int(template.output_delta)
                next_priority = priority(next_score, next_bits, next_output_delta)
                if len(next_bits) >= required_bits:
                    completed.append((next_priority, order, next_bits[:required_bits]))
                else:
                    next_states.append(
                        (
                            next_priority,
                            next_score,
                            symbol_count + 1,
                            next_output_delta,
                            order,
                            next_bits,
                        )
                    )
                order += 1
            next_states = prune_next_states(next_states)
            if expansions >= int(max_expansions):
                break
        for _priority, _order, bits in sorted(completed, key=lambda item: (item[0], item[1])):
            yielded += 1
            yield bits
            if yielded >= int(max_skeletons):
                return
        if not next_states:
            return
        by_priority = sorted(next_states, key=lambda item: (item[0], item[4]))
        by_output = sorted(
            next_states,
            key=lambda item: (
                output_closeness(item[5], item[3]),
                abs(len(item[5]) - target_bit_count),
                item[1],
                item[4],
            ),
        )
        selected: list[tuple[int, int, int, int, tuple[int | None, ...]]] = []
        selected_orders: set[int] = set()
        seen_keys: set[tuple[int, int, int]] = set()

        def add_item(item: tuple[int, int, int, int, int, tuple[int | None, ...]], *, enforce_key: bool) -> None:
            _priority, score, symbol_count, output_delta, state_order, bits = item
            if state_order in selected_orders:
                return
            key = (
                min(len(bits), target_bit_count) // 8,
                int(output_delta) // 2,
                min(7, max(0, len(bits) - target_bit_count) // 8),
            )
            if enforce_key and key in seen_keys and len(selected) >= beam_width // 2:
                return
            seen_keys.add(key)
            selected_orders.add(state_order)
            selected.append((score, symbol_count, output_delta, state_order, bits))

        for item in by_priority:
            add_item(item, enforce_key=True)
            if len(selected) >= beam_width // 2:
                break
        for item in by_output:
            add_item(item, enforce_key=False)
            if len(selected) >= beam_width:
                break
        beam = selected


def _semantic_output_penalty(
    bits: tuple[int | None, ...],
    output_delta: int,
    *,
    target_output_delta: int | None,
    target_bit_count: int,
) -> int:
    return _target_output_penalty(
        len(bits),
        output_delta,
        target_output_delta=target_output_delta,
        target_bit_count=target_bit_count,
        scale=8,
        cap=1024,
    )


def _semantic_priority(
    path: _SemanticPath,
    *,
    target_output_delta: int | None,
    target_bit_count: int,
) -> int:
    return (
        int(path.score)
        + _semantic_output_penalty(
            path.bits,
            path.output_delta,
            target_output_delta=target_output_delta,
            target_bit_count=target_bit_count,
        )
        + max(0, int(target_bit_count) - min(len(path.bits), int(target_bit_count)))
    )


def _semantic_length_options(
    length_index: int,
    bits: tuple[int | None, ...],
    *,
    output_delta: int,
    target_output_delta: int | None,
    limit: int,
) -> tuple[tuple[int, tuple[int, ...], int], ...]:
    base = deflate_probe.LENGTH_BASES[int(length_index)]
    preferred: list[int] = []
    if target_output_delta is not None:
        remaining = max(0, int(target_output_delta) - int(output_delta))
        preferred.extend((remaining - base, remaining - base - 1, remaining - base + 1))
    preferred.extend((0, 1, 2))
    options = _extra_assignment_options(bits, preferred_values=preferred, limit=limit)
    ranked: list[tuple[int, tuple[int, ...], int]] = []
    for value, concrete_bits, rank in options:
        length = base + int(value)
        target_penalty = 0
        if target_output_delta is not None:
            target_penalty = abs((int(output_delta) + length) - int(target_output_delta))
        ranked.append((value, concrete_bits, int(rank) + min(128, target_penalty * 4)))
    return tuple(sorted(ranked, key=lambda item: (item[2], item[0]))[: max(1, int(limit))])


def _semantic_distance_options(
    distance_symbol: int,
    bits: tuple[int | None, ...],
    *,
    output_tail: bytes,
    output_offset: int,
    distance_hints: tuple[int, ...],
    limit: int,
) -> tuple[tuple[int, tuple[int, ...], int], ...]:
    if int(distance_symbol) >= len(deflate_probe.DISTANCE_BASES):
        return ()
    base = deflate_probe.DISTANCE_BASES[int(distance_symbol)]
    max_extra = (1 << deflate_probe.DISTANCE_EXTRAS[int(distance_symbol)]) - 1
    preferred: list[int] = []
    for hint in distance_hints:
        preferred.extend((int(hint) - base, int(hint) - base - 1, int(hint) - base + 1))
    preferred.extend((0, min(max_extra, max(0, len(output_tail) - base)), max_extra))
    options = _extra_assignment_options(bits, preferred_values=preferred, limit=max(limit * 2, limit))
    ranked: list[tuple[int, tuple[int, ...], int]] = []
    for value, concrete_bits, rank in options:
        distance = base + int(value)
        if distance <= 0 or distance > int(output_offset) or distance > len(output_tail):
            continue
        penalty = int(rank) + _distance_value_penalty(distance, distance_hints, len(output_tail))
        ranked.append((value, concrete_bits, penalty))
    return tuple(sorted(ranked, key=lambda item: (item[2], item[0]))[: max(1, int(limit))])


def _semantic_symbol_expansions(
    payload: bytes,
    state: deflate_probe.DeflateHuffmanState,
    path: _SemanticPath,
    fixed_bit_count: int,
    candidate_bit_count: int,
    suffix_payload_bit_offset: int | None,
    suffix_bit_count: int,
    *,
    max_branch_tokens: int,
    distance_hints: tuple[int, ...],
    target_output_delta: int | None,
    semantic_extra_assignments: int,
) -> tuple[_SemanticPath, ...]:
    start_relative_bit = len(path.bits)
    max_symbol_options = max(16, int(max_branch_tokens) * 4)
    literal_options = _decode_symbol_options(
        payload,
        int(state.bit_offset),
        start_relative_bit,
        state.literal_table,
        state.literal_max_bits,
        fixed_bit_count,
        candidate_bit_count,
        suffix_payload_bit_offset,
        suffix_bit_count,
        max_results=max_symbol_options,
    )
    literal_options = tuple(
        sorted(
            literal_options,
            key=lambda item: (
                0 if 257 <= int(item[0]) <= 285 else 1,
                len(item[1]),
                int(item[0]),
            ),
        )[: max(1, int(max_branch_tokens))]
    )
    output: list[_SemanticPath] = []
    order_base = int(path.order) * max(1, int(max_branch_tokens)) * 64
    order = order_base
    for symbol, literal_bits in literal_options:
        symbol = int(symbol)
        if symbol < 256:
            next_bits = path.bits + literal_bits
            output_tail, tail_start, output_offset = _append_output_tail(
                path.output_tail,
                path.tail_start,
                path.output_offset,
                bytes((symbol,)),
            )
            fixed_inside = _candidate_fixed_bit_count(
                start_relative_bit,
                literal_bits,
                fixed_bit_count,
                candidate_bit_count,
            )
            score = path.score + len(literal_bits) * 8 - fixed_inside * 3 + 64
            output.append(
                _SemanticPath(
                    score,
                    path.symbol_count + 1,
                    path.output_delta + 1,
                    order,
                    next_bits,
                    output_tail,
                    tail_start,
                    output_offset,
                )
            )
            order += 1
            continue
        if not (257 <= symbol <= 285):
            continue
        length_index = symbol - 257
        length_extra_template = _extra_bits_template(
            payload,
            int(state.bit_offset),
            start_relative_bit + len(literal_bits),
            deflate_probe.LENGTH_EXTRAS[length_index],
            fixed_bit_count,
            candidate_bit_count,
            suffix_payload_bit_offset,
            suffix_bit_count,
        )
        length_options = _semantic_length_options(
            length_index,
            length_extra_template,
            output_delta=path.output_delta,
            target_output_delta=target_output_delta,
            limit=semantic_extra_assignments,
        )
        for length_extra_value, length_extra_bits, length_penalty in length_options:
            length = deflate_probe.LENGTH_BASES[length_index] + int(length_extra_value)
            distance_start = start_relative_bit + len(literal_bits) + len(length_extra_bits)
            distance_options = _decode_symbol_options(
                payload,
                int(state.bit_offset),
                distance_start,
                state.distance_table,
                state.distance_max_bits,
                fixed_bit_count,
                candidate_bit_count,
                suffix_payload_bit_offset,
                suffix_bit_count,
                max_results=max_symbol_options,
            )
            distance_options = tuple(
                sorted(
                    distance_options,
                    key=lambda item: (
                        _distance_hint_penalty(int(item[0]), distance_hints),
                        len(item[1]),
                        int(item[0]),
                    ),
                )[: max(1, int(max_branch_tokens))]
            )
            for distance_symbol, distance_bits in distance_options:
                if int(distance_symbol) >= len(deflate_probe.DISTANCE_BASES):
                    continue
                distance_extra_template = _extra_bits_template(
                    payload,
                    int(state.bit_offset),
                    distance_start + len(distance_bits),
                    deflate_probe.DISTANCE_EXTRAS[int(distance_symbol)],
                    fixed_bit_count,
                    candidate_bit_count,
                    suffix_payload_bit_offset,
                    suffix_bit_count,
                )
                distance_options_concrete = _semantic_distance_options(
                    int(distance_symbol),
                    distance_extra_template,
                    output_tail=path.output_tail,
                    output_offset=path.output_offset,
                    distance_hints=distance_hints,
                    limit=semantic_extra_assignments,
                )
                for distance_extra_value, distance_extra_bits, distance_penalty in distance_options_concrete:
                    distance = deflate_probe.DISTANCE_BASES[int(distance_symbol)] + int(distance_extra_value)
                    copied = _copy_from_output_tail(
                        path.output_tail,
                        path.tail_start,
                        path.output_offset,
                        distance,
                        length,
                    )
                    if copied is None:
                        continue
                    _copied_bytes, output_tail, tail_start, output_offset = copied
                    token_bits: tuple[int | None, ...] = (
                        literal_bits
                        + tuple(length_extra_bits)
                        + distance_bits
                        + tuple(distance_extra_bits)
                    )
                    next_bits = path.bits + token_bits
                    fixed_inside = _candidate_fixed_bit_count(
                        start_relative_bit,
                        token_bits,
                        fixed_bit_count,
                        candidate_bit_count,
                    )
                    score = (
                        path.score
                        + len(token_bits) * 5
                        + int(length_penalty)
                        + int(distance_penalty)
                        - min(96, length * 4)
                        - fixed_inside * 3
                    )
                    output.append(
                        _SemanticPath(
                            score,
                            path.symbol_count + 1,
                            path.output_delta + length,
                            order,
                            next_bits,
                            output_tail,
                            tail_start,
                            output_offset,
                        )
                    )
                    order += 1
    ordered = sorted(
        output,
        key=lambda item: (
            item.score,
            _semantic_output_penalty(
                item.bits,
                item.output_delta,
                target_output_delta=target_output_delta,
                target_bit_count=max(1, fixed_bit_count + candidate_bit_count),
            ),
            item.order,
        ),
    )
    return _select_semantic_paths(
        ordered,
        limit=max(1, int(max_branch_tokens) * 2),
        literal_output_delta=int(path.output_delta) + 1,
    )


def _iter_semantic_symbol_skeletons(
    payload: bytes,
    history: deflate_probe.DeflateHistoryState,
    fixed_bit_count: int,
    candidate_bit_count: int,
    suffix_payload_bit_offset: int | None,
    suffix_bit_count: int,
    *,
    max_skeletons: int,
    max_branch_tokens: int,
    max_symbols: int,
    target_output_delta: int | None,
    distance_hints: tuple[int, ...],
    semantic_extra_assignments: int,
    semantic_beam_width: int,
    semantic_expansions: int,
) -> Iterable[tuple[int | None, ...]]:
    state = history.huffman
    required_bits = int(fixed_bit_count) + int(candidate_bit_count) + max(0, int(suffix_bit_count))
    target_bit_count = max(1, int(fixed_bit_count) + int(candidate_bit_count))
    beam: list[_SemanticPath] = [
        _SemanticPath(
            0,
            0,
            0,
            0,
            (),
            history.output_tail,
            history.tail_start,
            int(state.output_offset),
        )
    ]
    yielded = 0
    expansions = 0
    seen_completed: set[tuple[int | None, ...]] = set()

    def prune_next_paths(paths: list[_SemanticPath]) -> list[_SemanticPath]:
        max_pending = max(32, int(semantic_beam_width) * 8)
        if len(paths) <= max_pending:
            return paths
        ranked = sorted(
            paths,
            key=lambda item: (
                _semantic_priority(
                    item,
                    target_output_delta=target_output_delta,
                    target_bit_count=target_bit_count,
                ),
                _semantic_output_penalty(
                    item.bits,
                    item.output_delta,
                    target_output_delta=target_output_delta,
                    target_bit_count=target_bit_count,
                ),
                item.order,
            ),
        )
        return ranked[: max(32, int(semantic_beam_width) * 4)]

    while beam and yielded < int(max_skeletons) and expansions < int(semantic_expansions):
        completed: list[tuple[int, int, tuple[int | None, ...]]] = []
        next_paths: list[_SemanticPath] = []
        for path in beam:
            if len(path.bits) >= required_bits:
                skeleton = path.bits[:required_bits]
                completed.append(
                    (
                        _semantic_priority(
                            path,
                            target_output_delta=target_output_delta,
                            target_bit_count=target_bit_count,
                        ),
                        path.order,
                        skeleton,
                    )
                )
                continue
            if path.symbol_count >= int(max_symbols):
                continue
            expansions += 1
            for next_path in _semantic_symbol_expansions(
                payload,
                state,
                path,
                fixed_bit_count,
                candidate_bit_count,
                suffix_payload_bit_offset,
                suffix_bit_count,
                max_branch_tokens=max_branch_tokens,
                distance_hints=distance_hints,
                target_output_delta=target_output_delta,
                semantic_extra_assignments=semantic_extra_assignments,
            ):
                if len(next_path.bits) >= required_bits:
                    skeleton = next_path.bits[:required_bits]
                    completed.append(
                        (
                            _semantic_priority(
                                next_path,
                                target_output_delta=target_output_delta,
                                target_bit_count=target_bit_count,
                            ),
                            next_path.order,
                            skeleton,
                        )
                    )
                else:
                    next_paths.append(next_path)
            next_paths = prune_next_paths(next_paths)
            if expansions >= int(semantic_expansions):
                break
        for _priority, _order, skeleton in sorted(completed, key=lambda item: (item[0], item[1])):
            if skeleton in seen_completed:
                continue
            seen_completed.add(skeleton)
            yielded += 1
            yield skeleton
            if yielded >= int(max_skeletons):
                return
        if not next_paths:
            return
        by_priority = sorted(
            next_paths,
            key=lambda item: (
                _semantic_priority(
                    item,
                    target_output_delta=target_output_delta,
                    target_bit_count=target_bit_count,
                ),
                item.order,
            ),
        )
        by_output = sorted(
            next_paths,
            key=lambda item: (
                _semantic_output_penalty(
                    item.bits,
                    item.output_delta,
                    target_output_delta=target_output_delta,
                    target_bit_count=target_bit_count,
                ),
                abs(len(item.bits) - target_bit_count),
                item.score,
                item.order,
            ),
        )
        selected: list[_SemanticPath] = []
        selected_orders: set[int] = set()
        seen_keys: set[tuple[int, int, int]] = set()

        def add_path(path: _SemanticPath, *, enforce_key: bool) -> None:
            if path.order in selected_orders:
                return
            key = (
                min(len(path.bits), target_bit_count) // 8,
                int(path.output_delta) // 2,
                min(7, max(0, len(path.bits) - target_bit_count) // 8),
            )
            if enforce_key and key in seen_keys and len(selected) >= max(1, int(semantic_beam_width) // 2):
                return
            seen_keys.add(key)
            selected_orders.add(path.order)
            selected.append(path)

        for path in by_priority:
            add_path(path, enforce_key=True)
            if len(selected) >= max(1, int(semantic_beam_width) // 2):
                break
        for path in by_output:
            add_path(path, enforce_key=False)
            if len(selected) >= max(1, int(semantic_beam_width)):
                break
        beam = selected


def _skeleton_rows(
    bits: tuple[int | None, ...],
    fixed_bit_count: int,
    candidate_bit_count: int,
) -> tuple[tuple[int, int], ...]:
    rows: list[tuple[int, int]] = []
    for index, bit in enumerate(bits):
        if bit is None:
            continue
        candidate_index = int(index) - int(fixed_bit_count)
        if 0 <= candidate_index < int(candidate_bit_count):
            rows.append((1 << candidate_index, int(bit) & 1))
    return tuple(rows)


def _local_output_delta_target(
    trace: deflate_probe.DeflateTrace,
    fixed_bit_count: int,
    candidate_bit_count: int,
    requested_target: int | None,
) -> int | None:
    compressed_size = max(1, int(trace.compressed_size))
    decompressed_size = max(0, int(trace.decompressed_size))
    if decompressed_size <= 0:
        return requested_target
    local_bytes = max(1.0, (int(fixed_bit_count) + int(candidate_bit_count)) / 8.0)
    ratio = min(16.0, max(0.25, decompressed_size / float(compressed_size)))
    estimated = max(1, int(round(local_bytes * ratio)))
    if requested_target is None:
        return estimated
    requested_target = int(requested_target)
    if requested_target <= max(estimated * 2, estimated + 8):
        return requested_target
    return estimated


def solve_idat_crc_huffman(
    payload: bytes,
    position: int,
    edit_kind: str,
    byte_count: int,
    prefix_crc: int,
    required_crc: int,
    trace: deflate_probe.DeflateTrace | None,
    *,
    suffix_payload_byte_offset: int,
    max_solutions: int = DEFAULT_MAX_SOLUTIONS,
    max_skeletons: int = DEFAULT_MAX_SKELETONS_PER_POSITION,
    suffix_bit_count: int = DEFAULT_SUFFIX_BITS,
    validate_local: bool = False,
    max_solutions_per_skeleton: int = 4,
    candidate_filter: Callable[[bytes], bool] | None = None,
    target_output_delta: int | None = None,
    max_expansions: int = DEFAULT_MAX_EXPANSIONS,
    distance_hints: tuple[int, ...] = (),
    semantic_extra_assignments: int = DEFAULT_SEMANTIC_EXTRA_ASSIGNMENTS,
    semantic_beam_width: int = DEFAULT_SEMANTIC_BEAM_WIDTH,
    semantic_expansions: int = DEFAULT_SEMANTIC_EXPANSIONS,
    semantic_max_skeletons: int = DEFAULT_SEMANTIC_MAX_SKELETONS,
    semantic_solutions_per_skeleton: int = DEFAULT_SEMANTIC_SOLUTIONS_PER_SKELETON,
) -> tuple[bytes, ...]:
    byte_count = int(byte_count)
    if edit_kind not in {"insert", "replace"} or byte_count <= 0 or trace is None or not trace.ok:
        return ()
    history = (
        _cached_history_state(payload, int(position), trace)
        if int(byte_count) >= 7 and int(semantic_expansions) > 0 and int(semantic_beam_width) > 0
        else None
    )
    state = (
        history.huffman
        if history is not None
        else deflate_probe.huffman_state_before_byte_boundary(payload, int(position), trace=trace)
    )
    if state is None:
        return ()
    fixed_bit_count = int(position) * 8 - int(state.bit_offset)
    if fixed_bit_count < 0 or fixed_bit_count > 64:
        return ()
    candidate_bit_count = byte_count * 8
    suffix_payload_bit_offset = max(0, int(suffix_payload_byte_offset)) * 8
    crc_rows = crc32_affine_rows(prefix_crc, required_crc, byte_count)
    max_symbols = max(4, byte_count * 3)
    local_target_output_delta = _local_output_delta_target(
        trace,
        fixed_bit_count,
        candidate_bit_count,
        target_output_delta,
    )
    seen: set[bytes] = set()
    solutions: list[bytes] = []

    def consume_skeletons(
        skeletons: Iterable[tuple[int | None, ...]],
        *,
        per_skeleton_limit: int,
    ) -> bool:
        for skeleton in skeletons:
            equations = crc_rows + _skeleton_rows(skeleton, fixed_bit_count, candidate_bit_count)
            for solution in solve_gf2(
                equations,
                None,
                candidate_bit_count,
                max_solutions=max(1, min(int(max_solutions), int(per_skeleton_limit))),
            ):
                candidate = int(solution).to_bytes(byte_count, "little")
                if candidate in seen:
                    continue
                if zlib.crc32(candidate, int(prefix_crc) & CRC32_MASK) & CRC32_MASK != (int(required_crc) & CRC32_MASK):
                    continue
                if candidate_filter is not None and not candidate_filter(candidate):
                    continue
                if validate_local:
                    local = deflate_probe.validate_local_edit(
                        payload,
                        int(position),
                        edit_kind,
                        byte_count,
                        candidate,
                        stop_after_output=int(state.output_offset) + max(4096, byte_count * 512),
                        checkpoint_stride=2048,
                    )
                    if not local.accepted:
                        continue
                seen.add(candidate)
                solutions.append(candidate)
                if len(solutions) >= int(max_solutions):
                    return True
        return False

    clean_distance_hints = tuple(int(item) for item in distance_hints if int(item) > 0)
    if history is not None:
        if consume_skeletons(
            _iter_semantic_symbol_skeletons(
                payload,
                history,
                fixed_bit_count,
                candidate_bit_count,
                suffix_payload_bit_offset,
                suffix_bit_count,
                max_skeletons=max(1, min(int(max_skeletons), int(semantic_max_skeletons))),
                max_branch_tokens=max(16, min(32, DEFAULT_MAX_BRANCH_TOKENS, int(semantic_beam_width) // 4)),
                max_symbols=max_symbols,
                target_output_delta=local_target_output_delta,
                distance_hints=clean_distance_hints,
                semantic_extra_assignments=semantic_extra_assignments,
                semantic_beam_width=semantic_beam_width,
                semantic_expansions=semantic_expansions,
            ),
            per_skeleton_limit=max(1, min(int(max_solutions_per_skeleton), int(semantic_solutions_per_skeleton))),
        ):
            return tuple(solutions)

    consume_skeletons(_iter_symbol_skeletons(
        payload,
        state,
        fixed_bit_count,
        candidate_bit_count,
        suffix_payload_bit_offset,
        suffix_bit_count,
        max_skeletons=max_skeletons,
        max_branch_tokens=DEFAULT_MAX_BRANCH_TOKENS,
        max_symbols=max_symbols,
        target_output_delta=local_target_output_delta,
        max_expansions=max_expansions,
        distance_hints=clean_distance_hints,
    ), per_skeleton_limit=max_solutions_per_skeleton)
    return tuple(solutions)
