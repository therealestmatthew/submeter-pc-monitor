"""Is ProcessKey (pid plus psutil's float start time) the same wherever it is computed?

Run from the repository root:
    uv run python docs/review/probes/a-linux/process_identity.py

Part 1 computes the start time of every process here, in a second Python process, and straight
from /proc/PID/stat field 22 plus the btime line of /proc/stat. Part 2 shows what btime is made
of and which clock field 22 counts on. Parts 3 and 4 simulate a step of the wall clock by
replacing the two functions that read it (psutil's boot time and time.time) inside this probe,
and run the baseline provider, sampler and attribution across the step. Part 5 ages the object
psutil caches for one pid, the way psutil's own tests imitate a reused pid.
Nothing on the machine is changed: the clock is never touched.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import psutil

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "src"))

from submeter.attribution.rules import Attributor, RuleSet
from submeter.collector.sampler import Sampler
from submeter.core.models import SampleBatch
from submeter.providers.psutil_provider import PsutilProvider

TICK = os.sysconf("SC_CLK_TCK")
OTHER = (
    "import json, psutil\n"
    "print(json.dumps({p.pid: p.create_time().hex() for p in psutil.process_iter()}))"
)
BUSY = "x = 0\nfor i in range(2000000): x += i * i\nimport time; time.sleep(30)"
SPIN = "import time\nwhile True: sum(i * i for i in range(20000)); time.sleep(0.001)"


def boot_line() -> int:
    for line in Path("/proc/stat").read_text().splitlines():
        if line.startswith("btime"):
            return int(line.split()[1])
    raise RuntimeError("no btime line")


def start_ticks(pid: int) -> int:
    stat = Path(f"/proc/{pid}/stat").read_text()
    return int(stat[stat.rfind(")") + 2 :].split()[19])


@contextmanager
def clock_step(btime_s: float, wall_s: float) -> Iterator[None]:
    """Pretend the wall clock was stepped: psutil's boot time and time.time both move."""
    real_boot, real_time = psutil._pslinux.boot_time, time.time
    psutil._pslinux.boot_time = lambda: real_boot() + btime_s
    time.time = lambda: real_time() + wall_s
    try:
        yield
    finally:
        psutil._pslinux.boot_time, time.time = real_boot, real_time


def same_everywhere() -> None:
    here = {p.pid: p.create_time() for p in psutil.process_iter()}
    reply = subprocess.run([sys.executable, "-c", OTHER], capture_output=True, text=True).stdout
    there = {int(pid): float.fromhex(text) for pid, text in json.loads(reply).items()}
    both = here.keys() & there.keys()
    equal = sum(1 for pid in both if here[pid] == there[pid])
    print("1. the same processes, three ways")
    print(f"  two Python processes: {equal} of {len(both)} start times identical to the last bit")
    btime, as_psutil, other_order, total = boot_line(), 0, 0, 0
    for pid, value in here.items():
        try:
            ticks = start_ticks(pid)
        except OSError:
            continue
        total += 1
        as_psutil += value == float(ticks) / TICK + float(btime)
        other_order += value == (ticks + btime * TICK) / TICK
    print(f"  /proc read, start ticks / {TICK} + btime: {as_psutil} of {total} identical")
    print(f"  /proc read, (start ticks + btime x {TICK}) / {TICK}: {other_order} of {total}")


def what_btime_is() -> None:
    boottime, monotonic = time.clock_gettime(time.CLOCK_BOOTTIME), time.monotonic()
    offset = time.time() - boottime
    child = subprocess.Popen(["/bin/sleep", "1"])
    born = start_ticks(child.pid) / TICK
    on_boottime = abs(born - time.clock_gettime(time.CLOCK_BOOTTIME))
    on_monotonic = abs(born - time.monotonic())
    child.wait()
    print("\n2. what the start time is made of")
    print(f"  btime equals floor(wall clock - time since boot): {boot_line() == int(offset)}")
    print(
        f"  the fraction dropped is {offset % 1:.3f} s, so a step forward of {1 - offset % 1:.3f} s"
        f" or back of {offset % 1:.3f} s moves btime, and every start time, by a whole second"
    )
    print(
        f"  field 22 of a child started now is {on_boottime:.2f} s from CLOCK_BOOTTIME and "
        f"{on_monotonic:.0f} s from time.monotonic()"
    )
    print(
        f"  time this machine has spent suspended since boot: {abs(boottime - monotonic):.0f} s,"
        " and the two clocks differ by exactly that"
    )
    print(f"  time.monotonic() is {time.get_clock_info('monotonic').implementation}")


