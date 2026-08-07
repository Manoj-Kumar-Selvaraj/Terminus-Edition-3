"""Local claims edge lab: plan adapter, origin stubs, and HTTP edge proxy."""
from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

VAR = Path("/app/var/edge")
DATA = Path("/app/data")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _canonicalize(value: Any) -> Any:
    """Order-stabilize a decoded plan for hashing.

    ``terraform show -json`` does not guarantee stable list ordering for
    independent resources across separate CLI invocations (graph-walk order
    varies run to run). Sort nested lists by an address/name-derived key so
    two plans with identical content hash identically regardless of that
    incidental ordering.
    """
    if isinstance(value, dict):
        return {k: _canonicalize(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        items = [_canonicalize(v) for v in value]

        def _sort_key(item: Any) -> str:
            if isinstance(item, dict):
                ident = item.get("address") or item.get("name")
                if ident is not None:
                    return json.dumps([str(ident)], sort_keys=True)
            return json.dumps(item, sort_keys=True, separators=(",", ":"))

        items.sort(key=_sort_key)
        return items
    return value


def plan_digest(plan: dict) -> str:
    # "timestamp" is the plan's wall-clock generation time, not plan content.
    stable_plan = {k: v for k, v in plan.items() if k != "timestamp"}
    blob = json.dumps(_canonicalize(stable_plan), sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def normalize_plan(plan: dict, inventory: dict | None = None) -> dict:
    """Build a domain graph from terraform show -json (or a sealed lab config)."""
    inventory = inventory or {
        "origins": _load_json(DATA / "origins.json"),
        "path_rules": _load_json(DATA / "path_rules.json"),
        "waf_policy": _load_json(DATA / "waf_policy.json"),
        "tls_policy": _load_json(DATA / "tls_policy.json"),
        "logging_policy": _load_json(DATA / "logging_policy.json"),
        "exception_requests": _load_json(DATA / "exception_requests.json"),
    }
    values = ((plan.get("planned_values") or {}).get("root_module") or {})
    resources = list(values.get("resources") or [])
    for child in values.get("child_modules") or []:
        resources.extend(child.get("resources") or [])

    by_type: dict[str, list[dict]] = {}
    for res in resources:
        by_type.setdefault(res.get("type") or "", []).append(res)

    oacs = {
        r["name"]: r.get("values") or {}
        for r in by_type.get("aws_cloudfront_origin_access_control", [])
    }
    dists = {
        r["name"]: r.get("values") or {}
        for r in by_type.get("aws_cloudfront_distribution", [])
    }
    waf = next(iter(by_type.get("aws_wafv2_web_acl", [])), None)
    headers = next(iter(by_type.get("aws_cloudfront_response_headers_policy", [])), None)
    buckets = {
        r["name"]: r.get("values") or {}
        for r in by_type.get("aws_s3_bucket", [])
    }
    policies = {
        r["name"]: r.get("values") or {}
        for r in by_type.get("aws_s3_bucket_policy", [])
    }

    # Map distribution comment/name to logical id
    dist_map = {}
    for name, vals in dists.items():
        comment = (vals.get("comment") or name or "").lower()
        if "fail" in comment or name == "failover":
            dist_map["failover"] = vals
        elif "signed" in comment or name == "signed_content":
            dist_map["signed-content"] = vals
        else:
            dist_map["static-api"] = vals

    graph = {
        "inventory": inventory,
        "oac_present": bool(oacs),
        "oac_count": len(oacs),
        "distributions": dist_map,
        "waf_name": (waf or {}).get("values", {}).get("name") if waf else None,
        "waf_arn_planned": True if waf else False,
        "headers_ok": False,
        "logging_hosts": {},
        "bucket_policy_principals": {},
        "has_s3_origin_config": False,
        "signed_trusted_on_default": False,
        "path_behaviors": {},
    }

    if headers:
        hv = headers.get("values") or {}
        sec = hv.get("security_headers_config") or {}
        if isinstance(sec, list):
            sec = sec[0] if sec else {}
        frame = sec.get("frame_options") or {}
        if isinstance(frame, list):
            frame = frame[0] if frame else {}
        referrer = sec.get("referrer_policy") or {}
        if isinstance(referrer, list):
            referrer = referrer[0] if referrer else {}
        graph["headers_ok"] = (
            "content_type_options" in sec
            and frame.get("frame_option") == "DENY"
            and referrer.get("referrer_policy") == "same-origin"
        )

    for logical, vals in dist_map.items():
        log = vals.get("logging_config") or {}
        if isinstance(log, list):
            log = log[0] if log else {}
        graph["logging_hosts"][logical] = log.get("bucket")
        viewer = vals.get("viewer_certificate") or {}
        if isinstance(viewer, list):
            viewer = viewer[0] if viewer else {}
        graph.setdefault("tls", {})[logical] = viewer.get("minimum_protocol_version")

        behaviors = []
        default = vals.get("default_cache_behavior") or {}
        if isinstance(default, list):
            default = default[0] if default else {}
        behaviors.append({"path": "/*", "default": True, **default})
        ordered = vals.get("ordered_cache_behavior") or []
        if isinstance(ordered, dict):
            ordered = [ordered]
        for b in ordered:
            behaviors.append({"path": b.get("path_pattern"), "default": False, **b})
        graph["path_behaviors"][logical] = behaviors
        if default.get("trusted_key_groups") or default.get("trusted_signers"):
            graph["signed_trusted_on_default"] = True

        for origin in vals.get("origin") or []:
            if origin.get("s3_origin_config"):
                graph["has_s3_origin_config"] = True

    for name, vals in policies.items():
        pol = vals.get("policy") or ""
        graph["bucket_policy_principals"][name] = "cloudfront.amazonaws.com" in pol and "*" not in pol.split("Principal")[1][:80] if "Principal" in pol else False
        if isinstance(vals.get("policy"), str):
            try:
                decoded = json.loads(vals["policy"])
                principals = []
                for stmt in decoded.get("Statement") or []:
                    p = stmt.get("Principal")
                    principals.append(p)
                graph["bucket_policy_principals"][name] = principals
            except json.JSONDecodeError:
                pass

    graph["buckets"] = list(buckets.keys())
    return graph


def _match_path(pattern: str, path: str) -> bool:
    if pattern.endswith("/*"):
        prefix = pattern[:-1]
        return path.startswith(prefix) or path == pattern[:-2]
    return path == pattern


def select_rule(rules: list[dict], distribution: str, path: str) -> dict | None:
    candidates = [r for r in rules if r.get("distribution") == distribution]
    candidates.sort(key=lambda r: int(r.get("priority", 999)))
    for rule in candidates:
        if _match_path(rule["path"], path):
            return rule
    return None


@dataclass
class LabState:
    graph: dict
    cache: dict = field(default_factory=dict)
    rate: dict = field(default_factory=dict)
    cache_events: list = field(default_factory=list)
    rate_events: list = field(default_factory=list)
    origin_hits: list = field(default_factory=list)
    clock: date = field(default_factory=lambda: date(2026, 8, 6))


class OriginHandler(BaseHTTPRequestHandler):
    origin_id = "unknown"
    requires_auth = False
    auth_header = ("", "")
    requires_oac = False

    def log_message(self, fmt: str, *args) -> None:  # noqa: A003
        return

    def do_GET(self) -> None:  # noqa: N802
        if self.requires_auth:
            name, value = self.auth_header
            if self.headers.get(name) != value:
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"missing origin auth")
                return
        if self.requires_oac and self.headers.get("X-Edge-OAC") != "1":
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"missing origin access identity")
            return
        body = f"origin={self.origin_id};path={self.path}".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _make_origin(origin_id: str, requires_auth=False, auth=("", ""), requires_oac=False):
    class H(OriginHandler):
        pass

    H.origin_id = origin_id
    H.requires_auth = requires_auth
    H.auth_header = auth
    H.requires_oac = requires_oac
    return H


class EdgeHandler(BaseHTTPRequestHandler):
    state: LabState
    distribution: str
    origins: dict[str, str]

    def log_message(self, fmt: str, *args) -> None:  # noqa: A003
        return

    def do_GET(self) -> None:  # noqa: N802
        self._handle()

    def do_POST(self) -> None:  # noqa: N802
        self._handle()

    def _handle(self) -> None:
        st = self.state
        inv = st.graph["inventory"]
        path = urlparse(self.path).path
        client = self.client_address[0]
        rule = select_rule(inv["path_rules"], self.distribution, path)
        if rule is None:
            self._respond(404, b"no rule")
            return

        methods = set(rule.get("allowed_methods") or ["GET", "HEAD"])
        if self.command not in methods:
            self._respond(405, b"method not allowed")
            return

        # Rate window
        limit = 2000
        for rr in inv["waf_policy"].get("rate_based_rules") or []:
            limit = int(rr.get("limit", limit))
        key = f"{self.distribution}:{client}"
        window = st.rate.setdefault(key, [])
        now = time.time()
        st.rate[key] = [t for t in window if now - t < 60]
        st.rate[key].append(now)
        if len(st.rate[key]) > limit:
            st.rate_events.append({"dist": self.distribution, "client": client, "action": "block"})
            self._respond(429, b"rate limited")
            return

        # Signed access
        if rule.get("signed"):
            approved = [
                e
                for e in inv["exception_requests"]
                if e.get("status") == "approved"
                and e.get("distribution") == self.distribution
                and _match_path(e["path_pattern"], path)
                and date.fromisoformat(e["expires_on"]) >= st.clock
            ]
            if not approved:
                self._respond(403, b"no approved exception")
                return
            if self.headers.get("X-Edge-Signature") != "valid":
                self._respond(403, b"signature required")
                return
        else:
            if self.headers.get("X-Edge-Signature") == "valid" and path.startswith("/private/"):
                # neighboring signed trust must not leak
                if not any(
                    _match_path(e["path_pattern"], path)
                    for e in inv["exception_requests"]
                    if e.get("status") == "approved"
                ):
                    self._respond(403, b"unsigned path")
                    return

        if st.graph.get("signed_trusted_on_default") and rule.get("path") == "/*":
            self._respond(500, b"default signed trust misconfigured")
            return

        origin_id = rule["origin_id"]
        origin_meta = next(o for o in inv["origins"] if o["origin_id"] == origin_id)
        cache_mode = rule.get("cache_policy") or ""
        no_cache = cache_mode in {"no-cache", "api-no-cache"} or origin_id in {"api", "maintenance"}

        # Cache key isolates origin class + path + method
        origin_class = "private-api" if origin_id == "api" else ("object" if origin_meta.get("type") == "s3" else "custom")
        ckey = f"{self.distribution}|{origin_class}|{self.command}|{path}"
        if not no_cache and ckey in st.cache:
            st.cache_events.append({"event": "HIT", "key": ckey, "origin": origin_id})
            body, headers = st.cache[ckey]
            self._respond(200, body, headers)
            return

        # Origin fetch
        import urllib.request

        req = urllib.request.Request(self.origins[origin_id] + path, method=self.command)
        if origin_meta.get("custom_header_name"):
            # Only when this origin is selected
            req.add_header(origin_meta["custom_header_name"], origin_meta["custom_header_value"])
        if origin_meta.get("requires_oac"):
            if not st.graph.get("oac_present") or st.graph.get("has_s3_origin_config"):
                self._respond(502, b"origin identity missing")
                return
            req.add_header("X-Edge-OAC", "1")

        try:
            with urllib.request.urlopen(req, timeout=2) as resp:
                body = resp.read()
        except Exception as exc:  # noqa: BLE001
            self._respond(502, str(exc).encode())
            return

        st.origin_hits.append({"dist": self.distribution, "origin": origin_id, "path": path})
        headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "same-origin",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "X-Cache": "MISS",
            "X-Origin": origin_id,
        }
        if not st.graph.get("headers_ok"):
            # still attach minimal; probes check presence when plan says ok
            pass
        if not no_cache:
            st.cache[ckey] = (body, {**headers, "X-Cache": "HIT"})
            st.cache_events.append({"event": "STORE", "key": ckey, "origin": origin_id})
        else:
            st.cache_events.append({"event": "BYPASS", "key": ckey, "origin": origin_id})

        self._respond(200, body, headers)

    def _respond(self, code: int, body: bytes, headers: dict | None = None) -> None:
        self.send_response(code)
        headers = headers or {"Content-Type": "text/plain"}
        for k, v in headers.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def start_lab(graph: dict, base_port: int = 18080) -> tuple[LabState, dict[str, ThreadingHTTPServer], dict[str, str]]:
    state = LabState(graph=graph)
    servers: dict[str, ThreadingHTTPServer] = {}
    urls: dict[str, str] = {}

    origin_specs = [
        ("api", True, ("X-Edge-Auth", "edge-token-claims"), False),
        ("maintenance", False, ("", ""), False),
        ("s3-static", False, ("", ""), True),
        ("failover-static", False, ("", ""), True),
    ]
    for idx, (oid, auth, hdr, oac) in enumerate(origin_specs):
        handler = _make_origin(oid, auth, hdr, oac)
        srv = ThreadingHTTPServer(("127.0.0.1", base_port + idx), handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        servers[oid] = srv
        urls[oid] = f"http://127.0.0.1:{base_port + idx}"

    edge_urls = {}
    for idx, dist in enumerate(["static-api", "failover", "signed-content"]):
        class H(EdgeHandler):
            pass

        H.state = state
        H.distribution = dist
        H.origins = urls
        port = base_port + 20 + idx
        srv = ThreadingHTTPServer(("127.0.0.1", port), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        servers[f"edge-{dist}"] = srv
        edge_urls[dist] = f"http://127.0.0.1:{port}"

    time.sleep(0.2)
    return state, servers, edge_urls


def stop_lab(servers: dict[str, ThreadingHTTPServer]) -> None:
    for srv in servers.values():
        srv.shutdown()


def run_probes(edge_urls: dict[str, str], state: LabState) -> list[dict]:
    import urllib.error
    import urllib.request

    results = []

    def fetch(url: str, headers: dict | None = None, method: str = "GET") -> tuple[int, dict, bytes]:
        req = urllib.request.Request(url, method=method, headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=2) as resp:
                return resp.status, dict(resp.headers), resp.read()
        except urllib.error.HTTPError as exc:
            return exc.code, dict(exc.headers), exc.read()

    # API must bypass cache across repeated GETs with distinct body class from static
    code, hdrs, body1 = fetch(edge_urls["static-api"] + "/api/claims/42")
    results.append({"name": "api_first", "ok": code == 200 and b"origin=api" in body1, "code": code})
    code, hdrs, body_static = fetch(edge_urls["static-api"] + "/static/banner.html")
    results.append({"name": "static_fetch", "ok": code == 200 and b"origin=s3-static" in body_static, "code": code})
    code, hdrs, body2 = fetch(edge_urls["static-api"] + "/api/claims/42")
    # Must not return static body via cache collision
    results.append(
        {
            "name": "api_cache_isolation",
            "ok": code == 200 and b"origin=api" in body2 and b"s3-static" not in body2,
            "code": code,
        }
    )
    bypass = [e for e in state.cache_events if e.get("event") == "BYPASS" and "api" in e.get("key", "")]
    results.append({"name": "api_no_cache_store", "ok": len(bypass) >= 1, "code": 0})

    # Signed path
    code, _, _ = fetch(edge_urls["signed-content"] + "/private/downloads/pack.zip")
    results.append({"name": "signed_requires_sig", "ok": code == 403, "code": code})
    code, _, body = fetch(
        edge_urls["signed-content"] + "/private/downloads/pack.zip",
        headers={"X-Edge-Signature": "valid"},
    )
    results.append({"name": "signed_with_sig", "ok": code == 200 and b"s3-static" in body, "code": code})
    code, _, _ = fetch(
        edge_urls["signed-content"] + "/private/other.zip",
        headers={"X-Edge-Signature": "valid"},
    )
    results.append({"name": "signed_neighbor_denied", "ok": code in {403, 404}, "code": code})

    # Failover needs OAC
    code, _, body = fetch(edge_urls["failover"] + "/failover/index.html")
    expect_ok = state.graph.get("oac_present") and not state.graph.get("has_s3_origin_config")
    results.append(
        {
            "name": "failover_origin_identity",
            "ok": (code == 200 and expect_ok) or (code == 502 and not expect_ok),
            "code": code,
            "expect_ok": expect_ok,
        }
    )

    # Security headers on static
    code, hdrs, _ = fetch(edge_urls["static-api"] + "/static/banner.html")
    results.append(
        {
            "name": "security_headers",
            "ok": hdrs.get("X-Frame-Options") == "DENY" and hdrs.get("Referrer-Policy") == "same-origin",
            "code": code,
        }
    )

    # TLS posture from plan
    tls_ok = all(
        v == "TLSv1.2_2021" for v in (state.graph.get("tls") or {}).values()
    ) and bool(state.graph.get("tls"))
    results.append({"name": "tls_plan", "ok": tls_ok, "code": 0})

    # Headers policy from plan
    results.append({"name": "headers_plan", "ok": bool(state.graph.get("headers_ok")), "code": 0})

    # Logging host form
    logs_ok = all(
        (h or "").endswith(".s3.amazonaws.com")
        for h in (state.graph.get("logging_hosts") or {}).values()
    ) and bool(state.graph.get("logging_hosts"))
    results.append({"name": "logging_hosts", "ok": logs_ok, "code": 0})

    return results


def write_evidence(plan: dict, graph: dict, probe_results: list[dict], state: LabState) -> dict:
    VAR.mkdir(parents=True, exist_ok=True)
    digest = plan_digest(plan)
    status = "READY" if all(p.get("ok") for p in probe_results) else "FAILED"
    evidence = {
        "status": status,
        "plan_digest": digest,
        "probe_results": probe_results,
        "cache_events": state.cache_events[-50:],
        "rate_events": state.rate_events[-50:],
        "oac_present": graph.get("oac_present"),
        "evidence_digest": "",
    }
    stable = {k: evidence[k] for k in ("status", "plan_digest", "probe_results", "oac_present")}
    evidence["evidence_digest"] = hashlib.sha256(
        json.dumps(stable, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    (VAR / "cutover-evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    (VAR / "plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    return evidence
