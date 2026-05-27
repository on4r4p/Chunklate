from __future__ import annotations

from dataclasses import dataclass
import zlib
from typing import Callable

from . import idat
from . import png


ProgressCallback = Callable[[int, int, bool], None]
QueueProgressCallback = Callable[[str, int, int], None]


@dataclass(frozen=True)
class IdatDeflateCandidate:
    data: bytes
    stream_offset: int
    file_offset: int
    idat_index: int
    idat_offset: int
    old_byte: int
    new_byte: int
    before: idat.IdatStreamAnalysis
    after: idat.IdatStreamAnalysis


@dataclass(frozen=True)
class IdatDeflateProbeResult:
    before: idat.IdatStreamAnalysis
    best: IdatDeflateCandidate | None
    window_start: int
    window_end: int
    tested_candidates: int
    budget_exhausted: bool
    strategy: str = "strict-byte"
    reason: str = ""
    chain: tuple[IdatDeflateCandidate, ...] = ()

    @property
    def improved(self) -> bool:
        return self.best is not None


def analysis_score(analysis: idat.IdatStreamAnalysis) -> tuple[int, int, int, int, int]:
    return (
        1 if analysis.complete else 0,
        analysis.usable_scanlines,
        analysis.complete_scanlines,
        analysis.decompressed_size,
        analysis.error_offset if analysis.error_offset is not None else -1,
    )


def _status_rank(status: str) -> int:
    return {
        "bad_zlib_header": 0,
        "corrupt_deflate": 1,
        "incomplete_stream": 2,
        "bad_adler": 3,
        "partial": 4,
        "complete": 5,
    }.get(status, -1)


def is_material_improvement(before: idat.IdatStreamAnalysis, after: idat.IdatStreamAnalysis) -> bool:
    if not after.supported:
        return False
    if after.complete and not before.complete:
        return True
    if after.usable_scanlines > before.usable_scanlines:
        return True
    if after.complete_scanlines > before.complete_scanlines:
        return True
    if after.decompressed_size > before.decompressed_size:
        return True

    before_rank = _status_rank(before.status)
    after_rank = _status_rank(after.status)
    return after_rank > before_rank and after.decompressed_size >= before.decompressed_size


def _idat_chunks_and_stream(data: bytes) -> tuple[tuple[png.PngChunk, ...], bytes]:
    chunks = tuple(png.iter_chunks(data))
    idat_chunks = tuple(chunk for chunk in chunks if chunk.chunk_type == b"IDAT")
    return idat_chunks, b"".join(chunk.data for chunk in idat_chunks)


def _locate_idat_stream_offset(
    idat_chunks: tuple[png.PngChunk, ...],
    stream_offset: int,
) -> tuple[png.PngChunk, int, int] | None:
    remaining = stream_offset
    for index, chunk in enumerate(idat_chunks, start=1):
        if remaining < chunk.length:
            return chunk, index, remaining
        remaining -= chunk.length
    return None


def mutate_idat_stream_byte(data: bytes, stream_offset: int, new_byte: int) -> IdatDeflateCandidate | None:
    before = idat.analyze_idat_stream(data)
    if stream_offset < 0:
        return None

    try:
        idat_chunks, idat_stream = _idat_chunks_and_stream(data)
    except png.PngFormatError:
        return None

    if stream_offset >= len(idat_stream):
        return None

    location = _locate_idat_stream_offset(idat_chunks, stream_offset)
    if location is None:
        return None

    chunk, idat_index, idat_offset = location
    old_byte = idat_stream[stream_offset]
    if old_byte == new_byte:
        return None

    file_offset = chunk.offset + 8 + idat_offset
    candidate = bytearray(data)
    candidate[file_offset] = new_byte

    payload_start = chunk.offset + 8
    payload_end = payload_start + chunk.length
    crc_offset = payload_end
    repaired_crc = zlib.crc32(chunk.chunk_type + bytes(candidate[payload_start:payload_end])) & 0xFFFFFFFF
    candidate[crc_offset : crc_offset + 4] = repaired_crc.to_bytes(4, "big")

    candidate_data = bytes(candidate)
    return IdatDeflateCandidate(
        data=candidate_data,
        stream_offset=stream_offset,
        file_offset=file_offset,
        idat_index=idat_index,
        idat_offset=idat_offset,
        old_byte=old_byte,
        new_byte=new_byte,
        before=before,
        after=idat.analyze_idat_stream(candidate_data),
    )


