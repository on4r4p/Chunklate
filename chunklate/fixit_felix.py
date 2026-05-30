from __future__ import annotations

from collections.abc import Iterable
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from typing import Callable
from typing import Literal

from .png import (
    repair_bkgd_length,
    repair_chrm_length,
    repair_color_profile_chunks,
    repair_duplicate_singleton_chunks,
    repair_empty_plte,
    repair_gama_length,
    repair_gifg_length,
    repair_hist_length,
    repair_ihdr,
    repair_indexed_plte,
    repair_itxt_compression_flag,
    repair_itxt_keyword_length,
    repair_itxt_compression_method,
    repair_known_chunk_type_case,
    repair_missing_chunk_data_byte,
    repair_offs_length,
    repair_phys_length,
    repair_sbit_length,
    repair_srgb_length,
    repair_ster_length,
    repair_time_length,
    repair_trns_length,
    repair_unknown_private_critical_chunks,
)
from .idat import rebuild_partial_idat_blackfill


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
GamaZeroAction = Literal["discard_false_positive"]
CriticalMissAction = Literal["pause_debug", "continue"]
NoNextChunkAction = Literal[
    "false_positive_iend",
    "wrong_iend_length",
    "append_missing_iend",
    "ask_length_probe",
]
NoNextFalsePositiveIendAction = Literal[
    "libpng_check",
    "the_good_place",
    "write_clean_iend_cut",
    "end_not_regular_iend",
    "continue",
]
NoNextAppendIendAction = Literal[
    "dummy_at_crc_tail",
    "dummy_at_eof",
    "end_iend_inside_exceeding",
]
AutomaticRepairHandler = Literal[
    "color_profile_cleanup",
    "duplicate_singleton_cleanup",
    "plte_cleanup",
    "gama_length",
    "gifg_length",
    "hist_length",
    "chrm_length",
    "bkgd_length",
    "itxt_keyword_length",
    "itxt_compression_flag",
    "itxt_compression_method",
    "offs_length",
    "phys_length",
    "time_length",
    "trns_length",
    "sbit_length",
    "srgb_length",
    "ster_length",
    "known_chunk_type_case",
    "unknown_private_critical_removal",
    "missing_chunk_data_byte",
    "ihdr_rebuild",
    "partial_idat_blackfill",
]
FixItFelixWorkKind = Literal["automatic_repair", "finding"]


AUTOMATIC_REPAIR_ORDER: tuple[AutomaticRepairHandler, ...] = (
    "color_profile_cleanup",
    "duplicate_singleton_cleanup",
    "plte_cleanup",
    "gama_length",
    "gifg_length",
    "hist_length",
    "chrm_length",
    "bkgd_length",
    "itxt_keyword_length",
    "itxt_compression_flag",
    "itxt_compression_method",
    "offs_length",
    "phys_length",
    "time_length",
    "trns_length",
    "sbit_length",
    "srgb_length",
    "ster_length",
    "known_chunk_type_case",
    "unknown_private_critical_removal",
    "missing_chunk_data_byte",
    "ihdr_rebuild",
    "partial_idat_blackfill",
)
GOOD_IEND_HEX = "0000000049454e44ae426082"
DEBUG_FLAG_NAMES: tuple[str, ...] = (
    "EOF",
    "Bad_Current_Name",
    "Bad_Ancillary",
    "Bad_No_Next_Chunk",
    "Bad_Next_Name",
    "Bad_Next_Ancillary",
    "Bad_Length",
    "Bad_Infos",
    "Bad_Crc",
    "Bad_Critical",
    "Bad_Missplaced",
    "Bad_Libpng",
    "Skip_Bad_Current_Name",
    "Skip_Bad_Ancillary",
    "Skip_Bad_No_Next_Chunk",
    "Skip_Bad_Next_Name",
    "Skip_Bad_Next_Ancillary",
    "Skip_Bad_Length",
    "Skip_Bad_Infos",
    "Skip_Bad_Crc",
    "Skip_Bad_Critical",
    "Skip_Bad_Missplaced",
    "Skip_Bad_Libpng",
)


@dataclass(frozen=True)
class FixItFelixRoute:
    handler: FixItFelixHandler
    finding: object


