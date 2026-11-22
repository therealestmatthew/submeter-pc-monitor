# The build prompt

> Submeter build brief · Part 3, the build · [Index](README.md)

The whole specification in one prompt, with all three review passes, the storage design, the configuration design, the build list, the four settled decisions and the baseline modules folded in. It can start a single-session build on its own. In the starter package it serves as the specification in compact form, and the execution prompt under [How to start](../README.md) replaces its working instructions.

> **Status in this package.** Work starts from [`prompts/01-execution-prompt.md`](../prompts/01-execution-prompt.md), which replaces the working instructions under "How to work" in the prompt that follows. Everything before that heading is the specification in compact form. The phases and gates under it are the starting point for the formal plan, not a script to follow.

---

# Build Submeter: a per-workload PC performance monitor

## What this is and why

I run many AI coding agents and heavy desktop apps at the same time, and I can't tell which of them is costing me what. I want a monitor I trust enough to make decisions from. It has three jobs, all served from one data set. When something has to be cut, they rank in this order, attribution highest:

1. Attribution: what does each workload (an agent run, a browser, an IDE, a build) cost in CPU, memory, I/O and GPU?
2. Live diagnosis: why is the machine slow right now?
3. Trends: how does behaviour drift over days and weeks, and where are the leaks and regressions?

Build it as a long-running local service with a CLI and a self-contained HTML report. A live web dashboard, and the local API it needs, come in version 1.1. Windows 11 is the target of version 1, and only Windows gets the platform layer: kernel accounting, the launcher and its holder, system counters and autostart. Linux must work from the same codebase, polled: there `submeter run` reports that tagged runs are unavailable and runs the command polled, and CI on a Linux runner runs the portable tests. Put everything OS-specific behind provider interfaces from the first commit, so the Linux platform layer can be added after version 1.

Version 1 only observes. It must never change a process's priority or affinity, suspend it, or kill it. Placing a process tree that Submeter itself launches into a Job Object or cgroup for accounting is allowed. Setting any limit on that group is not. A control layer will come later, so shape analysis output as plain data objects a future policy engine could consume.

## Priorities

When goals conflict, resolve them in this order:

1. Never show a wrong number. When a metric is unavailable, record it as unavailable. Never substitute zero or an estimate. Every figure shown to me should be traceable to how it was measured.
2. Stay inside the overhead budget.
3. Cover more metrics.
4. Add features.

## Stack and conventions

- Python 3.13 or newer for everything in version 1, managed with uv. From 3.13, `time.monotonic()` on Windows uses QueryPerformanceCounter, at 1 microsecond, instead of a clock that steps in 15.6 ms, which would put about 6% of error on a 250 ms interval. Ruff for lint and format. mypy in strict mode. pytest with pytest-asyncio.
- Pydantic v2 for all config, sample and finding models, with extra="forbid" and frozen=True.
- SQLite in WAL mode. Typer for the CLI.
- Report: `submeter report` writes one self-contained HTML file, with its script and data inline and a meta Content Security Policy, so no Node toolchain is needed. Draw its charts with a canvas chart library such as uPlot.
- psutil is the fallback and the cross-check on Windows, not the hot path there. On Linux in version 1 it is the process reader, and the overhead guard lengthens the intervals.
- Store timestamps in UTC. Measure intervals on a monotonic clock that keeps counting during suspend: CLOCK_BOOTTIME on Linux, and on Windows QueryPerformanceCounter, which `time.monotonic()` uses from Python 3.13.
- Before using any OS API you are not certain about, check current documentation instead of relying on memory. This applies most to Job Objects, cgroup v2 delegation, Windows performance counters, NVML, and psutil, whose API has changed across major versions.

## Architecture

Five layers with data flowing one way: providers, sampler, attribution, store, analysis. The CLI and the report are thin readers over store and analysis. Each layer must be testable in isolation from recorded fixtures.

### Three programs, one contract

Three programs share nothing but files on disk, and each writes only its own:

- submeter-collector: providers, sampler, attribution, redaction. It writes the raw files and nothing else.
- submeter-server: rollups, retention, analysis, alerts. It writes the history file, and reads the raw files, the session marker files and the final run files, deleting each run file once it has copied it into the history file.
- the launcher, `submeter run`: starts a tagged process tree and writes one small run file for it.

`submeter session start` and `stop` write the session marker files, which the server reads. None of the three programs writes them.

