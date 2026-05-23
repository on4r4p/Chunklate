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


def test_normalize_chunk_format_preserves_legacy_string_and_tuple_modes():
    assert specs.normalize_chunk_format("!H") == ["!H"]
    assert specs.normalize_chunk_format("!B") == ["!B"]
    assert specs.normalize_chunk_format(("!I", "!B")) == ("!I", "!B")


def test_expand_chunk_data_item_preserves_legacy_range_and_tuple_conversion():
    assert specs.expand_chunk_data_item("i for i in range(1,4)") == (1, 2, 3)
    assert specs.expand_chunk_data_item((0, 1)) == (0, 1)
    assert specs.expand_chunk_data_item("1229278788") == tuple("1229278788")


def test_expand_spec_values_preserves_legacy_iteration_expansion():
    assert specs.expand_spec_values(
        3,
        2,
        ("!B",),
        ("i for i in range(0,2)", (8, 16)),
        2,
    ) == (
        9,
        4,
        ("!B", "!B"),
        ((0, 1), (8, 16), (0, 1), (8, 16)),
    )


def test_expand_spec_values_preserves_tuple_length_multiplication():
    assert specs.expand_spec_values(
        2,
        (6, 1536),
        ("!B",),
        ((0,),),
        2,
    ) == (
        4,
        (6, 1536, 6, 1536),
        ("!B", "!B"),
        ((0,), (0,)),
    )


def test_apply_custom_spec_selection_counts_selected_fields_and_minres_pair():
    assert specs.apply_custom_spec_selection(
        ((1, 2, 3), (4, 5), (6,)),
        (0, 1),
        7,
    ) == (
        42,
        ((1, 2, 3), (4, 5)),
    )


def test_apply_custom_spec_selection_skips_minres_when_width_height_pair_is_incomplete():
    assert specs.apply_custom_spec_selection(
        ((1, 2, 3), (4, 5), (6,)),
        (1,),
        7,
    ) == (
        2,
        ((4, 5),),
    )


def test_build_chunks_spec_preserves_dynamic_legacy_values():
    chunks_spec = specs.build_chunks_spec(
        current_year=2026,
        idat_byte_count=640,
        max_resolution=100,
        min_resolution=10,
        min_resolution_product=90,
    )

    assert chunks_spec[b"IHDR"]["colortype:2:minres"] == (
        360,
        26,
        ("!I", "!I", "!B", "!B", "!B", "!B", "!B"),
        (
            "i for i in range(0,10)",
            (8, 16),
            "2",
            "0",
            "0",
            (0, 1),
        ),
    )
    assert chunks_spec[b"IHDR"]["colortype:2:minres:custom"][3][:2] == (
        "i for i in range(1,10)",
        "i for i in range(1,10)",
    )
    assert chunks_spec[b"tIME"]["nocolortype"][0] == ((1970 - 2026) * 12 * 31 * 23 * 59 * 60)
    assert chunks_spec[b"tIME"]["nocolortype"][3][0] == "i for i in range(1970,2027)"
    assert chunks_spec[b"IDAT"]["nocolortype"] == (
        256,
        (2, 4),
        "!B",
        ("i for i in range(0,256)",),
    )


def test_find_chunk_spec_preserves_nested_lookup_shape():
    chunks_spec = {
        b"IHDR": {"nocolortype": ("wrong",), "colortype:2:minres": ("right",)},
        b"IDAT": {"nocolortype": ("idat",)},
    }

    assert specs.find_chunk_spec(chunks_spec, b"IHDR", "colortype:2:minres") == ("right",)
    assert specs.find_chunk_spec(chunks_spec, b"PLTE", "nocolortype") is None
    assert specs.find_chunk_spec(chunks_spec, b"IHDR", "missing") is None


def test_select_spec_fields_preserves_all_and_field_order():
    assert specs.select_spec_fields(
        123,
        8,
        ("!I",),
        ((1, 2),),
        "nocolortype",
        ["All"],
    ) == (
        123,
        3,
        8,
        ("!I",),
        ((1, 2),),
        "nocolortype",
    )
    assert specs.select_spec_fields(
        123,
        8,
        ("!I",),
        ((1, 2),),
        "nocolortype",
        ["Length", "Format", "Data", "Color", "Product"],
    ) == (
        8,
        ("!I",),
        ((1, 2),),
        "nocolortype",
        123,
        3,
    )
    assert specs.select_spec_fields(123, 8, ("!I",), ((1, 2),), "nocolortype", []) is None


