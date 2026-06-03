from __future__ import annotations

import builtins
import os
import re
from dataclasses import dataclass
from collections.abc import Mapping, Sequence
from typing import Any


ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
DEBUG_LINE_PREFIXES = (
    "error:",
    "fixed:",
    "function:",
    "infos:",
    "chunk:",
    "ToolKit:",
    "Arg",
    "Pandora:",
    "key:",
    "Context:",
    "Result:",
    "Question:",
    "Patch bytes ready:",
    "Chnks nbr:",
    "idacounter:",
    "IDAT_Bytes_Len:",
)
DEBUG_DASH_PREFIXES = (
    "-CheckPoint:",
    "-CriticalHit:",
    "-CriticalMiss:",
    "-Error",
    "-No Error",
    "-Saved in",
    "-Saving",
    "-Preview image",
)


@dataclass(frozen=True)
class CloneTarget:
    name: str
    directory: str
    path: str


def source_stem(file_origin: str) -> str:
    filename = os.path.basename(file_origin)
    if filename.lower().endswith(".realpng"):
        filename = filename[: -len(".realpng")]
    if "." in filename:
        filename = os.path.splitext(filename)[0]
    return filename


def clone_folder(file_origin: str, file_dir: str = "") -> str:
    return os.path.join(file_dir, "Folder_" + source_stem(file_origin))


def lockdown_folder_lines(file_origin: str, file_dir: str = "") -> tuple[str, str]:
    folder = clone_folder(file_origin, file_dir)
    return folder, folder + "/"


def ensure_clone_folder(file_origin: str, file_dir: str = "") -> str:
    folder = clone_folder(file_origin, file_dir)
    os.makedirs(folder, exist_ok=True)
    return folder


def clone_basename(file_origin: str) -> str:
    return source_stem(file_origin) + "."


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


def strip_ansi(text: Any) -> str:
    return ANSI_ESCAPE_RE.sub("", str(text))


def clean_summary_text(text: Any) -> str:
    return strip_ansi(text)


def summary_path(file_origin: str, file_dir: str = "") -> str:
    folder = ensure_clone_folder(file_origin, file_dir)
    return os.path.join(
        folder,
        "Summary_Of_" + source_stem(file_origin),
    )


def summary_title(max_columns: int) -> str:
    return summary_separator(
        "▇ ▆ =|C|h|u|n|k|l|a|t|e| |S|u|m|m|a|r|y|= ▆ ▇",
        True,
        max_columns,
    )


def summary_entry_separator(sample_name: str) -> str:
    return "\n\n『" + sample_name + " :』\n"


def summary_operations_header(sample_name: str) -> str:
    return "\n\n『Summary: " + sample_name + "』\n\nOperations:\n"


def _write_summary_header_if_needed(namespace: Mapping[str, Any], handle: Any) -> None:
    if namespace.get("Summary_Header") is True:
        handle.write(summary_title(namespace["MAXCHAR"]))
        namespace["Summary_Header"] = False


def _write_summary_operations_header_if_needed(namespace: Mapping[str, Any], handle: Any) -> None:
    if namespace.get("Summary_Operations_Header") is True:
        return
    sample_name = namespace.get("Sample_Name") or os.path.basename(namespace["FILE_Origin"])
    handle.write(summary_operations_header(sample_name))
    namespace["Summary_Operations_Header"] = True


def _next_summary_step(namespace: Mapping[str, Any]) -> int:
    step = int(namespace.get("Summary_Step_Count", 0)) + 1
    namespace["Summary_Step_Count"] = step
    return step


def _summary_line_title(line: str, default_title: str) -> tuple[str, str]:
    prefixes = (
        ("-CheckPoint:", "CheckPoint"),
        ("-FixItFelix:", "FixItFelix"),
        ("-CriticalHit:", "CriticalHit"),
        ("-CriticalMiss:", "CriticalMiss"),
        ("-Error", "Error"),
        ("Error:", "Error"),
        ("-No Error", "Repair"),
        ("-Saved in", "Output"),
        ("-Saving", "Output"),
        ("-Preview image", "Preview"),
        ("error:", "Error Flag"),
        ("fixed:", "Fixed Flag"),
        ("function:", "Function"),
        ("infos:", "Info"),
        ("chunk:", "Chunk"),
        ("ToolKit:", "ToolKit"),
        ("Arg", "Tool"),
        ("Pandora:", "Pandora"),
        ("key:", "Pandora Key"),
        ("Context:", "Context"),
        ("Result:", "Result"),
        ("Question:", "Question"),
        ("Patch bytes ready:", "Patch"),
        ("Chnks nbr:", "Chunk Count"),
        ("idacounter:", "IDAT Count"),
        ("IDAT_Bytes_Len:", "IDAT Bytes"),
    )
    for prefix, title in prefixes:
        if not line.startswith(prefix):
            continue
        if prefix == "Arg":
            return title, line
        if prefix in ("-Error", "-No Error", "-Saved in", "-Saving", "-Preview image"):
            return title, line[1:].strip()
        detail = line[len(prefix):].strip()
        return title, detail
    return default_title, line


