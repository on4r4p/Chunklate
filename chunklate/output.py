from __future__ import annotations

import os
from dataclasses import dataclass
from collections.abc import Mapping, Sequence
from typing import Any


@dataclass(frozen=True)
class CloneTarget:
    name: str
    directory: str
    path: str


def clone_folder(file_origin: str, file_dir: str = "") -> str:
    folder_name = "Folder_" + os.path.basename(file_origin)
    return os.path.splitext(os.path.join(file_dir, folder_name))[0]


def lockdown_folder_lines(file_origin: str, file_dir: str = "") -> tuple[str, str]:
    folder = clone_folder(file_origin, file_dir)
    return folder, folder + "/"


def ensure_clone_folder(file_origin: str, file_dir: str = "") -> str:
    folder = clone_folder(file_origin, file_dir)
    os.makedirs(folder, exist_ok=True)
    return folder


def clone_basename(file_origin: str) -> str:
    filename = os.path.basename(file_origin)
    if "." in filename:
        filename = os.path.splitext(filename)[0]
    return filename + "."


def next_clone_target(file_origin: str, file_dir: str = "") -> CloneTarget:
    directory = ensure_clone_folder(file_origin, file_dir)
    filename = clone_basename(file_origin)
    fileid = 0
    name = filename + str(fileid) + "_Fixed.png"
    path = os.path.join(directory, name)
    while os.path.exists(path):
        fileid += 1
        name = filename + str(fileid) + "_Fixed.png"
        path = os.path.join(directory, name)
    return CloneTarget(name=name, directory=directory, path=path)


def clone_bytes(data: str | bytes | bytearray) -> bytes:
    if isinstance(data, bytes):
        return data
    if isinstance(data, bytearray):
        return bytes(data)
    return bytes.fromhex(str(data))


def write_clone(target: CloneTarget, data: Any) -> None:
    with open(target.path, "wb") as file:
        file.write(clone_bytes(data))


def summary_path(file_origin: str, file_dir: str = "") -> str:
    folder = ensure_clone_folder(file_origin, file_dir)
    return os.path.join(
        folder,
        "Summary_Of_" + os.path.splitext(os.path.basename(file_origin))[0],
    )


def summary_body(infos: Any, side_notes: Sequence[Any]) -> str | None:
    tmp = ""
    if infos is not None:
        if len(side_notes) > 0:
            for note in side_notes:
                tmp += "\n" + str(note) + "\n"
            return tmp + str(infos) + "\n"
        return "\n" + str(infos) + "\n"
    if len(side_notes) > 0:
        for note in side_notes:
            tmp += "\n" + str(note) + "\n"
        return tmp
    return None


def _value(state: Mapping[str, Any], name: str, default: Any = "") -> Any:
    return state.get(name, default)


def _has_len(value: Any) -> bool:
    return len(value) > 0


def _has_str_len(value: Any) -> bool:
    return len(str(value)) > 0


def _append_if(lines: list[str], state: Mapping[str, Any], name: str, text: str) -> None:
    value = _value(state, name)
    if _has_len(value):
        lines.append(text + str(value))


