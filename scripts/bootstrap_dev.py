#!/usr/bin/env python3
from __future__ import annotations

import importlib
import os
from pathlib import Path
import subprocess
import sys
import venv


ROOT_DIR = Path(__file__).resolve().parents[1]
VENV_DIR = Path(os.environ.get("VENV_DIR", ROOT_DIR / ".venv"))


def venv_python(venv_dir: Path = VENV_DIR, *, os_name: str = os.name) -> Path:
    if os_name == "nt":
        return venv_dir / "Scripts" / "python.exe"
    return venv_dir / "bin" / "python"


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT_DIR, check=True)


def ensure_venv() -> Path:
    python = venv_python()
    if not python.exists():
        venv.EnvBuilder(with_pip=True).create(VENV_DIR)
    return python


def check_imports() -> None:
    modules = {
        "Pillow": "PIL.Image",
        "inputimeout": "inputimeout",
        "numpy": "numpy",
        "opencv-python": "cv2",
        "psutil": "psutil",
        "ImageHash": "imagehash",
        "python3-tk": "tkinter",
        "colorama": "colorama",
    }

    missing = []
    for package, module in modules.items():
        try:
            importlib.import_module(module)
        except Exception as exc:
            missing.append((package, module, exc))

    if not missing:
        print("Dependency import check passed.")
        return

    print("Dependency import check failed:", file=sys.stderr)
    for package, module, exc in missing:
        print(f"- {package} (import {module}): {exc}", file=sys.stderr)
    if os.name != "nt" and any(package == "python3-tk" for package, _, _ in missing):
        print("Install Tkinter on Debian/Ubuntu with: sudo apt install python3-tk", file=sys.stderr)
    if os.name == "nt" and any(package == "python3-tk" for package, _, _ in missing):
        print(
            "Tkinter is installed by the official Python for Windows installer; "
            "repair Python with Tcl/Tk enabled if it is missing.",
            file=sys.stderr,
        )
    raise SystemExit(1)


def main() -> None:
    python = ensure_venv()
    run([str(python), "-m", "pip", "install", "--upgrade", "pip"])
    run([str(python), "-m", "pip", "install", "-e", f"{ROOT_DIR}[dev]"])
    run([str(python), "-c", "from scripts.bootstrap_dev import check_imports; check_imports()"])

    print()
    print(f"Dependencies installed in: {VENV_DIR}")
    if os.name == "nt":
        print(f"Activate with: {VENV_DIR}\\Scripts\\activate")
    else:
        print(f"Activate with: source \"{VENV_DIR}/bin/activate\"")
    print(f"Run tests with: \"{python}\" -m pytest")


if __name__ == "__main__":
    main()
