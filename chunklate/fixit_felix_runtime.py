from __future__ import annotations

import binascii
from dataclasses import dataclass
from pathlib import Path
import random
from typing import Any
from typing import Callable

from . import bruteforce
from . import bruteforce_runtime
from . import fixit_felix
from . import idat
from . import idat_bruteforce
from . import idat_chain
from . import messages
from . import png
from . import repair_routes
from . import relics
from . import specs
from . import writer


HEPHAESTUS_INITIAL_BRUTE_LEVEL = 1


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
    candy: Callable[..., Any]
    write_clone: Callable[[Any, str], Any]
    question: Callable[..., Any] | None = None
    preview_repair_image: Callable[..., Any] | None = None
    tk_manual_plte: Callable[..., Any] | None = None
    smash_brute_brawl: Callable[..., Any] | None = None
    data_hex: str = ""
    pandora_box: Any = None
    get_spec: Callable[..., Any] | None = None
    product: Callable[..., Any] | None = None
    loadingbar: Callable[..., Any] | None = None
    minibar: Callable[..., Any] | None = None
    file_origin: Any = ""
    interactive: bool = False


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
    run_relics: Callable[[str], Any]
    the_good_place: Callable[[Any, Any, Any], Any]
    write_clone: Callable[[Any, str], Any]
    the_end: Callable[[], Any]
    pause: Callable[[str], Any]
    debug_print: Callable[..., Any]
    dummy_chunk: Callable[..., Any]
    nearby_chunk: Callable[..., Any]
    nearby_found_later_iend: Callable[[], Any]
    chunks_history: tuple[Any, ...] = ()
    loadingbar: Callable[..., Any] | None = None
    minibar: Callable[..., Any] | None = None
    has_deferred_linefeed_repair: Callable[[], bool] = lambda: False
    apply_deferred_linefeed_repair: Callable[[], Any] | None = None


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
    try_idat_decision_gate: Callable[[Any], Any] | None = None


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
    def try_idat_decision_gate(finding: Any) -> Any:
        try:
            data = bytes.fromhex(namespace["DATAX"])
        except (KeyError, TypeError, ValueError):
            return None
        repair = fixit_felix.partial_idat_blackfill(data, (finding,))
        if repair is None:
            return None
        automatic_runtime = build_automatic_repair_runtime_from_namespace(namespace)
        return apply_partial_blackfill_decision(automatic_runtime, repair)

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
        try_idat_decision_gate=try_idat_decision_gate,
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
        run_relics=namespace["Relics"],
        the_good_place=namespace["TheGoodPlace"],
        write_clone=namespace["WriteClone"],
        the_end=namespace["TheEnd"],
        pause=namespace["Pause"],
        debug_print=namespace.get("DebugPrint", print),
        dummy_chunk=namespace["DummyChunk"],
        nearby_chunk=namespace["NearbyChunk"],
        nearby_found_later_iend=lambda: namespace.get("NEARBY_FOUND_LATER_IEND"),
        chunks_history=tuple(namespace.get("Chunks_History", ())),
        loadingbar=namespace.get("Loadingbar"),
        minibar=namespace.get("Minibar"),
        has_deferred_linefeed_repair=lambda: bool(namespace.get("DEFERRED_LINEFEED_SIGNATURE_REPAIR")),
        apply_deferred_linefeed_repair=namespace.get("Apply_Deferred_FindMagic_Repair"),
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
        candy=namespace["Candy"],
        write_clone=namespace["WriteClone"],
        question=namespace["Question"],
        preview_repair_image=namespace.get("Preview_Repair_Image"),
        tk_manual_plte=namespace.get("Tk_Manual_Plte"),
        smash_brute_brawl=namespace.get("SmashBruteBrawl"),
        data_hex=namespace["DATAX"],
        pandora_box=namespace["PandoraBox"],
        get_spec=namespace["GetSpec"],
        product=namespace["Product"],
        loadingbar=namespace.get("Loadingbar"),
        minibar=namespace.get("Minibar"),
        file_origin=namespace.get("FILE_Origin") or namespace.get("Sample") or "",
        interactive=namespace_interactive_prompts(namespace),
    )


def namespace_interactive_prompts(namespace: dict[str, Any]) -> bool:
    configured = namespace.get("INTERACTIVE_REPAIR_PROMPTS")
    if configured is not None:
        return bool(configured)

    sys_module = namespace.get("sys")
    stdin = getattr(sys_module, "stdin", None)
    stdout = getattr(sys_module, "stdout", None)
    if stdin is None or stdout is None:
        return False
    return bool(stdin.isatty() and stdout.isatty())


def _ihdr_validation_errors(repair: Any) -> tuple[str, ...]:
    strategy = str(getattr(repair, "strategy", ""))
    if "IHDR" not in strategy:
        return ()

    data = getattr(repair, "data", None)
    if not isinstance(data, bytes):
        return ("IHDR repair did not produce bytes",)

    return png.validate_png_structure(data).errors


def _first_ihdr_chunk(data: bytes) -> png.PngChunk | None:
    try:
        for chunk in png.iter_chunks(data, signature_offset=0):
            if chunk.chunk_type == b"IHDR":
                return chunk
    except png.PngFormatError:
        pass

    if not data.startswith(png.PNG_SIGNATURE):
        return None
    chunk = png.chunk_at(data, len(png.PNG_SIGNATURE))
    if chunk is not None and chunk.chunk_type == b"IHDR":
        return chunk
    return None


def _noop(*_args: Any, **_kwargs: Any) -> None:
    return None


def _ihdr_crc_progress_loader(runtime: AutomaticRepairRuntime) -> Callable[..., Any]:
    if runtime.minibar is None:
        return runtime.loadingbar or _noop

    def progress(total: int, _width: int, loop: int | None, _build: bool) -> None:
        current = 0 if loop is None else loop
        runtime.minibar(Indication="IHDR CRC %s/%s" % (current, total))

    return progress


def _ihdr_crc_bruteforce_scan(
    runtime: AutomaticRepairRuntime,
    ihdr: png.PngChunk,
) -> bruteforce_runtime.SmashBruteBrawlScanResult:
    def load_spec(request: bruteforce.BruteForceSpecRequest) -> Any:
        if runtime.get_spec is None:
            raise ValueError("IHDR brute force needs GetSpec")
        return runtime.get_spec(
            b"IHDR",
            request.mode,
            **bruteforce.spec_request_kwargs(request),
        )

    return bruteforce_runtime.run_scan(
        bruteforce_runtime.SmashBruteBrawlRuntime(
            load_spec=load_spec,
            product=runtime.product or _noop,
            loadingbar=_ihdr_crc_progress_loader(runtime),
            minibar=runtime.minibar or _noop,
            show_candidate=lambda *_args, **_kwargs: bruteforce.ViewerCandidateDecision(True),
            emit=_noop,
            pause=_noop,
            side_notes=runtime.side_notes,
        ),
        bruteforce_runtime.SmashBruteBrawlContext(
            file=runtime.file_origin or "IHDR",
            chunk_name=b"IHDR",
            chunk_length=ihdr.length,
            data_offset=ihdr.offset * 2,
            from_error="FixItFelix IHDR stored CRC brute force",
            data_hex=runtime.data_hex,
            pandora_box=runtime.pandora_box or {},
            edit_mode="Replace",
            bf_mode="Brutus",
            brute_crc=True,
            brute_length=True,
            old_crc=ihdr.crc.to_bytes(4, "big"),
        ),
    )


