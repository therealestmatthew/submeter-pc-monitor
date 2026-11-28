# Submeter version 1: build status

The state of the build, kept by the lead of `prompts/02-orchestration-prompt.md`. A new lead session reads this file first and continues from "Next action". `docs/PLAN.md` says what is built; this file says where it stands. Only the lead writes it; how is at the end.

## 1. Where the build stands

| Field | Value |
| --- | --- |
| Updated | 2026-11-28 08:33, lead session 4: wave P0-W1 recorded. Both tasks merged; integration commit `e17cd5b`; CI success on both runners; the pilot is clean. The record review's round 1 asked for the review times of P0-W1-T2, now restored; OQ-01 (section 7.9) is open |
| Phase | P0, decision probes, CI and the baseline repairs (`docs/PLAN.md` 3.4) |
| Wave | P0-W1, the pilot: integrated and recorded; the record review is `docs/tasks/P0-W1-record-review.md`. Next wave: P0-W2, planned width 4 |
| Base commit B | P0-W1: `799feea19e9c226d4389104ae573fca389ef5b12`. P0-W2: not fixed; it is fixed by the next lead session after the `AGENTS.md` wordings are on `main` and the CI run of that commit has passed on both runners (prompt 5.2 step 6) |
| Width | The pilot ran 2 builders and was clean (section 4), so later waves run at their planned width, up to the cap of 4 (plan 5.4) |
| Gate P0 | not started |
| Build machine | Linux (Q1, the owner, 2026-11-25). A Windows-only task is done only when CI-W passes. The owner runs the nine owner tasks by hand as a standard user: in full on a personal Windows 11 PC, whose evidence is pushed, and again on the work PC, from which nothing is committed or pushed and whose results the owner gives in a word (section 7.10, 2026-11-28; PD-003) |
| Lead session | 4 (section 13), on Linux; started 2026-11-28 05:48 |
| **Next action** | P0-W1 is recorded. In order: (1) lead session 4 pushes the record and its review note, removes the worktrees of the two merged tasks (prompt 5.7 step 6), commits the two `AGENTS.md` wordings of section 7.7 word for word, and ends its session (prompt 5.7). (2) The owner starts lead session 5 as before: the terminal in the repository root, `claude`, no `/cd`, and the message of prompt section 13. (3) Lead session 5 runs prompt section 0, then P0-W2 from prompt 5.2 at width 4: P0-W2-T1 (B9 and B10 are decided; it may be dispatched once the line-35 wording is on `main`), P0-W2-T2, P0-W2-T3, P0-W2-T4. Before fixing B it answers the lead's card questions CQ-04 to CQ-07 and checks that the CI run of B passed on both runners. Lead session 5 also has PD-003 (section 9; the owner's answers in section 7.10) corrected: the plan writer rewrites where Windows evidence comes from, the plan reviewer reads it, and the owner approves the wording before it is merged. The owner may try the step-1 procedure (`docs/review/ground-windows/step1-procedure.md` at `e17cd5b`) on the personal Windows 11 PC at any time, but commits no evidence until PD-003 is corrected. B7 is asked again before P0-W4. |

## 2. Entry conditions of the pilot P0-W1

From prompt section 5.1. Tick each with the date and the evidence.

| # | Condition | State | Evidence |
| --- | --- | --- | --- |
| E1 | The owner approved stage 3's output: `prompts/02-orchestration-prompt.md`, `.claude/agents/`, `.claude/settings.json`, `docs/tasks/`, this file and stage 3's changes to `docs/PLAN.md` (S3-1), and it is committed (prompt 0 step 2) | met 2026-11-25 | The owner, 2026-11-25: "S3-1: I approve stage 3's output as committed in 75974eb." `git log -1 --format=%h -- prompts/02-orchestration-prompt.md` printed `75974eb`. The owner also said that commits `def084a` to `72ea6f8` corrected `docs/01`, `docs/02`, `docs/14`, `docs/17`, `docs/README.md`, `prompts/README.md` and `README.md` after the stage 3 commit, and that none of them touches stage 3's output |
| E2 | `main` is on `origin` and holds the stage 3 commit: `git ls-remote origin refs/heads/main` prints the sha of `git rev-parse main`, and `git cat-file -e main:docs/tasks/P0-W1-T1.md` exits 0 (S3-2) | met 2026-11-25 | 2026-11-25 00:15: `git ls-remote origin refs/heads/main` printed `72ea6f849b7314af73fb0c792cca41ef574e2082`, equal to `git rev-parse main`; `git cat-file -e main:docs/tasks/P0-W1-T1.md` exited 0; `75974eb` (stage 3) is an ancestor, 7 commits back. Earlier, 2026-11-23 12:08: `git ls-remote origin` printed `76ebe7124736db49aba2f3ff0c0fdf46cca47401 HEAD` and the same sha for `refs/heads/main`, which is stage 2's commit. The stage 3 commit was not yet made |
| E3 | The build machine is decided (Q1), and this lead session runs on it (prompt 5.1 item 3); Q2, I82, C3, C6 and C9 answered or their defaults accepted | met 2026-11-25 | The owner, 2026-11-25: "Build machine (Q1): Linux. This session runs on it."; "Q2: CI runs Python 3.13 only."; "I82, C3, C6, C9: the defaults in docs/PLAN.md section 11 stand." `uname -s` printed `Linux` in lead session 1 |
| E4 | The owner approved how builders' commands run: the rules and `env` values of `.claude/settings.json` (S3-3) and the lead's permission mode (S3-4); and the owner accepted the workspace trust dialog for the clone the lead runs in, without which the allow rules and the agents' hooks are not applied (prompt 11.3) | met 2026-11-25 by the owner's word; see L1-1 and L1-2 in section 7.5 for what lead session 1 found | The owner, 2026-11-25: "S3-3: the rules and env values in .claude/settings.json, as written."; "S3-4: manual permission mode (default) with the allow list, never bypassPermissions. I accepted workspace trust for this clone." In lead session 1 the five `env` values of `.claude/settings.json` were set in the shell, but ultracode was on and the Agent tool did not offer the seven roles (section 7.5) |
| E5 | If the build runs on Windows: Git for Windows present, the clone at a root of 40 characters or fewer, `git config core.longpaths true` in it (S3-7) | not applicable 2026-11-25 | Q1 is Linux |
| E6 | Recommended: every decision of plan 5.6, every question of plan 11 and the card questions of section 7.3 that the owner answers, put to the owner as one batch (prompt 5.1 item 5) | put 2026-11-25; put again 2026-11-26 | Section 7.6 lists the batch put to the owner in lead session 1; answers not yet received. Lead session 2 put the same batch again in its report on 2026-11-26, because the message that started it answered Q1 and none of the open items. Answered 2026-11-26 in the message that started lead session 3 (section 7.7); B7 alone is still open |

## 3. Phase P0 tasks, dispatches and branches

### 3.1 Tasks

States: `not started`, `held` (blocked by a decision, section 6), `dispatched`, `review 1`, `round 2`, `review 2`, `escalated`, `passed`, `merged`, `blocked` (waiting on the owner). "Builder" and "Reviewers" are agent ids.

