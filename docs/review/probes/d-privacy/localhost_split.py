"""Can two programs own "the API port" at once, and which one does a client of `localhost` reach?

Run:  uv run python docs/review/probes/d-privacy/localhost_split.py

The brief binds the API to 127.0.0.1 and has every client send the token to a loopback name.
1. With a stand-in for the server listening on 127.0.0.1, can a second program listen on the
   same port number on the other loopback address, ::1?
2. In which order does this machine resolve `localhost`, and which listener receives the
   Authorization header of a client that was given http://localhost:PORT?
3. If the first listener sets SO_REUSEADDR before binding, as common servers do, can a second
   socket with the same option bind the very same address and port? (Linux answer only.)
Loopback only, fake token, no proxy. Nothing is stored.
"""

from __future__ import annotations

import socket
import threading
import urllib.request

TOKEN = "FAKE-api-token"
REPLY = b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok"


def listen(family: int, address: str, port: int, *, reuse: bool = False) -> socket.socket:
    listener = socket.socket(family, socket.SOCK_STREAM)
    if reuse:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind((address, port))
    listener.listen(4)
    listener.settimeout(3)
    return listener


def serve_once(listener: socket.socket, label: str, seen: list[str]) -> None:
    try:
        connection, _ = listener.accept()
    except TimeoutError:
        return
    with connection:
        request = connection.recv(4096).decode("latin-1")
        got = [line for line in request.split("\r\n") if line.startswith("Authorization")]
        seen.append(f"{label} received {got}")
        connection.sendall(REPLY)


def main() -> None:
    server = listen(socket.AF_INET, "127.0.0.1", 0)
    port = server.getsockname()[1]
    try:
        other = listen(socket.AF_INET6, "::1", port)
        print("1. a second program bound [::1] on the same port while 127.0.0.1 was held: True")
    except OSError as error:
        print(f"1. the ::1 bind was refused ({error.strerror}); the rest needs IPv6 loopback")
        server.close()
        return

    order = [info[4][0] for info in socket.getaddrinfo("localhost", port, type=socket.SOCK_STREAM)]
    print(f"2. this machine resolves localhost to, in order: {order}")
    seen: list[str] = []
    threads = [
        threading.Thread(target=serve_once, args=(server, "the listener on 127.0.0.1", seen)),
        threading.Thread(target=serve_once, args=(other, "the listener on ::1", seen)),
    ]
    for thread in threads:
        thread.start()
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    request = urllib.request.Request(
        f"http://localhost:{port}/api/v1/health", headers={"Authorization": f"Bearer {TOKEN}"}
    )
    with opener.open(request, timeout=3) as response:
        response.read()
    for thread in threads:
        thread.join()
    print(f"   a client given http://localhost:{port} was answered by: {seen}")
    server.close()
    other.close()

    first = listen(socket.AF_INET, "127.0.0.1", 0, reuse=True)
    try:
        listen(socket.AF_INET, "127.0.0.1", first.getsockname()[1], reuse=True).close()
        print("3. both with SO_REUSEADDR: the second socket BOUND THE SAME ADDRESS AND PORT")
    except OSError as error:
        print(f"3. both with SO_REUSEADDR: the second bind was refused here ({error.strerror})")
    first.close()


if __name__ == "__main__":
    main()
