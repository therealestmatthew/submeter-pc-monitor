@AGENTS.md

# Claude Code

## The repository

This project lives at https://github.com/therealestmatthew/submeter-pc-monitor. That is its only remote, and it is named `origin`.

- At the start of a session, confirm the connection: `git remote -v` shows that address, and `git ls-remote origin` answers. If `origin` is missing, add it. If it points anywhere else, stop and ask me.
- Push freely. Commit in small steps, push your branch as you go, and push `main` when its checks pass. No push here waits for my approval.
- Do not rewrite history that is already on GitHub. Parallel builders branch from it, so fix forward with a new commit.
- Push nowhere else, and upload no part of this repository to any other service.

## Working in this repository

- The rules above the heading come from `AGENTS.md`, so that other coding agents read the same ones. Change them there, not here.
- A subagent starts without this conversation. Give it the files to read, the files it may change, and the check that proves it is done.
- A new working copy for a parallel builder can start from the default branch on `origin`, not from your local commit. Push before you start a wave of builders, or set the base explicitly.
- Each working copy is a fresh checkout and needs its own `uv sync`.
- When context is compacted, keep the list of files changed, the checks run with their results, and the stage reached in whichever prompt under `prompts/` started the session.
