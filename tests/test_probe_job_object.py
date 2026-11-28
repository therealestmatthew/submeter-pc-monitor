"""Probe 1, the Job Object (P0-W2-T2): its decision rule and a smoke run of steps a to e.

The script is loaded by path, because scripts/ is not a package. Every step result here is
inline and made up for the test, in the shape the probe records it; none was read from a real
machine (docs/PLAN.md 7.3.1, "Probe 1's step results, one set per decision outcome").
"""

from __future__ import annotations

import ast
import functools
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "probes" / "job_object.py"
TIMEOUT_S = 60.0  # docs/PLAN.md 7.1 rule 3: every call that starts a process passes a timeout


@functools.cache
def load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("probe_job_object", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses look their module up here
    spec.loader.exec_module(module)
    return module


def recorded(
    *,
    a: str = "pass",
    b: str = "pass",
    reopen_while_held_error: int = 0,
    reopen_after_close_error: int = 2,
    outer_cpu_s: float = 1.0469,
    burner_cpu_s: float = 1.0469,
) -> dict[str, Any]:
    """One full set of step results a to h, as the probe records them on a run that behaves.

    Made up in the probe's shape: CPU in seconds, Windows error codes as integers (0 for a
    call that succeeded, 2 for ERROR_FILE_NOT_FOUND, 5 for ERROR_ACCESS_DENIED).
    """
    job = load()
    step = job.StepResult
    return {
        "a": step("a", "create a job as the user", a, {"error": 0 if a == job.PASS else 5}),
        "b": step(
            "b",
            "create a child inside a new job",
            b,
            {"probe_in_job": True, "child_in_job": b == job.PASS},
        ),
        "c": step(
            "c",
            "job CPU against the children's GetProcessTimes",
            job.PASS,
            {"job_cpu_s": 0.9844, "children_cpu_s": 0.9844, "active_processes": 0},
        ),
        "d": step(
            "d",
            "reopen the job by name",
            job.PASS if (reopen_while_held_error, reopen_after_close_error) == (0, 2) else job.FAIL,
            {
                "reopen_while_held_error": reopen_while_held_error,
                "reopen_after_close_error": reopen_after_close_error,
            },
        ),
        "e": step("e", "breakaway without BREAKAWAY_OK", job.RECORDED, {"error": 5}),
        "f": step("f", "node, then bash, then a grandchild", job.SKIPPED, {"reason": "no node"}),
        "g": step("g", "500 children busy 5 ms", job.RECORDED, {"job_cpu_s": 11.2969}),
        "h": step(
            "h",
            "a burner in a nested job",
            job.RECORDED,
            {"outer_cpu_s": outer_cpu_s, "inner_cpu_s": burner_cpu_s, "burner_cpu_s": burner_cpu_s},
        ),
    }


def test_decision_holder_design_stands() -> None:
    # Step d as expected (opened while held, error 2 after the holder closed it) and step h's
    # outer total 1.0313 s against the burner's 1.0469 s: 1.5% short, inside 2%.
    job = load()
    decision, reason = job.decide(recorded(outer_cpu_s=1.0313, burner_cpu_s=1.0469))
    assert decision == job.STANDS == "the holder design stands"
    assert reason


def test_decision_stops_when_step_a_fails() -> None:
    job = load()
    decision, reason = job.decide(recorded(a=job.FAIL))
    assert decision == job.STOP == "stop and ask"
    assert "step a" in reason


def test_decision_stops_when_step_b_fails() -> None:
    job = load()
    decision, reason = job.decide(recorded(b=job.FAIL))
    assert decision == job.STOP == "stop and ask"
    assert "step b" in reason


def test_decision_sends_b1_to_the_owner_when_the_outer_total_is_short() -> None:
    # The outer job holds 0.9375 s of a burner that used 1.0469 s: 10.4% short, beyond 2%.
    job = load()
    decision, reason = job.decide(recorded(outer_cpu_s=0.9375, burner_cpu_s=1.0469))
    assert decision == job.OWNER == "B1 goes to the owner"
    assert "step h" in reason


def test_decision_sends_b1_to_the_owner_when_reopen_misbehaves() -> None:
    # OpenJobObjectW failed with error 2 while the holder still held its handle.
    job = load()
    decision, reason = job.decide(recorded(reopen_while_held_error=2))
    assert decision == job.OWNER == "B1 goes to the owner"
    assert "step d" in reason


def test_the_probe_never_names_silent_breakaway_ok() -> None:
    # Fixed rule 1: the probe never sets the limit that lets a child leave its job unasked.
    forbidden = "SILENT_" + "BREAKAWAY_OK"
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"), filename=str(SCRIPT))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and forbidden in node.id.upper():
            found.append(f"name {node.id} at line {node.lineno}")
        elif isinstance(node, ast.Attribute) and forbidden in node.attr.upper():
            found.append(f"attribute {node.attr} at line {node.lineno}")
        elif (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and forbidden in node.value.upper()
        ):
            found.append(f"string at line {node.lineno}")
    assert found == []


@pytest.mark.skipif(sys.platform != "win32", reason="Job Objects exist only on Windows")
def test_steps_a_to_e_run_on_windows(capsys: pytest.CaptureFixture[str]) -> None:
    # A smoke test, not evidence: the CI-W runner is an administrator (docs/PLAN.md 7.5, R118).
    job = load()
    results = [
        job.step_a(),
        job.step_b(timeout_s=TIMEOUT_S),
        job.step_c(timeout_s=TIMEOUT_S),
        job.step_d(timeout_s=TIMEOUT_S),
        job.step_e(timeout_s=TIMEOUT_S),
    ]
    with capsys.disabled():  # the CI log keeps each result, IsProcessInJob of the runner too
        print()
        for result in results:
            print(job.describe(result))
    assert [result.step for result in results] == ["a", "b", "c", "d", "e"]
    for result in results:
        assert isinstance(result, job.StepResult)
        assert result.outcome in (job.PASS, job.FAIL, job.RECORDED), job.describe(result)
