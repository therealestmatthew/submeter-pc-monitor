# What it does

> Submeter build brief · Part 1, the product · [Index](README.md)

## Measure

- Exact totals for tagged workloads on Windows, kept by the kernel, including processes that exit between samples. On Linux tagged runs come after version 1.
- Everything else from one bulk snapshot per tick: busy processes every second, idle ones every ten.
- Memory in units that sum across processes, with separate units for spotting growth.
- GPU load, VRAM, frequency, throttling, battery and connections, each marked full, partial or unavailable.

## Attribute

- `submeter run --as NAME -- COMMAND` tags a whole process tree at launch, on Windows. On Linux in version 1 it runs the command polled.
- Rules claim everything else by executable, command line, parent or folder.
- Every workload shows whether the kernel or polling measured it.
- Unattributed, System, Restricted and Submeter itself are always shown, and the parts must sum to the whole.

## Remember

- Three lifetimes in three kinds of file: 48 hours of full detail, 30 days by the minute, hourly history kept.
- Retention is a file delete, under a 2 GB cap that is enforced exactly.
- Sessions and tagged runs are summarised when they end, so their cost stays exact for good.
- Every change of settings, rules or hardware starts a new epoch, marked on the charts.

## Explain

- A bottleneck verdict with confidence and evidence, or Inconclusive.
- Leak detection that waits for growth with no plateau.
- Baselines learned separately for idle and active use.
- Session diffs ranked by size of change.

## Show

- Live dashboard, history explorer, findings feed and session compare.
- A CLI with JSON output on every command.
- Self-contained HTML reports and alerts with cooldowns.
- A read-only MCP server, so an agent can ask what it is costing.

## Protect

- Observe only. No setting lets version 1 act on a process.
- Command lines are scrubbed of secrets before they are stored.
- The local API needs a token and refuses requests from web pages.
- Runs as the signed-in user and never asks for administrator rights.
- Nothing leaves the machine.
