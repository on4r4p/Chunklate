#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import image_viewer


class FakeProcess:
    def __init__(self, return_code, *, pid=1234):
        self.return_code = return_code
        self.pid = pid
        self.terminated = False
        self.killed = False
        self.wait_calls = 0

    def poll(self):
        return self.return_code

    def terminate(self):
        self.terminated = True
        self.return_code = -15

    def kill(self):
        self.killed = True
        self.return_code = -9

    def wait(self, timeout=None):
        self.wait_calls += 1
        return self.return_code


def test_open_image_prefers_feh_when_available():
    calls = []

    def popen(command, **kwargs):
        calls.append((tuple(command), kwargs))
        return FakeProcess(None)

    result = image_viewer.open_image(
        "/tmp/fixed.png",
        popen=popen,
        which=lambda name: "/usr/bin/feh" if name == "feh" else None,
        sleep=lambda _seconds: None,
    )

    assert result.success is True
    assert result.opener == "feh"
    assert calls == [
        (
            ("/usr/bin/feh", "/tmp/fixed.png"),
            {
                "stdin": image_viewer.subprocess.DEVNULL,
                "stdout": image_viewer.subprocess.DEVNULL,
                "stderr": image_viewer.subprocess.DEVNULL,
                "close_fds": True,
                "start_new_session": True,
            },
        )
    ]


def test_open_image_falls_back_to_default_when_feh_fails():
    calls = []

    def popen(command, **_kwargs):
        calls.append(tuple(command))
        return FakeProcess(1 if len(calls) == 1 else None)

    result = image_viewer.open_image(
        "/tmp/fixed.png",
        popen=popen,
        which=lambda name: "/usr/bin/feh" if name == "feh" else None,
        sleep=lambda _seconds: None,
        platform="linux",
    )

    assert result.success is True
    assert result.opener == "xdg-open"
    assert calls == [
        ("/usr/bin/feh", "/tmp/fixed.png"),
        ("xdg-open", "/tmp/fixed.png"),
    ]
    assert result.attempts[0].success is False
    assert result.attempts[1].success is True


def test_open_image_uses_default_when_feh_is_missing():
    calls = []

    def popen(command, **_kwargs):
        calls.append(tuple(command))
        return FakeProcess(None)

    result = image_viewer.open_image(
        "/tmp/fixed.png",
        popen=popen,
        which=lambda _name: None,
        sleep=lambda _seconds: None,
        platform="linux",
    )

    assert result.success is True
    assert result.opener == "xdg-open"
    assert calls == [("xdg-open", "/tmp/fixed.png")]


def test_open_image_uses_windows_startfile_before_subprocess_launcher():
    calls = []

    def popen(_command, **_kwargs):
        raise AssertionError("subprocess launcher should not run when startfile succeeds")

    result = image_viewer.open_image(
        "C:/Users/Alice/My Pictures/fixed image.png",
        popen=popen,
        which=lambda _name: None,
        startfile=lambda path: calls.append(("startfile", path)),
        sleep=lambda _seconds: None,
        platform="win32",
    )

    assert result.success is True
    assert result.opener == "startfile"
    assert calls == [("startfile", "C:/Users/Alice/My Pictures/fixed image.png")]
    assert result.close(platform="win32") is False


def test_open_image_falls_back_to_cmd_start_when_windows_startfile_fails():
    calls = []

    def popen(command, **_kwargs):
        calls.append(tuple(command))
        return FakeProcess(None)

    result = image_viewer.open_image(
        "C:/Users/Alice/My Pictures/fixed image.png",
        popen=popen,
        which=lambda _name: None,
        startfile=lambda _path: (_ for _ in ()).throw(OSError("denied")),
        sleep=lambda _seconds: None,
        platform="win32",
    )

    assert result.success is True
    assert result.opener == "cmd"
    assert result.attempts[0].opener == "startfile"
    assert result.attempts[0].success is False
    assert calls == [("cmd", "/c", "start", "", "C:/Users/Alice/My Pictures/fixed image.png")]


def test_default_image_open_command_uses_platform_launcher():
    assert image_viewer.default_image_open_command("/tmp/a.png", platform="linux") == (
        "xdg-open",
        "/tmp/a.png",
    )
    assert image_viewer.default_image_open_command("/tmp/a.png", platform="darwin") == (
        "open",
        "/tmp/a.png",
    )
    assert image_viewer.default_image_open_command("C:/a.png", platform="win32") == (
        "cmd",
        "/c",
        "start",
        "",
        "C:/a.png",
    )


def test_image_open_result_close_terminates_live_viewer_process():
    process = FakeProcess(None)
    result = image_viewer.ImageOpenResult(
        True,
        "feh",
        (image_viewer.ImageOpenAttempt("feh", ("feh", "/tmp/fixed.png"), True, process=process),),
    )

    assert result.close(platform="win32") is True
    assert process.terminated is True
    assert process.wait_calls == 1


def test_image_open_result_close_is_noop_for_finished_viewer_process():
    process = FakeProcess(0)
    result = image_viewer.ImageOpenResult(
        True,
        "feh",
        (image_viewer.ImageOpenAttempt("feh", ("feh", "/tmp/fixed.png"), True, process=process),),
    )

    assert result.close(platform="win32") is False
    assert process.terminated is False


def main():
    checks = [
        ("Prefer feh", test_open_image_prefers_feh_when_available),
        ("Fallback after feh failure", test_open_image_falls_back_to_default_when_feh_fails),
        ("Fallback when feh is missing", test_open_image_uses_default_when_feh_is_missing),
        ("Windows startfile", test_open_image_uses_windows_startfile_before_subprocess_launcher),
        ("Windows cmd fallback", test_open_image_falls_back_to_cmd_start_when_windows_startfile_fails),
        ("Platform defaults", test_default_image_open_command_uses_platform_launcher),
        ("Close live viewer", test_image_open_result_close_terminates_live_viewer_process),
        ("Close finished viewer", test_image_open_result_close_is_noop_for_finished_viewer_process),
    ]

    print("Running image viewer tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"image viewer tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
