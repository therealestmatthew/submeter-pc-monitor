"""Tests of the project settings in pyproject.toml. Run with: uv run pytest"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"

MARKS = {"owner_machine", "session", "hardware", "soak"}
SYNC = "uv sync --locked"
AGENTS_CHECKS = (
    SYNC,
    "uv run ruff check",
    "uv run ruff format --check",
    "uv run mypy src tests",
    "uv run mypy --platform win32 src tests",
    "uv run mypy --platform linux src tests",
    "uv run pytest",
)
AFTER_SYNC = "if: ${{ !cancelled() && steps.sync.outcome == 'success' }}"
RUNNERS = {"windows-2025": "gate-windows", "ubuntu-24.04": "gate-linux"}


def project_settings() -> dict[str, Any]:
    with PYPROJECT.open("rb") as file:
        return tomllib.load(file)


def pytest_settings() -> dict[str, Any]:
    settings: dict[str, Any] = project_settings()["tool"]["pytest"]["ini_options"]
    return settings


def test_python_floor_is_3_13() -> None:
    """Python 3.13 is the first whose time.monotonic() on Windows resolves 1 microsecond (R124)."""
    assert project_settings()["project"]["requires-python"] == ">=3.13"


def test_ruff_leaves_markdown_alone() -> None:
    """The brief's Markdown is not Python to format; ruff format would rewrite it (R134)."""
    assert "*.md" in project_settings()["tool"]["ruff"].get("extend-exclude", [])


def test_markers_are_registered_and_strict() -> None:
    """The four marks of docs/PLAN.md 7.1 are registered, and an unknown mark is an error (R118)."""
    settings = pytest_settings()
    lines: list[str] = settings.get("markers", [])
    assert {line.split(":", 1)[0].strip() for line in lines} == MARKS
    assert len(lines) == len(MARKS)
    addopts: str | list[str] = settings.get("addopts", [])
    args = shlex.split(addopts) if isinstance(addopts, str) else addopts
    assert "--strict-markers" in args


def run_pytest(folder: Path, basetemp: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    env = {key: value for key, value in os.environ.items() if not key.startswith("PYTEST_")}
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-c",
            str(PYPROJECT),
            f"--rootdir={folder}",
            f"--basetemp={basetemp}",
            "-p",
            "no:cacheprovider",
            "-v",
            *extra,
            str(folder / "test_sample.py"),
        ],
        cwd=folder,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )


def test_plain_pytest_deselects_the_marked_tests(tmp_path: Path) -> None:
    """A plain run leaves a `soak` test out, and `-m soak` runs it (docs/PLAN.md 3.1, OS)."""
    folder = tmp_path / "sample"
    folder.mkdir()
    (folder / "test_sample.py").write_text(
        "import pytest\n\n\n"
        "def test_unmarked() -> None:\n    pass\n\n\n"
        "@pytest.mark.soak\n"
        "def test_marked_soak() -> None:\n    pass\n",
        encoding="utf-8",
    )

    plain = run_pytest(folder, tmp_path / "plain")
    output = plain.stdout + plain.stderr
    assert plain.returncode == 0, output
    assert "1 passed, 1 deselected" in output, output
    assert "test_unmarked PASSED" in output, output
    assert "test_marked_soak" not in output, output

    soak = run_pytest(folder, tmp_path / "soak", "-m", "soak")
    output = soak.stdout + soak.stderr
    assert soak.returncode == 0, output
    assert "1 passed, 1 deselected" in output, output
    assert "test_marked_soak PASSED" in output, output
    assert "test_unmarked" not in output, output


def indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def jobs_and_steps(text: str) -> list[tuple[str, list[str]]]:
    """Split a workflow into (job text, its steps' texts), by indentation, without a YAML parser."""
    lines = text.splitlines()
    jobs_at = next(i for i, line in enumerate(lines) if line.rstrip() == "jobs:")
    body = lines[jobs_at + 1 :]
    job_indent = min(indent_of(line) for line in body if line.strip())
    starts = [
        i
        for i, line in enumerate(body)
        if line.strip() and indent_of(line) == job_indent and not line.lstrip().startswith("#")
    ]
    found: list[tuple[str, list[str]]] = []
    for start, end in zip(starts, [*starts[1:], len(body)], strict=True):
        job = body[start:end]
        steps_at = next(i for i, line in enumerate(job) if line.strip() == "steps:")
        step_lines = [line for line in job[steps_at + 1 :] if line.strip()]
        item_indent = indent_of(step_lines[0])
        steps: list[list[str]] = []
        for line in step_lines:
            if indent_of(line) < item_indent:
                break
            if indent_of(line) == item_indent and line.lstrip().startswith("- "):
                steps.append([])
            steps[-1].append(line)
        found.append(("\n".join(job), ["\n".join(step) for step in steps]))
    return found


def test_ci_runs_every_agents_check_on_both_systems() -> None:
    """ci.yml runs the seven AGENTS.md checks on Windows and Linux, each after a failure (R134)."""
    text = CI_WORKFLOW.read_text(encoding="utf-8")
    for check in AGENTS_CHECKS:
        assert check in text, check
    for label, artefact in RUNNERS.items():
        assert label in text, label
        assert artefact in text, artefact
    assert "SUBMETER_GATE_DIR" in text
    assert "--continue-on-collection-errors" in text
    assert "cancel-in-progress" not in text
    assert "continue-on-error" not in text
    # Python 3.13 installed by uv on both runners, never the runner image's own interpreter.
    assert re.search(r"^env:\n(?:  .*\n)*?  UV_PYTHON_PREFERENCE: only-managed\n", text, re.M), text

    jobs = jobs_and_steps(text)
    seen_labels: set[str] = set()
    for job, steps in jobs:
        runs_on = re.search(r"^\s*runs-on:\s*(\S+)\s*$", job, re.MULTILINE)
        assert runs_on is not None, job
        runner = runs_on.group(1)
        assert runner in RUNNERS, runner
        seen_labels.add(runner)
        assert re.search(r"^\s*timeout-minutes:\s*30\s*$", job, re.MULTILINE), job
        sync_at = [i for i, step in enumerate(steps) if re.search(r"\bid:\s*sync\s*$", step, re.M)]
        assert len(sync_at) == 1, steps
        assert SYNC in steps[sync_at[0]]
        after = steps[sync_at[0] + 1 :]
        assert after, f"no step after sync in the {runner} job"
        for step in after:
            assert AFTER_SYNC in step, step
        for check in AGENTS_CHECKS[1:]:
            assert any(check in step for step in after), (runner, check)
        assert any("--continue-on-collection-errors" in step for step in after)
        assert any("SUBMETER_GATE_DIR" in step for step in after)
        assert any(RUNNERS[runner] in step for step in after)
        assert "git status --porcelain" in after[-1]
    assert seen_labels == set(RUNNERS)
    assert len(jobs) == len(RUNNERS)
