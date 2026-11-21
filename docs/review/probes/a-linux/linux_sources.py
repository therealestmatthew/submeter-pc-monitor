"""Which Linux sources named in docs/09-telemetry.md deliver here, to a signed-in user?

Run from the repository root, never as root:
    uv run python docs/review/probes/a-linux/linux_sources.py

For each source it says whether the files exist and can be read, and ends with the line the
capability matrix of `submeter doctor` should print on this machine. It reads only. It prints
counts, driver names and field names: no address, path of a user, or command line.
"""

from __future__ import annotations

import ctypes.util
import os
from collections import Counter
from pathlib import Path

import psutil

CPU = Path("/sys/devices/system/cpu")
ME = os.getuid()
matrix: list[tuple[str, str, str]] = []


def can_read(path: Path) -> bool:
    try:
        path.read_bytes()
        return True
    except OSError:
        return False


def pressure() -> None:
    seen = {name: can_read(Path(f"/proc/pressure/{name}")) for name in ("cpu", "memory", "io")}
    lines = Path("/proc/pressure/cpu").read_text().split("\n") if seen["cpu"] else []
    kinds = [line.split()[0] for line in lines if line]
    print(f"pressure: readable {seen}; the cpu file has lines {kinds}")
    own = Path("/sys/fs/cgroup" + Path("/proc/self/cgroup").read_text().strip()[3:])
    per_group = [name for name in ("cpu", "memory", "io") if can_read(own / f"{name}.pressure")]
    print(f"  per cgroup, in this shell's own cgroup: {per_group}")
    matrix.append(("pressure", "full" if all(seen.values()) else "partial", "cpu, memory, io"))


def temperatures() -> None:
    chips = Counter[str]()
    for chip in Path("/sys/class/hwmon").glob("hwmon*"):
        inputs = list(chip.glob("temp*_input"))
        if inputs:
            chips[(chip / "name").read_text().strip()] += sum(can_read(path) for path in inputs)
    via_psutil = {name: len(readings) for name, readings in psutil.sensors_temperatures().items()}
    print(f"temperatures: hwmon chips with readable sensors {dict(chips)}; psutil {via_psutil}")
    matrix.append(("thermal.temp", "full" if chips else "unavailable", f"{len(chips)} chips"))


def frequency_and_throttling() -> None:
    cpus = sorted(CPU.glob("cpu[0-9]*"))
    current = sum(can_read(cpu / "cpufreq" / "scaling_cur_freq") for cpu in cpus)
    ceiling = sum(can_read(cpu / "cpufreq" / "cpuinfo_max_freq") for cpu in cpus)
    driver = CPU / "cpu0" / "cpufreq" / "scaling_driver"
    name = driver.read_text().strip() if driver.exists() else "none"
    print(
        f"frequency: {len(cpus)} CPUs, current readable for {current}, maximum for {ceiling}, "
        f"driver {name}; psutil gives {len(psutil.cpu_freq(percpu=True))} readings"
    )
    counters = [cpu / "thermal_throttle" / "package_throttle_count" for cpu in cpus]
    present = sum(path.exists() for path in counters)
    events = sum(int(path.read_text()) for path in counters if can_read(path))
    files = sorted(p.name for p in (CPU / "cpu0" / "thermal_throttle").glob("*"))
    vendor = next(
        line.split(":")[1].strip()
        for line in Path("/proc/cpuinfo").read_text().splitlines()
        if line.startswith("vendor_id")
    )
    print(
        f"throttle counters: present for {present} of {len(cpus)} CPUs ({vendor}), files {files}, "
        f"package events since boot {events}, up {uptime_days():.1f} days"
    )
    state = "full" if current and present else "partial" if current else "unavailable"
    matrix.append(("thermal.throttle", state, "frequency" + (" and counters" if present else "")))


def uptime_days() -> float:
    return float(Path("/proc/uptime").read_text().split()[0]) / 86400