None of the three imports another, and every file has exactly one writer. The reason is that the collector is the hot path, and I want to be able to replace it with a Rust binary later without touching anything else. In phase 0, measure one full sample. If it takes more than 10 ms at 300 processes, or the collector holds more than 80 MB, stop and tell me, because that is my trigger for the Rust collector.

### Collection: two accounting paths

Agents spawn thousands of processes that live for less than a second, and polling cannot see them. If children live 300 ms on average, a 1-second poll captures under a third of their CPU time. So use two paths, and label every workload with the one that measured it.

Kernel accounting, for tagged workloads. `submeter run --as NAME [--label LABEL] -- COMMAND` launches the command inside a named Windows Job Object (nested jobs), and records the group in a run file. The launcher sets SUBMETER_RUN in the command's environment to the id of the run, so an agent inside it can read its own run's cost with `submeter cost --run "$SUBMETER_RUN" --json`. NAME is a stable workload name that is reused across runs, such as agent:refactor. LABEL identifies one run. Time series are kept per name and totals per run, so a new label never starts a new series. Warn in `doctor` when there are more than 200 distinct workload names. The kernel's totals for the group are authoritative: CPU time, memory, I/O and process counts, including processes that have already exited.

A group's counters disappear when the group does, so:

- The launcher writes the run file when it creates the group, in the live state. It holds the group open while the command runs and passes the command's exit code through. When the group is empty, the launcher, or its detached holder below, replaces the run file by atomic rename with the final state, which holds the group's totals. A tagged run is therefore accounted for even if the collector was not running.
- `submeter run` must return when the command returns, even if the command left background processes behind. Those processes stay in the group, so something has to keep the group open until it is empty and then save the final totals: a small detached holder, which is the launcher's own detached part. It writes the final state by atomic rename only after the launcher's last write, so the run file keeps one writer. The collector never writes a run file.
- The collector finds live groups from the run files in the live state and reads their totals each tick. After a restart it re-attaches to every live group.
- Set no limits on the group. Do not allow breakaway and do not set kill-on-close.

Linux tagged runs (after version 1). Version 1 builds kernel accounting on Windows only. On Linux, `submeter run` reports that tagged runs are unavailable and runs the command polled, so its workload is labelled polled. The design kept for later: the launcher starts the command inside a cgroup v2 and records the group in the run file. `cpu.stat` is always readable, and the memory and io files only where those controllers are delegated. The holder, final-totals and re-attach rules above apply to the cgroup in the same way.

Bulk polling, for everything else. Do not walk processes one at a time on the hot path. Every tick, read the cumulative CPU and I/O counters and the memory gauges of every process. Read the costly fields on a slower cadence: USS or PSS at the USS interval, for the largest processes only; the working folder only when a rule uses it, at the USS interval; and the command line as each system's passage below says. The default active interval of 2 s fits the overhead budget only with a direct reader, such as the Windows bulk snapshot. With psutil the overhead guard lengthens the interval. Polled workloads are labelled as polled, with a note that short-lived children may be undercounted.

On Windows, take one system-wide process snapshot per tick that returns CPU times, memory counters, I/O counters, thread and handle counts for every process. Microsoft documents that call as subject to change, so fall back to psutil if it fails, report the provider as partial while the fallback is in use, and keep a CI test that fails loudly if the snapshot stops parsing. Read a process's command line once, when it is first seen, because a Windows process cannot start running a different program. Exclude pid 0, the System Idle Process, whose CPU time is the machine's idle time. Pid 4 (System) and the Registry, MemCompression and Secure System processes belong to System, not to any workload.

On Linux, version 1 polls through the psutil provider, and the direct /proc reader comes after version 1. psutil measured about 95 ms per tick, store writes included, at 300 processes on Linux, so there the overhead guard holds the active interval at about 3.2 s or longer and the idle interval at about 9.5 s or longer. Read command lines again at the USS interval, because a process can exec another program, or rewrite its title, under the same pid and start time. Recover reaped children's CPU time and I/O from the counters of the process that reaps them, without counting a child twice. Read each process's child time (cutime plus cstime) and credit its increase to that process. Its `/proc/<pid>/io` counters already include the I/O of every child it has reaped. When a child that polling saw is reaped, subtract the child's last-seen CPU time and child time, and its last-seen I/O counters, from the next increase of the process that reaped it: the child's last-seen parent, or the subreaper if that parent has ended. Keep a zombie in the snapshot while its /proc entry exists, because its CPU time is still readable; a zombie counted there must not be counted again from its parent's child-time counters after it is reaped. Tie the subtraction to the reaping, not to the child's last sighting, so an exited child must stay in the snapshot until it is reaped. This recovers descendants reaped inside the tree, and charges orphans to the subreaper's workload. Never recover more CPU time in an interval than busy time less the CPU time already credited. The children it cannot recover are listed under Known limits. Test it with a fixture of nested reaping, through the psutil provider.

