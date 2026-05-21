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
