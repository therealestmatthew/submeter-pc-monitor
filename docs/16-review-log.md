# Design review log

> Submeter build brief · Part 3, the build · [Index](README.md)

The design has been read three times as if by someone trying to prove its numbers wrong. The first pass found 14 flaws, the second 8, and the third, an audit of storage and time periods, 15. Thirty-four are fixed in the design and the prompt. Three cannot be fixed in version 1 and are listed under Known limits. Figures marked as estimates are reasoned, not measured, and the early phases exist to replace them with measurements.

## Index of findings

37 findings: 34 fixed and 3 accepted as limits. Findings from the first session of the build continue from R38.

| Finding | Pass | Severity | Outcome | Title |
| --- | --- | --- | --- | --- |
| R01 | First pass | critical | fixed | Polling cannot see short-lived children |
| R02 | First pass | critical | fixed | The overhead budget and the sampling rate conflict |
| R03 | First pass | critical | fixed | Raw storage would reach several gigabytes |
| R04 | First pass | critical | fixed | Command lines leak secrets, and localhost is not private |
| R05 | First pass | critical | fixed | WSL2 and Docker Desktop show up as one process |
| R06 | First pass | high | fixed | Leak detection would go blind under memory pressure |
| R07 | First pass | high | fixed | Workload totals would not add up to the system total |
| R08 | First pass | high | fixed | Sleep and variable cadence create false spikes |
| R09 | First pass | high | fixed | Two attribution rules were unreliable |
| R10 | First pass | high | fixed | Several acceptance gates could not be verified |
| R11 | First pass | medium | fixed | Detectors would fire on normal behaviour |
| R12 | First pass | medium | fixed | The bottleneck verdict claimed too much |
| R13 | First pass | medium | fixed | Hourly p95 could not be built from 1-minute p95 |
| R14 | First pass | medium | fixed | GPU and Windows counters have traps |
| R15 | Second pass | high | fixed | A tagged group's totals vanish with the group |
| R16 | Second pass | high | fixed | Per-process VRAM on Windows cannot be trusted yet |
| R17 | Second pass | medium | fixed | The bulk snapshot relies on a call Microsoft may change |
| R18 | Second pass | medium | fixed | The sample alert rule was a sentence to be parsed |
| R19 | Second pass | medium | fixed | Nothing could produce the loads the gates call for |
| R20 | Second pass | medium | fixed | A long build would lose the brief between sessions |
| R21 | Second pass | accepted limit | accepted limit | Work done on a workload's behalf is charged elsewhere |
| R22 | Second pass | accepted limit | accepted limit | A CPU-second is not a fixed amount of work |
| R23 | Third pass | critical | fixed | One database held data with three different lifetimes |
| R24 | Third pass | critical | fixed | Rollups could not reproduce totals |
| R25 | Third pass | high | fixed | The process table grew without limit |
| R26 | Third pass | high | fixed | Sessions outlived the data behind them |
| R27 | Third pass | high | fixed | Percentiles could not be combined across periods |
| R28 | Third pass | high | fixed | No process detail survived past 48 hours |
| R29 | Third pass | high | fixed | Workload names could multiply without limit |
| R30 | Third pass | high | fixed | Nothing said where files live |
| R31 | Third pass | medium | fixed | Change-only rows had no keyframes |
| R32 | Third pass | medium | fixed | Periods were not always comparable |
| R33 | Third pass | medium | fixed | No rule said which tier answers a question |
| R34 | Third pass | medium | fixed | Growth was checked at one horizon only |
| R35 | Third pass | medium | fixed | Days and weeks were undefined |
| R36 | Third pass | medium | fixed | Durability and versions were unstated |
| R37 | Third pass | accepted limit | accepted limit | Which files a process touches is not tracked |

## First pass, critical: the numbers would be wrong

### R01: Polling cannot see short-lived children

Agents spawn thousands of sub-second processes: git, ripgrep, test runners. A 1-second poll never sees most of them, so the workload you most want measured is the one most undercounted. The old gate, "50 short-lived children fully charged", was not achievable.

**Fix:** Tagged workloads run inside a Windows Job Object or a Linux cgroup. The kernel keeps exact totals for every process that ever lived in the group. Polling remains for rule-matched workloads and is labelled as such.

Amended by R151 (21 November 2026): version 1 builds the Windows Job Object path only. On Linux tagged runs are unavailable, `submeter run` runs the command polled, and the cgroup path comes after version 1.

### R02: The overhead budget and the sampling rate conflict

Reading 300 processes one at a time every second in Python likely costs 3 to 6% of a core on Windows (estimate), against a 1% budget. USS is worse, since its cost grows with each process's memory.

**Fix:** One bulk system call returns every process's counters at once. Processes are split into a hot set at 1 s and a cold set at 10 s. USS is read slowly and only for the largest processes. The budget is now 1% at idle and 3% when active, and cadence yields before the budget does.

