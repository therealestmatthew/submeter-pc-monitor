"""Tests for the collector's records, provider and sampler. Run with: uv run pytest"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from submeter.core.models import ProcessCounters, ProcessKey, ProcessSample

SECRET = "sk-abcdefghijklmnopqrstu"


# ---- records ---------------------------------------------------------------------------------
def test_reprs_leave_out_the_command_line() -> None:
    cmdline = ("tool", "--api-key", SECRET)
    counters = ProcessCounters(
        key=ProcessKey(pid=1, started=1.0), cmdline=cmdline, cwd=SECRET, cpu_s=0.0, memory_bytes=0
    )
    assert SECRET not in repr(counters) and SECRET not in str(counters)
    assert not any(ProcessSample.model_fields[name].repr for name in ("cmdline", "cwd"))


def test_validation_errors_leave_out_the_command_line() -> None:
    with pytest.raises(ValidationError) as caught:
        ProcessCounters.model_validate(
            {"key": {"pid": 1, "started": 1.0}, "cwd": ("x", SECRET), "cpu_s": 0, "memory_bytes": 0}
        )
    assert SECRET not in str(caught.value)


def test_counters_carry_an_optional_child_time() -> None:
    key = ProcessKey(pid=1, started=1.0)
    assert ProcessCounters(key=key, cpu_s=0.0, memory_bytes=0).children_cpu_s is None
    counters = ProcessCounters(key=key, cpu_s=0.0, memory_bytes=0, children_cpu_s=2.5)
    assert counters.children_cpu_s == 2.5
