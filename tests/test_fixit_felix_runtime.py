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


def critical_miss_runtime(emitted, pauses, *, candy_calls=None):
    if candy_calls is None:
        candy_calls = []
    state = {"explained": False, "seen": set()}

    def remember_finding(finding):
        text = str(finding)
        if text in state["seen"]:
            return False
        state["seen"].add(text)
        return True

    return fixit_felix_runtime.CriticalMissRuntime(
        emit=emitted.append,
        candy=lambda *args: candy_calls.append(args),
        pause=pauses.append,
        idat_crc_patch_failed=lambda: False,
        idat_crc_patch_failed_finding=lambda: None,
        idat_crc_defer_explained=lambda: state["explained"],
        set_idat_crc_defer_explained=lambda value: state.__setitem__("explained", value),
        remember_deferred_idat_crc_finding=remember_finding,
    )


def test_apply_critical_miss_emits_and_pauses_on_debug_action():
    emitted = []
    pauses = []
    runtime = critical_miss_runtime(emitted, pauses)
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
    runtime = critical_miss_runtime(emitted, pauses)
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
    runtime = critical_miss_runtime([], [])

    try:
        fixit_felix_runtime.apply_critical_miss(
            runtime,
            SimpleNamespace(action="unknown", finding="Critical"),
        )
    except ValueError as exc:
        assert str(exc) == "Unknown FixItFelix critical-miss action: unknown"
    else:
        raise AssertionError("Expected ValueError for unknown critical-miss action")


def wrong_crc_tools(*, chunk=b"IDAT", offset="0x2a", start=12, end=20):
    return SimpleNamespace(
        replacement_crc="fixed-crc-data",
        start=start,
        end=end,
        chunk=chunk,
        offset=offset,
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
    data_hex="00112233445566778899",
    last_question_status=None,
    deferred_routes=None,
):
    answer_iter = iter(answers)
    if deferred_routes is None:
        deferred_routes = set()

    def record(name, result=None):
        def callback(*args, **kwargs):
            calls.append((name, args, kwargs))
            return result

        return callback

    def question(*args, **kwargs):
        calls.append(("question", args, kwargs))
        return next(answer_iter)

    def remember_deferred_route(finding, tools):
        calls.append(("remember_deferred_idat_crc_route", (finding, tools), {}))
        deferred_routes.add(fixit_felix_runtime.deferred_idat_crc_route_key(finding, tools))

    def is_deferred_route(finding, tools):
        calls.append(("is_deferred_idat_crc_route", (finding, tools), {}))
        return fixit_felix_runtime.deferred_idat_crc_route_key(finding, tools) in deferred_routes

    return fixit_felix_runtime.WrongCrcRuntime(
        emit=record("emit"),
        candy=record("candy"),
        question=question,
        save_clone=record("save_clone", "saved"),
        chunk_story=record("chunk_story"),
        set_skip_bad_crc=record("set_skip_bad_crc"),
        set_old_bad_crc=record("set_old_bad_crc"),
        pandora_box=pandora_box if pandora_box is not None else {},
        data_hex=data_hex,
        cl_offset=cl_offset,
        crc_offset=crc_offset,
        original_chunk_length_hex=original_chunk_length_hex,
        last_question_status=lambda: last_question_status,
        set_idat_crc_patch_failed=record("set_idat_crc_patch_failed"),
        set_idat_crc_patch_failed_finding=record("set_idat_crc_patch_failed_finding"),
        remember_deferred_idat_crc_route=remember_deferred_route,
        is_deferred_idat_crc_route=is_deferred_route,
        debug=debug,
        pause_debug=pause_debug,
    )


def test_apply_wrong_crc_easy_answer_saves_clone():
    calls = []
    finding = "Checksum_Error_0:Wrong Crc b'gAMA'"
    chkd = "gAMA_Tool_"
    runtime = wrong_crc_runtime(
        calls,
        answers=(True,),
        pandora_box={finding: {chkd + "0": "fixed-crc-data"}},
    )

    result = fixit_felix_runtime.apply_wrong_crc(
        runtime,
        fixit_felix.WrongCrcDecision("ask_easy_crc_fix", finding, 0),
        chkd,
        wrong_crc_tools(chunk=b"gAMA"),
    )

    assert result == (True, "saved")
    assert calls[-1] == (
        "save_clone",
        (
            "fixed-crc-data",
            12,
            20,
            "-Found Chunk[b'gAMA'] has Wrong Crc at offset: 0x2a\n"
            "-Replaced with: fixed-crc-data old value was: old-crc",
        ),
        {},
    )


