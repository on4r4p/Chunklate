from __future__ import annotations

import binascii
from dataclasses import dataclass
from dataclasses import replace
import hashlib
import itertools
import json
import math
import multiprocessing
from pathlib import Path
import random
import time
from typing import Any
from typing import Callable

from . import bruteforce
from . import bruteforce_runtime
from . import deflate_header
from . import fixit_felix
from . import gpu_runtime
from . import idat
from . import idat_bruteforce
from . import idat_crc_forge
from . import idat_chain
from . import messages
from . import output
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
    file_dir: Any = ""
    interactive: bool = False
    retry_state: dict[str, Any] | None = None
    input_func: Callable[[str], str] | None = None
    ultimate_linefeed_reference: Callable[[], str] = lambda: ""
    ultimate_linefeed_reference_mode: Callable[[], str] = lambda: ""
    ultimate_linefeed_reference_regions: Callable[[], str] = lambda: ""
    ultimate_linefeed_reference_region_editor_run: Callable[..., Any] | None = None
    set_ultimate_linefeed_reference: Callable[[str], Any] | None = None
    set_ultimate_linefeed_reference_mode: Callable[[str], Any] | None = None
    set_ultimate_linefeed_reference_regions: Callable[[str], Any] | None = None
    smash_brute_brawl_force_level: int | None = None
    smash_brute_brawl_crc_forge: str = "auto"
    set_idat_deflate_route_consumed: Callable[[bool], Any] | None = None


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
    preview_repair_image: Callable[..., Any] | None = None
    file_origin: Any = ""
    file_dir: Any = ""
    interactive: bool = False
    input_func: Callable[[str], str] | None = None
    deep_beam_workers: Any = None
    deep_beam_gpu: Any = None
    deep_beam_gpu_config: Any = None
    deep_beam_budget: Any = None
    deep_beam_max_depth: Any = None
    final_investigation_budget: Any = None
    final_investigation_max_depth: Any = None
    final_investigation_seed_limit: Any = None
    deep_beam_gpu_shard_size: Any = None
    deep_beam_cpu_batch_size: Any = None
    deep_beam_prompt_cache: dict[str, Any] | None = None
    huffman_oracle_budget: Any = None
    crc_periodic_budget: Any = None
    huffman_kraft_budget: Any = None
    huffman_kraft_workers: Any = None
    huffman_kraft_gpu_config: Any = None
    kraft_backref_budget: Any = None
    stored_block_budget: Any = None
    global_crc_residue_budget: Any = None
    affine_corruption_budget: Any = None
    deflate_salvage_budget: Any = None
    seed_local_continuation_limit: Any = None
    seed_local_continuation_budget: Any = None
    seed_local_continuation_rounds: Any = None
    groundhogday_seed_pool_limit: Any = None
    prefinal_repair_cycles: Any = None
    prefinal_repair_batches: Any = None
    ultimate_linefeed_budget: Any = None
    ultimate_linefeed_unbounded: Any = None
    ultimate_linefeed_workers: Any = None
    ultimate_linefeed_max_depth: Any = None
    ultimate_linefeed_max_offsets: Any = None
    groundhogday_visual_guard: Any = None
    set_idat_deflate_route_consumed: Callable[[bool], Any] | None = None


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
    file_origin: Any = ""
    file_dir: Any = ""
    interactive: bool = False
    input_func: Callable[[str], str] | None = None
    deep_beam_workers: Any = None
    deep_beam_gpu: Any = None
    deep_beam_gpu_config: Any = None
    deep_beam_budget: Any = None
    deep_beam_max_depth: Any = None
    final_investigation_budget: Any = None
    final_investigation_max_depth: Any = None
    final_investigation_seed_limit: Any = None
    deep_beam_gpu_shard_size: Any = None
    deep_beam_cpu_batch_size: Any = None
    deep_beam_prompt_cache: dict[str, Any] | None = None
    huffman_oracle_budget: Any = None
    crc_periodic_budget: Any = None
    huffman_kraft_budget: Any = None
    huffman_kraft_workers: Any = None
    huffman_kraft_gpu_config: Any = None
    kraft_backref_budget: Any = None
    stored_block_budget: Any = None
    global_crc_residue_budget: Any = None
    affine_corruption_budget: Any = None
    deflate_salvage_budget: Any = None
    seed_local_continuation_limit: Any = None
    seed_local_continuation_budget: Any = None
    seed_local_continuation_rounds: Any = None
    groundhogday_seed_pool_limit: Any = None
    prefinal_repair_cycles: Any = None
    prefinal_repair_batches: Any = None
    ultimate_linefeed_budget: Any = None
    ultimate_linefeed_unbounded: Any = None
    ultimate_linefeed_workers: Any = None
    ultimate_linefeed_max_depth: Any = None
    ultimate_linefeed_max_offsets: Any = None
    groundhogday_visual_guard: Any = None
    queue_existing_clone: Callable[[str], Any] | None = None
    set_idat_deflate_route_consumed: Callable[[bool], Any] | None = None


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
    file_origin: Any = ""
    file_dir: Any = ""
    has_deferred_linefeed_repair: Callable[[], bool] = lambda: False
    apply_deferred_linefeed_repair: Callable[[], Any] | None = None
    interactive: bool = False
    input_func: Callable[[str], str] | None = None
    deep_beam_workers: Any = None
    deep_beam_gpu: Any = None
    deep_beam_gpu_config: Any = None
    deep_beam_budget: Any = None
    deep_beam_max_depth: Any = None
    final_investigation_budget: Any = None
    final_investigation_max_depth: Any = None
    final_investigation_seed_limit: Any = None
    deep_beam_gpu_shard_size: Any = None
    deep_beam_cpu_batch_size: Any = None
    deep_beam_prompt_cache: dict[str, Any] | None = None
    huffman_oracle_budget: Any = None
    crc_periodic_budget: Any = None
    huffman_kraft_budget: Any = None
    huffman_kraft_workers: Any = None
    huffman_kraft_gpu_config: Any = None
    kraft_backref_budget: Any = None
    stored_block_budget: Any = None
    global_crc_residue_budget: Any = None
    affine_corruption_budget: Any = None
    deflate_salvage_budget: Any = None
    seed_local_continuation_limit: Any = None
    seed_local_continuation_budget: Any = None
    seed_local_continuation_rounds: Any = None
    groundhogday_seed_pool_limit: Any = None
    prefinal_repair_cycles: Any = None
    prefinal_repair_batches: Any = None
    ultimate_linefeed_budget: Any = None
    ultimate_linefeed_unbounded: Any = None
    ultimate_linefeed_workers: Any = None
    ultimate_linefeed_max_depth: Any = None
    ultimate_linefeed_max_offsets: Any = None
    groundhogday_visual_guard: Any = None
    queue_existing_clone: Callable[[str], Any] | None = None
    set_idat_deflate_route_consumed: Callable[[bool], Any] | None = None


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


def queue_existing_clone_from_namespace(namespace: dict[str, Any], path: str) -> str:
    namespace["Sample"] = path
    namespace["CLONESWAR"] = False
    namespace["Have_A_KitKat"] = True
    namespace["CLONE_HANDOFF_PENDING"] = True
    namespace.setdefault("SideNotes", []).append(
        "-Existing clone queued as next sample: %s" % path
    )
    return path


def _namespace_idat_deep_beam_workers(namespace: dict[str, Any]) -> Any:
    workers = namespace.get("IDAT_DEEP_BEAM_WORKERS")
    if workers is None or str(workers).strip() == "":
        workers = namespace.get("IDAT_HUFFMAN_KRAFT_WORKERS")
    return workers


def _namespace_idat_huffman_kraft_workers(namespace: dict[str, Any]) -> Any:
    workers = namespace.get("IDAT_HUFFMAN_KRAFT_WORKERS")
    if workers is None or str(workers).strip() == "":
        workers = namespace.get("IDAT_DEEP_BEAM_WORKERS")
    return workers


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
        preview_repair_image=namespace.get("Preview_Repair_Image"),
        file_origin=namespace.get("FILE_Origin") or namespace.get("Sample") or "",
        file_dir=namespace.get("FILE_DIR") or "",
        interactive=namespace_interactive_prompts(namespace),
        input_func=namespace.get("Transcript_Input") or namespace.get("input") or input,
        deep_beam_workers=_namespace_idat_deep_beam_workers(namespace),
        deep_beam_gpu=namespace.get("IDAT_DEEP_BEAM_GPU"),
        deep_beam_gpu_config=namespace.get("GPU_CONFIG"),
        deep_beam_budget=namespace.get("IDAT_DEEP_BEAM_BUDGET"),
        deep_beam_max_depth=namespace.get("IDAT_DEEP_BEAM_MAX_DEPTH"),
        final_investigation_budget=namespace.get("IDAT_FINAL_INVESTIGATION_BUDGET"),
        final_investigation_max_depth=namespace.get("IDAT_FINAL_INVESTIGATION_MAX_DEPTH"),
        final_investigation_seed_limit=namespace.get("IDAT_FINAL_INVESTIGATION_SEED_LIMIT"),
        deep_beam_gpu_shard_size=namespace.get("IDAT_DEEP_BEAM_GPU_SHARD_SIZE"),
        deep_beam_cpu_batch_size=namespace.get("IDAT_DEEP_BEAM_CPU_BATCH_SIZE"),
        deep_beam_prompt_cache=namespace.setdefault("IDAT_DEEP_BEAM_PROMPT_CACHE", {}),
        huffman_oracle_budget=namespace.get("IDAT_HUFFMAN_ORACLE_BUDGET"),
        crc_periodic_budget=namespace.get("IDAT_CRC_PERIODIC_BUDGET"),
        huffman_kraft_budget=namespace.get("IDAT_HUFFMAN_KRAFT_BUDGET"),
        huffman_kraft_workers=_namespace_idat_huffman_kraft_workers(namespace),
        huffman_kraft_gpu_config=namespace.get("GPU_CONFIG"),
        kraft_backref_budget=namespace.get("IDAT_KRAFT_BACKREF_BUDGET"),
        stored_block_budget=namespace.get("IDAT_STORED_BLOCK_BUDGET"),
        global_crc_residue_budget=namespace.get("IDAT_GLOBAL_CRC_RESIDUE_BUDGET"),
        affine_corruption_budget=namespace.get("IDAT_AFFINE_CORRUPTION_BUDGET"),
        deflate_salvage_budget=namespace.get("IDAT_DEFLATE_SALVAGE_BUDGET"),
        seed_local_continuation_limit=namespace.get("IDAT_SEED_LOCAL_CONTINUATION_LIMIT"),
        seed_local_continuation_budget=namespace.get("IDAT_SEED_LOCAL_CONTINUATION_BUDGET"),
        seed_local_continuation_rounds=namespace.get("IDAT_SEED_LOCAL_CONTINUATION_ROUNDS"),
        groundhogday_seed_pool_limit=namespace.get("IDAT_GROUNDHOGDAY_SEED_POOL_LIMIT"),
        prefinal_repair_cycles=namespace.get("IDAT_PREFINAL_REPAIR_CYCLES"),
        prefinal_repair_batches=namespace.get("IDAT_PREFINAL_REPAIR_BATCHES"),
        ultimate_linefeed_budget=namespace.get("ULTIMATE_LINEFEED_BUDGET"),
        ultimate_linefeed_unbounded=namespace.get("ULTIMATE_LINEFEED_UNBOUNDED"),
        ultimate_linefeed_workers=namespace.get("ULTIMATE_LINEFEED_WORKERS"),
        ultimate_linefeed_max_depth=namespace.get("IDAT_GROUNDHOGDAY_ULTIMATE_LINEFEED_MAX_DEPTH"),
        ultimate_linefeed_max_offsets=namespace.get("IDAT_GROUNDHOGDAY_ULTIMATE_LINEFEED_MAX_OFFSETS"),
        groundhogday_visual_guard=namespace.get("IDAT_GROUNDHOGDAY_VISUAL_GUARD"),
        set_idat_deflate_route_consumed=lambda value: namespace.__setitem__("IDAT_DEFLATE_ROUTE_CONSUMED", value),
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
        file_origin=namespace.get("FILE_Origin") or namespace.get("Sample") or "",
        file_dir=namespace.get("FILE_DIR") or "",
        interactive=namespace_interactive_prompts(namespace),
        input_func=namespace.get("Transcript_Input") or namespace.get("input") or input,
        deep_beam_workers=_namespace_idat_deep_beam_workers(namespace),
        deep_beam_gpu=namespace.get("IDAT_DEEP_BEAM_GPU"),
        deep_beam_gpu_config=namespace.get("GPU_CONFIG"),
        deep_beam_budget=namespace.get("IDAT_DEEP_BEAM_BUDGET"),
        deep_beam_max_depth=namespace.get("IDAT_DEEP_BEAM_MAX_DEPTH"),
        final_investigation_budget=namespace.get("IDAT_FINAL_INVESTIGATION_BUDGET"),
        final_investigation_max_depth=namespace.get("IDAT_FINAL_INVESTIGATION_MAX_DEPTH"),
        final_investigation_seed_limit=namespace.get("IDAT_FINAL_INVESTIGATION_SEED_LIMIT"),
        deep_beam_gpu_shard_size=namespace.get("IDAT_DEEP_BEAM_GPU_SHARD_SIZE"),
        deep_beam_cpu_batch_size=namespace.get("IDAT_DEEP_BEAM_CPU_BATCH_SIZE"),
        deep_beam_prompt_cache=namespace.setdefault("IDAT_DEEP_BEAM_PROMPT_CACHE", {}),
        huffman_oracle_budget=namespace.get("IDAT_HUFFMAN_ORACLE_BUDGET"),
        crc_periodic_budget=namespace.get("IDAT_CRC_PERIODIC_BUDGET"),
        huffman_kraft_budget=namespace.get("IDAT_HUFFMAN_KRAFT_BUDGET"),
        huffman_kraft_workers=_namespace_idat_huffman_kraft_workers(namespace),
        huffman_kraft_gpu_config=namespace.get("GPU_CONFIG"),
        kraft_backref_budget=namespace.get("IDAT_KRAFT_BACKREF_BUDGET"),
        stored_block_budget=namespace.get("IDAT_STORED_BLOCK_BUDGET"),
        global_crc_residue_budget=namespace.get("IDAT_GLOBAL_CRC_RESIDUE_BUDGET"),
        affine_corruption_budget=namespace.get("IDAT_AFFINE_CORRUPTION_BUDGET"),
        deflate_salvage_budget=namespace.get("IDAT_DEFLATE_SALVAGE_BUDGET"),
        seed_local_continuation_limit=namespace.get("IDAT_SEED_LOCAL_CONTINUATION_LIMIT"),
        seed_local_continuation_budget=namespace.get("IDAT_SEED_LOCAL_CONTINUATION_BUDGET"),
        seed_local_continuation_rounds=namespace.get("IDAT_SEED_LOCAL_CONTINUATION_ROUNDS"),
        groundhogday_seed_pool_limit=namespace.get("IDAT_GROUNDHOGDAY_SEED_POOL_LIMIT"),
        prefinal_repair_cycles=namespace.get("IDAT_PREFINAL_REPAIR_CYCLES"),
        prefinal_repair_batches=namespace.get("IDAT_PREFINAL_REPAIR_BATCHES"),
        ultimate_linefeed_budget=namespace.get("ULTIMATE_LINEFEED_BUDGET"),
        ultimate_linefeed_unbounded=namespace.get("ULTIMATE_LINEFEED_UNBOUNDED"),
        ultimate_linefeed_workers=namespace.get("ULTIMATE_LINEFEED_WORKERS"),
        ultimate_linefeed_max_depth=namespace.get("IDAT_GROUNDHOGDAY_ULTIMATE_LINEFEED_MAX_DEPTH"),
        ultimate_linefeed_max_offsets=namespace.get("IDAT_GROUNDHOGDAY_ULTIMATE_LINEFEED_MAX_OFFSETS"),
        groundhogday_visual_guard=namespace.get("IDAT_GROUNDHOGDAY_VISUAL_GUARD"),
        queue_existing_clone=lambda path: queue_existing_clone_from_namespace(namespace, path),
        set_idat_deflate_route_consumed=lambda value: namespace.__setitem__("IDAT_DEFLATE_ROUTE_CONSUMED", value),
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
        file_origin=namespace.get("FILE_Origin") or namespace.get("Sample") or "",
        file_dir=namespace.get("FILE_DIR") or "",
        has_deferred_linefeed_repair=lambda: bool(namespace.get("DEFERRED_LINEFEED_SIGNATURE_REPAIR")),
        apply_deferred_linefeed_repair=namespace.get("Apply_Deferred_FindMagic_Repair"),
        interactive=namespace_interactive_prompts(namespace),
        input_func=namespace.get("Transcript_Input") or namespace.get("input") or input,
        deep_beam_workers=_namespace_idat_deep_beam_workers(namespace),
        deep_beam_gpu=namespace.get("IDAT_DEEP_BEAM_GPU"),
        deep_beam_gpu_config=namespace.get("GPU_CONFIG"),
        deep_beam_budget=namespace.get("IDAT_DEEP_BEAM_BUDGET"),
        deep_beam_max_depth=namespace.get("IDAT_DEEP_BEAM_MAX_DEPTH"),
        final_investigation_budget=namespace.get("IDAT_FINAL_INVESTIGATION_BUDGET"),
        final_investigation_max_depth=namespace.get("IDAT_FINAL_INVESTIGATION_MAX_DEPTH"),
        final_investigation_seed_limit=namespace.get("IDAT_FINAL_INVESTIGATION_SEED_LIMIT"),
        deep_beam_gpu_shard_size=namespace.get("IDAT_DEEP_BEAM_GPU_SHARD_SIZE"),
        deep_beam_cpu_batch_size=namespace.get("IDAT_DEEP_BEAM_CPU_BATCH_SIZE"),
        deep_beam_prompt_cache=namespace.setdefault("IDAT_DEEP_BEAM_PROMPT_CACHE", {}),
        huffman_oracle_budget=namespace.get("IDAT_HUFFMAN_ORACLE_BUDGET"),
        crc_periodic_budget=namespace.get("IDAT_CRC_PERIODIC_BUDGET"),
        huffman_kraft_budget=namespace.get("IDAT_HUFFMAN_KRAFT_BUDGET"),
        huffman_kraft_workers=_namespace_idat_huffman_kraft_workers(namespace),
        huffman_kraft_gpu_config=namespace.get("GPU_CONFIG"),
        kraft_backref_budget=namespace.get("IDAT_KRAFT_BACKREF_BUDGET"),
        stored_block_budget=namespace.get("IDAT_STORED_BLOCK_BUDGET"),
        global_crc_residue_budget=namespace.get("IDAT_GLOBAL_CRC_RESIDUE_BUDGET"),
        affine_corruption_budget=namespace.get("IDAT_AFFINE_CORRUPTION_BUDGET"),
        deflate_salvage_budget=namespace.get("IDAT_DEFLATE_SALVAGE_BUDGET"),
        seed_local_continuation_limit=namespace.get("IDAT_SEED_LOCAL_CONTINUATION_LIMIT"),
        seed_local_continuation_budget=namespace.get("IDAT_SEED_LOCAL_CONTINUATION_BUDGET"),
        seed_local_continuation_rounds=namespace.get("IDAT_SEED_LOCAL_CONTINUATION_ROUNDS"),
        groundhogday_seed_pool_limit=namespace.get("IDAT_GROUNDHOGDAY_SEED_POOL_LIMIT"),
        prefinal_repair_cycles=namespace.get("IDAT_PREFINAL_REPAIR_CYCLES"),
        prefinal_repair_batches=namespace.get("IDAT_PREFINAL_REPAIR_BATCHES"),
        ultimate_linefeed_budget=namespace.get("ULTIMATE_LINEFEED_BUDGET"),
        ultimate_linefeed_unbounded=namespace.get("ULTIMATE_LINEFEED_UNBOUNDED"),
        ultimate_linefeed_workers=namespace.get("ULTIMATE_LINEFEED_WORKERS"),
        ultimate_linefeed_max_depth=namespace.get("IDAT_GROUNDHOGDAY_ULTIMATE_LINEFEED_MAX_DEPTH"),
        ultimate_linefeed_max_offsets=namespace.get("IDAT_GROUNDHOGDAY_ULTIMATE_LINEFEED_MAX_OFFSETS"),
        groundhogday_visual_guard=namespace.get("IDAT_GROUNDHOGDAY_VISUAL_GUARD"),
        queue_existing_clone=lambda path: queue_existing_clone_from_namespace(namespace, path),
        set_idat_deflate_route_consumed=lambda value: namespace.__setitem__("IDAT_DEFLATE_ROUTE_CONSUMED", value),
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
    smash_brute_brawl_force_level = _coerce_optional_non_negative_int(
        namespace.get("SMASH_BRUTE_BRAWL_FORCE_LEVEL")
    )
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
        file_dir=namespace.get("FILE_DIR") or "",
        interactive=namespace_interactive_prompts(namespace),
        retry_state=namespace.setdefault("_SBB_BLACKFILL_RETRY_STATE", {}),
        input_func=namespace.get("input", input),
        ultimate_linefeed_reference=namespace.get("Ultimate_Linefeed_Reference", lambda: ""),
        ultimate_linefeed_reference_mode=namespace.get("Ultimate_Linefeed_Reference_Mode", lambda: ""),
        ultimate_linefeed_reference_regions=namespace.get("Ultimate_Linefeed_Reference_Regions", lambda: ""),
        ultimate_linefeed_reference_region_editor_run=namespace.get(
            "Ultimate_Linefeed_Reference_Region_Editor_Run"
        ),
        set_ultimate_linefeed_reference=lambda value: namespace.__setitem__(
            "ULTIMATE_LINEFEED_REFERENCE",
            value,
        ),
        set_ultimate_linefeed_reference_mode=lambda value: namespace.__setitem__(
            "ULTIMATE_LINEFEED_REFERENCE_MODE",
            value,
        ),
        set_ultimate_linefeed_reference_regions=lambda value: namespace.__setitem__(
            "ULTIMATE_LINEFEED_REFERENCE_REGIONS",
            value,
        ),
        smash_brute_brawl_force_level=smash_brute_brawl_force_level,
        smash_brute_brawl_crc_forge=str(namespace.get("SMASH_BRUTE_BRAWL_CRC_FORGE") or "auto"),
        set_idat_deflate_route_consumed=lambda value: namespace.__setitem__("IDAT_DEFLATE_ROUTE_CONSUMED", value),
    )


def _coerce_optional_non_negative_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    if parsed < 0:
        return None
    return parsed


def namespace_interactive_prompts(namespace: dict[str, Any]) -> bool:
    configured = namespace.get("INTERACTIVE_REPAIR_PROMPTS")
    if configured is not None:
        return bool(configured)
    if namespace.get("AUTO", False) or namespace.get("NODIALOGUE", False):
        return False

    sys_module = namespace.get("sys")
    stdin = getattr(sys_module, "stdin", None)
    if stdin is None:
        return False
    isatty = getattr(stdin, "isatty", None)
    return bool(isatty is not None and isatty())


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

    runtime.candy("Title", "DaedalusForce IHDR stored CRC")
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


def _is_partial_blackfill_repair(repair: Any) -> bool:
    return (
        isinstance(repair, idat.PartialIdatBlackfillRepair)
        and str(getattr(repair, "strategy", "")).startswith("partial-idat-blackfill")
    )


def _focused_idat_crc_forge_needs_choice(repair: Any) -> bool:
    return str(getattr(repair, "strategy", "")).startswith("focused 4-byte IDAT CRC repair")


def apply_focused_idat_crc_forge_choice(
    runtime: AutomaticRepairRuntime,
    repair: Any,
) -> bool | None:
    applied_repair = fixit_felix.applied_repair(repair)
    error_file_offset = getattr(repair, "error_file_offset", None)
    window_start = getattr(repair, "window_start", None)
    window_end = getattr(repair, "window_end", None)

    if error_file_offset is not None:
        runtime.candy(
            "Cowsay",
            "HermesProbe localized a deflate error near file offset 0x%x." % int(error_file_offset),
            "com",
        )
    runtime.side_notes.append(applied_repair.note)
    runtime.write_clone(applied_repair.data_hex, applied_repair.save_suffix)
    if runtime.preview_repair_image is not None:
        runtime.preview_repair_image(repair.data, "IDAT_CRC_Focused_Preview")
    runtime.candy(
        "Cowsay",
        "I wrote the focused 4-byte IDAT CRC repair clone. Say yes if the preview still holds, or no if blackfill should stay on deck.",
        "com",
    )

    if runtime.question is not None:
        accepted = runtime.question(
            id="IDAT CRC Forge:-Keep the focused 4-byte repair after preview?",
            idhash=(
                "IDAT-focused-crc-forge",
                error_file_offset,
                window_start,
                window_end,
            ),
            skipauto=True,
        )
        if not accepted:
            runtime.side_notes.append(
                "-FixItFelix:focused 4-byte IDAT CRC repair written but not confirmed; keeping blackfill fallback available."
            )
            return None

    runtime.candy(
        "Cowsay",
        automatic_repair_success_message(repair),
        "good",
    )
    return True


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

    crc_bad_chunks = [
        chunk
        for chunk in idat_chunks
        if (binascii.crc32(chunk.chunk_type + chunk.data) & 0xFFFFFFFF) != chunk.crc
    ]
    if crc_bad_chunks:
        return crc_bad_chunks[0]

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
    crc_label = (
        "trusted original IDAT CRC"
        if diagnostic.crc_target_useful
        else "not useful; stored CRC already matches current IDAT bytes or no original target is available"
    )
    reference_line = (
        "\nvisual proof: PNG is structurally valid; visual repair needs a reference/ROI"
        if diagnostic.requires_visual_reference
        else ""
    )
    if not diagnostic.supported:
        return (
            "DaedalusForce IDAT diagnostic:\n"
            "image: unsupported\n"
            "zlib status: %s\n"
            "CRC target: %s\n"
            "DaedalusForce chance: %s - %s\n"
            "HephaestusForge order: %s%s"
            % (
                diagnostic.zlib_status or "unknown",
                crc_label,
                diagnostic.success_estimate,
                diagnostic.success_reason or diagnostic.reason or "no usable IDAT measurement",
                order,
                reference_line,
            ),
            "bad",
        )

    message = (
        "DaedalusForce IDAT diagnostic:\n"
        "image: %sx%s, %s %s-bit\n"
        "IDAT: %s chunks, %s compressed bytes, zlib %s\n"
        "decompressed: expected %s, got %s, missing %s\n"
        "scanlines: %s/%s complete, %s bytes into next scanline\n"
        "CRC target: %s\n"
        "DaedalusForce chance: %s - %s\n"
        "HephaestusForge order: %s%s"
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
            reference_line,
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
        "IDAT partial blackfill:-Launch DaedalusForce on the original IDAT "
        "after writing the blackfill clone? (chance of success: %s)"
        % (success_estimate or "unknown")
    )


def _partial_blackfill_hephaestus_question_id(success_estimate: str) -> str:
    return (
        "IDAT partial blackfill:-Launch HephaestusForge after low "
        "chance diagnostic? (chance of success: %s)"
        % (success_estimate or "unknown")
    )


def _sbb_visual_reference_question_id() -> str:
    return "DaedalusForce Visual Reference ROI:-Do you have any similar png by any chance?"


def _sbb_reference_regions_path(runtime: AutomaticRepairRuntime) -> str:
    explicit = str(runtime.ultimate_linefeed_reference_regions() or "")
    if explicit:
        return explicit
    origin = str(runtime.file_origin or "")
    if origin:
        folder = output.clone_folder(origin, str(runtime.file_dir or ""))
        return str(Path(folder) / idat_bruteforce.ULTIMATE_LINEFEED_REFERENCE_REGION_NAME)
    return idat_bruteforce.ULTIMATE_LINEFEED_REFERENCE_REGION_NAME


def _maybe_prepare_sbb_visual_reference(
    runtime: AutomaticRepairRuntime,
    source_data: bytes,
    diagnostic: idat.SmashBruteBrawlIdatDiagnostic,
) -> None:
    if not diagnostic.requires_visual_reference:
        return
    if runtime.question is None:
        return
    if not bool(
        runtime.question(
            id=_sbb_visual_reference_question_id(),
            idhash=(
                "IDAT-partial-blackfill-visual-reference",
                str(runtime.file_origin or ""),
                diagnostic.width,
                diagnostic.height,
                diagnostic.zlib_status,
            ),
            skipauto=True,
        )
    ):
        return
    editor = runtime.ultimate_linefeed_reference_region_editor_run
    if editor is None:
        runtime.candy(
            "Cowsay",
            "I cannot open the ROI selector from this runtime, so HephaestusForge will continue without visual proof.",
            "bad",
        )
        return
    reference_path = str(runtime.ultimate_linefeed_reference() or "")
    regions_path = _sbb_reference_regions_path(runtime)
    try:
        result = editor(
            str(runtime.file_origin or ""),
            reference_path,
            regions_path,
            source_data=source_data,
        )
    except Exception as exc:
        runtime.candy(
            "Cowsay",
            "The ROI selector did not open cleanly: %s" % exc,
            "bad",
        )
        return
    selected_reference = str(getattr(result, "reference_path", "") or reference_path)
    if bool(getattr(result, "saved", False)):
        if selected_reference and runtime.set_ultimate_linefeed_reference is not None:
            runtime.set_ultimate_linefeed_reference(selected_reference)
        if runtime.set_ultimate_linefeed_reference_mode is not None:
            runtime.set_ultimate_linefeed_reference_mode("similar")
        if runtime.set_ultimate_linefeed_reference_regions is not None:
            runtime.set_ultimate_linefeed_reference_regions(regions_path)
        if runtime.retry_state is not None:
            runtime.retry_state["visual_reference"] = selected_reference
            runtime.retry_state["visual_reference_regions"] = regions_path
        runtime.side_notes.append(
            "-FixItFelix: Visual reference ROI saved for DaedalusForce/HephaestusForge: %s"
            % regions_path
        )
        runtime.candy(
            "Cowsay",
            "ROI saved. Chunky now has a visual reference instead of guessing from vibes.",
            "good",
        )
        return
    warning = str(getattr(result, "warning", "") or "ROI selector closed without saving")
    runtime.candy(
        "Cowsay",
        "No ROI saved: %s. HephaestusForge can still run, but visual proof stays unavailable."
        % warning,
        "com",
    )


def _hephaestus_primary_edit_mode(
    diagnostic: idat.SmashBruteBrawlIdatDiagnostic,
) -> str:
    order = diagnostic.hephaestus_order or ("Replace", "Insert", "Remove")
    first = str(order[0])
    return first if first in {"Replace", "Insert", "Remove"} else "Replace"


def _sbb_focus_reason(edit_mode: str) -> str:
    if edit_mode == "Insert":
        return "the measurement points first at missing compressed bytes."
    if edit_mode == "Remove":
        return "the measurement points first at extra compressed bytes."
    return "the measurement points first at changed bytes with the same length."


def _focus_order_from_choice(choice: str, diagnostic_order: tuple[str, ...]) -> tuple[str, ...]:
    clean_order = tuple(
        item for item in diagnostic_order if item in {"Insert", "Remove", "Replace"}
    ) or ("Replace", "Insert", "Remove")
    if choice == "progressive":
        return clean_order
    focus = {
        "insert": "Insert",
        "remove": "Remove",
        "replace": "Replace",
    }.get(choice)
    if focus is None:
        return clean_order
    return (focus,) + tuple(item for item in clean_order if item != focus)


def _ask_sbb_focus_choice(
    runtime: AutomaticRepairRuntime,
    diagnostic: idat.SmashBruteBrawlIdatDiagnostic,
) -> str:
    order = tuple(diagnostic.hephaestus_order or ("Replace", "Insert", "Remove"))
    recommended_edit = _hephaestus_primary_edit_mode(diagnostic)
    recommended_choice = {
        "Insert": "1",
        "Remove": "2",
        "Replace": "3",
    }.get(recommended_edit, "4")
    focus_name = {
        "1": "Insert focus",
        "2": "Remove focus",
        "3": "Replace focus",
        "4": "Progressive campaign",
    }[recommended_choice]
    if runtime.retry_state is not None:
        runtime.retry_state["diagnostic_order"] = order
        runtime.retry_state["campaign_focus"] = {
            "1": "insert",
            "2": "remove",
            "3": "replace",
            "4": "progressive",
        }[recommended_choice]
        runtime.retry_state["hephaestus_order"] = _focus_order_from_choice(
            str(runtime.retry_state.get("campaign_focus") or "progressive"),
            order,
        )
    if not runtime.interactive or runtime.input_func is None:
        return str(runtime.retry_state.get("campaign_focus") if runtime.retry_state else "progressive")

    runtime.candy(
        "Cowsay",
        "Chunky recommends %s because %s" % (focus_name, _sbb_focus_reason(recommended_edit)),
        "com",
    )
    runtime.candy(
        "Cowsay",
        "\n".join(
            [
                "Choose the DaedalusForce focus:",
                "1. Insert focus%s" % (" (recommended)" if recommended_choice == "1" else ""),
                "2. Remove focus%s" % (" (recommended)" if recommended_choice == "2" else ""),
                "3. Replace focus%s" % (" (recommended)" if recommended_choice == "3" else ""),
                "4. Progressive campaign%s" % (" (recommended)" if recommended_choice == "4" else ""),
                "",
                "Empty keeps the recommendation.",
            ]
        ),
        "com",
    )
    prompt = "DaedalusForce focus [%s %s] > " % (recommended_choice, focus_name)
    choices = {
        "1": "insert",
        "insert": "insert",
        "2": "remove",
        "remove": "remove",
        "3": "replace",
        "replace": "replace",
        "4": "progressive",
        "progressive": "progressive",
        "": {
            "1": "insert",
            "2": "remove",
            "3": "replace",
            "4": "progressive",
        }[recommended_choice],
    }
    while True:
        try:
            choice = str(runtime.input_func(prompt)).strip().lower()
        except EOFError:
            choice = ""
        focus = choices.get(choice)
        if focus is not None:
            if runtime.retry_state is not None:
                runtime.retry_state["campaign_focus"] = focus
                runtime.retry_state["hephaestus_order"] = _focus_order_from_choice(focus, order)
            return focus
        runtime.candy(
            "Cowsay",
            "Choose 1, 2, 3, 4, or leave it empty. Tiny paperwork, huge consequences.",
            "com",
        )


def _edit_mode_from_sbb_focus(focus: str, diagnostic: idat.SmashBruteBrawlIdatDiagnostic) -> str:
    if focus == "insert":
        return "Insert"
    if focus == "remove":
        return "Remove"
    if focus == "replace":
        return "Replace"
    return _hephaestus_primary_edit_mode(diagnostic)


