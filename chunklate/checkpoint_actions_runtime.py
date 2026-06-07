from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from . import checkpoint_runtime


LegacyCall = Callable[..., Any]
HEPHAESTUS_MIN_BRUTE_LEVEL = 1
SBB_TWOBYTES_CAMPAIGN_LEVELS = (0, 1)
SBB_HEPHAESTUS_CAMPAIGN_LEVELS = (1, 3, 7, 15)
SBB_HEPHAESTUS_AUTO_LEVEL_MAX = 3


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
    retry_state: dict[str, Any] = field(default_factory=dict)
    clear_smash_resume_files: Callable[[], Any] = lambda: None


def build_checkpoint_action_runtime_from_namespace(namespace: dict[str, Any]) -> CheckPointActionRuntime:
    def clear_smash_resume_files() -> None:
        paths = [
            namespace.get("SMASH_BRUTE_BRAWL_PROGRESS_PATH"),
            namespace.get("SMASH_BRUTE_BRAWL_SOURCE_RAW_PATH"),
            namespace.get("SMASH_BRUTE_BRAWL_SOURCE_PATH"),
        ]
        folder = namespace.get("SMASH_BRUTE_BRAWL_FOLDER")
        if folder:
            paths.extend(
                os.path.join(str(folder), name)
                for name in ("_SBB.progress.json", "_SBB.Source.raw", "_SBB.Source.png")
            )
        for path in paths:
            if not path:
                continue
            try:
                os.remove(path)
            except FileNotFoundError:
                pass
            except OSError:
                pass

    return CheckPointActionRuntime(
        checkpoint=namespace["CheckPoint_Runtime"](),
        side_notes=namespace["SideNotes"],
        apply_flags=namespace["CheckPoint_Apply_Flags"],
        raw_next_chunk=namespace["Raw_NextChunk"],
        get_brute_level=lambda: namespace["Brute_LvL"],
        set_brute_level=lambda value: namespace.__setitem__("Brute_LvL", value),
        eta=namespace["ETA"],
        ihdr_interlace=namespace["IHDR_Interlace"],
        retry_state=namespace.setdefault("_SBB_BLACKFILL_RETRY_STATE", {}),
        clear_smash_resume_files=clear_smash_resume_files,
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
    edit_mode=None,
    bf_mode=None,
    brute_level=None,
    has_old_crc=False,
    old_crc=None,
):
    if "FixItFelix partial IDAT blackfill" in str(from_error):
        runtime.retry_state["disable_resume_once"] = True
    return checkpoint_runtime.run_smash_brute_brawl_relaunch(
        runtime.checkpoint,
        toolkit,
        from_error,
        edit_mode=edit_mode,
        bf_mode=bf_mode,
        brute_level=brute_level,
        has_old_crc=has_old_crc,
        old_crc=old_crc,
    )


def action_smash_brute_brawl_retry_ihdr(runtime: CheckPointActionRuntime, decision, chunk, info, toolkit):
    brute_level = runtime.get_brute_level() + 1
    runtime.set_brute_level(brute_level)
    runtime.side_notes.append("-CheckPoint: %s" % info)
    has_old_crc = "OldCrc" in info
    from_error = toolkit[9] if has_old_crc else toolkit[8]
    old_crc = toolkit[8] if has_old_crc else None
    return checkpoint_runtime.run_smash_brute_brawl_retry_ihdr(
        runtime.checkpoint,
        toolkit,
        from_error,
        brute_level,
        has_old_crc=has_old_crc,
        old_crc=old_crc,
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
                brute_level=brute_level,
                has_old_crc=True,
                old_crc=toolkit[8],
            )
        else:
            smash_brute_brawl_relaunch(
                runtime,
                toolkit,
                toolkit[8],
                brute_level=brute_level,
            )
        return False, None

    return smash_brute_brawl_handle_twobytes_decline(runtime, info, toolkit)


