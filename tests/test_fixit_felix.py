#!/usr/bin/env python3
import struct
import sys
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import fixit_felix
from chunklate.png import IEND_CHUNK, PNG_SIGNATURE, build_png_chunk, iter_chunks, validate_png_structure


REPAIR_FIXTURES = ROOT / "Png_Errors_handled_by_Chunklate_So_Far"


def read_fixture(name):
    return (REPAIR_FIXTURES / name).read_bytes()


def build_rgb_png(width, height, filtered_scanlines, *, idat_data=None):
    ihdr = struct.pack("!IIBBBBB", width, height, 8, 2, 0, 0, 0)
    if idat_data is None:
        idat_data = zlib.compress(filtered_scanlines)
    return (
        PNG_SIGNATURE
        + build_png_chunk(b"IHDR", ihdr)
        + build_png_chunk(b"IDAT", idat_data)
        + IEND_CHUNK
    )


def test_route_finding_keeps_legacy_handler_order():
    assert fixit_felix.route_finding("Checksum_Error_0:Wrong Crc", skip_bad_crc=False).handler == "wrong_crc"
    assert fixit_felix.route_finding("Libpng_Error_0:libpng error: bad adaptive filter", skip_bad_crc=False).handler == "libpng_error"
    assert fixit_felix.route_finding("CheckChunkName_Error_0:has Wrong Chunk name at offset: 42", skip_bad_crc=False).handler == "wrong_chunk_name"
    assert fixit_felix.route_finding("CheckLength_Error_0:-No NextChunk", skip_bad_crc=False).handler == "no_next_chunk"
    assert fixit_felix.route_finding("GetInfo_Error_0:gAMA Chunk of 0 is Useless", skip_bad_crc=False).handler == "gama_zero"
    assert fixit_felix.route_finding("CheckChunkOrder_Error_0:Critical", skip_bad_crc=False).handler == "critical_miss"


def test_route_finding_preserves_skip_bad_crc_fallthrough():
    route = fixit_felix.route_finding("Checksum_Error_0:Wrong Crc", skip_bad_crc=True)

    assert route.handler == "critical_miss"


def test_gama_zero_false_positive_keeps_legacy_note():
    fix = fixit_felix.gama_zero_false_positive("GetInfo_Error_0:gAMA Chunk of 0 is Useless")

    assert fix.finding == "GetInfo_Error_0:gAMA Chunk of 0 is Useless"
    assert fix.note == "-Found False-Positive :[Error:-GetInfo_Error_0:gAMA Chunk of 0 is Useless]."


def test_gama_zero_decision_discards_false_positive():
    decision = fixit_felix.gama_zero_decision("GetInfo_Error_0:gAMA Chunk of 0 is Useless")

    assert decision.action == "discard_false_positive"
    assert decision.false_positive.finding == "GetInfo_Error_0:gAMA Chunk of 0 is Useless"
    assert decision.false_positive.note == "-Found False-Positive :[Error:-GetInfo_Error_0:gAMA Chunk of 0 is Useless]."


def test_libpng_error_decision_orders_solved_and_terminal_cases():
    assert (
        fixit_felix.libpng_error_decision("libpng error: anything", solved=True, skip_bad_libpng=False).action
        == "save_existing_solution"
    )
    assert (
        fixit_felix.libpng_error_decision("libpng error: Not enough image data", solved=False, skip_bad_libpng=False).action
        == "not_enough_image_data"
    )
    assert (
        fixit_felix.libpng_error_decision("libpng error: bad adaptive filter", solved=False, skip_bad_libpng=True).action
        == "skip"
    )
    assert (
        fixit_felix.libpng_error_decision("libpng error: bad adaptive filter", solved=False, skip_bad_libpng=False).action
        == "ask_relics"
    )


