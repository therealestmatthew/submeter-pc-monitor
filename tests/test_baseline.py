"""Tests for the baseline modules. Run with: uv run pytest"""

from __future__ import annotations

import json
import os
import random
import sys
import types
from datetime import date
from pathlib import Path

import pytest
from typer.testing import CliRunner

from submeter.analysis.growth import (
    GrowthResult,
    check_growth,
    daily_minimums,
    theil_sen,
    usual_range,
)
from submeter.attribution.rules import (
    RESTRICTED,
    UNATTRIBUTED,
    Attributor,
    Rule,
    RuleSet,
    aggregate,
)
from submeter.cli import app
from submeter.collector.sampler import Sampler, hot_keys
from submeter.core import histogram
from submeter.core.config import ConfigError, load_settings
from submeter.core.models import (
    ProcessCounters,
    ProcessKey,
    Snapshot,
    SystemCounters,
    Tier,
    WorkloadSample,
)
from submeter.core.units import (
    format_duration,
    format_size,
    parse_duration,
    parse_rate,
    parse_size,
)
from submeter.privacy.redact import REDACTED, redact_cmdline
from submeter.store.files import FileMap, InstanceLock
from submeter.store.query import TierChoice, choose_tier
from submeter.store.raw import RawFile, RawStore
from submeter.store.rollup import cores_percentile, merge, roll_up, well_covered

MB = 1024**2
DAY0 = 1_795_132_800.0  # 2026-11-20 00:00:00 UTC


def proc(
    pid: int, cpu: float, *, started: float = 100.0, parent: int | None = None, **extra: object
) -> ProcessCounters:
    fields: dict[str, object] = {"exe": "tool", "cmdline": ("tool",), "memory_bytes": 50 * MB}
    fields.update(extra)
    return ProcessCounters(
        key=ProcessKey(pid=pid, started=started), parent_pid=parent, cpu_s=cpu, **fields
    )


def snap(
    at: float, processes: list[ProcessCounters], busy: float = 0.0, mono: float | None = None
) -> Snapshot:
    system = SystemCounters(
        logical_cores=4,
        cpu_busy_s=(busy, 0.0, 0.0, 0.0),
        memory_total_bytes=16 * 1024**3,
        memory_available_bytes=8 * 1024**3,
    )
    return Snapshot(
        taken_at=at,
        monotonic=at if mono is None else mono,
        processes=tuple(processes),
        system=system,
    )


def workload(
    at: float, cpu: float, memory: int = 100 * MB, name: str = "agents", interval: float = 1.0
) -> WorkloadSample:
    return WorkloadSample(
        taken_at=at,
        interval_s=interval,
        workload=name,
        source="polled",
        cpu_s=cpu,
        memory_bytes=memory,
        io_read_bytes=0,
        io_write_bytes=0,
        processes=1,
        started=0,
    )


# ---- units -----------------------------------------------------------------------------------
def test_units_round_trip() -> None:
    assert parse_duration("250ms") == 0.25
    assert parse_duration("48h") == 172800
    assert parse_size("2GB") == 2 * 1024**3
    assert parse_rate("50MB/h") == pytest.approx(50 * MB / 3600)
    assert format_duration(172800) == "2d"
    assert format_size(1.5 * 1024**3) == "1.5 GB"
    with pytest.raises(ValueError, match="not a duration"):
        parse_duration("soon")


# ---- config ----------------------------------------------------------------------------------
def test_config_layers_and_sources(tmp_path: Path) -> None:
    file = tmp_path / "submeter.toml"
    file.write_text(
        '[sampling]\nactive_interval = "2s"\n[storage]\ndisk_budget = "1GB"\n'
        '[[alerts.rules]]\nname = "busy"\nmetric = "cpu_cores"\nabove = 12\nfor = "5m"\n'
        '[profile.laptop]\nsampling.idle_interval = "10s"\n'
    )
    loaded = load_settings(
        file,
        profile="laptop",
        env={"SUBMETER_SAMPLING__COLD_INTERVAL": "30s", "SUBMETER_HOME": "/x"},
    )
    sampling = loaded.settings.sampling
    assert (sampling.active_interval, sampling.idle_interval, sampling.cold_interval) == (
        2.0,
        10.0,
        30.0,
    )
    assert loaded.settings.alerts.rules[0].duration == 300
    assert loaded.sources["sampling.active_interval"] == "file"
    assert loaded.sources["sampling.idle_interval"] == "profile:laptop"
    assert loaded.sources["sampling.cold_interval"] == "env"
    assert dict((key, source) for key, _, source in loaded.effective())["api.port"] == "default"


