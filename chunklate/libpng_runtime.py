from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Callable

from . import libpng_check, stdio


@dataclass(frozen=True)
class LibpngCheckRuntime:
    candy: Callable
    emit: Callable
    checkpoint: Callable
    libpng_result: Callable = libpng_check.libpng_result
    result_has_error: Callable = libpng_check.result_has_error
    checkpoint_args: Callable = libpng_check.checkpoint_args


@dataclass(frozen=True)
class LibpngCheckContext:
    sample_name: str
    libpng_errors: Sequence[str]
    cv2_module: Any = None
    image_module: Any = None
    stderr_redirector: Callable = stdio.stderr_redirector
    warning_reader: Callable = libpng_check.known_bad_srgb_profile_warning_for_file


def run_known_bad_srgb_profile_warning(
    file: str,
    *,
    warning_reader: Callable = libpng_check.known_bad_srgb_profile_warning_for_file,
) -> str:
    return warning_reader(file)


def run_libpng_check(
    runtime: LibpngCheckRuntime,
    context: LibpngCheckContext,
    file: str,
):
    runtime.candy(
        "Title",
        "Libpng Returned :%s" % (runtime.candy("Color", "white", context.sample_name)),
    )
    result = runtime.libpng_result(
        file,
        cv2_module=context.cv2_module,
        image_module=context.image_module,
        stderr_redirector=context.stderr_redirector,
        warning_reader=context.warning_reader,
    )
    runtime.emit("Result:%s" % result)

    if not runtime.result_has_error(result, context.libpng_errors):
        runtime.emit(
            "-Libpng Check: %s %s"
            % (runtime.candy("Color", "green", "Ok!"), runtime.candy("Chunky", "good"))
        )
        runtime.candy(
            "Cowsay",
            "Good ! The AllMighty Libpng is happy !",
            "good",
        )
    else:
        runtime.emit(
            "-Libpng Check: %s %s"
            % (runtime.candy("Color", "red", "FAILED!"), runtime.candy("Chunky", "bad"))
        )

    return runtime.checkpoint(
        *runtime.checkpoint_args(file, result, context.libpng_errors)
    )
