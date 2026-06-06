#!/usr/bin/env python3
import sys
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

    assert result == (False, None)
    assert state["brute_level"] == 1
    assert side_notes == [
        "-CheckPoint: Keeping partial IDAT blackfill after SmashBruteBrawl decline."
    ]
    assert ("end", (), {}) not in calls
    assert [call[0] for call in calls].count("candy") == 6


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

    assert result == (False, None)
    assert state["brute_level"] == 0
    assert side_notes == [
        "-CheckPoint: Keeping partial IDAT blackfill after SmashBruteBrawl failure."
    ]
    assert ("end", (), {}) not in calls
    assert [call[0] for call in calls].count("candy") == 2


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
    assert state["brute_level"] == 1
    assert side_notes == [
        "-CheckPoint: Increasing partial blackfill SmashBruteBrawl BruteLevel to 1."
    ]
    assert ("set_brute_level", (1,), {}) in calls
    assert (
        "smash_brute_brawl",
        ("sample.png", b"IDAT", 4, 100, "FixItFelix partial IDAT blackfill"),
        {
            "EditMode": "edit",
            "BfMode": "TwoBytes",
            "BruteCrc": "crc",
            "BruteLength": "length",
            "OldCrc": "old-crc",
        },
    ) in calls


def test_blackfill_failure_full_chunk_relaunches_before_fallback():
    calls = []
    runtime, state, side_notes = build_runtime(calls, question_answers=(False, True), brute_level=3)
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
        "-CheckPoint: Trying full chunk SmashBruteBrawl before keeping blackfill."
    ]
    assert ("set_brute_level", (0,), {}) in calls
    assert (
        "smash_brute_brawl",
        ("sample.png", b"IDAT", 4, 100, "FixItFelix partial IDAT blackfill"),
        {
            "EditMode": "edit",
            "BfMode": "Brutus",
            "BruteCrc": "crc",
            "BruteLength": "length",
            "OldCrc": "old-crc",
        },
    ) in calls


def test_blackfill_failure_decline_keeps_existing_fallback():
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
        "-CheckPoint: Keeping partial IDAT blackfill after SmashBruteBrawl failure."
    ]
    assert ("end", (), {}) not in calls
    assert [call[0] for call in calls].count("question") == 2


def test_checkpoint_action_namespace_builder_wires_state_and_callbacks():
    calls = []
    checkpoint_rt = object()
    namespace = {
        "CheckPoint_Runtime": lambda: calls.append(("checkpoint_runtime",)) or checkpoint_rt,
        "SideNotes": [],
        "CheckPoint_Apply_Flags": lambda flags: calls.append(("flags", flags)),
        "Raw_NextChunk": b"nEXT",
        "Brute_LvL": 3,
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
        ("Blackfill failure full chunk SBB", test_blackfill_failure_full_chunk_relaunches_before_fallback),
        ("Blackfill failure decline fallback", test_blackfill_failure_decline_keeps_existing_fallback),
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
