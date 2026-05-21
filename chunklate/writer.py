from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from . import output


@dataclass(frozen=True)
class CloneWritePlan:
    target: output.CloneTarget
    data: bytes
    save_count: int
    max_saves_reached: bool = False


def prepare_clone_write(
    file_origin: str,
    file_dir: str,
    data: Any,
    save_count: int,
    max_saves: int | None,
) -> CloneWritePlan:
    clone_data = output.clone_bytes(data)
    target = output.next_clone_target(file_origin, file_dir)
    next_save_count = save_count + 1
    return CloneWritePlan(
        target=target,
        data=clone_data,
        save_count=next_save_count,
        max_saves_reached=max_saves is not None and next_save_count >= max_saves,
    )


def write_prepared_clone(plan: CloneWritePlan) -> None:
    output.write_clone(plan.target, plan.data)


def write_clone(
    file_origin: str,
    file_dir: str,
    data: Any,
    save_count: int,
    max_saves: int | None,
) -> CloneWritePlan:
    plan = prepare_clone_write(file_origin, file_dir, data, save_count, max_saves)
    write_prepared_clone(plan)
    return plan
