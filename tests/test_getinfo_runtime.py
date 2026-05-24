#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import chunk_state, getinfo_runtime


def build_runtime(
    calls,
    *,
    state=None,
    ihdr_color="0",
    ihdr_depth="8",
    chunks_history=(),
    raw_length="00000000",
    orig_cl="00000000",
):
    legacy = {}
    state = state or chunk_state.ChunkInfoState()

    def set_legacy(**values):
        calls.append(("set_legacy", values))
        legacy.update(values)

    def sync_legacy(section):
        calls.append(("sync_legacy", section))

    def checkpoint(*args):
        calls.append(("checkpoint", args))

    def emit(message):
        calls.append(("emit", message))

    def candy(kind, *args):
        calls.append(("candy", (kind,) + args))
        if kind == "Color":
            return "<%s:%s>" % (args[0], args[1])
        if kind == "Emoj":
            return ":%s:" % args[0]
        return "candy:%s" % kind

    runtime = getinfo_runtime.GetInfoRuntime(
        chunk_state=state,
        set_legacy=set_legacy,
        sync_legacy=sync_legacy,
        max_resolution=lambda: 32,
        checkpoint=checkpoint,
        emit=emit,
        candy=candy,
        color=lambda color, value: "<%s:%s>" % (color, value),
        emoji=lambda name: ":%s:" % name,
        raw_length=raw_length,
        orig_cl=orig_cl,
        ihdr_color=ihdr_color,
        ihdr_depth=ihdr_depth,
        chunks_history=tuple(chunks_history),
        private_chunks=(b"vpAg",),
        allchunks=(b"PNG", b"IHDR", b"gAMA", b"pHYs", b"vpAg"),
    )
    return runtime, state, legacy


def test_print_ok_uses_legacy_ok_message():
    calls = []
    runtime, state, legacy = build_runtime(calls)

    getinfo_runtime.print_ok(runtime)

    assert state.snapshot()["idat"]["counter"] == 0
    assert legacy == {}
    assert calls[-1] == ("emit", "\n-Errors Check :<green: OK >:good:")


def test_checkpoint_helpers_route_fix_or_ok():
    calls = []
    runtime, state, legacy = build_runtime(calls)
    fixes = ["-problem"]

    getinfo_runtime.checkpoint_or_ok(runtime, b"gAMA", fixes)
    getinfo_runtime.checkpoint_only(runtime, b"gAMA", fixes, "payload")
    getinfo_runtime.checkpoint_or_ok(runtime, b"pHYs", [])

    assert ("checkpoint", (True, False, "GetInfo", b"gAMA", fixes)) in calls
    assert ("checkpoint", (True, False, "GetInfo", b"gAMA", fixes, "payload")) in calls
    assert ("emit", "\n-Errors Check :<green: OK >:good:") in calls
    assert legacy == {}
    assert state.snapshot()["idat"]["counter"] == 0


def test_run_getinfo_dispatches_ihdr_and_syncs_state():
    calls = []
    runtime, state, legacy = build_runtime(calls)

    fixes = getinfo_runtime.run_getinfo(
        runtime,
        b"IHDR",
        "00000020000000100802000000",
    )

    assert fixes == []
    assert state.ihdr_width == "32"
    assert state.ihdr_height == "16"
    assert state.ihdr_depth == "8"
    assert state.ihdr_color == "2"
    assert ("sync_legacy", "ihdr") in calls
    assert ("emit", "\n-Errors Check :<green: OK >:good:") in calls
    assert legacy == {}


def test_run_getinfo_dispatches_gama_error_to_checkpoint():
    calls = []
    runtime, state, legacy = build_runtime(calls)

    fixes = getinfo_runtime.run_getinfo(runtime, b"gAMA", "00000000")

    assert fixes == ["-A gAMA Chunk of 0 is Useless."]
    assert legacy["gAMA"] == "0"
    assert ("checkpoint", (True, False, "GetInfo", b"gAMA", fixes)) in calls
    assert state.snapshot()["idat"]["counter"] == 0


def test_run_getinfo_reports_private_and_unknown_chunks():
    calls = []
    runtime, state, legacy = build_runtime(calls)

    assert getinfo_runtime.run_getinfo(runtime, b"vpAg", "") == []
    assert getinfo_runtime.run_getinfo(runtime, b"NOPE", "") == []

    assert ("emit", "-Private Chunk") in calls
    assert ("emit", "-<red:Unknown Chunk.>") in calls
    assert legacy == {}
    assert state.snapshot()["idat"]["counter"] == 0


def test_getinfo_handlers_cover_legacy_dispatch_names():
    assert set(getinfo_runtime.GETINFO_HANDLERS) == {
        b"PNG",
        b"IHDR",
        b"IDAT",
        b"pHYs",
        b"bKGD",
        b"PLTE",
        b"sPLT",
        b"hIST",
        b"tIME",
        b"tRNS",
        b"sRGB",
        b"cHRM",
        b"gAMA",
        b"iCCP",
        b"sBIT",
        b"oFFs",
        b"pCAL",
        b"gIFg",
        b"gIFx",
        b"sTER",
        b"tEXt",
        b"zTXt",
        b"iTXt",
        b"eXIf",
        b"spAL",
    }


def main():
    checks = [
        ("GetInfo OK helper", test_print_ok_uses_legacy_ok_message),
        ("GetInfo checkpoint helpers", test_checkpoint_helpers_route_fix_or_ok),
        ("GetInfo IHDR dispatch", test_run_getinfo_dispatches_ihdr_and_syncs_state),
        ("GetInfo gAMA checkpoint", test_run_getinfo_dispatches_gama_error_to_checkpoint),
        ("GetInfo private/unknown reports", test_run_getinfo_reports_private_and_unknown_chunks),
        ("GetInfo handler table", test_getinfo_handlers_cover_legacy_dispatch_names),
    ]

    print("Running GetInfo runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"getinfo runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
