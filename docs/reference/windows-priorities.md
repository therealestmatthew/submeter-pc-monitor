# What to check first on Windows

Everything in this package was written and run on Linux. This file lists what only a Windows computer can confirm, most urgent first, so the first session does not have to discover the order. Each item says what was done on Linux, what is still unknown, and how to find out.

Start with one command from the repository root. It runs items 2 to 6 and prints the evidence:

```
uv run python scripts/platform_check.py
```

Keep its full output in the review, whatever it says. A line that starts with FAIL is a finding. A crash is also reported as a FAIL, with the error.

## In order

| Priority | What | Unknown on Windows | Where |
| --- | --- | --- | --- |
| 1 | The baseline's own checks | Whether Ruff, mypy and the 20 tests pass at all | `uv run pytest` |
| 2 | The one-instance lock | How Windows answers the locking call | `src/submeter/store/files.py` |
| 3 | Reading processes | What a signed-in user may read, and what it costs | `src/submeter/providers/psutil_provider.py` |
| 4 | SQLite files | Deleting and closing files that Windows holds open | `src/submeter/store/raw.py` |
| 5 | Clocks and sleep | Clock resolution, and what happens across suspend | `src/submeter/collector/sampler.py` |
| 6 | File locations | Where the folders land on a managed work computer | `src/submeter/store/files.py` |
| 7 | Design claims not yet in code | Job Objects, the bulk snapshot and autostart (the phase 0 probes), GPU, thermal | `docs/09-telemetry.md`, `docs/15-phases-and-decisions.md` |
| 8 | Running a swarm of agents | Working copies, locks and line endings | `docs/reference/claude-code-notes.md` |

## 1. The baseline's own checks

- **Done on Linux:** `uv sync`, `uv run ruff check`, `uv run ruff format --check`, `uv run mypy src tests` and `uv run pytest` all pass on Python 3.13. They passed on 3.12 too, before the package required 3.13. mypy was also run with `--platform win32`, which type-checks the Windows-only branches without running them.
- **Unknown:** everything at run time. Likely trouble: a test's temporary folder that cannot be removed because a database file is still open, and path comparisons that assume forward slashes.
- **How to check:** run the five commands. Record the full output of any failure.
- **If it fails:** it is a finding for the review, not something to fix before the rulings.

## 2. The one-instance lock

This was the part most likely to be wrong, so it was redesigned before this package was built.

- **What changed:** the lock file is now only ever locked and never written. The earlier version locked the first byte and then wrote the holder's process id into the same file. On Windows a locked byte cannot be read by any other program, and truncating a file that holds a lock was untested. The process id now goes in a separate file beside the lock, `NAME.pid`.
- **Done on Linux:** two real processes were run against one lock. The second was refused and could read the holder's process id. After the holder was killed, the lock was free again. A second test replaces the Windows locking module with a stand-in and confirms the calls made: one byte, at the start of the file, without waiting, and an unlock on release.
- **Unknown:** how Windows itself answers those calls. Three things to confirm:
  1. A second process is refused while the first holds the lock.
  2. A second attempt from the same process, through a new handle, is also refused. The test `test_file_map_names_expiry_and_lock` depends on this.
  3. The lock is released when the holder is ended from Task Manager, not only when it exits cleanly.
- **How to check:** the first line of the script's output covers all three. To see it by hand, run `uv run pytest -k lock -v`.
- **If it fails:** the usual cause is that opening the file fails before locking does, which the code already treats as "held". Anything else, report with the error number.

## 3. Reading processes

- **Done on Linux:** the psutil provider reads every process, marks the ones it is refused as restricted, leaves the I/O, command-line or working-folder field empty when that read fails, returns a process whose other reads fail as a restricted record, and drops only a process that has already exited.
- **Unknown:**
  - **Private bytes.** On Windows memory is taken from the `private` field. That branch has never run. The script reports which field was used.
  - **How much is restricted.** On a work computer many processes belong to the system or to security software. If most of the machine's CPU time lands in Restricted, attribution is weaker than the brief assumes. The script prints the count. Compare it with the figure in `docs/03-cli-output.md`, which shows 14.
  - **Process CPU against busy time.** On Windows pid 0, the System Idle Process, reports the machine's idle time as its CPU time, so the provider skips it. The script sums every process's CPU time over 5 s and fails if the sum exceeds the machine's busy time by more than 5%. A failure means some process reports CPU time the machine did not spend on work, as pid 0 did before it was skipped.
  - **Cost.** The brief's rule is that one full sample of 300 processes should take under 10 ms, or the collector moves to Rust. The script times 20 snapshots, with and without working folders. psutil asks about one process at a time, so expect this provider to miss the target. That is the reason the bulk snapshot provider exists, not a defect in this one.
  - **Working folders.** They are read only when a rule matches on `cwd`. On Windows reading another process's working folder is slower and fails more often than on Linux. The second timing shows the cost.