def summary_note_block(note: Any, step: int, *, default_title: str = "Note") -> str:
    lines = [line.strip() for line in clean_summary_text(note).splitlines() if line.strip()]
    if not lines:
        return ""

    title, detail = _summary_line_title(lines[0], default_title)
    output_lines = ["  %03d. %s" % (step, title)]
    if detail:
        separator = ":" if title == "Error" and detail.startswith("-") else ": "
        output_lines[0] += separator + detail
    for line in lines[1:]:
        output_lines.append("       " + line)
    return "\n".join(output_lines) + "\n"


def append_summary_progress_note(namespace: Mapping[str, Any], note: Any) -> None:
    if "FILE_Origin" not in namespace or "FILE_DIR" not in namespace:
        return
    filename = summary_path(namespace["FILE_Origin"], namespace["FILE_DIR"])
    with builtins.open(filename, "a+", encoding="utf-8") as handle:
        _write_summary_header_if_needed(namespace, handle)
        _write_summary_operations_header_if_needed(namespace, handle)
        handle.write(summary_note_block(note, _next_summary_step(namespace)))


def reset_summary_output_if_needed(namespace: dict[str, Any]) -> None:
    if namespace.get("Summary_File_Reset") is True:
        return
    if "FILE_Origin" not in namespace or "FILE_DIR" not in namespace:
        return

    filename = summary_path(namespace["FILE_Origin"], namespace["FILE_DIR"])
    with builtins.open(filename, "w", encoding="utf-8"):
        pass
    namespace["Summary_File_Reset"] = True
    namespace["Summary_Header"] = True
    namespace["Summary_Operations_Header"] = False
    namespace["Summary_Step_Count"] = 0


class ImmediateSummaryNotes(list):
    def __init__(self, namespace: Mapping[str, Any]):
        super().__init__()
        self.namespace = namespace
        self.flushed_count = 0

    def append(self, note: Any) -> None:
        super().append(note)
        append_summary_progress_note(self.namespace, note)
        self.flushed_count = len(self)

    def extend(self, notes: Sequence[Any]) -> None:
        for note in notes:
            self.append(note)


def ensure_immediate_summary_notes(namespace: dict[str, Any]) -> ImmediateSummaryNotes:
    reset_summary_output_if_needed(namespace)
    current = namespace.get("SideNotes", [])
    if isinstance(current, ImmediateSummaryNotes):
        return current
    notes = ImmediateSummaryNotes(namespace)
    for note in current:
        notes.append(note)
    namespace["SideNotes"] = notes
    return notes


def pending_summary_notes(side_notes: Sequence[Any]) -> list[Any]:
    flushed_count = getattr(side_notes, "flushed_count", 0)
    return list(side_notes)[flushed_count:]


def summary_body(infos: Any, side_notes: Sequence[Any]) -> str | None:
    tmp = ""
    if infos is not None:
        if len(side_notes) > 0:
            for note in side_notes:
                tmp += "\n" + clean_summary_text(note) + "\n"
            return tmp + clean_summary_text(infos) + "\n"
        return "\n" + clean_summary_text(infos) + "\n"
    if len(side_notes) > 0:
        for note in side_notes:
            tmp += "\n" + clean_summary_text(note) + "\n"
        return tmp
    return None


def _is_relevant_debug_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.startswith("-Errors Check"):
        return False
    if stripped.startswith(DEBUG_LINE_PREFIXES):
        return True
    return stripped.startswith(DEBUG_DASH_PREFIXES)


def relevant_debug_lines(debug_notes: Sequence[Any]) -> list[str]:
    lines: list[str] = []
    previous = None
    for note in debug_notes:
        for raw_line in clean_summary_text(note).splitlines():
            line = raw_line.strip()
            if not _is_relevant_debug_line(line):
                continue
            if line == previous:
                continue
            lines.append(line)
            previous = line
    return lines


