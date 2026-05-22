#!/usr/bin/env python3
import sys
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import chunk_info, chunk_state


def test_chunk_info_state_applies_ihdr_fields():
    state = chunk_state.ChunkInfoState()
    info = chunk_info.parse_ihdr("00000020000000100802000000")

    state.apply_ihdr(info)

    assert state.ihdr_width == "32"
    assert state.ihdr_height == "16"
    assert state.ihdr_depth == "8"
    assert state.ihdr_color == "2"
    assert state.ihdr_method == "0"
    assert state.ihdr_filter == "0"
    assert state.ihdr_interlace == "0"


def test_chunk_info_state_tracks_idat_sequence_and_reset():
    state = chunk_state.ChunkInfoState()

    first = state.next_idat("abcd", "00000002")
    state.apply_idat(first)
    second = state.next_idat("ef", "00000001")
    state.apply_idat(second)

    assert state.idat_bytes_len_history == [2, 1]
    assert state.idat_avg_len == 2
    assert state.idat_bytes_len == 3
    assert state.idat_datastream == "abcdef"
    assert state.idat_counter == 2

    state.reset_idat()

    assert state.idat_bytes_len_history == []
    assert state.idat_avg_len == ""
    assert state.idat_bytes_len == 0
    assert state.idat_datastream == ""
    assert state.idat_counter == 0


def test_chunk_info_state_applies_palette_and_suggested_palette():
    state = chunk_state.ChunkInfoState()
    plte = chunk_info.parse_plte("000102030405", ihdr_depth="8")
    splt = chunk_info.parse_splt("70616c0008" + ("01" * 13))

    state.apply_plte(plte)
    state.apply_splt(splt)

    assert state.plte_r == ["00", "03"]
    assert state.plte_g == ["01", "04"]
    assert state.plte_b == ["02", "05"]
    assert state.plte_entry_count() == 2
    assert state.splt_name == ["70616c"]
    assert state.splt_depth == ["8"]
    assert state.splt_entry_count() == len(splt.red) * 4


def test_chunk_info_state_accepts_legacy_field_sync():
    state = chunk_state.ChunkInfoState()

    state.set_ihdr_legacy(
        height="16",
        width="32",
        depth="8",
        color="3",
        method="0",
        filter_method="0",
        interlace="0",
    )
    state.set_plte_legacy(["00"], ["01"], ["02"])
    state.set_splt_legacy(
        names=["70616c"],
        depths=["8"],
        red=["r"],
        green=["g"],
        blue=["b"],
        alpha=["a"],
        freq=["f"],
    )

    assert state.ihdr_width == "32"
    assert state.ihdr_height == "16"
    assert state.ihdr_depth == "8"
    assert state.ihdr_color == "3"
    assert state.plte_entry_count() == 1
    assert state.splt_name == ["70616c"]
    assert state.splt_entry_count() == 4


def test_chunk_info_state_applies_trns_and_pcal():
    state = chunk_state.ChunkInfoState()
    trns = chunk_info.parse_trns("0001", ihdr_color="3", has_plte=True, plte_entries=2)
    pcal = chunk_info.parse_pcal(
        "43616c00"
        "00000001"
        "00000002"
        "00"
        "02"
        "703100"
        "703200"
    )

    state.apply_trns(trns)
    state.apply_pcal(pcal)

    assert state.trns_index == ["0", "1"]
    assert state.pcal_key == "43616c"
    assert state.pcal_zero == "1"
    assert state.pcal_max == "2"
    assert state.pcal_eq == "0"
    assert state.pcal_pnbr == "2"
    assert state.pcal_param == ["7031", "7032"]


def test_chunk_info_state_applies_remaining_color_and_extension_chunks():
    state = chunk_state.ChunkInfoState()

    state.apply_chrm(
        chunk_info.parse_chrm(
            "0000000100000002000000030000000400000005000000060000000700000008"
        )
    )
    state.apply_iccp(chunk_info.parse_iccp("4943430000aabb", raw_length_hex="00000007"))
    state.apply_sbit(chunk_info.parse_sbit("01020304", ihdr_color="6", ihdr_depth="8"))
    state.apply_offs(chunk_info.parse_offs("00000001ffffffff01"))

    assert state.chrm_white_x == "1"
    assert state.chrm_blue_y == "8"
    assert state.iccp_name == "ICC"
    assert state.iccp_method == 0
    assert state.iccp_profile == "aabb"
    assert state.sbit_true_alpha_r == "1"
    assert state.sbit_true_alpha == "4"
    assert state.offs_x == "1"
    assert state.offs_y == "-1"
    assert state.offs_unit == "1"


