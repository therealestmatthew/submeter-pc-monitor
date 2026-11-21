"""Recompute the counts and sums the brief states, and print each next to its claim.

Reads docs/ and the source tree only. Run from the repository root:
    uv run python docs/review/probes/f-consistency/counts.py
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

DOCS = Path("docs")
SRC = Path("src/submeter")


def text(name: str) -> str:
    return (DOCS / name).read_text(encoding="utf-8")


def show(claim: str, found: object, ok: bool) -> None:
    print(f"{'same' if ok else 'DIFF'}  {claim}: {found}")


def section(doc: str, start: str, end: str) -> str:
    body = doc.split(start, 1)[1]
    return body.split(end, 1)[0] if end else body


build = text("13-build-list.md")
components = re.findall(r"^\| (\d\d) `", build, re.M)
show("13: 25 components", len(components), len(components) == 25)
tagged = [line for line in build.splitlines() if "[baseline]" in line]
show("13: twelve components carry a baseline tag", len(tagged), len(tagged) == 12)
tables = section(build, "## Tables, by file", "## Alongside")
per_file = [re.findall(r"`(\w+)`", line) for line in tables.splitlines() if line.startswith("- ")]
names = [n for row in per_file for n in row]
show("13: 18 tables (distinct names)", len(set(names)), len(set(names)) == 18)
show("    tables counted per file (meta in each)", len(names), len(names) == 18)
commands = section(build, "## Commands", "## API routes")
show("13: 13 commands", commands.count("\n- "), commands.count("\n- ") == 13)
routes = section(build, "## API routes", "## Not in version 1")
show("13: 13 API routes", routes.count("\n- "), routes.count("\n- ") == 13)

terms = re.findall(r"^- \*\*", text("12-glossary.md"), re.M)
show("README: twelve terms", len(terms), len(terms) == 12)

log = text("16-review-log.md")
rows = re.findall(r"^\| (R\d\d) \| (\w+) pass \| [^|]+\| ([^|]+) \|", log, re.M)
passes: dict[str, int] = {}
outcomes: dict[str, int] = {}
for _, which, outcome in rows:
    passes[which] = passes.get(which, 0) + 1
    outcomes[outcome.strip()] = outcomes.get(outcome.strip(), 0) + 1
show("16: passes 14, 8, 15", passes, list(passes.values()) == [14, 8, 15])
show("16: 34 fixed, 3 accepted", outcomes, outcomes == {"fixed": 34, "accepted limit": 3})
phases = re.findall(r"^## P(\d):", text("15-phases-and-decisions.md"), re.M)
show("01: 8 phases", len(phases), len(phases) == 8)

modules = text("14-baseline-modules.md")
stated = dict(re.findall(r"^\| \[`([\w.]+)`\][^|]+\| (\d+) \|", modules, re.M))
total = 0
for dotted, lines in stated.items():
    path = SRC / (dotted.replace(".", "/") + ".py")
    actual = len(path.read_text(encoding="utf-8").splitlines())
    total += actual
    if actual != int(lines):
        show(f"14: {dotted} {lines} lines", actual, False)
show("14: 15 modules", len(stated), len(stated) == 15)
show("14: 2,356 lines in the modules", total, total == 2356)
python_files = sorted(SRC.rglob("*.py"))
empty_inits = [p for p in python_files if p.name == "__init__.py" and p.stat().st_size == 0]
show("14: 7 empty __init__.py files", len(empty_inits), len(empty_inits) == 7)
in_scope = len(python_files) + len(list(Path("tests").glob("*.py")))
show("14: mypy checks 25 files (src and tests)", in_scope, in_scope == 25)
tests = 0
for path in Path("tests").glob("test_*.py"):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    tests += sum(1 for n in tree.body if isinstance(n, ast.FunctionDef) and n.name[:5] == "test_")
show("14 and README: 20 tests", tests, tests == 20)

# docs/02: the seven workloads at rest
cpu = [2.4, 0.9, 0.6, 0.3, 0.25, 0.35, 0.16]
mem = [6.2, 5.1, 3.4, 1.2, 2.0, 2.6, 0.3]
show("02: 4.96 cores, 31% of 16", (round(sum(cpu), 2), round(sum(cpu) / 16 * 100)), True)
show("02: 20.8 GB, 65% of 32", (round(sum(mem), 2), round(sum(mem) / 32 * 100)), True)
parts = [round(sum(cpu[:4]) / 16 * 100), round(0.25 / 16 * 100), round(0.35 / 16 * 100)]
parts += [round(0.16 / 16 * 100), round(100 - sum(cpu) / 16 * 100)]
show("02: 26 + 2 + 2 + 1 + 69 = 100", parts, parts == [26, 2, 2, 1, 69])

# docs/03 cost, why and store status
hours = [3.42, 2.07, 1.31, 0.52, 0.31, 0.11, 0.24, 0.05]
show("03 cost: total 8.03", round(sum(hours), 2), round(sum(hours), 2) == 8.03)
show("03 cost: 16 cores x 48 min = 12.80, 62.7%", (16 * 0.8, round(8.03 / 12.8 * 100, 1)), True)
busy = 88 + 1 + 3 + 1
show("03 why: 'cpu time 91% of capacity' against reconciled busy (100 - idle 7)", busy, busy == 91)
megabytes = [212, 371, 358, 19, 23, 22, 23, 22, 31, 93, 18]
show(
    "03 store status: total 1.19 GB", sum(megabytes) / 1000, round(sum(megabytes) / 1000, 2) == 1.19
)
show("06 disk table: total 'about 1.6 GB'", (0.7 + 0.1 + 0.1 + 0.3 + 0.05, 1.1 + 0.55), True)
logging = re.findall(r"(\w+) programs", text("03-cli-output.md") + text("06-storage.md"))
three = re.findall(
    r"Three programs|3 programs", text("01-overview.md") + build + text("05-data-flow.md")
)
show(
    "03 and 06: '2 programs' keep logs, against 01/05/13 'three programs'", (logging, three), False
)
both = [
    f"{name}:{n}"
    for name in ("15-phases-and-decisions.md", "17-build-prompt.md")
    for n, line in enumerate(text(name).splitlines(), 1)
    if "oth programs" in line
]
show("15 and 17: 'both programs' run as the signed-in user", both, not both)
