#!/usr/bin/env python3
import sys
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import Chunklate
from chunklate import relics, relics_runtime


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


def test_relics_runtime_keeps_legacy_callbacks():
    calls = []

    def callback(*args, **kwargs):
        calls.append((args, kwargs))
        return "called"

    runtime = relics_runtime.RelicsRuntime(
        save_clone=callback,
        smash_brute_brawl=callback,
        full_chunk_forcer_no_crc=callback,
        tk_manual_plte=callback,
        remove_chunk=callback,
        ask_choice=callback,
    )

    assert runtime.save_clone("data", 1, 2, "info") == "called"
    assert runtime.smash_brute_brawl("sample.png", b"IDAT", 4, 100, "error") == "called"
    assert runtime.full_chunk_forcer_no_crc("sample.png", b"IEND", 1, 2, "error") == "called"
    assert runtime.tk_manual_plte("sample.png", b"PLTE", 3, 4, "error") == "called"
    assert runtime.remove_chunk(1, 2, "remove") == "called"
    assert runtime.ask_choice("prompt", ("yes", "no"), "retry") == "called"
    assert len(calls) == 6


def test_relics_runtime_builder_keeps_named_legacy_callbacks():
    calls = []

    def callback(*args, **kwargs):
        calls.append((args, kwargs))
        return "called"

    runtime = relics_runtime.build_relics_runtime(
        save_clone=callback,
        smash_brute_brawl=callback,
        full_chunk_forcer_no_crc=callback,
        tk_manual_plte=callback,
        remove_chunk=callback,
        ask_choice=callback,
    )

    assert runtime == relics_runtime.RelicsRuntime(
        save_clone=callback,
        smash_brute_brawl=callback,
        full_chunk_forcer_no_crc=callback,
        tk_manual_plte=callback,
        remove_chunk=callback,
        ask_choice=callback,
    )
    assert runtime.save_clone("data") == "called"
    assert calls == [(("data",), {})]


def test_chunklate_relics_runtime_uses_current_legacy_functions():
    calls = []

    def fake_save_clone(*args, **kwargs):
        calls.append(("save_clone", args, kwargs))
        return "save"

    def fake_smash_brute_brawl(*args, **kwargs):
        calls.append(("smash_brute_brawl", args, kwargs))
        return "brawl"

    def fake_full_chunk_forcer(*args, **kwargs):
        calls.append(("full_chunk_forcer_no_crc", args, kwargs))
        return "forcer"

    def fake_tk_manual_plte(*args, **kwargs):
        calls.append(("tk_manual_plte", args, kwargs))
        return "manual"

    def fake_remove_chunk(*args, **kwargs):
        calls.append(("remove_chunk", args, kwargs))
        return "remove"

    def fake_ask_choice(asker, prompt, choices, retry_prompt):
        calls.append(("ask_choice", (prompt, choices, retry_prompt), {"asker": asker}))
        return "choice"

    with patched_attrs(
        Chunklate,
        SaveClone=fake_save_clone,
        SmashBruteBrawl=fake_smash_brute_brawl,
        FullChunkForcerNoCrc=fake_full_chunk_forcer,
        Tk_Manual_Plte=fake_tk_manual_plte,
        RemoveChunk=fake_remove_chunk,
    ), patched_attrs(Chunklate.decisions, ask_choice=fake_ask_choice):
        runtime = Chunklate.Relics_Runtime()

        assert runtime.save_clone("data", 1, 2, "info") == "save"
        assert runtime.smash_brute_brawl("sample.png", b"IDAT", 4, 100, "error") == "brawl"
        assert runtime.full_chunk_forcer_no_crc("sample.png", b"IEND", 1, 2, "error") == "forcer"
        assert runtime.tk_manual_plte("sample.png", b"PLTE", 3, 4, "error") == "manual"
        assert runtime.remove_chunk(1, 2, "remove") == "remove"
        assert runtime.ask_choice("prompt", ("yes", "no"), "retry") == "choice"

    assert [call[0] for call in calls] == [
        "save_clone",
        "smash_brute_brawl",
        "full_chunk_forcer_no_crc",
        "tk_manual_plte",
        "remove_chunk",
        "ask_choice",
    ]


def test_relics_runtime_runs_save_clone_plan():
    calls = []
    runtime = relics_runtime.RelicsRuntime(
        save_clone=lambda *args, **kwargs: calls.append(("save_clone", args, kwargs)) or "saved",
        smash_brute_brawl=lambda *args, **kwargs: None,
        full_chunk_forcer_no_crc=lambda *args, **kwargs: None,
        tk_manual_plte=lambda *args, **kwargs: None,
        remove_chunk=lambda *args, **kwargs: None,
        ask_choice=lambda *args, **kwargs: None,
    )
    plan = relics.WrongCrcSaveClonePlan("data", 10, 20, "fixed")

    assert relics_runtime.run_save_clone_plan(runtime, plan) == "saved"
    assert calls == [("save_clone", ("data", 10, 20, "fixed"), {})]


