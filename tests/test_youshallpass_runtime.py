#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import chunk_state, youshallpass_runtime


def build_runtime(
    calls,
    *,
    state=None,
    chunks_history=(),
    orig_cl="00000000",
):
    state = state or chunk_state.ChunkInfoState()

    def sync_state(section):
        calls.append(("sync_state", section))

    return youshallpass_runtime.YouShallPassRuntime(
        chunk_state=state,
        sync_state=sync_state,
        chunks_history=tuple(chunks_history),
        orig_cl=orig_cl,
    )


def test_youshallpass_runtime_dispatches_simple_validators():
    calls = []
    runtime = build_runtime(calls)

    assert youshallpass_runtime.youshallpass(
        runtime,
        b"IHDR",
        "00000020000000100802000000",
    ) is True
    assert youshallpass_runtime.youshallpass(
        runtime,
        b"IHDR",
        "00000000000000100802000000",
    ) is False
    assert youshallpass_runtime.youshallpass(runtime, b"gAMA", "0000b18f") is True
    assert youshallpass_runtime.youshallpass(runtime, b"gAMA", "00000000") is False
    assert calls == []


def test_youshallpass_runtime_syncs_ihdr_for_color_dependent_chunks():
    calls = []
    state = chunk_state.ChunkInfoState(ihdr_color="0", ihdr_depth="8")
    runtime = build_runtime(calls, state=state)

    assert youshallpass_runtime.youshallpass(runtime, b"bKGD", "0007") is True
    assert youshallpass_runtime.youshallpass(runtime, b"sBIT", "00") is False

    assert calls == [("sync_state", "ihdr"), ("sync_state", "ihdr")]


def test_youshallpass_runtime_uses_palette_and_splt_state():
    calls = []
    state = chunk_state.ChunkInfoState(
        ihdr_color="3",
        ihdr_depth="8",
        plte_r=["00", "03"],
        plte_g=["01", "04"],
        plte_b=["02", "05"],
    )
    runtime = build_runtime(calls, state=state, chunks_history=(b"PLTE",))

    assert youshallpass_runtime.youshallpass(runtime, b"hIST", "00010002") is True
    assert youshallpass_runtime.youshallpass(runtime, b"tRNS", "000102") is False

    assert calls == [
        ("sync_state", ("plte", "splt")),
        ("sync_state", ("ihdr", "plte", "splt")),
    ]


def test_youshallpass_runtime_uses_splt_duplicate_names():
    calls = []
    payload = "70616c0008" + ("01" * 6)
    state = chunk_state.ChunkInfoState(splt_name=["70616c"])
    runtime = build_runtime(calls, state=state)

    assert youshallpass_runtime.youshallpass(runtime, b"sPLT", payload) is False

    assert calls == [("sync_state", "splt")]


def test_youshallpass_runtime_uses_history_and_raw_length():
    calls = []
    iccp = "4943430000abcd"

    assert youshallpass_runtime.youshallpass(
        build_runtime(calls, chunks_history=(), orig_cl="00000007"),
        b"iCCP",
        iccp,
    ) is True
    assert youshallpass_runtime.youshallpass(
        build_runtime(calls, chunks_history=(b"cHRM",), orig_cl="00000007"),
        b"iCCP",
        iccp,
    ) is False
    assert youshallpass_runtime.youshallpass(
        build_runtime(calls, chunks_history=(), orig_cl="00000008"),
        b"iCCP",
        iccp,
    ) is False
    assert youshallpass_runtime.youshallpass(
        build_runtime(calls, chunks_history=(b"cHRM",), orig_cl="00000000"),
        b"sRGB",
        "00",
    ) is False

    assert calls == []


def test_youshallpass_runtime_preserves_unknown_chunks_as_valid():
    calls = []
    runtime = build_runtime(calls)

    assert youshallpass_runtime.youshallpass(runtime, b"NOPE", "") is True
    assert calls == []


def test_youshallpass_validators_cover_legacy_dispatch_names():
    assert set(youshallpass_runtime.YOUSHALLPASS_VALIDATORS) == {
        b"IHDR",
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
    }


def main():
    checks = [
        ("simple validators", test_youshallpass_runtime_dispatches_simple_validators),
        ("IHDR-dependent validators", test_youshallpass_runtime_syncs_ihdr_for_color_dependent_chunks),
        ("palette/sPLT state", test_youshallpass_runtime_uses_palette_and_splt_state),
        ("sPLT duplicate names", test_youshallpass_runtime_uses_splt_duplicate_names),
        ("history/raw length", test_youshallpass_runtime_uses_history_and_raw_length),
        ("unknown chunks", test_youshallpass_runtime_preserves_unknown_chunks_as_valid),
        ("validator table", test_youshallpass_validators_cover_legacy_dispatch_names),
    ]

    print("Running YouShallPass runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"YouShallPass runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
