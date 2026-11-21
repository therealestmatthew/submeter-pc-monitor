"""What every provider promises: say what it can deliver, then deliver a snapshot.

A provider is one source of data on one platform. The sampler depends only on
this protocol, so the psutil fallback, the Windows bulk snapshot and the Linux
/proc reader are interchangeable, and a test can pass in a fake.

Providers return cumulative counters and never rates. Turning counters into
per-interval figures is the sampler's job.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol, runtime_checkable

from submeter.core.models import Capability, Snapshot


@runtime_checkable
class ProcessProvider(Protocol):
    """Reads every process on the machine in one call."""

    name: str

    def capability(self) -> Capability:
        """Full, partial (with what is missing) or unavailable (with why)."""
        ...

    def snapshot(self) -> Snapshot:
        """Cumulative counters for every process, stamped with both clocks."""
        ...


def capability_report(providers: Iterable[ProcessProvider]) -> tuple[Capability, ...]:
    """The matrix `submeter doctor` prints, in a stable order."""
    return tuple(sorted((p.capability() for p in providers), key=lambda c: c.name))