def _partial_blackfill_bruteforce_question(
    runtime: AutomaticRepairRuntime,
    repair: idat.PartialIdatBlackfillRepair,
    target_chunk: png.PngChunk,
    source_data: bytes,
    crc_target_trusted: bool,
    diagnostic: idat.SmashBruteBrawlIdatDiagnostic | None = None,
) -> str | None:
    runtime.candy(
        "Cowsay",
        "libpng confirms the IDAT does not feed the whole image.",
        "bad",
    )
    if diagnostic is None:
        diagnostic = idat.analyze_sbb_idat_diagnostic(
            source_data,
            crc_target_trusted=crc_target_trusted,
        )
    if diagnostic.requires_visual_reference:
        runtime.candy(
            "Cowsay",
            "This PNG is structurally valid, but visual repair needs a similar reference/ROI.",
            "com",
        )
        runtime.candy(
            "Cowsay",
            "The blackfill clone is an inspection artifact until a reference confirms it.",
            "bad",
        )
    else:
        runtime.candy(
            "Cowsay",
            "The blackfill clone is a valid fallback: %s/%s scanlines are readable."
            % (repair.recovered_scanlines, repair.total_scanlines),
            "good",
        )
    diagnostic_message, diagnostic_mood = _format_sbb_idat_diagnostic(diagnostic)
    runtime.candy("Cowsay", diagnostic_message, diagnostic_mood)
    if not diagnostic.crc_target_useful:
        runtime.candy(
            "Cowsay",
            "CRC is not an oracle for this run. Any DaedalusForce hit must survive full PNG validation, and visual/reference proof if the file already decodes.",
            "com",
        )
    elif str(getattr(runtime, "smash_brute_brawl_crc_forge", "auto") or "auto") != "off":
        runtime.candy(
            "Cowsay",
            "HermesProbe CRC-forge targeted Insert/Replace/Remove 1-20 byte pass will run before broad DaedalusForce.",
            "com",
        )
    twobytes_too_small = _sbb_diagnostic_says_twobytes_is_too_small(diagnostic)
    if twobytes_too_small:
        runtime.candy(
            "Cowsay",
            "Missing decompressed bytes are not compressed bytes I can paste back one-for-one.",
            "com",
        )
        runtime.candy(
            "Cowsay",
            "HermesProbe level 0 probably cannot cover this damage. The blackfill clone is the safer fallback.",
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
            "I can also launch DaedalusForce on the original IDAT bytes, before accepting black rows as the final word.",
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
        if launch_hephaestus:
            _maybe_prepare_sbb_visual_reference(runtime, source_data, diagnostic)
            focus = _ask_sbb_focus_choice(runtime, diagnostic)
            return "hephaestus:%s" % _edit_mode_from_sbb_focus(focus, diagnostic)
        return None

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

    _maybe_prepare_sbb_visual_reference(runtime, source_data, diagnostic)
    focus = _ask_sbb_focus_choice(runtime, diagnostic)
    return "twobytes:%s" % _edit_mode_from_sbb_focus(focus, diagnostic)


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

    _preview_partial_blackfill_repair(runtime, repair, show=False)

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
        "-FixItFelix:launched DaedalusForce on source IDAT after partial blackfill %s/%s."
        % (repair.recovered_scanlines, repair.total_scanlines)
    )
    brute_level = _partial_blackfill_launch_brute_level(runtime, mode_name)
    smash_kwargs: dict[str, Any] = {
        "EditMode": edit_mode,
        "BfMode": "Brutus" if mode_name == "hephaestus" else "TwoBytes",
        "BruteCrc": True,
        "BruteLength": True,
        "BruteLevel": brute_level,
    }
    if runtime.smash_brute_brawl_force_level is not None:
        runtime.side_notes.append(
            "-FixItFelix: DaedalusForce forced to start at brute-force level %s."
            % brute_level
        )
    if mode_name == "hephaestus":
        runtime.side_notes.append(
            "-FixItFelix: low DaedalusForce diagnostic selected HephaestusForge (%s-first)." % edit_mode
        )
    if isinstance(runtime.retry_state, dict):
        runtime.retry_state["disable_resume_once"] = True
        runtime.retry_state["active_pass"] = {
            "edit_mode": edit_mode,
            "bf_mode": smash_kwargs["BfMode"],
            "brute_level": int(smash_kwargs["BruteLevel"]),
        }
    if old_crc is not None:
        smash_kwargs["OldCrc"] = old_crc
        runtime.side_notes.append("-FixItFelix: DaedalusForce will use stored IDAT CRC as target.")
    else:
        runtime.side_notes.append("-FixItFelix: stored IDAT CRC already matches current bytes; using image probe.")
    smash_data_offset = target_chunk.offset * 2
    if mode_name == "twobytes":
        smash_data_offset = (target_chunk.offset + 8) * 2
    runtime.smash_brute_brawl(
        runtime.file_origin or "IDAT",
        "IDAT",
        target_chunk.length,
        smash_data_offset,
        "FixItFelix partial IDAT blackfill HephaestusForge" if mode_name == "hephaestus" else "FixItFelix partial IDAT blackfill",
        **smash_kwargs,
    )


def _partial_blackfill_launch_brute_level(
    runtime: AutomaticRepairRuntime,
    mode_name: str,
) -> int:
    base_level = HEPHAESTUS_INITIAL_BRUTE_LEVEL if mode_name == "hephaestus" else 0
    force_level = runtime.smash_brute_brawl_force_level
    if force_level is None:
        return base_level
    return max(base_level, int(force_level))


def _preview_partial_blackfill_repair(
    runtime: AutomaticRepairRuntime,
    repair: idat.PartialIdatBlackfillRepair,
    *,
    show: bool = False,
) -> None:
    if runtime.preview_repair_image is None:
        return
    try:
        runtime.preview_repair_image(repair.data, "IDAT_Blackfill_Preview", show=show)
    except TypeError:
        runtime.preview_repair_image(repair.data, "IDAT_Blackfill_Preview")


def _partial_blackfill_can_be_final_clone(
    diagnostic: idat.SmashBruteBrawlIdatDiagnostic,
    repair: idat.PartialIdatBlackfillRepair,
) -> bool:
    if int(repair.recovered_scanlines) < int(repair.total_scanlines):
        return False
    if (
        int(diagnostic.expected_decompressed_size) > 0
        and int(diagnostic.decompressed_size) > int(diagnostic.expected_decompressed_size)
    ):
        return False
    if str(diagnostic.recommended_repair_family or "").lower() == "extra":
        return False
    return not bool(diagnostic.requires_visual_reference)


def apply_partial_blackfill_decision(
    runtime: AutomaticRepairRuntime,
    repair: idat.PartialIdatBlackfillRepair,
) -> bool:
    applied_repair = fixit_felix.applied_repair(repair)
    runtime.side_notes.append(applied_repair.note)

    source_data = _source_data_from_runtime(runtime)
    target_chunk = _idat_bruteforce_target(source_data) if source_data is not None else None
    if source_data is None or target_chunk is None:
        runtime.candy(
            "Cowsay",
            automatic_repair_success_message(repair),
            "com",
        )
        runtime.write_clone(applied_repair.data_hex, applied_repair.save_suffix)
        return True

    old_crc = _idat_original_crc_target(target_chunk)
    diagnostic = idat.analyze_sbb_idat_diagnostic(
        source_data,
        crc_target_trusted=old_crc is not None,
    )
    _preview_partial_blackfill_repair(runtime, repair, show=False)
    if runtime.smash_brute_brawl is None:
        if _partial_blackfill_can_be_final_clone(diagnostic, repair):
            runtime.candy(
                "Cowsay",
                automatic_repair_success_message(repair),
                "com",
            )
            runtime.write_clone(applied_repair.data_hex, applied_repair.save_suffix)
        else:
            runtime.side_notes.append(
                "-FixItFelix: partial IDAT blackfill kept as preview-only artifact; visual reference/ROI required before final clone."
            )
            runtime.candy(
                "Cowsay",
                "The blackfill output stays as a preview artifact because visual proof is missing.",
                "com",
            )
        return True

    launch_mode = _partial_blackfill_bruteforce_question(
        runtime,
        repair,
        target_chunk,
        source_data,
        old_crc is not None,
        diagnostic=diagnostic,
    )
    if launch_mode is None:
        if _partial_blackfill_can_be_final_clone(diagnostic, repair):
            runtime.write_clone(applied_repair.data_hex, applied_repair.save_suffix)
            runtime.side_notes.append("-FixItFelix: kept partial IDAT blackfill fallback after diagnostic gate.")
        else:
            runtime.side_notes.append(
                "-FixItFelix: partial IDAT blackfill kept as preview-only artifact after diagnostic gate; no final clone written without visual proof."
            )
            runtime.candy(
                "Cowsay",
                "I kept the blackfill preview, but I am not calling it fixed without reference proof.",
                "com",
            )
        return True
    runtime.side_notes.append(
        "-FixItFelix: partial IDAT blackfill parked as preview while DaedalusForce runs; no final clone written yet."
    )
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
        return (False, None)

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


def _plte_manual_window_from_data(data: bytes) -> tuple[int, int] | None:
    try:
        chunks = tuple(png.iter_chunks(data))
    except png.PngFormatError:
        return None

    plte = next((chunk for chunk in chunks if chunk.chunk_type == b"PLTE"), None)
    if plte is None:
        return None

    start = plte.offset * 2
    end = (plte.offset + 12 + plte.length) * 2
    return start, end


def _plte_manual_window_from_data_hex(data_hex: str) -> tuple[int, int] | None:
    try:
        data = bytes.fromhex(data_hex)
    except ValueError:
        return None
    return _plte_manual_window_from_data(data)


