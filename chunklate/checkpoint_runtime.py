from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import re
from typing import Any

from . import checkpoint
from . import fog_of_war


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
    question: LegacyCall
    print_libpng_critical: LegacyCall
    discard_libpng_warning: LegacyCall
    libpng_end_success: LegacyCall


@dataclass(frozen=True)
class CheckPointLoopRuntime:
    record_finding: LegacyCall
    apply_action: LegacyCall
    pause_error: LegacyCall


@dataclass(frozen=True)
class CheckPointEntryRuntime:
    candy: LegacyCall
    emit: LegacyCall
    pause_debug: LegacyCall
    record_finding: LegacyCall
    apply_action: LegacyCall
    pause_error: LegacyCall
    render_fog_of_war: LegacyCall | None = None


@dataclass(frozen=True)
class CheckPointLoopContext:
    error: bool
    fixed: bool
    function: Any
    chunk: Any
    infos: tuple[Any, ...]
    toolkit: tuple[Any, ...]
    brute_level: int
    libpng_errors: tuple[str, ...]
    libpng_finished_at_iend: bool
    pause_error_enabled: bool


@dataclass(frozen=True)
class CheckPointEntryContext:
    error: bool
    fixed: bool
    function: Any
    chunk: Any
    infos: tuple[Any, ...]
    toolkit: tuple[Any, ...]
    brute_level: int
    libpng_errors: tuple[str, ...]
    libpng_finished_at_iend: bool
    pandora_keys: tuple[Any, ...]
    chunks_history: tuple[Any, ...] = ()
    data_hex: str = ""
    current_offset: Any = None
    current_chunk_hint: Any = None
    sample_name: str = ""
    debug: bool = False
    pause_debug_enabled: bool = False
    pause_error_enabled: bool = False


def build_checkpoint_runtime_from_namespace(namespace: dict[str, Any]) -> CheckPointRuntime:
    return CheckPointRuntime(
        write_clone=namespace["WriteClone"],
        dummy_chunk=namespace["DummyChunk"],
        summarise=namespace["Summarise"],
        find_fucking_magic=namespace["FindFuckingMagic"],
        check_chunk_name=namespace["CheckChunkName"],
        save_clone=namespace["SaveClone"],
        fix_it_felix=namespace["FixItFelix"],
        relics=namespace["Relics"],
        smash_brute_brawl=namespace["SmashBruteBrawl"],
        candy=namespace["Candy"],
        emit=namespace["PRINT"],
        end=namespace["TheEnd"],
        question=namespace["Question"],
        print_libpng_critical=namespace["CheckPoint_Print_Libpng_Critical"],
        discard_libpng_warning=namespace["CheckPoint_Discard_Libpng_Warning"],
        libpng_end_success=namespace["CheckPoint_Libpng_End_Success"],
    )


def build_checkpoint_entry_runtime(
    *,
    candy: LegacyCall,
    emit: LegacyCall,
    pause_debug: LegacyCall,
    record_finding: LegacyCall,
    apply_action: LegacyCall,
    pause_error: LegacyCall,
    render_fog_of_war: LegacyCall | None = None,
) -> CheckPointEntryRuntime:
    return CheckPointEntryRuntime(
        candy=candy,
        emit=emit,
        pause_debug=pause_debug,
        record_finding=record_finding,
        apply_action=apply_action,
        pause_error=pause_error,
        render_fog_of_war=render_fog_of_war,
    )


def build_checkpoint_entry_runtime_from_namespace(namespace: dict[str, Any]) -> CheckPointEntryRuntime:
    return build_checkpoint_entry_runtime(
        candy=namespace["Candy"],
        emit=namespace["PRINT"],
        pause_debug=namespace["Pause"],
        record_finding=namespace["CheckPoint_Record_Finding"],
        apply_action=namespace["CheckPoint_Apply_Action_Decision"],
        pause_error=namespace["Pause"],
        render_fog_of_war=lambda context: render_fog_of_war_from_context(namespace, context),
    )


