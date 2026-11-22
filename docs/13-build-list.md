# Exactly what gets built

> Submeter build brief · Part 3, the build · [Index](README.md)

Three programs that share only files on disk: a collector, a server and the launcher. Together they are 22 components in version 1 (component 05 comes after it), 16 tables across two kinds of data file, raw and history, plus one run file per tagged run, and 14 commands. Version 1 has no API routes; the routes below are kept for version 1.1. Each program writes only its own files, and none imports another. Twelve of the 22 components are already started as tested code under [Baseline modules](14-baseline-modules.md). Each of those carries a baseline tag that links to its module.

## Components

| Component | What it does | Phase |
| --- | --- | --- |
| 01 `core.models` | Frozen Pydantic models for counters, samples, buckets, workloads, findings [baseline](../src/submeter/core/models.py) | P0 |
| 02 `core.config` | Loads and validates submeter.toml when a program starts. Tracks where each value came from [baseline](../src/submeter/core/config.py) | P0 |
| 03 `providers.base` | Provider protocol and capability report [baseline](../src/submeter/providers/base.py) | P0 |
| 04 `providers.windows.bulk` | One system-wide process snapshot per tick, with a psutil fallback | P2 |
| 05 `providers.linux.procfs` | Direct /proc reader, plus PSI. Not in version 1: Linux runs polled through the psutil provider | After v1 |
| 06 `providers.system` | Per-core load, frequency and throttling, commit, paging, disk latency, run queue and the on-battery flag, on Windows. On Linux, version 1 has only psutil's per-core load, available memory and on-battery flag; the Linux counters come after version 1 | P2 |
| 07 `collector.sampler` | Every process every tick, with the costly fields on a slower cadence. Adaptive cadence, deltas, gap detection, overhead guard [baseline](../src/submeter/collector/sampler.py) | P2 |
| 08 `store.files` | The file map, one-instance locks, schema versions, integrity checks, backups, the disk budget [baseline](../src/submeter/store/files.py) | P1 |
| 09 `store.raw` | Daily raw files: batched writes, change-only rows with keyframes, command lines stored once [baseline](../src/submeter/store/raw.py) | P2 |
| 10 `store.rollup` | Hourly buckets with sums, coverage and histograms, built from raw samples. Summaries per executable, session and run [baseline](../src/submeter/store/rollup.py) | P3 |
| 11 `store.query` | Answers a window from raw samples merged to wider steps while they cover it, else from hourly buckets. Merges histograms and states the tier and resolution used [baseline](../src/submeter/store/query.py) | P2 on |
| 12 `cli` | All commands, each with JSON output, in a package with one module per command group. Every command reads the store files directly, not through an API [baseline](../src/submeter/cli.py) | P1 on |
| 13 `launcher` | `submeter run`: creates the command inside a Job Object (PROC_THREAD_ATTRIBUTE_JOB_LIST), so no descendant starts outside it, returns the command's exit code, and writes one run file: live when the group is created, then final, with the group's totals, once the group is empty. When the command left processes behind, the launcher's detached holder writes the final state. It sets no limits on the group, does not allow breakaway and does not set kill-on-close. On Linux it reports that tagged runs are unavailable and runs the command polled; the cgroup path comes after version 1 | P1 |
| 14 `providers.group` | Reads a Job Object's totals: the final totals the launcher writes to the run file, and each live group's totals, with re-attach after a restart. cgroup totals come after version 1 | P1, P3 |
| 15 `attribution` | Rule engine, inheritance, the four fixed buckets with the machine-level figure for CPU time not seen by polling beside them, reconciliation check [baseline](../src/submeter/attribution/rules.py) | P2 on |
| 16 `privacy.redact` | Redacts command lines before they are stored: the executable name only by default, or scrubbed arguments in the opt-in scrub mode. Logs hold no command lines at all [baseline](../src/submeter/privacy/redact.py) | P2 |
| 17 `analysis.detectors` | Leak and runaway process count [baseline](../src/submeter/analysis/growth.py) | P4 |
| 18 `analysis.verdict` | Bottleneck classifier with confidence and evidence | P4 |
| 19 `analysis.diff` | Session and period comparison, with epoch checks | P4 |
| 22 `alerts` | Rule evaluation and cooldowns. A firing rule raises a finding | P4 |
| 23 `providers.extended` | GPU load by engine type, machine-wide and per process, with the busiest as the headline, and the adapter's VRAM used and total | P5 |
| 24 `report` | Self-contained HTML report for a session or range, with a meta Content Security Policy. Version 1's charts are drawn here | P5 |
| 26 `server` | The server program, `submeter-server`: checks the history file's integrity at start, builds hourly buckets from the raw files, applies retention and the disk budget, backs up the history file, copies final run files and session marker files into the history file, turns the collector's events into epochs, and runs analysis and alerts. It writes only the history file and its backups | P3 on |

## Tables, by file

- Raw file, one per day: `meta`, `event`, `command`, `process`, `workload_raw`, `process_raw`, `system_raw`, `gap`
- History file: `meta`, `workload`, `epoch`, `rollup_1h`, `exe_1h`, `run`, `session`, `session_summary`, `finding`

