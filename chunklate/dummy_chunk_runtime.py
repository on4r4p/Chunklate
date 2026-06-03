from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import dummy_chunk
from . import idat
from . import idat_bruteforce


LegacyCall = Callable[..., Any]


@dataclass(frozen=True)
class DummyChunkRuntime:
    data_hex: str
    side_notes: list[Any]
    candy: LegacyCall
    emit: LegacyCall
    checkpoint: LegacyCall
    end: LegacyCall
    pause: LegacyCall
    get_spec: LegacyCall
    spec_length: LegacyCall
    random_sample: LegacyCall
    repair_note: LegacyCall
    debug: bool = False
    pause_debug: bool = False
    question: LegacyCall | None = None
    file_origin: Any = ""
    write_clone: LegacyCall | None = None


def checkpoint_dummy_chunk(
    runtime: DummyChunkRuntime,
    chunk_name: bytes,
    *,
    solved: bool,
    fixed_data_hex: str,
    dummy_data_length: int,
    bad_pos: int,
    bad_start: int,
    bad_end: int,
    from_error: Any,
    info: list[str] | None = None,
) -> Any:
    return runtime.checkpoint(
        True,
        solved,
        "DummyChunk",
        chunk_name,
        ["Filling with a dummy chunk"] if info is None else info,
        fixed_data_hex,
        dummy_data_length,
        bad_pos,
        bad_start,
        bad_end,
        from_error,
    )


def emit_fake_data_ready(runtime: DummyChunkRuntime) -> None:
    runtime.candy(
        "Cowsay",
        "Fake datas ready to be served! Bonne appetit !",
        "good",
    )


def emit_todo_and_end(runtime: DummyChunkRuntime) -> Any:
    runtime.emit(runtime.candy("Color", "yellow", "\n-ToDo"))
    return runtime.end()


def append_repair_note(runtime: DummyChunkRuntime, decision: dummy_chunk.DummyChunkDecision) -> None:
    if decision.repair is not None:
        runtime.side_notes.append(runtime.repair_note(decision.repair))


def emit_debug_build(
    runtime: DummyChunkRuntime,
    chunk_name: bytes,
    build: dummy_chunk.LegacyDummyChunkBuild,
    bad_pos: int,
    bad_start: int,
    bad_end: int,
) -> None:
    if not runtime.debug:
        return

    if chunk_name != b"IEND":
        runtime.emit("chunklen_spec:%s" % str(build.chunklen_spec))
        runtime.emit("chunk_format:%s" % str(build.chunk_format))
        runtime.emit("color_type:%s" % str(build.color_type))
    runtime.emit("dumylen:%s" % build.dummy_length)
    runtime.emit("dumyname:%s" % build.dummy_name)
    runtime.emit("dumydata:%s" % build.dummy_data)
    runtime.emit("dumycrc:%s" % build.dummy_crc)
    runtime.emit("bad_start:%s" % bad_start)
    runtime.emit("bad_end:%s" % bad_end)
    runtime.emit("dumdum:%s" % build.chunk_hex)
    runtime.emit("bad pos:%s" % bad_pos)
    runtime.emit("datax:%s" % runtime.data_hex[bad_start:bad_end])

    if runtime.pause_debug:
        runtime.pause("Pause Debug")


def build_legacy_dummy(
    runtime: DummyChunkRuntime,
    chunk_name: bytes,
) -> dummy_chunk.LegacyDummyChunkBuild | None:
    if chunk_name == b"IHDR":
        return dummy_chunk.build_legacy_ihdr_dummy(
            chunk_name,
            get_spec=runtime.get_spec,
            spec_length=runtime.spec_length,
            random_sample=runtime.random_sample,
        )

    return None


def _dedupe_paths(paths: list[Path]) -> tuple[Path, ...]:
    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        try:
            key = str(path.resolve())
        except OSError:
            key = str(path)
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return tuple(unique)


def _truncated_idat_donor_roots(file_origin: Any) -> tuple[Path, ...]:
    roots: list[Path] = []
    origin_text = str(file_origin or "")
    if origin_text:
        origin = Path(origin_text)
        if not origin.is_absolute():
            origin = Path.cwd() / origin
        roots.append(origin.parent)
        for parent in origin.parents[:4]:
            roots.append(parent)
            roots.append(parent / "schaik-javapng-samples")
    roots.append(Path.cwd() / "schaik-javapng-samples")
    return _dedupe_paths(roots)


