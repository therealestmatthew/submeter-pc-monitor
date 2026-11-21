# Working notes of the lead reviewer

Not the report. These notes exist so that the session can find its place after an interruption, as the execution prompt asks. The report is `01-adversarial-review.md`. Delete this file once the report is written, or keep it as the trail.

## Where the session stands

- Stage: stage 1 report written to `01-adversarial-review.md` (R38 to R153). **Stopped for the owner's rulings.** Next: record them in `02-rulings.md`, then follow "After my rulings" in the execution prompt. Nothing outside `docs/review/` has been changed.
- Machine: Linux (Ubuntu 24.04, kernel 7.0, 8 logical cores), **not** the Windows 11 computer the prompt assumes. Windows claims are checked against vendor documentation or marked suspected.
- Git: `4823b09 Package as delivered`, `bfcb188 Lock dependencies`. `origin` is set and `git ls-remote origin` answers (empty, public repository). The push of `main` was refused by the session's permission system and is still owed.
- Ground output is kept in `docs/review/ground/`. Timing probes run on a quiet machine are in `docs/review/probes/measure/`.
- Eight lens reviewers write their probes under `docs/review/probes/<lens>/`. What they return is a lead, to be re-checked before it enters the report.
- 2026-11-21: the first lens run (`wf_afb696f6-921`, started 22:00 on 20 November) returned nothing. Lenses A to E made three attempts of about an hour each, and every attempt was cut off by the Fable usage limit, the last at 07:47. F, G and H never started. Their probe files survived. The review was resumed on Opus from another Claude Code session (`wf_5d17d3de-547`). Each interrupted lens got a digest of its earlier attempts, and the lens prompts were otherwise unchanged.

## Numbers measured here

| What | Result | Source |
| --- | --- | --- |
| Baseline checks | ruff clean, format clean (51 files: 26 Python, 25 Markdown), mypy clean on 25 files, 20 tests pass | `ground/*.txt` |
| `platform_check.py` | 6 results, 0 failed; 452 processes, 298 restricted, 0 without a readable command line | `ground/platform-check.txt` |
| psutil snapshot | median 111.2 ms, worst 121.8 ms, 447 processes; 74.6 ms per 300; 11.1% of a core at 1 s | `probes/measure/snapshot_cost.out.txt` |
| Direct `/proc`, stat only | median 11.2 ms for 448; 7.5 ms per 300 | same |
| Direct `/proc`, stat + statm + io | median 23.2 ms for 449; 15.5 ms per 300 | same |
| Whole baseline tick, no storage | median 125.9 ms; 12.6% of a core at 1 s | same |
| Collector-shaped process, 120 ticks | resident 39 MB, unique 35 MB; 14.1% of a core at 1 s | `probes/measure/collector_footprint.out.txt` |
| Raw store | 12.6 process rows and 3 workload rows a tick; 120 bytes a row; 3.0 M rows and 0.36 GB per 48 h | same |
| Reconciliation, quiet | 1.7% of capacity missing | `probes/measure/reconcile_under_spawn.out.txt` |
| Reconciliation, one spawner | 13.7% of capacity missing (72% of busy time) | same |
| Reconciliation, four spawners | 51.6% of capacity missing | same |

Other facts about this machine: the session's cgroup is under `user@UID.service/app.slice/`; delegated controllers are `cpu memory pids` (no `io`); PSI is readable; time zone is UTC-5; process names here include `.postgres-wrapp`, `Isolated Web Co` and `Web Content`, which are truncated or renamed and are not executable file names. uv resolved the environment to Python 3.14.5 because nothing pins a version.

## Leads from the lead reviewer's own reading

Each is to be confirmed or refuted before it enters the report. File and line are where the evidence is.

