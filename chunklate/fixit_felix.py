from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from .png import (
    repair_color_profile_chunks,
    repair_empty_plte,
    repair_ihdr,
    repair_known_chunk_type_case,
    repair_missing_chunk_data_byte,
    repair_unknown_private_critical_chunks,
)


def has_finding(findings: Iterable[object], *needles: str) -> bool:
    return any(all(needle in str(finding) for needle in needles) for finding in findings)


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