def power() -> None:
    supplies = Path("/sys/class/power_supply").glob("*")
    batteries = [s.name for s in supplies if (s / "type").read_text().strip() == "Battery"]
    via_psutil = psutil.sensors_battery() is not None
    print(f"battery: {len(batteries)} found; psutil reports one: {via_psutil}")
    matrix.append(("power.battery", "full" if batteries else "unavailable", ""))
    energy = list(Path("/sys/class/powercap").glob("*/energy_uj"))
    modes = sorted({oct(path.stat().st_mode & 0o777) for path in energy})
    owners = sorted({path.stat().st_uid for path in energy})
    print(
        f"RAPL: {len(energy)} energy counters, readable {sum(can_read(p) for p in energy)}, "
        f"modes {modes}, owner uids {owners}"
    )
    matrix.append(("power.energy", "unavailable", "RAPL counters are readable by root only"))


def connections() -> None:
    result = Counter[str]()
    for process in psutil.process_iter():
        try:
            owner = "own" if process.uids().real == ME else "other users'"
            process.net_connections()
            result[f"{owner} processes read"] += 1
        except psutil.AccessDenied:
            result[f"{owner} processes denied"] += 1
        except psutil.Error:
            continue
    everything = psutil.net_connections()
    unowned = sum(1 for connection in everything if connection.pid is None)
    print(f"connections: {dict(result)}")
    print(f"  system-wide list: {len(everything)} sockets, {unowned} with no process visible")
    matrix.append(("net.connections", "partial", "own-user processes only"))


def gpu() -> None:
    cards = {}
    for card in Path("/sys/class/drm").glob("card[0-9]"):
        driver = card / "device" / "driver"
        cards[card.name] = driver.resolve().name if driver.exists() else "unknown"
    nvml = ctypes.util.find_library("nvidia-ml")
    amd = list(Path("/sys/class/drm").glob("card[0-9]/device/gpu_busy_percent"))
    keys, clients, denied = Counter[str](), 0, 0
    for process in Path("/proc").glob("[0-9]*"):
        try:
            links = [(fd, os.readlink(fd)) for fd in (process / "fd").iterdir()]
        except PermissionError:
            denied += 1
            continue
        except OSError:
            continue
        info = [process / "fdinfo" / fd.name for fd, target in links if "/dev/dri/" in target]
        text = "".join(path.read_text() for path in info if can_read(path))
        found = {line.split(":")[0] for line in text.splitlines() if line.startswith("drm-")}
        clients += bool(found)
        keys.update(found)
    print(f"GPU: cards {cards}; NVML library {nvml}; AMD sysfs load files {len(amd)}")
    print(
        f"  DRM fdinfo: {clients} processes of this user hold a GPU client, fields "
        f"{sorted(keys)}; {denied} processes could not be inspected"
    )
    state = "full" if nvml else "unavailable"
    matrix.append(("gpu.load", state, "no NVML library and no AMD card" if not nvml else "NVML"))


def commit() -> None:
    info = {
        line.split(":")[0]: int(line.split()[1])
        for line in Path("/proc/meminfo").read_text().splitlines()
    }
    mode = Path("/proc/sys/vm/overcommit_memory").read_text().strip()
    print(
        f"commit: Committed_AS / CommitLimit = {info['Committed_AS'] / info['CommitLimit']:.2f} "
        f"with vm.overcommit_memory = {mode}; memory in use = "
        f"{1 - info['MemAvailable'] / info['MemTotal']:.2f} of RAM; swap in use = "
        f"{1 - info['SwapFree'] / max(info['SwapTotal'], 1):.2f}"
    )


if __name__ == "__main__":
    checks = (pressure, temperatures, frequency_and_throttling, power, connections, gpu, commit)
    for check in checks:
        check()
    print("\nwhat the capability matrix should print here")
    for name, status, note in matrix:
        print(f"  {name:<18}{status:<13}{note}")
