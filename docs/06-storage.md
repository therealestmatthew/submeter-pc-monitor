# What is kept, where, and for how long

> Submeter build brief · Part 2, the design · [Index](README.md)

This section is the outcome of an audit of the store and of every metric that is compared across time. The audit found 15 problems, listed as the third pass in the review log. The design below replaces the single database of earlier versions.

## Two lifetimes, two kinds of file

Data that expires together lives in a file together, so retention is always a file delete: exact, and with nothing left behind to compact. Each program writes only its own files, so every file has one writer.

| File | Written by | Kept for | Holds | If it is lost |
| --- | --- | --- | --- | --- |
| `raw/2026-11-20.db` | Collector | 48 hours | One file per UTC day. Every sample at full resolution, the processes seen that day, and their redacted command lines stored once each | Detail for that day. Hourly history survives |
| `history.db` | Server | Kept | Hourly buckets, hourly summaries per executable, runs, sessions and their summaries, findings, epochs | All long-term history, which is why it is backed up daily |
| `backups/history-*.db` | Server | Last 3 | A compacted copy of the history file | Nothing, unless the history file is lost too |
| `runs/*.json` | Launcher | Until the server has copied its final state into the history file. The server then deletes it | One small file per tagged run. The live state, written when the group is created, holds its group, its label, its parent run for a run started inside another tagged run, and, once the holder starts, the holder's pid and start time, so the submeter workload can claim the holder. It is replaced by atomic rename with the final state, the group's totals, once the group is empty. When the command left processes behind, the launcher's detached holder writes the final state. The collector never writes it | That run's exact totals, if the server had not yet copied them |
| `submeter.toml`, `rules.toml` | You | Kept | Settings and attribution rules | Defaults apply until you restore them |
| `logs/*.log` | Collector and server | 5 files of 5 MB | Each one's own diagnostics. They never contain command lines or working folders: a process is named by pid and executable, and validation errors leave out the values they refused | Nothing that was measured |
| `*.lock` | Collector and server | While the program runs | One lock each for the collector and the server, so two copies of either cannot run. The launcher takes no lock, because many tagged runs can be live at once. The API token file comes with the API in version 1.1 | Nothing that was measured |

The server keeps a rolled-up-until mark in the history file. At start it rolls up every raw day it holds, oldest first, before any retention pass, and it deletes a raw file only after the mark has passed that day's end. As a safety cap, the collector deletes its own raw files older than 7 days, or older than `retention.raw` if that is longer, so a stopped server cannot fill the disk. It records each such deletion as an event in its open raw file, and the server raises a finding when it next reads that file.

Retention deletes each raw file's .db with its -wal and -shm. A file's space is freed only once no program has it open: Windows refuses to delete a file that is open, and Linux keeps an open file's space until it is closed. A refused delete is retried on the next pass, and space counts as freed only when the files are gone.

## Where the files live

| Kind | Windows | Linux |
| --- | --- | --- |
| Settings | `%APPDATA%\Submeter` | `~/.config/submeter` |
| Data | `%LOCALAPPDATA%\Submeter\data` | `~/.local/share/submeter` |
| Logs, locks and control files | `%LOCALAPPDATA%\Submeter\state` | `~/.local/state/submeter` |
| Exports and reports | Wherever you run the command, or the folder given with `--out` | Wherever you run the command, or the folder given with `--out` |

Setting `SUBMETER_HOME` moves everything under one folder. `submeter store status` prints every file with its writer, size and coverage.

## Durability, access and versions

- Every data file is restricted to the current user.
- Each SQLite file runs in WAL mode with synchronous=NORMAL. A program crash loses nothing committed. A power loss or an operating-system crash may lose the samples written since the last checkpoint, up to a few minutes, and must never corrupt a file. The few minutes were measured at a 1 s interval and are to be confirmed at the shipped cadence once the collector exists.
- Read transactions are kept short so the write-ahead log can be checkpointed. `journal_size_limit` bounds the log left after a checkpoint. `submeter store status` and `doctor` report the size of each write-ahead log, and a finding is raised when one is larger than that limit.
- Every file carries a schema version, and readers accept every version still on disk.

## Table columns

