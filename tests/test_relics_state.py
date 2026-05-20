#!/usr/bin/env python3
import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHUNKLATE = ROOT / "Chunklate.py"


def load_chunklate():
    spec = importlib.util.spec_from_file_location("chunklate_legacy_for_relic_tests", CHUNKLATE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


chunklate = load_chunklate()


def reset_relic_state():
    chunklate.PandoraBox = {}
    chunklate.Cornucopia = {}
    chunklate.Pandemonium = {}
    chunklate.ArkOfCovenant = {}
    chunklate.SideNotes = []
    chunklate.Sample = "sample.png"
    chunklate.DEBUG = False
    chunklate.PAUSEDEBUG = False
    chunklate.PAUSEERROR = False
    chunklate.NODIALOGUE = True


def test_relic_build_tools_uses_legacy_tool_names():
    tools = chunklate.Relic_Build_Tools(b"IDAT", ("crc", 12, 20))

    assert tools == {
        "IDAT_Tool_0": "crc",
        "IDAT_Tool_1": 12,
        "IDAT_Tool_2": 20,
    }


def test_pandorabox_add_keeps_legacy_error_numbering():
    reset_relic_state()

    first = chunklate.PandoraBox_Add("Checksum", "Wrong Crc", {"IDAT_Tool_0": "newcrc"})
    second = chunklate.PandoraBox_Add("Checksum", "Another Crc", {"IDAT_Tool_0": "other"})

    assert first == "Checksum_Error_0:Wrong Crc"
    assert second == "Checksum_Error_1:Another Crc"
    assert list(chunklate.PandoraBox) == [first, second]


def test_checkpoint_records_current_errors_in_pandorabox():
    reset_relic_state()

    chunklate.CheckPoint(
        True,
        False,
        "Checksum",
        b"IDAT",
        ["Wrong Crc"],
        "newcrc",
        12,
        20,
    )

    assert chunklate.Bad_Crc is True
    assert chunklate.SideNotes == ["Error:Wrong Crc"]
    assert chunklate.PandoraBox == {
        "Checksum_Error_0:Wrong Crc": {
            "IDAT_Tool_0": "newcrc",
            "IDAT_Tool_1": 12,
            "IDAT_Tool_2": 20,
        }
    }


def test_checkpoint_records_fixed_items_in_cornucopia():
    reset_relic_state()

    chunklate.CheckPoint(
        True,
        True,
        "UnitTest",
        b"PLTE",
        ["Fixed Data"],
        "fixed-bytes",
        4,
        8,
        "solution-key",
    )

    assert chunklate.PandoraBox == {}
    assert chunklate.SideNotes == ["Error Fixed:Fixed Data"]
    assert chunklate.Cornucopia == {
        "solution-key": {
            "PLTE_Tool_0": "fixed-bytes",
            "PLTE_Tool_1": 4,
            "PLTE_Tool_2": 8,
            "PLTE_Tool_3": "solution-key",
        }
    }


def test_pandemonium_snapshot_preserves_legacy_shared_reference():
    reset_relic_state()
    chunklate.PandoraBox_Add("Checksum", "Wrong Crc", {"IDAT_Tool_0": "newcrc"})
    chunklate.Cornucopia_Add("fixed-key", {"IDAT_Tool_0": "fixedcrc"})

    chunklate.Pandemonium_Remember_Current_Sample()

    assert chunklate.Pandemonium["sample.png"] is chunklate.PandoraBox
    assert chunklate.ArkOfCovenant["sample.png"] is chunklate.Cornucopia


def main():
    checks = [
        ("Relic tools keep legacy key names", test_relic_build_tools_uses_legacy_tool_names),
        ("PandoraBox keys keep legacy numbering", test_pandorabox_add_keeps_legacy_error_numbering),
        ("CheckPoint records current errors", test_checkpoint_records_current_errors_in_pandorabox),
        ("CheckPoint records fixed items", test_checkpoint_records_fixed_items_in_cornucopia),
        ("Pandemonium snapshot keeps legacy references", test_pandemonium_snapshot_preserves_legacy_shared_reference),
    ]

    print("Running Relics state tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"relics state tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
