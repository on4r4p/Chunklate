#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import chunk_name_runtime, decisions


def build_runtime(calls, **overrides):
    def candy(kind, *args):
        calls.append(("candy", (kind,) + args))
        if kind == "Color":
            return "<%s:%s>" % (args[0], args[1])
        if kind == "Chunky":
            return ":%s:" % args[0]
        return "candy:%s" % kind

    defaults = {
        "candy": candy,
        "emit": lambda message: calls.append(("emit", message)),
        "checkpoint": lambda *args: calls.append(("checkpoint", args)) or "checkpoint-result",
        "pause": lambda message: calls.append(("pause", message)),
        "end": lambda: calls.append(("end",)),
        "betterror": lambda error, name: calls.append(("betterror", str(error), name)),
        "name_shift": lambda: calls.append(("name_shift",)) or False,
        "check_chunk_order": lambda *args: calls.append(("check_chunk_order", args)) or [],
        "nearby_chunk": lambda *args: calls.append(("nearby_chunk", args)) or "nearby-result",
        "save_clone": lambda *args: calls.append(("save_clone", args)) or "save-result",
        "crc_matches": lambda candidates: calls.append(("crc_matches", tuple(candidates))) or [],
        "save_auto_name": lambda *args: calls.append(("save_auto_name", args)) or "auto-result",
        "unknown_private_critical_removal": lambda: calls.append(("unknown_private_critical_removal",)) or None,
        "ask_pokemon_choice": lambda count, on_invalid: calls.append(("ask_pokemon_choice", count))
        or decisions.PokemonChoice("length"),
    }
    defaults.update(overrides)
    return chunk_name_runtime.ChunkNameRuntime(**defaults)


def base_context(**updates):
    values = {
        "chunks": (b"IHDR", b"IDAT", b"IEND"),
        "all_chunks": (b"IHDR", b"IDAT", b"IEND"),
        "chunks_history": (b"PNG", b"IHDR"),
        "original_chunk_type": b"bad!",
        "original_chunk_length": "00000004",
        "current_type_offset": 16,
        "current_type_offset_hex": "0x8",
        "idat_average_length": 4,
        "original_next_chunk": b"IEND",
        "next_chunk_offset": 32,
    }
    values.update(updates)
    return chunk_name_runtime.ChunkNameContext(**values)


def checkpoint_args(calls):
    matches = [call[1] for call in calls if call[0] == "checkpoint"]
    assert len(matches) == 1
    return matches[0]


def test_check_chunk_name_accepts_exact_current_chunk():
    calls = []
    runtime = build_runtime(calls)

    result = chunk_name_runtime.run_check_chunk_name(
        runtime,
        base_context(),
        b"IHDR",
        "0000000d",
        b"PNG",
    )

    assert result == "checkpoint-result"
    assert checkpoint_args(calls) == (
        False,
        False,
        "CheckChunkName",
        b"IHDR",
        ["-Name is valid for Chunk[b'IHDR']."],
        None,
    )


def test_check_chunk_name_routes_wrong_ancillary_current_chunk():
    calls = []
    runtime = build_runtime(calls)

    result = chunk_name_runtime.run_check_chunk_name(
        runtime,
        base_context(all_chunks=(b"IDAT",), original_chunk_type=b"idat"),
        b"idat",
        "00000000",
        b"IHDR",
    )

    assert result == "checkpoint-result"
    assert checkpoint_args(calls) == (
        True,
        False,
        "CheckChunkName",
        b"idat",
        ["-Found Chunk[b'idat'] Wrong Ancillary in known Chunk name at offset: 0x8"],
        "0x8",
        16,
        24,
        b"idat",
        b"IDAT",
        None,
    )


def test_check_chunk_name_routes_idat_length_mismatch():
    calls = []
    runtime = build_runtime(calls)

    result = chunk_name_runtime.run_check_chunk_name(
        runtime,
        base_context(
            chunks_history=(b"PNG", b"IDAT"),
            idat_average_length=4,
            original_next_chunk=b"IDAT",
        ),
        b"zzzz",
        "00000006",
        b"IDAT",
    )

    assert result == "checkpoint-result"
    assert checkpoint_args(calls)[4] == [
        "-Found Chunk[b'zzzz'] has Wrong Chunk name at offset: 0x8 and length is not the same than before."
    ]