def probe_idat_deflate_byte_candidates(
    data: bytes,
    *,
    window_radius: int = 16,
    budget: int = 10000,
    strategy: str = "strict-byte",
    progress: QueueProgressCallback | None = None,
) -> IdatDeflateProbeResult:
    before = idat.analyze_idat_stream(data)
    if not before.supported:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, before.reason)
    if before.complete:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, "IDAT stream is already complete")
    if before.error_offset is None:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, "IDAT error offset is unknown")

    try:
        _idat_chunks, idat_stream = _idat_chunks_and_stream(data)
    except png.PngFormatError as exc:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, str(exc))

    center = min(max(0, before.error_offset), max(0, len(idat_stream) - 1))
    window_start = max(0, center - window_radius)
    window_end = min(len(idat_stream), center + window_radius + 1)
    before_score = analysis_score(before)
    best: IdatDeflateCandidate | None = None
    best_score = before_score
    tested = 0
    budget_exhausted = False

    if progress is not None:
        progress(strategy, 0, budget)

    for stream_offset in range(window_start, window_end):
        old_byte = idat_stream[stream_offset]
        for new_byte in range(256):
            if new_byte == old_byte:
                continue
            if tested >= budget:
                budget_exhausted = True
                return IdatDeflateProbeResult(
                    before,
                    best,
                    window_start,
                    window_end,
                    tested,
                    budget_exhausted,
                    strategy,
                )

            tested += 1
            if progress is not None and tested % 100 == 0:
                progress(strategy, tested, budget)
            candidate = mutate_idat_stream_byte(data, stream_offset, new_byte)
            if candidate is None:
                continue

            if not is_material_improvement(before, candidate.after):
                continue

            candidate_score = analysis_score(candidate.after)
            if candidate_score > best_score:
                best = candidate
                best_score = candidate_score
                if candidate.after.complete:
                    if progress is not None:
                        progress(strategy, tested, budget)
                    return IdatDeflateProbeResult(
                        before,
                        best,
                        window_start,
                        window_end,
                        tested,
                        budget_exhausted,
                        strategy,
                    )

    if progress is not None:
        progress(strategy, tested, budget)
    return IdatDeflateProbeResult(before, best, window_start, window_end, tested, budget_exhausted, strategy)