def test_apply_wrong_crc_easy_decline_then_final_decline_keeps_skip_none_and_saves():
    calls = []
    finding = "Checksum_Error_0:Wrong Crc b'gAMA'"
    chkd = "gAMA_Tool_"
    runtime = wrong_crc_runtime(
        calls,
        answers=(False, False),
        pandora_box={finding: {chkd + "0": "fixed-crc-data"}},
    )

    result = fixit_felix_runtime.apply_wrong_crc(
        runtime,
        fixit_felix.WrongCrcDecision("ask_easy_crc_fix", finding, 0),
        chkd,
        wrong_crc_tools(chunk=b"gAMA"),
    )

    assert result == (True, "saved")
    assert ("set_skip_bad_crc", (None,), {}) in calls
    assert calls[-1][0] == "save_clone"


def test_deferred_idat_crc_route_key_ignores_error_counter():
    tools = wrong_crc_tools(chunk=b"IDAT", offset=182, start=12, end=20)

    first = fixit_felix_runtime.deferred_idat_crc_route_key(
        "Checksum_Error_0:Wrong Crc b'IDAT'",
        tools,
    )
    second = fixit_felix_runtime.deferred_idat_crc_route_key(
        "Checksum_Error_1:Wrong Crc b'IDAT'",
        tools,
    )
    other_offset = fixit_felix_runtime.deferred_idat_crc_route_key(
        "Checksum_Error_1:Wrong Crc b'IDAT'",
        wrong_crc_tools(chunk=b"IDAT", offset=184, start=12, end=20),
    )

    assert first == second
    assert first != other_offset


def test_apply_wrong_crc_skips_question_for_deferred_idat_route():
    calls = []
    chkd = "IDAT_Tool_"
    tools = wrong_crc_tools(chunk=b"IDAT", offset=182, start=12, end=20)
    routes = {
        fixit_felix_runtime.deferred_idat_crc_route_key(
            "Checksum_Error_0:Wrong Crc b'IDAT'",
            tools,
        )
    }
    runtime = wrong_crc_runtime(
        calls,
        answers=(True,),
        pandora_box={"Checksum_Error_1:Wrong Crc b'IDAT'": {chkd + "0": "fixed-crc-data"}},
        deferred_routes=routes,
    )

    result = fixit_felix_runtime.apply_wrong_crc(
        runtime,
        fixit_felix.WrongCrcDecision("ask_easy_crc_fix", "Checksum_Error_1:Wrong Crc b'IDAT'", 0),
        chkd,
        tools,
    )

    assert result == (False, None)
    assert not any(call[0] == "question" for call in calls)
    assert (
        "candy",
        (
            "Cowsay",
            "Oh, I know that one already... I hoped it would have gone away by itself. Anyway, let's keep going.",
            "com",
        ),
        {},
    ) in calls
    assert calls[-3:] == [
        ("chunk_story", ("add", b"IDAT", 33, 109, 13), {}),
        ("set_old_bad_crc", ("old-crc",), {}),
        ("set_skip_bad_crc", (True,), {}),
    ]


def test_apply_wrong_crc_records_failed_idat_crc_route_when_patch_still_breaks():
    calls = []
    finding = "Checksum_Error_0:Wrong Crc b'IDAT'"
    chkd = "IDAT_Tool_"
    tools = wrong_crc_tools(chunk=b"IDAT", offset=182, start=12, end=20)
    runtime = wrong_crc_runtime(
        calls,
        answers=(True,),
        pandora_box={finding: {chkd + "0": "fixed-crc-data"}},
        data_hex="00112233445566778899",
    )

    result = fixit_felix_runtime.apply_wrong_crc(
        runtime,
        fixit_felix.WrongCrcDecision("ask_easy_crc_fix", finding, 0),
        chkd,
        tools,
    )

    assert result == (False, None)
    assert any(call[0] == "question" for call in calls)
    assert ("set_idat_crc_patch_failed", (True,), {}) in calls
    assert ("set_idat_crc_patch_failed_finding", (finding,), {}) in calls
    assert any(call[0] == "remember_deferred_idat_crc_route" for call in calls)


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


def wrong_chunk_name_tools():
    return SimpleNamespace(
        chunk_type=b"zzzz",
        chunk_length="13",
        chunk_type_offset=128,
        previous_chunk=b"IHDR",
    )


