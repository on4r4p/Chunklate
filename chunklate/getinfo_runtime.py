from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from . import chunk_info, chunk_report


LegacyCall = Callable[..., Any]


@dataclass(frozen=True)
class GetInfoRuntime:
    chunk_state: Any
    set_legacy: LegacyCall
    sync_legacy: LegacyCall
    max_resolution: LegacyCall
    checkpoint: LegacyCall
    emit: LegacyCall
    candy: LegacyCall
    color: LegacyCall
    emoji: LegacyCall
    raw_length: str
    orig_cl: str
    ihdr_color: str
    ihdr_depth: str
    chunks_history: tuple[Any, ...]
    private_chunks: tuple[Any, ...]
    allchunks: tuple[Any, ...]


def print_ok(runtime: GetInfoRuntime) -> None:
    runtime.emit(
        "\n-Errors Check :"
        + runtime.candy("Color", "green", " OK ")
        + runtime.candy("Emoj", "good")
    )


def checkpoint_or_ok(
    runtime: GetInfoRuntime,
    chunk: Any,
    to_fix: list[Any],
    check_data: Any = None,
) -> None:
    if len(to_fix) > 0:
        if check_data is None:
            runtime.checkpoint(True, False, "GetInfo", chunk, to_fix)
        else:
            runtime.checkpoint(True, False, "GetInfo", chunk, to_fix, check_data)
    else:
        print_ok(runtime)


def checkpoint_only(
    runtime: GetInfoRuntime,
    chunk: Any,
    to_fix: list[Any],
    check_data: Any = None,
) -> None:
    if len(to_fix) > 0:
        if check_data is None:
            runtime.checkpoint(True, False, "GetInfo", chunk, to_fix)
        else:
            runtime.checkpoint(True, False, "GetInfo", chunk, to_fix, check_data)


def handle_png(runtime: GetInfoRuntime, chunk: Any, data: str, to_fix: list[Any]) -> None:
    runtime.candy(
        "Cowsay",
        " Well ..That's a start ..At least it looks like a png.",
        "good",
    )


def handle_ihdr(runtime: GetInfoRuntime, chunk: Any, data: str, to_fix: list[Any]) -> None:
    info = chunk_info.parse_ihdr(data, max_resolution=runtime.max_resolution())
    runtime.chunk_state.apply_ihdr(info)
    runtime.sync_legacy("ihdr")

    chunk_report.render_ihdr(info, runtime.emit, runtime.color)

    to_fix.extend(info.fixes)
    checkpoint_or_ok(runtime, chunk, to_fix)


def handle_idat(runtime: GetInfoRuntime, chunk: Any, data: str, to_fix: list[Any]) -> None:
    info = runtime.chunk_state.next_idat(data, runtime.raw_length)
    runtime.chunk_state.apply_idat(info)
    runtime.sync_legacy("idat")
    chunk_report.render_idat(info, runtime.emit, runtime.color)
    to_fix.extend(info.fixes)
    checkpoint_only(runtime, chunk, to_fix)


def handle_phys(runtime: GetInfoRuntime, chunk: Any, data: str, to_fix: list[Any]) -> None:
    info = chunk_info.parse_phys(data)
    runtime.set_legacy(pHYs_Y=info.y, pHYs_X=info.x, pHYs_Unit=info.unit)

    chunk_report.render_phys(info, runtime.emit, runtime.color, runtime.emoji)

    to_fix.extend(info.fixes)
    checkpoint_or_ok(runtime, chunk, to_fix)


def handle_bkgd(runtime: GetInfoRuntime, chunk: Any, data: str, to_fix: list[Any]) -> None:
    info = chunk_info.parse_bkgd(data, runtime.ihdr_color, runtime.ihdr_depth)
    runtime.set_legacy(
        bKGD_Gray=info.gray,
        bKGD_Red=info.red,
        bKGD_Green=info.green,
        bKGD_Blue=info.blue,
        bKGD_Index=info.index,
    )

    chunk_report.render_bkgd(info, runtime.emit, runtime.color)

    to_fix.extend(info.fixes)
    checkpoint_or_ok(runtime, chunk, to_fix)


