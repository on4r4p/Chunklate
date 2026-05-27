from __future__ import annotations

import builtins
from collections.abc import Callable
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from . import decisions
from . import idat
from . import runtime_state
from . import writer


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


def build_relics_runtime(
    *,
    save_clone: LegacyCall,
    smash_brute_brawl: LegacyCall,
    full_chunk_forcer_no_crc: LegacyCall,
    tk_manual_plte: LegacyCall,
    remove_chunk: LegacyCall,
    ask_choice: AskChoice,
) -> RelicsRuntime:
    return RelicsRuntime(
        save_clone=save_clone,
        smash_brute_brawl=smash_brute_brawl,
        full_chunk_forcer_no_crc=full_chunk_forcer_no_crc,
        tk_manual_plte=tk_manual_plte,
        remove_chunk=remove_chunk,
        ask_choice=ask_choice,
    )


def build_relics_runtime_from_namespace(namespace: dict[str, Any]) -> RelicsRuntime:
    return build_relics_runtime(
        save_clone=namespace["SaveClone"],
        smash_brute_brawl=namespace["SmashBruteBrawl"],
        full_chunk_forcer_no_crc=namespace["FullChunkForcerNoCrc"],
        tk_manual_plte=namespace["Tk_Manual_Plte"],
        remove_chunk=namespace["RemoveChunk"],
        ask_choice=lambda prompt, choices, retry_prompt: decisions.ask_choice(
            builtins.input,
            prompt,
            choices,
            retry_prompt,
        ),
    )


def build_relics_context_from_namespace(namespace: dict[str, Any], from_error: Any) -> runtime_state.RelicsRuntimeContext:
    return runtime_state.relics_runtime_context(
        from_error=from_error,
        pandemonium=namespace["Pandemonium"],
        pandora_box=namespace["PandoraBox"],
        cornucopia=namespace["Cornucopia"],
        side_notes=namespace["SideNotes"],
        all_chunks=namespace["ALLCHUNKS"],
        critical_chunks=namespace["CRITICAL_CHUNKS"],
        chunks_history=namespace["Chunks_History"],
        chunks_history_index=namespace["Chunks_History_Index"],
        file_origin=namespace["FILE_Origin"],
        sample=namespace["Sample"],
        sample_name=namespace["Sample_Name"],
        data_hex=namespace["DATAX"],
        crc_offset=namespace["CrcoffI"],
        bad_crc=namespace["Bad_Crc"],
        skip_bad_current_name=namespace["Skip_Bad_Current_Name"],
        skip_bad_infos=namespace["Skip_Bad_Infos"],
        skip_bad_critical=namespace["Skip_Bad_Critical"],
        skip_bad_crc=namespace["Skip_Bad_Crc"],
        chunks_len_not_fixed=namespace["CHUNKS_LEN_NOT_FIXED"],
        debug=namespace["DEBUG"],
        pause_debug=namespace["PAUSEDEBUG"],
        pause_error=namespace["PAUSEERROR"],
    )


def run_save_clone_plan(runtime: RelicsRuntime, save_plan: Any) -> Any:
    return runtime.save_clone(
        save_plan.fixed_data,
        save_plan.start,
        save_plan.end,
        save_plan.info,
    )


def idat_crc_only_patch_keeps_stream_invalid(data_hex: str, tools: Any) -> tuple[bool, str]:
    if not data_hex:
        return False, ""

    try:
        patched_hex = writer.replace_hex_range(
            data_hex,
            str(tools.replacement_crc),
            int(tools.start),
            int(tools.end),
        )
        analysis = idat.analyze_idat_stream(bytes.fromhex(patched_hex))
    except Exception as exc:
        return True, "I could not even build the CRC-only candidate: %s" % exc

    if analysis.complete:
        return False, ""

    reason = analysis.reason or analysis.zlib_error or analysis.status or "IDAT stream is still not a complete image"
    details = (
        "%s; chunks=%s; compressed=%s; decompressed=%s; expected=%s; scanlines=%s/%s"
        % (
            reason,
            analysis.idat_chunk_count,
            analysis.compressed_size,
            analysis.decompressed_size,
            analysis.expected_size,
            analysis.usable_scanlines,
            analysis.height,
        )
    )
    return True, details


def remember_deferred_relics_idat_crc(side_notes: Any, reason: str) -> None:
    if side_notes is None:
        return
    side_notes.append("-Deferred IDAT CRC-only patch from Relics: zlib stream still invalid: %s." % reason)


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


