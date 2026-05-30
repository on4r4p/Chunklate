from __future__ import annotations

import os
from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from typing import Any

from . import png


LEGACY_BAD_CHUNK_LABEL = "johnnybytesme"


@dataclass(frozen=True)
class WrongCrcTools:
    replacement_crc: Any
    start: Any
    end: Any
    chunk: Any
    offset: Any
    old_crc: Any
    chunk_length: Any = None
    data_offset: Any = None


@dataclass(frozen=True)
class WrongChunkNameTools:
    chunk_type: Any
    chunk_length: Any
    chunk_type_offset: Any
    previous_chunk: Any
    next_marker: Any = None


@dataclass(frozen=True)
class NoNextChunkTools:
    chunk_type: Any
    chunk_length: Any
    previous_chunk: Any


@dataclass(frozen=True)
class DummyChunkTools:
    fixed_data: Any
    dummy_data_length: Any
    bad_position: Any
    bad_start: Any
    bad_end: Any
    from_error: Any


@dataclass(frozen=True)
class WrongCrcRoute:
    source: Any
    error: Any
    chunk_name: str
    tool_prefix: str

    @property
    def is_current_file(self) -> bool:
        return self.source is None


@dataclass(frozen=True)
class DummyChunkRoute:
    source: Any
    error: Any
    chunk_name: str
    tool_prefix: str
    is_critical: bool


@dataclass(frozen=True)
class RelicErrorSummary:
    error: Any
    tools: tuple[tuple[str, Any], ...]


@dataclass(frozen=True)
class RelicSampleSummary:
    sample: Any
    errors: tuple[RelicErrorSummary, ...]


@dataclass(frozen=True)
class PandemoniumPolicyStep:
    action: str


@dataclass(frozen=True)
class NoPandemoniumPolicy:
    action: str
    chunk_name: str | None = None
    struct_index_errors: tuple[Any, ...] = ()
    known_chunk_route: "GetInfoChunkRoute | None" = None
    missing_plte_finding: Any = None


@dataclass(frozen=True)
class NoPandemoniumPromptContext:
    action: str
    print_hits: tuple[Any, ...] = ()


@dataclass(frozen=True)
class WrongCrcBrawlPlan:
    target_file: Any
    chunk: Any
    chunk_length: Any
    data_offset: Any
    from_error: Any
    old_crc: Any
    bf_mode: str | None = None
    brute_length: bool | None = None


@dataclass(frozen=True)
class WrongCrcSaveClonePlan:
    fixed_data: Any
    start: Any
    end: Any
    info: str


@dataclass(frozen=True)
class MissingPlteRepairPlan:
    save_plan: WrongCrcSaveClonePlan
    manual_plan: Any
    preview_data: str


@dataclass(frozen=True)
class DummyChunkBrawlPlan:
    target_file: Any
    chunk: Any
    chunk_length: Any
    data_offset: Any
    from_error: Any


@dataclass(frozen=True)
class GetInfoChunkRoute:
    finding: Any
    chunk_name: str


@dataclass(frozen=True)
class GetInfoBrawlPlan:
    target_file: Any
    chunk: Any
    chunk_length: int
    data_offset: int
    from_error: Any
    bf_mode: str


@dataclass(frozen=True)
class FullChunkForcerPlan:
    target_file: Any
    chunk: Any
    start: int
    end: int
    from_error: Any


@dataclass(frozen=True)
class PlteChunkWindow:
    chunk: bytes
    data_offset: int
    end_offset: int


@dataclass(frozen=True)
class PlteManualPlan:
    target_file: Any
    chunk: bytes
    chunk_length: int
    data_offset: int
    from_error: str


@dataclass(frozen=True)
class PlteRemovePlan:
    start: int
    end: int
    info: str


@dataclass(frozen=True)
class PlteBrawlPlan:
    target_file: Any
    chunk: bytes
    chunk_length: int
    data_offset: int
    from_error: str
    edit_mode: str
    old_crc: Any = None


@dataclass(frozen=True)
class PlteRepairDecision:
    action: str
    plan: Any = None
    side_note: str | None = None


@dataclass(frozen=True)
class DummyChunkRepairDecision:
    action: str
    plan: Any = None


@dataclass(frozen=True)
class RememberedDummyChunkRepairRequest:
    route: DummyChunkRoute
    tools: DummyChunkTools


@dataclass(frozen=True)
class NoPandemoniumRepairDecision:
    action: str
    plan: Any = None


