"""Probe: drive the real Attributor and aggregate() with synthetic batches.

Nothing is read from the machine and nothing is written. Run from the repository root:

    uv run python docs/review/probes/e-baseline/attribution_cases.py

Cases: a parent that exits while its child lives on, unavailable I/O, a workload labelled as
kernel-accounted, a deep process chain, a parent cycle, and ties in the sort.
"""

from __future__ import annotations

from submeter.attribution.rules import Attributor, Rule, RuleSet, aggregate
from submeter.collector.sampler import Sampler
from submeter.core.models import ProcessCounters, ProcessKey, SampleBatch, Snapshot, SystemCounters

MB = 1024**2


def proc(
    pid: int, cpu: float, *, started: float = 100.0, parent: int | None = None, **extra: object
) -> ProcessCounters:
    fields: dict[str, object] = {"exe": "tool", "cmdline": ("tool",), "memory_bytes": 50 * MB}
    fields.update(extra)
    return ProcessCounters(
        key=ProcessKey(pid=pid, started=started), parent_pid=parent, cpu_s=cpu, **fields
    )


def snap(at: float, processes: list[ProcessCounters]) -> Snapshot:
    system = SystemCounters(
        logical_cores=4,
        cpu_busy_s=(0.0, 0.0, 0.0, 0.0),
        memory_total_bytes=16 * 1024**3,
        memory_available_bytes=8 * 1024**3,
    )
    return Snapshot(taken_at=at, monotonic=at, processes=tuple(processes), system=system)


def batches(*snapshots: list[ProcessCounters]) -> list[SampleBatch]:
    sampler, found = Sampler(), []
    for index, processes in enumerate(snapshots):
        batch = sampler.ingest(snap(1000 + index, processes))
        if batch is not None:
            found.append(batch)
    return found


def parent_exits() -> None:
    print("1. A parent that exits while its child lives on (default inherit_from_parent=True)")
    rules = RuleSet(rule=(Rule(workload="agent:untagged", exe=("claude",), include_children=True),))
    agent = proc(10, 0.0, exe="claude")
    shell = proc(11, 0.0, parent=10, started=101, exe="sh")
    build = proc(12, 0.0, parent=11, started=102, exe="cc1plus")
    orphan = build.model_copy(update={"parent_pid": 1, "cpu_s": 3.0})  # reparented, as on Linux
    stale = build.model_copy(update={"cpu_s": 3.0})  # parent pid left pointing at 11, as on Windows
    init = proc(1, 0.0, started=1.0, exe="systemd")
    attributor = Attributor(rules)
    for label, later in (("reparented to pid 1", orphan), ("parent pid left stale", stale)):
        first, second = batches(
            [init, agent, shell, build],
            [init, agent, shell, build.model_copy(update={"cpu_s": 1.0})],
            [init, agent.model_copy(update={"cpu_s": 0.1}), later],  # the shell has exited
        )
        before = attributor.assign(first.processes)[build.key]
        after = attributor.assign(second.processes)[build.key]
        totals = {
            w.workload: round(w.cpu_s, 2)
            for w in aggregate(second, attributor.assign(second.processes))
        }
        print(
            f"   {label}: pid 12 was {before.workload!r} ({before.reason}), "
            f"then {after.workload!r} ({after.reason}); totals after: {totals}"
        )


def unavailable_io() -> None:
    print("2. I/O that the provider could not read (None) for a process claimed by a rule")
    rules = RuleSet(rule=(Rule(workload="docker", exe=("dockerd",)),))
    readable = {"io_read_bytes": 0, "io_write_bytes": 0}
    (batch,) = batches(
        [proc(20, 0.0, exe="dockerd", restricted=True), proc(21, 0.0, exe="other", **readable)],
        [
            proc(20, 1.0, exe="dockerd", restricted=True),
            proc(21, 1.0, exe="other", io_read_bytes=4096, io_write_bytes=8192),
        ],
    )
    for sample in batch.processes:
        print(
            f"   process {sample.exe}: io_read_bytes={sample.io_read_bytes}, "
            f"io_write_bytes={sample.io_write_bytes}"
        )
    for total in aggregate(batch, Attributor(rules).assign(batch.processes)):
        print(
            f"   workload {total.workload}: source={total.source.value}, "
            f"io_read_bytes={total.io_read_bytes}, io_write_bytes={total.io_write_bytes}"
        )


