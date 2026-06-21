#!/usr/bin/env python3
import contextlib
import io
import json
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import magic_runtime
from chunklate.png import (
    IEND_CHUNK,
    PNG_SIGNATURE,
    build_png_chunk,
    repair_linefeed_conversion,
    validate_png_structure,
)


def build_runtime(
    calls,
    side_notes=None,
    *,
    spec_length=None,
    ask=None,
    preview_image=None,
    ultimate_linefeed_budget=None,
    ultimate_linefeed_reference=None,
    ultimate_linefeed_reference_mode=None,
    ultimate_linefeed_reference_regions=None,
    ultimate_linefeed_reference_region_editor=None,
    ultimate_linefeed_reference_region_editor_run=None,
    ultimate_linefeed_interactive=None,
    ultimate_linefeed_source=None,
    ultimate_linefeed_workers=None,
    ultimate_visual_gallery_limit=None,
    ultimate_visual_min_coverage=None,
    ultimate_candidate_preview=None,
    ultimate_visual_candidate_selector=None,
    request_ultimate_groundhogday_retry=None,
    mark_ultimate_final_clone=None,
    gpu_config=None,
    defer_linefeed_signature_repair=None,
    prompt_candy=None,
    clear_dialogue_pause=None,
    finish_progress_line=None,
):
    if side_notes is None:
        side_notes = []

    def candy(kind, *args):
        calls.append(("candy", (kind,) + args))
        if kind == "Color":
            return "<%s:%s>" % (args[0], args[1])
        if kind == "Chunky":
            return ":%s:" % args[0]
        return "candy:%s" % kind

    def spec(chunk, length):
        calls.append(("spec_length", chunk, length))
        return length if spec_length is None else spec_length

    return magic_runtime.FindMagicRuntime(
        candy=candy,
        emit=lambda message: calls.append(("emit", message)),
        checkpoint=lambda *args: calls.append(("checkpoint", args)) or "checkpoint-result",
        end=lambda: calls.append(("end",)),
        betterror=lambda error, name: calls.append(("betterror", str(error), name)),
        pause=lambda message: calls.append(("pause", message)),
        spec_length=spec,
        minibar=lambda: calls.append(("minibar",)),
        loadingbar=lambda *args: calls.append(("loadingbar", args)),
        side_notes=side_notes,
        write_clone=lambda data, summary: calls.append(("write_clone", data, summary)) or "write-result",
        ask=ask,
        preview_image=preview_image or (lambda *args: calls.append(("preview", args))),
        prompt_candy=prompt_candy,
        clear_dialogue_pause=clear_dialogue_pause or (lambda *args: None),
        finish_progress_line=finish_progress_line or (lambda *args, **kwargs: None),
        ultimate_linefeed_budget=ultimate_linefeed_budget
        or (
            lambda estimate=None: magic_runtime.idat_bruteforce.ultimate_linefeed_budget_decision(
                getattr(estimate, "total_combinations", 0),
                "normal",
            )
        ),
        ultimate_linefeed_reference=ultimate_linefeed_reference or (lambda: ""),
        ultimate_linefeed_reference_mode=ultimate_linefeed_reference_mode or (lambda: "exact"),
        ultimate_linefeed_reference_regions=ultimate_linefeed_reference_regions or (lambda: ""),
        ultimate_linefeed_reference_region_editor=ultimate_linefeed_reference_region_editor or (lambda: False),
        ultimate_linefeed_reference_region_editor_run=ultimate_linefeed_reference_region_editor_run
        or (
            lambda *args, **kwargs: magic_runtime.ultimate_reference_ui.ReferenceRegionEditorResult(
                False,
                str(args[2]) if len(args) > 2 else "",
                "editor not wired",
            )
        ),
        ultimate_linefeed_interactive=ultimate_linefeed_interactive or (lambda: True),
        ultimate_linefeed_workers=ultimate_linefeed_workers or (lambda: 0),
        ultimate_source_path=ultimate_linefeed_source or (lambda: ""),
        ultimate_visual_gallery_limit=ultimate_visual_gallery_limit
        or (lambda: magic_runtime.idat_bruteforce.ULTIMATE_LINEFEED_VISUAL_GALLERY_LIMIT),
        ultimate_visual_min_coverage=ultimate_visual_min_coverage
        or (lambda: magic_runtime.idat_bruteforce.ULTIMATE_LINEFEED_VISUAL_MIN_COVERAGE),
        gpu_config=gpu_config or magic_runtime.gpu_runtime.GpuRuntimeConfig(),
        ultimate_candidate_preview=ultimate_candidate_preview,
        ultimate_visual_candidate_selector=ultimate_visual_candidate_selector
        or magic_runtime.ultimate_visual_ui.open_ultimate_visual_candidate_selector,
        request_ultimate_groundhogday_retry=request_ultimate_groundhogday_retry or (lambda *args, **kwargs: None),
        defer_linefeed_signature_repair=defer_linefeed_signature_repair or (lambda *args: False),
        mark_ultimate_final_clone=mark_ultimate_final_clone or (lambda *args, **kwargs: None),
    )


def test_ultimate_workers_default_to_normal_when_interactive(monkeypatch):
    calls = []
    runtime = build_runtime(
        calls,
        ultimate_linefeed_workers=lambda: None,
        ultimate_linefeed_interactive=lambda: True,
    )
    monkeypatch.setattr(magic_runtime.platform_runtime, "detected_cpu_count", lambda: 16)

    assert magic_runtime._ultimate_linefeed_workers(runtime) == 8


def test_ultimate_workers_stay_serial_when_auto_without_configuration(monkeypatch):
    calls = []
    runtime = build_runtime(
        calls,
        ultimate_linefeed_workers=lambda: None,
        ultimate_linefeed_interactive=lambda: False,
    )
    monkeypatch.setattr(magic_runtime.platform_runtime, "detected_cpu_count", lambda: 16)

    assert magic_runtime._ultimate_linefeed_workers(runtime) == 0


def base_context(data_hex, **updates):
    values = {
        "data_bytes": bytes.fromhex(data_hex),
        "data_hex": data_hex,
        "chunks": (b"IHDR", b"IDAT", b"IEND"),
        "before_idat": (b"IHDR",),
        "sample_name": "sample.png",
    }
    values.update(updates)
    return magic_runtime.FindMagicContext(**values)


def test_build_find_magic_runtime_from_namespace_propagates_gpu_config():
    gpu_config = magic_runtime.gpu_runtime.GpuRuntimeConfig(enabled=True)
    namespace = {
        "Candy": lambda *args: None,
        "PRINT": lambda *args: None,
        "CheckPoint": lambda *args: None,
        "TheEnd": lambda *args: None,
        "Betterror": lambda *args: None,
        "Pause": lambda *args: None,
        "SpecLength": lambda *args: None,
        "Minibar": lambda *args: None,
        "SideNotes": [],
        "WriteClone": lambda *args: None,
        "GPU_CONFIG": gpu_config,
    }

    runtime = magic_runtime.build_find_magic_runtime_from_namespace(namespace)

    assert runtime.gpu_config == gpu_config


def tiny_rgb_png():
    ihdr = b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
    return PNG_SIGNATURE + build_png_chunk(b"IHDR", ihdr) + build_png_chunk(
        b"IDAT",
        b"\x78\x01\x01\x04\x00\xfb\xff\x00\x00\x00\x00\x00\x04\x00\x01",
    ) + IEND_CHUNK


def linefeed_salvage_fixture():
    return (ROOT / "Png_Errors_handled_by_Chunklate_So_Far" / "linefeedcorruption3.png").read_bytes()


def _visual_candidate_for_magic_runtime(path, *, state_id):
    data = tiny_rgb_png()
    analysis = magic_runtime.idat.analyze_idat_stream(data)
    candidate = magic_runtime.idat_bruteforce.SuperMegaLinefeedCandidate(
        data,
        (),
        analysis,
        analysis,
        state_id=state_id,
        score=magic_runtime.idat_bruteforce.super_mega_linefeed_score(analysis, 0),
    )
    return magic_runtime.idat_bruteforce.UltimateVisualCandidate(
        candidate=candidate,
        preview_data=data,
        preview_strategy="test-preview",
        visual_hash="visual-%s" % state_id,
        scanline_hash="scanline-%s" % state_id,
        operation_hash="operation-%s" % state_id,
        diversity_key="visual-%s" % state_id,
        rank=(state_id,),
        coverage=1.0,
        tested_candidates=state_id * 10,
        preview_path=str(path),
    )


def test_ultimate_visual_selection_maps_paths_in_picker_order(tmp_path):
    first_path = tmp_path / "first.png"
    second_path = tmp_path / "second.png"
    first_path.write_bytes(tiny_rgb_png())
    second_path.write_bytes(tiny_rgb_png())
    first = _visual_candidate_for_magic_runtime(first_path, state_id=1)
    second = _visual_candidate_for_magic_runtime(second_path, state_id=2)
    probe = SimpleNamespace(
        visual_gallery_path=str(tmp_path / "_ULF.visual.json"),
        visual_candidates=(first, second),
    )
    selection = magic_runtime.ultimate_visual_ui.UltimateVisualSelectionResult(
        selected_preview_paths=(str(second_path), str(first_path)),
    )

    selected = magic_runtime._ultimate_visual_candidates_from_selection(probe, selection)

    assert [item.candidate.state_id for item in selected] == [2, 1]


def test_ultimate_visual_selection_after_probe_calls_selector(tmp_path):
    calls = []
    preview_path = tmp_path / "first.png"
    preview_path.write_bytes(tiny_rgb_png())
    visual = _visual_candidate_for_magic_runtime(preview_path, state_id=1)
    probe = SimpleNamespace(
        visual_gallery_path=str(tmp_path / "_ULF.visual.json"),
        visual_candidates=(visual,),
    )

    def selector(path, **kwargs):
        calls.append((path, kwargs))
        return magic_runtime.ultimate_visual_ui.UltimateVisualSelectionResult(
            selected_preview_paths=(str(preview_path),),
        )

    runtime = build_runtime(calls, ultimate_visual_candidate_selector=selector)

    selected, _selection = magic_runtime._select_ultimate_visual_candidates_after_probe(runtime, probe)

    assert [item.candidate.state_id for item in selected] == [1]
    assert calls[0][0] == str(tmp_path / "_ULF.visual.json")
    assert calls[0][1]["interactive"] is True


def test_ultimate_visual_selection_legacy_groundhogday_decision_is_ignored(tmp_path):
    calls = []
    summary = []
    preview_path = tmp_path / "first.png"
    preview_path.write_bytes(tiny_rgb_png())
    visual = _visual_candidate_for_magic_runtime(preview_path, state_id=1)
    selection = magic_runtime.ultimate_visual_ui.UltimateVisualSelectionResult(
        selected_preview_paths=(str(preview_path),),
        final_preview_dir=str(tmp_path / "Final_Previews"),
        final_preview_paths=(str(preview_path),),
        decision="groundhogday",
    )
    runtime = build_runtime(
        calls,
        request_ultimate_groundhogday_retry=lambda value: calls.append(("groundhogday_retry", value)),
    )

    magic_runtime._emit_ultimate_visual_selection(runtime, summary, (visual,), selection)

    assert not any(call[0] == "groundhogday_retry" for call in calls)
    assert not any("queued for GroundHogDay" in line for line in summary)
    assert magic_runtime._ultimate_visual_selection_decision(selection) == "undecided"