def try_ihdr_stored_crc_bruteforce(
    runtime: AutomaticRepairRuntime,
    repair: Any,
) -> bool | None:
    if getattr(repair, "preserved_crc", False):
        return None
    if not fixit_felix.has_finding(runtime.pandora_box or (), "IHDR", "Wrong Crc"):
        return None
    if runtime.question is None:
        return None
    if runtime.data_hex == "":
        return None

    try:
        source_data = bytes.fromhex(runtime.data_hex)
    except ValueError:
        return None

    ihdr = _first_ihdr_chunk(source_data)
    if ihdr is None or ihdr.length != 13:
        return None

    runtime.candy(
        "Cowsay",
        "IHDR is the chunk whose CRC is screaming, so I can try the old brute force first.",
        "com",
    )
    runtime.candy(
        "Cowsay",
        "I will search for header bytes that land back on the stored CRC. If that fails, I fall back to the coherent rebuilt IHDR.",
        "com",
    )
    question_id = "IHDR CRC Brute Force:-Wrong Crc b'IHDR'"
    if not runtime.question(id=question_id, idhash=("IHDR", ihdr.offset, ihdr.crc)):
        runtime.side_notes.append("-FixItFelix:IHDR stored-CRC brute force declined; using rebuilt IHDR candidate.")
        return None

    runtime.candy("Title", "SmashBruteBrawl IHDR stored CRC")
    if runtime.minibar is not None:
        runtime.minibar(Indication="IHDR CRC brute force: stored CRC target")
    try:
        scan = _ihdr_crc_bruteforce_scan(runtime, ihdr)
    except Exception as exc:
        runtime.candy(
            "Cowsay",
            "The IHDR stored-CRC brute force tripped before it could finish: %s" % exc,
            "bad",
        )
        runtime.candy(
            "Cowsay",
            "I am falling back to the rebuilt IHDR instead of turning that crash into a clone.",
            "com",
        )
        runtime.side_notes.append(
            "-FixItFelix:IHDR stored-CRC brute force failed before completion: %s." % exc
        )
        return None

    if not scan.state.bingo:
        runtime.candy(
            "Cowsay",
            "The IHDR brute force did not hit the stored CRC with a usable header. I am falling back to the rebuilt one.",
            "bad",
        )
        runtime.side_notes.append("-FixItFelix:IHDR stored-CRC brute force found no candidate.")
        return None

    validation = png.validate_png_structure(scan.png_bytes)
    if not validation.ok:
        runtime.candy(
            "Cowsay",
            "I did hit the stored CRC, but the resulting PNG is still structurally wrong: %s"
            % "; ".join(validation.errors),
            "bad",
        )
        runtime.candy(
            "Cowsay",
            "CRC proof without a valid PNG is not enough. I am falling back to the rebuilt IHDR.",
            "com",
        )
        runtime.side_notes.append(
            "-FixItFelix:IHDR stored-CRC brute force rejected: %s."
            % "; ".join(validation.errors)
        )
        return None

    summary = "\n".join(
        (
            "-FixItFelix:IHDR stored-CRC brute force recovered a structurally valid PNG.",
            "-FixItFelix:Original IHDR CRC target: 0x%08x." % ihdr.crc,
        )
    )
    runtime.side_notes.append("-FixItFelix:IHDR stored-CRC brute force succeeded.")
    runtime.candy(
        "Cowsay",
        "Good. The brute force found an IHDR that matches the stored CRC and still parses as a PNG.",
        "good",
    )
    runtime.write_clone(scan.png_bytes.hex(), summary)
    return True


def _has_ihdr_crc_finding(runtime: AutomaticRepairRuntime) -> bool:
    return fixit_felix.has_finding(runtime.pandora_box or (), "IHDR", "Wrong Crc")


def _ihdr_repair_description(repair: Any) -> str | None:
    width = getattr(repair, "width", None)
    height = getattr(repair, "height", None)
    bit_depth = getattr(repair, "bit_depth", None)
    color_type = getattr(repair, "color_type", None)
    if None in (width, height, bit_depth, color_type):
        return None
    return "%sx%s, bit depth %s, color type %s" % (
        width,
        height,
        bit_depth,
        color_type,
    )


def _chrm_repair_needs_choice(repair: Any) -> bool:
    return (
        getattr(repair, "missing_bytes", 0) > 0
        and getattr(repair, "inferred_payload", None) is not None
        and getattr(repair, "removal_data", None) is not None
        and not getattr(repair, "removed", False)
        and not getattr(repair, "preserved_crc", False)
    )


def _zero_scanline_blackfill_needs_choice(repair: Any) -> bool:
    return (
        isinstance(repair, idat.PartialIdatBlackfillRepair)
        and str(getattr(repair, "strategy", "")).startswith("partial-idat-blackfill")
        and getattr(repair, "recovered_scanlines", 0) == 0
        and getattr(repair, "total_scanlines", 0) > 0
    )


def _partial_blackfill_bruteforce_can_help(repair: Any) -> bool:
    return (
        isinstance(repair, idat.PartialIdatBlackfillRepair)
        and str(getattr(repair, "strategy", "")).startswith("partial-idat-blackfill")
        and 0 < getattr(repair, "recovered_scanlines", 0) < getattr(repair, "total_scanlines", 0)
    )


def _source_data_from_runtime(runtime: AutomaticRepairRuntime) -> bytes | None:
    if not runtime.data_hex:
        return None
    try:
        return bytes.fromhex(runtime.data_hex)
    except ValueError:
        return None


def _idat_bruteforce_target(source_data: bytes) -> png.PngChunk | None:
    try:
        chunks = tuple(png.iter_chunks(source_data))
    except png.PngFormatError:
        return None

    idat_chunks = tuple(chunk for chunk in chunks if chunk.chunk_type == b"IDAT")
    if not idat_chunks:
        return None

    analysis = idat.analyze_idat_stream(source_data)
    error_index = analysis.error_idat_index
    if error_index is not None and 1 <= error_index <= len(idat_chunks):
        return idat_chunks[error_index - 1]

    return idat_chunks[0]


def _idat_original_crc_target(chunk: png.PngChunk) -> str | None:
    actual_crc = binascii.crc32(chunk.chunk_type + chunk.data) & 0xFFFFFFFF
    if actual_crc == chunk.crc:
        return None
    return chunk.crc.to_bytes(4, "big").hex()


def _format_sbb_idat_diagnostic(
    diagnostic: idat.SmashBruteBrawlIdatDiagnostic,
) -> tuple[str, str]:
    order = " -> ".join(diagnostic.hephaestus_order or ("Replace", "Insert", "Remove"))
    if not diagnostic.supported:
        return (
            "SBB IDAT diagnostic:\n"
            "image: unsupported\n"
            "zlib status: %s\n"
            "CRC target: %s\n"
            "SBB chance: %s - %s\n"
            "HephaestusForge order: %s"
            % (
                diagnostic.zlib_status or "unknown",
                "trusted" if diagnostic.crc_target_trusted else "not trusted",
                diagnostic.success_estimate,
                diagnostic.success_reason or diagnostic.reason or "no usable IDAT measurement",
                order,
            ),
            "bad",
        )

    crc_label = "trusted original IDAT CRC" if diagnostic.crc_target_trusted else "not trusted"
    message = (
        "SBB IDAT diagnostic:\n"
        "image: %sx%s, %s %s-bit\n"
        "IDAT: %s chunks, %s compressed bytes, zlib %s\n"
        "decompressed: expected %s, got %s, missing %s\n"
        "scanlines: %s/%s complete, %s bytes into next scanline\n"
        "CRC target: %s\n"
        "SBB chance: %s - %s\n"
        "HephaestusForge order: %s"
        % (
            diagnostic.width,
            diagnostic.height,
            diagnostic.color_label,
            diagnostic.bit_depth,
            diagnostic.idat_chunk_count,
            f"{diagnostic.compressed_size:,}",
            diagnostic.zlib_status,
            f"{diagnostic.expected_decompressed_size:,}",
            f"{diagnostic.decompressed_size:,}",
            f"{diagnostic.missing_decompressed_size:,}",
            diagnostic.complete_scanlines,
            diagnostic.total_scanlines,
            diagnostic.partial_scanline_bytes,
            crc_label,
            diagnostic.success_estimate,
            diagnostic.success_reason,
            order,
        )
    )
    mood = "good" if diagnostic.success_estimate == "good" else "bad" if diagnostic.success_estimate == "low" else "com"
    return message, mood


def _sbb_diagnostic_says_twobytes_is_too_small(
    diagnostic: idat.SmashBruteBrawlIdatDiagnostic,
) -> bool:
    if not diagnostic.cheap_twobytes_viable:
        return True
    if diagnostic.success_estimate != "low":
        return False
    if not diagnostic.supported:
        return True
    threshold = max(diagnostic.scanline_size * 2, 4096)
    return diagnostic.missing_decompressed_size > threshold


def _partial_blackfill_question_id(success_estimate: str) -> str:
    return (
        "IDAT partial blackfill:-Launch SmashBruteBrawl on the original IDAT "
        "after writing the blackfill clone? (chance of success: %s)"
        % (success_estimate or "unknown")
    )


def _partial_blackfill_hephaestus_question_id(success_estimate: str) -> str:
    return (
        "IDAT partial blackfill:-Launch HephaestusForge after low "
        "chance diagnostic? (chance of success: %s)"
        % (success_estimate or "unknown")
    )


def _hephaestus_primary_edit_mode(
    diagnostic: idat.SmashBruteBrawlIdatDiagnostic,
) -> str:
    order = diagnostic.hephaestus_order or ("Replace", "Insert", "Remove")
    first = str(order[0])
    return first if first in {"Replace", "Insert", "Remove"} else "Replace"


