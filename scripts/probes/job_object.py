"""Probe 1, the Job Object (P0-W2-T2, gate P0.8, decision B1).

Run it from the repository root, naming the shell it runs from:

    uv run python scripts/probes/job_object.py terminal
    uv run python scripts/probes/job_object.py vscode
    uv run python scripts/probes/job_object.py claude-code

It runs steps a to h of gate P0.8 (docs/PLAN.md 6.4) and prints one text report: each step's
result, then the decision rows of P0.12 (B1, and the breakaway record of step f).

- a. Create a job as the user.
- b. Create a child inside a new job (PROC_THREAD_ATTRIBUTE_JOB_LIST), and record whether the
  probe itself runs in a job: IsProcessInJob(GetCurrentProcess(), NULL).
- c. After every child has exited, the job's CPU totals against each child's GetProcessTimes,
  read on handles held until the end: within 2%, with ActiveProcesses 0.
- d. Reopen the job by name after its creator exits while a holder keeps a handle (expected to
  succeed), then after the holder closes it (expected to fail with error 2).
- e. A process in a job without JOB_OBJECT_LIMIT_BREAKAWAY_OK starts a direct child with
  CREATE_BREAKAWAY_FROM_JOB: the error code is recorded.
- f. With JOB_OBJECT_LIMIT_BREAKAWAY_OK set (and never the silent breakaway limit): node, then
  bash, then a grandchild, which reports IsProcessInJob(grandchild, job). Skipped with the
  reason when node or bash is absent (B16).
- g. 500 children busy 5 ms each: the job CPU and the spacing of its values, to see whether
  it clusters at multiples of about 15.6 ms.
- h. A burner in a job nested inside a job the probe made: both jobs' CPU totals, and whether
  the outer job's total includes the burner's within 2%, as R49's subtraction assumes (K14).

The decision: step a or b failing gives "stop and ask" (tagged runs are on the floor,
docs/15-phases-and-decisions.md:75); steps d and h as expected give "the holder design stands";
step d or h otherwise gives "B1 goes to the owner".

It observes only (fixed rule 1). It acts only on processes it starts and on jobs it creates;
it sets a limit, BREAKAWAY_OK, only on step f's own job; it never terminates a process: every
child does fixed work and exits on its own, and a child still running at a timeout is left to
finish. It needs no administrator rights and opens no connection. Every Windows call is made
inside a function, so the module loads on Linux for its tests; run there, it prints that Job
Objects exist only on Windows and exits with code 2.

Children run the base interpreter (sys._base_executable) with -I -S, never sys.executable: a
virtual environment's python.exe on Windows is a redirector that starts the base interpreter
as a second process (docs/PLAN.md 7.4), so GetProcessTimes on the held handle would measure
the redirector, not the work.
"""

from __future__ import annotations

import ctypes
import functools
import math
import os
import platform
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import uuid
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# --- outcomes, decisions and thresholds ------------------------------------------------------

PASS = "pass"
FAIL = "fail"
RECORDED = "recorded"
SKIPPED = "skipped"
ERROR = "error"

STANDS = "the holder design stands"
STOP = "stop and ask"
OWNER = "B1 goes to the owner"

TOLERANCE = 0.02  # steps c and h: within 2% (docs/PLAN.md 6.4, P0.8)
TICK_100NS = 156_250  # 15.625 ms, the default clock interval, in 100-ns units
TICK_SLACK_100NS = TICK_100NS // 100  # a value within 1% of a tick multiple counts as on it
DEFAULT_TIMEOUT_S = 120.0  # the longest the probe waits for any one child
HOLD_LIMIT_S = 300.0  # a creator or holder exits on its own after this, if never told to

STEP_B_BUSY_MS = 50
STEP_C_CHILDREN = 4
STEP_C_BUSY_MS = 200
STEP_G_CHILDREN = 500
STEP_G_BUSY_MS = 5
STEP_H_BUSY_MS = 1000

TITLES = {
    "a": "create a job as the user",
    "b": "create a child inside a new job (PROC_THREAD_ATTRIBUTE_JOB_LIST)",
    "c": "job CPU against the children's GetProcessTimes, after every child exited",
    "d": "reopen the job by name after its creator exits, while held and after",
    "e": "a direct child with CREATE_BREAKAWAY_FROM_JOB, in a job without BREAKAWAY_OK",
    "f": "node, then bash, then a grandchild, in a job with BREAKAWAY_OK",
    "g": f"{STEP_G_CHILDREN} children busy {STEP_G_BUSY_MS} ms each: job CPU and its spacing",
    "h": "a burner in a job nested inside a job the probe made",
}

# --- Windows constants (Microsoft's documentation for each call) ------------------------------

ERROR_FILE_NOT_FOUND = 2
ERROR_ALREADY_EXISTS = 183
JOB_OBJECT_QUERY = 0x0004
JOB_OBJECT_LIMIT_BREAKAWAY_OK = 0x0000_0800
JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION = 1  # JOBOBJECTINFOCLASS JobObjectBasicAccounting...
JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9  # JOBOBJECTINFOCLASS JobObjectExtendedLimit...
CREATE_UNICODE_ENVIRONMENT = 0x0000_0400
EXTENDED_STARTUPINFO_PRESENT = 0x0008_0000
CREATE_BREAKAWAY_FROM_JOB = 0x0100_0000
PROC_THREAD_ATTRIBUTE_JOB_LIST = 0x0002_000D  # ProcThreadAttributeValue(13, FALSE, TRUE, FALSE)
WAIT_OBJECT_0 = 0

