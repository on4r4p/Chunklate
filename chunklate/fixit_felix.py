from __future__ import annotations

from collections.abc import Iterable
from collections.abc import Mapping
from dataclasses import dataclass
import re
from typing import Any
from typing import Callable
from typing import Literal

from . import idat
from . import idat_crc_forge
from . import png
from .png import (
    repair_bkgd_length,
    repair_chrm_length,
    repair_color_profile_chunks,
    repair_duplicate_ihdr_chunks,
    repair_duplicate_singleton_chunks,
    repair_empty_plte,
    repair_gama_length,
    repair_gifg_length,
    repair_grayscale_plte,
    repair_hist_out_of_place,
    repair_hist_length,
    repair_ihdr,
    repair_indexed_plte,
    repair_itxt_compression_flag,
    repair_itxt_keyword_length,
    repair_itxt_compression_method,
    repair_known_chunk_type_case,
    repair_missing_chunk_data_byte,
    repair_missing_chunk_length_zero_byte,
    repair_nonconsecutive_idat_interruption,
    repair_offs_length,
    repair_optional_truecolor_plte,
    repair_overlong_chunk_length_to_next_header,
    repair_pcal_out_of_place,
    repair_phys_length,
    repair_scal_payload,
    repair_sbit_length,
    repair_sbit_sample_depth,
    repair_splt_out_of_place,
    repair_splt_payloads,
    repair_srgb_length,
    repair_ster_out_of_place,
    repair_ster_length,
    repair_ster_mode,
    repair_text_null_bytes,
    repair_time_length,
    repair_time_value_range,
    repair_trns_length,
    repair_unknown_private_critical_chunks,
    repair_wrong_chunk_type_name,
    repair_ztxt_compression_method,
    repair_ztxt_data_format,
)
from .idat import rebuild_invalid_filter_type_as_filter0, rebuild_partial_idat_blackfill


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
    "write_partial_iend_tail",
]
AutomaticRepairHandler = Literal[
    "color_profile_cleanup",
    "hist_out_of_place_cleanup",
    "pcal_out_of_place_cleanup",
    "splt_out_of_place_cleanup",
    "ster_out_of_place_cleanup",
    "splt_payload_cleanup",
    "duplicate_ihdr_cleanup",
    "duplicate_singleton_cleanup",
    "plte_overlong_length_cleanup",
    "plte_cleanup",
    "gama_length",
    "gifg_length",
    "hist_length",
    "chrm_length",
    "bkgd_length",
    "itxt_keyword_length",
    "itxt_compression_flag",
    "itxt_compression_method",
    "ztxt_compression_method",
    "ztxt_data_format",
    "text_null_bytes",
    "offs_length",
    "phys_length",
    "scal_payload",
    "time_length",
    "time_value_range",
    "trns_length",
    "sbit_length",
    "srgb_length",
    "ster_length",
    "ster_mode",
    "idat_interruption_cleanup",
    "known_chunk_type_case",
    "unknown_private_critical_removal",
    "missing_chunk_data_byte",
    "ihdr_rebuild",
    "periodic_tail_xor_counter",
    "focused_idat_crc_forge",
    "partial_idat_blackfill",
]
FixItFelixWorkKind = Literal["automatic_repair", "finding"]