def across_a_step_back() -> None:
    provider, sampler, attributor = PsutilProvider(), Sampler(), Attributor(RuleSet())
    me = os.getpid()
    sampler.ingest(provider.snapshot())

    def child_workload(label: str) -> None:
        child = subprocess.Popen([sys.executable, "-S", "-c", BUSY])
        time.sleep(1.0)
        batch = sampler.ingest(provider.snapshot())
        assert batch is not None
        by_pid = {sample.key.pid: sample for sample in batch.processes}
        mine, its = by_pid[me], by_pid[child.pid]
        assigned = attributor.assign(batch.processes, tagged={mine.key: "tagged"})
        used = psutil.Process(child.pid).cpu_times()
        print(
            f"  {label}: child's start minus its parent's {its.key.started - mine.key.started:+.0f}"
            f" s, workload '{assigned[its.key].workload}', gap {batch.gap}, "
            f"CPU credited {its.cpu_s:.2f} s of {used.user + used.system:.2f} s"
        )
        child.kill()
        child.wait()

    print(
        "\n3. the baseline while the wall clock is set back one hour (the collector keeps running)"
    )
    child_workload("before the step       ")
    cached = {p.pid: p.create_time() for p in psutil.process_iter()}
    with clock_step(-3600.0, -3600.0):
        child_workload("interval with the step")
        child_workload("a later interval      ")
        fresh = {pid: psutil.Process(pid).create_time() for pid in cached if psutil.pid_exists(pid)}
    moved = sum(1 for pid, value in fresh.items() if value != cached[pid])
    print(
        f"  keys a program started after the step would compute: {moved} of {len(fresh)} differ "
        "from the ones the running collector holds"
    )


def counts(batch: SampleBatch | None) -> str:
    assert batch is not None
    seen = sum(1 for sample in batch.processes if sample.first_seen)
    credited = sum(sample.cpu_s for sample in batch.processes)
    return (
        f"{len(batch.processes)} processes, {seen} counted as started, {len(batch.exited)} as "
        f"exited, {credited:.2f} CPU-s credited of {batch.cpu_busy_s:.2f} busy, gap {batch.gap}"
    )


def start_time_worked_out_each_tick() -> None:
    """A reader that adds btime to field 22 at every tick, imitated by emptying psutil's cache."""
    provider, sampler = PsutilProvider(), Sampler()
    burner = subprocess.Popen([sys.executable, "-S", "-c", SPIN])

    def tick() -> SampleBatch | None:
        time.sleep(1.0)
        psutil.process_iter.cache_clear()
        return sampler.ingest(provider.snapshot())

    tick()
    print("\n4. a provider that works out the start time afresh at every tick")
    print(f"  a normal interval:       {counts(tick())}")
    with clock_step(-1.0, -0.3):
        print(f"  btime one second lower:  {counts(tick())}")
        print(f"  the interval after that: {counts(tick())}")
    burner.kill()
    burner.wait()


def reused_pid() -> None:
    provider, sampler = PsutilProvider(), Sampler()
    child = subprocess.Popen([sys.executable, "-S", "-c", SPIN])
    time.sleep(0.3)
    sampler.ingest(provider.snapshot())
    held = psutil._pmap[child.pid]
    true_start = held.create_time()
    held._ident = (child.pid, held._ident[1] - 100.0)  # the cache now holds "an older process"
    held._create_time = true_start - 100.0
    print("\n5. a pid reused between two snapshots (imitated by ageing psutil's cached object)")
    credited = 0.0
    for number in (1, 2, 3):
        time.sleep(1.0)
        batch = sampler.ingest(provider.snapshot())
        assert batch is not None
        found = [sample for sample in batch.processes if sample.key.pid == child.pid]
        if not found:
            print(f"  snapshot {number}: the process is missing from the snapshot")
            continue
        sample = found[0]
        credited += sample.cpu_s
        print(
            f"  snapshot {number}: present, key has the true start time: "
            f"{sample.key.started == true_start}, first seen {sample.first_seen}, "
            f"CPU credited {sample.cpu_s:.2f} s"
        )
    used = psutil.Process(child.pid).cpu_times()
    print(
        f"  credited {credited:.2f} s in three intervals; it used {used.user + used.system:.2f} s"
    )
    child.kill()
    child.wait()


if __name__ == "__main__":
    same_everywhere()
    what_btime_is()
    across_a_step_back()
    start_time_worked_out_each_tick()
    reused_pid()
