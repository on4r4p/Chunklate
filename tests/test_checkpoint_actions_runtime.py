#!/usr/bin/env python3
import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import checkpoint, checkpoint_actions_runtime, checkpoint_runtime


def build_runtime(
    calls,
    *,
    brute_level=0,
    eta=1,
    ihdr_interlace="0",
    question_answers=(True,),
    progress_path="",
    clear_smash_resume_files=None,
    force_brute_level=None,
):
    state = {"brute_level": brute_level}
    side_notes = []
    answers = iter(question_answers)

    def callback(name, result=None):
        def inner(*args, **kwargs):
            calls.append((name, args, kwargs))
            if name == "question":
                return next(answers)
            if result is not None:
                return result
            return name

        return inner

    def apply_flags(flags):
        calls.append(("apply_flags", (flags,), {}))

    def set_brute_level(value):
        calls.append(("set_brute_level", (value,), {}))
        state["brute_level"] = value

    checkpoint_rt = checkpoint_runtime.CheckPointRuntime(
        write_clone=callback("write_clone"),
        dummy_chunk=callback("dummy_chunk"),
        summarise=callback("summarise"),
        find_fucking_magic=callback("find_fucking_magic"),
        check_chunk_name=callback("check_chunk_name"),
        save_clone=callback("save_clone"),
        fix_it_felix=callback("fix_it_felix"),
        relics=callback("relics"),
        smash_brute_brawl=callback("smash_brute_brawl"),
        candy=callback("candy"),
        emit=callback("emit"),
        end=callback("end"),
        question=callback("question"),
        print_libpng_critical=callback("print_libpng_critical"),
        discard_libpng_warning=callback("discard_libpng_warning"),
        libpng_end_success=callback("libpng_end_success"),
    )

    runtime = checkpoint_actions_runtime.CheckPointActionRuntime(
        checkpoint=checkpoint_rt,
        side_notes=side_notes,
        apply_flags=apply_flags,
        raw_next_chunk=b"nEXT",
        get_brute_level=lambda: state["brute_level"],
        set_brute_level=set_brute_level,
        eta=eta,
        ihdr_interlace=ihdr_interlace,
        clear_smash_resume_files=clear_smash_resume_files or (lambda: None),
        progress_path=progress_path,
        force_brute_level=force_brute_level,
    )
    return runtime, state, side_notes


def test_apply_action_decision_applies_side_note_flags_and_write_clone():
    calls = []
    runtime, state, side_notes = build_runtime(calls)
    decision = checkpoint.CheckPointActionDecision(
        action="write_clone",
        side_note="-note",
        flags={"Bad_Crc": True},
    )

    result = checkpoint_actions_runtime.apply_action_decision(
        runtime,
        decision,
        b"IDAT",
        "-fixed",
        (b"fixed-png",),
    )

    assert result == (True, "write_clone")
    assert state["brute_level"] == 0
    assert side_notes == ["-note"]
    assert ("apply_flags", ({"Bad_Crc": True},), {}) in calls
    assert ("write_clone", (b"fixed-png", "-About to save."), {}) in calls


def test_apply_action_decision_rejects_unknown_action():
    calls = []
    runtime, state, side_notes = build_runtime(calls)
    decision = checkpoint.CheckPointActionDecision(action="unknown-action")

    try:
        checkpoint_actions_runtime.apply_action_decision(
            runtime,
            decision,
            b"IDAT",
            "-info",
            (),
        )
    except ValueError as exc:
        assert "unknown-action" in str(exc)
    else:
        raise AssertionError("unknown action should raise ValueError")

    assert state["brute_level"] == 0
    assert side_notes == []
    assert calls == [("apply_flags", (None,), {})]


def test_twobytes_retry_preserves_old_crc_route():
    calls = []
    runtime, state, side_notes = build_runtime(calls, eta=2)
    toolkit = (
        "sample.png",
        b"IDAT",
        4,
        100,
        "edit",
        "TwoBytes",
        "crc",
        "length",
        "old-crc",
        "from-error",
    )
    decision = checkpoint.CheckPointActionDecision(
        action="smash_brute_brawl_ask_twobytes_retry"
    )

    result = checkpoint_actions_runtime.apply_action_decision(
        runtime,
        decision,
        b"IDAT",
        "-Bruteforcer has Failed OldCrc",
        toolkit,
    )

    assert result == (False, None)
    assert state["brute_level"] == 1
    assert side_notes == [
        "-CheckPoint: Increasing BfLvl: -Bruteforcer has Failed OldCrc"
    ]
    assert ("set_brute_level", (1,), {}) in calls
    assert (
        "smash_brute_brawl",
        ("sample.png", b"IDAT", 4, 100, "from-error"),
        {
            "EditMode": "edit",
            "BfMode": "TwoBytes",
            "BruteCrc": "crc",
            "BruteLength": "length",
            "BruteLevel": 1,
            "OldCrc": "old-crc",
        },
    ) in calls


def test_custom_brutus_resets_brute_level_and_relaunches():
    calls = []
    runtime, state, side_notes = build_runtime(calls, brute_level=5)
    toolkit = (
        "sample.png",
        b"IDAT",
        4,
        100,
        "edit",
        "Custom",
        "crc",
        "length",
        "from-error",
    )
    decision = checkpoint.CheckPointActionDecision(
        action="smash_brute_brawl_ask_custom_brutus"
    )

    result = checkpoint_actions_runtime.apply_action_decision(
        runtime,
        decision,
        b"IDAT",
        "-Bruteforcer has Failed",
        toolkit,
    )

    assert result == (False, None)
    assert state["brute_level"] == 0
    assert side_notes == [
        "\n-Launched Data Chunk Bruteforcer.\n-Bruteforce has Failed!(CUSTOM END)"
    ]
    assert ("set_brute_level", (0,), {}) in calls
    assert (
        "smash_brute_brawl",
        ("sample.png", b"IDAT", 4, 100, "from-error"),
        {
            "EditMode": "edit",
            "BfMode": "Brutus",
            "BruteCrc": "crc",
            "BruteLength": "length",
        },
    ) in calls


