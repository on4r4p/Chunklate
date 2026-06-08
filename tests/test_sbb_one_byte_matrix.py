#!/usr/bin/env python3
import binascii
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
for path in (ROOT, TESTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from chunklate import idat
from chunklate.png import iter_chunks
from repair_matrix import SBB_ONE_BYTE_MATRIX


FIXTURES = ROOT / "brokenjavapngsuite"


def _first_idat_crc_target_trusted(data: bytes) -> bool:
    first = next(chunk for chunk in iter_chunks(data) if chunk.chunk_type == b"IDAT")
    calculated = binascii.crc32(first.chunk_type + first.data) & 0xFFFFFFFF
    return calculated != first.crc


def _expected_order(edit_mode: str) -> tuple[str, str, str]:
    if edit_mode == "Insert":
        return ("Insert", "Replace", "Remove")
    if edit_mode == "Remove":
        return ("Remove", "Replace", "Insert")
    return ("Replace", "Insert", "Remove")


def test_sbb_one_byte_matrix_is_complete_and_unique():
    names = [case.fixture for case in SBB_ONE_BYTE_MATRIX]

    assert len(names) == 12
    assert len(set(names)) == 12
    assert all((FIXTURES / name).exists() for name in names)


def test_sbb_one_byte_matrix_drives_diagnostic_order_and_crc_trust():
    failures = []

    for case in SBB_ONE_BYTE_MATRIX:
        data = (FIXTURES / case.fixture).read_bytes()
        crc_target_trusted = _first_idat_crc_target_trusted(data)
        diagnostic = idat.analyze_sbb_idat_diagnostic(
            data,
            crc_target_trusted=crc_target_trusted,
        )
        expected_order = _expected_order(case.expected_edit_mode)

        if diagnostic.hephaestus_order != expected_order:
            failures.append(
                "%s: expected order %s, got %s"
                % (case.fixture, expected_order, diagnostic.hephaestus_order)
            )
        if diagnostic.crc_target_useful != case.crc_useful:
            failures.append(
                "%s: expected crc_useful=%s, got %s"
                % (case.fixture, case.crc_useful, diagnostic.crc_target_useful)
            )
        if case.expected_outcome == "needs_reference" and not diagnostic.requires_visual_reference:
            failures.append("%s: expected visual reference/ROI route" % case.fixture)
        if case.expected_outcome == "clean_reject" and diagnostic.crc_target_useful:
            failures.append("%s: clean reject case should not have a CRC oracle" % case.fixture)
        if case.expected_outcome in {"repaired", "strict_validation_or_reference"} and not diagnostic.crc_target_useful:
            failures.append("%s: repaired case should have a useful CRC oracle" % case.fixture)

    assert failures == []


def test_sbb_one_byte_matrix_documents_user_observed_cases():
    by_name = {case.fixture: case for case in SBB_ONE_BYTE_MATRIX}

    assert by_name["05_zlib_decomp_plus_1_octet_crc_valide.png"].expected_outcome == "needs_reference"
    assert by_name["06_zlib_decomp_plus_1_octet_crc_original.png"].expected_outcome == "needs_reference"
    assert by_name["07_idat_payload_plus_1_octet_crc_valide.png"].expected_outcome == "clean_reject"
    assert by_name["08_idat_payload_plus_1_octet_crc_original.png"].expected_outcome == "strict_validation_or_reference"
    assert by_name["12_idat_payload_different_1_octet_crc_original.png"].expected_outcome == "strict_validation_or_reference"


def main():
    tests = [
        ("matrix complete", test_sbb_one_byte_matrix_is_complete_and_unique),
        ("diagnostic order", test_sbb_one_byte_matrix_drives_diagnostic_order_and_crc_trust),
        ("observed cases", test_sbb_one_byte_matrix_documents_user_observed_cases),
    ]
    print("Running SBB one-byte matrix tests")
    for label, test in tests:
        print(f"  - {label} ... ", end="", flush=True)
        test()
        print("ok")
    print(f"SBB one-byte matrix tests passed ({len(tests)} checks)")


if __name__ == "__main__":
    main()
