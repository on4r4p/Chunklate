from __future__ import annotations

from collections.abc import Callable, MutableSequence
from dataclasses import dataclass
import json
import os
from typing import Any

from . import idat
from . import idat_bruteforce
from . import ultimate_reference_ui
from . import chunk_scanner
from .png import (
    detect_png_signature_recovery,
    legacy_find_magic_checkpoint_args,
    repair_linefeed_conversion,
    repair_idat_marker_chain_from_visible_headers,
    repair_overlong_chunk_length_to_next_header,
)


LegacyCall = Callable[..., Any]

MAGIC = "89504e470d0a1a0a"
FULL_MAGIC = "89504e470d0a1a0a0000000d49484452"
SUPER_MEGA_LINEFEED_FORCE = "SuperMegaLineFeedForceOfDeath"
ULTIMATE_LINEFEED_FORCE = "UltimateMegaSuperLineFeedBruteForce"


def _hidden_tmp_path(path: str) -> str:
    directory, filename = os.path.split(path)
    tmp_name = ".%s.tmp" % (filename or "chunklate")
    return os.path.join(directory, tmp_name) if directory else tmp_name


@dataclass(frozen=True)
class FindMagicContext:
    data_bytes: bytes
    data_hex: str
    chunks: tuple[bytes, ...]
    before_idat: tuple[bytes, ...]
    sample_name: str
    debug: bool = False
    pause_debug: bool = False
    pause_error: bool = False


@dataclass(frozen=True)
class FindMagicRuntime:
    candy: LegacyCall
    emit: LegacyCall
    checkpoint: LegacyCall
    end: LegacyCall
    betterror: LegacyCall
    pause: LegacyCall
    spec_length: LegacyCall
    minibar: LegacyCall
    side_notes: MutableSequence[Any]
    chunk_story: LegacyCall = lambda *args, **kwargs: None
    write_clone: LegacyCall = lambda *args, **kwargs: None
    ask: LegacyCall | None = None
    preview_image: LegacyCall = lambda *args, **kwargs: None
    loadingbar: LegacyCall = lambda *args, **kwargs: None
    prompt_candy: LegacyCall | None = None
    clear_dialogue_pause: LegacyCall = lambda *args, **kwargs: None
    ultimate_checkpoint_path: LegacyCall = lambda *args, **kwargs: ""
    ultimate_progress_path: LegacyCall = lambda *args, **kwargs: ""
    ultimate_source_path: LegacyCall = lambda *args, **kwargs: ""
    ultimate_resume_decision: LegacyCall = lambda *args, **kwargs: "ask"
    ultimate_linefeed_budget: LegacyCall = (
        lambda estimate=None, *args, **kwargs: idat_bruteforce.ultimate_linefeed_budget_decision(
            getattr(estimate, "total_combinations", 0),
            "normal",
        )
    )
    ultimate_linefeed_reference: LegacyCall = lambda *args, **kwargs: ""
    ultimate_linefeed_reference_mode: LegacyCall = lambda *args, **kwargs: "exact"
    ultimate_linefeed_reference_regions: LegacyCall = lambda *args, **kwargs: ""
    ultimate_linefeed_reference_region_editor: LegacyCall = lambda *args, **kwargs: False
    ultimate_linefeed_reference_region_editor_run: LegacyCall = (
        lambda *args, **kwargs: ultimate_reference_ui.ReferenceRegionEditorResult(
            False,
            str(args[2]) if len(args) > 2 else "",
            "reference region editor is not wired",
        )
    )
    ultimate_linefeed_interactive: LegacyCall = lambda *args, **kwargs: True
    ultimate_visual_gallery_limit: LegacyCall = (
        lambda *args, **kwargs: idat_bruteforce.ULTIMATE_LINEFEED_VISUAL_GALLERY_LIMIT
    )
    ultimate_visual_min_coverage: LegacyCall = (
        lambda *args, **kwargs: idat_bruteforce.ULTIMATE_LINEFEED_VISUAL_MIN_COVERAGE
    )
    ultimate_candidate_preview: LegacyCall | None = None
    ultimate_interrupt_cleanup: LegacyCall = lambda *args, **kwargs: None
    defer_linefeed_signature_repair: LegacyCall = lambda *args, **kwargs: False


@dataclass(frozen=True)
class LinefeedAlternative:
    repair: Any
    summary: str


@dataclass(frozen=True)
class LinefeedChunkEvidence:
    idat_bruteforce_allowed: bool
    summary_lines: tuple[str, ...]


def _color(runtime: FindMagicRuntime, color: str, value: Any) -> Any:
    return runtime.candy("Color", color, value)


def _chunky(runtime: FindMagicRuntime, value: str) -> Any:
    return runtime.candy("Chunky", value)


def _cowsay(runtime: FindMagicRuntime, message: str, mood: str | None = None) -> Any:
    if mood is None:
        return runtime.candy("Cowsay", message)
    return runtime.candy("Cowsay", message, mood)


def _linefeed_repair_summary(repair) -> str:
    if getattr(repair, "linefeed_pattern", "") == "nul_stripped_linefeed_corruption":
        lines = [
            "-Line feed conversion repair: reconstructed bytes stripped by NUL removal and line-feed conversion.",
            "-Line feed conversion repair: %s." % repair.strategy,
        ]
    elif getattr(repair, "removed_extra_cr_offsets", ()):
        lines = ["-Line feed conversion repair: removed carriage returns inserted by CRLF conversion."]
        lines.append(
            "-Line feed conversion repair: removed %s extra CR byte%s."
            % (
                len(repair.removed_extra_cr_offsets),
                "" if len(repair.removed_extra_cr_offsets) == 1 else "s",
            )
        )
    else:
        lines = ["-Line feed conversion repair: restored missing carriage returns."]
    if repair.removed_prefix_bytes:
        lines.append(
            "-Line feed conversion repair: cut %s bytes before PNG signature."
            % repair.removed_prefix_bytes
        )
    if repair.inserted_signature_cr:
        lines.append("-Line feed conversion repair: inserted missing CR in PNG signature.")
    for patch in repair.payload_patches:
        lines.append(
            "-Line feed conversion repair: inserted CR in %s data at chunk offset 0x%x, payload offset 0x%x; CRC 0x%08x matched."
            % (
                patch.chunk_type.decode("ascii", errors="replace"),
                patch.chunk_offset,
                patch.payload_offset,
                patch.stored_crc,
            )
        )
    for error in getattr(repair, "validation_errors", ()):
        lines.append("-Line feed conversion repair: validation error after CR restoration: %s" % error)
    return "\n".join(lines)


def _linefeed_salvage_summary(realignment, salvage) -> str:
    return "\n".join(
        [
            "-Line feed conversion repair: %s at chunk offset 0x%x; next chunk at 0x%x; rebuilt CRC 0x%08x."
            % (
                realignment.strategy,
                realignment.chunk_offset,
                realignment.next_chunk_offset,
                realignment.rebuilt_crc,
            ),
            "-Line feed conversion repair: %s."
            % salvage.strategy,
        ]
    )


def _linefeed_reused_row_count(strategy: str) -> int:
    marker = "reused previous row for "
    if marker not in strategy:
        return 0
    tail = strategy.split(marker, 1)[1]
    digits = []
    for char in tail:
        if not char.isdigit():
            break
        digits.append(char)
    if not digits:
        return 0
    return int("".join(digits))


def _linefeed_marker_chain_structural_repair(marker_repair):
    analysis = idat.analyze_idat_stream(
        marker_repair.data,
        source_kind="candidate_from_original",
        crc_provenance="rebuilt_by_chunklate",
    )
    if not analysis.complete:
        return None
    return idat.PartialIdatBlackfillRepair(
        data=marker_repair.data,
        strategy=(
            "idat-marker-chain-complete recovered %s/%s scanlines with rebuilt PNG CRCs"
            % (analysis.usable_scanlines, analysis.height)
        ),
        recovered_scanlines=analysis.usable_scanlines,
        total_scanlines=analysis.height,
        width=analysis.width,
        height=analysis.height,
        bit_depth=analysis.bit_depth,
        color_type=analysis.color_type,
    )


def _linefeed_marker_chain_visual_repair(marker_repair):
    analysis = idat.analyze_idat_stream(
        marker_repair.data,
        source_kind="candidate_from_original",
        crc_provenance="rebuilt_by_chunklate",
    )
    repair = (
        _linefeed_marker_chain_structural_repair(marker_repair)
        or idat.rebuild_tolerant_idat_salvage(marker_repair.data)
        or idat.rebuild_partial_idat_blackfill(marker_repair.data)
    )
    return analysis, repair


def _linefeed_marker_chain_score(marker_repair, analysis, repair) -> tuple[int, ...]:
    reused_rows = _linefeed_reused_row_count(getattr(repair, "strategy", ""))
    extra_bytes = max(0, int(analysis.decompressed_size) - int(analysis.expected_size))
    return (
        1 if analysis.adler_status == "adler_match" else 0,
        int(repair.recovered_scanlines),
        1 if analysis.complete else 0,
        -reused_rows,
        -extra_bytes,
        -int(marker_repair.changed_chunk_count),
        len(marker_repair.preserved_chunks),
    )


def _linefeed_best_marker_chain_candidate(marker_repairs):
    best = None
    best_score: tuple[int, ...] | None = None
    for marker_repair in marker_repairs:
        analysis, repair = _linefeed_marker_chain_visual_repair(marker_repair)
        if repair is None:
            continue
        score = _linefeed_marker_chain_score(marker_repair, analysis, repair)
        if best_score is None or score > best_score:
            best = (marker_repair, analysis, repair)
            best_score = score
    return best


