from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from . import checkpoint_runtime


LegacyCall = Callable[..., Any]
HEPHAESTUS_MIN_BRUTE_LEVEL = 1
SBB_TWOBYTES_CAMPAIGN_LEVELS = (0, 1, 2)
SBB_HEPHAESTUS_CAMPAIGN_LEVELS = (1, 2, 3, 4, 7, 15)
SBB_HEPHAESTUS_AUTO_LEVEL_MAX = 3
SBB_LONG_PASS_SECONDS = 60 * 60
SBB_LONG_PASS_PHRASES = (
    "My calculator just put on a tiny helmet. This pass is not a coffee break.",
    "This scope has entered calendar territory.",
    "I can keep forging, but this loop is starting to look like a lease agreement.",
    "The checksum is not scared yet. It should be.",
)


def _hermes_window_bytes_for_level(brute_level: int) -> int:
    level = max(0, int(brute_level))
    if level == 0:
        return 1
    if level == 1:
        return 2
    if level == 2:
        return 4
    return 2 ** level


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
    progress_path: str = ""


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
        progress_path=namespace.get("SMASH_BRUTE_BRAWL_PROGRESS_PATH", ""),
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
        runtime.retry_state["active_pass"] = {
            "edit_mode": str(edit_mode if edit_mode is not None else toolkit[4]),
            "bf_mode": str(bf_mode if bf_mode is not None else toolkit[5]),
            "brute_level": int(brute_level if brute_level is not None else runtime.get_brute_level()),
        }
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


def _blackfill_campaign_focus(runtime: CheckPointActionRuntime, edit_mode: Any) -> str:
    focus = str(runtime.retry_state.get("campaign_focus") or "").strip().lower()
    if focus in {"insert", "remove", "replace", "progressive"}:
        return focus
    # If the user did not explicitly choose a focus, keep the historical
    # progressive behavior. The focus prompt writes insert/remove/replace when
    # the user chooses one.
    focus = "progressive"
    runtime.retry_state["campaign_focus"] = focus
    return focus


def _blackfill_campaign_start_mode(runtime: CheckPointActionRuntime, current_mode: str) -> str:
    start_mode = runtime.retry_state.get("campaign_start_mode")
    if not isinstance(start_mode, str) or not start_mode:
        start_mode = str(current_mode)
        runtime.retry_state["campaign_start_mode"] = start_mode
    return start_mode


def _blackfill_retry_key(
    runtime: CheckPointActionRuntime,
    toolkit,
    *,
    edit_mode: Any,
    bf_mode: Any,
    brute_level: int,
) -> tuple[str, str, int, str, str, str, str]:
    old_crc = toolkit[8] if len(toolkit) > 8 else ""
    return (
        str(bf_mode),
        str(edit_mode),
        int(brute_level),
        _blackfill_campaign_focus(runtime, edit_mode),
        str(toolkit[6]),
        str(toolkit[7]),
        str(old_crc),
    )

def _blackfill_attempt_record_from_key(
    key: tuple[str, str, int, str, str, str, str],
    *,
    status: str,
    tested_candidates: int,
    elapsed_seconds: int,
) -> dict[str, Any]:
    bf_mode, edit_mode, brute_level, focus, brute_crc, brute_length, old_crc = key
    return {
        "bf_mode": bf_mode,
        "edit_mode": edit_mode,
        "brute_level": int(brute_level),
        "focus": focus,
        "brute_crc": brute_crc,
        "brute_length": brute_length,
        "old_crc": old_crc,
        "status": status or "unknown",
        "tested_candidates": max(0, int(tested_candidates)),
        "elapsed_seconds": max(0, int(elapsed_seconds)),
    }


def _blackfill_store_attempt_record(
    runtime: CheckPointActionRuntime,
    key: tuple[str, str, int, str, str, str, str],
    *,
    status: str,
    tested_candidates: int,
    elapsed_seconds: int,
) -> None:
    records = runtime.retry_state.setdefault("attempt_records", [])
    if not isinstance(records, list):
        records = []
        runtime.retry_state["attempt_records"] = records
    record = _blackfill_attempt_record_from_key(
        key,
        status=status,
        tested_candidates=tested_candidates,
        elapsed_seconds=elapsed_seconds,
    )
    comparable = ("bf_mode", "edit_mode", "brute_level", "focus", "brute_crc", "brute_length", "old_crc")
    for index, existing in enumerate(records):
        if not isinstance(existing, dict):
            continue
        if all(existing.get(field) == record.get(field) for field in comparable):
            records[index] = record
            return
    records.append(record)


