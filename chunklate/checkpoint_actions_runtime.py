from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from . import checkpoint_runtime


LegacyCall = Callable[..., Any]


@dataclass(frozen=True)
class CheckPointActionRuntime:
    checkpoint: checkpoint_runtime.CheckPointRuntime
    side_notes: Any
    apply_flags: LegacyCall
    raw_next_chunk: Any
    get_brute_level: Callable[[], int]
    set_brute_level: Callable[[int], Any]
    eta: int
    ihdr_interlace: str


def build_checkpoint_action_runtime_from_namespace(namespace: dict[str, Any]) -> CheckPointActionRuntime:
    return CheckPointActionRuntime(
        checkpoint=namespace["CheckPoint_Runtime"](),
        side_notes=namespace["SideNotes"],
        apply_flags=namespace["CheckPoint_Apply_Flags"],
        raw_next_chunk=namespace["Raw_NextChunk"],
        get_brute_level=lambda: namespace["Brute_LvL"],
        set_brute_level=lambda value: namespace.__setitem__("Brute_LvL", value),
        eta=namespace["ETA"],
        ihdr_interlace=namespace["IHDR_Interlace"],
    )


def action_write_clone(runtime: CheckPointActionRuntime, decision, chunk, info, toolkit):
    return checkpoint_runtime.run_write_clone(runtime.checkpoint, toolkit)


def action_dummy_chunk_from_the_good_place(runtime: CheckPointActionRuntime, decision, chunk, info, toolkit):
    return checkpoint_runtime.run_dummy_chunk_from_the_good_place(
        runtime.checkpoint,
        toolkit,
        info,
    )


def action_return_value(runtime: CheckPointActionRuntime, decision, chunk, info, toolkit):
    return checkpoint_runtime.run_return_value(decision.return_value)


def action_summarise_and_write_clone(runtime: CheckPointActionRuntime, decision, chunk, info, toolkit):
    return checkpoint_runtime.run_summarise_and_write_clone(
        runtime.checkpoint,
        decision.summary,
        toolkit,
    )


def action_find_fucking_magic(runtime: CheckPointActionRuntime, decision, chunk, info, toolkit):
    return checkpoint_runtime.run_find_fucking_magic(runtime.checkpoint)


def action_check_chunk_name(runtime: CheckPointActionRuntime, decision, chunk, info, toolkit):
    return checkpoint_runtime.run_check_chunk_name(
        runtime.checkpoint,
        runtime.raw_next_chunk,
        chunk,
        toolkit,
    )


def action_save_clone(runtime: CheckPointActionRuntime, decision, chunk, info, toolkit):
    return checkpoint_runtime.run_save_clone(runtime.checkpoint, toolkit)


def action_save_clone_missing_bytes(runtime: CheckPointActionRuntime, decision, chunk, info, toolkit):
    return checkpoint_runtime.run_save_clone_missing_bytes(runtime.checkpoint, toolkit)


def action_fix_it_felix_continue(runtime: CheckPointActionRuntime, decision, chunk, info, toolkit):
    return checkpoint_runtime.run_fix_it_felix_continue(
        runtime.checkpoint,
        decision.return_value,
    )


def action_fix_it_felix_return(runtime: CheckPointActionRuntime, decision, chunk, info, toolkit):
    return checkpoint_runtime.run_fix_it_felix_return(
        runtime.checkpoint,
        decision.return_value,
    )


def action_libpng_warning_relics(runtime: CheckPointActionRuntime, decision, chunk, info, toolkit):
    return checkpoint_runtime.run_libpng_warning_relics(runtime.checkpoint, info)


def action_discard_libpng_warning(runtime: CheckPointActionRuntime, decision, chunk, info, toolkit):
    return checkpoint_runtime.run_discard_libpng_warning(
        runtime.checkpoint,
        decision.action,
        info,
    )


def action_libpng_end_success(runtime: CheckPointActionRuntime, decision, chunk, info, toolkit):
    return checkpoint_runtime.run_libpng_end_success(runtime.checkpoint)


def smash_brute_brawl_relaunch(
    runtime: CheckPointActionRuntime,
    toolkit,
    from_error,
    *,
    bf_mode=None,
    has_old_crc=False,
    old_crc=None,
):
    return checkpoint_runtime.run_smash_brute_brawl_relaunch(
        runtime.checkpoint,
        toolkit,
        from_error,
        bf_mode=bf_mode,
        has_old_crc=has_old_crc,
        old_crc=old_crc,
    )


def action_smash_brute_brawl_retry_ihdr(runtime: CheckPointActionRuntime, decision, chunk, info, toolkit):
    brute_level = runtime.get_brute_level() + 1
    runtime.set_brute_level(brute_level)
    runtime.side_notes.append("-CheckPoint: %s" % info)
    return checkpoint_runtime.run_smash_brute_brawl_retry_ihdr(
        runtime.checkpoint,
        toolkit,
        toolkit[8],
        brute_level,
    )


