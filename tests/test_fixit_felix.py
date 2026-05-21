#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import fixit_felix
from chunklate.png import iter_chunks


REPAIR_FIXTURES = ROOT / "Png_Errors_handled_by_Chunklate_So_Far"


def read_fixture(name):
    return (REPAIR_FIXTURES / name).read_bytes()


def test_route_finding_keeps_legacy_handler_order():
    assert fixit_felix.route_finding("Checksum_Error_0:Wrong Crc", skip_bad_crc=False).handler == "wrong_crc"
    assert fixit_felix.route_finding("Libpng_Error_0:libpng error: bad adaptive filter", skip_bad_crc=False).handler == "libpng_error"
    assert fixit_felix.route_finding("CheckChunkName_Error_0:has Wrong Chunk name at offset: 42", skip_bad_crc=False).handler == "wrong_chunk_name"
    assert fixit_felix.route_finding("CheckLength_Error_0:-No NextChunk", skip_bad_crc=False).handler == "no_next_chunk"
    assert fixit_felix.route_finding("GetInfo_Error_0:gAMA Chunk of 0 is Useless", skip_bad_crc=False).handler == "gama_zero"
    assert fixit_felix.route_finding("CheckChunkOrder_Error_0:Critical", skip_bad_crc=False).handler == "critical_miss"


def test_route_finding_preserves_skip_bad_crc_fallthrough():
    route = fixit_felix.route_finding("Checksum_Error_0:Wrong Crc", skip_bad_crc=True)

    assert route.handler == "critical_miss"


def test_gama_zero_false_positive_keeps_legacy_note():
    fix = fixit_felix.gama_zero_false_positive("GetInfo_Error_0:gAMA Chunk of 0 is Useless")

    assert fix.finding == "GetInfo_Error_0:gAMA Chunk of 0 is Useless"
    assert fix.note == "-Found False-Positive :[Error:-GetInfo_Error_0:gAMA Chunk of 0 is Useless]."


def test_libpng_error_decision_orders_solved_and_terminal_cases():
    assert (
        fixit_felix.libpng_error_decision("libpng error: anything", solved=True, skip_bad_libpng=False).action
        == "save_existing_solution"
    )
    assert (
        fixit_felix.libpng_error_decision("libpng error: Not enough image data", solved=False, skip_bad_libpng=False).action
        == "not_enough_image_data"
    )
    assert (
        fixit_felix.libpng_error_decision("libpng error: bad adaptive filter", solved=False, skip_bad_libpng=True).action
        == "skip"
    )
    assert (
        fixit_felix.libpng_error_decision("libpng error: bad adaptive filter", solved=False, skip_bad_libpng=False).action
        == "ask_relics"
    )


def test_wrong_crc_decision_keeps_easy_fix_before_other_errors():
    solved = fixit_felix.wrong_crc_decision("Checksum_Error_0:Wrong Crc", solved=True, pandora_box_len=1)
    easy = fixit_felix.wrong_crc_decision("Checksum_Error_0:Wrong Crc", solved=False, pandora_box_len=1)
    crowded = fixit_felix.wrong_crc_decision("Checksum_Error_0:Wrong Crc", solved=False, pandora_box_len=4)

    assert solved.action == "already_in_cornucopia"
    assert solved.other_error_count == 0
    assert easy.action == "ask_easy_crc_fix"
    assert easy.other_error_count == 0
    assert crowded.action == "ask_other_errors_first"
    assert crowded.other_error_count == 3


def test_wrong_chunk_name_decision_keeps_length_probe_before_bruteforce():
    assert (
        fixit_felix.wrong_chunk_name_decision(
            "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42 and length is not the same than before.",
            solved=False,
            bad_crc=True,
        ).action
        == "ask_length_probe"
    )
    assert (
        fixit_felix.wrong_chunk_name_decision(
            "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42",
            solved=False,
            bad_crc=True,
        ).action
        == "ask_bruteforce"
    )
    assert (
        fixit_felix.wrong_chunk_name_decision(
            "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42",
            solved=True,
            bad_crc=False,
        ).action
        == "save_existing_solution"
    )


