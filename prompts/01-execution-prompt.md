# Submeter: review, plan, then write the orchestration prompt

You are working in the Submeter repository on my Windows 11 work computer. Submeter is a local performance monitor: a collector, a server and a command line that attribute CPU, memory and I/O to named workloads. The repository holds the design brief under `docs/`, a small tested baseline under `src/` and `tests/`, and the standing rules in `AGENTS.md`, which `CLAUDE.md` imports. Nothing else has been built.

This session does not build Submeter. It does three things in order and stops for me twice:

1. An adversarial review of the brief and the baseline. Then stop for my rulings.
2. A formal plan that reflects those rulings.
3. The orchestration prompt that a later session will run to build Submeter with a parallel swarm of agents. Then stop.

## What is fixed and what is open

Three rules are fixed. Do not propose changing them. Check instead that every part of the design obeys them.

1. Observe only. Version 1 never changes a process: no priority, affinity, suspend, kill or memory cap, and no setting that enables one.
2. No administrator rights. Every program runs as the signed-in user and never asks to elevate.
3. Nothing leaves the machine. No upload, webhook, telemetry or update check. The API listens on loopback only.

Everything else is open to challenge, including choices I made earlier: the three jobs carrying equal weight, the service plus dashboard plus command line, the extra telemetry, Python as the language, the phase order, the 25 components and the baseline code. If one of them is wrong for version 1, say so as a finding, with evidence and the cheaper alternative. I would rather cut scope now than find out in phase 4.

## Before stage 1: establish the ground

1. Check the package is whole: `AGENTS.md`, `docs/README.md`, `prompts/`, `src/submeter/`, `tests/` and `pyproject.toml`. If anything is missing, stop and tell me.
2. If this folder is not a git repository, make it one with `git init -b main`. Either way, commit the package exactly as delivered, as one commit named "Package as delivered". That commit is the reference for "the review changed nothing". If git has no identity configured, ask me.
3. Connect it to GitHub. The repository is https://github.com/therealestmatthew/submeter-pc-monitor. Add it as `origin` if it is not set, confirm it answers with `git ls-remote origin`, and push `main`. If the remote already holds commits this folder does not have, stop and tell me before changing either side.
4. Report the Windows build, the shell you are using, the Python and uv versions, and your own version.
5. Run `uv sync`. It writes `uv.lock`, which the package does not ship. Commit that file on its own as "Lock dependencies", so that later diffs stay clean.
6. Run the baseline checks and keep their full output: `uv run ruff check`, `uv run ruff format --check`, `uv run mypy src tests`, `uv run pytest`. These have passed on Linux only. A failure here is a finding to report, not something to fix yet.
7. Run `uv run python scripts/platform_check.py` and keep its full output. It checks the parts of the baseline that depend on the operating system, and it has only ever run on Linux. `docs/reference/windows-priorities.md` explains each line and lists what else only this computer can confirm, most urgent first.
8. Read `docs/README.md`, then the documents it lists, then the code and its tests. `docs/16-review-log.md` holds 37 earlier findings, R01 to R37. Do not report those again unless a fix is missing or wrong.

## Stage 1: adversarial review

Read as someone trying to prove the design wrong. The aim is to find what would make Submeter's numbers false, break one of its promises, or make the build fail, while fixing it still costs a sentence and not a phase.

Rules for this stage:

- Change nothing. No edits to code, tests, documents or settings. You may create files only under `docs/review/`, and throwaway probe scripts only under `docs/review/probes/`. At the end, `git status --short` must show new files under `docs/review/` and nothing else.
- Verify before you assert. Mark each finding verified or suspected. Verified means you ran something on this machine, read the code, or found it in the vendor's documentation, and you cite the command and its output, the file and line, or the link. Suspected means you say what would confirm it. Do not rest a finding on memory of how Windows behaves when the machine is here to test.
- Probes obey the fixed rules: they read and measure, they never elevate, and they send nothing anywhere. They use the standard library, ctypes and the packages `uv sync` installed. Ask me before installing anything else on this computer. Reading vendor documentation on the web is fine. The only place this repository goes is its GitHub remote.
- Try to refute each finding before you keep it. A reviewer asked for problems always finds some, so report only what affects correctness, the fixed rules, the three jobs, or whether the build can succeed. No points of style. A few verified findings are worth more than many suspected ones.
- Use subagents to read in parallel where that keeps your own context clear: one per lens, reading only. Treat what they return as leads and check each one yourself before it goes in the report.

Cover every lens, and say "nothing found" where that is the result:

