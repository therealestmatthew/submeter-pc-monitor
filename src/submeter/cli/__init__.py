"""The command line: a thin layer that wires the other modules together.

No logic lives here. Each command builds what it needs from the modules below
it, calls them, and prints the result as a table or, with --json, as JSON with
a stable shape. This baseline has five commands. The rest of the list in the
brief (why, cost, diff, session, report, export, run, daemon) is added as the
components behind them are built.

Each command group is one module of this package. This file builds `app` and
calls `register(app)` on every module whose name does not start with an
underscore, in sorted order, so a new command is a new module and edits no
shared file (plan choice C8). Modules starting with an underscore hold what
several commands share.
"""

from __future__ import annotations

import importlib
import pkgutil

import typer

app = typer.Typer(
    no_args_is_help=True, add_completion=False, help="Submeter: what each workload costs."
)


def _register_all(target: typer.Typer) -> None:
    names = sorted(found.name for found in pkgutil.iter_modules(__path__))
    for name in names:
        if name.startswith("_"):
            continue
        module = importlib.import_module(f"{__name__}.{name}")
        register = getattr(module, "register", None)
        if not callable(register):
            raise ImportError(
                f"{module.__name__} defines no register(app): every module of {__name__}"
                " whose name does not start with an underscore must add its commands with one",
                name=module.__name__,
            )
        register(target)


_register_all(app)
