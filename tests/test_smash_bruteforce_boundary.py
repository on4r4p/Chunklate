#!/usr/bin/env python3
import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def smash_brute_brawl_node():
    module = ast.parse((ROOT / "Chunklate.py").read_text())
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == "SmashBruteBrawl":
            return node
    raise AssertionError("SmashBruteBrawl function not found")


def test_smash_brute_brawl_stays_a_legacy_bridge():
    node = smash_brute_brawl_node()
    names = {item.id for item in ast.walk(node) if isinstance(item, ast.Name)}
    attrs = {item.attr for item in ast.walk(node) if isinstance(item, ast.Attribute)}

    assert "smash_bruteforce" in names
    assert "bruteforce_runtime" not in names
    assert "bruteforce_result" not in names
    assert "bruteforce_viewer" not in names
    assert "run_legacy_smash_brute_brawl" in attrs

    forbidden_attrs = {
        "BruteForceResultContext",
        "BruteForceResultRuntime",
        "BruteForceViewerRuntime",
        "SmashBruteBrawlContext",
        "SmashBruteBrawlRuntime",
        "run_result",
        "run_scan",
        "show_candidate",
    }
    assert attrs.isdisjoint(forbidden_attrs)


def test_smash_brute_brawl_only_keeps_small_legacy_adapters():
    node = smash_brute_brawl_node()
    nested_functions = {
        item.name
        for item in node.body
        if isinstance(item, ast.FunctionDef)
    }

    assert nested_functions == {"LoadSpec", "SaveViewerError", "SyncLegacyState"}
    assert node.end_lineno - node.lineno + 1 <= 100


def main():
    checks = [
        ("Bridge boundary", test_smash_brute_brawl_stays_a_legacy_bridge),
        ("Bridge size", test_smash_brute_brawl_only_keeps_small_legacy_adapters),
    ]

    print("Running smash bruteforce boundary tests")
    for label, check in checks:
        print(f"  - {label} ... ", end="", flush=True)
        check()
        print("ok")

    print(f"smash bruteforce boundary tests passed ({len(checks)} checks)")


if __name__ == "__main__":
    main()
