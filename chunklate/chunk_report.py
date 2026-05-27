from __future__ import annotations

from collections.abc import Callable, Sequence

from . import chunk_info
from .png import LegacyChunkWindow


Emit = Callable[[str], None]
Color = Callable[[str, object], str]
Chunky = Callable[[str], str]


def _chunky(chunky: Chunky | None, name: str) -> str:
    if chunky is None:
        return ""
    return chunky(name)


def render_ihdr(info: chunk_info.IhdrInfo, emit: Emit, color: Color) -> None:
    emit("-Width    :%s" % color("yellow", info.width))
    emit("-Height   :%s" % color("yellow", info.height))
    emit("-Depht    :%s" % color("yellow", info.depth))
    emit("-Color    :%s" % color("yellow", info.color))
    emit("-Method   :%s" % color("yellow", info.method))
    emit("-Filter   :%s" % color("yellow", info.filter_method))
    emit("-Interlace:%s" % color("yellow", info.interlace))


def render_legacy_chunk_window(
    window: LegacyChunkWindow,
    emit: Emit,
    color: Color,
) -> None:
    emit(
        "-Found at offset            (%s/%s/%s): (%s/%s/%s) "
        % (
            color("yellow", "Hex"),
            color("blue", "Bytes"),
            color("purple", "Index"),
            color("yellow", window.length_offset_hex),
            color("blue", window.length_offset_byte),
            color("purple", window.length_offset_index),
        )
    )
    emit(
        "-Chunk Length:              (%s/%s)"
        % (
            color("yellow", hex(int(window.raw_length, 16))),
            color("blue", int(window.raw_length, 16)),
        )
    )
    emit("")
    emit(
        "-Found at offset            (%s/%s/%s): (%s/%s/%s) "
        % (
            color("yellow", "Hex"),
            color("blue", "Bytes"),
            color("purple", "Index"),
            color("yellow", window.type_offset_hex),
            color("blue", window.type_offset_byte),
            color("purple", window.type_offset_index),
        )
    )
    emit(
        "-Chunk Type :               (%s/%s)"
        % (color("yellow", window.raw_type), color("blue", window.chunk_type))
    )
    emit("")
    emit(
        "-Found Chunk Data at offset (%s/%s/%s): (%s/%s/%s) "
        % (
            color("yellow", "Hex"),
            color("blue", "Bytes"),
            color("purple", "Index"),
            color("yellow", window.data_offset_hex),
            color("blue", window.data_offset_byte),
            color("purple", window.data_offset_index),
        )
    )
    emit("")
    emit(
        "-Found at offset            (%s/%s/%s): (%s/%s/%s) "
        % (
            color("yellow", "Hex"),
            color("blue", "Bytes"),
            color("purple", "Index"),
            color("yellow", window.crc_offset_hex),
            color("blue", window.crc_offset_byte),
            color("purple", window.crc_offset_index),
        )
    )
    emit(
        "-Chunk Crc:                 (%s/offset :  %s)"
        % (color("yellow", window.raw_crc), color("yellow", hex(window.crc_offset_byte)))
    )

    emit("")
    emit(
        "-Found at offset            (%s/%s/%s): (%s/%s/%s) "
        % (
            color("yellow", "Hex"),
            color("blue", "Bytes"),
            color("purple", "Index"),
            color("yellow", window.next_chunk_offset_hex),
            color("blue", window.next_chunk_offset_byte),
            color("purple", window.next_chunk_offset_index),
        )
    )
    emit(
        "-Raw_NextChunk Type :       (%s/%s)"
        % (color("yellow", window.raw_next_chunk), color("blue", window.next_chunk_type))
    )


def render_idat(info: chunk_info.IdatInfo, emit: Emit, color: Color) -> None:
    emit("-Image Datastream.")


