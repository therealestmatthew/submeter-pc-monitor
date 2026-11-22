"""Tests for attribution: which workload each process belongs to, and the totals."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from submeter.attribution.rules import (
    SELF,
    UNATTRIBUTED,
    Attribution,
    Attributor,
    Rule,
    RuleSet,
    aggregate,
)
from submeter.core.models import GroupTotals, ProcessKey, ProcessSample, SampleBatch

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


def test_an_inherited_workload_lasts_for_the_life_of_the_process() -> None:
    rules = RuleSet(
        rule=(
            Rule(workload="agent", exe=("bash",)),
            Rule(workload="services", parent=("systemd",)),
            Rule(workload="db", exe=("postgres",)),
        )
    )
    attributor = Attributor(rules)
    kids = [sample(21, "node", 20), sample(22, "vite", 20), sample(23, "sh", 20)]
    first = names(attributor.assign([sample(1, "systemd"), sample(20, "bash"), *kids]))
    # The shell exits: 21 keeps a stale parent pid, 22 is re-parented to systemd, 23 execs.
    later = [sample(1, "systemd"), kids[0], sample(22, "vite", 1), sample(23, "postgres", 20)]
    second = names(attributor.assign(later))
    assert [first[pid] for pid in (21, 22, 23)] == ["agent"] * 3
    assert [second[pid] for pid in (21, 22, 23)] == ["agent", "agent", "db"]
    assert attributor.changes == [(ProcessKey(pid=23, started=123.0), "agent", "db")]
    gone = names(attributor.assign(later[:3], exited=[kids[1].key]))  # forgotten once exited
    assert (gone[21], gone[22]) == ("agent", "services")
    attributor.assign(later[:3], {kids[0].key: "agent:run"})  # 21 joins a kernel group late
    assert attributor.changes == [(kids[0].key, "agent", "agent:run")]


def test_capacity_reconciles_with_a_not_seen_by_polling_term() -> None:
    processes = [sample(20, "bash", cpu_s=0.2), sample(30, "agent", cpu_s=0.3), sample(40, "x")]
    batch = SampleBatch.model_validate(
        {"taken_at": 1001.0, "interval_s": 1.0, "gap": False, "processes": processes}
        | {"exited": (), "logical_cores": 4, "cpu_busy_s": 1.5, "memory_available_bytes": MB}
    )
    rules = RuleSet(rule=(Rule(workload="agent", exe=("bash",)),))
    assignment = Attributor(rules).assign(processes, {processes[1].key: "agent:run"})
    group = GroupTotals(cpu_s=0.6, io_read_bytes=None, io_write_bytes=None, processes=2)
    totals = aggregate(batch, assignment, kernel_workloads={"agent:run": group})
    capacity = batch.interval_s * batch.logical_cores
    workloads = sum(total.cpu_s for total in totals)  # the group's 0.6, not the polled 0.3
    idle, system = capacity - batch.cpu_busy_s, 0.0  # nothing is assigned to System yet
    not_seen = batch.cpu_busy_s - workloads - system
    assert min(capacity, idle, workloads, system, not_seen) >= 0
    assert idle + workloads + system + not_seen == pytest.approx(capacity)
    assert not_seen == pytest.approx(0.7)
