#!/usr/bin/env python3
from contextlib import contextmanager
from argparse import ArgumentParser
import builtins
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
CHUNKLATE = ROOT / "Chunklate.py"
VALID_FIXTURE = ROOT / "schaik-javapng-samples" / "basn0g01.png"
PLTE_EMPTY_FIXTURE = ROOT / "schaik-javapng-samples" / "brokenjavapngsuite" / "plte_empty.png"

import Chunklate
from chunklate import cli
from chunklate.png import iter_chunks, validate_png_structure


@contextmanager
def patched_attrs(module, **attrs):
    missing = object()
    old_values = {name: getattr(module, name, missing) for name in attrs}
    try:
        for name, value in attrs.items():
            setattr(module, name, value)
        yield
    finally:
        for name, value in old_values.items():
            if value is missing:
                delattr(module, name)
            else:
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
    assert "--no-color" in result.stdout
    assert "-workers" in result.stdout
    assert "-gpu" in result.stdout
    assert "--ultimate-linefeed-budget" not in result.stdout
    assert "-ulfb" not in result.stdout
    assert "--ultimate-linefeed-unbounded" not in result.stdout
    assert "-ulfu" not in result.stdout
    assert "--ultimate-linefeed-reference" not in result.stdout
    assert "-ulfr exact|similar PATH" in result.stdout
    assert "--ultimate-linefeed-reference-mode" not in result.stdout
    assert "-ulfrm" not in result.stdout
    assert "--ultimate-linefeed-reference-regions" not in result.stdout
    assert "-ulfroi PATH" not in result.stdout
    assert "--ultimate-linefeed-reference-region-editor" not in result.stdout
    assert "-ulfroi-edit" in result.stdout
    assert "--ultimate-linefeed-preview-timeout" not in result.stdout
    assert "-ulfpt" not in result.stdout
    assert "--ultimate-linefeed-show-previews" not in result.stdout
    assert "-ulfsp" in result.stdout
    assert "--ultimate-linefeed-visual-gallery-limit" not in result.stdout
    assert "-ulfgl" in result.stdout
    assert "--ultimate-linefeed-visual-min-coverage" not in result.stdout
    assert "-ulfmc" in result.stdout
    assert "--ultimate-linefeed-resume" not in result.stdout
    assert "-ulf-resume" not in result.stdout
    assert "--ultimate-linefeed-workers" not in result.stdout
    assert "-ulfw" not in result.stdout
    assert "--smashbrutebrawl-resume" not in result.stdout
    assert "-sbb-resume" not in result.stdout
    assert "--smashbrutebrawl-workers" not in result.stdout
    assert "-sbbw" not in result.stdout
    assert "--idat-huffman-kraft-workers" not in result.stdout
    assert "-ddll N" in result.stdout
    assert "--ddl-deflate-mitm" in result.stdout
    assert "-sbbl N" not in result.stdout
    assert "--sbb-deflate-mitm" not in result.stdout
    assert "--smashbrutebrawl-level" not in result.stdout
    assert "--ulf-budget" not in result.stdout


def test_sbb_crc_forge_bytes_accepts_targeted_20_byte_pass():
    assert cli.smash_brute_brawl_crc_forge_bytes_error("1") is None
    assert cli.smash_brute_brawl_crc_forge_bytes_error("20") is None
    assert cli.smash_brute_brawl_crc_forge_bytes_error("21") == (
        "--ddl-forge-bytes must be an integer from 1 to 20."
    )


def test_ultimate_linefeed_budget_prompt_supports_abort_choice():
    calls = []
    estimate = type(
        "Estimate",
        (),
        {
            "total_combinations": 1_000_000,
            "operation_count": 12,
            "max_depth": 4,
        },
    )()

    with patched_attrs(
        Chunklate,
        ULTIMATE_LINEFEED_UNBOUNDED=False,
        ULTIMATE_LINEFEED_BUDGET=None,
        AUTO=False,
        NODIALOGUE=False,
        Prompt_Candy=lambda mode, text, mood=None: calls.append(("prompt", mode, text, mood)),
        PRINT=lambda message: calls.append(("print", message)),
        Candy=lambda *args: args,
    ), patched_attrs(builtins, input=lambda _prompt: "10"):
        decision = Chunklate.Ultimate_Linefeed_Budget(estimate)

    assert decision.aborted is True
    assert "Enter a number from 1 to 10." in calls[0][2]
    assert "4. very deep       total / 1000" in calls[0][2]
    assert "5. deeeeeeep       total / 100" in calls[0][2]
    assert "6. abyssal         total / 10" in calls[0][2]
    assert "7. inception       total / 2" in calls[0][2]
    assert "8. no limit" in calls[0][2]
    assert "9. manual          exact candidate budget" in calls[0][2]
    assert "10. quit like a looser." in calls[0][2]


