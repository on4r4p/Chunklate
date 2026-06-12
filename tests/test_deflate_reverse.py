#!/usr/bin/env python3

from chunklate import deflate_probe, deflate_reverse


def test_reverse_bit_cursor_reads_backwards_lsb_order():
    cursor = deflate_reverse.ReverseBitCursor(bytes([0xB2]), 8)

    assert cursor.read_bits(4) == (1, 0, 1, 1)
    assert cursor.bit_offset == 4


def test_reverse_huffman_index_matches_fixed_literal_backwards():
    literal_table = deflate_probe._FIXED_TABLES[0]
    index = deflate_reverse.ReverseHuffmanIndex.from_table(literal_table)
    code, width = deflate_probe._symbol_codes(literal_table)[65]
    forward_bits = deflate_probe._bits_for_code(code, width)

    matches = index.matches_backward_bits(tuple(reversed(forward_bits)))

    assert any(match.symbol == 65 for match in matches)


def test_reverse_tail_paths_include_literal_suffix_token():
    literal_table, literal_max, distance_table, distance_max = deflate_probe._FIXED_TABLES
    state = deflate_probe.DeflateHuffmanState(
        byte_offset=0,
        bit_offset=0,
        output_offset=64,
        block_index=0,
        block_type=1,
        literal_table=literal_table,
        literal_max_bits=literal_max,
        distance_table=distance_table,
        distance_max_bits=distance_max,
    )

    paths = deflate_reverse.iter_reverse_tail_paths(
        state,
        candidate_start_relative_bit=0,
        candidate_end_relative_bit=80,
        max_paths=64,
        max_tokens=2,
    )

    assert paths
    assert any(path.output_delta >= 1 and path.start_relative_bit < 80 for path in paths)


def test_reverse_tail_paths_include_length_distance_when_history_allows():
    literal_table, literal_max, distance_table, distance_max = deflate_probe._FIXED_TABLES
    state = deflate_probe.DeflateHuffmanState(
        byte_offset=0,
        bit_offset=0,
        output_offset=4096,
        block_index=0,
        block_type=1,
        literal_table=literal_table,
        literal_max_bits=literal_max,
        distance_table=distance_table,
        distance_max_bits=distance_max,
    )

    paths = deflate_reverse.iter_reverse_tail_paths(
        state,
        candidate_start_relative_bit=0,
        candidate_end_relative_bit=160,
        max_paths=256,
        max_tokens=3,
        distance_hints=(8, 16, 32),
    )

    assert any(path.reason == "length-distance" for path in paths)


def main():
    test_reverse_bit_cursor_reads_backwards_lsb_order()
    test_reverse_huffman_index_matches_fixed_literal_backwards()
    test_reverse_tail_paths_include_literal_suffix_token()
    test_reverse_tail_paths_include_length_distance_when_history_allows()


if __name__ == "__main__":
    main()
