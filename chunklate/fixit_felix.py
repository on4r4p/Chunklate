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
LibpngErrorAction = Literal["not_enough_image_data", "ask_relics", "skip", "save_existing_solution"]
WrongCrcAction = Literal["already_in_cornucopia", "ask_easy_crc_fix", "ask_other_errors_first"]
WrongChunkNameAction = Literal["ask_length_probe", "ask_bruteforce", "save_existing_solution"]
NoNextChunkAction = Literal[
    "false_positive_iend",
    "wrong_iend_length",
    "append_missing_iend",
    "ask_length_probe",
]
AutomaticRepairHandler = Literal[
    "color_profile_cleanup",
    "plte_cleanup",
    "known_chunk_type_case",
    "unknown_private_critical_removal",
    "missing_chunk_data_byte",
    "ihdr_rebuild",
]


AUTOMATIC_REPAIR_ORDER: tuple[AutomaticRepairHandler, ...] = (
    "color_profile_cleanup",
    "plte_cleanup",
    "known_chunk_type_case",
    "unknown_private_critical_removal",
    "missing_chunk_data_byte",
    "ihdr_rebuild",
)


@dataclass(frozen=True)
class FixItFelixRoute:
    handler: FixItFelixHandler
    finding: object


@dataclass(frozen=True)
class FalsePositiveFix:
    finding: object
    note: str


@dataclass(frozen=True)
class LibpngErrorDecision:
    action: LibpngErrorAction
    finding: object


@dataclass(frozen=True)
class WrongCrcDecision:
    action: WrongCrcAction
    finding: object
    other_error_count: int


@dataclass(frozen=True)
class WrongChunkNameDecision:
    action: WrongChunkNameAction
    finding: object
    bad_crc: bool


@dataclass(frozen=True)
class NoNextChunkDecision:
    action: NoNextChunkAction
    current_chunk: object
    chunk_type: object
    chunk_length: object


@dataclass(frozen=True)
class AppliedRepair:
    data_hex: str
    note: str
    save_suffix: str


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


def gama_zero_false_positive(finding: object) -> FalsePositiveFix:
    return FalsePositiveFix(
        finding=finding,
        note="-Found False-Positive :[Error:-%s]." % str(finding),
    )


def libpng_error_decision(
    finding: object,
    *,
    solved: bool,
    skip_bad_libpng: bool,
) -> LibpngErrorDecision:
    if solved:
        return LibpngErrorDecision("save_existing_solution", finding)
    if "Not enough image data" in str(finding):
        return LibpngErrorDecision("not_enough_image_data", finding)
    if skip_bad_libpng:
        return LibpngErrorDecision("skip", finding)
    return LibpngErrorDecision("ask_relics", finding)


def wrong_crc_decision(
    finding: object,
    *,
    solved: bool,
    pandora_box_len: int,
) -> WrongCrcDecision:
    if solved:
        return WrongCrcDecision("already_in_cornucopia", finding, 0)
    if pandora_box_len <= 1:
        return WrongCrcDecision("ask_easy_crc_fix", finding, 0)
    return WrongCrcDecision("ask_other_errors_first", finding, pandora_box_len - 1)


def wrong_chunk_name_decision(
    finding: object,
    *,
    solved: bool,
    bad_crc: bool,
) -> WrongChunkNameDecision:
    if solved:
        return WrongChunkNameDecision("save_existing_solution", finding, bad_crc)
    if "and length is not the same than before." in str(finding):
        return WrongChunkNameDecision("ask_length_probe", finding, bad_crc)
    return WrongChunkNameDecision("ask_bruteforce", finding, bad_crc)


def no_next_chunk_decision(
    *,
    current_chunk: object,
    chunk_type: object,
    chunk_length: object,
    bad_critical: bool,
) -> NoNextChunkDecision:
    if current_chunk == b"IEND" and int(chunk_length) == 0:
        return NoNextChunkDecision("false_positive_iend", current_chunk, chunk_type, chunk_length)
    if chunk_type == b"IEND":
        return NoNextChunkDecision("wrong_iend_length", current_chunk, chunk_type, chunk_length)
    if bad_critical:
        return NoNextChunkDecision("append_missing_iend", current_chunk, chunk_type, chunk_length)
    return NoNextChunkDecision("ask_length_probe", current_chunk, chunk_type, chunk_length)


def applied_repair(repair: Any) -> AppliedRepair:
    return AppliedRepair(
        data_hex=repair.data.hex(),
        note="-FixItFelix:%s." % repair.strategy,
        save_suffix="-%s." % repair.strategy,
    )


def automatic_repair_order() -> tuple[AutomaticRepairHandler, ...]:
    return AUTOMATIC_REPAIR_ORDER


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
