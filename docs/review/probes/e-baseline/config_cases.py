"""Probe: settings that the baseline accepts, misreads or crashes on.

Writes only to a temporary folder, which it removes. Run from the repository root:

    uv run python docs/review/probes/e-baseline/config_cases.py

Each line shows one settings file, or one value, and what load_settings or core.units did.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from submeter.core.config import ConfigError, load_settings
from submeter.core.units import parse_rate

MB = 1024**2


def outcome(path: Path | None, **options: object) -> str:
    try:
        loaded = load_settings(path, **options)  # type: ignore[arg-type]
    except ConfigError as error:
        return f"refused: {'; '.join(error.problems)[:150]}"
    except Exception as error:
        return f"CRASH {type(error).__name__}: {str(error)[:110]}"
    return f"accepted ({len(loaded.sources)} keys set)"


def write(folder: Path, name: str, text: str | bytes) -> Path:
    path = folder / name
    if isinstance(text, bytes):
        path.write_bytes(text)
    else:
        path.write_text(text, encoding="utf-8")
    return path


def rates() -> None:
    print("1. parse_rate, in MB per hour (the rule: write it like '50MB/h')")
    for text in ("50MB/h", "50MB/2h", "100MB/2h", "1GB/24h", "1GB/d", "50MB/30m"):
        try:
            print(f"   {text!r} -> {parse_rate(text) * 3600 / MB:.2f} MB/h")
        except ValueError as error:
            print(f"   {text!r} -> refused: {error}")


def profiles(folder: Path) -> None:
    print("2. Profiles")
    bad = write(
        folder,
        "profile.toml",
        '[sampling]\nactive_interval = "1s"\n'
        '[profile.laptop]\nsampling.active_interval = "20s"\nsampling.colour = "blue"\n',
    )
    print(f"   bad values in a profile, no profile selected: {outcome(bad)}")
    print(f"   the same file, profile selected: {outcome(bad, profile='laptop')}")
    scalar = write(folder, "scalar.toml", "profile = 5\n")
    print(f"   profile = 5, no profile selected: {outcome(scalar)}")
    print(f"   profile = 5, profile selected: {outcome(scalar, profile='laptop')}")
    notable = write(folder, "notable.toml", "[profile]\nlaptop = 5\n")
    print(f"   profile.laptop = 5, profile selected: {outcome(notable, profile='laptop')}")
    env = {"SUBMETER_PROFILE": "laptop"}
    print(f"   SUBMETER_PROFILE=laptop in the environment: {outcome(bad, env=env)}")


def alert_rules(folder: Path) -> None:
    print("3. Alert rules and free-form tables")
    rule = '[[alerts.rules]]\nname = "x"\nmetric = "{metric}"\nworkload = "{workload}"\nabove = 1\n'
    for metric, workload in (
        ("cpu_cores", "agent:*"),
        ("cpu_coress", "agent:*"),
        ("commit_fraction", "browser"),
        ("overhead_fraction", "machine"),
    ):
        path = write(folder, "alert.toml", rule.format(metric=metric, workload=workload))
        print(f"   metric {metric!r} on workload {workload!r}: {outcome(path)}")
    thresholds = write(folder, "verdict.toml", "[verdict.thresholds]\ncpu_tyme = 0.85\n")
    print(f"   verdict.thresholds.cpu_tyme = 0.85: {outcome(thresholds)}")


def numbers(folder: Path) -> None:
    print("4. Bare, negative and not-a-number values")
    for text in (
        "[sampling]\nactive_interval = -1",
        "[sampling]\nactive_interval = nan",
        "[storage.retention]\nraw = -5",
        "[storage.retention]\nraw = nan",
        "[storage]\ndisk_budget = -1",
        "[analysis.leak]\nmin_slope = -1",
        "[analysis.leak]\nmin_duration = nan",
        "[alerts]\ncooldown = -60",
        "[attribution]\nunattributed_alert = 10",
        '[attribution]\nunattributed_alert = "250%"',
        "[sampling]\nhot_cpu_threshold = 0.5",
        "[api]\nport = 80",
    ):
        path = write(folder, "number.toml", text + "\n")
        print(f"   {text.replace(chr(10), ' ')}: {outcome(path)}")


def files(folder: Path) -> None:
    print("5. Settings files a Windows computer produces, and paths that are not files")
    body = '[sampling]\nactive_interval = "2s"\n'
    print(f"   a path that does not exist: {outcome(folder / 'missing.toml')}")
    print(f"   a folder: {outcome(folder)}")
    bom = write(folder, "bom.toml", b"\xef\xbb\xbf" + body.encode())
    print(f"   UTF-8 with a byte-order mark: {outcome(bom)}")
    utf16 = write(folder, "utf16.toml", body.encode("utf-16"))
    print(f"   UTF-16 (Windows PowerShell 5.1 redirection): {outcome(utf16)}")
    crlf = write(folder, "crlf.toml", body.replace("\n", "\r\n").encode())
    print(f"   CRLF line endings: {outcome(crlf)}")


def main() -> None:
    rates()
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as name:
        folder = Path(name)
        profiles(folder)
        alert_rules(folder)
        numbers(folder)
        files(folder)


if __name__ == "__main__":
    main()
