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
| 7 | Design claims not yet in code | Job Objects, the bulk snapshot, GPU, thermal, network | `docs/09-telemetry.md` |
| 8 | Running a swarm of agents | Working copies, locks and line endings | `docs/reference/claude-code-notes.md` |

## 1. The baseline's own checks

- **Done on Linux:** `uv sync`, `uv run ruff check`, `uv run ruff format --check`, `uv run mypy src tests` and `uv run pytest` all pass, on Python 3.12 and 3.13. mypy was also run with `--platform win32`, which type-checks the Windows-only branches without running them.
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

- **Done on Linux:** the psutil provider reads every process, marks the ones it cannot read fully as restricted, and never drops one.
- **Unknown:**
  - **Private bytes.** On Windows memory is taken from the `private` field. That branch has never run. The script reports which field was used.
  - **How much is restricted.** On a work computer many processes belong to the system or to security software. If most of the machine's CPU time lands in Restricted, attribution is weaker than the brief assumes. The script prints the count. Compare it with the figure in `docs/03-cli-output.md`, which shows 14.
  - **Cost.** The brief's rule is that one full sample of 300 processes should take under 10 ms, or the collector moves to Rust. The script times 20 snapshots, with and without working folders. psutil asks about one process at a time, so expect this provider to miss the target. That is the reason the bulk snapshot provider exists, not a defect in this one.
  - **Working folders.** They are read only when a rule matches on `cwd`. On Windows reading another process's working folder is slower and fails more often than on Linux. The second timing shows the cost.
- **How to check:** the script, then `uv run submeter top --seconds 2 --rules examples/rules.toml` to see real workloads.

## 4. SQLite files

- **Done on Linux:** a raw file is written, closed with its write-ahead log folded back in, and deleted.
- **Unknown:**
  - Windows refuses to delete a file that any program has open. Retention deletes whole expired files, so a dashboard or a command reading an old day would block it. The script reports whether deletion is refused while a reader is open. If it is, retention needs to retry later, which the build must plan for.
  - Antivirus software can hold a new file open for a moment after it is written. Watch for errors that come and go.
- **How to check:** the "raw file on disk" line of the script.

## 5. Clocks and sleep

- **Done on Linux:** the sampler treats an interval as a gap when the monotonic clock jumps by more than 30 seconds, or when the wall clock runs more than 2 seconds ahead of it. Both paths are tested with made-up clocks.
- **Unknown:**
  - The size of one step of the monotonic clock. If it is around 15 ms, intervals of 250 ms carry a few percent of error.
  - Whether the monotonic clock keeps counting while the computer sleeps. Either answer produces a gap, by a different rule, but only a real suspend proves it.
- **How to check:** the "clocks" line of the script for the first. For the second, start `uv run submeter top --seconds 60`, put the computer to sleep for a minute inside that window, and confirm the result reports no burst of CPU time.

## 6. File locations

- **Done on Linux:** the Windows paths are built and compared in a test: settings under `%APPDATA%\Submeter`, data and state under `%LOCALAPPDATA%\Submeter`.
- **Unknown:** whether those folders are writable, redirected or synced on a managed computer. Data must not land in a synced folder, because a synced database can be corrupted and would break the rule that nothing leaves the machine.
- **How to check:** the "file locations" line of the script, then look at where the two folders really are. Setting `SUBMETER_HOME` moves everything if they are unsuitable.
- **Later:** the API token must be readable only by its owner. On Windows that is an access control list, not a file mode, and no code for it exists yet.

## 7. Design claims that are not yet in code

These come from `docs/09-telemetry.md` and `docs/10-known-limits.md`. No baseline code depends on them, so they cannot fail a test today, but the plan rests on them.

- **Job Objects.** Whether this user can create one, whether nesting works when the terminal or Claude Code has already placed the process in a job, and whether accounting still includes children that have exited. This decides whether tagged workloads can be exact, which is the centre of the design.
- **The bulk process snapshot.** What it returns for other users' processes without administrator rights, and what one call costs.
- **GPU.** Whether the per-process counters are readable, and how far their sum drifts from the adapter total.
- **Thermal.** The brief says temperature is unavailable without administrator rights and that throttling can still be seen. Confirm both.
- **Network.** The brief says connections are visible for the user's own processes only.
- **WSL2 and Docker.** Whether their virtual machine uses more than 10% of CPU time here, which the brief uses to decide when a guest collector is built.
- **Security software.** Whether anything above is blocked, slowed or flagged on a managed computer. If a probe is flagged, stop and tell me.

## 8. Running a swarm of agents on Windows

- A working copy for each builder is a fresh checkout. Each needs its own `uv sync`, and a virtual environment that a running process holds open cannot be deleted.
- Deep folders under `.claude/worktrees/` can pass the 260-character path limit.
- The repository pins line endings to LF in `.gitattributes`. Confirm that a commit made on Windows does not show every line as changed.
- Sandboxed command execution is not available on native Windows.

## What this file does not cover

Linux needs its own pass later, for the parts that exist only there: the /proc reader, cgroup accounting and pressure information. None of that code exists yet.
