"""Probe: what a merged bucket says about capacity and epoch when either changed inside it.

Reads and measures only. Nothing is written.

    .venv/bin/python docs/review/probes/c-storage/merge_capacity.py

The design says percentages use the capacity recorded in each bucket, and that a change of
sampling interval, rules, provider status, hardware or version starts a new epoch. One hour is
built here from minute buckets whose logical core count and epoch change at half past: the
machine is fully busy throughout, on 8 cores and then on 16. The probe prints what rollup.merge
keeps of the two, and the share of capacity an hourly figure would then show.
"""

from __future__ import annotations

from _synth import DAY0, workload

from submeter.store.rollup import merge, roll_up


def half(start: float, cores: int, epoch: int) -> list:
    samples = [workload(start + second + 1, float(cores), name="machine") for second in range(1800)]
    return roll_up(samples, width_s=60, logical_cores=cores, epoch=epoch)


def main() -> None:
    minutes = half(DAY0, 8, 3) + half(DAY0 + 1800, 16, 4)
    hour = merge(minutes, start=DAY0, width_s=3600)
    true_capacity = sum(bucket.covered_s * bucket.logical_cores for bucket in minutes)
    shown = hour.cpu_s / (hour.covered_s * hour.logical_cores)
    print(
        f"60 minute buckets: epochs {sorted({b.epoch for b in minutes})}, logical cores "
        f"{sorted({b.logical_cores for b in minutes})}, CPU {hour.cpu_s:.0f} s of "
        f"{true_capacity:.0f} core-seconds of capacity: {hour.cpu_s / true_capacity:.0%} busy"
    )
    print(
        f"the merged hour keeps epoch {hour.epoch} and logical_cores {hour.logical_cores} (the "
        f"latest of each): CPU over covered_s x logical_cores = {shown:.0%}"
    )
    backwards = merge(list(reversed(minutes)), start=DAY0, width_s=3600)
    print(
        f"merge sorts by start, so the order given does not matter: epoch {backwards.epoch}, "
        f"logical_cores {backwards.logical_cores}. Fields of Bucket that could say an epoch or a "
        f"capacity changed inside it: "
        f"{[f for f in type(hour).model_fields if 'epoch' in f or 'cores' in f or 'capacity' in f]}"
    )
    direct = roll_up(
        [workload(DAY0 + second + 1, 8.0 if second < 1800 else 16.0) for second in range(3600)],
        width_s=3600,
        logical_cores=16,
        epoch=4,
    )[0]
    print(
        f"roll_up takes one logical_cores and one epoch for the whole call: an hour built "
        f"directly from raw samples is stamped epoch {direct.epoch}, {direct.logical_cores} cores"
    )


if __name__ == "__main__":
    main()
