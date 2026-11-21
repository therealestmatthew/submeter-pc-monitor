"""A process provider built on psutil. It runs on every platform.

This is the fallback and the cross-check, not the hot path: it asks about one
process at a time, which is too slow for a 1-second cadence on a busy machine.
The Windows bulk snapshot and the Linux /proc reader replace it there, and
tests compare their figures with this one.

A process that cannot be read fully is still returned, marked restricted, so
it is counted and never silently dropped.
"""

from __future__ import annotations

import time

import psutil

from submeter.core.models import (
    Availability,
    Capability,
    ProcessCounters,
    ProcessKey,
    Snapshot,
    SystemCounters,
)


class PsutilProvider:
    name = "process.psutil"

    def __init__(self, *, read_cwd: bool = False) -> None:
        self._read_cwd = read_cwd
        self._seen = 0
        self._restricted = 0

    def capability(self) -> Capability:
        if self._restricted:
            note = f"{self._restricted} of {self._seen} processes not fully readable"
            return Capability(name=self.name, status=Availability.PARTIAL, note=note)
        return Capability(name=self.name, status=Availability.FULL)

    def snapshot(self) -> Snapshot:
        taken_at, monotonic = time.time(), time.monotonic()
        processes = [c for c in map(self._read, psutil.process_iter()) if c is not None]
        self._seen = len(processes)
        self._restricted = sum(1 for c in processes if c.restricted)
        return Snapshot(
            taken_at=taken_at,
            monotonic=monotonic,
            processes=tuple(processes),
            system=self._system(),
        )

    def _read(self, process: psutil.Process) -> ProcessCounters | None:
        try:
            with process.oneshot():
                key = ProcessKey(pid=process.pid, started=process.create_time())
                restricted = False
                try:
                    times = process.cpu_times()
                    memory = process.memory_info()
                    cpu_s = times.user + times.system
                    memory_bytes = int(getattr(memory, "private", memory.rss))
                    threads = process.num_threads()
                except psutil.AccessDenied:
                    cpu_s, memory_bytes, threads, restricted = 0.0, 0, 0, True
                cmdline: tuple[str, ...] | None = None
                try:
                    cmdline = tuple(process.cmdline())
                except psutil.AccessDenied:
                    restricted = True
                read_bytes: int | None = None
                write_bytes: int | None = None
                io_counters = getattr(process, "io_counters", None)  # psutil has none on macOS
                if io_counters is not None:
                    try:
                        io = io_counters()
                        read_bytes, write_bytes = int(io.read_bytes), int(io.write_bytes)
                    except psutil.AccessDenied:
                        restricted = True
                    except NotImplementedError:
                        pass
                cwd: str | None = None
                if self._read_cwd:
                    try:
                        cwd = process.cwd()
                    except psutil.AccessDenied:
                        restricted = True
                return ProcessCounters(
                    key=key,
                    parent_pid=process.ppid(),
                    exe=process.name(),
                    cmdline=cmdline,
                    cwd=cwd,
                    cpu_s=cpu_s,
                    io_read_bytes=read_bytes,
                    io_write_bytes=write_bytes,
                    memory_bytes=memory_bytes,
                    threads=threads,
                    restricted=restricted,
                )
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            return None
        except psutil.AccessDenied:
            return ProcessCounters(
                key=ProcessKey(pid=process.pid, started=0.0),
                cpu_s=0.0,
                memory_bytes=0,
                restricted=True,
            )

    @staticmethod
    def _system() -> SystemCounters:
        per_core = psutil.cpu_times(percpu=True)
        busy = tuple(
            sum(t)
            - t.idle
            - getattr(t, "iowait", 0.0)
            - getattr(t, "guest", 0.0)
            - getattr(t, "guest_nice", 0.0)
            for t in per_core
        )
        memory = psutil.virtual_memory()
        return SystemCounters(
            logical_cores=len(per_core),
            cpu_busy_s=busy,
            memory_total_bytes=memory.total,
            memory_available_bytes=memory.available,
        )
