#!/usr/bin/env python3
import sys
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import fixit_felix
from chunklate import fixit_felix_runtime


def test_apply_repair_records_note_and_writes_clone():
    side_notes = []
    writes = []
    runtime = fixit_felix_runtime.AutomaticRepairRuntime(
        side_notes=side_notes,
        write_clone=lambda data_hex, save_suffix: writes.append((data_hex, save_suffix)),
    )
    repair = SimpleNamespace(
        data=b"fixed",
        strategy="unit-test-repair",
    )

    result = fixit_felix_runtime.apply_repair(runtime, repair)

    assert result is True
    assert side_notes == ["-FixItFelix:unit-test-repair."]
    assert writes == [("6669786564", "-unit-test-repair.")]


def test_apply_gama_zero_discards_false_positive_and_returns_legacy_target():
    finding = "GetInfo_Error_0:gAMA Chunk of 0 is Useless"
    pandora_box = {finding: {"gAMA_Tool_0": "sample.png"}}
    side_notes = []
    candy_calls = []
    target = object()
    runtime = fixit_felix_runtime.GamaZeroRuntime(
        candy=lambda *args: candy_calls.append(args),
        pandora_box=pandora_box,
        side_notes=side_notes,
        return_value=target,
    )

    result = fixit_felix_runtime.apply_gama_zero(
        runtime,
        fixit_felix.gama_zero_decision(finding),
    )

    assert result == (True, target)
    assert candy_calls == [
        ("Cowsay", "Bah that's just a warning who cares ?! !", "good")
    ]
    assert pandora_box == {}
    assert side_notes == [
        "-Found False-Positive :[Error:-GetInfo_Error_0:gAMA Chunk of 0 is Useless]."
    ]


def test_apply_gama_zero_rejects_unknown_action():
    runtime = fixit_felix_runtime.GamaZeroRuntime(
        candy=lambda *args: None,
        pandora_box={},
        side_notes=[],
        return_value=object(),
    )

    try:
        fixit_felix_runtime.apply_gama_zero(
            runtime,
            SimpleNamespace(action="unknown"),
        )
    except ValueError as exc:
        assert str(exc) == "Unknown FixItFelix gAMA action: unknown"
    else:
        raise AssertionError("Expected ValueError for unknown gAMA action")


def test_apply_critical_miss_emits_and_pauses_on_debug_action():
    emitted = []
    pauses = []
    runtime = fixit_felix_runtime.CriticalMissRuntime(
        emit=emitted.append,
        pause=pauses.append,
    )
    finding = "CheckChunkOrder_Error_0:Critical"

    result = fixit_felix_runtime.apply_critical_miss(
        runtime,
        fixit_felix.critical_miss_decision(
            finding,
            debug=True,
            pause_debug=True,
        ),
    )

    assert result == (False, None)
    assert emitted == ["\n-\033[1;31;49mCriticalMiss\033[m: %s" % finding]
    assert pauses == ["Pause:Debug"]


def test_apply_critical_miss_continue_does_not_pause():
    emitted = []
    pauses = []
    runtime = fixit_felix_runtime.CriticalMissRuntime(
        emit=emitted.append,
        pause=pauses.append,
    )
    finding = "CheckChunkOrder_Error_0:Critical"

    result = fixit_felix_runtime.apply_critical_miss(
        runtime,
        fixit_felix.critical_miss_decision(
            finding,
            debug=True,
            pause_debug=False,
        ),
    )

    assert result == (False, None)
    assert emitted == ["\n-\033[1;31;49mCriticalMiss\033[m: %s" % finding]
    assert pauses == []


def test_apply_critical_miss_rejects_unknown_action():
    runtime = fixit_felix_runtime.CriticalMissRuntime(
        emit=lambda message: None,
        pause=lambda message: None,
    )

    try:
        fixit_felix_runtime.apply_critical_miss(
            runtime,
            SimpleNamespace(action="unknown", finding="Critical"),
        )
    except ValueError as exc:
        assert str(exc) == "Unknown FixItFelix critical-miss action: unknown"
    else:
        raise AssertionError("Expected ValueError for unknown critical-miss action")


