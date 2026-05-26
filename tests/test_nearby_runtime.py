#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import nearby, nearby_runtime
from chunklate.png import PNG_SIGNATURE, build_png_chunk


def build_runtime(calls, side_notes=None, *, excluded=(), clean_result=None, bad_critical=False):
    if side_notes is None:
        side_notes = []

    def candy(kind, *args):
        calls.append(("candy", (kind,) + args))
        if kind == "Color":
            return "<%s:%s>" % (args[0], args[1])
        if kind == "Emoj":
            return ":%s:" % args[0]
        return "candy:%s" % kind

    return nearby_runtime.NearbyChunkRuntime(
        candy=candy,
        emit=lambda message: calls.append(("emit", message)),
        checkpoint=lambda *args: calls.append(("checkpoint", args)) or "checkpoint-result",
        check_chunk_order=lambda *args: calls.append(("check_chunk_order", args)) or list(excluded),
        clean_extra_bytes=lambda *args: calls.append(("clean_extra_bytes", args)) or clean_result,
        double_check=lambda *args: calls.append(("double_check", args)),
        fix_it_felix=lambda *args: calls.append(("fix_it_felix", args)) or "fixit-result",
        betterror=lambda error, name: calls.append(("betterror", str(error), name)),
        pause=lambda message: calls.append(("pause", message)),
        end=lambda: calls.append(("end",)),
        get_bad_critical=lambda: bad_critical,
        side_notes=side_notes,
    )


def build_remove_extra_runtime(calls, side_notes=None):
    if side_notes is None:
        side_notes = []

    return nearby_runtime.RemoveExtraBytesRuntime(
        save_clone=lambda *args: calls.append(("save_clone", args)) or "saved",
        side_notes=side_notes,
    )


def build_double_check_runtime(calls):
    def candy(kind, *args):
        calls.append(("candy", (kind,) + args))
        if kind == "Color":
            return "<%s:%s>" % (args[0], args[1])
        return "candy:%s" % kind

    return nearby_runtime.DoubleCheckRuntime(
        candy=candy,
        emit=lambda message: calls.append(("emit", message)),
        end=lambda: calls.append(("end",)),
        nearby_chunk=lambda *args, **kwargs: calls.append(("nearby_chunk", args, kwargs)) or "nearby-result",
    )


def base_context(**updates):
    values = {
        "data_hex": ("00" * 8) + b"IDAT".hex() + ("00" * 8),
        "chunks": (b"IHDR", b"IDAT", b"IEND"),
        "all_chunks": (b"IHDR", b"IDAT", b"IEND"),
        "current_length_offset": 0,
        "current_length_offset_hex": "0x0",
        "current_data_offset_byte": 8,
        "chunks_history": (b"PNG", b"IHDR"),
        "chunks_history_index": ("0:0:8", "1:8:16"),
        "original_chunk_type": b"IHDR",
        "original_chunk_length": "ffffffff",
        "sample_name": "sample.png",
    }
    values.update(updates)
    return nearby_runtime.NearbyChunkContext(**values)


def remove_extra_context(data_hex, **updates):
    values = {
        "data_hex": data_hex,
        "current_length_offset": len(PNG_SIGNATURE) * 2,
        "known_chunks": (b"IDAT",),
        "all_chunks": (b"IHDR", b"IDAT", b"IEND"),
    }
    values.update(updates)
    return nearby_runtime.RemoveExtraBytesContext(**values)


def checkpoint_args(calls):
    matches = [call[1] for call in calls if call[0] == "checkpoint"]
    assert len(matches) == 1
    return matches[0]


def test_nearby_runtime_returns_clean_extra_bytes_before_scan():
    calls = []
    runtime = build_runtime(calls, clean_result="cleaned")

    result = nearby_runtime.run_nearby_chunk(
        runtime,
        base_context(),
        b"fake",
        "0",
        b"IHDR",
        False,
        "Relics",
    )

    assert result == "cleaned"
    assert ("check_chunk_order", (b"IHDR", "Fix")) in calls
    assert ("clean_extra_bytes", (b"fake", b"IHDR", [])) in calls
    assert not [call for call in calls if call[0] == "checkpoint"]


