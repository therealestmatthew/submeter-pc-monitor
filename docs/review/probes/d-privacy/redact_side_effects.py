"""Three things beside the main leak test: log lines, harmless arguments, and the user's patterns.

Run:  uv run python docs/review/probes/d-privacy/redact_side_effects.py

1. redact_text is what a log line can be given, since a log line is not an argument list.
   Which secrets does it leave in place?
2. Which harmless arguments does redact_cmdline hide, so the process tree shows less?
3. Can the setting privacy.redact_patterns reach the store, and is a bad pattern refused on load?
Every secret is fake. Nothing is stored or sent.
"""

from __future__ import annotations

import inspect
import re

from submeter.core.config import load_settings
from submeter.privacy.redact import REDACTED, redact_cmdline, redact_text
from submeter.store.raw import RawFile, RawStore

PW, TOK = "FAKEpw-7x", "FAKEtok0123456789abcdef"
LOG_LINES = [
    (f"launch failed: tool --api-key {TOK}", TOK),
    (f"environment: API_TOKEN={TOK}", TOK),
    (f"upstream said 401 for Authorization: Bearer {TOK}", TOK),
    (f'127.0.0.1 "GET /api/v1/live?token={TOK} HTTP/1.1" 101', TOK),
    (f"could not read ['mysql', '--password', '{PW}']", PW),
    (f"ctrl: connect postgres://alice:{PW}@db/a", PW),
    ("ctrl: key sk-FAKEfake0123456789abcd rejected", "sk-FAKE"),
]
HARMLESS = [
    ["python", "/opt/agents/refactor-agent-v2/bin/worker"],
    ["cc1", "-I/usr/include/x86_64-linux-gnu/c++/13", "main.c"],
    ["git", "checkout", "3f2a9c1e5b7d4f608192a3b4c5d6e7f809112233"],
    ["rg", "--passthru", "TODO"],
    ["trainer", "--tokenizer", "gpt2"],
    ["tool", "--token-limit", "4096"],
    ["codex", "--dangerously-bypass-approvals-and-sandbox", "fix the failing test"],
    ["ctrl:", "tool", "--max-tokens", "4096"],
    ["ctrl:", "chrome", "--type=renderer"],
    ["ctrl:", "uv", "run", "pytest", "-n", "8"],
]


def main() -> None:
    print("1. redact_text on log lines")
    for line, secret in LOG_LINES:
        shown = redact_text(line)
        print(f"  {'LEAK' if secret in shown else 'ok':<5}{shown}")

    print("2. harmless arguments")
    for args in HARMLESS:
        shown = redact_cmdline(args)
        print(f"  {'HIDDEN' if REDACTED in shown else 'kept':<7}{' '.join(shown)}")

    print("3. privacy.redact_patterns")
    for target in (RawStore, RawFile):
        names = [name for name in inspect.signature(target).parameters if name != "self"]
        print(f"  {target.__name__} accepts: {', '.join(names)}")
    patterns = load_settings(overrides={"privacy": {"redact_patterns": ["("]}})
    print(f"  load_settings accepted the pattern {patterns.settings.privacy.redact_patterns[0]!r}")
    try:
        redact_cmdline(["tool", "x"], extra_patterns=patterns.settings.privacy.redact_patterns)
    except re.error as error:
        print(f"  redact_cmdline then raised {type(error).__name__}: {error}")


if __name__ == "__main__":
    main()
