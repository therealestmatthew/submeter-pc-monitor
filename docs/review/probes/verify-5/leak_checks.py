"""Probe: re-check the leak, warm-up, staircase and slow-growth claims (clusters M3, M4, M5).

Logic only, on synthetic minute buckets fed to the baseline's own check_growth() with the
defaults from core/config.py. Nothing is timed, no process is read, nothing is written.

    uv run python docs/review/probes/verify-5/leak_checks.py

M3: a leak at exactly 50 MiB/h and at 50 decimal MB/h, with and without noise; how many
minute buckets the first flag needs.
M4: the docs/07 browser warm-up (0.9 GiB, tau 0.35 h), checked every 5 minutes over a
sliding 2-hour window from hour 2 to hour 4, at several noise levels applied to each bucket;
then a staircase leak under a sliding and a growing window.
M5: the slow-growth settings, and daily minimums of a 10 MiB/h leak over 7 and 8 days.
"""

from __future__ import annotations

import math
import random
from collections.abc import Callable

from submeter.analysis.growth import check_growth, daily_minimums
from submeter.core.config import load_settings

MIB, GIB, HOUR, DAY = 1024**2, 1024**3, 3600.0, 86400.0
SETTINGS = load_settings().settings
LEAK = SETTINGS.analysis.leak
BASE = 3.0 * GIB
Series = Callable[[float], float]


def verdict(xs: list[float], ys: list[float], min_duration: float, min_slope: float) -> str:
    result = check_growth(xs, ys, min_duration_s=min_duration, min_slope_per_s=min_slope)
    return "FLAGGED" if result.flagged else result.reason


def leak_verdict(xs: list[float], ys: list[float]) -> str:
    return verdict(xs, ys, LEAK.min_duration, LEAK.min_slope)


def minutes(series: Series, hours: float, noise: float, seed: int, step_min: int = 1):
    rng = random.Random(seed)
    xs = [60.0 * step_min * i for i in range(round(hours * 60 / step_min) + 1)]
    return xs, [series(t) + rng.uniform(-noise, noise) for t in xs]


def linear(rate_per_h: float) -> Series:
    return lambda t: BASE + rate_per_h * t / HOUR


def warm_up(tau_h: float) -> Series:
    return lambda t: BASE + 0.9 * GIB * (1 - math.exp(-t / HOUR / tau_h))


def stairs(step: float, every_min: float) -> Series:
    return lambda t: BASE + step * math.floor(t / (60 * every_min))


def any_flag(series: Series, noise: float, seed: int, step_min: int, last_h: float) -> bool:
    """Checks every 5 minutes over a sliding 2-hour window, from hour 2 to last_h."""
    xs, ys = minutes(series, last_h, noise, seed, step_min)
    per_h = 60 // step_min
    for end in range(2 * per_h, len(xs), max(1, 5 // step_min)):
        window = slice(end - 2 * per_h, end + 1)
        if leak_verdict(xs[window], ys[window]) == "FLAGGED":
            return True
    return False


def m3() -> None:
    print("M3. leak acceptance against the default threshold")
    print(f"   min_slope = {LEAK.min_slope * HOUR:,.0f} bytes/h; 50 MB decimal = {50e6:,.0f}")
    for count in (120, 121):
        xs, ys = minutes(linear(100 * MIB), (count - 1) / 60, 0.0, 0)
        print(
            f"   100 MiB/h, {count} buckets spanning {xs[-1] / 60:.0f} min: {leak_verdict(xs, ys)}"
        )
    for name, rate in (("50 MiB/h", 50 * MIB), ("50 MB/h decimal", 50e6), ("55 MiB/h", 55 * MIB)):
        cells = []
        for noise in (0.0, 5e6, 30e6):
            seeds = 1 if noise == 0 else 200
            hits = sum(
                leak_verdict(*minutes(linear(rate), 2, noise, seed)) == "FLAGGED"
                for seed in range(seeds)
            )
            cells.append(f"noise {noise / 1e6:>2.0f} MB: {100 * hits / seeds:>3.0f}%")
        print(f"   {name:<16} 121 buckets flagged  " + "  ".join(cells))


def m4() -> None:
    print("\nM4. docs/07 browser warm-up, sliding 2-hour window, checks every 5 min, hours 2-4")
    clean = any_flag(warm_up(0.35), 0.0, 0, 1, 4.0)
    print(f"   noise-free warm-up (a fixture a builder might write): flagged={clean}")
    for step_min, label in ((1, "minute buckets"), (5, "5-minute points as in docs/07")):
        for noise in (5e6, 20e6, 40e6):
            hits = sum(any_flag(warm_up(0.35), noise, seed, step_min, 4.0) for seed in range(60))
            print(
                f"   {label:<30} noise +/-{noise / 1e6:>2.0f} MB:"
                f" {hits:>2} of 60 runs falsely flagged"
            )
    print("   staircase +256 MiB every 120 min (128 MiB/h), noise 5 MB, 12 h, one check per 5 min")
    xs, ys = minutes(stairs(256 * MIB, 120), 12, 5e6, 1)
    for growing in (False, True):
        flagged = checks = 0
        for end in range(120, len(xs), 5):
            start = 0 if growing else end - 120
            checks += 1
            flagged += leak_verdict(xs[start : end + 1], ys[start : end + 1]) == "FLAGGED"
        name = "growing window" if growing else "sliding 2 h window"
        print(f"      {name:<18}: flagged in {flagged} of {checks} checks")


def m5() -> None:
    print("\nM5. slow growth")
    fields = sorted(type(SETTINGS.analysis.slow_growth).model_fields)
    print(
        f"   SlowGrowth fields: {fields}; window = {SETTINGS.analysis.slow_growth.window / DAY} d"
    )
    for days, offset_h in ((7, 0), (8, 0), (7, 9)):
        start = 1_795_132_800.0 + offset_h * HOUR
        times = [start + HOUR * i for i in range(int(days * 24))]
        values = [BASE + 10 * MIB * i for i in range(len(times))]
        lows = daily_minimums(times, values)
        xs, ys = [day for day, _ in lows], [low for _, low in lows]
        span = (xs[-1] - xs[0]) / DAY
        window = SETTINGS.analysis.slow_growth.window
        with_leak_slope = verdict(xs, ys, window, LEAK.min_slope)
        with_low_slope = verdict(xs, ys, window, 5 * MIB / HOUR)
        print(
            f"   {days} d of hourly buckets from {offset_h:02d}:00: {len(lows)} daily minimums "
            f"spanning {span:.0f} d; with leak.min_slope: {with_leak_slope}; "
            f"with 5 MiB/h: {with_low_slope}"
        )


if __name__ == "__main__":
    m3()
    m4()
    m5()
