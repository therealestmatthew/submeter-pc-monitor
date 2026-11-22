# Telemetry by platform

> Submeter build brief · Part 2, the design · [Index](README.md)

Where each metric comes from. Rows marked Docs were checked against vendor documentation on 20 November 2026. The rest are confirmed by the capability probe in phase 0. A metric the system cannot deliver is shown as unavailable, never as zero. On Linux, version 1 polls through psutil, which reads the /proc files named below; a metric or Linux source marked after version 1 is not read in version 1. Version 1 reads VRAM only per adapter, used and total.

| Metric | Windows | Linux | Without admin | Checked |
| --- | --- | --- | --- | --- |
| Tagged workload totals | Job Object accounting, which includes processes that have exited | After version 1: cgroup v2, `cpu.stat` always, memory and io files where delegated. In version 1 `submeter run` runs the command polled | Full | Docs [1](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects) [2](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_accounting_information) [3](https://docs.kernel.org/admin-guide/cgroup-v2.html) |
| CPU per process | One system-wide process snapshot. Microsoft marks the call as subject to change, so psutil is the fallback | `/proc/<pid>/stat` | Full | Docs [4](https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-ntquerysysteminformation) |
| Memory per process | Private bytes, working set, USS | RSS, PSS and USS from `smaps_rollup` | Own user only | Phase 0 |
| Disk I/O per process | Process I/O counters, which include non-file I/O | `/proc/<pid>/io` | Own user only | Phase 0 |
| GPU load per process | GPU Engine counters by engine type, with the busiest engine as the headline | NVML for NVIDIA, sysfs for AMD | Full | Docs [5](https://devblogs.microsoft.com/directx/gpus-in-the-task-manager/) |
| VRAM per process (after version 1) | GPU Process Memory counter. Microsoft documents over-reporting on Windows 10, so it is checked against the adapter total. NVML reports it as unavailable under the desktop driver model | NVML | Partial until validated | Docs [6](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/gpu-process-memory-counters-report-wrong-value) [7](https://docs.nvidia.com/deploy/nvml-api/structnvmlProcessInfo__v1__t.html) |
| Temperatures (after version 1) | No dependable source without administrator rights, and psutil offers none here | hwmon | Linux only | Docs [8](https://psutil.readthedocs.io/latest/blog/2017/sensors-support.html) |
| CPU throttling | Processor frequency and performance counters. psutil reports only a nominal frequency here | cpufreq and `thermal_throttle` counters | Full | Docs [8](https://psutil.readthedocs.io/latest/blog/2017/sensors-support.html) |
| Power | The on-battery flag. Battery level after version 1 | The on-battery flag. Battery level after version 1. RAPL needs root | Battery only | Phase 0 |
| Network connections (after version 1) | Per process | Per process | Own user only | Phase 0 |
| Network bytes per process | Needs administrator rights | Needs root for other users' sockets | Not in version 1 | Phase 0 |
| Pressure signals | Run queue, commit, page writes, disk queue | After version 1: PSI for CPU, memory and I/O | Full | Phase 0 |

## What the documentation check changed

- Per-process VRAM on Windows is now partial until validated. It was listed as full.
- The bulk process snapshot now has a required fallback, because Microsoft marks the underlying call as subject to change.
- Task Manager is no longer a reference anywhere. Its CPU figure was frequency-scaled from Windows 8, and its Processes page moved to a time-based figure in 2025. [9](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/cpu-usage-exceeds-100) [10](https://www.windowslatest.com/2025/05/26/windows-11-24h2s-task-manager-new-cpu-usage-formula-rolls-out-to-everyone)

## Sources

1. [Microsoft Learn: Job Objects](https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects)
2. [Microsoft Learn: `JOBOBJECT_BASIC_ACCOUNTING_INFORMATION`](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_basic_accounting_information)
3. [Linux kernel documentation: Control Group v2](https://docs.kernel.org/admin-guide/cgroup-v2.html)
4. [Microsoft Learn: NtQuerySystemInformation](https://learn.microsoft.com/en-us/windows/win32/api/winternl/nf-winternl-ntquerysysteminformation)
5. [Microsoft DirectX blog: GPUs in the Task Manager](https://devblogs.microsoft.com/directx/gpus-in-the-task-manager/)
6. [Microsoft Learn: GPU process memory counters report incorrect values](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/gpu-process-memory-counters-report-wrong-value)
7. [NVIDIA: NVML API reference, process information](https://docs.nvidia.com/deploy/nvml-api/structnvmlProcessInfo__v1__t.html)
8. [psutil documentation: temperatures, battery and CPU frequency](https://psutil.readthedocs.io/latest/blog/2017/sensors-support.html)
9. [Microsoft Learn: CPU usage exceeds 100% in Task Manager](https://learn.microsoft.com/en-us/troubleshoot/windows-client/performance/cpu-usage-exceeds-100)
10. [Windows Latest: Task Manager's new CPU usage formula in Windows 11 24H2](https://www.windowslatest.com/2025/05/26/windows-11-24h2s-task-manager-new-cpu-usage-formula-rolls-out-to-everyone)