def _blackfill_mark_attempt(
    runtime: CheckPointActionRuntime,
    toolkit,
    *,
    edit_mode: Any,
    bf_mode: Any,
    brute_level: int,
    status: str = "",
    tested_candidates: int = 0,
    elapsed_seconds: int = 0,
) -> None:
    attempts = runtime.retry_state.setdefault("attempts", set())
    key = _blackfill_retry_key(
        runtime,
        toolkit,
        edit_mode=edit_mode,
        bf_mode=bf_mode,
        brute_level=brute_level,
    )
    attempts.add(key)
    _blackfill_store_attempt_record(
        runtime,
        key,
        status=status,
        tested_candidates=tested_candidates,
        elapsed_seconds=elapsed_seconds,
    )


def _blackfill_attempt_seen(runtime: CheckPointActionRuntime, toolkit, *, edit_mode: Any, bf_mode: Any, brute_level: int) -> bool:
    attempts = runtime.retry_state.get("attempts")
    if not isinstance(attempts, set):
        return False
    return (
        _blackfill_retry_key(
            runtime,
            toolkit,
            edit_mode=edit_mode,
            bf_mode=bf_mode,
            brute_level=brute_level,
        )
        in attempts
    )


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
    focus = _blackfill_campaign_focus(runtime, current_edit)
    attempts: list[tuple[str, str, int]] = []
    if focus == "progressive":
        if start_mode.lower() != "brutus":
            for level in SBB_TWOBYTES_CAMPAIGN_LEVELS:
                for edit in order:
                    attempts.append((edit, "TwoBytes", level))
        for level in SBB_HEPHAESTUS_CAMPAIGN_LEVELS:
            for edit in order:
                attempts.append((edit, "Brutus", level))
        return tuple(attempts)

    # A focused campaign really focuses: exhaust the requested edit family over
    # the useful scopes first, then keep the other families available afterward.
    for edit in order:
        if start_mode.lower() != "brutus":
            for level in SBB_TWOBYTES_CAMPAIGN_LEVELS:
                attempts.append((edit, "TwoBytes", level))
        for level in SBB_HEPHAESTUS_CAMPAIGN_LEVELS:
            attempts.append((edit, "Brutus", level))
    return tuple(attempts)


def _blackfill_attempt_label(edit_mode: str, bf_mode: str, brute_level: int) -> str:
    if str(bf_mode).lower() == "brutus":
        return "HephaestusForge %s level %s" % (edit_mode, brute_level)
    if str(bf_mode).lower() == "twobytes":
        return "HermesProbe %s %s-byte window" % (
            edit_mode,
            _hermes_window_bytes_for_level(brute_level),
        )
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
        runtime,
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
            runtime,
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
            runtime,
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
    return True


def _blackfill_recent_pass_stats(runtime: CheckPointActionRuntime) -> tuple[int, int]:
    if not runtime.progress_path:
        return 0, 0
    try:
        with open(runtime.progress_path, "r", encoding="utf-8") as handle:
            record = json.load(handle)
    except (OSError, ValueError, TypeError):
        return 0, 0
    counters = record.get("counters")
    if not isinstance(counters, dict):
        return 0, 0
    try:
        tested = int(counters.get("tested_candidates") or 0)
    except (TypeError, ValueError):
        tested = 0
    try:
        elapsed = int(counters.get("elapsed_seconds") or 0)
    except (TypeError, ValueError):
        elapsed = 0
    if elapsed <= 0:
        elapsed = int(runtime.eta or 0)
    return max(0, tested), max(0, elapsed)


def _blackfill_recent_pass_record(runtime: CheckPointActionRuntime) -> tuple[str, int, int]:
    return (
        _blackfill_recent_pass_status(runtime),
        *_blackfill_recent_pass_stats(runtime),
    )


def _blackfill_recent_pass_status(runtime: CheckPointActionRuntime) -> str:
    if not runtime.progress_path:
        return ""
    try:
        with open(runtime.progress_path, "r", encoding="utf-8") as handle:
            record = json.load(handle)
    except (OSError, ValueError, TypeError):
        return ""
    if not isinstance(record, dict):
        return ""
    return str(record.get("status") or "")


