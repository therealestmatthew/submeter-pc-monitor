"""Do the baseline's own commands open a network socket, or import anything that could?

Run:  uv run python docs/review/probes/d-privacy/no_network.py

Fixed rule 3 says nothing leaves the machine. The probe swaps socket.socket for a subclass
that counts, runs the five baseline commands in this process with SUBMETER_HOME pointing at
a temporary folder, and prints how many sockets were created. It then lists every import in
src/submeter that names a module able to open a connection or start a program.
"""

from __future__ import annotations

import ast
import os
import socket
import tempfile
from pathlib import Path

from typer.testing import CliRunner

ROOT = Path(__file__).resolve().parents[4]
WATCHED = {"socket", "ssl", "http", "urllib", "ftplib", "smtplib", "asyncio", "webbrowser"}
WATCHED |= {"subprocess", "requests", "httpx", "aiohttp", "websockets", "xmlrpc"}
COMMANDS = [
    ["doctor", "--json"],
    ["top", "--seconds", "0.3", "--json"],
    ["config", "show"],
    ["config", "check", str(ROOT / "examples" / "submeter.toml")],
    ["store", "status", "--json"],
]
created: list[int] = []


class Counting(socket.socket):
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        created.append(self.family)


def main() -> None:
    socket.socket = Counting  # type: ignore[misc]
    socket.socket().close()
    print(f"self-check, one socket made on purpose is counted: {len(created) == 1}")
    from submeter.cli import app

    with tempfile.TemporaryDirectory() as name:
        os.environ["SUBMETER_HOME"] = name
        for command in COMMANDS:
            before = len(created)
            result = CliRunner().invoke(app, command)
            opened = len(created) - before
            print(f"submeter {' '.join(command[:2])}: exit {result.exit_code}, sockets {opened}")
    found = []
    for path in sorted((ROOT / "src" / "submeter").rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = [alias.name for alias in getattr(node, "names", [])]
            module = getattr(node, "module", None) if isinstance(node, ast.ImportFrom) else None
            for name in [module] if module else names if isinstance(node, ast.Import) else []:
                if name.split(".")[0] in WATCHED:
                    found.append(f"{path.relative_to(ROOT)} imports {name}")
    print(f"imports of network or process-starting modules in src/submeter: {found or 'none'}")


if __name__ == "__main__":
    main()
