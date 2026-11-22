# Known limits

> Submeter build brief · Part 2, the design · [Index](README.md)

What version 1 cannot measure, and what it does about each. The CLI output, the report and `submeter doctor` state these beside the numbers they affect.

| Limit | Effect on the numbers | What Submeter does |
| --- | --- | --- |
| Work done for a workload by another process | Docker's daemon, a shared language server, a browser that was already open, or anything started through a service is charged to itself, not to the agent that asked | Shows those processes under their own workloads and says so beside agent totals |
| Short-lived children of polled workloads | Their CPU time is undercounted on Windows, by about 70% at a 1-second interval in the polling model in [Data flow](05-data-flow.md) | Labels the workload as polled. On Windows, launching it with `submeter run` removes the gap. On Linux, tagged runs are unavailable in version 1 |
| Linux in version 1 | Tagged runs are unavailable, and PSI and the other Linux system counters are not read. Polling through psutil costs about 95 ms per tick at 300 processes, store writes included, so the intervals are longer than on Windows | `submeter run` runs the command polled and labels the workload as polled. `why` reads Inconclusive or unavailable. The overhead guard holds the intervals at about 3.2 s active and 9.5 s idle, or longer |
| WSL2 and Docker Desktop | Everything inside appears as one VM process | Shows the VM as an opaque workload, and reports its share of busy CPU time in `doctor`. No guest collector is built in version 1 |
| A CPU-second is not a fixed amount of work | Efficiency cores and reduced frequency do less with the same second | Reports CPU time as measured, with frequency beside it. Nothing is normalised in version 1 |
| Per-process VRAM | Not collected in version 1. On Windows the only per-process counter may over-report | Reports the adapter's VRAM used and total, which the GPU-bound verdict reads |
| Temperatures on Windows | Not available without administrator rights | Detects throttling from frequency instead |
| Network per process | Bytes per process need administrator rights, and connections per process and bytes per interface are not collected in version 1 either | Reports no network figures in version 1 |
| Processes owned by other users or the system | CPU time and working set are counted. Command lines and USS are not readable | Counts them in the Restricted bucket and never drops them |
| Which files a process touches | Only bytes read and written and handle counts are recorded per process | Reports I/O totals per process and disk latency for the system. Per-file tracking would need deep tracing |
| Workload memory totals | Can lag by up to the USS interval, 30 seconds by default | Shows the age of the reading |