def maybe_offer_manual_plte_editor(runtime: AutomaticRepairRuntime, repair: Any) -> bool | None:
    prompt = _grayscale_plte_rebuild_prompt(repair)
    if prompt is None:
        return None
    if not runtime.interactive:
        return None
    if runtime.question is None or runtime.tk_manual_plte is None:
        return None

    repair_data = getattr(repair, "data", None)
    if not isinstance(repair_data, bytes):
        return None

    validation = png.validate_png_structure(repair_data)
    if not validation.ok:
        runtime.side_notes.append(
            "-FixItFelix:skipped Tkinter PLTE editor because repaired PLTE preview is not structurally valid: %s."
            % "; ".join(validation.errors)
        )
        return None

    window = _plte_manual_window_from_data(repair_data)
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
        repair_data.hex(),
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
    if strategy.startswith("focused 4-byte IDAT CRC repair"):
        if "PLTE" in strategy:
            return (
                "HermesProbe localized a deflate error near a single bad IDAT CRC. I am "
                "keeping the focused 4-byte repair clone after chaining the palette cleanup before blackfill."
            )
        return (
            "HermesProbe localized a deflate error near a single bad IDAT CRC. I am "
            "keeping the focused 4-byte repair clone before blackfill gets a chance to run."
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
        return (False, None)

    if _chrm_repair_needs_choice(repair):
        return apply_chrm_inference_choice(runtime, repair)
    if _zero_scanline_blackfill_needs_choice(repair):
        return apply_zero_scanline_blackfill_choice(runtime, repair)
    if _is_partial_blackfill_repair(repair):
        return apply_partial_blackfill_decision(runtime, repair)
    if _focused_idat_crc_forge_needs_choice(repair):
        return apply_focused_idat_crc_forge_choice(runtime, repair)

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


def remember_failed_idat_crc_only_patch(
    runtime: WrongCrcRuntime,
    finding: Any,
    tools: relics.WrongCrcTools,
    validation: WrongCrcPatchValidation,
) -> None:
    runtime.set_idat_crc_patch_failed(True)
    runtime.set_idat_crc_patch_failed_finding(finding)
    runtime.remember_deferred_idat_crc_route(finding, tools)
    remember_deferred_idat_crc_note(runtime, validation)


def already_explained_invalid_idat_crc_only_patch(runtime: WrongCrcRuntime) -> bool:
    return any(
        str(note).startswith("-Deferred IDAT CRC-only patch: zlib stream still invalid:")
        for note in runtime.side_notes
    )


def _runtime_can_write_clone(runtime: Any) -> bool:
    return callable(getattr(runtime, "write_clone", None))


def _consume_idat_deflate_route(runtime: Any) -> None:
    setter = getattr(runtime, "set_idat_deflate_route_consumed", None)
    if callable(setter):
        setter(True)


def _mark_idat_deflate_route_consumed_if_needed(runtime: Any, result: Any) -> None:
    if not (isinstance(result, tuple) and result and result[0] is False):
        return
    _consume_idat_deflate_route(runtime)


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


def _format_idat_queue_progress_counter(stage: str, tested: int, budget: int) -> str:
    tested_text = str(int(tested))
    budget_text = str(int(budget))
    if len(budget_text) > len(tested_text):
        tested_text = tested_text.zfill(len(budget_text))
    return "%s/%s" % (tested_text, budget_text)


def _runtime_idat_queue_progress(runtime: Any):
    minibar = getattr(runtime, "minibar", None)
    if minibar is None:
        return None
    started = time.monotonic()

    def progress(stage: str, tested: int, budget: int) -> None:
        elapsed = max(0.001, time.monotonic() - started)
        rate = float(tested) / elapsed if tested > 0 else 0.0
        remaining = max(0, int(budget) - int(tested))
        eta = (float(remaining) / rate) if rate > 0 else None
        minibar(
            "IDAT %s %s eta=%s rate=%.1f/s"
            % (
                stage,
                _format_idat_queue_progress_counter(stage, tested, budget),
                _format_eta_seconds(eta),
                rate,
            )
        )

    return progress


def _runtime_groundhogday_ultimate_linefeed_progress(runtime: Any):
    progress = _runtime_idat_queue_progress(runtime)
    if progress is None:
        return None

    def mini_progress(stage: str, tested: int, budget: int) -> None:
        if stage == "UltimateMegaSuperLineFeedBruteForce":
            stage = IDAT_GROUNDHOGDAY_MINI_ULTIMATE_LINEFEED_LABEL
        progress(stage, tested, budget)

    return mini_progress


def _bad_crc_idat_chunks(data: bytes) -> tuple[png.PngChunk, ...]:
    try:
        chunks = tuple(png.iter_chunks(data))
    except png.PngFormatError:
        return ()
    return tuple(
        chunk
        for chunk in chunks
        if chunk.chunk_type == b"IDAT" and chunk.crc != chunk.computed_crc
    )


def _focused_idat_crc_window(
    target_chunk: png.PngChunk,
    analysis: idat.IdatStreamAnalysis,
    *,
    byte_count: int = 4,
) -> tuple[int, int] | None:
    if analysis.error_file_offset is None:
        return None
    payload_offset = int(analysis.error_file_offset) - int(target_chunk.offset) - 8
    start = payload_offset - int(byte_count) + 1
    end = start + 1
    if start < 0 or end > len(target_chunk.data):
        return None
    return start, end


def try_focused_idat_crc_forge(
    runtime: Any,
    data: bytes,
    analysis: idat.IdatStreamAnalysis,
) -> tuple[bool, Any] | None:
    if analysis.status != "corrupt_deflate":
        return None
    if analysis.error_file_offset is None:
        return None
    target_chunk = fixit_felix.focused_idat_crc_target_chunk(data, analysis)
    if target_chunk is None:
        return None

    window = _focused_idat_crc_window(target_chunk, analysis, byte_count=4)
    if window is None:
        return None
    start, end = window

    runtime.candy(
        "Cowsay",
        "HermesProbe localized a deflate error near file offset 0x%x." % int(analysis.error_file_offset),
        "com",
    )
    runtime.candy(
        "Cowsay",
        "Trying focused 4-byte IDAT CRC repair around 0x%x before blackfill."
        % int(target_chunk.offset + 8 + start),
        "com",
    )

    old_crc = int(target_chunk.crc).to_bytes(4, "big")
    window_spec = "%s:%s" % (start, end)
    for candidate in idat_crc_forge.iter_forge_candidates(
        data,
        target_chunk,
        old_crc,
        edit_order=("replace",),
        byte_counts=(4,),
        window_spec=window_spec,
        mode="force",
        zlib_prefilter=True,
    ):
        candidate_data = candidate.hit.png_bytes
        candidate_analysis = idat.analyze_idat_stream(candidate_data)
        if not candidate_analysis.complete:
            continue
        finalized = fixit_felix.finalize_focused_idat_crc_candidate(candidate_data)
        if finalized is None:
            continue
        repaired_data, followup_strategy = finalized
        summary = "\n".join(
            (
                "-Repair hypothesis tried: focused 4-byte IDAT CRC forge.",
                idat_stream_diagnosis_note(analysis),
                "HermesProbe localized deflate error near file offset 0x%x."
                % int(analysis.error_file_offset),
                "Focused IDAT payload window: 0x%x..0x%x."
                % (int(start), int(start + 3)),
                "Patch: replace 4 byte(s) at IDAT payload offset 0x%x with %s."
                % (int(candidate.hit.byte_position), candidate.hit.brute_bytes.hex()),
                (
                    "Follow-up repair:%s." % followup_strategy
                    if followup_strategy
                    else "Follow-up repair: none needed."
                ),
                idat_stream_diagnosis_note(candidate_analysis),
            )
        )
        written = runtime.write_clone(repaired_data, summary)
        preview = getattr(runtime, "preview_repair_image", None)
        if preview is not None:
            preview(repaired_data, "IDAT_CRC_Focused_Preview")
        runtime.candy(
            "Cowsay",
            "I wrote the focused 4-byte IDAT CRC repair clone. Say yes if it still holds; no keeps blackfill available.",
            "com",
        )
        answer = runtime.question(
            id="IDAT CRC Forge:-Keep the focused 4-byte repair after preview?",
            idhash=(
                "IDAT-focused-crc-forge",
                int(analysis.error_file_offset),
                int(target_chunk.offset + 8 + start),
                int(target_chunk.offset + 8 + start + 3),
            ),
            skipauto=True,
        )
        if answer is False:
            runtime.side_notes.append(
                "-FixItFelix:focused 4-byte IDAT CRC repair written but not confirmed; keeping blackfill fallback available."
            )
            return None
        runtime.candy(
            "Cowsay",
            "HermesProbe found the four-byte bite mark. Patch: IDAT payload offset 0x%x -> %s."
            % (int(candidate.hit.byte_position), candidate.hit.brute_bytes.hex()),
            "good",
        )
        return True, written

    runtime.side_notes.append(
        "-Focused IDAT CRC forge found no validated 4-byte repair around file offset 0x%x."
        % int(target_chunk.offset + 8 + start)
    )
    return None


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


def _write_idat_diagnostic_artifact(
    runtime: Any,
    candidate: idat_bruteforce.SuperMegaLinefeedCandidate,
    *,
    label: str,
) -> str | None:
    file_origin = str(getattr(runtime, "file_origin", "") or "").strip()
    file_dir = str(getattr(runtime, "file_dir", "") or "")
    if not file_origin:
        runtime.side_notes.append(
            "-IDAT diagnostic artifact skipped: source file origin is unavailable."
        )
        return None
    try:
        folder = Path(output.ensure_clone_folder(file_origin, file_dir))
        payload_folder = folder / "Debug_Payloads"
        payload_folder.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha1(candidate.data).hexdigest()[:8]
        path = payload_folder / (
            "%s_%s_state%s_%s.png"
            % (
                output.repair_stem(file_origin, file_dir),
                label,
                candidate.state_id,
                digest,
            )
        )
        path.write_bytes(candidate.data)
    except Exception as exc:
        runtime.side_notes.append("-IDAT diagnostic artifact write failed: %s." % exc)
        return None

    relative_path = path.relative_to(folder).as_posix()
    runtime.side_notes.append(
        "-IDAT diagnostic artifact: %s; not a final fix; status=%s; scanlines=%s/%s; "
        "decompressed=%s/%s; error_offset=%s."
        % (
            relative_path,
            candidate.after.status,
            candidate.after.usable_scanlines,
            candidate.after.height,
            candidate.after.decompressed_size,
            candidate.after.expected_size,
            candidate.after.error_offset,
        )
    )
    return str(path)


def _idat_deep_beam_paths(runtime: Any) -> tuple[str, str]:
    file_origin = str(getattr(runtime, "file_origin", "") or "").strip()
    file_dir = str(getattr(runtime, "file_dir", "") or "")
    if not file_origin:
        return "", ""
    try:
        folder = Path(output.ensure_clone_folder(file_origin, file_dir))
        payload_folder = folder / "Debug_Payloads"
        payload_folder.mkdir(parents=True, exist_ok=True)
    except Exception:
        return "", ""
    stem = output.repair_stem(file_origin, file_dir)
    checkpoint_path = payload_folder / ("%s_deep_beam.checkpoint.jsonl" % stem)
    progress_path = payload_folder / ("%s_deep_beam.progress.json" % stem)
    return str(checkpoint_path), str(progress_path)


def _idat_periodic_model_paths(runtime: Any) -> tuple[str, str]:
    file_origin = str(getattr(runtime, "file_origin", "") or "").strip()
    file_dir = str(getattr(runtime, "file_dir", "") or "")
    if not file_origin:
        return "", ""
    try:
        folder = Path(output.ensure_clone_folder(file_origin, file_dir))
        payload_folder = folder / "Debug_Payloads"
        payload_folder.mkdir(parents=True, exist_ok=True)
    except Exception:
        return "", ""
    stem = output.repair_stem(file_origin, file_dir)
    checkpoint_path = payload_folder / ("%s_periodic_model.checkpoint.jsonl" % stem)
    progress_path = payload_folder / ("%s_periodic_model.progress.json" % stem)
    return str(checkpoint_path), str(progress_path)


def _idat_huffman_oracle_paths(runtime: Any) -> tuple[str, str]:
    file_origin = str(getattr(runtime, "file_origin", "") or "").strip()
    file_dir = str(getattr(runtime, "file_dir", "") or "")
    if not file_origin:
        return "", ""
    folder = Path(output.ensure_clone_folder(file_origin, file_dir))
    payload_folder = folder / "Debug_Payloads"
    payload_folder.mkdir(parents=True, exist_ok=True)
    stem = output.repair_stem(file_origin, file_dir)
    checkpoint_path = payload_folder / ("%s_huffman_oracle.checkpoint.jsonl" % stem)
    progress_path = payload_folder / ("%s_huffman_oracle.progress.json" % stem)
    return str(checkpoint_path), str(progress_path)


def _idat_crc_periodic_paths(runtime: Any) -> tuple[str, str]:
    file_origin = str(getattr(runtime, "file_origin", "") or "").strip()
    file_dir = str(getattr(runtime, "file_dir", "") or "")
    if not file_origin:
        return "", ""
    folder = Path(output.ensure_clone_folder(file_origin, file_dir))
    payload_folder = folder / "Debug_Payloads"
    payload_folder.mkdir(parents=True, exist_ok=True)
    stem = output.repair_stem(file_origin, file_dir)
    checkpoint_path = payload_folder / ("%s_crc_periodic.checkpoint.jsonl" % stem)
    progress_path = payload_folder / ("%s_crc_periodic.progress.json" % stem)
    return str(checkpoint_path), str(progress_path)


def _idat_frontier_paths(runtime: Any, label: str) -> tuple[str, str]:
    file_origin = str(getattr(runtime, "file_origin", "") or "").strip()
    file_dir = str(getattr(runtime, "file_dir", "") or "")
    if not file_origin:
        return "", ""
    folder = Path(output.ensure_clone_folder(file_origin, file_dir))
    payload_folder = folder / "Debug_Payloads"
    payload_folder.mkdir(parents=True, exist_ok=True)
    stem = output.repair_stem(file_origin, file_dir)
    checkpoint_path = payload_folder / ("%s_%s.checkpoint.jsonl" % (stem, label))
    progress_path = payload_folder / ("%s_%s.progress.json" % (stem, label))
    return str(checkpoint_path), str(progress_path)


def _idat_affine_corruption_paths(runtime: Any) -> tuple[str, str]:
    return _idat_frontier_paths(runtime, "affine_corruption")


def _idat_huffman_kraft_paths(runtime: Any) -> tuple[str, str]:
    return _idat_frontier_paths(runtime, "huffman_kraft")


def _idat_first_filter_literal_paths(runtime: Any) -> tuple[str, str]:
    return _idat_frontier_paths(runtime, "first_filter_literal")


def _idat_kraft_backref_paths(runtime: Any) -> tuple[str, str]:
    return _idat_frontier_paths(runtime, "kraft_backref")


def _idat_stored_block_paths(runtime: Any) -> tuple[str, str]:
    return _idat_frontier_paths(runtime, "stored_block")


def _idat_global_crc_residue_paths(runtime: Any) -> tuple[str, str]:
    return _idat_frontier_paths(runtime, "global_crc_residue")


def _idat_deflate_salvage_paths(runtime: Any) -> tuple[str, str]:
    return _idat_frontier_paths(runtime, "deflate_salvage")


def _idat_groundhogday_ultimate_linefeed_paths(runtime: Any) -> tuple[str, str]:
    return _idat_frontier_paths(runtime, "groundhogday_ultimate_linefeed")


def _idat_deflate_salvage_preview_path(runtime: Any) -> str:
    file_origin = str(getattr(runtime, "file_origin", "") or "").strip()
    file_dir = str(getattr(runtime, "file_dir", "") or "")
    if not file_origin:
        return ""
    try:
        folder = Path(output.ensure_clone_folder(file_origin, file_dir))
        payload_folder = folder / "Debug_Payloads"
        payload_folder.mkdir(parents=True, exist_ok=True)
    except Exception:
        return ""
    stem = output.repair_stem(file_origin, file_dir)
    return str(payload_folder / ("%s_deflate_salvage_preview.ppm" % stem))


def _idat_convoy_model_path(runtime: Any) -> str:
    file_origin = str(getattr(runtime, "file_origin", "") or "").strip()
    file_dir = str(getattr(runtime, "file_dir", "") or "")
    if not file_origin:
        return ""
    try:
        folder = Path(output.ensure_clone_folder(file_origin, file_dir))
        payload_folder = folder / "Debug_Payloads"
        payload_folder.mkdir(parents=True, exist_ok=True)
    except Exception:
        return ""
    stem = output.repair_stem(file_origin, file_dir)
    return str(payload_folder / ("%s_idat_convoy_model.json" % stem))


def _deep_beam_workers_from_profile(value: Any) -> str | int:
    if value is None:
        return "auto"
    if isinstance(value, int):
        return max(1, value)
    choice = str(value).strip().lower()
    if choice in ("", "auto"):
        return "auto"
    cpu_count = max(1, multiprocessing.cpu_count())
    if choice == "min":
        return max(1, cpu_count // 4)
    if choice == "normal":
        return max(1, min(idat_bruteforce.DEEP_BEAM_AUTO_WORKER_LIMIT, cpu_count // 2))
    if choice == "max":
        return max(1, cpu_count - 1)
    if choice in ("1", "single", "off", "disabled", "0"):
        return 1
    try:
        return max(1, int(choice))
    except ValueError:
        return "auto"


def _deep_beam_gpu_from_value(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "y", "on", "gpu", "opengl", "cuda", "opencl")
    return bool(value)


def _deep_beam_positive_int(value: Any, default: int) -> int:
    if value is None or str(value).strip() == "":
        return int(default)
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return int(default)


def _deep_beam_non_negative_int(value: Any, default: int) -> int:
    if value is None or str(value).strip() == "":
        return int(default)
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return int(default)


def _runtime_deep_beam_budget(runtime: Any) -> int:
    return _deep_beam_positive_int(
        getattr(runtime, "deep_beam_budget", None),
        idat_bruteforce.DEEP_BEAM_DEFAULT_BUDGET,
    )


def _runtime_deep_beam_max_depth(
    runtime: Any,
    resume_state: idat_bruteforce.IdatDeepBeamResumeState | None = None,
) -> tuple[int, bool]:
    configured = getattr(runtime, "deep_beam_max_depth", None)
    configured_text = "" if configured is None else str(configured).strip()
    explicit = configured_text != ""
    max_depth = _deep_beam_non_negative_int(
        configured,
        idat_bruteforce.DEEP_BEAM_DEFAULT_MAX_DEPTH,
    )
    auto_bumped = False
    if explicit or resume_state is None:
        return max_depth, auto_bumped
    if not (resume_state.available and resume_state.source_matches):
        return max_depth, auto_bumped

    if resume_state.max_depth > max_depth:
        max_depth = int(resume_state.max_depth)
    if resume_state.hard_depth_reached and resume_state.depth >= max_depth:
        max_depth = int(resume_state.depth) + 1
        auto_bumped = True
    return max_depth, auto_bumped


def _runtime_huffman_oracle_budget(runtime: Any) -> int:
    return _deep_beam_positive_int(
        getattr(runtime, "huffman_oracle_budget", None),
        idat_bruteforce.HUFFMAN_ORACLE_DEFAULT_BUDGET,
    )


def _runtime_crc_periodic_budget(runtime: Any) -> int:
    return _deep_beam_positive_int(
        getattr(runtime, "crc_periodic_budget", None),
        idat_bruteforce.CRC_PERIODIC_DEFAULT_BUDGET,
    )


def _runtime_huffman_kraft_budget(runtime: Any) -> int:
    return _deep_beam_positive_int(
        getattr(runtime, "huffman_kraft_budget", None),
        idat_bruteforce.HUFFMAN_KRAFT_DEFAULT_BUDGET,
    )


def _runtime_kraft_backref_budget(runtime: Any) -> int:
    return _deep_beam_positive_int(
        getattr(runtime, "kraft_backref_budget", None),
        idat_bruteforce.KRAFT_BACKREF_DEFAULT_BUDGET,
    )


def _runtime_stored_block_budget(runtime: Any) -> int:
    return _deep_beam_positive_int(
        getattr(runtime, "stored_block_budget", None),
        idat_bruteforce.STORED_BLOCK_DEFAULT_BUDGET,
    )


def _runtime_huffman_kraft_workers(runtime: Any) -> Any:
    value = getattr(runtime, "huffman_kraft_workers", None)
    if value is None or str(value).strip() == "":
        value = getattr(runtime, "deep_beam_workers", None)
    if value is None or str(value).strip() == "":
        return "auto"
    return value


def _runtime_huffman_kraft_gpu_config(runtime: Any) -> gpu_runtime.GpuRuntimeConfig:
    configured = getattr(runtime, "huffman_kraft_gpu_config", None)
    if isinstance(configured, gpu_runtime.GpuRuntimeConfig):
        return configured
    configured = getattr(runtime, "deep_beam_gpu_config", None)
    if isinstance(configured, gpu_runtime.GpuRuntimeConfig):
        return configured
    return gpu_runtime.GpuRuntimeConfig()


def _runtime_global_crc_residue_budget(runtime: Any) -> int:
    return _deep_beam_positive_int(
        getattr(runtime, "global_crc_residue_budget", None),
        idat_bruteforce.GLOBAL_CRC_RESIDUE_DEFAULT_BUDGET,
    )


def _runtime_affine_corruption_budget(runtime: Any) -> int:
    return _deep_beam_positive_int(
        getattr(runtime, "affine_corruption_budget", None),
        idat_bruteforce.AFFINE_CORRUPTION_DEFAULT_BUDGET,
    )


def _runtime_deflate_salvage_budget(runtime: Any) -> int:
    return _deep_beam_positive_int(
        getattr(runtime, "deflate_salvage_budget", None),
        idat_bruteforce.DEFLATE_SALVAGE_DEFAULT_BUDGET,
    )


def _runtime_seed_local_continuation_limit(runtime: Any) -> int:
    return _deep_beam_positive_int(
        getattr(runtime, "seed_local_continuation_limit", None),
        IDAT_SEED_LOCAL_CONTINUATION_LIMIT,
    )


def _runtime_seed_local_continuation_budget(runtime: Any) -> int:
    return _deep_beam_positive_int(
        getattr(runtime, "seed_local_continuation_budget", None),
        IDAT_SEED_LOCAL_CONTINUATION_BUDGET,
    )


def _runtime_seed_local_continuation_rounds(runtime: Any) -> int:
    return _deep_beam_positive_int(
        getattr(runtime, "seed_local_continuation_rounds", None),
        IDAT_SEED_LOCAL_CONTINUATION_ROUNDS,
    )


def _runtime_groundhogday_ultimate_linefeed_budget(runtime: Any) -> int | None:
    if bool(getattr(runtime, "ultimate_linefeed_unbounded", False)):
        return None
    value = getattr(runtime, "ultimate_linefeed_budget", None)
    if value is not None:
        text = str(value).strip().lower()
        if text in ("0", "off", "false", "no", "disabled"):
            return 0
    return _deep_beam_positive_int(
        value,
        IDAT_GROUNDHOGDAY_ULTIMATE_LINEFEED_DEFAULT_BUDGET,
    )


def _runtime_groundhogday_ultimate_linefeed_budget_explicit(runtime: Any) -> bool:
    if bool(getattr(runtime, "ultimate_linefeed_unbounded", False)):
        return True
    value = getattr(runtime, "ultimate_linefeed_budget", None)
    return value is not None and str(value).strip() != ""


def _runtime_groundhogday_ultimate_linefeed_configured(runtime: Any) -> bool:
    for name in (
        "ultimate_linefeed_budget",
        "ultimate_linefeed_unbounded",
        "ultimate_linefeed_workers",
        "ultimate_linefeed_max_depth",
        "ultimate_linefeed_max_offsets",
    ):
        value = getattr(runtime, name, None)
        if value is not None and str(value).strip() != "":
            return True
    return False


def _runtime_groundhogday_ultimate_linefeed_max_depth(runtime: Any) -> int:
    return _deep_beam_positive_int(
        getattr(runtime, "ultimate_linefeed_max_depth", None),
        IDAT_GROUNDHOGDAY_ULTIMATE_LINEFEED_MAX_DEPTH,
    )


def _runtime_groundhogday_ultimate_linefeed_max_offsets(runtime: Any) -> int:
    return _deep_beam_positive_int(
        getattr(runtime, "ultimate_linefeed_max_offsets", None),
        IDAT_GROUNDHOGDAY_ULTIMATE_LINEFEED_MAX_OFFSETS,
    )


def _runtime_groundhogday_ultimate_linefeed_workers(runtime: Any) -> int:
    value = getattr(runtime, "ultimate_linefeed_workers", None)
    if value is None or str(value).strip() == "":
        return 0
    return idat_bruteforce._deep_beam_workers(_deep_beam_workers_from_profile(value))


def _runtime_groundhogday_seed_pool_limit(runtime: Any) -> int:
    return max(
        _runtime_seed_local_continuation_limit(runtime),
        _deep_beam_positive_int(
            getattr(runtime, "groundhogday_seed_pool_limit", None),
            IDAT_GROUNDHOGDAY_SEED_POOL_LIMIT,
        ),
    )


def _GroundHogDay_runtime_repair_cycles(runtime: Any) -> int:
    return _deep_beam_positive_int(
        getattr(runtime, "prefinal_repair_cycles", None),
        IDAT_PREFINAL_REPAIR_CYCLES,
    )


def _GroundHogDay_runtime_repair_batches(runtime: Any) -> int:
    return _deep_beam_positive_int(
        getattr(runtime, "prefinal_repair_batches", None),
        IDAT_PREFINAL_REPAIR_BATCHES,
    )


def _runtime_final_investigation_budget(runtime: Any) -> int:
    return _deep_beam_positive_int(
        getattr(runtime, "final_investigation_budget", None),
        FINAL_INVESTIGATION_DEFAULT_BUDGET,
    )


def _runtime_final_investigation_max_depth(runtime: Any) -> int:
    return _deep_beam_non_negative_int(
        getattr(runtime, "final_investigation_max_depth", None),
        FINAL_INVESTIGATION_DEFAULT_MAX_DEPTH,
    )


def _runtime_final_investigation_seed_limit(runtime: Any) -> int:
    return _deep_beam_positive_int(
        getattr(runtime, "final_investigation_seed_limit", None),
        FINAL_INVESTIGATION_DEFAULT_SEED_LIMIT,
    )


def _runtime_final_investigation_configured(runtime: Any) -> bool:
    for name in (
        "final_investigation_budget",
        "final_investigation_max_depth",
        "final_investigation_seed_limit",
    ):
        value = getattr(runtime, name, None)
        if value is not None and str(value).strip() != "":
            return True
    return False


def _runtime_deep_beam_options(runtime: Any) -> tuple[str | int, bool, gpu_runtime.GpuRuntimeConfig, int, int, int]:
    configured_workers = getattr(runtime, "deep_beam_workers", None)
    configured_gpu = getattr(runtime, "deep_beam_gpu", None)
    configured_gpu_config = getattr(runtime, "deep_beam_gpu_config", None)
    prompt_cache = getattr(runtime, "deep_beam_prompt_cache", None)
    if isinstance(prompt_cache, dict):
        if configured_workers is None and "workers" in prompt_cache:
            configured_workers = prompt_cache.get("workers")
        if configured_gpu is None and "gpu" in prompt_cache:
            configured_gpu = prompt_cache.get("gpu")
    budget = _runtime_deep_beam_budget(runtime)
    gpu_shard_size = _deep_beam_positive_int(
        getattr(runtime, "deep_beam_gpu_shard_size", None),
        idat_bruteforce.DEEP_BEAM_DEFAULT_GPU_SHARD_SIZE,
    )
    cpu_batch_size = _deep_beam_positive_int(
        getattr(runtime, "deep_beam_cpu_batch_size", None),
        idat_bruteforce.DEEP_BEAM_DEFAULT_CPU_BATCH_SIZE,
    )
    workers: str | int = _deep_beam_workers_from_profile(configured_workers)
    if isinstance(configured_gpu_config, gpu_runtime.GpuRuntimeConfig):
        gpu_config = configured_gpu_config
    else:
        gpu_config = gpu_runtime.GpuRuntimeConfig(enabled=_deep_beam_gpu_from_value(configured_gpu))
    if configured_gpu is None:
        gpu_requested = bool(gpu_config.enabled)
    else:
        gpu_requested = _deep_beam_gpu_from_value(configured_gpu)
        gpu_config = replace(gpu_config, enabled=gpu_requested)

    input_func = getattr(runtime, "input_func", None)
    if getattr(runtime, "interactive", False) and input_func is not None:
        if configured_workers is None:
            cpu_count = max(1, multiprocessing.cpu_count())
            runtime.candy(
                "Cowsay",
                "\n".join(
                    (
                        "Deep IDAT beam worker setup:",
                        "auto. CPU auto, capped at %s" % idat_bruteforce.DEEP_BEAM_AUTO_WORKER_LIMIT,
                        "min. CPU / 4",
                        "normal. CPU / 2, capped at %s" % idat_bruteforce.DEEP_BEAM_AUTO_WORKER_LIMIT,
                        "max. CPU - 1",
                        "1. single process",
                        "or enter an exact worker count",
                        "Detected CPU cores: %s" % cpu_count,
                    )
                ),
                "com",
            )
            try:
                answer = input_func("Deep beam worker profile [auto] > ")
            except EOFError:
                answer = "auto"
            if isinstance(prompt_cache, dict):
                prompt_cache["workers"] = answer
            workers = _deep_beam_workers_from_profile(answer)

        if configured_gpu is None and not bool(getattr(gpu_config, "enabled", False)):
            runtime.candy(
                "Cowsay",
                "Deep IDAT beam can use the OpenGL compute backend as a mutation prefilter; CPU workers will still validate candidates.",
                "com",
            )
            try:
                answer = str(input_func("Enable OpenGL GPU prefilter for deep beam? [no] > ")).strip().lower()
            except EOFError:
                answer = ""
            gpu_requested = answer in ("1", "true", "yes", "y", "on", "gpu", "opengl", "cuda", "opencl")
            if isinstance(prompt_cache, dict):
                prompt_cache["gpu"] = "yes" if gpu_requested else "no"
            if gpu_requested:
                gpu_config = gpu_runtime.GpuRuntimeConfig(enabled=True, backend="opengl")

    if gpu_requested and not gpu_config.enabled:
        gpu_config = gpu_runtime.GpuRuntimeConfig(enabled=True, backend="opengl")

    worker_count = idat_bruteforce._deep_beam_workers(workers)
    runtime.side_notes.append(
        "-IDAT deep beam configuration: workers=%s; gpu_requested=%s; gpu_backend=%s; budget=%s; gpu_shard_size=%s; cpu_batch_size=%s."
        % (
            worker_count,
            "yes" if gpu_requested else "no",
            gpu_config.backend if gpu_requested else "none",
            budget,
            gpu_shard_size,
            cpu_batch_size,
        )
    )
    if gpu_requested:
        runtime.side_notes.append("-IDAT deep beam GPU prefilter enabled; CPU workers remain the validation path.")
    return workers, gpu_requested, gpu_config, budget, gpu_shard_size, cpu_batch_size


IDAT_DEBUG_ARTIFACT_TOP_LIMIT = 8
IDAT_SEED_LOCAL_CONTINUATION_LIMIT = 1
IDAT_SEED_LOCAL_CONTINUATION_BUDGET = 2048
IDAT_SEED_LOCAL_CONTINUATION_ROUNDS = 16
IDAT_PREFINAL_REPAIR_CYCLES = 16
IDAT_PREFINAL_REPAIR_BATCHES = 4
IDAT_GROUNDHOGDAY_SEED_POOL_LIMIT = 32
IDAT_GROUNDHOGDAY_ULTIMATE_LINEFEED_DEFAULT_BUDGET = 50_000
IDAT_GROUNDHOGDAY_ULTIMATE_LINEFEED_AUTO_BUDGET_CAP = 2_000_000
IDAT_GROUNDHOGDAY_ULTIMATE_LINEFEED_MAX_DEPTH = 2
IDAT_GROUNDHOGDAY_ULTIMATE_LINEFEED_MAX_OFFSETS = 256
IDAT_GROUNDHOGDAY_MINI_ULTIMATE_LINEFEED_LABEL = "MiniUltimateMegaSuperLineFeedBruteForce"
GROUNDHOGDAY_VISUAL_GUARD_DEFAULT = "balanced"
GROUNDHOGDAY_VISUAL_GUARD_CHOICES = {"off", "structure", "balanced", "strict"}
FINAL_INVESTIGATION_LABEL = "Punxsutawney Phil's shadow finder"
FINAL_INVESTIGATION_DEFAULT_BUDGET = 100_000_000
FINAL_INVESTIGATION_DEFAULT_MAX_DEPTH = 96
FINAL_INVESTIGATION_DEFAULT_SEED_LIMIT = 128
GROUNDHOGDAY_SCANLINE_PREVIEW_FOLDER = "GroundHogDay_Scanline_Previews"


@dataclass(frozen=True)
class GroundHogDayVisualScore:
    supported: bool
    passed: bool
    profile: str
    visual_score: int
    penalty: int
    usable_scanlines: int
    complete_scanlines: int
    invalid_filter_rows: int
    entropy: float = 0.0
    row_delta: float = 0.0
    repeated_row_ratio: float = 0.0
    filter_transition_ratio: float = 0.0
    palette_ok: bool = True
    reasons: tuple[str, ...] = ()


GROUNDHOGDAY_QUOTES: tuple[tuple[str, str], ...] = (
    ("good", "Okay, campers, rise and shine, and don't forget your booties 'cause it's cooooold out there today."),
    ("good", "It's coooold out there every day. What is this, Miami Beach?"),
    ("com", "Not hardly. And you know, you can expect hazardous travel later today with that, you know, that, uh, that blizzard thing."),
    ("com", "That blizzard - thing. That blizzard - thing. Oh, well, here's the report! The National Weather Service is calling for a big blizzard thing!"),
    ("good", "Yessss, they are. But you know, there's another reason why today is especially exciting."),
    ("good", "Especially cold!"),
    ("good", "Especially cold, okay, but the big question on everybody's lips...    "),
    ("good", "On their chapped lips..."),
    ("good", "On their chapped lips, right: Do ya think Phil is gonna come out and see his shadow?"),
    ("good", "Morning. Off to see the groundhog?"),
    ("good", "Strike up the music, the band has begun ..The Pennsylvania Polka !"),
    ("good", "Pick out your partner and join in the fun...The Pennsylvania Polka !"),
    ("good", "When Chekhov saw the long winter, he saw a winter bleak and dark and bereft of hope."),
    ("good", "But standing here among the people of Punxsutawney and basking in the warmth of their hearths and hearts, I couldn't imagine a better fate than a long and lustrous winter. From Punxsutawney, it's Phil Connors. So long."),
    ("bad", "This is pitiful. A thousand people freezing their butts off, waiting to worship a RAT. What a hype! "),
    ("good", "Groundhog Day used to mean something in this town. They used to pull the hog out, and they used to eat it! You're hypocrites! All of you! "),
    ("good", "You got a problem with what I'm saying, Larry? Untie your tongue, and you come out here and talk, huh? "),
    ("bad", "Am I upsetting you, princess? You know, you want a prediction about the weather you're asking the wrong Phil. "),
    ("bad", "If the shadow keeps lying, the route gets stopped."),
    ("bad", "I'll give you a winter prediction: it's gonna be cold, it's gonna be gray, and it's gonna last you for the rest of your life!"),
    ("com", "Do you ever have déjà vu?"),
    ("good", "Phil? Hey, Phil? Phil! Phil Connors? Phil Connors, I thought that was you!"),
    ("good", "See, whenever I see an opportunity, I charge it like a bull. 'Ned the Bull', that's me now. "),
    ("good", "You know, I have friends who live and die by the actuarial tables and I say, 'Hey! It's all one big crap-shoot anywho!' "),
    ("good", "Tell me, have you ever heard of single premium life because I think that could really be the ticket for you."),
    ("com", "Whoa-ho-ho! Watch out for that first step! It's a doozy!"),
    ("good", "Phil? Like the groundhog Phil?"),
    ("good", "Look out for your shadow there, buddy"),
    ("bad", "Morrons ..your bus is leaving.."),   
    ("good", "Hey! Phil? Phil? Hey! Phil Connors!"),
    ("good", "Ned?"),
    ("bad", "[Punches Ned in the face]"),
    ("bad", "Once again, the eyes of the nation have turned here to this... tiny village in Western Pennsylvania. Blah, blah, blah, blah!"),
    ("bad", "There is no way that this winter is *ever* going to end as long as this groundhog keeps seeing his shadow."),
    ("good", "I don't see any other way out. He's gotta be stopped. And I have to stop him."),
    ("com", "Don't drive angry. Don't drive angry!"),
    ("com", "It's the same thing your whole life: 'Clean up your room. Stand up straight. Pick up your feet. Take it like a man. Be nice to your sister. Dont mix beer and wine, ever.' "),
    ("com", "Oh yeah: 'Don't drive on the railroad track.'"),
    ("com", "I'm betting he's going to swerve first..."),
    ("bad", "[Phil drives the truck he steals off a cliff to kill both himself and Punxsutawney Phil the groundhog]"),
    ("com", "Do you ever have déjà vu?"),
    ("com", "Do you know what today is?"),
    ("bad", "Today is yesterday again and again.."),
    ("good", "I'm a god"),
    ("com", "I'm *a* god, I'm not *the* God... I don't think."),
    ("com", "I didn't just survive a wreck. I wasn't just blown up yesterday. I have been stabbed, shot, poisoned, frozen, hung, electrocuted, and burned."),
    ("com", "Every morning, I wake up with out a scratch on me, not a dent in the fender. I am an immortal!"),
    ("com", "I killed myself so many times I don't even exist anymore."),
    ("com", "I wake up every day, right here, right in Punxsutawney, and it's always February 2nd, and there's nothing I can do about it."),
    ("com", "Could I have one more of these with some booze in it please?"),
    ("bad", "Well, it's Groundhog Day... again..."),   
)


def _write_idat_deep_beam_debug_artifacts(
    runtime: Any,
    result: Any,
    *,
    label: str = "idat_deep_beam",
    include_dynamic_trace: bool = False,
) -> tuple[str, ...]:
    file_origin = str(getattr(runtime, "file_origin", "") or "").strip()
    file_dir = str(getattr(runtime, "file_dir", "") or "")
    if not file_origin:
        runtime.side_notes.append("-IDAT deep beam artifacts skipped: source file origin is unavailable.")
        return ()
    try:
        folder = Path(output.ensure_clone_folder(file_origin, file_dir))
        payload_folder = folder / "Debug_Payloads"
        payload_folder.mkdir(parents=True, exist_ok=True)
    except Exception as exc:
        runtime.side_notes.append("-IDAT deep beam artifact write failed: %s." % exc)
        return ()

    saved: list[str] = []
    stem = output.repair_stem(file_origin, file_dir)
    for stale_path in payload_folder.glob("%s_%s_rank*" % (stem, label)):
        if stale_path.suffix not in (".png", ".bin", ".json"):
            continue
        try:
            stale_path.unlink()
        except OSError:
            continue
    artifact_candidates = tuple(result.top_candidates[:IDAT_DEBUG_ARTIFACT_TOP_LIMIT])
    skipped_candidates = max(0, len(result.top_candidates) - len(artifact_candidates))
    for rank, candidate in enumerate(artifact_candidates, start=1):
        digest = hashlib.sha1(candidate.data).hexdigest()[:8]
        base = "%s_%s_rank%02d_state%s_%s" % (
            stem,
            label,
            rank,
            candidate.state_id,
            digest,
        )
        png_path = payload_folder / ("%s.png" % base)
        stream_path = payload_folder / ("%s_idat.bin" % base)
        raw_path = payload_folder / ("%s_raw_prefix.bin" % base)
        trace_path = payload_folder / ("%s_dynamic_trace.json" % base)
        try:
            png_path.write_bytes(candidate.data)
            stream_path.write_bytes(candidate.stream)
            raw_path.write_bytes(idat_bruteforce.idat_partial_raw_prefix(candidate.stream).raw)
            if include_dynamic_trace:
                trace = deflate_header.trace_dynamic_header(candidate.stream)
                trace_path.write_text(
                    json.dumps(
                        {
                            "status": trace.status,
                            "summary": trace.summary,
                            "bfinal": trace.bfinal,
                            "btype": trace.btype,
                            "hlit": trace.hlit,
                            "hdist": trace.hdist,
                            "hclen": trace.hclen,
                            "length_count": trace.length_count,
                            "bit_offset": trace.bit_offset,
                            "header_end_bit": trace.header_end_bit,
                            "literal_error": trace.literal_error,
                            "distance_error": trace.distance_error,
                        },
                        sort_keys=True,
                    )
                    + "\n",
                    encoding="utf-8",
                )
        except OSError:
            continue
        saved_items = [
            png_path.relative_to(folder).as_posix(),
            stream_path.relative_to(folder).as_posix(),
            raw_path.relative_to(folder).as_posix(),
        ]
        if include_dynamic_trace:
            saved_items.append(trace_path.relative_to(folder).as_posix())
        saved.extend(saved_items)
    if saved:
        note = "-IDAT deep beam artifacts: %s" % ", ".join(saved[: min(len(saved), 12)])
        if skipped_candidates:
            note += "; skipped %s lower-ranked debug candidate(s) to keep memory and IDE image decoding bounded" % skipped_candidates
        runtime.side_notes.append(note + ".")
    else:
        runtime.side_notes.append("-IDAT deep beam artifacts: no candidate artifacts written.")
    return tuple(saved)


def _idat_candidate_is_complete_clone(candidate: Any) -> bool:
    after = getattr(candidate, "after", None)
    return bool(
        after is not None
        and getattr(after, "supported", True)
        and getattr(after, "complete", False)
    )


def _idat_candidate_diagnostic_note(route_label: str, candidate: Any) -> str:
    after = getattr(candidate, "after", None)
    return (
        "-IDAT %s candidate kept as diagnostic evidence; status=%s; scanlines=%s/%s; "
        "decompressed=%s/%s; not promoted as clone."
        % (
            route_label,
            getattr(after, "status", "unknown"),
            getattr(after, "usable_scanlines", "?"),
            getattr(after, "height", "?"),
            getattr(after, "decompressed_size", "?"),
            getattr(after, "expected_size", "?"),
        )
    )


class _RuntimeWithOverrides:
    def __init__(self, runtime: Any, **overrides: Any) -> None:
        self._runtime = runtime
        self._overrides = overrides

    def __getattr__(self, name: str) -> Any:
        if name in self._overrides:
            return self._overrides[name]
        return getattr(self._runtime, name)


def _coerce_groundhogday_visual_guard_profile(value: Any) -> str:
    text = str(value or "").strip().lower()
    aliases = {
        "": GROUNDHOGDAY_VISUAL_GUARD_DEFAULT,
        "default": GROUNDHOGDAY_VISUAL_GUARD_DEFAULT,
        "auto": GROUNDHOGDAY_VISUAL_GUARD_DEFAULT,
        "balanced": "balanced",
        "balance": "balanced",
        "normal": "balanced",
        "structure": "structure",
        "structural": "structure",
        "noise": "structure",
        "noisy": "structure",
        "random": "structure",
        "strict": "strict",
        "coherent": "strict",
        "visual": "strict",
        "off": "off",
        "false": "off",
        "no": "off",
        "disabled": "off",
        "0": "off",
    }
    return aliases.get(text, GROUNDHOGDAY_VISUAL_GUARD_DEFAULT)


def _GroundHogDay_visual_guard_menu() -> str:
    return "\n".join(
        (
            "GroundHogDay visual guard:",
            "balanced. Prefer coherent scanline recovery, but allow some noisy real images.",
            "structure. Treat random/noisy captures as plausible; score structure and palette only.",
            "strict. Penalize line jumps, high entropy, odd repetition, and color incoherence hard.",
            "off. Do not use the visual guard.",
        )
    )


def _GroundHogDay_visual_guard_profile(runtime: Any) -> str:
    cache = getattr(runtime, "deep_beam_prompt_cache", None)
    if isinstance(cache, dict) and "groundhogday_visual_guard" in cache:
        return _coerce_groundhogday_visual_guard_profile(cache["groundhogday_visual_guard"])

    configured = getattr(runtime, "groundhogday_visual_guard", None)
    configured_text = str(configured or "").strip().lower()
    input_func = getattr(runtime, "input_func", None)
    force_prompt = configured_text in {"ask", "prompt", "choose", "choice"}
    if configured is not None and str(configured).strip() != "":
        profile = (
            GROUNDHOGDAY_VISUAL_GUARD_DEFAULT
            if force_prompt
            else _coerce_groundhogday_visual_guard_profile(configured)
        )
    else:
        profile = GROUNDHOGDAY_VISUAL_GUARD_DEFAULT

    if configured is None or str(configured).strip() == "" or force_prompt:
        runtime.candy("Cowsay", _GroundHogDay_visual_guard_menu(), "com")
        if (getattr(runtime, "interactive", False) or force_prompt) and input_func is not None:
            try:
                answer = str(input_func("GroundHogDay visual profile [balanced] > ")).strip()
            except EOFError:
                answer = ""
            profile = _coerce_groundhogday_visual_guard_profile(answer)
        else:
            runtime.candy(
                "Cowsay",
                "No interactive visual-guard choice is available in this run, so I am using %s. Set IDAT_GROUNDHOGDAY_VISUAL_GUARD=balanced, structure, strict, off, or ask to change it."
                % profile,
                "com",
            )
    else:
        runtime.candy(
            "Cowsay",
            "GroundHogDay visual guard profile is configured as %s."
            % profile,
            "com",
        )

    if isinstance(cache, dict):
        cache["groundhogday_visual_guard"] = profile
    runtime.side_notes.append("-IDAT GroundHogDay visual guard profile: %s." % profile)
    return profile


def _GroundHogDay_plte_entry_count(data: bytes) -> int | None:
    try:
        for chunk in png.iter_chunks(data):
            if chunk.chunk_type == b"PLTE":
                return len(chunk.data) // 3
    except png.PngFormatError:
        return None
    return None


def _GroundHogDay_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts: dict[int, int] = {}
    for value in data:
        counts[value] = counts.get(value, 0) + 1
    total = float(len(data))
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def _GroundHogDay_row_delta(raw_rows: bytes, row_data_size: int, rows: int) -> float:
    if row_data_size <= 0 or rows <= 1:
        return 0.0
    total = 0
    compared = 0
    previous = raw_rows[:row_data_size]
    for row_index in range(1, rows):
        start = row_index * row_data_size
        row = raw_rows[start : start + row_data_size]
        if len(row) != row_data_size:
            break
        total += sum(abs(int(a) - int(b)) for a, b in zip(previous, row))
        compared += row_data_size
        previous = row
    if compared <= 0:
        return 0.0
    return float(total) / float(compared * 255)


def _GroundHogDay_repeated_row_ratio(raw_rows: bytes, row_data_size: int, rows: int) -> float:
    if row_data_size <= 0 or rows <= 1:
        return 0.0
    repeated = 0
    previous = raw_rows[:row_data_size]
    for row_index in range(1, rows):
        start = row_index * row_data_size
        row = raw_rows[start : start + row_data_size]
        if len(row) != row_data_size:
            break
        if row == previous:
            repeated += 1
        previous = row
    return float(repeated) / float(max(1, rows - 1))


def _GroundHogDay_filter_transition_ratio(filtered: bytes, scanline_size: int, rows: int) -> float:
    if scanline_size <= 0 or rows <= 1:
        return 0.0
    filters = [filtered[index * scanline_size] for index in range(rows)]
    transitions = sum(1 for left, right in zip(filters, filters[1:]) if left != right)
    return float(transitions) / float(max(1, rows - 1))


def _GroundHogDay_visual_score(candidate: Any, profile: str) -> GroundHogDayVisualScore:
    profile = _coerce_groundhogday_visual_guard_profile(profile)
    after = getattr(candidate, "after", None)
    if after is None or not getattr(after, "supported", False):
        return GroundHogDayVisualScore(
            False,
            profile == "off",
            profile,
            -1_000_000,
            1_000_000,
            0,
            0,
            0,
            reasons=("unsupported IDAT analysis",),
        )

    usable = int(getattr(after, "usable_scanlines", 0) or 0)
    complete = int(getattr(after, "complete_scanlines", 0) or 0)
    scanline_size = int(getattr(after, "scanline_size", 0) or 0)
    height = int(getattr(after, "height", 0) or 0)
    invalid_filter_rows = max(0, complete - usable)
    reasons: list[str] = []
    penalty = 0
    if invalid_filter_rows:
        penalty += invalid_filter_rows * 1000
        reasons.append("invalid PNG filter rows=%s" % invalid_filter_rows)

    filtered = bytes(getattr(after, "recovered_scanlines", b"") or b"")
    rows = min(usable, len(filtered) // scanline_size) if scanline_size > 0 else 0
    row_data_size = max(0, scanline_size - 1)
    entropy = 0.0
    row_delta = 0.0
    repeated_ratio = 0.0
    filter_transition_ratio = 0.0
    palette_ok = True
    raw_rows = b""

    if rows <= 0:
        if usable <= 0:
            reasons.append("no usable scanlines")
            penalty += 500
    else:
        filtered = filtered[: rows * scanline_size]
        raw_rows = png.unfilter_scanlines(
            filtered,
            width=int(getattr(after, "width", 0) or 0),
            height=rows,
            bit_depth=int(getattr(after, "bit_depth", 0) or 0),
            color_type=int(getattr(after, "color_type", 0) or 0),
        ) or b""
        if not raw_rows:
            reasons.append("unfilter failed")
            penalty += 1000
        else:
            entropy = _GroundHogDay_entropy(raw_rows)
            row_delta = _GroundHogDay_row_delta(raw_rows, row_data_size, rows)
            repeated_ratio = _GroundHogDay_repeated_row_ratio(raw_rows, row_data_size, rows)
            filter_transition_ratio = _GroundHogDay_filter_transition_ratio(filtered, scanline_size, rows)

            if int(getattr(after, "color_type", 0) or 0) == 3:
                palette_count = _GroundHogDay_plte_entry_count(bytes(getattr(candidate, "data", b"") or b""))
                indices = png.unpack_indexed_scanlines(
                    raw_rows,
                    width=int(getattr(after, "width", 0) or 0),
                    height=rows,
                    bit_depth=int(getattr(after, "bit_depth", 0) or 0),
                )
                palette_ok = bool(
                    palette_count is not None
                    and indices is not None
                    and max(indices, default=0) < palette_count
                )
                if not palette_ok:
                    reasons.append("palette index outside PLTE")
                    penalty += 2000

            if profile not in {"off", "structure"}:
                entropy_limit = 7.75 if profile == "balanced" else 7.35
                row_delta_limit = 0.48 if profile == "balanced" else 0.32
                filter_transition_limit = 0.95 if profile == "balanced" else 0.78
                repeated_limit = 0.995 if profile == "balanced" else 0.94
                if len(raw_rows) >= 128 and entropy > entropy_limit:
                    extra = int((entropy - entropy_limit) * (120 if profile == "balanced" else 220))
                    penalty += max(1, extra)
                    reasons.append("high entropy %.2f" % entropy)
                if rows >= 3 and row_delta > row_delta_limit:
                    extra = int((row_delta - row_delta_limit) * (300 if profile == "balanced" else 500))
                    penalty += max(1, extra)
                    reasons.append("weak row continuity %.3f" % row_delta)
                if rows >= 8 and filter_transition_ratio > filter_transition_limit:
                    extra = int((filter_transition_ratio - filter_transition_limit) * 200)
                    penalty += max(1, extra)
                    reasons.append("unstable filter pattern %.3f" % filter_transition_ratio)
                if rows >= 12 and repeated_ratio > repeated_limit and entropy < 0.20:
                    extra = int((repeated_ratio - repeated_limit) * (250 if profile == "balanced" else 400))
                    penalty += max(1, extra)
                    reasons.append("absurd repeated rows %.3f" % repeated_ratio)

    base = (usable * 1000) + (complete * 200) + (int(getattr(after, "decompressed_size", 0) or 0) // 64)
    if getattr(after, "complete", False):
        base += 1000
    threshold = {
        "off": 1_000_000,
        "structure": 0,
        "balanced": 95,
        "strict": 15,
    }[profile]
    passed = profile == "off" or penalty <= threshold
    return GroundHogDayVisualScore(
        True,
        passed,
        profile,
        base - penalty,
        penalty,
        usable,
        complete,
        invalid_filter_rows,
        entropy=entropy,
        row_delta=row_delta,
        repeated_row_ratio=repeated_ratio,
        filter_transition_ratio=filter_transition_ratio,
        palette_ok=palette_ok,
        reasons=tuple(reasons),
    )


def _GroundHogDay_visual_score_line(score: GroundHogDayVisualScore) -> str:
    details = [
        "profile=%s" % score.profile,
        "passed=%s" % ("yes" if score.passed else "no"),
        "visual_score=%s" % score.visual_score,
        "penalty=%s" % score.penalty,
        "usable=%s" % score.usable_scanlines,
        "complete=%s" % score.complete_scanlines,
        "invalid_filters=%s" % score.invalid_filter_rows,
        "entropy=%.2f" % score.entropy,
        "row_delta=%.3f" % score.row_delta,
        "repeat=%.3f" % score.repeated_row_ratio,
        "filter_transition=%.3f" % score.filter_transition_ratio,
        "palette_ok=%s" % ("yes" if score.palette_ok else "no"),
    ]
    if score.reasons:
        details.append("reason=%s" % ", ".join(score.reasons[:4]))
    return "; ".join(details)


def _GroundHogDay_visual_guard_worse(
    previous: GroundHogDayVisualScore,
    candidate: GroundHogDayVisualScore,
) -> bool:
    if candidate.profile in {"off", "structure"}:
        return False
    if not previous.supported or previous.usable_scanlines < 2:
        return False
    margin = 40 if candidate.profile == "balanced" else 12
    if candidate.penalty > previous.penalty + margin:
        return True
    return candidate.visual_score < previous.visual_score - (250 if candidate.profile == "balanced" else 50)


def _GroundHogDay_visual_guard_candidates(
    runtime: Any,
    previous_seeds: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...],
    candidate_seeds: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...],
    *,
    route_label: str,
) -> tuple[idat_bruteforce.IdatDeepBeamCandidate, ...]:
    profile = _GroundHogDay_visual_guard_profile(runtime)
    if profile == "off":
        runtime.side_notes.append("-IDAT GroundHogDay visual guard disabled for %s." % route_label)
        return candidate_seeds

    previous = _GroundHogDay_idat_seed_best(previous_seeds)
    previous_score = (
        _GroundHogDay_visual_score(previous, profile)
        if previous is not None
        else GroundHogDayVisualScore(False, True, profile, -1_000_000, 0, 0, 0, 0)
    )
    accepted: list[idat_bruteforce.IdatDeepBeamCandidate] = []
    rejected_complete = False
    for candidate in _rank_idat_seed_candidates(candidate_seeds, limit=max(1, len(candidate_seeds))):
        score = _GroundHogDay_visual_score(candidate, profile)
        worse = _GroundHogDay_visual_guard_worse(previous_score, score)
        runtime.side_notes.append(
            "-IDAT GroundHogDay visual guard %s candidate state%s: %s."
            % (
                route_label,
                getattr(candidate, "state_id", "?"),
                _GroundHogDay_visual_score_line(score),
            )
        )
        if score.passed and not worse:
            accepted.append(candidate)
            continue
        rejected_complete = rejected_complete or bool(getattr(getattr(candidate, "after", None), "complete", False))
        reason = "visual score failed" if not score.passed else "visual score regressed"
        runtime.side_notes.append(
            "-IDAT GroundHogDay %s seed state%s kept structural-only: %s."
            % (route_label, getattr(candidate, "state_id", "?"), reason)
        )

    if accepted:
        return _rank_idat_seed_candidates(tuple(accepted), limit=max(1, len(candidate_seeds)))

    message = (
        "complete stream, visual score failed; I am keeping the previous GroundHogDay seed and treating this linefeed branch as structural-only evidence."
        if rejected_complete
        else "GroundHogDay linefeed improved structure, but the visual guard did not accept the recovered rows. I am keeping the previous seed."
    )
    runtime.candy("Cowsay", message, "bad" if rejected_complete else "com")
    return ()


def _write_complete_idat_candidate_clone(
    runtime: Any,
    candidate: Any,
    summary: str,
    *,
    route_label: str,
    success_message: str,
) -> tuple[bool, Any] | None:
    if not _idat_candidate_is_complete_clone(candidate):
        runtime.candy(
            "Cowsay",
            "That IDAT candidate moves the image forward, but the stream is still incomplete. I am keeping it as diagnostic evidence, not reloading it as a clone.",
            "com",
        )
        runtime.side_notes.append(_idat_candidate_diagnostic_note(route_label, candidate))
        return None
    if bool(getattr(runtime, "suppress_complete_idat_clone_write", False)):
        runtime.candy(
            "Cowsay",
            "That IDAT candidate is structurally complete, but this pass is running under GroundHogDay visual guard. I am keeping it as a seed first.",
            "com",
        )
        runtime.side_notes.append(
            "-IDAT %s complete candidate kept as visual-guard seed; clone write suppressed."
            % route_label
        )
        return None

    runtime.candy("Cowsay", success_message, "good")
    return True, runtime.write_clone(candidate.data, summary)


def _format_eta_seconds(seconds: float | None) -> str:
    if seconds is None or seconds < 0:
        return "--j --h --m --s"
    total = int(seconds)
    days, remainder = divmod(total, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    return "%sj %02dh %02dm %02ds" % (days, hours, minutes, secs)


def _runtime_idat_final_investigation_progress(runtime: Any):
    minibar = getattr(runtime, "minibar", None)
    loadingbar = getattr(runtime, "loadingbar", None)
    started = time.monotonic()

    def progress(stage: str, tested: int, budget: int) -> None:
        stage_label = "shadow-finder" if str(stage) == "final-investigation" else str(stage)
        elapsed = max(0.001, time.monotonic() - started)
        rate = float(tested) / elapsed if tested > 0 else 0.0
        remaining = max(0, int(budget) - int(tested))
        eta = (float(remaining) / rate) if rate > 0 else None
        message = (
            "IDAT %s %s %s eta=%s rate=%.1f/s"
            % (
                FINAL_INVESTIGATION_LABEL,
                stage_label,
                _format_idat_queue_progress_counter(stage_label, tested, budget),
                _format_eta_seconds(eta),
                rate,
            )
        )
        if minibar is not None:
            try:
                minibar(Indication=message)
            except TypeError:
                minibar(message)
            return
        if loadingbar is not None:
            loadingbar(budget, len(str(budget)), tested, True)

    return progress if minibar is not None or loadingbar is not None else None


def _final_investigation_payload_folder(runtime: Any, *, create: bool) -> Path | None:
    file_origin = str(getattr(runtime, "file_origin", "") or "").strip()
    file_dir = str(getattr(runtime, "file_dir", "") or "")
    if not file_origin:
        return None
    try:
        folder = (
            Path(output.ensure_clone_folder(file_origin, file_dir))
            if create
            else Path(output.clone_folder(file_origin, file_dir))
        )
        payload = folder / "Debug_Payloads"
        if create:
            payload.mkdir(parents=True, exist_ok=True)
        elif not payload.is_dir():
            return None
    except Exception:
        return None
    return payload


def _final_investigation_stem(runtime: Any, payload_folder: Path) -> str:
    parent = payload_folder.parent
    if parent.name.startswith("Folder_"):
        stem = output.source_stem(parent.name[len("Folder_") :])
        if stem:
            return stem
    return output.repair_stem(
        str(getattr(runtime, "file_origin", "") or "IDAT"),
        str(getattr(runtime, "file_dir", "") or ""),
    )


def _idat_final_investigation_paths(runtime: Any) -> tuple[str, str]:
    payload_folder = _final_investigation_payload_folder(runtime, create=True)
    if payload_folder is None:
        return "", ""
    stem = _final_investigation_stem(runtime, payload_folder)
    checkpoint_path = payload_folder / ("%s_final_investigation.checkpoint.jsonl" % stem)
    progress_path = payload_folder / ("%s_final_investigation.progress.json" % stem)
    return str(checkpoint_path), str(progress_path)


def _final_investigation_checkpoint_paths(runtime: Any) -> tuple[Path, ...]:
    payload_folder = _final_investigation_payload_folder(runtime, create=False)
    if payload_folder is None:
        return ()
    stem = _final_investigation_stem(runtime, payload_folder)
    return tuple(sorted(payload_folder.glob("%s_*.checkpoint.jsonl" % stem)))


def _final_investigation_artifact_paths(runtime: Any) -> tuple[Path, ...]:
    payload_folder = _final_investigation_payload_folder(runtime, create=False)
    if payload_folder is None:
        return ()
    stem = _final_investigation_stem(runtime, payload_folder)
    patterns = (
        "%s_idat_*_rank*.png" % stem,
        "%s_groundhogday_seed_state*.png" % stem,
        "%s_groundhogday_state*_linefeed_chain_round*.png" % stem,
    )
    paths: list[Path] = []
    seen: set[Path] = set()
    for pattern in patterns:
        for path in sorted(payload_folder.glob(pattern)):
            if not path.is_file() or path in seen:
                continue
            seen.add(path)
            paths.append(path)
    return tuple(paths)


def _final_investigation_has_evidence(runtime: Any) -> bool:
    return bool(
        _final_investigation_checkpoint_paths(runtime)
        or _final_investigation_artifact_paths(runtime)
    )


def _final_investigation_ready(runtime: Any) -> bool:
    return _runtime_final_investigation_configured(runtime) or _final_investigation_has_evidence(runtime)


def _artifact_idat_seed_candidate(
    artifact_path: Path,
    before: idat.IdatStreamAnalysis,
    *,
    original_idat_count: int,
    state_id: int,
) -> idat_bruteforce.IdatDeepBeamCandidate | None:
    try:
        artifact_data = artifact_path.read_bytes()
        _chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(artifact_data)
    except Exception:
        return None
    if not stream:
        return None
    after = idat.analyze_idat_stream(artifact_data)
    if before.supported and after.supported:
        for name in ("width", "height", "bit_depth", "color_type", "expected_size"):
            before_value = int(getattr(before, name, 0) or 0)
            after_value = int(getattr(after, name, 0) or 0)
            if before_value > 0 and after_value > 0 and before_value != after_value:
                return None
    operation = idat_bruteforce.IdatDeepBeamOperation(
        "shadow-finder-artifact-seed",
        0,
        b"",
        artifact_path.name.encode("utf-8", errors="replace")[:48],
    )
    return idat_bruteforce.IdatDeepBeamCandidate(
        data=artifact_data,
        stream=stream,
        operations=(operation,),
        before=before,
        after=after,
        state_id=state_id,
        parent_id=None,
        source_offsets=(),
        score=idat_bruteforce._deep_beam_score(
            after,
            stream,
            1,
            data=artifact_data,
            original_idat_count=original_idat_count,
        ),
    )


def _load_final_investigation_seed_candidates(
    runtime: Any,
    data: bytes,
    analysis: idat.IdatStreamAnalysis,
    *,
    seed_candidates: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...] = (),
) -> tuple[idat_bruteforce.IdatDeepBeamCandidate, ...]:
    seed_limit = _runtime_final_investigation_seed_limit(runtime)
    collection_limit = max(seed_limit * 3, IDAT_DEBUG_ARTIFACT_TOP_LIMIT * 64)
    try:
        chunks, _stream = idat_bruteforce._all_chunks_and_idat_stream(data)
        original_idat_count = sum(1 for chunk in chunks if chunk.chunk_type == b"IDAT")
    except Exception:
        original_idat_count = 1

    candidates: list[idat_bruteforce.IdatDeepBeamCandidate] = list(seed_candidates)
    checkpoint_count = 0
    for checkpoint_path in _final_investigation_checkpoint_paths(runtime):
        if checkpoint_count >= collection_limit:
            break
        checkpoint_candidates = _load_idat_deep_beam_seed_candidates(data, str(checkpoint_path))
        candidates.extend(checkpoint_candidates)
        checkpoint_count += len(checkpoint_candidates)

    next_state_id = max((int(getattr(candidate, "state_id", 0)) for candidate in candidates), default=0) + 1
    artifact_count = 0
    for artifact_path in _final_investigation_artifact_paths(runtime):
        if artifact_count >= collection_limit:
            break
        candidate = _artifact_idat_seed_candidate(
            artifact_path,
            analysis,
            original_idat_count=original_idat_count,
            state_id=next_state_id,
        )
        if candidate is None:
            continue
        candidates.append(candidate)
        artifact_count += 1
        next_state_id += 1

    merged = _merge_idat_seed_candidates(tuple(candidates))
    if not merged:
        return ()
    return idat_bruteforce._deep_beam_ranked_unique(merged, limit=seed_limit)


def _load_idat_artifact_seed_candidates(
    runtime: Any,
    data: bytes,
    analysis: idat.IdatStreamAnalysis,
    *,
    limit: int,
) -> tuple[idat_bruteforce.IdatDeepBeamCandidate, ...]:
    try:
        chunks, _stream = idat_bruteforce._all_chunks_and_idat_stream(data)
        original_idat_count = sum(1 for chunk in chunks if chunk.chunk_type == b"IDAT")
    except Exception:
        original_idat_count = 1

    collection_limit = max(int(limit) * 64, IDAT_DEBUG_ARTIFACT_TOP_LIMIT * 64)
    candidates: list[idat_bruteforce.IdatDeepBeamCandidate] = []
    next_state_id = 1
    for artifact_path in _final_investigation_artifact_paths(runtime):
        if len(candidates) >= collection_limit:
            break
        candidate = _artifact_idat_seed_candidate(
            artifact_path,
            analysis,
            original_idat_count=original_idat_count,
            state_id=next_state_id,
        )
        if candidate is None:
            continue
        candidates.append(candidate)
        next_state_id += 1

    merged = _merge_idat_seed_candidates(tuple(candidates))
    if not merged:
        return ()
    return idat_bruteforce._deep_beam_ranked_unique(merged, limit=max(1, int(limit)))


def _idat_seed_candidates_have_material_progress(
    analysis: idat.IdatStreamAnalysis,
    seed_candidates: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...],
) -> bool:
    return any(
        getattr(candidate, "after", None) is not None
        and idat_bruteforce.is_material_improvement(analysis, candidate.after)
        for candidate in seed_candidates
    )


def _idat_seed_candidates_have_frontier_progress(
    analysis: idat.IdatStreamAnalysis,
    seed_candidates: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...],
) -> bool:
    for candidate in seed_candidates:
        after = getattr(candidate, "after", None)
        if after is None or not getattr(after, "supported", False):
            continue
        if idat_bruteforce.is_material_improvement(analysis, after):
            return True
        if int(getattr(after, "complete_scanlines", 0) or 0) > int(
            getattr(analysis, "complete_scanlines", 0) or 0
        ):
            return True
        if int(getattr(after, "decompressed_size", 0) or 0) > int(
            getattr(analysis, "decompressed_size", 0) or 0
        ):
            return True
    return False


def _should_run_final_investigation(
    runtime: Any,
    analysis: idat.IdatStreamAnalysis,
    seed_candidates: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...] = (),
    *,
    evidence_ready: bool | None = None,
) -> bool:
    if _idat_seed_candidates_have_frontier_progress(analysis, seed_candidates):
        return True
    if seed_candidates and _runtime_final_investigation_configured(runtime):
        return True
    ready = _final_investigation_ready(runtime) if evidence_ready is None else bool(evidence_ready)
    if not ready:
        return False
    if analysis.usable_scanlines > 0 or analysis.decompressed_size > 0:
        return True
    return _final_investigation_has_evidence(runtime)


def _run_idat_final_investigation_runtime(
    runtime: Any,
    data: bytes,
    analysis: idat.IdatStreamAnalysis,
    *,
    seed_candidates: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...] = (),
) -> tuple[bool, Any] | None:
    if not _should_run_final_investigation(runtime, analysis, seed_candidates):
        return None
    if _block_deep_beam_if_chunk_names_are_stale(runtime, data):
        return None

    checkpoint_path, progress_path = _idat_final_investigation_paths(runtime)
    if not checkpoint_path:
        runtime.side_notes.append(
            "-IDAT %s skipped: source repair folder is unavailable."
            % FINAL_INVESTIGATION_LABEL
        )
        return None

    seeds = _load_final_investigation_seed_candidates(
        runtime,
        data,
        analysis,
        seed_candidates=seed_candidates,
    )
    runtime.side_notes.append(
        "-IDAT %s seed intake: %s candidate(s) from frontier/checkpoint/artifact evidence."
        % (FINAL_INVESTIGATION_LABEL, len(seeds))
    )
    runtime.candy(
        "Cowsay",
        "%s: I am switching to a long pure IDAT brute-force campaign with checkpointed progress."
        % FINAL_INVESTIGATION_LABEL,
        "com",
    )
    runtime.candy(
        "Cowsay",
        "It will reuse the strongest existing seeds, workers, and GPU prefilter; interruption keeps the checkpoint resumable.",
        "com",
    )
    runtime.candy("Title", FINAL_INVESTIGATION_LABEL)

    deep_workers, deep_gpu, deep_gpu_config, _deep_budget, deep_gpu_shard_size, deep_cpu_batch_size = _runtime_deep_beam_options(runtime)
    final_budget = _runtime_final_investigation_budget(runtime)
    final_max_depth = _runtime_final_investigation_max_depth(runtime)
    runtime.side_notes.append(
        "-IDAT %s configuration: budget=%s; max_depth=%s; checkpoint=%s; progress=%s."
        % (FINAL_INVESTIGATION_LABEL, final_budget, final_max_depth, checkpoint_path, progress_path)
    )
    result = idat_bruteforce.probe_idat_deflate_deep_beam(
        data,
        budget=final_budget,
        max_depth=final_max_depth,
        workers=deep_workers,
        gpu=deep_gpu,
        gpu_config=deep_gpu_config,
        gpu_shard_size=deep_gpu_shard_size,
        cpu_batch_size=deep_cpu_batch_size,
        overlap_gpu_cpu=True,
        checkpoint_path=checkpoint_path,
        progress_path=progress_path,
        seed_candidates=seeds,
        progress=_runtime_idat_final_investigation_progress(runtime),
    )
    result = replace(result, strategy=FINAL_INVESTIGATION_LABEL)
    runtime.side_notes.append(idat_bruteforce.deep_beam_summary_line(result))
    runtime.side_notes.extend(idat_bruteforce.deep_beam_candidate_summary_lines(result))
    _write_idat_deep_beam_debug_artifacts(runtime, result, label="idat_final_investigation", include_dynamic_trace=True)

    if result.interrupted:
        runtime.candy(
            "Cowsay",
            "%s interrupted; checkpoint/progress are saved, so the next run resumes instead of restarting."
            % FINAL_INVESTIGATION_LABEL,
            "bad",
        )
        runtime.side_notes.append(
            "-IDAT %s interrupted; checkpoint/progress saved."
            % FINAL_INVESTIGATION_LABEL
        )
        raise SystemExit(130)

    if result.best is None:
        if result.top_candidates:
            _GroundHogDay_write_resume_state(runtime, data, result.top_candidates)
            runtime.side_notes.append(
                "-IDAT %s handed checkpointed candidate(s) back to GroundHogDay resume."
                % FINAL_INVESTIGATION_LABEL
            )
            runtime.candy(
                "Cowsay",
                "%s kept candidate evidence but did not finish the PNG. GroundHogDay will use those saved seeds on the next pass."
                % FINAL_INVESTIGATION_LABEL,
                "com",
            )
        if result.budget_exhausted:
            runtime.candy(
                "Cowsay",
                "%s reached its current budget. The checkpoint, progress JSON, and top candidates are saved for the next pass."
                % FINAL_INVESTIGATION_LABEL,
                "bad",
            )
            runtime.candy(
                "Cowsay",
                "Increase IDAT_FINAL_INVESTIGATION_BUDGET or resume later; I am not marking the IDAT route as solved or exhausted.",
                "com",
            )
        else:
            runtime.candy(
                "Cowsay",
                "%s saved diagnostic candidates but has not produced a clone-worthy image yet."
                % FINAL_INVESTIGATION_LABEL,
                "bad",
            )
        runtime.side_notes.append(
            "-IDAT %s produced no final clone; route left open with checkpointed evidence."
            % FINAL_INVESTIGATION_LABEL
        )
        return None

    candidate = result.best
    summary = "\n".join(
        (
            "-Repair hypothesis tried: %s pure IDAT brute force."
            % FINAL_INVESTIGATION_LABEL,
            idat_deflate_header_note(analysis),
            idat_bruteforce.deep_beam_summary_line(result),
            *idat_bruteforce.deep_beam_candidate_summary_lines(result),
            idat_stream_diagnosis_note(candidate.after),
        )
    )
    written = _write_complete_idat_candidate_clone(
        runtime,
        candidate,
        summary,
        route_label=FINAL_INVESTIGATION_LABEL,
        success_message="%s found a complete IDAT candidate with validated image progress."
        % FINAL_INVESTIGATION_LABEL,
    )
    if written is None:
        _GroundHogDay_write_resume_state(runtime, data, result.top_candidates or (candidate,))
        runtime.side_notes.append(
            "-IDAT %s produced incomplete progress; GroundHogDay resume is the next route."
            % FINAL_INVESTIGATION_LABEL
        )
        runtime.candy(
            "Cowsay",
            "%s moved the IDAT stream, but not to a final PNG. I saved those candidates so GroundHogDay can keep alternating from there."
            % FINAL_INVESTIGATION_LABEL,
            "com",
        )
    return written


