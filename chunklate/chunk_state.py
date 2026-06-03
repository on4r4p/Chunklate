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

    chrm_white_x: str = ""
    chrm_white_y: str = ""
    chrm_red_x: str = ""
    chrm_red_y: str = ""
    chrm_green_x: str = ""
    chrm_green_y: str = ""
    chrm_blue_x: str = ""
    chrm_blue_y: str = ""

    iccp_name: str = ""
    iccp_method: int | str = ""
    iccp_profile: str = ""

    sbit_gray: str = ""
    sbit_true_r: str = ""
    sbit_true_g: str = ""
    sbit_true_b: str = ""
    sbit_gray_scale: str = ""
    sbit_gray_alpha: str = ""
    sbit_true_alpha_r: str = ""
    sbit_true_alpha_g: str = ""
    sbit_true_alpha_b: str = ""
    sbit_true_alpha: str = ""

    offs_x: str = ""
    offs_y: str = ""
    offs_unit: str = ""

    gifg_disposal_method: str = ""
    gifg_user_input_flag: str = ""
    gifg_delay_time: str = ""

    gifx_application_identifier: str = ""
    gifx_authentication_code: str = ""
    gifx_application_data: str = ""

    ster_mode: str = ""

    text_key: str = ""
    text_text: str = ""
    text_key_list: list[str] = field(default_factory=list)
    text_str_list: list[str] = field(default_factory=list)

    ztxt_key: str = ""
    ztxt_text: bytes = b""
    ztxt_key_list: list[str] = field(default_factory=list)
    ztxt_str_list: list[str] = field(default_factory=list)

    itxt_key: str = ""
    itxt_string: str = ""
    itxt_key_list: list[str] = field(default_factory=list)
    itxt_string_list: list[str] = field(default_factory=list)

    exif_endian: str = ""

    def reset_idat(self) -> None:
        self.idat_bytes_len = 0
        self.idat_datastream = ""
        self.idat_counter = 0
        self.idat_bytes_len_history = []
        self.idat_avg_len = ""

    def reset_splt(self) -> None:
        self.splt_name = []
        self.splt_depth = []
        self.splt_red = []
        self.splt_green = []
        self.splt_blue = []
        self.splt_alpha = []
        self.splt_freq = []

    def apply_ihdr(self, info: chunk_info.IhdrInfo) -> None:
        self.ihdr_width = info.width
        self.ihdr_height = info.height
        self.ihdr_depth = info.depth
        self.ihdr_color = info.color
        self.ihdr_method = info.method
        self.ihdr_filter = info.filter_method
        self.ihdr_interlace = info.interlace

    def set_ihdr_legacy(
        self,
        *,
        height: str | int,
        width: str | int,
        depth: str,
        color: str,
        method: str = "",
        filter_method: str = "",
        interlace: str = "",
    ) -> None:
        self.ihdr_height = height
        self.ihdr_width = width
        self.ihdr_depth = depth
        self.ihdr_color = color
        self.ihdr_method = method
        self.ihdr_filter = filter_method
        self.ihdr_interlace = interlace

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

    def set_plte_legacy(
        self,
        red: list[str],
        green: list[str],
        blue: list[str],
    ) -> None:
        self.plte_r = list(red)
        self.plte_g = list(green)
        self.plte_b = list(blue)

    def apply_splt(self, info: chunk_info.SpltInfo) -> None:
        self.splt_red = list(info.red)
        self.splt_green = list(info.green)
        self.splt_blue = list(info.blue)
        self.splt_alpha = list(info.alpha)
        self.splt_freq = list(info.freq)
        self.splt_depth = [info.depth] if len(info.depth) > 0 else []
        self.splt_name = [info.name] if len(info.name) > 0 else []

    def set_splt_legacy(
        self,
        *,
        names: list[str],
        depths: list[str] | None = None,
        red: list[str] | None = None,
        green: list[str] | None = None,
        blue: list[str] | None = None,
        alpha: list[str] | None = None,
        freq: list[str] | None = None,
    ) -> None:
        self.splt_name = list(names)
        if depths is not None:
            self.splt_depth = list(depths)
        if red is not None:
            self.splt_red = list(red)
        if green is not None:
            self.splt_green = list(green)
        if blue is not None:
            self.splt_blue = list(blue)
        if alpha is not None:
            self.splt_alpha = list(alpha)
        if freq is not None:
            self.splt_freq = list(freq)

    def apply_trns(self, info: chunk_info.TrnsInfo) -> None:
        self.trns_index = list(info.indexes)

    def apply_pcal(self, info: chunk_info.PcalInfo) -> None:
        self.pcal_param = list(info.parameters)
        self.pcal_key = info.keyword
        self.pcal_zero = info.zero
        self.pcal_max = info.maximum
        self.pcal_eq = info.equation
        self.pcal_pnbr = info.parameter_count

    def apply_chrm(self, info: chunk_info.ChrmInfo) -> None:
        self.chrm_white_x = info.white_x
        self.chrm_white_y = info.white_y
        self.chrm_red_x = info.red_x
        self.chrm_red_y = info.red_y
        self.chrm_green_x = info.green_x
        self.chrm_green_y = info.green_y
        self.chrm_blue_x = info.blue_x
        self.chrm_blue_y = info.blue_y

    def apply_iccp(self, info: chunk_info.IccpInfo) -> None:
        self.iccp_name = info.name
        self.iccp_method = info.method
        self.iccp_profile = info.profile

    def apply_sbit(self, info: chunk_info.SbitInfo) -> None:
        self.sbit_gray = info.gray
        self.sbit_true_r = info.true_r
        self.sbit_true_g = info.true_g
        self.sbit_true_b = info.true_b
        self.sbit_gray_scale = info.gray_scale
        self.sbit_gray_alpha = info.gray_alpha
        self.sbit_true_alpha_r = info.true_alpha_r
        self.sbit_true_alpha_g = info.true_alpha_g
        self.sbit_true_alpha_b = info.true_alpha_b
        self.sbit_true_alpha = info.true_alpha

    def apply_offs(self, info: chunk_info.OffsInfo) -> None:
        self.offs_x = info.x
        self.offs_y = info.y
        self.offs_unit = info.unit

    def apply_gifg(self, info: chunk_info.GifgInfo) -> None:
        self.gifg_disposal_method = info.disposal_method
        self.gifg_user_input_flag = info.user_input_flag
        self.gifg_delay_time = info.delay_time

    def apply_gifx(self, info: chunk_info.GifxInfo) -> None:
        self.gifx_application_identifier = info.application_identifier
        self.gifx_authentication_code = info.authentication_code
        self.gifx_application_data = info.application_data

    def apply_ster(self, info: chunk_info.SterInfo) -> None:
        self.ster_mode = info.mode

    def apply_text(self, info: chunk_info.TextInfo) -> None:
        self.text_key = info.keyword
        self.text_text = info.text
        self.text_key_list = []
        self.text_str_list = []
        if len(info.decoded_keyword) > 0:
            self.text_key_list.append(info.decoded_keyword)
        if len(info.decoded_text) > 0:
            self.text_str_list.append(info.decoded_text)

    def apply_ztxt(self, info: chunk_info.ZtxtInfo) -> None:
        self.ztxt_key = info.keyword
        self.ztxt_text = info.text
        self.ztxt_key_list = []
        self.ztxt_str_list = []
        if len(info.decoded_keyword) > 0:
            self.ztxt_key_list.append(info.decoded_keyword)
        if len(info.decoded_text) > 0:
            self.ztxt_str_list.append(info.decoded_text)

    def apply_itxt(self, info: chunk_info.ItxtInfo) -> None:
        self.itxt_key = info.keyword
        self.itxt_string = info.text
        self.itxt_key_list = []
        self.itxt_string_list = []
        if len(info.decoded_keyword) > 0:
            self.itxt_key_list.append(info.decoded_keyword)
        if len(info.text) > 0:
            self.itxt_string_list.append(info.text)

    def apply_exif(self, info: chunk_info.ExifInfo) -> None:
        self.exif_endian = info.endian

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
            "has_chrm": any(
                len(value) > 0
                for value in (
                    self.chrm_white_x,
                    self.chrm_white_y,
                    self.chrm_red_x,
                    self.chrm_red_y,
                    self.chrm_green_x,
                    self.chrm_green_y,
                    self.chrm_blue_x,
                    self.chrm_blue_y,
                )
            ),
            "has_iccp": len(self.iccp_name) > 0,
            "has_sbit": any(
                len(value) > 0
                for value in (
                    self.sbit_gray,
                    self.sbit_true_r,
                    self.sbit_true_g,
                    self.sbit_true_b,
                    self.sbit_gray_scale,
                    self.sbit_gray_alpha,
                    self.sbit_true_alpha_r,
                    self.sbit_true_alpha_g,
                    self.sbit_true_alpha_b,
                    self.sbit_true_alpha,
                )
            ),
            "text_entries": len(self.text_key_list),
            "ztxt_entries": len(self.ztxt_key_list),
            "itxt_entries": len(self.itxt_key_list),
            "ster_mode": self.ster_mode,
        }
