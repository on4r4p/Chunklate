from __future__ import annotations

import os
from datetime import datetime


def error_log_path(base_path: str) -> str:
    return os.path.join(str(base_path), "Chunklate_Errors.log")


def format_error_log_entry(message: str, *, now: datetime | None = None) -> str:
    if now is None:
        now = datetime.now()
    return str(now) + "\n" + message + "\n"


def append_error_log(message: str, base_path: str, *, now: datetime | None = None) -> str:
    logfile = error_log_path(base_path)
    with open(logfile, "a+") as handle:
        handle.write(format_error_log_entry(message, now=now))
    return logfile