Rules for both paths:

- Providers return cumulative counters. The sampler computes rates from deltas, so a change of cadence never loses or invents CPU time. Every sample records the interval it covers. A counter a provider cannot read is None, never a stand-in zero, and a provider never writes a stand-in start time. When either reading of a process's CPU time is None, the sampler has no baseline and credits that process no CPU for the interval, as for an older process seen for the first time. Cap every per-process CPU delta at the interval times the logical cores, and count the capped samples.
- Detect suspend and resume. Suspend is the growth of a clock that counts sleep over one that does not: CLOCK_BOOTTIME minus CLOCK_MONOTONIC on Linux, QueryPerformanceCounter minus QueryUnbiasedInterruptTime on Windows. Neither needs administrator rights. Read the clock that stops during suspend only for this test and for awake seconds, never to time an interval, because on Windows it is accurate only to a system clock tick, up to 15.625 ms. A tick is also a gap, a stall, when its interval is longer than three times the interval the collector meant to wait plus 2 s of slack; no fixed length makes a gap, because the settings with the battery multiplier allow intervals up to 600 s, and the overhead guard lengthens intervals. Record a gap. A gap keeps its CPU and I/O deltas: the counters are cumulative, so the deltas are exact, and a suspended process accrues nothing. The gap flag controls only how the interval's time is counted, so a gap never shows as one giant sample.
- Stamp each batch with the wall time read at an anchor plus the time elapsed since on the interval clock, so a suspend never makes a stamp lag, and stamps never go backwards. When the wall clock departs from the stamp by more than the 2 s slack and the suspend test does not fire, the wall clock was stepped: record a 'clock stepped' event, which starts an epoch, not a gap, so the interval keeps its CPU and its coverage. After a step forward, re-anchor. The rule after a step back, and for slow drift between the two clocks, is an open question for the owner: re-anchoring would move stamps backwards, and keeping the anchor leaves them ahead of the wall clock for the rest of the run.
- Identify a process by pid plus start time. The start time in a process identity is the platform's integer stamp: on Linux, field 22 of /proc/PID/stat (ticks since boot) with /proc/sys/kernel/random/boot_id; on Windows, CreateTime as a FILETIME integer. On Linux the psutil provider reads field 22 itself, because psutil gives only a wall-clock float worked out from the boot time, which moves when the clock is stepped. Convert to wall time only for display. Compare start times, and test whether a process was born in an interval, on the boot clock. Treat a parent link as valid only if the parent started before the child. Windows CreateTime is the system time at creation, so there a wall-clock step back can still put a child before its parent; the step is recorded as an event, as above, and Known limits says so.
- A process whose command line or owner cannot be read, the inputs that decide its workload, is counted in a Restricted bucket with whatever is visible. It is never dropped. A workload figure that only some of its processes can give is a partial sum, marked with the count of processes missing it, and one that none of them can give is unavailable, never zero. A process whose start time cannot be read has no identity, because a pid alone never identifies a process, so it appears only in a per-snapshot count of unreadable processes, which `doctor` and the reconciliation show beside Restricted. A failure reading one process never costs the whole snapshot: a failed optional read, of I/O, the command line or the working folder, leaves that field unavailable, and a process that fails to read at all is counted as above. psutil keeps one object per pid between calls, so when a pid it still lists is reported gone, the object may belong to an earlier process that held the pid: the psutil provider reads that pid again through a fresh object in the same tick, or the process that took the pid is missed for two ticks and then credited no CPU for them.
- WSL2 and Docker Desktop appear on Windows as a single VM process. Show it as its own workload labelled opaque, and report its share of busy CPU time, and of capacity, in `doctor`. A collector inside the guest is not in version 1.

Memory: collect units that can be added across processes. Workload totals use USS (or PSS on Linux) so shared pages are not counted twice. USS is expensive, so read it on a slow cadence and only for the largest processes, and show the age of the reading. For growth and leak detection use private bytes on Windows and RSS plus swap on Linux, because Windows trims working sets under pressure and USS then falls for a process that is still leaking.