def test_config_refuses_bad_values(tmp_path: Path) -> None:
    file = tmp_path / "bad.toml"
    file.write_text('[sampling]\nactive_interval = "20s"\ncolour = "blue"\n')
    with pytest.raises(ConfigError) as caught:
        load_settings(file)
    text = " | ".join(caught.value.problems)
    assert "sampling.active_interval: 20s is outside the allowed range, 250ms to 10s" in text
    assert "sampling.colour" in text
    with pytest.raises(ConfigError) as caught:
        load_settings(env={}, overrides={"sampling": {"gpu_interval": "45s"}})
    assert "outside the allowed range, 1s to 30s" in caught.value.problems[0]


# ---- histogram -------------------------------------------------------------------------------
def test_histogram_merges_exactly_and_bounds_error() -> None:
    rng = random.Random(1)
    values = [rng.lognormvariate(0.5, 0.8) for _ in range(4000)]
    first, second, both = (histogram.empty(histogram.CORES) for _ in range(3))
    for index, value in enumerate(values):
        histogram.add(first if index % 2 else second, histogram.CORES, value)
        histogram.add(both, histogram.CORES, value)
    assert histogram.merge(first, second) == tuple(both)
    exact = sorted(values)[int(0.95 * len(values))]
    estimate = histogram.percentile(both, histogram.CORES, 95)
    assert estimate is not None and exact / 1.18 < estimate < exact * 1.18
    assert histogram.percentile(histogram.empty(histogram.CORES), histogram.CORES, 50) is None


# ---- redaction -------------------------------------------------------------------------------
def test_redaction_hides_secrets_and_keeps_the_rest() -> None:
    args = [
        "claude",
        "--api-key",
        "sk-abcdefghijklmnopqrstu",
        "--max-tokens",
        "4096",
        "TOKEN=abc",
        "postgres://u:pw@host/db",
        "notes.md",
    ]
    cleaned = redact_cmdline(args)
    assert cleaned == (
        "claude",
        "--api-key",
        REDACTED,
        "--max-tokens",
        "4096",
        f"TOKEN={REDACTED}",
        f"postgres://u:{REDACTED}@host/db",
        "notes.md",
    )
    assert redact_cmdline(args, mode="exe_only") == ("claude",)
    assert redact_cmdline(["x", "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6"]) == ("x", REDACTED)


# ---- sampler ---------------------------------------------------------------------------------
def test_sampler_deltas_new_processes_and_pid_reuse() -> None:
    sampler = Sampler()
    assert sampler.ingest(snap(1000, [proc(1, 5.0), proc(2, 1.0)], busy=10)) is None
    batch = sampler.ingest(
        snap(
            1001,
            [
                proc(1, 5.4),
                proc(2, 9.0, started=1000.5),
                proc(3, 0.3, started=1000.2),
                proc(4, 7.0, started=50),
            ],
            busy=11.5,
        )
    )
    assert batch is not None and not batch.gap and batch.interval_s == 1.0
    by_pid = {sample.key.pid: sample for sample in batch.processes}
    assert by_pid[1].cpu_s == pytest.approx(0.4)
    assert (
        by_pid[2].cpu_s == 9.0 and by_pid[2].first_seen
    )  # same pid, new start time: a new process
    assert by_pid[3].cpu_s == 0.3  # born in this interval: all of its CPU belongs here
    assert by_pid[4].cpu_s == 0.0  # older than the last snapshot: no baseline yet
    assert batch.exited == (ProcessKey(pid=2, started=100.0),)
    assert batch.cpu_busy_s == pytest.approx(1.5)
    assert ProcessKey(pid=1, started=100.0) in hot_keys(batch, cpu_threshold=0.005)


