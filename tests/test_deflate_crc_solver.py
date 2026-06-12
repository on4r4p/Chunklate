#!/usr/bin/env python3
import random
import zlib

from chunklate import crc32_forge, deflate_crc_solver, deflate_probe


def _satisfies(rows, value):
    return all(((row & value).bit_count() & 1) == rhs for row, rhs in rows)


def _pack_bits(bits):
    output = bytearray()
    value = 0
    width = 0
    for bit in bits:
        value |= (int(bit) & 1) << width
        width += 1
        if width == 8:
            output.append(value)
            value = 0
            width = 0
    if width:
        output.append(value)
    return bytes(output)


def _fixed_literal_zlib(raw: bytes) -> bytes:
    literal_codes = deflate_probe._symbol_codes(deflate_probe._FIXED_TABLES[0])
    bits = [1, 1, 0]
    for value in raw:
        code, width = literal_codes[value]
        bits.extend(deflate_probe._bits_for_code(code, width))
    code, width = literal_codes[256]
    bits.extend(deflate_probe._bits_for_code(code, width))
    return b"\x78\x01" + _pack_bits(bits) + zlib.adler32(raw).to_bytes(4, "big")


def test_solve_gf2_handles_determined_system():
    rows = (
        (0b001, 1),
        (0b010, 0),
        (0b100, 1),
    )

    assert deflate_crc_solver.solve_gf2(rows, None, 3) == (0b101,)


def test_solve_gf2_enumerates_underdetermined_by_weight():
    rows = ((0b0011, 1),)

    solutions = deflate_crc_solver.solve_gf2(rows, None, 4, max_solutions=4)

    assert len(solutions) == 4
    assert all(_satisfies(rows, solution) for solution in solutions)
    assert solutions[0].bit_count() == 1


def test_crc32_affine_rows_match_known_transitions_1_to_20_bytes():
    rng = random.Random(20260611)
    for byte_count in (1, 2, 3, 4, 5, 10, 20):
        start_crc = rng.randrange(2**32)
        patch = rng.randbytes(byte_count)
        end_crc = zlib.crc32(patch, start_crc) & 0xFFFFFFFF

        rows = deflate_crc_solver.crc32_affine_rows(start_crc, end_crc, byte_count)
        patch_value = int.from_bytes(patch, "little")
        solutions = deflate_crc_solver.solve_gf2(rows, None, byte_count * 8, max_solutions=8)

        assert _satisfies(rows, patch_value)
        assert solutions
        for solution in solutions:
            candidate = int(solution).to_bytes(byte_count, "little")
            assert zlib.crc32(candidate, start_crc) & 0xFFFFFFFF == end_crc


def test_deflate_history_state_replays_fixed_huffman_tail():
    raw = bytes(range(64))
    stream = _fixed_literal_zlib(raw)
    trace = deflate_probe.analyze_deflate_stream(stream)

    history = None
    for byte_offset in range(3, len(stream) - 4):
        history = deflate_probe.huffman_history_state_before_byte_boundary(
            stream,
            byte_offset,
            trace=trace,
        )
        if history is not None and history.huffman.output_offset >= 4:
            break

    assert history is not None
    assert history.output_tail == raw[: history.huffman.output_offset]
    assert history.tail_start == 0


def test_semantic_copy_from_output_tail_handles_overlap():
    copied = deflate_crc_solver._copy_from_output_tail(
        b"abc",
        0,
        3,
        distance=3,
        length=6,
    )

    assert copied is not None
    copied_bytes, output_tail, tail_start, output_offset = copied
    assert copied_bytes == b"abcabc"
    assert output_tail.endswith(b"abcabcabc")
    assert tail_start == 0
    assert output_offset == 9


def test_semantic_distance_ranking_prefers_scanline_hint():
    options = deflate_crc_solver._semantic_distance_options(
        5,
        (None,),
        output_tail=b"x" * 32,
        output_offset=32,
        distance_hints=(8,),
        limit=4,
    )

    assert options
    assert deflate_probe.DISTANCE_BASES[5] + options[0][0] == 8


def test_contextual_template_selection_keeps_literal_diversity():
    templates = tuple(
        deflate_crc_solver._TokenTemplate(index, 4, (index & 1, None, None))
        for index in range(12)
    ) + (
        deflate_crc_solver._TokenTemplate(999, 1, (1, 1, 1, 1, 1, 1)),
    )

    selected = deflate_crc_solver._select_contextual_templates(templates, limit=6)

    assert any(template.output_delta == 1 for template in selected)