def test_blackfill_twobytes_decline_keeps_existing_fallback():
    calls = []
    runtime, state, side_notes = build_runtime(calls, question_answers=(False,))
    toolkit = (
        "sample.png",
        b"IDAT",
        4,
        100,
        "edit",
        "TwoBytes",
        "crc",
        "length",
        "FixItFelix partial IDAT blackfill",
    )
    decision = checkpoint.CheckPointActionDecision(
        action="smash_brute_brawl_ask_twobytes_retry"
    )

    result = checkpoint_actions_runtime.apply_action_decision(
        runtime,
        decision,
        "IDAT",
        "-Bruteforcer has Failed",
        toolkit,
    )

    assert result == (True, "end")
    assert state["brute_level"] == 1
    assert side_notes == [
        "-CheckPoint: Keeping partial IDAT blackfill after SmashBruteBrawl decline."
    ]
    assert ("end", (), {}) in calls
    assert [call[0] for call in calls].count("candy") == 7


def test_blackfill_smash_failure_keeps_existing_fallback():
    calls = []
    runtime, state, side_notes = build_runtime(calls)
    toolkit = (
        "sample.png",
        b"IDAT",
        4,
        100,
        "edit",
        "TwoBytes",
        "crc",
        "length",
        "FixItFelix partial IDAT blackfill",
    )
    decision = checkpoint.CheckPointActionDecision(
        action="smash_brute_brawl_keep_blackfill_fallback"
    )

    result = checkpoint_actions_runtime.apply_action_decision(
        runtime,
        decision,
        "IDAT",
        "-Bruteforcer has Failed",
        toolkit,
    )

    assert result == (True, "end")
    assert state["brute_level"] == 0
    assert side_notes == [
        "-CheckPoint: Keeping partial IDAT blackfill after SmashBruteBrawl failure."
    ]
    assert ("end", (), {}) in calls
    assert [call[0] for call in calls].count("candy") == 3


def test_blackfill_failure_next_level_relaunches_with_old_crc():
    calls = []
    runtime, state, side_notes = build_runtime(calls, question_answers=(True,), eta=2)
    toolkit = (
        "sample.png",
        b"IDAT",
        4,
        100,
        "edit",
        "TwoBytes",
        "crc",
        "length",
        "old-crc",
        "FixItFelix partial IDAT blackfill",
    )
    decision = checkpoint.CheckPointActionDecision(
        action="smash_brute_brawl_ask_blackfill_next_step"
    )

    result = checkpoint_actions_runtime.apply_action_decision(
        runtime,
        decision,
        "IDAT",
        "-Bruteforcer has Failed",
        toolkit,
    )

    assert result == (False, None)
    assert state["brute_level"] == 0
    assert side_notes == [
        "-CheckPoint: Progressive SBB campaign trying HermesProbe Replace 1-byte window."
    ]
    assert ("set_brute_level", (0,), {}) in calls
    assert (
        "smash_brute_brawl",
        ("sample.png", b"IDAT", 4, 100, "FixItFelix partial IDAT blackfill"),
        {
            "EditMode": "Replace",
            "BfMode": "TwoBytes",
            "BruteCrc": "crc",
            "BruteLength": "length",
            "BruteLevel": 0,
            "OldCrc": "old-crc",
        },
    ) in calls


def test_blackfill_remove_twobytes_failure_tries_next_family_before_hephaestusforge():
    calls = []
    runtime, state, side_notes = build_runtime(calls, question_answers=())
    toolkit = (
        "sample.png",
        b"IDAT",
        4,
        100,
        "Remove",
        "TwoBytes",
        "crc",
        "length",
        "old-crc",
        "FixItFelix partial IDAT blackfill",
    )
    decision = checkpoint.CheckPointActionDecision(
        action="smash_brute_brawl_ask_blackfill_next_step"
    )

    result = checkpoint_actions_runtime.apply_action_decision(
        runtime,
        decision,
        "IDAT",
        "-Bruteforcer has Failed OldCrc",
        toolkit,
    )

    assert result == (False, None)
    assert state["brute_level"] == 0
    assert side_notes == [
        "-CheckPoint: Progressive SBB campaign trying HermesProbe Replace 1-byte window."
    ]
    assert runtime.retry_state.get("disable_resume_once") is True
    assert ("set_brute_level", (0,), {}) in calls
    assert (
        "smash_brute_brawl",
        ("sample.png", b"IDAT", 4, 100, "FixItFelix partial IDAT blackfill"),
        {
            "EditMode": "Replace",
            "BfMode": "TwoBytes",
            "BruteCrc": "crc",
            "BruteLength": "length",
            "BruteLevel": 0,
            "OldCrc": "old-crc",
        },
    ) in calls


