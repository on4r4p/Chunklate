#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import chunk_order, chunk_order_runtime, nearby, runtime_state


def build_runtime(calls, *, warning=False):
    warning_box = {"value": warning}

    def candy(kind, *args):
        calls.append(("candy", (kind,) + args))
        if kind == "Color":
            return "<%s:%s>" % (args[0], args[1])
        if kind == "Emoj":
            return ":%s:" % args[0]
        return "candy:%s" % kind

    def set_warning(value):
        calls.append(("set_warning", value))
        warning_box["value"] = value

    runtime = chunk_order_runtime.CheckChunkOrderRuntime(
        candy=candy,
        emit=lambda message: calls.append(("emit", message)),
        checkpoint=lambda *args: calls.append(("checkpoint", args)) or "checkpoint-result",
        pause=lambda message: calls.append(("pause", message)),
        end=lambda: calls.append(("end",)),
        betterror=lambda error, name: calls.append(("betterror", str(error), name)),
        get_warning=lambda: warning_box["value"],
        set_warning=set_warning,
        raw_print=lambda *args: calls.append(("raw_print", args)),
    )
    return runtime, warning_box


def base_context(**updates):
    values = {
        "chunk_order_context": runtime_state.ChunkOrderRuntimeContext(
            sample_name="sample.png",
            chunks_history=(b"PNG", b"IHDR"),
            unique_chunks=(b"PNG", b"IHDR", b"IEND"),
        ),
        "minimal_chunks": (b"PNG", b"IHDR", b"IDAT", b"IEND"),
        "pandora_box": {},
        "before_plte": (b"gAMA", b"cHRM"),
        "before_idat2": (b"gAMA", b"cHRM"),
        "chunks": (b"PNG", b"IHDR", b"PLTE", b"IDAT", b"IEND", b"gAMA"),
        "after_plte": (b"tRNS", b"bKGD"),
        "before_idat": (b"gAMA", b"cHRM"),
        "ihdr_color": "2",
        "no_order_chunks": (b"IEND", b"tEXt"),
        "debug": False,
        "pause_debug": False,
    }
    values.update(updates)
    return chunk_order_runtime.CheckChunkOrderContext(**values)


def checkpoint_args(calls):
    matches = [call[1] for call in calls if call[0] == "checkpoint"]
    assert len(matches) == 1
    return matches[0]


def test_critical_mode_routes_missing_chunks_to_checkpoint():
    calls = []
    runtime, _warning = build_runtime(calls)

    result = chunk_order_runtime.run_check_chunk_order(
        runtime,
        base_context(),
        b"IHDR",
        "Critical",
    )

    assert result is None
    assert ("candy", ("Title", "Critical Chunks Check :")) in calls
    assert (
        "emit",
        "-Critical Chunk b'IDAT' is <red:Missing> !",
    ) in calls
    assert checkpoint_args(calls) == (
        True,
        False,
        "CheckChunkOrder",
        "Critical",
        ["-Critical Chunk b'IDAT' is Missing", "-Critical Chunk b'IEND' is Missing"],
    )


def test_critical_mode_prints_ok_without_checkpoint():
    calls = []
    runtime, _warning = build_runtime(calls)
    context = base_context(minimal_chunks=(b"PNG", b"IHDR"))

    result = chunk_order_runtime.run_check_chunk_order(runtime, context, b"IHDR", "Critical")

    assert result is None
    assert ("emit", "\n-Errors Check :<green: OK >:good:") in calls
    assert not [call for call in calls if call[0] == "checkpoint"]


def test_the_good_place_mode_preserves_ihdr_misplacement_checkpoint():
    calls = []
    runtime, _warning = build_runtime(calls)
    context = base_context(
        chunk_order_context=runtime_state.ChunkOrderRuntimeContext(
            sample_name="sample.png",
            chunks_history=(b"PNG", b"IDAT"),
            unique_chunks=(b"PNG", b"IHDR", b"IEND"),
        ),
    )

    result = chunk_order_runtime.run_check_chunk_order(
        runtime,
        context,
        b"IDAT",
        "TheGoodPlace",
    )

    assert result == "checkpoint-result"
    assert checkpoint_args(calls) == chunk_order.ihdr_misplacement_checkpoint_args(
        (b"PNG", b"IDAT")
    )


def test_fix_mode_header_exclusion_returns_everything_except_ihdr():
    calls = []
    runtime, _warning = build_runtime(calls)
    context = base_context(
        chunk_order_context=runtime_state.ChunkOrderRuntimeContext(
            sample_name="sample.png",
            chunks_history=(b"PNG",),
            unique_chunks=(b"PNG", b"IHDR"),
        ),
        chunks=(b"PNG", b"IHDR", b"IDAT"),
    )

    result = chunk_order_runtime.run_check_chunk_order(runtime, context, b"PNG", "Fix")

    assert result == [b"PNG", b"IDAT"]
    assert (
        "candy",
        ("Cowsay", chunk_order.only_ihdr_after_png_header_message(), "com"),
    ) in calls


