from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from . import dummy_chunk


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
) -> Any:
    return runtime.checkpoint(
        True,
        solved,
        "DummyChunk",
        chunk_name,
        ["Filling with a dummy chunk"],
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