def _run_idat_periodic_model_runtime(
    runtime: Any,
    data: bytes,
    analysis: idat.IdatStreamAnalysis,
) -> idat_bruteforce.IdatPeriodicCorruptionModelResult | None:
    if _block_deep_beam_if_chunk_names_are_stale(runtime, data):
        return None
    model_path = _idat_convoy_model_path(runtime)
    checkpoint_path, progress_path = _idat_periodic_model_paths(runtime)
    progress_state = idat_bruteforce.periodic_model_progress_state(data, progress_path)
    already_consumed = (
        progress_state.available
        and progress_state.source_matches
        and progress_state.exhausted
    )
    if already_consumed:
        runtime.side_notes.append(
            "-IDAT periodic corruption model already consumed for this source: tested=%s; reason=%s."
            % (progress_state.tested, progress_state.reason)
        )
    else:
        runtime.candy(
            "Cowsay",
            "I am trying the periodic IDAT corruption model before the wide deep beam.",
            "com",
        )
        runtime.candy("Title", "probe_idat_periodic_corruption_model")
    result = idat_bruteforce.probe_idat_periodic_corruption_model(
        data,
        convoy_model_path=model_path,
        checkpoint_path=checkpoint_path,
        progress_path=progress_path,
        progress=_runtime_idat_queue_progress(runtime),
    )
    runtime.side_notes.append(idat_bruteforce.periodic_corruption_model_summary_line(result))
    runtime.side_notes.extend(idat_bruteforce.periodic_corruption_model_candidate_summary_lines(result))
    if result.top_candidates and not already_consumed:
        _write_idat_deep_beam_debug_artifacts(runtime, result, label="idat_periodic_model")
    if result.best is None and not already_consumed:
        if result.top_candidates:
            runtime.candy(
                "Cowsay",
                "The periodic model produced diagnostic seeds, but still no usable PNG scanline.",
                "com",
            )
        else:
            runtime.candy(
                "Cowsay",
                "The periodic model had no clone-worthy candidate.",
                "bad",
            )
    return result


def _write_periodic_model_best_clone(
    runtime: Any,
    analysis: idat.IdatStreamAnalysis,
    result: idat_bruteforce.IdatPeriodicCorruptionModelResult,
) -> tuple[bool, Any] | None:
    candidate = result.best
    if candidate is None:
        raise ValueError("periodic model result has no best candidate")
    summary = "\n".join(
        (
            "-Repair hypothesis tried: periodic IDAT corruption model.",
            idat_deflate_header_note(analysis),
            idat_bruteforce.periodic_corruption_model_summary_line(result),
            *idat_bruteforce.periodic_corruption_model_candidate_summary_lines(result),
            idat_stream_diagnosis_note(candidate.after),
        )
    )
    return _write_complete_idat_candidate_clone(
        runtime,
        candidate,
        summary,
        route_label="periodic corruption model",
        success_message="The periodic corruption model found a complete IDAT candidate with validated image progress.",
    )


def _run_idat_affine_corruption_runtime(
    runtime: Any,
    data: bytes,
    analysis: idat.IdatStreamAnalysis,
) -> idat_bruteforce.IdatAffineCorruptionModelResult | None:
    if _block_deep_beam_if_chunk_names_are_stale(runtime, data):
        return None
    model_path = _idat_convoy_model_path(runtime)
    checkpoint_path, progress_path = _idat_affine_corruption_paths(runtime)
    budget = _runtime_affine_corruption_budget(runtime)
    workers = _runtime_huffman_kraft_workers(runtime)
    gpu_config = _runtime_huffman_kraft_gpu_config(runtime)
    progress_state = idat_bruteforce.affine_corruption_progress_state(data, progress_path)
    already_consumed = (
        progress_state.available
        and progress_state.source_matches
        and progress_state.exhausted
        and progress_state.budget >= budget
    )
    if already_consumed:
        runtime.side_notes.append(
            "-IDAT affine-corruption already consumed for this source/budget: tested=%s; budget=%s; reason=%s."
            % (progress_state.tested, progress_state.budget, progress_state.reason)
        )
    else:
        runtime.candy(
            "Cowsay",
            "I am projecting affine corruption rules learned from the IDAT convoy.",
            "com",
        )
        runtime.candy("Title", "probe_idat_affine_corruption_model")
    result = idat_bruteforce.probe_idat_affine_corruption_model(
        data,
        convoy_model_path=model_path,
        budget=budget,
        workers=workers,
        gpu=getattr(gpu_config, "enabled", False),
        gpu_config=gpu_config,
        checkpoint_path=checkpoint_path,
        progress_path=progress_path,
        progress=_runtime_idat_queue_progress(runtime),
    )
    runtime.side_notes.append(idat_bruteforce.affine_corruption_model_summary_line(result))
    runtime.side_notes.extend(idat_bruteforce.affine_corruption_model_candidate_summary_lines(result))
    if result.top_candidates and not already_consumed:
        _write_idat_deep_beam_debug_artifacts(runtime, result, label="idat_affine_corruption", include_dynamic_trace=True)
    if result.best is None and not already_consumed:
        runtime.candy(
            "Cowsay",
            "The affine corruption model produced no clone-worthy PNG scanline yet.",
            "bad",
        )
    return result


def _write_affine_corruption_best_clone(
    runtime: Any,
    analysis: idat.IdatStreamAnalysis,
    result: idat_bruteforce.IdatAffineCorruptionModelResult,
) -> tuple[bool, Any] | None:
    candidate = result.best
    if candidate is None:
        raise ValueError("affine corruption result has no best candidate")
    summary = "\n".join(
        (
            "-Repair hypothesis tried: affine IDAT corruption model.",
            idat_deflate_header_note(analysis),
            idat_bruteforce.affine_corruption_model_summary_line(result),
            *idat_bruteforce.affine_corruption_model_candidate_summary_lines(result),
            idat_stream_diagnosis_note(candidate.after),
        )
    )
    return _write_complete_idat_candidate_clone(
        runtime,
        candidate,
        summary,
        route_label="affine corruption model",
        success_message="The affine corruption model found a complete IDAT candidate with validated image progress.",
    )


def _run_idat_huffman_kraft_runtime(
    runtime: Any,
    data: bytes,
    analysis: idat.IdatStreamAnalysis,
    *,
    seed_candidates: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...] = (),
) -> idat_bruteforce.IdatHuffmanKraftSolverResult | None:
    if _block_deep_beam_if_chunk_names_are_stale(runtime, data):
        return None
    checkpoint_path, progress_path = _idat_huffman_kraft_paths(runtime)
    budget = _runtime_huffman_kraft_budget(runtime)
    workers = _runtime_huffman_kraft_workers(runtime)
    gpu_config = _runtime_huffman_kraft_gpu_config(runtime)
    progress_state = idat_bruteforce.huffman_kraft_progress_state(data, progress_path)
    already_consumed = (
        progress_state.available
        and progress_state.source_matches
        and progress_state.exhausted
        and progress_state.budget >= budget
    )
    if already_consumed:
        runtime.side_notes.append(
            "-IDAT huffman-kraft already consumed for this source/budget: tested=%s; budget=%s; reason=%s."
            % (progress_state.tested, progress_state.budget, progress_state.reason)
        )
    else:
        runtime.candy(
            "Cowsay",
            "I am solving the dynamic Huffman trees by Kraft debt before the wide beam.",
            "com",
        )
        runtime.candy("Title", "probe_idat_huffman_kraft_solver")
    result = idat_bruteforce.probe_idat_huffman_kraft_solver(
        data,
        budget=budget,
        workers=workers,
        gpu=getattr(gpu_config, "enabled", False),
        gpu_config=gpu_config,
        checkpoint_path=checkpoint_path,
        progress_path=progress_path,
        seed_candidates=seed_candidates,
        progress=_runtime_idat_queue_progress(runtime),
    )
    runtime.side_notes.append(idat_bruteforce.huffman_kraft_summary_line(result))
    runtime.side_notes.extend(idat_bruteforce.huffman_kraft_candidate_summary_lines(result))
    if "stop=memory_guard" in result.reason:
        tone = "bad" if not result.top_candidates else "com"
        runtime.candy(
            "Cowsay",
            (
                "The Kraft solver throttled before the desktop ran out of memory. "
                "Checkpoint/progress are flushed; I am handing the saved seeds to the next IDAT routes."
            )
            if result.top_candidates
            else (
                "The Kraft solver stopped before the desktop ran out of memory. "
                "Checkpoint/progress are flushed; resume later with fewer workers or GPU off."
            ),
            tone,
        )
        if not result.top_candidates:
            raise SystemExit(130)
    if result.top_candidates and not already_consumed:
        _write_idat_deep_beam_debug_artifacts(runtime, result, label="idat_huffman_kraft", include_dynamic_trace=True)
    if result.best is None and not already_consumed:
        runtime.candy(
            "Cowsay",
            "The Kraft solver kept diagnostic seeds, but no usable PNG scanline yet.",
            "bad",
        )
    return result


def _write_huffman_kraft_best_clone(
    runtime: Any,
    analysis: idat.IdatStreamAnalysis,
    result: idat_bruteforce.IdatHuffmanKraftSolverResult,
) -> tuple[bool, Any] | None:
    candidate = result.best
    if candidate is None:
        raise ValueError("huffman kraft result has no best candidate")
    summary = "\n".join(
        (
            "-Repair hypothesis tried: Kraft-constrained dynamic Huffman solver.",
            idat_deflate_header_note(analysis),
            idat_bruteforce.huffman_kraft_summary_line(result),
            *idat_bruteforce.huffman_kraft_candidate_summary_lines(result),
            idat_stream_diagnosis_note(candidate.after),
        )
    )
    return _write_complete_idat_candidate_clone(
        runtime,
        candidate,
        summary,
        route_label="Kraft Huffman solver",
        success_message="The Kraft Huffman solver found a complete IDAT candidate with validated image progress.",
    )


def _run_idat_first_filter_literal_runtime(
    runtime: Any,
    data: bytes,
    analysis: idat.IdatStreamAnalysis,
    *,
    seed_candidates: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...] = (),
) -> idat_bruteforce.IdatFirstFilterLiteralResult | None:
    if _block_deep_beam_if_chunk_names_are_stale(runtime, data):
        return None
    checkpoint_path, progress_path = _idat_first_filter_literal_paths(runtime)
    budget = idat_bruteforce.FIRST_FILTER_LITERAL_DEFAULT_BUDGET
    progress_state = idat_bruteforce.first_filter_literal_progress_state(data, progress_path)
    already_consumed = (
        progress_state.available
        and progress_state.source_matches
        and progress_state.exhausted
        and progress_state.budget >= budget
        and idat_bruteforce.frontier_progress_route_version(progress_path)
        >= idat_bruteforce.FIRST_FILTER_LITERAL_ROUTE_VERSION
    )
    if already_consumed:
        runtime.side_notes.append(
            "-IDAT first-filter-literal already consumed for this source/budget: tested=%s; budget=%s; reason=%s."
            % (progress_state.tested, progress_state.budget, progress_state.reason)
        )
    else:
        runtime.candy(
            "Cowsay",
            "I am forcing the first dynamic-Huffman symbol to a PNG filter before backref repair.",
            "com",
        )
        runtime.candy("Title", "probe_idat_first_filter_literal_solver")
    result = idat_bruteforce.probe_idat_first_filter_literal_solver(
        data,
        budget=budget,
        checkpoint_path=checkpoint_path,
        progress_path=progress_path,
        seed_candidates=seed_candidates,
        progress=_runtime_idat_queue_progress(runtime),
    )
    runtime.side_notes.append(idat_bruteforce.first_filter_literal_summary_line(result))
    runtime.side_notes.extend(idat_bruteforce.first_filter_literal_candidate_summary_lines(result))
    if result.top_candidates and not already_consumed:
        _write_idat_deep_beam_debug_artifacts(runtime, result, label="idat_first_filter_literal", include_dynamic_trace=True)
    if result.best is None and not already_consumed:
        if result.top_candidates:
            runtime.candy(
                "Cowsay",
                "The first-filter route produced PNG-plausible prefix seeds for the next repair routes.",
                "com",
            )
        else:
            runtime.candy(
                "Cowsay",
                "The first-filter route found no compatible first-symbol rewrite yet.",
                "bad",
            )
    return result


def _write_first_filter_literal_best_clone(
    runtime: Any,
    analysis: idat.IdatStreamAnalysis,
    result: idat_bruteforce.IdatFirstFilterLiteralResult,
) -> tuple[bool, Any] | None:
    candidate = result.best
    if candidate is None:
        raise ValueError("first-filter literal result has no best candidate")
    summary = "\n".join(
        (
            "-Repair hypothesis tried: first dynamic-Huffman symbol forced to PNG filter.",
            idat_deflate_header_note(analysis),
            idat_bruteforce.first_filter_literal_summary_line(result),
            *idat_bruteforce.first_filter_literal_candidate_summary_lines(result),
            idat_stream_diagnosis_note(candidate.after),
        )
    )
    return _write_complete_idat_candidate_clone(
        runtime,
        candidate,
        summary,
        route_label="first-filter literal solver",
        success_message="The first-filter literal solver found a complete IDAT candidate with validated image progress.",
    )


def _run_idat_kraft_backref_runtime(
    runtime: Any,
    data: bytes,
    analysis: idat.IdatStreamAnalysis,
    *,
    seed_candidates: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...] = (),
    path_label: str = "kraft_backref",
    seed_checkpoint_path: str | None = None,
) -> idat_bruteforce.IdatKraftBackrefRepairResult | None:
    if _block_deep_beam_if_chunk_names_are_stale(runtime, data):
        return None
    checkpoint_path, progress_path = _idat_frontier_paths(runtime, path_label)
    if seed_checkpoint_path is None:
        seed_checkpoint_path, _kraft_progress_path = _idat_huffman_kraft_paths(runtime)
    budget = _runtime_kraft_backref_budget(runtime)
    progress_state = idat_bruteforce.kraft_backref_progress_state(data, progress_path)
    if (
        progress_state.available
        and progress_state.source_matches
        and progress_state.exhausted
        and progress_state.budget >= budget
        and idat_bruteforce.frontier_progress_route_version(progress_path)
        >= idat_bruteforce.KRAFT_BACKREF_ROUTE_VERSION
    ):
        runtime.side_notes.append(
            "-IDAT kraft-backref already consumed for this source/budget: tested=%s; budget=%s; reason=%s."
            % (progress_state.tested, progress_state.budget, progress_state.reason)
        )
        result = idat_bruteforce.probe_idat_kraft_backref_repair(
            data,
            budget=budget,
            checkpoint_path=checkpoint_path,
            progress_path=progress_path,
            seed_candidates=seed_candidates,
            seed_checkpoint_path=seed_checkpoint_path or "",
            progress=_runtime_idat_queue_progress(runtime),
        )
        runtime.side_notes.append(idat_bruteforce.kraft_backref_repair_summary_line(result))
        runtime.side_notes.extend(idat_bruteforce.kraft_backref_repair_candidate_summary_lines(result))
        return result
    runtime.candy(
        "Cowsay",
        "I am repairing impossible Kraft backref distances before the oracle and wide beam.",
        "com",
    )
    runtime.candy("Title", "probe_idat_kraft_backref_repair")
    result = idat_bruteforce.probe_idat_kraft_backref_repair(
        data,
        budget=budget,
        checkpoint_path=checkpoint_path,
        progress_path=progress_path,
        seed_candidates=seed_candidates,
        seed_checkpoint_path=seed_checkpoint_path or "",
        progress=_runtime_idat_queue_progress(runtime),
    )
    runtime.side_notes.append(idat_bruteforce.kraft_backref_repair_summary_line(result))
    runtime.side_notes.extend(idat_bruteforce.kraft_backref_repair_candidate_summary_lines(result))
    if result.top_candidates:
        _write_idat_deep_beam_debug_artifacts(runtime, result, label="idat_%s" % path_label, include_dynamic_trace=True)
    if result.best is None:
        if result.top_candidates:
            runtime.candy(
                "Cowsay",
                "The Kraft backref route kept stronger PNG-prefix seeds, but no final clone yet.",
                "com",
            )
        else:
            runtime.candy(
                "Cowsay",
                "The Kraft backref route found no useful distance repair yet.",
                "bad",
            )
    return result


def _write_kraft_backref_best_clone(
    runtime: Any,
    analysis: idat.IdatStreamAnalysis,
    result: idat_bruteforce.IdatKraftBackrefRepairResult,
) -> tuple[bool, Any] | None:
    candidate = result.best
    if candidate is None:
        raise ValueError("kraft backref result has no best candidate")
    summary = "\n".join(
        (
            "-Repair hypothesis tried: Kraft backref distance repair.",
            idat_deflate_header_note(analysis),
            idat_bruteforce.kraft_backref_repair_summary_line(result),
            *idat_bruteforce.kraft_backref_repair_candidate_summary_lines(result),
            idat_stream_diagnosis_note(candidate.after),
        )
    )
    return _write_complete_idat_candidate_clone(
        runtime,
        candidate,
        summary,
        route_label="Kraft backref route",
        success_message="The Kraft backref route found a complete IDAT candidate with validated image progress.",
    )


def _run_idat_stored_block_runtime(
    runtime: Any,
    data: bytes,
    analysis: idat.IdatStreamAnalysis,
    *,
    seed_candidates: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...] = (),
    path_label: str = "stored_block",
    seed_checkpoint_path: str | None = None,
) -> idat_bruteforce.IdatStoredBlockLengthRepairResult | None:
    if _block_deep_beam_if_chunk_names_are_stale(runtime, data):
        return None
    checkpoint_path, progress_path = _idat_frontier_paths(runtime, path_label)
    if seed_checkpoint_path is None:
        seed_checkpoint_path, _backref_progress_path = _idat_kraft_backref_paths(runtime)
    budget = _runtime_stored_block_budget(runtime)
    progress_state = idat_bruteforce.stored_block_progress_state(data, progress_path)
    already_consumed = (
        progress_state.available
        and progress_state.source_matches
        and progress_state.exhausted
        and progress_state.budget >= budget
        and idat_bruteforce.frontier_progress_route_version(progress_path)
        >= idat_bruteforce.STORED_BLOCK_ROUTE_VERSION
    )
    if already_consumed:
        runtime.side_notes.append(
            "-IDAT stored-block already consumed for this source/budget: tested=%s; budget=%s; reason=%s."
            % (progress_state.tested, progress_state.budget, progress_state.reason)
        )
    else:
        runtime.candy(
            "Cowsay",
            "I am repairing stored deflate block length pairs from the frontier seeds.",
            "com",
        )
        runtime.candy("Title", "probe_idat_stored_block_length_repair")
    result = idat_bruteforce.probe_idat_stored_block_length_repair(
        data,
        budget=budget,
        checkpoint_path=checkpoint_path,
        progress_path=progress_path,
        seed_candidates=seed_candidates,
        seed_checkpoint_path=seed_checkpoint_path or "",
        progress=_runtime_idat_queue_progress(runtime),
    )
    runtime.side_notes.append(idat_bruteforce.stored_block_length_repair_summary_line(result))
    runtime.side_notes.extend(idat_bruteforce.stored_block_length_repair_candidate_summary_lines(result))
    if result.top_candidates and not already_consumed:
        _write_idat_deep_beam_debug_artifacts(runtime, result, label="idat_%s" % path_label, include_dynamic_trace=True)
    if result.best is None and not already_consumed:
        if result.top_candidates:
            runtime.candy(
                "Cowsay",
                "The stored-block route kept stronger prefix seeds, but no final clone yet.",
                "com",
            )
        else:
            runtime.candy(
                "Cowsay",
                "The stored-block route found no useful LEN/NLEN repair yet.",
                "bad",
            )
    return result


def _write_stored_block_best_clone(
    runtime: Any,
    analysis: idat.IdatStreamAnalysis,
    result: idat_bruteforce.IdatStoredBlockLengthRepairResult,
) -> tuple[bool, Any] | None:
    candidate = result.best
    if candidate is None:
        raise ValueError("stored block result has no best candidate")
    summary = "\n".join(
        (
            "-Repair hypothesis tried: stored deflate block LEN/NLEN repair.",
            idat_deflate_header_note(analysis),
            idat_bruteforce.stored_block_length_repair_summary_line(result),
            *idat_bruteforce.stored_block_length_repair_candidate_summary_lines(result),
            idat_stream_diagnosis_note(candidate.after),
        )
    )
    return _write_complete_idat_candidate_clone(
        runtime,
        candidate,
        summary,
        route_label="stored-block route",
        success_message="The stored-block route found a complete IDAT candidate with validated image progress.",
    )


def _run_idat_huffman_oracle_runtime(
    runtime: Any,
    data: bytes,
    analysis: idat.IdatStreamAnalysis,
    *,
    seed_candidates: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...] = (),
) -> idat_bruteforce.IdatHuffmanOracleSolverResult | None:
    if _block_deep_beam_if_chunk_names_are_stale(runtime, data):
        return None
    checkpoint_path, progress_path = _idat_huffman_oracle_paths(runtime)
    budget = _runtime_huffman_oracle_budget(runtime)
    progress_state = idat_bruteforce.huffman_oracle_progress_state(data, progress_path)
    already_consumed = (
        progress_state.available
        and progress_state.source_matches
        and progress_state.exhausted
        and progress_state.budget >= budget
    )
    if already_consumed:
        runtime.side_notes.append(
            "-IDAT huffman-oracle already consumed for this source/budget: tested=%s; budget=%s; reason=%s."
            % (progress_state.tested, progress_state.budget, progress_state.reason)
        )
    else:
        runtime.candy(
            "Cowsay",
            "I am trying a constrained dynamic-Huffman route with a PNG raw-filter oracle.",
            "com",
        )
        runtime.candy("Title", "probe_idat_dynamic_huffman_png_oracle_solver")
    result = idat_bruteforce.probe_idat_dynamic_huffman_png_oracle_solver(
        data,
        budget=budget,
        checkpoint_path=checkpoint_path,
        progress_path=progress_path,
        seed_candidates=seed_candidates,
        progress=_runtime_idat_queue_progress(runtime),
    )
    runtime.side_notes.append(idat_bruteforce.huffman_oracle_summary_line(result))
    runtime.side_notes.extend(idat_bruteforce.huffman_oracle_candidate_summary_lines(result))
    if result.top_candidates and not already_consumed:
        _write_idat_deep_beam_debug_artifacts(runtime, result, label="idat_huffman_oracle", include_dynamic_trace=True)
    if result.best is None and not already_consumed:
        message = "The Huffman oracle kept diagnostic seeds, but no usable PNG scanline yet."
        if "stop=frontier_exhausted" in result.reason:
            message = (
                "The Huffman oracle exhausted its constrained frontier before the budget; "
                "no usable PNG scanline yet."
            )
        elif "stop=depth_limit_reached" in result.reason:
            message = (
                "The Huffman oracle reached its depth limit before the budget; "
                "no usable PNG scanline yet."
            )
        runtime.candy(
            "Cowsay",
            message,
            "bad",
        )
    return result


def _write_huffman_oracle_best_clone(
    runtime: Any,
    analysis: idat.IdatStreamAnalysis,
    result: idat_bruteforce.IdatHuffmanOracleSolverResult,
) -> tuple[bool, Any] | None:
    candidate = result.best
    if candidate is None:
        raise ValueError("huffman oracle result has no best candidate")
    summary = "\n".join(
        (
            "-Repair hypothesis tried: constrained dynamic-Huffman PNG oracle.",
            idat_deflate_header_note(analysis),
            idat_bruteforce.huffman_oracle_summary_line(result),
            *idat_bruteforce.huffman_oracle_candidate_summary_lines(result),
            idat_stream_diagnosis_note(candidate.after),
        )
    )
    return _write_complete_idat_candidate_clone(
        runtime,
        candidate,
        summary,
        route_label="Huffman oracle",
        success_message="The Huffman oracle found a complete IDAT candidate with validated image progress.",
    )


def _run_idat_crc_periodic_runtime(
    runtime: Any,
    data: bytes,
    analysis: idat.IdatStreamAnalysis,
) -> idat_bruteforce.IdatCrcPeriodicPayloadSolverResult | None:
    if _block_deep_beam_if_chunk_names_are_stale(runtime, data):
        return None
    model_path = _idat_convoy_model_path(runtime)
    checkpoint_path, progress_path = _idat_crc_periodic_paths(runtime)
    budget = _runtime_crc_periodic_budget(runtime)
    progress_state = idat_bruteforce.crc_periodic_progress_state(data, progress_path)
    already_consumed = (
        progress_state.available
        and progress_state.source_matches
        and progress_state.exhausted
        and progress_state.budget >= budget
    )
    if already_consumed:
        runtime.side_notes.append(
            "-IDAT crc-periodic already consumed for this source/budget: tested=%s; budget=%s; reason=%s."
            % (progress_state.tested, progress_state.budget, progress_state.reason)
        )
    else:
        runtime.candy(
            "Cowsay",
            "I am trying a CRC-guided periodic payload route. CRCs nominate; PNG raw bytes judge.",
            "com",
        )
        runtime.candy("Title", "probe_idat_crc_periodic_payload_solver")
    result = idat_bruteforce.probe_idat_crc_periodic_payload_solver(
        data,
        convoy_model_path=model_path,
        budget=budget,
        checkpoint_path=checkpoint_path,
        progress_path=progress_path,
        progress=_runtime_idat_queue_progress(runtime),
    )
    runtime.side_notes.append(idat_bruteforce.crc_periodic_payload_summary_line(result))
    runtime.side_notes.extend(idat_bruteforce.crc_periodic_payload_candidate_summary_lines(result))
    if result.top_candidates and not already_consumed:
        _write_idat_deep_beam_debug_artifacts(runtime, result, label="idat_crc_periodic", include_dynamic_trace=True)
    if result.best is None and not already_consumed:
        message = "The CRC-periodic route produced no clone-worthy PNG scanline yet."
        if "stop=candidate_pool_exhausted" in result.reason:
            message = (
                "The CRC-periodic route exhausted its constrained candidate pool before the budget; "
                "no clone-worthy PNG scanline yet."
            )
        runtime.candy(
            "Cowsay",
            message,
            "bad",
        )
    return result


def _write_crc_periodic_best_clone(
    runtime: Any,
    analysis: idat.IdatStreamAnalysis,
    result: idat_bruteforce.IdatCrcPeriodicPayloadSolverResult,
) -> tuple[bool, Any] | None:
    candidate = result.best
    if candidate is None:
        raise ValueError("crc-periodic result has no best candidate")
    summary = "\n".join(
        (
            "-Repair hypothesis tried: CRC-guided periodic IDAT payload solver.",
            idat_deflate_header_note(analysis),
            idat_bruteforce.crc_periodic_payload_summary_line(result),
            *idat_bruteforce.crc_periodic_payload_candidate_summary_lines(result),
            idat_stream_diagnosis_note(candidate.after),
        )
    )
    return _write_complete_idat_candidate_clone(
        runtime,
        candidate,
        summary,
        route_label="CRC-periodic route",
        success_message="The CRC-periodic route found a complete IDAT candidate with validated image progress.",
    )


def _run_idat_global_crc_residue_runtime(
    runtime: Any,
    data: bytes,
    analysis: idat.IdatStreamAnalysis,
) -> idat_bruteforce.IdatGlobalCrcResidueSolverResult | None:
    if _block_deep_beam_if_chunk_names_are_stale(runtime, data):
        return None
    model_path = _idat_convoy_model_path(runtime)
    checkpoint_path, progress_path = _idat_global_crc_residue_paths(runtime)
    budget = _runtime_global_crc_residue_budget(runtime)
    progress_state = idat_bruteforce.global_crc_residue_progress_state(data, progress_path)
    already_consumed = (
        progress_state.available
        and progress_state.source_matches
        and progress_state.exhausted
        and progress_state.budget >= budget
    )
    if already_consumed:
        runtime.side_notes.append(
            "-IDAT global-crc-residue already consumed for this source/budget: tested=%s; budget=%s; reason=%s."
            % (progress_state.tested, progress_state.budget, progress_state.reason)
        )
    else:
        runtime.candy(
            "Cowsay",
            "I am trying a global CRC residue model. CRCs nominate; deflate and PNG raw bytes judge.",
            "com",
        )
        runtime.candy("Title", "probe_idat_global_crc_residue_solver")
    result = idat_bruteforce.probe_idat_global_crc_residue_solver(
        data,
        convoy_model_path=model_path,
        budget=budget,
        checkpoint_path=checkpoint_path,
        progress_path=progress_path,
        progress=_runtime_idat_queue_progress(runtime),
    )
    runtime.side_notes.append(idat_bruteforce.global_crc_residue_summary_line(result))
    runtime.side_notes.extend(idat_bruteforce.global_crc_residue_candidate_summary_lines(result))
    if result.top_candidates and not already_consumed:
        _write_idat_deep_beam_debug_artifacts(runtime, result, label="idat_global_crc_residue", include_dynamic_trace=True)
    if result.best is None and not already_consumed:
        message = "The global CRC residue route produced no clone-worthy PNG scanline yet."
        if "stop=candidate_pool_exhausted" in result.reason:
            message = (
                "The global CRC residue route exhausted its constrained candidate pool before the budget; "
                "no clone-worthy PNG scanline yet."
            )
        runtime.candy(
            "Cowsay",
            message,
            "bad",
        )
    return result


