"""Where every file lives, what it is called, and when it has expired.

Data that expires together lives in a file together: one raw file per UTC day,
one minute file per ISO week, one history file. Retention is then a file
delete. This module owns the names and locations, so no other module builds a
path by hand, and it provides the lock that stops two copies of a program
running at once.

SUBMETER_HOME moves everything under one folder, which is what tests and
portable installs use.
"""

from __future__ import annotations

import contextlib
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from types import TracebackType
from typing import Final, Literal

HOME_VARIABLE: Final = "SUBMETER_HOME"
Program = Literal["collector", "server"]


def utc_day(timestamp: float) -> date:
    return datetime.fromtimestamp(timestamp, UTC).date()


def _end_of(day: date, days: int) -> float:
    return datetime.combine(day + timedelta(days=days), datetime.min.time(), UTC).timestamp()


@dataclass(frozen=True, slots=True)
class FileMap:
    settings_dir: Path
    data_dir: Path
    state_dir: Path

    @classmethod
    def discover(cls, env: Mapping[str, str] | None = None, platform: str | None = None) -> FileMap:
        """Standard per-user locations for this platform, or one folder if SUBMETER_HOME is set."""
        variables = os.environ if env is None else env
        system = sys.platform if platform is None else platform
        home = variables.get(HOME_VARIABLE)
        if home:
            root = Path(home)
            return cls(root / "settings", root / "data", root / "state")
        if system == "win32":
            roaming = Path(variables.get("APPDATA") or Path.home() / "AppData" / "Roaming")
            local = Path(variables.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
            return cls(
                roaming / "Submeter", local / "Submeter" / "data", local / "Submeter" / "state"
            )
        config = Path(variables.get("XDG_CONFIG_HOME") or Path.home() / ".config")
        data = Path(variables.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")
        state = Path(variables.get("XDG_STATE_HOME") or Path.home() / ".local" / "state")
        return cls(config / "submeter", data / "submeter", state / "submeter")

    @property
    def settings_file(self) -> Path:
        return self.settings_dir / "submeter.toml"

    @property
    def rules_file(self) -> Path:
        return self.settings_dir / "rules.toml"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def minute_dir(self) -> Path:
        return self.data_dir / "minute"

    @property
    def history_file(self) -> Path:
        return self.data_dir / "history.db"

    @property
    def backups_dir(self) -> Path:
        return self.data_dir / "backups"

    @property
    def runs_dir(self) -> Path:
        return self.data_dir / "runs"

    @property
    def logs_dir(self) -> Path:
        return self.state_dir / "logs"

    @property
    def token_file(self) -> Path:
        return self.state_dir / "api-token"

    def lock_file(self, program: Program) -> Path:
        return self.state_dir / f"{program}.lock"

    def raw_file(self, day: date) -> Path:
        return self.raw_dir / f"{day.isoformat()}.db"

    def minute_file(self, day: date) -> Path:
        year, week, _ = day.isocalendar()
        return self.minute_dir / f"{year}-W{week:02d}.db"

    def ensure(self) -> None:
        """Create every directory. Safe to call at each start."""
        for folder in (
            self.settings_dir,
            self.raw_dir,
            self.minute_dir,
            self.backups_dir,
            self.runs_dir,
            self.logs_dir,
        ):
            folder.mkdir(parents=True, exist_ok=True)

    def expired_raw(self, now: float, retention_s: float, rolled_up_until: float) -> list[Path]:
        """Raw files whose whole day ended more than retention_s ago, oldest first.

        A day whose end is after the rolled-up-until mark is never offered, so no raw day goes
        before its hourly buckets are built. Each day's -wal and -shm come before its .db, so a
        pass cut short leaves the .db to find.
        """
        expired: list[Path] = []
        for path in sorted(self.raw_dir.glob("*.db")):
            try:
                day = date.fromisoformat(path.stem)
            except ValueError:
                continue
            day_end = _end_of(day, 1)
            if now - day_end > retention_s and day_end <= rolled_up_until:
                sides = (path.with_name(path.name + end) for end in ("-wal", "-shm"))
                expired += [*(side for side in sides if side.exists()), path]
        return expired

    def expired_minute(self, now: float, retention_s: float) -> list[Path]:
        """Minute files whose whole week ended more than retention_s ago, oldest first."""
        expired = []
        for path in sorted(self.minute_dir.glob("*.db")):
            try:
                year, week = path.stem.split("-W")
                monday = date.fromisocalendar(int(year), int(week), 1)
            except ValueError:
                continue
            if now - _end_of(monday, 7) > retention_s:
                expired.append(path)
        return expired

    def disk_use(self) -> dict[str, int]:
        """Bytes on disk per kind of file, for `submeter store status` and the budget."""

        def size(folder: Path, pattern: str) -> int:
            return sum(path.stat().st_size for path in folder.glob(pattern) if path.is_file())

        history = self.history_file.stat().st_size if self.history_file.exists() else 0
        return {
            "raw": size(self.raw_dir, "*.db*"),
            "minute": size(self.minute_dir, "*.db*"),
            "history": history,
            "backups": size(self.backups_dir, "*.db"),
            "logs": size(self.logs_dir, "*.log*"),
        }


def _try_lock(fd: int) -> bool:
    """Take an exclusive lock on an open file without waiting. False when another holder has it.

    Windows locks one byte at the start of the file, which may lie past the end of an empty file.
    The lock belongs to the handle, so the file itself is never written: other programs could
    not read a locked byte, and nothing here depends on its contents.
    """
    try:
        if sys.platform == "win32":
            import msvcrt

            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return False
    return True


def _unlock(fd: int) -> None:
    """Give the lock back. Closing the file would also do it; this keeps the order explicit."""
    try:
        if sys.platform == "win32":
            import msvcrt

            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_UN)
    except OSError:
        pass


class InstanceLock:
    """An exclusive lock held for as long as a program runs, so two copies cannot.

    The lock file is only ever locked, never written. The holder's pid goes in a file beside it,
    NAME.pid, which anyone may read. The operating system frees the lock if the holder dies.

    The POSIX path is exercised by the tests. The Windows path is exercised against a stand-in
    for msvcrt, which checks the calls made but not how Windows answers them. It still needs
    running on Windows: see docs/reference/windows-priorities.md.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._fd: int | None = None

    @property
    def pid_file(self) -> Path:
        return self._path.with_suffix(".pid")

    def acquire(self) -> bool:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(self._path, os.O_RDWR | os.O_CREAT, 0o600)
        except OSError:
            return False  # on Windows another holder can make even opening fail
        if not _try_lock(fd):
            os.close(fd)
            return False
        self._fd = fd
        with contextlib.suppress(OSError):  # the pid is a convenience; the lock is what matters
            self.pid_file.write_text(str(os.getpid()), encoding="ascii")
        return True

    def holder(self) -> int | None:
        """The pid recorded by whoever last took the lock, if it can be read."""
        try:
            return int(self.pid_file.read_text(encoding="ascii").strip())
        except (OSError, ValueError):
            return None

    def release(self) -> None:
        if self._fd is None:
            return
        with contextlib.suppress(OSError):
            self.pid_file.unlink()
        _unlock(self._fd)
        os.close(self._fd)
        self._fd = None

    def __enter__(self) -> InstanceLock:
        if not self.acquire():
            raise RuntimeError(f"another copy is already running (lock: {self._path})")
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        self.release()
