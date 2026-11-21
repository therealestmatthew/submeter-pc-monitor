"""Verifier probe for S12 and S2: tier choice against retention, and what expired_raw can know.

Reads and measures only. Creates nothing. Nothing is timed.

    uv run python docs/review/probes/verify-6/v6_tiers.py

1. Does the settings model accept raw retention longer than minute retention?
2. With such settings, which tier does choose_tier pick for windows of several lengths and ages,
   and does that tier's retention still cover the window start?
3. The parameters of FileMap.expired_raw: can it be told what has been rolled up?
"""

from __future__ import annotations

import inspect

from submeter.core.config import Retention
from submeter.core.models import Tier
from submeter.store.files import FileMap
from submeter.store.query import choose_tier

DAY, HOUR = 86400.0, 3600.0
NOW = 1_795_132_800.0


def main() -> None:
    retention = Retention.model_validate({"raw": "60d", "minute": "30d"})
    print(
        f"1. Retention(raw='60d', minute='30d') accepted: raw {retention.raw / DAY:g} d, "
        f"minute {retention.minute / DAY:g} d"
    )
    keep = {Tier.RAW: retention.raw, Tier.MINUTE: retention.minute, Tier.HOUR: float("inf")}
    print("2. window age, span -> tier chosen; is the window start inside that tier's retention?")
    for age_d, span_h in ((45, 12), (45, 1), (45, 0.5), (35, 48), (10, 12), (59, 30)):
        start = NOW - age_d * DAY
        choice = choose_tier(
            start=start,
            end=start + span_h * HOUR,
            now=NOW,
            raw_retention_s=retention.raw,
            minute_retention_s=retention.minute,
        )
        held = NOW - start <= keep[choice.tier]
        print(
            f"   {age_d:>2} d back, {span_h:>4g} h -> {choice.tier.value:<6} step "
            f"{choice.step_s:g} s; covered: {held}"
        )
    print(f"3. expired_raw{inspect.signature(FileMap.expired_raw)}")


if __name__ == "__main__":
    main()
