#!/usr/bin/env python3
import sys
import zlib
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import fixit_felix
from chunklate import fixit_felix_runtime
from chunklate import messages
from chunklate.png import IEND_CHUNK, PNG_SIGNATURE, build_png_chunk


def valid_png_bytes():
    ihdr = b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x00\x00\x00\x00"
    idat = zlib.compress(b"\x00\x00")
    return (
        PNG_SIGNATURE
        + build_png_chunk(b"IHDR", ihdr)
        + build_png_chunk(b"IDAT", idat)
        + IEND_CHUNK
    )


def test_apply_repair_records_note_and_writes_clone():
    side_notes = []
    writes = []
    candy_calls = []
    runtime = fixit_felix_runtime.AutomaticRepairRuntime(
        side_notes=side_notes,
        candy=lambda *args: candy_calls.append(args),
        write_clone=lambda data_hex, save_suffix: writes.append((data_hex, save_suffix)),
    )
    repair = SimpleNamespace(
        data=b"fixed",
        strategy="unit-test-repair",
    )

    result = fixit_felix_runtime.apply_repair(runtime, repair)

    assert result is True
    assert candy_calls == [
        (
            "Cowsay",
            "I found an automatic repair path: unit-test-repair.",
            "com",
        )
    ]
    assert side_notes == ["-FixItFelix:unit-test-repair."]
    assert writes == [("6669786564", "-unit-test-repair.")]


def test_apply_repair_prompts_before_unproven_chrm_inference():
    side_notes = []
    writes = []
    question_calls = []
    candy_calls = []
    runtime = fixit_felix_runtime.AutomaticRepairRuntime(
        side_notes=side_notes,
        candy=lambda *args: candy_calls.append(args),
        write_clone=lambda data_hex, save_suffix: writes.append((data_hex, save_suffix)),
        question=lambda **kwargs: question_calls.append(kwargs) or True,
    )
    repair = SimpleNamespace(
        data=b"inferred",
        strategy="inferred 1 missing cHRM byte(s) and rebuilt CRC",
        chunk_offset=49,
        old_length=31,
        new_length=32,
        missing_bytes=1,
        inferred_payload=b"x" * 32,
        removal_data=b"removed",
        preserved_crc=False,
        removed=False,
        crc_candidates_tested=256,
    )

    result = fixit_felix_runtime.apply_repair(runtime, repair)

    assert result is True
    assert question_calls[0]["skipauto"] is True
    assert question_calls[0]["id"] == "cHRM Missing Bytes Inference:-cHRM length is not Valid"
    assert any("None matched" in call[1] for call in candy_calls if len(call) > 1)
    assert side_notes == ["-FixItFelix:inferred 1 missing cHRM byte(s) and rebuilt CRC."]
    assert writes == [("696e666572726564", "-inferred 1 missing cHRM byte(s) and rebuilt CRC.")]


def test_apply_repair_removes_short_chrm_when_inference_declined():
    side_notes = []
    writes = []
    runtime = fixit_felix_runtime.AutomaticRepairRuntime(
        side_notes=side_notes,
        candy=lambda *args: None,
        write_clone=lambda data_hex, save_suffix: writes.append((data_hex, save_suffix)),
        question=lambda **_kwargs: False,
    )
    repair = SimpleNamespace(
        data=b"inferred",
        strategy="inferred 1 missing cHRM byte(s) and rebuilt CRC",
        chunk_offset=49,
        old_length=31,
        new_length=32,
        missing_bytes=1,
        inferred_payload=b"x" * 32,
        removal_data=b"removed",
        preserved_crc=False,
        removed=False,
        crc_candidates_tested=256,
    )

    result = fixit_felix_runtime.apply_repair(runtime, repair)

    assert result is True
    assert side_notes == [
        "-FixItFelix:removed short cHRM chunk length 31 below required 32 after declining inferred cHRM completion."
    ]
    assert writes == [("72656d6f766564", "-removed short cHRM chunk length 31 below required 32.")]


def test_apply_repair_explains_ihdr_rebuild_before_writing_clone():
    side_notes = []
    writes = []
    candy_calls = []
    runtime = fixit_felix_runtime.AutomaticRepairRuntime(
        side_notes=side_notes,
        candy=lambda *args: candy_calls.append(args),
        write_clone=lambda data_hex, save_suffix: writes.append((data_hex, save_suffix)),
        pandora_box={
            "Checksum_Error_0:Wrong Crc b'IHDR'": {},
        },
    )
    data = valid_png_bytes()
    repair = SimpleNamespace(
        data=data,
        strategy="rebuilt IHDR from IDAT scanline size",
    )

    result = fixit_felix_runtime.apply_repair(runtime, repair)

    assert result is True
    assert candy_calls == [
        (
            "Cowsay",
            "This is not just a cheap CRC sticker swap. I rebuilt IHDR from the image clues first.",
            "com",
        ),
        (
            "Cowsay",
            "Now I can write a clone with a coherent header instead of pretending the old one was fine.",
            "com",
        ),
    ]
    assert side_notes == ["-FixItFelix:rebuilt IHDR from IDAT scanline size."]
    assert writes == [(data.hex(), "-rebuilt IHDR from IDAT scanline size.")]


def test_apply_repair_explains_ihdr_value_rebuild_without_crc_noise():
    side_notes = []
    writes = []
    candy_calls = []
    runtime = fixit_felix_runtime.AutomaticRepairRuntime(
        side_notes=side_notes,
        candy=lambda *args: candy_calls.append(args),
        write_clone=lambda data_hex, save_suffix: writes.append((data_hex, save_suffix)),
        pandora_box={
            "GetInfo_Error_0:-IHDR Color 3: Wrong bit depht with IHDR Color type 3": {},
        },
    )
    data = valid_png_bytes()
    repair = SimpleNamespace(
        data=data,
        strategy="rebuilt IHDR from IDAT scanline size",
        width=32,
        height=32,
        bit_depth=8,
        color_type=3,
    )

    result = fixit_felix_runtime.apply_repair(runtime, repair)

    assert result is True
    assert candy_calls == [
        (
            "Cowsay",
            "IHDR's CRC is not the complaint here. The header values themselves are impossible together.",
            "bad",
        ),
        (
            "Cowsay",
            "I rebuilt IHDR from the IDAT scanline math: 32x32, bit depth 8, color type 3.",
            "com",
        ),
        (
            "Cowsay",
            "Now I can write a clone with a coherent header instead of pretending the old one was fine.",
            "com",
        ),
    ]
    assert not any("cheap CRC" in call[1] for call in candy_calls)
    assert side_notes == [
        "-FixItFelix:rebuilt IHDR from IDAT scanline size.\n"
        "-FixItFelix:Selected IHDR 32x32, bit depth 8, color type 3."
    ]
    assert writes == [(data.hex(), "-rebuilt IHDR from IDAT scanline size.")]


