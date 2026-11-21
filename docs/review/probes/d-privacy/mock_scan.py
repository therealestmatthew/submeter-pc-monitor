"""Scan docs/brief.html, the mock the dashboard starts from, for two things a build would inherit.

Run:  uv run python docs/review/probes/d-privacy/mock_scan.py

1. Hosts the browser contacts just by opening the page (link, script, img, @import, url()),
   as opposed to links a person has to click. Fixed rule 3 says nothing leaves the machine.
2. Places where the mock's script builds HTML from strings, and whether the workload name that
   goes into them is escaped. In the mock the names are constants; in the product they come
   from `submeter run --as NAME`, rules.toml and other users' processes.
The probe only reads the file. It opens no connection.
"""

from __future__ import annotations

import re
from pathlib import Path

PAGE = Path(__file__).resolve().parents[3] / "brief.html"
LOADED = re.compile(
    r"<(?:link|script|img|iframe|source)\b[^>]*?\b(?:href|src)=[\"'](https?://[^\"']+)"
    r"|@import\s+(?:url\()?[\"']?(https?://[^\"')]+)"
    r"|url\([\"']?(https?://[^\"')]+)",
    re.IGNORECASE,
)
SINK = re.compile(r"\.innerHTML\s*=|insertAdjacentHTML\(")


def main() -> None:
    lines = PAGE.read_text(encoding="utf-8").splitlines()
    print("1. fetched when the page opens")
    for number, line in enumerate(lines, start=1):
        for match in LOADED.finditer(line):
            url = next(group for group in match.groups() if group)
            print(f"  line {number}: {url[:88]}")
    anchors = sum(len(re.findall(r"<a\b[^>]*href=[\"']https?://", line)) for line in lines)
    print(f"  (plus {anchors} ordinary links to other sites, which need a click)")

    print("2. HTML built from strings in the mock's script")
    sinks = [(number, line) for number, line in enumerate(lines, start=1) if SINK.search(line)]
    raw_name = [number for number, line in sinks if re.search(r"\+\s*w?k?\.name\s*\+", line)]
    escaped = [number for number, line in sinks if "esc(" in line]
    print(f"  {len(sinks)} lines assign innerHTML or call insertAdjacentHTML")
    print(f"  workload name concatenated in unescaped, at lines: {raw_name}")
    print(f"  text passed through esc() first, at lines: {escaped}")
    tree = [number for number, line in enumerate(lines, start=1) if "$('tree').textContent" in line]
    print(f"  the process tree is set with textContent, at line: {tree}")


if __name__ == "__main__":
    main()
