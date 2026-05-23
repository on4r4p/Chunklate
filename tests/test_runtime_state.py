#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import runtime_state


def test_main_loop_scan_reset_values_preserve_legacy_defaults():
    assert runtime_state.main_loop_scan_reset_values() == {
        "IBN": 0,
        "IDAT_Bytes_Len": 0,
        "IDAT_Datastream": "",
    }


def test_main_loop_error_reset_values_preserve_legacy_defaults():
    values = runtime_state.main_loop_error_reset_values()

    assert values["Bad_Current_Name"] is False
    assert values["Bad_Missplaced"] is False
    assert values["Skip_Bad_Libpng"] is False
    assert values["EOF"] is False
    assert values["Show_Must_Go_On"] is False
    assert "Bad_Libpng" not in values


def test_main_loop_history_reset_values_preserve_fresh_containers():
    first = runtime_state.main_loop_history_reset_values()
    second = runtime_state.main_loop_history_reset_values()

    assert first == {
        "IDAT_Bytes_Len_History": [],
        "IDAT_Avg_Len": "",
        "Chunks_History": [],
        "Chunks_History_Index": [],
        "Bytes_History": [],
        "Loading_txt": "",
        "ERRORSFLAG": [],
        "PandoraBox": {},
        "Cornucopia": {},
        "SideNotes": [],
    }
    assert first["PandoraBox"] is not second["PandoraBox"]
    assert first["Chunks_History"] is not second["Chunks_History"]


def main():
    checks = [
        ("scan reset values", test_main_loop_scan_reset_values_preserve_legacy_defaults),
        ("error reset values", test_main_loop_error_reset_values_preserve_legacy_defaults),
        ("history reset values", test_main_loop_history_reset_values_preserve_fresh_containers),
    ]

    print("Running runtime state tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"runtime state tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
