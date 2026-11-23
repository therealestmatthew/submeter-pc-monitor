# Submeter version 1: build status

The state of the build, kept by the lead of `prompts/02-orchestration-prompt.md`. A new lead session reads this file first and continues from "Next action". `docs/PLAN.md` says what is built; this file says where it stands. Only the lead writes it; how is at the end.

## 1. Where the build stands

| Field | Value |
| --- | --- |
| Updated | 2026-11-23 12:24, starting state written in stage 3 |
| Phase | P0, decision probes, CI and the baseline repairs (`docs/PLAN.md` 3.4) |
| Wave | P0-W1, the pilot: not started |
| Base commit B | not fixed. P0-W1's B will be `main` once the stage 3 commit is on `origin` and the entry conditions of section 2 hold (prompt 5.2 step 6) |
| Width | 2 builders (pilot); cap 4 (plan 5.4) |
| Gate P0 | not started |
| Build machine | not decided (Q1). Stage 3 ran on Linux |
| Lead session | none has run |
| **Next action** | The lead runs prompt section 0 (if the stage 3 output is not committed, 0 step 2 says what to do). The owner meets E1 and E3 to E5 and answers the questions marked for P0-W1 in section 7: S3-1, S3-3, S3-4, Q1, Q2, I82, C3, C6, C9, and CQ-02, which the owner answers (7.3). The lead checks E2, answers CQ-01 and CQ-03 (prompt 5.2 step 2), then runs P0-W1 from prompt 5.2. |

## 2. Entry conditions of the pilot P0-W1

From prompt section 5.1. Tick each with the date and the evidence.

| # | Condition | State | Evidence |
| --- | --- | --- | --- |
| E1 | The owner approved stage 3's output: `prompts/02-orchestration-prompt.md`, `.claude/agents/`, `.claude/settings.json`, `docs/tasks/`, this file and stage 3's changes to `docs/PLAN.md` (S3-1), and it is committed (prompt 0 step 2) | open | — |
| E2 | `main` is on `origin` and holds the stage 3 commit: `git ls-remote origin refs/heads/main` prints the sha of `git rev-parse main`, and `git cat-file -e main:docs/tasks/P0-W1-T1.md` exits 0 (S3-2) | open | 2026-11-23 12:08: `git ls-remote origin` printed `76ebe7124736db49aba2f3ff0c0fdf46cca47401 HEAD` and the same sha for `refs/heads/main`, which is stage 2's commit. The stage 3 commit was not yet made |
| E3 | The build machine is decided (Q1), and this lead session runs on it (prompt 5.1 item 3); Q2, I82, C3, C6 and C9 answered or their defaults accepted | open | — |
| E4 | The owner approved how builders' commands run: the rules and `env` values of `.claude/settings.json` (S3-3) and the lead's permission mode (S3-4); and the owner accepted the workspace trust dialog for the clone the lead runs in, without which the allow rules and the agents' hooks are not applied (prompt 11.3) | open | — |
| E5 | If the build runs on Windows: Git for Windows present, the clone at a root of 40 characters or fewer, `git config core.longpaths true` in it (S3-7) | open, or not applicable | — |
| E6 | Recommended: every decision of plan 5.6, every question of plan 11 and the card questions of section 7.3 that the owner answers, put to the owner as one batch (prompt 5.1 item 5) | open | — |

## 3. Phase P0 tasks, dispatches and branches

### 3.1 Tasks

States: `not started`, `held` (blocked by a decision, section 6), `dispatched`, `review 1`, `round 2`, `review 2`, `escalated`, `passed`, `merged`, `blocked` (waiting on the owner). "Builder" and "Reviewers" are agent ids.

| Task | Title | Size | OS | Depends on | Blocked by | State | Builder | Reviewers | Rounds | Merge commit |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P0-W1-T1 | CI on both runners, and the test markers | S | either; proves itself on CI-W and CI-L | none | — | not started | | | | |
| P0-W1-T2 | Step-1 helper scripts for the owner's machine | M | either | none | — | not started | | | | |
| P0-W2-T1 | The test split and the layer rows | L | either | P0-W1-T1 | B9; B10 (`AGENTS.md:35` wording on `main`) | held | | | | |
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
| P0-O2 | The three probes and a second platform check | about 2 h | at the gate commit G0 | every P0 builder task | B16 | not started | `owner/P0-O2` | |

Unplanned tasks (prompt 5.2 step 3, 8.5) get a row here too when they are added, and their own row in section 10.

