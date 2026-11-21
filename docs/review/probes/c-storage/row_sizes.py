"""Probe: bytes per row on disk, for raw rows and for buckets, against the brief's 90 and 250.

Reads and measures only. Writes scratch databases in a temporary folder. Nothing is timed.

    .venv/bin/python docs/review/probes/c-storage/row_sizes.py

Part A writes half an hour of ticks through the baseline's RawFile (300 processes, 30 of them
busy, 8 workload rows a tick, timestamps with fractions as time.time() gives) and asks SQLite's
dbstat table how many bytes each table holds. Part B does the same for a per-core table, which
the metric catalogue needs and the raw schema lacks. Part C builds real Bucket records with
roll_up and stores them under several encodings of the two 66-bin histograms, then adds the
fields the catalogue lists and the Bucket record lacks. Each part projects the brief's totals.
"""

from __future__ import annotations

import random
import sqlite3
import struct
import tempfile
import zlib
from collections.abc import Callable, Sequence
from pathlib import Path

from _synth import DAY0, MB, pipeline, proc, snap, workload

from submeter.core.models import Bucket
from submeter.store.raw import RawFile
from submeter.store.rollup import roll_up

NAMES = ("agent:refactor", "agent:tests", "browser", "ide", "builds", "system", "restricted")
NAMES += ("unattributed",)
TICKS, PROCESSES, BUSY, PHASE = 1800, 300, 30, 0.137421
MODEL = {"hot": 5.184e6, "cold": 1.555e6, "workload": 1.382e6}  # docs/08 rows per 48 h, defaults


def per_row(path: Path) -> dict[str, tuple[int, float]]:
    """Rows and bytes per row of every table, from dbstat (whole pages, so free space counts)."""
    db = sqlite3.connect(path)
    used = dict(db.execute("SELECT name, SUM(pgsize) FROM dbstat GROUP BY name"))
    tables = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
    out = {}
    for table in tables:
        rows = db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        extra = sum(
            size for name, size in used.items() if name.startswith(f"sqlite_autoindex_{table}")
        )
        if rows:
            out[table] = (rows, (used.get(table, 0) + extra) / rows)
    db.close()
    return out


def raw_rows(folder: Path) -> None:
    rng, path = random.Random(11), folder / "2026-11-20.db"
    raw, cpu = RawFile(path), [0.0] * PROCESSES
    memory = [int(rng.uniform(20, 900)) * MB for _ in range(PROCESSES)]
    shots = []
    for tick in range(TICKS + 1):
        for pid in range(PROCESSES):
            cpu[pid] += rng.uniform(0.05, 0.6) if pid < BUSY else rng.uniform(0.0, 0.002)
            if pid < BUSY:
                memory[pid] += int(rng.uniform(-3, 3) * MB)
        shots.append(
            snap(
                DAY0 + tick + PHASE,
                [
                    proc(
                        1000 + 7 * pid,
                        cpu[pid],
                        started=DAY0 - 5000 + pid * 1.37,
                        memory_bytes=memory[pid],
                    )
                    for pid in range(PROCESSES)
                ],
            )
        )
    for batch, _, names in pipeline(shots):
        rows = [
            workload(
                batch.taken_at,
                rng.uniform(0.01, 3.0),
                name=name,
                memory=int(rng.uniform(0.3, 6) * 1024**3),
            )
            for name in NAMES
        ]
        raw.write(batch, rows, names, keyframe=round(batch.taken_at - DAY0) % 600 == 1)
    raw.close(at=DAY0 + TICKS + PHASE)
    sizes = per_row(path)
    shown = ", ".join(
        f"{table} {rows} rows at {size:.0f} B" for table, (rows, size) in sizes.items()
    )
    print(f"A. raw file after {TICKS} ticks, {path.stat().st_size / 1e6:.2f} MB: {shown}")
    process, work, system = (sizes[t][1] for t in ("process_raw", "workload_raw", "system_raw"))
    listed = (MODEL["hot"] + MODEL["cold"]) * process + MODEL["workload"] * work
    left_out = 172_800 * system + PROCESSES * 288 * process
    total_rows = sum(MODEL.values())
    print(
        f"   the brief's 8.12 M rows per 48 h at these sizes: {listed / 1e9:.2f} GB, "
        f"{listed / total_rows:.0f} B a row (brief: 0.73 GB at 90 B). Rows the brief does not "
        f"count, 172,800 system rows and 86,400 keyframe rows: {left_out / 1e6:.0f} MB more"
    )


