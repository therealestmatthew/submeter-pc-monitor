"""Verify G3: can the baseline Sampler take hot-set ticks and cold-set ticks?

Reads and measures only. Clocks and processes are synthetic.

    uv run python docs/review/probes/verify-1/hot_cold.py

One hot process at 0.90 cores and 9 cold ones at 0.02 cores each, ticks every 1 s for 30 s.
The cold set is read every 10th tick (docs/05 step 2: hot every 1 s, cold every 10 s).
A: a snapshot holds only the processes read that tick (cold ones absent between cold reads).
B: every snapshot lists every process, but a cold process's counters are the last ones read.
The hot set is chosen as hot_keys() would choose it.
"""

from __future__ import annotations

from _helpers import DAY0, proc, snap

from submeter.collector.sampler import Sampler

HOT, COLD = 0.90, 0.02
TICKS = 30


def truth(pid: int, k: int) -> float:
    return (HOT if pid == 1 else COLD) * k


def run(mode: str) -> None:
    sampler = Sampler()
    credited = {"hot": 0.0, "cold": 0.0}
    exits = starts = 0
    peak_cold_cores = 0.0
    last_cold = dict.fromkeys(range(2, 11), 0.0)
    for k in range(TICKS + 1):
        cold_tick = k % 10 == 0
        processes = [proc(1, truth(1, k))]
        for pid in range(2, 11):
            if cold_tick:
                last_cold[pid] = truth(pid, k)
                processes.append(proc(pid, last_cold[pid]))
            elif mode == "B":
                processes.append(proc(pid, last_cold[pid]))
        batch = sampler.ingest(snap(DAY0 + k, processes, mono=float(k)))
        if batch is None:
            continue
        exits += len(batch.exited)
        cold_cpu = 0.0
        for sample in batch.processes:
            if sample.key.pid == 1:
                credited["hot"] += sample.cpu_s
            else:
                credited["cold"] += sample.cpu_s
                cold_cpu += sample.cpu_s
            starts += sample.first_seen
        peak_cold_cores = max(peak_cold_cores, cold_cpu / batch.interval_s)
    print(
        f"   {mode}: hot credited {credited['hot']:.2f} of {HOT * TICKS:.2f} CPU-s; cold credited "
        f"{credited['cold']:.2f} of {9 * COLD * TICKS:.2f}; exits reported {exits}, starts "
        f"reported {starts} (truth 0 and 0); cold set's highest one-tick rate "
        f"{peak_cold_cores:.2f} cores (truth {9 * COLD:.2f})"
    )


if __name__ == "__main__":
    print("hot and cold sets through Sampler.ingest(), 30 one-second ticks")
    run("A")
    run("B")