def test_critical_miss_decision_keeps_debug_pause_gate():
    assert (
        fixit_felix.critical_miss_decision(
            "CheckChunkOrder_Error_0:Critical",
            debug=True,
            pause_debug=True,
        ).action
        == "pause_debug"
    )
    assert (
        fixit_felix.critical_miss_decision(
            "CheckChunkOrder_Error_0:Critical",
            debug=True,
            pause_debug=False,
        ).action
        == "continue"
    )
    assert (
        fixit_felix.critical_miss_decision(
            "CheckChunkOrder_Error_0:Critical",
            debug=False,
            pause_debug=True,
        ).action
        == "continue"
    )


def test_wrong_crc_decision_keeps_easy_fix_before_other_errors():
    solved = fixit_felix.wrong_crc_decision("Checksum_Error_0:Wrong Crc", solved=True, pandora_box_len=1)
    easy = fixit_felix.wrong_crc_decision("Checksum_Error_0:Wrong Crc", solved=False, pandora_box_len=1)
    crowded = fixit_felix.wrong_crc_decision("Checksum_Error_0:Wrong Crc", solved=False, pandora_box_len=4)

    assert solved.action == "already_in_cornucopia"
    assert solved.other_error_count == 0
    assert easy.action == "ask_easy_crc_fix"
    assert easy.other_error_count == 0
    assert crowded.action == "ask_other_errors_first"
    assert crowded.other_error_count == 3


def test_wrong_chunk_name_decision_keeps_length_probe_before_bruteforce():
    assert (
        fixit_felix.wrong_chunk_name_decision(
            "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42 and length is not the same than before.",
            solved=False,
            bad_crc=True,
        ).action
        == "ask_length_probe"
    )
    assert (
        fixit_felix.wrong_chunk_name_decision(
            "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42",
            solved=False,
            bad_crc=True,
        ).action
        == "ask_bruteforce"
    )
    assert (
        fixit_felix.wrong_chunk_name_decision(
            "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42",
            solved=True,
            bad_crc=False,
        ).action
        == "save_existing_solution"
    )


def test_no_next_chunk_decision_orders_iend_and_recovery_paths():
    assert (
        fixit_felix.no_next_chunk_decision(
            current_chunk=b"IEND",
            chunk_type=b"IEND",
            chunk_length="0",
            bad_critical=False,
        ).action
        == "false_positive_iend"
    )
    assert (
        fixit_felix.no_next_chunk_decision(
            current_chunk=b"IDAT",
            chunk_type=b"IEND",
            chunk_length="1",
            bad_critical=False,
        ).action
        == "wrong_iend_length"
    )
    assert (
        fixit_felix.no_next_chunk_decision(
            current_chunk=b"IDAT",
            chunk_type=b"IDAT",
            chunk_length="12",
            bad_critical=True,
        ).action
        == "append_missing_iend"
    )
    assert (
        fixit_felix.no_next_chunk_decision(
            current_chunk=b"IDAT",
            chunk_type=b"IDAT",
            chunk_length="12",
            bad_critical=False,
        ).action
        == "ask_length_probe"
    )


def test_no_next_false_positive_iend_decision_routes_tail_cases():
    data_hex = "00aa" + fixit_felix.GOOD_IEND_HEX

    assert (
        fixit_felix.no_next_false_positive_iend_decision(
            data_hex,
            bad_missplaced=False,
            has_missplaced_finding=False,
        ).action
        == "libpng_check"
    )
    assert (
        fixit_felix.no_next_false_positive_iend_decision(
            data_hex,
            bad_missplaced=True,
            has_missplaced_finding=True,
        ).action
        == "the_good_place"
    )
    assert (
        fixit_felix.no_next_false_positive_iend_decision(
            data_hex,
            bad_missplaced=True,
            has_missplaced_finding=False,
        ).action
        == "continue"
    )


