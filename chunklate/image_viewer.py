from __future__ import annotations

import os
import signal
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from typing import Any, Callable, Sequence


@dataclass(frozen=True)
class ImageOpenAttempt:
    opener: str
    command: tuple[str, ...]
    success: bool
    error: str = ""
    process: Any | None = None


@dataclass(frozen=True)
class ImageOpenResult:
    success: bool
    opener: str = ""
    attempts: tuple[ImageOpenAttempt, ...] = ()

    @property
    def error(self) -> str:
        if not self.attempts:
            return ""
        return self.attempts[-1].error

    @property
    def process(self) -> Any | None:
        for attempt in self.attempts:
            if attempt.success and attempt.process is not None:
                return attempt.process
        return None

    def close(
        self,
        *,
        timeout: float = 0.5,
        platform: str = sys.platform,
        killpg: Callable[[int, int], None] | None = None,
    ) -> bool:
        process = self.process
        if process is None:
            return False

        try:
            if process.poll() is not None:
                return False
        except Exception:
            return False

        pid = getattr(process, "pid", None)
        if killpg is None:
            killpg = getattr(os, "killpg", None)
        use_process_group = bool(pid) and killpg is not None and not platform.startswith("win")

        try:
            if use_process_group:
                killpg(pid, signal.SIGTERM)
            else:
                process.terminate()

            try:
                process.wait(timeout=timeout)
                return True
            except subprocess.TimeoutExpired:
                if use_process_group:
                    killpg(pid, signal.SIGKILL)
                else:
                    process.kill()
                process.wait(timeout=timeout)
                return True
        except ProcessLookupError:
            return False
        except Exception:
            try:
                process.kill()
            except Exception:
                return False
            return True


PopenFactory = Callable[..., subprocess.Popen]
WhichLookup = Callable[[str], str | None]
Sleeper = Callable[[float], None]


def default_image_open_command(path: str, *, platform: str = sys.platform) -> tuple[str, ...]:
    if platform == "darwin":
        return ("open", path)
    if platform.startswith("win"):
        return ("cmd", "/c", "start", "", path)
    return ("xdg-open", path)


def _launch_image_viewer(
    command: Sequence[str],
    *,
    popen: PopenFactory,
    sleep: Sleeper,
    settle_seconds: float,
) -> ImageOpenAttempt:
    opener = os.path.basename(command[0])
    command_tuple = tuple(command)
    try:
        process = popen(
            command_tuple,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            start_new_session=True,
        )
    except Exception as exc:
        return ImageOpenAttempt(opener, command_tuple, False, str(exc))

    if settle_seconds > 0:
        sleep(settle_seconds)

    return_code = process.poll()
    if return_code not in (None, 0):
        return ImageOpenAttempt(
            opener,
            command_tuple,
            False,
            "%s exited with status %s" % (opener, return_code),
            process,
        )

    return ImageOpenAttempt(opener, command_tuple, True, process=process)


def open_image(
    path: str,
    *,
    popen: PopenFactory = subprocess.Popen,
    which: WhichLookup = shutil.which,
    sleep: Sleeper = time.sleep,
    platform: str = sys.platform,
    settle_seconds: float = 0.2,
) -> ImageOpenResult:
    attempts: list[ImageOpenAttempt] = []

    feh = which("feh")
    if feh is not None:
        attempt = _launch_image_viewer(
            (feh, path),
            popen=popen,
            sleep=sleep,
            settle_seconds=settle_seconds,
        )
        attempts.append(attempt)
        if attempt.success:
            return ImageOpenResult(True, attempt.opener, tuple(attempts))

    default_command = default_image_open_command(path, platform=platform)
    attempt = _launch_image_viewer(
        default_command,
        popen=popen,
        sleep=sleep,
        settle_seconds=settle_seconds,
    )
    attempts.append(attempt)
    if attempt.success:
        return ImageOpenResult(True, attempt.opener, tuple(attempts))

    return ImageOpenResult(False, "", tuple(attempts))
