# Step 1 of P0 on the Windows machine (P0-O1)

This is the owner's procedure for step 1 of P0 (`docs/15-phases-and-decisions.md:11`, `:23`; `docs/PLAN.md` 3.4, P0-O1). It runs every command of step 1 in order and saves each one's output in its own file under `docs/review/ground-windows/step1/`. The files decide B4 (`cpu-time-check.txt`), give P0.5's figures (`platform-check.txt`, `top-norules.json`, `restricted-share.txt`) and P0.3's (`defender-asr.txt`), and are read by the gate reviewer for P0.2 to P0.5 (`docs/PLAN.md` 6.4).

It takes about 45 minutes, of which about 2 minutes have the computer asleep (step 8). Nothing here needs administrator rights, changes a process or a setting, or sends anything anywhere except the final push to `origin`.

Rules for every step:

- Use a PowerShell window started normally: from the Start menu, not "Run as administrator". Windows PowerShell 5.1 and PowerShell 7 both work.
- Paste the blocks in order into the same window, from the repository root. A step uses variables an earlier step set.
- Every file is written through `Out-File -Encoding utf8`. Windows PowerShell 5.1 writes UTF-16 with a bare `>`, which `git grep` and the review tools cannot search (`docs/PLAN.md` 6.2 step 4). Never use `>` here.
- Every file starts with a line `$ <command>` and ends with a line `exit=<code>`, as `docs/PLAN.md` 6.2 (evidence layout) asks. The function `Run` of step 0 writes both.
- If a step fails, keep its file as it is and go on. A failing check is a finding (it becomes a fix task, `docs/PLAN.md` 5.5), not something to fix during this run.

## 0. Set up

Open PowerShell normally, go to your clone of the repository, and check out the P0-W1 integration commit that `docs/STATUS.md` names for P0-O1:

```powershell
cd <your clone>
git fetch origin
git switch --detach <the P0-W1 integration commit>
git status --short              # must print nothing
```

Then paste this block. It makes the evidence folder, a folder in your temporary folder for three small helper files, and the function `Run`, which prints `$ <command>`, the command's output and `exit=<code>`, so that each step pipes it into its own file.

