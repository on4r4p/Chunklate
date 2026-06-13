#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import bruteforce_viewer


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

    def frombuffer(self, data, dtype):
        return ("array", data, dtype)


class FakeCv2:
    def __init__(self, calls):
        self.calls = calls

    def imdecode(self, array, flags):
        self.calls.append(("imdecode", array, flags))
        return "decoded"


class FakeImageObject:
    def __init__(self, calls, size=(64, 32), mode="RGBA"):
        self.calls = calls
        self.size = size
        self.mode = mode

    def show(self):
        self.calls.append(("show", self.size, self.mode))

    def convert(self, mode):
        self.calls.append(("convert", mode))
        return FakeImageObject(self.calls, self.size, mode)

    def save(self, path):
        self.calls.append(("save", path))


class FakeImageModule:
    def __init__(self, calls):
        self.calls = calls

    def open(self, stream):
        self.calls.append(("open", type(stream).__name__))
        return FakeImageObject(self.calls)


class FakeProcess:
    def __init__(self, path="/tmp/tmpabcd.PNG"):
        self.path = path
        self.killed = False

    def cmdline(self):
        return ("/usr/bin/display", self.path)

    def kill(self):
        self.killed = True


class FakePsutil:
    def __init__(self, calls, processes):
        self.calls = calls
        self.processes = processes

    def process_iter(self):
        self.calls.append(("process_iter",))
        return self.processes


def build_runtime(
    calls,
    *,
    redirect_outputs=(),
    answer="yes",
    processes=None,
    tmp_image_paths=None,
):
    tmp_image_paths = [] if tmp_image_paths is None else tmp_image_paths
    processes = [FakeProcess()] if processes is None else processes

    def emit(message):
        calls.append(("emit", message))

    def candy(kind, *args):
        calls.append(("candy", (kind,) + args))
        if kind == "Color":
            return "<%s:%s>" % (args[0], args[1])
        return "candy:%s" % kind

    def summarise(message):
        calls.append(("summarise", message))

    def ask_timeout(prompt="", timeout=None):
        calls.append(("ask_timeout", prompt, timeout))
        if isinstance(answer, BaseException):
            raise answer
        return answer

    def naming(file_origin):
        calls.append(("naming", file_origin))
        return "sample.png", "/tmp/out"

    def sleep(seconds):
        calls.append(("sleep", seconds))

    def save_error(error, def_name):
        calls.append(("save_error", str(error), def_name))

    def end():
        calls.append(("end",))
        return "ended"

    return bruteforce_viewer.BruteForceViewerRuntime(
        data_hex="ffffffff0011223344",
        data_offset=8,
        libpng_errors=("libpng error",),
        tmp_image_paths=tmp_image_paths,
        cv2=FakeCv2(calls),
        numpy=FakeNumpy(),
        image=FakeImageModule(calls),
        psutil=FakePsutil(calls, processes),
        stderr_redirector=FakeRedirectorFactory(redirect_outputs),
        sleep=sleep,
        ask_timeout=ask_timeout,
        naming=naming,
        file_origin="/tmp/sample.png",
        emit=emit,
        candy=candy,
        summarise=summarise,
        save_error=save_error,
        end=end,
        raw_print=lambda *args, **kwargs: calls.append(("raw_print", args, kwargs)),
    )


def test_viewer_rejects_libpng_error_without_opening_image():
    calls = []
    runtime = build_runtime(calls, redirect_outputs=("libpng error: bad filter",))

    result = bruteforce_viewer.show_candidate(runtime, b"png", bytes.fromhex("0011aa3344"), 12)

    assert result == bruteforce_viewer.BruteForceViewerResult(False)
    assert not [call for call in calls if call[0] == "open"]
    assert calls[0][0] == "imdecode"


def test_viewer_accepts_user_confirmed_candidate_and_returns_diff():
    calls = []
    runtime = build_runtime(calls, answer="yes")

    result = bruteforce_viewer.show_candidate(
        runtime,
        b"png",
        bytes.fromhex("0011aa3344"),
        12,
    )

    assert result.accepted is True
    assert result.diff == "0011\033[1;32;49maa\033[m3344"
    assert ("show", (64, 32), "RGBA") in calls
    assert ("emit", "-Tmp Image Number 10") in calls
    assert ("summarise", "-DaedalusForce:User chose yes at tries nbr:10") in calls


def test_viewer_decline_kills_tmp_viewers():
    calls = []
    tmp_proc = FakeProcess()
    runtime = build_runtime(calls, answer="no", processes=[tmp_proc])

    result = bruteforce_viewer.show_candidate(
        runtime,
        b"png",
        bytes.fromhex("0011aa3344"),
        12,
    )

    assert result == bruteforce_viewer.BruteForceViewerResult(False)
    assert tmp_proc.killed is True
    assert ("candy", ("Cowsay", "Ok back to work..", "bad")) in calls


def test_viewer_timeout_saves_candidate_image():
    calls = []
    tmp_image_paths = []
    runtime = build_runtime(
        calls,
        answer=TimeoutError("timeout"),
        tmp_image_paths=tmp_image_paths,
    )

    result = bruteforce_viewer.show_candidate(
        runtime,
        b"png",
        bytes.fromhex("0011aa3344"),
        12,
    )

    assert result == bruteforce_viewer.BruteForceViewerResult(False)
    assert len(tmp_image_paths) == 1
    assert tmp_image_paths[0].startswith("/tmp/out/BF-W64-H32-")
    assert tmp_image_paths[0].endswith("sample.png")
    assert ("emit", "\n-Skipped No input given within time limit.\n") in calls
    assert any(call[0] == "save" and call[1] == tmp_image_paths[0] for call in calls)


def main():
    checks = [
        ("Reject libpng error", test_viewer_rejects_libpng_error_without_opening_image),
        ("Accept confirmed candidate", test_viewer_accepts_user_confirmed_candidate_and_returns_diff),
        ("Decline candidate", test_viewer_decline_kills_tmp_viewers),
        ("Timeout saves candidate", test_viewer_timeout_saves_candidate_image),
    ]

    print("Running bruteforce viewer tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"bruteforce viewer tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
