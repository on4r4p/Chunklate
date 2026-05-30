#!/usr/bin/env python3
import shutil
import subprocess
import sys
import tempfile
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate.png import iter_chunks, is_complete_png_with_valid_crc, validate_png_structure
from repair_matrix import (
    LEGACY_CRC_ONLY_REPAIR_CASES,
    PILLOW_LENIENT_REPAIR_CASES,
    PILLOW_ONLY_REPAIR_CASES,
    REPAIR_MATRIX,
    REPAIR_CASES,
    UNCOVERED_REPAIR_CASES,
)
from repair_validators import validate_repaired_case

try:
    from PIL import Image
except ModuleNotFoundError:
    Image = None


CHUNKLATE = ROOT / "Chunklate.py"
FIXTURES = ROOT / "Png_Errors_handled_by_Chunklate_So_Far"


def current_repair_fixture_names():
    if (ROOT / ".git").exists():
        result = subprocess.run(
            [
                "git",
                "ls-files",
                "--",
                "Png_Errors_handled_by_Chunklate_So_Far/*.png",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return {Path(path).name for path in result.stdout.splitlines()}

    return {path.name for path in FIXTURES.glob("*.png")}


def repair_validation_errors(path):
    return validate_png_structure(path.read_bytes()).errors


def pillow_verify_ok(path):
    if Image is None:
        return True

    try:
        with Image.open(path) as img:
            img.verify()
    except Exception:
        return False
    return True


def run_chunklate_repair(fixture_name, tmp_path, max_saves):
    sample = tmp_path / fixture_name
    shutil.copy2(FIXTURES / fixture_name, sample)
    output_dir = tmp_path / "repair_outputs"

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
            str(max_saves),
        ],
        cwd=tmp_path,
        input="yes\n" * 20,
        capture_output=True,
        text=True,
        timeout=10,
    )

    return result, output_dir / f"Folder_{sample.stem}"


def test_repair_cases_produce_expected_valid_pngs(tmp_path):
    failures = []

    for repair_case in REPAIR_MATRIX:
        result, output_dir = run_chunklate_repair(
            repair_case.fixture,
            tmp_path,
            repair_case.max_saves,
        )

        if result.returncode != 0:
            failures.append(f"{repair_case.fixture}: rc={result.returncode}; stderr={result.stderr[-500:]}")
            continue

        if not output_dir.exists():
            failures.append(f"{repair_case.fixture}: no output directory; rc={result.returncode}")
            continue

        summary_path = output_dir / f"Summary_Of_{Path(repair_case.fixture).stem}"
        for fixed_name in repair_case.expected_outputs:
            fixed_path = output_dir / fixed_name
            if not fixed_path.exists():
                failures.append(f"{repair_case.fixture}: missing {fixed_name}; rc={result.returncode}")
            else:
                validation_errors = validate_repaired_case(repair_case, fixed_path, summary_path)
                if validation_errors:
                    failures.append(f"{repair_case.fixture}: {'; '.join(validation_errors)}")

    assert failures == []


def test_pillow_only_repair_cases_produce_viewable_pngs(tmp_path):
    if PILLOW_ONLY_REPAIR_CASES and Image is None:
        raise AssertionError("Pillow is required for Pillow-only repair regression tests")

    failures = []

    for fixture_name, (max_saves, expected_fixed_names, reason) in PILLOW_ONLY_REPAIR_CASES.items():
        result, output_dir = run_chunklate_repair(fixture_name, tmp_path, max_saves)

        if result.returncode != 0:
            failures.append(f"{fixture_name}: rc={result.returncode}; stderr={result.stderr[-500:]}")
            continue

        if not output_dir.exists():
            failures.append(f"{fixture_name}: no output directory; rc={result.returncode}")
            continue

        for fixed_name in expected_fixed_names:
            fixed_path = output_dir / fixed_name
            if not fixed_path.exists():
                failures.append(f"{fixture_name}: missing {fixed_name}; rc={result.returncode}")
            elif not pillow_verify_ok(fixed_path):
                failures.append(f"{fixture_name}: Pillow rejected {fixed_name}; {reason}")

    assert failures == []


def test_legacy_crc_only_repair_cases_are_not_counted_as_strict_repairs(tmp_path):
    failures = []

    for fixture_name, (max_saves, expected_fixed_names, reason) in LEGACY_CRC_ONLY_REPAIR_CASES.items():
        result, output_dir = run_chunklate_repair(fixture_name, tmp_path, max_saves)

        if result.returncode != 0:
            failures.append(f"{fixture_name}: rc={result.returncode}; stderr={result.stderr[-500:]}")
            continue

        if not output_dir.exists():
            failures.append(f"{fixture_name}: no output directory; rc={result.returncode}")
            continue

        for fixed_name in expected_fixed_names:
            fixed_path = output_dir / fixed_name
            if not fixed_path.exists():
                failures.append(f"{fixture_name}: missing {fixed_name}; rc={result.returncode}")
                continue

            if not is_complete_png_with_valid_crc(fixed_path.read_bytes()):
                failures.append(f"{fixture_name}: legacy output is not even PNG/CRC-valid: {fixed_name}")
                continue

            validation_errors = repair_validation_errors(fixed_path)
            if not validation_errors:
                failures.append(f"{fixture_name}: move back to REPAIR_CASES; strict validation now passes")
            elif not reason:
                failures.append(f"{fixture_name}: missing reason for legacy CRC-only classification")

    assert failures == []