def test_nearby_runtime_known_chunk_routes_length_repair_checkpoint():
    calls = []
    runtime = build_runtime(calls)

    result = nearby_runtime.run_nearby_chunk(
        runtime,
        base_context(),
        b"IHDR",
        "ffffffff",
        b"IHDR",
        False,
        "Relics",
    )

    repair = nearby.known_chunk_length_repair(
        display_chunk=b"IHDR",
        old_length="ffffffff",
        current_length_offset=0,
        current_length_offset_hex="0x0",
        current_data_offset_byte=8,
        found_chunk=b"IDAT",
        found_chunk_type_offset=16,
    )
    assert result == "checkpoint-result"
    assert checkpoint_args(calls) == (
        True,
        True,
        "NearbyChunk",
        b"IHDR",
        [repair.solved_message],
        repair.fixed_length,
        repair.replace_start,
        repair.replace_end,
        b"IHDR",
        "Relics",
    )


def test_nearby_runtime_excluded_found_chunk_routes_legacy_trap():
    calls = []
    side_notes = []
    runtime = build_runtime(calls, side_notes, excluded=(b"IDAT",))

    nearby_runtime.run_nearby_chunk(
        runtime,
        base_context(),
        b"IHDR",
        "ffffffff",
        b"IHDR",
        False,
    )

    assert "-NearbyChunk:Missplaced Chunk" in side_notes
    assert ("end",) in calls


def test_nearby_runtime_summarizes_candidates_without_alignment_in_normal_mode():
    calls = []
    runtime = build_runtime(calls)
    data_hex = (
        ("00" * 8)
        + b"IDAT".hex()
        + ("00" * 4)
        + b"IDAT".hex()
        + ("00" * 4)
        + b"IEND".hex()
    )

    result = nearby_runtime.run_nearby_chunk(
        runtime,
        base_context(data_hex=data_hex),
        b"@DAT",
        "04002000",
        b"IDAT",
        False,
        "Relics",
    )

    assert result == ()
    assert (
        "candy",
        ("Cowsay", "I found 2 possible IDAT chunks and an IEND later.", "good"),
    ) in calls
    assert (
        "candy",
        ("Cowsay", "But the current position still does not line up.", "bad"),
    ) in calls
    assert (
        "candy",
        (
            "Cowsay",
            "This smells more like a bad length before @DAT than a chunk-name-only problem.",
            "bad",
        ),
    ) in calls
    assert not [call for call in calls if call == ("candy", ("Cowsay", " Bingo!!!", "good"))]
    assert not any(
        call[0] == "candy" and "found nothing" in str(call[1])
        for call in calls
    )
    assert [call for call in calls if call[0] == "double_check"]


def test_nearby_runtime_keeps_bingo_details_in_debug_mode():
    calls = []
    runtime = build_runtime(calls)
    data_hex = ("00" * 8) + b"IDAT".hex() + ("00" * 4) + b"IEND".hex()

    nearby_runtime.run_nearby_chunk(
        runtime,
        base_context(data_hex=data_hex, debug=True),
        b"@DAT",
        "04002000",
        b"IDAT",
        False,
        "Relics",
    )

    assert ("candy", ("Cowsay", " Bingo!!!", "good")) in calls
    assert any(
        call[0] == "emit" and "-Found the closest Chunk to our position:" in call[1]
        for call in calls
    )
    assert not any(
        call[0] == "candy" and "does not line up" in str(call[1])
        for call in calls
    )


def test_nearby_runtime_alignment_still_routes_repair_without_summary():
    calls = []
    runtime = build_runtime(calls)

    result = nearby_runtime.run_nearby_chunk(
        runtime,
        base_context(),
        b"IHDR",
        "ffffffff",
        b"IHDR",
        False,
        "Relics",
    )

    assert result == "checkpoint-result"
    assert [call for call in calls if call[0] == "checkpoint"]
    assert not any(
        call[0] == "candy" and "does not line up" in str(call[1])
        for call in calls
    )


def test_nearby_runtime_doublecheck_missing_critical_routes_fixit():
    calls = []
    side_notes = []
    runtime = build_runtime(calls, side_notes, bad_critical=b"IEND")
    context = base_context(data_hex="00" * 20)

    result = nearby_runtime.run_nearby_chunk(
        runtime,
        context,
        b"IHDR",
        "0",
        b"IHDR",
        True,
    )

    assert result == "fixit-result"
    assert ("check_chunk_order", (b"IHDR", "Critical")) in calls
    assert ("fix_it_felix", (b"IHDR",)) in calls
    assert side_notes == ["-NearbyChunk:Critical Chunk Missing: b'IEND'"]


def test_remove_extra_bytes_runtime_routes_save_clone():
    calls = []
    side_notes = []
    data = PNG_SIGNATURE + b"XX" + build_png_chunk(b"IHDR", b"\x00" * 13)

    result = nearby_runtime.run_remove_extra_bytes_before_chunk(
        build_remove_extra_runtime(calls, side_notes),
        remove_extra_context(data.hex()),
        b"fake",
        b"PNG",
        [],
    )

    solved_message = "-Found 2 extra byte(s) before Chunk[IHDR] after Chunk[PNG] at offset: 0x8"
    assert result == "saved"
    assert side_notes == ["-Remove_Extra_Bytes_Before_Chunk:%s" % solved_message]
    assert calls == [("save_clone", ("", 16, 20, solved_message))]