def render_summary_footer(state: Mapping[str, Any], eof: str) -> str:
    lines: list[str] = ["\n\n『File Informations: 』\n"]

    ihdr_height = _value(state, "IHDR_Height", 0)
    ihdr_width = _value(state, "IHDR_Width", 0)
    if _has_str_len(ihdr_height):
        lines.append("\n")
        lines.append("\n-IHDR Width    :" + str(ihdr_height))
    if _has_str_len(ihdr_height):
        lines.append("\n-IHDR Height   :" + str(ihdr_width))
    for name, label in (
        ("IHDR_Depht", "\n-IHDR Depht    :"),
        ("IHDR_Color", "\n-IHDR Color    :"),
        ("IHDR_Method", "\n-IHDR Method   :"),
        ("IHDR_Interlace", "\n-IHDR Interlace:"),
    ):
        if _has_str_len(_value(state, name, "")):
            lines.append(label + str(_value(state, name)))

    if _has_len(_value(state, "pHYs_X")):
        lines.append("\n")
        lines.append("\n-pHYs Pixels per unit, X axis: " + _value(state, "pHYs_X"))
    _append_if(lines, state, "pHYs_Y", "\n-pHYs Pixels per unit, Y axis: ")
    _append_if(lines, state, "pHYs_Unit", "\n-pHYs Unit specifier         :")

    if _has_len(_value(state, "bKGD_Gray")):
        lines.append("\n")
        lines.append("\n-bKGD Gray   :" + _value(state, "bKGD_Gray"))
    if _has_len(_value(state, "bKGD_Red")):
        lines.append("\n")
        lines.append("\n-bKGD Red    :" + _value(state, "bKGD_Red"))
    _append_if(lines, state, "bKGD_Green", "\n-bKGD Green  :")
    _append_if(lines, state, "bKGD_Blue", "\n-bKGD Blue   :")
    _append_if(lines, state, "bKGD_Index", "\n-bKGD Palette:")

    if _has_len(_value(state, "gAMA")):
        lines.append("\n")
        lines.append("\n-Gama   :" + _value(state, "gAMA"))

    for name, label in (
        ("PLTE_R", "\n-PLTE Red Palettes    :"),
        ("PLTE_G", "\n-PLTE Green Palettes   :"),
        ("PLTE_B", "\n-PLTE Blue Palettes    :"),
    ):
        entries = _value(state, name, [])
        if _has_len(entries):
            if name == "PLTE_R":
                lines.append("\n")
            lines.append(label + str(len(entries)))

    for name, label in (
        ("sPLT_Red", "\n-sPLT Suggested Red palette stored:"),
        ("sPLT_Green", "\n-sPLT Suggested Green palettes stored:"),
        ("sPLT_Blue", "\n-sPLT Suggested Blue palettes stored:"),
        ("sPLT_Alpha", "\n-sPLT Suggested Alpha palettes stored:"),
        ("sPLT_Freq", "\n-sPLT Suggested Frequencies palettes stored:"),
    ):
        entries = _value(state, name, [])
        if _has_len(entries):
            if name == "sPLT_Red":
                lines.append("\n")
            lines.append(label + str(len(entries)))

    if _has_len(_value(state, "hIST", [])):
        lines.append("\n-Histogram frequencies stored:" + str(len(_value(state, "hIST"))))

    if _has_len(_value(state, "tRNS_Gray")):
        lines.append("\n")
        lines.append("\n-tRNS Transparency Gray     :" + _value(state, "tRNS_Gray"))
    _append_if(lines, state, "tRNS_TrueR", "\n-tRNS Transparency Red      :")
    _append_if(lines, state, "tRNS_TrueG", "\n-tRNS Transparency Green    :")
    _append_if(lines, state, "tRNS_TrueB", "\n-tRNS Transparency Blue     :")
    if _has_len(_value(state, "tRNS_Index", [])):
        lines.append("\n-tRNS Alpha indexes stored:" + str(len(_value(state, "tRNS_Index"))))

    if _has_len(_value(state, "sTER")):
        lines.append("\n-Subimage mode    :" + str(_value(state, "sTER")))

    for name, label in (
        ("cHRM_WhiteX", "\n-cHRM chromaticities WhiteX   :"),
        ("cHRM_WhiteY", "\n-cHRM chromaticities WhiteY   :"),
        ("cHRM_Redx", "\n-cHRM chromaticities RedX     :"),
        ("cHRM_Redy", "\n-cHRM chromaticities RedY     :"),
        ("cHRM_Greenx", "\n-cHRM chromaticities GreenX   :"),
        ("cHRM_Greeny", "\n-cHRM chromaticities GreenY   :"),
        ("cHRM_Bluex", "\n-cHRM chromaticities BlueX   :"),
        ("cHRM_Bluey", "\n-cHRM chromaticities BlueY   :"),
    ):
        if _has_len(_value(state, name)):
            if name == "cHRM_WhiteX":
                lines.append("\n")
            lines.append(label + _value(state, name))

    for name, label in (
        ("sBIT_Gray", "\n-sBIT Significant greyscale bits    :"),
        ("sBIT_TrueR", "\n-sBIT significant bits Red    :"),
        ("sBIT_TrueG", "\n-sBIT significant bits Green  :"),
        ("sBIT_TrueB", "\n-sBIT significant bits Blue   :"),
        ("sBIT_GrayScale", "\n-sBIT Gray scale significant bit:"),
        ("sBIT_GrayAlpha", "\n-sBIT Gray alpha significant bit:"),
        ("sBIT_TrueAlphaR", "\n-sBIT significant bits Alpha Red    :"),
        ("sBIT_TrueAlphaG", "\n-sBIT significant bits Alpha Green  :"),
        ("sBIT_TrueAlphaB", "\n-sBIT significant bits Alpha Blue   :"),
        ("sBIT_TrueAlpha", "\n-sBIT significant bits Alpha        :"),
    ):
        if _has_len(_value(state, name)):
            if name == "sBIT_Gray":
                lines.append("\n")
            lines.append(label + _value(state, name))

    if _has_len(_value(state, "pCAL_Key")):
        lines.append("\n")
        lines.append(
            "\n-pCAL Calibration name    :"
            + bytes.fromhex(_value(state, "pCAL_Key")).decode(errors="replace")
        )
    _append_if(lines, state, "pCAL_Zero", "\n-pCAL Original zero       :")
    _append_if(lines, state, "pCAL_Max", "\n-pCAL Original max        :")
    _append_if(lines, state, "pCAL_Eq", "\n-pCAL Equation type       :")
    _append_if(lines, state, "pCAL_PNBR", "\n-pCAL Number of parameters:")

    if _has_len(_value(state, "iCCP_Name")):
        lines.append("\n")
        lines.append("\n-iCCP Profile Name :" + _value(state, "iCCP_Name"))
    if _has_str_len(_value(state, "iCCP_Method")):
        lines.append("\n-iCCP Profile Method :" + str(_value(state, "iCCP_Method")))

    if _has_len(_value(state, "sRGB")):
        lines.append("\n")
        lines.append("\n-sRGB Rendering    :" + _value(state, "sRGB"))

    for name, label in (
        ("tIME_Yr", "\n-Year     :"),
        ("tIME_Mth", "\n-Month    :"),
        ("tIME_Day", "\n-Day      :"),
        ("tIME_Hr", "\n-Hour     :"),
        ("tIME_Min", "\n-Minute   :"),
        ("tIME_Sec", "\n-Seconde  :"),
    ):
        if _has_len(_value(state, name)):
            if name == "tIME_Yr":
                lines.append("\n")
            lines.append(label + _value(state, name))

    text_keys = _value(state, "tEXt_Key_List", [])
    text_strings = _value(state, "tEXt_Str_List", [])
    if _has_len(text_keys) and len(text_keys) == len(text_strings):
        lines.append("\n")
        for string, key in zip(text_strings, text_keys):
            lines.append("\n-tEXt %s :\n%s\n" % (key, string))

    itxt_keys = _value(state, "iTXt_Key_List", [])
    itxt_strings = _value(state, "iTXt_String_List", [])
    if _has_len(itxt_keys) and len(itxt_keys) == len(itxt_strings):
        lines.append("\n")
        for string, key in zip(itxt_strings, itxt_keys):
            lines.append("\n-iTXt %s :\n%s\n" % (key, string))

    ztxt_keys = _value(state, "zTXt_Key_List", [])
    ztxt_strings = _value(state, "zTXt_Str_List", [])
    if _has_len(ztxt_keys) and len(ztxt_keys) == len(ztxt_strings):
        lines.append("\n")
        for string, key in zip(ztxt_strings, ztxt_keys):
            lines.append("\n-zTXt %s :\n%s\n" % (key, string))

    lines.append(eof)
    return "".join(lines)


def summary_separator(waitforit: str, switch: bool, max_columns: int) -> str:
    if switch is True:
        sepa = " ▁ ▂ ▄ ▅ ▆ ▇ █ "
        rator = " █ ▇ ▆ ▅ ▄ ▂ ▁ "
    else:
        sepa = " ▁ ▂ ▄ ▅ ▆ ▇ █ █ ▇ ▆ ▅ ▄ ▂ ▁"
        rator = "▁ ▂ ▄ ▅ ▆ ▇ █ ▇ ▆ ▅ ▄ ▂ ▁"

    space = " " * int((max_columns / 2) - (len(sepa + waitforit + rator) / 2))
    return "\n" + space + sepa + waitforit + rator + "\n\n"


def the_end_debug_lines(
    chunks_history_index: Sequence[Any],
    idat_counter: Any,
    chunks_history: Any,
    idat_bytes_len: Any,
) -> list[Any]:
    return [
        "Chnks nbr:%s" % len(chunks_history_index),
        "idacounter:%s" % idat_counter,
        chunks_history,
        "IDAT_Bytes_Len:%s" % idat_bytes_len,
    ]
