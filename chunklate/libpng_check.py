from __future__ import annotations

from typing import Any, Callable
import io

from . import stdio
from .png import PngFormatError, iter_chunks, known_bad_srgb_profile_warning, validate_png_structure


WarningReader = Callable[[str], str]
StructureChecker = Callable[[str], str]


def cv2_check_result(file: str, cv2_module: Any, stderr_redirector=stdio.stderr_redirector) -> str:
    stream = io.BytesIO()
    with stderr_redirector(stream):
        cv2_module.imread(file)
    return "{0}".format(stream.getvalue().decode("utf-8"))


def pillow_check_result(file: str, image_module: Any) -> str:
    try:
        with image_module.open(file) as img:
            img.verify()
        return ""
    except Exception as e:
        return "libpng error: %s" % e


def chunk_stream_check_result(file: str) -> str:
    try:
        with open(file, "rb") as png_file:
            chunks = list(iter_chunks(png_file.read()))
        if not chunks or chunks[-1].chunk_type != b"IEND" or not all(chunk.crc_ok for chunk in chunks):
            return "libpng error: invalid PNG chunk stream"
        return ""
    except (OSError, PngFormatError) as e:
        return "libpng error: %s" % e


def structure_check_result(file: str) -> str:
    try:
        with open(file, "rb") as png_file:
            validation = validate_png_structure(png_file.read())
    except OSError as e:
        return "libpng error: %s" % e

    if validation.errors:
        return "libpng error: %s" % "; ".join(validation.errors)
    return ""


def known_bad_srgb_profile_warning_for_file(file: str) -> str:
    try:
        with open(file, "rb") as png_file:
            return known_bad_srgb_profile_warning(png_file.read())
    except OSError:
        return ""


def append_known_bad_srgb_warning(result: str, warning: str) -> str:
    if warning and "known incorrect sRGB profile" not in result:
        return (result + "\n" if result else "") + warning
    return result


def append_structure_check_result(result: str, structural_result: str) -> str:
    if structural_result and structural_result not in result:
        return (result + "\n" if result else "") + structural_result
    return result


def result_has_error(result: str, libpng_errors: tuple[str, ...] | list[str]) -> bool:
    return any(error in result for error in libpng_errors)


def checkpoint_args(
    file: str,
    result: str,
    libpng_errors: tuple[str, ...] | list[str],
) -> tuple[object, ...]:
    if result_has_error(result, libpng_errors):
        return (True, False, "LibpngCheck", file, ["-" + result])
    return (
        False,
        False,
        "LibpngCheck",
        file,
        ["-Libpng dis not found any error"],
    )


def libpng_result(
    file: str,
    *,
    cv2_module: Any = None,
    image_module: Any = None,
    stderr_redirector=stdio.stderr_redirector,
    warning_reader: WarningReader = known_bad_srgb_profile_warning_for_file,
    structure_checker: StructureChecker = structure_check_result,
) -> str:
    if cv2_module is not None:
        result = cv2_check_result(file, cv2_module, stderr_redirector)
    elif image_module is not None:
        result = pillow_check_result(file, image_module)
    else:
        result = chunk_stream_check_result(file)

    result = append_structure_check_result(result, structure_checker(file))
    return append_known_bad_srgb_warning(result, warning_reader(file))