def test_fix_mode_missing_palette_warning_sets_warning_once():
    calls = []
    runtime, warning = build_runtime(calls)
    context = base_context(
        chunk_order_context=runtime_state.ChunkOrderRuntimeContext(
            sample_name="sample.png",
            chunks_history=(b"PNG", b"IHDR", b"IDAT"),
            unique_chunks=(b"PNG", b"IHDR", b"IEND"),
        ),
        before_idat=(b"gAMA",),
        chunks=(b"PNG", b"IHDR", b"PLTE", b"IDAT", b"IEND", b"gAMA"),
        ihdr_color="2",
    )

    result = chunk_order_runtime.run_check_chunk_order(runtime, context, b"IDAT", "Fix")

    assert warning["value"] is True
    assert ("set_warning", True) in calls
    assert b"gAMA" in result
    assert (
        "candy",
        (
            "Cowsay",
            " There is a chance that some <red:Critical Palette> chunks are <yellow:Missing>.",
            "com",
        ),
    ) in calls


def test_the_good_place_missing_data_routes_missing_checkpoint():
    calls = []
    runtime = chunk_order_runtime.TheGoodPlaceRuntime(
        candy=build_runtime(calls)[0].candy,
        emit=lambda message: calls.append(("emit", message)),
        checkpoint=lambda *args: calls.append(("checkpoint", args)) or "checkpoint-result",
        pause=lambda message: calls.append(("pause", message)),
        end=lambda: calls.append(("end",)),
    )
    context = chunk_order_runtime.TheGoodPlaceContext(
        data_hex="aaaabbbbccccdddd",
        chunks_history=(b"PNG", b"IDAT"),
        chunks_history_index=("0:0:4", "1:4:8"),
        pandora_box={"Missplaced_error": {}},
    )

    result = chunk_order_runtime.run_the_good_place(runtime, context, b"IDAT", 1, b"IHDR")

    assert result == "checkpoint-result"
    assert ("emit", "\n-\033[1;31;49mCriticalHit\033[m: Missplaced_error") in calls
    assert checkpoint_args(calls) == chunk_order.the_good_place_missing_checkpoint_args(
        b"IHDR",
        1,
        4,
        8,
    )


def test_the_good_place_found_data_relocates_chunk_and_routes_checkpoint():
    calls = []
    runtime = chunk_order_runtime.TheGoodPlaceRuntime(
        candy=build_runtime(calls)[0].candy,
        emit=lambda message: calls.append(("emit", message)),
        checkpoint=lambda *args: calls.append(("checkpoint", args)) or "checkpoint-result",
        pause=lambda message: calls.append(("pause", message)),
        end=lambda: calls.append(("end",)),
    )
    context = chunk_order_runtime.TheGoodPlaceContext(
        data_hex="aaaabbbbccccdddd",
        chunks_history=(b"PNG", b"IDAT", b"IHDR"),
        chunks_history_index=("0:0:4", "1:4:8", "2:8:12"),
        pandora_box={},
    )

    result = chunk_order_runtime.run_the_good_place(runtime, context, b"IDAT", 1, b"IHDR")

    assert result == "checkpoint-result"
    assert checkpoint_args(calls) == chunk_order.the_good_place_found_checkpoint_args(
        b"IHDR",
        nearby.HistoryChunkPosition(2, 8, 12),
        "aaaaccccbbbbdddd",
    )


