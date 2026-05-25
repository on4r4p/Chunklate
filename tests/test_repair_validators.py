#!/usr/bin/env python3
import binascii
import struct
import sys
import tempfile
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from repair_matrix import RepairCase
from repair_validators import validate_repaired_case


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def chunk(chunk_type, data):
    return (
        len(data).to_bytes(4, "big")
        + chunk_type
        + data
        + struct.pack("!I", binascii.crc32(chunk_type + data))
    )


def simple_png(width=1, height=1, *, extra_chunks=()):
    ihdr = (
        width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + b"\x08\x02\x00\x00\x00"
    )
    raw_scanline = b"\x00" + b"\x00\x00\x00" * width
    idat = zlib.compress(raw_scanline * height)
    return (
        PNG_SIGNATURE
        + chunk(b"IHDR", ihdr)
        + b"".join(extra_chunks)
        + chunk(b"IDAT", idat)
        + chunk(b"IEND", b"")
    )


def repair_case(**updates):
    values = {
        "fixture": "sample.png",
        "corruption": "test corruption",
        "expected_strategy": "test strategy",
        "max_saves": 1,
        "expected_outputs": ("sample.0_Fixed.png",),
        "summary_contains": ("repair marker",),
        "validators": (),
    }
    values.update(updates)
    return RepairCase(**values)


def write_summary(tmp_path, text="repair marker"):
    summary = tmp_path / "Summary_Of_sample"
    summary.write_text(text)
    return summary


def test_validate_repaired_case_accepts_dimensions_chunks_and_idat(tmp_path):
    repaired = tmp_path / "fixed.png"
    summary = write_summary(tmp_path)
    repaired.write_bytes(
        simple_png(
            1,
            1,
            extra_chunks=(
                chunk(b"gAMA", (45455).to_bytes(4, "big")),
                chunk(b"PLTE", b"\x00\x00\x00"),
            ),
        )
    )
    case = repair_case(
        validators=(
            "first_chunk:IHDR",
            "ihdr_dimensions:1x1",
            "has_chunk:PLTE",
            "plte_non_empty",
            "gama_non_zero",
            "idat_decompress",
            "last_chunk:IEND",
        )
    )

    assert validate_repaired_case(case, repaired, summary) == []


def test_validate_repaired_case_reports_missing_contract_validator(tmp_path):
    repaired = tmp_path / "fixed.png"
    summary = write_summary(tmp_path)
    repaired.write_bytes(simple_png())
    case = repair_case(validators=())

    assert validate_repaired_case(case, repaired, summary) == [
        "sample.png: missing repair-specific validators"
    ]


def test_validate_repaired_case_reports_forbidden_chunk_still_present(tmp_path):
    repaired = tmp_path / "fixed.png"
    summary = write_summary(tmp_path)
    repaired.write_bytes(simple_png(extra_chunks=(chunk(b"gAMA", b"\x00\x00\x00\x00"),)))
    case = repair_case(validators=("missing_chunk:gAMA",))

    errors = validate_repaired_case(case, repaired, summary)

    assert "chunk gAMA is still present" in errors


def test_validate_repaired_case_reports_idat_length_mismatch(tmp_path):
    repaired = tmp_path / "fixed.png"
    summary = write_summary(tmp_path)
    repaired.write_bytes(simple_png(1, 2))
    case = repair_case(validators=("idat_decompressed_len:4",))

    errors = validate_repaired_case(case, repaired, summary)

    assert "expected decompressed IDAT length 4, got 8" in errors


def test_validate_repaired_case_reports_missing_summary_marker(tmp_path):
    repaired = tmp_path / "fixed.png"
    summary = write_summary(tmp_path, "different marker")
    repaired.write_bytes(simple_png())
    case = repair_case(validators=("idat_decompress",))

    errors = validate_repaired_case(case, repaired, summary)

    assert "sample.png: summary Summary_Of_sample missing marker 'repair marker'" in errors


def main():
    checks = [
        ("valid repaired case", test_validate_repaired_case_accepts_dimensions_chunks_and_idat),
        ("missing validator", test_validate_repaired_case_reports_missing_contract_validator),
        ("forbidden chunk", test_validate_repaired_case_reports_forbidden_chunk_still_present),
        ("idat length", test_validate_repaired_case_reports_idat_length_mismatch),
        ("summary marker", test_validate_repaired_case_reports_missing_summary_marker),
    ]

    print("Running repair validator tests")
    with tempfile.TemporaryDirectory(prefix="chunklate-repair-validator-tests-") as tmp:
        for label, check in checks:
            print(f"  - {label} ... ", end="", flush=True)
            check(Path(tmp))
            print("ok")

    print(f"repair validator tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
