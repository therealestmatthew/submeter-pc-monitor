# Prompts

One prompt starts each kind of session. Start a session in the repository root and say: "Read prompts/NAME and follow it."

The execution prompt has been run, and the build starts from the orchestration prompt. Start Claude Code interactively in the repository root, without `--effort ultracode`, accept the workspace trust dialog if asked, and send "Read prompts/02-orchestration-prompt.md and follow it." (section 13 of that prompt).

| File | Starts | Written by | State |
| --- | --- | --- | --- |
| `01-execution-prompt.md` | The first session: an adversarial review, a stop for rulings, a formal plan, then the orchestration prompt | Part of the package | Run from 20 to 23 November 2026. It wrote `docs/review/01-adversarial-review.md`, recorded the owner's rulings in `docs/review/02-rulings.md` and applied them, and wrote `docs/PLAN.md` and the orchestration prompt |
| `02-orchestration-prompt.md` | The build: a lead session and a parallel swarm of builders and reviewers | The first session, at its stage 3, committed on 23 November 2026 | Not yet run. The build starts here; `docs/STATUS.md` says where the build stands |

`docs/17-build-prompt.md` is a third prompt, kept as the specification in compact form. It can start a single-session build on its own, but in this repository `docs/PLAN.md` and the orchestration prompt replace its working instructions.
