#!/usr/bin/env python3
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

from candidate_matrix import CANDIDATE_CASES


CHUNKLATE = ROOT / "Chunklate.py"


def run_candidate(case, tmp_path):
    source = ROOT / case.source_path
    sample = tmp_path / case.fixture
    shutil.copy2(source, sample)
    output_dir = tmp_path / "candidate_outputs"

    result = subprocess.run(
        [
            sys.executable,
            str(CHUNKLATE),
            "-f",
            sample.name,
            "-stfu",
            "--output-dir",
            str(output_dir),
            "--max-saves",
            str(case.max_saves),
        ],
        cwd=tmp_path,
        input="yes\n" * 20,
        capture_output=True,
        text=True,
        timeout=10,
    )

    return result, output_dir / f"Folder_{sample.stem}"


def test_candidate_corpus_files_exist():
    missing = [
        case.source_path
        for case in CANDIDATE_CASES
        if not (ROOT / case.source_path).is_file()
    ]

    assert missing == []


def test_candidate_corpus_runs_without_python_crash_or_repo_output(tmp_path):
    failures = []

    for case in CANDIDATE_CASES:
        try:
            result, output_dir = run_candidate(case, tmp_path)
        except subprocess.TimeoutExpired:
            failures.append(f"{case.fixture}: timed out")
            continue

        combined_output = result.stdout + result.stderr
        has_traceback = "Traceback (most recent call last)" in combined_output
        if has_traceback and not case.known_python_traceback:
            failures.append(f"{case.fixture}: Python traceback")
        if case.known_python_traceback and not has_traceback:
            failures.append(f"{case.fixture}: expected known traceback is gone; reclassify it")
        if output_dir.exists() and not output_dir.is_relative_to(tmp_path):
            failures.append(f"{case.fixture}: output outside tmp_path: {output_dir}")

    assert failures == []


def main():
    checks = [
        ("candidate files", test_candidate_corpus_files_exist),
        ("candidate run smoke", test_candidate_corpus_runs_without_python_crash_or_repo_output),
    ]

    print("Running candidate corpus tests")
    with tempfile.TemporaryDirectory(prefix="chunklate-candidate-corpus-") as tmp:
        for label, check in checks:
            print(f"  - {label} ... ", end="", flush=True)
            if label == "candidate run smoke":
                check(Path(tmp))
            else:
                check()
            print("ok")

    print(f"candidate corpus tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
