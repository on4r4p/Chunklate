#!/usr/bin/env python3
from contextlib import contextmanager
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
CHUNKLATE = ROOT / "Chunklate.py"
VALID_FIXTURE = ROOT / "schaik-javapng-samples" / "basn0g01.png"

import Chunklate


@contextmanager
def patched_attrs(module, **attrs):
    old_values = {name: getattr(module, name) for name in attrs}
    try:
        for name, value in attrs.items():
            setattr(module, name, value)
        yield
    finally:
        for name, value in old_values.items():
            setattr(module, name, value)


class FakeStdin:
    def __init__(self, interactive=True):
        self.interactive = interactive

    def isatty(self):
        return self.interactive


class RunResult:
    def __init__(self, returncode=0):
        self.returncode = returncode


def run_chunklate(*args):
    return subprocess.run(
        [sys.executable, str(CHUNKLATE), *args],
        capture_output=True,
        text=True,
        timeout=10,
    )


def test_help_starts_without_optional_runtime_dependencies():
    result = run_chunklate("-h")

    assert result.returncode == 0
    assert "usage:" in result.stdout
    assert "--file" in result.stdout
    assert "--clear" in result.stdout
    assert "--output-dir" in result.stdout
    assert "--max-saves" in result.stdout
    assert "--ultimate-linefeed-budget" in result.stdout
    assert "--ultimate-linefeed-unbounded" in result.stdout


def test_missing_file_argument_returns_usage_error():
    result = run_chunklate()

    assert result.returncode == 1
    assert "usage:" in result.stderr


def test_valid_png_exits_successfully_with_optional_libpng_fallback():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        sample = tmp_path / VALID_FIXTURE.name
        sample.write_bytes(VALID_FIXTURE.read_bytes())

        result = subprocess.run(
            [
                sys.executable,
                str(CHUNKLATE),
                "-f",
                sample.name,
                "-stfu",
                "--output-dir",
                str(tmp_path / "out"),
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=10,
        )

    assert result.returncode == 0


def test_runtime_dependency_check_reports_missing_cv2_install_command():
    with patched_attrs(
        Chunklate,
        cv2=None,
        MISSING_IMPORT_ERRORS={"opencv-python": ModuleNotFoundError("No module named 'cv2'")},
    ):
        missing = Chunklate.Missing_Runtime_Dependencies()
        text = Chunklate.Format_Missing_Runtime_Dependencies(missing)

    assert ("opencv-python", "cv2", next(error for package, _, error in missing if package == "opencv-python")) in missing
    assert "- opencv-python (import cv2)" in text
    assert "scripts/bootstrap_dev.sh" in text
    assert ".venv/bin/python" in text


def test_dependency_install_prompt_runs_bootstrap_when_user_accepts():
    calls = []
    missing = (("opencv-python", "cv2", ModuleNotFoundError("No module named 'cv2'")),)

    with patched_attrs(Chunklate, NODIALOGUE=False, AUTO=False):
        result = Chunklate.Prompt_Dependency_Install(
            missing,
            input_func=lambda prompt: calls.append(("prompt", prompt)) or "yes",
            stdin=FakeStdin(True),
            runner=lambda args, cwd: calls.append(("run", args, cwd)) or RunResult(0),
        )

    assert result is True
    assert calls[0] == ("prompt", "Install/refresh missing dependencies now? (yes/no): ")
    assert calls[1][0] == "run"
    assert calls[1][1][0].endswith("scripts/bootstrap_dev.sh")


def test_dependency_install_prompt_does_not_run_in_noninteractive_mode():
    calls = []
    missing = (("opencv-python", "cv2", ModuleNotFoundError("No module named 'cv2'")),)

    with patched_attrs(Chunklate, NODIALOGUE=False, AUTO=False):
        result = Chunklate.Prompt_Dependency_Install(
            missing,
            input_func=lambda prompt: calls.append(("prompt", prompt)) or "yes",
            stdin=FakeStdin(False),
            runner=lambda args, cwd: calls.append(("run", args, cwd)) or RunResult(0),
        )

    assert result is False
    assert calls == []


def test_ensure_runtime_dependencies_reexecs_after_successful_install():
    calls = []

    with patched_attrs(
        Chunklate,
        cv2=None,
        MISSING_IMPORT_ERRORS={"opencv-python": ModuleNotFoundError("No module named 'cv2'")},
    ):
        assert (
            Chunklate.Ensure_Runtime_Dependencies(
                prompt_installer=lambda missing: calls.append(("install", missing)) or True,
                reexec=lambda: calls.append(("reexec",)),
            )
            is True
        )

    assert calls[0][0] == "install"
    assert calls[1] == ("reexec",)


def test_should_reexec_local_venv_uses_venv_path_not_realpath(tmp_path):
    root = tmp_path / "project"
    venv_bin = root / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    real_python = tmp_path / "python-real"
    real_python.write_text("")
    venv_python = venv_bin / "python"
    venv_python.symlink_to(real_python)
    script = root / "Chunklate.py"
    script.write_text("")

    assert Chunklate.Should_Reexec_Local_Venv(
        str(script),
        executable=str(real_python),
        env={},
    )
    assert not Chunklate.Should_Reexec_Local_Venv(
        str(script),
        executable=str(venv_python),
        env={},
    )


def main():
    checks = [
        ("CLI help starts without optional runtime dependencies", test_help_starts_without_optional_runtime_dependencies),
        ("Missing -f/--file returns a usage error", test_missing_file_argument_returns_usage_error),
        ("Valid PNG exits successfully with optional libpng fallback", test_valid_png_exits_successfully_with_optional_libpng_fallback),
        ("Runtime dependency check reports cv2", test_runtime_dependency_check_reports_missing_cv2_install_command),
        ("Dependency prompt runs bootstrap", test_dependency_install_prompt_runs_bootstrap_when_user_accepts),
        ("Dependency prompt skips noninteractive", test_dependency_install_prompt_does_not_run_in_noninteractive_mode),
        ("Ensure dependencies reexecs after install", test_ensure_runtime_dependencies_reexecs_after_successful_install),
        ("Venv reexec uses venv path", test_should_reexec_local_venv_uses_venv_path_not_realpath),
    ]

    print("Running CLI smoke tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"cli smoke tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