def handle_plte(runtime: GetInfoRuntime, chunk: Any, data: str, to_fix: list[Any]) -> None:
    info = chunk_info.parse_plte(data, runtime.ihdr_depth)
    runtime.chunk_state.apply_plte(info)
    runtime.sync_legacy("plte")

    chunk_report.render_plte(
        runtime.chunk_state.plte_r,
        runtime.chunk_state.plte_g,
        runtime.chunk_state.plte_b,
        runtime.emit,
        runtime.color,
    )

    to_fix.extend(info.fixes)
    checkpoint_or_ok(runtime, chunk, to_fix)


def handle_splt(runtime: GetInfoRuntime, chunk: Any, data: str, to_fix: list[Any]) -> None:
    info = chunk_info.parse_splt(
        data,
        previous_names=tuple(runtime.chunk_state.splt_name),
    )
    runtime.chunk_state.apply_splt(info)
    runtime.sync_legacy("splt")

    chunk_report.render_splt(
        info,
        runtime.chunk_state.splt_red,
        runtime.chunk_state.splt_green,
        runtime.chunk_state.splt_blue,
        runtime.chunk_state.splt_alpha,
        runtime.chunk_state.splt_freq,
        runtime.emit,
        runtime.color,
    )

    to_fix.extend(info.fixes)
    checkpoint_or_ok(runtime, chunk, to_fix, data)


def handle_hist(runtime: GetInfoRuntime, chunk: Any, data: str, to_fix: list[Any]) -> None:
    info = chunk_info.parse_hist(
        data,
        has_plte=b"PLTE" in runtime.chunks_history,
        has_splt=b"sPLT" in runtime.chunks_history,
        plte_entries=runtime.chunk_state.plte_entry_count(),
        splt_entries=runtime.chunk_state.splt_entry_count(),
    )
    entries = list(info.entries)
    runtime.set_legacy(hIST=entries)
    chunk_report.render_hist(entries, runtime.emit, runtime.color)

    to_fix.extend(info.fixes)
    checkpoint_or_ok(runtime, chunk, to_fix, data)


def handle_time(runtime: GetInfoRuntime, chunk: Any, data: str, to_fix: list[Any]) -> None:
    current_year = datetime.now().year
    info = chunk_info.parse_time(data, current_year=current_year)
    runtime.set_legacy(
        tIME_Yr=info.year,
        tIME_Mth=info.month,
        tIME_Day=info.day,
        tIME_Hr=info.hour,
        tIME_Min=info.minute,
        tIME_Sec=info.second,
    )
    chunk_report.render_time(
        info,
        current_year,
        runtime.emit,
        runtime.color,
        runtime.emoji,
    )
    to_fix.extend(info.fixes)
    checkpoint_or_ok(runtime, chunk, to_fix)


def handle_trns(runtime: GetInfoRuntime, chunk: Any, data: str, to_fix: list[Any]) -> None:
    info = chunk_info.parse_trns(
        data,
        runtime.ihdr_color,
        has_plte=b"PLTE" in runtime.chunks_history,
        has_splt=b"sPLT" in runtime.chunks_history,
        plte_entries=len(runtime.chunk_state.plte_r),
        splt_entries=len(runtime.chunk_state.splt_red),
    )
    runtime.set_legacy(
        tRNS_Gray=info.gray,
        tRNS_TrueR=info.true_r,
        tRNS_TrueG=info.true_g,
        tRNS_TrueB=info.true_b,
    )
    runtime.chunk_state.apply_trns(info)
    runtime.sync_legacy("trns")

    chunk_report.render_trns(info, runtime.emit, runtime.color)

    to_fix.extend(info.fixes)
    checkpoint_or_ok(runtime, chunk, to_fix)


def handle_srgb(runtime: GetInfoRuntime, chunk: Any, data: str, to_fix: list[Any]) -> None:
    has_chrm = b"cHRM" in runtime.chunks_history
    info = chunk_info.parse_srgb(data, has_chrm=has_chrm)
    runtime.set_legacy(sRGB=info.value)
    chunk_report.render_srgb(
        info,
        has_chrm,
        runtime.emit,
        runtime.color,
        runtime.emoji,
    )
    to_fix.extend(info.fixes)

    checkpoint_or_ok(runtime, chunk, to_fix)


