from __future__ import annotations

import binascii
from dataclasses import dataclass
from typing import Any, Callable

from . import idat
from .png import complete_iend_tail, repair_missing_ihdr_from_idat


@dataclass(frozen=True)
class DummyChunkDecision:
    action: str
    fixed_data_hex: str = ""
    dummy_data_length: int = 0
    solved: bool = False
    repair: Any | None = None


@dataclass(frozen=True)
class LegacyDummyChunkBuild:
    chunklen_spec: Any
    chunk_format: Any
    color_type: Any
    dummy_length: str
    dummy_name: str
    dummy_data: str
    dummy_crc: str
    chunk_hex: str
    solved: bool = False


def decide_dummy_chunk(chunk_name: bytes, data_hex: str, bad_start_hex: int) -> DummyChunkDecision:
    data = bytes.fromhex(data_hex)

    if chunk_name == b"IHDR":
        repair = repair_missing_ihdr_from_idat(data)
        if repair is not None:
            return DummyChunkDecision(
                action="strict_ihdr_repair",
                fixed_data_hex=repair.data.hex(),
                dummy_data_length=13,
                solved=True,
                repair=repair,
            )
        return DummyChunkDecision(action="fallback")

    if chunk_name == b"IDAT":
        repair = idat.rebuild_partial_idat_blackfill(data)
        if repair is not None:
            return DummyChunkDecision(
                action="partial_idat_blackfill",
                fixed_data_hex=repair.data.hex(),
                dummy_data_length=0,
                solved=True,
                repair=repair,
            )
        return DummyChunkDecision(action="todo")

    if chunk_name == b"IEND":
        fixed_data = complete_iend_tail(data, int(bad_start_hex / 2))
        return DummyChunkDecision(
            action="complete_iend",
            fixed_data_hex=fixed_data.hex(),
            dummy_data_length=0,
            solved=True,
        )

    return DummyChunkDecision(action="fallback")


def build_legacy_ihdr_dummy(
    chunk_name: bytes,
    *,
    get_spec: Callable[..., tuple[Any, Any, Any, Any]],
    spec_length: Callable[[bytes], str],
    random_sample: Callable[[Any, Any, Any], str],
) -> LegacyDummyChunkBuild:
    chunklen_spec, chunk_format, chunk_data, color_type = get_spec(
        chunk_name,
        "Spec",
        Fields=["Length", "Format", "Data", "Color"],
    )
    dummy_length = spec_length(chunk_name)
    dummy_name = hex(int.from_bytes(chunk_name, byteorder="big")).replace("0x", "")
    dummy_data = random_sample(chunk_data, color_type, chunk_format)
    dummy_crc = hex(binascii.crc32(chunk_name + bytes.fromhex(dummy_data))).replace(
        "0x",
        "",
    )
    return LegacyDummyChunkBuild(
        chunklen_spec=chunklen_spec,
        chunk_format=chunk_format,
        color_type=color_type,
        dummy_length=dummy_length,
        dummy_name=dummy_name,
        dummy_data=dummy_data,
        dummy_crc=dummy_crc,
        chunk_hex=dummy_length + dummy_name + dummy_data + dummy_crc,
        solved=False,
    )
