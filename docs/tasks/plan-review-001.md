# Plan review 001: a size exception for P0-W1-T2 (PD-001)

The change: branch `plan/p0-w1-t2-size`, written by the lead as plan writer, against `main` at `c62e940`; merged into `main` at `5635cf4` on 2026-11-28 after round 3 passed. It changes the Size row of `docs/tasks/P0-W1-T2.md`, `docs/PLAN.md` 3.1 (Size) and the plan entry of P0-W1-T2 in 3.4, and `prompts/02-orchestration-prompt.md` 8.1. The cause is planning defect PD-001 in `docs/STATUS.md` section 9.

Three rounds were used, each read by a different plan reviewer. The prompt sets a two-round limit for task reviews (8.1) and record reviews (5.7 step 4) and none for a plan change; the lead went on to a third round because each round found one real fault with a small, clear correction, and reported this to the owner.

Each reply below is the reviewer's final message, word for word, taken from its transcript.

## Round 1

- Reviewer agent id: acf85717eb9956990
- Date: 2026-11-28
- Read at: `db33ce5`
- Verdict: CHANGES
- Reply (word for word):

CHANGES

- **docs/tasks/P0-W1-T2.md:13 (card) against docs/PLAN.md:228 (plan 3.1, Size) and prompts/02-orchestration-prompt.md:411 (prompt 8.1).** The card overrides a plan rule that has no exception in it. Plan 3.1 says: "Nothing larger is planned, and a task that grows past L is split at its review." Prompt 8.1 says: "A task that grows past size L (about 600 changed lines) is split at review: the plan writer writes the parts as new cards, and the original card is closed with a note." Neither allows a card to say otherwise. The only escape is in the reviewer's check, prompt 3.5 check 5 (line 178): "unless the card says otherwise". That clause lets a card get past the reviewer, but it does not suspend the rule that tells the lead to split. Prompt section 1 puts the plan above the prompt on what is built, and a card comes from the plan. So the card can only say otherwise once the plan does. Evidence: `git diff c62e940 db33ce5` changes only `docs/tasks/P0-W1-T2.md` (1 insertion, 1 deletion). `docs/PLAN.md` and the prompt are unchanged on the branch. **Needed on `plan/p0-w1-t2-size`:** add an exception clause to plan 3.1 (line 228), with the same wording in prompt 8.1 (line 411). For example: a task found past L at review may be kept whole when its plan entry and card record a size exception under a planning defect that the plan reviewer has read.
- **docs/PLAN.md:322 (plan 3.4, the plan entry of P0-W1-T2) against docs/tasks/P0-W1-T2.md:13.** The plan entry still reads `**Size:** M` with nothing more. The card now carries an exception the plan does not have, so it no longer matches its plan task on Size. That match is required by the check for a plan change or new cards in prompt 3.3. The plan already has the form for this: P0-W2-T1 at docs/PLAN.md:336 reads `**Size:** L (about 890 lines move each way ...; the diff is longer than L's 300 to 600 lines, but ...)`, with the exception in the plan entry itself. **Needed:** the same kind of note on line 322, for example "M (finished at 989 changed lines; size exception PD-001)". The letter M can stay, so the counts in plan 5.3 and prompt section 1 ("15 S, 51 M, 29 L") do not change.

**Can the lead grant this, or does it need the owner?** The lead can grant it. No owner is needed.
- Prompt 3.1 lets the lead change `docs/PLAN.md` and `docs/tasks/`, with the plan reviewer reading each change. Its owner limit covers only a ruling, a gate number, a decision of plan 5.6 or a choice of plan 5.7.
- The size rule is none of these. `docs/review/02-rulings.md` says nothing about task size; its only line limit is the stage-1 "about fifty changed lines" rule for `fix now` changes (line 11). The rule is not a gate criterion in plan section 6, and it is not among B1 to B20 or C1 to C10.
- Prompt 6.4 step 4 and plan 10.3 ("Handled by the lead") treat the same kind of plan correction the same way: the owner is asked only if the correction changes a gate, a 5.6 decision or a 5.7 choice.