### R03: Raw storage would reach several gigabytes

300 processes at 1 s for 48 hours is 51.8 million rows before indexes. The first draft set retention by age only, with no ceiling on disk.

**Fix:** Workload totals are stored at full resolution. Per-process rows are written only when a value changes beyond a threshold. A disk budget, 2 GB by default, is enforced by trimming the oldest raw data first.

### R04: Command lines leak secrets, and localhost is not private

Command lines often carry API keys and tokens. The draft stored them in plain text and served them from an open local port, which any web page in your browser can reach. The planned MCP server would have handed them to agents.

**Fix:** Command lines are redacted before they are written. The API needs a token and checks Host and Origin headers. The MCP server never returns command lines.

### R05: WSL2 and Docker Desktop show up as one process

On Windows, everything inside WSL2 or Docker Desktop appears as a single VM process. If agents run there, attribution collapses into one opaque block.

**Fix:** The VM is shown as its own workload, labelled opaque. The ingest API accepts a second collector, so the Linux build can run inside WSL and report to the host. That collector is phase 7.

Amended by R140 (21 November 2026): the ingest part is not in version 1. No guest collector or transport is built, the VM stays one opaque workload, and `doctor` reports its share of busy CPU time. A guest collector is designed after version 1 if that share is large.

## First pass, high: misleading under real conditions

### R06: Leak detection would go blind under memory pressure

Windows trims working sets when memory is tight, so USS falls for a leaking process at the moment the leak matters.

**Fix:** Leak detection uses private bytes on Windows and RSS plus swap on Linux. USS is kept for summing workloads.

### R07: Workload totals would not add up to the system total

Kernel time, interrupts and processes the daemon cannot read all fall outside per-process sums. A dashboard whose parts do not reach the whole invites distrust.

**Fix:** System and Restricted are explicit buckets. Attributed, unattributed, system, restricted and idle must sum to 100% within 2%, and a test enforces it.

### R08: Sleep and variable cadence create false spikes

A laptop that sleeps for an hour would show one giant sample on wake. Mixed 1 s and 5 s samples also bias simple averages.

**Fix:** Providers return cumulative counters. Rates come from deltas over a monotonic clock, gaps are recorded as gaps, and rollups are time-weighted.

### R09: Two attribution rules were unreliable

Matching on an environment tag means reading another process's memory, which fails for elevated processes. Parent IDs on Windows can point at an unrelated process after reuse.

**Fix:** The environment rule is gone. Group membership replaces it. A parent link counts only if the parent started before the child.

### R10: Several acceptance gates could not be verified

Task Manager has changed how it measures CPU between Windows builds, so it is no reference. A coding agent cannot run a 24-hour soak, and it builds on one OS.

**Fix:** Reference figures come from kernel counters. CI runs on Windows and Linux with a 30-minute soak. The 24-hour soak is yours to run. Hardware providers are tested from recorded fixtures.

## First pass, medium: noise and overconfidence

### R11: Detectors would fire on normal behaviour

A slope test flags any cache warming up. A baseline built from idle hours has near-zero spread, so all activity looks anomalous.

**Fix:** A leak needs sustained growth with no plateau. Baselines are kept separately for idle and active states, with a learning period before any anomaly is raised.

### R12: The bottleneck verdict claimed too much

The classifier always returned an answer. On Windows, hard faults include harmless file mapping.

**Fix:** Every verdict carries a confidence level, and Inconclusive is a valid result. Windows memory pressure is read from commit and page writes.

### R13: Hourly p95 could not be built from 1-minute p95

A percentile of percentiles is not a percentile.

**Fix:** Hourly rollups are computed from raw samples while those still exist.

### R14: GPU and Windows counters have traps

GPU engine percentages do not add across engine types. Windows counter names change with the display language.

**Fix:** GPU load is reported per engine type, with the busiest engine as the headline. Counters are opened by their English names.

## Second pass, fixed: gaps in the version 3 additions

### R15: A tagged group's totals vanish with the group

A Job Object is destroyed once its last process has exited and its handles are closed. A cgroup is removed once it is empty. Either way the counters go with it, and the design never said who reads the final totals.

**Fix:** The launcher holds the group while the command runs and saves its totals when the command ends. Anything that outlives the command is held open by a detached helper until the group is empty. The collector re-attaches to live groups after a restart.

### R16: Per-process VRAM on Windows cannot be trusted yet

Microsoft documents a fault in which the GPU Process Memory counter appears to leak. NVML cannot supply the figure on desktop Windows either.

**Fix:** Phase 0 compares the per-process sum with the adapter total. If they drift, the provider is marked partial and leak detection stays off per-process VRAM.

### R17: The bulk snapshot relies on a call Microsoft may change

The single system call that makes the overhead budget reachable is documented as subject to change.

