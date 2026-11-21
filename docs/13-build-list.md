# Exactly what gets built

> Submeter build brief · Part 3, the build · [Index](README.md)

Three programs that share only files on disk: a collector, a server and the launcher. Together they are 25 components, 18 tables across three kinds of data file, 13 commands and 13 API routes. Each program writes only its own files, and none imports another. Twelve of the 25 components are already started as tested code under [Baseline modules](14-baseline-modules.md). Each of those carries a baseline tag that links to its module.

## Components

| Component | What it does | Phase |
| --- | --- | --- |
| 01 `core.models` | Frozen Pydantic models for counters, samples, buckets, workloads, findings [baseline](../src/submeter/core/models.py) | P0 |
| 02 `core.config` | Loads, validates and hot-reloads submeter.toml. Tracks where each value came from [baseline](../src/submeter/core/config.py) | P0 |
| 03 `providers.base` | Provider protocol and capability report [baseline](../src/submeter/providers/base.py) | P0 |
| 04 `providers.windows.bulk` | One system-wide process snapshot per tick, with a psutil fallback | P1 |
| 05 `providers.linux.procfs` | Direct /proc reader, plus PSI. Not in version 1: Linux runs polled through the psutil provider | After v1 |
| 06 `providers.system` | Per-core load, frequency, commit, paging, disk latency, run queue, on Windows. On Linux, version 1 has only psutil's per-core load and available memory; the Linux counters come after version 1 | P1 |
| 07 `collector.sampler` | Hot and cold sets, adaptive cadence, deltas, gap detection, overhead guard [baseline](../src/submeter/collector/sampler.py) | P1 |
| 08 `store.files` | The file map, one-instance locks, schema versions, integrity checks, backups, the disk budget [baseline](../src/submeter/store/files.py) | P1 |
| 09 `store.raw` | Daily raw files: batched writes, change-only rows with keyframes, command lines stored once [baseline](../src/submeter/store/raw.py) | P1 |
| 10 `store.rollup` | Minute and hourly buckets with sums, coverage and histograms. Summaries per executable, session and run [baseline](../src/submeter/store/rollup.py) | P1 on |
| 11 `store.query` | Picks the tier for a window, merges histograms, states the resolution used [baseline](../src/submeter/store/query.py) | P1 |
| 12 `cli` | All commands, each with JSON output [baseline](../src/submeter/cli.py) | P1 on |
| 13 `launcher` | `submeter run`: starts a tree inside a Job Object, returns the command's exit code, and writes one run file with the final totals. On Linux it reports that tagged runs are unavailable and runs the command polled; the cgroup path comes after version 1 | P2 |
| 14 `providers.group` | Reads Job Object totals for each live group and re-attaches after a restart. cgroup totals come after version 1 | P2 |
| 15 `attribution` | Rule engine, inheritance, the four fixed buckets, reconciliation check [baseline](../src/submeter/attribution/rules.py) | P2 |
| 16 `privacy.redact` | Scrubs command lines before anything is written, logs included [baseline](../src/submeter/privacy/redact.py) | P2 |
| 17 `analysis.detectors` | Leak, slow growth, baseline anomaly, spike, swap storm, process count [baseline](../src/submeter/analysis/growth.py) | P3 |
| 18 `analysis.verdict` | Bottleneck classifier with confidence and evidence | P3 |
| 19 `analysis.diff` | Session and period comparison, with epoch checks | P3 |
| 20 `server.api` | HTTP and WebSocket API, read-only apart from session markers, with token, Host and Origin checks | P4 |
| 21 `web` | Dashboard: live, workloads, history, findings, compare, settings | P4 |
| 22 `alerts` | Rule evaluation, cooldowns, dashboard and desktop delivery | P4 |
| 23 `providers.extended` | GPU load and VRAM, throttling and battery, connections per process | P5 |
| 24 `report` | Self-contained HTML report for a session or range | P6 |
| 25 `mcp` | Read-only MCP server: cost, findings, verdict | P6 |

## Tables, by file

- Raw file, one per day: `meta`, `event`, `command`, `process`, `workload_raw`, `process_raw`, `system_raw`, `gap`
- Minute file, one per week: `meta`, `rollup_1m`
- History file: `meta`, `workload`, `epoch`, `rollup_1h`, `exe_1h`, `run`, `session`, `session_summary`, `finding`, `baseline`

## Alongside the code

- CI on Windows and Linux runners with a 30-minute soak. The Linux runner runs the portable tests
- Recorded fixtures for every provider and detector
- A load generator: short-lived children, a controlled leak, a CPU burn
- Default `submeter.toml` and `rules.toml`
- Windows scheduled task
- The brief under `docs/`, `AGENTS.md` with `CLAUDE.md`, and `docs/STATUS.md`
- Capability matrix written in phase 0

## Commands

- `daemon start | stop | status | install | uninstall`
- `run --as NAME [--label L] -- COMMAND`
- `top` live workload view
- `why` bottleneck verdict
- `cost` cost per workload, session or run
- `diff A B` compare two sessions or periods
- `session start | stop | list`
- `report` self-contained HTML
- `export` Parquet or JSON
- `config show | check | reload | rotate-token`
- `rules test` which rule claims a process
- `store status | check | backup`
- `doctor` what this machine can measure

## API routes

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
- `POST /sessions` the only write
- `WS /live`

## Not in version 1

- Acting on processes: priority, affinity, suspend, kill, memory caps
- Anything that needs administrator rights: per-process network bytes, a temperature sensor bridge
- Sending anything off the machine, alerts included
- Deep tracing through ETW and eBPF, which per-file tracking would need
- One dashboard across several machines
- Normalising CPU time by core type or frequency
- A collector inside WSL2 or Docker Desktop: no transport from the guest to the host is designed. The VM shows as one opaque workload, and `doctor` reports its share of busy CPU time
- The Linux platform layer: cgroup tagged runs, the direct /proc reader, PSI and the other Linux system counters, and the systemd user unit. Version 1 builds the platform layer for Windows only, where the builds run, because a second design doubles every platform phase and its gates could be checked only on a CI runner. Linux runs polled through psutil and is tested in CI