So NEEDS OWNER does not apply. But the exception does contradict plan 3.1 and prompt 8.1 as they stand, so a card change alone is not enough. The two plan changes above, plus the prompt 8.1 wording, are needed on the same branch.

Checklist (plan change or new cards):

- **Owns:** passes. Not changed by the diff. The card's five paths equal docs/PLAN.md:316 and 4.4 line 1577.
- **Uses and Provides:** passes. Not changed by the diff, and consistent with plan 3.4 lines 317 to 318.
- **Tests first:** passes. Not changed. The card's 11 tests cover the plan entry's list at docs/PLAN.md:320.
- **Depends on:** passes. Not changed: "none", matching docs/PLAN.md:322 and 5.1 line 1779.
- **Size:** fails. See the two defects. The figures on the card are right: `git diff --numstat 799feea origin/task/P0-W1-T2` printed 344, 136, 154, 117 and 238 (the three scripts add up to 407), and `--shortstat` printed "5 files changed, 989 insertions(+)".
- **OS:** passes. Not changed, and it matches docs/PLAN.md:322.
- **Gate evidence:** passes. Not changed. The card's "P0.2 (a), P0.3, P0.4, P0.5" is the step-1 part of the plan's "P0.2 to P0.5". P0.2 (b) runs at G0 under P0-O2 (plan 6.4).
- **No path has two owners in wave P0-W1:** passes. T1 owns `.github/workflows/ci.yml`, `pyproject.toml`, `uv.lock` and `tests/test_project.py`. T2 owns `scripts/probes/cpu_time_check.py`, `scripts/probes/restricted_share.py`, `scripts/probes/replace_names.py`, `tests/test_probe_step1.py` and `docs/review/ground-windows/step1-procedure.md`. No path repeats, and no path falls under a folder the other task owns (docs/PLAN.md:1576 to 1577).
- **Every dependency is in an earlier wave:** passes. P0-W1-T2 has none.
- **Nothing contradicts a ruling, a recorded STATUS decision, or a plan 5.7 choice:** passes on rulings and decisions. No ruling covers task size. CQ-02 and CQ-03 (`docs/STATUS.md` lines 199 to 200) and C3 are untouched by the diff. It fails on agreement with plan 3.1 and prompt 8.1, as set out above.
- **Branch shape:** origin/plan/p0-w1-t2-size is one commit, db33ce5, whose parent is c62e940 (`git log --format='%H %P %s' c62e940..db33ce5`). It changes only `docs/tasks/P0-W1-T2.md`.

Not a defect, for the record: plan 5.4 (line 1957) calls the pilot "two small tasks (sizes S and M)". The planned size stays M, and the pilot's clean-run condition ("each review settled within two rounds") still holds if round 2 passes.

I committed and pushed nothing. My working copy is clean: `git status --short` printed nothing.