def wrong_chunk_name_runtime(
    calls,
    *,
    answers=(),
    bad_ancillary=False,
    pandora_box=None,
    cornucopia=None,
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

    return fixit_felix_runtime.WrongChunkNameRuntime(
        emit=record("emit"),
        candy=record("candy"),
        question=question,
        ancillary=record("ancillary"),
        nearby_chunk=record("nearby_chunk", "nearby-result"),
        brute_chunk=record("brute_chunk", "brute-result"),
        save_clone=record("save_clone", "saved"),
        set_skip_bad_next_name=record("set_skip_bad_next_name"),
        set_skip_bad_current_name=record("set_skip_bad_current_name"),
        bad_ancillary=lambda: bad_ancillary,
        pandora_box=pandora_box if pandora_box is not None else {},
        cornucopia=cornucopia if cornucopia is not None else {},
    )


def test_apply_wrong_chunk_name_length_probe_accepts_nearby_chunk():
    calls = []
    finding = "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42 and length is not the same than before."
    chkd = "zzzz_Tool_"
    runtime = wrong_chunk_name_runtime(
        calls,
        answers=(True,),
        bad_ancillary=True,
        pandora_box={finding: {chkd + "0": b"zzzz"}},
    )

    result = fixit_felix_runtime.apply_wrong_chunk_name(
        runtime,
        fixit_felix.WrongChunkNameDecision("ask_length_probe", finding, True),
        chkd,
        wrong_chunk_name_tools(),
    )

    assert result == (True, "nearby-result")
    assert ("ancillary", (b"zzzz",), {}) in calls
    assert calls[-1] == (
        "nearby_chunk",
        (b"zzzz", "13", 128, False, finding),
        {},
    )


def test_apply_wrong_chunk_name_length_probe_decline_then_bruteforce_decline_sets_skips():
    calls = []
    finding = "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42 and length is not the same than before."
    chkd = "zzzz_Tool_"
    runtime = wrong_chunk_name_runtime(
        calls,
        answers=(False, False),
        pandora_box={finding: {chkd + "0": b"zzzz"}},
    )

    result = fixit_felix_runtime.apply_wrong_chunk_name(
        runtime,
        fixit_felix.WrongChunkNameDecision("ask_length_probe", finding, True),
        chkd,
        wrong_chunk_name_tools(),
    )

    assert result == (False, None)
    assert ("set_skip_bad_next_name", (True,), {}) in calls
    assert calls[-1] == ("set_skip_bad_current_name", (True,), {})


def test_apply_wrong_chunk_name_bruteforce_accepts_brute_chunk():
    calls = []
    finding = "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42"
    chkd = "zzzz_Tool_"
    runtime = wrong_chunk_name_runtime(
        calls,
        answers=(True,),
        pandora_box={finding: {chkd + "0": b"zzzz"}},
    )

    result = fixit_felix_runtime.apply_wrong_chunk_name(
        runtime,
        fixit_felix.WrongChunkNameDecision("ask_bruteforce", finding, True),
        chkd,
        wrong_chunk_name_tools(),
    )

    assert result == (True, "brute-result")
    assert calls[-1] == (
        "brute_chunk",
        (b"zzzz", b"IHDR", "13", finding),
        {},
    )


def test_apply_wrong_chunk_name_saves_existing_solution():
    calls = []
    finding = "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42"
    chkd = "zzzz_Tool_"
    runtime = wrong_chunk_name_runtime(
        calls,
        cornucopia={
            finding: {
                chkd + "0": "fixed-data",
                chkd + "1": 12,
                chkd + "2": 20,
                chkd + "3": "legacy note",
                chkd + "4": "solved label",
            }
        },
    )

    result = fixit_felix_runtime.apply_wrong_chunk_name(
        runtime,
        fixit_felix.WrongChunkNameDecision("save_existing_solution", finding, True),
        chkd,
        None,
    )

    assert result == (True, "saved")
    assert calls == [
        ("emit", ("\n-\033[1;32;49mSolved\033[m: solved label",), {}),
        ("save_clone", ("fixed-data", 12, 20, "legacy note"), {}),
    ]


def test_apply_wrong_chunk_name_rejects_missing_tools_for_action():
    runtime = wrong_chunk_name_runtime([])

    try:
        fixit_felix_runtime.apply_wrong_chunk_name(
            runtime,
            fixit_felix.WrongChunkNameDecision("ask_bruteforce", "finding", True),
            "zzzz_Tool_",
            None,
        )
    except ValueError as exc:
        assert str(exc) == "FixItFelix wrong-chunk-name action needs chunk tools: ask_bruteforce"
    else:
        raise AssertionError("Expected ValueError for missing wrong-chunk-name tools")


def test_apply_wrong_chunk_name_rejects_unknown_action():
    runtime = wrong_chunk_name_runtime([])

    try:
        fixit_felix_runtime.apply_wrong_chunk_name(
            runtime,
            SimpleNamespace(action="unknown", finding="finding", bad_crc=True),
            "zzzz_Tool_",
            wrong_chunk_name_tools(),
        )
    except ValueError as exc:
        assert str(exc) == "Unknown FixItFelix wrong-chunk-name action: unknown"
    else:
        raise AssertionError("Expected ValueError for unknown wrong-chunk-name action")


def no_next_tools(chunk_type=b"IDAT", chunk_length="12", previous_chunk=b"IDAT"):
    return SimpleNamespace(
        chunk_type=chunk_type,
        chunk_length=chunk_length,
        previous_chunk=previous_chunk,
    )


def no_next_runtime(
    calls,
    *,
    pandora_box=None,
    data_hex="",
    crc_offset=0,
    bad_missplaced=False,
    eof=False,
):
    state = {"eof": eof}
    side_notes = []

    def record(name, result=None):
        def callback(*args, **kwargs):
            calls.append((name, args, kwargs))
            return result

        return callback

    def set_eof(value):
        calls.append(("set_eof", (value,), {}))
        state["eof"] = value

    return (
        fixit_felix_runtime.NoNextChunkRuntime(
            emit=record("emit"),
            candy=record("candy", "colored"),
            question=record("question", True),
            side_notes=side_notes,
            pandora_box=pandora_box if pandora_box is not None else {},
            sample="sample.png",
            data_hex=data_hex,
            cl_offset=33,
            crc_offset=crc_offset,
            original_chunk_length_hex="0d",
            raw_crc="raw-crc",
            debug=False,
            pause_debug=False,
            pause_error=False,
            bad_missplaced=bad_missplaced,
            set_skip_bad_no_next_chunk=record("set_skip_bad_no_next_chunk"),
            set_eof=set_eof,
            eof=lambda: state["eof"],
            chunk_story=record("chunk_story"),
            check_chunk_order=record("check_chunk_order"),
            libpng_check=record("libpng_check", "libpng-result"),
            the_good_place=record("the_good_place", "good-place-result"),
            write_clone=record("write_clone", "write-result"),
            the_end=record("the_end"),
            pause=record("pause"),
            debug_print=record("debug_print"),
            dummy_chunk=record("dummy_chunk", "dummy-result"),
            nearby_chunk=record("nearby_chunk", "nearby-result"),
        ),
        side_notes,
        state,
    )


def test_apply_no_next_false_positive_iend_runs_libpng_after_marking_eof():
    calls = []
    finding = "CheckLength_Error_0:-No NextChunk"
    pandora_box = {finding: {"IEND_Tool_0": b"IEND"}}
    runtime, side_notes, state = no_next_runtime(
        calls,
        pandora_box=pandora_box,
        data_hex="aabbccdd" + fixit_felix.GOOD_IEND_HEX,
    )

    result = fixit_felix_runtime.apply_no_next_chunk(
        runtime,
        fixit_felix.NoNextChunkDecision("false_positive_iend", b"IEND", b"IEND", "0"),
        finding,
        "IEND_Tool_",
        no_next_tools(chunk_type=b"IEND", chunk_length="0"),
    )

    assert result == (True, "libpng-result")
    assert pandora_box == {}
    assert state["eof"] is True
    assert side_notes == [
        "-Found False-Positive :[Error:-No NextChunk].",
        "-Reached the end of file.",
    ]
    assert ("chunk_story", ("add", b"IEND", 33, 8, 13), {}) in calls
    assert calls[-1] == ("libpng_check", ("sample.png",), {})


def test_apply_no_next_false_positive_iend_writes_clean_cut():
    calls = []
    finding = "CheckLength_Error_0:-No NextChunk"
    data_hex = "aabbccdd" + fixit_felix.GOOD_IEND_HEX + "ffee"
    runtime, side_notes, _state = no_next_runtime(
        calls,
        pandora_box={finding: {"IEND_Tool_0": b"IEND"}},
        data_hex=data_hex,
    )

    result = fixit_felix_runtime.apply_no_next_chunk(
        runtime,
        fixit_felix.NoNextChunkDecision("false_positive_iend", b"IEND", b"IEND", "0"),
        finding,
        "IEND_Tool_",
        no_next_tools(chunk_type=b"IEND", chunk_length="0"),
    )

    assert result == (True, "write-result")
    assert side_notes == [
        "-Found False-Positive :[Error:-No NextChunk].",
        "-FixitFelix:Removing extra bytes after IEND chunk.",
    ]
    assert calls[-1] == (
        "write_clone",
        (bytes.fromhex("aabbccdd" + fixit_felix.GOOD_IEND_HEX), "-Saved"),
        {},
    )


def test_apply_no_next_false_positive_iend_falls_back_when_missplaced_tools_are_incomplete():
    calls = []
    runtime, side_notes, state = no_next_runtime(
        calls,
        bad_missplaced=True,
        pandora_box={"ChunkOrder_Error_0:-Missplaced": {"Only_One_Tool": b"gAMA"}},
    )

    result = fixit_felix_runtime.apply_no_next_false_positive_iend(
        runtime,
        fixit_felix.NoNextFalsePositiveIendDecision("the_good_place"),
    )

    assert result == (True, "libpng-result")
    assert state["eof"] is True
    assert side_notes == ["-Reached the end of file."]
    assert all(call[0] != "the_good_place" for call in calls)
    assert calls[-1] == ("libpng_check", ("sample.png",), {})


def test_apply_no_next_wrong_iend_length_records_note_and_ends():
    calls = []
    runtime, side_notes, _state = no_next_runtime(calls)

    result = fixit_felix_runtime.apply_no_next_chunk(
        runtime,
        fixit_felix.NoNextChunkDecision("wrong_iend_length", b"IDAT", b"IEND", "1"),
        "CheckLength_Error_0:-No NextChunk",
        "IEND_Tool_",
        no_next_tools(chunk_type=b"IEND", chunk_length="1"),
    )

    assert result == (False, None)
    assert side_notes == ["-Wrong length for IEND"]
    assert calls[-1] == ("the_end", (), {})


def test_apply_no_next_append_missing_iend_uses_dummy_at_crc_tail():
    calls = []
    finding = "CheckLength_Error_0:-No NextChunk"
    runtime, side_notes, _state = no_next_runtime(calls, data_hex="aabbccddff")

    result = fixit_felix_runtime.apply_no_next_chunk(
        runtime,
        fixit_felix.NoNextChunkDecision("append_missing_iend", b"IDAT", b"IDAT", "12"),
        finding,
        "IDAT_Tool_",
        no_next_tools(),
    )

    assert result == (True, "dummy-result")
    assert side_notes == ["-Extra bits detected:ff"]
    assert calls[-1] == ("dummy_chunk", (b"IEND", 8, 8, 8, finding), {})


def test_apply_no_next_ask_length_probe_routes_to_nearby_chunk():
    calls = []
    finding = "CheckLength_Error_0:-No NextChunk"
    runtime, side_notes, _state = no_next_runtime(
        calls,
        pandora_box={finding: {"IDAT_Tool_0": b"IDAT"}},
    )

    result = fixit_felix_runtime.apply_no_next_chunk(
        runtime,
        fixit_felix.NoNextChunkDecision("ask_length_probe", b"IDAT", b"IDAT", "12"),
        finding,
        "IDAT_Tool_",
        no_next_tools(),
    )

    assert result == (True, "nearby-result")
    assert side_notes == ["-End of File Reached but IEND Chunk is missing"]
    assert calls[-1] == ("nearby_chunk", (b"IDAT", "12", b"IDAT", False, finding), {})


def test_apply_no_next_chunk_rejects_unknown_action():
    runtime, _side_notes, _state = no_next_runtime([])

    try:
        fixit_felix_runtime.apply_no_next_chunk(
            runtime,
            SimpleNamespace(action="unknown"),
            "finding",
            "IDAT_Tool_",
            no_next_tools(),
        )
    except ValueError as exc:
        assert str(exc) == "Unknown FixItFelix no-next-chunk action: unknown"
    else:
        raise AssertionError("Expected ValueError for unknown no-next action")


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


def test_namespace_runtime_builders_preserve_legacy_wiring():
    calls = []
    side_notes = []
    pandora_box = {}
    cornucopia = {}

    def callback(name):
        def inner(*args, **kwargs):
            calls.append((name, args, kwargs))
            return name

        return inner

    namespace = {
        "PRINT": callback("PRINT"),
        "Candy": callback("Candy"),
        "Question": callback("Question"),
        "SaveClone": callback("SaveClone"),
        "ChunkStory": callback("ChunkStory"),
        "FixItFelix_Set_Skip_Bad_Crc": callback("set_skip_bad_crc"),
        "FixItFelix_Set_Old_Bad_Crc": callback("set_old_bad_crc"),
        "FixItFelix_Set_Skip_Bad_Libpng": callback("set_skip_bad_libpng"),
        "FixItFelix_Set_Skip_Bad_Next_Name": callback("set_skip_bad_next_name"),
        "FixItFelix_Set_Skip_Bad_Current_Name": callback("set_skip_bad_current_name"),
        "FixItFelix_Set_Skip_Bad_No_Next_Chunk": callback("set_skip_bad_no_next_chunk"),
        "FixItFelix_Set_EOF": callback("set_eof"),
        "Relics": callback("Relics"),
        "GroundhogDay": callback("GroundhogDay"),
        "Ancillary": callback("Ancillary"),
        "NearbyChunk": callback("NearbyChunk"),
        "BruteChunk": callback("BruteChunk"),
        "CheckChunkOrder": callback("CheckChunkOrder"),
        "LibpngCheck": callback("LibpngCheck"),
        "TheGoodPlace": callback("TheGoodPlace"),
        "WriteClone": callback("WriteClone"),
        "TheEnd": callback("TheEnd"),
        "Pause": callback("Pause"),
        "DummyChunk": callback("DummyChunk"),
        "FixItFelix": callback("FixItFelix"),
        "PandoraBox": pandora_box,
        "Cornucopia": cornucopia,
        "SideNotes": side_notes,
        "CLoffI": 12,
        "CrcoffI": 40,
        "Orig_CL": "0000000d",
        "DEBUG": True,
        "PAUSEDEBUG": False,
        "PAUSEERROR": True,
        "Sample": "sample.png",
        "DATAX": "001122",
        "Raw_Crc": "deadbeef",
        "Bad_Missplaced": True,
        "Bad_Ancillary": False,
        "EOF": True,
    }

    wrong_crc = fixit_felix_runtime.build_wrong_crc_runtime_from_namespace(namespace)
    assert wrong_crc.emit is namespace["PRINT"]
    assert wrong_crc.candy is namespace["Candy"]
    assert wrong_crc.question is namespace["Question"]
    assert wrong_crc.save_clone is namespace["SaveClone"]
    assert wrong_crc.chunk_story is namespace["ChunkStory"]
    assert wrong_crc.set_skip_bad_crc is namespace["FixItFelix_Set_Skip_Bad_Crc"]
    assert wrong_crc.set_old_bad_crc is namespace["FixItFelix_Set_Old_Bad_Crc"]
    assert wrong_crc.pandora_box is pandora_box
    assert wrong_crc.cl_offset == 12
    assert wrong_crc.crc_offset == 40
    assert wrong_crc.original_chunk_length_hex == "0000000d"
    assert wrong_crc.debug is True
    assert wrong_crc.pause_debug is False

    libpng = fixit_felix_runtime.build_libpng_error_runtime_from_namespace(namespace)
    assert libpng.emit is namespace["PRINT"]
    assert libpng.candy is namespace["Candy"]
    assert libpng.question is namespace["Question"]
    assert libpng.the_end is namespace["TheEnd"]
    assert libpng.run_relics is namespace["Relics"]
    assert libpng.save_clone is namespace["SaveClone"]
    assert libpng.groundhog_day is namespace["GroundhogDay"]
    assert libpng.set_skip_bad_libpng is namespace["FixItFelix_Set_Skip_Bad_Libpng"]
    assert libpng.pandora_box is pandora_box
    assert libpng.cornucopia is cornucopia
    assert libpng.sample == "sample.png"

    wrong_name = fixit_felix_runtime.build_wrong_chunk_name_runtime_from_namespace(namespace)
    assert wrong_name.emit is namespace["PRINT"]
    assert wrong_name.candy is namespace["Candy"]
    assert wrong_name.question is namespace["Question"]
    assert wrong_name.ancillary is namespace["Ancillary"]
    assert wrong_name.nearby_chunk is namespace["NearbyChunk"]
    assert wrong_name.brute_chunk is namespace["BruteChunk"]
    assert wrong_name.save_clone is namespace["SaveClone"]
    assert wrong_name.set_skip_bad_next_name is namespace["FixItFelix_Set_Skip_Bad_Next_Name"]
    assert wrong_name.set_skip_bad_current_name is namespace["FixItFelix_Set_Skip_Bad_Current_Name"]
    assert wrong_name.bad_ancillary() is False
    namespace["Bad_Ancillary"] = True
    assert wrong_name.bad_ancillary() is True
    assert wrong_name.pandora_box is pandora_box
    assert wrong_name.cornucopia is cornucopia

    no_next = fixit_felix_runtime.build_no_next_chunk_runtime_from_namespace(namespace)
    assert no_next.emit is namespace["PRINT"]
    assert no_next.candy is namespace["Candy"]
    assert no_next.question is namespace["Question"]
    assert no_next.side_notes is side_notes
    assert no_next.pandora_box is pandora_box
    assert no_next.sample == "sample.png"
    assert no_next.data_hex == "001122"
    assert no_next.cl_offset == 12
    assert no_next.crc_offset == 40
    assert no_next.original_chunk_length_hex == "0000000d"
    assert no_next.raw_crc == "deadbeef"
    assert no_next.debug is True
    assert no_next.pause_debug is False
    assert no_next.pause_error is True
    assert no_next.bad_missplaced is True
    assert no_next.set_skip_bad_no_next_chunk is namespace["FixItFelix_Set_Skip_Bad_No_Next_Chunk"]
    assert no_next.set_eof is namespace["FixItFelix_Set_EOF"]
    assert no_next.eof() is True
    namespace["EOF"] = False
    assert no_next.eof() is False
    assert no_next.chunk_story is namespace["ChunkStory"]
    assert no_next.check_chunk_order is namespace["CheckChunkOrder"]
    assert no_next.libpng_check is namespace["LibpngCheck"]
    assert no_next.the_good_place is namespace["TheGoodPlace"]
    assert no_next.write_clone is namespace["WriteClone"]
    assert no_next.the_end is namespace["TheEnd"]
    assert no_next.pause is namespace["Pause"]
    assert no_next.debug_print is print
    assert no_next.dummy_chunk is namespace["DummyChunk"]
    assert no_next.nearby_chunk is namespace["NearbyChunk"]

    gama = fixit_felix_runtime.build_gama_zero_runtime_from_namespace(namespace)
    assert gama.candy is namespace["Candy"]
    assert gama.pandora_box is pandora_box
    assert gama.side_notes is side_notes
    assert gama.return_value is namespace["FixItFelix"]

    critical = fixit_felix_runtime.build_critical_miss_runtime_from_namespace(namespace)
    assert critical.emit is namespace["PRINT"]
    assert critical.pause is namespace["Pause"]

    automatic = fixit_felix_runtime.build_automatic_repair_runtime_from_namespace(namespace)
    assert automatic.side_notes is side_notes
    assert automatic.write_clone is namespace["WriteClone"]


def test_namespace_pipeline_builder_preserves_debug_and_repair_wiring():
    calls = []
    pandora_box = {"finding": {"IDAT_Tool_0": "tool-data"}}
    cornucopia = {}

    def callback(name):
        def inner(*args, **kwargs):
            calls.append((name, args, kwargs))
            return name

        return inner

    namespace = {
        "PRINT": callback("PRINT"),
        "Pause": callback("Pause"),
        "FixItFelix_Try_Automatic_Repair": callback("automatic_repair"),
        "FixItFelix_Wrong_Crc": callback("wrong_crc"),
        "FixItFelix_Libpng_Error": callback("libpng_error"),
        "FixItFelix_Wrong_Chunk_Name": callback("wrong_chunk_name"),
        "FixItFelix_No_NextChunk": callback("no_next_chunk"),
        "FixItFelix_Gama_Zero": callback("gama_zero"),
        "FixItFelix_Critical_Miss": callback("critical_miss"),
        "PandoraBox": pandora_box,
        "Cornucopia": cornucopia,
        "Skip_Bad_Crc": False,
        "Bad_Next_Name": False,
        "DEBUG": True,
        "PAUSEDEBUG": True,
    }
    for name in fixit_felix.DEBUG_FLAG_NAMES:
        namespace.setdefault(name, False)

    handlers = fixit_felix_runtime.build_legacy_fixit_felix_handlers_from_namespace(namespace)
    assert handlers.wrong_crc is namespace["FixItFelix_Wrong_Crc"]
    assert handlers.libpng_error is namespace["FixItFelix_Libpng_Error"]
    assert handlers.wrong_chunk_name is namespace["FixItFelix_Wrong_Chunk_Name"]
    assert handlers.no_next_chunk is namespace["FixItFelix_No_NextChunk"]
    assert handlers.gama_zero is namespace["FixItFelix_Gama_Zero"]
    assert handlers.critical_miss is namespace["FixItFelix_Critical_Miss"]

    fix_runtime = fixit_felix_runtime.build_fixit_felix_runtime_from_namespace(namespace)
    assert fix_runtime.try_automatic_repair("plte_cleanup") == "automatic_repair"
    assert fix_runtime.apply_finding_work_item(
        fixit_felix.FixItFelixWorkItem("finding", "wrong_crc", "finding"),
        "IDAT_Tool_",
        3,
        b"IDAT",
    ) == "wrong_crc"

    def runner(runtime, findings, *, skip_bad_crc, bad_next_name, chkd, chunk):
        calls.append(
            (
                "runner",
                (findings, skip_bad_crc, bad_next_name, chkd, chunk),
                {},
            )
        )
        assert runtime.try_automatic_repair("known_chunk_type_case") == "automatic_repair"
        assert runtime.apply_finding_work_item(
            fixit_felix.FixItFelixWorkItem("finding", "critical_miss", "finding"),
            chkd,
            1,
            chunk,
        ) == "critical_miss"
        return fixit_felix.FixItFelixRunResult(True, "pipeline-result")

    result = fixit_felix_runtime.run_fixit_felix_pipeline_from_namespace(
        namespace,
        b"IDAT",
        "IDAT_Tool_",
        runner=runner,
    )

    assert result == fixit_felix.FixItFelixRunResult(True, "pipeline-result")
    assert ("Pause", ("FixItFelix Debug Pause:",), {}) in calls
    assert (
        "runner",
        (pandora_box, False, False, "IDAT_Tool_", b"IDAT"),
        {},
    ) in calls
    assert any(call[0] == "PRINT" and str(call[1][0]).startswith("EOF:") for call in calls)


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
        ("Deferred IDAT CRC route ignores error counter", test_deferred_idat_crc_route_key_ignores_error_counter),
        ("Apply wrong CRC skips deferred IDAT route", test_apply_wrong_crc_skips_question_for_deferred_idat_route),
        (
            "Apply wrong CRC records failed IDAT route",
            test_apply_wrong_crc_records_failed_idat_crc_route_when_patch_still_breaks,
        ),
        ("Apply wrong CRC other errors defers", test_apply_wrong_crc_other_errors_defers_to_chunk_story),
        (
            "Apply wrong CRC Cornucopia debug path",
            test_apply_wrong_crc_already_in_cornucopia_uses_debug_emit_without_tools,
        ),
        ("Apply wrong CRC rejects missing tools", test_apply_wrong_crc_rejects_missing_tools_for_action),
        ("Apply wrong CRC rejects unknown action", test_apply_wrong_crc_rejects_unknown_action),
        (
            "Apply wrong chunk name length probe accepts",
            test_apply_wrong_chunk_name_length_probe_accepts_nearby_chunk,
        ),
        (
            "Apply wrong chunk name length probe declines",
            test_apply_wrong_chunk_name_length_probe_decline_then_bruteforce_decline_sets_skips,
        ),
        ("Apply wrong chunk name bruteforce accepts", test_apply_wrong_chunk_name_bruteforce_accepts_brute_chunk),
        ("Apply wrong chunk name saves existing", test_apply_wrong_chunk_name_saves_existing_solution),
        (
            "Apply wrong chunk name rejects missing tools",
            test_apply_wrong_chunk_name_rejects_missing_tools_for_action,
        ),
        ("Apply wrong chunk name rejects unknown action", test_apply_wrong_chunk_name_rejects_unknown_action),
        (
            "Apply no-next false positive runs libpng",
            test_apply_no_next_false_positive_iend_runs_libpng_after_marking_eof,
        ),
        ("Apply no-next false positive clean cut", test_apply_no_next_false_positive_iend_writes_clean_cut),
        ("Apply no-next wrong IEND length ends", test_apply_no_next_wrong_iend_length_records_note_and_ends),
        ("Apply no-next appends dummy at CRC tail", test_apply_no_next_append_missing_iend_uses_dummy_at_crc_tail),
        ("Apply no-next length probe routes nearby", test_apply_no_next_ask_length_probe_routes_to_nearby_chunk),
        ("Apply no-next rejects unknown action", test_apply_no_next_chunk_rejects_unknown_action),
        ("Apply libpng saves existing solution", test_apply_libpng_error_saves_existing_solution),
        ("Apply libpng accepts Relics prompt", test_apply_libpng_error_accepts_relics_prompt_and_sets_skip),
        ("Apply libpng declines Relics prompt", test_apply_libpng_error_declines_relics_prompt_and_ends),
        ("Apply libpng not enough image data ends", test_apply_libpng_error_not_enough_image_data_ends_after_todo),
        ("Apply libpng skip reports critical", test_apply_libpng_error_skip_only_reports_critical_hit),
        ("Apply libpng rejects unknown action", test_apply_libpng_error_rejects_unknown_action),
        ("Finding handlers route callback arguments", test_finding_handlers_route_legacy_callback_arguments),
        ("Apply finding work item dispatches", test_apply_finding_work_item_dispatches_through_fixit_felix_dispatch),
        ("Runtime uses automatic repair and callbacks", test_runtime_uses_automatic_repair_and_legacy_callbacks),
        ("Namespace runtime builders", test_namespace_runtime_builders_preserve_legacy_wiring),
        ("Namespace pipeline builder", test_namespace_pipeline_builder_preserves_debug_and_repair_wiring),
    ]

    print("Running FixItFelix runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"FixItFelix runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
