from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


LegacyCall = Callable[..., Any]


@dataclass(frozen=True)
class CheckPointRuntime:
    write_clone: LegacyCall
    dummy_chunk: LegacyCall
    summarise: LegacyCall
    find_fucking_magic: LegacyCall
    check_chunk_name: LegacyCall
    save_clone: LegacyCall
    fix_it_felix: LegacyCall
    relics: LegacyCall
    smash_brute_brawl: LegacyCall
    candy: LegacyCall
    emit: LegacyCall
    end: LegacyCall


def run_write_clone(runtime: CheckPointRuntime, toolkit: tuple[Any, ...]) -> tuple[bool, Any]:
    return True, runtime.write_clone(toolkit[0], "-About to save.")


def run_dummy_chunk_from_the_good_place(
    runtime: CheckPointRuntime,
    toolkit: tuple[Any, ...],
    info: Any,
) -> tuple[bool, Any]:
    return True, runtime.dummy_chunk(toolkit[0], toolkit[1], toolkit[2], toolkit[3], info)


def run_return_value(return_value: Any) -> tuple[bool, Any]:
    return True, return_value


def run_summarise_and_write_clone(
    runtime: CheckPointRuntime,
    summary: Any,
    toolkit: tuple[Any, ...],
) -> tuple[bool, Any]:
    runtime.summarise(summary)
    return True, runtime.write_clone(toolkit[0], "-About to save.")


def run_find_fucking_magic(runtime: CheckPointRuntime) -> tuple[bool, Any]:
    return True, runtime.find_fucking_magic()


def run_check_chunk_name(
    runtime: CheckPointRuntime,
    raw_next_chunk: Any,
    chunk: Any,
    toolkit: tuple[Any, ...],
) -> tuple[bool, Any]:
    return True, runtime.check_chunk_name(raw_next_chunk, int(toolkit[0], 16), chunk, True)


def run_save_clone(runtime: CheckPointRuntime, toolkit: tuple[Any, ...]) -> tuple[bool, Any]:
    return True, runtime.save_clone(toolkit[0], toolkit[1], toolkit[2], toolkit[3])


def run_save_clone_missing_bytes(
    runtime: CheckPointRuntime,
    toolkit: tuple[Any, ...],
) -> tuple[bool, Any]:
    return True, runtime.save_clone(
        toolkit[0],
        toolkit[2],
        toolkit[1] + toolkit[2],
        "Fixing Missing bytes corruption",
    )


def run_fix_it_felix_continue(runtime: CheckPointRuntime, return_value: Any) -> tuple[bool, Any]:
    runtime.fix_it_felix(return_value)
    return False, None


def run_fix_it_felix_return(runtime: CheckPointRuntime, return_value: Any) -> tuple[bool, Any]:
    return True, runtime.fix_it_felix(return_value)
