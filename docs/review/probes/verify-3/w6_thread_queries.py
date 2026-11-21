"""Probe W6: how many whole-system queries the psutil fallback would make per snapshot on Windows.

Two parts, both logic only (no timing):
1. Reads psutil's Windows module source in .venv with the ast module and reports which of the
   calls the provider makes reach Process._proc_info, which calls cext.proc_info (psutil's
   NtQuerySystemInformation(SystemProcessInformation) wrapper), and what oneshot() caches.
2. Runs PsutilProvider.snapshot() on this machine with Process.num_threads wrapped in a counter,
   and reports calls per snapshot against the number of processes read.

Run from the repository root:  uv run python docs/review/probes/verify-3/w6_thread_queries.py
"""

from __future__ import annotations

import ast
from pathlib import Path

import psutil

from submeter.providers.psutil_provider import PsutilProvider

CALLS_THE_PROVIDER_MAKES = ("create_time", "cpu_times", "memory_info", "num_threads", "io_counters")


def calls_in(node: ast.AST) -> list[str]:
    names = []
    for sub in ast.walk(node):
        if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
            owner = sub.func.value
            prefix = owner.id if isinstance(owner, ast.Name) else "?"
            names.append(f"{prefix}.{sub.func.attr}")
    return names


def source_part() -> None:
    path = Path(psutil.__file__).parent / "_pswindows.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    process = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Process")
    methods = {n.name: n for n in process.body if isinstance(n, ast.FunctionDef)}
    print(f"psutil {psutil.__version__}, psutil/_pswindows.py")
    print(f"_proc_info calls: {sorted(set(calls_in(methods['_proc_info'])))}")
    print(f"oneshot_enter calls: {calls_in(methods['oneshot_enter'])}")
    for name in CALLS_THE_PROVIDER_MAKES:
        body = methods.get(name)
        if body is None:
            continue
        reach = "self._proc_info" in calls_in(body)
        has_try = any(isinstance(n, ast.Try) for n in ast.walk(body))
        where = "inside an except fallback" if has_try else "on the only path"
        print(f"{name:<12} reaches _proc_info: {reach}" + (f" ({where})" if reach else ""))
    raw = methods["_get_raw_meminfo"]
    print(f"_get_raw_meminfo reaches _proc_info: {'self._proc_info' in calls_in(raw)}")


def runtime_part() -> None:
    counter = {"n": 0}
    original = psutil.Process.num_threads

    def counted(self: psutil.Process) -> int:
        counter["n"] += 1
        return original(self)

    psutil.Process.num_threads = counted  # type: ignore[method-assign]
    try:
        provider = PsutilProvider()
        for round_ in range(3):
            counter["n"] = 0
            snapshot = provider.snapshot()
            readable = sum(1 for p in snapshot.processes if not p.restricted)
            print(
                f"snapshot {round_ + 1}: {len(snapshot.processes)} processes returned, "
                f"{readable} fully readable, num_threads called {counter['n']} times"
            )
    finally:
        psutil.Process.num_threads = original  # type: ignore[method-assign]


if __name__ == "__main__":
    source_part()
    runtime_part()