def test_ultimate_visual_selection_after_budget_exhaustion_allows_keep_searching(tmp_path):
    calls = []
    preview_path = tmp_path / "first.png"
    preview_path.write_bytes(tiny_rgb_png())
    visual = _visual_candidate_for_magic_runtime(preview_path, state_id=1)
    probe = SimpleNamespace(
        visual_gallery_path=str(tmp_path / "_ULF.visual.json"),
        visual_candidates=(visual,),
        budget_exhausted=True,
    )

    def selector(path, **kwargs):
        calls.append((path, kwargs))
        return magic_runtime.ultimate_visual_ui.UltimateVisualSelectionResult(
            decision="keep_searching",
        )

    runtime = build_runtime(calls, ultimate_visual_candidate_selector=selector)

    selected, selection = magic_runtime._select_ultimate_visual_candidates_after_probe(runtime, probe)

    assert selected == ()
    assert selection.decision == "keep_searching"
    assert calls[0][1]["allow_keep_searching"] is True
    assert calls[0][1]["timeout_seconds"] == 60
    assert "Keep searching" in calls[0][1]["instruction"]


def test_ultimate_visual_review_keep_searching_resumes_fish_counter(tmp_path):
    calls = []

    def selector(path, **kwargs):
        calls.append(("selector", path, kwargs))
        return magic_runtime.ultimate_visual_ui.UltimateVisualSelectionResult(
            decision="keep_searching",
        )

    runtime = build_runtime(
        calls,
        ultimate_visual_candidate_selector=selector,
        finish_progress_line=lambda **kwargs: calls.append(("finish_progress_line", kwargs)),
    )

    review = magic_runtime._ultimate_visual_review_callback(runtime)
    selection = review(
        str(tmp_path / "_ULF.visual.json"),
        (),
        {"tested_candidates": 11775, "budget": 23323, "interval": 10000},
    )

    assert selection.decision == "keep_searching"
    assert ("finish_progress_line", {"clear": True}) in calls
    assert ("loadingbar", (23323, 5, 0, True)) in calls
    assert ("loadingbar", (23323, 5, 11775, False)) in calls


def test_next_ultimate_budget_keep_searching_advances_ladder():
    estimate = SimpleNamespace(total_combinations=7_012_540_641)
    normal = magic_runtime.idat_bruteforce.ultimate_linefeed_budget_decision(
        estimate.total_combinations,
        "normal",
    )
    inception = magic_runtime.idat_bruteforce.ultimate_linefeed_budget_decision(
        estimate.total_combinations,
        "inception",
    )

    deep = magic_runtime._next_ultimate_budget_after_keep_searching(normal, estimate)
    unbounded = magic_runtime._next_ultimate_budget_after_keep_searching(inception, estimate)

    assert deep.mode == "deep"
    assert deep.budget > normal.budget
    assert unbounded.mode == "unbounded"
    assert unbounded.budget is None
    assert magic_runtime._next_ultimate_budget_after_keep_searching(unbounded, estimate) is None


def test_next_ultimate_budget_keep_searching_doubles_custom_until_no_limit_cap():
    estimate = SimpleNamespace(total_combinations=100)
    custom = magic_runtime.idat_bruteforce.UltimateLinefeedBudgetDecision(
        "override",
        20,
        coverage=20.0,
    )
    capped = magic_runtime.idat_bruteforce.UltimateLinefeedBudgetDecision(
        "override",
        60,
        coverage=60.0,
    )

    doubled = magic_runtime._next_ultimate_budget_after_keep_searching(custom, estimate)

    assert doubled.mode == "override"
    assert doubled.budget == 40
    assert magic_runtime._next_ultimate_budget_after_keep_searching(capped, estimate) is None


def test_ultimate_source_snapshot_writes_decodable_preview_and_raw_bytes(tmp_path):
    source_data = linefeed_salvage_fixture()
    source_path = tmp_path / "_ULF.Source.png"
    raw_path = tmp_path / "_ULF.Source.raw"

    assert magic_runtime._write_ultimate_source_snapshot(str(source_path), source_data) is True
    assert magic_runtime._write_ultimate_raw_source_snapshot(str(raw_path), source_data) is True

    image, identity = magic_runtime.ultimate_reference_ui._load_image(str(source_path))
    assert image.size[0] > 0
    assert image.size[1] > 0
    assert identity != source_data
    assert raw_path.read_bytes() == source_data


def test_ultimate_source_snapshot_path_requires_checkpoint():
    runtime = build_runtime([])

    source_path = magic_runtime._ultimate_linefeed_source_path(runtime, "")
    raw_path = magic_runtime._ultimate_linefeed_raw_source_path("", source_path)

    assert source_path == ""
    assert raw_path == ""


def checkpoint_args(calls):
    matches = [call[1] for call in calls if call[0] == "checkpoint"]
    assert len(matches) == 1
    return matches[0]


def test_find_magic_runtime_single_candidate_cuts_at_best_magic():
    calls = []
    runtime = build_runtime(calls)
    data_hex = "aa" + magic_runtime.FULL_MAGIC + ("bb" * 30)

    result = magic_runtime.run_find_fucking_magic(runtime, base_context(data_hex))

    assert result == "checkpoint-result"
    assert checkpoint_args(calls) == (
        False,
        False,
        "FindFuckingMagic",
        "PngSig",
        ["-Cutting at Magic"],
        magic_runtime.FULL_MAGIC + ("bb" * 30),
        "0x1",
    )


def test_find_header_magic_runtime_found_at_start_records_story_and_checkpoint():
    calls = []
    runtime = build_runtime(calls)
    data_hex = (PNG_SIGNATURE + b"tail").hex()

    result = magic_runtime.run_find_magic(runtime, base_context(data_hex))

    assert result == "checkpoint-result"
    assert ("candy", ("Title", "Looking for magic header:")) in calls
    assert checkpoint_args(calls) == (
        False,
        False,
        "FindMagic",
        "PngSig",
        ["-Found Magic"],
        len(magic_runtime.MAGIC),
    )


def test_find_header_magic_runtime_cut_at_signature_routes_checkpoint():
    calls = []
    story_calls = []
    runtime = build_runtime(calls)
    runtime = magic_runtime.FindMagicRuntime(
        **{**runtime.__dict__, "chunk_story": lambda *args: story_calls.append(args)}
    )
    data = b"junk" + PNG_SIGNATURE + b"tail"

    result = magic_runtime.run_find_magic(runtime, base_context(data.hex()))

    assert result == "checkpoint-result"
    assert story_calls == [("add", "PNG", 8, 24, 4)]
    assert checkpoint_args(calls) == (
        False,
        False,
        "FindMagic",
        "PngSig",
        ["Cutting at Magic"],
        (PNG_SIGNATURE + b"tail").hex(),
        "0x4",
    )


def test_find_header_magic_runtime_deep_search_checkpoint():
    calls = []
    runtime = build_runtime(calls)

    result = magic_runtime.run_find_magic(runtime, base_context((b"not a png").hex()))

    assert result == "checkpoint-result"
    assert checkpoint_args(calls) == (
        False,
        False,
        "FindMagic",
        "PngSig",
        ["-dig a little bit deeper"],
    )


def test_find_header_magic_runtime_repairs_linefeed_conversion_with_clone():
    calls = []
    side_notes = []
    runtime = build_runtime(calls, side_notes)
    original = tiny_rgb_png()
    corrupted = original[:4] + original[5:]

    result = magic_runtime.run_find_magic(runtime, base_context(corrupted.hex()))

    write_calls = [call for call in calls if call[0] == "write_clone"]
    assert result == "write-result"
    assert len(write_calls) == 1
    assert bytes.fromhex(write_calls[0][1]) == original
    assert validate_png_structure(bytes.fromhex(write_calls[0][1])).ok
    assert "Line feed conversion repair" in write_calls[0][2]
    assert side_notes == [write_calls[0][2]]
    assert ("end",) not in calls


def test_find_header_magic_runtime_repairs_inserted_crlf_conversion_with_clone():
    calls = []
    side_notes = []
    runtime = build_runtime(calls, side_notes)
    original = tiny_rgb_png()
    corrupted = original.replace(b"\n", b"\r\n")

    result = magic_runtime.run_find_magic(runtime, base_context(corrupted.hex()))

    write_calls = [call for call in calls if call[0] == "write_clone"]
    assert result == "write-result"
    assert len(write_calls) == 1
    assert bytes.fromhex(write_calls[0][1]) == original
    assert validate_png_structure(bytes.fromhex(write_calls[0][1])).ok
    assert "removed carriage returns inserted by CRLF conversion" in write_calls[0][2]
    assert side_notes == [write_calls[0][2]]
    assert ("end",) not in calls


def test_find_header_magic_runtime_writes_linefeed_salvage_clone():
    calls = []
    side_notes = []
    runtime = build_runtime(calls, side_notes)
    corrupted = linefeed_salvage_fixture()

    result = magic_runtime.run_find_magic(runtime, base_context(corrupted.hex()))

    write_calls = [call for call in calls if call[0] == "write_clone"]
    assert result == "write-result"
    assert len(write_calls) == 1
    assert validate_png_structure(bytes.fromhex(write_calls[0][1])).ok
    assert "validation error after CR restoration" in write_calls[0][2]
    assert "marker-chain reconstructed visible IHDR/IDAT/IEND headers" in write_calls[0][2]
    assert "IDAT chunk preserved byte-for-byte where CRC already matched" in write_calls[0][2]
    assert "IDAT CRC rebuilt for marker-chain chunk(s): IDAT@0x202d" in write_calls[0][2]
    assert "kept declared IDAT payload bytes before rebuilding CRC: IDAT@0x202d" in write_calls[0][2]
    assert "partial-idat-raw-resync-salvage decoded 503/503 scanlines" in write_calls[0][2]
    assert "skipped 8 raw byte(s)" in write_calls[0][2]
    assert "reused previous row for 0 bad filter rows" in write_calls[0][2]
    assert "original Adler not recovered after marker-chain" in write_calls[0][2]
    assert side_notes == [write_calls[0][2]]
    assert ("end",) not in calls


def test_find_header_magic_runtime_can_defer_linefeed_signature_repair():
    calls = []
    side_notes = []
    story_calls = []

    def defer(data_bytes, sample_name, linefeed_pattern):
        calls.append(("defer", len(data_bytes), sample_name, linefeed_pattern))
        return True

    runtime = build_runtime(
        calls,
        side_notes,
        defer_linefeed_signature_repair=defer,
    )
    runtime = magic_runtime.FindMagicRuntime(
        **{**runtime.__dict__, "chunk_story": lambda *args: story_calls.append(args)}
    )
    corrupted = linefeed_salvage_fixture()

    result = magic_runtime.run_find_magic(runtime, base_context(corrupted.hex(), sample_name="6.bad.png"))

    assert result == "checkpoint-result"
    assert checkpoint_args(calls) == (
        False,
        False,
        "FindMagic",
        "PngSig",
        ["-Found Magic"],
        14,
    )
    assert story_calls == [("add", "PNG", 0, 14, 0)]
    assert [call for call in calls if call[0] == "defer"] == [
        ("defer", len(corrupted), "6.bad.png", "minor_linefeed_corruption")
    ]
    assert not [call for call in calls if call[0] == "write_clone"]
    assert side_notes == [
        "-FindMagic: line-feed signature repair deferred until the full chunk tour finishes."
    ]