def smash_brute_brawl_handle_twobytes_decline(runtime: CheckPointActionRuntime, info, toolkit):
    from_error = toolkit[9] if "OldCrc" in info and len(toolkit) > 9 else toolkit[8]
    if "FixItFelix partial IDAT blackfill" in str(from_error):
        runtime.side_notes.append("-CheckPoint: Keeping partial IDAT blackfill after SmashBruteBrawl decline.")
        runtime.clear_smash_resume_files()
        return checkpoint_runtime.run_smash_brute_brawl_keep_blackfill_fallback(
            runtime.checkpoint
        )

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


def action_smash_brute_brawl_keep_blackfill_fallback(runtime: CheckPointActionRuntime, decision, chunk, info, toolkit):
    runtime.side_notes.append("-CheckPoint: Keeping partial IDAT blackfill after SmashBruteBrawl failure.")
    runtime.clear_smash_resume_files()
    return checkpoint_runtime.run_smash_brute_brawl_keep_blackfill_fallback(
        runtime.checkpoint
    )


def _smash_old_crc_and_error(info, toolkit) -> tuple[bool, Any, Any]:
    has_old_crc = len(toolkit) > 9
    old_crc = toolkit[8] if has_old_crc else None
    from_error = toolkit[9] if has_old_crc else toolkit[8]
    return has_old_crc, old_crc, from_error


def _hephaestus_order_from_edit_mode(edit_mode: Any) -> tuple[str, str, str]:
    current = str(edit_mode)
    if current == "Insert":
        return ("Insert", "Replace", "Remove")
    if current == "Remove":
        return ("Remove", "Replace", "Insert")
    return ("Replace", "Insert", "Remove")


def _hephaestus_next_edit_mode(edit_mode: Any, order: tuple[str, ...] | None = None) -> str | None:
    current = str(edit_mode)
    selected_order = tuple(order or _hephaestus_order_from_edit_mode(current))
    try:
        index = selected_order.index(current)
    except ValueError:
        return selected_order[0] if selected_order else None
    next_index = index + 1
    if next_index >= len(selected_order):
        return None
    return selected_order[next_index]


def _blackfill_runtime_order(runtime: CheckPointActionRuntime, edit_mode: Any) -> tuple[str, ...]:
    cached = runtime.retry_state.get("hephaestus_order")
    if isinstance(cached, (list, tuple)) and cached:
        return tuple(str(item) for item in cached)
    order = _hephaestus_order_from_edit_mode(edit_mode)
    runtime.retry_state["hephaestus_order"] = order
    return order


def _blackfill_campaign_start_mode(runtime: CheckPointActionRuntime, current_mode: str) -> str:
    start_mode = runtime.retry_state.get("campaign_start_mode")
    if not isinstance(start_mode, str) or not start_mode:
        start_mode = str(current_mode)
        runtime.retry_state["campaign_start_mode"] = start_mode
    return start_mode


def _blackfill_retry_key(toolkit, *, edit_mode: Any, bf_mode: Any, brute_level: int) -> tuple[str, str, int, str, str, str]:
    old_crc = toolkit[8] if len(toolkit) > 8 else ""
    return (
        str(bf_mode),
        str(edit_mode),
        int(brute_level),
        str(toolkit[6]),
        str(toolkit[7]),
        str(old_crc),
    )


def _blackfill_mark_attempt(runtime: CheckPointActionRuntime, toolkit, *, edit_mode: Any, bf_mode: Any, brute_level: int) -> None:
    attempts = runtime.retry_state.setdefault("attempts", set())
    attempts.add(_blackfill_retry_key(toolkit, edit_mode=edit_mode, bf_mode=bf_mode, brute_level=brute_level))


def _blackfill_attempt_seen(runtime: CheckPointActionRuntime, toolkit, *, edit_mode: Any, bf_mode: Any, brute_level: int) -> bool:
    attempts = runtime.retry_state.get("attempts")
    if not isinstance(attempts, set):
        return False
    return _blackfill_retry_key(toolkit, edit_mode=edit_mode, bf_mode=bf_mode, brute_level=brute_level) in attempts


