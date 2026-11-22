# Configuration

> Submeter build brief · Part 2, the design · [Index](README.md)

Two files: `submeter.toml` for settings and `rules.toml` for attribution rules. Both are validated on load, and unknown keys are rejected. Most settings reload without a restart, and every change starts a new epoch, marked on the charts, so a shift in the data can be traced to the setting that caused it.

## Sample time explorer

Move the controls to see what a sampling choice costs. The figures come from a simple model with assumed costs, not from measurements. Phase 0 replaces the assumptions with real numbers.

The explorer in `brief.html` is a calculator with three sliders. It is a model with assumed costs, not a measurement. Its inputs, formulas and results are set out here.

**Inputs**

- **Active interval:** 250 ms, 500 ms, 1 s, 2 s, 5 s or 10 s. It starts at 1 s.
- **Cold interval:** 5 s, 10 s, 30 s or 60 s. It starts at 10 s.
- **Processes running:** 100 to 1,000 in steps of 50. It starts at 300.

**Formulas**, where a is the active interval in seconds, c the cold interval in seconds and P the number of processes

- Cost of one bulk sample, assumed: 1.5 ms plus 0.012 ms for each process.
- **Collector overhead**, shown "of one core, limit 3% when active": the sample cost divided by a, as a percentage, plus 0.2 points for the store and the API.
- Hot processes: 10% of P, and at least 10. Cold processes: the rest.
- **Raw rows per 48 h**: hot × 172,800 ÷ a, plus cold × 172,800 ÷ c ÷ 3, plus 8 × 172,800 ÷ a. A cold process is assumed to change enough to be written about one time in three, and the 8 is the workload rows written each interval.
- **Raw data on disk**, shown "of the 2 GB budget": rows × 90 bytes.
- **Short-lived CPU that polling captures**, shown for "children averaging 300 ms. Tagged workloads get 100%": (0.3 ÷ a) × (1 − e^(−a ÷ 0.3)).

**Status line**

| When | Label | Message |
| --- | --- | --- |
| Overhead above 3% and disk above 2 GB | Over | Over both budgets. The overhead guard would lengthen the interval, and raw retention would shrink to about N hours. |
| Overhead above 3% | Over | Over the overhead limit. The guard would lengthen the interval until the collector is back under 3%. |
| Disk above 2 GB | Over | Over the disk budget. Raw retention would shrink from 48 to about N hours. |
| Overhead above 1% | Active only | Fine while active, but above the 1% idle limit, so adaptive mode matters at this setting. |
| Otherwise | In budget | Inside both budgets. |

N is 96 divided by the disk figure in GB, rounded.

**Results**

| Active interval | Cold interval | Processes | Collector overhead | Raw rows per 48 h | Raw data on disk | Polling captures | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 250 ms | 10 s | 300 | 2.2% | 27.8 M | 2.50 GB | 68% | Over the disk budget, raw retention about 38 h |
| 500 ms | 10 s | 300 | 1.2% | 14.7 M | 1.32 GB | 49% | Active only |
| 1 s | 10 s | 300 | 0.7% | 8.1 M | 0.73 GB | 29% | In budget |
| 2 s | 10 s | 300 | 0.5% | 4.8 M | 0.44 GB | 15% | In budget |
| 5 s | 10 s | 300 | 0.3% | 2.9 M | 0.26 GB | 6% | In budget |
| 10 s | 10 s | 300 | 0.3% | 2.2 M | 0.20 GB | 3% | In budget |
| 1 s | 10 s | 100 | 0.5% | 3.6 M | 0.33 GB | 29% | In budget |
| 1 s | 10 s | 1000 | 1.6% | 23.8 M | 2.15 GB | 29% | Over the disk budget, raw retention about 45 h |
| 1 s | 5 s | 300 | 0.7% | 9.7 M | 0.87 GB | 29% | In budget |
| 1 s | 60 s | 300 | 0.7% | 6.8 M | 0.61 GB | 29% | In budget |
| 250 ms | 5 s | 1000 | 5.6% | 85.0 M | 7.65 GB | 68% | Over both budgets, raw retention about 13 h |

## Sampling settings

