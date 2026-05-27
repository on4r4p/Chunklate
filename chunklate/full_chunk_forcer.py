from __future__ import annotations

from collections.abc import Callable, MutableSequence
from dataclasses import dataclass
from typing import Any
import binascii
import difflib
import io


LegacyCall = Callable[..., Any]


@dataclass(frozen=True)
class FullChunkForcerContext:
    file: Any
    chunk: bytes
    data_offset: int
    chunk_length: int
    from_error: Any
    sample_path: str
    data_hex: str
    debug: bool = False
    pause_debug: bool = False
    pause_error: bool = False


@dataclass(frozen=True)
class FullChunkForcerRuntime:
    emit: LegacyCall
    candy: LegacyCall
    checkpoint: LegacyCall
    side_notes: MutableSequence[Any]
    minibar: LegacyCall
    pause: LegacyCall
    end: LegacyCall
    save_error: LegacyCall
    cv2: Any
    numpy: Any
    stderr_redirector: LegacyCall
    ask: LegacyCall = input
    open_file: LegacyCall = open


@dataclass(frozen=True)
class FullChunkCandidate:
    full_new_data_hex: str
    candidate_file_hex: str
    old_data_hex: str
    good_diff: str
    bad_diff: str


def diff_replacement(old_hex: str, full_new_data_hex: str) -> tuple[str, str]:
    diffobj = difflib.SequenceMatcher(None, old_hex, full_new_data_hex)
    good = ""
    bad = ""
    for block in diffobj.get_opcodes():
        if block[0] != "equal":
            good += "\033[1;32;49m%s\033[m" % full_new_data_hex[block[1] : block[2]]
            bad += "\033[1;31;49m%s\033[m" % old_hex[block[1] : block[2]]
        else:
            good += full_new_data_hex[block[1] : block[2]]
            bad += old_hex[block[1] : block[2]]
    return good, bad


def build_candidate(
    chunk: bytes,
    data_hex: str,
    chunk_data_hex: str,
    data_offset: int,
    chunk_length: int,
    replacement_hex: str,
    needle: int,
) -> FullChunkCandidate:
    new_data_hex = chunk_data_hex[:needle] + replacement_hex + chunk_data_hex[needle + len(replacement_hex) :]
    checksum = hex(binascii.crc32(chunk + bytes.fromhex(new_data_hex))).replace("0x", "").zfill(8)
    full_new_data_hex = chunk_data_hex[:16] + new_data_hex + checksum
    candidate_file_hex = data_hex[:data_offset] + full_new_data_hex + data_hex[chunk_length:]
    good, bad = diff_replacement(chunk_data_hex[16:], full_new_data_hex)
    return FullChunkCandidate(
        full_new_data_hex=full_new_data_hex,
        candidate_file_hex=candidate_file_hex,
        old_data_hex=chunk_data_hex[16:],
        good_diff=good,
        bad_diff=bad,
    )


def probe_candidate(runtime: FullChunkForcerRuntime, candidate_file_hex: str) -> str:
    stream = io.BytesIO()
    with runtime.stderr_redirector(stream):
        candidate_array = runtime.numpy.fromstring(
            bytes.fromhex(candidate_file_hex),
            runtime.numpy.uint8,
        )
        decoded = runtime.cv2.imdecode(candidate_array, runtime.cv2.IMREAD_COLOR)
        runtime.cv2.imread(decoded)
    return "{0}".format(stream.getvalue().decode("utf-8"))


def find_repair_candidate(
    runtime: FullChunkForcerRuntime,
    context: FullChunkForcerContext,
    chunk_data_hex: str,
) -> FullChunkCandidate | None:
    result = "result is empty"
    needle = 0
    needle2 = 2
    while needle2 <= len(chunk_data_hex):
        runtime.minibar()
        if needle < len(chunk_data_hex) - (needle2 - 1):
            for hexa in range(0, 16 ** needle2):
                newbyte = (hex(hexa).replace("0x", "")).zfill(needle2)
                candidate = build_candidate(
                    context.chunk,
                    context.data_hex,
                    chunk_data_hex,
                    context.data_offset,
                    context.chunk_length,
                    newbyte,
                    needle,
                )
                try:
                    result = probe_candidate(runtime, candidate.candidate_file_hex)
                    runtime.emit(result)
                    runtime.ask("pause")
                except Exception as exc:
                    runtime.save_error(exc, "FullChunkForcerNoCrc")
                    runtime.emit(
                        runtime.candy("Color", "red", "Error FullChunkForcerNoCrc:"),
                        runtime.candy("Color", "yellow", exc),
                    )
                    if (context.pause_debug or context.pause_error) is True:
                        runtime.pause("Pause Debug")

                if context.debug is True:
                    runtime.emit("fullnewdatax:%s" % candidate.full_new_data_hex)
                    if context.pause_debug is True:
                        runtime.pause("Pause Debug")

                if "libpng error" not in result and result != "result is empty":
                    return candidate
            needle += 1
        else:
            needle = 0
            needle2 += 2

    return None


