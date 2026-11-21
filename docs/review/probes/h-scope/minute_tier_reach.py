"""Which chart windows does the minute tier actually answer?

Logic only, no timing. Calls the baseline's store.query.choose_tier over a grid
of window spans and window ages, with the default retention (raw 48 h, minute
30 d) and raw intervals of 1 s and 2 s, and prints the tier each window gets.
It also says which documented checks read the minute tier (docs/06 lines 59-67).

Run: uv run python docs/review/probes/h-scope/minute_tier_reach.py
"""

from __future__ import annotations

from submeter.core.models import Tier
from submeter.store.query import choose_tier

H, D = 3600.0, 86400.0
RAW_RET, MINUTE_RET = 48 * H, 30 * D
NOW = 100 * D
SPANS = [("10 min", 600.0), ("1 h", H), ("6 h", 6 * H), ("24 h", D), ("2 d", 2 * D)]
SPANS += [("7 d", 7 * D), ("30 d", 30 * D)]
AGES = [("ends now", 0.0), ("ended 3 d ago", 3 * D), ("ended 20 d ago", 20 * D)]


def tier_for(span: float, ends_ago: float, raw_interval: float) -> str:
    end = NOW - ends_ago
    choice = choose_tier(
        start=end - span,
        end=end,
        now=NOW,
        raw_retention_s=RAW_RET,
        minute_retention_s=MINUTE_RET,
        raw_interval_s=raw_interval,
    )
    return f"{choice.tier.value}/{choice.step_s:g}s"


def main() -> None:
    for raw_interval in (1.0, 2.0):
        print(f"raw interval {raw_interval:g} s, max 2000 points per answer")
        print("  span      " + "".join(f"{label:>18}" for label, _ in AGES))
        minute_cells = 0
        for name, span in SPANS:
            cells = [tier_for(span, ago, raw_interval) for _, ago in AGES]
            minute_cells += sum(cell.startswith(Tier.MINUTE.value) for cell in cells)
            print(f"  {name:<9} " + "".join(f"{cell:>18}" for cell in cells))
        print(f"  windows answered by the minute tier: {minute_cells} of {len(SPANS) * len(AGES)}")
        lo, hi = 2000 * raw_interval, 2000 * 60.0
        print(f"  minute tier is chosen for spans over {lo / 60:g} min and up to {hi / H:.1f} h")
    print("documented readers of the minute tier (docs/06:59-67): leak check, 2 to 48 h back,")
    print("which lies inside raw retention; baseline, 14 d back. Every other check reads raw,")
    print("hourly buckets or stored totals.")


if __name__ == "__main__":
    main()
