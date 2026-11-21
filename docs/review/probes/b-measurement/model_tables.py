"""Probe: recompute the brief's modelled tables, then redo them with the measured costs.

Arithmetic only. Nothing is timed here: the measured costs are copied from
docs/review/probes/measure/*.out.txt and docs/review/ground/platform-check.txt.

    uv run python docs/review/probes/b-measurement/model_tables.py

1. docs/05 polling table: (L / T) * (1 - exp(-T / L)) with L = 300 ms, and the same share
   when every child lives exactly L instead of an exponentially distributed time.
2. docs/08 sample time explorer, as written, for the eleven rows of its table.
3. The same explorer with the per-process costs measured on this machine.
4. The switching rule in docs/11 applied to each measured number.
"""

from __future__ import annotations

import math

L = 0.3
ROW_BYTES = 90
WORKLOAD_ROWS = 8
ROWS = [
    (0.25, 10, 300),
    (0.5, 10, 300),
    (1, 10, 300),
    (2, 10, 300),
    (5, 10, 300),
    (10, 10, 300),
    (1, 10, 100),
    (1, 10, 1000),
    (1, 5, 300),
    (1, 60, 300),
    (0.25, 5, 1000),
]
# Measured on this machine while quiet (Python 3.14.5, psutil 7.2.2, Linux), ms and processes.
MEASURED = {
    "psutil provider, snapshot()": (111.2, 447),
    "direct /proc, stat only": (11.2, 448),
    "direct /proc, stat + statm + io": (23.2, 449),
    "baseline tick: snapshot + deltas + attribution + totals": (125.9, 447),
    "platform_check, psutil snapshot": (114.3, 452),
}
FOOTPRINT_CPU_S, FOOTPRINT_TICKS, FOOTPRINT_PROCESSES = 17.0, 120, 447
PIPELINE_CPU_MS = 125.8
MEMORY_MB = {"resident": 39, "unique": 35, "proportional": 36}


def exponential(interval: float, life: float = L) -> float:
    return (life / interval) * (1 - math.exp(-interval / life))


def fixed(interval: float, life: float = L) -> float:
    """Every child lives exactly `life`, polled every `interval` with a random phase."""
    if life <= interval:
        return life / (2 * interval)
    return 1 - interval / (2 * life)


def explorer(active: float, cold: float, processes: int, sample_ms: float, extra: float) -> str:
    overhead = sample_ms / active / 10 + extra
    hot = max(10, round(processes * 0.1))
    rows = (
        hot * 172_800 / active
        + (processes - hot) * 172_800 / cold / 3
        + WORKLOAD_ROWS * 172_800 / active
    )
    disk = rows * ROW_BYTES / 1e9
    if overhead > 3 and disk > 2:
        status = f"over both, about {round(96 / disk)} h"
    elif overhead > 3:
        status = "over the overhead limit"
    elif disk > 2:
        status = f"over the disk budget, about {round(96 / disk)} h"
    elif overhead > 1:
        status = "active only"
    else:
        status = "in budget"
    gib = rows * ROW_BYTES / 1024**3
    return (
        f"{overhead:5.2f}%  {rows / 1e6:5.1f} M  {disk:5.2f} GB ({gib:5.2f} GiB)  "
        f"{100 * exponential(active):3.0f}%  {status}"
    )