def test_resolve_getspec_result_preserves_expansion_and_selected_fields():
    assert specs.resolve_getspec_result(
        (
            3,
            2,
            ("!B",),
            ("i for i in range(0,2)", (8, 16)),
        ),
        "nocolortype",
        ["Length", "Format", "Data", "Product"],
        "Spec",
        None,
        2,
        7,
    ) == (
        4,
        ("!B", "!B"),
        ((0, 1), (8, 16), (0, 1), (8, 16)),
        9,
        1,
    )


def test_resolve_getspec_result_preserves_custom_selection():
    assert specs.resolve_getspec_result(
        (
            3,
            2,
            ("!B",),
            ((1, 2, 3), (4, 5), (6,)),
        ),
        "nocolortype",
        ["All"],
        "Custom",
        (0, 1),
        1,
        7,
    ) == (
        42,
        2,
        2,
        ("!B",),
        ((1, 2, 3), (4, 5)),
        "nocolortype",
    )


def test_getspec_color_type_only_uses_ihdr_state_for_color_sensitive_chunks():
    assert specs.getspec_color_type(
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
    assert specs.getspec_color_type(
        b"IDAT",
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
    ) == "nocolortype"


def test_build_getspec_context_preserves_color_resolution_and_specs():
    context = specs.build_getspec_context(
        current_year=2026,
        chunk_name=b"IHDR",
        mode="Brutus",
        idat_byte_count=640,
        max_resolution=100,
        brute_level=0,
        ihdr_color="2",
        ihdr_height=10,
        ihdr_width=10,
        pandora_box={},
        cornucopia={},
        pandemonium={},
        allchunks=(b"IHDR",),
        skip_bad_crc=False,
    )

    assert context.color_type == "colortype:2:minres"
    assert context.min_resolution == 10
    assert context.min_resolution_product == 90
    assert context.chunks_spec[b"IHDR"]["colortype:2:minres"][0] == 360


def test_resolve_getspec_uses_context_lookup_and_min_resolution():
    context = specs.GetSpecContext(
        color_type="nocolortype",
        min_resolution=7,
        min_resolution_product=42,
        chunks_spec={
            b"IHDR": {
                "nocolortype": (
                    3,
                    2,
                    ("!B",),
                    ((1, 2, 3), (4, 5), (6,)),
                )
            }
        },
    )

    assert specs.resolve_getspec(context, b"IHDR", ["All"], "Custom", (0, 1), 1) == (
        42,
        2,
        2,
        ("!B",),
        ((1, 2, 3), (4, 5)),
        "nocolortype",
    )
    assert specs.resolve_getspec(context, b"IDAT", ["All"], "Custom", (0, 1), 1) is None


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
        ("Normalize chunk format", test_normalize_chunk_format_preserves_legacy_string_and_tuple_modes),
        ("Expand chunk data item", test_expand_chunk_data_item_preserves_legacy_range_and_tuple_conversion),
        ("Expand spec values", test_expand_spec_values_preserves_legacy_iteration_expansion),
        ("Expand spec tuple length", test_expand_spec_values_preserves_tuple_length_multiplication),
        ("Custom spec selection", test_apply_custom_spec_selection_counts_selected_fields_and_minres_pair),
        ("Custom spec selection partial", test_apply_custom_spec_selection_skips_minres_when_width_height_pair_is_incomplete),
        ("Build chunk specs", test_build_chunks_spec_preserves_dynamic_legacy_values),
        ("Find chunk spec", test_find_chunk_spec_preserves_nested_lookup_shape),
        ("Select spec fields", test_select_spec_fields_preserves_all_and_field_order),
        ("Resolve spec result", test_resolve_getspec_result_preserves_expansion_and_selected_fields),
        ("Resolve custom spec result", test_resolve_getspec_result_preserves_custom_selection),
        ("GetSpec color type", test_getspec_color_type_only_uses_ihdr_state_for_color_sensitive_chunks),
        ("Build GetSpec context", test_build_getspec_context_preserves_color_resolution_and_specs),
        ("Resolve GetSpec", test_resolve_getspec_uses_context_lookup_and_min_resolution),
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