def test_all_current_repair_fixtures_are_classified():
    fixture_names = current_repair_fixture_names()
    classified_names = (
        set(REPAIR_CASES)
        | set(LEGACY_CRC_ONLY_REPAIR_CASES)
        | set(PILLOW_ONLY_REPAIR_CASES)
        | set(UNCOVERED_REPAIR_CASES)
    )

    assert fixture_names - classified_names == set()
    assert classified_names - fixture_names == set()
    assert {repair.fixture for repair in REPAIR_MATRIX if not repair.validators} == set()
    assert {repair.fixture for repair in REPAIR_MATRIX if not repair.summary_contains} == set()


def test_missing_ihdr_repair_summary_includes_selected_candidate(tmp_path):
    result, output_dir = run_chunklate_repair(
        "No_Png_Header_Missing_Chunk_Corrupted.png",
        tmp_path,
        2,
    )
    summary = output_dir / "Summary_Of_No_Png_Header_Missing_Chunk_Corrupted"

    assert result.returncode == 0
    assert summary.exists()
    summary_text = summary.read_text()
    assert "Selected IHDR 32x32, bit depth 8, color type 3" in summary_text
    assert "strict candidates:" in summary_text
    assert "selection score:" in summary_text


def test_partial_idat_blackfill_summary_and_output_are_explicit(tmp_path):
    result, output_dir = run_chunklate_repair(
        "IDAT_Partial_Blackfill.png",
        tmp_path,
        1,
    )
    repaired = output_dir / "IDAT_Partial_Blackfill.0_Fixed.png"
    summary = output_dir / "Summary_Of_IDAT_Partial_Blackfill"

    assert result.returncode == 0
    assert repaired.exists()
    assert summary.exists()
    assert validate_png_structure(repaired.read_bytes()).ok

    chunks = list(iter_chunks(repaired.read_bytes()))
    ihdr = chunks[0].data
    width = int.from_bytes(ihdr[0:4], "big")
    height = int.from_bytes(ihdr[4:8], "big")
    idat_stream = b"".join(chunk.data for chunk in chunks if chunk.chunk_type == b"IDAT")
    decompressed = zlib.decompress(idat_stream)

    assert (width, height) == (1, 10)
    assert len(decompressed) == 40

    summary_text = summary.read_text()
    assert "partial-idat-blackfill recovered 1/10 scanlines" in summary_text
    assert "Selected IHDR 1x10, bit depth 8, color type 2" in summary_text


def run_repair_cases_verbose(tmp_path):
    failures = []

    print("Running repair regression tests")
    for repair_case in REPAIR_MATRIX:
        print(
            f"  - {repair_case.fixture} -> max_saves={repair_case.max_saves}, "
            f"expect={', '.join(repair_case.expected_outputs)} ... ",
            end="",
            flush=True,
        )
        result, output_dir = run_chunklate_repair(repair_case.fixture, tmp_path, repair_case.max_saves)

        if result.returncode != 0:
            failures.append(f"{repair_case.fixture}: rc={result.returncode}; stderr={result.stderr[-500:]}")
            print("failed")
            continue

        missing_or_invalid = []
        summary_path = output_dir / f"Summary_Of_{Path(repair_case.fixture).stem}"
        for fixed_name in repair_case.expected_outputs:
            fixed_path = output_dir / fixed_name
            if not fixed_path.exists():
                missing_or_invalid.append(f"missing {fixed_name}")
            else:
                validation_errors = validate_repaired_case(repair_case, fixed_path, summary_path)
                if validation_errors:
                    missing_or_invalid.append(f"{fixed_name}: {'; '.join(validation_errors)}")

        if missing_or_invalid:
            failures.append(f"{repair_case.fixture}: {', '.join(missing_or_invalid)}")
            print("failed")
        elif repair_case.fixture in PILLOW_LENIENT_REPAIR_CASES:
            print(f"ok (PNG/CRC only; {PILLOW_LENIENT_REPAIR_CASES[repair_case.fixture]})")
        else:
            print("ok")

    if failures:
        print("\nRepair failures:")
        for failure in failures:
            print(f"  - {failure}")
        raise AssertionError("repair regression tests failed")


