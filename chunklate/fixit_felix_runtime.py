from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Callable

from . import fixit_felix
from . import relics


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
    write_clone: Callable[[Any, str], Any]


@dataclass(frozen=True)
class GamaZeroRuntime:
    candy: Callable[..., Any]
    pandora_box: Any
    side_notes: Any
    return_value: Any


@dataclass(frozen=True)
class CriticalMissRuntime:
    emit: Callable[[str], Any]
    pause: Callable[[str], Any]


@dataclass(frozen=True)
class WrongCrcRuntime:
    emit: Callable[[str], Any]
    candy: Callable[..., Any]
    question: Callable[..., Any]
    save_clone: Callable[[Any, Any, Any, Any], Any]
    chunk_story: Callable[..., Any]
    set_skip_bad_crc: Callable[[Any], Any]
    set_old_bad_crc: Callable[[Any], Any]
    pandora_box: Any
    cl_offset: Any
    crc_offset: Any
    original_chunk_length_hex: str
    debug: bool
    pause_debug: bool


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


def emit_libpng_critical(runtime: LibpngErrorRuntime, finding: Any) -> None:
    runtime.emit("\n-\033[1;31;49mCriticalHit\033[m: %s" % finding)


def apply_repair(runtime: AutomaticRepairRuntime, repair: Any) -> bool:
    applied_repair = fixit_felix.applied_repair(repair)
    runtime.side_notes.append(applied_repair.note)
    runtime.write_clone(applied_repair.data_hex, applied_repair.save_suffix)
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
    if decision.action == "pause_debug":
        runtime.pause("Pause:Debug")
        return False, None
    if decision.action == "continue":
        return False, None

    raise ValueError("Unknown FixItFelix critical-miss action: %s" % decision.action)


def emit_wrong_crc_critical(runtime: WrongCrcRuntime, finding: Any) -> None:
    runtime.emit("\n-\033[1;31;49mCriticalHit\033[m: %s" % finding)


def save_wrong_crc(runtime: WrongCrcRuntime, tools: relics.WrongCrcTools) -> tuple[bool, Any]:
    save_plan = relics.wrong_crc_save_clone_plan(tools)
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


def final_wrong_crc_question(
    runtime: WrongCrcRuntime,
    finding: Any,
    chkd: str,
    tools: relics.WrongCrcTools,
) -> tuple[bool, Any]:
    uniqh = relics.question_hash(runtime.pandora_box, finding, chkd)
    answer = runtime.question(id=finding, idhash=uniqh)
    if answer is False:
        return save_wrong_crc(runtime, tools)
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
        runtime.candy("Cowsay", "Crc checksum is not valid !!!", "bad")
        runtime.candy(
            "Cowsay",
            "This looks like an easy fix since there is no real errors beside the Crc issue.Do you wish to try to fix it ?",
            "com",
        )
        uniqh = relics.question_hash(runtime.pandora_box, decision.finding, chkd)
        answer = runtime.question(id=decision.finding, idhash=uniqh)
        if answer is True:
            return save_wrong_crc(runtime, tools)

        runtime.set_skip_bad_crc(None)
        return final_wrong_crc_question(runtime, decision.finding, chkd, tools)

    if decision.action == "ask_other_errors_first":
        runtime.candy(
            "Cowsay",
            "Crc checksum is not valid and there are %s other errors !"
            % decision.other_error_count,
            "bad",
        )
        runtime.candy(
            "Cowsay",
            "We may want to fix them first before jumping on that Crc what do you think ?",
            "com",
        )
        return final_wrong_crc_question(runtime, decision.finding, chkd, tools)

    raise ValueError("Unknown FixItFelix wrong-CRC action: %s" % decision.action)


def apply_libpng_error(
    runtime: LibpngErrorRuntime,
    decision: fixit_felix.LibpngErrorDecision,
    chkd: str,
) -> Any:
    emit_libpng_critical(runtime, decision.finding)

    if decision.action == "not_enough_image_data":
        runtime.candy("Cowsay", "Well this is as far as i could get for now. ", "bad")
        runtime.candy("Cowsay", "At least i was able to get some pixels out of it ..", "com")
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

        runtime.candy("Cowsay", "See You Space Cowboy....", "good")
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
