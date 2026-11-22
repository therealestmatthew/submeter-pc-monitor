# Baseline modules

> Submeter build brief · Part 3, the build · [Index](README.md)

Fifteen Python modules that form the platform-neutral core of Submeter, with the project file and their tests. This is working code, written and run for this brief: 2,356 lines in the modules and 20 tests. They start twelve of the 21 components in the build list. Each entry says what the module does, why it exists, what it provides, what it imports and what imports it.

In this package the files are already in place at the paths shown, 26 files in all: the 19 described here and 7 empty `__init__.py` files, one in each package folder.

## What was checked, and what was not

- Ruff reports nothing. mypy in strict mode reports no issues in 25 files, checked as Linux and again as Windows. All 20 tests pass on Python 3.12 and 3.13.
- Everything ran on Linux. `submeter top` took two snapshots of live processes and printed totals by workload.
- This package was unpacked into an empty folder, where `uv sync`, Ruff, mypy and the tests all passed.
- Nothing ran on Windows, so expect small fixes there. The one-instance lock was redesigned so that its lock file is never written, and its Windows calls are tested against a stand-in, but Windows itself has not answered them. Private-bytes memory in the psutil provider has never run. [`reference/windows-priorities.md`](reference/windows-priorities.md) lists what to check first, and `scripts/platform_check.py` checks it.
- The sample `submeter.toml` and `rules.toml` in `examples/` load through these modules without error.

## How they fit together

```mermaid
flowchart TD
    subgraph l3["COMMAND LINE"]
        direction TB
        cli["cli"]
    end
    subgraph l2["COLLECT, ATTRIBUTE, STORE, ANALYSE"]
        direction TB
        sampler["collector.sampler"]
        rules["attribution.rules"]
        growth["analysis.growth"]
        files["store.files"]
        raw["store.raw"]
        rollup["store.rollup"]
        query["store.query"]
    end
    subgraph l1["PRIVACY AND PROVIDERS"]
        direction TB
        redact["privacy.redact"]
        base["providers.base"]
        psutil["providers.psutil_provider"]
    end
    subgraph l0["CORE"]
        direction TB
        units["core.units"]
        models["core.models"]
        histogram["core.histogram"]
        config["core.config"]
    end
    l3 -->|imports| l2
    l2 --> l1
    l1 --> l0
```

*Figure:* Imports point only downward. A module may import from its own package or from a lower layer, and `tests/test_layers.py` fails if one does otherwise. That rule is what lets the collector be replaced later without touching the rest.

The table gives the same links module by module. "Nothing yet" means the caller is built in a later phase, and until then only the tests call that module.

| Module | Lines | Imports | Imported by |
| --- | --- | --- | --- |
| [`core.units`](../src/submeter/core/units.py) | 140 | nothing in the package | cli, core.config |
| [`core.models`](../src/submeter/core/models.py) | 187 | nothing in the package | analysis.growth, attribution.rules, collector.sampler, core.config, providers.base, providers.psutil_provider, store.query, store.raw, store.rollup |
| [`core.histogram`](../src/submeter/core/histogram.py) | 92 | nothing in the package | store.rollup |
| [`core.config`](../src/submeter/core/config.py) | 318 | core.models, core.units | cli |
| [`privacy.redact`](../src/submeter/privacy/redact.py) | 83 | nothing in the package | store.raw |
| [`providers.base`](../src/submeter/providers/base.py) | 36 | core.models | cli |
| [`providers.psutil_provider`](../src/submeter/providers/psutil_provider.py) | 129 | core.models | cli |
| [`collector.sampler`](../src/submeter/collector/sampler.py) | 112 | core.models | cli |
| [`attribution.rules`](../src/submeter/attribution/rules.py) | 233 | core.models | cli |
| [`store.files`](../src/submeter/store/files.py) | 260 | nothing in the package | cli, store.raw |
| [`store.raw`](../src/submeter/store/raw.py) | 287 | core.models, privacy.redact, store.files | nothing yet |
| [`store.rollup`](../src/submeter/store/rollup.py) | 173 | core.histogram, core.models | nothing yet |
| [`store.query`](../src/submeter/store/query.py) | 54 | core.models | nothing yet |
| [`analysis.growth`](../src/submeter/analysis/growth.py) | 110 | core.models | nothing yet |
| [`cli`](../src/submeter/cli.py) | 142 | attribution.rules, collector.sampler, core.config, core.units, providers.base, providers.psutil_provider, store.files | entry point |

