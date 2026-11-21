"""Probe: drive the real Sampler with synthetic snapshots and print what it reports.

Nothing is read from the machine and nothing is written. Run from the repository root:

    uv run python docs/review/probes/e-baseline/sampler_cases.py

Each case prints the CPU the processes really used (from their cumulative counters) beside the
CPU the sampler credited, so lost or invented CPU time is visible as a difference.
"""

from __future__ import annotations

from submeter.collector.sampler import Sampler
from submeter.core.models import ProcessCounters, ProcessKey, SampleBatch, Snapshot, SystemCounters

MB = 1024**2


def proc(pid: int, cpu: float, *, started: float = 100.0, **extra: object) -> ProcessCounters:
    fields: dict[str, object] = {"exe": "tool", "cmdline": ("tool",), "memory_bytes": 50 * MB}
    fields.update(extra)
    return ProcessCounters(key=ProcessKey(pid=pid, started=started), cpu_s=cpu, **fields)


def snap(at: float, processes: list[ProcessCounters], mono: float | None = None) -> Snapshot:
    system = SystemCounters(
        logical_cores=4,
        cpu_busy_s=(0.0, 0.0, 0.0, 0.0),
        memory_total_bytes=16 * 1024**3,
        memory_available_bytes=8 * 1024**3,
    )
    return Snapshot(
        taken_at=at,
        monotonic=at if mono is None else mono,
        processes=tuple(processes),
        system=system,
    )


def credited(batch: SampleBatch | None) -> float:
    assert batch is not None
    return sum(sample.cpu_s for sample in batch.processes)


def restricted_then_readable() -> None:
    print("1. A process that is restricted in one snapshot and readable in the next")
    sampler = Sampler()
    sampler.ingest(snap(1000, [proc(7, 0.0, memory_bytes=0, restricted=True)]))
    batch = sampler.ingest(snap(1001, [proc(7, 5000.0)]))
    assert batch is not None
    sample = batch.processes[0]
    print(
        f"   interval {batch.interval_s:g} s, gap={batch.gap}, first_seen={sample.first_seen}: "
        f"credited {sample.cpu_s:g} CPU-s to a 1-second interval"
    )


def hot_only_snapshots() -> None:
    print("2. Snapshots that do not contain every process (hot set every 1 s, cold every 10 s)")
    sampler = Sampler()

    def everything(tick: int, *, with_cold: bool) -> list[ProcessCounters]:
        hot = [proc(1, 0.9 * tick)]  # one busy process
        cold = [proc(pid, 0.004 * tick, started=50.0) for pid in range(100, 130)]  # 30 quiet ones
        return hot + cold if with_cold else hot

    sampler.ingest(snap(1000, everything(0, with_cold=True)))
    hot_credit, cold_credit, exits, starts = 0.0, 0.0, 0, 0
    for tick in range(1, 21):
        batch = sampler.ingest(snap(1000 + tick, everything(tick, with_cold=tick % 10 == 0)))
        assert batch is not None and not batch.gap
        hot_credit += sum(s.cpu_s for s in batch.processes if s.key.pid == 1)
        cold_credit += sum(s.cpu_s for s in batch.processes if s.key.pid != 1)
        exits += len(batch.exited)
        starts += sum(sample.first_seen for sample in batch.processes)
    print(
        f"   20 s: hot process used {0.9 * 20:.2f} CPU-s, credited {hot_credit:.2f}; "
        f"30 cold processes used {30 * 0.004 * 20:.2f} CPU-s, credited {cold_credit:.2f}; "
        f"{exits} exits and {starts} starts were reported, and none happened"
    )