def test_no_next_chunk_decision_orders_iend_and_recovery_paths():
    assert (
        fixit_felix.no_next_chunk_decision(
            current_chunk=b"IEND",
            chunk_type=b"IEND",
            chunk_length="0",
            bad_critical=False,
        ).action
        == "false_positive_iend"
    )
    assert (
        fixit_felix.no_next_chunk_decision(
            current_chunk=b"IDAT",
            chunk_type=b"IEND",
            chunk_length="1",
            bad_critical=False,
        ).action
        == "wrong_iend_length"
    )
    assert (
        fixit_felix.no_next_chunk_decision(
            current_chunk=b"IDAT",
            chunk_type=b"IDAT",
            chunk_length="12",
            bad_critical=True,
        ).action
        == "append_missing_iend"
    )
    assert (
        fixit_felix.no_next_chunk_decision(
            current_chunk=b"IDAT",
            chunk_type=b"IDAT",
            chunk_length="12",
            bad_critical=False,
        ).action
        == "ask_length_probe"
    )


def test_applied_repair_formats_legacy_note_and_save_suffix():
    class Repair:
        data = b"\x89PNG"
        strategy = "Some repair strategy"

    applied = fixit_felix.applied_repair(Repair())

    assert applied.data_hex == "89504e47"
    assert applied.note == "-FixItFelix:Some repair strategy."
    assert applied.save_suffix == "-Some repair strategy."


def test_applied_repair_adds_ihdr_metadata_when_available():
    class Repair:
        data = b"\x89PNG"
        strategy = "rebuilt missing IHDR from IDAT scanline size"
        width = 32
        height = 32
        bit_depth = 8
        color_type = 3
        strict_candidate_count = 4
        selection_score = (1, 1, 1, 1024, 0)

    applied = fixit_felix.applied_repair(Repair())

    assert applied.data_hex == "89504e47"
    assert "-FixItFelix:rebuilt missing IHDR from IDAT scanline size." in applied.note
    assert "-FixItFelix:Selected IHDR 32x32, bit depth 8, color type 3." in applied.note
    assert "-FixItFelix:strict candidates: 4." in applied.note
    assert "-FixItFelix:selection score: (1, 1, 1, 1024, 0)." in applied.note
    assert applied.save_suffix == "-rebuilt missing IHDR from IDAT scanline size."


def test_automatic_repair_order_keeps_legacy_priority():
    assert fixit_felix.automatic_repair_order() == (
        "color_profile_cleanup",
        "plte_cleanup",
        "known_chunk_type_case",
        "unknown_private_critical_removal",
        "missing_chunk_data_byte",
        "ihdr_rebuild",
    )


def test_color_profile_cleanup_requires_matching_finding():
    original = read_fixture("IncorrectSrgbProfile.png")

    assert fixit_felix.color_profile_cleanup(original, []) is None

    repaired = fixit_felix.color_profile_cleanup(original, ["libpng warning: known incorrect sRGB profile"])

    assert repaired is not None
    assert b"iCCP" not in {chunk.chunk_type for chunk in iter_chunks(repaired.data)}


def test_plte_cleanup_requires_noninteractive_mode_and_plte_finding():
    original = read_fixture("PLTE_Empty_Bad_Crc.png")

    assert fixit_felix.plte_cleanup(original, ["PLTE"], auto=False, nodialogue=False, max_saves=None) is None
    assert fixit_felix.plte_cleanup(original, ["Wrong Crc"], auto=True, nodialogue=False, max_saves=None) is None

    repaired = fixit_felix.plte_cleanup(original, ["PLTE"], auto=False, nodialogue=False, max_saves=1)

    assert repaired is not None
    assert b"PLTE" not in {chunk.chunk_type for chunk in iter_chunks(repaired.data)}


