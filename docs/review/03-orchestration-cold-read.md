# Cold read of the orchestration prompt

I read the repository as a fresh lead session would on 23 November 2026, given "Read prompts/02-orchestration-prompt.md and build Submeter as it says." I changed nothing. I read CLAUDE.md and AGENTS.md, then the whole prompt, then `docs/STATUS.md`, `.claude/settings.json`, `.claude/agents/builder.md`, the template and the two pilot cards. In `docs/PLAN.md` I read only the sections that prompt section 0 names (3.1, 3.4, 4.1-4.3, 4.4 for P0-W1, 5.3-5.7, 6.1-6.4, 6.11, 10.3, 11.10), plus 7.2, 7.5, 10.1, 10.2, 10.4 and 11.6, because steps of 5.1 and 5.2 cite them. Everything ran on Linux (Claude Code 2.1.322).

The prompt itself is clear and runs end to end on paper. Four problems would stop or misdirect the build:

1. Nothing stage 3 wrote is committed.
2. What happens if the owner chooses the Windows machine for the build (Q1).
3. Two parts of the plan disagree on where CI-W fixes go.
4. A round-2 builder cannot see its review notes.

## State found at the start

| Check | Result |
| --- | --- |
| `git remote -v` | `origin` = https://github.com/therealestmatthew/submeter-pc-monitor (fetch and push) |
| `git ls-remote origin` | `HEAD` and `refs/heads/main` = `76ebe71` ("Stage 2: the formal plan"); the reflog shows it was pushed on 2026-11-23 at 11:26 |
| `git status --porcelain` | ` M docs/PLAN.md`, `?? .claude/`, `?? docs/STATUS.md`, `?? docs/tasks/`, `?? prompts/02-orchestration-prompt.md` |
| `claude --version` | 2.1.322, the same as prompt 11, so no check against the documentation is needed |
| `git worktree list` | the main checkout plus 14 stage-1 worktrees under `/code/submeter-pc-monitor/wt/` (`docs-d1`..`docs-d9`, `fix-g1`..`fix-g5`); their branches are local only |
| `.github/`, `docs/gates/`, `docs/review/03-orchestration-cold-read.md` | do not exist yet |

## 1. What I would do first, up to dispatching the first builder

1. **Check the remote.** Run `git remote -v` and `git ls-remote origin` (CLAUDE.md; prompt 0.1). Both pass.
2. **Check the version.** Run `claude --version`: 2.1.322, so no re-check of 11.2 to 11.7.
3. **Check the working tree (prompt 0.2). It fails.** `git status --porcelain` lists five entries. `git switch main && git pull --ff-only` succeeds (already up to date). The prompt's own note that main is not on origin is out of date. The prompt gives no step for a dirty tree. I would stop here, because:
   - With `worktree.baseRef: "head"`, a builder's worktree is cut from the committed HEAD, `76ebe71`, which has no `docs/tasks/`. Every builder would fail at "read your card first".
4. **Read the state.** These are reads only, so they do not depend on a clean tree. Read `docs/STATUS.md` (0.3) and the plan sections listed above (0.4). Nothing is dispatched, so section 9 is skipped (0.5).
5. **Go to the next action in STATUS (0.6, then 5.1).** Entry conditions E1 to E6 are all open, so stop rule 11 applies: every task of P0-W1 waits on the owner.
   - Draft answers to CQ-01 and CQ-03 at their defaults.
   - Send CQ-02 to the owner. It sets the rule that decides B4, a decision of plan 5.6, and STATUS 7.3 sends such questions to the owner.
6. **Write one message to the owner (prompt 10.2).** A summary of 15 lines or fewer, then numbered decisions, each with its default:
   1. Q1, the build machine. This comes first: if the answer is Windows, this Linux checkout cannot be the lead.
   2. S3-1, approval of stage 3's output, and who commits it.
   3. S3-2. Main is already on origin; the stage-3 commit still has to be pushed.
   4. Q2, I82, C3, C6, C9.
   5. S3-3 and S3-4 (the allow and deny rules, and the permission mode); S3-5; S3-6.
   6. S3-7, if the answer to Q1 is Windows.
   7. Recommended now, as one batch: B9, the line-35 wording (B10 / S3-8) and B7, with the rest of plan 5.6 and section 11.
