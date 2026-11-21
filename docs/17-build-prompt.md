# The build prompt

> Submeter build brief · Part 3, the build · [Index](README.md)

The whole specification in one prompt, with all three review passes, the storage design, the configuration design, the build list, the four settled decisions and the baseline modules folded in. It can start a single-session build on its own. In the starter package it serves as the specification in compact form, and the execution prompt under [How to start](../README.md) replaces its working instructions.

> **Status in this package.** Work starts from [`prompts/01-execution-prompt.md`](../prompts/01-execution-prompt.md), which replaces the working instructions under "How to work" in the prompt that follows. Everything before that heading is the specification in compact form. The phases and gates under it are the starting point for the formal plan, not a script to follow.

---

# Build Submeter: a per-workload PC performance monitor

## What this is and why

I run many AI coding agents and heavy desktop apps at the same time, and I can't tell which of them is costing me what. I want a monitor I trust enough to make decisions from. It has three jobs of equal weight, all served from one data set:

1. Attribution: what does each workload (an agent run, a browser, an IDE, a build) cost in CPU, memory, I/O and GPU?
2. Live diagnosis: why is the machine slow right now?
3. Trends: how does behaviour drift over days and weeks, and where are the leaks and regressions?

Build it as a long-running local service with a web dashboard and a CLI. Windows 11 is the target of version 1, and only Windows gets the platform layer: kernel accounting, the launcher and its holder, system counters and autostart. Linux must work from the same codebase, polled: there `submeter run` reports that tagged runs are unavailable and runs the command polled, and CI on a Linux runner runs the portable tests. Put everything OS-specific behind provider interfaces from the first commit, so the Linux platform layer can be added after version 1.

Version 1 only observes. It must never change a process's priority or affinity, suspend it, or kill it. Placing a process tree that Submeter itself launches into a Job Object or cgroup for accounting is allowed. Setting any limit on that group is not. A control layer will come later, so shape analysis output as plain data objects a future policy engine could consume.

## Priorities

When goals conflict, resolve them in this order:

1. Never show a wrong number. When a metric is unavailable, record it as unavailable. Never substitute zero or an estimate. Every figure shown to me should be traceable to how it was measured.
2. Stay inside the overhead budget.
3. Cover more metrics.
4. Add features.

## Stack and conventions

- Python 3.12 or newer for everything in version 1, managed with uv. Ruff for lint and format. mypy in strict mode. pytest with pytest-asyncio.
- Pydantic v2 for all config, sample, finding and API models, with extra="forbid" and frozen=True.
- SQLite in WAL mode. FastAPI for the local API, with a WebSocket for live data. Typer for the CLI.
- Dashboard: a static front end served by the server process, with no Node toolchain needed to run it. Use a canvas chart library such as uPlot.
- psutil is the fallback and the cross-check, not the hot path.
- Store timestamps in UTC. Measure intervals on a monotonic clock.
- Before using any OS API you are not certain about, check current documentation instead of relying on memory. This applies most to Job Objects, cgroup v2 delegation, Windows performance counters, NVML, and psutil, whose API has changed across major versions.

## Architecture

Five layers with data flowing one way: providers, sampler, attribution, store, analysis. The API, CLI and dashboard are thin readers over store and analysis. Each layer must be testable in isolation from recorded fixtures.

### Three programs, one contract

Three programs share nothing but files on disk, and each writes only its own:

- submeter-collector: providers, sampler, attribution, redaction. It writes the raw files and nothing else.
- submeter-server: rollups, retention, analysis, alerts, API, dashboard, MCP. It writes the minute files and the history file, and reads the raw files.
- the launcher, `submeter run`: starts a tagged process tree and writes one small run file for it.

None of the three imports another, and every file has exactly one writer. The reason is that the collector is the hot path, and I want to be able to replace it with a Rust binary later without touching anything else. In phase 0, measure one full sample. If it takes more than 10 ms at 300 processes, or the collector holds more than 80 MB, stop and tell me, because that is my trigger for the Rust collector.

### Collection: two accounting paths

Agents spawn thousands of processes that live for less than a second, and polling cannot see them. If children live 300 ms on average, a 1-second poll captures under a third of their CPU time. So use two paths, and label every workload with the one that measured it.

