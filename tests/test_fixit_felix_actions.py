#!/usr/bin/env python3
import sys
from contextlib import contextmanager
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import Chunklate


@contextmanager
def patched_attrs(module, **attrs):
    old_values = {name: getattr(module, name) for name in attrs}
    try:
        for name, value in attrs.items():
            setattr(module, name, value)
        yield
    finally:
        for name, value in old_values.items():
            setattr(module, name, value)


def reset_fixit_globals():
    Chunklate.SideNotes = []
    Chunklate.PandoraBox = {}
    Chunklate.Cornucopia = {}
    Chunklate.Skip_Bad_Libpng = False
    Chunklate.Sample = "sample.png"


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


def main():
    checks = [
        ("gAMA zero discards false positive", test_gama_zero_discards_false_positive),
        ("Critical miss uses debug pause decision", test_critical_miss_uses_debug_pause_decision),
        ("Critical miss skips pause without debug gate", test_critical_miss_does_not_pause_without_debug_gate),
        ("Libpng error saves existing solution", test_libpng_error_saves_existing_solution_from_cornucopia),
        ("Libpng error ask relics sets skip", test_libpng_error_ask_relics_sets_skip_and_returns_relics),
        ("Libpng error skip reports only critical hit", test_libpng_error_skip_only_reports_critical_hit),
    ]

    print("Running FixItFelix action tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"FixItFelix action tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
