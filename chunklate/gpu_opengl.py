from __future__ import annotations

from dataclasses import dataclass
import importlib
import subprocess
import sys
from typing import Any, Callable


MODERNGL_REQUIREMENT = "moderngl>=5.10"


@dataclass(frozen=True)
class GpuAvailability:
    available: bool
    backend: str
    reason: str


@dataclass(frozen=True)
class GpuInstallResult:
    installed: bool
    reason: str


class OpenGLComputeUnavailable(RuntimeError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass
class OpenGLComputeHarness:
    context: Any

    def compile_compute_shader(self, source: str) -> Any:
        compiler = getattr(self.context, "compute_shader", None)
        if not callable(compiler):
            raise OpenGLComputeUnavailable("OpenGL context cannot compile compute shaders")
        return compiler(source)

    def buffer(self, data: bytes | None = None, *, reserve: int | None = None) -> Any:
        factory = getattr(self.context, "buffer", None)
        if not callable(factory):
            raise OpenGLComputeUnavailable("OpenGL context cannot create buffers")
        if data is not None:
            return factory(data)
        return factory(reserve=reserve)

    def dispatch(self, shader: Any, *, group_x: int, group_y: int = 1, group_z: int = 1) -> None:
        runner = getattr(shader, "run", None)
        if not callable(runner):
            raise OpenGLComputeUnavailable("OpenGL compute shader cannot be dispatched")
        runner(int(group_x), int(group_y), int(group_z))

    def memory_barrier(self) -> None:
        barrier = getattr(self.context, "memory_barrier", None)
        if callable(barrier):
            barrier()

    def release(self) -> None:
        _release_context(self.context)

    def __enter__(self) -> "OpenGLComputeHarness":
        return self

    def __exit__(self, _exc_type: Any, _exc: Any, _tb: Any) -> None:
        self.release()


def detect_opengl_compute(
    *,
    import_module: Callable[[str], Any] = importlib.import_module,
    context_factory: Callable[..., Any] | None = None,
    auto_install: bool = False,
    installer: Callable[[str], GpuInstallResult] | None = None,
) -> GpuAvailability:
    try:
        harness = create_compute_harness(
            import_module=import_module,
            context_factory=context_factory,
            auto_install=auto_install,
            installer=installer,
        )
    except OpenGLComputeUnavailable as exc:
        return GpuAvailability(False, "opengl", exc.reason)

    harness.release()
    return GpuAvailability(True, "opengl", "OpenGL compute context available")


def create_compute_harness(
    *,
    import_module: Callable[[str], Any] = importlib.import_module,
    context_factory: Callable[..., Any] | None = None,
    auto_install: bool = False,
    installer: Callable[[str], GpuInstallResult] | None = None,
) -> OpenGLComputeHarness:
    try:
        moderngl = import_module("moderngl")
    except Exception:
        if not auto_install:
            raise OpenGLComputeUnavailable("moderngl is not installed")
        install_result = (installer or install_moderngl)(MODERNGL_REQUIREMENT)
        if not install_result.installed:
            raise OpenGLComputeUnavailable(
                "moderngl is not installed and automatic install failed: %s" % install_result.reason,
            )
        try:
            moderngl = import_module("moderngl")
        except Exception as import_exc:
            raise OpenGLComputeUnavailable(
                "moderngl install completed but import still failed: %s" % import_exc,
            )

    factory = context_factory or getattr(moderngl, "create_standalone_context", None)
    if not callable(factory):
        raise OpenGLComputeUnavailable("moderngl cannot create a standalone context")

    context = None
    try:
        context = factory(require=430)
    except Exception as exc:
        raise OpenGLComputeUnavailable("OpenGL compute context unavailable: %s" % exc) from exc

    try:
        version_code = int(getattr(context, "version_code", 0) or 0)
    except Exception:
        version_code = 0
    if version_code and version_code < 430:
        _release_context(context)
        raise OpenGLComputeUnavailable("OpenGL 4.3 compute shaders are unavailable")

    return OpenGLComputeHarness(context)


def install_moderngl(requirement: str = MODERNGL_REQUIREMENT) -> GpuInstallResult:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", requirement],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except Exception as exc:
        return GpuInstallResult(False, str(exc))

    if result.returncode == 0:
        return GpuInstallResult(True, "installed %s" % requirement)

    details = (result.stderr or result.stdout or "pip exited with %s" % result.returncode).strip()
    details = " ".join(details.split())
    return GpuInstallResult(False, details)


def _release_context(context: Any) -> None:
    release = getattr(context, "release", None)
    if callable(release):
        try:
            release()
        except Exception:
            pass
