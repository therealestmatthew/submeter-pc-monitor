# Submeter starter package

Everything needed to start building Submeter, a local performance monitor that attributes CPU, memory and I/O to named workloads. This folder is laid out as the repository itself: unpack it, start a session in it, and hand over one prompt.

## How to start

The build starts from this package and one prompt. The package holds the brief as one file per section, the baseline modules in place, the standing rules and the execution prompt. That prompt has a Claude Code session review the brief and the baseline, stop for your rulings, write a formal plan, and then write the orchestration prompt that a second session uses to build Submeter with a parallel swarm of agents. Nothing is built until you have ruled on the review.

## The two sessions

**FIRST SESSION · prompts/01-execution-prompt.md**

1. **Ground:** check the package · commit it · run the checks
2. **Stage 1 · Adversarial review:** eight lenses · verified on this machine · changes nothing
3. **Stop 1 · Your rulings:** fix now · plan · reject · defer
4. **Apply the rulings:** documents made true · small fixes, test first
5. **Stage 2 · Formal plan:** tasks · file ownership · waves · gates
6. **Stage 3 · Orchestration prompt:** roles · task cards · wave loop · cold read
7. **Stop 2 · Your review:** the plan and the prompt, before anything is built

**SECOND SESSION · prompts/02-orchestration-prompt.md**, a file the first session writes

8. **Build · Parallel swarm:** a lead, with paired builders and reviewers · you approve gates

*Figure:* The first session writes documents and small approved fixes, and stops twice. The build is a second session, started with the prompt the first one wrote.

## What is fixed and what is open

- Fixed: observe only, no administrator rights, and nothing leaves the machine. The review checks that the design obeys these three and may not reopen them.
- Open: everything else, including the three jobs, the interface, the extra telemetry, Python, the phase order, the 25 components and the baseline code. A finding that argues for a cut needs evidence and a cheaper alternative.

## How the review is held to account

- It changes nothing. New files appear only under `docs/review/`, and `git status` proves it.
- Every finding is marked verified or suspected. Verified means a command and its output, a file and line, or a link to the vendor's documentation.
- It tries to refute each finding before keeping it, and reports nothing about style.
- It covers eight lenses: true on this machine, measurement, storage and time, privacy and local security, the baseline code, consistency, buildability and scope.
- Findings continue the numbering in the review log, from R38. Each carries a recommended ruling: fix now, plan, reject or defer.

## The build style it writes for

- A lead session coordinates and writes no product code.
- Every producer has a separate checker that starts with fresh context and cannot write.
- No file has two writers in one wave.
- Every task starts from a failing test.
- At most two review rounds for a task, then it escalates.
- Merges inside a wave are automatic. A phase gate waits for you.
- All state is in files, so the build can stop and resume.
- Roles and task cards are plain Markdown that another agent runner could follow.

## What is in the package

| Path | What it is |
| --- | --- |
| `README.md` | What the package is and how to start it |
| `AGENTS.md, CLAUDE.md` | The rules for every session: the three fixed rules, the checks to run, and the conventions that are easy to break. CLAUDE.md imports AGENTS.md, so other coding agents read the same rules |
| `prompts/01-execution-prompt.md` | The execution prompt |
| `docs/` | The brief, one file per section, with every chart and the dashboard mock written out as tables and text. Also the page itself as brief.html, notes on Claude Code checked against its documentation, and a list of what to check first on Windows |
| `scripts/platform_check.py` | One command that checks the parts that depend on the operating system and prints the evidence |
| `src/submeter/, tests/, pyproject.toml` | The baseline modules and their tests, already in place |
| `examples/` | The sample submeter.toml and rules.toml |

## Starting it on Windows

