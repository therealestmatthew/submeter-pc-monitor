"""Tests for the store's files, tiers, retention and lock. Run with: uv run pytest"""

from __future__ import annotations

from pathlib import Path

from submeter.core.models import Tier
from submeter.store.files import FileMap
from submeter.store.query import choose_tier

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