def wrong_crc_tools():
    return SimpleNamespace(
        replacement_crc="fixed-crc-data",
        start=12,
        end=20,
        chunk=b"IDAT",
        offset="0x2a",
        old_crc="old-crc",
    )


def wrong_crc_runtime(
    calls,
    *,
    answers=(),
    pandora_box=None,
    cl_offset=33,
    crc_offset=101,
    original_chunk_length_hex="0d",
    debug=False,
    pause_debug=False,
):
    answer_iter = iter(answers)

    def record(name, result=None):
        def callback(*args, **kwargs):
            calls.append((name, args, kwargs))
            return result

        return callback

    def question(*args, **kwargs):
        calls.append(("question", args, kwargs))
        return next(answer_iter)

    return fixit_felix_runtime.WrongCrcRuntime(
        emit=record("emit"),
        candy=record("candy"),
        question=question,
        save_clone=record("save_clone", "saved"),
        chunk_story=record("chunk_story"),
        set_skip_bad_crc=record("set_skip_bad_crc"),
        set_old_bad_crc=record("set_old_bad_crc"),
        pandora_box=pandora_box if pandora_box is not None else {},
        cl_offset=cl_offset,
        crc_offset=crc_offset,
        original_chunk_length_hex=original_chunk_length_hex,
        debug=debug,
        pause_debug=pause_debug,
    )


def test_apply_wrong_crc_easy_answer_saves_clone():
    calls = []
    finding = "Checksum_Error_0:Wrong Crc b'IDAT'"
    chkd = "IDAT_Tool_"
    runtime = wrong_crc_runtime(
        calls,
        answers=(True,),
        pandora_box={finding: {chkd + "0": "fixed-crc-data"}},
    )

    result = fixit_felix_runtime.apply_wrong_crc(
        runtime,
        fixit_felix.WrongCrcDecision("ask_easy_crc_fix", finding, 0),
        chkd,
        wrong_crc_tools(),
    )

    assert result == (True, "saved")
    assert calls[-1] == (
        "save_clone",
        (
            "fixed-crc-data",
            12,
            20,
            "-Found Chunk[b'IDAT'] has Wrong Crc at offset: 0x2a\n"
            "-Replaced with: fixed-crc-data old value was: old-crc",
        ),
        {},
    )


def test_apply_wrong_crc_easy_decline_then_final_decline_keeps_skip_none_and_saves():
    calls = []
    finding = "Checksum_Error_0:Wrong Crc b'IDAT'"
    chkd = "IDAT_Tool_"
    runtime = wrong_crc_runtime(
        calls,
        answers=(False, False),
        pandora_box={finding: {chkd + "0": "fixed-crc-data"}},
    )

    result = fixit_felix_runtime.apply_wrong_crc(
        runtime,
        fixit_felix.WrongCrcDecision("ask_easy_crc_fix", finding, 0),
        chkd,
        wrong_crc_tools(),
    )

    assert result == (True, "saved")
    assert ("set_skip_bad_crc", (None,), {}) in calls
    assert calls[-1][0] == "save_clone"


def test_apply_wrong_crc_other_errors_defers_to_chunk_story():
    calls = []
    finding = "Checksum_Error_0:Wrong Crc b'IDAT'"
    chkd = "IDAT_Tool_"
    runtime = wrong_crc_runtime(
        calls,
        answers=(True,),
        pandora_box={finding: {chkd + "0": "fixed-crc-data"}},
    )

    result = fixit_felix_runtime.apply_wrong_crc(
        runtime,
        fixit_felix.WrongCrcDecision("ask_other_errors_first", finding, 2),
        chkd,
        wrong_crc_tools(),
    )

    assert result == (False, None)
    assert calls[-3:] == [
        ("chunk_story", ("add", b"IDAT", 33, 109, 13), {}),
        ("set_old_bad_crc", ("old-crc",), {}),
        ("set_skip_bad_crc", (True,), {}),
    ]


def test_apply_wrong_crc_already_in_cornucopia_uses_debug_emit_without_tools():
    calls = []
    finding = "Checksum_Error_0:Wrong Crc b'IDAT'"
    runtime = wrong_crc_runtime(calls, debug=True, pause_debug=True)

    result = fixit_felix_runtime.apply_wrong_crc(
        runtime,
        fixit_felix.WrongCrcDecision("already_in_cornucopia", finding, 0),
        "IDAT_Tool_",
        None,
    )

    assert result == (False, None)
    assert calls == [
        ("emit", ("\n-\033[1;31;49mCriticalHit\033[m: %s" % finding,), {}),
        ("emit", ("-Cornucopia is True",), {}),
    ]


