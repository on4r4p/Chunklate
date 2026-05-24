#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import chunk_order, chunk_order_runtime, runtime_state


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


def main():
    checks = [
        ("Critical checkpoint", test_critical_mode_routes_missing_chunks_to_checkpoint),
        ("Critical OK", test_critical_mode_prints_ok_without_checkpoint),
        ("TheGoodPlace IHDR", test_the_good_place_mode_preserves_ihdr_misplacement_checkpoint),
        ("Fix header exclusion", test_fix_mode_header_exclusion_returns_everything_except_ihdr),
        ("Fix missing palette warning", test_fix_mode_missing_palette_warning_sets_warning_once),
    ]

    print("Running chunk order runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"chunk order runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