def _partial_blackfill_bruteforce_question(
    runtime: AutomaticRepairRuntime,
    repair: idat.PartialIdatBlackfillRepair,
    target_chunk: png.PngChunk,
    source_data: bytes,
    crc_target_trusted: bool,
) -> str | None:
    runtime.candy(
        "Cowsay",
        "libpng confirms the IDAT does not feed the whole image.",
        "bad",
    )
    runtime.candy(
        "Cowsay",
        "The blackfill clone is a valid fallback: %s/%s scanlines are readable."
        % (repair.recovered_scanlines, repair.total_scanlines),
        "good",
    )
    diagnostic = idat.analyze_sbb_idat_diagnostic(
        source_data,
        crc_target_trusted=crc_target_trusted,
    )
    diagnostic_message, diagnostic_mood = _format_sbb_idat_diagnostic(diagnostic)
    runtime.candy("Cowsay", diagnostic_message, diagnostic_mood)
    twobytes_too_small = _sbb_diagnostic_says_twobytes_is_too_small(diagnostic)
    if twobytes_too_small:
        runtime.candy(
            "Cowsay",
            "Missing decompressed bytes are not compressed bytes I can paste back one-for-one.",
            "com",
        )
        runtime.candy(
            "Cowsay",
            "TwoBytes level 0 probably cannot cover this damage. The blackfill clone is the safer fallback.",
            "bad",
        )
        runtime.candy(
            "Cowsay",
            "HephaestusForge can try %s first, then the other edit families, but it may take years and still fail."
            % _hephaestus_primary_edit_mode(diagnostic),
            "com",
        )
    else:
        runtime.candy(
            "Cowsay",
            "I can also launch SmashBruteBrawl on the original IDAT bytes, before accepting black rows as the final word.",
            "com",
        )
    if runtime.question is None:
        return None

    if twobytes_too_small:
        launch_hephaestus = bool(
            runtime.question(
                id=_partial_blackfill_hephaestus_question_id(diagnostic.success_estimate),
                idhash=(
                    "IDAT-partial-blackfill-hephaestus",
                    target_chunk.offset,
                    target_chunk.length,
                    repair.recovered_scanlines,
                    repair.total_scanlines,
                    repair.width,
                    repair.height,
                    _hephaestus_primary_edit_mode(diagnostic),
                ),
                skipauto=True,
            )
        )
        return "hephaestus:%s" % _hephaestus_primary_edit_mode(diagnostic) if launch_hephaestus else None

    launch_twobytes = bool(
        runtime.question(
            id=_partial_blackfill_question_id(diagnostic.success_estimate),
            idhash=(
                "IDAT-partial-blackfill-smash",
                target_chunk.offset,
                target_chunk.length,
                repair.recovered_scanlines,
                repair.total_scanlines,
                repair.width,
                repair.height,
            ),
            skipauto=True,
        )
    )
    if not launch_twobytes:
        return None

    return "twobytes:%s" % _hephaestus_primary_edit_mode(diagnostic)


def maybe_launch_partial_blackfill_bruteforce(
    runtime: AutomaticRepairRuntime,
    repair: Any,
) -> bool:
    if not _partial_blackfill_bruteforce_can_help(repair):
        return False
    if runtime.smash_brute_brawl is None:
        return False

    source_data = _source_data_from_runtime(runtime)
    if source_data is None:
        return False

    target_chunk = _idat_bruteforce_target(source_data)
    if target_chunk is None:
        return False

    if runtime.preview_repair_image is not None:
        runtime.preview_repair_image(repair.data, "IDAT_Blackfill_Preview")

    old_crc = _idat_original_crc_target(target_chunk)
    launch_mode = _partial_blackfill_bruteforce_question(
        runtime,
        repair,
        target_chunk,
        source_data,
        old_crc is not None,
    )
    if launch_mode is None:
        return False
    _launch_partial_blackfill_bruteforce(
        runtime,
        repair,
        target_chunk,
        old_crc,
        launch_mode,
    )
    return True


def _launch_partial_blackfill_bruteforce(
    runtime: AutomaticRepairRuntime,
    repair: idat.PartialIdatBlackfillRepair,
    target_chunk: png.PngChunk,
    old_crc: str | None,
    launch_mode: str,
) -> None:
    mode_name, _, edit_mode = launch_mode.partition(":")
    if edit_mode not in {"Replace", "Insert", "Remove"}:
        edit_mode = "Replace"
    runtime.side_notes.append(
        "-FixItFelix:launched SmashBruteBrawl on source IDAT after partial blackfill %s/%s."
        % (repair.recovered_scanlines, repair.total_scanlines)
    )
    smash_kwargs: dict[str, Any] = {
        "EditMode": edit_mode,
        "BfMode": "Brutus" if mode_name == "hephaestus" else "TwoBytes",
        "BruteCrc": True,
        "BruteLength": True,
        "BruteLevel": HEPHAESTUS_INITIAL_BRUTE_LEVEL if mode_name == "hephaestus" else 0,
    }
    if mode_name == "hephaestus":
        runtime.side_notes.append(
            "-FixItFelix: low SBB diagnostic selected HephaestusForge (%s-first)." % edit_mode
        )
    if old_crc is not None:
        smash_kwargs["OldCrc"] = old_crc
        runtime.side_notes.append("-FixItFelix: SmashBruteBrawl will use stored IDAT CRC as target.")
    else:
        runtime.side_notes.append("-FixItFelix: stored IDAT CRC already matches current bytes; using image probe.")
    runtime.smash_brute_brawl(
        runtime.file_origin or "IDAT",
        "IDAT",
        target_chunk.length,
        target_chunk.offset * 2,
        "FixItFelix partial IDAT blackfill HephaestusForge" if mode_name == "hephaestus" else "FixItFelix partial IDAT blackfill",
        **smash_kwargs,
    )


def apply_partial_blackfill_decision(
    runtime: AutomaticRepairRuntime,
    repair: idat.PartialIdatBlackfillRepair,
) -> bool:
    applied_repair = fixit_felix.applied_repair(repair)
    runtime.side_notes.append(applied_repair.note)

    source_data = _source_data_from_runtime(runtime)
    target_chunk = _idat_bruteforce_target(source_data) if source_data is not None else None
    if runtime.smash_brute_brawl is None or source_data is None or target_chunk is None:
        runtime.candy(
            "Cowsay",
            automatic_repair_success_message(repair),
            "com",
        )
        runtime.write_clone(applied_repair.data_hex, applied_repair.save_suffix)
        return True

    old_crc = _idat_original_crc_target(target_chunk)
    launch_mode = _partial_blackfill_bruteforce_question(
        runtime,
        repair,
        target_chunk,
        source_data,
        old_crc is not None,
    )
    runtime.write_clone(applied_repair.data_hex, applied_repair.save_suffix)
    if runtime.preview_repair_image is not None:
        runtime.preview_repair_image(repair.data, "IDAT_Blackfill_Preview")
    if launch_mode is None:
        runtime.side_notes.append("-FixItFelix: kept partial IDAT blackfill fallback after diagnostic gate.")
        return True
    _launch_partial_blackfill_bruteforce(
        runtime,
        repair,
        target_chunk,
        old_crc,
        launch_mode,
    )
    return True


def _dedupe_paths(paths: list[Path]) -> tuple[Path, ...]:
    unique: list[Path] = []
    seen: set[str] = set()
    for path in paths:
        try:
            key = str(path.resolve())
        except OSError:
            key = str(path)
        if key in seen:
            continue
        seen.add(key)
        unique.append(path)
    return tuple(unique)


def _idat_donor_search_roots(file_origin: Any) -> tuple[Path, ...]:
    roots: list[Path] = []
    origin_text = str(file_origin or "")
    if origin_text:
        origin = Path(origin_text)
        if not origin.is_absolute():
            origin = Path.cwd() / origin
        roots.append(origin.parent)
        for parent in origin.parents[:4]:
            roots.append(parent)
            roots.append(parent / "schaik-javapng-samples")
    roots.append(Path.cwd() / "schaik-javapng-samples")
    return _dedupe_paths(roots)


def _candidate_idat_donor_paths(file_origin: Any) -> tuple[Path, ...]:
    candidates: list[Path] = []
    origin_text = str(file_origin or "")
    try:
        origin_resolved = str(Path(origin_text).resolve()) if origin_text else ""
    except OSError:
        origin_resolved = origin_text

    for root in _idat_donor_search_roots(file_origin):
        if not root.is_dir():
            continue
        for path in sorted(root.glob("*.png")):
            try:
                resolved = str(path.resolve())
            except OSError:
                resolved = str(path)
            if resolved == origin_resolved:
                continue
            candidates.append(path)

    unique = _dedupe_paths(candidates)
    clean = tuple(path for path in unique if "brokenjavapngsuite" not in path.parts)
    broken = tuple(path for path in unique if "brokenjavapngsuite" in path.parts)
    return clean + broken


