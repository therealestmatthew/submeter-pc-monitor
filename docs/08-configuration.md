# Configuration

> Submeter build brief · Part 2, the design · [Index](README.md)

Two files: `submeter.toml` for settings and `rules.toml` for attribution rules. Both are validated on load, and unknown keys are rejected. Both are read when a program starts, so a change takes effect when `submeter config reload` restarts the collector and server. A restart that changes the sampling settings or the rules starts a new epoch, marked on the charts, so a shift in the data can be traced to the setting that caused it.

## Sample time explorer

Move the controls to see what a sampling choice costs. The figures come from a simple model with assumed costs, not from measurements. Phase 0 replaces the assumptions with real numbers.

`brief.html` holds the calculator of the v8 brief as delivered, with three sliders, one of them for the cold interval that version 1 no longer has. That page is frozen, and this section supersedes it. The model uses assumed costs, not measurements. Its inputs, formulas and results are set out here.

**Measured so far,** on Linux with the baseline code on one 8-core laptop. Windows is unmeasured until phase 0. Reading one process cost 0.025 ms from /proc stat alone and 0.052 ms from stat, statm and io, through the direct /proc reader that comes after version 1, and 0.25 ms through psutil: 2 to 21 times the assumed 0.012 ms. The Python work after the snapshot, deltas and attribution, cost about 0.033 ms per process. Raw-store writes cost about 10 ms per tick at 300 processes, which is 0.5 points of one core at a 2 s interval against the 0.2 points assumed below for the store and the server, and about 120 bytes per row.

**Inputs**

- **Active interval:** 250 ms, 500 ms, 1 s, 2 s, 5 s or 10 s. It starts at 2 s.
- **Processes running:** 100 to 1,000 in steps of 50. It starts at 300.

**Formulas**, where a is the active interval in seconds and P the number of processes

- Cost of one bulk sample, assumed: 1.5 ms plus 0.012 ms for each process.
- **Submeter overhead**, shown "of one core, limit 3% when active": the sample cost divided by a, as a percentage, plus 0.2 points for the store and the server.
- **Short-lived CPU that polling captures**, shown for "children averaging 300 ms. Tagged workloads get 100%": (0.3 ÷ a) × (1 − e^(−a ÷ 0.3)).

Raw rows and raw data on disk are not modelled. Every process is read every tick, but a process row is written only when the process changes enough or has held unwritten CPU time for 60 s, and how often that happens is not known until the collector's rows and bytes per tick are measured.

**Status line**

The status comes from the assumed costs, so it is not a budget check. The measured costs above are higher. The phase 0 measurement of the collector's whole tick, and the phase 2 and phase 3 soaks for every Submeter process, say whether a setting fits the budget.

| When | Label | Message |
| --- | --- | --- |
| Overhead above 3% | Over | Over the overhead limit. The guard would lengthen the collector's intervals until the summed overhead of every Submeter process is back under 3%. |
| Overhead above 1% | Active only | Fine while active, but above the 1% idle limit, so adaptive mode matters at this setting. |
| Otherwise | In budget | Inside the overhead budget. |

**Results**

| Active interval | Processes | Submeter overhead | Polling captures | Status |
| --- | --- | --- | --- | --- |
| 250 ms | 300 | 2.2% | 68% | Active only |
| 500 ms | 300 | 1.2% | 49% | Active only |
| 1 s | 300 | 0.7% | 29% | In budget |
| 2 s | 300 | 0.5% | 15% | In budget |
| 5 s | 300 | 0.3% | 6% | In budget |
| 10 s | 300 | 0.3% | 3% | In budget |
| 1 s | 100 | 0.5% | 29% | In budget |
| 1 s | 1000 | 1.6% | 29% | Active only |
| 250 ms | 1000 | 5.6% | 68% | Over the overhead limit |

## Sampling settings

