from __future__ import annotations

from collections.abc import MutableSequence
from dataclasses import dataclass
from typing import Any, Callable


LegacyCall = Callable[..., Any]


@dataclass(frozen=True)
class WriteCloneContext:
    file_origin: str
    file_dir: str
    save_count: int
    max_saves: int | None
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


def run_write_clone(
    runtime: WriteCloneRuntime,
    context: WriteCloneContext,
    data: Any,
    infos: Any,
) -> None:
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