def test_relics_runtime_runs_brawl_plans():
    calls = []
    runtime = relics_runtime.RelicsRuntime(
        save_clone=lambda *args, **kwargs: None,
        smash_brute_brawl=lambda *args, **kwargs: calls.append(("brawl", args, kwargs)) or "brawled",
        full_chunk_forcer_no_crc=lambda *args, **kwargs: None,
        tk_manual_plte=lambda *args, **kwargs: None,
        remove_chunk=lambda *args, **kwargs: None,
        ask_choice=lambda *args, **kwargs: None,
    )

    wrong_crc_plan = relics.WrongCrcBrawlPlan(
        "sample.png",
        b"IDAT",
        4,
        100,
        "from-error",
        old_crc="old-crc",
        bf_mode="TwoBytes",
        brute_length=True,
    )
    dummy_plan = relics.DummyChunkBrawlPlan("sample.png", b"IEND", 0, 200, "dummy")
    getinfo_plan = relics.GetInfoBrawlPlan("sample.png", b"gAMA", 4, 300, "info", "Bytes")
    plte_plan = relics.PlteBrawlPlan(
        "sample.png",
        b"PLTE",
        6,
        400,
        "plte",
        edit_mode="replace",
        old_crc="plte-crc",
    )

    assert relics_runtime.run_wrong_crc_brawl_plan(runtime, wrong_crc_plan) == "brawled"
    assert relics_runtime.run_dummy_chunk_brawl_plan(runtime, dummy_plan) == "brawled"
    assert relics_runtime.run_getinfo_brawl_plan(runtime, getinfo_plan) == "brawled"
    assert relics_runtime.run_plte_brawl_plan(runtime, plte_plan) == "brawled"

    assert calls == [
        (
            "brawl",
            ("sample.png", b"IDAT", 4, 100, "from-error"),
            {"OldCrc": "old-crc", "BfMode": "TwoBytes", "BruteLength": True},
        ),
        ("brawl", ("sample.png", b"IEND", 0, 200, "dummy"), {}),
        ("brawl", ("sample.png", b"gAMA", 4, 300, "info"), {"BfMode": "Bytes"}),
        (
            "brawl",
            ("sample.png", b"PLTE", 6, 400, "plte"),
            {"EditMode": "replace", "OldCrc": "plte-crc"},
        ),
    ]


def test_relics_runtime_runs_plte_and_forcer_plans():
    calls = []
    runtime = relics_runtime.RelicsRuntime(
        save_clone=lambda *args, **kwargs: None,
        smash_brute_brawl=lambda *args, **kwargs: None,
        full_chunk_forcer_no_crc=lambda *args, **kwargs: calls.append(("forcer", args, kwargs)) or "forced",
        tk_manual_plte=lambda *args, **kwargs: calls.append(("manual", args, kwargs)) or "manual",
        remove_chunk=lambda *args, **kwargs: calls.append(("remove", args, kwargs)) or "removed",
        ask_choice=lambda *args, **kwargs: calls.append(("ask", args, kwargs)) or "manually",
    )

    assert relics_runtime.run_full_chunk_forcer_plan(
        runtime,
        relics.FullChunkForcerPlan("sample.png", b"zzzz", 10, 20, "forcer"),
    ) == "forced"
    assert relics_runtime.run_plte_manual_plan(
        runtime,
        relics.PlteManualPlan("sample.png", b"PLTE", 6, 100, "manual"),
    ) == "manual"
    assert relics_runtime.run_plte_remove_plan(
        runtime,
        relics.PlteRemovePlan(12, 44, "remove PLTE"),
    ) == "removed"
    assert relics_runtime.ask_plte_repair(runtime, relics, has_bad_crc=False) == "manually"

    assert calls[0] == ("forcer", ("sample.png", b"zzzz", 10, 20, "forcer"), {})
    assert calls[1] == ("manual", ("sample.png", b"PLTE", 6, 100, "manual"), {})
    assert calls[2] == ("remove", (12, 44, "remove PLTE"), {})
    assert calls[3][0] == "ask"
    assert "manually" in calls[3][1][1]


def test_relics_runtime_handles_current_wrong_crc_flow():
    calls = []
    emitted = []
    runtime = relics_runtime.RelicsRuntime(
        save_clone=lambda *args, **kwargs: calls.append(("save", args, kwargs)) or "saved",
        smash_brute_brawl=lambda *args, **kwargs: None,
        full_chunk_forcer_no_crc=lambda *args, **kwargs: None,
        tk_manual_plte=lambda *args, **kwargs: None,
        remove_chunk=lambda *args, **kwargs: None,
        ask_choice=lambda *args, **kwargs: None,
    )

    class FakeUi:
        @staticmethod
        def emit_critical_hit(value, *, emit):
            emit("hit:%s" % value)

        @staticmethod
        def say_current_wrong_crc_idat(*, candy):
            calls.append(("ui", "current-idat"))

    contexts = (
        relics.CurrentWrongCrcPromptContext(
            relics.WrongCrcRoute(None, "Checksum_Error_0:Wrong Crc b'PLTE'", "PLTE", "PLTE_Tool_"),
        ),
        relics.CurrentWrongCrcPromptContext(
            relics.WrongCrcRoute(None, "Checksum_Error_1:Wrong Crc b'IDAT'", "IDAT", "IDAT_Tool_"),
            tools=relics.WrongCrcTools("newcrc", 12, 20, b"IDAT", "0x2a", "oldcrc", 433, 100),
            question_hash=1234,
        ),
    )

    assert relics_runtime.handle_current_wrong_crc_flow(
        runtime,
        relics,
        FakeUi,
        contexts,
        ask=lambda **kwargs: calls.append(("ask", (), kwargs)) or True,
        emit=emitted.append,
        candy=lambda *args: None,
    ) == (True, "saved")

    assert emitted == [
        "hit:Checksum_Error_0:Wrong Crc b'PLTE'",
        "hit:Checksum_Error_1:Wrong Crc b'IDAT'",
    ]
    assert calls == [
        ("ui", "current-idat"),
        ("ask", (), {"id": "Checksum_Error_1:Wrong Crc b'IDAT'", "idhash": 1234}),
        (
            "save",
            (
                "newcrc",
                12,
                20,
                "-Found Chunk[b'IDAT'] has Wrong Crc at offset: 0x2a\n"
                "-Replaced with: newcrc old value was: oldcrc",
            ),
            {},
        ),
    ]