@dataclass(frozen=True)
class SinglePandemoniumDecision:
    action: str
    route: WrongCrcRoute | None = None
    tools: WrongCrcTools | None = None
    plan: WrongCrcBrawlPlan | None = None


@dataclass(frozen=True)
class CurrentWrongCrcPromptContext:
    route: WrongCrcRoute
    tools: WrongCrcTools | None = None
    question_hash: int | None = None


@dataclass(frozen=True)
class RememberedWrongCrcBrawlRequest:
    route: WrongCrcRoute
    tools: WrongCrcTools
    plan: WrongCrcBrawlPlan


def chunk_label(chunk: Any) -> Any:
    if type(chunk) != bytes:
        return chunk
    try:
        return chunk.decode(errors="ignore")
    except Exception:
        return LEGACY_BAD_CHUNK_LABEL


def tool_prefix(chunk: Any) -> str:
    return str(chunk_label(chunk)) + "_Tool_"


def build_tools(chunk: Any, toolkit: tuple[Any, ...]) -> dict[str, Any]:
    prefix = tool_prefix(chunk)
    return {prefix + str(index): tool for index, tool in enumerate(toolkit)}


def tool_key(prefix: str, index: int | str) -> str:
    return prefix + str(index)


def first_tool_prefix(tools: Mapping[str, Any]) -> str | None:
    for key in tools:
        key_str = str(key)
        if key_str.endswith("_Tool_0"):
            return key_str[:-1]
    return None


def resolve_tool_prefix(tools: Mapping[str, Any], preferred_prefix: str) -> str:
    if tool_key(preferred_prefix, 0) in tools:
        return preferred_prefix
    return first_tool_prefix(tools) or preferred_prefix


def tool_value(tools: Mapping[str, Any], prefix: str, index: int | str) -> Any:
    return tools[tool_key(prefix, index)]


def optional_tool_value(
    tools: Mapping[str, Any],
    prefix: str,
    index: int | str,
    default: Any = None,
) -> Any:
    return tools.get(tool_key(prefix, index), default)


def wrong_crc_tools(tools: Mapping[str, Any], prefix: str) -> WrongCrcTools:
    return WrongCrcTools(
        replacement_crc=tool_value(tools, prefix, 0),
        start=tool_value(tools, prefix, 1),
        end=tool_value(tools, prefix, 2),
        chunk=tool_value(tools, prefix, 3),
        offset=tool_value(tools, prefix, 4),
        old_crc=tool_value(tools, prefix, 5),
        chunk_length=optional_tool_value(tools, prefix, 6),
        data_offset=optional_tool_value(tools, prefix, 7),
    )


def wrong_chunk_name_tools(tools: Mapping[str, Any], prefix: str) -> WrongChunkNameTools:
    return WrongChunkNameTools(
        chunk_type=tool_value(tools, prefix, 0),
        chunk_length=tool_value(tools, prefix, 1),
        chunk_type_offset=tool_value(tools, prefix, 2),
        previous_chunk=tool_value(tools, prefix, 3),
        next_marker=optional_tool_value(tools, prefix, 4),
    )


def no_next_chunk_tools(tools: Mapping[str, Any], prefix: str) -> NoNextChunkTools:
    return NoNextChunkTools(
        chunk_type=tool_value(tools, prefix, 0),
        chunk_length=tool_value(tools, prefix, 1),
        previous_chunk=tool_value(tools, prefix, 2),
    )


def dummy_chunk_tools(tools: Mapping[str, Any], prefix: str) -> DummyChunkTools:
    return DummyChunkTools(
        fixed_data=tool_value(tools, prefix, 0),
        dummy_data_length=tool_value(tools, prefix, 1),
        bad_position=tool_value(tools, prefix, 2),
        bad_start=tool_value(tools, prefix, 3),
        bad_end=tool_value(tools, prefix, 4),
        from_error=tool_value(tools, prefix, 5),
    )


def chunk_name_from_text(text: Any, known_chunks: list[bytes] | tuple[bytes, ...]) -> str:
    text = str(text)
    return "".join(
        chunk.decode(errors="ignore")
        for chunk in known_chunks
        if chunk.decode(errors="ignore") in text
    )


def chunk_name_from_tool_keys(tools: Mapping[str, Any], known_chunks: list[bytes] | tuple[bytes, ...]) -> str:
    return chunk_name_from_text(" ".join(str(tool) for tool in tools), known_chunks)


