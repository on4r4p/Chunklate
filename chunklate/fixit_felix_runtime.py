from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Any
from typing import Callable

from . import fixit_felix
from . import idat
from . import idat_bruteforce
from . import idat_chain
from . import png
from . import repair_routes
from . import relics
from . import writer


REPEATED_DEFER_MESSAGE_TEMPLATES = (
    "Ah shit ...here we go again ...another {target} in Grove Street. I will keep it for later.",
    "Well, that same smell again: another {target}. I am parking it for later.",
    "I know this tune already: another {target}. I will keep it on the side for now.",
    "Nope, not poking that twice: another {target}. I am saving the headache for later.",
    "Same kind of bruise, new spot: another {target}. I will deal with it after the structure behaves.",
    "That one is waving at us again: another {target}. I am leaving it in the notebook for now.",
    "I have seen this trick before: another {target}. I will keep moving and come back later.",
    "Great. {target}. Exactly what the floor needed: one more rake.",
    "Tiny paperwork, huge consequences: {target}. Later.",
    "I am adding {target} to the suspicious pile, with a little ribbon of shame.",
    "This {target} is wearing a fake moustache. I will question it later.",
    "Not today, {target}. The bigger mess still has the steering wheel.",
    "I am not fixing {target} while the map is still upside down.",
    "Parking {target} next to the other bad ideas.",
    "Logged: {target}. Touching it now would be improv theatre with bytes.",
    "This {target} is probably a symptom, not the patient.",
    "{target} noted. No heroic patching while the floor is moving.",
    "I am leaving {target} alone until I know what it is connected to.",
    "{target} gets a sticky note, not a scalpel.",
    "Fine. {target} goes into the later pile.",
)


@dataclass(frozen=True)
class LegacyFixItFelixHandlers:
    wrong_crc: Callable[[Any, str, int], tuple[bool, Any]]
    libpng_error: Callable[[Any, str], tuple[bool, Any]]
    wrong_chunk_name: Callable[[Any, str], tuple[bool, Any]]
    no_next_chunk: Callable[[Any, str, Any], tuple[bool, Any]]
    gama_zero: Callable[[Any], tuple[bool, Any]]
    critical_miss: Callable[[Any], tuple[bool, Any]]


@dataclass(frozen=True)
class AutomaticRepairRuntime:
    side_notes: Any
    write_clone: Callable[[Any, str], Any]


@dataclass(frozen=True)
class GamaZeroRuntime:
    candy: Callable[..., Any]
    pandora_box: Any
    side_notes: Any
    return_value: Any


@dataclass(frozen=True)
class CriticalMissRuntime:
    emit: Callable[[str], Any]
    candy: Callable[..., Any]
    pause: Callable[[str], Any]
    idat_crc_patch_failed: Callable[[], bool]
    idat_crc_patch_failed_finding: Callable[[], Any]
    idat_crc_defer_explained: Callable[[], bool]
    set_idat_crc_defer_explained: Callable[[bool], Any]
    remember_deferred_idat_crc_finding: Callable[[Any], bool]


@dataclass(frozen=True)
class WrongCrcRuntime:
    emit: Callable[[str], Any]
    candy: Callable[..., Any]
    question: Callable[..., Any]
    save_clone: Callable[[Any, Any, Any, Any], Any]
    write_clone: Callable[[Any, str], Any]
    chunk_story: Callable[..., Any]
    set_skip_bad_crc: Callable[[Any], Any]
    set_old_bad_crc: Callable[[Any], Any]
    side_notes: Any
    pandora_box: Any
    data_hex: str
    cl_offset: Any
    crc_offset: Any
    original_chunk_length_hex: str
    last_question_status: Callable[[], Any]
    set_idat_crc_patch_failed: Callable[[bool], Any]
    set_idat_crc_patch_failed_finding: Callable[[Any], Any]
    remember_deferred_idat_crc_route: Callable[[Any, relics.WrongCrcTools], Any]
    is_deferred_idat_crc_route: Callable[[Any, relics.WrongCrcTools], bool]
    remember_idat_deflate_probe: Callable[[idat.IdatStreamAnalysis], bool]
    debug: bool
    pause_debug: bool
    loadingbar: Callable[..., Any] | None = None
    minibar: Callable[..., Any] | None = None


@dataclass(frozen=True)
class WrongChunkNameRuntime:
    emit: Callable[[str], Any]
    candy: Callable[..., Any]
    question: Callable[..., Any]
    ancillary: Callable[[Any], Any]
    nearby_chunk: Callable[[Any, Any, Any, Any, Any], Any]
    brute_chunk: Callable[[Any, Any, Any, Any], Any]
    save_clone: Callable[[Any, Any, Any, Any], Any]
    write_clone: Callable[[Any, str], Any]
    set_skip_bad_next_name: Callable[[bool], Any]
    set_skip_bad_current_name: Callable[[bool], Any]
    bad_ancillary: Callable[[], bool]
    pandora_box: Any
    cornucopia: Any
    data_hex: str
    side_notes: Any
    remember_wrong_chunk_name_route: Callable[[Any, str, relics.WrongChunkNameTools, str], Any]
    is_wrong_chunk_name_route_tried: Callable[[Any, str, relics.WrongChunkNameTools, str], bool]
    loadingbar: Callable[..., Any] | None = None
    minibar: Callable[..., Any] | None = None


@dataclass(frozen=True)
class NoNextChunkRuntime:
    emit: Callable[[str], Any]
    candy: Callable[..., Any]
    question: Callable[..., Any]
    side_notes: Any
    pandora_box: Any
    sample: Any
    data_hex: str
    cl_offset: Any
    crc_offset: int
    original_chunk_length_hex: str
    raw_crc: Any
    debug: bool
    pause_debug: bool
    pause_error: bool
    bad_missplaced: bool
    set_skip_bad_no_next_chunk: Callable[[bool], Any]
    set_eof: Callable[[bool], Any]
    eof: Callable[[], bool]
    chunk_story: Callable[..., Any]
    check_chunk_order: Callable[..., Any]
    libpng_check: Callable[[Any], Any]
    the_good_place: Callable[[Any, Any, Any], Any]
    write_clone: Callable[[Any, str], Any]
    the_end: Callable[[], Any]
    pause: Callable[[str], Any]
    debug_print: Callable[..., Any]
    dummy_chunk: Callable[..., Any]
    nearby_chunk: Callable[..., Any]
    nearby_found_later_iend: Callable[[], Any]
    loadingbar: Callable[..., Any] | None = None
    minibar: Callable[..., Any] | None = None


@dataclass(frozen=True)
class LibpngErrorRuntime:
    emit: Callable[[str], Any]
    candy: Callable[..., Any]
    question: Callable[..., Any]
    the_end: Callable[[], Any]
    run_relics: Callable[[str], Any]
    save_clone: Callable[[Any, Any, Any, Any], Any]
    groundhog_day: Callable[[Any], Any]
    set_skip_bad_libpng: Callable[[bool], Any]
    pandora_box: Any
    cornucopia: Any
    sample: Any


def build_wrong_crc_runtime_from_namespace(namespace: dict[str, Any]) -> WrongCrcRuntime:
    return WrongCrcRuntime(
        emit=namespace["PRINT"],
        candy=namespace["Candy"],
        question=namespace["Question"],
        save_clone=namespace["SaveClone"],
        write_clone=namespace["WriteClone"],
        chunk_story=namespace["ChunkStory"],
        set_skip_bad_crc=namespace["FixItFelix_Set_Skip_Bad_Crc"],
        set_old_bad_crc=namespace["FixItFelix_Set_Old_Bad_Crc"],
        side_notes=namespace["SideNotes"],
        pandora_box=namespace["PandoraBox"],
        data_hex=namespace["DATAX"],
        cl_offset=namespace["CLoffI"],
        crc_offset=namespace["CrcoffI"],
        original_chunk_length_hex=namespace["Orig_CL"],
        last_question_status=lambda: namespace.get("LAST_QUESTION_STATUS"),
        set_idat_crc_patch_failed=lambda value: namespace.__setitem__("IDAT_CRC_PATCH_FAILED", value),
        set_idat_crc_patch_failed_finding=lambda value: namespace.__setitem__("IDAT_CRC_PATCH_FAILED_FINDING", value),
        remember_deferred_idat_crc_route=lambda finding, tools: remember_deferred_idat_crc_route(namespace, finding, tools),
        is_deferred_idat_crc_route=lambda finding, tools: is_deferred_idat_crc_route(namespace, finding, tools),
        remember_idat_deflate_probe=lambda analysis: remember_idat_deflate_probe(namespace, analysis),
        debug=namespace["DEBUG"],
        pause_debug=namespace["PAUSEDEBUG"],
        loadingbar=namespace.get("Loadingbar"),
        minibar=namespace.get("Minibar"),
    )