def test_relics_runtime_handles_remembered_idat_wrong_crc_flow():
    calls = []
    runtime = relics_runtime.RelicsRuntime(
        save_clone=lambda *args, **kwargs: None,
        smash_brute_brawl=lambda *args, **kwargs: calls.append(("brawl", args, kwargs)) or "brawl",
        full_chunk_forcer_no_crc=lambda *args, **kwargs: None,
        tk_manual_plte=lambda *args, **kwargs: None,
        remove_chunk=lambda *args, **kwargs: None,
        ask_choice=lambda *args, **kwargs: None,
    )

    class FakeUi:
        @staticmethod
        def say_wrong_crc_data_brawl(chunk_name, *, candy):
            calls.append(("ui", chunk_name))

    request = relics.RememberedWrongCrcBrawlRequest(
        route=relics.WrongCrcRoute("sample.0_Fixed.png", "Checksum_Error_0", "IDAT", "IDAT_Tool_"),
        tools=relics.WrongCrcTools("newcrc", 12, 20, b"IDAT", "0x2a", "oldcrc", 433, 100),
        plan=relics.WrongCrcBrawlPlan("origin.png", b"IDAT", 433, 100, "libpng", "oldcrc", bf_mode="TwoBytes"),
    )

    assert relics_runtime.handle_remembered_idat_wrong_crc_flow(
        runtime,
        FakeUi,
        (request,),
        candy=lambda *args: None,
    ) is None

    assert calls == [
        ("ui", "IDAT"),
        ("brawl", ("origin.png", b"IDAT", 433, 100, "libpng"), {"OldCrc": "oldcrc", "BfMode": "TwoBytes"}),
    ]


def test_relics_runtime_handles_single_pandemonium_flow():
    calls = []
    runtime = relics_runtime.RelicsRuntime(
        save_clone=lambda *args, **kwargs: None,
        smash_brute_brawl=lambda *args, **kwargs: calls.append(("brawl", args, kwargs)) or "brawl",
        full_chunk_forcer_no_crc=lambda *args, **kwargs: None,
        tk_manual_plte=lambda *args, **kwargs: None,
        remove_chunk=lambda *args, **kwargs: None,
        ask_choice=lambda *args, **kwargs: None,
    )

    class FakeUi:
        @staticmethod
        def say_single_pandemonium_intro(*, candy):
            calls.append(("ui", "intro"))

        @staticmethod
        def say_wrong_crc_data_brawl(chunk_name, *, candy):
            calls.append(("ui", "brawl", chunk_name))

        @staticmethod
        def say_single_pandemonium_unsupported(*, candy):
            calls.append(("ui", "unsupported"))

    decision = relics.SinglePandemoniumDecision(
        "wrong_crc_brawl",
        route=relics.WrongCrcRoute("sample.0_Fixed.png", "Checksum_Error_0", "IDAT", "IDAT_Tool_"),
        tools=relics.WrongCrcTools("newcrc", 12, 20, b"IDAT", "0x2a", "oldcrc", 433, 100),
        plan=relics.WrongCrcBrawlPlan("origin.png", b"IDAT", 433, 100, "libpng", "oldcrc", bf_mode="TwoBytes"),
    )

    assert relics_runtime.handle_single_pandemonium_flow(
        runtime,
        FakeUi,
        (decision,),
        debug=False,
        pause_debug=False,
        pause_error=False,
        pause=lambda message: calls.append(("pause", message)),
        the_end=lambda: calls.append(("end", (), {})),
        candy=lambda *args: None,
    ) == ()

    assert calls == [
        ("ui", "intro"),
        ("ui", "brawl", "IDAT"),
        ("brawl", ("origin.png", b"IDAT", 433, 100, "libpng"), {"OldCrc": "oldcrc", "BfMode": "TwoBytes"}),
    ]


def test_relics_runtime_handles_single_pandemonium_unsupported_flow():
    class StopLegacyEnd(Exception):
        pass

    calls = []

    class FakeUi:
        @staticmethod
        def say_single_pandemonium_intro(*, candy):
            calls.append(("ui", "intro"))

        @staticmethod
        def say_wrong_crc_data_brawl(chunk_name, *, candy):
            calls.append(("ui", "brawl", chunk_name))

        @staticmethod
        def say_single_pandemonium_unsupported(*, candy):
            calls.append(("ui", "unsupported"))

    runtime = relics_runtime.RelicsRuntime(
        save_clone=lambda *args, **kwargs: None,
        smash_brute_brawl=lambda *args, **kwargs: None,
        full_chunk_forcer_no_crc=lambda *args, **kwargs: None,
        tk_manual_plte=lambda *args, **kwargs: None,
        remove_chunk=lambda *args, **kwargs: None,
        ask_choice=lambda *args, **kwargs: None,
    )

    def stop_end():
        calls.append(("end", (), {}))
        raise StopLegacyEnd()

    try:
        relics_runtime.handle_single_pandemonium_flow(
            runtime,
            FakeUi,
            (relics.SinglePandemoniumDecision("unsupported"),),
            debug=True,
            pause_debug=True,
            pause_error=False,
            pause=lambda message: calls.append(("pause", message)),
            the_end=stop_end,
            candy=lambda *args: None,
        )
    except StopLegacyEnd:
        pass
    else:
        raise AssertionError("unsupported single-Pandemonium flow should call the legacy end callback")

    assert calls == [
        ("ui", "intro"),
        ("pause", "Pause Pandemonium Debug"),
        ("ui", "unsupported"),
        ("end", (), {}),
    ]