# --- result records ---------------------------------------------------------------------------

Value = float | int | bool | str | None


@dataclass(frozen=True)
class StepResult:
    """One step's result: its letter, title, outcome, the values it recorded and notes."""

    step: str
    title: str
    outcome: str
    values: Mapping[str, Value] = field(default_factory=dict)
    notes: tuple[str, ...] = ()


def _number(value: Value) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def _error_text(code: int) -> str:
    return "opened" if code == 0 else f"error {code}"


def reopen_as_expected(result: StepResult | None) -> tuple[bool, str]:
    """Step d as expected: opened while the holder held a handle, then error 2 after."""
    if result is None or result.outcome in (ERROR, SKIPPED):
        return False, "did not run" if result is None else f"{result.outcome}"
    held = result.values.get("reopen_while_held_error")
    after = result.values.get("reopen_after_close_error")
    if isinstance(held, bool) or not isinstance(held, int):
        return False, "the reopen while held was not recorded"
    if isinstance(after, bool) or not isinstance(after, int):
        return False, "the reopen after the holder closed was not recorded"
    ok = held == 0 and after == ERROR_FILE_NOT_FOUND
    return ok, (
        f"reopen while held: {_error_text(held)}; after the holder closed: {_error_text(after)}"
        " (expected: opened, then error 2)"
    )


def outer_includes_burner(result: StepResult | None) -> tuple[bool, str]:
    """Step h as expected: the outer job's CPU equals the nested burner's within 2%."""
    if result is None or result.outcome in (ERROR, SKIPPED):
        return False, "did not run" if result is None else f"{result.outcome}"
    outer = _number(result.values.get("outer_cpu_s"))
    burner = _number(result.values.get("burner_cpu_s"))
    if outer is None or burner is None:
        return False, "the outer job's or the burner's CPU was not recorded"
    if burner <= 0:
        return False, f"the burner's CPU is {burner} s, so no share can be judged"
    gap = (outer - burner) / burner
    ok = abs(gap) <= TOLERANCE + 1e-9  # the slack absorbs float rounding only
    return ok, (
        f"outer job {outer:.4f} s against the burner's {burner:.4f} s, {gap:+.2%}"
        f" (expected within {TOLERANCE:.0%})"
    )


def decide(results: Mapping[str, StepResult]) -> tuple[str, str]:
    """The B1 decision row of P0.12, and its reason, from the step results."""
    stopped = [
        f"step {letter} {'did not run' if letter not in results else results[letter].outcome}"
        for letter in ("a", "b")
        if letter not in results or results[letter].outcome != PASS
    ]
    if stopped:
        return STOP, (
            f"{'; '.join(stopped)}: tagged runs are on the floor"
            " (docs/15-phases-and-decisions.md:75)"
        )
    d_ok, d_why = reopen_as_expected(results.get("d"))
    h_ok, h_why = outer_includes_burner(results.get("h"))
    if d_ok and h_ok:
        return STANDS, f"step d: {d_why}; step h: {h_why}"
    checks = (("d", d_ok, d_why), ("h", h_ok, h_why))
    return OWNER, "; ".join(f"step {letter}: {why}" for letter, ok, why in checks if not ok)


def breakaway_record(result: StepResult | None) -> str:
    """The P0.12 row for step f: what happened to the grandchild, or why it was skipped."""
    if result is None:
        return "step f did not run"
    if result.outcome == SKIPPED:
        return f"skipped: {result.values.get('reason')}"
    if result.outcome == ERROR:
        return f"error: {result.values.get('error')}"
    return (
        f"IsProcessInJob(grandchild, job) = {result.values.get('grandchild_in_job')}"
        " with BREAKAWAY_OK set, through node then bash"
        f" (IsProcessInJob(grandchild, NULL) = {result.values.get('grandchild_in_any_job')})"
    )


def describe(result: StepResult) -> str:
    """One step's result as report lines."""
    lines = [f"step {result.step} [{result.outcome}] {result.title}"]
    lines += [f"    {key} = {value}" for key, value in result.values.items()]
    lines += [f"    note: {note}" for note in result.notes]
    return "\n".join(lines)


# --- Windows structures, of fixed-width types (64-bit layouts in the comments) -----------------


class BasicAccounting(ctypes.Structure):
    """JOBOBJECT_BASIC_ACCOUNTING_INFORMATION, 48 bytes."""

    _fields_ = [
        ("TotalUserTime", ctypes.c_int64),
        ("TotalKernelTime", ctypes.c_int64),
        ("ThisPeriodTotalUserTime", ctypes.c_int64),
        ("ThisPeriodTotalKernelTime", ctypes.c_int64),
        ("TotalPageFaultCount", ctypes.c_uint32),
        ("TotalProcesses", ctypes.c_uint32),
        ("ActiveProcesses", ctypes.c_uint32),
        ("TotalTerminatedProcesses", ctypes.c_uint32),
    ]


class BasicLimit(ctypes.Structure):
    """JOBOBJECT_BASIC_LIMIT_INFORMATION, 64 bytes."""

    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_int64),
        ("PerJobUserTimeLimit", ctypes.c_int64),
        ("LimitFlags", ctypes.c_uint32),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", ctypes.c_uint32),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", ctypes.c_uint32),
        ("SchedulingClass", ctypes.c_uint32),
    ]