def test_apply_repair_rejects_invalid_ihdr_rebuild_before_clone():
    side_notes = []
    writes = []
    candy_calls = []
    runtime = fixit_felix_runtime.AutomaticRepairRuntime(
        side_notes=side_notes,
        candy=lambda *args: candy_calls.append(args),
        write_clone=lambda data_hex, save_suffix: writes.append((data_hex, save_suffix)),
    )
    repair = SimpleNamespace(
        data=b"fixed",
        strategy="rebuilt IHDR from IDAT scanline size",
    )

    result = fixit_felix_runtime.apply_repair(runtime, repair)

    assert result is None
    assert writes == []
    assert candy_calls == [
        (
            "Cowsay",
            "The rebuilt IHDR still does not make a structurally valid PNG: PNG signature is not at offset 0",
            "bad",
        ),
        (
            "Cowsay",
            "So I am not writing that clone. Next stop is the IHDR brute force path.",
            "com",
        ),
    ]
    assert side_notes == [
        "-FixItFelix:IHDR automatic repair rejected before clone write: PNG signature is not at offset 0."
    ]


def test_try_ihdr_stored_crc_bruteforce_uses_loader_and_writes_valid_candidate():
    data = valid_png_bytes()
    calls = []
    side_notes = []
    original_run_scan = fixit_felix_runtime.bruteforce_runtime.run_scan

    def fake_run_scan(scan_runtime, scan_context):
        calls.append(("scan_context", scan_context))
        scan_runtime.loadingbar(50, 2, 0, True)
        scan_runtime.loadingbar(50, 2, 25, False)
        scan_runtime.minibar(Indication="scan-started")
        return fixit_felix_runtime.bruteforce_runtime.SmashBruteBrawlScanResult(
            state=fixit_felix_runtime.bruteforce.BruteForceMatchState(bingo=True),
            old_crc=b"crc!",
            bf_mode="Brutus",
            full_new_data=b"",
            png_bytes=data,
            to_brute="",
            diff="",
            crash=False,
            eta_seconds=0,
        )

    try:
        fixit_felix_runtime.bruteforce_runtime.run_scan = fake_run_scan
        runtime = fixit_felix_runtime.AutomaticRepairRuntime(
            side_notes=side_notes,
            candy=lambda *args: calls.append(("candy", args)),
            write_clone=lambda data_hex, summary: calls.append(("write_clone", data_hex, summary)),
            question=lambda **kwargs: calls.append(("question", kwargs)) or True,
            data_hex=data.hex(),
            pandora_box={"Checksum_Error_0:Wrong Crc b'IHDR'": {}},
            get_spec=lambda *args, **kwargs: calls.append(("get_spec", args, kwargs)),
            product=lambda *args, **kwargs: calls.append(("product", args, kwargs)),
            loadingbar=lambda *args, **kwargs: calls.append(("loadingbar", args, kwargs)),
            minibar=lambda *args, **kwargs: calls.append(("minibar", args, kwargs)),
            file_origin="sample.png",
        )
        repair = SimpleNamespace(
            data=data,
            strategy="rebuilt IHDR from IDAT scanline size",
            preserved_crc=False,
        )

        result = fixit_felix_runtime.try_ihdr_stored_crc_bruteforce(runtime, repair)
    finally:
        fixit_felix_runtime.bruteforce_runtime.run_scan = original_run_scan

    assert result is True
    assert (
        "question",
        {"id": "IHDR CRC Brute Force:-Wrong Crc b'IHDR'", "idhash": ("IHDR", 8, 981375829)},
    ) in calls
    assert ("minibar", (), {"Indication": "IHDR CRC brute force: stored CRC target"}) in calls
    assert ("minibar", (), {"Indication": "IHDR CRC 0/50"}) in calls
    assert ("minibar", (), {"Indication": "IHDR CRC 25/50"}) in calls
    assert ("minibar", (), {"Indication": "scan-started"}) in calls
    scan_context = next(call[1] for call in calls if call[0] == "scan_context")
    assert scan_context.chunk_name == b"IHDR"
    assert scan_context.bf_mode == "Brutus"
    assert scan_context.old_crc is not False
    assert any(call[0] == "write_clone" and call[1] == data.hex() for call in calls)
    assert "-FixItFelix:IHDR stored-CRC brute force succeeded." in side_notes


def test_try_ihdr_stored_crc_bruteforce_decline_falls_back_to_rebuild():
    data = valid_png_bytes()
    calls = []
    runtime = fixit_felix_runtime.AutomaticRepairRuntime(
        side_notes=[],
        candy=lambda *args: calls.append(("candy", args)),
        write_clone=lambda *args: calls.append(("write_clone", args)),
        question=lambda **kwargs: calls.append(("question", kwargs)) or False,
        data_hex=data.hex(),
        pandora_box={"Checksum_Error_0:Wrong Crc b'IHDR'": {}},
        minibar=lambda *args, **kwargs: calls.append(("minibar", args, kwargs)),
    )
    repair = SimpleNamespace(
        data=data,
        strategy="rebuilt IHDR from IDAT scanline size",
        preserved_crc=False,
    )

    result = fixit_felix_runtime.try_ihdr_stored_crc_bruteforce(runtime, repair)

    assert result is None
    assert (
        "question",
        {"id": "IHDR CRC Brute Force:-Wrong Crc b'IHDR'", "idhash": ("IHDR", 8, 981375829)},
    ) in calls
    assert not any(call[0] == "write_clone" for call in calls)


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


def test_repeated_deferred_repair_message_templates_are_adaptable():
    assert len(fixit_felix_runtime.REPEATED_DEFER_MESSAGE_TEMPLATES) == 20

    first = fixit_felix_runtime.repeated_deferred_repair_message(
        error_label="wrong CRC",
        chunk=b"IDAT",
        chooser=lambda choices: choices[0],
    )
    other_chunk = fixit_felix_runtime.repeated_deferred_repair_message(
        error_label="wrong CRC",
        chunk=b"PLTE",
        chooser=lambda choices: choices[1],
    )
    other_error = fixit_felix_runtime.repeated_deferred_repair_message(
        error_label="bad length",
        chunk=b"IEND",
        chooser=lambda choices: choices[-1],
    )
    generic = fixit_felix_runtime.repeated_deferred_repair_message(
        error_label="repeated route",
        chooser=lambda choices: choices[-1],
    )

    assert first == (
        "Ah shit ...here we go again ...another wrong CRC in an IDAT chunk in Grove Street. "
        "I will keep it for later."
    )
    assert "wrong CRC in a PLTE chunk" in other_chunk
    assert "bad length in an IEND chunk" in other_error
    assert generic == "Fine. repeated route goes into the later pile."


