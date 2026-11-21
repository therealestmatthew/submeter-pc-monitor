"""Probe: re-check the baseline range, verdict thresholds, frequency and self-attribution
claims (clusters M6, M9, M13).

Logic only, plus reading sysfs frequency files. Nothing is timed, no process is changed,
nothing is written.

    uv run python docs/review/probes/verify-5/config_and_baseline.py

M6: usual_range() on a steady idle series with the shipped floor, and day 8 of the docs/07
table computed both ways the floor can be read.
M9: whether verdict.thresholds refuses an unknown key; this machine's base and maximum
frequency, to show what "80% of maximum" means on a turbo CPU.
M13: which processes the baseline Attributor puts in the "submeter" workload.
"""

from __future__ import annotations

from pathlib import Path

from submeter.analysis.growth import usual_range
from submeter.attribution.rules import Attributor, RuleSet
from submeter.core.config import ConfigError, load_settings
from submeter.core.models import ProcessKey, ProcessSample

DOCS07_DAYS_1_TO_7 = [3.44, 3.45, 3.34, 3.42, 3.32, 3.42, 3.44]


def m6() -> None:
    print("M6. usual range")
    baseline = load_settings().settings.analysis.baseline
    print(f"   Baseline settings: {sorted(type(baseline).model_fields)}")
    idle_cpu = [0.0] * 20 + [0.001]
    print(f"   idle workload, 20 minutes at 0.000 cores and one at 0.001: {usual_range(idle_cpu)}")
    middle = sorted(DOCS07_DAYS_1_TO_7)[3]
    mad = sorted(abs(v - middle) for v in DOCS07_DAYS_1_TO_7)[3]
    on_deviation = 4 * 1.4826 * max(0.03, mad)
    low, _mid, high = usual_range(DOCS07_DAYS_1_TO_7, floor=0.03) or (0.0, 0.0, 0.0)
    print(f"   day 8, docs/07 sentence (floor on the deviation): {middle - on_deviation:.3f}")
    print(f"      to {middle + on_deviation:.3f}; usual_range(floor=0.03): {low:.3f} to {high:.3f}")
    print("      docs/07 table prints 3.25 to 3.60")


def m9() -> None:
    print("\nM9. verdict thresholds and frequency")
    for key in ("cpu_tyme", "anything"):
        try:
            loaded = load_settings(overrides={"verdict": {"thresholds": {key: 0.85}}})
            print(
                f"   verdict.thresholds.{key} = 0.85 accepted: {loaded.settings.verdict.thresholds}"
            )
        except ConfigError as error:
            print(f"   verdict.thresholds.{key} refused: {error}")
    try:
        load_settings(overrides={"verdict": {"thresold": {"cpu": 0.85}}})
        print("   verdict.thresold accepted")
    except ConfigError:
        print("   verdict.thresold (misspelt group) refused, so unknown keys are refused elsewhere")
    cpu0 = Path("/sys/devices/system/cpu/cpu0/cpufreq")
    try:
        top = int((cpu0 / "cpuinfo_max_freq").read_text())
        base = int((cpu0 / "base_frequency").read_text())
        now = sorted(
            int(p.read_text())
            for p in Path("/sys/devices/system/cpu").glob("cpu*/cpufreq/scaling_cur_freq")
        )
        print(
            f"   max {top / 1e6:.2f} GHz, base {base / 1e6:.2f} GHz"
            f" = {100 * base / top:.1f}% of max"
        )
        print(
            f"   80% of max is {0.8 * top / 1e6:.2f} GHz;"
            f" current {now[0] / 1e6:.2f} to {now[-1] / 1e6:.2f} GHz"
        )
    except OSError as error:
        print(f"   frequency files not readable: {error.strerror}")


def m13() -> None:
    print("\nM13. the submeter workload")

    def process(pid: int, exe: str) -> ProcessSample:
        return ProcessSample(
            key=ProcessKey(pid=pid, started=1.0),
            parent_pid=1,
            exe=exe,
            cmdline=None,
            cwd=None,
            cpu_s=0.01,
            io_read_bytes=0,
            io_write_bytes=0,
            memory_bytes=1,
            threads=1,
            first_seen=False,
            restricted=False,
        )

    assigned = Attributor(RuleSet(), self_pid=100).assign(
        [process(100, "submeter-collector"), process(200, "submeter-server")]
    )
    for key, value in sorted(assigned.items(), key=lambda item: item[0].pid):
        print(f"   pid {key.pid}: {value.workload} ({value.reason})")


if __name__ == "__main__":
    m6()
    m9()
    m13()