def _local_idat_donor_repair(runtime: AutomaticRepairRuntime) -> idat.IdatDonorRepair | None:
    if not runtime.data_hex:
        return None
    try:
        source_data = bytes.fromhex(runtime.data_hex)
    except ValueError:
        return None

    repairs: list[idat.IdatDonorRepair] = []
    for path in _candidate_idat_donor_paths(runtime.file_origin):
        try:
            donor_data = path.read_bytes()
        except OSError:
            continue
        try:
            donor_path = str(path.relative_to(Path.cwd()))
        except ValueError:
            donor_path = str(path)
        repair = idat.rebuild_idat_from_donor(
            source_data,
            donor_data,
            donor_label=path.name,
            donor_path=donor_path,
        )
        if repair is None:
            continue
        if repairs and repair.data == repairs[0].data:
            continue
        repairs.append(repair)
        if len(repairs) > 1:
            return None
    return repairs[0] if repairs else None


def _zero_scanline_options_message(runtime: AutomaticRepairRuntime) -> None:
    runtime.candy(
        "Cowsay",
        "IDAT gives zero readable scanlines. From this file alone, the original pixels are not recoverable.",
        "bad",
    )
    runtime.candy(
        "Cowsay",
        "I can offer three clearly different fallbacks: 1) local donor IDAT, 2) synthetic diagnostic IDAT from IHDR/PLTE, 3) all-black placeholder.",
        "com",
    )


def _apply_idat_donor_choice(
    runtime: AutomaticRepairRuntime,
    repair: idat.PartialIdatBlackfillRepair,
) -> bool | None:
    donor_repair = _local_idat_donor_repair(runtime)
    if donor_repair is None or runtime.question is None:
        return None

    runtime.candy(
        "Cowsay",
        "I found one local PNG with the same pixel structure and a complete IDAT: %s."
        % donor_repair.donor_path,
        "com",
    )
    runtime.candy(
        "Cowsay",
        "Option 1: Yes replaces only the broken IDAT stream with that donor IDAT. No means I offer the synthetic option next.",
        "bad",
    )

    use_donor = runtime.question(
        id=(
            "IDAT donor repair:-No readable IDAT scanlines. Replace IDAT with "
            "local donor %s?"
            % donor_repair.donor_path
        ),
        idhash=(
            "IDAT-donor",
            donor_repair.donor_path,
            repair.width,
            repair.height,
            repair.bit_depth,
            repair.color_type,
        ),
        skipauto=True,
    )
    if not use_donor:
        return None

    applied_repair = fixit_felix.applied_repair(donor_repair)
    runtime.side_notes.append(applied_repair.note)
    runtime.write_clone(applied_repair.data_hex, applied_repair.save_suffix)
    return True


def _apply_synthetic_idat_choice(
    runtime: AutomaticRepairRuntime,
    repair: idat.PartialIdatBlackfillRepair,
) -> bool | None:
    if runtime.question is None or not runtime.data_hex:
        return None
    try:
        source_data = bytes.fromhex(runtime.data_hex)
    except ValueError:
        return None

    synthetic_repair = idat.rebuild_synthetic_idat(source_data)
    if synthetic_repair is None:
        return None

    runtime.candy(
        "Cowsay",
        "Option 2: I can build a deterministic diagnostic IDAT from IHDR/PLTE. It will be valid PNG data, not the original picture.",
        "com",
    )
    use_synthetic = runtime.question(
        id="IDAT synthetic repair:-No original scanlines. Build synthetic diagnostic IDAT?",
        idhash=(
            "IDAT-synthetic",
            repair.width,
            repair.height,
            repair.bit_depth,
            repair.color_type,
        ),
        skipauto=True,
    )
    if not use_synthetic:
        return None

    applied_repair = fixit_felix.applied_repair(synthetic_repair)
    runtime.side_notes.append(applied_repair.note)
    runtime.write_clone(applied_repair.data_hex, applied_repair.save_suffix)
    return True


def apply_zero_scanline_blackfill_choice(
    runtime: AutomaticRepairRuntime,
    repair: idat.PartialIdatBlackfillRepair,
) -> bool | None:
    _zero_scanline_options_message(runtime)

    donor_result = _apply_idat_donor_choice(runtime, repair)
    if donor_result is not None:
        return donor_result

    synthetic_result = _apply_synthetic_idat_choice(runtime, repair)
    if synthetic_result is not None:
        return synthetic_result

    runtime.candy(
        "Cowsay",
        "Option 3: I can frame the absence with zero bytes, but that is a placeholder, not a recovered image.",
        "bad",
    )
    runtime.candy(
        "Cowsay",
        "Write the all-black placeholder only if you want a structurally valid PNG for testing.",
        "com",
    )

    skipped_note = (
        "-FixItFelix:skipped all-black placeholder because IDAT recovered 0/%s scanlines."
        % repair.total_scanlines
    )
    if runtime.question is None:
        runtime.side_notes.append(skipped_note)
        return None

    write_placeholder = runtime.question(
        id="IDAT Zero Scanline Blackfill:-No readable IDAT scanlines. Write all-black placeholder anyway?",
        idhash=(
            "IDAT-zero-blackfill",
            repair.width,
            repair.height,
            repair.bit_depth,
            repair.color_type,
        ),
        skipauto=True,
    )
    if not write_placeholder:
        runtime.side_notes.append(skipped_note)
        return None

    applied_repair = fixit_felix.applied_repair(repair)
    runtime.side_notes.append(applied_repair.note)
    runtime.write_clone(applied_repair.data_hex, applied_repair.save_suffix)
    return True


def apply_chrm_inference_choice(runtime: AutomaticRepairRuntime, repair: Any) -> bool | None:
    missing = getattr(repair, "missing_bytes", 0)
    tested = getattr(repair, "crc_candidates_tested", 0)
    runtime.candy(
        "Cowsay",
        "cHRM is short by %s byte(s). I made a plausible chromaticity hypothesis first."
        % missing,
        "com",
    )
    if tested:
        runtime.candy(
            "Cowsay",
            "Then I brute-forced %s completion(s) against the stored cHRM CRC. None matched."
            % tested,
            "bad",
        )
    else:
        runtime.candy(
            "Cowsay",
            "The missing tail is too wide for the small CRC brute force, so this is only an inference.",
            "bad",
        )
    runtime.candy(
        "Cowsay",
        "Yes means I write the inferred cHRM. No means I remove the optional cHRM chunk instead.",
        "com",
    )

    if runtime.question is None:
        runtime.side_notes.append(
            "-FixItFelix:cHRM inference needed a prompt; removed short cHRM conservatively."
        )
        runtime.write_clone(
            getattr(repair, "removal_data").hex(),
            "-removed short cHRM chunk length %s below required 32." % getattr(repair, "old_length", "?"),
        )
        return True

    question_id = "cHRM Missing Bytes Inference:-cHRM length is not Valid"
    accept_inference = runtime.question(
        id=question_id,
        idhash=(
            "cHRM",
            getattr(repair, "chunk_offset", None),
            getattr(repair, "old_length", None),
            getattr(repair, "inferred_payload", b"").hex(),
        ),
        skipauto=True,
    )
    if accept_inference:
        runtime.side_notes.append(fixit_felix.repair_note(repair))
        runtime.write_clone(
            getattr(repair, "data").hex(),
            "-%s." % getattr(repair, "strategy", "inferred cHRM"),
        )
        return True

    removal_strategy = "removed short cHRM chunk length %s below required 32" % getattr(
        repair,
        "old_length",
        "?",
    )
    runtime.side_notes.append(
        "-FixItFelix:%s after declining inferred cHRM completion." % removal_strategy
    )
    runtime.write_clone(getattr(repair, "removal_data").hex(), "-%s." % removal_strategy)
    return True


def emit_ihdr_repair_explanation(runtime: AutomaticRepairRuntime, repair: Any) -> None:
    description = _ihdr_repair_description(repair)
    strategy = str(getattr(repair, "strategy", ""))

    if _has_ihdr_crc_finding(runtime):
        runtime.candy(
            "Cowsay",
            "This is not just a cheap CRC sticker swap. I rebuilt IHDR from the image clues first.",
            "com",
        )
    else:
        runtime.candy(
            "Cowsay",
            "IHDR's CRC is not the complaint here. The header values themselves are impossible together.",
            "bad",
        )

    if description is not None:
        if "trimmed IHDR length" in strategy:
            runtime.candy(
                "Cowsay",
                "I trimmed IHDR back to 13 bytes and rebuilt its CRC. The header still describes: %s."
                % description,
                "com",
            )
        else:
            runtime.candy(
                "Cowsay",
                "I rebuilt IHDR from the IDAT scanline math: %s." % description,
                "com",
            )

    runtime.candy(
        "Cowsay",
        "Now I can write a clone with a coherent header instead of pretending the old one was fine.",
        "com",
    )


