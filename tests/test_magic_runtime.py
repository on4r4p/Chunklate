#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import magic_runtime
from chunklate.png import IEND_CHUNK, PNG_SIGNATURE, build_png_chunk, validate_png_structure


def build_runtime(calls, side_notes=None, *, spec_length=None):
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
        side_notes=side_notes,
        write_clone=lambda data, summary: calls.append(("write_clone", data, summary)) or "write-result",
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