AUTOMATIC_REPAIR_ORDER: tuple[AutomaticRepairHandler, ...] = (
    "ihdr_rebuild",
    "color_profile_cleanup",
    "hist_out_of_place_cleanup",
    "pcal_out_of_place_cleanup",
    "splt_out_of_place_cleanup",
    "ster_out_of_place_cleanup",
    "splt_payload_cleanup",
    "duplicate_ihdr_cleanup",
    "duplicate_singleton_cleanup",
    "plte_overlong_length_cleanup",
    "plte_cleanup",
    "gama_length",
    "gifg_length",
    "hist_length",
    "chrm_length",
    "bkgd_length",
    "itxt_keyword_length",
    "itxt_compression_flag",
    "itxt_compression_method",
    "ztxt_compression_method",
    "ztxt_data_format",
    "text_null_bytes",
    "offs_length",
    "phys_length",
    "scal_payload",
    "time_length",
    "time_value_range",
    "trns_length",
    "sbit_length",
    "srgb_length",
    "ster_length",
    "ster_mode",
    "idat_interruption_cleanup",
    "known_chunk_type_case",
    "unknown_private_critical_removal",
    "missing_chunk_data_byte",
    "periodic_tail_xor_counter",
    "focused_idat_crc_forge",
    "partial_idat_blackfill",
)
IDAT_PAYLOAD_AUTOMATIC_REPAIRS: tuple[AutomaticRepairHandler, ...] = (
    "periodic_tail_xor_counter",
    "focused_idat_crc_forge",
    "partial_idat_blackfill",
)
AUTOMATIC_REPAIR_INTENTS: dict[
    AutomaticRepairHandler,
    tuple[str, tuple[tuple[str, ...], ...]],
] = {
    "color_profile_cleanup": (
        "I am going to remove a known-bad color profile or useless zero gAMA metadata, then rebuild the chunk list.",
        (("gAMA Chunk of 0 is Useless",), ("known incorrect sRGB profile",)),
    ),
    "hist_out_of_place_cleanup": (
        "hIST is metadata, but PNG wants it before IDAT. I am going to move or drop it safely.",
        (("hIST: out of place",), ("hIST chunk must appear before the first IDAT chunk",)),
    ),
    "pcal_out_of_place_cleanup": (
        "pCAL is out of order. I am going to move it back before IDAT and rebuild CRCs.",
        (("pCAL: out of place",), ("pCAL chunk must appear before the first IDAT chunk",)),
    ),
    "splt_out_of_place_cleanup": (
        "sPLT is out of order. I am going to move the suggested palette before IDAT and rebuild CRCs.",
        (
            ("sPLT: out of place",),
            ("sPLT chunk must appear before the first IDAT chunk",),
            ("Missplaced",),
        ),
    ),
    "ster_out_of_place_cleanup": (
        "sTER is out of order. I am going to move the stereo-layout metadata before IDAT and rebuild CRCs.",
        (
            ("sTER: out of place",),
            ("sTER chunk must appear before the first IDAT chunk",),
            ("Missplaced",),
        ),
    ),
    "splt_payload_cleanup": (
        "sPLT metadata is malformed or has duplicate names. I can try to repair it, or remove the optional suggested palette chunk(s).",
        (
            ("sPLT", "Wrong"),
            ("sPLT", "malformed"),
            ("sPLT", "entries"),
            ("Sample depth is not correct it must be 8 or 16",),
            ("sPLT", "same name"),
            ("sPLT", "share the same name"),
        ),
    ),
    "duplicate_ihdr_cleanup": (
        "PNG only allows one IHDR. I am going to keep the first header and remove the duplicate.",
        (("Multiple", "IHDR"), ("IHDR", "must appear at most once")),
    ),
    "duplicate_singleton_cleanup": (
        "PNG only allows one copy of this singleton chunk. I am going to keep the safest copy and remove duplicates.",
        (("Multiple",), ("multiple", "chunks")),
    ),
    "plte_overlong_length_cleanup": (
        "The PLTE length appears to run past the next real chunk. I am going to shorten it, rebuild CRCs, then rebuild the palette if needed.",
        (("PLTE", "Wrong Chunk name after Chunk"), ("PLTE", "No NextChunk"), ("PLTE", "Wrong Crc")),
    ),
    "plte_cleanup": (
        "The palette is suspicious. I am going to rebuild, trim, or remove PLTE according to the image color type and used indexes.",
        (("PLTE",),),
    ),
    "gama_length": (
        "The gAMA payload length is wrong. I am going to infer the standard 4-byte value and rebuild the chunk.",
        (("gAMA length is not Valid",),),
    ),
    "gifg_length": (
        "The gIFg payload length is wrong. I am going to trim or pad it to the expected extension layout.",
        (("gIFg length is not Valid",),),
    ),
    "hist_length": (
        "The hIST payload does not match the palette size. I am going to resize the histogram entries.",
        (("hIST length is not Valid",), ("Histogram frequencies entries must match PLTE entries number",)),
    ),
    "chrm_length": (
        "The cHRM payload is short. I am going to infer the missing chromaticity bytes when the evidence is strong enough.",
        (("cHRM length is not Valid",),),
    ),
    "bkgd_length": (
        "The bKGD payload length does not match the color type. I am going to rebuild the background chunk shape.",
        (("bKGD length is not Valid",),),
    ),
    "itxt_keyword_length": (
        "The iTXt keyword length is invalid. I am going to normalize that text metadata boundary.",
        (("iTXt Keyword length is not Valid",),),
    ),
    "itxt_compression_flag": (
        "The iTXt compression flag is invalid. I am going to normalize it to a PNG-legal value.",
        (("iTXt Compression Flag must be 0 or 1",),),
    ),
    "itxt_compression_method": (
        "The iTXt compression method is invalid. I am going to normalize it to PNG method 0.",
        (("iTXt Compression Method must be 0",),),
    ),
    "ztxt_compression_method": (
        "The zTXt compression method is invalid. I am going to normalize it to PNG method 0.",
        (("zTXt Compression Method must be 0",),),
    ),
    "ztxt_data_format": (
        "The zTXt compressed text stream is invalid. I am going to repair the zlib data-format byte and rebuild the chunk CRC.",
        (("zTXt Text Error",), ("zTXt compressed text is invalid",)),
    ),
    "text_null_bytes": (
        "The tEXt payload contains null bytes inside the text field. I am going to remove those bytes and rebuild CRCs.",
        (("tEXt text must not contain null bytes",),),
    ),
    "offs_length": (
        "The oFFs payload/unit is invalid. I am going to rebuild it with a legal unit and length.",
        (("Wrong Offset unit",), ("oFFs length is not Valid",)),
    ),
    "phys_length": (
        "The pHYs payload/unit is invalid. I am going to rebuild the physical pixel metadata shape.",
        (
            ("Error pHYs U",),
            ("pHYs length is not Valid",),
            ("pHYs chunk length must be 9",),
            ("pHYs unit specifier must be 0 or 1",),
            ("Unit specifier :Wrong value",),
        ),
    ),
    "scal_payload": (
        "The sCAL physical-scale metadata is malformed. I am going to remove that ancillary chunk and keep the image pixels intact.",
        (
            ("sCAL",),
            ("sCAL:",),
        ),
    ),
    "time_length": (
        "The tIME payload is malformed. I am going to rebuild the timestamp chunk to its fixed 7-byte layout.",
        (("tIME length is not Valid",), ("tIME Not enough bytes",), ("tIME chunk length must be 7",)),
    ),
    "time_value_range": (
        "The tIME timestamp contains impossible values. I am going to normalize those fields and rebuild the CRC.",
        (
            ("Month value is not valid",),
            ("Day value is not valid",),
            ("Hour value is not valid",),
            ("Minute value is not valid",),
            ("Second  value is not valid",),
            ("Second value is not valid",),
            ("tIME Month value is not valid",),
            ("tIME Day value is not valid",),
            ("tIME Hour value is not valid",),
            ("tIME Minute value is not valid",),
            ("tIME Second value is not valid",),
            ("tIME year must be at least 1",),
            ("tIME month must be between 1 and 12",),
            ("tIME day must be between 1 and 31",),
            ("tIME hour must be between 0 and 23",),
            ("tIME minute must be between 0 and 59",),
            ("tIME second must be between 0 and 60",),
        ),
    ),
    "trns_length": (
        "The tRNS payload does not fit the color type or palette. I am going to resize or remove that transparency data.",
        (
            ("tRNS length is not Valid",),
            ("tRNS Chunk Must not be empty",),
            ("Error tRNS_",),
            ("tRNS Alpha indexes palettes entries must not be superior",),
            ("IHDR Color", "when used with tRNS"),
            ("tRNS chunk length must",),
            ("tRNS chunk is not allowed",),
        ),
    ),
    "sbit_length": (
        "The sBIT payload is invalid. I am going to resize it or clamp significant-bit metadata to the IHDR sample depth.",
        (
            ("sBIT length is not Valid",),
            ("sBIT chunk length must be",),
            ("sBit", "value"),
            ("Significant greyscale bits",),
        ),
    ),
    "srgb_length": (
        "The sRGB payload length is invalid. I am going to rebuild it to the legal one-byte rendering intent.",
        (("sRGB length is not Valid",), ("sRGB chunk length must be",)),
    ),
    "ster_length": (
        "The sTER payload length is invalid. I am going to rebuild it to the legal one-byte stereo mode.",
        (("sTER length is not Valid",), ("sTER chunk length must be",)),
    ),
    "ster_mode": (
        "The sTER stereo-layout mode is invalid. I am going to normalize it to PNG mode 0 and rebuild the CRC.",
        (("sTER should be 0 or 1",), ("sTER mode must be 0 or 1",)),
    ),
    "idat_interruption_cleanup": (
        "The IDAT chain is interrupted. I am going to keep the image stream consecutive by moving or removing the blocker.",
        (("Wrong Chunk name after Chunk[b'IDAT']",), ("IDAT chunks must be consecutive",), ("nonconsecutive", "IDAT"), ("No NextChunk",)),
    ),
    "known_chunk_type_case": (
        "This looks like a known chunk with the wrong case bit. I am going to restore the legal chunk name.",
        (("Wrong Ancillary in known Chunk name",),),
    ),
    "unknown_private_critical_removal": (
        "An unknown critical chunk is unsafe for PNG readers. I am going to remove it if it is not a known chunk typo.",
        (("Critical",), ("unknown", "critical"), ("Unhandled-Critical",)),
    ),
    "missing_chunk_data_byte": (
        "A chunk appears to be missing one data byte. I am going to test the bounded one-byte reconstruction route.",
        (("Wrong Crc",), ("No NextChunk",)),
    ),
    "ihdr_rebuild": (
        "IHDR is not trustworthy. I am going to rebuild it from PNG rules, CRC evidence, or IDAT scanline math.",
        (("IHDR", "GetInfo"), ("IHDR", "Wrong Crc")),
    ),
    "focused_idat_crc_forge": (
        "HermesProbe localized a deflate error near a single bad IDAT CRC. I am trying the tight 4-byte repair before the blackfill fallback.",
        (("Wrong Crc", "IDAT"),),
    ),
    "periodic_tail_xor_counter": (
        "The PNG damage has a periodic byte pattern. I am going to test bounded XOR, arithmetic, swap, and bit-level periodic repairs, then keep one only if the whole PNG validates.",
        (("Wrong Crc", "IDAT"), ("No NextChunk",), ("corrupt deflate",), ("BadCodeLengthHuffmanTree",)),
    ),
    "partial_idat_blackfill": (
        "The image data is damaged. I am going to salvage complete scanlines and rebuild the IDAT stream.",
        (
            ("IDAT",),
            ("Not enough image data",),
            ("Too much image data",),
            ("bad adaptive filter",),
            ("scanline filter type is invalid",),
        ),
    ),
}
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