def test_relics_runtime_applies_plte_repair_decisions():
    calls = []
    side_notes = []
    runtime = relics_runtime.RelicsRuntime(
        save_clone=lambda *args, **kwargs: None,
        smash_brute_brawl=lambda *args, **kwargs: calls.append(("brawl", args, kwargs)) or "brawl",
        full_chunk_forcer_no_crc=lambda *args, **kwargs: None,
        tk_manual_plte=lambda *args, **kwargs: calls.append(("manual", args, kwargs)) or "manual",
        remove_chunk=lambda *args, **kwargs: calls.append(("remove", args, kwargs)) or "remove",
        ask_choice=lambda *args, **kwargs: None,
    )

    assert relics_runtime.apply_plte_repair_decision(
        runtime,
        relics.PlteRepairDecision(
            "manual",
            relics.PlteManualPlan("sample.png", b"PLTE", 6, 100, "manual"),
        ),
        add_side_note=side_notes.append,
        the_end=lambda: calls.append(("end", (), {})),
    ) == (True, "manual")
    assert relics_runtime.apply_plte_repair_decision(
        runtime,
        relics.PlteRepairDecision(
            "remove",
            relics.PlteRemovePlan(12, 44, "remove PLTE"),
        ),
        add_side_note=side_notes.append,
        the_end=lambda: calls.append(("end", (), {})),
    ) == (True, "remove")
    assert relics_runtime.apply_plte_repair_decision(
        runtime,
        relics.PlteRepairDecision(
            "brawl",
            relics.PlteBrawlPlan("sample.png", b"PLTE", 6, 400, "plte", "Insert"),
        ),
        add_side_note=side_notes.append,
        the_end=lambda: calls.append(("end", (), {})),
    ) == (True, "brawl")
    assert relics_runtime.apply_plte_repair_decision(
        runtime,
        relics.PlteRepairDecision("quit", side_note="-User chose to quit."),
        add_side_note=side_notes.append,
        the_end=lambda: calls.append(("end", (), {})),
    ) == (False, None)

    assert [call[0] for call in calls] == ["manual", "remove", "brawl", "end"]
    assert side_notes == ["-User chose to quit."]


def test_relics_runtime_handles_plte_repair_flow_with_valid_crc():
    calls = []
    side_notes = []

    class FakeUi:
        @staticmethod
        def say_plte_intro(*, candy):
            calls.append(("ui", "intro"))

        @staticmethod
        def say_plte_valid_crc(*, candy):
            calls.append(("ui", "valid-crc"))

        @staticmethod
        def say_plte_bad_crc(*, candy):
            calls.append(("ui", "bad-crc"))

        @staticmethod
        def say_plte_fallback(*, candy):
            calls.append(("ui", "fallback"))

    runtime = relics_runtime.RelicsRuntime(
        save_clone=lambda *args, **kwargs: None,
        smash_brute_brawl=lambda *args, **kwargs: calls.append(("brawl", args, kwargs)) or "brawl",
        full_chunk_forcer_no_crc=lambda *args, **kwargs: None,
        tk_manual_plte=lambda *args, **kwargs: calls.append(("manual", args, kwargs)) or "manual",
        remove_chunk=lambda *args, **kwargs: None,
        ask_choice=lambda *args, **kwargs: calls.append(("ask", args, kwargs)) or "manually",
    )

    assert relics_runtime.handle_plte_repair_flow(
        runtime,
        relics,
        FakeUi,
        has_bad_crc=False,
        chunks_history=[b"IHDR", b"PLTE"],
        chunks_history_index=["0:8:21", "1:33:801"],
        target_file="sample.png",
        ask_fallback=lambda: False,
        add_side_note=side_notes.append,
        the_end=lambda: calls.append(("end", (), {})),
        candy=lambda *args: None,
    ) == (True, "manual")

    assert [call[0] for call in calls] == ["ui", "ui", "ask", "manual"]
    assert calls[1] == ("ui", "valid-crc")
    assert calls[3] == ("manual", ("sample.png", b"PLTE", 801, 33, "-PLTE Wrong Data"), {})
    assert side_notes == []


def test_relics_runtime_handles_plte_repair_flow_with_bad_crc():
    calls = []
    runtime = relics_runtime.RelicsRuntime(
        save_clone=lambda *args, **kwargs: None,
        smash_brute_brawl=lambda *args, **kwargs: calls.append(("brawl", args, kwargs)) or "brawl",
        full_chunk_forcer_no_crc=lambda *args, **kwargs: None,
        tk_manual_plte=lambda *args, **kwargs: None,
        remove_chunk=lambda *args, **kwargs: None,
        ask_choice=lambda *args, **kwargs: calls.append(("ask", args, kwargs)) or "bruteforce",
    )

    class FakeUi:
        @staticmethod
        def say_plte_intro(*, candy):
            calls.append(("ui", "intro"))

        @staticmethod
        def say_plte_valid_crc(*, candy):
            calls.append(("ui", "valid-crc"))

        @staticmethod
        def say_plte_bad_crc(*, candy):
            calls.append(("ui", "bad-crc"))

        @staticmethod
        def say_plte_fallback(*, candy):
            calls.append(("ui", "fallback"))

    assert relics_runtime.handle_plte_repair_flow(
        runtime,
        relics,
        FakeUi,
        has_bad_crc=True,
        chunks_history=[b"IHDR", b"PLTE"],
        chunks_history_index=["0:8:21", "1:33:801"],
        target_file="sample.png",
        old_crc="old-crc",
        ask_fallback=lambda: False,
        add_side_note=lambda note: calls.append(("note", (note,), {})),
        the_end=lambda: calls.append(("end", (), {})),
        candy=lambda *args: None,
    ) == (True, "brawl")

    assert [call[0] for call in calls] == ["ui", "ui", "ask", "brawl"]
    assert calls[1] == ("ui", "bad-crc")
    assert calls[3] == (
        "brawl",
        ("sample.png", b"PLTE", 801, 33, "-PLTE Wrong Data"),
        {"EditMode": "Insert", "OldCrc": "old-crc"},
    )


