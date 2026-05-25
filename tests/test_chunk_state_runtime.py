#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import chunk_state, chunk_state_runtime


def populated_state():
    state = chunk_state.ChunkInfoState()
    state.ihdr_width = "32"
    state.ihdr_height = "16"
    state.ihdr_depth = "8"
    state.ihdr_color = "3"
    state.ihdr_method = "0"
    state.ihdr_filter = "0"
    state.ihdr_interlace = "1"
    state.idat_bytes_len = 7
    state.idat_datastream = "aabb"
    state.idat_counter = 2
    state.idat_bytes_len_history = [3, 4]
    state.idat_avg_len = 4
    state.plte_r = ["00"]
    state.plte_g = ["01"]
    state.plte_b = ["02"]
    state.splt_name = ["name"]
    state.splt_depth = ["8"]
    state.splt_red = ["r"]
    state.splt_green = ["g"]
    state.splt_blue = ["b"]
    state.splt_alpha = ["a"]
    state.splt_freq = ["f"]
    state.trns_index = ["0"]
    state.pcal_param = ["p1"]
    state.pcal_key = "key"
    state.pcal_zero = "0"
    state.pcal_max = "9"
    state.pcal_eq = "2"
    state.pcal_pnbr = "1"
    state.chrm_white_x = "1"
    state.chrm_white_y = "2"
    state.chrm_red_x = "3"
    state.chrm_red_y = "4"
    state.chrm_green_x = "5"
    state.chrm_green_y = "6"
    state.chrm_blue_x = "7"
    state.chrm_blue_y = "8"
    state.iccp_name = "ICC"
    state.iccp_method = 0
    state.iccp_profile = "profile"
    state.sbit_gray = "1"
    state.sbit_true_r = "2"
    state.sbit_true_g = "3"
    state.sbit_true_b = "4"
    state.sbit_gray_scale = "5"
    state.sbit_gray_alpha = "6"
    state.sbit_true_alpha_r = "7"
    state.sbit_true_alpha_g = "8"
    state.sbit_true_alpha_b = "9"
    state.sbit_true_alpha = "10"
    state.gifg_disposal_method = "1"
    state.gifg_user_input_flag = "2"
    state.gifg_delay_time = "3"
    state.gifx_application_identifier = "appid"
    state.gifx_authentication_code = "auth"
    state.gifx_application_data = "data"
    state.ster_mode = "1"
    state.text_key_list = ["Key"]
    state.text_str_list = ["Value"]
    state.text_key = "4b6579"
    state.text_text = "56616c7565"
    state.ztxt_key_list = ["ZKey"]
    state.ztxt_str_list = ["ZValue"]
    state.ztxt_key = "5a4b6579"
    state.ztxt_text = b"ZValue"
    state.itxt_key_list = ["IKey"]
    state.itxt_string_list = ["IValue"]
    state.itxt_key = "494b6579"
    state.itxt_string = "IValue"
    state.exif_endian = "II"
    return state


def test_legacy_values_from_state_preserves_full_mapping_and_list_copies():
    state = populated_state()

    values = chunk_state_runtime.legacy_values_from_state(state)

    assert values["IHDR_Width"] == "32"
    assert values["IHDR_Height"] == "16"
    assert values["IDAT_Bytes_Len"] == 7
    assert values["IDAT_Bytes_Len_History"] == [3, 4]
    assert values["PLTE_R"] == ["00"]
    assert values["sPLT_Name"] == ["name"]
    assert values["tRNS_Index"] == ["0"]
    assert values["pCAL_Key"] == "key"
    assert values["cHRM_Bluey"] == "8"
    assert values["iCCP_Profile"] == "profile"
    assert values["sBIT_TrueAlpha"] == "10"
    assert values["gIFgT"] == "3"
    assert values["gIFDT"] == "data"
    assert values["sTER"] == "1"
    assert values["tEXt_Key_List"] == ["Key"]
    assert values["zTXt_Text"] == b"ZValue"
    assert values["iTXt_String_List"] == ["IValue"]
    assert values["eXIf_endian"] == "II"

    state.plte_r.append("ff")
    assert values["PLTE_R"] == ["00"]


def test_sync_state_to_legacy_respects_section_filter():
    namespace = {"IHDR_Width": "old", "PLTE_R": ["old"]}
    state = populated_state()

    chunk_state_runtime.sync_state_to_legacy(namespace, state, "plte")

    assert namespace["IHDR_Width"] == "old"
    assert namespace["PLTE_R"] == ["00"]
    assert namespace["PLTE_G"] == ["01"]
    assert namespace["PLTE_B"] == ["02"]


def test_sync_state_to_legacy_accepts_multiple_sections():
    namespace = {}
    state = populated_state()

    chunk_state_runtime.sync_state_to_legacy(namespace, state, ("ihdr", "idat"))

    assert namespace["IHDR_Color"] == "3"
    assert namespace["IDAT_Avg_Len"] == 4
    assert "PLTE_R" not in namespace


def test_sync_legacy_to_state_preserves_existing_legacy_sections():
    namespace = {
        "IHDR_Height": "16",
        "IHDR_Width": "32",
        "IHDR_Depht": "8",
        "IHDR_Color": "3",
        "IHDR_Method": "0",
        "IHDR_Filter": "0",
        "IHDR_Interlace": "1",
        "PLTE_R": ["00"],
        "PLTE_G": ["01"],
        "PLTE_B": ["02"],
        "sPLT_Name": ["name"],
        "sPLT_Depht": ["8"],
        "sPLT_Red": ["r"],
        "sPLT_Green": ["g"],
        "sPLT_Blue": ["b"],
        "sPLT_Alpha": ["a"],
        "sPLT_Freq": ["f"],
    }
    state = chunk_state.ChunkInfoState()

    chunk_state_runtime.sync_legacy_to_state(state, namespace)

    assert state.ihdr_width == "32"
    assert state.ihdr_height == "16"
    assert state.ihdr_depth == "8"
    assert state.ihdr_color == "3"
    assert state.plte_r == ["00"]
    assert state.splt_name == ["name"]
    assert state.splt_freq == ["f"]

    namespace["PLTE_R"].append("ff")
    assert state.plte_r == ["00"]


def test_sync_legacy_to_state_respects_section_filter():
    namespace = {
        "IHDR_Height": "16",
        "IHDR_Width": "32",
        "IHDR_Depht": "8",
        "IHDR_Color": "3",
        "IHDR_Method": "0",
        "IHDR_Filter": "0",
        "IHDR_Interlace": "1",
        "PLTE_R": ["00"],
        "PLTE_G": ["01"],
        "PLTE_B": ["02"],
    }
    state = chunk_state.ChunkInfoState()

    chunk_state_runtime.sync_legacy_to_state(state, namespace, "plte")

    assert state.ihdr_width == 0
    assert state.plte_r == ["00"]
    assert state.plte_g == ["01"]
    assert state.plte_b == ["02"]


def main():
    checks = [
        ("Full mapping", test_legacy_values_from_state_preserves_full_mapping_and_list_copies),
        ("State to legacy section", test_sync_state_to_legacy_respects_section_filter),
        ("State to legacy multiple", test_sync_state_to_legacy_accepts_multiple_sections),
        ("Legacy to state", test_sync_legacy_to_state_preserves_existing_legacy_sections),
        ("Legacy to state section", test_sync_legacy_to_state_respects_section_filter),
    ]

    print("Running chunk state runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"chunk state runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