def test_remove_extra_bytes_runtime_returns_none_without_candidate():
    calls = []
    side_notes = []
    data = PNG_SIGNATURE + b"XX" + build_png_chunk(b"IHDR", b"\x00" * 13)

    result = nearby_runtime.run_remove_extra_bytes_before_chunk(
        build_remove_extra_runtime(calls, side_notes),
        remove_extra_context(data.hex(), known_chunks=(b"IHDR",)),
        b"IHDR",
        b"PNG",
        [],
    )

    assert result is None
    assert calls == []
    assert side_notes == []


def test_double_check_runtime_routes_safety_off_nearby_search():
    calls = []

    result = nearby_runtime.run_double_check(
        build_double_check_runtime(calls),
        nearby_runtime.DoubleCheckContext(data_hex="00" * 67, sample_name="sample.png"),
        b"fake",
        "00000000",
        b"IHDR",
    )

    assert result == "nearby-result"
    assert ("candy", ("Title", "Double Check:")) in calls
    assert (
        "nearby_chunk",
        (b"fake", "00000000", b"IHDR"),
        {"DoubleCheck": True},
    ) in calls


def test_double_check_runtime_preserves_short_file_end_before_fallback_when_end_returns():
    calls = []

    result = nearby_runtime.run_double_check(
        build_double_check_runtime(calls),
        nearby_runtime.DoubleCheckContext(data_hex="00" * 66, sample_name="short.png"),
        b"fake",
        "00000000",
        b"IHDR",
    )

    assert result == "nearby-result"
    assert ("end",) in calls
    assert any(call[0] == "emit" and "-Wrong File Length" in call[1] for call in calls)
    assert (
        "nearby_chunk",
        (b"fake", "00000000", b"IHDR"),
        {"DoubleCheck": True},
    ) in calls


def test_namespace_helpers_build_nearby_runtime_and_context():
    calls = []
    side_notes = []

    def runner(runtime, context, chunk_type, chunk_length, last_chunk_type, double_check, from_error):
        calls.append(("runner", chunk_type, chunk_length, last_chunk_type, double_check, from_error))
        assert runtime.candy is namespace["Candy"]
        assert runtime.emit is namespace["PRINT"]
        assert runtime.checkpoint is namespace["CheckPoint"]
        assert runtime.check_chunk_order is namespace["CheckChunkOrder"]
        assert runtime.clean_extra_bytes is namespace["Remove_Extra_Bytes_Before_Chunk"]
        assert runtime.double_check is namespace["Double_Check"]
        assert runtime.fix_it_felix is namespace["FixItFelix"]
        assert runtime.betterror is namespace["Betterror"]
        assert runtime.pause is namespace["Pause"]
        assert runtime.end is namespace["TheEnd"]
        assert runtime.get_bad_critical() == b"IEND"
        assert runtime.side_notes is side_notes
        assert context.data_hex == "00"
        assert context.chunks == (b"IHDR", b"IDAT")
        assert context.all_chunks == (b"IHDR", b"IDAT", b"IEND")
        assert context.current_length_offset == 8
        assert context.current_length_offset_hex == "0x8"
        assert context.current_data_offset_byte == 16
        assert context.chunks_history == (b"PNG", b"IHDR")
        assert context.chunks_history_index == ("0:0:8", "1:8:16")
        assert context.original_chunk_type == b"IHDR"
        assert context.original_chunk_length == "0000000d"
        assert context.sample_name == "sample.png"
        assert context.debug is True
        assert context.pause_debug is False
        assert context.pause_error is True
        return "nearby"

    namespace = {
        "Candy": lambda *args: calls.append(("candy", args)),
        "PRINT": lambda message: calls.append(("emit", message)),
        "CheckPoint": lambda *args: calls.append(("checkpoint", args)),
        "CheckChunkOrder": lambda *args: calls.append(("order", args)),
        "Remove_Extra_Bytes_Before_Chunk": lambda *args: calls.append(("remove", args)),
        "Double_Check": lambda *args: calls.append(("double", args)),
        "FixItFelix": lambda *args: calls.append(("fix", args)),
        "Betterror": lambda *args: calls.append(("error", args)),
        "Pause": lambda *args: calls.append(("pause", args)),
        "TheEnd": lambda: calls.append(("end",)),
        "Bad_Critical": b"IEND",
        "SideNotes": side_notes,
        "DATAX": "00",
        "CHUNKS": [b"IHDR", b"IDAT"],
        "ALLCHUNKS": [b"IHDR", b"IDAT", b"IEND"],
        "CLoffI": 8,
        "CLoffX": "0x8",
        "CDoffB": 16,
        "Chunks_History": [b"PNG", b"IHDR"],
        "Chunks_History_Index": ["0:0:8", "1:8:16"],
        "Orig_CT": b"IHDR",
        "Orig_CL": "0000000d",
        "Sample_Name": "sample.png",
        "DEBUG": True,
        "PAUSEDEBUG": False,
        "PAUSEERROR": True,
    }

    result = nearby_runtime.run_nearby_chunk_from_namespace(
        namespace,
        b"IHDR",
        "0000000d",
        b"PNG",
        False,
        "Relics",
        runner=runner,
    )

    assert result == "nearby"
    assert calls == [("runner", b"IHDR", "0000000d", b"PNG", False, "Relics")]


