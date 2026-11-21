"""Does `uv run` contact another host when the environment is already in step? Linux, strace.

Run:  uv run python docs/review/probes/d-privacy/uv_run_network.py

Every command in the brief is started with `uv run`, and uv's documentation says it locks and
syncs the project before running. This probe starts `uv run python -c pass` under strace,
counts the connect() calls of uv and its children, and prints the count and the address
families. It tells nothing about an environment that is out of step, where uv has to download.
It needs strace, traces only its own child, and writes one file in a temporary folder.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from pathlib import Path


def main() -> None:
    if shutil.which("strace") is None or shutil.which("uv") is None:
        print("strace or uv is not installed, so nothing was measured")
        return
    with tempfile.TemporaryDirectory() as name:
        log = Path(name) / "trace.txt"
        command = ["strace", "-f", "-e", "trace=connect", "-o", str(log), "uv", "run"]
        result = subprocess.run([*command, "python", "-c", "pass"], capture_output=True, text=True)
        calls = [line for line in log.read_text().splitlines() if "connect(" in line]
    version = subprocess.run(["uv", "--version"], capture_output=True, text=True).stdout.strip()
    families = sorted(set(re.findall(r"sa_family=(\w+)", "\n".join(calls))))
    print(f"{version}: `uv run python -c pass` exited {result.returncode}")
    print(f"connect() calls made by uv and its children: {len(calls)}, families: {families}")


if __name__ == "__main__":
    main()
