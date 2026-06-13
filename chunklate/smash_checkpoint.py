from __future__ import annotations

from dataclasses import dataclass
import hashlib
from io import BytesIO
import json
import os
import time
import uuid
from typing import Any, Mapping

from . import png


SMASH_PROGRESS_VERSION = 2
SMASH_PROGRESS_COMPATIBLE_VERSIONS = (1, 2)
SMASH_PROGRESS_NAME = "_SBB.progress.json"
SMASH_SOURCE_RAW_NAME = "_SBB.Source.raw"
SMASH_SOURCE_NAME = "_SBB.Source.png"
SMASH_RESUME_MODES = ("ask", "auto", "never", "reset")
SMASH_PROGRESS_WRITE_STEP = 100
SMASH_PROGRESS_WRITE_INTERVAL_SECONDS = 2.0


@dataclass(frozen=True)
class SmashProgressPaths:
    folder: str
    progress_path: str
    source_raw_path: str
    source_png_path: str


class SmashBruteBrawlInterrupted(Exception):
    def __init__(self, progress_path: str):
        self.progress_path = progress_path
        super().__init__("DaedalusForce interrupted; progress saved to %s" % progress_path)


def source_hash(data: bytes) -> str:
    return hashlib.blake2b(data, digest_size=16).hexdigest()


def _hidden_tmp_path(path: str) -> str:
    directory, filename = os.path.split(path)
    tmp_name = ".%s.%s.%s.tmp" % (
        filename or "chunklate",
        os.getpid(),
        uuid.uuid4().hex,
    )
    return os.path.join(directory, tmp_name) if directory else tmp_name


def atomic_write_json(path: str, record: Mapping[str, Any]) -> None:
    if not path:
        return
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    tmp_path = _hidden_tmp_path(path)
    with open(tmp_path, "w", encoding="utf-8") as file:
        json.dump(dict(record), file, sort_keys=True, indent=2)
    os.replace(tmp_path, path)


def atomic_write_bytes(path: str, data: bytes) -> None:
    if not path:
        return
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    tmp_path = _hidden_tmp_path(path)
    with open(tmp_path, "wb") as file:
        file.write(data)
    os.replace(tmp_path, path)


def source_is_png_decodable(data: bytes) -> bool:
    if not data.startswith(png.PNG_SIGNATURE):
        return False
    try:
        tuple(png.iter_chunks(data))
    except Exception:
        return False
    try:
        from PIL import Image

        with Image.open(BytesIO(data)) as image:
            image.load()
    except Exception:
        return False
    return True


def write_source_snapshot(paths: SmashProgressPaths, data: bytes) -> None:
    atomic_write_bytes(paths.source_raw_path, data)
    if source_is_png_decodable(data):
        atomic_write_bytes(paths.source_png_path, data)
    elif paths.source_png_path:
        try:
            os.remove(paths.source_png_path)
        except FileNotFoundError:
            pass


def load_json(path: str) -> tuple[dict[str, Any] | None, str]:
    if not path or not os.path.exists(path):
        return None, ""
    try:
        with open(path, "r", encoding="utf-8") as file:
            record = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        return None, "DaedalusForce progress checkpoint is not readable: %s" % exc
    if not isinstance(record, dict):
        return None, "DaedalusForce progress checkpoint is not a JSON object."
    if int(record.get("version", 0) or 0) not in SMASH_PROGRESS_COMPATIBLE_VERSIONS:
        return None, "DaedalusForce progress checkpoint version is not compatible."
    return record, ""


def load_source_snapshot(paths: SmashProgressPaths) -> bytes | None:
    for path in (paths.source_raw_path, paths.source_png_path):
        if not path or not os.path.exists(path):
            continue
        try:
            with open(path, "rb") as file:
                return file.read()
        except OSError:
            continue
    return None


def normalize_old_crc(value: Any) -> str:
    if value in (False, None, ""):
        return ""
    if isinstance(value, bytes):
        return value.hex()
    return str(value)


def invocation_record(
    *,
    file: Any,
    chunk_name: bytes,
    chunk_length: int,
    data_offset: int,
    from_error: Any,
    edit_mode: str,
    bf_mode: str,
    brute_crc: bool,
    brute_length: bool,
    old_crc: Any,
    brute_level: int,
    campaign_focus: str = "",
) -> dict[str, Any]:
    return {
        "file": str(file),
        "chunk_name": chunk_name.decode(errors="replace"),
        "chunk_name_hex": chunk_name.hex(),
        "chunk_length": int(chunk_length),
        "data_offset": int(data_offset),
        "from_error": str(from_error),
        "edit_mode": str(edit_mode),
        "bf_mode": str(bf_mode),
        "brute_crc": bool(brute_crc),
        "brute_length": bool(brute_length),
        "old_crc": normalize_old_crc(old_crc),
        "brute_level": int(brute_level),
        "campaign_focus": str(campaign_focus or ""),
    }


def candidate_space_hash(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(dict(payload), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.blake2b(encoded, digest_size=16).hexdigest()


def progress_due(tested: int, last_write_at: float) -> bool:
    if tested <= 1:
        return True
    if tested % SMASH_PROGRESS_WRITE_STEP == 0:
        return True
    return time.monotonic() - last_write_at >= SMASH_PROGRESS_WRITE_INTERVAL_SECONDS
