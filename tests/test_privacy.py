"""Tests for the redaction of command lines on their way into the store."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from submeter.core.config import Privacy, Settings
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
    assert stored(tmp_path / "a", ("tool", "--x"), "") == stored(tmp_path / "b", (), "")  # no exe
    secret = ("worker --api-key sk-abcdefghijklmnopqrstu",)
    assert redact_cmdline(secret) == ("worker", "--api-key", REDACTED)


SCRUB_MISSES = (  # scrub is best-effort: these common forms pass through it unchanged
    ("curl", "-H", "Authorization: Bearer FAKEtok-1"),
    ("mysql", "-uroot", "-pFAKEpw-7x", "db"),
    ("curl", "-u", "alice:FAKEpw-7x", "https://example.invalid"),
    ("bash", "-c", "tool --api-key FAKEtok-1"),
    ("docker", "run", "--env=API_TOKEN=FAKEtok-1", "image"),
    ("app", "Server=db;User Id=sa;Password=FAKEpw-7x;"),
)


def test_exe_only_is_the_default_because_scrub_misses_common_forms(tmp_path: Path) -> None:
    """R96: by default only the executable is stored; scrub is an opt-in, best-effort mode."""
    assert b"FAKEpw" not in stored(tmp_path, ("mysql", "-pFAKEpw-7x"), "mysql")
    assert Settings().privacy.redaction == "exe_only"
    assert [redact_cmdline(args) for args in SCRUB_MISSES] == list(SCRUB_MISSES)


def test_scrub_keeps_harmless_words_paths_and_uuids() -> None:
    """R99: a secret word counts where a word ends, and only paths from '/' and UUIDs are kept."""
    path, uuid = "/srv/0123456789abcdef0123456789abcdef/out", "123e4567-e89b-12d3-a456-426614174000"
    args = ("tool", "--compass", "--bypass-cache", path, "--resume", uuid, "--password", "hunter2")
    assert redact_cmdline(args) == (*args[:-1], REDACTED)
    flags = ("-storepass", "-keypass", "--passphrase", "-passin", "--authtoken", "--dbpassword")
    assert [redact_cmdline(("tool", flag, "FAKEpw-1"))[2] for flag in flags] == [REDACTED] * 6
    pairs = ("PGPASSWORD=FAKEpw-7", "-Djavax.net.ssl.trustStorePassword=FAKEpw-5")
    assert not any("FAKE" in arg for arg in redact_cmdline(("java", *pairs)))
    assert redact_cmdline(("aws", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY")) == ("aws", REDACTED)


def test_redact_patterns_are_checked_and_reach_the_store(tmp_path: Path) -> None:
    """R133: a bad pattern is refused by name, and a good one hides text on the way to disk."""
    with pytest.raises(ValidationError, match=r"'\['"):
        Privacy(redact_patterns=("[",))
    settings: dict[str, Any] = {"redaction": "scrub", "redact_patterns": ("corp-[0-9]{6}",)}
    assert b"corp-123456" not in stored(tmp_path, ("tool", "corp-123456"), "tool", **settings)