def test_relics_runtime_handles_plte_repair_flow_fallback():
    calls = []
    runtime = relics_runtime.RelicsRuntime(
        save_clone=lambda *args, **kwargs: None,
        smash_brute_brawl=lambda *args, **kwargs: calls.append(("brawl", args, kwargs)) or "brawl",
        full_chunk_forcer_no_crc=lambda *args, **kwargs: None,
        tk_manual_plte=lambda *args, **kwargs: None,
        remove_chunk=lambda *args, **kwargs: None,
        ask_choice=lambda *args, **kwargs: calls.append(("ask", args, kwargs)) or "unknown",
    )

    class FakeUi:
        @staticmethod
        def say_plte_intro(*, candy):
            calls.append(("ui", "intro"))

        @staticmethod
        def say_plte_valid_crc(*, candy):
            calls.append(("ui", "valid-crc"))

        @staticmethod
        def say_plte_bad_crc(*, candy):
            calls.append(("ui", "bad-crc"))

        @staticmethod
        def say_plte_fallback(*, candy):
            calls.append(("ui", "fallback"))

    assert relics_runtime.handle_plte_repair_flow(
        runtime,
        relics,
        FakeUi,
        has_bad_crc=False,
        chunks_history=[b"IHDR", b"PLTE"],
        chunks_history_index=["0:8:21", "1:33:801"],
        target_file="sample.png",
        ask_fallback=lambda: True,
        add_side_note=lambda note: calls.append(("note", (note,), {})),
        the_end=lambda: calls.append(("end", (), {})),
        candy=lambda *args: None,
    ) == (True, "brawl")

    assert [call[0] for call in calls] == ["ui", "ui", "ask", "ui", "brawl"]
    assert calls[-1] == (
        "brawl",
        ("sample.png", b"PLTE", 801, 33, "-PLTE Wrong Data"),
        {"EditMode": "Insert"},
    )


def test_relics_runtime_applies_dummy_chunk_repair_decisions():
    class StopLegacyEnd(Exception):
        pass

    calls = []
    runtime = relics_runtime.RelicsRuntime(
        save_clone=lambda *args, **kwargs: None,
        smash_brute_brawl=lambda *args, **kwargs: calls.append(("brawl", args, kwargs)) or "brawl",
        full_chunk_forcer_no_crc=lambda *args, **kwargs: None,
        tk_manual_plte=lambda *args, **kwargs: None,
        remove_chunk=lambda *args, **kwargs: None,
        ask_choice=lambda *args, **kwargs: None,
    )

    assert relics_runtime.apply_dummy_chunk_repair_decision(
        runtime,
        relics.DummyChunkRepairDecision(
            "brawl",
            relics.DummyChunkBrawlPlan("sample.png", "IHDR", 13, 128, "dummy"),
        ),
        show_todo=lambda: calls.append(("todo", (), {})),
        the_end=lambda: calls.append(("end", (), {})),
    ) == "brawl"

    def stop_end():
        calls.append(("end", (), {}))
        raise StopLegacyEnd()

    try:
        relics_runtime.apply_dummy_chunk_repair_decision(
            runtime,
            relics.DummyChunkRepairDecision("todo_end"),
            show_todo=lambda: calls.append(("todo", (), {})),
            the_end=stop_end,
        )
    except StopLegacyEnd:
        pass
    else:
        raise AssertionError("todo_end should call the legacy end callback")

    try:
        relics_runtime.apply_dummy_chunk_repair_decision(
            runtime,
            relics.DummyChunkRepairDecision("unknown"),
            show_todo=lambda: calls.append(("todo", (), {})),
            the_end=stop_end,
        )
    except ValueError as exc:
        assert "Unknown dummy chunk relic decision" in str(exc)
    else:
        raise AssertionError("unknown dummy decisions must fail")

    assert [call[0] for call in calls] == ["brawl", "todo", "end"]


def test_relics_runtime_handles_remembered_dummy_chunk_flow():
    calls = []
    runtime = relics_runtime.RelicsRuntime(
        save_clone=lambda *args, **kwargs: None,
        smash_brute_brawl=lambda *args, **kwargs: calls.append(("brawl", args, kwargs)) or "brawl",
        full_chunk_forcer_no_crc=lambda *args, **kwargs: None,
        tk_manual_plte=lambda *args, **kwargs: None,
        remove_chunk=lambda *args, **kwargs: None,
        ask_choice=lambda *args, **kwargs: None,
    )

    class FakeUi:
        @staticmethod
        def say_dummy_chunk_critical_prompt(chunk_name, *, candy):
            calls.append(("ui-critical", (chunk_name,), {}))

        @staticmethod
        def say_dummy_chunk_ancillary_prompt(chunk_name, *, candy):
            calls.append(("ui-ancillary", (chunk_name,), {}))

    request = relics.RememberedDummyChunkRepairRequest(
        route=relics.DummyChunkRoute(
            source="sample.0_Fixed.png",
            error="DummyChunk_Error_0:Filling with a dummy chunk",
            chunk_name="IHDR",
            tool_prefix="IHDR_Tool_",
            is_critical=True,
        ),
        tools=relics.DummyChunkTools(
            fixed_data="fixed-data",
            dummy_data_length=13,
            bad_position=128,
            bad_start=128,
            bad_end=152,
            from_error="No NextChunk",
        ),
    )

    assert relics_runtime.handle_remembered_dummy_chunk_flow(
        runtime,
        relics,
        FakeUi,
        request,
        from_error="libpng",
        ask=lambda: True,
        show_todo=lambda: calls.append(("todo", (), {})),
        the_end=lambda: calls.append(("end", (), {})),
        candy=lambda *args: None,
    ) == "brawl"

    assert calls == [
        ("ui-critical", ("IHDR",), {}),
        ("brawl", ("sample.0_Fixed.png", "IHDR", 13, 128, "libpng"), {}),
    ]


