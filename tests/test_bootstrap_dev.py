#!/usr/bin/env python3
import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP = ROOT / "scripts" / "bootstrap_dev.py"


def load_bootstrap_module():
    spec = importlib.util.spec_from_file_location("bootstrap_dev", BOOTSTRAP)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_venv_python_uses_platform_layouts(tmp_path):
    bootstrap = load_bootstrap_module()

    assert bootstrap.venv_python(tmp_path / ".venv", os_name="posix") == tmp_path / ".venv" / "bin" / "python"
    assert bootstrap.venv_python(tmp_path / ".venv", os_name="nt") == tmp_path / ".venv" / "Scripts" / "python.exe"


def main():
    checks = [
        ("venv python paths", lambda: test_venv_python_uses_platform_layouts(Path("/tmp/chunklate-test"))),
    ]

    print("Running bootstrap tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"bootstrap tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