7. **After the answers:**
   - Copy them word for word into STATUS and tick E1 to E6 with dates and evidence.
   - Get the stage-3 output and STATUS into a commit, made by the owner or by the lead with the owner's word.
   - Run `git push origin main`, then confirm that `git ls-remote origin refs/heads/main` equals `git rev-parse main` (E2).
   - Run the seven checks at that commit, so that "every check that passed at B" is known for judging the pilot.
8. **Select (5.2).**
   - Wave P0-W1: P0-W1-T1 (CI and test markers, size S) and P0-W1-T2 (step-1 scripts, size M). Pilot width 2; no task is blocked by a decision.
   - Ownership: T1 owns `.github/workflows/ci.yml`, `pyproject.toml`, `uv.lock` and `tests/test_project.py`. T2 owns `scripts/probes/{cpu_time_check,restricted_share,replace_names}.py`, `tests/test_probe_step1.py` and `docs/review/ground-windows/step1-procedure.md`. They share no path, and nothing lies under P0-O1's `docs/review/ground-windows/step1/`.
   - B = HEAD = `origin/main`, with a clean tree. Commit nothing between fixing B and dispatching.
9. **Dispatch (5.3, 11.4).**
   - In one turn, make two Agent calls: `subagent_type: builder`, `isolation: "worktree"`, no `name`.
   - Each prompt is the 5.3 message: task id and title, card path, B, lead checkout `/code/submeter-pc-monitor/submeter-pc-monitor-extract`, branch `task/<id>`, Round 1.
   - Record the agent ids, times, B, round and model in STATUS. Commit `Dispatch P0-W1` (STATUS only) and push main.

## 2. Places I would have to guess

"Blocking" means a wrong guess would stop the build or send it the wrong way.

| # | Where | The guess | Blocking |
| --- | --- | --- | --- |
| G1 | Prompt 0.2, 5.1, 5.2.6; 11.2 says settings.json "is committed" | What to do with the uncommitted stage-3 output. Whether the lead may commit it before the owner approves it (E1). Whether that first commit needs a plan review (3.3). Without a commit, builders' worktrees have no cards. | **yes** |
| G2 | Prompt 0.2; STATUS E2; PLAN 3.4 line 300, 10.2 item 2 | All of them say main is not on origin; it is (`76ebe71`). The guess: E2 counts as met only once the stage-3 commit is pushed. | no |
| G3 | Prompt 5.1 item 3 (Q1), 11.6 | What a lead running on Linux does if Q1 is answered "Windows". The guess: stop, write the next action, and ask for a lead in a clone at a root of 40 characters or fewer on Windows. | **yes** |
| G4 | STATUS 1 and 7.3 (CQ-01 to CQ-03) | The prompt never says how the lead answers card questions. CQ-02 sets B4's rule, so it goes to the owner; accept the other defaults. | no |
| G5 | Prompt 5.2.6, 8.3, stop rule 7; CQ-01; PLAN 7.2 against K40 and 10.1 | Where CI-W baseline fixes go. The prompt and 7.2 require CI-W to be green at I1 before P0-W2, so the fixes need a wave of their own. K40 and 10.1 put them into later waves. 8.3 allows "one fix task", then stop rule 7. No id scheme exists for unplanned tasks. | **yes** |
| G6 | Prompt 4, 5.4.3-4, 3.4 step 1; builder.md | A round-2 or round-E builder detaches to `origin/task/<id>`, which is cut from B. The review notes are copied into the card on main after B, so the builder cannot see them in its own copy. When the notes get committed is also unstated. | **yes** (for round 2) |
| G7 | Prompt 5.2.4 | Running the seven checks at B before dispatch is not asked for, but the widening rule depends on knowing what passed at B. | no |
| G8 | Prompt 5.3.3, 11.4.9; STATUS 3 and 4 | STATUS has no column for each task's B or model. It also has no list of origin branches to compare with `git ls-remote`. | no |
| G9 | `.claude/settings.json` allow list; prompt 6.3; STATUS 14 | `git remote -v`, `claude --version`, `date` (STATUS wants clock times), `git reset --hard` (6.3), `git tag` (gates) and `git branch` are not allowed. It is unclear whether `Bash(uv sync *)` matches a bare `uv sync`. Each would prompt the owner and stall an unattended wave. | no |
| G10 | Prompt 11.3, "Hooks need workspace trust" | The lead cannot confirm from inside that the frontmatter hooks are active. | no |
| G11 | Prompt 11.4.6, S3-5 | Whether the `fable` model alias exists for this account; only matters at an escalation. | no |
| G12 | Prompt 5.4.2 | The code reviewer's dispatch message has no template. | no |
| G13 | `git worktree list` | 14 stage-1 worktrees and branches, local only and not in STATUS. Section 9 does not cover them. The guess: leave them and tell the owner. | no |
| G14 | Prompt 1, Precedence; AGENTS.md last section | Plan against brief is not ordered. The guess: hold the task and ask. | no |
| G15 | Prompt 5.7, "End the session" | How a lead ends its own session, and when to add its row to STATUS section 13. | no |

