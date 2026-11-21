"""The records that cross a boundary: provider to sampler, sampler to store, store to reader.

Every record is frozen and rejects unknown fields, so it cannot be changed
after it is made and a misspelt field fails loudly instead of being dropped.
These classes are the contract between the collector, the server and the CLI.
Nothing here does any work; behaviour lives in the modules that use them.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Record(BaseModel):
    """Base for every record: immutable, and strict about its fields."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)


class Availability(StrEnum):
    FULL = "full"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


class AccountingSource(StrEnum):
    """How a workload's numbers were obtained, shown beside every total."""

    KERNEL = "kernel"
    POLLED = "polled"
    COUNTERS = "counters"
    PARTIAL = "partial"


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    SERIOUS = "serious"
    CRITICAL = "critical"


class Confidence(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class Tier(StrEnum):
    RAW = "raw"
    MINUTE = "minute"
    HOUR = "hour"


class Capability(Record):
    """What one provider can deliver at the current privilege level."""

    name: str
    status: Availability
    note: str = ""


class ProcessKey(Record):
    """A process is identified by pid plus start time, never by pid alone."""

    pid: int
    started: float


class ProcessCounters(Record):
    """Cumulative counters and current gauges for one process, as a provider read them."""

    key: ProcessKey
    parent_pid: int | None = None
    exe: str = ""
    cmdline: tuple[str, ...] | None = Field(default=None, repr=False)
    cwd: str | None = Field(default=None, repr=False)
    cpu_s: float
    children_cpu_s: float | None = None  # Linux cutime + cstime of reaped children; not read yet
    io_read_bytes: int | None = None
    io_write_bytes: int | None = None
    memory_bytes: int
    threads: int | None = None
    restricted: bool = False


class SystemCounters(Record):
    """Machine-wide counters. cpu_busy_s is cumulative, one entry per logical core."""

    logical_cores: int
    cpu_busy_s: tuple[float, ...]
    memory_total_bytes: int
    memory_available_bytes: int


class Snapshot(Record):
    """Everything one provider call returned, stamped with both clocks."""

    taken_at: float
    monotonic: float
    processes: tuple[ProcessCounters, ...]
    system: SystemCounters


class ProcessSample(Record):
    """What one process did during one interval. cpu_s and the I/O fields are deltas."""

    key: ProcessKey
    parent_pid: int | None
    exe: str
    cmdline: tuple[str, ...] | None = Field(repr=False)
    cwd: str | None = Field(repr=False)
    cpu_s: float
    io_read_bytes: int | None
    io_write_bytes: int | None
    memory_bytes: int
    threads: int | None
    first_seen: bool
    restricted: bool


class SampleBatch(Record):
    """One interval of the whole machine. When gap is true the interval was not observed."""

    taken_at: float
    interval_s: float
    gap: bool
    processes: tuple[ProcessSample, ...]
    exited: tuple[ProcessKey, ...]
    logical_cores: int
    cpu_busy_s: float
    memory_available_bytes: int


class WorkloadSample(Record):
    """One workload's totals for one interval, ready to store."""

    taken_at: float
    interval_s: float
    workload: str
    source: AccountingSource
    cpu_s: float
    memory_bytes: int
    io_read_bytes: int
    io_write_bytes: int
    processes: int
    started: int


class Bucket(Record):
    """One series over one bucket of time, holding everything needed to merge buckets exactly.

    Counters are sums. Gauges keep minimum, maximum, time-weighted mean and last value.
    The two histograms are time-weighted, so percentiles can be read after merging.
    """

    series: str
    start: float
    width_s: float
    covered_s: float
    samples: int
    active_s: float
    cpu_s: float
    io_read_bytes: int
    io_write_bytes: int
    started: int
    memory_min: int
    memory_max: int
    memory_mean: float
    memory_last: int
    processes_max: int
    cores_hist: tuple[float, ...]
    memory_hist: tuple[float, ...]
    logical_cores: int
    epoch: int


class Finding(Record):
    """Something a detector noticed, with the evidence that triggered it."""

    kind: str
    severity: Severity
    confidence: Confidence
    workload: str
    window_start: float
    window_end: float
    evidence: tuple[str, ...]
