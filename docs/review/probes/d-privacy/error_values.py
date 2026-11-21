"""Does the text of a Pydantic validation error carry the command line it was given?

Run:  uv run python docs/review/probes/d-privacy/error_values.py

A new provider will, sooner or later, hand ProcessCounters something the record refuses. The
collector will log that error. This probe builds the record three ways a Windows provider could
get wrong, with a fake secret in the command line, and prints whether str(error), which is what
a log line or a traceback shows, contains the secret. It then repeats the worst case on a copy
of the record with hide_input_in_errors switched on. Nothing is stored or sent.
"""

from __future__ import annotations

from pydantic import ConfigDict, ValidationError

from submeter.core.models import ProcessCounters, ProcessKey, Record

SECRET = "FAKEsecret-9q"
KEY = ProcessKey(pid=1, started=1.0)
UNSPLIT = f"tool.exe --api-key {SECRET}"  # Windows hands back one string, not a list
CASES: list[tuple[str, dict[str, object]]] = [
    ("command line given as one string", {"cmdline": UNSPLIT, "cpu_s": 0.0, "memory_bytes": 1}),
    (
        "a list with one unreadable item",
        {"cmdline": ("tool.exe", "--api-key", SECRET, None), "cpu_s": 0.0, "memory_bytes": 1},
    ),
    (
        "a good command line, memory missing",
        {"cmdline": ("tool.exe", "--api-key", SECRET), "cpu_s": 0.0},
    ),
]


class Hidden(Record):
    """The same contract as Record, with input values kept out of error text."""

    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)
    cmdline: tuple[str, ...] | None = None


def main() -> None:
    for label, fields in CASES:
        try:
            ProcessCounters(key=KEY, **fields)  # type: ignore[arg-type]
        except ValidationError as error:
            text = str(error)
            line = next(row.strip() for row in text.splitlines() if "input_value" in row)
            print(f"{label}:")
            print(f"  str(error) contains the secret: {SECRET in text}")
            print(f"  a piece of the secret (its last five characters): {SECRET[-5:] in text}")
            print(f"  shown: {line[:118]}")
    try:
        Hidden(cmdline=UNSPLIT)  # type: ignore[arg-type]
    except ValidationError as error:
        text = str(error)
        print("with hide_input_in_errors=True on the record:")
        print(f"  str(error) contains the secret: {SECRET in text}")
        print(f"  shown: {text.splitlines()[2].strip()}")
        print(f"  error.errors() still holds the input: {SECRET in repr(error.errors())}")
        safe = error.errors(include_input=False)
        print(f"  error.errors(include_input=False) holds it: {SECRET in repr(safe)}")


if __name__ == "__main__":
    main()
