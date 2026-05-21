from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CloneTarget:
    name: str
    directory: str
    path: str


def clone_folder(file_origin: str, file_dir: str = "") -> str:
    folder_name = "Folder_" + os.path.basename(file_origin)
    return os.path.splitext(os.path.join(file_dir, folder_name))[0]


def ensure_clone_folder(file_origin: str, file_dir: str = "") -> str:
    folder = clone_folder(file_origin, file_dir)
    os.makedirs(folder, exist_ok=True)
    return folder


def clone_basename(file_origin: str) -> str:
    filename = os.path.basename(file_origin)
    if "." in filename:
        filename = os.path.splitext(filename)[0]
    return filename + "."


def next_clone_target(file_origin: str, file_dir: str = "") -> CloneTarget:
    directory = ensure_clone_folder(file_origin, file_dir)
    filename = clone_basename(file_origin)
    fileid = 0
    name = filename + str(fileid) + "_Fixed.png"
    path = os.path.join(directory, name)
    while os.path.exists(path):
        fileid += 1
        name = filename + str(fileid) + "_Fixed.png"
        path = os.path.join(directory, name)
    return CloneTarget(name=name, directory=directory, path=path)


def clone_bytes(data: str | bytes | bytearray) -> bytes:
    if isinstance(data, bytes):
        return data
    if isinstance(data, bytearray):
        return bytes(data)
    return bytes.fromhex(str(data))


def write_clone(target: CloneTarget, data: Any) -> None:
    with open(target.path, "wb") as file:
        file.write(clone_bytes(data))