def test_sampler_records_a_gap_instead_of_a_spike() -> None:
    sampler = Sampler()
    sampler.ingest(snap(1000, [proc(1, 5.0)], mono=10))
    batch = sampler.ingest(
        snap(4600, [proc(1, 5.2)], mono=11)
    )  # an hour passed on the wall clock only
    assert batch is not None and batch.gap and batch.interval_s == 3600
    assert batch.processes[0].cpu_s == 0.0 and batch.cpu_busy_s == 0.0


# ---- attribution -----------------------------------------------------------------------------
def test_attribution_order_inheritance_and_reconciliation() -> None:
    rules = RuleSet(
        rule=(
            Rule(workload="tools", exe=("tool",), priority=1),
            Rule(workload="browser", exe=("chrome.exe",), priority=5, include_children=True),
        )
    )
    sampler = Sampler()
    before = [
        proc(10, 0, exe=r"C:\Apps\chrome.exe"),
        proc(11, 0, parent=10, started=101, exe="helper"),
        proc(12, 0, parent=10, started=99, exe="older"),
        proc(13, 0, exe="mystery", restricted=True, cmdline=None),
        proc(14, 0),
        proc(15, 0, exe="agent"),
    ]
    sampler.ingest(snap(1000, before))
    after = [p.model_copy(update={"cpu_s": 0.1 * (i + 1)}) for i, p in enumerate(before)]
    batch = sampler.ingest(snap(1001, after))
    assert batch is not None
    tagged = {ProcessKey(pid=15, started=100.0): "agent:refactor"}
    assignment = Attributor(rules, inherit_from_parent=False).assign(batch.processes, tagged)
    names = {key.pid: value.workload for key, value in assignment.items()}
    assert names == {
        10: "browser",
        11: "browser",
        12: UNATTRIBUTED,
        13: RESTRICTED,
        14: "tools",
        15: "agent:refactor",
    }
    totals = aggregate(batch, assignment, kernel_workloads={"agent:refactor"})
    assert sum(total.cpu_s for total in totals) == pytest.approx(
        sum(sample.cpu_s for sample in batch.processes)
    )
    assert {total.workload: total.source.value for total in totals}["agent:refactor"] == "kernel"


def test_rules_file_loads_and_rejects_empty_rules(tmp_path: Path) -> None:
    file = tmp_path / "rules.toml"
    file.write_text(
        '[[rule]]\nworkload = "ide"\npriority = 50\nexe = ["Code.exe"]\n'
        "[[rule]]\nworkload = \"builds\"\ncwd = 'C:\\src\\**'\n"
    )
    assert [rule.workload for rule in RuleSet.load(file).ordered()] == ["ide", "builds"]
    assert (
        RuleSet.load(file).needs_cwd
        and not RuleSet(rule=(Rule(workload="a", exe=("a",)),)).needs_cwd
    )
    with pytest.raises(ValueError, match="at least one of"):
        Rule(workload="nothing")


def test_a_rule_can_match_on_the_parent_program() -> None:
    rules = RuleSet(rule=(Rule(workload="from-shell", parent=("Explorer.EXE",)),))
    started = [
        proc(20, 0, exe=r"C:\Windows\explorer.exe"),
        proc(21, 0, parent=20, started=101, exe="notepad.exe"),
        proc(22, 0, parent=20, started=99, exe="older.exe"),  # pid 20 was reused: not its parent
        proc(23, 0, exe="orphan.exe"),
    ]
    sampler = Sampler()
    sampler.ingest(snap(1000, started))
    batch = sampler.ingest(snap(1001, started))
    assert batch is not None
    assignment = Attributor(rules, inherit_from_parent=False).assign(batch.processes)
    assert {key.pid: value.workload for key, value in assignment.items()} == {
        20: UNATTRIBUTED,
        21: "from-shell",
        22: UNATTRIBUTED,
        23: UNATTRIBUTED,
    }


