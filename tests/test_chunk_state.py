#!/usr/bin/env python3
import sys
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
    }


def main():
    checks = [
        ("IHDR fields", test_chunk_info_state_applies_ihdr_fields),
        ("IDAT sequence", test_chunk_info_state_tracks_idat_sequence_and_reset),
        ("palette fields", test_chunk_info_state_applies_palette_and_suggested_palette),
        ("tRNS and pCAL fields", test_chunk_info_state_applies_trns_and_pcal),
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
