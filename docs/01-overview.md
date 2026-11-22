# At a glance

> Submeter build brief · Summary · [Index](README.md)

## Job 1 · Attribution: What does each workload cost?

- **Where you see it:** `submeter cost`, `submeter top` and the report
- **It works when:** The parts sum to the whole within 2%, and on Windows tagged workloads match the load generator's own accounting within 2%. On Linux tagged runs are unavailable in version 1.

## Job 2 · Live diagnosis: Why is the machine slow right now?

- **Where you see it:** `submeter why`
- **It works when:** A verdict with its evidence arrives in under 2 seconds, and reads Inconclusive when the signals disagree.

## Job 3 · Trends: What is drifting over days and weeks?

- **Where you see it:** `submeter findings`, `submeter diff` and the report's history charts
- **It works when:** A leak of 50 MB an hour is flagged within 2 hours, and a cache warming up is not.

## The design in eight lines

- **Interface:** Background service, CLI and self-contained HTML report on one data store. The live web dashboard comes in version 1.1
- **Extra telemetry:** GPU load by engine type and the adapter's VRAM. Per-process VRAM, temperatures, battery level and network per process come after version 1
- **Control:** Observe only. No process is ever changed in version 1
- **Platforms:** Windows 11 gets everything. Linux runs polled from the same codebase and is tested in CI. Its tagged runs, system counters and autostart come after version 1
- **Language:** Python 3.12 throughout, with the collector as its own process
- **Privileges:** Runs as the signed-in user. No administrator rights
- **Data:** Kept in local files. Nothing leaves the machine
- **Size of the build:** 3 programs, 25 components, 3 kinds of data file, 8 phases

To start, unpack the starter package and give a Claude Code session the execution prompt, as set out under [How to start](../README.md). It reviews the design, waits for your rulings, then writes the plan and the prompt that builds it. The four decisions that were open are settled under [Build phases](15-phases-and-decisions.md).
