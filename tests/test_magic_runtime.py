#!/usr/bin/env python3
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
    ultimate_visual_gallery_limit=None,
    ultimate_visual_min_coverage=None,
    ultimate_candidate_preview=None,
    defer_linefeed_signature_repair=None,
    prompt_candy=None,
    clear_dialogue_pause=None,
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
        ultimate_source_path=ultimate_linefeed_source or (lambda: ""),
        ultimate_visual_gallery_limit=ultimate_visual_gallery_limit
        or (lambda: magic_runtime.idat_bruteforce.ULTIMATE_LINEFEED_VISUAL_GALLERY_LIMIT),
        ultimate_visual_min_coverage=ultimate_visual_min_coverage
        or (lambda: magic_runtime.idat_bruteforce.ULTIMATE_LINEFEED_VISUAL_MIN_COVERAGE),
        ultimate_candidate_preview=ultimate_candidate_preview,
        defer_linefeed_signature_repair=defer_linefeed_signature_repair or (lambda *args: False),
    )


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


def tiny_rgb_png():
    ihdr = b"\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
    return PNG_SIGNATURE + build_png_chunk(b"IHDR", ihdr) + build_png_chunk(
        b"IDAT",
        b"\x78\x01\x01\x04\x00\xfb\xff\x00\x00\x00\x00\x00\x04\x00\x01",
    ) + IEND_CHUNK


def linefeed_salvage_fixture():
    return (ROOT / "Png_Errors_handled_by_Chunklate_So_Far" / "linefeedcorruption3.png").read_bytes()


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
    assert "partial-idat-tolerant-row-salvage decoded 498/503 scanlines" in write_calls[0][2]
    assert "reused previous row for 5 bad filter rows" in write_calls[0][2]
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
        and "498/503 scanlines" in message
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

    assert alternative.repair.recovered_scanlines == 495
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
        ("SuperMegaLineFeedForceOfDeath", "super-mega-linefeed-force-of-death-0x3ee9-498"),
    ) in calls
    assert (
        "ask",
        ("UltimateMegaSuperLineFeedBruteForce", "ultimate-mega-super-linefeed-bruteforce-0x3ee9-500"),
    ) in calls
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
    assert "partial-idat-tolerant-row-salvage decoded 500/503 scanlines" in write_calls[0][2]
    assert "SuperMegaLineFeedForceOfDeath" in write_calls[0][2]
    assert [call for call in calls if call[0] == "loadingbar"]
    assert not [call for call in calls if call[0] == "minibar"]
    preview_calls = [call for call in calls if call[0] == "preview"]
    assert len(preview_calls) == 1
    assert preview_calls[0][1][1] == "UltimateMegaSuperLineFeedBruteForce_Before"
    assert calls.index(preview_calls[0]) < calls.index(
        (
            "ask",
            ("UltimateMegaSuperLineFeedBruteForce", "ultimate-mega-super-linefeed-bruteforce-0x3ee9-500"),
        )
    )
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
        ultimate_candidate_preview=live_preview,
        clear_dialogue_pause=lambda *args: calls.append(("clear_dialogue_pause", args)),
    )
    corrupted = linefeed_salvage_fixture()

    magic_runtime.idat_bruteforce.probe_super_mega_linefeed_force_of_death = fast_super_mega
    magic_runtime.idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce = fake_ultimate
    try:
        result = magic_runtime.run_find_magic(runtime, base_context(corrupted.hex()))
    finally:
        magic_runtime.idat_bruteforce.probe_super_mega_linefeed_force_of_death = original_super_mega
        magic_runtime.idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce = original_ultimate

    write_calls = [call for call in calls if call[0] == "write_clone"]
    ultimate_asks = [
        call
        for call in calls
        if call[0] == "ask" and call[1][0] == "UltimateMegaSuperLineFeedBruteForce"
    ]
    assert result == "write-result"
    assert ultimate_asks
    assert ultimate_asks[0][2] == {"skipauto": True}
    assert ("candy", ("Title", "UltimateMegaSuperLineFeedBruteForce")) in calls
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
    assert "UltimateMegaSuperLineFeedBruteForce: start=0x3ee9" in write_calls[0][2]
    assert "test budget" in write_calls[0][2]
    assert side_notes == [write_calls[0][2]]


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


def test_ultimate_linefeed_resume_message_handles_complete_phase(tmp_path):
    progress_path = tmp_path / "_ULF.progress.json"
    progress_path.write_text(json.dumps({"phase": "complete"}), encoding="utf-8")

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


def test_ultimate_linefeed_direct_resume_skips_find_magic_tour():
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
    assert result == "write-result"
    assert write_calls
    assert validate_png_structure(bytes.fromhex(write_calls[0][1])).ok
    assert ("candy", ("Title", "Ultimate line-feed resume:")) in calls
    assert ("candy", ("Title", "Looking for magic header:")) not in calls
    ultimate_kwargs = [call[1] for call in calls if call[0] == "ultimate_kwargs"][0]
    assert ultimate_kwargs["super_result"] is None
    assert ultimate_kwargs["resume_progress"] is True
    assert ultimate_kwargs["start_offset"] is not None
    assert side_notes == [write_calls[0][2]]


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
        ("Ultimate progress zero draw", test_linefeed_queue_progress_draws_zero_state_after_build),
        (
            "Header linefeed ultimate direct resume",
            test_ultimate_linefeed_direct_resume_skips_find_magic_tour,
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
