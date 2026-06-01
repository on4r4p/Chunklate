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
    assert values["Have_A_KitKat"] is False
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
        "DebugNotes": [],
        "IDAT_CRC_PATCH_FAILED": False,
        "IDAT_CRC_PATCH_FAILED_FINDING": None,
        "IDAT_CRC_DEFER_EXPLAINED": False,
        "IDAT_CRC_DEFERRED_FINDINGS": set(),
        "IDAT_CRC_DEFERRED_ROUTES": set(),
        "IDAT_DEFLATE_PROBE_KEYS": set(),
        "WRONG_CHUNK_NAME_TRIED_ROUTES": set(),
        "REPAIR_ROUTE_STATES": {},
        "NEARBY_FOUND_LATER_IEND": None,
        "FOG_OF_WAR_BAD_CHUNKS": set(),
        "FOG_OF_WAR_LAST_MAP": None,
        "FOG_OF_WAR_LAST_WIDTH": None,
        "FOG_OF_WAR_LAST_RENDER_KEY": None,
        "FOG_OF_WAR_PREVIEW_CHUNK": None,
        "FOG_OF_WAR_PREVIEW_ERROR": False,
    }
    assert first["PandoraBox"] is not second["PandoraBox"]
    assert first["Chunks_History"] is not second["Chunks_History"]
    assert first["DebugNotes"] is not second["DebugNotes"]
    assert first["IDAT_CRC_DEFERRED_FINDINGS"] is not second["IDAT_CRC_DEFERRED_FINDINGS"]
    assert first["REPAIR_ROUTE_STATES"] is not second["REPAIR_ROUTE_STATES"]
    assert first["FOG_OF_WAR_BAD_CHUNKS"] is not second["FOG_OF_WAR_BAD_CHUNKS"]


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


def test_groundhogday_relaunch_args_preserve_legacy_shape_without_mutating_input():
    argv = ["Chunklate.py", "-f", "sample.png"]

    relaunch = runtime_state.groundhogday_relaunch_args(argv, "Folder_1/sample.png")

    assert argv == ["Chunklate.py", "-f", "sample.png"]
    assert relaunch == runtime_state.GroundhogDayRelaunch(
        argv=["Chunklate.py", "-f", "sample.png", "--CLONE Folder_1/sample.png"],
        strargs="-cmd Chunklate.py -f sample.png --CLONE Folder_1/sample.png",
        exec_args=["-cmd ", "Chunklate.py", "-f", "sample.png", "--CLONE Folder_1/sample.png"],
    )


def test_name_shift_runtime_context_freezes_legacy_runtime_inputs():
    chunks_history_index = ["0:0:16:8"]
    known_chunks = [b"IHDR"]

    context = runtime_state.name_shift_runtime_context(
        "89504e47",
        42,
        chunks_history_index,
        known_chunks,
    )

    chunks_history_index.append("1:16:24:0")
    known_chunks.append(b"IDAT")

    assert context == runtime_state.NameShiftRuntimeContext(
        data_hex="89504e47",
        current_type_offset=42,
        chunks_history_index=("0:0:16:8",),
        known_chunks=(b"IHDR",),
    )


def test_chunk_order_runtime_context_freezes_legacy_runtime_inputs():
    chunks_history = [b"PNG", b"IHDR"]
    unique_chunks = [b"PNG", b"IHDR"]

    context = runtime_state.chunk_order_runtime_context(
        "sample.png",
        chunks_history,
        unique_chunks,
    )

    chunks_history.append(b"IDAT")
    unique_chunks.append(b"IEND")

    assert context == runtime_state.ChunkOrderRuntimeContext(
        sample_name="sample.png",
        chunks_history=(b"PNG", b"IHDR"),
        unique_chunks=(b"PNG", b"IHDR"),
    )


def test_relics_runtime_context_freezes_lists_and_computes_old_crc():
    pandemonium = {"sample.png": {}}
    pandora_box = {"Error": {}}
    cornucopia = {"Tool": {}}
    side_notes = []
    all_chunks = [b"IHDR", b"IDAT"]
    critical_chunks = [b"IHDR"]
    chunks_history = [b"PNG", b"IHDR"]
    chunks_history_index = ["0:0:16:8"]

    context = runtime_state.relics_runtime_context(
        from_error="Relics",
        pandemonium=pandemonium,
        pandora_box=pandora_box,
        cornucopia=cornucopia,
        side_notes=side_notes,
        all_chunks=all_chunks,
        critical_chunks=critical_chunks,
        chunks_history=chunks_history,
        chunks_history_index=chunks_history_index,
        file_origin="origin.png",
        sample="sample.png",
        sample_name="sample.png",
        data_hex="00112233445566778899",
        crc_offset=4,
        bad_crc=True,
        skip_bad_current_name=False,
        skip_bad_infos=True,
        skip_bad_critical=False,
        skip_bad_crc=True,
        chunks_len_not_fixed={b"IDAT"},
        debug=True,
        pause_debug=False,
        pause_error=True,
    )

    all_chunks.append(b"IEND")
    critical_chunks.append(b"IEND")
    chunks_history.append(b"IDAT")
    chunks_history_index.append("1:16:24:0")

    assert context == runtime_state.RelicsRuntimeContext(
        from_error="Relics",
        pandemonium=pandemonium,
        pandora_box=pandora_box,
        cornucopia=cornucopia,
        side_notes=side_notes,
        all_chunks=(b"IHDR", b"IDAT"),
        critical_chunks=(b"IHDR",),
        chunks_history=(b"PNG", b"IHDR"),
        chunks_history_index=("0:0:16:8",),
        file_origin="origin.png",
        sample="sample.png",
        sample_name="sample.png",
        data_hex="00112233445566778899",
        bad_crc=True,
        old_crc="22334455",
        skip_bad_current_name=False,
        skip_bad_infos=True,
        skip_bad_critical=False,
        skip_bad_crc=True,
        chunks_len_not_fixed={b"IDAT"},
        debug=True,
        pause_debug=False,
        pause_error=True,
    )


def test_relics_runtime_context_omits_old_crc_without_bad_crc():
    context = runtime_state.relics_runtime_context(
        from_error="Relics",
        pandemonium={},
        pandora_box={},
        cornucopia={},
        side_notes=[],
        all_chunks=[],
        critical_chunks=[],
        chunks_history=[],
        chunks_history_index=[],
        file_origin="origin.png",
        sample="sample.png",
        sample_name="sample.png",
        data_hex="00112233445566778899",
        crc_offset=4,
        bad_crc=False,
        skip_bad_current_name=False,
        skip_bad_infos=False,
        skip_bad_critical=False,
        skip_bad_crc=False,
        chunks_len_not_fixed=(),
        debug=False,
        pause_debug=False,
        pause_error=False,
    )

    assert context.old_crc is None


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
        ("GroundhogDay relaunch args", test_groundhogday_relaunch_args_preserve_legacy_shape_without_mutating_input),
        ("NameShift runtime context", test_name_shift_runtime_context_freezes_legacy_runtime_inputs),
        ("ChunkOrder runtime context", test_chunk_order_runtime_context_freezes_legacy_runtime_inputs),
        ("Relics runtime context", test_relics_runtime_context_freezes_lists_and_computes_old_crc),
        ("Relics runtime context without CRC", test_relics_runtime_context_omits_old_crc_without_bad_crc),
    ]

    print("Running runtime state tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"runtime state tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
