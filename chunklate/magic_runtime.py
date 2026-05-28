from __future__ import annotations

from collections.abc import Callable, MutableSequence
from dataclasses import dataclass
from typing import Any

from . import idat
from . import idat_bruteforce
from . import chunk_scanner
from .png import (
    detect_png_signature_recovery,
    legacy_find_magic_checkpoint_args,
    repair_linefeed_conversion,
    repair_overlong_chunk_length_to_next_header,
)


LegacyCall = Callable[..., Any]

MAGIC = "89504e470d0a1a0a"
FULL_MAGIC = "89504e470d0a1a0a0000000d49484452"
SUPER_MEGA_LINEFEED_FORCE = "SuperMegaLineFeedForceOfDeath"
ULTIMATE_LINEFEED_FORCE = "UltimateMegaSuperLineFeedBruteForce"


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
    ultimate_checkpoint_path: LegacyCall = lambda *args, **kwargs: ""
    ultimate_linefeed_budget: LegacyCall = lambda *args, **kwargs: 50000


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


def _linefeed_heavy_probe_summary(probe, repair) -> tuple[str, ...]:
    lines = [idat_bruteforce.linefeed_insert_probe_summary_line(probe)]
    if probe.best is not None:
        lines.append(idat_bruteforce.linefeed_insert_candidate_summary_line(probe.best))
    lines.append("-Line feed conversion repair: %s." % repair.strategy)
    return tuple(lines)


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
    if repair is not None:
        lines.append("-Line feed conversion repair: %s." % repair.strategy)
    return tuple(lines)


def _should_offer_linefeed_heavy_probe(salvage) -> bool:
    if salvage.recovered_scanlines < salvage.total_scanlines:
        return True
    return "reused previous row" in salvage.strategy


def _preview_linefeed_candidate(runtime: FindMagicRuntime, repair, round_index: int) -> None:
    _cowsay(
        runtime,
        "Current IDAT repair preview: %s/%s scanlines. Look at it, then decide if I should push further."
        % (repair.recovered_scanlines, repair.total_scanlines),
        "com",
    )
    runtime.preview_image(
        repair.data,
        "LineFeed_IDAT_%02d_%s_of_%s"
        % (round_index, repair.recovered_scanlines, repair.total_scanlines),
    )