def _truncated_idat_donor_paths(file_origin: Any) -> tuple[Path, ...]:
    candidates: list[Path] = []
    origin_text = str(file_origin or "")
    try:
        origin_resolved = str(Path(origin_text).resolve()) if origin_text else ""
    except OSError:
        origin_resolved = origin_text

    for root in _truncated_idat_donor_roots(file_origin):
        if not root.is_dir():
            continue
        for path in sorted(root.glob("*.png")):
            try:
                resolved = str(path.resolve())
            except OSError:
                resolved = str(path)
            if resolved == origin_resolved:
                continue
            candidates.append(path)

    unique = _dedupe_paths(candidates)
    clean = tuple(path for path in unique if "brokenjavapngsuite" not in path.parts)
    broken = tuple(path for path in unique if "brokenjavapngsuite" in path.parts)
    return clean + broken


def _relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def _local_truncated_idat_donor_repair(
    runtime: DummyChunkRuntime,
    normalized_data: bytes,
) -> idat.IdatDonorRepair | None:
    repairs: list[idat.IdatDonorRepair] = []
    for path in _truncated_idat_donor_paths(runtime.file_origin):
        try:
            donor_data = path.read_bytes()
        except OSError:
            continue
        repair = idat.rebuild_idat_from_donor(
            normalized_data,
            donor_data,
            donor_label=path.name,
            donor_path=_relative_path(path),
        )
        if repair is None:
            continue
        if repairs and repair.data == repairs[0].data:
            continue
        repairs.append(repair)
        if len(repairs) > 1:
            return None
    return repairs[0] if repairs else None


def _checkpoint_truncated_idat_repair(
    runtime: DummyChunkRuntime,
    repair: Any,
    *,
    bad_pos: int,
    bad_start: int,
    bad_end: int,
    from_error: Any,
) -> Any:
    runtime.side_notes.append(runtime.repair_note(repair))
    if runtime.write_clone is not None:
        return runtime.write_clone(repair.data.hex(), "-%s." % repair.strategy)
    return checkpoint_dummy_chunk(
        runtime,
        b"IEND",
        solved=True,
        fixed_data_hex=repair.data.hex(),
        dummy_data_length=0,
        bad_pos=bad_pos,
        bad_start=bad_start,
        bad_end=bad_end,
        from_error=from_error,
        info=["Repaired truncated IDAT before missing IEND"],
    )


def _checkpoint_idat_candidate(
    runtime: DummyChunkRuntime,
    data: bytes,
    note: str,
    *,
    bad_pos: int,
    bad_start: int,
    bad_end: int,
    from_error: Any,
) -> Any:
    runtime.side_notes.append(note)
    if runtime.write_clone is not None:
        return runtime.write_clone(data.hex(), note)
    return checkpoint_dummy_chunk(
        runtime,
        b"IEND",
        solved=True,
        fixed_data_hex=data.hex(),
        dummy_data_length=0,
        bad_pos=bad_pos,
        bad_start=bad_start,
        bad_end=bad_end,
        from_error=from_error,
        info=["Repaired truncated IDAT before missing IEND"],
    )