def test_deferred_linefeed_signature_repair_writes_after_tour():
    calls = []
    side_notes = []
    runtime = build_runtime(calls, side_notes)
    corrupted = linefeed_salvage_fixture()

    result = magic_runtime.run_deferred_linefeed_signature_repair(
        runtime,
        base_context(corrupted.hex(), sample_name="6.bad.png"),
    )

    write_calls = [call for call in calls if call[0] == "write_clone"]
    assert result == "write-result"
    assert write_calls
    cowsay_messages = [
        call[1][1]
        for call in calls
        if call[0] == "candy" and call[1][0] == "Cowsay" and len(call[1]) > 1
    ]
    cowsay_moods = [
        call[1][2]
        for call in calls
        if call[0] == "candy" and call[1][0] == "Cowsay" and len(call[1]) > 2
    ]
    assert cowsay_moods[:4] == ["bad", "good", "good", "com"]
    assert any(
        "I rebuilt the visible IDAT marker chain before brute force" in message
        and "503/503 scanlines" in message
        for message in cowsay_messages
    )
    assert any(
        "I preserved the already-valid IDAT chunks" in message
        for message in cowsay_messages
    )
    assert any(
        "rebuilt-Adler visual salvage" in message
        for message in cowsay_messages
    )
    assert "Line feed conversion repair" in write_calls[0][2]
    assert "marker-chain reconstructed visible IHDR/IDAT/IEND headers" in write_calls[0][2]


def test_deferred_internal_idat_marker_chain_repair_uses_marker_chain_path():
    calls = []
    side_notes = []
    runtime = build_runtime(calls, side_notes)
    original_marker_repairs = magic_runtime.repair_idat_marker_chain_from_visible_headers
    original_best = magic_runtime._linefeed_best_marker_chain_candidate
    original_summary = magic_runtime._linefeed_marker_chain_summary
    original_supermega = magic_runtime._linefeed_supermega_probe_alternative

    marker_repair = SimpleNamespace(data=b"marker-data", preserved_chunks=[b"IDAT"])
    analysis = SimpleNamespace(adler_status="adler_mismatch")
    visual_repair = SimpleNamespace(
        recovered_scanlines=10,
        total_scanlines=20,
        data=b"visual-data",
    )

    try:
        magic_runtime.repair_idat_marker_chain_from_visible_headers = lambda data: [
            "marker-repair"
        ]
        magic_runtime._linefeed_best_marker_chain_candidate = lambda repairs: (
            marker_repair,
            analysis,
            visual_repair,
        )
        magic_runtime._linefeed_marker_chain_summary = (
            lambda marker, idat_analysis, repair: "marker summary"
        )
        magic_runtime._linefeed_supermega_probe_alternative = (
            lambda *args, **kwargs: None
        )

        result = magic_runtime.run_deferred_internal_idat_marker_chain_repair(
            runtime,
            base_context(b"internal-idat".hex(), sample_name="7.bad.png"),
        )
    finally:
        magic_runtime.repair_idat_marker_chain_from_visible_headers = original_marker_repairs
        magic_runtime._linefeed_best_marker_chain_candidate = original_best
        magic_runtime._linefeed_marker_chain_summary = original_summary
        magic_runtime._linefeed_supermega_probe_alternative = original_supermega

    write_calls = [call for call in calls if call[0] == "write_clone"]
    assert result == "write-result"
    assert write_calls == [("write_clone", b"visual-data".hex(), "marker summary")]
    assert side_notes == ["marker summary"]
    assert ("candy", ("Title", "Deferred internal IDAT line-feed repair:")) in calls
    cowsay_messages = [
        call[1][1]
        for call in calls
        if call[0] == "candy" and call[1][0] == "Cowsay" and len(call[1]) > 1
    ]
    assert any("PNG signature is fine" in message for message in cowsay_messages)


def test_linefeed_chunk_evidence_requires_chunk_level_proof_for_idat_bruteforce():
    signature_only = SimpleNamespace(payload_patches=())

    evidence = magic_runtime._linefeed_chunk_evidence(signature_only)

    assert evidence.idat_bruteforce_allowed is False
    assert "only the PNG signature was proven damaged" in evidence.summary_lines[0]


def test_linefeed_chunk_evidence_allows_idat_realign_and_payload_patch():
    idat_patch_repair = SimpleNamespace(
        payload_patches=(
            SimpleNamespace(
                chunk_type=b"IDAT",
                chunk_offset=0x20,
                stored_crc=0x12345678,
            ),
        )
    )
    realignment_repair = SimpleNamespace(payload_patches=())
    realignment = SimpleNamespace(
        chunk_name="IDAT",
        old_length=8192,
        new_length=8188,
        chunk_offset=0x202D,
    )

    patch_evidence = magic_runtime._linefeed_chunk_evidence(idat_patch_repair)
    realign_evidence = magic_runtime._linefeed_chunk_evidence(realignment_repair, realignment)

    assert patch_evidence.idat_bruteforce_allowed is True
    assert "restored CR inside IDAT payload" in patch_evidence.summary_lines[0]
    assert realign_evidence.idat_bruteforce_allowed is True
    assert "IDAT chunk length overran the next chunk by 4 bytes" in realign_evidence.summary_lines[0]


def test_linefeed_full_bruteforce_checks_length_realign_before_prompt():
    calls = []
    side_notes = []

    def ask(*args, **kwargs):
        raise AssertionError("brute force prompt should not run before length realignment")

    runtime = build_runtime(calls, side_notes, ask=ask)
    corrupted = linefeed_salvage_fixture()
    linefeed = repair_linefeed_conversion(corrupted, allow_partial=True)
    current_repair = SimpleNamespace(
        data=linefeed.data,
        strategy="weak current salvage",
        recovered_scanlines=0,
        total_scanlines=503,
        width=800,
        height=503,
        bit_depth=8,
        color_type=2,
    )
    summary_lines = []

    alternative = magic_runtime._linefeed_full_bruteforce_alternative(
        runtime,
        linefeed.data,
        current_repair,
        summary_lines,
        0x3EE9,
        source_data=linefeed.data,
    )

    assert alternative.repair.recovered_scanlines == 503
    assert "partial-idat-raw-resync-salvage decoded 503/503 scanlines" in alternative.summary
    assert "pre-bruteforce length check" not in alternative.summary
    assert "IDAT chunk length overran the next chunk by 4 bytes" in alternative.summary
    assert not [call for call in calls if call[0] == "ask"]


def test_linefeed_full_bruteforce_passes_known_gap_to_super_probe():
    calls = []
    side_notes = []
    captured = {}
    original_super_mega = magic_runtime.idat_bruteforce.probe_super_mega_linefeed_force_of_death

    def ask(*args, **kwargs):
        calls.append(("ask", args, kwargs))
        return True

    def fake_super_mega(data, **kwargs):
        captured.update(kwargs)
        before = magic_runtime.idat.analyze_idat_stream(data)
        return magic_runtime.idat_bruteforce.SuperMegaLinefeedProbeResult(
            before=before,
            best=None,
            error_anchor_offset=kwargs.get("start_offset"),
            search_start_offset=0,
            window_start=0,
            window_end=0,
            tested_candidates=0,
            budget_exhausted=False,
            reason="fake super",
        )

    corrupted = linefeed_salvage_fixture()
    linefeed = repair_linefeed_conversion(corrupted, allow_partial=True)
    realignment = magic_runtime.repair_overlong_chunk_length_to_next_header(linefeed.data)
    current_repair = SimpleNamespace(
        data=realignment.data,
        strategy="already strong",
        recovered_scanlines=503,
        total_scanlines=503,
        width=800,
        height=503,
        bit_depth=8,
        color_type=2,
    )
    runtime = build_runtime(calls, side_notes, ask=ask)

    magic_runtime.idat_bruteforce.probe_super_mega_linefeed_force_of_death = fake_super_mega
    try:
        alternative = magic_runtime._linefeed_full_bruteforce_alternative(
            runtime,
            realignment.data,
            current_repair,
            [],
            0x3EE9,
            source_data=realignment.data,
            known_gap_bytes=4,
            known_gap_chunk_offset=realignment.chunk_offset,
        )
    finally:
        magic_runtime.idat_bruteforce.probe_super_mega_linefeed_force_of_death = original_super_mega

    assert alternative.repair is current_repair
    assert captured["known_gap_bytes"] == 4
    assert captured["known_gap_chunk_offset"] == realignment.chunk_offset


def test_linefeed_final_salvage_promotes_equal_scanline_pixel_repair():
    calls = []
    summary_lines = []
    runtime = build_runtime(calls)
    current = SimpleNamespace(
        data=b"old-pixels",
        recovered_scanlines=503,
        total_scanlines=503,
    )
    salvage = SimpleNamespace(
        data=b"better-pixels",
        strategy="partial-idat-blackfill recovered 503/503 scanlines",
        recovered_scanlines=503,
        total_scanlines=503,
    )
    candidate = SimpleNamespace(data=b"candidate-png")
    original_tolerant = magic_runtime.idat.rebuild_tolerant_idat_salvage
    original_blackfill = magic_runtime.idat.rebuild_partial_idat_blackfill

    try:
        magic_runtime.idat.rebuild_tolerant_idat_salvage = lambda data: None
        magic_runtime.idat.rebuild_partial_idat_blackfill = lambda data: salvage
        repair = magic_runtime._linefeed_final_candidate_salvage(
            runtime,
            summary_lines,
            magic_runtime.SUPER_MEGA_LINEFEED_FORCE,
            candidate,
            current,
        )
    finally:
        magic_runtime.idat.rebuild_tolerant_idat_salvage = original_tolerant
        magic_runtime.idat.rebuild_partial_idat_blackfill = original_blackfill

    assert repair is salvage
    assert "final IDAT salvage after SuperMegaLineFeedForceOfDeath" in summary_lines[0]
    assert any(
        call[0] == "candy"
        and call[1][0] == "Cowsay"
        and "Final IDAT salvage pass after SuperMegaLineFeedForceOfDeath kept 503/503 scanlines" in call[1][1]
        and call[1][2] == "good"
        for call in calls
    )


def test_find_header_magic_runtime_can_launch_supermega_directly_after_salvage():
    calls = []
    side_notes = []
    answers = [True, False]
    original_super_mega = magic_runtime.idat_bruteforce.probe_super_mega_linefeed_force_of_death

    def fast_super_mega(data, **kwargs):
        kwargs.update(
            {
                "linefeed_budget": 100,
                "known_gap_budget": 64,
                "structural_budget": 100,
                "local_bit_budget": 32,
                "local_byte_budget": 64,
                "heavy_byte_budget": 64,
                "beam_width": 2,
                "max_depth": 1,
            }
        )
        return original_super_mega(data, **kwargs)

    def ask(*args):
        calls.append(("ask", args))
        return answers.pop(0)

    runtime = build_runtime(calls, side_notes, ask=ask)
    corrupted = linefeed_salvage_fixture()

    magic_runtime.idat_bruteforce.probe_super_mega_linefeed_force_of_death = fast_super_mega
    try:
        result = magic_runtime.run_find_magic(runtime, base_context(corrupted.hex()))
    finally:
        magic_runtime.idat_bruteforce.probe_super_mega_linefeed_force_of_death = original_super_mega

    write_calls = [call for call in calls if call[0] == "write_clone"]
    assert result == "write-result"
    assert (
        "ask",
        ("SuperMegaLineFeedForceOfDeath", "super-mega-linefeed-force-of-death-0x3ee9-503"),
    ) in calls
    ultimate_ask = next(
        call
        for call in calls
        if call[0] == "ask" and call[1][0] == "UltimateMegaSuperLineFeedBruteForce"
    )
    assert ultimate_ask[1][1].startswith("ultimate-mega-super-linefeed-bruteforce-0x3ee9-")
    assert ("candy", ("Title", "SuperMegaLineFeedForceOfDeath")) in calls
    assert len(write_calls) == 1
    assert validate_png_structure(bytes.fromhex(write_calls[0][1])).ok
    assert "using SuperMegaLineFeedForceOfDeath directly from chunk-level IDAT evidence" in write_calls[0][2]
    assert "legacy narrow" not in write_calls[0][2]
    assert "SuperMegaLineFeedForceOfDeath: anchor=0x3ee9; search=" in write_calls[0][2]
    assert "pre_error_backtrack=0x" in write_calls[0][2]
    assert "phase4-heavy-byte-window phase" in write_calls[0][2]
    assert "UltimateMegaSuperLineFeedBruteForce: user declined" in write_calls[0][2]
    assert "final IDAT salvage after SuperMegaLineFeedForceOfDeath" in write_calls[0][2]
    assert "partial-idat-raw-resync-salvage decoded 503/503 scanlines" in write_calls[0][2]
    assert "partial-idat-blackfill recovered 503/503 scanlines" in write_calls[0][2]
    assert "SuperMegaLineFeedForceOfDeath" in write_calls[0][2]
    assert [call for call in calls if call[0] == "loadingbar"]
    assert not [call for call in calls if call[0] == "minibar"]
    preview_calls = [call for call in calls if call[0] == "preview"]
    assert len(preview_calls) == 1
    assert preview_calls[0][1][1] == "UltimateMegaSuperLineFeedBruteForce_Before"
    assert calls.index(preview_calls[0]) < calls.index(ultimate_ask)
    assert side_notes == [write_calls[0][2]]
    assert ("end",) not in calls