def wrong_crc_tools(*, chunk=b"IDAT", offset="0x2a", start=12, end=20, replacement_crc="fixed-crc-data"):
    return SimpleNamespace(
        replacement_crc=replacement_crc,
        start=start,
        end=end,
        chunk=chunk,
        offset=offset,
        old_crc="old-crc",
    )


def bad_deflate_png_crc_patch():
    ihdr = build_png_chunk(
        b"IHDR",
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00",
    )
    idat_payload = b"\x00\x00\xff\xff"
    idat_chunk = build_png_chunk(b"IDAT", idat_payload)
    data = PNG_SIGNATURE + ihdr + idat_chunk + IEND_CHUNK
    idat_offset = len(PNG_SIGNATURE) + len(ihdr)
    crc_start = (idat_offset + 8 + len(idat_payload)) * 2
    crc_end = crc_start + 8
    replacement_crc = data[idat_offset + 8 + len(idat_payload) : idat_offset + 12 + len(idat_payload)].hex()
    return data.hex(), replacement_crc, crc_start, crc_end


def one_byte_corrupt_deflate_png_hex():
    ihdr = build_png_chunk(
        b"IHDR",
        b"\x00\x00\x00\x01\x00\x00\x00\x02\x08\x02\x00\x00\x00",
    )
    filtered = b"\x00abc" + b"\x00def"
    compressed = bytearray(zlib.compress(filtered))
    compressed[2] ^= 0xFF
    data = PNG_SIGNATURE + ihdr + build_png_chunk(b"IDAT", bytes(compressed)) + IEND_CHUNK
    return data.hex()


