# What is kept, where, and for how long

> Submeter build brief · Part 2, the design · [Index](README.md)

This section is the outcome of an audit of the store and of every metric that is compared across time. The audit found 15 problems, listed as the third pass in the review log. The design below replaces the single database of earlier versions.

## Three lifetimes, three kinds of file

Data that expires together lives in a file together, so retention is always a file delete: instant, exact, and with nothing left behind to compact. Each program writes only its own files, so every file has one writer.

| File | Written by | Kept for | Holds | If it is lost |
| --- | --- | --- | --- | --- |
| `raw/2026-11-20.db` | Collector | 48 hours | One file per UTC day. Every sample at full resolution, the processes seen that day, and their scrubbed command lines stored once each | Detail for that day. Minute and hourly history survive |
| `minute/2026-W47.db` | Server | 30 days | One file per week. One bucket per workload, and one for the system, per minute | Minute detail for that week. Hourly history survives |
| `history.db` | Server | Kept | Hourly buckets, hourly summaries per executable, runs, sessions and their summaries, findings, epochs, baselines | All long-term history, which is why it is backed up daily |
| `backups/history-*.db` | Server | Last 3 | A compacted copy of the history file | Nothing, unless the history file is lost too |
| `runs/*.json` | Launcher | Until read | One small file per tagged run: its group, its label and its final totals | That run's exact totals |
| `submeter.toml`, `rules.toml` | You | Kept | Settings and attribution rules | Defaults apply until you restore them |
| `logs/*.log` | Each program | 5 files of 5 MB | Each program's own diagnostics, with the same redaction as the store | Nothing that was measured |
| `api-token`, `*.lock` | Server, each program | Until rotated | The local API token, readable only by you, and one lock per program so two copies cannot run | A new token is issued at the next start |

## Where the files live

| Kind | Windows | Linux |
| --- | --- | --- |
| Settings | `%APPDATA%\Submeter` | `~/.config/submeter` |
| Data | `%LOCALAPPDATA%\Submeter\data` | `~/.local/share/submeter` |
| Logs, token, locks | `%LOCALAPPDATA%\Submeter\state` | `~/.local/state/submeter` |
| Exports and reports | Wherever you run the command, or the folder given with `--out` | Wherever you run the command, or the folder given with `--out` |

Setting `SUBMETER_HOME` moves everything under one folder. `submeter store status` prints every file with its writer, size and coverage.

## What every bucket records

- For counters such as CPU seconds, bytes read and written, and processes started: the sum. A total over any period is then an exact sum of sums.
- For gauges such as memory, process count and frequency: minimum, maximum, time-weighted mean and last value.
- For CPU cores in use and memory: a small histogram. A percentile over any period comes from merged bins, never from averaging percentiles.
- Covered seconds and sample count, so a gap is never read as zero use.
- Active seconds, so idle and busy periods can be compared separately.
- The machine's capacity at the time and an epoch number, both explained below.

## Which data answers which question

Legend: Raw samples; Minute buckets; Hourly buckets; Stored totals.

The chart draws lookback on a logarithmic time axis marked 1 s, 1 min, 1 h, 2 d, 30 d and 1 y. Its two halves are these tables.

**KEPT**

| Tier | Resolution | Reaches back |
| --- | --- | --- |
| Raw samples | 1 s | 48 h |
| Minute buckets | 1 min | 30 d |
| Hourly buckets | 1 h | kept |
| Run, session totals | one row per run or session | kept |

**READ BY**

| Check | Reads | Looks at |
| --- | --- | --- |
| Live chart | Raw samples | the last 2 min |
| Spike check | Raw samples | the last 10 s |
| Verdict | Raw samples | the last 5 min |
| Leak check | Minute buckets | 2 to 48 h back |
| Baseline | Minute buckets | 14 d back |
| Slow growth | Hourly buckets | 7 to 90 d back |
| Trend | Hourly buckets | months back, up to 1 y on the chart |
| Cost and diff | Stored totals | any session |