def _blackfill_recent_invocation_level(
    runtime: CheckPointActionRuntime,
    *,
    edit_mode: str,
    bf_mode: str,
) -> int | None:
    if not runtime.progress_path:
        return None
    try:
        with open(runtime.progress_path, "r", encoding="utf-8") as handle:
            record = json.load(handle)
    except (OSError, ValueError, TypeError):
        return None
    if not isinstance(record, dict):
        return None
    invocation = record.get("invocation")
    if not isinstance(invocation, dict):
        return None
    if str(invocation.get("edit_mode") or "") != str(edit_mode):
        return None
    if str(invocation.get("bf_mode") or "") != str(bf_mode):
        return None
    try:
        return int(invocation.get("brute_level"))
    except (TypeError, ValueError):
        return None


def _blackfill_active_pass_level(
    runtime: CheckPointActionRuntime,
    *,
    edit_mode: str,
    bf_mode: str,
) -> int | None:
    active_pass = runtime.retry_state.get("active_pass")
    if not isinstance(active_pass, dict):
        return None
    if str(active_pass.get("edit_mode") or "") != str(edit_mode):
        return None
    if str(active_pass.get("bf_mode") or "") != str(bf_mode):
        return None
    try:
        return int(active_pass.get("brute_level"))
    except (TypeError, ValueError):
        return None


def _blackfill_current_pass_level(
    runtime: CheckPointActionRuntime,
    toolkit,
    *,
    edit_mode: str,
    bf_mode: str,
) -> int:
    active_level = _blackfill_active_pass_level(
        runtime,
        edit_mode=edit_mode,
        bf_mode=bf_mode,
    )
    if active_level is not None:
        return active_level
    progress_level = _blackfill_recent_invocation_level(
        runtime,
        edit_mode=edit_mode,
        bf_mode=bf_mode,
    )
    if progress_level is not None:
        return progress_level
    level = int(runtime.get_brute_level())
    from_error = toolkit[9] if len(toolkit) > 9 else toolkit[8] if len(toolkit) > 8 else ""
    if (
        str(bf_mode).lower() == "brutus"
        and str(edit_mode) in {"Insert", "Remove", "Replace"}
        and level < HEPHAESTUS_MIN_BRUTE_LEVEL
        and "FixItFelix partial IDAT blackfill" in str(from_error)
    ):
        return HEPHAESTUS_MIN_BRUTE_LEVEL
    return level


def _blackfill_pass_transition_text(status: str) -> str:
    if status == "rejected_hit":
        return "SBB pass rejected invalid candidates"
    if status == "success":
        return "SBB pass already produced a validated hit"
    return "SBB pass exhausted"


def _blackfill_brutus_byte_lengths(brute_level: int) -> tuple[int, ...]:
    level = max(0, int(brute_level))
    return tuple(range(1, level + 2))


def _blackfill_estimated_brutus_candidates(
    *,
    edit_mode: str,
    brute_level: int,
    chunk_length: int,
) -> int:
    lengths = _blackfill_brutus_byte_lengths(brute_level)
    if str(edit_mode) == "Remove":
        payload_bytes = max(1, int(chunk_length))
        return sum(
            max(0, payload_bytes - candidate_bytes + 1)
            for candidate_bytes in lengths
        )
    return sum(256 ** candidate_bytes for candidate_bytes in lengths)


def _blackfill_estimated_next_candidates(
    runtime: CheckPointActionRuntime,
    toolkit,
    *,
    edit_mode: str,
    bf_mode: str,
    brute_level: int,
    current_level: int | None = None,
    previous_tested: int,
) -> int:
    if previous_tested <= 0:
        return 0
    try:
        chunk_length = max(1, int(toolkit[2]))
    except (TypeError, ValueError):
        chunk_length = 1
    if str(bf_mode).lower() != "brutus":
        candidate_bytes = _hermes_window_bytes_for_level(brute_level)
        positions = max(0, int(chunk_length) - int(candidate_bytes) + 1)
        if str(edit_mode) == "Remove":
            return positions
        return positions * (256 ** int(candidate_bytes))
    if str(bf_mode).lower() == "brutus":
        return _blackfill_estimated_brutus_candidates(
            edit_mode=edit_mode,
            brute_level=brute_level,
            chunk_length=chunk_length,
        )
    return previous_tested