def _linefeed_marker_chain_summary(marker_repair, analysis, repair) -> str:
    lines = [
        "-Line feed conversion repair: marker-chain reconstructed visible IHDR/IDAT/IEND headers: %s."
        % marker_repair.strategy
    ]
    if marker_repair.preserved_chunks:
        lines.append(
            "-Line feed conversion repair: IDAT chunk preserved byte-for-byte where CRC already matched: %s."
            % ", ".join(marker_repair.preserved_chunks)
        )
    if marker_repair.rebuilt_crc_chunks:
        lines.append(
            "-Line feed conversion repair: IDAT CRC rebuilt for marker-chain chunk(s): %s."
            % ", ".join(marker_repair.rebuilt_crc_chunks)
        )
    if marker_repair.declared_payload_chunks:
        lines.append(
            "-Line feed conversion repair: kept declared IDAT payload bytes before rebuilding CRC: %s."
            % ", ".join(marker_repair.declared_payload_chunks)
        )
    if marker_repair.shortened_chunks:
        lines.append(
            "-Line feed conversion repair: shortened IDAT payload to the next visible marker before rebuilding CRC: %s."
            % ", ".join(marker_repair.shortened_chunks)
        )
    if marker_repair.suspected_payload_markers:
        lines.append(
            "-Line feed conversion repair: ignored marker-looking bytes inside the visible IDAT payload: %s."
            % ", ".join(marker_repair.suspected_payload_markers)
        )
    if repair.data != marker_repair.data:
        lines.append(
            "-Line feed conversion repair: visual salvage recompressed scanlines with rebuilt Adler: %s."
            % repair.strategy
        )
    else:
        lines.append("-Line feed conversion repair: marker-chain output kept the repaired IDAT stream.")
    if analysis.adler_status != "adler_match":
        lines.append(
            "-Line feed conversion repair: original Adler not recovered after marker-chain; keeping rebuilt-Adler visual salvage."
        )
    return "\n".join(lines)


def _linefeed_marker_chain_alternative(
    runtime: FindMagicRuntime,
    repair,
    base_summary: str,
) -> LinefeedAlternative | None:
    marker_repairs = repair_idat_marker_chain_from_visible_headers(repair.data)
    best = _linefeed_best_marker_chain_candidate(marker_repairs)
    if best is None:
        return None
    marker_repair, analysis, visual_repair = best
    marker_summary = _linefeed_marker_chain_summary(marker_repair, analysis, visual_repair)
    _cowsay(
        runtime,
        (
            "I rebuilt the visible IDAT marker chain before brute force. "
            "The best visual salvage is now %s/%s scanlines."
        )
        % (visual_repair.recovered_scanlines, visual_repair.total_scanlines),
        "good",
    )
    if marker_repair.preserved_chunks:
        _cowsay(
            runtime,
            "I preserved the already-valid IDAT chunks and only rebuilt the suspect marker-chain segment.",
            "good",
        )
    if analysis.adler_status != "adler_match":
        _cowsay(
            runtime,
            "The original Adler still does not match, so this is a rebuilt-Adler visual salvage.",
            "com",
        )

    alternative = _linefeed_supermega_probe_alternative(
        runtime,
        marker_repair.data,
        visual_repair,
        marker_summary,
    )
    if alternative is not None:
        return LinefeedAlternative(
            alternative.repair,
            "\n".join((base_summary, alternative.summary)),
        )
    return LinefeedAlternative(
        visual_repair,
        "\n".join((base_summary, marker_summary)),
    )


def _linefeed_chunk_evidence(repair, realignment=None) -> LinefeedChunkEvidence:
    lines: list[str] = []
    idat_bruteforce_allowed = False

    for patch in getattr(repair, "payload_patches", ()):
        chunk_name = patch.chunk_type.decode("ascii", errors="replace")
        lines.append(
            "-Line feed conversion evidence: restored CR inside %s payload at chunk offset 0x%x; original CRC 0x%08x matched."
            % (chunk_name, patch.chunk_offset, patch.stored_crc)
        )
        if patch.chunk_type == b"IDAT":
            idat_bruteforce_allowed = True

    if realignment is not None:
        missing = max(0, int(realignment.old_length) - int(realignment.new_length))
        lines.append(
            "-Line feed conversion evidence: %s chunk length overran the next chunk by %s bytes at offset 0x%x; Chunklate shortened it and rebuilt the PNG CRC."
            % (realignment.chunk_name, missing, realignment.chunk_offset)
        )
        if realignment.chunk_name == "IDAT":
            idat_bruteforce_allowed = True

    if not lines:
        lines.append(
            "-Line feed conversion evidence: only the PNG signature was proven damaged; no chunk payload or chunk length evidence was found, so IDAT line-feed brute force is not offered."
        )

    return LinefeedChunkEvidence(
        idat_bruteforce_allowed=idat_bruteforce_allowed,
        summary_lines=tuple(lines),
    )


def _super_mega_linefeed_probe_summary(probe, repair=None) -> tuple[str, ...]:
    lines = [idat_bruteforce.super_mega_linefeed_probe_summary_line(probe)]
    lines.extend(idat_bruteforce.super_mega_linefeed_phase_summary_lines(probe))
    if probe.best is not None:
        lines.append(idat_bruteforce.super_mega_linefeed_candidate_summary_line(probe.best))
    if repair is not None:
        lines.append("-Line feed conversion repair: %s." % repair.strategy)
    return tuple(lines)


def _ultimate_linefeed_probe_summary(probe, repair=None) -> tuple[str, ...]:
    lines = [
        idat_bruteforce.ultimate_linefeed_probe_summary_line(probe),
        idat_bruteforce.ultimate_linefeed_offsets_summary_line(probe),
    ]
    if probe.best is not None:
        lines.append(idat_bruteforce.ultimate_linefeed_candidate_summary_line(probe.best))
    if probe.top_candidates:
        lines.append(
            "-%s top candidates saved for preview: %s."
            % (probe.strategy, len(probe.top_candidates))
        )
    if getattr(probe, "visual_gallery_limit", 0) > 0:
        lines.append(
            "-%s visual candidates kept: %s/%s."
            % (
                probe.strategy,
                len(getattr(probe, "visual_candidates", ())),
                probe.visual_gallery_limit,
            )
        )
        if getattr(probe, "visual_candidates", ()):
            lines.append(
                idat_bruteforce.ultimate_visual_candidate_summary_line(
                    probe.visual_candidates[0]
                )
            )
    if repair is not None:
        lines.append("-Line feed conversion repair: %s." % repair.strategy)
    return tuple(lines)


def _should_offer_linefeed_supermega_probe(salvage) -> bool:
    if salvage.recovered_scanlines < salvage.total_scanlines:
        return True
    return "reused previous row" in salvage.strategy


def _preview_ultimate_linefeed_candidate(runtime: FindMagicRuntime, repair) -> None:
    _cowsay(
        runtime,
        "Ultimate preview: this is the best visible reconstruction before I open the forbidden line-feed combinatorics vault no jutsu.",
        "com",
    )
    runtime.preview_image(
        repair.data,
        "UltimateMegaSuperLineFeedBruteForce_Before",
    )


def _linefeed_repair_is_stronger(current_repair, repair, candidate) -> bool:
    if repair.recovered_scanlines > current_repair.recovered_scanlines:
        return True
    return candidate.after.complete and not candidate.before.complete


def _linefeed_repair_is_ultimate_stronger(current_repair, repair, candidate) -> bool:
    if _linefeed_repair_is_stronger(current_repair, repair, candidate):
        return True
    return candidate.after.adler_status == "adler_match"


def _linefeed_final_salvage_is_better(current_repair, repair) -> bool:
    if repair is None:
        return False
    if getattr(repair, "data", None) == getattr(current_repair, "data", None):
        return False
    if repair.recovered_scanlines > current_repair.recovered_scanlines:
        return True
    return repair.recovered_scanlines == current_repair.recovered_scanlines


def _linefeed_final_candidate_salvage(
    runtime: FindMagicRuntime,
    summary_lines: list[str],
    force_name: str,
    candidate,
    current_repair,
):
    repair = (
        idat.rebuild_tolerant_idat_salvage(candidate.data)
        or idat.rebuild_partial_idat_blackfill(candidate.data)
    )
    if not _linefeed_final_salvage_is_better(current_repair, repair):
        return None
    _cowsay(
        runtime,
        (
            "Final IDAT salvage pass after %s kept %s/%s scanlines. "
            "I am keeping that pixel reconstruction in play."
        )
        % (force_name, repair.recovered_scanlines, repair.total_scanlines),
        "good",
    )
    summary_lines.append(
        "-Line feed conversion repair: final IDAT salvage after %s: %s."
        % (force_name, repair.strategy)
    )
    return repair


def _linefeed_bruteforce_repair(candidate):
    if candidate.after.complete:
        return idat.PartialIdatBlackfillRepair(
            data=candidate.data,
            strategy="line-feed-idat-complete recovered %s/%s scanlines"
            % (candidate.after.usable_scanlines, candidate.after.height),
            recovered_scanlines=candidate.after.usable_scanlines,
            total_scanlines=candidate.after.height,
            width=candidate.after.width,
            height=candidate.after.height,
            bit_depth=candidate.after.bit_depth,
            color_type=candidate.after.color_type,
        )
    return (
        idat.rebuild_tolerant_idat_salvage(candidate.data)
        or idat.rebuild_partial_idat_blackfill(candidate.data)
    )


def _linefeed_realign_complete_repair(realignment):
    analysis = idat.analyze_idat_stream(realignment.data)
    if not analysis.complete:
        return None
    return idat.PartialIdatBlackfillRepair(
        data=realignment.data,
        strategy="length-realigned-idat-complete recovered %s/%s scanlines"
        % (analysis.usable_scanlines, analysis.height),
        recovered_scanlines=analysis.usable_scanlines,
        total_scanlines=analysis.height,
        width=analysis.width,
        height=analysis.height,
        bit_depth=analysis.bit_depth,
        color_type=analysis.color_type,
    )


