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


def main():
    checks = [
        ("legacy globals", test_scan_legacy_chunk_exposes_window_and_legacy_globals),
        ("incomplete chunk fallback", test_scan_legacy_chunk_preserves_incomplete_chunk_fallbacks),
    ]

    print("Running chunk scanner tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"chunk scanner tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