def kernel_label() -> None:
    print("3. A workload named in kernel_workloads, with a child the polling never saw")
    (batch,) = batches([proc(30, 0.0, exe="agent")], [proc(30, 0.4, exe="agent")])
    tagged = {ProcessKey(pid=30, started=100.0): "agent:refactor"}
    assignment = Attributor(RuleSet()).assign(batch.processes, tagged)
    (total,) = aggregate(batch, assignment, kernel_workloads={"agent:refactor"})
    print(
        f"   source={total.source.value}, cpu_s={total.cpu_s:g}: the label says kernel, the figure "
        "is the polled sum. aggregate() has no parameter that carries a group's own totals"
    )


def deep_chain() -> None:
    print("4. A chain of processes, each the parent of the next, that no rule matches")
    for depth, order in (
        (1500, "parents first"),
        (900, "children first"),
        (1500, "children first"),
    ):
        chain = [
            proc(pid, 0.0, parent=pid - 1 if pid > 1 else None, started=100.0 + pid)
            for pid in range(1, depth + 1)
        ]
        if order == "children first":  # as when pids are not in order of creation
            chain.reverse()
        (batch,) = batches(chain, chain)
        try:
            Attributor(RuleSet()).assign(batch.processes)
            print(f"   depth {depth}, {order}: assigned")
        except RecursionError as error:
            print(f"   depth {depth}, {order}: RecursionError: {error}")


def cycle_and_ties() -> None:
    print("5. A parent cycle, and equal CPU totals")
    loop = [proc(40, 0.0, parent=41), proc(41, 0.0, parent=40)]
    (batch,) = batches(loop, loop)
    names = {k.pid: v.workload for k, v in Attributor(RuleSet()).assign(batch.processes).items()}
    print(f"   cycle between pids 40 and 41: {names}")
    rules = RuleSet(rule=(Rule(workload="b", exe=("b",)), Rule(workload="a", exe=("a",))))
    tied = [proc(50, 0.0, exe="a"), proc(51, 0.0, exe="b")]
    (batch,) = batches(tied, [p.model_copy(update={"cpu_s": 1.0}) for p in tied])
    order = [w.workload for w in aggregate(batch, Attributor(rules).assign(batch.processes))]
    print(f"   two workloads with equal CPU sort in the order first seen: {order}")


def left_behind() -> None:
    print("6. Background processes that outlive the program a rule matched")
    rules = RuleSet(rule=(Rule(workload="agent:untagged", exe=("claude",), include_children=True),))
    agent = proc(60, 0.0, exe="claude")
    server = proc(61, 0.0, parent=60, started=101, exe="node")
    attributor = Attributor(rules)
    first, second = batches(
        [agent, server],
        [agent, server.model_copy(update={"cpu_s": 1.0})],
        [server.model_copy(update={"cpu_s": 2.0})],  # the agent has exited, its server has not
    )
    names = [attributor.assign(batch.processes)[server.key].workload for batch in (first, second)]
    print(f"   a server the agent started: {names[0]!r} while the agent runs, then {names[1]!r}")
    # A wrapper that lives for less than one interval is never in a snapshot at all.
    late = proc(63, 0.0, parent=62, started=103, exe="node")  # pid 62 came and went unseen
    (batch,) = batches([agent], [agent, late])
    seen = attributor.assign(batch.processes)[late.key]
    print(f"   a grandchild whose parent was never sampled: {seen.workload!r} ({seen.reason})")


def main() -> None:
    parent_exits()
    unavailable_io()
    kernel_label()
    deep_chain()
    cycle_and_ties()
    left_behind()


if __name__ == "__main__":
    main()
