"""The Restricted row's share of all CPU time in a saved `submeter top --json` list (R137, P0.5).

Run it from the repository root, with the saved file as its one argument:

    uv run python scripts/probes/restricted_share.py <folder>/top-norules.json

The list is what `submeter top --seconds 2 --json` prints: one row per workload, each with
`workload`, `cpu_s` and `processes`. The script prints the `restricted` row's `cpu_s` as a share
of the summed `cpu_s` of all rows, and that row's `processes`. A list with no `restricted` row
means every process could be read: share 0 with 0 processes, said so, and not an error.

The saved file may start with a line `$ <command>` and end with a line `exit=<code>`, as P0-O1
saves every output; the JSON between them is read. It reads only that file.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

RESTRICTED = "restricted"  # src/submeter/attribution/rules.py, RESTRICTED
EXIT_LINE = re.compile(r"exit=-?\d+")


@dataclass(frozen=True)
class Share:
    found: bool  # whether the list has a restricted row
    restricted_cpu_s: float
    total_cpu_s: float
    processes: int
    share: float | None  # None when the rows sum to 0 CPU-s: the share is unavailable


def restricted_share(rows: Sequence[Mapping[str, object]]) -> Share:
    total = sum(_number(row, "cpu_s") for row in rows)
    restricted = [row for row in rows if row.get("workload") == RESTRICTED]
    cpu_s = sum(_number(row, "cpu_s") for row in restricted)
    processes = sum(int(_number(row, "processes")) for row in restricted)
    if not restricted:
        return Share(False, 0.0, total, 0, 0.0)
    return Share(True, cpu_s, total, processes, cpu_s / total if total > 0 else None)


def describe(found: Share) -> str:
    if not found.found:
        return (
            f"no restricted row: every process could be read. share 0 of {found.total_cpu_s:.2f} "
            "CPU-s, 0 processes"
        )
    share = "unavailable (the rows sum to 0 CPU-s)" if found.share is None else f"{found.share:.4f}"
    return (
        f"restricted: {found.restricted_cpu_s:.2f} of {found.total_cpu_s:.2f} CPU-s, "
        f"share {share}, {found.processes} processes"
    )


def parse_saved(text: str) -> list[dict[str, object]]:
    """The JSON list in a saved output, without its `$ <command>` and `exit=<code>` lines."""
    lines = text.strip().splitlines()
    if lines and lines[0].startswith("$ "):
        lines = lines[1:]
    if lines and EXIT_LINE.fullmatch(lines[-1].strip()):
        lines = lines[:-1]
    try:
        found = json.loads("\n".join(lines))
    except json.JSONDecodeError:
        found = _list_line(lines)  # a line uv wrote to standard error may precede the list
    if not isinstance(found, list) or not all(isinstance(row, dict) for row in found):
        raise ValueError("the file does not hold a JSON list of rows")
    return found


def read_saved(path: Path) -> list[dict[str, object]]:
    data = path.read_bytes()
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):  # a bare > in Windows PowerShell 5.1
        return parse_saved(data.decode("utf-16"))
    return parse_saved(data.decode("utf-8-sig"))  # Out-File -Encoding utf8 writes a BOM


def _list_line(lines: Sequence[str]) -> object:
    for line in lines:
        if line.lstrip().startswith("["):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    raise ValueError("no line of the file holds a JSON list")


def _number(row: Mapping[str, object], key: str) -> float:
    value = row.get(key)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"row {row.get('workload')!r} has no number under {key!r}")
    return float(value)


def main(argv: Sequence[str]) -> int:
    if len(argv) != 1:
        print("usage: restricted_share.py <saved top --json file>")
        return 2
    try:
        rows = read_saved(Path(argv[0]))
        found = restricted_share(rows)
    except (OSError, UnicodeDecodeError, ValueError) as error:
        print(f"error: {error}")
        return 2
    print(f"{len(rows)} rows")
    print(describe(found))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
