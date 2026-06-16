#!/usr/bin/env python3
import binascii
import struct
import sys
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import dummy_chunk
from chunklate.png import IEND_CHUNK, PNG_SIGNATURE, build_png_chunk, validate_png_structure


def rgb_ihdr(width=1, height=1):
    return struct.pack("!IIBBBBB", width, height, 8, 2, 0, 0, 0)


def test_dummy_chunk_decision_rebuilds_missing_ihdr_from_idat():
    data = PNG_SIGNATURE + build_png_chunk(b"IDAT", zlib.compress(b"\x00abc")) + IEND_CHUNK

    decision = dummy_chunk.decide_dummy_chunk(b"IHDR", data.hex(), len(PNG_SIGNATURE) * 2)

    assert decision.action == "strict_ihdr_repair"
    assert decision.solved is True
    assert decision.dummy_data_length == 13
    assert validate_png_structure(bytes.fromhex(decision.fixed_data_hex)).ok
    assert decision.repair.width == 1
    assert decision.repair.height == 1


def test_dummy_chunk_decision_completes_iend_tail():
    data = PNG_SIGNATURE + build_png_chunk(b"IHDR", rgb_ihdr()) + build_png_chunk(
        b"IDAT",
        zlib.compress(b"\x00abc"),
    )

    decision = dummy_chunk.decide_dummy_chunk(b"IEND", data.hex(), len(data) * 2)

    assert decision.action == "complete_iend"
    assert decision.solved is True
    assert bytes.fromhex(decision.fixed_data_hex).endswith(IEND_CHUNK)
    assert validate_png_structure(bytes.fromhex(decision.fixed_data_hex)).ok


def test_dummy_chunk_decision_replaces_partial_iend_prefix_at_eof():
    data = PNG_SIGNATURE + build_png_chunk(b"IHDR", rgb_ihdr()) + build_png_chunk(
        b"IDAT",
        zlib.compress(b"\x00abc"),
    )
    partial = data + IEND_CHUNK[:1]

    decision = dummy_chunk.decide_dummy_chunk(b"IEND", partial.hex(), len(partial) * 2)
    fixed = bytes.fromhex(decision.fixed_data_hex)

    assert decision.action == "complete_iend"
    assert fixed == data + IEND_CHUNK
    assert validate_png_structure(fixed).ok


def test_dummy_chunk_decision_cuts_extra_tail_byte_before_iend():
    data = PNG_SIGNATURE + build_png_chunk(b"IHDR", rgb_ihdr()) + build_png_chunk(
        b"IDAT",
        zlib.compress(b"\x00abc"),
    )
    extra_tail = data + b"\x82"

    decision = dummy_chunk.decide_dummy_chunk(b"IEND", extra_tail.hex(), len(extra_tail) * 2)
    fixed = bytes.fromhex(decision.fixed_data_hex)

    assert decision.action == "complete_iend"
    assert fixed == data + IEND_CHUNK
    assert validate_png_structure(fixed).ok


def test_dummy_chunk_decision_keeps_unknown_chunks_on_legacy_fallback():
    decision = dummy_chunk.decide_dummy_chunk(b"PLTE", "", 0)

    assert decision.action == "fallback"
    assert decision.fixed_data_hex == ""
    assert decision.solved is False


def test_dummy_chunk_builds_legacy_ihdr_dummy_with_injected_helpers():
    sample_data = "00000001000000010802000000"

    build = dummy_chunk.build_legacy_ihdr_dummy(
        b"IHDR",
        get_spec=lambda *args, **kwargs: (26, ("!I",), ["1"], "2"),
        spec_length=lambda chunk: "0000000d",
        random_sample=lambda chunk_data, color_type, chunk_format: sample_data,
    )

    expected_crc = hex(binascii.crc32(b"IHDR" + bytes.fromhex(sample_data))).replace(
        "0x",
        "",
    )
    assert build.chunklen_spec == 26
    assert build.chunk_format == ("!I",)
    assert build.color_type == "2"
    assert build.dummy_length == "0000000d"
    assert build.dummy_name == "49484452"
    assert build.dummy_data == sample_data
    assert build.dummy_crc == expected_crc
    assert build.chunk_hex == "0000000d49484452" + sample_data + expected_crc
    assert build.solved is False


def main():
    checks = [
        ("Missing IHDR decision", test_dummy_chunk_decision_rebuilds_missing_ihdr_from_idat),
        ("IEND completion decision", test_dummy_chunk_decision_completes_iend_tail),
        ("IEND partial prefix decision", test_dummy_chunk_decision_replaces_partial_iend_prefix_at_eof),
        ("IEND extra tail byte decision", test_dummy_chunk_decision_cuts_extra_tail_byte_before_iend),
        ("Fallback decision", test_dummy_chunk_decision_keeps_unknown_chunks_on_legacy_fallback),
        ("Legacy IHDR dummy build", test_dummy_chunk_builds_legacy_ihdr_dummy_with_injected_helpers),
    ]

    print("Running dummy chunk tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"dummy chunk tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
