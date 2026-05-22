#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_stderr_redirector_captures_stderr_and_restores_it():
    script = """
import io
import sys
from chunklate import stdio

stream = io.BytesIO()
with stdio.stderr_redirector(stream):
    sys.stderr.write("captured")
    sys.stderr.flush()

print(stream.getvalue().decode())
sys.stderr.write("restored")
sys.stderr.flush()
"""

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    assert result.stdout == "captured\n"
    assert result.stderr == "restored"


def main():
    checks = [
        ("stderr redirector captures and restores", test_stderr_redirector_captures_stderr_and_restores_it),
    ]

    print("Running stdio tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"stdio tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