```powershell
$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8   # read uv's and Python's output as UTF-8
$env:PYTHONIOENCODING = "utf-8"                             # and have Python write it as UTF-8
$d = "docs\review\ground-windows\step1"
New-Item -ItemType Directory -Force $d | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$tools = Join-Path $env:TEMP "submeter-step1-tools-$stamp"
New-Item -ItemType Directory $tools | Out-Null

function Run([scriptblock]$Command) {
  $text = $Command.ToString().Trim()
  Write-Host "running: $text"
  "`$ $text"
  $global:LASTEXITCODE = 0
  $failed = $false
  try {
    & $Command 2>&1 | ForEach-Object {
      if ($_ -is [System.Management.Automation.ErrorRecord]) { "$_" } else { $_ }
    } | Out-String -Stream -Width 4096
  } catch {
    "$_"
    $failed = $true
  }
  $code = if ($LASTEXITCODE) { $LASTEXITCODE } elseif ($failed) { 1 } else { 0 }
  Write-Host "exit=$code"
  "exit=$code"
}
```

## 1. The commit and the integrity level

```powershell
Run { git rev-parse HEAD; git status --short } | Out-File -Encoding utf8 "$d\0-commit.txt"
Run { whoami /groups | Select-String "Mandatory Level" } | Out-File -Encoding utf8 "$d\0-integrity.txt"
```

`0-commit.txt` holds the commit and one status line, `?? docs/review/ground-windows/step1/`, the folder this run is writing. `0-integrity.txt` must read `Medium Mandatory Level`. `High Mandatory Level` means the window is elevated: close it, open PowerShell normally and start again.

## 2. The seven checks

The seven commands of `AGENTS.md`, as `docs/PLAN.md` 6.2 step 4 runs them. Step 7 takes a few minutes.

```powershell
Run { uv sync --locked } | Out-File -Encoding utf8 "$d\1-sync.txt"
Run { uv run ruff check } | Out-File -Encoding utf8 "$d\2-ruff-check.txt"
Run { uv run ruff format --check } | Out-File -Encoding utf8 "$d\3-ruff-format.txt"
Run { uv run mypy src tests } | Out-File -Encoding utf8 "$d\4-mypy.txt"
Run { uv run mypy --platform win32 src tests } | Out-File -Encoding utf8 "$d\5-mypy-win32.txt"
Run { uv run mypy --platform linux src tests } | Out-File -Encoding utf8 "$d\6-mypy-linux.txt"
Run { uv run pytest -m "not owner_machine and not session and not hardware and not soak" -rsxX } | Out-File -Encoding utf8 "$d\7-pytest.txt"
```

Each file should end `exit=0`.

## 3. The platform check

The time just before the script goes in its own file, because step 4 looks for Defender events after it.

```powershell
$start = Get-Date
Run { $start.ToString("o") } | Out-File -Encoding utf8 "$d\platform-check-start.txt"
Run { uv run python scripts/platform_check.py } | Out-File -Encoding utf8 "$d\platform-check.txt"
```

`platform-check.txt` must print `administrator or root: False`. Its "process reading" line gives the number of restricted processes, the first of P0.5's three figures. A line starting `FAIL` is a finding (`docs/reference/windows-priorities.md`, sections 2 to 6).

## 4. Defender's attack surface reduction events (R126)

Events 1121 (blocked) and 1122 (audited) in the Defender Operational log since the time of step 3, and those that name python.exe (`docs/reference/windows-priorities.md:92`). If a standard user cannot read the log, the error is the file's content and its exit is 1 (Q4); that is a result, not a failure of the procedure.

```powershell
Run {
  try {
    $events = @(Get-WinEvent -ErrorAction Stop -FilterHashtable @{
      LogName = "Microsoft-Windows-Windows Defender/Operational"; Id = 1121, 1122; StartTime = $start })
  } catch {
    if ($_.FullyQualifiedErrorId -notlike "NoMatchingEventsFound*") { throw }
    $events = @()
  }
  $python = @($events | Where-Object { $_.Message -match "pythonw?\.exe" })
  "since $($start.ToString("o")): $($events.Count) events with id 1121 or 1122, $($python.Count) naming python.exe"
  $python | Format-List TimeCreated, Id, Message
} | Out-File -Encoding utf8 "$d\defender-asr.txt"
```

Any event naming python.exe stops the build for a ruling (P0.3).

## 5. Interrupt and DPC time (R125)

Three repetitions of 10 s. It prints r1 and r2 for every core, then the decision for B4: `subtract interrupt and DPC`, `keep the busy sum` or `ask` (`docs/PLAN.md` 6.4, P0.4).

```powershell
Run { uv run python scripts/probes/cpu_time_check.py } | Out-File -Encoding utf8 "$d\cpu-time-check.txt"
```

## 6. The Restricted share without rules (R137)

`submeter top` with `SUBMETER_HOME` set to a new empty folder, so that no rules file is read, then the Restricted row's share of all CPU time and its process count from that output.

```powershell
$norules = Join-Path $env:TEMP "submeter-step1-norules-$stamp"
New-Item -ItemType Directory $norules | Out-Null
Run { $env:SUBMETER_HOME = $norules; uv run submeter top --seconds 2 --json } | Out-File -Encoding utf8 "$d\top-norules.json"
Remove-Item Env:\SUBMETER_HOME
Run { uv run python scripts/probes/restricted_share.py docs/review/ground-windows/step1/top-norules.json } | Out-File -Encoding utf8 "$d\restricted-share.txt"
```

`restricted-share.txt` gives the other two of P0.5's figures. A list with no `restricted` row says so and gives share 0 with 0 processes.

## 7. The clock check (R124)

The size of one step of `time.monotonic()`, which `docs/reference/windows-priorities.md` section 5 expects to be about 1 microsecond under Python 3.13, against 15.6 ms under 3.12.

```powershell
@'
import time