## 3. Contradictions with AGENTS.md, CLAUDE.md or docs/PLAN.md

1. **Main on origin.** Prompt 0.2 and STATUS (section 1, E2), and also PLAN 3.4 and 10.2, say main is not on origin. The repository shows `76ebe71` there since 11:26 on 23 November. The prompt file dates from 11:21 and STATUS from 11:50.
2. **"Committed with the repository".** Prompt 11.2 says the settings file is committed, and section 4 says a new session can resume from the files alone. In fact the prompt, `.claude/`, `docs/tasks/` and STATUS are untracked, and PLAN.md has uncommitted edits. Prompt 0.2 fails as a result.
3. **CI-W fixes.** Prompt 5.2.6 and CQ-01 (green CI-W at I1 before P0-W2) disagree with PLAN 8.8 K40 and 10.1 (fixes go on later wave cards or into the spare places of P0-W3 to P0-W6). PLAN 7.2 agrees with the prompt, so the plan disagrees with itself.
4. **Builders and main.** CLAUDE.md line 10 says "push `main` when its checks pass"; the prompt says a builder never pushes main. This is acknowledged as S3-9. Only a hook enforces it, and only once workspace trust is accepted.
5. **Adding origin.** CLAUDE.md says "If `origin` is missing, add it", but settings.json denies `git remote add *`. Moot today.
6. **Showing check output.** AGENTS.md says "show what they printed"; prompt 6.2 says "read only each command's exit code and pytest's summary line".
7. **docs/14.** Prompt 3.1 lets the lead change `docs/14-baseline-modules.md`, yet also says it never edits "the brief's topic files", and docs/14 is one of them (docs/README; PLAN P0.11).
8. **Commits on main.** Prompt 4 says "every commit on main comes from a merge ... or from the lead's record. Nothing else." The prompt itself also requires Dispatch commits (5.3), review-note copies (5.4), gate commits (7) and approved wordings (12).
9. **Worktree paths.** PLAN 10.4 setting 5 says to record each worktree path at dispatch. Prompt 11.5 says the path is known only from the builder's report, and STATUS has no column for it.
10. **Dispatch record.** Prompt 5.3.3 asks for B and the model per task; STATUS section 3 has no column for either.
11. **C9 timing.** STATUS 7.2 marks C9 "Before P0-W2"; prompt 5.1, STATUS E3 and PLAN 11.10 put it before the pilot.
12. **CI job count.** PLAN 7.2 step 2 says "all four CI jobs"; the P0-W1-T1 card and PLAN 7.5 plan two.
13. **AGENTS.md lines 35 and 46.** Line 35 names `tests/test_baseline.py`, which P0-W2-T1 deletes. Line 46 names minute files, which P0-W3-T1 removes. Both are acknowledged (B10, plan 11.6); line 35 blocks P0-W2-T1.
14. **Minor figure.** The prompt gives about 108 MB per virtual environment; the plan gives about 101 MB.

Also minor: prompt section 13's start message, "Read prompts/02-orchestration-prompt.md and follow it.", differs from the one this run used. It does no harm.

## What would let the build start

