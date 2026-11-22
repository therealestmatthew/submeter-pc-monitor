# What it does

> Submeter build brief · Part 1, the product · [Index](README.md)

## Measure

- Exact CPU time, I/O and process counts for tagged workloads on Windows, kept by the kernel, including processes that exit between samples. Their current memory is a USS sum, as for every workload. On Linux tagged runs come after version 1.
- Everything else from one bulk snapshot per tick that reads every process: by default every 2 seconds while the machine is busy and every 5 once it is quiet. The costly readings, such as USS, are taken less often.
- Memory in units that sum across processes, with separate units for spotting growth.
- GPU load, the adapter's VRAM, frequency and throttling, each marked full, partial or unavailable. Per-process VRAM, connections, battery level and temperatures come after version 1.

## Attribute

- `submeter run --as NAME -- COMMAND` tags a whole process tree at launch, on Windows. On Linux in version 1 it runs the command polled.
- Rules claim everything else by executable, process name, command line, parent or folder.
- Every workload shows whether the kernel or polling measured it.
- Unattributed, System, Restricted and Submeter itself are always shown, with the CPU time that polling did not see beside them, and the parts must sum to the whole.

## Remember

- Two lifetimes in two kinds of file: 48 hours of full detail, and hourly history kept.
- Retention is a file delete, under a 2 GB cap that the server enforces while it runs. If the store is still over the cap once raw is down to 24 hours and backups to one, a finding is raised, and history is never deleted. No raw day is deleted before it is rolled up into hourly history. While the server is down, the collector deletes raw files older than 7 days, or older than the raw retention if that is longer.
- Sessions and tagged runs are summarised as they run, and the summary is closed when they end, so their cost stays exact for good, however long they ran.
- A change of sampling settings, rules, provider status, hardware or Submeter version starts a new epoch, marked on the charts. A wall-clock step that the collector detects also starts a new epoch. Cadence the collector changes itself, and edits to alert, UI or verdict settings, do not.

## Explain

- A bottleneck verdict with confidence and evidence, or Inconclusive.
- Leak detection that waits for growth with no plateau.
- Regressions shown by `submeter diff` and the hourly history. Baseline anomalies and slow growth come after version 1.
- Session diffs ranked by size of change.

## Show

- A CLI with JSON output on every command, with `submeter findings` for the findings and `submeter diff` to compare two sessions.
- Self-contained HTML reports, which hold the charts for a session or range.
- Alert rules with cooldowns, which raise findings. Version 1 has no desktop notifications.
- An agent started with `submeter run` can ask what it is costing with `submeter cost --run "$SUBMETER_RUN" --json`.
- The live dashboard, with its history explorer, findings feed and session compare, comes in version 1.1.

## Protect

- Observe only. No setting lets version 1 act on a process.
- Command lines are scrubbed of secrets before they are stored.
- Version 1 opens no network port. The local API of version 1.1 needs a token and refuses requests from web pages.
- Runs as the signed-in user and never asks for administrator rights.
- Nothing leaves the machine.
