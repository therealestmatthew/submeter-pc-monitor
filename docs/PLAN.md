# Submeter version 1: the plan

This is the formal plan for building Submeter version 1, written in stage 2 of `prompts/01-execution-prompt.md`. It starts from the brief as it stands after the owner's rulings on the stage 1 review (`docs/README.md` and `docs/01` to `docs/17`) and from the tested baseline under `src/` and `tests/`. It says what "version 1 is done" means in terms that can be tested, which rulings changed the brief, how the work divides into phases, waves and tasks, which task owns each file, the order the dependencies force, how each phase gate is run and judged, how the work is tested, the risks, how every promise of the brief maps to a task and a test, how many waves and sessions to expect, and which questions the owner still has to answer. The owner's rulings in `docs/review/02-rulings.md` override this plan wherever the two disagree; such a disagreement is a defect in the plan, which the lead corrects. Every figure the review measured came from its Linux machine and is marked as such where it bears on a Windows choice.

## Contents

1. [The objective, and what "version 1 is done" means](#1-the-objective-and-what-version-1-is-done-means)
2. [The rulings that changed the brief](#2-the-rulings-that-changed-the-brief)
3. [The work breakdown](#3-the-work-breakdown)
4. [File ownership map](#4-file-ownership-map)
5. [Dependency graph, waves and width](#5-dependency-graph-waves-and-width)
6. [The gates](#6-the-gates)
7. [The test strategy](#7-the-test-strategy)
8. [Risk register](#8-risk-register)
9. [Traceability](#9-traceability)
10. [Cadence](#10-cadence)
11. [Open questions for the owner](#11-open-questions-for-the-owner)

## 1. The objective, and what "version 1 is done" means

### 1.1 The objective

Build Submeter version 1 as the brief now specifies it: `docs/README.md` and `docs/01` to `docs/17`, with every finding the owner accepted on 21 November 2026 written in (`docs/review/02-rulings.md`). Version 1 is three programs that share only files on disk, the collector (`submeter-collector`), the server (`submeter-server`) and the launcher behind `submeter run`, and the `submeter` command line with a self-contained HTML report. Together they attribute CPU time, memory, disk I/O and, on Windows, GPU load to named workloads on one machine. Windows 11 is the target and the only system with the platform layer (Job Object accounting, the bulk process snapshot, system counters, autostart); Linux runs the same code polled through psutil and is tested in CI (R151; `docs/17-build-prompt.md:21`). 22 of the 26 numbered components are in version 1; 05, 20, 21 and 25 are not (`docs/13-build-list.md:5`). The three fixed rules of `AGENTS.md:9-11` hold throughout. When goals conflict, attribution ranks above live diagnosis, which ranks above trends (`docs/17-build-prompt.md:15`), and the first priority is never to show a wrong number: a metric that cannot be measured is recorded as unavailable (`docs/17-build-prompt.md:27-31`).

### 1.2 Done, in terms that can be tested

Version 1 is done when every row below holds at one commit on `main`, the owner has approved all six phase gates, and `docs/STATUS.md` records the result. Each row names the gate item or test that proves it. Gate items are named as in section 6: `P<phase>.<n>` for each phase's items and S1 to S5 for the criteria every gate shares. "Owner" is the owner's personal Windows 11 computer, the machine of record, used as the signed-in standard user, whose output is the evidence; the owner also runs P0's owner tasks and, from P1, each gate's owner check run on the work PC and reports each result in one word, and nothing from the work PC is committed or pushed (section 3.1, Owner tasks; `docs/STATUS.md` 7.10); CI-W and CI-L are the hosted Windows and Linux runners, which are administrators or have passwordless sudo and so cannot prove anything about privilege (`docs/15-phases-and-decisions.md:25`).

| Row | Condition | Proved by | Where |
| --- | --- | --- | --- |
| D1 | Job 1, tagged runs on Windows: a tagged tree that spawns 500 sub-second children is charged within 2% of the load generator's own accounting; the final totals survive the tree's exit; `submeter run` returns with the command's exit code while processes it left behind are still counted; a grandchild started in the command's first millisecond is in the job; a nested run records its parent, the parent's total excludes the child's and the two together are within 2%; a direct child that asks to break away gets an error, which is recorded; a grandchild started through node and then bash stays in the group; an agent reads its own run's cost with `submeter cost --run "$SUBMETER_RUN" --json` and the output holds no command line or working folder | gate P1.1 to P1.10 (harness P1-W3-T1, owner run P1-O1) | Owner; CI-W as a regression test |
| D2 | On Linux, `submeter run` says tagged runs are unavailable and runs the command polled | gate P1.11 | CI-L |
| D3 | Job 1, reconciliation: attributed + unattributed + system + restricted + not seen by polling + idle equals capacity within 2% in every 60 s window, and not seen by polling is never below −2% of capacity; on the recorded quiet fixture, not seen by polling stays under the share fixed before the recording (5% of capacity unless the owner sets another, section 6.6) | gate P2.3, P2.4 (P2-W6-T3; P2-O2 on the owner's machine) | CI-W, CI-L, Owner |
| D4 | Per-process CPU of every load-generator burner set above 10% of a core (15%, 25%, 50% and 100%) agrees with the burner's own accounting within 5% or 0.05 s, whichever is larger, over 10 minutes | gate P2.2 | CI-W, CI-L; Owner with the bulk provider |
| D5 | The overhead budget: with 300 processes running, every Submeter process together under 1% of one core at the idle cadence and under 3% at the active cadence; collector and server together under 150 MB (157,286,400 bytes; private bytes on Windows, USS on Linux) | gate P2.1 and P3.5 (30-minute CI soaks); gate P2.6 (the owner's 24-hour soak, with the memory-growth limit section 6 sets: under 10,485,760 bytes); gate P4.6 and P5.4 (the soak again at P4 and P5, P4-W4-T2, P5-W3-T2); gate P5.5 (a final 24-hour soak if the owner keeps it, P5-O2) | CI-W, CI-L, Owner |
| D6 | Crash safety: killing the collector mid-write loses no tick it had committed and `PRAGMA integrity_check` returns ok; after each soak every file passes the integrity check and the only gaps are those the collector recorded | gate P2.5 (P2-W6-T1), P2.6 | CI-W, CI-L, Owner |
| D7 | History: CPU-hours per hour from the hourly tier within 0.1% of the raw sum of samples whose end falls in that hour, with whole and fractional ticks; deleting a raw day with its `-wal` and `-shm` frees its space once no reader holds it; a restarted collector re-attaches to live groups; a session's cost reads the same before and after its raw data is deleted, including a session longer than raw retention | gate P3.1 to P3.4 (P3-W6-T1) | CI-W, CI-L; P3.3 also on Owner |
| D8 | Job 2: `submeter why` gives a verdict with its evidence in under 2 s; Inconclusive when two rules match, with under 60 s of data, or below `verdict.min_confidence`; each verdict class passes a trigger and a quiet fixture; on Linux it never reads No bottleneck | gate P4.1, P4.5 (P4-W4-T1, P4-O1) | CI-W, CI-L; timing on Owner |
| D9 | Job 3: a leak of 75 MiB an hour (78,643,200 bytes an hour) flagged within 2 h 5 min; the noisy browser warm-up of `docs/07-analysis.md:24` not flagged; the leak that grows in 256 MB steps every 2 hours flagged; each at the seed count and pass rate of decision B14; findings listed by `submeter findings` and shown by `submeter why` and the report | gate P4.2 to P4.4; gate P4.1 (the findings check in P4-W4-T1); gate P5.1 (a stored finding shown in the report, P5-W4-T1) | CI-W, CI-L |
| D10 | Sessions without an API: `submeter session start` and `stop` write marker files that the server reads; `submeter cost` and `submeter diff` read sessions | tests of P3-W2-T3, P3-W4-T3, P3-W5-T1, P4-W3-T2 | CI-W, CI-L |
| D11 | The report: `submeter report` writes one self-contained HTML file for a session or a range, with a meta Content Security Policy `default-src 'none'` and a hash for each inline block, no `http://` or `https://`, each chart naming its tier and resolution and marking each epoch boundary with its reason, each workload with its accounting source and its GPU load where present, the four fixed workloads, the known-limit notes beside the figures they affect, and no command line | gate P5.1 (P5-W4-T1) | CI-W, CI-L |
| D12 | GPU load by engine type and the adapter's VRAM pass their recorded fixtures and degrade cleanly when their source is absent; `docs/STATUS.md` names each provider that never ran on real hardware | gate P5.2, P5.3 | CI-W, CI-L; fixtures from Owner |
| D13 | A metric that cannot be measured is recorded as unavailable, never as zero or an estimate: no strict expected failure remains (R61's is removed by P0-W5-T1); provider, aggregate, raw, rollup, CLI and alert tests assert None and n/a | gate S2; tests of P0-W5-T1, P2-W2-T2, P2-W5-T2, P4-W2-T3, P5-W1-T2 | CI-W, CI-L |
| D14 | The fixed rules: no call in `src` that changes a process, asks to elevate or opens a network client; runtime dependencies pydantic, psutil and typer only; a tagged job's limit flags read back as 0; in every soak each Submeter process holds 0 sockets, and in the owner's soaks a token that is not elevated (CI-W's runner is an administrator, so its soak records elevation without judging it) | P0-W3-T3 on every push (gate S1); P1-W1-T4 and gate P1.12; the soak checker of P2-W5-T4 (gate P2.1, P2.6, P3.5, P4.6, P5.4, P5.5) | CI-W, CI-L, Owner |
| D15 | Command lines are redacted before anything is written: a canary argument appears in no byte of any `.db`, `-wal` or log file, nor in `cost --json` or the report | gate P2.7 (the canary check of P2-W6-T3); gate P1.10; gate P5.1 | CI-W, CI-L, Owner |
| D16 | The checks: the seven commands of `AGENTS.md:25-33` exit 0 on CI-W and CI-L at the final commit, and on the owner's machine | gate S1 | CI-W, CI-L, Owner |
| D17 | Every component of `docs/13-build-list.md` in version 1 is built by the tasks of section 3.2, the four that are not are absent, and every row of the traceability table (section 9) points to a passing test or to "not in version 1" | section 9; the self-check recorded in section 9.10, run again at P5 | — |
| D18 | `docs/STATUS.md` says what works, what was verified and how, and what could not be verified, at every gate; the owner has approved the P0 to P5 gates | gate S3 | — |

The floor of version 1 (`docs/15-phases-and-decisions.md:71-81`) is covered by these rows: tagged runs by D1 and D2; the collector, raw store, four fixed buckets and the not-seen figure by D3 and D4; the verdict, `why` and the adapter's VRAM by D8 and D12; the leak check and `submeter findings` by D9; sessions by marker files by D10; unavailable never zero by D13; the overhead budget by D5; redaction before anything is written by D15.


## 2. The rulings that changed the brief

On 21 November 2026 the owner answered the stage 1 review with "Accept all." (`docs/review/02-rulings.md:7`). Every finding R38 to R153 took its recommended disposition and, where it needed a decision, the recommended option: 97 `fix now`, 13 `plan` and 6 `defer`. Each accepted finding that changes the design was written into the document that states it, one commit per finding: 242 commits since the rulings (`git log --oneline 561a266..HEAD`), every one but two named by its finding. The 94 entries under "How the rulings combine" say how rulings that contradict, narrow or overtake one another were applied together; 32 of them carry an **Assumption** the owner has not confirmed, and section 11 lists each.

Code: the `fix now` code changes were made test first, with their evidence in `docs/review/fixes/`. Seven moved to the plan because they grew past about fifty changed lines (`docs/review/02-rulings.md:276-286`): R38, R39, R55, R56, R57, R111 and R145; section 3.3 names the task that now carries each. Seven were kept although slightly over: R58 at 62 changed lines, R59 at 57, R100 at 55, R97 at 54, R47 at 52, R71 at 52 and R99 at 51. AGENTS.md changed for R103 (line 43 no longer says "put in a finding"), R107 (line 44, anonymised fixtures) and R134 (lines 30-31, the two platform mypy checks); three more wordings wait for the owner (R108, R112 and I94; decision B10).

How to read the tables: findings are grouped by subject. "Ruling" is the disposition and, where there was one, the option chosen. "What the brief now says" is the subject line of the finding's first commit that changed a document, with the number of further document commits in brackets. "Documents changed" gives `docs/NN-*.md` by its number and other files by name. "Code" says what the finding left in the code: "kept" lists the source files of a `fix now` change that stayed, with "and tests" when tests changed too; an arrow points to the task of section 3 that carries a moved change or a `plan` finding; "none" means no code changed, not that no work is left (section 9 traces the remaining work of every finding). Where a later ruling overtook an option, as R145 did for R92's minute files, the entry under "How the rulings combine" says how the two were applied, and the brief follows that entry.


### Scope of version 1, phases and gates

| Finding | Ruling | What the brief now says (first document commit) | Documents changed | Code |
| --- | --- | --- | --- | --- |
| R83 | fix now | Use the load generator's own accounting as the gate reference | 13, 15, 16, 17 | none |
| R117 | plan | Name the soak's pass criteria and the hourly check's fixture | 15, 17 | plan → P2-W5-T4, P3-W1-T2, P4-W1-T2 (with section 6) |
| R118 | fix now | Say what CI proves and which tests run on the owner's machine | 15, 17 | none |
| R119 | fix now: directly from the store files, not through the API | Add the server program as a component and say the CLI reads files (+1 more) | 01, 13, 14, 15, 17, docs/README | none |
| R136 | fix now | Give the tools beside the code their phases, and name the generator | 13, 15, 17 | none |
| R137 | plan | Save phase 0's Windows output under review/ground-windows (+1 more) | 15, 17, docs/README, windows-priorities | plan → P0-W1-T2, P0-O1, P0-O2 (with section 8) |
| R140 | defer: defer it past v1 | Defer the WSL2 guest collector and drop phase 7 | 10, 13, 15, 16, 17, windows-priorities | none |
| R141 | fix now: tagged runs become phase 1 | Build tagged runs first, as phase 1 (+1 more) | 01, 06, 13, 14, 15, 17 | none |
| R142 | fix now: they choose only which costly extras are read; every process is read every tick; default active interval 2 s | Cut hot and cold sets; read every process, default 2 s active (+1 more) | 02, 03, 04, 05, 06, 08, 10, 12, 13, 14, 16, 17, docs/README, examples/submeter.toml | kept: `collector/sampler.py`, `core/config.py` and tests |
| R143 | defer: defer it; agents use `cost --json` | Defer the MCP server; agents read cost --run --json | 04, 05, 08, 13, 14, 15, 16, 17 | none |
| R144 | fix now: drop it; export JSON and CSV | Drop Parquet export; export JSON and CSV | 13, 17 | none |
| R145 | fix now: cut it; keep raw and hourly | Cut the minute tier, keeping raw and hourly (+1 more) | 03, 04, 05, 06, 08, 13, 14, 16, 17, examples/submeter.toml | built, undone; moved to plan → P0-W3-T1 |
| R146 | defer: defer both, and rank the jobs attribution > diagnosis > trends | Defer baseline anomaly and slow growth; rank the three jobs (+1 more) | 03, 04, 06, 07, 08, 13, 14, 15, 16, 17, docs/README, examples/submeter.toml | none |
| R147 | fix now: three decision probes on the owner's machine, plus CI | Make phase 0 three decision probes on the owner's machine plus CI | 09, 13, 15, 17, windows-priorities | none |
| R148 | defer: GPU load and adapter VRAM only | Trim phase 5 to GPU load and adapter VRAM (+1 more) | 01, 03, 04, 05, 06, 07, 08, 09, 10, 13, 15, 16, 17, windows-priorities | none |
| R149 | fix now: read only at start; no profiles; no per-session interval | Read settings only at start; no profiles or session interval (+1 more) | 08, 13, 14, 17, examples/submeter.toml | kept: `cli.py`, `core/config.py` and tests |
| R150 | defer: CLI plus a static HTML report; dashboard and API move to v1.1 | Make v1 CLI-first; the API and dashboard move to v1.1 (+2 more) | 01, 02, 04, 05, 06, 07, 08, 10, 11, 13, 14, 15, 16, 17, docs/README, windows-priorities | none |
| R151 | plan: Windows only, with Linux polled and covered by CI | Build the platform layer for Windows only; Linux runs polled (+2 more) | 01, 04, 05, 06, 07, 08, 09, 10, 11, 13, 14, 15, 16, 17, examples/rules.toml, windows-priorities | plan → P1-W2-T2, P2-W2-T2, P4-W2-T2 |
| R152 | defer: findings only; no desktop notifications in v1 | Defer desktop notifications; a firing alert rule raises a finding | 04, 08, 13, 15, 17, examples/submeter.toml | none |
| R153 | plan: adopt the floor and the six-phase list once the cuts are ruled | Write the six-phase list and the floor of version 1 (+1 more) | 01, 13, 14, 15, 17, README, docs/README | plan → section 1.2 and the phase list of section 3 |

### Process reading, attribution and reconciliation

| Finding | Ruling | What the brief now says (first document commit) | Documents changed | Code |
| --- | --- | --- | --- | --- |
| R38 | fix now | Mark a gap past three expected intervals and keep its deltas | 05, 14, 17, windows-priorities | built, reverted; moved to plan → P2-W1-T2 |
| R39 | fix now | Count a gap's sums but none of its time as covered (+2 more) | 05, 06, 14, 17, windows-priorities | reverted; moved to plan → P2-W1-T2 |
| R40 | fix now | Subtract a reaped child's last-seen CPU and I/O from its reaper | 09, 14, 17 | kept: `core/models.py` and tests |
| R41 | fix now | Exclude Windows pid 0 and check process CPU against busy time | 14, 17, windows-priorities | kept: `providers/psutil_provider.py`, `scripts/platform_check.py` and tests |
| R42 | plan: sum of readable members plus the unreadable count, labelled partial (option b) | Mark a figure some processes cannot give as partial, none as n/a | 06, 14, 17 | plan → P0-W5-T1, P2-W2-T2 |
| R44 | fix now: they choose only which costly extras are read; every process is read every tick; default active interval 2 s | No commit of its own: overtaken by R142, which cut hot and cold sets (I19). | none | none |
| R45 | fix now: its own visible term, "not seen by polling" (option a) | Define System and Idle, and add CPU time not seen by polling (+1 more) | 02, 03, 04, 12, 15, 16, 17, docs/README | kept: tests only |
| R46 | plan: sum members with a reading, labelled partial; measure full PSS in phase 0 (option a) | Make a workload's memory total the sum of members with a reading | 06, 08, 14, 15, 17 | plan → P0-W2-T4, P0-W5-T1, P2-W2-T2, P2-W3-T3 |
| R47 | fix now: the explicit rule wins and the change is recorded | Keep a process's workload for life unless it execs into a rule | 14, 17 | kept: `attribution/rules.py` and tests |
| R55 | fix now | Stamp batches on the interval clock and record clock steps (+1 more) | 04, 06, 08, 14, 17 | built, reverted; moved to plan → P2-W4-T4, P2-W3-T1 |
| R56 | fix now | Make a process's start time the platform's integer stamp | 10, 14, 17 | not attempted; moved to plan → P0-W4-T1 |
| R57 | fix now | Never use a stand-in zero as a CPU baseline, and cap each delta | 14, 17 | moved to plan → P0-W4-T1 |
| R58 | fix now | Keep a process when one read fails, and keep zombies (+1 more) | 14, 17, windows-priorities | kept: `providers/psutil_provider.py` and tests |
| R59 | fix now | Detect suspend with a clock that stops during it | 14, 17, windows-priorities | kept: `collector/sampler.py`, `core/models.py`, `providers/psutil_provider.py` and tests |
| R60 | plan: yes, unless phase 0 shows the cost breaks the budget | Place unseen Linux CPU by cgroup, if phase 0's cost allows | 09, 15, 17 | plan → P0-W2-T4, P2-W4-T2 |
| R61 | fix now | Report a tagged workload's group totals, not its polled sum (+1 more) | 05, 14, 17 | kept: `attribution/rules.py`, `core/models.py` and tests |
| R62 | fix now: overrides the global setting in both directions | Define include_children, which overrides inherit_from_parent | 08, 14 | kept: `attribution/rules.py` and tests |
| R63 | fix now | Match exe on the executable file name and add a name condition | 04, 08, 14, 17, examples/rules.toml | kept: `attribution/rules.py`, `collector/sampler.py`, `core/models.py`, `providers/psutil_provider.py` and tests |
| R64 | fix now | Count Linux kernel threads as System, and state what Linux reads (+2 more) | 10, 14, 17 | none |
| R65 | fix now | Label System counters and Restricted partial; Restricted memory n/a (+2 more) | 02, 03, 10, 14 | none |
| R66 | fix now | State the Linux polled undercount of short-lived children | 10, 17 | none |
| R70 | fix now | Say the psutil fallback shares the snapshot's call | 14, 16, 17 | kept: `core/models.py`, `providers/psutil_provider.py`, `store/raw.py` and tests |
| R76 | fix now | State the USS reading's cost and guard it before the intervals | 08, 15, 17 | none |
| R77 | fix now: do not keep them; name only (option a) | Keep only the name of another user's process on Linux (+2 more) | 02, 09, 10, 14, 17 | kept: `providers/psutil_provider.py` and tests |
| R78 | fix now | Add the measured Linux costs and time the whole tick in P0 (+1 more) | 08, 15, 17 | none |
| R79 | fix now: use the overhead budget itself, not the 10 ms rule | Make the overhead budget the Rust trigger, measured over 10 min (+1 more) | 11, 15, 17, windows-priorities | kept: `scripts/platform_check.py` |
| R87 | fix now: every Submeter process | Make the overhead budget cover every Submeter process (+2 more) | 08, 14, 15, 17 | kept: `attribution/rules.py`, `cli.py` and tests |
| R123 | plan | Read a reused pid again through a fresh psutil object | 14, 17 | plan → P2-W2-T2 |
| R124 | fix now | Name Python 3.13 as the oldest version (+1 more) | 01, 11, 14, 17, windows-priorities | kept: `pyproject.toml` and tests |
| R125 | fix now | Add the per-core interrupt and DPC check to Windows item 3 | 15, 17, windows-priorities | none |
| R126 | fix now | Open processes with limited query access; check Defender's log (+1 more) | 15, 17, windows-priorities | none |
| R127 | fix now | Describe Windows private bytes as read from vms | 14, windows-priorities | kept: `providers/psutil_provider.py`, `scripts/platform_check.py` and tests |
| R128 | fix now: a share of busy CPU time | Report the WSL VM share against capacity in docs/10 and docs/13 | 10, 13 | none |

### Tagged runs, programs, locks and autostart

| Finding | Ruling | What the brief now says (first document commit) | Documents changed | Code |
| --- | --- | --- | --- | --- |
| R48 | fix now | Keep the job's handle in the holder, never in the collector | 17 | none |
| R49 | fix now | Record a nested run's parent and subtract child runs from it (+1 more) | 06, 15, 17 | none |
| R50 | fix now: Normal (5); state that rule 1 covers observed processes, not Submeter itself | Specify the Windows logon task, at normal priority | 15, 17 | none |
| R67 | fix now: the launcher reads its own /proc/self/io, with the gaps documented | Take tagged memory from USS; a Job Object keeps only peak commit | 04, 05, 09, 17 | none |
| R68 | fix now: keep it forbidden, document that some programs then fail under `submeter run` | Keep breakaway forbidden and state which programs then fail (+1 more) | 10, 15, 17 | none |
| R69 | fix now | Create the command inside the job with a job-list attribute (+1 more) | 13, 17 | none |
| R71 | fix now | Describe the lock's 5 s retry and the size check | 14, windows-priorities | kept: `scripts/platform_check.py`, `store/files.py` and tests |
| R105 | fix now | Name a lock holder only while it holds the lock; verify every stop | 14, 17, windows-priorities | kept: `store/files.py` and tests |
| R113 | fix now | Give the run file a live and a final state, one writer, a deleter (+2 more) | 05, 06, 13, 17 | none |
| R114 | fix now | State that every command reads files and reaches programs by file | 05, 17 | none |
| R120 | fix now: control files polled each tick | Make files the only channel to the programs and list them (+2 more) | 05, 06, 13, 17, docs/README | none |

### Storage, time and history

| Finding | Ruling | What the brief now says (first document commit) | Documents changed | Code |
| --- | --- | --- | --- | --- |
| R53 | fix now | Assign each sample whole to the bucket that holds its end | 06, 14, 15, 17 | kept: `store/raw.py`, `store/rollup.py` and tests |
| R54 | fix now | Store undecodable text escaped so one record never fails a tick (+1 more) | 14, 17 | kept: `store/raw.py` and tests |
| R88 | fix now: the server, after rollup, plus a 7-day safety cap in the collector (option b) | Delete raw days only after roll-up, with a 7-day collector cap (+2 more) | 04, 06, 14, 17 | kept: `store/files.py` and tests |
| R89 | fix now: relax the promise to "since the last checkpoint" (option c) | Promise no loss on a program crash, checkpoint loss on power cut | 15, 16, 17 | none |
| R90 | fix now | Write a quiet process's held CPU within 60 s and at each hour (+2 more) | 08, 14, 17 | kept: `store/raw.py` and tests |
| R91 | fix now | Read raw files read-only and quarantine them with their side files | 14, 17 | kept: `store/raw.py` and tests |
| R92 | fix now: delete minute files oldest first down to 7 days, then raise a finding | State the hourly bucket encoding and drop "enforced exactly" (+1 more) | 04, 06 | none |
| R93 | plan | Give every catalogue metric a nullable column; read all versions (+1 more) | 06, 15, 17 | plan → P2-W3-T1, P3-W1-T1 |
| R94 | fix now: configured settings, rules, providers, hardware and version, not cadence the collector changes itself (option a); no for alert, UI and verdict edits | Define epochs once; buckets keep core-seconds and interval bounds (+2 more) | 04, 06, 08, 14, 16, 17 | kept: `core/models.py`, `store/raw.py`, `store/rollup.py` and tests |
| R95 | fix now | No commit of its own: folded into R145 and R139 (I69). | none | none |
| R122 | fix now | Accumulate session and run totals while they run | 04, 05, 06, 15, 16, 17 | none |
| R129 | fix now | Bound the write-ahead log with journal_size_limit, not truncation (+2 more) | 06, 14, 17 | kept: `store/files.py`, `store/raw.py` and tests |
| R130 | fix now | Delete each raw day's -wal and -shm with its .db | 06, 14, 15, 17 | kept: `store/files.py` and tests |
| R131 | fix now | Take each reading's local day from the OS; note half-hour zones | 06, 14, 17 | kept: `analysis/growth.py` and tests |
| R132 | fix now: merge them from minute buckets, as the code does, and update the brief | No commit of its own: overtaken by R145, which cut the minute tier (I39). | none | none |
| R139 | fix now | Take raw coverage from the files on disk, not retention (+1 more) | 06, 14, 17 | kept: `store/query.py` and tests |

### Privacy and local security

| Finding | Ruling | What the brief now says (first document commit) | Documents changed | Code |
| --- | --- | --- | --- | --- |
| R96 | fix now: exe_only by default; scrub opt-in, documented as best-effort | Make exe_only the default redaction; scrub opt-in, best-effort (+1 more) | 04, 05, 06, 08, 13, 14, 17, examples/submeter.toml | kept: `core/config.py`, `privacy/redact.py`, `store/raw.py` and tests |
| R97 | fix now | Store the executable name in exe_only, never a rewritten argv[0] | 08, 14, 17 | kept: `privacy/redact.py`, `store/raw.py` and tests |
| R98 | fix now | Keep command lines, working folders and input values out of logs (+1 more) | 06, 13, 14, 17 | kept: `core/models.py` and tests |
| R99 | fix now | Match secret names as whole words and say rules see the live text | 08, 14, 17 | kept: `privacy/redact.py` and tests |
| R100 | fix now | Make Submeter's folders 0700 and its files 0600 from creation | 14, 17, windows-priorities | kept: `cli.py`, `store/files.py`, `store/raw.py` and tests |
| R101 | fix now | Say how each version 1.1 client carries the API token | 17 | none |
| R102 | fix now | Have version 1.1 clients confirm the listener before the token | 08, 17 | none |
| R103 | fix now | Keep command lines out of findings and working folders out of cost | 15, 17, AGENTS.md | none |
| R104 | fix now: host runs it through wsl.exe and reads stdout (option a) | No commit of its own: moot once R140 deferred the WSL guest collector (I76). | none | none |
| R106 | fix now | Validate workload names and reserve the names Submeter assigns (+1 more) | 08, 14, 17, README, docs/README | kept: `attribution/rules.py`, `core/config.py`, `core/names.py` and tests |
| R107 | fix now: in AGENTS.md (owner approval), repeated in docs/17 | Anonymise recorded fixtures before they are written | 17, AGENTS.md | none |
| R133 | fix now | Check redact patterns when settings load and apply them in scrub | 08, 14, 17 | kept: `core/config.py`, `privacy/redact.py`, `store/raw.py` and tests |

### Analysis, alerts and settings

| Finding | Ruling | What the brief now says (first document commit) | Documents changed | Code |
| --- | --- | --- | --- | --- |
| R51 | fix now | Make commit_fraction unavailable on Linux unless overcommit is 2 (+2 more) | 02, 08, 12, 17 | none |
| R52 | plan | Add noisy warm-up and staircase leak fixtures to the P4 gate | 14, 15, 17 | plan → P4-W1-T2, P4-W2-T1 |
| R80 | fix now: raise the acceptance rate (e.g. 75 MiB/h) and keep the 50 MiB/h threshold | Set the leak acceptance to 75 MB an hour within 2 h 5 min | 01, 06, 08, 15, 17 | none |
| R81 | fix now | Give the after-v1 slow-growth check its own slope and window (+1 more) | 08, 17 | none |
| R82 | fix now | Name the baselined value, the floor's quantity and a floor per metric | 07, 17 | none |
| R84 | fix now | Make the docs/07 verdict table the single rule set (+4 more) | 02, 03, 07, 08, 14, 17 | none |
| R85 | fix now | Describe the histogram's edges and its q=100 rule in docs/14 | 14 | kept: `core/histogram.py` and tests |
| R86 | fix now | Define idle and active buckets and one usual-range window rule | 07, 14, 17 | none |
| R111 | fix now | Give the other settings a range column and refuse bad files (+1 more) | 08, 14, 17 | partial, undone; moved to plan → P0-W3-T2, P0-W4-T2 |

### Build structure, interfaces and checks

| Finding | Ruling | What the brief now says (first document commit) | Documents changed | Code |
| --- | --- | --- | --- | --- |
| R108 | fix now: new layer-3 program packages (option a) | Put the running loops in layer-3 programs beside cli (+1 more) | 13, 14, 17 | kept: tests only |
| R109 | fix now: approve FastAPI and uvicorn with docs pages off; defer Parquet; hand-write MCP; tzdata on Windows only; vendor uPlot | List v1's runtime dependencies and keep report assets local | 11, 13, 17 | none |
| R110 | plan |  | none | plan → P0-W6-T1 |
| R112 | plan | Split cli by command group and give each component its tests | 13, 14, 17 | plan → P0-W2-T1, P0-W2-T3, P0-W3-T1 |
| R115 | fix now | Close a session never stopped; name where group membership comes from | 05, 06, 17 | none |
| R116 | fix now | Write docs/17-only rules into the topic files and align docs/17 (+2 more) | 05, 06, 07, 13, 17, docs/README | none |
| R121 | plan | Name the --json envelope and the history DDL as first tasks (+2 more) | 03, 06, 13, 14, 15, 17, docs/README | plan → P1-W1-T1, P3-W1-T1 |
| R134 | fix now | Type-check Windows and Linux code in the AGENTS.md checks (+1 more) | 14, 15, AGENTS.md, windows-priorities | kept: `pyproject.toml` and tests |
| R135 | fix now | Fix the wording slips in programs, locks, parents and output (+1 more) | 03, 06, 08, 13, 15, 16, 17 | none |
| R138 | fix now: freeze it; the topic files win | Rank brief.html last in Which file wins; it is frozen as delivered | docs/README | none |

### Linux: what version 1 reads, and the cgroup design kept for later

| Finding | Ruling | What the brief now says (first document commit) | Documents changed | Code |
| --- | --- | --- | --- | --- |
| R43 | fix now | Delegate only the controllers the parent slice passes down (+1 more) | 09, 17 | none |
| R72 | fix now | Place a Linux tagged run in a delegated user scope (+1 more) | 16, 17 | none |
| R73 | fix now | Keep Linux tagged memory in anon plus swap, the cache peak apart | 06, 09, 17 | none |
| R74 | fix now | State that a Linux tagged tree can leave its group (+1 more) | 17 | none |
| R75 | fix now | Name the Linux GPU sources: NVML, DRM fdinfo, amdgpu device load | 07, 09, 17 | none |

## 3. The work breakdown

### 3.1 How to read a task

- **Ids.** `P<phase>-W<wave>-T<n>` for a builder task; `P<phase>-O<n>` for an owner task, which needs the owner's Windows machine and runs outside the waves. A task's wave is part of its id. Every task in the first wave of a phase depends on the previous phase's gate ("gate P<n>"), which the owner approves.
- **Advances.** The components of `docs/13-build-list.md` by number (04b is the psutil provider, the fallback for 04 and the Linux process reader in version 1), the tools beside the code (`docs/13-build-list.md:42-55`), and the findings (R-numbers) and combination entries (I-numbers, `docs/review/02-rulings.md:136-265`) whose remaining work the task does.
- **Owns.** Every path the task may create, change or delete. Section 4 is built from these lines.
- **Uses, Provides.** The interfaces the task reads and the ones it adds: records, functions, files, commands.
- **Tests first.** The tests that must fail before the change and pass after it; the reviewer checks both runs. A task that only moves code without changing behaviour (P0-W2-T1) has no failing test; its check is that the same tests are collected and pass before and after. For a probe or a tool, its logic is tested first (parsers, statistics and decision rules on recorded inputs). A gate harness is itself the acceptance test, must pass on CI before merge for every case not marked for the owner's machine, and follows the harness contract of section 6.2: one test function per gate item, named `test_p<n>_<k>_…`, each writing `P<n>.<k>.json` to the folder `SUBMETER_GATE_DIR` names. Owner tasks are measurements and change no code.
- **Gate evidence.** The gate items of section 6 the task's output feeds.
- **Size,** in builder sessions. A session is one builder agent from reading the task card to a pushed branch whose seven checks pass, including the failing test written first and the task report. **S**: well within one session; about 100 changed lines of source and tests or fewer, in three files or fewer. **M**: most of one session; about 100 to 300 changed lines, or one new module with its tests. **L**: one whole session; about 300 to 600 changed lines, or a new module with ctypes structures or fixtures. Nothing larger is planned, except where a plan entry sizes its task past L and says why (P0-W2-T1), and a task that grows past L is split at its review. Two cases are kept whole: a task whose plan entry sizes it past L and says why (P0-W2-T1); and a task found past L at its review whose plan entry and card record a size exception under a planning defect in `docs/STATUS.md` that the plan reviewer has read (P0-W1-T2, PD-001). For scale: the `fix now` changes measured in stage 1 were 47 to 102 changed lines each (`docs/review/02-rulings.md:276-286`), and the four checks took 12.1 s in a fresh working copy and 3.9 s afterwards on the review's Linux machine (measured for this plan on 22 November 2026).
- **OS.** "either": portable code, tested on both runners. "Windows (CI-W)": Windows-only code whose tests skip elsewhere; the task is done only when CI-W passes, whatever system the builder works on. "Linux (CI-L)" likewise. "The owner's machine": needs the unprivileged user, a logon session or hardware, which hosted runners do not provide (`docs/15-phases-and-decisions.md:25`, R118). Tests marked `owner_machine`, `session`, `hardware` or `soak` (registered by P0-W1-T1) are left out of CI's main job and run where their mark says. `addopts` in `pyproject.toml` (P0-W1-T1) leaves them out of the plain `uv run pytest` of `AGENTS.md:32` too, so builders and the lead run what CI's main job runs; a later `-m` on the command line replaces that selection, and `-m "soak or not soak"` selects every test. A case that takes longer than about 60 s carries `soak` and keeps a shorter variant without it (section 7.1).
- **Owner tasks** run as the signed-in standard user at the commit their card names. The phase's last owner task includes the owner check run of section 6.2 step 4 at the gate commit. The owner has two Windows machines (`docs/STATUS.md` 7.10, the owner's answers of 2026-11-28). The personal Windows 11 PC is the machine of record: the owner runs every owner task there, and its output is the task's evidence, committed and pushed from there. The work PC is checked by word only (`docs/STATUS.md` 7.12): the owner runs P0-O1 and P0-O2 there and, from P1 on, only the owner check run of section 6.2 step 4 at each gate commit; the fixture recordings (P2-O1, P5-O1), the 24-hour soaks (P2-O2, P5-O2), the daemon install with its sign-out (P3-O1) and P4-O1's restart and cold start run on the personal PC only. The owner reads the results on screen and tells the lead each item's outcome in one word (pass or fail, or the named choice: for B4 subtract, keep or ask; for B3 scheduled task or Run key; for probe 2's trigger fired or not), which the lead records in `docs/STATUS.md` as the owner's statement with the date. Nothing is ever committed or pushed from the work PC: no file, figure or copied text from it enters the repository. P0-O1 and P0-O2 therefore end with a summary screen that shows each item's one-word result, so that the owner can read them off on the work PC; the check run's words are pass or fail for each saved check, read from its `exit=` line. A figure with no pass mark (the restricted share of P0.5) comes from the personal PC only. The owner reads every file recorded on the personal PC before it is pushed. Each owner task replaces the user, host and domain names and the home folder in its output with `scripts/probes/replace_names.py` (P0-W1-T2), runs the name check of section 6.2 step 4 (from P2 also `tests/test_fixtures_anonymised.py`, P2-W1-T3, with `SUBMETER_SCAN_EVIDENCE=1` so that it also scans the evidence folders), and commits only its own folder on a branch named `owner/<task id>`. A reviewer reads the branch, and the lead merges it with the check that it touches only that folder (section 6.2 step 5). An owner card has the fields of a builder card with two differences. **Time** (attended time on the owner's machine) replaces Size, because no builder session is spent. There is no **Tests first**, because an owner task changes no code: it produces measurements and recorded files that a gate reviewer or a builder task reads. Its **Provides** line names those files, their format and the tasks or gate items that read them, and the card names the one-word results the work PC reports, if the task runs there.
- **Line references.** `docs/NN:line` is short for that line of `docs/NN-*.md`; every other reference names its file.
- **Other ids.** L00 is the rule that known limits are shown beside the numbers they affect (`docs/10-known-limits.md:5`); L01 to L13 are the rows of the table in `docs/10-known-limits.md:9-21`, in order. B1 to B20 are the decisions of section 5.6 and C1 to C10 the plan's own choices of section 5.7.
- **Locations the brief does not give** (plan choice C3). P0 probes live in `scripts/probes/` and run like `scripts/platform_check.py`. Test tools (load generator, soak tools, fixture recorder, synthetic store and series generators) live in the package `tests/tools/`, which `uv run mypy src tests` type-checks and the wheel does not ship; they run as `uv run --directory tests python -m tools.<name>`. Recorded fixtures go under `tests/fixtures/recorded/`, synthetic ones under `tests/fixtures/<component>/`.
- **Records.** `AGENTS.md:40` puts every record passed between layers in `core/models.py`, and R112's rewording waits for the owner (B10). So in each phase one task owns `core/models.py` with `tests/builders.py` and `tests/test_models.py` (plan choice C7): the first-wave contract task, or a P0 repair that changes record types. In P0 the test split (P0-W2-T1) first creates `tests/builders.py` and `tests/test_models.py` by moving existing code, and holds neither `core/models.py` nor any record.


### 3.2 Where each component is built

The Tasks column is generated from the Advances lines of the builder cards: a task is listed against every component number its Advances line names. Owner tasks build no component and are not listed.

| # | Component | In version 1 | Tasks |
| --- | --- | --- | --- |
| 01 | `core.models` | yes | P0-W3-T1, P0-W4-T1, P0-W5-T1, P1-W1-T2, P2-W1-T1, P3-W1-T1, P4-W1-T1, P5-W1-T1 |
| 02 | `core.config` | yes | P0-W3-T1, P0-W3-T2, P0-W4-T2, P0-W6-T1, P2-W1-T1, P4-W2-T2 |
| 03 | `providers.base` | yes | P2-W1-T1, P2-W5-T1 |
| 04 | `providers.windows.bulk` | yes | P0-W6-T2, P2-W2-T1, P2-W3-T4, P2-W6-T4 |
| 04b | `providers.psutil_provider` (fallback for 04; the Linux reader in version 1) | yes | P0-W2-T4, P0-W4-T1, P0-W6-T1, P2-W2-T2, P2-W4-T2, P2-W6-T4 |
| 05 | `providers.linux.procfs` | not in version 1: after it (R151; I12) | none; 04b stands in, and the Linux corrections it needs (R40, R56, R60, R64) are in P0-W4-T1, P2-W2-T2, P2-W3-T3 and P2-W4-T2 |
| 06 | `providers.system` | yes | P2-W1-T1, P2-W2-T3, P2-W4-T2, P2-W6-T4 |
| 07 | `collector.sampler`, with the loop in `programs.collector` | yes | P0-W4-T1, P0-W6-T1, P0-W6-T2, P2-W1-T2, P2-W3-T2, P2-W3-T3, P2-W4-T4, P2-W5-T1, P3-W2-T4, P5-W2-T2 |
| 08 | `store.files` | yes | P0-W3-T1, P0-W4-T1, P0-W6-T1, P1-W1-T2, P2-W3-T1, P2-W4-T1, P3-W1-T4, P3-W2-T3 |
| 09 | `store.raw` | yes | P0-W4-T1, P0-W5-T1, P0-W6-T1, P2-W1-T2, P2-W3-T1, P3-W1-T4 |
| 10 | `store.rollup` | yes | P0-W3-T1, P0-W5-T1, P0-W6-T1, P2-W1-T2, P3-W1-T1, P3-W2-T2 |
| 11 | `store.query` | yes | P0-W3-T1, P0-W6-T1, P3-W3-T2, P4-W1-T3 |
| 12 | `cli` | yes | P0-W2-T3, P0-W3-T2, P0-W5-T1, P0-W5-T2, P1-W1-T1, P1-W2-T2, P1-W2-T3, P1-W2-T4, P2-W1-T2, P2-W5-T2, P2-W5-T3, P3-W2-T3, P3-W3-T4, P3-W5-T1, P3-W5-T2, P3-W5-T3, P3-W5-T4, P3-W6-T3, P4-W3-T1, P4-W3-T2, P5-W2-T3, P5-W2-T4, P5-W3-T1 |
| 13 | `programs.launcher` | yes | P0-W2-T2, P1-W1-T2, P1-W1-T4, P1-W2-T1, P1-W2-T2 |
| 14 | `providers.group` | yes | P0-W2-T2, P1-W1-T2, P1-W1-T4, P1-W2-T4, P2-W1-T1, P3-W1-T3, P3-W2-T4 |
| 15 | `attribution` | yes | P0-W2-T4, P0-W5-T1, P0-W6-T1, P2-W1-T2, P2-W2-T4, P2-W4-T2, P2-W5-T1, P3-W2-T4, P3-W3-T4 |
| 16 | `privacy.redact` | yes | P2-W1-T3, P2-W4-T1, P3-W3-T4 |
| 17 | `analysis.detectors` | yes | P0-W3-T1, P4-W1-T2, P4-W1-T3, P4-W1-T4, P4-W2-T1 |
| 18 | `analysis.verdict` | yes | P0-W4-T2, P4-W1-T1, P4-W1-T2, P4-W2-T2, P4-W3-T1 |
| 19 | `analysis.diff` | yes | P4-W1-T1, P4-W2-T4, P4-W3-T2 |
| 20 | HTTP API, WebSocket and token | not in version 1: version 1.1 (R150) | none; `Api` settings kept unused (I57) |
| 21 | Live dashboard | not in version 1: version 1.1 (R150) | none; `Ui` settings kept unused (I57) |
| 22 | `alerts` | yes | P0-W4-T2, P4-W1-T2, P4-W1-T3, P4-W2-T3 |
| 23 | `providers.extended` | yes | P2-W1-T1, P5-W1-T2, P5-W1-T3, P5-W2-T2, P5-W2-T4 |
| 24 | `report` | yes | P5-W1-T1, P5-W1-T4, P5-W2-T1, P5-W3-T1, P5-W3-T3 |
| 25 | MCP server | not in version 1 (R143) | none; agents read `submeter cost --run "$SUBMETER_RUN" --json` (P1-W2-T3) |
| 26 | `programs.server` | yes | P3-W1-T1, P3-W2-T1, P3-W3-T1, P3-W4-T1, P3-W4-T2, P3-W4-T3, P3-W4-T4, P4-W3-T3 |

### 3.3 Where the moved code changes and the `plan` findings land

| Finding | What moved or was ruled `plan` | Task(s) |
| --- | --- | --- |
| R38 | `fix now` code built at 49 lines and reverted, because it ships with R39 (I1): the gap rule | P2-W1-T2 |
| R39 | `fix now` code of 73 lines reverted: gap and awake seconds through raw rows and rollups | P2-W1-T2 |
| R42 | `plan`: unavailable and partial figures (option b) | P0-W5-T1, P2-W2-T2 |
| R46 | `plan`: two memory units; Linux full PSS measured in P0 (option a) | P0-W2-T4, P0-W5-T1, P2-W2-T2, P2-W3-T3 |
| R52 | `plan`: the plateau test replaced and tuned on the 75 MiB an hour acceptance | P4-W1-T2, P4-W2-T1 |
| R55 | `fix now` code built at 47 lines and reverted after review: anchored stamps and clock steps; needs the backward-step rule (B8) | P2-W4-T4, P2-W3-T1 |
| R56 | `fix now` code not attempted, estimated at 75 lines: the integer start stamp | P0-W4-T1 |
| R57 | `fix now` code of 60 lines in its smallest clean form: optional CPU, no stand-in record, capped deltas | P0-W4-T1 |
| R60 | `plan`: Linux unseen CPU placed by cgroup unless P0's cost breaks the budget | P0-W2-T4, P2-W4-T2 |
| R93 | `plan`: a nullable column for every catalogue metric; the schema version read back | P2-W3-T1, P3-W1-T1 |
| R110 | `plan`: about ten focused tests for the behaviours mutation testing left unguarded | P0-W6-T1 |
| R111 | `fix now` code: a partial change reached 51 lines with its test still failing: settings validation and exit code 2 | P0-W3-T2, P0-W4-T2 |
| R112 | `plan`: the restructuring before parallel work on shared files, as three tasks that share no path: the test split, the CLI package and the record fields | P0-W2-T1, P0-W2-T3, P0-W3-T1 |
| R117 | `plan`: gates with references, data, machines and numbers | P2-W5-T4, P3-W1-T2, P4-W1-T2 (with section 6) |
| R121 | `plan`: the `--json` envelope first in P1 and the history DDL first in P3 | P1-W1-T1, P3-W1-T1 |
| R123 | `plan`: a reused pid read again through a fresh psutil object | P2-W2-T2 |
| R137 | `plan`: phase 0 measured on the owner's machine, and Linux figures marked as such | P0-W1-T2, P0-O1, P0-O2 (with section 8) |
| R145 | `fix now` code of 102 lines undone: the minute tier removed from the code | P0-W3-T1 |
| R151 | `plan`: the platform layer for Windows only; Linux polled | P1-W2-T2, P2-W2-T2, P4-W2-T2 |
| R153 | `plan`: the floor of version 1 and the six-phase list | section 1.2 and the phase list of section 3 |

### 3.4 P0: decision probes, CI and the baseline repairs

`docs/15-phases-and-decisions.md:7-27` gives P0 the owner's step 1, CI on both runners, two Linux CI measurements and three probes. This plan also puts in P0 the baseline repairs the rulings scheduled before feature work (plan choice C9): R112's restructuring; the moved `fix now` changes that P1 and P2 build on, R145, R57 with R56 and R111; R42 with R46, which `docs/review/fixes/R61.md` requires before the first task that passes group totals, P1's run file and holder; and R110's tests. The pilot wave changes two shared files, `pyproject.toml` and `uv.lock`, both held by P0-W1-T1, and nothing under `src/`. R112 comes next, as three tasks that share no path, before every task that edits the files they hold and so before wave 1 of P1, the first phase whose features need it: the test split and the CLI package in P0-W2, and the record fields in P0-W3 with the minute-tier removal, which holds `core/models.py` there. The probes have no dependencies and fill the waves where room is left: probe 1 in P0-W2, probe 3 in P0-W5 and probe 2 in P0-W6, after P0-W5-T1, whose record changes probe 2's smoke test drives. R38, R39 and R55 move to P2 with the sampler and raw store they change. The owner runs step 1 after W1 (P0-O1) and the probes at the gate commit, after W6 (P0-O2). Gate (`docs/15-phases-and-decisions.md:27`): both runners pass the checks, every output is saved, and each probe's choice is recorded.

Entry condition of P0-W1: `main` is on `origin`. P0-W1-T1 proves itself on CI, which runs only on pushed branches, and section 4.1 rule 3 starts every wave from a pushed base commit. On 22 November 2026 `git ls-remote origin` printed nothing, and stage 1's push of `main` was still owed (`docs/review/01-adversarial-review.md:17`; section 10.2). Updated in stage 3: stage 2 pushed `main` on 23 November 2026 (`git ls-remote origin` printed `76ebe71… refs/heads/main` at 12:08), so what remains is to push the stage 3 commit, which holds the task cards (`prompts/02-orchestration-prompt.md` 5.1 item 2).

#### Wave P0-W1 (2 builders)

**P0-W1-T1 · CI on both runners, and the test markers**

- **Advances:** tools beside the code: CI (docs/13:44); R118, R134, R109
- **Owns:** `.github/workflows/ci.yml`, `pyproject.toml`, `uv.lock`, `tests/test_project.py`
- **Uses:** the seven commands in AGENTS.md:25-33; `uv sync --locked`. **Provides:** workflow `ci` with a Windows job and a Linux job on pinned images (proposed `windows-2025` and `ubuntu-24.04`; the builder confirms both labels in GitHub's current runner list), Python 3.13 installed by uv, run on push to every branch; pytest markers `owner_machine`, `session`, `hardware` and `soak` registered with `--strict-markers`; `addopts` in `pyproject.toml` that deselects the four marks, so that the plain `uv run pytest` of `AGENTS.md:32` runs what CI's main job runs
- **Work:** Each job runs `uv sync --locked`, the six other AGENTS.md commands, and pytest with `-m "not owner_machine and not session and not hardware and not soak"` (R118: tests that need an unprivileged user, a user session or hardware run on the owner's machine at the gate). The jobs take the settings of section 7.5: pytest with `-rfEsxX --durations=25 --continue-on-collection-errors` and a `--basetemp` in the runner's temporary folder; every step after `uv sync --locked` (step id `sync`) carries `if: ${{ !cancelled() && steps.sync.outcome == 'success' }}`, because GitHub Actions skips a job's later steps once one step fails, and the test-only commit of section 7.2 fails strict mypy before pytest runs; the job still fails when any step failed; `SUBMETER_GATE_DIR` set to a folder that is uploaded as the artefact `gate-windows` or `gate-linux` (the harness contract of section 6.2); a last step that fails if `git status --porcelain` prints anything; a 30-minute job limit; no `cancel-in-progress`; actions pinned by commit and the uv version pinned. Python 3.13 only, unless the owner answers Q2 otherwise. This is the one `pyproject.toml` and `uv.lock` commit before parallel work that R109 asks for; it adds no package (I35, I82).
- **Tests first:** `tests/test_project.py::test_markers_are_registered_and_strict` (fails today: `pyproject.toml:47-50` registers no marker); `::test_plain_pytest_deselects_the_marked_tests`, in which a test marked `soak` is left out by a plain `uv run pytest` and run by `-m soak` (fails today: no `addopts`); and `::test_ci_runs_every_agents_check_on_both_systems`, which reads `ci.yml` as text and looks for each of the seven commands, both runner labels, `SUBMETER_GATE_DIR`, the two artefact names, `--continue-on-collection-errors` and the `!cancelled()` condition on every step after `uv sync --locked` (fails today: there is no `.github/`).
- **Gate evidence:** P0.1, S1
- **Depends on:** none · **Size:** S · **OS:** either; proves itself on CI-W and CI-L

**P0-W1-T2 · Step-1 helper scripts for the owner's machine**

- **Advances:** P0 step 1 (docs/15:11, :23); R125, R137, R126
- **Owns:** `scripts/probes/cpu_time_check.py`, `scripts/probes/restricted_share.py`, `scripts/probes/replace_names.py`, `tests/test_probe_step1.py`, `docs/review/ground-windows/step1-procedure.md`
- **Uses:** `psutil.cpu_times(percpu=True)`, `time.perf_counter()`; the bare JSON list `submeter top --json` prints today (`src/submeter/cli.py:100`). **Provides:** `cpu_time_check.py`: per core, r1 = Δ(user + system + idle) ÷ elapsed and r2 = Δ(user + system + idle + interrupt + dpc) ÷ elapsed over 10 s, three repetitions, and the decision (r1 within 1.00 ± 0.01 on every core: subtract interrupt and DPC; r2 within it: keep the busy sum; neither: ask); `restricted_share.py`: the `restricted` row's `cpu_s` as a share of all rows and its `processes`; `replace_names.py`: replaces the current user name, host name, domain name and home folder in every file of a folder with `<user>`, `<host>`, `<domain>` and `<home>`, as whole tokens and case-insensitively, in UTF-8 and UTF-16 files, for every owner task's output (section 3.1, Owner tasks); the procedure file: every command of step 1 in order with its output file name
- **Work:** The procedure covers, in a PowerShell started normally: the seven AGENTS.md commands, `scripts/platform_check.py`, the Defender Operational log query for events 1121 and 1122 naming python.exe after the script's start (R126), `cpu_time_check.py` (R125), `submeter top --seconds 2 --json` with `SUBMETER_HOME` pointing at a new empty folder and `restricted_share.py` (R137), the suspend and clock checks of `docs/reference/windows-priorities.md` section 5 (R59, R124), `icacls` on the folders `platform_check.py` created, to see whether R100's private folders hold on Windows, and whether `%APPDATA%\Submeter` and `%LOCALAPPDATA%\Submeter` are redirected or synced: the `AppData` and `Local AppData` values under `HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders`, and whether either folder lies under a OneDrive folder (`docs/reference/windows-priorities.md:77`, K18). Every output is saved through `Out-File -Encoding utf8`, because Windows PowerShell 5.1 writes UTF-16 with a bare `>` (section 6.2 step 4), so that the evidence can be searched and compared. The procedure ends with `replace_names.py` over the output folder and the name check of section 6.2 step 4, before the commit.
- **Tests first:** `tests/test_probe_step1.py` loads each script by path with importlib: the ratios and the decision from two recorded per-core readings (one per outcome); the share from a recorded `top` list, including a list with no `restricted` row (share 0 with 0 processes, stated, not an error); `replace_names.py` on a folder of planted UTF-8 and UTF-16 files replaces each name as a whole token and leaves a longer word that contains it. Fails before: the scripts do not exist.
- **Gate evidence:** P0.2 to P0.5 (the owner runs them in P0-O1)
- **Depends on:** none · **Size:** M (finished at 989 changed lines; size exception PD-001, `docs/STATUS.md` section 9) · **OS:** either for the tests; run on the owner's machine


#### Wave P0-W2 (4 builders)

**P0-W2-T1 · The test split and the layer rows**

- **Advances:** the test layout (`docs/17-build-prompt.md:43`: one test file per component); R112 (test part), R108 (`LAYER` rows), I79
- **Owns:** `tests/builders.py`, `tests/test_layers.py`, `tests/test_baseline.py`, `tests/test_collector.py`, `tests/test_store.py`, `tests/test_settings.py`, `tests/test_analysis.py`, `tests/test_models.py`, `tests/test_units.py`, `tests/test_config.py`, `tests/test_histogram.py`, `tests/test_psutil_provider.py`, `tests/test_sampler.py`, `tests/test_attribution.py`, `tests/test_files.py`, `tests/test_raw.py`, `tests/test_rollup.py`, `tests/test_query.py`, `tests/test_growth.py`, `tests/test_privacy.py`, `tests/test_cli.py`
- **Uses:** the baseline test files: `tests/test_baseline.py` (522 lines), `test_collector.py` (174), `test_store.py` (103), `test_settings.py` (49) and `test_analysis.py` (43), 891 lines in all. **Provides:** one test file per component; `tests/builders.py`; `LAYER` rows for `alerts` and `report`
- **Work:** (1) The five files are split by component into the files listed (docs/17:43), and the three copies of the record builders (`test_baseline.py:61-103`, `test_store.py:18-35`, `test_attribution.py:23-34`) move to `tests/builders.py`; moves only, no assertion changes. The model tests of `test_collector.py` (`test_reprs_leave_out_the_command_line`, `test_validation_errors_leave_out_the_command_line`, `test_counters_carry_an_optional_child_time`) go to `tests/test_models.py`, and `test_cli_runs_end_to_end` to `tests/test_cli.py`, where it still imports `submeter.cli.app`, which P0-W2-T3 keeps importable in the same wave. (2) `LAYER` gains `alerts: 2` and `report: 2` (decision B9, default (a)).
- **Note:** `AGENTS.md:35` tells every session to run one test with `uv run pytest tests/test_baseline.py -k NAME`, and this task deletes that file. The replacement wording is in section 11.6. Its approval is the line-35 part of decision B10, and it blocks this task: the task is not dispatched until the owner has approved the wording and it is on `main` at P0-W2's base commit, so that this builder and every later session read it (the lead starts a new session before dispatching P0-W2, for reason 3 under Sessions in 10.1). A merge hold would not do, because merges inside a wave are automatic once checks and review pass (`prompts/01-execution-prompt.md:104`).
- **Tests first:** No behaviour changes, so the check is against the wave's base commit, the P0-W1 integration commit: every test function name that `uv run pytest --collect-only -q` lists there is still listed after the change, now in its component's file, and the run's counts equal the base commit's. (At `1c734e0` there are 62 test functions and the run gives `61 passed, 1 xfailed`; P0-W1 adds tests of its own before this wave.) `test_no_module_imports_from_a_higher_layer` passes with the two new rows.
- **Gate evidence:** none directly; S1
- **Depends on:** P0-W1-T1; decision B9, B10 (the `AGENTS.md:35` wording only) · **Size:** L (about 890 lines move each way with no assertion changed; the diff is longer than L's 300 to 600 lines, but the move is checked by collected names and counts, not read line by line) · **OS:** either

**P0-W2-T2 · Probe 1: the Job Object**

- **Advances:** components 13, 14 (design input); R48, R68, R69, R137, I34
- **Owns:** `scripts/probes/job_object.py`, `tests/test_probe_job_object.py`
- **Uses:** ctypes: CreateJobObjectW, OpenJobObjectW, QueryInformationJobObject, IsProcessInJob, CreateProcessW with PROC_THREAD_ATTRIBUTE_JOB_LIST, GetProcessTimes. **Provides:** one text file with each step's result and the decision rows of P0.12
- **Work:** Steps a to h of gate P0.8: create a job as the user; create a child inside a new job while the probe is itself in a job, recording `IsProcessInJob(GetCurrentProcess(), NULL)` (the owner runs it from Windows Terminal, the VS Code terminal and Claude Code's shell); totals after every child has exited against each child's GetProcessTimes on held handles; reopen by name after the creator exits while a holder keeps a handle, then after the holder closes it (error 2 expected); a direct child with CREATE_BREAKAWAY_FROM_JOB in a job without BREAKAWAY_OK (the error is recorded); with JOB_OBJECT_LIMIT_BREAKAWAY_OK set, never SILENT_BREAKAWAY_OK, node then bash then a grandchild and `IsProcessInJob(grandchild, job)`, skipped with the reason when node or bash is absent (B16); 500 children busy 5 ms each, to see whether job CPU clusters at multiples of about 15.6 ms; a burner in a job nested inside a job the probe made, with both jobs' CPU totals, to see whether a parent job's totals include its child job's processes, as R49's subtraction assumes (K14).
- **Tests first:** The decision function from recorded step results (reopen as expected: the holder design stands; step a or b failing: stop and ask; step h's outer total short of the nested burner's CPU: B1 goes to the owner); an AST check that the script never names SILENT_BREAKAWAY_OK; on CI-W steps a to e run as a smoke test (the runner is an administrator, so this is not evidence).
- **Gate evidence:** P0.8
- **Depends on:** none · **Size:** M · **OS:** Windows (CI-W smoke run); evidence from the owner's machine in P0-O2

**P0-W2-T3 · The CLI package**

- **Advances:** components 12; R112 (CLI part)
- **Owns:** `src/submeter/cli.py`, `src/submeter/cli/__init__.py`, `src/submeter/cli/_common.py`, `src/submeter/cli/doctor.py`, `src/submeter/cli/top.py`, `src/submeter/cli/config.py`, `src/submeter/cli/store.py`, `tests/test_cli_registry.py`
- **Uses:** `cli.py` (145 lines, 5 commands). **Provides:** the package `submeter.cli` with `app` and one module per command group; command discovery (plan choice C8)
- **Work:** `cli.py` becomes `src/submeter/cli/` with `_common.py`, `doctor.py`, `top.py`, `config.py` and `store.py`; `cli/__init__.py` builds `app` and calls `register(app)` on every module in the package whose name does not start with an underscore, so a later command task adds a module and edits no shared file; `[project.scripts] submeter = "submeter.cli:app"` keeps working, and `from submeter.cli import app` still imports, which the CLI test P0-W2-T1 moves in the same wave relies on.
- **Tests first:** `tests/test_cli_registry.py` checks that every command module registers at least one command and that `submeter --help` lists doctor, top, config and store (fails today: `cli.py` is one module with no `register`); `test_cli_runs_end_to_end` passes unchanged where it stands at the base commit.
- **Gate evidence:** none directly; S1
- **Depends on:** P0-W1-T1 · **Size:** M · **OS:** either

**P0-W2-T4 · Linux CI measurements for cgroup reads and full PSS**

- **Advances:** components 04b, 15 (decision input); R60, R46, I22, I28
- **Owns:** `scripts/probes/linux_cgroup_cost.py`, `scripts/probes/linux_pss_cost.py`, `tests/test_probe_linux_costs.py`, `.github/workflows/ci.yml`
- **Uses:** `/sys/fs/cgroup/**/cpu.stat`, `/proc/PID/smaps_rollup`, `time.process_time()`. **Provides:** two outputs labelled "CI-runner figure", kept as workflow artefacts of the Linux job
- **Work:** The cgroup script lists leaf cgroups, reads each `cpu.stat` for 100 rounds and prints the leaf count, the median and worst CPU per round, the cost per leaf and the share of one core at 2 s and 5 s. The PSS script reads `smaps_rollup` for every readable pid once and prints the process count, resident GB, CPU ms for the round and ms per GB resident. The Linux CI job gains a step that runs both. The decision thresholds are the owner's (B5, B6).
- **Tests first:** Parsing of a recorded `cpu.stat` and `smaps_rollup` and the statistics (median, worst, per leaf, share). Fails before: the scripts do not exist.
- **Gate evidence:** P0.6, P0.7
- **Depends on:** P0-W1-T1 · **Size:** S · **OS:** Linux (CI-L)


#### Wave P0-W3 (3 builders)

**P0-W3-T1 · The optional record fields, and the minute tier removed from the code**

- **Advances:** components 01, 02, 08, 10, 11, 17; R112 (records part), R39, R42 and R46 (fields), R67, R145 (moved to plan, 102 lines measured), R95, R132, I8, I9, I39, I47, I66, I69, I70
- **Owns:** `src/submeter/core/models.py`, `tests/builders.py`, `tests/test_models.py`, `src/submeter/core/config.py`, `src/submeter/store/files.py`, `src/submeter/store/query.py`, `src/submeter/store/rollup.py`, `src/submeter/analysis/growth.py`, `tests/test_config.py`, `tests/test_files.py`, `tests/test_query.py`
- **Uses:** the baseline records (`core/models.py`, 204 lines); the list in docs/review/02-rulings.md:286. **Provides:** the optional fields every later phase writes; `Availability.OPAQUE`; a two-tier store in code: raw and hourly
- **Work:** (1) Optional fields, None meaning unavailable and None by default, for the docs/06:109-121 catalogue that version 1 collects: on `SystemCounters` per-core busy, idle, interrupt and DPC seconds, frequency and base frequency, commit used and limit, page reads and writes, disk queue length and latency, run queue, the on-battery flag, GPU load by engine type and adapter VRAM used and total; on `ProcessCounters` handles, the System mark, the total-unit memory (USS or PSS) with its read time, and GPU load by engine type (docs/13:31, docs/17:111), and the same four on `ProcessSample`, the per-process record the sampler builds and that attribution, `aggregate` and the raw writer read (`sampler.py:91-105` builds it field by field, so a field on `ProcessCounters` alone never reaches them; P0-W4-T1 copies them across); on `SampleBatch` per-core busy beside the existing machine total (kept, so `sampler.py` and `raw.py` need no change here; R112 asked for per-core in place of the float), awake seconds, the count of capped deltas, the count of processes whose start time could not be read, a clock-step flag and the expected interval; on `WorkloadSample` the gap flag (default False), awake seconds, the total-unit memory with its age, GPU load by engine type, and missing-member counts for I/O, memory and GPU load; on `Bucket` awake seconds, the total-unit memory's max, mean and age, and GPU load by engine type, max and mean; on `GroupTotals` processes started and active and peak commit (R67). No epoch on `WorkloadSample`, and `SCHEMA_VERSION` stays 1 (I9). (2) The minute tier: removes `Tier.MINUTE`, `Retention.minute`, `FileMap.minute_dir`, `minute_file` and `expired_minute`, the minute folder in `ensure()` and `disk_use()["minute"]`, the minute branch and `minute_retention_s` of `choose_tier`, and the minute wording in the docstrings of `rollup.py:9-10`, `query.py:1-8`, `files.py:4` and `growth.py:12`. The general `roll_up` and `merge` test keeps its 60 s width (I39). Comes before the settings validation, whose ranges must not cover `retention.minute` (I68). Part (1) is in this task because this task already holds `core/models.py` and `tests/test_models.py`, into which the test split of P0-W2-T1 moves the existing model tests in the wave before.
- **Note:** Until the owner approves R112's AGENTS.md:40 rewording (B10), every record passed between layers stays in `core/models.py`, which is why each phase's first wave has one task that owns it.
- **Tests first:** `tests/test_models.py` builds each record with each new field None and with a value (fails today: `extra="forbid"` refuses an unknown field); `Tier` has RAW and HOURLY only; `FileMap` has none of the three minute names; `disk_use()` has no `minute` key; `load_settings` refuses `storage.retention.minute`; `choose_tier` answers raw or hourly, and a window 24 to 48 h back whose day file is gone is answered from hourly at 1 h (R139). After the change `uv run submeter config check examples/submeter.toml` exits 0 (I70).
- **Gate evidence:** none directly
- **Depends on:** P0-W2-T1 · **Size:** L (the minute tier measured 102 lines; the fields and their tests add about 150) · **OS:** either

**P0-W3-T2 · Named settings and rules files exit with code 2**

- **Advances:** components 12, 02; R111 (CLI part)
- **Owns:** `src/submeter/cli/_common.py`, `src/submeter/cli/top.py`, `src/submeter/cli/config.py`, `tests/test_cli_files.py`
- **Uses:** `load_settings`, `ConfigError`, `RuleSet.load`. **Provides:** one loader for `--file` and `--rules` in `cli/_common.py`
- **Work:** A named `--file` or `--rules` that is missing, cannot be decoded as UTF-8 (a UTF-16 file included) or does not validate exits with code 2 and prints one line per problem (docs/08:116). Today `_load` treats a missing named file as no file (`cli.py:43-51`) and `top` calls `RuleSet.load` directly (`cli.py:89-90`). A default file that is absent stays silent.
- **Tests first:** For each of `--file` and `--rules`: missing, UTF-16, a TOML syntax error and a validation error each exit 2 with one line per problem. Fails today on the missing and UTF-16 cases.
- **Gate evidence:** none directly (`docs/08-configuration.md:116`)
- **Depends on:** P0-W2-T3 · **Size:** S · **OS:** either

**P0-W3-T3 · Static tests for the three fixed rules**

- **Advances:** all; fixed rules 1 to 3 (AGENTS.md:9-11); R109, R118; the first three items of `docs/13-build-list.md:93-95`
- **Owns:** `tests/test_fixed_rules.py`
- **Uses:** `ast` over `src/submeter`; `pyproject.toml`. **Provides:** a check on every push that no code changes a process, asks to elevate, or opens a network client
- **Work:** Fails on (1) a call that changes another process: psutil `nice`, `ionice`, `cpu_affinity` or `rlimit` with a value, `suspend`, `resume`, `kill`, `terminate`, `send_signal`; the Win32 names SetPriorityClass, SetProcessAffinityMask, SuspendThread, NtSuspendProcess, TerminateProcess; SetInformationJobObject anywhere except `providers/windows/job.py`; (2) `runas` or `requireAdministrator` anywhere in the package; (3) an import of `socket`, `http`, `urllib`, `ssl`, `ftplib` or `smtplib` in `src`; and checks that `[project] dependencies` names pydantic, psutil and typer only, and that no field of `Settings` turns on priority, affinity, suspend, kill, a memory cap, elevation, an upload, a webhook or telemetry (`docs/08-configuration.md:121-128`). Nothing in `src` today matches (checked with grep on 22 November 2026).
- **Tests first:** Each check is shown to fail on a violation the test plants in a copy of a module under `tmp_path`, and to pass on `src`.
- **Gate evidence:** section 1, row D14
- **Depends on:** none · **Size:** S · **OS:** either


#### Wave P0-W4 (2 builders)

**P0-W4-T1 · Unreadable CPU, capped deltas and integer start stamps**

- **Advances:** components 01, 04b, 07, 08, 09; R57 (60 lines), R56 (about 75 lines), I6, I12, I13, I42, I43
- **Owns:** `src/submeter/core/models.py`, `tests/builders.py`, `tests/test_models.py`, `src/submeter/providers/psutil_provider.py`, `src/submeter/collector/sampler.py`, `src/submeter/store/raw.py`, `src/submeter/store/files.py`, `src/submeter/attribution/rules.py`, `tests/test_psutil_provider.py`, `tests/test_sampler.py`, `tests/test_raw.py`, `tests/test_files.py`, `tests/test_attribution.py`, `scripts/platform_check.py`, `tests/test_platform_check.py`
- **Uses:** `/proc/PID/stat` field 22 and `/proc/sys/kernel/random/boot_id` on Linux; on Windows GetProcessTimes through ctypes, on a handle opened with PROCESS_QUERY_LIMITED_INFORMATION (R126). **Provides:** `ProcessCounters.cpu_s: float | None`; `ProcessKey.started: int`; `Snapshot.boot_id`; the unreadable-start count; capped deltas; `ProcessSample` carrying the optional per-process fields of P0-W3-T1 (the System mark, handles, the total-unit memory with its read time, GPU load by engine type), copied from `ProcessCounters` by the sampler
- **Work:** R57 first (`docs/review/02-rulings.md:283`): the psutil provider writes None for a refused CPU read and no longer builds the stand-in record with `started=0.0` (`psutil_provider.py:139-145`); a process whose start time cannot be read appears only in the Snapshot's unreadable count (I42 (b)); the sampler gives no CPU baseline when either reading is None and credits 0 (`sampler.py:83-90`); each credited delta is capped at `interval_s × logical cores` and the capped samples are counted (docs/17:98). Then R56 (`docs/review/02-rulings.md:284`): the start stamp is clock ticks since boot from field 22 on Linux, read by the provider's own Linux branch (I12), with `boot_id` on the Snapshot and in the raw file's `meta` table; on Windows CreateTime as the FILETIME integer GetProcessTimes returns, read on a handle opened with PROCESS_QUERY_LIMITED_INFORMATION (R126), never psutil's `create_time()`: that is a float of seconds since 1970, whose spacing near 1.8e9 s is 2.4e-7 s, wider than the FILETIME's 100 ns unit, so it cannot carry the stamp (of 100,000 random FILETIMEs of November 2026, 57,809 changed when converted to that float and back; computed for this plan on 22 November 2026). The stamp is read once for each new pid and kept while psutil's float for that pid is unchanged; a refused open puts the process in the unreadable count (I42 (b)); the born-in-interval test and the parent comparison use the boot clock (`sampler.py:87`); `process.started` and `process_raw.started` become INTEGER (`raw.py:41,50`); the pid file records the same stamp (`files.py:254-256,274`; I43); `platform_check.py` skips None CPU in its reconciliation check (docs/review/fixes/R41.md). The sampler copies each optional per-process field P0-W3-T1 added to `ProcessCounters` (the System mark, handles, the total-unit memory with its read time, GPU load by engine type) into the `ProcessSample` it builds (`sampler.py:91-105`), so that P0-W5-T1's `aggregate`, P2-W2-T4's System bucket, P2-W3-T1's `process_raw` columns, P3-W2-T4's tagged memory and P5-W2-T2's GPU readings receive them. `tests/test_platform_check.py` loads `scripts/platform_check.py` by path with importlib and runs its provider, reconciliation and SQLite checks in `tmp_path`, so that a later change to an interface the script calls fails a check on every push (section 4.2); `uv run mypy src tests` does not check `scripts/`.
- **Tests first:** A refused, then readable, CPU read credits 0; a delta above interval × cores is capped and counted; a process with an unreadable start time is only in the count (the stand-in case of `test_failed_reads_keep_the_process` changes accordingly); two reads of one process give equal integer keys; a wall-clock step does not cut a child from its parent; on CI-W the provider's start stamp for the test's own process equals, exactly, the CreateTime GetProcessTimes returns for it (fails today: the stamp is psutil's float); a recorded FILETIME with a sub-second part, 134397792001234567 (22 November 2026 plus 0.1234567 s; 57 bits), is stored unchanged, and the same value taken through psutil's float comes back as 134397792001234568, which the test asserts so that the reason for the integer read stays recorded; a `ProcessCounters` reading of each optional per-process field (the System mark, handles, the total-unit memory with its read time, GPU load by engine type) reaches the `ProcessSample` the sampler builds, and None stays None (fails today: `sampler.py:91-105` copies only the baseline fields); `tests/test_platform_check.py` runs the script's checks without an exception (fails before: the file does not exist).
- **Gate evidence:** none directly; prerequisite of P1's run file (the holder's start stamp) and of P2.2
- **Depends on:** P0-W3-T1 · **Size:** L · **OS:** either; the Linux reads on CI-L, the CreateTime read on CI-W

**P0-W4-T2 · Settings validation**

- **Advances:** components 02; 18 and 22 (setting shapes); R111 (settings part), R84, I50, I57, I68
- **Owns:** `src/submeter/core/config.py`, `tests/test_config.py`, `docs/08-configuration.md`, `examples/submeter.toml`
- **Uses:** docs/08:76-94, :134-142; docs/07:126-136. **Provides:** `AlertRule.metric` as a Literal; `Verdict.thresholds` as a model; finite ranges
- **Work:** `AlertRule.metric` becomes a Literal of the seven ids (docs/08:134-142) with the applies-to check (`commit_fraction` and `throttled` only for `machine`, `overhead_fraction` only for `submeter`); `Verdict.thresholds` becomes a model with one named field per row of docs/07:128-136, each with on and off values, and the values docs/07 leaves to phase 4 are `None` until P4-W2-T2 sets them; every duration, size, rate and fraction version 1 uses gets a finite range, `retention.raw` at least 24 h, `unattributed_alert` 0 to 100%; no range for the settings version 1 does not use (I57). The eight bounds docs/08:78-94 marks "not set yet" (`retention.raw` upper bound, `retention.executables`, `disk_budget`, `change_threshold.memory`, `leak.min_duration`, `leak.min_slope`, `verdict.window`, `alerts.cooldown`) come from the owner (B7) and are written into docs/08 here.
- **Tests first:** A misspelt threshold name is refused; a metric outside the seven is refused; `commit_fraction` on a workload pattern is refused; `retention.raw = "23h"` is refused with the range in the message; each bounded setting just outside its bound is refused; `examples/submeter.toml` still loads.
- **Gate evidence:** none directly (`docs/08-configuration.md:107, :114`)
- **Depends on:** P0-W3-T1; decision B7 · **Size:** M · **OS:** either


#### Wave P0-W5 (2 builders)

**P0-W5-T1 · Unavailable and partial figures, and the two memory units**

- **Advances:** components 01, 09, 10, 12, 15; R42, R46, R61, R65, I7, I15, I16, I17, I26
- **Owns:** `src/submeter/core/models.py`, `tests/builders.py`, `tests/test_models.py`, `src/submeter/attribution/rules.py`, `src/submeter/store/raw.py`, `src/submeter/store/rollup.py`, `src/submeter/cli/top.py`, `tests/test_attribution.py`, `tests/test_raw.py`, `tests/test_rollup.py`, `tests/test_cli_top.py`, `scripts/platform_check.py`
- **Uses:** the optional fields P0-W3-T1 added, on `ProcessSample` as P0-W4-T1's sampler copies them. **Provides:** I15's rule in `aggregate`; nullable workload columns; sums that keep None
- **Work:** `WorkloadSample` I/O and growth-unit memory become `int | None` with missing-member counts, `ProcessSample.cpu_s` optional (I16), `Bucket` I/O sums optional, and the total memory unit (USS on Windows, PSS on Linux) a separate figure with the time it was read (docs/17:105). `aggregate` applies I15: no member readable gives None, some give a partial sum with the missing count, all give a full sum; a tagged group that cannot report I/O gives None (R61); GPU load by engine type is summed per workload under the same rule, so a workload none of whose members has a GPU reading reads None; `source` keeps naming the CPU path (I7 (a)); Restricted is labelled polled with per-field partial marks and memory n/a (R65). `workload_raw` I/O and memory columns become nullable (`raw.py:44-48` are NOT NULL) and the total-unit columns are added; rollup sums keep None; `top` prints n/a; `platform_check.py` skips None. Placed here because docs/review/fixes/R61.md makes R42 a prerequisite of the first task that passes group totals, and that is P1's run file and holder (P1-W1-T2, P1-W2-T1).
- **Tests first:** The strict expected failure `tests/test_attribution.py::test_a_group_polling_never_saw_reports_its_io_and_memory_unavailable` passes and its marker is removed in this change; a workload whose members lack USS shows partial with the count; a raw row with None I/O comes back None; a bucket over None and int samples keeps the missing count; `top --json` prints null for an unavailable figure; two members with GPU readings sum per engine type, and a workload with none reads None.
- **Gate evidence:** S2 (no strict expected failure left); section 1, row D13
- **Depends on:** P0-W4-T1, P0-W3-T2 · **Size:** L · **OS:** either

**P0-W5-T2 · Probe 3: per-user autostart**

- **Advances:** components 12 (`daemon install` input); R50
- **Owns:** `scripts/probes/autostart.py`, `scripts/probes/autostart_task.xml`, `tests/test_probe_autostart.py`
- **Uses:** `schtasks /Create /XML`, `/Query /XML`, `/Run`, `/Delete`; `Get-AppLockerPolicy -Effective -Xml`. **Provides:** exit codes, the read-back XML with user and host names replaced, the decision row (scheduled task or the HKCU Run key)
- **Work:** Registers a logon task with the settings of docs/17:260 (InteractiveToken logon trigger for the current user, DisallowStartIfOnBatteries false, StopIfGoingOnBatteries false, ExecutionTimeLimit PT0S, MultipleInstancesPolicy IgnoreNew, restart on failure, Priority 5, RunLevel LeastPrivilege), reads it back and compares each setting, runs it once with an action that writes a marker file, deletes it, and records the effective AppLocker policy and Device Guard status, which decide whether a program in a user-writable folder may run at all.
- **Tests first:** Generation of the task XML and the comparison against a recorded read-back XML, on either system; registration refused gives the decision "HKCU Run key".
- **Gate evidence:** P0.10
- **Depends on:** none · **Size:** S · **OS:** Windows; evidence from the owner's machine (needs a logon session)


#### Wave P0-W6 (2 builders)

**P0-W6-T1 · Tests for the behaviours the mutation check left unguarded**

- **Advances:** components 02, 04b, 07, 08, 09, 10, 11, 15; R110, I66, I68, I70
- **Owns:** `scripts/mutation_check.py`, `tests/test_sampler.py`, `tests/test_attribution.py`, `tests/test_raw.py`, `tests/test_rollup.py`, `tests/test_psutil_provider.py`, `tests/test_config.py`, `tests/test_query.py`, `tests/test_examples.py`
- **Uses:** docs/review/probes/e-baseline/mutation_check.py (28 of 29 mutants survived the 20 delivered tests). **Provides:** about ten focused tests; an updated mutation script
- **Work:** Copies the review's mutation script to `scripts/mutation_check.py` (the probe stays as evidence), drops the mutants of removed code (`hot_keys`, `expired_minute`), adds mutants for the code P0 changed, runs it at HEAD, and writes a test for each surviving behaviour in R110's list (`docs/review/01-adversarial-review.md`, R110): sampler I/O delta; rule priority, kernel-group precedence, `inherit_from_parent`, Submeter's own pids, the cmdline condition; aggregate sums; raw CPU pending at exit, at rollover and at close, a keyframe after the first, a memory change writing a row, WAL mode; rollup time-weighted histograms, active seconds, `well_covered`; provider keeps an I/O-restricted process and does not count idle as busy; config precedence and the docs/08 defaults and ranges; `choose_tier`. `tests/test_examples.py` loads both example files (I70).
- **Tests first:** For each new test the reviewer runs `scripts/mutation_check.py` and sees the targeted mutant fail it while HEAD passes.
- **Gate evidence:** S1; the mutation output is kept with the P0 evidence
- **Depends on:** P0-W5-T1, P0-W4-T2 · **Size:** M · **OS:** either

**P0-W6-T2 · Probe 2: the bulk snapshot and the Rust trigger**

- **Advances:** components 04 (prototype), 07; R79, R78, R76, R137, I52, I56
- **Owns:** `scripts/probes/bulk_snapshot.py`, `tests/test_probe_bulk.py`
- **Uses:** ctypes NtQuerySystemInformation(SystemProcessInformation); `Sampler`, `Attributor`, `aggregate`, `RawFile` as P0-W4-T1 and P0-W5-T1 left them, with every workload figure possibly None. **Provides:** the figures of gate P0.9 per provider and interval, and the trigger result
- **Work:** A prototype bulk snapshot (pid 0 excluded) and the psutil provider each drive the sampler, attribution and raw store at the owner's process count: 10 minutes at a fixed 2 s and 10 minutes at a fixed 5 s per provider, 40 minutes, timing the whole tick; then the same 40 minutes again with 150 extra idle processes the probe starts itself, so that the 300-process figure comes from two points (80 minutes in all); the probe's user and kernel CPU apart (GetProcessTimes) and the raw store's share of the tick, so that the owner can judge what a Rust collector would remove (section 8.2); private bytes as the largest of samples taken every 10 s; one USS round for the 25 largest processes, and the combined share of the tick and that round at the 5 s idle interval for a `uss_interval` of 30 s, 60 s and 5 minutes (K2); Defender's CPU time over the same runs, or unavailable if a standard user cannot read it (K11); per-field availability for other users' processes. The trigger (docs/11:21-24): the bulk provider over 3% of one core at 2 s, over 1% at 5 s, or over 83,886,080 private bytes. The psutil figures are reported, not judged (I56).
- **Tests first:** The parser on a synthetic SYSTEM_PROCESS_INFORMATION buffer built from structures of fixed-width types (`c_uint32`, `c_uint64`, `c_uint16` for UTF-16 text), with each structure's size and field offsets checked against the values documented for 64-bit Windows (section 7.3.1; runs on both systems); the two-point derivation; the trigger decision from recorded figures; a smoke run of the probe for 3 short ticks with each provider the system has (psutil on both, the bulk prototype on CI-W), so that a later change to `Sampler`, `aggregate` or `RawFile` that breaks the probe fails a check on every push, not in P0-O2 (section 4.2).
- **Gate evidence:** P0.9
- **Depends on:** P0-W5-T1, P0-W4-T1 · **Size:** L · **OS:** Windows; evidence from the owner's machine in P0-O2


#### Owner tasks (outside the waves; no builder)

**P0-O1 · Owner: step 1 on the Windows machine** (after P0-W1 integrates)

- **Advances:** P0 step 1 (`docs/15-phases-and-decisions.md:11`, `:23`); R41, R59, R71, R100, R124, R125, R126, R127, R137
- **Owns:** `docs/review/ground-windows/step1/`
- **Uses:** `docs/review/ground-windows/step1-procedure.md` and the scripts of P0-W1-T2, and `scripts/platform_check.py`, at the P0-W1 integration commit. **Provides:** `docs/review/ground-windows/step1/`, one UTF-8 file per command, each starting with the command and ending with `exit=<code>`: `cpu-time-check.txt` decides B4, which blocks P2-W2-T3 and P2-W4-T2; `platform-check.txt`, `top-norules.json` and `restricted-share.txt` give P0.5's figures (K17); `defender-asr.txt` gives P0.3; each failing check becomes a fix task (section 5.5). The gate reviewer reads them for P0.2 to P0.5
- **Work:** Follows `docs/review/ground-windows/step1-procedure.md` at the W1 integration commit, as the signed-in standard user (`scripts/platform_check.py` prints `administrator or root: False`). One UTF-8 file per command; names replaced and checked before the commit (section 3.1, Owner tasks). Each failing check becomes a fix task (section 5.5).
- **Gate evidence:** P0.2, P0.3, P0.4, P0.5
- **Depends on:** P0-W1-T2 · **Time:** about 45 minutes · **OS:** the owner's personal Windows 11 PC, as the signed-in standard user, for the evidence; the same run on the work PC, reported by word (section 3.1, Owner tasks)

**P0-O2 · Owner: the three probes and a second platform check** (at the P0 gate commit G0, after P0-W6 integrates)

- **Advances:** decision input for the holder (B1), the collector's language and intervals (B2) and autostart (B3); R48, R50, R68, R69, R76, R78, R79, R126, R137, I56
- **Owns:** `docs/review/ground-windows/probes/`
- **Uses:** the three probes (P0-W2-T2, P0-W5-T2, P0-W6-T2), `scripts/platform_check.py` and the seven checks, at G0. **Provides:** `docs/review/ground-windows/probes/`, UTF-8 text: `checks/` (section 6.2 step 4); `job-object-terminal.txt`, `job-object-vscode.txt` and `job-object-claude-code.txt` (P0.8), which decide B1 and so P1-W1-T2, P1-W1-T4 and P1-W2-T1; `bulk-snapshot.txt` (P0.9), which decides B2 and so P2-W2-T1 and P2-W5-T1; `autostart.txt` (P0.10), which decides B3 and so P3-W5-T3; `platform-check.txt`; `defender-asr.txt` (P0.3); `startup-time.txt` (P0.14, the first reading for P4.5). The gate reviewer reads them, and the plan reviewer for P0.12
- **Work:** At G0 (section 6.2), once every P0 builder task is merged: first the owner check run of section 6.2 step 4, saved in `probes/checks/`; then `scripts/probes/job_object.py` from Windows Terminal, the VS Code terminal and Claude Code's shell; `bulk_snapshot.py` (about 80 minutes); `autostart.py`; `platform_check.py` again; `Measure-Command { uv run submeter --help }` 20 times, the start-up cost that bears on `why` under 2 s; the Defender log query again after the probes. node and bash for probe 1 step f only with the owner's approval (B16).
- **Gate evidence:** P0.2 (b), P0.3, P0.8, P0.9, P0.10, P0.14
- **Depends on:** every P0 builder task, among them P0-W2-T2, P0-W5-T2 and P0-W6-T2 (it runs at G0); decision B16 · **Time:** about 2 hours · **OS:** the owner's personal Windows 11 PC, as the signed-in standard user, for the evidence; the same run on the work PC, reported by word (section 3.1, Owner tasks)


### 3.5 P1: tagged runs

`docs/15-phases-and-decisions.md:29-35`: the launcher with its detached holder, the reading of a Job Object's final totals, the run file, `submeter cost --run` over run files only, and the load generator. No collector or store is needed. The envelope task comes first with one owner (`docs/15-phases-and-decisions.md:33`); the run-file contract, the load generator and the Job Object calls share its wave because none of them touches its files or needs its output. The design of the holder follows probe 1 (B1).

#### Wave P1-W1 (4 builders)

**P1-W1-T1 · The --json envelope for every command**

- **Advances:** components 12; R121; `docs/15-phases-and-decisions.md:33` (the first task of P1, one owner)
- **Owns:** `src/submeter/cli/_envelope.py`, `src/submeter/cli/_format.py`, `src/submeter/cli/doctor.py`, `src/submeter/cli/top.py`, `src/submeter/cli/store.py`, `src/submeter/cli/config.py`, `tests/test_cli.py`, `tests/test_cli_envelope.py`, `tests/test_cli_top.py`, `docs/03-cli-output.md`
- **Uses:** `submeter.cli` from P0-W2-T3. **Provides:** `emit(schema, fields)` printing `{"schema": "submeter.<command>/1", ...}`; `_format.py` for n/a and partial marks
- **Work:** One helper prints the envelope of docs/03:86 with the command's fields in the same object; doctor, top, store status, config show and config check move onto it, and config show and check gain `--json` (docs/03:5). The task decides and writes into docs/03 the schema name of a subcommand and the shape of `submeter.cost/1`, which must serve run files in P1 and history in P3 without a version change that agents would see.
- **Tests first:** A snapshot test per command in `tests/test_cli_envelope.py`, asserting the `schema` key and the field set, with the expected values kept in the test file (section 7.1, rule 3); each later command task keeps its own snapshot tests in its own test file. Fails today: doctor prints an object with `version`, top a bare list and store status `{bytes, total}` (`cli.py:67-70`, `:99-101`, `:140-142`).
- **Gate evidence:** S4
- **Depends on:** gate P0 · **Size:** M · **OS:** either

**P1-W1-T2 · The run file**

- **Advances:** components 01, 08, 13, 14; R113, R67, R49, R106, I33, I45
- **Owns:** `src/submeter/core/models.py`, `tests/builders.py`, `tests/test_models.py`, `src/submeter/store/runs.py`, `src/submeter/store/files.py`, `tests/test_runs.py`, `tests/test_files.py`, `docs/06-storage.md`
- **Uses:** `FileMap.runs_dir`, `WorkloadName`, `GroupTotals`. **Provides:** `RunFile` record; `store.runs` write, read, list and `state()`; `store.files.write_atomic()` for later control files
- **Work:** `RunFile`: run id, workload (`WorkloadName`), label, job name without a `Global\` prefix, parent run id or "unknown", start and end times in UTC, state live or final, the holder's pid and integer start stamp, and the final group totals as `GroupTotals` (CPU, I/O read and write, processes started, peak commit), with no current memory (R67). `store/runs.py`: path `runs/<id>.json`; write by a temporary file in the same folder and `os.replace`; created 0600; live moves to final only; `state()` returns lost for a live file whose holder is not alive (pid and start stamp, as `InstanceLock.holder()` matches them) when the caller's job check says the job is gone (the check is passed in, so `store` does not import a provider). The field names and types go into docs/06's run-file row. The holder's part depends on probe 1 (B1).
- **Tests first:** Live then final through the atomic rename while a reader polls 1,000 rewrites and parses every read; 0600 on POSIX; final to live refused; lost when the holder is dead and the job check says gone; a reserved workload name refused.
- **Gate evidence:** inputs to P1.2, P1.5
- **Depends on:** gate P0; decision B1 · **Size:** M · **OS:** either

**P1-W1-T3 · The load generator**

- **Advances:** tools beside the code: load generator (docs/13:48); R83, R136
- **Owns:** `tests/tools/__init__.py`, `tests/tools/loadgen/`, `tests/test_loadgen.py`
- **Uses:** GetProcessTimes and CreateProcessW through ctypes on Windows; `os.wait4` and `getrusage` on Linux; nothing from `submeter`. **Provides:** `uv run --directory tests python -m tools.loadgen <mode> ... --report FILE`: one JSON report per run
- **Work:** Modes: `spawn` (N children, each busy for a set time and alive under a set maximum, P at a time; keeps every child's handle open and sums their CPU with GetProcessTimes, or `wait4` on Linux, plus its own CPU); `burn` (one burner at a set share of a core that reports its own CPU seconds every 1 s with a UTC and a monotonic time, from GetProcessTimes or `getrusage(RUSAGE_SELF)`); `background` (a process left behind that burns a set CPU time and writes its own total when it ends, after the generator has exited); `idle` (holds N idle processes, to bring a runner to 300); `leak` (private bytes growing at a set rate or in steps); `memory` (commits and touches memory up to a set share of the machine's commit limit, then holds it for a set time, never going past the share it was given); `io` (reads and writes a file in a folder it is given, at a set rate, and reports its own byte counts from GetProcessIoCounters or `/proc/self/io`); `breakaway` (Windows: a direct child created with CREATE_BREAKAWAY_FROM_JOB, recording the error code); `grandchild` (a native chain through `cmd.exe /d /c start "" /b` whose grandchild reports IsProcessInJob, and node then bash when both are present). Children run the base interpreter (`sys._base_executable`) with `-I` and the standard library only, never `sys.executable`: on Windows a virtual environment's `python.exe` is a redirector that is expected to start the base interpreter as a second process, so GetProcessTimes on the held handle would measure the redirector and a job's process count would double (section 7.4; to be confirmed on CI-W). The reference for the P1 and P2 gates, so it never imports `submeter`.
- **Tests first:** `spawn` of 20 children of 50 ms reports 20 children, each at least 40 ms, and a sum equal to the per-child figures; `burn` at 50% for 3 s reports 1.2 to 1.8 CPU-s; `background` writes its total after its parent exited; `io` reports at least the bytes it was asked to write and read; `memory` stops at the share it was given; `leak` at 10,485,760 bytes a second for 3 s reports private bytes whose least-squares slope is within 10% of that rate, and `leak` in steps of 20,971,520 bytes every 1 s for 3 s reports three steps, each within 10% of its size; an AST check that the package imports nothing from `submeter`.
- **Gate evidence:** the reference of P1.1, P1.3, P1.6, P2.1, P2.2; the loads of P2-O1's recordings
- **Depends on:** gate P0 · **Size:** L · **OS:** either; Windows modes on CI-W

**P1-W1-T4 · Windows Job Object calls**

- **Advances:** components 14 (P1 part), 13; R67, R68, R69, R48
- **Owns:** `src/submeter/providers/windows/__init__.py`, `src/submeter/providers/windows/job.py`, `tests/test_job.py`
- **Uses:** ctypes (docs/13:55); `GroupTotals`. **Provides:** `create_job`, `open_job`, `totals`, `members`, `in_job`, `create_in_job`
- **Work:** Create a named job with no limits, breakaway not allowed and no kill-on-close (docs/17:78); open by name; read JOBOBJECT_BASIC_AND_IO_ACCOUNTING_INFORMATION and PeakJobMemoryUsed into `GroupTotals` (CPU as user plus kernel, I/O, TotalProcesses, ActiveProcesses, peak commit, R67); the member list (JobObjectBasicProcessIdList); IsProcessInJob; CreateProcessW with EXTENDED_STARTUPINFO_PRESENT and PROC_THREAD_ATTRIBUTE_JOB_LIST returning the process handle and pid, never CREATE_SUSPENDED and never AssignProcessToJobObject on the command (R69). On other systems the module imports and each call raises a stated unavailable error.
- **Tests first:** On CI-W: a child created inside the job is in it; the job's LimitFlags read back are 0 (fixed rule 1); totals after the child exits equal its GetProcessTimes within one 15.6 ms tick; opening a name with no job gives error 2. On both systems: each accounting structure is built from fixed-width types, and its size and field offsets match the values documented for 64-bit Windows (section 7.3.1). On Linux the import works and the calls raise.
- **Gate evidence:** inputs to P1.4, P1.5, P1.7; fixed rule 1
- **Depends on:** gate P0; decision B1 · **Size:** L · **OS:** Windows (CI-W)


#### Wave P1-W2 (4 builders)

**P1-W2-T1 · The launcher program and its detached holder**

- **Advances:** components 13; R48, R49, R68, R69, R113, I33, I45
- **Owns:** `src/submeter/programs/__init__.py`, `src/submeter/programs/launcher/__init__.py`, `src/submeter/programs/launcher/__main__.py`, `src/submeter/programs/launcher/holder.py`, `tests/test_launcher.py`
- **Uses:** `providers.windows.job`, `store.runs`. **Provides:** `python -m submeter.programs.launcher --status FILE --as NAME [--label L] -- COMMAND...` and its `hold <run-id>` mode; `SUBMETER_RUN`; live and final run files
- **Work:** The interface `submeter run` uses (P1-W2-T2): the launcher takes `run`'s arguments and `--status FILE`, a file the CLI created. If it cannot create the job, it writes `{"tagged": false, "reason": "..."}` to FILE and exits with code 0 without starting the command; otherwise it writes `{"tagged": true, "run": "<run id>"}` to FILE before it starts the command, and its exit code is the command's. Creates the named job, writes the live run file at once, sets `SUBMETER_RUN` to the run id in the command's environment (I33), creates the command inside the job with the job-list attribute and waits for it. A nested launcher reads `SUBMETER_RUN`, opens the outer job by name, confirms membership with IsProcessInJob and records the parent run, or "unknown" when the variable is missing or the check fails (R49). If processes remain when the command exits it starts the detached holder outside the job, records the holder's pid and start stamp in the live state (R113, I45), and returns the command's exit code without waiting; the holder keeps a handle until ActiveProcesses is 0 and writes the final state after the launcher's last write. Otherwise the launcher writes the final state. The design follows probe 1 (B1).
- **Tests first:** On CI-W: exit code 7 passed through; a 500 ms command with no children leaves a final run file; with a 3 s child left behind `run` returns within 2 s of the command's exit, the file is live with a holder pid, then final with the child's CPU; IsProcessInJob(launcher) is FALSE; a nested run records its parent; without `SUBMETER_RUN` the parent is "unknown"; when job creation fails (the test makes `create_job` raise) FILE reads `tagged: false` and the command is not started.
- **Gate evidence:** P1.1, P1.2, P1.3, P1.4, P1.6, P1.7
- **Depends on:** P1-W1-T2, P1-W1-T4; decision B1 · **Size:** L · **OS:** Windows (CI-W)

**P1-W2-T2 · The `submeter run` command**

- **Advances:** components 12, 13; R106, R151, I59
- **Owns:** `src/submeter/cli/run.py`, `tests/test_cli_run.py`
- **Uses:** `WorkloadName`; the envelope. **Provides:** `submeter run --as NAME [--label L] -- COMMAND`
- **Work:** Validates NAME as a `WorkloadName` and refuses reserved names with exit 2 (R106). On Windows it starts the launcher program as a child process, `sys.executable -m submeter.programs.launcher --status FILE` followed by the same arguments, with inherited standard streams, FILE being a new file the CLI creates with `tempfile.mkstemp` and deletes afterwards; it reads FILE when the launcher exits (the interface on P1-W2-T1's card) and returns the launcher's exit code (B9 (a): `cli` and `programs` are both layer 3, so the CLI may not import the launcher). Where tagged runs are unavailable (Linux in version 1, or Windows when FILE reads `tagged: false`) it says so, as a stable `tagged: false` field under `--json`, runs the command polled and returns its exit code (I59). On Linux it writes no run file and sets no `SUBMETER_RUN` (B13 default). `--json` prints the envelope `submeter.run/1` (docs/03:86, through P1-W1-T1's `emit`) with the `tagged` field, the run id when there is one, and the command's exit code.
- **Tests first:** Linux: `run --as x -- sh -c 'touch marker; exit 3'` exits 3, the marker exists and the output says tagged runs are unavailable; `run --as system -- ...` exits 2; the argument list handed to the launcher equals the user's command exactly, quoting included; a FILE reading `tagged: false` makes `run` say that tagged runs are unavailable and run the command polled; a snapshot test of `run --json`, kept in `tests/test_cli_run.py`, asserts the `schema` key `submeter.run/1` and the field set (S4).
- **Gate evidence:** P1.11
- **Depends on:** P1-W1-T1; decision B9, B13 · **Size:** M · **OS:** either

**P1-W2-T3 · `submeter cost --run`**

- **Advances:** components 12; R49, R67, R103, R143, I32
- **Owns:** `src/submeter/cli/cost.py`, `tests/test_cli_cost.py`
- **Uses:** `store.runs`, `providers.windows.job.open_job` (the lost check), the envelope. **Provides:** `submeter.cost/1` for runs
- **Work:** Reads run files only (no history file exists yet): `--run ID` and a list of runs. A parent's totals less the totals of the child runs that name it (R49); a live run whose holder is gone and whose job cannot be opened prints lost, never 0; mean memory and top executables printed as unavailable (R67). No command line and no working folder in any output (R103, R143).
- **Tests first:** From fixture run files: a parent of 10 CPU-s with a child of 4 CPU-s reports 6; a lost run reports lost; mean memory is null; a canary command line and folder planted in the run's environment appear nowhere in the output; snapshot tests of `cost --run ID --json` and of the run list with `--json`, kept in `tests/test_cli_cost.py`, assert the `schema` key `submeter.cost/1` and the field set (S4).
- **Gate evidence:** P1.6 (subtraction), P1.10
- **Depends on:** P1-W1-T1, P1-W1-T2, P1-W1-T4 · **Size:** M · **OS:** either; the job check on CI-W

**P1-W2-T4 · `doctor`: the tagged-run capability**

- **Advances:** components 12, 14; docs/15:21
- **Owns:** `src/submeter/cli/doctor.py`, `tests/test_cli_doctor.py`
- **Uses:** `providers.windows.job`. **Provides:** the `group.accounting` row
- **Work:** Full on Windows when a test job can be created and queried; unavailable on Linux, with the reason that tagged runs are not in version 1 there.
- **Tests first:** The row and its status on each system.
- **Gate evidence:** none directly
- **Depends on:** P1-W1-T1, P1-W1-T4 · **Size:** S · **OS:** either


#### Wave P1-W3 (1 builder)

**P1-W3-T1 · The P1 gate harness**

- **Advances:** gate P1; R83, R68, R69
- **Owns:** `tests/test_gate_p1.py`, `tests/data/page.html`
- **Uses:** the load generator, `submeter run` (P1-W2-T2), `submeter cost --run`. **Provides:** evidence files in the folder named by `SUBMETER_GATE_DIR`, under the harness contract of section 6.2
- **Work:** The procedures of gate items P1.1 to P1.11 as tests: 500 children busy 50 ms, alive under 1 s, 8 at a time, against the generator within 2%, and the run file's TotalProcesses equal to k0 + 500, where k0 is the TotalProcesses of the same command with 0 children measured in the same test (the interpreter may start a second process of its own, section 7.4); the left-behind process; the first-millisecond grandchild through cmd.exe, 20 of 20 in the job; the run file against the job's own counters (a parsing check); the nested run; the breakaway error recorded; node and bash (skipped with the reason when absent); the browser with a new profile folder, `--headless=new --dump-dom` of `tests/data/page.html`, every msedge.exe sampled in the job (marked `owner_machine`); an agent reading its own cost with canary arguments and folder; the Linux case of P1.11, which runs on CI-L. Built by a builder who built neither the launcher nor the generator.
- **Tests first:** It is the acceptance test. Before merge every case not marked `owner_machine` passes on CI-W, and the P1.11 case on CI-L.
- **Gate evidence:** P1.1 to P1.11
- **Depends on:** P1-W2-T1, P1-W2-T2, P1-W2-T3, P1-W1-T3 · **Size:** M · **OS:** Windows (CI-W) for P1.1 to P1.10; Linux (CI-L) for P1.11; `owner_machine` cases in P1-O1


#### Owner tasks (outside the waves; no builder)

**P1-O1 · Owner: the P1 gate run on the Windows machine** (at the P1 gate commit G1, after P1-W3 integrates)

- **Advances:** gate P1; R68, R141 (the tagged-run cases only the owner's machine can prove)
- **Owns:** `docs/gates/P1/owner/`
- **Uses:** `tests/test_gate_p1.py` (P1-W3-T1), `submeter run` and the load generator, at G1. **Provides:** `docs/gates/P1/owner/`: `checks/` (section 6.2 step 4) and `harness/`, with `P1.<k>.json` for each item under the harness contract of section 6.2 and `pytest.txt`. The gate reviewer reads them for S1 and P1.1 to P1.10
- **Work:** Begins with the owner check run of section 6.2 step 4 at G1. Then runs `tests/test_gate_p1.py` with `-m "soak or not soak"`, so that every case runs, the `owner_machine` cases included (section 6.5), as the standard user. If the browser cannot start its renderers under the job, which R68 expects of some programs, the owner rules whether that fails the gate or is recorded as the known limit L03 (Q7 in section 11).
- **Gate evidence:** S1 on the owner's machine; P1.1 to P1.10
- **Depends on:** every P1 builder task (it runs at G1); decision B16 · **Time:** about 30 minutes · **OS:** the owner's personal Windows 11 PC, as the signed-in standard user, for the evidence; on the work PC only the owner check run of section 6.2 step 4, reported by word (section 3.1, Owner tasks)


### 3.6 P2: collector and raw store

`docs/15-phases-and-decisions.md:37-45`: the bulk snapshot provider, the Windows system counters, the collector loop with adaptive cadence and the overhead guard, the raw files with a nullable column for every catalogue metric version 1 collects, redaction before writing, the baseline attribution with its four fixed buckets and reconciliation, Linux placement of unseen CPU by cgroup if P0 allows it, the full `top` and the fixture recorder. The first wave holds the contract task and R38 with R39, which the sampler, raw store and rollup tasks after it build on. If probe 2 fires the Rust trigger (B2), the build stops before P2 and this phase is planned again.

#### Wave P2-W1 (3 builders)

**P2-W1-T1 · Provider protocols and the P2 records**

- **Advances:** components 01, 02, 03; protocols for 06, 14 and 23; R70, R112, I24, I41
- **Owns:** `src/submeter/core/models.py`, `tests/builders.py`, `tests/test_models.py`, `src/submeter/providers/base.py`, `src/submeter/providers/psutil_provider.py` (its snapshot signature only), `src/submeter/core/limits.py`, `src/submeter/core/config.py`, `tests/test_providers_base.py`, `tests/test_config.py`, `examples/submeter.toml`
- **Uses:** docs/03:51-61, docs/10, docs/17:92, :177; `RunFile` (P1-W1-T2), which `GroupProvider.read` takes. **Provides:** `SystemProvider`, `GroupProvider` and `ExtendedProvider` protocols, with `GroupProvider.read(live_runs)`; `FieldRequest` and the `request` argument of `ProcessProvider.snapshot`; capability names; `choose_providers(platform, enabled)`; `Reconciliation`, `SystemInfo` and the event records, a start event and a hardware-change event among them; `SampleBatch.cadence`; `core.limits`
- **Work:** Protocols for the system counters, group totals and extended providers beside `ProcessProvider`; the collector merges their readings. `GroupProvider.read(live_runs)` takes, each tick, the live runs as `RunFile` records (job name, run id and parent run), which the collector reads with `store.runs` and passes in (P3-W2-T4), so that no provider reads a run file: `providers` is layer 1 and `store` layer 2 (`tests/test_layers.py:15-16`). `ProcessProvider.snapshot` takes no argument today (`src/submeter/providers/base.py:29`); it becomes `snapshot(request: FieldRequest | None = None)`, where `FieldRequest` names the pids that need the total-unit memory, the command line or the working folder this tick, and None asks for none of them, so every existing call stays valid (`scripts/platform_check.py` calls `snapshot()`). In the same change `PsutilProvider.snapshot` (`src/submeter/providers/psutil_provider.py:59`) takes the same `request` argument and ignores it until P2-W2-T2 honours it: under strict mypy a `PsutilProvider` whose `snapshot()` takes no argument no longer satisfies the protocol, and `doctor` passes one to `capability_report` (`src/submeter/cli.py:57-60`, now `cli/doctor.py`); a scratch copy with only `base.py` changed printed `List item 0 has incompatible type "PsutilProvider"; expected "ProcessProvider"`. That signature is the only change this task makes to the file. The sampler builds the request (P2-W3-T3) and the providers honour it (P2-W2-T2, P2-W3-T4). The capability names `doctor` prints (`process.psutil`, the psutil provider's own row, which it reports today (`psutil_provider.py:46`) as the Linux process reader and the Windows fallback, so that `doctor`'s row and `test_cli_runs_end_to_end` stay valid; `process.bulk`, `group.accounting`, `memory.uss`, `gpu.load`, `gpu.memory`, `thermal.temp`, `thermal.throttle`, `net.connections`, `net.bytes`, `vm.guest`), the rule that `process.bulk` is partial while the psutil fallback runs, and `providers.enabled` restricted to those names (empty means all). `choose_providers` names the process and system providers to use, by capability name and without importing a concrete provider: on Windows `process.bulk` with the psutil provider as its fallback, on Linux the psutil provider, each filtered by `providers.enabled`. The collector (P2-W5-T1) and `top` (P2-W5-T2) both call it, because `cli` may not import `programs` (`tests/test_layers.py:20-21`). `SampleBatch` gains the cadence state, active or idle, for the raw rows (P2-W3-T1) and the soak checker (P2-W5-T4). Records: `Reconciliation` (the six terms per batch, I24); `SystemInfo`, read at start: logical cores, memory total and the efficiency class of each logical processor (one class where the system reports none; Q11); and one event record per kind: provider status, clock step, guard action, raw day deleted under the cap, workload change after exec, a start event (a digest of the configured sampling settings, a digest of the rules file, `SystemInfo` and the Submeter version, the items of docs/06:129 that change only at a restart) and a hardware change (the old and new logical cores and memory total), with structured fields only (docs/17:177); and `SystemCounters.throttled`, the flag P2-W2-T3 sets while frequency is held below 80% of base under load (docs/07:120, docs/08:141), None where it is not read. `core/limits.py`: the notes of docs/10 as constants keyed L01 to L13, for the CLI and the report (L00).
- **Tests first:** An unknown capability name and an unknown name in `providers.enabled` are refused, and `process.psutil` is accepted; `PsutilProvider().snapshot(FieldRequest(...))` returns a `Snapshot`, and `PsutilProvider().capability().name` is `process.psutil`; `choose_providers` names the bulk provider then psutil on Windows and psutil on Linux, and leaves out a provider `providers.enabled` does not name; an event record refuses a free-text field; a start event carries both digests and `SystemInfo`; a `FieldRequest` naming one pid for each costly field round-trips, and `snapshot()` with no request asks for none; a fake `GroupProvider` defined in the test is given the live runs as its argument; each record builds with its fields None and set.
- **Gate evidence:** none directly
- **Depends on:** gate P1 · **Size:** M · **OS:** either

**P2-W1-T2 · Gaps and awake seconds**

- **Advances:** components 07, 09, 10, 15, 12; R38 (49 lines), R39 (73 lines), R59, I1, I2, I6, I92
- **Owns:** `src/submeter/collector/sampler.py`, `src/submeter/store/raw.py`, `src/submeter/store/rollup.py`, `src/submeter/attribution/rules.py`, `src/submeter/cli/top.py`, `tests/test_sampler.py`, `tests/test_raw.py`, `tests/test_rollup.py`, `tests/test_attribution.py`, `tests/test_cli_top.py`, `scripts/platform_check.py`, `scripts/probes/bulk_snapshot.py`, `tests/test_probe_bulk.py`
- **Uses:** the gap and awake fields of P0-W3-T1. **Provides:** the gap rule; awake seconds through raw rows and buckets; `system_raw.expected_s`
- **Work:** `Sampler.ingest` takes the interval the caller meant to wait; a tick is a gap past 3 times that plus 2 s, or when the suspend test fires; a gap keeps its CPU and I/O deltas and `cpu_busy_s`; intervals are measured on the clock that counts suspend and awake seconds come from the clock that stops (I2 (a)). `aggregate` passes the gap flag and awake seconds into each `WorkloadSample`; `workload_raw` and `system_raw` gain `gap` and `awake_s`, and `system_raw` gains `expected_s`, the interval the caller meant to wait, all returned by the readers; the soak checker (P2-W5-T4) reads `gap` and `expected_s` with plain SQL. In the rollup every sample goes whole to the bucket that holds its `taken_at`; a gap sample adds its sums and nothing to covered seconds, samples, active seconds, the memory weight or the histograms; `close()` and `merge()` accept `covered_s = 0` without dividing by zero; capacity in core-seconds and CPU and I/O rates are over awake seconds. `top --seconds` passes its wait as the expected interval, so 31 to 60 s no longer prints zeros. The task also changes the calls to `Sampler.ingest` in `scripts/platform_check.py` and `scripts/probes/bulk_snapshot.py`: `uv run mypy src tests` does not check `scripts/`, and their smoke tests (`tests/test_platform_check.py`, `tests/test_probe_bulk.py`) run on every push (section 4.2).
- **Tests first:** A 60 s interval expected at 60 s is not a gap; a 35 s stall at a 1 s cadence is a gap that keeps its CPU (the old gap test rewritten with explicit readings of both clocks, I6); a suspend across a bucket gives `covered_s` ≤ the width and `well_covered` False; an empty bucket closes and merges; a stall's rate stays at or below capacity; `expected_s` round-trips through `system_raw`; `top --seconds 45` prints non-zero CPU for a burner.
- **Gate evidence:** input to P3.1 (the gap case)
- **Depends on:** gate P1 · **Size:** L · **OS:** either

**P2-W1-T3 · The fixture anonymiser**

- **Advances:** components 16; R107; AGENTS.md:44
- **Owns:** `src/submeter/privacy/anonymise.py`, `tests/test_anonymise.py`, `tests/test_fixtures_anonymised.py`
- **Uses:** nothing above layer 1. **Provides:** `anonymise(record)`; the scan of `tests/fixtures/`
- **Work:** Replaces user name, host name, domain name and home folder; replaces executable names outside an allow-list with stable placeholders (the same name gives the same placeholder within one fixture); command lines in exe_only form; working folders dropped. `tests/test_fixtures_anonymised.py` scans every file under `tests/fixtures/` for the current user name, host name, domain name and home folder, as whole tokens, case-insensitively, in UTF-8 and UTF-16-LE, decompressing gzip-compressed fixtures first, and fails on a hit (section 7.3.3). With `SUBMETER_SCAN_EVIDENCE=1`, which the owner tasks set on the recording machine and CI does not, it also scans `docs/review/ground-windows/` and `docs/gates/` outside their `ci/` copies of the runners' own output. On CI the names are the runner's own, expected to be `runner` and `runneradmin` (to be confirmed in the first CI run). `runner` is an ordinary word in the evidence the lead writes: `verdict.md` quotes the gate reviewer word for word, and criteria such as P2.1 (7) name "the runner", so a CI scan of the evidence folders would fail on every push after the first such file. In `tests/fixtures/`, whole tokens keep a name from matching inside a longer word.
- **Tests first:** A recorded-shaped snapshot holding the user, host, home folder and a non-allow-listed executable comes out with none of them; a planted fixture holding the user name fails the scan, as UTF-8, as UTF-16-LE and gzip-compressed; a word that contains the user name inside it passes; with the scan's root pointed at `tmp_path`, a planted file under `docs/gates/P9/` holding the user name is not read without `SUBMETER_SCAN_EVIDENCE` and fails the scan with it set to 1.
- **Gate evidence:** S5
- **Depends on:** gate P1 · **Size:** M · **OS:** either


#### Wave P2-W2 (4 builders)

**P2-W2-T1 · The Windows bulk snapshot provider**

- **Advances:** components 04; R41, R70, R56, I14
- **Owns:** `src/submeter/providers/windows/bulk.py`, `tests/test_bulk.py`, `tests/fixtures/bulk/`
- **Uses:** the P0 prototype (`scripts/probes/bulk_snapshot.py`); `ProcessProvider`. **Provides:** `BulkProvider`
- **Work:** One NtQuerySystemInformation(SystemProcessInformation) call per tick: per process CPU times, CreateTime as the integer start stamp, private bytes, I/O counters, threads, handles, parent pid and image name. pid 0 excluded; pid 4, Registry, MemCompression and Secure System marked System (R41, I14). Falls back to the psutil provider when the call fails and reports `process.bulk` partial while it does; a parse guard fails loudly when a buffer no longer parses (R70). Built only if probe 2 keeps the collector in Python (B2).
- **Tests first:** Parse of a synthetic buffer on both systems, built from structures of fixed-width types whose sizes and field offsets are checked against the values documented for 64-bit Windows (section 7.3.1); pid 0 absent; System marks; a truncated buffer raises the parse error; on CI-W the live call includes the test's own process with a CreateTime equal to GetProcessTimes, and its `ProcessKey` equals the one the psutil provider gives the same process (P0-W4-T1), so a switch to the fallback gives no process a new key (K20); the fallback status is partial.
- **Gate evidence:** P2.2 (bulk provider on the owner's machine)
- **Depends on:** P2-W1-T1, P0-W6-T2; decision B2 · **Size:** L · **OS:** Windows (CI-W)

**P2-W2-T2 · The psutil provider for version 1**

- **Advances:** components 04b; R40, R42, R46, R123, R41, R64, I13, I17, I30
- **Owns:** `src/submeter/providers/psutil_provider.py`, `tests/test_psutil_provider.py`
- **Uses:** `ProcessProvider` and `FieldRequest` (P2-W1-T1); the P2 records. **Provides:** separate field reads, two memory units, System marks, Linux child time; costly fields for the pids a `FieldRequest` names
- **Work:** Separate reads for CPU and memory, the command line, and I/O, each failure leaving only its field None (I13, on R58's structure). Restricted only when an attribution input (command line or owner) is unreadable, or on Linux when the owner differs (I17). The growth unit every tick (private bytes on Windows; RSS plus swap on Linux, from VmSwap) and the total unit (USS on Windows, PSS on Linux) for the pids the `FieldRequest` names, which the sampler sets to the `uss_top_n` largest at `uss_interval` (P2-W3-T3); on Linux PSS for every process only if B6 says so. A pid psutil still lists that raised NoSuchProcess is read again through a fresh `psutil.Process` in the same tick (R123). System marks: pid 4, Registry, MemCompression and Secure System on Windows; kernel threads from PF_KTHREAD in field 9 of `/proc/PID/stat` on Linux (R64). The command line and the working folder are read only for the pids the request names (I30). `PsutilProvider()`, `PsutilProvider(read_cwd=True)` and `snapshot()` with no request stay valid, because `scripts/platform_check.py` calls them (section 4.2). On Linux, each process's child time (psutil's `children_user` plus `children_system`) into `children_cpu_s`, which the sampler's R40 subtraction reads (P2-W3-T3).
- **Tests first:** A refused I/O read keeps CPU and memory; `children_cpu_s` filled on Linux; a kernel-thread fixture is marked System; another user's process is Restricted with its name only; a cached object aged as `docs/review/probes/verify-1/pid_reuse.py` does is read again; the growth unit comes every tick and the total unit only for a pid the request names.
- **Gate evidence:** P2.2 on CI-L
- **Depends on:** P2-W1-T1; decision B6 · **Size:** L · **OS:** either; Linux parts on CI-L

**P2-W2-T3 · Windows system counters**

- **Advances:** components 06; R125, I14, I25; L06, L08, L09
- **Owns:** `src/submeter/providers/windows/system.py`, `tests/test_system.py`, `tests/fixtures/system/`
- **Uses:** `SystemProvider`, `SystemInfo`; PDH through ctypes with English counter names; GetLogicalProcessorInformationEx. **Provides:** `WindowsSystemProvider`; `SystemInfo` on Windows
- **Work:** Per-core busy, idle, interrupt and DPC time, with busy counting interrupt and DPC once (B4); frequency and base frequency, and the throttled signal (held below 80% of base under load, docs/07:120) into `SystemCounters.throttled` (P2-W1-T1), which P2-W3-T1 stores and the `throttled` alert metric reads (P4-W1-T3); commit used and limit; available memory; page reads and writes; disk queue length and latency; run queue; the on-battery flag; System CPU as the System processes' CPU plus interrupt and DPC time, never a remainder (docs/17:129). Capability rows: `thermal.throttle`; `thermal.temp` and `net.*` unavailable. Counters opened by their English names so that a localised Windows works; each source checked in current documentation (docs/17:45). Whether a power-saving plan is active (docs/07:120) is read only if an unprivileged source exists, otherwise unavailable with the reason. `SystemInfo` on Windows: logical cores, memory total, and each logical processor's efficiency class from GetLogicalProcessorInformationEx with RelationProcessorCore, whose `EfficiencyClass` field the builder confirms in current documentation; a processor without classes reports one class (Q11).
- **Tests first:** Parsers from synthetic counter values; on CI-W per-core busy plus idle equals elapsed time within 1% over 2 s; each field None with a reason when its counter is absent; each PDH structure, and the processor-information structure, is built from fixed-width types and its size and field offsets are checked on both systems (section 7.3.1); the efficiency classes parse from a synthetic processor-information buffer with two classes. The on-battery and throttling cases are marked `hardware`.
- **Gate evidence:** inputs to P2.3; L06, L08
- **Depends on:** P2-W1-T1; decision B4 · **Size:** L · **OS:** Windows (CI-W); `hardware` cases on the owner's machine

**P2-W2-T4 · The System bucket, reconciliation, the opaque VM and seeding**

- **Advances:** components 15; R45, R47, R41, R64, R128, I20, I24, I29, I42, I47
- **Owns:** `src/submeter/attribution/rules.py`, `src/submeter/attribution/reconcile.py`, `tests/test_attribution.py`, `tests/test_reconcile.py`
- **Uses:** `Reconciliation`; System marks from the providers, which reach the Attributor on `ProcessSample` (P0-W3-T1's field, copied by P0-W4-T1's sampler). **Provides:** `reconcile(batch, workloads, system)`; `Attributor.seed()`
- **Work:** Processes a provider marks System go to SYSTEM and leave the per-process figures; System CPU comes from the counters. `reconcile.py` computes per batch and per window the six terms: attributed, unattributed, system, restricted, not seen by polling (busy time less the reported workload totals, kernel totals net of child runs, less System) and idle, with the unreadable count beside Restricted (I42). A workload a rule names `opaque:` is labelled OPAQUE with its share of busy CPU time and of capacity (R128). `Attributor.seed()` takes remembered keys and workloads from the raw file's process table and workload-change events before the rules run (I29 (a)).
- **Tests first:** The existing `test_capacity_reconciles_with_a_not_seen_by_polling_term` extended: the six terms sum to capacity; not seen by polling is at least −2% of capacity, and a tagged member counted twice drives it below and is caught; a pid-4 process lands in System; a vmmem process under an opaque rule is OPAQUE; after `seed()` a child whose parent has exited keeps its inherited workload.
- **Gate evidence:** P2.3; the logic of P2.4
- **Depends on:** P2-W1-T1, P2-W1-T2 · **Size:** L · **OS:** either


#### Wave P2-W3 (4 builders)

**P2-W3-T1 · The raw store for version 1**

- **Advances:** components 09, 08; R93, R55 (store part), R45, I8, I9, I24, I41
- **Owns:** `src/submeter/store/raw.py`, `src/submeter/store/files.py`, `tests/test_raw.py`, `tests/test_files.py`, `docs/06-storage.md`
- **Uses:** the P2 records; `SampleBatch`; the per-process fields on `ProcessSample` (handles, GPU load by engine type; P0-W3-T1, copied by P0-W4-T1's sampler), from which `process_raw` is written (`src/submeter/store/raw.py:47-49`). **Provides:** the raw schema of version 1; raw readers; the same-day second file
- **Work:** Nullable columns for every catalogue metric version 1 collects, in schema version 1 (I9): on `process_raw` I/O, handles and GPU load by engine type; on `workload_raw` GPU load by engine type with its missing count; on `system_raw` per-core figures, frequency, the throttled flag (P2-W2-T3), commit, paging, disk, run queue, on-battery, System CPU, not seen by polling (I24), the count of processes whose start time could not be read (I42; `why` and the report show it beside Restricted), and the GPU columns P5 fills. How per-core values and GPU load by engine type are stored while the raw file keeps its eight tables is decided here and written into docs/06 (`docs/13-build-list.md:37` fixes the table list at eight). The `meta` table also holds the `SystemInfo` of the collector that opened the file (logical cores, memory total and each logical processor's efficiency class), which P3-W2-T2 reads for load per core class (Q11). `schema_version` is read when a day's file opens; another version, or another `boot_id`, starts a same-day second file under a name `FileMap` parses (`expired_raw`, `disk_use` and the oldest-raw-day input understand it). `RawStore` never reopens a day earlier than the open file (R55). The rule holds under every option of B8: under (b) and (c) stamps never decrease, and under (a) a batch stamped on an earlier day is written into the open file, so the readers choose the files of a window by each file's first and last tick, not by its name. `system_raw` gains the cadence state, active or idle, from `SampleBatch.cadence`, and keeps `gap`, `awake_s` and `expected_s` (P2-W1-T2) under those names, which the soak checker reads. Event rows are written from the event records, the start and hardware-change events of P2-W1-T1 among them, never as free text from a process. `RawFile(path)` and `close()`, which `scripts/platform_check.py` calls, stay valid (section 4.2). Readers: system rows, process rows, events after a tick, the first and last tick of a file; a closed file is opened only for the length of a query (docs/17:149).
- **Tests first:** A day file with another schema version gives a new file and leaves the old one untouched, and `expired_raw` handles the name; a batch stamped on an earlier day does not reopen the closed file, and a reader of that day's window finds it in the later file; each catalogue column, the cadence state, the unreadable count, the GPU columns of all three tables and `SystemInfo` in `meta` round-trip None and a value; a start event round-trips; an event with a free-text field is refused.
- **Gate evidence:** input to P2.5
- **Depends on:** P2-W1-T1, P2-W1-T2 · **Size:** L · **OS:** either

**P2-W3-T2 · Adaptive cadence and the overhead guard**

- **Advances:** components 07; R76, R87, R142, I41; L04
- **Owns:** `src/submeter/collector/cadence.py`, `src/submeter/collector/guard.py`, `tests/test_cadence.py`, `tests/test_guard.py`
- **Uses:** `Settings.sampling`; the guard event record. **Provides:** `Cadence.next_interval()`; `Guard.observe()` and its actions
- **Work:** Cadence: fixed mode always uses the active interval; adaptive mode the active interval while the machine is busy and the idle interval after `idle_after` of quiet, by the definition of quiet the owner gives (B11); `on_battery_multiplier` stretches every interval; it returns the expected interval the sampler needs and the cadence state, active or idle, that the collector puts on each batch; a cadence change starts no epoch. Guard: the CPU of every Submeter process (the `submeter` workload) as a share of one core per window; above `overhead_limit` (1% idle, 3% active) it first stretches `uss_interval` or shrinks `uss_top_n`, then lengthens the active and idle intervals, and emits a guard event (a finding later, not an epoch); it tracks the collector's private bytes against its share of 150 MB (157,286,400 bytes).
- **Tests first:** An injected tick cost of 95 ms at 2 s makes the guard act in the stated order and settle at or below 3% (the Linux figure of L04 is about 3.2 s active and 9.5 s idle); fixed mode never changes the interval; the on-battery multiplier applies to both intervals.
- **Gate evidence:** P2.1
- **Depends on:** P2-W1-T1; decision B11 · **Size:** M · **OS:** either

**P2-W3-T3 · The sampler for version 1**

- **Advances:** components 07; R40, R142, I3, I12, I30
- **Owns:** `src/submeter/collector/sampler.py`, `tests/test_sampler.py`
- **Uses:** `children_cpu_s` and the memory units of P2-W2-T2; `FieldRequest` (P2-W1-T1). **Provides:** per-core busy and awake seconds in `SampleBatch`; the costly-field schedule as one `FieldRequest` per tick
- **Work:** Per-core busy and awake seconds into `SampleBatch`. `Sampler()` and `Sampler.ingest(snapshot, expected_s)` keep their signatures, which `scripts/platform_check.py` and the probe of P0-W6-T2 call (section 4.2). The costly-field cadence, as the `FieldRequest` the sampler builds for the next tick: USS or PSS for the largest processes at `uss_interval`; command lines on Windows once per new process and on Linux again at `uss_interval`, with R47's rule retry on the read that shows a change; the working folder only when a rule uses `cwd`. Linux reaped children (R40): credit the increase of each process's child time, subtract a reaped child's last-seen CPU, child time and I/O from its reaper's next increase, and never recover more than busy time less credited CPU.
- **Tests first:** The nested-reaping fixture through the psutil provider's output (Linux); the same cumulative counters sampled at 2 s and at 5 s give equal CPU totals (docs/17:98); per-core values sum to the machine total; the request names USS pids only on USS ticks; on Linux a process's command line is asked for again at `uss_interval`, and a changed command line under the same pid reaches the rules (I30, R47).
- **Gate evidence:** P2.2, P2.3 inputs
- **Depends on:** P2-W1-T2, P2-W2-T2 · **Size:** M · **OS:** either; R40 on CI-L

**P2-W3-T4 · Windows command lines and costly fields**

- **Advances:** components 04; R126, R46, I17, I30
- **Owns:** `src/submeter/providers/windows/cmdline.py`, `src/submeter/providers/windows/bulk.py`, `tests/test_cmdline.py`, `tests/test_bulk.py`
- **Uses:** `BulkProvider`; `FieldRequest` (P2-W1-T1). **Provides:** command lines with limited access; USS and working folder for the pids a `FieldRequest` names
- **Work:** A command line is read once, when a process is first seen, with PROCESS_QUERY_LIMITED_INFORMATION and NtQueryInformationProcess(ProcessCommandLineInformation), never PROCESS_VM_READ; a refused read marks the process restricted (I17). USS for the pids the request names, the `uss_top_n` largest at `uss_interval` (psutil's USS read opens with PROCESS_QUERY_INFORMATION, a stated exception, docs/17:92); the working folder for the pids the request names, which it names only when a rule uses `cwd`.
- **Tests first:** On CI-W: the reader returns the test's own command line; the access mask passed to OpenProcess is PROCESS_QUERY_LIMITED_INFORMATION (the test intercepts the call); a refused read gives restricted.
- **Gate evidence:** `docs/17-build-prompt.md:92`; the owner's Defender log check in P2-O2
- **Depends on:** P2-W2-T1 · **Size:** M · **OS:** Windows (CI-W)


#### Wave P2-W4 (4 builders)

**P2-W4-T1 · Control files and logs**

- **Advances:** components 08, 16; R98, R100, R120, I77
- **Owns:** `src/submeter/store/control.py`, `src/submeter/store/logs.py`, `src/submeter/store/files.py`, `tests/test_control.py`, `tests/test_logs.py`, `tests/test_files.py`
- **Uses:** `FileMap`, `write_atomic`. **Provides:** `FileMap.control_dir` (`control/` under the state folder), `FileMap.sessions_dir` (`control/sessions/`), `FileMap.stop_file(program)` and `FileMap.backup_request` (`control/backup`); `request_stop`, `stop_requested`, `clear_stop`; `program_logger(program)`
- **Work:** `FileMap` gains the control folder, its `sessions` subfolder, the two stop files and the backup request (`docs/06-storage.md:49-55`), and `ensure()` creates both folders 0700 (R100), because `FileMap` is the only place a path is built (`src/submeter/store/files.py:3-6`, section 4.2) and today it has no control path (`files.py:66-125`); P3-W2-T3 uses the sessions folder and the backup request without holding `files.py`. `control/stop-collector` and `control/stop-server` under the state folder (presence is the request; the program removes it on a clean exit). Rotating logs, 5 files of 5 MB (5,242,880 bytes) per program in `FileMap.logs_dir`, created 0600, with a formatter that names a process by pid and executable only and logs validation errors without input values.
- **Tests first:** `FileMap` names `control/stop-collector`, `control/stop-server`, `control/sessions/` and `control/backup` under the state folder, and under `SUBMETER_HOME` when it is set; `ensure()` creates `control/` and `control/sessions/` with mode 0700 on POSIX; a stop request is seen and cleared; rotation at 5,242,880 bytes keeps 5 files; a log record carrying a command line comes out without it.
- **Gate evidence:** none directly (`docs/06-storage.md:18`, `docs/17-build-prompt.md:177`)
- **Depends on:** P1-W1-T2 · **Size:** M · **OS:** either

**P2-W4-T2 · Linux extras and the conditional busy-time changes**

- **Advances:** components 04b, 06, 15; R60, R125, R51, I12, I14, I22, I37
- **Owns:** `src/submeter/providers/psutil_provider.py`, `src/submeter/attribution/reconcile.py`, `tests/test_psutil_provider.py`, `tests/test_reconcile.py`
- **Uses:** P2-W2-T2, P2-W2-T4; `SystemInfo` (P2-W1-T1). **Provides:** on-battery flag, irq and softirq time; `SystemInfo` on Linux; cgroup placement if kept
- **Work:** The on-battery flag from `psutil.sensors_battery()` and irq plus softirq time for System; commit unavailable on Linux (R51). If B5 keeps R60: each tick, read every leaf cgroup's `cpu.stat` and each process's cgroup, and in `reconcile.py` charge a cgroup's increase less its processes' polled deltas to the one workload that owns all of its processes, otherwise leave it in not seen by polling, never in System. The cgroup increases reach `reconcile` as an optional keyword argument, so the calls of P2-W2-T4's tests and of the fixture recorder (P2-W4-T3, same wave) stay valid. If B4 says interrupt and DPC time is inside system time: subtract it in the Windows busy sum (`psutil_provider.py:147-157`). Either way, R41's check runs again as a CI-W test in `tests/test_psutil_provider.py`: over 5 s the summed CPU of every process the provider reads stays within the machine's busy time, as B4 defines it, plus 5%; the owner runs `scripts/platform_check.py` again at G2 (P2-O2). On Linux, `SystemInfo` from psutil: logical cores, memory total and one efficiency class.
- **Tests first:** A Linux fixture of cgroup increases against polled deltas; the on-battery flag None without a battery; the Windows busy sum from a fixture with and without the subtraction; on CI-W, R41's check with the busy sum B4 sets; `SystemInfo` on Linux reports one efficiency class.
- **Gate evidence:** P2.3 inputs
- **Depends on:** P2-W2-T2, P2-W2-T4; decision B4, B5 · **Size:** M · **OS:** Linux (CI-L) and Windows (CI-W) parts

**P2-W4-T3 · The fixture recorder**

- **Advances:** tools beside the code: fixture recorder (docs/13:50); R107, R136
- **Owns:** `tests/tools/record_fixture.py`, `tests/test_record_fixture.py`
- **Uses:** `privacy.anonymise`; the provider protocols of P2-W1-T1; the bulk, system and psutil providers; `Sampler`, `Attributor`, `aggregate` and `reconcile` (P2-W2-T4) as they stand at the wave's base commit, whose signatures P2-W4-T2 and P2-W4-T4 keep in the same wave; `examples/rules.toml`. **Provides:** `uv run --directory tests python -m tools.record_fixture <module>:<class> [--system <module>:<class>] --ticks N`, the form plan choice C3 gives every tool; the fixture format of section 7.3.3
- **Work:** Loads the named provider class, which implements one of the protocols of P2-W1-T1 (process, system, group or extended), so that P5-O1 records the Windows GPU provider with no change here. With `--system` it also loads a system provider and reads both on each tick, so that one fixture holds the process readings and the system counters of the same ticks, which reconciliation needs (P2.4). Saves the readings for N ticks as JSON Lines under `tests/fixtures/recorded/<name>/`, a path resolved from the tool's own location, not the working folder, through the anonymiser, with `manifest.json` (the provider classes, process count, core count, Windows build and the digest of the rules file) and `expected.json` beside it (section 7.3.3). For a fixture with process readings and system counters, `expected.json` holds, for each tick, the CPU of each workload and the six reconciliation terms, computed at recording time by feeding the readings through `Sampler`, `Attributor` with `examples/rules.toml`, `aggregate` and `reconcile`; for any other fixture it holds the parsed readings. A file over 1 MB is stored gzip-compressed; refuses to write if the scan finds the current user, host or domain name or home folder.
- **Tests first:** Recording the psutil provider with `--system` and a fake system provider defined in the test, for 3 ticks into `tmp_path`, gives one fixture with both readings for each tick, a manifest naming both providers, and an `expected.json` whose six terms for each tick equal those a direct call of `reconcile` on the same readings gives and sum to capacity within 2%; the files pass the scan; a fake extended provider records the same way, with its parsed readings in `expected.json`; a planted user name makes it refuse.
- **Gate evidence:** S5
- **Depends on:** P2-W1-T3, P2-W2-T1, P2-W2-T2, P2-W2-T3, P2-W2-T4, P2-W3-T3 · **Size:** M · **OS:** either; Windows fixtures are recorded in P2-O1

**P2-W4-T4 · Anchored batch stamps and clock steps**

- **Advances:** components 07; R55 (built at 47 lines and reverted), I6, I92; L13
- **Owns:** `src/submeter/collector/sampler.py`, `tests/test_sampler.py`
- **Uses:** the clock-step field of `SampleBatch`. **Provides:** stamps that never go backwards silently; the clock-step flag
- **Work:** `taken_at` is the wall time at an anchor plus the elapsed time on the interval clock; a departure beyond 2 s without suspend is a clock step, flagged on the batch for an event row that starts an epoch; re-anchor after a step forward. `Sampler()` and `Sampler.ingest(snapshot, expected_s)` keep their signatures, which the fixture recorder (P2-W4-T3, same wave) and `scripts/platform_check.py` call. The rule after a backward step and for slow drift is the owner's (B8): the reverted attempt left `taken_at` 1 h ahead after a 1 h step back and drifted +130 s in 30 days at +50 ppm (docs/review/02-rulings.md:282).
- **Tests first:** A step forward and a step back each flag a clock step; after a step back the stamps follow the rule B8 sets; 30 days of +50 ppm drift stay within the bound B8 sets.
- **Gate evidence:** L13; `docs/17-build-prompt.md:100`
- **Depends on:** P2-W3-T3, P2-W3-T1; decision B8 · **Size:** M · **OS:** either


#### Wave P2-W5 (4 builders)

**P2-W5-T1 · The collector program**

- **Advances:** components 07, 03, 15; R47, R54, R87, R88, R98, R113, R120, R142, I29, I45, I61, I63
- **Owns:** `src/submeter/programs/collector/__init__.py`, `src/submeter/programs/collector/__main__.py`, `src/submeter/programs/collector/loop.py`, `pyproject.toml`, `uv.lock`, `tests/test_collector_program.py`
- **Uses:** every P2 library, among them `choose_providers` (P2-W1-T1), the anchored stamps and clock-step flag (P2-W4-T4) and the Linux extras (P2-W4-T2); `store.runs` (live run files); `store.control`; `store.logs`. **Provides:** `submeter-collector = "submeter.programs.collector:main"`; raw files; event rows; the tick log
- **Work:** Instance lock and pid file; settings and rules read only at start; the process and system providers that `choose_providers` names; every process read every tick, costly fields on their cadence; attribution with `self_pids` from the pid files and the holder pids in live run files, each matched on pid and start stamp (I45), seeded at start from the open raw file (I29); aggregate and the reconciliation figures into `system_raw`; `RawStore.write`; event rows for provider-status changes, clock steps, guard actions, raw days deleted under the cap and workload changes; a start event when it starts (P2-W1-T1: the settings and rules digests, `SystemInfo` and the version), and a hardware-change event when `SystemInfo`, read again at each `uss_interval`, differs in logical cores or memory total; `SystemInfo` passed to the raw store for each file's `meta` table; polls `control/stop-collector` each tick and removes it on a clean exit; deletes its own raw files older than the larger of 7 days and `retention.raw`, with an event row (R88, I61); logs without command lines; a failed write never fails the tick (R54); the cadence state on each batch. When the environment variable `SUBMETER_TICK_LOG` names a file, the collector appends `begin <tick id>` before each write transaction and `commit <tick id>` after it commits, flushed before the next tick, for the kill test (P2-W6-T1).
- **Tests first:** The loop for 5 ticks with a fake provider in `tmp_path`: rows written; with `SUBMETER_TICK_LOG` set, each committed tick has a `begin` line and then a `commit` line; a stop file stops it within one tick and is removed; a restart keeps a child's inherited workload after its parent exited (R47); raw files 8 days old deleted with `retention.raw = 2d` and kept with `10d`; a holder pid from a live run file is attributed to `submeter`; the start event carries the settings and rules digests; a fake system provider whose core count changes gives one hardware-change event.
- **Gate evidence:** P2.1, P2.2, P2.3, P2.5, P2.6
- **Depends on:** P2-W3-T1, P2-W3-T2, P2-W3-T3, P2-W2-T1, P2-W2-T3, P2-W2-T4, P2-W4-T1, P2-W4-T2, P2-W4-T4; decision B2 · **Size:** L · **OS:** either

**P2-W5-T2 · The full `top`**

- **Advances:** components 12; R42, R46, R65, R66, I42; L00, L01, L02, L04, L10, L11, L12
- **Owns:** `src/submeter/cli/top.py`, `tests/test_cli_top.py`
- **Uses:** the providers, `choose_providers`, `aggregate`, `reconcile`, `core.limits`, `cli._format`. **Provides:** `submeter.top/1`
- **Work:** Keeps taking its own two snapshots, so it works without the collector (plan choice C1), through the same provider choice as the collector (`choose_providers`, P2-W1-T1); n/a and partial marks with missing counts; the memory unit named (private bytes, or RSS plus swap; USS or PSS with the age of the reading, L12); System, Restricted, Unattributed and Submeter always shown, with not seen by polling beside them (docs/17:127); known-limit notes beside the numbers they affect: work done for an agent by another process, beside `agent:*` totals (L01, `docs/10-known-limits.md:9`), polled (L02), Linux (L04), Restricted and System (L10), I/O per process with no record of which files (L11), memory age (L12). L03 does not apply here: `top` takes its own snapshots and shows no tagged run (C1).
- **Tests first:** A snapshot of `top`, kept in `tests/test_cli_top.py`, with a Restricted member lacking memory (n/a), a partial I/O figure with its count, the L11 note beside the I/O figures, the L01 note beside an `agent:*` workload, and the four fixed rows present with no members.
- **Gate evidence:** section 1, rows D3 and D13
- **Depends on:** P2-W2-T4, P2-W1-T1, P2-W2-T1; plan choice C1 · **Size:** M · **OS:** either

**P2-W5-T3 · `doctor` for phase 2**

- **Advances:** components 12; R77, R128, I42; L09, L10
- **Owns:** `src/submeter/cli/doctor.py`, `tests/test_cli_doctor.py`
- **Uses:** the capability rows of each provider. **Provides:** the capability matrix as far as P2
- **Work:** Rows for `process.bulk` (partial while the fallback runs), `memory.uss`, `thermal.throttle`, `thermal.temp` (unavailable), `net.*` (unavailable, not in version 1) and `vm.guest`; the restricted and unreadable counts; the collector's own cost from its last raw rows; on Linux, hidepid from the `/proc` mount options (R77).
- **Tests first:** Rows and statuses on each system; hidepid read from a fixture mount line.
- **Gate evidence:** L09, L10
- **Depends on:** P2-W1-T1, P2-W2-T1, P2-W2-T3 · **Size:** M · **OS:** either

**P2-W5-T4 · Soak monitor and soak checker**

- **Advances:** tools beside the code: the soak harness the P2 and P3 gates need; R117, R87, R118
- **Owns:** `tests/tools/soak/`, `tests/test_soak_tools.py`
- **Uses:** psutil; sqlite3 directly, on the `system_raw` columns `interval_s` (the baseline's), `gap`, `awake_s` and `expected_s` (P2-W1-T2) and `cadence` (P2-W3-T1), all merged before this wave; nothing from `submeter`. **Provides:** `python -m tools.soak monitor` (CSV every 10 s) and `python -m tools.soak check`
- **Work:** The monitor finds the Submeter processes of the budget: the pids in the state folder's pid files and the holder pids in live run files, each matched on its start stamp (I45), their children, and on Windows the console-script launcher or virtual-environment redirector each was started through (section 7.4). It records the launcher of `submeter run` and any CLI process apart, reported and not judged, until R69 in section 11.7 is answered (K49). Every 10 s it records each process's CPU times, private bytes on Windows or USS on Linux, open sockets and, on Windows, token elevation; the machine's process count (`docs/15-phases-and-decisions.md:25`: "The CI soak states its process count"); and the checkpoint sequence number and salts in the 32-byte header of each open raw file's `-wal`, whose change marks a restart of the log after a checkpoint. The checker applies the rules of P2.1 and P2.6 (section 6.6). The numbers that differ between the CI soak and the owner's are options, whose defaults judge nothing extra, so that neither run takes the other's numbers by default: `--window SECONDS` (no default; it must be given), `--skip SECONDS` (default 0), `--min-idle-windows N` (default 0), `--min-processes N` (default 0, no minimum), `--expect-holder` (default off), `--judge-elevation` (default off) and `--sleep FILE` (default none). Both callers write every option out: `soak.yml`'s driver passes `--window 60 --skip 120 --min-idle-windows 5 --min-processes 300`, with `--expect-holder` on CI-W only (P2-W6-T2), and the owner's command of section 6.6 passes `--window 600 --skip 0 --min-idle-windows 0 --min-processes 0 --judge-elevation --sleep <sleep.txt>`. The rules: each window of `--window` seconds from `--skip` seconds after the start has summed CPU under 3% of one core if any tick in it ran at the active cadence and under 1% if all ran at the idle cadence, the cadence read from the raw rows; at least `--min-idle-windows` windows are judged at the idle limit; the machine's process count is at least `--min-processes` at every minute; with `--sleep`, the two times in the file (written just before the sleep and just after waking) mark the sleep, every window that overlaps the span from the first time to the end of the first gap tick after it is left out of the CPU rule and listed as left out, and P2.6 (6) is judged: exactly one gap tick ends between the first time and 60 s after the second, and its `interval_s` less its `awake_s` is at least the noted sleep (the time between the two entries) less 120 s and at most the noted sleep plus 2 s, and the checker prints that tick's interval, its awake seconds, the noted sleep and the verdict; collector plus server under 157,286,400 bytes at every sample; with `--expect-holder`, which CI-W's soak passes, at least one holder pid among the processes measured (P2.1 (6)); 0 sockets; a token that is not elevated, judged only with `--judge-elevation`, which the owner's soaks pass and CI-W's does not, because its runner is an administrator (R118); memory growth from the median of hours 1-2 to the median of hours 23-24; every tick whose interval is longer than three times its expected interval plus 2 s carries the gap flag, the rule of `docs/05-data-flow.md:43`; the longest time between restarts of each raw file's write-ahead log; `PRAGMA integrity_check` ok.
- **Tests first:** The checker on a synthetic CSV and on a raw file the test writes with `RawFile` in P2-W3-T1's schema (the tools import nothing from `submeter`; their test may), so that the checker's SQL is tested against the columns the collector writes: a window at 3.1% fails and at 2.9% passes; with only `--window` given, the defaults skip nothing, require no idle window and no process count; the CI set (`--window 60 --skip 120 --min-idle-windows 5 --min-processes 300`) fails a machine of 120 processes and leaves the first 120 s unjudged, and the owner's set (`--window 600 --skip 0 --min-idle-windows 0 --min-processes 0 --judge-elevation`) passes the same machine and judges from the first second; with `--sleep` naming a file whose two times are 600 s apart, one gap tick of 900 s `interval_s` and 302 s `awake_s` ending 20 s after the second time passes P2.6 (6) and the windows across it are left out of the CPU rule and listed, the same tick with 880 s `awake_s` fails (6), and a sleep file with no gap tick ending between its first time and 60 s after its second fails (6); a window with one active tick is judged at 3%; a tick at three times its expected interval plus 3 s without the gap flag is reported, and one at three times plus 1 s is not; elevation is reported but not judged without `--judge-elevation`; a change of the `-wal` header counts as a checkpoint; `--expect-holder` fails when no holder pid was sampled; the monitor samples its own process.
- **Gate evidence:** P2.1, P2.6, P3.5; fixed rules 2 and 3 at run time
- **Depends on:** P2-W1-T2, P2-W3-T1 · **Size:** L · **OS:** either


#### Wave P2-W6 (4 builders)

**P2-W6-T1 · The kill test**

- **Advances:** gate P2; R89
- **Owns:** `tests/test_kill.py`
- **Uses:** `submeter-collector`; its tick log (`SUBMETER_TICK_LOG`, P2-W5-T1). **Provides:** evidence for P2.5, under the harness contract of section 6.2
- **Work:** Starts the collector with a test settings folder and a tick log, in fixed mode at an active interval of 1 s with `overhead_limit` at 10%, the top of its range (`docs/08-configuration.md:56-57`, `:66`): at 1 s the guard acts only above 100 ms of CPU a tick, which is more than psutil's 95.1 ms a tick at 300 processes [Linux], and the test adds no load, so the interval stays at 1 s. It kills the collector (`Popen.kill`: TerminateProcess on Windows, SIGKILL on Linux) after a random 1 to 60 committed ticks, counted from the tick log, in each of 50 trials. Each trial: `PRAGMA integrity_check` returns ok, 0 ticks with a `commit` line are missing from the raw file, and the next start reopens the day file, commits one tick and stops through its stop file. Reports how many kills fell inside a write transaction (a `begin` line with no `commit`), and each tick's interval, so that a guard action would show. Time: at most 3,100 ticks (52 minutes at 1 s) and 100 start-ups, budgeted at 5 s each (8 minutes): at most about 60 minutes, about 35 on average. The 50 trials are marked `soak` and run in the soak workflow's `soak-tests` job (P2-W6-T2) from the gate commit; a variant of 3 trials, each killed after 1 to 5 ticks (at most 21 ticks and 6 start-ups, about 51 s), carries no mark and runs in CI's main job, so that the test runs on both runners before merge. Built by a builder who built neither the collector nor the raw store.
- **Tests first:** It is the acceptance test. Before merge the 3-trial variant passes on CI-W and CI-L; the 50 trials run in the soak workflow at the gate (P2.5).
- **Gate evidence:** P2.5
- **Depends on:** P2-W5-T1 · **Size:** M · **OS:** either

**P2-W6-T2 · The CI soak workflow and the measured raw-store cost**

- **Advances:** tools beside the code: CI soak; R117, R118, R78, R89, I54, I55, I64
- **Owns:** `.github/workflows/soak.yml`, `tests/tools/soak_schedule.py`, `tests/test_soak_workflow.py`, `docs/06-storage.md`, `docs/05-data-flow.md`
- **Uses:** the load generator, the soak tools, the collector. **Provides:** a 30-minute soak on both runners and a job that runs every `soak` test; `uv run --directory tests python -m tools.soak_schedule`, the soak's steps as one driver that the workflow and its dry run both call; rows and bytes per tick; the longest time between checkpoints
- **Work:** A separate workflow, run by manual dispatch and by pushes to branches named `gate/*` and `soak/*`, with two jobs on both runners, which run at the same time on separate runners (section 7.5). The job `soak`, limited to 120 minutes: the driver brings the machine to at least 300 processes with the generator's `idle` mode; runs the collector 30 minutes (minutes 0-10 active load, 10-20 quiet, 20-30 active with the spawner); runs one `submeter run` of the generator's `background` mode during it, whose left-behind process burns for at least 30 s after the command exits, so that on CI-W the launcher starts a holder that the 10 s monitor samples (P2.1 (6)); on CI-L `submeter run` runs the command polled and starts no holder; runs the soak monitor every 10 s and the checker at the end with the rules of P2.1 (section 6.6) and every option written out, `--window 60 --skip 120 --min-idle-windows 5 --min-processes 300`, with `--expect-holder` on CI-W only (P2-W5-T4). It keeps the CSV, the checker output, the raw files' tick intervals and the event rows as the artefacts `soak-windows` and `soak-linux`. The job `soak-tests`, limited to 150 minutes, runs `uv run pytest -m soak` with `SUBMETER_GATE_DIR` set: the kill test, the 10-minute case of P2.2, this task's dry run and, from later phases, every other `soak` case; it keeps the folder `SUBMETER_GATE_DIR` names as `soak-tests-windows` and `soak-tests-linux`. Measures rows and bytes per tick and the longest time between checkpoints of the raw file's write-ahead log (the monitor's `-wal` header), and writes the measured figures into docs/06's disk table, into the "Volume per day" column of `docs/05-data-flow.md:78-87` in place of its estimates, and beside docs/06's power-loss promise, which says the few minutes are "to be confirmed at the shipped cadence" (`docs/06-storage.md:39`; R89, I64). Beside the figures it names the `soak.yml` run they come from, by run id and commit, and its task report names the same run, so that the gate step can copy that run's artefacts as P2.8's evidence (section 6.6).
- **Tests first:** `tests/test_soak_workflow.py`: a dry run of the driver for 60 s, marked `soak` (the branch is also pushed as `soak/P2-W6-T2`, so that the workflow runs before merge; section 7.5); a check of `soak.yml` as text for both triggers, both runner labels, the jobs `soak` and `soak-tests`, `-m soak` in `soak-tests`, the 120-minute limit of `soak` and the 150-minute limit of `soak-tests`, and the generator's `background` mode in the tagged run; the checker's argument list the driver builds holds `--window 60 --skip 120 --min-idle-windows 5 --min-processes 300` on both systems and `--expect-holder` on Windows only.
- **Gate evidence:** P2.1, P2.8; the runs of P2.2's 10-minute case and of P2.5
- **Depends on:** P2-W5-T1, P2-W5-T4, P1-W1-T3; decision B11 · **Size:** M · **OS:** either (both runners)

**P2-W6-T3 · The P2 gate harness**

- **Advances:** gate P2; R83, R45, R117
- **Owns:** `tests/test_gate_p2.py`
- **Uses:** the generator's `burn` mode, the collector, the raw readers. **Provides:** evidence for P2.2 to P2.4 and P2.7, under the harness contract of section 6.2
- **Work:** P2.2: burners at 5%, 15%, 25%, 50% and 100% of a core reporting every 1 s; the checker interpolates to the first and last tick; each burner set above 10% of a core (15%, 25%, 50% and 100%, chosen by the share it was set to, never by the share measured) within 5% or 0.05 s over 10 minutes; the 5% burner is reported, not judged. The 10-minute case is marked `soak` and runs in the soak workflow's `soak-tests` job; a 60 s variant carries no mark and runs on every push. P2.2's parsing check (`docs/15-phases-and-decisions.md:41`), on CI-W and the owner's machine only: for each burner, the provider's CPU reading against the burner's `\Process(<instance>)\% Processor Time` counter read raw through PDH at the same tick, the instance found by `\Process(*)\ID Process`. That counter's type is PERF_100NSEC_TIMER, whose raw value is the process's processor time in 100 ns units (the builder confirms this in current documentation), so the two compare directly in those units; the harness opens the counter through ctypes itself, not through P2-W2-T3's provider. P2.3: the six terms within 2% of capacity and not seen by polling at least −2% in every 60 s window. P2.4: the quiet fixture's process readings and system counters, which P2-O1 records together, are fed tick by tick through the sampler, attribution, `aggregate` and `reconcile`, and the not-seen share stays under the bound in `tests/fixtures/recorded/quiet/bound.json`, committed before the recording. P2.7, redaction: a burner whose arguments hold `--password=CANARY-<uuid>`, run once in `exe_only` mode and once in `scrub`, in a working folder named `CANARY-cwd-<uuid>` and holding open a file named `CANARY-file-<uuid>`; afterwards none of the three occurs, as UTF-8 or as UTF-16-LE bytes, in any `.db`, `-wal`, `-shm` or log file, which also shows that no record holds a file a process touched (L11).
- **Tests first:** It is the acceptance test; CI-W and CI-L cases pass before merge, the 10-minute case through the soak workflow at the gate.
- **Gate evidence:** P2.2, P2.3, P2.4, P2.7
- **Depends on:** P2-W5-T1, P1-W1-T3, P2-O1 · **Size:** M · **OS:** either; the bulk-provider case in P2-O2

**P2-W6-T4 · Replay tests on the recorded fixtures**

- **Advances:** components 04, 04b, 06; R107
- **Owns:** `tests/test_recorded_fixtures.py`
- **Uses:** `tests/fixtures/recorded/` from P2-O1. **Provides:** parse and logic tests on real Windows output, on both systems
- **Work:** Each recorded fixture whose manifest names the bulk, system or psutil provider parses. For a fixture holding process readings and system counters, both are fed tick by tick through the sampler, attribution, `aggregate` and `reconcile`, and each tick's workload CPU and six terms equal `expected.json`; any other fixture's parsed readings equal `expected.json`. The GPU fixtures of P5-O1 are replayed by the P5 gate harness (P5-W4-T1).
- **Tests first:** Fails before the fixtures exist; passes once P2-O1 has committed them.
- **Gate evidence:** P2.4 replay
- **Depends on:** P2-W4-T3, P2-O1 · **Size:** S · **OS:** either


#### Owner tasks (outside the waves; no builder)

**P2-O1 · Owner: record fixtures on the Windows machine** (after P2-W4 integrates)

- **Advances:** tools beside the code: recorded fixtures for the bulk provider, the system counters and the psutil fallback (`docs/13-build-list.md:50`); R107, R117
- **Owns:** `tests/fixtures/recorded/`, `docs/gates/P2/owner/anonymised-P2-O1.txt`
- **Uses:** the fixture recorder (P2-W4-T3) with the bulk provider (P2-W2-T1), the system counters (P2-W2-T3) and the psutil provider (P2-W2-T2); the load generator's `burn`, `io` and `memory` modes (P1-W1-T3); `tests/test_fixtures_anonymised.py` (P2-W1-T3); all at the P2-W4 integration commit. **Provides:** under `tests/fixtures/recorded/<name>/`, JSON Lines holding each tick's process readings and system counters, gzip-compressed over 1 MB, with `manifest.json` and `expected.json` beside them (section 7.3.3): the 10-minute quiet fixture, with `quiet/bound.json` committed first, which P2-W6-T3 replays for P2.4; every fixture, which P2-W6-T4 replays; the counter sets of the CPU-, I/O- and memory-bound loads and of the idle machine, from which P4-W1-T2 builds the verdict fixtures. Also `docs/gates/P2/owner/anonymised-P2-O1.txt` for S5
- **Work:** First commits the quiet fixture's bound, `tests/fixtures/recorded/quiet/bound.json` (5% of capacity unless the owner sets another; section 6.6), on the branch `owner/P2-O1`, before any recording (P2.4). Then runs the fixture recorder with `--system`, for the bulk provider with the system counters and for the psutil fallback with them, so that each fixture holds the process readings and the system counters of the same ticks; the 10-minute quiet fixture for P2.4 is recorded the same way, with the bulk provider; system-counter sets for P4's verdict fixtures, each at least 6 minutes long, while the load generator runs a CPU-bound load (`burn`), an I/O-bound load (`io`) and a memory-bound load (`memory`, only if the owner agrees to load the personal PC that way, Q14; otherwise the memory-bound verdict fixture is synthetic, P4-W1-T2), and while the machine is idle; on battery if the machine is a laptop. Runs `tests/test_fixtures_anonymised.py` on that machine before committing and saves its output as `docs/gates/P2/owner/anonymised-P2-O1.txt` (S5).
- **Gate evidence:** S5; inputs to P2.4 and P4.1
- **Depends on:** P2-W4-T3 · **Time:** about 1 hour · **OS:** the owner's personal Windows 11 PC only, as the signed-in standard user; not run on the work PC (section 3.1, Owner tasks)

**P2-O2 · Owner: the 24-hour soak and the bulk-provider checks** (at the P2 gate commit G2, after P2-W6 integrates)

- **Advances:** gate P2; R41 (R41's check again after B4), R87, R89, R126 (the Defender log)
- **Owns:** `docs/gates/P2/owner/`, except `anonymised-P2-O1.txt`, which P2-O1 commits before P2-O2 starts
- **Uses:** `tests/test_gate_p2.py` (P2-W6-T3), the collector (P2-W5-T1), the soak monitor and checker (P2-W5-T4) and `scripts/platform_check.py`, at G2. **Provides:** `docs/gates/P2/owner/`: `checks/`; `harness/` with `P2.2.json`, `P2.3.json` and `P2.4.json`; `soak/monitor.csv`, `soak/check.txt` and `soak/sleep.txt`; `platform-check.txt`; `defender-asr.txt`. The gate reviewer reads them for S1, P2.2 to P2.4 and P2.6
- **Work:** Begins with the owner check run of section 6.2 step 4 at G2. Then `tests/test_gate_p2.py` in full, with `-m "soak or not soak"` (section 6.6): P2.2 with the bulk provider as the standard user, P2.3 and P2.4; `scripts/platform_check.py` again, saved as `platform-check.txt`, which repeats R41's check after B4 (P2-W4-T2); the 24-hour soak with one sleep of at least 5 minutes, the soak monitor and the checker with the owner's options of section 6.6, `--judge-elevation` and `--sleep` among them; integrity checks after the collector is stopped; the Defender log query again.
- **Gate evidence:** S1 on the owner's machine; P2.2, P2.3, P2.4, P2.6
- **Depends on:** every P2 builder task (it runs at G2) · **Time:** 24 hours elapsed, under 1 hour attended · **OS:** the owner's personal Windows 11 PC, as the signed-in standard user, for the evidence; on the work PC only the owner check run of section 6.2 step 4, reported by word (section 3.1, Owner tasks)


### 3.7 P3: attribution rules, history, sessions

`docs/15-phases-and-decisions.md:47-57`: the server with the history file, its integrity check, hourly rollup, retention, disk budget, backups, epochs and the copying of run files; the attribution rules; sessions through marker files; the collector's reading of live groups with re-attach; and the synthetic store generator. The history DDL is the first task, with one owner (`docs/15-phases-and-decisions.md:51`). `daemon`, `rules test`, `store check` and `store backup` have no phase in the brief; this plan builds them here, where both programs first exist.

#### Wave P3-W1 (4 builders)

**P3-W1-T1 · The history DDL and its records**

- **Advances:** components 26, 10, 01; R93, R103, R121, R122, R94, I62, I67; `docs/15-phases-and-decisions.md:51` (the first task of P3, one owner)
- **Owns:** `src/submeter/core/models.py`, `tests/builders.py`, `tests/test_models.py`, `docs/06-storage.md`, `src/submeter/store/history.py`, `tests/test_history.py`
- **Uses:** `Bucket`, the raw schema of P2. **Provides:** the history DDL in docs/06 and in `store/history.py`; `SessionMarker`, `SessionSummary`, `RunRow`, `Epoch`, the history finding row and structured `Finding` evidence
- **Work:** Writes the DDL of `meta` (schema version, rolled-up-until mark), `workload`, `epoch`, `rollup_1h` (one `Bucket` per row, keyed by hour, workload and epoch, so that an hour that holds an epoch boundary keeps one row per epoch, Q17's default), `exe_1h`, `run`, `session`, `session_summary` and `finding` into docs/06 "Table columns", with a nullable column for every catalogue metric version 1 collects and no `baseline` table (I67). The `run` table keeps each run's parent run id, which `submeter cost` needs to subtract child runs from history rows (P3-W5-T1); the system series keeps the count of processes whose start time could not be read (I42); `rollup_1h` keeps each workload's GPU load by engine type. `Finding` evidence becomes named fields (workload, executable, metric), never a command line (R103), so that the findings P3 writes (P3-W4-T4) and P4's detectors (P4-W1-T4, P4-W2-T1) use it from the start. Decides how system gauges are stored (R112's evidence: no record exists for them), load per core class hourly among them (`docs/06-storage.md:117`) as Q11 decides, from the efficiency classes in each raw file's `meta` table (P2-W3-T1), where a run's and a session's per-executable figures live (R122), and the open-row columns (the last tick included, the incomplete mark, I62). `store/history.py` holds the DDL as code and creates `history.db` 0600 in WAL mode with `synchronous=NORMAL`. No history table is keyed by pid and no `finding` evidence holds one, because process rows live only in raw files and nothing keyed by pid is kept beyond 48 hours (`docs/17-build-prompt.md:150`); a run's holder pid stays in its run file.
- **Tests first:** The DDL in docs/06 and in `history.py` match (the test parses the Markdown code block and compares it with `sqlite_master` after create); create gives 0600 and WAL; every catalogue column is present and nullable; the `run` table has a parent column; `rollup_1h`'s key includes the epoch; no table of the DDL has a pid column in its primary key or in any unique index, and `Finding` evidence has no pid field (docs/17:150); a `Finding` with a free-text evidence field is refused.
- **Gate evidence:** none directly
- **Depends on:** gate P2 · **Size:** L · **OS:** either

**P3-W1-T2 · The synthetic raw-file generator**

- **Advances:** tools beside the code: synthetic store generator (docs/13:51), raw part; R117, R53, I81
- **Owns:** `tests/tools/synthetic/__init__.py`, `tests/tools/synthetic/raw.py`, `tests/test_synthetic_raw.py`
- **Uses:** `RawFile`. **Provides:** the 3-hour raw fixture; the 5-minute raw file; multi-day raw stores
- **Work:** Writes raw day files without a collector, from a seed, with the process count, duration, cadence and start time as arguments (section 7.3.2): the 3-hour fixture from 22:30 to 01:30 UTC, crossing a day file, once with ticks every 2 s on whole seconds and once at 2 s with a 0.3 s phase and ±0.05 s jitter, each with one long gap sample (600 s, ending at 23:05:00 or 23:05:00.3, so that it lies across an hour boundary and a wrong bucket rule moves far more than P3.1's 0.1%) and a manifest of the CPU generated per workload per hour by sample end, computed without SQLite; the 5-minute raw file of 150 ticks at 2 s with 300 processes and every catalogue column of `system_raw` filled, for P4-W3-T1, P4-W4-T1 and P4-O1; raw stores over several days for the retention and disk-budget tests.
- **Tests first:** Row counts and the split across two day files; the gap sample present and across 23:00; the same seed gives the same canonical row dump (each table's rows in key order), not the same bytes, because SQLite writes its library version into the file header (section 7.3.2); the manifest's hourly CPU equals the raw sum by end time; the 5-minute file has 150 ticks and 300 processes.
- **Gate evidence:** P3.1 and P4.5 data
- **Depends on:** gate P2 · **Size:** M · **OS:** either

**P3-W1-T3 · Live group reading**

- **Advances:** components 14; R49, R61, R67, R115, I32
- **Owns:** `src/submeter/providers/windows/job.py`, `tests/test_job.py`
- **Uses:** `GroupProvider.read(live_runs)` (P2-W1-T1): the live runs the collector reads with `store.runs` and passes in each tick (P3-W2-T4). This module reads no run file, because `providers` is layer 1 and `store` layer 2 (`tests/test_layers.py:15-16`). **Provides:** `WindowsGroupProvider`: per tick, each live group's `GroupTotals` deltas, member keys and parent run
- **Work:** Opens each live group named by a live run it is given, reads its totals each tick as deltas and its member list mapped to `ProcessKey`s, subtracts child runs that name a group as parent (net totals, I32), and re-attaches to every live group after a restart. The deltas, the child-run subtraction and the mapping of members to keys are one function of the job readings (`GroupTotals` and member pid lists, as P1-W1-T4's `totals` and `members` return them), so that it is tested on both runners without a job (docs/17:49); no owner recording of this provider is planned (Q18).
- **Tests first:** On both systems: a sequence of job readings written in the test, in the shape `totals` and `members` return, gives the expected deltas, a child run's totals subtracted from its parent's, and each member mapped to its `ProcessKey`, a pid whose start stamp changed giving a new key. On CI-W: deltas over two ticks equal the job's change; members mapped to keys; a child run's totals subtracted from its parent; a provider started after the job exists attaches to it; the live runs reach it only as the argument of `read`.
- **Gate evidence:** P3.3 input
- **Depends on:** gate P2 · **Size:** M · **OS:** Windows (CI-W) for the live reads; the logic on both runners

**P3-W1-T4 · Quarantine, backup names and the file listing**

- **Advances:** components 08, 09; R91, R100, R129
- **Owns:** `src/submeter/store/files.py`, `src/submeter/store/raw.py`, `tests/test_files.py`, `tests/test_raw.py`
- **Uses:** `FileMap`. **Provides:** `quarantine()`, backup names and pruning, `list_files()`
- **Work:** A damaged raw file is moved with its `-wal` and `-shm` to a quarantine folder and a gap recorded (docs/17:179); backups are named `backups/history-<UTC time>.db`, created 0600, listed and pruned to `backups.keep`; a per-file listing for `store status`: writer, size, coverage, `-wal` size and the warning above 4 MiB (4,194,304 bytes, R129).
- **Tests first:** A corrupt raw file is quarantined with its side files; three newest backups kept; a 5 MiB `-wal` flagged.
- **Gate evidence:** none directly (`docs/17-build-prompt.md:179`, `docs/06-storage.md:40`)
- **Depends on:** gate P2 · **Size:** M · **OS:** either


#### Wave P3-W2 (4 builders)

**P3-W2-T1 · History writers and readers**

- **Advances:** components 26; R122, R88
- **Owns:** `src/submeter/store/history.py`, `tests/test_history.py`
- **Uses:** the P3 records and DDL. **Provides:** writers used by the server only; readers for the CLI and the report
- **Work:** Writers: buckets, executable rows, runs, open and closed session summaries, epochs, findings, workload names and the rolled-up-until mark. Readers: runs with their parent run, sessions, findings newest first, buckets for a window, and the epochs in a window with their reasons, which the report marks on its charts (P5-W3-T1). An integrity-check function.
- **Tests first:** Write then read each row kind; findings come back newest first; the mark moves only forward.
- **Gate evidence:** P3.1, P3.4 inputs
- **Depends on:** P3-W1-T1 · **Size:** L · **OS:** either

**P3-W2-T2 · Hourly buckets for history**

- **Advances:** components 10; R53, R112, I39, I60
- **Owns:** `src/submeter/store/rollup.py`, `tests/test_rollup.py`
- **Uses:** the decisions of P3-W1-T1; `SystemInfo` in the raw `meta` table (P2-W3-T1); `system_raw.logical_cores`. **Provides:** catalogue gauges per bucket; `exe_1h` rows; `roll_up` and `SeriesAccumulator` taking the epoch id and logical cores of each sample
- **Work:** Catalogue gauges per bucket and the system series as P3-W1-T1 decided: load per core class (Q11), which groups the per-core raw values by the efficiency classes in each raw file's `meta` table; the count of processes whose start time could not be read, its maximum and mean per hour (I42); each workload's GPU load by engine type, maximum and mean; `exe_1h`: the top 10 executables per workload by CPU time and by peak memory each hour, keyed by executable name, never pid; docstring: hourly buckets are built from raw samples and `merge` gives wider steps (I39); `active_share` stays 0.005 (I60). `roll_up` and `SeriesAccumulator` take the epoch id and the logical cores of each sample instead of one value for the whole call (`src/submeter/store/rollup.py:36`, `:112`, both `epoch: int = 0` and one `logical_cores`), so that capacity is the sum of awake seconds times each sample's logical cores (docs/06:132, docs/17:159), and an accumulator never mixes two epochs: a sample of another epoch in the same hour opens a second bucket for that hour (Q17's default).
- **Tests first:** `exe_1h` from synthetic process rows; samples of two epochs in one hour give two buckets, each carrying its own epoch id; the capacity of a bucket whose samples have 4 and then 8 logical cores equals the sum of each sample's awake seconds times its cores (fails today: `roll_up` takes one epoch and one core count); gauge minimum, maximum and mean over a fixture; per-core load grouped by the two efficiency classes a raw file's `meta` names; the unreadable count's maximum and mean over a fixture.
- **Gate evidence:** P3.1 input
- **Depends on:** P3-W1-T1 · **Size:** M · **OS:** either

**P3-W2-T3 · Session markers, the backup request and `submeter session`**

- **Advances:** components 12, 08; R115, R120, R150, I85
- **Owns:** `src/submeter/store/control.py`, `src/submeter/cli/session.py`, `tests/test_control.py`, `tests/test_cli_session.py`
- **Uses:** `SessionMarker`, `write_atomic`; `FileMap.sessions_dir` and `FileMap.backup_request` (P2-W4-T1), so that this task builds no path by hand. **Provides:** `control/sessions/<id>.json`; `control/backup`; `session start | stop | list`
- **Work:** Session markers written by atomic rename; the backup request file; `session start [--label]`, `session stop [ID]` and `session list` (markers plus history sessions). Sessions may overlap. `--json` prints each subcommand's envelope, with the subcommand schema names P1-W1-T1 wrote into docs/03 (docs/03:86).
- **Tests first:** Start writes a live marker, stop adds the stop time, list shows both; two overlapping sessions are allowed; a snapshot test of each of `session start`, `stop` and `list` with `--json`, kept in `tests/test_cli_session.py`, asserts the `schema` key and the field set (S4).
- **Gate evidence:** P3.4 input
- **Depends on:** P3-W1-T1 · **Size:** M · **OS:** either

**P3-W2-T4 · The collector reads live groups**

- **Advances:** components 07, 14, 15; R49, R61, R67, I32, I45; `docs/17-build-prompt.md:80` (a process belongs to its innermost group)
- **Owns:** `src/submeter/programs/collector/loop.py`, `src/submeter/attribution/rules.py`, `tests/test_collector_program.py`, `tests/test_attribution.py`
- **Uses:** the group provider of P3-W1-T3; `store.runs` (P1-W1-T2), for the live runs it passes the provider; `quarantine()` (P3-W1-T4); the total-unit memory on `ProcessSample` (P0-W3-T1, copied by P0-W4-T1's sampler), which it sums over a group's members. **Provides:** kernel totals for tagged workloads each tick
- **Work:** At start, a day file the collector cannot open is moved aside with `quarantine()`, a gap is recorded and a new file is started (`docs/17-build-prompt.md:179`, R91). Each tick the loop reads the live run files with `store.runs` and passes the live runs to the group provider (`GroupProvider.read`, P2-W1-T1), which returns each live group's totals, members and parent run; it passes them to `aggregate` as `kernel_workloads` (net of child runs) and puts group members before the rules (kernel group first, docs/17:122). A process in the member lists of several live groups belongs to the innermost, the run deepest in the chain of parent runs (docs/17:80), so that its CPU, I/O and memory count in one workload; and takes a tagged group's current memory as the USS sum over members with a reading, partial with the count (R67).
- **Tests first:** With a fake group provider: a tagged workload reports the group's CPU, not its polled sum; a member never reaches the rules; memory is partial with the count; with a fake group provider in which one pid is in both an outer and an inner group's member list, that process lands only in the inner workload and its memory is counted once; a damaged day file at start is quarantined with its side files and a new one opened.
- **Gate evidence:** P3.3
- **Depends on:** P3-W1-T3, P3-W1-T4 · **Size:** M · **OS:** either (fake provider); end to end on CI-W in the P3 gate


#### Wave P3-W3 (4 builders)

**P3-W3-T1 · The server program**

- **Advances:** components 26; R53, R88, R91, R98, R120
- **Owns:** `src/submeter/programs/server/__init__.py`, `src/submeter/programs/server/__main__.py`, `src/submeter/programs/server/loop.py`, `src/submeter/programs/server/rollups.py`, `src/submeter/programs/server/retention.py`, `src/submeter/programs/server/backups.py`, `src/submeter/programs/server/ingest.py`, `src/submeter/programs/server/epochs.py`, `pyproject.toml`, `uv.lock`, `tests/test_server.py`, `tests/test_one_writer.py`
- **Uses:** `store.history`, `store.rollup`, `store.raw` readers, `store.control`, `store.logs`, `quarantine()` (P3-W1-T4). **Provides:** `submeter-server = "submeter.programs.server:main"`; the hourly tier
- **Work:** Instance lock, pid file, logs, the stop file polled each tick. The history file's integrity check at start; on failure it does what B19 decides. The hourly rollup: at start every raw day held is rolled up, oldest first, before any retention pass; the rolled-up-until mark is kept; a bucket is final 30 s after its hour; rollups are idempotent. Each sample is rolled up with the epoch id in force at its end time, read from the history `epoch` table, and with its own tick's logical cores from `system_raw` (P3-W2-T2), so that every `rollup_1h` row carries its true epoch id (docs/06:67, docs/17:159) and a bucket across a change of core count keeps the right capacity (docs/06:132). The rollup pass moves a raw file that fails to open or fails `PRAGMA quick_check` aside with `quarantine()` and records a gap event (R91, `docs/17-build-prompt.md:179`). The loop calls its passes in this order: epochs, rollup, retention, backups, ingest. Epochs come first so that the epochs of every sample the rollup reads are already in the `epoch` table; the epochs pass reads event rows only up to the last tick the rollup will then read, and a bucket that is not yet final is rolled up again on the next tick, after any new epoch. Retention follows the rollup (R88). This task writes epochs, retention, backups and ingest as modules with their signatures and bodies that do nothing, which P3-W4 fills; until P3-W4-T4 fills the epochs pass, every bucket carries epoch 0. The loop logs each pass's CPU time (`time.process_time()` before and after) and wall time in one structured log record, so that a soak can tell which pass used a window's budget (K4). `tests/test_one_writer.py` checks the imports under `src`: only `programs.collector` imports the raw writer and only `programs.server` imports the history writers, so that each file keeps one writer (`docs/06-storage.md:9`, `AGENTS.md:46`).
- **Tests first:** The 3-hour synthetic raw store rolled up once and again gives identical rows; with an epoch row the test writes into the `epoch` table at 23:30, samples ending before and after it land in buckets with different epoch ids; the loop runs the epochs pass before the rollup pass; a stop file stops the server within one tick; a corrupt history file is handled as B19 says; a damaged raw file is quarantined by the rollup pass with a gap recorded; a pass's log record carries its CPU seconds; the import check fails on a planted import of the history writers in `cli`.
- **Gate evidence:** P3.1, P3.5
- **Depends on:** P3-W2-T1, P3-W2-T2, P3-W1-T2, P3-W1-T4, P2-W4-T1; decision B19 · **Size:** L · **OS:** either

**P3-W3-T2 · Query readers**

- **Advances:** components 11; R53, R139, R94, I5
- **Owns:** `src/submeter/store/query.py`, `tests/test_query.py`
- **Uses:** raw and history readers. **Provides:** window readers that name their tier and resolution
- **Work:** Raw rows merged at query time into wider steps with the end rule (`roll_up` with the step as the width, I5); window readers across day files and the history file, with the tier and resolution named in every result; `choose_tier`'s caller takes raw coverage from the oldest raw file's first tick (R139); results that cross an epoch or a change of sampling interval are marked. Hourly window readers mark each bucket whose covered seconds are less than half its width, by `well_covered()` (`src/submeter/store/rollup.py:183`), and leave it out of the trend series they return, because such buckets are left out of trends (docs/06:133, docs/17:171); the report's history charts (P5-W2-T1) and the period diffs (P4-W2-T4) honour the mark.
- **Tests first:** A 600 s sample lands whole in the step holding its end; a 24 to 48 h window whose day file is gone is answered from hourly; a window across an epoch is marked; a bucket with `covered_s` below half its width is marked and absent from the trend series.
- **Gate evidence:** none directly (`docs/06-storage.md:99`, `:133`, `docs/17-build-prompt.md:171`)
- **Depends on:** P3-W2-T1, P3-W2-T2 · **Size:** M · **OS:** either

**P3-W3-T3 · Synthetic history and multi-day stores**

- **Advances:** tools beside the code: synthetic store generator, history part; I81
- **Owns:** `tests/tools/synthetic/history.py`, `tests/test_synthetic_history.py`
- **Uses:** `store.history` writers. **Provides:** history files and raw files over a number of days given as an argument, with runs, sessions and findings
- **Work:** Writes stores from a seed, without a running collector or server (section 7.3.2): the 7-day store (hourly history for 7 days, raw files for the last 2, runs of which one is nested, sessions of which two overlap, one was never stopped and one is longer than raw retention, and findings), with a variant whose raw files exceed `disk_budget`; and the 30-day store (hourly history beyond the 2 raw days, one rules change, one change of sampling interval and the daylight-saving change of 25 October 2026 under the Europe/London rule) for the diff across weeks (P4-W2-T4, P4-W3-T2), the export (P5-W2-T3) and the report over a range that spans raw and hourly data (P5-W3-T1, P5.1).
- **Tests first:** A 7-day store has the stated rows per table; a 30-day store holds the epoch, the interval change and the daylight-saving change; both reproduce from their seed as canonical row dumps.
- **Gate evidence:** P3.2 and P5.1 data
- **Depends on:** P3-W2-T1, P3-W1-T2 · **Size:** M · **OS:** either

**P3-W3-T4 · `submeter rules test`**

- **Advances:** components 15, 16, 12; R99, I53
- **Owns:** `src/submeter/cli/rules.py`, `src/submeter/privacy/redact.py`, `src/submeter/attribution/rules.py`, `tests/test_cli_rules.py`, `tests/test_privacy.py`, `tests/test_attribution.py`
- **Uses:** `RuleSet`, `redact_cmdline`. **Provides:** `rules test` with the rule, its matching conditions and the hidden arguments
- **Work:** For a live process of the user's own (I53): which rule claims it and why, and which arguments the store would hide, from a marking function in `redact.py`. `--json` prints the envelope with the subcommand schema name P1-W1-T1 wrote into docs/03 (docs/03:86).
- **Tests first:** A fake process matched by the second of two rules names that rule and its condition; a `--password` argument is marked hidden in scrub mode, and the whole command line in exe_only mode; a snapshot test of `rules test --json`, kept in `tests/test_cli_rules.py`, asserts the `schema` key and the field set (S4).
- **Gate evidence:** none directly
- **Depends on:** P3-W2-T4 · **Size:** M · **OS:** either


#### Wave P3-W4 (4 builders)

**P3-W4-T1 · Retention and the disk budget**

- **Advances:** components 26; R88, R92, R130, I61
- **Owns:** `src/submeter/programs/server/retention.py`, `tests/test_server_retention.py`
- **Uses:** `FileMap.expired_raw`, `disk_use`; the rollup pass (P3-W3-T1) and the query readers (P3-W3-T2), for the release test. **Provides:** the retention pass
- **Work:** Deletes raw days past `retention.raw` once the mark has passed them, each `.db` with its `-wal` and `-shm`; a refused delete (Windows, a reader open) is retried next pass and space counts as freed only when the files are gone. Over `disk_budget`: the oldest raw file first, never below 24 h, then backups down to one, then a finding; history is never deleted.
- **Tests first:** With a read-only reader open on CI-W the delete is refused and succeeds after the reader closes, and `disk_use` falls by exactly the three files' size; on CI-W, in one process, the server's rollup pass and a query reader read a closed raw day past `retention.raw`, and the server's own retention pass then deletes its `.db`, `-wal` and `-shm` on its first try, which shows that Submeter's own readers open a closed file only for the length of a query (docs/17:149, docs/06:23); a synthetic 7-day store over budget is trimmed in the stated order.
- **Gate evidence:** P3.2
- **Depends on:** P3-W3-T1, P3-W3-T2, P3-W3-T3 · **Size:** M · **OS:** either; the refused delete on CI-W

**P3-W4-T2 · Backups**

- **Advances:** components 26; R100, I85; `docs/06-storage.md:15` (a compacted copy)
- **Owns:** `src/submeter/programs/server/backups.py`, `tests/test_server_backups.py`
- **Uses:** SQLite's `VACUUM INTO`; `control/backup`. **Provides:** the backup pass
- **Work:** A daily backup written with `VACUUM INTO` into an empty file the pass first creates 0600 (SQLite accepts an empty existing file as the target), so that the copy is the compacted copy `docs/06-storage.md:15` describes and is taken while the server runs and readers hold the file, which is what `docs/17-build-prompt.md:180`'s "online backup" asks; SQLite's backup API copies pages as they are and does not compact (11.7). Keeps `backups.keep` files; migrations only after a backup; a `control/backup` request answered and removed.
- **Tests first:** A request file gives a backup and is removed; a fourth backup prunes the oldest; mode 0600 on POSIX; a backup of a history file from which half the rows were deleted is smaller than the file and passes `PRAGMA integrity_check`, taken while another connection holds a read transaction.
- **Gate evidence:** none directly
- **Depends on:** P3-W3-T1, P3-W1-T4, P3-W2-T3 · **Size:** M · **OS:** either

**P3-W4-T3 · Runs and sessions into history**

- **Advances:** components 26; R113, R115, R122, R141, I62, I65, I83
- **Owns:** `src/submeter/programs/server/ingest.py`, `tests/test_server_ingest.py`
- **Uses:** final run files, session markers, raw readers. **Provides:** the ingest pass
- **Work:** Copies each final run file into the `run` table, then deletes it. While a run or session is live, updates an open summary row on each raw tick and records its last tick; catches up after a restart; closes at stop, the per-executable part 60 s later (I65); a session never stopped closes at its last covered sample; a summary whose raw data went first is marked incomplete (I62).
- **Tests first:** With an injected clock, a 30-minute session's cost has every numeric field equal before and after the test deletes the session's raw day files itself, as a retention pass would (the retention pass of P3-W4-T1 is in the same wave; gate P3.4 runs the two together in P3-W6-T1); a run file is deleted only after its row is committed; a summary whose raw data went first is marked incomplete (I62); the per-executable part closes 60 s after the end (I65); a session never stopped closes at its last covered sample (R115); two runs of one workload with different labels give two `run` rows and, after the rollup pass, one workload series (`docs/06-storage.md:135`).
- **Gate evidence:** P3.4
- **Depends on:** P3-W3-T1, P3-W2-T3, P3-W2-T1 · **Size:** L · **OS:** either

**P3-W4-T4 · Epochs, findings from collector events, workload names**

- **Advances:** components 26; R94, R88, I41, I63
- **Owns:** `src/submeter/programs/server/epochs.py`, `tests/test_server_epochs.py`
- **Uses:** event rows, the start, hardware-change and raw-day-deleted-under-the-cap events among them (P2-W1-T1, P2-W5-T1); the rollup pass (P3-W3-T1), which reads the `epoch` table this pass writes. **Provides:** the epochs pass
- **Work:** Epochs from provider-status, clock-step and hardware-change events, and at each restart from the difference between two consecutive start events: the digest of the sampling settings, the digest of the rules file, `SystemInfo` or the version, each with its reason; never from cadence or from alert, UI or verdict settings. Findings from guard events and from raw days the collector deleted under its cap. The `workload` table that `doctor` reads for its 200-name warning.
- **Tests first:** A fixture of events gives the expected epochs with reasons; a cadence change starts none; a rules change between two hours starts an epoch and leaves the first hour's rows unchanged (docs/17:169); a guard event gives a finding; two start events with different rules digests start one epoch with the reason "rules file", and two with equal digests start none; a start event with another version or another logical core count, and a hardware-change event, each start one; with the rollup pass run after this pass, as the loop orders them, two consecutive start events with different rules digests give the hourly buckets before and after the second start different epoch ids; a raw file holding one "raw day deleted under the cap" event gives exactly one finding, and a second pass over the same file gives none (docs/06:21, docs/17:181).
- **Gate evidence:** none directly (`docs/17-build-prompt.md:169`, `docs/06-storage.md:129-132`)
- **Depends on:** P3-W3-T1, P3-W2-T1 · **Size:** M · **OS:** either


#### Wave P3-W5 (4 builders)

**P3-W5-T1 · `submeter cost` over history, sessions and workloads**

- **Advances:** components 12; R49, R143, I31; L01, L02, L03, L04, L10, L12; `docs/04-features.md:17`
- **Owns:** `src/submeter/cli/cost.py`, `tests/test_cli_cost.py`, `docs/03-cli-output.md`
- **Uses:** history readers (runs with their parent run), query readers. **Provides:** `submeter.cost/1` for workloads, sessions and runs
- **Work:** The table of docs/03:9-23 for workloads, `--session`, and runs from the history `run` table plus run files not yet copied (I31), in the shape P1-W1-T1 fixed; L01's note beside `agent:*` totals; L02's note beside polled workloads, the note the docs/03:22 sample prints; L03's note beside each tagged run's totals (`docs/10-known-limits.md:11`); L04's note beside figures read on Linux; L10's beside Restricted and System; L12's beside memory totals. No command line and no working folder in any output, whatever the redaction mode (docs/08:127). A parent run's totals are its own less the totals of the child runs that name it, whether each is a history row or a run file not yet copied (docs/17:80, R49): P1-W2-T3 does this for run files only, and a `run` row keeps the gross totals the job gave when the run ended (docs/17:165), so without this a parent counts its nested children's CPU twice once both files are copied and deleted. The four fixed workloads, System, Restricted, Unattributed and Submeter, appear in every workload table, with no members if none, and the CPU time not seen by polling beside them (docs/04:17, docs/17:127). The `cost` sample at docs/03:9-23 shows neither the `submeter` row nor that figure; under Q16's default this task adds both to that sample.
- **Tests first:** Snapshot tests for each form, kept in `tests/test_cli_cost.py`, asserting the `schema` key and the field set (S4); a run present both as a file and as a row is counted once; the L03 note beside a tagged run; the L01 note beside an `agent:*` workload, the L02 note beside a polled workload, the L04 note on a Linux-shaped store, the L10 note beside Restricted and System and the L12 note beside memory totals; on a synthetic store written in `scrub` mode whose stored arguments hold a plain canary (section 7.3.1, Canaries), `cost --json` for workloads, for `--session` and for `--run` contains no canary, as UTF-8 or UTF-16-LE bytes, while the raw file's `command` table holds it; a parent row of 10 CPU-s with a child row of 4 CPU-s, both run files deleted, reports 6, and so does a parent row whose child is still a run file; the four fixed rows appear with no members, with the not-seen figure beside them.
- **Gate evidence:** section 1, row D10
- **Depends on:** P3-W2-T1, P3-W3-T2 · **Size:** M · **OS:** either

**P3-W5-T2 · `submeter store status | check | backup`**

- **Advances:** components 12; R129, I85
- **Owns:** `src/submeter/cli/store.py`, `tests/test_cli_store.py`
- **Uses:** `list_files()`, the history integrity check, `control/backup`. **Provides:** the full `store status`
- **Work:** Every file with its writer, size, coverage, `-wal` size and the warning, integrity and epoch (docs/03:68-82); `check` runs `PRAGMA integrity_check` on every file read-only; `backup` writes the request file at `FileMap.backup_request`. `--json` prints each subcommand's envelope, with the subcommand schema names P1-W1-T1 wrote into docs/03 (docs/03:86).
- **Tests first:** A 5 MiB `-wal` warned; `check` on a corrupt file exits non-zero and names it; `backup` writes `control/backup`; a snapshot test of each of `store status`, `check` and `backup` with `--json`, kept in `tests/test_cli_store.py`, asserts the `schema` key and the field set (S4).
- **Gate evidence:** none directly
- **Depends on:** P3-W1-T4, P3-W2-T3, P3-W2-T1 · **Size:** M · **OS:** either

**P3-W5-T3 · `submeter daemon` and `config reload`**

- **Advances:** components 12; the Windows scheduled task (docs/13:52); R50, R105, R149, I36
- **Owns:** `src/submeter/cli/daemon.py`, `src/submeter/cli/config.py`, `tests/test_cli_daemon.py`
- **Uses:** `store.control`, `InstanceLock.holder()`. **Provides:** `daemon install | uninstall | start | stop | status`; `config reload`
- **Work:** `install`: one per-user logon task per program (plan choice C2) with the settings of docs/17:260, running the console scripts of the virtual environment it is run from (`.venv\Scripts\` on Windows), unless the owner's answer to Q12 names another install, or the HKCU Run key if B3 says so; the task names and settings are defined in one place in `cli/daemon.py`, which `doctor` reads back (P3-W6-T3); `uninstall`; `start` runs the tasks on Windows and, on Linux, starts both entry points detached (B17); `stop` writes the stop files or asks the service manager, never signals a process, and confirms with `InstanceLock.holder()` (R105); `status` shows lock holders and pid files; `config reload` stops through the stop files and starts as `daemon start` does (I36). `--json` prints each subcommand's envelope, with the subcommand schema names P1-W1-T1 wrote into docs/03 (docs/03:86).
- **Tests first:** The generated task XML has each docs/17:260 setting; a snapshot test of each of `daemon install`, `uninstall`, `start`, `stop` and `status` and of `config reload` with `--json`, kept in `tests/test_cli_daemon.py`, asserts the `schema` key and the field set (S4), the calls that register or run tasks replaced by fakes; `daemon stop` with a stale pid file signals nothing; stop then status shows no holder; `config reload` stops both programs through their stop files, starts them as `daemon start` does, and a changed setting applies (I36): on Linux with B17's real start; on CI-W with the call that runs the scheduled tasks replaced by a fake that starts the two entry points, because the runner has no logon session (section 7.6). The same case with the real scheduled tasks on Windows is marked `session` and runs on the owner's machine in step 4 of P3-O1.
- **Gate evidence:** P0.10's decision applied
- **Depends on:** P3-W3-T1, P2-W5-T1, P2-W4-T1; decision B3, B17; plan choice C2 · **Size:** L · **OS:** either; `install` and `start` on the owner's machine in P3-O1

**P3-W5-T4 · `doctor` for phase 3**

- **Advances:** components 12; R128, R129, R100
- **Owns:** `src/submeter/cli/doctor.py`, `tests/test_cli_doctor.py`
- **Uses:** history readers, `list_files()`. **Provides:** the rest of the capability matrix before P5, except the scheduled task's read-back (P3-W6-T3)
- **Work:** The VM's share of busy CPU time and of capacity (R128); disk use and `-wal` warnings (R129); others-readable paths, reported unavailable on Windows (R100); more than 200 workload names.
- **Tests first:** Each row from fixtures; the share computed from a fixture with a vmmem workload.
- **Gate evidence:** L05
- **Depends on:** P3-W1-T4, P3-W2-T1 · **Size:** M · **OS:** either


#### Wave P3-W6 (3 builders)

**P3-W6-T1 · The P3 gate harness**

- **Advances:** gate P3; R53, R117, R130, R122
- **Owns:** `tests/test_gate_p3.py`
- **Uses:** the synthetic generators, the server, the collector, the launcher. **Provides:** evidence for P3.1 to P3.4, under the harness contract of section 6.2
- **Work:** P3.1: CPU per hour from `rollup_1h` against Σ raw `cpu_s` by end time computed with plain SQL, not through `store.query` or `store.rollup`, within 0.1%, for whole and fractional ticks, and that raw sum against the generator's manifest within floating-point rounding (section 7.3.2). P3.2: delete with a reader open (Windows) and without. P3.3: a 120 s tagged burner; stop the collector by its stop file and, in a second trial, kill it; restart within 10 s; within one tick its rows carry source kernel, and the per-tick CPU summed over the run equals the final run file's within 2%. P3.4 through the CLI.
- **Tests first:** It is the acceptance test; CI-W and CI-L cases pass before merge.
- **Gate evidence:** P3.1, P3.2, P3.3, P3.4
- **Depends on:** P3-W4-T1, P3-W4-T3, P3-W5-T1, P3-W2-T4 · **Size:** M · **OS:** either; P3.3 on CI-W and in P3-O1

**P3-W6-T2 · The CI soak with the server**

- **Advances:** gate P3; R87, R117
- **Owns:** `.github/workflows/soak.yml`, `tests/tools/soak_schedule.py`, `tests/test_soak_workflow.py`
- **Uses:** the soak workflow of P2. **Provides:** the 30-minute soak with the server
- **Work:** The server joins the soak, which starts at minute 40 of an hour so it crosses an hour boundary, issues `submeter store backup` once and lets one retention pass run; the budget is judged over every Submeter process. The `soak` job keeps its limit of 120 minutes, which covers the wait for minute 40 (up to 60 minutes), the 30-minute soak and about 10 minutes of set-up and checking; P3's `soak` cases, such as P3.3's two 120 s trials, run in the `soak-tests` job, whose sum section 7.5 gives.
- **Tests first:** `tests/test_soak_workflow.py`: the dry run covers the server start, the backup request and the retention pass; the text check still finds both job limits.
- **Gate evidence:** P3.5
- **Depends on:** P3-W3-T1, P3-W4-T1, P3-W4-T2, P3-W5-T2 · **Size:** S · **OS:** either (both runners)

**P3-W6-T3 · `doctor` reads back the scheduled task**

- **Advances:** components 12; R50
- **Owns:** `src/submeter/cli/doctor.py`, `tests/test_cli_doctor.py`
- **Uses:** the task names and settings defined in `cli/daemon.py` (P3-W5-T3). **Provides:** the scheduled task row of `doctor`
- **Work:** On Windows, reads back each registered task with `schtasks /Query /XML` and compares the 8 settings of docs/17:260 with the definition in `cli/daemon.py`, reporting each difference; if B3 chose the HKCU Run key, it reads that value back and compares the command it starts. On Linux the row reads unavailable with the reason (B17). Placed after P3-W5-T3, which defines the names and settings, and P3-W5-T4, which held `doctor.py` in the wave before.
- **Tests first:** A recorded read-back XML with one setting changed gives one difference and the row partial; the row on Linux is unavailable with its reason.
- **Gate evidence:** none directly (P3.6 reads the tasks itself)
- **Depends on:** P3-W5-T3, P3-W5-T4 · **Size:** S · **OS:** either; the live read-back on the owner's machine


#### Owner tasks (outside the waves; no builder)

**P3-O1 · Owner: `daemon install` and re-attach on the Windows machine** (at the P3 gate commit G3, after P3-W6 integrates)

- **Advances:** gate P3; R50 (the logon task in use), R49 and R61 (re-attach on the owner's machine)
- **Owns:** `docs/gates/P3/owner/`
- **Uses:** `submeter daemon` (P3-W5-T3) from the virtual environment that step 4's `uv sync` makes at G3 (Q12), and `tests/test_gate_p3.py` (P3-W6-T1). **Provides:** `docs/gates/P3/owner/`: `checks/`, `daemon.txt` (each command's output, P3.6) and `harness/P3.3.json`. The gate reviewer reads them
- **Work:** Begins with the owner check run of section 6.2 step 4 at G3, whose `uv sync` makes the virtual environment whose console scripts the scheduled tasks run (Q12). Then `submeter daemon install` as the standard user; sign out and in; both programs started by their tasks; `daemon stop`; gate items P3.3 and P3.6 on this machine (section 6.7).
- **Gate evidence:** S1 on the owner's machine; P3.3, P3.6; P0.10's decision in use
- **Depends on:** every P3 builder task, among them P3-W5-T3 and P3-W6-T1 (it runs at G3) · **Time:** about 20 minutes · **OS:** the owner's personal Windows 11 PC, as the signed-in standard user, for the evidence; on the work PC only the owner check run of section 6.2 step 4, reported by word (section 3.1, Owner tasks)


### 3.8 P4: analysis

`docs/15-phases-and-decisions.md:59-63`: the verdict and `submeter why`, the leak check, the runaway process count, the session diff, and the alert rules whose findings `submeter findings` lists. The fixtures, those of the alert rules included, are written in the first wave by a builder who builds no detector, before any threshold is set, so that the gate can fail. The series the server feeds to the detectors and the alert rules are read from the raw store by one task in the same wave (P4-W1-T3).

#### Wave P4-W1 (4 builders)

**P4-W1-T1 · The P4 records**

- **Advances:** components 01, 18, 19; R84, I87
- **Owns:** `src/submeter/core/models.py`, `tests/builders.py`, `tests/test_models.py`
- **Uses:** docs/03:27-45, docs/07; the structured `Finding` of P3-W1-T1. **Provides:** `VerdictResult`, `DiffResult`
- **Work:** `VerdictResult`: verdict, confidence, evidence lines, contributors with their accounting source, the six terms and the window; `DiffResult`: the change per workload and flags for a comparison that crosses an epoch or a change of interval. `Finding` already has its structured evidence (P3-W1-T1), so the runaway count in this wave (P4-W1-T4) needs nothing from this task.
- **Tests first:** `VerdictResult` requires a confidence; a `DiffResult` across an epoch carries its flag.
- **Gate evidence:** none directly (`docs/17-build-prompt.md:196`)
- **Depends on:** gate P3 · **Size:** S · **OS:** either

**P4-W1-T2 · Detector and verdict fixtures**

- **Advances:** components 17, 18, 22; R52, R80, R84, I50
- **Owns:** `tests/tools/series.py`, `tests/fixtures/detectors/`, `tests/fixtures/verdict/`, `tests/fixtures/alerts/`, `tests/test_fixture_series.py`
- **Uses:** the counter sets recorded in P2-O1; the alert rules of `docs/08-configuration.md:146-152` and `examples/submeter.toml`. **Provides:** seeded leak, warm-up and staircase series; one fixture per verdict case; a trigger and a quiet series for each built-in alert rule and for one user rule on each per-workload metric
- **Work:** Seeded generators for the leak (75 MiB an hour, 78,643,200 bytes an hour), the browser warm-up of docs/07:24 (3.6 GB + 0.9 × (1 − e^(−t ÷ 0.35 h)) GB) and the 256 MB every 2 hours staircase, with noise as B14 fixes (proposed: rows every 30 s, uniform ±40 MiB per row, 200 seeds). Verdict fixtures from the recorded counter sets and synthetic system rows for each rule of docs/07:114-122 (the memory-bound case synthetic if P2-O1 recorded no memory-bound load, Q14), including two rules matching, a rule matching while its ruled-out condition holds, under 60 s of data and low confidence; GPU-bound from synthetic GPU rows. Alert series, in the series shape P4-W1-T3 provides (time and value or None, per workload and metric id), under `tests/fixtures/alerts/`: for each built-in rule (`commit_fraction` above 0.90 for 2 minutes on `machine`; `throttled` above 0 for 5 minutes on `machine`; `overhead_fraction` above 0.03 for 5 minutes on `submeter`; `docs/08-configuration.md:148-152`) and for one user rule on each per-workload metric (`cpu_cores`, as the shipped "agents eating the machine", above 12 cores for 5 minutes on `agent:*`; `memory_bytes`; `processes`; `io_bytes_per_s`), a trigger series that stays past the threshold 30 s longer than the rule's duration and then crosses it again inside the cooldown, and a quiet series that stays past it 30 s less than the duration. Written before any threshold is set, by a builder who does not build the detectors, the verdict or the alert rules.
- **Tests first:** Each generator reproduces from its seed; the leak's mean slope over 2 h is within 1% of 75 MiB an hour; each alert trigger series stays past its threshold for its rule's duration plus 30 s and each quiet series for the duration less 30 s.
- **Gate evidence:** P4.1 to P4.4 data
- **Depends on:** gate P3, P2-O1; decision B14 · **Size:** M · **OS:** either

**P4-W1-T3 · Series for the server's analysis: the leak series, the alert metrics and the runaway input**

- **Advances:** components 11, 22 (its input), 17 (the runaway count's input); I38, R51; `docs/08-configuration.md:72`, `:134-142`
- **Owns:** `src/submeter/store/query.py`, `tests/test_query.py`
- **Uses:** raw readers; `system_raw.throttled` and the commit columns (P2-W3-T1); the `submeter` workload. **Provides:** 1-minute time-weighted means per workload, and per process under B20's default, over up to 48 h; for each metric id of `docs/08-configuration.md:134-142`, a series per tick over a window the caller names: `cpu_cores`, `memory_bytes`, `processes` and `io_bytes_per_s` per workload, `commit_fraction` and `throttled` for `machine`, and `overhead_fraction` for `submeter`; processes alive and started per workload per tick, the runaway count's input. Each series is a plain sequence of (time, value or None) keyed by workload and metric id, so that `alerts` and `analysis` read it without a new record
- **Work:** Raw workload rows merged on read into 1-minute steps of time-weighted means, over up to 48 h or the raw data on disk, whichever is shorter; under B20 (a), the same steps for each process from raw process rows, keyed by pid and start stamp, because `docs/07-analysis.md:29` tracks growth "for each workload as well as for each process". The alert metrics, from raw rows: `cpu_cores` is the workload's `cpu_s` over the tick's `interval_s`; `memory_bytes` its total-unit memory (USS on Windows, PSS on Linux; "memory for totals", docs/08:137); `processes` its live processes; `io_bytes_per_s` its bytes read plus written over the interval; `commit_fraction` commit used over commit limit from `system_raw`, None when either is NULL, so always None on Linux in version 1 (R51); `throttled` `system_raw.throttled` as 1 or 0, None when NULL; `overhead_fraction` the `submeter` workload's CPU seconds over the interval, the summed CPU of every Submeter process as a share of one core, which is how `overhead_fraction` reports the total (docs/08:72, :142). A NULL raw figure gives None, never 0 (I15). The runaway input: each workload's `processes` and `started` per tick from `workload_raw`. The server passes every series to the detectors and the alert rules, which do not import `store` (P4-W3-T3).
- **Tests first:** A step's mean is time-weighted across rows of unequal length; the window stops at the oldest raw day on disk; a per-process series follows one process's rows and no other's; on a raw file the test writes with `RawFile`: `overhead_fraction` equals the `submeter` workload's CPU over the interval; `commit_fraction` equals commit used over limit, and is None on a file whose commit columns are NULL, as on Linux; `throttled` is 1 on ticks whose flag is set, 0 where it is clear and None where the column is NULL; `cpu_cores`, `memory_bytes`, `processes` and `io_bytes_per_s` match known rows per workload and are None where the raw figure is NULL; processes alive and started per workload match `workload_raw`.
- **Gate evidence:** P4.2 input; P4.1 input (the alert rules and the runaway count on stored rows, through P4-W3-T3)
- **Depends on:** gate P3; decision B20 · **Size:** L · **OS:** either

**P4-W1-T4 · The runaway process count**

- **Advances:** components 17; `docs/17-build-prompt.md:200`
- **Owns:** `src/submeter/analysis/runaway.py`, `tests/test_runaway.py`
- **Uses:** processes alive and started per workload per tick, in the series shape P4-W1-T3 reads from raw rows and the server passes in (P4-W3-T3); the structured `Finding` of P3-W1-T1. **Provides:** a `Finding` when the definition B12 gives is met
- **Work:** Implements the definition, threshold and window the owner gives (B12); the brief names the detector and defines none of them.
- **Tests first:** A trigger series and a quiet series per B12.
- **Gate evidence:** P4.1
- **Depends on:** gate P3; decision B12 · **Size:** S · **OS:** either


#### Wave P4-W2 (4 builders)

**P4-W2-T1 · The leak check**

- **Advances:** components 17; R52, R80, R103, I38
- **Owns:** `src/submeter/analysis/growth.py`, `src/submeter/analysis/leak.py`, `tests/test_growth.py`, `tests/test_leak.py`
- **Uses:** the leak series; `Settings.analysis.leak`. **Provides:** leak findings per workload and per process
- **Work:** Replaces `plateaued()` (`growth.py:45-53`) with a test that does not compare a short noisy tail with a fraction of the whole-window slope; checks the growth unit per workload and, under B20 (a), per process against `leak.min_duration` and `leak.min_slope`; a `Finding` whose evidence names workloads, executables and metrics; the window is up to 48 h or the raw data on disk.
- **Tests first:** On P4-W1-T2's fixtures at the pass rates B14 fixes (proposed: the 75 MiB/h leak flagged by 2 h 5 min in at least 190 of 200 seeds; the warm-up flagged in 0 of 200 over 6 h; the staircase flagged by 6 h in at least 190 of 200).
- **Gate evidence:** P4.2, P4.3, P4.4
- **Depends on:** P4-W1-T1, P4-W1-T2; decision B14, B20 · **Size:** L · **OS:** either

**P4-W2-T2 · The verdict engine**

- **Advances:** components 18, 02 (threshold values); R84, R51, I50; L08
- **Owns:** `src/submeter/analysis/verdict.py`, `src/submeter/core/config.py`, `docs/07-analysis.md`, `examples/submeter.toml`, `tests/test_verdict.py`, `tests/test_config.py`
- **Uses:** the system series, the reconciliation terms, `Settings.verdict`. **Provides:** `decide(window) -> VerdictResult`
- **Work:** The rule set of docs/07:114-122 (Windows column) with each ruled-out condition; on and off values; the off values and absolute disk thresholds docs/07 leaves to phase 4 chosen against the fixtures and written into docs/07 and as the `Verdict.thresholds` defaults (I50); confidence low, moderate or high, its computation written into docs/07 (the brief does not say how it is computed); below `min_confidence` Inconclusive; on Linux Inconclusive or unavailable, never No bottleneck; GPU-bound reads GPU load and adapter VRAM when present and treats the GPU signal as unavailable otherwise.
- **Tests first:** One fixture per verdict; two matching rules give Inconclusive; under 60 s gives Inconclusive; a value oscillating at a threshold does not flip the verdict; Linux rows never give No bottleneck.
- **Gate evidence:** P4.1
- **Depends on:** P4-W1-T1, P4-W1-T2 · **Size:** L · **OS:** either

**P4-W2-T3 · Alert rules**

- **Advances:** components 22; R51, R152, I57
- **Owns:** `src/submeter/alerts/__init__.py`, `src/submeter/alerts/evaluate.py`, `tests/test_alerts.py`
- **Uses:** the metric series of P4-W1-T3, which the server passes in; `Settings.alerts`; the alert fixtures of P4-W1-T2. **Provides:** `evaluate(rules, series) -> list[Finding]`
- **Work:** Each rule evaluated over its duration with the cooldown; the three built-in rules (memory nearly full: `commit_fraction` above 0.90 for 2 min, serious; thermal throttling: `throttled` above 0 for 5 min, warning; Submeter over budget: `overhead_fraction` above 0.03 for 5 min, warning) added to the user's; an unavailable metric never fires and never reads as 0 (`commit_fraction` on Linux, R51); a firing rule raises a `Finding`; `quiet_hours` and `channels` unused (I57); `attribution.unattributed_alert` only as B15 decides. Imports only `core` (layer 2).
- **Tests first:** For each built-in rule and for the user rule on each per-workload metric, P4-W1-T2's trigger series raises exactly one finding, its second crossing inside the cooldown raises none, and its quiet series raises none; a Linux series with commit None raises nothing.
- **Gate evidence:** P4.1
- **Depends on:** P4-W1-T1, P4-W1-T2; decision B15 · **Size:** M · **OS:** either

**P4-W2-T4 · The session diff**

- **Advances:** components 19; R94, R131
- **Owns:** `src/submeter/analysis/diff.py`, `tests/test_diff.py`
- **Uses:** stored summaries passed in by the CLI. **Provides:** `compare(a, b) -> DiffResult`
- **Work:** Compares two sessions or periods from stored summaries and ranks the change per workload; flags any comparison of maxima or percentiles that crosses a change of sampling interval or an epoch; leaves out of a period's figures every hourly bucket the readers mark as less than half covered (P3-W3-T2, docs/06:133) and says how many it left out; local days and weeks in the user's zone at query time, from the OS offset of each reading (R131).
- **Tests first:** A comparison across an interval change is flagged; a diff across a daylight-saving change takes each reading's own offset; a period holding one bucket under half covered is compared without it, and the count left out is 1.
- **Gate evidence:** section 1, row D10
- **Depends on:** P4-W1-T1 · **Size:** M · **OS:** either


#### Wave P4-W3 (3 builders)

**P4-W3-T1 · `submeter why`**

- **Advances:** components 18, 12; R84, R119, I42; L00, L01, L04, L06, L08
- **Owns:** `src/submeter/cli/why.py`, `tests/test_cli_why.py`
- **Uses:** raw readers, the verdict engine, history findings. **Provides:** `submeter.why/1`
- **Work:** Reads the last `verdict.window` (5 minutes) of raw rows read-only, runs the verdict and prints the verdict, confidence, evidence, top contributors with their accounting source, the six terms with the count of processes whose start time could not be read beside Restricted (I42, docs/17:102; P2-W3-T1's `system_raw` column), recent findings, frequency beside CPU time (L06) and the known-limit notes: L01 beside `agent:*` contributors and L04 on Linux; under 2 s. `--json` prints the envelope `submeter.why/1`.
- **Tests first:** On P3-W1-T2's synthetic raw file of 5 minutes at 300 processes and 2 s, `why --json` prints the six terms and the unreadable count beside Restricted; a snapshot test asserts the `schema` key `submeter.why/1` and the field set (S4); the frequency appears beside CPU time (L06); an `agent:*` contributor carries the L01 note; on a Linux-shaped raw file the L04 note appears; its time is recorded on CI and the test fails only above 4.0 s, because shared runners give noisy times; the 2.0 s criterion is judged on the owner's machine (P4.5, P4-O1).
- **Gate evidence:** P4.5
- **Depends on:** P4-W2-T2, P3-W3-T2 · **Size:** M · **OS:** either

**P4-W3-T2 · `submeter diff` and `submeter findings`**

- **Advances:** components 19, 12; I87, R150
- **Owns:** `src/submeter/cli/diff.py`, `src/submeter/cli/findings.py`, `tests/test_cli_diff.py`, `tests/test_cli_findings.py`
- **Uses:** `analysis.diff`, history readers. **Provides:** `submeter.diff/1`, `submeter.findings/1`
- **Work:** `diff A B` over sessions or periods; `findings`, newest first.
- **Tests first:** Snapshot tests of `diff --json` and `findings --json`, asserting the `schema` key and the field set (S4); findings sorted newest first.
- **Gate evidence:** section 1, row D9
- **Depends on:** P4-W2-T4, P3-W2-T1 · **Size:** M · **OS:** either

**P4-W3-T3 · The server runs analysis and alerts**

- **Advances:** components 26; R119, R146
- **Owns:** `src/submeter/programs/server/analysis.py`, `src/submeter/programs/server/loop.py`, `tests/test_server_analysis.py`
- **Uses:** the leak series, the metric series and the runaway input (P4-W1-T3), the leak check, the runaway count, the alert rules. **Provides:** findings written to history
- **Work:** A pass that reads P4-W1-T3's series over each detector's and each rule's window, feeds the leak series to the leak check, the runaway input to the runaway count and the metric series to the alert rules (the three built-in rules and the user's), and writes their findings; `why` stays a CLI computation (R119). The pass logs its CPU time with the pass, as P3-W3-T1's loop does for the others (K4).
- **Tests first:** A synthetic store with a leaking workload gets one leak finding after the pass; a second pass adds none; a synthetic store whose rows hold commit above 0.90 of the limit for 2 minutes and 30 s, the throttled flag for 5 minutes and 30 s, and the `submeter` workload above 3% of one core for 5 minutes and 30 s gets exactly one finding from each built-in rule, and the same store with each figure under its threshold gets none; a store that meets B12's definition gets one runaway finding; on CI-W, after a pass whose leak series read a closed raw day past `retention.raw`, the server's retention pass in the same process deletes that day's `.db`, `-wal` and `-shm` on its first try (docs/17:149); the pass's log record carries its CPU seconds.
- **Gate evidence:** P4.1; section 1, row D9
- **Depends on:** P4-W2-T1, P4-W2-T3, P4-W1-T3, P4-W1-T4 · **Size:** L · **OS:** either; the deletion case on CI-W


#### Wave P4-W4 (2 builders)

**P4-W4-T1 · The P4 gate harness**

- **Advances:** gate P4; R117, R52, R80
- **Owns:** `tests/test_gate_p4.py`, `tests/tools/time_cmd.py`
- **Uses:** the fixtures, the detectors, `why`. **Provides:** evidence for P4.1 to P4.5, under the harness contract of section 6.2
- **Work:** P4.1: each detector, verdict class and alert rule against a trigger and a quiet fixture; P4.2 to P4.4 at the fixed seed counts and pass rates; a finding raised by each detector appears in `findings` and `why`; P4.5: `tests/tools/time_cmd.py` times 20 runs of the virtual environment's own entry point (`.venv\Scripts\submeter.exe` on Windows, `.venv/bin/submeter` on Linux, not `uv run`; section 6.8) on P3-W1-T2's 5-minute, 300-process raw file, every run under 2.0 s, the first run after a restart recorded on its own.
- **Tests first:** It is the acceptance test; CI cases pass before merge.
- **Gate evidence:** P4.1 to P4.5
- **Depends on:** P4-W3-T1, P4-W3-T2, P4-W3-T3 · **Size:** M · **OS:** either; P4.5 on the owner's machine in P4-O1

**P4-W4-T2 · The soak with analysis on**

- **Advances:** gate P4; R87
- **Owns:** `.github/workflows/soak.yml`, `tests/tools/soak_schedule.py`, `tests/test_soak_workflow.py`
- **Uses:** the soak workflow. **Provides:** the budget measured again with analysis and alerts running
- **Work:** The 30-minute soak again with the server running analysis and alerts, since the leak check reads up to 48 h of raw rows per workload (I38).
- **Tests first:** `tests/test_soak_workflow.py`: the dry run covers the analysis pass.
- **Gate evidence:** P4.6; section 1, row D5
- **Depends on:** P4-W3-T3 · **Size:** S · **OS:** either (both runners)


#### Owner tasks (outside the waves; no builder)

**P4-O1 · Owner: `why` timing on the Windows machine** (at the P4 gate commit G4, after P4-W4 integrates)

- **Advances:** gate P4; R119 (`why` read from files on the target machine)
- **Owns:** `docs/gates/P4/owner/`
- **Uses:** `tests/test_gate_p4.py` and `tests/tools/time_cmd.py` (P4-W4-T1) on `.venv\Scripts\submeter.exe`, with P3-W1-T2's 5-minute raw file, at G4. **Provides:** `docs/gates/P4/owner/`: `harness/P4.5.json` with the 20 times and the first run after the restart apart, and `checks/`. The gate reviewer reads them
- **Work:** After a restart of the computer and before any other Submeter command, P4.5 through `tests/tools/time_cmd.py` on `.venv\Scripts\submeter.exe`, 20 runs, the first after the restart recorded on its own (section 6.8). Then the owner check run of section 6.2 step 4 at G4; here it comes second, because the cold start must come first.
- **Gate evidence:** S1 on the owner's machine; P4.5
- **Depends on:** every P4 builder task, among them P4-W4-T1 (it runs at G4) · **Time:** about 15 minutes · **OS:** the owner's personal Windows 11 PC, as the signed-in standard user, for the evidence; on the work PC only the owner check run of section 6.2 step 4, reported by word (section 3.1, Owner tasks)


### 3.9 P5: report and GPU load

`docs/15-phases-and-decisions.md:65-69`: `submeter report` and the extended providers for GPU load by engine type and the adapter's VRAM. `submeter export` (JSON and CSV, R144) has no phase in the brief and is built here. The API and the live dashboard are version 1.1.

#### Wave P5-W1 (4 builders)

**P5-W1-T1 · The report's data records**

- **Advances:** components 01, 24; I42, I78; L00, L06; `docs/04-features.md:16-17`; `docs/06-storage.md:129`, `:133`
- **Owns:** `src/submeter/core/models.py`, `tests/builders.py`, `tests/test_models.py`
- **Uses:** docs/07:5, docs/06:99-100. **Provides:** `ReportData` and its parts
- **Work:** Records the CLI fills and the report package renders: series with their tier and resolution and min-to-max envelope, each hourly bucket that fails `well_covered` marked so that trend series leave it out (P3-W3-T2); the epoch boundaries in the range, each with its time and reason (docs/06:129); the frequency series shown beside CPU time (L06); a row per workload with its accounting source (kernel, polled or counters; docs/04:16), its CPU, memory, I/O and GPU load by engine type, and the notes of the known limits that apply to it (L01, L02, L03, L04, L10, L12, from `core.limits`); the four fixed workloads, present with no members (docs/04:17); findings; the six terms with the count of processes whose start time could not be read (I42); the session diff and the leak view (B9 (a): the report sits at layer 2 and imports only `core`).
- **Tests first:** Each part refuses a missing tier or resolution; an epoch boundary refuses a missing reason; a workload row refuses a missing accounting source.
- **Gate evidence:** none directly
- **Depends on:** gate P4; decision B9 · **Size:** M · **OS:** either

**P5-W1-T2 · Windows GPU load and adapter VRAM**

- **Advances:** components 23; R148; L07
- **Owns:** `src/submeter/providers/windows/gpu.py`, `tests/test_gpu_windows.py`, `tests/fixtures/gpu/windows/`
- **Uses:** `ExtendedProvider`; PDH GPU Engine counters by English name. **Provides:** GPU load by engine type, machine-wide and per process; adapter VRAM used and total
- **Work:** Engine percentages are not added across engine types; the busiest type is the headline; the adapter's VRAM used and total come from a source the builder confirms in current documentation, and if none is readable without administrator rights the builder stops and reports the task blocked (section 10.3, item 12); the owner's ruling on B18 then holds the task's merge, not its dispatch, because this task's builder is the one who looks for the source. Capability rows `gpu.load` and `gpu.memory` ("adapter total only", L07). With its source absent the provider reports unavailable with a reason, every metric None, no exception.
- **Tests first:** Parsing of documentation-shaped counter fixtures; an absent counter set gives unavailable and None fields; each PDH structure is built from fixed-width types and its size and field offsets are checked on both systems (section 7.3.1).
- **Gate evidence:** P5.2, P5.3
- **Depends on:** gate P4 · **Size:** L · **OS:** Windows (CI-W); hardware on the owner's machine

**P5-W1-T3 · Linux GPU load**

- **Advances:** components 23; R75, I51
- **Owns:** `src/submeter/providers/linux_gpu.py`, `tests/test_gpu_linux.py`, `tests/fixtures/gpu/linux/`
- **Uses:** `ExtendedProvider`. **Provides:** GPU load on Linux from NVML, DRM fdinfo and amdgpu
- **Work:** NVML through ctypes for NVIDIA (no new dependency); DRM fdinfo `drm-engine-*` per process for the user's own processes (i915, xe); amdgpu `gpu_busy_percent` for the device only. NVIDIA and AMD are tested from documentation-shaped fixtures and stated as never run on real hardware.
- **Tests first:** Parsing of each fixture; each source absent gives unavailable and None fields.
- **Gate evidence:** P5.2, P5.3
- **Depends on:** gate P4 · **Size:** L · **OS:** Linux (CI-L)

**P5-W1-T4 · The vendored chart library**

- **Advances:** components 24; R109
- **Owns:** `src/submeter/report/assets/`, `tests/test_report_assets.py`
- **Uses:** the uPlot release at a pinned version. **Provides:** `uplot.min.js` and its licence text in the package
- **Work:** Vendors uPlot and its licence text under `src/submeter/report/assets/`, recording the SHA-256 of each file in the test; fetched once by the builder, never at run time.
- **Tests first:** Both files present with the recorded hashes; a wheel built with `uv build --wheel` contains both.
- **Gate evidence:** P5.1 input
- **Depends on:** gate P4 · **Size:** S · **OS:** either


#### Wave P5-W2 (4 builders)

**P5-W2-T1 · The report renderer**

- **Advances:** components 24; R109, I78; L00, L06
- **Owns:** `src/submeter/report/__init__.py`, `src/submeter/report/render.py`, `tests/test_report.py`
- **Uses:** `ReportData`, the vendored assets. **Provides:** `render(data) -> str`
- **Work:** One self-contained HTML file: script, styles, data and uPlot inline; a meta Content Security Policy `default-src 'none'` with a SHA-256 hash for each inline script and style; each chart names its tier and resolution and draws the min-to-max envelope; each epoch boundary in a chart's range is drawn on it as a marker with its reason (docs/06:129, docs/08:117); a history chart leaves out the buckets marked as less than half covered (docs/06:133); every value from data HTML-escaped and inserted with `textContent`, never `innerHTML` (I78); no command line and no working folder; frequency beside each CPU chart, with L06's note (`docs/10-known-limits.md:14`). The workload tables, findings, the six terms and the leak and session-diff views are P5-W3-T3's. Imports only `core` (layer 2).
- **Tests first:** 0 occurrences of `http://` or `https://`; the CSP hashes match the inline blocks; a process name holding `<script>` appears escaped; a CPU chart carries the frequency series and L06's note; a `ReportData` with one epoch boundary gives exactly one marker, with its reason; a bucket marked as less than half covered is absent from the chart's series.
- **Gate evidence:** P5.1
- **Depends on:** P5-W1-T1, P5-W1-T4; decision B9 · **Size:** L · **OS:** either

**P5-W2-T2 · The collector reads the GPU providers**

- **Advances:** components 07, 23; R148
- **Owns:** `src/submeter/programs/collector/loop.py`, `tests/test_collector_program.py`
- **Uses:** the GPU providers; GPU load by engine type on `ProcessCounters` and `ProcessSample` (P0-W3-T1), which P0-W4-T1's sampler copies from the one to the other. **Provides:** GPU columns filled in raw files
- **Work:** Reads the extended providers at `gpu_interval` and writes the machine-wide GPU columns the raw schema already has (P2-W3-T1). Each per-process GPU reading goes onto the `ProcessCounters` of the process with that pid in the same tick's snapshot, before `Sampler.ingest`, which copies it into the `ProcessSample`, so that `aggregate` sums it per workload by engine type (P0-W5-T1) and the per-process and per-workload GPU columns are filled (docs/13:31, docs/17:111); between GPU ticks they stay NULL.
- **Tests first:** With fake GPU providers the columns are filled at the GPU cadence and stay NULL when the source is absent; a fake per-process GPU reading reaches its process's row and its workload's row, summed by engine type over two members.
- **Gate evidence:** P5.3
- **Depends on:** P5-W1-T2, P5-W1-T3 · **Size:** M · **OS:** either

**P5-W2-T3 · `submeter export`**

- **Advances:** components 12; R144
- **Owns:** `src/submeter/cli/export.py`, `tests/test_cli_export.py`
- **Uses:** history and query readers. **Provides:** JSON and CSV export
- **Work:** Exports history and raw windows as JSON or CSV with the standard library, to the file the user names; no command lines. `--json` prints the envelope `submeter.export/1` (docs/03:86) naming the file written, its format, the window, the tiers it read and the row count.
- **Tests first:** A round trip of a synthetic window through JSON and CSV; a canary command line absent; a snapshot test of `export --json`, kept in `tests/test_cli_export.py`, asserts the `schema` key and the field set (S4).
- **Gate evidence:** none directly
- **Depends on:** gate P4 · **Size:** M · **OS:** either

**P5-W2-T4 · `doctor` for phase 5**

- **Advances:** components 12, 23; L07
- **Owns:** `src/submeter/cli/doctor.py`, `tests/test_cli_doctor.py`
- **Uses:** the GPU providers' capability rows. **Provides:** `gpu.load` and `gpu.memory` rows
- **Work:** The two GPU rows with their status and reason.
- **Tests first:** Rows on each system with the source absent.
- **Gate evidence:** P5.3
- **Depends on:** P5-W1-T2, P5-W1-T3 · **Size:** S · **OS:** either


#### Wave P5-W3 (3 builders)

**P5-W3-T1 · `submeter report`**

- **Advances:** components 24, 12; R150
- **Owns:** `src/submeter/cli/report.py`, `tests/test_cli_report.py`
- **Uses:** query and history readers, analysis, `submeter.report`. **Provides:** `submeter report [--session S | --from --to] [--out FILE]`
- **Work:** Builds `ReportData` for a session or a range and writes one file to the working folder or `--out`. `--json` prints the envelope `submeter.report/1` (docs/03:86) naming the file written and its session or range.
- **Tests first:** On a synthetic store, one file per run, for a session and for a range; a snapshot test of `report --json`, kept in `tests/test_cli_report.py`, asserts the `schema` key and the field set (S4); over a range of the 30-day store (P3-W3-T3) that crosses its rules change, the report holds exactly one epoch marker, with the reason "rules file".
- **Gate evidence:** P5.1
- **Depends on:** P5-W2-T1; decision B9 · **Size:** M · **OS:** either

**P5-W3-T2 · The soak with the GPU providers**

- **Advances:** gate P5; R148
- **Owns:** `.github/workflows/soak.yml`, `tests/tools/soak_schedule.py`, `tests/test_soak_workflow.py`
- **Uses:** the soak workflow. **Provides:** the budget measured with the GPU providers on
- **Work:** The 30-minute soak again with the GPU providers enabled (they degrade to unavailable on the runners, which have no GPU).
- **Tests first:** `tests/test_soak_workflow.py`: the dry run covers the GPU providers.
- **Gate evidence:** P5.4; section 1, row D5
- **Depends on:** P5-W2-T2 · **Size:** S · **OS:** either (both runners)

**P5-W3-T3 · The report's workload tables, terms and notes**

- **Advances:** components 24; R45, R65, I42, I78; L00, L01, L02, L03, L04, L10, L12; `docs/04-features.md:16-17`
- **Owns:** `src/submeter/report/render.py`, `src/submeter/report/tables.py`, `tests/test_report.py`
- **Uses:** `ReportData` (P5-W1-T1); `render` and its page (P5-W2-T1); `core.limits` (P2-W1-T1). **Provides:** the report's workload tables, findings, six terms, leak and session-diff views, and the known-limit notes beside the figures they affect
- **Work:** `report/tables.py` renders the parts of the page beside the charts, and `render.py` places them: a row per workload with its accounting source (kernel, polled or counters; docs/04:16), CPU, memory, I/O and GPU load by engine type where present, each n/a or partial with its count as `ReportData` gives it; the four fixed workloads, System, Restricted, Unattributed and Submeter, always shown, with no members if none, and the CPU time not seen by polling beside them (docs/04:17, docs/17:127; Q16); the six terms, with the count of processes whose start time could not be read beside Restricted (I42, docs/17:102); findings; the leak and session-diff views; and the known-limit notes beside the figures they affect (L00, `docs/10-known-limits.md:5`): L01 beside `agent:*` workloads, L02 beside polled workloads, L03 beside tagged runs, L04 beside figures read on Linux, L10 beside Restricted and System, L12 beside memory totals. Every value is escaped and inserted with `textContent` (I78). Split from the renderer of P5-W2-T1 so that neither task grows past size L.
- **Tests first:** In `tests/test_report.py`: a kernel and a polled workload each carry their label; each of the notes of L01, L02, L03, L04, L10 and L12 appears beside the figure it affects; the four fixed rows appear with no members, with the not-seen figure beside them; the unreadable count appears beside Restricted; a workload's GPU load appears per engine type, and n/a when absent; a finding and the six terms appear; a name holding `<script>` stays escaped in every table. Fails before: P5-W2-T1's renderer draws the charts only.
- **Gate evidence:** P5.1
- **Depends on:** P5-W2-T1, P5-W1-T1; decision B9 · **Size:** L · **OS:** either


#### Wave P5-W4 (1 builder)

**P5-W4-T1 · The P5 gate harness**

- **Advances:** gate P5; R109, I78
- **Owns:** `tests/test_gate_p5.py`
- **Uses:** the synthetic store, `submeter report`, a headless Chromium-based browser on the runner; the owner's GPU recordings (P5-O1). **Provides:** evidence for P5.1 to P5.3, under the harness contract of section 6.2
- **Work:** P5.1 on a synthetic store in scrub mode with canary arguments, over a range that spans raw and hourly data: one file per run; 0 `http://` or `https://`; the canaries absent; each chart caption names raw or hourly and a resolution; a finding stored in the synthetic store appears (row D9); each epoch boundary in the range is marked with its reason; each workload shows its accounting source, and the four fixed rows appear; the known-limit notes appear beside the figures they affect; the browser check of section 7.5, with no package added: a headless Chrome or Edge from the runner image runs `--dump-dom` on the report with every request sent to a closed local port and a NetLog file, read with the standard library, and records 0 Content Security Policy messages and 0 requests other than the report. The builder confirms in current Chromium documentation which images carry a browser and which switches give these records; if neither runner image has one, the case is marked `owner_machine` and runs with Edge in P5-O2's step 4. P5.2: each extended provider's fixtures replayed against the expected values written beside them: the owner's Windows GPU recordings (P5-O1) and the documentation-shaped fixtures of P5-W1-T2 and P5-W1-T3. P5.3: each source absent.
- **Tests first:** It is the acceptance test; CI cases pass before merge.
- **Gate evidence:** P5.1, P5.2, P5.3
- **Depends on:** P5-W3-T1, P5-W3-T3, P5-W2-T2, P5-O1 · **Size:** M · **OS:** either


#### Owner tasks (outside the waves; no builder)

**P5-O1 · Owner: GPU fixtures on the Windows machine** (after P5-W1 integrates)

- **Advances:** tools beside the code: recorded fixtures for the GPU providers (`docs/13-build-list.md:50`); R107, R148
- **Owns:** `tests/fixtures/recorded/gpu/`, `docs/gates/P5/owner/anonymised-P5-O1.txt`
- **Uses:** the fixture recorder (P2-W4-T3) and the Windows GPU provider (P5-W1-T2), at the P5-W1 integration commit; `tests/test_fixtures_anonymised.py`. **Provides:** `tests/fixtures/recorded/gpu/`: JSON Lines of the GPU provider's readings with `manifest.json` and `expected.json` (section 7.3.3), which P5-W4-T1 replays for P5.2; `docs/gates/P5/owner/anonymised-P5-O1.txt` for S5
- **Work:** Records the Windows GPU provider of P5-W1-T2 with the fixture recorder of P2-W4-T3, which takes any provider of P2-W1-T1's protocols (`uv run --directory tests python -m tools.record_fixture <module>:<class>`); runs `tests/test_fixtures_anonymised.py` on that machine before committing and saves its output as `docs/gates/P5/owner/anonymised-P5-O1.txt` (S5).
- **Gate evidence:** S5; P5.2
- **Depends on:** P5-W1-T2 · **Time:** about 15 minutes · **OS:** the owner's personal Windows 11 PC only, as the signed-in standard user; not run on the work PC (section 3.1, Owner tasks)

**P5-O2 · Owner: the final checks and 24-hour soak** (at the P5 gate commit G5, after P5-W4 integrates)

- **Advances:** gate P5; row D16 (the checks on the owner's machine at the final commit); R87 and R148 (the budget with every program and provider, if the soak is kept)
- **Owns:** `docs/gates/P5/owner/`, except `anonymised-P5-O1.txt`, which P5-O1 commits before P5-O2 starts
- **Uses:** every program of version 1 at G5; the soak monitor and checker (P2-W5-T4). **Provides:** `docs/gates/P5/owner/`: `checks/` (row D16) and, if the soak is kept, `soak/` as in P2-O2. The gate reviewer reads them for S1 and P5.5
- **Work:** Begins with the owner check run of section 6.2 step 4 at G5, which runs whether or not the soak is kept, so that the seven checks pass on the owner's machine at the final commit (row D16). Then, if the owner keeps it, the P2-O2 soak again with every program and provider of version 1 (proposed by this plan because the server's analysis and the GPU providers are added after P2's soak; the owner decides whether it is required, Q6).
- **Gate evidence:** S1 on the owner's machine (row D16); P5.5 if the soak is kept (row D5)
- **Depends on:** every P5 builder task, among them P5-W4-T1 (it runs at G5) · **Time:** step 4, then 24 hours elapsed and under 1 hour attended if the soak is kept · **OS:** the owner's personal Windows 11 PC, as the signed-in standard user, for the evidence; on the work PC only the owner check run of section 6.2 step 4, reported by word (section 3.1, Owner tasks)


## 4. File ownership map

### 4.1 Rules

1. In a wave each path has exactly one owning task. A path ending in `/` is a folder and covers everything under it. The map in 4.4 is generated from the tasks' Owns lines; a script checked that no path, and no path under an owned folder, has two owners in any wave, and that no builder task in a phase owns anything under an owner task's folder (section 9.10 records the result).
2. A task creates, changes or deletes only the paths it owns. It may read anything.
3. A builder's working copy starts from the wave's base commit: the integration commit of the previous wave, pushed before the wave starts. A later wave therefore sees every earlier wave's merged work.
4. Ownership ends when the task is merged; a later wave's task may own the same path.
5. Never owned by a builder: `docs/STATUS.md`, `docs/14-baseline-modules.md`, `docs/PLAN.md`, the task cards under `docs/tasks/` and the review notes (the lead, which writes the review notes from each checker's reply, because checkers cannot write; stage 3 sets their folder); `prompts/02-orchestration-prompt.md` and `.claude/agents/` (the lead, each change read by the plan reviewer); `.claude/settings.json` (the lead, each change approved by the owner, because it holds the permission rules); `AGENTS.md` and `CLAUDE.md` (the owner).
6. `docs/14-baseline-modules.md` describes each baseline module, its line count and its "Not here yet" items, so almost every task makes an entry stale. A builder writes the replacement lines in its task report under the heading "docs/14"; the lead applies them in the wave's record commit with `docs/STATUS.md`, and a reviewer with fresh context reads that commit before the next wave is dispatched (plan choice C6).
7. A merge conflict means the ownership was wrong. The lead stops the wave's remaining merges, records a planning defect in `docs/STATUS.md` and corrects the plan; the code is not patched round it.


### 4.2 Shared files and their owners

A shared file is one that more than one task changes over the build. Each has one standing owner, named first in the second column: the lead for every file a builder holds, and the owner for `AGENTS.md`, `CLAUDE.md` and the owner tasks' folders. The standing owner decides every change request against the file, in every wave (4.3 item 4). After the semicolon the second column says which task writes the file in each wave; in each wave at most one task holds it, and the third column lists those tasks. The table lists every path that more than one card's Owns line names, directly or under a folder that card owns, with its holders generated from the task cards; it also keeps a row for a file the stage 2 prompt names as shared, or one with a rule of its own, where only one task holds it, and for the files no builder holds. A path not in the table is held by the one task whose card owns it.

| Path | Standing owner; who writes it in each wave | Held by (the wave is in each task id) |
| --- | --- | --- |
| `pyproject.toml` | the lead; the task that holds it in its wave (P0-W1-T1 for CI, markers and `addopts`; then each program task that adds a console script); a new dependency also needs the owner's approval (`AGENTS.md:49`) | P0-W1-T1, P2-W5-T1, P3-W3-T1 |
| `uv.lock` | the lead; travels with `pyproject.toml`; changed only by `uv lock` after an approved dependency change, and none is planned (adding a console script leaves it unchanged, checked with `uv lock --offline` on a copy) | P0-W1-T1, P2-W5-T1, P3-W3-T1 |
| `src/submeter/core/models.py` | the lead; one task per phase that changes records (section 3.1, Records); travels with `tests/builders.py` and `tests/test_models.py` | P0-W3-T1, P0-W4-T1, P0-W5-T1, P1-W1-T2, P2-W1-T1, P3-W1-T1, P4-W1-T1, P5-W1-T1 |
| `tests/builders.py` | the lead; travels with `core/models.py`; P0-W2-T1 first creates it from the three copies in the baseline tests | P0-W2-T1, P0-W3-T1, P0-W4-T1, P0-W5-T1, P1-W1-T2, P2-W1-T1, P3-W1-T1, P4-W1-T1, P5-W1-T1 |
| `src/submeter/core/config.py` | the lead; the task that holds it in its wave; after P0 only P2-W1-T1 (provider names) and P4-W2-T2 (threshold values) | P0-W3-T1, P0-W4-T2, P2-W1-T1, P4-W2-T2 |
| `src/submeter/cli.py` | the lead; P0-W2-T3, which replaces it with the package `src/submeter/cli/` | P0-W2-T3 |
| `src/submeter/cli/__init__.py` | the lead; P0-W2-T3 only; commands register by discovery (plan choice C8), so no later task edits it | P0-W2-T3 |
| `src/submeter/cli/_common.py` | the lead; P0-W2-T3, then P0-W3-T2; later changes by change request | P0-W2-T3, P0-W3-T2 |
| `src/submeter/cli/_envelope.py` | the lead; P1-W1-T1; later changes by change request | P1-W1-T1 |
| `src/submeter/cli/_format.py` | the lead; P1-W1-T1; later changes by change request | P1-W1-T1 |
| `src/submeter/cli/top.py` | the lead; the task that holds it in its wave | P0-W2-T3, P0-W3-T2, P0-W5-T1, P1-W1-T1, P2-W1-T2, P2-W5-T2 |
| `src/submeter/cli/doctor.py` | the lead; one task per phase adds that phase's rows (two in P3); travels with `tests/test_cli_doctor.py` | P0-W2-T3, P1-W1-T1, P1-W2-T4, P2-W5-T3, P3-W5-T4, P3-W6-T3, P5-W2-T4 |
| `src/submeter/cli/config.py` | the lead; the task that holds it in its wave | P0-W2-T3, P0-W3-T2, P1-W1-T1, P3-W5-T3 |
| `src/submeter/cli/cost.py` | the lead; the task that holds it in its wave | P1-W2-T3, P3-W5-T1 |
| `src/submeter/store/files.py` | the lead; the task that holds it in its wave; `FileMap` is the only place paths are built, so each new kind of file is a change here: P2-W4-T1 adds the control folder, its sessions subfolder, the stop files and the backup request, which P3-W2-T3 uses | P0-W3-T1, P0-W4-T1, P1-W1-T2, P2-W3-T1, P2-W4-T1, P3-W1-T4 |
| `src/submeter/store/raw.py` | the lead; the task that holds it in its wave; the raw schema | P0-W4-T1, P0-W5-T1, P2-W1-T2, P2-W3-T1, P3-W1-T4 |
| `src/submeter/store/rollup.py` | the lead; the task that holds it in its wave | P0-W3-T1, P0-W5-T1, P2-W1-T2, P3-W2-T2 |
| `src/submeter/store/query.py` | the lead; the task that holds it in its wave | P0-W3-T1, P3-W3-T2, P4-W1-T3 |
| `src/submeter/store/control.py` | the lead; the task that holds it in its wave | P2-W4-T1, P3-W2-T3 |
| `src/submeter/store/history.py` | the lead; P3-W1-T1 (DDL), then P3-W2-T1 (writers and readers) | P3-W1-T1, P3-W2-T1 |
| `src/submeter/attribution/rules.py` | the lead; the task that holds it in its wave | P0-W4-T1, P0-W5-T1, P2-W1-T2, P2-W2-T4, P3-W2-T4, P3-W3-T4 |
| `src/submeter/attribution/reconcile.py` | the lead; the task that holds it in its wave | P2-W2-T4, P2-W4-T2 |
| `src/submeter/providers/psutil_provider.py` | the lead; the task that holds it in its wave. P2-W1-T1 changes only the `snapshot` signature, in the same change as the protocol in `providers/base.py`, because under strict mypy a provider that no longer matches the protocol fails `doctor`'s call (`cli.py:57-60`) | P0-W4-T1, P2-W1-T1, P2-W2-T2, P2-W4-T2 |
| `src/submeter/providers/windows/job.py` | the lead; P1-W1-T4, then P3-W1-T3 | P1-W1-T4, P3-W1-T3 |
| `src/submeter/providers/windows/bulk.py` | the lead; P2-W2-T1, then P2-W3-T4 | P2-W2-T1, P2-W3-T4 |
| `src/submeter/collector/sampler.py` | the lead; the task that holds it in its wave | P0-W4-T1, P2-W1-T2, P2-W3-T3, P2-W4-T4 |
| `src/submeter/programs/collector/loop.py` | the lead; P2-W5-T1, then one task in each of P3 and P5 | P2-W5-T1, P3-W2-T4, P5-W2-T2 |
| `src/submeter/programs/server/loop.py` | the lead; P3-W3-T1, then P4-W3-T3 | P3-W3-T1, P4-W3-T3 |
| `tests/test_layers.py` | the lead; P0-W2-T1 only: it writes the rows for every package version 1 adds, so no later task edits it | P0-W2-T1 |
| `tests/test_config.py` | the lead; the task that holds it in its wave | P0-W2-T1, P0-W3-T1, P0-W4-T2, P0-W6-T1, P2-W1-T1, P4-W2-T2 |
| `tests/test_attribution.py` | the lead; the task that holds it in its wave | P0-W2-T1, P0-W4-T1, P0-W5-T1, P0-W6-T1, P2-W1-T2, P2-W2-T4, P3-W2-T4, P3-W3-T4 |
| `tests/test_raw.py` | the lead; the task that holds it in its wave | P0-W2-T1, P0-W4-T1, P0-W5-T1, P0-W6-T1, P2-W1-T2, P2-W3-T1, P3-W1-T4 |
| `tests/test_sampler.py` | the lead; the task that holds it in its wave | P0-W2-T1, P0-W4-T1, P0-W6-T1, P2-W1-T2, P2-W3-T3, P2-W4-T4 |
| `tests/test_collector_program.py` | the lead; travels with `programs/collector/loop.py` | P2-W5-T1, P3-W2-T4, P5-W2-T2 |
| `scripts/platform_check.py` | the lead; the task that holds it in its wave; it calls `Sampler`, `PsutilProvider`, `FileMap`, `InstanceLock` and `RawFile`, and mypy does not check it. P2-W1-T2 changes its call to `Sampler.ingest`; after that, a task that changes a signature it calls keeps the old call valid (the cards of P2-W2-T2, P2-W3-T1, P2-W3-T3 and P2-W4-T4 say so), and `tests/test_platform_check.py` (P0-W4-T1) runs its checks on every push, so a break shows on the breaking task's branch | P0-W4-T1, P0-W5-T1, P2-W1-T2 |
| `.github/workflows/ci.yml` | the lead; P0-W1-T1, then P0-W2-T4 | P0-W1-T1, P0-W2-T4 |
| `.github/workflows/soak.yml` | the lead; P2-W6-T2, then one task in each of P3, P4 and P5 | P2-W6-T2, P3-W6-T2, P4-W4-T2, P5-W3-T2 |
| `tests/tools/soak_schedule.py`, `tests/test_soak_workflow.py` | the lead; travel with `soak.yml`: the soak's driver and its dry run | P2-W6-T2, P3-W6-T2, P4-W4-T2, P5-W3-T2 |
| `examples/submeter.toml` | the lead; the task whose settings change it holds it; every settings change must keep `uv run submeter config check examples/submeter.toml` at exit 0 | P0-W4-T2, P2-W1-T1, P4-W2-T2 |
| `docs/06-storage.md` | the lead; the task that holds it in its wave; the run file (P1), the raw columns and disk table (P2), the history DDL (P3) | P1-W1-T2, P2-W3-T1, P2-W6-T2, P3-W1-T1 |
| `docs/03-cli-output.md` | the lead; P1-W1-T1 (the envelope), then P3-W5-T1 (the `cost` sample, under Q16) | P1-W1-T1, P3-W5-T1 |
| `docs/07-analysis.md` | the lead; P4-W2-T2 | P4-W2-T2 |
| `docs/08-configuration.md` | the lead; P0-W4-T2 | P0-W4-T2 |
| `scripts/probes/bulk_snapshot.py` | the lead; P0-W6-T2, then P2-W1-T2, which changes its call to `Sampler.ingest`. After that, a task that changes a signature it calls keeps the old call valid (the cards of P2-W2-T2, P2-W3-T1, P2-W3-T3 and P2-W4-T4 say so); `tests/test_probe_bulk.py` runs it on every push, so a break shows on the breaking task's branch | P0-W6-T2, P2-W1-T2 |
| `src/submeter/analysis/growth.py` | the lead; the task that holds it in its wave | P0-W3-T1, P4-W2-T1 |
| `src/submeter/cli/store.py` | the lead; the task that holds it in its wave | P0-W2-T3, P1-W1-T1, P3-W5-T2 |
| `src/submeter/programs/server/backups.py` | the lead; P3-W3-T1 writes it as a pass that does nothing; P3-W4-T2 fills it | P3-W3-T1, P3-W4-T2 |
| `src/submeter/programs/server/epochs.py` | the lead; P3-W3-T1 writes it as a pass that does nothing; P3-W4-T4 fills it | P3-W3-T1, P3-W4-T4 |
| `src/submeter/programs/server/ingest.py` | the lead; P3-W3-T1 writes it as a pass that does nothing; P3-W4-T3 fills it | P3-W3-T1, P3-W4-T3 |
| `src/submeter/programs/server/retention.py` | the lead; P3-W3-T1 writes it as a pass that does nothing; P3-W4-T1 fills it | P3-W3-T1, P3-W4-T1 |
| `src/submeter/report/render.py` | the lead; P5-W2-T1 (the page and the charts), then P5-W3-T3 (the tables and notes) | P5-W2-T1, P5-W3-T3 |
| `tests/test_bulk.py` | the lead; travels with `providers/windows/bulk.py` | P2-W2-T1, P2-W3-T4 |
| `tests/test_cli.py` | the lead; the task that holds it in its wave | P0-W2-T1, P1-W1-T1 |
| `tests/test_cli_cost.py` | the lead; travels with `cli/cost.py` | P1-W2-T3, P3-W5-T1 |
| `tests/test_cli_doctor.py` | the lead; travels with `cli/doctor.py` | P1-W2-T4, P2-W5-T3, P3-W5-T4, P3-W6-T3, P5-W2-T4 |
| `tests/test_cli_top.py` | the lead; travels with `cli/top.py` | P0-W5-T1, P1-W1-T1, P2-W1-T2, P2-W5-T2 |
| `tests/test_control.py` | the lead; travels with `store/control.py` | P2-W4-T1, P3-W2-T3 |
| `tests/test_files.py` | the lead; the task that holds it in its wave | P0-W2-T1, P0-W3-T1, P0-W4-T1, P1-W1-T2, P2-W3-T1, P2-W4-T1, P3-W1-T4 |
| `tests/test_growth.py` | the lead; the task that holds it in its wave | P0-W2-T1, P4-W2-T1 |
| `tests/test_history.py` | the lead; travels with `store/history.py` | P3-W1-T1, P3-W2-T1 |
| `tests/test_job.py` | the lead; travels with `providers/windows/job.py` | P1-W1-T4, P3-W1-T3 |
| `tests/test_models.py` | the lead; travels with `core/models.py`; P0-W2-T1 first creates it, moving the existing model tests into it | P0-W2-T1, P0-W3-T1, P0-W4-T1, P0-W5-T1, P1-W1-T2, P2-W1-T1, P3-W1-T1, P4-W1-T1, P5-W1-T1 |
| `tests/test_privacy.py` | the lead; the task that holds it in its wave | P0-W2-T1, P3-W3-T4 |
| `tests/test_probe_bulk.py` | the lead; travels with `scripts/probes/bulk_snapshot.py` | P0-W6-T2, P2-W1-T2 |
| `tests/test_psutil_provider.py` | the lead; the task that holds it in its wave | P0-W2-T1, P0-W4-T1, P0-W6-T1, P2-W2-T2, P2-W4-T2 |
| `tests/test_query.py` | the lead; the task that holds it in its wave | P0-W2-T1, P0-W3-T1, P0-W6-T1, P3-W3-T2, P4-W1-T3 |
| `tests/test_reconcile.py` | the lead; travels with `attribution/reconcile.py` | P2-W2-T4, P2-W4-T2 |
| `tests/test_report.py` | the lead; travels with `report/render.py` | P5-W2-T1, P5-W3-T3 |
| `tests/test_rollup.py` | the lead; the task that holds it in its wave | P0-W2-T1, P0-W5-T1, P0-W6-T1, P2-W1-T2, P3-W2-T2 |
| `docs/14-baseline-modules.md` | the lead (its record step, from the builders' reports; plan choice C6); never a builder | no task |
| `docs/STATUS.md` | the lead (its record step); never a builder | no task |
| `docs/PLAN.md` | the lead (as plan writer); each change read by the plan reviewer; never a builder | no task |
| `AGENTS.md` | the owner; changed only with the owner's approval of the exact wording | no task |
| `CLAUDE.md` | the owner; as `AGENTS.md` | no task |
| `tests/fixtures/recorded/` | the owner; written only by the owner tasks that record fixtures (P2-O1, P5-O1) | no task |
| `docs/gates/P2/owner/`, `docs/gates/P5/owner/` | the owner; written by the phase's last owner task (P2-O2, P5-O2), except `anonymised-P2-O1.txt` and `anonymised-P5-O1.txt`, which the phase's first owner task commits before the last one starts (P2-O2 needs P2-W6-T3, which needs P2-O1; P5-O2 needs P5-W4-T1, which needs P5-O1), so the two never write at once | no task |
| `docs/tasks/`, the review notes | the lead (rule 5) | no task |
| `prompts/02-orchestration-prompt.md`, `.claude/agents/` | the lead; each change read by the plan reviewer | no task |
| `.claude/settings.json` | the lead; each change approved by the owner, because it holds the permission rules | no task |

### 4.3 How anyone else requests a change

1. A builder that needs a change in a path it does not own does not make it. It writes a change request in its task report: the path, the exact change (a diff or the wording), the reason, and which of its tests needs it.
2. If the task can be finished without the change, it is finished and merged, and the request waits. If it cannot, the builder stops and reports the task blocked. It never edits the other path and never skips or marks a test to get round it.
3. The lead gives the request an id (CR-nnn) and records it in `docs/STATUS.md` under "Change requests" with the requesting task and the path.
4. The lead, the standing owner of every file a builder holds (4.2), accepts or refuses the request, and schedules an accepted one into the next wave: into the task that owns the path in that wave, whose card gains it, or else as a new task of size S that owns the path. A request against a contract file (`core/models.py`, `core/config.py`, a module of `submeter.cli`, `store/raw.py`'s schema, `pyproject.toml`) is checked against this plan first, because other tasks read that file. A request against a file the owner owns goes to the owner (item 5).
5. A request to change `AGENTS.md` or `CLAUDE.md` goes to the owner with the proposed wording and waits for the owner's approval of that exact change. A request that adds a dependency needs the owner's approval too (`AGENTS.md:49`).
6. A request that would change a decision of section 5.6 or a choice of section 5.7 goes to the owner, not to a builder.


### 4.4 Paths owned in each wave

Every path a task may create, change or delete in its wave. A path ending in `/` is a folder and covers everything under it. Owner tasks own their evidence folders for their whole phase; no builder task in that phase owns anything under them.


**P0-W1**

- P0-W1-T1: `.github/workflows/ci.yml`, `pyproject.toml`, `uv.lock`, `tests/test_project.py`
- P0-W1-T2: `scripts/probes/cpu_time_check.py`, `scripts/probes/restricted_share.py`, `scripts/probes/replace_names.py`, `tests/test_probe_step1.py`, `docs/review/ground-windows/step1-procedure.md`
- P0-O1 (owner task, from the integration of this wave to the P0 gate): `docs/review/ground-windows/step1/`

**P0-W2**

- P0-W2-T1: `tests/builders.py`, `tests/test_layers.py`, `tests/test_baseline.py`, `tests/test_collector.py`, `tests/test_store.py`, `tests/test_settings.py`, `tests/test_analysis.py`, `tests/test_models.py`, `tests/test_units.py`, `tests/test_config.py`, `tests/test_histogram.py`, `tests/test_psutil_provider.py`, `tests/test_sampler.py`, `tests/test_attribution.py`, `tests/test_files.py`, `tests/test_raw.py`, `tests/test_rollup.py`, `tests/test_query.py`, `tests/test_growth.py`, `tests/test_privacy.py`, `tests/test_cli.py`
- P0-W2-T2: `scripts/probes/job_object.py`, `tests/test_probe_job_object.py`
- P0-W2-T3: `src/submeter/cli.py`, `src/submeter/cli/__init__.py`, `src/submeter/cli/_common.py`, `src/submeter/cli/doctor.py`, `src/submeter/cli/top.py`, `src/submeter/cli/config.py`, `src/submeter/cli/store.py`, `tests/test_cli_registry.py`
- P0-W2-T4: `scripts/probes/linux_cgroup_cost.py`, `scripts/probes/linux_pss_cost.py`, `tests/test_probe_linux_costs.py`, `.github/workflows/ci.yml`

**P0-W3**

- P0-W3-T1: `src/submeter/core/models.py`, `tests/builders.py`, `tests/test_models.py`, `src/submeter/core/config.py`, `src/submeter/store/files.py`, `src/submeter/store/query.py`, `src/submeter/store/rollup.py`, `src/submeter/analysis/growth.py`, `tests/test_config.py`, `tests/test_files.py`, `tests/test_query.py`
- P0-W3-T2: `src/submeter/cli/_common.py`, `src/submeter/cli/top.py`, `src/submeter/cli/config.py`, `tests/test_cli_files.py`
- P0-W3-T3: `tests/test_fixed_rules.py`

**P0-W4**

- P0-W4-T1: `src/submeter/core/models.py`, `tests/builders.py`, `tests/test_models.py`, `src/submeter/providers/psutil_provider.py`, `src/submeter/collector/sampler.py`, `src/submeter/store/raw.py`, `src/submeter/store/files.py`, `src/submeter/attribution/rules.py`, `tests/test_psutil_provider.py`, `tests/test_sampler.py`, `tests/test_raw.py`, `tests/test_files.py`, `tests/test_attribution.py`, `scripts/platform_check.py`, `tests/test_platform_check.py`
- P0-W4-T2: `src/submeter/core/config.py`, `tests/test_config.py`, `docs/08-configuration.md`, `examples/submeter.toml`

**P0-W5**

- P0-W5-T1: `src/submeter/core/models.py`, `tests/builders.py`, `tests/test_models.py`, `src/submeter/attribution/rules.py`, `src/submeter/store/raw.py`, `src/submeter/store/rollup.py`, `src/submeter/cli/top.py`, `tests/test_attribution.py`, `tests/test_raw.py`, `tests/test_rollup.py`, `tests/test_cli_top.py`, `scripts/platform_check.py`
- P0-W5-T2: `scripts/probes/autostart.py`, `scripts/probes/autostart_task.xml`, `tests/test_probe_autostart.py`

**P0-W6**

- P0-W6-T1: `scripts/mutation_check.py`, `tests/test_sampler.py`, `tests/test_attribution.py`, `tests/test_raw.py`, `tests/test_rollup.py`, `tests/test_psutil_provider.py`, `tests/test_config.py`, `tests/test_query.py`, `tests/test_examples.py`
- P0-W6-T2: `scripts/probes/bulk_snapshot.py`, `tests/test_probe_bulk.py`
- P0-O2 (owner task, at the gate commit G0, from the integration of this wave to the P0 gate): `docs/review/ground-windows/probes/`

**P1-W1**

- P1-W1-T1: `src/submeter/cli/_envelope.py`, `src/submeter/cli/_format.py`, `src/submeter/cli/doctor.py`, `src/submeter/cli/top.py`, `src/submeter/cli/store.py`, `src/submeter/cli/config.py`, `tests/test_cli.py`, `tests/test_cli_envelope.py`, `tests/test_cli_top.py`, `docs/03-cli-output.md`
- P1-W1-T2: `src/submeter/core/models.py`, `tests/builders.py`, `tests/test_models.py`, `src/submeter/store/runs.py`, `src/submeter/store/files.py`, `tests/test_runs.py`, `tests/test_files.py`, `docs/06-storage.md`
- P1-W1-T3: `tests/tools/__init__.py`, `tests/tools/loadgen/`, `tests/test_loadgen.py`
- P1-W1-T4: `src/submeter/providers/windows/__init__.py`, `src/submeter/providers/windows/job.py`, `tests/test_job.py`

**P1-W2**

- P1-W2-T1: `src/submeter/programs/__init__.py`, `src/submeter/programs/launcher/__init__.py`, `src/submeter/programs/launcher/__main__.py`, `src/submeter/programs/launcher/holder.py`, `tests/test_launcher.py`
- P1-W2-T2: `src/submeter/cli/run.py`, `tests/test_cli_run.py`
- P1-W2-T3: `src/submeter/cli/cost.py`, `tests/test_cli_cost.py`
- P1-W2-T4: `src/submeter/cli/doctor.py`, `tests/test_cli_doctor.py`

**P1-W3**

- P1-W3-T1: `tests/test_gate_p1.py`, `tests/data/page.html`
- P1-O1 (owner task, from the integration of this wave to the P1 gate): `docs/gates/P1/owner/`

**P2-W1**

- P2-W1-T1: `src/submeter/core/models.py`, `tests/builders.py`, `tests/test_models.py`, `src/submeter/providers/base.py`, `src/submeter/providers/psutil_provider.py`, `src/submeter/core/limits.py`, `src/submeter/core/config.py`, `tests/test_providers_base.py`, `tests/test_config.py`, `examples/submeter.toml`
- P2-W1-T2: `src/submeter/collector/sampler.py`, `src/submeter/store/raw.py`, `src/submeter/store/rollup.py`, `src/submeter/attribution/rules.py`, `src/submeter/cli/top.py`, `tests/test_sampler.py`, `tests/test_raw.py`, `tests/test_rollup.py`, `tests/test_attribution.py`, `tests/test_cli_top.py`, `scripts/platform_check.py`, `scripts/probes/bulk_snapshot.py`, `tests/test_probe_bulk.py`
- P2-W1-T3: `src/submeter/privacy/anonymise.py`, `tests/test_anonymise.py`, `tests/test_fixtures_anonymised.py`

**P2-W2**

- P2-W2-T1: `src/submeter/providers/windows/bulk.py`, `tests/test_bulk.py`, `tests/fixtures/bulk/`
- P2-W2-T2: `src/submeter/providers/psutil_provider.py`, `tests/test_psutil_provider.py`
- P2-W2-T3: `src/submeter/providers/windows/system.py`, `tests/test_system.py`, `tests/fixtures/system/`
- P2-W2-T4: `src/submeter/attribution/rules.py`, `src/submeter/attribution/reconcile.py`, `tests/test_attribution.py`, `tests/test_reconcile.py`

**P2-W3**

- P2-W3-T1: `src/submeter/store/raw.py`, `src/submeter/store/files.py`, `tests/test_raw.py`, `tests/test_files.py`, `docs/06-storage.md`
- P2-W3-T2: `src/submeter/collector/cadence.py`, `src/submeter/collector/guard.py`, `tests/test_cadence.py`, `tests/test_guard.py`
- P2-W3-T3: `src/submeter/collector/sampler.py`, `tests/test_sampler.py`
- P2-W3-T4: `src/submeter/providers/windows/cmdline.py`, `src/submeter/providers/windows/bulk.py`, `tests/test_cmdline.py`, `tests/test_bulk.py`

**P2-W4**

- P2-W4-T1: `src/submeter/store/control.py`, `src/submeter/store/logs.py`, `src/submeter/store/files.py`, `tests/test_control.py`, `tests/test_logs.py`, `tests/test_files.py`
- P2-W4-T2: `src/submeter/providers/psutil_provider.py`, `src/submeter/attribution/reconcile.py`, `tests/test_psutil_provider.py`, `tests/test_reconcile.py`
- P2-W4-T3: `tests/tools/record_fixture.py`, `tests/test_record_fixture.py`
- P2-W4-T4: `src/submeter/collector/sampler.py`, `tests/test_sampler.py`
- P2-O1 (owner task, from the integration of this wave to the P2 gate): `tests/fixtures/recorded/`, `docs/gates/P2/owner/anonymised-P2-O1.txt`

**P2-W5**

- P2-W5-T1: `src/submeter/programs/collector/__init__.py`, `src/submeter/programs/collector/__main__.py`, `src/submeter/programs/collector/loop.py`, `pyproject.toml`, `uv.lock`, `tests/test_collector_program.py`
- P2-W5-T2: `src/submeter/cli/top.py`, `tests/test_cli_top.py`
- P2-W5-T3: `src/submeter/cli/doctor.py`, `tests/test_cli_doctor.py`
- P2-W5-T4: `tests/tools/soak/`, `tests/test_soak_tools.py`

**P2-W6**

- P2-W6-T1: `tests/test_kill.py`
- P2-W6-T2: `.github/workflows/soak.yml`, `tests/tools/soak_schedule.py`, `tests/test_soak_workflow.py`, `docs/06-storage.md`, `docs/05-data-flow.md`
- P2-W6-T3: `tests/test_gate_p2.py`
- P2-W6-T4: `tests/test_recorded_fixtures.py`
- P2-O2 (owner task, at the gate commit G2, from the integration of this wave to the P2 gate): `docs/gates/P2/owner/`, except `anonymised-P2-O1.txt`, which P2-O1 has committed before P2-O2 starts

**P3-W1**

- P3-W1-T1: `src/submeter/core/models.py`, `tests/builders.py`, `tests/test_models.py`, `docs/06-storage.md`, `src/submeter/store/history.py`, `tests/test_history.py`
- P3-W1-T2: `tests/tools/synthetic/__init__.py`, `tests/tools/synthetic/raw.py`, `tests/test_synthetic_raw.py`
- P3-W1-T3: `src/submeter/providers/windows/job.py`, `tests/test_job.py`
- P3-W1-T4: `src/submeter/store/files.py`, `src/submeter/store/raw.py`, `tests/test_files.py`, `tests/test_raw.py`

**P3-W2**

- P3-W2-T1: `src/submeter/store/history.py`, `tests/test_history.py`
- P3-W2-T2: `src/submeter/store/rollup.py`, `tests/test_rollup.py`
- P3-W2-T3: `src/submeter/store/control.py`, `src/submeter/cli/session.py`, `tests/test_control.py`, `tests/test_cli_session.py`
- P3-W2-T4: `src/submeter/programs/collector/loop.py`, `src/submeter/attribution/rules.py`, `tests/test_collector_program.py`, `tests/test_attribution.py`

**P3-W3**

- P3-W3-T1: `src/submeter/programs/server/__init__.py`, `src/submeter/programs/server/__main__.py`, `src/submeter/programs/server/loop.py`, `src/submeter/programs/server/rollups.py`, `src/submeter/programs/server/retention.py`, `src/submeter/programs/server/backups.py`, `src/submeter/programs/server/ingest.py`, `src/submeter/programs/server/epochs.py`, `pyproject.toml`, `uv.lock`, `tests/test_server.py`, `tests/test_one_writer.py`
- P3-W3-T2: `src/submeter/store/query.py`, `tests/test_query.py`
- P3-W3-T3: `tests/tools/synthetic/history.py`, `tests/test_synthetic_history.py`
- P3-W3-T4: `src/submeter/cli/rules.py`, `src/submeter/privacy/redact.py`, `src/submeter/attribution/rules.py`, `tests/test_cli_rules.py`, `tests/test_privacy.py`, `tests/test_attribution.py`

**P3-W4**

- P3-W4-T1: `src/submeter/programs/server/retention.py`, `tests/test_server_retention.py`
- P3-W4-T2: `src/submeter/programs/server/backups.py`, `tests/test_server_backups.py`
- P3-W4-T3: `src/submeter/programs/server/ingest.py`, `tests/test_server_ingest.py`
- P3-W4-T4: `src/submeter/programs/server/epochs.py`, `tests/test_server_epochs.py`

**P3-W5**

- P3-W5-T1: `src/submeter/cli/cost.py`, `tests/test_cli_cost.py`, `docs/03-cli-output.md`
- P3-W5-T2: `src/submeter/cli/store.py`, `tests/test_cli_store.py`
- P3-W5-T3: `src/submeter/cli/daemon.py`, `src/submeter/cli/config.py`, `tests/test_cli_daemon.py`
- P3-W5-T4: `src/submeter/cli/doctor.py`, `tests/test_cli_doctor.py`

**P3-W6**

- P3-W6-T1: `tests/test_gate_p3.py`
- P3-W6-T2: `.github/workflows/soak.yml`, `tests/tools/soak_schedule.py`, `tests/test_soak_workflow.py`
- P3-W6-T3: `src/submeter/cli/doctor.py`, `tests/test_cli_doctor.py`
- P3-O1 (owner task, at the gate commit G3, from the integration of this wave to the P3 gate): `docs/gates/P3/owner/`

**P4-W1**

- P4-W1-T1: `src/submeter/core/models.py`, `tests/builders.py`, `tests/test_models.py`
- P4-W1-T2: `tests/tools/series.py`, `tests/fixtures/detectors/`, `tests/fixtures/verdict/`, `tests/fixtures/alerts/`, `tests/test_fixture_series.py`
- P4-W1-T3: `src/submeter/store/query.py`, `tests/test_query.py`
- P4-W1-T4: `src/submeter/analysis/runaway.py`, `tests/test_runaway.py`

**P4-W2**

- P4-W2-T1: `src/submeter/analysis/growth.py`, `src/submeter/analysis/leak.py`, `tests/test_growth.py`, `tests/test_leak.py`
- P4-W2-T2: `src/submeter/analysis/verdict.py`, `src/submeter/core/config.py`, `docs/07-analysis.md`, `examples/submeter.toml`, `tests/test_verdict.py`, `tests/test_config.py`
- P4-W2-T3: `src/submeter/alerts/__init__.py`, `src/submeter/alerts/evaluate.py`, `tests/test_alerts.py`
- P4-W2-T4: `src/submeter/analysis/diff.py`, `tests/test_diff.py`

**P4-W3**

- P4-W3-T1: `src/submeter/cli/why.py`, `tests/test_cli_why.py`
- P4-W3-T2: `src/submeter/cli/diff.py`, `src/submeter/cli/findings.py`, `tests/test_cli_diff.py`, `tests/test_cli_findings.py`
- P4-W3-T3: `src/submeter/programs/server/analysis.py`, `src/submeter/programs/server/loop.py`, `tests/test_server_analysis.py`

**P4-W4**

- P4-W4-T1: `tests/test_gate_p4.py`, `tests/tools/time_cmd.py`
- P4-W4-T2: `.github/workflows/soak.yml`, `tests/tools/soak_schedule.py`, `tests/test_soak_workflow.py`
- P4-O1 (owner task, at the gate commit G4, from the integration of this wave to the P4 gate): `docs/gates/P4/owner/`

**P5-W1**

- P5-W1-T1: `src/submeter/core/models.py`, `tests/builders.py`, `tests/test_models.py`
- P5-W1-T2: `src/submeter/providers/windows/gpu.py`, `tests/test_gpu_windows.py`, `tests/fixtures/gpu/windows/`
- P5-W1-T3: `src/submeter/providers/linux_gpu.py`, `tests/test_gpu_linux.py`, `tests/fixtures/gpu/linux/`
- P5-W1-T4: `src/submeter/report/assets/`, `tests/test_report_assets.py`
- P5-O1 (owner task, from the integration of this wave to the P5 gate): `tests/fixtures/recorded/gpu/`, `docs/gates/P5/owner/anonymised-P5-O1.txt`

**P5-W2**

- P5-W2-T1: `src/submeter/report/__init__.py`, `src/submeter/report/render.py`, `tests/test_report.py`
- P5-W2-T2: `src/submeter/programs/collector/loop.py`, `tests/test_collector_program.py`
- P5-W2-T3: `src/submeter/cli/export.py`, `tests/test_cli_export.py`
- P5-W2-T4: `src/submeter/cli/doctor.py`, `tests/test_cli_doctor.py`

**P5-W3**

- P5-W3-T1: `src/submeter/cli/report.py`, `tests/test_cli_report.py`
- P5-W3-T2: `.github/workflows/soak.yml`, `tests/tools/soak_schedule.py`, `tests/test_soak_workflow.py`
- P5-W3-T3: `src/submeter/report/render.py`, `src/submeter/report/tables.py`, `tests/test_report.py`

**P5-W4**

- P5-W4-T1: `tests/test_gate_p5.py`
- P5-O2 (owner task, at the gate commit G5, from the integration of this wave to the P5 gate): `docs/gates/P5/owner/`, except `anonymised-P5-O1.txt`, which P5-O1 has committed before P5-O2 starts

Every wave: the lead's record step owns `docs/STATUS.md`, `docs/14-baseline-modules.md` and `docs/PLAN.md`. `AGENTS.md` and `CLAUDE.md` change only with the owner's approval of the exact wording. Each phase's gate step owns `docs/gates/P<n>/` outside the owner's subfolder. For P0 it owns `docs/review/ground-windows/ci/` and `docs/gates/P0/`, which holds only `verdict.md` (section 6.4).

## 5. Dependency graph, waves and width

### 5.1 The dependency graph

Each row is a task and the tasks it needs merged first; together the rows are the graph's edges. "gate Pn" means the owner has approved phase n's gate. A dependency always points to an earlier wave (checked by the generator of this section), so no wave holds two tasks of which one needs the other. The last owner task of a phase runs at the gate commit, so it needs every builder task of its phase.


**P0**

| Task | Depends on | Blocked until decided |
| --- | --- | --- |
| P0-W1-T1 | none | none |
| P0-W1-T2 | none | none |
| P0-W2-T1 | P0-W1-T1 | B9, B10 |
| P0-W2-T2 | none | none |
| P0-W2-T3 | P0-W1-T1 | none |
| P0-W2-T4 | P0-W1-T1 | none |
| P0-W3-T1 | P0-W2-T1 | none |
| P0-W3-T2 | P0-W2-T3 | none |
| P0-W3-T3 | none | none |
| P0-W4-T1 | P0-W3-T1 | none |
| P0-W4-T2 | P0-W3-T1 | B7 |
| P0-W5-T1 | P0-W4-T1, P0-W3-T2 | none |
| P0-W5-T2 | none | none |
| P0-W6-T1 | P0-W5-T1, P0-W4-T2 | none |
| P0-W6-T2 | P0-W5-T1, P0-W4-T1 | none |
| P0-O1 (owner) | P0-W1-T2 | none |
| P0-O2 (owner) | every P0 builder task, among them P0-W2-T2, P0-W5-T2 and P0-W6-T2 (it runs at G0) | B16 |

**P1**

| Task | Depends on | Blocked until decided |
| --- | --- | --- |
| P1-W1-T1 | gate P0 | none |
| P1-W1-T2 | gate P0 | B1 |
| P1-W1-T3 | gate P0 | none |
| P1-W1-T4 | gate P0 | B1 |
| P1-W2-T1 | P1-W1-T2, P1-W1-T4 | B1 |
| P1-W2-T2 | P1-W1-T1 | B9, B13 |
| P1-W2-T3 | P1-W1-T1, P1-W1-T2, P1-W1-T4 | none |
| P1-W2-T4 | P1-W1-T1, P1-W1-T4 | none |
| P1-W3-T1 | P1-W2-T1, P1-W2-T2, P1-W2-T3, P1-W1-T3 | none |
| P1-O1 (owner) | every P1 builder task (it runs at G1) | B16 |

**P2**

| Task | Depends on | Blocked until decided |
| --- | --- | --- |
| P2-W1-T1 | gate P1 | none |
| P2-W1-T2 | gate P1 | none |
| P2-W1-T3 | gate P1 | none |
| P2-W2-T1 | P2-W1-T1, P0-W6-T2 | B2 |
| P2-W2-T2 | P2-W1-T1 | B6 |
| P2-W2-T3 | P2-W1-T1 | B4 |
| P2-W2-T4 | P2-W1-T1, P2-W1-T2 | none |
| P2-W3-T1 | P2-W1-T1, P2-W1-T2 | none |
| P2-W3-T2 | P2-W1-T1 | B11 |
| P2-W3-T3 | P2-W1-T2, P2-W2-T2 | none |
| P2-W3-T4 | P2-W2-T1 | none |
| P2-W4-T1 | P1-W1-T2 | none |
| P2-W4-T2 | P2-W2-T2, P2-W2-T4 | B4, B5 |
| P2-W4-T3 | P2-W1-T3, P2-W2-T1, P2-W2-T2, P2-W2-T3, P2-W2-T4, P2-W3-T3 | none |
| P2-W4-T4 | P2-W3-T3, P2-W3-T1 | B8 |
| P2-W5-T1 | P2-W3-T1, P2-W3-T2, P2-W3-T3, P2-W2-T1, P2-W2-T3, P2-W2-T4, P2-W4-T1, P2-W4-T2, P2-W4-T4 | B2 |
| P2-W5-T2 | P2-W2-T4, P2-W1-T1, P2-W2-T1 | none |
| P2-W5-T3 | P2-W1-T1, P2-W2-T1, P2-W2-T3 | none |
| P2-W5-T4 | P2-W1-T2, P2-W3-T1 | none |
| P2-W6-T1 | P2-W5-T1 | none |
| P2-W6-T2 | P2-W5-T1, P2-W5-T4, P1-W1-T3 | B11 |
| P2-W6-T3 | P2-W5-T1, P1-W1-T3, P2-O1 | none |
| P2-W6-T4 | P2-W4-T3, P2-O1 | none |
| P2-O1 (owner) | P2-W4-T3 | none |
| P2-O2 (owner) | every P2 builder task (it runs at G2) | none |

**P3**

| Task | Depends on | Blocked until decided |
| --- | --- | --- |
| P3-W1-T1 | gate P2 | none |
| P3-W1-T2 | gate P2 | none |
| P3-W1-T3 | gate P2 | none |
| P3-W1-T4 | gate P2 | none |
| P3-W2-T1 | P3-W1-T1 | none |
| P3-W2-T2 | P3-W1-T1 | none |
| P3-W2-T3 | P3-W1-T1 | none |
| P3-W2-T4 | P3-W1-T3, P3-W1-T4 | none |
| P3-W3-T1 | P3-W2-T1, P3-W2-T2, P3-W1-T2, P3-W1-T4, P2-W4-T1 | B19 |
| P3-W3-T2 | P3-W2-T1, P3-W2-T2 | none |
| P3-W3-T3 | P3-W2-T1, P3-W1-T2 | none |
| P3-W3-T4 | P3-W2-T4 | none |
| P3-W4-T1 | P3-W3-T1, P3-W3-T2, P3-W3-T3 | none |
| P3-W4-T2 | P3-W3-T1, P3-W1-T4, P3-W2-T3 | none |
| P3-W4-T3 | P3-W3-T1, P3-W2-T3, P3-W2-T1 | none |
| P3-W4-T4 | P3-W3-T1, P3-W2-T1 | none |
| P3-W5-T1 | P3-W2-T1, P3-W3-T2 | none |
| P3-W5-T2 | P3-W1-T4, P3-W2-T3, P3-W2-T1 | none |
| P3-W5-T3 | P3-W3-T1, P2-W5-T1, P2-W4-T1 | B3, B17 |
| P3-W5-T4 | P3-W1-T4, P3-W2-T1 | none |
| P3-W6-T1 | P3-W4-T1, P3-W4-T3, P3-W5-T1, P3-W2-T4 | none |
| P3-W6-T2 | P3-W3-T1, P3-W4-T1, P3-W4-T2, P3-W5-T2 | none |
| P3-W6-T3 | P3-W5-T3, P3-W5-T4 | none |
| P3-O1 (owner) | every P3 builder task, among them P3-W5-T3 and P3-W6-T1 (it runs at G3) | none |

**P4**

| Task | Depends on | Blocked until decided |
| --- | --- | --- |
| P4-W1-T1 | gate P3 | none |
| P4-W1-T2 | gate P3, P2-O1 | B14 |
| P4-W1-T3 | gate P3 | B20 |
| P4-W1-T4 | gate P3 | B12 |
| P4-W2-T1 | P4-W1-T1, P4-W1-T2 | B14, B20 |
| P4-W2-T2 | P4-W1-T1, P4-W1-T2 | none |
| P4-W2-T3 | P4-W1-T1, P4-W1-T2 | B15 |
| P4-W2-T4 | P4-W1-T1 | none |
| P4-W3-T1 | P4-W2-T2, P3-W3-T2 | none |
| P4-W3-T2 | P4-W2-T4, P3-W2-T1 | none |
| P4-W3-T3 | P4-W2-T1, P4-W2-T3, P4-W1-T3, P4-W1-T4 | none |
| P4-W4-T1 | P4-W3-T1, P4-W3-T2, P4-W3-T3 | none |
| P4-W4-T2 | P4-W3-T3 | none |
| P4-O1 (owner) | every P4 builder task, among them P4-W4-T1 (it runs at G4) | none |

**P5**

| Task | Depends on | Blocked until decided |
| --- | --- | --- |
| P5-W1-T1 | gate P4 | B9 |
| P5-W1-T2 | gate P4 | none |
| P5-W1-T3 | gate P4 | none |
| P5-W1-T4 | gate P4 | none |
| P5-W2-T1 | P5-W1-T1, P5-W1-T4 | B9 |
| P5-W2-T2 | P5-W1-T2, P5-W1-T3 | none |
| P5-W2-T3 | gate P4 | none |
| P5-W2-T4 | P5-W1-T2, P5-W1-T3 | none |
| P5-W3-T1 | P5-W2-T1 | B9 |
| P5-W3-T2 | P5-W2-T2 | none |
| P5-W3-T3 | P5-W2-T1, P5-W1-T1 | B9 |
| P5-W4-T1 | P5-W3-T1, P5-W3-T3, P5-W2-T2, P5-O1 | none |
| P5-O1 (owner) | P5-W1-T2 | none |
| P5-O2 (owner) | every P5 builder task, among them P5-W4-T1 (it runs at G5) | none |

### 5.2 The longest chains

- P0: P0-W1-T1 → P0-W2-T1 → P0-W3-T1 → P0-W4-T1 → P0-W5-T1 → P0-W6-T1 → P0-O2, six waves of which each needs the one before, then the owner's probe session at the gate commit; P0-W5-T1 → P0-W6-T2 → P0-O2 is as long. The gate also waits for P0-O1.
- P1: P1-W1-T4 → P1-W2-T1 → P1-W3-T1 → P1-O1, P1-W1-T2 → P1-W2-T1, and P1-W1-T1 → P1-W2-T2 → P1-W3-T1.
- P2: P2-W1-T2 → P2-W3-T1 → P2-W4-T4 → P2-W5-T1 → P2-W6-T2 → P2-O2, P2-W1-T1 → P2-W2-T2 → P2-W3-T3 → P2-W4-T4 → P2-W5-T1, and P2-W3-T1 → P2-W5-T4 → P2-W6-T2. P2-W4-T4 waits for B8, which has no default, and P2-W4-T2, which P2-W5-T1 also needs, for B4 and B5. P2-O2 is a 24-hour soak, so P2 is the longest phase in elapsed time.
- P3: P3-W1-T1 → P3-W2-T1 → P3-W3-T1 → P3-W4-T3 → P3-W6-T1 → P3-O1, and P3-W5-T3 → P3-W6-T3.
- P4: P4-W1-T2 → P4-W2-T2 → P4-W3-T1 → P4-W4-T1 → P4-O1.
- P5: P5-W1-T4 → P5-W2-T1 → P5-W3-T1 → P5-W4-T1 → P5-O2, and P5-W2-T1 → P5-W3-T3 → P5-W4-T1; P5-W4-T1 also waits for P5-O1's recordings, and P5-O2 is the owner check run, with the final soak if the owner keeps it.
- Across phases, beyond the gates: P2-W2-T1 reuses P0-W6-T2's prototype; P2-W1-T2 changes the calls of P0-W4-T1's `scripts/platform_check.py` and P0-W6-T2's probe; P3-W2-T4 reads live run files with P1-W1-T2's `store.runs` and passes them to P3-W1-T3's provider through P2-W1-T1's `GroupProvider.read`; P2-W4-T1 uses P1-W1-T2's `write_atomic`; P3-W2-T3 uses the control paths P2-W4-T1 adds to `FileMap`, and P3-W3-T1 and P3-W5-T3 use P2-W4-T1's control files and logs; P0-W5-T1, P2-W2-T4, P2-W3-T1, P3-W2-T4 and P5-W2-T2 read the per-process fields that P0-W4-T1's sampler copies into `ProcessSample`; P4-W3-T3 feeds P4-W1-T3's series to the detectors and the alert rules; P3-W5-T3 starts P2-W5-T1's program; P4-W1-T2 uses the counter sets the owner recorded in P2-O1; P4-W1-T4 and P4-W2-T1 use P3-W1-T1's structured `Finding`; P4-W3-T1 uses P3-W3-T2's readers and P3-W1-T2's 5-minute raw file; P5-O1 uses P2-W4-T3's recorder.


### 5.3 Waves and their planned width

| Wave | Tasks | Builders | Owner tasks that may start once this wave is integrated |
| --- | --- | ---: | --- |
| P0-W1 | P0-W1-T1, P0-W1-T2 | 2 | P0-O1 |
| P0-W2 | P0-W2-T1, P0-W2-T2, P0-W2-T3, P0-W2-T4 | 4 | — |
| P0-W3 | P0-W3-T1, P0-W3-T2, P0-W3-T3 | 3 | — |
| P0-W4 | P0-W4-T1, P0-W4-T2 | 2 | — |
| P0-W5 | P0-W5-T1, P0-W5-T2 | 2 | — |
| P0-W6 | P0-W6-T1, P0-W6-T2 | 2 | P0-O2 (at G0) |
| P1-W1 | P1-W1-T1, P1-W1-T2, P1-W1-T3, P1-W1-T4 | 4 | — |
| P1-W2 | P1-W2-T1, P1-W2-T2, P1-W2-T3, P1-W2-T4 | 4 | — |
| P1-W3 | P1-W3-T1 | 1 | P1-O1 (at G1) |
| P2-W1 | P2-W1-T1, P2-W1-T2, P2-W1-T3 | 3 | — |
| P2-W2 | P2-W2-T1, P2-W2-T2, P2-W2-T3, P2-W2-T4 | 4 | — |
| P2-W3 | P2-W3-T1, P2-W3-T2, P2-W3-T3, P2-W3-T4 | 4 | — |
| P2-W4 | P2-W4-T1, P2-W4-T2, P2-W4-T3, P2-W4-T4 | 4 | P2-O1 |
| P2-W5 | P2-W5-T1, P2-W5-T2, P2-W5-T3, P2-W5-T4 | 4 | — |
| P2-W6 | P2-W6-T1, P2-W6-T2, P2-W6-T3, P2-W6-T4 | 4 | P2-O2 (at G2) |
| P3-W1 | P3-W1-T1, P3-W1-T2, P3-W1-T3, P3-W1-T4 | 4 | — |
| P3-W2 | P3-W2-T1, P3-W2-T2, P3-W2-T3, P3-W2-T4 | 4 | — |
| P3-W3 | P3-W3-T1, P3-W3-T2, P3-W3-T3, P3-W3-T4 | 4 | — |
| P3-W4 | P3-W4-T1, P3-W4-T2, P3-W4-T3, P3-W4-T4 | 4 | — |
| P3-W5 | P3-W5-T1, P3-W5-T2, P3-W5-T3, P3-W5-T4 | 4 | — |
| P3-W6 | P3-W6-T1, P3-W6-T2, P3-W6-T3 | 3 | P3-O1 (at G3) |
| P4-W1 | P4-W1-T1, P4-W1-T2, P4-W1-T3, P4-W1-T4 | 4 | — |
| P4-W2 | P4-W2-T1, P4-W2-T2, P4-W2-T3, P4-W2-T4 | 4 | — |
| P4-W3 | P4-W3-T1, P4-W3-T2, P4-W3-T3 | 3 | — |
| P4-W4 | P4-W4-T1, P4-W4-T2 | 2 | P4-O1 (at G4) |
| P5-W1 | P5-W1-T1, P5-W1-T2, P5-W1-T3, P5-W1-T4 | 4 | P5-O1 |
| P5-W2 | P5-W2-T1, P5-W2-T2, P5-W2-T3, P5-W2-T4 | 4 | — |
| P5-W3 | P5-W3-T1, P5-W3-T2, P5-W3-T3 | 3 | — |
| P5-W4 | P5-W4-T1 | 1 | P5-O2 (at G5) |

In all: 6 phases, 29 waves, 95 builder tasks (15 S, 51 M, 29 L) and 9 owner tasks. Per phase: P0 6 waves and 15 tasks; P1 3 waves and 9 tasks; P2 6 waves and 23 tasks; P3 6 waves and 23 tasks; P4 4 waves and 13 tasks; P5 4 waves and 12 tasks.

### 5.4 Width: the pilot, the cap and why

- **Pilot.** P0-W1 has two builders on two small tasks (sizes S and M) that share no file and change nothing under `src/`: CI with the test markers, and the step-1 scripts. P0-W1-T1 changes two shared files, `pyproject.toml` and `uv.lock`, which no other task holds in the wave. The pilot starts only once `main` is on `origin` (section 3.4). It exercises the whole wave loop on work that cannot damage the baseline: separate working copies at the base commit, `uv sync` in each, tests first, review, merge in task order, the seven checks after each merge, and CI on both runners. Neither pilot branch can show its test-only commit failing on CI, because the pilot's base commit holds no workflow file and P0-W1-T2's branch never holds `ci.yml`; so the pilot follows the exception at the end of section 7.2's steps: the reviewer runs both tasks' before and after checks in its own worktree, P0-W1-T1's last commit runs on both runners before merge, and P0-W1-T2 is confirmed on CI-W and CI-L by the CI run of the P0-W1 integration commit, before P0-W2's base commit is fixed.
- **Widening.** After a clean pilot (both tasks merged without conflict, every check that passed at the base commit still passing after each merge and on both runners, each review settled within two rounds) later waves run at their planned width, up to the cap. A check that already fails at the pilot's base commit, as the baseline may on CI-W, where it has never run (`docs/17-build-prompt.md:337`), does not count against the pilot: it becomes a fix task under section 5.5 (K40). If a wave has a merge conflict, a review that needed escalation or a red check after a merge that its own changes caused, the next wave runs at 2 builders. The tasks of a wave share no path and do not depend on one another, so a wave splits into two without any change of ownership.
- **Cap: 4 builders per wave.** (1) Each builder has its own reviewer, so 4 builders means up to 8 agents working at once. (2) The lead merges one branch at a time and runs the seven checks after each merge: 16.8 s per merge with warm caches on the review's Linux machine, 13 s of it in the two `mypy --platform` runs, which invalidate the shared cache each time; then CI runs on both runners. (3) Four fresh working copies running the four checks at the same moment took 10.7 to 13.1 s each, against 12.0 s for one alone; six took 13.7 to 18.3 s (8 logical cores, Linux, 22 November 2026). (4) None of this was measured on Windows, where antivirus scanning of each working copy's virtual environment (about 101 MB) and of many small files, and the 260-character path limit, are expected to cost more; section 8 lists it as a risk. The cap is reviewed after P1 against the merge times measured there.
- **Blocked tasks.** A task blocked by a decision of section 5.6 is held back; its wave runs narrower, and the task moves to the next wave in which no planned task owns its paths.


### 5.5 Work that cannot be planned yet

Some tasks cannot be written until something is seen: what fails when the baseline first runs on CI-W (`docs/17-build-prompt.md:337` asks for that list), what fails in the owner's step 1 (P0-O1), findings of a review, and change requests (4.3). For each, the lead writes a task card with a size and an Owns line and places it in the next wave whose planned tasks do not own its paths, or in a wave of its own, and records it in `docs/STATUS.md` with its cause. P0-W3 and P0-W4 are planned at 3 and 2 builders, which leaves room under the cap for the fixes that P0-O1 is expected to bring. The fixes for the baseline's first failures on CI-W run earlier, as a wave of their own before P0-W2 (K40; changed in stage 3, see K40).


### 5.6 Decisions that block tasks

A task blocked by a decision is not dispatched until the decision is recorded in `docs/STATUS.md` (and, for a probe's choice, in the P0.12 decision rows). Where the plan has a default, the task is written for it and the owner may overturn it before the task is dispatched. Section 11 puts each to the owner.

| Id | Decision | Decided by | Default in this plan | Blocks |
| --- | --- | --- | --- | --- |
| B1 | The holder that keeps a tagged group open, and how the run file's final state is written | The owner, on probe 1's output (P0-O2) | `docs/17-build-prompt.md:75-77` as written, if reopening by name behaves as gate P0.8 step d expects and a parent job's totals include a nested job's processes (step h) | P1-W1-T2, P1-W1-T4, P1-W2-T1 |
| B2 | Python or Rust for the collector, and the default intervals | The owner, on probe 2's output and the trigger of `docs/11-language.md:21-24` | Python, 2 s active and 5 s idle, if the bulk provider stays under 3% of a core at 2 s, 1% at 5 s and 83,886,080 private bytes; if the trigger fires the build stops and P2 is planned again | P2-W2-T1, P2-W5-T1 |
| B3 | A scheduled task or the `HKCU\...\Run` key for `daemon install` | Probe 3's result (P0-O2), by the rule of `docs/15-phases-and-decisions.md:19`; if the work PC's word differs, the owner rules at the gate (6.4, P0.12) | the scheduled task, unless a standard user cannot register it | P3-W5-T3 |
| B4 | Whether Windows counts interrupt and DPC time inside system time | Step 1's per-core check (P0-O1), by the rule written in P0-W1-T2; if the work PC's word differs, the owner rules at the gate (6.4, P0.12) | none: the measured ratios decide | P2-W2-T3, P2-W4-T2 |
| B5 | The threshold at which reading every leaf cgroup's `cpu.stat` "breaks the budget" (R60) | The owner, on P0-W2-T4's figure | proposed: R60 stays if one round of reads costs under 0.1% of one core at the 5 s idle interval | P2-W4-T2 |
| B6 | Whether Linux workload memory totals use PSS for every process (R46) | The owner, on P0-W2-T4's figure | proposed: adopted if a full round costs less than 0.1 percentage points of one core more than the 25-largest round at the 30 s USS interval, judged on CPU ms per GB resident | P2-W2-T2 |
| B7 | The eight bounds `docs/08-configuration.md:78-94` marks "not set yet" | The owner | none | P0-W4-T2 |
| B8 | The batch stamp after a backward wall-clock step, and under slow drift between the two clocks (R55). P2-W3-T1's store rule holds under every option (section 3.6) | The owner; the options are in `docs/review/02-rulings.md:282` | none | P2-W4-T4, and through it P2-W5-T1 |
| B9 | How `submeter run` reaches the launcher, and where the report sits in `LAYER`. No ruling covers it: `cli` and `programs` are both layer 3 (`tests/test_layers.py:20-21`), so the CLI may not import the launcher, and a `report` package may neither import `store` at layer 2 nor be imported by `cli` at layer 3 | The owner | (a): the CLI starts the launcher as a child process (`python -m submeter.programs.launcher`), and the report renders records the CLI fills, at layer 2 importing only `core`; neither changes `AGENTS.md:39` or `docs/17-build-prompt.md:49`. The alternative (b), `cli` at a layer 4 above `programs` and `report`, changes both | P0-W2-T1, P1-W2-T2, P5-W1-T1, P5-W2-T1, P5-W3-T1, P5-W3-T3 |
| B10 | The `AGENTS.md` wordings waiting for approval (section 11.6): line 35 naming the per-component test files for running one test, because P0-W2-T1 deletes `tests/test_baseline.py`; line 39 naming `programs`, and the `alerts` and `report` packages P0-W2-T1 adds to `LAYER` at layer 2 (R108; B9 (a)); line 40 letting records live in their own core modules (R112); line 46 "the server writes the history file" (I94) | The owner | `AGENTS.md` unchanged; records stay in `core/models.py` (C7). Approving line 40 lets later phases drop their contract tasks. Line 35's wording blocks P0-W2-T1: it is approved and on `main` at P0-W2's base commit before that task is dispatched (merges inside a wave are automatic, so a hold at merge would not stop it) | P0-W2-T1 (the line-35 wording only); the other wordings block no task |
| B11 | What makes the machine busy or quiet for adaptive cadence; `docs/08-configuration.md:57-59` gives only the durations | The owner | none | P2-W3-T2, P2-W6-T2 |
| B12 | The runaway process count: its definition, threshold, window and finding; `docs/17-build-prompt.md:200` names it and defines none of them | The owner | none | P4-W1-T4 |
| B13 | On Linux, whether `submeter run` sets `SUBMETER_RUN` and writes a run file | The owner | neither; `cost --run` on Linux says tagged runs are unavailable | P1-W2-T2 |
| B14 | The leak gate's statistics: noise per raw row or per 1-minute step, the row interval, seeds, pass rates and the staircase's deadline | The owner | proposed: rows every 30 s, uniform ±40 MiB per row, 200 seeds; at least 190 of 200 leaks flagged by 2 h 5 min; 0 of 200 warm-ups flagged over 6 h; at least 190 of 200 staircases flagged by 6 h | P4-W1-T2, P4-W2-T1 |
| B15 | What acts on `attribution.unattributed_alert`; `docs/08-configuration.md:99` names no consumer | The owner | nothing acts on it until decided | P4-W2-T3 |
| B16 | Whether node.exe and bash.exe are on the owner's machine, and whether they may be installed | The owner | probe 1 and the P1 gate skip those steps and say so | P0-O2, P1-O1 |
| B17 | `daemon start` on Linux in version 1 | The owner | starts both entry points as detached processes; `install` and `uninstall` say they are unavailable on Linux (the systemd unit is after version 1) | P3-W5-T3 |
| B18 | The Windows source of the adapter's VRAM total | The builder of P5-W1-T2 from current documentation; the owner if no source works without administrator rights | stop and ask; the floor allows a GPU-bound rule-out rewritten so that it does not need VRAM (`docs/15-phases-and-decisions.md:77`) | no task at dispatch: P5-W1-T2's builder is the one who looks, so the task is dispatched, and only if it finds no source is it held (section 10.3, item 12) until the owner rules |
| B19 | What the server does when `history.db` fails its integrity check at start | The owner | refuses to start and logs it; `doctor` and `store check` report it; no repair | P3-W3-T1 |
| B20 | Whether growth is tracked for each process as well as for each workload (R116, I38). `docs/07-analysis.md:29` and `docs/17-build-prompt.md:198` say both, and no ruling says how | The owner | (a), as the brief says: P4-W1-T3 also reads 1-minute series per process from raw process rows and P4-W2-T1 checks each. (b) tracks growth per workload only and deletes "for each process" from both lines | P4-W1-T3, P4-W2-T1 |

### 5.7 Choices this plan made that the owner may overturn

No ruling covers these. Each is the plan's choice so that no builder has to guess; each is listed for section 11.

| Id | Choice | Why | Tasks it shapes |
| --- | --- | --- | --- |
| C1 | `top` keeps taking its own two snapshots and does not read the collector's raw file | it works without the collector, as the baseline does; `docs/17-build-prompt.md:339` says only "the full `top`" | P2-W5-T2 |
| C2 | `daemon install` registers one scheduled task per program | each program then restarts on failure on its own; the brief does not say one task or two | P3-W5-T3 |
| C3 | Probes in `scripts/probes/`; test tools in the package `tests/tools/` | probes run like `scripts/platform_check.py`; tools under `tests/` are type-checked by the AGENTS.md mypy commands and not shipped in the wheel | P0 probes; P1-W1-T3, P2-W5-T4, P2-W4-T3, P2-W6-T2, P3-W1-T2, P3-W3-T3, P4-W1-T2, P4-W4-T1 |
| C4 | `SampleBatch` keeps its machine-total busy figure beside the new per-core figures | R112 asked for per-core in place of the float; keeping the total leaves `sampler.py` and `raw.py` out of the record task | P0-W3-T1 |
| C5 | `boot_id` travels on the `Snapshot` and in the raw file's `meta` table, and a different `boot_id` starts the same-day second file | the brief does not say where `boot_id` is kept; this is the smallest change | P0-W4-T1, P2-W3-T1 |
| C6 | `docs/14-baseline-modules.md` and `docs/STATUS.md` are updated by the lead's record step from the builders' reports | almost every task makes a docs/14 entry stale; one writer per wave avoids a file every task would share | every wave |
| C7 | Records passed between layers stay in `core/models.py`, held in each phase by one task | `AGENTS.md:40` as it stands; it changes with B10 | P0-W3-T1, P0-W4-T1, P0-W5-T1, P1-W1-T2, P2-W1-T1, P3-W1-T1, P4-W1-T1, P5-W1-T1 |
| C8 | CLI commands register by discovery: each module of `submeter.cli` whose name does not start with an underscore exposes `register(app)` | later command tasks add a module and edit no shared file | P0-W2-T3 and every command task |
| C9 | P0 carries R112, R145, R57 with R56, R111, R42 with R46, and R110, besides the probes and CI | they repair the baseline the probes drive and every later phase builds on, and `docs/review/fixes/R61.md` puts R42 before P1 | P0-W2 to P0-W6 |
| C10 | Gate evidence for P1 to P5 under `docs/gates/P<n>/`, the owner's runs under `docs/gates/P<n>/owner/` | `docs/15-phases-and-decisions.md:23` names a folder for P0 only | owner tasks; section 6 |

## 6. The gates

Each phase ends at a gate (`docs/15-phases-and-decisions.md:5`). At a gate the build stops, the evidence below is collected at one commit, a reviewer who did none of the phase's work compares it with the numbers below, and the owner approves or rules (`docs/17-build-prompt.md:335`; principle 6, `prompts/01-execution-prompt.md:104`). No task of the next phase is dispatched until the owner's approval is recorded. Items are numbered `P<phase>.<n>`; S1 to S5 are the criteria every gate shares (6.3). Sizes in bytes are binary (`docs/08-configuration.md:115`): 150 MB is 157,286,400 bytes, 80 MB is 83,886,080 bytes, 10 MB is 10,485,760 bytes and 75 MiB an hour is 78,643,200 bytes an hour. CI-W, CI-L and Owner are as in section 1.2. Every number that no document or ruling gives is this plan's own and is listed in 6.12 for the owner.

### 6.1 Who does what at a gate

| Role | At a gate it | It is never |
| --- | --- | --- |
| Lead | fixes the gate commit, starts the CI runs, dispatches the test runner and the gate reviewer, merges the evidence, writes the phase's entry in `docs/STATUS.md`, copies the reviewer's verdict into `verdict.md` word for word, and puts it to the owner | the judge of any item |
| Test runner | runs the procedure of 6.2 at the gate commit in a fresh working copy, collects the CI runs, saves every output in the evidence folder and pushes it | an agent that built or reviewed a task of the phase |
| Gate reviewer | starts with fresh context and tools that cannot write; reads the evidence at the commit that holds it and compares each item with its number; returns one verdict line per item | the test runner, or an agent that built or reviewed a task of the phase |
| Failure investigator | for an item that failed or could not be judged: starts with fresh context and tools that cannot write, finds the cause and names the task and the files that hold it | the agent that fixes it |
| Plan reviewer | checks the decision rows of P0.12 against their evidence, and at P5 the plan's self-check of section 9.10 (row D17), run again on the plan as it then stands | the writer of the plan change it checks |
| Owner | runs the owner tasks as the signed-in standard user on the personal Windows 11 PC, whose output is the evidence, and runs P0's owner tasks and each later gate's owner check run again on the work PC, whose results the owner tells the lead in one word each (section 3.1, Owner tasks); rules where this section says the owner rules, and approves every gate | a source of any file, figure or copied text from the work PC |

If a build session runs on the owner's personal Windows PC without elevation and the owner allows it, a test runner there may type the owner tasks' commands (section 11 asks this). No build session or test runner runs on the work PC, because nothing is committed or pushed from it; the owner's own use of Claude Code's shell there to run probe 1 by hand (P0-O2) is not a build session. The steps that need the owner in person (a sleep, signing out and in, a restart) stay with the owner, and only the owner approves.

### 6.2 The procedure every gate follows

**Entry.** Every builder task of the phase is merged on `main` and recorded in `docs/STATUS.md`; every owner task of the phase has committed its evidence from the personal PC, with the work PC's words recorded where the task runs there (section 3.1, Owner tasks), or is the phase's last owner task, which runs at the gate commit (step 4); every decision of section 5.6 that blocks a task of the phase is recorded; every change request against the phase (4.3) is merged or moved to a later phase with the owner's agreement.

**Step 1. The gate commit (lead).**

```bash
git switch main && git pull --ff-only
n=2; G=$(git rev-parse HEAD)               # n is the phase
git push origin "$G:refs/heads/gate/P$n"
```

The lead records G in `docs/STATUS.md`. The push starts `ci.yml`, which runs on every branch (P0-W1-T1), and from P2 `soak.yml`, which runs on branches named `gate/*` (P2-W6-T2), each on both runners at G.

**Step 2. Checks and harness (test runner).** In a new working copy at G, on the system the build session runs on:

```bash
n=2; G=<the gate commit>; os=linux          # os is linux or windows
git fetch origin
git worktree add -b "evidence/P$n" "../gate-P$n" "$G" && cd "../gate-P$n"
d="docs/gates/P$n"; mkdir -p "$d/checks-$os" "$d/harness-$os" "$d/ci"
run() { f="$d/checks-$os/$1.txt"; shift; { echo "\$ $*"; "$@"; echo "exit=$?"; } > "$f" 2>&1; }
CI_MARKS="not owner_machine and not session and not hardware and not soak"
run 1-sync        uv sync --locked
run 2-ruff-check  uv run ruff check
run 3-ruff-format uv run ruff format --check
run 4-mypy        uv run mypy src tests
run 5-mypy-win32  uv run mypy --platform win32 src tests
run 6-mypy-linux  uv run mypy --platform linux src tests
run 7-pytest      uv run pytest -m "$CI_MARKS" -rsxX
uv run submeter --help > "$d/checks-$os/s4-help.txt" 2>&1          # from P1, for S4
export SUBMETER_GATE_DIR="$PWD/$d/harness-$os"
run 8-harness     uv run pytest "tests/test_gate_p$n.py" -m "not owner_machine and not session and not hardware" -rsxX
unset SUBMETER_GATE_DIR
```

Step 8 includes the `soak` mark, so the gate runs the long harness cases that CI's main job leaves to the soak workflow. P0 has no harness; 6.4 gives its steps and its folder. On Windows the same commands run in PowerShell in the form of step 4.

**Step 3. The CI runs (test runner).** Once every run started by step 1 has finished:

```bash
ids=$(gh run list --commit "$G" --json databaseId --jq '.[].databaseId')
for id in $ids; do gh run watch "$id" --exit-status > /dev/null; done
gh run list --commit "$G" --json databaseId,workflowName,headBranch,event,conclusion,url > "$d/ci/runs.json"
for id in $ids; do
  gh run view "$id" --json jobs --jq '.jobs[] | [.name, .conclusion] | @tsv' > "$d/ci/jobs-$id.tsv"
  gh run view "$id" --log > "$d/ci/run-$id.log"
  gh run download "$id" --dir "$d/ci/run-$id"
done
uv run python scripts/probes/replace_names.py "$d"   # the build machine's names (P0-W1-T2)
git add "$d" && git commit -m "Gate P$n: test runner's evidence at $G" && git push origin "evidence/P$n"
```

GitHub deletes workflow logs and artefacts after a retention period (90 days by default), so the copies in the repository are the evidence, not the Actions pages. The evidence branch is named `evidence/P<n>` so that its push does not start the 30-minute soak again.

**Step 4. The owner check run (owner).** The phase's last owner task begins with this, at G (P4-O1 runs it second, after the cold start of P4.5; section 6.8), in PowerShell started normally (not "Run as administrator"), from a clone checked out at G. Windows PowerShell 5.1 writes UTF-16 with a bare `>`, so every output goes through `Out-File -Encoding utf8`.

```powershell
$n = 2; $d = "docs\gates\P$n\owner\checks"
New-Item -ItemType Directory -Force $d | Out-Null
function Save($name, [scriptblock]$cmd) {
  & $cmd 2>&1 | Out-File -Encoding utf8 "$d\$name.txt"
  "exit=$LASTEXITCODE" | Out-File -Append -Encoding utf8 "$d\$name.txt"
}
Save 0-commit      { git rev-parse HEAD; git status --short }
Save 0-integrity   { whoami /groups | Select-String "Mandatory Level" }
Save 1-sync        { uv sync --locked }
Save 2-ruff-check  { uv run ruff check }
Save 3-ruff-format { uv run ruff format --check }
Save 4-mypy        { uv run mypy src tests }
Save 5-mypy-win32  { uv run mypy --platform win32 src tests }
Save 6-mypy-linux  { uv run mypy --platform linux src tests }
Save 7-pytest      { uv run pytest -m "not owner_machine and not session and not hardware and not soak" -rsxX }
Save 8-marked      { uv run pytest -m "owner_machine or session or hardware" -rsxX }
```

`0-integrity.txt` must read `Medium Mandatory Level`; `High Mandatory Level` means the shell is elevated and the run does not count. Step `8-marked` runs every test that only this machine can prove, wherever its task put it (for example the `hardware` cases of P2-W2-T3). For P0 the folder is `docs\review\ground-windows\probes\checks`. The owner task then runs its own items (6.4 to 6.9), shows its summary screen and, on the personal Windows 11 PC only, commits. Every owner task, not only the last, commits its folder this way from the personal PC, on a branch named after the task:

```powershell
$task = "P2-O2"; $f = "docs/gates/P2/owner"      # the owner task's id and its folder
git switch -c "owner/$task"
uv run python scripts/probes/replace_names.py $f      # P0-W1-T2
$env:SUBMETER_SCAN_EVIDENCE = "1"; uv run pytest tests/test_fixtures_anonymised.py -rsxX   # from P2 (P2-W1-T3)
git add $f
git grep --cached -n -i -F -e $env:USERNAME -e $env:COMPUTERNAME -- $f
git commit -m "${task}: owner's evidence"; git push origin "owner/$task"
```

The `git grep` must print nothing; a line it prints is changed to `<user>` or `<host>` and the grep repeated before the commit. No raw file, history file or log from the owner's machine is committed: they hold the names of the owner's other programs.

On the work PC, at the same commit and in a PowerShell started normally, the owner runs P0-O1 and P0-O2 in full and, from P1 on, only this step 4 check run (the rest of the phase's owner tasks run on the personal PC only; section 3.1), and stops at the summary screen, which for the check run is the `exit=` line of each saved check: there is no `git switch -c`, no commit and no push, and no file, figure or copied text from that machine enters the repository (`docs/STATUS.md` 7.10). The owner reads the summary screen and tells the lead each item's outcome in one word: pass or fail, or the named choice (B4: subtract, keep or ask; B3: scheduled task or Run key; probe 2's trigger: fired or not). The lead records each word as the owner's statement, with the date, in the phase's gate section of `docs/STATUS.md` (section 5 for P0), in a table headed "Work PC results by word", one row per item; the gate reviewer reads it there. A figure with no pass mark is not asked for from the work PC. Stop rules 4 and 5 of 10.3 (a request to elevate, a block by security software or policy on the work computer) apply to this run as written. An owner run made at an earlier commit C still counts at G when `git diff --quiet C G -- . ':!docs/gates' ':!docs/review' ':!docs/tasks' ':!docs/STATUS.md' ':!docs/PLAN.md' ':!docs/14-baseline-modules.md'` exits 0, that is, when nothing changed between C and G except the evidence and the lead's records, with C read from `0-commit.txt` or the owner task's own `commit.txt`; otherwise the owner runs the affected items again. The rule covers all of `tests/`, `scripts/` and `examples/`, because `7-pytest` and `8-marked` run every test, and the brief's own files, because some tests read them (P3-W1-T1's test parses the history DDL in `docs/06-storage.md`).

**Step 5. Merge the evidence (lead).**

```bash
git switch main && git pull --ff-only
git merge --no-ff "origin/evidence/P$n" -m "Gate P$n: test runner's evidence"
last=P2-O2                              # the phase's last owner task: P0-O2, P1-O1, P2-O2, P3-O1, P4-O1 or P5-O2
git merge --no-ff "origin/owner/$last" -m "$last: owner's evidence"
git diff --name-only "$G" HEAD          # only paths under docs/gates/P$n/ (for P0 also docs/review/ground-windows/)
```

Evidence of the phase's earlier owner tasks was merged the same way when each finished, with the same check that it touches only that task's folder. Any other path is a planning defect, handled as 4.1 rule 7 says. Every `owner/` branch merged here was pushed from the personal PC; the work PC's results are not merged, because they exist only as the owner's words recorded under step 4. The lead then writes the phase's entry in `docs/STATUS.md` from the evidence and those recorded words (S3), runs the seven checks, commits and pushes. This commit is E, the commit the reviewer reads.

**Step 6. Review (gate reviewer).** The reviewer is given this section, the phase's tasks in section 3, and the repository at E. It returns, for each item of the gate and for S1 to S5: the result (pass, fail, not run, or needs a ruling), the measured value with its unit, the limit, the evidence file, and one line of reason; for an item the work PC also runs, its word from the table "Work PC results by word" in `docs/STATUS.md`, or "not recorded". It also confirms that every evidence file it relies on is for G (by `runs.json`, `0-commit.txt` or the harness files) or passes step 4's rule; that, from P1, the builder of `tests/test_gate_p<n>.py` built none of the tasks whose output it tests (`docs/STATUS.md` names the builder of each task); and that every reference value in a harness comes from the load generator, a burner, plain SQL or a recorded fixture, never from the code under test (P1.1, P2.2, P3.1).

**Step 7. Record and ask (lead).** The lead writes `docs/gates/P<n>/verdict.md`: G, E, the date, the reviewer's reply word for word, and the rulings the owner is asked for, then commits, pushes and puts the gate to the owner with the paths of the evidence. The owner's answer is copied word for word, with the date, into `verdict.md` and `docs/STATUS.md`; the lead commits it, tags it `gate-P<n>` and pushes the tag. That commit is the base commit of the next phase's first wave.

**Evidence layout** (P1 to P5; P0 is in 6.4).

```
docs/gates/P<n>/
  checks-<os>/        step 2: the seven checks, s4-help.txt and 8-harness.txt on the test runner's system
  harness-<os>/       step 2: what the harness wrote to SUBMETER_GATE_DIR
  ci/                 step 3: runs.json, jobs-<id>.tsv, run-<id>.log, run-<id>/ (artefacts gate-windows,
                      gate-linux, soak-windows, soak-linux, soak-tests-windows, soak-tests-linux)
  owner/              the phase's owner tasks; owner/checks/ is step 4
  verdict.md          step 7
```

Every text file is UTF-8. A file holding a command's output starts with `$ <command>` and ends with `exit=<code>`, as `docs/review/ground/` does. Raw and history files are never committed as evidence; a harness or a checker reports what it read from them.

**The harness contract.** Each gate harness `tests/test_gate_p<n>.py` has one test function per gate item, named `test_p<n>_<k>_<words>`, so that one item runs with `-k "test_p<n>_<k>_"` (the trailing underscore keeps `p1_1_` from matching `p1_10`). A case that only the owner's machine can prove is marked `owner_machine`; a case longer than about a minute is marked `soak`. When `SUBMETER_GATE_DIR` is set, each test writes `P<n>.<k>.json` there: the item, the criterion, each measured value with its unit, the limit, the result, the system (`sys.platform` and the Windows build or kernel release) and the machine's process count, plus the inputs it compared as `P<n>.<k>-<name>.json` (a generator report, a run file, a command's output). CI sets `SUBMETER_GATE_DIR` and uploads the folder as the artefact `gate-windows` or `gate-linux`; the soak workflow's `soak` job uploads `soak-windows` and `soak-linux`, and its `soak-tests` job, which runs the `soak` cases, uploads its `SUBMETER_GATE_DIR` as `soak-tests-windows` and `soak-tests-linux`.

### 6.3 Criteria every gate shares

| Id | From | Criterion | How it is checked | Where | Evidence |
| --- | --- | --- | --- | --- | --- |
| S1 | P0 | The seven commands of `AGENTS.md:25-33` exit 0 at G, pytest with the CI selection of marks. `tests/test_fixed_rules.py` (P0-W3-T3, fixed rules 1 to 3) carries no mark and appears in no `SKIPPED` line | `exit=0` in the files `1-sync` to `8-harness` of step 2 and `1-sync` to `8-marked` of step 4, with one exception: `8-marked.txt` may end `exit=5`, pytest's code for no test collected, when its summary line reports only deselected tests, as at P0, where no test carries the marks `owner_machine`, `session` or `hardware` (on the baseline, `uv run pytest -m "owner_machine or session or hardware"` printed `62 deselected` and exited 5, checked for this plan on 22 November 2026). Other files that steps 2 and 3 save, such as P1.12's grep, are read by their own item; `conclusion` `success` for every job in `jobs-<id>.tsv` of `ci.yml` | CI-W, CI-L, the test runner's system, Owner | `checks-<os>/`, `ci/`, `owner/checks/` |
| S2 | P0 | The `-rsxX` summaries show 0 xfailed and 0 xpassed (the last strict expected failure, R61's, is removed by P0-W5-T1). Each `SKIPPED` line's reason names another operating system, an absent program this section names (node, bash, a Chromium-based browser, a GPU source), a missing condition of a `hardware` test (no battery) or an owner ruling recorded in `docs/STATUS.md`. A skip that is new since the previous gate is listed in `docs/STATUS.md` with its reason | read `7-pytest.txt`, `8-harness.txt`, `8-marked.txt` and the pytest part of each CI log | as S1 | as S1 |
| S3 | P0 | `docs/STATUS.md` at E says, for the phase: what works; what was verified, how and where, each with its evidence path; what could not be verified; the open change requests and rulings. At P5 it also names each provider that never ran on real hardware (`docs/17-build-prompt.md:342`) | the reviewer reads it and opens every path it names | — | `docs/STATUS.md` at E |
| S4 | P1 | Every command that `submeter --help` lists, and every subcommand, has a snapshot test asserting the `schema` key its `--json` output prints, with the name P1-W1-T1 wrote into `docs/03-cli-output.md` (`docs/03-cli-output.md:86`): 0 commands without one | compare `s4-help.txt` with the snapshot tests under `tests/` | CI-W, CI-L | `checks-<os>/s4-help.txt`, `7-pytest.txt` |
| S5 | P2 | `uv run pytest tests/test_fixtures_anonymised.py -rsxX` with `SUBMETER_SCAN_EVIDENCE=1` passes on the machine that recorded each fixture, run there before the fixture's commit: 0 files under `tests/fixtures/` holding that machine's user or host name (`AGENTS.md:44`), nor under `docs/review/ground-windows/` and `docs/gates/` outside their `ci/` copies (P2-W1-T3). In CI the same test runs without that variable and scans `tests/fixtures/` only, which proves less, because CI's user is the runner's, and `runner` is an ordinary word in the evidence the lead writes | the commit that adds the recorded fixtures also adds the output, saved as in step 4 | Owner (P2-O1, P5-O1), CI | `owner/anonymised-P2-O1.txt`, `owner/anonymised-P5-O1.txt` |

The fixed rules have no item of their own in `docs/15-phases-and-decisions.md`. This plan checks them at every gate through S1 (`tests/test_fixed_rules.py`), at P1 through P1.12, in every soak (0 sockets; on the owner's machine, no elevated token: P2.1, P2.6, P3.5, P4.6, P5.4, P5.5) and through the canary checks P1.10, P2.7 and P5.1.

### 6.4 Gate P0: decision probes and CI

The gate as written: the baseline passes its checks on both runners, the output of step 1 and of each probe is saved, each probe's choice is recorded, and the brief is in the repository (`docs/15-phases-and-decisions.md:27`). Evidence for P0 is saved under `docs/review/ground-windows/` (`docs/15-phases-and-decisions.md:23`): `step1/` (P0-O1), `probes/` (P0-O2, which runs at G0 and starts with the owner check run, saved in `probes/checks/`) and `ci/` (the gate step, in place of `docs/gates/P0/` in steps 2 and 3). The verdict is `docs/gates/P0/verdict.md`.

| Item | Pass criterion | Where | Evidence (under `docs/review/ground-windows/`) |
| --- | --- | --- | --- |
| P0.1 | Every run of `ci.yml` at G0 concluded `success`, with a Windows job and a Linux job, each running `uv sync --locked` and the six other `AGENTS.md` commands. A list of each change made to pass on CI-W, with its commit (`docs/17-build-prompt.md:337`), written by the lead from `docs/STATUS.md` | CI-W, CI-L | `ci/runs.json`, `ci/jobs-<id>.tsv`, `ci/run-<id>.log`, `ci/windows-fixes.md` |
| P0.2 | (a) Step 1's output is saved, one file per command, at the P0-W1 integration commit (P0-O1). (b) At G0 on the owner's machine: the seven commands exit 0 (`probes/checks/`), `0-integrity.txt` reads Medium Mandatory Level, and `platform_check.py` prints `administrator or root: False` and `<N> results, 0 failed`; or each failure has a fix merged before G0 or an owner ruling in `docs/STATUS.md` | Owner | `step1/`; `probes/checks/`; `probes/platform-check.txt` |
| P0.3 | In the Defender Operational log, after `platform_check.py` (P0-O1) and again after the probes (P0-O2): 0 events with id 1121 or 1122 naming python.exe after the script's start. Any such event stops the build for a ruling (`docs/reference/windows-priorities.md:92`). If a standard user cannot read the log, the error is saved and the owner rules how it is read | Owner | `step1/defender-asr.txt`, `probes/defender-asr.txt` |
| P0.4 | `cpu_time_check.py`, three repetitions of 10 s, prints r1 and r2 for every core. Decision B4 by P0-W1-T2's rule: r1 between 0.99 and 1.01 on every core in every repetition, subtract interrupt and DPC time; r2 between 0.99 and 1.01, keep the busy sum; neither, the owner decides | Owner | `step1/cpu-time-check.txt` |
| P0.5 | Three figures are present: the number of restricted processes from `platform_check.py`; the `restricted` row's `cpu_s` as a share of all rows; that row's `processes`. The last two come from one `submeter top --seconds 2 --json` run with `SUBMETER_HOME` set to a new empty folder. No pass threshold; from the personal PC only, so not asked for from the work PC (section 3.1, Owner tasks) | Owner | `step1/platform-check.txt`, `step1/top-norules.json`, `step1/restricted-share.txt` |
| P0.6 | `linux_cgroup_cost.py`'s output, labelled "CI-runner figure": leaf count; median and worst CPU per round over 100 rounds; cost per leaf; share of one core at 2 s and at 5 s. B5 recorded; the plan's default keeps R60 if the median round costs under 5 ms of CPU (0.1% of one core at 5 s) | CI-L | `ci/linux-cgroup-cost.txt` |
| P0.7 | `linux_pss_cost.py`'s output, labelled "CI-runner figure": process count, resident GB, CPU ms for the round, CPU ms per GB resident. B6 recorded with its arithmetic; the plan's default adopts full PSS if it costs under 30 ms of CPU per round more than the 25-largest round (0.1 percentage points of one core at the 30 s USS interval), judged on ms per GB | CI-L | `ci/linux-pss-cost.txt` |
| P0.8 | Probe 1, run from Windows Terminal, the VS Code terminal and Claude Code's shell. Step a succeeds. Step b succeeds in each of the 3 shells, with IsProcessInJob of the probe itself recorded. Step c: the job's CPU within 2% of the summed GetProcessTimes of its children, ActiveProcesses 0. Step d: reopening by name succeeds while the holder holds a handle and fails with error 2 after it closes. Step e: the breakaway error code recorded (non-zero). Step f: recorded, or skipped with B16's reason. Step g: the job CPU of 500 children of 5 ms recorded, with the spacing of its values. Step h: a burner in a job nested inside a job the probe made; both jobs' CPU recorded, and the outer job's CPU includes the burner's within 2%, as R49's subtraction assumes. Step a or b failing in any shell stops the build, because tagged runs are on the floor (`docs/15-phases-and-decisions.md:75`); step d or step h behaving otherwise sends B1 to the owner before P1 | Owner | `probes/job-object-terminal.txt`, `probes/job-object-vscode.txt`, `probes/job-object-claude-code.txt` |
| P0.9 | Probe 2, for each provider (the bulk prototype, psutil), 10 minutes at a fixed 2 s and 10 minutes at a fixed 5 s, at the machine's own count and again with 150 extra idle processes: process count, CPU ms per tick, cost per process, share of one core, the largest private bytes of samples taken every 10 s, the time of one USS round for the 25 largest processes, the combined share of the tick and that round at 5 s for a `uss_interval` of 30 s, 60 s and 5 minutes, the collector's user and kernel CPU apart, the raw store's share of the tick, Defender's CPU time over the runs if a standard user can read it, and per-field availability for other users' processes; the 300-process figure derived from the two points. The trigger (`docs/11-language.md:23`) fires if the bulk provider at 300 processes uses over 60 ms of CPU per tick at 2 s (3% of one core), over 50 ms per tick at 5 s (1%), or over 83,886,080 private bytes. Not fired: B2 is Python with 2 s and 5 s. Fired: the build stops and P2 is planned again | Owner | `probes/bulk-snapshot.txt` |
| P0.10 | Probe 3: `schtasks /Create /XML` exit code; the read-back XML matches 8 of 8 settings (InteractiveToken logon trigger for the current user, DisallowStartIfOnBatteries false, StopIfGoingOnBatteries false, ExecutionTimeLimit PT0S, MultipleInstancesPolicy IgnoreNew, restart on failure, Priority 5, RunLevel LeastPrivilege); `/Run` writes its marker file; `/Delete` exits 0; the effective AppLocker policy and the Device Guard status are saved; user and host names replaced. B3: the scheduled task if `/Create` exits 0 as the standard user, otherwise the Run key | Owner | `probes/autostart.txt` |
| P0.11 | `git ls-files docs/README.md 'docs/[01][0-9]-*.md' \| wc -l` prints 18 at G0 (the index and `docs/01` to `docs/17`) | the test runner's system | `ci/brief-files.txt` |
| P0.12 | `docs/STATUS.md` has one row for each of B1, B2 (language and default intervals), B3, B4, B5 and B6, and one for the breakaway record of P0.8 step f, each with the choice, its evidence file, who decided and the date. The evidence file is the personal PC's (section 3.1, Owner tasks). For B3, B4 and probe 2's trigger (B2) the row also records the work PC's word beside it, as the owner's statement with its date; where that word differs from the personal PC's result, the choice is not decided by the rule of P0.4, P0.9 or P0.10 but goes to the owner for a ruling at the gate, and the row records the ruling. Every figure in `docs/PLAN.md` that the review measured is marked as a Linux figure (R137) | — | `docs/STATUS.md` at E |
| P0.13 | `uv run python scripts/mutation_check.py` at G0: every mutant for a behaviour in R110's list is caught; a surviving mutant is listed with the reason it changes no behaviour, or the item fails | the test runner's system | `ci/mutation.txt` |
| P0.14 | `Measure-Command { uv run submeter --help }`, 20 runs: median and worst recorded. No pass threshold; the lead copies both into `docs/STATUS.md` as the first reading for P4.5 | Owner | `probes/startup-time.txt` |

**Procedure.** 6.2 with `d=docs/review/ground-windows/ci`: step 2 writes the seven checks to `ci/checks-<os>/` and makes no harness folder, and step 3 writes to `$d` itself in place of `$d/ci`, so that its files are the `ci/` files of the table. In place of step 2's harness the test runner runs:

```bash
{ echo '$ uv run python scripts/mutation_check.py'; uv run python scripts/mutation_check.py; echo "exit=$?"; } > "$d/mutation.txt" 2>&1
git ls-files docs/README.md 'docs/[01][0-9]-*.md' | wc -l > "$d/brief-files.txt"
```

After step 3 the test runner copies the two Linux figures from the Linux job's artefact (P0-W2-T4) to `ci/linux-cgroup-cost.txt` and `ci/linux-pss-cost.txt`. P0-O1 follows `docs/review/ground-windows/step1-procedure.md` (P0-W1-T2) at the P0-W1 integration commit. P0-O2 runs at G0: step 4, then the three probes, `platform_check.py`, the Defender query and the start-up timing. Each runs first on the personal Windows 11 PC, whose files are the evidence of the table, and then on the work PC, whose results the owner gives in one word each and the lead records (6.2 step 4); the "Owner" items of the table are judged on the personal PC's files, with the work PC's word beside them.

**Checked by.** The gate reviewer for P0.1 to P0.11, P0.13 and P0.14; the plan reviewer for P0.12. **Owner rulings due at this gate:** B1 to B6, any event under P0.3, any failure under P0.2 (b), B4 if neither ratio holds, B3, B4 or probe 2's trigger where the work PC's word differs from the personal PC's result (P0.12), and B16 before P0-O2 runs step f.

### 6.5 Gate P1: tagged runs

Entry: P1-W3 integrated; P1-O1 runs at G1. P1.1 to P1.10 are proved on the owner's machine and run on CI-W as a regression test on every push (row D1); P1.11 is proved on CI-L. Both CI-W and the owner's machine must pass each item that runs on both.

| Item | Pass criterion | Where | Evidence (under `docs/gates/P1/`) |
| --- | --- | --- | --- |
| P1.1 | `submeter run` of the generator's `spawn` mode: 500 children, each busy 50 ms and alive under 1 s, 8 at a time. Reference R = the children's summed CPU from GetProcessTimes on handles the generator keeps open, plus the generator's own CPU; R is at least 25 CPU-s. Pass: \|run file CPU − R\| ≤ 0.02 × R. The run file's TotalProcesses equals k0 + 500 exactly, where k0 is TotalProcesses of the same command with 0 children, measured in the same test: the interpreter the command names may start a second process of its own, so the count is calibrated, not assumed | Owner, CI-W | `owner/harness/P1.1.json`, `ci/run-<id>/gate-windows/P1.1.json` |
| P1.2 | The run file reaches its final state at most 5 s after the last member's exit, and `submeter cost --run <id> --json` then reports totals equal to the final run file's, field by field | Owner, CI-W | `P1.2.json` in both |
| P1.3 | The generator's `background` mode leaves one process that burns 10 CPU-s and writes its own GetProcessTimes total when it ends, then exits with code 7. `submeter run` exits 7; it returns at most 2 s after the command's exit while the background process is still running (its pid alive at the moment of return); the final run CPU is within 2% of generator + children + the background process's own total | Owner, CI-W | `P1.3.json` |
| P1.4 | 20 trials of a native command whose first action starts a grandchild through `cmd.exe /d /c start "" /b <grandchild>`; the grandchild reports IsProcessInJob TRUE in 20 of 20. With P1.12's static check (CreateProcessW with PROC_THREAD_ATTRIBUTE_JOB_LIST, never CREATE_SUSPENDED or AssignProcessToJobObject on the command) | Owner, CI-W | `P1.4.json` |
| P1.5 | Parsing check only. The harness opens the job by name during the run and keeps its handle, so the job outlives the holder; after the final state is written, the run file's CPU (100 ns units), I/O bytes, TotalProcesses and peak commit equal the values QueryInformationJobObject returns through that handle: 0 differences | Owner, CI-W | `P1.5.json` |
| P1.6 | An outer run whose command starts an inner `submeter run`. The inner run file names the outer run as parent; outer reported = outer kernel total − inner kernel total, 0 difference in 100 ns units; outer reported + inner reported within 2% of the generator's reference for both trees. With `SUBMETER_RUN` removed from the inner command's environment, the inner run file's parent is `unknown` | Owner, CI-W | `P1.6.json` |
| P1.7 | The generator's `breakaway` mode: CreateProcess with CREATE_BREAKAWAY_FROM_JOB fails inside the run; its error code is saved in the evidence (any non-zero code passes; 5 is expected) | Owner, CI-W | `P1.7.json` |
| P1.8 | node, then bash, then a grandchild: IsProcessInJob(grandchild, job) TRUE. Skipped with B16's reason when node or bash is absent; a skip is reported to the owner, not counted as a pass | Owner; CI-W if both are on the image | `P1.8.json` |
| P1.9 | `msedge.exe` with a new `--user-data-dir`, `--no-first-run --headless=new --dump-dom` of `tests/data/page.html` under `submeter run`: exit code 0, the page's marker string in the printed DOM, every `msedge.exe` sampled during the run inside the job, TotalProcesses at least 3. If the renderers cannot start under the job (R68, L03), the owner rules whether that fails the gate or is recorded as L03 with the browser named (section 11) | Owner only (`owner_machine`) | `owner/harness/P1.9.json` |
| P1.10 | Inside `submeter run`, a command whose arguments hold `--token=CANARY-<uuid>` and whose working folder is `CANARY-cwd-<uuid>` calls `submeter cost --run %SUBMETER_RUN% --json`: exit 0; one JSON object with `schema` `submeter.cost/1` and the run's id; 0 occurrences of either canary string or the folder path in the output | Owner, CI-W | `P1.10.json` |
| P1.11 | On CI-L, `submeter run --as x -- sh -c 'touch marker; exit 3'` exits 3, the marker exists and `--json` output carries `"tagged": false`; `submeter run --as system -- true` exits 2 | CI-L | `ci/run-<id>/gate-linux/P1.11.json` |
| P1.12 | Fixed rule 1. `tests/test_job.py` passes on CI-W, including the LimitFlags of a created job read back as 0 (P1-W1-T4). `git grep -n -E "AssignProcessToJobObject\|CREATE_SUSPENDED\|BREAKAWAY_OK\|KILL_ON_JOB_CLOSE" -- src` finds no call: the reviewer reads every line it prints | CI-W; the test runner's system | `ci/run-<id>.log`, `checks-<os>/p1-12-grep.txt` |

**Procedure.** 6.2, with one command added to step 2 after `7-pytest`, for P1.12:

```bash
run p1-12-grep git grep -n -E "AssignProcessToJobObject|CREATE_SUSPENDED|BREAKAWAY_OK|KILL_ON_JOB_CLOSE" -- src
```

The file starts with the `$` line and ends with the `exit=` line, as 6.2's evidence layout requires. `git grep` exits 1 when it finds nothing, so `exit=1` with no other line is the passing result; S1 does not read this file. On the owner's machine P1-O1 runs, after step 4:

```powershell
$env:SUBMETER_GATE_DIR = "$PWD\docs\gates\P1\owner\harness"
New-Item -ItemType Directory -Force $env:SUBMETER_GATE_DIR | Out-Null
uv run pytest tests/test_gate_p1.py -m "soak or not soak" -rsxX 2>&1 | Out-File -Encoding utf8 "$env:SUBMETER_GATE_DIR\pytest.txt"
```

With `-m "soak or not soak"`, which replaces the selection that `addopts` sets in `pyproject.toml` (P0-W1-T1), every case runs, including P1.9. **Checked by** the gate reviewer. **Owner rulings due:** the outcome of P1.9 if the browser fails; B16 if P1.8 skipped.

### 6.6 Gate P2: collector and raw store

Entry: P2-W6 integrated; P2-O1 has committed its fixtures, with the P2.4 bound committed before the recording; P2-O2 runs at G2. Step 1's push starts the soak workflow on both runners, in two jobs that run at the same time: `soak`, the 30-minute soak, and `soak-tests`, every test marked `soak` (the kill test and the 10-minute case of P2.2; section 7.5).

| Item | Pass criterion | Where | Evidence (under `docs/gates/P2/`) |
| --- | --- | --- | --- |
| P2.1 | The 30-minute CI soak on each runner (P2-W6-T2): minutes 0-10 active load, 10-20 quiet, 20-30 active with the spawner; one `submeter run` of the generator's `background` mode during it, whose left-behind process burns for at least 30 s after the command exits. The soak monitor and checker (P2-W5-T4), not Submeter's `overhead_fraction`, give the figures. (1) The machine's process count is at least 300 at every minute. (2) The summed CPU of every Submeter process, in each 60 s window from minute 2 to minute 30, is under 3% of one core (1.8 CPU-s) if any tick in the window ran at the active cadence, and under 1% (0.6 CPU-s) if every tick ran at the idle cadence; cadence is read from the raw ticks. Minutes 0 to 2 are reported, not judged. (3) At least 5 windows in minutes 10-20 are judged at the idle limit, so the 1% limit is tested. (4) Collector memory, with the server's from P3, under 157,286,400 bytes at every 10 s sample (private bytes on CI-W, USS on CI-L). (5) 0 sockets held by any Submeter process at every sample. (6) On CI-W only, at least one holder pid is among the processes measured (the checker's `--expect-holder`): the launcher starts a holder only when processes remain after the command exits (P1-W2-T1), which the `background` run makes sure of, and on CI-L `submeter run` starts no holder (P1-W2-T2, B13). (7) Token elevation is recorded but not judged on CI-W, whose runner is an administrator (`docs/15-phases-and-decisions.md:25`) | CI-W, CI-L | `ci/run-<id>/soak-windows/`, `ci/run-<id>/soak-linux/`: monitor CSV, checker output, tick intervals, guard event rows |
| P2.2 | Burners at 5% (reported, not judged), 15%, 25%, 50% and 100% of a core, each reporting its own CPU seconds every 1 s with a UTC and a monotonic time. Over 600 s, for each burner set above 10% of a core, that is 15%, 25%, 50% and 100% (the share a burner was set to decides whether it is judged, not the share measured, so noise never decides it): \|Submeter's stored CPU − the burner's own CPU interpolated to the window's first and last tick\| ≤ max(0.05 × the burner's CPU, 0.05 s). Parsing check, on CI-W and the owner's machine only (`docs/15-phases-and-decisions.md:41`: "Comparing with Windows performance counters is a parsing check only"): for each burner, \|the provider's CPU reading − the raw value of the burner's `\Process(<instance>)\% Processor Time` counter read at the same tick\| ≤ 156,000 units of 100 ns (15.6 ms). That counter is of type PERF_100NSEC_TIMER, whose raw value is the process's processor time in 100 ns units, so the two compare directly (P2-W6-T3). On the owner's machine with the bulk provider as the standard user | CI-W, CI-L, Owner; the parsing check CI-W and Owner only | `harness-<os>/P2.2.json`, `ci/run-<id>/soak-tests-*/P2.2.json`, `owner/harness/P2.2.json` |
| P2.3 | In every 60 s window of the P2.2 runs: \|attributed + unattributed + system + restricted + not seen by polling + idle − capacity\| ≤ 0.02 × capacity, with capacity = awake seconds × logical cores; and not seen by polling ≥ −0.02 × capacity, which is what catches a double count | CI-W, CI-L, Owner | `P2.3.json` in each |
| P2.4 | Replaying the owner's 10-minute quiet fixture, whose ticks hold both the bulk provider's process readings and the system counters (P2-O1, P2-W4-T3), through the sampler, attribution, `aggregate` and `reconcile`, not seen by polling stays under the bound, 5% of capacity unless the owner sets another, as a share of capacity. The bound was committed before the recording: `git log --diff-filter=A --format=%H -- tests/fixtures/recorded/quiet/bound.json` is an ancestor of, and not the same as, the commit that adds the recording | CI-W, CI-L | `P2.4.json`; the two commits named in it |
| P2.5 | The kill test (`tests/test_kill.py`, P2-W6-T1), 50 trials on each runner in the `soak-tests` job, each killing the collector after a random 1 to 60 committed ticks, at a fixed active interval of 1 s with `overhead_limit` at 10%: 50 of 50 report `PRAGMA integrity_check` `ok`, 0 acknowledged ticks missing, and the next start reopening the day file and continuing. The number of kills that fell inside a write transaction is reported; if it is 0 on a runner, the item is "not shown mid-write" and goes to the owner | CI-W, CI-L | `ci/run-<id>/soak-tests-*/P2.5.json` |
| P2.6 | The owner's 24-hour soak (P2-O2), with one sleep of at least 5 minutes. (1) Every 10-minute window that does not overlap the sleep, the span from the first time in `sleep.txt` to the end of the gap tick after it, which the checker's `--sleep` leaves out and lists: summed CPU of every Submeter process under 3% of one core (18 CPU-s) if any tick ran at the active cadence, under 1% (6 CPU-s) if every tick ran at the idle cadence. (2) Collector memory (private bytes) under 157,286,400 bytes at every 10 s sample. (3) Memory growth: the median of the collector's private bytes from 23 h to 24 h exceeds the median from 1 h to 2 h by less than 10,485,760 bytes; this is the limit `docs/15-phases-and-decisions.md:43` leaves to this section. (4) `PRAGMA integrity_check` `ok` for every raw file, read-only, after the collector stopped. (5) Every tick whose interval is longer than three times its expected interval plus 2 s carries the gap flag, the rule of `docs/05-data-flow.md:43`: 0 unrecorded gaps. (6) Exactly one gap tick ends between the first time in `sleep.txt` and 60 s after the second; its interval includes the sleep and its awake seconds do not (`docs/reference/windows-priorities.md:73`): its interval − its awake seconds is at least the noted sleep (the time between the two entries of `sleep.txt`) less 120 s, the time allowed for typing the two entries, and at most the noted sleep plus 2 s. `check.txt` prints that tick's interval, its awake seconds, the noted sleep and the windows left out of (1). (7) 0 sockets and a token that is not elevated, at every sample. (8) The machine's process count is recorded every minute; no minimum | Owner | `owner/soak/monitor.csv`, `owner/soak/check.txt`, `owner/soak/sleep.txt` |
| P2.7 | Redaction before anything is written (floor item). A burner whose arguments hold `--password=CANARY-<uuid>` runs under the collector once with the default `exe_only` mode and once with `scrub`. The burner runs in a working folder named `CANARY-cwd-<uuid>` and holds open a file named `CANARY-file-<uuid>`. Afterwards none of the three occurs, as UTF-8 bytes or as UTF-16-LE bytes, in any `.db`, `-wal`, `-shm` or log file under `SUBMETER_HOME`; the last two show that no record holds a file a process touched (L11) | CI-W, CI-L | `P2.7.json` |
| P2.8 | Measured store figures replace estimates: `docs/06-storage.md`'s disk table and the "Volume per day" column of `docs/05-data-flow.md:78-87` give rows and bytes per tick measured in a soak on each runner (P2-W6-T2), and name that `soak.yml` run by id and commit; the figures equal those in that run's artefacts, which the test runner copies at the gate (procedure below). `docs/06-storage.md` also gives the longest time between write-ahead log checkpoints at the shipped cadence, read by the soak monitor from the `-wal` header (P2-W5-T4), which `docs/06-storage.md:39` says is to be confirmed once the collector exists. G2's own soak gives the same figures again, which are reported beside them, not judged, because rows per tick depend on which processes cross the change thresholds and on keyframes (`src/submeter/store/raw.py:3-8`) | CI-W, CI-L | `docs/06-storage.md` and `docs/05-data-flow.md` at E; `ci/run-<named id>/soak-*/`; `ci/run-<id>/soak-*/` of G2 |

**Procedure.** 6.2, with one addition to step 3: for P2.8 the test runner reads the run id that `docs/06-storage.md` names beside its disk table and copies that run too, with `gh run view <id> --json databaseId,headSha,headBranch,conclusion,url > "$d/ci/named-run.json"` and `gh run download <id> --dir "$d/ci/run-<id>"`. P2-O2 runs on the owner's machine after step 4. First, at G2, `uv run pytest tests/test_gate_p2.py -m "soak or not soak" -rsxX` with `SUBMETER_GATE_DIR` set to `docs\gates\P2\owner\harness`, as in 6.5, which gives P2.2, P2.3 and P2.4 there. Then the soak, in two PowerShell windows. The flag names are those P2-W5-T4 gives its tools, and the checker's command writes out every option rather than relying on a default (P2-W5-T4); the inputs and outputs are as listed.

```powershell
# both windows
$env:SUBMETER_HOME = "$env:LOCALAPPDATA\SubmeterSoakP2"     # a new, empty folder
$o = "$PWD\docs\gates\P2\owner\soak"; New-Item -ItemType Directory -Force $o | Out-Null
# window 1
uv run submeter-collector
# window 2
uv run --directory tests python -m tools.soak monitor --out "$o\monitor.csv"
# after at least 1 h: put the computer to sleep for at least 5 minutes; note the time just before the sleep and just after waking
Get-Date -Format o | Out-File -Append -Encoding utf8 "$o\sleep.txt"      # just before the sleep, and again just after waking (2 minutes in all at most)
# after 24 h
New-Item -ItemType File "$env:SUBMETER_HOME\state\control\stop-collector" | Out-Null   # the collector stops within one tick
# stop the monitor with Ctrl+C, then
uv run --directory tests python -m tools.soak check --csv "$o\monitor.csv" --raw "$env:SUBMETER_HOME\data" --window 600 --skip 0 --min-idle-windows 0 --min-processes 0 --judge-elevation --sleep "$o\sleep.txt" 2>&1 | Out-File -Encoding utf8 "$o\check.txt"
```

The Defender query of P0.3 runs again afterwards, into `owner/defender-asr.txt`. The raw files stay on the owner's machine.

**Checked by** the gate reviewer. **Owner rulings due:** B11 before P2-W3-T2 is dispatched, since criterion (2) of P2.1 needs a definition of quiet; the P2.4 bound before P2-O1 records; P2.5 if no kill fell inside a write.

### 6.7 Gate P3: attribution rules, history, sessions

Entry: P3-W6 integrated; P3-O1 runs at G3. The soak workflow at G3 includes the server (P3-W6-T2).

| Item | Pass criterion | Where | Evidence (under `docs/gates/P3/`) |
| --- | --- | --- | --- |
| P3.1 | On the synthetic 3-hour raw fixture (P3-W1-T2), 22:30 to 01:30 UTC across two day files, once with ticks at whole seconds and once at 2 s with a 0.3 s phase and ±0.05 s jitter, with one gap sample: for each of the 3 hours, \|CPU from `rollup_1h` − the sum of raw `cpu_s` of samples whose end falls in that hour\| ≤ 0.001 × that sum. The reference is computed with plain SQL through `sqlite3`, not through `store.rollup` or `store.query`; the gap sample and the sample ending at exactly 00:00:00.0 are in the hour that holds their end | CI-W, CI-L | `P3.1.json` in each |
| P3.2 | On CI-W, with a read-only reader open on a raw day, the retention pass is refused, the `.db`, `-wal` and `-shm` remain and `disk_use` still counts them; after the reader closes, the next pass removes all three and the raw part of `disk_use` falls by exactly their total size in bytes. On CI-L the files go at once. On both, no day is deleted before the rolled-up-until mark has passed its end | CI-W, CI-L | `P3.2.json` |
| P3.3 | A 120 s tagged burner. Trial 1 stops the collector with its stop file, trial 2 kills it; each restarts it within 10 s. Within one tick of the restart the workload's rows carry source `kernel`, and the workload's per-tick CPU summed over the run, including the CPU recorded across the gap, is within 2% of the final run file's CPU, with no double count | CI-W, Owner | `P3.3.json`, `owner/harness/P3.3.json` |
| P3.4 | With an injected clock, a 30-minute session and a retention of 5 minutes passed directly to the retention function (`retention.raw` cannot go below 24 h): every numeric field of `submeter cost --session S --json` is equal before and after the session's raw data is deleted, 0 differences. A run file is deleted only after its row is committed | CI-W, CI-L | `P3.4.json` |
| P3.5 | The soak of P2.1 with the server running, starting at minute 40 of an hour so that it crosses an hour boundary; one `submeter store backup` and one retention pass during it. Criteria (1) to (7) of P2.1, summed over every Submeter process with the server included; collector plus server under 157,286,400 bytes. The server did its work: at least 1 `rollup_1h` row for the hour crossed, 1 file in `backups/`, and at least 1 retention pass in the server's log | CI-W, CI-L | `ci/run-<id>/soak-windows/`, `ci/run-<id>/soak-linux/` |
| P3.6 | The Windows logon task (or the Run key, if B3 chose it). As the standard user, `submeter daemon install` exits 0; after signing out and in, `submeter daemon status` shows a lock holder for the collector and for the server; `schtasks /Query /TN <task> /XML` matches the 8 settings of P0.10 for each task; `submeter daemon stop` leaves no holder within 10 s; `submeter daemon uninstall` exits 0 and removes the tasks | Owner (`session`) | `owner/daemon.txt` |

**Procedure.** 6.2 as written. P3-O1, after step 4: `submeter daemon install`, sign out and in, `submeter daemon status`, the read-back, then `uv run pytest tests/test_gate_p3.py -k "test_p3_3_" -m "soak or not soak" -rsxX` with `SUBMETER_GATE_DIR` at `docs\gates\P3\owner\harness`, then `daemon stop`, `daemon status` and `daemon uninstall`, each output saved in `owner/daemon.txt` as in step 4. **Checked by** the gate reviewer; for P3.1 the reviewer also reads the function that computes the reference and confirms it imports neither `store.rollup` nor `store.query`.

### 6.8 Gate P4: analysis

Entry: P4-W4 integrated; P4-O1 runs at G4. B12, B14, B15 and B20 are recorded, because P4-W1-T3, P4-W1-T4, P4-W2-T1 and P4-W2-T3 cannot be dispatched without them.

| Item | Pass criterion | Where | Evidence (under `docs/gates/P4/`) |
| --- | --- | --- | --- |
| P4.1 | Each of the 12 detectors fires on its trigger fixture and stays silent on its quiet fixture: the leak check, the runaway count (as B12 defines it), the 7 verdicts of `docs/07-analysis.md:114-122` (CPU-bound, memory-bound, I/O-bound, GPU-bound, thermally throttled, no bottleneck, inconclusive) and the 3 built-in alert rules (`docs/08-configuration.md:150-152`). Inconclusive is reached by each of its 4 routes: two rules match; a rule matches while its ruled-out condition holds; under 60 s of data; confidence below `verdict.min_confidence`. On CI-L, `why` reads Inconclusive or unavailable and never No bottleneck (`docs/07-analysis.md:112`). A finding raised by the leak check, the runaway count and each alert rule appears in `submeter findings --json` and in `submeter why --json`. The fixtures did not change after their own wave: `git log --oneline <P4-W1 integration commit>..G4 -- tests/fixtures/detectors tests/fixtures/verdict tests/fixtures/alerts tests/tools/series.py` prints nothing | CI-W, CI-L | `P4.1.json` in each; `checks-<os>/p4-1-fixtures.txt` |
| P4.2 | The leak of 78,643,200 bytes an hour, rows every 30 s, uniform noise of ±40 MiB per row, 200 seeds: flagged at most 2 h 5 min after the leak starts in at least 190 of 200 (B14's figures; the owner may set others) | CI-W, CI-L | `P4.2.json` |
| P4.3 | The browser warm-up of `docs/07-analysis.md:24` with the same noise, over 6 h, 200 seeds: flagged in 0 of 200 | CI-W, CI-L | `P4.3.json` |
| P4.4 | The staircase of 268,435,456 bytes (256 MB) every 2 h with the same noise: flagged within 6 h of the first step in at least 190 of 200 | CI-W, CI-L | `P4.4.json` |
| P4.5 | `why --json` through the installed entry point (`.venv\Scripts\submeter.exe`, not `uv run`) on a raw file of 5 minutes at 300 processes and a 2 s interval (150 ticks): each of 20 runs under 2.0 s of wall time, and the first run after a restart of the computer under 2.0 s, recorded on its own. If only that first run fails, the owner rules. On CI the times are measured and recorded, not judged | Owner; CI-W, CI-L measured only | `owner/harness/P4.5.json` |
| P4.6 | The soak of P3.5 with the server running analysis and alerts (P4-W4-T2): every criterion of P3.5, and at least 1 analysis pass in the server's log | CI-W, CI-L | `ci/run-<id>/soak-*/` |

**Procedure.** 6.2 as written. The lead names the P4-W1 integration commit from `docs/STATUS.md` for P4.1's `git log`; the test runner saves that output as `checks-<os>/p4-1-fixtures.txt`. P4-O1: restart the computer and sign in; before any other Submeter command, `uv run pytest tests/test_gate_p4.py -k "test_p4_5_" -m "soak or not soak" -rsxX` with `SUBMETER_GATE_DIR` at `docs\gates\P4\owner\harness`; then step 4. The harness's timer (`tests/tools/time_cmd.py`) records the first `why` run apart from the 20 that follow. **Checked by** the gate reviewer. **Owner rulings due:** P4.5 if only the first run fails.

### 6.9 Gate P5: report and GPU load

Entry: P5-W4 integrated; P5-O1 has committed the GPU fixtures; P5-O2 runs at G5, at least its step 4, so that the seven checks pass on the owner's machine at the final commit (row D16). This is the last gate: when the owner approves it, version 1 is done as section 1.2 defines.

| Item | Pass criterion | Where | Evidence (under `docs/gates/P5/`) |
| --- | --- | --- | --- |
| P5.1 | On a synthetic store in `scrub` mode with canary arguments, over a range that spans raw and hourly data, `submeter report` run once for a session and once for a range writes exactly 1 file each time. In each file: 0 occurrences of `http://` or `https://`; a meta Content Security Policy with `default-src 'none'` and one `sha256-` source for each inline script and style, every hash matching its block and as many hashes as blocks; 0 occurrences of any canary; every chart caption names `raw` or `hourly` and a resolution; a finding stored in the synthetic store appears; each epoch boundary in the range is marked on the charts it crosses, with its reason, and the range across the 30-day store's rules change shows exactly one marker; each workload shows its accounting source, kernel, polled or counters; the four fixed workloads appear, with the CPU time not seen by polling beside them; the notes of L01, L02, L03, L04, L10 and L12 appear beside the figures they affect; the count of processes whose start time could not be read appears beside Restricted; a name holding `<script>` appears escaped, with 0 unescaped. Opened in a headless Chromium-based browser with the network blocked: 0 Content Security Policy violations in the console log and 0 network requests. The browser is one the runner image lists, confirmed by P5-W4-T1's builder; if neither runner has one, this part runs on the owner's machine with Edge | CI-W, CI-L | `P5.1.json` in each |
| P5.2 | Each extended provider's recorded fixtures replay with values equal to the expected values written beside them when they were recorded: 0 differences. Windows: the owner's recorded GPU fixtures (P5-O1) and the documentation-shaped ones; Linux: NVML, DRM fdinfo and amdgpu fixtures shaped from documentation, which `docs/STATUS.md` names as never run on real hardware | CI-W, CI-L | `P5.2.json` |
| P5.3 | With each provider's source absent (no GPU counter set, no NVML library, no `/sys/class/drm`; the runners have no GPU): the provider reports unavailable with a reason, every metric it owns is None and never 0, 0 exceptions escape, the collector writes at least 10 further ticks, and `submeter doctor --json` shows `gpu.load` and `gpu.memory` as unavailable | CI-W, CI-L | `P5.3.json` |
| P5.4 | The soak of P4.6 with the GPU providers enabled (P5-W3-T2): every criterion of P4.6 | CI-W, CI-L | `ci/run-<id>/soak-*/` |
| P5.5 | If the owner keeps it, the 24-hour soak again with every program and provider of version 1 (P5-O2): P2.6's criteria (1) to (8), with collector plus server memory under 157,286,400 bytes and `PRAGMA integrity_check` `ok` for the history file too | Owner | `owner/soak/` |

**Procedure.** 6.2 as written; P5-O2 as P2-O2, with `SUBMETER_HOME` at a new folder `SubmeterSoakP5` and `uv run submeter-server` in a third window. The programs are not started through `submeter daemon start`: a scheduled task runs with the user's own environment, not the shell's, so it would not use the soak's `SUBMETER_HOME`. **Checked by** the gate reviewer; row D17 (every component built or cut, every traceability row pointing to a passing test or to "not in version 1") by the plan reviewer at E. **Owner rulings due:** B18 if P5-W1-T2's builder found no unprivileged source for the adapter's VRAM; whether P5.5 is required.

### 6.10 Where each gate needs the owner or a second operating system

The build session works on one system. Whatever it needs from the other system comes only from CI, and whatever needs an unprivileged user, a logon session or hardware comes only from the owner's machine (`docs/15-phases-and-decisions.md:25`). Every gate needs the owner's approval.

| Gate | On the owner's machine | Owner rulings at or before the gate | Needs CI-W | Needs CI-L |
| --- | --- | --- | --- | --- |
| P0 | P0-O1 (about 45 minutes, at the P0-W1 commit); P0-O2 (about 2 hours plus step 4, at G0) | B1 to B6; B7, B9 and B10's `AGENTS.md:35` wording earlier, before their tasks; B16; any P0.3 event; any P0.2 failure | P0.1 | P0.1, P0.6, P0.7 |
| P1 | P1-O1 (about 30 minutes plus step 4) | P1.9's outcome if the browser fails; B13 before P1-W2-T2 | P1.1 to P1.8, P1.10, P1.12 | P1.11 |
| P2 | P2-O1 (about 1 hour); P2-O2 (24 hours elapsed, under 1 hour attended, plus step 4) | B8 and B11 before their tasks; the P2.4 bound before recording; P2.5 if no kill fell inside a write | P2.1 to P2.5, P2.7, P2.8 | P2.1 to P2.5, P2.7, P2.8 |
| P3 | P3-O1 (about 20 minutes plus step 4, including a sign-out) | B17 and B19 before their tasks | P3.1 to P3.5 | P3.1, P3.2, P3.4, P3.5 |
| P4 | P4-O1 (about 15 minutes plus step 4, including a restart) | B12, B14, B15, B20 before their tasks; P4.5's first run if it alone fails | P4.1 to P4.4, P4.6 | P4.1 to P4.4, P4.6 |
| P5 | P5-O1 (about 15 minutes); P5-O2 (step 4 at least; 24 hours if P5.5 is kept) | B18; whether P5.5 is required | P5.1 to P5.4 | P5.1 to P5.4 |

If the build session runs on Linux, every CI-W item and every owner item is out of its reach and arrives as evidence from CI or from the owner. If it runs on the owner's personal Windows PC as the standard user, only the CI-L items need CI, and a test runner there may type the owner tasks' commands (6.1). The work PC is never a build machine: its results arrive only as the owner's words (6.2 step 4).

### 6.11 When a gate fails

1. For each item that fails or cannot be judged, the lead dispatches a failure investigator. Its report names the cause, the files and the task that owns them in the plan.
2. The lead writes a fix task card for each cause (section 5.5) and runs the fixes as a wave. After it integrates, the gate starts again at step 1 with a new gate commit. Steps 2 and 3 run in full, since `uv sync` and the seven checks took 26.3 s in a fresh copy on the review's Linux machine and CI runs by itself; an owner run counts again only by the rule of step 4.
3. An item that cannot be met as written, or whose outcome may be accepted as a known limit (P1.9, P2.5 without a kill inside a write, P4.5's first run), goes to the owner, and the ruling is recorded in `verdict.md` and `docs/STATUS.md`.
4. If the same item fails on two gate runs, the lead stops and puts both sets of evidence to the owner. There is no third run without the owner's word.
5. A failure that touches a fixed rule stops the build at once, whatever the other items show: an event under P0.3, a hit under P1.12, a socket or an elevated token in any soak, a canary found under P1.10, P2.7 or P5.1, or a failure of `tests/test_fixed_rules.py`.

### 6.12 Numbers this section sets that no document or ruling gives

Each is this plan's choice so that the gate can be run and can fail. Section 11 puts them to the owner.

| Item | Number | Why |
| --- | --- | --- |
| Every gate | The owner check run (step 4) at G, in the phase's last owner task | row D16 needs the checks on the owner's machine; `docs/15-phases-and-decisions.md` asks only for P0's |
| S2 | 0 xfailed, 0 xpassed; each skip reason from a fixed list | keeps a skipped test from standing in for a passing one |
| P0.4 | r1 or r2 between 0.99 and 1.01 on every core, 3 repetitions of 10 s | `docs/reference/windows-priorities.md:53` says "equals" with no tolerance |
| P0.8 c | job CPU within 2% of the children's summed GetProcessTimes | the tolerance P1 will need |
| P0.8 h | the outer job's CPU includes the nested job's burner within 2% | R49's subtraction rests on it, and no document states a tolerance |
| P0.9 | 10 minutes per provider, interval and process count (80 minutes); 150 extra idle processes for a second point; the largest of 10 s private-bytes samples | the brief does not say how the 300-process figure is derived |
| P1.1 | 500 children busy 50 ms, alive under 1 s, 8 at a time; the process count calibrated with a 0-child run | the brief gives only "500 sub-second children" |
| P1.2 | final state within 5 s of the last exit | no time is stated |
| P1.3 | return within 2 s of the command's exit; a 10 CPU-s background process; exit code 7 | no time is stated |
| P1.4 | 20 of 20 trials through `cmd.exe /d /c start` | a Python command cannot act in its first millisecond |
| P1.5, P1.6, P3.4 | exact equality, 0 differences | each compares stored values, not measurements |
| P2.1 | 60 s windows; minutes 0-2 not judged; at least 5 idle windows in minutes 10-20; at least 300 processes every minute; a holder pid on CI-W only, from a `background` run whose process lives at least 30 s past the command | the brief gives the budget but no window, start-up or process-count rule for a 30-minute run; a holder exists only on Windows and only when processes remain |
| P2.2 | burners at 5 (not judged), 15, 25, 50 and 100% of a core, judged by the share each was set to; 15% rather than 10%, so that the lowest judged burner is not at the threshold `docs/15-phases-and-decisions.md:41` names; 1 s reports interpolated to the ticks; the parsing check against the raw `% Processor Time` counter, within 156,000 units of 100 ns (15.6 ms) | alignment and the parsing check's counter and tolerance are not stated |
| P2.3 | not seen by polling at least −2% of capacity in every window | the sum holds by construction; the negative bound is what can fail |
| P2.4 | 5% of capacity, committed before the recording | no share is stated anywhere |
| P2.5 | 50 trials, a kill after 1 to 60 ticks at a fixed 1 s with `overhead_limit` at 10%; the `soak-tests` job's limit of 150 minutes (section 7.5) | no number of trials, interval or time is stated |
| P2.6 | 10-minute windows; growth under 10,485,760 bytes between the medians of 1-2 h and 23-24 h; one sleep of at least 5 minutes, noted by hand just before and just after; the gap tick ending within 60 s of the second note; the time awake seconds leave out at most 2 s above and at least 120 s below the noted sleep | `docs/15-phases-and-decisions.md:43` leaves the growth limit to this section |
| P2.7 | the canary searched as UTF-8 and UTF-16-LE bytes | Windows APIs return command lines as UTF-16 |
| P3.3 | restart within 10 s; source `kernel` within one tick; 2% | the brief says only "re-attaches" |
| P3.5 | start at minute 40; at least 1 hourly row, 1 backup and 1 retention pass | otherwise the server's costly work may not happen in 30 minutes |
| P3.6 | no holder within 10 s of `daemon stop` | no time is stated |
| P4.2 to P4.4 | B14's defaults: 30 s rows, ±40 MiB per row, 200 seeds, 190 of 200, 0 of 200 over 6 h, the staircase within 6 h | the brief states the noise two ways and no pass rate |
| P4.5 | 20 runs, every one under 2.0 s, and the first run after a restart under 2.0 s | no data volume, machine or count is stated |
| P5.3 | at least 10 ticks after the source is found absent | "degrades cleanly" is not defined |


## 7. The test strategy

Four rules shape every test in this plan. A change in behaviour starts with a failing test (`AGENTS.md:48`). A gate's reference never comes from the code it judges (R83). CI proves portability, and the owner's machine proves privilege, logon sessions and hardware (`docs/15-phases-and-decisions.md:25`, R118). Every fixture is built by a named task. Section 6 gives each gate's procedure and numbers; this section gives the tests, data, tools and CI behind them. Every timing quoted here was measured on the review's Linux machine (R137); none was taken on Windows.

### 7.1 Kinds of test and where each runs

| Kind | Files | Marker | Runs on | When |
| --- | --- | --- | --- | --- |
| Component tests | `tests/test_<component>.py` (`docs/17-build-prompt.md:43`), with records from `tests/builders.py` | none | the CI matrix (7.5); the builder's own machine | every push |
| Windows-only tests | the same files, skipped elsewhere with a stated reason | none | CI-W | every push |
| Linux-only tests | likewise | none | CI-L | every push |
| Static rule tests | `tests/test_layers.py`, `tests/test_fixed_rules.py` (P0-W3-T3), `tests/test_project.py`, `tests/test_fixtures_anonymised.py` (P2-W1-T3) | none | the CI matrix | every push |
| Replay tests on recorded fixtures | `tests/test_recorded_fixtures.py` (P2-W6-T4); the GPU cases of `tests/test_gate_p5.py` | none | CI-W, CI-L | every push |
| Gate harnesses | `tests/test_gate_p1.py` to `tests/test_gate_p5.py` | none for short cases; `soak` for long ones; `owner_machine`, `session` or `hardware` where the case needs them | CI; the soak workflow; the owner's machine | every push; gate branches; each gate |
| Soak and kill tests | `tests/test_kill.py`, the soak workflow's dry run, and every other case marked `soak` | `soak` | the soak workflow's `soak-tests` job (7.5) | `gate/*` and `soak/*` branches and manual runs |
| Owner-machine tests | any test file | `owner_machine`, `session`, `hardware` | the owner's Windows machine as the signed-in standard user | in each phase's owner tasks |
| The 24-hour soak | not pytest: the soak monitor and checker of `tests/tools/soak/` | none | the owner's machine | P2-O2, P5-O2 |
| Mutation check | `scripts/mutation_check.py` (P0-W6-T1) | none | the lead's checkout | the P0 gate; proposed: at each later gate, kept as evidence and not judged |

The markers are registered in `pyproject.toml` with `--strict-markers` by P0-W1-T1, and the main CI job deselects all four. `addopts` in `pyproject.toml` deselects the same four, so the plain `uv run pytest` of `AGENTS.md:32`, which builders and the lead run, selects what CI's main job selects; a later `-m` on the command line replaces that selection, and `-m "soak or not soak"` selects every test. What each one means:

- `owner_machine`: needs the unprivileged signed-in user or the owner's managed computer. Covers refused reads, Restricted counts, folder access lists, a token that is not elevated, Defender and AppLocker, and programs a runner image may not have (Edge with a new profile, node, bash).
- `session`: needs an interactive logon session. Covers registering and running the logon task, and signing out and in.
- `hardware`: needs hardware the hosted runners lack: a GPU, a battery, suspend, frequency throttling.
- `soak`: runs longer than 60 s, or loads the machine for minutes. Covers the kill test, the soak workflow's dry run, the 10-minute burners of P2.2, P3.3's two 120 s trials, and the 200-seed leak runs if they take longer than 60 s on a runner. The 60 s bound is proposed. They run in the soak workflow's `soak-tests` job, whose time 7.5 sums.

Rules for every test file:

1. A skip states its reason. CI runs pytest with `-rs`, and at each gate the gate reviewer reads the skip lists of all four CI jobs. A test that is skipped in all four jobs and carries no owner marker tests nothing anywhere, and is a finding. Today two tests skip on Windows: `tests/test_files.py:101` (permission bits mean nothing there) and the daylight-saving test of `tests/test_analysis.py:39` (its fixture at :17-24 needs `time.tzset`, which exists only on POSIX). `docs/STATUS.md` records the skip list at each gate.
2. Strict expected failures are allowed only as gate criterion S2 permits (section 6). CI runs with `-rxX` so that each one is listed.
3. No test package is added. `AGENTS.md:49` needs the owner's approval for a new dependency, and the dev group is mypy, pytest, pytest-asyncio, ruff and types-psutil (`pyproject.toml:19-25`). So there is no snapshot plugin, property-based testing library, parallel runner, timeout plugin or coverage tool unless the owner approves one. Instead: snapshot tests parse the command's JSON and compare it with expected values kept in the test file, or in a JSON file the task owns. Every call that starts a process passes `timeout=`, so a hung child fails its test rather than the CI job. The mutation check (P0-W6-T1) measures how strong the tests are, since no coverage figure is planned.
4. A test writes only under `tmp_path`. The last CI step checks that `git status --porcelain` prints nothing. That catches a test writing into the working copy, and a file rewritten with Windows line endings (`docs/reference/windows-priorities.md:98`; `.gitattributes` sets `* text=auto eol=lf`).
5. Every SQLite connection a test opens is closed before the test ends. Windows cannot delete a file that any program holds open (`docs/reference/windows-priorities.md:62`), so a leaked connection shows there as a refused retention delete or a failed clean-up.
6. Text compared byte for byte is written with `newline="\n"`: the report file and its CSP hashes. Every other comparison parses the output first (JSON, CSV), so Windows line endings do not fail it.
7. When pytest runs more than once at a time on one machine (in builders' working copies and in the lead's checkout), each run passes its own `--basetemp`, outside the working copy. pytest 9.2.0 deletes the `--basetemp` folder at the start of a run (`_pytest/tmpdir.py`, `getbasetemp`), so the folder must be unique to each working copy. Without the option, every run on the machine shares `pytest-of-<user>` under the system's temporary folder.
8. CI prints `--durations=25`. If a test case takes longer than 60 s on either runner, it gets the `soak` marker and keeps a shorter variant without it (proposed). A task that adds a `soak` case states the case's time on its card, and the cases together stay inside the `soak-tests` job's limit; section 7.5 sums them for each gate.

### 7.2 Tests first, and how a test-only task shows its test can fail

Each task branch follows these steps. They let the reviewer confirm that the test failed before the change and passes after it (stage 3, principle 4):

1. The branch's first commit adds or changes tests and nothing else. The builder pushes that commit alone and waits for its CI run. GitHub runs a push workflow once, on the commit the branch points to after the push. A test commit pushed together with the change therefore gets no failing run of its own. Most tests first import a module or call a signature the task has not yet written, so that run fails strict mypy, and a test file that imports a missing module is a pytest collection error, which without `--continue-on-collection-errors` stops the whole session with no other test run (reproduced for this plan on 23 November 2026 in a scratch copy of `1c734e0` with one new `tests/test_runs.py` importing `submeter.store.runs`: pytest printed `Interrupted: 1 error during collection` and ran none of the 62 existing tests; with `--continue-on-collection-errors` the same copy gave `61 passed, 1 xfailed, 1 error`; `uv run mypy src tests` printed `Found 1 error in 1 file`). `ci.yml` therefore runs every check after a failed one and pytest with that option (P0-W1-T1). The run is expected to show three things, and the reviewer checks each: mypy reports errors only in the task's new or changed test files; the failed or errored tests are exactly the tests the task card names (`-rfE` lists them); every other test passed.
2. The change follows in later commits. The run of the branch's last commit must pass in every job of `ci.yml`: two with Q2's default (a Windows job and a Linux job on Python 3.13, 7.5), four if the owner adds Python 3.14.
3. The reviewer reads both runs. For a test that only CI-W runs, the reviewer reads the CI-W job of each run, because a builder working on Linux has no other way to see a Windows-only test fail. `ci.yml` therefore does not cancel a branch's earlier runs when a new commit arrives (no `cancel-in-progress`).
4. Some tasks deliver only a test or a tool: gate harnesses, replay tests, the load generator, the soak tools and the generators. There is no product change for their tests to fail before. In a scratch copy, the reviewer plants a fault for the test to catch and confirms that the test fails:

| Task | Planted fault | The check that must fail |
| --- | --- | --- |
| P1-W1-T3, load generator | a child that skips its busy loop | that child's reported CPU is under 40 ms |
| P1-W3-T1, P1 gate | a run file 2.5% above the generator's reference; a run file that misses one child | the 2% comparison; the exact process count |
| P2-W5-T4, soak checker | a 60 s window at 3.1% of a core; a tick interval of 3 times the expected one plus 3 s without the gap flag | that window; the missing gap flag |
| P2-W6-T1, kill test | a collector that writes a tick's `commit` line to the tick log before its transaction commits | at least one trial reports a committed tick missing |
| P2-W6-T3, P2 gate | a stored CPU 6% above a burner's own figure; a not-seen-by-polling term at −3% of capacity; a canary written into a `-wal` file as UTF-16 | each of the three checks |
| P2-W6-T4, replay | one expected value changed by one unit | that fixture's replay |
| P3-W6-T1, P3 gate | an hourly rollup that assigns each sample by its midpoint | P3.1 on the long gap sample of the 3-hour fixture (7.3.2) |
| P4-W4-T1, P4 gate | a leak check that always flags; one that never flags | the warm-up case; the leak case |
| P5-W4-T1, P5 gate | an `https://` string in a caption; a wrong CSP hash; a command line in a tooltip | the text scan; the browser check (with a wrong hash the inline script does not run, so the chart canvases are absent from the dumped DOM); the canary scan |

**The pilot's exception (P0-W1).** At the pilot's base commit there is no `.github/` (`ls -d .github` at `1c734e0`: no such file or directory), and GitHub runs a push workflow only from the workflow files in the pushed commit. So P0-W1-T1's test-only commit starts no run, and P0-W1-T2's branch, cut from the same base, never runs on CI at all. For both tasks the reviewer runs the task's named tests in its own worktree at the test-only commit, where they must fail, and at the last commit, where they and the seven checks must pass. P0-W1-T1's last commit, which adds `ci.yml`, runs on both runners before merge. The CI run of the P0-W1 integration commit must then pass on CI-W and CI-L, P0-W1-T2's UTF-16 cases included, before the lead fixes P0-W2's base commit. Every later base commit holds `ci.yml`, so steps 1 to 3 apply from P0-W2 on.

**Fixes for tests that already fail at the base commit.** A fix task written for a failure that CI already shows at its base commit (the baseline's first CI-W failures, K40) has its failing test already: an existing test that fails at B. Its card names that test and a CI run that shows it failing at B, or at an earlier commit that differs from B only under `docs/`, and its branch may start with the change; the reviewer reads that run in place of a test-only commit's run and confirms the test passes in the run of the last change commit. A fix for a failure seen only on the owner's machine (P0-O1, 5.5) follows step 1: its test, which reproduces the failure, comes first. A fix that needs a new or sharper test still commits that test first, alone, as step 1 says. Added in stage 3, with `prompts/02-orchestration-prompt.md` 8.5.

**References from outside the code under test (R83).** Each gate takes its reference from a source the code under test does not compute:

- Tagged-run CPU (P1.1, P1.3, P1.6): the load generator's own accounting (7.4).
- Per-process CPU (P2.2): each burner's own report of its CPU seconds.
- The overhead budget (P2.1, P2.6, P3.5): the soak monitor, which reads every Submeter process from outside with psutil, never Submeter's own `overhead_fraction`.
- Hourly sums (P3.1): the generator's record of the CPU it generated per hour, and plain SQL over the raw file. Neither uses `store.rollup` or `store.query`.
- Crash safety (P2.5): the tick ids the collector logged after each commit, and `PRAGMA integrity_check`.
- The leak gate (P4.2 to P4.4): the known start time and slope of each generated series.
- The report (P5.1): text scans and a browser.

The code reviewer checks that each harness takes its reference from this list, and imports from `submeter` only the code it judges. The load generator and the soak tools import nothing from `submeter`. An AST test checks this for the load generator (P1-W1-T3), and the same test is proposed for the soak tools (P2-W5-T4).

### 7.3 Fixtures

There are four kinds:

- **Inline:** values written into the test file, taken from vendor documentation or from the review's probes under `docs/review/probes/`. Each one names its source in a comment.
- **Synthetic:** generated at test time from a seed, by a tool under `tests/tools/`.
- **Recorded:** read on the owner's machine with the fixture recorder, anonymised, and committed under `tests/fixtures/recorded/`.
- **Documentation-shaped:** files under `tests/fixtures/<component>/` for sources that no machine available to the build has, written to the format the vendor documents.

Rules:

1. Every fixture names the task that built it; the table in 7.3.1 lists them all.
2. Synthetic stores are built in `tmp_path` at test time and are not committed. That keeps them out of git, and each runner writes them with its own SQLite. Reproducibility is checked on a canonical row dump (each table's rows in key order), not on the file's bytes. SQLite writes the version of the library that last modified a file into the file's header (offset 96 in the SQLite file format), and the interpreters on the review machine carry different builds: SQLite 3.50.4 with uv's Python 3.14.5, and 3.45.1 with Python 3.13.13.
3. Anonymisation (`AGENTS.md:44`, R107) applies to recorded fixtures, and to any inline value taken from a real machine, including the review's Linux outputs. P2-W1-T3's scan covers every file under `tests/fixtures/`, and, with `SUBMETER_SCAN_EVIDENCE=1` on the recording machine, the evidence under `docs/review/ground-windows/` and `docs/gates/` outside their `ci/` copies (7.3.3).
4. A test that has passed only on documentation-shaped or synthetic data says so in its docstring, and `docs/STATUS.md` names every provider that never ran on real hardware (`docs/17-build-prompt.md:342`).

#### 7.3.1 Every fixture and the task that builds it

| Fixture | Kind | Built by | Where | Used by | Runs on |
| --- | --- | --- | --- | --- | --- |
| Per-core CPU readings, one for each outcome of the interrupt and DPC decision | inline | P0-W1-T2 | `tests/test_probe_step1.py` | P0.4's decision rule | both |
| A `submeter top --json` list with a `restricted` row, and one without it | inline | P0-W1-T2 | the same | P0.5 | both |
| Probe 1's step results, one set per decision outcome | inline | P0-W2-T2 | `tests/test_probe_job_object.py` | P0.8's decision rule | both |
| A Task Scheduler read-back XML in the documented schema | documentation-shaped, inline | P0-W5-T2 | `tests/test_probe_autostart.py` | P0.10's comparison of settings | both |
| `cpu.stat` and `smaps_rollup` text, in the format of `docs/review/probes/a-linux/` | inline | P0-W2-T4 | `tests/test_probe_linux_costs.py` | P0.6, P0.7 statistics | both |
| A Windows FILETIME with a sub-second part, 134397792001234567 (22 November 2026 plus 0.1234567 s, 57 bits), and the value psutil's float gives back for it, 134397792001234568 (R56) | inline | P0-W4-T1 | `tests/test_psutil_provider.py` | the integer start stamp, and the record of why psutil's float is not used | both; the exact GetProcessTimes read on CI-W |
| `SYSTEM_PROCESS_INFORMATION` buffers | synthetic, built in the test | P0-W6-T2, then P2-W2-T1 | `tests/test_probe_bulk.py`, `tests/fixtures/bulk/` | P0.9's parser; R41, R70 | both, with the layout checks below; the live call on CI-W |
| Mutants | inline | P0-W6-T1 | `scripts/mutation_check.py` | R110 | the lead's checkout |
| `examples/submeter.toml`, `examples/rules.toml` | tracked files | exist; loaded by P0-W6-T1's `tests/test_examples.py` | `examples/` | I70 | both |
| Run files: live, final, lost, nested | inline, written with `store.runs` | P1-W1-T2, P1-W2-T3 | their test files | P1.5's parsing check, P1.6's subtraction, the lost state | both |
| Each command's expected `--json` fields | inline | P1-W1-T1, then each task that adds or changes a command | each command's own test file (7.1, rule 3) | S4 | both |
| A local page whose script writes a marker | file | P1-W3-T1 | `tests/data/page.html` | P1.9 | the owner's machine; CI-W if Edge is on the image |
| A soak CSV; a raw file written with `RawFile` in P2-W3-T1's schema, holding one gap tick across a sleep; a sleep file of two times; all built in the test | synthetic | P2-W5-T4 | `tests/test_soak_tools.py` | the checker for P2.1, P2.6, P3.5 | both |
| A planted fixture holding the user name | built in `tmp_path` | P2-W1-T3 | `tests/test_anonymise.py` | S5 | both |
| System counter values, including absent counters | inline files | P2-W2-T3 | `tests/fixtures/system/` | L06, L08; inputs to P2.3 | both; the live comparison on CI-W |
| A processor-information buffer with two efficiency classes, built from the test's own fixed-width structures | synthetic, built in the test | P2-W2-T3 | `tests/test_system.py` | `SystemInfo`; load per core class (Q11) | both |
| A Linux kernel thread (PF_KTHREAD in field 9 of `/proc/PID/stat`), another user's process, a psutil object aged as `docs/review/probes/verify-1/pid_reuse.py` ages it | inline | P2-W2-T2 | `tests/test_psutil_provider.py` | R64, R77, R123 | both for parsing; CI-L for the live reads |
| A pid-4 process, a vmmem process under an `opaque:` rule, raw rows for seeding | inline | P2-W2-T4 | `tests/test_attribution.py`, `tests/test_reconcile.py` | L05, L10, P2.3 | both |
| Readings of a nested process tree whose children are reaped | inline | P2-W3-T3 | `tests/test_sampler.py` | R40 | both for the logic; CI-L through the provider |
| cgroup increases against polled deltas; busy sums with and without interrupt and DPC time | inline | P2-W4-T2 | `tests/test_reconcile.py`, `tests/test_psutil_provider.py` | R60, R125 | both |
| A `/proc` mount line with `hidepid` | inline | P2-W5-T3 | `tests/test_cli_doctor.py` | R77, L10 | both |
| Recorded output of the bulk provider and of the psutil fallback, each with the system counters of the same ticks | recorded | P2-O1, with P2-W4-T3's recorder and its `--system` option | `tests/fixtures/recorded/<name>/` | P2-W6-T4's replay; S5 | both |
| The quiet fixture: 10 minutes of the bulk provider's readings and the system counters of the same ticks, its bound fixed before recording | recorded | P2-O1 | `tests/fixtures/recorded/quiet/` | P2.4 | both |
| Counter sets of a CPU-bound, a memory-bound and an I/O-bound load and of an idle machine, each at least 6 minutes long (one 5-minute verdict window, `docs/08-configuration.md:90`, plus 60 s) | recorded | P2-O1 | `tests/fixtures/recorded/` | P4-W1-T2's verdict fixtures; P4.1 | both |
| A counter set on battery, if the owner's machine is a laptop | recorded | P2-O1 | `tests/fixtures/recorded/` | the on-battery flag and multiplier | both |
| The 3-hour raw fixture, in two variants | synthetic | P3-W1-T2 | generated | P3.1; P3-W3-T1's rollup test | both |
| Raw stores over several days | synthetic | P3-W1-T2 | generated | P3.2; retention | both |
| A 5-minute raw file: 300 processes, 2 s ticks | synthetic | P3-W1-T2 | generated | P4-W3-T1; P4.5 in P4-W4-T1 and P4-O1 | both; the owner's machine |
| The 7-day store | synthetic | P3-W3-T3 | generated | P3-W4-T1's disk-budget order; P3.2 | both |
| The 30-day store | synthetic | P3-W3-T3 | generated | P4-W2-T4 and P4-W3-T2 (diff across weeks); P5-W2-T3 (export); P5-W3-T1 and P5.1 (report over a range) | both |
| Collector events: provider status, clock step, guard action, hardware change, and start events whose settings digest, rules digest, `SystemInfo` or version differ | inline | P3-W4-T4 | `tests/test_server_epochs.py` | epochs | both |
| A workload holding a vmmem process | inline | P3-W5-T4 | `tests/test_cli_doctor.py` | L05, R128 | both |
| An outer and an inner live group whose member lists share a pid, from a fake group provider | inline | P3-W2-T4 | `tests/test_collector_program.py` | the innermost-group rule (P95) | both |
| An hourly bucket whose `covered_s` is below half its width | inline | P3-W3-T2 | `tests/test_query.py` | buckets left out of trends (P99) | both |
| A parent run row of 10 CPU-s and a child row of 4 CPU-s with both run files deleted, and a parent row whose child is still a run file | inline, written with the history writers and `store.runs` | P3-W5-T1 | `tests/test_cli_cost.py` | R49 over history | both |
| The leak of 75 MiB an hour, the browser warm-up of `docs/07-analysis.md:24`, the staircase of 256 MB every 2 hours | synthetic, from seeds | P4-W1-T2 | `tests/tools/series.py`, `tests/fixtures/detectors/` | P4.2 to P4.4 | both |
| One fixture per rule of `docs/07-analysis.md:114-122`, and the Inconclusive cases; GPU-bound from synthetic GPU rows | recorded counter sets plus synthetic rows | P4-W1-T2 | `tests/fixtures/verdict/` | P4.1 | both |
| A trigger series and a quiet series for the runaway process count, as B12 defines it | inline | P4-W1-T4 | `tests/test_runaway.py` | P4.1 | both |
| A trigger and a quiet series for each built-in alert rule (`commit_fraction` above 0.90 for 2 minutes, `throttled` above 0 for 5 minutes, `overhead_fraction` above 0.03 for 5 minutes) and for one user rule on each per-workload metric (`cpu_cores`, `memory_bytes`, `processes`, `io_bytes_per_s`), each trigger crossing again inside the cooldown | synthetic, from seeds | P4-W1-T2 | `tests/fixtures/alerts/` | P4-W2-T3; P4.1 | both |
| A Linux series whose commit is None | inline | P4-W2-T3 | `tests/test_alerts.py` | R51 | both |
| Raw rows from which each metric series is read: commit used and limit (and NULL, as on Linux), the throttled flag, the `submeter` workload's CPU, and per-workload CPU, memory, processes and I/O | synthetic, written with `RawFile` in the test | P4-W1-T3 | `tests/test_query.py` | the alert metrics; P74 | both |
| A synthetic store in which each built-in alert rule and the runaway count fire once, and one in which none does | synthetic, written with `RawFile` | P4-W3-T3 | `tests/test_server_analysis.py` | P4.1 on stored rows | both |
| Two summaries across a change of sampling interval, and two across a daylight-saving change | inline | P4-W2-T4 | `tests/test_diff.py` | R131; row D10 | both; the daylight-saving case on CI-L only (`time.tzset`) |
| GPU Engine counters and adapter memory counters in the documented shape | documentation-shaped | P5-W1-T2 | `tests/fixtures/gpu/windows/` | P5.2, P5.3 | both |
| NVML results, DRM fdinfo files, amdgpu `gpu_busy_percent` | documentation-shaped | P5-W1-T3 | `tests/fixtures/gpu/linux/` | P5.2, P5.3 | both |
| Recorded Windows GPU readings | recorded | P5-O1 | `tests/fixtures/recorded/gpu/` | P5.2 | both |
| uPlot and its licence text, with their SHA-256 | vendored | P5-W1-T4 | `src/submeter/report/assets/` | P5.1 | both |
| A fake per-process GPU reading for two members of one workload | inline | P5-W2-T2 | `tests/test_collector_program.py` | GPU load per workload (P96) | both |
| `ReportData` holding one epoch boundary, a bucket marked as less than half covered, a kernel and a polled workload, the four fixed rows, an unreadable count, per-workload GPU load and each limit's note | inline | P5-W2-T1, P5-W3-T3 | `tests/test_report.py` | P5.1; P96 to P99 | both |
| A store in scrub mode with canary arguments, covering raw and hourly data | synthetic, built with the P3 generators | P5-W4-T1 | generated | P5.1 | both |

**Windows structures tested on Linux.** P0-W6-T2 and P2-W2-T1 test the bulk-snapshot parser on both systems against a buffer built from the parser's own ctypes structures. On Linux, `ctypes.wintypes.DWORD` and `ULONG` are 8 bytes and `ctypes.c_wchar` is 4 bytes (checked with Python 3.14.5); on Windows they are 4 and 2. A round trip through the same structures therefore passes on Linux whatever the layout. So the structures use fixed-width types (`c_uint32`, `c_uint64`, `c_uint16` for UTF-16 text), image names are decoded from bytes as UTF-16-LE, and the test asserts each structure's size and field offsets against the values documented for 64-bit Windows, with the source named in the test. The same applies to the Job Object accounting structures and the PDH structures, whose tests otherwise run on CI-W only.

**Canaries.** A canary is the string `CANARY-` followed by a new UUID, generated for each test run. It is planted in three forms:

- an argument shaped like a secret: `--password=CANARY-…`;
- a plain argument: `CANARY-…`;
- the name of the working folder: `CANARY-cwd-…`.

The scan searches the bytes of every `.db`, `-wal`, `-shm` and log file, every report, and every command output, as UTF-8 and as UTF-16-LE.

- In `exe_only` mode (the default, R96), no form of the canary may appear anywhere.
- In `scrub` mode, the secret-shaped canary may appear nowhere. The plain canary must appear in the raw file's `command` table, which proves the input reached the store and the scan is not searching for something that was never there. It must appear nowhere else: not in logs, reports, or the output of `cost`, `findings`, `export` or `why`.

Used by P1-W2-T3, P1-W3-T1 (P1.10), P2-W4-T1 (logs), P2-W6-T3, P3-W5-T1 (`cost --json` over a store written in `scrub` mode), P5-W2-T3 and P5-W4-T1.

#### 7.3.2 Synthetic stores

All synthetic stores are written through the product's raw writer (`RawFile`) and history writers. Their references are kept apart from that code, as described below.

- **The 3-hour raw fixture (P3-W1-T2).**
  - Coverage: 22:30 to 01:30 UTC, across two day files.
  - Two variants: ticks every 2 s on whole seconds, which include R53's sample ending at exactly 00:00:00.0; and ticks every 2 s at a 0.3 s phase with ±0.05 s jitter.
  - Contents: 50 processes in 5 workloads, from a seed (proposed).
  - A long gap sample (600 s, ending at 23:05:00 or 23:05:00.3). Without it, P3.1's 0.1% bound cannot catch a wrong bucket rule:
    - The end rule puts the whole gap sample in the hour 23:00 to 24:00. A midpoint rule would put it in 22:00 to 23:00, moving 600 s times the cores busy: 1,200 CPU-s at 2 cores, 17% of a 7,200 CPU-s hour.
    - An ordinary 2 s sample moves at most 4 CPU-s at 2 cores, 0.056% of that hour, which the bound does not catch.
  - The generator also writes a manifest of the CPU it generated per workload per hour, keyed by sample end time, computed without SQLite. P3-W6-T1 checks two things: the raw sum by end time equals the manifest within floating-point rounding, and `rollup_1h` equals the raw sum within 0.1%.
- **Raw stores over several days (P3-W1-T2).** Day files with set dates and sizes, for `expired_raw`, the retention pass and the disk budget. P2-W5-T1 tests the collector's 7-day cap with raw files it writes in its own test, because it comes before this generator.
- **The 5-minute raw file (P3-W1-T2).** 150 ticks at 2 s with 300 processes, and system rows that fill every catalogue column P2-W3-T1 defines. P4-W3-T1 uses it for its regression timing, and P4-W4-T1 and P4-O1 for P4.5. The generator takes the process count, duration and cadence as arguments.
- **The 7-day store (P3-W3-T3).** It holds:
  - hourly history for 7 days, and raw files for the last 2 days;
  - runs, one of them nested;
  - sessions: two that overlap, one that was never stopped, and one longer than raw retention;
  - findings.

  A second variant sizes the raw files so that the store exceeds `disk_budget`, for the trimming order of P3-W4-T1.
- **The 30-day store (P3-W3-T3, run for 30 days).** It holds hourly history beyond the 2 raw days, one rules change (an epoch), one change of sampling interval, and the daylight-saving change of 25 October 2026 under the Europe/London rule that `tests/test_analysis.py:20` uses. It serves three uses: the tier choice for windows that start 2 to 30 days back (`docs/13-build-list.md:106`), the diff of two weeks, and the report and export over a range that spans raw and hourly data. "A 30-day range loads in under one second" is the version 1.1 API gate (`docs/17-build-prompt.md:279`) and is not tested in version 1.
- **The leak series (P4-W1-T2).** The parameters are those B14 fixes. B14's proposal: a row every 30 s, uniform noise of ±40 MiB per row, 200 seeds; the warm-up over 6 h; the staircase of 256 MB every 2 h. The generator's own test checks that the leak's mean slope over 2 h is within 1% of 78,643,200 bytes an hour. If 200 seeds of all three series take longer than 60 s on a runner, the full run carries `soak` and 20 seeds run on every push (proposed).

#### 7.3.3 Recorded provider output

- **The recorder** is `tests/tools/record_fixture.py` (P2-W4-T3), run as `uv run --directory tests python -m tools.record_fixture <module>:<class> [--system <module>:<class>]`. It records N ticks of the readings of any provider that implements one of P2-W1-T1's protocols, the GPU providers included; with `--system` it reads a process provider and a system provider on each tick and writes both readings of that tick into the same fixture. It writes JSON Lines, one record per line, serialised by the record's own Pydantic model (`model_dump(mode="json")`) after `privacy.anonymise` (P2-W1-T3). It refuses to write a fixture in which the scan finds the current user or host name.
- **Beside each fixture** go two files:
  - `manifest.json`: the provider or providers and their capability status, the Submeter commit, the digest of the rules file used for `expected.json`, the UTC date, the Windows build, the logical cores, the process count, the tick count and interval, and what the machine was doing (quiet, CPU-bound and so on). For the quiet fixture it also holds the bound on the not-seen-by-polling share, fixed before recording.
  - `expected.json`: the values P2-W6-T4's replay compares against, written at recording time. For a fixture with process readings and system counters: for each tick, the CPU of each workload and the six reconciliation terms, computed by the sampler, the attribution of `examples/rules.toml`, `aggregate` and `reconcile`. For any other fixture: the parsed readings.
- **What replay proves.** P2-W6-T4 loads each fixture of the bulk, system and psutil providers with today's records and runs the portable pipeline on it (sampler, attribution, `aggregate`, and `reconcile` fed the process readings and the system counters of each tick) on both runners; P5-W4-T1 replays the GPU fixtures for P5.2. That shows the records still parse and the logic gives the results it gave at recording time. It does not show the parser is right, because the expected values came from the same code. Correctness on real Windows comes from the live comparisons on CI-W (CreateTime against GetProcessTimes in P2-W2-T1; per-core busy plus idle against elapsed time in P2-W2-T3) and from the owner's runs.
- **Raw OS buffers are not recorded.** The bulk snapshot's buffer holds image names, which cannot be anonymised without rebuilding the buffer. Its parser is tested on synthetic buffers (7.3.1) and on the live call on CI-W.
- **Size.** A 10-minute fixture at 2 s with 300 processes holds 300 ticks of 300 records. At about 300 bytes a record as JSON (an estimate, not measured), that is about 27 MB. So a fixture file over 1 MB is stored gzip-compressed with the standard library (P2-W4-T3), and the anonymisation scan decompresses it before searching (P2-W1-T3).
- **When a record changes.** A later phase that adds an optional field leaves old fixtures valid, because a missing optional field loads as None. A rename or a removal makes them fail to load. The task making that change cannot edit `tests/fixtures/recorded/`, which only owner tasks own (section 4.2), so it raises a change request (section 4.3). Then either the owner records again, or a task of size S migrates the files in a wave in which no owner task holds the folder.
- **The anonymisation scan** (P2-W1-T3). It reads `tests/fixtures/` always, and `docs/review/ground-windows/` and `docs/gates/` outside their `ci/` copies of the runners' output only with `SUBMETER_SCAN_EVIDENCE=1`, which the owner tasks set on the recording machine. It matches the user name, the host name, the domain name and the home folder path as whole tokens, case-insensitively, in UTF-8 and UTF-16-LE. On hosted runners the names are expected to be `runner` on Linux and `runneradmin` on Windows, to be confirmed in the first CI run with `whoami`. Whole tokens keep such a name from matching inside a longer word, but `runner` is also a whole word in the evidence the lead writes (`verdict.md` quotes the reviewer, and criteria such as P2.1 (7) name "the runner"), so CI scans `tests/fixtures/` only. The run that counts is the one on the recording machine before the commit (S5).

### 7.4 The load generator

P1-W1-T3 builds it in `tests/tools/loadgen/`, and it runs as `uv run --directory tests python -m tools.loadgen <mode> … --report FILE`. It is the reference for P1.1, P1.3, P1.6 and P2.2 (R83). It therefore imports nothing from `submeter`, which an AST test checks. It is built in a different task from the launcher (P1-W2-T1) and the collector (P2-W5-T1), and the P1 gate harness is built by a builder who built neither the launcher nor the generator.

| Mode | What it does | What it reports | Used by |
| --- | --- | --- | --- |
| `spawn` | N children, each busy for a set CPU time and alive under a set wall time, P at a time | for each child: pid, user and kernel CPU (GetProcessTimes on a handle held until the end on Windows; the rusage from `os.wait4` on Linux) and exit code; their sum; the generator's own CPU | P1.1 (500 children, 50 ms each, alive under 1 s, 8 at a time); P1.6 |
| `burn` | one process at a set share of a core | its own CPU seconds every 1 s, with a UTC time and a monotonic time (GetProcessTimes on itself; `getrusage(RUSAGE_SELF)`) | P2.2 (5, 15, 25, 50 and 100% of a core); P3.3 (120 s, tagged); load in the soaks |
| `background` | leaves behind a process that burns a set CPU time after the generator has exited | that process's own total, written to a file when it ends | P1.2, P1.3; the tagged run inside each soak, whose left-behind process lives at least 30 s so that on CI-W a holder exists for the 10 s monitor to sample (P2.1 (6)) |
| `idle` | holds N sleeping processes | the count | P2.1, P3.5: brings the runner to at least 300 processes |
| `leak` | private bytes growing at a set rate or in steps | its own private bytes over time | no gate in version 1: built because `docs/13-build-list.md:48` and `docs/17-build-prompt.md:323` ask for a controlled leak, and proved by P1-W1-T3's own test (a set rate within 10%, and each step); the leak gate uses seeded series (P4-W1-T2) |
| `memory` | commits and touches memory up to a set share of the commit limit, then holds it | its own private bytes and the share it reached | P2-O1's memory-bound counter set, if the owner agrees (Q14) |
| `breakaway` | a direct child created with CREATE_BREAKAWAY_FROM_JOB | the error code | P1.7 |
| `grandchild` | a native chain through `cmd.exe /d /c start "" /b`, and through node then bash where both exist | `IsProcessInJob` of the grandchild | P1.4, P1.8 |
| `io` | reads and writes a file at a set rate | its own byte counts (GetProcessIoCounters; `/proc/self/io`) | P2-O1's I/O-bound counter set; I/O attribution checks |

- **Busy loops spend CPU time, not wall time.** Each child spins until `time.process_time()` has advanced by its set amount. A loaded runner then lengthens the elapsed time without changing the CPU each child uses.
- **Children run the base interpreter.** On Windows, a virtual environment's `python.exe` is a redirector, not the interpreter (Python's `venv` documentation: "Changed in version 3.7.2: Windows now uses redirector scripts for `python[w].exe` instead of copying the actual binaries"). The redirector is expected to start the base interpreter as a second process; to be confirmed on CI-W, including for environments uv creates. A child started with `sys.executable` would then be two processes. GetProcessTimes on the handle the generator holds would measure the redirector, not the busy interpreter, and the job's process count would be double. So children run the base interpreter (`sys._base_executable`) with `-I` and the standard library only. P1-W1-T3's test that each child reports at least 40 ms catches the error if it is made.
- **The report** is one JSON object per run, with schema `loadgen.report/1` (proposed). It holds the mode, the arguments, the UTC and monotonic start and end, the generator's own CPU, and the figures each mode reports.
- **Checks of the generator itself**, beyond P1-W1-T3's card:
  - On Linux, the sum of each child's CPU from `wait4` equals the increase of `getrusage(RUSAGE_CHILDREN)`, which is a second kernel path, within 1 ms a child (proposed tolerance).
  - On Windows, each child's own last reading just before exit is at most one clock tick (15.6 ms) below the reading taken on the held handle after exit.
- **Clock-tick counting.** Windows may count per-process CPU in clock ticks of about 15.6 ms. Probe 1's step g (P0-O2) shows whether job totals cluster at multiples of it. The reference and the job read the same per-thread times, but if step g shows clustering, the child busy time of P1.1 is reviewed before P1-W3-T1 is dispatched.

**The soak tools** (P2-W5-T4) are the other reference.

- The monitor reads every Submeter process from outside every 10 s. On Windows that set includes console-script launchers and virtual-environment redirectors (to confirm on CI-W, as above).
- The checker reads raw files with plain SQL. Its SQL depends on the raw schema, so it is built in P2-W5, after P2-W1-T2 and P2-W3-T1 have fixed the columns it reads (`interval_s`, `gap`, `awake_s`, `expected_s` and `cadence`), and its own tests run it on a raw file written with `RawFile`. P2-W6-T2's dry run then runs it on a raw file the collector wrote.
- On CI-W every process runs with the runner's administrator token (R118). The monitor records elevation there, and elevation is judged only on the owner's machine, where the checker runs with `--judge-elevation` (P2-W5-T4).

### 7.5 The CI matrix

| Workflow and job | Trigger | Runners | Python | Steps | Built by |
| --- | --- | --- | --- | --- | --- |
| `ci.yml`, checks | push to every branch (`docs/15-phases-and-decisions.md:25`) | `windows-2025` and `ubuntu-24.04` (proposed; P0-W1-T1 confirms the labels) | 3.13; 3.14 as well if the owner chooses (Q2) | with 3.13: `uv sync --locked`, the six other `AGENTS.md` commands, pytest with the four markers deselected, each check run even after an earlier one failed (7.2); with 3.14, if chosen: `uv sync --locked` and pytest; on both: `git status --porcelain` empty | P0-W1-T1 |
| `ci.yml`, Linux measurements | the same | `ubuntu-24.04` | 3.13 | the cgroup and PSS scripts, output kept as artefacts and labelled "CI-runner figure" | P0-W2-T4 |
| `soak.yml`, `soak` | manual dispatch; push to `gate/*` and to `soak/*` | both | 3.13 | 300 processes, the 30-minute schedule, `submeter run` of the generator's `background` mode, monitor and checker, artefacts `soak-windows` and `soak-linux` | P2-W6-T2, then P3-W6-T2, P4-W4-T2, P5-W3-T2 |
| `soak.yml`, `soak-tests` | the same; runs beside `soak` on its own runners | both | 3.13 | `uv run pytest -m soak` with `SUBMETER_GATE_DIR` set; artefacts `soak-tests-windows` and `soak-tests-linux` | P2-W6-T2 |
| The owner's machine (not CI) | each owner task | Windows 11, as the signed-in standard user | whichever interpreter uv picks (there is no `.python-version` file) | `uv run pytest`, then `uv run pytest -m "owner_machine or session or hardware"`, then the owner task's own procedure | the owner tasks |

**Python versions.** `pyproject.toml:5` requires 3.13 or later. Ruff's `target-version = "py313"` (`pyproject.toml:36`) and mypy's `python_version = "3.13"` (`pyproject.toml:44`) make both tools check against 3.13 whatever interpreter runs them, so only pytest needs a second interpreter.

- 3.13 is the oldest version the brief allows (`docs/17-build-prompt.md:36`, R124).
- 3.14 is what uv chose on the review machine with no pin (3.14.5), so it is the likely interpreter in a builder's working copy.
- uv 0.11.14 lists 3.15 only as `3.15.0b1`. Whether to add a stable 3.15 when one exists is the owner's decision, because a new interpreter can lack wheels for pydantic-core or psutil.

P0-W1-T1's card installs 3.13 only, the default of Q2 in section 11, which asks whether to add 3.14.

**mypy (R134).** Both runners run all three mypy commands of `AGENTS.md:29-31`, so on every push Windows-only code is type-checked on Linux and Linux-only code on Windows. On a runner every run starts with an empty cache. In a warm local checkout, the two `--platform` runs replace each other's entries in the one shared cache, so each takes 6.5 to 6.7 s, and the seven commands take 16.8 s. With `MYPY_CACHE_DIR` set to a separate folder for each platform, each run keeps its own cache warm (0.48 to 0.51 s) and the commands stay as `AGENTS.md` writes them; mypy 2.4.1 reads that variable at `mypy/main.py:1485`. This is for the lead's checks after each merge (stage 3).

**The pytest command in CI:**

```
uv run pytest -m "not owner_machine and not session and not hardware and not soak" -rfEsxX --durations=25 --continue-on-collection-errors --basetemp=<runner temp folder>/pytest
```

**Other CI settings** (P0-W1-T1 builds those of `ci.yml`, P2-W6-T2 those of `soak.yml`):

- `uv sync --locked`, so that a `uv.lock` out of step with `pyproject.toml` fails. `AGENTS.md:26` writes `uv sync`.
- Every step after `uv sync --locked` runs with `if: ${{ !cancelled() && steps.sync.outcome == 'success' }}`, and pytest with `--continue-on-collection-errors`, so that a test-only commit's run shows every check's result (7.2). GitHub Actions otherwise skips a job's later steps once one fails, and pytest otherwise stops at the first collection error. The job still fails when any step failed.
- Actions pinned by commit, and the uv version pinned (the review used 0.11.14).
- No `cancel-in-progress` on task branches (7.2).
- Job time limits: 30 minutes for `ci.yml`; 120 minutes for `soak.yml`'s `soak` job, which covers P3-W6-T2's wait for minute 40 of the hour (up to 60 minutes), the 30-minute soak and about 10 minutes of set-up and checking; 150 minutes for its `soak-tests` job, whose cases are summed below. A hosted job may run for up to 360 minutes (7.6). The two jobs run at the same time, on separate runners.

  | Case marked `soak` | From | Time, at most |
  | --- | --- | ---: |
  | Kill test, 50 trials of 1 to 60 ticks at 1 s, 100 start-ups at about 5 s (P2-W6-T1) | P2 | 60 min |
  | P2.2's 10-minute burners, with set-up (P2-W6-T3) | P2 | 12 min |
  | The soak driver's dry run, extended in each phase (P2-W6-T2, P3-W6-T2, P4-W4-T2, P5-W3-T2) | P2 | 5 min |
  | P3.3's two 120 s trials with their restarts (P3-W6-T1; CI-W only) | P3 | 6 min |
  | The 200-seed leak runs, if they take longer than 60 s (P4-W2-T1, P4-W4-T1; 7.3.2) | P4 | 15 min, a budget, not a measurement |
  | `uv sync` and the interpreter | P2 | 3 min |
  | **Sum at G2 / G3 / G4 and G5** | | **80 / 86 / 101 min** |

  The 49 minutes left under 150 at G4 and G5 are for Windows, where starting a Python process is expected to be slower and nothing has been timed. If the CI time of a case passes its row, the task that owns it reports it and the lead raises the limit with a plan change, up to 360 minutes, or splits the cases over two jobs.
- Artefacts: pytest output, the gate evidence the harnesses write to the folder `SUBMETER_GATE_DIR` names, and P0-W2-T4's figures. GitHub keeps artefacts and logs for a limited period, 90 days by default, so the gate step copies what each gate needs into `docs/gates/P<n>/` (`docs/review/ground-windows/ci/` for P0).
- The soak workflow needs a run before merge. A task that adds or changes `soak.yml` or a `soak` test also pushes its branch as `soak/<task id>`. In P2-W6, the wave that creates `soak.yml`, the kill test (P2-W6-T1) and P2.2's 10-minute case (P2-W6-T3) have no workflow at their base commit, so before merge they run only as their short unmarked variants, and in full in the soak workflow at the gate. GitHub is expected to offer manual dispatch only for a workflow whose file is on the default branch (to confirm in GitHub's documentation when P2-W6-T2 is built). Until then, a push trigger is the only way to run a new or changed `soak.yml` before merge.
- The first runs record facts about the runners that nobody has checked:
  - the user name (`whoami`);
  - the process count;
  - whether CI-W places the job's own process in a Job Object (`IsProcessInJob`, from P0-W2-T2's smoke run);
  - whether Chrome or Edge is on each image (P5-W4-T1 needs one, and P1.9 can run on CI-W only if Edge is there);
  - the SQLite version each interpreter carries;
  - the time of the seven checks on CI-W, the first Windows timing of this plan.

**How the P5 browser check works without a new dependency.** Chrome DevTools needs a WebSocket client, which the standard library lacks. The check runs the browser headless on the report file with `--dump-dom`, with every request sent to a closed local port, and with a NetLog file (`--log-net-log`) that lists every request it attempted. The test passes when:

- the NetLog lists no request other than the report file;
- the dumped DOM holds the canvases the inline script creates (with a wrong CSP hash the script does not run, so they are absent);
- the browser's own log, written to standard error, holds no Content Security Policy message.

The exact switches are confirmed against current Chromium documentation when P5-W4-T1 is built.

### 7.6 What cannot be tested here

"Here" means the hosted runners and any build machine other than the owner's Windows computer.

| What | Why not here | Where it is tested instead | If nowhere |
| --- | --- | --- | --- |
| Reads as the unprivileged user: Restricted counts and share, refused opens, command lines read with limited access (R126) | CI-W is an administrator with UAC off; CI-L has passwordless sudo (R118) | `owner_machine` tests at each gate; P0-O1 (restricted count and share); P2-O2 (the bulk provider as the standard user) | — |
| Fixed rule 2 at run time: no Submeter process holds an elevated token | the same | the soak monitor in P2-O2 and P5-O2 | the static check on every push (P0-W3-T3) covers asking to elevate |
| Private folders (R100) | mode bits mean nothing on Windows (`tests/test_files.py:101`) | `icacls` in P0-O1 | — |
| The logon task, registered and started at sign-in | runners have no interactive session (R118) | P0-O2 (probe 3); P3-O1 | — |
| Managed-computer policy: Defender ASR events, AppLocker, Device Guard, folder redirection or syncing | runners carry no such policy | P0-O1, P0-O2, and the Defender log again in P2-O2; `platform_check.py`'s file locations line and P0-W1-T2's check of the two folders' redirection and syncing | — |
| Job Objects under the owner's shells: Windows Terminal, the VS Code terminal, Claude Code's shell | the runner's own Job Object state is unknown | P0-O2, probe 1 step b; CI-W's smoke run records the runner's state | — |
| A Chromium-based browser under the job; grandchildren through node and bash | Edge's single instance and the computer's policy; node and bash may be absent (B16) | P1-O1 | if B16 keeps node and bash off the machine, P1.8 is not tested, and `docs/STATUS.md` says so |
| Suspend and resume | runners never sleep | P0-O1 (the sleep check of `docs/reference/windows-priorities.md` section 5); P2-O2 (one sleep of at least 5 minutes) | injected clocks in every other test |
| A real wall-clock step | stepping the clock needs root on Linux (the review's Not checked list, `docs/review/01-adversarial-review.md:1608`) and the right to change the system time on Windows, which a standard account may not hold | nowhere in version 1; injected clocks (P0-W4-T1, P2-W4-T4); L13 is shown beside the numbers | a disposable runner could step its own clock with its administrator rights; not planned, because it puts an elevated step into the tests; the owner may ask for it |
| The on-battery flag and the battery multiplier; frequency throttling | runners have no battery and are not expected to throttle | `hardware` tests on the owner's machine, if it is a laptop and if it throttles under the CPU-bound load | fixtures only, stated in `docs/STATUS.md` |
| Windows GPU load and adapter VRAM | runners have no GPU (R118) | P5-O1 records from the owner's GPU (model unknown) | fixtures only, if the owner's machine gives no readable source (B18) |
| NVIDIA and AMD GPUs on Linux | no machine available here has either | documentation-shaped fixtures (P5-W1-T3) | never run on real hardware, stated in `docs/STATUS.md` (`docs/17-build-prompt.md:342`) |
| Intel GPUs on Linux (DRM fdinfo) | runners have none | the review's Linux machine has an i915 GPU; recorded only if a build session runs there | fixtures only otherwise |
| A Windows installed in another language | runners, and probably the owner's machine, are in English | a test intercepts the counter calls and checks that every counter is added by its English name (P2-W2-T3, P5-W1-T2) | a non-English Windows is not tested |
| Power loss | — | not tested (`docs/15-phases-and-decisions.md:41`, R89) | the promise is loss only since the last checkpoint |
| 24-hour behaviour: memory growth, antivirus over a day | a hosted CI job stops after 6 hours | P2-O2; P5-O2 if the owner keeps it | — |
| The owner's own process mix and count | runners reach 300 processes only with idle children | P0-O2 runs probe 2 at the owner's count; the owner's soaks | — |
| `why` under 2 s, cold, on the owner's machine | shared runners give noisy times (P4.5) | P4-O1 | CI records the time and fails only above 4.0 s (P4-W3-T1) |
| Antivirus holding new files open and slowing many small writes | the runners' antivirus settings are unknown | P0-O1 (the "raw file on disk" line); the owner's soaks; the pilot wave on the build machine | the retry on a refused delete is tested with an injected refusal |
| Windows local days across a daylight-saving change | `time.tzset` exists only on POSIX (`tests/test_analysis.py:17-24`) | CI-L, with a TZ rule string and no zone files | not tested on Windows |
| Many working copies on one Windows machine: the 260-character path limit, locked virtual environments | a runner has one checkout at a short path | the pilot wave (P0-W1) on the build machine. The longest tracked path is 63 characters today (`git ls-files`), which leaves 196 for the folder that holds a working copy | — |
| Linux desktops: other users' processes, `hidepid`, a desktop's cgroup tree | the runner is a service with no user session (R118) | fixtures (P2-W2-T2, P2-W5-T3); P0-W2-T4's figures are labelled as CI-runner figures | beyond CI, Linux has its own pass after version 1 (`docs/reference/windows-priorities.md:103`) |
| The WSL2 or Docker Desktop VM process on a real machine | runners cannot run WSL (R118) | fixtures with a vmmem process (P2-W2-T4, P3-W5-T4); the owner's `doctor` output if WSL is installed | — |


## 8. Risk register

Each risk has an id (K1 to K49), a likelihood, an impact, the sign that shows it is happening and where that sign is read, and the response. Where a response needs a choice, the choice goes to the owner as sections 5.6 and 11 do; the lead records it and does not make it. Task ids are those of section 3; B and C ids are those of sections 5.6 and 5.7.

### 8.1 How to read it

- **Likelihood.** High: expected unless the response is taken. Medium: no evidence either way, or evidence from Linux only. Low: needs an unusual combination of conditions.
- **Impact.** High: a fixed rule broken, a number shown wrong, a gate failed on the owner's machine, or a phase planned again. Medium: a task done again, a wave held, or a gate run again. Low: a session or a day of elapsed time lost, or a figure that needs a label.
- **[Linux].** Every figure the review measured came from its Linux machine: Ubuntu 24.04.5, kernel 7.0, 8 logical cores, about 450 processes, Python 3.14.5, psutil 7.2.2 (`docs/review/01-adversarial-review.md:11-15`). This register marks each such figure [Linux]. No [Linux] figure decides a Windows choice; those choices rest on the output saved from the owner's machine under `docs/review/ground-windows/` (R137; `docs/15-phases-and-decisions.md:23`). Figures from the hosted runners do not decide them either, because those runners are administrators on other hardware (R118).
- **Shares of one core** are CPU milliseconds per tick divided by the interval. At the default intervals (`docs/08-configuration.md:57-58`) the budget is 3% at 2 s, which is 60 ms of CPU per tick, and 1% at 5 s, which is 50 ms per tick. A "per 300 processes" figure is the measured figure scaled linearly from the 447 to 449 processes measured, as the review scaled it.

### 8.2 The Python or Rust collector (decision B2)

#### The rule R79 set

The owner ruled R79 with its recommended option: the trigger is the overhead budget itself, not the earlier rule of 10 ms for one full sample (`docs/review/02-rulings.md:60`). As now written in the brief (`docs/11-language.md:23-24`, `docs/17-build-prompt.md:63`):

- Probe 2 runs the collector (snapshot, deltas, attribution and raw-store writes) for 10 minutes on the owner's Windows machine, with the provider that will ship (the bulk snapshot) and with the psutil fallback. It reports the process count and the cost per process, so that the figures for 300 processes can be derived.
- Switch the collector to Rust if, for 300 processes at the default intervals with the shipping provider, its CPU time is over 3% of one core at 2 s or over 1% at 5 s, or its private bytes are over 80 MB (83,886,080 bytes). The psutil fallback's figures are reported, not judged. The brief says "stop and tell me": the owner decides, and the decision is recorded as B2.
- Under I56 the collector alone is compared with the whole budget, because neither the server nor a holder exists in P0. The 80 MB is the collector's part of the 150 MB (157,286,400 bytes) for collector and server together (`docs/review/02-rulings.md:215-216`).

Two things follow from the rule and the numbers below.

1. Since R142 every process is read every tick at either cadence (`docs/08-configuration.md:68`), so a tick costs about the same at 2 s and at 5 s. The idle limit, 50 ms per tick at 300 processes, is the one a tick reaches first.
2. A Rust collector removes only the work done in the interpreter: parsing the snapshot, deltas, attribution and the calls into SQLite. Time spent in the kernel, inside NtQuerySystemInformation and in file writes, stays; the brief expects that time to be most of the tick on Windows (`docs/11-language.md:7`). The owner can judge whether Rust would bring the collector inside the budget only if probe 2 reports the tick's user time and kernel time apart, which P0-W6-T2 does, with the raw store's share of the tick (gate P0.9).

The earlier rule shows why R79 replaced it. On one machine it said "stay" for a reader of 7.5 ms per 300 processes (stat only) and "switch" for one of 15.5 ms (stat, statm and io) whose whole collector was inside the budget [Linux] (`docs/review/probes/b-measurement/model_tables.out.txt`, section 4).

#### What R137 says must be measured on Windows first

R137 (`docs/review/01-adversarial-review.md:1281-1289`): before the Rust decision, run these on the owner's Windows machine as the signed-in user and save them under `docs/review/ground-windows/`.

| R137 item | Plan task that produces it | Evidence |
| --- | --- | --- |
| The checks: four when R137 was written, the seven of `AGENTS.md:26-32` now | P0-O1, following P0-W1-T2's procedure | `docs/review/ground-windows/step1/` |
| `scripts/platform_check.py` | P0-O1, and again in P0-O2 | `step1/` and `probes/` |
| A bulk-snapshot prototype timed over at least 20 runs, with the process count | P0-W6-T2, run in P0-O2: each 10-minute run is 300 ticks at 2 s or 120 ticks at 5 s | `docs/review/ground-windows/probes/` |
| A nested Job Object, with accounting read after the children exit | P0-W2-T2 steps b and c, run in P0-O2 | `probes/` |
| The Restricted count and its CPU share | P0-W1-T2's `restricted_share.py`, run in P0-O1 | `step1/` |

`docs/15-phases-and-decisions.md:23` and `docs/17-build-prompt.md:337` add that the plan marks the review's figures as Linux figures, and that every phase 0 choice, the Rust choice among them, rests on the owner's output. B2 is therefore recorded only from files under `docs/review/ground-windows/probes/`. The P0 gate reviewer should check that the B2 row cites such a file and no CI-W or [Linux] figure.

#### The numbers measured in this review [Linux]

All at 300 processes, scaled linearly from the count measured. The R79 column applies the rule as if that reader were the shipping provider. On Linux in version 1 none is: Linux runs psutil, held inside the budget by the overhead guard (L04).

| What was measured [Linux] | Per tick, 300 processes | At 2 s | At 5 s | R79's rule | Source |
| --- | ---: | ---: | ---: | --- | --- |
| psutil snapshot alone (median 111.2 ms, worst 121.8 ms for 447 processes, 20 runs) | 74.6 ms | 3.73% | 1.49% | snapshot only, not judged | `docs/review/probes/measure/snapshot_cost.out.txt` |
| Direct `/proc` read, stat only (median 11.2 ms for 448) | 7.5 ms | 0.38% | 0.15% | snapshot only | same |
| Direct `/proc` read, stat, statm and io (median 23.2 ms for 449) | 15.5 ms | 0.78% | 0.31% | snapshot only | same |
| Baseline tick without storage, psutil (median 125.9 ms for 447) | 84.5 ms | 4.23% | 1.69% | over both | same |
| Whole tick with the raw store, direct `/proc` (modelled from the runs above) | 36.0 ms | 1.80% | 0.72% | inside both | `docs/review/probes/b-measurement/model_tables.out.txt`, section 3 |
| Whole tick with the raw store, psutil (17.0 s of CPU over 120 ticks, 141.7 ms a tick for 447) | 95.1 ms | 4.76% | 1.90% | over both | `docs/review/probes/measure/collector_footprint.out.txt`; model_tables, section 3 |
| Collector memory, psutil and raw store, after 120 ticks | resident 39 MB, unique 35 MB, proportional 36 MB | | | inside 80 MB | collector_footprint |
| One USS/PSS round for the 25 largest processes, which held 8.23 GB; one round every 30 s (`uss_interval`) at either cadence | 241.6 ms a round | 0.81% | 0.81% | outside the trigger, inside the budget | `docs/review/probes/a-linux/smaps_cost.out.txt`; R76 |

Other figures that bear on the decision:

- With the direct reader, the work in Python after the snapshot (deltas, attribution and raw-store writes) was about 20 of the 36 ms [Linux]. With psutil, the snapshot itself was about 75 of the 95 ms (`docs/11-language.md:9`).
- For a tick costing c ms, the shortest intervals inside the budget are c ÷ 0.03 active and c ÷ 0.01 idle. For psutil's 95.1 ms that is 3.2 s and 9.5 s [Linux], the intervals `docs/10-known-limits.md:12` states for Linux in version 1. For the direct reader's 36.0 ms it is 1.2 s and 3.6 s [Linux].
- What the Linux figures support: a Python collector whose read of 300 processes costs about 15 ms meets both limits at the default intervals, 14 ms per tick under the idle limit (36.0 ms against 50 ms). A collector that reads through psutil does not: 95.1 ms per tick is 1.9 times the idle limit.
- What they do not support: any figure for the Windows bulk call, for Python on the owner's processor, for what Defender adds to the store's writes, or for the private bytes of a Python process on Windows. None of these exists until P0-O2.

#### What the P0 figure leaves out

Probe 2 drives the baseline sampler, attribution and raw store. The version 1 collector does more each tick, and the server and holders share the budget. The budget is therefore measured again at P2.1 and P2.6 (P2-W6-T2, P2-O2), at P3.5 (P3-W6-T2), in P4-W4-T2 and P5-W3-T2, and in P5-O2 if the owner keeps it. Not in the P0 figure:

- the Windows system counters read every tick through PDH (P2-W2-T3);
- the version 1 raw schema: a nullable column for every catalogue metric, event rows and the reconciliation terms (P2-W3-T1), against the baseline's 120 bytes a row [Linux];
- command lines read once per new process (P2-W3-T4) and the USS round at `uss_interval`, which is in the budget but not in the trigger (K2);
- live group reads each tick (P3-W2-T4) and the GPU counters at `gpu_interval` (P5-W2-T2; K12);
- the server's passes and the holders (I56; K4).

#### The decision point and the responses

The decision point is the P0 gate, on P0-O2's output. P1 does not depend on it: the launcher, run files and `cost --run` need no collector (`docs/15-phases-and-decisions.md:31`), so a Rust outcome stops P2 only (section 3.6). There is a second decision point at the P2 gate: if the version 1 collector breaks the budget in the owner's 24-hour soak (P2.6) where the prototype did not, B2 goes back to the owner with both figures.

| Probe 2 on the owner's machine (bulk provider, 300 processes) | Response |
| --- | --- |
| Inside 60 ms per tick at 2 s and 50 ms at 5 s, and under 83,886,080 private bytes | Python. The B2 row records the shares at 2 s and at 5 s, the private bytes, the USS round, the default `uss_interval` at which the tick and the USS round together stay under 1% at 5 s (K2), and the share of the budget left for the server and holders (K4). P2 proceeds as planned |
| CPU over the limit, mostly user time | Stop and tell the owner. The brief gives two options: the Rust collector, its stated fallback (`docs/11-language.md:16`); or Python with longer default intervals, because probe 2 also decides the default intervals (`docs/15-phases-and-decisions.md:18`). The probe's tick cost c gives those intervals as c ÷ 0.03 and c ÷ 0.01 |
| CPU over the limit, mostly kernel time | Stop and tell the owner that a Rust collector would not remove most of the excess. Longer default intervals are the other option the brief gives |
| Private bytes over 83,886,080 | Stop and tell the owner, with the private bytes after start-up and after 10 minutes, so that growth is told apart from start-up size |
| The bulk call does not work for the standard user | The psutil fallback would ship, and R79 does not judge its figures. [Linux] it costs 95.1 ms per tick, 1.9 times the idle limit. Stop and tell the owner: no rule covers this case |

If the owner chooses Rust, section 3.6 already says the build stops before P2 and P2 is planned again. That replanning must cover:

- **Dependencies.** A Rust toolchain and its crates are new dependencies and need the owner's approval (`AGENTS.md:49`). The toolchain must install without administrator rights on the work computer. rustup installs per user, but the default Windows target links with Microsoft's C++ build tools, whose installer may need administrator rights (suspected; to be checked in rustup's current Windows documentation before the choice is put to the owner). A collector binary built on the Windows runner would avoid installing it on the owner's machine.
- **Two implementations.** Redaction and the attribution rules would exist in Rust in the collector and in Python for `submeter rules test` (P3-W3-T4) and for `top`, which takes its own snapshots (C1). Command lines are redacted before they are stored (`AGENTS.md:43`), so one set of test cases must pass in both languages, and C1 goes back to the owner.
- **What stays.** The raw schema is the contract between collector and server (`docs/11-language.md:11`), so P2-W1-T1's records, P2-W3-T1's schema and the Python raw readers stay, as do the soak tools, the anonymiser, the control files and logs, and the P2-W6 harnesses, which drive the collector from outside.
- **What is rewritten.** The sampler part of P2-W1-T2, cadence and guard (P2-W3-T2), the sampler (P2-W3-T3), anchored stamps (P2-W4-T4), the collector program (P2-W5-T1), and the attribution and reconciliation the collector runs (P2-W2-T4 and the reconciliation part of P2-W4-T2). The providers (P2-W2-T1, P2-W2-T2, P2-W2-T3, P2-W3-T4) are rewritten for the collector and kept in Python as well only if C1 stands.

### 8.3 Measurement and the overhead budget

| Id | Risk | Likelihood | Impact | Sign that it is happening | Response |
| --- | --- | --- | --- | --- | --- |
| K1 | The Python collector misses the budget on the owner's machine, so the trigger fires (B2) | Medium: no Windows figure exists; the Linux direct reader came to 36.0 ms per tick, 14 ms under the idle limit [Linux] | High: P2 planned again | Probe 2's output in P0-O2: over 60 ms per tick at 2 s, over 50 ms at 5 s, or over 83,886,080 private bytes | Section 8.2 |
| K2 | The USS round takes most of the idle budget. It is outside the trigger but inside the budget (`docs/17-build-prompt.md:299`), so the trigger can say "stay" while the collector breaks 1% at 5 s. [Linux] one round for the 25 largest costs 0.81% of a core at the 30 s default, which leaves 9.7 ms per 5 s tick for everything else | Medium; high on the Linux figure. The Windows cost of the USS read is unmeasured | Medium: the guard stretches `uss_interval` all the time and workload memory totals age (L12, `docs/10-known-limits.md:20`), or idle soak windows fail | Probe 2's USS round time; idle soak windows over 1% that fall on USS ticks; guard events that name `uss_interval` | B2 records a default `uss_interval` (range 10 s to 5 min, `docs/08-configuration.md:60`) at which the tick and the USS round fit 1% at 5 s. On the Linux figure, 5 min puts the round at 0.08%. The guard's order stays as the brief sets it (`docs/08-configuration.md:70`) |
| K3 | Linux in version 1 is over the budget at the default intervals: psutil costs 95.1 ms per tick at 300 processes [Linux], 4.76% at 2 s and 1.90% at 5 s, and passes only with the guard at about 3.2 s and 9.5 s (L04, `docs/10-known-limits.md:12`) | High: expected, and accepted by R151 | Low for the product (Linux data at longer intervals, a stated limit); medium for the gate: the CI-L soaks (P2.1, P3.5) pass only if the guard settles inside the checker's windows | P2-W3-T2's test with an injected 95 ms tick; CI-L soak windows over the limit; guard events | None for the limit. For the gate, K5 |
| K4 | A server pass breaks one judging window. At idle the whole budget in a 60 s window is 600 ms of CPU for every Submeter process. A collector at the [Linux] direct-reader figure, 36.0 ms per tick and 12 ticks a minute, uses 432 ms of it and leaves 168 ms. The hourly rollup, a retention pass, the daily backup of `history.db` (P3-W4-T2) and the leak check over up to 48 h of raw rows per workload (I38, P4-W3-T3) each run as one pass, which can fall inside one minute. The brief gives the budget no window (`docs/17-build-prompt.md:299`); the soak checker uses 60 s (P2-W5-T4) | Medium | Medium: P3.5, or the P4 and P5 soaks, fail at the hour mark or at the backup | P3-W6-T2's and P4-W4-T2's failing windows at the hour, the backup or the analysis pass; each pass's CPU time, which the server logs with the pass (P3-W3-T1, P4-W3-T3) | The owner chooses between spreading each pass over several minutes and judging the server over the 10-minute windows the owner's soak uses. The B2 row states the share the collector leaves for the server (I56) |
| K5 | The guard acts after the window in which the load or the cadence changed, so that window is over the limit. The guard measures per window (P2-W3-T2); the checker judges every 60 s window (P2-W5-T4) | Medium | Low to medium: P2.1 fails by one window | Single failing windows at cadence changes in the CI soak's CSV | P2-W3-T2's test reports how many windows the guard takes to settle. Whether the window of a change is judged is the owner's ruling, recorded before P2-W6 |
| K6 | The owner's machine runs more than 300 processes. The budget is stated at 300 (`docs/17-build-prompt.md:299`); the review machine ran 452 [Linux] (`docs/review/ground/platform-check.txt`). The gate is judged on the 300-process figure while daily use costs more | Medium | Low: the guard lengthens the intervals in daily use, inside the budget | The process count in P0-O1's `platform_check.py` output | Probe 2 reports the share at the owner's real count beside the 300-process figure. Whether the gate must also hold at the real count is the owner's ruling |
| K7 | Memory over the budget or growing: collector private bytes over 83,886,080, collector and server over 157,286,400, or growth over 24 h. [Linux]: 39 MB resident and 35 MB unique after 120 ticks. Windows and the server are unmeasured | Medium | Medium to high: B2's memory branch, or P2.6 failing after a day | Probe 2's private bytes; the soak monitor's samples every 10 s (P2-W5-T4); growth from the median of hours 1-2 to the median of hours 23-24 against the limit section 6 sets | B2 at P0 for the collector. Growth found in a soak becomes a fix task that names the structure that grows. The lead does not raise the limit |
| K8 | CPU time not seen by polling is large. [Linux]: 1.7% of capacity when quiet (2.04% in a second probe), 13.7% with one spawning loop, 51.6% with four (`docs/review/probes/measure/reconcile_under_spawn.out.txt`, `docs/review/probes/b-measurement/reconcile_terms.out.txt`). On Windows at 2 s about 85% of a polled workload's short-lived children's CPU is missed (`docs/10-known-limits.md:10`). Reconciliation holds through its own term, but attribution of polled workloads is weak | Medium | Medium: P2.4's quiet bound fails on the owner's machine | The quiet fixture's not-seen share in P2-O1 | The bound is fixed before the recording (P2-O1). Tagged runs are the stated remedy (L02). A failed bound goes to the owner, not to a second recording |
| K9 | Interrupt and DPC time counted twice in Windows busy time (R125) | Medium | High: busy time and System over-stated, so not seen by polling carries a positive bias, and P2.3's floor of −2% can hide a member counted twice | P0-O1's `cpu_time_check.py`: per core, r1 within 1.00 ± 0.01 means interrupt and DPC are inside system time | B4 by the rule written in P0-W1-T2; P2-W2-T3 and P2-W4-T2 apply it. Neither ratio inside the tolerance: stop and ask |
| K10 | The bulk call changes or stops parsing. CPU times, start time and I/O in SYSTEM_PROCESS_INFORMATION are documented only as Reserved, and psutil uses the same call for processes it cannot open (`docs/16-review-log.md:177-183`, R17 with R70) | Low in any one Windows update | Medium: the collector falls back to psutil, `process.bulk` reads partial, and on the [Linux] figure the fallback costs 1.9 times the idle limit, so the guard lengthens the intervals | P2-W2-T1's parse guard fails on CI-W, or on the owner's machine after an update | The fallback and the guard as designed; a fix task for the parser; the owner is told, as for any change of provider status |
| K11 | Cost outside Submeter's processes: Defender's scanning of the raw files and their `-wal` is charged to Defender, and the budget counts only Submeter's processes (`docs/17-build-prompt.md:299`). Suspected; nothing measured | Low | Low to medium: the machine pays more than the budget shows | The CPU time of Defender's process over probe 2's runs, against a quiet period of the same length | P0-W6-T2 records that figure in P0-O2, if a standard user can read it. It goes to the owner as a fact; nothing in the brief counts it |
| K12 | The GPU counters cost more than any gate measures. The GPU Engine counter set has one instance per process per engine (suspected; to confirm in current documentation in P5-W1-T2). The runners have no GPU, so P5-W3-T2's soak sees the providers unavailable; only P5-O2, which the owner may drop, measures them on real hardware | Medium | Medium: the budget fails in daily use and no gate shows it | P5-O2's soak, or a 30-minute run on the owner's machine with the GPU providers on | If the owner drops P5-O2, propose a 30-minute owner run with the GPU providers on at the P5 gate. The guard's documented actions do not include `gpu_interval` (`docs/08-configuration.md:70`), so a longer default (range 1 s to 30 s, `docs/08-configuration.md:62`) is the owner's choice |

### 8.4 Windows and the work computer

| Id | Risk | Likelihood | Impact | Sign that it is happening | Response |
| --- | --- | --- | --- | --- | --- |
| K13 | The holder design does not work (B1): a standard user cannot create or nest a job, for example inside the job the terminal or Claude Code has already placed the shell in, or the job's name does not reopen while a holder keeps a handle | Low to medium: documented behaviour, never run as this user | High: job 1, the first priority; P1 planned again | P0-O2, probe 1: step a or b fails, or step d differs from what gate P0.8 expects | P0-W2-T2's decision function: a or b failing stops the build and goes to the owner. A different result at d changes B1, and P1-W1-T2, P1-W1-T4 and P1-W2-T1 are re-carded before dispatch |
| K14 | Nested job accounting is not as R49's subtraction assumes. `cost --run` subtracts child runs' totals from the parent's (P1-W2-T3, P3-W1-T3), which is right only if a parent job's totals include its child jobs' processes. The review did not check this (`docs/review/01-adversarial-review.md:1639`), and probe 1 nests only inside the shell's job, not inside a job the probe made | Low to medium | Medium: P1-W2-T3 and P3-W1-T3 done again; caught at the latest by P1.6 in P1-W3-T1 | Probe 1's step h in P0-O2 (gate P0.8); later P1-W2-T1's nested-run test, or P1-W3-T1's nested case (P1.6), on CI-W | Probe 1's step h (P0-W2-T2) settles it at P0; a result other than R49 assumes sends B1 to the owner before P1, and P1-W2-T3 and P3-W1-T3 are re-carded before dispatch |
| K15 | Programs that ask to break away fail under `submeter run` (L03, R68): breakaway stays forbidden (`docs/10-known-limits.md:11`) | Medium for Chromium-based browsers, which R68 expects to be among them | Medium: P1.9 fails or becomes a known limit; such programs cannot be tagged | P1-O1's browser case; probe 1 step f (node, then bash) | The owner rules at P1-O1 whether it fails the gate or is recorded under L03. Breakaway is never allowed to make a test pass |
| K16 | Security software or policy blocks or flags Submeter: Defender attack surface reduction events 1121 or 1122 naming python.exe (R126); AppLocker or Device Guard refusing programs in user-writable folders, where uv's interpreter and the virtual environment live; the scheduled task refused; PDH or the bulk call refused to a standard user | Medium: a managed work computer, nothing checked yet | High: Submeter cannot run, or is flagged, on its only target machine | P0-O1's Defender query; P0-W5-T2's effective AppLocker policy, Device Guard status and `schtasks` exit codes in P0-O2; any probe that fails with access denied | Stop and tell the owner if anything is blocked or flagged (`docs/reference/windows-priorities.md:92`). The scheduled task's alternative, the `HKCU` Run key, is B3. Nothing is worked round |
| K17 | A large Restricted share. On a managed computer many processes belong to the system or to security software, and if most CPU lands in Restricted, attribution of polled workloads is weaker than the brief assumes (`docs/reference/windows-priorities.md:51`). The brief's sample shows 14 restricted processes (`docs/03-cli-output.md:19`); the review machine had 298 of 452 [Linux] | Medium | Medium: job 1 for polled workloads; tagged runs are not affected | P0-O1's `restricted_share.py`: the Restricted row's share of all workloads' cores, and the count | Reported to the owner at the P0 gate with the figures. Nothing changes without a ruling |
| K18 | The data folders are redirected or synced. If `%APPDATA%\Submeter` or `%LOCALAPPDATA%\Submeter` is redirected or synced on the managed computer, raw and history files leave the machine and a synced SQLite file can be corrupted (`docs/reference/windows-priorities.md:77`) | Low to medium | High: fixed rule 3 | Where the folders really are, after the file-locations line of `platform_check.py` in P0-O1, and whether they are redirected or synced, which P0-W1-T2's procedure records | `SUBMETER_HOME` set to a local folder that is not synced, chosen with the owner. If no such folder exists, stop and ask |
| K19 | The private folders are not private on Windows. Mode 0o700 becomes an access list that admits the current user and administrators (Python 3.12.4 and later), unverified on the owner's machine; `doctor` cannot check it (R100) | Low | Medium: other local users could read workload names and figures | `icacls` in P0-O1 lists another user | A fix task that sets the access list itself. It needs the Windows security API through ctypes, so it goes to the owner as a change of scope |
| K20 | Start stamps differ between the bulk provider and the psutil fallback. psutil gives a Windows start time as a float of seconds since 1970, about 1.8e9 in 2026, where a float's spacing is 2.4e-7 s, wider than the 100 ns unit of the FILETIME that the bulk call gives; a FILETIME of 2026 counts from 1601 and is about 1.344e17 (57 bits). So the float cannot carry the stamp: of 100,000 random FILETIMEs of November 2026, 57,809 changed when taken through it and back (computed for this plan on 22 November 2026). Keys built from the float would differ from the bulk provider's, and a switch to the fallback during a run would give most processes a new key, which shows exits and starts that did not happen | High if the float were used; low with the response | Medium: wrong CPU deltas for every process at each switch to or from the fallback | On CI-W, P0-W4-T1's exact comparison with GetProcessTimes fails, or P2-W2-T1's comparison of the two providers' keys for one process | In P0-W4-T1: the psutil provider reads CreateTime as an integer with GetProcessTimes, on a handle opened with PROCESS_QUERY_LIMITED_INFORMATION (R126), never from psutil's float; P2-W2-T1 checks that both providers give one process the same key |
| K21 | SQLite files on Windows: a delete is refused while any reader holds the file, and antivirus may hold a new file briefly (`docs/reference/windows-priorities.md:62-63`) | High for the first; medium for the second | Low to medium: retention runs late; a write fails | The "raw file on disk" line of `platform_check.py`; failed-write and refused-delete events | As designed: retention retries at the next pass and counts space as freed only when the files are gone (P3-W4-T1); a failed write never fails the tick (R54). Errors that come and go are recorded with their error numbers |
| K22 | Suspend and the two clocks do not behave as documented. QueryUnbiasedInterruptTime has never run on Windows, and the behaviour across a real suspend is unconfirmed (`docs/reference/windows-priorities.md:72`). The gap rule and awake seconds (R38, R39) rest on it | Low | High: covered time and rates wrong after every sleep, the case R38 and R39 were rated critical for | P0-O1's sleep check: `gap` false, or the clock that stops during suspend moved while the machine slept (`docs/reference/windows-priorities.md:73`) | Stop and ask before P2-W1-T2 is dispatched |
| K23 | A restart or sign-out during a 24-hour soak. A managed computer may restart for updates or sign the user out; P2-O2 and P5-O2 each need 24 hours with one sleep | Medium | Low to medium: a day of elapsed time per attempt, in the phase that is already the longest in elapsed time (section 5.2) | The soak monitor's CSV ends early; a restart or sign-out in the system event log | The owner schedules each soak outside update windows. A soak cut short is reported as not run, never as passed |
| K24 | The owner's machine lacks hardware or permissions a test needs: no battery, no GPU with its own memory, or sleep not allowed by policy. Then the `hardware` cases (on-battery flag, throttling, suspend), P5-O1's GPU fixtures and P2-O2's sleep cannot run | Medium | Low to medium: D12 and parts of P2.6 unverified | P2-O1's and P5-O1's outputs; the `doctor` rows | `docs/STATUS.md` names each provider and case that never ran on real hardware (D12). The floor allows the GPU-bound rule-out to be rewritten without VRAM (`docs/15-phases-and-decisions.md:77`; B18) |
| K25 | `why` takes over 2 s on Windows. Python's start-up with typer and pydantic, and Defender scanning a new environment, are unmeasured | Medium | Medium: P4.5 fails on the owner's machine | P0-O2's 20 runs of `Measure-Command { uv run submeter --help }`, which include uv's own start-up; P4-O1 | If start-up alone takes most of the 2 s, P4-W3-T1 imports heavy modules inside the command. P4.5 is judged on the virtual environment's own `submeter.exe`, not `uv run` (section 6.8); how Submeter is installed for the scheduled tasks is Q12 |

### 8.5 Owner decisions, owner time and the governing documents

| Id | Risk | Likelihood | Impact | Sign that it is happening | Response |
| --- | --- | --- | --- | --- | --- |
| K26 | A decision is not recorded when its task is due. Every task a decision blocks waits until the decision is recorded (section 5.6). Four decisions have no default and sit on or feed a phase's longest chain: B7 (P0-W4-T2, then P0-W6-T1 and the P0 gate), B11 (P2-W3-T2, then P2-W5-T1, P2-W6 and the 24-hour soak), B8 (P2-W4-T4, then P2-W5-T1, P2-W6 and the P2 gate) and B12 (P4-W1-T4, then P4-W3-T3) | Medium | Medium: narrower waves, longer phases | A task held at dispatch for a decision | Each phase's decisions go to the owner at the gate before that phase, and P0's before P0-W2. By phase: P0 B7, B9, B10 (the `AGENTS.md:35` wording), B16; P1 B1, B13; P2 B2, B4, B5, B6, B8, B11; P3 B3, B17, B19; P4 B12, B14, B15, B20; P5 B18, which holds P5-W1-T2's merge only if its builder finds no source, never its dispatch (B9 again in P1 and P5). B7 and B11 first, because they have no default and are on a longest chain. B10's line-35 wording blocks P0-W2-T1; its other wordings unblock no task but remove K28 |
| K27 | Owner time on the longest chains. The owner tasks take about 7 hours attended: P0-O1 about 45 minutes, P0-O2 about 2 hours, P1-O1 30 minutes, P2-O1 1 hour, P2-O2 under 1 hour attended over 24 hours, P3-O1 20 minutes, P4-O1 15 minutes, P5-O1 15 minutes and P5-O2 under 1 hour over 24 hours if kept, besides six gate approvals. P2-W6-T3 and P2-W6-T4 cannot be dispatched until P2-O1 has committed its fixtures, nor P5-W4-T1 until P5-O1 has committed the GPU fixtures | Medium | Medium: idle builders, longer elapsed time | A wave whose dispatch waits on an owner task | The lead asks for each owner task as soon as its wave integrates (section 5.3). P2-O1 is asked for when P2-W4 integrates, one wave before P2-W6 needs it |
| K28 | `AGENTS.md` lags the rulings (B10). Line 39 lists no `programs` layer (R108), line 40 puts every record in `core/models.py` (R112), and line 46 says the server writes minute files (I94), which R145 removed. Line 35 tells a session to run one test from `tests/test_baseline.py`, which P0-W2-T1 deletes. Builders read `AGENTS.md` as standing rules; `CLAUDE.md` imports it | Medium | Low to medium: a builder stops to ask, or builds what a ruling removed | A task report that cites `AGENTS.md:35`, `:39`, `:40` or `:46` against its card | Each affected card quotes the ruling that overrides the line (`AGENTS.md:54`: "my rulings override both"). The wordings of 11.6 go to the owner before P0-W2; line 35's blocks P0-W2-T1 and is on `main` at P0-W2's base commit (B10) |
| K29 | Known disagreements between brief and code stop builders. `AGENTS.md:52-54` tells a builder to say so and ask when the brief and the code disagree, and until their tasks land, the moved code changes of section 8.6 leave the code behind the brief: the minute tier (R145, until P0-W3-T1), the stand-in zero CPU and the float start time (R57, R56, until P0-W4-T1), settings validation (R111, until P0-W4-T2), the fixed 30 s gap rule and covered gaps (R38, R39, until P2-W1-T2), and wall-clock stamps (R55, until P2-W4-T4) | High without the response | Low: builders stop to ask questions already answered | Escalations that cite one of these | `docs/STATUS.md` lists each known disagreement with the task that removes it, and each card points to that list |
| K30 | The machine the build runs on is not settled (`docs/review/01-adversarial-review.md:1694`). If the swarm runs on Linux, as stage 1 did, eleven Windows-only tasks can be tested only by pushing to CI-W: P0-W2-T2, P0-W5-T2, P0-W6-T2, P1-W1-T4, P1-W2-T1, P1-W3-T1, P2-W2-T1, P2-W2-T3, P2-W3-T4, P3-W1-T3 and P5-W1-T2, six of them of size L. All of P1's longest chain (P1-W1-T4, P1-W2-T1, P1-W3-T1) is among them. If it runs on the owner's Windows machine, K38 applies | High: one of the two cases applies whichever machine is chosen | Medium: review rounds spent waiting for CI-W, or the costs of K38 | The time from a builder's push to a CI-W result, measured in the pilot | The owner answers (section 11). The pilot measures the round trip on whichever machine is chosen |

### 8.6 The code changes moved to the plan

Seven `fix now` code changes grew past about fifty changed lines and moved to the plan (`docs/review/02-rulings.md:276-286`). Each row says what holds until its task lands and what could go wrong in the task.

| Id | Change and task | Measured, and what holds until it lands | Risk | Likelihood, impact | Sign | Response |
| --- | --- | --- | --- | --- | --- | --- |
| K31 | R38 with R39: P2-W1-T2 (L) | 49 and 73 changed lines, before awake seconds were added (`docs/review/02-rulings.md:280-281`). Until then a tick over 30 s zeroes all CPU, `submeter top --seconds 31..60` prints zeros, and a gap is stored as covered zero-use time | The task grows past L, and splitting it the obvious way would ship R38's rule without R39's, which I1 forbids because each alone loses the CPU the other keeps | Medium, medium | The builder's report, or the first review, shows more than about 600 changed lines | Split into (a) the gap flag and awake seconds through records, raw rows and buckets, with no change of behaviour, and (b) the gap rule with the rollup rules. (a) may merge alone; (b) merges as one |
| K32 | R55: P2-W4-T4 (M), blocked on B8 | Built at 47 lines and reverted: after a 1 h step back `taken_at` stayed 1 h ahead for the rest of the run, and it drifted +130 s in 30 days at +50 ppm (`docs/review/02-rulings.md:282`). Until then batch stamps follow the wall clock (L13) | B8 is unanswered when P2-W4 starts, so P2-W4-T4 is held, and with it the collector program (P2-W5-T1 depends on it), P2-W6 and the P2 gate | Medium, medium | B8 not recorded at gate P1 | B8 goes to the owner at gate P1 with the two measured outcomes |
| K33 | R57 with R56: P0-W4-T1 (L) | R57 was 60 lines in its smallest clean form; R56 was not attempted and is estimated at about 75 lines (`docs/review/02-rulings.md:283-284`). Until then a refused CPU read gives a stand-in record with `started=0.0` and zero CPU, and start times are wall-clock floats, so a clock step cuts children from their parents | Six source files, the platform script with its smoke test and the Windows CreateTime read (K20) in one task, on P0's longest chain; P0-W5-T1 and the bulk probe P0-W6-T2 wait for it | Medium, medium | A second review round | Split in the task's own order: R57 first, then R56, each merged in turn |
| K34 | R111: P0-W3-T2 (S) and P0-W4-T2 (M) | A partial change reached 51 lines with its test still failing at `verdict.thresholds` (`docs/review/02-rulings.md:285`). Until then a missing named settings file is read as no file (`src/submeter/cli.py:43-51`), so a run with a mistyped `--file` uses the defaults without saying so | P0-W4-T2 is blocked on B7, which has no default, and P0-W6-T1 and the P0 gate wait for it | Medium, medium | B7 not recorded when P0-W3 integrates | B7 goes to the owner before P0-W2. If it is still open at P0-W4, the owner may choose to have P0-W4-T2 ship the other ranges and leave the eight bounds to a later task of size S; the lead does not choose this |
| K35 | R145: P0-W3-T1 (L, with the record fields) | 102 lines: 45 added, 57 removed (`docs/review/02-rulings.md:286`). Until then the code keeps the minute tier (`Tier.MINUTE`, minute files, `Retention.minute`) that the brief removed | A removal with tests; it must come before P0-W4-T2 (I68), which the waves already order | Low, low | `uv run submeter config check examples/submeter.toml` fails after the change | None beyond the task's tests |

### 8.7 Risks from the open assumptions

**K36.** 32 entries of "How the rulings combine" carry an **Assumption** the owner has not confirmed (`docs/review/02-rulings.md:136-265`). Each takes a finding's recommended option, or the reading that keeps two accepted rulings consistent, so the likelihood that any one is overturned is low. The risk lies in when an answer comes: an assumption overturned after the first task built on it has merged costs that task again, and the tasks after it. The sign is an answer in section 11 that differs from the assumption. The response: each assumption goes to the owner before its first task is dispatched; the lead records "stands" or the new ruling in `docs/STATUS.md`; a changed ruling re-cards the task before dispatch. The three of high impact are confirmed first: I89 before P0-W1, I12 before P0-W4 and I56 before P0-O2.

| Assumption | What it settles | First task built on it | Work at risk if overturned after that task merges | Impact |
| --- | --- | --- | --- | --- |
| I2 | Awake seconds per sample and bucket; CPU and I/O rates and capacity over awake seconds (option a) | P2-W1-T2 | The gap and awake path through sampler, raw store, rollup, attribution and `top` | Medium |
| I5 | Query-time merges use R53's end rule; no proportional split | P3-W3-T2 | Query readers and the leak series reader (P4-W1-T3) | Low |
| I7 | `source` names the CPU path; partial is a mark per field | P0-W5-T1 | Records, `aggregate`, raw columns, `top` | Medium |
| I9 | Schema version stays 1; the server assigns epochs | P0-W3-T1 | Records, the raw schema (P2-W3-T1), the epochs pass (P3-W4-T4) | Medium |
| I12 | Component 05 is not in version 1; Linux reads sit in the psutil provider's Linux branch | P0-W4-T1 | Linux reads in P0-W4-T1, P2-W2-T2, P2-W3-T3 and P2-W4-T2. Overturning adds component 05 and its tasks to P2 | High |
| I17 | Restricted when the command line or owner is unreadable, or on Linux when the owner differs | P0-W5-T1 | Provider and aggregate rules (P2-W2-T2, P2-W3-T4) | Medium |
| I21 | `docs/02` opens by saying its dashboard is version 1.1 | None; already in `docs/02` | One sentence | Low |
| I22 | R60 stays in version 1 as a P2 task, dropped if P0's cost breaks the budget | P0-W2-T4 | The cgroup part of P2-W4-T2 | Low |
| I24 | Not seen by polling is a column in `system_raw`, not a workload | P2-W1-T1 | Records, raw schema, reconciliation, `top` | Medium |
| I28 | Full PSS measured once on the Linux runner in P0 | P0-W2-T4 | One probe script | Low |
| I29 | At start the collector seeds attribution from the open raw file (option a) | P2-W2-T4 | `Attributor.seed()` and the collector's start (P2-W5-T1) | Medium |
| I30 | Costly fields: USS or PSS at `uss_interval`; command lines once per new process on Windows and again at `uss_interval` on Linux; the working folder only for a `cwd` rule | P2-W2-T2 | Provider and sampler schedules (P2-W3-T3, P2-W3-T4) | Medium |
| I33 | The run-id variable is `SUBMETER_RUN` | P1-W1-T2 | Little code, but agents that read the variable after P1 would break | Medium |
| I36 | `config reload` stops through the stop files and starts as `daemon start` does | P3-W5-T3 | One command | Low |
| I38 | The leak check reads raw rows merged into 1-minute time-weighted means over up to 48 h | P4-W1-T3 | The series reader, the leak check's tuning and B14's fixtures | Medium |
| I42 | A process whose start time cannot be read is only counted, with no key (option b) | P0-W4-T1 | Provider, sampler, reconciliation, `top`, `doctor` | Medium |
| I45 | The `submeter` workload is the pid files plus the holder's pid in live run files, each matched with its start stamp | P1-W1-T2 | Run file, launcher, the collector's attribution (P2-W5-T1, P3-W2-T4); see K49 | Medium |
| I50 | The P4 builder sets the disk queue and latency thresholds and tunes them on fixtures | P4-W2-T2 | Threshold values | Low |
| I51 | Linux GPU load is in version 1, tested from fixtures | P5-W1-T3 | One task; overturning removes it | Low |
| I54 | The cost explorer in `docs/08` is cut until P2 measures rows and bytes | P2-W6-T2 | A table in `docs/08` | Low |
| I56 | In P0 the collector alone is compared with the whole budget | P0-W6-T2 | The B2 decision itself (section 8.2). Overturning lowers the collector's limit and can fire the trigger | High |
| I57 | Unused settings stay in `config.py`, unvalidated | P0-W4-T2 | Settings validation | Low |
| I61 | The collector's cap is the larger of 7 days and `retention.raw`; only the server enforces the disk budget | P2-W5-T1 | The collector's deletion and the retention pass (P3-W4-T1) | Low |
| I67 | No `baseline` table in version 1's history schema | P3-W1-T1 | The DDL; a later migration either way | Low |
| I75 | The agent-cost check is in the P1 gate | P1-W3-T1 | One gate case | Low |
| I78 | The report escapes every value and inserts data with `textContent` | P5-W1-T1 | The renderer (P5-W2-T1) | Low |
| I81 | The synthetic store generator is kept; the 30-day dashboard load gate is dropped | P3-W1-T2 | Test tools | Low |
| I82 | tzdata's approval is recorded, and it is not added in version 1 | P0-W1-T1 | The dependency test | Low |
| I85 | `store backup` writes a request file that the server answers | P3-W2-T3 | Control file, backup pass and CLI (P3-W4-T2, P3-W5-T2) | Low |
| I87 | A `submeter findings` command; `why` and the report show findings | P4-W1-T1 | One command (P4-W3-T2) | Low |
| I89 | The phase column of `docs/13` | All of section 3 | The phase order; overturning re-plans the waves | High |
| I94 | `AGENTS.md:46` keeps its wording until the owner approves a change | None | Wording only (K28) | Low |

### 8.8 Building with the swarm

| Id | Risk | Likelihood | Impact | Sign that it is happening | Response |
| --- | --- | --- | --- | --- | --- |
| K37 | Builders start from the wrong commit. `origin` was an empty repository when last checked and the push of `main` is recorded as still owed (`docs/review/00-working-notes.md:9`); the local repository has no remote-tracking branch (`git for-each-ref refs/remotes` printed nothing on 22 November 2026). A new worktree starts from the remote's default branch unless `worktree.baseRef` is `"head"` (`docs/reference/claude-code-notes.md:30`), and section 4.1 rule 3 starts each wave from a pushed base commit | High unless the response is taken | High for the pilot: builders on an empty or old base, and merge conflicts that are not planning defects | A builder's `git rev-parse HEAD` differs from the base commit B in its dispatch message (changed in stage 3: B is not written on the card, 10.4 setting 2) | Push `main` before P0-W1 (done for stage 2's commit on 23 November 2026; 10.2 item 2); `CLAUDE.md` lets the lead push without approval, and if the session's permissions refuse the push again, the owner pushes. Also set the base explicitly, and make the first step of every card a check that HEAD is the wave's base commit |
| K38 | Running the swarm on Windows costs more than on Linux. [Linux] a fresh working copy took 12.1 s for the four checks and 26.3 s for `uv sync` and the seven; four copies at once took 10.7 to 13.1 s each and six took 13.7 to 18.3 s (measured for this plan on 22 November 2026, 8 logical cores). On Windows each copy's 101 MB virtual environment and many small files are scanned by antivirus; deep paths under `.claude/worktrees/` can pass 260 characters; a running process holds its virtual environment and SQLite files open, so a worktree cannot be removed; line endings must stay LF (`.gitattributes:1`); native Windows has no sandbox (`docs/reference/claude-code-notes.md:9`; `docs/reference/windows-priorities.md:94-99`) | Medium | Medium: slower waves; worktrees left on disk | Pilot timings several times the Linux ones; `git worktree remove` failing; a diff that shows every line changed | The pilot records its timings, and the cap of 4 is reviewed after P1 against them (section 5.4). The repository stays at a short path. Each builder stops every process it started before its worktree is removed |
| K39 | CI-W passes what the owner's machine fails. The Windows runner is an administrator with User Account Control off (R118), and whether it runs job steps inside its own Job Object is unchecked (`docs/review/01-adversarial-review.md:1683`) | Medium | Medium: gate items fail late, at the owner's run | `owner_machine` cases failing at a gate after CI-W was green | `owner_machine` cases run at every gate (P1-O1, P2-O2, P3-O1, P4-O1). P0-W2-T2's smoke run on CI-W records `IsProcessInJob` for the runner's own process |
| K40 | The baseline fails on CI-W at the pilot. It has never run on Windows (`docs/17-build-prompt.md:337` asks what needed fixing), and P0-W1-T1 is its first run there. Section 5.4 widens only after "the checks green after each merge and on both runners". The fixes are likely to touch files that P0-W3 and P0-W4 tasks own, such as `store/files.py`, `store/raw.py` and `providers/psutil_provider.py` | High | Medium: one or two waves added before P0-W2 | P0-W1-T1's first CI-W run | Each failure is recorded with its cause in `docs/STATUS.md`. The fixes run as a wave of their own, P0-W1a, before P0-W2's base commit is fixed, and a second, P0-W1b, if failures remain; a third is a stop (10.3 item 9). They run first because 7.2's pilot exception requires the CI run of the P0-W1 integration to pass on CI-W before P0-W2, and because from P0-W2 on each task's tests-first check reads both runners (7.2 step 1). In a wave of their own no planned task owns the files they touch. The pilot is judged on failures its own changes caused (section 5.4). Changed in stage 3: this row and 10.1 put the fixes on later waves' cards or in P0-W3 to P0-W6's spare places, against 7.2 (`prompts/02-orchestration-prompt.md` 8.5) |
| K41 | Contract files and change requests hold tasks. `core/models.py` has eight holders, one in each phase's first wave or P0 repair (section 4.2), and any record change by another task waits a wave as a change request (section 4.3) | Medium | Low to medium: tasks finish without what they asked for, or report blocked | Change requests open longer than one wave; tasks reported blocked | As section 4.3. Approving the `AGENTS.md:40` wording (B10) lets records live in their own modules, which removes most of these |
| K42 | A task grows past size L. There are 27 tasks of size L. The `fix now` changes measured in stage 1 were 47 to 102 lines each, and several L tasks combine two of them (P0-W4-T1, P2-W1-T2) or add ctypes structures (P1-W1-T4, P2-W2-T1, P2-W2-T3, P5-W1-T2) | Medium | Medium: a session lost; the wave waits | More than about 600 changed lines, or a second review round that fails | Split at review (section 3.1). After two rounds the task goes to a stronger model or to the owner (`prompts/01-execution-prompt.md`, Stage 3, principle 5) |
| K43 | Python versions differ between machines. uv chose Python 3.14.5 on the review machine because nothing pins the interpreter (`docs/review/01-adversarial-review.md:13`); P0-W1-T1 installs 3.13 on CI; the owner's machine gets whatever uv picks | Low to medium | Low: a failure seen on one version only | A test that fails on one machine and passes on CI | The owner chooses between running CI on both 3.13 and 3.14 and pinning one version |
| K44 | Merges are slow. The seven checks take 16.8 s per merge with warm caches [Linux], 13 s of it in the two `mypy --platform` runs, which replace the shared mypy cache each time; with a separate cache folder per platform the seven take about 4.8 s (measured for this plan on 22 November 2026) | High | Low | Merge times in `docs/STATUS.md` | Separate cache folders change the checks in `AGENTS.md`, so the wording goes to the owner for approval |

### 8.9 Gates, fixtures and the fixed rules

| Id | Risk | Likelihood | Impact | Sign that it is happening | Response |
| --- | --- | --- | --- | --- | --- |
| K45 | The leak check cannot meet B14's pass rates. On the baseline's plateau test, which P4-W2-T1 replaces, with noise of ±40 MB on minute buckets: the warm-up was falsely flagged in 34 of 60 runs with a sliding 2-hour window and in 18 of 60 with a growing window; a 75 MiB an hour leak was flagged in 200 of 200 seeds at the first allowed check; and the lower bound of the tail slope cleared 50 MiB an hour in only 38% (`docs/review/probes/audit/audit_growth_windows.out.txt`, parts 1, 3 and 4). B14 proposes 0 of 200 warm-ups and at least 190 of 200 leaks by 2 h 5 min, with the noise on each 30 s raw row, so each 1-minute mean (I38) averages two rows. These are synthetic series and do not depend on the operating system | Medium | Medium: P4.2 to P4.4 | P4-W2-T1's tests at review | The fixtures and pass rates are fixed before the detector exists (P4-W1-T2). A detector that cannot meet them is reported to the owner with the rates it reaches. Neither a builder nor the lead loosens the rates |
| K46 | No source of the adapter's VRAM total works for a standard user on Windows (B18) | Medium: no source confirmed yet | Medium: the GPU-bound rule-out | P5-W1-T2's builder finds none in current documentation | Stop and ask (B18's default). The floor allows the rule-out to be rewritten without VRAM (`docs/15-phases-and-decisions.md:77`) |
| K47 | A recorded fixture carries the owner's user name, host name or home folder (`AGENTS.md:44`). The repository was public when the review checked it (`docs/review/00-working-notes.md:9`), and pushed history is not rewritten (`CLAUDE.md`), so a pushed leak cannot be removed. In CI the scan runs as the runner's user and proves little | Low: the recorder refuses on a hit (P2-W4-T3) | High: personal details published for good | The anonymisation scan on the recording machine (S5) | The owner runs the scan before committing in P2-O1 and P5-O1. A hit stops the commit; nothing from an owner task is pushed before its scan has passed |
| K48 | A call that breaks a fixed rule escapes the static test. P0-W3-T3's check finds calls by name; a Win32 call through a name computed at run time on a ctypes library, or a new dependency's own code, is not seen | Low | High: a fixed rule broken | Nothing from the static test. The run-time checks: a tagged job's limit flags read back as 0 (P1-W1-T4); 0 sockets and a token that is not elevated in every soak (P2-W5-T4) | Reviewers read every ctypes call against the three fixed rules. The run-time checks run in every soak, CI and owner |
| K49 | Submeter's own launcher and CLI processes are charged to a user workload. The `submeter` workload holds the pid files and the holders (I45). The launcher of `submeter run`, started as `python -m submeter.programs.launcher` outside the job and alive for the command's whole run (P1-W2-T1), and the CLI processes are in neither, so rules attribute them: `examples/rules.toml:34-38` gives `python.exe` with a working folder under `C:\src` to `builds` | High wherever such a rule exists | Low: a small cost of Submeter's own in a user workload; the budget as written names neither the launcher nor the CLI (`docs/17-build-prompt.md:299`) | A run's launcher pid under a user workload in the P1 or P3 gate data | Under I45 as written, neither the launcher nor a CLI process is in the `submeter` workload or in the judged budget; the soak monitor records them apart (P2-W5-T4). Whether they join is the owner's choice, since I45 is an assumption: R69 in section 11.7, before P1-W1-T2 |


## 9. Traceability

This section maps everything the brief asks version 1 to do to the tasks of section 3 and the tests that prove it: the three jobs, the three fixed rules, the known limits, every accepted finding (R38 to R153), the "not in version 1" list, the other testable promises of `docs/01` to `docs/17`, and the commands and tools of `docs/13-build-list.md`. The 26 numbered components are traced in section 3.2 and the floor of version 1 in section 1.2; neither is repeated here. Section 9.10 records the plan's check of itself.

### 9.1 How to read the tables

- **Source.** An inventory built for this plan at commit `1c734e0` and checked against the repository at that commit: each existing test cited below was found by name under `tests/` (43 names), and each new test file cited is in a task card of section 3, the fixed rules at `AGENTS.md:9-11`, the limits at `docs/10-known-limits.md:9-21`, the floor at `docs/15-phases-and-decisions.md:71-81`, the cut list at `docs/13-build-list.md:91-109`, and the dispositions in `docs/review/02-rulings.md:19-134` (116 findings: 97 `fix now`, 13 `plan`, 6 `defer`).
- **Tasks** are the ids of section 3. An owner task (`P<n>-O<n>`) is listed when the evidence can only come from the owner's machine.
- **Tests** name the test file and the case written first in the task card, or an existing test by its function name. P0-W2-T1 moves the existing tests into one file per component without renaming them, so function names are given without a file. "gate Pn.m" is a gate item of section 6; S1 to S5 are the criteria every gate shares; D1 to D18 are the rows of section 1.2.
- **Done** means the change and its test are already on `main` at `1c734e0` and no version 1 work is left. **Not in version 1** cites the item of `docs/13-build-list.md:91-109`, numbered N01 to N19 in 9.6.
- Nothing in these tables is assigned to a task that section 3 does not contain.

### 9.2 The three jobs

| Job | Acceptance | Tasks | Tests and gate items | Where |
| --- | --- | --- | --- | --- |
| J1 Attribution | The parts sum to the whole within 2%; on Windows a tagged workload matches the load generator's own accounting within 2%; on Linux tagged runs are unavailable in version 1 (`docs/01-overview.md:5-8`; `docs/15-phases-and-decisions.md:75-76`) | Tagged runs: P1-W1-T2, P1-W1-T3, P1-W1-T4, P1-W2-T1, P1-W2-T2, P1-W2-T3, P1-W3-T1, P1-O1. Polled attribution and reconciliation: P2-W2-T1, P2-W2-T2, P2-W2-T3, P2-W2-T4, P2-W3-T1, P2-W3-T3, P2-W4-T2, P2-W5-T1, P2-W6-T3, P2-O2. Live groups: P3-W1-T3, P3-W2-T4. `cost` over history: P3-W5-T1 | gate P1.1 to P1.11; gate P2.2, P2.3, P2.4; gate P3.3; rows D1 to D4 | Owner (P1.1 to P1.10, P2.2 with the bulk provider); CI-W; CI-L |
| J2 Live diagnosis | A verdict with its evidence in under 2 s; Inconclusive when the signals disagree (`docs/01-overview.md:10-13`; `docs/15-phases-and-decisions.md:77`) | Inputs: P2-W2-T3 (system counters), P2-W3-T1 (columns). Verdict: P4-W1-T1, P4-W1-T2, P4-W2-T2, P4-W3-T1, P4-W4-T1, P4-O1. GPU-bound rule-out: synthetic GPU rows in P4-W1-T2, adapter VRAM from P5-W1-T2 when present | `tests/test_verdict.py`: one fixture per verdict, two matching rules give Inconclusive, under 60 s gives Inconclusive, no flip at a threshold, Linux rows never give No bottleneck; `tests/test_cli_why.py`: time recorded on CI, failing above 4.0 s; gate P4.1, P4.5; row D8 | CI-W, CI-L; timing on Owner (P4-O1) |
| J3 Trends | A leak of 75 MiB an hour (78,643,200 bytes an hour) flagged within 2 h 5 min; a cache warming up not flagged (`docs/01-overview.md:15-18`; `docs/15-phases-and-decisions.md:63,78`) | P4-W1-T2 (fixtures), P4-W1-T3 (1-minute series), P4-W2-T1 (leak check), P4-W3-T3 (server pass), P4-W2-T4 and P4-W3-T2 (`diff`, `findings`), P4-W4-T1; history charts P5-W2-T1, P5-W3-T1; findings in the report P5-W4-T1 | `tests/test_leak.py` at the pass rates of B14; gate P4.2, P4.3, P4.4; `tests/test_cli_findings.py`; gate P5.1; row D9 | CI-W, CI-L |

### 9.3 The three fixed rules

| Rule | Tasks | Tests and gate items | Where |
| --- | --- | --- | --- |
| F1 Observe only: no priority, affinity, suspend, kill or memory cap, and no setting that enables one (`AGENTS.md:9`) | P0-W3-T3 (static test); P1-W1-T4 (job created with no limits, breakaway not allowed, no kill-on-close); P1-W3-T1 (breakaway refused and recorded). Submeter's own logon task at priority 5 is allowed (R50, `docs/17-build-prompt.md:260`) | `tests/test_fixed_rules.py`: process-changing calls in `src`, and no `Settings` field that turns on priority, affinity, suspend, kill or a memory cap, each shown failing on a planted violation; `tests/test_job.py`: LimitFlags read back as 0 on CI-W; gate P1.7; row D14 | CI-W, CI-L on every push |
| F2 No administrator rights (`AGENTS.md:10`) | P0-W3-T3 (no `runas` or `requireAdministrator`); P0-W5-T2 (probe 3 registers the logon task as a standard user, RunLevel LeastPrivilege); P3-W5-T3 (task definition); P2-W5-T4 (soak monitor records token elevation, judged in the owner's soaks); every owner task P0-O1 to P5-O2 runs as the signed-in standard user, and `scripts/platform_check.py` prints `administrator or root: False` | `tests/test_fixed_rules.py`; `tests/test_probe_autostart.py`; `tests/test_cli_daemon.py` (generated task XML); `tests/test_soak_tools.py`; gate P0.2, P0.10, P2.6 (not elevated in any sample), P3.3 on Owner; row D14 | Owner only: hosted runners are administrators and prove nothing about privilege (`docs/15-phases-and-decisions.md:25`, R118) |
| F3 Nothing leaves the machine; the API listens on loopback only (`AGENTS.md:11`) | P0-W3-T3 (no `socket`, `http`, `urllib`, `ssl`, `ftplib` or `smtplib` import in `src`; runtime dependencies pydantic, psutil and typer only); P2-W5-T4 (open sockets per Submeter process); P5-W1-T4 (uPlot vendored, fetched once by the builder, never at run time); P5-W2-T1 and P5-W4-T1 (report); P4-W2-T3 (an alert raises a finding and sends nothing). The loopback clause applies to the version 1.1 API: version 1 opens no listener (component 20, R150) | `tests/test_fixed_rules.py`; `tests/test_soak_tools.py` and gate P2.1, P2.6, P3.5 (0 sockets in every sample); `tests/test_report.py` (0 `http://` or `https://`); gate P5.1 (headless Chromium with the network blocked: 0 requests, 0 CSP violations); row D14 | CI-W, CI-L, Owner |

### 9.4 Known limits

`docs/10-known-limits.md:5` requires each limit to be stated beside the numbers it affects in the CLI output, the report and `doctor`. L00 is that rule; L01 to L13 are the rows of `docs/10-known-limits.md:9-21` in order. The notes themselves are constants in `core/limits.py` (P2-W1-T1).

| Limit | What version 1 does | Tasks | Tests and gate items |
| --- | --- | --- | --- |
| L00 Limits are shown beside the numbers they affect | One note per limit, printed by the commands and the report that show the affected figure | P2-W1-T1 (`core/limits.py`), P2-W5-T2 (`top`), P3-W5-T1 (`cost`), P4-W3-T1 (`why`), P5-W1-T1, P5-W2-T1 and P5-W3-T3 (report), P2-W5-T3, P3-W5-T4 and P5-W2-T4 (`doctor`) | Snapshot tests in `tests/test_cli_top.py`, `tests/test_cli_cost.py`, `tests/test_cli_why.py`, `tests/test_report.py`, `tests/test_cli_doctor.py` |
| L01 Work done for a workload by another process is charged to that process | Note beside `agent:*` totals in `top`, `cost`, `why` and the report | P2-W5-T2, P3-W5-T1, P4-W3-T1, P5-W3-T3 | `tests/test_cli_top.py`, `tests/test_cli_cost.py` and `tests/test_cli_why.py`: the L01 note beside an `agent:*` workload or contributor; `tests/test_report.py`: the L01 note beside an `agent:*` workload |
| L02 Short-lived children of polled workloads are undercounted | Polled label and note; `submeter run` closes the gap on Windows | P2-W5-T2; P1-W2-T1, P1-W3-T1; P1-W2-T2 (Linux run labelled polled); P3-W5-T1 (the note beside polled workloads in `cost`, as the docs/03:22 sample prints it); P5-W3-T3 (the note and the polled label in the report) | `tests/test_cli_top.py`; gate P1.1; `tests/test_cli_run.py` Linux case; `tests/test_cli_cost.py`: the L02 note beside a polled workload; `tests/test_report.py`: the L02 note beside a polled workload |
| L03 Programs that break away from a job fail under `submeter run` | Breakaway stays forbidden | P0-W2-T2 (probe steps e and f), P1-W1-T4, P1-W3-T1, P1-O1 (the owner rules whether a browser that fails under the job fails the gate or is recorded as L03), P3-W5-T1 (the L03 note beside each tagged run's totals in `cost`), P5-W3-T3 (the same in the report) | `tests/test_job.py`; gate P0.8, P1.7, P1.8, P1.9; `tests/test_cli_cost.py` and `tests/test_report.py`: the L03 note beside a tagged run |
| L04 Linux in version 1: no tagged runs, no PSI or Linux system counters, about 95 ms per tick at 300 processes | `run` runs the command polled; `why` reads Inconclusive or unavailable; the guard holds about 3.2 s active and 9.5 s idle or longer | P1-W2-T2, P2-W2-T2, P2-W3-T2, P2-W5-T2, P3-W5-T1 and P4-W3-T1 (the note beside figures read on Linux in `cost` and `why`), P4-W2-T2, P5-W3-T3 (the note beside figures read on Linux in the report) | `tests/test_cli_run.py` (Linux exits with the command's code and says tagged runs are unavailable); `tests/test_guard.py` (95 ms injected tick cost at 2 s); `tests/test_verdict.py` Linux rows; `tests/test_cli_cost.py` and `tests/test_cli_why.py`: the L04 note on a Linux-shaped store; `tests/test_report.py`: the L04 note; gate P1.11; gate P2.1 on CI-L |
| L05 WSL2 and Docker Desktop appear as one VM process | Opaque workload; `doctor` reports its share of busy CPU time and of capacity | P2-W2-T4 (OPAQUE), P2-W5-T3 (`vm.guest` row), P3-W5-T4 (the two shares) | `tests/test_reconcile.py` or `tests/test_attribution.py`: a vmmem process under an `opaque:` rule is OPAQUE; `tests/test_cli_doctor.py`: shares from a vmmem fixture |
| L06 A CPU-second is not a fixed amount of work | CPU time as measured with frequency beside it; nothing normalised | P2-W2-T3 (frequency and base frequency), P4-W3-T1 (frequency beside CPU time in `why`), P5-W1-T1 and P5-W2-T1 (frequency beside CPU time in the report) | `tests/test_system.py`; `tests/test_cli_why.py`: the frequency beside CPU time; `tests/test_report.py`: a CPU chart carries the frequency series and L06's note |
| L07 Per-process VRAM not collected | Adapter VRAM used and total; `gpu.memory` reads "adapter total only" | P5-W1-T2 (B18), P5-W2-T4 | `tests/test_gpu_windows.py`; `tests/test_cli_doctor.py`; gate P5.2, P5.3 |
| L08 Temperatures not read | Throttling detected from frequency on Windows | P2-W2-T3 (throttled signal; `thermal.temp` unavailable), P2-W5-T3, P4-W2-T2 (Throttled verdict), P4-W2-T3 (throttling alert) | `tests/test_system.py` (`hardware` cases on Owner); `tests/test_verdict.py`; `tests/test_alerts.py`; `tests/test_cli_doctor.py` |
| L09 Network per process not collected | No network figures | P2-W2-T3 (`net.*` unavailable), P2-W5-T3 (`doctor` says "not in version 1") | `tests/test_cli_doctor.py` |
| L10 Other users' and system processes | Restricted bucket, never dropped; System for pid 4, Registry, MemCompression, Secure System and Linux kernel threads; Restricted memory n/a without USS; Linux keeps the name only; `doctor` reports hidepid | P2-W2-T1, P2-W2-T2, P2-W2-T4, P0-W5-T1, P2-W5-T2, P2-W5-T3, P3-W5-T1 (the note beside Restricted and System in `cost`), P5-W3-T3 (the note beside Restricted and System in the report) | `tests/test_cli_cost.py` and `tests/test_report.py`: the L10 note; `tests/test_bulk.py` (System marks); `tests/test_psutil_provider.py` (kernel thread to System, another user's process Restricted with its name only); `tests/test_attribution.py` (pid 4 to System); `tests/test_cli_top.py`; `tests/test_cli_doctor.py` (hidepid from a fixture mount line); done: `test_another_users_command_line_is_not_kept_on_linux` |
| L11 Which files a process touches is not recorded | I/O totals per process; disk latency and queue for the system | P2-W2-T1, P2-W2-T2 (I/O per process), P2-W2-T3 (disk latency and queue), P2-W5-T2 (the note beside I/O in `top`), P2-W6-T3 (a working folder and an open file named with canaries) | `tests/test_bulk.py`, `tests/test_psutil_provider.py`, `tests/test_system.py`; `tests/test_cli_top.py`: the L11 note beside I/O; gate P2.7: neither the working folder's name nor the open file's name occurs in any stored file |
| L12 Workload memory totals lag by up to the USS interval (30 s) | Age of the reading shown | P0-W5-T1 (total unit with its read time), P2-W3-T3 (USS at `uss_interval`), P2-W5-T2, P3-W5-T1 (the note beside memory totals in `cost`), P5-W3-T3 (the note beside memory totals in the report) | `tests/test_cli_top.py`; `tests/test_cli_cost.py` and `tests/test_report.py`: the L12 note |
| L13 Parent links across a wall-clock step back on Windows | Clock step recorded as an event that starts an epoch; Linux uses ticks since boot | P2-W4-T4 (flag; B8), P2-W3-T1 (event row), P2-W5-T1, P3-W4-T4 (epoch); P0-W4-T1 (Linux stamp) | `tests/test_sampler.py` (a step forward and a step back each flagged; a wall-clock step does not cut a child from its parent on Linux); `tests/test_server_epochs.py` |

### 9.5 Accepted findings R38 to R153

One row per finding, in number order. "Ruling" is the disposition (`docs/review/02-rulings.md:19-134`). "Before the plan" is what is already on `main`: an existing test by name, "docs" for a document change only, or the state of a moved code change. Section 2 gives the documents each finding changed.

| Finding | Subject | Ruling | Before the plan | Version 1 tasks | Tests and gate items |
| --- | --- | --- | --- | --- | --- |
| R38 | A fixed 30 s gap rule zeroes CPU; `top --seconds 31` to `60` prints zeros | fix now; code moved to plan | built at 49 lines, reverted (ships with R39, I1) | P2-W1-T2 | `tests/test_sampler.py`: a 60 s interval expected at 60 s is not a gap; a 35 s stall at a 1 s cadence is a gap that keeps its CPU; `tests/test_cli_top.py`: `top --seconds 45` prints non-zero CPU |
| R39 | A gap is stored and rolled up as covered time with zero use | fix now; code moved to plan | 73 lines, reverted | P0-W3-T1 (fields), P2-W1-T2 | `tests/test_rollup.py`: suspend across a bucket gives `covered_s` at most the width and `well_covered` False; an empty bucket closes and merges; a stall's rate stays at or below capacity |
| R40 | Linux child-time recovery double counts | fix now | field only: `test_counters_carry_an_optional_child_time` | P2-W2-T2 (provider reads child time), P2-W3-T3 (subtraction) | nested-reaping fixture through the psutil provider's output in `tests/test_sampler.py` on CI-L; `tests/test_psutil_provider.py`: `children_cpu_s` filled on Linux |
| R41 | Windows pid 0 read as a process | fix now | `test_windows_idle_process_is_not_read`; reconciliation check in `platform_check.py` | P0-O1; P2-W2-T1 (pid 0 excluded, System marks); P2-W2-T4; P2-W4-T2 (check re-run after R125) | gate P0.2 (summed process CPU within busy time + 5%); `tests/test_bulk.py` (pid 0 absent) |
| R42 | Records cannot say a figure is unavailable | plan (option b) | — | P0-W3-T1 (fields), P0-W5-T1, P2-W2-T2, P2-W5-T2 | `test_a_group_polling_never_saw_reports_its_io_and_memory_unavailable` passes and its strict xfail marker is removed (P0-W5-T1); `tests/test_raw.py` and `tests/test_rollup.py` keep None; `top --json` prints null; gate S2; row D13 |
| R43 | `Delegate=yes` turns on the cpu controller | fix now; Linux text after version 1 | docs | none: version 1 creates no cgroup | not in version 1 (N08) |
| R44 | Hot and cold sets cannot be built | fix now; overtaken by R142 (I19) | — | none | not in version 1 (N16); see R142 |
| R45 | Reconciliation leaves System and Idle undefined | fix now (option a) | `test_capacity_reconciles_with_a_not_seen_by_polling_term` | P2-W1-T1 (`Reconciliation`), P2-W2-T4, P2-W3-T1 (not-seen column, I24), P2-W5-T1, P2-W6-T3, P4-W3-T1 (six terms in `why`), P5-W3-T3 (six terms in the report) | `tests/test_reconcile.py`; gate P2.3, P2.4; row D3 |
| R46 | Linux memory overstated; one field for two units | plan (option a) | — | P0-W2-T4 (full-PSS cost; B6), P0-W3-T1, P0-W5-T1, P2-W2-T2, P2-W3-T3, P2-W3-T4, P2-W5-T2 | gate P0.7; `tests/test_attribution.py`: members lacking USS give partial with the count; `tests/test_psutil_provider.py`: growth unit every tick, total unit when asked |
| R47 | Inherited workload lost when the parent exits | fix now | `test_an_inherited_workload_lasts_for_the_life_of_the_process` | P2-W2-T4 (`Attributor.seed()`), P2-W5-T1 (workload-change events; seeding at start) | `tests/test_attribution.py`: after `seed()` a child keeps its workload; `tests/test_collector_program.py`: a restart keeps it |
| R48 | A job's name disappears with its last handle | fix now | docs | P0-W2-T2 (probe step d), P1-W1-T2 (`state()` lost), P1-W1-T4 (`open_job`), P1-W2-T1 (holder), P1-W2-T3 | gate P0.8; `tests/test_runs.py` (lost); `tests/test_launcher.py` (final state after the launcher exits); `tests/test_cli_cost.py` (lost, never 0); gate P1.2 |
| R49 | Nested tagged runs double count | fix now | docs | P1-W2-T1 (`SUBMETER_RUN`, IsProcessInJob, parent or "unknown"), P1-W2-T3 (run files), P3-W1-T1 (the parent column of `run`), P3-W1-T3 (net live totals, I32), P3-W2-T4, P3-W5-T1 (history rows) | `tests/test_launcher.py`; `tests/test_cli_cost.py` (parent 10 CPU-s less child 4 gives 6, from run files in P1 and from history rows with both run files deleted in P3); `tests/test_job.py`; gate P1.6 |
| R50 | The scheduled task is unspecified | fix now (priority 5) | docs | P0-W5-T2, P3-W5-T3, P3-W6-T3 (read back), P3-O1 | `tests/test_probe_autostart.py`; `tests/test_cli_daemon.py` (each `docs/17-build-prompt.md:260` setting in the XML); `tests/test_cli_doctor.py` (a changed setting in a read-back XML is reported); gate P0.10, P3.6 |
| R51 | Linux commit tile and alert read about 265% | fix now | docs | P2-W4-T2 (commit unavailable on Linux), P4-W1-T3 (`commit_fraction` None where commit is NULL), P4-W2-T3 | `tests/test_query.py`: `commit_fraction` None on a file whose commit columns are NULL; `tests/test_alerts.py`: a Linux series with commit None raises nothing |
| R52 | The plateau test flags or clears by noise | plan | — | P4-W1-T2, P4-W2-T1 (replaces `plateaued()`), P4-W4-T1 | `tests/test_leak.py` at the B14 pass rates; gate P4.3, P4.4 |
| R53 | End rule against midpoint rule loses CPU | fix now | `test_one_hour_read_and_rolled_up_matches_the_whole_day_rollup` | P3-W1-T2 (fractional-tick fixture), P3-W2-T2, P3-W3-T1, P3-W3-T2 (query merges by the end rule, I5), P3-W6-T1 | `tests/test_query.py`: a 600 s sample lands whole in the step holding its end; gate P3.1 (within 0.1%) |
| R54 | Non-UTF-8 text stops raw writes | fix now | `test_undecodable_text_and_a_failed_write_do_not_stop_later_writes` | none (P2-W5-T1 keeps the rule that a failed write never fails the tick) | done |
| R55 | A wall-clock step reopens day files | fix now; code moved to plan | built at 47 lines, reverted after review | P2-W4-T4 (anchored stamps, clock-step flag; B8), P2-W3-T1 (no earlier day reopened; event row), P3-W4-T4 (epoch) | `tests/test_sampler.py`: step forward and step back flagged, stamps after a step back and 30 days of +50 ppm drift within B8's rule; `tests/test_raw.py`: a batch stamped on an earlier day does not reopen the closed file |
| R56 | A process's start time is a wall-clock float | fix now; code moved to plan | not attempted (about 75 lines) | P0-W4-T1, P2-W2-T1 (CreateTime as an integer) | two reads give equal integer keys; a wall-clock step does not cut a child from its parent; on CI-W the start stamp equals GetProcessTimes' CreateTime exactly, and 134397792001234567 is stored unchanged while psutil's float gives 134397792001234568 (P0-W4-T1); `tests/test_bulk.py`: CreateTime equals GetProcessTimes on CI-W, and the bulk and psutil providers give one process the same key |
| R57 | A stand-in zero becomes the next baseline | fix now; code moved to plan | narrowed by R58: `test_a_failed_cpu_read_is_no_baseline` | P0-W4-T1 | a refused then readable read credits 0; a delta above interval × cores is capped and counted; a process with an unreadable start time is only in the count |
| R58 | One read error aborts the snapshot; zombies dropped | fix now | `test_failed_reads_keep_the_process` | none (P0-W4-T1 changes its stand-in case; P2-W2-T2 builds on its structure) | done |
| R59 | Windows' monotonic clock counts sleep | fix now | `test_suspend_is_told_by_the_clock_that_stops_not_by_the_wall_clock` | P0-W1-T2 and P0-O1 (`docs/reference/windows-priorities.md` section 5 on Windows), P2-W1-T2 (awake seconds) | gate P0.2; `tests/test_sampler.py` stall case |
| R60 | Linux cgroup `cpu.stat` can place unseen CPU | plan | — | P0-W2-T4 (cost; B5), P2-W4-T2 (if B5 keeps it) | gate P0.6; `tests/test_reconcile.py`: cgroup increases against polled deltas |
| R61 | `aggregate` labels a polled sum "kernel" | fix now | `GroupTotals` mapping; strict xfail test | P0-W5-T1, P3-W1-T3, P3-W2-T4 | the xfail test passes (gate S2); `tests/test_collector_program.py`: a tagged workload reports the group's CPU, not its polled sum |
| R62 | `include_children` undefined | fix now | `test_include_children_overrides_the_global_setting_both_ways` | none | done |
| R63 | Linux `exe` stored from `name()` | fix now | `test_exe_is_the_executable_file_and_name_is_kept_apart` | none | done |
| R64 | Linux Restricted holds two thirds, kernel threads included | fix now; code to plan (I12, I17) | docs | P2-W2-T2 (PF_KTHREAD), P2-W2-T4 (System bucket), P2-W4-T2 (irq and softirq time) | `tests/test_psutil_provider.py`: a kernel thread is System, another user's process Restricted |
| R65 | `docs/03` mislabels System and Restricted | fix now | docs | P0-W3-T1 (OPAQUE), P0-W5-T1, P2-W5-T2 | `tests/test_cli_top.py`: Restricted memory n/a, partial I/O with its count, the four fixed rows with no members |
| R66 | Polled undercount stated as Windows-only | fix now | docs | P2-W5-T2 (L02 note) | `tests/test_cli_top.py` |
| R67 | A job keeps no current memory | fix now; Linux decision after version 1 | docs | P0-W3-T1 (`GroupTotals` peak commit), P1-W1-T2, P1-W1-T4, P1-W2-T3, P3-W2-T4 | `tests/test_cli_cost.py`: mean memory null; `tests/test_collector_program.py`: tagged memory partial with the count |
| R68 | Forbidden breakaway makes some programs fail | fix now (keep forbidden) | docs | P0-W2-T2, P1-W1-T4, P1-W2-T1, P1-W3-T1, P1-O1 | gate P0.8, P1.7, P1.8, P1.9 |
| R69 | How the command enters the job | fix now | docs | P0-W2-T2, P1-W1-T4 (`create_in_job` with the job-list attribute), P1-W2-T1, P1-W3-T1 | `tests/test_job.py`; `tests/test_launcher.py`: IsProcessInJob(launcher) is FALSE; gate P1.4 |
| R70 | The psutil fallback is not independent of the bulk call | fix now | `test_windows_threads_are_unavailable` | P2-W1-T1 (`process.bulk` partial while the fallback runs), P2-W2-T1 (parse guard), P2-W6-T4 | `tests/test_bulk.py`: a truncated buffer raises, the live call parses on CI-W, the fallback reads partial; `tests/test_recorded_fixtures.py` |
| R71 | One-instance lock on Windows | fix now | `test_acquire_waits_for_a_lock_freed_late` | P0-O1 (`platform_check.py`'s lock check) | gate P0.2 |
| R72 | Where a Linux tagged cgroup lives | fix now; after version 1 | docs | none | not in version 1 (N08) |
| R73 | cgroup memory includes page cache | fix now; after version 1 | docs | none | not in version 1 (N08) |
| R74 | A Linux tagged tree can leave its group | fix now; after version 1 | docs | none | not in version 1 (N08) |
| R75 | Linux GPU sources wrong | fix now | docs | P5-W1-T3 (the Linux GPU-bound verdict is after version 1, I51) | `tests/test_gpu_linux.py`; gate P5.2, P5.3 |
| R76 | Cost of USS and PSS reads | fix now | docs | P0-W6-T2 (one USS round for the 25 largest), P2-W3-T2 (guard order) | gate P0.9; `tests/test_guard.py`: `uss_interval` or `uss_top_n` changed before the intervals |
| R77 | Linux: other users' command lines readable | fix now (option a) | `test_another_users_command_line_is_not_kept_on_linux` | P2-W5-T3 (`doctor` hidepid) | `tests/test_cli_doctor.py`: hidepid from a fixture mount line |
| R78 | The explorer's assumed costs are too low | fix now | docs | P0-W6-T2 (whole tick, both providers), P2-W6-T2 (rows and bytes per tick) | gate P0.9, P2.8; a measurement, no unit test. P2-W6-T2 also replaces the estimates of `docs/05-data-flow.md:78-87` |
| R79 | The Rust switching rule is undefined | fix now (budget as the trigger) | `platform_check.py` message | P0-W6-T2, P0-O2; decision B2 | `tests/test_probe_bulk.py` (trigger from recorded figures); gate P0.9, P0.12 |
| R80 | The leak acceptance sits on the threshold | fix now (75 MiB/h) | docs | P4-W1-T2, P4-W2-T1, P4-W4-T1 | gate P4.2 |
| R81 | Slow growth has no threshold | fix now; moot in version 1 (I58) | docs | none | not in version 1 (N15) |
| R82 | Usual-range floor | fix now; after version 1 (I58) | docs | none | not in version 1 (N15) |
| R83 | The gates use the product's own source | fix now | docs | P1-W1-T3 (generator imports nothing from `submeter`), P1-W3-T1, P2-W6-T3 | `tests/test_loadgen.py` (AST check); gate P1.1, P1.3, P1.6, P2.2 |
| R84 | Verdict rules disagree; thresholds a free mapping | fix now | docs | P0-W4-T2 (`Verdict.thresholds` model), P4-W1-T1, P4-W1-T2, P4-W2-T2, P4-W3-T1 | `tests/test_config.py`: a misspelt threshold is refused; `tests/test_verdict.py`; gate P4.1 |
| R85 | `percentile(q=100)` returns the top of the scale | fix now | `test_top_percentile_is_the_highest_filled_bin_with_float_weights` | none | done |
| R86 | Idle and active baselines undefined | fix now; after version 1 (I60) | docs | none (P3-W2-T2 keeps `active_share` at 0.005) | not in version 1 (N15) |
| R87 | Which processes the budget covers | fix now (every Submeter process) | `test_every_submeter_pid_and_its_children_are_submeter` | P1-W2-T1 (holder pid in the live run file), P2-W5-T4, P2-W3-T2, P2-W5-T1, P3-W6-T2, P4-W4-T2, P5-W3-T2 | `tests/test_collector_program.py`: a holder pid from a live run file is `submeter`; gate P2.1, P2.6, P3.5; row D5 |
| R88 | Raw days deleted before roll-up | fix now (option b) | `test_expired_raw_waits_for_the_rolled_up_mark` | P2-W5-T1 (collector cap with an event row), P3-W2-T1 (mark), P3-W3-T1 (roll-up before retention), P3-W4-T1, P3-W4-T4 (finding) | `tests/test_collector_program.py`: 8-day-old files deleted with `retention.raw = 2d`, kept with `10d`; `tests/test_history.py`: the mark moves only forward; `tests/test_server_epochs.py`: a cap-deletion event gives exactly one finding, and a second pass none |
| R89 | The power-loss promise | fix now (option c) | docs | P2-W6-T1; P2-W5-T4 and P2-W6-T2 (the longest time between checkpoints) | `tests/test_kill.py` (50 trials); gate P2.5; gate P2.8: the longest time between checkpoints at the shipped cadence, written into `docs/06-storage.md`, confirms or replaces "up to a few minutes" |
| R90 | A quiet process's CPU held for 10 minutes | fix now | `test_a_quiet_process_gets_a_row_each_minute_and_none_crosses_an_hour` | none (the 60 s close of per-executable figures is P3-W4-T3, I65) | done |
| R91 | The only raw reader is the writer class | fix now | `test_reading_a_raw_file_never_writes_to_it` | P3-W1-T4 (`quarantine()`), P3-W3-T1 (the rollup pass quarantines), P3-W2-T4 (the collector at start), P2-W3-T1 (closed files opened only for a query) | `tests/test_raw.py`: a corrupt raw file is quarantined with its side files; `tests/test_server.py`: the rollup pass quarantines a damaged raw file and records a gap; `tests/test_collector_program.py`: a damaged day file at start is quarantined |
| R92 | Minute-file estimate; a cap called exactly enforced | fix now | docs | P3-W4-T1 | `tests/test_server_retention.py`: a synthetic store over budget is trimmed in the stated order; gate P3.2 |
| R93 | The raw schema lacks columns; its version is never read back | plan | — | P2-W3-T1, P3-W1-T1 | `tests/test_raw.py`: another version gives a new same-day file, the old one untouched, `expired_raw` handles the name; `tests/test_history.py`: every catalogue column present and nullable |
| R94 | What starts an epoch | fix now (option a) | `test_a_bucket_keeps_its_interval_bounds_and_capacity_in_core_seconds` | P2-W1-T2 (capacity over awake seconds), P3-W1-T1 (`rollup_1h` keyed by epoch, Q17), P3-W2-T2 (epoch and logical cores per sample), P3-W3-T1 (the epochs pass before the rollup; each bucket's epoch id), P3-W3-T2, P3-W4-T4, P4-W2-T4 | `tests/test_server_epochs.py`: epochs with reasons from a fixture, none from a cadence change, and buckets either side of a rules change carry different epoch ids; `tests/test_rollup.py`: two epochs in one hour give two buckets, and capacity across a change of core count sums each sample's cores; `tests/test_server.py`: a bucket takes the epoch in force at its samples' end; `tests/test_query.py`: a window across an epoch is marked; `tests/test_diff.py` |
| R95 | `choose_tier`'s minute fallback ignores retention | fix now; folded into R145 and R139 (I69) | — | P0-W3-T1 | see R145 |
| R96 | The scrub default misses credentials | fix now | `test_exe_only_is_the_default_because_scrub_misses_common_forms` | none | done |
| R97 | `exe_only` keeps `argv[0]` | fix now | `test_exe_only_stores_the_executable_and_scrub_splits_a_title` | none | done |
| R98 | Logs and reprs bypass redaction | fix now | `test_reprs_leave_out_the_command_line` | P2-W1-T1 (structured event records), P2-W4-T1 (rotating logs and formatter), P2-W5-T1, P3-W3-T1 | `tests/test_logs.py`: a record carrying a command line comes out without it; the canary check of P2-W6-T3 over every `.db`, `-wal` and log file; row D15 |
| R99 | Scrub hides harmless arguments; rules see the unredacted text | fix now | `test_scrub_keeps_harmless_words_paths_and_uuids` | P3-W3-T4 (`rules test` marks hidden arguments) | `tests/test_cli_rules.py` |
| R100 | Files created 0755 and 0644 | fix now | `test_submeter_files_are_private_to_the_user` | P2-W4-T1 (the control folders 0700), P3-W1-T4 and P3-W4-T2 (backups 0600), P3-W5-T4 (`doctor` lists others-readable paths), P0-W1-T2 and P0-O1 (`icacls` on Windows) | `tests/test_server_backups.py` (0600 on POSIX); `tests/test_cli_doctor.py`; gate P0.2 |
| R101 | Token transport | fix now; version 1.1 | docs | none | not in version 1 (N11) |
| R102 | Token sent to whatever holds the port | fix now; version 1.1 | docs | none (`Api.port` kept unused, I57) | not in version 1 (N11) |
| R103 | What MCP withholds; findings carry command lines | fix now | `AGENTS.md:43` changed | P1-W2-T3 (no working folder in `cost`), P3-W1-T1 (structured `Finding` evidence), P4-W2-T1 | `tests/test_models.py`: a `Finding` with free-text evidence is refused; `tests/test_cli_cost.py`: canary command line and folder absent; gate P1.10 |
| R104 | WSL ingest API | fix now; moot (I76) | — | none | not in version 1 (N07) |
| R105 | A pid file outlives a crashed holder | fix now | `test_holder_names_only_the_live_holder_of_a_held_lock` | P0-W4-T1 (pid file stamp, I43), P3-W5-T3 (`daemon stop` never signals) | `tests/test_cli_daemon.py`: a stale pid file signals nothing |
| R106 | Workload names not validated | fix now | `test_workload_names_are_checked` | P1-W1-T2, P1-W2-T2 (`run --as`), P5-W2-T1 (escaping, I78) | `tests/test_cli_run.py`: `run --as system` exits 2; `tests/test_runs.py`: a reserved name refused; `tests/test_report.py`: markup in a name is escaped |
| R107 | Fixtures from the owner's computer pushed publicly (the finding named the work computer; since PD-003 fixtures are recorded and pushed from the personal PC only, section 3.1) | fix now (`AGENTS.md:44`) | `AGENTS.md:44` changed | P2-W1-T3, P2-W4-T3, P2-O1, P5-O1 | `tests/test_anonymise.py`; `tests/test_fixtures_anonymised.py`; `tests/test_record_fixture.py`; gate S5 |
| R108 | The layer rule forbids program imports | fix now (option a) | `test_no_program_imports_another` | P0-W2-T1 (`LAYER` rows), P1-W2-T1, P2-W5-T1, P3-W3-T1 (the three program packages); `AGENTS.md:39` wording waits for B10 | `test_no_module_imports_from_a_higher_layer` and `test_no_program_imports_another` on every push |
| R109 | Dependencies beyond three | fix now | docs | P0-W1-T1 (the one `pyproject.toml` and `uv.lock` commit, no package added), P0-W3-T3, P5-W1-T4, P5-W2-T1, P5-W4-T1 | `tests/test_fixed_rules.py` (three runtime dependencies); `tests/test_report_assets.py` (hashes); `tests/test_report.py` (CSP hashes, no `http(s)://`); gate P5.1 |
| R110 | 20 tests catch 1 of 29 breaks | plan | — | P0-W6-T1 | each new test fails its targeted mutant in `scripts/mutation_check.py` and passes at HEAD |
| R111 | Settings validation gaps | fix now; code moved to plan | partial change undone (51 lines, test still failing) | P0-W3-T2 (exit code 2), P0-W4-T2 (Literal metric, thresholds model, ranges; B7) | `tests/test_cli_files.py`: missing, UTF-16, syntax error and validation error each exit 2; `tests/test_config.py`: `retention.raw = "23h"` refused with the range, each bound just outside refused |
| R112 | The models cannot express the catalogue; shared files | plan | — | P0-W2-T1 (the test split), P0-W2-T3 (the CLI package), P0-W3-T1 (the record fields); P2-W1-T1 and P3-W1-T1 for later records; `AGENTS.md:40` wording waits for B10 | `tests/test_models.py` (each new field None and set); `tests/test_cli_registry.py`; every test function name collected at the wave's base commit still collected after the split |
| R113 | The run file's life is contradictory | fix now | docs | P1-W1-T2, P1-W2-T1, P2-W5-T1 (reads live files), P3-W4-T3 (copies final files, then deletes them) | `tests/test_runs.py`: live to final by atomic rename under a polling reader, final to live refused; `tests/test_server_ingest.py`: a run file deleted only after its row is committed |
| R114 | Routes and admin channels | fix now (reduced, I76) | docs | none of its own: every command reads files, programs are reached by files (P60 in 9.7) | — |
| R115 | Behaviours never specified | fix now (reduced, I68) | docs | P3-W1-T3 (membership from the job's process list), P3-W2-T3 (overlapping sessions), P3-W4-T3 (a session never stopped closes at its last covered sample) | `tests/test_cli_session.py` (overlap); `tests/test_job.py` (members mapped to keys); `tests/test_server_ingest.py`: a session never stopped closes at its last covered sample |
| R116 | `docs/17` and the topic files differ | fix now | docs | none of its own: each rule it copied is traced under its promise in 9.7; growth per process is decision B20 (P78) | — |
| R117 | The gates lack data and criteria | plan | — | section 6; P2-W5-T4, P2-W6-T2, P2-W6-T3, P3-W1-T2, P3-W6-T1, P3-W6-T2, P4-W4-T1 | `tests/test_gate_p2.py` to `tests/test_gate_p4.py`; `tests/test_soak_tools.py` |
| R118 | The CI runners are elevated | fix now | docs | P0-W1-T1 (markers `owner_machine`, `session`, `hardware`, `soak`, deselected in CI's main job); owner tasks P0-O1 to P5-O2 | `tests/test_project.py::test_markers_are_registered_and_strict`; gate P0.1, S1 |
| R119 | Gates depend on later phases | fix now (direct reads) | docs | none of its own (`why` reads raw files directly, P4-W3-T1) | — |
| R120 | No channel for stop and sessions | fix now (control files) | docs | P2-W4-T1 (stop files), P2-W5-T1, P3-W2-T3 (session markers, backup request), P3-W3-T1, P3-W4-T2 | `tests/test_control.py`; `tests/test_collector_program.py` and `tests/test_server.py` (a stop file stops the program within one tick); `tests/test_server_backups.py` (a request file is answered and removed) |
| R121 | Shared interfaces left to guess | plan | — | P1-W1-T1 (`--json` envelope), P3-W1-T1 (history DDL) | `tests/test_cli_envelope.py` and a snapshot per command (gate S4); `tests/test_history.py`: the DDL in `docs/06` equals `sqlite_master` after create |
| R122 | A long session cannot be summarised at its end | fix now (build planned) | docs | P3-W1-T1 (open-row columns), P3-W2-T1, P3-W4-T3, P3-W6-T1 | `tests/test_server_ingest.py` with an injected clock: the incomplete mark (I62) and the 60 s close (I65); gate P3.4 |
| R123 | Pid reuse inside psutil's cache | plan | — | P2-W2-T2 | `tests/test_psutil_provider.py`: an object aged as `docs/review/probes/verify-1/pid_reuse.py` does is read again |
| R124 | Python 3.12's monotonic clock is too coarse | fix now | `test_python_floor_is_3_13` | P0-W1-T2, P0-O1 (clock step measured on Windows) | gate P0.2 |
| R125 | Interrupt and DPC time counted twice | fix now (code conditional) | docs | P0-W1-T2 (`cpu_time_check.py`), P0-O1 (B4), P2-W2-T3, P2-W4-T2 | `tests/test_probe_step1.py`; gate P0.4; `tests/test_psutil_provider.py`: the busy sum with and without the subtraction |
| R126 | psutil reads the PEB; Defender attack surface reduction | fix now | docs | P0-W1-T2, P0-O1, P0-O2, P2-O2 (Defender log), P2-W3-T4 (limited-access reader) | `tests/test_cmdline.py`: own command line read, access mask PROCESS_QUERY_LIMITED_INFORMATION, refused read gives restricted; gate P0.3 |
| R127 | Windows private bytes read from an alias | fix now | `test_windows_memory_is_private_bytes` | P0-O1 | gate P0.2 |
| R128 | The WSL 10% share is undefined | fix now (share of busy CPU time) | docs | P2-W2-T4, P2-W5-T3, P3-W5-T4 | see L05 |
| R129 | The write-ahead log is not truncated | fix now | `test_write_ahead_logs_are_bounded_and_counted` | P3-W1-T4, P3-W5-T2, P3-W5-T4 | `tests/test_files.py`: a 5 MiB `-wal` flagged; `tests/test_cli_store.py` |
| R130 | Side files left behind | fix now | `test_expired_raw_takes_the_side_files_with_the_day` | P3-W4-T1, P3-W6-T1 | `tests/test_server_retention.py`: refused while a reader is open on CI-W, freed after; gate P3.2 |
| R131 | `daily_minimums` uses one offset | fix now | `test_local_days_follow_the_daylight_saving_change` | P4-W2-T4 | `tests/test_diff.py`: a diff across a daylight-saving change uses each reading's offset |
| R132 | Hourly merged from minute buckets | fix now; overtaken by R145 (I39) | — | P0-W3-T1 | see R145 |
| R133 | `redact_patterns` unvalidated | fix now | `test_redact_patterns_are_checked_and_reach_the_store` | none | done |
| R134 | The checks miss Windows types; ruff formats Markdown | fix now | `test_ruff_leaves_markdown_alone`; `AGENTS.md:30-31` | P0-W1-T1 (CI runs both `mypy --platform` checks) | `tests/test_project.py::test_ci_runs_every_agents_check_on_both_systems`; gate P0.1 |
| R135 | Wording slips | fix now | docs | none | — |
| R136 | Tools beside the code have no phase | fix now | docs | P0-W1-T1 (CI), P1-W1-T3 (load generator), P2-W4-T3 (fixture recorder), P3-W1-T2 and P3-W3-T3 (synthetic store), P3-W5-T3 (scheduled task) | each tool's tests, listed in 9.8 |
| R137 | Every measured figure is from Linux | plan | — | P0-W1-T2, P0-W2-T2, P0-W6-T2, P0-O1, P0-O2; section 8 marks the Linux figures | gate P0.2 to P0.5, P0.8 to P0.10, P0.12 |
| R138 | `brief.html` not ranked | fix now (freeze) | docs | none | — |
| R139 | `choose_tier` uses the retention setting | fix now | `test_tier_choice_takes_raw_coverage_from_disk` | P0-W3-T1 (test kept through the minute-tier removal), P3-W3-T2 (the caller reads coverage from the oldest raw file) | `tests/test_query.py`: a window 24 to 48 h back whose day file is gone is answered from hourly |
| R140 | Defer the WSL guest collector | defer | docs | none; the opaque VM and its `doctor` share stay (R128) | not in version 1 (N07) |
| R141 | Tagged runs first, as P1 | fix now | docs | every P1 task (section 3.5) | gate P1.1 to P1.11 |
| R142 | Cut hot and cold sets | fix now | `test_hot_and_cold_sets_are_removed` | P2-W3-T2, P2-W3-T3 (costly fields on their cadence), P2-W5-T1 (every process every tick) | `tests/test_sampler.py`: USS asked for only on USS ticks; `tests/test_collector_program.py` |
| R143 | Defer the MCP server | defer | docs | version 1 part: P1-W2-T3, P3-W5-T1 (`cost --run --json`); `Api.mcp_enabled` stays unused | not in version 1 (N09); gate P1.10 |
| R144 | Drop Parquet | fix now | docs | P5-W2-T3 (`export` to JSON and CSV) | `tests/test_cli_export.py`: round trip; canary absent |
| R145 | Cut the minute tier | fix now; code moved to plan | built at 102 lines, undone | P0-W3-T1 | `Tier` has RAW and HOURLY only; no minute names in `FileMap`; `disk_use()` has no `minute` key; `storage.retention.minute` refused; `submeter config check examples/submeter.toml` exits 0 |
| R146 | Defer baseline anomaly and slow growth | defer | docs | version 1 part: P4-W2-T2 (I/O verdict on absolute thresholds, I50), P4-W3-T3 | not in version 1 (N15) |
| R147 | P0 is three probes plus CI | fix now | docs | P0-W1-T1, P0-W1-T2, P0-W2-T2, P0-W2-T4, P0-W5-T2, P0-W6-T2, P0-O1, P0-O2 | gate P0.1 to P0.12 |
| R148 | Trim P5 | defer | docs | version 1 part: P5-W1-T2, P5-W1-T3, P5-W2-T2, P5-W3-T2; the on-battery flag in P2-W2-T3 and P2-W4-T2 | not in version 1 (N13); gate P5.2, P5.3 |
| R149 | Shrink the settings surface | fix now | `test_profiles_are_removed` | P3-W5-T3 (`config reload` as a restart, I36) | `tests/test_cli_daemon.py`: `config reload` stops and starts both programs and a changed setting applies |
| R150 | CLI first; API and dashboard to version 1.1 | defer | docs | version 1 part: P3-W2-T3 (session markers), P4-W3-T2 (`findings`), P5-W3-T1 (charts in the report) | not in version 1 (N11) |
| R151 | One operating system's platform layer | plan (Windows only) | docs | P0-W1-T1 (both runners), P1-W2-T2, P2-W2-T2, P4-W2-T2 | `tests/test_cli_run.py` Linux case; gate P1.11; `tests/test_verdict.py` Linux rows; the `--as` name of a polled Linux run is R151 in section 11.7 |
| R152 | Defer desktop notifications | defer | docs | version 1 part: P4-W2-T3 (a firing rule raises a finding) | not in version 1 (N12); `tests/test_alerts.py` |
| R153 | The floor of version 1 and six phases | plan | docs | section 1.2 (rows D1 to D18) and section 3 | the stage 2 self-check recorded in section 9.10 |

Count: 116 findings. 89 have version 1 work in a task; R153 is met by the plan's own text (section 1.2 and section 3); 9 are done with no work left (R54, R58, R62, R63, R85, R90, R96, R97, R133); 12 leave version 1 entirely (R43, R44, R72, R73, R74, R81, R82, R86, R101, R102, R104, R140); 5 changed documents only and leave no work of their own (R114, R116, R119, R135, R138).

### 9.6 Not in version 1

The list of `docs/13-build-list.md:91-109`, with the check or the version 1 work that stands in for each.

| Id | Item | What version 1 has instead, and the check |
| --- | --- | --- |
| N01 | Acting on processes | Nothing. `tests/test_fixed_rules.py` (P0-W3-T3) fails on a process-changing call or setting |
| N02 | Anything that needs administrator rights: per-process network bytes, a temperature sensor bridge | `doctor` shows `net.bytes` and `thermal.temp` unavailable (P2-W2-T3, P2-W5-T3); F2 |
| N03 | Sending anything off the machine, alerts included | An alert raises a finding (P4-W2-T3); F3 |
| N04 | Deep tracing through ETW and eBPF | L11 |
| N05 | One dashboard across several machines | No work |
| N06 | Normalising CPU time by core type or frequency | L06 |
| N07 | A collector inside WSL2 or Docker Desktop | Opaque workload and the `doctor` share (L05; R128) |
| N08 | The Linux platform layer | Linux polled through psutil, tested on CI-L; `tests/test_cli_run.py` Linux fallback (P1-W2-T2) |
| N09 | An MCP server (component 25) | `submeter cost --run "$SUBMETER_RUN" --json` (P1-W2-T3); gate P1.10 |
| N10 | Parquet export | `export` to JSON and CSV (P5-W2-T3) |
| N11 | HTTP API, WebSocket and token (component 20); live dashboard (component 21) | Version 1.1. Version 1 opens no listener (F3 static test); `Api` and `Ui` settings kept unused (I57) |
| N12 | Desktop notifications | Findings (P4-W2-T3), shown by `findings`, `why` and the report |
| N13 | Per-process VRAM, network connections and interface bytes, battery level, temperatures | Adapter VRAM (P5-W1-T2) and the on-battery flag (P2-W2-T3, P2-W4-T2) |
| N14 | A minute tier | Removed from the code by P0-W3-T1 |
| N15 | Slow growth, baseline anomaly, spike and swap-storm detectors | `daily_minimums` and `usual_range` in `analysis/growth.py` stay unused (I58) |
| N16 | Hot and cold sets | Removed: `test_hot_and_cold_sets_are_removed` |
| N17 | Reloading settings while running, named profiles, a per-session interval | `test_profiles_are_removed`; `config reload` restarts both programs (P3-W5-T3) |
| N18 | Component 05 `providers.linux.procfs` | After version 1; the psutil provider stands in (section 3.2) |
| N19 | The twelve API routes and `WS /live` (`docs/13-build-list.md:72-89`) | Version 1.1; no route in version 1 |

### 9.7 Other promises of the brief

Testable statements of `docs/01` to `docs/17` that are not already a row above, found by a search for "must", "never", "always", "within", "at most" and "under" and merged where two sources state one promise; hits that are not version 1 promises are left out. P100 was found by the second round of checks, under "nothing"; P95 to P99 were added after the first. Sources are in the inventory; the promise text here is shortened.

**Measurement and attribution**

| Id | Promise | Tasks | Tests and gate items |
| --- | --- | --- | --- |
| P01 | The six terms sum to capacity within 2%; all six shown in `why` and the report | P2-W2-T4, P2-W5-T1, P4-W3-T1, P5-W3-T3 | gate P2.3; `tests/test_cli_why.py` prints the six terms; `tests/test_report.py` |
| P02 | Not seen by polling stays under the share stated with the quiet fixture | P2-O1, P2-W6-T3 | gate P2.4; the share is 5% of capacity unless the owner sets another (section 6.6, Q5) |
| P03 | A Windows tagged tree of 500 sub-second children within 2% of the generator | P1-W1-T3, P1-W2-T1, P1-W3-T1, P1-O1 | gate P1.1 |
| P04 | Final totals survive the tree's exit; `run` returns with the command's exit code while left-behind processes are still counted | P1-W2-T1 | `tests/test_launcher.py`; gate P1.2, P1.3 |
| P05 | A grandchild started in the command's first millisecond is in the job | P1-W1-T4, P1-W2-T1, P1-W3-T1 | gate P1.4 |
| P06 | A nested run records its parent; the parent excludes the child; both within 2% | P1-W2-T1, P1-W2-T3 | gate P1.6 |
| P07 | Each burner set above 10% of a core (15, 25, 50 and 100%) within 5% or 0.05 s over 10 minutes | P2-W5-T1, P2-W6-T3, P2-O2 | gate P2.2 |
| P08 | With 300 processes, every Submeter process together under 1% idle and 3% active; collector and server under 150 MB | P2-W5-T4, P2-W3-T2, P2-W5-T1, P2-W6-T2, P3-W6-T2, P4-W4-T2, P5-W3-T2, P2-O2, P5-O2 | gate P2.1, P2.6, P3.5; row D5 |
| P09 | The guard lengthens intervals until under 3%, stretching `uss_interval` or `uss_top_n` first | P2-W3-T2 | `tests/test_guard.py` |
| P10 | A cadence change never loses or invents CPU time; providers return cumulative counters | P2-W3-T3 | `tests/test_sampler.py`: equal totals at 2 s and 5 s |
| P11 | An unreadable counter is None; no stand-in start time; capped deltas counted | P0-W4-T1 | its tests (R57) |
| P12 | The clock that stops during suspend never times an interval | P2-W1-T2, P0-O1 | `tests/test_sampler.py`; gate P0.2 |
| P13 | A gap is past 3 × expected + 2 s or a fired suspend test, keeps its CPU and I/O, and is never one giant sample | P2-W1-T2 | `tests/test_sampler.py` (R38) |
| P14 | Batch stamps never lag after a suspend or go backwards; a clock step records an event | P2-W4-T4 (B8) | `tests/test_sampler.py` (R55) |
| P15 | A process is pid plus integer start stamp; a parent link counts only if the parent started no later | P0-W4-T1 | its tests (R56) |
| P16 | Restricted processes never dropped; partial with the missing count; unavailable never zero | P0-W5-T1, P2-W2-T2 | R61's test passes; gate S2; row D13 |
| P17 | A process whose start time cannot be read is only in a per-snapshot count, shown by `doctor` and the reconciliation | P0-W4-T1, P2-W2-T4, P2-W3-T1 (the `system_raw` column), P2-W5-T3, P3-W2-T2 (hourly), P4-W3-T1 (`why`), P5-W1-T1 and P5-W3-T3 (the report) | P0-W4-T1's test; `tests/test_cli_doctor.py`; `tests/test_raw.py` (the column round-trips); `tests/test_cli_why.py` and `tests/test_report.py` (the count beside Restricted) |
| P18 | One process's failed read never costs the snapshot | done (R58) | `test_failed_reads_keep_the_process` |
| P19 | A pid psutil lists but reports gone is read again in the same tick | P2-W2-T2 | `tests/test_psutil_provider.py` (R123) |
| P20 | Linux zombies and unreaped children handled; recovery never exceeds busy less credited | P2-W2-T2, P2-W3-T3 | nested-reaping fixture on CI-L |
| P21 | Linux command lines read again at the USS interval | P2-W3-T3 | `tests/test_sampler.py`: on Linux the command line is asked for again at `uss_interval` and a change reaches the rules |
| P22 | Windows command lines once per new process with limited access, never PROCESS_VM_READ | P2-W3-T4 | `tests/test_cmdline.py`; Defender log in P2-O2 |
| P23 | Bulk snapshot: pid 0 excluded, System marks, fallback reported partial, a parse test that fails loudly | P2-W2-T1 | `tests/test_bulk.py` |
| P24 | System read from counters, never a remainder; not seen by polling never put in System | P2-W2-T3, P2-W2-T4, P2-W4-T2 | `tests/test_system.py`; `tests/test_reconcile.py` |
| P25 | System, Restricted, Unattributed and Submeter always shown, with not seen beside them | P2-W5-T2 (`top`), P3-W5-T1 (`cost`), P5-W1-T1 and P5-W3-T3 (the report); the `cost` sample of docs/03 differs (Q16) | `tests/test_cli_top.py`, `tests/test_cli_cost.py` and `tests/test_report.py`: the four rows with no members, the not-seen figure beside them |
| P26 | A tagged workload reports its group's kernel totals; peak commit never shown as current memory | P1-W1-T2, P1-W2-T3, P3-W2-T4 | `tests/test_cli_cost.py`; `tests/test_collector_program.py` |
| P27 | The collector never writes a run file and is never the holder; a live run file whose job cannot be opened reads as lost | P1-W1-T2, P1-W2-T1, P1-W2-T3, P2-W5-T1 (reads only) | `tests/test_runs.py`; `tests/test_cli_cost.py` |
| P28 | The launcher never joins the job | P1-W2-T1 | `tests/test_launcher.py`: IsProcessInJob(launcher) FALSE |
| P29 | Series kept per name and totals per run, so a new label never starts a series; `doctor` warns past 200 names | P1-W1-T2, P3-W4-T3, P3-W4-T4 (`workload` table), P3-W5-T4 | `tests/test_cli_doctor.py` (200 names); `tests/test_server_ingest.py`: two runs with different labels share one workload series |
| P30 | A workload name is 1 to 64 characters; reserved names refused for rules and `run --as` | done for rules (R106); P1-W2-T2 | `test_workload_names_are_checked`; `tests/test_cli_run.py` |
| P31 | Every condition of a rule must hold; `exe` and `name` are case-insensitive globs | done (baseline, R63) | existing attribution tests |
| P32 | On Windows a tagged group's member never reaches the rules; a Linux `run` command is polled and does | P3-W2-T4, P1-W2-T2 | `tests/test_collector_program.py`: a member never reaches the rules |
| P33 | Linux keeps only another user's process name; `doctor` reports hidepid | done in the provider (R77); P2-W5-T3 | `test_another_users_command_line_is_not_kept_on_linux`; `tests/test_cli_doctor.py` |
| P34 | On Linux `run` says tagged runs are unavailable and runs the command polled, labelled polled | P1-W2-T2 | `tests/test_cli_run.py`; gate P1.11; how the polled command gets its `--as` name: R151 in section 11.7 |
| P95 | A process belongs to its innermost group (`docs/17-build-prompt.md:80`) | P3-W2-T4 | `tests/test_collector_program.py`: a pid in an outer and an inner group's member list lands in the inner workload only, its memory counted once |
| P96 | GPU load is read per process and charged to workloads: job 1's cost includes GPU (`docs/13-build-list.md:31`, `docs/17-build-prompt.md:17`, `:111`, `docs/09-telemetry.md:14`) | P0-W3-T1 (fields), P0-W5-T1 (summed in `aggregate`), P2-W3-T1 (columns), P3-W1-T1 and P3-W2-T2 (hourly), P5-W1-T2 and P5-W1-T3 (per-process readings), P5-W2-T2 (onto each process's counters), P5-W3-T3 (shown in the report) | `tests/test_attribution.py` (two members sum per engine type); `tests/test_collector_program.py` (a fake per-process reading reaches its workload's row); `tests/test_report.py` |
| P97 | Every workload shows whether the kernel or polling measured it (`docs/04-features.md:16`) | P0-W5-T1 (`source`, I7), P2-W5-T2 (`top`), P3-W5-T1 (`cost`, the `source` column of docs/03:11), P5-W1-T1 and P5-W3-T3 (the report) | `tests/test_cli_top.py`; `tests/test_cli_cost.py`; `tests/test_report.py`: a kernel and a polled label |

**Store**

| Id | Promise | Tasks | Tests and gate items |
| --- | --- | --- | --- |
| P35 | Retention is always a file delete; each file has one writer | P3-W4-T1; P3-W3-T1 (the one-writer import check); one writer during the build by the ownership of section 4 | `tests/test_server_retention.py` (retention deletes whole files); `tests/test_one_writer.py`; `retention.executables`, the one setting that would delete rows, is Q15 |
| P36 | A program crash loses nothing committed; nothing ever corrupts a file | P2-W6-T1, P2-O2 | gate P2.5, P2.6 |
| P37 | A quiet process's CPU written within 60 s and at each UTC hour | done (R90) | `test_a_quiet_process_gets_a_row_each_minute_and_none_crosses_an_hour` |
| P38 | Another schema version starts a new file; readers accept every version on disk | P2-W3-T1 | `tests/test_raw.py` (R93) |
| P39 | A closed day's file is never written again, even after a step back across midnight | P2-W3-T1 | `tests/test_raw.py` (R55) |
| P40 | Raw files read through a read-only connection; closed files opened only for a query, so they can be deleted on Windows | done for reading (R91); P2-W3-T1, P3-W3-T2, P3-W4-T1, P4-W3-T3 | `test_reading_a_raw_file_never_writes_to_it`; `tests/test_server_retention.py` on CI-W: delete after the test's own reader closes, and the server's rollup pass and a query reader read a closed day that its retention pass then deletes, `.db`, `-wal` and `-shm`, on the first try in the same process; `tests/test_server_analysis.py` on CI-W: the same after the analysis pass's leak series read the day |
| P41 | Percentiles from merged bins, within one bin; q = 100 is the top of the highest filled bin | done (baseline, R85) | `test_histogram_merges_exactly_and_bounds_error`; `test_top_percentile_is_the_highest_filled_bin_with_float_weights` |
| P42 | A gap never reads as zero use; a bucket with no covered seconds never divides by zero | P2-W1-T2 | `tests/test_rollup.py` (R39) |
| P43 | Rates and capacity over awake seconds | P2-W1-T2 | `tests/test_rollup.py` (stall rate at or below capacity) |
| P44 | Hourly CPU-hours match the raw sum by end time within 0.1% | P3-W2-T2, P3-W3-T1, P3-W6-T1 | gate P3.1 |
| P45 | A session's cost reads the same before and after its raw data is deleted; incomplete when raw went first; per-executable part closed 60 s after the end | P3-W4-T3, P3-W6-T1 | gate P3.4; `tests/test_server_ingest.py` (incomplete; 60 s close) |
| P46 | A session never stopped closes at its last covered sample; sessions may overlap | P3-W4-T3, P3-W2-T3 | `tests/test_cli_session.py` (overlap); `tests/test_server_ingest.py` (never stopped) |
| P47 | Each hour keeps the top 10 executables per workload by CPU and by peak memory, keyed by name, for a year | P3-W2-T2 | `tests/test_rollup.py` (`exe_1h`); "for a year" (`retention.executables`) waits on Q15, whose default leaves the setting unused and the rows kept |
| P48 | Stored history is never rewritten when rules change; the boundary is marked | P3-W4-T4 (the epoch); P5-W1-T1, P5-W2-T1 and P5-W3-T1 (the marker on the report's charts, P98) | `tests/test_server_epochs.py`; `tests/test_report.py`; `tests/test_cli_report.py` |
| P49 | A comparison of maxima or percentiles across sampling intervals or epochs is flagged | P3-W3-T2, P4-W2-T4 | `tests/test_query.py`; `tests/test_diff.py` |
| P50 | Over budget: oldest raw first, never below 24 h, then backups down to one, then a finding; history never deleted | P3-W4-T1 | `tests/test_server_retention.py` |
| P51 | No raw day deleted before roll-up; the collector's cap with an event row; each cap deletion and guard action becomes a finding | P2-W5-T1, P3-W3-T1, P3-W4-T1, P3-W4-T4 | `tests/test_collector_program.py`; `test_expired_raw_waits_for_the_rolled_up_mark`; `tests/test_server_epochs.py` (a guard event gives a finding; a cap-deletion event gives exactly one finding, and a second pass none) |
| P52 | A raw day's `.db`, `-wal` and `-shm` free their space once no reader holds them; a refused delete is retried | P3-W4-T1, P3-W6-T1 | gate P3.2 |
| P53 | A record that cannot be stored never fails the tick | done (R54) | `test_undecodable_text_and_a_failed_write_do_not_stop_later_writes` |
| P54 | `choose_tier` never picks a raw day the budget deleted | done in `query.py` (R139); caller P3-W3-T2 | `test_tier_choice_takes_raw_coverage_from_disk`; `tests/test_query.py` |
| P55 | Every answer and chart states its tier and resolution | P3-W3-T2, P5-W1-T1, P5-W2-T1 | `tests/test_query.py`; `tests/test_report.py`; gate P5.1 |
| P56 | The lock file is only ever locked; a pid is the holder only while the lock is held and its stamp matches | done (R71, R105); P0-W4-T1 (stamp); P0-O1 | `test_file_map_names_expiry_and_lock`; `test_holder_names_only_the_live_holder_of_a_held_lock`; gate P0.2 |
| P57 | `SUBMETER_HOME` moves everything; control files in the state folder; run files in the data folder | done (`FileMap`); P1-W1-T2, P2-W4-T1 | `test_file_map_names_expiry_and_lock`; `tests/test_runs.py`; `tests/test_files.py` (the control paths under the state folder and under `SUBMETER_HOME`, P2-W4-T1); `tests/test_control.py` |
| P58 | Folders 0700 and files 0600 from creation; `doctor` lists others-readable paths | done (R100) except the control folders, backups and `doctor`: P2-W4-T1, P3-W4-T2, P3-W5-T4 | `test_submeter_files_are_private_to_the_user`; `tests/test_files.py` (`control/` and `control/sessions/` created 0700); `tests/test_server_backups.py`; `tests/test_cli_doctor.py` |
| P59 | Logs never hold command lines or working folders; event rows hold structured fields | P2-W1-T1, P2-W3-T1, P2-W4-T1 | `tests/test_logs.py`; `tests/test_providers_base.py` (free-text field refused); P2-W6-T3 canary |
| P98 | Every epoch is marked on every chart, with its reason (`docs/06-storage.md:129`, `docs/08-configuration.md:5`, `:117`, `docs/04-features.md:24`, `docs/17-build-prompt.md:235`) | P3-W2-T1 (the epochs reader), P5-W1-T1 (epoch boundaries in `ReportData`), P5-W2-T1 (the markers), P5-W3-T1 | `tests/test_report.py`: one boundary gives one marker with its reason; `tests/test_cli_report.py`: a range across the 30-day store's rules change gives exactly one marker; gate P5.1 |
| P99 | Buckets with less than half their time covered are left out of trends (`docs/06-storage.md:133`, `docs/17-build-prompt.md:171`) | P3-W3-T2 (the mark, by `well_covered()`), P4-W2-T4 (period diffs), P5-W2-T1 (history charts) | `tests/test_query.py`: such a bucket is marked and absent from the trend series; `tests/test_diff.py`; `tests/test_report.py` |
| P100 | Process rows live only in raw files; nothing keyed by pid is kept beyond 48 hours (`docs/17-build-prompt.md:150`) | P2-W3-T1 (process rows in raw files), P3-W1-T1 (no history table keyed by pid; `Finding` evidence without a pid) | `tests/test_history.py`: no table of the history DDL has a pid column in its primary key or a unique index, and `Finding` evidence has no pid field |

**Interfaces and control**

| Id | Promise | Tasks | Tests and gate items |
| --- | --- | --- | --- |
| P60 | Every command reads files; a running program is reached only through files or the service manager | every CLI task; P0-W3-T3 | `tests/test_fixed_rules.py` (no network client); `tests/test_control.py` |
| P61 | `daemon stop` never signals a process; the launcher and holders are not stopped by stop files | P3-W5-T3 | `tests/test_cli_daemon.py` (stale pid file signals nothing) |
| P62 | `cost --json` and the report never contain command lines or working folders, whatever the redaction mode (`docs/08-configuration.md:127`) | P1-W2-T3, P3-W5-T1, P5-W2-T1 | `tests/test_cli_cost.py`: the canary from run files (P1-W2-T3), and a plain canary stored in `scrub` mode absent from `cost --json` for workloads, `--session` and `--run` over history (P3-W5-T1); gate P1.10, P5.1 |
| P63 | The report escapes every value, uses `textContent`, has a meta CSP and no `http(s)://` | P5-W2-T1, P5-W4-T1 | `tests/test_report.py`; gate P5.1 |
| P64 | Finding evidence never holds a command line | P4-W1-T1 | `tests/test_models.py` |
| P65 | Provider status changes and clock steps start epochs; a restart only if a listed item changed; cadence, alert, UI and verdict edits do not | P2-W1-T1 (the start and hardware-change event records), P2-W5-T1 (writes them), P3-W4-T4 | `tests/test_server_epochs.py`: consecutive start events compared item by item, a hardware-change event; `tests/test_collector_program.py`: the start event and a hardware change written |
| P66 | Settings and rules read when a program starts, never while it runs | done (R149); P2-W5-T1, P3-W3-T1, P3-W5-T3 | `test_profiles_are_removed`; `tests/test_cli_daemon.py` (reload) |
| P67 | Out-of-range values refused with the range in the message; finite ranges; `retention.raw` at least 24 h | P0-W4-T2 (B7) | `tests/test_config.py` |
| P68 | Verdict thresholds are named fields; any other name refused | P0-W4-T2 | `tests/test_config.py` |
| P69 | Each redact pattern must compile | done (R133) | `test_redact_patterns_are_checked_and_reach_the_store` |
| P70 | A named `--file` or `--rules` that is missing, undecodable or invalid exits 2 | P0-W3-T2 | `tests/test_cli_files.py` |
| P71 | Each machine reads its own settings file | done | `test_config_layers_and_sources` |
| P72 | Fixed mode always uses the active interval | P2-W3-T2 | `tests/test_cadence.py` |
| P73 | `exe_only` stores the executable name only | done (R96, R97) | `test_exe_only_stores_the_executable_and_scrub_splits_a_title` |
| P74 | An alert rule names one of seven metric ids that applies to its workload; an unavailable metric never fires; `overhead_fraction` reports the total of every Submeter process (`docs/08-configuration.md:72`); the three built-in rules ship switched on (`:146-152`) | P0-W4-T2, P2-W1-T1 and P2-W2-T3 (`SystemCounters.throttled`), P2-W3-T1 (the `throttled` column), P4-W1-T3 (the series of every metric), P4-W1-T2 (the alert fixtures), P4-W2-T3, P4-W3-T3 (the server feeds the series to the rules) | `tests/test_config.py`; `tests/test_query.py`: each metric series from raw rows, `commit_fraction` None where commit is NULL; `tests/test_alerts.py`: each built-in rule and a user rule on each per-workload metric, trigger and quiet with the cooldown; `tests/test_server_analysis.py`: each built-in rule raises one finding from a synthetic store |
| P75 | The verdict rules: one matching rule, No bottleneck, Inconclusive, never forced; Linux never No bottleneck; confidence and evidence always | P4-W2-T2 | `tests/test_verdict.py`; gate P4.1 |
| P76 | Throttling judged against base frequency, below 80% under load | P2-W2-T3, P4-W2-T2 | `tests/test_system.py`; `tests/test_verdict.py` |
| P77 | `why` answers in under 2 s | P4-W3-T1, P4-W4-T1, P4-O1 | gate P4.5 |
| P78 | The 75 MiB/h leak flagged by 2 h 5 min; the warm-up cleared; the staircase flagged; growth tracked for each workload and, under B20, each process (`docs/07-analysis.md:29`) | P4-W1-T3, P4-W2-T1, P4-W4-T1 | gate P4.2, P4.3, P4.4; `tests/test_query.py` (a per-process series) |
| P79 | Each detector has a trigger fixture and a quiet fixture | P4-W1-T2, P4-W1-T4 (B12), P4-W2-T1, P4-W2-T2, P4-W2-T3, P4-W4-T1 | gate P4.1 |
| P80 | The not-configurable list has no setting | P0-W3-T3 | `tests/test_fixed_rules.py` (`Settings` fields) |
| P81 | `daemon install`: the logon task's settings, the HKCU Run fallback, read back by `doctor` | P0-W5-T2, P3-W5-T3, P3-W6-T3, P3-O1 | `tests/test_cli_daemon.py`; `tests/test_cli_doctor.py`; gate P0.10, P3.6 |
| P82 | Each layer is testable in isolation from recorded fixtures | every component task; P2-W4-T3, P2-W6-T4; the group provider's logic from job readings written in its test (P3-W1-T3), with no recording, which Q18 puts to the owner | `tests/test_recorded_fixtures.py`; `tests/test_job.py` |
| P83 | The Windows provider modules are written and tested on Windows | P1-W1-T4, P2-W2-T1, P2-W2-T3, P2-W3-T4, P3-W1-T3, P5-W1-T2 | CI-W must pass (section 3.1, OS); owner runs |
| P84 | Ruff never rewrites the brief | done (R134) | `test_ruff_leaves_markdown_alone` |
| P85 | `PROGRAMS` names collector, server and launcher only | done (R108); P1-W2-T1, P2-W5-T1, P3-W3-T1 | `test_no_program_imports_another` |

**Process promises at the gates**

| Id | Promise | Tasks | Tests and gate items |
| --- | --- | --- | --- |
| P86 | Phase 0 output saved under `docs/review/ground-windows/` | P0-O1, P0-O2 | gate P0.2 to P0.5, P0.8 to P0.10 |
| P87 | The Job Object probe tests BREAKAWAY_OK, never SILENT_BREAKAWAY_OK | P0-W2-T2 | `tests/test_probe_job_object.py` (AST check) |
| P88 | P0 gate: checks pass on both runners, each probe's output saved and its choice recorded | all P0 tasks | gate P0.1 to P0.12 |
| P89 | The owner's 24-hour soak: budget held, memory growth under the plan's limit, integrity ok, only recorded gaps | P2-W5-T4, P2-O2 | gate P2.6; the limit is 10,485,760 bytes (section 6.6, Q5) |
| P90 | The 30-minute CI soak with the server stays inside the budget | P3-W6-T2 | gate P3.5 |
| P91 | A restarted collector re-attaches to live groups on Windows | P3-W1-T3, P3-W2-T4, P3-W6-T1, P3-O1 | gate P3.3 |
| P92 | Each extended provider passes its recorded fixtures and degrades cleanly | P5-W1-T2, P5-W1-T3, P2-W4-T3, P5-O1, P5-W4-T1 | gate P5.2 (P5-O1's recordings, made with P2-W4-T3's recorder and replayed by P5-W4-T1), P5.3 |
| P93 | `docs/STATUS.md` written at every gate | the lead's record step (section 4.1, rule 6) | gate S3 |
| P94 | `docs/STATUS.md` names the providers that never ran on real hardware | the lead; P5-W1-T3 states it for NVIDIA and AMD | gate S3, P5.3; row D12 |

### 9.8 Commands and tools of `docs/13-build-list.md`

| Item | Tasks | Tests |
| --- | --- | --- |
| `daemon start`, `stop`, `status`, `install`, `uninstall` | P3-W5-T3, P3-O1 | `tests/test_cli_daemon.py` |
| `run --as NAME [--label L] -- COMMAND` | P1-W2-T2 (with the launcher, P1-W2-T1) | `tests/test_cli_run.py`; gate P1 |
| `top` | baseline; P0-W3-T2, P0-W5-T1, P1-W1-T1, P2-W1-T2, P2-W5-T2 | `tests/test_cli_top.py` |
| `why` | P4-W3-T1 | `tests/test_cli_why.py`; gate P4.5 |
| `cost` | P1-W2-T3 (runs), P3-W5-T1 (workloads, sessions, runs) | `tests/test_cli_cost.py` |
| `diff A B` | P4-W2-T4, P4-W3-T2 | `tests/test_diff.py`; `tests/test_cli_diff.py` |
| `findings` | P4-W3-T2 | `tests/test_cli_findings.py` |
| `session start`, `stop`, `list` | P3-W2-T3 | `tests/test_cli_session.py` |
| `report` | P5-W1-T1, P5-W2-T1, P5-W3-T1, P5-W3-T3 | `tests/test_report.py`; `tests/test_cli_report.py`; gate P5.1 |
| `export` | P5-W2-T3 | `tests/test_cli_export.py` |
| `config show`, `check`, `reload` | baseline `show` and `check`; P0-W3-T2, P1-W1-T1 (`--json`), P3-W5-T3 (`reload`) | `tests/test_cli_files.py`; `tests/test_cli.py`; `tests/test_cli_daemon.py` (reload) |
| `rules test` | P3-W3-T4 | `tests/test_cli_rules.py` |
| `store status`, `check`, `backup` | baseline `status`; P1-W1-T1, P3-W5-T2 | `tests/test_cli_store.py` |
| `doctor` and its capability matrix | baseline; P1-W1-T1, P1-W2-T4, P2-W5-T3, P3-W5-T4, P3-W6-T3, P5-W2-T4 | `tests/test_cli_doctor.py` |
| CI on both runners with a 30-minute soak | P0-W1-T1, P0-W2-T4, P2-W6-T2, P3-W6-T2, P4-W4-T2, P5-W3-T2 | `tests/test_project.py`; `tests/test_soak_workflow.py` (dry runs marked `soak`) |
| Recorded fixtures for every provider and detector | P2-O1, P5-O1; synthetic fixtures in P2-W2-T1, P2-W2-T3, P3-W1-T3, P4-W1-T2, P5-W1-T2, P5-W1-T3; replay P2-W6-T4. One exception, put to the owner as Q18: the group provider (component 14) has no recording from the owner's machine; its logic is tested on both runners from job readings written in P3-W1-T3's test, and its live reads on CI-W | `tests/test_recorded_fixtures.py`; `tests/test_job.py` (the group provider's logic on both systems); gate S5 |
| Load generator | P1-W1-T3 | `tests/test_loadgen.py` |
| Default `submeter.toml` and `rules.toml` | in the package; P0-W6-T1 loads both; P0-W4-T2, P2-W1-T1 and P4-W2-T2 keep the first valid | `tests/test_examples.py` |
| Fixture recorder | P2-W4-T3 (any provider of P2-W1-T1's protocols, the GPU providers included; P5-O1 records the GPU) | `tests/test_record_fixture.py` |
| Synthetic store generator | P3-W1-T2 (raw), P3-W3-T3 (history) | `tests/test_synthetic_raw.py`; `tests/test_synthetic_history.py` |
| Windows scheduled task | P0-W5-T2 (probe), P3-W5-T3 | `tests/test_probe_autostart.py`; `tests/test_cli_daemon.py` |
| The brief, `AGENTS.md`, `CLAUDE.md`, `docs/STATUS.md` | present; `docs/STATUS.md` by the lead at every gate (section 4.1, rule 5) | gate P0.11, S3 |
| Runtime dependencies pydantic, psutil and typer; uPlot vendored | P0-W1-T1, P0-W3-T3, P5-W1-T4 | `tests/test_fixed_rules.py`; `tests/test_report_assets.py` |
| Soak monitor and checker, kill test, mutation check (added by this plan) | P2-W5-T4, P2-W6-T1, P0-W6-T1 | `tests/test_soak_tools.py`; `tests/test_kill.py`; `scripts/mutation_check.py` |

### 9.9 Coverage

| Kind | Items | With a task | Done or not in version 1 | Without a task in part |
| --- | ---: | ---: | ---: | --- |
| Jobs | 3 | 3 | 0 | none |
| Fixed rules | 3 | 3 | 0 | none |
| Known limits (L00 to L13) | 14 | 14 | 0 | none |
| Findings R38 to R153 | 116 | 89, and R153 by the plan's text | 21 done or not in version 1; 5 with no work of their own | none |
| Not in version 1 (N01 to N19) | 19 | — | 19 | none |
| Promises P01 to P100 | 100 | 91 | 9 done (P18, P31, P37, P41, P53, P69, P71, P73, P84) | P47's year of `exe_1h` rows, which waits on Q15 |
| Commands and tools | 24 | 23 | 1 present (the brief and the rules files; `docs/STATUS.md` written by the lead) | none |

Section 9.5's 89 and section 9.7's 91 count rows whose remaining work sits in a named task of section 3. Every part of the brief now has a task and a named test, or is not in version 1, except the one part in the last column: keeping `exe_1h` rows for a year needs a deletion that `docs/06-storage.md:9` and `docs/17-build-prompt.md:182` rule out, so it waits on the owner (Q15).

### 9.10 The stage 2 self-check

Stage 2 asks for one check of the plan against itself before stage 3 (`prompts/01-execution-prompt.md:91`). It was run on this plan on 23 November 2026, after the second round of checkers' findings was applied, with a script that reads the task cards of section 3 and rebuilds from them the Tasks column of 3.2, the holders of 4.2, the lists of 4.4, the tables of 5.1 and 5.3 and the counts of 10.1. The plan reviewer runs the same check again at P5 (6.1, row D17) and after any change to section 3.

| Check | What it covers | Result |
| --- | --- | --- |
| Components | The prompt says 25; R119 added the server program as component 26 (`docs/13-build-list.md:33`, commit `5df9dfb`, which changed "21 components in version 1" to 22), so the check covers all 26; R136 adds the items beside the code (`docs/13-build-list.md:42-55`), and 11.7 asks whether to edit `prompts/01-execution-prompt.md:91` | 22 of the 26 are in version 1, and each has between 2 and 23 builder tasks in 3.2, generated from the Advances lines; 04b, the psutil provider, has 6. The other 4 are cut by a ruling: 05 (R151, I12), 20 and 21 (R150) and 25 (R143), each with what stands in for it in 3.2 and 9.6 |
| Items beside the code | `docs/13-build-list.md:42-55` | Each has a task in 9.8 |
| Gates | Every gate has a procedure, numbered pass criteria and an evidence list | 6.2 is the procedure every gate follows; 6.3 gives S1 to S5; 6.4 to 6.9 give P0.1 to P0.14, P1.1 to P1.12, P2.1 to P2.8, P3.1 to P3.6, P4.1 to P4.6 and P5.1 to P5.5, each section ending with its procedure and who checks it; 6.10 says which need the owner or CI |
| Ownership | No path, and no path under an owned folder, has two owners in one wave; no builder task in a phase owns a path under an owner task's folder in that phase | 29 waves and 95 builder tasks: 0 paths owned twice in a wave, 0 builder paths under an owner task's folder |
| Dependencies | Every dependency points to an earlier wave, so no wave holds two tasks of which one needs the other | 0 dependencies on a task of the same or a later wave |
| Pilot | The first wave is small enough to be a pilot | P0-W1: 2 builders, sizes S and M, no path under `src/`; the two shared files it changes, `pyproject.toml` and `uv.lock`, are held by P0-W1-T1 alone (5.4) |
| Traceability | Every row of section 9 names a task and a test, or "not in version 1" | 9.9: one part without a task, P47's year of `exe_1h` rows, which waits on Q15 |


## 10. Cadence

This section says how many waves and sessions the build is expected to take, where the owner is needed, when the build stops and asks, and which mechanism runs the parallel builders. Task ids, decisions (B1 to B20) and plan choices (C1 to C10) are those of sections 3 to 5. Every timing below was measured on the review's Linux machine (R137); nothing here was measured on Windows.

### 10.1 Waves and sessions

| Phase | Waves | Builder tasks (S / M / L) | Spare builder places under the cap of 4 | Owner tasks | Owner's attended time |
| --- | ---: | --- | ---: | --- | --- |
| P0 | 6 | 15 (5 / 5 / 5) | 7 | P0-O1, P0-O2 | about 2 h 45 min |
| P1 | 3 | 9 (1 / 5 / 3) | 3 | P1-O1 | about 30 min |
| P2 | 6 | 23 (1 / 14 / 8) | 1 | P2-O1, P2-O2 | about 2 h, and 24 h elapsed |
| P3 | 6 | 23 (2 / 16 / 5) | 1 | P3-O1 | about 20 min |
| P4 | 4 | 13 (3 / 6 / 4) | 3 | P4-O1 | about 15 min |
| P5 | 4 | 12 (3 / 5 / 4) | 4 | P5-O1, P5-O2 | about 1 h 15 min, and 24 h elapsed if P5-O2 is kept |
| **Total** | **29** | **95 (15 / 51 / 29)** | **19** | **9** | **about 7 h 5 min, and 24 or 48 h elapsed** |

"Spare places" is 4 less the planned width, summed over every wave but the pilot P0-W1, which is held at 2 by design (5.4). The attended times are the Time lines of the owner tasks in section 3, with each 24-hour soak counted at its stated upper bound of 1 hour attended.

**Waves.** 29 are planned. I expect 30 to 33 to run:

- P0 is the first contact with Windows. `docs/17-build-prompt.md:337` expects the baseline to need fixes on CI-W; they run as one or two waves of their own before P0-W2 (K40). P0-O1 turns each failing check on the owner's machine into a fix task (5.5). P0 has 7 spare places after its pilot (1 in P0-W3, 2 in P0-W4, 2 in P0-W5, 2 in P0-W6), so P0-O1's fixes fit unless they need paths a planned task of the same wave owns.
- P2 has 23 tasks and 1 spare place (P2-W1). Any unplanned task in P2 needs a wave of its own.
- After a wave with a merge conflict, an escalated review or a red check after a merge, the next wave runs at 2 builders (5.4), so a planned wave of 4 then takes two dispatches.

**Sessions.** Three kinds, all counted before any unplanned work:

| Kind | Count | Basis |
| --- | ---: | --- |
| Builder sessions | 95 | One per task: section 3.1 sizes every task at one builder session or less |
| Code reviews | 95 to 190 | One per task per round, at most two rounds (Stage 3 principle 5) |
| Record reviews | 29 | One per wave: a reviewer with fresh context reads the lead's record commit before the next wave (4.1 rule 6, C6) |
| Gate reviews | 6 | One per phase gate, never by an agent that did the work |
| Plan reviews, failure investigations | as needed | One per plan change (4.1 rule 7) and per red check after a merge |
| **Agent runs in all** | **225 to 320** | Every parallel approach multiplies token use (`docs/reference/claude-code-notes.md:42`) |

The lead is one more session, restarted several times. It needs at least 6 sessions, one per phase, because every gate ends with a stop and a wait for the owner (`docs/15-phases-and-decisions.md:5`, `docs/17-build-prompt.md:335`), and after approval a new lead session starts from the files (Stage 3 principle 7). I expect about 10, for three reasons:

1. P0 and P2 each hold a likely wait in the middle. In P0 the wait is for B9 and B7 if they are not answered before the build (10.2), and at the end for P0-O2's probes at the gate commit. In P2 it is for P2-O1's fixtures before P2-W6.
2. Proposed here: the lead ends its session at the next wave boundary once its conversation has been compacted. After compaction it works from a summary (`CLAUDE.md:20` lists what to keep). A new session reads the same facts in full from `docs/STATUS.md`.
3. An isolated subagent takes its instruction files from the lead's conversation, not from its worktree (`docs/reference/claude-code-notes.md:34`). So after an approved change to `AGENTS.md`, the lead starts a new session before it dispatches again. Otherwise builders would work to the old rules.

**Time.** Only some of it is known:

- **Measured on Linux** for this plan on 22 November 2026:
  - The seven `AGENTS.md:25-33` checks take 16.8 s per merge with warm caches. 13 s of that is the two `mypy --platform` runs, which invalidate the shared cache each time.
  - `uv sync` and the seven checks take 26.3 s in a fresh working copy.
  - Four fresh copies running the four checks at once took 10.7 to 13.1 s each.
  - So a wave of four merges spends about 67 s on local checks.
- **Fixed by the plan:**
  - A 30-minute CI soak on each runner at the P2, P3, P4 and P5 gates (P2-W6-T2, P3-W6-T2, P4-W4-T2, P5-W3-T2).
  - The owner's 24-hour soak at P2 (P2-O2), and at P5 if kept (P5-O2).
  - Probe 2 runs for about 80 minutes inside P0-O2.
- **Not measured:** how long a builder session, a review or a CI run on each hosted runner takes. So this plan gives no calendar estimate. Instead:
  - For each task, the lead records in `docs/STATUS.md` the times of dispatch, of the pushed branch, of the review verdict and of the merge, and the CI run time.
  - At the P0 gate the lead gives the owner an estimate for P1 to P5 from P0's figures.
  - At the P1 gate it revises the estimate with the cap review of 5.4.
- **Windows-only work is slower to prove.** These 10 builder tasks are proved only on CI-W: P0-W2-T2, P0-W5-T2, P0-W6-T2, P1-W1-T4, P1-W2-T1, P1-W3-T1, P2-W2-T1, P2-W2-T3, P2-W3-T4 and P5-W1-T2. P2-W4-T2 and P3-W1-T3 are proved partly on CI-W, and P3-W4-T1 and P4-W3-T3 each have one case that runs only there. Stage 1 ran on Linux (`docs/review/01-adversarial-review.md:7`). If builders run there too, every Windows test cycle of these tasks is a push and a CI-W run, and each merge waits for CI-W on the task's branch. The repository is public (`gh repo view`, 22 November 2026), and standard GitHub-hosted runners are free for public repositories (GitHub's Actions billing documentation). So the cost of a push is time, not money.

### 10.2 Where the owner is needed

#### Before the first wave

1. **Approve stage 3's output:** the orchestration prompt, the P0 task cards and the starting `docs/STATUS.md`.
2. **Put `main` on `origin`.**
   - On 22 November 2026 `git ls-remote origin` printed nothing: the remote has no branch.
   - Stage 1's push of `main` "was refused by the session's permission checks twice and is still owed" (`docs/review/01-adversarial-review.md:17`).
   - The build needs pushes for three things: CI runs only on pushed branches (P0-W1-T1); a wave's base commit is pushed before the wave (4.1 rule 3); and builders push their branches.
   - `CLAUDE.md:10` already allows these pushes, so this is a permission setting the owner must fix, not a new approval.
   - Updated in stage 3: done for stage 2's commit. On 23 November 2026 at 12:08 `git ls-remote origin` printed `76ebe7124736db49aba2f3ff0c0fdf46cca47401 refs/heads/main`. The stage 3 commit, which holds the task cards and the prompt, is pushed at the end of stage 3 or by the lead (`prompts/02-orchestration-prompt.md` 0 step 2 and 5.1 item 2).
3. **Say where the build sessions run.** The choice is the Windows machine as the signed-in standard user, or Linux as in stage 1 (Q1 in section 11). It decides who runs the owner tasks (below) and whether the Windows points of 10.4 apply.
4. **Approve how builders' commands are allowed to run.**
   - A background subagent surfaces every permission prompt in the lead's session (sub-agents page, "Run subagents in foreground or background"). So a wave runs without the owner only if the builders' commands are allowed beforehand in `.claude/settings.json`, or the owner chooses a permission mode that does not prompt.
   - On Windows, an approval given in a worktree stays with that worktree (worktrees page, "What worktrees share with the main checkout"). So the rules must be in the project settings file before the wave starts.
   - Stage 3 proposes the rules and the owner approves them.
5. **Answer the decisions before the waves they block.**
   - B9 and the wording for `AGENTS.md:35` (11.6, the line-35 part of B10) block P0-W2-T1, the test split on which P0's longest chain starts, so both are needed before P0-W2, and the approved line-35 wording is on `main` at P0-W2's base commit.
   - Four decisions have no default: B7 (needed by P0-W4), B11 (by P2-W3), B8 (by P2-W4) and B12 (by P4-W1). All four also hold up their phase's gate, because P0-W6-T1, P2-W5-T1 (for B11 and B8) and P4-W3-T3 depend on the tasks they block.
   - Recommended: put section 5.6 and section 11 to the owner as one batch before P0-W1, so that no wave waits. Each default the owner leaves standing is recorded in `docs/STATUS.md` as accepted.
6. **tzdata.** `docs/17-build-prompt.md:40` says the owner decides "before the first wave or when a feature first needs named time zones". I82 assumes none in version 1, and no task needs it.

#### During the phases

| When | What the owner does | Attended time | What waits for it |
| --- | --- | --- | --- |
| After P0-W1 integrates | P0-O1: step 1 on the personal Windows 11 PC (the evidence, pushed from there), then on the work PC (each result told to the lead in one word) | about 45 min on each machine | B4 (P2-W2-T3, P2-W4-T2); P0's fix tasks (5.5); gate P0 |
| After P0-W2 integrates | B5 and B6, on P0-W2-T4's CI-runner figures | — | P2-W2-T2 (B6), P2-W4-T2 (B5) |
| Before P0-W4 | B7, if not already answered; Q15, whether `retention.executables` is used in version 1 (default: no) | — | P0-W4-T2, then P0-W6-T1 and gate P0 |
| After P0-W6 integrates, at G0 | B16, then P0-O2: the owner check run, the three probes and a second platform check | about 2 h | B1, B2, B3; gate P0 |
| Gate P0 | Approves the gate; decides B1 on probe 1 and B2 on probe 2. If the Rust trigger fires, the build stops and P2 is planned again (`docs/17-build-prompt.md:63`) | — | every P1 task |
| Before P1-W2 | B13 (the default stands unless overturned) | — | P1-W2-T2 |
| After P1-W3 integrates | P1-O1; if the browser cannot start under the job, rules whether that fails the gate or is the known limit L03 | about 30 min | gate P1 |
| Gate P1 | Approves the gate; reviews the cap of 4 against P1's merge times (5.4) | — | every P2 task |
| Before P2-W3 | B11, if not already answered | — | P2-W3-T2, then P2-W5-T1 and P2-W6-T2 |
| Before P2-W4 | B8, if not already answered | — | P2-W4-T4, then P2-W5-T1, P2-W6 and gate P2 |
| After P2-W4 integrates, while P2-W5 runs | P2-O1: commits the quiet fixture's bound, records the fixtures (the memory-bound load only if Q14 allows it) and runs the anonymisation test on that machine | about 1 h | P2-W6-T3, P2-W6-T4, P4-W1-T2. If it is late, P2-W6 runs with T1 and T2 only |
| After P2-W6 integrates | P2-O2: the 24-hour soak with one sleep | under 1 h; 24 h elapsed | gate P2 |
| Gate P2 | Approves the gate | — | every P3 task |
| Before P3-W3 | B19 (default: refuse to start) | — | P3-W3-T1 |
| Before P3-W5 | B17 (default); B3 is recorded from probe 3 at gate P0; Q16 (default: the four fixed rows in `cost`) | — | P3-W5-T3, P3-W5-T1 |
| After P3-W6 integrates | P3-O1: `daemon install`, sign out and in, re-attach | about 20 min | gate P3 |
| Gate P3 | Approves the gate | — | every P4 task |
| Before P4-W1 | B12 if not already answered; B14 (proposed values); B20 (default (a)) | — | P4-W1-T4 (then P4-W3-T3 and P4-W4-T1), P4-W1-T2, P4-W1-T3, P4-W2-T1 |
| Before P4-W2 | B15 (default: nothing acts) | — | P4-W2-T3 |
| After P4-W4 integrates | P4-O1: `why` timing | about 15 min | gate P4 |
| Gate P4 | Approves the gate | — | every P5 task |
| During P5-W1, if the builder asks | B18: the VRAM source if none works without administrator rights | — | P5-W1-T2 |
| After P5-W1 integrates | P5-O1: GPU fixtures | about 15 min | P5-W4-T1, which replays them for P5.2 |
| After P5-W4 integrates, at G5 | P5-O2: the owner check run, then the final 24-hour soak if the owner keeps it | step 4; under 1 h and 24 h elapsed for the soak | gate P5 |
| Gate P5 | Approves the gate; version 1 is done when section 1.2 holds | — | — |

**Who runs the owner tasks.** If the build sessions run on Linux, the owner runs all nine by hand on the personal Windows 11 PC for the evidence, and P0-O1, P0-O2 and each later gate's owner check run again on the work PC for the one-word results (section 3.1, Owner tasks).

If a session runs on the personal Windows PC as the signed-in standard user, a test-runner agent there can run P0-O1, probes 1 and 2 of P0-O2, P1-O1, P2-O1, P4-O1 and P5-O1. The owner still does five things:
- runs the 24-hour soaks with their sleep (P2-O2, P5-O2);
- does the sign-out and sign-in of P3-O1;
- installs anything a step needs (B16);
- makes the decisions;
- runs P0-O1, P0-O2 and each later gate's owner check run on the work PC, where no agent runs, and tells the lead each result in one word.

**What the owner reads before it is pushed.** The repository is public. `AGENTS.md:44` (R107) anonymises recorded fixtures only. Step 1's output, though, includes `icacls` on Submeter's folders, which prints the account name, and the Defender log and AppLocker policy of the computer. So every owner task replaces the user, host and domain names and the home folder in its output with `scripts/probes/replace_names.py` (P0-W1-T2) and runs the name check of section 6.2 step 4, and the owner reads every file recorded on the personal Windows PC before it is pushed. Nothing recorded on the work PC is committed or pushed: the owner reads its summary screen there and tells the lead each item's word, and the lead records it in the gate section's table "Work PC results by word" (section 3.1, Owner tasks; 6.2 step 4). From P2, `tests/test_fixtures_anonymised.py` (P2-W1-T3), run with `SUBMETER_SCAN_EVIDENCE=1` on that machine, also scans `docs/review/ground-windows/` and `docs/gates/`, outside their `ci/` copies; CI runs it on `tests/fixtures/` only.

**How owner outputs reach `main`** (section 3.1, Owner tasks; section 6.2 steps 4 and 5):
- the owner, or the session on the personal Windows PC, commits the personal PC's output on a branch named `owner/<task id>` and pushes it from there after reading it;
- the lead merges that branch like a builder's, after a reviewer has read it and, from P2 on, the anonymisation scan passes;
- the work PC's results reach `main` only as the owner's one-word statements, which the lead records with their date in the gate section of `docs/STATUS.md`, in the table "Work PC results by word" (6.2 step 4).

**Approvals only the owner can give** (4.3 rules 5 and 6):

- **`AGENTS.md` and `CLAUDE.md`.** Only the line-35 wording blocks a task (P0-W2-T1, B10); the others block none under the plan's defaults (C7). Each needs the owner's approval of the exact wording:
  - B10's three wordings, for `AGENTS.md:39`, `:40` and `:46`;
  - the change option (b) of B9 would make to `AGENTS.md:39`;
  - the consistency review's wordings for `AGENTS.md:46` (R145) and `:39` (R108), in 11.6;
  - the wording for `AGENTS.md:35`, which names `tests/test_baseline.py`, deleted by P0-W2-T1; this one blocks that task and is applied before P0-W2's base commit is fixed (11.6);
  - a separate mypy cache for the win32 run in the `AGENTS.md` checks. This would cut the seven checks from 16.8 s to about 4.8 s per merge on Linux (measured for this plan), which matters for about 95 merges.

  An approved change is applied at a gate, for reason 3 under Sessions in 10.1, except the line-35 wording, which is applied before P0-W2's base commit is fixed; the lead then starts a new session before it dispatches P0-W2.
- **Dependencies** (`AGENTS.md:49`). None is planned.
  - tzdata waits on `docs/17-build-prompt.md:40`.
  - uPlot is approved and is vendored as files (`docs/17-build-prompt.md:39`), so it adds no package.
  - A dev dependency a builder finds it needs, for example a browser driver, is a change request to the owner, not a builder's choice. P5-W4-T1 is written to need none: it reads the browser's own output with the standard library (section 7.5).
- **Software on either Windows machine (the personal PC and the work PC):** node and bash (B16), and anything else a gate would install.
- **The plan's own decisions:** a decision of 5.6, a choice of 5.7, whether P5-O2 is required, and the permission rules in `.claude/settings.json`.

### 10.3 When the build stops and asks

There are three outcomes:
- **Stop:** no new wave is dispatched; tasks already running finish and are recorded, and the lead asks the owner.
- **Hold:** one task waits; the wave runs narrower (5.4, "Blocked tasks") and the owner is asked.
- **Handle and report:** the lead deals with it under the rules already written and reports it at the next stop.

**The build stops and asks the owner when:**

1. **A phase gate is reached.** The gate reviewer checks the evidence against section 6, the lead records the result in `docs/STATUS.md`, and the build waits for approval (`docs/15-phases-and-decisions.md:5`, `docs/17-build-prompt.md:335`, Stage 3 principle 6). Merges inside a wave do not wait for the owner.
2. **Probe 2 fires the Rust trigger.** The trigger is in `docs/11-language.md:21-24`, and `docs/17-build-prompt.md:63` says "stop and tell me". The build stops before P2, and P2 is planned again (B2).
3. **Probe 1's step a or b fails:** this user cannot create a job, or cannot create a child inside a new job. P0-W2-T2's decision function says to stop and ask, because P1's design rests on both steps.
4. **A fixed rule is at risk.** A design or a change would break a rule of `AGENTS.md:9-11`; `tests/test_fixed_rules.py` (P0-W3-T3) fails on `main`; or any step on the work computer asks to elevate.
5. **Security software or policy on the work computer blocks a step.** Examples: an attack surface reduction event naming python.exe, an AppLocker or Device Guard refusal (P0-W5-T2 records the policy), or a quarantined file. The block is never worked around.
6. **A push to `origin` is refused.** There is no other remote to use (`CLAUDE.md:12`), and without pushes there is no CI and no base commit.
7. **`main` keeps failing its checks.** After the first failed check on `main` the lead stops merging. A failure investigator finds the cause and one fix task is dispatched. If that task, within its two review rounds, does not make `main` green, the build stops. History already on `origin` is never rewritten (`CLAUDE.md:11`).
8. **A gate criterion cannot be met as section 6 states it.** The lead does not relax a number or substitute a procedure; the owner rules at the gate.
9. **Unplanned work exceeds the plan** (proposed here, for section 11): a phase needs more than two waves beyond its plan, or P0's fix tasks need more than its 7 spare places. The lead reports this and asks whether to go on or to plan the phase again.

**A task is held and the owner asked, while other work continues, when:**

10. **A decision of 5.6 is not recorded when its task's wave is next.** If no task of the next wave can be dispatched, this becomes a stop.
11. **A change needs the owner's approval** (10.2, Approvals). The task is held only if it cannot be finished without the change (4.3 rule 2).
12. **The brief and the code disagree,** or the brief leaves open something a task needs and no decision of 5.6 or choice of 5.7 covers it (`AGENTS.md:52-54`). B18 is the planned case of this.
13. **A task fails its second review.** The lead escalates it once to a stronger model. If it still does not pass, the lead holds the task and its dependents and asks the owner (Stage 3 principle 5).
14. **An owner task is outstanding,** as when P2-O1 is not done when P2-W6 is due, or P5-O1 when P5-W4 is due. The tasks that depend on it wait.
15. **Something recorded on the personal Windows PC is ready to merge.** It waits until the owner has read it (10.2). Nothing recorded on the work PC is ever merged; its results are the owner's words (section 3.1, Owner tasks).

**Handled by the lead and reported at the next stop:**

- **A merge conflict.** The lead stops the wave's remaining merges, records a planning defect and corrects the plan, and the plan reviewer reads the correction (4.1 rule 7). It asks the owner only if the correction changes a gate, a decision of 5.6 or a choice of 5.7.
- **A red check after a merge** that one fix task makes green.
- **A wave that runs narrower** under 5.4.
- **A builder whose working copy is not at the wave's base commit and cannot reach it.** The builder stops at its first step, and the task is dispatched again at the right commit (10.4, setting 2).

### 10.4 The mechanism for parallel builders

**Choice: Claude Code subagents.**
- The lead starts each subagent with the Agent tool, from a definition in `.claude/agents/` (`docs/reference/claude-code-notes.md:20-22`).
- Every builder has `isolation: worktree`, so it works in its own git worktree on its own branch.
- Every checker is a separate subagent whose `tools` list leaves out Edit and Write. When a checker must run the tests before and after a change (Stage 3 principle 4), it runs them in its own worktree of the branch under review.
- Agent teams, `/batch`, agent view and dynamic workflows are not used for builders.

I checked the notes of 20 November 2026 against the current pages on 22 November 2026: "Create custom subagents", "Orchestrate teams of Claude Code sessions", "Run parallel sessions with worktrees", "Run agents in parallel" and "Orchestrate subagents at scale with dynamic workflows", all at code.claude.com. They agree on every point below. Stage 3 checked the choice again on 23 November 2026 and it still holds. The documentation now differs from the notes on ten points, listed in `prompts/02-orchestration-prompt.md` 11.9: two of them corrected the Windows points at the end of this section, and four settings follow from them (forks off, nesting off, at most 8 subagents at once, ultracode off; prompt 11.2).

| | Subagents in worktrees (chosen) | Agent teams | Dynamic workflows | Agent view | `/batch` |
| --- | --- | --- | --- | --- | --- |
| Status | No experimental or preview label in the notes or on the subagents page | "Experimental and disabled by default"; enabled with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` (notes:38; agent-teams page) | No label; on all paid plans (workflows page). The notes record nothing about its stability (notes:41) | "Research preview" (notes:40; agents page) | A bundled skill that uses subagents in worktrees (notes:39) |
| After a resumed session | A finished subagent continues with SendMessage, history intact (notes:25). Transcripts persist, and "You can resume a subagent after restarting Claude Code by resuming the same session" (subagents page) | "`/resume` and `/rewind` do not restore in-process teammates" (agent-teams page, Limitations; notes:38) | A run can be relaunched from saved results in the same session; "In a fresh session, Claude has no earlier run to relaunch and starts the workflow over" (workflows page) | — | — |
| Isolation | Its own worktree and branch (notes:29). Edits and commands aimed at the main checkout are blocked (notes:33) | "Agent teams don't isolate teammates in worktrees" (agents page; notes:38) | Agents can be isolated, but a stalled agent restarts from its prompt and "files the stalled attempt already changed stay changed" (workflows page) | Sessions move into a worktree before editing (agents page) | One worktree per subagent |
| The lead's judgment between producer and checker, and the owner's at a gate | The lead decides after each result | The lead decides | "No mid-run user input"; sign-off between stages needs one workflow per stage (workflows page) | The owner dispatches each session by hand | One large change with no dependency order and no gate |
| Fits the width | 8 agents at the cap (5.4), against a default limit of 20 running subagents (notes:24; subagents page) | — | Up to 16 concurrent agents by default | — | 5 to 30 subagents: more than the pilot of 2 and the cap of 4 |

**Why subagents.**
- They are the only option of the five that is neither experimental nor a preview and that can be resumed after a restart: by resuming the same session, a finished builder can be continued by its agent ID.
- Each builder gets the isolation exclusive ownership needs: its own checkout at the wave's base commit, and its own branch for the lead to merge in dependency order.
- The lead keeps the judgment the wave loop needs: escalation after two rounds, stopping merges on a conflict, scheduling change requests. A workflow script would have to encode all of that in advance, and could not wait for the owner partway through a run.
- The definitions are Markdown with YAML frontmatter, so their bodies can carry the same role text as the neutral role files, which keeps Claude Code-specific material under `.claude/` (Stage 3 principle 8).

**The build does not depend on any agent surviving an interruption.** State is in files (principle 7), and every builder pushes its branch as it goes (`CLAUDE.md:10`).

**Settings and rules the choice brings.** Stage 3 writes these out in full.

1. **Agent teams stay off.** `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` must be unset or `0` for the whole build. While agent teams are enabled, "a subagent that Claude names launches as a teammate", and "an `isolation` value in the subagent's frontmatter doesn't prevent it, and the teammate then runs in the main session's working directory" (subagents page, "Subagent names"; agent-teams page, "How Claude starts agent teams"). That would put a builder in the main checkout.
2. **The base commit.**
   - By default a worktree branches from the remote's default branch. Under the default `"fresh"` base, Claude Code fetches only when the repository "hasn't been fetched in the last 24 hours", capped at 5 s. Setting `worktree.baseRef` to `"head"` makes worktrees branch from the current local commit (notes:30; worktrees page, "Choose the base branch").
   - Proposed: `"worktree": {"baseRef": "head"}` in the project's `.claude/settings.json`. When it dispatches a wave, the lead's checkout is on `main` at the wave's base commit, and `main` has already been pushed (`CLAUDE.md:18`; 4.1 rule 3).
   - Each builder's first step compares `git rev-parse HEAD` with the base commit B. Changed in stage 3: B is given in the dispatch message and recorded in `docs/STATUS.md`, not written on the card, because a card that held B would need a commit made after B. A new working copy that is not at B switches to B (`git switch --detach <B>`; it holds nothing yet) and checks again, and the builder stops only if B cannot be reached (`prompts/02-orchestration-prompt.md` 3.4 step 1).
3. **A fresh environment per worktree.** Each worktree runs `uv sync` before anything else (notes:31; `CLAUDE.md:19`). On Linux this took 0.81 s offline with uv's cache filled, and makes about 101 MB of virtual environment per worktree (measured for this plan).
4. **Removing worktrees.** After merging a branch, the lead removes its worktree with `git worktree remove` (notes:32). Claude Code locks a worktree while its agent runs. A worktree with changes is otherwise kept until a periodic sweep (worktrees page, "Worktree locks and manual removal").
5. **Recording a dispatch.** At dispatch the lead records in `docs/STATUS.md` each task's agent ID and branch, and at the verdict the agent ID of its reviewer. Changed in stage 3: the worktree path is recorded from the builder's report, not at dispatch, because Claude Code chooses the path (`prompts/02-orchestration-prompt.md` 11.5). These records exist so that the gate reviewer can confirm that each gate harness was built by an agent that built none of the tasks it tests (section 6.2 step 6). Builders commit and push their branch as they go, and end with a pushed branch and their task report (3.1, Size).

**Resuming after an interruption.** The lead, whether resumed or new, does three things:
1. It reads `docs/PLAN.md`, `docs/STATUS.md` and the open task cards.
2. It lists `git worktree list` and the branches on `origin`.
3. For each dispatched task that has no recorded verdict, it takes the first of these that applies:
   - If this is the same session resumed, it continues the builder with SendMessage, using the agent ID recorded at dispatch.
   - If the task's branch is pushed with its report, it sends the branch to review.
   - Otherwise it dispatches the task again from its card at the same base commit. The old branch and worktree are kept: the new builder reads any unpushed work in them, and nothing is deleted until the task is merged.

**On Windows, if the build sessions run on the owner's personal Windows PC** (never on the work PC, from which nothing is committed or pushed; section 3.1, Owner tasks)**:**
- Sandboxed commands are not available on native Windows (notes:9), so nothing but permission rules limits what a builder's commands can touch.
- For PowerShell commands, worktree isolation applies only its working-directory check (notes:33; worktrees page, "How Claude Code enforces isolation"). Corrected in stage 3 against the documentation of 23 November 2026: with Git for Windows installed, the PowerShell tool is on by default for claude.ai and Console accounts and "Claude treats PowerShell as the primary shell" (tools reference, "PowerShell tool"); notes:8 is out of date. So no subagent definition lists the PowerShell tool, and builders and checkers use Git Bash, where all four checks apply (`prompts/02-orchestration-prompt.md` 11.3). Proposed: Git for Windows on the work computer, which counts as software for the owner to approve if it is not already there.
- Each worktree adds `.claude\worktrees\<name>\` to every path inside it. Corrected in stage 3: Claude Code chooses the name of a subagent's worktree, and the documentation gives no way to set it, so worktrees cannot be named by task id. The task id is carried by the branch pushed to `origin` (`task/<task id>`), and paths are kept short by keeping the clone at a root of 40 characters or fewer, with `git config core.longpaths true` in it (`prompts/02-orchestration-prompt.md` 11.6). Section 8 carries path length and antivirus scanning of each worktree's virtual environment as risks.


## 11. Open questions for the owner

Every question the plan leaves to the owner, in one place. Each has an id: B1 to B20 are the decisions of section 5.6, C1 to C10 the plan's choices of section 5.7, I-numbers the **Assumption** entries of `docs/review/02-rulings.md`, R-numbers the findings, and Q1 to Q18 the questions this section adds. Each row carries one mark:

- **Blocks** a task: the task is not dispatched until the answer is recorded in `docs/STATUS.md` (section 5.6).
- **Before** a task: the task is written for the default or the assumption shown. An answer that changes it must arrive before that task is dispatched; after that it means reworking merged code.
- **None**: no task waits on it. It is a wording, a document already changed, or something the owner should know.

An answer such as "accept the defaults" confirms every default and assumption below. Any item can also be answered on its own by its id. Line references follow section 3.1: `docs/NN:line` is that line of `docs/NN-*.md`.

### 11.1 What to answer first

The build reaches these first, in this order:

1. **Before the pilot wave P0-W1:** Q1 (the machine the build sessions run on), Q2 (Python versions in CI, P0-W1-T1), I82 (no tzdata, P0-W1-T1), C3 (where probes and test tools live, P0-W1-T2), C6 (the lead writes `docs/14` and `docs/STATUS.md`, every wave).
2. **Before P0-W2, the second wave:** B9 and the `AGENTS.md:35` wording of 11.6 (the line-35 part of B10) block P0-W2-T1, the test split on which P0's longest chain starts (section 5.2). Also before P0-W2-T3: C8. Before P0-W3-T1, the record fields: I9, C4, C7 and the fields of I2.
3. **Before P0-W4:** B7 blocks P0-W4-T2, and Q15 shapes it. Before P0-W4-T1: I12, I42, C5.
4. **Before the owner's probe session P0-O2:** B16.
5. **On P0's outputs, before gate P0:** B1, B2 and B3 are decided on the three probes (P0-O2), B4 on step 1 (P0-O1), and B5 and B6 on P0-W2-T4's CI-L figures. Each blocks tasks in P1, P2 or P3 (11.2).

Section 11.10 lists every question by the wave it first affects.

### 11.2 Decisions that block tasks (section 5.6)

| Id | Question | Default in this plan | Mark |
| --- | --- | --- | --- |
| B1 | Which holder keeps a tagged group open, and how the run file's final state is written; decided on probe 1's output (P0-O2) | `docs/17:75-77` as written, if reopening the job by name behaves as gate P0.8 step d expects | Blocks P1-W1-T2, P1-W1-T4, P1-W2-T1 |
| B2 | Python or Rust for the collector, and the default intervals; decided on probe 2 (P0-O2) and the trigger of `docs/11:21-24` | Python at 2 s active and 5 s idle, if the bulk provider stays under 3% of one core at 2 s, 1% at 5 s and 83,886,080 private bytes (80 MiB); if the trigger fires, the build stops and P2 is planned again | Blocks P2-W2-T1, P2-W5-T1 |
| B3 | A scheduled task or the `HKCU\...\Run` key for `daemon install`; decided by probe 3 (P0-O2) under the rule of `docs/15:19`; if the work PC's word differs, the owner rules at the gate (6.4, P0.12) | The scheduled task, unless a standard user cannot register it | Blocks P3-W5-T3 |
| B4 | Whether Windows counts interrupt and DPC time inside system time; decided by step 1's per-core check (P0-O1) under the rule P0-W1-T2 writes; if the work PC's word differs, the owner rules at the gate (6.4, P0.12) | None: the measured ratios decide | Blocks P2-W2-T3, P2-W4-T2 |
| B5 | The cost at which reading every leaf cgroup's `cpu.stat` "breaks the budget" (R60, I22); judged on P0-W2-T4's CI-L figure | R60 stays if one round of reads costs under 0.1% of one core at the 5 s idle interval | Blocks P2-W4-T2 |
| B6 | Whether Linux workload memory totals use PSS for every process (R46, I28); judged on P0-W2-T4's CI-L figure | Adopted if a full round costs less than 0.1 percentage points of one core more than the 25-largest round at the 30 s `uss_interval`, judged on CPU ms per GB resident | Blocks P2-W2-T2 |
| B7 | The eight bounds `docs/08:78-94` marks "not set yet": the upper bound of `retention.raw`, `retention.executables`, `disk_budget`, the memory part of `change_threshold`, `leak.min_duration`, `leak.min_slope`, `verdict.window` and `alerts.cooldown` | None | Blocks P0-W4-T2 |
| B8 | The batch stamp after a backward wall-clock step, and under slow drift between the interval clock and the wall clock (R55; `docs/17:100`; `docs/review/02-rulings.md:282`). Options: (a) re-anchor back, with a clock-step event and an epoch, so stamps decrease and the store must accept rows for an earlier day; (b) keep the anchor, so stamps stay ahead of the wall clock until a later forward step; (c) converge slowly, never decreasing. The reverted attempt left stamps 1 h ahead after a 1 h step back, and drifted +130 s in 30 days at +50 ppm | None | Blocks P2-W4-T4, and through it P2-W5-T1. P2-W3-T1's store rule holds under every option (section 3.6) |
| B9 | How `submeter run` reaches the launcher, and the report's place in `LAYER`: `cli` and `programs` are both layer 3 (`tests/test_layers.py:20-21`) | (a) The CLI starts the launcher as a child process (`python -m submeter.programs.launcher`); `report` sits at layer 2, imports only `core` and renders records the CLI fills. (b) would put `cli` at a layer 4 and change `AGENTS.md:39` and `docs/17:49` | Blocks P0-W2-T1, P1-W2-T2, P5-W1-T1, P5-W2-T1, P5-W3-T1, P5-W3-T3 |
| B10 | The `AGENTS.md` wordings waiting for approval; see 11.6 | Line 35: the wording of 11.6, which must be approved; the other lines unchanged, and records stay in `core/models.py` (C7) | Blocks P0-W2-T1 for the line-35 wording only; None for the others |
| B11 | What makes the machine busy or quiet for adaptive cadence; `docs/08:57-59` gives only the durations | None | Blocks P2-W3-T2, P2-W6-T2 |
| B12 | The runaway process count: its definition, threshold, window and finding; `docs/17:200` names it and defines none of them | None | Blocks P4-W1-T4 |
| B13 | On Linux, whether `submeter run` sets `SUBMETER_RUN` and writes a run file. Read with the R151 question in 11.7 | Neither; `cost --run` on Linux says tagged runs are unavailable | Blocks P1-W2-T2 |
| B14 | The leak gate's statistics: noise per raw row or per 1-minute step, the row interval, seeds, pass rates and the staircase's deadline | Rows every 30 s, uniform ±40 MiB per row, 200 seeds; at least 190 of 200 leaks flagged by 2 h 5 min; 0 of 200 warm-ups flagged over 6 h; at least 190 of 200 staircases flagged by 6 h | Blocks P4-W1-T2, P4-W2-T1 |
| B15 | What acts on `attribution.unattributed_alert`; `docs/08:99` names no consumer | Nothing acts on it until decided | Blocks P4-W2-T3 |
| B16 | Whether node.exe and bash.exe are on the owner's machine, and whether they may be installed | Probe 1 and the P1 gate skip those steps and say so | Blocks P0-O2, P1-O1 |
| B17 | `daemon start` on Linux in version 1 | Starts both entry points as detached processes; `install` and `uninstall` say they are unavailable on Linux | Blocks P3-W5-T3 |
| B18 | The Windows source of the adapter's VRAM total; the P5-W1-T2 builder looks first, the owner decides if no source works without administrator rights | Stop and ask; the floor allows a GPU-bound rule-out rewritten so that it does not need VRAM (`docs/15:77`) | None at dispatch: P5-W1-T2's builder is the one who looks, and the task is held (section 10.3, item 12) only if it finds no source |
| B19 | What the server does when `history.db` fails its integrity check at start | Refuses to start and logs it; `doctor` and `store check` report it; no repair | Blocks P3-W3-T1 |
| B20 | Whether growth is tracked for each process as well as for each workload (R116, I38). `docs/07:29` and `docs/17:198` say both. (a) needs a per-process series reader and runs the leak check once per process; (b) tracks growth per workload only and deletes "for each process" from both lines | (a), as the brief says: P4-W1-T3 also reads 1-minute series per process from raw process rows, and P4-W2-T1 checks each | Blocks P4-W1-T3, P4-W2-T1 |

### 11.3 Assumptions in the rulings

The 32 entries of "How the rulings combine" that carry an **Assumption**. The line is that of the assumption in `docs/review/02-rulings.md`. Each was applied to the brief as written here; overturning one changes the documents named in its entry and the tasks shown.

| Entry | Line | Assumption taken | Mark |
| --- | --- | --- | --- |
| I2 | 142 | Option (a): each sample and bucket records awake seconds, the growth of the clock that stops during suspend; CPU and I/O rates and capacity in core-seconds divide by awake seconds; `covered_s` stays observed time for memory means, histograms and `well_covered()`. (b) would keep a gap's CPU and I/O as separate sums, outside every rate | Before P2-W1-T2 (P0-W3-T1 adds the optional fields) |
| I5 | 146 | Query-time merges of raw rows put each sample whole in the step that holds its end (R53's rule, one function with stored buckets); R38's proportional split is not built | Before P3-W3-T2; also P4-W1-T3's 1-minute steps |
| I7 | 149 | Option (a): `source` names the CPU accounting path (KERNEL, POLLED, COUNTERS) and partiality is carried per field by missing-member counts. (b) would add a source per field | Before P0-W5-T1 |
| I9 | 152 | The raw schema stays version 1 and is changed in place, because no build has written raw files outside tests; the server assigns epochs when it reads raw rows, so `WorkloadSample` carries no epoch | Before P0-W3-T1; also P2-W3-T1 |
| I12 | 156 | Component 05 is not in version 1; Linux runs the psutil provider, whose Linux branch reads `/proc/PID/stat` for R56's start stamp and R64's kernel-thread mark; R40's nested-reaping fixture moves to the psutil provider's tests; Linux runs at the overhead guard's longer intervals | Before P0-W4-T1; also P2-W2-T2, P2-W3-T3, P2-W4-T2 |
| I17 | 162 | A process is Restricted when an attribution input (command line or owner) is unreadable, or on Linux when its owner differs from the collector's (R77 (a)); each field's availability is recorded on its own; R64's "restricted only when CPU or memory is unreadable" is not applied | Before P0-W5-T1; also P2-W2-T2, P2-W3-T4 |
| I21 | 167 | `docs/02` keeps its dashboard content under a lead sentence saying the dashboard is planned for version 1.1 and version 1 shows the figures through the CLI and the report (now `docs/02:5`) | None |
| I22 | 169 | R60 stays in version 1: unseen Linux CPU is placed by cgroup from `cpu.stat`, read in the psutil provider's Linux branch; its cost is measured on CI-L in P0, and the work is dropped if that breaks the budget (B5) | Before P0-W2-T4; P2-W4-T2 is held by B5 |
| I24 | 172 | "Not seen by polling" is a machine-level column in `system_raw` beside `cpu_busy_s`, not a workload series, so R106's reserved names are unchanged | Before P2-W1-T1; also P2-W2-T4, P2-W3-T1 |
| I28 | 177 | Linux full PSS is measured in P0 on CI-L: every readable process once, with the CPU cost and the process count, labelled a CI-runner figure, and judged at `uss_interval` because the cold interval is gone | Before P0-W2-T4; P2-W2-T2 is held by B6 |
| I29 | 179 | Option (a): at start the collector seeds its attribution map from the open raw file's process table and workload-change events, then runs the rules, so a restart (every settings change, R149) keeps inherited workloads. (b) would state in `docs/10` that inheritance from an exited parent is lost at each restart | Before P2-W2-T4; also P2-W5-T1 |
| I30 | 181 | USS or PSS at `uss_interval`; the command line on Windows once per new process (R126) and on Linux again at `uss_interval`, with R47's rule retry on a change; the working folder only when a rule uses `cwd`, at `uss_interval`; psutil's read of command lines through the process environment block is a stated exception while the fallback runs. See R126 in 11.4 | Before P2-W2-T2; also P2-W3-T3, P2-W3-T4 |
| I33 | 185 | The run-id variable is `SUBMETER_RUN`, not `SUBMETER_RUN_ID` | Before P1-W1-T2; also P1-W2-T1 |
| I36 | 189 | `config reload` stops the programs through their stop files and starts them as `daemon start` does, which on Windows runs the scheduled task so that R50's settings hold | Before P3-W5-T3 |
| I38 | 192 | The leak check reads raw workload rows merged on read into 1-minute steps of time-weighted means, over up to 48 h or the raw data on disk, whichever is shorter. See R116 in 11.7 | Before P4-W1-T3; also P4-W2-T1 |
| I42 | 197 | Option (b): a process whose start time cannot be read has no key; it appears only in a per-snapshot unreadable count, shown beside Restricted by `doctor` and the reconciliation, and its CPU falls in "not seen by polling". (a) would make `ProcessKey.started` optional | Before P0-W4-T1; also P2-W2-T4, P2-W5-T2, P2-W5-T3 |
| I45 | 201 | The `submeter` workload is the set of pids from the collector's and server's pid files plus each holder's pid in its run file's live state, matched on pid and start stamp; the launcher uses PROC_THREAD_ATTRIBUTE_JOB_LIST and stays outside the job. See R69 in 11.7 | Before P1-W1-T2; also P1-W2-T1, P2-W5-T1, P3-W2-T4 |
| I50 | 207 | The verdict task's builder sets starting values for the absolute disk queue and latency thresholds and tunes them on the fixtures, as `docs/07` says of every threshold | Before P4-W2-T2 (P0-W4-T2 leaves the values None) |
| I51 | 209 | Linux GPU load is in version 1 (NVML and DRM fdinfo, tested from recorded fixtures); the Linux GPU-bound verdict comes after version 1 | Before P5-W1-T3, which is dropped if this is overturned |
| I54 | 213 | The sample time explorer in `docs/08` is cut to the active interval and the process count, keeping the overhead and capture columns; the raw-row and disk columns stay out until P2 measures rows and bytes per tick | None (`docs/08:7-51` already says so; P2-W6-T2 measures) |
| I56 | 216 | In P0 the Rust trigger compares the collector's share with the whole budget, because no server or holder exists yet; the summed budget of every Submeter process is checked at the P2 soak and again with the server in P3 | Before P0-W6-T2; B2 is decided on its output |
| I57 | 218 | The settings of deferred features (SlowGrowth, Baseline, `Api` port and `mcp_enabled`, `Ui`, `Alerts.quiet_hours` and `channels`, and R148's two fields) stay in `config.py`, marked in `docs/08` as not used in version 1, with no ranges added | Before P0-W4-T2; also P4-W2-T3 |
| I61 | 223 | The collector deletes its own raw files older than the larger of 7 days and `retention.raw`; only the server enforces `disk_budget`, so the budget is not enforced while the server is down | Before P2-W5-T1; also P3-W4-T1 |
| I67 | 230 | No `baseline` table in version 1's history schema; a migration adds it with the feature | Before P3-W1-T1 |
| I75 | 239 | The agent-cost check (`submeter cost --run "$SUBMETER_RUN" --json`, with no command line or working folder in the output) is part of the P1 gate | Before P1-W3-T1 (gate item P1.10); also P1-W2-T3 |
| I78 | 243 | The report section states that every value taken from data is HTML-escaped and that any script in the report inserts data with `textContent` | Before P5-W1-T1; also P5-W2-T1, P5-W4-T1 |
| I81 | 247 | The synthetic store generator stays, for P3's retention and disk-budget tests and the P5 report; the 30-day dashboard load gate is dropped | Before P3-W1-T2; also P3-W3-T3 |
| I82 | 249 | The approval of tzdata is recorded, but tzdata is not added in version 1, because no version 1 code uses a named time zone | Before P0-W1-T1 |
| I85 | 253 | `submeter store backup` writes a backup request file beside the stop files; the server polls it, writes the backup and removes the request, so the server stays the only writer of `backups/` | Before P3-W2-T3; also P3-W4-T2, P3-W5-T2 |
| I87 | 256 | Findings get a `submeter findings` command; `why` and the report also show them | Before P4-W1-T1; also P4-W3-T2 |
| I89 | 259 | The Phase column of `docs/13`: 01-03 P0; 04, 06 (Windows half), 07 and 09 P2; 05 after version 1; 08 "P1 on"; 10 P3; 11 "P2 on"; 12 "P1 on"; 13 P1; 14 "P1, P3"; 15 "P2 on"; 16 P2; 17-19 and 22 P4; 23 and 24 P5; 20, 21 and 25 not in version 1. Section 3 follows it | None (`docs/13:11-33`); a change moves tasks between phases |
| I94 | 265 | `AGENTS.md`'s one-writer line stays as it is until the owner approves new wording; see 11.6 | None |

### 11.4 Questions from the moved code changes and from the `fix now` builders

Seven `fix now` code changes moved to the plan (`docs/review/02-rulings.md:276-286`). R56 raised no question: psutil's float cannot carry a Windows FILETIME (K20), so P0-W4-T1 reads CreateTime as an integer with GetProcessTimes. The others, and the questions the builders of the kept changes left:

| Finding | Question | Default | Mark |
| --- | --- | --- | --- |
| R55 | The rule after a backward wall-clock step and under slow drift: B8 | None | Blocks P2-W4-T4 |
| R38, R39 | The gap rule and the gap handling ship together in P2-W1-T2 (I1). Until then the baseline keeps the fixed 30 s gap rule, so `submeter top --seconds` with a value from 31 to 60 prints zeros (`docs/review/02-rulings.md:281`; `docs/14:289`). Is that acceptable through P0 and P1? | Yes | None; P2-W1-T2 removes it |
| R57 | Whether a process whose start time cannot be read is counted without a key: I42 | I42 (b) | Before P0-W4-T1 |
| R111 | The eight bounds marked "not set yet": B7 | None | Blocks P0-W4-T2 |
| R145 | The minute tier stays in the code until P0-W3-T1 removes it; the `AGENTS.md:46` wording is in 11.6 | — | None |
| R99 | Scrub's secret-name rule as built differs from the accepted wording, "bounded by start, '-', '_' or end" (`docs/review/01-adversarial-review.md:846`). That wording stopped scrub hiding values it hid before, such as those after `-storepass`, `-keypass`, `--passphrase`, `-passin`, `--authtoken`, `--dbpassword` and `--accesstoken`, and those of `PGPASSWORD=` and `-Djavax.net.ssl.trustStorePassword=`. The built rule (`src/submeter/privacy/redact.py:27-31`, `:46-52`): a secret word counts wherever it ends a word of the flag or name, at `-`, `_`, `.` or the end, with no start bound; `pass` also matches `passphrase`, `passin` and `passout`; `pass` after `com` or `by` does not count, so `--compass` and `--bypass-cache` are kept; the opaque test exempts a string starting with `/` and a UUID. It still misses a string starting with `/` and a secret word followed by more letters or digits (`--password2`, `--passwords`) (`docs/review/fixes/R99.md`). Scrub is opt-in and best-effort (R96); `exe_only` is the default. Keep the built rule, or rebuild to the accepted wording? | Keep the built rule | None; a rebuild is a change request on `privacy/redact.py` |
| R126 | May the collector read a process's working folder, which needs PROCESS_VM_READ, and its USS, for which psutil opens the process with PROCESS_QUERY_INFORMATION (`docs/17:92`), when command lines are read with PROCESS_QUERY_LIMITED_INFORMATION only? If not, `cwd` rules cannot match on Windows, and every figure built from USS (the total-unit memory, and a tagged group's current memory under R67) reads unavailable on Windows | Both allowed as stated exceptions (P2-W3-T4): the working folder only when a rule uses `cwd`, USS for the `uss_top_n` largest at `uss_interval` | Before P2-W3-T4; also P2-W3-T3's schedule |
| R49 | When `SUBMETER_RUN` is missing, the run file records the parent as unknown (`docs/17:80`). A top-level run never has the variable, so every top-level run reads "parent unknown". Should a run without the variable record "no parent" instead, accepting that a nested run that lost the variable (through sudo, `env -i` or a sandboxed shell) then looks top-level? Either way the parent's total is not reduced by that child | As `docs/17:80` says: unknown | Before P1-W1-T2 (the field's values); also P1-W2-T1 |
| R61 | Accepted with a recorded breach of "unavailable, never zero": a tagged group without I/O accounting, whose members polling never saw, reports I/O and memory as 0 until R42's planned task makes those fields optional. The strict expected failure at `tests/test_attribution.py:109-112` holds the required behaviour (`docs/review/fixes/R61.md:7-14`). Is the breach acceptable until P0-W5-T1 merges? | Yes | None; P0-W5-T1 removes the breach and the expected failure (section 1.2, D13) |

### 11.5 `fix now` changes kept although over about fifty lines

Step 3 of "After my rulings" moves a change to the plan when it grows past about fifty changed lines. The rulings took up to about 55 as "about fifty" (`docs/review/02-rulings.md:278`); R58 and R59 are past that too. Keep all seven, or name any to revert and move to the plan?

| Finding | Changed lines, source and tests | What the change does | What a revert would also remove |
| --- | ---: | --- | --- |
| R58 | 62: 52, plus a 10-line repair a review required (`docs/review/fixes/R58.md:26,48`) | Keeps a process when one read fails, and keeps zombies | The `fake_process` test helper that six later findings' tests use |
| R59 | 57: 55 plus 2 (`docs/review/fixes/R59.md:22,44`) | Detects suspend with a clock that stops during it | The clock R38 builds on |
| R100 | 55 (`docs/review/fixes/R100.md:32`) | Makes Submeter's folders 0700 and its files 0600 from creation | — |
| R97 | 54 | Stores the executable name in `exe_only` mode, never a rewritten argv[0] | — |
| R47 | 52: 45 plus 7 (`docs/review/fixes/R47.md:22,35`) | Keeps a process's workload for life unless it execs into a rule | — |
| R71 | 52 (`docs/review/fixes/R71.md:30`) | The lock's 5 s retry and the size check | — |
| R99 | 51: 28 plus 23, 12 of them R96's docstring text (`docs/review/fixes/R99.md:20,33`) | Matches secret names as whole words of a flag | — |

Default: keep all seven. Mark: None; a revert would add a task to P0.

### 11.6 `AGENTS.md` wordings waiting for approval (B10)

`AGENTS.md` changes only with the owner's approval of the exact wording (section 4.3, item 5). The R103, R107 and R134 changes are already made. These wait. The line numbers are those of `AGENTS.md` today: R107 added line 44 and R134 lines 30-31, so the line `docs/review/02-rulings.md:264` cites as `AGENTS.md:43` for I94 is now line 46.

| Line now | Text now | Proposed | Source | What approval changes in the plan |
| --- | --- | --- | --- | --- |
| 46 | "the server writes minute and history files" | "the server writes the history file and its backups" | R145, I94; wording from the consistency review | Removes the last statement of minute files. No task changes |
| 39 | The layer list ends "then `cli`" and does not name `programs` | "... then `cli` and `programs`. No program imports another. ... add a new program to `PROGRAMS`" (R108, I79). This plan adds: the line should also name `alerts` and `report`, which P0-W2-T1 adds to `LAYER` at layer 2 under B9 (a) | R108, I79; `tests/test_layers.py:21,23` already has `programs` and `PROGRAMS` | `AGENTS.md` matches the layer test. No task changes |
| 40 | "Subclass `Record` in `core/models.py`" | New records may live in their own `core` modules | R112, I79 | `core/models.py` stops being held by one task per phase (C7): P1-W1-T2, P2-W1-T1, P3-W1-T1, P4-W1-T1 and P5-W1-T1 could put their records in new modules, and other tasks in their waves could add records without a change request |
| 43 | "redacted before it is stored, logged or written into a test fixture" | Optional: "never logged", to match `docs/17:177`, where logs never contain command lines | I72 (`docs/review/02-rulings.md:235`) | None |
| 35 | "To run one test: `uv run pytest tests/test_baseline.py -k NAME`." | "To run one test: `uv run pytest tests/test_<component>.py -k NAME`, where `<component>` names the component's test file (`docs/17-build-prompt.md:43`)." | This plan: P0-W2-T1 splits `tests/test_baseline.py` into one file per component and deletes it | The line names a file that exists. Blocks P0-W2-T1 (B10) |
| 30-31 | The two `mypy --platform` commands share `.mypy_cache` with the plain run | Give each platform run its own `--cache-dir` | This plan. On the review's Linux machine on 22 November 2026 the seven commands took 16.8 s with warm caches, 13 s of it in the two platform runs, which invalidate the shared cache each time; with a cache per platform each mypy run took about 0.5 s and the seven commands about 4.8 s | The lead's checks after each merge get shorter (section 5.4) |

Default: `AGENTS.md` unchanged, except line 35. Mark: None for every row but line 35, which Blocks P0-W2-T1: the task is not dispatched until the owner has approved the wording and it is on `main` at P0-W2's base commit, because without it `AGENTS.md:35` names a deleted file to every later session, and merges inside a wave are automatic, so a hold at merge would not stop it.

### 11.7 Left by the consistency review

Item 3 of the consistency review's list is 11.6. The others:

| Finding | Question | Default | Mark |
| --- | --- | --- | --- |
| R116 (I38) | `docs/07:29` and `docs/17:198` track growth per workload "as well as for each process". Does growth per process read raw process rows (a), or is growth tracked per workload only (b)? This is decision B20 (11.2) | (a); P4-W1-T3 and P4-W2-T1 are written for it | Blocks P4-W1-T3 and P4-W2-T1 (B20) |
| R136 (I91) | `prompts/01-execution-prompt.md:91` asks the stage 2 self-check to cover "the 25 components". The brief numbers 26 because R119 added the server program as component 26 (`docs/13:33`, commit `5df9dfb`), and R136's accepted change has that line count the items beside the code with the components; but `prompts/` is not edited (I91 says so of `prompts/01:19`). Edit `prompts/01:91`, or leave it? | Leave `prompts/` unedited; the self-check covers the 26 numbered components and the items beside the code (`docs/13:42-55`); section 3.2 lists all 26, and section 9.10 records the check | None |
| R151 | No document says how the processes of a polled Linux run get its `--as` name. With B13's default (no run file and no `SUBMETER_RUN` on Linux), nothing tells the collector which processes belong to the run, so the rules attribute them and the name appears nowhere in the stored data. Accept that, or have the Linux run write a run file with the command's pid and start stamp so the collector attributes that process and its descendants to the name, polled? | Accept: the name has no effect on Linux in version 1, and `docs/10:12` says so | Before P1-W2-T2 (with B13); the second option also adds work to P2-W5-T1 |
| R153 (I89) | Confirm row 08 of `docs/13`, `store.files`, now "P1 on" (`docs/13:18`), with the other I89 rows in 11.3 | "P1 on": P1-W1-T2 adds the run files to `FileMap` | None |
| R69 (I45) | Record the launcher's own pid and start stamp in the run file, so that the `submeter` workload claims it, and should CLI processes join the `submeter` workload too? Under the default the soak monitor records both apart, reported and not judged (P2-W5-T4). Without it the launcher, and under B9 (a) the `submeter run` process that starts it, are attributed by the rules like any process: `examples/rules.toml:34-38` would give a python.exe whose working folder is under `C:\src` to `builds`. Neither the collector's `self_pids` nor the soak monitor of P2-W5-T4, which finds Submeter processes by pid file, run file and entry point, includes the launcher | No (I45 as written) | Before P1-W1-T2; a yes adds a field to P1-W1-T2, a write to P1-W2-T1 and a read to P2-W5-T1 and P2-W5-T4 |
| docs/06 and docs/17 on backups | `docs/06-storage.md:15` says a backup is "a compacted copy of the history file"; `docs/17-build-prompt.md:180` says "SQLite's online backup", whose API copies pages as they are and does not compact. `docs/README.md:76` says the topic file is right and the difference is a defect to report. Which does P3-W4-T2 follow? | `docs/06:15`: P3-W4-T2 writes each backup with `VACUUM INTO`, which compacts and runs while the server and readers hold the file, so it is also an online backup; docs/17:180 is left as written unless the owner wants it reworded. Checked for this plan on 23 November 2026 with SQLite 3.45.1: a 10,272,768-byte file with half its rows deleted gave a 5,140,480-byte copy, mode 0600 kept from the empty file created first, `integrity_check` ok, with another connection's read transaction open | Before P3-W4-T2 |
| R129 | Should the server also raise a finding when a `-wal` file grows past `journal_size_limit`? Today `submeter store status` and `doctor` warn (`docs/06:40`) | No | Before P3-W4-T4, which would raise it |

### 11.8 The plan's own choices (section 5.7)

No ruling covers these. Each is written into the tasks shown; the owner may overturn any of them before those tasks are dispatched.

| Id | Choice | Mark |
| --- | --- | --- |
| C1 | `submeter top` keeps taking its own two snapshots and does not read the collector's raw file, so it works without the collector | Before P2-W5-T2 |
| C2 | `daemon install` registers one scheduled task per program, so each program restarts on failure on its own | Before P3-W5-T3 |
| C3 | Probes live in `scripts/probes/`; test tools in the package `tests/tools/`, type-checked by the `AGENTS.md` mypy commands, not shipped in the wheel, run as `uv run --directory tests python -m tools.<name>` | Before P0-W1-T2 (the pilot wave); also every probe and tool task |
| C4 | `SampleBatch` keeps its machine-total busy figure beside the new per-core figures, so the record task leaves `sampler.py` and `raw.py` alone | Before P0-W3-T1 |
| C5 | `boot_id` travels on the `Snapshot` and in the raw file's `meta` table, and a different `boot_id` starts a same-day second raw file | Before P0-W4-T1; also P2-W3-T1 |
| C6 | `docs/14-baseline-modules.md` and `docs/STATUS.md` are written by the lead's record step from the builders' reports, never by a builder | Before P0-W1 (every wave) |
| C7 | Records passed between layers stay in `core/models.py`, held in each phase by one task (follows from B10) | Before P0-W3-T1; also each phase's contract task |
| C8 | CLI commands register by discovery: each module of `submeter.cli` whose name does not start with an underscore exposes `register(app)` | Before P0-W2-T3; also every command task |
| C9 | P0 carries R112, R145, R57 with R56, R111, R42 with R46, and R110, besides the probes and CI. Overturning it moves these into P1 and P2 | Before P0-W2 |
| C10 | Gate evidence for P1 to P5 goes under `docs/gates/P<n>/`, and the owner's runs under `docs/gates/P<n>/owner/`; P0's stays under `docs/review/ground-windows/` (`docs/15:23`) | Before P1-O1 |

### 11.9 Other questions the plan needs answered

| Id | Question | Default | Mark |
| --- | --- | --- | --- |
| Q1 | Which machine do the build sessions run on: the Windows 11 computer as the signed-in standard user (`prompts/01-execution-prompt.md:3`), or Linux, as stage 1 did (`docs/review/01-adversarial-review.md:7`, `:1694`)? On Windows a test-runner agent can run most `owner_machine` cases; on Linux the owner runs all nine owner tasks by hand, and Windows-only tasks are proved only on CI-W | Either; a Windows-only task is done only when CI-W passes (section 3.1, OS) | Before P0-W1; affects every Windows (CI-W) task and every owner task |
| Q2 | Which Python versions CI runs: 3.13 only (`pyproject.toml:5` requires 3.13 or later), or 3.13 and a later release as well? The review's Linux figures came from Python 3.14.5 | 3.13 only | Before P0-W1-T1 |
| Q3 | Must step 1 on the owner's machine (the seven checks and `scripts/platform_check.py`) pass for gate P0? | Each failing check becomes a fix task (section 5.5), and the gate waits for it unless the owner rules the failure acceptable | Before P0-O1 |
| Q4 | If a standard user cannot read the Defender Operational log (R126's check in P0-O1, again in P0-O2 and P2-O2), how is it read? | Recorded in `docs/STATUS.md` as not verified | None |
| Q5 | Approve the numbers section 6 sets where the brief leaves them to the plan: the share of capacity "not seen by polling" must stay under on the quiet fixture (P2.4; `docs/15:41`), which must be fixed before the fixture is recorded; the collector's memory-growth limit in the 24-hour soak (P2.6; `docs/15:43`); the data and conditions under which `why` must answer in under 2 s (P4.5); and what "degrades cleanly" means for a provider (P5.3) | The values in section 6 | Before P2-O1 (the P2.4 share), P2-O2, P4-O1 and P5-W4-T1 |
| Q6 | Keep the final 24-hour soak (P5-O2), proposed because the server's analysis and the GPU providers are added after P2's soak? | Kept | None; it adds a day before gate P5 |
| Q7 | If a Chromium-based browser cannot start its renderers under `submeter run` (R68 expects some programs to fail), does gate item P1.9 fail, or is it recorded as the known limit L03? | Recorded as L03, with the result in `docs/STATUS.md` | Before P1-O1 |
| Q8 | Accept the run-time and static checks of the three fixed rules this plan adds, though no gate in `docs/15` checks them: P0-W3-T3's static test, P1-W1-T4's read-back of a tagged job's limit flags as 0, and the soak checker's 0 sockets and unelevated token (P2-W5-T4) | Accepted | Before P0-W3-T3 |
| Q9 | How the verdict's confidence (low, moderate or high) is computed; `docs/07:109-111` uses it and no document defines it | The P4-W2-T2 builder writes the computation into `docs/07`, and the owner reads it at gate P4 | Before P4-W2-T2 |
| Q10 | The source of "a power-saving plan is active", the ruled-out condition of the thermally throttled verdict (`docs/07:120`); no document names one | The P4-W2-T2 builder names a documented source that needs no administrator rights; without one, the condition reads unavailable | Before P4-W2-T2 |
| Q11 | `docs/06:117` keeps load per core "per core class hourly", and no document defines a core class. Is it, for example, performance and efficiency cores, is load stored hourly per core, or only as a machine figure? | Performance and efficiency cores, as Windows reports a class for each logical processor; one class on Linux and on a processor without classes. P2-W2-T3 reads each logical processor's efficiency class with GetLogicalProcessorInformationEx, P2-W3-T1 stores it in each raw file's `meta` table, P3-W1-T1 writes how load per class is stored into `docs/06`, and P3-W2-T2 builds it | Before P2-W2-T3; also P2-W3-T1, P3-W1-T1, P3-W2-T2 |
| Q12 | How Submeter is installed on the owner's machine, given that the scheduled task runs the installed entry point, not `uv run` (`docs/17:244`, `:260`). The method decides the path the task registers and what the AppLocker policy recorded by probe 3 must allow | The scheduled tasks run the console scripts of the virtual environment of the clone that `daemon install` is run from (`.venv\Scripts\`), so nothing is installed beyond `uv sync`; P4.5 times `.venv\Scripts\submeter.exe` (section 6.8). Another method, for example `uv tool install`, is software on the work computer for the owner to approve | Before P3-W5-T3; also P3-O1 and P4-O1 |
| Q13 | Job 2 on Linux: with PSI and the Linux system counters after version 1, `why` on Linux reads Inconclusive or unavailable (I37; `docs/17:288`). R151's decision named only job 1. This is for the owner to know; no ruling needs to change | — | None |
| Q14 | May P2-O1 load the personal Windows PC, whose recordings are the fixtures (section 3.1, Owner tasks), with a memory-bound load (the load generator's `memory` mode, up to a share of the commit limit, for at least 6 minutes) to record the memory-bound verdict's counter set? It may disturb the owner's other work | Recorded at a share the owner chooses at the time; if the owner declines, the memory-bound verdict fixture is synthetic (P4-W1-T2) and `docs/STATUS.md` says so | Before P2-O1 |
| Q15 | `retention.executables` (`docs/08:79`, default 1 year) keeps `exe_1h` rows for a year (`docs/06:103`), but no task deletes them, and deleting rows conflicts with `docs/06:9` ("retention is always a file delete") and `docs/17:182` ("Never delete history automatically"). Is the setting unused in version 1? | Unused in version 1: P0-W4-T2 marks it so in `docs/08`, as I57 does for other settings, and `exe_1h` rows are kept; its bound in B7 is then not needed | Before P0-W4-T2 |
| Q16 | `docs/04-features.md:17` and `docs/17-build-prompt.md:127` say that System, Restricted, Unattributed and Submeter are always shown, with the CPU time not seen by polling beside them, but the `submeter cost` sample at `docs/03-cli-output.md:11-22` shows no `submeter` row and no not-seen figure. Both `docs/03` and `docs/04` are topic files (`docs/README.md:75`). Which does `cost` follow, and does the report follow the same? | `docs/04:17`, which states the rule; the sample omits it. `cost` (P3-W5-T1) and the report (P5-W3-T3) show the four rows, with no members if none, and the not-seen figure beside them, and P3-W5-T1 adds both to the `docs/03` sample | Before P3-W5-T1; also P5-W3-T3 |
| Q17 | When an epoch starts inside an hour, what does that hour's bucket hold? `docs/06:67` and `docs/17:159` give every bucket one epoch id, and no document says what happens when an epoch boundary falls inside an hour, as a rules change at a restart or a provider status change usually will | (a) One row per epoch: the hour's samples before the boundary form one bucket and those after it another, each with its own epoch id, so that no bucket mixes two rules files and sums still add across both; `rollup_1h` is keyed by hour, workload and epoch (P3-W1-T1). (b) One row per hour, carrying the epoch of its last sample and a mark that an epoch began inside it | Before P3-W1-T1 (the `rollup_1h` key); also P3-W2-T2 and P3-W3-T1 |
| Q18 | `docs/17-build-prompt.md:49` asks that each layer be testable in isolation from recorded fixtures, and `docs/13-build-list.md:47` asks for recorded fixtures for every provider. The group provider (component 14) is recorded nowhere: recording it needs a live tagged run whose run file the recorder would pass to `GroupProvider.read`, and an owner task in the middle of P3, while P3-O1 runs only at the gate. Is a recording needed? | No: P3-W1-T3 tests the provider's deltas, child-run subtraction and mapping of members to keys on both runners from job readings written in its test, in the shape P1-W1-T4's calls return, and its live reads on CI-W, which is a real Windows; 9.8 states the exception. A yes adds an owner task after P3-W1, a change to the recorder and a replay task | Before P3-W1-T3 |

### 11.10 Which questions each wave meets

The first wave or owner task each question affects. "Blocks" holds the named task; "Before" means an answer that changes the default must arrive before the named task is dispatched.

| Wave or owner task | Blocks | Before |
| --- | --- | --- |
| P0-W1 (pilot) | — | Q1 (all tasks); Q2, I82 → P0-W1-T1; C3 → P0-W1-T2; C6, C9 |
| P0-W2 | B9, B10 (the `AGENTS.md:35` wording, 11.6) → P0-W2-T1 | C8 → P0-W2-T3; I22, I28 → P0-W2-T4 |
| P0-W3 | — | I2 (fields), I9, C4, C7 → P0-W3-T1; Q8 → P0-W3-T3 |
| P0-W4 | B7 → P0-W4-T2 | I12, I42, R57, C5 → P0-W4-T1; I50, I57, Q15 → P0-W4-T2 |
| P0-W5 | — | I7, I17 → P0-W5-T1 |
| P0-W6 | — | I56 → P0-W6-T2 |
| P0-O1, P0-O2 | B16 → P0-O2 | Q3 → P0-O1; Q4 |
| Gate P0 | B1, B2, B3, B4, B5, B6 are decided on P0's outputs | — |
| P1-W1 | B1 → P1-W1-T2, P1-W1-T4 | I33, I45, R49, R69 → P1-W1-T2 |
| P1-W2 | B1 → P1-W2-T1; B9, B13 → P1-W2-T2 | R151 (`--as` on Linux) → P1-W2-T2 |
| P1-W3, P1-O1 | B16 → P1-O1 | I75 → P1-W3-T1; Q7, C10 → P1-O1 |
| P2-W1 | — | I24 → P2-W1-T1; I2 → P2-W1-T2 |
| P2-W2 | B2 → P2-W2-T1; B6 → P2-W2-T2; B4 → P2-W2-T3 | I17, I30 → P2-W2-T2; Q11 → P2-W2-T3; I29, I42 → P2-W2-T4 |
| P2-W3 | B11 → P2-W3-T2 | I30 → P2-W3-T3; R126 → P2-W3-T4 |
| P2-W4 | B4, B5 → P2-W4-T2; B8 → P2-W4-T4 | — |
| P2-W5 | B2 → P2-W5-T1 | I61 → P2-W5-T1; C1 → P2-W5-T2 |
| P2-W6, P2-O1, P2-O2 | B11 → P2-W6-T2 | Q5 (P2.4 share), Q14 → P2-O1; Q5 (P2.6 limit) → P2-O2 |
| P3-W1 | — | I67, Q11, Q17 → P3-W1-T1; I81 → P3-W1-T2; Q18 → P3-W1-T3 |
| P3-W2 | — | I85 → P3-W2-T3 |
| P3-W3 | B19 → P3-W3-T1 | I5 → P3-W3-T2 |
| P3-W4 | — | docs/06 against docs/17 on backups (11.7) → P3-W4-T2; R129 → P3-W4-T4 |
| P3-W5, P3-O1 | B3, B17 → P3-W5-T3 | Q16 → P3-W5-T1; I36, C2, Q12 → P3-W5-T3 |
| P4-W1 | B14 → P4-W1-T2; B20 → P4-W1-T3; B12 → P4-W1-T4 | I87 → P4-W1-T1; I38 → P4-W1-T3 |
| P4-W2 | B14, B20 → P4-W2-T1; B15 → P4-W2-T3 | I50, Q9, Q10 → P4-W2-T2 |
| P4-O1 | — | Q5 (P4.5 conditions), Q12 |
| P5-W1 | B9 → P5-W1-T1 | B18 → P5-W1-T2's merge, only if its builder finds no source; I78 → P5-W1-T1; I51 → P5-W1-T3 |
| P5-W2, P5-W3 | B9 → P5-W2-T1, P5-W3-T1 | — |
| P5-W4, P5-O2 | — | Q5 (P5.3) → P5-W4-T1; Q6 → P5-O2 |
| No task | — | B10's other wordings (11.6); I21, I54, I89, I94; R38 with R39, R61, R99, R136, R153 row 08; the seven kept changes of 11.5; Q13 |