1. **Reconciliation cannot hold for polled workloads.** CPU time of processes that exit between samples is in the machine's busy time and in no process. `docs/17-build-prompt.md:98`, `docs/01-overview.md:8`, `docs/15-phases-and-decisions.md:13`. Nothing says how the System bucket is derived, so the missing time either breaks the 2% invariant or hides in System. Measured above.
2. **A gap becomes covered time with zero use.** `sampler.py:59` gives a gap batch the whole gap as its interval; `rules.py:219-221` copies that interval into each workload sample; `raw.py:112-129` stores it; `rollup.py:53` adds it to covered seconds, and `rollup.py:60,70-71` weight mean memory and both histograms by it. `WorkloadSample` has no gap flag.
3. **The gap threshold is a fixed 30 s** (`sampler.py:39,55`) while the allowed settings reach 60 s for the idle and cold intervals and a tenfold on-battery multiplier (`config.py:46-51,92`, `docs/08-configuration.md:62-63,71`). Such an interval is zeroed. `cli.py:79` lets `top --seconds` reach 60, so 31 to 60 prints zeros, and step 5 of `docs/reference/windows-priorities.md` uses 60.
4. **Attribution is recomputed from nothing each batch** (`rules.py:137-163`). A child that inherited its workload loses it when the parent exits. `raw.py:133,159` records a process's workload once, so the process table and the workload totals then disagree.
5. **`redact_cmdline` misses common forms** (`redact.py:74-82`): a header value such as `Authorization: Bearer x`, `-u user:password`, `-pSECRET`, `--env=NAME=secret`, `/pass:x`, a connection string, a URL query token after the first parameter, a token as the URL user.
6. **The switching rule cannot be applied as written.** `docs/11-language.md:21`, `docs/17-build-prompt.md:56`. Phase 0 has only the psutil provider, which the brief already expects to fail; the bulk providers are phase 1. The rule does not say which part of a tick, which provider, which memory figure.
7. **The sampler assumes every snapshot is complete** (`sampler.py:49,65`). A hot-only snapshot makes cold processes look exited, drops their CPU time and counts them as started again. `SampleBatch` has one interval for all processes (`models.py:126`).
8. **Power loss can cost more than 5 seconds** with WAL and `synchronous=NORMAL` (`raw.py:69-71`, `docs/17-build-prompt.md:138`) unless something syncs the log every 5 s. To be settled from sqlite.org.
9. **Two rules decide which bucket a sample is in.** `raw.py:199` selects by end time; `rollup.py:110` assigns by midpoint. A per-bucket query then yields a stray partial bucket.
10. **"50 MB an hour within 2 hours" sits on both thresholds** (`docs/01-overview.md:18`, `growth.py:73,78`), and `50MB/h` is binary in the settings (`units.py:29-35`). The plateau test (`growth.py:45-53`) may clear a staircase leak.
11. **Dependencies.** `AGENTS.md:46` allows three. `docs/17-build-prompt.md:38-39,142` names FastAPI, a WebSocket, uPlot and Parquet; MCP, NVML and desktop notifications also need something.
12. **Phase 7 has a gate and no component, route or schema** (`docs/15-phases-and-decisions.md:35-37`, `docs/13-build-list.md`). A guest reporting to the host conflicts with loopback only.
13. **Job Objects.** Not allowing breakaway (`docs/17-build-prompt.md:69`) may make a launched program's own process creation fail. The name of a job may go when its last handle closes, which would decide "a holder, or the collector" (`docs/17-build-prompt.md:67`). Suspected.
14. **cgroups here.** `io` is not delegated, so a group's I/O total is not available from the kernel. A cgroup made with mkdir is not removed when empty, against R15.
15. **The records cannot say "unavailable".** `models.py:79,82` (CPU and memory are required numbers), `psutil_provider.py:66` (zeros when denied), `rules.py:208-209` (unreadable I/O added as zero), against `AGENTS.md:44`.
16. **Data folders and files are not private on Linux.** `files.py:119` and `raw.py:66-68` use default modes, against `docs/17-build-prompt.md:146`.
17. **No Python version is pinned.** The brief says 3.12; this checkout runs 3.14.5.
18. **Settings that are not checked.** Profiles that are not selected (`config.py:293-299`), alert metric ids (`config.py:153`), verdict thresholds (`config.py:143`), negative or NaN bare numbers for unranged durations and sizes (`config.py:97-99`, `units.py:44-45`), a settings path that does not exist (`cli.py:47`).
19. **Phase 0 asks for things that need later phases:** a working day of measurement, the full capability matrix, a VRAM check that needs a GPU. "`doctor` is correct" has no oracle.
20. **Phase 1 gate.** A 30-minute soak cannot hold a full hourly bucket; "within 5% of kernel counters" compares a source with itself on Linux; runners do not have 300 processes.
21. **Retention belongs to the server** (`docs/17-build-prompt.md:53`). With the server down, raw files grow without limit. Nothing says a raw file may not be deleted before it is rolled up.
22. **What MCP withholds differs:** command lines (`docs/08-configuration.md:125`, the phase 6 gate) against command lines and working directories (`docs/17-build-prompt.md:148`).
23. **Small differences between documents:** 85% and 86% thresholds (`docs/07-analysis.md:97-98`, `docs/02-what-it-looks-like.md:74-75`); the `why` sample shows 91% CPU time and 93% reconciled (`docs/03-cli-output.md:33,43-44`).
24. **`ProcessKey.started` is a float** (`models.py:68`, `raw.py:38,47`). Whether two providers, or two runs, produce the same value is untested.
25. **The field called `exe` holds psutil's `name()`** (`psutil_provider.py:92`), which on Linux is a thread name cut to 15 characters.
26. **Rule 3 hazards in the named stack:** FastAPI's documentation page loads assets from a CDN; a chart library must be vendored; `docs/brief.html` loads web fonts.
27. **How the dashboard gets the token is not specified,** nor how a browser WebSocket presents it.
28. **A wall clock stepped backwards** is not a gap (`sampler.py:55`), and `raw.py:103,113` use `INSERT OR REPLACE` on the timestamp.
29. **`choose_tier` decides from the retention settings,** not from what is on disk (`query.py:40-45`).
30. **A workload row mixes intervals** once cold processes are sampled every 10 s: cores in use for that tick is overstated.
31. **psutil on Windows** may run a system-wide query for each process it cannot open, and its per-core sum may count interrupt and deferred-call time twice (`psutil_provider.py:114-122`). Suspected.
32. **A scheduled task at logon** may need administrator rights. Suspected.
33. **"GB" is binary in settings and decimal in the brief's arithmetic.**
34. **Never specified:** how System is derived, what makes a period idle or active, which bucket an epoch change falls in, who deletes a run file.
35. **The bucket record holds about a third of the metric catalogue** (`models.py:150-175`, `docs/06-storage.md:77-94`), and the brief assumes 250 bytes a bucket.
36. **Other users' command lines are readable on Linux,** against `docs/10-known-limits.md:16`.
37. **ruff 0.17 formats code blocks in Markdown,** so a document can fail `ruff format --check`.
38. **A session longer than raw retention** cannot be summarised exactly at its end unless totals are accumulated as it runs.