| Setting | Default | Range | What it changes |
| --- | --- | --- | --- |
| `mode` | adaptive | adaptive, fixed | Adaptive moves between the active and idle intervals. Fixed always uses the active interval |
| `active_interval` | 1s | 250ms to 10s | How often the hot set is sampled while anything is busy |
| `idle_interval` | 5s | 1s to 60s | Sampling rate once the machine has been quiet |
| `cold_interval` | 10s | 5s to 60s | How often inactive processes are checked |
| `idle_after` | 60s | 10s to 10m | Quiet time before dropping to the idle interval |
| `hot_cpu_threshold` | 0.5% | 0.1% to 5% | CPU use that moves a process into the hot set |
| `uss_interval` | 30s | 10s to 5m | How often the expensive memory reading is taken |
| `uss_top_n` | 25 | 0 to 200 | How many of the largest processes get that reading |
| `gpu_interval` | 2s | 1s to 30s | GPU load and adapter VRAM sampling |
| `thermal_interval` | 5s | 1s to 60s | Not used in version 1, which reads no temperatures or battery level. Frequency and the on-battery flag are read with the system counters. Later, temperature and battery sampling |
| `network_interval` | 5s | 1s to 60s | Not used in version 1, which reads no network figures. Later, connection counts and interface bytes |
| `on_battery_multiplier` | 2 | 1 to 10 | Stretches every interval while on battery |
| `overhead_limit` | 1% idle, 3% active | 0.5% to 10% | When exceeded, intervals lengthen and a finding is raised |

A session can override the interval for its own duration, for example `submeter session start bench --interval 250ms`.

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
| Analysis | `slow_growth.window` | 7d | Not used in version 1, which has no slow-growth check. Later, the days of daily minimums used to catch leaks too slow for the leak check |
| Analysis | `baseline.learning_period` | 7d | Not used in version 1, which has no baseline anomaly check. Later, the days of history before anomalies are raised |
| Analysis | `baseline.window` | 14d | Not used in version 1. Later, how far back the usual range looks |
| Analysis | `baseline.sensitivity` | 4.0 | Not used in version 1. Later, the distance from normal, in spreads, that counts as an anomaly |
| Verdict | `window` | 5m | How far back `submeter why` looks |
| Verdict | `thresholds.*` | see verdict table | Tune each signal to your hardware |
| Verdict | `min_confidence` | moderate | Below this the verdict reads Inconclusive |
| Alerts | `rules[]` | 3 built in | Your own thresholds per workload or system-wide |
| Alerts | `cooldown` | 15m | Minimum gap between repeats of the same alert |
| Alerts | `quiet_hours` | off | Not used in version 1, which has no desktop notifications. Later, it holds notifications overnight |
| Alerts | `channels` | dashboard, desktop | Not used in version 1, where every alert is a finding. Later, it says where alerts appear. Nothing is sent off the machine |
| Attribution | `rules_file` | rules.toml | Where workload rules live |
| Attribution | `inherit_from_parent` | true | Turn off to see helper processes on their own |
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
- Any change to sampling, rules or providers starts a new epoch, which is marked on every chart.
- Each machine can carry a named profile, so the desktop and the laptop share one file.

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
| `commit_fraction` | `machine` | Memory commit as a share of the commit limit | 0 to 1 |
| `throttled` | `machine` | 1 while frequency is held down under load, otherwise 0 | 0 or 1 |
| `overhead_fraction` | `submeter` | The collector's CPU time as a share of one core | 0 to 1 |

## The three built-in alert rules

These ship switched on, and your own rules are added to them. They obey the same cooldown. A firing rule raises a finding, which `submeter findings`, `submeter why` and the report show.

| Name | Workload | Metric | Condition | For | Severity |
| --- | --- | --- | --- | --- | --- |
| memory nearly full | `machine` | `commit_fraction` | above 0.90 | 2m | serious |
| thermal throttling | `machine` | `throttled` | above 0 | 5m | warning |
| submeter over budget | `submeter` | `overhead_fraction` | above 0.03 | 5m | warning |

## Sample submeter.toml

The same file is in this package as [`examples/submeter.toml`](../examples/submeter.toml).

```toml
[sampling]
mode = "adaptive"
active_interval = "1s"
idle_interval = "5s"
cold_interval = "10s"
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

[profile.laptop]
sampling.active_interval = "2s"
storage.disk_budget = "1GB"
```

## Sample rules.toml

The same file is in this package as [`examples/rules.toml`](../examples/rules.toml).

Rules claim processes that were not started with `submeter run`. The highest-priority match wins, and `submeter rules test` shows which rule claimed a process. A rule may give `exe`, `cmdline`, `cwd` and `parent`, the program that started the process, and every condition it gives must hold. Working folders are read only when some rule uses `cwd`, because reading them costs extra.

```toml
# Highest priority wins. Workloads started with
# "submeter run" never reach these rules.

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