| Setting | Default | Range | What it changes |
| --- | --- | --- | --- |
| `mode` | adaptive | adaptive, fixed | Adaptive moves between the active and idle intervals. Fixed always uses the active interval |
| `active_interval` | 2s | 250ms to 10s | How often every process is sampled while anything is busy |
| `idle_interval` | 5s | 1s to 60s | Sampling rate once the machine has been quiet |
| `idle_after` | 60s | 10s to 10m | Quiet time before dropping to the idle interval |
| `uss_interval` | 30s | 10s to 5m | How often the costly per-process readings are taken: the expensive memory reading, working folders when a rule uses them, and command lines on Linux |
| `uss_top_n` | 25 | 0 to 200 | How many of the largest processes get the expensive memory reading. A workload's memory total is the sum over its processes that have a reading, marked partial with the count of processes without one |
| `gpu_interval` | 2s | 1s to 30s | GPU load and adapter VRAM sampling |
| `thermal_interval` | 5s | 1s to 60s | Not used in version 1, which reads no temperatures or battery level. Frequency and the on-battery flag are read with the system counters. Later, temperature and battery sampling |
| `network_interval` | 5s | 1s to 60s | Not used in version 1, which reads no network figures. Later, connection counts and interface bytes |
| `on_battery_multiplier` | 2 | 1 to 10 | Stretches every interval while on battery |
| `overhead_limit` | 1% idle, 3% active | 0.5% to 10% | When exceeded, intervals lengthen and a finding is raised |

Every tick reads CPU time, I/O and memory for every process. Only the costly readings wait for the USS interval. The 2 s default active interval fits the overhead budget only with a direct reader, such as the Windows bulk snapshot. With psutil, which is the fallback on Windows and the reader on Linux in version 1, the overhead guard lengthens the intervals, as [Known limits](10-known-limits.md) states for Linux.

The expensive memory reading has a cost of its own. On Linux it costs about 25 to 30 ms of CPU per GB resident in the processes read; with the defaults that is about 0.8% of one core on a desktop with 8 GB in its 25 largest processes, most of the 1% idle budget. The overhead guard stretches `uss_interval` or shrinks `uss_top_n` before it lengthens the active and idle intervals.

The overhead budget covers every Submeter process: the collector, the server and the launcher's detached holders, which the `submeter` workload holds together. With 300 processes running, their summed CPU time stays under `overhead_limit`, 1% of one core at the idle cadence and 3% at the active cadence, and the collector and server together stay under 150 MB of memory, measured as private bytes on Windows and USS on Linux. The overhead guard acts on the collector, whose intervals are the only ones it lengthens, and `overhead_fraction` reports the total.

## Other settings worth exposing