- **A. True on this machine.** Work through `docs/reference/windows-priorities.md` in its order. Each Windows claim in `docs/09-telemetry.md` and `docs/10-known-limits.md`. Whether this user can create Job Objects, nest them, and read accounting for children that have exited. What the bulk process snapshot and performance counters return without elevation. What security software or policy on a work computer blocks.
- **B. Measurement.** Whether each gate in `docs/15-phases-and-decisions.md` can be met as written. Measure the cost of one full process snapshot here with the baseline's psutil provider, 20 runs, median and worst, and compare it with the 1% and 3% overhead limits and the switching rule in `docs/11-language.md`. Check the attribution order, the reconciliation tolerances and the polling model.
- **C. Storage and time.** Retention, exact rollups, crash safety, suspend, clock changes and daylight saving, the disk budget arithmetic, and SQLite on Windows: write-ahead logging, deleting a file that is open, antivirus holding a file.
- **D. Privacy and local security.** Try to get a secret past `redact_cmdline`. Check the token, the loopback API, what an MCP client could read, and what reaches a log.
- **E. The baseline code.** Bugs, behaviour on Windows (the one-instance lock and private-bytes memory have never run there), gaps in the tests, and interfaces that will cost later.
- **F. Consistency.** Brief against brief and brief against code: counts, names, defaults, ranges. Anything stated twice with different values. Anything promised and never specified.
- **G. Buildability.** Gates that cannot be tested as written, work that needs Linux or hardware this machine lacks, phases that are too large, fixtures that do not exist, and every place a builder would have to guess.
- **H. Scope.** What to cut, defer or reorder for version 1, given what the other lenses found.

Write the report to `docs/review/01-adversarial-review.md`:

- **Ground.** The environment and the baseline check results.
- **Summary.** Counts by severity, the ten findings that matter most, and anything that blocks planning.
- **Findings**, numbered from R38. For each: title, lens, severity, status with its evidence, impact, the proposed change (which file, and what it should say or do), the cost, whether it needs my decision, and the disposition you recommend.
- **Not checked.** What you could not verify, and why.

Severity: critical means a number would be wrong or a fixed rule broken. High means a job or a gate fails under real conditions. Medium means misleading, or costly later. Low means worth knowing.

Disposition: `fix now` for a small change to a document or to the baseline that should happen before planning. `plan` for work to schedule as a task. `reject`. `defer` for after version 1.

Then stop. In chat, give me a summary of 15 lines or fewer, then the decisions you need as a numbered list with your recommendation for each. I will answer "accept all recommendations", or list finding numbers with dispositions.

## After my rulings

1. Record them in `docs/review/02-rulings.md`: the finding, my ruling, and my reason if I gave one.
2. Make the documents true. Every accepted finding that changes the design is written into the document that states it, one commit per finding, with the finding number at the start of the message. This applies to `fix now` and to `plan` alike, so that nobody later builds from a document we already know is wrong.
3. Apply the `fix now` changes to code, and only those. For each: change or add the test first and show it failing, make it pass, commit with the finding number. If one grows past about fifty changed lines, stop and move it to `plan`.
4. Run the full checks again. A green baseline on this machine is the entry condition for stage 2. If it cannot be reached with `fix now` changes, tell me before planning.

## Stage 2: the formal plan

Write `docs/PLAN.md`. It must contain:

1. The objective, and what "version 1 is done" means in terms that can be tested.
2. The rulings that changed the brief, with the documents that were updated.
3. The work breakdown: phases, then waves, then tasks. Each task has an id, the components it advances, the files it owns, the interfaces it uses and provides, the tests that must fail first and then pass, the gate evidence it contributes, what it depends on, a size, and the operating system it needs.
4. A file ownership map. In any wave each path has exactly one owning task. Shared files, such as `pyproject.toml`, `uv.lock`, `core/models.py`, `core/config.py`, `cli.py`, `AGENTS.md` and `docs/STATUS.md`, have one named owner, and the plan says how anyone else requests a change.
5. The dependency graph, the waves that follow from it, and the planned width of each wave.
6. The gates. For each phase gate: the exact commands or procedure, the pass criteria as numbers, the evidence to keep, who checks it (never the agent that did the work), and which gates need me or a second operating system.
7. The test strategy: fixtures, the load generator, recorded provider output, the CI matrix, and what cannot be tested here.
8. A risk register, including the decision point between a Python and a Rust collector with the numbers you measured.
9. Traceability: a table from each of the three jobs, each fixed rule, each known limit and each accepted finding to the tasks and tests that cover it. Nothing in the brief is left without a task or an explicit "not in version 1".
10. Cadence: how many waves and sessions you expect, where I am needed, and the conditions under which the build stops and asks.
11. Open questions for me.