def handle_current_wrong_crc_flow(
    runtime: RelicsRuntime,
    relics_module: Any,
    ui_module: Any,
    contexts: Any,
    *,
    data_hex: str = "",
    side_notes: Any = None,
    ask: LegacyCall,
    emit: Callable[[str], Any],
    candy: LegacyCall,
) -> tuple[bool, Any]:
    for context in contexts:
        route = context.route
        ui_module.emit_critical_hit(route.error, emit=emit)
        if route.chunk_name == "IDAT":
            stream_invalid, reason = idat_crc_only_patch_keeps_stream_invalid(data_hex, context.tools)
            if stream_invalid:
                candy(
                    "Cowsay",
                    "I checked that old CRC-only idea again. It still only makes the label prettier.",
                    "bad",
                )
                candy(
                    "Cowsay",
                    "The IDAT stream is still broken, so I am not writing another clone for the same lie.",
                    "com",
                )
                remember_deferred_relics_idat_crc(side_notes, reason)
                continue

            ui_module.say_current_wrong_crc_idat(candy=candy)
            answer = ask(id=route.error, idhash=context.question_hash)
            if answer is True:
                return True, run_save_clone_plan(
                    runtime,
                    relics_module.wrong_crc_save_clone_plan(context.tools),
                )

    return False, None


def handle_remembered_idat_wrong_crc_flow(
    runtime: RelicsRuntime,
    ui_module: Any,
    requests: Any,
    *,
    candy: LegacyCall,
) -> None:
    for request in requests:
        ui_module.say_wrong_crc_data_brawl(request.route.chunk_name, candy=candy)
        run_wrong_crc_brawl_plan(runtime, request.plan)


def handle_single_pandemonium_flow(
    runtime: RelicsRuntime,
    ui_module: Any,
    decisions: Any,
    *,
    debug: bool,
    pause_debug: bool,
    pause_error: bool,
    pause: LegacyCall,
    the_end: Callable[[], Any],
    candy: LegacyCall,
) -> Any:
    ui_module.say_single_pandemonium_intro(candy=candy)

    for decision in decisions:
        if decision.action == "wrong_crc_brawl":
            ui_module.say_wrong_crc_data_brawl(decision.route.chunk_name, candy=candy)
            run_wrong_crc_brawl_plan(runtime, decision.plan)
            return ()

        if debug is True:
            if pause_debug is True or pause_error is True:
                pause("Pause Pandemonium Debug")
        ui_module.say_single_pandemonium_unsupported(candy=candy)
        the_end()

    return ()


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


def handle_pandemonium_flow(
    runtime: RelicsRuntime,
    relics_module: Any,
    ui_module: Any,
    context: Any,
    *,
    ask: Callable[..., Any],
    emit: Callable[[str], Any],
    pause: LegacyCall,
    show_todo: Callable[[], Any],
    the_end: Callable[[], Any],
    candy: LegacyCall,
) -> tuple[bool, Any]:
    if len(context.pandemonium) < 1:
        return False, None

    ui_module.emit_pandemonium_summary(
        relics_module.pandemonium_summary(context.pandemonium),
        emit=emit,
        candy=candy,
    )

    for policy_step in relics_module.pandemonium_policy_steps(len(context.pandemonium)):
        if policy_step.action == "current_wrong_crc":
            should_return, result = handle_current_wrong_crc_flow(
                runtime,
                relics_module,
                ui_module,
                relics_module.current_wrong_crc_prompt_contexts(
                    context.pandora_box,
                    context.cornucopia,
                    context.all_chunks,
                ),
                data_hex=getattr(context, "data_hex", ""),
                side_notes=getattr(context, "side_notes", None),
                ask=ask,
                emit=emit,
                candy=candy,
            )
            if should_return:
                return True, result

        elif policy_step.action == "remembered_idat_wrong_crc":
            handle_remembered_idat_wrong_crc_flow(
                runtime,
                ui_module,
                relics_module.remembered_idat_wrong_crc_brawl_requests(
                    context.pandemonium,
                    context.all_chunks,
                    target_file=context.file_origin,
                    from_error=context.from_error,
                ),
                candy=candy,
            )

        elif policy_step.action == "plte":
            plte_finding = relics_module.first_current_plte_repair_finding(
                context.pandora_box,
                context.cornucopia,
                skip_bad_current_name=context.skip_bad_current_name,
                skip_bad_infos=context.skip_bad_infos,
                skip_bad_critical=context.skip_bad_critical,
            )
            if plte_finding is not None:
                should_return, result = handle_plte_repair_flow(
                    runtime,
                    relics_module,
                    ui_module,
                    has_bad_crc=context.bad_crc,
                    chunks_history=context.chunks_history,
                    chunks_history_index=context.chunks_history_index,
                    target_file=context.sample_name,
                    old_crc=context.old_crc,
                    ask_fallback=ask,
                    add_side_note=context.side_notes.append,
                    the_end=the_end,
                    candy=candy,
                )
                if should_return:
                    return True, result

        elif policy_step.action == "single_pandemonium":
            return True, handle_single_pandemonium_flow(
                runtime,
                ui_module,
                relics_module.single_pandemonium_decisions(
                    context.pandemonium,
                    known_chunks=context.all_chunks,
                    file_origin=context.file_origin,
                    current_sample=context.sample,
                    from_error=context.from_error,
                ),
                debug=context.debug,
                pause_debug=context.pause_debug,
                pause_error=context.pause_error,
                pause=pause,
                the_end=the_end,
                candy=candy,
            )

        elif policy_step.action == "remembered_dummy_chunks":
            return True, handle_remembered_dummy_chunk_flow(
                runtime,
                relics_module,
                ui_module,
                relics_module.first_remembered_dummy_chunk_repair_request(
                    context.pandemonium,
                    context.all_chunks,
                    context.critical_chunks,
                ),
                from_error=context.from_error,
                ask=ask,
                show_todo=show_todo,
                the_end=the_end,
                candy=candy,
            )

    return True, None


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


