#!/usr/bin/env python3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chunklate import libpng_runtime


def build_runtime(calls, *, result):
    def candy(kind, *args):
        calls.append(("candy", (kind,) + args))
        if kind == "Color":
            return "<%s:%s>" % (args[0], args[1])
        if kind == "Emoj":
            return "<emoj:%s>" % args[0]
        return "candy:%s" % kind

    return libpng_runtime.LibpngCheckRuntime(
        candy=candy,
        emit=lambda message: calls.append(("emit", message)),
        checkpoint=lambda *args: calls.append(("checkpoint", args)) or "checkpoint-result",
        libpng_result=lambda file, **kwargs: calls.append(("libpng_result", file, kwargs)) or result,
    )


def context(**updates):
    values = {
        "sample_name": "sample.png",
        "libpng_errors": ("libpng error:", "libpng warning:"),
        "cv2_module": "cv2",
        "image_module": "image",
        "stderr_redirector": "stderr",
        "warning_reader": "warning-reader",
    }
    values.update(updates)
    return libpng_runtime.LibpngCheckContext(**values)


def test_run_libpng_check_reports_success_and_checkpoints():
    calls = []

    result = libpng_runtime.run_libpng_check(
        build_runtime(calls, result=""),
        context(),
        "sample.png",
    )

    assert result == "checkpoint-result"
    assert ("emit", "Result:") in calls
    assert ("emit", "-Libpng Check: <green:Ok!> <emoj:good>") in calls
    assert ("candy", ("Cowsay", "Good ! The AllMighty Libpng is happy !", "good")) in calls
    assert (
        "checkpoint",
        (False, False, "LibpngCheck", "sample.png", ["-Libpng dis not found any error"]),
    ) in calls


def test_run_libpng_check_reports_failure_and_checkpoints():
    calls = []

    result = libpng_runtime.run_libpng_check(
        build_runtime(calls, result="libpng error: bad"),
        context(),
        "sample.png",
    )

    assert result == "checkpoint-result"
    assert ("emit", "Result:libpng error: bad") in calls
    assert ("emit", "-Libpng Check: <red:FAILED!> <emoj:bad>") in calls
    assert (
        "checkpoint",
        (True, False, "LibpngCheck", "sample.png", ["-libpng error: bad"]),
    ) in calls


def test_run_libpng_check_passes_modules_to_result_reader():
    calls = []

    libpng_runtime.run_libpng_check(
        build_runtime(calls, result=""),
        context(),
        "sample.png",
    )

    assert calls[2] == (
        "libpng_result",
        "sample.png",
        {
            "cv2_module": "cv2",
            "image_module": "image",
            "stderr_redirector": "stderr",
            "warning_reader": "warning-reader",
        },
    )


def test_run_known_bad_srgb_profile_warning_delegates_reader():
    assert (
        libpng_runtime.run_known_bad_srgb_profile_warning(
            "sample.png",
            warning_reader=lambda file: "warning for " + file,
        )
        == "warning for sample.png"
    )


def main():
    checks = [
        ("Libpng success", test_run_libpng_check_reports_success_and_checkpoints),
        ("Libpng failure", test_run_libpng_check_reports_failure_and_checkpoints),
        ("Libpng reader kwargs", test_run_libpng_check_passes_modules_to_result_reader),
        ("Known bad sRGB warning", test_run_known_bad_srgb_profile_warning_delegates_reader),
    ]

    print("Running libpng runtime tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"libpng runtime tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
