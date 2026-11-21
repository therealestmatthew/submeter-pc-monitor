"""Checks the parts of the baseline that depend on the operating system, and prints the evidence.

Run it from the repository root:  uv run python scripts/platform_check.py

It reads and measures only. It writes to a temporary folder, never elevates and sends nothing
anywhere. It was written and run on Linux. Its job is to be run on Windows, where the answers
are not yet known: see docs/reference/windows-priorities.md.
"""

from __future__ import annotations

import os
import platform
import sqlite3
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import psutil

from submeter.collector.sampler import Sampler
from submeter.providers.psutil_provider import PsutilProvider
from submeter.store.files import FileMap, InstanceLock
from submeter.store.raw import RawFile

HOLD = (
    "import sys, time; from pathlib import Path; from submeter.store.files import InstanceLock; "
    "lock = InstanceLock(Path(sys.argv[1])); print(lock.acquire(), lock.holder(), flush=True); "
    "time.sleep(float(sys.argv[2]))"
)
results: list[tuple[str, str, str]] = []


def record(name: str, verdict: str, detail: str) -> None:
    results.append((name, verdict, detail))
    print(f"{verdict:<5} {name}: {detail}", flush=True)


def check_lock(folder: Path) -> None:
    path = folder / "probe.lock"
    holder = subprocess.Popen(
        [sys.executable, "-c", HOLD, str(path), "60"], stdout=subprocess.PIPE, text=True
    )
    assert holder.stdout is not None
    first = holder.stdout.readline().split()
    second = subprocess.run(
        [sys.executable, "-c", HOLD, str(path), "0"], capture_output=True, text=True, check=False
    ).stdout.split()
    same_process = InstanceLock(path).acquire(wait_s=0)
    empty = path.stat().st_size == 0
    holder.kill()
    holder.wait()
    freed = InstanceLock(path)  # poll for up to 5 s: Windows may free a dead holder's lock late
    if freed.acquire(wait_s=5.0):
        freed.release()
    third = subprocess.run(
        [sys.executable, "-c", HOLD, str(path), "0"], capture_output=True, text=True, check=False
    ).stdout.split()
    good = (
        first[:1] == ["True"]
        and second[:1] == ["False"]
        and not same_process
        and empty
        and third[:1] == ["True"]
    )
    record(
        "one-instance lock",
        "PASS" if good else "FAIL",
        f"first holder {first[:1]}, second process {second[:1]} and it read the holder's pid: "
        f"{second[1:2] == first[1:2]}, this process refused: {not same_process}, "
        f"lock file left empty: {empty}, free after the holder was killed: {third[:1]}",
    )


def check_provider() -> None:
    plain, with_folders = PsutilProvider(), PsutilProvider(read_cwd=True)
    snapshot = plain.snapshot()
    total = len(snapshot.processes)
    restricted = sum(1 for process in snapshot.processes if process.restricted)
    no_cmdline = sum(1 for process in snapshot.processes if process.cmdline is None)
    memory = "private bytes (vms)" if sys.platform == "win32" else "resident set size"

    def cost(provider: PsutilProvider) -> tuple[float, float]:
        times = []
        for _ in range(20):
            started = time.perf_counter()
            provider.snapshot()
            times.append((time.perf_counter() - started) * 1000)
        return statistics.median(times), max(times)

    median, worst = cost(plain)
    median_cwd, worst_cwd = cost(with_folders)
    record(
        "process reading",
        "PASS" if total > 0 and restricted < total else "FAIL",
        f"{total} processes, {restricted} restricted, {no_cmdline} without a readable command "
        f"line, memory taken from {memory}",
    )
    record(
        "cost of one full snapshot",
        "INFO",
        f"median {median:.1f} ms, worst {worst:.1f} ms over 20 runs for {total} processes. "
        f"With working folders: median {median_cwd:.1f} ms, worst {worst_cwd:.1f} ms. "
        "The rule in docs/11-language.md is 10 ms for 300 processes",
    )


def check_reconciliation() -> None:
    provider, sampler = PsutilProvider(), Sampler()
    sampler.ingest(provider.snapshot())
    time.sleep(5.0)
    batch = sampler.ingest(provider.snapshot())
    assert batch is not None
    used = sum(sample.cpu_s for sample in batch.processes)
    record(
        "process CPU within busy time",
        "PASS" if used <= batch.cpu_busy_s * 1.05 else "FAIL",
        f"over {batch.interval_s:.1f} s the processes used {used:.2f} CPU-s and the machine was "
        f"busy {batch.cpu_busy_s:.2f} CPU-s; the processes may exceed busy time by 5% at most",
    )


def check_sqlite(folder: Path) -> None:
    path = folder / "2026-11-20.db"
    RawFile(path).close()
    leftovers = sorted(p.name for p in folder.glob("2026-11-20.db-*"))
    reader = sqlite3.connect(path)
    reader.execute("select count(*) from meta").fetchone()
    try:
        path.unlink()
        while_open = "allowed"
    except OSError as error:
        while_open = f"refused ({type(error).__name__})"
    reader.close()
    if path.exists():
        path.unlink()
    record(
        "raw file on disk",
        "PASS" if not leftovers and not path.exists() else "FAIL",
        f"side files left after close: {leftovers or 'none'}, deleting a file that a reader "
        f"has open: {while_open}, deleted once closed: {not path.exists()}",
    )


def check_clock() -> None:
    steps = []
    last = time.monotonic()
    while len(steps) < 200:
        now = time.monotonic()
        if now > last:
            steps.append(now - last)
            last = now
    wall, mono = time.time(), time.monotonic()
    time.sleep(1.0)
    drift = (time.time() - wall) - (time.monotonic() - mono)
    record(
        "clocks",
        "PASS" if abs(drift) < 0.1 else "FAIL",
        f"smallest monotonic step {min(steps) * 1e6:.0f} microseconds, wall clock and "
        f"monotonic clock disagree by {drift * 1000:.1f} ms over one second. Whether the "
        "monotonic clock counts time asleep cannot be tested from a script",
    )


def check_places(folder: Path) -> None:
    real = FileMap.discover()
    probe = FileMap.discover({"SUBMETER_HOME": str(folder / "home")})
    probe.ensure()
    record(
        "file locations",
        "PASS" if probe.raw_dir.is_dir() else "FAIL",
        f"settings {real.settings_file.parent}, data {real.raw_dir.parent}, "
        f"state {real.logs_dir.parent}. Folders could be created under a test home: "
        f"{probe.raw_dir.is_dir()}",
    )


def main() -> int:
    print(
        f"{platform.platform()} | Python {platform.python_version()} | psutil {psutil.__version__}"
    )
    print(f"administrator or root: {_elevated()}\n")
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as name:
        folder = Path(name)
        for check in (check_lock, check_sqlite, check_places):
            _run(check.__name__, lambda check=check: check(folder))
        for plain in (check_provider, check_reconciliation, check_clock):
            _run(plain.__name__, plain)
    failed = [name for name, verdict, _ in results if verdict == "FAIL"]
    print(
        f"\n{len(results)} results, {len(failed)} failed"
        + (f": {', '.join(failed)}" if failed else "")
    )
    return 1 if failed else 0


def _run(name: str, check: object) -> None:
    try:
        check()  # type: ignore[operator]
    except Exception as error:  # a crash is a finding too, so report it and carry on
        record(name, "FAIL", f"crashed with {type(error).__name__}: {error}")


def _elevated() -> bool:
    if sys.platform == "win32":
        import ctypes

        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    return os.geteuid() == 0


if __name__ == "__main__":
    sys.exit(main())