- Finish stage 3's "Clean state": commit and push the stage-3 output. B is then that commit.
- Update STATUS (section 1, E2), prompt 0.2, and PLAN 3.4 and 10.2 to say main is on origin.
- Ask Q1 first, and write down what a lead on the wrong machine does.
- Choose one rule for CI-W baseline fixes: either the prompt and 7.2, or K40 and 10.1. Allow more than one fix task at the pilot.
- Say how a round-2 builder reads its review notes, and when they are committed.
- Add `date`, `git remote -v`, `git reset --hard` and `git tag` to the allow list for the lead, with the owner's approval.

## Outside this step

The relayed question, about ultracode and work lost to the session limit, is not answered by this cold read. Two facts I saw bear on it:

- Prompt 11.2 sets `"ultracode": false` for the build. The reason it gives, quoting the documentation, is that with ultracode on, Claude picks workflows in place of subagents, the limit on concurrent subagents is not enforced, and the session "reaches a session or weekly limit sooner".
- The 14 leftover stage-1 branches all have their commit subjects on main except one, `383d612` "R109: Leave the installed-entry-point clause..." on `docs-d8`. The repository cannot show whether any of that work was redone because of a session limit.

## Critical files

- /code/submeter-pc-monitor/submeter-pc-monitor-extract/prompts/02-orchestration-prompt.md
- /code/submeter-pc-monitor/submeter-pc-monitor-extract/docs/STATUS.md
- /code/submeter-pc-monitor/submeter-pc-monitor-extract/docs/PLAN.md (3.4, 5.2-5.7, 7.2, 8.8 K40, 10.1-10.4)
- /code/submeter-pc-monitor/submeter-pc-monitor-extract/.claude/settings.json
- /code/submeter-pc-monitor/submeter-pc-monitor-extract/.claude/agents/builder.md

## Fixes made after the cold read

This was a single cold read. The owner chose a leaner Stage 3 on 23 November 2026, so there was no second read. The account of the fixes made after it follows.

I fixed the Stage 3 files for every reported guess and contradiction. Nothing is committed, and AGENTS.md and CLAUDE.md are untouched. I re-ran the mechanical self-check after the last change to the agent files and settings: 212 checks, 0 failed. That includes frontmatter fields against the downloaded frontmatter table, valid JSON in .claude/settings.json, and `claude plugin validate .claude/agents` printing "Validation passed" (output in stage3/selfcheck/selfcheck4.out).

**Things to know before the stage-3 session commits:**
1. The prompt now refers to docs/review/03-orchestration-cold-read.md (0 step 2, 5.1 item 1). That file does not exist yet. The execution prompt requires stage 3 to save it before committing.
2. I fixed one blocking defect the reader did not report. In Manual mode every Edit or Write prompts, so each background builder's edits would have waited for the owner. I added `Edit(/**)` to the allow list, plus ask rules `Edit(**/AGENTS.md)` and `Edit(**/CLAUDE.md)`, documented in prompt 11.2 and covered by S3-3. The documentation says `.claude/worktrees/` is not a protected path. I did not test live how these rules anchor inside a subagent's worktree.
3. I checked origin at 12:08: `git ls-remote origin` printed only `76ebe7124736db49aba2f3ff0c0fdf46cca47401 refs/heads/main`.

**Blocking guesses**
- **G1 (uncommitted stage-3 output):** fixed in prompt 0 step 2.
  - If only stage-3 paths are uncommitted, the lead asks the owner (S3-1) whether to commit them as "Stage 3: the orchestration prompt" and push. Any other uncommitted change: stop, and never commit, stash or reset it.
  - That commit needs no plan review; the cold read and the owner's approval check it (5.1 item 1).
  - 5.2 step 6 adds `git cat-file -e <B>:docs/tasks/<id>.md` for every card. E2 now requires the stage-3 commit to be on origin.