def build_libpng_error_runtime_from_namespace(namespace: dict[str, Any]) -> LibpngErrorRuntime:
    return LibpngErrorRuntime(
        emit=namespace["PRINT"],
        candy=namespace["Candy"],
        question=namespace["Question"],
        the_end=namespace["TheEnd"],
        run_relics=namespace["Relics"],
        save_clone=namespace["SaveClone"],
        groundhog_day=namespace["GroundhogDay"],
        set_skip_bad_libpng=namespace["FixItFelix_Set_Skip_Bad_Libpng"],
        pandora_box=namespace["PandoraBox"],
        cornucopia=namespace["Cornucopia"],
        sample=namespace["Sample"],
    )


def build_wrong_chunk_name_runtime_from_namespace(namespace: dict[str, Any]) -> WrongChunkNameRuntime:
    return WrongChunkNameRuntime(
        emit=namespace["PRINT"],
        candy=namespace["Candy"],
        question=namespace["Question"],
        ancillary=namespace["Ancillary"],
        nearby_chunk=namespace["NearbyChunk"],
        brute_chunk=namespace["BruteChunk"],
        save_clone=namespace["SaveClone"],
        write_clone=namespace["WriteClone"],
        set_skip_bad_next_name=namespace["FixItFelix_Set_Skip_Bad_Next_Name"],
        set_skip_bad_current_name=namespace["FixItFelix_Set_Skip_Bad_Current_Name"],
        bad_ancillary=lambda: namespace["Bad_Ancillary"],
        pandora_box=namespace["PandoraBox"],
        cornucopia=namespace["Cornucopia"],
        data_hex=namespace["DATAX"],
        side_notes=namespace["SideNotes"],
        remember_wrong_chunk_name_route=lambda finding, chkd, tools, action: remember_wrong_chunk_name_route(
            namespace,
            finding,
            chkd,
            tools,
            action,
        ),
        is_wrong_chunk_name_route_tried=lambda finding, chkd, tools, action: is_wrong_chunk_name_route_tried(
            namespace,
            finding,
            chkd,
            tools,
            action,
        ),
        loadingbar=namespace.get("Loadingbar"),
        minibar=namespace.get("Minibar"),
    )


def build_no_next_chunk_runtime_from_namespace(namespace: dict[str, Any]) -> NoNextChunkRuntime:
    return NoNextChunkRuntime(
        emit=namespace["PRINT"],
        candy=namespace["Candy"],
        question=namespace["Question"],
        side_notes=namespace["SideNotes"],
        pandora_box=namespace["PandoraBox"],
        sample=namespace["Sample"],
        data_hex=namespace["DATAX"],
        cl_offset=namespace["CLoffI"],
        crc_offset=namespace["CrcoffI"],
        original_chunk_length_hex=namespace["Orig_CL"],
        raw_crc=namespace["Raw_Crc"],
        debug=namespace["DEBUG"],
        pause_debug=namespace["PAUSEDEBUG"],
        pause_error=namespace["PAUSEERROR"],
        bad_missplaced=namespace["Bad_Missplaced"],
        set_skip_bad_no_next_chunk=namespace["FixItFelix_Set_Skip_Bad_No_Next_Chunk"],
        set_eof=namespace["FixItFelix_Set_EOF"],
        eof=lambda: namespace["EOF"],
        chunk_story=namespace["ChunkStory"],
        check_chunk_order=namespace["CheckChunkOrder"],
        libpng_check=namespace["LibpngCheck"],
        the_good_place=namespace["TheGoodPlace"],
        write_clone=namespace["WriteClone"],
        the_end=namespace["TheEnd"],
        pause=namespace["Pause"],
        debug_print=print,
        dummy_chunk=namespace["DummyChunk"],
        nearby_chunk=namespace["NearbyChunk"],
        nearby_found_later_iend=lambda: namespace.get("NEARBY_FOUND_LATER_IEND"),
        loadingbar=namespace.get("Loadingbar"),
        minibar=namespace.get("Minibar"),
    )


def build_gama_zero_runtime_from_namespace(namespace: dict[str, Any]) -> GamaZeroRuntime:
    return GamaZeroRuntime(
        candy=namespace["Candy"],
        pandora_box=namespace["PandoraBox"],
        side_notes=namespace["SideNotes"],
        return_value=namespace["FixItFelix"],
    )


def build_critical_miss_runtime_from_namespace(namespace: dict[str, Any]) -> CriticalMissRuntime:
    return CriticalMissRuntime(
        emit=namespace["PRINT"],
        candy=namespace["Candy"],
        pause=namespace["Pause"],
        idat_crc_patch_failed=lambda: bool(namespace.get("IDAT_CRC_PATCH_FAILED")),
        idat_crc_patch_failed_finding=lambda: namespace.get("IDAT_CRC_PATCH_FAILED_FINDING"),
        idat_crc_defer_explained=lambda: bool(namespace.get("IDAT_CRC_DEFER_EXPLAINED")),
        set_idat_crc_defer_explained=lambda value: namespace.__setitem__("IDAT_CRC_DEFER_EXPLAINED", value),
        remember_deferred_idat_crc_finding=lambda finding: remember_deferred_idat_crc_finding(namespace, finding),
    )


def build_automatic_repair_runtime_from_namespace(namespace: dict[str, Any]) -> AutomaticRepairRuntime:
    return AutomaticRepairRuntime(
        side_notes=namespace["SideNotes"],
        write_clone=namespace["WriteClone"],
    )


def emit_libpng_critical(runtime: LibpngErrorRuntime, finding: Any) -> None:
    runtime.emit("\n-\033[1;31;49mCriticalHit\033[m: %s" % finding)


def apply_repair(runtime: AutomaticRepairRuntime, repair: Any) -> bool:
    applied_repair = fixit_felix.applied_repair(repair)
    runtime.side_notes.append(applied_repair.note)
    runtime.write_clone(applied_repair.data_hex, applied_repair.save_suffix)
    return True


def apply_gama_zero(runtime: GamaZeroRuntime, decision: fixit_felix.GamaZeroDecision) -> tuple[bool, Any]:
    if decision.action == "discard_false_positive":
        runtime.candy("Cowsay", "Bah that's just a warning who cares ?! !", "good")
        relics.discard_pandora_error(
            runtime.pandora_box,
            decision.false_positive.finding,
        )
        runtime.side_notes.append(decision.false_positive.note)
        return True, runtime.return_value

    raise ValueError("Unknown FixItFelix gAMA action: %s" % decision.action)


def apply_critical_miss(
    runtime: CriticalMissRuntime,
    decision: fixit_felix.CriticalMissDecision,
) -> tuple[bool, Any]:
    runtime.emit("\n-\033[1;31;49mCriticalMiss\033[m: %s" % decision.finding)
    explain_deferred_idat_crc(runtime, decision.finding)
    if decision.action == "pause_debug":
        runtime.pause("Pause:Debug")
        return False, None
    if decision.action == "continue":
        return False, None

    raise ValueError("Unknown FixItFelix critical-miss action: %s" % decision.action)


def is_idat_wrong_crc_finding(finding: Any) -> bool:
    text = str(finding)
    return "Wrong Crc" in text and "IDAT" in text


def deferred_idat_crc_route_key(
    _finding: Any,
    tools: relics.WrongCrcTools,
) -> repair_routes.RepairRouteKey:
    return repair_routes.route_key(
        "idat_crc_only",
        chunk=tools.chunk,
        file_offset=tools.offset,
        source=tools.old_crc,
        target=tools.replacement_crc,
        start=tools.start,
        end=tools.end,
    )


def remember_deferred_idat_crc_route(
    namespace: dict[str, Any],
    finding: Any,
    tools: relics.WrongCrcTools,
) -> None:
    key = deferred_idat_crc_route_key(finding, tools)
    routes = namespace.setdefault("IDAT_CRC_DEFERRED_ROUTES", set())
    routes.add(key)
    repair_routes.remember_route(namespace, key, "deferred")


