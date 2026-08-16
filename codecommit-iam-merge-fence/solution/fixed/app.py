from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from cc.errors import CcError
from cc.iam import actions as iam_actions
from cc.pipelines.deliver import deliver
from cc.prs import approvals, merge, store as pr_store
from cc.repos import catalog, gitops
from cc.services import authz_gateway, metrics
from cc.util import full_ref
from cc.webhooks.dispatch import dispatch_pending


def _read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length") or 0)
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    return json.loads(raw.decode() or "{}")


class Handler(BaseHTTPRequestHandler):
    fixed: bool = False

    def log_message(self, fmt: str, *args: object) -> None:
        return

    def _send(self, code: int, body: dict[str, Any]) -> None:
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _auth_headers(self) -> tuple[str, bool, str]:
        principal = self.headers.get("X-Principal") or ""
        mfa = (self.headers.get("X-MFA") or "").lower() in ("1", "true", "yes")
        source_ip = self.headers.get("X-Source-Ip") or "127.0.0.1"
        return principal, mfa, source_ip

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            if path == "/health":
                self._send(200, {"ok": True})
                return
            if path == "/repos":
                self._send(200, {"repos": catalog.list_repos()})
                return
            if path == "/metrics":
                self._send(200, metrics.snapshot())
                return
            if path.startswith("/prs/"):
                pr_id = int(path.rsplit("/", 1)[-1])
                pr = pr_store.get(pr_id)
                self._send(200, pr.to_dict())
                return
            self._send(404, {"error": "NotFound"})
        except CcError as exc:
            self._send(403 if exc.error == "AccessDenied" else 400, exc.to_dict())

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        body = _read_json(self)
        principal, mfa, source_ip = self._auth_headers()
        fixed = True
        try:
            if path == "/repos":
                name = str(body.get("name"))
                catalog.upsert_repo(name, default_branch=str(body.get("default_branch") or "main"))
                gitops.ensure_bare(name)
                self._send(200, catalog.get_repo(name) or {})
                return
            if path.endswith("/push") and path.startswith("/repos/"):
                repo = path.split("/")[2]
                ref = full_ref(str(body.get("ref") or "main"))
                worktree = str(body.get("worktree"))
                authz_gateway.gated_authorize(
                    principal,
                    iam_actions.GIT_PUSH,
                    repo,
                    ref,
                    mfa=mfa,
                    source_ip=source_ip,
                    fixed=True,
                )
                commit = gitops.push(repo, Path(worktree), ref)
                self._send(200, {"ok": True, "repo": repo, "ref": ref, "commit": commit})
                return
            if path == "/prs":
                repo = str(body["repo"])
                source = str(body["source"])
                dest = str(body["dest"])
                authz_gateway.gated_authorize(
                    principal,
                    iam_actions.GIT_PULL,
                    repo,
                    source,
                    mfa=mfa,
                    source_ip=source_ip,
                    fixed=True,
                )
                src_commit = gitops.ref_commit(repo, source)
                pr = pr_store.create(repo, source, dest, src_commit, principal)
                self._send(200, pr.to_dict())
                return
            if path.endswith("/approve"):
                pr_id = int(path.split("/")[2])
                self._send(200, approvals.approve(pr_id, principal, fixed=True))
                return
            if path.endswith("/merge"):
                pr_id = int(path.split("/")[2])
                self._send(
                    200,
                    merge.merge(pr_id, principal, mfa=mfa, source_ip=source_ip, fixed=True),
                )
                return
            if path == "/deliver":
                self._send(200, deliver(str(body["repo"]), str(body["ref"]), fixed=True))
                return
            if path == "/webhooks/dispatch":
                self._send(200, {"ok": True, "results": dispatch_pending(fixed=True, sink=[])})
                return
            self._send(404, {"error": "NotFound"})
        except CcError as exc:
            self._send(403 if exc.error == "AccessDenied" else 400, exc.to_dict())
        except Exception as exc:  # noqa: BLE001
            self._send(500, {"error": "InternalError", "message": str(exc)})


def serve(host: str = "127.0.0.1", port: int = 8080, *, fixed: bool = False) -> ThreadingHTTPServer:
    fixed = True
    Handler.fixed = fixed
    httpd = ThreadingHTTPServer((host, port), Handler)
    return httpd


def main() -> None:
    import os

    host = os.environ.get("CC_API_HOST", "127.0.0.1")
    port = int(os.environ.get("CC_API_PORT", "8080"))
    httpd = serve(host, port, fixed=True)
    print(json.dumps({"ok": True, "listen": f"{host}:{port}", "fixed": True}))
    httpd.serve_forever()


if __name__ == "__main__":
    main()
