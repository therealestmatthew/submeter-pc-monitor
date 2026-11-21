"""P2: does the baseline provider ever hand redact_cmdline a one-string argv on Linux?

Run:  uv run python docs/review/probes/verify-7/p2_split.py

For every live process it reads /proc/PID/cmdline, splits it on NUL only (as `man proc`
describes, and as a direct /proc reader would), and separately asks psutil for cmdline(),
which is what the baseline's PsutilProvider passes on. It counts the processes whose NUL split
is one string with spaces, and, for those, whether exe_only mode would store the whole title
under each reader. It prints counts only, never a command line or a program name.
"""

from __future__ import annotations

import os
from pathlib import Path

import psutil

from submeter.privacy.redact import redact_cmdline


def main() -> None:
    unsplit = psutil_split = whole_nul = whole_psutil = padded = 0
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            data = Path(f"/proc/{pid}/cmdline").read_bytes()
            from_psutil = psutil.Process(int(pid)).cmdline()
        except (OSError, psutil.Error):
            continue
        parts = [p.decode(errors="replace") for p in data.split(b"\0") if p]
        if len(parts) != 1 or " " not in parts[0]:
            continue
        unsplit += 1
        psutil_split += len(from_psutil) > 1
        whole_nul += " ".join(redact_cmdline(parts, mode="exe_only")) == parts[0]
        whole = " ".join(redact_cmdline(from_psutil, mode="exe_only")) == parts[0]
        whole_psutil += whole
        padded += whole and all(item == "" for item in from_psutil[1:])
    print(f"processes whose NUL split is one string with spaces: {unsplit}")
    print(f"  of those, psutil.cmdline() returns more than one item: {psutil_split}")
    print(f"  psutil item 0 is the whole title and the rest are empty (NUL padding): {padded}")
    print(f"  exe_only stores the whole title, NUL-only reader: {whole_nul}")
    print(f"  exe_only stores the whole title, psutil (baseline provider): {whole_psutil}")
    title = ("postgres: alice appdb 10.0.0.5(5432) idle",)
    print(f"exe_only on a hand-made one-item argv: {redact_cmdline(title, mode='exe_only')}")


if __name__ == "__main__":
    main()
