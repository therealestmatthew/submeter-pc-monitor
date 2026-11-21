# What the tool looks like

> Submeter build brief · Part 1, the product · [Index](README.md)

Not in version 1. The live dashboard described here is planned for version 1.1. Version 1 shows these figures through the CLI and the HTML report written by `submeter report`.

A working mock of the live dashboard on a machine with 16 logical cores and 32 GB of memory. Every number is synthetic and the clock runs faster than real time. Pick a scenario, switch the chart between CPU and memory, and select a workload to see its process tree.

## The mock, described

The page `brief.html` in this folder runs the mock in a browser. This section states everything the mock shows, so nothing here depends on opening it.

The mock models a machine with 16 logical cores, 12 on performance cores and 4 efficiency cores, and 32 GB of memory. It advances once a second and keeps the last 120 points, which is 2 minutes. It pauses itself when the browser asks for reduced motion.

### Layout, from top to bottom

1. **Title bar.** "Submeter · Live", with the label "Simulation · synthetic data".
2. **Scenario buttons.** Steady day, Launch 12 agents, Memory leak in IDE, Thermal throttle, and Pause.
3. **Verdict banner.** A severity chip that reads Healthy, Warning or Serious, a title such as "No bottleneck", the line "confidence: high · last 5 min", and two or three chips of evidence.
4. **Four tiles**, each with a meter. They are listed in the next table.
5. **Load per logical core.** Sixteen bars in two groups, labelled "Performance, 12 logical" and "Efficiency, 4", beside the line "frequency 100% of maximum". The percentage follows the scenario.
6. **Chart.** "CPU by workload, last 2 minutes" is a stacked area chart with one band per workload. A switch marked CPU and Memory changes it to "Memory by workload, last 2 minutes". The unit line reads "cores in use, of 16" or "GB in use, of 32". The time axis reads "2 min ago", "1 min ago" and "now". Hovering shows each workload's value and the total for that second.
7. **Where the CPU time went**, marked "must sum to 100%". One bar is split by workload, with idle time last. Under it is a line such as "Attributed 26% + unattributed 2% + system 2% + restricted 1% + idle 69% = 100%", which is the steady scenario.
8. **Workloads**, marked "select a name to see its process tree". The table's columns are Workload, CPU, Memory, Procs, CPU trend and State. Each name carries its accounting source, and CPU trend is a small line of the last 40 seconds.
9. **Process tree** of the selected workload.
10. **Findings**, marked "newest first". The list keeps the five most recent.

### The four tiles

| Tile | Value | Line below it | Meter |
| --- | --- | --- | --- |
| CPU time in use | Percent of 16 cores | "5.0 of 16 cores" | Turns serious above 86% |
| Memory commit | Percent of 32 GB | "20.8 of 32 GB" | Turns warning above 74% and serious above 86% |
| GPU busiest engine | Percent | "3D engine · VRAM 2.8 of 12 GB". VRAM is modelled as 2.1 GB plus the GPU percentage divided by 22 | Shows the percentage |
| Submeter overhead | Percent of one core | "1 s cadence · limit 3%" | Shows the share of the 3% limit in use |

### The seven workloads at rest

| Workload | Accounting source | CPU, cores | Memory | Processes |
| --- | --- | --- | --- | --- |
| Agents | kernel · job | 2.4 | 6.2 GB | 38 |
| Browser | polled | 0.9 | 5.1 GB | 24 |
| IDE | polled | 0.6 | 3.4 GB | 11 |
| Builds | kernel · job | 0.3 | 1.2 GB | 4 |
| Unattributed | polled | 0.25 | 2.0 GB | 61 |
| System | counters | 0.35 | 2.6 GB | n/a |
| Restricted | partial | 0.16 | 0.3 GB | 14 |

Together they use 4.96 cores, which is 31% of 16, and 20.8 GB, which is 65% of 32.

The State column reads Steady unless one of these holds:

- **Running:** Builds is above 0.6 cores.
- **Elevated:** Agents, Browser, IDE or Builds is above 2.2 times its usual CPU.
- **Slowed:** Agents, Browser, IDE and Builds, while the machine is throttled.
- **Growing:** the IDE is more than 1.5 GB above its usual memory in the leak scenario.

### The four scenarios