## How to check them

- Run `uv sync`, then `uv run ruff check`, `uv run mypy src tests` and `uv run pytest`. Expect 20 tests to pass.
- Then hand over the execution prompt. It tells the session that this baseline exists, and that the build extends it instead of rewriting it.

## Not in the baseline, and why

- The Windows bulk snapshot and the Job Object launcher. They call Windows APIs and must be written and tested on Windows.
- The Linux /proc reader and cgroup accounting. They come after version 1, behind the same provider protocol. Version 1 runs Linux polled through the psutil provider.
- The writer for the history file, the detectors that call the growth arithmetic, the server and the report. Each depends on decisions made in its own phase.

## Module by module

### `pyproject.toml`

49 lines · [open the file](../pyproject.toml)

Declares the package, its three runtime dependencies, the submeter command, and the Ruff, mypy and pytest settings from the brief.

- **Why it exists:** So that uv sync and uv run pytest work from the first commit, and every later module is checked the same way.
- **Worth knowing:**
  - Source lives under src/submeter, and tests import it through the pytest pythonpath setting.
  - mypy runs in strict mode with the Pydantic plugin. Ruff uses a 100-character line.
  - Requires Python 3.12 or newer. The build backend is hatchling.
- **Builds toward:** Project file

### `src/submeter/__init__.py`

3 lines · [open the file](../src/submeter/__init__.py)

Names the package and holds the version string.

- **Why it exists:** The command line reads the version from here, so it is stated once.
- **Worth knowing:**
  - Three lines. Each package folder also needs an empty `__init__.py`, which this package includes.
- **Builds toward:** Package marker
- **Provides:** `__version__`

### `src/submeter/core/units.py`

140 lines · [open the file](../src/submeter/core/units.py)

Converts "250ms", "48h", "2GB", "50MB/h" and "1%" into seconds, bytes, bytes per second and fractions, and back again.

- **Why it exists:** Settings are written for people and code needs numbers. Doing the conversion in one place gives every malformed value the same error message.
- **Worth knowing:**
  - Sizes are binary: 1 GB is 1024 cubed bytes.
  - "forever" becomes infinity, which retention settings use.
  - `duration_range` and `fraction_range` build validators that refuse a value outside a range and name the range in the message.
  - Duration, Size, Fraction and Rate are the types that Pydantic fields use.
- **Builds toward:** Supports component 02, core.config
- **Provides:** `FOREVER`, `parse_duration`, `parse_size`, `parse_percent`, `parse_rate`, `format_duration`, `format_size`, `duration_range`, `fraction_range`, `Duration`, `Size`, `Fraction`, `Rate`
- **Imports:** pydantic
- **Imported by:** [`cli`](../src/submeter/cli.py), [`core.config`](../src/submeter/core/config.py)

### `src/submeter/core/models.py`

187 lines · [open the file](../src/submeter/core/models.py)

The frozen records passed between layers: counters, samples, workload totals, buckets, findings and capabilities.

- **Why it exists:** These classes are the contract between the collector, the server and the command line. Frozen and strict, so a record cannot be altered after it is made or carry a misspelt field.
- **Worth knowing:**
  - A process is identified by ProcessKey, which is pid plus start time.
  - ProcessCounters holds running totals as a provider read them. ProcessSample holds what happened in one interval.
  - Bucket carries everything needed to merge buckets exactly: sums, extremes, a time-weighted mean, two histograms and covered seconds.
  - No behaviour lives here.
