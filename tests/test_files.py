"""Tests for the store's files, tiers, retention and lock. Run with: uv run pytest"""

from __future__ import annotations

import os
import threading
from pathlib import Path

import psutil

from submeter.core.models import Tier
from submeter.store.files import FileMap, InstanceLock
from submeter.store.query import choose_tier
from submeter.store.raw import RawFile

DAY0 = 1_795_132_800.0  # 2026-11-20 00:00:00 UTC
HOUR = 3600.0


def test_tier_choice_takes_raw_coverage_from_disk() -> None:
    """R139: raw on disk covers only the last 30 h, so a window 40 h back cannot come from raw."""
    start = DAY0 - 40 * HOUR
    choice = choose_tier(
        start=start,
        end=start + 20 * 60,
        now=DAY0,
        raw_covered_from=DAY0 - 30 * HOUR,
        minute_retention_s=30 * 24 * HOUR,
    )
    assert (choice.tier, choice.step_s) == (Tier.MINUTE, 60.0)


def test_expired_raw_takes_the_side_files_with_the_day(tmp_path: Path) -> None:
    """R130: deleting only the .db would leave its -wal and -shm behind, counted forever."""
    files = FileMap.discover({"SUBMETER_HOME": str(tmp_path)})
    files.ensure()
    for name in ("2026-11-17.db", "2026-11-17.db-wal", "2026-11-17.db-shm", "2026-11-20.db"):
        (files.raw_dir / name).write_bytes(b"x")
    now = DAY0 + 9 * HOUR
    expired = files.expired_raw(now, 48 * HOUR, rolled_up_until=now)
    # the side files come first, so a pass cut short leaves the .db to be found next time
    assert [path.name for path in expired] == [
        "2026-11-17.db-wal",
        "2026-11-17.db-shm",
        "2026-11-17.db",
    ]


def test_expired_raw_waits_for_the_rolled_up_mark(tmp_path: Path) -> None:
    """R88: a raw day is never offered for deletion before its hourly buckets are built."""
    files = FileMap.discover({"SUBMETER_HOME": str(tmp_path)})
    files.ensure()
    for day in (17, 18, 19, 20):
        (files.raw_dir / f"2026-11-{day}.db").write_bytes(b"x")
    now, end_of_17th = DAY0 + 9 * HOUR, DAY0 - 48 * HOUR
    # retention alone (24 h) would expire the 17th and the 18th
    expired = files.expired_raw(now, 24 * HOUR, rolled_up_until=end_of_17th)
    assert [path.name for path in expired] == ["2026-11-17.db"]


def test_write_ahead_logs_are_bounded_and_counted(tmp_path: Path) -> None:
    """R129: 4 MiB of log left after a checkpoint, and the history file's log is in disk_use."""
    raw = RawFile(tmp_path / "day.db")
    assert raw._db.execute("PRAGMA journal_size_limit").fetchone() == (4 * 1024**2,)
    raw.close()
    files = FileMap.discover({"SUBMETER_HOME": str(tmp_path)})
    files.ensure()
    files.history_file.write_bytes(b"x" * 10)
    files.history_file.with_name("history.db-wal").write_bytes(b"x" * 5)
    assert files.disk_use()["history"] == 15


def test_holder_names_only_the_live_holder_of_a_held_lock(tmp_path: Path) -> None:
    """R105: a stale or reused pid is never reported, so nothing can signal an unrelated process."""
    path = tmp_path / "collector.lock"
    crashed = InstanceLock(path)
    assert crashed.acquire() and crashed._fd is not None
    os.close(crashed._fd)  # the holder dies: the system frees the lock and the pid file stays
    assert crashed.pid_file.exists() and InstanceLock(path).holder() is None
    with InstanceLock(path) as lock:
        assert lock.holder() == os.getpid()
        started = psutil.Process().create_time()
        lock.pid_file.write_text(f"{os.getpid()} {started + 1}", encoding="ascii")
        assert lock.holder() is None  # that pid now names a process that started at another time


def test_acquire_waits_for_a_lock_freed_late(tmp_path: Path) -> None:
    """R71: Windows may free a dead holder's lock some time after it dies, so acquire() retries."""
    path = tmp_path / "collector.lock"
    first, second = InstanceLock(path), InstanceLock(path)
    assert first.acquire()
    threading.Timer(0.3, first.release).start()
    assert second.acquire(wait_s=1.0)
    second.release()