Files read (lead's checkout untouched; reads from origin refs in my worktree):
- /code/submeter-pc-monitor/submeter-pc-monitor-extract/.claude/worktrees/agent-acf85717eb9956990/docs/tasks/P0-W1-T2.md (at db33ce5)
- /code/submeter-pc-monitor/submeter-pc-monitor-extract/.claude/worktrees/agent-acf85717eb9956990/docs/PLAN.md (at c62e940)
- /code/submeter-pc-monitor/submeter-pc-monitor-extract/.claude/worktrees/agent-acf85717eb9956990/prompts/02-orchestration-prompt.md (at c62e940)
- /code/submeter-pc-monitor/submeter-pc-monitor-extract/.claude/worktrees/agent-acf85717eb9956990/docs/STATUS.md (at c62e940)
- /code/submeter-pc-monitor/submeter-pc-monitor-extract/.claude/worktrees/agent-acf85717eb9956990/docs/review/02-rulings.md (at c62e940)

## Round 2

- Reviewer agent id: a4c5061fb5b92ecab
- Date: 2026-11-28
- Read at: `5a7c56e`
- Verdict: CHANGES
- Reply (word for word):

CHANGES
- `docs/PLAN.md:228` and `prompts/02-orchestration-prompt.md:411`: both new clauses begin "The one exception". That is not true, because the plan already sizes another task past L. P0-W2-T1's plan entry at `docs/PLAN.md:336` reads "**Size:** L (about 890 lines move each way with no assertion changed; the diff is longer than L's 300 to 600 lines, but the move is checked by collected names and counts, not read line by line)". Its card, `docs/tasks/P0-W2-T1.md:13`, says the same. That task will be about 1,780 changed lines when it is reviewed, so it will be "found past L at its review". Its plan entry and card name no planning defect in `docs/STATUS.md`. Under the new 8.1 wording ("is split at review ... The one exception ...") it therefore has to be split, which its own plan entry rules out. Before this change, 3.5 check 5's "unless the card says otherwise" was what kept P0-W2-T1 whole. The new clause now says no other exception exists, and "(first used for P0-W1-T2, PD-001)" says the same thing again. Evidence: `git grep -n -i -E "past (size )?L|grows past|split at" 5a7c56e` finds both clauses; `git show 5a7c56e:docs/PLAN.md | sed -n 336p` prints the P0-W2-T1 size line above. Fix: drop "one" and give both cases in both files. That is, a task whose plan entry sizes it past L and says why (P0-W2-T1), and a task found past L at its review whose plan entry and card record a size exception under a planning defect that the plan reviewer has read. The older "Nothing larger is planned" at line 228 is already contradicted by line 336, and should be corrected at the same time.

Checklist, plan change or new cards:
- **Round 1 defect 1 (no exception clause in the plan or the prompt): answered.** Commit 5a7c56e puts a clause into plan 3.1 Size (line 228) and prompt 8.1 (line 411), on the same branch as the card. Apart from the defect above, the two clauses agree with each other and with 3.5 check 5 ("unless the card says otherwise").
- **Round 1 defect 2 (plan 3.4 entry still read "Size: M"): answered.** `docs/PLAN.md:322` now reads "M (finished at 989 changed lines; size exception PD-001, `docs/STATUS.md` section 9)". That matches the card's Size row, "M as planned. Size exception (PD-001 ...)".
- **Is the wording too wide?** Not beyond the defect above. Each use needs a plan entry, a card, a planning defect and a plan review. The card limits its own exception to "about 1,000 changed lines" and to check 5 alone ("covers this task only and no other check").
- **The card's figures:** `git diff --numstat 799feea origin/task/P0-W1-T2` (tip 6139e62) printed 344, 136, 154, 117 and 238 lines. That is 407 in the three scripts and 989 in all, which matches the card and PD-001.
- **Card against plan task.** Owns, Tests first, Depends on, Size, OS and Gate evidence all match. This change edits only the Size row. The card's five Owns paths are exactly the plan's Owns line (`docs/PLAN.md` 3.4, P0-W1-T2). Depends on is "none" in both.
- **No path has two owners in the wave.** P0-W1-T1 owns `.github/workflows/ci.yml`, `pyproject.toml`, `uv.lock` and `tests/test_project.py`. P0-W1-T2 owns `scripts/probes/cpu_time_check.py`, `scripts/probes/restricted_share.py`, `scripts/probes/replace_names.py`, `tests/test_probe_step1.py` and `docs/review/ground-windows/step1-procedure.md`. No path appears twice. The three files this branch changes belong to the lead (plan 4.1 rule 5) and are on no Owns line.
- **Every dependency is in an earlier wave:** both tasks in the wave depend on nothing, and this change leaves that as it was.
- **Nothing contradicts a ruling, a decision in STATUS or a 5.7 choice.** `docs/review/02-rulings.md` says nothing about builder task sizes. Its only line limit is the stage-2 "about fifty changed lines" for `fix now` work (line 11). Size is not a 5.6 decision, a 5.7 choice (C1 to C10) or a gate number. The branch is cut from c62e940 (`git merge-base` = c62e940) and has two commits.
- **No owner decision is needed, and I agree.** Prompt 3.1 lets the lead change `docs/PLAN.md` and this prompt, with each change read by the plan reviewer. Prompt 3.1 "Answers", 6.4 step 4 and plan 4.3 items 5 and 6 send to the owner only changes to a ruling, a gate number, a 5.6 decision or a 5.7 choice. The size rule in plan 3.1 is none of those, and it is not on plan 10.2's list of "Approvals only the owner can give".

