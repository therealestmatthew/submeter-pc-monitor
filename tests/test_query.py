"""Tests for the choice of tier and step for a window of history."""

from __future__ import annotations

from builders import DAY0

from submeter.core.models import Tier
from submeter.store.query import TierChoice, choose_tier


def tier(start: float) -> TierChoice:
    return choose_tier(
        start=start,
        end=DAY0,
        now=DAY0,
        raw_covered_from=DAY0 - 48 * 3600.0,
        minute_retention_s=30 * 86400.0,
    )


def test_tier_choice_follows_retention_and_point_budget() -> None:
    assert tier(DAY0 - 300).tier is Tier.RAW
    assert tier(DAY0 - 6 * 3600).tier is Tier.MINUTE
    assert tier(DAY0 - 7 * 86400).tier is Tier.HOUR
    year = tier(DAY0 - 365 * 86400)
    assert year.tier is Tier.HOUR and year.step_s == 5 * 3600 and "merged" in year.reason
