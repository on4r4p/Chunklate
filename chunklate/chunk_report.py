from __future__ import annotations

from collections.abc import Callable, Sequence

from . import chunk_info


Emit = Callable[[str], None]
Color = Callable[[str, object], str]
Emoji = Callable[[str], str]


def _emoji(emoji: Emoji | None, name: str) -> str:
    if emoji is None:
        return ""
    return emoji(name)


def render_ihdr(info: chunk_info.IhdrInfo, emit: Emit, color: Color) -> None:
    emit("-Width    :%s" % color("yellow", info.width))
    emit("-Height   :%s" % color("yellow", info.height))
    emit("-Depht    :%s" % color("yellow", info.depth))
    emit("-Color    :%s" % color("yellow", info.color))
    emit("-Method   :%s" % color("yellow", info.method))
    emit("-Filter   :%s" % color("yellow", info.filter_method))
    emit("-Interlace:%s" % color("yellow", info.interlace))


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
    emoji: Emoji | None = None,
) -> None:
    if len(info.y) > 0:
        emit("-Pixels per unit, Y axis: %s" % color("yellow", info.y))
        if int(info.y) > chunk_info.PHYS_MAX_PIXELS_PER_UNIT:
            emit(
                "-Pixels per unit, Y axis:"
                + color("red", " Wrong size (Too high)")
                + " Must be between 1 to 2147483647."
                + _emoji(emoji, "bad")
            )
    else:
        emit(
            "-Pixels per unit, Y axis :"
            + color("red", " Wrong size (Too low)")
            + " Must be between 1 to 2147483647."
            + _emoji(emoji, "bad")
        )

    if len(info.x) > 0:
        emit("-Pixels per unit, X axis: %s" % color("yellow", info.x))
        if int(info.x) > chunk_info.PHYS_MAX_PIXELS_PER_UNIT:
            emit(
                "Pixels per unit, X axis"
                + color("red", " Wrong size (Too high)")
                + " Must be between 1 to 2147483647."
                + _emoji(emoji, "bad")
            )
    else:
        emit(
            "-Pixels per unit, X axis"
            + color("red", " Wrong size (Too low)")
            + " Must be between 1 to 2147483647."
            + _emoji(emoji, "bad")
        )

    if len(info.unit) > 0:
        emit("-Unit specifier         :%s" % color("yellow", info.unit))
        if info.unit not in ("0", "1"):
            emit(
                "-Unit specifier :"
                + color("red", " Wrong value")
                + " Must be between 0 (unknown) or 1(meter)."
                + _emoji(emoji, "bad")
            )


def render_time(
    info: chunk_info.TimeInfo,
    current_year: int,
    emit: Emit,
    color: Color,
    emoji: Emoji | None = None,
) -> None:
    if not info.can_print_timestamp:
        emit(
            "-tIME %s inside tIME data.%s"
            % (color("red", "Not enough bytes"), _emoji(emoji, "bad"))
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
            % (color("red", info.year), _emoji(emoji, "bad"))
        )
    if len(str(info.month)) > 0 and int(info.month) not in range(1, 13):
        emit(
            "-Month value is not valid   : %s %s"
            % (color("red", info.month), _emoji(emoji, "bad"))
        )
    if len(str(info.day)) > 0 and int(info.day) not in range(1, 32):
        emit(
            "-Day value is not valid      : %s %s"
            % (color("red", info.day), _emoji(emoji, "bad"))
        )
    if len(str(info.hour)) > 0 and int(info.hour) not in range(0, 24):
        emit(
            "-Hour value is not valid     : %s %s"
            % (color("red", info.hour), _emoji(emoji, "bad"))
        )
    if len(str(info.minute)) > 0 and int(info.minute) not in range(0, 60):
        emit(
            "-Minute value is not valid  : %s %s"
            % (color("red", info.minute), _emoji(emoji, "bad"))
        )
    if len(str(info.second)) > 0 and int(info.second) not in range(0, 61):
        emit(
            "-Second  value is not valid : %s %s"
            % (color("red", info.second), _emoji(emoji, "bad"))
        )


def render_srgb(
    info: chunk_info.SrgbInfo,
    has_chrm: bool,
    emit: Emit,
    color: Color,
    emoji: Emoji | None = None,
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
            % (color("red", "Wrong"), _emoji(emoji, "bad"))
        )

    if has_chrm:
        emit(
            "-%s already present cHRM will be %s if reconized by decoders %s"
            % (
                color("red", "cHRM"),
                color("red", "overide"),
                _emoji(emoji, "bad"),
            )
        )


def render_gama(info: chunk_info.GamaInfo, emit: Emit, color: Color) -> None:
    if len(info.value) > 0:
        emit("-Gama   :%s" % color("white", info.value))
        if info.value == "0":
            emit("-A gAMA Chunk of %s is Useless." % color("red", "0"))


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
