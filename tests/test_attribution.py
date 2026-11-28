"""Tests for attribution: which workload each process belongs to, and the totals."""

from __future__ import annotations

from pathlib import Path

import pytest
from builders import MB, names, proc, sample, snap

from submeter.attribution.rules import (
    RESTRICTED,
    SELF,
    UNATTRIBUTED,
    Attributor,
    Rule,
    RuleSet,
    aggregate,
)
from submeter.collector.sampler import Sampler
from submeter.core.models import GroupTotals, ProcessKey, SampleBatch


def test_attribution_order_inheritance_and_conservation() -> None:
    rules = RuleSet(
        rule=(
            Rule(workload="tools", exe=("tool",), priority=1),
            Rule(workload="browser", exe=("chrome.exe",), priority=5, include_children=True),
        )
    )
    sampler = Sampler()
    before = [
        proc(10, 0, exe=r"C:\Apps\chrome.exe"),
        proc(11, 0, parent=10, started=101, exe="helper"),
        proc(12, 0, parent=10, started=99, exe="older"),
        proc(13, 0, exe="mystery", restricted=True, cmdline=None),
        proc(14, 0),
        proc(15, 0, exe="agent"),
    ]
    sampler.ingest(snap(1000, before))
    after = [p.model_copy(update={"cpu_s": 0.1 * (i + 1)}) for i, p in enumerate(before)]
    batch = sampler.ingest(snap(1001, after))
    assert batch is not None
    tagged = {ProcessKey(pid=15, started=100.0): "agent:refactor"}
    assignment = Attributor(rules, inherit_from_parent=False).assign(batch.processes, tagged)
    names = {key.pid: value.workload for key, value in assignment.items()}
    assert names == {
        10: "browser",
        11: "browser",
        12: UNATTRIBUTED,
        13: RESTRICTED,
        14: "tools",
        15: "agent:refactor",
    }
    group = GroupTotals(cpu_s=0.9, io_read_bytes=None, io_write_bytes=None, processes=1)
    totals = aggregate(batch, assignment, kernel_workloads={"agent:refactor": group})
    polled = [total for total in totals if total.workload != "agent:refactor"]
    assert sum(total.cpu_s for total in polled) == pytest.approx(
        sum(sample.cpu_s for sample in batch.processes if sample.key.pid != 15)
    )
    tagged_total = next(total for total in totals if total.workload == "agent:refactor")
    assert (tagged_total.cpu_s, tagged_total.source.value) == (0.9, "kernel")  # polled sum 0.6


def test_rules_file_loads_and_rejects_empty_rules(tmp_path: Path) -> None:
    file = tmp_path / "rules.toml"
    file.write_text(
        '[[rule]]\nworkload = "ide"\npriority = 50\nexe = ["Code.exe"]\n'
        "[[rule]]\nworkload = \"builds\"\ncwd = 'C:\\src\\**'\n"
    )
    assert [rule.workload for rule in RuleSet.load(file).ordered()] == ["ide", "builds"]
    assert (
        RuleSet.load(file).needs_cwd
        and not RuleSet(rule=(Rule(workload="a", exe=("a",)),)).needs_cwd
    )
    with pytest.raises(ValueError, match="at least one of"):
        Rule(workload="nothing")


def test_a_rule_can_match_on_the_parent_program() -> None:
    rules = RuleSet(rule=(Rule(workload="from-shell", parent=("Explorer.EXE",)),))
    started = [
        proc(20, 0, exe=r"C:\Windows\explorer.exe"),
        proc(21, 0, parent=20, started=101, exe="notepad.exe"),
        proc(22, 0, parent=20, started=99, exe="older.exe"),  # pid 20 was reused: not its parent
        proc(23, 0, exe="orphan.exe"),
    ]
    sampler = Sampler()
    sampler.ingest(snap(1000, started))
    batch = sampler.ingest(snap(1001, started))
    assert batch is not None
    assignment = Attributor(rules, inherit_from_parent=False).assign(batch.processes)
    assert {key.pid: value.workload for key, value in assignment.items()} == {
        20: UNATTRIBUTED,
        21: "from-shell",
        22: UNATTRIBUTED,
        23: UNATTRIBUTED,
    }


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


def test_a_pid_registered_after_its_first_batch_moves_to_submeter() -> None:
    attributor = Attributor(RuleSet(rule=(Rule(workload="agent", exe=("bash",)),)), self_pids=[10])
    holder = sample(20, "python", 5)  # started by an agent's shell before its pid is known
    assert names(attributor.assign([sample(5, "bash"), holder]))[20] == "agent"
    attributor.set_self_pids({10, 20})
    assert names(attributor.assign([sample(5, "bash"), holder]))[20] == SELF
    assert attributor.changes == [(holder.key, "agent", SELF)]


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


@pytest.mark.xfail(
    strict=True,
    reason="R61 known breach: WorkloadSample cannot say unavailable until R42's planned task",
)
def test_a_group_polling_never_saw_reports_its_io_and_memory_unavailable() -> None:
    batch = SampleBatch.model_validate(
        {"taken_at": 1001.0, "interval_s": 1.0, "gap": False, "processes": ()}
        | {"exited": (), "logical_cores": 4, "cpu_busy_s": 1.0, "memory_available_bytes": MB}
    )
    group = GroupTotals(cpu_s=0.6, io_read_bytes=None, io_write_bytes=None, processes=2)
    (total,) = aggregate(batch, {}, kernel_workloads={"agent:run": group})
    assert total.cpu_s == pytest.approx(0.6)
    fields: tuple[object, ...] = (total.io_read_bytes, total.io_write_bytes, total.memory_bytes)
    assert fields == (None, None, None)