The raw file's columns are defined in [`store/raw.py`](../src/submeter/store/raw.py). The first task of phase 3 writes the history file's columns as DDL in [Storage](06-storage.md#table-columns).

## Alongside the code

Each is built in the phase that first needs it: CI in P0, the load generator in P1, the fixture recorder in P2 and the synthetic store generator in P3. Each provider's and detector's recorded fixtures come with that component, and the capability matrix in `doctor` grows with each provider. The default `submeter.toml` and `rules.toml` and the brief are already in the package, and `docs/STATUS.md` is written at every gate.

- CI on Windows and Linux runners with a 30-minute soak. The Linux runner runs the portable tests
- Recorded fixtures for every provider and detector
- A load generator: short-lived children, a controlled leak, a CPU burn. It reports its own accounting, each burner's CPU seconds and its children's summed CPU time, which the P1 and P2 gates use as their reference
- Default `submeter.toml` and `rules.toml`
- A fixture recorder, which saves a provider's output on a real machine as a recorded fixture
- A synthetic store generator: raw files and a history file covering several days, written without a running collector, for the retention and disk-budget tests of P3 and the report of P5
- Windows scheduled task
- The brief under `docs/`, `AGENTS.md` with `CLAUDE.md`, and `docs/STATUS.md`
- The capability matrix in `doctor`, which grows as each provider is built
- The runtime dependencies, approved by the owner before the build: pydantic, psutil and typer, as in the baseline, with Windows API calls made through ctypes and no added package. tzdata is approved for Windows only; the owner decides whether it goes into `pyproject.toml` and `uv.lock` before the first wave or when a feature first needs named time zones. If the report draws its charts with uPlot, it is vendored in the package with its licence text. FastAPI and uvicorn, with websockets, and httpx for tests only, are approved for the API of version 1.1, and an MCP server, if one is built later, is hand-written

## Commands

- `daemon start | stop | status | install | uninstall` stop writes each program's stop file
- `run --as NAME [--label L] -- COMMAND`
- `top` live workload view
- `why` bottleneck verdict
- `cost` cost per workload, session or run
- `diff A B` compare two sessions or periods
- `findings` the findings, newest first
- `session start | stop | list` start and stop write a session marker file, which the server reads
- `report` self-contained HTML
- `export` JSON or CSV
- `config show | check | reload` reload restarts the collector and server
- `rules test` which rule claims a process
- `store status | check | backup`
- `doctor` what this machine can measure

## API routes (version 1.1)

Not in version 1, which has no API. These are kept for the dashboard in version 1.1. All are read-only, under the prefix `/api/v1`.

- `GET /health`
- `GET /capabilities`
- `GET /config`
- `GET /epochs`
- `GET /workloads`
- `GET /workloads/{id}/processes`
- `GET /series` any metric and range, with the tier used
- `GET /verdict`
- `GET /findings`
- `GET /diff`
- `GET /sessions`
- `WS /live` live data. Its message format and rate are not written yet; version 1.1 writes them before it builds the route

## Not in version 1

- Acting on processes: priority, affinity, suspend, kill, memory caps
- Anything that needs administrator rights: per-process network bytes, a temperature sensor bridge
- Sending anything off the machine, alerts included
- Deep tracing through ETW and eBPF, which per-file tracking would need
- One dashboard across several machines
- Normalising CPU time by core type or frequency
- A collector inside WSL2 or Docker Desktop: no transport from the guest to the host is designed. The VM shows as one opaque workload, and `doctor` reports its share of busy CPU time, and of capacity
- The Linux platform layer: cgroup tagged runs, the direct /proc reader, PSI and the other Linux system counters, and the systemd user unit. Version 1 builds the platform layer for Windows only, where the builds run, because a second design doubles every platform phase and its gates could be checked only on a CI runner. Linux runs polled through psutil and is tested in CI
- An MCP server (component 25, read-only cost, findings and verdict). It would add a phase, a new dependency or a hand-written server, a transport and a withholding rule, for what the CLI already gives the same agents: an agent started with `submeter run` reads its own run's cost with `submeter cost --run "$SUBMETER_RUN" --json`
- Parquet export. It needs a large new dependency, pyarrow, and no job, gate or report reads an export. JSON and CSV need only the standard library
- The HTTP API with its WebSocket and token (component 20), and the live dashboard (component 21). No job's acceptance check needs them, and they would bring version 1's only network listener, a token system and four or more new dependencies. Version 1 draws its charts in `submeter report`, lists findings with `submeter findings` and records sessions in marker files. Both come in version 1.1
- Desktop notifications. A firing alert rule raises a finding instead, which `submeter findings`, `submeter why` and the report show. Delivery would need a subprocess or a new dependency, and hosted CI, which has no user session, could not test it
- Per-process VRAM, network connections and bytes per interface, battery level and temperatures. No job's acceptance check or verdict reads them, and most would be built and tested only from recorded fixtures. Version 1 keeps the adapter's VRAM, which the GPU-bound verdict reads, and the on-battery flag, which stretches the intervals
- A minute tier. Raw samples cover the last 48 hours and hourly buckets everything older. No job's acceptance check needs 1-minute data older than 48 hours, and a third kind of file would need its own writer, retention and migrations. Windows of 34 minutes to 33 hours that start 2 to 30 days back are answered at 1-hour resolution, and per-core detail is kept for 48 hours
- Slow growth, baseline anomaly, spike and swap-storm detectors. Slow growth and baselines need weeks of real data before they can be checked, and no job's acceptance check needs any of the four. Regressions are found by hand with `submeter diff` and the hourly history. The design of slow growth and baseline anomaly is kept for later in [How it decides](07-analysis.md) and the [build prompt](17-build-prompt.md)
- Hot and cold sets, which sampled idle processes less often. Every process is read every tick, and only the costly fields wait for the USS interval. As specified, the sets either lost about a third of the CPU time and reported processes starting and exiting that had not, or showed more cores in use than the machine has
- Reloading settings while a program runs, named per-machine profiles, and a sampling interval set per session. Settings and rules are read when a program starts, and `submeter config reload` restarts the collector and server. Each would need a control channel to the running programs and epoch rules for changes made mid-run. What is lost: a change without a restart, one settings file shared across machines, and a session sampled faster than the rest, such as a 250 ms benchmark