def render_bkgd(info: chunk_info.BkgdInfo, emit: Emit, color: Color) -> None:
    if len(info.gray) > 0:
        emit("-Gray    :%s" % color("yellow", info.gray))
    if len(info.red) > 0:
        emit("-Red    :%s" % color("red", info.red))
    if len(info.green) > 0:
        emit("-Green  :%s" % color("green", info.green))
    if len(info.blue) > 0:
        emit("-Blue   :%s" % color("blue", info.blue))
    if len(info.index) > 0:
        emit("-Palette    :%s" % color("yellow", info.index))


def render_plte(
    red_entries: Sequence[str],
    green_entries: Sequence[str],
    blue_entries: Sequence[str],
    emit: Emit,
    color: Color,
) -> None:
    emit("-%s Red palettes are stored." % color("yellow", len(red_entries)))
    emit("-%s Green palettes are stored." % color("yellow", len(green_entries)))
    emit("-%s Blue palettes are stored." % color("yellow", len(blue_entries)))
    emit(
        "-%s RGB palettes are stored."
        % color("yellow", len(red_entries) + len(green_entries) + len(blue_entries))
    )


def render_splt(
    info: chunk_info.SpltInfo,
    red_entries: Sequence[str],
    green_entries: Sequence[str],
    blue_entries: Sequence[str],
    alpha_entries: Sequence[str],
    freq_entries: Sequence[str],
    emit: Emit,
    color: Color,
) -> None:
    if len(info.decoded_name) > 0:
        emit("-sPLT name : %s" % color("white", info.decoded_name))
    emit("-%s Suggested Red palettes are stored." % color("yellow", len(red_entries)))
    emit("-%s Suggested Green palettes are stored." % color("yellow", len(green_entries)))
    emit("-%s Suggested Blue palettes are stored." % color("yellow", len(blue_entries)))
    emit("-%s Suggested Alpha palettes are stored." % color("yellow", len(alpha_entries)))
    emit("-%s Suggested Frequency values are stored." % color("yellow", len(freq_entries)))


def render_hist(entries: Sequence[str], emit: Emit, color: Color) -> None:
    if len(entries) > 0:
        emit("-%s Histogram frequencies are stored." % color("yellow", len(entries)))


def render_trns(info: chunk_info.TrnsInfo, emit: Emit, color: Color) -> None:
    if len(info.gray) > 0:
        emit("-Gray    :%s" % color("yellow", info.gray))
    if len(info.true_r) > 0:
        emit("-Red    :%s" % color("red", info.true_r))
    if len(info.true_g) > 0:
        emit("-Green  :%s" % color("green", info.true_g))
    if len(info.true_b) > 0:
        emit("-Blue   :%s" % color("blue", info.true_b))
    if len(info.indexes) > 0:
        emit("-%s Alpha indexes are stored." % color("yellow", len(info.indexes)))


def render_phys(
    info: chunk_info.PhysInfo,
    emit: Emit,
    color: Color,
    chunky: Chunky | None = None,
) -> None:
    if len(info.y) > 0:
        emit("-Pixels per unit, Y axis: %s" % color("yellow", info.y))
        if int(info.y) > chunk_info.PHYS_MAX_PIXELS_PER_UNIT:
            emit(
                "-Pixels per unit, Y axis:"
                + color("red", " Wrong size (Too high)")
                + " Must be between 1 to 2147483647."
                + _chunky(chunky, "bad")
            )
    else:
        emit(
            "-Pixels per unit, Y axis :"
            + color("red", " Wrong size (Too low)")
            + " Must be between 1 to 2147483647."
            + _chunky(chunky, "bad")
        )

    if len(info.x) > 0:
        emit("-Pixels per unit, X axis: %s" % color("yellow", info.x))
        if int(info.x) > chunk_info.PHYS_MAX_PIXELS_PER_UNIT:
            emit(
                "Pixels per unit, X axis"
                + color("red", " Wrong size (Too high)")
                + " Must be between 1 to 2147483647."
                + _chunky(chunky, "bad")
            )
    else:
        emit(
            "-Pixels per unit, X axis"
            + color("red", " Wrong size (Too low)")
            + " Must be between 1 to 2147483647."
            + _chunky(chunky, "bad")
        )

    if len(info.unit) > 0:
        emit("-Unit specifier         :%s" % color("yellow", info.unit))
        if info.unit not in ("0", "1"):
            emit(
                "-Unit specifier :"
                + color("red", " Wrong value")
                + " Must be between 0 (unknown) or 1(meter)."
                + _chunky(chunky, "bad")
            )