def _noop_progress(_indication: str) -> None:
    return None


@dataclass(frozen=True)
class FixItFelixRuntime:
    try_automatic_repair: Callable[[AutomaticRepairHandler], Any]
    apply_finding_work_item: Callable[[FixItFelixWorkItem, str, int, Any], tuple[bool, Any]]
    progress: Callable[[str], Any] = _noop_progress


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


@dataclass(frozen=True)
class IdatCrcForgeRepair:
    data: bytes
    strategy: str
    error_file_offset: int
    window_start: int
    window_end: int


@dataclass(frozen=True)
class PeriodicByteCorruptionRepair:
    data: bytes
    strategy: str
    mechanism: str
    period: int
    phase: int
    width: int
    start_block: int
    end_block: int


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

    donor_path = getattr(repair, "donor_path", "")
    donor_label = getattr(repair, "donor_label", "")
    if donor_path or donor_label:
        parts.append("IDAT donor: %s" % (donor_path or donor_label))

    synthetic_pattern = getattr(repair, "synthetic_pattern", "")
    if synthetic_pattern:
        parts.append("synthetic IDAT pattern: %s; original pixels were not recoverable" % synthetic_pattern)

    mechanism = getattr(repair, "mechanism", "")
    period = getattr(repair, "period", None)
    phase = getattr(repair, "phase", None)
    periodic_width = getattr(repair, "width", None)
    start_block = getattr(repair, "start_block", None)
    end_block = getattr(repair, "end_block", None)
    if None not in (period, phase, periodic_width, start_block, end_block):
        parts.append(
            "periodic byte repair: mechanism=%s; period=%s; phase=%s; width=%s; blocks=%s..%s"
            % (
                mechanism or "unknown",
                period,
                phase,
                periodic_width,
                start_block,
                max(int(start_block), int(end_block) - 1),
            )
        )

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


def automatic_repair_intent(
    name: AutomaticRepairHandler,
    findings: Iterable[object],
) -> str | None:
    intent = AUTOMATIC_REPAIR_INTENTS[name]
    message, trigger_groups = intent
    for triggers in trigger_groups:
        if has_finding(findings, *triggers):
            return message
    return None


def automatic_repair_failure_explanation(
    name: AutomaticRepairHandler,
    findings: Iterable[object],
) -> str | None:
    if name == "ihdr_rebuild" and has_finding(findings, "IHDR Compression Algorithms"):
        return (
            "Private compression probe refused: the IDAT looked like a known "
            "compression signature, but no bounded prefix completion decoded "
            "to valid PNG scanlines"
        )
    return None


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


def _is_wrong_chunk_name_work_item(item: FixItFelixWorkItem) -> bool:
    return item.kind == "finding" and item.handler == "wrong_chunk_name"