class IoCounters(ctypes.Structure):
    """IO_COUNTERS, 48 bytes."""

    _fields_ = [
        ("ReadOperationCount", ctypes.c_uint64),
        ("WriteOperationCount", ctypes.c_uint64),
        ("OtherOperationCount", ctypes.c_uint64),
        ("ReadTransferCount", ctypes.c_uint64),
        ("WriteTransferCount", ctypes.c_uint64),
        ("OtherTransferCount", ctypes.c_uint64),
    ]


class ExtendedLimit(ctypes.Structure):
    """JOBOBJECT_EXTENDED_LIMIT_INFORMATION, 144 bytes."""

    _fields_ = [
        ("BasicLimitInformation", BasicLimit),
        ("IoInfo", IoCounters),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
    ]


class StartupInfo(ctypes.Structure):
    """STARTUPINFOW, 104 bytes."""

    _fields_ = [
        ("cb", ctypes.c_uint32),
        ("lpReserved", ctypes.c_void_p),
        ("lpDesktop", ctypes.c_void_p),
        ("lpTitle", ctypes.c_void_p),
        ("dwX", ctypes.c_uint32),
        ("dwY", ctypes.c_uint32),
        ("dwXSize", ctypes.c_uint32),
        ("dwYSize", ctypes.c_uint32),
        ("dwXCountChars", ctypes.c_uint32),
        ("dwYCountChars", ctypes.c_uint32),
        ("dwFillAttribute", ctypes.c_uint32),
        ("dwFlags", ctypes.c_uint32),
        ("wShowWindow", ctypes.c_uint16),
        ("cbReserved2", ctypes.c_uint16),
        ("lpReserved2", ctypes.c_void_p),
        ("hStdInput", ctypes.c_void_p),
        ("hStdOutput", ctypes.c_void_p),
        ("hStdError", ctypes.c_void_p),
    ]


class StartupInfoEx(ctypes.Structure):
    """STARTUPINFOEXW, 112 bytes."""

    _fields_ = [("StartupInfo", StartupInfo), ("lpAttributeList", ctypes.c_void_p)]


class ProcessInformation(ctypes.Structure):
    """PROCESS_INFORMATION, 24 bytes."""

    _fields_ = [
        ("hProcess", ctypes.c_void_p),
        ("hThread", ctypes.c_void_p),
        ("dwProcessId", ctypes.c_uint32),
        ("dwThreadId", ctypes.c_uint32),
    ]


# --- Windows calls -----------------------------------------------------------------------------


class Unavailable(RuntimeError):
    """Raised on a system without Job Objects."""


class CallFailed(OSError):
    """A Windows call returned failure; `error` is GetLastError's code."""

    def __init__(self, call: str, error: int) -> None:
        super().__init__(f"{call} failed with error {error}")
        self.call = call
        self.error = error


def _last_error() -> int:
    if sys.platform != "win32":
        return 0
    return ctypes.get_last_error()


def _clear_error() -> None:
    """Zero the saved last error, so a success that sets none is not read as a stale failure."""
    if sys.platform == "win32":
        ctypes.set_last_error(0)


@functools.cache
def kernel32() -> Any:
    """kernel32 with the signature of every call the probe makes."""
    if sys.platform != "win32":
        raise Unavailable("Job Objects exist only on Windows")
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    handle, dword, boolean = ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int
    signatures: dict[str, tuple[Any, tuple[Any, ...]]] = {
        "CreateJobObjectW": (handle, (ctypes.c_void_p, ctypes.c_wchar_p)),
        "OpenJobObjectW": (handle, (dword, boolean, ctypes.c_wchar_p)),
        "QueryInformationJobObject": (
            boolean,
            (handle, ctypes.c_int, ctypes.c_void_p, dword, ctypes.POINTER(dword)),
        ),
        "SetInformationJobObject": (boolean, (handle, ctypes.c_int, ctypes.c_void_p, dword)),
        "IsProcessInJob": (boolean, (handle, handle, ctypes.POINTER(boolean))),
        "GetCurrentProcess": (handle, ()),
        "GetProcessTimes": (boolean, (handle, *(ctypes.POINTER(ctypes.c_uint64),) * 4)),
        "CloseHandle": (boolean, (handle,)),
        "CreateProcessW": (
            boolean,
            (
                ctypes.c_wchar_p,
                ctypes.c_wchar_p,
                ctypes.c_void_p,
                ctypes.c_void_p,
                boolean,
                dword,
                ctypes.c_void_p,
                ctypes.c_wchar_p,
                ctypes.c_void_p,
                ctypes.POINTER(ProcessInformation),
            ),
        ),
        "InitializeProcThreadAttributeList": (
            boolean,
            (ctypes.c_void_p, dword, dword, ctypes.POINTER(ctypes.c_size_t)),
        ),
        "UpdateProcThreadAttribute": (
            boolean,
            (
                ctypes.c_void_p,
                dword,
                ctypes.c_size_t,
                ctypes.c_void_p,
                ctypes.c_size_t,
                ctypes.c_void_p,
                ctypes.c_void_p,
            ),
        ),
        "DeleteProcThreadAttributeList": (None, (ctypes.c_void_p,)),
        "WaitForSingleObject": (dword, (handle, dword)),
        "GetExitCodeProcess": (boolean, (handle, ctypes.POINTER(dword))),
    }
    for name, (restype, argtypes) in signatures.items():
        function = getattr(k, name)
        function.restype = restype
        function.argtypes = argtypes
    return k


