"""Fold samples into buckets, and buckets into larger buckets, without losing the totals.

A bucket keeps sums for counters, the minimum, maximum, time-weighted mean and
last value for gauges, a time-weighted histogram for cores in use and for
memory, and how many seconds it really covers. That is enough to merge any
number of buckets exactly: a week's CPU-hours is a sum of sums, and a week's
95th percentile is read from merged bins.

The same functions build minute buckets from raw samples and hourly buckets
from minute buckets. Nothing here touches a file.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence

from submeter.core import histogram
from submeter.core.models import Bucket, WorkloadSample


def bucket_start(timestamp: float, width_s: float) -> float:
    return math.floor(timestamp / width_s) * width_s


class SeriesAccumulator:
    """Collects the samples of one series that fall inside one bucket."""

    def __init__(
        self,
        *,
        series: str,
        start: float,
        width_s: float,
        logical_cores: int,
        epoch: int = 0,
        active_share: float = 0.005,
    ) -> None:
        self._series, self._start, self._width_s = series, start, width_s
        self._logical_cores, self._epoch, self._active_share = logical_cores, epoch, active_share
        self._covered_s = self._active_s = self._cpu_s = self._memory_weighted = 0.0
        self._samples = self._read = self._write = self._started = self._processes_max = 0
        self._memory_min: int | None = None
        self._memory_max = self._memory_last = 0
        self._cores = histogram.empty(histogram.CORES)
        self._memory = histogram.empty(histogram.MEMORY)

    def add(self, sample: WorkloadSample) -> None:
        interval = sample.interval_s
        if interval <= 0:
            return
        cores = sample.cpu_s / interval
        self._covered_s += interval
        self._samples += 1
        self._cpu_s += sample.cpu_s
        self._read += sample.io_read_bytes
        self._write += sample.io_write_bytes
        self._started += sample.started
        self._processes_max = max(self._processes_max, sample.processes)
        self._memory_weighted += sample.memory_bytes * interval
        self._memory_max = max(self._memory_max, sample.memory_bytes)
        self._memory_min = (
            sample.memory_bytes
            if self._memory_min is None
            else min(self._memory_min, sample.memory_bytes)
        )
        self._memory_last = sample.memory_bytes
        if cores >= self._active_share:
            self._active_s += interval
        histogram.add(self._cores, histogram.CORES, cores, interval)
        histogram.add(self._memory, histogram.MEMORY, sample.memory_bytes, interval)

    def close(self) -> Bucket | None:
        """The finished bucket, or None if nothing was observed."""
        if self._memory_min is None:
            return None
        return Bucket(
            series=self._series,
            start=self._start,
            width_s=self._width_s,
            covered_s=self._covered_s,
            samples=self._samples,
            active_s=self._active_s,
            cpu_s=self._cpu_s,
            io_read_bytes=self._read,
            io_write_bytes=self._write,
            started=self._started,
            memory_min=self._memory_min,
            memory_max=self._memory_max,
            memory_mean=self._memory_weighted / self._covered_s,
            memory_last=self._memory_last,
            processes_max=self._processes_max,
            cores_hist=tuple(self._cores),
            memory_hist=tuple(self._memory),
            logical_cores=self._logical_cores,
            epoch=self._epoch,
        )


def roll_up(
    samples: Iterable[WorkloadSample],
    *,
    width_s: float,
    logical_cores: int,
    epoch: int = 0,
) -> list[Bucket]:
    """Group samples by workload and bucket, and return the finished buckets in time order."""
    open_buckets: dict[tuple[float, str], SeriesAccumulator] = {}
    for sample in samples:
        start = bucket_start(sample.taken_at, width_s)
        accumulator = open_buckets.get((start, sample.workload))
        if accumulator is None:
            accumulator = SeriesAccumulator(
                series=sample.workload,
                start=start,
                width_s=width_s,
                logical_cores=logical_cores,
                epoch=epoch,
            )
            open_buckets[(start, sample.workload)] = accumulator
        accumulator.add(sample)
    closed = (open_buckets[key].close() for key in sorted(open_buckets))
    return [bucket for bucket in closed if bucket is not None]


def merge(buckets: Sequence[Bucket], *, start: float, width_s: float) -> Bucket:
    """Combine buckets of one series into one wider bucket. Sums stay sums."""
    if not buckets:
        raise ValueError("nothing to merge")
    if len({bucket.series for bucket in buckets}) != 1:
        raise ValueError("buckets of different series cannot be merged")
    ordered = sorted(buckets, key=lambda bucket: bucket.start)
    covered = sum(bucket.covered_s for bucket in ordered)
    cores = ordered[0].cores_hist
    memory = ordered[0].memory_hist
    for bucket in ordered[1:]:
        cores = histogram.merge(cores, bucket.cores_hist)
        memory = histogram.merge(memory, bucket.memory_hist)
    latest = ordered[-1]
    return Bucket(
        series=latest.series,
        start=start,
        width_s=width_s,
        covered_s=covered,
        samples=sum(bucket.samples for bucket in ordered),
        active_s=sum(bucket.active_s for bucket in ordered),
        cpu_s=sum(bucket.cpu_s for bucket in ordered),
        io_read_bytes=sum(bucket.io_read_bytes for bucket in ordered),
        io_write_bytes=sum(bucket.io_write_bytes for bucket in ordered),
        started=sum(bucket.started for bucket in ordered),
        memory_min=min(bucket.memory_min for bucket in ordered),
        memory_max=max(bucket.memory_max for bucket in ordered),
        memory_mean=sum(bucket.memory_mean * bucket.covered_s for bucket in ordered) / covered,
        memory_last=latest.memory_last,
        processes_max=max(bucket.processes_max for bucket in ordered),
        cores_hist=cores,
        memory_hist=memory,
        logical_cores=latest.logical_cores,
        epoch=latest.epoch,
    )


def cores_percentile(bucket: Bucket, q: float) -> float | None:
    return histogram.percentile(bucket.cores_hist, histogram.CORES, q)


def memory_percentile(bucket: Bucket, q: float) -> float | None:
    return histogram.percentile(bucket.memory_hist, histogram.MEMORY, q)


def well_covered(bucket: Bucket, minimum: float = 0.5) -> bool:
    """Whether enough of the bucket was observed for baselines and trends to use it."""
    return bucket.covered_s >= minimum * bucket.width_s
