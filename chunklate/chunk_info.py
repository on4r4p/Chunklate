from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from typing import Any
import zlib


PHYS_MAX_PIXELS_PER_UNIT = 2147483647
IHDR_MAX_DIMENSION = 2147483647
IHDR_VALID_DEPTHS = ("1", "2", "4", "8", "16")
IHDR_VALID_COLOR_TYPES = ("0", "2", "3", "4", "6")
OFFS_MIN_POSITION = -2147483647
OFFS_MAX_POSITION = 2147483647
OFFS_PARSE_FALLBACK = "2147483649"
SRGB_RENDERING_INTENTS = {
    "0": "Perceptual",
    "1": "Relative colorimetric",
    "2": "Saturation",
    "3": "Absolute colorimetric",
}
BKGD_EXPECTED_HEX_LENGTH = {
    "0": 4,
    "4": 4,
    "2": 12,
    "6": 12,
    "3": 2,
}


@dataclass(frozen=True)
class GamaInfo:
    value: str = ""
    fixes: tuple[str, ...] = ()


@dataclass(frozen=True)
class PhysInfo:
    y: str = ""
    x: str = ""
    unit: str = ""
    fixes: tuple[str, ...] = ()


@dataclass(frozen=True)
class TimeInfo:
    year: str = ""
    month: str = ""
    day: str = ""
    hour: str = ""
    minute: str = ""
    second: str = ""
    parse_fixes: tuple[str, ...] = ()
    validation_fixes: tuple[str, ...] = ()

    @property
    def fixes(self) -> tuple[str, ...]:
        return self.parse_fixes + self.validation_fixes

    @property
    def can_print_timestamp(self) -> bool:
        return len(self.parse_fixes) == 0


@dataclass(frozen=True)
class SterInfo:
    mode: str = ""
    fixes: tuple[str, ...] = ()


@dataclass(frozen=True)
class SrgbInfo:
    value: str = ""
    fixes: tuple[str, ...] = ()


@dataclass(frozen=True)
class OffsInfo:
    x: str = OFFS_PARSE_FALLBACK
    y: str = OFFS_PARSE_FALLBACK
    unit: str = OFFS_PARSE_FALLBACK
    fixes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ChrmInfo:
    white_x: str = ""
    white_y: str = ""
    red_x: str = ""
    red_y: str = ""
    green_x: str = ""
    green_y: str = ""
    blue_x: str = ""
    blue_y: str = ""
    fixes: tuple[str, ...] = ()


@dataclass(frozen=True)
class GifgInfo:
    disposal_method: str = ""
    user_input_flag: str = ""
    delay_time: str = ""
    fixes: tuple[str, ...] = ()


@dataclass(frozen=True)
class GifxInfo:
    application_identifier: str = ""
    authentication_code: str = ""
    application_data: str = ""
    fixes: tuple[str, ...] = ()


@dataclass(frozen=True)
class IccpInfo:
    name: str = ""
    method: int | str = ""
    profile: str = ""
    null_pos: int = 0
    bad_chars: tuple[tuple[str, int], ...] = ()
    fixes: tuple[Any, ...] = ()


@dataclass(frozen=True)
class ExifInfo:
    endian: str = ""
    raw_values: tuple[str, ...] = ()
    fixes: tuple[str, ...] = ()


@dataclass(frozen=True)
class IhdrInfo:
    width: str = ""
    height: str = ""
    depth: str = ""
    color: str = ""
    method: str = ""
    filter_method: str = ""
    interlace: str = ""
    fixes: tuple[str, ...] = ()


@dataclass(frozen=True)
class BkgdInfo:
    gray: str = ""
    red: str = ""
    green: str = ""
    blue: str = ""
    index: str = ""
    fixes: tuple[str, ...] = ()


@dataclass(frozen=True)
class HistInfo:
    entries: tuple[str, ...] = ()
    fixes: tuple[str, ...] = ()


@dataclass(frozen=True)
class TrnsInfo:
    gray: str = ""
    true_r: str = ""
    true_g: str = ""
    true_b: str = ""
    indexes: tuple[str, ...] = ()
    fixes: tuple[str, ...] = ()


@dataclass(frozen=True)
class SbitInfo:
    gray: str = ""
    true_r: str = ""
    true_g: str = ""
    true_b: str = ""
    gray_scale: str = ""
    gray_alpha: str = ""
    true_alpha_r: str = ""
    true_alpha_g: str = ""
    true_alpha_b: str = ""
    true_alpha: str = ""
    fixes: tuple[str, ...] = ()


@dataclass(frozen=True)
class PlteInfo:
    red: tuple[str, ...] = ()
    green: tuple[str, ...] = ()
    blue: tuple[str, ...] = ()
    fixes: tuple[str, ...] = ()


@dataclass(frozen=True)
class SpltInfo:
    name: str = ""
    decoded_name: str = ""
    depth: str = ""
    red: tuple[str, ...] = ()
    green: tuple[str, ...] = ()
    blue: tuple[str, ...] = ()
    alpha: tuple[str, ...] = ()
    freq: tuple[str, ...] = ()
    bad_chars: tuple[tuple[str, int], ...] = ()
    fixes: tuple[Any, ...] = ()


@dataclass(frozen=True)
class TextInfo:
    keyword: str = ""
    text: str = ""
    decoded_keyword: str = ""
    decoded_text: str = ""
    fixes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ZtxtInfo:
    keyword: str = ""
    text: bytes = b""
    decoded_keyword: str = ""
    decoded_text: str = ""
    fixes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ItxtInfo:
    keyword: str = ""
    text: str = ""
    compression_flag: str = ""
    compression_method: str = ""
    language: str = ""
    translated_keyword: str = ""
    decoded_keyword: str = ""
    decoded_language: str = ""
    decoded_translated_keyword: str = ""
    fixes: tuple[str, ...] = ()


@dataclass(frozen=True)
class IdatInfo:
    raw_length: int = 0
    length_history: tuple[int, ...] = ()
    average_length: int | str = ""
    bytes_len: int = 0
    datastream: str = ""
    counter: int = 0
    fixes: tuple[str, ...] = ()


@dataclass(frozen=True)
class PcalInfo:
    keyword: str = ""
    decoded_keyword: str = ""
    zero: str = ""
    maximum: str = ""
    equation: str = ""
    parameter_count: str = ""
    unit: bytes | str = ""
    parameters: tuple[str, ...] = ()
    fixes: tuple[str, ...] = ()


@dataclass(frozen=True)
class SpalInfo:
    message: str = "-intermediate sPLT test version"
    fixes: tuple[str, ...] = ()


def _hex_int_text(data: str, start: int, end: int) -> str:
    return str(int(data[start:end], 16))


