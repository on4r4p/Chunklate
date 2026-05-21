from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


PHYS_MAX_PIXELS_PER_UNIT = 2147483647
OFFS_MIN_POSITION = -2147483647
OFFS_MAX_POSITION = 2147483647
OFFS_PARSE_FALLBACK = "2147483649"
SRGB_RENDERING_INTENTS = {
    "0": "Perceptual",
    "1": "Relative colorimetric",
    "2": "Saturation",
    "3": "Absolute colorimetric",
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


def _hex_int_text(data: str, start: int, end: int) -> str:
    return str(int(data[start:end], 16))


def _unsigned_hex_int_text(data: str, start: int, end: int) -> str:
    return str(int.from_bytes(bytes.fromhex(data[start:end]), byteorder="big", signed=False))


def _signed_hex_int_text(data: str, start: int, end: int) -> str:
    return str(int.from_bytes(bytes.fromhex(data[start:end]), byteorder="big", signed=True))


def parse_gama(data: str) -> GamaInfo:
    fixes: list[str] = []
    value = ""

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
        delay_time = _hex_int_text(data, 4, 6)
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

    return IccpInfo(
        name=name,
        method=method,
        profile=profile,
        null_pos=null_pos,
        bad_chars=tuple(bad_chars),
        fixes=tuple(fixes),
    )


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
