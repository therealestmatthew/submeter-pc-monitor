# Submeter

Submeter is a local performance monitor that attributes CPU, memory and I/O to named workloads. This repository holds its brief, the baseline modules, the standing rules, the plan and the prompts that build it. It began as the Submeter starter package, and the build of version 1 has not started yet.

## Where the project stands

The package was committed as delivered on 20 November 2026 (`4823b09`, "Package as delivered"). The first session made the folder a git repository and committed it before changing anything, so that it could prove its review changed nothing. The execution prompt, `prompts/01-execution-prompt.md`, has since been run in full:

| Step | Date | Record |
| --- | --- | --- |
| Ground: the package committed as delivered, `uv.lock` added | 20 November 2026 | `4823b09`, `bfcb188` |
| Stage 1: the adversarial review, 116 findings (R38 to R153), with the ground checks' output | 21 November 2026 | `docs/review/01-adversarial-review.md`, `docs/review/ground/` (`5295097`) |
| Stop 1: the owner's ruling, "Accept all." | 21 November 2026 | `docs/review/02-rulings.md` (`561a266`) |
| The rulings applied to the documents and the code, one commit per finding | 21 to 22 November 2026 | up to `1c734e0` |
| Stage 2: the formal plan | 23 November 2026 | `docs/PLAN.md` (`76ebe71`) |
| Stage 3: the orchestration prompt, the agent definitions and settings, the task cards of phase P0 and the starting status | 23 November 2026 | `prompts/02-orchestration-prompt.md`, `.claude/`, `docs/tasks/`, `docs/STATUS.md` (`75974eb`) |

`main` is on `origin` at the stage 3 commit. Stop 2, the owner's review of stage 3's output, is open: it is decision S3-1 and entry condition E1 in [`docs/STATUS.md`](docs/STATUS.md). No lead session has run and no task has been dispatched.

## How to start

The build starts from the orchestration prompt, [`prompts/02-orchestration-prompt.md`](prompts/02-orchestration-prompt.md). Start Claude Code interactively in the repository root, without `--effort ultracode`, accept the workspace trust dialog if asked, and send:

```text
Read prompts/02-orchestration-prompt.md and follow it.
```

