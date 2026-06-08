from __future__ import annotations

import json
from pathlib import Path
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


def blackfill_artifact_check_result(file: str) -> str:
    path = Path(file)
    if "_Fixed" not in path.name:
        return ""
    preview_marker = path.parent / "Bruteforce_Previews" / "_Preview_IDAT_Blackfill_Preview.png"
    summary_marked_blackfill = False
    for summary_path in path.parent.glob("Summary_Of_*"):
        try:
            summary_text = summary_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "partial-idat-blackfill" in summary_text or "IDAT_Blackfill_Preview" in summary_text:
            summary_marked_blackfill = True
            break
    if not preview_marker.exists() and not summary_marked_blackfill:
        return ""

    progress_path = path.parent / "_SBB.progress.json"
    try:
        progress = json.loads(progress_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        progress = {}
    if isinstance(progress, dict) and str(progress.get("status") or "") == "success":
        return ""
    return "libpng error: visual repair needs reference/ROI before accepting blackfill artifact"


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
    artifact_checker: StructureChecker = blackfill_artifact_check_result,
) -> str:
    if cv2_module is not None:
        result = cv2_check_result(file, cv2_module, stderr_redirector)
    elif image_module is not None:
        result = pillow_check_result(file, image_module)
    else:
        result = chunk_stream_check_result(file)

    result = append_structure_check_result(result, structure_checker(file))
    result = append_structure_check_result(result, artifact_checker(file))
    return append_known_bad_srgb_warning(result, warning_reader(file))
