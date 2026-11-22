# Language recommendation

> Submeter build brief · Part 2, the design · [Index](README.md)

**Recommended: Python 3.13 for all of version 1, with the collector isolated as its own process**

Python 3.13 is the oldest version accepted, because from 3.13 `time.monotonic()` on Windows resolves 1 microsecond instead of 15.6 ms, which matters at intervals as short as 250 ms.

Once the collector takes one bulk snapshot per tick, its cost is the system call, not the interpreter. Python then gives you the strongest analysis libraries, a codebase you can review yourself, and one typed language for a coding agent to keep consistent. The system call is most of the cost only with the Windows bulk snapshot. On Linux each process is read on its own, through psutil in version 1 and /proc later. With a direct /proc reader, measured on Linux with the baseline code, the Python work after the snapshot (deltas, attribution and raw-store writes) was about half of each tick, 20 of 36 ms at 300 processes. With psutil, the version 1 reader, the snapshot itself was about 75 of the 95 ms.

The collector and the server share nothing but the database schema. If phase 0 shows Python missing the budget, only the collector is rewritten in Rust and nothing else changes.

| Option | Strength | Cost | Call |
| --- | --- | --- | --- |
| Python throughout | Fastest to build and review. Best fit for analysis, API and reports | Higher memory. Per-process loops are slow, so the bulk path is mandatory | Start here |
| Rust collector, Python elsewhere | Lowest overhead on the hot path. Direct access to Windows and Linux kernel APIs. One small binary | Two toolchains. Slower iteration on the part that changes most early on | Fallback |
| Rust throughout | Smallest footprint overall | Analysis, API and reports take far longer to write. Little gain off the hot path | No |
| Go throughout | Easy deployment, good concurrency | A new language for you with no analysis advantage over Python | No |
| C# and .NET | Best Windows API coverage | Weak fit for the Linux half of the brief | No |

## When to switch the collector to Rust

- In phase 0, the bulk-snapshot probe runs the collector (snapshot, deltas, attribution and raw-store writes) for 10 minutes on the owner's Windows machine, with the provider that will ship and with the psutil fallback. It reports the process count and the cost per process, so that the figures for 300 processes can be derived, the collector's CPU time as a share of one core at the default active interval (2 s) and idle interval (5 s), and its private bytes.
- Switch if, for 300 processes at the default intervals with the provider that will ship, that CPU share is over the overhead budget (3% of one core active, 1% idle), or the private bytes are over 80 MB. The psutil fallback's figures are reported, not judged.
- You add deep tracing later. ETW and eBPF deliver thousands of events per second, which Python cannot keep up with.

The report's charts are plain JavaScript with a canvas chart library, inlined in the HTML file, so nothing needs a Node build step. The live dashboard of version 1.1 is built the same way.