Kernel accounting, for tagged workloads. `submeter run --as NAME [--label LABEL] -- COMMAND` launches the command inside a named Windows Job Object (nested jobs), and records the group in a run file. NAME is a stable workload name that is reused across runs, such as agent:refactor. LABEL identifies one run. Time series are kept per name and totals per run, so a new label never starts a new series. Warn in `doctor` when there are more than 200 distinct workload names. The kernel's totals for the group are authoritative: CPU time, memory, I/O and process counts, including processes that have already exited.

A group's counters disappear when the group does, so:

- The launcher holds the group open while the command runs, passes the command's exit code through, and writes the group's totals to its run file when the command ends. A tagged run is therefore accounted for even if the collector was not running.
- `submeter run` must return when the command returns, even if the command left background processes behind. Those processes stay in the group, so something has to keep the group open until it is empty and then save the final totals: a small detached holder, or the collector. Choose one and test it.
- The collector finds live groups from the run files and reads their totals each tick. After a restart it re-attaches to every live group.
- Set no limits on the group. Do not allow breakaway and do not set kill-on-close.

Linux tagged runs (after version 1). Version 1 builds kernel accounting on Windows only. On Linux, `submeter run` reports that tagged runs are unavailable and runs the command polled, so its workload is labelled polled. The design kept for later: the launcher starts the command inside a cgroup v2 and records the group in the run file. `cpu.stat` is always readable, and the memory and io files only where those controllers are delegated. The holder, final-totals and re-attach rules above apply to the cgroup in the same way.

Bulk polling, for everything else. Do not walk processes one at a time on the hot path. On Windows, take one system-wide process snapshot per tick that returns CPU times, memory counters, I/O counters, thread and handle counts for every process. Microsoft documents that call as subject to change, so fall back to psutil if it fails, report the provider as partial while the fallback is in use, and keep a CI test that fails loudly if the snapshot stops parsing. On Linux, version 1 polls through the psutil provider, and the direct /proc reader comes after version 1. psutil measured about 95 ms per tick, store writes included, at 300 processes on Linux, so there the overhead guard holds the active interval at about 3.2 s or longer and the idle interval at about 9.5 s or longer. Keep a hot set of recently active processes at the active interval and a cold set at the cold interval. Polled workloads are labelled as polled, with a note that short-lived children may be undercounted. On Linux, recover reaped children's CPU time from the parent's child-time counters.

Rules for both paths:

- Providers return cumulative counters. The sampler computes rates from deltas, so a change of cadence never loses or invents CPU time. Every sample records the interval it covers.
- Detect suspend and resume. Record a gap. Never emit one giant sample across it.
- Identify a process by pid plus start time. Treat a parent link as valid only if the parent started before the child.
- A process the collector cannot read is counted in a Restricted bucket with whatever is visible. It is never dropped.
- WSL2 and Docker Desktop appear on Windows as a single VM process. Show it as its own workload labelled opaque. Design the ingest path so a second collector running inside the guest can report to the host later (phase 7).

Memory: collect units that can be added across processes. Workload totals use USS (or PSS on Linux) so shared pages are not counted twice. USS is expensive, so read it on a slow cadence and only for the largest processes, and show the age of the reading. For growth and leak detection use private bytes on Windows and RSS plus swap on Linux, because Windows trims working sets under pressure and USS then falls for a process that is still leaking.

System-wide, on Windows: per-core load and frequency, commit and available memory, paging split into reads and writes, disk latency and run queue. On Linux, version 1 reads only per-core load and available memory, through psutil. PSI and the other Linux system counters come after version 1. A CPU-second is not a fixed amount of work, because efficiency cores and reduced frequency do less with it. Report CPU time as measured and show processor frequency beside it. Do not normalise workload figures in version 1.

Extended providers, each declaring its capability at the current privilege level (full, partial with what is missing, or unavailable with why):

- GPU load per process. On Windows use the GPU Engine counters. Engine percentages do not add across engine types, so report per engine type and use the busiest as the headline. Open counters by their English names so a localised Windows does not break them. On Linux use NVML and sysfs.
- VRAM per process. On Windows the GPU Process Memory counter is the only per-process source, because NVML reports the figure as unavailable under the desktop driver model. Microsoft documents a fault in which that counter over-reports. In phase 0, compare the sum of per-process values with the adapter total over time. If they drift, mark the provider partial and keep leak detection off per-process VRAM.
- Thermals and power. Temperatures through hwmon on Linux. Windows has no dependable unprivileged temperature source, so detect throttling from processor frequency and performance counters. Do not use psutil for frequency on Windows, where it reports only a nominal value. Battery on both.
- Network per process. Connection counts and remote endpoints per process, and bytes per interface. Per-process byte counts need administrator rights and are not part of version 1.

