#!/usr/bin/env python3
import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def tk_manual_plte_node():
    module = ast.parse((ROOT / "Chunklate.py").read_text())
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == "Tk_Manual_Plte":
            return node
    raise AssertionError("Tk_Manual_Plte not found")


def test_tk_manual_plte_keeps_tk_ui_but_delegates_non_ui_setup():
    node = tk_manual_plte_node()
    attrs = {item.attr for item in ast.walk(node) if isinstance(item, ast.Attribute)}

    assert "create_manual_palette_setup" in attrs
    assert "create_manual_palette_editor" in attrs
    assert "create_manual_palette_session" not in attrs
    assert "manual_palette_full_new_data" not in attrs
    assert "imdecode" not in attrs
    assert "fromarray" not in attrs
    assert "create_palette_editor_window" not in attrs
    assert "create_palette_editor_frames" not in attrs
    assert "create_palette_slider_canvas" not in attrs
    assert "create_palette_sliders" not in attrs
    assert "mainloop" in attrs


def main():
    print("Running palette runtime boundary tests")
    print("  - Tk manual PLTE boundary ... ", end="", flush=True)
    test_tk_manual_plte_keeps_tk_ui_but_delegates_non_ui_setup()
    print("ok")
    print("palette runtime boundary tests passed (1 check)")


if __name__ == "__main__":
    main()