- **G3 (lead on the wrong machine for Q1):** prompt 5.1 item 3 and new stop rule 12. The lead writes the next action (a new lead on that machine, in a clone that meets E5), fills its session row, pushes and stops. The prompt also asks for `uname -s` in 0 step 3. The Git Bash output form (`MINGW64_NT-…`) is from memory; I did not run it.
- **G5 (where the CI-W baseline fixes go):** new prompt 8.5.
  - Baseline failures are identified by one failure investigator. The fixes run as their own wave P0-W1a (P0-W1b if needed; a third wave hits stop rule 9) before P0-W2. They are not stop rule 7.
  - Ids for unplanned work: next free T number in a planned wave, or an inserted wave named P0-W1a/b (5.2 step 3, STATUS 10).
  - Fixes whose test already fails at B need no test-only commit: prompt 3.4 step 4, 3.5 check 2, the builder and code-reviewer files, TEMPLATE, and a new plan 7.2 paragraph.
  - I changed plan K40, 5.5 and 10.1 to match plan 7.2. This was the plan's fault: it contradicted itself. It is listed as S3-10.
- **G6 (round-2 builders cannot see review notes):** 5.4 step 3 now commits the notes as "Review <id> round <n>" and pushes at once. Builders and reviewers read them with `git show origin/main:docs/tasks/<id>.md` (3.4, 5.3 template, new 5.4 reviewer template, builder.md, code-reviewer.md, TEMPLATE).

**Non-blocking guesses**
- **G2 (stale "main not on origin"):** updated with the 12:08 evidence in prompt 0 step 2 and 5.1 item 2, STATUS section 1 and E2, plan 3.4, 10.2 item 2 and K37.
- **G4 (who answers card questions):** prompt 3.1 "Answers" and 5.2 step 2, plus a "Who answers" column in STATUS 7.3. CQ-02 goes to the owner because it decides B4; so does CQ-11's Windows case. The rest go to the lead. Noted on the P0-W1-T2 and P0-W4-T1 cards.
- **G7 (checks at B):** 5.2 step 6 runs the seven checks at B. They are recorded in a new "Checks at B" column in STATUS section 4.
- **G8 (where to record B, model and branches):** new STATUS 3.2 Dispatches (B, model, agent id, worktree path) and 3.3 Branches on origin. Used in 5.3, 5.7, 9 and 11.4 steps 9–10.
- **G9 (allow list gaps):** added `git remote -v`, `git cat-file`, `git reset --hard`, `git tag gate-P*`, `date`, `uname` and `claude --version`.
  - The documentation settles the bare-command question: `Bash(uv sync *)` matches bare `uv sync`.
  - The lead's merge and gate commands no longer use shell variables (6.2, 6.3, 6.5, 7).
  - The PowerShell tool is off for every session (`CLAUDE_CODE_USE_POWERSHELL_TOOL=0`), so the Bash allow rules and hooks apply on Windows.
  - Left off on purpose, so they still prompt: `git branch`, `uv add`, `uv lock` and others (listed in 11.2).
- **G10 (is workspace trust on?):** 11.3 gives three checks: the owner confirms it (E4); an allow-listed command prompting in Manual mode means it is off; and where it is stored in ~/.claude.json, for the owner to read. New stop rule 13.
- **G11 (fable availability):** left as an open question. The account was not checked; if the Agent call refuses the model, escalation goes to the owner (11.4 step 6, S3-5).
- **G12:** the reviewer dispatch template is in 5.4 step 2.
- **G13 (stage-1 worktrees):** listed in STATUS 7.4 and S3-11 as an open question, default left alone (9 step 3, 11.5). None of the 14 is on origin or an ancestor of main. `git cherry` finds only some of their commits on main, and I did not check whether any work on them is still needed.
- **G14 (plan vs brief precedence):** section 1 now ranks rulings, then the brief (per AGENTS.md), then the plan. If the plan and brief disagree, hold the task and ask.
- **G15 (ending a session):** 5.7 gives four steps for ending a session. The session's row in STATUS 13 is added at session start (0 step 3), with new columns.

