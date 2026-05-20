#!/usr/bin/env python3
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate.png import PngFormatError, iter_chunks

try:
    from PIL import Image
except ModuleNotFoundError:
    Image = None


CHUNKLATE = ROOT / "Chunklate.py"
FIXTURES = ROOT / "Png_Errors_handled_by_Chunklate_So_Far"


REPAIR_CASES = {
    "Bad-Chunk-Lenght-Missing-Bit.png": (1, ("Bad-Chunk-Lenght-Missing-Bit.0_Fixed.png",)),
    "Bad-Chunk-Length-Missing-Bit.png": (1, ("Bad-Chunk-Length-Missing-Bit.0_Fixed.png",)),
    "Bad-Chunk-Length-Exceeding-Bit.png": (1, ("Bad-Chunk-Length-Exceeding-Bit.0_Fixed.png",)),
    "Classic-Bad-Chunk-Crc.png": (1, ("Classic-Bad-Chunk-Crc.0_Fixed.png",)),
    "Classic-Bad-Chunk-Length.png": (1, ("Classic-Bad-Chunk-Length.0_Fixed.png",)),
    "IHDR-Messed-Up-Bad-Crc.png": (1, ("IHDR-Messed-Up-Bad-Crc.0_Fixed.png",)),
    "IHDR-Wrong-Height-Above-Estimated-Max-Resolution.png": (
        1,
        ("IHDR-Wrong-Height-Above-Estimated-Max-Resolution.0_Fixed.png",),
    ),
    "IHDR-Wrong-Quick.png": (1, ("IHDR-Wrong-Quick.0_Fixed.png",)),
    "IHDR-Wrong-Width-Bad-Crc.png": (1, ("IHDR-Wrong-Width-Bad-Crc.0_Fixed.png",)),
    "IHDR-Wrong-Width.png": (1, ("IHDR-Wrong-Width.0_Fixed.png",)),
    "IHDR_Messed_Up_Crc_Valid.png": (1, ("IHDR_Messed_Up_Crc_Valid.0_Fixed.png",)),
    "IHDR_Missplaced.png": (1, ("IHDR_Missplaced.0_Fixed.png",)),
    "IEND_Missing.png": (1, ("IEND_Missing.0_Fixed.png",)),
    "IEND_Missing_And_Extra_Bytes.png": (1, ("IEND_Missing_And_Extra_Bytes.0_Fixed.png",)),
    "Missplaced_Ihdr.png": (1, ("Missplaced_Ihdr.0_Fixed.png",)),
    "No_Png_Header.png": (1, ("No_Png_Header.0_Fixed.png",)),
    "No_Png_Header_Corrupted_Length.png": (1, ("No_Png_Header_Corrupted_Length.0_Fixed.png",)),
    "No_Png_Header_Missing_Chunk_Corrupted.png": (
        2,
        ("No_Png_Header_Missing_Chunk_Corrupted.1_Fixed.png",),
    ),
    "PLTE_Empty_Bad_Crc.png": (1, ("PLTE_Empty_Bad_Crc.0_Fixed.png",)),
    "PLTE_Empty_Good_Crc.png": (1, ("PLTE_Empty_Good_Crc.0_Fixed.png",)),
    "Private_Critical_Chunk_Bad_Crc.png": (2, ("Private_Critical_Chunk_Bad_Crc.1_Fixed.png",)),
    "Private_Critical_Chunk_Crc_Valid.png": (2, ("Private_Critical_Chunk_Crc_Valid.1_Fixed.png",)),
    "Wrong-Chunk-Name-Bad-Crc.png": (1, ("Wrong-Chunk-Name-Bad-Crc.0_Fixed.png",)),
    "Wrong-Chunk-Name-Crc-Valid.png": (2, ("Wrong-Chunk-Name-Crc-Valid.1_Fixed.png",)),
    "chunk_crc.png": (1, ("chunk_crc.0_Fixed.png",)),
    "chunk_private_critical_badcrc.png": (2, ("chunk_private_critical_badcrc.1_Fixed.png",)),
    "chunk_private_critical_goodcrc.png": (2, ("chunk_private_critical_goodcrc.1_Fixed.png",)),
    "chunk_type.png": (2, ("chunk_type.1_Fixed.png",)),
    "gama_zero.png": (1, ("gama_zero.0_Fixed.png",)),
    "ihdr_image_size.png": (1, ("ihdr_image_size.0_Fixed.png",)),
}