- **Builds toward:** Component 01, core.models
- **Provides:** `Record`, `Availability`, `AccountingSource`, `Severity`, `Confidence`, `Tier`, `Capability`, `ProcessKey`, `ProcessCounters`, `SystemCounters`, `Snapshot`, `ProcessSample`, `SampleBatch`, `WorkloadSample`, `Bucket`, `Finding`
- **Imports:** pydantic
- **Imported by:** [`analysis.growth`](../src/submeter/analysis/growth.py), [`attribution.rules`](../src/submeter/attribution/rules.py), [`collector.sampler`](../src/submeter/collector/sampler.py), [`core.config`](../src/submeter/core/config.py), [`providers.base`](../src/submeter/providers/base.py), [`providers.psutil_provider`](../src/submeter/providers/psutil_provider.py), [`store.query`](../src/submeter/store/query.py), [`store.raw`](../src/submeter/store/raw.py), [`store.rollup`](../src/submeter/store/rollup.py)

### `src/submeter/core/histogram.py`

92 lines · [open the file](../src/submeter/core/histogram.py)

A 64-bin histogram that merges by adding bins and returns percentiles.

- **Why it exists:** A percentile of percentiles is not a percentile. Keeping a histogram in every bucket is what makes a weekly 95th percentile valid (finding R27).
- **Worth knowing:**
  - Two scales are defined: cores from 0.01 to 256, and memory from 16 MiB to 256 GiB.
  - A reported percentile is within one bin of the true value, a factor of about 1.17. The test checks that bound.
  - Weights are seconds, so the histogram is time-weighted.
  - merge can check only the bin count, and both scales have the same count. Keeping cores and memory histograms apart is the caller's job.
- **Builds toward:** Part of component 10, store.rollup
- **Provides:** `Scale`, `CORES`, `MEMORY`, `empty`, `add`, `merge`, `percentile`
- **Imports:** standard library only
- **Imported by:** [`store.rollup`](../src/submeter/store/rollup.py)

### `src/submeter/core/config.py`

318 lines · [open the file](../src/submeter/core/config.py)

Builds one immutable Settings object from defaults, submeter.toml, environment variables and overrides, and records where each value came from.

- **Why it exists:** The rule that values are refused and never clamped, and the config show --effective command, both need a single validated source of truth.
- **Worth knowing:**
  - Every default and range in the tables of `docs/08-configuration.md` was checked against this module. A value outside its range is refused, with the range in the error.
  - Unknown keys are errors, so a typo cannot silently do nothing.
  - Alert rules are structured fields. The TOML key "for" maps to the field duration.
  - Environment variables look like `SUBMETER_SAMPLING__ACTIVE_INTERVAL`.
  - The sample `submeter.toml` in `examples/` loads through this module without error.
  - Not here yet: the three built-in alert rules. The rules list holds only your own.
- **Builds toward:** Component 02, core.config
- **Provides:** `ENV_PREFIX`, `ActiveInterval`, `IdleInterval`, `IdleAfter`, `SlowInterval`, `GpuInterval`, `UssInterval`, `KeyframeInterval`, `OverheadShare`, `OverheadLimit`, `Sampling`, `Retention`, `Backups`, `ChangeThreshold`, `Storage`, `Leak`, `SlowGrowth`, `Baseline`, `Analysis`, `Verdict`, `AlertRule`, `Alerts`, `Attribution`, `Privacy`, `Providers`, `Api`, `Ui`, `Settings`, `ConfigError`, `LoadedSettings`, `load_settings`
- **Imports:** [`core.models`](../src/submeter/core/models.py), [`core.units`](../src/submeter/core/units.py), pydantic
- **Imported by:** [`cli`](../src/submeter/cli.py)

### `src/submeter/privacy/redact.py`

83 lines · [open the file](../src/submeter/privacy/redact.py)

Hides secrets in command lines and in free text before anything is stored.

- **Why it exists:** Command lines carry keys and tokens. Scrubbing on the way in means no later bug can expose what was never written (finding R04).
- **Worth knowing:**
  - Hides the value after a secret-looking flag, the value of a secret-looking NAME=value pair, known token shapes, URL passwords, and long opaque strings of letters and digits.
  - Errs towards hiding too much. A 40-character commit hash is hidden as well.
  - Ordinary arguments survive: --max-tokens 4096 is left alone.
  - In `exe_only` mode only the executable is kept.