def _preview_ultimate_linefeed_candidate(runtime: FindMagicRuntime, repair) -> None:
    _cowsay(
        runtime,
        "Ultimate preview: this is the best visible reconstruction before I open the forbidden line-feed combinatorics vault.",
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
    _cowsay(
        runtime,
        "Focused line-feed probing is at %s/%s scanlines. If you say yes now, I launch %s around the first error anchor %s, with a pre-error margin."
        % (repair.recovered_scanlines, repair.total_scanlines, SUPER_MEGA_LINEFEED_FORCE, offset_label),
        "com",
    )
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
    _cowsay(
        runtime,
        (
            "%s is the last basement door. This can take several billion years, "
            "several coffees, and possibly the emotional collapse of this terminal. "
            "If I recover the original Adler, we get real evidence. If I do not, "
            "I may only bring back a better-looking reconstruction. "
            "By default I try 50000 candidates, because even chaos deserves a receipt. "
            "If you want me to go much further, rerun with --ultimate-linefeed-budget 1000000000000. "
            "If you really want the no-ceiling vault, rerun with --ultimate-linefeed-unbounded."
        )
        % ULTIMATE_LINEFEED_FORCE,
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

    def progress(_stage: str, tested: int, budget: int) -> None:
        nonlocal disabled
        if disabled:
            return
        total = max(1, int(budget))
        try:
            runtime.loadingbar(total, len(str(total)), tested, tested == 0)
        except (OSError, IndexError):
            disabled = True
            return

    return progress


def _ultimate_linefeed_checkpoint_path(runtime: FindMagicRuntime) -> str:
    try:
        return str(runtime.ultimate_checkpoint_path() or "")
    except (OSError, TypeError, ValueError):
        return ""


def _ultimate_linefeed_budget(runtime: FindMagicRuntime) -> int | None:
    try:
        return runtime.ultimate_linefeed_budget()
    except (OSError, TypeError, ValueError):
        return 50000


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

    runtime.candy("Title", ULTIMATE_LINEFEED_FORCE)
    _cowsay(
        runtime,
        "Opening the forbidden line-feed combinatorics vault. I brought a checkpoint, because hope is not a persistence format.",
        "com",
    )
    probe = idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce(
        source_data,
        start_offset=start_offset,
        target_adler=super_probe.target_adler,
        super_result=super_probe,
        checkpoint_path=_ultimate_linefeed_checkpoint_path(runtime),
        budget=_ultimate_linefeed_budget(runtime),
        progress=_linefeed_queue_progress(runtime),
    )
    summary_lines.extend(_ultimate_linefeed_probe_summary(probe))
    if probe.best is None:
        _cowsay(runtime, "%s found no candidate that survived pruning." % ULTIMATE_LINEFEED_FORCE, "com")
        summary_lines.append("-%s: no candidate survived pruning." % ULTIMATE_LINEFEED_FORCE)
        return LinefeedAlternative(current_repair, "\n".join(summary_lines))

    repair = _linefeed_bruteforce_repair(probe.best)
    if repair is None or not _linefeed_repair_is_ultimate_stronger(current_repair, repair, probe.best):
        _cowsay(runtime, "%s did not beat the current reconstruction." % ULTIMATE_LINEFEED_FORCE, "com")
        summary_lines.append("-%s: kept current reconstruction." % ULTIMATE_LINEFEED_FORCE)
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

    repair = _linefeed_bruteforce_repair(probe.best)
    if repair is None or not _linefeed_repair_is_stronger(current_repair, repair, probe.best):
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


def _linefeed_heavy_probe_alternative(
    runtime: FindMagicRuntime,
    data: bytes,
    salvage,
    salvage_summary: str,
    realignment=None,
) -> LinefeedAlternative | None:
    if runtime.ask is None:
        return None
    if not _should_offer_linefeed_heavy_probe(salvage):
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
    max_rounds = 8

    for round_index in range(max_rounds):
        _preview_linefeed_candidate(runtime, current_repair, round_index)
        if not runtime.ask(
            "LineFeed Heavy Probe",
            "linefeed-cr-insert-%s-%s"
            % (round_index, current_repair.recovered_scanlines),
        ):
            if current_repair is salvage and len(summary_lines) == 1:
                return None
            return LinefeedAlternative(current_repair, "\n".join(summary_lines))

        runtime.candy("Title", "LineFeed Heavy Probe")
        _cowsay(runtime, "Trying focused line-feed brute force on the IDAT stream.", "com")
        probe = idat_bruteforce.probe_idat_linefeed_cr_insertions(current_data)
        if probe.best is None:
            _cowsay(runtime, "No stronger line-feed candidate found in that window.", "com")
            summary_lines.append(idat_bruteforce.linefeed_insert_probe_summary_line(probe))
            summary_lines.append(
                "-Line feed conversion repair: focused IDAT line-feed probe found no stronger candidate."
            )
            _preview_linefeed_candidate(runtime, current_repair, round_index + 1)
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

        repair = _linefeed_bruteforce_repair(probe.best)
        if repair is None or not _linefeed_repair_is_stronger(current_repair, repair, probe.best):
            _cowsay(runtime, "Focused line-feed probing did not improve the visible scanline recovery.", "com")
            summary_lines.extend(_linefeed_heavy_probe_summary(probe, current_repair))
            summary_lines.append(
                "-Line feed conversion repair: focused IDAT line-feed probe found no better visible salvage."
            )
            _preview_linefeed_candidate(runtime, current_repair, round_index + 1)
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
        _cowsay(
            runtime,
            "Found a stronger line-feed candidate: %s/%s scanlines."
            % (repair.recovered_scanlines, repair.total_scanlines),
            "good",
        )
        summary_lines.extend(_linefeed_heavy_probe_summary(probe, repair))
        current_data = probe.best.data
        current_repair = repair
        if probe.best.after.complete:
            _cowsay(runtime, "The IDAT stream is complete now. No need to push this branch further.", "good")
            return LinefeedAlternative(current_repair, "\n".join(summary_lines))
        if repair.recovered_scanlines >= repair.total_scanlines:
            _preview_linefeed_candidate(runtime, current_repair, round_index + 1)
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

    _cowsay(runtime, "Reached the line-feed probe round limit for this IDAT branch.", "com")
    summary_lines.append("-Line feed conversion repair: reached line-feed IDAT probe round limit.")
    _preview_linefeed_candidate(runtime, current_repair, max_rounds)
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
        if recovery.linefeed_pattern == "minor_linefeed_corruption":
            runtime.emit(
                "-Some bytes are %s from Png Signature.."
                % _color(runtime, "red", "missing")
            )
            _cowsay(
                runtime,
                " %s seems corrupted due to line feed conversion...It doesnt look that bad...But I ll keep that in mind while im on it.."
                % _color(runtime, "white", context.sample_name),
            )
            repair = repair_linefeed_conversion(context.data_bytes, allow_partial=True)
            if repair is not None:
                _cowsay(
                    runtime,
                    "Yep. Line-feed conversion chewed some carriage returns out of this PNG.",
                    "com",
                )
                summary = _linefeed_repair_summary(repair)
                if repair.validation_errors:
                    realignment = repair_overlong_chunk_length_to_next_header(repair.data)
                    salvage = (
                        idat.rebuild_tolerant_idat_salvage(realignment.data)
                        or idat.rebuild_partial_idat_blackfill(realignment.data)
                        if realignment is not None
                        else None
                    )
                    if salvage is not None:
                        _cowsay(
                            runtime,
                            "The missing bytes cannot be recovered cleanly, but I can write a valid partial IDAT salvage.",
                            "com",
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
                                "I have chunk-level evidence that line-feed damage reached IDAT. Now the IDAT brute force branch is allowed.",
                                "com",
                            )
                            alternative = _linefeed_heavy_probe_alternative(
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
                        "I can restore the signature CR, but the result is still not a valid PNG, so I am not writing it.",
                        "com",
                    )
                    runtime.side_notes.append(summary)
                    runtime.emit(_color(runtime, "yellow", "\n-ToDo"))
                    runtime.end()
                    return None
                else:
                    _cowsay(
                        runtime,
                        "I can put those CR bytes back where the CRCs agree and write a clean clone.",
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

    if spec_length != length_hex and type(spec_length) != list:
        length_hex = spec_length
    elif type(spec_length) == list:
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
        ultimate_checkpoint_path=namespace.get("Ultimate_Linefeed_Checkpoint_Path", lambda *args, **kwargs: ""),
        ultimate_linefeed_budget=namespace.get("Ultimate_Linefeed_Budget", lambda *args, **kwargs: 50000),
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


def run_find_fucking_magic_from_namespace(
    namespace: dict[str, Any],
    *,
    runner: LegacyCall = run_find_fucking_magic,
) -> Any:
    return runner(
        build_find_magic_runtime_from_namespace(namespace),
        build_find_magic_context_from_namespace(namespace),
    )