def _linefeed_length_realign_before_bruteforce(
    runtime: FindMagicRuntime,
    current_data: bytes,
    current_repair,
    summary_lines: list[str],
) -> LinefeedAlternative | None:
    realignment = repair_overlong_chunk_length_to_next_header(current_data)
    if realignment is None:
        summary_lines.append(
            "-Line feed conversion pre-bruteforce length check: no overlong IDAT length landed on a valid following chunk."
        )
        return None

    _cowsay(
        runtime,
        "Before brute force, I checked chunk length drift and found a valid following chunk. I will try that cleaner path first.",
        "com",
    )
    evidence = _linefeed_chunk_evidence(None, realignment)
    summary_lines.extend(evidence.summary_lines)
    salvage = (
        _linefeed_realign_complete_repair(realignment)
        or idat.rebuild_tolerant_idat_salvage(realignment.data)
        or idat.rebuild_partial_idat_blackfill(realignment.data)
    )
    if salvage is None:
        summary_lines.append(
            "-Line feed conversion pre-bruteforce length check: chunk chain realigned, but IDAT salvage still produced no usable image."
        )
        return None

    summary_lines.append(_linefeed_salvage_summary(realignment, salvage))
    if salvage.recovered_scanlines <= current_repair.recovered_scanlines:
        summary_lines.append(
            "-Line feed conversion pre-bruteforce length check: length realignment did not improve the current salvage."
        )
        return None

    _cowsay(
        runtime,
        "Length realignment improved the IDAT salvage to %s/%s scanlines, so I am not opening the heavier brute force branch yet."
        % (salvage.recovered_scanlines, salvage.total_scanlines),
        "good",
    )
    return LinefeedAlternative(salvage, "\n".join(summary_lines))


def _ask_linefeed_full_bruteforce(
    runtime: FindMagicRuntime,
    repair,
    start_offset: int | None,
) -> bool:
    if runtime.ask is None:
        return False

    offset_label = "unknown" if start_offset is None else "0x%x" % start_offset
    message = (
        "Current IDAT salvage is at %s/%s scanlines. If you say yes now, I launch %s around the first error anchor %s, with a pre-error margin."
        % (repair.recovered_scanlines, repair.total_scanlines, SUPER_MEGA_LINEFEED_FORCE, offset_label)
    )
    _cowsay(runtime, message, "com")
    return bool(
        runtime.ask(
            SUPER_MEGA_LINEFEED_FORCE,
            "super-mega-linefeed-force-of-death-%s-%s"
            % (offset_label, repair.recovered_scanlines),
        )
    )


def _ask_runtime_question(runtime: FindMagicRuntime, question_id: str, question_hash: str, *, skipauto: bool = False) -> bool:
    if runtime.ask is None:
        return False
    if skipauto:
        try:
            return bool(runtime.ask(question_id, question_hash, skipauto=True))
        except TypeError:
            return bool(runtime.ask(question_id, question_hash))
    return bool(runtime.ask(question_id, question_hash))


def _ask_ultimate_linefeed_bruteforce(
    runtime: FindMagicRuntime,
    repair,
    start_offset: int | None,
) -> bool:
    offset_label = "unknown" if start_offset is None else "0x%x" % start_offset
    _cowsay(runtime, "%s is the last basement door." % ULTIMATE_LINEFEED_FORCE, "bad")
    _cowsay(
        runtime,
        "This can take several billion years, several coffees, and possibly the emotional collapse of this terminal.",
        "bad",
    )
    _cowsay(
        runtime,
        "If I recover the original Adler, we get real evidence. If I do not, I may only bring back a better-looking reconstruction.",
        "com",
    )
    _cowsay(
        runtime,
        "For exact control, use -ulfb N, -ulfu, or the budget no jutsu prompt.",
        "com",
    )
    return _ask_runtime_question(
        runtime,
        ULTIMATE_LINEFEED_FORCE,
        "ultimate-mega-super-linefeed-bruteforce-%s-%s"
        % (offset_label, repair.recovered_scanlines),
        skipauto=True,
    )


def _linefeed_queue_progress(runtime: FindMagicRuntime):
    disabled = False
    built = False

    def progress(_stage: str, tested: int, budget: int) -> None:
        nonlocal built, disabled
        if disabled:
            return
        total = max(1, int(budget))
        try:
            if not built:
                runtime.loadingbar(total, len(str(total)), 0, True)
                built = True
            runtime.loadingbar(total, len(str(total)), tested, False)
        except (OSError, IndexError):
            disabled = True
            return

    return progress


def _ultimate_linefeed_progress_total(budget: int | None) -> int:
    if budget is None:
        return idat_bruteforce.UNBOUNDED_PROGRESS_TOTAL
    return max(1, int(budget))


def _prime_ultimate_linefeed_minibar(runtime: FindMagicRuntime, budget: int | None) -> None:
    total = _ultimate_linefeed_progress_total(budget)
    try:
        runtime.loadingbar(total, len(str(total)), 0, True)
        runtime.loadingbar(total, len(str(total)), 0, False)
    except (OSError, IndexError):
        return


def _ultimate_linefeed_resume_message(progress_path: str, checkpoint_path: str) -> str:
    phase = ""
    if progress_path and os.path.exists(progress_path):
        try:
            with open(progress_path, "r", encoding="utf-8") as file:
                record = json.load(file)
            if isinstance(record, dict):
                phase = str(record.get("phase", "")).strip().lower()
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            phase = ""
    if phase == "frontier":
        return "Resume checkpoint found. I am rebuilding the useful frontier before the fish counter starts moving."
    if phase == "exhaustive":
        return "Resume checkpoint found. I am jumping back into the exhaustive vault from the saved cursor."
    if phase == "complete":
        return "Resume checkpoint found. The previous Ultimate run already marked this search complete."
    if checkpoint_path and os.path.exists(checkpoint_path):
        return "Resume checkpoint found. I am rebuilding the useful candidates before the fish counter starts moving."
    return ""


def _ultimate_linefeed_checkpoint_path(runtime: FindMagicRuntime) -> str:
    try:
        return str(runtime.ultimate_checkpoint_path() or "")
    except (OSError, TypeError, ValueError):
        return ""


def _ultimate_linefeed_progress_path(runtime: FindMagicRuntime, checkpoint_path: str) -> str:
    try:
        value = str(runtime.ultimate_progress_path() or "")
    except (OSError, TypeError, ValueError):
        value = ""
    if value:
        return value
    return idat_bruteforce.ultimate_linefeed_progress_path_from_checkpoint(checkpoint_path)


def _ultimate_linefeed_source_path(runtime: FindMagicRuntime, checkpoint_path: str) -> str:
    try:
        value = str(runtime.ultimate_source_path() or "")
    except (OSError, TypeError, ValueError):
        value = ""
    if value:
        return value
    if checkpoint_path.endswith(".checkpoint.jsonl"):
        return checkpoint_path[: -len(".checkpoint.jsonl")] + ".Source.png"
    if not checkpoint_path:
        return ""
    return checkpoint_path + ".Source.png"


def _ultimate_linefeed_raw_source_path(checkpoint_path: str, source_path: str = "") -> str:
    if checkpoint_path.endswith(".checkpoint.jsonl"):
        return checkpoint_path[: -len(".checkpoint.jsonl")] + ".Source.raw"
    if source_path.endswith(".Source.png"):
        return source_path[: -len(".Source.png")] + ".Source.raw"
    if not checkpoint_path:
        return ""
    return checkpoint_path + ".Source.raw"


def _source_snapshot_preview_data(data: bytes) -> bytes:
    def preview_from(candidate: bytes) -> bytes | None:
        return ultimate_reference_ui._source_preview_data(candidate)

    preview = preview_from(data)
    if preview is not None:
        return preview
    try:
        linefeed = repair_linefeed_conversion(data, allow_partial=True)
    except Exception:
        linefeed = None
    if linefeed is not None:
        preview = preview_from(linefeed.data)
        if preview is not None:
            return preview
        try:
            realigned = repair_overlong_chunk_length_to_next_header(linefeed.data)
        except Exception:
            realigned = None
        if realigned is not None:
            preview = preview_from(realigned.data)
            if preview is not None:
                return preview
        try:
            marker_repairs = repair_idat_marker_chain_from_visible_headers(linefeed.data)
        except Exception:
            marker_repairs = ()
        for marker_repair in marker_repairs or ():
            preview = preview_from(marker_repair.data)
            if preview is not None:
                return preview
        return linefeed.data
    return data


def _write_ultimate_source_snapshot(path: str, data: bytes) -> bool:
    if not path:
        return False
    try:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        tmp_path = _hidden_tmp_path(path)
        with open(tmp_path, "wb") as file:
            file.write(_source_snapshot_preview_data(data))
        os.replace(tmp_path, path)
        return True
    except OSError:
        return False


def _write_ultimate_raw_source_snapshot(path: str, data: bytes) -> bool:
    if not path:
        return False
    try:
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        tmp_path = _hidden_tmp_path(path)
        with open(tmp_path, "wb") as file:
            file.write(data)
        os.replace(tmp_path, path)
        return True
    except OSError:
        return False


def _read_ultimate_source_snapshot(path: str) -> bytes | None:
    if not path:
        return None
    try:
        with open(path, "rb") as file:
            return file.read()
    except OSError:
        return None


def _ultimate_linefeed_should_resume(runtime: FindMagicRuntime) -> bool:
    try:
        decision = str(runtime.ultimate_resume_decision() or "").strip().lower()
    except (OSError, TypeError, ValueError):
        decision = ""
    return decision in ("resume", "auto", "ask", "")


def _format_count(value: int) -> str:
    return "%s" % format(int(value), ",")


def _normal_ultimate_linefeed_budget(
    estimate: idat_bruteforce.UltimateLinefeedSearchEstimate,
) -> idat_bruteforce.UltimateLinefeedBudgetDecision:
    return idat_bruteforce.ultimate_linefeed_budget_decision(
        estimate.total_combinations,
        "normal",
    )


