"""Probe: which behaviours can be broken without any of the 20 tests noticing?

It copies src/, tests/ and pyproject.toml to a temporary folder outside the repository, breaks
one behaviour at a time in that copy, runs the whole test suite there and restores the file.
Nothing in the repository is changed. Run from the repository root (two to three minutes):

    uv run python docs/review/probes/e-baseline/mutation_check.py

"SURVIVED" means every test still passed with the behaviour broken. The first entry is a
control that must be caught, which proves the tests are running against the copy.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
RULES, RAW = "src/submeter/attribution/rules.py", "src/submeter/store/raw.py"
SAMPLER, ROLLUP = "src/submeter/collector/sampler.py", "src/submeter/store/rollup.py"
PROVIDER, CONFIG = "src/submeter/providers/psutil_provider.py", "src/submeter/core/config.py"
QUERY, FILES = "src/submeter/store/query.py", "src/submeter/store/files.py"
UNITS = "src/submeter/core/units.py"
GROUP = "        group = groups.get(process.key)\n        if group is not None"
DENIED = "                    except psutil.AccessDenied:\n"
NOT_IMPLEMENTED = "                    except NotImplementedError:"

# (what is broken, file, text to find, replacement)
MUTATIONS: list[tuple[str, str, str, str]] = [
    (
        "control: the sampler credits no CPU at all",
        SAMPLER,
        "cpu_s = max(0.0, now.cpu_s - before.cpu_s)",
        "cpu_s = 0.0",
    ),
    (
        "sampler: I/O is reported as the running total, not the delta",
        SAMPLER,
        "    return max(0, now - before)",
        "    return now",
    ),
    (
        "sampler: a jump of the monotonic clock is no longer a gap",
        SAMPLER,
        "elapsed > self._gap_after_s or ",
        "",
    ),
    (
        "sampler: hot_keys returns every process",
        SAMPLER,
        "if sample.first_seen or sample.cpu_s / batch.interval_s >= cpu_threshold",
        "if True",
    ),
    (
        "attribution: rule priority is ignored (file order wins)",
        RULES,
        "key=lambda pair: (-pair[1].priority, pair[0])",
        "key=lambda pair: pair[0]",
    ),
    (
        "attribution: a rule beats kernel-group membership",
        RULES,
        GROUP + ":",
        GROUP + " and not any(r.matches(process, parent) for r in self._rules):",
    ),
    (
        "attribution: the inherit_from_parent setting is ignored",
        RULES,
        "inheritable=self._inherit or rule.include_children",
        "inheritable=rule.include_children",
    ),
    (
        "attribution: Submeter's own process is not recognised",
        RULES,
        "if process.key.pid == self._self_pid:",
        "if False:",
    ),
    (
        "attribution: a rule's cmdline condition is ignored",
        RULES,
        "if self.cmdline is not None and (",
        "if False and (",
    ),
    (
        "totals: the Restricted bucket is labelled polled, not partial",
        RULES,
        "return AccountingSource.PARTIAL if workload == RESTRICTED else AccountingSource.POLLED",
        "return AccountingSource.POLLED",
    ),
    (
        "totals: workload totals drop all bytes read",
        RULES,
        "total.io_read_bytes += process.io_read_bytes or 0",
        "total.io_read_bytes += 0",
    ),
    (
        "totals: workload memory is not summed",
        RULES,
        "total.memory_bytes += process.memory_bytes",
        "total.memory_bytes += 0",
    ),
    (
        "raw: CPU pending when a process exits is thrown away",
        RAW,
        "            for key in batch.exited:",
        "            for key in ():",
    ),
    (
        "raw: CPU pending at midnight rollover and at close is thrown away",
        RAW,
        "self._file.close(self._last_at)",
        "self._file.close(None)",
    ),
    (
        "raw: no keyframe after the one that opens a file",
        RAW,
        "or batch.taken_at - self._keyframe_at >= self._keyframe_interval_s",
        "or False",
    ),
    (
        "raw: a change of memory no longer writes a process row",
        RAW,
        "moved = last is None or abs(sample.memory_bytes - last) >= self._memory_step",
        "moved = last is None",
    ),
    (
        "raw: the workload of a process is never recorded",
        RAW,
        'workload_of.get(key, "unattributed")',
        '"unattributed"',
    ),
    (
        "raw: the file is not in write-ahead-log mode",
        RAW,
        "PRAGMA journal_mode=WAL",
        "PRAGMA journal_mode=DELETE",
    ),
    (
        "rollup: histograms are not time-weighted",
        ROLLUP,
        "histogram.add(self._cores, histogram.CORES, cores, interval)",
        "histogram.add(self._cores, histogram.CORES, cores, 1.0)",
    ),
    (
        "rollup: active seconds are never counted",
        ROLLUP,
        "            self._active_s += interval",
        "            self._active_s += 0.0",
    ),
    (
        "rollup: every bucket counts as well covered",
        ROLLUP,
        "    return bucket.covered_s >= minimum * bucket.width_s",
        "    return True",
    ),
    (
        "provider: a process whose I/O cannot be read is dropped from the snapshot",
        PROVIDER,
        DENIED + "                        restricted = True\n" + NOT_IMPLEMENTED,
        DENIED + "                        return None\n" + NOT_IMPLEMENTED,
    ),
    (
        "provider: idle time is counted as busy time",
        PROVIDER,
        "            - t.idle\n",
        "            - 0.0\n",
    ),
    (
        "config: command-line overrides lose to environment variables",
        CONFIG,
        '        layers.append(("flag", overrides))',
        '        layers.insert(0, ("flag", overrides))',
    ),
    (
        "config: the layers are applied in reverse (the file beats the environment)",
        CONFIG,
        "    for name, layer in layers:",
        "    for name, layer in reversed(layers):",
    ),
    (
        "config: a default differs from the table in docs/08 (idle_after 61s)",
        CONFIG,
        "idle_after: IdleAfter = 60.0",
        "idle_after: IdleAfter = 61.0",
    ),
    (
        "config: a range differs from the table in docs/08 (uss_interval up to 50m)",
        CONFIG,
        'duration_range("10s", "5m")',
        'duration_range("10s", "50m")',
    ),
    (
        "query: minute retention is ignored when choosing a tier",
        QUERY,
        "    elif age <= minute_retention_s:",
        "    elif True:",
    ),
    (
        "files: expired_minute reports every weekly file as expired",
        FILES,
        "            if now - _end_of(monday, 7) > retention_s:",
        "            if True:",
    ),
    (
        "layers: core imports cli through a relative import",
        UNITS,
        "def parse_duration(value: object) -> float:",
        "def _upward() -> object:\n    from ..cli import app\n\n    return app\n\n\n"
        "def parse_duration(value: object) -> float:",
    ),
]


def run_tests(copy: Path) -> tuple[bool, str]:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    done = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider"],
        cwd=copy,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    last = (done.stdout.strip().splitlines() or ["(no output)"])[-1]
    return done.returncode == 0, last.split(" in ")[0]


def main() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as name:
        copy = Path(name)
        for folder in ("src", "tests"):
            shutil.copytree(
                REPO / folder, copy / folder, ignore=shutil.ignore_patterns("__pycache__")
            )
        shutil.copy(REPO / "pyproject.toml", copy / "pyproject.toml")
        passed, summary = run_tests(copy)
        print(f"unchanged copy: {summary}")
        assert passed
        survived = 0
        for what, file, find, replacement in MUTATIONS:
            path = copy / file
            original = path.read_text(encoding="utf-8")
            assert original.count(find) == 1, f"{file}: text not found exactly once: {find!r}"
            path.write_text(original.replace(find, replacement), encoding="utf-8")
            passed, summary = run_tests(copy)
            path.write_text(original, encoding="utf-8")
            survived += passed
            print(f"{'SURVIVED' if passed else 'caught  '}  {what}  [{summary}]")
        print(f"{survived} of {len(MUTATIONS) - 1} broken behaviours survived (control excluded)")


if __name__ == "__main__":
    main()
