from __future__ import annotations

from dataclasses import dataclass
import importlib.metadata
import json
import re
import sys
from typing import Any, Callable
from urllib.error import URLError
from urllib.request import urlopen


PYPI_JSON_URL = "https://pypi.org/pypi/%s/json"
DEFAULT_PACKAGE_NAME = "chunklate"
DEFAULT_TIMEOUT = 2.5


@dataclass(frozen=True)
class PackageUpdateStatus:
    package_name: str
    current_version: str
    latest_version: str | None
    up_to_date: bool | None
    error: str = ""

    @property
    def update_available(self) -> bool:
        return self.up_to_date is False


def installed_package_version(package_name: str = DEFAULT_PACKAGE_NAME) -> str:
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        if package_name != DEFAULT_PACKAGE_NAME:
            raise

    try:
        from chunklate import __version__
    except Exception:
        return "0+unknown"
    return str(__version__)


def _version_key(version: str) -> tuple[int, ...]:
    public = str(version).split("+", 1)[0]
    parts: list[int] = []
    for raw_part in re.split(r"[._!-]", public):
        match = re.match(r"(\d+)", raw_part)
        if match is None:
            break
        parts.append(int(match.group(1)))
    while parts and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def version_is_current(current_version: str, latest_version: str) -> bool:
    current_key = _version_key(current_version)
    latest_key = _version_key(latest_version)
    if not current_key or not latest_key:
        return str(current_version) == str(latest_version)
    return current_key >= latest_key


def latest_pypi_version(
    package_name: str = DEFAULT_PACKAGE_NAME,
    *,
    opener: Callable[..., Any] = urlopen,
    timeout: float = DEFAULT_TIMEOUT,
) -> str:
    with opener(PYPI_JSON_URL % package_name, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    version = str(payload.get("info", {}).get("version", "")).strip()
    if not version:
        raise ValueError("PyPI response did not include info.version")
    return version


def check_package_update(
    package_name: str = DEFAULT_PACKAGE_NAME,
    *,
    current_version: str | None = None,
    fetch_latest: Callable[..., str] = latest_pypi_version,
    timeout: float = DEFAULT_TIMEOUT,
) -> PackageUpdateStatus:
    current = str(current_version or installed_package_version(package_name))
    try:
        latest = fetch_latest(package_name, timeout=timeout)
    except (OSError, URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        return PackageUpdateStatus(
            package_name=package_name,
            current_version=current,
            latest_version=None,
            up_to_date=None,
            error=str(exc),
        )
    return PackageUpdateStatus(
        package_name=package_name,
        current_version=current,
        latest_version=latest,
        up_to_date=version_is_current(current, latest),
    )


def upgrade_command(package_name: str = DEFAULT_PACKAGE_NAME, *, python_executable: str | None = None) -> str:
    executable = python_executable or sys.executable
    return '"%s" -m pip install --upgrade %s' % (executable, package_name)


def format_update_message(
    status: PackageUpdateStatus,
    *,
    python_executable: str | None = None,
) -> str:
    if status.up_to_date is True:
        return "%s is up to date (%s)." % (status.package_name, status.current_version)
    if status.up_to_date is None:
        return (
            "Could not check whether %s is up to date.\n"
            "Current version: %s\n"
            "Reason: %s"
        ) % (status.package_name, status.current_version, status.error or "unknown")
    return (
        "%s update available.\n"
        "Installed version: %s\n"
        "Latest PyPI version: %s\n"
        "\n"
        "Update with:\n"
        "  %s\n"
        "\n"
        "If you installed the optional GPU extra, use:\n"
        "  %s"
    ) % (
        status.package_name,
        status.current_version,
        status.latest_version,
        upgrade_command(status.package_name, python_executable=python_executable),
        upgrade_command(status.package_name + "[gpu]", python_executable=python_executable),
    )
