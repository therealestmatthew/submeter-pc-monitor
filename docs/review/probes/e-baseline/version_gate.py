"""Probe: do the checks catch code that runs on the Python uv chose but not on Python 3.12?

pyproject.toml says requires-python >=3.12 and tells ruff and mypy to check as 3.12, but no
.python-version file pins the interpreter, so uv picked 3.14 here and pytest runs on 3.14.
This writes two small modules into a temporary folder (removed afterwards) beside a copy of
pyproject.toml, runs ruff, mypy, Python 3.14 and the system Python 3.12 on each, and prints
what each said. Nothing is installed. Run from the repository root:

    uv run python docs/review/probes/e-baseline/version_gate.py
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
BIN = Path(sys.executable).parent
OLD = Path("/usr/bin/python3.12")
MODULES = {
    "late_name.py": (
        "def size(item: Item) -> int:\n    return item.n\n\n\n"
        "class Item:\n    n: int = 1\n\n\nprint(size(Item()))\n"
    ),
    "bare_except.py": (
        "def parse(text: str) -> int:\n    try:\n        return int(text)\n"
        "    except ValueError, TypeError:\n        return 0\n\n\nprint(parse('x'))\n"
    ),
}


def run(folder: Path, *command: str) -> str:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", NO_COLOR="1")
    done = subprocess.run(command, cwd=folder, env=env, capture_output=True, text=True, check=False)
    lines = [line for line in (done.stdout + done.stderr).splitlines() if line.strip()]
    return f"exit {done.returncode}: {(lines[-1] if lines else '(no output)')[:80]}"


def main() -> None:
    print(f"uv's interpreter: {sys.version.split()[0]}; system 3.12 present: {OLD.exists()}")
    with tempfile.TemporaryDirectory() as name:
        folder = Path(name)
        shutil.copy(REPO / "pyproject.toml", folder / "pyproject.toml")
        for module, text in MODULES.items():
            (folder / module).write_text(text, encoding="utf-8")
            print(module)
            print("   ruff check :", run(folder, str(BIN / "ruff"), "check", "--no-cache", module))
            mypy = [str(BIN / "mypy"), "--cache-dir", str(folder / "cache"), module]
            print("   mypy       :", run(folder, *mypy))
            print("   python 3.14:", run(folder, sys.executable, module))
            if OLD.exists():
                print("   python 3.12:", run(folder, str(OLD), module))


if __name__ == "__main__":
    main()