def _blackfill_long_eta_phrase(runtime: CheckPointActionRuntime) -> str:
    index = int(runtime.retry_state.get("long_eta_phrase_index", 0) or 0)
    runtime.retry_state["long_eta_phrase_index"] = index + 1
    return SBB_LONG_PASS_PHRASES[index % len(SBB_LONG_PASS_PHRASES)]


def _format_sbb_eta(seconds: int | float) -> str:
    try:
        total_seconds = int(seconds)
    except (TypeError, ValueError, OverflowError):
        return "unknown"
    if total_seconds < 0:
        return "unknown"
    days, remainder = divmod(total_seconds, 24 * 60 * 60)
    hours, remainder = divmod(remainder, 60 * 60)
    minutes, secs = divmod(remainder, 60)
    if days:
        return "%s days, %s:%02d:%02d" % (f"{days:,}", hours, minutes, secs)
    return "%s:%02d:%02d" % (hours, minutes, secs)


def _blackfill_timed_campaign_allowed(
    runtime: CheckPointActionRuntime,
    toolkit,
    *,
    edit_mode: str,
    bf_mode: str,
    brute_level: int,
    current_level: int | None = None,
) -> bool:
    previous_tested, previous_elapsed = _blackfill_recent_pass_stats(runtime)
    if previous_tested <= 0:
        return True
    previous_elapsed = max(1, int(previous_elapsed))
    estimated_candidates = _blackfill_estimated_next_candidates(
        runtime,
        toolkit,
        edit_mode=edit_mode,
        bf_mode=bf_mode,
        brute_level=brute_level,
        current_level=current_level,
        previous_tested=previous_tested,
    )
    if estimated_candidates <= 0:
        return True
    candidates_per_second = previous_tested / max(1, previous_elapsed)
    estimated_seconds = int(estimated_candidates / max(0.001, candidates_per_second))
    if estimated_seconds < SBB_LONG_PASS_SECONDS:
        return True
    prompt_key = (
        "eta",
        str(bf_mode),
        str(edit_mode),
        int(brute_level),
        int(estimated_candidates),
    )
    prompted = runtime.retry_state.setdefault("eta_prompted_passes", set())
    if prompt_key in prompted:
        return True
    prompted.add(prompt_key)
    runtime.checkpoint.candy("Cowsay", _blackfill_long_eta_phrase(runtime), "bad")
    runtime.checkpoint.emit(
        "-SBB estimated next pass: %s candidates at about %.1f candidates/s -> %s."
        % (
            f"{estimated_candidates:,}",
            candidates_per_second,
            _format_sbb_eta(estimated_seconds),
        )
    )
    runtime.checkpoint.candy(
        "Cowsay",
        "Should I continue this SBB pass before accepting the blackfill fallback?",
        "com",
    )
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
    current_edit = str(toolkit[4])
    current_mode = str(toolkit[5])
    current_level = _blackfill_current_pass_level(
        runtime,
        toolkit,
        edit_mode=current_edit,
        bf_mode=current_mode,
    )
    recent_status, recent_tested, recent_elapsed = _blackfill_recent_pass_record(runtime)
    _blackfill_mark_attempt(
        runtime,
        toolkit,
        edit_mode=current_edit,
        bf_mode=current_mode,
        brute_level=current_level,
        status=recent_status,
        tested_candidates=recent_tested,
        elapsed_seconds=recent_elapsed,
    )
    if recent_status == "success":
        runtime.side_notes.append(
            "-CheckPoint: SBB pass already produced a validated hit; no further campaign pass launched."
        )
        runtime.retry_state.clear()
        return False, None
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
    if not _blackfill_timed_campaign_allowed(
        runtime,
        toolkit,
        edit_mode=next_edit,
        bf_mode=next_mode,
        brute_level=next_level,
        current_level=current_level,
    ):
        return _blackfill_keep_existing_fallback(runtime)

    runtime.set_brute_level(next_level)
    runtime.retry_state["disable_resume_once"] = True
    runtime.checkpoint.emit(
        "-%s: %s; trying %s."
        % (
            _blackfill_pass_transition_text(_blackfill_recent_pass_status(runtime)),
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
