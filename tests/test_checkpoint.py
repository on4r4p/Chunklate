#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import checkpoint


def test_checkpoint_registration_ignores_non_errors():
    registration = checkpoint.finding_registration(
        error=False,
        fixed=False,
        function="Checksum",
        chunk=b"IDAT",
        info="-Crc is correct",
        toolkit=(),
    )

    assert registration.should_record is False
    assert registration.store is None
    assert registration.tools == {}


def test_checkpoint_registration_builds_pandorabox_entry():
    registration = checkpoint.finding_registration(
        error=True,
        fixed=False,
        function="Checksum",
        chunk=b"IDAT",
        info="-Wrong Crc",
        toolkit=("newcrc", 12, 20),
    )

    assert registration.should_record is True
    assert registration.store == "pandora_box"
    assert registration.side_note == "Error:-Wrong Crc"
    assert registration.function == "Checksum"
    assert registration.info == "-Wrong Crc"
    assert registration.tools == {
        "IDAT_Tool_0": "newcrc",
        "IDAT_Tool_1": 12,
        "IDAT_Tool_2": 20,
    }


def test_checkpoint_registration_builds_cornucopia_entry():
    registration = checkpoint.finding_registration(
        error=True,
        fixed=True,
        function="UnitTest",
        chunk=b"PLTE",
        info="-Fixed Data",
        toolkit=("fixed-bytes", 4, 8, "solution-key"),
    )

    assert registration.should_record is True
    assert registration.store == "cornucopia"
    assert registration.store_key == "solution-key"
    assert registration.side_note == "Error Fixed:-Fixed Data"
    assert registration.tools == {
        "PLTE_Tool_0": "fixed-bytes",
        "PLTE_Tool_1": 4,
        "PLTE_Tool_2": 8,
        "PLTE_Tool_3": "solution-key",
    }


def test_checkpoint_action_decision_handles_find_magic_offset():
    decision = checkpoint.action_decision(
        error=False,
        function="FindMagic",
        chunk=b"PNG",
        info="-Found Magic",
        toolkit=(16,),
    )

    assert decision.action == "return_value"
    assert decision.return_value == 16
    assert decision.side_note == "-CheckPoint: Returning next position based on Magic Offset 16"


def test_checkpoint_action_decision_handles_find_magic_cut_without_legacy_dash():
    decision = checkpoint.action_decision(
        error=False,
        function="FindMagic",
        chunk="PngSig",
        info="Cutting at Magic",
        toolkit=("89504e47", "0x43c"),
    )

    assert decision.action == "summarise_and_write_clone"
    assert decision.summary == (
        "-File does not start with a png signature.\n"
        "-Found a png signature at offset: 0x43c\n"
        "-Creating starting with the right signature."
    )


def test_checkpoint_action_decision_handles_check_length_paths():
    found = checkpoint.action_decision(
        error=False,
        function="CheckLength",
        chunk=b"IHDR",
        info="-Found NextChunk",
        toolkit=("0000000d",),
    )
    missing = checkpoint.action_decision(
        error=True,
        function="CheckLength",
        chunk=b"IDAT",
        info="-No NextChunk",
        toolkit=(b"IDAT", "12", b"PLTE"),
    )

    assert found.action == "check_chunk_name"
    assert found.side_note == "-CheckPoint:From Chunk [b'IHDR'] Found NextChunk at length previously indicated for checking [0000000d]."
    assert missing.action is None
    assert missing.flags == {"Bad_No_Next_Chunk": True}


def test_checkpoint_action_decision_handles_dummy_iend_write_clone():
    decision = checkpoint.action_decision(
        error=True,
        function="DummyChunk",
        chunk=b"IEND",
        info="Filling with a dummy chunk",
        toolkit=("fixed-data", 0, 128, 128, 152, "No NextChunk"),
    )

    assert decision.action == "write_clone"
    assert decision.flags == {"Bad_Critical": False}


def test_checkpoint_action_decision_handles_flags():
    order = checkpoint.action_decision(
        error=True,
        function="CheckChunkOrder",
        chunk="Critical",
        info="Critical Chunk IHDR is Missing",
        toolkit=(),
    )
    crc = checkpoint.action_decision(
        error=True,
        function="Checksum",
        chunk=b"IDAT",
        info="-Wrong Crc b'IDAT'",
        toolkit=(),
    )

    assert order.flags == {"Bad_Critical": True}
    assert crc.flags == {"Bad_Crc": True}