*Figure:* How far back each tier reaches, on a logarithmic time axis, and which tier each check reads. Nothing needs raw samples older than 48 hours, which is what lets raw files be deleted on schedule.

- A question is answered from the finest tier that covers its whole window, and every answer states the tier and resolution it came from.
- Charts draw the minimum-to-maximum envelope, so a spike survives in coarser tiers.
- A session or tagged run is summarised when it ends, so its cost stays exact after its raw data is gone.
- Each hour keeps the top ten executables per workload by CPU time and by peak memory, for a year. That answers "what inside the browser grew last week" without keeping every process.

## Metric catalogue

| Metric | Kind | Kept per bucket | Feeds |
| --- | --- | --- | --- |
| CPU time | Counter, seconds | Sum, plus a histogram of cores in use | Cost, verdict, baseline, trend |
| Memory for growth: private bytes, or RSS plus swap | Gauge, bytes | Min, max, mean, last, histogram | Leak, slow growth, baseline |
| Memory for totals: USS or PSS | Gauge, bytes | Max, mean, age of the reading | Workload totals |
| Disk bytes read and written | Counter, bytes | Sum | Cost, I/O verdict |
| Processes alive and started | Gauge and counter | Max and mean; sum | Process-count check, cost |
| Threads and handles | Gauge | Max | Process tree view |
| GPU load by engine type | Gauge, percent | Max, mean | GPU verdict |
| VRAM | Gauge, bytes | Max, mean | GPU verdict. Leak checks only once validated |
| Connections | Gauge | Max, mean | Workload table |
| Load per core and frequency | Gauge | Min, max, mean. Per core in the raw and minute tiers, per core class hourly | CPU and thermal verdicts |
| Commit, available memory, page reads and writes | Gauges and counters | Min, max, mean; sum | Memory verdict |
| Run queue and pressure stall time | Gauge and counter | Max and mean; sum | CPU, memory and I/O verdicts |
| Disk latency and queue | Gauge | Max, mean | I/O verdict |
| Submeter's own cost | Gauge | Max, mean | Overhead guard |

## When two periods can be compared

- An epoch is a stretch of time in which the sampling intervals, the rules file, each provider's status, the hardware and the Submeter version all stayed the same. Any change starts a new epoch and is marked on every chart.
- Sums compare freely across epochs. Maxima and percentiles depend on the sampling interval, so a comparison that crosses an interval change is flagged.
- A rules change moves processes between workloads. Stored history is not rewritten. The boundary is marked.
- Percentages use the capacity recorded in each bucket, so new hardware does not distort old data.
- Buckets with less than half their time covered are left out of baselines and trends.
- Days and weeks are worked out in your time zone when you ask, from buckets stored in UTC. A day of 23 or 25 hours is compared per hour.
- A workload name is stable and reused across runs. A label marks one run. Time series are kept per name and totals per run, so a new label never starts a new series.

## Disk use after a year

| Files | Size | Basis |
| --- | --- | --- |
| Raw, 2 to 3 daily files | 0.7 to 1.1 GB | 8.1 M rows per 48 hours at 90 bytes each |
| Minute, 5 to 6 weekly files | 0.1 GB | 9 series, 1,440 buckets a day, 250 bytes each |
| History | 0.1 GB | Hourly buckets and per-executable summaries. Grows about 0.1 GB a year |
| Backups, 3 copies | 0.3 GB | Three copies of the history file |
| Logs | 0.05 GB | 2 programs, 5 files of 5 MB each |
| Total | About 1.6 GB | Of the 2 GB budget |

These sizes are estimates, and phase 1 measures the real bytes per row. When over budget the oldest raw file goes first, never below 24 hours, then backups down to one, then a finding is raised. History is never deleted automatically.

## File activity of the processes being watched

Submeter records bytes read and written, and handle counts, per process, with disk latency and queue length for the system. It does not record which files a process touches. That needs the deep tracing left out of version 1, and it is listed under Known limits.