Before stage 3, check the plan against itself: each of the 25 components is in a task or cut by a ruling, every gate has a procedure, no two tasks in a wave own the same file, and the first wave is small enough to be a pilot.

## Stage 3: the orchestration prompt

Write `prompts/02-orchestration-prompt.md`. A fresh session will be given that file to build Submeter. It must work with no memory of this session, so everything it needs is in the repository.

The build style is a parallel swarm: a lead session coordinates while several builders work at once, each on its own files. Design it on these principles:

1. **The lead coordinates and carries little.** It holds the plan, the status, the task cards, the merge order and the gates. It writes no product code, and it reads summaries in place of whole files wherever it can.
2. **Every producer has a separate checker.** Whoever writes a thing does not approve it: plan writer and plan reviewer, builder and code reviewer, test runner and failure investigator. A checker starts with fresh context and tools that cannot write.
3. **Exclusive file ownership.** No file has two writers in one wave.
4. **Tests first.** A task starts from a failing test that states its acceptance criteria. The reviewer confirms the test failed before the change and passes after it.
5. **Bounded loops.** At most two review rounds for a task, then escalate to a stronger model or to me. No open-ended retrying.
6. **I approve gates.** Merges inside a wave are automatic once checks and review pass. A phase gate waits for me, with the evidence in front of me.
7. **State lives in files.** `docs/PLAN.md`, `docs/STATUS.md`, the task cards and the review notes are enough for a new session to resume after any interruption.
8. **Neutral where possible.** Roles, task cards and rules are plain Markdown that another agent runner could follow. Anything specific to Claude Code stays under `.claude/` and in one marked section of the prompt.

Produce:

- `prompts/02-orchestration-prompt.md`, covering its purpose and stop rules, the roles, the wave loop (select, dispatch, review, integrate, verify, record), the integration and gate procedures, failure handling and escalation, how to resume, the three fixed rules, and how it reports to me.
- `.claude/agents/`, one definition for each role other than the lead. Use only fields your current documentation lists.
- `docs/tasks/`, with a task card template and the cards for the first phase. Cards for a later phase are written when that phase begins.
- `docs/STATUS.md`, in its starting state.
- Any settings the swarm depends on, each explained in the prompt.

Get these mechanics right, and check them against your own current documentation instead of memory. `docs/reference/claude-code-notes.md` records what the documentation said on 20 November 2026.

- How each builder is isolated, and which commit its working copy starts from. It must be the wave's base commit, which is not always the default: with a remote configured, a new working copy can start from the remote's default branch, so push before each wave or set the base explicitly.
- A new working copy is a fresh checkout and needs its own `uv sync`.
- How work comes back: one branch per task, merged by the lead in dependency order, with the full checks after each merge. If ownership holds there are no conflicts, so a conflict is a planning defect to record, not to patch around.
- The width. Start with a pilot wave of two builders. Widen only when the pilot integrates cleanly, and state the cap and the reason for it.
- Windows: path lengths, locks on SQLite files and virtual environments, line endings, antivirus slowing many small writes, and the absence of sandboxing.
- Which mechanism to use: subagents, agent teams or something else. Choose by what the documentation says today about stability, resuming and isolation. Prefer one that is not experimental and survives a resumed session, and say why in the plan.

Check the orchestration prompt before you stop:

1. **Cold read.** Give it to a fresh subagent that has the repository and nothing else. Ask it, without starting work, what it would do first, every place it would have to guess, and anything that contradicts `AGENTS.md` or the plan. Fix and repeat until no guess would block it. Save the last report as `docs/review/03-orchestration-cold-read.md`.
2. **Pilot on paper.** Name the pilot wave's tasks, the files each owns, the base commit, the merge order and the checks. Confirm no file has two owners.
3. **Clean state.** Commit your work. All checks pass and `git status` is clean.

Then stop and tell me, briefly: what you wrote and where, the decisions I still owe you, the exact message that starts the build session, and what you could not verify.

## Working rules for this session

- If the conversation is compacted or resumed, read this file and `docs/review/` again to find your place before you continue.
- Show evidence, not confidence: the command and what it printed.
- If something here conflicts with what this machine or your tools can do, say so and propose the nearest honest alternative. Do not work around it quietly.
- Commit as you go and push to `origin` freely, at the least at each stop. Do not rewrite history that is already pushed, and push nowhere else.