| Group | Setting | Default | Why you would change it |
| --- | --- | --- | --- |
| Storage | `retention.raw` | 48h | Keep full detail longer for slow investigations |
| Storage | `retention.executables` | 1y | How long the hourly per-executable summaries are kept |
| Storage | `disk_budget` | 2GB | Raise on a large drive, lower on a laptop |
| Storage | `change_threshold` | 0.5 pt CPU, 8MB | How much a process must change before a row is written |
| Storage | `keyframe_interval` | 10m | How often every live process is written in full |
| Storage | `backups.keep` | 3 | Copies of the history file to keep |
| Analysis | `leak.min_duration` | 2h | Shorter catches leaks sooner and raises more false alarms |
| Analysis | `leak.min_slope` | 50MB/h | Ignore growth too slow to matter within a day |
| Analysis | `slow_growth.window` | 7d | Not used in version 1, which has no slow-growth check. Later, the daily minimums the slow-growth check fits: at least 7, which needs 8 days of hourly buckets |
| Analysis | `baseline.learning_period` | 7d | Not used in version 1, which has no baseline anomaly check. Later, the days of history before anomalies are raised |
| Analysis | `baseline.window` | 14d | Not used in version 1. Later, how far back the usual range looks |
| Analysis | `baseline.sensitivity` | 4.0 | Not used in version 1. Later, the distance from normal, in spreads, that counts as an anomaly |
| Verdict | `window` | 5m | How far back `submeter why` looks |
| Verdict | `thresholds.*` | see the verdict table in [How it decides](07-analysis.md) | Tune each signal to your hardware |
| Verdict | `min_confidence` | moderate | Below this the verdict reads Inconclusive |
| Alerts | `rules[]` | 3 built in | Your own thresholds per workload or system-wide |
| Alerts | `cooldown` | 15m | Minimum gap between repeats of the same alert |
| Alerts | `quiet_hours` | off | Not used in version 1, which has no desktop notifications. Later, it holds notifications overnight |
| Alerts | `channels` | dashboard, desktop | Not used in version 1, where every alert is a finding. Later, it says where alerts appear. Nothing is sent off the machine |
| Attribution | `rules_file` | rules.toml | Where workload rules live |
| Attribution | `inherit_from_parent` | true | Turn off to see helper processes on their own. A rule's `include_children` overrides it, in either direction, for the processes that rule matches |
| Attribution | `unattributed_alert` | 10% CPU | Tells you when a rule is missing |
| Attribution | `max_workload_names` | 200 | `doctor` warns when names multiply past this |
| Privacy | `redaction` | scrub | Set to `exe_only` to store no arguments at all |
| Privacy | `redact_patterns[]` | built-in list | Add your own secret formats |
| Providers | `enabled[]` | all | Switch off anything you do not need |
| API and UI | `port, mcp_enabled` | 8787, false | Not used in version 1, which has no API or MCP server. In version 1.1, `port` moves the API |
| API and UI | `units, default_range` | GiB, 1h | Not used in version 1. In version 1.1, how the dashboard opens |

## How configuration behaves

- Precedence is command-line flag, then environment variable, then file, then built-in default.
- `submeter config show --effective` prints every value and where it came from.
- `submeter config check` validates a file without applying it.
- Out-of-range values are refused with the allowed range in the message. They are never silently clamped.
- Sizes are binary, in settings and in the acceptance checks: 1 MB is 1024 × 1024 bytes and 1 GB is 1024 cubed bytes, so `50MB/h` is 50 MiB an hour.
- Any change to sampling, rules or providers starts a new epoch, which is marked on every chart. A wall-clock step that the collector detects also starts a new epoch.
- Settings and rules are read only when a program starts. `submeter config reload` applies a change by restarting the collector and server.
- Each machine reads its own settings file: the one in the standard location, the one under `SUBMETER_HOME`, or one named with `--file`.

## Fixed on purpose

- Observe-only. No setting lets version 1 act on a process.
- The collector and server run as the signed-in user. They never ask for administrator rights.
- Nothing is sent off the machine. There is no webhook, upload or update check.
- Version 1 opens no network port. The API of version 1.1 binds to loopback and always requires a token.
- `submeter cost --json` and the report never contain command lines, whatever the redaction mode.
- Unavailable metrics stay unavailable. There is no option to fill gaps with estimates.

## What an alert rule can name

An alert rule names one workload pattern and one metric from this list. A rule that names any other metric is refused when the settings are loaded. `machine` is a reserved workload name for the whole computer.

| Metric id | Applies to | Meaning | Unit |
| --- | --- | --- | --- |
| `cpu_cores` | Any workload | Cores in use, averaged over the rule's duration | Cores |
| `memory_bytes` | Any workload | Memory for totals | Bytes |
| `processes` | Any workload | Live processes | Count |
| `io_bytes_per_s` | Any workload | Disk bytes read plus written | Bytes per second |
| `commit_fraction` | `machine` | Memory commit as a share of the commit limit. Read on Windows. On Linux unavailable in version 1, which reads no Linux commit counter; after version 1 it is read only when `vm.overcommit_memory` is 2, otherwise unavailable | 0 to 1 |
| `throttled` | `machine` | 1 while frequency is held down under load, otherwise 0 | 0 or 1 |
| `overhead_fraction` | `submeter` | The summed CPU time of every Submeter process as a share of one core | 0 to 1 |