### Attribution

Every process maps to exactly one workload, in this order: kernel group membership, then rules, then inheritance from a valid parent, then Unattributed.

- Rules live in rules.toml and match on executable, command-line pattern, parent chain or working directory, with explicit priority. Do not match on environment variables, because reading another process's environment is unreliable.
- System (kernel, interrupts), Restricted, Unattributed and Submeter itself are always-visible workloads.
- Reconciliation invariant: for any window, attributed plus unattributed plus system plus restricted plus idle CPU time equals total capacity within 2%. Test it, and show it in the UI and in `submeter why`.

### Store

Data that expires together lives in a file together, so retention is always a file delete. Each file is SQLite in WAL mode with one writer.

- Raw files, one per UTC day, written by the collector: every sample at full resolution, the processes seen that day, and their redacted command lines stored once each. Kept 48 hours.
- Minute files, one per ISO week, written by the server: one bucket per minute for each workload and for the system. Kept 30 days.
- One history file, written by the server and kept: hourly buckets, hourly summaries per workload and executable, runs, sessions and their summaries, findings, epochs and baselines.
- Run files, one small JSON file per tagged run, written by the launcher with an atomic rename and read by the server.

Rules for raw files:

- Workload totals are written every sample. Per-process rows are written only when a value changes beyond a threshold, plus a full snapshot of every live process at the start of each file and every 10 minutes, so no query looks back further than that.
- A closed day's file is never written again and never migrated. Open closed files only for the length of a query, so they can be deleted on Windows.
- Process rows live only in raw files. Nothing keyed by pid is kept beyond 48 hours.

What every minute and hourly bucket records:

- for counters (CPU seconds, bytes read and written, processes started): the sum;
- for gauges (memory, process count, GPU load, frequency, run queue): minimum, maximum, time-weighted mean and last value;
- for CPU cores in use and for memory: a fixed-bin histogram that can be merged, so a percentile over any period comes from merged bins and never from averaging percentiles;
- covered seconds, sample count and active seconds, so a gap is never read as zero use;
- the capacity at the time (logical cores, memory) and an epoch id.

Build hourly buckets from raw data while it still exists. Rollups are idempotent: recomputing a bucket gives the same row. A bucket is final 30 seconds after it ends.

Summaries that must outlive the raw data:

- When a session stops or a tagged run ends, store its exact totals per workload: CPU seconds, peak and mean memory, I/O, processes started and top executables. `cost` and `diff` read these.
- Each hour, store the top 10 executables per workload by CPU time and by peak memory, keyed by executable name and never by pid. Keep these one year.

Epochs. An epoch is a stretch of time in which the sampling intervals, the rules file, each provider's status, the hardware and the Submeter version all stayed the same. Any change starts a new epoch with a stated reason. The collector records such events in the raw file and the server turns them into epochs. Never rewrite stored history when rules change.

Queries. Answer from the finest tier that covers the whole window, and return the tier and resolution with every result. Charts draw the minimum-to-maximum envelope. Leave buckets with less than half their time covered out of baselines and trends. Work out days and weeks in my time zone at query time, from buckets stored in UTC.

Operations:

- Put files in the platform's standard per-user locations for settings, data and state, with SUBMETER_HOME overriding all of them. `submeter store status` prints every file with its writer, size and coverage.
- One-instance lock per program. Rotating logs, 5 files of 5 MB each, with the same redaction as the store. The API token lives in a file only the current user can read.
- Durability: synchronous=NORMAL. A crash or power loss may lose up to 5 seconds of samples and must never corrupt a file. Keep read transactions short so the write-ahead log can be checkpointed, and truncate it at each checkpoint.
- At start, run an integrity check on the history file. Quarantine a damaged raw or minute file, record a gap and carry on.
- Back up the history file daily with SQLite's online backup and keep 3 copies. Migrate it only after a backup. Every file carries a schema version, and readers accept the current and previous versions.
- Enforce the disk budget, default 2 GB, across all files. When over budget, delete the oldest raw file first, never going below 24 hours, then backups down to one, then raise a finding. Never delete history automatically.
- Export to Parquet and JSON.