def test_blackfill_failure_opens_hephaestusforge_before_fallback():
    calls = []
    runtime, state, side_notes = build_runtime(calls, question_answers=(False, True), brute_level=3)
    toolkit = (
        "sample.png",
        b"IDAT",
        4,
        100,
        "Insert",
        "TwoBytes",
        "crc",
        "length",
        "old-crc",
        "FixItFelix partial IDAT blackfill",
    )
    decision = checkpoint.CheckPointActionDecision(
        action="smash_brute_brawl_ask_blackfill_next_step"
    )

    result = checkpoint_actions_runtime.apply_action_decision(
        runtime,
        decision,
        "IDAT",
        "-Bruteforcer has Failed",
        toolkit,
    )

    assert result == (False, None)
    assert state["brute_level"] == 1
    assert side_notes == [
        "-CheckPoint: Progressive SBB campaign trying HephaestusForge Insert level 1."
    ]
    assert ("set_brute_level", (1,), {}) in calls
    assert (
        "smash_brute_brawl",
        ("sample.png", b"IDAT", 4, 100, "FixItFelix partial IDAT blackfill"),
        {
            "EditMode": "Insert",
            "BfMode": "Brutus",
            "BruteCrc": "crc",
            "BruteLength": "length",
            "BruteLevel": 1,
            "OldCrc": "old-crc",
        },
    ) in calls


def test_blackfill_failure_auto_retries_without_questions():
    calls = []
    runtime, state, side_notes = build_runtime(calls, question_answers=(False, False))
    toolkit = (
        "sample.png",
        b"IDAT",
        4,
        100,
        "edit",
        "TwoBytes",
        "crc",
        "length",
        "old-crc",
        "FixItFelix partial IDAT blackfill",
    )
    decision = checkpoint.CheckPointActionDecision(
        action="smash_brute_brawl_ask_blackfill_next_step"
    )

    result = checkpoint_actions_runtime.apply_action_decision(
        runtime,
        decision,
        "IDAT",
        "-Bruteforcer has Failed",
        toolkit,
    )

    assert result == (False, None)
    assert state["brute_level"] == 0
    assert side_notes == [
        "-CheckPoint: Progressive SBB campaign trying HermesProbe Replace 1-byte window."
    ]
    assert (
        "smash_brute_brawl",
        ("sample.png", b"IDAT", 4, 100, "FixItFelix partial IDAT blackfill"),
        {
            "EditMode": "Replace",
            "BfMode": "TwoBytes",
            "BruteCrc": "crc",
            "BruteLength": "length",
            "BruteLevel": 0,
            "OldCrc": "old-crc",
        },
    ) in calls
    assert [call[0] for call in calls].count("question") == 0


def test_blackfill_failure_prompts_before_measured_long_pass():
    calls = []
    clear_calls = []
    with tempfile.TemporaryDirectory() as directory:
        progress_path = str(Path(directory) / "_SBB.progress.json")
        Path(progress_path).write_text(
            json.dumps(
                {
                    "status": "exhausted",
                    "counters": {
                        "tested_candidates": 6_291_456,
                        "elapsed_seconds": 60,
                    },
                }
            ),
            encoding="utf-8",
        )
        runtime, state, side_notes = build_runtime(
            calls,
            question_answers=(False,),
            progress_path=progress_path,
            clear_smash_resume_files=lambda: clear_calls.append("clear"),
        )
        runtime.retry_state["campaign_focus"] = "insert"
        toolkit = (
            "sample.png",
            b"IDAT",
            8192,
            100,
            "Insert",
            "TwoBytes",
            "crc",
            "length",
            "old-crc",
            "FixItFelix partial IDAT blackfill",
        )
        decision = checkpoint.CheckPointActionDecision(
            action="smash_brute_brawl_ask_blackfill_next_step"
        )

        result = checkpoint_actions_runtime.apply_action_decision(
            runtime,
            decision,
            "IDAT",
            "-Bruteforcer has Failed",
            toolkit,
        )
        progress_still_exists = Path(progress_path).exists()

    assert result == (True, "end")
    assert state["brute_level"] == 0
    assert clear_calls == []
    assert progress_still_exists is True
    assert [call[0] for call in calls].count("question") == 1
    assert any(
        call[0] == "emit"
        and "SBB estimated next pass (HermesProbe Insert 2-byte window)" in call[1][0]
        for call in calls
    )
    assert all(call[0] != "smash_brute_brawl" for call in calls)


def test_blackfill_rejected_hit_status_is_reported_before_next_pass():
    calls = []
    with tempfile.TemporaryDirectory() as directory:
        progress_path = str(Path(directory) / "_SBB.progress.json")
        Path(progress_path).write_text(
            json.dumps(
                {
                    "status": "rejected_hit",
                    "counters": {
                        "tested_candidates": 42,
                        "rejected_candidates": 1,
                        "elapsed_seconds": 1,
                    },
                }
            ),
            encoding="utf-8",
        )
        runtime, state, side_notes = build_runtime(
            calls,
            progress_path=progress_path,
        )
        toolkit = (
            "sample.png",
            b"IDAT",
            4,
            100,
            "Insert",
            "TwoBytes",
            "crc",
            "length",
            "old-crc",
            "FixItFelix partial IDAT blackfill",
        )
        decision = checkpoint.CheckPointActionDecision(
            action="smash_brute_brawl_ask_blackfill_next_step"
        )

        result = checkpoint_actions_runtime.apply_action_decision(
            runtime,
            decision,
            "IDAT",
            "-Bruteforcer has Failed OldCrc",
            toolkit,
        )

    assert result == (False, None)
    assert state["brute_level"] == 0
    assert runtime.retry_state["attempt_records"] == [
        {
            "bf_mode": "TwoBytes",
            "edit_mode": "Insert",
            "brute_level": 0,
            "focus": "progressive",
            "brute_crc": "crc",
            "brute_length": "length",
            "old_crc": "old-crc",
            "status": "rejected_hit",
            "tested_candidates": 42,
            "elapsed_seconds": 1,
        }
    ]
    assert any(
        call[0] == "emit" and "SBB pass rejected invalid candidates" in call[1][0]
        for call in calls
    )
    assert (
        "smash_brute_brawl",
        ("sample.png", b"IDAT", 4, 100, "FixItFelix partial IDAT blackfill"),
        {
            "EditMode": "Replace",
            "BfMode": "TwoBytes",
            "BruteCrc": "crc",
            "BruteLength": "length",
            "BruteLevel": 0,
            "OldCrc": "old-crc",
        },
    ) in calls