def _try_truncated_idat_bruteforce(
    runtime: DummyChunkRuntime,
    normalized: idat.TruncatedIdatNormalization,
    *,
    bad_pos: int,
    bad_start: int,
    bad_end: int,
    from_error: Any,
) -> Any | None:
    analysis = idat.analyze_idat_stream(normalized.data)
    runtime.side_notes.append(
        "-FixItFelix:IDAT declared %s byte(s), but only %s byte(s) exist before EOF."
        % (normalized.declared_length, normalized.available_length)
    )
    runtime.side_notes.append(
        "-FixItFelix:normalized truncated IDAT to %s available byte(s) before probing deflate."
        % normalized.available_length
    )

    runtime.candy(
        "Cowsay",
        "IDAT says it has %s bytes, but EOF arrives after %s. I will normalize that wound before probing zlib."
        % (normalized.declared_length, normalized.available_length),
        "bad",
    )
    runtime.candy(
        "Cowsay",
        "Bounded brute force first: header probe, then the small IDAT strategy queue. Missing %s bytes is not a random-byte lottery."
        % normalized.missing_bytes,
        "com",
    )

    header_probe = idat_bruteforce.probe_deflate_header_candidates(normalized.data)
    runtime.side_notes.append(idat_bruteforce.probe_summary_line(header_probe))
    if header_probe.best is not None and header_probe.best.after.complete:
        runtime.side_notes.extend(idat_bruteforce.candidate_summary_lines(header_probe))
        return _checkpoint_idat_candidate(
            runtime,
            header_probe.best.data,
            "-FixItFelix:repaired truncated IDAT with bounded deflate-header probe.",
            bad_pos=bad_pos,
            bad_start=bad_start,
            bad_end=bad_end,
            from_error=from_error,
        )

    queue_probe = idat_bruteforce.probe_idat_deflate_strategy_queue(normalized.data)
    runtime.side_notes.append(idat_bruteforce.probe_summary_line(queue_probe))
    if queue_probe.best is not None and queue_probe.best.after.complete:
        runtime.side_notes.extend(idat_bruteforce.candidate_summary_lines(queue_probe))
        return _checkpoint_idat_candidate(
            runtime,
            queue_probe.best.data,
            "-FixItFelix:repaired truncated IDAT with bounded deflate strategy queue.",
            bad_pos=bad_pos,
            bad_start=bad_start,
            bad_end=bad_end,
            from_error=from_error,
        )

    runtime.side_notes.append(
        "-FixItFelix:bounded IDAT brute force found no complete zlib stream from the available bytes."
    )
    runtime.candy(
        "Cowsay",
        "The bounded brute force found no complete zlib stream. I am not brute-forcing hundreds of missing bytes blindly.",
        "bad",
    )
    return None


def _ask_truncated_idat_fallbacks(
    runtime: DummyChunkRuntime,
    normalized: idat.TruncatedIdatNormalization,
    *,
    bad_pos: int,
    bad_start: int,
    bad_end: int,
    from_error: Any,
) -> Any:
    donor_repair = (
        _local_truncated_idat_donor_repair(runtime, normalized.data)
        if runtime.question is not None
        else None
    )
    if donor_repair is not None and runtime.question is not None:
        runtime.candy(
            "Cowsay",
            "Option 1: I found one local PNG with matching pixels structure and palette: %s."
            % donor_repair.donor_path,
            "com",
        )
        if runtime.question(
            id="IDAT donor repair:-Truncated IDAT. Replace IDAT with local donor %s?"
            % donor_repair.donor_path,
            idhash=(
                "IDAT-donor",
                donor_repair.donor_path,
                donor_repair.width,
                donor_repair.height,
                donor_repair.bit_depth,
                donor_repair.color_type,
            ),
            skipauto=True,
        ):
            return _checkpoint_truncated_idat_repair(
                runtime,
                donor_repair,
                bad_pos=bad_pos,
                bad_start=bad_start,
                bad_end=bad_end,
                from_error=from_error,
            )

    partial_repair = idat.rebuild_partial_idat_blackfill(normalized.data)
    if partial_repair is not None and partial_repair.recovered_scanlines > 0:
        runtime.candy(
            "Cowsay",
            "I recovered %s/%s filtered scanlines from the truncated IDAT. I will blackfill the missing tail and write a salvage PNG."
            % (partial_repair.recovered_scanlines, partial_repair.total_scanlines),
            "com",
        )
        return _checkpoint_truncated_idat_repair(
            runtime,
            partial_repair,
            bad_pos=bad_pos,
            bad_start=bad_start,
            bad_end=bad_end,
            from_error=from_error,
        )

    if runtime.question is None:
        runtime.side_notes.append("-FixItFelix:truncated IDAT needed a prompt; no fallback selected.")
        return runtime.end()

    synthetic_repair = idat.rebuild_synthetic_idat(normalized.data)
    if synthetic_repair is not None:
        runtime.candy(
            "Cowsay",
            "Option 2: I can build a diagnostic IDAT from IHDR/PLTE. Valid PNG, invented pixels.",
            "com",
        )
        if runtime.question(
            id="IDAT synthetic repair:-No original scanlines. Build synthetic diagnostic IDAT?",
            idhash=(
                "IDAT-synthetic",
                synthetic_repair.width,
                synthetic_repair.height,
                synthetic_repair.bit_depth,
                synthetic_repair.color_type,
            ),
            skipauto=True,
        ):
            return _checkpoint_truncated_idat_repair(
                runtime,
                synthetic_repair,
                bad_pos=bad_pos,
                bad_start=bad_start,
                bad_end=bad_end,
                from_error=from_error,
            )

    placeholder_repair = idat.rebuild_zero_scanline_placeholder(normalized.data)
    if placeholder_repair is not None:
        runtime.candy(
            "Cowsay",
            "Option 3: I can write an all-zero placeholder. It is structural, not recovered pixels.",
            "bad",
        )
        if runtime.question(
            id="IDAT Zero Scanline Blackfill:-Truncated IDAT. Write all-zero placeholder anyway?",
            idhash=(
                "IDAT-zero-blackfill",
                placeholder_repair.width,
                placeholder_repair.height,
                placeholder_repair.bit_depth,
                placeholder_repair.color_type,
            ),
            skipauto=True,
        ):
            return _checkpoint_truncated_idat_repair(
                runtime,
                placeholder_repair,
                bad_pos=bad_pos,
                bad_start=bad_start,
                bad_end=bad_end,
                from_error=from_error,
            )

    runtime.side_notes.append("-FixItFelix:truncated IDAT fallback options were declined or unavailable.")
    return runtime.end()