# ---- files -----------------------------------------------------------------------------------
def test_file_map_names_expiry_and_lock(tmp_path: Path) -> None:
    windows = FileMap.discover({"APPDATA": "C:/R", "LOCALAPPDATA": "C:/L"}, "win32")
    assert windows.settings_file == Path("C:/R/Submeter/submeter.toml")
    files = FileMap.discover({"SUBMETER_HOME": str(tmp_path)})
    files.ensure()
    day = date(2026, 11, 20)
    assert (
        files.raw_file(day).name == "2026-11-20.db" and files.minute_file(day).name == "2026-W47.db"
    )
    for name in ("2026-11-17.db", "2026-11-18.db", "2026-11-20.db"):
        (files.raw_dir / name).write_bytes(b"x")
    now = DAY0 + 9 * 3600  # 09:00 UTC on the 20th
    expired = files.expired_raw(now, 48 * 3600, rolled_up_until=now)
    assert [path.name for path in expired] == ["2026-11-17.db"]
    assert files.disk_use()["raw"] == 3
    lock = InstanceLock(files.lock_file("collector"))
    with lock:
        assert not InstanceLock(files.lock_file("collector")).acquire()
        assert lock.holder() == os.getpid() and files.lock_file("collector").read_bytes() == b""
    assert lock.holder() is None  # the pid file goes when the lock is released
    again = InstanceLock(files.lock_file("collector"))
    assert again.acquire()
    again.release()