@dataclass(frozen=True)
class FixItFelixWorkItem:
    kind: FixItFelixWorkKind
    handler: AutomaticRepairHandler | FixItFelixHandler
    finding: object | None = None


@dataclass(frozen=True)
class FixItFelixRuntime:
    try_automatic_repair: Callable[[AutomaticRepairHandler], Any]
    apply_finding_work_item: Callable[[FixItFelixWorkItem, str, int, Any], tuple[bool, Any]]


@dataclass(frozen=True)
class FixItFelixRunResult:
    should_return: bool
    result: Any = None


ActionHandler = Callable[..., Any]
FindingWorkItemHandler = Callable[[FixItFelixWorkItem, str, int, Any], tuple[bool, Any]]


@dataclass(frozen=True)
class FalsePositiveFix:
    finding: object
    note: str


@dataclass(frozen=True)
class GamaZeroDecision:
    action: GamaZeroAction
    false_positive: FalsePositiveFix


@dataclass(frozen=True)
class LibpngErrorDecision:
    action: LibpngErrorAction
    finding: object


@dataclass(frozen=True)
class CriticalMissDecision:
    action: CriticalMissAction
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
class NoNextFalsePositiveIendDecision:
    action: NoNextFalsePositiveIendAction
    cut_hex: str | None = None


@dataclass(frozen=True)
class NoNextAppendIendDecision:
    action: NoNextAppendIendAction
    exceeding: str


@dataclass(frozen=True)
class AppliedRepair:
    data_hex: str
    note: str
    save_suffix: str


def repair_metadata_note(repair: Any) -> str:
    width = getattr(repair, "width", None)
    height = getattr(repair, "height", None)
    bit_depth = getattr(repair, "bit_depth", None)
    color_type = getattr(repair, "color_type", None)

    parts = []
    if None not in (width, height, bit_depth, color_type):
        parts.append(
            "Selected IHDR %sx%s, bit depth %s, color type %s"
            % (width, height, bit_depth, color_type)
        )

    strict_candidate_count = getattr(repair, "strict_candidate_count", 0)
    if strict_candidate_count:
        parts.append("strict candidates: %s" % strict_candidate_count)

    selection_score = getattr(repair, "selection_score", None)
    if selection_score is not None:
        parts.append("selection score: %s" % (selection_score,))

    if not parts:
        return ""

    return " ".join("-FixItFelix:%s." % part for part in parts)


def repair_note(repair: Any) -> str:
    note = "-FixItFelix:%s." % repair.strategy
    metadata = repair_metadata_note(repair)
    if metadata:
        note += "\n" + metadata
    return note


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


def effective_pandora_box_len(findings: Iterable[object], *, bad_next_name: bool) -> int:
    length = len(findings)
    if bad_next_name is False:
        return length
    return length - 1


def repair_work_items(findings: Iterable[object], *, skip_bad_crc: bool) -> tuple[FixItFelixWorkItem, ...]:
    items: list[FixItFelixWorkItem] = [
        FixItFelixWorkItem("automatic_repair", handler)
        for handler in automatic_repair_order()
    ]
    items.extend(
        FixItFelixWorkItem(
            "finding",
            route_finding(finding, skip_bad_crc=skip_bad_crc).handler,
            finding,
        )
        for finding in findings
    )
    return tuple(items)


def debug_flag_values(values: Mapping[str, Any]) -> dict[str, Any]:
    return {name: values[name] for name in DEBUG_FLAG_NAMES}


def debug_report_lines(
    flags: Mapping[str, Any],
    pandora_box: Mapping[Any, Mapping[Any, Any]],
    cornucopia: Mapping[Any, Mapping[Any, Any]],
) -> tuple[str, ...]:
    lines = ["%s:%s" % (name, flags[name]) for name in DEBUG_FLAG_NAMES]
    lines.extend(("", "PandoraBox:\n%s" % pandora_box))

    for key in pandora_box:
        lines.append("Len PandoraBox:%s" % len(pandora_box))
        for toolkey, keyvalue in pandora_box[key].items():
            lines.append("PandoraBox toolkey:%s" % toolkey)
            lines.append("PandoraBox keyvalue:%s" % keyvalue)

    lines.extend(("", "Cornucopia:"))
    for key in cornucopia:
        lines.append("Len Cornucopia:%s" % len(cornucopia))
        for toolkey, keyvalue in cornucopia[key].items():
            lines.append("Cornucopia toolkey:%s" % toolkey)
            lines.append("Cornucopia keyvalue:%s" % keyvalue)

    return tuple(lines)