**Fix:** A psutil fallback, a provider status of partial while it is in use, and a CI test that fails if the snapshot stops parsing.

### R18: The sample alert rule was a sentence to be parsed

A rule written as text needs its own small language, its own parser and its own error messages.

**Fix:** Rules are structured fields, validated like every other setting.

### R19: Nothing could produce the loads the gates call for

The gates ask for 500 sub-second children, a controlled leak and a CPU burn. No component made them.

**Fix:** A load generator ships with the tests.

### R20: A long build would lose the brief between sessions

The prompt was a single message, and a build of eight phases runs across many sessions.

**Fix:** The builder's first step is to save the brief and the standing rules in the repository.

## Second pass, accepted: limits version 1 will state

### R21: Work done on a workload's behalf is charged elsewhere

An agent that asks Docker, a shared language server or an open browser to do work is not charged for it.

**Outcome:** Process accounting cannot fix this. It is listed under Known limits and stated beside agent totals.

### R22: A CPU-second is not a fixed amount of work

Efficiency cores and reduced frequency do less with the same second, so equal CPU time is not equal work.

**Outcome:** CPU time is reported as measured, with frequency beside it. Normalising is left for a later version.

## Third pass, critical: storage that would lose or distort data

### R23: One database held data with three different lifetimes

Raw samples churn by the million each day beside history meant to last years. Deleted rows leave a file the same size, so the disk budget could not be enforced exactly, and one damaged page could cost everything.

**Fix:** Daily raw files, weekly minute files and one small history file. Retention is a file delete, and every file has one writer.

### R24: Rollups could not reproduce totals

Buckets stored means, extremes and a percentile, with no sums and no record of how much time they covered. A week's CPU-hours could only be approximated, and a gap looked like idle time.

**Fix:** Counters store sums. Every bucket stores covered seconds, sample count and active seconds.

## Third pass, high: history that would not hold up

### R25: The process table grew without limit

Every short-lived process got a permanent row with its command line, outside any retention rule. With agents that is tens of thousands of rows a day.

**Fix:** Process rows live in the raw file and expire with it. Command lines are stored once each. Nothing keyed by process ID survives 48 hours.

### R26: Sessions outlived the data behind them

After 48 hours a session's cost could only be rebuilt from coarser buckets, and its process counts and peaks were gone.

**Fix:** A session or tagged run is summarised exactly when it ends. `cost` and `diff` read the summaries.

### R27: Percentiles could not be combined across periods

The first review made the hourly p95 come from raw data, but a daily or weekly p95 still had nothing valid to be built from.

**Fix:** Buckets carry a mergeable histogram for CPU and memory. A percentile for any window comes from merged bins.

### R28: No process detail survived past 48 hours

Long-term history existed only per workload, so "what inside the browser grew last week" had no answer.

**Fix:** Each hour keeps the top ten executables per workload by CPU time and by peak memory, for a year.

### R29: Workload names could multiply without limit

A new name for every run would start a new series each time and swell every tier.

**Fix:** A stable workload name plus a per-run label. Series are kept per name and totals per run, and `doctor` warns past 200 names.

### R30: Nothing said where files live

Data, settings, logs, the API token and locks had no stated location, owner or lifetime, and two collectors could run at once.

**Fix:** A file map per platform with one override, a one-instance lock per program, rotating redacted logs, and a token file only you can read.

## Third pass, medium: comparisons that could mislead

### R31: Change-only rows had no keyframes

Writing a process only when it changes saves space, but finding its value at a given moment meant searching back without limit.

**Fix:** A full snapshot at the start of each raw file and every 10 minutes.

### R32: Periods were not always comparable

A change of sampling interval, rules, provider status or hardware could shift a series with nothing to show why.

**Fix:** Epochs. Any such change starts one and is marked on every chart, and a comparison of maxima or percentiles across an interval change is flagged.

### R33: No rule said which tier answers a question

A 7-day chart could mix raw and rolled-up data without saying so.

**Fix:** The finest tier that covers the whole window answers, and every result states its tier and resolution.

### R34: Growth was checked at one horizon only

A leak slower than 50 MB an hour was invisible however long it ran.

**Fix:** A second check fits the daily minimum over at least 7 days on the hourly tier.

### R35: Days and weeks were undefined

Daily peaks and week-over-week views had no stated time zone or daylight-saving rule.

**Fix:** Buckets are stored in UTC, and days are worked out in your time zone when you ask.

### R36: Durability and versions were unstated

Nothing said how much a crash may lose, how the write-ahead log stays small, or what happens when the three programs disagree on a schema.

**Fix:** At most 5 seconds lost and never a corrupt file, short read transactions, an integrity check at start, a daily backup of history, and a schema version in every file.

## Third pass, accepted

### R37: Which files a process touches is not tracked

Only bytes and handle counts per process are recorded.

**Outcome:** Per-file tracing needs the deep tracing left out of version 1. It is listed under Known limits.
