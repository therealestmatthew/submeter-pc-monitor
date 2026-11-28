"""The step-1 helper scripts of P0 (P0-W1-T2): the CPU time check, the Restricted share and the
name replacement. Each script is loaded by path, because scripts/ is not a package.

Every input here is inline and made up for the test, in the shape its source documents; none
was read from a real machine (docs/PLAN.md 7.3.1).
"""

from __future__ import annotations

import functools
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

PROBES = Path(__file__).resolve().parents[1] / "scripts" / "probes"


@functools.cache
def load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"step1_{name}", PROBES / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses look their module up here
    spec.loader.exec_module(module)
    return module


# --- cpu_time_check.py -----------------------------------------------------------------------


def core(user: float, system: float, idle: float, interrupt: float, dpc: float) -> dict[str, float]:
    """One core's reading, with the fields psutil.cpu_times(percpu=True) has on Windows."""
    return {"user": user, "system": system, "idle": idle, "interrupt": interrupt, "dpc": dpc}


def repetition(
    per_core: list[tuple[float, float, float, float, float]],
) -> list[tuple[float, float]]:
    """The ratios of one 10 s repetition, from a zero reading and the given per-core increases."""
    check = load("cpu_time_check")
    before = [core(0.0, 0.0, 0.0, 0.0, 0.0) for _ in per_core]
    after = [core(*fields) for fields in per_core]
    ratios: list[tuple[float, float]] = check.ratios(before, after, 10.0)
    return ratios


def test_ratios_per_core_from_two_readings() -> None:
    # Made up in the shape of psutil.cpu_times(percpu=True) on Windows: cumulative seconds per
    # core, read twice 10.0 s apart (time.perf_counter()).
    check = load("cpu_time_check")
    before = [core(100.0, 50.0, 850.0, 2.0, 1.0), core(200.0, 80.0, 720.0, 4.0, 3.0)]
    after = [core(102.0, 51.0, 857.0, 2.2, 1.1), core(203.0, 81.5, 725.2, 4.25, 3.05)]
    # Core 0: (2 + 1 + 7) / 10 = 1.00 and (2 + 1 + 7 + 0.2 + 0.1) / 10 = 1.03.
    # Core 1: (3 + 1.5 + 5.2) / 10 = 0.97 and (3 + 1.5 + 5.2 + 0.25 + 0.05) / 10 = 1.00.
    found = check.ratios(before, after, 10.0)
    assert len(found) == 2
    assert found[0] == pytest.approx((1.00, 1.03))
    assert found[1] == pytest.approx((0.97, 1.00))


def test_decision_subtracts_interrupt_and_dpc_when_r1_holds() -> None:
    # User + system + idle equals the 10 s elapsed on every core; interrupt + DPC add 0.3 s (3%).
    check = load("cpu_time_check")
    one = repetition([(2.0, 1.0, 7.0, 0.2, 0.1), (4.0, 2.0, 4.0, 0.25, 0.05)])
    decision, _reason = check.decide([one, one, one])
    assert decision == check.SUBTRACT == "subtract interrupt and DPC"


def test_decision_keeps_the_busy_sum_when_r2_holds() -> None:
    # r1 = 9.7 / 10 = 0.97 and r2 = (9.7 + 0.2 + 0.1) / 10 = 1.00 on every core.
    check = load("cpu_time_check")
    one = repetition([(2.0, 1.0, 6.7, 0.2, 0.1), (4.0, 2.0, 3.7, 0.25, 0.05)])
    decision, _reason = check.decide([one, one, one])
    assert decision == check.KEEP == "keep the busy sum"


def test_decision_asks_when_neither_ratio_holds() -> None:
    # Core 1 has r1 = 9.5 / 10 = 0.95 and r2 = 9.7 / 10 = 0.97; core 0 alone would say subtract.
    check = load("cpu_time_check")
    one = repetition([(2.0, 1.0, 7.0, 0.2, 0.1), (4.0, 2.0, 3.5, 0.1, 0.1)])
    decision, reason = check.decide([one, one, one])
    assert decision == check.ASK == "ask"
    assert reason


def test_decision_asks_when_both_ratios_hold() -> None:
    # Interrupt + DPC are 0.04 s of 10 s (0.4%): r1 = 0.998 and r2 = 1.002, both within 0.01.
    # CQ-02, answered by the owner on 2026-11-25: "ask", so the owner decides B4.
    check = load("cpu_time_check")
    one = repetition([(2.0, 1.0, 6.98, 0.03, 0.01), (4.0, 2.0, 3.98, 0.02, 0.02)])
    decision, reason = check.decide([one, one, one])
    assert decision == check.ASK
    assert "interrupt plus DPC under 1% of elapsed" in reason
    assert "cannot tell" in reason


# --- restricted_share.py ---------------------------------------------------------------------


def top_row(workload: str, cpu_s: float, processes: int) -> dict[str, object]:
    """One row of `submeter top --json` at the base commit (a WorkloadSample dump, cli.py:100)."""
    return {
        "taken_at": 1795864059.8,
        "interval_s": 2.0,
        "workload": workload,
        "source": "polled",
        "cpu_s": cpu_s,
        "memory_bytes": 1_000_000,
        "io_read_bytes": 0,
        "io_write_bytes": 0,
        "processes": processes,
        "started": 0,
    }


