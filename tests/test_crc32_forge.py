#!/usr/bin/env python3
import random
import zlib

from chunklate import crc32_forge


def test_crc32_4byte_transition_matches_zlib_crc32():
    random.seed(1234)
    for _index in range(200):
        start_crc = random.randrange(2**32)
        end_crc = random.randrange(2**32)
        patch = crc32_forge.forge_crc32_4byte_transition(start_crc, end_crc)

        assert len(patch) == 4
        assert zlib.crc32(patch, start_crc) & 0xFFFFFFFF == end_crc


def test_crc32_4byte_fast_delta_solver_matches_generic_solver():
    random.seed(1236)
    for _index in range(200):
        delta = random.randrange(2**32)

        fast = crc32_forge._solve_patch_delta_4byte_fast(delta)
        generic = crc32_forge._solve_patch_delta(delta, 4)

        assert fast == generic


def test_crc32_short_transition_solves_representable_1_to_3_byte_patches():
    random.seed(1235)
    for byte_count in (1, 2, 3):
        for _index in range(100):
            start_crc = random.randrange(2**32)
            expected_patch = random.randbytes(byte_count)
            end_crc = zlib.crc32(expected_patch, start_crc) & 0xFFFFFFFF

            patch = crc32_forge.solve_crc32_nbyte_transition(start_crc, end_crc, byte_count)

            assert patch == expected_patch
            assert zlib.crc32(patch, start_crc) & 0xFFFFFFFF == end_crc


def test_crc32_required_before_suffixes_reverse_to_target():
    payload = bytes(range(64))
    target_crc = 0x59B4169A

    required = crc32_forge.crc32_required_before_suffixes(payload, target_crc)

    assert len(required) == len(payload) + 1
    for index in (0, 1, 17, 63, 64):
        assert zlib.crc32(payload[index:], required[index]) & 0xFFFFFFFF == target_crc


def test_crc32_prefix_and_required_suffix_can_forge_idat_patch():
    payload = b"abcdefghi"
    target_payload = payload[:3] + b"\x01\x02\x03\x04" + payload[7:]
    target_crc = zlib.crc32(b"IDAT" + target_payload) & 0xFFFFFFFF
    prefixes = crc32_forge.crc32_prefixes(b"IDAT", payload)
    required = crc32_forge.crc32_required_before_suffixes(payload, target_crc)

    patch = crc32_forge.forge_crc32_4byte_transition(prefixes[3], required[7])
    repaired = payload[:3] + patch + payload[7:]

    assert repaired == target_payload
    assert zlib.crc32(b"IDAT" + repaired) & 0xFFFFFFFF == target_crc


def main():
    test_crc32_4byte_transition_matches_zlib_crc32()
    test_crc32_4byte_fast_delta_solver_matches_generic_solver()
    test_crc32_short_transition_solves_representable_1_to_3_byte_patches()
    test_crc32_required_before_suffixes_reverse_to_target()
    test_crc32_prefix_and_required_suffix_can_forge_idat_patch()


if __name__ == "__main__":
    main()