def build_checkpoint_entry_context(
    namespace: dict[str, Any],
    *,
    error: bool,
    fixed: bool,
    function: Any,
    chunk: Any,
    infos: Any,
    toolkit: tuple[Any, ...],
) -> CheckPointEntryContext:
    chunks_history = namespace["Chunks_History"]
    return CheckPointEntryContext(
        error=error,
        fixed=fixed,
        function=function,
        chunk=chunk,
        infos=tuple(infos),
        toolkit=toolkit,
        brute_level=namespace["Brute_LvL"],
        libpng_errors=tuple(namespace["LIBPNG_ERR"]),
        libpng_finished_at_iend=(
            bool(chunks_history)
            and chunks_history[-1] == b"IEND"
            and namespace["EOF"] is True
        ),
        pandora_keys=tuple(namespace["PandoraBox"]),
        chunks_history=tuple(chunks_history),
        data_hex=namespace["DATAX"],
        current_offset=namespace["CLoffI"],
        current_chunk_hint=namespace.get("Orig_CT"),
        sample_name=namespace["Sample_Name"],
        debug=namespace["DEBUG"],
        pause_debug_enabled=namespace["PAUSEDEBUG"],
        pause_error_enabled=namespace["PAUSEERROR"],
    )


def run_checkpoint_from_namespace(
    namespace: dict[str, Any],
    *,
    error: bool,
    fixed: bool,
    function: Any,
    chunk: Any,
    infos: Any,
    toolkit: tuple[Any, ...],
    runner: LegacyCall | None = None,
) -> Any:
    if runner is None:
        runner = run_checkpoint
    return runner(
        build_checkpoint_entry_runtime_from_namespace(namespace),
        build_checkpoint_entry_context(
            namespace,
            error=error,
            fixed=fixed,
            function=function,
            chunk=chunk,
            infos=tuple(infos),
            toolkit=toolkit,
        ),
    )


CHECKPOINT_COFFEE = r"""
   ( (
    ) )
  ........
  |      |]
  \      /
   `----'"""


def render_fog_of_war_from_context(namespace: dict[str, Any], context: CheckPointEntryContext) -> str:
    colorizer = lambda color, value: namespace["Candy"]("Color", color, value)
    idat_wrong_crc_count = _idat_wrong_crc_count(context)
    update_fog_of_war_bad_chunks(namespace, context)
    preview_next = _is_check_chunk_name_next_context(context)
    current_chunk = _fog_current_chunk(context) if preview_next or _is_multiple_chunk_order_context(context) else context.chunk
    current_error = context.error and not context.fixed and not preview_next
    chunks_history = _fog_chunks_history(context, current_chunk, preview_next)
    preview_chunk, preview_error = update_fog_of_war_preview(
        namespace,
        context,
        current_chunk,
        preview_next,
    )
    fog_map = fog_of_war.build_map(
        chunks_history,
        current_chunk,
        data_hex=context.data_hex,
        current_offset=context.current_offset,
        error=current_error,
        sample_name=context.sample_name,
        idat_wrong_crc_count=idat_wrong_crc_count,
        bad_chunk_labels=namespace.get("FOG_OF_WAR_BAD_CHUNKS", ()),
        bad_chunk_occurrences=namespace.get("FOG_OF_WAR_BAD_CHUNK_OCCURRENCES", ()),
        preview_chunk=preview_chunk,
        preview_error=preview_error,
    )
    previous_key = namespace.get("FOG_OF_WAR_LAST_RENDER_KEY")
    current_key = _fog_of_war_render_key(fog_map, context)
    current_width = fog_of_war.visible_body_width(fog_map, color=colorizer)
    namespace["FOG_OF_WAR_LAST_MAP"] = fog_map
    namespace["FOG_OF_WAR_LAST_WIDTH"] = current_width
    namespace["FOG_OF_WAR_LAST_RENDER_KEY"] = current_key

    if previous_key == current_key:
        return ""

    return fog_of_war.render(fog_map, color=colorizer)


def _is_idat_wrong_crc_text(value: Any) -> bool:
    text = str(value)
    return "Wrong Crc" in text and "IDAT" in text


def _is_check_chunk_name_next_context(context: CheckPointEntryContext) -> bool:
    if context.function != "CheckChunkName":
        return False
    info_text = " ".join(str(info) for info in context.infos)
    return "next chunk" in info_text.lower()


