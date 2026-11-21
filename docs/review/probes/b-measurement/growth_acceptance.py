"""Probe: the leak check's arithmetic against "a leak of 50 MB an hour is flagged within
2 hours, and a cache warming up is not", using the baseline's own check_growth().

Logic only, on synthetic series of minute buckets. No process is read. It takes a few minutes.

    uv run python docs/review/probes/b-measurement/growth_acceptance.py

Defaults under test (core/config.py): min_slope 50MB/h, read as 50 * 1024**2 bytes an hour,
and min_duration 2h. Two ways a detector could pick its window are tried, because the brief
names neither: the last 2 hours ("sliding"), or everything since the series began ("growing").
The check runs every 5 minutes from hour 2 on, as a detector would. Each run draws its noise
once, one value per minute bucket, so successive checks see the same history.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable

from submeter.analysis.growth import check_growth
from submeter.core.config import load_settings

MIB, GIB, HOUR = 1024**2, 1024**3, 3600.0
LEAK = load_settings().settings.analysis.leak
BASE = 3.0 * GIB
LEVELLED = "growth has levelled off"
Series = Callable[[float], float]
Watched = tuple[int, int, int, float | None]


def judge(xs: list[float], ys: list[float]) -> str:
    result = check_growth(xs, ys, min_duration_s=LEAK.min_duration, min_slope_per_s=LEAK.min_slope)
    return "FLAGGED" if result.flagged else result.reason


def history(series: Series, hours: float, noise: float, seed: int) -> tuple[list[float], ...]:
    """One value per minute bucket for the whole run, with its noise drawn once."""
    rng = random.Random(seed)
    xs = [60.0 * i for i in range(round(hours * 60) + 1)]
    return xs, [series(t) + rng.uniform(-noise, noise) for t in xs]


def linear(rate: float, start_h: float = 0.0) -> Series:
    return lambda t: BASE + rate * max(0.0, t / HOUR - start_h)


def stairs(step: float, every_min: float) -> Series:
    return lambda t: BASE + step * math.floor(t / (60 * every_min))


def sawtooth(floor_rate: float, height: float, period_h: float) -> Series:
    return lambda t: BASE + floor_rate * t / HOUR + height * ((t / HOUR / period_h) % 1.0)


def warm_up(tau_h: float) -> Series:
    return lambda t: BASE + 0.9 * GIB * (1 - math.exp(-t / HOUR / tau_h))


def ramp(final_rate: float, over_h: float) -> Series:
    """A leak whose rate climbs steadily from nothing to final_rate over over_h hours."""

    def value(t: float) -> float:
        hours = t / HOUR
        climbing = min(hours, over_h) ** 2 / (2 * over_h)
        return BASE + final_rate * (climbing + max(0.0, hours - over_h))

    return value


def watch(
    series: Series, *, hours: float, noise: float, growing: bool, seed: int = 1, stop: bool = False
) -> Watched:
    """Checks run, flagged, levelled off, and the hour of the first flag."""
    xs, ys = history(series, hours, noise, seed)
    checks = flagged = levelled = 0
    first: float | None = None
    for end in range(120, len(xs), 5):
        start = 0 if growing else end - 120
        verdict = judge(xs[start : end + 1], ys[start : end + 1])
        checks += 1
        levelled += verdict == LEVELLED
        if verdict == "FLAGGED":
            flagged += 1
            first = xs[end] / HOUR if first is None else first
            if stop:
                break
    return checks, flagged, levelled, first


def said(result: Watched) -> str:
    checks, flagged, levelled, first = result
    when = "never" if first is None else f"first at {first:.2f} h"
    return f"flagged in {flagged:>3} of {checks} checks ({when}), levelled off in {levelled}"


def runs_flagged(series: Series, *, hours: float, noise: float, growing: bool, seeds: int) -> int:
    return sum(
        watch(series, hours=hours, noise=noise, growing=growing, seed=seed, stop=True)[1]
        for seed in range(seeds)
    )


def main() -> None:
    print(f"threshold {LEAK.min_slope * HOUR:,.0f} bytes an hour; 50 decimal MB is {50e6:,.0f}")

    print("\n1. how soon: a clean 100 MiB/h leak in minute buckets")
    for count in (120, 121):
        xs, ys = history(linear(100 * MIB), (count - 1) / 60, 0.0, 0)
        print(f"   {count} buckets, span {xs[-1] / 60:.0f} min: {judge(xs, ys)}")
    print("   bucket 121 starts at 2 h 00 min, ends at 2 h 01 min and is final 30 s later")

    print("\n2. exactly on the threshold, no noise, 121 buckets")
    for name, rate in (("50 MiB/h", 50.0 * MIB), ("50 MB/h decimal", 50e6)):
        print(f"   {name:<16} {judge(*history(linear(rate), 2, 0.0, 0))}")

    print("\n3. share of 300 noisy 2-hour windows flagged (uniform noise on each minute bucket)")
    print("   leak rate          noise 5 MB   noise 30 MB   noise 100 MB")
    rates = (("50 MB decimal", 50e6), ("50 MiB", 50.0 * MIB), ("55 MiB", 55.0 * MIB))
    for name, rate in (
        *rates,
        ("60 MiB", 60.0 * MIB),
        ("75 MiB", 75.0 * MIB),
        ("100 MiB", 1e2 * MIB),
    ):
        cells = []
        for noise in (5e6, 30e6, 100e6):
            hits = sum(
                judge(*history(linear(rate), 2, noise, seed)) == "FLAGGED" for seed in range(300)
            )
            cells.append(f"{100 * hits / 300:>9.0f}%")
        print(f"   {name:<16}" + "   ".join(cells))

    print("\n4. a steady leak watched for 12 h, noise 30 MB: how often the finding is up")
    for rate in (50, 55, 60, 75):
        cells = [
            f"{'growing' if growing else 'sliding'}: "
            + said(watch(linear(rate * MIB), hours=12, noise=30e6, growing=growing))
            for growing in (False, True)
        ]
        print(f"   {rate} MiB/h\n      " + "\n      ".join(cells))

    print("\n5. a leak that starts after 6 flat hours, noise 30 MB: delay from its start")
    for rate in (60, 100, 200, 380):
        cells = []
        for growing in (False, True):
            series = linear(rate * MIB, start_h=6.0)
            first = watch(series, hours=16, noise=30e6, growing=growing, stop=True)[3]
            delay = "not in 10 h" if first is None else f"{first - 6:.2f} h"
            cells.append(f"{'growing' if growing else 'sliding'} window {delay}")
        print(f"   {rate:>3} MiB/h: " + ", ".join(cells))
    slow = watch(ramp(200 * MIB, 4), hours=8, noise=30e6, growing=False, stop=True)[3]
    print(f"   rate climbing from 0 to 200 MiB/h over 4 h, sliding window: first flag at {slow} h")

    print("\n6. staircase leaks, sliding window, 12 h, noise 5 MB")
    for step, every in ((32, 15), (64, 45), (128, 60), (256, 120)):
        result = watch(stairs(step * MIB, every), hours=12, noise=5e6, growing=False)
        rate = step * 60 / every
        print(f"   +{step:>3} MiB every {every:>3} min ({rate:>3.0f} MiB/h): {said(result)}")

    print("\n7. sawtooth from garbage collection, sliding window, 12 h, noise 5 MB")
    for name, floor, height, period in (
        ("no leak, 200 MiB freed every 30 min", 0, 200, 0.5),
        ("no leak, 600 MiB freed every 3 h", 0, 600, 3.0),
        ("no leak, 400 MiB freed every 6 h", 0, 400, 6.0),
        ("100 MiB/h leak, 500 MiB freed every 30 min", 100, 500, 0.5),
    ):
        series = sawtooth(floor * MIB, height * MIB, period)
        print(f"   {name:<43} {said(watch(series, hours=12, noise=5e6, growing=False))}")

    print("\n8. a cache warming up by 0.9 GiB with time constant tau, 12 h, noise 30 MB")
    for tau in (0.35, 1.0, 2.0, 4.0):
        for growing in (False, True):
            result = watch(warm_up(tau), hours=12, noise=30e6, growing=growing)
            window = "growing" if growing else "sliding"
            print(f"   tau {tau:>4} h, {window} window: {said(result)}")

    print("\n9. the brief's own warm-up (tau 0.35 h): runs of 12 h with at least one false flag")
    for noise in (5e6, 30e6, 40e6):
        cells = []
        for growing, seeds in ((False, 60), (True, 12)):
            hits = runs_flagged(warm_up(0.35), hours=12, noise=noise, growing=growing, seeds=seeds)
            cells.append(f"{'growing' if growing else 'sliding'} {hits} of {seeds} runs")
        print(f"   noise {noise / 1e6:>3.0f} MB: " + ", ".join(cells))

    print("\n10. no leak at all, a noisy total (children coming and going), sliding window, 24 h")
    for noise in (100e6, 300e6, 1000e6):
        flat = linear(0.0)
        hits = runs_flagged(flat, hours=24, noise=noise, growing=False, seeds=20)
        one = said(watch(flat, hours=24, noise=noise, growing=False))
        print(
            f"   noise {noise / 1e6:>5.0f} MB: {hits} of 20 days with a false flag; one day: {one}"
        )


if __name__ == "__main__":
    main()