PILLOW_LENIENT_REPAIR_CASES = {
    "No_Png_Header_Missing_Chunk_Corrupted.png": (
        "legacy repair can generate multiple CRC-valid variants; Pillow is not deterministic yet"
    ),
}


PILLOW_ONLY_REPAIR_CASES = {}


NO_NONINTERACTIVE_CLONE = "non-interactive audit exits rc=1 before writing any _Fixed.png"
NEEDS_EXPLICIT_LIBPNG_PROFILE_WARNING = "needs explicit known incorrect sRGB profile signal before removing iCCP"
UNCOVERED_REPAIR_CASES = {
    "Good-Chunk-lenght-Missing-Bit.png": NO_NONINTERACTIVE_CLONE,
    "IncorrectSrgbProfile.png": NEEDS_EXPLICIT_LIBPNG_PROFILE_WARNING,
    "Incorrect_Srgb_Profile.png": NEEDS_EXPLICIT_LIBPNG_PROFILE_WARNING,
    "Unhandled-Critical-Chunk.png": NO_NONINTERACTIVE_CLONE,
    "chunk_private_critical.png": NO_NONINTERACTIVE_CLONE,
}


def is_complete_png_with_valid_crc(path):
    try:
        chunks = list(iter_chunks(path.read_bytes()))
    except PngFormatError:
        return False

    return bool(chunks) and chunks[-1].chunk_type == b"IEND" and all(chunk.crc_ok for chunk in chunks)


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

    for fixture_name, (max_saves, expected_fixed_names) in REPAIR_CASES.items():
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
            elif not is_complete_png_with_valid_crc(fixed_path):
                failures.append(f"{fixture_name}: invalid repaired PNG {fixed_name}")
            elif fixture_name not in PILLOW_LENIENT_REPAIR_CASES and not pillow_verify_ok(fixed_path):
                failures.append(f"{fixture_name}: Pillow rejected repaired PNG {fixed_name}")

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


def test_all_current_repair_fixtures_are_classified():
    fixture_names = {path.name for path in FIXTURES.glob("*.png")}
    classified_names = set(REPAIR_CASES) | set(PILLOW_ONLY_REPAIR_CASES) | set(UNCOVERED_REPAIR_CASES)

    assert fixture_names - classified_names == set()
    assert classified_names - fixture_names == set()


def run_repair_cases_verbose(tmp_path):
    failures = []

    print("Running repair regression tests")
    for fixture_name, (max_saves, expected_fixed_names) in REPAIR_CASES.items():
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
            elif not is_complete_png_with_valid_crc(fixed_path):
                missing_or_invalid.append(f"invalid PNG/CRC {fixed_name}")
            elif fixture_name not in PILLOW_LENIENT_REPAIR_CASES and not pillow_verify_ok(fixed_path):
                missing_or_invalid.append(f"Pillow rejected {fixed_name}")

        if missing_or_invalid:
            failures.append(f"{fixture_name}: {', '.join(missing_or_invalid)}")
            print("failed")
        elif fixture_name in PILLOW_LENIENT_REPAIR_CASES:
            print(f"ok (PNG/CRC only; {PILLOW_LENIENT_REPAIR_CASES[fixture_name]})")
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


def print_uncovered_repair_cases():
    print("\nClassified but not yet covered by green repair tests")
    for fixture_name, reason in sorted(UNCOVERED_REPAIR_CASES.items()):
        print(f"  - {fixture_name}: {reason}")


def main():
    with tempfile.TemporaryDirectory(prefix="chunklate-repair-tests-") as tmp:
        run_repair_cases_verbose(Path(tmp))
        run_pillow_only_repair_cases_verbose(Path(tmp))
    test_all_current_repair_fixtures_are_classified()
    print_uncovered_repair_cases()
    print(
        f"\nrepair regression tests passed "
        f"({len(REPAIR_CASES)} strict cases, {len(PILLOW_ONLY_REPAIR_CASES)} Pillow-viewable cases)"
    )


if __name__ == "__main__":
    main()