def _coerce_ultimate_linefeed_budget_decision(
    value: Any,
    estimate: idat_bruteforce.UltimateLinefeedSearchEstimate,
) -> idat_bruteforce.UltimateLinefeedBudgetDecision:
    if isinstance(value, idat_bruteforce.UltimateLinefeedBudgetDecision):
        return value
    if isinstance(value, str) and value.strip().lower() in ("abort", "abandon", "quit"):
        return idat_bruteforce.ultimate_linefeed_budget_decision(
            estimate.total_combinations,
            "abort",
        )
    if value is None:
        return idat_bruteforce.ultimate_linefeed_budget_decision(
            estimate.total_combinations,
            "unbounded",
        )
    budget = int(value)
    if budget < 1:
        raise ValueError("ultimate linefeed budget must be greater than zero")
    return idat_bruteforce.UltimateLinefeedBudgetDecision(
        "override",
        budget,
        coverage=idat_bruteforce.ultimate_linefeed_budget_coverage(
            estimate.total_combinations,
            budget,
        ),
    )


def _ultimate_linefeed_budget(
    runtime: FindMagicRuntime,
    estimate: idat_bruteforce.UltimateLinefeedSearchEstimate,
) -> idat_bruteforce.UltimateLinefeedBudgetDecision:
    try:
        value = runtime.ultimate_linefeed_budget(estimate)
    except TypeError:
        try:
            value = runtime.ultimate_linefeed_budget()
        except (OSError, TypeError, ValueError):
            return _normal_ultimate_linefeed_budget(estimate)
    except (OSError, TypeError, ValueError):
        return _normal_ultimate_linefeed_budget(estimate)
    try:
        return _coerce_ultimate_linefeed_budget_decision(value, estimate)
    except (TypeError, ValueError):
        return _normal_ultimate_linefeed_budget(estimate)


def _ultimate_linefeed_reference(runtime: FindMagicRuntime) -> str:
    try:
        return str(runtime.ultimate_linefeed_reference() or "")
    except (OSError, TypeError, ValueError):
        return ""


def _ultimate_linefeed_reference_mode(runtime: FindMagicRuntime) -> str:
    try:
        mode = str(runtime.ultimate_linefeed_reference_mode() or "exact").strip().lower()
    except (OSError, TypeError, ValueError):
        mode = "exact"
    return mode if mode in ("exact", "similar") else "exact"


def _ultimate_linefeed_reference_regions(runtime: FindMagicRuntime) -> str:
    try:
        return str(runtime.ultimate_linefeed_reference_regions() or "")
    except (OSError, TypeError, ValueError):
        return ""


def _ultimate_linefeed_reference_region_editor_enabled(runtime: FindMagicRuntime) -> bool:
    try:
        return bool(runtime.ultimate_linefeed_reference_region_editor())
    except (OSError, TypeError, ValueError):
        return False


def _ultimate_linefeed_is_interactive(runtime: FindMagicRuntime) -> bool:
    try:
        return bool(runtime.ultimate_linefeed_interactive())
    except (OSError, TypeError, ValueError):
        return True


def _ultimate_linefeed_default_reference_regions_path(checkpoint_path: str) -> str:
    folder = os.path.dirname(checkpoint_path)
    if not folder:
        return idat_bruteforce.ULTIMATE_LINEFEED_REFERENCE_REGION_NAME
    return os.path.join(folder, idat_bruteforce.ULTIMATE_LINEFEED_REFERENCE_REGION_NAME)


def _ultimate_linefeed_reference_regions_path(
    runtime: FindMagicRuntime,
    checkpoint_path: str,
) -> str:
    explicit = _ultimate_linefeed_reference_regions(runtime)
    return explicit or _ultimate_linefeed_default_reference_regions_path(checkpoint_path)


def _ultimate_linefeed_regions_file_is_valid(path: str) -> bool:
    if not path or not os.path.exists(path):
        return False
    mapping, _warning = idat_bruteforce.load_ultimate_reference_regions(path)
    return mapping is not None and bool(mapping.regions)


def _prepare_ultimate_reference_regions(
    runtime: FindMagicRuntime,
    *,
    source_data: bytes,
    source_path: str,
    checkpoint_path: str,
) -> str:
    reference_path = _ultimate_linefeed_reference(runtime)
    reference_mode = _ultimate_linefeed_reference_mode(runtime)
    if reference_mode != "similar" or not reference_path:
        return ""

    regions_path = _ultimate_linefeed_reference_regions_path(runtime, checkpoint_path)
    force_editor = _ultimate_linefeed_reference_region_editor_enabled(runtime)
    if not force_editor and _ultimate_linefeed_regions_file_is_valid(regions_path):
        return regions_path

    if not _ultimate_linefeed_is_interactive(runtime):
        _cowsay(
            runtime,
            "No manual ROI mapping is ready. I will use similar auto-patch scoring for this run.",
            "com",
        )
        return ""

    _cowsay(
        runtime,
        "I need matching reference regions before similar scoring can be trusted.",
        "com",
    )
    result = runtime.ultimate_linefeed_reference_region_editor_run(
        source_path,
        reference_path,
        regions_path,
        source_data=source_data,
    )
    warning = str(getattr(result, "warning", "") or "")
    if warning:
        _cowsay(runtime, warning, "com")
    if bool(getattr(result, "saved", False)) and _ultimate_linefeed_regions_file_is_valid(regions_path):
        _cowsay(
            runtime,
            "Manual ROI mapping saved. Similar scoring will use your paired rectangles.",
            "good",
        )
        return regions_path

    _cowsay(
        runtime,
        "No manual ROI mapping was saved. I will fall back to similar auto-patch scoring.",
        "com",
    )
    return ""


def _ultimate_visual_gallery_limit(runtime: FindMagicRuntime) -> int:
    try:
        return max(0, int(runtime.ultimate_visual_gallery_limit()))
    except (OSError, TypeError, ValueError):
        return idat_bruteforce.ULTIMATE_LINEFEED_VISUAL_GALLERY_LIMIT


def _ultimate_visual_min_coverage(runtime: FindMagicRuntime) -> float:
    try:
        value = float(runtime.ultimate_visual_min_coverage())
    except (OSError, TypeError, ValueError):
        return idat_bruteforce.ULTIMATE_LINEFEED_VISUAL_MIN_COVERAGE
    return min(1.0, max(0.0, value))


def _ultimate_eta_line(eta: idat_bruteforce.UltimateLinefeedEta) -> str:
    if eta.duration == "unbounded":
        return (
            "rough ETA @ %s candidates/s: unbounded "
            "(13 billion years, I'm kidding... but not that much)"
        ) % _format_count(eta.candidates_per_second)
    return "rough ETA @ %s candidates/s: %s" % (
        _format_count(eta.candidates_per_second),
        eta.duration,
    )


def _emit_ultimate_budget_plan(
    runtime: FindMagicRuntime,
    estimate: idat_bruteforce.UltimateLinefeedSearchEstimate,
    decision: idat_bruteforce.UltimateLinefeedBudgetDecision,
    checkpoint_path: str,
    progress_path: str = "",
    visual_gallery_limit: int | None = None,
) -> None:
    selected = "unbounded" if decision.budget is None else _format_count(decision.budget)
    eta = idat_bruteforce.ultimate_linefeed_eta(decision.budget)
    mode_label = {
        "quick": "quick",
        "normal": "normal",
        "deep": "deep",
        "very_deep": "very deep",
        "deeeeeeep": "deeeeeeep",
        "abyssal": "abyssal",
        "inception": "inception",
        "manual": "manual",
        "override": "override",
        "unbounded": "no limit",
    }.get(decision.mode, decision.mode)
    lines = [
        "Ultimate budget selected:",
        "mode: %s" % mode_label,
        "selected budget: %s" % selected,
        "coverage: %.4f %%" % decision.coverage,
        _ultimate_eta_line(eta),
        "chunky forecast: %s" % eta.phrase,
        "checkpoint: %s" % ("enabled" if checkpoint_path else "disabled"),
        "progress: %s" % (progress_path if progress_path else "disabled"),
    ]
    if visual_gallery_limit is not None:
        lines.append("visual gallery cap: %s saved candidates" % _format_count(visual_gallery_limit))
    if runtime.prompt_candy is not None:
        runtime.prompt_candy("Cowsay", "\n".join(lines), "com")
        runtime.clear_dialogue_pause()
        return
    _cowsay(runtime, "\n".join(lines), "com")
    runtime.clear_dialogue_pause()


def _preview_ultimate_top_candidates(
    runtime: FindMagicRuntime,
    candidates: tuple[idat_bruteforce.SuperMegaLinefeedCandidate, ...],
) -> None:
    if not candidates:
        return
    _cowsay(runtime, "I saved the best ultimate candidates so you can judge the pixels.", "com")
    for index, candidate in enumerate(candidates[: idat_bruteforce.ULTIMATE_LINEFEED_TOP_CANDIDATES], start=1):
        runtime.preview_image(
            candidate.data,
            "UltimateCandidate_%02d_%s_scanlines_%s"
            % (index, candidate.after.usable_scanlines, candidate.after.adler_status),
        )


def _ultimate_keep_current_lines(current_repair, probe) -> tuple[str, ...]:
    current_line = "Current reconstruction already has %s/%s scanlines." % (
        current_repair.recovered_scanlines,
        current_repair.total_scanlines,
    )
    candidate = probe.best or (probe.top_candidates[0] if probe.top_candidates else None)
    if candidate is None:
        return (
            current_line,
            "Ultimate found no previewable candidate.",
            "Keeping current reconstruction.",
        )
    found_line = "Ultimate found %s/%s too, but no original Adler match." % (
        candidate.after.usable_scanlines,
        candidate.after.height,
    )
    if candidate.after.adler_status == "adler_match":
        found_line = "Ultimate found %s/%s with original Adler, but the repair output was not stronger." % (
            candidate.after.usable_scanlines,
            candidate.after.height,
        )
    return (current_line, found_line, "Keeping current reconstruction.")