def test_ultimate_linefeed_reference_roi_cli_aliases_parse():
    parser = Chunklate.cli.configure_parser(ArgumentParser())
    args = parser.parse_args(
        [
            "-f",
            "sample.png",
            "-ulfroi",
            "regions.json",
            "-ulfroi-edit",
        ]
    )

    assert args.ULTIMATE_LINEFEED_REFERENCE_REGIONS == "regions.json"
    assert args.ULTIMATE_LINEFEED_REFERENCE_REGION_EDITOR is True


def test_ultimate_linefeed_combined_reference_cli_parses_mode_and_path():
    parser = Chunklate.cli.configure_parser(ArgumentParser())

    combined = parser.parse_args(["-f", "sample.png", "-ulfr", "similar", "ref.png"])
    legacy = parser.parse_args(["-f", "sample.png", "-ulfr", "ref.png", "-ulfrm", "similar"])

    assert combined.ULTIMATE_LINEFEED_REFERENCE == "ref.png"
    assert combined.ULTIMATE_LINEFEED_REFERENCE_MODE == "similar"
    assert legacy.ULTIMATE_LINEFEED_REFERENCE == "ref.png"
    assert legacy.ULTIMATE_LINEFEED_REFERENCE_MODE == "similar"


def test_ultimate_linefeed_workers_cli_parses_profiles_and_custom_count():
    parser = Chunklate.cli.configure_parser(ArgumentParser())

    profile_args = parser.parse_args(["-f", "sample.png", "-ulfw", "normal"])
    custom_args = parser.parse_args(["-f", "sample.png", "-ulfw", "12"])
    zero_args = parser.parse_args(["-f", "sample.png", "-ulfw", "0"])

    assert profile_args.ULTIMATE_LINEFEED_WORKERS == "normal"
    assert custom_args.ULTIMATE_LINEFEED_WORKERS == "12"
    assert zero_args.ULTIMATE_LINEFEED_WORKERS == "0"


def test_smash_brute_brawl_workers_cli_parses_profiles_and_custom_count():
    parser = Chunklate.cli.configure_parser(ArgumentParser())

    profile_args = parser.parse_args(["-f", "sample.png", "-ddlw", "normal"])
    custom_args = parser.parse_args(["-f", "sample.png", "-ddlw", "12"])
    zero_args = parser.parse_args(["-f", "sample.png", "-ddlw", "0"])
    old_alias_args = parser.parse_args(["-f", "sample.png", "-sbbw", "normal"])

    assert profile_args.SMASH_BRUTE_BRAWL_WORKERS == "normal"
    assert custom_args.SMASH_BRUTE_BRAWL_WORKERS == "12"
    assert zero_args.SMASH_BRUTE_BRAWL_WORKERS == "0"
    assert old_alias_args.SMASH_BRUTE_BRAWL_WORKERS == "normal"


def test_smash_brute_brawl_level_cli_parses_short_public_flag_only():
    parser = Chunklate.cli.configure_parser(ArgumentParser())

    level_args = parser.parse_args(["-f", "sample.png", "-ddll", "2"])
    old_alias_args = parser.parse_args(["-f", "sample.png", "-sbbl", "2"])

    assert level_args.SMASH_BRUTE_BRAWL_FORCE_LEVEL == "2"
    assert old_alias_args.SMASH_BRUTE_BRAWL_FORCE_LEVEL == "2"


def test_global_workers_cli_parses_without_exposing_specific_worker_flags():
    parser = Chunklate.cli.configure_parser(ArgumentParser())

    parsed = parser.parse_args(["-f", "sample.png", "-workers", "normal"])
    specific = parser.parse_args(
        [
            "-f",
            "sample.png",
            "-workers",
            "normal",
            "-ulfw",
            "3",
            "-ddlw",
            "max",
            "--idat-huffman-kraft-workers",
            "7",
        ]
    )

    assert parsed.GLOBAL_WORKERS == "normal"
    assert parsed.ULTIMATE_LINEFEED_WORKERS is None
    assert parsed.SMASH_BRUTE_BRAWL_WORKERS is None
    assert parsed.IDAT_HUFFMAN_KRAFT_WORKERS is None
    assert specific.GLOBAL_WORKERS == "normal"
    assert specific.ULTIMATE_LINEFEED_WORKERS == "3"
    assert specific.SMASH_BRUTE_BRAWL_WORKERS == "max"
    assert specific.IDAT_HUFFMAN_KRAFT_WORKERS == "7"


def test_idat_huffman_kraft_workers_cli_parses_profiles_and_custom_count():
    parser = Chunklate.cli.configure_parser(ArgumentParser())

    profile_args = parser.parse_args(["-f", "sample.png", "--idat-huffman-kraft-workers", "normal"])
    custom_args = parser.parse_args(["-f", "sample.png", "--idat-huffman-kraft-workers", "12"])
    auto_args = parser.parse_args(["-f", "sample.png", "--idat-huffman-kraft-workers", "auto"])

    assert profile_args.IDAT_HUFFMAN_KRAFT_WORKERS == "normal"
    assert custom_args.IDAT_HUFFMAN_KRAFT_WORKERS == "12"
    assert auto_args.IDAT_HUFFMAN_KRAFT_WORKERS == "auto"


