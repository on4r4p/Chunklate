#!/usr/bin/env python3
import sys
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
        ultimate_linefeed_budget=ultimate_linefeed_budget or (lambda: 50000),
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


def test_find_header_magic_runtime_writes_linefeed_salvage_clone():
    calls = []
    side_notes = []
    runtime = build_runtime(calls, side_notes)
    corrupted = (ROOT / "David" / "6.bad.png").read_bytes()

    result = magic_runtime.run_find_magic(runtime, base_context(corrupted.hex()))

    write_calls = [call for call in calls if call[0] == "write_clone"]
    assert result == "write-result"
    assert len(write_calls) == 1
    assert validate_png_structure(bytes.fromhex(write_calls[0][1])).ok
    assert "validation error after CR restoration" in write_calls[0][2]
    assert "partial-idat-tolerant-row-salvage decoded 495/503 scanlines" in write_calls[0][2]
    assert "reused previous row for 8 bad filter rows" in write_calls[0][2]
    assert "Line feed conversion evidence: IDAT chunk length overran the next chunk by 4 bytes" in write_calls[0][2]
    assert side_notes == [write_calls[0][2]]
    assert ("end",) not in calls


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
    corrupted = (ROOT / "David" / "6.bad.png").read_bytes()
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

    corrupted = (ROOT / "David" / "6.bad.png").read_bytes()
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


def test_find_header_magic_runtime_can_choose_linefeed_heavy_probe():
    calls = []
    side_notes = []
    answers = [True, True, False]
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
    corrupted = (ROOT / "David" / "6.bad.png").read_bytes()

    magic_runtime.idat_bruteforce.probe_super_mega_linefeed_force_of_death = fast_super_mega
    try:
        result = magic_runtime.run_find_magic(runtime, base_context(corrupted.hex()))
    finally:
        magic_runtime.idat_bruteforce.probe_super_mega_linefeed_force_of_death = original_super_mega

    write_calls = [call for call in calls if call[0] == "write_clone"]
    assert result == "write-result"
    assert ("ask", ("LineFeed Heavy Probe", "linefeed-cr-insert-0-495")) in calls
    assert (
        "ask",
        ("SuperMegaLineFeedForceOfDeath", "super-mega-linefeed-force-of-death-0x3ee9-503"),
    ) in calls
    assert (
        "ask",
        ("UltimateMegaSuperLineFeedBruteForce", "ultimate-mega-super-linefeed-bruteforce-0x3ee9-503"),
    ) in calls
    assert not [
        call
        for call in calls
        if call == ("ask", ("LineFeed Heavy Probe", "linefeed-cr-insert-1-503"))
    ]
    assert ("candy", ("Title", "LineFeed Heavy Probe")) in calls
    assert ("candy", ("Title", "SuperMegaLineFeedForceOfDeath")) in calls
    assert len(write_calls) == 1
    assert validate_png_structure(bytes.fromhex(write_calls[0][1])).ok
    assert "IDAT line-feed probe: strategy=linefeed-cr-insert" in write_calls[0][2]
    assert "SuperMegaLineFeedForceOfDeath: anchor=0x3ee9; search=" in write_calls[0][2]
    assert "pre_error_backtrack=0x" in write_calls[0][2]
    assert "phase4-heavy-byte-window phase" in write_calls[0][2]
    assert "UltimateMegaSuperLineFeedBruteForce: user declined" in write_calls[0][2]
    assert "partial-idat-blackfill recovered 503/503 scanlines" in write_calls[0][2]
    assert "SuperMegaLineFeedForceOfDeath" in write_calls[0][2]
    assert [call for call in calls if call[0] == "loadingbar"]
    assert not [call for call in calls if call[0] == "minibar"]
    preview_calls = [call for call in calls if call[0] == "preview"]
    assert len(preview_calls) == 3
    assert preview_calls[0][1][1] == "LineFeed_IDAT_00_495_of_503"
    assert preview_calls[1][1][1] == "LineFeed_IDAT_01_503_of_503"
    assert preview_calls[2][1][1] == "UltimateMegaSuperLineFeedBruteForce_Before"
    assert calls.index(preview_calls[0]) < calls.index(("ask", ("LineFeed Heavy Probe", "linefeed-cr-insert-0-495")))
    assert calls.index(preview_calls[1]) < calls.index(
        (
            "ask",
            ("SuperMegaLineFeedForceOfDeath", "super-mega-linefeed-force-of-death-0x3ee9-503"),
        )
    )
    assert calls.index(preview_calls[2]) < calls.index(
        (
            "ask",
            ("UltimateMegaSuperLineFeedBruteForce", "ultimate-mega-super-linefeed-bruteforce-0x3ee9-503"),
        )
    )
    assert side_notes == [write_calls[0][2]]
    assert ("end",) not in calls


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

    runtime = build_runtime(calls, side_notes, ask=ask, ultimate_linefeed_budget=lambda: 1234)
    corrupted = (ROOT / "David" / "6.bad.png").read_bytes()

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
    ultimate_prompt_lines = [
        call[1][1]
        for call in calls
        if call[0] == "candy"
        and call[1][0] == "Cowsay"
        and "UltimateMegaSuperLineFeedBruteForce is the last basement door" in str(call[1][1])
    ]
    assert ultimate_prompt_lines
    assert "--ultimate-linefeed-budget 1000000000000" in ultimate_prompt_lines[0]
    assert "--ultimate-linefeed-unbounded" in ultimate_prompt_lines[0]
    assert [call for call in calls if call[0] == "loadingbar"]
    assert [call for call in calls if call[0] == "ultimate_kwargs"][0][1]["budget"] == 1234
    assert "UltimateMegaSuperLineFeedBruteForce: start=0x3ee9" in write_calls[0][2]
    assert "test budget" in write_calls[0][2]
    assert side_notes == [write_calls[0][2]]


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
        ("Header linefeed salvage", test_find_header_magic_runtime_writes_linefeed_salvage_clone),
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
        ("Header linefeed heavy probe", test_find_header_magic_runtime_can_choose_linefeed_heavy_probe),
        ("Header linefeed ultimate probe", test_find_header_magic_runtime_can_launch_ultimate_linefeed_probe),
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