def test_find_header_magic_runtime_can_decline_direct_supermega():
    calls = []
    side_notes = []
    answers = [False]

    def ask(*args, **kwargs):
        calls.append(("ask", args, kwargs))
        return answers.pop(0)

    runtime = build_runtime(calls, side_notes, ask=ask)
    corrupted = linefeed_salvage_fixture()

    result = magic_runtime.run_find_magic(runtime, base_context(corrupted.hex()))

    write_calls = [call for call in calls if call[0] == "write_clone"]
    assert result == "write-result"
    assert [
        call
        for call in calls
        if call[0] == "ask" and call[1][0] == "SuperMegaLineFeedForceOfDeath"
    ]
    cowsay_messages = [
        call[1][1]
        for call in calls
        if call[0] == "candy" and call[1][0] == "Cowsay" and len(call[1]) > 1
    ]
    preview_calls = [call for call in calls if call[0] == "preview"]
    assert any("I rebuilt the visible IDAT marker chain before brute force" in message for message in cowsay_messages)
    assert any("I preserved the already-valid IDAT chunks" in message for message in cowsay_messages)
    assert any("IDAT line-feed evidence is strong enough" in message for message in cowsay_messages)
    assert not any("Current IDAT repair preview" in message for message in cowsay_messages)
    assert not preview_calls
    assert any("IDAT line-feed evidence is strong enough" in message for message in cowsay_messages)
    assert not any("Legacy narrow" in message for message in cowsay_messages)
    assert "using SuperMegaLineFeedForceOfDeath directly from chunk-level IDAT evidence" in write_calls[0][2]
    assert "legacy narrow" not in write_calls[0][2]
    assert "SuperMegaLineFeedForceOfDeath: user declined the wider IDAT line-feed brute force" in write_calls[0][2]


def test_find_header_magic_runtime_can_launch_ultimate_linefeed_probe():
    calls = []
    side_notes = []
    answers = [True, True, True]
    original_super_mega = magic_runtime.idat_bruteforce.probe_super_mega_linefeed_force_of_death
    original_ultimate = magic_runtime.idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce
    original_gpu_explain = magic_runtime.ultimate_opengl_backend.explain
    original_gpu_run = magic_runtime.ultimate_opengl_backend.run_gpu

    def fast_super_mega(data, **kwargs):
        kwargs.update(
            {
                "linefeed_budget": 100,
                "known_gap_budget": 64,
                "structural_budget": 100,
                "local_bit_budget": 32,
                "local_byte_budget": 64,
                "heavy_byte_budget": 64,
                "beam_width": 2,
                "max_depth": 1,
            }
        )
        return original_super_mega(data, **kwargs)

    def fake_ultimate(data, **kwargs):
        calls.append(("ultimate_kwargs", kwargs))
        progress = kwargs.get("progress")
        if progress is not None:
            progress("UltimateMegaSuperLineFeedBruteForce", 0, 10)
            progress("UltimateMegaSuperLineFeedBruteForce", 10, 10)
        before = magic_runtime.idat.analyze_idat_stream(data)
        return magic_runtime.idat_bruteforce.UltimateLinefeedProbeResult(
            before,
            None,
            kwargs.get("target_adler"),
            kwargs.get("start_offset"),
            1,
            3,
            (kwargs.get("start_offset") or 0,),
            10,
            11,
            11,
            3,
            0,
            kwargs.get("checkpoint_path", ""),
            True,
            reason="test budget",
        )

    def ask(*args, **kwargs):
        calls.append(("ask", args, kwargs))
        return answers.pop(0)

    live_preview = lambda *args: calls.append(("live_preview", args))
    runtime = build_runtime(
        calls,
        side_notes,
        ask=ask,
        ultimate_linefeed_budget=lambda: 1234,
        ultimate_visual_gallery_limit=lambda: 77,
        ultimate_visual_min_coverage=lambda: 0.8,
        ultimate_linefeed_workers=lambda: 3,
        ultimate_candidate_preview=live_preview,
        gpu_config=magic_runtime.gpu_runtime.GpuRuntimeConfig(enabled=True),
        clear_dialogue_pause=lambda *args: calls.append(("clear_dialogue_pause", args)),
    )
    corrupted = linefeed_salvage_fixture()

    magic_runtime.idat_bruteforce.probe_super_mega_linefeed_force_of_death = fast_super_mega
    magic_runtime.idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce = fake_ultimate
    magic_runtime.ultimate_opengl_backend.explain = (
        lambda plan, gpu_config: magic_runtime.ultimate_opengl_backend.UltimateOpenGLDecision(
            True,
            "OpenGL Ultimate offset preflight active; CPU still runs the repair search.",
        )
    )
    magic_runtime.ultimate_opengl_backend.run_gpu = (
        lambda plan, gpu_config: magic_runtime.ultimate_opengl_backend.UltimateOpenGLOffsetResult(
            (3, 7),
            22,
        )
    )
    try:
        result = magic_runtime.run_find_magic(runtime, base_context(corrupted.hex()))
    finally:
        magic_runtime.idat_bruteforce.probe_super_mega_linefeed_force_of_death = original_super_mega
        magic_runtime.idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce = original_ultimate
        magic_runtime.ultimate_opengl_backend.explain = original_gpu_explain
        magic_runtime.ultimate_opengl_backend.run_gpu = original_gpu_run

    write_calls = [call for call in calls if call[0] == "write_clone"]
    ultimate_asks = [
        call
        for call in calls
        if call[0] == "ask" and call[1][0] == "UltimateMegaSuperLineFeedBruteForce"
    ]
    assert result is None
    assert write_calls == []
    assert ultimate_asks
    assert ultimate_asks[0][2] == {"skipauto": True}
    assert ("candy", ("Title", "UltimateMegaSuperLineFeedBruteForce")) in calls
    assert (
        "emit",
        "-GPU requested: OpenGL Ultimate offset preflight active; CPU still runs the repair search. Found 2 Ultimate offset hint(s).",
    ) in calls
    ultimate_kwargs = [call[1] for call in calls if call[0] == "ultimate_kwargs"][0]
    assert ultimate_kwargs["candidate_preview"] is live_preview
    ultimate_prompt_calls = [
        call
        for call in calls
        if call[0] == "candy"
        and call[1][0] == "Cowsay"
        and (
            "UltimateMegaSuperLineFeedBruteForce is the last basement door" in str(call[1][1])
            or "several billion years" in str(call[1][1])
            or "If I recover the original Adler" in str(call[1][1])
            or "-ulfb" in str(call[1][1])
            or "-ulfu" in str(call[1][1])
            or "budget no jutsu" in str(call[1][1])
        )
    ]
    assert [call[1][2] for call in ultimate_prompt_calls] == ["bad", "bad", "com", "com"]
    ultimate_prompt_text = " ".join(str(call[1][1]) for call in ultimate_prompt_calls)
    assert "-ulfb N" in ultimate_prompt_text
    assert "-ulfu" in ultimate_prompt_text
    budget_selected_calls = [
        call
        for call in calls
        if call[0] == "candy"
        and call[1][0] == "Cowsay"
        and "Ultimate budget selected:" in str(call[1][1])
    ]
    assert len(budget_selected_calls) == 1
    assert "selected budget: 1,234" in str(budget_selected_calls[0][1][1])
    assert "visual gallery cap: 77 saved candidates" in str(budget_selected_calls[0][1][1])
    assert "possible combinations:" not in str(budget_selected_calls[0][1][1])
    ultimate_kwargs = next(call[1] for call in calls if call[0] == "ultimate_kwargs")
    assert ultimate_kwargs["budget"] == 1234
    assert ultimate_kwargs["reference_path"] == ""
    assert ultimate_kwargs["reference_mode"] == "exact"
    assert ultimate_kwargs["visual_gallery_limit"] == 77
    assert ultimate_kwargs["visual_min_coverage"] == 0.8
    assert ultimate_kwargs["ultimate_workers"] == 3
    assert ultimate_kwargs["gpu_suspect_offsets"] == (3, 7)
    assert any(
        call[0] == "candy" and "Ultimate will use 3 CPU workers" in str(call[1][1])
        for call in calls
    )
    assert [call for call in calls if call[0] == "loadingbar"]
    opening_index = next(
        index
        for index, call in enumerate(calls)
        if call[0] == "candy"
        and call[1][0] == "Cowsay"
        and "Opening the forbidden line-feed combinatorics vault no jutsu" in str(call[1][1])
    )
    ultimate_call_index = next(
        index for index, call in enumerate(calls) if call[0] == "ultimate_kwargs"
    )
    assert any(
        opening_index < index < ultimate_call_index
        for index, call in enumerate(calls)
        if call[0] == "clear_dialogue_pause"
    )
    assert [call for call in calls if call[0] == "ultimate_kwargs"][0][1]["budget"] == 1234
    assert side_notes
    assert "UltimateMegaSuperLineFeedBruteForce: start=0x3ee9" in side_notes[0]
    assert "test budget" in side_notes[0]
    assert "no candidate survived pruning" in side_notes[0]


def test_linefeed_queue_progress_draws_zero_state_after_build():
    calls = []
    runtime = SimpleNamespace(
        loadingbar=lambda total, size, tested, build: calls.append(
            (total, size, tested, build)
        )
    )

    progress = magic_runtime._linefeed_queue_progress(runtime)
    progress("UltimateMegaSuperLineFeedBruteForce", 0, 701254065)

    assert calls == [
        (701254065, 9, 0, True),
        (701254065, 9, 0, False),
    ]


def test_linefeed_queue_progress_builds_before_resume_counter():
    calls = []
    runtime = SimpleNamespace(
        loadingbar=lambda total, size, tested, build: calls.append(
            (total, size, tested, build)
        )
    )

    progress = magic_runtime._linefeed_queue_progress(runtime)
    progress("UltimateMegaSuperLineFeedBruteForce", 3226, 1000000000000)

    assert calls == [
        (1000000000000, 13, 0, True),
        (1000000000000, 13, 3226, False),
    ]


def test_linefeed_queue_progress_clears_between_super_mega_phases():
    calls = []
    runtime = SimpleNamespace(
        loadingbar=lambda total, size, tested, build: calls.append(
            ("loadingbar", total, size, tested, build)
        ),
        finish_progress_line=lambda **kwargs: calls.append(("finish", kwargs)),
    )

    progress = magic_runtime._linefeed_queue_progress(runtime)
    progress("phase2-crlf-structural", 1024, 1024)
    progress("phase3-deflate-byte", 50, 70)

    assert calls == [
        ("loadingbar", 1024, 4, 0, True),
        ("loadingbar", 1024, 4, 1024, False),
        ("finish", {"clear": True}),
        ("loadingbar", 70, 2, 0, True),
        ("loadingbar", 70, 2, 50, False),
    ]