def test_apply_wrong_crc_rejects_missing_tools_for_action():
    runtime = wrong_crc_runtime([])

    try:
        fixit_felix_runtime.apply_wrong_crc(
            runtime,
            fixit_felix.WrongCrcDecision("ask_easy_crc_fix", "finding", 0),
            "IDAT_Tool_",
            None,
        )
    except ValueError as exc:
        assert str(exc) == "FixItFelix wrong-CRC action needs CRC tools: ask_easy_crc_fix"
    else:
        raise AssertionError("Expected ValueError for missing wrong-CRC tools")


def test_apply_wrong_crc_rejects_unknown_action():
    runtime = wrong_crc_runtime([])

    try:
        fixit_felix_runtime.apply_wrong_crc(
            runtime,
            SimpleNamespace(action="unknown", finding="finding"),
            "IDAT_Tool_",
            wrong_crc_tools(),
        )
    except ValueError as exc:
        assert str(exc) == "Unknown FixItFelix wrong-CRC action: unknown"
    else:
        raise AssertionError("Expected ValueError for unknown wrong-CRC action")


def libpng_runtime(
    calls,
    *,
    answer=True,
    pandora_box=None,
    cornucopia=None,
    sample="sample.png",
):
    def record(name, result=None):
        def callback(*args, **kwargs):
            calls.append((name, args, kwargs))
            return result

        return callback

    return fixit_felix_runtime.LibpngErrorRuntime(
        emit=record("emit"),
        candy=record("candy", "colored"),
        question=record("question", answer),
        the_end=record("the_end"),
        run_relics=record("run_relics", "relics-result"),
        save_clone=record("save_clone", "saved"),
        groundhog_day=record("groundhog_day", "groundhog-result"),
        set_skip_bad_libpng=record("set_skip_bad_libpng"),
        pandora_box=pandora_box if pandora_box is not None else {},
        cornucopia=cornucopia if cornucopia is not None else {},
        sample=sample,
    )


def test_apply_libpng_error_saves_existing_solution():
    calls = []
    finding = "Libpng_Error_0:libpng error: bad adaptive filter"
    chkd = "LibpngCheck_Tool_"
    runtime = libpng_runtime(
        calls,
        cornucopia={
            finding: {
                chkd + "0": "fixed-data",
                chkd + "1": 12,
                chkd + "2": 20,
                chkd + "3": "legacy save note",
            }
        },
    )

    result = fixit_felix_runtime.apply_libpng_error(
        runtime,
        fixit_felix.LibpngErrorDecision("save_existing_solution", finding),
        chkd,
    )

    assert result == (True, "groundhog-result")
    assert calls == [
        ("emit", ("\n-\033[1;31;49mCriticalHit\033[m: %s" % finding,), {}),
        ("emit", ("\n-\033[1;32;49mSolved\033[m: legacy save note",), {}),
        ("save_clone", ("fixed-data", 12, 20, "legacy save note"), {}),
        ("groundhog_day", ("sample.png",), {}),
    ]


def test_apply_libpng_error_accepts_relics_prompt_and_sets_skip():
    calls = []
    finding = "Libpng_Error_0:libpng error: bad adaptive filter"
    chkd = "LibpngCheck_Tool_"
    pandora_box = {
        finding: {
            chkd + "0": "candidate",
            chkd + "1": 12,
            chkd + "2": 20,
        }
    }
    runtime = libpng_runtime(calls, pandora_box=pandora_box)

    result = fixit_felix_runtime.apply_libpng_error(
        runtime,
        fixit_felix.LibpngErrorDecision("ask_relics", finding),
        chkd,
    )

    assert result == (True, "relics-result")
    assert calls[0] == ("emit", ("\n-\033[1;31;49mCriticalHit\033[m: %s" % finding,), {})
    assert calls[-2:] == [
        ("set_skip_bad_libpng", (True,), {}),
        ("run_relics", (finding,), {}),
    ]
    question_calls = [call for call in calls if call[0] == "question"]
    assert question_calls == [
        (
            "question",
            (),
            {
                "id": finding,
                "idhash": hash("candidate1220"),
            },
        )
    ]