def test_relics_runtime_handles_remembered_dummy_chunk_flow_decline_and_missing_request():
    class StopLegacyEnd(Exception):
        pass

    calls = []
    runtime = relics_runtime.RelicsRuntime(
        save_clone=lambda *args, **kwargs: None,
        smash_brute_brawl=lambda *args, **kwargs: calls.append(("brawl", args, kwargs)) or "brawl",
        full_chunk_forcer_no_crc=lambda *args, **kwargs: None,
        tk_manual_plte=lambda *args, **kwargs: None,
        remove_chunk=lambda *args, **kwargs: None,
        ask_choice=lambda *args, **kwargs: None,
    )

    class FakeUi:
        @staticmethod
        def say_dummy_chunk_critical_prompt(chunk_name, *, candy):
            calls.append(("ui-critical", (chunk_name,), {}))

        @staticmethod
        def say_dummy_chunk_ancillary_prompt(chunk_name, *, candy):
            calls.append(("ui-ancillary", (chunk_name,), {}))

    request = relics.RememberedDummyChunkRepairRequest(
        route=relics.DummyChunkRoute(
            source="sample.1_Fixed.png",
            error="DummyChunk_Error_1:Filling with a dummy chunk",
            chunk_name="tEXt",
            tool_prefix="tEXt_Tool_",
            is_critical=False,
        ),
        tools=relics.DummyChunkTools(
            fixed_data="fixed-data",
            dummy_data_length=4,
            bad_position=256,
            bad_start=256,
            bad_end=280,
            from_error="No NextChunk",
        ),
    )

    def stop_end():
        calls.append(("end", (), {}))
        raise StopLegacyEnd()

    try:
        relics_runtime.handle_remembered_dummy_chunk_flow(
            runtime,
            relics,
            FakeUi,
            request,
            from_error="libpng",
            ask=lambda: False,
            show_todo=lambda: calls.append(("todo", (), {})),
            the_end=stop_end,
            candy=lambda *args: None,
        )
    except StopLegacyEnd:
        pass
    else:
        raise AssertionError("ancillary dummy decline should call the legacy end callback")

    try:
        relics_runtime.handle_remembered_dummy_chunk_flow(
            runtime,
            relics,
            FakeUi,
            None,
            from_error="libpng",
            ask=lambda: True,
            show_todo=lambda: calls.append(("todo", (), {})),
            the_end=stop_end,
            candy=lambda *args: None,
        )
    except StopLegacyEnd:
        pass
    else:
        raise AssertionError("missing dummy request should call the legacy end callback")

    assert [call[0] for call in calls] == ["ui-ancillary", "todo", "end", "end"]


def test_relics_runtime_skips_pandemonium_flow_without_pandemonium():
    runtime = relics_runtime.RelicsRuntime(
        save_clone=lambda *args, **kwargs: None,
        smash_brute_brawl=lambda *args, **kwargs: None,
        full_chunk_forcer_no_crc=lambda *args, **kwargs: None,
        tk_manual_plte=lambda *args, **kwargs: None,
        remove_chunk=lambda *args, **kwargs: None,
        ask_choice=lambda *args, **kwargs: None,
    )

    assert relics_runtime.handle_pandemonium_flow(
        runtime,
        relics,
        object(),
        SimpleNamespace(pandemonium={}),
        ask=lambda **kwargs: True,
        emit=lambda value: None,
        pause=lambda message: None,
        show_todo=lambda: None,
        the_end=lambda: None,
        candy=lambda *args: None,
    ) == (False, None)


def test_relics_runtime_handles_pandemonium_current_wrong_crc_first():
    calls = []
    emitted = []
    pandora_box = {
        "Checksum_Error_0:Wrong Crc b'IDAT'": {
            "IDAT_Tool_0": "new-crc-data",
            "IDAT_Tool_1": 12,
            "IDAT_Tool_2": 20,
            "IDAT_Tool_3": b"IDAT",
            "IDAT_Tool_4": "0x2a",
            "IDAT_Tool_5": "old-crc",
        }
    }

    runtime = relics_runtime.RelicsRuntime(
        save_clone=lambda *args, **kwargs: calls.append(("save", args, kwargs)) or "saved",
        smash_brute_brawl=lambda *args, **kwargs: calls.append(("brawl", args, kwargs)),
        full_chunk_forcer_no_crc=lambda *args, **kwargs: None,
        tk_manual_plte=lambda *args, **kwargs: None,
        remove_chunk=lambda *args, **kwargs: None,
        ask_choice=lambda *args, **kwargs: None,
    )

    class FakeUi:
        @staticmethod
        def emit_pandemonium_summary(summary, *, emit, candy):
            calls.append(("summary", tuple(summary)))

        @staticmethod
        def emit_critical_hit(value, *, emit):
            emit("hit:%s" % value)

        @staticmethod
        def say_current_wrong_crc_idat(*, candy):
            calls.append(("ui", "current-idat"))

    context = SimpleNamespace(
        pandemonium={"sample.png": {}},
        pandora_box=pandora_box,
        cornucopia={},
        all_chunks=(b"IDAT",),
    )

    assert relics_runtime.handle_pandemonium_flow(
        runtime,
        relics,
        FakeUi,
        context,
        ask=lambda **kwargs: calls.append(("ask", (), kwargs)) or True,
        emit=emitted.append,
        pause=lambda message: calls.append(("pause", message)),
        show_todo=lambda: calls.append(("todo", (), {})),
        the_end=lambda: calls.append(("end", (), {})),
        candy=lambda *args: None,
    ) == (True, "saved")

    assert emitted == ["hit:Checksum_Error_0:Wrong Crc b'IDAT'"]
    assert [call[0] for call in calls] == ["summary", "ui", "ask", "save"]
    assert calls[-1] == (
        "save",
        (
            "new-crc-data",
            12,
            20,
            "-Found Chunk[b'IDAT'] has Wrong Crc at offset: 0x2a\n"
            "-Replaced with: new-crc-data old value was: old-crc",
        ),
        {},
    )