def render_time(
    info: chunk_info.TimeInfo,
    current_year: int,
    emit: Emit,
    color: Color,
    chunky: Chunky | None = None,
) -> None:
    if not info.can_print_timestamp:
        emit(
            "-tIME %s inside tIME data.%s"
            % (color("red", "Not enough bytes"), _chunky(chunky, "bad"))
        )
        return

    emit(
        "-Last Modified: %s/%s/%s %s:%s:%s"
        % (
            color("white", info.day),
            color("white", info.month),
            color("white", info.year),
            color("white", info.hour),
            color("white", info.minute),
            color("white", info.second),
        )
    )

    if len(str(info.year)) > 0 and int(info.year) > current_year:
        emit(
            "-Year is > than current year    : %s %s"
            % (color("red", info.year), _chunky(chunky, "bad"))
        )
    if len(str(info.month)) > 0 and int(info.month) not in range(1, 13):
        emit(
            "-Month value is not valid   : %s %s"
            % (color("red", info.month), _chunky(chunky, "bad"))
        )
    if len(str(info.day)) > 0 and int(info.day) not in range(1, 32):
        emit(
            "-Day value is not valid      : %s %s"
            % (color("red", info.day), _chunky(chunky, "bad"))
        )
    if len(str(info.hour)) > 0 and int(info.hour) not in range(0, 24):
        emit(
            "-Hour value is not valid     : %s %s"
            % (color("red", info.hour), _chunky(chunky, "bad"))
        )
    if len(str(info.minute)) > 0 and int(info.minute) not in range(0, 60):
        emit(
            "-Minute value is not valid  : %s %s"
            % (color("red", info.minute), _chunky(chunky, "bad"))
        )
    if len(str(info.second)) > 0 and int(info.second) not in range(0, 61):
        emit(
            "-Second  value is not valid : %s %s"
            % (color("red", info.second), _chunky(chunky, "bad"))
        )


def render_srgb(
    info: chunk_info.SrgbInfo,
    has_chrm: bool,
    emit: Emit,
    color: Color,
    chunky: Chunky | None = None,
) -> None:
    if info.value == "0":
        emit("-Rendering Perceptual :%s" % color("yellow", info.value))
    elif info.value == "1":
        emit("-Rendering Relative colorimetric :%s" % color("yellow", info.value))
    elif info.value == "2":
        emit("-Rendering Saturation :%s" % color("yellow", info.value))
    elif info.value == "3":
        emit("-Rendering Absolute colorimetric :%s" % color("yellow", info.value))
    else:
        emit(
            "-%s sRGB value must be between 0 to 3. %s"
            % (color("red", "Wrong"), _chunky(chunky, "bad"))
        )

    if has_chrm:
        emit(
            "-%s already present cHRM will be %s if reconized by decoders %s"
            % (
                color("red", "cHRM"),
                color("red", "overide"),
                _chunky(chunky, "bad"),
            )
        )


def render_gama(info: chunk_info.GamaInfo, emit: Emit, color: Color) -> None:
    if len(info.value) > 0:
        emit("-Gama   :%s" % color("white", info.value))
        if info.value == "0":
            emit("-A gAMA Chunk of %s is Useless." % color("red", "0"))