System-wide, on Windows: per-core load and frequency, commit and available memory, paging split into reads and writes, disk latency, run queue and the on-battery flag. Detect throttling from processor frequency and performance counters. Do not use psutil for frequency on Windows, where it reports only a nominal value. On Linux, version 1 reads only per-core load, available memory and the on-battery flag, through psutil. PSI and the other Linux system counters come after version 1. A CPU-second is not a fixed amount of work, because efficiency cores and reduced frequency do less with it. Report CPU time as measured and show processor frequency beside it. Do not normalise workload figures in version 1.

Extended providers, each declaring its capability at the current privilege level (full, partial with what is missing, or unavailable with why). Version 1 has two:

- GPU load per process. On Windows use the GPU Engine counters. Engine percentages do not add across engine types, so report per engine type and use the busiest as the headline. Open counters by their English names so a localised Windows does not break them. On Linux use NVML and sysfs.
- VRAM per adapter, used and total. The GPU-bound verdict reads it to rule itself out when VRAM is full.

Other extended providers (after version 1). No job's acceptance check or verdict reads them, so version 1 does not build them. The design kept for later:

- VRAM per process. On Windows the GPU Process Memory counter is the only per-process source, because NVML reports the figure as unavailable under the desktop driver model. Microsoft documents a fault in which that counter over-reports. Before it is used, compare the sum of per-process values with the adapter total over time. If they drift, mark the provider partial and keep leak detection off per-process VRAM.
- Temperatures and battery level. Temperatures through hwmon on Linux. Windows has no dependable unprivileged temperature source. Battery level on both.
- Network per process. Connection counts and remote endpoints per process, and bytes per interface. Per-process byte counts need administrator rights.

### Attribution

Every process maps to exactly one workload, in this order: kernel group membership, then rules, then inheritance from a valid parent, then Unattributed.

- Rules live in rules.toml and match on executable, command-line pattern, parent chain or working directory, with explicit priority. Do not match on environment variables, because reading another process's environment is unreliable.
- A tagged workload reports its group's kernel totals for CPU time, I/O and process count, not the sum of its polled processes. That sum is kept only as a cross-check and for the process tree.
- System (kernel, interrupts), Restricted, Unattributed and Submeter itself are always-visible workloads.
- Reconciliation invariant: for any window, attributed plus unattributed plus system plus restricted plus idle CPU time equals total capacity within 2%. Test it, and show it in the UI and in `submeter why`.

### Store

Data that expires together lives in a file together, so retention is always a file delete. Each file is SQLite in WAL mode with one writer.

- Raw files, one per UTC day, written by the collector: every sample at full resolution, the processes seen that day, and their redacted command lines stored once each. Kept 48 hours.
- One history file, written by the server and kept: hourly buckets, hourly summaries per workload and executable, runs, sessions and their summaries, findings and epochs.
- Run files, one small JSON file per tagged run, written by the launcher with an atomic rename: live when the group is created, and final, with the group's totals, once the group is empty. The collector reads the live ones. The server copies each final run file into the history file's run table and then deletes it. `submeter cost --run` reads the run table and any run file not yet copied.
- Session marker files, one small file per session, written by `submeter session start` and `stop` with an atomic rename and read by the server. They replace an API call, because version 1 has no API.

Rules for raw files:

- Workload totals are written every sample, and each workload and system row carries its batch's gap flag and awake seconds. Per-process rows are written only when a value changes beyond a threshold, plus a full snapshot of every live process at the start of each file and every 10 minutes, so no query looks back further than that.
- A closed day's file is never written again and never migrated, even when the wall clock steps back across midnight. Open closed files only for the length of a query, so they can be deleted on Windows.
- Process rows live only in raw files. Nothing keyed by pid is kept beyond 48 hours.

What every hourly bucket records:

- for counters (CPU seconds, bytes read and written, processes started): the sum;
- for gauges (memory, process count, GPU load, frequency, run queue): minimum, maximum, time-weighted mean and last value;
- for CPU cores in use and for memory: a fixed-bin histogram that can be merged, so a percentile over any period comes from merged bins and never from averaging percentiles;
- covered seconds, sample count and active seconds, so a gap is never read as zero use. A gap sample goes whole into the bucket that holds its end, adds its CPU, I/O and processes started to the sums, and adds nothing to covered seconds, the sample count, active seconds, the memory mean or the histograms. A bucket with no covered seconds is valid, and closing or merging one must not divide by zero;
- awake seconds, the growth of the clock that stops during suspend. CPU and I/O rates and capacity in core-seconds are worked out over awake seconds, so a stall's CPU, which its gap keeps, never raises a rate above capacity. Covered seconds stay the observed time for the memory mean, the histograms and the coverage rule under Queries;
- the capacity at the time (logical cores, memory) and an epoch id.

