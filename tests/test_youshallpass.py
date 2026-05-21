#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import Chunklate


def with_chunks_history(chunks, check):
    old_chunks = Chunklate.Chunks_History
    try:
        Chunklate.Chunks_History = chunks
        check()
    finally:
        Chunklate.Chunks_History = old_chunks


def with_iccp_state(chunks, raw_length, check):
    old_chunks = Chunklate.Chunks_History
    old_orig_cl = Chunklate.Orig_CL
    try:
        Chunklate.Chunks_History = chunks
        Chunklate.Orig_CL = raw_length
        check()
    finally:
        Chunklate.Chunks_History = old_chunks
        Chunklate.Orig_CL = old_orig_cl


def test_youshallpass_uses_phys_parser():
    assert Chunklate.YouShallPass(b"pHYs", "000000010000000201") is True
    assert Chunklate.YouShallPass(b"pHYs", "000000010000000202") is False
    assert Chunklate.YouShallPass(b"pHYs", "800000000000000201") is False


def test_youshallpass_uses_time_parser():
    assert Chunklate.YouShallPass(b"tIME", "07e80515112233") is True
    assert Chunklate.YouShallPass(b"tIME", "07ff0d20243d3d") is False
    assert Chunklate.YouShallPass(b"tIME", "00") is False


def test_youshallpass_uses_gama_parser():
    assert Chunklate.YouShallPass(b"gAMA", "0000b18f") is True
    assert Chunklate.YouShallPass(b"gAMA", "00000000") is False
    assert Chunklate.YouShallPass(b"gAMA", "zzzzzzzz") is False


def test_youshallpass_uses_ster_parser():
    assert Chunklate.YouShallPass(b"sTER", "00") is True
    assert Chunklate.YouShallPass(b"sTER", "01") is True
    assert Chunklate.YouShallPass(b"sTER", "02") is False


def test_youshallpass_uses_srgb_parser():
    def check_without_chrm():
        assert Chunklate.YouShallPass(b"sRGB", "00") is True
        assert Chunklate.YouShallPass(b"sRGB", "03") is True
        assert Chunklate.YouShallPass(b"sRGB", "04") is False

    def check_with_chrm():
        assert Chunklate.YouShallPass(b"sRGB", "00") is False

    with_chunks_history([], check_without_chrm)
    with_chunks_history([b"cHRM"], check_with_chrm)


def test_youshallpass_uses_chrm_parser():
    valid_chrm = (
        "00000001"
        "00000002"
        "00000003"
        "00000004"
        "00000005"
        "00000006"
        "00000007"
        "00000008"
    )

    def check_without_override():
        assert Chunklate.YouShallPass(b"cHRM", valid_chrm) is True
        assert Chunklate.YouShallPass(b"cHRM", "zz" + valid_chrm[2:]) is False

    def check_with_override():
        assert Chunklate.YouShallPass(b"cHRM", valid_chrm) is False

    with_chunks_history([], check_without_override)
    with_chunks_history([b"sRGB"], check_with_override)


def test_youshallpass_uses_offs_parser():
    assert Chunklate.YouShallPass(b"oFFs", "00000001ffffffff01") is True
    assert Chunklate.YouShallPass(b"oFFs", "800000007fffffff01") is False
    assert Chunklate.YouShallPass(b"oFFs", "000000010000000102") is False


def test_youshallpass_uses_gifg_parser():
    assert Chunklate.YouShallPass(b"gIFg", "010203") is True
    assert Chunklate.YouShallPass(b"gIFg", "01") is False
    assert Chunklate.YouShallPass(b"gIFg", "0102zz") is False


def test_youshallpass_uses_gifx_parser():
    assert Chunklate.YouShallPass(b"gIFx", "0000000000000001000002ff") is True
    assert Chunklate.YouShallPass(b"gIFx", "0000000000000001000002") is False
    assert Chunklate.YouShallPass(b"gIFx", "0000000000000001000002zz") is False


def test_youshallpass_uses_iccp_parser():
    def check_without_chrm():
        assert Chunklate.YouShallPass(b"iCCP", "4943430000abcd") is True
        assert Chunklate.YouShallPass(b"iCCP", "4943430001abcd") is False
        assert Chunklate.YouShallPass(b"iCCP", "0143430000abcd") is False

    def check_bad_length():
        assert Chunklate.YouShallPass(b"iCCP", "4943430000abcd") is False

    def check_with_chrm():
        assert Chunklate.YouShallPass(b"iCCP", "4943430000abcd") is False

    with_iccp_state([], "00000007", check_without_chrm)
    with_iccp_state([], "00000008", check_bad_length)
    with_iccp_state([b"cHRM"], "00000007", check_with_chrm)


def test_youshallpass_uses_exif_parser():
    assert Chunklate.YouShallPass(b"eXIf", "494900000000") is True
    assert Chunklate.YouShallPass(b"eXIf", "4d4d") is True
    assert Chunklate.YouShallPass(b"eXIf", "0000") is False
    assert Chunklate.YouShallPass(b"eXIf", "zzzz") is False


def main():
    checks = [
        ("pHYs parser", test_youshallpass_uses_phys_parser),
        ("tIME parser", test_youshallpass_uses_time_parser),
        ("gAMA parser", test_youshallpass_uses_gama_parser),
        ("sTER parser", test_youshallpass_uses_ster_parser),
        ("sRGB parser", test_youshallpass_uses_srgb_parser),
        ("cHRM parser", test_youshallpass_uses_chrm_parser),
        ("oFFs parser", test_youshallpass_uses_offs_parser),
        ("gIFg parser", test_youshallpass_uses_gifg_parser),
        ("gIFx parser", test_youshallpass_uses_gifx_parser),
        ("iCCP parser", test_youshallpass_uses_iccp_parser),
        ("eXIf parser", test_youshallpass_uses_exif_parser),
    ]

    print("Running YouShallPass tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"YouShallPass tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
