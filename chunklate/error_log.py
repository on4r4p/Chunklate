from __future__ import annotations

import os
from datetime import datetime
from types import TracebackType
from typing import Any

from . import output


def error_log_path(base_path: str) -> str:
    return os.path.join(str(base_path), "Chunklate_Errors.log")


def format_error_log_entry(message: str, *, now: datetime | None = None) -> str:
    if now is None:
        now = datetime.now()
    return str(now) + "\n" + message + "\n"


def format_exception_message(
    file_name: str,
    exc_type: object,
    function_name: str,
    line_number: int,
    error_msg: object,
) -> str:
    return (
        "!!\nFile: %s has encounter a %s error in %s() at line %s\nError Message:%s\n!!"
        % (file_name, exc_type, function_name, line_number, error_msg)
    )


def format_exception_from_exc_info(
    exc_info: tuple[type[BaseException] | None, BaseException | None, TracebackType | None],
    function_name: str,
    error_msg: Any,
) -> str:
    exc_type, _exc_obj, exc_tb = exc_info
    if exc_tb is None:
        raise ValueError("exc_info traceback is required")
    file_name = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    return format_exception_message(
        file_name,
        exc_type,
        function_name,
        exc_tb.tb_lineno,
        error_msg,
    )


def append_error_log(message: str, base_path: str, *, now: datetime | None = None) -> str:
    logfile = error_log_path(base_path)
    with open(logfile, "a+", encoding="utf-8") as handle:
        handle.write(format_error_log_entry(message, now=now))
    return logfile


def append_repair_folder_error_log(
    message: str,
    file_origin: str,
    file_dir: str = "",
    *,
    now: datetime | None = None,
) -> str:
    folder = output.ensure_clone_folder(file_origin, file_dir)
    return append_error_log(message, folder, now=now)


def append_repair_folder_error_log_from_namespace(
    namespace: dict[str, Any],
    message: str,
) -> str | None:
    file_origin = str(namespace.get("FILE_Origin") or "").strip()
    if not file_origin:
        return None
    file_dir = str(namespace.get("FILE_DIR") or "")
    return append_repair_folder_error_log(message, file_origin, file_dir)


def append_error_log_from_namespace(namespace: dict[str, Any], message: str) -> None:
    try:
        append_error_log(message, str(namespace["sys"].path[0]))
        append_repair_folder_error_log_from_namespace(namespace, message)
        namespace["SideNotes"].append(message)
    except Exception as exc:
        namespace["Betterror"](exc, namespace["inspect"].stack()[0][3])


def betterror_from_namespace(namespace: dict[str, Any], error_msg: Any, def_name: str) -> Any:
    try:
        error_to_log = format_exception_from_exc_info(
            namespace["sys"].exc_info(),
            def_name,
            error_msg,
        )
        if namespace["DEBUG"] is True:
            namespace["PRINT"](error_to_log)

    except Exception as exc:
        namespace["Betterror"](exc, namespace["inspect"].stack()[0][3])
        error_to_log = format_exception_from_exc_info(
            namespace["sys"].exc_info(),
            "Betterror",
            exc,
        )
        if namespace["DEBUG"] is True:
            namespace["PRINT"](error_to_log)

    return namespace["Error_Log"](error_to_log)
