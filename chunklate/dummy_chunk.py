from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import idat
from .png import complete_iend_tail, repair_missing_ihdr_from_idat


@dataclass(frozen=True)
class DummyChunkDecision:
    action: str
    fixed_data_hex: str = ""
    dummy_data_length: int = 0
    solved: bool = False
    repair: Any | None = None


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
