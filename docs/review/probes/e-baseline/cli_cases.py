"""Probe: the command line on a long watch, on missing files and on bad files.

Reads live processes through the baseline's own `top` command, as the tests do. It writes only
to a temporary folder, which it removes, and takes about 40 seconds because one case really
waits 31 seconds. Run from the repository root:

    uv run python docs/review/probes/e-baseline/cli_cases.py
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from typer.testing import CliRunner

from submeter.cli import app


def show(label: str, arguments: list[str]) -> None:
    result = CliRunner().invoke(app, arguments)
    crash = ""
    if result.exception is not None and not isinstance(result.exception, SystemExit):
        crash = f", uncaught {type(result.exception).__name__}"
    first = (result.output.strip().splitlines() or ["(no output)"])[0]
    print(f"   {label}: exit code {result.exit_code}{crash}; first line: {first[:90]}")


def watch(seconds: str) -> None:
    result = CliRunner().invoke(app, ["top", "--seconds", seconds, "--json"])
    workloads = json.loads(result.stdout)
    cpu = sum(workload["cpu_s"] for workload in workloads)
    interval = workloads[0]["interval_s"]
    print(
        f"   top --seconds {seconds}: exit code {result.exit_code}, interval_s={interval:.1f}, "
        f"CPU-seconds summed over all workloads={cpu:.3f}, keys={sorted(workloads[0])}"
    )


def main() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as name:
        folder = Path(name)
        os.environ["SUBMETER_HOME"] = str(folder / "home")
        print("1. top with a short and a long --seconds (the option allows up to 60)")
        watch("2")
        watch("31")
        print("2. Files named on the command line that do not exist or cannot be read")
        missing = str(folder / "missing.toml")
        show("top --rules MISSING", ["top", "--seconds", "0.2", "--rules", missing])
        show("config show --file MISSING", ["config", "show", "--file", missing])
        show("config check MISSING", ["config", "check", missing])
        bad_rules = folder / "rules.toml"
        bad_rules.write_text('[[rule]]\nworkload = "x"\nexe = ["a"]\ncolour = "blue"\n')
        show(
            "top --rules with an unknown key",
            ["top", "--seconds", "0.2", "--rules", str(bad_rules)],
        )
        utf16 = folder / "utf16.toml"
        utf16.write_bytes("[api]\nport = 8787\n".encode("utf-16"))
        show("config check on a UTF-16 file", ["config", "check", str(utf16)])
        print("3. Controls: errors that are reported as the brief says")
        bad = folder / "bad.toml"
        bad.write_text("[api]\nport = 80\n")
        show("config check with a port out of range", ["config", "check", str(bad)])
        show("config show --profile nosuch", ["config", "show", "--profile", "nosuch"])


if __name__ == "__main__":
    main()