def current_wrong_crc_routes(
    pandora_box: Mapping[Any, Mapping[str, Any]],
    cornucopia: Mapping[Any, Any],
    known_chunks: list[bytes] | tuple[bytes, ...],
) -> list[WrongCrcRoute]:
    routes = []
    for key in pandora_box:
        if "Wrong Crc" not in str(key):
            continue
        if str(key) in cornucopia:
            continue

        chunk_name = chunk_name_from_text(key, known_chunks)
        if not chunk_name:
            continue
        routes.append(
            WrongCrcRoute(
                source=None,
                error=key,
                chunk_name=chunk_name,
                tool_prefix=chunk_name + "_Tool_",
            )
        )
    return routes


def current_wrong_crc_prompt_contexts(
    pandora_box: Mapping[Any, Mapping[str, Any]],
    cornucopia: Mapping[Any, Any],
    known_chunks: list[bytes] | tuple[bytes, ...],
) -> tuple[CurrentWrongCrcPromptContext, ...]:
    contexts = []
    for route in current_wrong_crc_routes(pandora_box, cornucopia, known_chunks):
        if route.chunk_name != "IDAT":
            contexts.append(CurrentWrongCrcPromptContext(route=route))
            continue

        contexts.append(
            CurrentWrongCrcPromptContext(
                route=route,
                tools=wrong_crc_tools(pandora_box[route.error], route.tool_prefix),
                question_hash=question_hash(
                    pandora_box,
                    route.error,
                    route.tool_prefix,
                ),
            )
        )
    return tuple(contexts)


def remembered_wrong_crc_routes(
    pandemonium: Mapping[Any, Mapping[Any, Mapping[str, Any]]],
    known_chunks: list[bytes] | tuple[bytes, ...],
) -> list[WrongCrcRoute]:
    routes = []
    for sample, sample_errors in pandemonium.items():
        for error, tools in sample_errors.items():
            if "Wrong Crc" not in str(error):
                continue

            chunk_name = chunk_name_from_tool_keys(tools, known_chunks)
            if not chunk_name:
                continue
            routes.append(
                WrongCrcRoute(
                    source=sample,
                    error=error,
                    chunk_name=chunk_name,
                    tool_prefix=chunk_name + "_Tool_",
                )
            )
    return routes


def remembered_dummy_chunk_routes(
    pandemonium: Mapping[Any, Mapping[Any, Mapping[str, Any]]],
    known_chunks: list[bytes] | tuple[bytes, ...],
    critical_chunks: list[bytes] | tuple[bytes, ...],
) -> list[DummyChunkRoute]:
    routes = []
    for sample, sample_errors in pandemonium.items():
        for error, tools in sample_errors.items():
            if "Filling with a dummy chunk" not in str(error):
                continue

            chunk_name = chunk_name_from_tool_keys(tools, known_chunks)
            if not chunk_name:
                continue
            routes.append(
                DummyChunkRoute(
                    source=sample,
                    error=error,
                    chunk_name=chunk_name,
                    tool_prefix=chunk_name + "_Tool_",
                    is_critical=chunk_name.encode() in critical_chunks,
                )
            )
    return routes


def first_remembered_dummy_chunk_repair_request(
    pandemonium: Mapping[Any, Mapping[Any, Mapping[str, Any]]],
    known_chunks: list[bytes] | tuple[bytes, ...],
    critical_chunks: list[bytes] | tuple[bytes, ...],
) -> RememberedDummyChunkRepairRequest | None:
    for route in remembered_dummy_chunk_routes(
        pandemonium,
        known_chunks,
        critical_chunks,
    ):
        return RememberedDummyChunkRepairRequest(
            route=route,
            tools=dummy_chunk_tools(
                pandemonium[route.source][route.error],
                route.tool_prefix,
            ),
        )
    return None


def idat_wrong_crc_routes(routes: list[WrongCrcRoute] | tuple[WrongCrcRoute, ...]) -> tuple[WrongCrcRoute, ...]:
    return tuple(route for route in routes if route.chunk_name == "IDAT")


def pandemonium_policy_steps(pandemonium_len: int) -> tuple[PandemoniumPolicyStep, ...]:
    if pandemonium_len < 1:
        return ()

    steps = [
        PandemoniumPolicyStep("current_wrong_crc"),
        PandemoniumPolicyStep("remembered_idat_wrong_crc"),
        PandemoniumPolicyStep("plte"),
    ]
    if pandemonium_len == 1:
        steps.append(PandemoniumPolicyStep("single_pandemonium"))
    else:
        steps.append(PandemoniumPolicyStep("remembered_dummy_chunks"))
    return tuple(steps)