- **How to check:** the script, then `uv run submeter top --seconds 2 --rules examples/rules.toml` to see real workloads.

## 4. SQLite files

- **Done on Linux:** a raw file is written, closed with its write-ahead log folded back in, and deleted.
- **Unknown:**
  - Windows refuses to delete a file that any program has open. Retention deletes whole expired files, so a command or a report reading an old day would block it. The script reports whether deletion is refused while a reader is open. If it is, retention needs to retry later, which the build must plan for.
  - Antivirus software can hold a new file open for a moment after it is written. Watch for errors that come and go.
- **How to check:** the "raw file on disk" line of the script.

## 5. Clocks and sleep

- **Done on Linux:** each snapshot carries two clocks: one that counts suspend, CLOCK_BOOTTIME, on which every interval is measured, and one that stops during suspend, CLOCK_MONOTONIC. The sampler treats an interval as a gap when it is longer than 30 seconds, or when the first clock ran more than 2 seconds ahead of the second. The wall clock plays no part in the test. Both paths are tested with made-up clocks.
- **Settled by Microsoft's documentation:** QueryPerformanceCounter, which `time.monotonic()` uses from Python 3.13, "returns the total number of ticks that have occurred since the Windows operating system was started, including the time when the machine was in a sleep state such as standby, hibernate, or connected standby". QueryUnbiasedInterruptTime "does not include time the system spends in sleep or hibernation". So on Windows the provider measures intervals on the first and reads the second only for the suspend test and for awake seconds. Neither needs administrator rights.
- **Unknown:**
  - The size of one step of the monotonic clock. From Python 3.13, which the package requires, `time.monotonic()` uses QueryPerformanceCounter, documented at 1 microsecond. Under 3.12 it stepped in 15.6 ms, which put about 6% of error on a 250 ms interval.
  - Whether the two clocks behave as documented across a real suspend on this computer. The provider's call to QueryUnbiasedInterruptTime has never run on Windows.
- **How to check:** the "clocks" line of the script for the first. For the second, run the sampler at a 10 s expected interval across a 60 s sleep: take a snapshot with the psutil provider, put the computer to sleep for a minute, wake it, take a second snapshot, pass both to the sampler, and print the batch's `gap` and `interval_s` and how far each clock moved. It passes when `gap` is true, `interval_s` includes the minute asleep, and the clock that stops during suspend moved only by the time the computer was awake. A gap alone does not pass it, because an interval of about 70 seconds is a gap by its length alone, whatever the clocks do.

## 6. File locations

- **Done on Linux:** the Windows paths are built and compared in a test: settings under `%APPDATA%\Submeter`, data and state under `%LOCALAPPDATA%\Submeter`.
- **Unknown:** whether those folders are writable, redirected or synced on a managed computer. Data must not land in a synced folder, because a synced database can be corrupted and would break the rule that nothing leaves the machine.
- **How to check:** the "file locations" line of the script, then look at where the two folders really are. Setting `SUBMETER_HOME` moves everything if they are unsuitable.
- **Later, in version 1.1 with the API:** the API token must be readable only by its owner. On Windows that is an access control list, not a file mode, and no code for it exists yet.

## 7. Design claims that are not yet in code

Most come from `docs/09-telemetry.md` and `docs/10-known-limits.md`. No baseline code depends on them, so they cannot fail a test today, but the plan rests on them. The first three are the probes of phase 0. [Build phases](../15-phases-and-decisions.md) lists what each probe does and the choice it decides, so the checks are not repeated here.

- **Job Objects.** The Job Object probe. It decides whether tagged workloads can be exact, which is the centre of the design.
- **The bulk process snapshot.** The bulk-snapshot probe.
- **Per-user autostart.** The autostart probe.
- **GPU.** Whether the per-process GPU engine counters and the adapter's VRAM figures are readable. Per-process VRAM, and how far its sum drifts from the adapter total, comes after version 1.
- **Thermal.** The brief says temperature is unavailable without administrator rights and that throttling can still be seen. Confirm both.
- **Network (after version 1).** The brief says connections are visible for the user's own processes only.
- **Security software.** Whether anything above is blocked, slowed or flagged on a managed computer. If a probe is flagged, stop and tell me.

## 8. Running a swarm of agents on Windows

- A working copy for each builder is a fresh checkout. Each needs its own `uv sync`, and a virtual environment that a running process holds open cannot be deleted.
- Deep folders under `.claude/worktrees/` can pass the 260-character path limit.
- The repository pins line endings to LF in `.gitattributes`. Confirm that a commit made on Windows does not show every line as changed.
- Sandboxed command execution is not available on native Windows.

## What this file does not cover

Linux needs its own pass after version 1, for the parts that exist only there: the /proc reader, cgroup accounting and pressure information. None of that code exists yet. Version 1 runs Linux polled through psutil, tested in CI.
