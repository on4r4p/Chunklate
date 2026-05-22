#!/usr/bin/env python3
import struct
import sys
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import dummy_chunk
from chunklate.png import IEND_CHUNK, PNG_SIGNATURE, build_png_chunk, validate_png_structure


FIXTURES = ROOT / "Png_Errors_handled_by_Chunklate_So_Far"


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


def test_dummy_chunk_decision_rebuilds_partial_idat_blackfill():
    data = (FIXTURES / "IDAT_Partial_Blackfill.png").read_bytes()

    decision = dummy_chunk.decide_dummy_chunk(b"IDAT", data.hex(), 0)

    assert decision.action == "partial_idat_blackfill"
    assert decision.solved is True
    assert "partial-idat-blackfill" in decision.repair.strategy
    assert validate_png_structure(bytes.fromhex(decision.fixed_data_hex)).ok


def test_dummy_chunk_decision_keeps_unknown_chunks_on_legacy_fallback():
    decision = dummy_chunk.decide_dummy_chunk(b"PLTE", "", 0)

    assert decision.action == "fallback"
    assert decision.fixed_data_hex == ""
    assert decision.solved is False


def main():
    checks = [
        ("Missing IHDR decision", test_dummy_chunk_decision_rebuilds_missing_ihdr_from_idat),
        ("IEND completion decision", test_dummy_chunk_decision_completes_iend_tail),
        ("Partial IDAT blackfill decision", test_dummy_chunk_decision_rebuilds_partial_idat_blackfill),
        ("Fallback decision", test_dummy_chunk_decision_keeps_unknown_chunks_on_legacy_fallback),
    ]

    print("Running dummy chunk tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"dummy chunk tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
