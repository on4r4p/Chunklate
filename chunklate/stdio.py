from __future__ import annotations

from contextlib import contextmanager
import ctypes
import os
import sys
import tempfile
from typing import Callable


def _flush_c_stderr() -> None:
    try:
        libc = ctypes.CDLL(None)
        c_stderr = ctypes.c_void_p.in_dll(libc, "stderr")
        libc.fflush(c_stderr)
    except Exception:
        return


def _safe_flush_c_stderr(flusher: Callable[[], None] | None) -> None:
    if flusher is None:
        return
    try:
        flusher()
    except Exception:
        return


@contextmanager
def stderr_redirector(
    stream,
    *,
    c_stderr_flusher: Callable[[], None] | None = _flush_c_stderr,
):
    original_stderr_fd = sys.stderr.fileno()
    saved_stderr_fd = os.dup(original_stderr_fd)

    with tempfile.TemporaryFile(mode="w+b") as tfile:
        try:
            sys.stderr.flush()
            _safe_flush_c_stderr(c_stderr_flusher)
            os.dup2(tfile.fileno(), original_stderr_fd)
            yield
            sys.stderr.flush()
            _safe_flush_c_stderr(c_stderr_flusher)
        finally:
            os.dup2(saved_stderr_fd, original_stderr_fd)
            os.close(saved_stderr_fd)
            tfile.flush()
            tfile.seek(0, os.SEEK_SET)
            stream.write(tfile.read())
