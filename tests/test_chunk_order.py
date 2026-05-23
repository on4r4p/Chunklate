#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import chunk_order
from chunklate import nearby


def test_as_chunk_bytes_preserves_bytes_and_encodes_text():
    assert chunk_order.as_chunk_bytes(b"IHDR") == b"IHDR"
    assert chunk_order.as_chunk_bytes("IHDR") == b"IHDR"


def test_chunk_name_decoding_helpers_preserve_legacy_decode_errors_ignore():
    assert chunk_order.decode_chunk_name(b"IHDR") == "IHDR"
    assert chunk_order.decode_chunk_name(b"\xffID") == "ID"
    assert chunk_order.decode_chunk_names([b"IHDR", b"\xffID"]) == ["IHDR", "ID"]


def test_missing_critical_chunks_preserves_legacy_messages_source():
    missing = chunk_order.missing_critical_chunks(
        [b"PNG", b"IHDR"],
        (b"PNG", b"IHDR", b"IDAT", b"IEND"),
    )
    findings = list(chunk_order.missing_critical_infos(missing))

    assert missing == (b"IDAT", b"IEND")
    assert tuple(findings) == (
        "-Critical Chunk b'IDAT' is Missing",
        "-Critical Chunk b'IEND' is Missing",
    )
    assert chunk_order.has_findings(findings) is True
    assert chunk_order.has_findings([]) is False
    assert chunk_order.critical_checkpoint_args(findings) == (
        True,
        False,
        "CheckChunkOrder",
        "Critical",
        findings,
    )


def test_unique_seen_chunks_and_unique_exclusions_preserve_order():
    used = chunk_order.unique_seen_chunks([b"PNG", b"IHDR", b"IDAT", b"IDAT", b"IEND"])
    excluded = chunk_order.unique_chunk_exclusions(used, (b"PNG", b"IHDR", b"IEND"))
    context = chunk_order.build_chunk_order_context(
        [b"PNG", b"IHDR", b"IDAT", b"IDAT", b"IEND"],
        (b"PNG", b"IHDR", b"IEND"),
    )

    assert used == (b"PNG", b"IHDR", b"IDAT", b"IEND")
    assert excluded == (b"PNG", b"IHDR", b"IEND")
    assert context.used_chunks == used
    assert context.excluded_chunks == excluded


def test_legacy_unique_chunk_multiple_check_preserves_current_behavior():
    excluded = (b"PNG", b"IHDR")

    assert chunk_order.legacy_flags_unique_chunk_as_multiple(b"IHDR", excluded, (b"IHDR",))
    assert not chunk_order.legacy_flags_unique_chunk_as_multiple(b"IDAT", excluded, (b"IHDR",))
    assert chunk_order.multiple_chunk_info() == "-Multiple"
    assert chunk_order.missplaced_info() == "-Missplaced"
    findings = [chunk_order.missplaced_info()]
    assert chunk_order.missplaced_checkpoint_args(findings) == (
        True,
        False,
        "CheckChunkOrder",
        "Missplaced",
        findings,
    )


def test_signature_and_ihdr_placement_decisions():
    assert chunk_order.png_signature_is_misplaced([b"IHDR"])
    assert not chunk_order.png_signature_is_misplaced([b"PNG", b"IHDR"])
    assert chunk_order.ihdr_is_misplaced([b"PNG", b"IDAT"])
    assert not chunk_order.ihdr_is_misplaced([b"PNG", b"IHDR"])
    assert chunk_order.ihdr_misplacement_already_recorded(
        {"Check_Error_0:Should be IHDR Instead At Chunk Number:1": {}}
    )
    assert chunk_order.ihdr_misplacement_checkpoint_args([b"PNG", b"IDAT"]) == (
        True,
        False,
        "CheckChunkOrder",
        b"IDAT",
        ["-Missplaced [b'IDAT'] Should be IHDR Instead At Chunk Number:1"],
        b"IDAT",
        1,
        b"IHDR",
    )


def test_plte_and_idat_order_decisions():
    used = (b"PNG", b"IHDR", b"PLTE", b"IDAT")

    assert chunk_order.must_appear_before_plte(b"gAMA", used, (b"gAMA", b"cHRM"))
    assert not chunk_order.must_appear_before_plte(b"tEXt", used, (b"gAMA", b"cHRM"))
    assert chunk_order.missplaced_before_plte_info(b"gAMA") == (
        "-gAMA is missplaced must appears before PLTE Chunk"
    )
    assert chunk_order.must_appear_before_idat(b"gAMA", used, (), (b"gAMA", b"cHRM"))
    assert chunk_order.must_appear_before_idat(b"IHDR", used, (b"IHDR",), ())
    assert not chunk_order.must_appear_before_idat(b"tEXt", used, (), (b"gAMA", b"cHRM"))


def test_only_ihdr_allowed_after_png_header():
    assert chunk_order.only_ihdr_allowed_after_png_header(
        [b"PNG"],
        (b"IHDR", b"IDAT", b"IEND"),
    ) == (b"IDAT", b"IEND")
    assert chunk_order.only_ihdr_allowed_after_png_header(
        [b"PNG", b"IHDR"],
        (b"IHDR", b"IDAT", b"IEND"),
    ) is None


