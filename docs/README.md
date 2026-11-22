# Submeter: the build brief

A local performance monitor that answers three questions from one data set: what each workload costs, why the machine is slow right now, and how behaviour drifts over weeks.

This folder is the Submeter build brief as one file per section. Its own heading reads "Build brief · v8 · reviewed three times, with tested baseline code and a starter package". Every sentence, table and sample from the brief as delivered is here, and the topic files have since been corrected by the rulings in `review/02-rulings.md`. The charts and the dashboard mock, which the brief draws with script, are written out as tables and text, and [`brief.html`](brief.html) is the v8 brief as delivered, for anyone who wants to see them drawn. It is not updated after rulings.

## Read in this order

**Summary**

| File | What it holds |
| --- | --- |
| [`01-overview.md`](01-overview.md) | The three jobs, where each one shows and how you know it works, and the design in eight lines |

**Part 1 · The product**

What you would see and type once it is running.

| File | What it holds |
| --- | --- |
| [`02-what-it-looks-like.md`](02-what-it-looks-like.md) | The live dashboard planned for version 1.1: its layout, the seven workloads, the four scenarios, how the verdict is chosen, and the process trees |
| [`03-cli-output.md`](03-cli-output.md) | Sample output of `cost`, `why`, `doctor` and `store status` |
| [`04-features.md`](04-features.md) | What it does, in six groups: measure, attribute, remember, explain, show, protect |

**Part 2 · The design**

How the numbers are produced, and how far each one can be trusted.

| File | What it holds |
| --- | --- |
| [`05-data-flow.md`](05-data-flow.md) | The three programs and the path of one sample, why tagged workloads use kernel accounting, and what one sample becomes |
| [`06-storage.md`](06-storage.md) | Files and lifetimes, where they live, what a bucket records, which tier answers which question, the metric catalogue, and disk use |
| [`07-analysis.md`](07-analysis.md) | Leak detection, the session diff and the bottleneck verdict, with the data behind each chart, and the baseline anomaly check kept for after version 1 |
| [`08-configuration.md`](08-configuration.md) | Every setting with its default and range, the sample-time model, how configuration behaves, what is fixed on purpose, and both sample files |
| [`09-telemetry.md`](09-telemetry.md) | Where each metric comes from on Windows and Linux, what works without administrator rights, and the sources |
| [`10-known-limits.md`](10-known-limits.md) | What version 1 cannot measure, and what it does about each |
| [`11-language.md`](11-language.md) | Why Python, the alternatives, and when the collector would move to Rust |
| [`12-glossary.md`](12-glossary.md) | Fourteen terms |

**Part 3 · The build**

What gets made, in what order, and the prompt that starts it.

| File | What it holds |
| --- | --- |
| [`13-build-list.md`](13-build-list.md) | The 21 components, 16 tables and 14 commands of version 1, the API routes kept for version 1.1, and what is not in version 1 |
| [`14-baseline-modules.md`](14-baseline-modules.md) | The fifteen modules already written: what each does, why, what it provides, what it imports and what imports it |
| [`15-phases-and-decisions.md`](15-phases-and-decisions.md) | The six phases with their gates, the floor of version 1, and the four settled decisions |
| [`16-review-log.md`](16-review-log.md) | All 37 findings from three review passes, with an index |
| [`17-build-prompt.md`](17-build-prompt.md) | The whole specification as one prompt, kept as a compact digest |

**Reference**

| File | What it holds |
| --- | --- |
| [`reference/windows-priorities.md`](reference/windows-priorities.md) | What only a Windows computer can confirm, most urgent first, with what was done on Linux and how to check each item |
| [`reference/claude-code-notes.md`](reference/claude-code-notes.md) | What Claude Code does with instruction files, subagents, working copies and parallel agents, checked against its documentation on 20 November 2026 |
| [`brief.html`](brief.html) | The v8 brief as delivered, as a web page, with the charts, the working mock and the calculator. It is not updated after rulings; where it differs, the topic files win. Open it in a browser |

## Written later, by the sessions that build Submeter

| File | What it holds |
| --- | --- |
| `review/01-adversarial-review.md` | Findings from R38 on, from the first session |
| `review/02-rulings.md` | My ruling on each finding |
| `PLAN.md` | The formal plan: tasks, file ownership, waves and gates |
| `tasks/` | One card for each task |
| `STATUS.md` | What works, what was verified and how, and what could not be verified |

## Which file wins

1. The three fixed rules in `AGENTS.md`. Nothing overrides them.
2. `review/02-rulings.md`, once it exists. A ruling overrides anything written before it, and the document it affects is corrected at the same time.
3. The topic files, 01 to 16.
4. `17-build-prompt.md`, which restates the topic files compactly. Where the two differ, the topic file is right and the difference is a defect to report.
5. `brief.html` is the v8 page as delivered. It is not updated after rulings; where it differs, the topic files win.

`16-review-log.md` records why the design says what it says. Read it before proposing to undo something.

## History of the brief

Submeter was called Perfwatch until version 5 and Loadscope until version 8. Everything in the simulation, the sample charts and the sample-time explorer is synthetic or modelled.

1. Version 1: feature set, design decisions, first prompt.
2. Version 2: first adversarial review, simulated dashboard, data flow, sample charts.
3. Version 3: configuration design, language recommendation, build list.
4. Version 4: second review pass, platform claims checked against vendor documentation, known limits, memory view and per-core load in the simulation, baseline and polling figures, tables that reflow on phones.
5. Version 5: audit of storage and time periods, a store split by lifetime, the metric catalogue, the four open decisions settled, and the new name.
6. Version 6: fifteen baseline Python modules with tests, each with its purpose and its imports.
7. Version 7: the starter package and the execution prompt, with an adversarial review, a formal plan and a parallel-swarm orchestration prompt ahead of any build. The sample rule for untagged agents now matches the executable, where it used to match any command line that mentioned the name.
8. Version 8: renamed to Submeter, and the brief and the package reviewed file by file before the build starts.
