# Claude Code: what the build tooling does

These notes were checked against the Claude Code documentation at code.claude.com on 20 November 2026. The tool changes often, so treat them as leads: confirm each one against the documentation for the version you are running (`claude --version`) before relying on it. The pages used are listed at the end.

## Running on Windows

- Claude Code installs natively on Windows 10 1809 or later and on Windows 11, from PowerShell or CMD, without administrator rights. Run `claude --version` to confirm the install and `claude doctor` for a read-only diagnosis.
- Git for Windows is optional but recommended. With it, shell commands run through Git Bash. Without it, they run through the PowerShell tool.
- Sandboxed command execution is not available on native Windows. It needs WSL 2.

## Instruction files

- `CLAUDE.md` in the working directory, and in every directory above it, is loaded at the start of each session. A `CLAUDE.md` in a subdirectory loads when Claude first reads or edits a file there.
- `CLAUDE.md` can import other files with `@path`. Relative paths resolve from the file that contains the import, and imports nest to at most four levels. This package's `CLAUDE.md` imports `AGENTS.md` that way.
- `AGENTS.md` is read on its own only when no `CLAUDE.md` is present, and only from version 2.1.277. When both exist, only `CLAUDE.md` is read, which is why the import matters.
- Instruction files are context, not enforcement. Keep them short: a long file causes its rules to be missed. For something that must happen every time, use a hook.

## Subagents

- A subagent is a Markdown file with YAML frontmatter under `.claude/agents/`. Only `name` and `description` are required. The body is its system prompt.
- Other fields include `tools`, `disallowedTools`, `model`, `permissionMode`, `maxTurns`, `effort`, `skills`, `hooks`, `memory`, `background`, `omitClaudeMd` and `isolation`. Multi-word names are camelCase. An unrecognised field is ignored without an error, and from version 2.1.296 `claude --debug` logs the ones it ignored.
- The main session starts a subagent with the Agent tool, which was called Task before version 2.1.63.
- A subagent begins with a fresh context: its own system prompt, the task message the main session wrote, the `CLAUDE.md` hierarchy and a snapshot of git status. It does not see the conversation that started it. The built-in Explore and Plan subagents skip `CLAUDE.md`.
- Several subagents can run at once. The default limit is 20 running at a time, set by `CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`. Subagents can start their own, three levels deep by default.
- When a subagent finishes, the main session receives its agent ID and can continue it with the SendMessage tool, with its history intact.

## Working copies for parallel builders

- `isolation: worktree` in a subagent's frontmatter gives it its own git worktree, a separate checkout on its own branch under `.claude/worktrees/`. Keep that folder in `.gitignore`.
- By default a new worktree branches from the repository's default branch on the remote, not from the local `HEAD`. Setting `worktree.baseRef` to `"head"` in settings makes it branch from the current local commit. With no remote configured it falls back to the local `HEAD`. A builder that must see the wave's latest merged work depends on this.
- A worktree is a fresh checkout of tracked files only. The virtual environment is not there, so each one needs its own `uv sync`. A `.worktreeinclude` file can copy chosen ignored files into each new worktree.
- A subagent's worktree is removed when it finishes without changes. One with changes stays on disk. A periodic sweep removes old worktrees only once they hold no uncommitted or unpushed work, so the lead should merge each branch and then remove its worktree with `git worktree remove`.
- While isolated, edits and commands aimed at the main checkout are blocked. For PowerShell commands only the working-directory check applies.
- An isolated subagent takes its instruction files from the main conversation, not from its own worktree.

## Other ways to run several agents

- **Agent teams** are experimental and off by default, enabled with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`. A lead and its teammates share a task list and message each other. Teammates are not isolated in worktrees, so the work has to be split by file. Teammates are not restored when a session is resumed, a session has one team, and teams do not nest. Split panes are not supported in Windows Terminal, though the default in-process display works anywhere.
- **`/batch`** is a bundled skill that splits one large change across 5 to 30 subagents, each in its own worktree.
- **Agent view**, opened with `claude agents`, dispatches and monitors background sessions. It is a research preview.
- **Dynamic workflows** are scripts that run many subagents and check their results against each other.
- Every parallel approach multiplies token use.

## Permission modes

- The modes are `default` (shown as Manual), `acceptEdits`, `plan`, `auto`, `dontAsk` and `bypassPermissions`. Choose one at start with `--permission-mode`, or cycle with Shift+Tab.
- Plan mode reads and explores but does not edit source files until the plan is approved.
- In auto mode a classifier reviews actions in place of a prompt. It is the starting mode for interactive sessions from version 2.1.283. The documentation is plain that it does not guarantee safety.

## Practices the documentation recommends

- Give the session a check it can run, and ask for the evidence: the command and what it printed.
- Explore, then plan, then build. Start a fresh session to carry out a written plan.
- Have a fresh subagent review a change, since it sees the result and not the reasoning behind it. Tell it to report only gaps in correctness or requirements, because a reviewer asked for problems will always find some.
- Keep context for judgment. Use subagents for bulk reading, and clear the conversation between unrelated tasks.

## Pages used

- [Advanced setup](https://code.claude.com/docs/en/setup.md)
- [How Claude remembers your project](https://code.claude.com/docs/en/memory.md)
- [Create custom subagents](https://code.claude.com/docs/en/sub-agents.md)
- [Run parallel sessions with worktrees](https://code.claude.com/docs/en/worktrees.md)
- [Run agents in parallel](https://code.claude.com/docs/en/agents.md)
- [Orchestrate teams of Claude Code sessions](https://code.claude.com/docs/en/agent-teams)
- [Permission modes](https://code.claude.com/docs/en/permission-modes.md)
- [Best practices for Claude Code](https://code.claude.com/docs/en/best-practices.md)
