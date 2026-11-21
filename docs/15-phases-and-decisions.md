# Build phases

> Submeter build brief · Part 3, the build · [Index](README.md)

Each phase ends at a gate. The builder stops there, writes what it verified, and waits.

## P0: Capability probe and CI

Gate: the baseline modules pass their checks on Windows and Linux runners, and `doctor` is correct on both. The cost of one full sample is measured. Per-process VRAM is checked against the adapter total. The share of CPU time held by a WSL2 or Docker VM is reported. The brief is saved in the repository.

## P1: Collector, store, CLI

Gate: a 30-minute CI soak stays inside the budget, per-process figures are within 5% of Windows performance counters, and totals reconcile within 2%. Killing the collector mid-write loses at most 5 seconds and corrupts nothing. CPU-hours from the hourly tier match the raw sum within 0.1%. Deleting a day of raw data frees its space at once.

## P2: Kernel accounting on Windows, attribution, sessions

Gate: on Windows, a tagged tree spawning 500 sub-second children is charged within 2% of the kernel total, its final totals survive its exit, a restarted collector re-attaches to live groups, and `submeter run` returns when the command does. On Linux, `submeter run` reports that tagged runs are unavailable and runs the command polled. A session's cost reads the same before and after its raw data is deleted.

## P3: Analysis

Gate: every detector passes a trigger fixture and a quiet fixture, including a cache warm-up and a leak too slow for the hourly check. `why` answers in under 2 seconds.

## P4: API and dashboard

Gate: requests without a token or with a foreign Origin are refused. A 30-day range loads in under 1 second and states the tier it came from.

## P5: GPU, throttling, battery, connections

Gate: each provider passes its recorded fixtures and degrades cleanly when its source is absent.

## P6: Reports and MCP server

Gate: an agent can retrieve its own cost for a session, and no response contains a command line.

## P7: WSL2 guest collector

Gate: processes inside WSL appear under their own workloads on the host dashboard. This phase moves to directly after phase 2 if the phase 0 measurement calls for it.

## Decisions made

The four decisions that were open, settled on my recommendation. Each row says how to change it later.

| Decision | Settled as | Why | To change it later |
| --- | --- | --- | --- |
| Agents inside WSL2 or Docker Desktop | Decided by measurement. Phase 0 reports the VM's share of CPU time over a working day. Above 10%, the guest collector moves to directly after phase 2. Otherwise it stays last | It is a fact about your machine, so measuring beats guessing. The VM is shown as its own workload either way | Nothing to change. The rule applies itself |
| Administrator rights | No. Both programs run as the signed-in user | The Windows machine is a work computer, where administrator rights are often unavailable and a long-running elevated service is the riskiest shape to ask for. All three jobs work without them for your own processes | Add a small elevated helper for per-process network bytes. The collector itself stays unprivileged |
| Alerts off the machine | No. Dashboard and desktop notifications only, with no webhook in version 1 | Version 1 cannot act on a process, so a remote alert could not be acted on either. Leaving it out keeps one plain guarantee: nothing leaves the machine | Add a webhook together with the control layer, when an alert becomes something you can respond to |
| The name | Submeter, replacing Loadscope and the first working name Perfwatch | A package called perfwatch already exists on the Python package index, so `pip install perfwatch` would fetch someone else's code. Loadscope was free there, but it reads as a load-testing tool and shares its name with a pytest-xdist option. A submeter measures each tenant's share of a supply and must add up to the main meter, which is what this tool does for workloads. Submeter was unclaimed on the index on 20 November 2026 | Done throughout this brief and the starter package. No trademark search was done |