def handle_no_pandemonium_context_flow(
    runtime: RelicsRuntime,
    relics_module: Any,
    ui_module: Any,
    context: Any,
    *,
    ask: Callable[[], Any],
    emit: Callable[[str], Any],
    candy: LegacyCall,
    the_end: Callable[[], Any],
) -> Any:
    policy = None
    prompt_context = None
    if len(context.pandora_box) > 0:
        policy = relics_module.no_pandemonium_policy(
            context.pandora_box,
            context.critical_chunks,
            context.all_chunks,
        )
        prompt_context = relics_module.no_pandemonium_prompt_context(
            policy,
            context.pandora_box,
        )

    return handle_no_pandemonium_flow(
        runtime,
        relics_module,
        ui_module,
        policy=policy,
        prompt_context=prompt_context,
        chunks_history=context.chunks_history,
        chunks_history_index=context.chunks_history_index,
        target_file=context.sample_name,
        from_error=context.from_error,
        chunks_len_not_fixed=context.chunks_len_not_fixed,
        skip_bad_crc=context.skip_bad_crc,
        ask=ask,
        emit=emit,
        candy=candy,
        the_end=the_end,
    )


def handle_relics_context_flow(
    runtime: RelicsRuntime,
    relics_module: Any,
    ui_module: Any,
    context: Any,
    *,
    ask: Callable[..., Any],
    emit: Callable[[str], Any],
    pause: LegacyCall,
    show_todo: Callable[[], Any],
    the_end: Callable[[], Any],
    candy: LegacyCall,
) -> Any:
    ui_module.emit_debug_state(
        debug=context.debug,
        pandemonium=context.pandemonium,
        pandora_box=context.pandora_box,
        chunks_history=context.chunks_history,
        chunks_history_index=context.chunks_history_index,
        pause_debug=context.pause_debug,
        emit=emit,
        pause=pause,
    )

    handled, result = handle_pandemonium_flow(
        runtime,
        relics_module,
        ui_module,
        context,
        ask=ask,
        emit=emit,
        pause=pause,
        show_todo=show_todo,
        the_end=the_end,
        candy=candy,
    )
    if handled:
        return result

    return handle_no_pandemonium_context_flow(
        runtime,
        relics_module,
        ui_module,
        context,
        ask=ask,
        emit=emit,
        candy=candy,
        the_end=the_end,
    )


def handle_relics_from_namespace(
    namespace: dict[str, Any],
    from_error: Any,
    *,
    runner: LegacyCall = handle_relics_context_flow,
) -> Any:
    namespace["Candy"]("Title", "Opening the Ark Of The Covenant :")
    return runner(
        build_relics_runtime_from_namespace(namespace),
        namespace["relics"],
        namespace["relics_ui"],
        build_relics_context_from_namespace(namespace, from_error),
        ask=namespace["Question"],
        emit=namespace["PRINT"],
        pause=namespace["Pause"],
        show_todo=lambda: namespace["relics_ui"].emit_todo(
            emit=namespace["PRINT"],
            candy=namespace["Candy"],
        ),
        candy=namespace["Candy"],
        the_end=namespace["TheEnd"],
    )


def ask_plte_repair(runtime: RelicsRuntime, relics_module: Any, has_bad_crc: bool) -> Any:
    return runtime.ask_choice(
        relics_module.plte_repair_prompt(has_bad_crc),
        relics_module.plte_repair_choices(has_bad_crc),
        relics_module.plte_repair_retry_prompt(has_bad_crc),
    )
