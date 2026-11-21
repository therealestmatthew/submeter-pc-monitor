"""Tests for the redaction of command lines on their way into the store."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from submeter.core.models import SampleBatch
from submeter.privacy.redact import REDACTED, redact_cmdline
from submeter.store.raw import RawFile


def stored(tmp_path: Path, cmdline: tuple[str, ...], exe: str, **settings: Any) -> bytes:
    """Write one process through a RawFile and return the closed file's bytes."""
    process: dict[str, Any] = {"key": {"pid": 1, "started": 1.0}, "exe": exe, "cmdline": cmdline}
    process |= {"cwd": None, "parent_pid": None, "cpu_s": 0.0, "io_read_bytes": 0, "threads": 1}
    process |= {"io_write_bytes": 0, "memory_bytes": 1, "first_seen": True, "restricted": False}
    batch: dict[str, Any] = {"taken_at": 1.0, "interval_s": 1.0, "processes": [process]}
    batch |= {"gap": False, "exited": [], "logical_cores": 1, "cpu_busy_s": 0.0}
    batch |= {"memory_available_bytes": 1}
    raw = RawFile(tmp_path / "day.db", **settings)
    raw.write(SampleBatch.model_validate(batch), [], {})
    raw.close()
    return raw.path.read_bytes()


def test_exe_only_stores_the_executable_and_scrub_splits_a_title(tmp_path: Path) -> None:
    """R97: a title a process wrote over its argv[0] is never stored whole."""
    title = ("postgres: alice appdb 10.0.0.5(5432) idle",)
    assert b"alice" not in stored(tmp_path, title, "postgres", redaction="exe_only")
    assert redact_cmdline(title, mode="exe_only", exe="postgres") == ("postgres",)
    secret = ("worker --api-key sk-abcdefghijklmnopqrstu",)
    assert redact_cmdline(secret) == ("worker", "--api-key", REDACTED)
