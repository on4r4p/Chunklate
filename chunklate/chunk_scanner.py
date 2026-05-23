from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from . import sorting

from .png import LegacyChunkWindow, legacy_chunk_window


LEGACY_GLOBAL_NAMES = (
    "Raw_Length",
    "Orig_CL",
    "CLoffX",
    "CLoffB",
    "CLoffI",
    "Raw_Type",
    "Orig_CT",
    "CToffX",
    "CToffB",
    "CToffI",
    "Raw_Data",
    "Orig_CD",
    "CDoffX",
    "CDoffB",
    "CDoffI",
    "Raw_Crc",
    "Orig_CRC",
    "CrcoffX",
    "CrcoffB",
    "CrcoffI",
    "Raw_NextChunk",
    "Orig_NC",
    "NCoffX",
    "NCoffB",
    "NCoffI",
)


@dataclass(frozen=True)
class LegacyChunkScanState:
    window: LegacyChunkWindow

    @classmethod
    def scan(cls, data: bytes, offset: int) -> "LegacyChunkScanState":
        return cls(legacy_chunk_window(data, offset))

    def legacy_globals(self) -> dict[str, Any]:
        window = self.window
        return {
            "Raw_Length": window.raw_length,
            "Orig_CL": window.raw_length,
            "CLoffX": window.length_offset_hex,
            "CLoffB": window.length_offset_byte,
            "CLoffI": window.length_offset_index,
            "Raw_Type": window.raw_type,
            "Orig_CT": window.chunk_type,
            "CToffX": window.type_offset_hex,
            "CToffB": window.type_offset_byte,
            "CToffI": window.type_offset_index,
            "Raw_Data": window.raw_data,
            "Orig_CD": window.raw_data,
            "CDoffX": window.data_offset_hex,
            "CDoffB": window.data_offset_byte,
            "CDoffI": window.data_offset_index,
            "Raw_Crc": window.raw_crc,
            "Orig_CRC": window.raw_crc,
            "CrcoffX": window.crc_offset_hex,
            "CrcoffB": window.crc_offset_byte,
            "CrcoffI": window.crc_offset_index,
            "Raw_NextChunk": window.raw_next_chunk,
            "Orig_NC": window.next_chunk_type,
            "NCoffX": window.next_chunk_offset_hex,
            "NCoffB": window.next_chunk_offset_byte,
            "NCoffI": window.next_chunk_offset_index,
        }


def scan_legacy_chunk(data: bytes, offset: int) -> LegacyChunkScanState:
    return LegacyChunkScanState.scan(data, offset)


@dataclass(frozen=True)
class MagicBingoScan:
    bingo_list: list[str]
    best_score: str
    best_signature: str
    best_count: int


def magic_bingo_scan(
    data_hex: str,
    full_magic_hex: str,
    progress: Callable[[], None] | None = None,
) -> MagicBingoScan:
    magic_chars = [i for i in full_magic_hex]
    start = 0
    end = len(full_magic_hex)
    bingo_list = []
    while end <= len(data_hex):
        if progress is not None:
            progress()
        bingo = 0
        sample = data_hex[start:end]
        sample_chars = [i for i in sample]
        for magic_char, sample_char in zip(magic_chars, sample_chars):
            if magic_char == sample_char:
                bingo += 1
        bingo_list.append(str(bingo) + " " + str(sample))
        start += 1
        end += 1
    bingo_list.sort(key=sorting.natural_sort_key)
    bingo_list = bingo_list[::-1]
    best_score = bingo_list[0].split(" ")[0]
    best_signature = bingo_list[0].split(" ")[1]
    best_count = len(
        [
            bingo.split(" ")[0].count(best_score)
            for bingo in bingo_list
            if int(bingo.split(" ")[0].count(best_score)) > 0
        ]
    )
    return MagicBingoScan(
        bingo_list=bingo_list,
        best_score=best_score,
        best_signature=best_signature,
        best_count=best_count,
    )
