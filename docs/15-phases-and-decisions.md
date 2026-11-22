# Build phases

> Submeter build brief · Part 3, the build · [Index](README.md)

Each phase ends at a gate. The builder stops there, writes what it verified, and waits.

## P0: Decision probes and CI

Phase 0 settles the facts that change the design of version 1 on the owner's own machine, and sets up CI, before anything is built on them.

1. On the owner's Windows machine, as the signed-in standard user, run the four checks in `AGENTS.md` (ruff check, ruff format, mypy and pytest) and `scripts/platform_check.py`, and save their full output. After `scripts/platform_check.py`, look in the Defender Operational log for attack surface reduction (ASR) events naming python.exe, and save what is found. [What to check first on Windows](reference/windows-priorities.md) explains each line. Item 3 of that file also has a check of interrupt and DPC time that the script does not run; run it by hand and save its output.
2. Set up CI on Windows and Linux runners for the portable tests. On the Linux runner, also measure the per-tick cost of reading `cpu.stat` in every leaf cgroup, which decides whether Linux places CPU time not seen by polling by cgroup (P2). Run a script there that reads PSS once for every readable process, and save its CPU cost and the process count with the other phase 0 output, labelled as a CI-runner figure. Judged at the USS interval, it decides whether Linux workload memory totals can use PSS for every process instead of only the largest.
3. Write three probes that the owner runs on that machine. Each saves its output, and each decides one choice:

| Probe | What it does | What it decides |
| --- | --- | --- |
| Job Object | Creates a job as this user, nests one job inside another, also when the terminal or Claude Code has already placed the process in a job, reads the totals after every child has exited, and reopens the job by name after the process that created it has exited. It also records the error a direct child gets when it asks to break away, and whether a grandchild started through node and then bash stays in the job | The design of the holder that keeps a tagged group open until it is empty, and whether allowing breakaway would be safe. Version 1 keeps breakaway forbidden |
| Bulk snapshot | A prototype of the system-wide process snapshot, timed at the owner's process count. It also shows what the snapshot returns for other users' processes without administrator rights | Whether the collector stays in Python, and the default intervals |
| Per-user autostart | As a standard user, registers and deletes a logon task with the settings `submeter daemon install` uses: an InteractiveToken logon trigger, no stop or refusal on battery, no time limit and normal priority (see the [build prompt](17-build-prompt.md)) | How `submeter daemon install` installs on Windows: that scheduled task, or the `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` key if a standard user cannot register the task |

`doctor` is not built out into the full capability matrix in phase 0. It grows with each provider.

Gate: the baseline passes its checks on the Windows and Linux runners, the output of step 1 and of each probe is saved, and the choice each probe decides is recorded. The brief is saved in the repository.

## P1: Tagged runs

Builds the launcher, `submeter run`, with its detached holder; the reading of a Job Object's final totals (part of component 14); the run file; `submeter cost --run`, which reads run files only, because the history file does not exist yet; and the load generator. No collector or store is needed. A run file holds the kernel's CPU time, I/O and process counts and the job's peak commit. A run's mean memory and top executables come from the collector's samples, so they are unavailable until the collector (P2) and the server (P3) exist.

Gate: on Windows, a tagged tree spawning 500 sub-second children is charged within 2% of the load generator's own accounting, its final totals survive its exit, and `submeter run` returns with the command's exit code while processes it left behind are still counted. A tagged run started inside another records its parent, the parent's run total excludes the child's, and the two together match the load generator's own accounting within 2%. In a tagged run, a direct child that asks to break away gets an error, which is recorded; a grandchild started through node and then bash stays in the group; and a Chromium-based browser opens pages. An agent started with `submeter run` retrieves its own run's cost with `submeter cost --run "$SUBMETER_RUN" --json`, and the output holds no command line. On the Linux CI runner, `submeter run` reports that tagged runs are unavailable and runs the command polled.

## P2: Collector and raw store

Builds the Windows bulk snapshot provider, the Windows system counters (component 06), the collector loop with adaptive cadence and the overhead guard, the raw files with command lines redacted before they are written, and the baseline attribution with its four fixed buckets, so that reconciliation can be tested. On Linux it also places CPU time not seen by polling by cgroup, unless phase 0 showed that reading every leaf cgroup's `cpu.stat` each tick breaks the overhead budget.

Gate: a 30-minute CI soak stays inside the budget, per-process figures are within 5% of Windows performance counters, and totals reconcile within 2%, with CPU time not seen by polling as its own term. On a quiet fixture that term stays under the share stated with the fixture. Killing the collector mid-write loses at most 5 seconds and corrupts nothing.