def repair_work_items(findings: Iterable[object], *, skip_bad_crc: bool) -> tuple[FixItFelixWorkItem, ...]:
    finding_items = tuple(
        FixItFelixWorkItem(
            "finding",
            route_finding(finding, skip_bad_crc=skip_bad_crc).handler,
            finding,
        )
        for finding in findings
    )
    has_wrong_chunk_name = any(_is_wrong_chunk_name_work_item(item) for item in finding_items)
    delayed_automatic = set(IDAT_PAYLOAD_AUTOMATIC_REPAIRS if has_wrong_chunk_name else ())

    items: list[FixItFelixWorkItem] = [
        FixItFelixWorkItem("automatic_repair", handler)
        for handler in automatic_repair_order()
        if handler not in delayed_automatic
    ]
    items.extend(item for item in finding_items if _is_wrong_chunk_name_work_item(item))
    items.extend(
        FixItFelixWorkItem("automatic_repair", handler)
        for handler in automatic_repair_order()
        if handler in delayed_automatic
    )
    items.extend(item for item in finding_items if not _is_wrong_chunk_name_work_item(item))
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


def _work_item_progress_indication(index: int, total: int) -> str:
    width = max(2, len(str(total)))
    return "FixItFelix %s/%s" % (
        str(index).zfill(width),
        str(total).zfill(width),
    )


def run_repair_work_items(
    runtime: FixItFelixRuntime,
    work_items: Iterable[FixItFelixWorkItem],
    *,
    chkd: str,
    pandora_box_len: int,
    chunk: Any,
) -> FixItFelixRunResult:
    ordered_work_items = tuple(work_items)
    total_work_items = len(ordered_work_items)
    for index, work_item in enumerate(ordered_work_items, start=1):
        runtime.progress(_work_item_progress_indication(index, total_work_items))

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
    finding_text = str(finding)
    if (
        "Not enough image data" in finding_text
        or "Too much image data" in finding_text
        or "IDAT zlib stream is invalid" in finding_text
        or "bad adaptive filter" in finding_text
        or "scanline filter type is invalid" in finding_text
        or "visual repair needs reference/ROI" in finding_text
    ):
        return LibpngErrorDecision("idat_decision_gate", finding)
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

    if exceeding and exceeding.startswith(good_ending[:len(exceeding)]):
        return NoNextAppendIendDecision("write_partial_iend_tail", exceeding)

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


def duplicate_ihdr_cleanup(data: bytes, findings: Iterable[object]) -> Any | None:
    if not (
        has_finding(findings, "Multiple", "IHDR")
        or has_finding(findings, "IHDR", "must appear at most once")
    ):
        return None

    return repair_duplicate_ihdr_chunks(data)


def hist_out_of_place_cleanup(data: bytes, findings: Iterable[object]) -> Any | None:
    if not (
        has_finding(findings, "hIST: out of place")
        or has_finding(findings, "hIST chunk must appear before the first IDAT chunk")
    ):
        return None

    return repair_hist_out_of_place(data)


def pcal_out_of_place_cleanup(data: bytes, findings: Iterable[object]) -> Any | None:
    if not (
        has_finding(findings, "pCAL: out of place")
        or has_finding(findings, "pCAL chunk must appear before the first IDAT chunk")
    ):
        return None

    return repair_pcal_out_of_place(data)


def splt_out_of_place_cleanup(data: bytes, findings: Iterable[object]) -> Any | None:
    if not (
        has_finding(findings, "sPLT: out of place")
        or has_finding(findings, "sPLT chunk must appear before the first IDAT chunk")
        or has_finding(findings, "Missplaced")
    ):
        return None

    return repair_splt_out_of_place(data)


def ster_out_of_place_cleanup(data: bytes, findings: Iterable[object]) -> Any | None:
    if not (
        has_finding(findings, "sTER: out of place")
        or has_finding(findings, "sTER chunk must appear before the first IDAT chunk")
        or has_finding(findings, "Missplaced")
    ):
        return None

    return repair_ster_out_of_place(data)


def splt_payload_cleanup(data: bytes, findings: Iterable[object]) -> Any | None:
    if not (
        has_finding(findings, "sPLT", "Wrong")
        or has_finding(findings, "sPLT", "malformed")
        or has_finding(findings, "sPLT", "entries")
        or has_finding(findings, "Sample depth is not correct it must be 8 or 16")
        or has_finding(findings, "sPLT", "same name")
        or has_finding(findings, "sPLT", "share the same name")
    ):
        return None

    return repair_splt_payloads(data)


def plte_overlong_length_cleanup(
    data: bytes,
    findings: Iterable[object],
    *,
    auto: bool,
    nodialogue: bool,
    max_saves: int | None,
) -> Any | None:
    if not (
        has_finding(findings, "PLTE")
        and (
            has_finding(findings, "Wrong Chunk name after Chunk")
            or has_finding(findings, "No NextChunk")
            or has_finding(findings, "Wrong Crc")
        )
    ):
        return None

    realigned = repair_overlong_chunk_length_to_next_header(
        data,
        max_overrun=4096,
        chunk_types=(b"PLTE",),
    )
    if realigned is None:
        return None

    return plte_cleanup(
        realigned.data,
        ("PLTE",),
        auto=auto,
        nodialogue=nodialogue,
        max_saves=max_saves,
    ) or realigned


def plte_cleanup(
    data: bytes,
    findings: Iterable[object],
    *,
    auto: bool,
    nodialogue: bool,
    max_saves: int | None,
) -> Any | None:
    if not has_finding(findings, "PLTE"):
        return None

    return (
        repair_empty_plte(data)
        or repair_grayscale_plte(data)
        or repair_indexed_plte(data)
        or repair_optional_truecolor_plte(data)
    )


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


def ztxt_compression_method(data: bytes, findings: Iterable[object]) -> Any | None:
    if not has_finding(findings, "zTXt Compression Method must be 0"):
        return None

    return repair_ztxt_compression_method(data)