def run_success(
    runtime: FullChunkForcerRuntime,
    context: FullChunkForcerContext,
    candidate: FullChunkCandidate,
) -> Any:
    chunk_label = context.chunk.decode(errors="ignore")
    runtime.emit(
        "-Bruteforce was %s %s"
        % (runtime.candy("Color", "green", "Successfull!"), runtime.candy("Chunky", "good"))
    )
    runtime.emit(
        "-Chunk %s has been repaired by changing those bytes:\n"
        % runtime.candy("Color", "green", context.chunk)
    )
    runtime.emit(candidate.bad_diff)
    runtime.emit("\n-With those bytes:\n")
    runtime.emit(candidate.good_diff)
    runtime.candy("Cowsay", "Wow ...I wasn't sure this would work to be honest !", "good")
    runtime.side_notes.append(
        "\n-Launched Data Chunk Bruteforcer.\n-Bruteforce was successfull.\n-Chunk %s has been repaired by changing those bytes:\n%s\n-with bytes:\n%s"
        % (context.chunk, candidate.old_data_hex, candidate.full_new_data_hex)
    )

    return runtime.checkpoint(
        True,
        True,
        "FullChunkForcerNoCrc",
        chunk_label,
        ["-Data has been corrupted"],
        candidate.full_new_data_hex,
        context.data_offset,
        context.data_offset + context.chunk_length,
        "-Replacing Corrupted %s Data:\n%s\n-With:\n%s"
        % (chunk_label, candidate.old_data_hex, candidate.full_new_data_hex),
        chunk_label,
        context.from_error,
    )


def run_failure(runtime: FullChunkForcerRuntime, context: FullChunkForcerContext) -> Any:
    runtime.emit(
        "-Bruteforce has %s %s"
        % (runtime.candy("Color", "red", "Failed!"), runtime.candy("Chunky", "bad"))
    )
    runtime.candy("Cowsay", "I was afraid of this ..Looks like we r stuck..", "bad")
    runtime.side_notes.append("\n-Launched Data Chunk Bruteforcer.\n-Bruteforce has Failed!")
    runtime.end()
    return runtime.checkpoint(
        True,
        False,
        "FullChunkForcerNoCrc",
        context.chunk.decode(errors="ignore"),
        ["-Bruteforcer has Failed"],
        context.from_error,
    )


def run_legacy_full_chunk_forcer_no_crc(
    runtime: FullChunkForcerRuntime,
    context: FullChunkForcerContext,
) -> Any:
    if context.debug is True:
        runtime.emit("file:%s" % context.file)
        runtime.emit("chunk:%s" % context.chunk)
        runtime.emit("offd:%s" % context.data_offset)
        runtime.emit("cl:%s" % context.chunk_length)
        if context.pause_debug is True:
            runtime.pause("Debug Pause:")

    try:
        with runtime.open_file(context.sample_path, "rb") as handle:
            data = handle.read()
    except Exception as exc:
        runtime.save_error(exc, "FullChunkForcerNoCrc")
        runtime.emit(runtime.candy("Color", "red", "Error:%s") % runtime.candy("Color", "yellow", exc))
        runtime.end()
        return None

    chunk_data_hex = data.hex()[context.data_offset : context.chunk_length]
    candidate = find_repair_candidate(runtime, context, chunk_data_hex)
    if candidate is not None:
        return run_success(runtime, context, candidate)

    return run_failure(runtime, context)


def build_full_chunk_forcer_runtime_from_namespace(namespace: dict[str, Any]) -> FullChunkForcerRuntime:
    return FullChunkForcerRuntime(
        emit=namespace["PRINT"],
        candy=namespace["Candy"],
        checkpoint=namespace["CheckPoint"],
        side_notes=namespace["SideNotes"],
        minibar=namespace["Minibar"],
        pause=namespace["Pause"],
        end=namespace["TheEnd"],
        save_error=lambda error, def_name: namespace["Betterror"](error, def_name),
        cv2=namespace["cv2"],
        numpy=namespace["np"],
        stderr_redirector=namespace["stderr_redirector"],
    )


def build_full_chunk_forcer_context_from_namespace(
    namespace: dict[str, Any],
    file: Any,
    chunk: bytes,
    data_offset: int,
    chunk_length: int,
    from_error: Any,
) -> FullChunkForcerContext:
    return FullChunkForcerContext(
        file=file,
        chunk=chunk,
        data_offset=data_offset,
        chunk_length=chunk_length,
        from_error=from_error,
        sample_path=namespace["Sample"],
        data_hex=namespace["DATAX"],
        debug=namespace["DEBUG"],
        pause_debug=namespace["PAUSEDEBUG"],
        pause_error=namespace["PAUSEERROR"],
    )


def run_full_chunk_forcer_no_crc_from_namespace(
    namespace: dict[str, Any],
    file: Any,
    chunk: Any,
    data_offset: int,
    chunk_length: int,
    from_error: Any,
    *,
    runner: LegacyCall = run_legacy_full_chunk_forcer_no_crc,
) -> Any:
    namespace["Candy"]("Title", "FullChunkForcerNoCrc")
    namespace["Candy"]("Title", "Attempting To Repair Corrupted Chunk Data:")
    chunk = chunk.encode(errors="ignore")
    return runner(
        build_full_chunk_forcer_runtime_from_namespace(namespace),
        build_full_chunk_forcer_context_from_namespace(
            namespace,
            file,
            chunk,
            data_offset,
            chunk_length,
            from_error,
        ),
    )