def test_no_next_false_positive_iend_decision_cuts_or_ends():
    extra = "abcdef"
    cut_decision = fixit_felix.no_next_false_positive_iend_decision(
        "0011" + fixit_felix.GOOD_IEND_HEX + extra,
        bad_missplaced=False,
        has_missplaced_finding=False,
    )
    bad_ending = fixit_felix.no_next_false_positive_iend_decision(
        "001122334455",
        bad_missplaced=False,
        has_missplaced_finding=False,
    )

    assert cut_decision.action == "write_clean_iend_cut"
    assert cut_decision.cut_hex == "0011" + fixit_felix.GOOD_IEND_HEX
    assert bad_ending.action == "end_not_regular_iend"


def test_no_next_append_iend_decision_routes_exceeding_bytes():
    empty = fixit_felix.no_next_append_iend_decision("aabbccdd", crc_offset=0)
    partial_iend = fixit_felix.no_next_append_iend_decision(
        "aabbccdd" + fixit_felix.GOOD_IEND_HEX[:4],
        crc_offset=0,
    )
    garbage = fixit_felix.no_next_append_iend_decision(
        "aabbccddff",
        crc_offset=0,
    )
    long_garbage = fixit_felix.no_next_append_iend_decision(
        "aabbccdd" + ("ff" * 20),
        crc_offset=0,
    )
    iend_inside = fixit_felix.no_next_append_iend_decision(
        "aabbccdd" + ("ff" * 13) + fixit_felix.GOOD_IEND_HEX,
        crc_offset=0,
    )

    assert empty.action == "dummy_at_eof"
    assert partial_iend.action == "dummy_at_eof"
    assert partial_iend.exceeding == fixit_felix.GOOD_IEND_HEX[:4]
    assert garbage.action == "dummy_at_crc_tail"
    assert long_garbage.action == "dummy_at_crc_tail"
    assert iend_inside.action == "end_iend_inside_exceeding"


def test_applied_repair_formats_legacy_note_and_save_suffix():
    class Repair:
        data = b"\x89PNG"
        strategy = "Some repair strategy"

    applied = fixit_felix.applied_repair(Repair())

    assert applied.data_hex == "89504e47"
    assert applied.note == "-FixItFelix:Some repair strategy."
    assert applied.save_suffix == "-Some repair strategy."


def test_applied_repair_adds_ihdr_metadata_when_available():
    class Repair:
        data = b"\x89PNG"
        strategy = "rebuilt missing IHDR from IDAT scanline size"
        width = 32
        height = 32
        bit_depth = 8
        color_type = 3
        strict_candidate_count = 4
        selection_score = (1, 1, 1, 1024, 0)

    applied = fixit_felix.applied_repair(Repair())

    assert applied.data_hex == "89504e47"
    assert "-FixItFelix:rebuilt missing IHDR from IDAT scanline size." in applied.note
    assert "-FixItFelix:Selected IHDR 32x32, bit depth 8, color type 3." in applied.note
    assert "-FixItFelix:strict candidates: 4." in applied.note
    assert "-FixItFelix:selection score: (1, 1, 1, 1024, 0)." in applied.note
    assert applied.save_suffix == "-rebuilt missing IHDR from IDAT scanline size."


def test_automatic_repair_order_keeps_legacy_priority():
    assert fixit_felix.automatic_repair_order() == (
        "color_profile_cleanup",
        "plte_cleanup",
        "known_chunk_type_case",
        "unknown_private_critical_removal",
        "missing_chunk_data_byte",
        "ihdr_rebuild",
        "partial_idat_blackfill",
    )


def test_effective_pandora_box_len_preserves_bad_next_name_adjustment():
    findings = {
        "CheckChunkName_Error_0:has Wrong Chunk name after Chunk[b'IHDR']": {},
        "Checksum_Error_0:Wrong Crc": {},
    }

    assert fixit_felix.effective_pandora_box_len(findings, bad_next_name=False) == 2
    assert fixit_felix.effective_pandora_box_len(findings, bad_next_name=True) == 1


