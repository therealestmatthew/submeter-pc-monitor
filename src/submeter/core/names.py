"""Workload names: 1 to 64 of a-z, 0-9 and . _ : -, starting with a letter or digit.

Names Submeter assigns itself are reserved, so a user rule cannot claim them. An
alert pattern may also use '*' and may name any workload, reserved ones included.
"""

from __future__ import annotations

import re
from typing import Annotated, Final

from pydantic import AfterValidator

RESERVED: Final = frozenset({"system", "restricted", "unattributed", "submeter", "machine"})


def _checked(pattern: str, reserved: frozenset[str]) -> AfterValidator:
    shape = re.compile(pattern)

    def check(value: str) -> str:
        if not shape.fullmatch(value):
            raise ValueError(f"{value!r} does not match {pattern}")
        if value in reserved:
            raise ValueError(f"{value!r} is reserved: {', '.join(sorted(reserved))}")
        return value

    return AfterValidator(check)


WorkloadName = Annotated[str, _checked(r"[a-z0-9][a-z0-9._:-]{0,63}", RESERVED)]
WorkloadPattern = Annotated[str, _checked(r"[a-z0-9*][a-z0-9._:*-]{0,63}", frozenset())]
