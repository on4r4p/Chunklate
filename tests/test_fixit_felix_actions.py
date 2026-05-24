#!/usr/bin/env python3
import sys
from contextlib import contextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import Chunklate
from chunklate import fixit_felix


@contextmanager
def patched_attrs(module, **attrs):
    missing = object()
    old_values = {name: getattr(module, name, missing) for name in attrs}
    try:
        for name, value in attrs.items():
            setattr(module, name, value)
        yield
    finally:
        for name, value in old_values.items():
            if value is missing:
                delattr(module, name)
            else:
                setattr(module, name, value)


def reset_fixit_globals():
    Chunklate.SideNotes = []
    Chunklate.PandoraBox = {}
    Chunklate.Cornucopia = {}
    Chunklate.Skip_Bad_Crc = False
    Chunklate.Skip_Bad_Libpng = False
    Chunklate.Skip_Bad_No_Next_Chunk = False
    Chunklate.Skip_Bad_Current_Name = False
    Chunklate.Skip_Bad_Next_Name = False
    Chunklate.Old_Bad_Crc = None
    Chunklate.EOF = False
    Chunklate.Bad_Critical = False
    Chunklate.Bad_Missplaced = False
    Chunklate.Bad_Crc = False
    Chunklate.Bad_Ancillary = False
    Chunklate.DEBUG = False
    Chunklate.PAUSEDEBUG = False
    Chunklate.Sample = "sample.png"
    Chunklate.DATAX = ""
    Chunklate.CLoffI = 0
    Chunklate.CrcoffI = 0
    Chunklate.Orig_CL = "0"
    Chunklate.Raw_Crc = ""


def wrong_crc_pandora_box(key, chkd):
    return {
        key: {
            chkd + "0": "fixed-crc-data",
            chkd + "1": 12,
            chkd + "2": 20,
            chkd + "3": b"IDAT",
            chkd + "4": "0x2a",
            chkd + "5": "old-crc",
        }
    }


def wrong_chunk_name_pandora_box(key, chkd):
    return {
        key: {
            chkd + "0": b"zzzz",
            chkd + "1": "13",
            chkd + "2": 128,
            chkd + "3": b"IHDR",
        }
    }


def test_wrong_crc_easy_answer_saves_clone():
    reset_fixit_globals()
    key = "Checksum_Error_0:Wrong Crc b'IDAT'"
    chkd = "IDAT_Tool_"
    Chunklate.PandoraBox = wrong_crc_pandora_box(key, chkd)
    save_calls = []

    def fake_save_clone(data, start, end, note):
        save_calls.append((data, start, end, note))
        return "saved"

    with patched_attrs(
        Chunklate,
        PRINT=lambda *args, **kwargs: None,
        Candy=lambda *args, **kwargs: "",
        Question=lambda **kwargs: True,
        SaveClone=fake_save_clone,
    ):
        should_return, result = Chunklate.FixItFelix_Wrong_Crc(key, chkd, 1)

    assert should_return is True
    assert result == "saved"
    assert save_calls == [
        (
            "fixed-crc-data",
            12,
            20,
            "-Found Chunk[b'IDAT'] has Wrong Crc at offset: 0x2a\n"
            "-Replaced with: fixed-crc-data old value was: old-crc",
        )
    ]
    assert Chunklate.Skip_Bad_Crc is False
    assert Chunklate.Old_Bad_Crc is None


def test_wrong_crc_easy_decline_then_final_decline_keeps_legacy_skip_none_and_saves():
    reset_fixit_globals()
    key = "Checksum_Error_0:Wrong Crc b'IDAT'"
    chkd = "IDAT_Tool_"
    answers = iter((False, False))
    Chunklate.PandoraBox = wrong_crc_pandora_box(key, chkd)
    save_calls = []

    with patched_attrs(
        Chunklate,
        PRINT=lambda *args, **kwargs: None,
        Candy=lambda *args, **kwargs: "",
        Question=lambda **kwargs: next(answers),
        SaveClone=lambda *args: save_calls.append(args) or "saved",
    ):
        should_return, result = Chunklate.FixItFelix_Wrong_Crc(key, chkd, 1)

    assert should_return is True
    assert result == "saved"
    assert Chunklate.Skip_Bad_Crc is None
    assert Chunklate.Old_Bad_Crc is None
    assert len(save_calls) == 1