def wrong_crc_save_clone_plan(tools: WrongCrcTools) -> WrongCrcSaveClonePlan:
    return WrongCrcSaveClonePlan(
        fixed_data=tools.replacement_crc,
        start=tools.start,
        end=tools.end,
        info=(
            "-Found Chunk[%s] has Wrong Crc at offset: %s\n-Replaced with: %s old value was: %s"
            % (
                tools.chunk,
                tools.offset,
                tools.replacement_crc,
                tools.old_crc,
            )
        ),
    )


def pandemonium_summary(
    pandemonium: Mapping[Any, Mapping[Any, Mapping[str, Any]]],
) -> tuple[RelicSampleSummary, ...]:
    return tuple(
        RelicSampleSummary(
            sample=sample,
            errors=tuple(
                RelicErrorSummary(error=error, tools=tuple(tools.items()))
                for error, tools in sample_errors.items()
            ),
        )
        for sample, sample_errors in pandemonium.items()
    )


def plte_repair_choices(has_bad_crc: bool) -> tuple[str, ...]:
    if has_bad_crc:
        return ("manually", "bruteforce", "remove", "quit")
    return ("manually", "remove", "quit")


def plte_repair_prompt(has_bad_crc: bool) -> str:
    if has_bad_crc:
        return "Answer(Manually/Bruteforce/Remove/Quit):"
    return "Answer(Manually/Remove/Quit):"


def plte_repair_retry_prompt(has_bad_crc: bool) -> str | None:
    if has_bad_crc:
        return "Answer(Manually/bruteforce/Remove/Quit):"
    return None


def first_current_plte_repair_finding(
    pandora_box: Mapping[Any, Any],
    cornucopia: Mapping[Any, Any],
    *,
    skip_bad_current_name: bool,
    skip_bad_infos: bool,
    skip_bad_critical: bool,
) -> Any | None:
    if skip_bad_current_name or skip_bad_infos or skip_bad_critical:
        return None

    for key in pandora_box:
        if "-PLTE" not in str(key):
            continue
        if str(key) not in cornucopia:
            return key
    return None


def is_missing_plte_finding(finding: Any) -> bool:
    text = str(finding).lower()
    return (
        "missing plte" in text
        or "requires a plte chunk" in text
        or "plte chunk or splt is missing" in text
    )


def first_missing_plte_finding(pandora_box: Mapping[Any, Any]) -> Any | None:
    for key in pandora_box:
        if is_missing_plte_finding(key):
            return key
    return None


def missing_plte_chunk_window(
    chunks_history: list[Any] | tuple[Any, ...],
    chunks_history_index: list[Any] | tuple[Any, ...],
) -> PlteChunkWindow | None:
    for chunk, chunk_index in zip(chunks_history, chunks_history_index):
        if chunk not in (b"tRNS", b"hIST", b"bKGD", b"IDAT"):
            continue
        parts = str(chunk_index).split(":")
        insert_offset = int(parts[1])
        return PlteChunkWindow(
            chunk=b"PLTE",
            data_offset=insert_offset,
            end_offset=insert_offset,
        )
    return None


def missing_plte_save_clone_plan(
    data_hex: str,
    chunks_history: list[Any] | tuple[Any, ...],
    chunks_history_index: list[Any] | tuple[Any, ...],
) -> WrongCrcSaveClonePlan | None:
    window = missing_plte_chunk_window(chunks_history, chunks_history_index)
    if window is None or not data_hex:
        return None

    try:
        chunks = list(png.iter_chunks(bytes.fromhex(data_hex)))
    except (ValueError, png.PngFormatError):
        return None

    ihdr = next((chunk for chunk in chunks if chunk.chunk_type == b"IHDR"), None)
    if ihdr is None or len(ihdr.data) < 10:
        return None

    bit_depth = ihdr.data[8]
    color_type = ihdr.data[9]
    if color_type != 3 or bit_depth not in (1, 2, 4, 8):
        return None

    palette = png.grayscale_palette(2 ** bit_depth)
    if palette is None:
        return None

    return WrongCrcSaveClonePlan(
        fixed_data=png.build_png_chunk(b"PLTE", palette).hex(),
        start=window.data_offset,
        end=window.data_offset,
        info="-Inserted missing indexed PLTE as grayscale palette.",
    )


