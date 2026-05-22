from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence


def as_chunk_bytes(chunk: bytes | str) -> bytes:
    if isinstance(chunk, bytes):
        return chunk
    return chunk.encode(errors="ignore")


def unique_seen_chunks(chunks_history: Sequence[bytes]) -> tuple[bytes, ...]:
    return tuple(dict.fromkeys(chunks_history))


def missing_critical_chunks(
    chunks_history: Sequence[bytes],
    minimal_chunks: Iterable[bytes],
) -> tuple[bytes, ...]:
    return tuple(chunk for chunk in minimal_chunks if chunk not in chunks_history)


def unique_chunk_exclusions(
    used_chunks: Sequence[bytes],
    unique_chunks: Iterable[bytes],
) -> tuple[bytes, ...]:
    unique_set = set(unique_chunks)
    return tuple(chunk for chunk in used_chunks if chunk in unique_set)


def legacy_flags_unique_chunk_as_multiple(
    lastchunk: bytes,
    excluded: Sequence[bytes],
    unique_chunks: Iterable[bytes],
) -> bool:
    return lastchunk in set(unique_chunks) and lastchunk in excluded


def png_signature_is_misplaced(chunks_history: Sequence[bytes]) -> bool:
    return len(chunks_history) > 0 and chunks_history[0] != b"PNG"


def ihdr_is_misplaced(chunks_history: Sequence[bytes]) -> bool:
    return len(chunks_history) > 1 and chunks_history[1] != b"IHDR"


def ihdr_misplacement_already_recorded(pandora_box: Mapping[object, object]) -> bool:
    return any("Should be IHDR Instead At Chunk Number:" in str(key) for key in pandora_box)


def must_appear_before_plte(
    lastchunk: bytes,
    used_chunks: Sequence[bytes],
    before_plte: Iterable[bytes],
) -> bool:
    return b"PLTE" in used_chunks and lastchunk in set(before_plte)


def must_appear_before_idat(
    lastchunk: bytes,
    used_chunks: Sequence[bytes],
    excluded: Sequence[bytes],
    before_idat: Iterable[bytes],
) -> bool:
    return b"IDAT" in used_chunks and (
        lastchunk in excluded or lastchunk in set(before_idat)
    )


def only_ihdr_allowed_after_png_header(
    chunks_history: Sequence[bytes],
    chunks: Iterable[bytes],
) -> tuple[bytes, ...] | None:
    if len(chunks_history) == 1 and chunks_history[0] == b"PNG":
        return tuple(chunk for chunk in chunks if chunk != b"IHDR")
    return None
