#!/usr/bin/env python3
import argparse
import json
import os
import selectors
import signal
import socket
import struct
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class Endpoint:
    name: str
    host: str
    port: int
    behavior: str


ENDPOINTS = (
    Endpoint("echo", "127.0.0.1", 19001, "echo every received byte"),
    Endpoint("slow", "127.0.0.1", 19002, "read small chunks with deterministic delay"),
    Endpoint("half-close", "127.0.0.1", 19003, "send greeting then close write direction"),
    Endpoint("reset", "127.0.0.1", 19004, "abort connection with TCP reset"),
    Endpoint("proxy-inspection", "127.0.0.1", 19005, "validate one PROXY protocol v2 header"),
)


class EventLog:
    def __init__(self, root: Path, maximum: int = 1024) -> None:
        self.root = root
        self.maximum = maximum
        self.lock = threading.Lock()
        self.events: list[dict[str, object]] = []

    def add(self, backend: str, event: str, **fields: object) -> None:
        record = {"at_ns": time.time_ns(), "backend": backend, "event": event, **fields}
        with self.lock:
            self.events.append(record)
            if len(self.events) > self.maximum:
                del self.events[: len(self.events) - self.maximum]
            self.root.mkdir(parents=True, exist_ok=True)
            temporary = self.root / "events.json.tmp"
            temporary.write_text(json.dumps(self.events, sort_keys=True) + "\n", encoding="ascii")
            os.replace(temporary, self.root / "events.json")


class Backend:
    def __init__(self, endpoint: Endpoint, handler: Callable[[socket.socket, tuple[str, int]], None], events: EventLog) -> None:
        self.endpoint = endpoint
        self.handler = handler
        self.events = events
        self.listener: socket.socket | None = None
        self.thread: threading.Thread | None = None
        self.stopping = threading.Event()

    def start(self) -> None:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind((self.endpoint.host, self.endpoint.port))
        listener.listen(128)
        listener.settimeout(0.25)
        self.listener = listener
        self.thread = threading.Thread(target=self._accept, name=self.endpoint.name, daemon=True)
        self.thread.start()

    def _accept(self) -> None:
        assert self.listener is not None
        while not self.stopping.is_set():
            try:
                connection, peer = self.listener.accept()
            except TimeoutError:
                continue
            except OSError:
                if self.stopping.is_set():
                    return
                raise
            self.events.add(self.endpoint.name, "accepted")
            threading.Thread(target=self._serve, args=(connection, peer), daemon=True).start()

    def _serve(self, connection: socket.socket, peer: tuple[str, int]) -> None:
        try:
            connection.settimeout(10)
            self.handler(connection, peer)
            self.events.add(self.endpoint.name, "completed")
        except Exception as error:
            self.events.add(self.endpoint.name, "error", error=type(error).__name__)
        finally:
            connection.close()

    def stop(self) -> None:
        self.stopping.set()
        if self.listener is not None:
            self.listener.close()
        if self.thread is not None:
            self.thread.join(timeout=2)


def echo(connection: socket.socket, _peer: tuple[str, int]) -> None:
    while data := connection.recv(16384):
        connection.sendall(data)


def slow(connection: socket.socket, _peer: tuple[str, int]) -> None:
    while data := connection.recv(256):
        time.sleep(0.025)
        connection.sendall(data)


def half_close(connection: socket.socket, _peer: tuple[str, int]) -> None:
    connection.sendall(b"half-close-ready\n")
    connection.shutdown(socket.SHUT_WR)
    while connection.recv(4096):
        pass


def reset(connection: socket.socket, _peer: tuple[str, int]) -> None:
    connection.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("ii", 1, 0))


def receive_exact(connection: socket.socket, size: int) -> bytes:
    output = bytearray()
    while len(output) < size:
        chunk = connection.recv(size - len(output))
        if not chunk:
            raise EOFError("short PROXY header")
        output.extend(chunk)
    return bytes(output)


def proxy_inspection(connection: socket.socket, _peer: tuple[str, int]) -> None:
    prefix = receive_exact(connection, 16)
    if prefix[:12] != b"\r\n\r\n\x00\r\nQUIT\n":
        raise ValueError("invalid PROXY signature")
    if prefix[12] != 0x21:
        raise ValueError("unsupported PROXY version or command")
    address_length = struct.unpack("!H", prefix[14:16])[0]
    if address_length > 216:
        raise ValueError("PROXY address block too large")
    receive_exact(connection, address_length)
    while data := connection.recv(16384):
        connection.sendall(data)


HANDLERS = {
    "echo": echo,
    "slow": slow,
    "half-close": half_close,
    "reset": reset,
    "proxy-inspection": proxy_inspection,
}


def endpoint_document() -> dict[str, object]:
    return {"backends": [endpoint.__dict__ for endpoint in ENDPOINTS]}


def run(root: Path) -> int:
    events = EventLog(root)
    backends = [Backend(endpoint, HANDLERS[endpoint.name], events) for endpoint in ENDPOINTS]
    stopping = threading.Event()

    def request_stop(_number: int, _frame: object) -> None:
        stopping.set()

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)
    for backend in backends:
        backend.start()
    print(json.dumps(endpoint_document(), sort_keys=True), flush=True)
    while not stopping.wait(0.25):
        pass
    for backend in reversed(backends):
        backend.stop()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("start", "list"))
    parser.add_argument("--state", default="/app/sovereign-lb/state/lab")
    arguments = parser.parse_args()
    if arguments.command == "list":
        print(json.dumps(endpoint_document(), indent=2, sort_keys=True))
        return 0
    return run(Path(arguments.state))


if __name__ == "__main__":
    sys.exit(main())