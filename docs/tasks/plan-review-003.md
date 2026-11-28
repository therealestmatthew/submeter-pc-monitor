# Plan review 003: the size exception for P0-W2-T2 (PD-004)

The change: branch `plan/p0-w2-t2-size`, written by the plan writer (agent a285b254159173fcf) for planning defect PD-004 (`docs/STATUS.md` section 9). The reply is copied word for word.

## Round 1

- Reviewer agent id: abe17aff391661550
- Date: 2026-11-28
- Branch tip read: `14d7ec12bca6c2fa357d0ec45370bef2a71c5782`
- Verdict: PASS
- Reply (word for word):

> PASS
>
> I found no defect. The branch makes exactly the change PD-004 asks for, the figures are correct, and nothing else moved.
>
> **Checklist (plan change or new cards)**
>
> 1. **Shape of the branch.**
>    - `git log origin/main..origin/plan/p0-w2-t2-size` shows one commit, 14d7ec1. Its merge base with `origin/main` is 0ad14fe.
>    - `git diff --stat origin/main...origin/plan/p0-w2-t2-size` lists only `docs/PLAN.md` (2 lines) and `docs/tasks/P0-W2-T2.md` (1 line).
>    - `git diff --stat 0ad14fe origin/main` lists only `docs/STATUS.md` and `docs/tasks/plan-review-002.md`, so those later commits on `main` don't touch this branch's files.
>
> 2. **The figures are correct.**
>    - `git diff --numstat 37fe97b origin/task/P0-W2-T2` printed `1133 0 scripts/probes/job_object.py` and `161 0 tests/test_probe_job_object.py`.
>    - `--shortstat` printed `2 files changed, 1294 insertions(+)`.
>    - The card and the plan entry both say 1294 lines in total. The card's split of 1133 and 161 matches too, and its allowance of "up to about 1,300" covers 1294.
>
> 3. **The card and its plan entry agree.**
>    - The card's Size row (`docs/tasks/P0-W2-T2.md:13`) says "M as planned", then records the size exception and cites PD-004.
>    - The plan entry (`docs/PLAN.md:346`) says "M (finished at 1294 changed lines; size exception PD-004, `docs/STATUS.md` section 9)".
>    - Both use the same form as the precedent, P0-W1-T2: the card's Size row at `docs/tasks/P0-W1-T2.md:13` and the plan entry at `docs/PLAN.md:322`.
>    - The card's date, 2026-11-28, matches PD-004's date in `docs/STATUS.md` section 9.
>
> 4. **Nothing else on the card changed.**
>    - The one changed line on the card is line 13, the Size row.
>    - Owns, Reads, Uses, Provides, Work, Tests first, Acceptance, Gate evidence and OS are unchanged.
>    - The Review notes are unchanged: Round 1 still shows reviewer af113a30355f962e4, 15:07 and BLOCKED, and Round 2 is still empty.
>    - The plan entry's Owns, Tests first, Depends on ("none"), OS and Gate evidence (P0.8) are unchanged and still match the card.
>
> 5. **The exception meets the condition for keeping a task whole** (plan 3.1, `docs/PLAN.md:228`; prompt 8.1, `prompts/02-orchestration-prompt.md:411`).
>    - The task was found past L at its review: Round 1 was BLOCKED on check 5 alone.
>    - Its plan entry and card both record the exception.
>    - The planning defect it rests on, PD-004, is in `docs/STATUS.md` section 9. It is there at the base 0ad14fe (one match for `PD-004 |`) and on `origin/main`.
>    - This review is the plan reviewer's reading that the condition requires.
>    - Prompt 3.5 check 5 ("unless the card says otherwise", `prompts/02-orchestration-prompt.md:178`) is met by the card's sentence "For check 5 of prompt 3.5 this card says otherwise". The card also limits the exception to this task and to that one check.
>
> 6. **No sentence elsewhere is now untrue.**
>    - Plan 3.1 still reads "Nothing larger is planned, except … (P0-W2-T1)". That stays true, because P0-W2-T2 was planned at M.
>    - Plan 3.1's "Two cases are kept whole" names kinds of case, not tasks, so adding "P0-W2-T2, PD-004" to the second kind is consistent.
>    - Prompt 8.1 names no task for the second kind, so it stays true without an edit.
>    - Plan 9's "Builder sessions | 95 | … one builder session or less" (`docs/PLAN.md:3309`) still holds: the builder's report shows one session, 14:20 to 16:05.
>    - K42 (`docs/PLAN.md:2884`) still says "27 tasks of size L". That mistake was there before this change (it was noted under PD-001) and this branch doesn't touch it.
>
> 7. **No path has two owners in wave P0-W2.**
>    - P0-W2-T1 owns 21 files under `tests/`.
>    - P0-W2-T2 owns `scripts/probes/job_object.py` and `tests/test_probe_job_object.py`.
>    - P0-W2-T3 owns the `src/submeter/cli*` files and `tests/test_cli_registry.py`.
>    - P0-W2-T4 owns `scripts/probes/linux_cgroup_cost.py`, `scripts/probes/linux_pss_cost.py`, `tests/test_probe_linux_costs.py` and `.github/workflows/ci.yml`.
>    - No path appears twice (`docs/PLAN.md:330,341,351,361`), and the branch changes no Owns line.
>
> 8. **Dependencies.** The branch changes none. P0-W2-T2 still depends on nothing.
>
> 9. **No ruling, gate, 5.6 decision or 5.7 choice is touched.**
>    - The only changes are at `docs/PLAN.md:228` (section 3.1) and `docs/PLAN.md:346` (section 3.4).
>    - Sections 5.6, 5.7, 6 and `docs/review/02-rulings.md` are not changed.
>    - The rulings set no task size; their only line limit is the stage-1 "about fifty".
>    - So, as in plan review 001, the owner doesn't need to decide anything.
>
> **Should the task be split instead?** I see no reason to split it.
> - One task owns both paths, and the Round 1 reviewer passed every check except size.
> - The plan entry's Provides is "one text file", produced by one script that the owner runs in three shells.
> - The script runs copies of itself as its child processes. It does this through `SCRIPT = Path(__file__)` and the `_role_*` functions (`scripts/probes/job_object.py:606-680` on `origin/task/P0-W2-T2`). Splitting the file would change how those children start, and would gain nothing the reviewer can check.
> - The builder finished it in one session.
>
> **For the lead, outside this change:** PD-004 points out that the two probes still to be built, P0-W5-T2 (L) and P0-W6-T2 (S), may also run past their sizes. You could re-size them before they are dispatched, instead of granting another exception at review.
>
> I changed, committed and pushed nothing. My working copy is clean, and I ran only read-only commands. One combined command was blocked by a hook, so I ran its parts separately; every result above comes from a command that ran.
>
> Files read:
> - /code/submeter-pc-monitor/submeter-pc-monitor-extract/.claude/worktrees/agent-abe17aff391661550/docs/PLAN.md (at `origin/plan/p0-w2-t2-size`)
> - /code/submeter-pc-monitor/submeter-pc-monitor-extract/.claude/worktrees/agent-abe17aff391661550/docs/tasks/P0-W2-T2.md
> - /code/submeter-pc-monitor/submeter-pc-monitor-extract/.claude/worktrees/agent-abe17aff391661550/docs/STATUS.md (section 9)
> - /code/submeter-pc-monitor/submeter-pc-monitor-extract/.claude/worktrees/agent-abe17aff391661550/docs/tasks/plan-review-001.md
> - /code/submeter-pc-monitor/submeter-pc-monitor-extract/.claude/worktrees/agent-abe17aff391661550/prompts/02-orchestration-prompt.md