| Scenario | What it changes | Verdict it reaches | Findings it raises |
| --- | --- | --- | --- |
| Steady day | Nothing. Builds bursts by 1.4 cores for 6 seconds in every 37. GPU 16%, overhead 0.6% | Healthy: No bottleneck | None |
| Launch 12 agents | Agents go to 9.8 cores, 9.6 GB and 152 processes. Builds go to 2.6 cores, 2.6 GB and 17 processes. GPU 58%, overhead 1.3% | Warning: CPU-bound, at about 92% of 16 cores | "Bottleneck: CPU-bound. Agent trees and the builds they trigger are using most of 16 cores." and "Process count: Agents went from 38 to 125 processes in under a minute." The count is whatever it has reached when it first passes 120 |
| Memory leak in IDE | IDE memory climbs 0.16 GB each second until it reaches 13.5 GB. Overhead 0.7% | Warning: Memory tightening above 74% commit, then Serious: Memory-bound above 86% | After 14 seconds, "Memory growth: IDE private bytes up 1.8 GB with no plateau.", where the figure is the growth so far. At Memory-bound, "Bottleneck: Memory-bound. Commit is near the limit and page writes have started." |
| Thermal throttle | Agents 8.6, Browser 1.6, IDE 1.2, Builds 1.9, Unattributed 0.5 and System 0.6 cores. Frequency falls to 62% of maximum. Overhead 0.9% | Serious: Thermally throttled | "Throttling: frequency is held at 78% of maximum while every core is busy." It is raised as the frequency first drops below 80%, on its way to 62% |

Two findings are present from the start: a Warning from 12 min ago, "Baseline anomaly: Browser memory is 1.4 GB above its usual range for active use.", and a Cleared entry from 41 min ago, "Growth check: Browser memory levelled off after warm-up. No leak."

### How the verdict is chosen

The rules are checked in this order and the first match wins. The two "stays until" clauses are hysteresis, so the verdict does not flicker at a threshold.

| Verdict | Severity | Rule | Confidence | Evidence shown |
| --- | --- | --- | --- | --- |
| Thermally throttled | Serious | Frequency below 80% of maximum | high | "Frequency 62% of maximum under load", "CPU time 91%, the work of 9.0 full-speed cores", "No power-saving plan active" |
| Memory-bound | Serious | Commit above 86%. Stays until it falls below 82% | high | "Commit 88% of limit", "Page writes rising", "IDE private bytes still growing" |
| CPU-bound | Warning | CPU time above 86%. Stays until it falls below 80% | high | "Run queue 2.0 per core", "Agents hold 67% of CPU time", "Frequency not limited" |
| Memory tightening | Warning | Commit above 74% | moderate | "Commit 78% of limit", "No page writes yet" |
| No bottleneck | Healthy | None of the above | high | "No pressure signals", "Commit 65% of limit", "Frequency at maximum" |

The numbers inside the evidence follow the simulation. Run queue is modelled as 1 plus 9 times the amount by which CPU time exceeds 80%.

### The process trees

Each tree is shown with the workload's values at rest.

**Agents**

```text
agents  kernel · 2.40 cores · 6.2 GB
├─ agent:refactor             job
│  ├─ node claude             1.1 GB
│  ├─ python pytest -q        0.4 GB
│  └─ git, rg, sh (exited)
│     3,412 short-lived children
│     212 CPU-s, from job accounting
├─ agent:tests                job
└─ agent:docs                 job
```

**Browser**

```text
browser  polled · 0.90 cores · 5.1 GB
├─ chrome --type=browser      0.6 GB
├─ chrome --type=gpu-process  0.4 GB
└─ chrome --type=renderer     x21
rule: exe = chrome.exe, with children
```

**IDE**

```text
ide  polled · 0.60 cores · 3.4 GB
├─ Code.exe                   0.5 GB
├─ Code.exe extensionHost     2.1 GB
└─ pylance, eslint server     x4
rule: exe = Code.exe, with children
```

**Builds**

```text
builds  kernel · 0.30 cores · 1.2 GB
└─ uv run pytest -n 8
   └─ python                  x8
started with: submeter run --as builds
```

**Unattributed**

```text
unattributed  polled · 0.25 cores · 2.0 GB
61 processes matched no rule.
Largest: SearchIndexer, OneDrive.
Claim them with a rule in rules.toml.
```

**System**

```text
system  counters · 0.35 cores · 2.6 GB
Kernel time, interrupts, deferred calls
and non-process memory.
No process owns these.
```

**Restricted**

```text
restricted  partial · 0.16 cores · 0.3 GB
14 processes owned by other users.
CPU time and working set are counted.
Command lines and USS are not readable,
because Submeter never runs elevated.
```

### How the mock moves

Each second every workload moves part of the way to its target: 18% for CPU, 22% for memory and 25% for process count, with a little noise. Total CPU is capped at 98.5% of 16 cores. Per-core load weights performance cores about two and a half times as heavily as efficiency cores, with noise of up to 22% on each. Frequency, GPU load and overhead ease towards their targets in the same way.