def _blackfill_next_untried_edit(
    runtime: CheckPointActionRuntime,
    toolkit,
    *,
    current_edit: Any,
    order: tuple[str, ...],
    brute_level: int,
) -> str | None:
    next_edit = _hephaestus_next_edit_mode(current_edit, order)
    while next_edit is not None and _blackfill_attempt_seen(
        runtime,
        toolkit,
        edit_mode=next_edit,
        bf_mode="Brutus",
        brute_level=brute_level,
    ):
        next_edit = _hephaestus_next_edit_mode(next_edit, order)
    return next_edit


def _blackfill_campaign_attempts(
    runtime: CheckPointActionRuntime,
    toolkit,
    *,
    current_edit: str,
    current_mode: str,
) -> tuple[tuple[str, str, int], ...]:
    order = _blackfill_runtime_order(runtime, current_edit)
    start_mode = _blackfill_campaign_start_mode(runtime, current_mode)
    attempts: list[tuple[str, str, int]] = []
    if start_mode.lower() != "brutus":
        for level in SBB_TWOBYTES_CAMPAIGN_LEVELS:
            for edit in order:
                attempts.append((edit, "TwoBytes", level))
    for level in SBB_HEPHAESTUS_CAMPAIGN_LEVELS:
        for edit in order:
            attempts.append((edit, "Brutus", level))
    return tuple(attempts)


def _blackfill_attempt_label(edit_mode: str, bf_mode: str, brute_level: int) -> str:
    if str(bf_mode).lower() == "brutus":
        return "HephaestusForge %s level %s" % (edit_mode, brute_level)
    return "%s level %s" % (edit_mode, brute_level)


def _blackfill_next_campaign_attempt(
    runtime: CheckPointActionRuntime,
    toolkit,
    *,
    current_edit: str,
    current_mode: str,
    current_level: int,
) -> tuple[str, str, int] | None:
    current_key = _blackfill_retry_key(
        toolkit,
        edit_mode=current_edit,
        bf_mode=current_mode,
        brute_level=current_level,
    )
    attempts = _blackfill_campaign_attempts(
        runtime,
        toolkit,
        current_edit=current_edit,
        current_mode=current_mode,
    )
    current_is_in_campaign = any(
        _blackfill_retry_key(
            toolkit,
            edit_mode=edit_mode,
            bf_mode=bf_mode,
            brute_level=brute_level,
        )
        == current_key
        for edit_mode, bf_mode, brute_level in attempts
    )
    past_current = not current_is_in_campaign
    for edit_mode, bf_mode, brute_level in attempts:
        if not current_is_in_campaign:
            if str(current_mode).lower() != "brutus" and str(bf_mode).lower() != "brutus" and int(current_level) > max(SBB_TWOBYTES_CAMPAIGN_LEVELS):
                continue
            if (
                str(current_mode).lower() == "brutus"
                and str(bf_mode).lower() == "brutus"
                and int(current_level) >= HEPHAESTUS_MIN_BRUTE_LEVEL
                and int(brute_level) <= int(current_level)
            ):
                continue
        key = _blackfill_retry_key(
            toolkit,
            edit_mode=edit_mode,
            bf_mode=bf_mode,
            brute_level=brute_level,
        )
        if key == current_key:
            past_current = True
            continue
        if not past_current and _blackfill_attempt_seen(
            runtime,
            toolkit,
            edit_mode=edit_mode,
            bf_mode=bf_mode,
            brute_level=brute_level,
        ):
            continue
        if not past_current:
            continue
        if _blackfill_attempt_seen(
            runtime,
            toolkit,
            edit_mode=edit_mode,
            bf_mode=bf_mode,
            brute_level=brute_level,
        ):
            continue
        return edit_mode, bf_mode, brute_level
    return None


