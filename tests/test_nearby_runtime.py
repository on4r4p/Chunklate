#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import nearby, nearby_runtime


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


def main():
    checks = [
        ("Clean extra bytes", test_nearby_runtime_returns_clean_extra_bytes_before_scan),
        ("Known chunk checkpoint", test_nearby_runtime_known_chunk_routes_length_repair_checkpoint),
        ("Excluded trap", test_nearby_runtime_excluded_found_chunk_routes_legacy_trap),
        ("Doublecheck critical", test_nearby_runtime_doublecheck_missing_critical_routes_fixit),
    ]

    print("Running nearby runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"nearby runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
