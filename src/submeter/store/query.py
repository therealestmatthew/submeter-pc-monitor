"""Choose which tier answers a question, and say so.

A window is answered from the finest tier that still holds its whole span:
raw samples if the window starts within raw retention, minute buckets if it
starts within minute retention, hourly buckets otherwise. If that would return
more points than a chart can use, the choice moves to a coarser tier, and then
to wider steps. Every answer carries the tier and resolution it came from, so
a chart can state them and never mixes tiers without saying so.
"""

from __future__ import annotations

import math

from submeter.core.models import Record, Tier

_WIDTH_S = {Tier.MINUTE: 60.0, Tier.HOUR: 3600.0}


class TierChoice(Record):
    tier: Tier
    step_s: float
    reason: str


def choose_tier(
    *,
    start: float,
    end: float,
    now: float,
    raw_retention_s: float,
    minute_retention_s: float,
    raw_interval_s: float = 1.0,
    max_points: int = 2000,
) -> TierChoice:
    if end <= start:
        raise ValueError("the window must end after it starts")
    span, age = end - start, now - start
    widths = {Tier.RAW: raw_interval_s, **_WIDTH_S}
    if age <= raw_retention_s:
        tiers, reason = [Tier.RAW, Tier.MINUTE, Tier.HOUR], "window is inside raw retention"
    elif age <= minute_retention_s:
        tiers, reason = [Tier.MINUTE, Tier.HOUR], "window starts before raw retention"
    else:
        tiers, reason = [Tier.HOUR], "window starts before minute retention"
    for tier in tiers:
        if span / widths[tier] <= max_points:
            if tier is not tiers[0]:
                reason += f"; {tiers[0].value} would exceed {max_points} points"
            return TierChoice(tier=tier, step_s=widths[tier], reason=reason)
    coarsest = tiers[-1]
    step = widths[coarsest] * math.ceil(span / widths[coarsest] / max_points)
    reason += f"; {coarsest.value} buckets merged to stay under {max_points} points"
    return TierChoice(tier=coarsest, step_s=step, reason=reason)
