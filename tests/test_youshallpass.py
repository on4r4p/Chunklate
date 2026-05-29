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


def with_chunk_state(check, **updates):
    old_values = {name: getattr(Chunklate, name) for name in updates}
    try:
        for name, value in updates.items():
            setattr(Chunklate, name, value)
        check()
    finally:
        for name, value in old_values.items():
            setattr(Chunklate, name, value)


def test_youshallpass_uses_ihdr_parser():
    assert Chunklate.YouShallPass(b"IHDR", "00000020000000100802000000") is True
    assert Chunklate.YouShallPass(b"IHDR", "00000000000000100802000000") is False
    assert Chunklate.YouShallPass(b"IHDR", "00000020000000100303010202") is False


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
        assert Chunklate.YouShallPass(b"cHRM", valid_chrm[:-2]) is False
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


def test_youshallpass_uses_color_dependent_parsers():
    def check():
        assert Chunklate.YouShallPass(b"bKGD", "0007") is True
        assert Chunklate.YouShallPass(b"bKGD", "00070000") is False
        assert Chunklate.YouShallPass(b"bKGD", "0100") is False
        assert Chunklate.YouShallPass(b"sBIT", "08") is True
        assert Chunklate.YouShallPass(b"sBIT", "00") is False
        assert Chunklate.YouShallPass(b"tRNS", "0007") is True
        assert Chunklate.YouShallPass(b"tRNS", "") is False

    with_chunk_state(
        check,
        IHDR_Color="0",
        IHDR_Depht="8",
        Chunks_History=[],
        PLTE_R=[],
        PLTE_G=[],
        PLTE_B=[],
    )


def test_youshallpass_uses_palette_dependent_parsers():
    def check():
        assert Chunklate.YouShallPass(b"PLTE", "000102030405") is True
        assert Chunklate.YouShallPass(b"hIST", "00010002") is True
        assert Chunklate.YouShallPass(b"tRNS", "0001") is True
        assert Chunklate.YouShallPass(b"tRNS", "000102") is False

    with_chunk_state(
        check,
        IHDR_Color="3",
        IHDR_Depht="8",
        Chunks_History=[b"PLTE"],
        PLTE_R=["00", "03"],
        PLTE_G=["01", "04"],
        PLTE_B=["02", "05"],
    )


def test_youshallpass_uses_splt_parser():
    payload = "70616c0008" + ("01" * 13)

    assert Chunklate.YouShallPass(b"sPLT", payload) is True

    def check_duplicate():
        assert Chunklate.YouShallPass(b"sPLT", payload) is False

    with_chunk_state(check_duplicate, sPLT_Name=["70616c"])


def test_youshallpass_uses_text_parsers():
    assert Chunklate.YouShallPass(b"tEXt", "5469746c650048656c6c6f") is True
    assert Chunklate.YouShallPass(b"tEXt", "0048656c6c6f") is False
    assert Chunklate.YouShallPass(b"tEXt", ("41" * 80) + "00") is False
    assert Chunklate.YouShallPass(b"zTXt", "4b65790000789cf348cdc9c90700058c01f5") is True
    assert Chunklate.YouShallPass(b"zTXt", "0000789cf348cdc9c90700058c01f5") is False
    assert Chunklate.YouShallPass(b"zTXt", "4b65790000ff") is False
    assert Chunklate.YouShallPass(b"iTXt", "4b6579000000000048656c6c6f") is True
    assert Chunklate.YouShallPass(b"iTXt", "000000656e2d75730000437563756d626572") is False
    assert Chunklate.YouShallPass(b"iTXt", "4b6579000200000048656c6c6f") is False


def test_youshallpass_uses_pcal_parser():
    valid = (
        "43616c00"
        "00000001"
        "00000002"
        "00"
        "02"
        "703100"
        "703200"
    )

    assert Chunklate.YouShallPass(b"pCAL", valid) is True
    assert Chunklate.YouShallPass(b"pCAL", "010000000001000000020000") is False
    assert Chunklate.YouShallPass(b"pCAL", "43616c00") is False


def test_youshallpass_uses_exif_parser():
    assert Chunklate.YouShallPass(b"eXIf", "494900000000") is True
    assert Chunklate.YouShallPass(b"eXIf", "4d4d") is True
    assert Chunklate.YouShallPass(b"eXIf", "0000") is False
    assert Chunklate.YouShallPass(b"eXIf", "zzzz") is False


def main():
    checks = [
        ("IHDR parser", test_youshallpass_uses_ihdr_parser),
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
        ("color dependent parsers", test_youshallpass_uses_color_dependent_parsers),
        ("palette dependent parsers", test_youshallpass_uses_palette_dependent_parsers),
        ("sPLT parser", test_youshallpass_uses_splt_parser),
        ("text parsers", test_youshallpass_uses_text_parsers),
        ("pCAL parser", test_youshallpass_uses_pcal_parser),
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