def close(handle: int | None) -> None:
    if handle:
        kernel32().CloseHandle(handle)


def current_process() -> int:
    handle: int = kernel32().GetCurrentProcess()
    return handle


def create_job(name: str) -> int:
    """A new named job with no limits; raises CallFailed if the name already exists."""
    k = kernel32()
    _clear_error()
    job = k.CreateJobObjectW(None, name)
    error = _last_error()
    if not job:
        raise CallFailed("CreateJobObjectW", error)
    if error == ERROR_ALREADY_EXISTS:
        close(job)
        raise CallFailed("CreateJobObjectW (the name was taken)", error)
    handle: int = job
    return handle


def open_job(name: str) -> tuple[int | None, int]:
    """OpenJobObjectW(JOB_OBJECT_QUERY) by name: the handle, or None and the error code."""
    job = kernel32().OpenJobObjectW(JOB_OBJECT_QUERY, False, name)
    if not job:
        return None, _last_error()
    handle: int = job
    return handle, 0


def try_open(name: str) -> int:
    """0 if the job could be opened by name (the handle is closed again), else the error."""
    job, error = open_job(name)
    close(job)
    return error


def accounting(job: int | None) -> BasicAccounting:
    info = BasicAccounting()
    ok = kernel32().QueryInformationJobObject(
        job, JOB_OBJECT_BASIC_ACCOUNTING_INFORMATION, ctypes.byref(info), ctypes.sizeof(info), None
    )
    if not ok:
        raise CallFailed("QueryInformationJobObject (basic accounting)", _last_error())
    return info


def limit_flags(job: int) -> int:
    info = ExtendedLimit()
    ok = kernel32().QueryInformationJobObject(
        job, JOB_OBJECT_EXTENDED_LIMIT_INFORMATION, ctypes.byref(info), ctypes.sizeof(info), None
    )
    if not ok:
        raise CallFailed("QueryInformationJobObject (extended limits)", _last_error())
    flags: int = info.BasicLimitInformation.LimitFlags
    return flags


def allow_breakaway(job: int) -> None:
    """Set JOB_OBJECT_LIMIT_BREAKAWAY_OK, and nothing else, on a job the probe created."""
    info = ExtendedLimit()
    info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_BREAKAWAY_OK
    ok = kernel32().SetInformationJobObject(
        job, JOB_OBJECT_EXTENDED_LIMIT_INFORMATION, ctypes.byref(info), ctypes.sizeof(info)
    )
    if not ok:
        raise CallFailed("SetInformationJobObject (BREAKAWAY_OK)", _last_error())


def in_job(process: int, job: int | None) -> bool:
    """IsProcessInJob; job None asks whether the process runs in any job."""
    result = ctypes.c_int(0)
    if not kernel32().IsProcessInJob(process, job, ctypes.byref(result)):
        raise CallFailed("IsProcessInJob", _last_error())
    return bool(result.value)


def cpu_100ns(process: int) -> tuple[int, int]:
    """GetProcessTimes: (kernel, user) in 100-ns units."""
    creation, exited, kernel, user = (ctypes.c_uint64() for _ in range(4))
    ok = kernel32().GetProcessTimes(
        process,
        ctypes.byref(creation),
        ctypes.byref(exited),
        ctypes.byref(kernel),
        ctypes.byref(user),
    )
    if not ok:
        raise CallFailed("GetProcessTimes", _last_error())
    return kernel.value, user.value


def job_cpu_100ns(info: BasicAccounting) -> int:
    total: int = info.TotalUserTime + info.TotalKernelTime
    return total


@dataclass
class Child:
    """A process the probe created, with the handles it holds."""

    pid: int
    process: int
    thread: int

    def wait(self, timeout_s: float) -> int:
        """Wait for the child to exit on its own; its exit code. Never terminates it."""
        k = kernel32()
        waited = k.WaitForSingleObject(self.process, max(0, int(timeout_s * 1000)))
        if waited != WAIT_OBJECT_0:
            raise TimeoutError(
                f"pid {self.pid} still running after {timeout_s:.0f} s (wait returned {waited});"
                " the probe never terminates a process, so it is left to finish"
            )
        code = ctypes.c_uint32(0)
        if not k.GetExitCodeProcess(self.process, ctypes.byref(code)):
            raise CallFailed("GetExitCodeProcess", _last_error())
        return code.value

    def close(self) -> None:
        close(self.thread)
        close(self.process)
        self.thread = self.process = 0


def _environment_block(environment: Mapping[str, str]) -> Any:
    text = "".join(
        f"{key}={value}\0" for key, value in sorted(environment.items(), key=lambda i: i[0].upper())
    )
    text += "\0"
    return (ctypes.c_wchar * len(text))(*text)


