#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import magic_runtime


def build_runtime(calls, side_notes=None, *, spec_length=None):
    if side_notes is None:
        side_notes = []

    def candy(kind, *args):
        calls.append(("candy", (kind,) + args))
        if kind == "Color":
            return "<%s:%s>" % (args[0], args[1])
        if kind == "Emoj":
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
        side_notes=side_notes,
    )


def base_context(data_hex, **updates):
    values = {
        "data_hex": data_hex,
        "chunks": (b"IHDR", b"IDAT", b"IEND"),
        "before_idat": (b"IHDR",),
        "sample_name": "sample.png",
    }
    values.update(updates)
    return magic_runtime.FindMagicContext(**values)


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


def main():
    checks = [
        ("Single candidate", test_find_magic_runtime_single_candidate_cuts_at_best_magic),
        ("No known chunks", test_find_magic_runtime_too_low_without_known_chunks_ends_with_note),
        ("Prepend nearest", test_find_magic_runtime_too_low_prepends_magic_before_nearest_chunk),
    ]

    print("Running magic runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"magic runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
