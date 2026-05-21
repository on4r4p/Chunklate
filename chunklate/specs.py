from __future__ import annotations

import itertools
from typing import Any


VALID_IHDR_COLOR_TYPES = ("0", "2", "3", "4", "6")


def min_res_iter(min_res: int) -> int:
    count = 0
    for width in range(1, min_res):
        for _height in range(1, width + 1):
            count += 2
    return count


def iter_product_values(chunk_data: Any, color_type: str):
    for candidate in itertools.product(*chunk_data):
        if color_type.endswith("minres"):
            for width in range(1, candidate[0] + 1):
                width_first = tuple([candidate[0]] + [width] + list(candidate[1:]))
                yield width_first
                height_first = tuple([width] + [candidate[0]] + list(candidate[1:]))
                if height_first != width_first:
                    yield height_first
        else:
            yield candidate


def ihdr_state_is_safe(
    pandora_box: dict[Any, Any],
    cornucopia: dict[Any, Any],
    pandemonium: dict[Any, Any],
    allchunks: list[bytes] | tuple[bytes, ...],
    ihdr_color: Any,
    ihdr_height: int,
    ihdr_width: int,
    skip_bad_crc: bool,
) -> tuple[bool, bool]:
    safe_value = True
    width_unknown = False
    height_unknown = False

    for key in pandora_box:
        if "IHDR" in str(key):
            if "Wrong Crc" in str(key) and skip_bad_crc is False:
                if str(key) not in cornucopia:
                    safe_value = False
            if "bad adaptive filter" in str(key):
                if str(key) not in cornucopia:
                    safe_value = False
            if "-IHDR Color" in str(key):
                if str(key) not in cornucopia:
                    safe_value = False
            if "IHDR: CRC error" in str(key):
                if str(key) not in cornucopia:
                    safe_value = False
            if "StructIndex:0" in str(key):
                width_unknown = True
            if "StructIndex:1" in str(key):
                height_unknown = True

    use_min_res = width_unknown and height_unknown

    for _file, file_value in pandemonium.items():
        for errors, errors_values in file_value.items():
            if "Filling with a dummy chunk" in errors:
                for tools, _tools_values in errors_values.items():
                    chunk_name = "".join(
                        [
                            chunk.decode(errors="ignore")
                            for chunk in allchunks
                            if chunk.decode(errors="ignore") in tools
                        ]
                    )
                    if chunk_name == "IHDR":
                        safe_value = False

    if ihdr_color not in VALID_IHDR_COLOR_TYPES:
        safe_value = False

    if ihdr_height == 0 or ihdr_width == 0:
        safe_value = False

    return safe_value, use_min_res


def color_type_label(
    get_chunk: bytes,
    mode: str,
    brute_level: int,
    ihdr_color: Any,
    ihdr_height: int,
    ihdr_width: int,
    pandora_box: dict[Any, Any],
    cornucopia: dict[Any, Any],
    pandemonium: dict[Any, Any],
    allchunks: list[bytes] | tuple[bytes, ...],
    skip_bad_crc: bool,
) -> str:
    safe_value, use_min_res = ihdr_state_is_safe(
        pandora_box,
        cornucopia,
        pandemonium,
        allchunks,
        ihdr_color,
        ihdr_height,
        ihdr_width,
        skip_bad_crc,
    )

    if safe_value is False:
        if get_chunk == b"IHDR":
            if brute_level == 0:
                if mode == "Custom" and not use_min_res:
                    return "nocolortype:minres:custom"
                return "nocolortype:minres"
            if brute_level == 1:
                return "nocolortype:medres"
            return "nocolortype:maxres"
        return "nocolortype"

    if brute_level == 0:
        if mode == "Custom" and not use_min_res:
            return "colortype:" + str(ihdr_color) + ":minres:custom"
        return "colortype:" + str(ihdr_color) + ":minres"
    if brute_level == 1:
        return "colortype:" + str(ihdr_color) + ":medres"
    return "colortype:" + str(ihdr_color) + ":maxres"