def test_blackfill_eta_formatter_handles_huge_values_without_overflow():
    assert checkpoint_actions_runtime._format_sbb_eta(13_122_988_552_192) == (
        "151,886,441 days, 13:49:52"
    )
    assert checkpoint_actions_runtime._format_sbb_eta("nope") == "unknown"


def test_blackfill_hephaestus_estimates_insert_replace_value_space():
    assert checkpoint_actions_runtime._blackfill_estimated_brutus_candidates(
        edit_mode="Insert",
        brute_level=1,
        chunk_length=8192,
    ) == 65_792
    assert checkpoint_actions_runtime._blackfill_estimated_brutus_candidates(
        edit_mode="Replace",
        brute_level=2,
        chunk_length=8192,
    ) == 16_843_008


def test_blackfill_hephaestus_remove_estimates_windows_not_byte_values():
    assert checkpoint_actions_runtime._blackfill_estimated_brutus_candidates(
        edit_mode="Remove",
        brute_level=15,
        chunk_length=8192,
    ) == 130_952


def test_blackfill_hephaestus_remove_fast_pass_does_not_prompt():
    calls = []
    with tempfile.TemporaryDirectory() as directory:
        progress_path = str(Path(directory) / "_SBB.progress.json")
        Path(progress_path).write_text(
            json.dumps(
                {
                    "status": "exhausted",
                    "counters": {
                        "tested_candidates": 65_508,
                        "elapsed_seconds": 60,
                    },
                }
            ),
            encoding="utf-8",
        )
        runtime, state, side_notes = build_runtime(
            calls,
            brute_level=7,
            question_answers=(),
            progress_path=progress_path,
        )
        runtime.retry_state["campaign_focus"] = "remove"
        toolkit = (
            "sample.png",
            b"IDAT",
            8192,
            100,
            "Remove",
            "Brutus",
            "crc",
            "length",
            "old-crc",
            "FixItFelix partial IDAT blackfill",
        )
        decision = checkpoint.CheckPointActionDecision(
            action="smash_brute_brawl_ask_blackfill_next_step"
        )

        result = checkpoint_actions_runtime.apply_action_decision(
            runtime,
            decision,
            "IDAT",
            "-Bruteforcer has Failed",
            toolkit,
        )

    assert result == (False, None)
    assert state["brute_level"] == 15
    assert [call[0] for call in calls].count("question") == 0
    assert (
        "smash_brute_brawl",
        ("sample.png", b"IDAT", 8192, 100, "FixItFelix partial IDAT blackfill"),
        {
            "EditMode": "Remove",
            "BfMode": "Brutus",
            "BruteCrc": "crc",
            "BruteLength": "length",
            "BruteLevel": 15,
            "OldCrc": "old-crc",
        },
    ) in calls


def test_blackfill_success_status_is_terminal_for_campaign_action():
    calls = []
    with tempfile.TemporaryDirectory() as directory:
        progress_path = str(Path(directory) / "_SBB.progress.json")
        Path(progress_path).write_text(
            json.dumps(
                {
                    "status": "success",
                    "counters": {
                        "tested_candidates": 7,
                        "accepted_candidates": 1,
                        "elapsed_seconds": 2,
                    },
                }
            ),
            encoding="utf-8",
        )
        runtime, state, side_notes = build_runtime(
            calls,
            progress_path=progress_path,
        )
        toolkit = (
            "sample.png",
            b"IDAT",
            4,
            100,
            "Insert",
            "TwoBytes",
            "crc",
            "length",
            "old-crc",
            "FixItFelix partial IDAT blackfill",
        )
        decision = checkpoint.CheckPointActionDecision(
            action="smash_brute_brawl_ask_blackfill_next_step"
        )

        result = checkpoint_actions_runtime.apply_action_decision(
            runtime,
            decision,
            "IDAT",
            "-Bruteforcer has Failed OldCrc",
            toolkit,
        )

    assert result == (False, None)
    assert state["brute_level"] == 0
    assert side_notes == [
        "-CheckPoint: SBB pass already produced a validated hit; no further campaign pass launched."
    ]
    assert runtime.retry_state == {}
    assert all(call[0] != "smash_brute_brawl" for call in calls)


def test_blackfill_hephaestus_campaign_does_not_skip_level_two():
    calls = []
    runtime, state, side_notes = build_runtime(calls, brute_level=1)
    runtime.retry_state["campaign_focus"] = "insert"
    toolkit = (
        "sample.png",
        b"IDAT",
        8192,
        100,
        "Insert",
        "Brutus",
        "crc",
        "length",
        "old-crc",
        "FixItFelix partial IDAT blackfill",
    )
    decision = checkpoint.CheckPointActionDecision(
        action="smash_brute_brawl_ask_blackfill_next_step"
    )

    result = checkpoint_actions_runtime.apply_action_decision(
        runtime,
        decision,
        "IDAT",
        "-Bruteforcer has Failed",
        toolkit,
    )

    assert result == (False, None)
    assert state["brute_level"] == 2
    assert side_notes == [
        "-CheckPoint: Progressive SBB campaign trying HephaestusForge Insert level 2."
    ]
    assert (
        "smash_brute_brawl",
        ("sample.png", b"IDAT", 8192, 100, "FixItFelix partial IDAT blackfill"),
        {
            "EditMode": "Insert",
            "BfMode": "Brutus",
            "BruteCrc": "crc",
            "BruteLength": "length",
            "BruteLevel": 2,
            "OldCrc": "old-crc",
        },
    ) in calls


