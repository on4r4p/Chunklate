from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Any

from . import output


@dataclass(frozen=True)
class CloneWritePlan:
    target: output.CloneTarget
    data: bytes
    save_count: int
    max_saves_reached: bool = False
    already_exists: bool = False
    sha256: str = ""


def clone_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def existing_clone_target_with_sha(
    file_origin: str,
    file_dir: str,
    sha256: str,
) -> output.CloneTarget | None:
    directory = output.ensure_clone_folder(file_origin, file_dir)
    prefix = output.clone_basename(file_origin, file_dir)
    suffix = "_Fixed.png"
    candidates: list[tuple[int, output.CloneTarget]] = []

    for name in os.listdir(directory):
        if not name.startswith(prefix) or not name.endswith(suffix):
            continue
        index_text = name[len(prefix) : -len(suffix)]
        try:
            index = int(index_text)
        except ValueError:
            continue
        candidates.append(
            (
                index,
                output.CloneTarget(
                    name=name,
                    directory=directory,
                    path=os.path.join(directory, name),
                ),
            )
        )

    for _, target in sorted(candidates, key=lambda candidate: candidate[0]):
        try:
            if file_sha256(target.path) == sha256:
                return target
        except OSError:
            continue
    return None


def prepare_clone_write(
    file_origin: str,
    file_dir: str,
    data: Any,
    save_count: int,
    max_saves: int | None,
) -> CloneWritePlan:
    clone_data = output.clone_bytes(data)
    digest = clone_sha256(clone_data)
    existing_target = existing_clone_target_with_sha(file_origin, file_dir, digest)
    if existing_target is not None:
        return CloneWritePlan(
            target=existing_target,
            data=clone_data,
            save_count=save_count,
            max_saves_reached=False,
            already_exists=True,
            sha256=digest,
        )

    target = output.next_clone_target(file_origin, file_dir)
    next_save_count = save_count + 1
    return CloneWritePlan(
        target=target,
        data=clone_data,
        save_count=next_save_count,
        max_saves_reached=max_saves is not None and next_save_count >= max_saves,
        sha256=digest,
    )


def write_prepared_clone(plan: CloneWritePlan) -> None:
    if plan.already_exists:
        return
    if os.path.exists(plan.target.path):
        digest = plan.sha256 or clone_sha256(plan.data)
        if file_sha256(plan.target.path) == digest:
            return
        raise FileExistsError(
            "Refusing to overwrite existing clone with different SHA: %s"
            % plan.target.path
        )
    output.write_clone(plan.target, plan.data)


def remove_hex_range(data_hex: str, start: int, end: int) -> str:
    return data_hex[:start] + data_hex[end:]


def replace_hex_range(data_hex: str, data_fix: str, start: int, end: int) -> str:
    return data_hex[:start] + data_fix + data_hex[end:]


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
