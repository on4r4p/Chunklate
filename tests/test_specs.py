#!/usr/bin/env python3
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import specs
from chunklate.png import IEND_CHUNK, PNG_SIGNATURE, build_png_chunk


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


def test_estimate_max_resolution_preserves_legacy_formula():
    assert specs.estimate_max_resolution(10) == 57
    assert specs.estimate_max_resolution(78) == 16
    assert specs.estimate_max_resolution(1000) == 563


def test_estimate_max_resolution_from_file_uses_file_size(tmp_path):
    sample = tmp_path / "sample.bin"
    sample.write_bytes(b"x" * 78)

    assert specs.estimate_max_resolution_from_file(str(sample)) == (16, 78)


def test_resolution_iteration_bounds_preserves_legacy_minres_logic():
    assert specs.resolution_iteration_bounds(640, "colortype:2:minres") == (10, 90)
    assert specs.resolution_iteration_bounds(640, "nocolortype") == (10, 100)
    assert specs.resolution_iteration_bounds(1280000, "nocolortype") == (10000, 100000000)


def test_estimate_idat_bytes_from_hex_preserves_legacy_scan():
    single = PNG_SIGNATURE + build_png_chunk(b"IDAT", b"abc") + IEND_CHUNK
    multiple = (
        PNG_SIGNATURE
        + build_png_chunk(b"IDAT", b"ab")
        + build_png_chunk(b"IDAT", b"cdef")
        + IEND_CHUNK
    )

    assert specs.estimate_idat_bytes_from_hex(single.hex()) == 3
    assert specs.estimate_idat_bytes_from_hex(multiple.hex()) == 6
    assert specs.estimate_idat_bytes_from_hex("not hex at all") == 0


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
    tmp = tempfile.TemporaryDirectory()
    tmp_path = Path(tmp.name)
    checks = [
        ("Chunk constant groups", test_chunk_constant_groups_preserve_legacy_sets_and_order),
        ("Min resolution iterator", test_min_res_iter_preserves_legacy_counting),
        ("Max resolution estimate", test_estimate_max_resolution_preserves_legacy_formula),
        ("Max resolution estimate from file", lambda: test_estimate_max_resolution_from_file_uses_file_size(tmp_path)),
        ("Resolution iteration bounds", test_resolution_iteration_bounds_preserves_legacy_minres_logic),
        ("IDAT bytes estimate", test_estimate_idat_bytes_from_hex_preserves_legacy_scan),
        ("Regular product", test_iter_product_values_preserves_regular_product),
        ("Minres product", test_iter_product_values_expands_minres_width_height_pairs),
        ("Safe color type", test_color_type_label_uses_safe_ihdr_color_and_brute_level),
        ("Custom minres", test_color_type_label_preserves_custom_minres_when_width_height_unknown),
        ("Unsafe color type", test_color_type_label_falls_back_when_ihdr_is_unsafe),
    ]

    try:
        print("Running specs tests")
        for label, check in checks:
            print(f"  - {label} ... ", end="", flush=True)
            check()
            print("ok")

        print(f"specs tests passed ({len(checks)} checks)")
    finally:
        tmp.cleanup()


if __name__ == "__main__":
    main()