def legal_intervals_are_gaps() -> None:
    print("3. Intervals the settings allow, against the fixed 30-second gap rule")
    for label, interval in (
        ("idle_interval 20s x on_battery_multiplier 2", 40.0),
        ("idle_interval 60s", 60.0),
        ("cold_interval 60s", 60.0),
        ("idle_interval 5s x on_battery_multiplier 10", 50.0),
        ("idle_interval 5s x on_battery_multiplier 2", 10.0),
    ):
        sampler = Sampler()
        sampler.ingest(snap(1000, [proc(1, 5.0)]))
        batch = sampler.ingest(snap(1000 + interval, [proc(1, 5.0 + interval * 0.5)]))
        assert batch is not None
        print(
            f"   {label}: gap={batch.gap}, used {interval * 0.5:g} CPU-s, "
            f"credited {credited(batch):g}"
        )


def identity_flip() -> None:
    print("4. A process whose start time could not be read (0.0) and then could")
    sampler = Sampler()
    sampler.ingest(snap(1000, [proc(9, 0.0, started=0.0, restricted=True)]))
    batch = sampler.ingest(snap(1001, [proc(9, 40.0, started=500.0)]))
    assert batch is not None
    sample = batch.processes[0]
    print(
        f"   exited={[key.pid for key in batch.exited]}, first_seen={sample.first_seen}, "
        f"credited {sample.cpu_s:g} CPU-s: one process is recorded as an exit and a start"
    )


def wall_clock_steps() -> None:
    print("5. The wall clock is stepped while the machine keeps running")
    sampler = Sampler()
    sampler.ingest(snap(1000, [proc(1, 5.0)], mono=10))
    forward = sampler.ingest(snap(1006, [proc(1, 5.8)], mono=11))  # +5 s step, 1 s really passed
    assert forward is not None
    print(
        f"   forward 5 s: gap={forward.gap}, interval_s={forward.interval_s:g}, "
        f"used 0.8 CPU-s, credited {credited(forward):g}"
    )
    back = sampler.ingest(snap(1002, [proc(1, 6.6)], mono=12))  # stepped back 5 s
    assert back is not None
    print(
        f"   back 5 s: gap={back.gap}, interval_s={back.interval_s:g}, taken_at went from "
        f"{forward.taken_at:g} to {back.taken_at:g}, credited {credited(back):g}"
    )


def pid_reuse_and_first_sighting() -> None:
    print("6. Pid reuse and first sightings (expected behaviour, shown for completeness)")
    sampler = Sampler()
    sampler.ingest(snap(1000, [proc(1, 5.0)]))
    batch = sampler.ingest(
        snap(
            1001,
            [proc(1, 9.0, started=1000.5), proc(3, 7.0, started=50), proc(4, 0.3, started=998)],
        )
    )
    assert batch is not None
    for sample in batch.processes:
        print(
            f"   pid {sample.key.pid} started {sample.key.started:g}: "
            f"first_seen={sample.first_seen}, credited {sample.cpu_s:g}"
        )
    print(f"   exited: {[(key.pid, key.started) for key in batch.exited]}")


def missed_once() -> None:
    print("7. A live process that one snapshot fails to return (a read that raced or was refused)")
    sampler = Sampler()
    sampler.ingest(snap(1000, [proc(1, 0.0), proc(2, 0.0)]))
    used, got, exits, starts = 0.0, 0.0, 0, 0
    for tick in range(1, 7):
        present = [proc(1, 0.0)] + ([] if tick == 3 else [proc(2, 0.8 * tick)])
        batch = sampler.ingest(snap(1000 + tick, present))
        assert batch is not None
        used += 0.8
        got += sum(sample.cpu_s for sample in batch.processes if sample.key.pid == 2)
        exits += len(batch.exited)
        starts += sum(sample.first_seen for sample in batch.processes)
    print(
        f"   pid 2 used {used:.1f} CPU-s over 6 s and was credited {got:.1f}; "
        f"{exits} exit and {starts} start were reported, and none happened"
    )


def main() -> None:
    restricted_then_readable()
    hot_only_snapshots()
    legal_intervals_are_gaps()
    identity_flip()
    wall_clock_steps()
    pid_reuse_and_first_sighting()
    missed_once()


if __name__ == "__main__":
    main()