def ztxt_data_format(data: bytes, findings: Iterable[object]) -> Any | None:
    if not (
        has_finding(findings, "zTXt Text Error")
        or has_finding(findings, "zTXt compressed text is invalid")
    ):
        return None

    return repair_ztxt_data_format(data)


def text_null_bytes(data: bytes, findings: Iterable[object]) -> Any | None:
    if not has_finding(findings, "tEXt text must not contain null bytes"):
        return None

    return repair_text_null_bytes(data)


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
        or has_finding(findings, "pHYs unit specifier must be 0 or 1")
        or has_finding(findings, "Unit specifier :Wrong value")
    ):
        return None

    return repair_phys_length(data)


def scal_payload(data: bytes, findings: Iterable[object]) -> Any | None:
    if not has_finding(findings, "sCAL"):
        return None

    return repair_scal_payload(data)


def time_length(data: bytes, findings: Iterable[object]) -> Any | None:
    if not (
        has_finding(findings, "tIME length is not Valid")
        or has_finding(findings, "tIME Not enough bytes")
        or has_finding(findings, "tIME chunk length must be 7")
    ):
        return None

    return repair_time_length(data)


def time_value_range(data: bytes, findings: Iterable[object]) -> Any | None:
    if not (
        has_finding(findings, "Month value is not valid")
        or has_finding(findings, "Day value is not valid")
        or has_finding(findings, "Hour value is not valid")
        or has_finding(findings, "Minute value is not valid")
        or has_finding(findings, "Second  value is not valid")
        or has_finding(findings, "Second value is not valid")
        or has_finding(findings, "tIME Month value is not valid")
        or has_finding(findings, "tIME Day value is not valid")
        or has_finding(findings, "tIME Hour value is not valid")
        or has_finding(findings, "tIME Minute value is not valid")
        or has_finding(findings, "tIME Second value is not valid")
        or has_finding(findings, "tIME year must be at least 1")
        or has_finding(findings, "tIME month must be between 1 and 12")
        or has_finding(findings, "tIME day must be between 1 and 31")
        or has_finding(findings, "tIME hour must be between 0 and 23")
        or has_finding(findings, "tIME minute must be between 0 and 59")
        or has_finding(findings, "tIME second must be between 0 and 60")
    ):
        return None

    return repair_time_value_range(data)


def trns_length(data: bytes, findings: Iterable[object]) -> Any | None:
    if not (
        has_finding(findings, "tRNS length is not Valid")
        or has_finding(findings, "tRNS Chunk Must not be empty")
        or has_finding(findings, "Error tRNS_")
        or has_finding(findings, "tRNS Alpha indexes palettes entries must not be superior")
        or has_finding(findings, "IHDR Color", "when used with tRNS")
        or has_finding(findings, "tRNS chunk length must")
        or has_finding(findings, "tRNS chunk is not allowed")
    ):
        return None

    return repair_trns_length(data)


def sbit_length(data: bytes, findings: Iterable[object]) -> Any | None:
    if not (
        has_finding(findings, "sBIT length is not Valid")
        or has_finding(findings, "sBIT chunk length must be")
        or has_finding(findings, "sBit", "value")
        or has_finding(findings, "Significant greyscale bits")
    ):
        return None

    return repair_sbit_length(data) or repair_sbit_sample_depth(data)


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


def ster_mode(data: bytes, findings: Iterable[object]) -> Any | None:
    if not (
        has_finding(findings, "sTER should be 0 or 1")
        or has_finding(findings, "sTER mode must be 0 or 1")
    ):
        return None

    return repair_ster_mode(data)


def missing_chunk_data_byte(data: bytes, findings: Iterable[object]) -> Any | None:
    if not (has_finding(findings, "Wrong Crc") or has_finding(findings, "No NextChunk")):
        return None

    return repair_missing_chunk_data_byte(data) or repair_missing_chunk_length_zero_byte(data)


def known_chunk_type_case(data: bytes, findings: Iterable[object], known_chunk_types: Iterable[bytes]) -> Any | None:
    if not (
        has_finding(findings, "Wrong Ancillary in known Chunk name")
        or has_finding(findings, "Wrong Chunk name")
    ):
        return None

    return (
        repair_known_chunk_type_case(data, known_chunk_types)
        or repair_wrong_chunk_type_name(data, known_chunk_types)
    )


def unknown_private_critical_removal(data: bytes, known_chunk_types: Iterable[bytes]) -> Any | None:
    return repair_unknown_private_critical_chunks(data, known_chunk_types)


def idat_interruption_cleanup(data: bytes, findings: Iterable[object]) -> Any | None:
    if not (
        has_finding(findings, "Wrong Chunk name after Chunk[b'IDAT']")
        or has_finding(findings, "IDAT chunks must be consecutive")
        or has_finding(findings, "nonconsecutive", "IDAT")
        or has_finding(findings, "No NextChunk")
    ):
        return None

    return repair_nonconsecutive_idat_interruption(data)


def ihdr_rebuild(data: bytes, findings: Iterable[object]) -> Any | None:
    if not (
        has_finding(findings, "IHDR", "GetInfo")
        or has_finding(findings, "IHDR", "Wrong Crc")
    ):
        return None

    return repair_ihdr(data)


PERIODIC_TAIL_XOR_PERIOD = 32
PERIODIC_TAIL_XOR_PHASE = 30
PERIODIC_TAIL_XOR_WIDTH = 2
PERIODIC_CORRUPTION_PERIODS = (32, 16, 64, 24, 8, 12, 20, 28, 40, 48, 56, 96, 128)
PERIODIC_CORRUPTION_WIDTHS = (2, 1, 4)
PERIODIC_CORRUPTION_START_BLOCK_LIMIT = 8
PERIODIC_CORRUPTION_PHASE_HINT_RADIUS = 2


def _periodic_tail_xor_counter_mask(block_delta: int) -> tuple[int, int]:
    q, r = divmod(max(0, int(block_delta)), 256)
    first = ((q & ~3) + (7 - (q & 3))) & 0xFF
    second = (r ^ ((r + q + 1) & 0xFF)) & 0xFF
    if r + q + 1 >= 256:
        overflow_index = r - (256 - (q + 1))
        second ^= (overflow_index ^ (overflow_index + 1)) & 0xFF
    return first, second