for name in ("monotonic", "perf_counter", "time"):
    info = time.get_clock_info(name)
    print(
        f"{name}: {info.implementation}, resolution {info.resolution * 1e6:.3f} us, "
        f"monotonic {info.monotonic}, adjustable {info.adjustable}"
    )
steps = []
last = time.monotonic()
while len(steps) < 1000:
    now = time.monotonic()
    if now > last:
        steps.append(now - last)
        last = now
steps.sort()
print(
    f"time.monotonic() over 1000 observed steps: smallest {steps[0] * 1e6:.2f} us, "
    f"median {steps[500] * 1e6:.2f} us, largest {steps[-1] * 1e6:.2f} us"
)
over = []
for _ in range(20):
    started = time.monotonic()
    time.sleep(0.25)
    over.append(time.monotonic() - started - 0.25)
over.sort()
print(
    f"a 250 ms sleep timed on time.monotonic(), 20 runs: median overshoot "
    f"{over[10] * 1000:.2f} ms, largest {over[-1] * 1000:.2f} ms"
)
'@ | Set-Content -Encoding ascii "$tools\clock_check.py"
Run { uv run python "$tools\clock_check.py" } | Out-File -Encoding utf8 "$d\clock-step.txt"
```

## 8. The suspend check (R59)

The check of `docs/reference/windows-priorities.md` section 5: a snapshot with the psutil provider, a sleep of at least 60 s, a second snapshot, both passed to the sampler. It passes when the batch is a gap, its `interval_s` includes the time asleep, the clock that counts suspend (QueryPerformanceCounter) moved by the whole time, and the clock that stops during suspend (QueryUnbiasedInterruptTime) moved only by the time awake. A gap alone does not pass it: about 70 s is a gap by its length alone.

First record which sleep states this computer has:

```powershell
Run { powercfg /a } | Out-File -Encoding utf8 "$d\sleep-states.txt"
```

Then write the check, start it, and as soon as `running:` appears, put the computer to sleep (Start, Power, Sleep). Leave it asleep for at least 2 minutes, wake it and sign in. The script waits up to 10 minutes for the sleep, notices the wake by the jump in the wall clock, and ends by itself 5 s later.

```powershell
@'
import sys
import time

from submeter.collector.sampler import Sampler
from submeter.providers.psutil_provider import PsutilProvider

WAIT_S, ASLEEP_S, SETTLE_S = 600.0, 60.0, 5.0
provider, sampler = PsutilProvider(), Sampler()
first = provider.snapshot()
sampler.ingest(first)
print(f"first snapshot taken; waiting up to {WAIT_S:.0f} s for a sleep of {ASLEEP_S:.0f} s or more")
deadline, last, asleep = time.time() + WAIT_S, time.time(), 0.0
while time.time() < deadline and asleep < ASLEEP_S:
    time.sleep(1.0)
    now = time.time()
    asleep, last = max(asleep, now - last - 1.0), now
time.sleep(SETTLE_S)
second = provider.snapshot()
batch = sampler.ingest(second)
assert batch is not None
wall = second.taken_at - first.taken_at
interval = second.monotonic - first.monotonic
awake = None
if first.awake is not None and second.awake is not None:
    awake = second.awake - first.awake
