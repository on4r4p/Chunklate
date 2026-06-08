#!/usr/bin/env python3
import binascii
import struct
import sys
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
for path in (ROOT, TESTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from chunklate import idat
from chunklate.png import iter_chunks
from repair_matrix import SBB_ONE_BYTE_MATRIX


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _chunk(chunk_type: bytes, payload: bytes, *, crc: int | None = None) -> bytes:
    if crc is None:
        crc = binascii.crc32(chunk_type + payload) & 0xFFFFFFFF
    return (
        struct.pack(">I", len(payload))
        + chunk_type
        + payload
        + struct.pack(">I", crc)
    )


def _base_filtered_rows() -> bytes:
    width = 8
    height = 8
    rows = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            row.extend(((x * 31 + y * 7) & 0xFF, (x * 17 + y * 19) & 0xFF, (x * 3 + y * 41) & 0xFF))
        rows.append(bytes(row))
    return b"".join(rows)


def _build_rgb_png(filtered_rows: bytes, *, idat_payload: bytes | None = None, idat_crc: int | None = None) -> bytes:
    width = 8
    height = 8
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    payload = zlib.compress(filtered_rows) if idat_payload is None else idat_payload
    return (
        PNG_SIGNATURE
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", payload, crc=idat_crc)
        + _chunk(b"IEND", b"")
    )


BASE_FILTERED_ROWS = _base_filtered_rows()
BASE_IDAT_PAYLOAD = zlib.compress(BASE_FILTERED_ROWS)
BASE_IDAT_CRC = binascii.crc32(b"IDAT" + BASE_IDAT_PAYLOAD) & 0xFFFFFFFF


def _mutate_one_byte(payload: bytes, mode: str, offset: int, value: int = 0xA5) -> bytes:
    if mode == "minus":
        return payload[:offset] + payload[offset + 1 :]
    if mode == "plus":
        return payload[:offset] + bytes((value,)) + payload[offset:]
    if mode == "different":
        replacement = payload[offset] ^ 0x5A
        if replacement == payload[offset]:
            replacement ^= 0xFF
        return payload[:offset] + bytes((replacement,)) + payload[offset + 1 :]
    raise AssertionError("unknown mutation mode %r" % mode)


def _generated_fixture_bytes(case) -> bytes:
    raw_offset = len(BASE_FILTERED_ROWS) // 2
    idat_offset = max(2, len(BASE_IDAT_PAYLOAD) // 2)
    if case.corruption_family == "zlib_decompressed_payload":
        mutated_rows = _mutate_one_byte(BASE_FILTERED_ROWS, case.mode, raw_offset)
        idat_payload = zlib.compress(mutated_rows)
    elif case.corruption_family == "compressed_idat_payload_before_zlib_decompression":
        if case.mode == "minus":
            idat_payload = _mutate_one_byte(BASE_IDAT_PAYLOAD, case.mode, len(BASE_IDAT_PAYLOAD) - 1)
        elif case.mode == "plus":
            idat_payload = _mutate_one_byte(BASE_IDAT_PAYLOAD, case.mode, len(BASE_IDAT_PAYLOAD))
        else:
            idat_payload = _mutate_one_byte(BASE_IDAT_PAYLOAD, case.mode, idat_offset)
    else:
        raise AssertionError("unknown corruption family %r" % case.corruption_family)

    idat_crc = None
    if case.crc_policy == "original_crc_kept":
        idat_crc = BASE_IDAT_CRC
    elif case.crc_policy != "valid_recalculated_crc":
        raise AssertionError("unknown CRC policy %r" % case.crc_policy)
    return _build_rgb_png(BASE_FILTERED_ROWS, idat_payload=idat_payload, idat_crc=idat_crc)


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
    assert all(_generated_fixture_bytes(case).startswith(PNG_SIGNATURE) for case in SBB_ONE_BYTE_MATRIX)


def test_sbb_one_byte_matrix_drives_diagnostic_order_and_crc_trust():
    failures = []

    for case in SBB_ONE_BYTE_MATRIX:
        data = _generated_fixture_bytes(case)
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
