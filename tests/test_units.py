"""Tests for parsing and formatting durations, sizes and rates. Run with: uv run pytest"""

from __future__ import annotations

import pytest
from builders import MB

from submeter.core.units import (
    format_duration,
    format_size,
    parse_duration,
    parse_rate,
    parse_size,
)


def test_units_round_trip() -> None:
    assert parse_duration("250ms") == 0.25
    assert parse_duration("48h") == 172800
    assert parse_size("2GB") == 2 * 1024**3
    assert parse_rate("50MB/h") == pytest.approx(50 * MB / 3600)
    assert format_duration(172800) == "2d"
    assert format_size(1.5 * 1024**3) == "1.5 GB"
    with pytest.raises(ValueError, match="not a duration"):
        parse_duration("soon")