def test_repair_work_items_runs_automatic_repairs_before_pandorabox_routes():
    findings = {
        "Checksum_Error_0:Wrong Crc": {},
        "Libpng_Error_0:libpng error: bad adaptive filter": {},
        "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42": {},
    }

    items = fixit_felix.repair_work_items(findings, skip_bad_crc=False)

    automatic_count = len(fixit_felix.automatic_repair_order())
    assert [item.kind for item in items[:automatic_count]] == ["automatic_repair"] * automatic_count
    assert [item.handler for item in items[:automatic_count]] == list(fixit_felix.automatic_repair_order())
    assert [(item.kind, item.handler, item.finding) for item in items[automatic_count:]] == [
        ("finding", "wrong_crc", "Checksum_Error_0:Wrong Crc"),
        ("finding", "libpng_error", "Libpng_Error_0:libpng error: bad adaptive filter"),
        ("finding", "wrong_chunk_name", "CheckChunkName_Error_0:has Wrong Chunk name at offset: 42"),
    ]


def test_repair_work_items_respects_skip_bad_crc_route_fallthrough():
    findings = {"Checksum_Error_0:Wrong Crc": {}}

    items = fixit_felix.repair_work_items(findings, skip_bad_crc=True)

    assert items[-1].kind == "finding"
    assert items[-1].handler == "critical_miss"
    assert items[-1].finding == "Checksum_Error_0:Wrong Crc"


def test_run_repair_work_items_returns_first_automatic_repair_result():
    calls = []
    runtime = fixit_felix.FixItFelixRuntime(
        try_automatic_repair=lambda handler: calls.append(("auto", handler)) or (
            "repaired" if handler == "plte_cleanup" else None
        ),
        apply_finding_work_item=lambda *args: calls.append(("finding", args)) or (False, None),
    )

    result = fixit_felix.run_repair_work_items(
        runtime,
        (
            fixit_felix.FixItFelixWorkItem("automatic_repair", "color_profile_cleanup"),
            fixit_felix.FixItFelixWorkItem("automatic_repair", "plte_cleanup"),
            fixit_felix.FixItFelixWorkItem("finding", "wrong_crc", "Checksum_Error_0:Wrong Crc"),
        ),
        chkd="IDAT_Tool_",
        pandora_box_len=1,
        chunk=b"IDAT",
    )

    assert result == fixit_felix.FixItFelixRunResult(True, "repaired")
    assert calls == [
        ("auto", "color_profile_cleanup"),
        ("auto", "plte_cleanup"),
    ]


def test_run_repair_work_items_dispatches_findings_after_empty_automatic_repairs():
    calls = []

    def apply_finding(work_item, chkd, pandora_box_len, chunk):
        calls.append((work_item, chkd, pandora_box_len, chunk))
        return True, "handled"

    runtime = fixit_felix.FixItFelixRuntime(
        try_automatic_repair=lambda handler: calls.append(("auto", handler)) or None,
        apply_finding_work_item=apply_finding,
    )
    work_item = fixit_felix.FixItFelixWorkItem(
        "finding",
        "wrong_crc",
        "Checksum_Error_0:Wrong Crc",
    )

    result = fixit_felix.run_repair_work_items(
        runtime,
        (
            fixit_felix.FixItFelixWorkItem("automatic_repair", "color_profile_cleanup"),
            work_item,
        ),
        chkd="IDAT_Tool_",
        pandora_box_len=2,
        chunk=b"IDAT",
    )

    assert result == fixit_felix.FixItFelixRunResult(True, "handled")
    assert calls == [
        ("auto", "color_profile_cleanup"),
        (work_item, "IDAT_Tool_", 2, b"IDAT"),
    ]


def test_run_repair_work_items_reports_no_result_when_nothing_handles():
    runtime = fixit_felix.FixItFelixRuntime(
        try_automatic_repair=lambda handler: None,
        apply_finding_work_item=lambda *args: (False, None),
    )

    result = fixit_felix.run_repair_work_items(
        runtime,
        (fixit_felix.FixItFelixWorkItem("finding", "critical_miss", "unknown"),),
        chkd="IDAT_Tool_",
        pandora_box_len=1,
        chunk=b"IDAT",
    )

    assert result == fixit_felix.FixItFelixRunResult(False)