def bad_adler_png_hex():
    ihdr = build_png_chunk(
        b"IHDR",
        b"\x00\x00\x00\x01\x00\x00\x00\x02\x08\x02\x00\x00\x00",
    )
    filtered = b"\x00abc" + b"\x00def"
    compressed = bytearray(zlib.compress(filtered))
    compressed[-1] ^= 0xFF
    data = PNG_SIGNATURE + ihdr + build_png_chunk(b"IDAT", bytes(compressed)) + IEND_CHUNK
    return data.hex()


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
    side_notes=None,
    last_question_status=None,
    deferred_routes=None,
    deflate_probe_keys=None,
    loadingbar=None,
    minibar=None,
):
    answer_iter = iter(answers)
    if deferred_routes is None:
        deferred_routes = set()
    if deflate_probe_keys is None:
        deflate_probe_keys = set()
    if side_notes is None:
        side_notes = []

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

    def remember_deflate_probe(analysis):
        calls.append(("remember_idat_deflate_probe", (analysis,), {}))
        key = fixit_felix_runtime.idat_deflate_probe_key(analysis)
        if key in deflate_probe_keys:
            return False
        deflate_probe_keys.add(key)
        return True

    return fixit_felix_runtime.WrongCrcRuntime(
        emit=record("emit"),
        candy=record("candy"),
        question=question,
        save_clone=record("save_clone", "saved"),
        write_clone=record("write_clone", "written"),
        chunk_story=record("chunk_story"),
        set_skip_bad_crc=record("set_skip_bad_crc"),
        set_old_bad_crc=record("set_old_bad_crc"),
        side_notes=side_notes,
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
        remember_idat_deflate_probe=remember_deflate_probe,
        debug=debug,
        pause_debug=pause_debug,
        loadingbar=loadingbar,
        minibar=minibar,
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
    assert (
        "candy",
        (
            "Cowsay",
            "This is the cheap CRC-only patch: I am changing the checksum label, not the chunk data.",
            "com",
        ),
        {},
    ) in calls
    assert (
        "candy",
        (
            "Cowsay",
            "If the bytes are lying too, this will not save them. But the structure lets me try this tiny bandage.",
            "com",
        ),
        {},
    ) in calls
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


def test_deferred_idat_crc_route_records_structural_state():
    namespace = {}
    tools = wrong_crc_tools(chunk=b"IDAT", offset=182, start=12, end=20)
    key = fixit_felix_runtime.deferred_idat_crc_route_key(
        "Checksum_Error_0:Wrong Crc b'IDAT'",
        tools,
    )

    fixit_felix_runtime.remember_deferred_idat_crc_route(
        namespace,
        "Checksum_Error_0:Wrong Crc b'IDAT'",
        tools,
    )

    assert namespace["REPAIR_ROUTE_STATES"][key] == "deferred"
    assert fixit_felix_runtime.is_deferred_idat_crc_route(
        namespace,
        "Checksum_Error_1:Wrong Crc b'IDAT'",
        tools,
    ) is True
    assert namespace["REPAIR_ROUTE_STATES"][key] == "skipped_duplicate"


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
    assert not any(call[0] == "question" for call in calls)
    assert ("set_idat_crc_patch_failed", (True,), {}) in calls
    assert ("set_idat_crc_patch_failed_finding", (finding,), {}) in calls
    assert any(call[0] == "remember_deferred_idat_crc_route" for call in calls)
    assert (
        "candy",
        (
            "Cowsay",
            "So i'm not asking you to bless a fake fix. I will keep that CRC for later.",
            "com",
        ),
        {},
    ) in calls


def test_apply_wrong_crc_defers_crc_only_when_idat_stream_stays_invalid():
    calls = []
    side_notes = []
    finding = "Checksum_Error_0:Wrong Crc b'IDAT'"
    chkd = "IDAT_Tool_"
    data_hex, replacement_crc, start, end = bad_deflate_png_crc_patch()
    runtime = wrong_crc_runtime(
        calls,
        answers=(True,),
        pandora_box={finding: {chkd + "0": replacement_crc}},
        data_hex=data_hex,
        side_notes=side_notes,
    )

    result = fixit_felix_runtime.apply_wrong_crc(
        runtime,
        fixit_felix.WrongCrcDecision("ask_easy_crc_fix", finding, 0),
        chkd,
        wrong_crc_tools(chunk=b"IDAT", replacement_crc=replacement_crc, start=start, end=end),
    )

    assert result == (False, None)
    assert not [call for call in calls if call[0] == "save_clone"]
    assert not [call for call in calls if call[0] == "question"]
    assert any(note.startswith("-IDAT stream diagnosis: status=bad_zlib_header") for note in side_notes)
    assert any(note.startswith("-Deferred IDAT CRC-only patch: zlib stream still invalid:") for note in side_notes)


def test_apply_wrong_crc_writes_improved_deflate_probe_instead_of_crc_clone():
    calls = []
    side_notes = []
    finding = "Checksum_Error_0:Wrong Crc b'IDAT'"
    chkd = "IDAT_Tool_"
    runtime = wrong_crc_runtime(
        calls,
        answers=(True,),
        pandora_box={finding: {chkd + "0": "fixed-crc-data"}},
        data_hex=one_byte_corrupt_deflate_png_hex(),
        side_notes=side_notes,
        minibar=lambda *args: calls.append(("minibar", args, {})),
    )

    result = fixit_felix_runtime.apply_wrong_crc(
        runtime,
        fixit_felix.WrongCrcDecision("ask_easy_crc_fix", finding, 0),
        chkd,
        wrong_crc_tools(chunk=b"IDAT", replacement_crc="00000000", start=12, end=20),
    )

    assert result == (True, "written")
    assert not [call for call in calls if call[0] == "save_clone"]
    assert not [call for call in calls if call[0] == "question"]
    assert ("candy", ("Title", "probe_deflate_header_candidates"), {}) in calls
    assert any(call[0] == "minibar" and "IDAT deflate-header" in call[1][0] for call in calls)
    assert [call for call in calls if call[0] == "write_clone"]
    assert "-Repair hypothesis tried: targeted IDAT deflate header probe." in calls[-1][1][1]
    assert any(note.startswith("-IDAT deflate candidate:") for note in side_notes)


def test_apply_wrong_crc_uses_heavy_probe_loadingbar_after_quick_probe_fails():
    calls = []
    side_notes = []
    finding = "Checksum_Error_0:Wrong Crc b'IDAT'"
    chkd = "IDAT_Tool_"
    original_quick = fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_strategy_queue
    original_heavy = fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_heavy_candidates

    def loadingbar(*args):
        calls.append(("loadingbar", args, {}))

    def quick_no_candidate(data, **_kwargs):
        before = fixit_felix_runtime.idat.analyze_idat_stream(data)
        return fixit_felix_runtime.idat_bruteforce.IdatDeflateProbeResult(
            before,
            None,
            0,
            0,
            0,
            False,
            "strategy-queue",
        )

    def heavy_candidate(data, *, progress=None):
        return original_heavy(
            data,
            backtrack=8,
            forward=8,
            budget=5000,
            progress=progress,
        )

    try:
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_strategy_queue = quick_no_candidate
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_heavy_candidates = heavy_candidate
        runtime = wrong_crc_runtime(
            calls,
            answers=(True,),
            pandora_box={finding: {chkd + "0": "fixed-crc-data"}},
            data_hex=bad_adler_png_hex(),
            side_notes=side_notes,
            loadingbar=loadingbar,
        )

        result = fixit_felix_runtime.apply_wrong_crc(
            runtime,
            fixit_felix.WrongCrcDecision("ask_easy_crc_fix", finding, 0),
            chkd,
            wrong_crc_tools(chunk=b"IDAT", replacement_crc="00000000", start=12, end=20),
        )
    finally:
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_strategy_queue = original_quick
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_heavy_candidates = original_heavy

    assert result == (True, "written")
    assert any(call[0] == "question" for call in calls)
    assert ("candy", ("Title", "probe_idat_deflate_strategy_queue"), {}) in calls
    assert ("candy", ("Title", "probe_idat_deflate_heavy_candidates"), {}) in calls
    assert any(call == ("loadingbar", (5000, 4, 0, True), {}) for call in calls)
    assert any(call[0] == "write_clone" for call in calls)
    assert any(note.startswith("-IDAT deflate probe: strategy=heavy-byte") for note in side_notes)


def test_apply_wrong_crc_declines_heavy_probe_without_loadingbar_or_clone():
    calls = []
    side_notes = []
    finding = "Checksum_Error_0:Wrong Crc b'IDAT'"
    chkd = "IDAT_Tool_"
    original_quick = fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_strategy_queue
    original_heavy = fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_heavy_candidates

    def quick_no_candidate(data, **_kwargs):
        before = fixit_felix_runtime.idat.analyze_idat_stream(data)
        return fixit_felix_runtime.idat_bruteforce.IdatDeflateProbeResult(
            before,
            None,
            0,
            0,
            0,
            False,
            "strategy-queue",
        )

    def fail_heavy(*args, **kwargs):
        raise AssertionError("heavy probe should not run when user declines")

    try:
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_strategy_queue = quick_no_candidate
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_heavy_candidates = fail_heavy
        runtime = wrong_crc_runtime(
            calls,
            answers=(False,),
            pandora_box={finding: {chkd + "0": "fixed-crc-data"}},
            data_hex=bad_adler_png_hex(),
            side_notes=side_notes,
            loadingbar=lambda *args: calls.append(("loadingbar", args, {})),
        )

        result = fixit_felix_runtime.apply_wrong_crc(
            runtime,
            fixit_felix.WrongCrcDecision("ask_easy_crc_fix", finding, 0),
            chkd,
            wrong_crc_tools(chunk=b"IDAT", replacement_crc="00000000", start=12, end=20),
        )
    finally:
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_strategy_queue = original_quick
        fixit_felix_runtime.idat_bruteforce.probe_idat_deflate_heavy_candidates = original_heavy

    assert result == (False, None)
    assert any(call[0] == "question" for call in calls)
    assert ("candy", ("Title", "probe_idat_deflate_strategy_queue"), {}) in calls
    assert ("candy", ("Title", "probe_idat_deflate_heavy_candidates"), {}) not in calls
    assert not any(call[0] == "loadingbar" for call in calls)
    assert not any(call[0] == "write_clone" for call in calls)
    assert "-IDAT heavy probe declined by user." in side_notes
    assert "-IDAT deflate heavy probe skipped: user declined." in side_notes


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


def raw_png_chunk(declared_length, chunk_type, payload):
    return declared_length.to_bytes(4, "big") + chunk_type + payload + b"\x00\x00\x00\x00"


def idat_chain_candidate_hex():
    data = (
        PNG_SIGNATURE
        + build_png_chunk(b"IHDR", b"\x00" * 13)
        + raw_png_chunk(4, b"IDAT", b"aaaa")
        + raw_png_chunk(4, b"IDAT", b"0000")
        + raw_png_chunk(5, b"@DAT", b"bbbb")
        + raw_png_chunk(4, b"IDAT", b"cccc")
        + IEND_CHUNK
    )
    return data.hex()


def idat_chain_aligned_bad_deflate_hex():
    ihdr = build_png_chunk(
        b"IHDR",
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00",
    )
    data = (
        PNG_SIGNATURE
        + ihdr
        + raw_png_chunk(2, b"IDAT", b"\x78\x9c")
        + raw_png_chunk(2, b"IDAT", b"\xff\xff")
        + IEND_CHUNK
    )
    return data.hex()


def wrong_chunk_name_before_first_idat_hex():
    ihdr = build_png_chunk(
        b"IHDR",
        b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00",
    )
    data = (
        PNG_SIGNATURE
        + ihdr
        + raw_png_chunk(4, b"zzzz", b"aaaa")
        + raw_png_chunk(4, b"IDAT", b"bbbb")
        + IEND_CHUNK
    )
    return data.hex(), len(PNG_SIGNATURE) + len(ihdr) + 4


def test_wrong_chunk_name_route_key_ignores_error_counter():
    first = fixit_felix_runtime.wrong_chunk_name_route_key(
        "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42",
        "zzzz_Tool_",
        wrong_chunk_name_tools(),
        "bruteforce",
    )
    second = fixit_felix_runtime.wrong_chunk_name_route_key(
        "CheckChunkName_Error_1:has Wrong Chunk name at offset: 42",
        "zzzz_Tool_",
        wrong_chunk_name_tools(),
        "bruteforce",
    )
    other = fixit_felix_runtime.wrong_chunk_name_route_key(
        "CheckChunkName_Error_1:has Wrong Chunk name at offset: 42",
        "zzzz_Tool_",
        SimpleNamespace(
            chunk_type=b"IDA^",
            chunk_length="13",
            chunk_type_offset=128,
            previous_chunk=b"IHDR",
        ),
        "bruteforce",
    )

    assert first == second
    assert first != other


def test_wrong_chunk_name_route_records_structural_state():
    namespace = {}
    tools = wrong_chunk_name_tools()
    key = fixit_felix_runtime.wrong_chunk_name_route_key(
        "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42",
        "zzzz_Tool_",
        tools,
        "bruteforce",
    )

    fixit_felix_runtime.remember_wrong_chunk_name_route(
        namespace,
        "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42",
        "zzzz_Tool_",
        tools,
        "bruteforce",
    )

    assert namespace["REPAIR_ROUTE_STATES"][key] == "tried"
    assert fixit_felix_runtime.is_wrong_chunk_name_route_tried(
        namespace,
        "CheckChunkName_Error_1:has Wrong Chunk name at offset: 42",
        "zzzz_Tool_",
        tools,
        "bruteforce",
    ) is True
    assert namespace["REPAIR_ROUTE_STATES"][key] == "skipped_duplicate"


def test_wrong_chunk_name_before_first_idat_does_not_block_name_repair():
    data_hex, chunk_type_offset = wrong_chunk_name_before_first_idat_hex()
    tools = SimpleNamespace(
        chunk_type=b"zzzz",
        chunk_length="4",
        chunk_type_offset=chunk_type_offset,
        previous_chunk=b"pHYs",
    )

    assert fixit_felix_runtime.wrong_chunk_name_precedes_first_parsed_idat(data_hex, tools) is True


def wrong_chunk_name_runtime(
    calls,
    *,
    answers=(),
    bad_ancillary=False,
    pandora_box=None,
    cornucopia=None,
    side_notes=None,
    tried_routes=None,
    data_hex="00112233445566778899",
):
    answer_iter = iter(answers)
    if side_notes is None:
        side_notes = []
    if tried_routes is None:
        tried_routes = set()

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
        write_clone=record("write_clone", "written"),
        set_skip_bad_next_name=record("set_skip_bad_next_name"),
        set_skip_bad_current_name=record("set_skip_bad_current_name"),
        bad_ancillary=lambda: bad_ancillary,
        pandora_box=pandora_box if pandora_box is not None else {},
        cornucopia=cornucopia if cornucopia is not None else {},
        data_hex=data_hex,
        side_notes=side_notes,
        remember_wrong_chunk_name_route=lambda finding, chkd, tools, action: tried_routes.add(
            fixit_felix_runtime.wrong_chunk_name_route_key(finding, chkd, tools, action)
        ),
        is_wrong_chunk_name_route_tried=lambda finding, chkd, tools, action: (
            fixit_felix_runtime.wrong_chunk_name_route_key(finding, chkd, tools, action)
            in tried_routes
        ),
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
    side_notes = []
    runtime = wrong_chunk_name_runtime(
        calls,
        answers=(True,),
        pandora_box={finding: {chkd + "0": b"zzzz"}},
        side_notes=side_notes,
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
    assert side_notes == ["-Repair hypothesis tried: chunk-name recovery for zzzz at 0x80."]


def test_apply_wrong_chunk_name_bruteforce_skips_known_route_without_question():
    calls = []
    finding = "CheckChunkName_Error_1:has Wrong Chunk name at offset: 42"
    chkd = "zzzz_Tool_"
    tools = wrong_chunk_name_tools()
    side_notes = []
    tried_routes = {
        fixit_felix_runtime.wrong_chunk_name_route_key(
            "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42",
            chkd,
            tools,
            "bruteforce",
        )
    }
    runtime = wrong_chunk_name_runtime(
        calls,
        answers=(),
        pandora_box={finding: {chkd + "0": b"zzzz"}},
        side_notes=side_notes,
        tried_routes=tried_routes,
    )

    result = fixit_felix_runtime.apply_wrong_chunk_name(
        runtime,
        fixit_felix.WrongChunkNameDecision("ask_bruteforce", finding, True),
        chkd,
        tools,
    )

    assert result == (False, None)
    assert not [call for call in calls if call[0] == "question"]
    assert ("set_skip_bad_current_name", (True,), {}) in calls
    assert (
        "-Repair hypothesis skipped: chunk-name recovery for zzzz at 0x80; "
        "reason: route was already tried."
    ) in side_notes


def test_apply_wrong_chunk_name_uses_idat_chain_batch_before_bruteforce():
    calls = []
    side_notes = []
    finding = "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42"
    chkd = "zzzz_Tool_"
    runtime = wrong_chunk_name_runtime(
        calls,
        answers=(),
        pandora_box={finding: {chkd + "0": b"zzzz"}},
        side_notes=side_notes,
        data_hex=idat_chain_candidate_hex(),
    )

    result = fixit_felix_runtime.apply_wrong_chunk_name(
        runtime,
        fixit_felix.WrongChunkNameDecision("ask_bruteforce", finding, True),
        chkd,
        wrong_chunk_name_tools(),
    )

    assert result == (True, "written")
    assert not [call for call in calls if call[0] == "question"]
    assert not [call for call in calls if call[0] == "ancillary"]
    assert not [call for call in calls if call[0] == "brute_chunk"]
    assert any(call[0] == "write_clone" for call in calls)
    assert "-Repair hypothesis tried: IDAT chain header repair." in side_notes
    assert any("type @DAT -> IDAT" in note for note in side_notes)


def test_apply_wrong_chunk_name_uses_deflate_probe_when_aligned_stream_is_bad():
    calls = []
    side_notes = []
    finding = "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42"
    chkd = "zzzz_Tool_"
    runtime = wrong_chunk_name_runtime(
        calls,
        answers=(True,),
        pandora_box={finding: {chkd + "0": b"zzzz"}},
        side_notes=side_notes,
        data_hex=idat_chain_aligned_bad_deflate_hex(),
    )

    result = fixit_felix_runtime.apply_wrong_chunk_name(
        runtime,
        fixit_felix.WrongChunkNameDecision("ask_bruteforce", finding, True),
        chkd,
        wrong_chunk_name_tools(),
    )

    assert result == (False, None)
    assert not [call for call in calls if call[0] == "question"]
    assert not [call for call in calls if call[0] == "ancillary"]
    assert not [call for call in calls if call[0] == "brute_chunk"]
    assert not [call for call in calls if call[0] == "write_clone"]
    assert any(note.startswith("-IDAT stream diagnosis: status=corrupt_deflate") for note in side_notes)
    assert "-IDAT deflate header probe found no clone-worthy scanline progress." in side_notes
    assert "-IDAT wide deflate probes skipped: header probe produced no usable scanline." in side_notes


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
    chunks_history=(),
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
            nearby_found_later_iend=lambda: state.get("nearby_found_later_iend"),
            chunks_history=tuple(chunks_history),
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
    assert (
        "candy",
        ("Cowsay", "That No NextChunk is a false positive im removing it ..", "good"),
        {},
    ) in calls
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

    assert result == (False, None)
    assert state["eof"] is True
    assert side_notes == [
        "-Reached the end of file.",
        "-Stopped before libpng: unresolved misplaced chunk remains after IDAT.",
    ]
    assert all(call[0] != "the_good_place" for call in calls)
    assert not [call for call in calls if call[0] == "libpng_check"]
    assert (
        "candy",
        (
            "Cowsay",
            "I still have an unrepaired misplaced chunk on the table. No Kraken snack until that mess is handled.",
            "bad",
        ),
        {},
    ) in calls
    assert calls[-1] == ("the_end", (), {})


def test_apply_no_next_false_positive_iend_infers_before_idat_repair_from_history():
    calls = []
    runtime, side_notes, state = no_next_runtime(
        calls,
        bad_missplaced=True,
        pandora_box={"ChunkOrder_Error_0:-Missplaced": {"Only_One_Tool": ["-Missplaced"]}},
        chunks_history=(b"PNG", b"IHDR", b"gAMA", b"IDAT", b"bKGD"),
    )

    result = fixit_felix_runtime.apply_no_next_false_positive_iend(
        runtime,
        fixit_felix.NoNextFalsePositiveIendDecision("the_good_place"),
    )

    assert result == (True, "good-place-result")
    assert state["eof"] is True
    assert side_notes == ["-Reached the end of file."]
    assert ("the_good_place", (b"IDAT", 3, b"bKGD"), {}) in calls
    assert not [call for call in calls if call[0] == "libpng_check"]
    assert not [call for call in calls if call[0] == "the_end"]


def test_apply_no_next_false_positive_iend_infers_before_plte_repair_from_lowercase_missplaced():
    calls = []
    runtime, side_notes, state = no_next_runtime(
        calls,
        bad_missplaced=True,
        pandora_box={
            "CheckChunkOrder_Error_0:-cHRM is missplaced must appears before PLTE Chunk": {
                "Only_One_Tool": ["-cHRM is missplaced must appears before PLTE Chunk"]
            }
        },
        chunks_history=(b"PNG", b"IHDR", b"gAMA", b"PLTE", b"cHRM", b"IDAT"),
    )

    result = fixit_felix_runtime.apply_no_next_false_positive_iend(
        runtime,
        fixit_felix.NoNextFalsePositiveIendDecision("the_good_place"),
    )

    assert result == (True, "good-place-result")
    assert state["eof"] is True
    assert side_notes == ["-Reached the end of file."]
    assert ("the_good_place", (b"PLTE", 3, b"cHRM"), {}) in calls
    assert not [call for call in calls if call[0] == "libpng_check"]
    assert not [call for call in calls if call[0] == "the_end"]


def test_apply_no_next_false_positive_iend_repairs_hist_before_plte_before_libpng():
    calls = []
    finding = "GetInfo_Error_0:-PLTE Chunk sPLT is missing.(hIST must be used after one of them)"
    runtime, side_notes, state = no_next_runtime(
        calls,
        pandora_box={finding: {}},
        chunks_history=(b"PNG", b"IHDR", b"gAMA", b"sBIT", b"hIST", b"PLTE", b"IDAT"),
    )

    result = fixit_felix_runtime.apply_no_next_false_positive_iend(
        runtime,
        fixit_felix.NoNextFalsePositiveIendDecision("libpng_check"),
    )

    assert result == (True, "good-place-result")
    assert state["eof"] is True
    assert side_notes == [
        "-Reached the end of file.",
        "-Stopped before libpng: unresolved findings remain: %s." % finding,
    ]
    assert (
        "candy",
        (
            "Cowsay",
            "Libpng might smile at the pixels, but Pandora still has unpaid invoices. No Kraken snack yet.",
            "bad",
        ),
        {},
    ) in calls
    assert (
        "candy",
        (
            "Cowsay",
            "I found a chunk-order repair path, so I am trying TheGoodPlace before calling this perfect.",
            "com",
        ),
        {},
    ) in calls
    assert ("the_good_place", (b"hIST", 4, b"PLTE"), {}) in calls
    assert not [call for call in calls if call[0] == "libpng_check"]
    assert not [call for call in calls if call[0] == "the_end"]


def test_apply_no_next_false_positive_iend_refuses_libpng_when_other_errors_remain():
    calls = []
    runtime, side_notes, state = no_next_runtime(
        calls,
        pandora_box={"CheckChunkOrder_Error_0:-cHRM is missplaced must appears before PLTE Chunk": {}},
    )

    result = fixit_felix_runtime.apply_no_next_false_positive_iend(
        runtime,
        fixit_felix.NoNextFalsePositiveIendDecision("libpng_check"),
    )

    assert result == (False, None)
    assert state["eof"] is True
    assert side_notes == [
        "-Reached the end of file.",
        "-Stopped before libpng: unresolved findings remain: "
        "CheckChunkOrder_Error_0:-cHRM is missplaced must appears before PLTE Chunk.",
    ]
    assert (
        "candy",
        ("Cowsay", messages.UNIMPLEMENTED_REPAIR_ROUTE_MESSAGE, "bad"),
        {},
    ) in calls
    assert not [call for call in calls if call[0] == "libpng_check"]
    assert calls[-1] == ("the_end", (), {})


def test_apply_no_next_false_positive_iend_reports_unimplemented_non_order_error():
    calls = []
    finding = "GetInfo_Error_0:-iTXt Compression Flag must be 0 or 1"
    runtime, side_notes, state = no_next_runtime(
        calls,
        pandora_box={finding: {}},
    )

    result = fixit_felix_runtime.apply_no_next_false_positive_iend(
        runtime,
        fixit_felix.NoNextFalsePositiveIendDecision("libpng_check"),
    )

    assert result == (False, None)
    assert state["eof"] is True
    assert side_notes == [
        "-Reached the end of file.",
        "-Stopped before libpng: unresolved findings remain: %s." % finding,
    ]
    assert (
        "candy",
        (
            "Cowsay",
            "Libpng might smile at the pixels, but Pandora still has unpaid invoices. No Kraken snack yet.",
            "bad",
        ),
        {},
    ) in calls
    assert (
        "candy",
        ("Cowsay", messages.UNIMPLEMENTED_REPAIR_ROUTE_MESSAGE, "bad"),
        {},
    ) in calls
    assert not [call for call in calls if call[0] in ("libpng_check", "the_good_place")]
    assert calls[-1] == ("the_end", (), {})


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


def test_apply_no_next_uses_idat_chain_batch_before_iend_append():
    calls = []
    finding = "CheckLength_Error_0:-No NextChunk"
    runtime, side_notes, _state = no_next_runtime(
        calls,
        data_hex=idat_chain_candidate_hex(),
    )

    result = fixit_felix_runtime.apply_no_next_chunk(
        runtime,
        fixit_felix.NoNextChunkDecision("append_missing_iend", b"IDAT", b"IDAT", "12"),
        finding,
        "IDAT_Tool_",
        no_next_tools(),
    )

    assert result == (True, "write-result")
    assert not [call for call in calls if call[0] == "dummy_chunk"]
    assert any(call[0] == "write_clone" for call in calls)
    assert "-Repair hypothesis tried: IDAT chain header repair." in side_notes


def test_apply_no_next_uses_deflate_probe_when_idat_chain_is_aligned_but_stream_is_bad():
    calls = []
    finding = "CheckLength_Error_0:-No NextChunk"
    runtime, side_notes, _state = no_next_runtime(
        calls,
        data_hex=idat_chain_aligned_bad_deflate_hex(),
    )

    result = fixit_felix_runtime.apply_no_next_chunk(
        runtime,
        fixit_felix.NoNextChunkDecision("append_missing_iend", b"IDAT", b"IDAT", "12"),
        finding,
        "IDAT_Tool_",
        no_next_tools(),
    )

    assert result == (False, None)
    assert not [call for call in calls if call[0] == "dummy_chunk"]
    assert not [call for call in calls if call[0] == "write_clone"]
    assert any(note.startswith("-IDAT stream diagnosis: status=corrupt_deflate") for note in side_notes)
    assert "-IDAT deflate header probe found no clone-worthy scanline progress." in side_notes
    assert "-IDAT wide deflate probes skipped: header probe produced no usable scanline." in side_notes


def test_apply_no_next_does_not_append_iend_when_nearby_already_found_one():
    calls = []
    finding = "CheckLength_Error_0:-No NextChunk"
    runtime, side_notes, state = no_next_runtime(calls, data_hex="aabbccddff")
    state["nearby_found_later_iend"] = {
        "sample_name": "sample.png",
        "idat_count": 2,
        "double_check": True,
    }

    result = fixit_felix_runtime.apply_no_next_chunk(
        runtime,
        fixit_felix.NoNextChunkDecision("append_missing_iend", b"IDAT", b"IDAT", "12"),
        finding,
        "IDAT_Tool_",
        no_next_tools(),
    )

    assert result == (False, None)
    assert side_notes == [
        "-Skipped adding IEND chunk: NearbyChunk already found an IEND later."
    ]
    assert ("set_skip_bad_no_next_chunk", (True,), {}) in calls
    assert not [call for call in calls if call[0] == "dummy_chunk"]


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


def test_apply_no_next_without_idat_evidence_stops_terminally():
    calls = []
    finding = "CheckLength_Error_0:-No NextChunk"
    runtime, side_notes, state = no_next_runtime(
        calls,
        pandora_box={finding: {"gAMA_Tool_0": b"gAMA"}},
        chunks_history=(b"IHDR", b"gAMA"),
    )

    result = fixit_felix_runtime.apply_no_next_chunk(
        runtime,
        fixit_felix.NoNextChunkDecision("ask_length_probe", b"gAMA", b"gAMA", "4"),
        finding,
        "gAMA_Tool_",
        no_next_tools(chunk_type=b"gAMA", chunk_length="4", previous_chunk=b"IHDR"),
    )

    assert result == (False, None)
    assert side_notes == [
        "-Critical Chunk b'IDAT' is Missing",
        "-Terminal PNG error: no IDAT chunk found; no image data to repair.",
    ]
    assert state["eof"] is True
    assert ("set_skip_bad_no_next_chunk", (True,), {}) in calls
    assert ("set_eof", (True,), {}) in calls
    assert calls[-1] == ("the_end", (), {})
    assert not [call for call in calls if call[0] == "question"]
    assert not [call for call in calls if call[0] == "nearby_chunk"]
    assert any(
        call[0] == "candy"
        and call[1][0] == "Cowsay"
        and "No IDAT chunk, no image stream" in call[1][1]
        for call in calls
    )


def test_apply_no_next_raw_idat_bytes_keep_length_probe_available():
    calls = []
    finding = "CheckLength_Error_0:-No NextChunk"
    runtime, side_notes, _state = no_next_runtime(
        calls,
        data_hex="89504e470d0a1a0a0000000467414d410000000049444154",
        chunks_history=(b"IHDR", b"gAMA"),
    )

    result = fixit_felix_runtime.apply_no_next_chunk(
        runtime,
        fixit_felix.NoNextChunkDecision("ask_length_probe", b"gAMA", b"gAMA", "4"),
        finding,
        "gAMA_Tool_",
        no_next_tools(chunk_type=b"gAMA", chunk_length="4", previous_chunk=b"IHDR"),
    )

    assert result == (True, "nearby-result")
    assert side_notes == ["-End of File Reached but IEND Chunk is missing"]
    assert calls[-1] == ("nearby_chunk", (b"gAMA", "4", b"IHDR", False, finding), {})


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
        "GetSpec": callback("GetSpec"),
        "Product": callback("Product"),
        "Loadingbar": callback("Loadingbar"),
        "Minibar": callback("Minibar"),
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
        "FILE_Origin": "source.png",
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
    assert wrong_crc.side_notes is side_notes
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
    assert wrong_name.write_clone is namespace["WriteClone"]
    assert wrong_name.set_skip_bad_next_name is namespace["FixItFelix_Set_Skip_Bad_Next_Name"]
    assert wrong_name.set_skip_bad_current_name is namespace["FixItFelix_Set_Skip_Bad_Current_Name"]
    assert wrong_name.bad_ancillary() is False
    namespace["Bad_Ancillary"] = True
    assert wrong_name.bad_ancillary() is True
    assert wrong_name.pandora_box is pandora_box
    assert wrong_name.cornucopia is cornucopia
    assert wrong_name.data_hex == "001122"

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
    assert automatic.question is namespace["Question"]
    assert automatic.data_hex == "001122"
    assert automatic.pandora_box is pandora_box
    assert automatic.get_spec is namespace["GetSpec"]
    assert automatic.product is namespace["Product"]
    assert automatic.loadingbar is namespace["Loadingbar"]
    assert automatic.minibar is namespace["Minibar"]
    assert automatic.file_origin == "source.png"


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
        (
            "Apply repair prompts before unproven cHRM inference",
            test_apply_repair_prompts_before_unproven_chrm_inference,
        ),
        (
            "Apply repair removes short cHRM when inference declined",
            test_apply_repair_removes_short_chrm_when_inference_declined,
        ),
        (
            "Apply repair explains IHDR rebuild",
            test_apply_repair_explains_ihdr_rebuild_before_writing_clone,
        ),
        (
            "Apply repair explains IHDR value rebuild without CRC noise",
            test_apply_repair_explains_ihdr_value_rebuild_without_crc_noise,
        ),
        (
            "Apply repair rejects invalid IHDR rebuild",
            test_apply_repair_rejects_invalid_ihdr_rebuild_before_clone,
        ),
        (
            "IHDR stored CRC brute force uses loader",
            test_try_ihdr_stored_crc_bruteforce_uses_loader_and_writes_valid_candidate,
        ),
        (
            "IHDR stored CRC brute force decline",
            test_try_ihdr_stored_crc_bruteforce_decline_falls_back_to_rebuild,
        ),
        ("Apply gAMA zero discards false positive", test_apply_gama_zero_discards_false_positive_and_returns_legacy_target),
        ("Apply gAMA zero rejects unknown action", test_apply_gama_zero_rejects_unknown_action),
        ("Apply critical miss emits and pauses", test_apply_critical_miss_emits_and_pauses_on_debug_action),
        ("Apply critical miss continue skips pause", test_apply_critical_miss_continue_does_not_pause),
        ("Apply critical miss rejects unknown action", test_apply_critical_miss_rejects_unknown_action),
        (
            "Repeated deferred repair message templates",
            test_repeated_deferred_repair_message_templates_are_adaptable,
        ),
        ("Apply wrong CRC easy answer saves clone", test_apply_wrong_crc_easy_answer_saves_clone),
        (
            "Apply wrong CRC easy decline keeps skip none",
            test_apply_wrong_crc_easy_decline_then_final_decline_keeps_skip_none_and_saves,
        ),
        ("Deferred IDAT CRC route ignores error counter", test_deferred_idat_crc_route_key_ignores_error_counter),
        (
            "Deferred IDAT CRC route records structural state",
            test_deferred_idat_crc_route_records_structural_state,
        ),
        ("Apply wrong CRC skips deferred IDAT route", test_apply_wrong_crc_skips_question_for_deferred_idat_route),
        (
            "Apply wrong CRC records failed IDAT route",
            test_apply_wrong_crc_records_failed_idat_crc_route_when_patch_still_breaks,
        ),
        (
            "Apply wrong CRC defers invalid IDAT stream",
            test_apply_wrong_crc_defers_crc_only_when_idat_stream_stays_invalid,
        ),
        (
            "Apply wrong CRC writes improved IDAT deflate probe",
            test_apply_wrong_crc_writes_improved_deflate_probe_instead_of_crc_clone,
        ),
        (
            "Apply wrong CRC heavy IDAT deflate probe loadingbar",
            test_apply_wrong_crc_uses_heavy_probe_loadingbar_after_quick_probe_fails,
        ),
        (
            "Apply wrong CRC heavy IDAT deflate probe decline",
            test_apply_wrong_crc_declines_heavy_probe_without_loadingbar_or_clone,
        ),
        ("Apply wrong CRC other errors defers", test_apply_wrong_crc_other_errors_defers_to_chunk_story),
        (
            "Apply wrong CRC Cornucopia debug path",
            test_apply_wrong_crc_already_in_cornucopia_uses_debug_emit_without_tools,
        ),
        ("Apply wrong CRC rejects missing tools", test_apply_wrong_crc_rejects_missing_tools_for_action),
        ("Apply wrong CRC rejects unknown action", test_apply_wrong_crc_rejects_unknown_action),
        ("Wrong chunk name route ignores error counter", test_wrong_chunk_name_route_key_ignores_error_counter),
        (
            "Wrong chunk name route records structural state",
            test_wrong_chunk_name_route_records_structural_state,
        ),
        (
            "Wrong chunk name before first IDAT stays available",
            test_wrong_chunk_name_before_first_idat_does_not_block_name_repair,
        ),
        (
            "Apply wrong chunk name length probe accepts",
            test_apply_wrong_chunk_name_length_probe_accepts_nearby_chunk,
        ),
        (
            "Apply wrong chunk name length probe declines",
            test_apply_wrong_chunk_name_length_probe_decline_then_bruteforce_decline_sets_skips,
        ),
        ("Apply wrong chunk name bruteforce accepts", test_apply_wrong_chunk_name_bruteforce_accepts_brute_chunk),
        (
            "Apply wrong chunk name skips known route",
            test_apply_wrong_chunk_name_bruteforce_skips_known_route_without_question,
        ),
        (
            "Apply wrong chunk name IDAT chain batch",
            test_apply_wrong_chunk_name_uses_idat_chain_batch_before_bruteforce,
        ),
        (
            "Apply wrong chunk name probes after aligned bad stream",
            test_apply_wrong_chunk_name_uses_deflate_probe_when_aligned_stream_is_bad,
        ),
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
        (
            "Apply no-next false positive infers before-IDAT repair",
            test_apply_no_next_false_positive_iend_infers_before_idat_repair_from_history,
        ),
        (
            "Apply no-next false positive infers before-PLTE repair",
            test_apply_no_next_false_positive_iend_infers_before_plte_repair_from_lowercase_missplaced,
        ),
        (
            "Apply no-next false positive repairs hIST before PLTE",
            test_apply_no_next_false_positive_iend_repairs_hist_before_plte_before_libpng,
        ),
        (
            "Apply no-next false positive blocks libpng with pending errors",
            test_apply_no_next_false_positive_iend_refuses_libpng_when_other_errors_remain,
        ),
        ("Apply no-next wrong IEND length ends", test_apply_no_next_wrong_iend_length_records_note_and_ends),
        ("Apply no-next appends dummy at CRC tail", test_apply_no_next_append_missing_iend_uses_dummy_at_crc_tail),
        (
            "Apply no-next IDAT chain batch",
            test_apply_no_next_uses_idat_chain_batch_before_iend_append,
        ),
        (
            "Apply no-next probes after aligned bad stream",
            test_apply_no_next_uses_deflate_probe_when_idat_chain_is_aligned_but_stream_is_bad,
        ),
        (
            "Apply no-next skips append after nearby IEND",
            test_apply_no_next_does_not_append_iend_when_nearby_already_found_one,
        ),
        ("Apply no-next length probe routes nearby", test_apply_no_next_ask_length_probe_routes_to_nearby_chunk),
        ("Apply no-next without IDAT evidence ends", test_apply_no_next_without_idat_evidence_stops_terminally),
        (
            "Apply no-next raw IDAT keeps probe",
            test_apply_no_next_raw_idat_bytes_keep_length_probe_available,
        ),
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
