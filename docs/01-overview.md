# At a glance

> Submeter build brief · Summary · [Index](README.md)

## Job 1 · Attribution: What does each workload cost?

- **Where you see it:** Workload table, `submeter cost`
- **It works when:** The parts sum to the whole within 2%, and tagged workloads match the kernel's own totals within 2%.

## Job 2 · Live diagnosis: Why is the machine slow right now?

- **Where you see it:** Verdict strip, `submeter why`
- **It works when:** A verdict with its evidence arrives in under 2 seconds, and reads Inconclusive when the signals disagree.

## Job 3 · Trends: What is drifting over days and weeks?

- **Where you see it:** History view, findings feed, `submeter diff`
- **It works when:** A leak of 50 MB an hour is flagged within 2 hours, and a cache warming up is not.

## The design in eight lines

- **Interface:** Background service, web dashboard and CLI on one data store
- **Extra telemetry:** GPU and VRAM, thermals and power, network per process
- **Control:** Observe only. No process is ever changed in version 1
- **Platforms:** Windows 11 first, Linux from the same codebase
- **Language:** Python 3.12 throughout, with the collector as its own process
- **Privileges:** Runs as the signed-in user. No administrator rights
- **Data:** Kept in local files. Nothing leaves the machine
- **Size of the build:** 3 programs, 25 components, 3 kinds of data file, 8 phases

To start, unpack the starter package and give a Claude Code session the execution prompt, as set out under [How to start](../README.md). It reviews the design, waits for your rulings, then writes the plan and the prompt that builds it. The four decisions that were open are settled under [Build phases](15-phases-and-decisions.md).