def emit_libpng_critical(runtime: LibpngErrorRuntime, finding: Any) -> None:
    runtime.emit("\n-\033[1;31;49mCriticalHit\033[m: %s" % finding)


def _idat_interruption_question_hash(repair: png.IdatInterruptionRepairPlan, action: str) -> str:
    return "IDAT-interruption:%s:%s" % (action, ",".join(repair.interrupting_chunks))


def _apply_idat_interruption_plan(
    runtime: AutomaticRepairRuntime,
    repair: png.IdatInterruptionRepairPlan,
) -> bool | None:
    chunks = ", ".join(repair.interrupting_chunks)
    runtime.candy(
        "Cowsay",
        "This PNG has ancillary chunk(s) sitting between IDAT chunks: %s." % chunks,
        "bad",
    )
    runtime.candy(
        "Cowsay",
        "IDAT chunks must stay consecutive. I can move that passenger after the final IDAT, before IEND.",
        "com",
    )

    if runtime.question is not None and runtime.question(
        id="IDAT Interruption Move:-Move ancillary chunk(s) out of the IDAT chain?",
        idhash=_idat_interruption_question_hash(repair, "move"),
        skipauto=True,
    ):
        return apply_repair(runtime, repair.move_repair)

    if repair.remove_repair is None:
        runtime.candy(
            "Cowsay",
            "I am not deleting it automatically: at least one interrupter is not low-risk safe-to-copy metadata.",
            "bad",
        )
        runtime.side_notes.append(
            "-FixItFelix:kept IDAT-interrupting chunk(s) after relocation was declined: %s."
            % chunks
        )
        return None

    runtime.candy(
        "Cowsay",
        "Those interrupter chunk(s) are ancillary and safe-to-copy, so deletion is also a reasonable cleanup.",
        "com",
    )
    if runtime.question is not None and runtime.question(
        id="IDAT Interruption Removal:-Remove safe-to-copy ancillary chunk(s) from the clone?",
        idhash=_idat_interruption_question_hash(repair, "remove"),
        skipauto=True,
    ):
        return apply_repair(runtime, repair.remove_repair)

    runtime.side_notes.append(
        "-FixItFelix:kept IDAT-interrupting safe-to-copy chunk(s) after user declined move/removal: %s."
        % chunks
    )
    return None


def _write_no_next_repair(runtime: NoNextChunkRuntime, repair: Any) -> Any:
    note = fixit_felix.repair_note(repair)
    runtime.side_notes.append(note)
    return runtime.write_clone(repair.data.hex(), note)


def _apply_idat_interruption_plan_before_libpng(
    runtime: NoNextChunkRuntime,
    repair: png.IdatInterruptionRepairPlan,
) -> tuple[bool, Any]:
    chunks = ", ".join(repair.interrupting_chunks)
    runtime.candy(
        "Cowsay",
        "I found ancillary chunk(s) between IDAT chunks before libpng gets a vote: %s." % chunks,
        "bad",
    )
    runtime.candy(
        "Cowsay",
        "The least destructive repair is to move them after the final IDAT, before IEND.",
        "com",
    )

    if runtime.question(
        id="IDAT Interruption Move:-Move ancillary chunk(s) out of the IDAT chain?",
        idhash=_idat_interruption_question_hash(repair, "move"),
        skipauto=True,
    ):
        return True, _write_no_next_repair(runtime, repair.move_repair)

    if repair.remove_repair is None:
        runtime.candy(
            "Cowsay",
            "I am leaving it alone: deleting an unsafe-to-copy or non-low-risk chunk needs a human choice.",
            "bad",
        )
        runtime.side_notes.append(
            "-FixItFelix:kept IDAT-interrupting chunk(s) after relocation was declined: %s."
            % chunks
        )
        return False, None

    runtime.candy(
        "Cowsay",
        "Those interrupter chunk(s) are ancillary and safe-to-copy, so deletion is also available.",
        "com",
    )
    if runtime.question(
        id="IDAT Interruption Removal:-Remove safe-to-copy ancillary chunk(s) from the clone?",
        idhash=_idat_interruption_question_hash(repair, "remove"),
        skipauto=True,
    ):
        return True, _write_no_next_repair(runtime, repair.remove_repair)

    runtime.side_notes.append(
        "-FixItFelix:kept IDAT-interrupting safe-to-copy chunk(s) after user declined move/removal: %s."
        % chunks
    )
    return False, None


def _splt_payload_question_hash(repair: png.SpltPayloadRepairPlan) -> str:
    return "sPLT-payload:%s" % ",".join(repair.affected_chunks)


def _trns_transparency_question_hash(repair: png.TrnsTransparencyRepairPlan) -> str:
    return "tRNS-transparency:%s" % ",".join(repair.affected_chunks)


def _describe_trns_transparency_plan(
    runtime: AutomaticRepairRuntime | NoNextChunkRuntime,
    repair: png.TrnsTransparencyRepairPlan,
) -> None:
    runtime.candy(
        "Cowsay",
        "I found an indexed tRNS alpha table longer than its PLTE palette.",
        "bad",
    )
    if repair.trimmed_payload_is_fully_transparent:
        runtime.candy(
            "Cowsay",
            "Trimming it to the palette size is PNG-legal, but it makes every palette entry transparent.",
            "bad",
        )
    runtime.candy(
        "Cowsay",
        "I can trim tRNS to the PLTE entry count, or remove that optional transparency chunk.",
        "com",
    )


def _trns_transparency_question_id(repair: png.TrnsTransparencyRepairPlan) -> str:
    if repair.trimmed_payload_is_fully_transparent:
        return (
            "tRNS Indexed Alpha Removal:-Trimmed tRNS would make every PLTE entry "
            "transparent. Remove tRNS instead?"
        )
    return "tRNS Indexed Alpha Resize:-Trim tRNS alpha table to PLTE entry count?"


def _apply_trns_transparency_plan(
    runtime: AutomaticRepairRuntime,
    repair: png.TrnsTransparencyRepairPlan,
) -> bool | None:
    _describe_trns_transparency_plan(runtime, repair)
    if repair.trimmed_payload_is_fully_transparent:
        if runtime.question is None or runtime.question(
            id=_trns_transparency_question_id(repair),
            idhash=_trns_transparency_question_hash(repair),
        ):
            return apply_repair(runtime, repair.remove_repair)

        return apply_repair(runtime, repair.trim_repair)

    if runtime.question is None or runtime.question(
        id=_trns_transparency_question_id(repair),
        idhash=_trns_transparency_question_hash(repair),
    ):
        return apply_repair(runtime, repair.trim_repair)

    return apply_repair(runtime, repair.remove_repair)


def _apply_trns_transparency_plan_before_libpng(
    runtime: NoNextChunkRuntime,
    repair: png.TrnsTransparencyRepairPlan,
) -> tuple[bool, Any]:
    _describe_trns_transparency_plan(runtime, repair)
    if repair.trimmed_payload_is_fully_transparent:
        if runtime.question(
            id=_trns_transparency_question_id(repair),
            idhash=_trns_transparency_question_hash(repair),
        ):
            return True, _write_no_next_repair(runtime, repair.remove_repair)

        return True, _write_no_next_repair(runtime, repair.trim_repair)

    if runtime.question(
        id=_trns_transparency_question_id(repair),
        idhash=_trns_transparency_question_hash(repair),
    ):
        return True, _write_no_next_repair(runtime, repair.trim_repair)

    return True, _write_no_next_repair(runtime, repair.remove_repair)


def _apply_splt_payload_plan(
    runtime: AutomaticRepairRuntime,
    repair: png.SpltPayloadRepairPlan,
) -> bool | None:
    chunks = ", ".join(repair.affected_chunks)
    runtime.candy(
        "Cowsay",
        "I found malformed or duplicate sPLT suggested-palette metadata: %s." % chunks,
        "bad",
    )
    if repair.repair_repair is None:
        runtime.candy(
            "Cowsay",
            "I do not have a plausible sPLT repair candidate, so deletion is the only clean branch.",
            "bad",
        )
        return apply_repair(runtime, repair.remove_repair)

    if runtime.question is None or runtime.question(
        id="sPLT Payload Repair:-Try to repair malformed/duplicate sPLT chunk(s)?",
        idhash=_splt_payload_question_hash(repair),
    ):
        return apply_repair(runtime, repair.repair_repair)

    return apply_repair(runtime, repair.remove_repair)