def create_in_jobs(
    args: Sequence[str],
    jobs: Sequence[int],
    *,
    flags: int = 0,
    environment: Mapping[str, str] | None = None,
) -> Child:
    """CreateProcessW with PROC_THREAD_ATTRIBUTE_JOB_LIST: the child starts inside the jobs,
    assigned in the order given, so a later job is nested inside an earlier one."""
    k = kernel32()
    size = ctypes.c_size_t(0)
    k.InitializeProcThreadAttributeList(None, 1, 0, ctypes.byref(size))  # sizes the list
    attributes = ctypes.create_string_buffer(size.value)
    if not k.InitializeProcThreadAttributeList(attributes, 1, 0, ctypes.byref(size)):
        raise CallFailed("InitializeProcThreadAttributeList", _last_error())
    try:
        handles = (ctypes.c_void_p * len(jobs))(*jobs)  # must live until the list is deleted
        if not k.UpdateProcThreadAttribute(
            attributes,
            0,
            PROC_THREAD_ATTRIBUTE_JOB_LIST,
            handles,
            ctypes.sizeof(handles),
            None,
            None,
        ):
            raise CallFailed("UpdateProcThreadAttribute (job list)", _last_error())
        startup = StartupInfoEx()
        startup.StartupInfo.cb = ctypes.sizeof(StartupInfoEx)
        startup.lpAttributeList = ctypes.addressof(attributes)
        command = ctypes.create_unicode_buffer(subprocess.list2cmdline(args))
        block = None if environment is None else _environment_block(environment)
        creation = EXTENDED_STARTUPINFO_PRESENT | flags
        if block is not None:
            creation |= CREATE_UNICODE_ENVIRONMENT
        created = ProcessInformation()
        ok = k.CreateProcessW(
            args[0],
            command,
            None,
            None,
            False,
            creation,
            block,
            None,
            ctypes.byref(startup),
            ctypes.byref(created),
        )
        if not ok:
            raise CallFailed("CreateProcessW (job list)", _last_error())
    finally:
        k.DeleteProcThreadAttributeList(attributes)
    return Child(created.dwProcessId, created.hProcess, created.hThread)


# --- children ----------------------------------------------------------------------------------

SCRIPT = Path(__file__).resolve()
CHILD_PYTHON = str(getattr(sys, "_base_executable", "") or sys.executable)
# Busy for argv[1] ms of wall time, then exit: one line, so it needs no newline on the command
# line; iter() calls the lambda until it returns the sentinel False.
BUSY = (
    "import sys,time;e=time.perf_counter()+float(sys.argv[1])/1000;"
    "all(iter(lambda:time.perf_counter()<e,False))"
)


def busy_args(milliseconds: int) -> list[str]:
    return [CHILD_PYTHON, "-I", "-S", "-c", BUSY, str(milliseconds)]


def role_args(role: str, *args: str) -> list[str]:
    return [CHILD_PYTHON, "-I", "-S", str(SCRIPT), "--role", role, *args]


def job_name(step: str) -> str:
    return f"submeter-probe1-{os.getpid()}-{step}-{uuid.uuid4().hex[:8]}"


def shown(path: str | Path) -> str:
    """A path as the report prints it: the home folder as ~, so no user name is written."""
    text, home = str(path), str(Path.home())
    return "~" + text[len(home) :] if home and text.lower().startswith(home.lower()) else text


def _hold_until_told(job: int | None) -> int:
    """Keep the handle until a line or the end of stdin arrives, then close it and exit.

    After HOLD_LIMIT_S with neither, close it and exit anyway: a creator or holder whose probe
    vanished still ends on its own.
    """
    reader = threading.Thread(target=sys.stdin.readline, daemon=True)
    reader.start()
    reader.join(HOLD_LIMIT_S)
    close(job)
    print("closed", flush=True)
    if reader.is_alive():  # the reader still holds stdin's lock, so skip the normal shutdown
        os._exit(3)
    return 0


def _role_creator(name: str) -> int:
    """Create the named job, say so, and keep it until told to exit."""
    _clear_error()
    job = kernel32().CreateJobObjectW(None, name)
    print(f"created {0 if job else _last_error()}", flush=True)
    return _hold_until_told(job)


def _role_holder(name: str) -> int:
    """Open the named job, say so, and hold the handle until told to close it."""
    job, error = open_job(name)
    print(f"held {error}", flush=True)
    return _hold_until_told(job)


def _role_breakaway(out: str) -> int:
    """From inside a job, start a direct child with CREATE_BREAKAWAY_FROM_JOB; write the error."""
    try:
        child = subprocess.Popen(
            [sys.executable, "-I", "-S", "-c", "pass"], creationflags=CREATE_BREAKAWAY_FROM_JOB
        )
    except OSError as failed:
        code = getattr(failed, "winerror", None) or failed.errno or -1
        Path(out).write_text(f"{code}\n", encoding="utf-8")
        return 0
    child.wait(timeout=DEFAULT_TIMEOUT_S)
    Path(out).write_text("0\n", encoding="utf-8")
    return 0


def _role_grandchild() -> int:
    """At the end of node, then bash: write IsProcessInJob for this process and step f's job."""
    out = Path(os.environ["SUBMETER_PROBE_OUT"])
    job, error = open_job(os.environ["SUBMETER_PROBE_JOB"])
    me = current_process()
    in_named = in_job(me, job) if job else None
    close(job)
    out.write_text(
        f"in_job={in_named} any_job={in_job(me, None)} open_error={error}\n", encoding="utf-8"
    )
    return 0


ROLES: dict[str, Callable[..., int]] = {
    "creator": _role_creator,
    "holder": _role_holder,
    "breakaway": _role_breakaway,
    "grandchild": _role_grandchild,
}


