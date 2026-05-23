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


def test_select_sample_preserves_current_sample_when_cloneswar_is_false():
    selection = runtime_state.select_sample(
        "/tmp/sample.png",
        False,
        basename=lambda value: value.rsplit("/", 1)[-1],
    )

    assert selection == runtime_state.SampleSelection(
        sample="/tmp/sample.png",
        sample_name="sample.png",
        cloneswar=False,
    )


def test_select_sample_uses_cloneswar_and_resets_it():
    selection = runtime_state.select_sample(
        "/tmp/original.png",
        "/tmp/Folder_1/clone.png",
        basename=lambda value: value.rsplit("/", 1)[-1],
    )

    assert selection == runtime_state.SampleSelection(
        sample="/tmp/Folder_1/clone.png",
        sample_name="clone.png",
        cloneswar=False,
    )


def test_select_sample_preserves_legacy_identity_check_for_false():
    selection = runtime_state.select_sample(
        "/tmp/original.png",
        "",
        basename=lambda value: "basename:%s" % value,
    )

    assert selection == runtime_state.SampleSelection(
        sample="",
        sample_name="basename:",
        cloneswar=False,
    )


def test_sample_data_from_bytes_keeps_bytes_and_hex():
    assert runtime_state.sample_data_from_bytes(b"\x89PNG") == runtime_state.LoadedSampleData(
        data_bytes=b"\x89PNG",
        data_hex="89504e47",
    )


def test_load_sample_data_uses_binary_mode_and_context_manager():
    calls = []

    class FakeHandle:
        def __enter__(self):
            calls.append(("enter",))
            return self

        def __exit__(self, exc_type, exc, tb):
            calls.append(("exit", exc_type, exc, tb))

        def read(self):
            calls.append(("read",))
            return b"png"

    def opener(path, mode):
        calls.append(("open", path, mode))
        return FakeHandle()

    assert runtime_state.load_sample_data("sample.png", opener=opener) == runtime_state.LoadedSampleData(
        data_bytes=b"png",
        data_hex="706e67",
    )
    assert calls == [
        ("open", "sample.png", "rb"),
        ("enter",),
        ("read",),
        ("exit", None, None, None),
    ]


def test_next_chunk_offset_preserves_legacy_length_sum():
    assert runtime_state.next_chunk_offset(
        10,
        b"len!",
        b"type",
        b"data-data",
        b"crc!",
    ) == 31


def test_kitkat_break_decision_resets_only_true_flag():
    assert runtime_state.kitkat_break_decision(True) == (True, False)
    assert runtime_state.kitkat_break_decision(False) == (False, False)


def main():
    checks = [
        ("scan reset values", test_main_loop_scan_reset_values_preserve_legacy_defaults),
        ("error reset values", test_main_loop_error_reset_values_preserve_legacy_defaults),
        ("history reset values", test_main_loop_history_reset_values_preserve_fresh_containers),
        ("select current sample", test_select_sample_preserves_current_sample_when_cloneswar_is_false),
        ("select CLONESWAR sample", test_select_sample_uses_cloneswar_and_resets_it),
        ("select sample identity check", test_select_sample_preserves_legacy_identity_check_for_false),
        ("sample data from bytes", test_sample_data_from_bytes_keeps_bytes_and_hex),
        ("load sample data", test_load_sample_data_uses_binary_mode_and_context_manager),
        ("next chunk offset", test_next_chunk_offset_preserves_legacy_length_sum),
        ("kitkat break decision", test_kitkat_break_decision_resets_only_true_flag),
    ]

    print("Running runtime state tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"runtime state tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