def test_wrong_crc_other_errors_defer_sets_story_and_old_crc():
    reset_fixit_globals()
    key = "Checksum_Error_0:Wrong Crc b'IDAT'"
    chkd = "IDAT_Tool_"
    Chunklate.PandoraBox = wrong_crc_pandora_box(key, chkd)
    Chunklate.CLoffI = 33
    Chunklate.CrcoffI = 101
    Chunklate.Orig_CL = "0d"
    story_calls = []

    with patched_attrs(
        Chunklate,
        PRINT=lambda *args, **kwargs: None,
        Candy=lambda *args, **kwargs: "",
        Question=lambda **kwargs: True,
        ChunkStory=lambda *args: story_calls.append(args),
    ):
        should_return, result = Chunklate.FixItFelix_Wrong_Crc(key, chkd, 3)

    assert should_return is False
    assert result is None
    assert story_calls == [("add", b"IDAT", 33, 109, 13)]
    assert Chunklate.Old_Bad_Crc == "old-crc"
    assert Chunklate.Skip_Bad_Crc is True


def test_wrong_crc_already_in_cornucopia_does_not_require_pandora_tools():
    reset_fixit_globals()
    key = "Checksum_Error_0:Wrong Crc b'IDAT'"
    chkd = "IDAT_Tool_"
    printed = []
    Chunklate.Cornucopia = {key: {}}

    with patched_attrs(
        Chunklate,
        DEBUG=True,
        PAUSEDEBUG=True,
        PRINT=lambda message, *args, **kwargs: printed.append(message),
    ):
        should_return, result = Chunklate.FixItFelix_Wrong_Crc(key, chkd, 1)

    assert should_return is False
    assert result is None
    assert printed[-1] == "-Cornucopia is True"


def test_wrong_chunk_name_length_probe_accept_routes_to_nearby_chunk():
    reset_fixit_globals()
    key = "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42 and length is not the same than before."
    chkd = "zzzz_Tool_"
    Chunklate.PandoraBox = wrong_chunk_name_pandora_box(key, chkd)
    nearby_calls = []
    ancillary_calls = []

    with patched_attrs(
        Chunklate,
        PRINT=lambda *args, **kwargs: None,
        Candy=lambda *args, **kwargs: "",
        Question=lambda **kwargs: True,
        Ancillary=lambda chunk: ancillary_calls.append(chunk),
        NearbyChunk=lambda *args: nearby_calls.append(args) or "nearby-result",
    ):
        should_return, result = Chunklate.FixItFelix_Wrong_Chunk_Name(key, chkd)

    assert should_return is True
    assert result == "nearby-result"
    assert ancillary_calls == [b"zzzz"]
    assert nearby_calls == [(b"zzzz", "13", 128, False, key)]
    assert Chunklate.Skip_Bad_Next_Name is False
    assert Chunklate.Skip_Bad_Current_Name is False


def test_wrong_chunk_name_length_probe_decline_then_bruteforce_decline_sets_skips():
    reset_fixit_globals()
    key = "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42 and length is not the same than before."
    chkd = "zzzz_Tool_"
    answers = iter((False, False))
    Chunklate.Bad_Crc = True
    Chunklate.PandoraBox = wrong_chunk_name_pandora_box(key, chkd)

    with patched_attrs(
        Chunklate,
        PRINT=lambda *args, **kwargs: None,
        Candy=lambda *args, **kwargs: "",
        Question=lambda **kwargs: next(answers),
        Ancillary=lambda chunk: None,
    ):
        should_return, result = Chunklate.FixItFelix_Wrong_Chunk_Name(key, chkd)

    assert should_return is False
    assert result is None
    assert Chunklate.Skip_Bad_Next_Name is True
    assert Chunklate.Skip_Bad_Current_Name is True