def test_brute_chunk_routes_nameshift_repair_to_checkpoint():
    calls = []
    runtime = build_runtime(calls, name_shift=lambda: ["fixed", 7, 12])

    result = chunk_name_runtime.run_brute_chunk(
        runtime,
        base_context(original_chunk_type=b"bad!"),
        b"bad!",
        b"IHDR",
        "00000004",
        "Relics",
    )

    assert result == "checkpoint-result"
    assert checkpoint_args(calls) == (
        True,
        True,
        "CheckChunkName",
        b"bad!",
        ["-Chunk length has been corrupted due to some missing bytes."],
        "fixed",
        7,
        12,
        "-Chunk length has been corrupted due to some missing bytes.",
        "Relics",
    )


def test_brute_chunk_prefers_single_crc_match_auto_name():
    calls = []
    runtime = build_runtime(
        calls,
        crc_matches=lambda candidates: calls.append(("crc_matches", tuple(candidates))) or [b"IDAT"],
    )

    result = chunk_name_runtime.run_brute_chunk(
        runtime,
        base_context(),
        b"bad!",
        b"IHDR",
        "00000004",
        "Relics",
    )

    assert result == "auto-result"
    assert ("save_auto_name", (b"bad!", "Relics", b"IDAT", "stored CRC matched candidate chunk name")) in calls


def test_brute_chunk_pokemon_length_choice_routes_nearby_chunk():
    calls = []
    runtime = build_runtime(calls)

    result = chunk_name_runtime.run_brute_chunk(
        runtime,
        base_context(chunks=(b"IHDR", b"IDAT")),
        b"zzzz",
        b"IHDR",
        "00000004",
        "Relics",
    )

    assert result == ()
    assert ("ask_pokemon_choice", 2) in calls
    assert ("nearby_chunk", (b"zzzz", "00000004", b"IHDR", False)) in calls


def build_namespace(calls):
    return {
        "Candy": lambda *args: calls.append(("candy", args)),
        "PRINT": lambda message: calls.append(("emit", message)),
        "CheckPoint": lambda *args: calls.append(("checkpoint", args)),
        "Pause": lambda message: calls.append(("pause", message)),
        "TheEnd": lambda: calls.append(("end",)),
        "Betterror": lambda *args: calls.append(("betterror", args)),
        "NameShift": lambda: calls.append(("name_shift",)),
        "CheckChunkOrder": lambda *args: calls.append(("check_order", args)),
        "NearbyChunk": lambda *args: calls.append(("nearby", args)),
        "SaveClone": lambda *args: calls.append(("save", args)),
        "BruteChunk_Crc_Matches": lambda candidates: calls.append(("crc", tuple(candidates))),
        "BruteChunk_Save_Auto_Name": lambda *args: calls.append(("auto_name", args)),
        "FixItFelix_Try_Automatic_Repair": lambda key: calls.append(("auto_repair", key)),
        "CHUNKS": [b"IHDR", b"IDAT"],
        "ALLCHUNKS": [b"IHDR", b"IDAT", b"IEND"],
        "Chunks_History": [b"PNG", b"IHDR"],
        "Orig_CT": b"bad!",
        "Orig_CL": "00000004",
        "CToffI": 16,
        "CToffX": "0x8",
        "IDAT_Avg_Len": 4,
        "Orig_NC": b"IEND",
        "NCoffI": 32,
        "DEBUG": True,
        "PAUSEDEBUG": False,
    }