def test_apply_libpng_error_declines_relics_prompt_and_ends():
    calls = []
    finding = "Libpng_Error_0:libpng error: bad adaptive filter"
    runtime = libpng_runtime(calls, answer=False)

    result = fixit_felix_runtime.apply_libpng_error(
        runtime,
        fixit_felix.LibpngErrorDecision("ask_relics", finding),
        "LibpngCheck_Tool_",
    )

    assert result is None
    assert calls[-2:] == [
        ("candy", ("Cowsay", "See You Space Cowboy....", "good"), {}),
        ("the_end", (), {}),
    ]


def test_apply_libpng_error_not_enough_image_data_ends_after_todo():
    calls = []
    finding = "Libpng_Error_0:libpng error: Not enough image data"
    runtime = libpng_runtime(calls)

    result = fixit_felix_runtime.apply_libpng_error(
        runtime,
        fixit_felix.LibpngErrorDecision("not_enough_image_data", finding),
        "LibpngCheck_Tool_",
    )

    assert result is None
    assert calls[-2:] == [
        ("emit", ("colored",), {}),
        ("the_end", (), {}),
    ]


def test_apply_libpng_error_skip_only_reports_critical_hit():
    calls = []
    finding = "Libpng_Error_0:libpng error: bad adaptive filter"
    runtime = libpng_runtime(calls)

    result = fixit_felix_runtime.apply_libpng_error(
        runtime,
        fixit_felix.LibpngErrorDecision("skip", finding),
        "LibpngCheck_Tool_",
    )

    assert result == (False, None)
    assert calls == [
        ("emit", ("\n-\033[1;31;49mCriticalHit\033[m: %s" % finding,), {})
    ]


def test_apply_libpng_error_rejects_unknown_action():
    runtime = libpng_runtime([])

    try:
        fixit_felix_runtime.apply_libpng_error(
            runtime,
            SimpleNamespace(action="unknown", finding="Libpng_Error_0:bad"),
            "LibpngCheck_Tool_",
        )
    except ValueError as exc:
        assert str(exc) == "Unknown FixItFelix libpng action: unknown"
    else:
        raise AssertionError("Expected ValueError for unknown libpng action")


def recording_callbacks(calls):
    return fixit_felix_runtime.LegacyFixItFelixHandlers(
        wrong_crc=lambda finding, chkd, pandora_len: calls.append(
            ("wrong_crc", finding, chkd, pandora_len)
        )
        or (True, "wrong-crc"),
        libpng_error=lambda finding, chkd: calls.append(
            ("libpng_error", finding, chkd)
        )
        or (True, "libpng"),
        wrong_chunk_name=lambda finding, chkd: calls.append(
            ("wrong_chunk_name", finding, chkd)
        )
        or (True, "wrong-name"),
        no_next_chunk=lambda finding, chkd, chunk: calls.append(
            ("no_next_chunk", finding, chkd, chunk)
        )
        or (True, "no-next"),
        gama_zero=lambda finding: calls.append(("gama_zero", finding))
        or (True, "gama"),
        critical_miss=lambda finding: calls.append(("critical_miss", finding))
        or (False, None),
    )


def test_finding_handlers_route_legacy_callback_arguments():
    cases = [
        ("wrong_crc", ("wrong_crc", "finding", "IDAT_Tool_", 2), (True, "wrong-crc")),
        ("libpng_error", ("libpng_error", "finding", "IDAT_Tool_"), (True, "libpng")),
        ("wrong_chunk_name", ("wrong_chunk_name", "finding", "IDAT_Tool_"), (True, "wrong-name")),
        ("no_next_chunk", ("no_next_chunk", "finding", "IDAT_Tool_", b"IDAT"), (True, "no-next")),
        ("gama_zero", ("gama_zero", "finding"), (True, "gama")),
        ("critical_miss", ("critical_miss", "finding"), (False, None)),
    ]

    for handler_name, expected_call, expected_result in cases:
        calls = []
        handlers = fixit_felix_runtime.finding_handlers(recording_callbacks(calls))
        work_item = fixit_felix.FixItFelixWorkItem("finding", handler_name, "finding")

        result = handlers[handler_name](work_item, "IDAT_Tool_", 2, b"IDAT")

        assert result == expected_result
        assert calls == [expected_call]