### 3.2 Dispatches

One row per builder dispatched (prompt 5.3 step 3), written at dispatch; the worktree path is added from the builder's report, because Claude Code chooses it (prompt 11.5).

| Task | Round | B | Model | Builder agent id | Dispatched | Branch | Worktree path |
| --- | --- | --- | --- | --- | --- | --- | --- |

### 3.3 Branches on origin

Every branch an agent or the lead is expected to push, added when the agent is dispatched or the branch is pushed. After each checker and each builder returns, `git ls-remote origin` must show no branch that is missing here (prompt 11.4 steps 9 and 10). `main` is always expected.

| Branch | Pushed by (task or role, agent id) | Added | State (open, or merged at a sha) |
| --- | --- | --- | --- |
| `main` | the lead | 2026-11-23 | on `origin` at `76ebe71` (stage 2) |

## 4. Waves of P0

| Wave | Planned width | Run width | B (base) | Checks at B | Dispatch commit | I (last merge) | R (record) | Record review | CI on R |
| --- | ---: | ---: | --- | --- | --- | --- | --- | --- | --- |
| P0-W1 | 2 | | | | | | | | |
| P0-W2 | 4 | | | | | | | | |
| P0-W3 | 3 | | | | | | | | |
| P0-W4 | 2 | | | | | | | | |
| P0-W5 | 2 | | | | | | | | |
| P0-W6 | 2 | | | | | | | | |

"Checks at B": the exit code of each of the seven `AGENTS.md` checks run at B in the lead's checkout, and pytest's summary line (prompt 5.2 step 6). An inserted wave (P0-W1a, P0-W1b; prompt 5.2 step 3, 8.5) gets a row below the wave it follows.

