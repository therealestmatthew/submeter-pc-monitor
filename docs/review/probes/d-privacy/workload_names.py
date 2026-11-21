"""Which workload names does the baseline accept, and can a rule or a tag claim a reserved one?

Run:  uv run python docs/review/probes/d-privacy/workload_names.py

A workload name comes from rules.toml or from `submeter run --as NAME`. It becomes a Job Object
or cgroup name, part of a file name, text in the dashboard and a field in MCP answers. The
brief reserves `machine` and `submeter` for alert rules and always shows system, restricted
and unattributed. The probe builds rules with awkward names and totals one small batch.
"""

from __future__ import annotations

from pydantic import ValidationError

from submeter.attribution.rules import Attributor, Rule, RuleSet, aggregate
from submeter.collector.sampler import Sampler
from submeter.core.models import ProcessCounters, ProcessKey, Snapshot, SystemCounters

NAMES = ["system", "restricted", "unattributed", "submeter", "machine", "", "a\nb", "../../x"]
NAMES += ["agent:*", '<img src=x onerror="alert(1)">', "x" * 300]


def snapshot(at: float, cpu: float) -> Snapshot:
    system = SystemCounters(
        logical_cores=4,
        cpu_busy_s=(cpu, 0.0, 0.0, 0.0),
        memory_total_bytes=2**34,
        memory_available_bytes=2**33,
    )
    processes = (
        ProcessCounters(key=ProcessKey(pid=1, started=1.0), exe="miner", cpu_s=cpu, memory_bytes=1),
        ProcessCounters(
            key=ProcessKey(pid=2, started=1.0), exe="tagged", cpu_s=cpu, memory_bytes=1
        ),
    )
    return Snapshot(taken_at=at, monotonic=at, processes=processes, system=system)


def main() -> None:
    for name in NAMES:
        try:
            Rule(workload=name, exe=("tool",))
            verdict = "accepted"
        except ValidationError:
            verdict = "refused"
        print(f"  {verdict}: rule with workload = {name[:40]!r}")
    sampler = Sampler()
    sampler.ingest(snapshot(1000.0, 1.0))
    batch = sampler.ingest(snapshot(1001.0, 1.5))
    assert batch is not None
    rules = RuleSet(rule=(Rule(workload="system", exe=("miner",)),))
    tagged = {ProcessKey(pid=2, started=1.0): "submeter"}  # as from: submeter run --as submeter
    totals = aggregate(batch, Attributor(rules).assign(batch.processes, tagged))
    for total in totals:
        print(
            f"  workload {total.workload!r}: {total.cpu_s:.1f} CPU-s from {total.processes} process"
        )


if __name__ == "__main__":
    main()
