#!/usr/bin/env python3
import sys
import tempfile
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import libpng_check
from chunklate.png import IEND_CHUNK, PNG_SIGNATURE, build_png_chunk


FIXTURE = ROOT / "schaik-javapng-samples" / "basn0g01.png"


class FakeVerifiedImage:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def verify(self):
        return None


class FakePillowOk:
    @staticmethod
    def open(file):
        return FakeVerifiedImage()


class FakePillowError:
    @staticmethod
    def open(file):
        raise ValueError("bad pixels")


class FakeCv2:
    @staticmethod
    def imread(file):
        return None


class FakeRedirector:
    def __init__(self, stream):
        self.stream = stream

    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc, traceback):
        self.stream.write(b"libpng warning: noisy profile")
        return False


def indexed_png_without_plte():
    ihdr = (1).to_bytes(4, "big") + (1).to_bytes(4, "big") + b"\x08\x03\x00\x00\x00"
    return (
        PNG_SIGNATURE
        + build_png_chunk(b"IHDR", ihdr)
        + build_png_chunk(b"IDAT", zlib.compress(b"\x00\x00"))
        + IEND_CHUNK
    )


def write_temp_png(data):
    png_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    try:
        png_file.write(data)
        return Path(png_file.name)
    finally:
        png_file.close()


def test_chunk_stream_check_accepts_valid_png_fixture():
    assert libpng_check.chunk_stream_check_result(str(FIXTURE)) == ""


def test_chunk_stream_check_reports_invalid_png_stream():
    assert "libpng error:" in libpng_check.chunk_stream_check_result(str(ROOT / "missing.png"))


def test_structure_check_reports_missing_indexed_palette():
    png_file = write_temp_png(indexed_png_without_plte())
    try:
        assert libpng_check.structure_check_result(str(png_file)) == (
            "libpng error: Indexed-color PNG requires a PLTE chunk"
        )
    finally:
        png_file.unlink(missing_ok=True)


def test_pillow_check_result_uses_verify_success():
    assert libpng_check.pillow_check_result("sample.png", FakePillowOk) == ""


def test_pillow_check_result_reports_verify_error():
    assert libpng_check.pillow_check_result("sample.png", FakePillowError) == "libpng error: bad pixels"


def test_cv2_check_result_captures_stderr_redirector_output():
    assert (
        libpng_check.cv2_check_result("sample.png", FakeCv2, FakeRedirector)
        == "libpng warning: noisy profile"
    )


def test_append_known_bad_srgb_warning_adds_missing_warning_once():
    warning = "libpng warning: iCCP: known incorrect sRGB profile"

    assert libpng_check.append_known_bad_srgb_warning("", warning) == warning
    assert (
        libpng_check.append_known_bad_srgb_warning("libpng error: bad\n" + warning, warning)
        == "libpng error: bad\n" + warning
    )


def test_libpng_result_prefers_cv2_then_appends_known_warning():
    result = libpng_check.libpng_result(
        str(FIXTURE),
        cv2_module=FakeCv2,
        image_module=FakePillowError,
        stderr_redirector=FakeRedirector,
        warning_reader=lambda file: "libpng warning: iCCP: known incorrect sRGB profile",
    )

    assert result == (
        "libpng warning: noisy profile\n"
        "libpng warning: iCCP: known incorrect sRGB profile"
    )


def test_libpng_result_appends_structure_errors_after_pillow_success():
    png_file = write_temp_png(indexed_png_without_plte())
    try:
        assert libpng_check.libpng_result(
            str(png_file),
            image_module=FakePillowOk,
            warning_reader=lambda file: "",
        ) == "libpng error: Indexed-color PNG requires a PLTE chunk"
    finally:
        png_file.unlink(missing_ok=True)


def test_libpng_result_flags_unvalidated_blackfill_fixed_artifact():
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        png_file = folder / "sample.0_Fixed.png"
        png_file.write_bytes(FIXTURE.read_bytes())
        preview_folder = folder / "Bruteforce_Previews"
        preview_folder.mkdir()
        (preview_folder / "_Preview_IDAT_Blackfill_Preview.png").write_bytes(FIXTURE.read_bytes())

        result = libpng_check.libpng_result(
            str(png_file),
            image_module=FakePillowOk,
            warning_reader=lambda file: "",
        )

    assert "visual repair needs reference/ROI" in result


def test_libpng_result_flags_summary_marked_blackfill_fixed_artifact():
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        png_file = folder / "sample.0_Fixed.png"
        png_file.write_bytes(FIXTURE.read_bytes())
        (folder / "Summary_Of_sample").write_text(
            "FixItFelix: partial-idat-blackfill recovered 500/500 scanlines.",
            encoding="utf-8",
        )

        result = libpng_check.libpng_result(
            str(png_file),
            image_module=FakePillowOk,
            warning_reader=lambda file: "",
        )

    assert "visual repair needs reference/ROI" in result


def test_libpng_result_allows_validated_sbb_success_fixed_artifact():
    with tempfile.TemporaryDirectory() as directory:
        folder = Path(directory)
        png_file = folder / "sample.0_Fixed.png"
        png_file.write_bytes(FIXTURE.read_bytes())
        preview_folder = folder / "Bruteforce_Previews"
        preview_folder.mkdir()
        (preview_folder / "_Preview_IDAT_Blackfill_Preview.png").write_bytes(FIXTURE.read_bytes())
        (folder / "_SBB.progress.json").write_text('{"status": "success"}', encoding="utf-8")

        result = libpng_check.libpng_result(
            str(png_file),
            image_module=FakePillowOk,
            warning_reader=lambda file: "",
        )

    assert "visual repair needs reference/ROI" not in result


def test_result_has_error_uses_legacy_error_markers():
    errors = ["libpng error:", "libpng warning:"]

    assert libpng_check.result_has_error("", errors) is False
    assert libpng_check.result_has_error("all good", errors) is False
    assert libpng_check.result_has_error("libpng warning: noisy", errors) is True
    assert libpng_check.result_has_error("libpng error: broken", errors) is True


def test_checkpoint_args_preserve_success_and_error_call_shapes():
    errors = ["libpng error:", "libpng warning:"]

    assert libpng_check.checkpoint_args("sample.png", "", errors) == (
        False,
        False,
        "LibpngCheck",
        "sample.png",
        ["-Libpng dis not found any error"],
    )
    assert libpng_check.checkpoint_args("sample.png", "libpng error: bad", errors) == (
        True,
        False,
        "LibpngCheck",
        "sample.png",
        ["-libpng error: bad"],
    )


def main():
    checks = [
        ("Chunk stream accepts valid PNG", test_chunk_stream_check_accepts_valid_png_fixture),
        ("Chunk stream reports invalid PNG", test_chunk_stream_check_reports_invalid_png_stream),
        ("Structure check reports missing PLTE", test_structure_check_reports_missing_indexed_palette),
        ("Pillow verify success", test_pillow_check_result_uses_verify_success),
        ("Pillow verify error", test_pillow_check_result_reports_verify_error),
        ("cv2 stderr capture", test_cv2_check_result_captures_stderr_redirector_output),
        ("Append known sRGB warning", test_append_known_bad_srgb_warning_adds_missing_warning_once),
        ("Libpng result preference order", test_libpng_result_prefers_cv2_then_appends_known_warning),
        ("Libpng result appends structure errors", test_libpng_result_appends_structure_errors_after_pillow_success),
        ("Libpng result error markers", test_result_has_error_uses_legacy_error_markers),
        ("Libpng checkpoint args", test_checkpoint_args_preserve_success_and_error_call_shapes),
    ]

    print("Running libpng check tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"libpng check tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
