"""Scrub secrets from command lines before anything is stored, logged or served.

Command lines carry API keys, tokens and passwords. This module is applied on
the way into the store, so no later bug can expose what was never written.

It errs towards hiding too much. An argument that follows a secret-looking
flag is hidden, values of secret-looking NAME=value pairs are hidden, known
token shapes are hidden wherever they appear, and any long opaque string of
letters and digits is hidden. The executable itself is always kept.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Final, Literal

REDACTED: Final = "[redacted]"
Mode = Literal["scrub", "exe_only"]

_SECRET_NAME: Final = re.compile(
    r"pass(word|wd)?|pwd|secret|token(?!s)|credential|authorization|bearer"
    r"|(api|access|secret|private)[-_]?key",
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


def _looks_opaque(text: str) -> bool:
    return (
        bool(_OPAQUE.match(text))
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
    extra_patterns: Sequence[str] = (),
) -> tuple[str, ...]:
    """Return the command line with secrets hidden. In exe_only mode, only the executable."""
    if not args:
        return ()
    if mode == "exe_only":
        return (args[0],)
    extra = [re.compile(pattern) for pattern in extra_patterns]
    cleaned = [args[0]]
    hide_next = False
    for arg in args[1:]:
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
