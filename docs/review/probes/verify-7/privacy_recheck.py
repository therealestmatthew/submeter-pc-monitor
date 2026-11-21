"""Batch 7 re-check of the privacy leads P1-P7, P13 and P14 against the baseline code.

Run:  uv run python docs/review/probes/verify-7/privacy_recheck.py

Every secret is fake. The probe calls baseline functions with hand-made inputs, starts two
short-lived children of its own (a Python sleeping two seconds with a non-UTF-8 argument, to see
what psutil returns, and a Python that takes an InstanceLock and exits without releasing it),
and writes files only under a temporary folder that it removes. For live
processes it prints counts only, never a command line, a program name or a user name. It sends
nothing anywhere and changes no other process.
"""

from __future__ import annotations

import inspect
import os
import re
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import psutil
from pydantic import ValidationError

from submeter.attribution.rules import Attributor, Rule, RuleSet, aggregate
from submeter.core.config import Settings
from submeter.core.models import ProcessCounters, ProcessKey, ProcessSample, SampleBatch
from submeter.privacy.redact import redact_cmdline, redact_text
from submeter.store.files import FileMap, InstanceLock
from submeter.store.raw import RawFile, RawStore

TOK = "FAKEtok0123456789abcdef"
PW = "FAKEpw-7x"


def show(label: str, args: list[str], secret: str | None = None, mode: str = "scrub") -> None:
    out = " ".join(redact_cmdline(args, mode=mode))  # type: ignore[arg-type]
    verdict = "" if secret is None else ("LEAK " if secret in out else "hid  ")
    print(f"  {verdict}{label:<34} -> {out}")


def p1() -> None:
    print("P1 scrub on common credential forms (secret survives = LEAK)")
    show(
        "curl bearer header", ["curl", "-H", f"Authorization: Bearer {TOK}", "https://x.test"], TOK
    )
    show("mysql attached -p", ["mysql", "-uroot", f"-p{PW}", "db"], PW)
    show("curl -u user:pass", ["curl", "-u", f"alice:{PW}", "https://x.test"], PW)
    show("bash -c wrapper", ["bash", "-c", f"tool --api-key {TOK}"], TOK)
    show("docker --env=NAME=value", ["docker", "run", f"--env=API_TOKEN={PW}", "img"], PW)
    show("conn string", ["app", f"Server=db;User Id=sa;Password={PW};"], PW)
    show("control: --password value", ["mysql", "--password", PW], PW)
    show("control: -e NAME=value", ["docker", "run", "-e", f"API_TOKEN={TOK}", "img"], TOK)
    show("control: url user:pw@", ["git", "clone", f"https://alice:{PW}@x.test/r"], PW)
    show(
        "exe_only, same bearer case",
        ["curl", "-H", f"Authorization: Bearer {TOK}"],
        TOK,
        "exe_only",
    )


def p2() -> None:
    print("P2 one-string titles on this machine (counts only)")
    nul_unsplit = psutil_whole = total = 0
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            data = Path(f"/proc/{pid}/cmdline").read_bytes()
            via_psutil = psutil.Process(int(pid)).cmdline()
        except (OSError, psutil.Error):
            continue
        if not data:
            continue
        total += 1
        parts = [p for p in data.split(b"\0") if p]
        if len(parts) == 1 and b" " in parts[0]:
            nul_unsplit += 1
        if via_psutil and " " in via_psutil[0]:
            psutil_whole += 1
    print(f"  readable non-empty command lines: {total}")
    print(f"  NUL split gives one string with spaces (a direct /proc reader): {nul_unsplit}")
    print(f"  psutil argv[0] contains a space, so exe_only stores it whole: {psutil_whole}")
    title = ("postgres: alice appdb 10.0.0.5(5432) idle",)
    print(f"  exe_only on a one-item argv: {redact_cmdline(title, mode='exe_only')}")


def sample(pid: int, exe: str, cmdline: tuple[str, ...] | None) -> ProcessSample:
    return ProcessSample(
        key=ProcessKey(pid=pid, started=1000.0 + pid),
        parent_pid=None,
        exe=exe,
        cmdline=cmdline,
        cwd=None,
        cpu_s=0.1,
        io_read_bytes=None,
        io_write_bytes=None,
        memory_bytes=1 << 20,
        threads=1,
        first_seen=True,
        restricted=False,
    )


def batch(at: float, processes: tuple[ProcessSample, ...]) -> SampleBatch:
    return SampleBatch(
        taken_at=at,
        interval_s=1.0,
        gap=False,
        processes=processes,
        exited=(),
        logical_cores=8,
        cpu_busy_s=1.0,
        memory_available_bytes=1 << 30,
    )


def p3(tmp: Path) -> None:
    print("P3 non-UTF-8 argument")
    child = subprocess.Popen(
        [sys.executable.encode(), b"-c", b"import time; time.sleep(2)", b"caf\xe9-FAKE"]
    )
    try:
        time.sleep(0.3)
        got = psutil.Process(child.pid).cmdline()[-1]
        print(f"  psutil returns the last argument as {got!r}")
    finally:
        child.wait()
    good = sample(1, "init", ("init",))
    bad = sample(2, "tool", ("tool", got))
    for mode in ("scrub", "exe_only"):
        raw = RawFile(tmp / f"p3-{mode}.db", redaction=mode)  # type: ignore[arg-type]
        results = []
        for tick in range(3):
            try:
                raw.write(batch(2000.0 + tick, (good, bad)), [], {})
                results.append("ok")
            except UnicodeEncodeError:
                results.append("UnicodeEncodeError")
        rows = raw._db.execute("SELECT COUNT(*) FROM system_raw").fetchone()[0]
        print(f"  {mode:<8} bad item is last arg: ticks {results}; system_raw rows {rows}")
        raw.close()
    raw = RawFile(tmp / "p3-exe.db", redaction="exe_only")
    try:
        raw.write(batch(3000.0, (good, sample(3, got, ("tool",)))), [], {})
        print("  exe_only, bad character in exe: ok")
    except UnicodeEncodeError:
        print("  exe_only, bad character in exe: UnicodeEncodeError")
    raw.close()