Build hourly buckets from raw data while it still exists. Rollups are idempotent: recomputing a bucket gives the same row. A bucket is final 30 seconds after it ends.

Summaries that must outlive the raw data:

- When a session stops or a tagged run ends, store its exact totals per workload: CPU seconds, peak and mean memory, I/O, processes started and top executables. `cost` and `diff` read these.
- Each hour, store the top 10 executables per workload by CPU time and by peak memory, keyed by executable name and never by pid. Keep these one year.

Epochs. An epoch is a stretch of time in which the sampling intervals, the rules file, each provider's status, the hardware and the Submeter version all stayed the same. Any change starts a new epoch with a stated reason. A wall-clock step that the collector detects also starts a new epoch. The collector records such events in the raw file and the server turns them into epochs. Never rewrite stored history when rules change.

Queries. Answer from raw samples, merged to wider steps, while they cover the start of the window, and otherwise from hourly buckets. Return the tier and resolution with every result. Charts draw the minimum-to-maximum envelope. Leave buckets with less than half their time covered out of baselines and trends. Work out days and weeks in my time zone at query time, from buckets stored in UTC.

Operations:

- Put files in the platform's standard per-user locations for settings, data and state, with SUBMETER_HOME overriding all of them. `submeter store status` prints every file with its writer, size and coverage.
- One-instance lock per program. Rotating logs, 5 files of 5 MB each, with the same redaction as the store.
- Durability: synchronous=NORMAL. A crash or power loss may lose up to 5 seconds of samples and must never corrupt a file. Keep read transactions short so the write-ahead log can be checkpointed, and truncate it at each checkpoint.
- At start, run an integrity check on the history file. Quarantine a damaged raw file, record a gap and carry on.
- Back up the history file daily with SQLite's online backup and keep 3 copies. Migrate it only after a backup. Every file carries a schema version, and readers accept the current and previous versions.
- Enforce the disk budget, default 2 GB, across all files. When over budget, delete the oldest raw file first, never going below 24 hours, then backups down to one, then raise a finding. Never delete history automatically.
- Export to JSON and CSV.

### Privacy and local security

Command lines often contain keys and tokens. Redact them before they are written: keep the executable and a pattern-scrubbed argument list, with a configurable redaction list and a strict mode that stores the executable only. Restrict every data file to the current user.

Version 1 opens no network port: the CLI reads the store files directly, and the API with its token comes in version 1.1. `submeter cost --json` and the report must never contain command lines or working directories. Nothing leaves the machine. Version 1 has no webhook, upload or update check. Both programs run as the signed-in user and never request administrator rights.

### Analysis

Detectors emit findings: type, severity, confidence, workload, time window, and the evidence that triggered them.

- Leak: sustained growth by a robust slope such as Theil-Sen, over a minimum duration, with no plateau. Growth that levels off is a warm-up and must be cleared. Track growth at workload level too, so a leak that spans short-lived processes is still seen. With default settings, growth of 50 MB an hour must be flagged within two hours. Run this check on raw workload rows, merged on read into 1-minute steps of time-weighted means, over up to 48 hours or the raw data on disk, whichever is shorter.
- Bottleneck verdict for a window: CPU-bound, memory-bound, I/O-bound, GPU-bound, thermally throttled or inconclusive. Always include a confidence level and the evidence. Inconclusive is a correct answer when signals disagree. On Windows judge memory pressure from commit and page writes, not from hard faults alone.
- Runaway process count.
- Session diff: compare two sessions or periods and rank what changed. Read the stored summaries, and flag any comparison of maxima or percentiles that crosses a change of sampling interval.

Each detector needs a fixture that triggers it and at least one quiet fixture that must not, including a cache warm-up for the leak detector.

Slow growth and baseline anomaly (after version 1). Version 1 has neither, and has no spike or swap-storm check. Regressions are found by hand with `submeter diff` and the hourly history. The design kept for later:

- Slow growth: on the hourly tier, fit the daily minimum of memory over at least 7 days. This catches leaks too slow for the leak check.
- Baseline anomaly: keep baselines separately for idle and active states, using median and MAD with a floor on spread, computed from hourly buckets over a trailing 14 days. Raise nothing until a learning period has enough samples. Hold the baseline still while an anomaly is open, so a regression does not become the new normal. The history file's `baseline` table is added by a migration with this feature.

## Configuration