def is_deferred_idat_crc_route(
    namespace: dict[str, Any],
    finding: Any,
    tools: relics.WrongCrcTools,
) -> bool:
    key = deferred_idat_crc_route_key(finding, tools)
    routes = namespace.setdefault("IDAT_CRC_DEFERRED_ROUTES", set())
    if key in routes or repair_routes.is_exhausted(namespace, key):
        repair_routes.remember_route(namespace, key, "skipped_duplicate")
        return True
    return False


def idat_deflate_probe_key(analysis: idat.IdatStreamAnalysis) -> tuple[Any, ...]:
    return (
        analysis.status,
        analysis.idat_chunk_count,
        analysis.compressed_size,
        analysis.error_offset,
        analysis.error_file_offset,
        analysis.error_context_hex,
    )


def remember_idat_deflate_probe(namespace: dict[str, Any], analysis: idat.IdatStreamAnalysis) -> bool:
    seen = namespace.setdefault("IDAT_DEFLATE_PROBE_KEYS", set())
    key = idat_deflate_probe_key(analysis)
    if key in seen:
        return False
    seen.add(key)
    return True


def remember_deferred_idat_crc_finding(namespace: dict[str, Any], finding: Any) -> bool:
    seen = namespace.setdefault("IDAT_CRC_DEFERRED_FINDINGS", set())
    text = str(finding)
    if text in seen:
        return False
    seen.add(text)
    return True