class _Role:
    """A creator or holder of step d: started outside every job the probe made, told to exit
    by the end of its stdin, and read line by line on a thread, so each read can time out."""

    def __init__(self, role: str, *args: str) -> None:
        self.process = subprocess.Popen(
            role_args(role, *args),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        self.lines: queue.Queue[str] = queue.Queue()
        self.pump = threading.Thread(target=self._pump, daemon=True)
        self.pump.start()

    def _pump(self) -> None:
        assert self.process.stdout is not None
        for line in self.process.stdout:
            self.lines.put(line)

    def read(self, timeout_s: float) -> str:
        try:
            return self.lines.get(timeout=timeout_s).strip()
        except queue.Empty:
            raise TimeoutError(f"no line from the child within {timeout_s:.0f} s") from None

    def tell_to_exit(self) -> None:
        if self.process.stdin is not None and not self.process.stdin.closed:
            self.process.stdin.close()

    def release(self, timeout_s: float) -> int:
        """Tell it to exit, wait until it has, and return its exit code."""
        self.tell_to_exit()
        code = self.process.wait(timeout=timeout_s)
        self.pump.join(timeout_s)
        if self.process.stdout is not None and not self.pump.is_alive():
            self.process.stdout.close()
        return code


# --- steps -------------------------------------------------------------------------------------


def _failed(step: str, failure: CallFailed, **values: Value) -> StepResult:
    return StepResult(
        step, TITLES[step], FAIL, {"call": failure.call, "error": failure.error, **values}
    )


def step_a() -> StepResult:
    """Create a job as the user, and read its accounting back."""
    try:
        job = create_job(job_name("a"))
    except CallFailed as failure:
        return _failed("a", failure)
    try:
        info = accounting(job)
        return StepResult(
            "a",
            TITLES["a"],
            PASS,
            {"error": 0, "total_processes": info.TotalProcesses, "limit_flags": limit_flags(job)},
        )
    finally:
        close(job)


def step_b(timeout_s: float = DEFAULT_TIMEOUT_S) -> StepResult:
    """A child created inside a new job; the probe's own membership of any job recorded."""
    probe_in_job = in_job(current_process(), None)
    try:
        job = create_job(job_name("b"))
    except CallFailed as failure:
        return _failed("b", failure, probe_in_job=probe_in_job)
    try:
        try:
            child = create_in_jobs(busy_args(STEP_B_BUSY_MS), [job])
        except CallFailed as failure:
            return _failed("b", failure, probe_in_job=probe_in_job)
        try:
            child_in_job = in_job(child.process, job)
            exit_code = child.wait(timeout_s)
        finally:
            child.close()
        return StepResult(
            "b",
            TITLES["b"],
            PASS if child_in_job else FAIL,
            {"probe_in_job": probe_in_job, "child_in_job": child_in_job, "child_exit": exit_code},
        )
    finally:
        close(job)


def step_c(
    timeout_s: float = DEFAULT_TIMEOUT_S,
    children: int = STEP_C_CHILDREN,
    busy_ms: int = STEP_C_BUSY_MS,
) -> StepResult:
    """After every child exited: the job's CPU against the sum of the children's own."""
    job = create_job(job_name("c"))
    started: list[Child] = []
    try:
        for _ in range(children):
            started.append(create_in_jobs(busy_args(busy_ms), [job]))
        for child in started:
            child.wait(timeout_s)
        info = accounting(job)
        per_child = [sum(cpu_100ns(child.process)) for child in started]
    finally:
        for child in started:
            child.close()
        close(job)
    job_s, children_s = job_cpu_100ns(info) / 1e7, sum(per_child) / 1e7
    gap = (job_s - children_s) / children_s if children_s > 0 else math.nan
    ok = info.ActiveProcesses == 0 and abs(gap) <= TOLERANCE + 1e-9
    notes: tuple[str, ...] = ()
    if info.TotalProcesses != children:
        notes = (
            f"the job counted {info.TotalProcesses} processes for {children} children:"
            " a child started another process (an interpreter redirector?)",
        )
    return StepResult(
        "c",
        TITLES["c"],
        PASS if ok else FAIL,
        {
            "children": children,
            "busy_ms_each": busy_ms,
            "job_cpu_s": round(job_s, 7),
            "children_cpu_s": round(children_s, 7),
            "gap": f"{gap:+.3%}",
            "per_child_cpu_s": " ".join(f"{value / 1e7:.4f}" for value in per_child),
            "active_processes": info.ActiveProcesses,
            "total_processes": info.TotalProcesses,
        },
        notes,
    )


def step_d(timeout_s: float = DEFAULT_TIMEOUT_S) -> StepResult:
    """Reopen by name after the creator exits: while a holder holds a handle, then after."""
    name = job_name("d")
    creator = _Role("creator", name)
    holder: _Role | None = None
    try:
        created = creator.read(timeout_s)
        if created != "created 0":
            return StepResult("d", TITLES["d"], FAIL, {"creator": created})
        holder = _Role("holder", name)
        held = holder.read(timeout_s)
        creator_exit = creator.release(timeout_s)
        while_held = try_open(name)
        holder_exit = holder.release(timeout_s)
        after_close = try_open(name)
    finally:
        for role in (creator, holder):  # the end of stdin makes each exit on its own
            if role is not None:
                role.tell_to_exit()
    values: dict[str, Value] = {
        "job_name": name,
        "holder": held,
        "creator_exit": creator_exit,
        "holder_exit": holder_exit,
        "reopen_while_held_error": while_held,
        "reopen_after_close_error": after_close,
    }
    ok, why = reopen_as_expected(StepResult("d", TITLES["d"], RECORDED, values))
    return StepResult("d", TITLES["d"], PASS if ok else FAIL, values, (why,))


def step_e(timeout_s: float = DEFAULT_TIMEOUT_S) -> StepResult:
    """A process in a job without BREAKAWAY_OK starts a direct child with the breakaway flag."""
    job = create_job(job_name("e"))
    try:
        flags = limit_flags(job)
        with tempfile.TemporaryDirectory(prefix="submeter-probe1-e-") as folder:
            out = Path(folder) / "breakaway.txt"
            child = create_in_jobs(role_args("breakaway", str(out)), [job])
            try:
                exit_code = child.wait(timeout_s)
            finally:
                child.close()
            written = out.read_text(encoding="utf-8").strip() if out.exists() else ""
        info = accounting(job)
    finally:
        close(job)
    error: Value = int(written) if written.lstrip("-").isdigit() else None
    notes: tuple[str, ...] = ()
    if error == 0:
        notes = ("the breakaway child started: the job let it leave without BREAKAWAY_OK",)
    elif error is None:
        notes = (f"the child wrote no error code (exit code {exit_code})",)
    return StepResult(
        "e",
        TITLES["e"],
        RECORDED,
        {
            "error": error,
            "limit_flags": f"0x{flags:08x}",
            "child_exit": exit_code,
            "total_processes": info.TotalProcesses,
        },
        notes,
    )


def find_bash() -> tuple[str | None, str]:
    """Git's bash.exe (or bash on PATH), never WSL's launcher in System32; and a reason if none."""
    candidates: list[Path] = []
    on_path = shutil.which("bash")
    system_root = os.environ.get("SYSTEMROOT", r"C:\Windows")
    if on_path and not on_path.lower().startswith(system_root.lower()):
        candidates.append(Path(on_path))
    git = shutil.which("git")
    if git:
        candidates.append(Path(git).resolve().parent.parent / "bin" / "bash.exe")
    for root in (os.environ.get("PROGRAMFILES"), os.environ.get("PROGRAMW6432")):
        if root:
            candidates.append(Path(root) / "Git" / "bin" / "bash.exe")
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate), ""
    if on_path:
        return None, f"bash absent: only {shown(on_path)} (WSL's launcher) is on PATH (B16)"
    return None, "bash absent (B16)"


