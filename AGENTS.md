# Submeter: rules for every session

Submeter is a local performance monitor for one machine: a collector, a server and a command line that attribute CPU, memory and I/O to named workloads. Windows 11 is the first target, and Linux must work from the same code.

## Fixed rules

These three are not open to change. A design or a change that breaks one is wrong, however useful it looks.

1. **Observe only.** Version 1 never changes a process: no priority, affinity, suspend, kill or memory cap, and no setting that enables one.
2. **No administrator rights.** Every program runs as the signed-in user and never asks to elevate.
3. **Nothing leaves the machine.** No upload, webhook, telemetry or update check. The API listens on loopback only.

## Where things are

- `docs/README.md` indexes the design brief, one file per topic. Read the file for the topic in hand, not all of them.
- `docs/review/02-rulings.md`, once it exists, records my decisions. `docs/PLAN.md` and `docs/STATUS.md`, once they exist, say what is being built and where it stands.
- `prompts/` holds the prompt that starts each kind of session.
- `src/submeter/` is the package and `tests/` its tests. `docs/14-baseline-modules.md` describes each module.
- `scripts/platform_check.py` checks the parts that depend on the operating system. `docs/reference/windows-priorities.md` says what is still unproven on Windows.

## Checks

Run these before saying a change is done, and show what they printed.

```
uv sync
uv run ruff check
uv run ruff format --check
uv run mypy src tests
uv run mypy --platform win32 src tests
uv run mypy --platform linux src tests
uv run pytest
```

To run one test: `uv run pytest tests/test_<component>.py -k NAME`, where `<component>` names the component's test file (`docs/17-build-prompt.md:43`).

## Rules that are easy to break

- Imports point only downward: `core`, then `privacy` and `providers`, then `store`, `collector`, `attribution` and `analysis`, then `cli`. `tests/test_layers.py` fails otherwise. Add a new package to its `LAYER` table.
- Records passed between layers are frozen Pydantic models that refuse unknown fields. Subclass `Record` in `core/models.py`.
- A process is identified by pid plus start time (`ProcessKey`), never by pid alone.
- Providers return cumulative counters, never rates. Only the sampler turns counters into deltas.
- A command line is redacted before it is stored, logged or written into a test fixture.
- A recorded fixture is anonymised before it is written: user name, host name and home folder replaced; executable names outside an allow-list replaced with stable placeholders; command lines in exe_only form; working folders dropped. A test fails if any fixture contains the current user or host name.
- A setting outside its range is refused with the range in the message. It is never clamped.
- Each data file has one writer: the collector writes raw files, the server writes the history file and its backups, and the launcher writes one file per run.
- A metric the system cannot deliver is reported as unavailable, never as zero and never as an estimate.
- A change in behaviour starts with a failing test.
- No new dependency without my approval. There are three at runtime: pydantic, psutil and typer.
- Code must pass on Windows and on Linux. Say which one you ran it on.

## When the brief and the code disagree

Say so and ask. Do not pick one quietly. The brief is the specification, `docs/16-review-log.md` records why it says what it says, and my rulings override both.