def probe_idat_deflate_bit_candidates(
    data: bytes,
    *,
    backtrack: int = 128,
    forward: int = 8,
    budget: int = 4096,
    strategy: str = "pre-error-bit",
    progress: QueueProgressCallback | None = None,
) -> IdatDeflateProbeResult:
    before = idat.analyze_idat_stream(data)
    if not before.supported:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, before.reason)
    if before.complete:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, "IDAT stream is already complete")
    if before.error_offset is None:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, "IDAT error offset is unknown")

    try:
        _idat_chunks, idat_stream = _idat_chunks_and_stream(data)
    except png.PngFormatError as exc:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, str(exc))

    center = min(max(0, before.error_offset), max(0, len(idat_stream) - 1))
    window_start = max(0, center - backtrack)
    window_end = min(len(idat_stream), center + forward + 1)
    before_score = analysis_score(before)
    best: IdatDeflateCandidate | None = None
    best_score = before_score
    tested = 0
    budget_exhausted = False

    if progress is not None:
        progress(strategy, 0, budget)

    for stream_offset in range(window_start, window_end):
        old_byte = idat_stream[stream_offset]
        for bit in range(8):
            if tested >= budget:
                budget_exhausted = True
                return IdatDeflateProbeResult(
                    before,
                    best,
                    window_start,
                    window_end,
                    tested,
                    budget_exhausted,
                    strategy,
                )

            tested += 1
            if progress is not None and tested % 100 == 0:
                progress(strategy, tested, budget)
            candidate = mutate_idat_stream_byte(data, stream_offset, old_byte ^ (1 << bit))
            if candidate is None:
                continue
            if not is_material_improvement(before, candidate.after):
                continue

            candidate_score = analysis_score(candidate.after)
            if candidate_score > best_score:
                best = candidate
                best_score = candidate_score
                if candidate.after.complete:
                    if progress is not None:
                        progress(strategy, tested, budget)
                    return IdatDeflateProbeResult(
                        before,
                        best,
                        window_start,
                        window_end,
                        tested,
                        budget_exhausted,
                        strategy,
                    )

    if progress is not None:
        progress(strategy, tested, budget)
    return IdatDeflateProbeResult(before, best, window_start, window_end, tested, budget_exhausted, strategy)


def probe_idat_deflate_heavy_candidates(
    data: bytes,
    *,
    backtrack: int = 2048,
    forward: int = 256,
    budget: int = 250000,
    strategy: str = "heavy-byte",
    progress: ProgressCallback | None = None,
) -> IdatDeflateProbeResult:
    before = idat.analyze_idat_stream(data)
    if not before.supported:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, before.reason)
    if before.complete:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, "IDAT stream is already complete")
    if before.error_offset is None:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, "IDAT error offset is unknown")

    try:
        _idat_chunks, idat_stream = _idat_chunks_and_stream(data)
    except png.PngFormatError as exc:
        return IdatDeflateProbeResult(before, None, 0, 0, 0, False, strategy, str(exc))

    center = min(max(0, before.error_offset), max(0, len(idat_stream) - 1))
    window_start = max(0, center - backtrack)
    window_end = min(len(idat_stream), center + forward + 1)
    before_score = analysis_score(before)
    best: IdatDeflateCandidate | None = None
    best_score = before_score
    tested = 0
    budget_exhausted = False

    if progress is not None:
        progress(0, budget, True)

    for stream_offset in range(window_start, window_end):
        old_byte = idat_stream[stream_offset]
        for new_byte in range(256):
            if new_byte == old_byte:
                continue
            if tested >= budget:
                budget_exhausted = True
                if progress is not None:
                    progress(tested, budget, False)
                return IdatDeflateProbeResult(
                    before,
                    best,
                    window_start,
                    window_end,
                    tested,
                    budget_exhausted,
                    strategy,
                )

            tested += 1
            if progress is not None and tested % 100 == 0:
                progress(tested, budget, False)

            candidate = mutate_idat_stream_byte(data, stream_offset, new_byte)
            if candidate is None:
                continue
            if not is_material_improvement(before, candidate.after):
                continue

            candidate_score = analysis_score(candidate.after)
            if candidate_score > best_score:
                best = candidate
                best_score = candidate_score
                if candidate.after.complete:
                    if progress is not None:
                        progress(tested, budget, False)
                    return IdatDeflateProbeResult(
                        before,
                        best,
                        window_start,
                        window_end,
                        tested,
                        budget_exhausted,
                        strategy,
                    )

    if progress is not None:
        progress(tested, budget, False)
    return IdatDeflateProbeResult(before, best, window_start, window_end, tested, budget_exhausted, strategy)


