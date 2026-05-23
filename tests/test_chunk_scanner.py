#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import chunk_scanner
from chunklate.png import PNG_SIGNATURE


FIXTURE = ROOT / "schaik-javapng-samples" / "basn0g01.png"


def test_scan_legacy_chunk_exposes_window_and_legacy_globals():
    scan = chunk_scanner.scan_legacy_chunk(
        FIXTURE.read_bytes(),
        len(PNG_SIGNATURE) * 2,
    )
    values = scan.legacy_globals()

    assert tuple(values) == chunk_scanner.LEGACY_GLOBAL_NAMES
    assert scan.window.chunk_type == b"IHDR"
    assert values["Raw_Length"] == "0000000d"
    assert values["Orig_CL"] == "0000000d"
    assert values["Raw_Type"] == "49484452"
    assert values["Orig_CT"] == b"IHDR"
    assert values["Raw_Crc"] == "5b014759"
    assert values["Orig_CRC"] == "5b014759"
    assert values["Raw_NextChunk"] == "67414d41"
    assert values["Orig_NC"] == b"gAMA"
    assert values["CLoffI"] == 16
    assert values["CToffI"] == 24
    assert values["CDoffI"] == 32
    assert values["CrcoffI"] == 58
    assert values["NCoffI"] == 90


def test_scan_legacy_chunk_preserves_incomplete_chunk_fallbacks():
    data = PNG_SIGNATURE + b"\x00\x00\x00\x04IDATab"
    scan = chunk_scanner.scan_legacy_chunk(data, len(PNG_SIGNATURE) * 2)
    values = scan.legacy_globals()

    assert values["Raw_Length"] == "00000004"
    assert values["Raw_Type"] == "49444154"
    assert values["Raw_Data"] == "6162"
    assert values["Raw_Crc"] == ""
    assert values["Orig_CT"] == b"IDAT"


def test_magic_bingo_scan_preserves_best_signature_and_progress_calls():
    calls = []
    scan = chunk_scanner.magic_bingo_scan(
        "abxdzzabcd",
        "abcd",
        progress=lambda: calls.append("tick"),
    )

    assert calls == ["tick"] * 7
    assert scan.best_score == "4"
    assert scan.best_signature == "abcd"
    assert scan.best_count == 1
    assert scan.bingo_list[0] == "4 abcd"


def test_magic_bingo_scan_counts_multiple_best_scores():
    scan = chunk_scanner.magic_bingo_scan("abcdxxxxabcd", "abcd")

    assert scan.best_score == "4"
    assert scan.best_count == 2
    assert scan.bingo_list[:2] == ["4 abcd", "4 abcd"]


def test_scan_known_chunks_until_idat_stops_at_first_idat():
    scan = chunk_scanner.scan_known_chunks_until_idat(
        "00" + b"IHDR".hex() + "11" + b"IDAT".hex() + "22" + b"IEND".hex(),
        [b"IHDR", b"IDAT", b"IEND"],
    )

    assert scan.found_idat is True
    assert scan.chunks_found == {b"IHDR": 2, b"IDAT": 12}
    assert scan.hits == (
        chunk_scanner.KnownChunkHit(b"IHDR", 2),
        chunk_scanner.KnownChunkHit(b"IDAT", 12),
    )
    assert scan.hits[1].offset_byte == 6
    assert scan.hits[1].offset_hex == "0x6"
    assert scan.hits[1].is_idat is True


def test_scan_known_chunks_until_idat_reports_no_idat():
    scan = chunk_scanner.scan_known_chunks_until_idat(
        "00" + b"IHDR".hex() + "11" + b"IEND".hex(),
        [b"IHDR", b"IDAT", b"IEND"],
    )

    assert scan.found_idat is False
    assert scan.chunks_found == {b"IHDR": 2, b"IEND": 12}
    assert [hit.chunk for hit in scan.hits] == [b"IHDR", b"IEND"]


def test_nearest_found_chunk_uses_lowest_offset_and_previous_length():
    candidate = chunk_scanner.nearest_found_chunk(
        "aaaabbbbccccIIIIDDDD",
        {b"IDAT": 16, b"IHDR": 8},
    )

    assert candidate == chunk_scanner.NearestFoundChunk(
        chunk=b"IHDR",
        offset=8,
        preceding_length="aaaabbbb",
    )
    assert candidate.offset_byte == 4
    assert candidate.offset_hex == "0x4"


def test_nearest_found_chunk_uses_prefix_when_no_previous_length():
    candidate = chunk_scanner.nearest_found_chunk("aaaabbbb", {b"IHDR": 4})

    assert candidate.preceding_length == "aaaa"


def test_prepend_magic_before_nearest_preserves_legacy_join():
    assert chunk_scanner.prepend_magic_before_nearest(
        "aaaabbbbcccc",
        "89504e47",
        "0000000d",
        8,
    ) == "89504e470000000dcccc"


def main():
    checks = [
        ("legacy globals", test_scan_legacy_chunk_exposes_window_and_legacy_globals),
        ("incomplete chunk fallback", test_scan_legacy_chunk_preserves_incomplete_chunk_fallbacks),
        ("magic bingo best signature", test_magic_bingo_scan_preserves_best_signature_and_progress_calls),
        ("magic bingo best count", test_magic_bingo_scan_counts_multiple_best_scores),
        ("known chunk scan until IDAT", test_scan_known_chunks_until_idat_stops_at_first_idat),
        ("known chunk scan without IDAT", test_scan_known_chunks_until_idat_reports_no_idat),
        ("nearest found chunk", test_nearest_found_chunk_uses_lowest_offset_and_previous_length),
        ("nearest found chunk prefix", test_nearest_found_chunk_uses_prefix_when_no_previous_length),
        ("prepend magic before nearest", test_prepend_magic_before_nearest_preserves_legacy_join),
    ]

    print("Running chunk scanner tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"chunk scanner tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