Pilot result (plan 5.4): not yet run. Widening needs both pilot tasks merged without a conflict, every check that passed at B ("Checks at B") still passing after each merge and on both runners, and each review settled within two rounds. Failures of the baseline's first run on CI-W do not count against the pilot (prompt 8.5).

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
| B7 | The eight bounds `docs/08-configuration.md:78-94` marks "not set yet" | none | open; blocks P0-W4-T2 | | | | |
| B9 | How `submeter run` reaches the launcher, and the report's place in `LAYER` | (a): the CLI starts the launcher as a child process; `report` at layer 2 importing only `core` | open; blocks P0-W2-T1 | | | | |
| B10 | The `AGENTS.md` wordings of plan 11.6 | line 35 reworded (prompt section 12, S3-8); the other lines unchanged | open; the line-35 wording blocks P0-W2-T1 and must be on `main` at P0-W2's base commit | | | | |
| B16 | Whether node.exe and bash.exe are on the owner's machine, and whether they may be installed | probe 1 and the P1 gate skip those steps and say so | open; blocks P0-O2 | | | | |

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
| CQ-01 | P0-W1-T1 | A CI-W failure in code or tests the task does not own: is the task done? | Yes, when `ci.yml` is right (both jobs ran every step, the Linux job passed); each CI-W failure becomes an unplanned fix task (plan 5.5, K40), run in the wave P0-W1a before P0-W2's base commit (prompt 8.5) | lead | Before P0-W1-T1 | |
| CQ-02 | P0-W1-T2 | `cpu_time_check.py` when r1 and r2 both hold (interrupt plus DPC under 1% of elapsed) | "ask": the owner decides B4, as when neither holds | owner: the rule decides B4, a decision of plan 5.6 | Before P0-W1-T2 | |
| CQ-03 | P0-W1-T2 | `replace_names.py` on a file that is neither UTF-8 nor UTF-16 | left unchanged, listed as `not scanned`, exit 1 | lead | Before P0-W1-T2 | |
| CQ-04 | P0-W2-T1 | The builder copies that share a name but differ (`workload` in `test_baseline.py` and `test_store.py`) | each moves unchanged; the `test_store.py` copy gets the suffix `_store` | lead | Before P0-W2-T1 | |
| CQ-05 | P0-W2-T1 | Delete `test_collector.py`, `test_store.py`, `test_settings.py` and `test_analysis.py` once emptied, as well as `test_baseline.py` | all five deleted | lead | Before P0-W2-T1 | |
| CQ-06 | P0-W2-T4 | The artefact that carries the two Linux figures | a separate artefact `linux-costs` with `linux-cgroup-cost.txt` and `linux-pss-cost.txt` | lead | Before P0-W2-T4 | |
| CQ-07 | P0-W2-T4 | Does `linux_pss_cost.py` also time the 25-largest round that B6's default compares with? | yes: it prints the 25 largest processes' resident GB and one round's CPU over only them | lead: the figure serves B6's default as written and changes no decision | Before P0-W2-T4 | |
| CQ-08 | P0-W3-T1 | Names and types of the new record fields (the brief gives none) | `core/models.py`'s style; per-core figures as tuples; figures keyed by GPU engine or adapter as sorted `(name, value)` tuples | lead | Before P0-W3-T1 | |
| CQ-09 | P0-W3-T2 | Does `config check FILE` follow the exit-2 rule of `docs/08-configuration.md:116`? | yes, through the same loader | lead | Before P0-W3-T2 | |
| CQ-10 | P0-W3-T3 | How the static test decides that a setting "turns on" a forbidden action | a field name holding `priority`, `affinity`, `suspend`, `kill`, `elevate`, `elevation`, `admin`, `upload`, `webhook`, `telemetry`, or `memory` with `cap` or `limit` | lead | Before P0-W3-T3 | |
| CQ-11 | P0-W4-T1 | On Windows the start stamp (CreateTime) is wall-clock time, so a backward clock step can still cut a child from its parent (R56) | the wall-clock test runs on Linux and is skipped on Windows with the reason; the lead puts the Windows case to the owner as a known limit or a follow-up task | owner for the Windows case (a known limit is the owner's to accept); lead for the rest | Before P0-W4-T1 | |

### 7.4 Worktrees and branches that are not the build's

Found on the stage 3 machine (Linux) on 2026-11-23 by `git worktree list`. Not on `origin` (`git ls-remote origin` listed only `main`), and not part of any wave. The build neither reads nor removes them (prompt 9 step 3, 11.5); the owner decides (S3-11). A clone on another machine does not have them.

| Paths | Branches | What they hold |
| --- | --- | --- |
| `/code/submeter-pc-monitor/wt/docs-d1` to `docs-d9` | `docs-d1` to `docs-d9` | stage 1's document changes for the rulings, branched from `1a2f47e`; 8 to 22 commits each that `main` does not contain |
| `/code/submeter-pc-monitor/wt/fix-g1` to `fix-g5` | `fix-g1` to `fix-g5` | stage 1's `fix now` code changes, branched from `561a266`; 3 to 17 commits each that `main` does not contain |

None of the fourteen is an ancestor of `main` (`git merge-base --is-ancestor <branch> main` failed for each). `git cherry main <branch>` finds some of their commits on `main` as equal patches (all of `docs-d1`, `fix-g1`, `fix-g3` and `fix-g4`) and not others (for example 12 of 19 on `docs-d2`, all 8 on `docs-d8`), which can mean the changes reached `main` in a different form. Whether anything on them is still needed was not checked in stage 3.

## 8. Change requests

None. Format: `CR-nnn | requesting task | path | change | reason | decided by | decision | scheduled into`.

## 9. Planning defects

None. Format: `PD-nnn | date | what | tasks and paths | correction | plan reviewer's note`.

## 10. Unplanned tasks

None. Format: `task id | cause (baseline failure on CI-W, P0-O1 failure, red check on main, review finding, CR), with the investigation or CR | wave | Owns | card | state`.

Ids (prompt 5.2 step 3): a task placed in a planned wave takes that wave's next free task number (P0-W3-T4); a wave of its own between two planned waves takes the number of the wave before it with a letter (P0-W1a, then P0-W1b), and its tasks are numbered from T1 (P0-W1a-T1). The Owns line here is what the card's Owns line must equal (prompt 3.2).

## 11. Timings

Recorded for each task and merge, so that the cap can be reviewed at gate P1 (plan 5.4) and the P1 to P5 estimate given at gate P0 (plan 10.1).

| Task | Dispatched | uv sync (s) | Test-only push | Branch pushed | Verdict | Merged | Merge checks (s) | CI minutes |
| --- | --- | ---: | --- | --- | --- | --- | ---: | ---: |

## 12. Skips new since the previous gate

None (gate criterion S2).

## 13. Lead sessions

One row per lead session, added at its start and committed with its first commit of this file (prompt 0 step 3); filled in when it ends (prompt 5.7, "End the session").

| # | Started | System (`uname -s`) | Runner version | Ended | Why it ended | Next action left |
| --- | --- | --- | --- | --- | --- | --- |

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
