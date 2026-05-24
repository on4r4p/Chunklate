#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import full_chunk_forcer


class FakeFile:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return self.data


class FakeRedirectorFactory:
    def __init__(self, outputs=()):
        self.outputs = list(outputs)

    def __call__(self, stream):
        output = self.outputs.pop(0) if self.outputs else ""

        class Redirector:
            def __enter__(self_inner):
                stream.write(output.encode())
                return self_inner

            def __exit__(self_inner, exc_type, exc, traceback):
                return False

        return Redirector()


class FakeNumpy:
    uint8 = "uint8"

    def __init__(self, calls):
        self.calls = calls

    def fromstring(self, data, dtype):
        self.calls.append(("fromstring", data, dtype))
        return ("array", data, dtype)


class FakeCv2:
    IMREAD_COLOR = "color"

    def __init__(self, calls):
        self.calls = calls

    def imdecode(self, array, mode):
        self.calls.append(("imdecode", array, mode))
        return "decoded"

    def imread(self, image):
        self.calls.append(("imread", image))
        return "read"


def build_runtime(calls, *, file_data=b"\xaa\xbb\xcc\xdd", probe_outputs=("",)):
    side_notes = []

    def emit(*args):
        calls.append(("emit", args))

    def candy(kind, *args):
        calls.append(("candy", (kind,) + args))
        if kind == "Color":
            return "<%s:%s>" % (args[0], args[1])
        if kind == "Emoj":
            return ":%s:" % args[0]
        return "candy:%s" % kind

    def checkpoint(*args):
        calls.append(("checkpoint", args))
        return "checkpoint-result"

    def open_file(path, mode):
        calls.append(("open_file", path, mode))
        return FakeFile(file_data)

    return full_chunk_forcer.FullChunkForcerRuntime(
        emit=emit,
        candy=candy,
        checkpoint=checkpoint,
        side_notes=side_notes,
        minibar=lambda: calls.append(("minibar",)),
        pause=lambda message: calls.append(("pause", message)),
        end=lambda: calls.append(("end",)),
        save_error=lambda error, name: calls.append(("save_error", str(error), name)),
        cv2=FakeCv2(calls),
        numpy=FakeNumpy(calls),
        stderr_redirector=FakeRedirectorFactory(probe_outputs),
        ask=lambda prompt: calls.append(("ask", prompt)),
        open_file=open_file,
    )


def base_context(**updates):
    context = {
        "file": "broken.png",
        "chunk": b"gAMA",
        "data_offset": 0,
        "chunk_length": 4,
        "from_error": "Relics",
        "sample_path": "broken.png",
        "data_hex": "0011223344556677",
        "debug": False,
        "pause_debug": False,
        "pause_error": False,
    }
    context.update(updates)
    return full_chunk_forcer.FullChunkForcerContext(**context)


def checkpoint_args(calls):
    matches = [call[1] for call in calls if call[0] == "checkpoint"]
    assert len(matches) == 1
    return matches[0]


def test_build_candidate_preserves_legacy_slices_and_crc():
    candidate = full_chunk_forcer.build_candidate(
        b"gAMA",
        "0011223344556677",
        "aabb",
        0,
        4,
        "00",
        0,
    )

    assert candidate.old_data_hex == ""
    assert candidate.full_new_data_hex == "aabb00bb8535e2ab"
    assert candidate.candidate_file_hex == "aabb00bb8535e2ab223344556677"
    assert candidate.good_diff == "\033[1;32;49m\033[m"
    assert candidate.bad_diff == "\033[1;31;49m\033[m"


def test_full_chunk_forcer_success_routes_checkpoint_and_side_note():
    calls = []
    runtime = build_runtime(calls, file_data=bytes.fromhex("aabbccdd"))
    context = base_context()
    expected = full_chunk_forcer.build_candidate(
        b"gAMA",
        context.data_hex,
        "aabb",
        context.data_offset,
        context.chunk_length,
        "00",
        0,
    )

    result = full_chunk_forcer.run_legacy_full_chunk_forcer_no_crc(runtime, context)

    assert result == "checkpoint-result"
    assert ("open_file", "broken.png", "rb") in calls
    assert ("ask", "pause") in calls
    assert ("emit", ("-Bruteforce was <green:Successfull!> :good:",)) in calls
    assert checkpoint_args(calls) == (
        True,
        True,
        "FullChunkForcerNoCrc",
        "gAMA",
        ["-Data has been corrupted"],
        expected.full_new_data_hex,
        0,
        4,
        "-Replacing Corrupted gAMA Data:\n\n-With:\n%s" % expected.full_new_data_hex,
        "gAMA",
        "Relics",
    )
    assert runtime.side_notes == [
        "\n-Launched Data Chunk Bruteforcer.\n-Bruteforce was successfull."
        "\n-Chunk b'gAMA' has been repaired by changing those bytes:\n"
        "\n-with bytes:\n%s" % expected.full_new_data_hex
    ]


def test_full_chunk_forcer_failure_routes_theend_and_checkpoint():
    calls = []
    runtime = build_runtime(calls, file_data=b"")
    context = base_context(chunk_length=0)

    result = full_chunk_forcer.run_legacy_full_chunk_forcer_no_crc(runtime, context)

    assert result == "checkpoint-result"
    assert ("end",) in calls
    assert checkpoint_args(calls) == (
        True,
        False,
        "FullChunkForcerNoCrc",
        "gAMA",
        ["-Bruteforcer has Failed"],
        "Relics",
    )
    assert runtime.side_notes == ["\n-Launched Data Chunk Bruteforcer.\n-Bruteforce has Failed!"]


def test_full_chunk_forcer_read_error_calls_end_without_checkpoint():
    calls = []
    runtime = build_runtime(calls)

    def fail_open(path, mode):
        raise FileNotFoundError("missing")

    runtime = full_chunk_forcer.FullChunkForcerRuntime(
        **{
            **runtime.__dict__,
            "open_file": fail_open,
        }
    )

    result = full_chunk_forcer.run_legacy_full_chunk_forcer_no_crc(runtime, base_context())

    assert result is None
    assert ("save_error", "missing", "FullChunkForcerNoCrc") in calls
    assert ("end",) in calls
    assert not [call for call in calls if call[0] == "checkpoint"]


def main():
    checks = [
        ("Build candidate", test_build_candidate_preserves_legacy_slices_and_crc),
        ("Success checkpoint", test_full_chunk_forcer_success_routes_checkpoint_and_side_note),
        ("Failure checkpoint", test_full_chunk_forcer_failure_routes_theend_and_checkpoint),
        ("Read error", test_full_chunk_forcer_read_error_calls_end_without_checkpoint),
    ]

    print("Running full chunk forcer tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"full chunk forcer tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
