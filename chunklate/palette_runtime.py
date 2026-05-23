from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from . import palette, palette_ui


GuessPaletteCount = Callable[[bytes, bytes], int]


@dataclass(frozen=True)
class ManualPaletteSession:
    before: bytes
    after: bytes
    wanabyte: bytes
    palette_count: int
    state: palette_ui.PaletteEditorState


def manual_palette_after_index(data_offset: int, chunk_length: int) -> int:
    return data_offset + (chunk_length - data_offset)


def manual_palette_slices(data_hex: str, data_offset: int, chunk_length: int) -> tuple[bytes, bytes]:
    before = bytes.fromhex(data_hex[:data_offset])
    after = bytes.fromhex(data_hex[manual_palette_after_index(data_offset, chunk_length) :])
    return before, after


def manual_palette_full_new_data(session: ManualPaletteSession) -> bytes:
    if session.after:
        return session.wanabyte[len(session.before) : len(session.wanabyte) - len(session.after)]
    return session.wanabyte[len(session.before) :]


def create_manual_palette_session(
    *,
    data_hex: str,
    data_offset: int,
    chunk_length: int,
    chunk_name: bytes,
    guess_palette_count: GuessPaletteCount,
) -> ManualPaletteSession:
    before, after = manual_palette_slices(data_hex, data_offset, chunk_length)
    wanabyte = palette.initial_manual_palette_png(before, chunk_name, after)
    palette_count = guess_palette_count(before, after)
    return ManualPaletteSession(
        before=before,
        after=after,
        wanabyte=wanabyte,
        palette_count=palette_count,
        state=palette_ui.create_palette_editor_state(palette_count, wanabyte),
    )