def p4() -> None:
    print("P4 redact_patterns")
    settings = Settings.model_validate({"privacy": {"redact_patterns": ["("]}})
    print(f"  Settings accepts the pattern '(': {settings.privacy.redact_patterns}")
    try:
        redact_cmdline(["tool", "x"], extra_patterns=["("])
        print("  redact_cmdline with '(' : ok")
    except re.error as error:
        print(f"  redact_cmdline with '(' raises {type(error).__name__}: {error}")
    print(f"  RawFile parameters: {list(inspect.signature(RawFile).parameters)}")
    print(f"  RawStore parameters: {list(inspect.signature(RawStore).parameters)}")


def p5() -> None:
    print("P5 paths around the store")
    counters = ProcessCounters(
        key=ProcessKey(pid=5, started=1.0),
        cmdline=("tool", "--api-key", TOK),
        cpu_s=0.0,
        memory_bytes=0,
    )
    print(f"  repr(ProcessCounters) contains the secret: {TOK in repr(counters)}")
    try:
        ProcessCounters.model_validate(
            {"key": {"pid": 5, "started": 1.0}, "cmdline": f"tool --api-key {TOK}", "cpu_s": 0.0}
        )
    except ValidationError as error:
        print(f"  str(ValidationError) contains the secret: {TOK in str(error)}")
    line = f"launch failed: tool --api-key {TOK}"
    print(f"  redact_text on a log line keeps the secret: {TOK in redact_text(line)}")


def p6() -> None:
    print("P6 harmless arguments that scrub hides")
    show("script path, no extension", ["python", "/home/alice/work/agents/refactor2/run_worker"])
    show("--passes", ["optimizer", "--passes", "3", "model.onnx"])
    show("--tokenizer", ["trainer", "--tokenizer", "bpe"])
    show("git -C path", ["git", "-C", "/home/alice/src/checkout-0123456789", "status"])
    show("session id", ["claude", "--resume", "0f8e2c1a-4b5d-4e6f-9a0b-1c2d3e4f5a6b"])
    show("control: --max-tokens", ["tool", "--max-tokens", "4096"])


def mode_of(path: Path) -> str:
    return oct(stat.S_IMODE(path.stat().st_mode))


def p7(tmp: Path) -> None:
    print("P7 modes under umask 0022")
    old = os.umask(0o022)
    try:
        files = FileMap.discover(env={"SUBMETER_HOME": str(tmp / "home")})
        files.ensure()
        raw = RawFile(files.raw_file(__import__("datetime").date(2026, 11, 20)))
        raw.write(batch(4000.0, (sample(1, "init", ("init",)),)), [], {})
        lock = InstanceLock(files.lock_file("collector"))
        lock.acquire()
        for path in (files.data_dir, files.raw_dir, files.state_dir):
            print(f"  dir  {mode_of(path)} {path.relative_to(tmp)}")
        for path in sorted(files.raw_dir.iterdir()):
            print(f"  file {mode_of(path)} {path.relative_to(tmp)}")
        for path in (files.lock_file("collector"), lock.pid_file):
            print(f"  file {mode_of(path)} {path.relative_to(tmp)}")
        lock.release()
        raw.close()
    finally:
        os.umask(old)


def p13(tmp: Path) -> None:
    print("P13 pid file after the holder dies without release()")
    lock_path = tmp / "state" / "collector.lock"
    code = (
        "import os, sys; sys.path.insert(0, 'src');"
        "from pathlib import Path; from submeter.store.files import InstanceLock;"
        f"InstanceLock(Path({str(lock_path)!r})).acquire(); os._exit(0)"
    )
    child = subprocess.run([sys.executable, "-c", code], check=True)
    del child
    lock = InstanceLock(lock_path)
    holder = lock.holder()
    alive = holder is not None and psutil.pid_exists(holder)
    print(f"  holder() returns a pid: {holder is not None}; that pid is alive now: {alive}")
    print(f"  lock can be taken again: {lock.acquire()}")
    lock.release()


def p14() -> None:
    print("P14 workload names")
    for name in ("system", "submeter", "", "<img src=x onerror=1>", "../../x"):
        try:
            Rule(workload=name, exe=("miner",))
            print(f"  accepted: {name!r}")
        except ValidationError:
            print(f"  refused:  {name!r}")
    rules = RuleSet(rule=(Rule(workload="system", exe=("miner",)),))
    procs = (sample(10, "miner", ("miner",)), sample(11, "kworker", None))
    assignment = Attributor(rules).assign(procs)
    totals = aggregate(batch(5000.0, procs), assignment)
    print(f"  aggregate rows: {[(w.workload, w.processes) for w in totals]}")


def main() -> None:
    p1()
    p2()
    p4()
    p5()
    p6()
    p14()
    with tempfile.TemporaryDirectory() as folder:
        tmp = Path(folder)
        p3(tmp)
        p7(tmp)
        p13(tmp)


if __name__ == "__main__":
    main()