def action_smash_brute_brawl_ask_twobytes_retry(runtime: CheckPointActionRuntime, decision, chunk, info, toolkit):
    brute_level = runtime.get_brute_level() + 1
    runtime.set_brute_level(brute_level)
    answer = checkpoint_runtime.ask_smash_brute_brawl_twobytes_retry(
        runtime.checkpoint,
        toolkit,
        brute_level=brute_level,
        eta=runtime.eta,
        ihdr_interlace=runtime.ihdr_interlace,
    )
    if answer:
        runtime.side_notes.append("-CheckPoint: Increasing BfLvl: %s" % info)
        if "OldCrc" in info:
            smash_brute_brawl_relaunch(
                runtime,
                toolkit,
                toolkit[9],
                has_old_crc=True,
                old_crc=toolkit[8],
            )
        else:
            smash_brute_brawl_relaunch(runtime, toolkit, toolkit[8])
        return False, None

    return smash_brute_brawl_handle_twobytes_decline(runtime, info, toolkit)


def smash_brute_brawl_handle_twobytes_decline(runtime: CheckPointActionRuntime, info, toolkit):
    if toolkit[1] == b"IDAT" and runtime.ihdr_interlace == "1":
        answer = checkpoint_runtime.ask_smash_brute_brawl_dummy_idat_fallback(
            runtime.checkpoint
        )
        if answer is True:
            runtime.side_notes.append("-CheckPoint:User choose to replace IDAT: %s" % info)
            if "OldCrc" in info:
                runtime.checkpoint.dummy_chunk(toolkit[1], toolkit[3], toolkit[3], toolkit[2], toolkit[9])
            else:
                runtime.checkpoint.dummy_chunk(toolkit[1], toolkit[3], toolkit[3], toolkit[2], toolkit[8])
            return False, None

        runtime.side_notes.append("-CheckPoint: %s User chose to quit." % info)
        runtime.checkpoint.end()
        return False, None

    return action_smash_brute_brawl_end_failed_noncustom(
        runtime,
        None,
        None,
        info,
        toolkit,
    )


def action_smash_brute_brawl_end_failed_noncustom(runtime: CheckPointActionRuntime, decision, chunk, info, toolkit):
    runtime.side_notes.append("-CheckPoint: %s" % info)
    return checkpoint_runtime.run_smash_brute_brawl_end_failed_noncustom(
        runtime.checkpoint
    )


def action_smash_brute_brawl_ask_custom_brutus(runtime: CheckPointActionRuntime, decision, chunk, info, toolkit):
    runtime.side_notes.append(
        "\n-Launched Data Chunk Bruteforcer.\n-Bruteforce has Failed!(CUSTOM END)"
    )
    answer = checkpoint_runtime.ask_smash_brute_brawl_custom_brutus(runtime.checkpoint)
    if answer is True:
        runtime.set_brute_level(0)
        smash_brute_brawl_relaunch(runtime, toolkit, toolkit[8], bf_mode="Brutus")
    else:
        runtime.checkpoint.end()
    return False, None


def action_smash_brute_brawl_end_unhandled(runtime: CheckPointActionRuntime, decision, chunk, info, toolkit):
    runtime.side_notes.append("-CheckPoint: %s" % info)
    return checkpoint_runtime.run_smash_brute_brawl_end_unhandled(runtime.checkpoint)


ACTION_HANDLERS = {
    "write_clone": action_write_clone,
    "dummy_chunk_from_the_good_place": action_dummy_chunk_from_the_good_place,
    "return_value": action_return_value,
    "summarise_and_write_clone": action_summarise_and_write_clone,
    "find_fucking_magic": action_find_fucking_magic,
    "check_chunk_name": action_check_chunk_name,
    "save_clone": action_save_clone,
    "save_clone_missing_bytes": action_save_clone_missing_bytes,
    "fix_it_felix_continue": action_fix_it_felix_continue,
    "fix_it_felix_return": action_fix_it_felix_return,
    "libpng_warning_relics": action_libpng_warning_relics,
    "discard_libpng_warning": action_discard_libpng_warning,
    "discard_libpng_warning_and_end": action_discard_libpng_warning,
    "libpng_end_success": action_libpng_end_success,
    "smash_brute_brawl_retry_ihdr_harder": action_smash_brute_brawl_retry_ihdr,
    "smash_brute_brawl_ask_twobytes_retry": action_smash_brute_brawl_ask_twobytes_retry,
    "smash_brute_brawl_end_failed_noncustom": action_smash_brute_brawl_end_failed_noncustom,
    "smash_brute_brawl_ask_custom_brutus": action_smash_brute_brawl_ask_custom_brutus,
    "smash_brute_brawl_end_unhandled": action_smash_brute_brawl_end_unhandled,
}


def apply_action_decision(
    runtime: CheckPointActionRuntime,
    decision,
    chunk,
    info,
    toolkit,
):
    if decision.side_note is not None:
        runtime.side_notes.append(decision.side_note)

    runtime.apply_flags(decision.flags)

    if decision.action is None:
        return False, None

    handler = ACTION_HANDLERS.get(decision.action)
    if handler is not None:
        return handler(runtime, decision, chunk, info, toolkit)

    raise ValueError("Unknown CheckPoint action decision: %s" % decision.action)