def test_wrong_chunk_name_bruteforce_accept_routes_to_brute_chunk():
    reset_fixit_globals()
    key = "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42"
    chkd = "zzzz_Tool_"
    Chunklate.Bad_Crc = True
    Chunklate.PandoraBox = wrong_chunk_name_pandora_box(key, chkd)
    brute_calls = []

    with patched_attrs(
        Chunklate,
        PRINT=lambda *args, **kwargs: None,
        Candy=lambda *args, **kwargs: "",
        Question=lambda **kwargs: True,
        Ancillary=lambda chunk: None,
        BruteChunk=lambda *args: brute_calls.append(args) or "brute-result",
    ):
        should_return, result = Chunklate.FixItFelix_Wrong_Chunk_Name(key, chkd)

    assert should_return is True
    assert result == "brute-result"
    assert brute_calls == [(b"zzzz", b"IHDR", "13", key)]
    assert Chunklate.Skip_Bad_Current_Name is False


def test_wrong_chunk_name_save_existing_solution_uses_cornucopia():
    reset_fixit_globals()
    key = "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42"
    chkd = "zzzz_Tool_"
    save_calls = []
    Chunklate.Cornucopia = {
        key: {
            chkd + "0": "fixed-data",
            chkd + "1": 12,
            chkd + "2": 20,
            chkd + "3": "legacy note",
            chkd + "4": "solved label",
        }
    }

    with patched_attrs(
        Chunklate,
        PRINT=lambda *args, **kwargs: None,
        SaveClone=lambda *args: save_calls.append(args) or "saved",
    ):
        should_return, result = Chunklate.FixItFelix_Wrong_Chunk_Name(key, chkd)

    assert should_return is True
    assert result == "saved"
    assert save_calls == [("fixed-data", 12, 20, "legacy note")]


def test_wrong_chunk_name_skip_current_name_short_circuits():
    reset_fixit_globals()
    key = "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42"
    Chunklate.Skip_Bad_Current_Name = True

    with patched_attrs(
        Chunklate,
        PRINT=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("should not print")),
    ):
        should_return, result = Chunklate.FixItFelix_Wrong_Chunk_Name(key, "zzzz_Tool_")

    assert should_return is False
    assert result is None


def test_gama_zero_discards_false_positive():
    reset_fixit_globals()
    key = "GetInfo_Error_0:gAMA Chunk of 0 is Useless"
    Chunklate.PandoraBox = {key: {"gAMA_Tool_0": "sample.png"}}

    with patched_attrs(Chunklate, Candy=lambda *args, **kwargs: ""):
        should_return, result = Chunklate.FixItFelix_Gama_Zero(key)

    assert should_return is True
    assert result is Chunklate.FixItFelix
    assert Chunklate.PandoraBox == {}
    assert Chunklate.SideNotes == [
        "-Found False-Positive :[Error:-GetInfo_Error_0:gAMA Chunk of 0 is Useless]."
    ]


def test_critical_miss_uses_debug_pause_decision():
    reset_fixit_globals()
    pause_calls = []

    with patched_attrs(
        Chunklate,
        DEBUG=True,
        PAUSEDEBUG=True,
        PRINT=lambda *args, **kwargs: None,
        Pause=lambda msg: pause_calls.append(msg),
    ):
        should_return, result = Chunklate.FixItFelix_Critical_Miss(
            "CheckChunkOrder_Error_0:Critical"
        )

    assert should_return is False
    assert result is None
    assert pause_calls == ["Pause:Debug"]


def test_critical_miss_does_not_pause_without_debug_gate():
    reset_fixit_globals()
    pause_calls = []

    with patched_attrs(
        Chunklate,
        DEBUG=True,
        PAUSEDEBUG=False,
        PRINT=lambda *args, **kwargs: None,
        Pause=lambda msg: pause_calls.append(msg),
    ):
        should_return, result = Chunklate.FixItFelix_Critical_Miss(
            "CheckChunkOrder_Error_0:Critical"
        )

    assert should_return is False
    assert result is None
    assert pause_calls == []


def test_libpng_error_saves_existing_solution_from_cornucopia():
    reset_fixit_globals()
    key = "Libpng_Error_0:libpng error: bad adaptive filter"
    chkd = "LibpngCheck_Tool_"
    save_calls = []
    groundhog_calls = []
    Chunklate.Cornucopia = {
        key: {
            chkd + "0": "fixed-data",
            chkd + "1": 12,
            chkd + "2": 20,
            chkd + "3": "legacy save note",
        }
    }

    def fake_save_clone(data, start, end, note):
        save_calls.append((data, start, end, note))
        return "saved"

    def fake_groundhog_day(sample):
        groundhog_calls.append(sample)
        return "groundhog-result"

    with patched_attrs(
        Chunklate,
        PRINT=lambda *args, **kwargs: None,
        SaveClone=fake_save_clone,
        GroundhogDay=fake_groundhog_day,
    ):
        should_return, result = Chunklate.FixItFelix_Libpng_Error(key, chkd)

    assert should_return is True
    assert result == "groundhog-result"
    assert save_calls == [("fixed-data", 12, 20, "legacy save note")]
    assert groundhog_calls == ["sample.png"]