def test_chunk_name_namespace_builders_preserve_runtime_callbacks_and_context():
    calls = []
    namespace = build_namespace(calls)

    runtime = chunk_name_runtime.build_chunk_name_runtime_from_namespace(namespace)
    context = chunk_name_runtime.build_chunk_name_context_from_namespace(namespace)

    assert runtime.candy is namespace["Candy"]
    assert runtime.emit is namespace["PRINT"]
    assert runtime.checkpoint is namespace["CheckPoint"]
    assert runtime.pause is namespace["Pause"]
    assert runtime.end is namespace["TheEnd"]
    assert runtime.betterror is namespace["Betterror"]
    assert runtime.name_shift is namespace["NameShift"]
    assert runtime.check_chunk_order is namespace["CheckChunkOrder"]
    assert runtime.nearby_chunk is namespace["NearbyChunk"]
    assert runtime.save_clone is namespace["SaveClone"]
    assert runtime.crc_matches is namespace["BruteChunk_Crc_Matches"]
    assert runtime.save_auto_name is namespace["BruteChunk_Save_Auto_Name"]
    runtime.unknown_private_critical_removal()
    assert ("auto_repair", "unknown_private_critical_removal") in calls

    assert context.chunks == (b"IHDR", b"IDAT")
    assert context.all_chunks == (b"IHDR", b"IDAT", b"IEND")
    assert context.chunks_history == (b"PNG", b"IHDR")
    assert context.original_chunk_type == b"bad!"
    assert context.original_chunk_length == "00000004"
    assert context.current_type_offset == 16
    assert context.current_type_offset_hex == "0x8"
    assert context.idat_average_length == 4
    assert context.original_next_chunk == b"IEND"
    assert context.next_chunk_offset == 32
    assert context.debug is True
    assert context.pause_debug is False


def test_chunk_name_namespace_run_helpers_pass_legacy_arguments():
    calls = []
    namespace = build_namespace(calls)

    def brute_runner(runtime, context, chunk_type, last_chunk_type, chunk_length, from_error):
        assert runtime.candy is namespace["Candy"]
        assert context.original_chunk_type == b"bad!"
        assert (chunk_type, last_chunk_type, chunk_length, from_error) == (
            b"bad!",
            b"IHDR",
            "00000004",
            "Relics",
        )
        return "brute"

    def check_runner(runtime, context, chunk_type, chunk_length, last_chunk_type, next_chunk):
        assert runtime.candy is namespace["Candy"]
        assert context.original_chunk_type == b"bad!"
        assert (chunk_type, chunk_length, last_chunk_type, next_chunk) == (
            b"IHDR",
            "0000000d",
            b"PNG",
            b"IDAT",
        )
        return "check"

    assert chunk_name_runtime.run_brute_chunk_from_namespace(
        namespace,
        b"bad!",
        b"IHDR",
        "00000004",
        "Relics",
        runner=brute_runner,
    ) == "brute"
    assert chunk_name_runtime.run_check_chunk_name_from_namespace(
        namespace,
        b"IHDR",
        "0000000d",
        b"PNG",
        b"IDAT",
        runner=check_runner,
    ) == "check"


def test_save_auto_name_from_namespace_preserves_checkpoint_payload():
    calls = []
    namespace = build_namespace(calls)
    namespace["CheckPoint"] = lambda *args: calls.append(("checkpoint", args)) or "saved"

    result = chunk_name_runtime.save_auto_name_from_namespace(
        namespace,
        b"bad!",
        "Relics",
        b"IDAT",
        "stored CRC matched candidate chunk name",
    )

    solved_msg = (
        "-Found Chunk[b'bad!'] has wrong name at offset: 0x8 but BruteChunk changed 4 bytes "
        "turning it into a valid Chunk name: IDAT (stored CRC matched candidate chunk name)"
    )
    assert result == "saved"
    assert calls == [
        (
            "checkpoint",
            (
                True,
                True,
                "CheckChunkName",
                b"bad!",
                [solved_msg],
                "49444154",
                16,
                24,
                b"bad!",
                solved_msg,
                "Relics",
            ),
        )
    ]


def main():
    checks = [
        ("Valid current chunk", test_check_chunk_name_accepts_exact_current_chunk),
        ("Wrong ancillary", test_check_chunk_name_routes_wrong_ancillary_current_chunk),
        ("IDAT length mismatch", test_check_chunk_name_routes_idat_length_mismatch),
        ("NameShift repair", test_brute_chunk_routes_nameshift_repair_to_checkpoint),
        ("CRC auto name", test_brute_chunk_prefers_single_crc_match_auto_name),
        ("Pokemon length", test_brute_chunk_pokemon_length_choice_routes_nearby_chunk),
        ("Namespace builders", test_chunk_name_namespace_builders_preserve_runtime_callbacks_and_context),
        ("Namespace runners", test_chunk_name_namespace_run_helpers_pass_legacy_arguments),
        ("Namespace auto save", test_save_auto_name_from_namespace_preserves_checkpoint_payload),
    ]

    print("Running chunk name runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"chunk name runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
