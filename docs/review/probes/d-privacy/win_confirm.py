"""Windows only: four checks the Linux review could not run. Written on Linux, never run.

Run on Windows as the signed-in user, not elevated:
    uv run python docs/review/probes/d-privacy/win_confirm.py

1. Who may read a folder made under %LOCALAPPDATA%, with the default mode and with 0o700, and
   what a folder on the drive root would inherit. Prints icacls output with the user and
   computer names replaced.
2. Whether starting a child with CREATE_BREAKAWAY_FROM_JOB fails once this process is inside
   a Job Object that sets no limits, which is how the brief says tagged trees are launched.
3. Whether a second socket can bind a loopback port that is already bound, for each socket
   option the first one might have set.
4. In which order `localhost` resolves, and whether ::1 can be bound on a port that is already
   bound on 127.0.0.1.
It makes two folders and removes them, puts itself (only) in one new Job Object, and opens
loopback sockets. It touches no other process, never elevates and sends nothing.
"""

from __future__ import annotations

import ctypes
import os
import socket
import subprocess
import sys
import tempfile
from pathlib import Path


def acl(path: str) -> str:
    text = subprocess.run(["icacls", path], capture_output=True, text=True).stdout
    for secret, label in ((os.environ["USERNAME"], "USER"), (os.environ["COMPUTERNAME"], "PC")):
        text = text.replace(secret, label)
    return " | ".join(line.strip() for line in text.splitlines()[:-2] if line.strip())


def check_folders() -> None:
    local = os.environ["LOCALAPPDATA"]
    with tempfile.TemporaryDirectory(dir=local) as name:
        plain, private = Path(name) / "plain", Path(name) / "private"
        plain.mkdir()
        os.mkdir(private, 0o700)
        print(f"1. %LOCALAPPDATA%: {acl(local)}")
        print(f"   new folder, default mode: {acl(str(plain))}")
        version = sys.version.split()[0]
        print(f"   new folder, os.mkdir(0o700) on Python {version}: {acl(str(private))}")
    print(f"   drive root, what SUBMETER_HOME there would inherit: {acl(Path(local).anchor)}")


def spawn_with_breakaway() -> str:
    try:
        subprocess.run(["cmd", "/c", "exit"], creationflags=subprocess.CREATE_BREAKAWAY_FROM_JOB)
    except OSError as error:
        return f"failed: {error}"
    return "succeeded"


def check_breakaway() -> None:
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateJobObjectW.restype = ctypes.c_void_p
    kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    kernel32.AssignProcessToJobObject.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
    print(f"2. before joining a job, a breakaway spawn {spawn_with_breakaway()}")
    job = kernel32.CreateJobObjectW(None, None)  # no limits set, so breakaway is not allowed
    joined = kernel32.AssignProcessToJobObject(job, kernel32.GetCurrentProcess())
    print(f"   joined a new job with no limits: {bool(joined)}")
    print(f"   inside it, a breakaway spawn {spawn_with_breakaway()}")


def check_ports() -> None:
    exclusive = getattr(socket, "SO_EXCLUSIVEADDRUSE", None)
    options = {"no option": None, "SO_REUSEADDR": socket.SO_REUSEADDR, "exclusive": exclusive}
    for first_name, first_option in options.items():
        first = socket.socket()
        if first_option is not None:
            first.setsockopt(socket.SOL_SOCKET, first_option, 1)
        first.bind(("127.0.0.1", 0))
        first.listen(1)
        results = []
        for second_name in ("no option", "SO_REUSEADDR"):
            second = socket.socket()
            if options[second_name] is not None:
                second.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                second.bind(("127.0.0.1", first.getsockname()[1]))
                results.append(f"second with {second_name} BOUND THE SAME PORT")
            except OSError as error:
                results.append(f"second with {second_name} refused ({error.errno})")
            second.close()
        print(f"3. first socket with {first_name}: {'; '.join(results)}")
        first.close()


def check_localhost() -> None:
    first = socket.socket()
    first.bind(("127.0.0.1", 0))
    first.listen(1)
    port = first.getsockname()[1]
    order = [info[4][0] for info in socket.getaddrinfo("localhost", port, type=socket.SOCK_STREAM)]
    print(f"4. localhost resolves to, in order: {order}")
    second = socket.socket(socket.AF_INET6)
    try:
        second.bind(("::1", port))
        print("   a second socket BOUND ::1 on the port already bound on 127.0.0.1")
    except OSError as error:
        print(f"   binding ::1 on the same port was refused ({error.errno})")
    second.close()
    first.close()


if __name__ == "__main__":
    if sys.platform != "win32":
        sys.exit("This probe is for Windows. Nothing was run.")
    check_folders()
    check_ports()
    check_localhost()
    check_breakaway()