def test_checkpoint_action_decision_handles_lowercase_missplaced_flag():
    decision = checkpoint.action_decision(
        error=True,
        function="CheckChunkOrder",
        chunk="Missplaced",
        info="-cHRM is missplaced must appears before PLTE Chunk",
        toolkit=(),
    )

    assert decision.flags == {"Bad_Missplaced": True}


def test_checkpoint_action_decision_handles_libpng_error():
    decision = checkpoint.action_decision(
        error=True,
        function="LibpngCheck",
        chunk="LibpngCheck",
        info="libpng error: IDAT: CRC error",
        toolkit=(),
    )

    assert decision.action == "fix_it_felix_continue"
    assert decision.flags == {"Bad_Libpng": True}
    assert decision.return_value == "LibpngCheck"


def test_checkpoint_action_decision_blocks_libpng_success_with_pending_structural_error():
    decision = checkpoint.action_decision(
        error=True,
        function="LibpngCheck",
        chunk="sample.png",
        info="-Libpng is happy, but Chunklate still has unresolved findings: CheckChunkOrder_Error_0:-cHRM is missplaced",
        toolkit=(),
    )

    assert decision.action is None
    assert decision.flags == {"Bad_Libpng": True}


def test_checkpoint_action_decision_handles_known_srgb_warning():
    decision = checkpoint.action_decision(
        error=True,
        function="LibpngCheck",
        chunk="LibpngCheck",
        info="libpng warning: iCCP: known incorrect sRGB profile",
        toolkit=(),
    )

    assert decision.action == "fix_it_felix_return"
    assert decision.flags == {"Bad_Libpng": True}
    assert decision.return_value == "LibpngCheck"


def test_checkpoint_action_decision_handles_hist_out_of_place_warning():
    decision = checkpoint.action_decision(
        error=True,
        function="LibpngCheck",
        chunk="LibpngCheck",
        info="libpng warning: hIST: out of place",
        toolkit=(),
    )

    assert decision.action == "fix_it_felix_return"
    assert decision.flags == {"Bad_Libpng": True}
    assert decision.return_value == "LibpngCheck"


def test_checkpoint_action_decision_handles_pcal_out_of_place_warning():
    decision = checkpoint.action_decision(
        error=True,
        function="LibpngCheck",
        chunk="LibpngCheck",
        info="libpng warning: pCAL: out of place",
        toolkit=(),
    )

    assert decision.action == "fix_it_felix_return"
    assert decision.flags == {"Bad_Libpng": True}
    assert decision.return_value == "LibpngCheck"


def test_checkpoint_action_decision_handles_splt_out_of_place_warning():
    decision = checkpoint.action_decision(
        error=True,
        function="LibpngCheck",
        chunk="LibpngCheck",
        info="libpng warning: sPLT: out of place",
        toolkit=(),
    )

    assert decision.action == "fix_it_felix_return"
    assert decision.flags == {"Bad_Libpng": True}
    assert decision.return_value == "LibpngCheck"


def test_checkpoint_action_decision_handles_scal_format_warning():
    decision = checkpoint.action_decision(
        error=True,
        function="LibpngCheck",
        chunk="LibpngCheck",
        info="libpng warning: sCAL: bad width format",
        toolkit=(),
    )

    assert decision.action == "fix_it_felix_return"
    assert decision.flags == {"Bad_Libpng": True}
    assert decision.return_value == "LibpngCheck"


def test_checkpoint_action_decision_handles_libpng_warning_classification():
    known_warning = checkpoint.action_decision(
        error=True,
        function="LibpngCheck",
        chunk="LibpngCheck",
        info="libpng warning: IDAT: CRC error",
        toolkit=(),
        libpng_errors=("CRC error",),
    )
    false_positive = checkpoint.action_decision(
        error=True,
        function="LibpngCheck",
        chunk="LibpngCheck",
        info="libpng warning: iCCP: profile is noisy",
        toolkit=(),
    )
    final_false_positive = checkpoint.action_decision(
        error=True,
        function="LibpngCheck",
        chunk="LibpngCheck",
        info="libpng warning: iCCP: profile is noisy",
        toolkit=(),
        libpng_finished_at_iend=True,
    )

    assert known_warning.action == "libpng_warning_relics"
    assert false_positive.action == "discard_libpng_warning"
    assert final_false_positive.action == "discard_libpng_warning_and_end"