def _linefeed_ultimate_alternative(
    runtime: FindMagicRuntime,
    source_data: bytes,
    current_repair,
    summary_lines: list[str],
    start_offset: int | None,
    super_probe,
) -> LinefeedAlternative:
    best = getattr(super_probe, "best", None)
    if best is not None and best.after.adler_status == "adler_match":
        return LinefeedAlternative(current_repair, "\n".join(summary_lines))
    if getattr(super_probe, "target_adler", None) is None:
        return LinefeedAlternative(current_repair, "\n".join(summary_lines))

    _preview_ultimate_linefeed_candidate(runtime, current_repair)
    if not _ask_ultimate_linefeed_bruteforce(runtime, current_repair, start_offset):
        summary_lines.append("-%s: user declined the final combinatorics vault." % ULTIMATE_LINEFEED_FORCE)
        return LinefeedAlternative(current_repair, "\n".join(summary_lines))

    return _linefeed_run_ultimate_probe(
        runtime,
        source_data,
        current_repair,
        summary_lines,
        start_offset,
        super_probe.target_adler,
        super_probe=super_probe,
    )


def _linefeed_run_ultimate_probe(
    runtime: FindMagicRuntime,
    source_data: bytes,
    current_repair,
    summary_lines: list[str],
    start_offset: int | None,
    target_adler: int | None,
    super_probe=None,
) -> LinefeedAlternative:
    estimate = idat_bruteforce.estimate_ultimate_linefeed_search(
        source_data,
        start_offset=start_offset,
        target_adler=target_adler,
        super_result=super_probe,
    )
    budget_decision = _ultimate_linefeed_budget(runtime, estimate)
    if budget_decision.aborted:
        _cowsay(runtime, "%s abandoned by budget no jutsu quit option." % ULTIMATE_LINEFEED_FORCE, "com")
        summary_lines.append("-%s: user abandoned the budget prompt." % ULTIMATE_LINEFEED_FORCE)
        return LinefeedAlternative(current_repair, "\n".join(summary_lines))

    checkpoint_path = _ultimate_linefeed_checkpoint_path(runtime)
    progress_path = _ultimate_linefeed_progress_path(runtime, checkpoint_path)
    source_path = _ultimate_linefeed_source_path(runtime, checkpoint_path)
    raw_source_path = _ultimate_linefeed_raw_source_path(checkpoint_path, source_path)
    _write_ultimate_raw_source_snapshot(raw_source_path, source_data)
    if _write_ultimate_source_snapshot(source_path, source_data):
        summary_lines.append("-%s: source snapshot saved at %s." % (ULTIMATE_LINEFEED_FORCE, source_path))
    reference_regions_path = _prepare_ultimate_reference_regions(
        runtime,
        source_data=source_data,
        source_path=source_path,
        checkpoint_path=checkpoint_path,
    )
    visual_gallery_limit = _ultimate_visual_gallery_limit(runtime)
    _emit_ultimate_budget_plan(
        runtime,
        estimate,
        budget_decision,
        checkpoint_path,
        progress_path,
        visual_gallery_limit,
    )
    runtime.candy("Title", ULTIMATE_LINEFEED_FORCE)
    _cowsay(
        runtime,
        "Opening the forbidden line-feed combinatorics vault no jutsu. I brought a checkpoint, because hope is not a persistence format.",
        "com",
    )
    if _ultimate_linefeed_should_resume(runtime):
        resume_message = _ultimate_linefeed_resume_message(progress_path, checkpoint_path)
        if resume_message:
            _cowsay(runtime, resume_message, "com")
            _cowsay(
                runtime,
                "Please don't Panic!",
                "bad",
            )
    _prime_ultimate_linefeed_minibar(runtime, budget_decision.budget)
    runtime.clear_dialogue_pause()
    try:
        probe = idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce(
            source_data,
            start_offset=start_offset,
            target_adler=target_adler,
            super_result=super_probe,
            checkpoint_path=checkpoint_path,
            budget=budget_decision.budget,
            reference_path=_ultimate_linefeed_reference(runtime),
            reference_mode=_ultimate_linefeed_reference_mode(runtime),
            reference_regions_path=reference_regions_path,
            progress=_linefeed_queue_progress(runtime),
            candidate_preview=runtime.ultimate_candidate_preview,
            progress_path=progress_path,
            resume_progress=_ultimate_linefeed_should_resume(runtime),
            visual_gallery_limit=visual_gallery_limit,
            visual_min_coverage=_ultimate_visual_min_coverage(runtime),
        )
    except (KeyboardInterrupt, idat_bruteforce.UltimateLinefeedInterrupted):
        runtime.ultimate_interrupt_cleanup()
        _cowsay(
            runtime,
            "%s stopped. I kept the progress checkpoint so the next run can resume: %s"
            % (ULTIMATE_LINEFEED_FORCE, progress_path),
            "com",
        )
        raise SystemExit(130)
    if probe.reference_warning:
        _cowsay(runtime, probe.reference_warning, "com")
    if probe.progress_warning:
        _cowsay(runtime, probe.progress_warning, "com")
    summary_lines.extend(_ultimate_linefeed_probe_summary(probe))
    if probe.best is None:
        _preview_ultimate_top_candidates(runtime, probe.top_candidates)
        _cowsay(runtime, "%s found no candidate that survived pruning." % ULTIMATE_LINEFEED_FORCE, "com")
        summary_lines.append("-%s: no candidate survived pruning." % ULTIMATE_LINEFEED_FORCE)
        return LinefeedAlternative(current_repair, "\n".join(summary_lines))

    final_salvage = _linefeed_final_candidate_salvage(
        runtime,
        summary_lines,
        ULTIMATE_LINEFEED_FORCE,
        probe.best,
        current_repair,
    )
    repair = final_salvage or _linefeed_bruteforce_repair(probe.best)
    if repair is None or (
        final_salvage is None
        and not _linefeed_repair_is_ultimate_stronger(current_repair, repair, probe.best)
    ):
        _preview_ultimate_top_candidates(runtime, probe.top_candidates)
        for line in _ultimate_keep_current_lines(current_repair, probe):
            _cowsay(runtime, line, "com")
        summary_lines.append("-%s: kept current reconstruction." % ULTIMATE_LINEFEED_FORCE)
        summary_lines.extend("-%s: %s" % (ULTIMATE_LINEFEED_FORCE, line) for line in _ultimate_keep_current_lines(current_repair, probe))
        return LinefeedAlternative(current_repair, "\n".join(summary_lines))

    if probe.best.after.adler_status == "adler_match":
        _cowsay(runtime, "%s recovered the original Adler target." % ULTIMATE_LINEFEED_FORCE, "good")
    else:
        _cowsay(runtime, "%s found a stronger visible reconstruction." % ULTIMATE_LINEFEED_FORCE, "good")
    summary_lines.append("-Line feed conversion repair: %s." % repair.strategy)
    return LinefeedAlternative(repair, "\n".join(summary_lines))


def _linefeed_full_bruteforce_alternative(
    runtime: FindMagicRuntime,
    current_data: bytes,
    current_repair,
    summary_lines: list[str],
    start_offset: int | None,
    source_data: bytes | None = None,
    known_gap_bytes: int = 0,
    known_gap_chunk_offset: int | None = None,
) -> LinefeedAlternative:
    length_alternative = _linefeed_length_realign_before_bruteforce(
        runtime,
        current_data,
        current_repair,
        summary_lines,
    )
    if length_alternative is not None:
        return length_alternative

    if not _ask_linefeed_full_bruteforce(runtime, current_repair, start_offset):
        summary_lines.append("-%s: user declined the wider IDAT line-feed brute force." % SUPER_MEGA_LINEFEED_FORCE)
        return LinefeedAlternative(current_repair, "\n".join(summary_lines))

    offset_label = "unknown" if start_offset is None else "0x%x" % start_offset
    runtime.candy("Title", SUPER_MEGA_LINEFEED_FORCE)
    _cowsay(
        runtime,
        "Launching %s around error anchor %s. I will start before it, because zlib reports where decoding fails, not necessarily where corruption began."
        % (SUPER_MEGA_LINEFEED_FORCE, offset_label),
        "com",
    )
    probe_data = source_data if source_data is not None else current_data
    probe = idat_bruteforce.probe_super_mega_linefeed_force_of_death(
        probe_data,
        start_offset=start_offset,
        known_gap_bytes=known_gap_bytes,
        known_gap_chunk_offset=known_gap_chunk_offset,
        progress=_linefeed_queue_progress(runtime),
    )
    summary_lines.extend(_super_mega_linefeed_probe_summary(probe))
    if probe.best is None:
        _cowsay(runtime, "%s did not find a stronger candidate." % SUPER_MEGA_LINEFEED_FORCE, "com")
        summary_lines.append(
            "-%s: hybrid IDAT line-feed brute force found no stronger candidate around the first error anchor."
            % SUPER_MEGA_LINEFEED_FORCE
        )
        return _linefeed_ultimate_alternative(
            runtime,
            probe_data,
            current_repair,
            summary_lines,
            start_offset,
            probe,
        )

    final_salvage = _linefeed_final_candidate_salvage(
        runtime,
        summary_lines,
        SUPER_MEGA_LINEFEED_FORCE,
        probe.best,
        current_repair,
    )
    repair = final_salvage or _linefeed_bruteforce_repair(probe.best)
    if repair is None or (
        final_salvage is None
        and not _linefeed_repair_is_stronger(current_repair, repair, probe.best)
    ):
        _cowsay(
            runtime,
            "%s did not improve the visible scanline recovery."
            % SUPER_MEGA_LINEFEED_FORCE,
            "com",
        )
        summary_lines.append(
            "-%s: hybrid IDAT line-feed brute force found no better visible salvage."
            % SUPER_MEGA_LINEFEED_FORCE
        )
        return _linefeed_ultimate_alternative(
            runtime,
            probe_data,
            current_repair,
            summary_lines,
            start_offset,
            probe,
        )

    _cowsay(
        runtime,
        "%s found a stronger candidate: %s/%s scanlines."
        % (SUPER_MEGA_LINEFEED_FORCE, repair.recovered_scanlines, repair.total_scanlines),
        "good",
    )
    summary_lines.append("-Line feed conversion repair: %s." % repair.strategy)
    if probe.best.after.adler_status != "adler_match":
        return _linefeed_ultimate_alternative(
            runtime,
            probe_data,
            repair,
            summary_lines,
            start_offset,
            probe,
        )
    return LinefeedAlternative(repair, "\n".join(summary_lines))


