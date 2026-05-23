from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .png import LegacyChunkWindow, legacy_chunk_window


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
