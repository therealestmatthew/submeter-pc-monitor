"""What would each redaction mode cost on this machine? Counts only, never a command line.

Run:  uv run python docs/review/probes/d-privacy/mode_tradeoff.py

1. The cases of redact_leaks.py again, in exe_only mode: how many secrets survive.
2. This user's live processes, read with psutil as the baseline provider does. How many run a
   shell or a language runtime, so that the executable alone does not say what they are doing;
   how many of those name a script as their first plain argument, and how many carry a whole
   command in one argument; and how many different texts each mode would store. Scrub mode is
   also counted for how often it hides something.
It reads command lines to count them and prints numbers only. Nothing is stored or sent.
"""

from __future__ import annotations

import getpass
import re

import psutil
from redact_leaks import CASES

from submeter.privacy.redact import REDACTED, redact_cmdline

RUNTIME = re.compile(
    r"^(python[\d.]*|node|bun|deno|java|ruby|perl|php|dotnet|bash|sh|dash|zsh|fish|pwsh"
    r"|powershell|cmd|uv|npm|npx|pnpm|yarn|cargo|go)(\.exe)?$",
    re.IGNORECASE,
)
SCRIPT = re.compile(r"\.(py|js|mjs|cjs|ts|sh|ps1|rb|pl|php|jar|bat|cmd)$", re.IGNORECASE)
WRAPPER = {"-c", "-lc", "-ic", "/c", "/k", "-command", "-encodedcommand", "-e"}


def base(path: str) -> str:
    return re.split(r"[\\/]", path)[-1]


def main() -> None:
    plain = [case for case in CASES if not case[0].endswith("ctrl")]
    leaked = sum(
        secret in " ".join(redact_cmdline(args, mode="exe_only")) for _, args, secret in plain
    )
    print(f"1. exe_only on the {len(plain)} realistic cases, given a split list: {leaked} leaked")

    me = getpass.getuser()
    mine: list[list[str]] = []
    for process in psutil.process_iter(["username", "cmdline"]):
        if process.info["username"] == me and process.info["cmdline"]:
            mine.append(process.info["cmdline"])
    runtimes = [args for args in mine if RUNTIME.match(base(args[0]))]
    first_plain = [next((a for a in args[1:] if not a.startswith("-")), "") for args in runtimes]
    with_script = sum(1 for argument in first_plain if SCRIPT.search(argument))
    wrapped = sum(1 for args in runtimes if WRAPPER & {a.lower() for a in args[1:4]})
    scrubbed = [" ".join(redact_cmdline(args)) for args in mine]
    print(f"2. this user's processes with a readable command line: {len(mine)}")
    print(f"   running a shell or a language runtime: {len(runtimes)}")
    print(f"   of those, with a script file as the first plain argument: {with_script}")
    print(f"   of those, given a whole command in one argument (-c and the like): {wrapped}")
    print(f"   different texts stored in exe_only mode: {len({base(args[0]) for args in mine})}")
    print(f"   different texts stored in scrub mode: {len(set(scrubbed))}")
    hidden = sum(1 for text in scrubbed if REDACTED in text)
    print(f"   command lines in which scrub mode hides at least one argument: {hidden}")


if __name__ == "__main__":
    main()
