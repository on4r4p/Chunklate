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
class WrongChunkNameRuntime:
    emit: Callable[[str], Any]
    candy: Callable[..., Any]
    question: Callable[..., Any]
    ancillary: Callable[[Any], Any]
    nearby_chunk: Callable[[Any, Any, Any, Any, Any], Any]
    brute_chunk: Callable[[Any, Any, Any, Any], Any]
    save_clone: Callable[[Any, Any, Any, Any], Any]
    set_skip_bad_next_name: Callable[[bool], Any]
    set_skip_bad_current_name: Callable[[bool], Any]
    bad_ancillary: Callable[[], bool]
    pandora_box: Any
    cornucopia: Any


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
    the_good_place: Callable[[Any, Any, Any], Any]
    write_clone: Callable[[Any, str], Any]
    the_end: Callable[[], Any]
    pause: Callable[[str], Any]
    debug_print: Callable[..., Any]
    dummy_chunk: Callable[..., Any]
    nearby_chunk: Callable[..., Any]


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


def build_wrong_crc_runtime_from_namespace(namespace: dict[str, Any]) -> WrongCrcRuntime:
    return WrongCrcRuntime(
        emit=namespace["PRINT"],
        candy=namespace["Candy"],
        question=namespace["Question"],
        save_clone=namespace["SaveClone"],
        chunk_story=namespace["ChunkStory"],
        set_skip_bad_crc=namespace["FixItFelix_Set_Skip_Bad_Crc"],
        set_old_bad_crc=namespace["FixItFelix_Set_Old_Bad_Crc"],
        pandora_box=namespace["PandoraBox"],
        cl_offset=namespace["CLoffI"],
        crc_offset=namespace["CrcoffI"],
        original_chunk_length_hex=namespace["Orig_CL"],
        debug=namespace["DEBUG"],
        pause_debug=namespace["PAUSEDEBUG"],
    )


def build_libpng_error_runtime_from_namespace(namespace: dict[str, Any]) -> LibpngErrorRuntime:
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
        set_skip_bad_next_name=namespace["FixItFelix_Set_Skip_Bad_Next_Name"],
        set_skip_bad_current_name=namespace["FixItFelix_Set_Skip_Bad_Current_Name"],
        bad_ancillary=lambda: namespace["Bad_Ancillary"],
        pandora_box=namespace["PandoraBox"],
        cornucopia=namespace["Cornucopia"],
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
        the_good_place=namespace["TheGoodPlace"],
        write_clone=namespace["WriteClone"],
        the_end=namespace["TheEnd"],
        pause=namespace["Pause"],
        debug_print=print,
        dummy_chunk=namespace["DummyChunk"],
        nearby_chunk=namespace["NearbyChunk"],
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
        pause=namespace["Pause"],
    )


def build_automatic_repair_runtime_from_namespace(namespace: dict[str, Any]) -> AutomaticRepairRuntime:
    return AutomaticRepairRuntime(
        side_notes=namespace["SideNotes"],
        write_clone=namespace["WriteClone"],
    )


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