### Privacy and local security

Command lines often contain keys and tokens. Redact them before they are written: keep the executable and a pattern-scrubbed argument list, with a configurable redaction list and a strict mode that stores the executable only. Restrict every data file and the API token to the current user.

Binding to 127.0.0.1 is not enough, because any web page in my browser can reach a local port. Require a token on every HTTP and WebSocket request, reject requests whose Host is not a loopback name, and check Origin on the WebSocket. The MCP server must never return command lines or working directories. Nothing leaves the machine. Version 1 has no webhook, upload or update check. Both programs run as the signed-in user and never request administrator rights.

### Analysis

Detectors emit findings: type, severity, confidence, workload, time window, and the evidence that triggered them.

- Leak: sustained growth by a robust slope such as Theil-Sen, over a minimum duration, with no plateau. Growth that levels off is a warm-up and must be cleared. Track growth at workload level too, so a leak that spans short-lived processes is still seen. With default settings, growth of 50 MB an hour must be flagged within two hours. Run this check on the minute tier.
- Slow growth: on the hourly tier, fit the daily minimum of memory over at least 7 days. This catches leaks too slow for the check above.
- Baseline anomaly: keep baselines separately for idle and active states, using median and MAD with a floor on spread, computed from minute buckets over a trailing 14 days. Raise nothing until a learning period has enough samples. Hold the baseline still while an anomaly is open, so a regression does not become the new normal.
- Bottleneck verdict for a window: CPU-bound, memory-bound, I/O-bound, GPU-bound, thermally throttled or inconclusive. Always include a confidence level and the evidence. Inconclusive is a correct answer when signals disagree. On Windows judge memory pressure from commit and page writes, not from hard faults alone.
- Spike, swap storm, runaway process count.
- Session diff: compare two sessions or periods and rank what changed. Read the stored summaries, and flag any comparison of maxima or percentiles that crosses a change of sampling interval.

Each detector needs a fixture that triggers it and at least one quiet fixture that must not, including a cache warm-up for the leak detector.

## Configuration

Settings live in submeter.toml and attribution rules in rules.toml. Both load into frozen Pydantic models with unknown keys rejected. Precedence: command-line flag, environment variable, file, built-in default. Durations and sizes are written as strings such as "1s", "48h", "2GB".

Sampling settings and defaults:

- mode = adaptive (or fixed)
- active_interval = 1s (allowed 250ms to 10s)
- idle_interval = 5s (1s to 60s)
- cold_interval = 10s (5s to 60s)
- idle_after = 60s
- hot_cpu_threshold = 0.5%
- uss_interval = 30s, uss_top_n = 25
- gpu_interval = 2s, thermal_interval = 5s, network_interval = 5s
- on_battery_multiplier = 2
- overhead_limit: idle 1%, active 3%

Other settings: storage (retention for raw, minute and executables, disk_budget, change_threshold, keyframe_interval 10m, backups to keep), analysis (leak min_duration 2h and min_slope 50MB/h, slow_growth window 7d, baseline learning_period 7d, window 14d and sensitivity 4.0), verdict (window 5m, per-signal thresholds, min_confidence), alerts (rules, cooldown 15m, quiet_hours, channels dashboard and desktop), attribution (rules_file, inherit_from_parent, unattributed_alert, max_workload_names 200), privacy (redaction scrub or exe_only, extra patterns), providers (enabled list), api (port, mcp_enabled), ui (units, default_range), and named per-machine profiles that override any of the above.

Alert rules are structured fields: a workload pattern, a metric, above or below, a value, a duration and a severity. Do not invent a rule language to parse. An alert rule may name only these metric ids: cpu_cores, memory_bytes, processes and io_bytes_per_s for any workload, commit_fraction and throttled for the reserved workload `machine`, and overhead_fraction for the workload `submeter`. Refuse any other. Three rules ship built in: commit_fraction above 0.90 for 2 minutes (serious), throttled for 5 minutes (warning), and overhead_fraction above 0.03 for 5 minutes (warning).

Behaviour:

- Reject out-of-range values with the allowed range in the error. Never clamp silently.
- Hot reload on `submeter config reload` and on file change. Settings that need a restart must say so.
- `submeter config show --effective` prints every value with its source. `submeter config check FILE` validates without applying.
- Every effective change starts a new epoch and is marked on the charts, so a shift in the data can be traced to a settings change.
- A session may override the sampling interval for its own duration.
- The overhead guard outranks the configured interval. If the limit is exceeded, lengthen intervals and raise a finding.

Not configurable: observe-only behaviour, running without administrator rights, sending nothing off the machine, loopback binding, the token requirement, the rule that MCP never returns command lines, and the rule that unavailable metrics are never estimated.

## Interfaces

CLI, where every command accepts --json with a stable schema:

- `submeter daemon start|stop|status|install|uninstall`, installing a Windows scheduled task at logon (a systemd user unit for Linux comes after version 1)
- `submeter run --as NAME [--label LABEL] -- COMMAND`
- `submeter top`, `submeter why`, `submeter cost`, `submeter diff A B`
- `submeter session start|stop|list`
- `submeter report` for a self-contained HTML report
- `submeter export` to Parquet or JSON
- `submeter config show|check|reload|rotate-token`
- `submeter store status|check|backup`
- `submeter rules test` to show which rule claims a given process
- `submeter doctor` for the capability matrix, restricted-process count, disk usage and the collector's own cost

`submeter why` must answer in under two seconds.

Dashboard views: live overview with the verdict, load per core, a chart by workload that switches between CPU and memory, and the reconciliation bar; a workload table that shows each workload's accounting source and drills down to its process tree; a historical explorer across retention tiers with settings changes marked; a findings feed; session compare. Alerts have thresholds and cooldowns, and appear in the dashboard and as desktop notifications.

Later phases add a read-only MCP server exposing cost, findings and verdict queries.

## Known limits to show, not hide

Version 1 cannot measure some things. Say so in the dashboard and in `doctor`, beside the numbers they affect, instead of leaving a gap that looks like a zero:

- Work done for a workload by another process, such as the Docker daemon, a shared language server or a browser that was already open, is charged to that other process.
- Polled workloads on Windows undercount short-lived children.
- On Linux, tagged runs are unavailable in version 1: `submeter run` runs the command polled. PSI and the other Linux system counters are not read either, so `why` on Linux reads Inconclusive or unavailable.
- The WSL2 and Docker Desktop VM is opaque until the guest collector exists.
- Workload memory totals can lag by up to the USS interval.
- CPU time is not normalised for core type or frequency.
- Which files a process reads or writes is not recorded, only bytes and handle counts.
- Temperatures on Windows and per-process network bytes are not collected, because version 1 runs without administrator rights.

## Overhead budget

The monitor must not become the problem. With 300 processes running: under 1% of one core at idle cadence, under 3% at active cadence, and under 150 MB of memory across collector and server. If cadence and budget conflict, slow the cadence. Measure the cost of one full sample in phase 0 and tell me if these numbers are unrealistic before building on them.

## Build list

Build these components, and tell me before adding any that are not listed:

1. core.models and core.config
2. providers.base, providers.windows.bulk and providers.system (Windows counters; providers.linux.procfs and the Linux system counters come after version 1)
3. collector.sampler (hot and cold sets, adaptive cadence, deltas, gap detection, overhead guard)
4. store.files, store.raw, store.rollup, store.query
5. launcher (`submeter run`) and providers.group (Job Object totals; cgroup totals come after version 1)
6. attribution and privacy.redact
7. analysis.detectors, analysis.verdict, analysis.diff
8. server.api, web, alerts
9. providers.extended (GPU load and VRAM, throttling and battery, connections)
10. report and mcp
11. cli, covering every command above

Tables, by file:

- raw file: meta, event, command, process, workload_raw, process_raw, system_raw, gap
- minute file: meta, rollup_1m
- history file: meta, workload, epoch, rollup_1h, exe_1h, run, session, session_summary, finding, baseline

API, all under /api/v1 and read-only except session markers: health, capabilities, config, epochs, workloads, workloads/{id}/processes, series, verdict, findings, diff, sessions (GET and POST), and a WebSocket at /live. Every series response names the tier and resolution it came from.