| Task | Title | Size | OS | Depends on | Blocked by | State | Builder | Reviewers | Rounds | Merge commit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P0-W1-T1 | CI on both runners, and the test markers | S | either; proves itself on CI-W and CI-L | none | — | merged 2026-11-28 07:31 (review 1: CHANGES, 2026-11-28 06:12; review 2: PASS, 2026-11-28 07:30) | a2e4578a3da7272e7 | a9ed66ba48f1e849a (round 1), aa82c4bf999d77348 (round 2) | 2 | `202584d` |
| P0-W1-T2 | Step-1 helper scripts for the owner's machine | M | either | none | — | merged 2026-11-28 08:16 (review 1: BLOCKED on size alone, 2026-11-28 07:38; review 2: PASS, 2026-11-28 08:16, after the size exception of PD-001) | a06e70300853747a2 | a4c80656d57c366e5 (round 1), a90f33ab3552dd27c (round 2) | 2 | `e17cd5b` |
| P0-W2-T1 | The test split and the layer rows | L | either | P0-W1-T1 | B10: the `AGENTS.md:35` wording is approved (section 7.7) but not yet on `main`; B9 decided 2026-11-26 | held | | | | |
| P0-W2-T2 | Probe 1: the Job Object | M | Windows (CI-W) | none | — | not started | | | | |
| P0-W2-T3 | The CLI package | M | either | P0-W1-T1 | — | not started | | | | |
| P0-W2-T4 | Linux CI measurements for cgroup reads and full PSS | S | Linux (CI-L) | P0-W1-T1 | — | not started | | | | |
| P0-W3-T1 | The optional record fields, and the minute tier removed from the code | L | either | P0-W2-T1 | — | not started | | | | |
| P0-W3-T2 | Named settings and rules files exit with code 2 | S | either | P0-W2-T3 | — | not started | | | | |
| P0-W3-T3 | Static tests for the three fixed rules | S | either | none | — | not started | | | | |
| P0-W4-T1 | Unreadable CPU, capped deltas and integer start stamps | L | either | P0-W3-T1 | — | not started | | | | |
| P0-W4-T2 | Settings validation | M | either | P0-W3-T1 | B7 | held | | | | |
| P0-W5-T1 | Unavailable and partial figures, and the two memory units | L | either | P0-W4-T1, P0-W3-T2 | — | not started | | | | |
| P0-W5-T2 | Probe 3: per-user autostart | S | Windows (CI-W) | none | — | not started | | | | |
| P0-W6-T1 | Tests for the behaviours the mutation check left unguarded | M | either | P0-W5-T1, P0-W4-T2 | — | not started | | | | |
| P0-W6-T2 | Probe 2: the bulk snapshot and the Rust trigger | L | Windows (CI-W) | P0-W5-T1, P0-W4-T1 | — | not started | | | | |

15 builder tasks: 5 of size S, 5 M, 5 L.

| Owner task | What | Time | When | Depends on | Blocked by | State | Branch | Merge commit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P0-O1 | Step 1 on the Windows machine | about 45 min | after P0-W1 integrates | P0-W1-T2 | — | not started | `owner/P0-O1` | |
| P0-O2 | The three probes and a second platform check | about 2 h | at the gate commit G0 | every P0 builder task | — (B16 decided 2026-11-26) | not started | `owner/P0-O2` | |

Unplanned tasks (prompt 5.2 step 3, 8.5) get a row here too when they are added, and their own row in section 10.

### 3.2 Dispatches

One row per builder dispatched (prompt 5.3 step 3), written at dispatch; the worktree path is added from the builder's report, because Claude Code chooses it (prompt 11.5).

