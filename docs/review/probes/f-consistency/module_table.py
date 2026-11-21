"""Check docs/14's per-module entries (imports, imported by, provides) against the source.

Parses every module with ast; imports nothing from the package. Run from the repository root:
    uv run python docs/review/probes/f-consistency/module_table.py
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

SRC = Path("src/submeter")
DOC = Path("docs/14-baseline-modules.md").read_text(encoding="utf-8")


def dotted(path: Path) -> str:
    return ".".join(path.relative_to(SRC).with_suffix("").parts)


modules = {dotted(p): p for p in SRC.rglob("*.py") if p.name != "__init__.py"}
imports: dict[str, set[str]] = {}
public: dict[str, set[str]] = {}
for name, path in modules.items():
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("submeter"):
            base = node.module.removeprefix("submeter").lstrip(".")
            for alias in node.names:
                candidate = f"{base}.{alias.name}" if base else alias.name
                found.add(candidate if candidate in modules else base)
    imports[name] = {m for m in found if m in modules}
    names = set()
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names |= {t.id for t in node.targets if isinstance(t, ast.Name)}
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    public[name] = {n for n in names if not n.startswith("_")}

importers = {name: {m for m, deps in imports.items() if name in deps} for name in modules}
table = re.findall(r"^\| \[`([\w.]+)`\][^|]+\| \d+ \| ([^|]+) \| ([^|]+) \|", DOC, re.M)
problems = 0
for name, said_imports, said_by in table:
    said_i = set() if "nothing" in said_imports else {s.strip() for s in said_imports.split(",")}
    words = said_by.strip()
    said_b = (
        set() if words in {"nothing yet", "entry point"} else {s.strip() for s in words.split(",")}
    )
    if said_i != imports[name] or said_b != importers[name]:
        problems += 1
        print(
            f"DIFF {name}: imports {sorted(imports[name])}, imported by {sorted(importers[name])}"
        )
print(f"table rows checked: {len(table)}, rows that differ: {problems}")

for name, provides in re.findall(
    r"### `src/submeter/([\w/]+)\.py`.*?\*\*Provides:\*\* ([^\n]+)", DOC, re.S
):
    key = name.replace("/", ".")
    if key not in public:
        continue
    said = set(re.findall(r"`(\w+)`", provides))
    missing, extra = said - public[key], public[key] - said
    if missing or extra:
        print(f"provides {key}: named but absent {sorted(missing)}, unnamed {sorted(extra)}")
print("provides lists checked:", len(re.findall(r"\*\*Provides:\*\*", DOC)))
