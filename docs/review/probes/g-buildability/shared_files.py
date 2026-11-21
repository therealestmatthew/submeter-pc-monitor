"""Probe: which files the 25 components would all need to edit, counted from the sources.

Reads docs/13-build-list.md, tests/test_layers.py, tests/test_baseline.py, src/submeter/cli.py,
core/models.py, core/config.py and pyproject.toml, and prints counts. Reads only. Run from the
repository root:

    uv run python docs/review/probes/g-buildability/shared_files.py
"""

from __future__ import annotations

import ast
import re
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
SRC = REPO / "src" / "submeter"


def tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"))


def literal_layer() -> dict[str, int]:
    for node in ast.walk(tree(REPO / "tests" / "test_layers.py")):
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "LAYER":
            value = ast.literal_eval(node.value)
            assert isinstance(value, dict)
            return value
    return {}


def main() -> None:
    build_list = (REPO / "docs" / "13-build-list.md").read_text(encoding="utf-8")
    components = re.findall(r"^\| (\d\d) `([a-z_.]+)`", build_list, re.MULTILINE)
    packages = sorted({name.split(".")[0] for _, name in components})
    layer = literal_layer()
    print(f"1. components in docs/13: {len(components)}; top-level packages they name: {packages}")
    print(f"   LAYER keys: {sorted(layer)}")
    print(f"   named packages missing from LAYER: {[p for p in packages if p not in layer]}")

    models = tree(SRC / "core" / "models.py")
    records = [
        n.name
        for n in models.body
        if isinstance(n, ast.ClassDef) and any(getattr(b, "id", "") == "Record" for b in n.bases)
    ]
    print(f"2. Record subclasses in core/models.py: {len(records)}")
    settings = next(
        n for n in tree(SRC / "core" / "config.py").body if getattr(n, "name", "") == "Settings"
    )
    assert isinstance(settings, ast.ClassDef)
    groups = [ast.unparse(n.target) for n in settings.body if isinstance(n, ast.AnnAssign)]
    print(f"   setting groups in the one Settings class in core/config.py: {len(groups)} {groups}")

    commands = re.findall(r"^- `([a-z]+)", build_list.split("## Commands")[1], re.MULTILINE)
    cli_text = (SRC / "cli.py").read_text(encoding="utf-8")
    present = re.findall(r"@(?:app|config_app|store_app)\.command\((?:\"([a-z-]+)\")?", cli_text)
    print(
        f"3. command groups in docs/13: {len(commands)}; commands in cli.py today: {len(present)}"
    )
    print("   every new command is added to the single module cli.py (one Typer app)")

    tests = tree(REPO / "tests" / "test_baseline.py")
    functions = [
        n for n in tests.body if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")
    ]
    imported = sorted(
        {
            n.module
            for n in tests.body
            if isinstance(n, ast.ImportFrom) and n.module and n.module.startswith("submeter")
        }
    )
    print(f"4. tests/test_baseline.py: {len(functions)} tests; modules it imports:")
    print(f"   {len(imported)}: {imported}")

    project = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    print(f"5. runtime dependencies in pyproject.toml: {project['project']['dependencies']}")
    print(f"   console scripts: {project['project']['scripts']}")
    print(f"   .github folder present: {(REPO / '.github').exists()}")
    print(f"   .python-version present: {(REPO / '.python-version').exists()}")
    fixtures = [
        p.name for p in (REPO / "tests").iterdir() if p.is_dir() and p.name != "__pycache__"
    ]
    print(f"   folders under tests/ (fixtures, load generator): {fixtures or 'none'}")


if __name__ == "__main__":
    main()
