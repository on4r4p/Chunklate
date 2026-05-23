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


def apply_plte_repair_decision(
    runtime: RelicsRuntime,
    decision: Any,
    *,
    add_side_note: Callable[[Any], Any],
    the_end: Callable[[], Any],
) -> tuple[bool, Any]:
    if decision.action == "manual":
        return True, run_plte_manual_plan(runtime, decision.plan)

    if decision.action == "remove":
        return True, run_plte_remove_plan(runtime, decision.plan)

    if decision.action == "brawl":
        return True, run_plte_brawl_plan(runtime, decision.plan)

    if decision.action == "quit":
        if decision.side_note is not None:
            add_side_note(decision.side_note)
        the_end()

    return False, None


def handle_plte_repair_flow(
    runtime: RelicsRuntime,
    relics_module: Any,
    ui_module: Any,
    *,
    has_bad_crc: bool,
    chunks_history: Any,
    chunks_history_index: Any,
    target_file: Any,
    old_crc: Any = None,
    ask_fallback: Callable[[], Any],
    add_side_note: Callable[[Any], Any],
    the_end: Callable[[], Any],
    candy: LegacyCall,
) -> tuple[bool, Any]:
    ui_module.say_plte_intro(candy=candy)

    if not has_bad_crc:
        ui_module.say_plte_valid_crc(candy=candy)
        answer = ask_plte_repair(runtime, relics_module, False)
        window = relics_module.plte_chunk_window(chunks_history, chunks_history_index)
        should_return, result = apply_plte_repair_decision(
            runtime,
            relics_module.plte_repair_decision(
                answer,
                window,
                target_file=target_file,
                quit_note="-User chose to quit.",
            ),
            add_side_note=add_side_note,
            the_end=the_end,
        )
        if should_return:
            return True, result

    else:
        ui_module.say_plte_bad_crc(candy=candy)
        answer = ask_plte_repair(runtime, relics_module, True)
        window = relics_module.plte_chunk_window(chunks_history, chunks_history_index)
        should_return, result = apply_plte_repair_decision(
            runtime,
            relics_module.plte_repair_decision(
                answer,
                window,
                target_file=target_file,
                old_crc=old_crc,
                quit_note="-User chose to quit.",
            ),
            add_side_note=add_side_note,
            the_end=the_end,
        )
        if should_return:
            return True, result

    ui_module.say_plte_fallback(candy=candy)
    answer = ask_fallback()
    if answer is True:
        window = relics_module.plte_chunk_window(chunks_history, chunks_history_index)
        should_return, result = apply_plte_repair_decision(
            runtime,
            relics_module.plte_repair_decision(
                "bruteforce",
                window,
                target_file=target_file,
            ),
            add_side_note=add_side_note,
            the_end=the_end,
        )
        if should_return:
            return True, result
    else:
        the_end()

    return False, None


def apply_dummy_chunk_repair_decision(
    runtime: RelicsRuntime,
    decision: Any,
    *,
    show_todo: Callable[[], Any],
    the_end: Callable[[], Any],
) -> Any:
    if decision.action == "brawl":
        return run_dummy_chunk_brawl_plan(runtime, decision.plan)

    if decision.action == "todo_end":
        show_todo()
        the_end()

    if decision.action == "end":
        the_end()

    raise ValueError("Unknown dummy chunk relic decision: %s" % decision.action)


def handle_remembered_dummy_chunk_flow(
    runtime: RelicsRuntime,
    relics_module: Any,
    ui_module: Any,
    request: Any,
    *,
    from_error: Any,
    ask: Callable[[], Any],
    show_todo: Callable[[], Any],
    the_end: Callable[[], Any],
    candy: LegacyCall,
) -> Any:
    if request is None:
        the_end()
        return ()

    route = request.route
    tools = request.tools
    chunk_name = route.chunk_name

    if route.is_critical:
        ui_module.say_dummy_chunk_critical_prompt(chunk_name, candy=candy)
    else:
        ui_module.say_dummy_chunk_ancillary_prompt(chunk_name, candy=candy)

    return apply_dummy_chunk_repair_decision(
        runtime,
        relics_module.dummy_chunk_repair_decision(
            route,
            tools,
            from_error=from_error,
            answer=ask(),
        ),
        show_todo=show_todo,
        the_end=the_end,
    )


def apply_no_pandemonium_repair_decision(
    runtime: RelicsRuntime,
    decision: Any,
) -> tuple[bool, Any]:
    if decision.action == "getinfo_brawl":
        return True, run_getinfo_brawl_plan(runtime, decision.plan)

    if decision.action == "full_chunk_forcer":
        return True, run_full_chunk_forcer_plan(runtime, decision.plan)

    if decision.action in ("none", "unsupported"):
        return False, None

    raise ValueError(
        "Unknown no-Pandemonium relic decision: %s" % decision.action
    )


def handle_no_pandemonium_flow(
    runtime: RelicsRuntime,
    relics_module: Any,
    ui_module: Any,
    *,
    policy: Any = None,
    prompt_context: Any = None,
    chunks_history: Any,
    chunks_history_index: Any,
    target_file: Any,
    from_error: Any,
    chunks_len_not_fixed: Any,
    skip_bad_crc: bool,
    ask: Callable[[], Any],
    emit: Callable[[str], Any],
    candy: LegacyCall,
    the_end: Callable[[], Any],
) -> Any:
    ui_module.say_no_pandemonium_intro(emit=emit, candy=candy)

    if policy is not None and prompt_context is not None:
        if prompt_context.action == "getinfo_brawl":
            ui_module.emit_prompt_context_hits(prompt_context, emit=emit)
            ui_module.say_no_pandemonium_getinfo(
                skip_bad_crc=skip_bad_crc,
                candy=candy,
            )
            should_return, result = apply_no_pandemonium_repair_decision(
                runtime,
                relics_module.no_pandemonium_repair_decision(
                    policy,
                    chunks_history,
                    chunks_history_index,
                    target_file=target_file,
                    from_error=from_error,
                    chunks_len_not_fixed=chunks_len_not_fixed,
                    answer=ask(),
                ),
            )
            if should_return:
                return result

        elif prompt_context.action == "full_chunk_forcer":
            ui_module.emit_prompt_context_hits(prompt_context, emit=emit)
            ui_module.say_no_pandemonium_forcer(candy=candy)

            should_return, result = apply_no_pandemonium_repair_decision(
                runtime,
                relics_module.no_pandemonium_repair_decision(
                    policy,
                    chunks_history,
                    chunks_history_index,
                    target_file=target_file,
                    from_error=from_error,
                    chunks_len_not_fixed=chunks_len_not_fixed,
                    answer=ask(),
                ),
            )
            if should_return:
                return result

    ui_module.say_no_pandemonium_failure(candy=candy)
    the_end()


def ask_plte_repair(runtime: RelicsRuntime, relics_module: Any, has_bad_crc: bool) -> Any:
    return runtime.ask_choice(
        relics_module.plte_repair_prompt(has_bad_crc),
        relics_module.plte_repair_choices(has_bad_crc),
        relics_module.plte_repair_retry_prompt(has_bad_crc),
    )
