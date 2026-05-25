from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import io

from . import palette, palette_ui


GuessPaletteCount = Callable[[bytes, bytes], int]


@dataclass(frozen=True)
class ManualPaletteSession:
    before: bytes
    after: bytes
    wanabyte: bytes
    palette_count: int
    state: palette_ui.PaletteEditorState


@dataclass(frozen=True)
class PaletteCountGuessRuntime:
    cv2: object
    numpy: object
    image: object
    imagehash: object
    stderr_redirector: Callable
    betterror: Callable
    emit: Callable
    candy: Callable
    end: Callable
    raw_print: Callable
    side_notes: list
    build_palette_png: Callable = palette.build_palette_png


@dataclass(frozen=True)
class PaletteCountGuessContext:
    x11_colors: tuple[str, ...]
    libpng_errors: tuple[str, ...]
    ihdr_depth: str


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


def guess_palette_count(
    runtime: PaletteCountGuessRuntime,
    context: PaletteCountGuessContext,
    before: bytes,
    after: bytes,
) -> int:
    hashes = []
    palette_guess_count = None
    palette_values = []

    for index, color in enumerate(context.x11_colors):
        palette_values.append(int(color, 16))
        wanabyte = runtime.build_palette_png(before, palette_values, after)
        stderr = io.BytesIO()

        with runtime.stderr_redirector(stderr):
            try:
                image_array = runtime.cv2.imdecode(
                    runtime.numpy.frombuffer(wanabyte, runtime.numpy.uint8),
                    -1,
                )
            except Exception:
                pass

        result = "{0}".format(stderr.getvalue().decode("utf-8"))
        if any(error in result for error in context.libpng_errors):
            runtime.raw_print("-Error Guess_Palettes_Nbr():", result)
            runtime.end()

        try:
            pil_image = runtime.image.fromarray(image_array)
        except Exception as exc:
            runtime.betterror(exc, "Guess_Palettes_Nbr")
            runtime.raw_print("-Error Guess_Palettes_Nbr():", exc)
            runtime.end()

        current_hash = runtime.imagehash.phash(pil_image)
        hashes.append(current_hash)
        if len(hashes) > 1:
            distance_last = hashes[-2] - hashes[-1]
            if distance_last != 0:
                palette_guess_count = index

    if palette_guess_count:
        runtime.emit(
            "-PLTE palettes number estimation: %s"
            % runtime.candy("Color", "green", str(palette_guess_count))
        )
        runtime.side_notes.append("-PLTE palettes number estimation: %s" % str(palette_guess_count))
        return palette_guess_count

    runtime.emit(runtime.candy("Color", "yellow", "Warning:%s") % "Could not estimate palette number.")
    runtime.side_notes.append(
        "Warning:Could not estimate palette number.Returning Max Palettes number according to IHDR Depht"
    )
    return 2 ** int(context.ihdr_depth) - 1