[Exactly what gets built](13-build-list.md) lists the tables of each file. The raw file's columns start from the baseline's [`store/raw.py`](../src/submeter/store/raw.py). The brief adds to them the gap flag and awake seconds on each `workload_raw` and `system_raw` row, as the rules for raw files in the [build prompt](17-build-prompt.md) say, and a nullable column for every catalogue metric version 1 collects, as [Metric catalogue](#metric-catalogue) below says. The history file's columns are not written yet. The first task of phase 3, with one owner, writes the DDL of every history table here, before the server writes the file or anything reads it, so that the server's writers, the analysis and the CLI are built against one definition. A `rollup_1h` row maps to one `Bucket` record from `core.models`.

## How commands reach the programs

Commands reach the running programs only through files, which each program polls each tick, except that `submeter daemon stop` may ask the service manager instead. There is no control port and Submeter sends no signal, because Windows has no signal that asks a process to exit cleanly. Control files live under the state folder. Run files stay in the data folder.

| File | Written by | Read by | What it does |
| --- | --- | --- | --- |
| `control/stop-collector`, `control/stop-server` | `submeter daemon stop` (or the service manager instead), and `submeter config reload` before it starts the programs again | That program | Asks it to exit cleanly. The program removes the file as it exits |
| `control/sessions/<id>.json` | `submeter session start` and `stop`, with an atomic rename | The server | Marks a session's start and stop |
| `control/backup` | `submeter store backup` | The server | Asks it to back up the history file now. The server writes the copy into `backups/`, then removes the file, so it stays the only writer of backups |
| `runs/<id>.json` | The launcher | The collector while live, the server once final | Names a tagged group, then holds its final totals, as the table of files above says |
| `event` rows in the open raw file | The collector | The server, and the collector when it starts | Reports a change in a provider's status and a wall-clock step the collector detects, each of which starts an epoch; the overhead guard lengthening the intervals and a raw file the collector deleted under its 7-day cap, each of which becomes a finding; and each change of a process's workload after an exec, which the collector reads back to seed attribution when it starts |

## What every bucket records

- For counters such as CPU seconds, bytes read and written, and processes started: the sum. A total over any period is then an exact sum of sums.
- For gauges such as memory, process count and frequency: minimum, maximum, time-weighted mean and last value.
- For CPU cores in use and memory: a small histogram. A percentile over any period comes from merged bins, never from averaging percentiles.
- Covered seconds and sample count, so a gap is never read as zero use. A gap sample goes whole into the bucket that holds its end. It adds its CPU, I/O and processes started to the sums, and nothing to covered seconds, the sample count, active seconds, the memory mean or the histograms, so a bucket can hold sums with no covered seconds at all.
- Awake seconds: how far the clock that stops during suspend moved. CPU and I/O rates, and capacity in core-seconds, are worked out over awake seconds, because a gap keeps the CPU of a stall in which the machine was awake. Covered seconds remain the observed time on which the memory mean, the histograms and the rule below for buckets less than half covered rest.
- Active seconds, so idle and busy periods can be compared separately.
- The machine's capacity at the time, with CPU capacity in core-seconds, the shortest and longest sampling interval it contains, and an epoch number, all explained below.

A sample belongs, whole, to the bucket that holds its end time. A bucket covers [start, start + width), the same half-open split that puts each sample in its day file, so no bucket needs two day files. A read of raw samples for a window, and a query that merges raw samples into wider steps, use the same rule. The per-executable part of a session or run summary is closed 60 seconds after the session or run ends, because a quiet process's CPU can be held that long before its row is written.

Rollups are idempotent: recomputing a bucket gives the same row. A bucket is final 30 seconds after it ends.

## Which data answers which question

Legend: Raw samples; Hourly buckets; Stored totals.

The chart draws lookback on a logarithmic time axis marked 1 s, 1 min, 1 h, 2 d, 30 d and 1 y. Its two halves are these tables.

**KEPT**

| Tier | Resolution | Reaches back |
| --- | --- | --- |
| Raw samples | 2 s by default | 48 h |
| Hourly buckets | 1 h | kept |
| Run, session totals | one row per run or session | kept |

**READ BY**

| Check | Reads | Looks at |
| --- | --- | --- |
| Report charts | Raw samples while they cover the range, else hourly buckets | the session or range asked for |
| Verdict | Raw samples | the last 5 min |
| Leak check | Raw workload rows, merged into 1-minute steps | from 48 h back, or from the oldest raw data on disk if that is later, to now. Nothing is judged until the data spans 2 h (`leak.min_duration`) |
| Trend | Hourly buckets | months back, up to 1 y on the chart |
| Cost and diff | Stored totals, and for a run not yet copied into the history file, its run file | any session or run |

*Figure:* How far back each tier reaches, on a logarithmic time axis, and which tier each check reads. Nothing needs raw samples older than 48 hours, which is what lets raw files be deleted on schedule.

- A question is answered from raw samples, merged to wider steps, while the raw files still on disk cover the start of its window, and otherwise from hourly buckets. Coverage is taken from the oldest raw file left and its first tick, not from the retention setting, because the disk budget can delete raw days sooner. Every answer states the tier and resolution it came from.
- Charts draw the minimum-to-maximum envelope, so a spike survives in wider steps.
- A session's or tagged run's totals accumulate while it runs: as each raw tick is written, the server adds it to an open summary row in the history file, and closes the row when the session stops or the run ends. Nothing is recomputed from raw at the end, so its cost stays exact however long it ran and after its raw data is gone. After a restart the server catches up from the raw data still on disk; a summary whose raw data was deleted before that is marked incomplete. For a tagged run, CPU, I/O and process counts still come from the kernel at the end.
- A session that is never stopped, for example because the machine crashed or restarted, is closed at its last covered sample and summarised then. Sessions may overlap.
- Each hour keeps the top ten executables per workload by CPU time and by peak memory, for a year. That answers "what inside the browser grew last week" without keeping every process.

## Metric catalogue

| Metric | Kind | Kept per bucket | Feeds |
| --- | --- | --- | --- |
| CPU time | Counter, seconds | Sum, plus a histogram of cores in use | Cost, verdict, trend |
| Memory for growth: private bytes, or RSS plus swap | Gauge, bytes | Min, max, mean, last, histogram | Leak |
| Memory for totals: USS or PSS, read for the largest processes only, so a workload's total is partial when some of its processes have no reading. After version 1, a Linux tagged group uses `memory.stat` anon plus swap, the cgroup figure comparable with USS | Gauge, bytes | Max, mean, age of the reading | Workload totals |
| Disk bytes read and written | Counter, bytes | Sum | Cost, I/O verdict |
| Processes alive and started | Gauge and counter | Max and mean; sum | Process-count check, cost |
| Threads and handles | Gauge | Max | Process tree view |
| GPU load by engine type | Gauge, percent | Max, mean | GPU verdict |
| VRAM used and total, per adapter | Gauge, bytes | Max, mean | GPU verdict |
| Load per core and frequency | Gauge | Min, max, mean. Per core in raw samples, per core class hourly | CPU and thermal verdicts |
| Commit, available memory, page reads and writes | Gauges and counters | Min, max, mean; sum | Memory verdict |
| Run queue, and on Linux after version 1 pressure stall time (PSI) | Gauge and counter | Max and mean; sum | CPU, memory and I/O verdicts |
| Disk latency and queue | Gauge | Max, mean | I/O verdict |
| Submeter's own cost | Gauge | Max, mean | Overhead guard |

A workload's figure for a metric is the sum over its processes that gave a reading. If all of them did, it is a full sum. If only some did, the figure is marked partial, with the count of processes missing it. If none did, it is unavailable, shown as n/a and never as 0. The mark is kept for each figure, so the workload's accounting source still names the path that measured its CPU time.

From their first schema version, the raw and history tables hold a nullable column for every catalogue metric version 1 collects, where NULL means unavailable. Every file carries a schema version, and readers accept every version still on disk. When the collector opens a day's raw file and finds a different schema version, it starts a new file for the rest of the day, under a name the file map parses and expires, and leaves the old file as it is.

## When two periods can be compared

- An epoch is a stretch of time with one set of sampling settings, one rules file, one status for each provider, the same hardware and the same Submeter version. A new epoch starts when the configured sampling settings, the rules file, a provider's status, the hardware or the Submeter version differ. It is marked on every chart. A wall-clock step that the collector detects also starts a new epoch. Cadence the collector changes itself, switching between the active and idle intervals or the overhead guard lengthening them, does not start one, and neither does an edit to alert, UI or verdict settings. Settings and rules change only at a restart, which starts an epoch only if something in this list differs; a provider's status and the hardware can change while the programs run.
- Sums compare freely across epochs. Maxima and percentiles depend on the sampling interval, and each bucket records the shortest and longest interval it contains, so a comparison of maxima or percentiles across different intervals is flagged, within an epoch as well as across one.
- A rules change moves processes between workloads. Stored history is not rewritten. The boundary is marked.
- Percentages use the capacity recorded in each bucket, stored as core-seconds (awake seconds times logical cores, summed), so new hardware does not distort old data, and a bucket or a merged period that spans a change of core count keeps the right percentage.
- Buckets with less than half their time covered are left out of baselines and trends.
- Days and weeks are worked out in your time zone when you ask, from buckets stored in UTC. A day of 23 or 25 hours is compared per hour. Each reading's local day comes from the operating system's rules for your zone, so a daylight-saving change moves the day boundary on the right date. In zones not a whole number of hours from UTC, local days built from hourly buckets are approximate by up to 30 minutes.
- A workload name is stable and reused across runs. A label marks one run. Time series are kept per name and totals per run, so a new label never starts a new series.

## Disk use after a year

| Files | Size | Basis |
| --- | --- | --- |
| Raw, 2 to 3 daily files | 0.7 to 1.1 GB | 8.1 M rows per 48 hours at 90 bytes each, from the earlier model of a 1 s active interval with hot and cold sets, kept until the collector's rows and bytes per tick are measured |
| History | 0.1 GB | Hourly buckets and per-executable summaries. A bucket stores only the filled bins of its histograms, about 300 bytes, so each series (one workload, or the system) adds about 2.6 MB a year: about 0.13 GB a year at 50 series and 0.53 GB at 200. The 0.1 GB is the earlier estimate of a year's growth |
| Backups, 3 copies | 0.3 GB | Three copies of the history file |
| Logs | 0.05 GB | 2 programs, 5 files of 5 MB each |
| Total | About 1.5 GB | Of the 2 GB budget |

These sizes are estimates, and phase 2 measures the real bytes per row. When over budget the oldest raw file goes first, never below 24 hours, then backups down to one, then a finding is raised. History is never deleted automatically. The server enforces the budget, so it is not enforced while the server is down. The collector does not enforce it: its cap bounds the raw files to about 7 days, or to `retention.raw` if that is longer.

## File activity of the processes being watched

Submeter records bytes read and written, and handle counts, per process, with disk latency and queue length for the system. It does not record which files a process touches. That needs the deep tracing left out of version 1, and it is listed under Known limits.
