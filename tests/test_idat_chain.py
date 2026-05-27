#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import idat_chain
from chunklate.png import IEND_CHUNK, PNG_SIGNATURE, build_png_chunk


def raw_chunk(declared_length, chunk_type, payload):
    return declared_length.to_bytes(4, "big") + chunk_type + payload + b"\x00\x00\x00\x00"


def sample_prefix():
    return PNG_SIGNATURE + build_png_chunk(b"IHDR", b"\x00" * 13)


def test_idat_chain_complete_without_patch_is_ok():
    data = (
        sample_prefix()
        + raw_chunk(4, b"IDAT", b"aaaa")
        + raw_chunk(4, b"IDAT", b"bbbb")
        + IEND_CHUNK
    )

    analysis = idat_chain.analyze_idat_chain_headers(data)

    assert analysis.status == "ok"
    assert analysis.repairable is False
    assert analysis.patches == ()
    assert analysis.idat_count == 2


def test_idat_chain_repairs_length_and_type_before_iend():
    data = (
        sample_prefix()
        + raw_chunk(4, b"IDAT", b"aaaa")
        + raw_chunk(4, b"IDAT", b"0000")
        + raw_chunk(5, b"@DAT", b"bbbb")
        + raw_chunk(4, b"IDAT", b"cccc")
        + IEND_CHUNK
    )

    analysis = idat_chain.analyze_idat_chain_headers(data)

    assert analysis.repairable is True
    assert analysis.status == "repairable"
    assert len(analysis.patches) == 1
    patch = analysis.patches[0]
    assert patch.old_length == 5
    assert patch.new_length == 4
    assert patch.old_type == b"@DAT"
    assert analysis.fixed_data is not None
    reparsed = idat_chain.analyze_idat_chain_headers(analysis.fixed_data)
    assert reparsed.status == "ok"


def test_idat_chain_repairs_idatish_bad_names_on_grid():
    data = (
        sample_prefix()
        + raw_chunk(4, b"IDAT", b"aaaa")
        + raw_chunk(4, b"IDAT", b"0000")
        + raw_chunk(4, b"IDA^", b"bbbb")
        + raw_chunk(4, b"IDAF", b"cccc")
        + raw_chunk(4, b"ZDAT", b"dddd")
        + raw_chunk(4, b"`DAT", b"eeee")
        + IEND_CHUNK
    )

    analysis = idat_chain.analyze_idat_chain_headers(data)

    assert analysis.repairable is True
    assert [patch.old_type for patch in analysis.patches] == [
        b"IDA^",
        b"IDAF",
        b"ZDAT",
        b"`DAT",
    ]
    assert idat_chain.analyze_idat_chain_headers(analysis.fixed_data).status == "ok"


def test_idat_chain_accepts_last_short_idat_before_iend():
    data = (
        sample_prefix()
        + raw_chunk(4, b"IDAT", b"aaaa")
        + raw_chunk(4, b"IDAT", b"bbbb")
        + raw_chunk(3, b"`DAT", b"cc")
        + IEND_CHUNK
    )

    analysis = idat_chain.analyze_idat_chain_headers(data)

    assert analysis.repairable is True
    patch = analysis.patches[0]
    assert patch.old_length == 3
    assert patch.new_length == 2
    assert patch.old_type == b"`DAT"
    assert idat_chain.analyze_idat_chain_headers(analysis.fixed_data).status == "ok"


def test_idat_chain_without_iend_is_candidate_not_repairable():
    data = (
        sample_prefix()
        + raw_chunk(4, b"IDAT", b"aaaa")
        + raw_chunk(4, b"IDAT", b"bbbb")
        + raw_chunk(5, b"@DAT", b"cccc")
    )

    analysis = idat_chain.analyze_idat_chain_headers(data)

    assert analysis.status == "candidate_without_iend"
    assert analysis.repairable is False
    assert analysis.fixed_data is None


def test_idat_chain_rejects_non_idatish_grid_noise():
    data = (
        sample_prefix()
        + raw_chunk(4, b"IDAT", b"aaaa")
        + raw_chunk(4, b"zzzz", b"bbbb")
        + IEND_CHUNK
    )

    analysis = idat_chain.analyze_idat_chain_headers(data)

    assert analysis.status == "unsupported"
    assert analysis.repairable is False


def run_all():
    checks = [
        ("complete", test_idat_chain_complete_without_patch_is_ok),
        ("length and type", test_idat_chain_repairs_length_and_type_before_iend),
        ("bad names", test_idat_chain_repairs_idatish_bad_names_on_grid),
        ("last short IDAT", test_idat_chain_accepts_last_short_idat_before_iend),
        ("without IEND", test_idat_chain_without_iend_is_candidate_not_repairable),
        ("reject noise", test_idat_chain_rejects_non_idatish_grid_noise),
    ]
    print("Running IDAT chain tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")
    print(f"IDAT chain tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    run_all()