def missing_plte_repair_plan(
    data_hex: str,
    chunks_history: list[Any] | tuple[Any, ...],
    chunks_history_index: list[Any] | tuple[Any, ...],
    *,
    target_file: Any,
) -> MissingPlteRepairPlan | None:
    save_plan = missing_plte_save_clone_plan(
        data_hex,
        chunks_history,
        chunks_history_index,
    )
    window = missing_plte_chunk_window(chunks_history, chunks_history_index)
    if save_plan is None or window is None:
        return None

    return MissingPlteRepairPlan(
        save_plan=save_plan,
        manual_plan=plte_manual_plan(window, target_file=target_file),
        preview_data=data_hex[: save_plan.start] + save_plan.fixed_data + data_hex[save_plan.end :],
    )


def plte_chunk_window(
    chunks_history: list[Any] | tuple[Any, ...],
    chunks_history_index: list[Any] | tuple[Any, ...],
) -> PlteChunkWindow | None:
    for chunk, chunk_index in zip(chunks_history, chunks_history_index):
        if chunk != b"PLTE":
            continue
        parts = str(chunk_index).split(":")
        return PlteChunkWindow(
            chunk=b"PLTE",
            data_offset=int(parts[1]),
            end_offset=int(parts[2]),
        )
    return None


def plte_manual_plan(window: PlteChunkWindow, *, target_file: Any) -> PlteManualPlan:
    return PlteManualPlan(
        target_file=target_file,
        chunk=window.chunk,
        chunk_length=window.end_offset,
        data_offset=window.data_offset,
        from_error="-PLTE Wrong Data",
    )


def plte_remove_plan(window: PlteChunkWindow) -> PlteRemovePlan:
    return PlteRemovePlan(
        start=window.data_offset,
        end=window.end_offset,
        info="-PLTE Chunk Removed.",
    )


def plte_brawl_plan(
    window: PlteChunkWindow,
    *,
    target_file: Any,
    old_crc: Any = None,
) -> PlteBrawlPlan:
    return PlteBrawlPlan(
        target_file=target_file,
        chunk=window.chunk,
        chunk_length=window.end_offset,
        data_offset=window.data_offset,
        from_error="-PLTE Wrong Data",
        edit_mode="Insert",
        old_crc=old_crc,
    )


def plte_repair_decision(
    answer: Any,
    window: PlteChunkWindow | None,
    *,
    target_file: Any,
    old_crc: Any = None,
    quit_note: str | None = None,
) -> PlteRepairDecision:
    if answer == "quit":
        return PlteRepairDecision("quit", side_note=quit_note)

    if window is None:
        return PlteRepairDecision("none")

    if answer == "manually":
        return PlteRepairDecision(
            "manual",
            plte_manual_plan(window, target_file=target_file),
        )

    if answer == "remove":
        return PlteRepairDecision("remove", plte_remove_plan(window))

    if answer == "bruteforce":
        return PlteRepairDecision(
            "brawl",
            plte_brawl_plan(window, target_file=target_file, old_crc=old_crc),
        )

    return PlteRepairDecision("none")


def remembered_sample_target(
    sample_index: int,
    remembered_sample: Any,
    *,
    file_origin: Any,
    current_sample: Any,
) -> Any:
    if sample_index == 0:
        return file_origin
    return os.path.dirname(current_sample) + "/" + str(remembered_sample)


def wrong_crc_brawl_plan(
    route: WrongCrcRoute,
    tools: WrongCrcTools,
    *,
    target_file: Any,
    from_error: Any,
) -> WrongCrcBrawlPlan:
    if route.chunk_name == "IDAT":
        return WrongCrcBrawlPlan(
            target_file=target_file,
            chunk=tools.chunk,
            chunk_length=tools.chunk_length,
            data_offset=tools.data_offset,
            from_error=from_error,
            old_crc=tools.old_crc,
            bf_mode="TwoBytes",
        )

    return WrongCrcBrawlPlan(
        target_file=target_file,
        chunk=tools.chunk,
        chunk_length=tools.chunk_length,
        data_offset=tools.data_offset,
        from_error=from_error,
        old_crc=tools.old_crc,
        brute_length=False,
    )


