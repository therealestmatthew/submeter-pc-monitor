"""What the baseline stores in the field called exe on Linux, and what the sample rules match.

Run from the repository root, never as root:
    uv run python docs/review/probes/a-linux/process_names.py

Part 1 compares, for every process, psutil's name() (what the provider stores as exe), the
kernel's 15-character comm, and the file name of the real executable where it can be read.
Part 2 starts one small script three ways and shows the three names it gets.
Part 3 runs the baseline provider and attribution with examples/rules.toml, then with the
same rules given Linux names, and compares the browser rule with the browser's own cgroups.
It prints program names only, and only for programs installed in system folders.
"""

from __future__ import annotations

import os
import re
import stat
import subprocess
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

import psutil

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))

from submeter.attribution.rules import Attributor, Rule, RuleSet
from submeter.collector.sampler import Sampler
from submeter.providers.psutil_provider import PsutilProvider

REPO = Path(__file__).resolve().parents[4]
SYSTEM = ("/usr/", "/bin/", "/sbin/", "/snap/", "/opt/", "/lib/", "/nix/")
INTERPRETERS = ("python", "node", "bash", "sh", "dash", "perl", "ruby", "java", "bwrap")


def comm(pid: int) -> str:
    text = Path(f"/proc/{pid}/stat").read_text()
    return text[text.find("(") + 1 : text.rfind(")")]


def names() -> None:
    kinds, examples = Counter[str](), dict[str, set[str]]()
    longer = unreadable = total = full = 0
    for process in psutil.process_iter():
        try:
            name, short = process.name(), comm(process.pid)
            total += 1
            longer += name != short
            full += len(short) == 15
            path = os.readlink(f"/proc/{process.pid}/exe").removesuffix(" (deleted)")
        except PermissionError:
            unreadable += 1
            continue
        except (OSError, psutil.Error):
            continue
        real = os.path.basename(path)
        if name == real:
            kind = "same as the executable's file name"
        elif real.startswith(short) and len(short) == 15:
            kind = "cut to 15 characters"
        elif real.startswith(INTERPRETERS):
            kind = "a script's name, the executable is an interpreter"
        else:
            kind = "set by the program itself or by its launcher"
        kinds[kind] += 1
        if name != real and path.startswith(SYSTEM):
            examples.setdefault(kind, set()).add(f"{name!r} is {real!r}")
    print(f"1. {total} processes; the kernel's comm is 15 characters long for {full} of them")
    print(f"  psutil's name() is longer than comm, repaired from the command line: {longer}")
    print(f"  executable not readable (other users, kernel threads): {unreadable}")
    for kind, count in kinds.most_common():
        print(f"  {count:>4}  {kind}")
        for example in sorted(examples.get(kind, ()))[:6]:
            print(f"          {example}")


def three_ways() -> None:
    print("\n2. one script, started three ways (name() / comm / executable)")
    with tempfile.TemporaryDirectory() as folder:
        python = os.path.realpath(sys.executable)
        ways = (("#!interpreter", python), ("#!/usr/bin/env", "/usr/bin/env python3"))
        for label, shebang in ways:
            script = Path(folder) / "submeter-probe-long-script-name"
            script.write_text(f"#!{shebang}\nimport time\ntime.sleep(2)\n")
            script.chmod(script.stat().st_mode | stat.S_IXUSR)
            show(f"./script with {label}", [str(script)])
        show("interpreter script", [python, str(script)])


def show(label: str, command: list[str]) -> None:
    child = subprocess.Popen(command)
    time.sleep(0.5)
    real = os.path.basename(os.readlink(f"/proc/{child.pid}/exe"))
    real = "python" if real.startswith("python") else real
    print(f"  {label:<28} {psutil.Process(child.pid).name()!r} / {comm(child.pid)!r} / {real!r}")
    child.kill()
    child.wait()


def rules() -> None:
    provider, sampler = PsutilProvider(), Sampler()
    sampler.ingest(provider.snapshot())
    batch = sampler.ingest(provider.snapshot())
    assert batch is not None
    shipped = RuleSet.load(REPO / "examples" / "rules.toml")
    browsers = ("firefox", "chrome", "chromium")
    linux = RuleSet(
        rule=(
            Rule(workload="browser", priority=50, exe=browsers, include_children=True),
            Rule(workload="ide", priority=50, exe=("code",), include_children=True),
            Rule(workload="agent:untagged", priority=40, exe=("claude",), include_children=True),
        )
    )
    print("\n3. what rules claim here (processes per workload)")
    for label, rule_set in (("examples/rules.toml", shipped), ("the same with Linux names", linux)):
        assigned = Attributor(rule_set).assign(batch.processes)
        print(f"  {label}: {dict(Counter(a.workload for a in assigned.values()))}")
    assigned = Attributor(linux).assign(batch.processes)
    claimed = {key.pid for key, a in assigned.items() if a.workload == "browser"}
    in_groups, homes = set(), Counter[str]()
    for sample in batch.processes:
        try:
            group = Path(f"/proc/{sample.key.pid}/cgroup").read_text().strip()
        except OSError:
            continue
        unit = re.sub(r"[0-9a-f]{8}-[0-9a-f-]{27}|\d{3,}", "N", group.rsplit("/", 1)[-1])
        if unit.startswith(("snap.firefox", "app-com.google.Chrome", "snap.chromium")):
            in_groups.add(sample.key.pid)
        if sample.key.pid in claimed:
            homes[unit] += 1
    print(
        f"  browser: the rule claims {len(claimed)} processes; the browsers' own cgroups hold "
        f"{len(in_groups)}; in both {len(claimed & in_groups)}"
    )
    print(f"  cgroups of the processes the browser rule claims: {dict(homes)}")
    exe = {s.key.pid: s.exe for s in batch.processes}
    missed = Counter(exe[pid] for pid in in_groups - claimed)
    print(f"  in a browser's cgroup and not claimed by the rule: {dict(missed)}")
    stored = Counter(exe[pid] for pid in in_groups)
    print(f"  names stored as exe inside those cgroups: {dict(stored.most_common(8))}")


if __name__ == "__main__":
    names()
    three_ways()
    rules()