def core_rows(folder: Path, cores: int = 16) -> None:
    rng, path = random.Random(12), folder / "cores.db"
    db = sqlite3.connect(path)
    db.execute(
        "CREATE TABLE core_raw (ts REAL NOT NULL, core INTEGER NOT NULL, busy_s REAL NOT NULL,"
        " mhz INTEGER NOT NULL, PRIMARY KEY (ts, core)) WITHOUT ROWID"
    )
    db.execute("CREATE TABLE core_blob (ts REAL PRIMARY KEY, cores BLOB NOT NULL) WITHOUT ROWID")
    with db:
        for tick in range(TICKS):
            at = DAY0 + tick + PHASE
            values = [(rng.random(), rng.randint(800, 4800)) for _ in range(cores)]
            db.executemany(
                "INSERT INTO core_raw VALUES (?, ?, ?, ?)",
                [(at, core, busy, mhz) for core, (busy, mhz) in enumerate(values)],
            )
            packed = b"".join(struct.pack("<fH", busy, mhz) for busy, mhz in values)
            db.execute("INSERT INTO core_blob VALUES (?, ?)", (at, packed))
    db.close()
    sizes = per_row(path)
    as_rows = cores * 172_800 * sizes["core_raw"][1]
    as_blob = 172_800 * sizes["core_blob"][1]
    print(
        f"B. load and frequency per core, {cores} cores, which the raw schema has no table for: "
        f"one row per core is {sizes['core_raw'][1]:.0f} B a row, {cores * 172_800 / 1e6:.2f} M "
        f"rows and {as_rows / 1e6:.0f} MB per 48 h; one packed row per tick is "
        f"{sizes['core_blob'][1]:.0f} B, {as_blob / 1e6:.0f} MB per 48 h"
    )


def buckets() -> list[Bucket]:
    rng, out = random.Random(13), []
    for index, name in enumerate((*NAMES, "machine")):
        base_cores, base_memory = 0.05 * (index + 1) ** 2, (0.2 + 0.7 * index) * 1024**3
        samples = [
            workload(
                DAY0 + second + 1,
                base_cores * rng.lognormvariate(0.0, 0.35),
                name=name,
                memory=int(base_memory * rng.gauss(1.0, 0.01)),
            )
            for second in range(4 * 3600)
        ]
        out += roll_up(samples, width_s=60, logical_cores=16)
    return out


def sparse(bins: Sequence[float]) -> bytes:
    return b"".join(
        struct.pack("<Bf", index, weight) for index, weight in enumerate(bins) if weight
    )


def dense(code: str) -> Callable[[Sequence[float]], bytes]:
    return lambda bins: struct.pack(f"<{len(bins)}{code}", *bins)


def stored_size(
    path: Path, rows: Sequence[Bucket], pack: Callable, extra: int, layout: str
) -> float:
    """Bytes per bucket in a scratch table keyed as the raw tables are, or with a rowid."""
    db = sqlite3.connect(path)
    scalar = [field for field in Bucket.model_fields if not field.endswith("_hist")]
    more = [f"extra{index}" for index in range(extra)]
    columns = [*scalar, *more, "cores_hist", "memory_hist"]
    db.execute(
        f"CREATE TABLE rollup_1m ({', '.join(columns)}, PRIMARY KEY (series, start)){layout}"
    )
    rng = random.Random(14)
    with db:
        for bucket in rows:
            values = [getattr(bucket, field) for field in scalar]
            values += [
                rng.uniform(0, 1e9) if index % 2 else rng.randint(0, 10**6)
                for index in range(extra)
            ]
            values += [pack(bucket.cores_hist), pack(bucket.memory_hist)]
            db.execute(f"INSERT INTO rollup_1m VALUES ({', '.join('?' * len(columns))})", values)
    db.close()
    return per_row(path)["rollup_1m"][1]


def bucket_rows(folder: Path) -> None:
    rows = buckets()
    filled = sum(
        sum(1 for w in b.cores_hist if w) + sum(1 for w in b.memory_hist if w) for b in rows
    )
    as_json = sum(len(b.model_dump_json()) for b in rows) / len(rows)
    print(
        f"C. {len(rows)} minute buckets built by roll_up; {filled / len(rows):.1f} of 132 "
        f"histogram bins are filled on average; one bucket as JSON is {as_json:.0f} B"
    )
    keyed, plain = " WITHOUT ROWID", ""
    encodings = (
        ("dense 8-byte floats, WITHOUT ROWID as raw.py", dense("d"), 0, keyed),
        ("dense 8-byte floats, rowid table", dense("d"), 0, plain),
        ("dense 4-byte floats, WITHOUT ROWID", dense("f"), 0, keyed),
        (
            "dense 8-byte floats through zlib",
            lambda bins: zlib.compress(dense("d")(bins)),
            0,
            keyed,
        ),
        ("filled bins only", sparse, 0, keyed),
        ("filled bins only, plus 18 catalogue fields", sparse, 18, keyed),
    )
    for number, (label, pack, extra, layout) in enumerate(encodings):
        size = stored_size(folder / f"buckets{number}.db", rows, pack, extra, layout)
        day = 1440 * size
        print(
            f"   {label:<45} {size:5.0f} B a bucket; 9 series: {9 * day * 30 / 1e9:.2f} to "
            f"{9 * day * 37 / 1e9:.2f} GB for 30 to 37 days; 26 series: {26 * day * 37 / 1e9:.2f} "
            f"GB; 200 series: {200 * day * 37 / 1e9:.2f} GB"
        )
    print(
        "   brief: 250 B a bucket, 9 series, 0.1 GB. The machine's bucket also needs min, max "
        f"and mean of load and frequency per core in the minute tier: 16 cores x 6 values x 4 B "
        f"= {16 * 6 * 4} B more on that one series"
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as name:
        folder = Path(name)
        raw_rows(folder)
        core_rows(folder)
        bucket_rows(folder)


if __name__ == "__main__":
    main()