def _unsigned_hex_int_text(data: str, start: int, end: int) -> str:
    return str(int.from_bytes(bytes.fromhex(data[start:end]), byteorder="big", signed=False))


def _signed_hex_int_text(data: str, start: int, end: int) -> str:
    return str(int.from_bytes(bytes.fromhex(data[start:end]), byteorder="big", signed=True))


def _parse_ihdr_field(
    data: str,
    start: int,
    end: int,
    error_prefix: str,
    struct_index: int,
) -> tuple[str, str | None]:
    try:
        return _hex_int_text(data, start, end), None
    except (NameError, ValueError) as exc:
        return "", f"-Error IHDR {error_prefix}:{str(exc)} StructIndex:{struct_index}"


def _find_hex_separator(data: str, search4: str = "00") -> int | None:
    for index in range(0, len(data), len(search4)):
        if data[index : index + len(search4)] == search4:
            return index
    return None


def _decode_hex_text(data: str, errors: str = "replace") -> str:
    return bytes.fromhex(data).decode(errors=errors)


def _keyword_bad_char_fixes(data: str, chunk_name: str) -> list[str]:
    fixes: list[str] = []
    for index in range(0, len(data), 2):
        value = int(data[index : index + 2], 16)
        if value not in range(32, 127) and value not in range(161, 256):
            if data[index : index + 2] != "00" and data[index : index + 2] != "0a":
                fixes.append(
                    "-Character not allowed %s at index %s in %s Keyword "
                    "(must be between 32-126 and 161-255 but is %s)"
                    % (data[index : index + 2], index, chunk_name, value)
                )
    return fixes


def _keyword_length_fixes(keyword: str, chunk_name: str) -> list[str]:
    byte_length = len(keyword) // 2
    if 1 <= byte_length <= 79:
        return []
    return ["-%s Keyword length is not Valid :%s" % (chunk_name, len(keyword))]


def parse_ihdr(data: str, max_resolution: int | None = None) -> IhdrInfo:
    fixes: list[str] = []
    width, error = _parse_ihdr_field(data, 0, 8, "Height", 1)
    if error is not None:
        fixes.append(error)

    height, error = _parse_ihdr_field(data, 8, 16, "Width", 0)
    if error is not None:
        fixes.append(error)

    depth, error = _parse_ihdr_field(data, 16, 18, "Depht", 2)
    if error is not None:
        fixes.append(error)

    color, error = _parse_ihdr_field(data, 18, 20, "Color", 3)
    if error is not None:
        fixes.append(error)

    method, error = _parse_ihdr_field(data, 20, 22, "Method", 4)
    if error is not None:
        fixes.append(error)

    filter_method, error = _parse_ihdr_field(data, 22, 24, "Filter", 5)
    if error is not None:
        fixes.append(error)

    interlace, error = _parse_ihdr_field(data, 24, 26, "Interlace", 6)
    if error is not None:
        fixes.append(error)

    if len(data) != 26:
        fixes.append("-IHDR size have to always be 13 bytes")

    if len(height) > 0:
        if int(height) > IHDR_MAX_DIMENSION or int(height) < 1:
            fixes.append("-IHDR Height Must be between 1 to 2147483647. StructIndex:1")
        if max_resolution is not None:
            if int(height) > (max_resolution * 2):
                fixes.append(
                    "-IHDR Height Error %s Above estimated max resolution(*2):%s. StructIndex:1"
                    % (height, max_resolution * 2)
                )
            elif int(height) > max_resolution:
                fixes.append(
                    "-IHDR Height Warning %s Above estimated max resolution:%s. StructIndex:1"
                    % (height, max_resolution)
                )
    else:
        fixes.append("-Height is empty. StructIndex:1")

    if len(width) > 0:
        if int(width) > IHDR_MAX_DIMENSION or int(width) < 1:
            fixes.append("-IHDR Width Must be between 1 to 2147483647. StructIndex:0")
        if max_resolution is not None:
            if int(width) > (max_resolution * 2):
                fixes.append(
                    "-IHDR Width Error %s Above estimated max resolution(*2):%s. StructIndex:0"
                    % (width, max_resolution * 2)
                )
            elif int(width) > max_resolution:
                fixes.append(
                    "-IHDR Width Warning %s Above estimated max resolution:%s. StructIndex:0"
                    % (width, max_resolution)
                )
    else:
        fixes.append("-IHDR Width is empty. StructIndex:0")

    if len(depth) > 0:
        if depth not in IHDR_VALID_DEPTHS:
            fixes.append(
                "-IHDR Depht: Wrong bit depht (depht must be 1,2,4,8 or 16). StructIndex:2"
            )
    else:
        fixes.append("-IHDR Depht Must not be empty. StructIndex:2")

    if len(color) > 0:
        if color not in IHDR_VALID_COLOR_TYPES:
            fixes.append("-IHDR Color Must be 0,2,3,4 or 6. StructIndex:3")
        if color in ("2", "4", "6") and depth not in ("8", "16"):
            fixes.append("-IHDR Color :Wrong bit depht must be 8 or 16. StructIndex:3")
        if color == "3" and depth not in ("1", "2", "4", "8"):
            fixes.append(
                "-IHDR Color 3: Wrong bit depht with IHDR Color type 3 "
                "(depht must be 1,2,4 or 8). StructIndex:3"
            )
    else:
        fixes.append("-IHDR Color Must not be empty. StructIndex:3")

    if len(filter_method) > 0 and filter_method != "0":
        fixes.append("-IHDR Filter Method Wrong value must be 0. StructIndex:4")
    elif len(filter_method) == 0:
        fixes.append("-IHDR Filter Method Must not be empty. StructIndex:4")

    if len(method) > 0 and method != "0":
        fixes.append("-IHDR Compression Algorithms : Wrong value must be 0. StructIndex:5")
    elif len(method) == 0:
        fixes.append("-IHDR Compression Algorithms must not be empty. StructIndex:5")

    if len(interlace) > 0 and interlace not in ("0", "1"):
        fixes.append(
            "-IHDR Interlace Method :Wrong value must be 0 "
            "(no interlace) or 1 (Adam7 interlace). StructIndex:6"
        )
    elif len(interlace) == 0:
        fixes.append("-IHDR Interlace Must not be empty. StructIndex:6")

    return IhdrInfo(
        width=width,
        height=height,
        depth=depth,
        color=color,
        method=method,
        filter_method=filter_method,
        interlace=interlace,
        fixes=tuple(fixes),
    )


