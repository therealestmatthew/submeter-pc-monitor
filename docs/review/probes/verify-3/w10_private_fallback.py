"""Probe W10: what the provider records as memory when psutil's memory_info lacks 'private'.

Replaces psutil.Process.memory_info for this process with two stand-ins shaped like psutil's
Windows result: one with a 'private' field and one without it (as after the alias is removed).
Reads this process through PsutilProvider._read and reports the memory figure it kept, and
whether any warning or error was raised. Logic only; nothing is written.

Run from the repository root:  uv run python docs/review/probes/verify-3/w10_private_fallback.py
"""

from __future__ import annotations

import os
import warnings
from collections import namedtuple

import psutil

from submeter.providers.psutil_provider import PsutilProvider

WithPrivate = namedtuple("WithPrivate", "rss vms private")
WithoutPrivate = namedtuple("WithoutPrivate", "rss vms")
RSS, VMS = 111_000_000, 333_000_000


def read_with(fake: object) -> tuple[int | None, list[str]]:
    # Patch the platform layer that psutil.Process.memory_info delegates to, so psutil's own
    # oneshot() caching stays intact.
    platform_process = psutil._psplatform.Process  # type: ignore[attr-defined]
    original = platform_process.memory_info
    platform_process.memory_info = lambda self: fake
    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            counters = PsutilProvider()._read(psutil.Process(os.getpid()))
        return (None if counters is None else counters.memory_bytes), [
            str(w.category.__name__) for w in caught
        ]
    finally:
        platform_process.memory_info = original


if __name__ == "__main__":
    kept, warned = read_with(WithPrivate(RSS, VMS, VMS))
    print(f"with 'private' (= {VMS}): provider kept {kept}; warnings: {warned or 'none'}")
    kept, warned = read_with(WithoutPrivate(RSS, VMS))
    print(
        f"without 'private': provider kept {kept} (rss is {RSS}, vms is {VMS}); "
        f"warnings: {warned or 'none'}; fell back to working set silently: {kept == RSS}"
    )
