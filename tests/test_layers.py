"""Imports may only point downward. This keeps the collector replaceable and the core reusable."""

from __future__ import annotations

import ast
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / "src" / "submeter"
LAYER = {
    "core": 0,
    "privacy": 1,
    "providers": 1,
    "store": 2,
    "collector": 2,
    "attribution": 2,
    "analysis": 2,
    "cli": 3,
}


def imports_of(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module
    }
    found |= {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    return {name for name in found if name.startswith("submeter.")}


def test_no_module_imports_from_a_higher_layer() -> None:
    for path in SOURCE.rglob("*.py"):
        package = path.relative_to(SOURCE).parts[0].removesuffix(".py")
        if package == "__init__":
            continue
        for imported in imports_of(path):
            target = imported.split(".")[1]
            same_package = target == package
            assert same_package or LAYER[target] < LAYER[package], f"{path.name} imports {imported}"
