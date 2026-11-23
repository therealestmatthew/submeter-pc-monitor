# <task id> · <title>

<!--
How to use this template (delete this comment in a card):

- Copy it to docs/tasks/<task id>.md. Keep every "##" heading below, in this order. Write "none" under a heading that has nothing.
- The plan writer fills every section except "Review notes". The lead fills "Review notes" from each checker's reply.
- A card carries everything one builder needs. The builder reads the card first and then only what "Reads" lists; it needs no memory of any session.
- Every line of a card comes from docs/PLAN.md section 3 (the task's own entry), section 4 (ownership), section 6 (gates), section 7 (tests), docs/review/02-rulings.md or a brief topic file, and says which. Where none of them settles a point a builder would otherwise have to guess, the card says so under "Questions for the lead", with a default, and the same question goes into docs/STATUS.md section 7.3.
- "Owns" must equal the task's Owns line in docs/PLAN.md section 3 and its line in section 4.4, path for path. The plan reviewer checks this.
- The base commit B is never written on a card. A card that held B would need a commit made after B. B is given in the dispatch message and recorded in docs/STATUS.md (prompts/02-orchestration-prompt.md 5.2 step 7).
- Owner task cards (P<n>-O<k>) use the same headings with three differences (docs/PLAN.md 3.1, Owner tasks): "Time" (attended minutes on the owner's machine) replaces "Size"; "Tests first" says "none: an owner task changes no code"; "Provides" names each file the task records, its format and the tasks or gate items that read it. The branch is owner/<task id>, and "Identity" names the commit the task runs at.
- Plain Markdown. Nothing on a card is specific to one agent runner.
-->

## Identity

| Field | Value |
| --- | --- |
| Task | `P<n>-W<m>-T<k>`, <title> |
| Phase | P<n>, <phase title> (`docs/PLAN.md` 3.<x>) |
| Wave | P<n>-W<m>, planned width <w>; the other tasks of the wave: <ids>, or "none" |
| Plan entry | `docs/PLAN.md` 3.<x>, the paragraph headed "<task id> · <title>" |
| Depends on | tasks merged before this wave's base commit, and decisions recorded in `docs/STATUS.md` section 6; or "none" |
| Blocked by | decisions of `docs/PLAN.md` 5.6 that hold the task until recorded; or "none" |
| Size | S, M or L (`docs/PLAN.md` 3.1, Size), with the plan's line estimate if it gives one. Owner card: **Time**, in minutes on the owner's machine |
| OS | "either", "Windows (CI-W)", "Linux (CI-L)" or "the owner's machine" (`docs/PLAN.md` 3.1, OS), and what that means for "done" |
| Branch | `task/<task id>` (owner card: `owner/<task id>`) |
| Base commit | Not on this card: B is in the dispatch message and in `docs/STATUS.md` (prompt 5.2 step 7). Owner card: the commit the task runs at, named by its role (for example "the P0-W1 integration commit I, `docs/STATUS.md` section 4") |

## Goal

One paragraph: what is true when this task is merged that is not true at B, in terms a test or a command can check.

## Advances

The components of `docs/13-build-list.md` by number, the tools beside the code, and the findings (R-numbers) and combination entries (I-numbers) whose remaining work this task does, as the plan entry lists them.

## Owns

Every path this task may create, change or delete in its wave, one per line. A path ending in `/` covers everything under it. No other task of the wave owns any of these paths (`docs/PLAN.md` 4.1 rule 1). For each path, say whether it is created, changed or deleted.

A change needed in any other path is a change request in the task report (`docs/PLAN.md` 4.3), never an edit.

## Reads

The files to read before writing code, with line ranges where they help. The builder may read anything; these are enough. Always includes this card and `AGENTS.md`.

## Uses

The interfaces the task reads: records, functions, files, commands, operating-system calls, each with where it is defined.

## Provides

The interfaces the task adds or changes, with their names and types where the plan or brief gives them, and the later tasks that read them.

## Work

What to build, in the order to build it, taken from the plan entry. Points the plan leaves to the builder are marked "builder's choice; name it in the report". Points the plan does not settle and a builder would have to guess are not here: they are under "Questions for the lead".

## Tests first

The tests that fail at B and pass after the change. One row per test function.

| Test | Asserts | Fails at B because |
| --- | --- | --- |
| `tests/<file>.py::<test name>` | the behaviour, with the values | the reason, for example "the module does not exist" |

The first commit after B changes these test files and nothing else (prompt 3.4 step 4). From wave P0-W2 on, its CI run must show what `docs/PLAN.md` 7.2 step 1 expects: mypy errors only in this task's test files, the failed or errored tests exactly the ones above, every other test passed. In P0-W1 there is no CI at B, and the builder records the local failing output instead.

A task that changes no behaviour (a move) says how the reviewer shows nothing changed. A task that only delivers a test or a tool names the fault the reviewer plants (`docs/PLAN.md` 7.2 step 4). A fix for a test that already fails at B (an unplanned fix task, prompt 8.5) names that test and a CI run that shows it failing at B, or at an earlier commit that differs from B only under `docs/`, writes "already fails at B" in the third column, and needs no test-only commit (`docs/PLAN.md` 7.2, "Fixes for tests that already fail at the base commit"); a test it adds or sharpens still comes first.

## Acceptance

Numbered commands, each with the output that counts as a pass. Run in the builder's own working copy at the branch tip. Always includes:

1. The named tests: `uv run pytest <files> -q -rfE` → the summary line the card states.
2. The seven checks of `AGENTS.md`, each exit 0, with the system they ran on named.
3. Ownership: `git diff --name-only <B>..HEAD` → only paths under "Owns".
4. Tests first: `git diff --name-only <B> <test-only commit>` → only test files from "Tests first".
5. Any command the plan entry or the gate names, with its expected output.

## Gate evidence

The gate items of `docs/PLAN.md` section 6 this task's output feeds, and how.

## Rules that bear on this task

- The fixed rules of `AGENTS.md` (observe only; no administrator rights; nothing leaves the machine) that this task could break, and how the task keeps each.
- The entries of `AGENTS.md` "Rules that are easy to break" that the diff touches.
- Any ruling of `docs/review/02-rulings.md` or decision of `docs/PLAN.md` 5.6 or choice of 5.7 the task must follow.

## Questions for the lead

Each point the plan and brief do not settle, one per line: `CQ-<nn>`: the question; the default the card is written for; what changes if the answer differs. The same id is in `docs/STATUS.md` section 7.3, whose "Who answers" column says whether the lead or the owner answers it (the owner when the answer would change a ruling, a gate number, a decision of `docs/PLAN.md` 5.6 or a choice of 5.7; prompt 3.1). "none" if the card leaves nothing to guess.

If the builder meets a new one, it does not guess: it writes the question in its task report under "Questions for the lead" and, if the task cannot go on, reports `BLOCKED`.

## Review notes

Filled by the lead, never by the builder. One entry per review round: the checker's reply word for word, its agent id and the date. Checkers have no tool that writes files, so the lead copies the reply here and commits it to `main` as `Review <task id> round <n>` (prompt 4 and 5.4 step 3). The notes are therefore on `main`, not at B: a builder in round 2 or the escalated round E reads every entry, before changing anything, with `git fetch origin` and `git show origin/main:docs/tasks/<task id>.md`.

### Round 1

- Reviewer agent id:
- Date:
- Verdict: PASS, CHANGES or BLOCKED
- Reply (word for word):

### Round 2

- Reviewer agent id:
- Date:
- Verdict:
- Reply (word for word):

### Escalated round E

- Builder model and agent id:
- Reviewer agent id:
- Date:
- Verdict:
- Reply (word for word):