def test_dispatch_action_calls_matching_handler_with_args():
    calls = []

    def handle_action(*args):
        calls.append(args)
        return "handled"

    result = fixit_felix.dispatch_action(
        {"save_existing_solution": handle_action},
        "save_existing_solution",
        "FixItFelix libpng action",
        "decision",
        "finding",
        "IDAT_Tool_",
    )

    assert result == "handled"
    assert calls == [("decision", "finding", "IDAT_Tool_")]


def test_dispatch_action_rejects_unknown_handler_with_legacy_message():
    try:
        fixit_felix.dispatch_action(
            {},
            "ask_easy_crc_fix",
            "FixItFelix wrong-CRC action",
            "decision",
        )
    except ValueError as exc:
        assert str(exc) == "Unknown FixItFelix wrong-CRC action: ask_easy_crc_fix"
    else:
        raise AssertionError("Expected ValueError for unknown FixItFelix action")


def test_dispatch_finding_work_item_calls_matching_handler():
    calls = []
    work_item = fixit_felix.FixItFelixWorkItem(
        "finding",
        "wrong_crc",
        "Checksum_Error_0:Wrong Crc",
    )

    def handle_wrong_crc(item, chkd, pandora_box_len, chunk):
        calls.append((item, chkd, pandora_box_len, chunk))
        return True, "handled"

    result = fixit_felix.dispatch_finding_work_item(
        {"wrong_crc": handle_wrong_crc},
        work_item,
        "IDAT_Tool_",
        3,
        b"IDAT",
    )

    assert result == (True, "handled")
    assert calls == [(work_item, "IDAT_Tool_", 3, b"IDAT")]


def test_dispatch_finding_work_item_rejects_unknown_handler():
    work_item = fixit_felix.FixItFelixWorkItem(
        "finding",
        "wrong_crc",
        "Checksum_Error_0:Wrong Crc",
    )

    try:
        fixit_felix.dispatch_finding_work_item(
            {},
            work_item,
            "IDAT_Tool_",
            1,
            b"IDAT",
        )
    except ValueError as exc:
        assert str(exc) == "Unknown FixItFelix finding handler: wrong_crc"
    else:
        raise AssertionError("Expected ValueError for unknown FixItFelix finding handler")


def test_tool_prefix_for_chunk_preserves_legacy_bytes_and_string_labels():
    assert fixit_felix.tool_prefix_for_chunk(b"IDAT") == "IDAT_Tool_"
    assert fixit_felix.tool_prefix_for_chunk("gAMA") == "gAMA_Tool_"


def test_color_profile_cleanup_requires_matching_finding():
    original = read_fixture("IncorrectSrgbProfile.png")

    assert fixit_felix.color_profile_cleanup(original, []) is None

    repaired = fixit_felix.color_profile_cleanup(original, ["libpng warning: known incorrect sRGB profile"])

    assert repaired is not None
    assert b"iCCP" not in {chunk.chunk_type for chunk in iter_chunks(repaired.data)}


def test_plte_cleanup_requires_noninteractive_mode_and_plte_finding():
    original = read_fixture("PLTE_Empty_Bad_Crc.png")

    assert fixit_felix.plte_cleanup(original, ["PLTE"], auto=False, nodialogue=False, max_saves=None) is None
    assert fixit_felix.plte_cleanup(original, ["Wrong Crc"], auto=True, nodialogue=False, max_saves=None) is None

    repaired = fixit_felix.plte_cleanup(original, ["PLTE"], auto=False, nodialogue=False, max_saves=1)

    assert repaired is not None
    assert b"PLTE" not in {chunk.chunk_type for chunk in iter_chunks(repaired.data)}


