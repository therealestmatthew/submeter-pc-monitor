"""Tests for the store's files, tiers, retention and lock. Run with: uv run pytest"""

from __future__ import annotations

import os
import stat
import sys
import threading
import types
from datetime import date
from pathlib import Path

import psutil
import pytest
from builders import DAY0, HOUR

from submeter.core.models import Tier
from submeter.store.files import FileMap, InstanceLock
from submeter.store.query import choose_tier
from submeter.store.raw import RawFile


def test_file_map_names_expiry_and_lock(tmp_path: Path) -> None:
    windows = FileMap.discover({"APPDATA": "C:/R", "LOCALAPPDATA": "C:/L"}, "win32")
    assert windows.settings_file == Path("C:/R/Submeter/submeter.toml")
    files = FileMap.discover({"SUBMETER_HOME": str(tmp_path)})
    files.ensure()
    day = date(2026, 11, 20)
    assert (
        files.raw_file(day).name == "2026-11-20.db" and files.minute_file(day).name == "2026-W47.db"
    )
    for name in ("2026-11-17.db", "2026-11-18.db", "2026-11-20.db"):
        (files.raw_dir / name).write_bytes(b"x")
    now = DAY0 + 9 * 3600  # 09:00 UTC on the 20th
    expired = files.expired_raw(now, 48 * 3600, rolled_up_until=now)
    assert [path.name for path in expired] == ["2026-11-17.db"]
    assert files.disk_use()["raw"] == 3
    lock = InstanceLock(files.lock_file("collector"))
    with lock:
        assert not InstanceLock(files.lock_file("collector")).acquire(wait_s=0)
        assert lock.holder() == os.getpid() and files.lock_file("collector").stat().st_size == 0
    assert lock.holder() is None  # the pid file goes when the lock is released
    again = InstanceLock(files.lock_file("collector"))
    assert again.acquire()
    again.release()


def test_the_windows_lock_makes_the_calls_windows_expects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stand-in for msvcrt: this checks the calls, not how Windows answers them."""
    calls: list[tuple[int, int, int]] = []
    held: set[int] = set()

    def locking(fd: int, mode: int, nbytes: int) -> None:
        inode = os.fstat(fd).st_ino
        calls.append((mode, nbytes, os.lseek(fd, 0, os.SEEK_CUR)))
        if mode == 2:  # LK_NBLCK: fail at once if any other handle holds the byte
            if inode in held:
                raise PermissionError(13, "Permission denied")
            held.add(inode)
        else:
            held.discard(inode)

    fake = types.ModuleType("msvcrt")
    fake.LK_NBLCK, fake.LK_UNLCK, fake.locking = 2, 0, locking  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "msvcrt", fake)
    monkeypatch.setattr(sys, "platform", "win32")
    path = tmp_path / "collector.lock"
    first, second = InstanceLock(path), InstanceLock(path)
    assert first.acquire() and not second.acquire(wait_s=0)
    assert first.holder() == os.getpid() and path.read_bytes() == b""
    first.release()
    assert second.acquire()
    second.release()
    # every call is on one byte at offset 0: try, try and fail, probe and fail, unlock, try, unlock
    assert calls == [(2, 1, 0), (2, 1, 0), (2, 1, 0), (0, 1, 0), (2, 1, 0), (0, 1, 0)]


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


@pytest.mark.skipif(sys.platform == "win32", reason="permission bits mean nothing on Windows")
def test_submeter_files_are_private_to_the_user(tmp_path: Path) -> None:
    """R100: under umask 0o022, folders are 0700 and files 0600, and anything else is flagged."""
    files = FileMap.discover({"SUBMETER_HOME": str(tmp_path)})
    mask = os.umask(0o022)
    try:
        files.raw_dir.mkdir(parents=True)  # made before this rule, at 0755
        files.ensure()
        raw = RawFile(files.raw_file(date(2026, 11, 20)))
        lock = InstanceLock(files.lock_file("collector"))
        assert lock.acquire()
    finally:
        os.umask(mask)
    folders = (files.settings_dir, files.data_dir, files.raw_dir, files.state_dir, files.logs_dir)
    assert {stat.S_IMODE(folder.stat().st_mode) for folder in folders} == {0o700}
    assert {stat.S_IMODE(path.stat().st_mode) for path in (raw.path, lock.pid_file)} == {0o600}
    assert files.readable_by_others() == []
    lock.pid_file.chmod(0o644)
    assert files.readable_by_others() == [str(lock.pid_file)]
    lock.release()
    raw.close()
