# Build phases

> Submeter build brief · Part 3, the build · [Index](README.md)

Each phase ends at a gate. The builder stops there, writes what it verified, and waits.

## P0: Capability probe and CI

Gate: the baseline modules pass their checks on Windows and Linux runners, and `doctor` is correct on both. The cost of one full sample is measured. Per-process VRAM is checked against the adapter total. The brief is saved in the repository.

## P1: Collector, store, CLI

Gate: a 30-minute CI soak stays inside the budget, per-process figures are within 5% of Windows performance counters, and totals reconcile within 2%. Killing the collector mid-write loses at most 5 seconds and corrupts nothing. CPU-hours from the hourly tier match the raw sum within 0.1%. Deleting a day of raw data frees its space at once.

## P2: Kernel accounting on Windows, attribution, sessions

Gate: on Windows, a tagged tree spawning 500 sub-second children is charged within 2% of the kernel total, its final totals survive its exit, a restarted collector re-attaches to live groups, and `submeter run` returns when the command does. An agent started with `submeter run` retrieves its own run's cost with `submeter cost --run "$SUBMETER_RUN" --json`, and the output holds no command line. On Linux, `submeter run` reports that tagged runs are unavailable and runs the command polled. A session's cost reads the same before and after its raw data is deleted.

## P3: Analysis

Gate: every detector passes a trigger fixture and a quiet fixture, including a cache warm-up and a leak too slow for the hourly check. `why` answers in under 2 seconds.

## P4: Report

Gate: `submeter report` writes one self-contained HTML file for a session or a range, with a meta Content Security Policy. Each chart states the tier and resolution it came from, and the report holds no command line. The API and the live dashboard are not in version 1; their design and gate are kept for version 1.1 in the [build prompt](17-build-prompt.md).

## P5: GPU, throttling, battery, connections

Gate: each provider passes its recorded fixtures and degrades cleanly when its source is absent.

## Decisions made

The four decisions that were open, settled on my recommendation. Each row says how to change it later.

| Decision | Settled as | Why | To change it later |
| --- | --- | --- | --- |
| Agents inside WSL2 or Docker Desktop | Not in version 1. The VM is an opaque workload, and `doctor` reports its share of busy CPU time, and of capacity, from version 1 data. A guest collector is designed after version 1 if that share is large | No transport from the guest to the host is designed. The opaque workload already shows what the VM costs as a whole | Design a guest collector after version 1. Candidate transports: the host collector runs it through wsl.exe and reads its samples from standard output, which keeps the host collector the only writer of raw files; the host pulls from it over WSL's localhost forwarding; or the guest writes JSON files with an atomic rename. A live SQLite file shared across the boundary is ruled out, because WAL does not work over a network filesystem |
| Administrator rights | No. Both programs run as the signed-in user | The Windows machine is a work computer, where administrator rights are often unavailable and a long-running elevated service is the riskiest shape to ask for. All three jobs work without them for your own processes | Add a small elevated helper for per-process network bytes. The collector itself stays unprivileged |
| Alerts off the machine | No. Findings only in version 1: a firing alert rule raises a finding, which `submeter findings`, `submeter why` and the report show. Desktop delivery comes later, and there is no webhook | Version 1 cannot act on a process, so a remote alert could not be acted on either. Leaving it out keeps one plain guarantee: nothing leaves the machine | Add a webhook together with the control layer, when an alert becomes something you can respond to |
| The name | Submeter, replacing Loadscope and the first working name Perfwatch | A package called perfwatch already exists on the Python package index, so `pip install perfwatch` would fetch someone else's code. Loadscope was free there, but it reads as a load-testing tool and shares its name with a pytest-xdist option. A submeter measures each tenant's share of a supply and must add up to the main meter, which is what this tool does for workloads. Submeter was unclaimed on the index on 20 November 2026 | Done throughout this brief and the starter package. No trademark search was done |