def parse_bkgd(data: str, ihdr_color: str, ihdr_depth: str) -> BkgdInfo:
    fixes: list[str] = []
    gray = red = green = blue = index = ""
    expected_length = BKGD_EXPECTED_HEX_LENGTH.get(str(ihdr_color))
    if expected_length is not None and len(data) != expected_length:
        fixes.append(
            "-bKGD length is not Valid :%s must be %s for IHDR color type %s"
            % (len(data) // 2, expected_length // 2, ihdr_color)
        )

    def max_depth_value() -> int:
        return (2 ** int(ihdr_depth)) - 1

    if ihdr_color in ("0", "4"):
        try:
            gray = _hex_int_text(data, 0, 4)
        except Exception as exc:
            fixes.append("-Error bKGD Gray:" + str(exc))

        if len(gray) > 0:
            try:
                max_value = max_depth_value()
                if int(gray) > max_value:
                    fixes.append("-Gray level : Wrong value Must be less than" + str(max_value))
            except Exception as exc:
                fixes.append("-Error bKGD Gray:" + str(exc))

    if ihdr_color in ("2", "6"):
        try:
            red = _hex_int_text(data, 0, 4)
        except Exception as exc:
            fixes.append("-Error bKGD Red:" + str(exc))
        try:
            green = _hex_int_text(data, 4, 8)
        except Exception as exc:
            fixes.append("-Error bKGD Green:" + str(exc))
        try:
            blue = _hex_int_text(data, 8, 12)
        except Exception as exc:
            fixes.append("-Error bKGD Blue:" + str(exc))

        try:
            max_value = max_depth_value()
            if len(red) > 0 and int(red) > max_value:
                fixes.append("-Red level : Wrong value Must be less than " + str(max_value))
            if len(green) > 0 and int(green) > max_value:
                fixes.append("-Bkgd_Green Wrong value Must be less than " + str(max_value))
            if len(blue) > 0 and int(blue) > max_value:
                fixes.append("-Blue level : Wrong value Must be less than " + str(max_value))
        except Exception as exc:
            fixes.append("-Error Bkgd:" + str(exc))

    if ihdr_color == "3":
        try:
            index = _hex_int_text(data, 0, 2)
        except Exception as exc:
            fixes.append("-Error bKGD Index:" + str(exc))

    return BkgdInfo(
        gray=gray,
        red=red,
        green=green,
        blue=blue,
        index=index,
        fixes=tuple(fixes),
    )


def parse_hist(
    data: str,
    has_plte: bool = False,
    has_splt: bool = False,
    plte_entries: int = 0,
    splt_entries: int = 0,
) -> HistInfo:
    fixes: list[str] = []
    entries: tuple[str, ...] = ()

    if len(data) <= 0:
        fixes.append("-hIST must Not be empty")
        return HistInfo(entries=entries, fixes=tuple(fixes))

    if not has_plte and not has_splt:
        fixes.append("-PLTE Chunk sPLT is missing.(hIST must be used after one of them)")

    entries = tuple(data[index : index + 4] for index in range(0, len(data), 4))

    if has_plte and len(entries) != plte_entries:
        fixes.append("-Histogram frequencies entries must match PLTE entries number")

    if has_splt and len(entries) != splt_entries:
        fixes.append("-Histogram frequencies entries must match sPLT entries number")

    return HistInfo(entries=entries, fixes=tuple(fixes))


def parse_trns(
    data: str,
    ihdr_color: str,
    has_plte: bool = False,
    has_splt: bool = False,
    plte_entries: int = 0,
    splt_entries: int = 0,
) -> TrnsInfo:
    fixes: list[str] = []
    gray = true_r = true_g = true_b = ""
    indexes: list[str] = []

    if len(ihdr_color) == 0:
        fixes.append("-IHDR Color Have to be either 0,2 or 3 when used with tRNS")
        return TrnsInfo(fixes=tuple(fixes))

    if len(data) == 0:
        fixes.append("-tRNS Chunk Must not be empty")
        return TrnsInfo(fixes=tuple(fixes))

    if ihdr_color not in ("0", "2", "3"):
        fixes.append(
            "-IHDR Color IHDR Color Have to be either 0,2 or 3 when used with tRNS"
        )
        return TrnsInfo(fixes=tuple(fixes))

    if ihdr_color == "0":
        try:
            gray = _hex_int_text(data, 0, 4)
        except Exception as exc:
            fixes.append("-Error tRNS_Gray:" + str(exc))

    if ihdr_color == "2":
        try:
            true_r = _hex_int_text(data, 0, 4)
        except Exception as exc:
            fixes.append("-Error tRNS_TrueR:" + str(exc))
        try:
            true_g = _hex_int_text(data, 4, 8)
        except Exception as exc:
            fixes.append("-Error tRNS_TrueG:" + str(exc))
        try:
            true_b = _hex_int_text(data, 8, 16)
        except Exception as exc:
            fixes.append("-Error tRNS_TrueB:" + str(exc))

    if ihdr_color == "3":
        if not has_plte and not has_splt:
            fixes.append(
                "-PLTE Chunk or sPLT is missing.(tRNS must be used after one of them)"
            )
        for index in range(0, len(data), 2):
            try:
                indexes.append(_hex_int_text(data, index, index + 2))
            except Exception as exc:
                fixes.append("-Error tRNS_Index:" + str(exc))

        if has_plte and len(indexes) > plte_entries:
            fixes.append(
                "-tRNS Alpha indexes palettes entries must not be superior to PLTE entries"
            )

        if has_splt and len(indexes) > splt_entries:
            fixes.append(
                "-tRNS Alpha indexes palettes entries must not be superior to sPLT entries"
            )

    return TrnsInfo(
        gray=gray,
        true_r=true_r,
        true_g=true_g,
        true_b=true_b,
        indexes=tuple(indexes),
        fixes=tuple(fixes),
    )


def parse_sbit(data: str, ihdr_color: str, ihdr_depth: str) -> SbitInfo:
    fixes: list[str] = []
    gray = true_r = true_g = true_b = ""
    gray_scale = gray_alpha = ""
    true_alpha_r = true_alpha_g = true_alpha_b = true_alpha = ""

    def parse_component(start: int, end: int, label: str) -> str:
        try:
            return _hex_int_text(data, start, end)
        except Exception as exc:
            fixes.append("-Error sBIT %s:" % label + str(exc))
            return ""

    def depth_value() -> int:
        return int(ihdr_depth)

    if ihdr_color == "0":
        gray = parse_component(0, 2, "Gray")
        if gray == "0":
            fixes.append("-Significant greyscale bits (must be greater than 0) ")

    if ihdr_color in ("2", "3"):
        true_r = parse_component(0, 2, "Red")
        true_g = parse_component(2, 4, "Green")
        true_b = parse_component(4, 6, "Blue")

        if true_r == "0":
            fixes.append("-sBit red value (must be greater than 0")
        if true_g == "0":
            fixes.append("-sBit green value (must be greater than 0")
        if true_b == "0":
            fixes.append("-sBit blue value (must be greater than 0")

        if ihdr_color == "3":
            if len(true_r) > 0 and int(true_r) > 8:
                fixes.append("-sBit red value (must be greater than 0")
            if len(true_g) > 0 and int(true_g) > 8:
                fixes.append("-sBit green value (must not be greater than 8)")
            if len(true_b) > 0 and int(true_b) > 8:
                fixes.append("-sBit blue value (must not be greater than 8)")
        else:
            try:
                max_depth = depth_value()
                if len(true_r) > 0 and int(true_r) > max_depth:
                    fixes.append("-sBit red value (must not be greater than %s)" % ihdr_depth)
                if len(true_g) > 0 and int(true_g) > max_depth:
                    fixes.append("-sBit green value (must not be greater than %s)" % ihdr_depth)
                if len(true_b) > 0 and int(true_b) > max_depth:
                    fixes.append("-sBit blue value (must not be greater than %s)" % ihdr_depth)
            except Exception as exc:
                fixes.append("-Error sBIT Depht:" + str(exc))

    if ihdr_color == "4":
        gray_scale = parse_component(0, 2, "GrayScale")
        gray_alpha = parse_component(2, 4, "GrayAlpha")
        if gray_scale == "0":
            fixes.append("-sBit Grayscale value (must not be greater than 0)")
        if gray_alpha == "0":
            fixes.append("-sBit Grayscale alpha value (must not be greater than 0)")
        try:
            max_depth = depth_value()
            if len(gray_scale) > 0 and int(gray_scale) > max_depth:
                fixes.append(
                    "-sBit Grayscale value (must not be greater than %s)" % ihdr_depth
                )
            if len(gray_alpha) > 0 and int(gray_alpha) > max_depth:
                fixes.append(
                    "-sBit Grayscale alpha value (must not be greater than %s)"
                    % ihdr_depth
                )
        except Exception as exc:
            fixes.append("-Error sBIT Depht:" + str(exc))

    if ihdr_color == "6":
        true_alpha_r = parse_component(0, 2, "TrueAlphaR")
        true_alpha_g = parse_component(2, 4, "TrueAlphaG")
        true_alpha_b = parse_component(4, 6, "TrueAlphaB")
        true_alpha = parse_component(6, 8, "TrueAlpha")

        if true_alpha_r == "0":
            fixes.append("-sBit True alpha red value (must not be greater than 0)")
        if true_alpha_g == "0":
            fixes.append("-sBit True alpha green value (must not be greater than 0)")
        if true_alpha_b == "0":
            fixes.append("-sBit True alpha blue value (must not be greater than 0)")
        if true_alpha == "0":
            fixes.append("-sBit True alpha value (must not be greater than 0)")

        try:
            max_depth = depth_value()
            if len(true_alpha_r) > 0 and int(true_alpha_r) > max_depth:
                fixes.append(
                    "-sBit True alpha red value (must not be greater than %s)" % ihdr_depth
                )
            if len(true_alpha_g) > 0 and int(true_alpha_g) > max_depth:
                fixes.append(
                    "-sBit True alpha green value (must not be greater than %s)"
                    % ihdr_depth
                )
            if len(true_alpha_b) > 0 and int(true_alpha_b) > max_depth:
                fixes.append(
                    "-sBit True alpha blue value (must not be greater than %s)"
                    % ihdr_depth
                )
            if len(true_alpha) > 0 and int(true_alpha) > max_depth:
                fixes.append(
                    "-sBit True alpha  value (must not be greater than %s)" % ihdr_depth
                )
        except Exception as exc:
            fixes.append("-Error sBIT Depht:" + str(exc))

    return SbitInfo(
        gray=gray,
        true_r=true_r,
        true_g=true_g,
        true_b=true_b,
        gray_scale=gray_scale,
        gray_alpha=gray_alpha,
        true_alpha_r=true_alpha_r,
        true_alpha_g=true_alpha_g,
        true_alpha_b=true_alpha_b,
        true_alpha=true_alpha,
        fixes=tuple(fixes),
    )


def parse_plte(data: str, ihdr_depth: str) -> PlteInfo:
    fixes: list[str] = []
    red: list[str] = []
    green: list[str] = []
    blue: list[str] = []
    total = len(data)

    if not str(int(total) / 3).endswith(".0"):
        fixes.append("-PLTE Total palettes number must be divisible by 3")

    for index in range(0, total, 6):
        red_value = data[index : index + 2]
        green_value = data[index + 2 : index + 4]
        blue_value = data[index + 4 : index + 6]
        try:
            int(red_value, 16)
        except Exception as exc:
            fixes.append("-Error PLTER wrong value at" + str(index) + ":" + str(exc))
        try:
            int(green_value, 16)
        except Exception as exc:
            fixes.append("-Error PLTEG wrong value at " + str(index + 2) + ":" + str(exc))
        try:
            int(blue_value, 16)
        except Exception as exc:
            fixes.append("-Error PLTEB wrong value at " + str(index + 4) + ":" + str(exc))

        red.append(str(red_value))
        green.append(str(green_value))
        blue.append(str(blue_value))

    if len(red) > 256:
        fixes.append("-Error PLTER > 256 :%s" % len(red))
    if len(green) > 256:
        fixes.append("-Error PLTER > 256 :%s" % len(red))
    if len(blue) > 256:
        fixes.append("-Error PLTER > 256 :%s" % len(red))

    if len(ihdr_depth) > 0:
        try:
            max_entries = 2 ** int(ihdr_depth)
            last_blue_len = len(blue[-1]) if blue else 0
            if len(red) > max_entries:
                fixes.append(
                    "-PLTE Wrong RED %s palettes not in bitdepht range "
                    "(must not be > 2 power of image Depht:%s)"
                    % (str(last_blue_len - 1), max_entries)
                )
            elif len(red) == 0:
                fixes.append("-PLTE Wrong RED palettes entry must Not be empty")

            if len(green) > max_entries:
                fixes.append(
                    "-PLTE %s Wrong Green palettes not in bitdepht range: "
                    "(must not be > 2 power of image Depht:%s)"
                    % (str(last_blue_len), max_entries)
                )
            elif len(green) == 0:
                fixes.append("-PLTE Wrong Green palettes entry must Not be empty")

            if len(blue) > max_entries:
                fixes.append("-PLTE Blue palettes not in bitdepht range")
            elif len(green) == 0:
                fixes.append("-PLTE Wrong Blue palettes entry must Not be empty")
        except Exception as exc:
            fixes.append("-IHDR Depht value have to be fixed first:" + str(exc))
    else:
        fixes.append("-IHDR Depht value have to be fixed first")

    return PlteInfo(red=tuple(red), green=tuple(green), blue=tuple(blue), fixes=tuple(fixes))


def parse_splt(data: str, previous_names: tuple[str, ...] = ()) -> SpltInfo:
    fixes: list[Any] = []
    red: list[str] = []
    green: list[str] = []
    blue: list[str] = []
    alpha: list[str] = []
    freq: list[str] = []
    bad_chars: list[tuple[str, int]] = []
    badchar_marker: list[Any] = ["badchar"]

    if len(data) <= 0:
        fixes.append("-sPLT entries must Not be empty")
        return SpltInfo(fixes=tuple(fixes))

    null_pos = _find_hex_separator(data)
    if null_pos is None:
        fixes.append("-sPLT haven't found any Null Bytes !")
        return SpltInfo(fixes=tuple(fixes))

    name = data[:null_pos]
    decoded_name = ""

    for index in range(0, len(name), 2):
        try:
            value = int(data[index : index + 2], 16)
            char = chr(value)
        except Exception:
            value = 258
            char = chr(value)

        if value not in range(32, 127) and value not in range(161, 256):
            decoded_name += "€"
            bad_chars.append((char, index))
            badchar_marker.append(index)
            fixes.append(
                "-Character not allowed %s at index %s in sPLT_Name\n-Replaced by [€] "
                % (char, index)
            )
        else:
            decoded_name += char

    if len(badchar_marker) > 1:
        fixes.append(badchar_marker)

    try:
        depth = _hex_int_text(data, null_pos + 2, null_pos + 4)
    except Exception as exc:
        depth = ""
        fixes.append("-Sample depth is not correct it must be 8 or 16:" + str(exc))

    if depth not in ("8", "16"):
        fixes.append("-Sample depth is not correct it must be 8 or 16")

    pos = 0
    if depth == "8":
        for _ in range(len(data)):
            red.append(data[:pos])
            green.append(data[pos : pos + 2])
            blue.append(data[pos + 2 : pos + 4])
            alpha.append(data[pos + 4 : pos + 6])
            freq.append(data[pos + 6 : pos + 8])
            pos += 8
    elif depth == "16":
        for _ in range(len(data)):
            red.append(data[:pos])
            green.append(data[pos : pos + 4])
            blue.append(data[pos + 4 : pos + 8])
            alpha.append(data[pos + 8 : pos + 16])
            freq.append(data[pos + 16 : pos + 24])
            pos += 24

    if len(name) > 79:
        fixes.append("-Length of sPLT name is not Valid (Too long >79)")

    if depth == "8":
        if not str(int(len(red)) / 6).endswith(".0"):
            fixes.append(
                "-Wrong Red sPLT length: %s /6= %s (not divisible by 6)."
                % (len(red), str(len(red) / 6))
            )
        if not str(int(len(green)) / 6).endswith(".0"):
            fixes.append(
                "-Wrong Green sPLT length: %s /6= %s (not divisible by 6)."
                % (len(green), str(len(green) / 6))
            )
        if not str(int(len(blue)) / 6).endswith(".0"):
            fixes.append(
                "-Wrong Green sPLT length: %s /6= %s (not divisible by 6)."
                % (len(blue), str(len(blue) / 6))
            )
        if not str(int(len(alpha)) / 6).endswith(".0"):
            fixes.append(
                "-Wrong Alpha sPLT length: %s /6= %s (not divisible by 6)."
                % (len(alpha), str(len(alpha) / 6))
            )
        if not str(int(len(freq)) / 6).endswith(".0"):
            fixes.append(
                "-Wrong Frequency sPLT length: %s /6= %s (not divisible by 6)."
                % (len(freq), str(len(freq) / 6))
            )
    elif depth == "16":
        if not str(int(len(red)) / 10).endswith(".0"):
            fixes.append(
                "-Wrong Red sPLT length: %s /10= %s (not divisible by 10)."
                % (len(red), str(len(red) / 10))
            )
        if not str(int(len(green)) / 10).endswith(".0"):
            fixes.append(
                "-Wrong Red sPLT length: %s /10= %s (not divisible by 10)."
                % (len(green), str(len(green) / 10))
            )
        if not str(int(len(blue)) / 10).endswith(".0"):
            fixes.append(
                "-Wrong Red sPLT length: %s /10= %s (not divisible by 10)."
                % (len(blue), str(len(blue) / 10))
            )
        if not str(int(len(alpha)) / 10).endswith(".0"):
            fixes.append(
                "-Wrong Alpha sPLT length: %s /10= %s (not divisible by 10)."
                % (len(alpha), str(len(alpha) / 10))
            )
        if not str(int(len(freq)) / 10).endswith(".0"):
            fixes.append(
                "-Wrong Frequency sPLT length: %s /10= %s (not divisible by 10)."
                % (len(freq), str(len(freq) / 10))
            )

    if name in previous_names:
        fixes.append("-sPLT can be used multiple times but cannot share the same name.")

    return SpltInfo(
        name=name,
        decoded_name=decoded_name,
        depth=depth,
        red=tuple(red),
        green=tuple(green),
        blue=tuple(blue),
        alpha=tuple(alpha),
        freq=tuple(freq),
        bad_chars=tuple(bad_chars),
        fixes=tuple(fixes),
    )


def parse_text(data: str) -> TextInfo:
    fixes: list[str] = []
    null_pos = _find_hex_separator(data)
    if null_pos is None:
        return TextInfo(fixes=("-tEXt missing keyword separator",))

    keyword = data[:null_pos]
    text = data[null_pos + 2 :]
    fixes.extend(_keyword_bad_char_fixes(keyword, "tEXt"))
    fixes.extend(_keyword_length_fixes(keyword, "tEXt"))

    return TextInfo(
        keyword=keyword,
        text=text,
        decoded_keyword=_decode_hex_text(keyword),
        decoded_text=_decode_hex_text(text, errors="ignore"),
        fixes=tuple(fixes),
    )


def parse_ztxt(data: str) -> ZtxtInfo:
    fixes: list[str] = []
    null_pos = _find_hex_separator(data)
    if null_pos is None:
        return ZtxtInfo(fixes=("-zTXt missing keyword separator",))

    keyword = data[:null_pos]
    try:
        text = zlib.decompress(bytes.fromhex(data[null_pos + 4 :]))
    except Exception as exc:
        return ZtxtInfo(
            keyword=keyword,
            decoded_keyword=_decode_hex_text(keyword),
            fixes=("-zTXt Text Error:" + str(exc),),
        )

    fixes.extend(_keyword_bad_char_fixes(keyword, "zTXt"))
    fixes.extend(_keyword_length_fixes(keyword, "zTXt"))

    return ZtxtInfo(
        keyword=keyword,
        text=text,
        decoded_keyword=_decode_hex_text(keyword),
        decoded_text=text.decode(errors="ignore"),
        fixes=tuple(fixes),
    )


def parse_itxt(data: str) -> ItxtInfo:
    fixes: list[str] = []
    null_pos = _find_hex_separator(data)
    if null_pos is None:
        return ItxtInfo(fixes=("-iTXt missing keyword separator",))

    keyword = data[:null_pos]
    fixes.extend(_keyword_bad_char_fixes(keyword, "iTXt"))
    fixes.extend(_keyword_length_fixes(keyword, "iTXt"))

    flag = data[len(keyword) + 2 : len(keyword) + 4]
    method = data[len(keyword) + 4 : len(keyword) + 6]
    newpos = len(keyword) + len(flag) + len(method) + 2

    if data[newpos : newpos + 2] == "00":
        language = ""
    else:
        lang_null_pos = _find_hex_separator(data[newpos:])
        if lang_null_pos is None:
            return ItxtInfo(
                keyword=keyword,
                compression_flag=flag,
                compression_method=method,
                fixes=tuple(fixes + ["-iTXt missing language separator"]),
            )
        language = data[newpos : newpos + lang_null_pos]

    newpos = newpos + len(language) + 2

    if data[newpos : newpos + 2] == "00":
        translated_keyword = ""
    else:
        translated_null_pos = _find_hex_separator(data[newpos:])
        if translated_null_pos is None:
            return ItxtInfo(
                keyword=keyword,
                compression_flag=flag,
                compression_method=method,
                language=language,
                fixes=tuple(fixes + ["-iTXt missing translated keyword separator"]),
            )
        translated_keyword = data[newpos : newpos + translated_null_pos]

    newpos = newpos + len(translated_keyword) + 2
    text = data[newpos:]

    try:
        if flag == "01":
            decoded_text = zlib.decompress(bytes.fromhex(text)).decode(errors="ignore")
        elif flag == "00":
            decoded_text = _decode_hex_text(text)
        else:
            decoded_text = _decode_hex_text(text)
            fixes.append("-iTXt Compression Flag must be 0 or 1")
    except Exception as exc:
        decoded_text = ""
        fixes.append("-iTXt String Error:" + str(exc))

    if flag == "01" and method != "00":
        fixes.append("-iTXt Compression Method must be 0")

    return ItxtInfo(
        keyword=keyword,
        text=decoded_text,
        compression_flag=flag,
        compression_method=method,
        language=language,
        translated_keyword=translated_keyword,
        decoded_keyword=_decode_hex_text(keyword),
        decoded_language=_decode_hex_text(language),
        decoded_translated_keyword=_decode_hex_text(translated_keyword),
        fixes=tuple(fixes),
    )


def parse_idat(
    data: str,
    raw_length_hex: str,
    length_history: tuple[int, ...] = (),
    bytes_len: int = 0,
    datastream: str = "",
    counter: int = 0,
) -> IdatInfo:
    fixes: list[str] = []

    try:
        raw_length = int(raw_length_hex, 16)
    except Exception as exc:
        raw_length = 0
        fixes.append("-IDAT Length Error:" + str(exc))

    next_history = tuple(length_history) + (raw_length,)
    try:
        average_length: int | str = Counter(next_history).most_common(1)[0][0]
    except Exception as exc:
        average_length = next_history[-1] if next_history else ""
        fixes.append("-IDAT Average Length Error:" + str(exc))

    return IdatInfo(
        raw_length=raw_length,
        length_history=next_history,
        average_length=average_length,
        bytes_len=bytes_len + raw_length,
        datastream=datastream + data,
        counter=counter + 1,
        fixes=tuple(fixes),
    )


def parse_pcal(data: str) -> PcalInfo:
    fixes: list[str] = []
    parameters: list[str] = []
    keyword = data.split("00")[0]

    for index in range(0, len(keyword), 2):
        try:
            value = int(keyword[index : index + 2], 16)
        except Exception as exc:
            fixes.append("-pCAL Keyword byte error:" + str(exc))
            continue

        if value not in range(32, 127) and value not in range(161, 256):
            if keyword[index : index + 2] != "00" and keyword[index : index + 2] != "0a":
                fixes.append(
                    "-Character not allowed %s at index %s in pCAL Keyword "
                    "(must be between 32-126 and 161-255 but is %s"
                    % (keyword[index : index + 2], index, value)
                )

    if len(keyword) >= 79:
        fixes.append("-pCAL Keyword length is not Valid :%s" % len(keyword))

    try:
        decoded_keyword = _decode_hex_text(keyword)
    except Exception:
        decoded_keyword = ""

    keypos = len(keyword) + 2
    try:
        zero = _hex_int_text(data, keypos, keypos + 8)
    except Exception as exc:
        zero = ""
        fixes.append("-pCAL Original zero Error:" + str(exc))

    try:
        maximum = _hex_int_text(data, keypos + 8, keypos + 16)
    except Exception as exc:
        maximum = ""
        fixes.append("-pCAL Original max Error:" + str(exc))

    try:
        equation = _hex_int_text(data, keypos + 16, keypos + 18)
    except Exception as exc:
        equation = ""
        fixes.append("-pCAL Equation type Error:" + str(exc))

    try:
        parameter_count = _hex_int_text(data, keypos + 18, keypos + 20)
    except Exception as exc:
        parameter_count = ""
        fixes.append("-pCAL Number of parameters Error:" + str(exc))

    unit: bytes | str = ""
    if parameter_count != "" and parameter_count != "0":
        try:
            unit = bytes.fromhex(data[20:].split("00")[0])
        except Exception as exc:
            fixes.append("-pCAL Unit Error:" + str(exc))

    newlength = keypos + 20
    try:
        count = int(parameter_count)
    except Exception:
        count = 0

    for _ in range(count):
        param = ""
        try:
            for index in range(0, len(data[newlength:]), 2):
                hx = data[newlength + index : newlength + index + 2]
                if hx != "00":
                    param += str(hx)
                else:
                    break
            parameters.append(param)
            newlength += len(param) + 2
        except Exception as exc:
            fixes.append("-pCAL Parameter Error:" + str(exc))

    return PcalInfo(
        keyword=keyword,
        decoded_keyword=decoded_keyword,
        zero=zero,
        maximum=maximum,
        equation=equation,
        parameter_count=parameter_count,
        unit=unit,
        parameters=tuple(parameters),
        fixes=tuple(fixes),
    )


def parse_spal(data: str) -> SpalInfo:
    return SpalInfo()


def parse_gama(data: str) -> GamaInfo:
    fixes: list[str] = []
    value = ""
    byte_length = len(data) // 2

    if byte_length != 4:
        fixes.append("-gAMA length is not Valid :%s must be 4" % byte_length)

    try:
        value = _hex_int_text(data, 0, 8)
    except Exception as exc:
        fixes.append("-Gama value error" + str(exc))
        return GamaInfo(value=value, fixes=tuple(fixes))

    if value == "0":
        fixes.append("-A gAMA Chunk of 0 is Useless.")

    return GamaInfo(value=value, fixes=tuple(fixes))


def parse_phys(data: str) -> PhysInfo:
    fixes: list[str] = []
    y = ""
    x = ""
    unit = ""

    try:
        y = _hex_int_text(data, 0, 8)
    except (NameError, ValueError) as exc:
        fixes.append("-Error pHYs Y:" + str(exc))

    try:
        x = _hex_int_text(data, 8, 16)
    except (NameError, ValueError) as exc:
        fixes.append("-Error pHYs X:" + str(exc))

    try:
        unit = _hex_int_text(data, 16, 18)
    except (NameError, ValueError) as exc:
        fixes.append("-Error pHYs U:" + str(exc))

    if len(y) > 0:
        if int(y) > PHYS_MAX_PIXELS_PER_UNIT:
            fixes.append(
                "-Pixels per unit, Y axis: Wrong size (Too high) "
                "Must be between 1 to 2147483647."
            )
    else:
        fixes.append(
            "-Pixels per unit, Y axis: Wrong size (Too low) "
            "Must be between 1 to 2147483647."
        )

    if len(x) > 0:
        if int(x) > PHYS_MAX_PIXELS_PER_UNIT:
            fixes.append(
                "-Pixels per unit, X axis: Wrong size (Too high) "
                "Must be between 1 to 2147483647."
            )
    else:
        fixes.append(
            "-Pixels per unit, X axis: Wrong size (Too low) "
            "Must be between 1 to 2147483647."
        )

    if len(unit) > 0 and unit not in ("0", "1"):
        fixes.append("-Unit specifier :Wrong value Must be between 0 (unknown) or 1(meter).")

    return PhysInfo(y=y, x=x, unit=unit, fixes=tuple(fixes))


def parse_time(data: str, current_year: int | None = None) -> TimeInfo:
    if current_year is None:
        current_year = datetime.now().year

    if len(data) < 14:
        return TimeInfo(parse_fixes=("-tIME Not enough bytes inside tIME data.",))

    parse_fixes: list[str] = []

    try:
        year = _hex_int_text(data, 0, 4)
    except Exception:
        year = ""
        parse_fixes.append("-tIME Year is > than the current year")

    try:
        month = _hex_int_text(data, 4, 6)
    except Exception:
        month = ""
        parse_fixes.append("-tIME Month value is not valid")

    try:
        day = _hex_int_text(data, 6, 8)
    except Exception:
        day = ""
        parse_fixes.append("-tIME Day value is not valid")

    try:
        hour = _hex_int_text(data, 8, 10)
    except Exception:
        hour = ""
        parse_fixes.append("-tIME Hour value is not valid")

    try:
        minute = _hex_int_text(data, 10, 12)
    except Exception:
        minute = ""
        parse_fixes.append("-tIME Minute value is not valid")

    try:
        second = _hex_int_text(data, 12, 14)
    except Exception:
        second = ""
        parse_fixes.append("-tIME Second value is not valid")

    validation_fixes: list[str] = []

    if len(year) > 0 and int(year) > current_year:
        validation_fixes.append("-Year is > than current year" + str(year))
    if len(month) > 0 and int(month) not in range(1, 13):
        validation_fixes.append("-Month value is not valid " + str(month))
    if len(day) > 0 and int(day) not in range(1, 32):
        validation_fixes.append("-Day value is not valid" + str(day))
    if len(hour) > 0 and int(hour) not in range(0, 24):
        validation_fixes.append("-Hour value is not valid " + str(hour))
    if len(minute) > 0 and int(minute) not in range(0, 60):
        validation_fixes.append("-Minute value is not valid" + str(minute))
    if len(second) > 0 and int(second) not in range(0, 61):
        validation_fixes.append("-Second  value is not valid" + str(second))

    return TimeInfo(
        year=year,
        month=month,
        day=day,
        hour=hour,
        minute=minute,
        second=second,
        parse_fixes=tuple(parse_fixes),
        validation_fixes=tuple(validation_fixes),
    )


def parse_ster(data: str) -> SterInfo:
    fixes: list[str] = []
    mode = ""

    try:
        mode = _hex_int_text(data, 0, 2)
    except Exception as exc:
        fixes.append("-sTER value error" + str(exc))
        return SterInfo(mode=mode, fixes=tuple(fixes))

    if mode not in ("0", "1"):
        fixes.append("-sTER should be 0 or 1")

    return SterInfo(mode=mode, fixes=tuple(fixes))


def parse_srgb(data: str, has_chrm: bool = False) -> SrgbInfo:
    fixes: list[str] = []
    value = ""

    try:
        value = _hex_int_text(data, 0, 2)
    except Exception as exc:
        fixes.append("-sRGB value error" + str(exc))
        return SrgbInfo(value=value, fixes=tuple(fixes))

    if value not in SRGB_RENDERING_INTENTS:
        fixes.append("-sRGB value must be between 0 to 3.")

    if has_chrm:
        fixes.append("-cHRM is overided by sRGB chunk")

    return SrgbInfo(value=value, fixes=tuple(fixes))


def parse_chrm(data: str, has_srgb_or_iccp: bool = False) -> ChrmInfo:
    fixes: list[str] = []
    values: dict[str, str] = {}
    if len(data) != 64:
        fixes.append("-cHRM length is not Valid :%s must be 32" % (len(data) // 2))

    fields = (
        ("white_x", "WhiteX", 0, 8),
        ("white_y", "WhiteY", 8, 16),
        ("red_x", "RedX", 16, 24),
        ("red_y", "RedY", 24, 32),
        ("green_x", "GreenX", 32, 40),
        ("green_y", "GreenY", 40, 48),
        ("blue_x", "BlueX", 48, 56),
        ("blue_y", "BlueY", 56, 64),
    )

    for attr, label, start, end in fields:
        try:
            values[attr] = _unsigned_hex_int_text(data, start, end)
        except Exception as exc:
            values[attr] = ""
            fixes.append("-cHRM " + label + " Error:" + str(exc))

    if has_srgb_or_iccp:
        fixes.append("-cHRM is overided by sRGB chunk and iCCP")

    return ChrmInfo(
        white_x=values["white_x"],
        white_y=values["white_y"],
        red_x=values["red_x"],
        red_y=values["red_y"],
        green_x=values["green_x"],
        green_y=values["green_y"],
        blue_x=values["blue_x"],
        blue_y=values["blue_y"],
        fixes=tuple(fixes),
    )


def parse_offs(data: str) -> OffsInfo:
    fixes: list[str] = []

    try:
        x = _signed_hex_int_text(data, 0, 8)
    except Exception:
        x = OFFS_PARSE_FALLBACK

    try:
        y = _signed_hex_int_text(data, 8, 16)
    except Exception:
        y = OFFS_PARSE_FALLBACK

    try:
        unit = _hex_int_text(data, 16, 18)
    except Exception:
        unit = OFFS_PARSE_FALLBACK

    if int(x) not in range(OFFS_MIN_POSITION, OFFS_MAX_POSITION + 1):
        fixes.append(
            "-Wrong Offset position X must be between -2,147,483,647 to +2,147,483,647"
        )

    if int(y) not in range(OFFS_MIN_POSITION, OFFS_MAX_POSITION + 1):
        fixes.append(
            "-Wrong Offset position Y must be between -2,147,483,647 to +2,147,483,647"
        )

    if unit not in ("0", "1"):
        fixes.append("-Wrong Offset unit must be between 0 or 1")

    return OffsInfo(x=x, y=y, unit=unit, fixes=tuple(fixes))


def parse_gifg(data: str) -> GifgInfo:
    fixes: list[str] = []
    byte_length = len(data) // 2

    if byte_length != 4:
        fixes.append("-gIFg length is not Valid :%s must be 4" % byte_length)

    try:
        disposal_method = _hex_int_text(data, 0, 2)
    except Exception as exc:
        disposal_method = ""
        fixes.append("-gIFg Disposal Method Error:" + str(exc))

    try:
        user_input_flag = _hex_int_text(data, 2, 4)
    except Exception as exc:
        user_input_flag = ""
        fixes.append("-gIFg User Input Flag Error:" + str(exc))

    try:
        delay_time = _hex_int_text(data, 4, 8)
    except Exception as exc:
        delay_time = ""
        fixes.append("-gIFg Delay Time Error:" + str(exc))

    return GifgInfo(
        disposal_method=disposal_method,
        user_input_flag=user_input_flag,
        delay_time=delay_time,
        fixes=tuple(fixes),
    )


def parse_gifx(data: str) -> GifxInfo:
    fixes: list[str] = []

    try:
        application_identifier = _hex_int_text(data, 0, 16)
    except Exception as exc:
        application_identifier = ""
        fixes.append("-gIFx Application Identifier Error:" + str(exc))

    try:
        authentication_code = _hex_int_text(data, 16, 22)
    except Exception as exc:
        authentication_code = ""
        fixes.append("-gIFx Authentication Code Error:" + str(exc))

    try:
        application_data = str(int(data[22:], 16))
    except Exception as exc:
        application_data = ""
        fixes.append("-gIFx Application Data Error:" + str(exc))

    return GifxInfo(
        application_identifier=application_identifier,
        authentication_code=authentication_code,
        application_data=application_data,
        fixes=tuple(fixes),
    )


def parse_iccp(
    data: str,
    raw_length_hex: str | None = None,
    has_chrm: bool = False,
) -> IccpInfo:
    fixes: list[Any] = []
    name = ""
    null_pos = 0
    bad_chars: list[tuple[str, int]] = []
    badchar_marker: list[Any] = ["badchar"]

    for index in range(0, len(data), 2):
        try:
            byte_value = int(data[index : index + 2], 16)
        except Exception as exc:
            fixes.append("-iCCP Name byte error:" + str(exc))
            return IccpInfo(
                name=name,
                method="",
                profile="",
                null_pos=null_pos,
                bad_chars=tuple(bad_chars),
                fixes=tuple(fixes),
            )

        char = chr(byte_value)
        if data[index : index + 2] == "00":
            null_pos = index
            if index > 79:
                fixes.append("-Length of iCCP Profile name is not valid")
            break

        if byte_value not in range(32, 127) and byte_value not in range(161, 255):
            name += "€"
            bad_chars.append((char, index))
            badchar_marker.append(index)
            fixes.append(
                "-Character not allowed %s at index %s in iCCP_Name\n-Replaced by [€]"
                % (char, index)
            )
        else:
            name += char

    if len(badchar_marker) > 1:
        fixes.append(badchar_marker)

    try:
        method: int | str = int(data[null_pos + 2 : null_pos + 4], 16)
    except Exception as exc:
        fixes.append("-iCCP Method Error:" + str(exc))
        return IccpInfo(
            name=name,
            method="",
            profile="",
            null_pos=null_pos,
            bad_chars=tuple(bad_chars),
            fixes=tuple(fixes),
        )

    if method > 0:
        fixes.append("-Compression method is supposed to be 0 but is %s instead ." % method)

    profile = data[null_pos + 4 :]

    if raw_length_hex is not None:
        try:
            expected_profile_length = int(raw_length_hex, 16) - (int(null_pos / 2) + 2)
            actual_profile_length = int(len(profile) / 2)
            if expected_profile_length != actual_profile_length:
                fixes.append("-iCCP Profile length is not Valid")
        except Exception as exc:
            fixes.append("-iCCP Profile length error:" + str(exc))

    if has_chrm:
        fixes.append("-cHRM already present cHRM will be overide if reconized by decoders")

    if _is_known_bad_srgb_iccp_profile(name, method, profile):
        fixes.append("libpng warning: iCCP: known incorrect sRGB profile")

    return IccpInfo(
        name=name,
        method=method,
        profile=profile,
        null_pos=null_pos,
        bad_chars=tuple(bad_chars),
        fixes=tuple(fixes),
    )


def _is_known_bad_srgb_iccp_profile(name: str, method: int | str, profile: str) -> bool:
    if name != "Photoshop ICC profile" or method != 0:
        return False

    try:
        decompressed = zlib.decompress(bytes.fromhex(profile))
    except Exception:
        return False

    return b"IEC sRGB" in decompressed and b"acsp" in decompressed[:64]


def parse_exif(data: str) -> ExifInfo:
    fixes: list[str] = []

    try:
        endian = bytes.fromhex(data[:4]).decode(errors="ignore")
    except Exception as exc:
        endian = ""
        fixes.append("-eXIf endianess error:" + str(exc))

    if endian not in ("II", "MM"):
        fixes.append("-eXIf endianess should be II or MM")

    raw_values: list[str] = []
    raw = ""
    separator_count = 0

    for index in range(0, len(data), 2):
        raw += data[index : index + 2]
        if data[index : index + 2] == "00":
            separator_count += 1
            if separator_count >= 3:
                raw_values.append(raw)
                raw = ""
                separator_count = 0

    return ExifInfo(endian=endian, raw_values=tuple(raw_values), fixes=tuple(fixes))
