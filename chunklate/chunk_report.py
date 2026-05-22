from __future__ import annotations

from collections.abc import Callable, Sequence

from . import chunk_info


Emit = Callable[[str], None]
Color = Callable[[str, object], str]


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