def main() -> None:
    print("1. docs/05 polling model, children living 300 ms on average")
    print("   interval   exponential lives (the brief)   every child lives exactly 300 ms")
    for interval in (5, 2, 1, 0.5, 0.25):
        print(
            f"   {interval:>5} s   {100 * exponential(interval):5.1f}%"
            f"                          {100 * fixed(interval):5.1f}%"
        )
    print(
        "   measured children (reconcile_under_spawn): mean life 82 ms, interval about 1.13 s\n"
        f"   exponential model {100 * exponential(1.13, 0.082):.1f}%, "
        f"fixed-life model {100 * fixed(1.13, 0.082):.1f}%, "
        f"measured about {100 * (16.75 - (18.55 - 2.28)) / 16.75:.1f}% "
        "(16.75 CPU-s used, 18.55 missing, 2.28 missing when quiet)"
    )

    print("\n2. docs/08 explorer as written: 1.5 ms + 0.012 ms per process, +0.2 points")
    print("   active  cold  procs  overhead  rows     disk                     captures  status")
    for active, cold, processes in ROWS:
        line = explorer(active, cold, processes, 1.5 + 0.012 * processes, 0.2)
        print(f"   {active:>5}s {cold:>4}s {processes:>5}  {line}")

    rows_1000 = 100 * 172_800 + 900 * 172_800 / 10 / 3 + WORKLOAD_ROWS * 172_800
    print(
        f"   the 1 s, 10 s, 1000 row is {rows_1000 * ROW_BYTES:,.0f} bytes: over 2 GB counted in "
        f"decimal, under the 2GB setting as core/units.py reads it ({2 * 1024**3:,} bytes)"
    )

    print("\n3. per-process cost: assumed 0.012 ms, measured")
    for name, (ms, count) in MEASURED.items():
        per = ms / count
        print(
            f"   {name:<56} {per:.4f} ms = {per / 0.012:4.1f} times the assumption; "
            f"300 processes {300 * per:5.1f} ms"
        )
    tick_ms = 1000 * FOOTPRINT_CPU_S / FOOTPRINT_TICKS
    store_ms = tick_ms - PIPELINE_CPU_MS
    print(
        f"   collector_footprint: {tick_ms:.1f} ms CPU per tick with the raw store, "
        f"so the store adds about {store_ms:.1f} ms per tick = {store_ms / 10:.1f} points "
        "at 1 s (assumed: 0.2 points for the store and the API)"
    )
    proc_full = 23.2 / 449
    rest = (125.9 - 111.2) / 447
    store = store_ms / FOOTPRINT_PROCESSES
    print("   explorer redone with measured costs, every process read every tick, 300 processes:")
    for label, per_process, extra_ms in (
        ("snapshot only (stat+statm+io)", proc_full, 0.0),
        ("whole tick (+ deltas, attribution, totals)", proc_full + rest, 0.0),
        ("whole tick + raw store", proc_full + rest + store, 0.0),
        ("whole tick + raw store, psutil fallback", 111.2 / 447 + rest + store, 0.0),
    ):
        cells = []
        for active in (0.25, 1, 5):
            overhead = (300 * per_process + extra_ms) / active / 10
            limit = 1 if active == 5 else 3
            cells.append(f"{active}s {overhead:5.2f}% ({'over' if overhead > limit else 'ok'})")
        print(f"   {label:<44} {300 * per_process:5.1f} ms  " + "  ".join(cells))
    print("   (limits used: 3% at 0.25 s and 1 s, 1% at the 5 s idle interval)")
    whole = proc_full + rest + store
    print("   the same whole tick when only a hot set is handled each tick (cold every 10 s):")
    for hot_share in (0.1, 0.3):
        hot, cells = 300 * hot_share, []
        for active in (0.25, 1, 5):
            handled_per_s = hot / active + (300 - hot) / 10
            cells.append(f"{active}s {handled_per_s * whole / 10:5.2f}%")
        print(f"   {100 * hot_share:3.0f}% of 300 processes hot: " + "  ".join(cells))

    print("\n4. switching rule in docs/11: more than 10 ms for 300 processes, or more than 80 MB")
    for name, (ms, count) in MEASURED.items():
        scaled = ms * 300 / count
        print(f"   {name:<56} {scaled:5.1f} ms -> {'switch' if scaled > 10 else 'stay'}")
    for name, value in MEMORY_MB.items():
        print(
            f"   collector memory, {name:<38} {value:5d} MB -> {'switch' if value > 80 else 'stay'}"
        )
    print(
        "   10 ms per sample is 1.0% of a core at 1 s and 0.2% at 5 s; the budget itself allows\n"
        "   30 ms per tick at 1 s (3%) and 50 ms per tick at 5 s (1%)"
    )


if __name__ == "__main__":
    main()
