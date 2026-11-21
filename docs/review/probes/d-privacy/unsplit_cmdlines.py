"""Count live processes whose kernel command line is one string, not a NUL-separated list.

Run:  uv run python docs/review/probes/d-privacy/unsplit_cmdlines.py

Programs that rewrite their title (Chrome, Firefox, PostgreSQL, nginx) leave /proc/PID/cmdline
with spaces where the NULs should be. psutil repairs that. A direct /proc reader that splits on
NUL, as `man proc` describes, would hand redact_cmdline a one-item list, and item 0 is always
kept. This probe reads /proc and prints counts and program names only, never a command line.
"""

from __future__ import annotations

import os
from collections import Counter
from pathlib import Path

from submeter.privacy.redact import redact_cmdline


def main() -> None:
    readable = unsplit = kept_scrub = kept_exe_only = 0
    names: Counter[str] = Counter()
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            data = Path(f"/proc/{pid}/cmdline").read_bytes()
            name = Path(f"/proc/{pid}/comm").read_text().strip()
        except OSError:
            continue
        if not data:
            continue  # kernel threads have no command line
        readable += 1
        args = [part.decode(errors="replace") for part in data.split(b"\0") if part]
        if len(args) != 1 or " " not in args[0]:
            continue
        unsplit += 1
        names[name.split()[0]] += 1
        kept_scrub += " ".join(redact_cmdline(args)) == args[0]
        kept_exe_only += " ".join(redact_cmdline(args, mode="exe_only")) == args[0]
    print(f"processes with a readable command line: {readable}")
    print(f"of those, one string with spaces when split on NUL only: {unsplit}")
    print(f"programs: {', '.join(f'{name} x{count}' for name, count in names.most_common(8))}")
    print(f"returned whole and unchanged by redact_cmdline in scrub mode: {kept_scrub}")
    print(f"returned whole and unchanged in exe_only mode: {kept_exe_only}")


if __name__ == "__main__":
    main()