print(f"largest jump of the wall clock (the time asleep, to about 1 s): {asleep:.1f} s")
print(f"wall clock moved {wall:.1f} s")
print(f"clock that counts suspend (QueryPerformanceCounter) moved {interval:.1f} s")
shown = "unavailable" if awake is None else f"{awake:.1f} s"
print(f"clock that stops in suspend (QueryUnbiasedInterruptTime) moved {shown}")
print(f"sampler: gap={batch.gap} interval_s={batch.interval_s:.1f}")
checks = {
    f"the computer slept {ASLEEP_S:.0f} s or more": asleep >= ASLEEP_S,
    "the batch is a gap": batch.gap,
    "interval_s includes the time asleep": batch.interval_s >= wall - 2.0,
    "the clock that counts suspend moved by the whole time": abs(interval - wall) <= 2.0,
    "the clock that stops in suspend moved by the time awake only": (
        awake is not None and abs(awake - (wall - asleep)) <= 5.0
    ),
}
for name, passed in checks.items():
    print(f"{'PASS' if passed else 'FAIL'}  {name}")
sys.exit(0 if all(checks.values()) else 1)
'@ | Set-Content -Encoding ascii "$tools\suspend_check.py"
Run { uv run python "$tools\suspend_check.py" } | Out-File -Encoding utf8 "$d\suspend-check.txt"
```

If the file holds `FAIL  the computer slept 60 s or more`, no sleep of 60 s was seen: run the last line again and put the computer to sleep sooner. It overwrites the file.

## 9. Whether the private folders hold (R100)

`platform_check.py` made its folders under a temporary folder that it deletes when it ends, so this step makes them again the same way, with `FileMap.ensure()` under a new `SUBMETER_HOME` (`scripts/platform_check.py`, `check_places`), and lists their access control lists. Each folder Submeter makes should list only you, SYSTEM and Administrators (`docs/reference/windows-priorities.md:78`). The first `icacls` shows the temporary folder they sit in, for comparison.

```powershell
@'
import sys

from submeter.store.files import FileMap

files = FileMap.discover({"SUBMETER_HOME": sys.argv[1]})
files.ensure()
for folder in (files.settings_dir, files.data_dir, files.raw_dir, files.state_dir, files.logs_dir):
    print(f"{folder} made: {folder.is_dir()}")