**Contradictions**
- **C1, C2:** fixed as G2 and G1. Section 11.2 no longer says the file "is committed".
- **C3:** fixed as G5. Plan K40, 5.5 and 10.1 were corrected.
- **C4 (builders vs CLAUDE.md "push main"):** CLAUDE.md is unchanged. Prompt 3.4 and builder.md now say main's checks are the lead's merge checks, so only the lead pushes main. A new 11.4 step 10 checks origin/main after each builder, which works even without the hooks. S3-9 still proposes the wording.
- **C5:** removed the `git remote add` deny. The allow list has only the exact command that adds origin with its address.
- **C6:** 6.2 now matches AGENTS.md: show each check's one-line output, pytest's summary line, and the full output of any failing check.
- **C7:** 3.1 makes docs/14 an explicit exception under plan choice C6.
- **C8:** section 4 lists every kind of lead commit. Plan, prompt, agent and card changes reach main only through a reviewed plan/ branch. The plan writer's scope widened to match (3.2, plan-writer.md).
- **C9:** plan 10.4 setting 5 corrected (the plan's fault): the worktree path is recorded from the builder's report.
- **C10:** fixed as G8.
- **C11:** STATUS 7.2 C9 changed to "Before P0-W1".
- **C12:** plan 7.2 step 2 changed from "four" to every ci.yml job, two with Q2's default (the plan's fault).
- **C13 (AGENTS.md lines 35 and 46):** cannot fix without editing AGENTS.md. Prompt section 12 now lists the known disagreements and recommends approving line 46 together with line 35 (S3-8). The P0-W3-T1 card says the stale line 46 is not a question to raise.
- **C14 (101 vs 108 MB):** prompt 5.2 now cites the plan's 101 MB. Section 11.5 explains the 23 November figures: `du -sm` printed 108 (disk blocks) and the apparent size was 105 MB.

All of the plan edits are listed in prompt section 12.

## Pilot on paper

