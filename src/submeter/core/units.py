"""Durations, sizes, rates and percentages, written the way a person writes them.

Settings say "250ms", "48h", "2GB", "50MB/h" and "1%". Inside the program
everything is seconds, bytes, bytes per second and fractions. This module is
the only place that converts between the two, so every complaint about a
malformed value comes from here and reads the same way.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from typing import Annotated, Final

from pydantic import BeforeValidator

FOREVER: Final[float] = math.inf

_DURATION_UNITS: Final[dict[str, float]] = {
    "ms": 0.001,
    "s": 1.0,
    "m": 60.0,
    "h": 3600.0,
    "d": 86400.0,
    "w": 604800.0,
    "y": 31536000.0,
}
_SIZE_UNITS: Final[dict[str, int]] = {
    "": 1,
    "k": 1024,
    "m": 1024**2,
    "g": 1024**3,
    "t": 1024**4,
}
_NUMBER: Final = r"(\d+(?:\.\d+)?)"
_DURATION_RE: Final = re.compile(rf"^\s*{_NUMBER}\s*(ms|s|m|h|d|w|y)\s*$")
_SIZE_RE: Final = re.compile(rf"^\s*{_NUMBER}\s*([kmgt]?)i?b\s*$", re.IGNORECASE)
_PERCENT_RE: Final = re.compile(rf"^\s*{_NUMBER}\s*%\s*$")


def parse_duration(value: object) -> float:
    """Return seconds for "250ms", "5m", "48h", "forever" or a plain number of seconds."""
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        if value.strip().lower() == "forever":
            return FOREVER
        match = _DURATION_RE.match(value)
        if match:
            return float(match.group(1)) * _DURATION_UNITS[match.group(2)]
    raise ValueError(f"not a duration: {value!r} (write it like '250ms', '5m' or '48h')")


def parse_size(value: object) -> int:
    """Return bytes for "8MB" or "2GB". Units are binary, so 1 GB is 1024**3 bytes."""
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        match = _SIZE_RE.match(value)
        if match:
            return round(float(match.group(1)) * _SIZE_UNITS[match.group(2).lower()])
    raise ValueError(f"not a size: {value!r} (write it like '8MB' or '2GB')")


def parse_percent(value: object) -> float:
    """Return a fraction for "1%". A bare number is taken as a fraction already."""
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        match = _PERCENT_RE.match(value)
        if match:
            return float(match.group(1)) / 100.0
    raise ValueError(f"not a percentage: {value!r} (write it like '1%')")


def parse_rate(value: object) -> float:
    """Return bytes per second for "50MB/h". A bare number is bytes per second."""
    if isinstance(value, int | float) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str) and "/" in value:
        size, _, per = value.partition("/")
        try:
            return parse_size(size) / parse_duration("1" + per.strip())
        except ValueError:
            pass
    raise ValueError(f"not a rate: {value!r} (write it like '50MB/h')")


def format_duration(seconds: float) -> str:
    """Write seconds back in the largest unit that divides them evenly."""
    if math.isinf(seconds):
        return "forever"
    if 0 < seconds < 1:
        return f"{round(seconds * 1000)}ms"
    for unit in ("d", "h", "m", "s"):
        size = _DURATION_UNITS[unit]
        if seconds >= size and math.isclose(seconds / size, round(seconds / size)):
            return f"{round(seconds / size)}{unit}"
    return f"{seconds:g}s"


def format_size(size: float) -> str:
    """Write bytes with a binary unit and at most two decimals."""
    for prefix in ("t", "g", "m", "k"):
        unit = _SIZE_UNITS[prefix]
        if abs(size) >= unit:
            return f"{size / unit:.2f}".rstrip("0").rstrip(".") + f" {prefix.upper()}B"
    return f"{round(size)} B"


def duration_range(low: str, high: str) -> Callable[[float], float]:
    """Build a validator that refuses durations outside low..high and says so."""
    lowest, highest = parse_duration(low), parse_duration(high)

    def check(value: float) -> float:
        if not lowest <= value <= highest:
            shown = format_duration(value)
            raise ValueError(f"{shown} is outside the allowed range, {low} to {high}")
        return value

    return check


def fraction_range(low: str, high: str) -> Callable[[float], float]:
    """Build a validator that refuses fractions outside low..high, written as percentages."""
    lowest, highest = parse_percent(low), parse_percent(high)

    def check(value: float) -> float:
        if not lowest <= value <= highest:
            raise ValueError(f"{value:.2%} is outside the allowed range, {low} to {high}")
        return value

    return check


Duration = Annotated[float, BeforeValidator(parse_duration)]
Size = Annotated[int, BeforeValidator(parse_size)]
Fraction = Annotated[float, BeforeValidator(parse_percent)]
Rate = Annotated[float, BeforeValidator(parse_rate)]
