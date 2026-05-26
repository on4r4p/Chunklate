from __future__ import annotations

from collections.abc import MutableSequence
from dataclasses import dataclass
from typing import Any, Callable

from . import writer


LegacyCall = Callable[..., Any]


@dataclass(frozen=True)
class WriteCloneContext:
    file_origin: str
    file_dir: str
    save_count: int
    max_saves: int | None
    have_a_kitkat: bool = False
    pause_enabled: bool = False


@dataclass(frozen=True)
class WriteCloneRuntime:
    remember_current_sample: LegacyCall
    prepare_clone_write: LegacyCall
    write_prepared_clone: LegacyCall
    betterror: LegacyCall
    end: LegacyCall
    candy: LegacyCall
    emit: LegacyCall
    pause: LegacyCall
    summarise: LegacyCall
    exit_process: Callable[[int], Any]
    set_sample: Callable[[str], Any]
    set_save_count: Callable[[int], Any]
    set_have_a_kitkat: Callable[[bool], Any]
    side_notes: MutableSequence[str]


@dataclass(frozen=True)
class ClonePatchRuntime:
    data_hex: str
    candy: LegacyCall
    emit: LegacyCall
    betterror: LegacyCall
    write_clone: LegacyCall
    set_show_must_go_on: Callable[[bool], Any]
    remove_hex_range: LegacyCall = writer.remove_hex_range
    replace_hex_range: LegacyCall = writer.replace_hex_range


def build_write_clone_runtime(
    *,
    namespace: dict[str, Any],
    remember_current_sample: LegacyCall,
    betterror: LegacyCall,
    end: LegacyCall,
    candy: LegacyCall,
    emit: LegacyCall,
    pause: LegacyCall,
    summarise: LegacyCall,
    exit_process: Callable[[int], Any],
    side_notes: MutableSequence[str],
    prepare_clone_write: LegacyCall = writer.prepare_clone_write,
    write_prepared_clone: LegacyCall = writer.write_prepared_clone,
) -> WriteCloneRuntime:
    return WriteCloneRuntime(
        remember_current_sample=remember_current_sample,
        prepare_clone_write=prepare_clone_write,
        write_prepared_clone=write_prepared_clone,
        betterror=betterror,
        end=end,
        candy=candy,
        emit=emit,
        pause=pause,
        summarise=summarise,
        exit_process=exit_process,
        set_sample=lambda value: namespace.__setitem__("Sample", value),
        set_save_count=lambda value: namespace.__setitem__("SAVE_COUNT", value),
        set_have_a_kitkat=lambda value: namespace.__setitem__("Have_A_KitKat", value),
        side_notes=side_notes,
    )


def build_write_clone_runtime_from_namespace(namespace: dict[str, Any]) -> WriteCloneRuntime:
    return build_write_clone_runtime(
        namespace=namespace,
        remember_current_sample=namespace["Pandemonium_Remember_Current_Sample"],
        betterror=namespace["Betterror"],
        end=namespace["TheEnd"],
        candy=namespace["Candy"],
        emit=namespace["PRINT"],
        pause=namespace["Pause"],
        summarise=namespace["Summarise"],
        exit_process=namespace["sys"].exit,
        side_notes=namespace["SideNotes"],
    )


def build_write_clone_context(namespace: dict[str, Any]) -> WriteCloneContext:
    return WriteCloneContext(
        file_origin=namespace["FILE_Origin"],
        file_dir=namespace["FILE_DIR"],
        save_count=namespace["SAVE_COUNT"],
        max_saves=namespace["MAX_SAVES"],
        have_a_kitkat=namespace["Have_A_KitKat"],
        pause_enabled=namespace["PAUSE"],
    )


def run_write_clone(
    runtime: WriteCloneRuntime,
    context: WriteCloneContext,
    data: Any,
    infos: Any,
) -> None:
    if context.have_a_kitkat is True:
        runtime.emit("-Clone already queued")
        runtime.candy("Color", "yellow", "Skipping alternate repair branch before this becomes a mille-feuille.")  #
        runtime.side_notes.append("-Clone already queued; skipping alternate repair branch before this becomes a mille-feuille.")
        return None

    runtime.remember_current_sample()

    try:
        clone_plan = runtime.prepare_clone_write(
            context.file_origin,
            context.file_dir,
            data,
            context.save_count,
            context.max_saves,
        )
    except Exception as exc:
        runtime.betterror(exc, "WriteClone")
        runtime.end()
        return None

    target = clone_plan.target
    runtime.emit(runtime.candy("Color", "green", "-Saving to : %s") % target.path)
    runtime.side_notes.append("-Saving to : %s" % target.path)

    try:
        runtime.write_prepared_clone(clone_plan)
        runtime.set_sample(target.path)
        runtime.set_save_count(clone_plan.save_count)
    except Exception as exc:
        runtime.betterror(exc, "WriteClone")
        runtime.emit(
            runtime.candy("Color", "red", "Error WriteClone:%s")
            % runtime.candy("Color", "yellow", exc)
        )
        runtime.end()
        return None

    runtime.set_have_a_kitkat(True)

    if context.pause_enabled is True:
        runtime.pause("-Saved Press Return to continue:")

    runtime.summarise(infos)

    if clone_plan.max_saves_reached:
        runtime.emit("-Max saves reached: %s" % context.max_saves)
        runtime.exit_process(0)

    return None


def run_write_clone_from_namespace(
    namespace: dict[str, Any],
    data: Any,
    infos: Any,
    *,
    runner: LegacyCall = run_write_clone,
) -> None:
    return runner(
        build_write_clone_runtime_from_namespace(namespace),
        build_write_clone_context(namespace),
        data,
        infos,
    )


def run_remove_chunk(
    runtime: ClonePatchRuntime,
    start: int,
    length: int,
    infos: Any,
) -> Any:
    runtime.candy("Title", "Removing Chunk")
    fix = runtime.remove_hex_range(runtime.data_hex, start, length)
    return runtime.write_clone(fix, infos)


def run_save_clone(
    runtime: ClonePatchRuntime,
    data_fix: str,
    start: int,
    end: int,
    infos: Any,
) -> Any:
    runtime.set_show_must_go_on(True)
    runtime.candy("Title", "Saving Clone")
    try:
        runtime.emit("-Data : %s\n" % bytes.fromhex(data_fix))
    except Exception as exc:
        runtime.betterror(exc, "SaveClone")

    fix = runtime.replace_hex_range(runtime.data_hex, data_fix, start, end)
    return runtime.write_clone(fix, infos)