def test_prime_ultimate_linefeed_minibar_draws_unbounded_placeholder():
    calls = []
    runtime = SimpleNamespace(
        loadingbar=lambda total, size, tested, build: calls.append(
            (total, size, tested, build)
        )
    )

    magic_runtime._prime_ultimate_linefeed_minibar(runtime, None)

    assert calls == [
        (1000000000000, 13, 0, True),
        (1000000000000, 13, 0, False),
    ]


def test_ultimate_linefeed_resume_message_uses_frontier_phase(tmp_path):
    progress_path = tmp_path / "_ULF.progress.json"
    progress_path.write_text(json.dumps({"phase": "frontier"}), encoding="utf-8")

    message = magic_runtime._ultimate_linefeed_resume_message(str(progress_path), "")

    assert "frontier" in message
    assert "saved cursor" not in message


def test_ultimate_linefeed_resume_message_uses_exhaustive_phase(tmp_path):
    progress_path = tmp_path / "_ULF.progress.json"
    progress_path.write_text(json.dumps({"phase": "exhaustive"}), encoding="utf-8")

    message = magic_runtime._ultimate_linefeed_resume_message(str(progress_path), "")

    assert "exhaustive vault" in message
    assert "frontier" not in message


def test_ultimate_linefeed_resume_message_uses_fast_v2_exhaustive_phase(tmp_path):
    progress_path = tmp_path / "_ULF.progress.json"
    progress_path.write_text(
        json.dumps(
                {
                    "version": 2,
                    "phase": "exhaustive",
                    "tested_candidates": 1234,
                    "attempted_candidates": 4321,
                    "parallel_workers": 4,
                    "shards": [
                        {"start_rank": 0, "end_rank": 1000, "next_rank": 1000, "status": "done"},
                        {"start_rank": 1000, "end_rank": 2000, "next_rank": 1500, "status": "pending"},
                        {"start_rank": 2000, "end_rank": 3000, "next_rank": 2200, "status": "running"},
                    ],
                }
            ),
        encoding="utf-8",
    )

    message = magic_runtime._ultimate_linefeed_resume_message(str(progress_path), "")

    assert "Fast resume" in message
    assert "Checkpoint archive scan skipped" in message
    assert "attempted 1700" in message
    assert "committed 1234" in message
    assert "pending shards: 2" in message
    assert "workers: 4" in message
    assert "last confirmed shard cursor" in message


def test_ultimate_linefeed_resume_message_handles_complete_phase(tmp_path):
    progress_path = tmp_path / "_ULF.progress.json"
    progress_path.write_text(json.dumps({"phase": "complete"}), encoding="utf-8")

    message = magic_runtime._ultimate_linefeed_resume_message(str(progress_path), "")

    assert "old complete marker" in message
    assert "verify it from checkpoint candidates" in message


def test_ultimate_linefeed_resume_message_handles_trusted_complete_phase(tmp_path):
    progress_path = tmp_path / "_ULF.progress.json"
    progress_path.write_text(
        json.dumps({"phase": "complete", "completion_reason": "search_exhausted"}),
        encoding="utf-8",
    )

    message = magic_runtime._ultimate_linefeed_resume_message(str(progress_path), "")

    assert "already marked this search complete" in message


def test_ultimate_linefeed_resume_message_falls_back_to_checkpoint(tmp_path):
    progress_path = tmp_path / "_ULF.progress.json"
    checkpoint_path = tmp_path / "_ULF.checkpoint.jsonl"
    progress_path.write_text("{", encoding="utf-8")
    checkpoint_path.write_text("", encoding="utf-8")

    message = magic_runtime._ultimate_linefeed_resume_message(
        str(progress_path),
        str(checkpoint_path),
    )

    assert "useful candidates" in message
    assert "frontier" not in message


def _write_roi_mapping(path, source_data, reference_path):
    reference_image, _warning = magic_runtime.idat_bruteforce._load_ultimate_reference_image(
        str(reference_path)
    )
    record = magic_runtime.idat_bruteforce.build_ultimate_reference_regions_record(
        candidate_size=(1, 1),
        reference_size=(1, 1),
        candidate_hash=magic_runtime.idat_bruteforce._ultimate_image_hash_from_bytes(source_data),
        reference_hash=magic_runtime.idat_bruteforce._ultimate_image_hash_from_image(reference_image),
        regions=(
            magic_runtime.idat_bruteforce.UltimateReferenceRegion(
                candidate_region=(0.0, 0.0, 1.0, 1.0),
                reference_region=(0.0, 0.0, 1.0, 1.0),
                weight=1.0,
                label="full",
            ),
        ),
    )
    path.write_text(json.dumps(record), encoding="utf-8")


def test_ultimate_reference_regions_editor_opens_when_missing(tmp_path):
    calls = []
    source_data = tiny_rgb_png()
    source_path = tmp_path / "_ULF.Source.png"
    reference_path = tmp_path / "reference.png"
    regions_path = tmp_path / "_ULF.reference_regions.json"
    source_path.write_bytes(source_data)
    reference_path.write_bytes(source_data)

    def editor(source, reference, output, **kwargs):
        calls.append(("editor", source, reference, output, kwargs.get("source_data")))
        _write_roi_mapping(Path(output), source_data, reference_path)
        return magic_runtime.ultimate_reference_ui.ReferenceRegionEditorResult(
            True,
            output,
            region_count=1,
        )

    runtime = build_runtime(
        calls,
        ultimate_linefeed_reference=lambda: str(reference_path),
        ultimate_linefeed_reference_mode=lambda: "similar",
        ultimate_linefeed_reference_regions=lambda: str(regions_path),
        ultimate_linefeed_reference_region_editor_run=editor,
    )

    result = magic_runtime._prepare_ultimate_reference_regions(
        runtime,
        source_data=source_data,
        source_path=str(source_path),
        checkpoint_path=str(tmp_path / "_ULF.checkpoint.jsonl"),
    )

    assert result == str(regions_path)
    editor_call = next(call for call in calls if call[0] == "editor")
    assert editor_call[1:4] == (str(source_path), str(reference_path), str(regions_path))


def test_ultimate_reference_regions_existing_mapping_skips_editor(tmp_path):
    calls = []
    source_data = tiny_rgb_png()
    source_path = tmp_path / "_ULF.Source.png"
    reference_path = tmp_path / "reference.png"
    regions_path = tmp_path / "_ULF.reference_regions.json"
    source_path.write_bytes(source_data)
    reference_path.write_bytes(source_data)
    _write_roi_mapping(regions_path, source_data, reference_path)

    runtime = build_runtime(
        calls,
        ultimate_linefeed_reference=lambda: str(reference_path),
        ultimate_linefeed_reference_mode=lambda: "similar",
        ultimate_linefeed_reference_regions=lambda: str(regions_path),
        ultimate_linefeed_reference_region_editor_run=lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("editor should not open")
        ),
    )

    result = magic_runtime._prepare_ultimate_reference_regions(
        runtime,
        source_data=source_data,
        source_path=str(source_path),
        checkpoint_path=str(tmp_path / "_ULF.checkpoint.jsonl"),
    )

    assert result == str(regions_path)


def test_ultimate_reference_prompt_opens_roi_selector_when_reference_missing(tmp_path):
    calls = []
    source_data = tiny_rgb_png()
    source_path = tmp_path / "_ULF.Source.png"
    reference_path = tmp_path / "reference.png"
    regions_path = tmp_path / "_ULF.reference_regions.json"
    source_path.write_bytes(source_data)
    reference_path.write_bytes(source_data)

    def ask(*args, **kwargs):
        calls.append(("ask", args, kwargs))
        return True

    def editor(source, reference, output, **kwargs):
        calls.append(("editor", source, reference, output, kwargs.get("source_data")))
        assert reference == ""
        _write_roi_mapping(Path(output), source_data, reference_path)
        return magic_runtime.ultimate_reference_ui.ReferenceRegionEditorResult(
            True,
            output,
            region_count=1,
            reference_path=str(reference_path),
        )

    runtime = build_runtime(
        calls,
        ask=ask,
        ultimate_linefeed_reference=lambda: "",
        ultimate_linefeed_reference_regions=lambda: str(regions_path),
        ultimate_linefeed_reference_region_editor_run=editor,
    )

    handled, reference, mode, regions = magic_runtime._maybe_prepare_ultimate_reference_from_prompt(
        runtime,
        source_data=source_data,
        source_path=str(source_path),
        checkpoint_path=str(tmp_path / "_ULF.checkpoint.jsonl"),
        start_offset=0x1234,
    )

    assert handled is True
    assert reference == str(reference_path)
    assert mode == "similar"
    assert regions == str(regions_path)
    assert [
        call
        for call in calls
        if call[0] == "ask" and call[1][0] == "Ultimate Visual Reference ROI:-Do you have any similar png by any chance?"
    ]
    assert [call for call in calls if call[0] == "editor"]


def test_ultimate_reference_prompt_can_use_visible_preview_for_roi_source(tmp_path):
    calls = []
    answers = [True, True]
    source_data = tiny_rgb_png()
    source_path = tmp_path / "_ULF.Source.png"
    preview_path = tmp_path / "Bruteforce_Previews" / "_Preview_UltimateMegaSuperLineFeedBruteForce_Before.png"
    reference_path = tmp_path / "reference.png"
    regions_path = tmp_path / "_ULF.reference_regions.json"
    preview_path.parent.mkdir()
    source_path.write_bytes(source_data)
    preview_path.write_bytes(source_data)
    reference_path.write_bytes(source_data)

    def ask(*args, **kwargs):
        calls.append(("ask", args, kwargs))
        return answers.pop(0)

    def editor(source, reference, output, **kwargs):
        calls.append(("editor", source, reference, output, kwargs.get("source_data")))
        assert source == str(preview_path)
        assert reference == ""
        _write_roi_mapping(Path(output), source_data, reference_path)
        return magic_runtime.ultimate_reference_ui.ReferenceRegionEditorResult(
            True,
            output,
            region_count=1,
            reference_path=str(reference_path),
        )

    runtime = build_runtime(
        calls,
        ask=ask,
        ultimate_linefeed_reference=lambda: "",
        ultimate_linefeed_reference_regions=lambda: str(regions_path),
        ultimate_linefeed_reference_region_editor_run=editor,
    )

    handled, reference, mode, regions = magic_runtime._maybe_prepare_ultimate_reference_from_prompt(
        runtime,
        source_data=source_data,
        source_path=str(source_path),
        checkpoint_path=str(tmp_path / "_ULF.checkpoint.jsonl"),
        start_offset=0x1234,
        roi_source_preview_path=str(preview_path),
    )

    assert (handled, reference, mode, regions) == (True, str(reference_path), "similar", str(regions_path))
    assert any(
        call[0] == "ask"
        and call[1][0] == "Ultimate Visual Reference ROI:-Do you have any similar png by any chance?"
        for call in calls
    )
    assert any(
        call[0] == "ask"
        and call[1][0] == "Ultimate Visual ROI Snapshot:-Use the visible Ultimate preview instead of _ULF.Source.png?"
        for call in calls
    )


