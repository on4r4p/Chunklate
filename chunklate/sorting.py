from __future__ import annotations

import re


def digit_or_text(part: str) -> int | str:
    return int(part) if part.isdigit() else part


def natural_sort_key(value: str) -> list[int | str]:
    return [digit_or_text(part) for part in re.split(r"(\d+)", value)]
