from __future__ import annotations

from typing import Any


def append_byte_history(bytes_history: list[Any], byte_number: Any) -> None:
    bytes_history.append(byte_number)