def _apply_splt_payload_plan_before_libpng(
    runtime: NoNextChunkRuntime,
    repair: png.SpltPayloadRepairPlan,
) -> tuple[bool, Any]:
    chunks = ", ".join(repair.affected_chunks)
    runtime.candy(
        "Cowsay",
        "I found malformed or duplicate sPLT suggested-palette metadata before libpng: %s." % chunks,
        "bad",
    )
    if repair.repair_repair is not None and runtime.question(
        id="sPLT Payload Repair:-Try to repair malformed/duplicate sPLT chunk(s)?",
        idhash=_splt_payload_question_hash(repair),
    ):
        return True, _write_no_next_repair(runtime, repair.repair_repair)

    return True, _write_no_next_repair(runtime, repair.remove_repair)


GRAYSCALE_PLTE_REBUILD_PROMPTS = {
    "rebuilt empty indexed PLTE as grayscale palette": (
        "empty_plte_grayscale_plte",
        "empty-indexed-grayscale",
    ),
    "rebuilt malformed indexed PLTE as grayscale palette": (
        "malformed_plte_grayscale_plte",
        "malformed-indexed-grayscale",
    ),
    "rebuilt undersized indexed PLTE as grayscale palette": (
        "undersized_plte_grayscale_plte",
        "undersized-indexed-grayscale",
    ),
    "rebuilt oversized indexed PLTE as grayscale palette": (
        "oversized_plte_grayscale_plte",
        "oversized-indexed-grayscale",
    ),
    "rebuilt low-diversity indexed PLTE as grayscale palette": (
        "low_diversity_plte_grayscale_plte",
        "low-diversity-indexed-grayscale",
    ),
}


def _grayscale_plte_rebuild_prompt(repair: Any) -> tuple[str, str] | None:
    return GRAYSCALE_PLTE_REBUILD_PROMPTS.get(str(getattr(repair, "strategy", "")))


def _plte_manual_window_from_data_hex(data_hex: str) -> tuple[int, int] | None:
    try:
        chunks = tuple(png.iter_chunks(bytes.fromhex(data_hex)))
    except (ValueError, png.PngFormatError):
        return None

    plte = next((chunk for chunk in chunks if chunk.chunk_type == b"PLTE"), None)
    if plte is None:
        return None

    start = plte.offset * 2
    end = (plte.offset + 12 + plte.length) * 2
    return start, end


def maybe_offer_manual_plte_editor(runtime: AutomaticRepairRuntime, repair: Any) -> bool | None:
    prompt = _grayscale_plte_rebuild_prompt(repair)
    if prompt is None:
        return None
    if not runtime.interactive:
        return None
    if runtime.question is None or runtime.tk_manual_plte is None:
        return None

    window = _plte_manual_window_from_data_hex(runtime.data_hex)
    if window is None:
        return None

    start, end = window
    preview_label, route_label = prompt
    if runtime.preview_repair_image is not None:
        runtime.preview_repair_image(repair.data, preview_label)

    runtime.candy(
        "Cowsay",
        "I rebuilt that PLTE with a grayscale emergency palette. Valid PNG, yes. Haute couture, maybe not.",
        "com",
    )
    runtime.candy(
        "Cowsay",
        "If the preview makes your eyes file a complaint, say yes and I hand you the Tkinter palette controls.",
        "com",
    )

    if not runtime.question(
        id="PLTE Palette Editor:-Open Tkinter to tune this reconstructed PLTE?",
        idhash=("PLTE", start, end, route_label),
        skipauto=True,
    ):
        return None

    runtime.side_notes.append("-FixItFelix:opened Tkinter PLTE editor after grayscale PLTE preview.")
    runtime.tk_manual_plte(
        runtime.file_origin,
        b"PLTE",
        end,
        start,
        "-PLTE Wrong Data",
    )
    return True


def automatic_repair_success_message(repair: Any) -> str:
    strategy = str(getattr(repair, "strategy", "automatic repair"))
    if "converted private" in strategy and "compression method" in strategy:
        return (
            "The IHDR compression byte is private, but the IDAT decoded as a known "
            "compression stream. I am rewriting IHDR compression to 0 and storing "
            "the image data as standard zlib."
        )
    if strategy.startswith("idat-filter0-normalize"):
        return (
            "The IDAT stream decompresses cleanly, but some scanline filter bytes "
            "are outside PNG's 0..4 range. I am changing only those row filters to "
            "0, then recompressing IDAT."
        )
    if strategy.startswith("partial-idat-blackfill"):
        return (
            "The IDAT stream stops before the full image is available. I am keeping "
            "the readable scanlines and filling the missing rows with black pixels."
        )
    if "tRNS" in strategy:
        return (
            "The transparency metadata does not match the PNG palette/color rules. "
            "I am applying the selected tRNS branch and rebuilding CRCs."
        )
    if "PLTE" in strategy:
        return (
            "The palette does not match PNG rules or the used indexes. I am going "
            "to rebuild, trim, or remove PLTE while keeping the IDAT indexes intact."
        )
    if "sPLT" in strategy:
        return (
            "The suggested-palette metadata does not match PNG rules. I am applying "
            "the selected sPLT branch while keeping the image pixels intact."
        )
    if "duplicate" in strategy:
        return (
            "PNG readers want a single owner for this chunk type. I am removing the "
            "extra copy and rebuilding CRCs."
        )
    if "length" in strategy or "trimmed" in strategy or "padded" in strategy:
        return (
            "The chunk payload length does not match the PNG spec. I am resizing "
            "that payload and rebuilding the chunk CRC."
        )
    if "removed" in strategy:
        return (
            "This chunk is unsafe or illegal in this position. I am removing it and "
            "keeping the rest of the PNG stream intact."
        )
    if "moved" in strategy:
        return (
            "The chunk data looks usable, but it is in the wrong position. I am "
            "moving it to a PNG-legal place and rebuilding CRCs."
        )
    return (
        "I found an automatic repair path: %s. I am writing a separate clone with "
        "that change, leaving the original file untouched."
    ) % strategy


def apply_repair(runtime: AutomaticRepairRuntime, repair: Any) -> bool | None:
    if isinstance(repair, png.IdatInterruptionRepairPlan):
        return _apply_idat_interruption_plan(runtime, repair)
    if isinstance(repair, png.SpltPayloadRepairPlan):
        return _apply_splt_payload_plan(runtime, repair)
    if isinstance(repair, png.TrnsTransparencyRepairPlan):
        return _apply_trns_transparency_plan(runtime, repair)

    applied_repair = fixit_felix.applied_repair(repair)
    strategy = str(getattr(repair, "strategy", "automatic repair"))
    validation_errors = _ihdr_validation_errors(repair)
    if validation_errors:
        runtime.candy(
            "Cowsay",
            "The rebuilt IHDR still does not make a structurally valid PNG: %s"
            % "; ".join(validation_errors),
            "bad",
        )
        runtime.candy(
            "Cowsay",
            "So I am not writing that clone. Next stop is the IHDR brute force path.",
            "com",
        )
        runtime.side_notes.append(
            "-FixItFelix:IHDR automatic repair rejected before clone write: %s."
            % "; ".join(validation_errors)
        )
        return None

    if _chrm_repair_needs_choice(repair):
        return apply_chrm_inference_choice(runtime, repair)
    if _zero_scanline_blackfill_needs_choice(repair):
        return apply_zero_scanline_blackfill_choice(runtime, repair)
    if _partial_blackfill_bruteforce_can_help(repair):
        return apply_partial_blackfill_decision(runtime, repair)

    manual_plte_result = maybe_offer_manual_plte_editor(runtime, repair)
    if manual_plte_result is not None:
        return manual_plte_result

    if "duplicate IHDR" in strategy:
        runtime.candy(
            "Cowsay",
            "PNG only gets one IHDR. I am keeping the first header and cutting the duplicate.",
            "com",
        )
    elif "IHDR" in strategy:
        emit_ihdr_repair_explanation(runtime, repair)
    elif "cHRM" in strategy and getattr(repair, "preserved_crc", False):
        runtime.candy(
            "Cowsay",
            "The cHRM was short, but the missing bytes brute force landed back on the stored CRC.",
            "good",
        )
    else:
        runtime.candy(
            "Cowsay",
            automatic_repair_success_message(repair),
            "com",
        )
    runtime.side_notes.append(applied_repair.note)
    runtime.write_clone(applied_repair.data_hex, applied_repair.save_suffix)
    maybe_launch_partial_blackfill_bruteforce(runtime, repair)
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
    runtime.candy(
        "Cowsay",
        "This is the cheap CRC-only patch: I am changing the checksum label, not the chunk data.",
        "com",
    )
    runtime.candy(
        "Cowsay",
        "If the bytes are lying too, this will not save them. But the structure lets me try this tiny bandage.",
        "com",
    )
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
    if analysis.deflate_header is not None:
        details.append("deflate_header=%s" % analysis.deflate_header.summary)
    reason = analysis.reason or analysis.zlib_error
    if reason:
        details.append("reason=%s" % reason)
    return "; ".join(details) + "."