def _debug_value(line: str, prefix: str) -> str:
    return line[len(prefix):].strip()


def _format_debug_event(event: dict[str, Any], step: int) -> str:
    function = event.get("function") or "Checkpoint"
    chunk = event.get("chunk")
    status = "ERROR" if event.get("error") == "True" else "OK"
    if event.get("fixed") == "True":
        status += " fixed"

    header = "  %03d. %s" % (step, function)
    if chunk:
        header += " [%s]" % chunk
    header += ": " + status

    output_lines = [header]
    for info in event.get("infos", []):
        output_lines.append("       info: " + info)
    for arg in event.get("args", []):
        output_lines.append("       tool: " + arg)
    keys = event.get("keys", [])
    if keys:
        output_lines.append("       pandora: " + ", ".join(keys))
    return "\n".join(output_lines) + "\n"


def debug_trace_blocks(debug_notes: Sequence[Any]) -> list[str]:
    blocks: list[str] = []
    event: dict[str, Any] | None = None

    def flush_event() -> None:
        nonlocal event
        if event is None:
            return
        blocks.append(_format_debug_event(event, len(blocks) + 1))
        event = None

    for line in relevant_debug_lines(debug_notes):
        if line.startswith("error:"):
            flush_event()
            event = {"error": _debug_value(line, "error:"), "infos": [], "args": [], "keys": []}
            continue

        if event is not None:
            if line.startswith("fixed:"):
                event["fixed"] = _debug_value(line, "fixed:")
                continue
            if line.startswith("function:"):
                event["function"] = _debug_value(line, "function:")
                continue
            if line.startswith("infos:"):
                event["infos"].append(_debug_value(line, "infos:"))
                continue
            if line.startswith("chunk:"):
                event["chunk"] = _debug_value(line, "chunk:")
                continue
            if line.startswith("Arg"):
                event["args"].append(line)
                continue
            if line.startswith("key:"):
                event["keys"].append(_debug_value(line, "key:"))
                continue
            if line in ("ToolKit:", "Pandora:"):
                continue

        flush_event()
        blocks.append(summary_note_block(line, len(blocks) + 1, default_title="Debug"))

    flush_event()
    return blocks


def debug_trace_body(debug_notes: Sequence[Any]) -> str | None:
    blocks = debug_trace_blocks(debug_notes)
    if len(blocks) == 0:
        return None

    body = ["\n\n『Debug Trace』\n\n"]
    body.extend(blocks)
    body.append("\n")
    return "".join(body)


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


def run_summarise_from_namespace(
    namespace: dict[str, Any],
    infos: Any,
    summary_footer: bool = False,
) -> None:
    reset_summary_output_if_needed(namespace)
    title = summary_title(namespace["MAXCHAR"])
    eof = summary_separator(
        "_,-=|S|u|m|m|a|r|y| |E|n|d|=-,_",
        False,
        namespace["MAXCHAR"],
    )
    current_side_notes = namespace["SideNotes"]
    side_notes = pending_summary_notes(current_side_notes)
    debug_notes = list(namespace.get("DebugNotes", []))
    body = summary_body(infos, side_notes)
    debug_trace = debug_trace_body(debug_notes) if namespace.get("DEBUGFILE") is True else None

    filename = summary_path(namespace["FILE_Origin"], namespace["FILE_DIR"])
    builtins.print(namespace["Candy"]("Color", "green", "-Saving Summary : "), filename)
    with builtins.open(filename, "a+", encoding="utf-8") as handle:

        _write_summary_header_if_needed(namespace, handle)

        if body is not None:
            _write_summary_operations_header_if_needed(namespace, handle)
            for note in side_notes:
                handle.write(summary_note_block(note, _next_summary_step(namespace)))
            if infos is not None:
                handle.write(summary_note_block(infos, _next_summary_step(namespace), default_title="Result"))

        if debug_trace is not None:
            handle.write(debug_trace)

        if summary_footer is True:
            handle.write(render_summary_footer(namespace, eof))

    if namespace.get("DEBUGFILE") is True:
        namespace["DebugNotes"] = []
    if isinstance(current_side_notes, ImmediateSummaryNotes):
        current_side_notes.clear()
        current_side_notes.flushed_count = 0
    else:
        namespace["SideNotes"] = []
