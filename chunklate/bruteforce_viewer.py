from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any
import io

from . import bruteforce, decisions


LegacyCall = Callable[..., Any]


@dataclass(frozen=True)
class BruteForceViewerRuntime:
    data_hex: str
    data_offset: int
    libpng_errors: tuple[str, ...]
    tmp_image_paths: list[str]
    cv2: Any
    numpy: Any
    image: Any
    psutil: Any
    stderr_redirector: LegacyCall
    sleep: LegacyCall
    ask_timeout: LegacyCall
    naming: LegacyCall
    file_origin: str
    emit: LegacyCall
    candy: LegacyCall
    summarise: LegacyCall
    save_error: LegacyCall
    end: LegacyCall
    raw_print: LegacyCall = print
    debug: bool = False


@dataclass(frozen=True)
class BruteForceViewerResult:
    accepted: bool
    diff: str = ""


def libpng_probe(runtime: BruteForceViewerRuntime, png_bytes: bytes) -> str:
    stream = io.BytesIO()
    with runtime.stderr_redirector(stream):
        try:
            runtime.cv2.imdecode(runtime.numpy.frombuffer(png_bytes, runtime.numpy.uint8), -1)
        except Exception:
            pass
    return "{0}".format(stream.getvalue().decode("utf-8"))


def open_and_show_candidate(
    runtime: BruteForceViewerRuntime,
    png_bytes: bytes,
    candidate_bytes: bytes,
    debug_bytes: bytes | None = None,
):
    stream = io.BytesIO()
    tmp_image = None
    tmp_width = 0
    tmp_height = 0

    with runtime.stderr_redirector(stream):
        try:
            tmp_image = runtime.image.open(io.BytesIO(png_bytes))
            tmp_width, tmp_height = tmp_image.size
            tmp_image.show()
        except Exception as exc:
            if bruteforce.has_libpng_error(str(exc), runtime.libpng_errors):
                if tmp_image is not None and tmp_image.mode != "RGB":
                    tmp_image = tmp_image.convert("RGB")
                    tmp_width, tmp_height = tmp_image.size
                    tmp_image.show()
            elif runtime.debug:
                runtime.raw_print(
                    "bvalue:%s ndx:%s error:%s immode:%s"
                    % (
                        (debug_bytes or candidate_bytes).hex(),
                        candidate_bytes.hex(),
                        str(exc),
                        getattr(tmp_image, "mode", None),
                    ),
                    end="\r",
                )

    return tmp_image, tmp_width, tmp_height


def save_timeout_candidate(
    runtime: BruteForceViewerRuntime,
    tmp_image: Any,
    tmp_width: int,
    tmp_height: int,
    try_number: int,
) -> None:
    name, directory = runtime.naming(runtime.file_origin)
    runtime.emit("\n-Skipped No input given within time limit.\n")
    save_result = bruteforce.save_viewer_timeout_image(
        tmp_image.save,
        directory,
        name,
        tmp_width,
        tmp_height,
        datetime.now().strftime("-%y%m%d%H%M%S-"),
        try_number,
    )
    if save_result.saved:
        runtime.candy(
            "Cowsay",
            "I took the liberty to save a copy of that image just in case.",
            "com",
        )
        runtime.emit("-Image saved at:%s\n" % save_result.path)
        runtime.tmp_image_paths.append(save_result.path)
        runtime.summarise(save_result.summary)
    else:
        runtime.save_error(save_result.error, "ShowPng")
        runtime.emit(
            runtime.candy("Color", "red", "Error:%s")
            % runtime.candy("Color", "yellow", save_result.error)
        )
        runtime.summarise(save_result.summary)


def handle_user_timeout_or_crash(
    runtime: BruteForceViewerRuntime,
    exc: Exception,
    tmp_image: Any,
    tmp_width: int,
    tmp_height: int,
    try_number: int,
) -> bool:
    if isinstance(exc, EOFError):
        runtime.raw_print(exc)
        runtime.candy("Cowsay", "Aouch my head ...Didn't see that one coming..", "bad")
        runtime.candy("Cowsay", "Please close this terminal and open it again.", "com")
        runtime.candy("Cowsay", "Then Launch Chunklate again like you did before,", "com")
        runtime.candy(
            "Cowsay",
            "But add --crash %s at the end of the argument." % str(try_number),
            "com",
        )
        runtime.candy("Cowsay", "And Everything would be fine i think!", "good")
        runtime.end()
        return False

    save_timeout_candidate(runtime, tmp_image, tmp_width, tmp_height, try_number)
    return False


def show_candidate(
    runtime: BruteForceViewerRuntime,
    png_bytes: bytes,
    candidate_bytes: bytes,
    loop_index: int,
    debug_bytes: bytes | None = None,
) -> BruteForceViewerResult:
    probe_result = libpng_probe(runtime, png_bytes)
    viewer_candidate = bruteforce.viewer_candidate_decision(
        probe_result,
        runtime.libpng_errors,
    )
    if not viewer_candidate.acceptable:
        return BruteForceViewerResult(False)

    tmp_image, tmp_width, tmp_height = open_and_show_candidate(
        runtime,
        png_bytes,
        candidate_bytes,
        debug_bytes,
    )
    runtime.emit("")
    runtime.emit("-Waiting for Image viewer to launch.")
    bruteforce.wait_for_tmp_png_viewer(runtime.psutil.process_iter, runtime.sleep)

    runtime.candy("Cowsay", "Ah ! Iv got One !", "good")
    try_number = bruteforce.viewer_try_number(loop_index)
    runtime.emit("-Tmp Image Number %s" % str(try_number))
    runtime.emit("-Tmp Image Width: %s" % tmp_width)
    runtime.emit("-Tmp Image Height: %s" % tmp_height)
    runtime.summarise(
        bruteforce.viewer_found_summary(
            try_number,
            tmp_width,
            tmp_height,
            datetime.now().strftime("%y-%m-%d:%H:%M:%S"),
        )
    )
    runtime.emit("")
    runtime.candy("Cowsay", "Does it looks good or should i keep trying ?", "com")

    try:
        answer = decisions.ask_yes_no(
            lambda prompt: runtime.ask_timeout(prompt=prompt, timeout=23),
            "Answer(yes/no) auto answer in 23s:",
        )
        runtime.summarise(bruteforce.viewer_user_choice_summary(answer, try_number))
    except Exception as exc:
        answer = handle_user_timeout_or_crash(
            runtime,
            exc,
            tmp_image,
            tmp_width,
            tmp_height,
            try_number,
        )

    if answer is True:
        diff = bruteforce.accepted_candidate_diff(
            runtime.data_hex,
            runtime.data_offset,
            candidate_bytes,
        )
        return BruteForceViewerResult(True, diff)

    bruteforce.kill_tmp_png_viewers(runtime.psutil.process_iter())
    runtime.candy("Cowsay", "Ok back to work..", "bad")
    return BruteForceViewerResult(False)
