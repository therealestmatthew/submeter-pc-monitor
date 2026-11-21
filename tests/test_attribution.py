"""Tests for attribution: which workload each process belongs to, and the totals."""

from __future__ import annotations

from collections.abc import Mapping

from submeter.attribution.rules import (
    SELF,
    UNATTRIBUTED,
    Attribution,
    Attributor,
    Rule,
    RuleSet,
)
from submeter.core.models import ProcessKey, ProcessSample

MB = 1024**2


def sample(pid: int, exe: str, parent: int | None = None, **extra: object) -> ProcessSample:
    """A process started at 100 + pid, so a lower pid is always the older process."""
    key = ProcessKey(pid=pid, started=100.0 + pid)
    fields: dict[str, object] = {"key": key, "parent_pid": parent, "exe": exe, "cmdline": (exe,)}
    fields |= {"cwd": None, "cpu_s": 0.0, "io_read_bytes": 0, "io_write_bytes": 0, "threads": 1}
    fields |= {"memory_bytes": MB, "first_seen": False, "restricted": False}
    return ProcessSample.model_validate(fields | extra)


def names(assignment: Mapping[ProcessKey, Attribution]) -> dict[int, str]:
    return {key.pid: value.workload for key, value in assignment.items()}


def test_include_children_overrides_the_global_setting_both_ways() -> None:
    rules = RuleSet(
        rule=(
            Rule(workload="builds", exe=("make",), include_children=False),
            Rule(workload="browser", exe=("chrome",), include_children=True),
            Rule(workload="ide", exe=("code",)),  # omitted: follows inherit_from_parent
        )
    )
    processes = [sample(10, "make"), sample(11, "cc", 10), sample(20, "chrome")]
    processes += [sample(21, "gpu", 20), sample(30, "code"), sample(31, "node", 30)]
    on = names(Attributor(rules, inherit_from_parent=True).assign(processes))
    off = names(Attributor(rules, inherit_from_parent=False).assign(processes))
    assert (on[11], on[21], on[31]) == (UNATTRIBUTED, "browser", "ide")
    assert (off[11], off[21], off[31]) == (UNATTRIBUTED, "browser", UNATTRIBUTED)


def test_every_submeter_pid_and_its_children_are_submeter() -> None:
    processes = [sample(10, "python"), sample(20, "python"), sample(21, "sh", 20)]
    assignment = Attributor(RuleSet(), self_pids={10, 20}).assign([*processes, sample(30, "x")])
    assert names(assignment) == {10: SELF, 20: SELF, 21: SELF, 30: UNATTRIBUTED}