def _blackfill_deep_campaign_allowed(
    runtime: CheckPointActionRuntime,
    toolkit,
    *,
    edit_mode: str,
    bf_mode: str,
    brute_level: int,
) -> bool:
    if str(bf_mode).lower() != "brutus" or int(brute_level) <= SBB_HEPHAESTUS_AUTO_LEVEL_MAX:
        return True
    prompted = runtime.retry_state.setdefault("deep_prompted_levels", set())
    prompt_key = (str(bf_mode), str(edit_mode), int(brute_level))
    if prompt_key in prompted:
        return True
    prompted.add(prompt_key)
    runtime.checkpoint.candy(
        "Cowsay",
        "The next HephaestusForge scope is bigger: %s bytes-ish. This can get expensive fast."
        % max(1, int(brute_level) + 1),
        "bad",
    )
    runtime.checkpoint.candy(
        "Cowsay",
        "Should I continue the progressive forge campaign before accepting blackfill?",
        "com",
    )
    try:
        return bool(runtime.checkpoint.question(skipauto=True, timeout_seconds=30, timeout_default=True))
    except TypeError:
        return bool(runtime.checkpoint.question(skipauto=True))


def _blackfill_keep_existing_fallback(runtime: CheckPointActionRuntime) -> tuple[bool, Any]:
    runtime.side_notes.append(
        "-CheckPoint: Keeping partial IDAT blackfill after progressive SmashBruteBrawl campaign."
    )
    runtime.retry_state.clear()
    runtime.clear_smash_resume_files()
    return checkpoint_runtime.run_smash_brute_brawl_keep_blackfill_fallback(
        runtime.checkpoint
    )


def action_smash_brute_brawl_ask_blackfill_next_step(runtime: CheckPointActionRuntime, decision, chunk, info, toolkit):
    has_old_crc, old_crc, from_error = _smash_old_crc_and_error(info, toolkit)
    current_level = runtime.get_brute_level()
    current_edit = str(toolkit[4])
    current_mode = str(toolkit[5])
    _blackfill_mark_attempt(
        runtime,
        toolkit,
        edit_mode=current_edit,
        bf_mode=current_mode,
        brute_level=current_level,
    )
    next_attempt = _blackfill_next_campaign_attempt(
        runtime,
        toolkit,
        current_edit=current_edit,
        current_mode=current_mode,
        current_level=current_level,
    )
    if next_attempt is None:
        runtime.checkpoint.candy(
            "Cowsay",
            "I was afraid of this...",
            "bad",
        )
        return _blackfill_keep_existing_fallback(runtime)

    next_edit, next_mode, next_level = next_attempt
    if not _blackfill_deep_campaign_allowed(
        runtime,
        toolkit,
        edit_mode=next_edit,
        bf_mode=next_mode,
        brute_level=next_level,
    ):
        return _blackfill_keep_existing_fallback(runtime)

    runtime.set_brute_level(next_level)
    runtime.retry_state["disable_resume_once"] = True
    runtime.checkpoint.emit(
        "-SBB pass exhausted: %s; trying %s."
        % (
            _blackfill_attempt_label(current_edit, current_mode, current_level),
            _blackfill_attempt_label(next_edit, next_mode, next_level),
        )
    )
    runtime.checkpoint.emit(
        "-SBB campaign keeps the blackfill fallback parked while this pass runs."
    )
    runtime.side_notes.append(
        "-CheckPoint: Progressive SBB campaign trying %s."
        % _blackfill_attempt_label(next_edit, next_mode, next_level)
    )
    smash_brute_brawl_relaunch(
        runtime,
        toolkit,
        from_error,
        edit_mode=next_edit,
        bf_mode=next_mode,
        brute_level=next_level,
        has_old_crc=has_old_crc,
        old_crc=old_crc,
    )
    return False, None


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
    "smash_brute_brawl_keep_blackfill_fallback": action_smash_brute_brawl_keep_blackfill_fallback,
    "smash_brute_brawl_ask_blackfill_next_step": action_smash_brute_brawl_ask_blackfill_next_step,
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