def idat_deflate_header_note(analysis: idat.IdatStreamAnalysis) -> str:
    if analysis.deflate_header is None:
        return "-IDAT deflate header diagnosis: unavailable."
    return "-IDAT deflate header diagnosis: %s." % analysis.deflate_header.summary


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
    runtime.side_notes.append(idat_stream_diagnosis_note(analysis))
    if analysis.decompressed_size == 0:
        runtime.candy(
            "Cowsay",
            "The first deflate table breaks before I can even pull one scanline out.",
            "bad",
        )
        runtime.candy(
            "Cowsay",
            "I will probe the deflate header first. No wide fishing net until this table makes sense.",
            "com",
        )
        runtime.candy("Title", "probe_deflate_header_candidates")
        runtime.side_notes.append(idat_deflate_header_note(analysis))
        header_probe = idat_bruteforce.probe_deflate_header_candidates(
            data,
            progress=_runtime_idat_queue_progress(runtime),
        )
        runtime.side_notes.append(idat_bruteforce.probe_summary_line(header_probe))

        if header_probe.best is None:
            runtime.candy(
                "Cowsay",
                "I did not get a usable scanline from the deflate-header probe. No clone, no wider brute force yet.",
                "bad",
            )
            runtime.side_notes.append("-IDAT deflate header probe found no clone-worthy scanline progress.")
            runtime.side_notes.append("-IDAT wide deflate probes skipped: header probe produced no usable scanline.")
            return None

        candidate = header_probe.best
        runtime.side_notes.extend(idat_bruteforce.candidate_summary_lines(header_probe))
        runtime.candy(
            "Cowsay",
            "I found a header byte that gets real scanline progress. Still an hypothesis, but now it has a pulse.",
            "good",
        )
        runtime.candy(
            "Cowsay",
            "Patch: IDAT stream offset 0x%x, byte %02x -> %02x."
            % (candidate.stream_offset, candidate.old_byte, candidate.new_byte),
            "com",
        )
        summary = "\n".join(
            (
                "-Repair hypothesis tried: targeted IDAT deflate header probe.",
                idat_deflate_header_note(analysis),
                idat_bruteforce.probe_summary_line(header_probe),
                *idat_bruteforce.candidate_summary_lines(header_probe),
                idat_stream_diagnosis_note(candidate.after),
            )
        )
        return True, runtime.write_clone(candidate.data, summary)

    runtime.candy(
        "Cowsay",
        "I will run the bounded IDAT strategy queue: strict byte, pre-error bit flips, then a wider byte probe.",
        "com",
    )
    runtime.candy("Title", "probe_idat_deflate_strategy_queue")
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

        runtime.candy("Title", "probe_idat_deflate_heavy_candidates")
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


def save_clean_idat_crc_only_patch_before_other_errors(
    runtime: WrongCrcRuntime,
    tools: relics.WrongCrcTools,
) -> tuple[bool, Any] | None:
    if tools.chunk != b"IDAT":
        return None

    validation = validate_idat_crc_only_patch(runtime, tools)
    if not validation.can_save:
        return None

    runtime.candy(
        "Cowsay",
        "The IDAT CRC-only patch validates cleanly even with the other finding still visible.",
        "good",
    )
    return save_wrong_crc(runtime, tools)


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
        clean_idat_crc_patch = save_clean_idat_crc_only_patch_before_other_errors(runtime, tools)
        if clean_idat_crc_patch is not None:
            return clean_idat_crc_patch

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
    if already_aligned:
        runtime.candy(
            "Cowsay",
            "So this is a diagnostic stop, not a clone-worthy repair yet.",
            "com",
        )
    else:
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
            finding_label = str(pandora_key).rsplit(":", 1)[-1].lstrip("-") or str(pandora_key)
            runtime.candy(
                "Cowsay",
                "That %s is a false positive im removing it .." % finding_label,
                "good",
            )
            relics.discard_pandora_error(runtime.pandora_box, pandora_key)
            runtime.side_notes.append("-Found False-Positive :[Error:-No NextChunk].")
            runtime.set_skip_bad_no_next_chunk(True)
            break


def no_next_missplaced_tools(runtime: NoNextChunkRuntime) -> list[Any] | None:
    for pandora_key in runtime.pandora_box:
        if _is_chunk_order_finding(pandora_key) and runtime.eof() is True:
            tools = list(runtime.pandora_box[pandora_key].values())
            if len(tools) >= 3:
                return tools
            inferred = infer_no_next_missplaced_tools_from_history(runtime.chunks_history)
            if inferred is not None:
                return list(inferred)
    return None


def _is_chunk_order_finding(value: Any) -> bool:
    text = str(value).lower()
    return any(
        clue in text
        for clue in (
            "missplaced",
            "chunkorder",
            "must be used after",
            "must appears before",
            "must appear before",
        )
    )


def _chunk_bytes(value: Any) -> bytes | None:
    if isinstance(value, bytes):
        return value
    if isinstance(value, str) and len(value) == 4:
        return value.encode("ascii", errors="ignore")
    return None


def infer_no_next_missplaced_tools_from_history(
    chunks_history: tuple[Any, ...],
) -> tuple[bytes, int, bytes] | None:
    history = tuple(_chunk_bytes(chunk) for chunk in chunks_history)
    if any(chunk is None for chunk in history):
        return None

    typed_history = tuple(chunk for chunk in history if chunk is not None)

    if len(typed_history) > 1 and typed_history[1] != b"IHDR" and b"IHDR" in typed_history:
        return (typed_history[1], 1, b"IHDR")

    if b"PLTE" in typed_history:
        plte_index = typed_history.index(b"PLTE")
        after_plte = set(specs.AFTER_PLTE)
        for index in range(1, plte_index):
            if typed_history[index] in after_plte:
                return (typed_history[index], index, b"PLTE")

        before_plte = set(specs.BEFORE_PLTE) - {b"PNG", b"IHDR"}
        for index in range(plte_index + 1, len(typed_history)):
            if typed_history[index] in before_plte:
                return (b"PLTE", plte_index, typed_history[index])

    if b"IDAT" in typed_history:
        idat_index = typed_history.index(b"IDAT")
        before_idat = set(specs.BEFORE_IDAT2) - {b"IHDR"}
        for index in range(idat_index + 1, len(typed_history)):
            if typed_history[index] in before_idat:
                return (b"IDAT", idat_index, typed_history[index])

    return None


def mark_no_next_iend_reached(runtime: NoNextChunkRuntime) -> None:
    runtime.check_chunk_order(b"IEND", "Critical")
    runtime.candy("Cowsay", "We have reached the end of file.", "good")
    runtime.set_eof(True)
    runtime.side_notes.append("-Reached the end of file.")


def apply_deferred_linefeed_after_chunk_tour(
    runtime: NoNextChunkRuntime,
) -> tuple[bool, Any]:
    if not runtime.has_deferred_linefeed_repair():
        return False, None
    if runtime.apply_deferred_linefeed_repair is None:
        return False, None

    runtime.candy(
        "Cowsay",
        "The chunk tour is complete, so I am applying the deferred line-feed repair now.",
        "com",
    )
    runtime.side_notes.append(
        "-Deferred line-feed repair applied after full chunk tour."
    )
    return True, runtime.apply_deferred_linefeed_repair()


def unresolved_non_no_next_findings(runtime: NoNextChunkRuntime) -> tuple[Any, ...]:
    return tuple(
        pandora_key
        for pandora_key in runtime.pandora_box
        if "no nextchunk" not in str(pandora_key).lower()
    )