def handle_truncated_idat_before_iend(
    runtime: DummyChunkRuntime,
    *,
    bad_pos: int,
    bad_start: int,
    bad_end: int,
    from_error: Any,
) -> tuple[bool, Any]:
    try:
        data = bytes.fromhex(runtime.data_hex)
    except ValueError:
        return False, None

    normalized = idat.normalize_truncated_idat_at_eof(data)
    if normalized is None:
        return False, None

    brute_result = _try_truncated_idat_bruteforce(
        runtime,
        normalized,
        bad_pos=bad_pos,
        bad_start=bad_start,
        bad_end=bad_end,
        from_error=from_error,
    )
    if brute_result is not None:
        return True, brute_result

    return True, _ask_truncated_idat_fallbacks(
        runtime,
        normalized,
        bad_pos=bad_pos,
        bad_start=bad_start,
        bad_end=bad_end,
        from_error=from_error,
    )


def run_dummy_chunk(
    runtime: DummyChunkRuntime,
    chunk_name: bytes,
    bad_pos: int,
    bad_start: int,
    bad_end: int,
    from_error: Any,
) -> Any:
    runtime.candy("Title", "Creating DummyChunk:")
    runtime.candy(
        "Cowsay",
        "Mkay i will need to get some infos on the file before..",
        "com",
    )

    if chunk_name == b"IEND":
        handled, result = handle_truncated_idat_before_iend(
            runtime,
            bad_pos=bad_pos,
            bad_start=bad_start,
            bad_end=bad_end,
            from_error=from_error,
        )
        if handled:
            return result

    decision = dummy_chunk.decide_dummy_chunk(chunk_name, runtime.data_hex, bad_start)
    if decision.action in ("strict_ihdr_repair", "partial_idat_blackfill"):
        append_repair_note(runtime, decision)
        return checkpoint_dummy_chunk(
            runtime,
            chunk_name,
            solved=True,
            fixed_data_hex=decision.fixed_data_hex,
            dummy_data_length=decision.dummy_data_length,
            bad_pos=bad_pos,
            bad_start=bad_start,
            bad_end=bad_end,
            from_error=from_error,
        )

    if decision.action == "complete_iend":
        emit_fake_data_ready(runtime)
        return checkpoint_dummy_chunk(
            runtime,
            chunk_name,
            solved=decision.solved,
            fixed_data_hex=decision.fixed_data_hex,
            dummy_data_length=decision.dummy_data_length,
            bad_pos=bad_pos,
            bad_start=bad_start,
            bad_end=bad_end,
            from_error=from_error,
        )

    build = build_legacy_dummy(runtime, chunk_name)
    if build is None:
        return emit_todo_and_end(runtime)

    emit_debug_build(runtime, chunk_name, build, bad_pos, bad_start, bad_end)
    fixed_data_hex = runtime.data_hex[:bad_start] + build.chunk_hex + runtime.data_hex[bad_start:]
    emit_fake_data_ready(runtime)
    return checkpoint_dummy_chunk(
        runtime,
        chunk_name,
        solved=build.solved,
        fixed_data_hex=fixed_data_hex,
        dummy_data_length=len(build.dummy_data),
        bad_pos=bad_pos,
        bad_start=bad_start,
        bad_end=bad_end,
        from_error=from_error,
    )
