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

echo
echo "Dependencies installed in: $VENV_DIR"
echo "Activate with: source \"$VENV_DIR/bin/activate\""
echo "Run tests with: \"$VENV_DIR/bin/python\" -m pytest"