Checklist, change to the orchestration prompt:
- **Agrees with `AGENTS.md` and `CLAUDE.md`:** it touches none of their rules (observe only, no administrator rights, nothing leaves the machine, the checks).
- **Agrees with the plan:** 8.1 now matches plan 3.1 word for word, apart from the "one exception" defect.
- **Agrees with section 3:** the 3.3 plan reviewer's job and 3.5 check 5 are unchanged and consistent with it.
- **`.claude/agents/`:** not changed. `git diff --stat c62e940 5a7c56e` lists only the three files.

I committed and pushed nothing. My working copy was read only.

Files involved:
- `/code/submeter-pc-monitor/submeter-pc-monitor-extract/.claude/worktrees/agent-a4c5061fb5b92ecab/docs/PLAN.md` (lines 228, 322, 336 at 5a7c56e)
- `/code/submeter-pc-monitor/submeter-pc-monitor-extract/.claude/worktrees/agent-a4c5061fb5b92ecab/prompts/02-orchestration-prompt.md` (line 411)
- `/code/submeter-pc-monitor/submeter-pc-monitor-extract/.claude/worktrees/agent-a4c5061fb5b92ecab/docs/tasks/P0-W1-T2.md` (line 13)
- `/code/submeter-pc-monitor/submeter-pc-monitor-extract/.claude/worktrees/agent-a4c5061fb5b92ecab/docs/tasks/P0-W2-T1.md` (line 13)

## Round 3

- Reviewer agent id: a9f00b51f0151b606
- Date: 2026-11-28
- Read at: `95b52eb`
- Verdict: PASS
- Reply (word for word):

PASS

The wording at 95b52eb holds for the whole plan, and I found no defect in the three commits. Nothing was committed or pushed, and I ran only read commands in my own worktree.

**Plan change or new cards: checklist**

- **The card matches its plan task.** Commit db33ce5 changes only the card's Size row, and 5a7c56e changes the Size of P0-W1-T2's plan entry (`docs/PLAN.md:322`). Both say "M" as planned, record the size exception and cite PD-001. Owns, Tests first, Depends on, OS and Gate evidence are unchanged (`git log --name-only` shows the card touched only by db33ce5, in that one row).
- **The 989 figure and its breakdown are correct.** `git diff --numstat 799feea origin/task/P0-W1-T2` gives 344 for the procedure, 136 + 154 + 117 = 407 for the three scripts and 238 for the tests: 5 files, 989 insertions. Those five paths are exactly the card's Owns and the plan entry's Owns (`docs/PLAN.md` 3.4, line 317).
- **No path has two owners in the wave.** P0-W1-T1 owns `.github/workflows/ci.yml`, `pyproject.toml`, `uv.lock` and `tests/test_project.py`. P0-W1-T2 owns the three files in `scripts/probes/`, `tests/test_probe_step1.py` and `docs/review/ground-windows/step1-procedure.md`. No path repeats, and this branch changes no Owns line.
- **Every dependency is in an earlier wave.** Depends on is still "none", unchanged.
- **The wording is true of the whole plan.** I searched the Size values in `docs/PLAN.md` at 95b52eb:
  - 27 plain L, 50 plain M, 15 S and three with a note.
  - The only entry sized past L is P0-W2-T1: "L (about 890 lines move each way …; the diff is longer than L's 300 to 600 lines …)" at line 336.
  - P0-W3-T1's note gives about 252 lines, within L. P0-W1-T2 is the review-time case.
  - The card Size rows in `docs/tasks/` (`git grep "^| Size |"`) agree: only P0-W2-T1 is past L.
  - The only other passages about growing past L are risks K31 and K42 (lines 2830 and 2884). Both describe a possible overrun and answer it with a split, which is consistent with the default rule.
  - So "except where a plan entry sizes its task past L and says why (P0-W2-T1)" and the two named cases are complete. The round 2 defect ("The one exception") is gone.
