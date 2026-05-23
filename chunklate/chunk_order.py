from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ChunkOrderContext:
    used_chunks: tuple[bytes, ...]
    excluded_chunks: tuple[bytes, ...]


def as_chunk_bytes(chunk: bytes | str) -> bytes:
    if isinstance(chunk, bytes):
        return chunk
    return chunk.encode(errors="ignore")


def decode_chunk_name(chunk: bytes) -> str:
    return chunk.decode(errors="ignore")


def decode_chunk_names(chunks: Iterable[bytes]) -> list[str]:
    return [decode_chunk_name(chunk) for chunk in chunks]


def seen_chunks_message(
    sample_name: str,
    used_chunks: Iterable[bytes],
    separator: str = "",
) -> str:
    return (
        " So far we came across those chunks in "
        + sample_name
        + separator
        + str(decode_chunk_names(used_chunks))
    )


def critical_missing_print_line(chunk: bytes, missing_label: str) -> str:
    return "-Critical Chunk %s is %s !" % (chunk, missing_label)


def errors_ok_print_line(ok_label: str, good_emoj: str) -> str:
    return "\n-Errors Check :" + ok_label + good_emoj


def unique_seen_chunks(chunks_history: Sequence[bytes]) -> tuple[bytes, ...]:
    return tuple(dict.fromkeys(chunks_history))


def missing_critical_chunks(
    chunks_history: Sequence[bytes],
    minimal_chunks: Iterable[bytes],
) -> tuple[bytes, ...]:
    return tuple(chunk for chunk in minimal_chunks if chunk not in chunks_history)


def missing_critical_infos(missing_chunks: Iterable[bytes]) -> tuple[str, ...]:
    return tuple("-Critical Chunk %s is Missing" % chunk for chunk in missing_chunks)


def has_findings(findings: Sequence[object]) -> bool:
    return len(findings) > 0


def critical_checkpoint_args(to_fix: Sequence[str]) -> tuple[object, ...]:
    return (True, False, "CheckChunkOrder", "Critical", to_fix)


def unique_chunk_exclusions(
    used_chunks: Sequence[bytes],
    unique_chunks: Iterable[bytes],
) -> tuple[bytes, ...]:
    unique_set = set(unique_chunks)
    return tuple(chunk for chunk in used_chunks if chunk in unique_set)


def build_chunk_order_context(
    chunks_history: Sequence[bytes],
    unique_chunks: Iterable[bytes],
) -> ChunkOrderContext:
    used_chunks = unique_seen_chunks(chunks_history)
    return ChunkOrderContext(
        used_chunks=used_chunks,
        excluded_chunks=unique_chunk_exclusions(used_chunks, unique_chunks),
    )


def legacy_flags_unique_chunk_as_multiple(
    lastchunk: bytes,
    excluded: Sequence[bytes],
    unique_chunks: Iterable[bytes],
) -> bool:
    return lastchunk in set(unique_chunks) and lastchunk in excluded


def multiple_chunk_print_line(colored_chunk: str, colored_cannot: str) -> str:
    return "-%s chunk %s be used multiple times." % (colored_chunk, colored_cannot)


def multiple_chunk_info() -> str:
    return "-Multiple"


def missplaced_info() -> str:
    return "-Missplaced"


def missplaced_checkpoint_args(to_fix: Sequence[str]) -> tuple[object, ...]:
    return (True, False, "CheckChunkOrder", "Missplaced", to_fix)


def missplaced_failed_print_line(failed_label: str, bad_emoj: str) -> str:
    return "\n-Missplaced Chunk Check :" + failed_label + bad_emoj


def missplaced_ok_print_line(ok_label: str, good_emoj: str) -> str:
    return "\n-Missplaced Chunk Check :" + ok_label + good_emoj


def png_signature_is_misplaced(chunks_history: Sequence[bytes]) -> bool:
    return len(chunks_history) > 0 and chunks_history[0] != b"PNG"


def png_signature_misplaced_print_line(colored_before: str, bad_emoj: str) -> str:
    return "-PNG signature have to be placed %s all the other chunks. %s" % (
        colored_before,
        bad_emoj,
    )


def ihdr_is_misplaced(chunks_history: Sequence[bytes]) -> bool:
    return len(chunks_history) > 1 and chunks_history[1] != b"IHDR"


def ihdr_misplaced_print_line(colored_before_all: str, bad_emoj: str) -> str:
    return "-IHDR Chunk have to be placed %s and after Png Signature. %s" % (
        colored_before_all,
        bad_emoj,
    )


def ihdr_misplacement_already_recorded(pandora_box: Mapping[object, object]) -> bool:
    return any("Should be IHDR Instead At Chunk Number:" in str(key) for key in pandora_box)


def ihdr_misplacement_checkpoint_args(chunks_history: Sequence[bytes]) -> tuple[object, ...]:
    return (
        True,
        False,
        "CheckChunkOrder",
        chunks_history[-1],
        [
            "-Missplaced [%s] Should be IHDR Instead At Chunk Number:%s"
            % (chunks_history[-1], str(len(chunks_history) - 1))
        ],
        chunks_history[-1],
        len(chunks_history) - 1,
        b"IHDR",
    )


def must_appear_before_plte(
    lastchunk: bytes,
    used_chunks: Sequence[bytes],
    before_plte: Iterable[bytes],
) -> bool:
    return b"PLTE" in used_chunks and lastchunk in set(before_plte)


