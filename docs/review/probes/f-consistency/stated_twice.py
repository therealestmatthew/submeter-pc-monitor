"""Find each statement that docs/17 makes alone, or that two topic files make differently.

For each pattern it prints every line in docs/01..17 that matches, as file:line, so the report
can cite both sides. Reads docs only. Run from the repository root:
    uv run python docs/review/probes/f-consistency/stated_twice.py
"""

from __future__ import annotations

import re
from pathlib import Path

FILES = sorted(Path("docs").glob("[01][0-9]-*.md"))
CHECKS = {
    "memory budget for collector and server": r"150 MB|80 MB",
    "SQLite synchronous setting": r"synchronous",
    "when a bucket is final, idempotent rollups": r"final 30 seconds|idempotent",
    "Job Object breakaway and kill-on-close": r"breakaway|kill-on-close",
    "which files are private to the user": r"only the current user|readable only by you|only you",
    "readers accept an older schema version": r"previous versions|schema version",
    "where the Origin header is checked": r"Origin",
    "what MCP never returns": r"MCP[^.]*never|never return",
    "rules match on the parent": r"parent chain|the program that started",
    "parent link and start time": r"started before the child|no later than the child",
    "Linux child-time counters": r"child-time",
    "polled children undercounted, which platform": r"undercount",
    "what starts a new epoch": r"new epoch|starts one",
    "CPU-bound and memory-bound thresholds": r"(CPU time|Commit) above 8\d%",
    "a verdict for a healthy machine": r"No bottleneck|Healthy",
    "verdict classes listed": r"CPU-bound, memory-bound|Memory tightening",
    "accounting source of System and Restricted": (
        r"^(system|restricted) +\w+ |\| (System|Restricted) \|"
    ),
    "how hourly buckets are built": r"[Hh]ourly (buckets|rollups) (are )?(built|computed)|Build h",
    "who holds a group after the command ends": r"detached (helper|holder)|or the collector",
    "how long a run file is kept, and who reads it": r"runs/\*\.json|run files|run file",
    "the only API write": r"only write|read-only (apart|except)",
    "an ingest path for a second collector": r"ingest",
    "who runs as the signed-in user": r"[Bb]oth programs|Every program|collector and server run",
    "how many programs keep logs": r"\d programs|Each program",
}

for title, pattern in CHECKS.items():
    print(f"== {title}")
    regex = re.compile(pattern)
    for path in FILES:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if regex.search(line):
                print(f"   {path.name}:{number}: {line.strip()[:150]}")