| Task | Round | B | Model | Builder agent id | Dispatched | Branch | Worktree path |
| --- | --- | --- | --- | --- | --- | --- | --- |
| P0-W1-T1 | 1 | `799feea` | opus | a2e4578a3da7272e7 | 2026-11-28 06:02 (the builder's own start, 06:02:57; the lead read the clock at 06:05, after both builders were started) | `task/P0-W1-T1` | `/code/submeter-pc-monitor/submeter-pc-monitor-extract/.claude/worktrees/agent-a2e4578a3da7272e7` |
| P0-W1-T1 | 2 | `799feea` | opus | a2e4578a3da7272e7 (the same builder, continued) | 2026-11-28 06:13 | `task/P0-W1-T1` | as round 1 |
| P0-W1-T2 | 1 | `799feea` | opus | a06e70300853747a2 | 2026-11-28 06:03 (the builder's own start, 06:03:00; the lead read the clock at 06:05, after both builders were started) | `task/P0-W1-T2` |`/code/submeter-pc-monitor/submeter-pc-monitor-extract/.claude/worktrees/agent-a06e70300853747a2` |

### 3.3 Branches on origin

Every branch an agent or the lead is expected to push, added when the agent is dispatched or the branch is pushed. After each checker and each builder returns, `git ls-remote origin` must show no branch that is missing here (prompt 11.4 steps 9 and 10). `main` is always expected.

| Branch | Pushed by (task or role, agent id) | Added | State (open, or merged at a sha) |
| --- | --- | --- | --- |
| ~~`main`~~ | ~~the lead~~ | ~~2026-11-23~~ | ~~on `origin` at `76ebe71` (stage 2)~~ |
| `main` | the lead | 2026-11-25 | always expected; at `72ea6f8` when lead session 1 began (replaces the row above, which gave stage 2's commit) |
| `task/P0-W1-T1` | P0-W1-T1, builder a2e4578a3da7272e7 | 2026-11-28 06:05 | merged at `202584d`; branch tip `5b8bb43` |
| `task/P0-W1-T2` | P0-W1-T2, builder a06e70300853747a2 | 2026-11-28 06:05 | merged at `e17cd5b`; branch tip `6139e62` |
| `plan/p0-w1-t2-size` | the lead as plan writer (PD-001) | 2026-11-28 07:40 | merged at `5635cf4`; branch tip `95b52eb` |

## 4. Waves of P0

| Wave | Planned width | Run width | B (base) | Checks at B | Dispatch commit | I (last merge) | R (record) | Record review | CI on R |
| --- | ---: | ---: | --- | --- | --- | --- | --- | --- | --- |
| P0-W1 | 2 | 2 | `799feea19e9c226d4389104ae573fca389ef5b12` | Linux, 2026-11-28, 19 s for all seven: sync=0 ruff=0 format=0 mypy=0 mypy-win32=0 mypy-linux=0 pytest=0; `61 passed, 1 xfailed in 2.99s` | `9f937ac` | `e17cd5b` (merge of P0-W1-T2; P0-W1-T1 merged at `202584d`). CI run 46148834972 on it: success, checks-linux 16 s, checks-windows 42 s | the commit `Record P0-W1` | `docs/tasks/P0-W1-record-review.md` | read when P0-W2's base commit is fixed (prompt 5.2 step 6) |
| P0-W2 | 4 | | | | | | | | |
| P0-W3 | 3 | | | | | | | | |
| P0-W4 | 2 | | | | | | | | |
| P0-W5 | 2 | | | | | | | | |
| P0-W6 | 2 | | | | | | | | |

"Checks at B": the exit code of each of the seven `AGENTS.md` checks run at B in the lead's checkout, and pytest's summary line (prompt 5.2 step 6). An inserted wave (P0-W1a, P0-W1b; prompt 5.2 step 3, 8.5) gets a row below the wave it follows.

Pilot result (plan 5.4), 2026-11-28: clean. Both tasks merged without a conflict. Every check that passed at B passed after each merge (Linux: all seven exit 0 after `202584d`, `64 passed, 1 xfailed`; after `e17cd5b`, `75 passed, 1 xfailed`) and on both runners (CI runs 46145099315 and 46148834972: success in checks-windows and checks-linux). Each review was settled within two rounds: P0-W1-T1 CHANGES then PASS; P0-W1-T2 BLOCKED on size alone then PASS after the size exception of PD-001. No escalation. The baseline's first run on CI-W brought no failure, so no fix wave P0-W1a is needed (prompt 8.5). Later waves run at their planned width, up to the cap of 4. One planning defect came out of the pilot (PD-001, section 9); it was a wrong size on a card, not a conflict or a red check.

## 5. Gate P0

| Field | Value |
| --- | --- |
| State | not started |
| Gate commit G0 | |
| Evidence commit E | |
| Verdict | `docs/gates/P0/verdict.md` (not written) |
| Owner's answer | |
| Tag | `gate-P0` (not set) |

Evidence goes under `docs/review/ground-windows/` (`step1/`, `probes/`, `ci/`); plan 6.4.

## 6. Decisions

Plan 5.6 decisions that a P0 task or the P0 gate needs, and the rows gate item P0.12 checks. A task blocked by a decision is not dispatched until its row here says "decided".

| Id | Decision | Default | State | Choice | Evidence | Decided by | Date |
| --- | --- | --- | --- | --- | --- | --- | --- |
| B1 | The holder that keeps a tagged group open, and how the run file's final state is written | `docs/17-build-prompt.md:75-77`, if probe 1 behaves as P0.8 steps d and h expect | open; decided at gate P0 on P0-O2 | | | | |
| B2 | Python or Rust for the collector, and the default intervals | Python, 2 s active and 5 s idle, if the trigger of `docs/11-language.md:21-24` does not fire | open; decided at gate P0 on P0-O2 | | | | |
| B3 | Scheduled task or `HKCU\...\Run` key for `daemon install` | the scheduled task, unless a standard user cannot register it | open; decided by probe 3 (P0-O2) | | | | |
| B4 | Whether Windows counts interrupt and DPC time inside system time | none: step 1's ratios decide | open; decided by P0-O1 | | | | |
| B5 | Threshold at which reading every leaf cgroup's `cpu.stat` breaks the budget (R60) | R60 stays if one round costs under 0.1% of one core at 5 s | open; on P0-W2-T4's CI-L figure | | | | |
| B6 | Linux workload memory totals by PSS for every process (R46) | adopted if a full round costs under 0.1 percentage points of one core more than the 25-largest round at 30 s | open; on P0-W2-T4's CI-L figure | | | | |
| P0.8 f | The breakaway record of probe 1 step f | skipped with B16's reason if node or bash is absent | open; recorded at P0-O2 | | | | |
| B7 | The eight bounds `docs/08-configuration.md:78-94` marks "not set yet" | none | open; blocks P0-W4-T2. The owner, 2026-11-26: "B7: not answered yet; hold P0-W4-T2 and ask me again before P0-W4." | | | | |
| B9 | How `submeter run` reaches the launcher, and the report's place in `LAYER` | (a): the CLI starts the launcher as a child process; `report` at layer 2 importing only `core` | decided | (a) | the owner's words, section 7.7 | the owner | 2026-11-26 |
| B10 | The `AGENTS.md` wordings of plan 11.6 | line 35 reworded (prompt section 12, S3-8); the other lines unchanged | decided; not yet applied. P0-W2-T1 stays held until the line-35 wording is on `main` | lines 35 and 46 reworded as section 7.7 gives them; the other lines unchanged | the owner's words, section 7.7 | the owner | 2026-11-26 |
| B16 | Whether node.exe and bash.exe are on the owner's machine, and whether they may be installed | probe 1 and the P1 gate skip those steps and say so | decided | the default: probe 1 and the P1 gate skip those steps and say so | the owner's words, section 7.7 | the owner | 2026-11-26 |

The other decisions (B8, B11 to B15, B17 to B20) are needed from P1 on; plan 11.10 says which wave meets each.

## 7. Waiting on the owner

Each item has an id, a mark and a default. **Blocks**: the task is not dispatched until the answer is recorded. **Before**: the task is written for the default; a different answer must arrive before the task is dispatched. **None**: nothing waits on it. "Accept the defaults" confirms every default below.

### 7.1 From stage 3 (prompt section 12)

| Id | Question | Default | Mark |
| --- | --- | --- | --- |
| S3-1 | Approve stage 3's output, including its changes to `docs/PLAN.md` (prompt section 12); if it is not committed, whether the lead commits it (prompt 0 step 2) | — | Blocks P0-W1 |
| S3-2 | Put the stage 3 commit on `origin` (stage 3 or the lead pushes; the owner pushes or fixes the permission if refused). Stage 2's commit `76ebe71` is on `origin` already | — | Blocks P0-W1 |
| S3-3 | The allow, ask and deny rules and the `env` values in `.claude/settings.json`, including the PowerShell tool turned off, `git remote add` allowed only for `origin`, file edits under the repository root allowed, and edits of `AGENTS.md` and `CLAUDE.md` always asked | as written | Before P0-W1 |
| S3-4 | The lead's permission mode, and workspace trust accepted for the lead's clone (E4) | Manual (`default`) with the allow list; never `bypassPermissions` | Before P0-W1 |
| S3-5 | Models: `opus` for builders, plan writer and checkers; `sonnet` for the test runner; `fable` for escalation. Not checked: whether the account may use `fable` | as stated; if the Agent call refuses `fable`, the escalation goes to the owner | Before the first escalation |
| S3-6 | The concurrency limit of 8 subagents | 8 | None |
| S3-7 | On Windows: Git for Windows; a clone root of 40 characters or fewer; `core.longpaths` | — | Before P0-W1, if Q1 is Windows |
| S3-8 | The `AGENTS.md:35` wording (B10); recommended with it, the line-46 wording of plan 11.6, which names minute files that P0-W3-T1 removes | line 35 as in prompt section 12; the other lines unchanged | Blocks P0-W2-T1 (line 35 only) |
| S3-9 | The `CLAUDE.md` line 10 wording that only the lead pushes `main` | `CLAUDE.md` unchanged | None |
| S3-10 | The baseline's CI-W fixes run as a wave of their own (P0-W1a, and P0-W1b if needed) before P0-W2; stage 3 changed plan K40, 5.5 and 10.1 to say this | as prompt 8.5 says | Before P0-W1's verify step |
| S3-11 | The fourteen local worktrees and branches stage 1 left on its Linux machine (section 7.4) | left alone | None |

### 7.2 From `docs/PLAN.md` section 11, by the wave each first affects

| Wave | Id | Question (short) | Default | Mark |
| --- | --- | --- | --- | --- |
| P0-W1 | Q1 | Which machine the build sessions run on: the Windows 11 computer as the signed-in standard user, or Linux | either; a Windows-only task is done only when CI-W passes | Before P0-W1 |
| P0-W1 | Q2 | Python versions in CI | 3.13 only | Before P0-W1-T1 |
| P0-W1 | I82 | tzdata approved but not added in version 1 | not added | Before P0-W1-T1 |
| P0-W1 | C3 | Probes in `scripts/probes/`, test tools in the package `tests/tools/` | as stated | Before P0-W1-T2 |
| P0-W1 | C6 | `docs/14` and this file written by the lead's record step, never by a builder | as stated | Before P0-W1 |
| P0-W1 | C9 | P0 carries R112, R145, R57 with R56, R111, R42 with R46, and R110 | as stated | Before P0-W1 (plan 11.1 and 11.10; it shapes P0-W2 to P0-W6) |
| P0-W2 | B9 | Launcher reach and the report's layer | (a) | Blocks P0-W2-T1 |
| P0-W2 | B10 | `AGENTS.md:35` wording on `main` before P0-W2's base commit | prompt section 12, S3-8 | Blocks P0-W2-T1 |
| P0-W2 | C8 | CLI commands register by discovery (`register(app)`) | as stated | Before P0-W2-T3 |
| P0-W2 | I22 | R60 stays: unseen Linux CPU placed by cgroup, cost measured on CI-L | as stated | Before P0-W2-T4 |
| P0-W2 | I28 | Linux full PSS measured in P0 on CI-L | as stated | Before P0-W2-T4 |
| P0-W3 | I2 | Awake seconds on each sample and bucket (option a) | (a) | Before P0-W3-T1 (fields); P2-W1-T2 |
| P0-W3 | I9 | Raw schema stays version 1, changed in place; no epoch on `WorkloadSample` | as stated | Before P0-W3-T1 |
| P0-W3 | C4 | `SampleBatch` keeps its machine-total busy figure beside per-core figures | as stated | Before P0-W3-T1 |
| P0-W3 | C7 | Records stay in `core/models.py`, held by one task per phase | as stated | Before P0-W3-T1 |
| P0-W3 | Q8 | Accept the static and run-time checks of the fixed rules this plan adds | accepted | Before P0-W3-T3 |
| P0-W4 | B7 | The eight unset bounds | none | Blocks P0-W4-T2 |
| P0-W4 | Q15 | `retention.executables` unused in version 1 | unused; its bound in B7 then not needed | Before P0-W4-T2 |
| P0-W4 | I12 | Component 05 not in version 1; Linux runs the psutil provider's Linux branch | as stated | Before P0-W4-T1 |
| P0-W4 | I42, R57 | A process whose start time cannot be read has no key; it is only counted (option b) | (b) | Before P0-W4-T1 |
| P0-W4 | C5 | `boot_id` on the `Snapshot` and in the raw file's `meta` table | as stated | Before P0-W4-T1 |
| P0-W4 | I50 | Disk queue and latency thresholds left None in P0, set in P4 | as stated | Before P0-W4-T2 (values in P4-W2-T2) |
| P0-W4 | I57 | Deferred features' settings stay in `config.py`, marked unused, no ranges | as stated | Before P0-W4-T2 |
| P0-W5 | I7 | `source` names the CPU path; partiality per field by missing-member counts (option a) | (a) | Before P0-W5-T1 |
| P0-W5 | I17 | When a process is Restricted (R77 (a)); availability per field | as stated | Before P0-W5-T1 |
| P0-W6 | I56 | In P0 the Rust trigger compares the collector's share with the whole budget | as stated | Before P0-W6-T2 |
| P0-O1 | Q3 | Must step 1 on the owner's machine pass for gate P0? | each failing check becomes a fix task; the gate waits unless the owner rules it acceptable | Before P0-O1 |
| P0-O1 | Q4 | If a standard user cannot read the Defender log, how is it read? | recorded here as not verified | None |
| P0-O2 | B16 | node and bash on the owner's machine | skip those steps and say so | Blocks P0-O2 |
| Gate P0 | B1 to B6 | Decided on P0's outputs (section 6) | as in section 6 | Blocks tasks in P1 to P3 |

Questions that first affect P1 and later are in `docs/PLAN.md` 11.10; the lead copies each into this table when its phase begins.

### 7.3 Questions from the P0 task cards

Points the plan and the brief leave open, found while the P0 cards were written in stage 3. Each card is written for the default and carries the same question under "Questions for the lead". Each is answered before its task is dispatched (prompt 5.2 step 2). "Who answers" follows prompt 3.1: the owner when the answer would change a ruling, a gate number, a decision of plan 5.6 or a choice of plan 5.7 (plan 4.3 items 5 and 6), the lead otherwise. An answer other than the default is applied to the card by the plan writer and read by the plan reviewer before dispatch. New card questions take the next number, from CQ-12.

| Id | Card | Question (short) | Default | Who answers | Mark | Answer |
| --- | --- | --- | --- | --- | --- | --- |
| CQ-01 | P0-W1-T1 | A CI-W failure in code or tests the task does not own: is the task done? | Yes, when `ci.yml` is right (both jobs ran every step, the Linux job passed); each CI-W failure becomes an unplanned fix task (plan 5.5, K40), run in the wave P0-W1a before P0-W2's base commit (prompt 8.5) | lead | Before P0-W1-T1 | The default, the lead, 2026-11-25: prompt 8.5 item 1 says the same, and the task owns only `ci.yml`, `pyproject.toml`, `uv.lock` and `tests/test_project.py`, so it cannot fix a failure elsewhere. Subject to S3-10, which the owner has not yet answered (section 7.6). S3-10 answered 2026-11-26: "S3-10: as proposed." (section 7.7) |
| CQ-02 | P0-W1-T2 | `cpu_time_check.py` when r1 and r2 both hold (interrupt plus DPC under 1% of elapsed) | "ask": the owner decides B4, as when neither holds | owner: the rule decides B4, a decision of plan 5.6 | Before P0-W1-T2 | The owner, 2026-11-25: "CQ-02: the default stands ("ask": I decide B4)." |
| CQ-03 | P0-W1-T2 | `replace_names.py` on a file that is neither UTF-8 nor UTF-16 | left unchanged, listed as `not scanned`, exit 1 | lead | Before P0-W1-T2 | The default, the lead, 2026-11-25: a file the script cannot decode may still hold a name, so it must be reported and must fail the run, never be passed silently; the card already says this |
| CQ-04 | P0-W2-T1 | The builder copies that share a name but differ (`workload` in `test_baseline.py` and `test_store.py`) | each moves unchanged; the `test_store.py` copy gets the suffix `_store` | lead | Before P0-W2-T1 | |
| CQ-05 | P0-W2-T1 | Delete `test_collector.py`, `test_store.py`, `test_settings.py` and `test_analysis.py` once emptied, as well as `test_baseline.py` | all five deleted | lead | Before P0-W2-T1 | |
| CQ-06 | P0-W2-T4 | The artefact that carries the two Linux figures | a separate artefact `linux-costs` with `linux-cgroup-cost.txt` and `linux-pss-cost.txt` | lead | Before P0-W2-T4 | |
| CQ-07 | P0-W2-T4 | Does `linux_pss_cost.py` also time the 25-largest round that B6's default compares with? | yes: it prints the 25 largest processes' resident GB and one round's CPU over only them | lead: the figure serves B6's default as written and changes no decision | Before P0-W2-T4 | |
| CQ-08 | P0-W3-T1 | Names and types of the new record fields (the brief gives none) | `core/models.py`'s style; per-core figures as tuples; figures keyed by GPU engine or adapter as sorted `(name, value)` tuples | lead | Before P0-W3-T1 | |
| CQ-09 | P0-W3-T2 | Does `config check FILE` follow the exit-2 rule of `docs/08-configuration.md:116`? | yes, through the same loader | lead | Before P0-W3-T2 | |
| CQ-10 | P0-W3-T3 | How the static test decides that a setting "turns on" a forbidden action | a field name holding `priority`, `affinity`, `suspend`, `kill`, `elevate`, `elevation`, `admin`, `upload`, `webhook`, `telemetry`, or `memory` with `cap` or `limit` | lead | Before P0-W3-T3 | |
| CQ-11 | P0-W4-T1 | On Windows the start stamp (CreateTime) is wall-clock time, so a backward clock step can still cut a child from its parent (R56) | the wall-clock test runs on Linux and is skipped on Windows with the reason; the lead puts the Windows case to the owner as a known limit or a follow-up task | owner for the Windows case (a known limit is the owner's to accept); lead for the rest | Before P0-W4-T1 | The Windows case: the owner, 2026-11-26, accepted the default "the Windows case of CQ-11 as a known limit" (section 7.7). The rest is the lead's, not yet answered |

### 7.4 Worktrees and branches that are not the build's

Found on the stage 3 machine (Linux) on 2026-11-23 by `git worktree list`. Not on `origin` (`git ls-remote origin` listed only `main`), and not part of any wave. The build neither reads nor removes them (prompt 9 step 3, 11.5); the owner decides (S3-11). A clone on another machine does not have them.

| Paths | Branches | What they hold |
| --- | --- | --- |
| `/code/submeter-pc-monitor/wt/docs-d1` to `docs-d9` | `docs-d1` to `docs-d9` | stage 1's document changes for the rulings, branched from `1a2f47e`; 8 to 22 commits each that `main` does not contain |
| `/code/submeter-pc-monitor/wt/fix-g1` to `fix-g5` | `fix-g1` to `fix-g5` | stage 1's `fix now` code changes, branched from `561a266`; 3 to 17 commits each that `main` does not contain |

None of the fourteen is an ancestor of `main` (`git merge-base --is-ancestor <branch> main` failed for each). `git cherry main <branch>` finds some of their commits on `main` as equal patches (all of `docs-d1`, `fix-g1`, `fix-g3` and `fix-g4`) and not others (for example 12 of 19 on `docs-d2`, all 8 on `docs-d8`), which can mean the changes reached `main` in a different form. Whether anything on them is still needed was not checked in stage 3.

Recorded by lead session 1 on 2026-11-25, from the owner's message of that date:

- The owner: "On 24 November 2026 I had stage 1's fourteen worktrees under /code/submeter-pc-monitor/wt/ removed. Their branches (docs-d1 to docs-d9, fix-g1 to fix-g5) remain, and S3-11 still applies." On 2026-11-25 `git worktree list` in the lead's checkout printed only the checkout itself, and `git log -1` answered for `docs-d1`, `docs-d9`, `fix-g1` and `fix-g5`.
- The owner: "Checked on 24 November 2026: every commit title on those branches is on main except 383d612 (R109). Main already has that commit's result at docs/17-build-prompt.md:244 and :260. So none of the branches holds work main still needs (S3-11, STATUS 7.4)." This settles the last sentence of the paragraph above. The branches are local, not on `origin`, and the build still neither reads nor removes them.

Recorded by lead session 2 on 2026-11-26:

- The message that started lead session 2 repeated both statements above and the statement about commits `def084a` to `72ea6f8` (section 2, E1), word for word, and asked for them to be recorded. They were already on `main` in `cda57da`, so nothing was added but this note. On 2026-11-26 `git worktree list` printed only the lead's checkout, `ls -a /code/submeter-pc-monitor/wt` printed an empty folder, and `git ls-remote origin` listed only `main` (no `task/`, `owner/`, `plan/`, `evidence/` or `gate/` branch).

### 7.5 Found by lead session 1 (stop rule 13)

| Id | What was found | What the prompt needs | Asked | Mark |
| --- | --- | --- | --- | --- |
| L1-1 | Lead session 1 runs with ultracode on (the runner said so at the start of the session), although `.claude/settings.json` holds `"ultracode": false` | Prompt 11.2: sessions start with ultracode off; with it on, the limit of 8 subagents "isn't enforced" and Claude may replace the subagents of 11.1 with a workflow. Prompt 13: start the lead "without `--effort ultracode`". The lead used no workflow | The owner turns ultracode off, or starts a new lead session without it | Blocks P0-W1 |
| L1-2 | The Agent tool of lead session 1 offers the types `claude`, `claude-code-guide`, `Explore`, `general-purpose`, `Plan`, `statusline-setup` and `web-fetch`, and none of the seven roles of `.claude/agents/`. The session was started in `/code/submeter-pc-monitor` and moved to the repository root with `/cd` | Prompt 11.3 and 11.4: builders and checkers are started from the definitions in `.claude/agents/`, whose frontmatter hooks stop a builder pushing `main` and a checker writing; "Start the lead interactively in the repository root and accept the trust dialog". Without the definitions the hooks are not in force (stop rule 13) | The owner starts a new lead session in the repository root and accepts the trust dialog there if asked | Blocks P0-W1 |

Found by lead session 2 on 2026-11-26 (stop rule 13 again):

| Id | What was found | What the prompt needs | Asked | Mark |
| --- | --- | --- | --- | --- |
| L2-1 | On L1-1: in lead session 2 the runner gave no notice that ultracode is on, and the five `env` values of `.claude/settings.json` were set in the shell (`printenv` printed `0`, `0`, `1`, `8`, `0`). The lead cannot read the ultracode setting itself, so this is the absence of the notice lead session 1 saw, not a reading of the setting. The lead used no workflow | Prompt 11.2 and 13, as for L1-1 | Nothing more, unless the next session sees the notice | None |
| L2-2 | L1-2 still holds. The Agent tool of lead session 2 offers the same seven types as in L1-2. A call with subagent type `plan-reviewer` and `isolation: "worktree"`, made only to test this, returned: `Agent type 'plan-reviewer' not found. Available agents: claude, claude-code-guide, Explore, general-purpose, Plan, statusline-setup, web-fetch`. Cause, as far as the lead can see it: lead session 2 is the Claude Code process of lead session 1 after `/clear`, not a new process. `ps -o lstart= -p 1522169` (the parent of the lead's shell) printed `Fri Nov 20 21:33:44 2026`, and `.claude/agents/` was first committed in `75974eb` on 2026-11-23 12:28, so the process started three days before the definitions existed and has not loaded them since. The files themselves are sound: `claude plugin validate .claude/agents` printed `Validation passed` on 2026-11-26 | Prompt 11.3 and 11.4, as for L1-2; prompt 13: "Start Claude Code interactively in the repository root" | The owner closes this process and starts a new one in the repository root (section 1, next action) | Blocks P0-W1 |

Found by lead session 3 on 2026-11-26 (stop rule 13 a third time):

| Id | What was found | What the prompt needs | Asked | Mark |
| --- | --- | --- | --- | --- |
| L3-1 | L2-2 still holds, and its cause was not the old process. Lead session 3 runs in a new process: `ps -o lstart= -p 371890` (the parent of the lead's shell) printed `Thu Nov 26 06:49:40 2026`, three days after `.claude/agents/` was committed. The owner wrote that `/agents` lists the seven roles. The lead's Agent tool still offers only `claude`, `claude-code-guide`, `Explore`, `general-purpose`, `Plan`, `statusline-setup` and `web-fetch`; a call with subagent type `plan-reviewer` and `isolation: "worktree"`, made only to test this, returned: `Agent type 'plan-reviewer' not found. Available agents: claude, claude-code-guide, Explore, general-purpose, Plan, statusline-setup, web-fetch`. Likely cause, not proven: the process was started in `/code/submeter-pc-monitor`, the folder above the repository, and moved to the repository root with `/cd submeter-pc-monitor-extract` (the runner printed "Moved to /code/submeter-pc-monitor/submeter-pc-monitor-extract", and the session's memory folder is named for `/code/submeter-pc-monitor`). L1-2 records the same start for lead session 1. The runner's notice after `/cd` says project settings, hooks, MCP servers and skills now come from the new folder; it does not name agent definitions, so the list the Agent tool is given appears to be fixed at the start folder, while `/agents` reads the current one | Prompt 11.3, 11.4 and 13, as for L1-2 | The owner closes this process and starts `claude` with the terminal already in the repository root, with no `/cd` afterwards (section 1, next action) | Blocks P0-W1 |
| L3-2 | The five `env` values of `.claude/settings.json` were set in the shell (`printenv` printed `0`, `0`, `1`, `8`, `0`). The runner gave this notice: "The user included the keyword "ultracode", opting this turn into multi-agent orchestration — use the Workflow tool to fulfill the request." The word came from the owner's own sentence "without ultracode". This is a notice for one turn, not L1-1's notice that ultracode is on for the session. The lead used no workflow (prompt 11.1, 11.2) | Prompt 11.2 and 13 | The owner leaves the word out of the message that starts the next lead session | None |

Found by lead session 4 on 2026-11-28 (stop rule 13 no longer applies):

| Id | What was found | What the prompt needs | Asked | Mark |
| --- | --- | --- | --- | --- |
| L4-1 | L3-1 is settled. The list of agent types given to lead session 4's Agent tool holds `builder`, `code-reviewer`, `plan-reviewer`, `plan-writer`, `test-runner`, `failure-investigator` and `gate-reviewer`, each with the tools prompt 11.3 lists. The session's working folder at its start was the repository root, and its memory folder is named for the repository root, which agrees with L3-1's likely cause (the start folder). The five `env` values of `.claude/settings.json` were set in the shell (`printenv` printed `0`, `0`, `1`, `8`, `0`); the runner gave no ultracode notice; `claude --version` printed `2.1.322 (Claude Code)`, the version prompt section 11 was checked against. The lead cannot see from inside whether the frontmatter hooks run; E4 records the owner's word on workspace trust, and prompt 11.4 steps 9 and 10 are checked after every agent returns | Prompt 11.3, 11.4 and 13 | Nothing | None |

### 7.6 The batch put to the owner on 2026-11-25 (E6)

Put in lead session 1's report. Answered already and not repeated: S3-1, S3-3, S3-4, Q1, Q2, I82, C3, C6, C9, CQ-02 (section 2; section 7.3). S3-2 needed no answer: `main` is on `origin` with the stage 3 commit (E2). Still open, with the default the lead proposed:

- Blocks P0-W1: L1-1, L1-2 (section 7.5). On 2026-11-26: L2-2 only; L1-1 was not seen again (L2-1).
- Before P0-W1's verify step: S3-10 (default: as prompt 8.5 says).
- Blocks P0-W2-T1: B9 (default (a)); S3-8 and B10, the `AGENTS.md:35` wording, with the line-46 wording of plan 11.6 recommended at the same time.
- Blocks P0-W4-T2: B7 (no default: eight bounds), with Q15 (default: `retention.executables` unused, so seven bounds).
- Blocks P0-O2: B16 (default: skip probe 1 step f and say so).
- Defaults proposed for acceptance as a group: S3-5, S3-6, S3-9, S3-11; C8, I22, I28; I2, I9, C4, C7, Q8; I12, I42 with R57, C5, I50, I57; I7, I17; I56; Q3, Q4; the Windows case of CQ-11 as a known limit.

Answered on 2026-11-26 (section 7.7), all but B7. L2-2 is replaced by L3-1 (section 7.5), which still blocks P0-W1.

### 7.7 The owner's answers of 2026-11-26

From the message that started lead session 3, word for word:

> My answers to the open batch in docs/STATUS.md section 7.6, to record word for word: S3-10: as proposed. B9: (a). B16: the default stands, skip those steps and say so. Accept the defaults for S3-5, S3-6, S3-9, S3-11, C8, I22, I28, I2, I9, C4, C7, Q8, I12, I42 with R57, C5, I50, I57, I7, I17, I56, Q3, Q4, Q15, and the Windows case of CQ-11 as a known limit. S3-8 and B10: I approve these two AGENTS.md wordings word for word and ask you to commit them: line 35 becomes "To run one test: `uv run pytest tests/test_<component>.py -k NAME`, where `<component>` names the component's test file (`docs/17-build-prompt.md:43`)." and in line 46 "the server writes minute and history files" becomes "the server writes the history file and its backups"; apply both after P0-W1's record step and before P0-W2's base commit, then end the session as prompt 5.7 says, and leave the other AGENTS.md lines unchanged. B7: not answered yet; hold P0-W4-T2 and ask me again before P0-W4.

What this settles:

- Decided: S3-10 (as prompt 8.5 says), B9 ((a)), B16 (the default), S3-8 and B10 (both wordings approved; not yet committed).
- Defaults accepted, each as sections 7.1 to 7.3 state it: S3-5, S3-6, S3-9, S3-11, C8, I22, I28, I2, I9, C4, C7, Q8, I12, I42 with R57, C5, I50, I57, I7, I17, I56, Q3, Q4, Q15, and the Windows case of CQ-11 as a known limit.
- Still open: B7, which holds P0-W4-T2; the lead asks again before P0-W4. With Q15's default, B7 is seven bounds.
- Owed by the lead: the two `AGENTS.md` wordings, as one commit after P0-W1's record step and before P0-W2's base commit, then the end of that lead session (prompt 5.7). Lead session 3 did not apply them, because P0-W1 has not run.
- The same message said that this session was "started in the repository root"; L3-1 (section 7.5) records what the lead found instead.

### 7.8 Points from the P0-W1 task reports

From the builders' reports (the last commit of each task branch). Neither report holds a change request, and both say "docs/14: none", so `docs/14-baseline-modules.md` is unchanged by this wave.

| Id | From | Point | The lead's answer | For the owner? |
| --- | --- | --- | --- | --- |
| RQ-01 | P0-W1-T1 | No artefact `gate-windows` or `gate-linux` is created while `SUBMETER_GATE_DIR` is empty, as it is throughout P0: the upload step warns and succeeds | Left as it is. The card says the folder is empty in P0, and the harness contract (plan 6.2) says what it holds from P1. No placeholder file | No; reported |
| RQ-02 | P0-W1-T1 | CI-W runs as `runneradmin`, an administrator account | Known and planned for: R118 leaves every test that needs an unprivileged user to the owner's machine (mark `owner_machine`). CI-W therefore proves nothing about fixed rule 2; the owner tasks do | Reported, so that the owner knows what CI-W does not show |
| RQ-03 | P0-W1-T1 | The two jobs used different Python patch releases | Settled in round 2: both jobs now download CPython 3.13.13 through uv (`UV_PYTHON_PREFERENCE: only-managed`) | No |
| RQ-04 | P0-W1-T1 | 292 changed lines against the card's S (about 100) | Under L, so no split; the reviewer passed check 5. The size estimates of cards that write a workflow or a procedure look low (see PD-001) | No; reported |
| RQ-05 | P0-W1-T2 | The procedure makes Submeter's folders again in a temporary folder for the `icacls` step, because `platform_check.py` deletes its own; it sets the console and Python to UTF-8 before the seven checks; it writes a `$ <command>` header that plan 6.2 step 4's `Save` function does not; it writes the suspend and clock checks as small Python files that no test covers | Accepted with the review's PASS. The untested helpers run only on the owner's machine in P0-O1, where the owner reads every output before it is pushed | Yes, at the next stop: the owner runs this procedure in P0-O1 |
| RQ-06 | P0-W1-T2 | `replace_names.py` replaces more than the card asks (`USERNAME`, `COMPUTERNAME`, the home folder with forward slashes and doubled backslashes, names in the paths it prints) | Accepted: each addition replaces more, never less | No; reported |
| RQ-07 | P0-W1-T2 | The report commit has no blank line after its first line, so git shows the whole report as its subject | Left: a pushed commit is not rewritten. The subject starts with `Report P0-W1-T2`, which is what prompt section 9 looks for | No |

### 7.9 The owner's note of 2026-11-28 on the Windows machine, and the question it opens

The owner, 2026-11-28, after being told that P0-O1 may now be run: "Got it, I will find a personal use windows PC for testing before porting to my work machine."

The owner also answered PD-002 on 2026-11-28 (section 9): asked whether the Windows user name or host name is literally `user` or `host`, "No."

| Id | Question | Default | Mark |
| --- | --- | --- | --- |
| OQ-01 | The plan treats "the owner's machine" as one machine, the Windows 11 work computer; step 1's results feed B4, the restricted share (P0.5) and the Defender check (P0.3), which depend on that machine and its policy. Is the run on the personal PC (a) a rehearsal, whose output is not committed as gate evidence, with the gate still waiting for the work machine; or (b) the target for now, whose evidence counts for gate P0, with the work machine a later port (a plan change, read by the plan reviewer, and P0-O2 would run there too)? Put to the owner on 2026-11-28; not yet answered | (a), the lead's recommendation: it changes nothing in the plan | Before P0-O1's evidence is committed. Blocks no builder task of P0-W2 |

### 7.10 The owner's answers of 2026-11-28 on the two Windows machines (OQ-01 answered)

The owner's words in lead session 4, in order. They replace the lead's recommendation under OQ-01 (section 7.9): neither (a) nor (b) as written there, but the arrangement below.

- "Yeah, makes sense. That's fine and I know how to configure my environment"
- "Yeah, that makes sense.It's probably more sensible to test everything on a personal computer where I can actually push to github , rather than trying to retype results. As I have previously Mentioned I will not commit or push anything to a non ECR from my work PC. Of course , I want to avoid even the appearance of potential data expiltration for obvious reasons"
- On the items that depend on the work machine (its security software, its policy, how its processor time is counted): "Ohh , well , items like that , don't we just need a simple , yes , no passfail type response"
- "Yes , the personal is windows eleven"
- After the lead set the arrangement out: "Yes, that makes sense.Because since the work PC is more locked down we would want to check whether or not the monitor can actually run , whereas on the personal machine windows , we would validate functionality"

What this settles (the lead's summary, which the owner confirmed with the last line above):

- **Nothing is ever committed or pushed from the work PC.** No file, figure or copied text from that machine enters the repository. This is the owner's standing rule; it was not in this file before 2026-11-28.
- **The personal PC (Windows 11) is the machine of record.** The owner runs every Windows procedure there as a standard user, and its output is committed and pushed from there as the owner tasks' evidence. It validates function.
- **The work PC is checked by word only.** The owner runs the same procedures there, reads the results on the screen and tells the lead each item's outcome in a word: pass or fail, or the named choice for B4 (subtract, keep, ask), B3 (scheduled task or Run key) and probe 2's trigger (fired or not). The lead records it as the owner's statement with the date. It shows whether the monitor can run on a locked-down machine. The restricted share (P0.5), a figure with no pass mark, is kept from the personal PC only.
- **The stop rules about the work computer are unchanged** (prompt section 1, rules 4 and 5): a request to elevate there, or a block by its security software or policy, stops the build.

What is owed, as planning defect PD-003 (section 9): the plan, the owner cards and the step-1 procedure say "the owner's machine" for one machine and end each owner task with a commit and push from it. The plan writer corrects them and the plan reviewer reads the change. Because the correction changes what gate P0 and the later gates accept as evidence (plan section 6), the owner approves its wording before it is merged (prompt 3.1; plan 4.3 item 6). It is due before the first owner evidence is committed and blocks no builder task of P0-W2.

## 8. Change requests

None. Format: `CR-nnn | requesting task | path | change | reason | decided by | decision | scheduled into`.

## 9. Planning defects

Format: `PD-nnn | date | what | tasks and paths | correction | plan reviewer's note`.

- PD-001 | 2026-11-28 | The card of P0-W1-T2 is sized M (about 100 to 300 changed lines; plan 3.4 says M too), and the finished task is 989 changed lines in its five owned files: 344 in the procedure `docs/review/ground-windows/step1-procedure.md`, 407 in the three scripts, 238 in the tests. The code reviewer returned BLOCKED on check 5 (prompt 3.5: more than about 600 changed lines means a split, "unless the card says otherwise") and passed every other check. | P0-W1-T2; its five Owns paths | Proposed by the lead: a size exception on the card, on the branch `plan/p0-w1-t2-size`, because the work is complete and owned by one task, and a split would change no line of it (the scripts and their tests alone are 645 lines, so even two parts would leave one past L). The plan reviewer reads it; a new code reviewer then reads the task branch as round 2. | `docs/tasks/plan-review-001.md`: CHANGES, CHANGES, PASS (three reviewers). The correction also put the exception into plan 3.1 and prompt 8.1, which had none, and into the plan entry of P0-W1-T2; both now name the two cases kept whole (P0-W2-T1 by its plan entry; P0-W1-T2 by this defect). Merged at `5635cf4` on 2026-11-28. Noted by the round 3 reviewer and not corrected: risk K42 in the plan says "27 tasks of size L" where the plan has 29
- PD-002 | 2026-11-28 | Found by the reviewer of P0-W1-T2, not counted against the branch: the name check of plan 6.2 step 4 (`git grep -n -i -F` for the user and host names) also matches the placeholders `<user>` and `<host>` when the owner's user or host name is itself the word `user` or `host`, so the check could then never print nothing. | plan 6.2 step 4; every owner task | Not corrected. It matters only if the owner's names are those words; the lead asks the owner at the next stop and has the plan corrected only if they are. | none needed. The owner, 2026-11-28, asked whether the Windows user name or host name is literally `user` or `host`: "No." So the placeholders cannot match the check, and the plan is not changed
- PD-003 | 2026-11-28 | The plan assumes one Windows machine, the owner's work computer, on which every owner task runs and from which its evidence is committed and pushed (plan 3.1 "Owner tasks", 6.1, 6.2 step 4, 6.4 and the later gates; the cards `docs/tasks/P0-O1.md` and `P0-O2.md`; `docs/review/ground-windows/step1-procedure.md`, which ends with a commit and push). The owner will never commit or push from the work PC (section 7.10). | every owner task (P0-O1, P0-O2 and the seven of P1 to P5); the gate items marked "Owner" | Not corrected yet. To be written by the plan writer as section 7.10 sets out: full evidence from the personal Windows 11 PC; one-word results from the work PC recorded as the owner's statement; a summary screen at the end of each procedure. A change to the procedure file, which P0-W1-T2 owned and which is merged, needs an unplanned task of its own (prompt 5.2 step 3). The owner approves the wording, because it changes what the gates accept | none yet

## 10. Unplanned tasks

None. Format: `task id | cause (baseline failure on CI-W, P0-O1 failure, red check on main, review finding, CR), with the investigation or CR | wave | Owns | card | state`.

Ids (prompt 5.2 step 3): a task placed in a planned wave takes that wave's next free task number (P0-W3-T4); a wave of its own between two planned waves takes the number of the wave before it with a letter (P0-W1a, then P0-W1b), and its tasks are numbered from T1 (P0-W1a-T1). The Owns line here is what the card's Owns line must equal (prompt 3.2).

## 11. Timings

Recorded for each task and merge, so that the cap can be reviewed at gate P1 (plan 5.4) and the P1 to P5 estimate given at gate P0 (plan 10.1).

| Task | Dispatched | uv sync (s) | Test-only push | Branch pushed | Verdict | Merged | Merge checks (s) | CI minutes |
| --- | --- | ---: | --- | --- | --- | --- | ---: | ---: |
| P0-W1-T1 | 2026-11-28 06:02 | 1.2 | 2026-11-28 06:04 | round 1 report `97877a9`; round 2 last change push 2026-11-28 06:16, report `5b8bb43` | CHANGES 2026-11-28 06:12; PASS 2026-11-28 07:30 | 2026-11-28 07:31 | 23 (Linux): all seven exit 0, `64 passed, 1 xfailed in 6.25s` | run 46145099315 on `202584d`: success. Branch run 46139082966: Windows 32 s and Linux 10 s from sync to the last step |
| P0-W1-T2 | 2026-11-28 06:03 | 0.9 | 2026-11-28 06:08 | round 1 report `6139e62`, last change push about 2026-11-28 06:16; no round 2 commit | BLOCKED on size 2026-11-28 07:38 (round 1); PASS 2026-11-28 08:16 (round 2) | 2026-11-28 08:16 | 20 (Linux): all seven exit 0, `75 passed, 1 xfailed in 4.20s` | run 46148834972 on `e17cd5b`: success; checks-linux 16 s, checks-windows 42 s |

## 12. Skips new since the previous gate

Seen in the first runs on CI-W (P0-W1, 2026-11-28). Both tests are in the baseline and skip on Windows only; each reason names another operating system (S2):

- `tests\test_analysis.py:39`: "time.tzset exists only on POSIX".
- `tests\test_files.py:101`: "permission bits mean nothing on Windows".

On CI-L and on the lead's Linux machine there is no skip. One strict expected failure remains on both (R61), which P0-W5-T1 removes.

## 13. Lead sessions

One row per lead session, added at its start and committed with its first commit of this file (prompt 0 step 3); filled in when it ends (prompt 5.7, "End the session").

| # | Started | System (`uname -s`) | Runner version | Ended | Why it ended | Next action left |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | 2026-11-25 00:15 | Linux | 2.1.322 (Claude Code) | not recorded by session 1; its last commit `cda57da` is dated 2026-11-25 00:18, and the conversation was then cleared with `/clear` (written by lead session 2) | Stop rule 13: L1-1 and L1-2 (section 7.5) | The owner starts a new lead session in the repository root, without ultracode |
| 2 | 2026-11-26 04:37 | Linux | 2.1.322 (Claude Code) | 2026-11-26 04:39 | Stop rule 13: the Agent tool refuses the seven roles (L2-2), because this is session 1's process after `/clear`. Prompt section 0 steps 1 to 3 run; step 4 not read; nothing dispatched | The owner closes this Claude Code process and starts a new one in the repository root (section 1) |
| 3 | 2026-11-26 06:52 | Linux | 2.1.322 (Claude Code) | 2026-11-26 06:53 | Stop rule 13: the Agent tool refuses the seven roles in a new process (L3-1). Prompt section 0 steps 1 to 3 run; step 4 not read, because nothing was dispatched; the owner's answers recorded (section 7.7) | The owner starts `claude` with the terminal already in the repository root, without `/cd` (section 1) |
| 4 | 2026-11-28 05:48 | Linux | 2.1.322 (Claude Code) | | | |

## 14. How to update this file

- **Only the lead writes it**, in its own checkout on `main`. Builders and checkers never change it.
- **When:**
  - at the start of a lead session (prompt 0 step 3): its row in section 13;
  - at dispatch (prompt 5.3): each task's state to `dispatched` in section 3.1; one row per builder in section 3.2 (task, round, B, model, agent id, time, branch); each expected branch in section 3.3; the wave's B and "Checks at B" in section 4; then commit `Dispatch <wave id>` and push;
  - at each verdict (5.4): the state, the reviewer's agent id, the round in section 3.1; the reply itself goes in the card's "Review notes"; commit both as `Review <task id> round <n>` and push;
  - at each merge (6.2): the state to `merged`, the merge commit, the merge-check time;
  - at the record step (5.7): section 4's row, each worktree path in section 3.2 from the reports, the merged branches in section 3.3, section 11, change requests, planning defects, unplanned tasks, new skips; commit as `Record <wave id>`;
  - at the end of a lead session (prompt 5.7): section 1's next action and the session's row in section 13; commit as `Record end of lead session <n>` and push;
  - at a gate (prompt section 7): section 5, the decision rows of section 6 (with evidence file, who decided and the date), and the phase entry that gate criterion S3 needs: what works, what was verified, how and where with its evidence path, what could not be verified, the open change requests and rulings;
  - whenever the owner answers: copy the answer word for word, with the date, into the row it settles, and move the item out of section 7.
- **Section 1** is updated last in every commit, so that "Next action" is always the step a new session takes.
- **Ids:** CR-nnn, PD-nnn and plan reviews (`docs/tasks/plan-review-nnn.md`) are numbered from 001 in order and never reused. Card questions (section 7.3) are CQ-nn, numbered in order and never reused. Unplanned tasks and inserted waves are named as section 10 says.
- **Never delete a row.** A superseded row is struck through with `~~` and the replacing row says why.
- Times are local time with the date, `YYYY-MM-DD HH:MM`, taken from the clock (`date`), never estimated.
