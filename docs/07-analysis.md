# How it decides

> Submeter build brief · Part 2, the design · [Index](README.md)

Illustrative data showing what each detector looks at. These are the views the report's charts show in version 1, and the dashboard's History and Compare pages in version 1.1.

## Leak detection: growth without a plateau

Legend: IDE, private bytes; Browser, private bytes.

The chart shows private bytes in GB over six hours, one point every 5 minutes. Both series are synthetic.

| Time | IDE, GB | Browser, GB |
| --- | --- | --- |
| start | 3.09 | 3.60 |
| 1 h | 3.44 | 4.46 |
| 2 h | 3.82 | 4.51 |
| 3 h | 4.27 | 4.52 |
| 4 h | 4.62 | 4.46 |
| 5 h | 5.02 | 4.53 |
| 6 h | 5.43 | 4.51 |

- IDE: 3.1 GB plus 0.38 GB per hour, with noise of up to 0.05 GB either way. It ends at 5.4 GB.
- Browser: 3.6 GB plus 0.9 × (1 − e^(−t ÷ 0.35 h)) GB, with noise of up to 0.04 GB either way. It ends at 4.5 GB.
- The shaded band, marked "flagged window, 5 h", runs from hour 1 to hour 6. The fitted line for the IDE runs from 3.48 GB at hour 1 to 5.38 GB at hour 6.

*Figure:* The IDE grows 0.38 GB per hour for five hours with no levelling off, so it is flagged. The browser grows faster at first but flattens within the hour, which is a cache warming up, so it is cleared.

Growth is tracked for each workload as well as for each process, so a leak spread across short-lived processes is still seen.

## Baseline anomaly: a regression against the usual range (after version 1)

Not in version 1. Version 1 has no baseline anomaly or slow-growth check: regressions are found by hand with the session diff and the hourly history. The design below is kept for later.

Legend: IDE, daily peak memory; Outside the usual range.

The chart shows the IDE's daily peak memory in GB over 30 days. The data is synthetic: about 3.4 GB until day 22, then about 4.25 GB, with noise of up to 0.1 GB either way.

The value compared with the usual range is one per local day, built from hourly buckets: the daily peak, which is the highest hourly maximum of the day for memory and the highest hourly 95th percentile of cores in use for CPU.

Idle and active baselines are kept apart. An hourly bucket is active when its active seconds are at least half of its covered seconds, and a sample counts as active when the workload uses at least 0.005 of one core. Each baseline uses only the buckets of its own state, so a day gives one active and one idle daily peak, and a day with no buckets of a state gives no value for it.

- Days 1 to 7 are the learning period, so no range is drawn and nothing is raised.
- From day 8 the usual range is the median of the values from the last 14 days (`baseline.window`) that were not flagged, plus or minus 4 × 1.4826 × the median absolute deviation. From the first value outside the range until values return inside it, the range is held still.
- The floor bounds the median absolute deviation before it is scaled. It is never taken as less than 0.03 GB for memory or 0.05 cores for CPU, so a series that barely moves, such as an idle workload, still gets a range of non-zero width. `usual_range` applies its `floor` argument to the scaled spread, so the detector passes it 1.4826 times these values.
- A value outside the range is flagged and left out of later ranges, so one anomaly does not widen the band.
- An anomaly is raised only when 3 values in a row are outside the range, so one odd day raises nothing.
- A vertical line at day 12 is marked "settings changed".
- Day 23 is the first value outside the range, and the anomaly is raised on day 25, the third day in a row outside it.

The ranges in the table are approximate. They were drawn from unrounded data, so recomputing them from the rounded peaks shown moves some ends by a few hundredths of a GB.

| Day | Peak, GB | Usual range, GB | Status |
| --- | --- | --- | --- |
| 1 | 3.44 | learning | learning |
| 2 | 3.45 | learning | learning |
| 3 | 3.34 | learning | learning |
| 4 | 3.42 | learning | learning |
| 5 | 3.32 | learning | learning |
| 6 | 3.42 | learning | learning |
| 7 | 3.44 | learning | learning |
| 8 | 3.39 | 3.25 to 3.60 | within usual range |
| 9 | 3.48 | 3.24 to 3.60 | within usual range |
| 10 | 3.35 | 3.25 to 3.60 | within usual range |
| 11 | 3.46 | 3.23 to 3.61 | within usual range |
| 12 | 3.45 | 3.24 to 3.61 | within usual range |
| 13 | 3.43 | 3.25 to 3.61 | within usual range |
| 14 | 3.30 | 3.25 to 3.61 | within usual range |
| 15 | 3.39 | 3.25 to 3.61 | within usual range |
| 16 | 3.36 | 3.23 to 3.61 | within usual range |
| 17 | 3.48 | 3.14 to 3.67 | within usual range |
| 18 | 3.36 | 3.23 to 3.61 | within usual range |
| 19 | 3.45 | 3.13 to 3.68 | within usual range |
| 20 | 3.44 | 3.23 to 3.62 | within usual range |
| 21 | 3.35 | 3.19 to 3.69 | within usual range |
| 22 | 3.30 | 3.13 to 3.70 | within usual range |
| 23 | 4.31 | 3.09 to 3.73 | outside usual range |
| 24 | 4.19 | 3.09 to 3.73 | outside usual range |
| 25 | 4.20 | 3.09 to 3.73 | outside usual range |
| 26 | 4.17 | 3.09 to 3.73 | outside usual range |
| 27 | 4.24 | 3.09 to 3.73 | outside usual range |
| 28 | 4.35 | 3.09 to 3.73 | outside usual range |
| 29 | 4.20 | 3.09 to 3.73 | outside usual range |
| 30 | 4.17 | 3.09 to 3.73 | outside usual range |

