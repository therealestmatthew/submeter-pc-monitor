"""Decide which workload every process belongs to, and total the results.

Each process maps to exactly one workload, tried in this order: membership of
a tagged kernel group, then the rules in rules.toml, then inheritance from a
valid parent, then the Unattributed or Restricted bucket. Nothing is dropped,
which is what lets the parts be checked against the whole. Outside a kernel group,
a process keeps its workload for life, unless it execs into a program a rule matches.

A parent link counts only if the parent started no later than the child,
because operating systems reuse process ids.
"""

from __future__ import annotations

import fnmatch
import re
import tomllib
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Final

from pydantic import model_validator

from submeter.core.models import (
    AccountingSource,
    GroupTotals,
    ProcessKey,
    ProcessSample,
    Record,
    SampleBatch,
    WorkloadSample,
)

UNATTRIBUTED: Final = "unattributed"
RESTRICTED: Final = "restricted"
SYSTEM: Final = "system"
SELF: Final = "submeter"


@lru_cache(maxsize=256)
def _pattern(text: str) -> re.Pattern[str]:
    return re.compile(text)


def _base_name(path: str) -> str:
    return re.split(r"[\\/]", path)[-1].lower()


def _folder(path: str) -> str:
    return path.replace("\\", "/").lower()


class Rule(Record):
    """One entry of rules.toml. Every condition that is given must hold."""

    workload: str
    priority: int = 0
    exe: tuple[str, ...] = ()
    name: tuple[str, ...] = ()
    cmdline: str | None = None
    cwd: str | None = None
    parent: tuple[str, ...] = ()
    include_children: bool | None = None  # None: follow attribution.inherit_from_parent
    note: str = ""

    @model_validator(mode="after")
    def _usable(self) -> Rule:
        if not (self.exe or self.name or self.cmdline or self.cwd or self.parent):
            raise ValueError("a rule needs at least one of exe, name, cmdline, cwd or parent")
        if self.cmdline is not None:
            try:
                re.compile(self.cmdline)
            except re.error as error:
                raise ValueError(f"cmdline is not a valid pattern: {error}") from error
        return self

    def matches(self, process: ProcessSample, parent: ProcessSample | None = None) -> bool:
        """`parent` is the process that started this one, when it is known and still running."""
        exe, name = _base_name(process.exe), process.name.lower()  # both match as glob patterns
        if self.exe and not any(fnmatch.fnmatchcase(exe, p.lower()) for p in self.exe):
            return False
        if self.name and not any(fnmatch.fnmatchcase(name, p.lower()) for p in self.name):
            return False
        if self.parent and (
            parent is None or _base_name(parent.exe) not in {name.lower() for name in self.parent}
        ):
            return False
        if self.cmdline is not None and (
            process.cmdline is None or not _pattern(self.cmdline).search(" ".join(process.cmdline))
        ):
            return False
        return self.cwd is None or (
            process.cwd is not None and fnmatch.fnmatchcase(_folder(process.cwd), _folder(self.cwd))
        )


class RuleSet(Record):
    rule: tuple[Rule, ...] = ()

    @classmethod
    def load(cls, path: Path) -> RuleSet:
        with path.open("rb") as handle:
            return cls.model_validate(tomllib.load(handle))

    @property
    def needs_cwd(self) -> bool:
        """True when some rule matches on the working folder, which costs extra to read."""
        return any(rule.cwd is not None for rule in self.rule)

    def ordered(self) -> tuple[Rule, ...]:
        """Highest priority first. Order in the file breaks ties."""
        ranked = sorted(enumerate(self.rule), key=lambda pair: (-pair[1].priority, pair[0]))
        return tuple(rule for _, rule in ranked)


class Attribution(Record):
    workload: str
    reason: str
    inheritable: bool = False


