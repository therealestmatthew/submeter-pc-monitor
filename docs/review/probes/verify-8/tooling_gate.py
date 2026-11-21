"""Verify-8, cluster B6: what the AGENTS.md checks catch in Windows-only code and in Markdown.

Writes a two-file project to a temporary folder, runs mypy and ruff from this environment on it,
and removes the folder. Nothing in the repository is read or changed. Run from the repository
root:

    uv run python docs/review/probes/verify-8/tooling_gate.py

Case 1: a function whose wrong return type sits under `if sys.platform == "win32"`, checked as
this machine runs it and again with --platform win32. Case 2: a Markdown file with a Python
block that is not ruff-formatted, under `ruff format --check`, as AGENTS.md runs it.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

WINDOWS_ONLY = """import sys

if sys.platform == "win32":

    def handle_count() -> int:
        return "not a number"
"""

NOTE = """# Note

```python
x = {  'a':1 }
```
"""


def run(folder: Path, *args: str) -> str:
    done = subprocess.run(
        [sys.executable, "-m", *args], cwd=folder, capture_output=True, text=True, check=False
    )
    last = (done.stdout.strip() or done.stderr.strip() or "(no output)").splitlines()[-1]
    return f"exit {done.returncode}; {last}"


def main() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as name:
        folder = Path(name)
        (folder / "winonly.py").write_text(WINDOWS_ONLY, encoding="utf-8")
        print("1. mypy on a Windows-only wrong return type")
        print(f"   as run here: {run(folder, 'mypy', '--no-incremental', 'winonly.py')}")
        windows = run(folder, "mypy", "--no-incremental", "--platform", "win32", "winonly.py")
        print(f"   --platform win32: {windows}")
        (folder / "winonly.py").unlink()
        (folder / "note.md").write_text(NOTE, encoding="utf-8")
        print("2. ruff format --check on a folder holding only note.md")
        print(f"   {run(folder, 'ruff', 'format', '--check')}")
        print(f"   ruff version: {run(folder, 'ruff', '--version')}")


if __name__ == "__main__":
    main()