def _write_global_crc_residue_best_clone(
    runtime: Any,
    analysis: idat.IdatStreamAnalysis,
    result: idat_bruteforce.IdatGlobalCrcResidueSolverResult,
) -> tuple[bool, Any] | None:
    candidate = result.best
    if candidate is None:
        raise ValueError("global CRC residue result has no best candidate")
    summary = "\n".join(
        (
            "-Repair hypothesis tried: global CRC residue IDAT solver.",
            idat_deflate_header_note(analysis),
            idat_bruteforce.global_crc_residue_summary_line(result),
            *idat_bruteforce.global_crc_residue_candidate_summary_lines(result),
            idat_stream_diagnosis_note(candidate.after),
        )
    )
    return _write_complete_idat_candidate_clone(
        runtime,
        candidate,
        summary,
        route_label="global CRC residue route",
        success_message="The global CRC residue route found a complete IDAT candidate with validated image progress.",
    )


def _run_deflate_resync_salvage_runtime(
    runtime: Any,
    data: bytes,
    analysis: idat.IdatStreamAnalysis,
) -> idat_bruteforce.DeflateResyncSalvageResult | None:
    if _block_deep_beam_if_chunk_names_are_stale(runtime, data):
        return None
    _checkpoint_path, progress_path = _idat_deflate_salvage_paths(runtime)
    budget = _runtime_deflate_salvage_budget(runtime)
    progress_state = idat_bruteforce.deflate_salvage_progress_state(data, progress_path)
    if progress_state.available and progress_state.source_matches and progress_state.exhausted and progress_state.budget >= budget:
        runtime.side_notes.append(
            "-IDAT deflate-salvage already consumed for this source/budget: tested=%s; budget=%s; reason=%s."
            % (progress_state.tested, progress_state.budget, progress_state.reason)
        )
        return None
    runtime.candy(
        "Cowsay",
        "I am trying a deflate resync salvage preview route. This writes debug evidence only, not a Fixed clone.",
        "com",
    )
    runtime.candy("Title", "probe_deflate_resync_salvage")
    result = idat_bruteforce.probe_deflate_resync_salvage(
        data,
        budget=budget,
        progress_path=progress_path,
        preview_path=_idat_deflate_salvage_preview_path(runtime),
        progress=_runtime_idat_queue_progress(runtime),
    )
    runtime.side_notes.append(idat_bruteforce.deflate_resync_salvage_summary_line(result))
    if result.preview_path:
        runtime.candy(
            "Cowsay",
            "The salvage route wrote a partial preview artifact, but it is not a final PNG repair.",
            "com",
        )
    else:
        runtime.candy(
            "Cowsay",
            "The salvage route found no usable partial preview yet.",
            "bad",
        )
    return result


def _block_deep_beam_if_chunk_names_are_stale(runtime: Any, data: bytes) -> bool:
    _chunks, problems, status = _chunk_name_audit(data)
    if status == "ok" and not problems:
        return False
    details = "; ".join(problems) if problems else status
    runtime.side_notes.append(
        "-IDAT deep beam blocked: convoy clone not active/stale; chunk-name audit still reports %s."
        % details
    )
    runtime.candy(
        "Cowsay",
        "I am not launching the deep IDAT beam because chunk names are not clean in the active PNG. Convoy clone not active/stale.",
        "bad",
    )
    return True


def _run_idat_deep_beam_runtime(
    runtime: Any,
    data: bytes,
    analysis: idat.IdatStreamAnalysis,
    *,
    checkpoint_path: str,
    progress_path: str,
    resume_state: idat_bruteforce.IdatDeepBeamResumeState | None = None,
    seed_candidates: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...] = (),
    final_investigation_ready: bool | None = None,
) -> tuple[bool, Any] | None:
    if _block_deep_beam_if_chunk_names_are_stale(runtime, data):
        _consume_idat_deflate_route(runtime)
        return False, None

    if resume_state is not None and resume_state.available and resume_state.source_matches:
        runtime.candy(
            "Cowsay",
            "I found an existing deep-beam checkpoint/progress for this IDAT stream. Resuming from there.",
            "com",
        )
        runtime.side_notes.append(
            "-IDAT deep beam resume: source matched; tested=%s; depth=%s; interrupted=%s; reason=%s."
            % (
                resume_state.tested,
                resume_state.depth,
                "yes" if resume_state.interrupted else "no",
                resume_state.reason,
            )
        )
    else:
        runtime.candy(
            "Cowsay",
            "I am launching the aggressive deep IDAT beam now. It is checkpointed; CRCs remain evidence, not a final proof.",
            "com",
        )

    deep_workers, deep_gpu, deep_gpu_config, deep_budget, deep_gpu_shard_size, deep_cpu_batch_size = _runtime_deep_beam_options(runtime)
    deep_max_depth, depth_auto_bumped = _runtime_deep_beam_max_depth(runtime, resume_state)
    runtime.side_notes.append(
        "-IDAT deep beam depth configuration: max_depth=%s; auto_bumped_from_resume=%s."
        % (deep_max_depth, "yes" if depth_auto_bumped else "no")
    )
    if depth_auto_bumped:
        runtime.candy(
            "Cowsay",
            "The previous deep beam hit the depth guard before the budget. I am raising the max depth for this resume instead of replaying the same wall.",
            "com",
        )
    if seed_candidates:
        runtime.side_notes.append(
            "-IDAT deep beam seeded with %s frontier candidate(s)." % len(seed_candidates)
        )
    runtime.candy("Title", "probe_idat_deflate_deep_beam")
    deep_probe = idat_bruteforce.probe_idat_deflate_deep_beam(
        data,
        budget=deep_budget,
        max_depth=deep_max_depth,
        workers=deep_workers,
        gpu=deep_gpu,
        gpu_config=deep_gpu_config,
        gpu_shard_size=deep_gpu_shard_size,
        cpu_batch_size=deep_cpu_batch_size,
        checkpoint_path=checkpoint_path,
        progress_path=progress_path,
        seed_candidates=seed_candidates,
        progress=_runtime_idat_queue_progress(runtime),
    )
    runtime.side_notes.append(idat_bruteforce.deep_beam_summary_line(deep_probe))
    runtime.side_notes.extend(idat_bruteforce.deep_beam_candidate_summary_lines(deep_probe))
    _write_idat_deep_beam_debug_artifacts(runtime, deep_probe)
    if deep_probe.interrupted:
        runtime.candy(
            "Cowsay",
            "Deep beam interrupted; checkpoint/progress are saved, so I am stopping this run now.",
            "bad",
        )
        runtime.side_notes.append(
            "-IDAT deep beam interrupted by user; checkpoint/progress saved, stopping repair pass."
        )
        raise SystemExit(130)
    if deep_probe.best is None:
        runtime.candy(
            "Cowsay",
            "The deep beam kept diagnostic candidates, but none reached usable scanlines yet.",
            "bad",
        )
        runtime.side_notes.append("-IDAT deep beam found no clone-worthy scanline progress.")
        post_deep_result = _run_idat_post_deep_frontier_routes_runtime(
            runtime,
            data,
            analysis,
            deep_probe.top_candidates,
        )
        if post_deep_result is not None:
            return post_deep_result
        if _should_run_final_investigation(
            runtime,
            analysis,
            deep_probe.top_candidates,
            evidence_ready=final_investigation_ready,
        ):
            prefinal_result, prefinal_seeds, prefinal_deferred = _GroundHogDay_run_idat_prefinal_seed_routes_runtime(
                runtime,
                data,
                analysis,
                deep_probe.top_candidates,
            )
            if prefinal_result is not None:
                return prefinal_result
            if prefinal_deferred:
                return None
            final_result = _run_idat_final_investigation_runtime(
                runtime,
                data,
                analysis,
                seed_candidates=prefinal_seeds or deep_probe.top_candidates,
            )
            if final_result is not None:
                return final_result
            return None
        if deep_probe.budget_exhausted:
            runtime.side_notes.append(
                "-IDAT deep beam budget exhausted for this source/budget; increase IDAT_DEEP_BEAM_BUDGET or remove checkpoint/progress to relaunch."
            )
        if resume_state is not None and resume_state.available and resume_state.source_matches:
            runtime.side_notes.append("-IDAT deep beam resume did not return to short probes; checkpoint/progress remain the next state.")
        if _idat_deep_beam_failure_is_terminal(deep_probe):
            _consume_idat_deflate_route(runtime)
        else:
            runtime.side_notes.append(
                "-IDAT deep beam stopped with checkpointed candidates still available; route left open for resume/post-deep passes."
            )
            runtime.candy(
                "Cowsay",
                "The deep beam stopped with checkpointed seeds still alive. I am leaving the IDAT route open instead of calling it exhausted.",
                "com",
            )
        return False, None

    candidate = deep_probe.best
    summary = "\n".join(
        (
            "-Repair hypothesis tried: aggressive IDAT deflate deep beam.",
            idat_deflate_header_note(analysis),
            idat_bruteforce.deep_beam_summary_line(deep_probe),
            *idat_bruteforce.deep_beam_candidate_summary_lines(deep_probe),
            idat_stream_diagnosis_note(candidate.after),
        )
    )
    written = _write_complete_idat_candidate_clone(
        runtime,
        candidate,
        summary,
        route_label="deep beam",
        success_message="The deep beam found a complete IDAT candidate with validated image progress.",
    )
    if written is not None:
        return written
    post_deep_result = _run_idat_post_deep_frontier_routes_runtime(
        runtime,
        data,
        analysis,
        _merge_idat_seed_candidates((candidate,), deep_probe.top_candidates),
    )
    if post_deep_result is not None:
        return post_deep_result
    return None


def _idat_deflate_header_for_data(data: bytes) -> deflate_header.DeflateHeaderAnalysis | None:
    try:
        stream = b"".join(
            chunk.data for chunk in png.iter_chunks(data) if chunk.chunk_type == b"IDAT"
        )
    except Exception:
        return None
    if not stream:
        return None
    try:
        return deflate_header.analyze_deflate_header(stream)
    except Exception:
        return None


def _is_false_fixed_huffman_diagnostic(
    before: idat.IdatStreamAnalysis,
    candidate: idat_bruteforce.SuperMegaLinefeedCandidate,
) -> bool:
    if idat_bruteforce.is_material_improvement(before, candidate.after):
        return False
    before_header = before.deflate_header
    if before_header is None:
        return False
    if before_header.btype != 2:
        return False
    after_header = candidate.after.deflate_header or _idat_deflate_header_for_data(candidate.data)
    return bool(after_header is not None and after_header.ok and after_header.btype != before_header.btype)


def _probe_idat_lf_route_for_diagnostics(runtime: Any, data: bytes, analysis: idat.IdatStreamAnalysis) -> None:
    runtime.candy(
        "Cowsay",
        "I am also trying the missing-LF hypothesis around the deflate wound and logging the trail.",
        "com",
    )
    runtime.candy("Title", "probe_idat_linefeed_lf_insertions")
    lf_probe = idat_bruteforce.probe_idat_linefeed_lf_insertions(
        data,
        window_radius=512,
        budget=1024,
        progress=_runtime_idat_queue_progress(runtime),
    )
    runtime.side_notes.append(idat_bruteforce.linefeed_insert_probe_summary_line(lf_probe))
    if lf_probe.best is not None:
        runtime.side_notes.append(idat_bruteforce.linefeed_insert_candidate_summary_line(lf_probe.best))
        runtime.candy(
            "Cowsay",
            "The LF route moves zlib, but I still need usable PNG scanlines before I write anything.",
            "com",
        )

    runtime.candy("Title", "probe_super_mega_linefeed_force_of_death")
    super_probe = idat_bruteforce.probe_super_mega_linefeed_force_of_death(
        data,
        start_offset=analysis.error_offset,
        pre_error_backtrack=512,
        beam_width=8,
        max_depth=2,
        linefeed_budget=0,
        structural_budget=0,
        local_bit_budget=0,
        local_byte_budget=0,
        heavy_byte_budget=0,
        adler_budget=0,
        lf_insert_budget=2048,
        structural_forward=256,
        progress=_runtime_idat_queue_progress(runtime),
    )
    runtime.side_notes.append(idat_bruteforce.super_mega_linefeed_probe_summary_line(super_probe))
    runtime.side_notes.extend(idat_bruteforce.super_mega_linefeed_phase_summary_lines(super_probe))
    if super_probe.best is not None:
        runtime.side_notes.append(idat_bruteforce.super_mega_linefeed_candidate_summary_line(super_probe.best))
        if _is_false_fixed_huffman_diagnostic(analysis, super_probe.best):
            runtime.side_notes.append(
                "-IDAT diagnostic LF artifact skipped: candidate changes dynamic Huffman to fixed Huffman without usable scanlines."
            )
        elif super_probe.best.after.decompressed_size > analysis.decompressed_size:
            _write_idat_diagnostic_artifact(
                runtime,
                super_probe.best,
                label="idat_lf_diagnostic",
            )


def _run_idat_frontier_routes_runtime(
    runtime: Any,
    data: bytes,
    analysis: idat.IdatStreamAnalysis,
) -> tuple[tuple[bool, Any] | None, tuple[idat_bruteforce.IdatDeepBeamCandidate, ...]]:
    seed_groups: list[tuple[idat_bruteforce.IdatDeepBeamCandidate, ...]] = []

    periodic_result = _run_idat_periodic_model_runtime(runtime, data, analysis)
    if periodic_result is not None:
        if periodic_result.best is not None:
            written = _write_periodic_model_best_clone(runtime, analysis, periodic_result)
            if written is not None:
                return written, ()
        seed_groups.append(periodic_result.top_candidates)

    affine_result = _run_idat_affine_corruption_runtime(runtime, data, analysis)
    if affine_result is not None:
        if affine_result.best is not None:
            written = _write_affine_corruption_best_clone(runtime, analysis, affine_result)
            if written is not None:
                return written, ()
        seed_groups.append(affine_result.top_candidates)

    kraft_seed_candidates = tuple(itertools.chain.from_iterable(seed_groups))
    kraft_result = _run_idat_huffman_kraft_runtime(
        runtime,
        data,
        analysis,
        seed_candidates=kraft_seed_candidates,
    )
    if kraft_result is not None:
        if kraft_result.best is not None:
            written = _write_huffman_kraft_best_clone(runtime, analysis, kraft_result)
            if written is not None:
                return written, ()
        seed_groups.append(kraft_result.top_candidates)

    first_filter_seed_candidates = kraft_result.top_candidates if kraft_result is not None else tuple(itertools.chain.from_iterable(seed_groups))
    first_filter_result = _run_idat_first_filter_literal_runtime(
        runtime,
        data,
        analysis,
        seed_candidates=first_filter_seed_candidates,
    )
    if first_filter_result is not None:
        if first_filter_result.best is not None:
            written = _write_first_filter_literal_best_clone(runtime, analysis, first_filter_result)
            if written is not None:
                return written, ()
        seed_groups.append(first_filter_result.top_candidates)

    kraft_backref_seed_candidates = (
        first_filter_result.top_candidates
        if first_filter_result is not None and first_filter_result.top_candidates
        else kraft_result.top_candidates if kraft_result is not None else ()
    )
    kraft_backref_result = _run_idat_kraft_backref_runtime(
        runtime,
        data,
        analysis,
        seed_candidates=kraft_backref_seed_candidates,
    )
    if kraft_backref_result is not None:
        if kraft_backref_result.best is not None:
            written = _write_kraft_backref_best_clone(runtime, analysis, kraft_backref_result)
            if written is not None:
                return written, ()
        seed_groups.append(kraft_backref_result.top_candidates)

    stored_block_seed_candidates = (
        kraft_backref_result.top_candidates
        if kraft_backref_result is not None and kraft_backref_result.top_candidates
        else ()
    )
    if stored_block_seed_candidates:
        stored_block_result = _run_idat_stored_block_runtime(
            runtime,
            data,
            analysis,
            seed_candidates=stored_block_seed_candidates,
        )
        if stored_block_result is not None:
            if stored_block_result.best is not None:
                written = _write_stored_block_best_clone(runtime, analysis, stored_block_result)
                if written is not None:
                    return written, ()
            seed_groups.append(stored_block_result.top_candidates)

    huffman_seed_candidates = tuple(itertools.chain.from_iterable(seed_groups))
    huffman_result = _run_idat_huffman_oracle_runtime(
        runtime,
        data,
        analysis,
        seed_candidates=huffman_seed_candidates,
    )
    if huffman_result is not None:
        if huffman_result.best is not None:
            written = _write_huffman_oracle_best_clone(runtime, analysis, huffman_result)
            if written is not None:
                return written, ()
        seed_groups.append(huffman_result.top_candidates)

    oracle_backref_seed_candidates = (
        huffman_result.top_candidates
        if huffman_result is not None and huffman_result.top_candidates
        else ()
    )
    oracle_backref_result = None
    if oracle_backref_seed_candidates:
        oracle_backref_result = _run_idat_kraft_backref_runtime(
            runtime,
            data,
            analysis,
            seed_candidates=oracle_backref_seed_candidates,
            path_label="kraft_backref_oracle",
            seed_checkpoint_path="",
        )
        if oracle_backref_result is not None:
            if oracle_backref_result.best is not None:
                written = _write_kraft_backref_best_clone(runtime, analysis, oracle_backref_result)
                if written is not None:
                    return written, ()
            seed_groups.append(oracle_backref_result.top_candidates)

    oracle_stored_block_seed_candidates = (
        oracle_backref_result.top_candidates
        if oracle_backref_result is not None
        and oracle_backref_result.top_candidates
        else ()
    )
    if oracle_stored_block_seed_candidates:
        oracle_stored_block_result = _run_idat_stored_block_runtime(
            runtime,
            data,
            analysis,
            seed_candidates=oracle_stored_block_seed_candidates,
            path_label="stored_block_oracle",
            seed_checkpoint_path="",
        )
        if oracle_stored_block_result is not None:
            if oracle_stored_block_result.best is not None:
                written = _write_stored_block_best_clone(runtime, analysis, oracle_stored_block_result)
                if written is not None:
                    return written, ()
            seed_groups.append(oracle_stored_block_result.top_candidates)

    global_crc_result = _run_idat_global_crc_residue_runtime(runtime, data, analysis)
    if global_crc_result is not None:
        if global_crc_result.best is not None:
            written = _write_global_crc_residue_best_clone(runtime, analysis, global_crc_result)
            if written is not None:
                return written, ()
        seed_groups.append(global_crc_result.top_candidates)

    crc_periodic_result = _run_idat_crc_periodic_runtime(runtime, data, analysis)
    if crc_periodic_result is not None:
        if crc_periodic_result.best is not None:
            written = _write_crc_periodic_best_clone(runtime, analysis, crc_periodic_result)
            if written is not None:
                return written, ()
        seed_groups.append(crc_periodic_result.top_candidates)

    return None, tuple(itertools.chain.from_iterable(seed_groups))


def _idat_root_frontier_seed(
    data: bytes,
    analysis: idat.IdatStreamAnalysis,
) -> idat_bruteforce.IdatDeepBeamCandidate | None:
    try:
        chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(data)
    except Exception:
        return None
    return idat_bruteforce._frontier_root_candidate(
        data=data,
        stream=stream,
        before=analysis,
        original_idat_count=sum(1 for chunk in chunks if chunk.chunk_type == b"IDAT"),
    )


def _run_idat_prefix_frontier_routes_runtime(
    runtime: Any,
    data: bytes,
    analysis: idat.IdatStreamAnalysis,
) -> tuple[bool, Any] | None:
    root = _idat_root_frontier_seed(data, analysis)
    if root is None:
        return None
    root_seed = (root,)
    stored_first = "stored block" in str(analysis.zlib_error or analysis.reason or "").lower()
    if stored_first:
        stored_result = _run_idat_stored_block_runtime(
            runtime,
            data,
            analysis,
            seed_candidates=root_seed,
            path_label="stored_block_prefix",
            seed_checkpoint_path="",
        )
        if stored_result is not None and stored_result.best is not None:
            written = _write_stored_block_best_clone(runtime, analysis, stored_result)
            if written is not None:
                return written
        backref_seeds = stored_result.top_candidates if stored_result is not None and stored_result.top_candidates else root_seed
    else:
        backref_seeds = root_seed

    backref_result = _run_idat_kraft_backref_runtime(
        runtime,
        data,
        analysis,
        seed_candidates=backref_seeds,
        path_label="kraft_backref_prefix",
        seed_checkpoint_path="",
    )
    if backref_result is not None and backref_result.best is not None:
        written = _write_kraft_backref_best_clone(runtime, analysis, backref_result)
        if written is not None:
            return written

    stored_seeds = (
        backref_result.top_candidates
        if backref_result is not None and backref_result.top_candidates
        else root_seed
    )
    stored_result = _run_idat_stored_block_runtime(
        runtime,
        data,
        analysis,
        seed_candidates=stored_seeds,
        path_label="stored_block_prefix",
        seed_checkpoint_path="",
    )
    if stored_result is not None and stored_result.best is not None:
        written = _write_stored_block_best_clone(runtime, analysis, stored_result)
        if written is not None:
            return written
    return None


def _idat_original_idat_count(data: bytes) -> int:
    try:
        chunks, _stream = idat_bruteforce._all_chunks_and_idat_stream(data)
    except Exception:
        return 1
    return sum(1 for chunk in chunks if chunk.chunk_type == b"IDAT")


def _rank_idat_seed_candidates(
    seed_candidates: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...],
    *,
    limit: int,
) -> tuple[idat_bruteforce.IdatDeepBeamCandidate, ...]:
    merged = _merge_idat_seed_candidates(seed_candidates)
    if not merged:
        return ()
    return idat_bruteforce._deep_beam_ranked_unique(merged, limit=max(1, int(limit)))


def _idat_seed_local_continuation_candidate(
    parent: idat_bruteforce.IdatDeepBeamCandidate,
    candidate: idat_bruteforce.IdatDeflateCandidate,
    *,
    before: idat.IdatStreamAnalysis,
    state_id: int,
    original_idat_count: int,
    kind: str = "seed-local-deflate",
) -> idat_bruteforce.IdatDeepBeamCandidate | None:
    return idat_bruteforce._deep_beam_candidate_from_deflate_candidate(
        parent,
        candidate,
        before=before,
        state_id=state_id,
        original_idat_count=original_idat_count,
        kind=kind,
    )


def _idat_deflate_probe_candidate_options(
    probe: idat_bruteforce.IdatDeflateProbeResult,
) -> tuple[tuple[idat_bruteforce.IdatDeflateCandidate, str], ...]:
    options: list[tuple[idat_bruteforce.IdatDeflateCandidate, str]] = []
    seen: set[bytes] = set()
    for candidate, suffix in (
        (probe.best, ""),
        (probe.diagnostic_best, "-diagnostic"),
    ):
        if candidate is None:
            continue
        digest = hashlib.sha1(candidate.data).digest()
        if digest in seen:
            continue
        seen.add(digest)
        options.append((candidate, suffix))
    return tuple(options)


def _run_idat_seed_local_continuation_runtime(
    runtime: Any,
    data: bytes,
    analysis: idat.IdatStreamAnalysis,
    seed_candidates: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...] = (),
) -> tuple[tuple[bool, Any] | None, tuple[idat_bruteforce.IdatDeepBeamCandidate, ...]]:
    if _block_deep_beam_if_chunk_names_are_stale(runtime, data):
        return None, ()

    seed_limit = _runtime_seed_local_continuation_limit(runtime)
    local_budget = _runtime_seed_local_continuation_budget(runtime)
    local_rounds = _runtime_seed_local_continuation_rounds(runtime)
    seeds = seed_candidates
    if not seeds:
        seeds = _load_idat_artifact_seed_candidates(
            runtime,
            data,
            analysis,
            limit=seed_limit,
        )
    if not seeds:
        seeds = _load_final_investigation_seed_candidates(
            runtime,
            data,
            analysis,
            seed_candidates=(),
        )
    seeds = _rank_idat_seed_candidates(seeds, limit=seed_limit)
    if not seeds:
        return None, ()

    runtime.side_notes.append(
        "-IDAT seed-local continuation: probing %s seed(s) with budget=%s for up to %s round(s) each before %s."
        % (
            len(seeds),
            local_budget,
            local_rounds,
            FINAL_INVESTIGATION_LABEL,
        )
    )
    runtime.candy(
        "Cowsay",
        "I have stronger IDAT seeds now, so I am probing locally around their current deflate wound before %s."
        % FINAL_INVESTIGATION_LABEL,
        "com",
    )
    _GroundHogDay_emit_quote_before_title(runtime)
    runtime.candy("Title", "probe_idat_seed_local_continuation")

    original_idat_count = _idat_original_idat_count(data)
    next_state_id = max((int(getattr(seed, "state_id", 0)) for seed in seeds), default=0) + 1
    continuations: list[idat_bruteforce.IdatDeepBeamCandidate] = []
    tested = 0
    window_starts: list[int] = []
    window_ends: list[int] = []
    progress = _runtime_idat_queue_progress(runtime)

    for seed in seeds:
        parent = seed
        before_seed = getattr(parent, "after", None)
        if before_seed is None or getattr(before_seed, "complete", False):
            continue
        for _round_index in range(local_rounds):
            if getattr(parent.after, "complete", False):
                break
            probe = idat_bruteforce.probe_idat_deflate_local_candidates(
                parent.data,
                budget=local_budget,
                progress=progress,
            )
            tested += int(probe.tested_candidates)
            window_starts.append(int(probe.window_start))
            window_ends.append(int(probe.window_end))
            candidate_options = _idat_deflate_probe_candidate_options(probe)
            if not candidate_options:
                break
            runtime.side_notes.append(idat_bruteforce.probe_summary_line(probe))
            runtime.side_notes.extend(idat_bruteforce.candidate_summary_lines(probe))
            runtime.side_notes.extend(idat_bruteforce.diagnostic_candidate_summary_lines(probe))
            round_continuations: list[idat_bruteforce.IdatDeepBeamCandidate] = []
            for deflate_candidate, suffix in candidate_options:
                continuation = _idat_seed_local_continuation_candidate(
                    parent,
                    deflate_candidate,
                    before=analysis,
                    state_id=next_state_id,
                    original_idat_count=original_idat_count,
                    kind="seed-local-deflate%s" % suffix,
                )
                if continuation is None:
                    continue
                continuations.append(continuation)
                round_continuations.append(continuation)
                next_state_id += 1
            if not round_continuations:
                break
            parent = _rank_idat_seed_candidates(tuple(round_continuations), limit=1)[0]
            if _idat_candidate_is_complete_clone(parent):
                break
        if continuations and _idat_candidate_is_complete_clone(continuations[-1]):
            break

    top = _rank_idat_seed_candidates(tuple(continuations), limit=max(seed_limit, IDAT_DEBUG_ARTIFACT_TOP_LIMIT))
    if not top:
        runtime.side_notes.append("-IDAT seed-local continuation produced no stronger seed.")
        return None, ()

    best = next((candidate for candidate in top if _idat_candidate_is_complete_clone(candidate)), top[0])
    result = idat_bruteforce.IdatDeepBeamProbeResult(
        before=analysis,
        best=best,
        top_candidates=top,
        window_start=min(window_starts) if window_starts else 0,
        window_end=max(window_ends) if window_ends else 0,
        tested_candidates=tested,
        budget_exhausted=False,
        reached_depth=max((len(candidate.operations) for candidate in top), default=0),
        state_count=next_state_id,
        visited_count=len(top),
        strategy="seed-local-continuation",
        reason="seeds=%s; continuations=%s" % (len(seeds), len(top)),
    )
    runtime.side_notes.append(idat_bruteforce.deep_beam_summary_line(result))
    runtime.side_notes.extend(idat_bruteforce.deep_beam_candidate_summary_lines(result))
    _write_idat_deep_beam_debug_artifacts(
        runtime,
        result,
        label="idat_seed_local_continuation",
        include_dynamic_trace=True,
    )
    summary = "\n".join(
        (
            "-Repair hypothesis tried: seed-local IDAT deflate continuation.",
            idat_deflate_header_note(analysis),
            idat_bruteforce.deep_beam_summary_line(result),
            *idat_bruteforce.deep_beam_candidate_summary_lines(result),
            idat_stream_diagnosis_note(best.after),
        )
    )
    written = _write_complete_idat_candidate_clone(
        runtime,
        best,
        summary,
        route_label="seed-local continuation",
        success_message="The seed-local continuation found a complete IDAT candidate with validated image progress.",
    )
    if written is not None:
        return written, top
    return None, top


def _run_idat_filter_alignment_runtime(
    runtime: Any,
    data: bytes,
    analysis: idat.IdatStreamAnalysis,
    seed_candidates: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...] = (),
) -> tuple[tuple[bool, Any] | None, tuple[idat_bruteforce.IdatDeepBeamCandidate, ...]]:
    if _block_deep_beam_if_chunk_names_are_stale(runtime, data):
        return None, ()

    seed_limit = _runtime_seed_local_continuation_limit(runtime)
    local_budget = _runtime_seed_local_continuation_budget(runtime)
    seeds = _rank_idat_seed_candidates(seed_candidates, limit=seed_limit)
    if not seeds:
        seeds = _load_idat_artifact_seed_candidates(
            runtime,
            data,
            analysis,
            limit=seed_limit,
        )
    if not seeds:
        return None, ()

    runtime.side_notes.append(
        "-IDAT PNG-filter local alignment: probing %s seed(s) with budget=%s before %s."
        % (len(seeds), local_budget, FINAL_INVESTIGATION_LABEL)
    )
    runtime.candy(
        "Cowsay",
        "I am checking the local IDAT wound again, this time scoring PNG row-filter markers before raw byte length.",
        "com",
    )
    runtime.candy("Title", "probe_idat_deflate_local_candidates_png_filter")

    original_idat_count = _idat_original_idat_count(data)
    next_state_id = max((int(getattr(seed, "state_id", 0)) for seed in seeds), default=0) + 1
    continuations: list[idat_bruteforce.IdatDeepBeamCandidate] = []
    tested = 0
    window_starts: list[int] = []
    window_ends: list[int] = []
    progress = _runtime_idat_queue_progress(runtime)

    for parent in seeds:
        if getattr(parent.after, "complete", False):
            continue
        probe = idat_bruteforce.probe_idat_deflate_local_candidates(
            parent.data,
            budget=local_budget,
            score_mode="png-filter",
            progress=progress,
        )
        tested += int(probe.tested_candidates)
        window_starts.append(int(probe.window_start))
        window_ends.append(int(probe.window_end))
        runtime.side_notes.append(idat_bruteforce.probe_summary_line(probe))
        runtime.side_notes.extend(idat_bruteforce.candidate_summary_lines(probe))
        runtime.side_notes.extend(idat_bruteforce.diagnostic_candidate_summary_lines(probe))
        candidate_options = _idat_deflate_probe_candidate_options(probe)
        if not candidate_options:
            continue
        for deflate_candidate, suffix in candidate_options:
            continuation = _idat_seed_local_continuation_candidate(
                parent,
                deflate_candidate,
                before=analysis,
                state_id=next_state_id,
                original_idat_count=original_idat_count,
                kind="seed-local-png-filter%s" % suffix,
            )
            if continuation is None:
                continue
            continuations.append(continuation)
            next_state_id += 1
            if _idat_candidate_is_complete_clone(continuation):
                break
        if continuations and _idat_candidate_is_complete_clone(continuations[-1]):
            break

    top = _rank_idat_seed_candidates(tuple(continuations), limit=max(seed_limit, IDAT_DEBUG_ARTIFACT_TOP_LIMIT))
    if not top:
        runtime.side_notes.append("-IDAT PNG-filter local alignment produced no stronger filter seed.")
        return None, ()

    best = next((candidate for candidate in top if _idat_candidate_is_complete_clone(candidate)), top[0])
    result = idat_bruteforce.IdatDeepBeamProbeResult(
        before=analysis,
        best=best,
        top_candidates=top,
        window_start=min(window_starts) if window_starts else 0,
        window_end=max(window_ends) if window_ends else 0,
        tested_candidates=tested,
        budget_exhausted=False,
        reached_depth=max((len(candidate.operations) for candidate in top), default=0),
        state_count=next_state_id,
        visited_count=len(top),
        strategy="png-filter-local-alignment",
        reason="seeds=%s; continuations=%s" % (len(seeds), len(top)),
    )
    runtime.side_notes.append(idat_bruteforce.deep_beam_summary_line(result))
    runtime.side_notes.extend(idat_bruteforce.deep_beam_candidate_summary_lines(result))
    _write_idat_deep_beam_debug_artifacts(
        runtime,
        result,
        label="idat_filter_alignment",
        include_dynamic_trace=True,
    )
    summary = "\n".join(
        (
            "-Repair hypothesis tried: PNG row-filter local IDAT alignment.",
            idat_deflate_header_note(analysis),
            idat_bruteforce.deep_beam_summary_line(result),
            *idat_bruteforce.deep_beam_candidate_summary_lines(result),
            idat_stream_diagnosis_note(best.after),
        )
    )
    written = _write_complete_idat_candidate_clone(
        runtime,
        best,
        summary,
        route_label="PNG-filter local alignment",
        success_message="The PNG-filter local alignment route found a complete IDAT candidate with validated image progress.",
    )
    if written is not None:
        return written, top
    return None, top


def _idat_deflate_probe_best_progress_score(
    probe: idat_bruteforce.IdatDeflateProbeResult,
) -> tuple[int, int, int, int, int, int]:
    after = getattr(probe.best, "after", None)
    if after is None:
        return (-1, -1, -1, -1, -1, -1)
    return (
        1 if getattr(after, "complete", False) else 0,
        int(getattr(after, "usable_scanlines", 0) or 0),
        int(getattr(after, "complete_scanlines", 0) or 0),
        int(getattr(after, "decompressed_size", 0) or 0),
        int(getattr(after, "error_offset", -1) or -1),
        -len(getattr(probe, "chain", ()) or ()),
    )


