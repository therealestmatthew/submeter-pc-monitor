# Plan review 002: the correction for PD-003 (two Windows machines)

The change: branch `plan/pd-003-two-windows-machines`, written by the plan writer (agent a98f4b6abeaaa8bee) for planning defect PD-003 (`docs/STATUS.md` section 9), on the owner's answers in `docs/STATUS.md` 7.10 and 7.12. Each round's reply is copied word for word.

## Round 1

- Reviewer agent id: a1f5e59e5a3e3de57
- Date: 2026-11-28
- Branch tip read: `f4e9612ee6b9efd9990df8ef7a222b26485d1343`
- Verdict: CHANGES
- Reply (word for word):

> CHANGES
>
> 1. **`docs/tasks/P0-O1.md:16` and `:82` and `:117` (CQ-13), against `docs/PLAN.md:2119`, `:481` and `:2193`.** The card has the work PC run step 1 at a different commit from the personal PC. The plan says it is the same commit. Card line 16 says the work PC runs at "the commit the lead names once P0-W3-T4 (the summary screen, PD-003) is merged". Plan 6.2 step 4 (line 2119) says "On the work PC, at the same commit". Plan 3.4 (line 481) calls it "the same run on the work PC", and its Uses and Work lines fix P0-O1 at the P0-W1 integration commit. Plan 6.4 Procedure (line 2193) says "P0-O1 follows … at the P0-W1 integration commit … Each runs first on the personal Windows 11 PC … and then on the work PC". The plan is also wrong on its own terms. Plan 3.1 (line 230) says P0-O1 ends with a summary screen, but the procedure at that commit has none (CQ-13 says so itself). The plan's P0-O1 Depends on line still names only P0-W1-T2, and the plan never mentions the task that builds the screen. A card question's default cannot override the plan. Either the plan states the work PC's commit and the dependency on the summary-screen task (P0-W3-T4, or whatever it is called), or the card follows the plan.
>
> 2. **`docs/PLAN.md:2119`, `:2182` (P0.12) and `:2193`, against `docs/STATUS.md` 7.12 on origin/main.** The plan does not record the owner's answer that stop rules 2 and 3 apply to a result from either machine. 7.12 settles it: "Stop rules 2 and 3 of the prompt (probe 2's trigger fires; probe 1's step a or b fails) apply to a result from either machine" (owner: "Yes, either machine stops it"). Plan 6.2 step 4 names only "Stop rules 4 and 5 of 10.3 … apply to this run as written", which reads as excluding 2 and 3. Line 2193 says the Owner items "are judged on the personal PC's files, with the work PC's word beside them". P0.12 sends a different trigger word to a ruling at the gate, not to a stop. Only `docs/tasks/P0-O2.md:86` records 7.12's answer, and a card is governed by the plan, not the other way round.
>
> 3. **`docs/PLAN.md:3508`.** The section heading (line 3504) now reads "On Windows, if the build sessions run on the owner's personal Windows PC (never on the work PC…)". A bullet under it still says "Proposed: Git for Windows on the work computer". Build sessions never run on the work PC, so the approval this bullet asks for names the wrong machine. Evidence: `git show origin/plan/pd-003-two-windows-machines:docs/PLAN.md | sed -n '3504,3508p'`.
>
> 4. **Owner time understated: `docs/PLAN.md:481`, `:490`, `:2319`, `:2821` (K27), `:3291` and `:3370`, against `docs/tasks/P0-O1.md:13` and `docs/tasks/P0-O2.md:13`.**
>    - The cards now say "about 45 minutes, attended, on each of the two machines" and "about 2 hours, attended, on each of the two machines".
>    - Plan 3.4's Time lines still read "about 45 minutes" and "about 2 hours". So the cards do not match their plan entries on Time.
>    - Line 3299 says the attended-time table is taken from those Time lines. So P0's "about 2 h 45 min" (line 3291) and K27's "about 7 hours attended" leave out the work PC repeats of P0-O1 and P0-O2, and every later gate's work PC check run.
>    - The 10.2 row "After P0-W6 integrates, at G0 … about 2 h" (line 3370) leaves out the work PC run. The P0-O1 row just above it was changed to "about 45 min on each machine".
>
> Checklist, plan change or new cards:
> - **Files changed:** only the four allowed (`git diff --stat origin/main...origin/plan/pd-003-two-windows-machines`: `docs/PLAN.md`, `docs/tasks/P0-O1.md`, `docs/tasks/P0-O2.md`, `prompts/02-orchestration-prompt.md`). The merge base is `2c89335`; the tip is `f4e9612`.
> - **Cards match plan section 3:** Owns, Uses and Provides, Tests first ("none"), Depends on, OS and Gate evidence match. Two exceptions: the work PC's base commit and dependency (defect 1) and Time (defect 4).
> - **Owns lines of P0-O1 and P0-O2 unchanged:** the diff has no `| Owns` line in either card and no `**Owns:**` line in plan 3.4.
> - **Card for an unplanned task:** none in this change. P0-W3-T4's card is out of scope, as the lead said.
> - **No path with two owners in one wave:** no task was added to a wave and no Owns line changed, so nothing repeats.
> - **Every dependency in an earlier wave:** holds for the planned Depends on lines. The work PC run of P0-O1 depends on a P0-W3 task that the plan does not name (defect 1).
> - **Gate numbers:** none changed. P0.5 and P0.12 gained text about where the evidence comes from and the owner's ruling when the machines differ. No number or threshold in 6.4 changed.
> - **Plan 5.7 choices:** no hunk touches 5.7.
> - **Plan 5.6 decisions:** only the "Decided by" cells of B3 and B4 changed (line 1973 hunk), adding "if the work PC's word differs, the owner rules at the gate (6.4, P0.12)". 11.2 has the same pointer. This is within what the lead allowed.
> - **Stop rules 4 and 5 still in force for the work PC:** prompt lines 58 and 59 and plan lines 3438 and 3439 are unchanged and still say "work computer". Plan 2119, `P0-O1.md` step 9 and `P0-O2.md:86` repeat them for the work PC run.
> - **Nothing committed or pushed from the work PC:** I grepped all four files on the branch for "work computer", "work machine", "owner's computer", "owner's Windows" and "his machine". No passage commits, pushes or merges from the work PC. The prompt's 3.6, 4, 6.5, 7 step 4 and 11.6, and the plan's 3.1, 6.1, 6.2 steps 4 and 5, and 10.2, each say nothing from it is committed or pushed.
> - **PD-003's list of places to correct:** every place listed in STATUS section 9 is changed. That is plan 3.1, 6.1, 6.2 step 4, 6.4, the later gates' OS lines, 10.2 and 10.3 item 15; both cards; and prompt section 1, 3.6, the section 4 table, 6.5 and section 7 step 4. The step-1 procedure is left alone, as the lead intended. The P0.12 rule for when the machines differ is present.
> - **STATUS 7.10 and 7.12:**
>   - The personal PC is the machine of record: matches.
>   - The work PC gives one word per item, recorded by the lead in "Work PC results by word": matches.
>   - The restricted share comes from the personal PC only: matches.
>   - When the machines differ, the owner rules at the gate: matches.
>   - Only the short checks run on the work PC: matches (3.1 and the OS lines of P2-O1 and P5-O1).
>   - Probe 1 is run by hand from Claude Code's shell on the work PC: matches (plan 6.1 and `P0-O2.md`).
>   - Stop rules 2 and 3 for either machine: in the card only, not the plan (defect 2).
> - **Rulings:** R107, R137 and R147 still hold. The personal PC is the owner's machine, and R107's anonymisation is unchanged. Checked with `git grep … docs/review/02-rulings.md`.
> - **Card question ids:** CQ-13 to CQ-17 are unused on origin/main. STATUS 7.3 says new ones start "from CQ-12", so CQ-12 is skipped. The lead already records "CQ-13 to CQ-17" in 7.12, and the skip does no harm.
>
> Checklist, changes to the prompt:
> - **Agrees with `AGENTS.md`, `CLAUDE.md` and `docs/PLAN.md`:** fixed rule 3 holds and pushes go only to origin. Prompt 3.6, 3.9, 6.5 and section 7 step 4 match plan 3.1, 6.1 and 6.2 steps 4 and 5. The prompt's section 3 roles are otherwise unchanged, including 3.3.
> - **Frontmatter fields:** not applicable. Nothing under `.claude/agents/` changed.
> - **Checker definitions keep no file-editing tool:** not applicable, for the same reason.
>
> I committed and pushed nothing. I only ran read-only git commands in /code/submeter-pc-monitor/submeter-pc-monitor-extract/.claude/worktrees/agent-a1f5e59e5a3e3de57.
