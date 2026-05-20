#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHUNKLATE = ROOT / "Chunklate.py"


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


def test_missing_file_argument_returns_usage_error():
    result = run_chunklate()

    assert result.returncode == 1
    assert "usage:" in result.stderr


def main():
    checks = [
        ("CLI help starts without optional runtime dependencies", test_help_starts_without_optional_runtime_dependencies),
        ("Missing -f/--file returns a usage error", test_missing_file_argument_returns_usage_error),
    ]

    print("Running CLI smoke tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"cli smoke tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