def test_apply_finding_work_item_dispatches_through_fixit_felix_dispatch():
    calls = []
    work_item = fixit_felix.FixItFelixWorkItem("finding", "wrong_crc", "finding")

    result = fixit_felix_runtime.apply_finding_work_item(
        recording_callbacks(calls),
        work_item,
        "IDAT_Tool_",
        3,
        b"IDAT",
    )

    assert result == (True, "wrong-crc")
    assert calls == [("wrong_crc", "finding", "IDAT_Tool_", 3)]


def test_runtime_uses_automatic_repair_and_legacy_callbacks():
    calls = []
    runtime = fixit_felix_runtime.runtime(
        try_automatic_repair=lambda handler: calls.append(("auto", handler)) or None,
        callbacks=recording_callbacks(calls),
    )

    result = fixit_felix.run_repair_work_items(
        runtime,
        (
            fixit_felix.FixItFelixWorkItem("automatic_repair", "plte_cleanup"),
            fixit_felix.FixItFelixWorkItem("finding", "no_next_chunk", "finding"),
        ),
        chkd="IDAT_Tool_",
        pandora_box_len=4,
        chunk=b"IDAT",
    )

    assert result == fixit_felix.FixItFelixRunResult(True, "no-next")
    assert calls == [
        ("auto", "plte_cleanup"),
        ("no_next_chunk", "finding", "IDAT_Tool_", b"IDAT"),
    ]


def main():
    checks = [
        ("Apply repair records note and writes clone", test_apply_repair_records_note_and_writes_clone),
        ("Apply gAMA zero discards false positive", test_apply_gama_zero_discards_false_positive_and_returns_legacy_target),
        ("Apply gAMA zero rejects unknown action", test_apply_gama_zero_rejects_unknown_action),
        ("Apply critical miss emits and pauses", test_apply_critical_miss_emits_and_pauses_on_debug_action),
        ("Apply critical miss continue skips pause", test_apply_critical_miss_continue_does_not_pause),
        ("Apply critical miss rejects unknown action", test_apply_critical_miss_rejects_unknown_action),
        ("Apply wrong CRC easy answer saves clone", test_apply_wrong_crc_easy_answer_saves_clone),
        (
            "Apply wrong CRC easy decline keeps skip none",
            test_apply_wrong_crc_easy_decline_then_final_decline_keeps_skip_none_and_saves,
        ),
        ("Apply wrong CRC other errors defers", test_apply_wrong_crc_other_errors_defers_to_chunk_story),
        (
            "Apply wrong CRC Cornucopia debug path",
            test_apply_wrong_crc_already_in_cornucopia_uses_debug_emit_without_tools,
        ),
        ("Apply wrong CRC rejects missing tools", test_apply_wrong_crc_rejects_missing_tools_for_action),
        ("Apply wrong CRC rejects unknown action", test_apply_wrong_crc_rejects_unknown_action),
        ("Apply libpng saves existing solution", test_apply_libpng_error_saves_existing_solution),
        ("Apply libpng accepts Relics prompt", test_apply_libpng_error_accepts_relics_prompt_and_sets_skip),
        ("Apply libpng declines Relics prompt", test_apply_libpng_error_declines_relics_prompt_and_ends),
        ("Apply libpng not enough image data ends", test_apply_libpng_error_not_enough_image_data_ends_after_todo),
        ("Apply libpng skip reports critical", test_apply_libpng_error_skip_only_reports_critical_hit),
        ("Apply libpng rejects unknown action", test_apply_libpng_error_rejects_unknown_action),
        ("Finding handlers route callback arguments", test_finding_handlers_route_legacy_callback_arguments),
        ("Apply finding work item dispatches", test_apply_finding_work_item_dispatches_through_fixit_felix_dispatch),
        ("Runtime uses automatic repair and callbacks", test_runtime_uses_automatic_repair_and_legacy_callbacks),
    ]

    print("Running FixItFelix runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"FixItFelix runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