NODE = (
    "const r=require('child_process').spawnSync(process.env.SUBMETER_PROBE_BASH,"
    "['-c','\"$SUBMETER_PROBE_PY\" -I -S \"$SUBMETER_PROBE_SCRIPT\" --role grandchild'],"
    "{stdio:'inherit'});process.exit(r.status===null?3:r.status)"
)


def step_f(timeout_s: float = DEFAULT_TIMEOUT_S) -> StepResult:
    """BREAKAWAY_OK set: node, then bash, then a grandchild that reports its job membership."""
    node = shutil.which("node")
    bash, why = find_bash()
    if node is None:
        return StepResult("f", TITLES["f"], SKIPPED, {"reason": "node absent (B16)"})
    if bash is None:
        return StepResult("f", TITLES["f"], SKIPPED, {"reason": why})
    name = job_name("f")
    job = create_job(name)
    try:
        allow_breakaway(job)
        flags = limit_flags(job)
        with tempfile.TemporaryDirectory(prefix="submeter-probe1-f-") as folder:
            out = Path(folder) / "grandchild.txt"
            environment = {
                **os.environ,
                "SUBMETER_PROBE_BASH": bash,
                "SUBMETER_PROBE_PY": Path(CHILD_PYTHON).as_posix(),
                "SUBMETER_PROBE_SCRIPT": SCRIPT.as_posix(),
                "SUBMETER_PROBE_JOB": name,
                "SUBMETER_PROBE_OUT": str(out),
            }
            child = create_in_jobs([node, "-e", NODE], [job], environment=environment)
            try:
                node_in_job = in_job(child.process, job)
                exit_code = child.wait(timeout_s)
            finally:
                child.close()
            written = out.read_text(encoding="utf-8").strip() if out.exists() else ""
        info = accounting(job)
    finally:
        close(job)
    reported = dict(part.split("=", 1) for part in written.split() if "=" in part)
    return StepResult(
        "f",
        TITLES["f"],
        RECORDED,
        {
            "node": shown(node),
            "bash": shown(bash),
            "limit_flags": f"0x{flags:08x}",
            "node_in_job": node_in_job,
            "node_exit": exit_code,
            "grandchild_in_job": reported.get("in_job"),
            "grandchild_in_any_job": reported.get("any_job"),
            "grandchild_open_error": reported.get("open_error"),
            "total_processes": info.TotalProcesses,
            "active_processes": info.ActiveProcesses,
        },
        () if written else ("the grandchild wrote nothing: it did not run or could not write",),
    )


