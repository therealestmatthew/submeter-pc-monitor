# Language recommendation

> Submeter build brief · Part 2, the design · [Index](README.md)

**Recommended: Python 3.12 for all of version 1, with the collector isolated as its own process**

Once the collector takes one bulk snapshot per tick, its cost is the system call, not the interpreter. Python then gives you the strongest analysis libraries, a codebase you can review yourself, and one typed language for a coding agent to keep consistent.

The collector and the server share nothing but the database schema. If phase 0 shows Python missing the budget, only the collector is rewritten in Rust and nothing else changes.

| Option | Strength | Cost | Call |
| --- | --- | --- | --- |
| Python throughout | Fastest to build and review. Best fit for analysis, API and reports | Higher memory. Per-process loops are slow, so the bulk path is mandatory | Start here |
| Rust collector, Python elsewhere | Lowest overhead on the hot path. Direct access to Windows and Linux kernel APIs. One small binary | Two toolchains. Slower iteration on the part that changes most early on | Fallback |
| Rust throughout | Smallest footprint overall | Analysis, API and reports take far longer to write. Little gain off the hot path | No |
| Go throughout | Easy deployment, good concurrency | A new language for you with no analysis advantage over Python | No |
| C# and .NET | Best Windows API coverage | Weak fit for the Linux half of the brief | No |

## When to switch the collector to Rust

- One full sample of 300 processes takes more than 10 ms in phase 0.
- The collector process holds more than 80 MB.
- You add deep tracing later. ETW and eBPF deliver thousands of events per second, which Python cannot keep up with.

The report's charts are plain JavaScript with a canvas chart library, inlined in the HTML file, so nothing needs a Node build step. The live dashboard of version 1.1 is built the same way.