def single_pandemonium_decision(
    sample_index: int,
    remembered_sample: Any,
    error: Any,
    tools: Mapping[str, Any],
    *,
    known_chunks: list[bytes] | tuple[bytes, ...],
    file_origin: Any,
    current_sample: Any,
    from_error: Any,
) -> SinglePandemoniumDecision:
    if "Wrong Crc" not in str(error):
        return SinglePandemoniumDecision("unsupported")

    chunk_name = chunk_name_from_tool_keys(tools, known_chunks)
    chunk_tool_prefix = chunk_name + "_Tool_"
    crc_tools = wrong_crc_tools(tools, chunk_tool_prefix)
    route = WrongCrcRoute(
        source=remembered_sample,
        error=error,
        chunk_name=chunk_name,
        tool_prefix=chunk_tool_prefix,
    )
    plan = wrong_crc_brawl_plan(
        route,
        crc_tools,
        target_file=remembered_sample_target(
            sample_index,
            remembered_sample,
            file_origin=file_origin,
            current_sample=current_sample,
        ),
        from_error=from_error,
    )
    return SinglePandemoniumDecision(
        "wrong_crc_brawl",
        route=route,
        tools=crc_tools,
        plan=plan,
    )


def single_pandemonium_decisions(
    pandemonium: Mapping[Any, Mapping[Any, Mapping[str, Any]]],
    *,
    known_chunks: list[bytes] | tuple[bytes, ...],
    file_origin: Any,
    current_sample: Any,
    from_error: Any,
) -> tuple[SinglePandemoniumDecision, ...]:
    decisions = []
    for sample_index, (sample, sample_errors) in enumerate(pandemonium.items()):
        for error, tools in sample_errors.items():
            decisions.append(
                single_pandemonium_decision(
                    sample_index,
                    sample,
                    error,
                    tools,
                    known_chunks=known_chunks,
                    file_origin=file_origin,
                    current_sample=current_sample,
                    from_error=from_error,
                )
            )
    return tuple(decisions)


def remembered_idat_wrong_crc_brawl_requests(
    pandemonium: Mapping[Any, Mapping[Any, Mapping[str, Any]]],
    known_chunks: list[bytes] | tuple[bytes, ...],
    *,
    target_file: Any,
    from_error: Any,
) -> tuple[RememberedWrongCrcBrawlRequest, ...]:
    requests = []
    for route in idat_wrong_crc_routes(
        remembered_wrong_crc_routes(pandemonium, known_chunks)
    ):
        crc_tools = wrong_crc_tools(
            pandemonium[route.source][route.error],
            route.tool_prefix,
        )
        requests.append(
            RememberedWrongCrcBrawlRequest(
                route=route,
                tools=crc_tools,
                plan=wrong_crc_brawl_plan(
                    route,
                    crc_tools,
                    target_file=target_file,
                    from_error=from_error,
                ),
            )
        )
    return tuple(requests)


def dummy_chunk_brawl_plan(
    route: DummyChunkRoute,
    tools: DummyChunkTools,
    *,
    from_error: Any,
) -> DummyChunkBrawlPlan:
    return DummyChunkBrawlPlan(
        target_file=route.source,
        chunk=route.chunk_name,
        chunk_length=tools.dummy_data_length,
        data_offset=tools.bad_start,
        from_error=from_error,
    )


def dummy_chunk_decline_action(route: DummyChunkRoute) -> str:
    if route.is_critical:
        return "end"
    return "todo_end"


def dummy_chunk_repair_decision(
    route: DummyChunkRoute,
    tools: DummyChunkTools,
    *,
    from_error: Any,
    answer: Any,
) -> DummyChunkRepairDecision:
    if answer is True:
        return DummyChunkRepairDecision(
            "brawl",
            dummy_chunk_brawl_plan(route, tools, from_error=from_error),
        )
    return DummyChunkRepairDecision(dummy_chunk_decline_action(route))


def first_getinfo_critical_chunk(
    pandora_box: Mapping[Any, Any],
    critical_chunks: list[bytes] | tuple[bytes, ...],
) -> str | None:
    for key in pandora_box:
        if "GetInfo" not in str(key):
            continue
        for chunk in critical_chunks:
            chunk_name = chunk.decode(errors="ignore")
            if chunk_name in str(key):
                return chunk_name
    return None


def getinfo_struct_index_errors(pandora_box: Mapping[Any, Any], chunk_name: str) -> tuple[Any, ...]:
    return tuple(
        key
        for key in pandora_box
        if chunk_name in str(key) and "StructIndex:" in str(key)
    )


def getinfo_brawl_mode(
    chunk_name: str,
    *,
    struct_index_error_count: int,
    chunks_len_not_fixed: list[bytes] | tuple[bytes, ...],
) -> str:
    if chunk_name.encode() in chunks_len_not_fixed:
        return "Brutus"
    if struct_index_error_count > 2:
        return "Brutus"
    return "Custom"