def _linefeed_supermega_probe_alternative(
    runtime: FindMagicRuntime,
    data: bytes,
    salvage,
    salvage_summary: str,
    realignment=None,
) -> LinefeedAlternative | None:
    if runtime.ask is None:
        return None
    if not _should_offer_linefeed_supermega_probe(salvage):
        return None

    current_data = data
    current_repair = salvage
    summary_lines = [salvage_summary]
    first_error_offset = idat_bruteforce.first_idat_problem_stream_offset(data)
    known_gap_bytes = 0
    known_gap_chunk_offset = None
    if realignment is not None and realignment.chunk_name == "IDAT":
        known_gap_bytes = max(0, int(realignment.old_length) - int(realignment.new_length))
        known_gap_chunk_offset = int(realignment.chunk_offset)
    _cowsay(
        runtime,
        "IDAT line-feed evidence is strong enough. I am launching SuperMegaLineFeedForceOfDeath directly.",
        "com",
    )
    summary_lines.append(
        "-Line feed conversion repair: using SuperMegaLineFeedForceOfDeath directly from chunk-level IDAT evidence."
    )
    return _linefeed_full_bruteforce_alternative(
        runtime,
        current_data,
        current_repair,
        summary_lines,
        first_error_offset,
        source_data=data,
        known_gap_bytes=known_gap_bytes,
        known_gap_chunk_offset=known_gap_chunk_offset,
    )


def _linefeed_signature_chunk_start(data: bytes, recovery) -> int | None:
    if recovery.signature_offset is None:
        return None
    marker = b"\x00\x00\x00\rIHDR"
    start = max(0, int(recovery.signature_offset))
    end = min(len(data), start + 32)
    offset = data.find(marker, start, end)
    if offset >= 0:
        return offset
    return None


def _defer_linefeed_signature_repair(
    runtime: FindMagicRuntime,
    context: FindMagicContext,
    recovery,
) -> bool:
    try:
        return bool(
            runtime.defer_linefeed_signature_repair(
                context.data_bytes,
                context.sample_name,
                recovery.linefeed_pattern,
            )
        )
    except (OSError, TypeError, ValueError):
        return False


def _handle_linefeed_signature_repair(
    runtime: FindMagicRuntime,
    context: FindMagicContext,
    *,
    deferred: bool = False,
) -> Any:
    repair = repair_linefeed_conversion(context.data_bytes, allow_partial=True)
    if repair is not None:
        _cowsay(
            runtime,
            "Yep. Line-feed conversion damaged the carriage returns in this PNG.",
            "bad",
        )
        summary = _linefeed_repair_summary(repair)
        if repair.validation_errors:
            marker_alternative = _linefeed_marker_chain_alternative(
                runtime,
                repair,
                summary,
            )
            if marker_alternative is not None:
                runtime.side_notes.append(marker_alternative.summary)
                return runtime.write_clone(
                    marker_alternative.repair.data.hex(),
                    marker_alternative.summary,
                )

            realignment = repair_overlong_chunk_length_to_next_header(repair.data)
            salvage = (
                idat.rebuild_tolerant_idat_salvage(realignment.data)
                or idat.rebuild_partial_idat_blackfill(realignment.data)
                if realignment is not None
                else None
            )
            if salvage is not None:
                missing = int(realignment.old_length) - int(realignment.new_length)
                if deferred:
                    _cowsay(
                        runtime,
                        (
                            "Good thing I waited for the full chunk tour: it found the real IDAT drift. "
                            "The %s length overran the next chunk by %s bytes at 0x%x."
                        )
                        % (realignment.chunk_name, missing, realignment.chunk_offset),
                        "good",
                    )
                else:
                    _cowsay(
                        runtime,
                        (
                            "The repaired chunk chain shows the real IDAT drift. "
                            "The %s length overran the next chunk by %s bytes at 0x%x."
                        )
                        % (realignment.chunk_name, missing, realignment.chunk_offset),
                        "good",
                    )
                _cowsay(
                    runtime,
                    "I shortened that chunk to %s bytes and rebuilt its PNG CRC before the IDAT salvage."
                    % realignment.new_length,
                    "good",
                )
                evidence = _linefeed_chunk_evidence(repair, realignment)
                salvage_summary = "\n".join(
                    (
                        _linefeed_salvage_summary(realignment, salvage),
                        *evidence.summary_lines,
                    )
                )
                if evidence.idat_bruteforce_allowed:
                    _cowsay(
                        runtime,
                        "I can write a valid partial IDAT salvage while the deeper branch tries to recover the remaining scanlines.",
                        "com",
                    )
                    _cowsay(
                        runtime,
                        "I have chunk-level evidence that line-feed damage reached IDAT. Now the IDAT brute force branch is allowed.",
                        "good",
                    )
                    alternative = _linefeed_supermega_probe_alternative(
                        runtime,
                        realignment.data,
                        salvage,
                        salvage_summary,
                        realignment=realignment,
                    )
                    if alternative is not None:
                        salvage = alternative.repair
                        salvage_summary = alternative.summary
                else:
                    _cowsay(
                        runtime,
                        "I only proved the PNG signature lost a carriage return. I am not opening the IDAT brute force basement without chunk-level evidence.",
                        "com",
                    )
                summary = "\n".join(
                    [
                        summary,
                        salvage_summary,
                    ]
                )
                runtime.side_notes.append(summary)
                return runtime.write_clone(salvage.data.hex(), summary)

            _cowsay(
                runtime,
                "I can repair the line-ending damage, but the result is still not a valid PNG, so I am not writing it.",
                "com",
            )
            runtime.side_notes.append(summary)
            runtime.emit(_color(runtime, "yellow", "\n-ToDo"))
            runtime.end()
            return None
        else:
            _cowsay(
                runtime,
                "I can repair the line-ending damage and write a clean clone.",
                "good",
            )
        runtime.side_notes.append(summary)
        return runtime.write_clone(repair.data.hex(), summary)

    runtime.side_notes.append(
        "-Corruption due to line feed conversion\n-File may still be recovered.\n-Not yet implemented."
    )
    runtime.emit(_color(runtime, "yellow", "\n-ToDo"))
    runtime.end()
    return None


def run_deferred_linefeed_signature_repair(runtime: FindMagicRuntime, context: FindMagicContext) -> Any:
    recovery = detect_png_signature_recovery(context.data_bytes)
    if recovery.action != "linefeed_signature_candidate":
        return None
    runtime.candy("Title", "Deferred line-feed signature repair:")
    return _handle_linefeed_signature_repair(runtime, context, deferred=True)


def run_ultimate_linefeed_direct_resume(runtime: FindMagicRuntime, context: FindMagicContext) -> Any:
    checkpoint_path = _ultimate_linefeed_checkpoint_path(runtime)
    source_path = _ultimate_linefeed_source_path(runtime, checkpoint_path)
    raw_source_path = _ultimate_linefeed_raw_source_path(checkpoint_path, source_path)
    source_data = (
        _read_ultimate_source_snapshot(raw_source_path)
        or _read_ultimate_source_snapshot(source_path)
    )
    if source_data is None:
        _cowsay(
            runtime,
            "I found a resume checkpoint, but no clean Ultimate source snapshot yet.",
            "bad",
        )
        _cowsay(
            runtime,
            "I will finish the file tour before resuming Ultimate.",
            "com",
        )
        return None

    analysis = idat.analyze_idat_stream(source_data)
    if not analysis.supported or analysis.stored_adler is None:
        _cowsay(
            runtime,
            "The Ultimate source snapshot is not a usable IDAT context. I will finish the file tour before resuming Ultimate.",
            "com",
        )
        return None

    current_repair = (
        idat.rebuild_tolerant_idat_salvage(source_data)
        or idat.rebuild_partial_idat_blackfill(source_data)
    )
    if current_repair is None and analysis.usable_scanlines > 0:
        current_repair = idat.PartialIdatBlackfillRepair(
            data=source_data,
            strategy="ultimate-source-snapshot recovered %s/%s scanlines"
            % (analysis.usable_scanlines, analysis.height),
            recovered_scanlines=analysis.usable_scanlines,
            total_scanlines=analysis.height,
            width=analysis.width,
            height=analysis.height,
            bit_depth=analysis.bit_depth,
            color_type=analysis.color_type,
        )
    if current_repair is None:
        _cowsay(
            runtime,
            "The Ultimate source snapshot did not produce a visible IDAT repair context. I will finish the file tour before resuming Ultimate.",
            "com",
        )
        return None

    start_offset = idat_bruteforce.first_idat_problem_stream_offset(source_data)
    runtime.candy("Title", "Ultimate line-feed resume:")
    _cowsay(
        runtime,
        "Resume accepted. I loaded the clean Ultimate source snapshot and I am jumping straight back to UltimateMegaSuperLineFeedBruteForce.",
        "good",
    )
    summary_lines = [
        "-%s: resumed from source snapshot %s." % (ULTIMATE_LINEFEED_FORCE, source_path),
        "-Line feed conversion repair: %s." % current_repair.strategy,
    ]
    alternative = _linefeed_run_ultimate_probe(
        runtime,
        source_data,
        current_repair,
        summary_lines,
        start_offset,
        analysis.stored_adler,
        super_probe=None,
    )
    runtime.side_notes.append(alternative.summary)
    return runtime.write_clone(alternative.repair.data.hex(), alternative.summary)