- **Builds toward:** Component 16, privacy.redact
- **Provides:** `REDACTED`, `Mode`, `redact_text`, `redact_cmdline`
- **Imports:** standard library only
- **Imported by:** [`store.raw`](../src/submeter/store/raw.py)

### `src/submeter/providers/base.py`

36 lines · [open the file](../src/submeter/providers/base.py)

The protocol every process provider implements, and the capability report that doctor prints.

- **Why it exists:** The sampler depends on this protocol alone, so the psutil fallback, the Windows bulk snapshot, the Linux /proc reader and a fake in a test are interchangeable.
- **Worth knowing:**
  - Providers return running totals and never rates.
  - A capability is full, partial with what is missing, or unavailable with why.
- **Builds toward:** Component 03, providers.base
- **Provides:** `ProcessProvider`, `capability_report`
- **Imports:** [`core.models`](../src/submeter/core/models.py)
- **Imported by:** [`cli`](../src/submeter/cli.py)

### `src/submeter/providers/psutil_provider.py`

129 lines · [open the file](../src/submeter/providers/psutil_provider.py)

A process provider built on psutil, so it is not tied to one operating system.

- **Why it exists:** It gives a working collector on the first day. It is the fallback and cross-check the brief requires for the Windows bulk snapshot, and in version 1 it is the process reader on Linux.
- **Worth knowing:**
  - It asks about one process at a time, which is too slow for a 1-second cadence on a busy machine. On Windows it is not the hot path. On Linux in version 1 it is, so the overhead guard will hold the intervals longer there.
  - A process that cannot be read fully is still returned and marked restricted. Nothing is dropped.
  - Memory is private bytes on Windows and resident memory elsewhere. Swap is not added yet.
  - Disk I/O is left empty where psutil cannot read it, as on macOS.
  - Reading each working directory is off by default because of its cost.
- **Builds toward:** Fallback for component 04, and the Linux process reader in version 1 (component 05 comes after it)
- **Provides:** `PsutilProvider`
- **Imports:** [`core.models`](../src/submeter/core/models.py), psutil
- **Imported by:** [`cli`](../src/submeter/cli.py)

### `src/submeter/collector/sampler.py`

112 lines · [open the file](../src/submeter/collector/sampler.py)

Subtracts consecutive snapshots to find what each process did during the interval.

- **Why it exists:** Turning totals into deltas is where CPU time could be lost or invented. One module handles first sightings, reused process ids and gaps.
- **Worth knowing:**
  - The first call returns nothing, because there is no interval yet.
  - A process born during the interval is credited all its CPU time. An older process seen for the first time is credited none.
  - A reused pid is a new process, because identity includes the start time.
  - Each snapshot carries two clocks. Intervals are measured on the one that counts suspend: CLOCK_BOOTTIME on Linux, `time.monotonic()` on Windows. The other stops during suspend, CLOCK_MONOTONIC on Linux and QueryUnbiasedInterruptTime on Windows, and is read only for the suspend test. Where it is not read, there is no suspend test.
  - An interval longer than 30 seconds, or one in which the clock that counts suspend ran more than 2 seconds ahead of the clock that does not, is a gap: deltas are zero and the batch says so.
  - Not here yet: the adaptive cadence loop and the overhead guard.
  - The fixed 30-second rule and the zeroed deltas are wrong (finding R38), and a planned task replaces them together with R39's gap handling in the store. ingest() will take the interval expected for the tick. A tick will be a gap only past three times that interval plus the 2-second slack, or when the suspend test fires, and a gap will keep its CPU and I/O deltas. Until then any interval over 30 seconds records zero CPU, and `submeter top --seconds` above 30 prints zero cores for every workload.
- **Builds toward:** Core of component 07, collector.sampler
- **Provides:** `Sampler`
- **Imports:** [`core.models`](../src/submeter/core/models.py)
- **Imported by:** [`cli`](../src/submeter/cli.py)

### `src/submeter/attribution/rules.py`

233 lines · [open the file](../src/submeter/attribution/rules.py)

Gives every process exactly one workload, with the reason, and totals a batch by workload.