*Figure:* Thirty days of one workload. Nothing is raised during the 7-day learning period. After that the usual range is the median plus or minus four spreads, and it holds still while an anomaly is open. The jump on day 23 is flagged, and raised as an anomaly on day 25, once three days in a row are outside the range. The settings change on day 12 is marked so it can be ruled out as the cause.

## Session diff: what changed between two days

Legend: Cost more on Tuesday; Cost less.

The chart is a bar for each workload, to either side of zero.

| Workload | Change in CPU-hours |
| --- | --- |
| Agents | +6.8 |
| Builds | +1.9 |
| Browser | +0.2 |
| Unattributed | +0.1 |
| Submeter | +0.05 |
| IDE | −0.3 |

*Figure:* Change in CPU-hours per workload, Tuesday (12 agents) against Monday (4 agents). Agents and the builds they trigger account for nearly all of the increase.

## How a bottleneck verdict is reached

This table is the single rule set for the verdict. `submeter why` checks every rule against the window, and the verdict is:

- the one rule that matches, when exactly one matches, its ruled-out condition does not hold and the verdict's confidence is at least `verdict.min_confidence`;
- No bottleneck, when no rule matches and the window holds at least 60 seconds of data;
- Inconclusive, when the signals disagree, the window holds fewer than 60 seconds of data, or the verdict's confidence is below `verdict.min_confidence`. The signals disagree when two or more rules match, or when a rule matches while its ruled-out condition holds.

| Verdict | Windows signals | Linux signals (after version 1) | Ruled out when |
| --- | --- | --- | --- |
| CPU-bound | Run queue above 1 per core, CPU time above 85% | CPU pressure (PSI) some above 20% | Frequency is being held down |
| Memory-bound | Commit above 85% of limit, page writes rising | Memory pressure full above 5%, swap-out rising | Page reads only, with no writes |
| I/O-bound | Disk queue length and latency above absolute thresholds | I/O pressure full above 10% | CPU is saturated too |
| GPU-bound | One engine type above 90% | Busiest DRM engine or NVML utilisation above 90% | The adapter's VRAM is full, which is reported separately |
| Thermally throttled | Frequency below 80% of the base (nominal) frequency under load | Throttle counters rising, frequency capped | A power-saving plan is active |
| No bottleneck | No rule above matches, with at least 60 seconds of data | The same as on Windows | Any rule above matches |
| Inconclusive | Two or more rules match, a rule matches while its ruled-out condition holds, fewer than 60 seconds of data, or the verdict's confidence is below `verdict.min_confidence` | The same as on Windows | Never forced into another class |

The base frequency is the processor's rated (nominal) frequency, not its turbo maximum. Turbo frequencies are not sustainable, so a laptop under steady all-core load would otherwise read as throttled.

Each threshold has an on value and an off value on the far side of it: lower for a signal that turns on above its threshold, higher for frequency, which turns on below it. A signal that has turned on stays on until it is back past its off value, so the verdict does not flicker at a threshold. Each threshold is named under `verdict.thresholds` in the settings.

| Setting | Signal | On | Off |
| --- | --- | --- | --- |
| `run_queue` | Run queue, per logical core | above 1.0 | set in phase 4 |
| `cpu_time` | CPU time, share of capacity | above 85% | below 80% |
| `commit` | Commit, share of the commit limit | above 85% | below 82% |
| `disk_queue` | Disk queue length | absolute value, set in phase 4 | set in phase 4 |
| `disk_latency` | Disk latency | absolute value, set in phase 4 | set in phase 4 |
| `gpu_engine` | Busiest GPU engine type | above 90% | set in phase 4 |
| `frequency` | Frequency under load, share of the base frequency | below 80% | set in phase 4 |

The Linux thresholds get on and off values in the same way when that column is built after version 1.

Version 1 does not judge the Linux column: PSI and the other Linux system counters come after version 1, and the Linux GPU load that version 1 reads is not used by the verdict. On Linux `why` reads Inconclusive or unavailable in version 1.

The disk queue and latency thresholds are absolute values, because version 1 learns no baselines. Thresholds are starting points for the builder to tune against fixtures. All of them are configurable.