def test_blackfill_hephaestus_uses_active_pass_level_when_global_level_is_stale():
    calls = []
    runtime, state, side_notes = build_runtime(calls, brute_level=0)
    runtime.retry_state["campaign_focus"] = "insert"
    runtime.retry_state["active_pass"] = {
        "edit_mode": "Insert",
        "bf_mode": "Brutus",
        "brute_level": 1,
    }
    toolkit = (
        "sample.png",
        b"IDAT",
        8192,
        100,
        "Insert",
        "Brutus",
        "crc",
        "length",
        "old-crc",
        "FixItFelix partial IDAT blackfill",
    )
    decision = checkpoint.CheckPointActionDecision(
        action="smash_brute_brawl_ask_blackfill_next_step"
    )

    result = checkpoint_actions_runtime.apply_action_decision(
        runtime,
        decision,
        "IDAT",
        "-Bruteforcer has Failed",
        toolkit,
    )

    assert result == (False, None)
    assert state["brute_level"] == 2
    assert side_notes == [
        "-CheckPoint: Progressive SBB campaign trying HephaestusForge Insert level 2."
    ]
    assert (
        "smash_brute_brawl",
        ("sample.png", b"IDAT", 8192, 100, "FixItFelix partial IDAT blackfill"),
        {
            "EditMode": "Insert",
            "BfMode": "Brutus",
            "BruteCrc": "crc",
            "BruteLength": "length",
            "BruteLevel": 2,
            "OldCrc": "old-crc",
        },
    ) in calls
    assert not any(
        call[0] == "smash_brute_brawl" and call[2].get("BruteLevel") == 1
        for call in calls
    )


def test_blackfill_hephaestus_uses_progress_invocation_level_when_global_level_is_stale():
    calls = []
    with tempfile.TemporaryDirectory() as directory:
        progress_path = str(Path(directory) / "_SBB.progress.json")
        Path(progress_path).write_text(
            json.dumps(
                {
                    "status": "exhausted",
                    "invocation": {
                        "edit_mode": "Insert",
                        "bf_mode": "Brutus",
                        "brute_level": 1,
                    },
                    "counters": {
                        "tested_candidates": 65792,
                        "elapsed_seconds": 2,
                    },
                }
            ),
            encoding="utf-8",
        )
        runtime, state, side_notes = build_runtime(
            calls,
            brute_level=0,
            progress_path=progress_path,
        )
        runtime.retry_state["campaign_focus"] = "insert"
        toolkit = (
            "sample.png",
            b"IDAT",
            8192,
            100,
            "Insert",
            "Brutus",
            "crc",
            "length",
            "old-crc",
            "FixItFelix partial IDAT blackfill",
        )
        decision = checkpoint.CheckPointActionDecision(
            action="smash_brute_brawl_ask_blackfill_next_step"
        )

        result = checkpoint_actions_runtime.apply_action_decision(
            runtime,
            decision,
            "IDAT",
            "-Bruteforcer has Failed",
            toolkit,
        )

    assert result == (False, None)
    assert state["brute_level"] == 2
    assert side_notes == [
        "-CheckPoint: Progressive SBB campaign trying HephaestusForge Insert level 2."
    ]
    assert (
        "smash_brute_brawl",
        ("sample.png", b"IDAT", 8192, 100, "FixItFelix partial IDAT blackfill"),
        {
            "EditMode": "Insert",
            "BfMode": "Brutus",
            "BruteCrc": "crc",
            "BruteLength": "length",
            "BruteLevel": 2,
            "OldCrc": "old-crc",
        },
    ) in calls


def test_blackfill_hephaestus_prompts_before_measured_long_pass():
    calls = []
    with tempfile.TemporaryDirectory() as directory:
        progress_path = str(Path(directory) / "_SBB.progress.json")
        Path(progress_path).write_text(
            json.dumps(
                {
                    "status": "exhausted",
                    "counters": {
                        "tested_candidates": 6_291_456,
                        "elapsed_seconds": 60,
                    },
                }
            ),
            encoding="utf-8",
        )
        runtime, state, side_notes = build_runtime(
            calls,
            brute_level=2,
            question_answers=(False,),
            progress_path=progress_path,
        )
        runtime.retry_state["campaign_focus"] = "insert"
        toolkit = (
            "sample.png",
            b"IDAT",
            8192,
            100,
            "Insert",
            "Brutus",
            "crc",
            "length",
            "old-crc",
            "FixItFelix partial IDAT blackfill",
        )
        decision = checkpoint.CheckPointActionDecision(
            action="smash_brute_brawl_ask_blackfill_next_step"
        )

        result = checkpoint_actions_runtime.apply_action_decision(
            runtime,
            decision,
            "IDAT",
            "-Bruteforcer has Failed",
            toolkit,
        )

    assert result == (True, "end")
    assert state["brute_level"] == 2
    assert [call[0] for call in calls].count("question") == 1
    assert any(
        call[0] == "emit" and "SBB estimated next pass" in call[1][0]
        for call in calls
    )
    assert all(call[0] != "smash_brute_brawl" for call in calls)