def test_ultimate_reference_regions_prompt_keeps_source_snapshot_when_preview_declined(tmp_path):
    calls = []
    source_data = tiny_rgb_png()
    source_path = tmp_path / "_ULF.Source.png"
    preview_path = tmp_path / "Bruteforce_Previews" / "_Preview_UltimateMegaSuperLineFeedBruteForce_Before.png"
    reference_path = tmp_path / "reference.png"
    regions_path = tmp_path / "_ULF.reference_regions.json"
    preview_path.parent.mkdir()
    source_path.write_bytes(source_data)
    preview_path.write_bytes(source_data)
    reference_path.write_bytes(source_data)

    def ask(*args, **kwargs):
        calls.append(("ask", args, kwargs))
        return False

    def editor(source, reference, output, **kwargs):
        calls.append(("editor", source, reference, output, kwargs.get("source_data")))
        assert source == str(source_path)
        assert reference == str(reference_path)
        _write_roi_mapping(Path(output), source_data, reference_path)
        return magic_runtime.ultimate_reference_ui.ReferenceRegionEditorResult(
            True,
            output,
            region_count=1,
        )

    runtime = build_runtime(
        calls,
        ask=ask,
        ultimate_linefeed_reference=lambda: str(reference_path),
        ultimate_linefeed_reference_mode=lambda: "similar",
        ultimate_linefeed_reference_regions=lambda: str(regions_path),
        ultimate_linefeed_reference_region_editor_run=editor,
    )

    result = magic_runtime._prepare_ultimate_reference_regions(
        runtime,
        source_data=source_data,
        source_path=str(source_path),
        checkpoint_path=str(tmp_path / "_ULF.checkpoint.jsonl"),
    )

    assert result == str(regions_path)
    assert any(
        call[0] == "ask"
        and call[1][0] == "Ultimate Visual ROI Snapshot:-Use the visible Ultimate preview instead of _ULF.Source.png?"
        for call in calls
    )


def test_ultimate_reference_prompt_skips_when_reference_already_configured(tmp_path):
    calls = []
    runtime = build_runtime(
        calls,
        ask=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("prompt should not open")),
        ultimate_linefeed_reference=lambda: "reference.png",
        ultimate_linefeed_reference_region_editor_run=lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("editor should not open")
        ),
    )

    handled, reference, mode, regions = magic_runtime._maybe_prepare_ultimate_reference_from_prompt(
        runtime,
        source_data=tiny_rgb_png(),
        source_path=str(tmp_path / "_ULF.Source.png"),
        checkpoint_path=str(tmp_path / "_ULF.checkpoint.jsonl"),
        start_offset=0x1234,
    )

    assert (handled, reference, mode, regions) == (False, "", "", "")


def test_ultimate_reference_regions_noninteractive_falls_back_to_auto_patch(tmp_path):
    calls = []
    source_data = tiny_rgb_png()
    source_path = tmp_path / "_ULF.Source.png"
    reference_path = tmp_path / "reference.png"
    source_path.write_bytes(source_data)
    reference_path.write_bytes(source_data)
    runtime = build_runtime(
        calls,
        ultimate_linefeed_reference=lambda: str(reference_path),
        ultimate_linefeed_reference_mode=lambda: "similar",
        ultimate_linefeed_interactive=lambda: False,
        ultimate_linefeed_reference_region_editor_run=lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("editor should not open")
        ),
    )

    result = magic_runtime._prepare_ultimate_reference_regions(
        runtime,
        source_data=source_data,
        source_path=str(source_path),
        checkpoint_path=str(tmp_path / "_ULF.checkpoint.jsonl"),
    )

    assert result == ""
    assert any(
        call[0] == "candy" and "auto-patch" in str(call[1][1])
        for call in calls
    )


def test_ultimate_linefeed_direct_resume_without_adler_match_skips_clone_relaunch():
    calls = []
    side_notes = []
    original_ultimate = magic_runtime.idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce

    def fake_ultimate(data, **kwargs):
        calls.append(("ultimate_kwargs", kwargs))
        before = magic_runtime.idat.analyze_idat_stream(data)
        return magic_runtime.idat_bruteforce.UltimateLinefeedProbeResult(
            before,
            None,
            kwargs.get("target_adler"),
            kwargs.get("start_offset"),
            1,
            4,
            (kwargs.get("start_offset") or 0,),
            0,
            1,
            1,
            0,
            1,
            kwargs.get("checkpoint_path", ""),
            False,
            reason="direct resume test",
        )

    corrupted = linefeed_salvage_fixture()
    linefeed = repair_linefeed_conversion(corrupted, allow_partial=True)
    realignment = magic_runtime.repair_overlong_chunk_length_to_next_header(linefeed.data)
    with tempfile.TemporaryDirectory() as directory:
        source_path = Path(directory) / "_ULF.Source.png"
        source_path.write_bytes(realignment.data)
        runtime = build_runtime(
            calls,
            side_notes,
            ultimate_linefeed_budget=lambda estimate=None: 10,
            ultimate_linefeed_source=lambda: str(source_path),
        )

        magic_runtime.idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce = fake_ultimate
        try:
            result = magic_runtime.run_ultimate_linefeed_direct_resume(
                runtime,
                base_context(corrupted.hex(), sample_name="6.bad.png"),
            )
        finally:
            magic_runtime.idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce = original_ultimate

    write_calls = [call for call in calls if call[0] == "write_clone"]
    assert result is None
    assert not write_calls
    assert ("candy", ("Title", "Ultimate line-feed resume:")) in calls
    assert ("candy", ("Title", "Looking for magic header:")) not in calls
    ultimate_kwargs = [call[1] for call in calls if call[0] == "ultimate_kwargs"][0]
    assert ultimate_kwargs["super_result"] is None
    assert ultimate_kwargs["resume_progress"] is True
    assert ultimate_kwargs["start_offset"] is not None
    assert side_notes
    assert "no candidate survived pruning" in side_notes[0]


def test_ultimate_linefeed_direct_resume_keeps_non_adler_candidate_as_evidence():
    calls = []
    side_notes = []
    final_marks = []
    original_ultimate = magic_runtime.idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce

    def fake_ultimate(data, **kwargs):
        calls.append(("ultimate_kwargs", kwargs))
        before = magic_runtime.idat.analyze_idat_stream(data)
        current_repair = magic_runtime.idat.rebuild_tolerant_idat_salvage(data)
        assert current_repair is not None
        after = magic_runtime.idat.analyze_idat_stream(
            current_repair.data,
            target_adler=kwargs.get("target_adler"),
        )
        assert after.complete is True
        assert after.adler_status != "adler_match"
        candidate = magic_runtime.idat_bruteforce.SuperMegaLinefeedCandidate(
            current_repair.data,
            (),
            before,
            after,
            state_id=7,
            score=magic_runtime.idat_bruteforce.super_mega_linefeed_score(after, 0),
        )
        return magic_runtime.idat_bruteforce.UltimateLinefeedProbeResult(
            before,
            candidate,
            kwargs.get("target_adler"),
            kwargs.get("start_offset"),
            1,
            4,
            (kwargs.get("start_offset") or 0,),
            10,
            11,
            11,
            0,
            1,
            kwargs.get("checkpoint_path", ""),
            False,
            reason="original Adler target was not recovered",
            top_candidates=(candidate,),
        )

    corrupted = linefeed_salvage_fixture()
    linefeed = repair_linefeed_conversion(corrupted, allow_partial=True)
    realignment = magic_runtime.repair_overlong_chunk_length_to_next_header(linefeed.data)
    with tempfile.TemporaryDirectory() as directory:
        source_path = Path(directory) / "_ULF.Source.png"
        source_path.write_bytes(realignment.data)
        runtime = build_runtime(
            calls,
            side_notes,
            ultimate_linefeed_budget=lambda estimate=None: 10,
            ultimate_linefeed_source=lambda: str(source_path),
            mark_ultimate_final_clone=lambda: final_marks.append("marked"),
        )

        magic_runtime.idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce = fake_ultimate
        try:
            result = magic_runtime.run_ultimate_linefeed_direct_resume(
                runtime,
                base_context(corrupted.hex(), sample_name="6.bad.png"),
            )
        finally:
            magic_runtime.idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce = original_ultimate

    assert result is None
    assert not [call for call in calls if call[0] == "write_clone"]
    assert final_marks == []
    assert side_notes
    assert "clone relaunch skipped until original Adler is recovered" in side_notes[0]


def test_ultimate_linefeed_perfect_visual_selection_overrides_current_reconstruction(tmp_path):
    calls = []
    side_notes = []
    final_marks = []
    original_ultimate = magic_runtime.idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce

    preview_path = tmp_path / "selected.png"
    selected_data = tiny_rgb_png()
    preview_path.write_bytes(selected_data)

    def fake_ultimate(data, **kwargs):
        calls.append(("ultimate_kwargs", kwargs))
        before = magic_runtime.idat.analyze_idat_stream(data)
        current_repair = magic_runtime.idat.rebuild_tolerant_idat_salvage(data)
        assert current_repair is not None
        after = magic_runtime.idat.analyze_idat_stream(
            current_repair.data,
            target_adler=kwargs.get("target_adler"),
        )
        candidate = magic_runtime.idat_bruteforce.SuperMegaLinefeedCandidate(
            current_repair.data,
            (),
            before,
            after,
            state_id=7,
            score=magic_runtime.idat_bruteforce.super_mega_linefeed_score(after, 0),
            visual_score=22.0,
            visual_score_kind="similar_manual_roi",
            matched_patch_count=3,
        )
        visual = magic_runtime.idat_bruteforce.UltimateVisualCandidate(
            candidate=candidate,
            preview_data=selected_data,
            preview_strategy="test-preview",
            visual_hash="visual-selected",
            scanline_hash="scanline-selected",
            operation_hash="operation-selected",
            diversity_key="visual-selected",
            rank=magic_runtime.idat_bruteforce._ultimate_visual_candidate_rank(
                candidate,
                coverage=1.0,
                visual_score=22.0,
            ),
            coverage=1.0,
            tested_candidates=10749,
            preview_path=str(preview_path),
        )
        return magic_runtime.idat_bruteforce.UltimateLinefeedProbeResult(
            before,
            candidate,
            kwargs.get("target_adler"),
            kwargs.get("start_offset"),
            1,
            4,
            (kwargs.get("start_offset") or 0,),
            10,
            11,
            11,
            0,
            1,
            kwargs.get("checkpoint_path", ""),
            False,
            reason="user selected visual candidate during Ultimate review",
            top_candidates=(candidate,),
            visual_candidates=(visual,),
            visual_gallery_path=str(tmp_path / "_ULF.visual.json"),
            visual_review_decision="perfect",
            visual_review_selected_paths=(str(preview_path),),
        )

    def selector(_gallery_path, **kwargs):
        calls.append(("selector", kwargs))
        return magic_runtime.ultimate_visual_ui.UltimateVisualSelectionResult(
            selected_preview_paths=(str(preview_path),),
            final_preview_dir=str(tmp_path / "Final_Previews"),
            final_preview_paths=(str(preview_path),),
            decision="perfect",
        )

    corrupted = linefeed_salvage_fixture()
    linefeed = repair_linefeed_conversion(corrupted, allow_partial=True)
    realignment = magic_runtime.repair_overlong_chunk_length_to_next_header(linefeed.data)
    source_path = tmp_path / "_ULF.Source.png"
    source_path.write_bytes(realignment.data)
    runtime = build_runtime(
        calls,
        side_notes,
        ultimate_linefeed_budget=lambda estimate=None: 10,
        ultimate_linefeed_source=lambda: str(source_path),
        ultimate_visual_candidate_selector=selector,
        mark_ultimate_final_clone=lambda: final_marks.append("marked"),
    )

    magic_runtime.idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce = fake_ultimate
    try:
        result = magic_runtime.run_ultimate_linefeed_direct_resume(
            runtime,
            base_context(corrupted.hex(), sample_name="6.bad.png"),
        )
    finally:
        magic_runtime.idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce = original_ultimate

    assert result == "write-result"
    assert final_marks == ["marked"]
    assert [call for call in calls if call[0] == "write_clone"]
    assert side_notes
    assert "user accepted selected Final preview as perfect" in side_notes[0]
    assert "kept current reconstruction" not in side_notes[0]


