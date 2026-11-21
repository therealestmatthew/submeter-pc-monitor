"""Severity audit probe for clusters M3 and M4: when does the docs/07 warm-up get flagged, and
does the window choice matter; does the acceptance rate proposed for M3 hold under noise.

Logic only. Synthetic minute buckets go to the baseline's own check_growth() with the defaults
from core/config.py. Nothing is timed, no process is read, nothing is written or sent.

    uv run python docs/review/probes/audit/audit_growth_windows.py

Part 1 (M4): the docs/07 browser warm-up (0.9 GiB, tau 0.35 h) on minute buckets with uniform
noise, checked every 5 minutes from hour 2 to hour 4, under a sliding 2-hour window and under a
window that grows from the start of the series (docs/06:64 '2 to 48 h back'). It reports how
many runs are falsely flagged, and at which check times the flags fall.
Part 2 (M4): the same warm-up started 30 minutes before the series begins (the collector or the
window starts after the browser), to see whether the flags need the steep start in the window.
Part 3 (M3): how often a linear leak at 50 MiB/h and at 75 MiB/h is flagged at the first check
the defaults allow (121 minute buckets), under the same noise.
Part 4 (M4 against M3): M4 proposes that the tail slope's lower confidence bound must clear
min_slope. For a 75 MiB/h leak (M3's proposed acceptance rate) on 121 minute buckets, it reports
the spread of the tail's Theil-Sen slope across seeds, and how often the tail estimate, and an
estimate minus 1.645 spreads (a one-sided 95% bound using the true spread), clear min_slope.
"""

from __future__ import annotations

import math
import random
import statistics
from collections import Counter
from collections.abc import Callable

from submeter.analysis.growth import check_growth, theil_sen
from submeter.core.config import load_settings

MIB, GIB, HOUR = 1024**2, 1024**3, 3600.0
LEAK = load_settings().settings.analysis.leak
BASE = 3.6 * GIB
Series = Callable[[float], float]


def flagged(xs: list[float], ys: list[float]) -> bool:
    return check_growth(
        xs, ys, min_duration_s=LEAK.min_duration, min_slope_per_s=LEAK.min_slope
    ).flagged


def warm_up(shift_h: float) -> Series:
    return lambda t: BASE + 0.9 * GIB * (1 - math.exp(-(t / HOUR + shift_h) / 0.35))


def linear(rate_per_h: float) -> Series:
    return lambda t: BASE + rate_per_h * t / HOUR


def series(fn: Series, hours: float, noise: float, seed: int) -> tuple[list[float], list[float]]:
    rng = random.Random(seed)
    xs = [60.0 * i for i in range(round(hours * 60) + 1)]
    return xs, [fn(t) + rng.uniform(-noise, noise) for t in xs]


def flag_times(fn: Series, noise: float, seed: int, growing: bool) -> list[int]:
    xs, ys = series(fn, 4.0, noise, seed)
    hits = []
    for end in range(120, len(xs), 5):
        start = 0 if growing else end - 120
        if flagged(xs[start : end + 1], ys[start : end + 1]):
            hits.append(end)
    return hits


def part_warm_up(shift_h: float, label: str) -> None:
    print(label)
    for noise in (20e6, 40e6):
        for growing in (False, True):
            runs = 0
            when: Counter[int] = Counter()
            for seed in range(60):
                hits = flag_times(warm_up(shift_h), noise, seed, growing)
                runs += bool(hits)
                when.update(hits)
            name = "growing window" if growing else "sliding 2 h window"
            times = ", ".join(f"{m // 60}h{m % 60:02d}:{n}" for m, n in sorted(when.items()))
            print(
                f"   noise +/-{noise / 1e6:.0f} MB, {name:<18}: {runs:>2} of 60 runs flagged;"
                f" flags by check time (count) {times or 'none'}"
            )


def part_rates() -> None:
    print("Part 3. linear leak, first allowed check (121 minute buckets), 200 seeds")
    for rate in (50 * MIB, 75 * MIB):
        cells = []
        for noise in (5e6, 40e6):
            hits = sum(flagged(*series(linear(rate), 2.0, noise, seed)) for seed in range(200))
            cells.append(f"noise +/-{noise / 1e6:.0f} MB: {hits / 2:.0f}%")
        print(f"   {rate / MIB:.0f} MiB/h  " + "  ".join(cells))


def part_tail_bound() -> None:
    print("Part 4. 75 MiB/h leak, 121 minute buckets: tail (last third) slope against min_slope")
    floor = LEAK.min_slope * HOUR / MIB
    for noise in (5e6, 20e6, 40e6):
        tails = []
        for seed in range(200):
            xs, ys = series(linear(75 * MIB), 2.0, noise, seed)
            cut = int(len(xs) * (1 - 1 / 3))
            tails.append(theil_sen(xs[cut:], ys[cut:]) * HOUR / MIB)
        spread = statistics.pstdev(tails)
        point = sum(t >= floor for t in tails) / 2
        bound = sum(t - 1.645 * spread >= floor for t in tails) / 2
        print(
            f"   noise +/-{noise / 1e6:.0f} MB: tail slope spread {spread:.1f} MiB/h;"
            f" estimate clears {floor:.0f} MiB/h in {point:.0f}%,"
            f" lower bound clears it in {bound:.0f}%"
        )


if __name__ == "__main__":
    part_warm_up(0.0, "Part 1. docs/07 warm-up starting at the first bucket, checks 2h00..4h00")
    part_warm_up(0.5, "Part 2. same warm-up, 30 min old when the series begins")
    part_rates()
    part_tail_bound()