def test_target_output_penalty_allows_suffix_overshoot_after_candidate_bits():
    assert deflate_crc_solver._target_output_penalty(
        160,
        40,
        target_output_delta=23,
        target_bit_count=96,
        scale=8,
        cap=512,
    ) == 0
    assert deflate_crc_solver._target_output_penalty(
        160,
        10,
        target_output_delta=23,
        target_bit_count=96,
        scale=8,
        cap=512,
    ) > 0


def test_semantic_expansion_generates_length_distance_copy():
    literal_table, literal_max, distance_table, distance_max = deflate_probe._FIXED_TABLES
    state = deflate_probe.DeflateHuffmanState(
        byte_offset=0,
        bit_offset=0,
        output_offset=10,
        block_index=0,
        block_type=1,
        literal_table=literal_table,
        literal_max_bits=literal_max,
        distance_table=distance_table,
        distance_max_bits=distance_max,
    )
    history = deflate_probe.DeflateHistoryState(
        huffman=state,
        output_tail=b"abcdefghij",
        tail_start=0,
        history_size=32768,
    )
    literal_codes = deflate_probe._symbol_codes(literal_table)
    distance_codes = deflate_probe._symbol_codes(distance_table)
    expected_prefix = (
        deflate_probe._bits_for_code(*literal_codes[264])
        + deflate_probe._bits_for_code(*distance_codes[6])
        + (1, 0)
    )

    path = deflate_crc_solver._SemanticPath(
        0,
        0,
        0,
        0,
        (),
        history.output_tail,
        history.tail_start,
        state.output_offset,
    )
    expansions = deflate_crc_solver._semantic_symbol_expansions(
        b"\x00" * 32,
        state,
        path,
        0,
        80,
        None,
        0,
        max_branch_tokens=64,
        distance_hints=(10,),
        target_output_delta=10,
        semantic_extra_assignments=16,
    )

    assert any(expansion.bits[: len(expected_prefix)] == expected_prefix for expansion in expansions)


def _synthetic_trace(payload: bytes) -> deflate_probe.DeflateTrace:
    state = deflate_probe.DeflateHuffmanState(
        byte_offset=0,
        bit_offset=0,
        output_offset=4096,
        block_index=0,
        block_type=1,
        literal_table={(0, 8): 0},
        literal_max_bits=8,
        distance_table={(0, 5): 0},
        distance_max_bits=5,
    )
    return deflate_probe.DeflateTrace(
        status="complete",
        compressed_size=len(payload),
        decompressed_size=4096,
        huffman_states=(state,),
    )


def _solve_synthetic(edit_kind: str, byte_count: int) -> tuple[bytes, ...]:
    repair = b"\x00" * byte_count
    suffix = b"\x00" * 32
    if edit_kind == "insert":
        original = repair + suffix
        broken = suffix
        suffix_offset = 0
    else:
        original = repair + suffix
        broken = b"\xff" * byte_count + suffix
        suffix_offset = byte_count
    target_crc = zlib.crc32(b"IDAT" + original) & 0xFFFFFFFF
    prefixes = crc32_forge.crc32_prefixes(b"IDAT", broken)
    required = crc32_forge.crc32_required_before_suffixes(broken, target_crc)
    return deflate_crc_solver.solve_idat_crc_huffman(
        broken,
        0,
        edit_kind,
        byte_count,
        prefixes[0],
        required[suffix_offset],
        _synthetic_trace(broken),
        suffix_payload_byte_offset=suffix_offset,
        max_solutions=4,
        max_skeletons=64,
        max_solutions_per_skeleton=8,
        suffix_bit_count=64,
    )


def test_huffman_solver_recovers_synthetic_insert_10_and_20():
    assert _solve_synthetic("insert", 10)[0] == b"\x00" * 10
    assert _solve_synthetic("insert", 20)[0] == b"\x00" * 20


def test_huffman_solver_recovers_synthetic_replace_10_and_20():
    assert _solve_synthetic("replace", 10)[0] == b"\x00" * 10
    assert _solve_synthetic("replace", 20)[0] == b"\x00" * 20


def main():
    test_solve_gf2_handles_determined_system()
    test_solve_gf2_enumerates_underdetermined_by_weight()
    test_crc32_affine_rows_match_known_transitions_1_to_20_bytes()
    test_deflate_history_state_replays_fixed_huffman_tail()
    test_semantic_copy_from_output_tail_handles_overlap()
    test_semantic_distance_ranking_prefers_scanline_hint()
    test_contextual_template_selection_keeps_literal_diversity()
    test_target_output_penalty_allows_suffix_overshoot_after_candidate_bits()
    test_semantic_expansion_generates_length_distance_copy()
    test_huffman_solver_recovers_synthetic_insert_10_and_20()
    test_huffman_solver_recovers_synthetic_replace_10_and_20()


if __name__ == "__main__":
    main()