def test_relics_runtime_applies_no_pandemonium_repair_decisions():
    calls = []
    runtime = relics_runtime.RelicsRuntime(
        save_clone=lambda *args, **kwargs: None,
        smash_brute_brawl=lambda *args, **kwargs: calls.append(("brawl", args, kwargs)) or "brawl",
        full_chunk_forcer_no_crc=lambda *args, **kwargs: calls.append(("forcer", args, kwargs)) or "forcer",
        tk_manual_plte=lambda *args, **kwargs: None,
        remove_chunk=lambda *args, **kwargs: None,
        ask_choice=lambda *args, **kwargs: None,
    )

    assert relics_runtime.apply_no_pandemonium_repair_decision(
        runtime,
        relics.NoPandemoniumRepairDecision(
            "getinfo_brawl",
            relics.GetInfoBrawlPlan("sample.png", "IDAT", 277, 33, "GetInfo", "Brutus"),
        ),
    ) == (True, "brawl")
    assert relics_runtime.apply_no_pandemonium_repair_decision(
        runtime,
        relics.NoPandemoniumRepairDecision(
            "full_chunk_forcer",
            relics.FullChunkForcerPlan("sample.png", "tEXt", 33, 277, "GetInfo"),
        ),
    ) == (True, "forcer")
    assert relics_runtime.apply_no_pandemonium_repair_decision(
        runtime,
        relics.NoPandemoniumRepairDecision("none"),
    ) == (False, None)
    assert relics_runtime.apply_no_pandemonium_repair_decision(
        runtime,
        relics.NoPandemoniumRepairDecision("unsupported"),
    ) == (False, None)

    try:
        relics_runtime.apply_no_pandemonium_repair_decision(
            runtime,
            relics.NoPandemoniumRepairDecision("unknown"),
        )
    except ValueError as exc:
        assert "Unknown no-Pandemonium relic decision" in str(exc)
    else:
        raise AssertionError("unknown no-Pandemonium decisions must fail")

    assert [call[0] for call in calls] == ["brawl", "forcer"]


def test_relics_runtime_handles_no_pandemonium_getinfo_flow():
    calls = []
    emitted = []
    runtime = relics_runtime.RelicsRuntime(
        save_clone=lambda *args, **kwargs: None,
        smash_brute_brawl=lambda *args, **kwargs: calls.append(("brawl", args, kwargs)) or "brawl",
        full_chunk_forcer_no_crc=lambda *args, **kwargs: None,
        tk_manual_plte=lambda *args, **kwargs: None,
        remove_chunk=lambda *args, **kwargs: None,
        ask_choice=lambda *args, **kwargs: None,
    )

    class FakeUi:
        @staticmethod
        def say_no_pandemonium_intro(*, emit, candy):
            calls.append(("ui", "intro"))

        @staticmethod
        def emit_prompt_context_hits(prompt_context, *, emit):
            calls.append(("ui", "hits", prompt_context.print_hits))

        @staticmethod
        def say_no_pandemonium_getinfo(*, skip_bad_crc, candy):
            calls.append(("ui", "getinfo", skip_bad_crc))

        @staticmethod
        def say_no_pandemonium_forcer(*, candy):
            calls.append(("ui", "forcer"))

        @staticmethod
        def say_no_pandemonium_failure(*, candy):
            calls.append(("ui", "failure"))

    result = relics_runtime.handle_no_pandemonium_flow(
        runtime,
        relics,
        FakeUi,
        policy=relics.NoPandemoniumPolicy(
            action="getinfo_brawl",
            chunk_name="IDAT",
            struct_index_errors=("StructIndex:0", "StructIndex:1", "StructIndex:2"),
        ),
        prompt_context=relics.NoPandemoniumPromptContext(
            "getinfo_brawl",
            ("hit-0", "hit-1"),
        ),
        chunks_history=[b"IHDR", b"IDAT"],
        chunks_history_index=["0:8:21", "1:33:277"],
        target_file="sample.png",
        from_error="GetInfo",
        chunks_len_not_fixed=[],
        skip_bad_crc=False,
        ask=lambda: True,
        emit=emitted.append,
        candy=lambda *args: None,
        the_end=lambda: calls.append(("end", (), {})),
    )

    assert result == "brawl"
    assert calls == [
        ("ui", "intro"),
        ("ui", "hits", ("hit-0", "hit-1")),
        ("ui", "getinfo", False),
        ("brawl", ("sample.png", "IDAT", 277, 33, "GetInfo"), {"BfMode": "Brutus"}),
    ]


def test_relics_runtime_handles_no_pandemonium_forcer_flow():
    calls = []
    runtime = relics_runtime.RelicsRuntime(
        save_clone=lambda *args, **kwargs: None,
        smash_brute_brawl=lambda *args, **kwargs: None,
        full_chunk_forcer_no_crc=lambda *args, **kwargs: calls.append(("forcer", args, kwargs)) or "forcer",
        tk_manual_plte=lambda *args, **kwargs: None,
        remove_chunk=lambda *args, **kwargs: None,
        ask_choice=lambda *args, **kwargs: None,
    )

    class FakeUi:
        @staticmethod
        def say_no_pandemonium_intro(*, emit, candy):
            calls.append(("ui", "intro"))

        @staticmethod
        def emit_prompt_context_hits(prompt_context, *, emit):
            calls.append(("ui", "hits", prompt_context.print_hits))

        @staticmethod
        def say_no_pandemonium_getinfo(*, skip_bad_crc, candy):
            calls.append(("ui", "getinfo", skip_bad_crc))

        @staticmethod
        def say_no_pandemonium_forcer(*, candy):
            calls.append(("ui", "forcer"))

        @staticmethod
        def say_no_pandemonium_failure(*, candy):
            calls.append(("ui", "failure"))

    result = relics_runtime.handle_no_pandemonium_flow(
        runtime,
        relics,
        FakeUi,
        policy=relics.NoPandemoniumPolicy(
            action="full_chunk_forcer",
            known_chunk_route=relics.GetInfoChunkRoute("GetInfo_Error_0:tEXt", "tEXt"),
        ),
        prompt_context=relics.NoPandemoniumPromptContext(
            "full_chunk_forcer",
            ("hit-0",),
        ),
        chunks_history=["IHDR", "tEXt"],
        chunks_history_index=["0:8:21", "1:33:277"],
        target_file="sample.png",
        from_error="GetInfo",
        chunks_len_not_fixed=[],
        skip_bad_crc=True,
        ask=lambda: True,
        emit=lambda value: calls.append(("emit", (value,), {})),
        candy=lambda *args: None,
        the_end=lambda: calls.append(("end", (), {})),
    )

    assert result == "forcer"
    assert calls == [
        ("ui", "intro"),
        ("ui", "hits", ("hit-0",)),
        ("ui", "forcer"),
        ("forcer", ("sample.png", "tEXt", 33, 277, "GetInfo"), {}),
    ]