def emit_debug_report(
    emit: Callable[[str], Any],
    values: Mapping[str, Any],
    pandora_box: Mapping[Any, Mapping[Any, Any]],
    cornucopia: Mapping[Any, Mapping[Any, Any]],
) -> None:
    for line in debug_report_lines(
        debug_flag_values(values),
        pandora_box,
        cornucopia,
    ):
        emit(line)


def run_repair_work_items(
    runtime: FixItFelixRuntime,
    work_items: Iterable[FixItFelixWorkItem],
    *,
    chkd: str,
    pandora_box_len: int,
    chunk: Any,
) -> FixItFelixRunResult:
    for work_item in work_items:
        if work_item.kind == "automatic_repair":
            repair_result = runtime.try_automatic_repair(work_item.handler)
            if repair_result is not None:
                return FixItFelixRunResult(True, repair_result)
            continue

        should_return, result = runtime.apply_finding_work_item(
            work_item,
            chkd,
            pandora_box_len,
            chunk,
        )
        if should_return:
            return FixItFelixRunResult(True, result)

    return FixItFelixRunResult(False)


def run_repair_pipeline(
    runtime: FixItFelixRuntime,
    findings: Iterable[object],
    *,
    skip_bad_crc: bool,
    bad_next_name: bool,
    chkd: str,
    chunk: Any,
) -> FixItFelixRunResult:
    return run_repair_work_items(
        runtime,
        repair_work_items(
            findings,
            skip_bad_crc=skip_bad_crc,
        ),
        chkd=chkd,
        pandora_box_len=effective_pandora_box_len(
            findings,
            bad_next_name=bad_next_name,
        ),
        chunk=chunk,
    )


def dispatch_action(
    handlers: Mapping[str, ActionHandler],
    action: str,
    error_label: str,
    *args: Any,
) -> Any:
    handler = handlers.get(action)
    if handler is None:
        raise ValueError("Unknown %s: %s" % (error_label, action))
    return handler(*args)


def dispatch_finding_work_item(
    handlers: Mapping[str, FindingWorkItemHandler],
    work_item: FixItFelixWorkItem,
    chkd: str,
    pandora_box_len: int,
    chunk: Any,
) -> tuple[bool, Any]:
    return dispatch_action(
        handlers,
        work_item.handler,
        "FixItFelix finding handler",
        work_item,
        chkd,
        pandora_box_len,
        chunk,
    )


def tool_prefix_for_chunk(chunk: Any) -> str:
    try:
        return chunk.decode(errors="ignore") + "_Tool_"
    except AttributeError:
        return chunk + "_Tool_"


def gama_zero_false_positive(finding: object) -> FalsePositiveFix:
    return FalsePositiveFix(
        finding=finding,
        note="-Found False-Positive :[Error:-%s]." % str(finding),
    )