def stop_before_libpng_for_unresolved_findings(
    runtime: NoNextChunkRuntime,
    findings: tuple[Any, ...],
) -> tuple[bool, Any]:
    runtime.candy(
        "Cowsay",
        "Libpng might smile at the pixels, but Pandora still has unpaid invoices. No Kraken snack yet.",
        "bad",
    )
    runtime.side_notes.append(
        "-Stopped before libpng: unresolved findings remain: %s."
        % ", ".join(str(finding) for finding in findings)
    )
    missing_plte_finding = next(
        (finding for finding in findings if relics.is_missing_plte_finding(finding)),
        None,
    )
    if missing_plte_finding is not None:
        runtime.candy(
            "Cowsay",
            "I found a missing PLTE repair path, so I am opening the Ark before calling this unsupported.",
            "com",
        )
        return True, runtime.run_relics(str(missing_plte_finding))

    png_bytes = bytes.fromhex(runtime.data_hex)
    duplicate_ihdr_repair = fixit_felix.duplicate_ihdr_cleanup(png_bytes, findings)
    if duplicate_ihdr_repair is not None:
        note = fixit_felix.repair_note(duplicate_ihdr_repair)
        runtime.candy(
            "Cowsay",
            "I found more than one IHDR, so I am keeping the first header and cutting the extra one.",
            "com",
        )
        runtime.side_notes.append(note)
        return True, runtime.write_clone(duplicate_ihdr_repair.data.hex(), note)

    duplicate_repair = fixit_felix.duplicate_singleton_cleanup(png_bytes, findings)
    if duplicate_repair is not None:
        note = fixit_felix.repair_note(duplicate_repair)
        runtime.candy(
            "Cowsay",
            "I found duplicate singleton metadata, so I am keeping the first copy and writing a cleaner clone.",
            "com",
        )
        runtime.side_notes.append(note)
        return True, runtime.write_clone(duplicate_repair.data.hex(), note)

    splt_payload_repair = fixit_felix.splt_payload_cleanup(png_bytes, findings)
    if isinstance(splt_payload_repair, png.SpltPayloadRepairPlan):
        return _apply_splt_payload_plan_before_libpng(runtime, splt_payload_repair)

    trns_repair = fixit_felix.trns_length(png_bytes, findings)
    if isinstance(trns_repair, png.TrnsTransparencyRepairPlan):
        return _apply_trns_transparency_plan_before_libpng(runtime, trns_repair)
    if trns_repair is not None:
        note = fixit_felix.repair_note(trns_repair)
        runtime.candy(
            "Cowsay",
            "I found invalid tRNS transparency metadata, so I am repairing it before libpng gets the final word.",
            "com",
        )
        runtime.side_notes.append(note)
        return True, runtime.write_clone(trns_repair.data.hex(), note)

    ster_mode_repair = fixit_felix.ster_mode(png_bytes, findings)
    if ster_mode_repair is not None:
        note = fixit_felix.repair_note(ster_mode_repair)
        runtime.candy(
            "Cowsay",
            "I found an invalid sTER stereo-layout mode, so I am normalizing it before libpng gets the final word.",
            "com",
        )
        runtime.side_notes.append(note)
        return True, runtime.write_clone(ster_mode_repair.data.hex(), note)

    time_value_repair = fixit_felix.time_value_range(png_bytes, findings)
    if time_value_repair is not None:
        note = fixit_felix.repair_note(time_value_repair)
        runtime.candy(
            "Cowsay",
            "I found impossible tIME timestamp values, so I am normalizing them before libpng gets the final word.",
            "com",
        )
        runtime.side_notes.append(note)
        return True, runtime.write_clone(time_value_repair.data.hex(), note)

    text_null_repair = fixit_felix.text_null_bytes(png_bytes, findings)
    if text_null_repair is not None:
        note = fixit_felix.repair_note(text_null_repair)
        runtime.candy(
            "Cowsay",
            "I found null bytes inside tEXt metadata, so I am removing them before libpng gets the final word.",
            "com",
        )
        runtime.side_notes.append(note)
        return True, runtime.write_clone(text_null_repair.data.hex(), note)

    idat_interruption_repair = fixit_felix.idat_interruption_cleanup(png_bytes, findings)
    if isinstance(idat_interruption_repair, png.IdatInterruptionRepairPlan):
        should_return, result = _apply_idat_interruption_plan_before_libpng(
            runtime,
            idat_interruption_repair,
        )
        if should_return:
            return True, result

    if any(_is_chunk_order_finding(finding) for finding in findings):
        rustine = no_next_missplaced_tools(runtime)
        if rustine is not None and len(rustine) >= 3:
            runtime.candy(
                "Cowsay",
                "I found a chunk-order repair path, so I am trying TheGoodPlace before calling this perfect.",
                "com",
            )
            return True, runtime.the_good_place(rustine[0], rustine[1], rustine[2])

    runtime.candy("Cowsay", messages.UNIMPLEMENTED_REPAIR_ROUTE_MESSAGE, "bad")
    runtime.the_end()
    return False, None


def apply_no_next_false_positive_iend(
    runtime: NoNextChunkRuntime,
    decision: fixit_felix.NoNextFalsePositiveIendDecision,
) -> tuple[bool, Any]:
    if decision.action in ("libpng_check", "the_good_place", "continue"):
        mark_no_next_iend_reached(runtime)

        if decision.action == "libpng_check":
            unresolved = unresolved_non_no_next_findings(runtime)
            if unresolved:
                return stop_before_libpng_for_unresolved_findings(runtime, unresolved)
            deferred_applied, deferred_result = apply_deferred_linefeed_after_chunk_tour(
                runtime
            )
            if deferred_applied:
                return True, deferred_result
            runtime.candy("Cowsay", "Ok let's feed the Kraken now..", "com")
            return True, runtime.libpng_check(runtime.sample)

        if decision.action == "the_good_place":
            rustine = no_next_missplaced_tools(runtime)
            if rustine is not None and len(rustine) >= 3:
                runtime.candy("Cowsay", "But the fun isnt over yet..", "com")
                return True, runtime.the_good_place(rustine[0], rustine[1], rustine[2])
            runtime.candy(
                "Cowsay",
                "I still have an unrepaired misplaced chunk on the table. No Kraken snack until that mess is handled.",
                "bad",
            )
            runtime.side_notes.append(
                "-Stopped before libpng: unresolved misplaced chunk remains after IDAT."
            )
            runtime.the_end()
            return False, None

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
        has_missplaced_finding=any(
            "missplaced" in str(pandora_key).lower() for pandora_key in runtime.pandora_box
        ),
    )
    return apply_no_next_false_positive_iend(runtime, false_positive_decision)


def handle_no_next_wrong_iend_length(runtime: NoNextChunkRuntime) -> tuple[bool, None]:
    runtime.emit(
        "-%s length for IEND %s "
        % (runtime.candy("Color", "red", "Wrong"), runtime.candy("Chunky", "bad"))
    )
    runtime.candy(
        "Cowsay",
        "IEND is supposed to be empty. This one packed a byte like it was going on vacation.",
        "bad",
    )
    runtime.candy(
        "Cowsay",
        "I am rebuilding the final IEND chunk with zero length and the canonical CRC.",
        "com",
    )
    try:
        repair = png.repair_iend_length(bytes.fromhex(runtime.data_hex))
    except ValueError:
        repair = None
    if repair is None:
        runtime.emit(runtime.candy("Color", "yellow", "\n-ToDo"))
        runtime.side_notes.append("-Wrong length for IEND")
        runtime.the_end()
        return False, None

    note = "-FixItFelix:%s." % repair.strategy
    runtime.side_notes.append(note)
    return True, runtime.write_clone(repair.data, note)


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


def _is_idat_label(value: Any) -> bool:
    if isinstance(value, bytes):
        return value == b"IDAT"
    return str(value) == "IDAT"


def _data_hex_mentions_idat(data_hex: Any) -> bool:
    return "49444154" in str(data_hex).lower()


def no_next_has_idat_evidence(
    runtime: NoNextChunkRuntime,
    current_chunk: Any,
    tools: relics.NoNextChunkTools | None,
) -> bool:
    if _data_hex_mentions_idat(runtime.data_hex):
        return True
    labels = [current_chunk]
    labels.extend(runtime.chunks_history)
    if tools is not None:
        labels.extend((tools.chunk_type, tools.previous_chunk))
    return any(_is_idat_label(label) for label in labels)


def handle_no_next_missing_idat_terminal(
    runtime: NoNextChunkRuntime,
) -> tuple[bool, Any]:
    runtime.candy(
        "Cowsay",
        "No IDAT chunk, no image stream. This is not a repair job, this is PNG paperwork with the picture missing.",
        "bad",
    )
    runtime.candy(
        "Cowsay",
        "I can fix bent chunks, but I cannot invent the compressed pixels that never showed up.",
        "com",
    )
    runtime.side_notes.append("-Critical Chunk b'IDAT' is Missing")
    runtime.side_notes.append("-Terminal PNG error: no IDAT chunk found; no image data to repair.")
    runtime.set_skip_bad_no_next_chunk(True)
    runtime.set_eof(True)
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

    if not no_next_has_idat_evidence(runtime, getattr(decision, "current_chunk", None), tools):
        return handle_no_next_missing_idat_terminal(runtime)

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

    if decision.action == "idat_decision_gate":
        runtime.candy(
            "Cowsay",
            "libpng confirms that the IDAT stream is not feeding the image cleanly.",
            "bad",
        )
        if runtime.try_idat_decision_gate is not None:
            gated = runtime.try_idat_decision_gate(decision.finding)
            if gated is not None:
                return gated
        runtime.candy("Cowsay", "Well this is as far as i could get for now. ", "bad")
        runtime.candy("Cowsay", "At least I was able to get some pixels out of it.", "com")
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
