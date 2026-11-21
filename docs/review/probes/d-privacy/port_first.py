"""Does a client that follows the brief notice when something else owns the API port?

Run:  uv run python docs/review/probes/d-privacy/port_first.py

The brief has every client send the API token to a loopback port taken from the settings, and
says nothing about who is listening there. This probe binds a free loopback port with a
stand-in that is not Submeter, then makes the request a command-line client would make, with
a fake token. It prints what the stand-in received, and what a server that starts afterwards
is told when it asks for the same port. Loopback only, and no proxy is used.
"""

from __future__ import annotations

import socket
import threading
import urllib.request

TOKEN = "FAKE-api-token"
REPLY = (
    b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: 15\r\n"
    b'Connection: close\r\n\r\n{"status":"ok"}'
)


def stand_in(listener: socket.socket, seen: list[str]) -> None:
    connection, _ = listener.accept()
    with connection:
        request = connection.recv(4096).decode("latin-1")
        seen.extend(line for line in request.split("\r\n") if line.startswith("Authorization"))
        connection.sendall(REPLY)


def main() -> None:
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(1)
    port = listener.getsockname()[1]
    seen: list[str] = []
    thread = threading.Thread(target=stand_in, args=(listener, seen))
    thread.start()

    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request(
        f"http://127.0.0.1:{port}/api/v1/health", headers={"Authorization": f"Bearer {TOKEN}"}
    )
    with opener.open(request, timeout=5) as response:
        print(f"the client was answered: {response.status} {response.read().decode()}")
    thread.join()
    print(f"the stand-in, which is not Submeter, received: {seen}")

    late = socket.socket()
    try:
        late.bind(("127.0.0.1", port))
        print("a server starting afterwards could bind the same port as well")
    except OSError as error:
        print(f"a server starting afterwards cannot bind the port: {error.strerror}")
    finally:
        late.close()
        listener.close()


if __name__ == "__main__":
    main()
