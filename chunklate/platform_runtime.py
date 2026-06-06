from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath
import os
import shlex
import subprocess
import sys
from typing import Any


@dataclass(frozen=True)
class TerminalColorDecision:
    use_color: bool
    initialized: bool = False
    reason: str = ""


def os_family(*, platform: str = sys.platform, os_name: str = os.name) -> str:
    if os_name == "nt" or platform.startswith("win"):
        return "windows"
    if platform == "darwin":
        return "darwin"
    return "linux"


def is_windows(*, platform: str = sys.platform, os_name: str = os.name) -> bool:
    return os_family(platform=platform, os_name=os_name) == "windows"


def _positive_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if parsed <= 0:
        return None
    return parsed


def detected_cpu_count(*, env: dict[str, str] | None = None, os_module: Any = os) -> int:
    """Return the usable logical CPU count across Linux/macOS/Windows."""
    affinity = getattr(os_module, "sched_getaffinity", None)
    if callable(affinity):
        try:
            count = len(affinity(0))
        except (OSError, TypeError, ValueError):
            count = 0
        if count > 0:
            return count

    env = os.environ if env is None else env
    for key in ("NUMBER_OF_PROCESSORS", "CHUNKLATE_CPU_COUNT"):
        count = _positive_int(env.get(key))
        if count is not None:
            return count

    cpu_count = getattr(os_module, "cpu_count", None)
    if callable(cpu_count):
        count = _positive_int(cpu_count())
        if count is not None:
            return count

    sysconf = getattr(os_module, "sysconf", None)
    if callable(sysconf):
        for key in ("SC_NPROCESSORS_ONLN", "NPROCESSORS_ONLN"):
            try:
                count = _positive_int(sysconf(key))
            except (OSError, TypeError, ValueError):
                count = None
            if count is not None:
                return count

    return 1


def recommended_worker_count(
    cpu_count: int | None = None,
    *,
    profile: str = "normal",
    cap: int | None = None,
) -> int:
    detected = detected_cpu_count() if cpu_count is None else max(1, int(cpu_count))
    normalized = str(profile or "normal").strip().lower()
    if normalized == "auto":
        normalized = "normal"
    if normalized == "min":
        recommended = max(detected // 4, 1)
    elif normalized == "normal":
        recommended = max(detected // 2, 1)
    elif normalized == "max":
        recommended = max(detected - 1, 1)
    else:
        raise ValueError("Unknown worker profile: %s" % profile)
    if cap is None:
        return recommended
    return min(recommended, max(1, int(cap)))


def _pure_path_for_os(os_name: str):
    if os_name == "nt":
        return PureWindowsPath
    return PurePosixPath


def local_venv_python(root: str | os.PathLike[str], *, os_name: str = os.name) -> str:
    root_path = _pure_path_for_os(os_name)(root)
    if os_name == "nt":
        return str(root_path / ".venv" / "Scripts" / "python.exe")
    return str(root_path / ".venv" / "bin" / "python")


def bootstrap_python_script(root: str | os.PathLike[str], *, os_name: str = os.name) -> str:
    return str(_pure_path_for_os(os_name)(root) / "scripts" / "bootstrap_dev.py")


def bootstrap_command(
    root: str | os.PathLike[str],
    *,
    executable: str = sys.executable,
    os_name: str = os.name,
) -> list[str]:
    return [executable, bootstrap_python_script(root, os_name=os_name)]


def format_command(command: list[str] | tuple[str, ...], *, os_name: str = os.name) -> str:
    if os_name == "nt":
        return subprocess.list2cmdline([str(part) for part in command])
    return shlex.join([str(part) for part in command])


def configure_text_stream_errors(*streams: Any, errors: str = "replace") -> int:
    configured = 0
    for stream in streams:
        reconfigure = getattr(stream, "reconfigure", None)
        if not callable(reconfigure):
            continue
        try:
            reconfigure(errors=errors)
        except (OSError, TypeError, ValueError):
            continue
        configured += 1
    return configured


def stream_is_tty(stream: Any) -> bool:
    return bool(hasattr(stream, "isatty") and stream.isatty())


def decide_terminal_color(
    color_mode: str,
    *,
    stream: Any = None,
    os_name: str = os.name,
    platform: str = sys.platform,
    colorama_module: Any = None,
) -> TerminalColorDecision:
    if color_mode not in ("auto", "always", "never"):
        raise ValueError("Unknown color mode: %s" % color_mode)

    if color_mode == "never":
        return TerminalColorDecision(False, reason="disabled")

    stream = sys.stdout if stream is None else stream
    is_tty = stream_is_tty(stream)
    use_color = color_mode == "always" or is_tty
    initialized = False

    if use_color and is_windows(platform=platform, os_name=os_name) and colorama_module is not None:
        colorama_module.just_fix_windows_console()
        initialized = True

    if not use_color:
        return TerminalColorDecision(False, initialized=initialized, reason="not-a-tty")
    return TerminalColorDecision(True, initialized=initialized, reason=color_mode)