def _periodic_counter_mask(block_delta: int, width: int, mask_name: str) -> tuple[int, ...] | None:
    block_delta = max(0, int(block_delta))
    if mask_name == "legacy-counter":
        if width != 2:
            return None
        return _periodic_tail_xor_counter_mask(block_delta)

    value = block_delta
    if mask_name.startswith("one-based-"):
        value += 1

    if mask_name.endswith("-le"):
        return tuple((value >> (8 * lane)) & 0xFF for lane in range(width))
    if mask_name.endswith("-be"):
        return tuple((value >> (8 * (width - lane - 1))) & 0xFF for lane in range(width))
    return None


def _periodic_transform_byte(value: int, operation: str, mask: int = 0) -> int:
    if operation == "xor":
        return value ^ mask
    if operation == "add":
        return (value + mask) & 0xFF
    if operation == "sub":
        return (value - mask) & 0xFF
    if operation == "not":
        return value ^ 0xFF
    if operation == "nibble-swap":
        return ((value << 4) | (value >> 4)) & 0xFF
    if operation == "rol1":
        return ((value << 1) | (value >> 7)) & 0xFF
    if operation == "ror1":
        return ((value >> 1) | ((value & 1) << 7)) & 0xFF
    raise ValueError("unknown periodic transform operation: %s" % operation)


def _periodic_mechanisms(width: int) -> tuple[tuple[str, str, str], ...]:
    mechanisms: list[tuple[str, str, str]] = []
    if width == 2:
        mechanisms.extend(
            (
                ("xor legacy-counter", "xor", "legacy-counter"),
                ("sub legacy-counter", "sub", "legacy-counter"),
                ("add legacy-counter", "add", "legacy-counter"),
            )
        )

    for mask_name in ("block-index-le", "block-index-be", "one-based-le", "one-based-be"):
        mechanisms.extend(
            (
                ("xor %s" % mask_name, "xor", mask_name),
                ("sub %s" % mask_name, "sub", mask_name),
                ("add %s" % mask_name, "add", mask_name),
            )
        )

    if width == 2:
        mechanisms.append(("swap periodic pair", "swap", ""))
    mechanisms.extend(
        (
            ("bit-not periodic bytes", "not", ""),
            ("nibble-swap periodic bytes", "nibble-swap", ""),
            ("rotate-left periodic bytes", "rol1", ""),
            ("rotate-right periodic bytes", "ror1", ""),
        )
    )
    return tuple(mechanisms)


def _apply_periodic_corruption_transform(
    data: bytes,
    *,
    start_block: int,
    end_block: int,
    period: int,
    phase: int,
    width: int,
    operation: str,
    mask_name: str,
) -> bytes | None:
    if start_block < 0 or end_block <= start_block or period <= 0 or width <= 0:
        return None
    if phase < 0 or phase + width > period:
        return None

    candidate = bytearray(data)
    for block in range(start_block, end_block):
        offset = block * period + phase
        if offset + width > len(candidate):
            return None
        if operation == "swap":
            if width != 2:
                return None
            candidate[offset], candidate[offset + 1] = candidate[offset + 1], candidate[offset]
            continue

        mask = _periodic_counter_mask(block - start_block, width, mask_name) if mask_name else (0,) * width
        if mask is None:
            return None
        for lane in range(width):
            candidate[offset + lane] = _periodic_transform_byte(
                candidate[offset + lane],
                operation,
                mask[lane],
            )
    return bytes(candidate)


def _apply_periodic_tail_xor_counter(
    data: bytes,
    *,
    start_block: int,
    end_block: int,
    period: int = PERIODIC_TAIL_XOR_PERIOD,
    phase: int = PERIODIC_TAIL_XOR_PHASE,
) -> bytes | None:
    return _apply_periodic_corruption_transform(
        data,
        start_block=start_block,
        end_block=end_block,
        period=period,
        phase=phase,
        width=PERIODIC_TAIL_XOR_WIDTH,
        operation="xor",
        mask_name="legacy-counter",
    )