That session is the lead. It reads [`docs/STATUS.md`](docs/STATUS.md), which says where the build stands and what it waits on. Before the first wave, the pilot P0-W1, the owner approves stage 3's output (S3-1), says which machine the build runs on (Q1), approves the permission rules and the lead's permission mode (S3-3, S3-4), and answers or lets stand the other questions that `docs/STATUS.md` section 7 marks for P0-W1. Section 12 of the orchestration prompt lists every decision the owner owes. If the build runs on Windows, start the lead there, in a clone set up as [Starting the build on Windows](#starting-the-build-on-windows) describes.

## The two sessions

**FIRST SESSION · prompts/01-execution-prompt.md** · run from 20 to 23 November 2026

1. **Ground:** check the package · commit it · run the checks
2. **Stage 1 · Adversarial review:** eight lenses · verified on this machine · changes nothing
3. **Stop 1 · The owner's rulings:** fix now · plan · reject · defer
4. **Apply the rulings:** documents made true · small fixes, test first
5. **Stage 2 · Formal plan:** tasks · file ownership · waves · gates
6. **Stage 3 · Orchestration prompt:** roles · task cards · wave loop · cold read
7. **Stop 2 · The owner's review:** the plan and the prompt, before anything is built

**SECOND SESSION · prompts/02-orchestration-prompt.md**, written by the first session in stage 3

8. **Build · Parallel swarm:** a lead, with paired builders and reviewers · the owner approves gates

*Figure:* The first session wrote documents and small approved fixes, and stopped twice. Steps 1 to 6 are done; step 7 is open (S3-1). The build is the second session, started with the prompt the first one wrote. It has not been started.

## The execution prompt

`prompts/01-execution-prompt.md`, 2,742 words, was part of the package. It ran the first session above from 20 to 23 November 2026. Open [`prompts/01-execution-prompt.md`](prompts/01-execution-prompt.md) to read it.

### What was fixed and what was open

- Fixed: observe only, no administrator rights, and nothing leaves the machine. The review checked that the design obeys these three and could not reopen them.
- Open: everything else, including the three jobs, the interface, the extra telemetry, Python, the phase order, the components in docs/13-build-list.md and the baseline code. A finding that argued for a cut needed evidence and a cheaper alternative.

### How the review was held to account

- It changed nothing: the stage 1 commit added files only under `docs/review/`.
- Every finding was marked verified or suspected: 114 verified and 2 suspected. Verified means a command and its output, a file and line, or a link to the vendor's documentation.
- It was required to try to refute each finding before keeping it, and to report nothing about style.
- It covered eight lenses: true on this machine, measurement, storage and time, privacy and local security, the baseline code, consistency, buildability and scope.
- Findings continued the numbering in the review log, from R38 to R153. Each carried a recommended ruling: fix now, plan, reject or defer.

### The build style it wrote for

- A lead session coordinates and writes no product code.
- Every producer has a separate checker that starts with fresh context and cannot write.
- No file has two writers in one wave.
- Every task starts from a failing test.
- At most two review rounds for a task, then it escalates.
- Merges inside a wave are automatic. A phase gate waits for the owner.
- All state is in files, so the build can stop and resume.
- Roles and task cards are plain Markdown that another agent runner could follow.

## What is in the repository

| Path | What it is |
| --- | --- |
| `README.md` | What the repository is, where the project stands and how to start the build |
| `AGENTS.md, CLAUDE.md` | The rules for every session: the three fixed rules, the checks to run, and the conventions that are easy to break. CLAUDE.md imports AGENTS.md, so other coding agents read the same rules |
| `prompts/01-execution-prompt.md` | The execution prompt, part of the package, run from 20 to 23 November 2026 |
| `prompts/02-orchestration-prompt.md` | The orchestration prompt, written in stage 3. The build starts from it |
| `.claude/agents/, .claude/settings.json` | The definitions of the build's seven agent roles other than the lead, and the permission rules and settings the build relies on, written in stage 3 |
| `docs/` | The brief, one file per section, with every chart and the dashboard mock written out as tables and text. Also the page itself as brief.html, notes on Claude Code checked against its documentation, and a list of what to check first on Windows |
| `docs/review/` | The stage 1 review and its evidence, the owner's rulings, and the cold read of the orchestration prompt |
| `docs/PLAN.md` | The formal plan: tasks, file ownership, waves and gates |
| `docs/tasks/` | The task cards of phase P0, and the card template |
| `docs/STATUS.md` | Where the build stands, kept by the lead |
| `scripts/platform_check.py` | One command that checks the parts that depend on the operating system and prints the evidence |
| `src/submeter/, tests/, pyproject.toml, uv.lock` | The baseline modules and their tests, already in place, and the locked dependencies |
| `examples/` | The sample submeter.toml and rules.toml |

## Starting the build on Windows

The build machine is not decided yet: it is question Q1 in `docs/STATUS.md`, the Windows 11 computer as the signed-in standard user, or Linux. On Windows the lead runs in a clone of `origin` that meets entry condition E5 (orchestration prompt section 11.6): Git for Windows installed, the clone at a root of 40 characters or fewer, and `git config core.longpaths true` set in it. Git, uv and Claude Code must be installed; the commands are under [Installing the tools](#installing-the-tools).

```text
PS> git clone https://github.com/therealestmatthew/submeter-pc-monitor.git C:\src\submeter
PS> cd C:\src\submeter
PS> git config core.longpaths true
PS> claude

> Read prompts/02-orchestration-prompt.md and follow it.
```

The package was delivered as a zip. The instructions it carried for unpacking it on Windows and handing over the execution prompt are in the README as delivered: `git show 4823b09:README.md`.

## Installing the tools

Three tools need to be on the Windows computer.

- **Git.** [Git for Windows](https://git-scm.com/downloads/win) also gives Claude Code a Bash shell to work in.
- **uv.** In PowerShell: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`, or `winget install --id=astral-sh.uv -e`. It fetches a suitable Python by itself.
- **Claude Code.** In PowerShell: `irm https://claude.ai/install.ps1 | iex`. Then `claude --version` confirms it, and `claude doctor` reports on the install.

## The GitHub repository

The project lives at <https://github.com/therealestmatthew/submeter-pc-monitor>. It is this repository's `origin`, and `main` is there at the stage 3 commit. Sessions push freely (`CLAUDE.md`). In the build, each builder pushes only its own task branch and the lead pushes `main` (orchestration prompt sections 3.4 and 6.1).

There is no license file yet, so all rights stay with the owner until one is added.

## What has and has not been checked

- Before delivery, the code was unpacked from the package into an empty folder on Linux, where `uv sync`, Ruff, mypy in strict mode and all 20 tests passed. mypy was also run as if on Windows.
- In the first session the checks ran again on Linux (`docs/review/ground/`), and the rulings' code fixes brought the tests to 62 (`docs/14-baseline-modules.md`).
- Nothing here has run on Windows yet. The review and stage 3 ran on Linux. Phase P0 of the build is where Windows is checked: CI on a Windows runner (P0-W1-T1), and step 1 and the three probes on the owner's Windows computer (P0-O1, P0-O2). [`docs/reference/windows-priorities.md`](docs/reference/windows-priorities.md) lists what to check, most urgent first, and `uv run python scripts/platform_check.py` runs the checks and prints the evidence.
- Before delivery, every piece of text in the brief was checked to be present in these files. The few sentences that only make sense on the web page were restated, and `docs/README.md` explains how the folder maps to the brief.
- The execution prompt was written against the Claude Code documentation as it stood on 20 November 2026, summarised in [`docs/reference/claude-code-notes.md`](docs/reference/claude-code-notes.md). Stage 3 checked the orchestration prompt against the documentation of 23 November 2026; section 11.9 of that prompt lists where the documentation differs from the notes, and `docs/review/03-orchestration-cold-read.md` holds a fresh agent's cold read of it. The orchestration prompt has not been run.

## Layout

```text
submeter-pc-monitor/
├── README.md                     this file
├── AGENTS.md                     rules for every session, for any coding agent
├── CLAUDE.md                     imports AGENTS.md, plus notes for Claude Code
├── pyproject.toml                package, dependencies and tool settings
├── uv.lock                       the locked dependencies
├── .gitignore, .gitattributes    what git ignores, and one line-ending rule
├── .claude/
│   ├── settings.json             permission rules and settings for the build
│   └── agents/                   the build's seven agent definitions
├── prompts/
│   ├── README.md                 which prompt starts which session
│   ├── 01-execution-prompt.md    review, rulings, plan, orchestration prompt (run)
│   └── 02-orchestration-prompt.md  the build: a lead and a parallel swarm
├── docs/
│   ├── README.md                 index of the brief, and which file wins
│   ├── 01-overview.md … 17-build-prompt.md
│   ├── brief.html                the brief as a web page
│   ├── PLAN.md                   the formal plan
│   ├── STATUS.md                 where the build stands
│   ├── tasks/                    the task cards of phase P0
│   ├── review/                   the review, the rulings and their evidence
│   └── reference/
│       ├── windows-priorities.md   what to check first on Windows
│       └── claude-code-notes.md    what the build tooling does
├── scripts/
│   └── platform_check.py         checks the parts that depend on the operating system
├── examples/
│   ├── submeter.toml            sample settings
│   └── rules.toml                sample attribution rules
├── src/submeter/                the baseline: 16 modules in 7 packages
└── tests/                        62 tests in 10 files, including the layering rule
```

The first session added `uv.lock`, `docs/review/`, `docs/PLAN.md`, `docs/STATUS.md`, `docs/tasks/`, `prompts/02-orchestration-prompt.md` and `.claude/`.