- **Why it exists:** The order of attribution and the rule that nothing is dropped are what let the parts be checked against the whole.
- **Worth knowing:**
  - Order: tagged kernel group, then Submeter itself, then rules in priority order, then inheritance from a valid parent, then Unattributed or Restricted.
  - A parent link counts only if the parent started no later than the child.
  - A rule may match on exe, cmdline, cwd and parent, the program that started the process. Every condition it gives must hold. Program names match on file name, ignoring case.
  - `needs_cwd` tells the caller whether any rule uses the working folder, so that folders are read only then.
  - aggregate marks each workload as measured by the kernel, by polling, or partially.
  - The sample `rules.toml` in `examples/` loads through this module without error.
- **Builds toward:** Component 15, attribution
- **Provides:** `UNATTRIBUTED`, `RESTRICTED`, `SYSTEM`, `SELF`, `Rule`, `RuleSet`, `Attribution`, `Attributor`, `aggregate`
- **Imports:** [`core.models`](../src/submeter/core/models.py), pydantic
- **Imported by:** [`cli`](../src/submeter/cli.py)

### `src/submeter/store/files.py`

260 lines · [open the file](../src/submeter/store/files.py)

The file map: where settings, data and state live on each platform, the name of the file for a given day or week, which files have expired, and the lock that stops two copies running.

- **Why it exists:** No other module builds a path by hand, so the layout can change in one place (finding R30).
- **Worth knowing:**
  - `SUBMETER_HOME` moves everything under one folder. The tests use it.
  - Raw files are named by UTC day, minute files by ISO week.
  - A file expires only once its whole day or week ended longer ago than the retention.
  - The lock file is only ever locked, never written. The holder's process id goes in a file beside it, NAME.pid.
  - The lock was run on Linux with two real processes, and against a stand-in for the Windows locking call. How Windows itself answers has still to be run there.
- **Builds toward:** Component 08, store.files
- **Provides:** `HOME_VARIABLE`, `Program`, `utc_day`, `FileMap`, `InstanceLock`
- **Imports:** standard library only
- **Imported by:** [`cli`](../src/submeter/cli.py), [`store.raw`](../src/submeter/store/raw.py)

### `src/submeter/store/raw.py`

287 lines · [open the file](../src/submeter/store/raw.py)

Writes the daily raw file: workload totals every interval, process rows on change with keyframes, and command lines stored once.

- **Why it exists:** This is the redesigned raw store from the storage audit (findings R23, R25 and R31).
- **Worth knowing:**
  - CPU used between written rows is carried into the next row, so per-process sums stay exact. A test compares the stored sum with the true total.
  - A keyframe writes every live process in full. One opens each file and one follows every keyframe interval.
  - A gap is recorded in its own table, and that batch is written in full.
  - Command lines are redacted here whatever the caller did. A test reads the file bytes to confirm the secret is absent.
  - RawStore rolls over at UTC midnight and flushes pending CPU before closing a file.
- **Builds toward:** Component 09, store.raw
- **Provides:** `SCHEMA_VERSION`, `RawFile`, `RawStore`
- **Imports:** [`core.models`](../src/submeter/core/models.py), [`privacy.redact`](../src/submeter/privacy/redact.py), [`store.files`](../src/submeter/store/files.py)
- **Imported by:** Nothing yet. The collector loop will, in phase 2.

### `src/submeter/store/rollup.py`

173 lines · [open the file](../src/submeter/store/rollup.py)

Folds samples into buckets, and buckets into wider buckets, keeping totals exact.

- **Why it exists:** Rollups that cannot reproduce totals were the second critical finding of the storage audit (R24).
- **Worth knowing:**
  - Counters are summed. Gauges keep minimum, maximum, time-weighted mean and last value.
  - Each bucket records covered seconds and active seconds.
  - An hour merged from 60 minute buckets equals the hour built directly from samples. A test checks the sum, the mean, the extremes and the 95th percentile.
  - Merging buckets from different series is refused.
  - Pure functions with no files. The writer for the history file is still to build.