def missplaced_before_plte_info(lastchunk: bytes) -> str:
    return "-%s is missplaced must appears before PLTE Chunk" % decode_chunk_name(lastchunk)


def before_plte_print_line(colored_missplaced: str, chunk_name: str, bad_emoj: str) -> str:
    return "-%s  %s must appears before PLTE Chunk. %s" % (
        colored_missplaced,
        chunk_name,
        bad_emoj,
    )


def must_appear_before_idat(
    lastchunk: bytes,
    used_chunks: Sequence[bytes],
    excluded: Sequence[bytes],
    before_idat: Iterable[bytes],
) -> bool:
    return b"IDAT" in used_chunks and (
        lastchunk in excluded or lastchunk in set(before_idat)
    )


def before_idat_print_line(colored_missplaced: str, chunk_name: str, bad_emoj: str) -> str:
    return "-%s  %s must be before IDAT Chunk. %s" % (
        colored_missplaced,
        chunk_name,
        bad_emoj,
    )


def only_ihdr_allowed_after_png_header(
    chunks_history: Sequence[bytes],
    chunks: Iterable[bytes],
) -> tuple[bytes, ...] | None:
    if len(chunks_history) == 1 and chunks_history[0] == b"PNG":
        return tuple(chunk for chunk in chunks if chunk != b"IHDR")
    return None


def must_stay_before_plte_without_ihdr(
    lastchunk: bytes,
    used_chunks: Sequence[bytes],
    before_plte: Iterable[bytes],
) -> bool:
    return lastchunk in set(before_plte) and b"IHDR" not in used_chunks


def must_follow_plte(lastchunk: bytes, after_plte: Iterable[bytes]) -> bool:
    return lastchunk in set(after_plte)


def has_idat(used_chunks: Sequence[bytes]) -> bool:
    return b"IDAT" in used_chunks


def add_iend_exclusion(excluded: Sequence[bytes]) -> tuple[bytes, ...]:
    return tuple(list(excluded) + [b"IEND"])


def before_plte_forget_message(colored_chunk: str, excluded_names: Sequence[str]) -> str:
    return (
        " %s chunk must be placed before any PLTE related chunks we can forget about thoses:\n%s"
        % (colored_chunk, excluded_names)
    )


def after_plte_forget_message(lastchunk: bytes, excluded_names: Sequence[str]) -> str:
    return (
        " %s chunk must be placed after PLTE related chunks we can forget about thoses:\n%s"
        % (lastchunk, excluded_names)
    )


def extend_exclusions_not_in(
    excluded: Sequence[bytes],
    chunks: Iterable[bytes],
    allowed_chunks: Iterable[bytes],
) -> tuple[bytes, ...]:
    allowed_set = set(allowed_chunks)
    return tuple(list(excluded) + [chunk for chunk in chunks if chunk not in allowed_set])


def extend_exclusions_in(
    excluded: Sequence[bytes],
    chunks: Iterable[bytes],
    selected_chunks: Iterable[bytes],
) -> tuple[bytes, ...]:
    selected_set = set(selected_chunks)
    return tuple(list(excluded) + [chunk for chunk in chunks if chunk in selected_set])


def extend_exclusions_before_idat_after_idat(
    excluded: Sequence[bytes],
    chunks: Iterable[bytes],
    before_idat: Iterable[bytes],
) -> tuple[bytes, ...]:
    before_idat_set = set(before_idat)
    return tuple(list(excluded) + [chunk for chunk in chunks if chunk in before_idat_set and chunk not in excluded])


def may_have_missing_critical_palette(
    ihdr_color: int | str,
    chunks_history: Sequence[bytes],
) -> bool:
    color = int(ihdr_color)
    return (
        (color == 2)
        or (color == 6)
        and (
            b"PLTE" not in chunks_history
            and b"sPLT" not in chunks_history
        )
    )


def missing_critical_palette_info() -> str:
    return "-There is a chance that some Critical Palette chunks are missing."


def is_indexed_color(ihdr_color: int | str) -> bool:
    return int(ihdr_color) == 3


def indexed_idat_previous_chunk_is_plte(used_chunks: Sequence[bytes]) -> bool:
    return used_chunks[used_chunks.index(b"IDAT") - 1] == b"PLTE"


def is_idat_chunk(chunk: bytes) -> bool:
    return chunk == b"IDAT"


def idat_next_candidates_message(no_order_chunks: Iterable[bytes]) -> str:
    return (
        " So ..the last Chunk Type was IDAT so we either looking for another IDAT,IEND or one of them:%s"
        % decode_chunk_names(no_order_chunks)
    )


def the_good_place_missing_checkpoint_args(
    to_fix_chunk: bytes,
    bad_pos: int,
    bad_start: int,
    bad_end: int,
) -> tuple[object, ...]:
    return (
        True,
        False,
        "TheGoodPlace",
        to_fix_chunk,
        ["-Missing Data Has Not Been Found : [%s]" % to_fix_chunk],
        to_fix_chunk,
        bad_pos,
        bad_start,
        bad_end,
    )


def the_good_place_found_checkpoint_args(
    to_fix_chunk: bytes,
    fix_position: Any,
    rubber_tape: str,
) -> tuple[object, ...]:
    return (
        True,
        True,
        "TheGoodPlace",
        to_fix_chunk,
        [
            "-Found Missing Data:[%s] at Chunk Position:%s Starting at:%s Ending at:%s"
            % (to_fix_chunk, fix_position.position, fix_position.start, fix_position.end)
        ],
        rubber_tape,
    )