def test_ultimate_linefeed_keep_searching_after_exhausted_budget_doubles_custom_budget(tmp_path):
    calls = []
    side_notes = []
    budgets = []
    original_ultimate = magic_runtime.idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce

    preview_path = tmp_path / "first.png"
    preview_path.write_bytes(tiny_rgb_png())

    def fake_ultimate(data, **kwargs):
        budgets.append(kwargs.get("budget"))
        calls.append(("ultimate_kwargs", kwargs))
        before = magic_runtime.idat.analyze_idat_stream(data)
        if len(budgets) == 1:
            visual = _visual_candidate_for_magic_runtime(preview_path, state_id=1)
            return magic_runtime.idat_bruteforce.UltimateLinefeedProbeResult(
                before,
                None,
                kwargs.get("target_adler"),
                kwargs.get("start_offset"),
                1,
                4,
                (kwargs.get("start_offset") or 0,),
                10,
                11,
                11,
                0,
                1,
                kwargs.get("checkpoint_path", ""),
                True,
                reason="budget exhausted",
                visual_candidates=(visual,),
                visual_gallery_path=str(tmp_path / "_ULF.visual.json"),
            )
        return magic_runtime.idat_bruteforce.UltimateLinefeedProbeResult(
            before,
            None,
            kwargs.get("target_adler"),
            kwargs.get("start_offset"),
            1,
            4,
            (kwargs.get("start_offset") or 0,),
            20,
            12,
            12,
            0,
            1,
            kwargs.get("checkpoint_path", ""),
            False,
            reason="second pass",
        )

    def selector(_gallery_path, **kwargs):
        calls.append(("selector", kwargs))
        return magic_runtime.ultimate_visual_ui.UltimateVisualSelectionResult(
            decision="keep_searching",
        )

    corrupted = linefeed_salvage_fixture()
    linefeed = repair_linefeed_conversion(corrupted, allow_partial=True)
    realignment = magic_runtime.repair_overlong_chunk_length_to_next_header(linefeed.data)
    source_path = tmp_path / "_ULF.Source.png"
    source_path.write_bytes(realignment.data)
    runtime = build_runtime(
        calls,
        side_notes,
        ultimate_linefeed_budget=lambda estimate=None: 10,
        ultimate_linefeed_source=lambda: str(source_path),
        ultimate_visual_candidate_selector=selector,
    )

    magic_runtime.idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce = fake_ultimate
    try:
        result = magic_runtime.run_ultimate_linefeed_direct_resume(
            runtime,
            base_context(corrupted.hex(), sample_name="6.bad.png"),
        )
    finally:
        magic_runtime.idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce = original_ultimate

    assert result is None
    assert budgets == [10, 20]
    assert calls[0][0] != "write_clone"
    assert any(call[0] == "selector" and call[1]["allow_keep_searching"] is True for call in calls)
    assert any("Keep searching raised budget from 10 to 20" in note for note in side_notes)


def test_ultimate_linefeed_visual_guidance_after_exhausted_budget_resumes_with_selected_preview(tmp_path):
    calls = []
    side_notes = []
    budgets = []
    guidance_paths = []
    original_ultimate = magic_runtime.idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce

    preview_path = tmp_path / "first.png"
    preview_path.write_bytes(tiny_rgb_png())

    def fake_ultimate(data, **kwargs):
        budgets.append(kwargs.get("budget"))
        guidance_paths.append(tuple(kwargs.get("visual_guidance_paths") or ()))
        calls.append(("ultimate_kwargs", kwargs))
        before = magic_runtime.idat.analyze_idat_stream(data)
        if len(budgets) == 1:
            visual = _visual_candidate_for_magic_runtime(preview_path, state_id=1)
            return magic_runtime.idat_bruteforce.UltimateLinefeedProbeResult(
                before,
                None,
                kwargs.get("target_adler"),
                kwargs.get("start_offset"),
                1,
                4,
                (kwargs.get("start_offset") or 0,),
                10,
                11,
                11,
                0,
                1,
                kwargs.get("checkpoint_path", ""),
                True,
                reason="budget exhausted",
                visual_candidates=(visual,),
                visual_gallery_path=str(tmp_path / "_ULF.visual.json"),
            )
        return magic_runtime.idat_bruteforce.UltimateLinefeedProbeResult(
            before,
            None,
            kwargs.get("target_adler"),
            kwargs.get("start_offset"),
            1,
            4,
            (kwargs.get("start_offset") or 0,),
            20,
            12,
            12,
            0,
            1,
            kwargs.get("checkpoint_path", ""),
            False,
            reason="second pass",
        )

    def selector(_gallery_path, **kwargs):
        calls.append(("selector", kwargs))
        return magic_runtime.ultimate_visual_ui.UltimateVisualSelectionResult(
            selected_preview_paths=(str(preview_path),),
            final_preview_dir=str(tmp_path / "Final_Previews"),
            final_preview_paths=(str(preview_path),),
            decision="visual_guidance",
        )

    corrupted = linefeed_salvage_fixture()
    linefeed = repair_linefeed_conversion(corrupted, allow_partial=True)
    realignment = magic_runtime.repair_overlong_chunk_length_to_next_header(linefeed.data)
    source_path = tmp_path / "_ULF.Source.png"
    source_path.write_bytes(realignment.data)
    runtime = build_runtime(
        calls,
        side_notes,
        ultimate_linefeed_budget=lambda estimate=None: 10,
        ultimate_linefeed_source=lambda: str(source_path),
        ultimate_visual_candidate_selector=selector,
    )

    magic_runtime.idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce = fake_ultimate
    try:
        result = magic_runtime.run_ultimate_linefeed_direct_resume(
            runtime,
            base_context(corrupted.hex(), sample_name="6.bad.png"),
        )
    finally:
        magic_runtime.idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce = original_ultimate

    assert result is None
    assert budgets == [10, 20]
    assert guidance_paths == [(), (str(preview_path),)]
    assert any("visual guidance raised budget from 10 to 20" in note for note in side_notes)


def test_ultimate_linefeed_direct_resume_without_source_snapshot_falls_back():
    calls = []
    runtime = build_runtime(calls, ultimate_linefeed_source=lambda: "missing-source.png")

    result = magic_runtime.run_ultimate_linefeed_direct_resume(
        runtime,
        base_context(linefeed_salvage_fixture().hex(), sample_name="6.bad.png"),
    )

    assert result is None
    assert not [call for call in calls if call[0] == "write_clone"]
    fallback_calls = [
        call
        for call in calls
        if call[0] == "candy"
        and call[1][0] == "Cowsay"
        and (
            "no clean Ultimate source snapshot yet" in str(call[1][1])
            or "finish the file tour before resuming Ultimate" in str(call[1][1])
        )
    ]
    assert fallback_calls == [
        (
            "candy",
            (
                "Cowsay",
                "I found a resume checkpoint, but no clean Ultimate source snapshot yet.",
                "bad",
            ),
        ),
        (
            "candy",
            (
                "Cowsay",
                "I will finish the file tour before resuming Ultimate.",
                "com",
            ),
        ),
    ]


def test_ultimate_budget_plan_uses_prompt_candy_without_dialogue_pause():
    calls = []
    runtime = build_runtime(
        calls,
        prompt_candy=lambda *args: calls.append(("prompt_candy", args)),
        clear_dialogue_pause=lambda *args: calls.append(("clear_dialogue_pause", args)),
    )
    estimate = SimpleNamespace(
        operation_count=641,
        max_depth=4,
        total_combinations=7_012_540_641,
    )
    decision = magic_runtime.idat_bruteforce.ultimate_linefeed_budget_decision(
        estimate.total_combinations,
        "inception",
    )

    magic_runtime._emit_ultimate_budget_plan(runtime, estimate, decision, "checkpoint.jsonl")

    assert calls == [
        (
            "prompt_candy",
            (
                "Cowsay",
                "Ultimate budget selected:\n"
                "mode: inception\n"
                "selected budget: 3,506,270,321\n"
                "coverage: 50.0000 %\n"
                "rough ETA @ 100 candidates/s: 1y 40d\n"
                "chunky forecast: Multi-year archaeology, but with pixels.\n"
                "checkpoint: enabled\n"
                "progress: disabled",
                "com",
            ),
        ),
        ("clear_dialogue_pause", ()),
    ]


def test_ultimate_budget_plan_unbounded_eta_uses_joke_line():
    calls = []
    runtime = build_runtime(
        calls,
        prompt_candy=lambda *args: calls.append(("prompt_candy", args)),
        clear_dialogue_pause=lambda *args: calls.append(("clear_dialogue_pause", args)),
    )
    estimate = SimpleNamespace(
        operation_count=641,
        max_depth=4,
        total_combinations=7_012_540_641,
    )
    decision = magic_runtime.idat_bruteforce.ultimate_linefeed_budget_decision(
        estimate.total_combinations,
        "unbounded",
    )

    magic_runtime._emit_ultimate_budget_plan(runtime, estimate, decision, "checkpoint.jsonl")

    text = calls[0][1][1]
    assert "mode: no limit" in text
    assert "selected budget: unbounded" in text
    assert (
        "rough ETA @ 100 candidates/s: unbounded "
        "(13 billion years, I'm kidding... but not that much)"
    ) in text


def test_ultimate_interrupt_flush_progress_announces_once_and_counts():
    magic_runtime._ULTIMATE_FLUSH_RUNTIME_STATE.clear()
    calls = []
    runtime = build_runtime(
        calls,
        clear_dialogue_pause=lambda *args: calls.append(("clear_dialogue_pause", args)),
    )
    progress = magic_runtime._ultimate_linefeed_interrupt_flush_progress(runtime)

    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        progress(34, 123)
        progress(35, 123)

    assert calls == [
        (
            "candy",
            (
                "Cowsay",
                "Chunky is saving the remaining visual candidates. Please wait a little before leaving the vault.",
                "com",
            ),
        ),
        ("clear_dialogue_pause", ()),
    ]
    text = output.getvalue()
    assert "\r-Ultimate visual flush: 34/123" in text
    assert "\r-Ultimate visual flush: 35/123" in text


def test_ultimate_interrupt_flush_progress_shares_state_across_callbacks():
    magic_runtime._ULTIMATE_FLUSH_RUNTIME_STATE.clear()
    calls = []
    runtime = build_runtime(
        calls,
        clear_dialogue_pause=lambda *args: calls.append(("clear_dialogue_pause", args)),
    )
    first = magic_runtime._ultimate_linefeed_interrupt_flush_progress(runtime)
    second = magic_runtime._ultimate_linefeed_interrupt_flush_progress(runtime)

    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        first(6, 100)
        second(6, 100)
        second(7, 100)

    assert calls == [
        (
            "candy",
            (
                "Cowsay",
                "Chunky is saving the remaining visual candidates. Please wait a little before leaving the vault.",
                "com",
            ),
        ),
        ("clear_dialogue_pause", ()),
    ]
    text = output.getvalue()
    assert text.count("Ultimate visual flush") == 2
    assert "\r-Ultimate visual flush: 6/100" in text
    assert "\r-Ultimate visual flush: 7/100" in text


def test_ultimate_interrupt_flush_progress_is_monotone_and_skips_duplicates():
    magic_runtime._ULTIMATE_FLUSH_RUNTIME_STATE.clear()
    calls = []
    runtime = build_runtime(calls)
    progress = magic_runtime._ultimate_linefeed_interrupt_flush_progress(runtime)

    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        progress(90, 100)
        progress(90, 100)
        progress(89, 100)
        progress(91, 100)

    text = output.getvalue()
    assert text.count("Ultimate visual flush") == 2
    assert "\r-Ultimate visual flush: 90/100" in text
    assert "\r-Ultimate visual flush: 91/100" in text
    assert "89/100" not in text