def render_chrm(
    info: chunk_info.ChrmInfo,
    has_srgb_or_iccp: bool,
    emit: Emit,
    color: Color,
    chunky: Chunky | None = None,
) -> None:
    if len(info.white_x) > 0:
        emit("-WhiteX   :%s" % color("white", info.white_x))
    if len(info.white_y) > 0:
        emit("-WhiteY   :%s" % color("white", info.white_y))
    if len(info.red_x) > 0:
        emit("-RedX     :%s" % color("red", info.red_x))
    if len(info.red_y) > 0:
        emit("-RedY     :%s" % color("red", info.red_y))
    if len(info.green_x) > 0:
        emit("-GreenX   :%s" % color("green", info.green_x))
    if len(info.green_y) > 0:
        emit("-GreenY   :%s" % color("green", info.green_y))
    if len(info.blue_x) > 0:
        emit("-BlueX    :%s" % color("blue", info.blue_x))
    if len(info.blue_y) > 0:
        emit("-BlueY    :%s" % color("blue", info.blue_y))

    if has_srgb_or_iccp:
        emit(
            "-%s or %s already present cHRM will be overide if reconized by decoders %s"
            % (color("red", "sRGB"), color("red", "iCCP"), _chunky(chunky, "bad"))
        )


def render_iccp(
    info: chunk_info.IccpInfo,
    has_chrm: bool,
    emit: Emit,
    color: Color,
    chunky: Chunky | None = None,
) -> None:
    if "-Length of iCCP Profile name is not valid" in info.fixes:
        emit(
            "-Length of iCCP Profile name is %s :%s"
            % (color("red", "not Valid"), color("red", info.null_pos))
        )

    for bad_char, bad_index in info.bad_chars:
        emit(
            "-Character %s at index %s in iCCP_Name\n-Replaced by [€]"
            % (
                color("red", "not allowed [" + bad_char + "]"),
                color("red", bad_index),
            )
        )

    if isinstance(info.method, int) and info.method > 0:
        emit(
            "-Compression method is supposed to be %s but is %s instead ."
            % (color("green", "0"), color("red", info.method))
        )

    if "-iCCP Profile length is not Valid" in info.fixes:
        emit("-iCCP Profile length is %s" % color("red", "not Valid"))

    if has_chrm:
        emit(
            "-%s already present cHRM will be %s if reconized by decoders %s"
            % (color("red", "cHRM"), color("red", "overide"), _chunky(chunky, "bad"))
        )

    if len(info.name) > 0:
        emit("-iCCP Profile Name :%s" % color("yellow", info.name))
    if len(str(info.method)) > 0:
        emit("-iCCP Profile Method :%s" % color("yellow", info.method))


def render_sbit(info: chunk_info.SbitInfo, emit: Emit, color: Color) -> None:
    if len(info.gray) > 0:
        emit("-Significant greyscale bits    :%s" % color("yellow", info.gray))
    if len(info.true_r) > 0:
        emit("-significant bits Red    :%s" % color("red", info.true_r))
    if len(info.true_g) > 0:
        emit("-significant bits Green  :%s" % color("green", info.true_g))
    if len(info.true_b) > 0:
        emit("-significant bits Blue   :%s" % color("blue", info.true_b))
    if len(info.gray_scale) > 0:
        emit("-Gray scale significant bit:%s" % color("white", info.gray_scale))
    if len(info.gray_alpha) > 0:
        emit("-Gray alpha significant bit:%s" % color("white", info.gray_alpha))
    if len(info.true_alpha_r) > 0:
        emit("-significant bits Alpha Red    :%s" % color("red", info.true_alpha_r))
    if len(info.true_alpha_g) > 0:
        emit("-significant bits Alpha Green  :%s" % color("green", info.true_alpha_g))
    if len(info.true_alpha_b) > 0:
        emit("-significant bits Alpha Blue   :%s" % color("blue", info.true_alpha_b))
    if len(info.true_alpha) > 0:
        emit("-significant bits Alpha        :%s" % color("white", info.true_alpha))