def _run_idat_row_filter_literal_repair_runtime(
    runtime: Any,
    data: bytes,
    analysis: idat.IdatStreamAnalysis,
    seed_candidates: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...] = (),
) -> tuple[tuple[bool, Any] | None, tuple[idat_bruteforce.IdatDeepBeamCandidate, ...]]:
    if _block_deep_beam_if_chunk_names_are_stale(runtime, data):
        return None, ()

    seed_limit = _runtime_seed_local_continuation_limit(runtime)
    seeds = _rank_idat_seed_candidates(seed_candidates, limit=seed_limit)
    if not seeds:
        seeds = _load_idat_artifact_seed_candidates(
            runtime,
            data,
            analysis,
            limit=seed_limit,
        )
    if not seeds:
        return None, ()

    runtime.side_notes.append(
        "-IDAT row-filter literal repair: probing %s seed(s) before %s."
        % (len(seeds), FINAL_INVESTIGATION_LABEL)
    )
    runtime.candy(
        "Cowsay",
        "I am checking whether invalid PNG row-filter bytes map directly to literal IDAT bytes.",
        "com",
    )
    runtime.candy("Title", "probe_idat_png_filter_literal_repair")

    original_idat_count = _idat_original_idat_count(data)
    next_state_id = max((int(getattr(seed, "state_id", 0)) for seed in seeds), default=0) + 1
    continuations: list[idat_bruteforce.IdatDeepBeamCandidate] = []
    tested = 0
    window_starts: list[int] = []
    window_ends: list[int] = []
    progress = _runtime_idat_queue_progress(runtime)

    for seed in seeds:
        if getattr(seed.after, "complete", False):
            continue
        probe = idat_bruteforce.probe_idat_png_filter_literal_repair(
            seed.data,
            max_rows=32,
            max_repairs=4,
            replacement_filter=0,
            search_radius=4,
            candidate_budget=4000,
            progress=progress,
        )
        fast_tested = int(probe.tested_candidates)
        selected_probe_already_counted = False
        if probe.best is None:
            runtime.side_notes.append(
                "-IDAT row-filter literal repair fast pass produced no stronger seed; trying the wider row-filter pass."
            )
            probe = idat_bruteforce.probe_idat_png_filter_literal_repair(
                seed.data,
                max_rows=64,
                max_repairs=64,
                replacement_filter=0,
                progress=progress,
            )
            tested += fast_tested
        if (
            probe.best is not None
            and int(getattr(probe.best.after, "usable_scanlines", 0) or 0)
            <= int(getattr(seed.after, "usable_scanlines", 0) or 0)
        ):
            runtime.side_notes.append(
                "-IDAT row-filter literal repair did not unlock a new usable row; trying a wider backtrack search around the first bad filter byte."
            )
            backtrack_probe = idat_bruteforce.probe_idat_png_filter_literal_repair(
                seed.data,
                max_rows=64,
                max_repairs=1,
                replacement_filter=0,
                search_radius=256,
                search_direction="backtrack",
                candidate_budget=12000,
                progress=progress,
            )
            tested += int(backtrack_probe.tested_candidates)
            if _idat_deflate_probe_best_progress_score(backtrack_probe) > _idat_deflate_probe_best_progress_score(probe):
                probe = backtrack_probe
                selected_probe_already_counted = True
        if not selected_probe_already_counted:
            tested += int(probe.tested_candidates)
        window_starts.append(int(probe.window_start))
        window_ends.append(int(probe.window_end))
        runtime.side_notes.append(idat_bruteforce.probe_summary_line(probe))
        runtime.side_notes.extend(idat_bruteforce.candidate_summary_lines(probe))
        if probe.best is None:
            continue

        parent = seed
        continuation = None
        for deflate_candidate in tuple(probe.chain) or (probe.best,):
            continuation = _idat_seed_local_continuation_candidate(
                parent,
                deflate_candidate,
                before=analysis,
                state_id=next_state_id,
                original_idat_count=original_idat_count,
                kind="png-filter-literal-repair",
            )
            if continuation is None:
                break
            parent = continuation
            next_state_id += 1
        if continuation is None:
            continue
        continuations.append(continuation)
        if _idat_candidate_is_complete_clone(continuation):
            break

    top = _rank_idat_seed_candidates(tuple(continuations), limit=max(seed_limit, IDAT_DEBUG_ARTIFACT_TOP_LIMIT))
    if not top:
        runtime.side_notes.append("-IDAT row-filter literal repair produced no stronger seed.")
        return None, ()

    best = next((candidate for candidate in top if _idat_candidate_is_complete_clone(candidate)), top[0])
    result = idat_bruteforce.IdatDeepBeamProbeResult(
        before=analysis,
        best=best,
        top_candidates=top,
        window_start=min(window_starts) if window_starts else 0,
        window_end=max(window_ends) if window_ends else 0,
        tested_candidates=tested,
        budget_exhausted=False,
        reached_depth=max((len(candidate.operations) for candidate in top), default=0),
        state_count=next_state_id,
        visited_count=len(top),
        strategy="png-row-filter-literal-repair",
        reason="seeds=%s; continuations=%s" % (len(seeds), len(top)),
    )
    runtime.side_notes.append(idat_bruteforce.deep_beam_summary_line(result))
    runtime.side_notes.extend(idat_bruteforce.deep_beam_candidate_summary_lines(result))
    _write_idat_deep_beam_debug_artifacts(
        runtime,
        result,
        label="idat_row_filter_repair",
        include_dynamic_trace=True,
    )
    summary = "\n".join(
        (
            "-Repair hypothesis tried: PNG row-filter literal IDAT repair.",
            idat_deflate_header_note(analysis),
            idat_bruteforce.deep_beam_summary_line(result),
            *idat_bruteforce.deep_beam_candidate_summary_lines(result),
            idat_stream_diagnosis_note(best.after),
        )
    )
    written = _write_complete_idat_candidate_clone(
        runtime,
        best,
        summary,
        route_label="PNG row-filter literal repair",
        success_message="The PNG row-filter literal repair route found a complete IDAT candidate with validated image progress.",
    )
    if written is not None:
        return written, top
    return None, top


def _run_idat_groundhogday_linefeed_runtime(
    runtime: Any,
    data: bytes,
    analysis: idat.IdatStreamAnalysis,
    seed_candidates: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...] = (),
) -> tuple[tuple[bool, Any] | None, tuple[idat_bruteforce.IdatDeepBeamCandidate, ...]]:
    if _block_deep_beam_if_chunk_names_are_stale(runtime, data):
        return None, ()

    seed_limit = _runtime_seed_local_continuation_limit(runtime)
    seeds = _rank_idat_seed_candidates(seed_candidates, limit=seed_limit)
    if not seeds:
        seeds = _load_idat_artifact_seed_candidates(
            runtime,
            data,
            analysis,
            limit=seed_limit,
        )
    if not seeds:
        return None, ()

    runtime.side_notes.append(
        "-IDAT GroundHogDay linefeed route: probing %s seed(s) before %s."
        % (len(seeds), FINAL_INVESTIGATION_LABEL)
    )
    runtime.candy(
        "Cowsay",
        "I am editing compressed IDAT bytes only. The decompressed rows are the scoreboard; noisy rows count as evidence, not proof.",
        "com",
    )
    runtime.candy("Title", "probe_idat_groundhogday_linefeed_seed_repair")

    original_idat_count = _idat_original_idat_count(data)
    next_state_id = max((int(getattr(seed, "state_id", 0)) for seed in seeds), default=0) + 1
    continuations: list[idat_bruteforce.IdatDeepBeamCandidate] = []
    tested = 0
    window_starts: list[int] = []
    window_ends: list[int] = []
    progress = _runtime_idat_queue_progress(runtime)

    for seed in seeds:
        if getattr(seed.after, "complete", False):
            continue

        for insert_probe in (
            idat_bruteforce.probe_idat_linefeed_lf_insertions(
                seed.data,
                window_radius=1024,
                budget=4096,
                progress=progress,
            ),
            idat_bruteforce.probe_idat_linefeed_cr_insertions(
                seed.data,
                window_radius=1024,
                budget=4096,
                progress=progress,
            ),
        ):
            tested += int(insert_probe.tested_candidates)
            window_starts.append(int(insert_probe.window_start))
            window_ends.append(int(insert_probe.window_end))
            runtime.side_notes.append(idat_bruteforce.linefeed_insert_probe_summary_line(insert_probe))
            if insert_probe.best is None:
                continue
            continuation = _GroundHogDay_linefeed_insert_to_seed(
                seed,
                insert_probe.best,
                before=analysis,
                state_id=next_state_id,
                original_idat_count=original_idat_count,
            )
            if continuation is None:
                continue
            continuations.append(continuation)
            next_state_id += 1
            if _idat_candidate_is_complete_clone(continuation):
                break
        if continuations and _idat_candidate_is_complete_clone(continuations[-1]):
            break

        super_probe = idat_bruteforce.probe_super_mega_linefeed_force_of_death(
            seed.data,
            start_offset=getattr(seed.after, "error_offset", None),
            pre_error_backtrack=2048,
            beam_width=8,
            max_depth=3,
            linefeed_budget=2048,
            structural_budget=512,
            local_bit_budget=512,
            local_byte_budget=1024,
            heavy_byte_budget=2048,
            adler_budget=16,
            lf_insert_budget=4096,
            structural_forward=512,
            progress=progress,
        )
        tested += int(super_probe.tested_candidates)
        window_starts.append(int(super_probe.search_start_offset))
        window_ends.append(int(super_probe.window_end))
        runtime.side_notes.append(idat_bruteforce.super_mega_linefeed_probe_summary_line(super_probe))
        runtime.side_notes.extend(idat_bruteforce.super_mega_linefeed_phase_summary_lines(super_probe))
        if super_probe.best is None:
            continue
        runtime.side_notes.append(idat_bruteforce.super_mega_linefeed_candidate_summary_line(super_probe.best))
        continuation = _GroundHogDay_super_linefeed_to_seed(
            seed,
            super_probe.best,
            before=analysis,
            state_id=next_state_id,
            original_idat_count=original_idat_count,
        )
        if continuation is None:
            continue
        continuations.append(continuation)
        next_state_id += 1
        if _idat_candidate_is_complete_clone(continuation):
            break

    ultimate_parent_seeds = _rank_idat_seed_candidates(
        _merge_idat_seed_candidates(tuple(continuations), seeds),
        limit=seed_limit,
    )
    ultimate_result, ultimate_seeds, next_state_id = _run_idat_groundhogday_ultimate_linefeed_runtime(
        runtime,
        data,
        analysis,
        ultimate_parent_seeds,
        next_state_id=next_state_id,
        original_idat_count=original_idat_count,
    )
    if ultimate_result is not None:
        return ultimate_result, ultimate_seeds
    continuations.extend(ultimate_seeds)

    top = _rank_idat_seed_candidates(tuple(continuations), limit=max(seed_limit, IDAT_DEBUG_ARTIFACT_TOP_LIMIT))
    if not top:
        runtime.side_notes.append("-IDAT GroundHogDay linefeed route produced no stronger seed.")
        return None, ()

    best = next((candidate for candidate in top if _idat_candidate_is_complete_clone(candidate)), top[0])
    result = idat_bruteforce.IdatDeepBeamProbeResult(
        before=analysis,
        best=best,
        top_candidates=top,
        window_start=min(window_starts) if window_starts else 0,
        window_end=max(window_ends) if window_ends else 0,
        tested_candidates=tested,
        budget_exhausted=False,
        reached_depth=max((len(candidate.operations) for candidate in top), default=0),
        state_count=next_state_id,
        visited_count=len(top),
        strategy="groundhogday-linefeed-seed-repair",
        reason="seeds=%s; continuations=%s" % (len(seeds), len(top)),
    )
    runtime.side_notes.append(idat_bruteforce.deep_beam_summary_line(result))
    runtime.side_notes.extend(idat_bruteforce.deep_beam_candidate_summary_lines(result))
    _write_idat_deep_beam_debug_artifacts(
        runtime,
        result,
        label="idat_groundhogday_linefeed",
        include_dynamic_trace=True,
    )
    if any(_idat_candidate_is_complete_clone(candidate) for candidate in top):
        runtime.side_notes.append(
            "-IDAT GroundHogDay linefeed complete stream kept structural-only pending row-filter/filter-alignment cleanup and visual guard."
        )
        runtime.candy(
            "Cowsay",
            "Linefeed produced a structurally complete stream. I am not calling that a visual fix yet; GroundHogDay will run cleanup and the visual guard first.",
            "com",
        )
    return None, top


def _run_idat_filter_seed_stored_block_runtime(
    runtime: Any,
    data: bytes,
    analysis: idat.IdatStreamAnalysis,
    seed_candidates: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...] = (),
) -> tuple[tuple[bool, Any] | None, tuple[idat_bruteforce.IdatDeepBeamCandidate, ...]]:
    if _block_deep_beam_if_chunk_names_are_stale(runtime, data):
        return None, ()

    seed_limit = _runtime_seed_local_continuation_limit(runtime)
    seeds = _rank_idat_seed_candidates(seed_candidates, limit=seed_limit)
    if not seeds:
        seeds = _load_idat_artifact_seed_candidates(
            runtime,
            data,
            analysis,
            limit=seed_limit,
        )
    if not seeds:
        return None, ()

    runtime.side_notes.append(
        "-IDAT stored-block filter-seed route: probing %s PNG-filter-ranked seed(s) before %s."
        % (len(seeds), FINAL_INVESTIGATION_LABEL)
    )
    runtime.candy(
        "Cowsay",
        "I am combining the cleaner PNG-filter seed with the stored-block LEN/NLEN repair route.",
        "com",
    )
    stored_result = _run_idat_stored_block_runtime(
        runtime,
        data,
        analysis,
        seed_candidates=seeds,
        path_label="stored_block_filter_seed",
        seed_checkpoint_path="",
    )
    if stored_result is None:
        return None, ()
    if stored_result.best is not None:
        written = _write_stored_block_best_clone(runtime, analysis, stored_result)
        if written is not None:
            return written, stored_result.top_candidates
    if stored_result.top_candidates:
        runtime.side_notes.append(
            "-IDAT stored-block filter-seed route produced %s follow-up seed(s)."
            % len(stored_result.top_candidates)
        )
        return None, stored_result.top_candidates
    return None, ()


def _GroundHogDay_source_hash(data: bytes) -> str:
    try:
        _chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(data)
    except Exception:
        return hashlib.sha1(data).hexdigest()
    return idat_bruteforce._stream_state_key(stream)


def _GroundHogDay_resume_state_path(runtime: Any, *, create: bool) -> Path | None:
    payload_folder = _final_investigation_payload_folder(runtime, create=create)
    if payload_folder is None:
        return None
    stem = _final_investigation_stem(runtime, payload_folder)
    return payload_folder / ("%s_groundhogday.resume.json" % stem)


def _GroundHogDay_read_resume_state(runtime: Any) -> dict[str, Any]:
    path = _GroundHogDay_resume_state_path(runtime, create=False)
    if path is None or not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        runtime.side_notes.append("-IDAT GroundHogDay resume state ignored: %s." % exc)
        return {}
    if not isinstance(payload, dict):
        runtime.side_notes.append("-IDAT GroundHogDay resume state ignored: JSON payload is not an object.")
        return {}
    return payload


def _GroundHogDay_source_marker_matches(state: dict[str, Any], data: bytes) -> bool:
    return bool(
        state
        and state.get("route") == "GroundHogDay"
        and str(state.get("source_hash") or "") == _GroundHogDay_source_hash(data)
    )


def _GroundHogDay_day_index(value: Any, *, default: int = 1) -> int:
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return max(1, int(default))


def _GroundHogDay_debug_payload_day_evidence(runtime: Any) -> dict[str, int]:
    payload_folder = _final_investigation_payload_folder(runtime, create=False)
    if payload_folder is None:
        return {}
    stem = _final_investigation_stem(runtime, payload_folder)
    preview_folder = payload_folder / GROUNDHOGDAY_SCANLINE_PREVIEW_FOLDER

    def count(pattern: str) -> int:
        return len(tuple(payload_folder.glob(pattern)))

    def preview_count(pattern: str) -> int:
        if not preview_folder.is_dir():
            return 0
        return len(tuple(preview_folder.glob(pattern)))

    return {
        "preview_metadata": count("%s_groundhogday_preview_state*.json" % stem),
        "seed_artifacts": count("%s_groundhogday_seed_state*.png" % stem),
        "scanline_previews": count("%s_groundhogday_scanline_preview_state*.png" % stem)
        + preview_count("%s_groundhogday_scanline_preview_state*.png" % stem),
        "tolerant_previews": count("%s_groundhogday_tolerant_preview_state*.png" % stem)
        + preview_count("%s_groundhogday_tolerant_preview_state*.png" % stem),
        "linefeed_chain_artifacts": count("%s_groundhogday_state*_linefeed_chain_round*.png" % stem),
    }


def _GroundHogDay_inferred_next_day_from_debug_payloads(
    runtime: Any,
) -> tuple[int, str]:
    evidence = _GroundHogDay_debug_payload_day_evidence(runtime)
    if not evidence:
        return 1, ""
    best_label, best_count = max(evidence.items(), key=lambda item: item[1])
    if best_count <= 0:
        return 1, ""
    details = ", ".join("%s=%s" % item for item in sorted(evidence.items()))
    return best_count + 1, "%s; %s" % (best_label, details)


def _GroundHogDay_resume_next_day(
    runtime: Any,
    data: bytes,
    *,
    default: int = 1,
) -> int:
    state = _GroundHogDay_read_resume_state(runtime)
    inferred, inferred_details = _GroundHogDay_inferred_next_day_from_debug_payloads(runtime)
    if not _GroundHogDay_source_marker_matches(state, data):
        if inferred > 1:
            runtime.side_notes.append(
                "-IDAT GroundHogDay resume day inferred from Debug_Payloads despite missing/stale resume source marker: next_day=%s; %s."
                % (inferred, inferred_details)
            )
            return inferred
        return _GroundHogDay_day_index(default)
    if "next_day" in state:
        saved = _GroundHogDay_day_index(state.get("next_day"), default=default)
        if inferred > saved:
            runtime.side_notes.append(
                "-IDAT GroundHogDay resume day raised from saved next_day=%s to inferred next_day=%s from Debug_Payloads: %s."
                % (saved, inferred, inferred_details)
            )
            return inferred
        return saved

    if inferred > 1:
        runtime.side_notes.append(
            "-IDAT GroundHogDay resume day inferred from Debug_Payloads: next_day=%s; %s."
            % (inferred, inferred_details)
        )
        return inferred
    return _GroundHogDay_day_index(default)


def _GroundHogDay_analysis_progress_score(
    analysis: idat.IdatStreamAnalysis,
) -> tuple[int, int, int, int, int, int, int]:
    return (
        1 if getattr(analysis, "complete", False) else 0,
        int(getattr(analysis, "usable_scanlines", 0) or 0),
        int(getattr(analysis, "complete_scanlines", 0) or 0),
        int(getattr(analysis, "decompressed_size", 0) or 0),
        int(getattr(analysis, "error_offset", -1) or -1),
        int(getattr(analysis, "expected_size", 0) or 0),
        0,
    )


def _GroundHogDay_seed_resume_record(
    candidate: idat_bruteforce.IdatDeepBeamCandidate,
) -> dict[str, Any]:
    after = getattr(candidate, "after", None)
    stream = getattr(candidate, "stream", b"")
    return {
        "state_id": int(getattr(candidate, "state_id", 0) or 0),
        "stream_hash": idat_bruteforce._stream_state_key(stream) if stream else "",
        "operation_count": len(getattr(candidate, "operations", ()) or ()),
        "status": getattr(after, "status", "unknown"),
        "complete": bool(getattr(after, "complete", False)),
        "usable_scanlines": int(getattr(after, "usable_scanlines", 0) or 0),
        "complete_scanlines": int(getattr(after, "complete_scanlines", 0) or 0),
        "height": int(getattr(after, "height", 0) or 0),
        "decompressed_size": int(getattr(after, "decompressed_size", 0) or 0),
        "expected_size": int(getattr(after, "expected_size", 0) or 0),
        "error_offset": getattr(after, "error_offset", None),
    }


def _GroundHogDay_operation_record(operation: Any) -> dict[str, Any]:
    return {
        "kind": str(getattr(operation, "kind", "")),
        "stream_offset": int(getattr(operation, "stream_offset", 0) or 0),
        "old": bytes(getattr(operation, "old_bytes", b"") or b"").hex(),
        "new": bytes(getattr(operation, "new_bytes", b"") or b"").hex(),
    }


def _GroundHogDay_write_preview_artifacts(
    runtime: Any,
    local_seeds: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...],
) -> tuple[str, ...]:
    best = _GroundHogDay_idat_seed_best(local_seeds)
    if best is None:
        return ()
    payload_folder = _final_investigation_payload_folder(runtime, create=True)
    if payload_folder is None:
        runtime.side_notes.append("-IDAT GroundHogDay preview skipped: repair folder is unavailable.")
        return ()

    state_id = int(getattr(best, "state_id", 0) or 0)
    digest = hashlib.sha1(getattr(best, "data", b"")).hexdigest()[:8]
    stem = _final_investigation_stem(runtime, payload_folder)
    saved: list[str] = []
    preview_folder = payload_folder / GROUNDHOGDAY_SCANLINE_PREVIEW_FOLDER
    try:
        preview_folder.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        runtime.side_notes.append("-IDAT GroundHogDay scanline preview folder create failed: %s." % exc)

    seed_name = "%s_groundhogday_seed_state%s_%s.png" % (stem, state_id, digest)
    seed_path = payload_folder / seed_name
    try:
        seed_path.write_bytes(best.data)
        saved.append(seed_name)
    except OSError as exc:
        runtime.side_notes.append("-IDAT GroundHogDay seed artifact write failed: %s." % exc)

    preview = idat.rebuild_visual_idat_preview(best.data)
    preview_name = ""
    preview_relative = ""
    if preview is not None:
        preview_name = (
            "%s_groundhogday_scanline_preview_state%s_%s_%s_of_%s.png"
            % (
                stem,
                state_id,
                digest,
                preview.recovered_scanlines,
                preview.total_scanlines,
            )
        )
        preview_path = preview_folder / preview_name
        try:
            preview_path.write_bytes(preview.data)
            preview_relative = "%s/%s" % (
                GROUNDHOGDAY_SCANLINE_PREVIEW_FOLDER,
                preview_name,
            )
            saved.append(preview_relative)
        except OSError as exc:
            runtime.side_notes.append("-IDAT GroundHogDay scanline preview write failed: %s." % exc)
            preview_name = ""
            preview_relative = ""
    else:
        runtime.side_notes.append(
            "-IDAT GroundHogDay scanline preview skipped: best seed has no rebuildable usable scanlines."
        )

    tolerant_preview = idat.rebuild_tolerant_idat_preview(best.data)
    tolerant_preview_name = ""
    tolerant_preview_relative = ""
    if tolerant_preview is not None and (
        preview is None
        or int(tolerant_preview.recovered_scanlines) > int(preview.recovered_scanlines)
    ):
        tolerant_preview_name = (
            "%s_groundhogday_tolerant_preview_state%s_%s_%s_complete_of_%s.png"
            % (
                stem,
                state_id,
                digest,
                tolerant_preview.recovered_scanlines,
                tolerant_preview.total_scanlines,
            )
        )
        tolerant_preview_path = preview_folder / tolerant_preview_name
        try:
            tolerant_preview_path.write_bytes(tolerant_preview.data)
            tolerant_preview_relative = "%s/%s" % (
                GROUNDHOGDAY_SCANLINE_PREVIEW_FOLDER,
                tolerant_preview_name,
            )
            saved.append(tolerant_preview_relative)
        except OSError as exc:
            runtime.side_notes.append("-IDAT GroundHogDay tolerant preview write failed: %s." % exc)
            tolerant_preview_name = ""
            tolerant_preview_relative = ""

    metadata_name = "%s_groundhogday_preview_state%s_%s.json" % (stem, state_id, digest)
    metadata_path = payload_folder / metadata_name
    metadata = {
        "route": "GroundHogDay",
        "version": 1,
        "state_id": state_id,
        "seed_artifact": seed_name if seed_name in saved else "",
        "scanline_preview": preview_relative,
        "tolerant_preview": tolerant_preview_relative,
        "seed_count": len(local_seeds),
        "best": _GroundHogDay_seed_resume_record(best),
        "operations": [
            _GroundHogDay_operation_record(operation)
            for operation in tuple(getattr(best, "operations", ()) or ())[-16:]
        ],
    }
    try:
        metadata_path.write_text(json.dumps(metadata, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        saved.append(metadata_name)
    except OSError as exc:
        runtime.side_notes.append("-IDAT GroundHogDay preview metadata write failed: %s." % exc)

    if saved:
        runtime.side_notes.append(
            "-IDAT GroundHogDay preview artifacts: %s."
            % ", ".join("Debug_Payloads/%s" % name for name in saved)
        )
        runtime.candy(
            "Cowsay",
            "I saved the best GroundHogDay seed and scanline preview artifacts in Debug_Payloads/%s."
            % GROUNDHOGDAY_SCANLINE_PREVIEW_FOLDER,
            "com",
        )
    return tuple(saved)


def _GroundHogDay_write_resume_state(
    runtime: Any,
    data: bytes | None,
    local_seeds: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...],
    *,
    next_day: Any = None,
) -> None:
    if data is None or not local_seeds:
        return
    path = _GroundHogDay_resume_state_path(runtime, create=True)
    if path is None:
        return
    best = _GroundHogDay_idat_seed_best(local_seeds)
    if best is None:
        return
    next_day_value = (
        _GroundHogDay_day_index(next_day)
        if next_day is not None
        else _GroundHogDay_resume_next_day(runtime, data)
    )
    payload = {
        "route": "GroundHogDay",
        "version": 1,
        "updated_at": int(time.time()),
        "source_hash": _GroundHogDay_source_hash(data),
        "next_day": next_day_value,
        "seed_count": len(local_seeds),
        "best": _GroundHogDay_seed_resume_record(best),
    }
    try:
        path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    except OSError as exc:
        runtime.side_notes.append("-IDAT GroundHogDay resume state write failed: %s." % exc)
        return
    runtime.side_notes.append(
        "-IDAT GroundHogDay resume state saved: %s." % path.name
    )
    _GroundHogDay_write_preview_artifacts(runtime, local_seeds)


def _GroundHogDay_super_linefeed_to_seed(
    parent: idat_bruteforce.IdatDeepBeamCandidate,
    candidate: idat_bruteforce.SuperMegaLinefeedCandidate,
    *,
    before: idat.IdatStreamAnalysis,
    state_id: int,
    original_idat_count: int,
) -> idat_bruteforce.IdatDeepBeamCandidate | None:
    try:
        _chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(candidate.data)
    except png.PngFormatError:
        return None
    if not stream:
        return None
    operations = tuple(getattr(parent, "operations", ()) or ()) + tuple(
        idat_bruteforce.IdatDeepBeamOperation(
            "groundhogday-linefeed-%s" % operation.kind,
            int(operation.stream_offset),
            operation.old_bytes,
            operation.new_bytes,
        )
        for operation in candidate.operations
    )
    return idat_bruteforce.IdatDeepBeamCandidate(
        data=candidate.data,
        stream=stream,
        operations=operations,
        before=before,
        after=candidate.after,
        state_id=int(state_id),
        parent_id=getattr(parent, "state_id", None),
        source_offsets=tuple(getattr(parent, "source_offsets", ()) or ())
        + tuple(int(operation.stream_offset) for operation in candidate.operations),
        score=idat_bruteforce._deep_beam_score(
            candidate.after,
            stream,
            len(operations),
            data=candidate.data,
            original_idat_count=original_idat_count,
        ),
    )


def _GroundHogDay_linefeed_insert_to_seed(
    parent: idat_bruteforce.IdatDeepBeamCandidate,
    candidate: idat_bruteforce.IdatLinefeedInsertCandidate,
    *,
    before: idat.IdatStreamAnalysis,
    state_id: int,
    original_idat_count: int,
) -> idat_bruteforce.IdatDeepBeamCandidate | None:
    try:
        _chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(candidate.data)
    except png.PngFormatError:
        return None
    if not stream:
        return None
    inserted = int(candidate.inserted_byte) & 0xFF
    operations = tuple(getattr(parent, "operations", ()) or ()) + (
        idat_bruteforce.IdatDeepBeamOperation(
            "groundhogday-linefeed-insert-%02x" % inserted,
            int(candidate.stream_offset),
            b"",
            bytes((inserted,)),
        ),
    )
    return idat_bruteforce.IdatDeepBeamCandidate(
        data=candidate.data,
        stream=stream,
        operations=operations,
        before=before,
        after=candidate.after,
        state_id=int(state_id),
        parent_id=getattr(parent, "state_id", None),
        source_offsets=tuple(getattr(parent, "source_offsets", ()) or ())
        + (int(candidate.stream_offset),),
        score=idat_bruteforce._deep_beam_score(
            candidate.after,
            stream,
            len(operations),
            data=candidate.data,
            original_idat_count=original_idat_count,
        ),
    )


def _run_idat_groundhogday_ultimate_linefeed_runtime(
    runtime: Any,
    data: bytes,
    analysis: idat.IdatStreamAnalysis,
    seed_candidates: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...],
    *,
    next_state_id: int,
    original_idat_count: int,
) -> tuple[tuple[bool, Any] | None, tuple[idat_bruteforce.IdatDeepBeamCandidate, ...], int]:
    base_budget = _runtime_groundhogday_ultimate_linefeed_budget(runtime)
    budget = _GroundHogDay_ultimate_linefeed_auto_budget(runtime, seed_candidates, base_budget)
    if budget == 0:
        runtime.side_notes.append("-IDAT GroundHogDay UltimateLineFeed skipped: budget is disabled.")
        return None, (), next_state_id
    if (
        not _runtime_groundhogday_ultimate_linefeed_configured(runtime)
        and not str(getattr(runtime, "file_origin", "") or "").strip()
    ):
        runtime.side_notes.append(
            "-IDAT GroundHogDay UltimateLineFeed skipped: source file origin is unavailable and no UltimateLineFeed budget was configured."
        )
        return None, (), next_state_id

    seeds = _rank_idat_seed_candidates(
        seed_candidates,
        limit=_runtime_groundhogday_seed_pool_limit(runtime),
    )
    if not seeds:
        return None, (), next_state_id

    checkpoint_path, progress_path = _idat_groundhogday_ultimate_linefeed_paths(runtime)
    max_depth = _runtime_groundhogday_ultimate_linefeed_max_depth(runtime)
    max_offsets = _runtime_groundhogday_ultimate_linefeed_max_offsets(runtime)
    workers = _runtime_groundhogday_ultimate_linefeed_workers(runtime)
    resume_seeds = _GroundHogDay_ultimate_linefeed_resume_seeds(
        runtime,
        seeds,
        progress_path=progress_path,
        max_depth=max_depth,
        max_offsets=max_offsets,
    )
    if resume_seeds:
        seeds = resume_seeds
    runtime.side_notes.append(
        "-IDAT GroundHogDay UltimateLineFeed: seeds=%s; budget=%s; max_depth=%s; max_offsets=%s; workers=%s; checkpoint=%s."
        % (
            len(seeds),
            "unbounded" if budget is None else budget,
            max_depth,
            max_offsets,
            workers,
            checkpoint_path or "none",
        )
    )
    runtime.candy(
        "Cowsay",
        "GroundHogDay is pushing the linefeed hypothesis harder now: a checkpointed UltimateLineFeed pass gets a bounded budget before I call the loop stuck.",
        "com",
    )
    runtime.candy("Title", "IDAT %s" % IDAT_GROUNDHOGDAY_MINI_ULTIMATE_LINEFEED_LABEL)

    continuations: list[idat_bruteforce.IdatDeepBeamCandidate] = []
    for seed in seeds:
        try:
            result = idat_bruteforce.probe_ultimate_mega_super_linefeed_bruteforce(
                seed.data,
                start_offset=getattr(seed.after, "error_offset", None),
                checkpoint_path=checkpoint_path,
                progress_path=progress_path,
                max_depth=max_depth,
                max_offsets=max_offsets,
                budget=budget,
                beam_width=64,
                ultimate_workers=workers,
                progress=_runtime_groundhogday_ultimate_linefeed_progress(runtime),
            )
            result = replace(result, strategy=IDAT_GROUNDHOGDAY_MINI_ULTIMATE_LINEFEED_LABEL)
        except idat_bruteforce.UltimateLinefeedInterrupted as exc:
            runtime.side_notes.append(
                "-IDAT GroundHogDay UltimateLineFeed interrupted; progress saved: %s."
                % exc.progress_path
            )
            runtime.candy(
                "Cowsay",
                "UltimateLineFeed was interrupted; progress/checkpoint are saved, so I am stopping this pass instead of losing the cursor.",
                "bad",
            )
            raise SystemExit(130) from exc

        runtime.side_notes.append(idat_bruteforce.ultimate_linefeed_probe_summary_line(result))
        runtime.side_notes.append(idat_bruteforce.ultimate_linefeed_offsets_summary_line(result))
        if result.best is None:
            continue
        runtime.side_notes.append(idat_bruteforce.ultimate_linefeed_candidate_summary_line(result.best))

        seen_streams: set[str] = set()
        linefeed_candidates: list[idat_bruteforce.SuperMegaLinefeedCandidate] = []
        for candidate in (result.best, *tuple(result.top_candidates or ())):
            if candidate is None:
                continue
            try:
                _chunks, stream = idat_bruteforce._all_chunks_and_idat_stream(candidate.data)
            except png.PngFormatError:
                continue
            key = idat_bruteforce._stream_state_key(stream)
            if key in seen_streams:
                continue
            seen_streams.add(key)
            linefeed_candidates.append(candidate)

        for candidate in linefeed_candidates:
            continuation = _GroundHogDay_super_linefeed_to_seed(
                seed,
                candidate,
                before=analysis,
                state_id=next_state_id,
                original_idat_count=original_idat_count,
            )
            if continuation is None:
                continue
            continuations.append(continuation)
            next_state_id += 1
        if continuations and any(_idat_candidate_is_complete_clone(candidate) for candidate in continuations):
            break

    top = _rank_idat_seed_candidates(
        tuple(continuations),
        limit=max(_runtime_groundhogday_seed_pool_limit(runtime), IDAT_DEBUG_ARTIFACT_TOP_LIMIT),
    )
    if not top:
        runtime.side_notes.append("-IDAT GroundHogDay UltimateLineFeed produced no stronger seed.")
        return None, (), next_state_id

    best = next((candidate for candidate in top if _idat_candidate_is_complete_clone(candidate)), top[0])
    source_offsets = tuple(
        offset
        for candidate in top
        for offset in tuple(getattr(candidate, "source_offsets", ()) or ())
    )
    result = idat_bruteforce.IdatDeepBeamProbeResult(
        before=analysis,
        best=best,
        top_candidates=top,
        window_start=min(source_offsets) if source_offsets else 0,
        window_end=max(source_offsets) if source_offsets else 0,
        tested_candidates=0,
        budget_exhausted=False,
        reached_depth=max((len(candidate.operations) for candidate in top), default=0),
        state_count=next_state_id,
        visited_count=len(top),
        strategy="groundhogday-ultimate-linefeed",
        reason="seeds=%s; continuations=%s" % (len(seeds), len(top)),
    )
    runtime.side_notes.append(idat_bruteforce.deep_beam_summary_line(result))
    runtime.side_notes.extend(idat_bruteforce.deep_beam_candidate_summary_lines(result))
    _write_idat_deep_beam_debug_artifacts(
        runtime,
        result,
        label="idat_groundhogday_ultimate_linefeed",
        include_dynamic_trace=True,
    )
    if any(_idat_candidate_is_complete_clone(candidate) for candidate in top):
        runtime.side_notes.append(
            "-IDAT GroundHogDay %s complete stream kept structural-only pending row-filter/filter-alignment cleanup and visual guard."
            % IDAT_GROUNDHOGDAY_MINI_ULTIMATE_LINEFEED_LABEL
        )
        runtime.candy(
            "Cowsay",
            "%s produced a structurally complete stream. I am treating it as evidence, not proof."
            % IDAT_GROUNDHOGDAY_MINI_ULTIMATE_LINEFEED_LABEL,
            "com",
        )
    return None, top, next_state_id


def _GroundHogDay_cleanup_linefeed_seeds_runtime(
    runtime: Any,
    data: bytes,
    analysis: idat.IdatStreamAnalysis,
    linefeed_seeds: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...],
    title_counter: list[int],
) -> tuple[tuple[bool, Any] | None, tuple[idat_bruteforce.IdatDeepBeamCandidate, ...]]:
    cleanup_runtime = _RuntimeWithOverrides(
        runtime,
        suppress_complete_idat_clone_write=True,
    )
    seed_limit = _runtime_groundhogday_seed_pool_limit(runtime)
    cleanup_seeds = _rank_idat_seed_candidates(linefeed_seeds, limit=seed_limit)
    runtime.side_notes.append(
        "-IDAT GroundHogDay linefeed cleanup: starting from structural-only seed(s), best %s."
        % _GroundHogDay_idat_seed_progress_summary(cleanup_seeds)
    )

    row_result, row_seeds = _run_idat_row_filter_literal_repair_runtime(
        _GroundHogDay_next_title_runtime(
            cleanup_runtime,
            title_counter,
            seed_local_continuation_limit=seed_limit,
        ),
        data,
        analysis,
        cleanup_seeds,
    )
    if row_result is not None:
        return row_result, row_seeds
    if _GroundHogDay_idat_seed_candidates_make_progress(row_seeds, cleanup_seeds):
        _GroundHogDay_emit_scanline_recovery_update(
            runtime,
            cleanup_seeds,
            row_seeds,
            "linefeed row-filter cleanup",
        )
        cleanup_seeds = _rank_idat_seed_candidates(row_seeds, limit=seed_limit)

    filter_result, filter_seeds = _run_idat_filter_alignment_runtime(
        _GroundHogDay_next_title_runtime(
            cleanup_runtime,
            title_counter,
            seed_local_continuation_limit=seed_limit,
        ),
        data,
        analysis,
        cleanup_seeds,
    )
    if filter_result is not None:
        return filter_result, filter_seeds
    if _GroundHogDay_idat_seed_candidates_make_progress(filter_seeds, cleanup_seeds):
        _GroundHogDay_emit_scanline_recovery_update(
            runtime,
            cleanup_seeds,
            filter_seeds,
            "linefeed filter-alignment cleanup",
        )
        cleanup_seeds = _rank_idat_seed_candidates(filter_seeds, limit=seed_limit)

    return None, cleanup_seeds


