"""Verify-2 probe: the baseline attribution and aggregate paths on synthetic batches.

Clusters R3, R8, R9, R10 and R11. Builds snapshots by hand and feeds them through the
unmodified Sampler, Attributor and aggregate(), then prints what comes out:

- R8: a rule-matched process whose I/O is unreadable (None) next to one that is readable;
- R9: an agent, a shell it started and a server the shell started; the shell then exits and
  the server is reparented, once to pid 1 and once with its parent pid left stale;
- R10: aggregate() called with kernel_workloads for a workload whose figure is a polled sum;
- R11: a rule with include_children left False, under inherit_from_parent True and False;
- R3: the sum over workloads against capacity minus idle, with a busy figure the processes
  do not account for, to show what the baseline's 'reconciliation' assertion checks.

Reads and writes nothing outside memory. Run from the repository root:

    uv run python docs/review/probes/verify-2/attribution_checks.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))

from submeter.attribution.rules import Attributor, Rule, RuleSet, aggregate
from submeter.collector.sampler import Sampler
from submeter.core.models import (
    ProcessCounters,
    ProcessKey,
    SampleBatch,
    Snapshot,
    SystemCounters,
)


def proc(pid: int, cpu: float, exe: str, parent: int | None = None, **extra: object):
    fields: dict[str, object] = {"cmdline": (exe,), "memory_bytes": 1 << 20}
    fields.update(extra)
    return ProcessCounters(
        key=ProcessKey(pid=pid, started=100.0 + pid / 1000),
        parent_pid=parent,
        exe=exe,
        cpu_s=cpu,
        **fields,
    )


def snap(at: float, processes: list[ProcessCounters], busy: float = 0.0) -> Snapshot:
    system = SystemCounters(
        logical_cores=4,
        cpu_busy_s=(busy, 0.0, 0.0, 0.0),
        memory_total_bytes=1 << 34,
        memory_available_bytes=1 << 33,
    )
    return Snapshot(taken_at=at, monotonic=at, processes=tuple(processes), system=system)


def batch_of(before: list[ProcessCounters], after: list[ProcessCounters], busy=(0.0, 0.0)):
    sampler = Sampler()
    sampler.ingest(snap(1000.0, before, busy[0]))
    out = sampler.ingest(snap(1001.0, after, busy[1]))
    assert isinstance(out, SampleBatch)
    return out


def r8() -> None:
    rules = RuleSet(rule=(Rule(workload="docker", exe=("dockerd", "helper")),))
    before = [
        proc(10, 0.0, "dockerd", io_read_bytes=None, io_write_bytes=None, restricted=True),
        proc(11, 0.0, "helper", io_read_bytes=0, io_write_bytes=0),
    ]
    after = [
        proc(10, 0.5, "dockerd", io_read_bytes=None, io_write_bytes=None, restricted=True),
        proc(11, 0.1, "helper", io_read_bytes=4096, io_write_bytes=8192),
    ]
    batch = batch_of(before, after)
    assignment = Attributor(rules).assign(batch.processes)
    for w in aggregate(batch, assignment):
        print(
            f"  R8 workload {w.workload}: source={w.source.value} io_read={w.io_read_bytes} "
            f"io_write={w.io_write_bytes} (dockerd's I/O was None)"
        )


def r9() -> None:
    rules = RuleSet(rule=(Rule(workload="agent", exe=("claude",)),))
    first = [proc(20, 0.0, "claude", 1), proc(21, 0.0, "bash", 20), proc(22, 0.0, "node", 21)]
    alive = [proc(20, 1.0, "claude", 1), proc(21, 0.1, "bash", 20), proc(22, 1.0, "node", 21)]
    attributor = Attributor(rules)
    names = {
        k.pid: a.workload for k, a in attributor.assign(batch_of(first, alive).processes).items()
    }
    print(f"  R9 while the shell lives: {names}")
    for label, ppid in (("reparented to pid 1", 1), ("parent pid left stale", 21)):
        gone = [proc(20, 2.0, "claude", 1), proc(22, 2.0, "node", ppid)]
        later = batch_of([proc(20, 1.0, "claude", 1), proc(22, 1.0, "node", ppid)], gone)
        names = {k.pid: a.workload for k, a in attributor.assign(later.processes).items()}
        print(f"  R9 after the shell exits, {label}: {names}")


def r10() -> None:
    before = [proc(30, 0.0, "agent")]
    after = [proc(30, 0.4, "agent")]
    batch = batch_of(before, after, busy=(0.0, 2.0))
    tagged = {ProcessKey(pid=30, started=100.03): "agent:run"}
    assignment = Attributor(RuleSet()).assign(batch.processes, tagged)
    (w,) = aggregate(batch, assignment, kernel_workloads={"agent:run"})
    print(
        f"  R10 source={w.source.value} cpu_s={w.cpu_s:.2f}; aggregate() has these parameters: "
        f"{aggregate.__code__.co_varnames[: aggregate.__code__.co_argcount + 1]}"
    )


def r11() -> None:
    rules = RuleSet(rule=(Rule(workload="builds", exe=("make",), include_children=False),))
    before = [proc(40, 0.0, "make"), proc(41, 0.0, "cc", 40)]
    after = [proc(40, 0.1, "make"), proc(41, 0.9, "cc", 40)]
    batch = batch_of(before, after)
    for inherit in (True, False):
        got = Attributor(rules, inherit_from_parent=inherit).assign(batch.processes)
        print(
            f"  R11 include_children=False, inherit_from_parent={inherit}: child cc -> "
            f"{got[ProcessKey(pid=41, started=100.041)].workload}"
        )
    rules = RuleSet(rule=(Rule(workload="builds", exe=("make",), include_children=True),))
    got = Attributor(rules, inherit_from_parent=False).assign(batch.processes)
    print(
        f"  R11 include_children=True, inherit_from_parent=False: child cc -> "
        f"{got[ProcessKey(pid=41, started=100.041)].workload}"
    )


def r3() -> None:
    before = [proc(50, 0.0, "a"), proc(51, 0.0, "b")]
    after = [proc(50, 0.5, "a"), proc(51, 0.5, "b")]
    batch = batch_of(before, after, busy=(0.0, 3.0))
    totals = aggregate(batch, Attributor(RuleSet()).assign(batch.processes))
    summed = sum(w.cpu_s for w in totals)
    capacity = batch.logical_cores * batch.interval_s
    idle = capacity - batch.cpu_busy_s
    print(
        f"  R3 the test's check: sum over workloads {summed:.2f} == sum over processes "
        f"{sum(p.cpu_s for p in batch.processes):.2f} -> holds"
    )
    print(
        f"  R3 the brief's invariant: workloads {summed:.2f} + idle {idle:.2f} = "
        f"{summed + idle:.2f} of capacity {capacity:.2f}; the missing "
        f"{capacity - summed - idle:.2f} has no term in the baseline (no code assigns System)"
    )


def main() -> None:
    r8()
    r9()
    r10()
    r11()
    r3()


if __name__ == "__main__":
    main()