# Made up in the shape `submeter top --seconds 2 --json` prints without a rules file: the
# Restricted row holds 2.0 of 8.0 CPU-s and 14 processes (14 is docs/03-cli-output.md's figure).
TOP_LIST = [
    top_row("unattributed", 5.5, 190),
    top_row("submeter", 0.5, 1),
    top_row("restricted", 2.0, 14),
]


def test_restricted_share_of_a_top_list() -> None:
    share = load("restricted_share")
    found = share.restricted_share(TOP_LIST)
    assert found.share == pytest.approx(0.25)
    assert found.processes == 14
    assert found.found
    assert "0.25" in share.describe(found)


def test_restricted_share_without_a_restricted_row() -> None:
    # The same list without its restricted row: every process could be read.
    share = load("restricted_share")
    found = share.restricted_share(TOP_LIST[:2])
    assert found.share == 0
    assert found.processes == 0
    assert not found.found
    assert "no restricted row" in share.describe(found)


def test_restricted_share_reads_a_saved_file(tmp_path: Path) -> None:
    # Saved as P0-O1 saves every output: the command, the output, then the exit code, written
    # by Out-File -Encoding utf8, which in Windows PowerShell 5.1 starts with a byte-order mark.
    share = load("restricted_share")
    saved = tmp_path / "top-norules.json"
    text = f"$ uv run submeter top --seconds 2 --json\r\n{json.dumps(TOP_LIST)}\r\nexit=0\r\n"
    saved.write_bytes(text.encode("utf-8-sig"))
    from_file = share.restricted_share(share.read_saved(saved))
    from_list = share.restricted_share(TOP_LIST)
    assert from_file == from_list
    bare = tmp_path / "bare.json"
    bare.write_text(json.dumps(TOP_LIST), encoding="utf-8")
    assert share.restricted_share(share.read_saved(bare)) == from_list


# --- replace_names.py ------------------------------------------------------------------------

# Planted names, made up for these tests. None is the name of a real user, host or domain.
PLANTED = {
    "users": ["zelda"],
    "hosts": ["bluefin-lab.corp.example", "bluefin-lab"],
    "domains": ["ACMECORP"],
    "homes": ["C:\\Users\\zelda"],
}


def test_replace_names_in_utf8_and_utf16_files(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    names = load("replace_names")
    text = (
        "whoami: acmecorp\\ZELDA on Bluefin-Lab\r\n"
        "folder C:\\USERS\\Zelda\\AppData\\Local\\Submeter\\data owned by Zelda\r\n"
        "host BLUEFIN-LAB.corp.example in AcmeCorp\r\n"
    )
    expected = (
        "whoami: <domain>\\<user> on <host>\r\n"
        "folder <home>\\AppData\\Local\\Submeter\\data owned by <user>\r\n"
        "host <host> in <domain>\r\n"
    )
    folder = tmp_path / "step1"
    (folder / "nested").mkdir(parents=True)
    plain, with_bom, wide = folder / "plain.txt", folder / "bom.txt", folder / "nested" / "wide.txt"
    plain.write_bytes(text.encode("utf-8"))
    with_bom.write_bytes(text.encode("utf-8-sig"))  # Out-File -Encoding utf8 in PowerShell 5.1
    wide.write_bytes(b"\xff\xfe" + text.encode("utf-16-le"))  # a bare > in PowerShell 5.1

    code = names.run(folder, **PLANTED)

    assert code == 0
    assert plain.read_bytes() == expected.encode("utf-8")
    assert with_bom.read_bytes() == expected.encode("utf-8-sig")
    assert wide.read_bytes() == b"\xff\xfe" + expected.encode("utf-16-le")
    printed = capsys.readouterr().out
    assert printed.count("plain.txt") == 1 and "wide.txt" in printed
    assert not any(name in printed.lower() for name in ("zelda", "bluefin", "acmecorp"))


def test_replace_names_keeps_a_longer_word(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    names = load("replace_names")
    note = tmp_path / "note.txt"
    note.write_text("annual report by Ann (ann_x, ann2, joanne, ann-marie)\n", encoding="utf-8")
    code = names.run(tmp_path, users=["ann"], hosts=[], domains=[], homes=[])
    assert code == 0
    assert note.read_text(encoding="utf-8") == (
        "annual report by <user> (ann_x, ann2, joanne, <user>-marie)\n"
    )


def test_replace_names_lists_a_file_it_cannot_decode(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Latin-1 bytes and stray continuation bytes, with no byte-order mark: neither UTF-8 nor
    # UTF-16. CQ-03, the default the lead kept on 2026-11-25: unchanged, listed, exit 1.
    names = load("replace_names")
    raw = b"caf\xe9 zelda \x80\x81 C:\\Users\\zelda\r\n"
    odd = tmp_path / "odd.log"
    odd.write_bytes(raw)
    good = tmp_path / "good.txt"
    good.write_text("zelda\n", encoding="utf-8")
    code = names.run(tmp_path, **PLANTED)
    assert code == 1
    assert odd.read_bytes() == raw
    assert good.read_text(encoding="utf-8") == "<user>\n"
    printed = capsys.readouterr().out
    assert "not scanned: " in printed
    assert any(
        line.startswith("not scanned: ") and "odd.log" in line for line in printed.splitlines()
    )