def test_gpu_cli_parses_permission_flag():
    parser = Chunklate.cli.configure_parser(ArgumentParser())

    default_args = parser.parse_args(["-f", "sample.png"])
    gpu_args = parser.parse_args(["-f", "sample.png", "-gpu"])

    assert default_args.GPU is False
    assert gpu_args.GPU is True


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


def test_plte_empty_repairs_in_default_interactive_mode():
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        sample = tmp_path / PLTE_EMPTY_FIXTURE.name
        sample.write_bytes(PLTE_EMPTY_FIXTURE.read_bytes())
        output_dir = tmp_path / "out"

        result = subprocess.run(
            [
                sys.executable,
                str(CHUNKLATE),
                "-f",
                sample.name,
                "--output-dir",
                str(output_dir),
                "--no-color",
            ],
            cwd=tmp_path,
            input="yes\n" * 20,
            capture_output=True,
            text=True,
            timeout=10,
        )

        fixed_path = output_dir / "Folder_plte_empty" / "plte_empty.0_Fixed.png"
        summary_path = output_dir / "Folder_plte_empty" / "Summary_Of_plte_empty"

        assert result.returncode == 0
        assert fixed_path.exists()
        assert validate_png_structure(fixed_path.read_bytes()).ok
        plte = next(chunk for chunk in iter_chunks(fixed_path.read_bytes()) if chunk.chunk_type == b"PLTE")
        assert plte.length == 768
        assert "rebuilt empty indexed PLTE as grayscale palette" in summary_path.read_text(errors="replace")


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
    normalized = text.replace("\\", "/")
    assert "scripts/bootstrap_dev.py" in normalized
    assert ".venv/bin/python" in normalized or ".venv/Scripts/python.exe" in normalized


def test_runtime_dependency_check_reports_missing_imagehash_install_command():
    with patched_attrs(
        Chunklate,
        imagehash=None,
        MISSING_IMPORT_ERRORS={"ImageHash": ModuleNotFoundError("No module named 'imagehash'")},
    ):
        missing = Chunklate.Missing_Runtime_Dependencies()
        text = Chunklate.Format_Missing_Runtime_Dependencies(missing)

    error = next(error for package, _, error in missing if package == "ImageHash")
    assert ("ImageHash", "imagehash", error) in missing
    assert "- ImageHash (import imagehash)" in text


def test_runtime_dependency_message_uses_windows_paths_and_tkinter_guidance():
    missing = (("python3-tk", "tkinter", ModuleNotFoundError("No module named 'tkinter'")),)

    text = Chunklate.Format_Missing_Runtime_Dependencies(missing, os_name="nt")

    assert "scripts\\bootstrap_dev.py" in text or "scripts/bootstrap_dev.py" in text
    assert ".venv" in text
    assert "Scripts" in text
    assert "python.exe" in text
    assert "official Python for Windows installer" in text
    assert "sudo apt install python3-tk" not in text


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
    assert calls[1][1][0] == sys.executable
    assert calls[1][1][1].replace("\\", "/").endswith("scripts/bootstrap_dev.py")


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
    if os.name == "nt":
        venv_python = root / ".venv" / "Scripts" / "python.exe"
        real_python = tmp_path / "python-real.exe"
    else:
        venv_python = root / ".venv" / "bin" / "python"
        real_python = tmp_path / "python-real"
    venv_python.parent.mkdir(parents=True)
    real_python.write_text("")
    venv_python.write_text("")
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
        ("SBB CRC-forge accepts 20 bytes", test_sbb_crc_forge_bytes_accepts_targeted_20_byte_pass),
        ("Missing -f/--file returns a usage error", test_missing_file_argument_returns_usage_error),
        ("Valid PNG exits successfully with optional libpng fallback", test_valid_png_exits_successfully_with_optional_libpng_fallback),
        ("Empty PLTE repairs in default mode", test_plte_empty_repairs_in_default_interactive_mode),
        ("Runtime dependency check reports cv2", test_runtime_dependency_check_reports_missing_cv2_install_command),
        ("Runtime dependency check reports imagehash", test_runtime_dependency_check_reports_missing_imagehash_install_command),
        ("Runtime dependency check reports Windows tkinter", test_runtime_dependency_message_uses_windows_paths_and_tkinter_guidance),
        ("Dependency prompt runs bootstrap", test_dependency_install_prompt_runs_bootstrap_when_user_accepts),
        ("Dependency prompt skips noninteractive", test_dependency_install_prompt_does_not_run_in_noninteractive_mode),
        ("Ensure dependencies reexecs after install", test_ensure_runtime_dependencies_reexecs_after_successful_install),
        ("Venv reexec uses venv path", test_should_reexec_local_venv_uses_venv_path_not_realpath),
    ]

    print("Running CLI smoke tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        if check is test_should_reexec_local_venv_uses_venv_path_not_realpath:
            with tempfile.TemporaryDirectory(prefix="chunklate-cli-") as tmp:
                check(Path(tmp))
        else:
            check()
        print("ok")

    print(f"cli smoke tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
