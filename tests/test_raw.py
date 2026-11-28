"""Tests for the raw store: the collector's day files, their rows and how they are read."""

from __future__ import annotations

import random
from contextlib import closing
from datetime import date
from pathlib import Path

import pytest
from builders import DAY0, HOUR, batch, proc, process, snap, workload, workload_store

from submeter.collector.sampler import Sampler
from submeter.store.files import FileMap
from submeter.store.raw import RawFile, RawStore, open_read_only


def test_raw_file_keeps_sums_exact_and_secrets_out(tmp_path: Path) -> None:
    sampler, raw = Sampler(), RawFile(tmp_path / "day.db")
    secret = "sk-abcdefghijklmnopqrstuvwx"
    total, cpu = 0.0, [0.0, 0.0, 0.0]
    sampler.ingest(
        snap(1000, [proc(i, 0.0, cmdline=("tool", "--api-key", secret)) for i in range(3)])
    )
    rng = random.Random(3)
    for tick in range(1, 121):
        cpu = [value + (rng.random() * 0.002 if index else 0.3) for index, value in enumerate(cpu)]
        batch = sampler.ingest(
            snap(
                1000 + tick,
                [proc(i, cpu[i], cmdline=("tool", "--api-key", secret)) for i in range(3)],
            )
        )
        assert batch is not None
        total += sum(sample.cpu_s for sample in batch.processes)
        raw.write(
            batch,
            [workload(batch.taken_at, sum(s.cpu_s for s in batch.processes))],
            {},
            keyframe=tick == 1,
        )
    rows = raw.count("process_raw")
    raw.close(at=1120)
    reopened = RawFile(tmp_path / "day.db")
    assert reopened.process_cpu_total() == pytest.approx(total)  # suppressed rows lost nothing
    assert 120 < rows < 3 * 120  # the busy process is written every tick, the idle two are not
    assert reopened.count("command") == 1 and reopened.count("process") == 3
    assert len(RawFile.workload_samples(tmp_path / "day.db", 1000, 1121)) == 120
    reopened.close()
    assert secret.encode() not in (tmp_path / "day.db").read_bytes()


def test_raw_store_rolls_over_at_utc_midnight_and_marks_gaps(tmp_path: Path) -> None:
    files = FileMap.discover({"SUBMETER_HOME": str(tmp_path)})
    store, sampler = RawStore(files, keyframe_interval_s=600), Sampler()
    sampler.ingest(snap(DAY0 - 2, [proc(1, 0.0)]))
    for at in (DAY0 - 1, DAY0 + 1, DAY0 + 5000):  # the last one is a gap of over an hour
        batch = sampler.ingest(snap(at, [proc(1, at - DAY0 + 10)]))
        assert batch is not None
        store.write(batch, [workload(at, 1.0)], {})
    store.close()
    assert sorted(path.name for path in files.raw_dir.glob("*.db")) == [
        "2026-11-19.db",
        "2026-11-20.db",
    ]
    today = RawFile(files.raw_file(date(2026, 11, 20)))
    assert today.count("gap") == 1 and today.count("process_raw") == 2
    today.close()


def test_reading_a_raw_file_never_writes_to_it(tmp_path: Path) -> None:
    """R91: the reader opens the file read-only, so the collector stays its only writer."""
    with pytest.raises(FileNotFoundError):
        RawFile.workload_samples(tmp_path / "2026-11-21.db", DAY0, DAY0 + HOUR)
    assert list(tmp_path.iterdir()) == []
    writer = RawFile(tmp_path / "day.db")
    for k in range(1, 11):
        writer.write(batch(DAY0 + k, 1.0), [workload_store(DAY0 + k, 0.5, 1.0)], {})
    wal = tmp_path / "day.db-wal"
    size = wal.stat().st_size
    assert len(RawFile.workload_samples(writer.path, DAY0, DAY0 + HOUR)) == 10
    assert wal.stat().st_size == size > 0
    writer.close()


def test_undecodable_text_and_a_failed_write_do_not_stop_later_writes(tmp_path: Path) -> None:
    """R54: undecodable text no longer fails every write, and a failed write is undone whole."""
    raw = RawFile(tmp_path / "day.db", redaction="scrub")
    odd = process(1, 0.0, exe="t\udcffl", cmdline=("tool", "caf\udce9"))
    for k in range(1, 4):
        raw.write(batch(DAY0 + k, 1.0, processes=(odd,)), [workload_store(DAY0 + k, 0.0, 1.0)], {})
    huge = process(3, 0.5, memory_bytes=2**63)  # SQLite cannot store it, so the write fails
    with pytest.raises(OverflowError):
        raw.write(batch(DAY0 + 4, 1.0, processes=(process(2, 0.5), huge)), [], {})
    raw.write(batch(DAY0 + 5, 1.0, processes=(process(2, 0.5),)), [], {})
    assert (raw.count("workload_raw"), raw.count("process"), raw.process_cpu_total()) == (3, 2, 0.5)
    raw.close()
    assert b"tool caf\\udce9" in raw.path.read_bytes() and b"t\\udcffl" in raw.path.read_bytes()


def test_a_quiet_process_gets_a_row_each_minute_and_none_crosses_an_hour(tmp_path: Path) -> None:
    """R90: CPU held for a quiet process is written within 60 s and at the last tick of an hour."""
    raw, hour = RawFile(tmp_path / "day.db"), DAY0 + HOUR
    for at in range(int(hour) - 99, int(hour) + 101):  # 0.1% of a core at 1 s ticks
        raw.write(batch(float(at), 1.0, processes=(process(1, 0.001),)), [], {})
    with closing(open_read_only(raw.path)) as db:
        rows = db.execute("SELECT ts - ?, cpu_s FROM process_raw ORDER BY ts", (hour,)).fetchall()
    raw.close()
    held = [(-99, 0.001), (-39, 0.06), (-1, 0.038), (59, 0.06)]  # first seen, 60 s, hour, 60 s
    assert [(ts, round(cpu, 9)) for ts, cpu in rows] == held
