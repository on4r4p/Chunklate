from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import chunk_info


@dataclass
class ChunkInfoState:
    ihdr_height: str | int = 0
    ihdr_width: str | int = 0
    ihdr_depth: str = ""
    ihdr_color: str = ""
    ihdr_method: str = ""
    ihdr_filter: str = ""
    ihdr_interlace: str = ""

    idat_bytes_len: int = 0
    idat_datastream: str = ""
    idat_counter: int = 0
    idat_bytes_len_history: list[int] = field(default_factory=list)
    idat_avg_len: int | str = ""

    plte_r: list[str] = field(default_factory=list)
    plte_g: list[str] = field(default_factory=list)
    plte_b: list[str] = field(default_factory=list)

    splt_name: list[str] = field(default_factory=list)
    splt_depth: list[str] = field(default_factory=list)
    splt_red: list[str] = field(default_factory=list)
    splt_green: list[str] = field(default_factory=list)
    splt_blue: list[str] = field(default_factory=list)
    splt_alpha: list[str] = field(default_factory=list)
    splt_freq: list[str] = field(default_factory=list)

    trns_index: list[str] = field(default_factory=list)

    pcal_param: list[str] = field(default_factory=list)
    pcal_key: str = ""
    pcal_zero: str = ""
    pcal_max: str = ""
    pcal_eq: str = ""
    pcal_pnbr: str = ""

    def reset_idat(self) -> None:
        self.idat_bytes_len = 0
        self.idat_datastream = ""
        self.idat_counter = 0
        self.idat_bytes_len_history = []
        self.idat_avg_len = ""

    def apply_ihdr(self, info: chunk_info.IhdrInfo) -> None:
        self.ihdr_width = info.width
        self.ihdr_height = info.height
        self.ihdr_depth = info.depth
        self.ihdr_color = info.color
        self.ihdr_method = info.method
        self.ihdr_filter = info.filter_method
        self.ihdr_interlace = info.interlace

    def next_idat(self, data: str, raw_length_hex: str) -> chunk_info.IdatInfo:
        return chunk_info.parse_idat(
            data,
            raw_length_hex,
            length_history=tuple(self.idat_bytes_len_history),
            bytes_len=self.idat_bytes_len,
            datastream=self.idat_datastream,
            counter=self.idat_counter,
        )

    def apply_idat(self, info: chunk_info.IdatInfo) -> None:
        self.idat_bytes_len_history = list(info.length_history)
        self.idat_avg_len = info.average_length
        self.idat_bytes_len = info.bytes_len
        self.idat_datastream = info.datastream
        self.idat_counter = info.counter

    def apply_plte(self, info: chunk_info.PlteInfo) -> None:
        self.plte_r = list(info.red)
        self.plte_g = list(info.green)
        self.plte_b = list(info.blue)

    def apply_splt(self, info: chunk_info.SpltInfo) -> None:
        self.splt_red = list(info.red)
        self.splt_green = list(info.green)
        self.splt_blue = list(info.blue)
        self.splt_alpha = list(info.alpha)
        self.splt_freq = list(info.freq)
        self.splt_depth = [info.depth] if len(info.depth) > 0 else []
        self.splt_name = [info.name] if len(info.name) > 0 else []

    def apply_trns(self, info: chunk_info.TrnsInfo) -> None:
        self.trns_index = list(info.indexes)

    def apply_pcal(self, info: chunk_info.PcalInfo) -> None:
        self.pcal_param = list(info.parameters)
        self.pcal_key = info.keyword
        self.pcal_zero = info.zero
        self.pcal_max = info.maximum
        self.pcal_eq = info.equation
        self.pcal_pnbr = info.parameter_count

    def splt_entry_count(self) -> int:
        return len(self.splt_red) + len(self.splt_green) + len(self.splt_blue) + len(
            self.splt_alpha
        )

    def plte_entry_count(self) -> int:
        return int((len(self.plte_r) + len(self.plte_g) + len(self.plte_b)) / 3)

    def snapshot(self) -> dict[str, Any]:
        return {
            "ihdr": {
                "width": self.ihdr_width,
                "height": self.ihdr_height,
                "depth": self.ihdr_depth,
                "color": self.ihdr_color,
                "method": self.ihdr_method,
                "filter": self.ihdr_filter,
                "interlace": self.ihdr_interlace,
            },
            "idat": {
                "bytes_len": self.idat_bytes_len,
                "counter": self.idat_counter,
                "avg_len": self.idat_avg_len,
                "history": list(self.idat_bytes_len_history),
            },
            "plte_entries": self.plte_entry_count(),
            "splt_entries": self.splt_entry_count(),
            "trns_indexes": len(self.trns_index),
            "pcal_parameters": len(self.pcal_param),
        }
