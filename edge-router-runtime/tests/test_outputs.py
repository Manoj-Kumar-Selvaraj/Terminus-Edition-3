import http.client
import json
import os
import signal
import socket
import subprocess
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

APP = Path("/app/edge-router")
CONFIG = APP / "config.json"
BINARY = APP / "edge-router"


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


class Backend:
    def __init__(self, name, status=200, block=False):
        self.name = name
        self.status = status
        self.block = block
        self.started = threading.Event()
        self.release = threading.Event()
        self.requests = []
        self.port = free_port()
        owner = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def _serve(self):
                length = int(self.headers.get("Content-Length", "0") or "0")
                body = self.rfile.read(length) if length else b""
                owner.requests.append(
                    {
                        "method": self.command,
                        "path": self.path,
                        "host": self.headers.get("Host"),
                        "headers": {k.lower(): v for k, v in self.headers.items()},
                        "body": body.decode("utf-8", errors="replace"),
                    }
                )
                owner.started.set()
                if owner.block:
                    owner.release.wait(timeout=10)
                payload = json.dumps(
                    {
                        "backend": owner.name,
                        "method": self.command,
                        "path": self.path,
                        "host": self.headers.get("Host"),
                        "headers": {k.lower(): v for k, v in self.headers.items()},
                        "body": body.decode("utf-8", errors="replace"),
                    }
                ).encode()
                self.send_response(owner.status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.send_header("Connection", "X-Up-Remove")
                self.send_header("X-Up-Remove", "secret")
                self.send_header("Keep-Alive", "timeout=9")
                self.end_headers()
                self.wfile.write(payload)

            do_GET = _serve
            do_HEAD = _serve
            do_OPTIONS = _serve
            do_POST = _serve
            do_PUT = _serve

            def log_message(self, *_args):
                return

        self.server = ThreadingHTTPServer(("127.0.0.1", self.port), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def url(self):
        return f"http://127.0.0.1:{self.port}"

    def start(self):
        self.thread.start()
        return self

    def stop(self):
        self.release.set()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


@pytest.fixture(scope="session", autouse=True)
def build_binary():
    """Build the submitted Go program once before behavioral verification."""
    subprocess.run(
        ["go", "build", "-o", str(BINARY), "."],
        cwd=APP,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


@contextmanager
def backends(*specs):
    items = [Backend(*spec).start() for spec in specs]
    try:
        yield items
    finally:
        for item in items:
            item.stop()


def write_config(routes, public_port=None, admin_port=None, shutdown_ms=2500, upstream_ms=1200):
    public_port = public_port or free_port()
    admin_port = admin_port or free_port()
    data = {
        "listen": f"127.0.0.1:{public_port}",
        "admin_listen": f"127.0.0.1:{admin_port}",
        "shutdown_timeout_ms": shutdown_ms,
        "upstream_timeout_ms": upstream_ms,
        "routes": routes,
    }
    CONFIG.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data, public_port, admin_port


def wait_http(port, path="/_edge/health", timeout=5):
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        try:
            conn = http.client.HTTPConnection("127.0.0.1", port, timeout=0.5)
            conn.request("GET", path)
            response = conn.getresponse()
            body = response.read()
            conn.close()
            if response.status < 500:
                return response.status, body, dict(response.getheaders())
        except OSError as exc:
            last_error = exc
        time.sleep(0.03)
    raise AssertionError(f"service did not become ready: {last_error}")


@contextmanager
def gateway(routes, shutdown_ms=2500, upstream_ms=1200):
    data, public_port, admin_port = write_config(
        routes, shutdown_ms=shutdown_ms, upstream_ms=upstream_ms
    )
    proc = subprocess.Popen(
        [str(BINARY), "-config", str(CONFIG)],
        cwd=APP,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        wait_http(admin_port)
        yield proc, data, public_port, admin_port
    finally:
        if proc.poll() is None:
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2)


def request(port, method, path, host, body=None, headers=None):
    headers = dict(headers or {})
    headers["Host"] = host
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=4)
    conn.request(method, path, body=body, headers=headers)
    response = conn.getresponse()
    raw = response.read()
    result = (response.status, raw, dict(response.getheaders()))
    conn.close()
    return result


def body_json(raw):
    return json.loads(raw.decode("utf-8"))


def admin_json(port, path):
    status, raw, _headers = wait_http(port, path)
    assert status == 200
    return body_json(raw)


def wait_generation(admin_port, generation, timeout=4):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            current = admin_json(admin_port, "/_edge/health")
            if current["generation"] == generation:
                return current
        except (OSError, AssertionError, json.JSONDecodeError):
            pass
        time.sleep(0.03)
    raise AssertionError(f"generation {generation} was not observed")


def test_route_precedence_host_normalization_and_query_preservation():
    """Select exact hosts before wildcards, then longest prefixes, while preserving request URI semantics."""
    with backends(("wild",), ("exact-root",), ("exact-deep",)) as (wild, root, deep):
        routes = [
            {"host": "*.example.test", "path_prefix": "/v1", "upstreams": [wild.url]},
            {"host": "api.example.test", "path_prefix": "/", "upstreams": [root.url]},
            {"host": "api.example.test", "path_prefix": "/v1/private", "upstreams": [deep.url]},
        ]
        with gateway(routes) as (_proc, _cfg, public_port, _admin_port):
            status, raw, _ = request(
                public_port,
                "GET",
                "/v1/private/item?x=1&x=2",
                "API.EXAMPLE.TEST:443",
            )
            assert status == 200
            payload = body_json(raw)
            assert payload["backend"] == "exact-deep"
            assert payload["path"] == "/v1/private/item?x=1&x=2"

            status, raw, _ = request(public_port, "GET", "/v1/public", "foo.example.test")
            assert status == 200
            assert body_json(raw)["backend"] == "wild"

            status, _raw, _ = request(public_port, "GET", "/v1/public", "example.test")
            assert status == 404


def test_round_robin_is_independent_per_route():
    """Rotate upstream selection in config order and keep each route's counter independent."""
    with backends(("a",), ("b",)) as (a, b):
        routes = [
            {"host": "rr.test", "path_prefix": "/one", "upstreams": [a.url, b.url]},
            {"host": "rr.test", "path_prefix": "/two", "upstreams": [a.url, b.url]},
        ]
        with gateway(routes) as (_proc, _cfg, public_port, _admin_port):
            seen_one = [body_json(request(public_port, "GET", "/one", "rr.test")[1])["backend"] for _ in range(4)]
            seen_two = [body_json(request(public_port, "GET", "/two", "rr.test")[1])["backend"] for _ in range(2)]
            assert seen_one == ["a", "b", "a", "b"]
            assert seen_two == ["a", "b"]


def test_proxy_headers_and_response_hop_headers_are_sanitized():
    """Remove hop-by-hop headers in both directions and construct forwarding headers without destroying the existing chain."""
    with backends(("headers",)) as (backend,):
        routes = [{"host": "headers.test", "path_prefix": "/", "upstreams": [backend.url]}]
        with gateway(routes) as (_proc, _cfg, public_port, _admin_port):
            status, raw, response_headers = request(
                public_port,
                "GET",
                "/echo",
                "headers.test:8443",
                headers={
                    "Connection": "X-Remove, keep-alive",
                    "X-Remove": "secret",
                    "Keep-Alive": "timeout=4",
                    "X-Forwarded-For": "198.51.100.7",
                },
            )
            assert status == 200
            payload = body_json(raw)
            forwarded = payload["headers"]
            assert "x-remove" not in forwarded
            assert "connection" not in forwarded
            assert "keep-alive" not in forwarded
            assert forwarded["x-forwarded-for"].startswith("198.51.100.7, ")
            assert forwarded["x-forwarded-for"].endswith("127.0.0.1")
            assert forwarded["x-forwarded-host"] == "headers.test:8443"
            assert forwarded["x-forwarded-proto"] == "http"
            assert payload["host"] == "headers.test:8443"
            lowered_response = {k.lower(): v for k, v in response_headers.items()}
            assert "x-up-remove" not in lowered_response
            assert "keep-alive" not in lowered_response


def test_transport_retry_is_limited_to_safe_bodyless_methods():
    """Retry one transport failure for safe bodyless methods but never replay a POST body."""
    dead_port = free_port()
    with backends(("live-get",), ("live-post",)) as (live_get, live_post):
        routes = [
            {
                "host": "retry.test",
                "path_prefix": "/get",
                "upstreams": [f"http://127.0.0.1:{dead_port}", live_get.url],
            },
            {
                "host": "retry.test",
                "path_prefix": "/post",
                "upstreams": [f"http://127.0.0.1:{dead_port}", live_post.url],
            },
        ]
        with gateway(routes, upstream_ms=500) as (_proc, _cfg, public_port, _admin_port):
            status, raw, _ = request(public_port, "GET", "/get", "retry.test")
            assert status == 200
            assert body_json(raw)["backend"] == "live-get"
            assert len(live_get.requests) == 1

            status, _raw, _ = request(
                public_port,
                "POST",
                "/post",
                "retry.test",
                body="do-not-replay",
                headers={"Content-Type": "text/plain"},
            )
            assert status == 502
            assert live_post.requests == []


def test_http_status_never_triggers_retry():
    """Treat an upstream HTTP response, including 5xx, as final rather than as a retryable transport failure."""
    with backends(("first", 503), ("second", 200)) as (first, second):
        routes = [{"host": "status.test", "path_prefix": "/", "upstreams": [first.url, second.url]}]
        with gateway(routes) as (_proc, _cfg, public_port, _admin_port):
            status, raw, _ = request(public_port, "GET", "/", "status.test")
            assert status == 503
            assert body_json(raw)["backend"] == "first"
            assert len(first.requests) == 1
            assert second.requests == []


def test_reload_is_atomic_and_rejects_invalid_or_listener_changing_config():
    """Publish valid SIGHUP reloads atomically while retaining the prior generation after any invalid reload."""
    with backends(("old",), ("new",)) as (old, new):
        routes = [{"host": "reload.test", "path_prefix": "/", "upstreams": [old.url]}]
        with gateway(routes) as (proc, cfg, public_port, admin_port):
            assert admin_json(admin_port, "/_edge/health") == {"status": "ok", "generation": 1}
            assert admin_json(admin_port, "/_edge/config") == {"generation": 1, "route_count": 1}
            assert body_json(request(public_port, "GET", "/", "reload.test")[1])["backend"] == "old"

            cfg["routes"][0]["upstreams"] = [new.url]
            CONFIG.write_text(json.dumps(cfg), encoding="utf-8")
            proc.send_signal(signal.SIGHUP)
            wait_generation(admin_port, 2)
            assert body_json(request(public_port, "GET", "/", "reload.test")[1])["backend"] == "new"

            invalid = json.loads(json.dumps(cfg))
            invalid["routes"][0]["upstreams"] = ["ftp://127.0.0.1/nope"]
            CONFIG.write_text(json.dumps(invalid), encoding="utf-8")
            proc.send_signal(signal.SIGHUP)
            time.sleep(0.15)
            assert admin_json(admin_port, "/_edge/health")["generation"] == 2
            assert body_json(request(public_port, "GET", "/", "reload.test")[1])["backend"] == "new"

            moved = json.loads(json.dumps(cfg))
            moved["listen"] = f"127.0.0.1:{free_port()}"
            CONFIG.write_text(json.dumps(moved), encoding="utf-8")
            proc.send_signal(signal.SIGHUP)
            time.sleep(0.15)
            assert admin_json(admin_port, "/_edge/config")["generation"] == 2
            assert proc.poll() is None


def test_admin_unknown_path_is_404():
    """Expose only the documented health and config resources on the admin listener."""
    with backends(("admin",)) as (backend,):
        routes = [{"host": "admin.test", "path_prefix": "/", "upstreams": [backend.url]}]
        with gateway(routes) as (_proc, _cfg, _public_port, admin_port):
            status, _raw, _headers = wait_http(admin_port, "/not-an-admin-resource")
            assert status == 404


def test_graceful_shutdown_drains_inflight_request_before_exit():
    """Stop on SIGTERM without killing a request that was already executing upstream."""
    with backends(("slow", 200, True)) as (slow,):
        routes = [{"host": "drain.test", "path_prefix": "/", "upstreams": [slow.url]}]
        with gateway(routes, shutdown_ms=3000, upstream_ms=6000) as (proc, _cfg, public_port, _admin_port):
            result = {}

            def call_gateway():
                try:
                    result["response"] = request(public_port, "GET", "/slow", "drain.test")
                except Exception as exc:  # captured for assertion in the main test thread
                    result["error"] = repr(exc)

            thread = threading.Thread(target=call_gateway)
            thread.start()
            assert slow.started.wait(timeout=3), "upstream never received the in-flight request"
            proc.send_signal(signal.SIGTERM)
            time.sleep(0.1)
            assert proc.poll() is None, "process exited while an in-flight request was still blocked"
            slow.release.set()
            thread.join(timeout=4)
            assert not thread.is_alive()
            assert "error" not in result
            status, raw, _headers = result["response"]
            assert status == 200
            assert body_json(raw)["backend"] == "slow"
            proc.wait(timeout=4)
            assert proc.returncode == 0