def test_blackfill_failure_after_hephaestusforge_keeps_existing_fallback():
    calls = []
    runtime, state, side_notes = build_runtime(calls, question_answers=())
    toolkit = (
        "sample.png",
        b"IDAT",
        4,
        100,
        "edit",
        "Brutus",
        "crc",
        "length",
        "old-crc",
        "FixItFelix partial IDAT blackfill",
    )
    decision = checkpoint.CheckPointActionDecision(
        action="smash_brute_brawl_ask_blackfill_next_step"
    )

    result = checkpoint_actions_runtime.apply_action_decision(
        runtime,
        decision,
        "IDAT",
        "-Bruteforcer has Failed",
        toolkit,
    )

    assert result == (False, None)
    assert state["brute_level"] == 1
    assert side_notes == [
        "-CheckPoint: Progressive SBB campaign trying HephaestusForge Replace level 1."
    ]
    assert (
        "smash_brute_brawl",
        ("sample.png", b"IDAT", 4, 100, "FixItFelix partial IDAT blackfill"),
        {
            "EditMode": "Replace",
            "BfMode": "Brutus",
            "BruteCrc": "crc",
            "BruteLength": "length",
            "BruteLevel": 1,
            "OldCrc": "old-crc",
        },
    ) in calls
    assert [call[0] for call in calls].count("question") == 0


def test_blackfill_hephaestusforge_failure_tries_next_edit_family():
    calls = []
    runtime, state, side_notes = build_runtime(calls, question_answers=(True,), brute_level=1)
    toolkit = (
        "sample.png",
        b"IDAT",
        4,
        100,
        "Insert",
        "Brutus",
        "crc",
        "length",
        "old-crc",
        "FixItFelix partial IDAT blackfill HephaestusForge",
    )
    decision = checkpoint.CheckPointActionDecision(
        action="smash_brute_brawl_ask_blackfill_next_step"
    )

    result = checkpoint_actions_runtime.apply_action_decision(
        runtime,
        decision,
        "IDAT",
        "-Bruteforcer has Failed",
        toolkit,
    )

    assert result == (False, None)
    assert state["brute_level"] == 1
    assert side_notes == [
        "-CheckPoint: Progressive SBB campaign trying HephaestusForge Replace level 1."
    ]
    assert ("set_brute_level", (1,), {}) in calls
    assert (
        "smash_brute_brawl",
        ("sample.png", b"IDAT", 4, 100, "FixItFelix partial IDAT blackfill HephaestusForge"),
        {
            "EditMode": "Replace",
            "BfMode": "Brutus",
            "BruteCrc": "crc",
            "BruteLength": "length",
            "BruteLevel": 1,
            "OldCrc": "old-crc",
        },
    ) in calls


def test_blackfill_hephaestusforge_remove_failure_tries_replace_without_prompt():
    calls = []
    runtime, state, side_notes = build_runtime(calls, question_answers=(), brute_level=1)
    toolkit = (
        "sample.png",
        b"IDAT",
        4,
        100,
        "Remove",
        "Brutus",
        "crc",
        "length",
        "old-crc",
        "FixItFelix partial IDAT blackfill HephaestusForge",
    )
    decision = checkpoint.CheckPointActionDecision(
        action="smash_brute_brawl_ask_blackfill_next_step"
    )

    result = checkpoint_actions_runtime.apply_action_decision(
        runtime,
        decision,
        "IDAT",
        "-Bruteforcer has Failed",
        toolkit,
    )

    assert result == (False, None)
    assert state["brute_level"] == 1
    assert side_notes == [
        "-CheckPoint: Progressive SBB campaign trying HephaestusForge Replace level 1."
    ]
    assert ("set_brute_level", (1,), {}) in calls
    assert (
        "smash_brute_brawl",
        ("sample.png", b"IDAT", 4, 100, "FixItFelix partial IDAT blackfill HephaestusForge"),
        {
            "EditMode": "Replace",
            "BfMode": "Brutus",
            "BruteCrc": "crc",
            "BruteLength": "length",
            "BruteLevel": 1,
            "OldCrc": "old-crc",
        },
    ) in calls
    assert [call[0] for call in calls].count("question") == 0


def test_blackfill_brutus_remove_failure_keeps_edit_sequence_without_hephaestus_label():
    calls = []
    runtime, state, side_notes = build_runtime(calls, question_answers=(), brute_level=1)
    toolkit = (
        "sample.png",
        b"IDAT",
        4,
        100,
        "Remove",
        "Brutus",
        "crc",
        "length",
        "old-crc",
        "FixItFelix partial IDAT blackfill",
    )
    decision = checkpoint.CheckPointActionDecision(
        action="smash_brute_brawl_ask_blackfill_next_step"
    )

    result = checkpoint_actions_runtime.apply_action_decision(
        runtime,
        decision,
        "IDAT",
        "-Bruteforcer has Failed",
        toolkit,
    )

    assert result == (False, None)
    assert state["brute_level"] == 1
    assert side_notes == [
        "-CheckPoint: Progressive SBB campaign trying HephaestusForge Replace level 1."
    ]
    assert (
        "smash_brute_brawl",
        ("sample.png", b"IDAT", 4, 100, "FixItFelix partial IDAT blackfill"),
        {
            "EditMode": "Replace",
            "BfMode": "Brutus",
            "BruteCrc": "crc",
            "BruteLength": "length",
            "BruteLevel": 1,
            "OldCrc": "old-crc",
        },
    ) in calls