def _periodic_end_blocks(data: bytes, *, period: int, phase: int, width: int) -> tuple[int, ...]:
    if period <= 0 or width <= 0 or phase < 0 or phase + width > period:
        return ()
    max_end = max(0, ((len(data) - width - phase) // period) + 1)
    candidates = {max_end}

    iend_offset = data.rfind(b"IEND")
    if iend_offset >= 0:
        candidates.add(iend_offset // period)
        candidates.add(max(0, iend_offset // period - 1))

    for tail_blocks in range(1, 5):
        candidates.add(max(0, max_end - tail_blocks))

    return tuple(sorted(candidate for candidate in candidates if candidate > 0))


def _periodic_hint_offsets(data: bytes) -> tuple[int, ...]:
    offsets: list[int] = []
    validation = png.validate_png_structure(data)
    for error in validation.errors:
        for match in re.finditer(r"0x[0-9a-fA-F]+|\b\d{2,}\b", str(error)):
            try:
                offset = int(match.group(0), 0)
            except ValueError:
                continue
            if 0 <= offset < len(data):
                offsets.append(offset)

    try:
        analysis = idat.analyze_idat_stream(data)
    except Exception:
        analysis = None
    if analysis is not None:
        for value in (
            getattr(analysis, "error_file_offset", None),
            getattr(analysis, "error_idat_offset", None),
            getattr(analysis, "error_offset", None),
        ):
            if value is None:
                continue
            try:
                offset = int(value)
            except (TypeError, ValueError):
                continue
            if 0 <= offset < len(data):
                offsets.append(offset)

    try:
        chunks = tuple(png.iter_chunks(data))
    except Exception:
        chunks = ()
    for chunk in chunks:
        if chunk.crc == chunk.computed_crc:
            continue
        offsets.extend(
            (
                int(chunk.offset),
                int(chunk.offset) + 4,
                int(chunk.offset) + 8,
                int(chunk.offset) + 8 + max(0, int(chunk.length) - 1),
                int(chunk.offset) + 8 + int(chunk.length),
            )
        )

    unique: list[int] = []
    seen: set[int] = set()
    for offset in offsets:
        if not 0 <= offset < len(data):
            continue
        if offset in seen:
            continue
        seen.add(offset)
        unique.append(offset)
    return tuple(unique)


def _periodic_phase_candidates(
    hint_offsets: tuple[int, ...],
    *,
    period: int,
    width: int,
) -> tuple[int, ...]:
    candidates = {max(0, period - width)}
    for offset in hint_offsets:
        for lane in range(width):
            phase = (offset - lane) % period
            for delta in range(-PERIODIC_CORRUPTION_PHASE_HINT_RADIUS, PERIODIC_CORRUPTION_PHASE_HINT_RADIUS + 1):
                candidate = phase + delta
                if 0 <= candidate and candidate + width <= period:
                    candidates.add(candidate)
    return tuple(sorted(candidates))


def _periodic_transform_specs(data: bytes) -> tuple[tuple[int, int, int, str, str, str], ...]:
    specs: list[tuple[int, int, int, str, str, str]] = []
    seen: set[tuple[int, int, int, str, str, str]] = set()
    hint_offsets = _periodic_hint_offsets(data)

    def add_spec(
        period: int,
        width: int,
        phase: int,
        mechanism: str,
        operation: str,
        mask_name: str,
    ) -> None:
        spec = (period, width, phase, mechanism, operation, mask_name)
        if spec in seen:
            return
        seen.add(spec)
        specs.append(spec)

    for mechanism, operation, mask_name in _periodic_mechanisms(PERIODIC_TAIL_XOR_WIDTH):
        add_spec(
            PERIODIC_TAIL_XOR_PERIOD,
            PERIODIC_TAIL_XOR_WIDTH,
            PERIODIC_TAIL_XOR_PHASE,
            mechanism,
            operation,
            mask_name,
        )

    for period in PERIODIC_CORRUPTION_PERIODS:
        for width in PERIODIC_CORRUPTION_WIDTHS:
            if width > period:
                continue
            for phase in _periodic_phase_candidates(hint_offsets, period=period, width=width):
                for mechanism, operation, mask_name in _periodic_mechanisms(width):
                    add_spec(period, width, phase, mechanism, operation, mask_name)
    return tuple(specs)


def _periodic_byte_repair_candidate(data: bytes) -> PeriodicByteCorruptionRepair | None:
    if not data.startswith(png.PNG_SIGNATURE):
        return None
    if png.validate_png_structure(data).ok:
        return None

    for period, width, phase, mechanism, operation, mask_name in _periodic_transform_specs(data):
        end_blocks = _periodic_end_blocks(data, period=period, phase=phase, width=width)
        for start_block in range(0, PERIODIC_CORRUPTION_START_BLOCK_LIMIT):
            for end_block in end_blocks:
                repaired = _apply_periodic_corruption_transform(
                    data,
                    start_block=start_block,
                    end_block=end_block,
                    period=period,
                    phase=phase,
                    width=width,
                    operation=operation,
                    mask_name=mask_name,
                )
                if repaired is None:
                    continue
                validation = png.validate_png_structure(repaired)
                if not validation.ok:
                    continue
                try:
                    analysis = idat.analyze_idat_stream(repaired)
                except Exception:
                    continue
                if not analysis.complete:
                    continue
                return PeriodicByteCorruptionRepair(
                    data=repaired,
                    strategy="repaired periodic byte corruption via %s" % mechanism,
                    mechanism=mechanism,
                    period=period,
                    phase=phase,
                    width=width,
                    start_block=start_block,
                    end_block=end_block,
                )
    return None


def _no_next_points_at_damaged_idat_stream(data: bytes, findings: Iterable[object]) -> bool:
    if not has_finding(findings, "No NextChunk"):
        return False
    try:
        analysis = idat.analyze_idat_stream(data)
    except Exception:
        return False
    return bool(
        analysis.supported
        and not analysis.complete
        and analysis.status in {"corrupt_deflate", "incomplete_stream", "bad_adler"}
    )


def periodic_tail_xor_counter(data: bytes, findings: Iterable[object]) -> Any | None:
    direct_idat_signal = (
        has_finding(findings, "Wrong Crc", "IDAT")
        or has_finding(findings, "No NextChunk", "IDAT")
        or has_finding(findings, "corrupt deflate")
        or has_finding(findings, "BadCodeLengthHuffmanTree")
    )
    if not (direct_idat_signal or _no_next_points_at_damaged_idat_stream(data, findings)):
        return None
    return _periodic_byte_repair_candidate(data)


def partial_idat_blackfill(data: bytes, findings: Iterable[object]) -> Any | None:
    if not (
        has_finding(findings, "IDAT")
        or has_finding(findings, "Not enough image data")
        or has_finding(findings, "Too much image data")
        or has_finding(findings, "bad adaptive filter")
        or has_finding(findings, "scanline filter type is invalid")
    ):
        return None

    if has_finding(findings, "bad adaptive filter") or has_finding(findings, "scanline filter type is invalid"):
        repaired_invalid_filter = rebuild_invalid_filter_type_as_filter0(data)
        if repaired_invalid_filter is not None:
            return repaired_invalid_filter

    return rebuild_partial_idat_blackfill(data)


def _bad_crc_idat_chunks(data: bytes) -> tuple[png.PngChunk, ...]:
    try:
        chunks = tuple(png.iter_chunks(data))
    except png.PngFormatError:
        return ()

    return tuple(
        chunk
        for chunk in chunks
        if chunk.chunk_type == b"IDAT" and chunk.crc != chunk.computed_crc
    )


def focused_idat_crc_target_chunk(
    data: bytes,
    analysis: idat.IdatStreamAnalysis,
) -> png.PngChunk | None:
    bad_chunks = _bad_crc_idat_chunks(data)
    if len(bad_chunks) == 1:
        return bad_chunks[0]

    if analysis.error_idat_index is None:
        return None

    try:
        idat_chunks = tuple(chunk for chunk in png.iter_chunks(data) if chunk.chunk_type == b"IDAT")
    except png.PngFormatError:
        return None

    index = int(analysis.error_idat_index) - 1
    if index < 0 or index >= len(idat_chunks):
        return None

    target_chunk = idat_chunks[index]
    if target_chunk.crc == target_chunk.computed_crc:
        return None
    return target_chunk


def _focused_idat_crc_window(
    target_chunk: png.PngChunk,
    analysis: idat.IdatStreamAnalysis,
    *,
    byte_count: int = 4,
) -> tuple[int, int] | None:
    if analysis.error_file_offset is None:
        return None

    payload_offset = int(analysis.error_file_offset) - int(target_chunk.offset) - 8
    start = payload_offset - int(byte_count) + 1
    end = start + 1
    if start < 0 or end > len(target_chunk.data):
        return None
    return start, end


def finalize_focused_idat_crc_candidate(candidate_data: bytes) -> tuple[bytes, str] | None:
    validation = png.validate_png_structure(candidate_data)
    if validation.ok:
        return candidate_data, ""

    plte_repair = png.repair_indexed_plte(candidate_data)
    if plte_repair is None:
        return None
    if not png.validate_png_structure(plte_repair.data).ok:
        return None
    return plte_repair.data, " then %s" % plte_repair.strategy


def focused_idat_crc_forge(data: bytes, findings: Iterable[object]) -> Any | None:
    if not (
        has_finding(findings, "Wrong Crc", "IDAT")
        or has_finding(findings, "libpng error", "IDAT")
        or has_finding(findings, "corrupt_deflate")
    ):
        return None

    try:
        analysis = idat.analyze_idat_stream(data)
    except Exception:
        return None

    if analysis.status != "corrupt_deflate" or analysis.error_file_offset is None:
        return None

    target_chunk = focused_idat_crc_target_chunk(data, analysis)
    if target_chunk is None:
        return None
    window = _focused_idat_crc_window(target_chunk, analysis, byte_count=4)
    if window is None:
        return None

    start, end = window
    old_crc = target_chunk.crc.to_bytes(4, "big")
    window_spec = "%s:%s" % (start, end)
    target_file_offset = int(target_chunk.offset) + 8 + int(start)

    for candidate in idat_crc_forge.iter_forge_candidates(
        data,
        target_chunk,
        old_crc,
        edit_order=("replace",),
        byte_counts=(4,),
        window_spec=window_spec,
        mode="force",
        zlib_prefilter=True,
    ):
        candidate_data = candidate.hit.png_bytes
        candidate_analysis = idat.analyze_idat_stream(candidate_data)
        if not candidate_analysis.complete:
            continue
        finalized = finalize_focused_idat_crc_candidate(candidate_data)
        if finalized is None:
            continue
        repaired_data, followup_strategy = finalized

        return IdatCrcForgeRepair(
            data=repaired_data,
            strategy="focused 4-byte IDAT CRC repair around file offset 0x%x%s before blackfill"
            % (target_file_offset, followup_strategy),
            error_file_offset=int(analysis.error_file_offset),
            window_start=target_file_offset,
            window_end=target_file_offset + 3,
        )

    return None


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
    if name == "hist_out_of_place_cleanup":
        return hist_out_of_place_cleanup(data, findings)
    if name == "pcal_out_of_place_cleanup":
        return pcal_out_of_place_cleanup(data, findings)
    if name == "splt_out_of_place_cleanup":
        return splt_out_of_place_cleanup(data, findings)
    if name == "ster_out_of_place_cleanup":
        return ster_out_of_place_cleanup(data, findings)
    if name == "splt_payload_cleanup":
        return splt_payload_cleanup(data, findings)
    if name == "duplicate_ihdr_cleanup":
        return duplicate_ihdr_cleanup(data, findings)
    if name == "duplicate_singleton_cleanup":
        return duplicate_singleton_cleanup(data, findings)
    if name == "plte_overlong_length_cleanup":
        return plte_overlong_length_cleanup(
            data,
            findings,
            auto=auto,
            nodialogue=nodialogue,
            max_saves=max_saves,
        )
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
    if name == "ztxt_compression_method":
        return ztxt_compression_method(data, findings)
    if name == "ztxt_data_format":
        return ztxt_data_format(data, findings)
    if name == "text_null_bytes":
        return text_null_bytes(data, findings)
    if name == "offs_length":
        return offs_length(data, findings)
    if name == "phys_length":
        return phys_length(data, findings)
    if name == "scal_payload":
        return scal_payload(data, findings)
    if name == "time_length":
        return time_length(data, findings)
    if name == "time_value_range":
        return time_value_range(data, findings)
    if name == "trns_length":
        return trns_length(data, findings)
    if name == "sbit_length":
        return sbit_length(data, findings)
    if name == "srgb_length":
        return srgb_length(data, findings)
    if name == "ster_length":
        return ster_length(data, findings)
    if name == "ster_mode":
        return ster_mode(data, findings)
    if name == "idat_interruption_cleanup":
        return idat_interruption_cleanup(data, findings)
    if name == "known_chunk_type_case":
        return known_chunk_type_case(data, findings, known_chunk_types)
    if name == "unknown_private_critical_removal":
        return unknown_private_critical_removal(data, known_chunk_types)
    if name == "missing_chunk_data_byte":
        return missing_chunk_data_byte(data, findings)
    if name == "ihdr_rebuild":
        return ihdr_rebuild(data, findings)
    if name == "periodic_tail_xor_counter":
        return periodic_tail_xor_counter(data, findings)
    if name == "focused_idat_crc_forge":
        return focused_idat_crc_forge(data, findings)
    if name == "partial_idat_blackfill":
        return partial_idat_blackfill(data, findings)
    raise ValueError("Unknown FixItFelix automatic repair: %s" % name)