def _route_value(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return str(value)


def _route_offset(value: Any) -> str:
    try:
        return "0x%x" % int(value)
    except (TypeError, ValueError):
        return str(value)


def wrong_chunk_name_route_key(
    _finding: Any,
    _chkd: str,
    tools: relics.WrongChunkNameTools,
    action: str,
) -> tuple[str, str, str, str, str, str]:
    return (
        "wrong_chunk_name",
        action,
        _route_value(tools.chunk_type),
        _route_offset(tools.chunk_type_offset),
        str(tools.chunk_length),
        _route_value(tools.previous_chunk),
    )


def wrong_chunk_name_route_label(tools: relics.WrongChunkNameTools) -> str:
    return "%s at %s" % (
        _route_value(tools.chunk_type),
        _route_offset(tools.chunk_type_offset),
    )


def remember_wrong_chunk_name_route(
    namespace: dict[str, Any],
    finding: Any,
    chkd: str,
    tools: relics.WrongChunkNameTools,
    action: str,
) -> None:
    key = wrong_chunk_name_route_key(finding, chkd, tools, action)
    routes = namespace.setdefault("WRONG_CHUNK_NAME_TRIED_ROUTES", set())
    routes.add(key)
    repair_routes.remember_route(namespace, key, "tried")


def is_wrong_chunk_name_route_tried(
    namespace: dict[str, Any],
    finding: Any,
    chkd: str,
    tools: relics.WrongChunkNameTools,
    action: str,
) -> bool:
    key = wrong_chunk_name_route_key(finding, chkd, tools, action)
    routes = namespace.setdefault("WRONG_CHUNK_NAME_TRIED_ROUTES", set())
    if key in routes or repair_routes.is_exhausted(namespace, key):
        repair_routes.remember_route(namespace, key, "skipped_duplicate")
        return True
    return False


def _remember_wrong_chunk_name_note(
    runtime: WrongChunkNameRuntime,
    tools: relics.WrongChunkNameTools,
    status: str,
    reason: str = "",
) -> None:
    note = "-Repair hypothesis %s: chunk-name recovery for %s." % (
        status,
        wrong_chunk_name_route_label(tools),
    )
    if reason:
        note = note[:-1] + "; reason: %s." % reason
    runtime.side_notes.append(note)


def _emit_wrong_chunk_name_deja_vu(runtime: WrongChunkNameRuntime, tools: relics.WrongChunkNameTools) -> None:
    runtime.candy("Cowsay", "Huh ..? Déja-vu. I already tried that repair route .", "com")
    runtime.candy(
        "Cowsay",
        "So i'm changing the answer before we headbutt the same door twice.",
        "com",
    )
    _remember_wrong_chunk_name_note(runtime, tools, "skipped", "route was already tried")


def _chunk_label(chunk: Any) -> str:
    if isinstance(chunk, bytes):
        try:
            return chunk.decode("latin1")
        except Exception:
            return repr(chunk)
    return str(chunk)


def _chunk_article(label: str) -> str:
    if not label:
        return "a"
    return "an" if label[0].upper() in {"A", "E", "I", "O", "U"} else "a"


def repeated_deferred_repair_message(
    *,
    error_label: str,
    chunk: Any = None,
    chooser: Callable[[tuple[str, ...]], str] | None = None,
) -> str:
    if chunk is None:
        target = error_label
    else:
        label = _chunk_label(chunk)
        target = "%s in %s %s chunk" % (error_label, _chunk_article(label), label)

    pick = chooser or random.choice
    return pick(REPEATED_DEFER_MESSAGE_TEMPLATES).format(target=target)


def explain_deferred_idat_crc(runtime: CriticalMissRuntime, finding: Any) -> None:
    if not is_idat_wrong_crc_finding(finding):
        return
    if not runtime.idat_crc_patch_failed():
        return
    if str(finding) == str(runtime.idat_crc_patch_failed_finding()):
        return
    if not runtime.remember_deferred_idat_crc_finding(finding):
        return

    if not runtime.idat_crc_defer_explained():
        runtime.candy(
            "Cowsay",
            "The CRCs are wrong, yes. But if I fix them now, i'm just putting clean labels on suspicious boxes.",
            "bad",
        )
        runtime.candy(
            "Cowsay",
            "Those IDAT boxes are glued together into one zlib stream. Right now the stream is still coughing blood, so a nice CRC would only lie better.",
            "com",
        )
        runtime.candy(
            "Cowsay",
            "I'm leaving these CRCs alone until the chunk structure makes sense. Then we fix the labels.",
            "good",
        )
        runtime.set_idat_crc_defer_explained(True)
        return

    runtime.candy(
        "Cowsay",
        repeated_deferred_repair_message(error_label="wrong CRC", chunk=b"IDAT"),
        "com",
    )


def emit_wrong_crc_critical(runtime: WrongCrcRuntime, finding: Any) -> None:
    runtime.emit("\n-\033[1;31;49mCriticalHit\033[m: %s" % finding)


def save_wrong_crc(runtime: WrongCrcRuntime, tools: relics.WrongCrcTools) -> tuple[bool, Any]:
    save_plan = relics.wrong_crc_save_clone_plan(tools)
    return True, runtime.save_clone(
        save_plan.fixed_data,
        save_plan.start,
        save_plan.end,
        save_plan.info,
    )


def defer_wrong_crc(runtime: WrongCrcRuntime, tools: relics.WrongCrcTools) -> tuple[bool, None]:
    runtime.chunk_story(
        "add",
        tools.chunk,
        runtime.cl_offset,
        runtime.crc_offset + 8,
        int(runtime.original_chunk_length_hex, 16),
    )
    runtime.set_old_bad_crc(tools.old_crc)
    runtime.set_skip_bad_crc(True)
    return False, None


@dataclass(frozen=True)
class WrongCrcPatchValidation:
    can_save: bool
    reason: str = ""
    stream_analysis: idat.IdatStreamAnalysis | None = None


def idat_stream_diagnosis_note(analysis: idat.IdatStreamAnalysis) -> str:
    details = [
        "-IDAT stream diagnosis: status=%s" % analysis.status,
        "chunks=%s" % analysis.idat_chunk_count,
        "compressed=%s" % analysis.compressed_size,
        "decompressed=%s" % analysis.decompressed_size,
        "expected=%s" % analysis.expected_size,
        "scanlines=%s/%s" % (analysis.usable_scanlines, analysis.height),
    ]
    if analysis.error_offset is not None:
        details.append("error_offset=%s" % analysis.error_offset)
    if analysis.error_idat_index is not None:
        details.append("error_idat=%s/%s" % (analysis.error_idat_index, analysis.idat_chunk_count))
    if analysis.error_idat_offset is not None:
        details.append("error_idat_offset=0x%x" % analysis.error_idat_offset)
    if analysis.error_file_offset is not None:
        details.append("error_file_offset=0x%x" % analysis.error_file_offset)
    if analysis.error_context_hex:
        details.append("error_context=%s" % analysis.error_context_hex)
    reason = analysis.reason or analysis.zlib_error
    if reason:
        details.append("reason=%s" % reason)
    return "; ".join(details) + "."


def defer_idat_crc_only_note(reason: str) -> str:
    return "-Deferred IDAT CRC-only patch: zlib stream still invalid: %s." % reason


def remember_deferred_idat_crc_note(runtime: WrongCrcRuntime, validation: WrongCrcPatchValidation) -> None:
    if validation.stream_analysis is not None:
        runtime.side_notes.append(idat_stream_diagnosis_note(validation.stream_analysis))
    if validation.reason:
        runtime.side_notes.append(defer_idat_crc_only_note(validation.reason))


def _runtime_can_write_clone(runtime: Any) -> bool:
    return callable(getattr(runtime, "write_clone", None))


def _remember_runtime_idat_probe(runtime: Any, analysis: idat.IdatStreamAnalysis) -> bool:
    remember = getattr(runtime, "remember_idat_deflate_probe", None)
    if remember is None:
        return True
    return bool(remember(analysis))


def _runtime_idat_heavy_progress(runtime: Any):
    loadingbar = getattr(runtime, "loadingbar", None)
    if loadingbar is None:
        return None

    def progress(loop_index: int, budget: int, build: bool) -> None:
        loadingbar(budget, len(str(budget)), loop_index, build)

    return progress


def _runtime_idat_queue_progress(runtime: Any):
    minibar = getattr(runtime, "minibar", None)
    if minibar is None:
        return None

    def progress(stage: str, tested: int, budget: int) -> None:
        minibar("IDAT %s %s/%s" % (stage, tested, budget))

    return progress


def _ask_idat_heavy_probe(runtime: Any, analysis: idat.IdatStreamAnalysis) -> bool:
    runtime.candy(
        "Cowsay",
        "The next probe is heavier. It may take a bit, but it still only writes if the stream actually moves forward.",
        "com",
    )
    answer = runtime.question(
        id="IDAT Heavy Probe:-Deflate stream still broken",
        idhash=idat_deflate_probe_key(analysis),
    )
    if answer is True:
        return True

    runtime.candy(
        "Cowsay",
        "Fair. I am not sending the fish into the engine room without permission.",
        "com",
    )
    runtime.side_notes.append("-IDAT heavy probe declined by user.")
    return False


def try_idat_deflate_bruteforce(
    runtime: Any,
    analysis: idat.IdatStreamAnalysis | None = None,
) -> tuple[bool, Any] | None:
    if not _runtime_can_write_clone(runtime):
        return None

    try:
        data = bytes.fromhex(runtime.data_hex)
    except Exception:
        return None

    analysis = analysis or idat.analyze_idat_stream(data)
    if analysis.complete or not analysis.supported:
        return None
    if analysis.status not in ("corrupt_deflate", "incomplete_stream", "bad_adler"):
        return None
    if analysis.error_offset is None:
        return None
    if not _remember_runtime_idat_probe(runtime, analysis):
        runtime.candy(
            "Cowsay",
            "I already poked that exact IDAT wound. Same smell, same bandage budget.",
            "com",
        )
        return None

    runtime.candy(
        "Cowsay",
        "The boxes line up now, but the compressed stuff inside is still screaming.",
        "bad",
    )
    runtime.candy(
        "Cowsay",
        "I will run the bounded IDAT strategy queue: strict byte, pre-error bit flips, then a wider byte probe.",
        "com",
    )
    runtime.side_notes.append(idat_stream_diagnosis_note(analysis))
    probe = idat_bruteforce.probe_idat_deflate_strategy_queue(
        data,
        progress=_runtime_idat_queue_progress(runtime),
    )
    runtime.side_notes.append(idat_bruteforce.probe_summary_line(probe))

    if probe.best is None:
        runtime.candy(
            "Cowsay",
            "I tried the small deflate probe. Nothing got better, so I could send the fish into a wider net.",
            "bad",
        )
        if not _ask_idat_heavy_probe(runtime, analysis):
            runtime.side_notes.append("-IDAT deflate heavy probe skipped: user declined.")
            return None

        heavy_probe = idat_bruteforce.probe_idat_deflate_heavy_candidates(
            data,
            progress=_runtime_idat_heavy_progress(runtime),
        )
        runtime.side_notes.append(idat_bruteforce.probe_summary_line(heavy_probe))

        if getattr(runtime, "emit", None) is not None:
            runtime.emit("")

        if heavy_probe.best is not None:
            probe = heavy_probe
        else:
            runtime.candy(
                "Cowsay",
                "The fish came back wet and empty. No measurable progress, no clone.",
                "bad",
            )
            runtime.candy(
                "Cowsay",
                "I am not launching the heavier legacy brawl automatically. That one needs a clear budget.",
                "com",
            )
            runtime.side_notes.append("-IDAT deflate heavy probe found no improved candidate.")
            runtime.side_notes.append("-IDAT legacy bruteforce skipped: automatic heavy probing is disabled.")
            return None

    if probe.best is None:
        runtime.candy(
            "Cowsay",
            "I am not launching the heavy probe automatically. That one needs a clear budget.",
            "com",
        )
        runtime.side_notes.append("-IDAT deflate probe found no improved candidate.")
        runtime.side_notes.append("-IDAT heavy probe skipped: automatic heavy probing is disabled.")
        return None

    candidate = probe.best
    candidates = tuple(probe.chain) or (candidate,)
    runtime.side_notes.extend(idat_bruteforce.candidate_summary_lines(probe))
    if len(candidates) == 1:
        runtime.candy(
            "Cowsay",
            "I found one byte that makes the IDAT stream behave better. Still an hypothesis, not a victory parade.",
            "good",
        )
        runtime.candy(
            "Cowsay",
            "Patch: IDAT stream offset 0x%x, byte %02x -> %02x."
            % (candidate.stream_offset, candidate.old_byte, candidate.new_byte),
            "com",
        )
    else:
        runtime.candy(
            "Cowsay",
            "I found %s byte changes that keep moving the IDAT stream forward. This is a trail, not a solved case."
            % len(candidates),
            "good",
        )
        for index, candidate_patch in enumerate(candidates, start=1):
            runtime.candy(
                "Cowsay",
                "Patch %s: IDAT stream offset 0x%x, byte %02x -> %02x."
                % (
                    index,
                    candidate_patch.stream_offset,
                    candidate_patch.old_byte,
                    candidate_patch.new_byte,
                ),
                "com",
            )
    summary = "\n".join(
        (
            "-Repair hypothesis tried: targeted IDAT deflate strategy queue.",
            idat_bruteforce.probe_summary_line(probe),
            *idat_bruteforce.candidate_summary_lines(probe),
            idat_stream_diagnosis_note(candidate.after),
        )
    )
    return True, runtime.write_clone(candidate.data, summary)


def validate_idat_crc_only_patch(
    runtime: WrongCrcRuntime,
    tools: relics.WrongCrcTools,
) -> WrongCrcPatchValidation:
    if tools.chunk != b"IDAT":
        return WrongCrcPatchValidation(True)

    try:
        patched_hex = writer.replace_hex_range(
            runtime.data_hex,
            str(tools.replacement_crc),
            int(tools.start),
            int(tools.end),
        )
        patched_data = bytes.fromhex(patched_hex)
    except Exception as exc:
        return WrongCrcPatchValidation(False, "I could not even build the CRC-only candidate: %s" % exc)

    analysis = idat.analyze_idat_stream(patched_data)
    if analysis.complete:
        return WrongCrcPatchValidation(True)

    reason = analysis.reason or analysis.zlib_error or analysis.status or "IDAT stream is still not a complete image"
    return WrongCrcPatchValidation(False, reason, analysis)


def save_or_defer_wrong_crc(
    runtime: WrongCrcRuntime,
    tools: relics.WrongCrcTools,
    finding: Any = None,
) -> tuple[bool, Any]:
    validation = validate_idat_crc_only_patch(runtime, tools)
    if validation.can_save:
        return save_wrong_crc(runtime, tools)

    if tools.chunk == b"IDAT":
        runtime.set_idat_crc_patch_failed(True)
        runtime.set_idat_crc_patch_failed_finding(finding)
        runtime.remember_deferred_idat_crc_route(finding, tools)
        remember_deferred_idat_crc_note(runtime, validation)

    runtime.candy(
        "Cowsay",
        "I tested the cheap CRC patch in my head. It still breaks: %s" % validation.reason,
        "bad",
    )
    runtime.candy(
        "Cowsay",
        "So i'm not writing a pretend fixed clone for that one. Let's keep digging.",
        "com",
    )
    return defer_wrong_crc(runtime, tools)


def preflight_idat_crc_only_patch(
    runtime: WrongCrcRuntime,
    tools: relics.WrongCrcTools,
    finding: Any,
) -> tuple[bool, Any] | None:
    if tools.chunk != b"IDAT":
        return None

    try:
        current_analysis = idat.analyze_idat_stream(bytes.fromhex(runtime.data_hex))
    except Exception:
        current_analysis = None
    if current_analysis is not None:
        probe_result = try_idat_deflate_bruteforce(runtime, current_analysis)
        if probe_result is not None:
            return probe_result

    validation = validate_idat_crc_only_patch(runtime, tools)
    if validation.can_save:
        return None

    runtime.set_idat_crc_patch_failed(True)
    runtime.set_idat_crc_patch_failed_finding(finding)
    runtime.remember_deferred_idat_crc_route(finding, tools)
    remember_deferred_idat_crc_note(runtime, validation)
    runtime.candy(
        "Cowsay",
        "I tested the cheap CRC patch in my head. It still breaks: %s" % validation.reason,
        "bad",
    )
    runtime.candy(
        "Cowsay",
        "So i'm not asking you to bless a fake fix. I will keep that CRC for later.",
        "com",
    )
    return defer_wrong_crc(runtime, tools)


def wrong_crc_visible_other_errors(runtime: WrongCrcRuntime, finding: Any) -> tuple[Any, ...]:
    return tuple(
        pandora_finding
        for pandora_finding in runtime.pandora_box
        if pandora_finding != finding
    )


def ask_easy_wrong_crc_message(other_error_count: int) -> str:
    if other_error_count <= 0:
        return (
            "This looks like an easy fix since there are no real errors beside "
            "the Crc issue.Do you wish to try to fix it ?"
        )

    plural = "s" if other_error_count > 1 else ""
    return (
        "The Crc itself is fixable, but i can also see %s other suspicious "
        "thing%s nearby. I can patch that Crc now, but don't call it clean yet. "
        "Do you wish to try it ?"
        % (other_error_count, plural)
    )


def final_wrong_crc_question(
    runtime: WrongCrcRuntime,
    finding: Any,
    chkd: str,
    tools: relics.WrongCrcTools,
) -> tuple[bool, Any]:
    uniqh = relics.question_hash(runtime.pandora_box, finding, chkd)
    answer = runtime.question(id=finding, idhash=uniqh)
    if runtime.last_question_status() in ("duplicate_flipped", "route_exhausted"):
        return defer_wrong_crc(runtime, tools)
    if answer is False:
        return save_or_defer_wrong_crc(runtime, tools, finding)
    return defer_wrong_crc(runtime, tools)


def apply_wrong_crc(
    runtime: WrongCrcRuntime,
    decision: fixit_felix.WrongCrcDecision,
    chkd: str,
    tools: relics.WrongCrcTools | None,
) -> tuple[bool, Any]:
    emit_wrong_crc_critical(runtime, decision.finding)

    if decision.action == "already_in_cornucopia":
        if runtime.debug is True and runtime.pause_debug is True:
            runtime.emit("-Cornucopia is True")
        return False, None

    if tools is None:
        raise ValueError("FixItFelix wrong-CRC action needs CRC tools: %s" % decision.action)

    if decision.action == "ask_easy_crc_fix":
        if tools.chunk == b"IDAT" and runtime.is_deferred_idat_crc_route(decision.finding, tools):
            runtime.set_idat_crc_patch_failed(True)
            runtime.set_idat_crc_patch_failed_finding(decision.finding)
            runtime.candy(
                "Cowsay",
                "Oh, I know that one already... I hoped it would have gone away by itself. Anyway, let's keep going.",
                "com",
            )
            return defer_wrong_crc(runtime, tools)

        preflight = preflight_idat_crc_only_patch(runtime, tools, decision.finding)
        if preflight is not None:
            return preflight

        runtime.candy("Cowsay", "Crc checksum is not valid !!!", "bad")
        visible_other_errors = wrong_crc_visible_other_errors(runtime, decision.finding)
        runtime.candy(
            "Cowsay",
            ask_easy_wrong_crc_message(len(visible_other_errors)),
            "com",
        )
        uniqh = relics.question_hash(runtime.pandora_box, decision.finding, chkd)
        answer = runtime.question(id=decision.finding, idhash=uniqh)
        if answer is True:
            return save_or_defer_wrong_crc(runtime, tools, decision.finding)

        if runtime.last_question_status() in ("duplicate_flipped", "route_exhausted"):
            return defer_wrong_crc(runtime, tools)

        runtime.set_skip_bad_crc(None)
        return final_wrong_crc_question(runtime, decision.finding, chkd, tools)

    if decision.action == "ask_other_errors_first":
        visible_other_error_count = len(wrong_crc_visible_other_errors(runtime, decision.finding))
        other_error_count = visible_other_error_count or decision.other_error_count
        plural = "s" if other_error_count > 1 else ""
        runtime.candy(
            "Cowsay",
            "Crc checksum is not valid and there are %s other error%s !"
            % (other_error_count, plural),
            "bad",
        )
        runtime.candy(
            "Cowsay",
            "We may want to fix them first before jumping on that Crc what do you think ?",
            "com",
        )
        return final_wrong_crc_question(runtime, decision.finding, chkd, tools)

    raise ValueError("Unknown FixItFelix wrong-CRC action: %s" % decision.action)


def _idat_chain_summary(analysis: idat_chain.IdatChainAnalysis) -> str:
    lines = ["-Repair hypothesis tried: IDAT chain header repair."]
    lines.extend(idat_chain.patch_summary_lines(analysis.patches))
    return "\n".join(lines)


def _explain_idat_stream_after_header_repair(
    runtime: Any,
    analysis: idat.IdatStreamAnalysis,
    *,
    already_aligned: bool = False,
) -> None:
    runtime.side_notes.append(idat_stream_diagnosis_note(analysis))
    if analysis.complete:
        if already_aligned:
            runtime.candy("Cowsay", "The IDAT road signs already line up and the compressed stream answers cleanly.", "good")
        else:
            runtime.candy("Cowsay", "The IDAT road signs line up and the compressed stream answers cleanly.", "good")
        return

    reason = analysis.reason or analysis.zlib_error or analysis.status
    if already_aligned:
        runtime.candy("Cowsay", "The IDAT road signs already line up to IEND.", "good")
    else:
        runtime.candy("Cowsay", "The IDAT road signs line up now.", "good")
    runtime.candy(
        "Cowsay",
        "But the compressed stream is still broken: %s" % reason,
        "bad",
    )
    runtime.candy(
        "Cowsay",
        "So this clone is a map correction, not the final picture yet.",
        "com",
    )


def _block_isolated_idat_repairs_after_chain_diagnostic(
    runtime: Any,
    analysis: idat.IdatStreamAnalysis,
) -> tuple[bool, Any]:
    probe_result = try_idat_deflate_bruteforce(runtime, analysis)
    if probe_result is not None:
        return probe_result

    _explain_idat_stream_after_header_repair(runtime, analysis, already_aligned=True)
    runtime.candy(
        "Cowsay",
        "So I am not adding IEND, renaming chunks, or polishing CRC labels on this pass.",
        "com",
    )
    return False, None


def try_idat_chain_header_repair(
    runtime: Any,
    *,
    block_if_aligned_bad_stream: bool = False,
) -> tuple[bool, Any] | None:
    try:
        data = bytes.fromhex(runtime.data_hex)
    except Exception:
        return None

    analysis = idat_chain.analyze_idat_chain_headers(data)
    if block_if_aligned_bad_stream and analysis.status == "ok":
        stream_analysis = idat.analyze_idat_stream(data)
        if not stream_analysis.complete:
            return _block_isolated_idat_repairs_after_chain_diagnostic(runtime, stream_analysis)
        return None

    if not analysis.repairable:
        return None

    runtime.candy(
        "Cowsay",
        "I found a regular IDAT convoy, but some road signs are bent.",
        "good",
    )
    runtime.candy(
        "Cowsay",
        "I am fixing the IDAT headers as a batch. CRCs can complain after that.",
        "com",
    )
    summary = _idat_chain_summary(analysis)
    runtime.side_notes.extend(summary.splitlines())
    stream_analysis = idat.analyze_idat_stream(analysis.fixed_data)
    _explain_idat_stream_after_header_repair(runtime, stream_analysis)
    summary = "\n".join([summary, idat_stream_diagnosis_note(stream_analysis)])
    return True, runtime.write_clone(analysis.fixed_data, summary)


def wrong_chunk_name_precedes_first_parsed_idat(data_hex: str, tools: relics.WrongChunkNameTools) -> bool:
    try:
        data = bytes.fromhex(data_hex)
        chunks = tuple(png.iter_chunks(data))
    except Exception:
        return False

    first_idat = next((chunk for chunk in chunks if chunk.chunk_type == b"IDAT"), None)
    if first_idat is None:
        return False

    try:
        chunk_type_offset = int(tools.chunk_type_offset)
    except (TypeError, ValueError):
        return False

    return chunk_type_offset < first_idat.offset + 4


def emit_wrong_chunk_name_critical(runtime: WrongChunkNameRuntime, finding: Any) -> None:
    runtime.emit("\n-\033[1;31;49mCriticalHit\033[m: %s" % finding)


def describe_wrong_chunk_name(
    runtime: WrongChunkNameRuntime,
    decision: fixit_felix.WrongChunkNameDecision,
) -> None:
    if runtime.bad_ancillary() is True:
        runtime.candy(
            "Cowsay",
            "I don't know that chunk but it has passed Ancillary nomenclature check ..",
            "com",
        )
        if decision.bad_crc is True:
            runtime.candy(
                "Cowsay",
                "But since Crc is not valid there is more chances that this Chunkname is corrupt.",
                "bad",
            )
        else:
            runtime.candy(
                "Cowsay",
                "and since Crc is valid too this may be a legit private chunk..",
                "com",
            )
    else:
        runtime.candy(
            "Cowsay",
            "I don't know that chunk and it has failed Ancillary nomenclature check ..",
            "bad",
        )
        if decision.bad_crc is True:
            runtime.candy(
                "Cowsay",
                "And since Crc is wrong this definitely looks like a corrupted Chunkname .",
                "bad",
            )
        else:
            runtime.candy(
                "Cowsay",
                "But the CRC is still Valid !!! Usually this means that it has been made on purpose by someone...",
                "bad",
            )
            runtime.candy(
                "Cowsay",
                "Or....SOMEHTING !!",
                "com",
            )


def ask_wrong_chunk_name_bruteforce(
    runtime: WrongChunkNameRuntime,
    decision: fixit_felix.WrongChunkNameDecision,
    chkd: str,
    tools: relics.WrongChunkNameTools,
) -> tuple[bool, Any]:
    route_action = "bruteforce"
    if runtime.is_wrong_chunk_name_route_tried(decision.finding, chkd, tools, route_action):
        _emit_wrong_chunk_name_deja_vu(runtime, tools)
        runtime.set_skip_bad_current_name(True)
        return False, None

    if decision.bad_crc is False:
        runtime.candy(
            "Cowsay",
            "Do you want me to try to fix this regardless of CRC's validity ?",
            "com",
        )
    else:
        runtime.candy(
            "Cowsay",
            "How about im taking care of the rest ?",
            "com",
        )
    uniqh = relics.question_hash(runtime.pandora_box, decision.finding, chkd)
    answer = runtime.question(id=decision.finding, idhash=uniqh)
    if answer is True:
        runtime.remember_wrong_chunk_name_route(decision.finding, chkd, tools, route_action)
        _remember_wrong_chunk_name_note(runtime, tools, "tried")
        runtime.candy(
            "Cowsay",
            "I am treating this chunk-name repair as a hypothesis, not a victory lap.",
            "com",
        )
        return True, runtime.brute_chunk(
            tools.chunk_type,
            tools.previous_chunk,
            tools.chunk_length,
            str(decision.finding),
        )

    runtime.remember_wrong_chunk_name_route(decision.finding, chkd, tools, route_action)
    _remember_wrong_chunk_name_note(
        runtime,
        tools,
        "deferred",
        "user declined this chunk-name recovery route",
    )
    runtime.set_skip_bad_current_name(True)
    return False, None


def apply_wrong_chunk_name(
    runtime: WrongChunkNameRuntime,
    decision: fixit_felix.WrongChunkNameDecision,
    chkd: str,
    tools: relics.WrongChunkNameTools | None,
) -> tuple[bool, Any]:
    if decision.action == "save_existing_solution":
        runtime.emit(
            "\n-\033[1;32;49mSolved\033[m: %s"
            % relics.tool_value(runtime.cornucopia[decision.finding], chkd, 4)
        )
        return True, runtime.save_clone(
            relics.tool_value(runtime.cornucopia[decision.finding], chkd, 0),
            relics.tool_value(runtime.cornucopia[decision.finding], chkd, 1),
            relics.tool_value(runtime.cornucopia[decision.finding], chkd, 2),
            relics.tool_value(runtime.cornucopia[decision.finding], chkd, 3),
        )

    if tools is None:
        raise ValueError("FixItFelix wrong-chunk-name action needs chunk tools: %s" % decision.action)

    emit_wrong_chunk_name_critical(runtime, decision.finding)
    block_after_alignment = not wrong_chunk_name_precedes_first_parsed_idat(runtime.data_hex, tools)
    idat_chain_repair = try_idat_chain_header_repair(
        runtime,
        block_if_aligned_bad_stream=block_after_alignment,
    )
    if idat_chain_repair is not None:
        return idat_chain_repair

    runtime.ancillary(tools.chunk_type)
    describe_wrong_chunk_name(runtime, decision)

    if decision.action == "ask_length_probe":
        route_action = "length_probe"
        if runtime.is_wrong_chunk_name_route_tried(decision.finding, chkd, tools, route_action):
            _emit_wrong_chunk_name_deja_vu(runtime, tools)
            runtime.set_skip_bad_next_name(True)
            return ask_wrong_chunk_name_bruteforce(runtime, decision, chkd, tools)

        runtime.candy(
            "Cowsay",
            "By the way IDAT chunk's length is different from the one usually used for some reason..",
            "com",
        )
        runtime.candy(
            "Cowsay",
            "May i suggest to start by checking if this a length problem ?",
            "good",
        )
        uniqh = relics.question_hash(runtime.pandora_box, decision.finding, chkd)
        answer = runtime.question(id=decision.finding, idhash=uniqh)
        if answer is True:
            runtime.remember_wrong_chunk_name_route(decision.finding, chkd, tools, route_action)
            _remember_wrong_chunk_name_note(runtime, tools, "tried")
            return True, runtime.nearby_chunk(
                tools.chunk_type,
                tools.chunk_length,
                tools.chunk_type_offset,
                False,
                decision.finding,
            )

        runtime.remember_wrong_chunk_name_route(decision.finding, chkd, tools, route_action)
        _remember_wrong_chunk_name_note(
            runtime,
            tools,
            "deferred",
            "length probe was declined",
        )
        runtime.set_skip_bad_next_name(True)
        return ask_wrong_chunk_name_bruteforce(runtime, decision, chkd, tools)

    if decision.action == "ask_bruteforce":
        return ask_wrong_chunk_name_bruteforce(runtime, decision, chkd, tools)

    raise ValueError("Unknown FixItFelix wrong-chunk-name action: %s" % decision.action)


def emit_no_next_critical(runtime: NoNextChunkRuntime, finding: Any) -> None:
    runtime.emit("\n-\033[1;31;49mCriticalHit\033[m: %s" % finding)


def discard_no_next_false_positive(runtime: NoNextChunkRuntime) -> None:
    for pandora_key in list(runtime.pandora_box):
        if "No NextChunk" in str(pandora_key):
            runtime.candy(
                "Cowsay",
                "That one is a false positive im removing it ..",
                "good",
            )
            relics.discard_pandora_error(runtime.pandora_box, pandora_key)
            runtime.side_notes.append("-Found False-Positive :[Error:-No NextChunk].")
            runtime.set_skip_bad_no_next_chunk(True)
            break


def no_next_missplaced_tools(runtime: NoNextChunkRuntime) -> list[Any] | None:
    for pandora_key in runtime.pandora_box:
        if "Missplaced" in str(pandora_key) and runtime.eof() is True:
            return list(runtime.pandora_box[pandora_key].values())
    return None


def mark_no_next_iend_reached(runtime: NoNextChunkRuntime) -> None:
    runtime.check_chunk_order(b"IEND", "Critical")
    runtime.candy("Cowsay", "We have reached the end of file.", "good")
    runtime.set_eof(True)
    runtime.side_notes.append("-Reached the end of file.")


def apply_no_next_false_positive_iend(
    runtime: NoNextChunkRuntime,
    decision: fixit_felix.NoNextFalsePositiveIendDecision,
) -> tuple[bool, Any]:
    if decision.action in ("libpng_check", "the_good_place", "continue"):
        mark_no_next_iend_reached(runtime)

        if decision.action == "libpng_check":
            runtime.candy("Cowsay", "Ok let's feed the Kraken now..", "com")
            return True, runtime.libpng_check(runtime.sample)

        if decision.action == "the_good_place":
            rustine = no_next_missplaced_tools(runtime)
            if rustine is not None and len(rustine) >= 3:
                runtime.candy("Cowsay", "But the fun isnt over yet..", "com")
                return True, runtime.the_good_place(rustine[0], rustine[1], rustine[2])
            runtime.candy("Cowsay", "Ok let's feed the Kraken now..", "com")
            return True, runtime.libpng_check(runtime.sample)

        return False, None

    if decision.action == "write_clean_iend_cut":
        cleancut = bytes.fromhex(decision.cut_hex)
        runtime.side_notes.append("-FixitFelix:Removing extra bytes after IEND chunk.")
        return True, runtime.write_clone(cleancut, "-Saved")

    if decision.action == "end_not_regular_iend":
        runtime.emit(runtime.candy("Color", "yellow", "Not ending with regular IEND\n-ToDo"))
        runtime.side_notes.append("-Not ending with regular IEND Chunk")
        runtime.emit("-Exceptation: %s" % (str(fixit_felix.GOOD_IEND_HEX)))
        runtime.emit("-Reality: %s" % (str(runtime.data_hex[-len(fixit_felix.GOOD_IEND_HEX) :])))
        runtime.the_end()
        return False, None

    raise ValueError("Unknown no-next false-positive IEND action: %s" % decision.action)


def handle_no_next_false_positive_iend(
    runtime: NoNextChunkRuntime,
) -> tuple[bool, Any]:
    discard_no_next_false_positive(runtime)
    runtime.chunk_story(
        "add",
        b"IEND",
        runtime.cl_offset,
        runtime.crc_offset + 8,
        int(runtime.original_chunk_length_hex, 16),
    )

    false_positive_decision = fixit_felix.no_next_false_positive_iend_decision(
        runtime.data_hex,
        bad_missplaced=runtime.bad_missplaced,
        has_missplaced_finding=any("Missplaced" in str(pandora_key) for pandora_key in runtime.pandora_box),
    )
    return apply_no_next_false_positive_iend(runtime, false_positive_decision)


def handle_no_next_wrong_iend_length(runtime: NoNextChunkRuntime) -> tuple[bool, None]:
    runtime.emit(
        "-%s length for IEND %s "
        % (runtime.candy("Color", "red", "Wrong"), runtime.candy("Chunky", "bad"))
    )
    runtime.emit(runtime.candy("Color", "yellow", "\n-ToDo"))
    runtime.side_notes.append("-Wrong length for IEND")
    runtime.the_end()
    return False, None


def print_no_next_append_debug(runtime: NoNextChunkRuntime) -> None:
    if runtime.debug:
        runtime.debug_print("CrcoffI:", runtime.crc_offset)
        runtime.debug_print("Raw_Crc:", runtime.raw_crc)
        runtime.debug_print("DATAX[crc]:", runtime.data_hex[runtime.crc_offset : runtime.crc_offset + 8])
        if runtime.pause_debug is True or runtime.pause_error is True:
            runtime.pause("Pause Debug")


def report_no_next_exceeding(runtime: NoNextChunkRuntime, exceeding: str) -> None:
    if len(exceeding) <= 0:
        return

    if int(len(exceeding) / 2) == 0:
        runtime.candy("Cowsay", "Ah there is one bit left after the Crc ..", "com")
    else:
        runtime.candy("Cowsay", "Ah there are %s bytes left after the Crc .." % (str(int(len(exceeding) / 2))), "com")
    runtime.side_notes.append("-Extra bits detected:%s" % str(exceeding))


def apply_no_next_append_iend(
    runtime: NoNextChunkRuntime,
    decision: fixit_felix.NoNextAppendIendDecision,
    finding: Any,
) -> tuple[bool, Any]:
    exceeding = decision.exceeding

    if decision.action == "end_iend_inside_exceeding":
        runtime.candy("Cowsay", "And it seems that the IEND chunk is inside it  ..", "com")
        runtime.debug_print("-iendsample:", fixit_felix.GOOD_IEND_HEX)
        runtime.debug_print("-exceeding:", exceeding)
        runtime.side_notes.append("-Part or full IEND chunk detected:%s" % (str(exceeding)))
        runtime.emit(runtime.candy("Color", "yellow", "\n-ToDo"))
        runtime.the_end()
        return False, None

    if decision.action == "dummy_at_crc_tail":
        if len(exceeding) > len(fixit_felix.GOOD_IEND_HEX):
            runtime.candy("Cowsay", "But i don't know what to do with those bytes  ..", "com")
            runtime.candy("Cowsay", "So..Im just going to append an IEND chunk there for the moment ..", "com")
        else:
            runtime.candy("Cowsay", "It doesn't looks like and IEND chunk ..", "bad")
            runtime.candy("Cowsay", "And i don't know what to do with those bytes  ..", "com")
            runtime.candy("Cowsay", "So..Im just going to append an IEND chunk there for the moment ..", "com")
        runtime.debug_print("-exceeding:", exceeding)
        return True, runtime.dummy_chunk(
            b"IEND",
            runtime.crc_offset + 8,
            runtime.crc_offset + 8,
            runtime.crc_offset + 8,
            str(finding),
        )

    if decision.action == "dummy_at_eof":
        if exceeding:
            runtime.candy("Cowsay", "And it seems that it matches with some part of IEND chunk ..", "com")
            runtime.candy("Cowsay", "I don't think this is a coincidence.", "good")
            runtime.side_notes.append("-Part or full IEND chunk detected:%s" % (str(exceeding)))
            runtime.debug_print("-iendsample:", fixit_felix.GOOD_IEND_HEX)
            runtime.debug_print("-exceeding:", exceeding)
        return True, runtime.dummy_chunk(
            b"IEND",
            len(runtime.data_hex),
            len(runtime.data_hex),
            len(runtime.data_hex),
            str(finding),
        )

    raise ValueError("Unknown no-next append-IEND action: %s" % decision.action)


def handle_no_next_append_missing_iend(
    runtime: NoNextChunkRuntime,
    finding: Any,
) -> tuple[bool, Any]:
    idat_chain_repair = try_idat_chain_header_repair(runtime, block_if_aligned_bad_stream=True)
    if idat_chain_repair is not None:
        return idat_chain_repair

    later_iend = runtime.nearby_found_later_iend()
    if later_iend:
        runtime.candy("Cowsay", "I already saw an IEND later in this file.", "good")
        runtime.candy(
            "Cowsay",
            "So I am not adding another one. That would be a new crime scene, not a fix.",
            "bad",
        )
        runtime.side_notes.append(
            "-Skipped adding IEND chunk: NearbyChunk already found an IEND later."
        )
        runtime.set_skip_bad_no_next_chunk(True)
        return False, None

    runtime.candy("Cowsay", "Well it seems that i need to add that IEND chunk myself after all ..", "bad")
    print_no_next_append_debug(runtime)

    append_decision = fixit_felix.no_next_append_iend_decision(
        runtime.data_hex,
        crc_offset=runtime.crc_offset,
    )
    report_no_next_exceeding(runtime, append_decision.exceeding)
    return apply_no_next_append_iend(runtime, append_decision, finding)


def handle_no_next_ask_length_probe(
    runtime: NoNextChunkRuntime,
    finding: Any,
    chkd: str,
    tools: relics.NoNextChunkTools,
) -> tuple[bool, Any]:
    runtime.emit(
        "\n-End of File Reached but IEND Chunk is %s ! %s"
        % (runtime.candy("Color", "red", " MISSING! "), runtime.candy("Chunky", "bad"))
    )
    runtime.side_notes.append("-End of File Reached but IEND Chunk is missing")
    runtime.candy(
        "Cowsay",
        "A length error maybe ? Do you want me to have a look ?",
        "com",
    )
    uniqh = relics.question_hash(runtime.pandora_box, finding, chkd)
    answer = runtime.question(id=finding, idhash=uniqh)
    if answer is True:
        return True, runtime.nearby_chunk(
            tools.chunk_type,
            tools.chunk_length,
            tools.previous_chunk,
            False,
            finding,
        )

    runtime.the_end()
    return False, None


def apply_no_next_chunk(
    runtime: NoNextChunkRuntime,
    decision: fixit_felix.NoNextChunkDecision,
    finding: Any,
    chkd: str,
    tools: relics.NoNextChunkTools | None,
) -> tuple[bool, Any]:
    emit_no_next_critical(runtime, finding)

    if tools is None:
        raise ValueError("FixItFelix no-next-chunk action needs chunk tools: %s" % decision.action)

    if decision.action == "false_positive_iend":
        return handle_no_next_false_positive_iend(runtime)

    if decision.action == "wrong_iend_length":
        return handle_no_next_wrong_iend_length(runtime)

    if decision.action == "append_missing_iend":
        return handle_no_next_append_missing_iend(runtime, finding)

    if decision.action == "ask_length_probe":
        return handle_no_next_ask_length_probe(runtime, finding, chkd, tools)

    raise ValueError("Unknown FixItFelix no-next-chunk action: %s" % decision.action)


def apply_libpng_error(
    runtime: LibpngErrorRuntime,
    decision: fixit_felix.LibpngErrorDecision,
    chkd: str,
) -> Any:
    emit_libpng_critical(runtime, decision.finding)

    if decision.action == "not_enough_image_data":
        runtime.candy("Cowsay", "Well this is as far as i could get for now. ", "bad")
        runtime.candy("Cowsay", "At least i was able to get some pixels out of it ..", "com")
        runtime.emit(runtime.candy("Color", "yellow", "\n-ToDo"))
        runtime.the_end()
        return None

    if decision.action == "ask_relics":
        runtime.candy(
            "Cowsay",
            "The All Mighty Libpng has spoken ...",
            "com",
        )
        runtime.candy("Cowsay", "Damned!! We were so close !", "bad")
        runtime.candy(
            "Cowsay",
            "We should go some step back before to see if we can do something else..",
            "com",
        )
        runtime.candy(
            "Cowsay",
            "Are you agree ? Otherwise Chunklate is going to exit",
            "com",
        )
        uniqh = relics.question_hash(runtime.pandora_box, decision.finding, chkd)
        answer = runtime.question(id=decision.finding, idhash=uniqh)
        if answer is True:
            runtime.set_skip_bad_libpng(True)
            return True, runtime.run_relics(str(decision.finding))

        runtime.candy("Cowsay", "See You Space Cowboy....", "good")
        runtime.the_end()
        return None

    if decision.action == "skip":
        return False, None

    if decision.action == "save_existing_solution":
        runtime.emit(
            "\n-\033[1;32;49mSolved\033[m: %s"
            % relics.tool_value(runtime.cornucopia[decision.finding], chkd, 3)
        )
        runtime.save_clone(
            relics.tool_value(runtime.cornucopia[decision.finding], chkd, 0),
            relics.tool_value(runtime.cornucopia[decision.finding], chkd, 1),
            relics.tool_value(runtime.cornucopia[decision.finding], chkd, 2),
            relics.tool_value(runtime.cornucopia[decision.finding], chkd, 3),
        )
        return True, runtime.groundhog_day(runtime.sample)

    raise ValueError("Unknown FixItFelix libpng action: %s" % decision.action)


def finding_handlers(callbacks: LegacyFixItFelixHandlers) -> dict[str, fixit_felix.FindingWorkItemHandler]:
    return {
        "wrong_crc": lambda work_item, chkd, pandora_box_len, chunk: callbacks.wrong_crc(
            work_item.finding,
            chkd,
            pandora_box_len,
        ),
        "libpng_error": lambda work_item, chkd, pandora_box_len, chunk: callbacks.libpng_error(
            work_item.finding,
            chkd,
        ),
        "wrong_chunk_name": lambda work_item, chkd, pandora_box_len, chunk: callbacks.wrong_chunk_name(
            work_item.finding,
            chkd,
        ),
        "no_next_chunk": lambda work_item, chkd, pandora_box_len, chunk: callbacks.no_next_chunk(
            work_item.finding,
            chkd,
            chunk,
        ),
        "gama_zero": lambda work_item, chkd, pandora_box_len, chunk: callbacks.gama_zero(
            work_item.finding,
        ),
        "critical_miss": lambda work_item, chkd, pandora_box_len, chunk: callbacks.critical_miss(
            work_item.finding,
        ),
    }


def build_legacy_fixit_felix_handlers_from_namespace(namespace: dict[str, Any]) -> LegacyFixItFelixHandlers:
    return LegacyFixItFelixHandlers(
        wrong_crc=namespace["FixItFelix_Wrong_Crc"],
        libpng_error=namespace["FixItFelix_Libpng_Error"],
        wrong_chunk_name=namespace["FixItFelix_Wrong_Chunk_Name"],
        no_next_chunk=namespace["FixItFelix_No_NextChunk"],
        gama_zero=namespace["FixItFelix_Gama_Zero"],
        critical_miss=namespace["FixItFelix_Critical_Miss"],
    )


def apply_finding_work_item(
    callbacks: LegacyFixItFelixHandlers,
    work_item: fixit_felix.FixItFelixWorkItem,
    chkd: str,
    pandora_box_len: int,
    chunk: Any,
) -> tuple[bool, Any]:
    return fixit_felix.dispatch_finding_work_item(
        finding_handlers(callbacks),
        work_item,
        chkd,
        pandora_box_len,
        chunk,
    )


def runtime(
    *,
    try_automatic_repair: Callable[[fixit_felix.AutomaticRepairHandler], Any],
    callbacks: LegacyFixItFelixHandlers,
) -> fixit_felix.FixItFelixRuntime:
    return fixit_felix.FixItFelixRuntime(
        try_automatic_repair=try_automatic_repair,
        apply_finding_work_item=lambda work_item, chkd, pandora_box_len, chunk: apply_finding_work_item(
            callbacks,
            work_item,
            chkd,
            pandora_box_len,
            chunk,
        ),
    )


def build_fixit_felix_runtime_from_namespace(namespace: dict[str, Any]) -> fixit_felix.FixItFelixRuntime:
    return runtime(
        try_automatic_repair=namespace["FixItFelix_Try_Automatic_Repair"],
        callbacks=build_legacy_fixit_felix_handlers_from_namespace(namespace),
    )


def run_fixit_felix_pipeline_from_namespace(
    namespace: dict[str, Any],
    chunk: Any,
    chkd: str,
    *,
    runner: Callable[..., fixit_felix.FixItFelixRunResult] = fixit_felix.run_repair_pipeline,
) -> fixit_felix.FixItFelixRunResult:
    if namespace["DEBUG"] is True:
        fixit_felix.emit_debug_report(
            namespace["PRINT"],
            namespace,
            namespace["PandoraBox"],
            namespace["Cornucopia"],
        )

        if namespace["PAUSEDEBUG"] is True:
            namespace["Pause"]("FixItFelix Debug Pause:")

    return runner(
        build_fixit_felix_runtime_from_namespace(namespace),
        namespace["PandoraBox"],
        skip_bad_crc=namespace["Skip_Bad_Crc"],
        bad_next_name=namespace["Bad_Next_Name"],
        chkd=chkd,
        chunk=chunk,
    )
