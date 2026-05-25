from __future__ import annotations

from collections.abc import Callable, MutableSequence
from dataclasses import dataclass
from typing import Any

from . import chunk_scanner
from .png import detect_png_signature_recovery, legacy_find_magic_checkpoint_args


LegacyCall = Callable[..., Any]

MAGIC = "89504e470d0a1a0a"
FULL_MAGIC = "89504e470d0a1a0a0000000d49484452"


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


def _color(runtime: FindMagicRuntime, color: str, value: Any) -> Any:
    return runtime.candy("Color", color, value)


def _emoj(runtime: FindMagicRuntime, value: str) -> Any:
    return runtime.candy("Emoj", value)


def _cowsay(runtime: FindMagicRuntime, message: str, mood: str | None = None) -> Any:
    if mood is None:
        return runtime.candy("Cowsay", message)
    return runtime.candy("Cowsay", message, mood)


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
        % (_color(runtime, "red", "does not"), _emoj(runtime, "bad"))
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
    runtime.emit("-Done! %s\n" % _emoj(runtime, "good"))
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