- **Nothing contradicts a ruling, a STATUS decision or a 5.7 choice.**
  - `docs/review/02-rulings.md` sets no task size. Its only line threshold is the stage-1 "about fifty" for `fix now` changes (lines 11 and 278).
  - Plan 5.6 and 5.7 (lines 1968 to 2011) hold no size or split rule, so under prompt 6.4 step 4 the lead may make this change without the owner.
  - PD-001 is in `docs/STATUS.md` section 9 (line 292, on `origin/main`), and this branch leaves STATUS unchanged, as the lead's own PD-001 proposal says.
  - Plan 5.4 still calls the pilot "two small tasks (sizes S and M)". That gives the planned sizes, which the entry keeps ("M … finished at 989"), so it is not a contradiction.

**Changes to the orchestration prompt or `.claude/agents/`: checklist**

- **Plan 3.1 and prompt 8.1 agree.** Both name the same two cases in the same words: a task whose plan entry sizes it past L and says why (P0-W2-T1), and a task found past L at review whose plan entry and card record a size exception under a STATUS planning defect the plan reviewer has read. The prompt points to "plan 3.1, Size" (`prompts/02-orchestration-prompt.md:411`, `docs/PLAN.md:228`).
- **Prompt 3.5 check 5 agrees with both.** Check 5 (`prompts/02-orchestration-prompt.md:178`) and `.claude/agents/code-reviewer.md:123` both say more than about 600 lines should have been split "unless the card says otherwise". The P0-W1-T2 card now says otherwise in so many words: "For check 5 of prompt 3.5 this card says otherwise: up to about 1,000 changed lines pass on size." 989 is within that. The P0-W2-T1 card already gives its 890-line estimate.
- **Neither of the other two files needs a change.** `git grep` for "split at review", "600" and "size exception" in `.claude/agents/` finds only `code-reviewer.md:123`, quoted above, and it already agrees. `AGENTS.md` and `CLAUDE.md` say nothing about task size.
- **Frontmatter and file-editing tools are untouched.** `git log --name-only c62e940..95b52eb` lists only `docs/tasks/P0-W1-T2.md`, `docs/PLAN.md` and `prompts/02-orchestration-prompt.md`.

**Range and scope:** `origin/plan/p0-w1-t2-size` is at 95b52eba2bee0808c469f8e1e6dae7a606f20ff3 and `origin/main` at c62e940, so the three commits sit directly on main. Each commit touches only the files the lead named.

**Two notes**

- **Card on main first.** The code reviewer reads the card "as it stands on `origin/main`" (prompt 3.5, Reads). This branch has to be merged before round 2 of the code review of `task/P0-W1-T2`, or that reviewer will not see the exception.
- **An older count, not part of this change.** Risk K42 (`docs/PLAN.md:2884`) says "There are 27 tasks of size L". The plan has 27 plain L entries plus 2 L entries with a note (P0-W2-T1 and P0-W3-T1), 29 in all. The count was the same before this branch, so I have not counted it against this round.

Files read:
- /code/submeter-pc-monitor/submeter-pc-monitor-extract/.claude/worktrees/agent-a9f00b51f0151b606/docs/PLAN.md (at 95b52eb)
- /code/submeter-pc-monitor/submeter-pc-monitor-extract/.claude/worktrees/agent-a9f00b51f0151b606/docs/tasks/P0-W1-T2.md (at 95b52eb)
- /code/submeter-pc-monitor/submeter-pc-monitor-extract/.claude/worktrees/agent-a9f00b51f0151b606/prompts/02-orchestration-prompt.md (at 95b52eb)
- /code/submeter-pc-monitor/submeter-pc-monitor-extract/.claude/worktrees/agent-a9f00b51f0151b606/docs/STATUS.md (section 9)
- /code/submeter-pc-monitor/submeter-pc-monitor-extract/.claude/worktrees/agent-a9f00b51f0151b606/.claude/agents/code-reviewer.md (line 123)
