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


def test_missing_critical_chunks_preserves_legacy_messages_source():
    missing = chunk_order.missing_critical_chunks(
        [b"PNG", b"IHDR"],
        (b"PNG", b"IHDR", b"IDAT", b"IEND"),
    )

    assert missing == (b"IDAT", b"IEND")


def test_unique_seen_chunks_and_unique_exclusions_preserve_order():
    used = chunk_order.unique_seen_chunks([b"PNG", b"IHDR", b"IDAT", b"IDAT", b"IEND"])
    excluded = chunk_order.unique_chunk_exclusions(used, (b"PNG", b"IHDR", b"IEND"))

    assert used == (b"PNG", b"IHDR", b"IDAT", b"IEND")
    assert excluded == (b"PNG", b"IHDR", b"IEND")


def test_legacy_unique_chunk_multiple_check_preserves_current_behavior():
    excluded = (b"PNG", b"IHDR")

    assert chunk_order.legacy_flags_unique_chunk_as_multiple(b"IHDR", excluded, (b"IHDR",))
    assert not chunk_order.legacy_flags_unique_chunk_as_multiple(b"IDAT", excluded, (b"IHDR",))


def test_signature_and_ihdr_placement_decisions():
    assert chunk_order.png_signature_is_misplaced([b"IHDR"])
    assert not chunk_order.png_signature_is_misplaced([b"PNG", b"IHDR"])
    assert chunk_order.ihdr_is_misplaced([b"PNG", b"IDAT"])
    assert not chunk_order.ihdr_is_misplaced([b"PNG", b"IHDR"])
    assert chunk_order.ihdr_misplacement_already_recorded(
        {"Check_Error_0:Should be IHDR Instead At Chunk Number:1": {}}
    )


def test_plte_and_idat_order_decisions():
    used = (b"PNG", b"IHDR", b"PLTE", b"IDAT")

    assert chunk_order.must_appear_before_plte(b"gAMA", used, (b"gAMA", b"cHRM"))
    assert not chunk_order.must_appear_before_plte(b"tEXt", used, (b"gAMA", b"cHRM"))
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
        ("Missing critical chunks", test_missing_critical_chunks_preserves_legacy_messages_source),
        ("Unique chunk exclusions", test_unique_seen_chunks_and_unique_exclusions_preserve_order),
        ("Legacy unique multiple check", test_legacy_unique_chunk_multiple_check_preserves_current_behavior),
        ("Signature and IHDR placement", test_signature_and_ihdr_placement_decisions),
        ("PLTE and IDAT order decisions", test_plte_and_idat_order_decisions),
        ("Only IHDR after PNG header", test_only_ihdr_allowed_after_png_header),
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
