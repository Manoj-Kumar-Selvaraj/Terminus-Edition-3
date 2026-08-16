#!/usr/bin/env python3
"""Generate codecommit-iam-merge-fence large_system_strict control plane.

Writes solver-visible environment (broken starter) and solution/fixed modules.
Run from Terminus-Edition-3 root:
  python _gen_codecommit_strict.py
"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent / "codecommit-iam-merge-fence"
ENV = ROOT / "environment" / "codecommit"
FIXED = ROOT / "solution" / "fixed"


def w(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(body).lstrip("\n"), encoding="utf-8")


def gen_core() -> None:
    w(
        ENV / "lib" / "cc" / "__init__.py",
        '''
        """Local CodeCommit platform control plane."""
        __version__ = "2.0.0"
        ''',
    )
    w(
        ENV / "lib" / "cc" / "home.py",
        '''
        from __future__ import annotations

        import os
        from pathlib import Path


        def root() -> Path:
            return Path(os.environ.get("CC_ROOT", "/app/codecommit")).resolve()


        def lib_dir() -> Path:
            return root() / "lib"


        def ops_dir() -> Path:
            return root() / "ops"


        def policies_dir() -> Path:
            return root() / "policies"


        def var_dir() -> Path:
            return root() / "var"


        def repos_dir() -> Path:
            return var_dir() / "repos"


        def docs_dir() -> Path:
            return root() / "docs"


        def log_dir() -> Path:
            return root() / "log"


        def principals_path() -> Path:
            return ops_dir() / "principals.json"


        def approval_rules_path() -> Path:
            return ops_dir() / "approval-rules.json"


        def pipelines_path() -> Path:
            return ops_dir() / "pipelines.json"


        def webhooks_path() -> Path:
            return ops_dir() / "webhooks.json"


        def catalog_path() -> Path:
            return var_dir() / "catalog.json"


        def prs_path() -> Path:
            return var_dir() / "prs.json"


        def triggers_path() -> Path:
            return var_dir() / "triggers.jsonl"


        def audit_path() -> Path:
            return var_dir() / "audit.jsonl"


        def outbox_path() -> Path:
            return var_dir() / "outbox.jsonl"


        def bare_repo(name: str) -> Path:
            return repos_dir() / f"{name}.git"


        def ensure_layout() -> None:
            for p in (ops_dir(), policies_dir(), var_dir(), repos_dir(), docs_dir(), log_dir()):
                p.mkdir(parents=True, exist_ok=True)
        ''',
    )
    w(
        ENV / "lib" / "cc" / "errors.py",
        '''
        from __future__ import annotations

        import json
        from typing import Any


        class CcError(Exception):
            def __init__(self, error: str, code: str | None = None, **extra: Any) -> None:
                self.error = error
                self.code = code
                self.extra = extra
                super().__init__(error if code is None else f"{error}:{code}")

            def to_dict(self) -> dict[str, Any]:
                body: dict[str, Any] = {"error": self.error}
                if self.code is not None:
                    body["code"] = self.code
                body.update(self.extra)
                return body

            def to_json(self) -> str:
                return json.dumps(self.to_dict(), separators=(",", ":"))


        class AccessDenied(CcError):
            def __init__(self, code: str | None = None, **extra: Any) -> None:
                super().__init__("AccessDenied", code=code, **extra)


        class ValidationException(CcError):
            def __init__(self, code: str, **extra: Any) -> None:
                super().__init__("ValidationException", code=code, **extra)
        ''',
    )
    w(
        ENV / "lib" / "cc" / "util.py",
        '''
        from __future__ import annotations

        import ipaddress
        import json
        import os
        import subprocess
        from pathlib import Path
        from typing import Any, Iterable


        GIT_ENV = {
            "GIT_AUTHOR_NAME": "CodeCommit Lab",
            "GIT_AUTHOR_EMAIL": "lab@local",
            "GIT_COMMITTER_NAME": "CodeCommit Lab",
            "GIT_COMMITTER_EMAIL": "lab@local",
            "GIT_AUTHOR_DATE": "2026-04-01T12:00:00+0000",
            "GIT_COMMITTER_DATE": "2026-04-01T12:00:00+0000",
            "GIT_TERMINAL_PROMPT": "0",
        }


        def full_ref(branch: str) -> str:
            branch = branch.strip()
            if branch.startswith("refs/"):
                return branch
            return f"refs/heads/{branch}"


        def short_ref(ref: str) -> str:
            ref = full_ref(ref)
            prefix = "refs/heads/"
            return ref[len(prefix) :] if ref.startswith(prefix) else ref


        def ip_in_cidrs(addr: str, cidrs: Iterable[str]) -> bool:
            try:
                ip = ipaddress.ip_address(addr)
            except ValueError:
                return False
            for c in cidrs:
                try:
                    if ip in ipaddress.ip_network(c, strict=False):
                        return True
                except ValueError:
                    continue
            return False


        def load_json(path: Path, default: Any) -> Any:
            if not path.exists():
                return default
            return json.loads(path.read_text(encoding="utf-8"))


        def dump_json(path: Path, data: Any) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\\n", encoding="utf-8")


        def append_jsonl(path: Path, row: dict[str, Any]) -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, separators=(",", ":")) + "\\n")


        def read_jsonl(path: Path) -> list[dict[str, Any]]:
            if not path.exists():
                return []
            rows: list[dict[str, Any]] = []
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
            return rows


        def run_git(args: list[str], cwd: Path | None = None, check: bool = True) -> str:
            env = os.environ.copy()
            env.update(GIT_ENV)
            cp = subprocess.run(
                ["git", *args],
                cwd=str(cwd) if cwd else None,
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            if check and cp.returncode != 0:
                raise RuntimeError(f"git {args} failed: {cp.stderr or cp.stdout}")
            return (cp.stdout or "").strip()
        ''',
    )
    w(
        ENV / "lib" / "cc" / "models.py",
        '''
        from __future__ import annotations

        from dataclasses import asdict, dataclass, field
        from typing import Any


        @dataclass
        class Principal:
            name: str
            policies: list[str]
            roles: list[str] = field(default_factory=list)

            @classmethod
            def from_dict(cls, name: str, raw: dict[str, Any]) -> "Principal":
                return cls(
                    name=name,
                    policies=list(raw.get("policies") or []),
                    roles=list(raw.get("roles") or []),
                )


        @dataclass
        class AuthContext:
            principal: str
            action: str
            resource_arn: str
            reference: str
            mfa: bool
            source_ip: str

            def as_eval_map(self) -> dict[str, Any]:
                return {
                    "aws:MultiFactorAuthPresent": self.mfa,
                    "aws:SourceIp": self.source_ip,
                    "codecommit:References": self.reference,
                }


        @dataclass
        class PullRequest:
            pr_id: int
            repo: str
            source: str
            dest: str
            source_commit: str
            author: str
            status: str
            approvals: list[str] = field(default_factory=list)
            merged_commit: str | None = None

            def to_dict(self) -> dict[str, Any]:
                return asdict(self)


        @dataclass
        class AuditEvent:
            principal: str
            action: str
            resource: str
            reference: str
            allowed: bool
            reason: str
            source_ip: str
            mfa: bool

            def to_row(self) -> dict[str, Any]:
                return asdict(self)


        @dataclass
        class OutboxItem:
            event_id: str
            repo: str
            ref: str
            commit: str
            pipeline: str
            webhook_id: str
            status: str
            attempts: int = 0
            last_error: str | None = None

            def to_row(self) -> dict[str, Any]:
                return asdict(self)
        ''',
    )


def gen_store() -> None:
    w(
        ENV / "lib" / "cc" / "store" / "__init__.py",
        '''
        from cc.store.jsonstore import JsonStore
        from cc.store.lock import FileLock

        __all__ = ["JsonStore", "FileLock"]
        ''',
    )
    w(
        ENV / "lib" / "cc" / "store" / "lock.py",
        '''
        from __future__ import annotations

        import os
        import time
        from pathlib import Path


        class FileLock:
            """Best-effort exclusive lock using a lockfile beside the target."""

            def __init__(self, target: Path, timeout_sec: float = 10.0) -> None:
                self.target = target
                self.lock_path = target.with_suffix(target.suffix + ".lock")
                self.timeout_sec = timeout_sec
                self._fd: int | None = None

            def acquire(self) -> None:
                self.lock_path.parent.mkdir(parents=True, exist_ok=True)
                deadline = time.time() + self.timeout_sec
                while True:
                    try:
                        self._fd = os.open(str(self.lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                        os.write(self._fd, str(os.getpid()).encode())
                        return
                    except FileExistsError:
                        if time.time() >= deadline:
                            raise TimeoutError(f"lock timeout: {self.lock_path}")
                        time.sleep(0.05)

            def release(self) -> None:
                if self._fd is not None:
                    os.close(self._fd)
                    self._fd = None
                try:
                    self.lock_path.unlink(missing_ok=True)
                except OSError:
                    pass

            def __enter__(self) -> "FileLock":
                self.acquire()
                return self

            def __exit__(self, *args: object) -> None:
                self.release()
        ''',
    )
    w(
        ENV / "lib" / "cc" / "store" / "jsonstore.py",
        '''
        from __future__ import annotations

        from pathlib import Path
        from typing import Any, Callable

        from cc.store.lock import FileLock
        from cc.util import dump_json, load_json


        class JsonStore:
            def __init__(self, path: Path, default_factory: Callable[[], Any]) -> None:
                self.path = path
                self.default_factory = default_factory

            def read(self) -> Any:
                return load_json(self.path, self.default_factory())

            def write(self, data: Any) -> None:
                with FileLock(self.path):
                    dump_json(self.path, data)

            def update(self, mutator: Callable[[Any], Any]) -> Any:
                with FileLock(self.path):
                    data = load_json(self.path, self.default_factory())
                    data = mutator(data)
                    dump_json(self.path, data)
                    return data
        ''',
    )


# Continue in next write for IAM - the file is getting long; I'll append via StrReplace or second script section
print("core+store helpers defined")
