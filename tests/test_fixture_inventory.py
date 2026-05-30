#!/usr/bin/env python3
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_LINEFEED_FIXTURES = (
    Path("David/6.bad.png"),
    Path("David/6.output.png"),
)


def test_required_linefeed_fixtures_exist():
    missing = [
        str(path)
        for path in REQUIRED_LINEFEED_FIXTURES
        if not (ROOT / path).is_file()
    ]

    assert missing == []


def test_required_linefeed_fixtures_are_tracked_when_git_metadata_exists():
    if not (ROOT / ".git").exists():
        return

    result = subprocess.run(
        ["git", "ls-files", "--error-unmatch", *map(str, REQUIRED_LINEFEED_FIXTURES)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, (
        "Required fixtures must be tracked by git, not only present locally: "
        + result.stderr.strip()
    )