def test_fix_mode_exclusion_helpers_preserve_legacy_list_growth():
    chunks = (b"IHDR", b"gAMA", b"PLTE", b"IDAT", b"IEND")
    before_plte = (b"IHDR", b"gAMA")

    assert chunk_order.must_stay_before_plte_without_ihdr(b"gAMA", (b"PNG",), before_plte)
    assert not chunk_order.must_stay_before_plte_without_ihdr(b"gAMA", (b"PNG", b"IHDR"), before_plte)
    assert chunk_order.must_follow_plte(b"tRNS", (b"tRNS", b"bKGD"))
    assert not chunk_order.must_follow_plte(b"gAMA", (b"tRNS", b"bKGD"))
    assert chunk_order.has_idat((b"IHDR", b"IDAT")) is True
    assert chunk_order.has_idat((b"IHDR", b"PLTE")) is False
    assert chunk_order.add_iend_exclusion((b"IHDR",)) == (b"IHDR", b"IEND")
    assert chunk_order.extend_exclusions_not_in((b"IHDR",), chunks, before_plte) == (
        b"IHDR",
        b"PLTE",
        b"IDAT",
        b"IEND",
    )
    assert chunk_order.extend_exclusions_in((b"PNG",), chunks, before_plte) == (
        b"PNG",
        b"IHDR",
        b"gAMA",
    )
    assert chunk_order.extend_exclusions_before_idat_after_idat(
        (b"IHDR",),
        chunks,
        (b"IHDR", b"gAMA", b"PLTE"),
    ) == (
        b"IHDR",
        b"gAMA",
        b"PLTE",
    )


def test_missing_critical_palette_warning_preserves_legacy_precedence():
    assert chunk_order.may_have_missing_critical_palette("2", [b"IHDR", b"IDAT"]) is True
    assert chunk_order.may_have_missing_critical_palette("2", [b"IHDR", b"PLTE", b"IDAT"]) is True
    assert chunk_order.may_have_missing_critical_palette("6", [b"IHDR", b"IDAT"]) is True
    assert chunk_order.may_have_missing_critical_palette("6", [b"IHDR", b"PLTE", b"IDAT"]) is False
    assert chunk_order.may_have_missing_critical_palette("0", [b"IHDR", b"IDAT"]) is False
    assert chunk_order.missing_critical_palette_info() == (
        "-There is a chance that some Critical Palette chunks are missing."
    )


def test_indexed_color_idat_plte_predicates_preserve_legacy_rules():
    assert chunk_order.is_indexed_color("3") is True
    assert chunk_order.is_indexed_color(2) is False
    assert chunk_order.indexed_idat_previous_chunk_is_plte([b"IHDR", b"PLTE", b"IDAT"]) is True
    assert chunk_order.indexed_idat_previous_chunk_is_plte([b"IHDR", b"gAMA", b"IDAT"]) is False
    assert chunk_order.indexed_idat_previous_chunk_is_plte([b"IDAT", b"PLTE"]) is True
    assert chunk_order.is_idat_chunk(b"IDAT") is True
    assert chunk_order.is_idat_chunk(b"PLTE") is False


def test_the_good_place_checkpoint_args_preserve_missing_and_found_shapes():
    assert chunk_order.the_good_place_missing_checkpoint_args(b"IHDR", 1, 20, 40) == (
        True,
        False,
        "TheGoodPlace",
        b"IHDR",
        ["-Missing Data Has Not Been Found : [b'IHDR']"],
        b"IHDR",
        1,
        20,
        40,
    )
    assert chunk_order.the_good_place_found_checkpoint_args(
        b"IHDR",
        nearby.HistoryChunkPosition(2, 60, 90),
        "fixed-data",
    ) == (
        True,
        True,
        "TheGoodPlace",
        b"IHDR",
        ["-Found Missing Data:[b'IHDR'] at Chunk Position:2 Starting at:60 Ending at:90"],
        "fixed-data",
    )


def main():
    checks = [
        ("Chunk bytes coercion", test_as_chunk_bytes_preserves_bytes_and_encodes_text),
        ("Chunk name decoding", test_chunk_name_decoding_helpers_preserve_legacy_decode_errors_ignore),
        ("Missing critical chunks", test_missing_critical_chunks_preserves_legacy_messages_source),
        ("Unique chunk exclusions", test_unique_seen_chunks_and_unique_exclusions_preserve_order),
        ("Legacy unique multiple check", test_legacy_unique_chunk_multiple_check_preserves_current_behavior),
        ("Signature and IHDR placement", test_signature_and_ihdr_placement_decisions),
        ("PLTE and IDAT order decisions", test_plte_and_idat_order_decisions),
        ("Only IHDR after PNG header", test_only_ihdr_allowed_after_png_header),
        ("Fix mode exclusion helpers", test_fix_mode_exclusion_helpers_preserve_legacy_list_growth),
        ("Missing critical palette warning", test_missing_critical_palette_warning_preserves_legacy_precedence),
        ("Indexed IDAT PLTE predicates", test_indexed_color_idat_plte_predicates_preserve_legacy_rules),
        ("TheGoodPlace checkpoint args", test_the_good_place_checkpoint_args_preserve_missing_and_found_shapes),
    ]

    print("Running chunk order tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"chunk order tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
