from __future__ import annotations

import itertools
import math
import os
from typing import Any


VALID_IHDR_COLOR_TYPES = ("0", "2", "3", "4", "6")
MINIMAL_CHUNKS = (b"PNG", b"IHDR", b"IDAT", b"IEND")
CRITICAL_CHUNKS = (b"PNG", b"IHDR", b"PLTE", b"IDAT", b"IEND")
CHUNKS = (
    b"sBIT",
    b"IEND",
    b"sPLT",
    b"tRNS",
    b"fRAc",
    b"hIST",
    b"dSIG",
    b"sTER",
    b"iCCP",
    b"sRGB",
    b"zTXt",
    b"gAMA",
    b"IDAT",
    b"sCAL",
    b"cHRM",
    b"bKGD",
    b"tEXt",
    b"tIME",
    b"iTXt",
    b"IHDR",
    b"gIFx",
    b"gIFg",
    b"oFFs",
    b"pCAL",
    b"PLTE",
    b"gIFt",
    b"pHYs",
    b"eXIf",
)
PRIVATE_CHUNKS = (
    b"cmOD",
    b"cmPP",
    b"cpIp",
    b"mkBF",
    b"mkBS",
    b"mkBT",
    b"mkTS",
    b"spAL",
    b"pcLb",
    b"prVW",
    b"JDAT",
    b"JSEP",
    b"DHDR",
    b"FRAM",
    b"SAVE",
    b"SEEK",
    b"nEED",
    b"DEFI",
    b"BACK",
    b"MOVE",
    b"CLON",
    b"SHOW",
    b"CLIP",
    b"LOOP",
    b"ENDL",
    b"PROM",
    b"fPRI",
    b"eXPI",
    b"BASI",
    b"IPNG",
    b"PPLT",
    b"PAST",
    b"TERM",
    b"DISC",
    b"pHYg",
    b"DROP",
    b"DBYK",
    b"ORDR",
    b"MAGN",
    b"MEND",
)
BEFORE_PLTE = (b"PNG", b"IHDR", b"gAMA", b"cHRM", b"iCCP", b"sRGB", b"sBIT")
AFTER_PLTE = (b"tRNS", b"hIST", b"bKGD")
BEFORE_IDAT = (
    b"PNG",
    b"sPLT",
    b"sBIT",
    b"pHYs",
    b"tRNS",
    b"hIST",
    b"gAMA",
    b"iCCP",
    b"sRGB",
    b"cHRM",
    b"PLTE",
    b"IHDR",
    b"bKGD",
)
BEFORE_IDAT2 = (
    b"IHDR",
    b"sPLT",
    b"sBIT",
    b"pHYs",
    b"tRNS",
    b"hIST",
    b"gAMA",
    b"iCCP",
    b"sRGB",
    b"cHRM",
    b"PLTE",
    b"bKGD",
)
UNIQUE_CHUNK = (
    b"PNG",
    b"sBIT",
    b"IEND",
    b"tRNS",
    b"hIST",
    b"sTER",
    b"iCCP",
    b"sRGB",
    b"gAMA",
    b"sCAL",
    b"cHRM",
    b"bKGD",
    b"IHDR",
    b"oFFs",
    b"pCAL",
    b"PLTE",
    b"pHYs",
    b"IEND",
    b"eXIf",
)
NO_ORDER_CHUNKS = (b"tIME", b"tEXt", b"zTXt", b"iTXt", b"fRAc", b"gIFg", b"gIFx", b"gIFt")
CHUNKS_LEN_NOT_FIXED = (b"PLTE", b"tRNS", b"hIST")
ALLCHUNKS = CHUNKS + PRIVATE_CHUNKS
LIBPNG_ERR = (
    "libpng error:",
    "Too much image data",
    "Out of memory",
    " in PLTE",
    "Invalid palette",
    " in IDAT",
    "is too large for this architecture",
    " in IHDR",
    "bad result",
    "conversion not supported",
    "known incorrect sRGB profile",
)


def min_res_iter(min_res: int) -> int:
    count = 0
    for width in range(1, min_res):
        for _height in range(1, width + 1):
            count += 2
    return count


def estimate_max_resolution(file_size: int) -> int:
    if file_size < 77:
        calc = math.floor(((file_size) * 8 - 1) / 2) * 86 + 1
    else:
        calc = math.floor(((file_size - 77) * 8 - 1) / 2) * 86 + 1
    return int(math.sqrt(calc))


def estimate_max_resolution_from_file(file_path: str) -> tuple[int, int]:
    file_size = os.path.getsize(file_path)
    return estimate_max_resolution(file_size), file_size


def resolution_iteration_bounds(idat_byte_count: int, color_type_label: str) -> tuple[int, int]:
    min_resolution = int(idat_byte_count / 64)
    if min_resolution > 10000:
        min_resolution = int(min_resolution / 2)
    if color_type_label.endswith(":minres"):
        return min_resolution, min_res_iter(min_resolution)
    return min_resolution, min_resolution * min_resolution


def estimate_idat_bytes_from_hex(data_hex: str, known_chunks: tuple[bytes, ...] = CHUNKS) -> int:
    byte_count = 0
    last_byte_count = 0
    needle = 0
    idat_switch = False
    enough = False

    while needle < len(data_hex):
        scope_hex = data_hex[needle : needle + 8]
        if len(scope_hex) < 8:
            break
        if enough:
            break

        try:
            scope = bytes.fromhex(scope_hex)
        except ValueError:
            needle += 1
            continue

        if scope == b"IDAT":
            idat_switch = True
            if last_byte_count == 0:
                last_byte_count = needle
            else:
                byte_count += (needle - last_byte_count) - 24
                last_byte_count = needle
        elif idat_switch:
            for chunk in known_chunks:
                if chunk == scope:
                    byte_count += (needle - last_byte_count) - 24
                    last_byte_count = needle
                    enough = True
                    break
        needle += 1

    return int(byte_count / 2)


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
