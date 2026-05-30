#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${PYTHON:-python3}"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"

if [ ! -x "$VENV_DIR/bin/python" ]; then
    "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -e "${ROOT_DIR}[dev]"
"$VENV_DIR/bin/python" - <<'PY'
import importlib
import sys

modules = {
    "Pillow": "PIL.Image",
    "inputimeout": "inputimeout",
    "numpy": "numpy",
    "opencv-python": "cv2",
    "psutil": "psutil",
    "ImageHash": "imagehash",
    "python3-tk": "tkinter",
}

missing = []
for package, module in modules.items():
    try:
        importlib.import_module(module)
    except Exception as exc:
        missing.append((package, module, exc))

if missing:
    print("Dependency import check failed:", file=sys.stderr)
    for package, module, exc in missing:
        print(f"- {package} (import {module}): {exc}", file=sys.stderr)
    if any(package == "python3-tk" for package, _, _ in missing):
        print("Install Tkinter on Debian/Ubuntu with: sudo apt install python3-tk", file=sys.stderr)
    raise SystemExit(1)

print("Dependency import check passed.")
PY

echo
echo "Dependencies installed in: $VENV_DIR"
echo "Activate with: source \"$VENV_DIR/bin/activate\""
echo "Run tests with: \"$VENV_DIR/bin/python\" -m pytest"