def test_namespace_helper_builds_check_chunk_order_runtime_and_context():
    calls = []
    namespace = {
        "Sample_Name": "sample.png",
        "Chunks_History": [b"PNG", b"IHDR"],
        "UNIQUE_CHUNK": [b"PNG", b"IHDR"],
        "MINIMAL_CHUNKS": [b"PNG", b"IHDR", b"IDAT", b"IEND"],
        "PandoraBox": {"key": "value"},
        "BEFORE_PLTE": [b"gAMA"],
        "BEFORE_IDAT2": [b"cHRM"],
        "CHUNKS": [b"IHDR", b"IDAT"],
        "AFTER_PLTE": [b"tRNS"],
        "BEFORE_IDAT": [b"PLTE"],
        "IHDR_Color": "3",
        "NO_ORDER_CHUNKS": [b"tEXt"],
        "DEBUG": True,
        "PAUSEDEBUG": False,
        "Candy": lambda *args: calls.append(("candy", args)),
        "PRINT": lambda message: calls.append(("emit", message)),
        "CheckPoint": lambda *args: calls.append(("checkpoint", args)),
        "Pause": lambda message: calls.append(("pause", message)),
        "TheEnd": lambda: calls.append(("end",)),
        "Betterror": lambda *args: calls.append(("betterror", args)),
        "Warning": False,
    }

    def runner(runtime, context, lastchunk, mode):
        assert runtime.candy is namespace["Candy"]
        assert runtime.emit is namespace["PRINT"]
        assert runtime.checkpoint is namespace["CheckPoint"]
        assert runtime.pause is namespace["Pause"]
        assert runtime.end is namespace["TheEnd"]
        assert runtime.betterror is namespace["Betterror"]
        assert runtime.get_warning() is False
        runtime.set_warning(True)
        assert namespace["Warning"] is True
        assert context.chunk_order_context.sample_name == "sample.png"
        assert context.chunk_order_context.chunks_history == (b"PNG", b"IHDR")
        assert context.chunk_order_context.unique_chunks == (b"PNG", b"IHDR")
        assert context.minimal_chunks == (b"PNG", b"IHDR", b"IDAT", b"IEND")
        assert context.pandora_box == {"key": "value"}
        assert context.before_plte == (b"gAMA",)
        assert context.before_idat2 == (b"cHRM",)
        assert context.chunks == (b"IHDR", b"IDAT")
        assert context.after_plte == (b"tRNS",)
        assert context.before_idat == (b"PLTE",)
        assert context.ihdr_color == "3"
        assert context.no_order_chunks == (b"tEXt",)
        assert context.debug is True
        assert context.pause_debug is False
        assert (lastchunk, mode) == (b"IHDR", "Fix")
        return "checked"

    result = chunk_order_runtime.run_check_chunk_order_from_namespace(
        namespace,
        b"IHDR",
        "Fix",
        runner=runner,
    )

    assert result == "checked"


def test_the_good_place_namespace_helper_builds_runtime_and_context():
    calls = []
    namespace = {
        "DATAX": "aaaabbbbccccdddd",
        "Chunks_History": [b"PNG", b"IDAT", b"IHDR"],
        "Chunks_History_Index": ["0:0:4", "1:4:8", "2:8:12"],
        "PandoraBox": {"Missplaced_error": {}},
        "DEBUG": True,
        "PAUSEDEBUG": False,
        "Candy": lambda *args: calls.append(("candy", args)),
        "PRINT": lambda message: calls.append(("emit", message)),
        "CheckPoint": lambda *args: calls.append(("checkpoint", args)),
        "Pause": lambda message: calls.append(("pause", message)),
        "TheEnd": lambda: calls.append(("end",)),
    }

    def runner(runtime, context, missplaced_chunk_name, missplaced_chunk_pos, to_fix_chunk_name):
        assert runtime.candy is namespace["Candy"]
        assert runtime.emit is namespace["PRINT"]
        assert runtime.checkpoint is namespace["CheckPoint"]
        assert runtime.pause is namespace["Pause"]
        assert runtime.end is namespace["TheEnd"]
        assert context.data_hex == "aaaabbbbccccdddd"
        assert context.chunks_history == (b"PNG", b"IDAT", b"IHDR")
        assert context.chunks_history_index == ("0:0:4", "1:4:8", "2:8:12")
        assert context.pandora_box == {"Missplaced_error": {}}
        assert context.debug is True
        assert context.pause_debug is False
        assert (missplaced_chunk_name, missplaced_chunk_pos, to_fix_chunk_name) == (
            b"IDAT",
            1,
            b"IHDR",
        )
        return "placed"

    result = chunk_order_runtime.run_the_good_place_from_namespace(
        namespace,
        b"IDAT",
        1,
        b"IHDR",
        runner=runner,
    )

    assert result == "placed"


def main():
    checks = [
        ("Critical checkpoint", test_critical_mode_routes_missing_chunks_to_checkpoint),
        ("Critical OK", test_critical_mode_prints_ok_without_checkpoint),
        ("TheGoodPlace IHDR", test_the_good_place_mode_preserves_ihdr_misplacement_checkpoint),
        ("Fix header exclusion", test_fix_mode_header_exclusion_returns_everything_except_ihdr),
        ("Fix missing palette warning", test_fix_mode_missing_palette_warning_sets_warning_once),
        ("TheGoodPlace missing data", test_the_good_place_missing_data_routes_missing_checkpoint),
        ("TheGoodPlace found data", test_the_good_place_found_data_relocates_chunk_and_routes_checkpoint),
        ("Namespace check order", test_namespace_helper_builds_check_chunk_order_runtime_and_context),
        ("Namespace TheGoodPlace", test_the_good_place_namespace_helper_builds_runtime_and_context),
    ]

    print("Running chunk order runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"chunk order runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
