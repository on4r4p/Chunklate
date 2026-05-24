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
        if kind == "Emoj":
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


def main():
    checks = [
        ("Valid current chunk", test_check_chunk_name_accepts_exact_current_chunk),
        ("Wrong ancillary", test_check_chunk_name_routes_wrong_ancillary_current_chunk),
        ("IDAT length mismatch", test_check_chunk_name_routes_idat_length_mismatch),
        ("NameShift repair", test_brute_chunk_routes_nameshift_repair_to_checkpoint),
        ("CRC auto name", test_brute_chunk_prefers_single_crc_match_auto_name),
        ("Pokemon length", test_brute_chunk_pokemon_length_choice_routes_nearby_chunk),
    ]

    print("Running chunk name runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"chunk name runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