def run_pillow_only_repair_cases_verbose(tmp_path):
    if not PILLOW_ONLY_REPAIR_CASES:
        return

    if Image is None:
        raise AssertionError("Pillow is required for Pillow-viewable repair regression tests")

    failures = []

    print("\nRunning Pillow-viewable repair regression tests")
    for fixture_name, (max_saves, expected_fixed_names, reason) in PILLOW_ONLY_REPAIR_CASES.items():
        print(
            f"  - {fixture_name} -> max_saves={max_saves}, "
            f"expect={', '.join(expected_fixed_names)} ... ",
            end="",
            flush=True,
        )
        result, output_dir = run_chunklate_repair(fixture_name, tmp_path, max_saves)

        if result.returncode != 0:
            failures.append(f"{fixture_name}: rc={result.returncode}; stderr={result.stderr[-500:]}")
            print("failed")
            continue

        missing_or_invalid = []
        for fixed_name in expected_fixed_names:
            fixed_path = output_dir / fixed_name
            if not fixed_path.exists():
                missing_or_invalid.append(f"missing {fixed_name}")
            elif not pillow_verify_ok(fixed_path):
                missing_or_invalid.append(f"Pillow rejected {fixed_name}")

        if missing_or_invalid:
            failures.append(f"{fixture_name}: {', '.join(missing_or_invalid)}")
            print("failed")
        else:
            print(f"ok (Pillow-viewable only; {reason})")

    if failures:
        print("\nPillow-viewable repair failures:")
        for failure in failures:
            print(f"  - {failure}")
        raise AssertionError("Pillow-viewable repair regression tests failed")


def run_legacy_crc_only_repair_cases_verbose(tmp_path):
    if not LEGACY_CRC_ONLY_REPAIR_CASES:
        return

    failures = []

    print("\nRunning legacy CRC-only repair regression tests")
    for fixture_name, (max_saves, expected_fixed_names, reason) in LEGACY_CRC_ONLY_REPAIR_CASES.items():
        print(
            f"  - {fixture_name} -> max_saves={max_saves}, "
            f"expect={', '.join(expected_fixed_names)} ... ",
            end="",
            flush=True,
        )
        result, output_dir = run_chunklate_repair(fixture_name, tmp_path, max_saves)

        if result.returncode != 0:
            failures.append(f"{fixture_name}: rc={result.returncode}; stderr={result.stderr[-500:]}")
            print("failed")
            continue

        missing_or_invalid = []
        strict_errors = []
        for fixed_name in expected_fixed_names:
            fixed_path = output_dir / fixed_name
            if not fixed_path.exists():
                missing_or_invalid.append(f"missing {fixed_name}")
                continue
            if not is_complete_png_with_valid_crc(fixed_path.read_bytes()):
                missing_or_invalid.append(f"not PNG/CRC-valid {fixed_name}")
                continue
            validation_errors = repair_validation_errors(fixed_path)
            if not validation_errors:
                missing_or_invalid.append(f"{fixed_name} is now strict; move it to REPAIR_CASES")
            else:
                strict_errors.extend(validation_errors)

        if missing_or_invalid:
            failures.append(f"{fixture_name}: {', '.join(missing_or_invalid)}")
            print("failed")
        else:
            print(f"ok (legacy CRC-only; {reason}; strict errors: {'; '.join(sorted(set(strict_errors)))})")

    if failures:
        print("\nLegacy CRC-only repair failures:")
        for failure in failures:
            print(f"  - {failure}")
        raise AssertionError("legacy CRC-only repair regression tests failed")


def print_uncovered_repair_cases():
    print("\nClassified but not yet covered by green repair tests")
    for fixture_name, reason in sorted(UNCOVERED_REPAIR_CASES.items()):
        print(f"  - {fixture_name}: {reason}")


def main():
    with tempfile.TemporaryDirectory(prefix="chunklate-repair-tests-") as tmp:
        run_repair_cases_verbose(Path(tmp))
        run_pillow_only_repair_cases_verbose(Path(tmp))
        run_legacy_crc_only_repair_cases_verbose(Path(tmp))
    test_all_current_repair_fixtures_are_classified()
    with tempfile.TemporaryDirectory(prefix="chunklate-repair-summary-") as tmp:
        test_missing_ihdr_repair_summary_includes_selected_candidate(Path(tmp))
    with tempfile.TemporaryDirectory(prefix="chunklate-repair-idat-") as tmp:
        test_partial_idat_blackfill_summary_and_output_are_explicit(Path(tmp))
    print_uncovered_repair_cases()
    print(
        f"\nrepair regression tests passed "
        f"({len(REPAIR_CASES)} strict cases, "
        f"{len(PILLOW_ONLY_REPAIR_CASES)} Pillow-viewable cases, "
        f"{len(LEGACY_CRC_ONLY_REPAIR_CASES)} legacy CRC-only cases)"
    )


if __name__ == "__main__":
    main()
