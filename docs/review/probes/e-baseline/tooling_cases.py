"""Probe: what the settings in pyproject.toml make ruff, mypy and the layer test do.

Everything is tried in a temporary folder outside the repository, which is removed. Nothing in
the repository is changed. Run from the repository root (about 20 seconds):

    uv run python docs/review/probes/e-baseline/tooling_cases.py

1. Which Python runs the checks, against what the project file says.
2. Whether `ruff format --check` and `ruff check` look inside Markdown files.
3. Whether mypy type-checks code guarded by `sys.platform == "win32"` when run on Linux.
4. Whether the layer test lets a collector loop import the raw store, as docs/14 says it will.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
BIN = Path(sys.executable).parent
MARKDOWN = "# Notes\n\n```python\nimport os\nx = {  'a':1 }\n```\n"
GUARDED = (
    "import sys\n\n\n"
    "def handles() -> int:\n"
    '    if sys.platform == "win32":\n'
    '        return "not a number"\n'
    "    return 0\n"
)
LOOP = "from submeter.store.raw import RawStore\n\n__all__ = ['RawStore']\n"


def run(folder: Path, *command: str) -> tuple[int, str]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", NO_COLOR="1")
    done = subprocess.run(command, cwd=folder, env=env, capture_output=True, text=True, check=False)
    lines = [line for line in (done.stdout + done.stderr).splitlines() if line.strip()]
    return done.returncode, (lines[-1] if lines else "(no output)")


def interpreter() -> None:
    print("1. The interpreter")
    project = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    checked, target = project["tool"]["mypy"]["python_version"], project["tool"]["ruff"]
    print(
        f"   running Python {sys.version.split()[0]}; requires-python "
        f"{project['project']['requires-python']!r}; .python-version file present: "
        f"{(REPO / '.python-version').exists()}; mypy python_version {checked!r}; "
        f"ruff target-version {target['target-version']!r}"
    )


def markdown(folder: Path) -> None:
    print("2. ruff and Markdown")
    (folder / "note.md").write_text(MARKDOWN, encoding="utf-8")
    code, last = run(folder, str(BIN / "ruff"), "format", "--check", "--no-cache", ".")
    print(f"   ruff format --check on a folder holding only note.md: exit {code}; {last}")
    code, last = run(folder, str(BIN / "ruff"), "check", "--no-cache", ".")
    print(f"   ruff check on the same folder (the block has an unused import): exit {code}; {last}")
    (folder / "note.md").unlink()


def platforms(folder: Path) -> None:
    print("3. mypy and code that runs only on Windows")
    (folder / "guarded.py").write_text(GUARDED, encoding="utf-8")
    mypy = [str(BIN / "mypy"), "--strict", "--cache-dir", str(folder / "cache"), "guarded.py"]
    for label, extra in (("as run here", []), ("with --platform win32", ["--platform", "win32"])):
        code, last = run(folder, *mypy, *extra)
        print(f"   {label}: exit {code}; {last}")
    (folder / "guarded.py").unlink()


def layers(folder: Path) -> None:
    print("4. The layer test and a collector loop that writes raw files")
    for name in ("src", "tests"):
        shutil.copytree(REPO / name, folder / name, ignore=shutil.ignore_patterns("__pycache__"))
    (folder / "src" / "submeter" / "collector" / "loop.py").write_text(LOOP, encoding="utf-8")
    pytest = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "-p",
        "no:cacheprovider",
        "tests/test_layers.py",
    ]
    code, last = run(folder, *pytest)
    print(f"   collector/loop.py imports submeter.store.raw: exit {code}; {last}")


def main() -> None:
    interpreter()
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as name:
        folder = Path(name)
        shutil.copy(REPO / "pyproject.toml", folder / "pyproject.toml")
        markdown(folder)
        platforms(folder)
        layers(folder)


if __name__ == "__main__":
    main()