## P3: Attribution rules, history, sessions

Builds the server, with the history file, the hourly rollup, retention, the disk budget, backups and the copying of final run files into the history file; the attribution rules; sessions, through their marker files; and the collector's reading of each live group's totals, with re-attach after a restart.

Gate: CPU-hours from the hourly tier match the raw sum within 0.1%. Deleting a day of raw data frees its space at once. On Windows, a restarted collector re-attaches to live groups. A session's cost reads the same before and after its raw data is deleted.

## P4: Analysis

Builds the bottleneck verdict and `submeter why`, the leak check, the runaway process count, the session diff, and the alert rules, whose findings `submeter findings` lists.

Gate: every detector passes a trigger fixture and a quiet fixture, including a cache warm-up. `why` answers in under 2 seconds.

## P5: Report and GPU load

Builds `submeter report` and the extended providers: GPU load by engine type and the adapter's VRAM.

Gate: `submeter report` writes one self-contained HTML file for a session or a range, with a meta Content Security Policy. Each chart states the tier and resolution it came from, and the report holds no command line. Each extended provider passes its recorded fixtures and degrades cleanly when its source is absent. The API and the live dashboard are not in version 1; their design and gate are kept for version 1.1 in the [build prompt](17-build-prompt.md).

## The floor of version 1

No cut may remove these, because the acceptance checks of the three jobs in [At a glance](01-overview.md), the first two priorities in the [build prompt](17-build-prompt.md) or the rules in `AGENTS.md` depend on them:

- Tagged runs on Windows: tagged workloads match the load generator's own accounting within 2% (job 1). On Linux in version 1, tagged runs are unavailable.
- The collector and the raw store, with the baseline attribution and its four fixed buckets, and beside them the machine-level figure for CPU time not seen by polling, so that reconciliation can be tested and the parts sum to the whole within 2% (job 1).
- The bottleneck verdict and `submeter why`, which answer with their evidence in under 2 seconds and read Inconclusive when the signals disagree, and the adapter's VRAM, which the GPU-bound verdict reads to rule itself out, or a GPU-bound rule-out rewritten so that it does not need it (job 2).
- The leak check, held to job 3's acceptance, and a CLI surface for findings: `submeter findings`, with `submeter why` and the report also showing them (job 3).
- A path for sessions that needs no API: `submeter session start` and `stop` write marker files, which the server reads. `submeter cost` and `submeter diff` read sessions (jobs 1 and 3).
- A metric that cannot be measured is recorded as unavailable, never as zero or an estimate, and Submeter stays inside its overhead budget (priorities 1 and 2).
- Command lines are redacted before anything is written, as `AGENTS.md` requires.

## Decisions made

The four decisions that were open, settled on my recommendation. Each row says how to change it later.

| Decision | Settled as | Why | To change it later |
| --- | --- | --- | --- |
| Agents inside WSL2 or Docker Desktop | Not in version 1. The VM is an opaque workload, and `doctor` reports its share of busy CPU time, and of capacity, from version 1 data. A guest collector is designed after version 1 if that share is large | No transport from the guest to the host is designed. The opaque workload already shows what the VM costs as a whole | Design a guest collector after version 1. Candidate transports: the host collector runs it through wsl.exe and reads its samples from standard output, which keeps the host collector the only writer of raw files; the host pulls from it over WSL's localhost forwarding; or the guest writes JSON files with an atomic rename. A live SQLite file shared across the boundary is ruled out, because WAL does not work over a network filesystem |
| Administrator rights | No. Both programs run as the signed-in user | The Windows machine is a work computer, where administrator rights are often unavailable and a long-running elevated service is the riskiest shape to ask for. All three jobs work without them for your own processes | Add a small elevated helper for per-process network bytes. The collector itself stays unprivileged |
| Alerts off the machine | No. Findings only in version 1: a firing alert rule raises a finding, which `submeter findings`, `submeter why` and the report show. Desktop delivery comes later, and there is no webhook | Version 1 cannot act on a process, so a remote alert could not be acted on either. Leaving it out keeps one plain guarantee: nothing leaves the machine | Add a webhook together with the control layer, when an alert becomes something you can respond to |
| The name | Submeter, replacing Loadscope and the first working name Perfwatch | A package called perfwatch already exists on the Python package index, so `pip install perfwatch` would fetch someone else's code. Loadscope was free there, but it reads as a load-testing tool and shares its name with a pytest-xdist option. A submeter measures each tenant's share of a supply and must add up to the main meter, which is what this tool does for workloads. Submeter was unclaimed on the index on 20 November 2026 | Done throughout this brief and the starter package. No trademark search was done |
