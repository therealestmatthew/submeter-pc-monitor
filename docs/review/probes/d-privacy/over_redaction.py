"""What scrub mode hides that was never a secret, and what that does to writing a rule.

Run:  uv run python docs/review/probes/d-privacy/over_redaction.py

1. Arguments that say which container, session, script or folder a process belongs to, fed to
   redact_cmdline. HIDDEN means the stored text no longer tells two such processes apart.
2. A rule matches the command line the collector reads, but a person writes the rule from the
   text Submeter shows. For one process the probe prints both texts, and tries a rule written
   from each. Nothing is stored or sent, and every value is made up.
"""

from __future__ import annotations

import re

from submeter.attribution.rules import Rule
from submeter.core.models import ProcessKey, ProcessSample
from submeter.privacy.redact import REDACTED, redact_cmdline

HEX64 = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08"
UUID = "550e8400-e29b-41d4-a716-446655440000"
WORKER = "/home/alice/work/agents/refactor2/run_worker"
CASES: list[tuple[str, list[str]]] = [
    ("which container", ["containerd-shim-runc-v2", "-namespace", "moby", "-id", HEX64]),
    ("which agent session", ["claude", "--resume", UUID]),
    ("which script (no extension)", ["python", WORKER]),
    ("which checkout", ["git", "-C", "/home/alice/work/agents/refactor2/checkout", "status"]),
    ("which module path", ["node", "--require", "/usr/lib/node_modules/tsx/dist/preflight2"]),
    ("value after --passes", ["optimizer", "--passes", "3", "model.onnx"]),
    ("value after --bypass-cache", ["bazel", "build", "--bypass-cache", "//app:server"]),
    ("file after --no-password-prompt", ["psql", "--no-password-prompt", "report.sql"]),
    ("the folder in PWD=", ["env", "PWD=/srv/builds/app", "make", "-j8"]),
    ("an ssh option", ["ssh", "-o", "PasswordAuthentication=no", "build.example.test"]),
    ("ctrl: script with an extension", ["python", WORKER + ".py"]),
    ("ctrl: Windows path", ["python.exe", r"C:\src\agents\refactor2\tools\run_worker_for_ci"]),
    ("ctrl: short id", ["docker", "exec", "-it", "3f2a9c1e5b7d", "sh"]),
]


def sample(cmdline: tuple[str, ...]) -> ProcessSample:
    return ProcessSample(
        key=ProcessKey(pid=1, started=1.0),
        parent_pid=None,
        exe=cmdline[0],
        cmdline=cmdline,
        cwd=None,
        cpu_s=0.0,
        io_read_bytes=None,
        io_write_bytes=None,
        memory_bytes=1,
        threads=1,
        first_seen=False,
        restricted=False,
    )


def main() -> None:
    print("1. harmless arguments in scrub mode")
    for label, args in CASES:
        shown = redact_cmdline(args)
        verdict = "HIDDEN" if REDACTED in " ".join(shown) else "kept"
        print(f"  {verdict:<7}{label:<33}{' '.join(shown)}")

    print("2. a rule is matched against one text and written from another")
    live = ("python", WORKER, "--queue", "nightly")
    shown_text = " ".join(redact_cmdline(live))
    print(f"  the collector matches rules against: {' '.join(live)}")
    print(f"  the store, and so the process tree, shows: {shown_text}")
    from_live = Rule(workload="agent:refactor", cmdline=r"refactor2/run_worker")
    from_shown = Rule(workload="agent:refactor", cmdline=re.escape(shown_text))
    print(f"  a rule written from the real text matches: {from_live.matches(sample(live))}")
    print(f"  a rule written from the shown text matches: {from_shown.matches(sample(live))}")


if __name__ == "__main__":
    main()