def test_chunk_info_state_applies_animation_stereo_and_text_chunks():
    state = chunk_state.ChunkInfoState()
    ztxt_payload = zlib.compress(b"Value").hex()

    state.apply_gifg(chunk_info.parse_gifg("010203"))
    state.apply_gifx(chunk_info.parse_gifx("00000000000000010000020003"))
    state.apply_ster(chunk_info.parse_ster("01"))
    state.apply_text(chunk_info.parse_text("4b65790056616c7565"))
    state.apply_ztxt(chunk_info.parse_ztxt("4b65790000" + ztxt_payload))
    state.apply_itxt(chunk_info.parse_itxt("4b6579000000000056616c7565"))
    state.apply_exif(chunk_info.parse_exif("494900000000"))

    assert state.gifg_disposal_method == "1"
    assert state.gifg_user_input_flag == "2"
    assert state.gifg_delay_time == "3"
    assert state.gifx_application_identifier == "1"
    assert state.gifx_authentication_code == "2"
    assert state.gifx_application_data == "3"
    assert state.ster_mode == "1"
    assert state.text_key == "4b6579"
    assert state.text_text == "56616c7565"
    assert state.text_key_list == ["Key"]
    assert state.text_str_list == ["Value"]
    assert state.ztxt_key == "4b6579"
    assert state.ztxt_text == b"Value"
    assert state.ztxt_key_list == ["Key"]
    assert state.ztxt_str_list == ["Value"]
    assert state.itxt_key == "4b6579"
    assert state.itxt_string == "Value"
    assert state.itxt_key_list == ["Key"]
    assert state.itxt_string_list == ["Value"]
    assert state.exif_endian == "II"


def test_chunk_info_state_snapshot_keeps_summary_counts():
    state = chunk_state.ChunkInfoState()
    state.apply_ihdr(chunk_info.parse_ihdr("00000020000000100802000000"))
    state.apply_idat(state.next_idat("abcd", "00000002"))
    state.apply_plte(chunk_info.parse_plte("000102030405", ihdr_depth="8"))
    state.apply_trns(chunk_info.parse_trns("0001", ihdr_color="3", has_plte=True, plte_entries=2))

    assert state.snapshot() == {
        "ihdr": {
            "width": "32",
            "height": "16",
            "depth": "8",
            "color": "2",
            "method": "0",
            "filter": "0",
            "interlace": "0",
        },
        "idat": {
            "bytes_len": 2,
            "counter": 1,
            "avg_len": 2,
            "history": [2],
        },
        "plte_entries": 2,
        "splt_entries": 0,
        "trns_indexes": 2,
        "pcal_parameters": 0,
        "has_chrm": False,
        "has_iccp": False,
        "has_sbit": False,
        "text_entries": 0,
        "ztxt_entries": 0,
        "itxt_entries": 0,
        "ster_mode": "",
    }


def main():
    checks = [
        ("IHDR fields", test_chunk_info_state_applies_ihdr_fields),
        ("IDAT sequence", test_chunk_info_state_tracks_idat_sequence_and_reset),
        ("palette fields", test_chunk_info_state_applies_palette_and_suggested_palette),
        ("legacy field sync", test_chunk_info_state_accepts_legacy_field_sync),
        ("tRNS and pCAL fields", test_chunk_info_state_applies_trns_and_pcal),
        (
            "color and extension chunks",
            test_chunk_info_state_applies_remaining_color_and_extension_chunks,
        ),
        (
            "animation stereo and text chunks",
            test_chunk_info_state_applies_animation_stereo_and_text_chunks,
        ),
        ("snapshot counts", test_chunk_info_state_snapshot_keeps_summary_counts),
    ]

    print("Running chunk state tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"chunk state tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
