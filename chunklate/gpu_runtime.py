from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GpuRuntimeConfig:
    enabled: bool = False
    backend: str = "opengl"
    install_missing: bool = True


def _lookup(source: Any, key: str, default: Any = None) -> Any:
    if isinstance(source, dict):
        return source.get(key, default)
    return getattr(source, key, default)


def gpu_requested(namespace: Any) -> bool:
    return bool(_lookup(namespace, "GPU", False))


def build_gpu_config(namespace: Any) -> GpuRuntimeConfig:
    existing = _lookup(namespace, "GPU_CONFIG", None)
    if isinstance(existing, GpuRuntimeConfig):
        return existing
    return GpuRuntimeConfig(enabled=gpu_requested(namespace))
