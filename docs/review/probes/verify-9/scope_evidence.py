"""Re-check the counts and arithmetic that lens H's scope recommendations rest on.

Logic only: reads files in the repository and does arithmetic. Nothing is timed, no
process is read, nothing is written outside this folder's .out.txt (made by the shell).

    uv run python docs/review/probes/verify-9/scope_evidence.py

1. Settings rows in docs/08 (H10 says 13 + 29 = 42, 13 of them cut by other findings).
2. Overhead arithmetic for H3 and H12, from the per-tick costs in model_tables.out.txt.
3. Commands in docs/13: is there any CLI surface for findings once the dashboard goes (H11)?
4. Lines cited by the H leads that do not exist (docs/05 has how many lines?).
5. How many of the cut terms docs/brief.html repeats, so a scope edit must touch it too.
6. What the GPU-bound verdict row needs (H9 drops all VRAM).
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
DOCS = ROOT / "docs"


def lines(name: str) -> list[str]:
    return (DOCS / name).read_text(encoding="utf-8").splitlines()


def settings_rows() -> None:
    conf = lines("08-configuration.md")
    sampling = [row for row in conf[59:72] if row.startswith("| `")]
    other = [row for row in conf[79:108] if row.startswith("| ")]
    print(f"1. docs/08 sampling rows 60-72: {len(sampling)}; other rows 80-108: {len(other)}")
    cut = [
        "cold_interval",
        "hot_cpu_threshold",
        "thermal_interval",
        "network_interval",
        "retention.minute",
        "slow_growth.window",
        "baseline.learning_period",
        "baseline.window",
        "baseline.sensitivity",
        "quiet_hours",
        "channels",
        "port, mcp_enabled",
        "units, default_range",
    ]
    found = [name for name in cut if any(f"`{name}`" in row for row in sampling + other)]
    print(f"   rows named as cut by other findings and present: {len(found)} of {len(cut)}")


def overhead() -> None:
    # Per-tick CPU at 300 processes on this Linux machine, from model_tables.out.txt section 3.
    direct, psutil_tick = 36.0, 95.1
    print("2. whole tick + raw store, share of one core (limits 3% active, 1% idle)")
    for label, ms in (("direct /proc", direct), ("psutil fallback", psutil_tick)):
        cells = "  ".join(f"{s:g}s {ms / (s * 1000) * 100:.2f}%" for s in (1, 2, 5, 10))
        print(f"   {label:<16} {ms:5.1f} ms  {cells}")
    scaled = direct * 452 / 300
    print(f"   direct /proc scaled to 452 processes: {scaled:.1f} ms -> 2s {scaled / 20:.2f}%,")
    print(f"     5s {scaled / 50:.2f}%, 10s {scaled / 100:.2f}%  (452 is this review machine)")
    for label, ms in (("direct /proc", direct), ("psutil fallback", psutil_tick)):
        print(
            f"   shortest in-budget interval, {label}: active {ms / 30:.2f} s, idle {ms / 10:.2f} s"
        )


def commands() -> None:
    build = lines("13-build-list.md")
    cmds = [row[2:].split("`")[1] for row in build[54:67] if row.startswith("- `")]
    print(f"3. docs/13 commands: {len(cmds)}: {', '.join(c.split()[0] for c in cmds)}")
    print(f"   a command that lists findings: {any('finding' in c for c in cmds)}")
    only_write = any("POST /sessions` the only write" in row for row in build)
    print(f"   docs/13 'POST /sessions the only write': {only_write}")
    where = [n for n, row in enumerate(lines("01-overview.md"), 1) if "Where you see it" in row]
    for n in where:
        print(f"   docs/01:{n} {lines('01-overview.md')[n - 1].split(':** ')[1]}")


def citations() -> None:
    flow = lines("05-data-flow.md")
    print(f"4. docs/05 has {len(flow)} lines; H3 cites docs/05:84")
    hits = [n for n, row in enumerate(flow, 1) if re.search(r"hot (set|1)", row)]
    print(f"   docs/05 lines naming the hot set: {hits}")
    overview = lines("01-overview.md")
    print(f"   docs/01:11 is {overview[10]!r}; docs/01:12 starts {overview[11][:40]!r}")


def brief_html() -> None:
    html = (DOCS / "brief.html").read_text(encoding="utf-8")
    terms = ["Parquet", "cold_interval", "hot set", "Minute files", "guest collector", "MCP"]
    terms += ["quiet_hours", "hot-reloads", "WS /live", "profile"]
    counts = ", ".join(f"{t} {html.count(t)}" for t in terms)
    print(f"5. docs/brief.html ({len(html.splitlines())} lines) repeats: {counts}")
    readme = lines("README.md")
    said = [row for row in readme if "brief.html" in row and "brief itself" in row]
    print(f"   docs/README.md calls it the brief itself: {bool(said)}")


def gpu_row() -> None:
    analysis = lines("07-analysis.md")
    row = next(r for r in analysis if r.startswith("| GPU-bound"))
    print(f"6. docs/07 GPU-bound row: {row}")
    storage = lines("06-storage.md")
    vram = next(r for r in storage if r.startswith("| VRAM"))
    print(f"   docs/06 catalogue: {vram}")


if __name__ == "__main__":
    settings_rows()
    overhead()
    commands()
    citations()
    brief_html()
    gpu_row()