def _fog_current_chunk(context: CheckPointEntryContext) -> Any:
    if _is_multiple_chunk_order_context(context):
        parsed_label = _multiple_chunk_label_from_info(" ".join(str(info) for info in context.infos))
        if parsed_label:
            return parsed_label
        if context.chunks_history:
            return context.chunks_history[-1]
    hint_label = _chunk_label(context.current_chunk_hint)
    if hint_label not in GENERIC_BAD_CHUNK_LABELS and hint_label != "None":
        return context.current_chunk_hint
    if context.chunks_history:
        return context.chunks_history[-1]
    return context.chunk


def _fog_chunks_history(
    context: CheckPointEntryContext,
    current_chunk: Any,
    preview_next: bool,
) -> tuple[Any, ...]:
    if preview_next:
        return context.chunks_history
    if _is_multiple_chunk_order_context(context):
        return context.chunks_history
    if context.function != "Checksum" or not context.chunks_history:
        return context.chunks_history
    if _chunk_label(context.chunks_history[-1]) != _chunk_label(current_chunk):
        return context.chunks_history
    return context.chunks_history[:-1]


def _clear_fog_of_war_preview(namespace: dict[str, Any]) -> None:
    namespace["FOG_OF_WAR_PREVIEW_CHUNK"] = None
    namespace["FOG_OF_WAR_PREVIEW_ERROR"] = False


def update_fog_of_war_preview(
    namespace: dict[str, Any],
    context: CheckPointEntryContext,
    current_chunk: Any,
    preview_next: bool,
) -> tuple[Any, bool]:
    if preview_next:
        preview_error = context.error and not context.fixed
        namespace["FOG_OF_WAR_PREVIEW_CHUNK"] = context.chunk
        namespace["FOG_OF_WAR_PREVIEW_ERROR"] = preview_error
        return context.chunk, preview_error

    preview_chunk = namespace.get("FOG_OF_WAR_PREVIEW_CHUNK")
    if preview_chunk is None:
        return None, False

    preview_label = _chunk_label(preview_chunk)
    current_label = _chunk_label(current_chunk)
    history_label = _chunk_label(context.chunks_history[-1]) if context.chunks_history else ""
    if preview_label in ("", "None", "PNG") or preview_label in (current_label, history_label):
        _clear_fog_of_war_preview(namespace)
        return None, False

    return preview_chunk, bool(namespace.get("FOG_OF_WAR_PREVIEW_ERROR", False))


def _fog_of_war_render_key(fog_map: fog_of_war.FogOfWarMap, context: CheckPointEntryContext) -> tuple[Any, ...]:
    return (
        fog_map,
        context.function,
        _chunk_label(context.chunk),
        tuple(str(info) for info in context.infos),
    )


GENERIC_BAD_CHUNK_LABELS = {"", "Critical", "Missplaced", "LibpngCheck"}