## The three built-in alert rules

These ship switched on, and your own rules are added to them. They obey the same cooldown. A firing rule raises a finding, which `submeter findings`, `submeter why` and the report show.

| Name | Workload | Metric | Condition | For | Severity |
| --- | --- | --- | --- | --- | --- |
| memory nearly full | `machine` | `commit_fraction` | above 0.90 | 2m | serious |
| thermal throttling | `machine` | `throttled` | above 0 | 5m | warning |
| submeter over budget | `submeter` | `overhead_fraction` | above 0.03 | 5m | warning |

On Linux the kernel enforces the commit limit only when `vm.overcommit_memory` is 2. Under the default setting committed memory commonly exceeds the limit, so an ordinary desktop would read well above 1 and the rule would never clear. Version 1 reads no Linux commit counter, so `commit_fraction` is unavailable on Linux in version 1, and memory nearly full reads unavailable there instead of firing. After version 1, `commit_fraction` is read on Linux only when that setting is 2, because only then does the kernel enforce the limit, and is unavailable otherwise. After version 1, when Linux pressure stall information is read, a machine metric `memory_pressure_full` (Linux only) joins the list above, and on Linux the built-in rule uses memory pressure (PSI memory full) instead.

## Sample submeter.toml

The same file is in this package as [`examples/submeter.toml`](../examples/submeter.toml).

```toml
[sampling]
mode = "adaptive"
active_interval = "2s"
idle_interval = "5s"
idle_after = "60s"
uss_interval = "30s"
uss_top_n = 25
on_battery_multiplier = 2

[sampling.overhead_limit]
idle = "1%"
active = "3%"

[storage]
disk_budget = "2GB"
keyframe_interval = "10m"
retention = { raw = "48h", executables = "1y" }
backups = { keep = 3 }

[analysis.leak]
min_duration = "2h"
min_slope = "50MB/h"

[alerts]
cooldown = "15m"

[[alerts.rules]]
name = "agents eating the machine"
workload = "agent:*"
metric = "cpu_cores"
above = 12
for = "5m"
severity = "warning"

[attribution]
rules_file = "rules.toml"
max_workload_names = 200

[privacy]
redaction = "scrub"
```

## Sample rules.toml

The same file is in this package as [`examples/rules.toml`](../examples/rules.toml).

Rules claim processes that were not started with `submeter run`. The highest-priority match wins, and `submeter rules test` shows which rule claimed a process. A rule may give `exe`, `name`, `cmdline`, `cwd` and `parent`, the program that started the process, and every condition it gives must hold. `exe` matches the executable's file name where it can be read, and otherwise the process name. `name` matches the process name, which on Linux a program can set for itself. Both accept glob patterns such as `python3*` and ignore case. Working folders are read only when some rule uses `cwd`, because reading them costs extra. `include_children` decides whether processes started by a matched process inherit its workload. A rule that omits it follows `attribution.inherit_from_parent`.

```toml
# Highest priority wins. Workloads started with
# "submeter run" never reach these rules.
#
# The exe names are Windows file names. On Linux
# they have no .exe: chrome, firefox, code, node,
# cargo. A pattern such as python3* matches every
# Python 3 version.

[[rule]]
workload = "opaque:wsl"
priority = 90
exe = ["vmmem", "vmmemWSL"]

[[rule]]
workload = "browser"
priority = 50
exe = ["chrome.exe", "msedge.exe", "firefox.exe"]
include_children = true

[[rule]]
workload = "ide"
priority = 50
exe = ["Code.exe", "pycharm64.exe"]
include_children = true

[[rule]]
workload = "agent:untagged"
priority = 40
exe = ["claude.exe", "claude"]
include_children = true
note = "started without submeter run, so polled"

[[rule]]
workload = "builds"
priority = 30
exe = ["python.exe", "node.exe", "cargo.exe"]
cwd = 'C:\src\**'
```
