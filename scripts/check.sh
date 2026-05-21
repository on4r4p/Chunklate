#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_PYTHON="$ROOT_DIR/.venv/bin/python"

if [ -n "${PYTHON:-}" ]; then
    PYTHON_BIN="$PYTHON"
elif [ -x "$DEFAULT_PYTHON" ]; then
    PYTHON_BIN="$DEFAULT_PYTHON"
else
    PYTHON_BIN="python3"
fi

cd "$ROOT_DIR"

echo "==> Python bytecode check"
"$PYTHON_BIN" -m py_compile \
    Chunklate.py \
    chunklate/__init__.py \
    chunklate/bruteforce.py \
    chunklate/checkpoint.py \
    chunklate/decisions.py \
    chunklate/fixit_felix.py \
    chunklate/output.py \
    chunklate/palette.py \
    chunklate/palette_ui.py \
    chunklate/png.py \
    chunklate/relics.py \
    tests/test_bruteforce.py \
    tests/test_checkpoint_actions.py \
    tests/test_checkpoint.py \
    tests/test_cli.py \
    tests/test_decisions.py \
    tests/test_fixit_felix_actions.py \
    tests/test_fixit_felix.py \
    tests/test_output.py \
    tests/test_palette.py \
    tests/test_palette_ui.py \
    tests/test_png.py \
    tests/test_relics_state.py \
    tests/test_repairs.py

echo "==> pytest"
if ! "$PYTHON_BIN" -m pytest "$@"; then
    echo
    echo "pytest failed or is missing. Run ./scripts/bootstrap_dev.sh first."
    exit 1
fi

echo "==> git diff --check"
git diff --check

echo "==> local checks passed"
