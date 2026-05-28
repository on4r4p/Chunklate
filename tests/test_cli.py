#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHUNKLATE = ROOT / "Chunklate.py"
VALID_FIXTURE = ROOT / "schaik-javapng-samples" / "basn0g01.png"


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


def main():
    checks = [
        ("CLI help starts without optional runtime dependencies", test_help_starts_without_optional_runtime_dependencies),
        ("Missing -f/--file returns a usage error", test_missing_file_argument_returns_usage_error),
        ("Valid PNG exits successfully with optional libpng fallback", test_valid_png_exits_successfully_with_optional_libpng_fallback),
    ]

    print("Running CLI smoke tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"cli smoke tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