def handle_chrm(runtime: GetInfoRuntime, chunk: Any, data: str, to_fix: list[Any]) -> None:
    has_srgb_or_iccp = b"sRGB" in runtime.chunks_history or b"iCCP" in runtime.chunks_history
    info = chunk_info.parse_chrm(data, has_srgb_or_iccp=has_srgb_or_iccp)
    runtime.chunk_state.apply_chrm(info)
    runtime.sync_legacy("chrm")
    chunk_report.render_chrm(
        info,
        has_srgb_or_iccp,
        runtime.emit,
        runtime.color,
        runtime.emoji,
    )
    to_fix.extend(info.fixes)

    checkpoint_or_ok(runtime, chunk, to_fix)


def handle_gama(runtime: GetInfoRuntime, chunk: Any, data: str, to_fix: list[Any]) -> None:
    info = chunk_info.parse_gama(data)
    runtime.set_legacy(gAMA=info.value)
    chunk_report.render_gama(info, runtime.emit, runtime.color)
    to_fix.extend(info.fixes)
    checkpoint_only(runtime, chunk, to_fix)


def handle_iccp(runtime: GetInfoRuntime, chunk: Any, data: str, to_fix: list[Any]) -> None:
    info = chunk_info.parse_iccp(
        data,
        raw_length_hex=runtime.orig_cl,
        has_chrm=b"cHRM" in runtime.chunks_history,
    )
    runtime.chunk_state.apply_iccp(info)
    runtime.sync_legacy("iccp")

    chunk_report.render_iccp(
        info,
        b"cHRM" in runtime.chunks_history,
        runtime.emit,
        runtime.color,
        runtime.emoji,
    )
    to_fix.extend(info.fixes)

    checkpoint_or_ok(runtime, chunk, to_fix)


def handle_sbit(runtime: GetInfoRuntime, chunk: Any, data: str, to_fix: list[Any]) -> None:
    info = chunk_info.parse_sbit(data, runtime.ihdr_color, runtime.ihdr_depth)
    runtime.chunk_state.apply_sbit(info)
    runtime.sync_legacy("sbit")

    chunk_report.render_sbit(info, runtime.emit, runtime.color)

    to_fix.extend(info.fixes)
    checkpoint_or_ok(runtime, chunk, to_fix)


def handle_offs(runtime: GetInfoRuntime, chunk: Any, data: str, to_fix: list[Any]) -> None:
    info = chunk_info.parse_offs(data)
    runtime.chunk_state.apply_offs(info)

    chunk_report.render_offs(info, runtime.emit, runtime.color, runtime.emoji)
    to_fix.extend(info.fixes)
    checkpoint_or_ok(runtime, chunk, to_fix)


def handle_pcal(runtime: GetInfoRuntime, chunk: Any, data: str, to_fix: list[Any]) -> None:
    info = chunk_info.parse_pcal(data)
    runtime.chunk_state.apply_pcal(info)
    runtime.sync_legacy("pcal")

    chunk_report.render_pcal(info, runtime.emit, runtime.color)

    to_fix.extend(info.fixes)
    checkpoint_only(runtime, chunk, to_fix)


def handle_gifg(runtime: GetInfoRuntime, chunk: Any, data: str, to_fix: list[Any]) -> None:
    info = chunk_info.parse_gifg(data)
    runtime.chunk_state.apply_gifg(info)
    runtime.sync_legacy("gifg")

    chunk_report.render_gifg(info, runtime.emit, runtime.color)
    to_fix.extend(info.fixes)

    checkpoint_only(runtime, chunk, to_fix)


def handle_gifx(runtime: GetInfoRuntime, chunk: Any, data: str, to_fix: list[Any]) -> None:
    info = chunk_info.parse_gifx(data)
    runtime.chunk_state.apply_gifx(info)
    runtime.sync_legacy("gifx")

    chunk_report.render_gifx(info, runtime.emit, runtime.color)
    to_fix.extend(info.fixes)

    checkpoint_only(runtime, chunk, to_fix)