def probe_idat_deflate_single_pass(
    data: bytes,
    *,
    progress: QueueProgressCallback | None = None,
) -> IdatDeflateProbeResult:
    strict = probe_idat_deflate_byte_candidates(
        data,
        window_radius=16,
        budget=10000,
        strategy="strict-byte",
        progress=progress,
    )
    if strict.best is not None:
        return strict

    bit = probe_idat_deflate_bit_candidates(data, progress=progress)
    if bit.best is not None:
        return bit

    wider = probe_idat_deflate_byte_candidates(
        data,
        window_radius=64,
        budget=32768,
        strategy="wide-byte",
        progress=progress,
    )
    if wider.best is not None:
        return wider

    return IdatDeflateProbeResult(
        strict.before,
        None,
        min(strict.window_start, wider.window_start),
        max(strict.window_end, wider.window_end),
        strict.tested_candidates + bit.tested_candidates + wider.tested_candidates,
        strict.budget_exhausted or bit.budget_exhausted or wider.budget_exhausted,
        "strategy-queue",
        wider.reason or bit.reason or strict.reason,
    )


def probe_idat_deflate_strategy_queue(
    data: bytes,
    *,
    max_steps: int = 4,
    progress: QueueProgressCallback | None = None,
) -> IdatDeflateProbeResult:
    original = idat.analyze_idat_stream(data)
    current_data = data
    chain: list[IdatDeflateCandidate] = []
    total_tested = 0
    budget_exhausted = False
    last_result: IdatDeflateProbeResult | None = None

    for _step in range(max_steps):
        result = probe_idat_deflate_single_pass(current_data, progress=progress)
        last_result = result
        total_tested += result.tested_candidates
        budget_exhausted = budget_exhausted or result.budget_exhausted
        if result.best is None:
            break

        chain.append(result.best)
        current_data = result.best.data
        if result.best.after.complete:
            break

    if chain:
        best = chain[-1]
        if len(chain) == 1:
            return IdatDeflateProbeResult(
                original,
                best,
                last_result.window_start if last_result else 0,
                last_result.window_end if last_result else 0,
                total_tested,
                budget_exhausted,
                last_result.strategy if last_result else "strategy-queue",
                last_result.reason if last_result else "",
                tuple(chain),
            )
        return IdatDeflateProbeResult(
            original,
            best,
            0,
            best.stream_offset + 1,
            total_tested,
            budget_exhausted,
            "chase",
            "",
            tuple(chain),
        )

    if last_result is None:
        return IdatDeflateProbeResult(original, None, 0, 0, 0, False, "strategy-queue", "IDAT strategy queue did not run")
    return IdatDeflateProbeResult(
        original,
        None,
        last_result.window_start,
        last_result.window_end,
        total_tested,
        budget_exhausted,
        "strategy-queue",
        last_result.reason,
    )


def probe_summary_line(result: IdatDeflateProbeResult) -> str:
    line = (
        "-IDAT deflate probe: strategy=%s; window=0x%x..0x%x; tested=%s"
        % (result.strategy, result.window_start, result.window_end, result.tested_candidates)
    )
    if result.budget_exhausted:
        line += "; budget exhausted"
    if result.reason:
        line += "; reason=%s" % result.reason
    return line + "."


def candidate_summary_line(candidate: IdatDeflateCandidate) -> str:
    return (
        "-IDAT deflate candidate: stream=0x%x; file=0x%x; IDAT=%s; byte %02x -> %02x; "
        "status %s -> %s; scanlines %s/%s -> %s/%s; error_offset %s -> %s."
        % (
            candidate.stream_offset,
            candidate.file_offset,
            candidate.idat_index,
            candidate.old_byte,
            candidate.new_byte,
            candidate.before.status,
            candidate.after.status,
            candidate.before.usable_scanlines,
            candidate.before.height,
            candidate.after.usable_scanlines,
            candidate.after.height,
            candidate.before.error_offset,
            candidate.after.error_offset,
        )
    )


def candidate_summary_lines(result: IdatDeflateProbeResult) -> tuple[str, ...]:
    if result.chain:
        return tuple(candidate_summary_line(candidate) for candidate in result.chain)
    if result.best is not None:
        return (candidate_summary_line(result.best),)
    return ()