Settings live in submeter.toml and attribution rules in rules.toml. Both load into frozen Pydantic models with unknown keys rejected. Precedence: command-line flag, environment variable, file, built-in default. Durations and sizes are written as strings such as "1s", "48h", "2GB".

Sampling settings and defaults:

- mode = adaptive (or fixed)
- active_interval = 2s (allowed 250ms to 10s)
- idle_interval = 5s (1s to 60s)
- idle_after = 60s
- uss_interval = 30s, uss_top_n = 25
- gpu_interval = 2s
- on_battery_multiplier = 2
- overhead_limit: idle 1%, active 3%

Other settings: storage (retention for raw and executables, disk_budget, change_threshold, keyframe_interval 10m, backups to keep), analysis (leak min_duration 2h and min_slope 50MB/h), verdict (window 5m, per-signal thresholds, min_confidence), alerts (rules, cooldown 15m), attribution (rules_file, inherit_from_parent, unattributed_alert, max_workload_names 200), privacy (redaction scrub or exe_only, extra patterns) and providers (enabled list).

Alert rules are structured fields: a workload pattern, a metric, above or below, a value, a duration and a severity. Do not invent a rule language to parse. An alert rule may name only these metric ids: cpu_cores, memory_bytes, processes and io_bytes_per_s for any workload, commit_fraction and throttled for the reserved workload `machine`, and overhead_fraction for the workload `submeter`. Refuse any other. Three rules ship built in: commit_fraction above 0.90 for 2 minutes (serious), throttled for 5 minutes (warning), and overhead_fraction above 0.03 for 5 minutes (warning).

Behaviour:

- Reject out-of-range values with the allowed range in the error. Never clamp silently.
- Settings and rules are read when a program starts, and never while it runs. `submeter config reload` restarts the collector and server: it stops them as `daemon stop` does and starts them as `daemon start` does, which on Windows runs the scheduled task.
- `submeter config show --effective` prints every value with its source. `submeter config check FILE` validates without applying.
- A restart starts a new epoch only if something that defines an epoch (see Epochs under Store) has changed. The epoch is marked on the charts, so a shift in the data can be traced to a settings change.
- The overhead guard outranks the configured interval. If the limit is exceeded, lengthen intervals and raise a finding.

Not configurable: observe-only behaviour, running without administrator rights, sending nothing off the machine, the rule that `submeter cost --json` and the report never contain command lines, and the rule that unavailable metrics are never estimated.

## Interfaces

CLI, where every command accepts --json with a stable schema:

- `submeter daemon start|stop|status|install|uninstall`, installing a Windows scheduled task at logon (a systemd user unit for Linux comes after version 1)
- `submeter run --as NAME [--label LABEL] -- COMMAND`
- `submeter top`, `submeter why`, `submeter cost`, `submeter diff A B`
- `submeter findings` to list findings, newest first
- `submeter session start|stop|list`, where start and stop write the session's marker file
- `submeter report` for a self-contained HTML report, which holds version 1's charts for a session or range
- `submeter export` to JSON or CSV
- `submeter config show|check|reload`, where reload restarts the collector and server
- `submeter store status|check|backup`
- `submeter rules test` to show which rule claims a given process
- `submeter doctor` for the capability matrix, restricted-process count, disk usage and the collector's own cost

`submeter why` must answer in under two seconds.

Alerts have thresholds and cooldowns. A firing alert rule raises a finding, which `submeter findings`, `submeter why` and the report show. Desktop notifications come after version 1.

Agents get their cost from the CLI: an agent started with `submeter run` reads its own run's cost with `submeter cost --run "$SUBMETER_RUN" --json`. An MCP server is not in version 1.

## The API and dashboard (version 1.1)

Not in version 1. The design is kept here for version 1.1:

- Stack: FastAPI for the local API, with a WebSocket for live data. The dashboard is a static front end served by the server process, with no Node toolchain needed to run it, and uses the report's canvas chart library.
- Security: binding to 127.0.0.1 is not enough, because any web page in my browser can reach a local port. Require a token on every HTTP and WebSocket request, reject requests whose Host is not a loopback name, and check Origin on the WebSocket. The API token lives in a file only the current user can read, and `submeter config rotate-token` replaces it. Loopback binding and the token requirement are not configurable.
- API, all under /api/v1 and read-only: health, capabilities, config, epochs, workloads, workloads/{id}/processes, series, verdict, findings, diff, sessions, and a WebSocket at /live. Every series response names the tier and resolution it came from.
- Dashboard views: live overview with the verdict, load per core, a chart by workload that switches between CPU and memory, and the reconciliation bar; a workload table that shows each workload's accounting source and drills down to its process tree; a historical explorer across retention tiers with settings changes marked; a findings feed; session compare.
- Settings: api (port) and ui (units, default_range). Version 1 accepts them and does not use them.
- Gate: requests without a token or with a foreign Origin are refused, and a 30-day range loads in under one second and names the tier it came from.