def _chunk_label(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("ascii", errors="replace")
    return str(value)


def _misplaced_chunk_label_from_info(info_text: str) -> str:
    match = re.search(r"-([A-Za-z][A-Za-z0-9]{3})\s+is\s+missplaced", info_text, re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(r"-Missplaced\s+\[b'([^']+)'\]", info_text)
    if match:
        return match.group(1)
    return ""


def _multiple_chunk_label_from_info(info_text: str) -> str:
    match = re.search(r"-Multiple\s+([A-Za-z][A-Za-z0-9]{3})\s+chunk", info_text, re.IGNORECASE)
    if match:
        return match.group(1)
    match = re.search(r"-Multiple\s+\[b'([^']+)'\]", info_text)
    if match:
        return match.group(1)
    return ""


def _is_multiple_chunk_order_context(context: CheckPointEntryContext) -> bool:
    if context.function != "CheckChunkOrder":
        return False
    info_text = " ".join(str(info) for info in context.infos)
    return "multiple" in info_text.lower()


def _multiple_chunk_occurrence_from_context(context: CheckPointEntryContext) -> tuple[str, int] | None:
    info_text = " ".join(str(info) for info in context.infos)
    label = _multiple_chunk_label_from_info(info_text)
    if not label and context.chunks_history:
        label = _chunk_label(context.chunks_history[-1])
    if not label or label == "PNG":
        return None

    occurrence = sum(1 for chunk in context.chunks_history if _chunk_label(chunk) == label) + 1
    return label, occurrence


def _context_bad_chunk_labels(context: CheckPointEntryContext) -> tuple[str, ...]:
    labels: list[str] = []
    info_text = " ".join(str(info) for info in context.infos)
    info_text_lower = info_text.lower()
    chunk_label = _chunk_label(context.chunk)

    if context.function == "CheckLength" and "No NextChunk" in info_text and chunk_label == "IEND":
        return ()

    if chunk_label not in GENERIC_BAD_CHUNK_LABELS:
        labels.append(chunk_label)

    if context.function == "CheckChunkOrder" and "missplaced" in info_text_lower:
        parsed_label = _misplaced_chunk_label_from_info(info_text)
        hint_label = _chunk_label(context.current_chunk_hint)
        if parsed_label:
            labels.append(parsed_label)
        elif hint_label not in GENERIC_BAD_CHUNK_LABELS and hint_label != "None":
            labels.append(hint_label)
        elif context.chunks_history:
            labels.append(_chunk_label(context.chunks_history[-1]))

    return tuple(dict.fromkeys(label for label in labels if label and label != "PNG"))


def update_fog_of_war_bad_chunks(namespace: dict[str, Any], context: CheckPointEntryContext) -> None:
    bad_chunks = namespace.setdefault("FOG_OF_WAR_BAD_CHUNKS", set())
    bad_occurrences = namespace.setdefault("FOG_OF_WAR_BAD_CHUNK_OCCURRENCES", set())
    labels = _context_bad_chunk_labels(context)
    occurrence = _multiple_chunk_occurrence_from_context(context) if _is_multiple_chunk_order_context(context) else None
    if not labels and occurrence is None:
        return
    if context.error is True and context.fixed is True:
        for label in labels:
            bad_chunks.discard(label)
        if occurrence is not None:
            bad_occurrences.discard(occurrence)
        return
    if context.error is True:
        bad_chunks.update(labels)
        if occurrence is not None:
            bad_occurrences.add(occurrence)


def _idat_wrong_crc_count(context: CheckPointEntryContext) -> int:
    count = sum(1 for key in context.pandora_keys if _is_idat_wrong_crc_text(key))
    current_is_idat_wrong_crc = (
        context.error is True
        and str(context.chunk).upper() in ("IDAT", "B'IDAT'")
        and any(_is_idat_wrong_crc_text(info) for info in context.infos)
    )
    if current_is_idat_wrong_crc:
        count += 1
    return count


def checkpoint_debug_toolkit_value(value: Any, limit: int = 100) -> Any:
    if len(str(value)) <= limit:
        return value
    if type(value) == bytes:
        return value[0:40] + b"...To big to be displayed ..."
    if type(value) == str:
        return value[0:40] + "...To big to be displayed ..."
    return str(value)[0:40] + "...To big to be displayed ..."


def checkpoint_debug_infos_value(infos: Any) -> Any:
    if isinstance(infos, tuple):
        if len(infos) == 1:
            return infos[0]
        return list(infos)
    return infos


def checkpoint_debug_lines(
    *,
    error: Any,
    fixed: Any,
    function: Any,
    infos: Any,
    chunk: Any,
    toolkit: tuple[Any, ...],
    pandora_keys: tuple[Any, ...],
) -> tuple[str, ...]:
    lines = [
        "error:%s" % error,
        "fixed:%s" % fixed,
        "function:%s" % function,
        "infos:%s" % checkpoint_debug_infos_value(infos),
        "chunk:%s" % chunk,
        "ToolKit:",
    ]
    for index, value in enumerate(toolkit):
        lines.append(
            "Arg%s:%s type:%s"
            % (index, checkpoint_debug_toolkit_value(value), type(value))
        )
    lines.append("Pandora:")
    for key in pandora_keys:
        lines.append("key:%s" % str(key))
    return tuple(lines)


def emit_checkpoint_debug(
    emit: LegacyCall,
    *,
    error: Any,
    fixed: Any,
    function: Any,
    infos: Any,
    chunk: Any,
    toolkit: tuple[Any, ...],
    pandora_keys: tuple[Any, ...],
) -> None:
    for line in checkpoint_debug_lines(
        error=error,
        fixed=fixed,
        function=function,
        infos=infos,
        chunk=chunk,
        toolkit=toolkit,
        pandora_keys=pandora_keys,
    ):
        emit(line)


def emit_checkpoint_findings(
    emit: LegacyCall,
    context: CheckPointEntryContext,
) -> None:
    if context.error is not True or context.fixed is True:
        return
    for info in context.infos:
        emit("\n-\033[1;31;49mCriticalHit\033[m: %s" % info)


def run_checkpoint_loop(
    runtime: CheckPointLoopRuntime,
    context: CheckPointLoopContext,
) -> Any:
    for info in context.infos:
        registration = checkpoint.finding_registration(
            error=context.error,
            fixed=context.fixed,
            function=context.function,
            chunk=context.chunk,
            info=info,
            toolkit=context.toolkit,
        )
        if registration.should_record:
            runtime.record_finding(registration)
            if registration.store == "pandora_box" and context.pause_error_enabled:
                runtime.pause_error("Pause:Error")

        decision = checkpoint.action_decision(
            error=context.error,
            function=context.function,
            chunk=context.chunk,
            info=info,
            toolkit=context.toolkit,
            brute_level=context.brute_level,
            libpng_errors=context.libpng_errors,
            libpng_finished_at_iend=context.libpng_finished_at_iend,
        )
        should_return, result = runtime.apply_action(
            decision,
            context.chunk,
            info,
            context.toolkit,
        )
        if should_return:
            return result

    return ()


def run_checkpoint(
    runtime: CheckPointEntryRuntime,
    context: CheckPointEntryContext,
) -> Any:
    runtime.candy("Title", "CheckPoint")
    if runtime.render_fog_of_war is not None:
        runtime.emit(runtime.render_fog_of_war(context))
    else:
        runtime.emit(CHECKPOINT_COFFEE)

    emit_checkpoint_findings(runtime.emit, context)

    if context.debug is True:
        emit_checkpoint_debug(
            runtime.emit,
            error=context.error,
            fixed=context.fixed,
            function=context.function,
            infos=context.infos,
            chunk=context.chunk,
            toolkit=context.toolkit,
            pandora_keys=context.pandora_keys,
        )

        if context.pause_debug_enabled is True:
            runtime.pause_debug("Checkpoint pause")

    return run_checkpoint_loop(
        CheckPointLoopRuntime(
            record_finding=runtime.record_finding,
            apply_action=runtime.apply_action,
            pause_error=runtime.pause_error,
        ),
        CheckPointLoopContext(
            error=context.error,
            fixed=context.fixed,
            function=context.function,
            chunk=context.chunk,
            infos=context.infos,
            toolkit=context.toolkit,
            brute_level=context.brute_level,
            libpng_errors=context.libpng_errors,
            libpng_finished_at_iend=context.libpng_finished_at_iend,
            pause_error_enabled=context.pause_error_enabled,
        ),
    )


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


def run_libpng_warning_relics(runtime: CheckPointRuntime, info: Any) -> tuple[bool, Any]:
    runtime.print_libpng_critical(info)
    runtime.candy("Cowsay", "Ah found something !", "good")
    return True, runtime.relics(info)


def run_discard_libpng_warning(
    runtime: CheckPointRuntime,
    action: str,
    info: Any,
) -> tuple[bool, Any]:
    runtime.print_libpng_critical(info)
    runtime.candy("Cowsay", "Bah that's just a warning who cares ?! !", "good")
    runtime.candy("Cowsay", "im removing it ..", "good")
    runtime.discard_libpng_warning()
    if action == "discard_libpng_warning_and_end":
        runtime.libpng_end_success(
            "Well maybe i am missing something but as for my abilities my job is done here!"
        )
    return False, None


def run_libpng_end_success(runtime: CheckPointRuntime) -> tuple[bool, Any]:
    runtime.libpng_end_success(
        "Well maybe i am missing something but as far as my current abilities goes the job is done for me here!"
    )
    return False, None


def run_smash_brute_brawl_relaunch(
    runtime: CheckPointRuntime,
    toolkit: tuple[Any, ...],
    from_error: Any,
    *,
    bf_mode: Any = None,
    has_old_crc: bool = False,
    old_crc: Any = None,
) -> Any:
    kwargs = {
        "EditMode": toolkit[4],
        "BfMode": bf_mode if bf_mode is not None else toolkit[5],
        "BruteCrc": toolkit[6],
        "BruteLength": toolkit[7],
    }
    if has_old_crc:
        kwargs["OldCrc"] = old_crc
    return runtime.smash_brute_brawl(
        toolkit[0],
        toolkit[1],
        toolkit[2],
        toolkit[3],
        from_error,
        **kwargs,
    )


def run_smash_brute_brawl_retry_ihdr(
    runtime: CheckPointRuntime,
    toolkit: tuple[Any, ...],
    from_error: Any,
    brute_level: int,
    *,
    has_old_crc: bool = False,
    old_crc: Any = None,
) -> tuple[bool, Any]:
    runtime.candy(
        "Cowsay",
        "One More Try Hang In There ! Increasing Bruteforce Lvl! (%s/3)"
        % brute_level,
        "bad",
    )
    run_smash_brute_brawl_relaunch(
        runtime,
        toolkit,
        from_error,
        has_old_crc=has_old_crc,
        old_crc=old_crc,
    )
    return False, None


def ask_smash_brute_brawl_twobytes_retry(
    runtime: CheckPointRuntime,
    toolkit: tuple[Any, ...],
    *,
    brute_level: int,
    eta: int,
    ihdr_interlace: str,
) -> Any:
    runtime.candy("Cowsay", "Too bad that was the easy way ..", "bad")
    runtime.candy(
        "Cowsay",
        "I may increase the BruteForce Level in case there is another corrupted bytes that iv missed.",
        "com",
    )
    runtime.candy("Cowsay", "But this will take litterally forever...i mean like this :", "bad")
    estimation = eta * toolkit[2]
    if toolkit[1] == b"IDAT":
        estimation *= 3
    from datetime import timedelta

    runtime.emit("-BruteForce Estimated Time : %s\n" % str(timedelta(seconds=estimation)))
    runtime.candy("Cowsay", "And of course this may fail .. Do you still want to try ?", "com")
    if toolkit[1] == b"IDAT" and ihdr_interlace == "1":
        runtime.candy(
            "Cowsay",
            "Since this is an IDAT chunk i may have another solution just answer: 'No' then.",
            "good",
        )

    answer = runtime.question(skipauto=True)
    if answer:
        runtime.candy(
            "Cowsay",
            "One More Try Hang In There ! Increasing Bruteforce Lvl! (%s/1)"
            % brute_level,
            "bad",
        )
    return answer


def ask_smash_brute_brawl_dummy_idat_fallback(runtime: CheckPointRuntime) -> Any:
    runtime.candy(
        "Cowsay",
        "So let's face it ..I wont be able to recover that IDAT before one of us die.",
        "bad",
    )
    runtime.candy("Cowsay", "But i could create another one full of black pixels..", "com")
    runtime.candy("Cowsay", "This way i hope we could end up with a valid png.", "good")
    runtime.candy(
        "Cowsay",
        "At the cost of one beautiful white rectangle in the middle of that image..",
        "bad",
    )
    runtime.candy(
        "Cowsay",
        "What do you say ? Otherwise Chunklate is going to exit .",
        "com",
    )
    return runtime.question()


def run_smash_brute_brawl_end_failed_noncustom(
    runtime: CheckPointRuntime,
) -> tuple[bool, Any]:
    runtime.candy(
        "Cowsay",
        "Iv tried everything , im out of option sorry ..",
        "bad",
    )
    runtime.end()
    return False, None


def ask_smash_brute_brawl_custom_brutus(runtime: CheckPointRuntime) -> Any:
    runtime.candy("Cowsay", "Too bad that was the easy way ..", "bad")
    runtime.candy("Cowsay", "Wanna try to bruteforce the entire chunk instead ?", "com")
    return runtime.question()


def run_smash_brute_brawl_end_unhandled(runtime: CheckPointRuntime) -> tuple[bool, Any]:
    runtime.end()
    return False, None