Checked on 23 November 2026 against the uncommitted Stage 3 files in `/code/submeter-pc-monitor/submeter-pc-monitor-extract`, on Linux. Sources: `docs/PLAN.md` 3.4, 4.4, 5.3, 5.4 and 7.2 (the pilot's exception); `prompts/02-orchestration-prompt.md` 5.1 to 5.7 and 6.2; the cards `docs/tasks/P0-W1-T1.md` and `docs/tasks/P0-W1-T2.md`.

### 1. The tasks

| Task | Title | Size | OS | Depends on | Card |
| --- | --- | --- | --- | --- | --- |
| P0-W1-T1 | CI on both runners, and the test markers | S | either; proves itself on CI-W and CI-L | none | `docs/tasks/P0-W1-T1.md` |
| P0-W1-T2 | Step-1 helper scripts for the owner's machine | M | either for the tests; run on the owner's machine in P0-O1 | none | `docs/tasks/P0-W1-T2.md` |

Width 2 (plan 5.4, prompt 5.2 step 4). With one code reviewer per builder, at most 4 subagents run at once, under the limit of 8 in `.claude/settings.json`.

### 2. The files each owns

| Task | Path | Change |
| --- | --- | --- |
| P0-W1-T1 | `.github/workflows/ci.yml` | created (`.github/` does not exist at `76ebe71`) |
| P0-W1-T1 | `pyproject.toml` | changed: `[tool.pytest.ini_options]` only (four marks, `--strict-markers`, `addopts`) |
| P0-W1-T1 | `uv.lock` | owned, expected unchanged (no package added) |
| P0-W1-T1 | `tests/test_project.py` | changed: 3 tests added to the existing 2 |
| P0-W1-T2 | `scripts/probes/cpu_time_check.py` | created (`scripts/probes/` does not exist at `76ebe71`) |
| P0-W1-T2 | `scripts/probes/restricted_share.py` | created |
| P0-W1-T2 | `scripts/probes/replace_names.py` | created |
| P0-W1-T2 | `tests/test_probe_step1.py` | created |
| P0-W1-T2 | `docs/review/ground-windows/step1-procedure.md` | created (`docs/review/ground-windows/` does not exist at `76ebe71`) |

Owner task that starts once the wave is integrated, outside the wave: P0-O1 owns `docs/review/ground-windows/step1/` (a folder) until the P0 gate.

### 3. No file has two owners

Every owned path in the wave, sorted, with its owner:

| Path | Owner | Any other owner in P0-W1? |
| --- | --- | --- |
| `.github/workflows/ci.yml` | P0-W1-T1 | no |
| `docs/review/ground-windows/step1-procedure.md` | P0-W1-T2 | no; it is a file beside the folder `docs/review/ground-windows/step1/` that P0-O1 owns, not under it (the folder's path ends in `/`, and `step1-procedure.md` does not start with `step1/`) |
| `pyproject.toml` | P0-W1-T1 | no (shared file; its standing owner is the lead, plan 4.2) |
| `scripts/probes/cpu_time_check.py` | P0-W1-T2 | no |
| `scripts/probes/replace_names.py` | P0-W1-T2 | no |
| `scripts/probes/restricted_share.py` | P0-W1-T2 | no |
| `tests/test_probe_step1.py` | P0-W1-T2 | no |
| `tests/test_project.py` | P0-W1-T1 | no |
| `uv.lock` | P0-W1-T1 | no (shared file; travels with `pyproject.toml`, plan 4.2) |

9 paths, 9 distinct, no path equal to or under another task's path. No folder is owned in the wave; `scripts/probes/` and `.github/` are created only by the task that owns the files in them. The script check (`stage3/selfcheck/selfcheck.py`) printed: `PASS  P0-W1: 9 owned paths over 2 tasks, no path with two owners, none under an owner task's folder`, and both cards' Owns lines equal the plan's lines in 3.4 and 4.4.

Never owned by either builder (plan 4.1 rule 5): `docs/STATUS.md`, `docs/14-baseline-modules.md`, `docs/PLAN.md`, `docs/tasks/`, `prompts/02-orchestration-prompt.md`, `.claude/`, `AGENTS.md`, `CLAUDE.md`.

Independence beyond the file lists: P0-W1-T2's tests carry no pytest mark, so P0-W1-T1's `--strict-markers` and `addopts` select them unchanged; P0-W1-T1's `ci.yml` test reads only `.github/workflows/ci.yml`, which P0-W1-T2 does not touch; neither task imports the other's files.

### 4. The base commit

B is not fixed yet, and it will not be `76ebe71`.

- Today: `git ls-remote origin` prints `76ebe7124736db49aba2f3ff0c0fdf46cca47401 refs/heads/main`, and `git rev-parse main origin/main` prints the same sha. `main` is on `origin` at the Stage 2 commit ("Stage 2: the formal plan").
- Stage 3's files are not committed. Their commit, and the lead's commits that record the owner's answers to the entry conditions (`docs/STATUS.md` section 2) and to CQ-01 to CQ-03 (section 7.3), come after `76ebe71`.
- B is fixed by prompt 5.2 step 6: the current `main` after those commits, pushed (`git rev-parse HEAD` equals `git rev-parse origin/main`), with `git status --porcelain` empty and the lead's checkout on `main` at B. Nothing is committed between fixing B and dispatching (5.2 step 7).
- B goes into the dispatch message and into `docs/STATUS.md` (section 1 and section 4, row P0-W1), never onto a card. With `worktree.baseRef: "head"`, each builder's worktree starts at the lead's `HEAD`, which is B; the builder's step 1 checks it and switches to B if needed.
- Facts true at `76ebe71` that the pilot's tests rely on, and that Stage 3's commit does not change (it touches only `docs/`, `prompts/` and `.claude/`): no `.github/`; no `scripts/probes/`; `pyproject.toml` registers no pytest mark; 62 tests collected; `uv run pytest` gives `61 passed, 1 xfailed` on Linux.

### 5. Dispatch

Both builders in one turn, each with the message of prompt 5.3:

```
Task: P0-W1-T1, CI on both runners, and the test markers
Card: docs/tasks/P0-W1-T1.md. Read it first; it is the whole task.
Base commit B: <sha fixed at 5.2 step 6>
Lead's checkout (never work there): <absolute path of the lead's checkout>
Branch to push: task/P0-W1-T1
Round: 1. Review notes so far: the card's section "Review notes".
You may change only the paths in the card's Owns line.
Done when: the steps of prompts/02-orchestration-prompt.md section 3.4 are complete and the report of 3.4.1 is your branch's last commit.
```

and the same for P0-W1-T2. Then the lead records B, the time, each agent id, the round and the model in `docs/STATUS.md`, commits `Dispatch P0-W1` (that file only) and pushes `main`.

### 6. Review

One code reviewer per branch, fresh context, its own worktree. The pilot's exception (plan 7.2) applies to both tasks, because B holds no `ci.yml`:

- The reviewer runs the card's named tests at the test-only commit, where they must fail: P0-W1-T1's 3 new tests in `tests/test_project.py`; P0-W1-T2's 11 tests in `tests/test_probe_step1.py`.
- At the tip it runs them and the seven checks, which must pass: `tests/test_project.py` → `5 passed`; `tests/test_probe_step1.py` → `11 passed`.
- P0-W1-T1's last change commit has run `ci.yml` on both runners before merge (card acceptance 7). A CI-W failure in a file P0-W1-T1 does not own is handled by CQ-01's default.
- Ownership: `git diff --name-only <B> origin/task/<task id>` lists only the card's Owns paths.

### 7. Merge order and the checks after each merge

Ascending task number (prompt 5.5): **P0-W1-T1, then P0-W1-T2**. Each merges only on `PASS`. For each, in the lead's checkout (prompt 6.2):

```bash
t=P0-W1-T1                     # then t=P0-W1-T2
git switch main && git pull --ff-only
pre=$(git rev-parse HEAD)
git fetch origin "task/$t"
git merge --no-ff "origin/task/$t" -m "Merge $t: <title>"
git diff --name-only "$pre" HEAD
uv sync
uv run ruff check
uv run ruff format --check
uv run mypy src tests
uv run mypy --platform win32 src tests
uv run mypy --platform linux src tests
uv run pytest
git push origin main
```

| After merging | `git diff --name-only "$pre" HEAD` must list only | Expected `uv run pytest` on Linux (if no fix task was added) |
| --- | --- | --- |
| P0-W1-T1 | `.github/workflows/ci.yml`, `pyproject.toml`, `tests/test_project.py` (and not `uv.lock`) | 65 tests: `64 passed, 1 xfailed` |
| P0-W1-T2 | `scripts/probes/cpu_time_check.py`, `scripts/probes/restricted_share.py`, `scripts/probes/replace_names.py`, `tests/test_probe_step1.py`, `docs/review/ground-windows/step1-procedure.md` | 76 tests: `75 passed, 1 xfailed` |

The `1 xfailed` is R61's strict expected failure (`tests/test_attribution.py:109-112`), removed by P0-W5-T1. A merge conflict cannot happen if the table in section 3 holds; if one does, `git merge --abort` and record a planning defect (prompt 6.4). A failed check: `git reset --hard "$pre"`, do not push, start a failure investigator (prompt 6.3).

### 8. Verify and record

1. After the second merge is pushed, the CI run of the integration commit I must pass on CI-W and CI-L, P0-W1-T2's UTF-16 cases included (plan 7.2, the pilot's exception). This is the first time P0-W1-T2's tests run on CI.
2. Record step (prompt 5.7): `docs/STATUS.md` (verdicts, merge commits, times, CI) and the "docs/14" lines of both reports applied to `docs/14-baseline-modules.md`, committed as `Record P0-W1`; a plan reviewer reads B..R; the review note is committed and `main` pushed. That commit is P0-W2's base commit only once the CI run of I has passed on both runners (prompt 5.2 step 6).
3. The pilot is clean when: both tasks merged without a conflict; every check that passed at B still passed after each merge and on both runners; each review settled within two rounds. Then later waves run at their planned width, up to 4 (plan 5.4). A check that already failed at B on CI-W does not count against the pilot; it becomes a fix task (K40, CQ-01).
4. P0-O1 (the owner's step 1) may start at I.

### 9. What must be answered before the pilot is dispatched

From `docs/STATUS.md`: E1 (S3-1, approve Stage 3's output), E2 (S3-2, `main` on `origin`; true today at `76ebe71`, to be true again after Stage 3's commit is pushed), E3 (Q1; Q2, I82, C3, C6 and C9 or their defaults), E4 (S3-3, S3-4), E5 if the build runs on Windows (S3-7); and the card questions CQ-01 (P0-W1-T1), CQ-02 and CQ-03 (P0-W1-T2).
