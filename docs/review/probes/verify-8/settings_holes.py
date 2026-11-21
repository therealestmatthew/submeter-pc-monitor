"""Verify-8, cluster B4: settings the baseline accepts that docs/08 or AGENTS.md say it refuses.

Writes only to a temporary folder, which it removes. Run from the repository root:

    uv run python docs/review/probes/verify-8/settings_holes.py

Checks: an alert metric outside the docs/08 list, a metric on the wrong workload, a misspelt
verdict threshold, negative and NaN retention and what FileMap.expired_raw then lists, and what
the CLI does with a settings file that does not exist.
"""

from __future__ import annotations

import tempfile
from datetime import UTC, date, datetime
from pathlib import Path

from typer.testing import CliRunner

from submeter.cli import app
from submeter.core.config import ConfigError, load_settings
from submeter.store.files import FileMap


def load(folder: Path, text: str) -> str:
    path = folder / "submeter.toml"
    path.write_text(text, encoding="utf-8")
    try:
        loaded = load_settings(path)
    except ConfigError as error:
        return f"refused: {error.problems[0][:90]}"
    except Exception as error:
        return f"CRASH {type(error).__name__}"
    return f"accepted ({len(loaded.sources)} keys set)"


RULE = '[[alerts.rules]]\nname = "x"\nworkload = "{w}"\nmetric = "{m}"\nabove = 1\n'


def main() -> None:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as name:
        folder = Path(name)
        print("1. alert rules (docs/08:130: any other metric 'is refused when settings load')")
        for workload, metric in [
            ("agent:*", "cpu_cores"),
            ("agent:*", "cpu_coress"),
            ("browser", "commit_fraction"),
        ]:
            print(
                f"   {metric!r} on {workload!r}: {load(folder, RULE.format(w=workload, m=metric))}"
            )
        print("2. verdict threshold with a misspelt name (docs/14:173 'Unknown keys are errors')")
        print(f"   cpu_tyme = 0.85: {load(folder, '[verdict.thresholds]\ncpu_tyme = 0.85\n')}")
        print("3. retention values and what expired_raw lists at 00:00:10 UTC")
        home = folder / "home"
        files = FileMap.discover(env={"SUBMETER_HOME": str(home)})
        files.ensure()
        yesterday, today = date(2026, 11, 20), date(2026, 11, 21)
        for day in (yesterday, today):
            files.raw_file(day).touch()
        now = datetime(2026, 11, 21, 0, 0, 10, tzinfo=UTC).timestamp()
        for value in ("48h", "-5", "nan", "0"):
            text = f"[storage.retention]\nraw = {value if value != '48h' else repr(value)}\n"
            verdict = load(folder, text)
            listed = "-"
            if verdict.startswith("accepted"):
                raw = load_settings(folder / "submeter.toml").settings.storage.retention.raw
                listed = str([p.name for p in files.expired_raw(now, raw)])
            print(f"   raw = {value}: {verdict}; expired_raw -> {listed}")
        print("4. the CLI with a settings file that does not exist")
        missing = str(folder / "missing.toml")
        runner = CliRunner()
        for args in (["config", "check", missing], ["config", "show", "--file", missing]):
            result = runner.invoke(app, args)
            kind = type(result.exception).__name__ if result.exception else "none"
            print(f"   {' '.join(args[:2])} MISSING: exit {result.exit_code}, exception {kind}")


if __name__ == "__main__":
    main()