def gama_zero_decision(finding: object) -> GamaZeroDecision:
    return GamaZeroDecision(
        action="discard_false_positive",
        false_positive=gama_zero_false_positive(finding),
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


def critical_miss_decision(
    finding: object,
    *,
    debug: bool,
    pause_debug: bool,
) -> CriticalMissDecision:
    if debug is True and pause_debug is True:
        return CriticalMissDecision("pause_debug", finding)
    return CriticalMissDecision("continue", finding)


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


def no_next_false_positive_iend_decision(
    data_hex: str,
    *,
    bad_missplaced: bool,
    has_missplaced_finding: bool,
    good_ending: str = GOOD_IEND_HEX,
) -> NoNextFalsePositiveIendDecision:
    if data_hex[-len(good_ending):] == good_ending:
        if bad_missplaced is False:
            return NoNextFalsePositiveIendDecision("libpng_check")
        if has_missplaced_finding:
            return NoNextFalsePositiveIendDecision("the_good_place")
        return NoNextFalsePositiveIendDecision("continue")

    if good_ending in data_hex:
        cut_here = data_hex.index(good_ending) + len(good_ending)
        return NoNextFalsePositiveIendDecision(
            "write_clean_iend_cut",
            cut_hex=data_hex[:cut_here],
        )

    return NoNextFalsePositiveIendDecision("end_not_regular_iend")


def no_next_crc_exceeding(data_hex: str, crc_offset: int) -> str:
    return data_hex[crc_offset + 8:]


def no_next_append_iend_decision(
    data_hex: str,
    *,
    crc_offset: int,
    good_ending: str = GOOD_IEND_HEX,
) -> NoNextAppendIendDecision:
    exceeding = no_next_crc_exceeding(data_hex, crc_offset)

    if len(exceeding) > len(good_ending):
        if good_ending in exceeding:
            return NoNextAppendIendDecision("end_iend_inside_exceeding", exceeding)
        return NoNextAppendIendDecision("dummy_at_crc_tail", exceeding)

    if exceeding.startswith(good_ending[:len(exceeding)]):
        return NoNextAppendIendDecision("dummy_at_eof", exceeding)

    return NoNextAppendIendDecision("dummy_at_crc_tail", exceeding)


def applied_repair(repair: Any) -> AppliedRepair:
    return AppliedRepair(
        data_hex=repair.data.hex(),
        note=repair_note(repair),
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


def duplicate_singleton_cleanup(data: bytes, findings: Iterable[object]) -> Any | None:
    if not (
        has_finding(findings, "Multiple")
        or has_finding(findings, "multiple", "chunks")
    ):
        return None

    return repair_duplicate_singleton_chunks(data)


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

    return repair_empty_plte(data) or repair_indexed_plte(data)


def bkgd_length(data: bytes, findings: Iterable[object]) -> Any | None:
    if not has_finding(findings, "bKGD length is not Valid"):
        return None

    return repair_bkgd_length(data)


def gama_length(data: bytes, findings: Iterable[object]) -> Any | None:
    if not has_finding(findings, "gAMA length is not Valid"):
        return None

    return repair_gama_length(data)


def gifg_length(data: bytes, findings: Iterable[object]) -> Any | None:
    if not has_finding(findings, "gIFg length is not Valid"):
        return None

    return repair_gifg_length(data)


def hist_length(data: bytes, findings: Iterable[object]) -> Any | None:
    if not (
        has_finding(findings, "hIST length is not Valid")
        or has_finding(findings, "Histogram frequencies entries must match PLTE entries number")
    ):
        return None

    return repair_hist_length(data)


def chrm_length(data: bytes, findings: Iterable[object]) -> Any | None:
    if not has_finding(findings, "cHRM length is not Valid"):
        return None

    return repair_chrm_length(data)


def itxt_compression_flag(data: bytes, findings: Iterable[object]) -> Any | None:
    if not has_finding(findings, "iTXt Compression Flag must be 0 or 1"):
        return None

    return repair_itxt_compression_flag(data)


def itxt_keyword_length(data: bytes, findings: Iterable[object]) -> Any | None:
    if not has_finding(findings, "iTXt Keyword length is not Valid"):
        return None

    return repair_itxt_keyword_length(data)


def itxt_compression_method(data: bytes, findings: Iterable[object]) -> Any | None:
    if not has_finding(findings, "iTXt Compression Method must be 0"):
        return None

    return repair_itxt_compression_method(data)


def offs_length(data: bytes, findings: Iterable[object]) -> Any | None:
    if not (
        has_finding(findings, "Wrong Offset unit")
        or has_finding(findings, "oFFs length is not Valid")
    ):
        return None

    return repair_offs_length(data)


def phys_length(data: bytes, findings: Iterable[object]) -> Any | None:
    if not (
        has_finding(findings, "Error pHYs U")
        or has_finding(findings, "pHYs length is not Valid")
        or has_finding(findings, "pHYs chunk length must be 9")
    ):
        return None

    return repair_phys_length(data)


def time_length(data: bytes, findings: Iterable[object]) -> Any | None:
    if not (
        has_finding(findings, "tIME length is not Valid")
        or has_finding(findings, "tIME Not enough bytes")
        or has_finding(findings, "tIME chunk length must be 7")
    ):
        return None

    return repair_time_length(data)


def trns_length(data: bytes, findings: Iterable[object]) -> Any | None:
    if not (
        has_finding(findings, "tRNS length is not Valid")
        or has_finding(findings, "tRNS Chunk Must not be empty")
        or has_finding(findings, "Error tRNS_")
        or has_finding(findings, "tRNS Alpha indexes palettes entries must not be superior")
        or has_finding(findings, "tRNS chunk length must")
        or has_finding(findings, "tRNS chunk is not allowed")
    ):
        return None

    return repair_trns_length(data)


def sbit_length(data: bytes, findings: Iterable[object]) -> Any | None:
    if not (
        has_finding(findings, "sBIT length is not Valid")
        or has_finding(findings, "sBIT chunk length must be")
    ):
        return None

    return repair_sbit_length(data)


def srgb_length(data: bytes, findings: Iterable[object]) -> Any | None:
    if not (
        has_finding(findings, "sRGB length is not Valid")
        or has_finding(findings, "sRGB chunk length must be")
    ):
        return None

    return repair_srgb_length(data)


def ster_length(data: bytes, findings: Iterable[object]) -> Any | None:
    if not (
        has_finding(findings, "sTER length is not Valid")
        or has_finding(findings, "sTER chunk length must be")
    ):
        return None

    return repair_ster_length(data)


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


def partial_idat_blackfill(data: bytes, findings: Iterable[object]) -> Any | None:
    if not (
        has_finding(findings, "IDAT")
        or has_finding(findings, "Not enough image data")
        or has_finding(findings, "Too much image data")
        or has_finding(findings, "bad adaptive filter")
    ):
        return None

    return rebuild_partial_idat_blackfill(data)


def automatic_repair(
    name: AutomaticRepairHandler,
    data: bytes,
    findings: Iterable[object],
    *,
    known_chunk_types: Iterable[bytes],
    auto: bool,
    nodialogue: bool,
    max_saves: int | None,
) -> Any | None:
    if name == "color_profile_cleanup":
        return color_profile_cleanup(data, findings)
    if name == "duplicate_singleton_cleanup":
        return duplicate_singleton_cleanup(data, findings)
    if name == "plte_cleanup":
        return plte_cleanup(
            data,
            findings,
            auto=auto,
            nodialogue=nodialogue,
            max_saves=max_saves,
        )
    if name == "bkgd_length":
        return bkgd_length(data, findings)
    if name == "gama_length":
        return gama_length(data, findings)
    if name == "gifg_length":
        return gifg_length(data, findings)
    if name == "hist_length":
        return hist_length(data, findings)
    if name == "chrm_length":
        return chrm_length(data, findings)
    if name == "itxt_keyword_length":
        return itxt_keyword_length(data, findings)
    if name == "itxt_compression_flag":
        return itxt_compression_flag(data, findings)
    if name == "itxt_compression_method":
        return itxt_compression_method(data, findings)
    if name == "offs_length":
        return offs_length(data, findings)
    if name == "phys_length":
        return phys_length(data, findings)
    if name == "time_length":
        return time_length(data, findings)
    if name == "trns_length":
        return trns_length(data, findings)
    if name == "sbit_length":
        return sbit_length(data, findings)
    if name == "srgb_length":
        return srgb_length(data, findings)
    if name == "ster_length":
        return ster_length(data, findings)
    if name == "known_chunk_type_case":
        return known_chunk_type_case(data, findings, known_chunk_types)
    if name == "unknown_private_critical_removal":
        return unknown_private_critical_removal(data, known_chunk_types)
    if name == "missing_chunk_data_byte":
        return missing_chunk_data_byte(data, findings)
    if name == "ihdr_rebuild":
        return ihdr_rebuild(data, findings)
    if name == "partial_idat_blackfill":
        return partial_idat_blackfill(data, findings)
    raise ValueError("Unknown FixItFelix automatic repair: %s" % name)