def test_checkpoint_action_decision_handles_chunk_name_fixes():
    decision = checkpoint.action_decision(
        error=True,
        function="CheckChunkName",
        chunk=b"bADR",
        info="turning it into a valid Chunk name",
        toolkit=(b"data", b"bad", b"fixed", "chunk_type", None, None),
    )

    assert decision.action == "fix_it_felix_continue"
    assert decision.side_note == "-CheckChunkName: turning it into a valid Chunk name"
    assert decision.return_value == "chunk_type"


def test_checkpoint_action_decision_handles_chunk_name_flags():
    current_name = checkpoint.action_decision(
        error=True,
        function="CheckChunkName",
        chunk=b"bADR",
        info="Chunk has Wrong Chunk name at offset: 42",
        toolkit=(),
    )
    next_name = checkpoint.action_decision(
        error=True,
        function="CheckChunkName",
        chunk=b"bADR",
        info="Chunk has Wrong Chunk name after Chunk[b'IHDR']",
        toolkit=(),
    )
    ancillary = checkpoint.action_decision(
        error=True,
        function="CheckChunkName",
        chunk=b"gAMA",
        info="Wrong Ancillary in known Chunk name at offset 12",
        toolkit=(None, None, None, None, None, None),
    )
    next_ancillary = checkpoint.action_decision(
        error=True,
        function="CheckChunkName",
        chunk=b"gAMA",
        info="Wrong Ancillary in known Chunk name at offset 12",
        toolkit=(None, None, None, None, None, b"IHDR"),
    )

    assert current_name.flags == {"Bad_Current_Name": True}
    assert next_name.flags == {"Bad_Next_Name": True}
    assert ancillary.flags == {"Bad_Ancillary": True}
    assert next_ancillary.flags == {"Bad_Next_Ancillary": True}


def test_checkpoint_action_decision_handles_chunk_name_missing_bytes():
    decision = checkpoint.action_decision(
        error=True,
        function="CheckChunkName",
        chunk=b"IDAT",
        info="Chunk name corrupted due to some missing bytes.",
        toolkit=(b"prefix", b"missing", b"suffix", None),
    )

    assert decision.action == "save_clone_missing_bytes"


def test_checkpoint_action_decision_handles_simple_smash_brute_brawl_paths():
    replaced = checkpoint.action_decision(
        error=True,
        function="SmashBruteBrawl",
        chunk=b"IDAT",
        info="Corrupted Data has been replaced",
        toolkit=(b"fixed",),
    )
    old_crc = checkpoint.action_decision(
        error=True,
        function="SmashBruteBrawl",
        chunk=b"IDAT",
        info="Previous Crc checksum has been restored",
        toolkit=(b"fixed", b"IDAT", 12, 20),
    )

    assert replaced.action == "write_clone"
    assert replaced.side_note == "-CheckPoint: Corrupted Data has been replaced"
    assert old_crc.action == "save_clone"
    assert old_crc.side_note == "-CheckPoint: Previous Crc checksum has been restored"


def test_smash_brute_brawl_failure_decision_routes_retry_paths():
    ihdr_retry = checkpoint.smash_brute_brawl_failure_decision(
        info="-Bruteforcer has Failed",
        chunk="IHDR",
        brute_level=2,
        bf_mode="Bytes",
    )
    twobytes_retry = checkpoint.smash_brute_brawl_failure_decision(
        info="-Bruteforcer has Failed",
        chunk="IDAT",
        brute_level=0,
        bf_mode="TwoBytes",
    )
    noncustom_end = checkpoint.smash_brute_brawl_failure_decision(
        info="-Bruteforcer has Failed",
        chunk="IDAT",
        brute_level=1,
        bf_mode="Bytes",
    )
    custom_brutus = checkpoint.smash_brute_brawl_failure_decision(
        info="-Bruteforcer has Failed",
        chunk="IDAT",
        brute_level=1,
        bf_mode="Custom",
    )
    unhandled = checkpoint.smash_brute_brawl_failure_decision(
        info="-Something else happened",
        chunk="IDAT",
        brute_level=0,
        bf_mode=None,
    )

    assert ihdr_retry.action == "smash_brute_brawl_retry_ihdr_harder"
    assert twobytes_retry.action == "smash_brute_brawl_ask_twobytes_retry"
    assert noncustom_end.action == "smash_brute_brawl_end_failed_noncustom"
    assert custom_brutus.action == "smash_brute_brawl_ask_custom_brutus"
    assert unhandled.action == "smash_brute_brawl_end_unhandled"


