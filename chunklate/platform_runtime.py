from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
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


def local_venv_python(root: str | os.PathLike[str], *, os_name: str = os.name) -> str:
    root_path = Path(root)
    if os_name == "nt":
        return str(root_path / ".venv" / "Scripts" / "python.exe")
    return str(root_path / ".venv" / "bin" / "python")


def bootstrap_python_script(root: str | os.PathLike[str]) -> str:
    return str(Path(root) / "scripts" / "bootstrap_dev.py")


def bootstrap_command(
    root: str | os.PathLike[str],
    *,
    executable: str = sys.executable,
) -> list[str]:
    return [executable, bootstrap_python_script(root)]


def format_command(command: list[str] | tuple[str, ...], *, os_name: str = os.name) -> str:
    if os_name == "nt":
        return subprocess.list2cmdline([str(part) for part in command])
    return shlex.join([str(part) for part in command])


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