You need Git, uv and Claude Code installed. The commands are under [Installing the tools](#installing-the-tools). Unpack the zip, open PowerShell in the folder that holds it, and hand the session the prompt by name.

```text
PS> Expand-Archive submeter-pc-monitor.zip -DestinationPath .
PS> cd submeter-pc-monitor
PS> claude

> Read prompts/01-execution-prompt.md and follow it.

  ... it reviews, writes docs/review/01-adversarial-review.md, and stops ...

> accept all recommendations

  ... it applies your rulings, writes docs/PLAN.md and
      prompts/02-orchestration-prompt.md, and stops ...
```

At the first stop you can also rule on findings one at a time, for example "R38 fix now, R41 reject, the rest as recommended". When the first session has finished, start a new one and give it `prompts/02-orchestration-prompt.md` the same way.

## The execution prompt

2,742 words. It is the file `prompts/01-execution-prompt.md` in the package, and it expects the rest of the package to be there.

Open [`prompts/01-execution-prompt.md`](prompts/01-execution-prompt.md) to read it.

## Installing the tools

Three tools need to be on the Windows computer.

- **Git.** [Git for Windows](https://git-scm.com/downloads/win) also gives Claude Code a Bash shell to work in.
- **uv.** In PowerShell: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`, or `winget install --id=astral-sh.uv -e`. It fetches a suitable Python by itself.
- **Claude Code.** In PowerShell: `irm https://claude.ai/install.ps1 | iex`. Then `claude --version` confirms it, and `claude doctor` reports on the install.

The first session makes this folder a git repository and commits it as delivered, so that it can prove its review changed nothing. You can do that yourself first if you prefer: `git init -b main`, `git add -A`, `git commit -m "Package as delivered"`.

## The GitHub repository

The project lives at <https://github.com/therealestmatthew/submeter-pc-monitor>. The first session adds it as `origin`, confirms it can reach it and pushes, and sessions push freely after that. To connect it yourself: `git remote add origin https://github.com/therealestmatthew/submeter-pc-monitor.git`, then `git push -u origin main`. The push is simplest if the GitHub repository starts empty.

There is no license file yet, so all rights stay with the owner until one is added.

## What has and has not been checked

- The code was unpacked from this package into an empty folder on Linux, where `uv sync`, Ruff, mypy in strict mode and all 20 tests passed. mypy was also run as if on Windows.
- Nothing here has run on Windows. The first job of the first session is to find out what that changes. [`docs/reference/windows-priorities.md`](docs/reference/windows-priorities.md) lists what to check, most urgent first, and `uv run python scripts/platform_check.py` runs the checks and prints the evidence.
- Every piece of text in the brief was checked to be present in these files. The few sentences that only make sense on the web page were restated, and `docs/README.md` explains how the folder maps to the brief.
- The execution prompt has not been run. It was written against the Claude Code documentation as it stood on 20 November 2026, summarised in [`docs/reference/claude-code-notes.md`](docs/reference/claude-code-notes.md). If the tool has moved on, the prompt tells the session to trust the current documentation.

## Layout

```text
submeter-pc-monitor/
├── README.md                     this file
├── AGENTS.md                     rules for every session, for any coding agent
├── CLAUDE.md                     imports AGENTS.md, plus notes for Claude Code
├── pyproject.toml                package, dependencies and tool settings
├── .gitignore, .gitattributes    what git ignores, and one line-ending rule
├── prompts/
│   ├── README.md                 which prompt starts which session
│   └── 01-execution-prompt.md    review, rulings, plan, orchestration prompt
├── docs/
│   ├── README.md                 index of the brief, and which file wins
│   ├── 01-overview.md … 17-build-prompt.md
│   ├── brief.html                the brief as a web page
│   └── reference/
│       ├── windows-priorities.md   what to check first on Windows
│       └── claude-code-notes.md    what the build tooling does
├── scripts/
│   └── platform_check.py         checks the parts that depend on the operating system
├── examples/
│   ├── submeter.toml            sample settings
│   └── rules.toml                sample attribution rules
├── src/submeter/                the baseline: 15 modules in 7 packages
└── tests/                        20 tests, including the layering rule
```

The first session adds `uv.lock`, `docs/review/`, `docs/PLAN.md`, `docs/STATUS.md`, `docs/tasks/`, `prompts/02-orchestration-prompt.md` and `.claude/agents/`.
