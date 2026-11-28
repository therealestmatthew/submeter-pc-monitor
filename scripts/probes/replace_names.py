"""Replaces this machine's user, host and domain names and home folder in every file of a folder.

Run it from the repository root, before anything recorded on a machine is committed:

    uv run python scripts/probes/replace_names.py docs/review/ground-windows/step1

The home folder becomes <home>, the user name <user>, the host name <host> (both the full name
and its part before the first dot) and the domain name (USERDOMAIN, where set) <domain>. Each is
matched as a whole token, case-insensitively: a token boundary is any character that is not a
letter, digit or underscore, so the user name `ann` is replaced in `ann-pc` and `C:\\Users\\ann`
but not in `annual`. The home folder is replaced first, so `C:\\Users\\ann\\x` becomes
`<home>\\x`; then the other names, longest first.

UTF-16 files are recognised by their byte-order mark; every other file is read as UTF-8, with
or without a byte-order mark. Each file is written back in the encoding it was read in, with
its line endings unchanged. A file that is neither is left unchanged and listed as
`not scanned: <path>`, and the run exits 1, so that it is looked at before the commit.

It prints one line per file changed, with the number of replacements, and never prints a name
it replaced. It reads and writes only files under the folder it is given.
"""

from __future__ import annotations

import getpass
import os
import re
import socket
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

USER, HOST, DOMAIN, HOME = "<user>", "<host>", "<domain>", "<home>"
BOMS = (
    (b"\xff\xfe", "utf-16-le"),
    (b"\xfe\xff", "utf-16-be"),
    (b"\xef\xbb\xbf", "utf-8"),
)

Plan = list[tuple[re.Pattern[str], str]]


def plan(
    *,
    users: Iterable[str],
    hosts: Iterable[str],
    domains: Iterable[str],
    homes: Iterable[str],
) -> Plan:
    """The patterns to apply, in order: home folders first, then the other names, longest first."""
    folders: list[tuple[str, str]] = []
    for home in homes:
        if home:  # the folder as written, with forward slashes, and escaped as in JSON
            for form in (home, home.replace("\\", "/"), home.replace("\\", "\\\\")):
                folders.append((form, HOME))
    names = [(name, USER) for name in users if name]
    names += [(name, HOST) for name in hosts if name]
    names += [(name, DOMAIN) for name in domains if name]
    names.sort(key=lambda pair: -len(pair[0]))  # stable: equal lengths keep the order above
    seen: set[str] = set()
    found: Plan = []
    for value, placeholder in folders + names:
        if value.casefold() in seen:
            continue
        seen.add(value.casefold())
        before = r"(?<!\w)" if _word(value[0]) else ""  # a boundary only where it can be one
        after = r"(?!\w)" if _word(value[-1]) else ""
        found.append((re.compile(before + re.escape(value) + after, re.IGNORECASE), placeholder))
    return found


def _word(character: str) -> bool:
    return re.match(r"\w", character) is not None


def substitute(text: str, patterns: Plan) -> tuple[str, int]:
    count = 0
    for pattern, placeholder in patterns:
        text, made = pattern.subn(placeholder, text)
        count += made
    return text, count


def decode(data: bytes) -> tuple[str, bytes, str] | None:
    """The text, the byte-order mark and the codec of a file, or None if it is neither encoding."""
    for bom, codec in BOMS:
        if data.startswith(bom):
            try:
                return data[len(bom) :].decode(codec), bom, codec
            except UnicodeDecodeError:
                return None
    try:
        return data.decode("utf-8"), b"", "utf-8"
    except UnicodeDecodeError:
        return None


def run(
    folder: Path,
    *,
    users: Sequence[str],
    hosts: Sequence[str],
    domains: Sequence[str],
    homes: Sequence[str],
) -> int:
    """Replace the names in every file under folder. 0 when every file was read, 1 otherwise."""
    patterns = plan(users=users, hosts=hosts, domains=domains, homes=homes)
    files = sorted(path for path in folder.rglob("*") if path.is_file())
    changed = total = 0
    unread: list[str] = []
    for path in files:
        shown = substitute(str(path), patterns)[0]  # a path may hold a name too
        data = path.read_bytes()
        found = decode(data)
        if found is None:
            unread.append(shown)
            print(f"not scanned: {shown}")
            continue
        text, bom, codec = found
        replaced, count = substitute(text, patterns)
        if count:
            path.write_bytes(bom + replaced.encode(codec))
            changed += 1
            total += count
            print(f"{count:>5} replaced in {shown}")
    print(f"{len(files)} files, {changed} changed, {total} replacements, {len(unread)} not scanned")
    return 1 if unread else 0


def this_machine() -> dict[str, list[str]]:
    """The names of the user running this script and of this machine.

    USERNAME and COMPUTERNAME are added where set, because the name check after this script
    greps for them, and COMPUTERNAME, the NetBIOS name, is cut to 15 characters.
    """
    host = socket.gethostname()
    domain = os.environ.get("USERDOMAIN", "")
    return {
        "users": [getpass.getuser(), os.environ.get("USERNAME", "")],
        "hosts": [host, host.split(".")[0], os.environ.get("COMPUTERNAME", "")],
        "domains": [domain] if domain else [],
        "homes": [str(Path.home())],
    }


def main(argv: Sequence[str]) -> int:
    if len(argv) != 1 or not Path(argv[0]).is_dir():
        print("usage: replace_names.py <folder>   (the folder must exist)")
        return 2
    return run(Path(argv[0]), **this_machine())


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