def test_relics_runtime_handles_no_pandemonium_failure_flow():
    class StopLegacyEnd(Exception):
        pass

    calls = []

    class FakeUi:
        @staticmethod
        def say_no_pandemonium_intro(*, emit, candy):
            calls.append(("ui", "intro"))

        @staticmethod
        def emit_prompt_context_hits(prompt_context, *, emit):
            calls.append(("ui", "hits"))

        @staticmethod
        def say_no_pandemonium_getinfo(*, skip_bad_crc, candy):
            calls.append(("ui", "getinfo"))

        @staticmethod
        def say_no_pandemonium_forcer(*, candy):
            calls.append(("ui", "forcer"))

        @staticmethod
        def say_no_pandemonium_failure(*, candy):
            calls.append(("ui", "failure"))

    def stop_end():
        calls.append(("end", (), {}))
        raise StopLegacyEnd()

    runtime = relics_runtime.RelicsRuntime(
        save_clone=lambda *args, **kwargs: None,
        smash_brute_brawl=lambda *args, **kwargs: None,
        full_chunk_forcer_no_crc=lambda *args, **kwargs: None,
        tk_manual_plte=lambda *args, **kwargs: None,
        remove_chunk=lambda *args, **kwargs: None,
        ask_choice=lambda *args, **kwargs: None,
    )

    try:
        relics_runtime.handle_no_pandemonium_flow(
            runtime,
            relics,
            FakeUi,
            policy=None,
            prompt_context=None,
            chunks_history=[],
            chunks_history_index=[],
            target_file="sample.png",
            from_error="GetInfo",
            chunks_len_not_fixed=[],
            skip_bad_crc=False,
            ask=lambda: True,
            emit=lambda value: calls.append(("emit", (value,), {})),
            candy=lambda *args: None,
            the_end=stop_end,
        )
    except StopLegacyEnd:
        pass
    else:
        raise AssertionError("no-Pandemonium failure should call the legacy end callback")

    assert calls == [("ui", "intro"), ("ui", "failure"), ("end", (), {})]


def main():
    checks = [
        ("RelicsRuntime keeps callbacks", test_relics_runtime_keeps_legacy_callbacks),
        ("Chunklate builds RelicsRuntime from legacy functions", test_chunklate_relics_runtime_uses_current_legacy_functions),
        ("RelicsRuntime runs SaveClone plans", test_relics_runtime_runs_save_clone_plan),
        ("RelicsRuntime runs brawl plans", test_relics_runtime_runs_brawl_plans),
        ("RelicsRuntime runs PLTE and forcer plans", test_relics_runtime_runs_plte_and_forcer_plans),
        ("RelicsRuntime handles current wrong CRC flow", test_relics_runtime_handles_current_wrong_crc_flow),
        (
            "RelicsRuntime handles remembered IDAT wrong CRC flow",
            test_relics_runtime_handles_remembered_idat_wrong_crc_flow,
        ),
        ("RelicsRuntime handles single-Pandemonium flow", test_relics_runtime_handles_single_pandemonium_flow),
        (
            "RelicsRuntime handles single-Pandemonium unsupported flow",
            test_relics_runtime_handles_single_pandemonium_unsupported_flow,
        ),
        ("RelicsRuntime applies PLTE repair decisions", test_relics_runtime_applies_plte_repair_decisions),
        (
            "RelicsRuntime handles PLTE repair flow with valid CRC",
            test_relics_runtime_handles_plte_repair_flow_with_valid_crc,
        ),
        (
            "RelicsRuntime handles PLTE repair flow with bad CRC",
            test_relics_runtime_handles_plte_repair_flow_with_bad_crc,
        ),
        (
            "RelicsRuntime handles PLTE repair flow fallback",
            test_relics_runtime_handles_plte_repair_flow_fallback,
        ),
        ("RelicsRuntime applies dummy chunk repair decisions", test_relics_runtime_applies_dummy_chunk_repair_decisions),
        (
            "RelicsRuntime handles remembered dummy chunk flow",
            test_relics_runtime_handles_remembered_dummy_chunk_flow,
        ),
        (
            "RelicsRuntime handles remembered dummy chunk decline and missing request",
            test_relics_runtime_handles_remembered_dummy_chunk_flow_decline_and_missing_request,
        ),
        (
            "RelicsRuntime skips empty Pandemonium flow",
            test_relics_runtime_skips_pandemonium_flow_without_pandemonium,
        ),
        (
            "RelicsRuntime handles Pandemonium current wrong CRC first",
            test_relics_runtime_handles_pandemonium_current_wrong_crc_first,
        ),
        (
            "RelicsRuntime applies no-Pandemonium repair decisions",
            test_relics_runtime_applies_no_pandemonium_repair_decisions,
        ),
        (
            "RelicsRuntime handles no-Pandemonium GetInfo flow",
            test_relics_runtime_handles_no_pandemonium_getinfo_flow,
        ),
        (
            "RelicsRuntime handles no-Pandemonium forcer flow",
            test_relics_runtime_handles_no_pandemonium_forcer_flow,
        ),
        (
            "RelicsRuntime handles no-Pandemonium failure flow",
            test_relics_runtime_handles_no_pandemonium_failure_flow,
        ),
    ]

    print("Running Relics runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"relics runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