def test_namespace_helpers_build_double_check_and_remove_extra_runtimes():
    calls = []
    side_notes = []
    namespace = {
        "Candy": lambda *args: calls.append(("candy", args)),
        "PRINT": lambda message: calls.append(("emit", message)),
        "TheEnd": lambda: calls.append(("end",)),
        "NearbyChunk": lambda *args, **kwargs: calls.append(("nearby", args, kwargs)),
        "SaveClone": lambda *args: calls.append(("save", args)),
        "SideNotes": side_notes,
        "DATAX": "001122",
        "Sample_Name": "sample.png",
        "CLoffI": 4,
        "CHUNKS": [b"IHDR"],
        "ALLCHUNKS": [b"IHDR", b"IDAT"],
    }

    def double_runner(runtime, context, chunk_type, chunk_length, last_chunk_type):
        assert runtime.candy is namespace["Candy"]
        assert runtime.emit is namespace["PRINT"]
        assert runtime.end is namespace["TheEnd"]
        assert runtime.nearby_chunk is namespace["NearbyChunk"]
        assert context.data_hex == "001122"
        assert context.sample_name == "sample.png"
        assert (chunk_type, chunk_length, last_chunk_type) == (b"IHDR", "13", b"PNG")
        return "double"

    def remove_runner(runtime, context, chunk_type, last_chunk_type, excluded):
        assert runtime.save_clone is namespace["SaveClone"]
        assert runtime.side_notes is side_notes
        assert context.data_hex == "001122"
        assert context.current_length_offset == 4
        assert context.known_chunks == (b"IHDR",)
        assert context.all_chunks == (b"IHDR", b"IDAT")
        assert (chunk_type, last_chunk_type, excluded) == (b"IHDR", b"PNG", [b"IDAT"])
        return "remove"

    assert nearby_runtime.run_double_check_from_namespace(
        namespace,
        b"IHDR",
        "13",
        b"PNG",
        runner=double_runner,
    ) == "double"
    assert nearby_runtime.run_remove_extra_bytes_before_chunk_from_namespace(
        namespace,
        b"IHDR",
        b"PNG",
        [b"IDAT"],
        runner=remove_runner,
    ) == "remove"


def main():
    checks = [
        ("Clean extra bytes", test_nearby_runtime_returns_clean_extra_bytes_before_scan),
        ("Known chunk checkpoint", test_nearby_runtime_known_chunk_routes_length_repair_checkpoint),
        ("Excluded trap", test_nearby_runtime_excluded_found_chunk_routes_legacy_trap),
        ("Scan summary", test_nearby_runtime_summarizes_candidates_without_alignment_in_normal_mode),
        ("Debug bingo details", test_nearby_runtime_keeps_bingo_details_in_debug_mode),
        ("Aligned repair", test_nearby_runtime_alignment_still_routes_repair_without_summary),
        ("Doublecheck critical", test_nearby_runtime_doublecheck_missing_critical_routes_fixit),
        ("Remove extra bytes", test_remove_extra_bytes_runtime_routes_save_clone),
        ("Remove extra bytes none", test_remove_extra_bytes_runtime_returns_none_without_candidate),
        ("Double check", test_double_check_runtime_routes_safety_off_nearby_search),
        ("Double check short file", test_double_check_runtime_preserves_short_file_end_before_fallback_when_end_returns),
        ("Namespace nearby", test_namespace_helpers_build_nearby_runtime_and_context),
        ("Namespace double/remove", test_namespace_helpers_build_double_check_and_remove_extra_runtimes),
    ]

    print("Running nearby runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"nearby runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