def test_missing_chunk_data_byte_requires_crc_or_no_next_finding():
    original = read_fixture("Good-Chunk-lenght-Missing-Bit.png")

    assert fixit_felix.missing_chunk_data_byte(original, []) is None

    repaired = fixit_felix.missing_chunk_data_byte(original, ["Checksum_Error_0:Wrong Crc"])

    assert repaired is not None
    assert repaired.chunk_name == "PLTE"


def test_known_chunk_type_case_requires_wrong_ancillary_finding():
    original = read_fixture("chunk_private_critical.png")

    assert fixit_felix.known_chunk_type_case(original, [], [b"gAMA"]) is None

    repaired = fixit_felix.known_chunk_type_case(
        original,
        ["CheckChunkName_Error_0:Wrong Ancillary in known Chunk name"],
        [b"gAMA"],
    )

    assert repaired is not None
    assert repaired.original_name == "GaMA"
    assert repaired.repaired_name == "gAMA"


def test_unknown_private_critical_removal_is_standalone_salvage():
    original = read_fixture("Unhandled-Critical-Chunk.png")

    repaired = fixit_felix.unknown_private_critical_removal(original, [b"IHDR", b"gAMA", b"PLTE", b"IDAT", b"IEND"])

    assert repaired is not None
    assert repaired.removed_chunks == ("QpZZ",)


def test_ihdr_rebuild_requires_ihdr_finding():
    original = read_fixture("IHDR-Wrong-Quick.png")

    assert fixit_felix.ihdr_rebuild(original, ["Wrong Crc"]) is None

    repaired = fixit_felix.ihdr_rebuild(original, ["GetInfo_Error_0:IHDR Width"])

    assert repaired is not None
    assert next(iter_chunks(repaired.data)).chunk_type == b"IHDR"


def test_partial_idat_blackfill_requires_idat_finding_and_partial_stream():
    filtered = b"".join(b"\x00" + bytes((row, row, row)) for row in range(10))
    compressed = zlib.compress(filtered)
    original = None
    for cut in range(2, len(compressed)):
        candidate = build_rgb_png(1, 10, filtered, idat_data=compressed[:cut])
        repaired = fixit_felix.partial_idat_blackfill(candidate, ["IDAT"])
        if repaired is not None:
            original = candidate
            break

    assert original is not None
    assert fixit_felix.partial_idat_blackfill(original, ["Wrong Crc"]) is None

    repaired = fixit_felix.partial_idat_blackfill(original, ["libpng error: bad adaptive filter in IDAT"])

    assert repaired is not None
    assert "partial-idat-blackfill" in repaired.strategy
    assert validate_png_structure(repaired.data).ok


def test_automatic_repair_dispatches_partial_idat_blackfill_last_handler():
    original = read_fixture("IDAT_Partial_Blackfill.png")

    repaired = fixit_felix.automatic_repair(
        "partial_idat_blackfill",
        original,
        ["Checksum_Error_0:Wrong Crc b'IDAT'"],
        known_chunk_types=[b"IHDR", b"IDAT", b"IEND"],
        auto=False,
        nodialogue=False,
        max_saves=None,
    )

    assert repaired is not None
    assert "partial-idat-blackfill" in repaired.strategy
    assert validate_png_structure(repaired.data).ok


def test_automatic_repair_dispatch_rejects_unknown_handler():
    try:
        fixit_felix.automatic_repair(
            "unknown",
            b"",
            [],
            known_chunk_types=[],
            auto=False,
            nodialogue=False,
            max_saves=None,
        )
    except ValueError as exc:
        assert "Unknown FixItFelix automatic repair" in str(exc)
    else:
        raise AssertionError("automatic_repair accepted an unknown handler")