def handle_ster(runtime: GetInfoRuntime, chunk: Any, data: str, to_fix: list[Any]) -> None:
    info = chunk_info.parse_ster(data)
    runtime.chunk_state.apply_ster(info)
    runtime.sync_legacy("ster")

    chunk_report.render_ster(info, runtime.emit, runtime.color)
    to_fix.extend(info.fixes)

    checkpoint_only(runtime, chunk, to_fix)


def handle_text(runtime: GetInfoRuntime, chunk: Any, data: str, to_fix: list[Any]) -> None:
    info = chunk_info.parse_text(data)
    runtime.chunk_state.apply_text(info)
    runtime.sync_legacy("text")

    chunk_report.render_text(info, runtime.emit, runtime.color)

    to_fix.extend(info.fixes)
    checkpoint_only(runtime, chunk, to_fix)


def handle_ztxt(runtime: GetInfoRuntime, chunk: Any, data: str, to_fix: list[Any]) -> None:
    info = chunk_info.parse_ztxt(data)
    runtime.chunk_state.apply_ztxt(info)
    runtime.sync_legacy("ztxt")

    chunk_report.render_ztxt(info, runtime.emit, runtime.color)

    to_fix.extend(info.fixes)
    checkpoint_only(runtime, chunk, to_fix)


def handle_itxt(runtime: GetInfoRuntime, chunk: Any, data: str, to_fix: list[Any]) -> None:
    info = chunk_info.parse_itxt(data)
    runtime.chunk_state.apply_itxt(info)
    runtime.sync_legacy("itxt")

    chunk_report.render_itxt(info, runtime.emit, runtime.color)

    to_fix.extend(info.fixes)
    checkpoint_only(runtime, chunk, to_fix)


def handle_exif(runtime: GetInfoRuntime, chunk: Any, data: str, to_fix: list[Any]) -> None:
    info = chunk_info.parse_exif(data)
    runtime.chunk_state.apply_exif(info)
    runtime.sync_legacy("exif")

    chunk_report.render_exif(info, runtime.emit, runtime.color)
    to_fix.extend(info.fixes)

    checkpoint_only(runtime, chunk, to_fix)


def handle_spal(runtime: GetInfoRuntime, chunk: Any, data: str, to_fix: list[Any]) -> None:
    info = chunk_info.parse_spal(data)
    chunk_report.render_spal(info, runtime.emit, runtime.color)
    to_fix.extend(info.fixes)

    checkpoint_only(runtime, chunk, to_fix)


GETINFO_HANDLERS = {
    b"PNG": handle_png,
    b"IHDR": handle_ihdr,
    b"IDAT": handle_idat,
    b"pHYs": handle_phys,
    b"bKGD": handle_bkgd,
    b"PLTE": handle_plte,
    b"sPLT": handle_splt,
    b"hIST": handle_hist,
    b"tIME": handle_time,
    b"tRNS": handle_trns,
    b"sRGB": handle_srgb,
    b"cHRM": handle_chrm,
    b"gAMA": handle_gama,
    b"iCCP": handle_iccp,
    b"sBIT": handle_sbit,
    b"oFFs": handle_offs,
    b"pCAL": handle_pcal,
    b"gIFg": handle_gifg,
    b"gIFx": handle_gifx,
    b"sTER": handle_ster,
    b"tEXt": handle_text,
    b"zTXt": handle_ztxt,
    b"iTXt": handle_itxt,
    b"eXIf": handle_exif,
    b"spAL": handle_spal,
}


def run_getinfo(runtime: GetInfoRuntime, chunk: Any, data: str) -> list[Any]:
    to_fix: list[Any] = []
    runtime.candy("Title", "Getting infos about:", runtime.candy("Color", "white", str(chunk)))

    handler = GETINFO_HANDLERS.get(chunk)
    if handler is not None:
        handler(runtime, chunk, data, to_fix)

    if chunk in runtime.private_chunks:
        runtime.emit("-Private Chunk")
        if len(to_fix) > 0:
            runtime.checkpoint(True, False, "GetInfo", chunk, to_fix)

    if chunk not in runtime.allchunks:
        runtime.emit("-%s" % runtime.candy("Color", "red", "Unknown Chunk."))
        if len(to_fix) > 0:
            runtime.checkpoint(True, False, "GetInfo", chunk, to_fix)

    return to_fix