def getinfo_brawl_plan(
    chunk_name: str,
    chunks_history: list[Any] | tuple[Any, ...],
    chunks_history_index: list[Any] | tuple[Any, ...],
    *,
    target_file: Any,
    from_error: Any,
    chunks_len_not_fixed: list[bytes] | tuple[bytes, ...],
    struct_index_error_count: int,
) -> GetInfoBrawlPlan | None:
    for chunk, chunk_index in zip(chunks_history, chunks_history_index):
        if chunk != chunk_name.encode():
            continue
        parts = str(chunk_index).split(":")
        return GetInfoBrawlPlan(
            target_file=target_file,
            chunk=chunk_name,
            chunk_length=int(parts[2]),
            data_offset=int(parts[1]),
            from_error=from_error,
            bf_mode=getinfo_brawl_mode(
                chunk_name,
                struct_index_error_count=struct_index_error_count,
                chunks_len_not_fixed=chunks_len_not_fixed,
            ),
        )
    return None


def first_getinfo_known_chunk(
    pandora_box: Mapping[Any, Any],
    known_chunks: list[bytes] | tuple[bytes, ...],
) -> GetInfoChunkRoute | None:
    for key in pandora_box:
        if "GetInfo" not in str(key):
            continue
        for chunk in known_chunks:
            chunk_name = chunk.decode(errors="ignore")
            if chunk_name in str(key):
                return GetInfoChunkRoute(finding=key, chunk_name=chunk_name)
    return None


def no_pandemonium_policy(
    pandora_box: Mapping[Any, Any],
    critical_chunks: list[bytes] | tuple[bytes, ...],
    known_chunks: list[bytes] | tuple[bytes, ...],
) -> NoPandemoniumPolicy:
    missing_plte_finding = first_missing_plte_finding(pandora_box)
    if missing_plte_finding is not None:
        return NoPandemoniumPolicy(
            action="missing_plte",
            missing_plte_finding=missing_plte_finding,
        )

    chosen_one = first_getinfo_critical_chunk(pandora_box, critical_chunks)
    struct_index_errors = (
        getinfo_struct_index_errors(pandora_box, chosen_one)
        if chosen_one
        else ()
    )

    if chosen_one and struct_index_errors:
        return NoPandemoniumPolicy(
            action="getinfo_brawl",
            chunk_name=chosen_one,
            struct_index_errors=struct_index_errors,
        )

    known_chunk_route = first_getinfo_known_chunk(pandora_box, known_chunks)
    if known_chunk_route is not None:
        return NoPandemoniumPolicy(
            action="full_chunk_forcer",
            known_chunk_route=known_chunk_route,
        )

    return NoPandemoniumPolicy(action="unsupported")


def getinfo_related_print_hits(
    pandora_box: Mapping[Any, Any],
    chunk_name: str,
    printed_finding: Any,
) -> tuple[Any, ...]:
    return tuple(printed_finding for key in pandora_box if chunk_name in str(key))


def no_pandemonium_prompt_context(
    policy: NoPandemoniumPolicy,
    pandora_box: Mapping[Any, Any],
) -> NoPandemoniumPromptContext:
    if policy.action == "getinfo_brawl":
        return NoPandemoniumPromptContext(
            "getinfo_brawl",
            tuple(policy.struct_index_errors),
        )

    if policy.action == "full_chunk_forcer" and policy.known_chunk_route is not None:
        return NoPandemoniumPromptContext(
            "full_chunk_forcer",
            getinfo_related_print_hits(
                pandora_box,
                policy.known_chunk_route.chunk_name,
                policy.known_chunk_route.finding,
            ),
        )

    if policy.action == "missing_plte" and policy.missing_plte_finding is not None:
        return NoPandemoniumPromptContext(
            "missing_plte",
            (policy.missing_plte_finding,),
        )

    return NoPandemoniumPromptContext("unsupported")


def full_chunk_forcer_plan(
    chunk_name: str,
    chunks_history: list[Any] | tuple[Any, ...],
    chunks_history_index: list[Any] | tuple[Any, ...],
    *,
    target_file: Any,
    from_error: Any,
) -> FullChunkForcerPlan | None:
    for chunk, chunk_index in zip(chunks_history, chunks_history_index):
        if chunk != chunk_name:
            continue
        parts = str(chunk_index).split(":")
        return FullChunkForcerPlan(
            target_file=target_file,
            chunk=chunk_name,
            start=int(parts[1]),
            end=int(parts[2]),
            from_error=from_error,
        )
    return None