Also deliver: CI on Windows and Linux, where the Linux runner runs the portable tests; recorded fixtures for every provider and detector; a load generator that can spawn short-lived children, leak memory at a set rate and burn CPU, because the gates below depend on it; default submeter.toml and rules.toml; a Windows scheduled task (the systemd user unit comes after version 1); and docs/STATUS.md.

## How to work

A baseline already exists in the repository: pyproject.toml and fifteen tested modules under src/submeter (core.units, core.models, core.histogram, core.config, privacy.redact, providers.base, providers.psutil_provider, collector.sampler, attribution.rules, store.files, store.raw, store.rollup, store.query, analysis.growth and cli), with tests in tests/. Read them before writing anything. Extend them instead of rewriting them, keep their interfaces unless you tell me why a change is needed, and keep the rule that imports only point downward, which tests/test_layers.py enforces. If the repository is empty, stop and tell me, because I have not added them yet.

In the starter package the brief is already in docs/, one file per topic, the standing rules are in AGENTS.md, which CLAUDE.md imports, and work starts from prompts/01-execution-prompt.md, whose plan replaces the working instructions in this section. Without the package, save this brief verbatim as docs/BRIEF.md before anything else, and create a CLAUDE.md that carries the priorities, the conventions and the not-configurable rules, so later sessions start from them. Either way, when a decision changes the design, change the document that states it in the same commit.

These are decided, so do not ask about them again: both programs run as the signed-in user and never request administrator rights, nothing is sent off the machine, and the name is Submeter. One thing is decided by measurement. In phase 0, report what share of CPU time a WSL2 or Docker Desktop VM holds over a working day. If it is above 10%, tell me, and the guest collector moves to directly after phase 2.

Work in phases. Set up CI on Windows and Linux runners in phase 0, because you can only run one OS yourself. At the end of each phase run ruff, mypy strict and pytest, confirm the gate, and write a short status to docs/STATUS.md: what works, what was verified and how, and what you could not verify. Then stop and wait for me.

- Phase 0, baseline check, capability probe and CI: get the baseline passing ruff, mypy strict and pytest on both runners (it has only been run on Linux, so tell me what needed fixing on Windows), then build `submeter doctor` out into the full capability matrix, and report the measured cost of one full sample, the per-process VRAM check, the WSL2 or Docker VM measurement, and a written matrix of what each OS delivers with and without elevation.
- Phase 1, collector, store and CLI: the Windows bulk snapshot provider behind the existing protocol, the collector loop with adaptive cadence and the overhead guard around the existing sampler, the minute and history files built on the existing rollup functions, retention and backups, and the full `top` and `store status`. Gate: a 30-minute CI soak stays inside the budget, per-process figures agree with Windows performance counters within 5%, and totals reconcile within 2%. Killing the collector mid-write loses at most 5 seconds and corrupts nothing. CPU-hours from the hourly tier match the raw sum within 0.1%. Deleting a day of raw data frees its space at once. Do not use Task Manager as a reference; its CPU figure has changed basis between Windows builds. I will run a 24-hour soak myself.
- Phase 2, kernel accounting on Windows, attribution and sessions. Gate: on Windows, a tagged tree that spawns 500 sub-second children is charged within 2% of the kernel's total, its final totals survive its exit, a restarted collector re-attaches to live groups, and `submeter run` returns with the command's exit code while background processes it left behind are still accounted for. On Linux, `submeter run` reports that tagged runs are unavailable and runs the command polled. A session's cost must read the same before and after its raw data is deleted.
- Phase 3, analysis. Gate: every detector passes its trigger and quiet fixtures, including a leak too slow for the hourly check, and `why` answers in under two seconds.
- Phase 4, API and dashboard. Gate: requests without a token or with a foreign Origin are refused, and a 30-day range loads in under one second and names the tier it came from.
- Phase 5, extended providers. Hardware you do not have is tested from recorded fixtures. Say plainly which providers were never run on real hardware.
- Phase 6, HTML reports and MCP server. Gate: no MCP response contains a command line.
- Phase 7, guest collector for WSL2.

Start with phase 0. Before writing code, tell me in a few sentences how you plan to extend the existing layout and any part of this brief or the baseline you think is wrong or underspecified. If something here conflicts with what an OS can really do, say so and propose the closest honest alternative instead of working around it quietly.