def test_checkpoint_action_decision_handles_smash_brute_brawl_failures():
    ihdr_retry = checkpoint.action_decision(
        error=True,
        function="SmashBruteBrawl",
        chunk="IHDR",
        info="-Bruteforcer has Failed",
        toolkit=("sample.png", b"IHDR", 13, 8, "edit", "Bytes", "crc", "length", "from-error"),
        brute_level=2,
    )
    custom_brutus = checkpoint.action_decision(
        error=True,
        function="SmashBruteBrawl",
        chunk="IDAT",
        info="-Bruteforcer has Failed",
        toolkit=("sample.png", b"IDAT", 4, 100, "edit", "Custom", "crc", "length", "from-error"),
        brute_level=1,
    )

    assert ihdr_retry.action == "smash_brute_brawl_retry_ihdr_harder"
    assert custom_brutus.action == "smash_brute_brawl_ask_custom_brutus"


def main():
    checks = [
        ("Checkpoint registration ignores non errors", test_checkpoint_registration_ignores_non_errors),
        ("Checkpoint registration builds PandoraBox entry", test_checkpoint_registration_builds_pandorabox_entry),
        ("Checkpoint registration builds Cornucopia entry", test_checkpoint_registration_builds_cornucopia_entry),
        ("Checkpoint action handles FindMagic offset", test_checkpoint_action_decision_handles_find_magic_offset),
        (
            "Checkpoint action handles FindMagic cut without dash",
            test_checkpoint_action_decision_handles_find_magic_cut_without_legacy_dash,
        ),
        ("Checkpoint action handles CheckLength paths", test_checkpoint_action_decision_handles_check_length_paths),
        ("Checkpoint action handles dummy IEND write clone", test_checkpoint_action_decision_handles_dummy_iend_write_clone),
        ("Checkpoint action handles flags", test_checkpoint_action_decision_handles_flags),
        (
            "Checkpoint action handles lowercase missplaced flag",
            test_checkpoint_action_decision_handles_lowercase_missplaced_flag,
        ),
        ("Checkpoint action handles libpng error", test_checkpoint_action_decision_handles_libpng_error),
        (
            "Checkpoint action blocks libpng success with pending structural error",
            test_checkpoint_action_decision_blocks_libpng_success_with_pending_structural_error,
        ),
        ("Checkpoint action handles known sRGB warning", test_checkpoint_action_decision_handles_known_srgb_warning),
        (
            "Checkpoint action handles hIST out-of-place warning",
            test_checkpoint_action_decision_handles_hist_out_of_place_warning,
        ),
        (
            "Checkpoint action handles pCAL out-of-place warning",
            test_checkpoint_action_decision_handles_pcal_out_of_place_warning,
        ),
        (
            "Checkpoint action handles sPLT out-of-place warning",
            test_checkpoint_action_decision_handles_splt_out_of_place_warning,
        ),
        (
            "Checkpoint action handles sCAL format warning",
            test_checkpoint_action_decision_handles_scal_format_warning,
        ),
        ("Checkpoint action handles libpng warning classification", test_checkpoint_action_decision_handles_libpng_warning_classification),
        ("Checkpoint action handles chunk name fixes", test_checkpoint_action_decision_handles_chunk_name_fixes),
        ("Checkpoint action handles chunk name flags", test_checkpoint_action_decision_handles_chunk_name_flags),
        ("Checkpoint action handles chunk name missing bytes", test_checkpoint_action_decision_handles_chunk_name_missing_bytes),
        ("Checkpoint action handles simple SmashBruteBrawl paths", test_checkpoint_action_decision_handles_simple_smash_brute_brawl_paths),
        ("SmashBruteBrawl failure decision routes retry paths", test_smash_brute_brawl_failure_decision_routes_retry_paths),
        ("Checkpoint action handles SmashBruteBrawl failures", test_checkpoint_action_decision_handles_smash_brute_brawl_failures),
    ]

    print("Running CheckPoint tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"checkpoint tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