def render_offs(
    info: chunk_info.OffsInfo,
    emit: Emit,
    color: Color,
    chunky: Chunky | None = None,
) -> None:
    emit("-Offset position X    :%s" % color("blue", info.x))
    emit("-Offset position Y  :%s" % color("purple", info.y))
    emit("-Offset Unit   :%s" % color("white", info.unit))
    if int(info.x) not in range(chunk_info.OFFS_MIN_POSITION, chunk_info.OFFS_MAX_POSITION + 1):
        emit(
            "-%s Offset position X must be between -2,147,483,647 to +2,147,483,647 %s"
            % (color("red", "Wrong"), _chunky(chunky, "bad"))
        )
    if int(info.y) not in range(chunk_info.OFFS_MIN_POSITION, chunk_info.OFFS_MAX_POSITION + 1):
        emit(
            "-%s Offset position Y must be between -2,147,483,647 to +2,147,483,647 %s"
            % (color("red", "Wrong"), _chunky(chunky, "bad"))
        )
    if info.unit not in ("0", "1"):
        emit(
            "-%s Offset unit must be between 0 or 1 %s"
            % (color("red", "Wrong"), _chunky(chunky, "bad"))
        )


def render_pcal(info: chunk_info.PcalInfo, emit: Emit, color: Color) -> None:
    if len(info.decoded_keyword) > 0:
        emit("-Calibration name    :%s" % color("yellow", info.decoded_keyword))
    if len(info.zero) > 0:
        emit("-Original zero       :%s" % color("yellow", info.zero))
    if len(info.maximum) > 0:
        emit("-Original max        :%s" % color("yellow", info.maximum))
    if len(info.equation) > 0:
        emit("-Equation type       :%s" % color("yellow", info.equation))
    if len(info.parameter_count) > 0:
        emit("-Number of parameters:%s" % color("yellow", info.parameter_count))


def render_gifg(info: chunk_info.GifgInfo, emit: Emit, color: Color) -> None:
    if len(info.disposal_method) > 0:
        emit("-Disposal Method    :%s" % color("yellow", info.disposal_method))
    if len(info.delay_time) > 0:
        emit("-User Input Flag    :%s" % color("yellow", info.delay_time))
        emit("-Delay Time    :%s" % color("yellow", info.delay_time))


def render_gifx(info: chunk_info.GifxInfo, emit: Emit, color: Color) -> None:
    if len(info.application_identifier) > 0:
        emit("-Application Identifier    :%s" % color("yellow", info.application_identifier))
    if len(info.authentication_code) > 0:
        emit("-Authentication Code    :%s" % color("yellow", info.authentication_code))
    if len(info.application_data) > 0:
        emit("-Application Data    :%s" % color("yellow", info.application_data))


def render_ster(info: chunk_info.SterInfo, emit: Emit, color: Color) -> None:
    if len(info.mode) > 0:
        emit("-Subimage mode    :%s" % color("yellow", info.mode))


def render_text(info: chunk_info.TextInfo, emit: Emit, color: Color) -> None:
    emit("-Keyword : %s" % color("green", info.decoded_keyword))
    emit("-String  : %s" % color("green", info.decoded_text))


def render_ztxt(info: chunk_info.ZtxtInfo, emit: Emit, color: Color) -> None:
    emit("-Keyword : %s" % color("green", info.decoded_keyword))
    emit("-String  : %s" % color("green", info.decoded_text))


def render_itxt(info: chunk_info.ItxtInfo, emit: Emit, color: Color) -> None:
    emit("-Keyword             : %s" % color("green", info.decoded_keyword))
    emit("-Compression Flag    : %s" % color("green", info.compression_flag))
    emit("-Compression Method  : %s" % color("green", info.compression_method))
    emit("-Language            : %s" % color("green", info.decoded_language))
    emit("-Keyword Traduction  : %s" % color("green", info.decoded_translated_keyword))
    emit("-String              : %s" % color("green", info.text))


def render_exif(info: chunk_info.ExifInfo, emit: Emit, color: Color) -> None:
    if info.endian == "II":
        emit("-eXif endianess is little-endian : %s" % info.endian)
    elif info.endian == "MM":
        emit("-eXif endianess is big-endian : %s" % info.endian)

    emit("\nRaw values from eXIf data :\n\n")
    for raw in info.raw_values:
        if len(raw) < 150:
            emit("- " + bytes.fromhex(raw).decode(errors="ignore"))
        else:
            emit("-Raw data is too long to be displayed")


def render_spal(info: chunk_info.SpalInfo, emit: Emit, color: Color) -> None:
    emit(info.message)
