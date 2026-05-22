#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import specs


def test_chunk_constant_groups_preserve_legacy_sets_and_order():
    assert specs.MINIMAL_CHUNKS == (b"PNG", b"IHDR", b"IDAT", b"IEND")
    assert specs.CRITICAL_CHUNKS == (b"PNG", b"IHDR", b"PLTE", b"IDAT", b"IEND")
    assert specs.CHUNKS[:4] == (b"sBIT", b"IEND", b"sPLT", b"tRNS")
    assert specs.CHUNKS[-3:] == (b"gIFt", b"pHYs", b"eXIf")
    assert specs.PRIVATE_CHUNKS[:3] == (b"cmOD", b"cmPP", b"cpIp")
    assert specs.PRIVATE_CHUNKS[-3:] == (b"ORDR", b"MAGN", b"MEND")
    assert specs.ALLCHUNKS == specs.CHUNKS + specs.PRIVATE_CHUNKS
    assert specs.CHUNKS_LEN_NOT_FIXED == (b"PLTE", b"tRNS", b"hIST")
    assert "known incorrect sRGB profile" in specs.LIBPNG_ERR


def test_min_res_iter_preserves_legacy_counting():
    assert specs.min_res_iter(1) == 0
    assert specs.min_res_iter(4) == 12


def test_iter_product_values_preserves_regular_product():
    assert list(specs.iter_product_values([(1, 2), (3,)], "nocolortype")) == [
        (1, 3),
        (2, 3),
    ]


def test_iter_product_values_expands_minres_width_height_pairs():
    assert list(specs.iter_product_values([(3,), (8,)], "colortype:2:minres")) == [
        (3, 1, 8),
        (1, 3, 8),
        (3, 2, 8),
        (2, 3, 8),
        (3, 3, 8),
    ]


def test_color_type_label_uses_safe_ihdr_color_and_brute_level():
    assert specs.color_type_label(
        b"IHDR",
        "Brutus",
        brute_level=0,
        ihdr_color="2",
        ihdr_height=10,
        ihdr_width=10,
        pandora_box={},
        cornucopia={},
        pandemonium={},
        allchunks=(b"IHDR",),
        skip_bad_crc=False,
    ) == "colortype:2:minres"
    assert specs.color_type_label(
        b"IHDR",
        "Brutus",
        brute_level=1,
        ihdr_color="2",
        ihdr_height=10,
        ihdr_width=10,
        pandora_box={},
        cornucopia={},
        pandemonium={},
        allchunks=(b"IHDR",),
        skip_bad_crc=False,
    ) == "colortype:2:medres"


def test_color_type_label_preserves_custom_minres_when_width_height_unknown():
    assert specs.color_type_label(
        b"IHDR",
        "Custom",
        brute_level=0,
        ihdr_color="2",
        ihdr_height=10,
        ihdr_width=10,
        pandora_box={
            "Check_Error_0:IHDR Width StructIndex:0": {},
            "Check_Error_1:IHDR Height StructIndex:1": {},
        },
        cornucopia={},
        pandemonium={},
        allchunks=(b"IHDR",),
        skip_bad_crc=False,
    ) == "colortype:2:minres"


def test_color_type_label_falls_back_when_ihdr_is_unsafe():
    assert specs.color_type_label(
        b"IHDR",
        "Custom",
        brute_level=0,
        ihdr_color="9",
        ihdr_height=10,
        ihdr_width=10,
        pandora_box={},
        cornucopia={},
        pandemonium={},
        allchunks=(b"IHDR",),
        skip_bad_crc=False,
    ) == "nocolortype:minres:custom"
    assert specs.color_type_label(
        b"bKGD",
        "Brutus",
        brute_level=0,
        ihdr_color="9",
        ihdr_height=10,
        ihdr_width=10,
        pandora_box={},
        cornucopia={},
        pandemonium={},
        allchunks=(b"IHDR",),
        skip_bad_crc=False,
    ) == "nocolortype"


def main():
    checks = [
        ("Chunk constant groups", test_chunk_constant_groups_preserve_legacy_sets_and_order),
        ("Min resolution iterator", test_min_res_iter_preserves_legacy_counting),
        ("Regular product", test_iter_product_values_preserves_regular_product),
        ("Minres product", test_iter_product_values_expands_minres_width_height_pairs),
        ("Safe color type", test_color_type_label_uses_safe_ihdr_color_and_brute_level),
        ("Custom minres", test_color_type_label_preserves_custom_minres_when_width_height_unknown),
        ("Unsafe color type", test_color_type_label_falls_back_when_ihdr_is_unsafe),
    ]

    print("Running specs tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"specs tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
