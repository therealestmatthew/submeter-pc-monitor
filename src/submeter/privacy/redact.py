"""Scrub secrets from command lines before anything is stored, logged or served.

Command lines carry API keys, tokens and passwords. This module is applied on
the way into the store, so no later bug can expose what was never written.

The default mode, exe_only, keeps the executable name and nothing else. Scrub is
opt-in and best-effort: it hides known shapes and cannot recognise every
credential. It hides the argument after a flag one of whose words names a
secret, the value of a NAME=value pair whose name does, known token shapes
wherever they appear, and long opaque strings of letters and digits. It does not
hide paths or UUIDs, or secrets passed in other forms: an attached -pPASS,
-u user:pass, a header such as "Authorization: Bearer ...", a command inside
bash -c, --env=NAME=value, or a connection string. The executable is always kept.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Final, Literal

REDACTED: Final = "[redacted]"
Mode = Literal["scrub", "exe_only"]

_SECRET_NAME: Final = re.compile(  # whole words of a flag or name: --compass is not a password
    r"(^|[-_.])(pass(word|wd)?|pwd|secrets?|token|credentials?|authorization|bearer"
    r"|(api|access|secret|private)[-_]?key)(?=$|[-_.])",
    re.IGNORECASE,
)
_SECRET_SHAPES: Final = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}"),
)
_URL_PASSWORD: Final = re.compile(
    r"(?P<head>[a-z][a-z0-9+.-]*://[^/\s:@]+):[^@\s/]+@", re.IGNORECASE
)
_OPAQUE: Final = re.compile(r"^[A-Za-z0-9+/_=-]{32,}$")
_UUID: Final = re.compile(r"^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$", re.IGNORECASE)


def _looks_opaque(text: str) -> bool:
    return (
        bool(_OPAQUE.match(text))
        and "/" not in text  # a path, whose folder names may be long hashes
        and not _UUID.match(text)
        and any(c.isdigit() for c in text)
        and any(c.isalpha() for c in text)
    )


def redact_text(text: str, extra: Sequence[re.Pattern[str]] = ()) -> str:
    """Hide known secret shapes and URL passwords inside free text, such as a log line."""
    text = _URL_PASSWORD.sub(rf"\g<head>:{REDACTED}@", text)
    for pattern in (*_SECRET_SHAPES, *extra):
        text = pattern.sub(REDACTED, text)
    return text


def redact_cmdline(
    args: Sequence[str],
    *,
    mode: Mode = "scrub",
    exe: str = "",
    extra_patterns: Sequence[str | re.Pattern[str]] = (),
) -> tuple[str, ...]:
    """Return the command line with secrets hidden. In exe_only mode, only exe, never argv[0]."""
    if not args:
        return ()
    if mode == "exe_only":
        return (exe,) if exe else ()
    extra = [re.compile(pattern) for pattern in extra_patterns]
    first, *title = args[0].split(" ")  # a process may have rewritten argv[0] into a title
    cleaned = [first]
    hide_next = False
    for arg in (*title, *args[1:]):
        if hide_next:
            cleaned.append(REDACTED)
            hide_next = False
            continue
        name, equals, _value = arg.partition("=")
        if equals and _SECRET_NAME.search(name):
            cleaned.append(f"{name}={REDACTED}")
        elif arg.startswith("-") and not equals and _SECRET_NAME.search(arg):
            cleaned.append(arg)
            hide_next = True
        else:
            scrubbed = redact_text(arg, extra)
            cleaned.append(REDACTED if _looks_opaque(scrubbed) else scrubbed)
    return tuple(cleaned)