def ask_wrong_chunk_name_bruteforce(
    runtime: WrongChunkNameRuntime,
    decision: fixit_felix.WrongChunkNameDecision,
    chkd: str,
    tools: relics.WrongChunkNameTools,
) -> tuple[bool, Any]:
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
        return True, runtime.brute_chunk(
            tools.chunk_type,
            tools.previous_chunk,
            tools.chunk_length,
            str(decision.finding),
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

    emit_wrong_chunk_name_critical(runtime, decision.finding)
    runtime.ancillary(tools.chunk_type)
    describe_wrong_chunk_name(runtime, decision)

    if decision.action == "ask_length_probe":
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
        uniqh = relics.question_hash(runtime.pandora_box, decision.finding, chkd)
        answer = runtime.question(id=decision.finding, idhash=uniqh)
        if answer is True:
            return True, runtime.nearby_chunk(
                tools.chunk_type,
                tools.chunk_length,
                tools.chunk_type_offset,
                False,
                decision.finding,
            )

        runtime.set_skip_bad_next_name(True)
        return ask_wrong_chunk_name_bruteforce(runtime, decision, chkd, tools)

    if decision.action == "ask_bruteforce":
        return ask_wrong_chunk_name_bruteforce(runtime, decision, chkd, tools)

    raise ValueError("Unknown FixItFelix wrong-chunk-name action: %s" % decision.action)


def emit_no_next_critical(runtime: NoNextChunkRuntime, finding: Any) -> None:
    runtime.emit("\n-\033[1;31;49mCriticalHit\033[m: %s" % finding)


def discard_no_next_false_positive(runtime: NoNextChunkRuntime) -> None:
    for pandora_key in list(runtime.pandora_box):
        if "No NextChunk" in str(pandora_key):
            runtime.candy(
                "Cowsay",
                "That one is a false positive im removing it ..",
                "good",
            )
            relics.discard_pandora_error(runtime.pandora_box, pandora_key)
            runtime.side_notes.append("-Found False-Positive :[Error:-No NextChunk].")
            runtime.set_skip_bad_no_next_chunk(True)
            break


def no_next_missplaced_tools(runtime: NoNextChunkRuntime) -> list[Any] | None:
    for pandora_key in runtime.pandora_box:
        if "Missplaced" in str(pandora_key) and runtime.eof() is True:
            return list(runtime.pandora_box[pandora_key].values())
    return None


def mark_no_next_iend_reached(runtime: NoNextChunkRuntime) -> None:
    runtime.check_chunk_order(b"IEND", "Critical")
    runtime.candy("Cowsay", "We have reached the end of file.", "good")
    runtime.set_eof(True)
    runtime.side_notes.append("-Reached the end of file.")


def apply_no_next_false_positive_iend(
    runtime: NoNextChunkRuntime,
    decision: fixit_felix.NoNextFalsePositiveIendDecision,
) -> tuple[bool, Any]:
    if decision.action in ("libpng_check", "the_good_place", "continue"):
        mark_no_next_iend_reached(runtime)

        if decision.action == "libpng_check":
            runtime.candy("Cowsay", "Ok let's feed the Kraken now..", "com")
            return True, runtime.libpng_check(runtime.sample)

        if decision.action == "the_good_place":
            rustine = no_next_missplaced_tools(runtime)
            if rustine is not None:
                runtime.candy("Cowsay", "But the fun isnt over yet..", "com")
                return True, runtime.the_good_place(rustine[0], rustine[1], rustine[2])

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
        has_missplaced_finding=any("Missplaced" in str(pandora_key) for pandora_key in runtime.pandora_box),
    )
    return apply_no_next_false_positive_iend(runtime, false_positive_decision)


def handle_no_next_wrong_iend_length(runtime: NoNextChunkRuntime) -> tuple[bool, None]:
    runtime.emit(
        "-%s length for IEND %s "
        % (runtime.candy("Color", "red", "Wrong"), runtime.candy("Emoj", "bad"))
    )
    runtime.emit(runtime.candy("Color", "yellow", "\n-ToDo"))
    runtime.side_notes.append("-Wrong length for IEND")
    runtime.the_end()
    return False, None


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
    runtime.candy("Cowsay", "Well it seems that i need to add that IEND chunk myself after all ..", "bad")
    print_no_next_append_debug(runtime)

    append_decision = fixit_felix.no_next_append_iend_decision(
        runtime.data_hex,
        crc_offset=runtime.crc_offset,
    )
    report_no_next_exceeding(runtime, append_decision.exceeding)
    return apply_no_next_append_iend(runtime, append_decision, finding)


def handle_no_next_ask_length_probe(
    runtime: NoNextChunkRuntime,
    finding: Any,
    chkd: str,
    tools: relics.NoNextChunkTools,
) -> tuple[bool, Any]:
    runtime.emit(
        "\n-End of File Reached but IEND Chunk is %s ! %s"
        % (runtime.candy("Color", "red", " MISSING! "), runtime.candy("Emoj", "bad"))
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
