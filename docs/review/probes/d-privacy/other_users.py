"""How many command lines of other users would the baseline write into this user's raw file?

Run:  uv run python docs/review/probes/d-privacy/other_users.py

The brief says command lines of processes owned by other users are not readable. On Linux they
are, so the baseline provider returns them and the raw store keeps them for 48 hours in a file
this user owns. The probe takes one snapshot with the baseline provider and prints counts only:
no command line, no user name.
"""

from __future__ import annotations

import getpass

import psutil

from submeter.providers.psutil_provider import PsutilProvider


def main() -> None:
    me = getpass.getuser()
    owner = {process.pid: process.info["username"] for process in psutil.process_iter(["username"])}
    snapshot = PsutilProvider().snapshot()
    other = [p for p in snapshot.processes if owner.get(p.key.pid) not in (me, None)]
    with_arguments = [p for p in other if p.cmdline and len(p.cmdline) > 1]
    of_root = sum(1 for p in with_arguments if owner.get(p.key.pid) == "root")
    owners = {owner[p.key.pid] for p in with_arguments}
    print(f"processes in one snapshot: {len(snapshot.processes)}")
    print(f"owned by another user (kernel threads included): {len(other)}")
    print(
        f"of those, handed to the store with arguments in the command line: {len(with_arguments)}"
    )
    print(f"  belonging to root: {of_root}; distinct other owners: {len(owners)}")
    print(f"  marked restricted by the provider: {sum(1 for p in with_arguments if p.restricted)}")


if __name__ == "__main__":
    main()
