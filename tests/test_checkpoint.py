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


def main():
    checks = [
        ("Checkpoint registration ignores non errors", test_checkpoint_registration_ignores_non_errors),
        ("Checkpoint registration builds PandoraBox entry", test_checkpoint_registration_builds_pandorabox_entry),
        ("Checkpoint registration builds Cornucopia entry", test_checkpoint_registration_builds_cornucopia_entry),
        ("Checkpoint action handles FindMagic offset", test_checkpoint_action_decision_handles_find_magic_offset),
        ("Checkpoint action handles CheckLength paths", test_checkpoint_action_decision_handles_check_length_paths),
        ("Checkpoint action handles dummy IEND write clone", test_checkpoint_action_decision_handles_dummy_iend_write_clone),
        ("Checkpoint action handles flags", test_checkpoint_action_decision_handles_flags),
        ("Checkpoint action handles libpng error", test_checkpoint_action_decision_handles_libpng_error),
        ("Checkpoint action handles known sRGB warning", test_checkpoint_action_decision_handles_known_srgb_warning),
        ("Checkpoint action handles libpng warning classification", test_checkpoint_action_decision_handles_libpng_warning_classification),
    ]

    print("Running CheckPoint tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"checkpoint tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
