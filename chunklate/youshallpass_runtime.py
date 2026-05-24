from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from . import chunk_info


LegacyCall = Callable[..., Any]


@dataclass(frozen=True)
class YouShallPassRuntime:
    chunk_state: Any
    sync_state: LegacyCall
    chunks_history: tuple[Any, ...]
    orig_cl: str


def passes(info: Any) -> bool:
    return len(info.fixes) == 0


def validate_bkgd(runtime: YouShallPassRuntime, data: str) -> bool:
    runtime.sync_state("ihdr")
    return passes(
        chunk_info.parse_bkgd(
            data,
            runtime.chunk_state.ihdr_color,
            runtime.chunk_state.ihdr_depth,
        )
    )


def validate_plte(runtime: YouShallPassRuntime, data: str) -> bool:
    runtime.sync_state("ihdr")
    return passes(chunk_info.parse_plte(data, runtime.chunk_state.ihdr_depth))


def validate_splt(runtime: YouShallPassRuntime, data: str) -> bool:
    runtime.sync_state("splt")
    return passes(
        chunk_info.parse_splt(
            data,
            previous_names=tuple(runtime.chunk_state.splt_name),
        )
    )


def validate_hist(runtime: YouShallPassRuntime, data: str) -> bool:
    runtime.sync_state(("plte", "splt"))
    return passes(
        chunk_info.parse_hist(
            data,
            has_plte=b"PLTE" in runtime.chunks_history,
            has_splt=b"sPLT" in runtime.chunks_history,
            plte_entries=runtime.chunk_state.plte_entry_count(),
            splt_entries=runtime.chunk_state.splt_entry_count(),
        )
    )


def validate_trns(runtime: YouShallPassRuntime, data: str) -> bool:
    runtime.sync_state(("ihdr", "plte", "splt"))
    return passes(
        chunk_info.parse_trns(
            data,
            runtime.chunk_state.ihdr_color,
            has_plte=b"PLTE" in runtime.chunks_history,
            has_splt=b"sPLT" in runtime.chunks_history,
            plte_entries=len(runtime.chunk_state.plte_r),
            splt_entries=len(runtime.chunk_state.splt_red),
        )
    )


def validate_sbit(runtime: YouShallPassRuntime, data: str) -> bool:
    runtime.sync_state("ihdr")
    return passes(
        chunk_info.parse_sbit(
            data,
            runtime.chunk_state.ihdr_color,
            runtime.chunk_state.ihdr_depth,
        )
    )


def validate_ihdr(runtime: YouShallPassRuntime, data: str) -> bool:
    return passes(chunk_info.parse_ihdr(data))


def validate_phys(runtime: YouShallPassRuntime, data: str) -> bool:
    return passes(chunk_info.parse_phys(data))


def validate_time(runtime: YouShallPassRuntime, data: str) -> bool:
    return passes(chunk_info.parse_time(data))


def validate_srgb(runtime: YouShallPassRuntime, data: str) -> bool:
    return passes(
        chunk_info.parse_srgb(data, has_chrm=b"cHRM" in runtime.chunks_history)
    )


def validate_chrm(runtime: YouShallPassRuntime, data: str) -> bool:
    return passes(
        chunk_info.parse_chrm(
            data,
            has_srgb_or_iccp=b"sRGB" in runtime.chunks_history
            or b"iCCP" in runtime.chunks_history,
        )
    )


def validate_gama(runtime: YouShallPassRuntime, data: str) -> bool:
    return passes(chunk_info.parse_gama(data))


def validate_iccp(runtime: YouShallPassRuntime, data: str) -> bool:
    return passes(
        chunk_info.parse_iccp(
            data,
            raw_length_hex=runtime.orig_cl,
            has_chrm=b"cHRM" in runtime.chunks_history,
        )
    )


def validate_offs(runtime: YouShallPassRuntime, data: str) -> bool:
    return passes(chunk_info.parse_offs(data))


def validate_pcal(runtime: YouShallPassRuntime, data: str) -> bool:
    return passes(chunk_info.parse_pcal(data))


def validate_gifg(runtime: YouShallPassRuntime, data: str) -> bool:
    return passes(chunk_info.parse_gifg(data))


def validate_gifx(runtime: YouShallPassRuntime, data: str) -> bool:
    return passes(chunk_info.parse_gifx(data))


def validate_ster(runtime: YouShallPassRuntime, data: str) -> bool:
    return passes(chunk_info.parse_ster(data))


def validate_text(runtime: YouShallPassRuntime, data: str) -> bool:
    return passes(chunk_info.parse_text(data))


def validate_ztxt(runtime: YouShallPassRuntime, data: str) -> bool:
    return passes(chunk_info.parse_ztxt(data))


def validate_itxt(runtime: YouShallPassRuntime, data: str) -> bool:
    return passes(chunk_info.parse_itxt(data))


def validate_exif(runtime: YouShallPassRuntime, data: str) -> bool:
    return passes(chunk_info.parse_exif(data))


YOUSHALLPASS_VALIDATORS = {
    b"IHDR": validate_ihdr,
    b"pHYs": validate_phys,
    b"bKGD": validate_bkgd,
    b"PLTE": validate_plte,
    b"sPLT": validate_splt,
    b"hIST": validate_hist,
    b"tIME": validate_time,
    b"tRNS": validate_trns,
    b"sRGB": validate_srgb,
    b"cHRM": validate_chrm,
    b"gAMA": validate_gama,
    b"iCCP": validate_iccp,
    b"sBIT": validate_sbit,
    b"oFFs": validate_offs,
    b"pCAL": validate_pcal,
    b"gIFg": validate_gifg,
    b"gIFx": validate_gifx,
    b"sTER": validate_ster,
    b"tEXt": validate_text,
    b"zTXt": validate_ztxt,
    b"iTXt": validate_itxt,
    b"eXIf": validate_exif,
}


def youshallpass(runtime: YouShallPassRuntime, chunk: Any, data: str) -> bool:
    validator = YOUSHALLPASS_VALIDATORS.get(chunk)
    if validator is not None:
        return validator(runtime, data)

    return True
