# CLI output

> Submeter build brief · Part 1, the product · [Index](README.md)

One sample for each job. Every command also takes `--json`.

## Job 1: what did that session cost?

```text
$ submeter cost --session "12 agents, Tuesday"
workload         source   cpu-hours   peak mem   avg mem   procs seen
agent:refactor   kernel        3.42     4.1 GB    2.8 GB        3,412
agent:tests      kernel        2.07     2.6 GB    1.9 GB        1,180
builds           kernel        1.31     2.2 GB    0.9 GB          212
browser          polled        0.52     5.4 GB    5.0 GB           31
ide              polled        0.31     3.6 GB    3.4 GB           14
unattributed     polled        0.11     2.1 GB    2.0 GB           74
system           counters      0.24        n/a       n/a          n/a
restricted       partial       0.05        n/a       n/a           14

Total  8.03 of 12.80 CPU-hours available (62.7%) over 48 min
Note   polled workloads may undercount short-lived children
```

## Job 2: why is it slow?

```text
$ submeter why
Verdict    CPU-bound     confidence: high     window: last 5 min

Evidence
  run queue        2.3 per core
  cpu time         91% of capacity
  frequency        98% of maximum  not throttled
  commit           71% of limit

Top contributors
  agent:refactor   38%   kernel-accounted
  agent:tests      23%   kernel-accounted
  builds           14%   kernel-accounted
  browser           6%   polled

Reconciled  attributed 87 + unattributed 1 + system 3 + restricted 1
            + not seen by polling 1 + idle 7 = 100%
```

## What can this machine measure?

```text
$ submeter doctor          (Windows 11, signed-in user)
provider            status        note
process.bulk        full
group.accounting    full          nested jobs available
memory.uss          partial       own-user processes only
gpu.load            full          per engine type
gpu.memory          full          adapter total only
thermal.temp        unavailable   no source without administrator rights
thermal.throttle    full
net.connections     unavailable   not in version 1
net.bytes           unavailable   not in version 1
vm.guest            opaque        WSL2 VM holds 3% of busy CPU time, 2% of capacity

Restricted   14 processes visible but not readable
Workloads    11 names, limit 200
Collector    0.6% of one core at 2 s, 41 MB
```

## Where is the data, and how much?

```text
$ submeter store status
file                    writer      size     covers
raw/2026-11-20.db       collector   212 MB   today, open
raw/2026-11-19.db       collector   371 MB   yesterday
raw/2026-11-18.db       collector   358 MB   expires in 15 h
history.db              server       31 MB   since 2026-08-02
backups/ (3 copies)     server       93 MB   latest 02:10 today
logs/ (2 programs)      each         18 MB

Total   1.08 GB of 2 GB    integrity ok    1 writer per file
Epoch   14, since 2026-11-12: active_interval 1s to 2s
```
