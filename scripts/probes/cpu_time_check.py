"""Whether Windows counts interrupt and DPC time inside system time (R125, decision B4).

Run it from the repository root:  uv run python scripts/probes/cpu_time_check.py

Per core it reads psutil.cpu_times(percpu=True) and time.perf_counter(), waits 10 s, reads both
again, and prints two ratios over the elapsed time:

    r1 = increase of (user + system + idle) / elapsed
    r2 = increase of (user + system + idle + interrupt + dpc) / elapsed

It does that three times, then prints the decision (docs/PLAN.md 6.4, P0.4):

- r1 within 1.00 +- 0.01 on every core in every repetition: "subtract interrupt and DPC";
  interrupt and DPC time are already inside system time, so the busy sum counts them twice.
- r2 within it: "keep the busy sum".
- neither, or both (interrupt plus DPC under 1% of elapsed, CQ-02): "ask"; the owner decides.

It only reads counters: it changes no process and no setting, and opens no connection. On a
system whose cpu_times has no interrupt or dpc field (Linux) it says so and measures nothing.
"""

from __future__ import annotations

import platform
import sys
import time
from collections.abc import Mapping, Sequence

import psutil

R1_FIELDS = ("user", "system", "idle")
R2_FIELDS = (*R1_FIELDS, "interrupt", "dpc")
TOLERANCE = 0.01
SECONDS = 10.0
REPETITIONS = 3

SUBTRACT = "subtract interrupt and DPC"
KEEP = "keep the busy sum"
ASK = "ask"

Reading = Sequence[Mapping[str, float]]  # one mapping of field to cumulative seconds per core
Ratios = list[tuple[float, float]]  # (r1, r2) per core


def ratios(before: Reading, after: Reading, elapsed_s: float) -> Ratios:
    """(r1, r2) for each core, from two cumulative readings elapsed_s seconds apart."""
    if len(before) != len(after):
        raise ValueError(f"the two readings have {len(before)} and {len(after)} cores")
    if elapsed_s <= 0:
        raise ValueError(f"elapsed time must be above 0 s, got {elapsed_s}")
    found: Ratios = []
    for first, second in zip(before, after, strict=True):
        r1 = sum(second[field] - first[field] for field in R1_FIELDS) / elapsed_s
        r2 = sum(second[field] - first[field] for field in R2_FIELDS) / elapsed_s
        found.append((r1, r2))
    return found


def _within(ratio: float) -> bool:
    return abs(ratio - 1.0) <= TOLERANCE + 1e-9  # the slack absorbs float rounding only


def _outside(repetitions: Sequence[Ratios], which: int) -> list[str]:
    return [
        f"repetition {number} core {index} r{which + 1}={pair[which]:.4f}"
        for number, cores in enumerate(repetitions, start=1)
        for index, pair in enumerate(cores)
        if not _within(pair[which])
    ]


def decide(repetitions: Sequence[Ratios]) -> tuple[str, str]:
    """The decision and its reason, from the ratios of every repetition."""
    if not repetitions or not all(repetitions):
        return ASK, "no ratios were measured"
    r1_misses, r2_misses = _outside(repetitions, 0), _outside(repetitions, 1)
    band = f"1.00 +- {TOLERANCE:.2f}"
    if not r1_misses and not r2_misses:
        return ASK, "interrupt plus DPC under 1% of elapsed: the check cannot tell"
    if not r1_misses:
        return SUBTRACT, f"r1 within {band} on every core in every repetition"
    if not r2_misses:
        return KEEP, f"r2 within {band} on every core in every repetition"
    return ASK, (
        f"neither ratio within {band} everywhere; first misses: "
        f"{'; '.join(r1_misses[:3])}; {'; '.join(r2_misses[:3])}"
    )


def missing_fields(reading: Reading) -> list[str]:
    """The fields the two ratios need that this system's cpu_times does not have."""
    present = set(reading[0]) if reading else set()
    return [field for field in R2_FIELDS if field not in present]


def read_cores() -> tuple[float, list[dict[str, float]]]:
    """One reading of every core, stamped at the middle of the call."""
    started = time.perf_counter()
    cores = [dict(times._asdict()) for times in psutil.cpu_times(percpu=True)]
    return (started + time.perf_counter()) / 2, cores


def measure(seconds: float) -> Ratios:
    first_at, first = read_cores()
    time.sleep(seconds)
    second_at, second = read_cores()
    return ratios(first, second, second_at - first_at)


def main() -> int:
    print(
        f"{platform.platform()} | Python {platform.python_version()} | psutil {psutil.__version__}"
    )
    missing = missing_fields(read_cores()[1])
    if missing:
        print(
            f"unavailable: cpu_times on this system has no {' or '.join(missing)} field, "
            "so neither ratio can be measured. Run this on Windows."
        )
        return 2
    print(f"{psutil.cpu_count()} logical cores, {REPETITIONS} repetitions of {SECONDS:.0f} s")
    print("r1 = d(user + system + idle) / elapsed; r2 = d(user + system + idle + interrupt + dpc)")
    measured: list[Ratios] = []
    for number in range(1, REPETITIONS + 1):
        found = measure(SECONDS)
        measured.append(found)
        for index, (r1, r2) in enumerate(found):
            print(f"repetition {number} core {index:>3}: r1={r1:.4f} r2={r2:.4f}", flush=True)
    decision, reason = decide(measured)
    print(f"decision: {decision}")
    print(f"reason: {reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
