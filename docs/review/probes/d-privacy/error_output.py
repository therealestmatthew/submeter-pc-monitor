"""What do the installed Typer and Pydantic print when an error is not handled?

Run:  uv run python docs/review/probes/d-privacy/error_output.py

1. A Typer command crashes while a local variable holds a fake secret. Does the traceback on
   stderr show the value, with the library's default and with show_locals switched on?
2. A record that carries an unredacted command line fails validation. Does the message, which
   a collector would log, contain the command line?
Each Typer case runs in a child process, because the traceback is printed by its excepthook.
"""

from __future__ import annotations

import subprocess
import sys

import typer
from pydantic import ValidationError

from submeter.cli import app as baseline_app
from submeter.core.models import ProcessCounters, ProcessKey

SECRET = "FAKEsecret-9q"
CHILD = """
import typer
app = typer.Typer({options})
@app.command()
def crash() -> None:
    cmdline = ("tool", "--api-key", "{secret}")
    raise RuntimeError("provider failed")
app()
"""


def typer_case(label: str, options: str) -> None:
    code = CHILD.format(options=options, secret=SECRET)
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    shows = "shows" if SECRET in result.stderr else "does not show"
    locals_panel = "has" if "locals" in result.stderr else "has no"
    print(f"  {label}: stderr {shows} the local value and {locals_panel} locals panel")


def pydantic_case(label: str, **fields: object) -> None:
    key = ProcessKey(pid=1, started=1.0)
    try:
        ProcessCounters(key=key, cmdline=("tool", "--api-key", SECRET), **fields)  # type: ignore[arg-type]
    except ValidationError as error:
        text = str(error)
        inputs = repr([issue["input"] for issue in error.errors()])
        print(f"  {label}:")
        print(f"    str(error) contains the secret: {SECRET in text}")
        print(f"    error.errors() inputs contain the secret: {SECRET in inputs}")
        print(f"    last line: {text.splitlines()[-2].strip()[:110]}")


def main() -> None:
    print(f"typer {typer.__version__}")
    setting = baseline_app.pretty_exceptions_show_locals
    print(f"  the baseline app does not set it, so pretty_exceptions_show_locals = {setting}")
    typer_case("library default", "")
    typer_case("pretty_exceptions_show_locals=True", "pretty_exceptions_show_locals=True")
    print("pydantic, a ProcessCounters holding a raw command line")
    pydantic_case("a required field is missing (cpu_s)", memory_bytes=1)
    pydantic_case("a field has the wrong type", cpu_s="much", memory_bytes=1)
    pydantic_case("an unknown field is passed", cpu_s=1.0, memory_bytes=1, colour="blue")


if __name__ == "__main__":
    main()