def run_find_magic(runtime: FindMagicRuntime, context: FindMagicContext) -> Any:
    runtime.candy("Title", "Looking for magic header:")
    recovery = detect_png_signature_recovery(context.data_bytes)
    magic_length = len(MAGIC)

    if recovery.action in ("found_at_start", "cut_at_signature"):
        pos = recovery.signature_hex_offset
        runtime.chunk_story("add", "PNG", pos, pos + magic_length, int(pos / 2))
        runtime.emit(
            "-%s is Magic : %s\n"
            % (
                _color(runtime, "white", context.sample_name),
                _color(runtime, "green", context.data_hex[:magic_length]),
            )
        )
        runtime.emit(
            "-Found Png Signature at offset (%s/%s/%s): (%s/%s/%s)\n"
            % (
                _color(runtime, "yellow", "Hex"),
                _color(runtime, "blue", "Bytes"),
                _color(runtime, "purple", "Index"),
                _color(runtime, "yellow", hex(int(pos / 2))),
                _color(runtime, "blue", int(pos / 2)),
                _color(runtime, "purple", pos),
            )
        )
        if recovery.action == "cut_at_signature":
            runtime.emit("-File does not start with a png signature.")
            _cowsay(runtime, " Mkay ...Things just keeps better and better ..", "bad")
            runtime.emit(
                "-Cutting %s bytes from %s since png header starts at offset %s ."
                % (
                    _color(runtime, "blue", int(pos / 2)),
                    _color(runtime, "white", context.sample_name),
                    _color(runtime, "blue", hex(int(pos / 2))),
                )
            )
            return runtime.checkpoint(*legacy_find_magic_checkpoint_args(recovery, magic_length))

        return runtime.checkpoint(*legacy_find_magic_checkpoint_args(recovery, magic_length))

    runtime.emit(
        "-File %s start with valid png signature .%s\n"
        % (_color(runtime, "red", "does not"), _chunky(runtime, "bad"))
    )
    _cowsay(runtime, " This better be a real png or else ....", "bad")

    if recovery.action == "linefeed_signature_candidate":
        if recovery.linefeed_pattern in (
            "minor_linefeed_corruption",
            "extra_cr_linefeed_corruption",
            "nul_stripped_linefeed_corruption",
        ):
            if recovery.linefeed_pattern == "extra_cr_linefeed_corruption":
                runtime.emit(
                    "-Some bytes are %s in Png Signature.."
                    % _color(runtime, "red", "extra")
                )
                _cowsay(
                    runtime,
                    " %s seems corrupted by CRLF line ending conversion...I will try to remove the injected carriage returns."
                    % _color(runtime, "white", context.sample_name),
                    "com",
                )
            elif recovery.linefeed_pattern == "nul_stripped_linefeed_corruption":
                runtime.emit(
                    "-Some bytes are %s from Png Signature.."
                    % _color(runtime, "red", "missing")
                )
                _cowsay(
                    runtime,
                    " %s seems corrupted by NUL stripping plus line-feed conversion...I will try a bounded structural reconstruction."
                    % _color(runtime, "white", context.sample_name),
                    "com",
                )
            else:
                runtime.emit(
                    "-Some bytes are %s from Png Signature.."
                    % _color(runtime, "red", "missing")
                )
                _cowsay(
                    runtime,
                    " %s seems corrupted due to line feed conversion...It doesnt look that bad...But I ll keep that in mind while im on it.."
                    % _color(runtime, "white", context.sample_name),
                    "com",
                )
            chunk_start = _linefeed_signature_chunk_start(context.data_bytes, recovery)
            if chunk_start is not None and _defer_linefeed_signature_repair(runtime, context, recovery):
                _cowsay(
                    runtime,
                    "I found enough structure to keep walking the file first. The signature repair is queued until the full chunk tour is done.",
                    "com",
                )
                runtime.side_notes.append(
                    "-FindMagic: line-feed signature repair deferred until the full chunk tour finishes."
                )
                runtime.chunk_story(
                    "add",
                    "PNG",
                    recovery.signature_hex_offset,
                    chunk_start * 2,
                    recovery.signature_offset or 0,
                )
                return runtime.checkpoint(
                    False,
                    False,
                    "FindMagic",
                    "PngSig",
                    ["-Found Magic"],
                    chunk_start * 2,
                )

            return _handle_linefeed_signature_repair(runtime, context)

        if recovery.linefeed_pattern == "major_linefeed_corruption":
            _cowsay(runtime, " Hang on a sec....This is bad news i m afraid..", "com")
            _cowsay(
                runtime,
                " %s is badly corrupted ...I cannot guarantee any results and it may take forever to find a solution..."
                % context.sample_name,
                "com",
            )
            runtime.emit(_color(runtime, "yellow", "\n-ToDo"))
            runtime.side_notes.append(
                "-Major Corruption due to line feed conversion\n-File may not be recovered.\n-Not yet implemented."
            )
            runtime.emit(_color(runtime, "yellow", "\n-ToDo"))
            runtime.end()
            return None

    _cowsay(runtime, " Ok let's dig a little bit deeper..", "bad")
    return runtime.checkpoint(*legacy_find_magic_checkpoint_args(recovery, magic_length))


def _emit_first_twenty(runtime: FindMagicRuntime, bingo_list: list[str]) -> None:
    for index in range(0, 20):
        runtime.emit(bingo_list[index])


def _run_single_candidate(
    runtime: FindMagicRuntime,
    context: FindMagicContext,
    scan: chunk_scanner.MagicBingoScan,
) -> Any:
    rebuild = chunk_scanner.rebuild_from_best_magic(
        context.data_hex,
        FULL_MAGIC,
        scan.best_signature,
    )
    runtime.emit("\n...\n")
    runtime.emit("-Done! %s\n" % _chunky(runtime, "good"))
    runtime.emit(
        "-Found at offset %s with a score of %s/32 :\n %s\n"
        % (
            _color(runtime, "blue", rebuild.offset_hex),
            _color(runtime, "green", scan.best_score),
            _color(runtime, "purple", scan.best_signature),
        )
    )
    runtime.candy(
        "Cowsay",
        " I think this is a good start to work with.Lets see where that leads us...",
        "good",
    )
    return runtime.checkpoint(
        False,
        False,
        "FindFuckingMagic",
        "PngSig",
        ["-Cutting at Magic"],
        rebuild.data_hex,
        rebuild.offset_hex,
    )


def _run_multiple_candidates(
    runtime: FindMagicRuntime,
    scan: chunk_scanner.MagicBingoScan,
) -> None:
    runtime.emit("\n\n")
    runtime.emit("\n\n...")
    _emit_first_twenty(runtime, scan.bingo_list)
    runtime.emit(
        "\n\n-Found multiple %s png signatures"
        % _color(runtime, "yellow", "potentials")
    )
    runtime.candy("Cowsay", " Looks like i gonna have to test them all.", "bad")
    runtime.emit(_color(runtime, "yellow", "\n-ToDo"))
    runtime.side_notes.append(
        "-FindFuckingMagic:Found multiple potentials png signatures\n-Not Implemented yet"
    )
    runtime.candy("Cowsay", "Erf this case is not implemented yet ...", "bad")
    runtime.end()


def _scan_known_chunks(
    runtime: FindMagicRuntime,
    context: FindMagicContext,
) -> chunk_scanner.KnownChunkScan | None:
    try:
        return chunk_scanner.scan_known_chunks_until_idat(context.data_hex, context.chunks)
    except Exception as exc:
        runtime.betterror(exc, "FindFuckingMagic")
        if context.debug is True:
            runtime.emit(_color(runtime, "red", "Error:%s") % _color(runtime, "yellow", exc))
            if context.pause_debug is True or context.pause_error is True:
                runtime.pause("Pause Debug")
        runtime.end()
        return None


def _emit_known_chunk_hits(runtime: FindMagicRuntime, scan: chunk_scanner.KnownChunkScan) -> None:
    for hit in scan.hits:
        runtime.candy("Cowsay", " Bingo!!!", "good")
        runtime.emit(
            "-Found the closest Chunk to our position:%s at offset %s %s"
            % (
                _color(runtime, "green", hit.chunk),
                _color(runtime, "blue", hit.offset_hex),
                _color(runtime, "yellow", hit.offset_byte),
            )
        )
        if hit.is_idat:
            runtime.candy(
                "Cowsay",
                "No need to go any further i think i have enough data now...",
                "com",
            )


def _handle_no_known_chunks(runtime: FindMagicRuntime) -> None:
    runtime.candy("Cowsay", " ...??Just Reach the EOF and found nothing!!", "bad")
    runtime.candy("Cowsay", "Can't do much about that sorry ...", "com")
    runtime.side_notes.append("-FindFuckingMagic:Haven't found any known png chunk in this file.")
    runtime.end()


def _handle_no_idat(runtime: FindMagicRuntime) -> None:
    runtime.candy("Cowsay", " ...??Havn't found any IDAT Chunk!!", "bad")
    runtime.candy("Cowsay", "Can't do much about that sorry ...", "com")
    runtime.side_notes.append("-FindFuckingMagic:Haven't found any IDAT chunk in this file.")
    runtime.end()


def _prepend_magic_before_nearest(
    runtime: FindMagicRuntime,
    context: FindMagicContext,
    chunks_found: dict[bytes, int],
) -> Any:
    for chunk in chunks_found:
        runtime.emit("ChunksFound Chunk:%s index:%s" % (chunk, chunks_found[chunk]))

    if chunk_scanner.missing_chunks_before_idat(chunks_found, context.before_idat):
        runtime.candy(
            "Cowsay",
            "Great...This is the worst situation..Some chunks are missing..",
            "bad",
        )
        runtime.candy("Cowsay", "Will need to take care of this later.", "com")
        runtime.candy("Cowsay", "I just hope there were no PLTE inside or Missing IDAT!", "com")
        runtime.candy(
            "Cowsay",
            "Cause i will not be able to repair this file without many years of bruteforcing !!",
            "bad",
        )
        runtime.side_notes.append("-FindFuckingMagic:Chunks known to be found before IDAT are missing.")

    runtime.candy("Cowsay", "Kay .. Let me try somthing.", "com")
    runtime.candy(
        "Cowsay",
        "Im going to prepend the PNG Chuck before the nearest Chunk and we'll see from there !",
        "good",
    )
    nearest = chunk_scanner.nearest_found_chunk(context.data_hex, chunks_found)
    length_hex = nearest.preceding_length
    spec_length = runtime.spec_length(nearest.chunk, length_hex)

    if spec_length != length_hex and not isinstance(spec_length, list):
        length_hex = spec_length
    elif isinstance(spec_length, list):
        runtime.emit(_color(runtime, "yellow", "\n-ToDo"))

    odin = chunk_scanner.prepend_magic_before_nearest(
        context.data_hex,
        MAGIC,
        length_hex,
        nearest.offset,
    )
    if context.debug is True:
        runtime.emit("New:")
        runtime.emit(odin[: nearest.offset + 64])
        runtime.emit("Old:")
        runtime.emit(context.data_hex[: nearest.offset + 64])

    return runtime.checkpoint(
        False,
        False,
        "FindFuckingMagic",
        "PngSig",
        ["-Prepending Magic"],
        odin,
        nearest.offset_hex,
    )


