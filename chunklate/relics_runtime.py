from __future__ import annotations

from collections.abc import Callable
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any


AskChoice = Callable[[str, Sequence[str], str], Any]
LegacyCall = Callable[..., Any]


@dataclass(frozen=True)
class RelicsRuntime:
    save_clone: LegacyCall
    smash_brute_brawl: LegacyCall
    full_chunk_forcer_no_crc: LegacyCall
    tk_manual_plte: LegacyCall
    remove_chunk: LegacyCall
    ask_choice: AskChoice


def run_save_clone_plan(runtime: RelicsRuntime, save_plan: Any) -> Any:
    return runtime.save_clone(
        save_plan.fixed_data,
        save_plan.start,
        save_plan.end,
        save_plan.info,
    )


def run_wrong_crc_brawl_plan(runtime: RelicsRuntime, brawl_plan: Any) -> Any:
    kwargs = {"OldCrc": brawl_plan.old_crc}
    if brawl_plan.bf_mode is not None:
        kwargs["BfMode"] = brawl_plan.bf_mode
    if brawl_plan.brute_length is not None:
        kwargs["BruteLength"] = brawl_plan.brute_length

    return runtime.smash_brute_brawl(
        brawl_plan.target_file,
        brawl_plan.chunk,
        brawl_plan.chunk_length,
        brawl_plan.data_offset,
        brawl_plan.from_error,
        **kwargs,
    )


def run_dummy_chunk_brawl_plan(runtime: RelicsRuntime, brawl_plan: Any) -> Any:
    return runtime.smash_brute_brawl(
        brawl_plan.target_file,
        brawl_plan.chunk,
        brawl_plan.chunk_length,
        brawl_plan.data_offset,
        brawl_plan.from_error,
    )


def run_getinfo_brawl_plan(runtime: RelicsRuntime, brawl_plan: Any) -> Any:
    return runtime.smash_brute_brawl(
        brawl_plan.target_file,
        brawl_plan.chunk,
        brawl_plan.chunk_length,
        brawl_plan.data_offset,
        brawl_plan.from_error,
        BfMode=brawl_plan.bf_mode,
    )


def run_full_chunk_forcer_plan(runtime: RelicsRuntime, forcer_plan: Any) -> Any:
    return runtime.full_chunk_forcer_no_crc(
        forcer_plan.target_file,
        forcer_plan.chunk,
        forcer_plan.start,
        forcer_plan.end,
        forcer_plan.from_error,
    )


def run_plte_manual_plan(runtime: RelicsRuntime, plte_plan: Any) -> Any:
    return runtime.tk_manual_plte(
        plte_plan.target_file,
        plte_plan.chunk,
        plte_plan.chunk_length,
        plte_plan.data_offset,
        plte_plan.from_error,
    )


def run_plte_remove_plan(runtime: RelicsRuntime, plte_plan: Any) -> Any:
    return runtime.remove_chunk(
        plte_plan.start,
        plte_plan.end,
        plte_plan.info,
    )


def run_plte_brawl_plan(runtime: RelicsRuntime, plte_plan: Any) -> Any:
    kwargs = {"EditMode": plte_plan.edit_mode}
    if plte_plan.old_crc is not None:
        kwargs["OldCrc"] = plte_plan.old_crc

    return runtime.smash_brute_brawl(
        plte_plan.target_file,
        plte_plan.chunk,
        plte_plan.chunk_length,
        plte_plan.data_offset,
        plte_plan.from_error,
        **kwargs,
    )


def ask_plte_repair(runtime: RelicsRuntime, relics_module: Any, has_bad_crc: bool) -> Any:
    return runtime.ask_choice(
        relics_module.plte_repair_prompt(has_bad_crc),
        relics_module.plte_repair_choices(has_bad_crc),
        relics_module.plte_repair_retry_prompt(has_bad_crc),
    )