def _GroundHogDay_guard_linefeed_progress_runtime(
    runtime: Any,
    data: bytes,
    analysis: idat.IdatStreamAnalysis,
    previous_seeds: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...],
    linefeed_seeds: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...],
    title_counter: list[int],
) -> tuple[tuple[bool, Any] | None, tuple[idat_bruteforce.IdatDeepBeamCandidate, ...]]:
    if not linefeed_seeds:
        return None, ()
    runtime.side_notes.append(
        "-IDAT GroundHogDay linefeed seeds marked structural-only until cleanup and visual guard pass."
    )
    cleanup_result, cleanup_seeds = _GroundHogDay_cleanup_linefeed_seeds_runtime(
        runtime,
        data,
        analysis,
        linefeed_seeds,
        title_counter,
    )
    if cleanup_result is not None:
        return cleanup_result, cleanup_seeds
    candidate_seeds = (
        cleanup_seeds
        if _GroundHogDay_idat_seed_candidates_make_progress(cleanup_seeds, linefeed_seeds)
        else linefeed_seeds
    )
    accepted = _GroundHogDay_visual_guard_candidates(
        runtime,
        previous_seeds,
        candidate_seeds,
        route_label="linefeed",
    )
    if accepted:
        return None, accepted
    _GroundHogDay_write_resume_state(runtime, data, candidate_seeds, next_day=title_counter[0])
    return None, ()


def _GroundHogDay_resume_seed_candidates(
    runtime: Any,
    data: bytes,
    analysis: idat.IdatStreamAnalysis,
) -> tuple[idat_bruteforce.IdatDeepBeamCandidate, ...]:
    if analysis.complete or not analysis.supported:
        return ()
    if analysis.status not in ("corrupt_deflate", "incomplete_stream", "bad_adler"):
        return ()
    if analysis.error_offset is None:
        return ()
    _chunks, problems, status = _chunk_name_audit(data)
    if status != "ok" or problems:
        return ()

    seed_limit = _runtime_groundhogday_seed_pool_limit(runtime)
    seeds = _load_idat_artifact_seed_candidates(
        runtime,
        data,
        analysis,
        limit=seed_limit,
    )
    seeds = _rank_idat_seed_candidates(seeds, limit=seed_limit)
    if not seeds:
        return ()

    best = _GroundHogDay_idat_seed_best(seeds)
    if best is None:
        return ()
    state = _GroundHogDay_read_resume_state(runtime)
    if _GroundHogDay_source_marker_matches(state, data):
        return seeds
    if _GroundHogDay_idat_seed_progress_score(best) > _GroundHogDay_analysis_progress_score(analysis):
        return seeds
    return ()


def _GroundHogDay_defer_final_investigation_after_local_progress(
    runtime: Any,
    local_seeds: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...],
    *,
    data: bytes | None = None,
) -> bool:
    if not local_seeds:
        return False
    best = local_seeds[0]
    after = getattr(best, "after", None)
    _GroundHogDay_write_resume_state(runtime, data, local_seeds)
    runtime.side_notes.append(
        "-IDAT %s deferred by GroundHogDay: produced %s follow-up seed(s); best status=%s; decompressed=%s; scanlines=%s/%s."
        % (
            FINAL_INVESTIGATION_LABEL,
            len(local_seeds),
            getattr(after, "status", "unknown"),
            getattr(after, "decompressed_size", "?"),
            getattr(after, "usable_scanlines", "?"),
            getattr(after, "height", "?"),
        )
    )
    runtime.side_notes.append(
        "-IDAT GroundHogDay stopped this pass unresolved on purpose: the file still has problems, but the pre-Final route is still producing stronger seeds."
    )
    runtime.candy(
        "Cowsay",
        "GroundHogDay is still making measurable IDAT progress, so I am not launching %s in this pass."
        % FINAL_INVESTIGATION_LABEL,
        "com",
    )
    runtime.candy(
        "Cowsay",
        "The new seeds are checkpointed as debug artifacts; rerun or raise IDAT_PREFINAL_REPAIR_CYCLES/IDAT_PREFINAL_REPAIR_BATCHES before using %s."
        % FINAL_INVESTIGATION_LABEL,
        "com",
    )
    _GroundHogDay_emit_unresolved_stop(
        runtime,
        reason="pre-Final repair routes are still producing stronger seeds, so %s is deferred"
        % FINAL_INVESTIGATION_LABEL,
        seeds=local_seeds,
    )
    return True


def _GroundHogDay_ultimate_linefeed_auto_budget(
    runtime: Any,
    seed_candidates: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...],
    base_budget: int | None,
) -> int | None:
    if base_budget is None or base_budget == 0:
        return base_budget
    if _runtime_groundhogday_ultimate_linefeed_budget_explicit(runtime):
        return base_budget
    _checkpoint_path, progress_path = _idat_groundhogday_ultimate_linefeed_paths(runtime)
    if not progress_path or not Path(progress_path).is_file():
        return base_budget
    max_depth = _runtime_groundhogday_ultimate_linefeed_max_depth(runtime)
    max_offsets = _runtime_groundhogday_ultimate_linefeed_max_offsets(runtime)
    boosted_budget = int(base_budget)
    first_warning = ""
    for seed in _rank_idat_seed_candidates(
        seed_candidates,
        limit=_runtime_groundhogday_seed_pool_limit(runtime),
    ):
        after = getattr(seed, "after", None)
        progress, warning = idat_bruteforce.load_ultimate_progress_for_source(
            seed.data,
            progress_path,
            start_offset=getattr(after, "error_offset", None),
            max_depth=max_depth,
            max_offsets=max_offsets,
        )
        if progress is None:
            if warning and not first_warning:
                first_warning = warning
            continue
        attempted = idat_bruteforce.ultimate_progress_attempted_floor(progress)
        saved_budget = int(progress.budget or base_budget)
        if attempted < max(int(base_budget), saved_budget):
            continue
        next_budget = min(
            IDAT_GROUNDHOGDAY_ULTIMATE_LINEFEED_AUTO_BUDGET_CAP,
            max(int(base_budget) * 2, saved_budget * 2, attempted * 2),
        )
        if next_budget > boosted_budget:
            boosted_budget = next_budget
    if first_warning:
        runtime.side_notes.append(
            "-IDAT GroundHogDay MiniUltimate budget probe ignored at least one seed: %s."
            % first_warning
        )
    if boosted_budget > int(base_budget):
        runtime.side_notes.append(
            "-IDAT GroundHogDay MiniUltimate auto-budget: previous checkpoint reached %s; next budget=%s."
            % (base_budget, boosted_budget)
        )
        runtime.candy(
            "Cowsay",
            "MiniUltimate hit its automatic budget, not a real dead end. I am raising that checkpointed budget to %s before handing off."
            % boosted_budget,
            "com",
        )
    return boosted_budget


def _GroundHogDay_ultimate_linefeed_route_open(
    runtime: Any,
    seed_candidates: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...],
) -> bool:
    _checkpoint_path, progress_path = _idat_groundhogday_ultimate_linefeed_paths(runtime)
    if not progress_path or not Path(progress_path).is_file():
        return False
    current_budget = _GroundHogDay_ultimate_linefeed_auto_budget(
        runtime,
        seed_candidates,
        _runtime_groundhogday_ultimate_linefeed_budget(runtime),
    )
    max_depth = _runtime_groundhogday_ultimate_linefeed_max_depth(runtime)
    max_offsets = _runtime_groundhogday_ultimate_linefeed_max_offsets(runtime)
    first_warning = ""
    for seed in _rank_idat_seed_candidates(
        seed_candidates,
        limit=_runtime_groundhogday_seed_pool_limit(runtime),
    ):
        after = getattr(seed, "after", None)
        progress, warning = idat_bruteforce.load_ultimate_progress_for_source(
            seed.data,
            progress_path,
            start_offset=getattr(after, "error_offset", None),
            max_depth=max_depth,
            max_offsets=max_offsets,
        )
        if progress is None:
            if warning and not first_warning:
                first_warning = warning
            continue
        attempted = idat_bruteforce.ultimate_progress_attempted_floor(progress)
        budget = current_budget if current_budget is not None else progress.budget
        if current_budget is None or budget is None or attempted < int(budget):
            runtime.side_notes.append(
                "-IDAT GroundHogDay MiniUltimate route still open: attempted=%s; budget=%s; progress=%s."
                % (attempted, "unbounded" if budget is None else budget, Path(progress_path).name)
            )
            return True
    if first_warning:
        runtime.side_notes.append(
            "-IDAT GroundHogDay MiniUltimate route progress ignored at least one seed: %s."
            % first_warning
        )
    return False


def _GroundHogDay_ultimate_linefeed_resume_seeds(
    runtime: Any,
    seeds: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...],
    *,
    progress_path: str,
    max_depth: int,
    max_offsets: int,
) -> tuple[idat_bruteforce.IdatDeepBeamCandidate, ...]:
    if not progress_path or not Path(progress_path).is_file():
        return ()
    matching: list[idat_bruteforce.IdatDeepBeamCandidate] = []
    first_warning = ""
    for seed in seeds:
        after = getattr(seed, "after", None)
        progress, warning = idat_bruteforce.load_ultimate_progress_for_source(
            seed.data,
            progress_path,
            start_offset=getattr(after, "error_offset", None),
            max_depth=max_depth,
            max_offsets=max_offsets,
        )
        if progress is not None:
            matching.append(seed)
        elif warning and not first_warning:
            first_warning = warning
    if matching:
        runtime.side_notes.append(
            "-IDAT GroundHogDay MiniUltimate resume priority: %s seed(s) match %s; probing them before other seeds to preserve the checkpoint cursor."
            % (len(matching), Path(progress_path).name)
        )
        return tuple(matching)
    if first_warning:
        runtime.side_notes.append(
            "-IDAT GroundHogDay MiniUltimate resume priority found no matching seed: %s."
            % first_warning
        )
    return ()


def _GroundHogDay_stored_block_route_open(runtime: Any, data: bytes) -> bool:
    _checkpoint_path, progress_path = _idat_frontier_paths(runtime, "stored_block_filter_seed")
    if not progress_path or not Path(progress_path).is_file():
        return False
    progress_state = idat_bruteforce.stored_block_progress_state(data, progress_path)
    if not (progress_state.available and progress_state.source_matches):
        return False
    budget = _runtime_stored_block_budget(runtime)
    if progress_state.exhausted and progress_state.budget >= budget:
        return False
    runtime.side_notes.append(
        "-IDAT GroundHogDay stored-block route still open: tested=%s; budget=%s; exhausted=%s."
        % (
            progress_state.tested,
            progress_state.budget,
            "yes" if progress_state.exhausted else "no",
        )
    )
    return True


def _GroundHogDay_open_route_reasons(
    runtime: Any,
    data: bytes,
    seed_candidates: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...],
) -> tuple[str, ...]:
    reasons: list[str] = []
    if _GroundHogDay_ultimate_linefeed_route_open(runtime, seed_candidates):
        reasons.append("MiniUltimate linefeed checkpoint")
    if _GroundHogDay_stored_block_route_open(runtime, data):
        reasons.append("stored-block filter-seed checkpoint")
    return tuple(reasons)


class _GroundHogDayTitleRuntime:
    def __init__(
        self,
        runtime: Any,
        title_counter: list[int],
        overrides: dict[str, Any] | None = None,
    ) -> None:
        self._runtime = runtime
        self._title_counter = title_counter
        self._overrides = dict(overrides or {})

    def __getattr__(self, name: str) -> Any:
        if name in self._overrides:
            return self._overrides[name]
        return getattr(self._runtime, name)

    def candy(self, *args: Any, **kwargs: Any) -> Any:
        if len(args) >= 2 and args[0] == "Title":
            _GroundHogDay_emit_day_quote(self._runtime, self._title_counter)
            title = _GroundHogDay_numbered_title(self._title_counter, args[1])
            return self._runtime.candy(args[0], title, *args[2:], **kwargs)
        if str(kwargs.get("Type") or kwargs.get("type") or "") == "Title":
            key = "Text" if "Text" in kwargs else "text" if "text" in kwargs else ""
            if key:
                _GroundHogDay_emit_day_quote(self._runtime, self._title_counter)
                kwargs = dict(kwargs)
                kwargs[key] = _GroundHogDay_numbered_title(self._title_counter, kwargs[key])
        return self._runtime.candy(*args, **kwargs)


def _GroundHogDay_emit_quote_before_title(runtime: Any) -> None:
    if isinstance(runtime, _GroundHogDayTitleRuntime):
        _GroundHogDay_emit_day_quote(runtime._runtime, runtime._title_counter)


def _GroundHogDay_numbered_title(title_counter: list[int], title: Any) -> str:
    title_text = str(title)
    if title_text.startswith("GroundHogDay "):
        return title_text
    title_index = int(title_counter[0])
    return "GroundHogDay %s: %s" % (title_index, title_text)


def _GroundHogDay_advance_day(title_counter: list[int]) -> None:
    title_counter[0] = int(title_counter[0]) + 1


def _GroundHogDay_emitted_quote_days(title_counter: list[Any]) -> set[int]:
    if len(title_counter) < 2 or not isinstance(title_counter[1], set):
        title_counter.append(set())
    return title_counter[1]


def _GroundHogDay_quote_for_day(_runtime: Any, day_index: int) -> tuple[int, str, str]:
    entries = GROUNDHOGDAY_QUOTES
    quote_index = ((max(1, int(day_index)) - 1) % len(entries)) + 1
    mood, text = entries[quote_index - 1]
    try:
        text = text.format(day=day_index, quote=quote_index)
    except Exception:
        pass
    return quote_index, mood, text


def _GroundHogDay_emit_day_quote(runtime: Any, title_counter: list[Any]) -> None:
    day_index = int(title_counter[0])
    emitted_days = _GroundHogDay_emitted_quote_days(title_counter)
    if day_index in emitted_days:
        return
    emitted_days.add(day_index)
    _quote_index, mood, text = _GroundHogDay_quote_for_day(runtime, day_index)
    runtime.candy(
        "Cowsay",
        "GroundHog Day part %s:\n\n%s" % (day_index, text),
        mood,
    )


def _GroundHogDay_next_title_runtime(
    runtime: Any,
    title_counter: list[int],
    **overrides: Any,
) -> Any:
    return _GroundHogDayTitleRuntime(runtime, title_counter, overrides)


def _GroundHogDay_emit_unresolved_stop(
    runtime: Any,
    *,
    reason: str,
    seeds: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...] = (),
) -> None:
    if seeds:
        _GroundHogDay_write_preview_artifacts(runtime, seeds)
    summary = _GroundHogDay_idat_seed_progress_summary(seeds)
    note = "-IDAT GroundHogDay unresolved stop: %s" % reason
    if seeds:
        note += "; best %s" % summary
    runtime.side_notes.append(note + ".")
    runtime.candy(
        "Cowsay",
        "I know this PNG still has problems. I am stopping this pass cleanly, not pretending it is fixed.",
        "bad",
    )
    runtime.candy(
        "Cowsay",
        "%s stays a last-resort route. The saved GroundHogDay seeds are the next resume point."
        % FINAL_INVESTIGATION_LABEL,
        "com",
    )


def _GroundHogDay_idat_seed_best(
    seed_candidates: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...],
) -> idat_bruteforce.IdatDeepBeamCandidate | None:
    ranked = _rank_idat_seed_candidates(seed_candidates, limit=1)
    return ranked[0] if ranked else None


def _GroundHogDay_idat_seed_progress_score(
    candidate: idat_bruteforce.IdatDeepBeamCandidate | None,
) -> tuple[int, int, int, int, int, int, int]:
    if candidate is None:
        return (-1, -1, -1, -1, -1, -1, 0)
    after = getattr(candidate, "after", None)
    if after is None:
        return (-1, -1, -1, -1, -1, -1, -len(getattr(candidate, "operations", ())))
    return (
        1 if getattr(after, "complete", False) else 0,
        int(getattr(after, "usable_scanlines", 0) or 0),
        int(getattr(after, "complete_scanlines", 0) or 0),
        int(getattr(after, "decompressed_size", 0) or 0),
        int(getattr(after, "error_offset", -1) or -1),
        int(getattr(after, "expected_size", 0) or 0),
        -len(getattr(candidate, "operations", ())),
    )


def _GroundHogDay_idat_seed_progress_summary(
    seed_candidates: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...],
) -> str:
    best = _GroundHogDay_idat_seed_best(seed_candidates)
    after = getattr(best, "after", None)
    if best is None or after is None:
        return "none"
    return "status=%s; usable=%s/%s; complete=%s/%s; decompressed=%s; error_offset=%s" % (
        getattr(after, "status", "unknown"),
        getattr(after, "usable_scanlines", "?"),
        getattr(after, "height", "?"),
        getattr(after, "complete_scanlines", "?"),
        getattr(after, "height", "?"),
        getattr(after, "decompressed_size", "?"),
        getattr(after, "error_offset", "?"),
    )


def _GroundHogDay_idat_seed_candidates_make_progress(
    new_seeds: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...],
    old_seeds: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...],
) -> bool:
    new_best = _GroundHogDay_idat_seed_best(new_seeds)
    if new_best is None:
        return False
    old_best = _GroundHogDay_idat_seed_best(old_seeds)
    if old_best is None:
        return True
    new_score = _GroundHogDay_idat_seed_progress_score(new_best)
    old_score = _GroundHogDay_idat_seed_progress_score(old_best)
    if new_score > old_score:
        return True
    return new_score == old_score and new_best.data != old_best.data


def _GroundHogDay_seed_scanline_counts(
    seed_candidates: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...],
) -> tuple[int, int, int]:
    best = _GroundHogDay_idat_seed_best(seed_candidates)
    after = getattr(best, "after", None)
    if after is None:
        return 0, 0, 0
    return (
        int(getattr(after, "usable_scanlines", 0) or 0),
        int(getattr(after, "complete_scanlines", 0) or 0),
        int(getattr(after, "height", 0) or 0),
    )


def _GroundHogDay_emit_scanline_recovery_update(
    runtime: Any,
    old_seeds: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...],
    new_seeds: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...],
    route_label: str,
) -> None:
    old_usable, old_complete, old_height = _GroundHogDay_seed_scanline_counts(old_seeds)
    new_usable, new_complete, new_height = _GroundHogDay_seed_scanline_counts(new_seeds)
    if new_usable <= old_usable and new_complete <= old_complete:
        return
    height = max(old_height, new_height)
    runtime.side_notes.append(
        "-IDAT GroundHogDay scanline gain via %s: usable %s->%s/%s; complete %s->%s/%s."
        % (
            route_label,
            old_usable,
            new_usable,
            height,
            old_complete,
            new_complete,
            height,
        )
    )
    runtime.candy(
        "Cowsay",
        (
            "GroundHogDay %s recovered more scanlines: usable %s/%s "
            "(was %s/%s), complete rows %s/%s (was %s/%s)."
        )
        % (
            route_label,
            new_usable,
            height,
            old_usable,
            height,
            new_complete,
            height,
            old_complete,
            height,
        ),
        "good",
    )


def _GroundHogDay_seed_has_unusable_complete_rows(
    seed_candidates: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...],
) -> bool:
    best = _GroundHogDay_idat_seed_best(seed_candidates)
    after = getattr(best, "after", None)
    if after is None:
        return False
    return int(getattr(after, "complete_scanlines", 0) or 0) > int(
        getattr(after, "usable_scanlines", 0) or 0
    )


def _GroundHogDay_run_idat_prefinal_alternating_repair_runtime(
    runtime: Any,
    data: bytes,
    analysis: idat.IdatStreamAnalysis,
    seed_candidates: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...] = (),
    title_counter: list[int] | None = None,
) -> tuple[tuple[bool, Any] | None, tuple[idat_bruteforce.IdatDeepBeamCandidate, ...]]:
    if title_counter is None:
        title_counter = [1]
    seed_limit = _runtime_groundhogday_seed_pool_limit(runtime)
    cycles = _GroundHogDay_runtime_repair_cycles(runtime)
    seeds = _rank_idat_seed_candidates(seed_candidates, limit=seed_limit)
    if not seeds:
        seeds = _load_idat_artifact_seed_candidates(
            runtime,
            data,
            analysis,
            limit=seed_limit,
        )
    if not seeds:
        seeds = _load_final_investigation_seed_candidates(
            runtime,
            data,
            analysis,
            seed_candidates=(),
        )
    seeds = _rank_idat_seed_candidates(seeds, limit=seed_limit)
    if not seeds:
        return None, ()

    runtime.side_notes.append(
        "-IDAT GroundHogDay: starting with %s seed(s), cycles=%s, best %s."
        % (len(seeds), cycles, _GroundHogDay_idat_seed_progress_summary(seeds))
    )
    runtime.candy(
        "Cowsay",
        "GroundHogDay starts before %s. I am not looping blindly: each lap must produce a stronger IDAT seed, or I stop."
        % FINAL_INVESTIGATION_LABEL,
        "com",
    )
    runtime.candy(
        "Cowsay",
        "One lap tries one local deflate continuation step first. If that keeps moving, I checkpoint and keep pushing it; row-filter repair gets a turn only after local progress stalls.",
        "com",
    )

    progressed_seeds: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...] = ()
    for cycle_index in range(cycles):
        cycle_changed = False

        local_result, local_seeds = _run_idat_seed_local_continuation_runtime(
            _GroundHogDay_next_title_runtime(
                runtime,
                title_counter,
                seed_local_continuation_rounds=1,
                seed_local_continuation_limit=seed_limit,
            ),
            data,
            analysis,
            seeds,
        )
        if local_result is not None:
            return local_result, local_seeds
        if _GroundHogDay_idat_seed_candidates_make_progress(local_seeds, seeds):
            new_seeds = _rank_idat_seed_candidates(local_seeds, limit=seed_limit)
            _GroundHogDay_emit_scanline_recovery_update(runtime, seeds, new_seeds, "local deflate")
            seeds = new_seeds
            progressed_seeds = seeds
            cycle_changed = True
            _GroundHogDay_write_resume_state(runtime, data, seeds, next_day=title_counter[0])
            runtime.side_notes.append(
                "-IDAT GroundHogDay cycle %s/%s accepted local seed: %s."
                % (cycle_index + 1, cycles, _GroundHogDay_idat_seed_progress_summary(seeds))
            )
            if _GroundHogDay_seed_has_unusable_complete_rows(seeds):
                runtime.side_notes.append(
                    "-IDAT GroundHogDay cycle %s/%s postponed row-filter repair: local deflate is still producing stronger complete-row seeds."
                    % (cycle_index + 1, cycles)
                )
                runtime.candy(
                    "Cowsay",
                    "GroundHogDay has new complete rows, but their PNG filters are still dirty. Since local deflate is still moving, I am pushing that linefeed-shaped trail before spending time on row-filter cleanup.",
                    "com",
                )
            _GroundHogDay_advance_day(title_counter)
            continue

        row_result, row_seeds = _run_idat_row_filter_literal_repair_runtime(
            _GroundHogDay_next_title_runtime(
                runtime,
                title_counter,
                seed_local_continuation_limit=seed_limit,
            ),
            data,
            analysis,
            seeds,
        )
        if row_result is not None:
            return row_result, row_seeds
        if _GroundHogDay_idat_seed_candidates_make_progress(row_seeds, seeds):
            new_seeds = _rank_idat_seed_candidates(row_seeds, limit=seed_limit)
            _GroundHogDay_emit_scanline_recovery_update(runtime, seeds, new_seeds, "row-filter repair")
            seeds = new_seeds
            progressed_seeds = seeds
            cycle_changed = True
            _GroundHogDay_write_resume_state(runtime, data, seeds, next_day=title_counter[0])
            runtime.side_notes.append(
                "-IDAT GroundHogDay cycle %s/%s accepted row-filter seed: %s."
                % (cycle_index + 1, cycles, _GroundHogDay_idat_seed_progress_summary(seeds))
            )

            local_after_row_result, local_after_row_seeds = _run_idat_seed_local_continuation_runtime(
                _GroundHogDay_next_title_runtime(
                    runtime,
                    title_counter,
                    seed_local_continuation_rounds=1,
                    seed_local_continuation_limit=seed_limit,
                ),
                data,
                analysis,
                seeds,
            )
            if local_after_row_result is not None:
                return local_after_row_result, local_after_row_seeds
            if _GroundHogDay_idat_seed_candidates_make_progress(local_after_row_seeds, seeds):
                new_seeds = _rank_idat_seed_candidates(local_after_row_seeds, limit=seed_limit)
                _GroundHogDay_emit_scanline_recovery_update(runtime, seeds, new_seeds, "local-after-row deflate")
                seeds = new_seeds
                progressed_seeds = seeds
                _GroundHogDay_write_resume_state(runtime, data, seeds, next_day=title_counter[0])
                runtime.side_notes.append(
                    "-IDAT GroundHogDay cycle %s/%s accepted local-after-row seed: %s."
                    % (cycle_index + 1, cycles, _GroundHogDay_idat_seed_progress_summary(seeds))
                )

        _GroundHogDay_advance_day(title_counter)
        if not cycle_changed:
            runtime.side_notes.append(
                "-IDAT GroundHogDay stopped at cycle %s/%s: no stronger row/local seed."
                % (cycle_index + 1, cycles)
            )
            runtime.candy(
                "Cowsay",
                "GroundHogDay stopped because this lap did not improve the best seed. That is the guard against spinning in place.",
                "com",
            )
            break

    if progressed_seeds:
        runtime.side_notes.append(
            "-IDAT GroundHogDay produced follow-up seed(s); best %s."
            % _GroundHogDay_idat_seed_progress_summary(progressed_seeds)
        )
        runtime.candy(
            "Cowsay",
            "GroundHogDay made measurable IDAT progress, so %s stays parked for this pass."
            % FINAL_INVESTIGATION_LABEL,
            "com",
        )
    else:
        runtime.side_notes.append("-IDAT GroundHogDay produced no stronger seed.")
    return None, progressed_seeds


def _GroundHogDay_run_idat_prefinal_seed_routes_runtime(
    runtime: Any,
    data: bytes,
    analysis: idat.IdatStreamAnalysis,
    seed_candidates: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...] = (),
) -> tuple[
    tuple[bool, Any] | None,
    tuple[idat_bruteforce.IdatDeepBeamCandidate, ...],
    bool,
    ]:
    seeds = _merge_idat_seed_candidates(seed_candidates)
    progressed_seeds: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...] = ()
    title_counter = [_GroundHogDay_resume_next_day(runtime, data)]
    configured_batches = _GroundHogDay_runtime_repair_batches(runtime)
    seed_pool_limit = _runtime_groundhogday_seed_pool_limit(runtime)
    stopped_on_plateau = False
    structural_only_progress = False
    open_route_plateaus = 0
    open_route_reasons_at_stop: tuple[str, ...] = ()
    runtime.side_notes.append(
        "-IDAT GroundHogDay pre-Final campaign: checkpoint interval=%s batch(es); each batch has up to %s cycle(s)."
        % (configured_batches, _GroundHogDay_runtime_repair_cycles(runtime))
    )
    runtime.candy(
        "Cowsay",
        "GroundHogDay will not stop just because a cycle batch is spent. If the best seed improves, I checkpoint it and keep going.",
        "com",
    )
    _GroundHogDay_visual_guard_profile(runtime)

    batch_index = 0
    while True:
        batch_index += 1
        batch_label = str(batch_index)
        if batch_index > 1:
            runtime.side_notes.append(
                "-IDAT GroundHogDay batch %s continuing from best %s."
                % (batch_label, _GroundHogDay_idat_seed_progress_summary(seeds))
            )
            runtime.candy(
                "Cowsay",
                "GroundHogDay is still finding stronger seeds. I am continuing batch %s before %s."
                % (batch_label, FINAL_INVESTIGATION_LABEL),
                "com",
            )

        batch_progressed: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...] = ()
        alternating_result, alternating_seeds = _GroundHogDay_run_idat_prefinal_alternating_repair_runtime(
            runtime,
            data,
            analysis,
            seeds,
            title_counter,
        )
        if alternating_result is not None:
            return alternating_result, alternating_seeds, False
        if _GroundHogDay_idat_seed_candidates_make_progress(alternating_seeds, seeds):
            seeds = alternating_seeds
            progressed_seeds = alternating_seeds
            batch_progressed = alternating_seeds
            open_route_plateaus = 0
            _GroundHogDay_write_resume_state(runtime, data, seeds, next_day=title_counter[0])

        filter_result, filter_seeds = _run_idat_filter_alignment_runtime(
            _GroundHogDay_next_title_runtime(
                runtime,
                title_counter,
                seed_local_continuation_limit=seed_pool_limit,
            ),
            data,
            analysis,
            seeds,
        )
        if filter_result is not None:
            return filter_result, filter_seeds, False
        if _GroundHogDay_idat_seed_candidates_make_progress(filter_seeds, seeds):
            _GroundHogDay_emit_scanline_recovery_update(runtime, seeds, filter_seeds, "filter alignment")
            seeds = filter_seeds
            progressed_seeds = filter_seeds
            batch_progressed = filter_seeds
            open_route_plateaus = 0
            _GroundHogDay_write_resume_state(runtime, data, seeds, next_day=title_counter[0])

            row_filter_after_filter_result, row_filter_after_filter_seeds = _run_idat_row_filter_literal_repair_runtime(
                _GroundHogDay_next_title_runtime(
                    runtime,
                    title_counter,
                    seed_local_continuation_limit=seed_pool_limit,
                ),
                data,
                analysis,
                filter_seeds,
            )
            if row_filter_after_filter_result is not None:
                return row_filter_after_filter_result, row_filter_after_filter_seeds, False
            if _GroundHogDay_idat_seed_candidates_make_progress(
                row_filter_after_filter_seeds,
                seeds,
            ):
                _GroundHogDay_emit_scanline_recovery_update(
                    runtime,
                    seeds,
                    row_filter_after_filter_seeds,
                    "row-filter-after-alignment repair",
                )
                seeds = row_filter_after_filter_seeds
                progressed_seeds = row_filter_after_filter_seeds
                batch_progressed = row_filter_after_filter_seeds
                open_route_plateaus = 0
                _GroundHogDay_write_resume_state(runtime, data, seeds, next_day=title_counter[0])

        linefeed_result, linefeed_seeds = _run_idat_groundhogday_linefeed_runtime(
            _GroundHogDay_next_title_runtime(
                runtime,
                title_counter,
                seed_local_continuation_limit=seed_pool_limit,
            ),
            data,
            analysis,
            seeds,
        )
        if linefeed_result is not None:
            return linefeed_result, linefeed_seeds, False
        if _GroundHogDay_idat_seed_candidates_make_progress(linefeed_seeds, seeds):
            _GroundHogDay_emit_scanline_recovery_update(runtime, seeds, linefeed_seeds, "linefeed repair")
            guarded_result, guarded_seeds = _GroundHogDay_guard_linefeed_progress_runtime(
                runtime,
                data,
                analysis,
                seeds,
                linefeed_seeds,
                title_counter,
            )
            if guarded_result is not None:
                return guarded_result, guarded_seeds, False
            if not guarded_seeds:
                structural_only_progress = True
                runtime.side_notes.append(
                    "-IDAT GroundHogDay kept previous seed after linefeed structural-only branch failed visual guard."
                )
            else:
                seeds = guarded_seeds
                progressed_seeds = guarded_seeds
                batch_progressed = guarded_seeds
                open_route_plateaus = 0
                _GroundHogDay_write_resume_state(runtime, data, seeds, next_day=title_counter[0])

                if _GroundHogDay_seed_has_unusable_complete_rows(seeds):
                    runtime.side_notes.append(
                        "-IDAT GroundHogDay postponed row-filter-after-linefeed repair: linefeed route is still producing stronger complete-row seeds."
                    )
                    runtime.candy(
                        "Cowsay",
                        "Linefeed just moved the IDAT stream again. I am checkpointing it and continuing the linefeed trail before row-filter cleanup.",
                        "com",
                    )

        stored_result, stored_seeds = _run_idat_filter_seed_stored_block_runtime(
            _GroundHogDay_next_title_runtime(
                runtime,
                title_counter,
                seed_local_continuation_limit=seed_pool_limit,
            ),
            data,
            analysis,
            seeds,
        )
        if stored_result is not None:
            return stored_result, stored_seeds, False
        if _GroundHogDay_idat_seed_candidates_make_progress(stored_seeds, seeds):
            _GroundHogDay_emit_scanline_recovery_update(runtime, seeds, stored_seeds, "stored-block repair")
            seeds = stored_seeds
            progressed_seeds = stored_seeds
            batch_progressed = stored_seeds
            open_route_plateaus = 0
            _GroundHogDay_write_resume_state(runtime, data, seeds, next_day=title_counter[0])

            row_filter_after_stored_result, row_filter_after_stored_seeds = _run_idat_row_filter_literal_repair_runtime(
                _GroundHogDay_next_title_runtime(
                    runtime,
                    title_counter,
                    seed_local_continuation_limit=seed_pool_limit,
                ),
                data,
                analysis,
                stored_seeds,
            )
            if row_filter_after_stored_result is not None:
                return row_filter_after_stored_result, row_filter_after_stored_seeds, False
            if _GroundHogDay_idat_seed_candidates_make_progress(
                row_filter_after_stored_seeds,
                seeds,
            ):
                _GroundHogDay_emit_scanline_recovery_update(
                    runtime,
                    seeds,
                    row_filter_after_stored_seeds,
                    "row-filter-after-stored repair",
                )
                seeds = row_filter_after_stored_seeds
                progressed_seeds = row_filter_after_stored_seeds
                batch_progressed = row_filter_after_stored_seeds
                open_route_plateaus = 0
                _GroundHogDay_write_resume_state(runtime, data, seeds, next_day=title_counter[0])

        if not batch_progressed:
            open_reasons = _GroundHogDay_open_route_reasons(runtime, data, seeds)
            if open_reasons:
                open_route_plateaus += 1
                open_route_reasons_at_stop = open_reasons
                runtime.side_notes.append(
                    "-IDAT GroundHogDay batch %s found no stronger seed, but route(s) remain open: %s."
                    % (batch_label, ", ".join(open_reasons))
                )
                if open_route_plateaus <= max(1, configured_batches):
                    _GroundHogDay_write_resume_state(runtime, data, seeds, next_day=title_counter[0])
                    runtime.candy(
                        "Cowsay",
                        "GroundHogDay did not improve this lap, but %s still has checkpointed work. I am continuing instead of handing off."
                        % ", ".join(open_reasons),
                        "com",
                    )
                    _GroundHogDay_advance_day(title_counter)
                    continue
            stopped_on_plateau = True
            runtime.side_notes.append(
                "-IDAT GroundHogDay pre-Final campaign stopped after batch %s: no stronger seed."
                % batch_label
            )
            if seeds:
                _GroundHogDay_write_resume_state(runtime, data, seeds, next_day=title_counter[0])
                runtime.side_notes.append(
                    "-IDAT GroundHogDay plateau checkpoint saved: best %s."
                    % _GroundHogDay_idat_seed_progress_summary(seeds)
                )
            _GroundHogDay_advance_day(title_counter)
            break
        _GroundHogDay_write_resume_state(runtime, data, batch_progressed, next_day=title_counter[0])
        if batch_index % max(1, configured_batches) == 0:
            runtime.side_notes.append(
                "-IDAT GroundHogDay checkpoint interval reached after batch %s; progress still moving, continuing instead of stopping."
                % batch_label
            )
            runtime.candy(
                "Cowsay",
                "GroundHogDay reached checkpoint batch %s with a stronger seed. I saved preview/resume artifacts and I am continuing."
                % batch_label,
                "com",
            )
        _GroundHogDay_advance_day(title_counter)
        if batch_progressed:
            _GroundHogDay_write_resume_state(runtime, data, batch_progressed, next_day=title_counter[0])

    if stopped_on_plateau:
        if open_route_reasons_at_stop:
            runtime.side_notes.append(
                "-IDAT GroundHogDay paused with open route(s): %s; %s is deferred."
                % (", ".join(open_route_reasons_at_stop), FINAL_INVESTIGATION_LABEL)
            )
            runtime.candy(
                "Cowsay",
                "GroundHogDay still has open route work (%s). I am leaving the checkpoint active instead of launching %s."
                % (", ".join(open_route_reasons_at_stop), FINAL_INVESTIGATION_LABEL),
                "com",
            )
            _GroundHogDay_emit_unresolved_stop(
                runtime,
                reason="GroundHogDay route still open: %s" % ", ".join(open_route_reasons_at_stop),
                seeds=seeds,
            )
            return None, seeds, True
        if structural_only_progress:
            runtime.side_notes.append(
                "-IDAT GroundHogDay stopped with structural-only linefeed evidence; %s is not launched automatically from this plateau."
                % FINAL_INVESTIGATION_LABEL
            )
            runtime.candy(
                "Cowsay",
                "GroundHogDay found linefeed structure, but the visual guard did not accept it. I am stopping with the checkpoint instead of jumping straight to %s."
                % FINAL_INVESTIGATION_LABEL,
                "com",
            )
            return None, seeds, True
        if progressed_seeds:
            _GroundHogDay_write_resume_state(runtime, data, progressed_seeds, next_day=title_counter[0])
            runtime.side_notes.append(
                "-IDAT GroundHogDay reached a true plateau after earlier progress; no open GroundHogDay route remains, so %s may take the last-resort handoff."
                % FINAL_INVESTIGATION_LABEL
            )
            runtime.candy(
                "Cowsay",
                "GroundHogDay reached a true plateau after real progress. The best seeds are saved; %s can take the last-resort handoff now."
                % FINAL_INVESTIGATION_LABEL,
                "com",
            )
        return None, seeds, False

    return None, seeds, False