def test_libpng_error_ask_relics_sets_skip_and_returns_relics():
    reset_fixit_globals()
    key = "Libpng_Error_0:libpng error: bad adaptive filter"
    chkd = "LibpngCheck_Tool_"
    Chunklate.PandoraBox = {key: {}}
    relic_calls = []

    def fake_relics(finding):
        relic_calls.append(finding)
        return "relics-result"

    with patched_attrs(
        Chunklate,
        PRINT=lambda *args, **kwargs: None,
        Candy=lambda *args, **kwargs: "",
        Question=lambda **kwargs: True,
        Relics=fake_relics,
    ):
        should_return, result = Chunklate.FixItFelix_Libpng_Error(key, chkd)

    assert should_return is True
    assert result == "relics-result"
    assert Chunklate.Skip_Bad_Libpng is True
    assert relic_calls == [key]


def test_libpng_error_skip_only_reports_critical_hit():
    reset_fixit_globals()
    key = "Libpng_Error_0:libpng error: bad adaptive filter"

    with patched_attrs(
        Chunklate,
        Skip_Bad_Libpng=True,
        PRINT=lambda *args, **kwargs: None,
    ):
        should_return, result = Chunklate.FixItFelix_Libpng_Error(
            key,
            "LibpngCheck_Tool_",
        )

    assert should_return is False
    assert result is None


def test_no_next_false_positive_iend_feeds_libpng_after_tail_iend():
    reset_fixit_globals()
    key = "CheckLength_Error_0:-No NextChunk"
    chkd = "IEND_Tool_"
    Chunklate.PandoraBox = {
        key: {
            chkd + "0": b"IEND",
            chkd + "1": "0",
            chkd + "2": b"IDAT",
        }
    }
    Chunklate.DATAX = "aabbccdd" + fixit_felix.GOOD_IEND_HEX
    calls = {"chunk_story": [], "check_order": [], "libpng": []}

    with patched_attrs(
        Chunklate,
        PRINT=lambda *args, **kwargs: None,
        Candy=lambda *args, **kwargs: "",
        ChunkStory=lambda *args: calls["chunk_story"].append(args),
        CheckChunkOrder=lambda *args: calls["check_order"].append(args),
        LibpngCheck=lambda sample: calls["libpng"].append(sample) or "libpng-result",
    ):
        should_return, result = Chunklate.FixItFelix_No_NextChunk(key, chkd, b"IEND")

    assert should_return is True
    assert result == "libpng-result"
    assert Chunklate.PandoraBox == {}
    assert Chunklate.Skip_Bad_No_Next_Chunk is True
    assert Chunklate.EOF is True
    assert calls["chunk_story"] == [("add", b"IEND", 0, 8, 0)]
    assert calls["check_order"] == [(b"IEND", "Critical")]
    assert calls["libpng"] == ["sample.png"]
    assert Chunklate.SideNotes == [
        "-Found False-Positive :[Error:-No NextChunk].",
        "-Reached the end of file.",
    ]


def test_no_next_append_missing_iend_uses_dummy_at_crc_tail():
    reset_fixit_globals()
    key = "CheckLength_Error_0:-No NextChunk"
    chkd = "IDAT_Tool_"
    Chunklate.Bad_Critical = True
    Chunklate.CrcoffI = 0
    Chunklate.DATAX = "aabbccddff"
    Chunklate.PandoraBox = {
        key: {
            chkd + "0": b"IDAT",
            chkd + "1": "12",
            chkd + "2": b"IDAT",
        }
    }
    dummy_calls = []

    def fake_dummy_chunk(chunk, data_length, bad_position, bad_start, from_error):
        dummy_calls.append((chunk, data_length, bad_position, bad_start, from_error))
        return "dummy-iend"

    with patched_attrs(
        Chunklate,
        PRINT=lambda *args, **kwargs: None,
        Candy=lambda *args, **kwargs: "",
        print=lambda *args, **kwargs: None,
        DummyChunk=fake_dummy_chunk,
    ):
        should_return, result = Chunklate.FixItFelix_No_NextChunk(key, chkd, b"IDAT")

    assert should_return is True
    assert result == "dummy-iend"
    assert dummy_calls == [(b"IEND", 8, 8, 8, key)]
    assert Chunklate.SideNotes == ["-Extra bits detected:ff"]


