"""P3: what a lone surrogate in a process record does to RawFile.write, without a child process.

Run:  uv run python docs/review/probes/verify-7/p3_surrogate.py

On Linux psutil decodes command lines and paths with surrogateescape, so a byte that is not
UTF-8 arrives as a lone surrogate such as '\\udce9'. This probe builds a two-process batch by
hand, one process carrying such a character in one field, and writes it three times through
RawFile in a temporary folder, in both redaction modes and for three fields (an argument,
argv[0] and exe). It prints whether each write succeeded and how many system rows reached the
file. Also writes one event whose detail carries the character. Nothing leaves the folder.
"""

from __future__ import annotations

import contextlib
import tempfile
from pathlib import Path
from typing import get_args

from submeter.core.models import ProcessKey, ProcessSample, SampleBatch
from submeter.privacy.redact import Mode
from submeter.store.raw import RawFile

BAD = "caf\udce9"


def sample(pid: int, exe: str, cmdline: tuple[str, ...]) -> ProcessSample:
    return ProcessSample(
        key=ProcessKey(pid=pid, started=10.0),
        parent_pid=None,
        exe=exe,
        cmdline=cmdline,
        cwd=None,
        cpu_s=0.5,
        io_read_bytes=None,
        io_write_bytes=None,
        memory_bytes=1024,
        threads=1,
        first_seen=True,
        restricted=False,
    )


def batch(at: float, odd: ProcessSample) -> SampleBatch:
    good = sample(1, "python", ("python", "x.py"))
    return SampleBatch(
        taken_at=at,
        interval_s=1.0,
        gap=False,
        processes=(good, odd),
        exited=(),
        logical_cores=4,
        cpu_busy_s=1.0,
        memory_available_bytes=1,
    )


def main() -> None:
    cases = {
        "last argument": sample(2, "tool", ("tool", BAD)),
        "argv[0]": sample(2, "tool", (BAD, "x")),
        "exe": sample(2, f"/opt/{BAD}/tool", ("tool", "x")),
    }
    with tempfile.TemporaryDirectory() as folder:
        for mode in get_args(Mode):
            for what, odd in cases.items():
                raw = RawFile(Path(folder) / f"{mode}-{what[:4]}.db", redaction=mode)
                outcomes = []
                for tick in range(3):
                    try:
                        raw.write(batch(100.0 + tick, odd), [], {})
                        outcomes.append("ok")
                    except UnicodeEncodeError:
                        outcomes.append("UnicodeEncodeError")
                rows = raw._db.execute("SELECT COUNT(*) FROM system_raw").fetchone()[0]
                print(f"{mode:<9}{what:<14} ticks: {', '.join(outcomes)}; system rows: {rows}")
                raw.close()
        # after the odd process exits, does the good one's identity row exist?
        raw = RawFile(Path(folder) / "after.db")
        odd = cases["last argument"]
        with contextlib.suppress(UnicodeEncodeError):
            raw.write(batch(100.0, odd), [], {})
        alone = batch(101.0, odd).model_copy(update={"processes": batch(101.0, odd).processes[:1]})
        raw.write(alone, [], {})
        known = raw._db.execute("SELECT COUNT(*) FROM process WHERE pid = 1").fetchone()[0]
        rows = raw._db.execute("SELECT COUNT(*) FROM process_raw WHERE pid = 1").fetchone()[0]
        print(f"after one failed tick, good pid 1: process rows {known}, process_raw rows {rows}")
        raw.close()
        raw = RawFile(Path(folder) / "event.db")
        try:
            raw.record_event(1.0, "provider", f"fell back on {BAD}")
            print("record_event with the character: ok")
        except UnicodeEncodeError:
            print("record_event with the character: UnicodeEncodeError")
        raw.close()


if __name__ == "__main__":
    main()
