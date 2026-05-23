#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import libpng_check


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


def test_chunk_stream_check_accepts_valid_png_fixture():
    assert libpng_check.chunk_stream_check_result(str(FIXTURE)) == ""


def test_chunk_stream_check_reports_invalid_png_stream():
    assert "libpng error:" in libpng_check.chunk_stream_check_result(str(ROOT / "missing.png"))


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
        "sample.png",
        cv2_module=FakeCv2,
        image_module=FakePillowError,
        stderr_redirector=FakeRedirector,
        warning_reader=lambda file: "libpng warning: iCCP: known incorrect sRGB profile",
    )

    assert result == (
        "libpng warning: noisy profile\n"
        "libpng warning: iCCP: known incorrect sRGB profile"
    )


def main():
    checks = [
        ("Chunk stream accepts valid PNG", test_chunk_stream_check_accepts_valid_png_fixture),
        ("Chunk stream reports invalid PNG", test_chunk_stream_check_reports_invalid_png_stream),
        ("Pillow verify success", test_pillow_check_result_uses_verify_success),
        ("Pillow verify error", test_pillow_check_result_reports_verify_error),
        ("cv2 stderr capture", test_cv2_check_result_captures_stderr_redirector_output),
        ("Append known sRGB warning", test_append_known_bad_srgb_warning_adds_missing_warning_once),
        ("Libpng result preference order", test_libpng_result_prefers_cv2_then_appends_known_warning),
    ]

    print("Running libpng check tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"libpng check tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