def no_pandemonium_repair_decision(
    policy: NoPandemoniumPolicy,
    chunks_history: list[Any] | tuple[Any, ...],
    chunks_history_index: list[Any] | tuple[Any, ...],
    *,
    target_file: Any,
    from_error: Any,
    chunks_len_not_fixed: list[bytes] | tuple[bytes, ...],
    answer: Any,
    data_hex: str = "",
) -> NoPandemoniumRepairDecision:
    if answer is not True:
        return NoPandemoniumRepairDecision("none")

    if policy.action == "getinfo_brawl" and policy.chunk_name is not None:
        plan = getinfo_brawl_plan(
            policy.chunk_name,
            chunks_history,
            chunks_history_index,
            target_file=target_file,
            from_error=from_error,
            chunks_len_not_fixed=chunks_len_not_fixed,
            struct_index_error_count=len(policy.struct_index_errors),
        )
        if plan is not None:
            return NoPandemoniumRepairDecision("getinfo_brawl", plan)
        return NoPandemoniumRepairDecision("none")

    if policy.action == "full_chunk_forcer" and policy.known_chunk_route is not None:
        plan = full_chunk_forcer_plan(
            policy.known_chunk_route.chunk_name,
            chunks_history,
            chunks_history_index,
            target_file=target_file,
            from_error=from_error,
        )
        if plan is not None:
            return NoPandemoniumRepairDecision("full_chunk_forcer", plan)
        return NoPandemoniumRepairDecision("none")

    if policy.action == "missing_plte":
        repair_plan = missing_plte_repair_plan(
            data_hex,
            chunks_history,
            chunks_history_index,
            target_file=target_file,
        )
        if repair_plan is not None:
            return NoPandemoniumRepairDecision("missing_plte_auto", repair_plan)

        window = missing_plte_chunk_window(chunks_history, chunks_history_index)
        if window is not None:
            return NoPandemoniumRepairDecision(
                "plte_manual",
                plte_manual_plan(window, target_file=target_file),
            )
        return NoPandemoniumRepairDecision("none")

    return NoPandemoniumRepairDecision("unsupported")


def next_error_number(pandora_box: Mapping[str, Any], function: Any) -> int:
    number = 0
    for key in pandora_box:
        while key.startswith(str(function) + "_Error_" + str(number)):
            number += 1
    return number


def add_pandora_error(
    pandora_box: MutableMapping[str, Any],
    function: Any,
    info: Any,
    tools: Mapping[str, Any],
) -> str:
    number = next_error_number(pandora_box, function)
    key = str(function) + "_Error_" + str(number) + ":" + str(info)
    pandora_box[key] = tools
    return key


def add_cornucopia_fix(
    cornucopia: MutableMapping[Any, Any],
    key: Any,
    tools: Mapping[str, Any],
) -> Any:
    cornucopia[key] = tools
    return key


def record_checkpoint_registration(
    pandora_box: MutableMapping[str, Any],
    cornucopia: MutableMapping[Any, Any],
    registration: Any,
) -> Any:
    if not registration.should_record:
        return None
    if registration.store == "pandora_box":
        return add_pandora_error(
            pandora_box,
            registration.function,
            registration.info,
            registration.tools,
        )
    if registration.store == "cornucopia":
        return add_cornucopia_fix(cornucopia, registration.store_key, registration.tools)
    raise ValueError("Unknown CheckPoint registration store: %s" % registration.store)


def discard_pandora_error(
    pandora_box: MutableMapping[str, Any],
    key: Any,
    default: Any = "key_not_found",
) -> Any:
    return pandora_box.pop(key, default)


def remember_sample(
    pandemonium: MutableMapping[Any, Any],
    ark_of_covenant: MutableMapping[Any, Any],
    sample: Any,
    pandora_box: MutableMapping[str, Any],
    cornucopia: MutableMapping[Any, Any],
) -> None:
    # Preserve the legacy shared-reference snapshot. Relics relies on the same
    # dict objects for now; switching to a copy is a separate behavior change.
    pandemonium[sample] = pandora_box
    ark_of_covenant[sample] = cornucopia


def question_hash(store: Mapping[Any, Mapping[str, Any]], key: Any, prefix: str) -> int:
    try:
        return hash(
            str(store[key][prefix + "0"])
            + str(store[key][prefix + "1"])
            + str(store[key][prefix + "2"])
        )
    except Exception:
        return hash(key)
