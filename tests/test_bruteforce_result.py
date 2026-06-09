#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import bruteforce, bruteforce_result


def build_runtime(calls, side_notes=None):
    side_notes = [] if side_notes is None else side_notes

    def emit(message):
        calls.append(("emit", message))

    def candy(kind, *args):
        calls.append(("candy", (kind,) + args))
        if kind == "Color":
            return "<%s:%s>" % (args[0], args[1])
        if kind == "Chunky":
            return ":%s:" % args[0]
        return "candy:%s" % kind

    def checkpoint(*args):
        calls.append(("checkpoint", args))
        return "checkpoint-result"

    return bruteforce_result.BruteForceResultRuntime(
        emit=emit,
        candy=candy,
        checkpoint=checkpoint,
        side_notes=side_notes,
    )


def base_context(**updates):
    context = {
        "state": bruteforce.BruteForceMatchState(),
        "old_crc": False,
        "file": "sample.png",
        "chunk_name": b"IDAT",
        "full_new_data_hex": "0011aa",
        "png_bytes_hex": "89504e47",
        "data_offset": 16,
        "chunk_length": 10,
        "to_brute": "001122",
        "edit_mode": "Replace",
        "bf_mode": "TwoBytes",
        "brute_crc": True,
        "brute_length": True,
        "from_error": "Relics",
        "diff": "0011\033[1;32;49maa\033[m",
        "tmp_image_paths": (),
    }
    context.update(updates)
    return bruteforce_result.BruteForceResultContext(**context)


def checkpoint_args(calls):
    matches = [call[1] for call in calls if call[0] == "checkpoint"]
    assert len(matches) == 1
    return matches[0]


def test_bruteforce_result_success_emits_repair_and_checkpoint():
    calls = []
    side_notes = []
    runtime = build_runtime(calls, side_notes)
    context = base_context(
        state=bruteforce.BruteForceMatchState(bingo=True, replace_flag=True),
    )

    result = bruteforce_result.run_result(runtime, context)

    assert result == "checkpoint-result"
    assert ("emit", "-Bruteforce was <green:Successfull!> :good:") in calls
    assert (
        "emit",
        "-Chunk <green:b'IDAT'> has been repaired by changing those bytes:\n",
    ) in calls
    assert ("emit", context.diff) in calls
    assert side_notes == [
        "\n-Launched Data Chunk Bruteforcer.\n-Bruteforce was successfull."
        "\n-Chunk b'IDAT' has been repaired by changing those bytes:\n%s"
        % context.diff
    ]
    assert checkpoint_args(calls) == (
        True,
        True,
        "SmashBruteBrawl",
        "IDAT",
        ["-Corrupted Data has been replaced"],
        "89504e47",
        16,
        26,
        "-Replacing Corrupted IDAT Data:\n001122\n-With:\n0011aa",
        "IDAT",
        "Relics",
    )


def test_bruteforce_result_success_preserves_bonus_note():
    calls = []
    side_notes = []
    runtime = build_runtime(calls, side_notes)
    context = base_context(
        state=bruteforce.BruteForceMatchState(
            bingo=True,
            insert_flag=True,
            bonus=True,
        ),
    )

    bruteforce_result.run_success(runtime, context)

    assert side_notes[0] == bruteforce.BRUTE_FORCE_BONUS_NOTE
    assert (
        "candy",
        ("Cowsay", bruteforce.BRUTE_FORCE_BONUS_NOTE, "bad"),
    ) in calls
    assert "adding those bytes" in side_notes[1]


def test_bruteforce_result_success_oldcrc_uses_validated_png_toolkit():
    calls = []
    runtime = build_runtime(calls)
    context = base_context(
        state=bruteforce.BruteForceMatchState(bingo=True, remove_flag=True),
        old_crc=b"crc",
    )

    bruteforce_result.run_success(runtime, context)

    assert checkpoint_args(calls) == (
        True,
        True,
        "SmashBruteBrawl",
        "IDAT",
        ["-Previous Crc checksum found by replacing datas"],
        "89504e47",
        0,
        -1,
        "-Replacing Corrupted IDAT Data:\n001122\n-With:\n0011aa",
        "IDAT",
        "Relics",
    )


def test_bruteforce_result_failure_emits_saved_images_and_checkpoint():
    calls = []
    side_notes = []
    runtime = build_runtime(calls, side_notes)
    context = base_context(tmp_image_paths=("/tmp/a.png", "/tmp/b.png"))

    result = bruteforce_result.run_result(runtime, context)

    assert result == "checkpoint-result"
    assert ("emit", "\n-Bruteforce has <red:Failed!> :bad:") in calls
    assert (
        "candy",
        ("Cowsay", "But while you were away i v saved some pictures maybe you should take a look ...", "bad"),
    ) in calls
    assert ("emit", "-Saved Valid Image: /tmp/a.png") in calls
    assert ("emit", "-Saved Valid Image: /tmp/b.png") in calls
    assert side_notes == [bruteforce.BRUTE_FORCE_FAILURE_NOTE]
    assert checkpoint_args(calls) == (
        True,
        False,
        "SmashBruteBrawl",
        "IDAT",
        ["-Bruteforcer has Failed"],
        "sample.png",
        b"IDAT",
        10,
        16,
        "Replace",
        "TwoBytes",
        True,
        True,
        "Relics",
    )


def main():
    checks = [
        ("Success result", test_bruteforce_result_success_emits_repair_and_checkpoint),
        ("Success bonus", test_bruteforce_result_success_preserves_bonus_note),
        ("Success OldCrc", test_bruteforce_result_success_oldcrc_uses_full_new_data_toolkit),
        ("Failure result", test_bruteforce_result_failure_emits_saved_images_and_checkpoint),
    ]

    print("Running bruteforce result tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"bruteforce result tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