'@ | Set-Content -Encoding ascii "$tools\make_folders.py"
$acl = Join-Path $env:TEMP "submeter-step1-acl-$stamp"
Run { uv run python "$tools\make_folders.py" $acl } | Out-File -Encoding utf8 "$d\folders-made.txt"
Run { icacls $env:TEMP; icacls $acl /T } | Out-File -Encoding utf8 "$d\icacls.txt"
```

## 10. Where `AppData` and `Local AppData` are (K18)

Submeter keeps settings under `%APPDATA%\Submeter` and data and state under `%LOCALAPPDATA%\Submeter`. Data must not land in a redirected or synced folder (`docs/reference/windows-priorities.md:77-79`). This reads the two values under `HKCU`, as stored and expanded, and says whether either Submeter folder lies under a OneDrive folder or on a network share. It only reads.

```powershell
Run {
  $key = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
  Get-ItemProperty -Path $key -Name "AppData", "Local AppData" -ErrorAction Stop | Format-List "AppData", "Local AppData"
  $item = Get-Item -Path $key
  foreach ($value in "AppData", "Local AppData") {
    "$value as stored: $($item.GetValue($value, $null, 'DoNotExpandEnvironmentNames'))"
  }
  "APPDATA=$env:APPDATA"
  "LOCALAPPDATA=$env:LOCALAPPDATA"
  $clouds = @($env:OneDrive, $env:OneDriveCommercial, $env:OneDriveConsumer | Where-Object { $_ } | Select-Object -Unique)
  "OneDrive folders: $(if ($clouds) { $clouds -join '; ' } else { 'none set' })"
  foreach ($folder in (Join-Path $env:APPDATA "Submeter"), (Join-Path $env:LOCALAPPDATA "Submeter")) {
    $under = @($clouds | Where-Object { $folder.StartsWith($_.TrimEnd("\") + "\", [StringComparison]::OrdinalIgnoreCase) })
    "$folder under OneDrive: $($under.Count -gt 0); on a network share: $($folder.StartsWith('\\'))"
  }
  foreach ($parent in $env:APPDATA, $env:LOCALAPPDATA) {
    $info = Get-Item -Force -Path $parent
    "$parent attributes: $($info.Attributes); link type: $(if ($info.LinkType) { $info.LinkType } else { 'none' })"
  }
} | Out-File -Encoding utf8 "$d\appdata-location.txt"
```

## 11. Read, replace the names, check, commit and push

1. Make the branch, then replace your user name, host name, domain name and home folder in every file with `<user>`, `<host>`, `<domain>` and `<home>`:

   ```powershell
   git switch -c owner/P0-O1
   uv run python scripts/probes/replace_names.py docs/review/ground-windows/step1
   ```

   It prints one line per file it changed and never prints a name. It must end `0 not scanned` and exit 0 (`$LASTEXITCODE`). A `not scanned:` line names a file it could not read as UTF-8 or UTF-16: that file was written another way. Write it again with its step, and run the line above again.

2. Read every file in `docs/review/ground-windows/step1/` before the commit, for example with `notepad`. Look for anything you do not want in the repository, such as the name of another program or a folder of yours, as well as the results the table below lists.

3. Stage the folder and run the name check of `docs/PLAN.md` 6.2 step 4:

   ```powershell
   git add docs/review/ground-windows/step1
   git grep --cached -n -i -F -e $env:USERNAME -e $env:COMPUTERNAME -- docs/review/ground-windows/step1
   ```

   It must print nothing. It matches inside longer words too, so read each line it prints: change every occurrence of your name to `<user>` or `<host>`, save the file, and run both lines again until it prints nothing.

4. Commit only this folder and push the branch:

   ```powershell
   git status --short          # only files under docs/review/ground-windows/step1/
   git commit -m "P0-O1: owner's evidence"
   git push origin owner/P0-O1
   ```

5. Remove the temporary folders this run made. They hold nothing that is committed:

   ```powershell
   Remove-Item -Recurse -Force $tools, $norules, $acl
   ```

## The files

All under `docs/review/ground-windows/step1/`, UTF-8, each starting with `$ <command>` and ending with `exit=<code>`. The five names P0-O1 lists are fixed; the others are this procedure's.

| File | Step | What to read in it | Read for |
| --- | --- | --- | --- |
| `0-commit.txt` | 1 | the P0-W1 integration commit; only the `step1/` folder in the status | P0.2 (a) |
| `0-integrity.txt` | 1 | `Medium Mandatory Level` | P0.2 |
| `1-sync.txt` to `7-pytest.txt` | 2 | `exit=0` in each; the pytest summary line | P0.2, S1 |
| `platform-check-start.txt` | 3 | the time step 4 searches from | P0.3 |
| `platform-check.txt` | 3 | `administrator or root: False`; `FAIL` lines; the restricted count | P0.2, P0.5 |
| `defender-asr.txt` | 4 | 0 events naming python.exe, or the error a standard user gets | P0.3 |
| `cpu-time-check.txt` | 5 | r1 and r2 for every core in every repetition, and the decision | P0.4, B4 |
| `top-norules.json` | 6 | the JSON list of workloads, with or without a `restricted` row | P0.5 |
| `restricted-share.txt` | 6 | the share and the process count of the `restricted` row | P0.5 |
| `clock-step.txt` | 7 | the smallest step of `time.monotonic()` | R124 |
| `sleep-states.txt` | 8 | which sleep states the computer has | R59 |
| `suspend-check.txt` | 8 | five `PASS` lines, or which one failed | R59 |
| `folders-made.txt` | 9 | every folder `made: True` | R100 |
| `icacls.txt` | 9 | no other user on the folders Submeter made | R100 |
| `appdata-location.txt` | 10 | `under OneDrive: False` and `on a network share: False` for both folders | K18 |