def test_blackfill_retry_skips_already_attempted_hephaestus_edit():
    calls = []
    runtime, state, side_notes = build_runtime(calls, question_answers=(), brute_level=1)
    toolkit = (
        "sample.png",
        b"IDAT",
        4,
        100,
        "Remove",
        "Brutus",
        "crc",
        "length",
        "old-crc",
        "FixItFelix partial IDAT blackfill HephaestusForge",
    )
    runtime.retry_state["campaign_focus"] = "progressive"
    runtime.retry_state["hephaestus_order"] = ("Remove", "Replace", "Insert")
    checkpoint_actions_runtime._blackfill_mark_attempt(
        runtime,
        toolkit,
        edit_mode="Replace",
        bf_mode="Brutus",
        brute_level=1,
    )
    decision = checkpoint.CheckPointActionDecision(
        action="smash_brute_brawl_ask_blackfill_next_step"
    )

    result = checkpoint_actions_runtime.apply_action_decision(
        runtime,
        decision,
        "IDAT",
        "-Bruteforcer has Failed",
        toolkit,
    )

    assert result == (False, None)
    assert state["brute_level"] == 1
    assert side_notes == [
        "-CheckPoint: Progressive SBB campaign trying HephaestusForge Insert level 1."
    ]
    assert (
        "smash_brute_brawl",
        ("sample.png", b"IDAT", 4, 100, "FixItFelix partial IDAT blackfill HephaestusForge"),
        {
            "EditMode": "Insert",
            "BfMode": "Brutus",
            "BruteCrc": "crc",
            "BruteLength": "length",
            "BruteLevel": 1,
            "OldCrc": "old-crc",
        },
    ) in calls


def test_blackfill_focus_campaign_runs_all_hermes_before_hephaestus():
    calls = []
    runtime, _state, _side_notes = build_runtime(calls)
    toolkit = (
        "sample.png",
        b"IDAT",
        4,
        100,
        "Remove",
        "TwoBytes",
        "crc",
        "length",
        "old-crc",
        "FixItFelix partial IDAT blackfill",
    )
    runtime.retry_state["campaign_focus"] = "remove"
    runtime.retry_state["hephaestus_order"] = ("Remove", "Replace", "Insert")

    attempts = checkpoint_actions_runtime._blackfill_campaign_attempts(
        runtime,
        toolkit,
        current_edit="Remove",
        current_mode="TwoBytes",
    )

    assert attempts[:9] == (
        ("Remove", "TwoBytes", 0),
        ("Remove", "TwoBytes", 1),
        ("Remove", "TwoBytes", 2),
        ("Replace", "TwoBytes", 0),
        ("Replace", "TwoBytes", 1),
        ("Replace", "TwoBytes", 2),
        ("Insert", "TwoBytes", 0),
        ("Insert", "TwoBytes", 1),
        ("Insert", "TwoBytes", 2),
    )
    assert attempts[9:15] == (
        ("Remove", "Brutus", 1),
        ("Remove", "Brutus", 2),
        ("Remove", "Brutus", 3),
        ("Remove", "Brutus", 4),
        ("Remove", "Brutus", 7),
        ("Remove", "Brutus", 15),
    )


def test_blackfill_attempt_label_names_hermes_direct_windows():
    assert (
        checkpoint_actions_runtime._blackfill_attempt_label("Replace", "TwoBytes", 0)
        == "HermesProbe Replace 1-byte window"
    )
    assert (
        checkpoint_actions_runtime._blackfill_attempt_label("Replace", "TwoBytes", 1)
        == "HermesProbe Replace 2-byte window"
    )
    assert (
        checkpoint_actions_runtime._blackfill_attempt_label("Replace", "TwoBytes", 2)
        == "HermesProbe Replace 4-byte window"
    )


def test_blackfill_estimates_hermes_level_one_as_direct_two_byte_window():
    calls = []
    runtime, _state, _side_notes = build_runtime(calls)
    payload_bytes = 1_455_181
    toolkit = (
        "sample.png",
        b"IDAT",
        payload_bytes,
        100,
        "Replace",
        "TwoBytes",
        "crc",
        "length",
        "old-crc",
        "FixItFelix partial IDAT blackfill",
    )

    estimated = checkpoint_actions_runtime._blackfill_estimated_next_candidates(
        runtime,
        toolkit,
        edit_mode="Replace",
        bf_mode="TwoBytes",
        brute_level=1,
        previous_tested=payload_bytes * 256,
    )

    assert estimated == (payload_bytes - 1) * (256**2)


def test_blackfill_progressive_campaign_keeps_level_first_order():
    calls = []
    runtime, _state, _side_notes = build_runtime(calls)
    toolkit = (
        "sample.png",
        b"IDAT",
        4,
        100,
        "Remove",
        "TwoBytes",
        "crc",
        "length",
        "old-crc",
        "FixItFelix partial IDAT blackfill",
    )
    runtime.retry_state["campaign_focus"] = "progressive"
    runtime.retry_state["hephaestus_order"] = ("Remove", "Replace", "Insert")

    attempts = checkpoint_actions_runtime._blackfill_campaign_attempts(
        runtime,
        toolkit,
        current_edit="Remove",
        current_mode="TwoBytes",
    )

    assert attempts[:6] == (
        ("Remove", "TwoBytes", 0),
        ("Replace", "TwoBytes", 0),
        ("Insert", "TwoBytes", 0),
        ("Remove", "TwoBytes", 1),
        ("Replace", "TwoBytes", 1),
        ("Insert", "TwoBytes", 1),
    )


