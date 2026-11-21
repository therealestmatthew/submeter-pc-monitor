"""Probe: what tests/test_layers.py enforces, and what it lets through.

Copies src/ and tests/test_layers.py into a temporary folder, adds one small module per case,
runs the layer test's own function against that copy, and prints whether it passed. Nothing in
the repository changes, and the temporary folder is removed. Run from the repository root:

    uv run python docs/review/probes/g-buildability/layer_rule_cases.py

Cases: imports written in forms the test does not parse, a new package missing from LAYER,
and imports between the three programs once they have packages of their own.
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import ModuleType

REPO = Path(__file__).resolve().parents[4]

CASES: list[tuple[str, str, str]] = [
    ("baseline as delivered", "", ""),
    (
        "collector imports the raw store, absolute",
        "collector/loop.py",
        "import submeter.store.raw\n",
    ),
    (
        "collector imports the raw store, relative",
        "collector/loop.py",
        "from ..store.raw import RawStore\n\n__all__ = ['RawStore']\n",
    ),
    ("core imports the store package by name", "core/peek.py", "from submeter import store\n"),
    (
        "core imports cli through importlib",
        "core/peek.py",
        "import importlib\n\ncli = importlib.import_module('submeter.cli')\n",
    ),
    ("new package server, not in LAYER", "server/app.py", "import submeter.store.rollup\n"),
]

PROGRAM_CASES: list[tuple[str, str, str]] = [
    ("launcher imports the collector", "launcher/run.py", "import submeter.collector.sampler\n"),
    ("server imports the collector", "server/app.py", "import submeter.collector.sampler\n"),
]


def load_layer_test(folder: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("copied_layers", folder / "test_layers.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.SOURCE = folder / "src" / "submeter"
    return module


def prepare(folder: Path, path: str, text: str) -> None:
    if folder.exists():
        shutil.rmtree(folder)
    shutil.copytree(REPO / "src", folder / "src", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(REPO / "tests" / "test_layers.py", folder / "test_layers.py")
    if path:
        target = folder / "src" / "submeter" / path
        target.parent.mkdir(parents=True, exist_ok=True)
        (target.parent / "__init__.py").touch()
        target.write_text(text, encoding="utf-8")


def verdict(module: ModuleType) -> str:
    try:
        module.test_no_module_imports_from_a_higher_layer()
    except AssertionError as error:
        return f"FAILS ({error})"
    except KeyError as error:
        return f"ERROR KeyError {error}"
    return "passes"


def really_imports(folder: Path, dotted: str) -> str:
    env = dict(os.environ, PYTHONPATH=str(folder / "src"), PYTHONDONTWRITEBYTECODE="1")
    code = f"import {dotted}, submeter; print(submeter.__file__.startswith({str(folder)!r}))"
    done = subprocess.run(
        [sys.executable, "-c", code], env=env, capture_output=True, text=True, check=False
    )
    return f"exit {done.returncode}, loaded from the copy: {done.stdout.strip() or '?'}"


def main() -> None:
    with tempfile.TemporaryDirectory() as name:
        folder = Path(name) / "copy"
        print("1. forms of import, layer table as delivered")
        for label, path, text in CASES:
            prepare(folder, path, text)
            line = f"   {label}: layer test {verdict(load_layer_test(folder))}"
            if "relative" in label:
                line += f"; module {really_imports(folder, 'submeter.collector.loop')}"
            print(line)
        print("2. the three programs as packages, with server and launcher added at layer 3")
        for label, path, text in PROGRAM_CASES:
            prepare(folder, path, text)
            module = load_layer_test(folder)
            module.LAYER.update({"server": 3, "launcher": 3})
            print(f"   {label}: layer test {verdict(module)}")
        print("3. what the delivered cli.py imports, as the layer test reads it")
        prepare(folder, "", "")
        module = load_layer_test(folder)
        found = sorted(module.imports_of(folder / "src" / "submeter" / "cli.py"))
        print(f"   {', '.join(found)}")
        print(f"   LAYER keys: {', '.join(module.LAYER)}")


if __name__ == "__main__":
    main()