- **Builds toward:** Component 10, store.rollup
- **Provides:** `bucket_start`, `SeriesAccumulator`, `roll_up`, `merge`, `cores_percentile`, `memory_percentile`, `well_covered`
- **Imports:** [`core.histogram`](../src/submeter/core/histogram.py), [`core.models`](../src/submeter/core/models.py)
- **Imported by:** Nothing yet. The history writer will, in phase 3.

### `src/submeter/store/query.py`

54 lines · [open the file](../src/submeter/store/query.py)

Chooses the tier and step for a time window, and explains the choice.

- **Why it exists:** Without a rule, a 7-day chart could mix raw and rolled-up data without saying so (finding R33).
- **Worth knowing:**
  - Picks the finest tier whose retention still covers the start of the window.
  - Moves to a coarser tier, and then to wider steps, when the answer would hold more points than a chart can use.
  - Returns the reason as text, for the CLI and the report's charts to show.
- **Builds toward:** Component 11, store.query
- **Provides:** `TierChoice`, `choose_tier`
- **Imports:** [`core.models`](../src/submeter/core/models.py)
- **Imported by:** Nothing yet. The commands that read history, and the report, will.

### `src/submeter/analysis/growth.py`

110 lines · [open the file](../src/submeter/analysis/growth.py)

The Theil-Sen slope, the plateau test, the usual range from median and spread, and daily minimums.

- **Why it exists:** Leak and baseline checks need statistics that one spike cannot move.
- **Worth knowing:**
  - A leak is long enough, steep enough, and still climbing. Growth that stops is cleared.
  - The slope is the median of the slopes between pairs of points, so one spike does not move it. A test confirms that with 20 points.
  - `check_growth` answers "not enough data yet" until it has 8 points spanning the minimum duration.
  - `usual_range` returns nothing until it has five values.
  - `daily_minimums` feeds the slow-growth check and takes a UTC offset for local days.
- **Builds toward:** Arithmetic for component 17, analysis.detectors
- **Provides:** `theil_sen`, `plateaued`, `GrowthResult`, `check_growth`, `usual_range`, `daily_minimums`
- **Imports:** [`core.models`](../src/submeter/core/models.py)
- **Imported by:** Nothing yet. The detectors will, in phase 4.

### `src/submeter/cli.py`

142 lines · [open the file](../src/submeter/cli.py)

The command line, with the first five commands: doctor, top, config show, config check and store status.

- **Why it exists:** It proves the modules connect end to end, and it stays thin so that no logic hides in it.
- **Worth knowing:**
  - submeter top takes two snapshots, attributes the difference and prints totals by workload.
  - doctor, top and store status accept --json. config show accepts --effective, which is also its default.
  - top reads working folders only when a rule matches on cwd.
  - A bad settings file exits with code 2 and one line per problem.
- **Builds toward:** Start of component 12, cli
- **Provides:** `app`, `config_app`, `store_app`, `JsonFlag`, `FileOption`, `doctor`, `top`, `config_show`, `config_check`, `store_status`
- **Imports:** [`attribution.rules`](../src/submeter/attribution/rules.py), [`collector.sampler`](../src/submeter/collector/sampler.py), [`core.config`](../src/submeter/core/config.py), [`core.units`](../src/submeter/core/units.py), [`providers.base`](../src/submeter/providers/base.py), [`providers.psutil_provider`](../src/submeter/providers/psutil_provider.py), [`store.files`](../src/submeter/store/files.py), typer
- **Imported by:** Nothing. It is the entry point behind the submeter command.

### `tests/test_baseline.py`

521 lines · [open the file](../tests/test_baseline.py)

Nineteen tests covering every module above, including one that runs the command line end to end.

- **Why it exists:** They state what each module promises, and they are how you confirm the files were copied correctly.
- **Worth knowing:**
  - Exact sums through change suppression, exact totals through rollups, and the histogram error bound are each tested directly.
  - The redaction test reads the database file bytes.
- **Builds toward:** Tests

### `tests/test_layers.py`

43 lines · [open the file](../tests/test_layers.py)

One rule, checked from the source itself: a module may import only from its own package or from a lower layer.

- **Why it exists:** This is what keeps the collector replaceable and the core reusable.
- **Worth knowing:**
  - Add a new package to the LAYER table when you create one.
- **Builds toward:** Tests