def test_the_windows_lock_makes_the_calls_windows_expects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stand-in for msvcrt: this checks the calls, not how Windows answers them."""
    calls: list[tuple[int, int, int]] = []
    held: set[int] = set()

    def locking(fd: int, mode: int, nbytes: int) -> None:
        inode = os.fstat(fd).st_ino
        calls.append((mode, nbytes, os.lseek(fd, 0, os.SEEK_CUR)))
        if mode == 2:  # LK_NBLCK: fail at once if any other handle holds the byte
            if inode in held:
                raise PermissionError(13, "Permission denied")
            held.add(inode)
        else:
            held.discard(inode)

    fake = types.ModuleType("msvcrt")
    fake.LK_NBLCK, fake.LK_UNLCK, fake.locking = 2, 0, locking  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "msvcrt", fake)
    monkeypatch.setattr(sys, "platform", "win32")
    path = tmp_path / "collector.lock"
    first, second = InstanceLock(path), InstanceLock(path)
    assert first.acquire() and not second.acquire()
    assert first.holder() == os.getpid() and path.read_bytes() == b""
    first.release()
    assert second.acquire()
    second.release()
    # every call is on one byte at offset 0: try, try and fail, probe and fail, unlock, try, unlock
    assert calls == [(2, 1, 0), (2, 1, 0), (2, 1, 0), (0, 1, 0), (2, 1, 0), (0, 1, 0)]


# ---- raw store -------------------------------------------------------------------------------
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
    assert len(reopened.workload_samples(1000, 1120)) == 120
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


# ---- rollup ----------------------------------------------------------------------------------
def test_rollups_reproduce_totals_and_percentiles() -> None:
    rng = random.Random(5)
    samples = [
        workload(DAY0 + second + 1, rng.random() * 4, memory=int((200 + rng.random() * 50) * MB))
        for second in range(3600)
    ]
    minutes = roll_up(samples, width_s=60, logical_cores=16)
    hour = merge(minutes, start=DAY0, width_s=3600)
    direct = roll_up(samples, width_s=3600, logical_cores=16)[0]
    assert len(minutes) == 60 and minutes[0].covered_s == 60 and well_covered(hour)
    assert hour.cpu_s == pytest.approx(sum(sample.cpu_s for sample in samples))
    assert hour.cpu_s == pytest.approx(direct.cpu_s) and hour.memory_mean == pytest.approx(
        direct.memory_mean
    )
    assert (hour.memory_min, hour.memory_max) == (direct.memory_min, direct.memory_max)
    assert cores_percentile(hour, 95) == pytest.approx(cores_percentile(direct, 95))
    with pytest.raises(ValueError, match="different series"):
        merge(
            [minutes[0], minutes[1].model_copy(update={"series": "other"})],
            start=DAY0,
            width_s=3600,
        )


# ---- query -----------------------------------------------------------------------------------
def tier(start: float) -> TierChoice:
    return choose_tier(
        start=start,
        end=DAY0,
        now=DAY0,
        raw_covered_from=DAY0 - 48 * 3600.0,
        minute_retention_s=30 * 86400.0,
    )


def test_tier_choice_follows_retention_and_point_budget() -> None:
    assert tier(DAY0 - 300).tier is Tier.RAW
    assert tier(DAY0 - 6 * 3600).tier is Tier.MINUTE
    assert tier(DAY0 - 7 * 86400).tier is Tier.HOUR
    year = tier(DAY0 - 365 * 86400)
    assert year.tier is Tier.HOUR and year.step_s == 5 * 3600 and "merged" in year.reason


# ---- growth ----------------------------------------------------------------------------------
def grows(xs: list[float], ys: list[float]) -> GrowthResult:
    return check_growth(xs, ys, min_duration_s=2 * 3600.0, min_slope_per_s=50 * MB / 3600)


def test_growth_flags_a_leak_and_clears_a_warm_up() -> None:
    rng = random.Random(9)
    minutes = [60.0 * i for i in range(300)]  # five hours of minute buckets
    noise = [rng.uniform(-3e7, 3e7) for _ in minutes]
    leak = [3.1e9 + 105_000 * t + n for t, n in zip(minutes, noise, strict=True)]  # ~380 MB/h
    warm = [
        3.6e9 + 9e8 * (1 - 2.718 ** (-t / 1200)) + n for t, n in zip(minutes, noise, strict=True)
    ]
    late = [3.1e9 + 100_000 * min(t, 12_600.0) + n for t, n in zip(minutes, noise, strict=True)]
    flat = [3.4e9 + n for n in noise]
    assert grows(minutes, leak).flagged
    assert not grows(minutes, warm).flagged  # a cache filling in the first half hour
    assert grows(minutes, late).reason == "growth has levelled off"  # climbed, then stopped
    assert grows(minutes, flat).reason == "growth is below the threshold"
    assert grows(minutes[:60], leak[:60]).reason == "not enough data yet"
    spiked = [2.0 * x if x != 10 else 1000.0 for x in range(20)]
    assert theil_sen([float(x) for x in range(20)], spiked) == pytest.approx(
        2.0
    )  # one spike changes nothing


def test_usual_range_and_daily_minimums() -> None:
    low, middle, high = usual_range([3.4, 3.35, 3.45, 3.4, 3.38, 3.42, 3.41]) or (0, 0, 0)
    assert low < 3.35 and high > 3.45 and middle == 3.4 and not low < 4.25 < high
    assert usual_range([1.0, 2.0]) is None
    assert daily_minimums([DAY0 + 10, DAY0 + 20, DAY0 + 86400 + 5], [5.0, 3.0, 7.0]) == [
        (DAY0, 3.0),
        (DAY0 + 86400, 7.0),
    ]


# ---- command line ----------------------------------------------------------------------------
def test_cli_runs_end_to_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUBMETER_HOME", str(tmp_path))
    runner = CliRunner()
    doctor = runner.invoke(app, ["doctor", "--json"])
    assert (
        doctor.exit_code == 0
        and json.loads(doctor.stdout)["providers"][0]["name"] == "process.psutil"
    )
    watched = runner.invoke(app, ["top", "--seconds", "0.3", "--json"])
    assert watched.exit_code == 0 and {"workload", "cpu_s", "source"} <= set(
        json.loads(watched.stdout)[0]
    )
    bad = tmp_path / "bad.toml"
    bad.write_text("[api]\nport = 80\n")
    assert runner.invoke(app, ["config", "check", str(bad)]).exit_code == 2
    assert "api.port" in runner.invoke(app, ["config", "show"]).stdout
    shown = runner.invoke(app, ["config", "show", "--effective"])
    assert shown.exit_code == 0 and "api.port" in shown.stdout
    assert json.loads(runner.invoke(app, ["store", "status", "--json"]).stdout)["total"] == 0
