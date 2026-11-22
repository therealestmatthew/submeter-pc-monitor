# Terms used here

> Submeter build brief · Part 2, the design · [Index](README.md)

- **Workload:** A named group of processes whose cost is reported together, such as one agent run or the browser.
- **Kernel accounting:** Totals the operating system keeps for a group of processes, including those that have exited.
- **Job Object:** The Windows mechanism for grouping processes and accounting for them together.
- **cgroup:** The Linux equivalent: a control group with its own usage counters.
- **USS:** Unique set size. Memory that belongs to one process alone and would be freed if it exited.
- **PSS:** Proportional set size. USS plus a fair share of every shared page. Linux only.
- **Private bytes:** Memory a Windows process has committed for itself, whether or not it is in RAM.
- **Working set:** The part of a process's memory currently in RAM. Windows trims it under pressure.
- **Commit:** Memory the system has promised to processes. Allocations fail as it nears the limit.
- **PSI:** Pressure stall information. Linux's measure of time lost waiting for CPU, memory or I/O.
- **MAD:** Median absolute deviation. A measure of spread that outliers barely move.
