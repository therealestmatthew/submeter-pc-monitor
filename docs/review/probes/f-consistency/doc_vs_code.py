"""Check statements in docs/08, docs/02, docs/03 and docs/14 against what the baseline code does.

1. examples/*.toml against the samples printed in docs/08.
2. Every default and range in docs/08's sampling table, and the defaults in its other table.
3. include_children, which only examples/rules.toml uses, under the default inherit_from_parent.
4. A parent and child with the same start time (docs/16 R09 says "before", docs/14 "no later").
5. The accounting-source labels aggregate() gives, against docs/02 and docs/03.
Run from the repository root:  uv run python docs/review/probes/f-consistency/doc_vs_code.py
"""

from __future__ import annotations

import re
from pathlib import Path

from submeter.attribution.rules import SYSTEM, Attributor, Rule, RuleSet, aggregate
from submeter.core.config import Settings, load_settings
from submeter.core.models import ProcessKey, ProcessSample, SampleBatch
from submeter.core.units import parse_duration, parse_percent, parse_size

doc = Path("docs/08-configuration.md").read_text(encoding="utf-8")
blocks = re.findall(r"```toml\n(.*?)```", doc, re.S)
for block, name in zip(blocks, ("submeter.toml", "rules.toml"), strict=True):
    same = block.strip() == Path("examples", name).read_text(encoding="utf-8").strip()
    print(f"1. examples/{name} identical to the docs/08 sample: {same}")
print("   examples/submeter.toml loads:", bool(load_settings(Path("examples/submeter.toml"))))
print("   examples/rules.toml rules:", len(RuleSet.load(Path("examples/rules.toml")).rule))

print("2. docs/08 sampling table: default and range, checked by loading values")
s = Settings().sampling
for key, default, low, high in re.findall(
    r"^\| `(\w+)` \| ([^|]+?) \| (\S+) to (\S+) \|", doc, re.M
):
    if key == "overhead_limit":
        print(f"   {key}: idle {s.overhead_limit.idle}, active {s.overhead_limit.active}")
        continue
    parse = parse_percent if "%" in low else (float if key == "uss_top_n" else parse_duration)
    if key == "on_battery_multiplier":
        parse = float
    actual = getattr(s, key)
    verdicts = []
    for value in (low, high):
        try:
            Settings.model_validate(
                {"sampling": {key: value if parse is not float else float(value)}}
            )
            verdicts.append("ok")
        except ValueError:
            verdicts.append("REFUSED")
    match = abs(parse(default) - actual) < 1e-9
    print(f"   {key:<22} doc {default:<6} code {actual!s:<6} same={match} ends {verdicts}")
st = Settings()
other = {
    "retention.raw 48h": st.storage.retention.raw == parse_duration("48h"),
    "retention.minute 30d": st.storage.retention.minute == parse_duration("30d"),
    "retention.executables 1y": st.storage.retention.executables == parse_duration("1y"),
    "disk_budget 2GB": st.storage.disk_budget == parse_size("2GB"),
    "change_threshold 0.5 pt, 8MB": (st.storage.change_threshold.cpu_points, 8 * 2**20)
    == (0.5, st.storage.change_threshold.memory),
    "keyframe_interval 10m": st.storage.keyframe_interval == 600,
    "backups.keep 3": st.storage.backups.keep == 3,
    "verdict.window 5m": st.verdict.window == 300,
    "verdict.thresholds 'see verdict table'": st.verdict.thresholds,
    "alerts.rules '3 built in'": len(st.alerts.rules),
    "alerts.cooldown 15m": st.alerts.cooldown == 900,
    "attribution.unattributed_alert 10%": st.attribution.unattributed_alert == 0.10,
    "privacy.redact_patterns 'built-in list'": st.privacy.redact_patterns,
    "api.port 8787, mcp false": (st.api.port, st.api.mcp_enabled) == (8787, False),
    "ui GiB, 1h": (st.ui.units, st.ui.default_range) == ("GiB", 3600),
}
for claim, result in other.items():
    print(f"   {claim:<40} {result}")


def proc(pid: int, exe: str, parent: int | None, started: float) -> ProcessSample:
    return ProcessSample(
        key=ProcessKey(pid=pid, started=started),
        parent_pid=parent,
        exe=exe,
        cmdline=None,
        cwd=None,
        cpu_s=1.0,
        io_read_bytes=None,
        io_write_bytes=None,
        memory_bytes=1,
        threads=1,
        first_seen=False,
        restricted=pid == 9,
    )


print("3. a child (git) of a process claimed by a rule, by include_children and the global setting")
child = [proc(1, "python.exe", None, 10.0), proc(2, "git", 1, 11.0)]
for include in (False, True):
    for inherit in (True, False):
        rules = RuleSet(
            rule=(Rule(workload="builds", exe=("python.exe",), include_children=include),)
        )
        got = Attributor(rules, inherit_from_parent=inherit).assign(child)
        print(
            f"   include_children={include!s:<5} inherit_from_parent={inherit!s:<5} "
            f"-> git is {got[child[1].key].workload}"
        )

print("4. a parent and child that report the same start time")
same = [proc(1, "claude", None, 10.0), proc(2, "node", 1, 10.0)]
rules = RuleSet(rule=(Rule(workload="agent", exe=("claude",)),))
print("   child ->", Attributor(rules).assign(same)[same[1].key].workload)

print("5. accounting sources from aggregate(), with a kernel-tagged workload named")
batch = SampleBatch(
    taken_at=1.0,
    interval_s=1.0,
    gap=False,
    logical_cores=8,
    cpu_busy_s=8.0,
    memory_available_bytes=1,
    exited=(),
    processes=(proc(1, "a", None, 0.0), proc(9, "b", None, 0.0)),
)
tags = {batch.processes[0].key: "agent:x"}
assigned = Attributor(RuleSet()).assign(batch.processes, tags)
totals = aggregate(batch, assigned, kernel_workloads={"agent:x"})
for w in totals:
    print(
        f"   {w.workload:<12} source={w.source.value:<8} cpu_s={w.cpu_s} io_read={w.io_read_bytes}"
    )
print("   a 'system' row is produced:", any(w.workload == SYSTEM for w in totals))
print("   any row labelled 'counters':", any(w.source.value == "counters" for w in totals))
