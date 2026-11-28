"""Imports may only point downward. This keeps the collector replaceable and the core reusable."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "src" / "submeter"
LAYER = {
    "core": 0,
    "privacy": 1,
    "providers": 1,
    "store": 2,
    "collector": 2,
    "attribution": 2,
    "analysis": 2,
    "alerts": 2,
    "report": 2,
    "cli": 3,
    "programs": 3,
}
PROGRAMS = {"collector", "server", "launcher"}  # packages under programs; none imports another


def _is_module(name: str) -> bool:
    path = SOURCE.joinpath(*name.split(".")[1:])
    return path.is_dir() or path.with_suffix(".py").is_file()


def imports_of(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    package = ["submeter", *path.relative_to(SOURCE).parent.parts]
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):  # relative: resolved against the module's package
            up = package[: len(package) - node.level + 1] if node.level else []
            base = ".".join([*up, *filter(None, [node.module])])
            found |= {base} | {
                f"{base}.{a.name}" for a in node.names if _is_module(f"{base}.{a.name}")
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


def test_no_program_imports_another() -> None:
    home = SOURCE / "programs"
    for path in home.rglob("*.py"):
        own = path.relative_to(home).parts[0]
        assert path.parent == home or own in PROGRAMS, f"add {own} to PROGRAMS"
        for imported in imports_of(path):
            other = imported.removeprefix("submeter.programs.").split(".")[0]
            assert other == own or other not in PROGRAMS, f"{own} imports {imported}"


def test_relative_and_package_imports_are_resolved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "submeter"
    (root / "attribution").mkdir(parents=True)
    (root / "store").mkdir()
    (root / "cli.py").write_text("")
    module = root / "attribution" / "loop.py"
    module.write_text("from ..store import raw\nfrom submeter import cli, __version__\n")
    monkeypatch.setattr(sys.modules[__name__], "SOURCE", root)
    assert imports_of(module) == {"submeter.store", "submeter.cli"}
