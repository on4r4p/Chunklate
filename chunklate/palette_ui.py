from __future__ import annotations

import binascii
import struct
from dataclasses import dataclass
from typing import Any
from typing import Iterable


EMPTY_PALETTE_ENTRY = "empty"


@dataclass(frozen=True)
class PaletteSaveCheckpoint:
    error: bool
    fixed: bool
    function: str
    chunk: bytes
    infos: tuple[str, ...]
    toolkit: tuple[Any, ...]


def palette_values_to_bytes(values: Iterable[Any]) -> bytes:
    palette_data = b""
    for value in values:
        if value != EMPTY_PALETTE_ENTRY:
            palette_data += int(value).to_bytes(3, "big")
    return palette_data


def build_plte_chunk(palette_data: bytes) -> bytes:
    length = len(palette_data).to_bytes(4, "big")
    checksum = struct.pack("!I", binascii.crc32(b"PLTE" + palette_data))
    return length + b"PLTE" + palette_data + checksum


def build_palette_png(before: bytes, palette_values: Iterable[Any], after: bytes) -> bytes:
    return before + build_plte_chunk(palette_values_to_bytes(palette_values)) + after


def set_palette_value(values: list[Any], index: int, raw_value: Any) -> None:
    if raw_value == "-1":
        values[index] = EMPTY_PALETTE_ENTRY
    else:
        values[index] = raw_value


def apply_color_table(values: list[Any], sliders: Iterable[Any], colors: Iterable[str]) -> None:
    for index, (slider, color) in enumerate(zip(sliders, colors)):
        color_value = int(color, 16)
        values[index] = color_value
        slider.var.set(color_value)


def random_palette_values(values: list[Any], sliders: Iterable[Any], random_int) -> None:
    for index, slider in enumerate(sliders):
        color_value = random_int(0, 16777215)
        values[index] = color_value
        slider.var.set(color_value)


def legacy_palette_count(values: Iterable[Any]) -> int:
    return 256 - list(values).count(EMPTY_PALETTE_ENTRY)


def initial_manual_palette_png(before: bytes, chunk_name: bytes, after: bytes) -> bytes:
    palette_data = bytes.fromhex("000000")
    length = int(3).to_bytes(4, "big")
    checksum = struct.pack("!I", binascii.crc32(chunk_name + palette_data))
    return before + length + chunk_name + palette_data + checksum + after


def save_checkpoint(
    *,
    cancel: bool,
    palette_values: Iterable[Any],
    wanabyte: bytes,
    chunk_length: int,
    data_offset: int,
    from_error: Any,
) -> PaletteSaveCheckpoint:
    if cancel:
        return PaletteSaveCheckpoint(
            error=True,
            fixed=False,
            function="Tk_Save_Plte",
            chunk=b"PLTE",
            infos=("-Manually modify PLTE datas has been canceled by user.",),
            toolkit=(
                wanabyte.hex(),
                data_offset,
                data_offset + chunk_length,
                "-Manually modify PLTE datas has been canceled by user.",
                b"PLTE",
                from_error,
            ),
        )

    return PaletteSaveCheckpoint(
        error=True,
        fixed=True,
        function="Tk_Save_Plte",
        chunk=b"PLTE",
        infos=("-PLTE Data has been replaced manually.",),
        toolkit=(
            wanabyte.hex(),
            data_offset,
            data_offset + chunk_length,
            "-PLTE Data has been modified with %s new palettes."
            % legacy_palette_count(palette_values),
            b"PLTE",
            from_error,
        ),
    )
