"""Tests for the store's files, tiers, retention and lock. Run with: uv run pytest"""

from __future__ import annotations

from submeter.core.models import Tier
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