def test_no_next_ask_length_probe_routes_to_nearbychunk():
    reset_fixit_globals()
    key = "CheckLength_Error_0:-No NextChunk"
    chkd = "IDAT_Tool_"
    Chunklate.PandoraBox = {
        key: {
            chkd + "0": b"IDAT",
            chkd + "1": "12",
            chkd + "2": b"IDAT",
        }
    }
    nearby_calls = []

    def fake_nearby_chunk(chunk_type, chunk_length, previous_chunk, next_flag, finding):
        nearby_calls.append((chunk_type, chunk_length, previous_chunk, next_flag, finding))
        return "nearby-result"

    with patched_attrs(
        Chunklate,
        PRINT=lambda *args, **kwargs: None,
        Candy=lambda *args, **kwargs: "",
        Question=lambda **kwargs: True,
        NearbyChunk=fake_nearby_chunk,
    ):
        should_return, result = Chunklate.FixItFelix_No_NextChunk(key, chkd, b"IDAT")

    assert should_return is True
    assert result == "nearby-result"
    assert nearby_calls == [(b"IDAT", "12", b"IDAT", False, key)]
    assert Chunklate.SideNotes == ["-End of File Reached but IEND Chunk is missing"]


def main():
    checks = [
        ("Wrong CRC easy answer saves clone", test_wrong_crc_easy_answer_saves_clone),
        (
            "Wrong CRC easy decline keeps legacy skip state",
            test_wrong_crc_easy_decline_then_final_decline_keeps_legacy_skip_none_and_saves,
        ),
        ("Wrong CRC other errors defer to story", test_wrong_crc_other_errors_defer_sets_story_and_old_crc),
        (
            "Wrong CRC already in Cornucopia does not need Pandora tools",
            test_wrong_crc_already_in_cornucopia_does_not_require_pandora_tools,
        ),
        (
            "Wrong chunk name length probe accepts NearbyChunk",
            test_wrong_chunk_name_length_probe_accept_routes_to_nearby_chunk,
        ),
        (
            "Wrong chunk name length probe decline sets skips",
            test_wrong_chunk_name_length_probe_decline_then_bruteforce_decline_sets_skips,
        ),
        (
            "Wrong chunk name bruteforce accepts BruteChunk",
            test_wrong_chunk_name_bruteforce_accept_routes_to_brute_chunk,
        ),
        (
            "Wrong chunk name saves existing solution",
            test_wrong_chunk_name_save_existing_solution_uses_cornucopia,
        ),
        (
            "Wrong chunk name skip short circuits",
            test_wrong_chunk_name_skip_current_name_short_circuits,
        ),
        ("gAMA zero discards false positive", test_gama_zero_discards_false_positive),
        ("Critical miss uses debug pause decision", test_critical_miss_uses_debug_pause_decision),
        ("Critical miss skips pause without debug gate", test_critical_miss_does_not_pause_without_debug_gate),
        ("Libpng error saves existing solution", test_libpng_error_saves_existing_solution_from_cornucopia),
        ("Libpng error ask relics sets skip", test_libpng_error_ask_relics_sets_skip_and_returns_relics),
        ("Libpng error skip reports only critical hit", test_libpng_error_skip_only_reports_critical_hit),
        ("No-next false positive feeds libpng", test_no_next_false_positive_iend_feeds_libpng_after_tail_iend),
        ("No-next append missing IEND uses dummy chunk", test_no_next_append_missing_iend_uses_dummy_at_crc_tail),
        ("No-next ask length probe routes to NearbyChunk", test_no_next_ask_length_probe_routes_to_nearbychunk),
    ]

    print("Running FixItFelix action tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"FixItFelix action tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