def test_missing_chunk_data_byte_requires_crc_or_no_next_finding():
    original = read_fixture("Good-Chunk-lenght-Missing-Bit.png")

    assert fixit_felix.missing_chunk_data_byte(original, []) is None

    repaired = fixit_felix.missing_chunk_data_byte(original, ["Checksum_Error_0:Wrong Crc"])

    assert repaired is not None
    assert repaired.chunk_name == "PLTE"


def test_known_chunk_type_case_requires_wrong_ancillary_finding():
    original = read_fixture("chunk_private_critical.png")

    assert fixit_felix.known_chunk_type_case(original, [], [b"gAMA"]) is None

    repaired = fixit_felix.known_chunk_type_case(
        original,
        ["CheckChunkName_Error_0:Wrong Ancillary in known Chunk name"],
        [b"gAMA"],
    )

    assert repaired is not None
    assert repaired.original_name == "GaMA"
    assert repaired.repaired_name == "gAMA"


def test_unknown_private_critical_removal_is_standalone_salvage():
    original = read_fixture("Unhandled-Critical-Chunk.png")

    repaired = fixit_felix.unknown_private_critical_removal(original, [b"IHDR", b"gAMA", b"PLTE", b"IDAT", b"IEND"])

    assert repaired is not None
    assert repaired.removed_chunks == ("QpZZ",)


def test_ihdr_rebuild_requires_ihdr_finding():
    original = read_fixture("IHDR-Wrong-Quick.png")

    assert fixit_felix.ihdr_rebuild(original, ["Wrong Crc"]) is None

    repaired = fixit_felix.ihdr_rebuild(original, ["GetInfo_Error_0:IHDR Width"])

    assert repaired is not None
    assert next(iter_chunks(repaired.data)).chunk_type == b"IHDR"


def main():
    checks = [
        ("Route finding keeps legacy handler order", test_route_finding_keeps_legacy_handler_order),
        ("Route finding preserves skip-bad-crc fallthrough", test_route_finding_preserves_skip_bad_crc_fallthrough),
        ("gAMA zero false positive keeps legacy note", test_gama_zero_false_positive_keeps_legacy_note),
        ("Libpng error decision orders solved and terminal cases", test_libpng_error_decision_orders_solved_and_terminal_cases),
        ("Wrong CRC decision keeps easy fix before other errors", test_wrong_crc_decision_keeps_easy_fix_before_other_errors),
        ("Wrong chunk name decision keeps length probe before bruteforce", test_wrong_chunk_name_decision_keeps_length_probe_before_bruteforce),
        ("No-next-chunk decision orders IEND and recovery paths", test_no_next_chunk_decision_orders_iend_and_recovery_paths),
        ("Applied repair formats legacy note and save suffix", test_applied_repair_formats_legacy_note_and_save_suffix),
        ("Applied repair adds IHDR metadata", test_applied_repair_adds_ihdr_metadata_when_available),
        ("Automatic repair order keeps legacy priority", test_automatic_repair_order_keeps_legacy_priority),
        ("Color profile cleanup requires matching finding", test_color_profile_cleanup_requires_matching_finding),
        ("PLTE cleanup requires noninteractive mode and PLTE finding", test_plte_cleanup_requires_noninteractive_mode_and_plte_finding),
        ("Missing chunk data byte requires CRC or no-next finding", test_missing_chunk_data_byte_requires_crc_or_no_next_finding),
        ("Known chunk type case requires wrong ancillary finding", test_known_chunk_type_case_requires_wrong_ancillary_finding),
        ("Unknown private critical removal is standalone salvage", test_unknown_private_critical_removal_is_standalone_salvage),
        ("IHDR rebuild requires IHDR finding", test_ihdr_rebuild_requires_ihdr_finding),
    ]

    print("Running FixItFelix family tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"FixItFelix family tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
