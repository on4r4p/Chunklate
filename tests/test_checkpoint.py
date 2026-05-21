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


def main():
    checks = [
        ("Checkpoint registration ignores non errors", test_checkpoint_registration_ignores_non_errors),
        ("Checkpoint registration builds PandoraBox entry", test_checkpoint_registration_builds_pandorabox_entry),
        ("Checkpoint registration builds Cornucopia entry", test_checkpoint_registration_builds_cornucopia_entry),
    ]

    print("Running CheckPoint tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"checkpoint tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
