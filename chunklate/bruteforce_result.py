from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from . import bruteforce


LegacyCall = Callable[..., Any]


@dataclass(frozen=True)
class BruteForceResultRuntime:
    emit: LegacyCall
    candy: LegacyCall
    checkpoint: LegacyCall
    side_notes: list[Any]
    suppress_failure_theatre: bool = False


@dataclass(frozen=True)
class BruteForceResultContext:
    state: bruteforce.BruteForceMatchState
    old_crc: Any
    file: Any
    chunk_name: Any
    full_new_data_hex: str
    png_bytes_hex: str
    data_offset: int
    chunk_length: int
    to_brute: str
    edit_mode: str
    bf_mode: str
    brute_crc: bool
    brute_length: bool
    from_error: Any
    diff: str
    tmp_image_paths: tuple[str, ...] = ()
    brute_level: int = 0


def run_success(runtime: BruteForceResultRuntime, context: BruteForceResultContext) -> Any:
    runtime.emit(
        "-Bruteforce was %s %s"
        % (runtime.candy("Color", "green", "Successfull!"), runtime.candy("Chunky", "good"))
    )

    if context.state.bonus:
        runtime.candy("Cowsay", bruteforce.BRUTE_FORCE_BONUS_NOTE, "bad")
        runtime.side_notes.append(bruteforce.BRUTE_FORCE_BONUS_NOTE)

    for repair_message in bruteforce.success_repair_messages(
        context.state,
        context.chunk_name,
        context.diff,
    ):
        runtime.emit(
            repair_message.line_template
            % runtime.candy("Color", "green", context.chunk_name)
        )
        runtime.side_notes.append(repair_message.side_note)

    runtime.emit(context.diff)
    runtime.candy("Cowsay", "Wow ...I wasn't sure this would work to be honest !", "good")

    checkpoint_request = bruteforce.success_checkpoint_request(
        old_crc=context.old_crc,
        chunk_name=context.chunk_name,
        full_new_data_hex=context.full_new_data_hex,
        png_bytes_hex=context.png_bytes_hex,
        data_offset=context.data_offset,
        chunk_length=context.chunk_length,
        to_brute=context.to_brute,
        from_error=context.from_error,
    )
    return runtime.checkpoint(*checkpoint_request.as_args())


def _sbb_pass_label(context: BruteForceResultContext) -> str:
    if str(context.bf_mode).lower() == "brutus":
        return "HephaestusForge %s level %s" % (context.edit_mode, context.brute_level)
    if str(context.bf_mode).lower() == "twobytes":
        return "HermesProbe %s level %s" % (context.edit_mode, context.brute_level)
    return "%s level %s" % (context.edit_mode, context.brute_level)


def run_failure(runtime: BruteForceResultRuntime, context: BruteForceResultContext) -> Any:
    if runtime.suppress_failure_theatre:
        runtime.emit(
            "\n-SBB pass failed: %s. I will continue the blackfill retry sequence."
            % _sbb_pass_label(context)
        )
        runtime.side_notes.append("\n-SmashBruteBrawl blackfill pass failed.")
    else:
        runtime.emit(
            "\n-Bruteforce has %s %s"
            % (runtime.candy("Color", "red", "Failed!"), runtime.candy("Chunky", "bad"))
        )

        runtime.candy("Cowsay", "I was afraid of this ...", "bad")
        runtime.side_notes.append(bruteforce.BRUTE_FORCE_FAILURE_NOTE)

    if len(context.tmp_image_paths) > 0:
        runtime.candy(
            "Cowsay",
            "But while you were away i v saved some pictures maybe you should take a look ...",
            "bad",
        )
        for path in context.tmp_image_paths:
            runtime.emit("-Saved Valid Image: %s" % path)

    checkpoint_request = bruteforce.failure_checkpoint_request(
        old_crc=context.old_crc,
        file=context.file,
        chunk_name=context.chunk_name,
        chunk_length=context.chunk_length,
        data_offset=context.data_offset,
        edit_mode=context.edit_mode,
        bf_mode=context.bf_mode,
        brute_crc=context.brute_crc,
        brute_length=context.brute_length,
        from_error=context.from_error,
    )
    return runtime.checkpoint(*checkpoint_request.as_args())


def run_result(runtime: BruteForceResultRuntime, context: BruteForceResultContext) -> Any:
    if context.state.bingo is True:
        return run_success(runtime, context)

    return run_failure(runtime, context)