def test_blackfill_forced_level_skips_lower_campaign_levels():
    calls = []
    runtime, _state, _side_notes = build_runtime(calls, force_brute_level=2)
    toolkit = (
        "sample.png",
        b"IDAT",
        4,
        100,
        "Replace",
        "TwoBytes",
        "crc",
        "length",
        "old-crc",
        "FixItFelix partial IDAT blackfill",
    )
    runtime.retry_state["campaign_focus"] = "progressive"
    runtime.retry_state["hephaestus_order"] = ("Replace", "Insert", "Remove")

    attempts = checkpoint_actions_runtime._blackfill_campaign_attempts(
        runtime,
        toolkit,
        current_edit="Replace",
        current_mode="TwoBytes",
    )

    assert attempts[:6] == (
        ("Replace", "TwoBytes", 2),
        ("Insert", "TwoBytes", 2),
        ("Remove", "TwoBytes", 2),
        ("Replace", "Brutus", 2),
        ("Insert", "Brutus", 2),
        ("Remove", "Brutus", 2),
    )
    assert all(level >= 2 for _edit, _mode, level in attempts)


def test_checkpoint_action_namespace_builder_wires_state_and_callbacks():
    calls = []
    checkpoint_rt = object()
    namespace = {
        "CheckPoint_Runtime": lambda: calls.append(("checkpoint_runtime",)) or checkpoint_rt,
        "SideNotes": [],
        "CheckPoint_Apply_Flags": lambda flags: calls.append(("flags", flags)),
        "Raw_NextChunk": b"nEXT",
        "Brute_LvL": 3,
        "SMASH_BRUTE_BRAWL_FORCE_LEVEL": "2",
        "ETA": 7,
        "IHDR_Interlace": "1",
    }

    runtime = checkpoint_actions_runtime.build_checkpoint_action_runtime_from_namespace(namespace)

    assert runtime.checkpoint is checkpoint_rt
    assert runtime.side_notes is namespace["SideNotes"]
    assert runtime.apply_flags is namespace["CheckPoint_Apply_Flags"]
    assert runtime.raw_next_chunk == b"nEXT"
    assert runtime.get_brute_level() == 3
    runtime.set_brute_level(4)
    assert namespace["Brute_LvL"] == 4
    assert runtime.force_brute_level == 2
    assert runtime.eta == 7
    assert runtime.ihdr_interlace == "1"
    runtime.apply_flags({"Bad_Crc": True})
    assert calls == [("checkpoint_runtime",), ("flags", {"Bad_Crc": True})]


def main():
    checks = [
        (
            "Apply side notes, flags, and WriteClone",
            test_apply_action_decision_applies_side_note_flags_and_write_clone,
        ),
        ("Reject unknown action", test_apply_action_decision_rejects_unknown_action),
        ("Preserve TwoBytes OldCrc retry", test_twobytes_retry_preserves_old_crc_route),
        ("Reset Custom Brutus retry", test_custom_brutus_resets_brute_level_and_relaunches),
        ("Keep blackfill on TwoBytes decline", test_blackfill_twobytes_decline_keeps_existing_fallback),
        ("Keep blackfill on SmashBruteBrawl failure", test_blackfill_smash_failure_keeps_existing_fallback),
        ("Blackfill failure next SBB level", test_blackfill_failure_next_level_relaunches_with_old_crc),
        ("Blackfill failure opens HephaestusForge", test_blackfill_failure_opens_hephaestusforge_before_fallback),
        ("Blackfill failure auto retry", test_blackfill_failure_auto_retries_without_questions),
        ("Blackfill long pass ETA prompt", test_blackfill_failure_prompts_before_measured_long_pass),
        ("Blackfill rejected hit transition", test_blackfill_rejected_hit_status_is_reported_before_next_pass),
        ("Blackfill success status terminal", test_blackfill_success_status_is_terminal_for_campaign_action),
        ("Blackfill HephaestusForge does not skip level 2", test_blackfill_hephaestus_campaign_does_not_skip_level_two),
        (
            "Blackfill HephaestusForge active pass level",
            test_blackfill_hephaestus_uses_active_pass_level_when_global_level_is_stale,
        ),
        (
            "Blackfill HephaestusForge progress pass level",
            test_blackfill_hephaestus_uses_progress_invocation_level_when_global_level_is_stale,
        ),
        ("Blackfill HephaestusForge long pass ETA prompt", test_blackfill_hephaestus_prompts_before_measured_long_pass),
        ("Blackfill failure after HephaestusForge", test_blackfill_failure_after_hephaestusforge_keeps_existing_fallback),
        ("Blackfill HephaestusForge next edit", test_blackfill_hephaestusforge_failure_tries_next_edit_family),
        ("Blackfill HephaestusForge Remove next edit", test_blackfill_hephaestusforge_remove_failure_tries_replace_without_prompt),
        ("Blackfill Brutus Remove keeps edit sequence", test_blackfill_brutus_remove_failure_keeps_edit_sequence_without_hephaestus_label),
        ("Blackfill retry skips attempted edit", test_blackfill_retry_skips_already_attempted_hephaestus_edit),
        ("Blackfill focus campaign order", test_blackfill_focus_campaign_runs_all_hermes_before_hephaestus),
        ("Blackfill progressive campaign order", test_blackfill_progressive_campaign_keeps_level_first_order),
        ("Blackfill forced campaign level", test_blackfill_forced_level_skips_lower_campaign_levels),
        ("Namespace action runtime", test_checkpoint_action_namespace_builder_wires_state_and_callbacks),
    ]

    print("Running CheckPoint action runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"checkpoint action runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
