#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import platform_runtime


class FakeStream:
    def __init__(self, tty):
        self.tty = tty

    def isatty(self):
        return self.tty


class FakeColorama:
    def __init__(self):
        self.calls = 0

    def just_fix_windows_console(self):
        self.calls += 1


class FakeTextStream:
    def __init__(self, fail=False):
        self.fail = fail
        self.calls = []

    def reconfigure(self, **kwargs):
        if self.fail:
            raise OSError("closed")
        self.calls.append(kwargs)


def test_os_family_detects_common_platforms():
    assert platform_runtime.os_family(platform="win32", os_name="nt") == "windows"
    assert platform_runtime.os_family(platform="darwin", os_name="posix") == "darwin"
    assert platform_runtime.os_family(platform="linux", os_name="posix") == "linux"


def test_local_venv_python_uses_platform_layouts():
    assert platform_runtime.local_venv_python("C:/repo", os_name="nt").replace("\\", "/").endswith(
        "C:/repo/.venv/Scripts/python.exe"
    )
    assert platform_runtime.local_venv_python("/repo", os_name="posix") == "/repo/.venv/bin/python"


def test_bootstrap_command_uses_python_script():
    assert platform_runtime.bootstrap_command("/repo", executable="python", os_name="posix") == [
        "python",
        "/repo/scripts/bootstrap_dev.py",
    ]


def test_format_command_uses_windows_and_posix_quoting():
    command = ["python", "C:/repo/scripts/bootstrap dev.py"]

    assert platform_runtime.format_command(command, os_name="nt") == 'python "C:/repo/scripts/bootstrap dev.py"'
    assert platform_runtime.format_command(command, os_name="posix") == "python 'C:/repo/scripts/bootstrap dev.py'"


def test_configure_text_stream_errors_uses_reconfigure_when_available():
    ok = FakeTextStream()
    failed = FakeTextStream(fail=True)

    assert platform_runtime.configure_text_stream_errors(ok, object(), failed, errors="replace") == 1
    assert ok.calls == [{"errors": "replace"}]


def test_terminal_color_decision_modes():
    colorama = FakeColorama()

    auto_non_tty = platform_runtime.decide_terminal_color(
        "auto",
        stream=FakeStream(False),
        os_name="posix",
        platform="linux",
    )
    windows_auto = platform_runtime.decide_terminal_color(
        "auto",
        stream=FakeStream(True),
        os_name="nt",
        platform="win32",
        colorama_module=colorama,
    )
    forced_off = platform_runtime.decide_terminal_color(
        "never",
        stream=FakeStream(True),
        os_name="nt",
        platform="win32",
        colorama_module=colorama,
    )

    assert auto_non_tty.use_color is False
    assert windows_auto.use_color is True
    assert windows_auto.initialized is True
    assert colorama.calls == 1
    assert forced_off.use_color is False


def main():
    checks = [
        ("OS family", test_os_family_detects_common_platforms),
        ("venv python path", test_local_venv_python_uses_platform_layouts),
        ("bootstrap command", test_bootstrap_command_uses_python_script),
        ("command quoting", test_format_command_uses_windows_and_posix_quoting),
        ("stream error handling", test_configure_text_stream_errors_uses_reconfigure_when_available),
        ("terminal color modes", test_terminal_color_decision_modes),
    ]

    print("Running platform runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"platform runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