## Known limits to show, not hide

Version 1 cannot measure some things. Say so in the CLI output, in the report and in `doctor`, beside the numbers they affect, instead of leaving a gap that looks like a zero:

- Work done for a workload by another process, such as the Docker daemon, a shared language server or a browser that was already open, is charged to that other process.
- Polled workloads on Windows undercount short-lived children.
- On Linux, tagged runs are unavailable in version 1: `submeter run` runs the command polled. PSI and the other Linux system counters are not read either, so `why` on Linux reads Inconclusive or unavailable.
- The WSL2 and Docker Desktop VM is opaque: version 1 has no guest collector.
- Workload memory totals can lag by up to the USS interval.
- On Windows, after a wall-clock step back, a child started within the step of its parent can appear to start before it, so its parent link is refused.
- CPU time is not normalised for core type or frequency.
- Which files a process reads or writes is not recorded, only bytes and handle counts.
- Temperatures, per-process VRAM and network figures are not collected in version 1. On Windows, temperatures and per-process network bytes would also need administrator rights.

## Overhead budget

The monitor must not become the problem. With 300 processes running: under 1% of one core at idle cadence, under 3% at active cadence, and under 150 MB of memory across collector and server. If cadence and budget conflict, slow the cadence. Measure the cost of one full sample in phase 0 and tell me if these numbers are unrealistic before building on them.

## Build list

Build these components, and tell me before adding any that are not listed:

1. core.models and core.config
2. providers.base, providers.windows.bulk and providers.system (Windows counters; providers.linux.procfs and the Linux system counters come after version 1)
3. collector.sampler (every process every tick with the costly fields on a slower cadence, adaptive cadence, deltas, gap detection, overhead guard)
4. store.files, store.raw, store.rollup, store.query
5. launcher (`submeter run`) and providers.group (Job Object totals; cgroup totals come after version 1)
6. attribution and privacy.redact
7. analysis.detectors, analysis.verdict, analysis.diff
8. alerts
9. providers.extended (GPU load by engine type and the adapter's VRAM)
10. report
11. cli, covering every command above

Tables, by file:

- raw file: meta, event, command, process, workload_raw, process_raw, system_raw, gap
- history file: meta, workload, epoch, rollup_1h, exe_1h, run, session, session_summary, finding

Also deliver: CI on Windows and Linux, where the Linux runner runs the portable tests; recorded fixtures for every provider and detector; a load generator that can spawn short-lived children, leak memory at a set rate and burn CPU, because the gates below depend on it; default submeter.toml and rules.toml; a Windows scheduled task (the systemd user unit comes after version 1); and docs/STATUS.md.

## How to work

A baseline already exists in the repository: pyproject.toml and fifteen tested modules under src/submeter (core.units, core.models, core.histogram, core.config, privacy.redact, providers.base, providers.psutil_provider, collector.sampler, attribution.rules, store.files, store.raw, store.rollup, store.query, analysis.growth and cli), with tests in tests/. Read them before writing anything. Extend them instead of rewriting them, keep their interfaces unless you tell me why a change is needed, and keep the rule that imports only point downward, which tests/test_layers.py enforces. If the repository is empty, stop and tell me, because I have not added them yet.

In the starter package the brief is already in docs/, one file per topic, the standing rules are in AGENTS.md, which CLAUDE.md imports, and work starts from prompts/01-execution-prompt.md, whose plan replaces the working instructions in this section. Without the package, save this brief verbatim as docs/BRIEF.md before anything else, and create a CLAUDE.md that carries the priorities, the conventions and the not-configurable rules, so later sessions start from them. Either way, when a decision changes the design, change the document that states it in the same commit.

These are decided, so do not ask about them again: both programs run as the signed-in user and never request administrator rights, nothing is sent off the machine, and the name is Submeter.

Work in phases. Set up CI on Windows and Linux runners in phase 0, because you can only run one OS yourself. At the end of each phase run ruff, mypy strict and pytest, confirm the gate, and write a short status to docs/STATUS.md: what works, what was verified and how, and what you could not verify. Then stop and wait for me.

- Phase 0, decision probes and CI: on my Windows machine, as the signed-in standard user, run ruff, mypy strict, pytest and scripts/platform_check.py and keep their full output, and check per core whether Windows counts interrupt and DPC time inside system time. Set up CI on Windows and Linux runners for the portable tests, and get the baseline passing on both (it has only been run on Linux, so tell me what needed fixing on Windows). Write three probes that I run on my machine, each saving its output: a Job Object probe that creates a job, nests one inside another, reads the totals after every child has exited and reopens the job by name after the process that created it has exited, which decides the design of the holder; a bulk-snapshot prototype timed at my process count, which decides whether the collector stays in Python and the default intervals; and a per-user autostart probe that makes a program start at logon without administrator rights, which decides how `daemon install` installs. `doctor` grows with each provider and is not built out into the full capability matrix here. Gate: the baseline passes on both runners, each probe's output is saved, and the choice each probe decides is recorded.
- Phase 1, tagged runs: the launcher (`submeter run`) with its detached holder, the reading of a Job Object's final totals, the run file, `submeter cost --run` reading run files only (the history file does not exist yet), and the load generator. No collector or store is needed. A run file holds the kernel's CPU time, I/O and process counts and the job's peak commit; a run's mean memory and top executables come from the collector's samples, so they are unavailable until the collector (phase 2) and the server (phase 3) exist. Gate: on Windows, a tagged tree that spawns 500 sub-second children is charged within 2% of the load generator's own accounting, its final totals survive its exit, and `submeter run` returns with the command's exit code while background processes it left behind are still accounted for. An agent started with `submeter run` retrieves its own run's cost with `submeter cost --run "$SUBMETER_RUN" --json`, and the output holds no command line. On the Linux CI runner, `submeter run` reports that tagged runs are unavailable and runs the command polled.
- Phase 2, collector and raw store: the Windows bulk snapshot provider behind the existing protocol, the Windows system counters, the collector loop with adaptive cadence and the overhead guard around the existing sampler, the raw files with command lines redacted before they are written, the baseline attribution with its four fixed buckets so that reconciliation can be tested, and the full `top`. Gate: a 30-minute CI soak stays inside the budget, per-process figures agree with Windows performance counters within 5%, and totals reconcile within 2%. Killing the collector mid-write loses at most 5 seconds and corrupts nothing. Do not use Task Manager as a reference; its CPU figure has changed basis between Windows builds. I will run a 24-hour soak myself.
- Phase 3, attribution rules, history and sessions: the server, with the history file built on the existing rollup functions, the hourly rollup, retention, the disk budget, backups and the copying of final run files into the history file; the attribution rules; sessions through their marker files; the collector's reading of each live group's totals every tick, with re-attach to every live group after a restart; and the full `store status`. Gate: CPU-hours from the hourly tier match the raw sum within 0.1%. Deleting a day of raw data frees its space at once. On Windows, a restarted collector re-attaches to live groups. A session's cost must read the same before and after its raw data is deleted.
- Phase 4, analysis: the verdict and `why`, the leak check, the runaway process count, the session diff, and the alert rules, whose findings `submeter findings` lists. Gate: every detector passes its trigger and quiet fixtures, and `why` answers in under two seconds.
- Phase 5, the report and GPU load: `submeter report`, and the extended providers for GPU load and the adapter's VRAM. Hardware you do not have is tested from recorded fixtures. Say plainly which providers were never run on real hardware. Gate: `submeter report` writes one self-contained HTML file for a session or a range, with a meta Content Security Policy. Each chart names the tier and resolution it came from, and the report holds no command line. Each extended provider passes its recorded fixtures and degrades cleanly when its source is absent.

The floor of version 1, which no cut may cross: tagged runs on Windows that match the load generator's own accounting within 2% (on Linux they are unavailable in version 1); the collector and raw store with the baseline attribution, its four fixed buckets and the CPU time not seen by polling, so the parts reconcile with the whole within 2%; the verdict and `why` in under two seconds, reading Inconclusive when signals disagree, with the adapter's VRAM or a GPU-bound rule-out that does not need it; the leak check and `submeter findings`; session marker files, which need no API; unavailable metrics recorded as unavailable; the overhead budget; and redaction of command lines before anything is written.

Start with phase 0. Before writing code, tell me in a few sentences how you plan to extend the existing layout and any part of this brief or the baseline you think is wrong or underspecified. If something here conflicts with what an OS can really do, say so and propose the closest honest alternative instead of working around it quietly.
