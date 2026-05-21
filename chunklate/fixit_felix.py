from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any
from typing import Literal

from .png import (
    repair_color_profile_chunks,
    repair_empty_plte,
    repair_ihdr,
    repair_known_chunk_type_case,
    repair_missing_chunk_data_byte,
    repair_unknown_private_critical_chunks,
)


FixItFelixHandler = Literal[
    "wrong_crc",
    "libpng_error",
    "wrong_chunk_name",
    "no_next_chunk",
    "gama_zero",
    "critical_miss",
]


@dataclass(frozen=True)
class FixItFelixRoute:
    handler: FixItFelixHandler
    finding: object


def has_finding(findings: Iterable[object], *needles: str) -> bool:
    return any(all(needle in str(finding) for needle in needles) for finding in findings)


def route_finding(finding: object, *, skip_bad_crc: bool) -> FixItFelixRoute:
    text = str(finding)
    if "Wrong Crc" in text and not skip_bad_crc:
        return FixItFelixRoute("wrong_crc", finding)
    if "libpng error:" in text:
        return FixItFelixRoute("libpng_error", finding)
    if "has Wrong Chunk name at offset:" in text:
        return FixItFelixRoute("wrong_chunk_name", finding)
    if "No NextChunk" in text:
        return FixItFelixRoute("no_next_chunk", finding)
    if "gAMA Chunk of 0 is Useless" in text:
        return FixItFelixRoute("gama_zero", finding)
    return FixItFelixRoute("critical_miss", finding)


def color_profile_cleanup(data: bytes, findings: Iterable[object]) -> Any | None:
    remove_zero_gama = has_finding(findings, "gAMA Chunk of 0 is Useless")
    remove_known_bad_srgb_iccp = has_finding(findings, "known incorrect sRGB profile")
    if not remove_zero_gama and not remove_known_bad_srgb_iccp:
        return None

    return repair_color_profile_chunks(
        data,
        remove_zero_gama=remove_zero_gama,
        remove_known_bad_srgb_iccp=remove_known_bad_srgb_iccp,
    )


def plte_cleanup(
    data: bytes,
    findings: Iterable[object],
    *,
    auto: bool,
    nodialogue: bool,
    max_saves: int | None,
) -> Any | None:
    if not (auto or nodialogue or max_saves is not None):
        return None

    if not has_finding(findings, "PLTE"):
        return None

    return repair_empty_plte(data)


def missing_chunk_data_byte(data: bytes, findings: Iterable[object]) -> Any | None:
    if not (has_finding(findings, "Wrong Crc") or has_finding(findings, "No NextChunk")):
        return None

    return repair_missing_chunk_data_byte(data)


def known_chunk_type_case(data: bytes, findings: Iterable[object], known_chunk_types: Iterable[bytes]) -> Any | None:
    if not has_finding(findings, "Wrong Ancillary in known Chunk name"):
        return None

    return repair_known_chunk_type_case(data, known_chunk_types)


def unknown_private_critical_removal(data: bytes, known_chunk_types: Iterable[bytes]) -> Any | None:
    return repair_unknown_private_critical_chunks(data, known_chunk_types)


def ihdr_rebuild(data: bytes, findings: Iterable[object]) -> Any | None:
    if not (
        has_finding(findings, "IHDR", "GetInfo")
        or has_finding(findings, "IHDR", "Wrong Crc")
    ):
        return None

    return repair_ihdr(data)
