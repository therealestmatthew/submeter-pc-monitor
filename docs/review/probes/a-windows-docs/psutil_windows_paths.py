"""Lists, for each psutil call the Submeter provider makes, what psutil does on Windows.

It reads the Windows module that ships in the Linux wheel (psutil/_pswindows.py) with the ast
module and reports, per method, which native calls it makes and whether each sits on the main
path or inside an except handler (a fallback). self._proc_info is cext.proc_info: one
NtQuerySystemInformation(SystemProcessInformation) query over the whole system, then a search
for one pid. It reads code only and runs nothing Windows-only.

Run from the repository root:
    uv run python docs/review/probes/a-windows-docs/psutil_windows_paths.py
"""

from __future__ import annotations

import ast
from pathlib import Path

import psutil

SOURCE = Path(psutil.__file__).with_name("_pswindows.py")
CALLED_BY_PROVIDER = (
    "create_time",
    "cpu_times",
    "memory_info",
    "_get_raw_meminfo",
    "num_threads",
    "cmdline",
    "io_counters",
    "cwd",
    "ppid",
    "name",
    "exe",
)
NATIVE = {"self._proc_info", "ppid_map", "self.exe", "self._get_raw_meminfo"}


def calls(method: ast.FunctionDef) -> list[tuple[str, int, str]]:
    """(call, line, 'main' or 'fallback') for each native call in one method."""
    in_handler: set[int] = set()
    for node in ast.walk(method):
        if isinstance(node, ast.ExceptHandler):
            in_handler.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
    found = set()
    for node in ast.walk(method):
        if isinstance(node, ast.Call):
            text = ast.unparse(node.func)
            if text.startswith("cext.") or text in NATIVE:
                found.add((text, node.lineno, "fallback" if node.lineno in in_handler else "main"))
    return sorted(found, key=lambda item: item[1])


def main() -> None:
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    process = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Process")
    methods = {n.name: n for n in process.body if isinstance(n, ast.FunctionDef)}
    print(f"psutil {psutil.__version__}, psutil/{SOURCE.name}")
    whole_system_main = []
    for name in CALLED_BY_PROVIDER:
        found = calls(methods[name])
        text = "; ".join(f"{call} line {line} {where}" for call, line, where in found)
        print(f"{name:17} {text or 'no native call'}")
        if ("self._proc_info", "main") in {(call, where) for call, _, where in found}:
            whole_system_main.append(name)
    print(f"main path is a whole-system query: {whole_system_main}")
    print("oneshot_enter body:", ast.unparse(methods["oneshot_enter"]).splitlines()[1:])


if __name__ == "__main__":
    main()
