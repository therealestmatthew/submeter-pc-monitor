# Known limits

> Submeter build brief · Part 2, the design · [Index](README.md)

What version 1 cannot measure, and what it does about each. The dashboard and `submeter doctor` state these beside the numbers they affect.

| Limit | Effect on the numbers | What Submeter does |
| --- | --- | --- |
| Work done for a workload by another process | Docker's daemon, a shared language server, a browser that was already open, or anything started through a service is charged to itself, not to the agent that asked | Shows those processes under their own workloads and says so beside agent totals |
| Short-lived children of polled workloads | Their CPU time is undercounted on Windows, by about 70% at a 1-second interval in the polling model in [Data flow](05-data-flow.md) | Labels the workload as polled. Launching it with `submeter run` removes the gap |
| WSL2 and Docker Desktop | Everything inside appears as one VM process | Shows the VM as an opaque workload until the guest collector exists in phase 7 |
| A CPU-second is not a fixed amount of work | Efficiency cores and reduced frequency do less with the same second | Reports CPU time as measured, with frequency beside it. Nothing is normalised in version 1 |
| Per-process VRAM on Windows | The counter may over-report | Checks it against the adapter total in phase 0 and marks it partial if the two drift |
| Temperatures on Windows | Not available without administrator rights | Detects throttling from frequency instead |
| Network bytes per process | Not collected in version 1, which runs without administrator rights | Reports connections per process and bytes per interface |
| Processes owned by other users or the system | CPU time and working set are counted. Command lines and USS are not readable | Counts them in the Restricted bucket and never drops them |
| Which files a process touches | Only bytes read and written and handle counts are recorded per process | Reports I/O totals per process and disk latency for the system. Per-file tracking would need deep tracing |
| Workload memory totals | Can lag by up to the USS interval, 30 seconds by default | Shows the age of the reading |