def spacing(values: Sequence[int]) -> dict[str, Value]:
    """How CPU values in 100-ns units sit against the 15.625 ms clock tick."""
    if not values:
        return {"values": 0}
    on_tick = sum(
        1 for v in values if min(v % TICK_100NS, TICK_100NS - v % TICK_100NS) <= TICK_SLACK_100NS
    )
    common = Counter(values).most_common(5)
    nonzero = [v for v in values if v]
    return {
        "values": len(values),
        "distinct": len(set(values)),
        "on_tick_multiples": f"{on_tick} of {len(values)} ({on_tick / len(values):.0%})",
        "gcd_ms": round(functools.reduce(math.gcd, nonzero, 0) / 1e4, 4) if nonzero else 0,
        "most_common_ms": ", ".join(f"{v / 1e4:.4f} x{n}" for v, n in common),
        "smallest_ms": round(min(values) / 1e4, 4),
        "largest_ms": round(max(values) / 1e4, 4),
    }


def step_g(
    timeout_s: float = DEFAULT_TIMEOUT_S,
    children: int = STEP_G_CHILDREN,
    busy_ms: int = STEP_G_BUSY_MS,
) -> StepResult:
    """Children one after another; the job CPU read after each, and each child's own."""
    job = create_job(job_name("g"))
    increments: list[int] = []
    per_child: list[int] = []
    try:
        before = job_cpu_100ns(accounting(job))
        for _ in range(children):
            child = create_in_jobs(busy_args(busy_ms), [job])
            try:
                child.wait(timeout_s)
                per_child.append(sum(cpu_100ns(child.process)))
            finally:
                child.close()
            now = job_cpu_100ns(accounting(job))
            increments.append(now - before)
            before = now
        info = accounting(job)
    finally:
        close(job)
    values: dict[str, Value] = {
        "children": children,
        "busy_ms_each": busy_ms,
        "job_cpu_s": round(job_cpu_100ns(info) / 1e7, 7),
        "children_cpu_s": round(sum(per_child) / 1e7, 7),
        "job_cpu_on_tick_multiple": job_cpu_100ns(info) % TICK_100NS == 0,
        "total_processes": info.TotalProcesses,
    }
    values |= {f"job_step_{key}": value for key, value in spacing(increments).items()}
    values |= {f"child_{key}": value for key, value in spacing(per_child).items()}
    return StepResult("g", TITLES["g"], RECORDED, values)


def step_h(timeout_s: float = DEFAULT_TIMEOUT_S, busy_ms: int = STEP_H_BUSY_MS) -> StepResult:
    """A burner in an inner job nested inside an outer job: both jobs' CPU and the burner's."""
    outer = create_job(job_name("h-outer"))
    inner: int | None = None
    try:
        inner = create_job(job_name("h-inner"))
        burner = create_in_jobs(busy_args(busy_ms), [outer, inner])
        try:
            in_outer, in_inner = in_job(burner.process, outer), in_job(burner.process, inner)
            burner.wait(timeout_s)
            outer_info, inner_info = accounting(outer), accounting(inner)
            burner_100ns = sum(cpu_100ns(burner.process))
        finally:
            burner.close()
    finally:
        close(inner)
        close(outer)
    values: dict[str, Value] = {
        "busy_ms": busy_ms,
        "outer_cpu_s": round(job_cpu_100ns(outer_info) / 1e7, 7),
        "inner_cpu_s": round(job_cpu_100ns(inner_info) / 1e7, 7),
        "burner_cpu_s": round(burner_100ns / 1e7, 7),
        "burner_in_outer": in_outer,
        "burner_in_inner": in_inner,
        "outer_total_processes": outer_info.TotalProcesses,
        "inner_total_processes": inner_info.TotalProcesses,
    }
    ok, why = outer_includes_burner(StepResult("h", TITLES["h"], RECORDED, values))
    return StepResult("h", TITLES["h"], PASS if ok else FAIL, values, (why,))


STEPS: dict[str, Callable[[], StepResult]] = {
    "a": step_a,
    "b": step_b,
    "c": step_c,
    "d": step_d,
    "e": step_e,
    "f": step_f,
    "g": step_g,
    "h": step_h,
}


def run_step(letter: str) -> StepResult:
    """One step; an exception becomes an error result, so the report goes on."""
    try:
        return STEPS[letter]()
    except Exception as failed:  # a probe reports what broke and carries on with the next step
        return StepResult(
            letter, TITLES[letter], ERROR, {"error": f"{type(failed).__name__}: {failed}"}
        )


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["--role"] and len(args) >= 2 and args[1] in ROLES:
        return ROLES[args[1]](*args[2:])
    if len(args) != 1 or args[0].startswith("-"):
        print("usage: job_object.py <shell name>, for example terminal, vscode or claude-code")
        return 2
    print("Probe 1, the Job Object (P0-W2-T2, gate P0.8)")
    print(f"shell: {args[0]}")
    print(f"when: {datetime.now(UTC).isoformat(timespec='seconds')}")
    print(f"system: {platform.platform()} | Python {platform.python_version()}")
    if sys.platform != "win32":
        print("unavailable: Job Objects exist only on Windows. Run this on Windows.")
        return 2
    print(f"children run: {shown(CHILD_PYTHON)} -I -S")
    probe_in_job = in_job(current_process(), None)
    print(f"probe in a job: IsProcessInJob(GetCurrentProcess(), NULL) = {probe_in_job}")
    print(flush=True)
    results: dict[str, StepResult] = {}
    for letter in STEPS:
        results[letter] = run_step(letter)
        print(describe(results[letter]), flush=True)
    decision, reason = decide(results)
    print()
    print("decision rows (P0.12)")
    print(f"B1: {decision}")
    print(f"    reason: {reason}")
    print(f"breakaway record (step f): {breakaway_record(results.get('f'))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
