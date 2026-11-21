"""Probe (Linux): what each term of the reconciliation invariant would hold on this machine,
under the two ways "System" could be defined, and how fine the CPU counters are.

Reads /proc only and starts nothing. Every figure is CPU time counted by the kernel, not speed.

    uv run python docs/review/probes/b-measurement/reconcile_terms.py [SECONDS]

It polls every second for SECONDS (default 20) the way the baseline sampler does: a process
seen twice is credited its delta, one born since the last poll is credited everything. It then
splits the machine's busy time into what processes account for and what nothing accounts for.
"""

from __future__ import annotations

import os
import sys
import time

TICK = os.sysconf("SC_CLK_TCK")
KERNEL_THREAD = 0x00200000  # PF_KTHREAD, in the flags field of /proc/PID/stat
Row = tuple[float, float, bool]


def machine() -> dict[str, float]:
    with open("/proc/stat") as handle:
        parts = handle.readline().split()[1:]
    names = ("user", "nice", "system", "idle", "iowait", "irq", "softirq", "steal")
    return {name: int(value) / TICK for name, value in zip(names, parts, strict=False)}


def processes() -> dict[tuple[int, int], Row]:
    """(pid, start tick) -> own CPU seconds, reaped children's CPU seconds, is a kernel thread."""
    found: dict[tuple[int, int], Row] = {}
    for name in os.listdir("/proc"):
        if not name.isdigit():
            continue
        try:
            with open(f"/proc/{name}/stat", "rb") as handle:
                data = handle.read()
        except OSError:
            continue
        fields = data[data.rfind(b")") + 2 :].split()
        own = (int(fields[11]) + int(fields[12])) / TICK
        reaped = (int(fields[13]) + int(fields[14])) / TICK
        kernel = bool(int(fields[6]) & KERNEL_THREAD)
        found[(int(name), int(fields[19]))] = (own, reaped, kernel)
    return found


def main() -> int:
    seconds = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    cores = os.cpu_count() or 1
    load, tick_ms = os.getloadavg()[0], 1000 // TICK
    print(f"{cores} logical cores; load average {load:.2f}; one tick is {tick_ms} ms")
    print(
        f"hot threshold 0.5% of a core over 1 s is {5.0 / tick_ms:.1f} tick, so the smallest "
        f"use that can be seen in one second is {100 / TICK:.0f}% of a core; over 250 ms it is "
        f"{400 / TICK:.0f}%"
    )
    fine = os.path.exists("/proc/self/schedstat")
    print(f"nanosecond run time per process (schedstat) present: {fine}")

    first_machine, before, started = machine(), processes(), time.monotonic()
    last_machine = first_machine
    seen = kernel = reaped = born = 0.0
    for _ in range(seconds):
        time.sleep(1.0)
        last_machine, now = machine(), processes()
        for key, (own, children, is_kernel) in now.items():
            earlier = before.get(key)
            credit = own - earlier[0] if earlier else own
            born += 0.0 if earlier else own
            reaped += children - earlier[1] if earlier else 0.0
            seen += credit
            kernel += credit if is_kernel else 0.0
        before = now
    elapsed = time.monotonic() - started
    delta = {name: last_machine[name] - first_machine[name] for name in first_machine}
    capacity = elapsed * cores
    busy = sum(delta.values()) - delta["idle"] - delta["iowait"]
    interrupts = delta["irq"] + delta["softirq"]
    missing = busy - seen

    def share(value: float) -> str:
        of_capacity, of_busy = 100 * value / capacity, 100 * value / busy
        return f"{value:7.2f} CPU-s = {of_capacity:5.2f}% of capacity, {of_busy:5.1f}% of busy"

    idle = capacity - busy
    print(f"\nover {elapsed:.1f} s: capacity {capacity:.1f} CPU-s, idle and waiting {idle:.1f}")
    print(f"  machine busy (per-core counters)        {share(busy)}")
    print(f"  credited to processes by 1 s polling    {share(seen)}")
    print(f"    of which kernel threads               {share(kernel)}")
    print(f"    of which first sightings              {share(born)}")
    print(f"  interrupt time the counters report      {share(interrupts)}")
    print(f"  stolen by a hypervisor                  {share(delta['steal'])}")
    print(f"  busy time that no process accounts for  {share(missing)}")
    print(f"  parents' child-time counters rose by    {share(reaped)} (gross)")
    remainder = 100 * missing / capacity
    counted = 100 * (interrupts + kernel) / capacity
    left = 100 * (missing - interrupts) / capacity
    print(
        f"\nSystem as a remainder (busy less processes) would show {remainder:.2f}% of capacity, "
        "and the invariant is exact by definition.\n"
        f"System from counters (interrupts, plus kernel threads) would show {counted:.2f}%, "
        f"leaving {left:.2f}% of capacity for the 2% tolerance to absorb."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