class Attributor:
    def __init__(
        self,
        rules: RuleSet,
        *,
        inherit_from_parent: bool = True,
        self_pids: Collection[int] = (),
    ) -> None:
        """self_pids are every running Submeter process; each one, and its children, is Submeter."""
        self._rules = rules.ordered()
        self._inherit = inherit_from_parent
        self._self_pids = frozenset(self_pids)
        self._known: dict[ProcessKey, tuple[str, tuple[str, ...] | None, Attribution]] = {}
        self.changes: list[tuple[ProcessKey, str, str]] = []  # (process, from, to), last assign

    def assign(
        self,
        processes: Sequence[ProcessSample],
        tagged: Mapping[ProcessKey, str] | None = None,
        exited: Collection[ProcessKey] = (),
    ) -> dict[ProcessKey, Attribution]:
        """Give every process exactly one workload, with the reason it got it."""
        for key in exited:
            self._known.pop(key, None)
        self.changes = []
        groups = tagged or {}
        by_pid = {process.key.pid: process for process in processes}
        resolved: dict[ProcessKey, Attribution] = {}

        def resolve(process: ProcessSample, trail: frozenset[int]) -> Attribution:
            known = resolved.get(process.key)
            if known is not None:
                return known
            parent = by_pid.get(process.parent_pid) if process.parent_pid is not None else None
            if parent is not None and (
                parent.key.pid == process.key.pid or parent.key.started > process.key.started
            ):
                parent = None  # a reused pid, not the process that started this one
            result = self._remembered(process, self._direct(process, groups, parent))
            if result is None and parent is not None and parent.key.pid not in trail:
                above = resolve(parent, trail | {process.key.pid})
                if above.inheritable:
                    reason = f"inherited from pid {parent.key.pid}"
                    result = Attribution(workload=above.workload, reason=reason, inheritable=True)
            if result is None:
                bucket = RESTRICTED if process.restricted else UNATTRIBUTED
                result = Attribution(workload=bucket, reason="no rule matched")
            self._known[process.key] = (process.exe, process.cmdline, result)
            resolved[process.key] = result
            return result

        for process in processes:
            resolve(process, frozenset())
        return resolved

    def _remembered(self, process: ProcessSample, direct: Attribution | None) -> Attribution | None:
        """Last batch's workload, unless a kernel group or, after an exec, a rule now decides."""
        before = self._known.get(process.key)
        if before is None or (direct is not None and direct.reason == "kernel group"):
            return direct
        exe, cmdline, kept = before
        if direct is None or (exe, cmdline) == (process.exe, process.cmdline):
            return kept
        if direct.workload != kept.workload:
            self.changes.append((process.key, kept.workload, direct.workload))
        return direct

    def _direct(
        self,
        process: ProcessSample,
        groups: Mapping[ProcessKey, str],
        parent: ProcessSample | None,
    ) -> Attribution | None:
        group = groups.get(process.key)
        if group is not None:
            return Attribution(workload=group, reason="kernel group", inheritable=True)
        if process.key.pid in self._self_pids:
            return Attribution(workload=SELF, reason="submeter itself", inheritable=True)
        for rule in self._rules:
            if rule.matches(process, parent):
                return Attribution(
                    workload=rule.workload,
                    reason=f"rule for {rule.workload}",
                    inheritable=(
                        self._inherit if rule.include_children is None else rule.include_children
                    ),
                )
        return None


@dataclass(slots=True)
class _Total:
    cpu_s: float = 0.0
    memory_bytes: int = 0
    io_read_bytes: int = 0
    io_write_bytes: int = 0
    processes: int = 0
    started: int = 0


def aggregate(
    batch: SampleBatch,
    assignment: Mapping[ProcessKey, Attribution],
    *,
    kernel_workloads: Mapping[str, GroupTotals] = {},
) -> tuple[WorkloadSample, ...]:
    """Total a batch per workload, largest CPU user first.

    A tagged workload reports its kernel group's CPU, I/O and process count in place of its
    polled sum, because the group's figures include the processes that polling missed.
    """
    totals: dict[str, _Total] = {}
    for process in batch.processes:
        total = totals.setdefault(assignment[process.key].workload, _Total())
        total.cpu_s += process.cpu_s
        total.memory_bytes += process.memory_bytes
        total.io_read_bytes += process.io_read_bytes or 0
        total.io_write_bytes += process.io_write_bytes or 0
        total.processes += 1
        total.started += process.first_seen
    for workload, group in kernel_workloads.items():
        total = totals.setdefault(workload, _Total())
        total.cpu_s, total.processes = group.cpu_s, group.processes
        if group.io_read_bytes is not None:  # else the polled sum, until records can say None
            total.io_read_bytes = group.io_read_bytes
        if group.io_write_bytes is not None:
            total.io_write_bytes = group.io_write_bytes

    def source(workload: str) -> AccountingSource:
        if workload in kernel_workloads:
            return AccountingSource.KERNEL
        return AccountingSource.PARTIAL if workload == RESTRICTED else AccountingSource.POLLED

    samples = (
        WorkloadSample(
            taken_at=batch.taken_at,
            interval_s=batch.interval_s,
            workload=workload,
            source=source(workload),
            cpu_s=total.cpu_s,
            memory_bytes=total.memory_bytes,
            io_read_bytes=total.io_read_bytes,
            io_write_bytes=total.io_write_bytes,
            processes=total.processes,
            started=total.started,
        )
        for workload, total in totals.items()
    )
    return tuple(sorted(samples, key=lambda sample: -sample.cpu_s))
