# What is kept, where, and for how long

> Submeter build brief · Part 2, the design · [Index](README.md)

This section is the outcome of an audit of the store and of every metric that is compared across time. The audit found 15 problems, listed as the third pass in the review log. The design below replaces the single database of earlier versions.

## Two lifetimes, two kinds of file

Data that expires together lives in a file together, so retention is always a file delete: instant, exact, and with nothing left behind to compact. Each program writes only its own files, so every file has one writer.

| File | Written by | Kept for | Holds | If it is lost |
| --- | --- | --- | --- | --- |
| `raw/2026-11-20.db` | Collector | 48 hours | One file per UTC day. Every sample at full resolution, the processes seen that day, and their scrubbed command lines stored once each | Detail for that day. Hourly history survives |
| `history.db` | Server | Kept | Hourly buckets, hourly summaries per executable, runs, sessions and their summaries, findings, epochs | All long-term history, which is why it is backed up daily |
| `backups/history-*.db` | Server | Last 3 | A compacted copy of the history file | Nothing, unless the history file is lost too |
| `runs/*.json` | Launcher | Until the server has copied its final state into the history file. The server then deletes it | One small file per tagged run: its group and its label, written live when the group is created, then replaced by atomic rename with the final state, the group's totals, once the group is empty. When the command left processes behind, the launcher's detached holder writes the final state. The collector never writes it | That run's exact totals, if the server had not yet copied them |
| `submeter.toml`, `rules.toml` | You | Kept | Settings and attribution rules | Defaults apply until you restore them |
| `logs/*.log` | Each program | 5 files of 5 MB | Each program's own diagnostics, with the same redaction as the store | Nothing that was measured |
| `*.lock` | Each program | While the program runs | One lock per program, so two copies cannot run. The API token file comes with the API in version 1.1 | Nothing that was measured |

## Where the files live

| Kind | Windows | Linux |
| --- | --- | --- |
| Settings | `%APPDATA%\Submeter` | `~/.config/submeter` |
| Data | `%LOCALAPPDATA%\Submeter\data` | `~/.local/share/submeter` |
| Logs and locks | `%LOCALAPPDATA%\Submeter\state` | `~/.local/state/submeter` |
| Exports and reports | Wherever you run the command, or the folder given with `--out` | Wherever you run the command, or the folder given with `--out` |

Setting `SUBMETER_HOME` moves everything under one folder. `submeter store status` prints every file with its writer, size and coverage.

## What every bucket records

- For counters such as CPU seconds, bytes read and written, and processes started: the sum. A total over any period is then an exact sum of sums.
- For gauges such as memory, process count and frequency: minimum, maximum, time-weighted mean and last value.
- For CPU cores in use and memory: a small histogram. A percentile over any period comes from merged bins, never from averaging percentiles.
- Covered seconds and sample count, so a gap is never read as zero use. A gap sample goes whole into the bucket that holds its end. It adds its CPU, I/O and processes started to the sums, and nothing to covered seconds, the sample count, active seconds, the memory mean or the histograms, so a bucket can hold sums with no covered seconds at all.
- Awake seconds: how far the clock that stops during suspend moved. CPU and I/O rates, and capacity in core-seconds, are worked out over awake seconds, because a gap keeps the CPU of a stall in which the machine was awake. Covered seconds remain the observed time on which the memory mean, the histograms and the rule below for buckets less than half covered rest.
- Active seconds, so idle and busy periods can be compared separately.
- The machine's capacity at the time and an epoch number, both explained below.

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
| Leak check | Raw workload rows, merged into 1-minute steps | 2 to 48 h back, or as far as the raw data on disk reaches |
| Trend | Hourly buckets | months back, up to 1 y on the chart |
| Cost and diff | Stored totals, and for a run not yet copied into the history file, its run file | any session or run |

*Figure:* How far back each tier reaches, on a logarithmic time axis, and which tier each check reads. Nothing needs raw samples older than 48 hours, which is what lets raw files be deleted on schedule.

- A question is answered from raw samples, merged to wider steps, while they cover the start of its window, and otherwise from hourly buckets. Every answer states the tier and resolution it came from.
- Charts draw the minimum-to-maximum envelope, so a spike survives in wider steps.
- A session or tagged run is summarised when it ends, so its cost stays exact after its raw data is gone.
- Each hour keeps the top ten executables per workload by CPU time and by peak memory, for a year. That answers "what inside the browser grew last week" without keeping every process.

## Metric catalogue

| Metric | Kind | Kept per bucket | Feeds |
| --- | --- | --- | --- |
| CPU time | Counter, seconds | Sum, plus a histogram of cores in use | Cost, verdict, trend |
| Memory for growth: private bytes, or RSS plus swap | Gauge, bytes | Min, max, mean, last, histogram | Leak |
| Memory for totals: USS or PSS | Gauge, bytes | Max, mean, age of the reading | Workload totals |
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

## When two periods can be compared

- An epoch is a stretch of time in which the sampling intervals, the rules file, each provider's status, the hardware and the Submeter version all stayed the same. Any change starts a new epoch and is marked on every chart. A wall-clock step that the collector detects also starts a new epoch.
- Sums compare freely across epochs. Maxima and percentiles depend on the sampling interval, so a comparison that crosses an interval change is flagged.
- A rules change moves processes between workloads. Stored history is not rewritten. The boundary is marked.
- Percentages use the capacity recorded in each bucket, so new hardware does not distort old data.
- Buckets with less than half their time covered are left out of baselines and trends.
- Days and weeks are worked out in your time zone when you ask, from buckets stored in UTC. A day of 23 or 25 hours is compared per hour.
- A workload name is stable and reused across runs. A label marks one run. Time series are kept per name and totals per run, so a new label never starts a new series.

## Disk use after a year

| Files | Size | Basis |
| --- | --- | --- |
| Raw, 2 to 3 daily files | 0.7 to 1.1 GB | 8.1 M rows per 48 hours at 90 bytes each, from the earlier model of a 1 s active interval with hot and cold sets, kept until the collector's rows and bytes per tick are measured |
| History | 0.1 GB | Hourly buckets and per-executable summaries. Grows about 0.1 GB a year |
| Backups, 3 copies | 0.3 GB | Three copies of the history file |
| Logs | 0.05 GB | 2 programs, 5 files of 5 MB each |
| Total | About 1.5 GB | Of the 2 GB budget |

These sizes are estimates, and phase 2 measures the real bytes per row. When over budget the oldest raw file goes first, never below 24 hours, then backups down to one, then a finding is raised. History is never deleted automatically.

## File activity of the processes being watched

Submeter records bytes read and written, and handle counts, per process, with disk latency and queue length for the system. It does not record which files a process touches. That needs the deep tracing left out of version 1, and it is listed under Known limits.