def test_ultimate_interrupt_repeat_warning_throttles_and_rotates_lines(monkeypatch):
    magic_runtime._ULTIMATE_INTERRUPT_WARNING_STATE.clear()
    calls = []
    runtime = build_runtime(
        calls,
        clear_dialogue_pause=lambda *args: calls.append(("clear_dialogue_pause", args)),
    )
    warning = magic_runtime._ultimate_linefeed_interrupt_repeat_warning(runtime)
    now = [100.0]
    monkeypatch.setattr(magic_runtime.time, "monotonic", lambda: now[0])

    warning(1)
    warning(2)
    now[0] += magic_runtime.ULTIMATE_INTERRUPT_WARNING_INTERVAL_SECONDS + 0.1
    warning(3)

    assert calls == [
        (
            "candy",
            (
                "Cowsay",
                "I heard you. The workers are parking the shards.",
                "com",
            ),
        ),
        ("clear_dialogue_pause", ()),
        (
            "candy",
            (
                "Cowsay",
                "More Ctrl+C will not make zlib confess faster.",
                "com",
            ),
        ),
        ("clear_dialogue_pause", ()),
    ]


def test_ultimate_resume_budget_guard_rejects_low_override():
    calls = []
    runtime = build_runtime(
        calls,
        ultimate_linefeed_budget=lambda estimate=None: magic_runtime.idat_bruteforce.UltimateLinefeedBudgetDecision(
            "override",
            100,
            coverage=1.0,
        ),
    )
    estimate = SimpleNamespace(total_combinations=10_000)
    progress = SimpleNamespace(tested_candidates=250)

    decision = magic_runtime._ultimate_linefeed_budget_with_resume_guard(runtime, estimate, progress)

    assert decision.aborted is True
    assert decision.mode == "resume_budget_too_low"
    assert any("already tested 250 candidates" in str(call) for call in calls)


def test_ultimate_resume_budget_guard_bumps_auto_budget():
    calls = []
    runtime = build_runtime(
        calls,
        ultimate_linefeed_budget=lambda estimate=None: magic_runtime.idat_bruteforce.UltimateLinefeedBudgetDecision(
            "normal",
            100,
            coverage=1.0,
        ),
        ultimate_linefeed_interactive=lambda: False,
    )
    estimate = SimpleNamespace(total_combinations=10_000)
    progress = SimpleNamespace(tested_candidates=250)

    decision = magic_runtime._ultimate_linefeed_budget_with_resume_guard(runtime, estimate, progress)

    assert decision.aborted is False
    assert decision.budget == 350
    assert decision.mode == "normal"
    assert any("bumped this auto run to 350 candidates" in str(call) for call in calls)


def test_find_magic_runtime_too_low_without_known_chunks_ends_with_note():
    calls = []
    side_notes = []
    runtime = build_runtime(calls, side_notes)

    result = magic_runtime.run_find_fucking_magic(
        runtime,
        base_context("ff" * 60),
    )

    assert result is None
    assert ("end",) in calls
    assert "-FindFuckingMagic:Haven't found any known png chunk in this file." in side_notes


def test_find_magic_runtime_too_low_prepends_magic_before_nearest_chunk():
    calls = []
    runtime = build_runtime(calls)
    data_hex = ("ff" * 20) + b"IHDR".hex() + ("00" * 4) + b"IDAT".hex() + ("00" * 8)

    result = magic_runtime.run_find_fucking_magic(runtime, base_context(data_hex))

    expected = magic_runtime.MAGIC + "ffffffff" + data_hex[40:]
    assert result == "checkpoint-result"
    assert ("spec_length", b"IHDR", "ffffffff") in calls
    assert checkpoint_args(calls) == (
        False,
        False,
        "FindFuckingMagic",
        "PngSig",
        ["-Prepending Magic"],
        expected,
        "0x14",
    )


def build_namespace(calls, side_notes):
    return {
        "Candy": lambda *args: calls.append(("candy", args)),
        "Prompt_Candy": lambda *args: calls.append(("prompt_candy", args)),
        "Clear_Terminal_Dialogue_Pause": lambda *args: calls.append(("clear_dialogue_pause", args)),
        "PRINT": lambda message: calls.append(("emit", message)),
        "CheckPoint": lambda *args: calls.append(("checkpoint", args)),
        "TheEnd": lambda: calls.append(("end",)),
        "Betterror": lambda *args: calls.append(("betterror", args)),
        "Pause": lambda message: calls.append(("pause", message)),
        "SpecLength": lambda *args: calls.append(("spec", args)),
        "Minibar": lambda: calls.append(("minibar",)),
        "WriteClone": lambda *args: calls.append(("write_clone", args)),
        "SideNotes": side_notes,
        "ChunkStory": lambda *args: calls.append(("story", args)),
        "DATA_BYTES": b"png",
        "DATAX": "706e67",
        "CHUNKS": [b"IHDR", b"IDAT"],
        "BEFORE_IDAT": [b"IHDR"],
        "Sample_Name": "sample.png",
        "DEBUG": True,
        "PAUSEDEBUG": False,
        "PAUSEERROR": True,
    }


def test_find_magic_namespace_bridge_injects_chunk_story_and_context():
    calls = []
    side_notes = []
    namespace = build_namespace(calls, side_notes)

    def runner(runtime, context):
        assert runtime.candy is namespace["Candy"]
        assert runtime.emit is namespace["PRINT"]
        assert runtime.checkpoint is namespace["CheckPoint"]
        assert runtime.end is namespace["TheEnd"]
        assert runtime.betterror is namespace["Betterror"]
        assert runtime.pause is namespace["Pause"]
        assert runtime.spec_length is namespace["SpecLength"]
        assert runtime.minibar is namespace["Minibar"]
        assert runtime.write_clone is namespace["WriteClone"]
        assert runtime.side_notes is side_notes
        assert runtime.chunk_story is namespace["ChunkStory"]
        assert context.data_bytes == b"png"
        assert context.data_hex == "706e67"
        assert context.chunks == (b"IHDR", b"IDAT")
        assert context.before_idat == (b"IHDR",)
        assert context.sample_name == "sample.png"
        assert context.debug is True
        assert context.pause_debug is False
        assert context.pause_error is True
        return "magic"

    assert magic_runtime.run_find_magic_from_namespace(namespace, runner=runner) == "magic"


def test_find_fucking_magic_namespace_bridge_keeps_default_chunk_story():
    calls = []
    side_notes = []
    namespace = build_namespace(calls, side_notes)

    def runner(runtime, context):
        runtime.chunk_story("add", "PNG")
        assert not [call for call in calls if call[0] == "story"]
        assert context.sample_name == "sample.png"
        return "hard-magic"

    assert magic_runtime.run_find_fucking_magic_from_namespace(namespace, runner=runner) == "hard-magic"


def main():
    checks = [
        ("Header found", test_find_header_magic_runtime_found_at_start_records_story_and_checkpoint),
        ("Header cut", test_find_header_magic_runtime_cut_at_signature_routes_checkpoint),
        ("Header deep search", test_find_header_magic_runtime_deep_search_checkpoint),
        ("Header linefeed repair", test_find_header_magic_runtime_repairs_linefeed_conversion_with_clone),
        (
            "Header inserted CRLF repair",
            test_find_header_magic_runtime_repairs_inserted_crlf_conversion_with_clone,
        ),
        ("Header linefeed salvage", test_find_header_magic_runtime_writes_linefeed_salvage_clone),
        (
            "Header linefeed deferred",
            test_find_header_magic_runtime_can_defer_linefeed_signature_repair,
        ),
        (
            "Header linefeed deferred apply",
            test_deferred_linefeed_signature_repair_writes_after_tour,
        ),
        (
            "Header linefeed deferred internal IDAT",
            test_deferred_internal_idat_marker_chain_repair_uses_marker_chain_path,
        ),
        (
            "Header linefeed evidence guard",
            test_linefeed_chunk_evidence_requires_chunk_level_proof_for_idat_bruteforce,
        ),
        (
            "Header linefeed evidence IDAT",
            test_linefeed_chunk_evidence_allows_idat_realign_and_payload_patch,
        ),
        (
            "Header linefeed length before brute force",
            test_linefeed_full_bruteforce_checks_length_realign_before_prompt,
        ),
        (
            "Header linefeed known gap to SuperMega",
            test_linefeed_full_bruteforce_passes_known_gap_to_super_probe,
        ),
        (
            "Header linefeed final salvage promotion",
            test_linefeed_final_salvage_promotes_equal_scanline_pixel_repair,
        ),
        (
            "Header linefeed direct SuperMega",
            test_find_header_magic_runtime_can_launch_supermega_directly_after_salvage,
        ),
        (
            "Header linefeed decline direct SuperMega",
            test_find_header_magic_runtime_can_decline_direct_supermega,
        ),
        ("Header linefeed ultimate probe", test_find_header_magic_runtime_can_launch_ultimate_linefeed_probe),
        (
            "Ultimate ROI uses visible preview",
            test_ultimate_reference_prompt_can_use_visible_preview_for_roi_source,
        ),
        (
            "Ultimate ROI source decline keeps snapshot",
            test_ultimate_reference_regions_prompt_keeps_source_snapshot_when_preview_declined,
        ),
        ("Ultimate progress zero draw", test_linefeed_queue_progress_draws_zero_state_after_build),
        (
            "Header linefeed ultimate direct resume",
            test_ultimate_linefeed_direct_resume_without_adler_match_skips_clone_relaunch,
        ),
        (
            "Header linefeed ultimate non-Adler evidence",
            test_ultimate_linefeed_direct_resume_keeps_non_adler_candidate_as_evidence,
        ),
        (
            "Header linefeed ultimate keep searching budget bump",
            test_ultimate_linefeed_keep_searching_after_exhausted_budget_doubles_custom_budget,
        ),
        (
            "Header linefeed ultimate visual guidance budget bump",
            test_ultimate_linefeed_visual_guidance_after_exhausted_budget_resumes_with_selected_preview,
        ),
        (
            "Header linefeed ultimate direct resume fallback",
            test_ultimate_linefeed_direct_resume_without_source_snapshot_falls_back,
        ),
        (
            "Header linefeed ultimate budget no pause",
            test_ultimate_budget_plan_uses_prompt_candy_without_dialogue_pause,
        ),
        (
            "Header linefeed ultimate interrupt flush progress",
            test_ultimate_interrupt_flush_progress_announces_once_and_counts,
        ),
        (
            "Header linefeed ultimate interrupt flush monotone",
            test_ultimate_interrupt_flush_progress_is_monotone_and_skips_duplicates,
        ),
        (
            "Header linefeed ultimate interrupt repeat warning",
            test_ultimate_interrupt_repeat_warning_throttles_and_rotates_lines,
        ),
        (
            "Header linefeed ultimate resume budget guard override",
            test_ultimate_resume_budget_guard_rejects_low_override,
        ),
        (
            "Header linefeed ultimate resume budget guard auto",
            test_ultimate_resume_budget_guard_bumps_auto_budget,
        ),
        ("Single candidate", test_find_magic_runtime_single_candidate_cuts_at_best_magic),
        ("No known chunks", test_find_magic_runtime_too_low_without_known_chunks_ends_with_note),
        ("Prepend nearest", test_find_magic_runtime_too_low_prepends_magic_before_nearest_chunk),
        ("Namespace FindMagic", test_find_magic_namespace_bridge_injects_chunk_story_and_context),
        ("Namespace FindFuckingMagic", test_find_fucking_magic_namespace_bridge_keeps_default_chunk_story),
    ]

    print("Running magic runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"magic runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