def _run_too_low(
    runtime: FindMagicRuntime,
    context: FindMagicContext,
    scan: chunk_scanner.MagicBingoScan,
) -> Any:
    runtime.emit("\n\n")
    _emit_first_twenty(runtime, scan.bingo_list)
    runtime.emit("\n\n-Matching score :%s" % _color(runtime, "red", "too low"))
    runtime.emit("\n...\n-Done\n")
    runtime.candy(
        "Cowsay",
        " Im afraid i wasn't able to find anything that looks like a png signature.",
        "com",
    )
    runtime.candy(
        "Cowsay",
        "Maybe i could try to find if there any Known Chunks names in this file ?",
        "good",
    )
    runtime.side_notes.append(
        "-FindFuckingMagic:Png signatures matching score are too low\nLooking for any known Chunks in file-"
    )

    known_chunk_scan = _scan_known_chunks(runtime, context)
    if known_chunk_scan is None:
        return None

    _emit_known_chunk_hits(runtime, known_chunk_scan)
    if len(known_chunk_scan.chunks_found) == 0:
        _handle_no_known_chunks(runtime)
        return None
    if known_chunk_scan.found_idat is False:
        _handle_no_idat(runtime)
        return None

    return _prepend_magic_before_nearest(runtime, context, known_chunk_scan.chunks_found)


def run_find_fucking_magic(runtime: FindMagicRuntime, context: FindMagicContext) -> Any:
    runtime.candy("Title", "Looking harder for magic header:")
    runtime.candy("Cowsay", " This may take me sometimes please wait ..", "com")
    scan = chunk_scanner.magic_bingo_scan(context.data_hex, FULL_MAGIC, progress=runtime.minibar)
    action = chunk_scanner.magic_bingo_action(scan)

    if action == "single_candidate":
        return _run_single_candidate(runtime, context, scan)
    if action == "multiple_candidates":
        return _run_multiple_candidates(runtime, scan)
    return _run_too_low(runtime, context, scan)


def build_find_magic_runtime_from_namespace(
    namespace: dict[str, Any],
    *,
    include_chunk_story: bool = False,
) -> FindMagicRuntime:
    kwargs = {}
    if include_chunk_story:
        kwargs["chunk_story"] = namespace["ChunkStory"]

    return FindMagicRuntime(
        candy=namespace["Candy"],
        emit=namespace["PRINT"],
        checkpoint=namespace["CheckPoint"],
        end=namespace["TheEnd"],
        betterror=namespace["Betterror"],
        pause=namespace["Pause"],
        spec_length=namespace["SpecLength"],
        minibar=namespace["Minibar"],
        side_notes=namespace["SideNotes"],
        write_clone=namespace["WriteClone"],
        ask=namespace.get("Question"),
        preview_image=namespace.get("Preview_Repair_Image", lambda *args, **kwargs: None),
        loadingbar=namespace.get("Loadingbar", lambda *args, **kwargs: None),
        prompt_candy=namespace.get("Prompt_Candy"),
        clear_dialogue_pause=namespace.get("Clear_Terminal_Dialogue_Pause", lambda *args, **kwargs: None),
        ultimate_checkpoint_path=namespace.get("Ultimate_Linefeed_Checkpoint_Path", lambda *args, **kwargs: ""),
        ultimate_progress_path=namespace.get("Ultimate_Linefeed_Progress_Path", lambda *args, **kwargs: ""),
        ultimate_source_path=namespace.get("Ultimate_Linefeed_Source_Path", lambda *args, **kwargs: ""),
        ultimate_resume_decision=lambda *args, **kwargs: namespace.get("ULTIMATE_LINEFEED_RESUME_DECISION", namespace.get("ULTIMATE_LINEFEED_RESUME", "ask")),
        ultimate_linefeed_budget=namespace.get(
            "Ultimate_Linefeed_Budget",
            lambda estimate=None, *args, **kwargs: idat_bruteforce.ultimate_linefeed_budget_decision(
                getattr(estimate, "total_combinations", 0),
                "normal",
            ),
        ),
        ultimate_linefeed_reference=namespace.get("Ultimate_Linefeed_Reference", lambda *args, **kwargs: ""),
        ultimate_linefeed_reference_mode=namespace.get(
            "Ultimate_Linefeed_Reference_Mode",
            lambda *args, **kwargs: namespace.get("ULTIMATE_LINEFEED_REFERENCE_MODE", "exact"),
        ),
        ultimate_linefeed_reference_regions=namespace.get(
            "Ultimate_Linefeed_Reference_Regions",
            lambda *args, **kwargs: namespace.get("ULTIMATE_LINEFEED_REFERENCE_REGIONS", ""),
        ),
        ultimate_linefeed_reference_region_editor=namespace.get(
            "Ultimate_Linefeed_Reference_Region_Editor",
            lambda *args, **kwargs: namespace.get("ULTIMATE_LINEFEED_REFERENCE_REGION_EDITOR", False),
        ),
        ultimate_linefeed_reference_region_editor_run=namespace.get(
            "Ultimate_Linefeed_Reference_Region_Editor_Run",
            lambda *args, **kwargs: ultimate_reference_ui.ReferenceRegionEditorResult(
                False,
                str(args[2]) if len(args) > 2 else "",
                "reference region editor is not wired",
            ),
        ),
        ultimate_linefeed_interactive=lambda *args, **kwargs: not namespace.get("AUTO", False)
        and not namespace.get("NODIALOGUE", False),
        ultimate_visual_gallery_limit=namespace.get(
            "Ultimate_Linefeed_Visual_Gallery_Limit",
            lambda *args, **kwargs: namespace.get(
                "ULTIMATE_LINEFEED_VISUAL_GALLERY_LIMIT",
                idat_bruteforce.ULTIMATE_LINEFEED_VISUAL_GALLERY_LIMIT,
            ),
        ),
        ultimate_visual_min_coverage=namespace.get(
            "Ultimate_Linefeed_Visual_Min_Coverage",
            lambda *args, **kwargs: namespace.get(
                "ULTIMATE_LINEFEED_VISUAL_MIN_COVERAGE",
                idat_bruteforce.ULTIMATE_LINEFEED_VISUAL_MIN_COVERAGE,
            ),
        ),
        ultimate_candidate_preview=namespace.get("Ultimate_Linefeed_Candidate_Preview"),
        ultimate_interrupt_cleanup=namespace.get("Close_Preview_Image", lambda *args, **kwargs: None),
        defer_linefeed_signature_repair=namespace.get(
            "Deferred_Linefeed_Signature_Repair",
            lambda *args, **kwargs: False,
        ),
        **kwargs,
    )


def build_find_magic_context_from_namespace(namespace: dict[str, Any]) -> FindMagicContext:
    return FindMagicContext(
        data_bytes=namespace["DATA_BYTES"],
        data_hex=namespace["DATAX"],
        chunks=tuple(namespace["CHUNKS"]),
        before_idat=tuple(namespace["BEFORE_IDAT"]),
        sample_name=namespace["Sample_Name"],
        debug=namespace["DEBUG"],
        pause_debug=namespace["PAUSEDEBUG"],
        pause_error=namespace["PAUSEERROR"],
    )


def run_find_magic_from_namespace(
    namespace: dict[str, Any],
    *,
    runner: LegacyCall = run_find_magic,
) -> Any:
    return runner(
        build_find_magic_runtime_from_namespace(namespace, include_chunk_story=True),
        build_find_magic_context_from_namespace(namespace),
    )


def run_deferred_linefeed_signature_repair_from_namespace(namespace: dict[str, Any]) -> Any:
    pending = namespace.get("DEFERRED_LINEFEED_SIGNATURE_REPAIR")
    if not pending:
        return None
    namespace["DEFERRED_LINEFEED_SIGNATURE_REPAIR"] = None
    data_bytes = pending.get("data_bytes", b"")
    return run_deferred_linefeed_signature_repair(
        build_find_magic_runtime_from_namespace(namespace, include_chunk_story=True),
        FindMagicContext(
            data_bytes=data_bytes,
            data_hex=data_bytes.hex(),
            chunks=tuple(namespace["CHUNKS"]),
            before_idat=tuple(namespace["BEFORE_IDAT"]),
            sample_name=str(pending.get("sample_name") or namespace.get("Sample", "")),
            debug=namespace["DEBUG"],
            pause_debug=namespace["PAUSEDEBUG"],
            pause_error=namespace["PAUSEERROR"],
        ),
    )


def run_ultimate_linefeed_direct_resume_from_namespace(namespace: dict[str, Any]) -> Any:
    return run_ultimate_linefeed_direct_resume(
        build_find_magic_runtime_from_namespace(namespace, include_chunk_story=True),
        build_find_magic_context_from_namespace(namespace),
    )


def run_find_fucking_magic_from_namespace(
    namespace: dict[str, Any],
    *,
    runner: LegacyCall = run_find_fucking_magic,
) -> Any:
    return runner(
        build_find_magic_runtime_from_namespace(namespace),
        build_find_magic_context_from_namespace(namespace),
    )