def _run_idat_post_deep_frontier_routes_runtime(
    runtime: Any,
    data: bytes,
    analysis: idat.IdatStreamAnalysis,
    seed_candidates: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...],
) -> tuple[bool, Any] | None:
    seeds = _merge_idat_seed_candidates(seed_candidates)
    if not seeds:
        return None

    runtime.side_notes.append(
        "-IDAT post-deep frontier seeded with %s deep-beam candidate(s)." % len(seeds)
    )
    runtime.candy(
        "Cowsay",
        "The deep beam left checkpointed seeds, so I am trying the bounded post-deep repair routes before calling the IDAT route exhausted.",
        "com",
    )

    backref_result = _run_idat_kraft_backref_runtime(
        runtime,
        data,
        analysis,
        seed_candidates=seeds,
        path_label="kraft_backref_deep",
        seed_checkpoint_path="",
    )
    if backref_result is not None:
        if backref_result.best is not None:
            written = _write_kraft_backref_best_clone(runtime, analysis, backref_result)
            if written is not None:
                return written
        if backref_result.top_candidates:
            seeds = backref_result.top_candidates

    stored_result = _run_idat_stored_block_runtime(
        runtime,
        data,
        analysis,
        seed_candidates=seeds,
        path_label="stored_block_deep",
        seed_checkpoint_path="",
    )
    if stored_result is not None:
        if stored_result.best is not None:
            written = _write_stored_block_best_clone(runtime, analysis, stored_result)
            if written is not None:
                return written
        if stored_result.top_candidates:
            seeds = stored_result.top_candidates

    backref_second_result = _run_idat_kraft_backref_runtime(
        runtime,
        data,
        analysis,
        seed_candidates=seeds,
        path_label="kraft_backref_deep2",
        seed_checkpoint_path="",
    )
    if backref_second_result is not None:
        if backref_second_result.best is not None:
            written = _write_kraft_backref_best_clone(runtime, analysis, backref_second_result)
            if written is not None:
                return written
        if backref_second_result.top_candidates:
            seeds = backref_second_result.top_candidates

    if not _idat_seed_candidates_have_frontier_progress(analysis, seeds):
        runtime.side_notes.append(
            "-IDAT post-deep frontier kept diagnostic seed(s), but none moved the deflate frontier; GroundHogDay skipped for this post-deep pass."
        )
        return None

    prefinal_result, _prefinal_seeds, prefinal_deferred = _GroundHogDay_run_idat_prefinal_seed_routes_runtime(
        runtime,
        data,
        analysis,
        seeds,
    )
    if prefinal_result is not None:
        return prefinal_result
    if prefinal_deferred:
        open_route_note = (
            "-IDAT deep beam stopped with checkpointed candidates still available; "
            "route left open for resume/post-deep passes."
        )
        if open_route_note not in runtime.side_notes:
            runtime.side_notes.append(open_route_note)
        return False, None

    return None


def _merge_idat_seed_candidates(
    *groups: tuple[idat_bruteforce.IdatDeepBeamCandidate, ...],
) -> tuple[idat_bruteforce.IdatDeepBeamCandidate, ...]:
    merged: list[idat_bruteforce.IdatDeepBeamCandidate] = []
    seen: set[str] = set()
    for candidate in itertools.chain.from_iterable(groups):
        stream = getattr(candidate, "stream", b"")
        if not stream:
            continue
        key = hashlib.sha1(stream).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        merged.append(candidate)
    return tuple(merged)


def _idat_deep_beam_failure_is_terminal(
    result: idat_bruteforce.IdatDeepBeamProbeResult,
) -> bool:
    if result.budget_exhausted:
        return True
    if not _merge_idat_seed_candidates(result.top_candidates):
        return True
    reason = str(result.reason or "").lower()
    if "frontier exhausted" in reason:
        return True
    return False


def _load_idat_deep_beam_seed_candidates(
    data: bytes,
    checkpoint_path: str,
) -> tuple[idat_bruteforce.IdatDeepBeamCandidate, ...]:
    if not checkpoint_path:
        return ()
    try:
        _before, _chunks, _stream, _source_hash, _count, candidates = (
            idat_bruteforce._load_frontier_candidates_for_progress(
                data,
                checkpoint_path,
                top_candidates=idat_bruteforce.DEEP_BEAM_DEFAULT_TOP_CANDIDATES,
                max_operation_depth=None,
            )
        )
    except Exception:
        return ()
    return tuple(candidates)


def _maybe_run_deflate_salvage_after_frontier(runtime: Any, data: bytes, analysis: idat.IdatStreamAnalysis) -> None:
    _run_deflate_resync_salvage_runtime(runtime, data, analysis)


def _idat_strategy_queue_max_steps(analysis: idat.IdatStreamAnalysis) -> int:
    if analysis.usable_scanlines > 0:
        return 16
    return 4


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

    final_investigation_ready = _final_investigation_ready(runtime)
    checkpoint_path, progress_path = _idat_deep_beam_paths(runtime)
    resume_state = idat_bruteforce.deep_beam_resume_state(data, checkpoint_path, progress_path)
    deep_budget = _runtime_deep_beam_budget(runtime)
    groundhogday_resume_seeds = _GroundHogDay_resume_seed_candidates(runtime, data, analysis)
    if groundhogday_resume_seeds:
        groundhogday_resume_next_day = _GroundHogDay_resume_next_day(runtime, data)
        runtime.side_notes.append(
            "-IDAT GroundHogDay resume-first: found %s artifact seed(s); next_day=%s; best %s."
            % (
                len(groundhogday_resume_seeds),
                groundhogday_resume_next_day,
                _GroundHogDay_idat_seed_progress_summary(groundhogday_resume_seeds),
            )
        )
        runtime.candy(
            "Cowsay",
            "I found GroundHogDay resume evidence in Debug_Payloads. I am jumping back to that loop instead of replaying the earlier IDAT probes.",
            "com",
        )
        runtime.candy(
            "Cowsay",
            "This is a checkpoint resume: each lap still needs a stronger seed, so repeated GroundHogDay titles mean controlled alternation, not a blind restart.",
            "com",
        )
        runtime.candy(
            "Cowsay",
            "GroundHogDay will resume at part %s, using the saved checkpoint instead of pretending this is day 1 again."
            % groundhogday_resume_next_day,
            "good",
        )
        prefinal_result, prefinal_seeds, prefinal_deferred = _GroundHogDay_run_idat_prefinal_seed_routes_runtime(
            runtime,
            data,
            analysis,
            groundhogday_resume_seeds,
        )
        if prefinal_result is not None:
            return prefinal_result
        if prefinal_deferred:
            return None
        runtime.side_notes.append(
            "-IDAT GroundHogDay resume made no new progress; earlier IDAT probes were not replayed in this pass."
        )
        final_seed_candidates = prefinal_seeds or groundhogday_resume_seeds
        if _should_run_final_investigation(
            runtime,
            analysis,
            final_seed_candidates,
            evidence_ready=final_investigation_ready,
        ):
            runtime.side_notes.append(
                "-IDAT GroundHogDay resume plateau reached; handing saved seeds to %s as the last resort."
                % FINAL_INVESTIGATION_LABEL
            )
            runtime.candy(
                "Cowsay",
                "GroundHogDay resume hit a plateau. I am handing its saved seeds to %s as the last resort."
                % FINAL_INVESTIGATION_LABEL,
                "com",
            )
            final_result = _run_idat_final_investigation_runtime(
                runtime,
                data,
                analysis,
                seed_candidates=final_seed_candidates,
            )
            if final_result is not None:
                return final_result
            return None
        _GroundHogDay_emit_unresolved_stop(
            runtime,
            reason="resume seeds did not improve and older IDAT probes were intentionally not replayed",
            seeds=groundhogday_resume_seeds,
        )
        return None
    if resume_state.available and resume_state.source_matches:
        frontier_clone, seed_candidates = _run_idat_frontier_routes_runtime(runtime, data, analysis)
        if frontier_clone is not None:
            return frontier_clone
        deep_seed_candidates = _load_idat_deep_beam_seed_candidates(data, checkpoint_path)
        resume_seed_candidates = _merge_idat_seed_candidates(seed_candidates, deep_seed_candidates)
        if deep_seed_candidates:
            post_deep_result = _run_idat_post_deep_frontier_routes_runtime(
                runtime,
                data,
                analysis,
                resume_seed_candidates,
            )
            if post_deep_result is not None:
                return post_deep_result
        if _should_run_final_investigation(
            runtime,
            analysis,
            resume_seed_candidates,
            evidence_ready=final_investigation_ready,
        ):
            prefinal_result, prefinal_seeds, prefinal_deferred = _GroundHogDay_run_idat_prefinal_seed_routes_runtime(
                runtime,
                data,
                analysis,
                resume_seed_candidates,
            )
            if prefinal_result is not None:
                return prefinal_result
            if prefinal_deferred:
                return None
            final_result = _run_idat_final_investigation_runtime(
                runtime,
                data,
                analysis,
                seed_candidates=prefinal_seeds or resume_seed_candidates,
            )
            if final_result is not None:
                return final_result
            return None
        if not resume_state.interrupted and resume_state.tested >= deep_budget:
            runtime.side_notes.append(
                "-IDAT deep beam budget exhausted for this source/budget; not relaunching automatically."
            )
            runtime.candy(
                "Cowsay",
                "The existing deep-beam progress already reached this budget. Increase IDAT_DEEP_BEAM_BUDGET or delete the checkpoint/progress to run it again.",
                "bad",
            )
            _maybe_run_deflate_salvage_after_frontier(runtime, data, analysis)
            _consume_idat_deflate_route(runtime)
            return False, None
        runtime.side_notes.append("-IDAT deep beam resume-first: existing checkpoint/progress matches this IDAT stream.")
        runtime.side_notes.append(idat_stream_diagnosis_note(analysis))
        deep_result = _run_idat_deep_beam_runtime(
            runtime,
            data,
            analysis,
            checkpoint_path=checkpoint_path,
            progress_path=progress_path,
            resume_state=resume_state,
            seed_candidates=seed_candidates,
            final_investigation_ready=final_investigation_ready,
        )
        if deep_result is None or deep_result == (False, None):
            _maybe_run_deflate_salvage_after_frontier(runtime, data, analysis)
        return deep_result
    if resume_state.available and not resume_state.source_matches:
        runtime.side_notes.append("-IDAT deep beam resume ignored: %s." % resume_state.reason)

    if not _remember_runtime_idat_probe(runtime, analysis):
        runtime.candy(
            "Cowsay",
            "I already poked that exact IDAT wound. Same smell, same bandage budget.",
            "com",
        )
        return None

    focused_crc = try_focused_idat_crc_forge(runtime, data, analysis)
    if focused_crc is not None:
        return focused_crc

    runtime.candy(
        "Cowsay",
        "The boxes line up now, but the compressed stuff inside is still screaming.",
        "bad",
    )
    runtime.side_notes.append(idat_stream_diagnosis_note(analysis))
    runtime.side_notes.extend(idat_bruteforce.idat_crc_evidence_summary_lines(data))
    if analysis.decompressed_size == 0:
        runtime.candy(
            "Cowsay",
            "The first deflate table breaks before I can even pull one scanline out.",
            "bad",
        )
        runtime.candy(
            "Cowsay",
            "I am logging the local dynamic-Huffman evidence before trying a repair.",
            "com",
        )
        runtime.candy("Title", "probe_idat_deflate_local_candidates")
        runtime.side_notes.extend(
            idat_bruteforce.idat_local_deflate_diagnostic_summary_lines(
                data,
                analysis=analysis,
            )
        )
        local_probe = idat_bruteforce.probe_idat_deflate_local_candidates(
            data,
            progress=_runtime_idat_queue_progress(runtime),
        )
        runtime.side_notes.append(idat_bruteforce.probe_summary_line(local_probe))
        runtime.side_notes.extend(idat_bruteforce.candidate_summary_lines(local_probe))
        runtime.side_notes.extend(idat_bruteforce.diagnostic_candidate_summary_lines(local_probe))
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
        runtime.side_notes.extend(idat_bruteforce.probe_detail_summary_lines(header_probe))

        if header_probe.best is None:
            diagnostic_lines = idat_bruteforce.diagnostic_candidate_summary_lines(header_probe)
            runtime.side_notes.extend(diagnostic_lines)
            if diagnostic_lines:
                runtime.candy(
                    "Cowsay",
                    "I found a pre-scanline deflate route, but it still gives me zero usable PNG scanlines.",
                    "com",
                )
                runtime.candy(
                    "Cowsay",
                    "I am logging it as diagnostic evidence, not writing it as a repair.",
                    "com",
                )
            runtime.candy(
                "Cowsay",
                "I did not get a usable scanline from the deflate-header probe. I will keep probing routes, but still no blind clone.",
                "bad",
            )
            _probe_idat_lf_route_for_diagnostics(runtime, data, analysis)
            runtime.side_notes.append("-IDAT deflate header probe found no clone-worthy scanline progress.")
            runtime.side_notes.append("-IDAT diagnostic LF route found no clone-worthy scanline progress.")
            frontier_clone, seed_candidates = _run_idat_frontier_routes_runtime(runtime, data, analysis)
            if frontier_clone is not None:
                return frontier_clone
            deep_result = _run_idat_deep_beam_runtime(
                runtime,
                data,
                analysis,
                checkpoint_path=checkpoint_path,
                progress_path=progress_path,
                seed_candidates=seed_candidates,
                final_investigation_ready=final_investigation_ready,
            )
            if deep_result is None or deep_result == (False, None):
                _maybe_run_deflate_salvage_after_frontier(runtime, data, analysis)
            return deep_result

        candidate = header_probe.best
        runtime.side_notes.extend(idat_bruteforce.candidate_summary_lines(header_probe))
        runtime.candy(
            "Cowsay",
            "I found a header byte that gets real scanline progress. Still an hypothesis, but now it has a pulse.",
            "good",
        )
        runtime.candy(
            "Cowsay",
            idat_bruteforce.candidate_patch_note(candidate),
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
        return _write_complete_idat_candidate_clone(
            runtime,
            candidate,
            summary,
            route_label="deflate header probe",
            success_message="The deflate-header probe found a complete IDAT candidate with validated image progress.",
        )

    if analysis.decompressed_size > 0 or analysis.usable_scanlines > 0:
        prefix_frontier = _run_idat_prefix_frontier_routes_runtime(runtime, data, analysis)
        if prefix_frontier is not None:
            return prefix_frontier

    runtime.candy(
        "Cowsay",
        "I will run the bounded IDAT strategy queue: strict byte, pre-error bit flips, then a wider byte probe.",
        "com",
    )
    runtime.candy("Title", "probe_idat_deflate_strategy_queue")
    probe = idat_bruteforce.probe_idat_deflate_strategy_queue(
        data,
        max_steps=_idat_strategy_queue_max_steps(analysis),
        progress=_runtime_idat_queue_progress(runtime),
    )
    runtime.side_notes.append(idat_bruteforce.probe_summary_line(probe))

    if probe.best is None:
        runtime.candy(
            "Cowsay",
            "I tried the small deflate probe. Nothing got better, so I could send the fish into a wider net.",
            "bad",
        )
        if _should_run_final_investigation(
            runtime,
            analysis,
            evidence_ready=final_investigation_ready,
        ):
            prefinal_result, prefinal_seeds, prefinal_deferred = _GroundHogDay_run_idat_prefinal_seed_routes_runtime(
                runtime,
                data,
                analysis,
            )
            if prefinal_result is not None:
                return prefinal_result
            if prefinal_deferred:
                return None
            final_result = _run_idat_final_investigation_runtime(
                runtime,
                data,
                analysis,
                seed_candidates=prefinal_seeds,
            )
            if final_result is not None:
                return final_result
            return None

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
            idat_bruteforce.candidate_patch_note(candidate),
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
                "Step %s: %s"
                % (index, idat_bruteforce.candidate_patch_note(candidate_patch)),
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
    return _write_complete_idat_candidate_clone(
        runtime,
        candidate,
        summary,
        route_label="strategy queue",
        success_message="The IDAT strategy queue found a complete IDAT candidate with validated image progress.",
    )


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
        remember_failed_idat_crc_only_patch(runtime, finding, tools, validation)

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
            _mark_idat_deflate_route_consumed_if_needed(runtime, probe_result)
            return probe_result

    validation = validate_idat_crc_only_patch(runtime, tools)
    if validation.can_save:
        return None

    remember_failed_idat_crc_only_patch(runtime, finding, tools, validation)
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
        if tools.chunk == b"IDAT" and runtime.is_deferred_idat_crc_route(decision.finding, tools):
            runtime.set_idat_crc_patch_failed(True)
            runtime.set_idat_crc_patch_failed_finding(decision.finding)
            runtime.candy(
                "Cowsay",
                "I already checked that IDAT CRC-only route. It still only makes the checksum label prettier.",
                "com",
            )
            return defer_wrong_crc(runtime, tools)

        clean_idat_crc_patch = save_clean_idat_crc_only_patch_before_other_errors(runtime, tools)
        if clean_idat_crc_patch is not None:
            return clean_idat_crc_patch

        if tools.chunk == b"IDAT":
            validation = validate_idat_crc_only_patch(runtime, tools)
            if not validation.can_save:
                already_explained = already_explained_invalid_idat_crc_only_patch(runtime)
                remember_failed_idat_crc_only_patch(runtime, decision.finding, tools, validation)
                if already_explained:
                    runtime.candy(
                        "Cowsay",
                        repeated_deferred_repair_message(error_label="wrong CRC", chunk=b"IDAT"),
                        "com",
                    )
                else:
                    runtime.candy(
                        "Cowsay",
                        "I tested the cheap CRC patch in my head. It still breaks: %s" % validation.reason,
                        "bad",
                    )
                    runtime.candy(
                        "Cowsay",
                        "So i'm not asking you to bless the same fake fix while other errors are still visible.",
                        "com",
                    )
                return defer_wrong_crc(runtime, tools)

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


PNG_KNOWN_CRITICAL_CHUNKS = {b"IHDR", b"PLTE", b"IDAT", b"IEND"}


def _chunk_type_label(chunk_type: bytes) -> str:
    try:
        return chunk_type.decode("ascii")
    except UnicodeDecodeError:
        return repr(chunk_type)


def _chunk_type_name_problem(chunk_type: bytes) -> str | None:
    if len(chunk_type) != 4:
        return "type length is %s, expected 4" % len(chunk_type)
    if not all(65 <= value <= 90 or 97 <= value <= 122 for value in chunk_type):
        return "not ASCII alphabetic"
    if chunk_type[2] & 0x20:
        return "reserved bit is lowercase"
    if not (chunk_type[0] & 0x20) and chunk_type not in PNG_KNOWN_CRITICAL_CHUNKS:
        return "unknown critical chunk"
    return None


def _chunk_name_audit(data: bytes) -> tuple[tuple[png.PngChunk, ...], tuple[str, ...], str]:
    try:
        chunks = tuple(png.iter_chunks(data))
    except Exception as exc:
        return (), ("parser stopped before chunk-name audit completed: %s" % exc,), "unparseable"

    problems: list[str] = []
    for chunk in chunks:
        problem = _chunk_type_name_problem(chunk.chunk_type)
        if problem is None:
            continue
        problems.append(
            "%s@0x%x (%s)" % (
                _chunk_type_label(chunk.chunk_type),
                chunk.offset,
                problem,
            )
        )
    return chunks, tuple(problems), "ok"


def _confirm_chunk_names_for_idat_chain(runtime: Any, original_data: bytes, fixed_data: bytes) -> bool:
    original_chunks, original_problems, original_status = _chunk_name_audit(original_data)
    fixed_chunks, fixed_problems, fixed_status = _chunk_name_audit(fixed_data)

    if fixed_status != "ok" or fixed_problems:
        details = "; ".join(fixed_problems) if fixed_problems else fixed_status
        runtime.side_notes.append(
            "-IDAT convoy chunk-name gate: blocked; proposed realignment still has bad chunk name(s): %s."
            % details
        )
        runtime.candy(
            "Cowsay",
            "I am not launching the IDAT convoy because the realigned candidate still has bad chunk names.",
            "bad",
        )
        return False

    fixed_types = ",".join(_chunk_type_label(chunk.chunk_type) for chunk in fixed_chunks)
    if original_status != "ok" or original_problems:
        details = "; ".join(original_problems) if original_problems else original_status
        runtime.side_notes.append(
            "-IDAT convoy chunk-name gate: current parser still sees bad chunk name(s): %s."
            % details
        )
        runtime.side_notes.append(
            "-IDAT convoy chunk-name gate: after proposed realignment, chunk names are valid/known: %s."
            % fixed_types
        )
        runtime.candy(
            "Cowsay",
            "Chunk-name check: the current parse is not clean, but the proposed IDAT realignment produces clean chunk names.",
            "com",
        )
        return True

    original_types = ",".join(_chunk_type_label(chunk.chunk_type) for chunk in original_chunks)
    runtime.side_notes.append(
        "-IDAT convoy chunk-name gate: current chunk names are valid/known before convoy: %s."
        % original_types
    )
    return True


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
        _mark_idat_deflate_route_consumed_if_needed(runtime, probe_result)
        return probe_result

    _explain_idat_stream_after_header_repair(runtime, analysis, already_aligned=True)
    runtime.candy(
        "Cowsay",
        "So I am not adding IEND, renaming chunks, or polishing CRC labels on this pass.",
        "com",
    )
    return False, None


def _existing_fixed_clone_with_data(file_origin: Any, file_dir: Any, data: bytes) -> Path | None:
    origin = str(file_origin or "").strip()
    if not origin:
        return None
    try:
        folder = Path(output.clone_folder(origin, str(file_dir or "")))
    except Exception:
        return None
    if not folder.exists() or not folder.is_dir():
        return None
    pattern = "%s.*_Fixed.png" % output.repair_stem(origin, str(file_dir or ""))
    for candidate in sorted(folder.glob(pattern)):
        if not candidate.is_file():
            continue
        try:
            if candidate.read_bytes() == data:
                return candidate
        except OSError:
            continue
    return None


def _write_or_reuse_idat_convoy_clone(runtime: Any, data: bytes, summary: str) -> tuple[Any, bool]:
    existing = _existing_fixed_clone_with_data(
        getattr(runtime, "file_origin", ""),
        getattr(runtime, "file_dir", ""),
        data,
    )
    if existing is not None:
        runtime.side_notes.append(
            "-IDAT convoy clone reused: %s already contains this working data."
            % existing
        )
        runtime.candy(
            "Cowsay",
            "The IDAT-convoy working clone already exists, so I am reusing it instead of writing another Fixed file.",
            "com",
        )
        queue_existing_clone = getattr(runtime, "queue_existing_clone", None)
        if callable(queue_existing_clone):
            return queue_existing_clone(str(existing)), True
        return str(existing), True
    return runtime.write_clone(data, summary), False


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
    if not _confirm_chunk_names_for_idat_chain(runtime, data, analysis.fixed_data):
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
    summary = "\n".join(
        [
            summary,
            idat_stream_diagnosis_note(stream_analysis),
            "-IDAT convoy clone: intermediate working clone before deflate deep beam.",
        ]
    )
    convoy_clone, convoy_reused = _write_or_reuse_idat_convoy_clone(runtime, analysis.fixed_data, summary)
    model_path = _idat_convoy_model_path(runtime)
    if model_path:
        model_written = idat_bruteforce.write_idat_convoy_model(
            model_path,
            data,
            analysis.fixed_data,
            analysis,
        )
        runtime.side_notes.append(
            "-IDAT convoy model %s: %s."
            % ("written" if model_written else "reused", model_path)
        )
    if convoy_reused:
        runtime.side_notes.append("-IDAT convoy clone reused after clean chunk-name gate.")
    else:
        runtime.side_notes.append("-IDAT convoy clone written after clean chunk-name gate.")
    runtime.candy(
        "Cowsay",
        "IDAT convoy clone written/reused; restart from this clone before deflate probing.",
        "com",
    )
    runtime.side_notes.append(
        "-IDAT convoy clone boundary: deep-beam deferred until the next pass from this clone."
    )
    return True, convoy_clone


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


def _chunk_type_bytes(value: Any) -> bytes | None:
    if isinstance(value, bytes) and len(value) == 4:
        return value
    if isinstance(value, str) and len(value) == 4:
        try:
            return value.encode("latin1")
        except UnicodeEncodeError:
            return None
    return None


def _idat_typo_distance(chunk_type: bytes) -> int:
    return sum(1 for left, right in zip(chunk_type, b"IDAT") if left != right)


def _wrong_chunk_name_has_idat_context(
    decision: fixit_felix.WrongChunkNameDecision,
    tools: relics.WrongChunkNameTools,
) -> bool:
    previous_chunk = _chunk_type_bytes(tools.previous_chunk)
    next_marker = _chunk_type_bytes(getattr(tools, "next_marker", None))
    finding = str(decision.finding)
    return (
        previous_chunk == b"IDAT"
        or next_marker == b"IDAT"
        or "Chunk[b'IDAT']" in finding
        or 'Chunk["IDAT"]' in finding
    )


def _idatish_wrong_chunk_name(
    decision: fixit_felix.WrongChunkNameDecision,
    tools: relics.WrongChunkNameTools,
) -> bytes | None:
    chunk_type = _chunk_type_bytes(tools.chunk_type)
    if chunk_type is None or chunk_type == b"IDAT":
        return None
    if decision.bad_crc is not True:
        return None
    if _idat_typo_distance(chunk_type) > 1:
        return None
    if not _wrong_chunk_name_has_idat_context(decision, tools):
        return None
    return chunk_type


def _wrong_chunk_type_index_candidates(value: Any) -> tuple[int, ...]:
    try:
        offset = value if isinstance(value, int) else int(str(value), 0)
    except (TypeError, ValueError):
        return ()
    candidates = [offset]
    doubled = offset * 2
    if doubled != offset:
        candidates.append(doubled)
    return tuple(candidates)


def _wrong_chunk_at_stored_type_offset(
    data: bytes,
    tools: relics.WrongChunkNameTools,
    expected_type: bytes,
) -> tuple[int, png.PngChunk] | None:
    for type_index in _wrong_chunk_type_index_candidates(tools.chunk_type_offset):
        if type_index < 8 or type_index % 2:
            continue
        type_offset = type_index // 2
        if data[type_offset : type_offset + 4] != expected_type:
            continue
        chunk = png.chunk_at(data, type_offset - 4)
        if chunk is not None and chunk.chunk_type == expected_type:
            return type_index, chunk
    return None


def _idat_name_repair_crc_note(chunk: png.PngChunk) -> str:
    computed_crc = binascii.crc32(b"IDAT" + chunk.data) & 0xFFFFFFFF
    if computed_crc == chunk.crc:
        return "-Direct IDAT chunk-name repair: stored CRC matches after renaming to IDAT."
    return (
        "-Direct IDAT chunk-name repair: stored CRC still mismatches after renaming "
        "to IDAT; keeping the repaired name and leaving CRC/data repair for later."
    )


def try_direct_idatish_chunk_name_repair(
    runtime: WrongChunkNameRuntime,
    decision: fixit_felix.WrongChunkNameDecision,
    chkd: str,
    tools: relics.WrongChunkNameTools,
) -> tuple[bool, Any] | None:
    chunk_type = _idatish_wrong_chunk_name(decision, tools)
    if chunk_type is None:
        return None

    route_action = "direct_idat_name"
    if runtime.is_wrong_chunk_name_route_tried(decision.finding, chkd, tools, route_action):
        _emit_wrong_chunk_name_deja_vu(runtime, tools)
        if decision.action == "ask_length_probe":
            runtime.set_skip_bad_next_name(True)
        else:
            runtime.set_skip_bad_current_name(True)
        return False, None

    try:
        data = bytes.fromhex(runtime.data_hex)
    except ValueError:
        return None

    located = _wrong_chunk_at_stored_type_offset(data, tools, chunk_type)
    if located is None:
        return None

    type_index, chunk = located
    type_offset = type_index // 2
    fixed_data = bytearray(data)
    fixed_data[type_offset : type_offset + 4] = b"IDAT"

    changed = _idat_typo_distance(chunk_type)
    chunk_label = chunk_type.decode("latin1", errors="replace")
    repair_note = (
        "-Repair hypothesis tried: direct chunk-name recovery for %s at %s; "
        "changed %s byte%s -> IDAT."
        % (
            chunk_label,
            _route_offset(type_index),
            changed,
            "" if changed == 1 else "s",
        )
    )
    crc_note = _idat_name_repair_crc_note(chunk)
    runtime.side_notes.extend((repair_note, crc_note))
    runtime.remember_wrong_chunk_name_route(decision.finding, chkd, tools, route_action)
    runtime.candy(
        "Cowsay",
        "This chunk name looks like a damaged IDAT at the recorded offset, so I am fixing that sign first.",
        "good",
    )
    runtime.candy(
        "Cowsay",
        "CRC can still complain after the rename; if it does, I am leaving that as the next problem.",
        "com",
    )
    return True, runtime.write_clone(bytes(fixed_data), "\n".join((repair_note, crc_note)))


def _nearby_result_is_scan_summary(result: Any) -> bool:
    return getattr(result, "action", None) == "scan_summary"


def _defer_length_symptom_name_bruteforce(
    runtime: WrongChunkNameRuntime,
    tools: relics.WrongChunkNameTools,
    reason: str,
) -> tuple[bool, None]:
    _remember_wrong_chunk_name_note(
        runtime,
        tools,
        "deferred",
        "%s; not brute-forcing a chunk name that is probably payload bytes" % reason,
    )
    runtime.set_skip_bad_next_name(True)
    runtime.set_skip_bad_current_name(True)
    return False, None


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

    def idat_chain_fallback() -> tuple[bool, Any] | None:
        route_action = "idat_chain"
        if runtime.is_wrong_chunk_name_route_tried(decision.finding, chkd, tools, route_action):
            _emit_wrong_chunk_name_deja_vu(runtime, tools)
            runtime.set_skip_bad_current_name(True)
            return False, None
        runtime.remember_wrong_chunk_name_route(decision.finding, chkd, tools, route_action)
        block_after_alignment = not wrong_chunk_name_precedes_first_parsed_idat(runtime.data_hex, tools)
        return try_idat_chain_header_repair(
            runtime,
            block_if_aligned_bad_stream=block_after_alignment,
        )

    if decision.action == "ask_length_probe" and runtime.is_wrong_chunk_name_route_tried(
        decision.finding,
        chkd,
        tools,
        "length_probe",
    ):
        fallback = idat_chain_fallback()
        if fallback is not None:
            return fallback
        return _defer_length_symptom_name_bruteforce(
            runtime,
            tools,
            "length probe route was already tried",
        )

    emit_wrong_chunk_name_critical(runtime, decision.finding)
    runtime.ancillary(tools.chunk_type)
    describe_wrong_chunk_name(runtime, decision)

    direct_idat_name_repair = try_direct_idatish_chunk_name_repair(runtime, decision, chkd, tools)
    if direct_idat_name_repair is not None:
        return direct_idat_name_repair

    if decision.action == "ask_length_probe":
        route_action = "length_probe"
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
        runtime.remember_wrong_chunk_name_route(decision.finding, chkd, tools, route_action)
        _remember_wrong_chunk_name_note(runtime, tools, "tried")
        result = runtime.nearby_chunk(
            tools.chunk_type,
            tools.chunk_length,
            tools.chunk_type_offset,
            False,
            decision.finding,
        )
        if result is not None and not _nearby_result_is_scan_summary(result):
            return True, result

        fallback = idat_chain_fallback()
        if fallback is not None:
            return fallback
        return _defer_length_symptom_name_bruteforce(
            runtime,
            tools,
            "length probe found no clone-worthy repair",
        )

    if decision.action == "ask_bruteforce":
        result = ask_wrong_chunk_name_bruteforce(runtime, decision, chkd, tools)
        if result[0]:
            return result
        fallback = idat_chain_fallback()
        if fallback is not None:
            return fallback
        return result

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


def _is_benign_pre_libpng_metadata_finding(finding: Any) -> bool:
    text = str(finding).lower()
    if "missplaced" in text or "must appear" in text or "must appears" in text:
        return False
    if "length is not valid" in text or "wrong" in text:
        return False
    return any(
        clue in text
        for clue in (
            "overided by srgb chunk",
            "overridden by srgb chunk",
            "srgb or iccp already present chrm will be overide",
            "known incorrect srgb profile",
            "iccp: profile is noisy",
        )
    )


def _discard_benign_pre_libpng_metadata_findings(
    runtime: NoNextChunkRuntime,
    findings: tuple[Any, ...],
) -> tuple[Any, ...]:
    actionable: list[Any] = []
    for finding in findings:
        if not _is_benign_pre_libpng_metadata_finding(finding):
            actionable.append(finding)
            continue
        relics.discard_pandora_error(runtime.pandora_box, finding)
        runtime.side_notes.append(
            "-Found benign metadata advisory before libpng: %s." % finding
        )
    return tuple(actionable)


def stop_before_libpng_for_unresolved_findings(
    runtime: NoNextChunkRuntime,
    findings: tuple[Any, ...],
) -> tuple[bool, Any]:
    findings = _discard_benign_pre_libpng_metadata_findings(runtime, findings)
    if not findings:
        runtime.candy(
            "Cowsay",
            "Only harmless metadata paperwork is left. I am feeding libpng before making the repair call.",
            "com",
        )
        runtime.side_notes.append(
            "-LibpngCheck allowed after filtering benign metadata advisories."
        )
        return True, runtime.libpng_check(runtime.sample)

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

    if findings and all(is_idat_wrong_crc_finding(finding) for finding in findings):
        runtime.candy(
            "Cowsay",
            "Only IDAT CRC wounds remain, and the IDAT stream is still invalid. I am handing this to HermesProbe instead of stopping here.",
            "com",
        )
        probe_result = try_idat_deflate_bruteforce(runtime)
        if probe_result is not None:
            _mark_idat_deflate_route_consumed_if_needed(runtime, probe_result)
            return probe_result

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

    if decision.action == "write_partial_iend_tail":
        runtime.candy("Cowsay", "And it seems that it matches with some part of IEND chunk ..", "com")
        runtime.candy("Cowsay", "I am replacing that partial tail with a clean IEND chunk.", "good")
        runtime.side_notes.append("-Part or full IEND chunk detected:%s" % (str(exceeding)))
        runtime.debug_print("-iendsample:", fixit_felix.GOOD_IEND_HEX)
        runtime.debug_print("-exceeding:", exceeding)
        cut_hex = runtime.data_hex[: runtime.crc_offset + 8]
        fixed = bytes.fromhex(cut_hex + fixit_felix.GOOD_IEND_HEX)
        note = "-FixItFelix:replaced partial IEND tail with canonical IEND chunk."
        runtime.side_notes.append(note)
        return True, runtime.write_clone(fixed, note)

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


def try_no_next_partial_iend_tail(
    runtime: NoNextChunkRuntime,
    finding: Any,
) -> tuple[bool, Any] | None:
    append_decision = fixit_felix.no_next_append_iend_decision(
        runtime.data_hex,
        crc_offset=runtime.crc_offset,
    )
    if append_decision.action != "write_partial_iend_tail":
        return None
    report_no_next_exceeding(runtime, append_decision.exceeding)
    return apply_no_next_append_iend(runtime, append_decision, finding)


def handle_no_next_ask_length_probe(
    runtime: NoNextChunkRuntime,
    finding: Any,
    chkd: str,
    tools: relics.NoNextChunkTools,
) -> tuple[bool, Any]:
    partial_iend_tail = try_no_next_partial_iend_tail(runtime, finding)
    if partial_iend_tail is not None:
        return partial_iend_tail

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