def main():
    checks = [
        ("Route finding keeps legacy handler order", test_route_finding_keeps_legacy_handler_order),
        ("Route finding preserves skip-bad-crc fallthrough", test_route_finding_preserves_skip_bad_crc_fallthrough),
        ("gAMA zero false positive keeps legacy note", test_gama_zero_false_positive_keeps_legacy_note),
        ("gAMA zero decision discards false positive", test_gama_zero_decision_discards_false_positive),
        ("Libpng error decision orders solved and terminal cases", test_libpng_error_decision_orders_solved_and_terminal_cases),
        ("Critical miss decision keeps debug pause gate", test_critical_miss_decision_keeps_debug_pause_gate),
        ("Wrong CRC decision keeps easy fix before other errors", test_wrong_crc_decision_keeps_easy_fix_before_other_errors),
        ("Wrong chunk name decision keeps length probe before bruteforce", test_wrong_chunk_name_decision_keeps_length_probe_before_bruteforce),
        ("No-next-chunk decision orders IEND and recovery paths", test_no_next_chunk_decision_orders_iend_and_recovery_paths),
        ("No-next false-positive IEND routes tail cases", test_no_next_false_positive_iend_decision_routes_tail_cases),
        ("No-next false-positive IEND cuts or ends", test_no_next_false_positive_iend_decision_cuts_or_ends),
        ("No-next append IEND routes exceeding bytes", test_no_next_append_iend_decision_routes_exceeding_bytes),
        ("Applied repair formats legacy note and save suffix", test_applied_repair_formats_legacy_note_and_save_suffix),
        ("Applied repair adds IHDR metadata", test_applied_repair_adds_ihdr_metadata_when_available),
        ("Automatic repair order keeps legacy priority", test_automatic_repair_order_keeps_legacy_priority),
        ("Effective PandoraBox len preserves Bad_Next_Name adjustment", test_effective_pandora_box_len_preserves_bad_next_name_adjustment),
        ("Repair work items run automatic repairs first", test_repair_work_items_runs_automatic_repairs_before_pandorabox_routes),
        ("Repair work items respect skip-bad-crc fallthrough", test_repair_work_items_respects_skip_bad_crc_route_fallthrough),
        ("Run work items returns automatic repair", test_run_repair_work_items_returns_first_automatic_repair_result),
        ("Run work items dispatches findings", test_run_repair_work_items_dispatches_findings_after_empty_automatic_repairs),
        ("Run work items reports no result", test_run_repair_work_items_reports_no_result_when_nothing_handles),
        ("Dispatch action calls matching handler", test_dispatch_action_calls_matching_handler_with_args),
        ("Dispatch action rejects unknown handler", test_dispatch_action_rejects_unknown_handler_with_legacy_message),
        ("Dispatch finding work item calls matching handler", test_dispatch_finding_work_item_calls_matching_handler),
        ("Dispatch finding work item rejects unknown handler", test_dispatch_finding_work_item_rejects_unknown_handler),
        ("Tool prefix preserves legacy labels", test_tool_prefix_for_chunk_preserves_legacy_bytes_and_string_labels),
        ("Color profile cleanup requires matching finding", test_color_profile_cleanup_requires_matching_finding),
        ("PLTE cleanup requires noninteractive mode and PLTE finding", test_plte_cleanup_requires_noninteractive_mode_and_plte_finding),
        ("Missing chunk data byte requires CRC or no-next finding", test_missing_chunk_data_byte_requires_crc_or_no_next_finding),
        ("Known chunk type case requires wrong ancillary finding", test_known_chunk_type_case_requires_wrong_ancillary_finding),
        ("Unknown private critical removal is standalone salvage", test_unknown_private_critical_removal_is_standalone_salvage),
        ("IHDR rebuild requires IHDR finding", test_ihdr_rebuild_requires_ihdr_finding),
        (
            "Partial IDAT blackfill requires IDAT finding",
            test_partial_idat_blackfill_requires_idat_finding_and_partial_stream,
        ),
        (
            "Automatic repair dispatches partial IDAT blackfill",
            test_automatic_repair_dispatches_partial_idat_blackfill_last_handler,
        ),
        (
            "Automatic repair dispatch rejects unknown handler",
            test_automatic_repair_dispatch_rejects_unknown_handler,
        ),
    ]

    print("Running FixItFelix family tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"FixItFelix family tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
