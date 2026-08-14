"""Projected read-only workspace and bubblewrap sandbox for LOCAL_COMMAND."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from retrieval.indexer import RepositoryIndexer
from retrieval.policy import ALL_ROLES, ALL_STAGES, RetrievalPolicy

_MUTATING_ROLE_CLASSES = frozenset({"PRODUCER", "FIXER"})
_RUNTIME_ROOTS = (Path("/usr"), Path("/bin"), Path("/lib"), Path("/lib64"), Path("/usr/local"))


class SandboxUnavailable(RuntimeError):
    """Raised when LOCAL_COMMAND cannot be isolated safely."""


@dataclass
class SandboxProjection:
    workspace: Path
    wrapped_argv: list[str]
    projection_hash: str
    authorized_file_count: int
    backend: str = "BWRAP"


class LocalExecutorSandbox:
    """Build an evidence-aware read-only workspace and bwrap command."""

    def __init__(self, root: Path, policy: RetrievalPolicy | None = None):
        self.root = root.resolve()
        self.policy = policy or RetrievalPolicy(self.root)
        self._tmp: tempfile.TemporaryDirectory[str] | None = None

    def prepare(
        self,
        invocation: Mapping[str, Any],
        argv: Sequence[str],
    ) -> SandboxProjection:
        stage = invocation["stage"]
        if str(stage.get("role_class")) in _MUTATING_ROLE_CLASSES:
            raise ValueError(
                "LOCAL_COMMAND is read-only and unavailable for PRODUCER/FIXER stages; use MANUAL_CHAT"
            )
        if platform.system() != "Linux":
            raise SandboxUnavailable(
                "LOCAL_COMMAND requires Linux bubblewrap; use WSL/Linux or MANUAL_CHAT"
            )
        bwrap = shutil.which("bwrap")
        if not bwrap:
            raise SandboxUnavailable(
                "LOCAL_COMMAND requires bubblewrap (bwrap); no unsafe fallback is permitted"
            )

        self._tmp = tempfile.TemporaryDirectory(prefix="terminus-executor-")
        workspace = Path(self._tmp.name).resolve()
        entries = self._project_authorized_files(invocation, workspace)
        wrapped = self._bubblewrap_argv(bwrap, workspace, argv)
        projection_hash = hashlib.sha256(
            json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return SandboxProjection(
            workspace=workspace,
            wrapped_argv=wrapped,
            projection_hash=projection_hash,
            authorized_file_count=len(entries),
        )

    def close(self) -> None:
        if self._tmp is not None:
            self._tmp.cleanup()
            self._tmp = None

    def _project_authorized_files(
        self,
        invocation: Mapping[str, Any],
        workspace: Path,
    ) -> list[tuple[str, str]]:
        authority = invocation["authority"]
        stage = invocation["stage"]
        evidence = invocation["evidence"]
        task_id = str(authority.get("task_id", ""))
        task_commit = str(authority.get("task_commit", ""))
        control_commit = str(authority["control_plane_commit"])
        allowed = set(evidence["authorized_evidence_classes"])
        mode = str(evidence["retrieval_mode"])
        stage_id = str(stage["stage_id"])
        role_id = str(stage["role_id"])
        entries: list[tuple[str, str]] = []

        for relative in evidence.get("mandatory_exact_reads", []):
            data = self._git_bytes(control_commit, str(relative))
            self._write(workspace, str(relative), data)
            entries.append((str(relative), hashlib.sha256(data).hexdigest()))

        task_root = self._find_task_root(task_commit, task_id) if task_id and task_commit else None
        indexer = RepositoryIndexer(self.root, None, self.policy)  # classification only
        if task_root:
            for relative in self._tracked_paths(task_commit):
                source_kind = indexer.classify_path(
                    relative,
                    task_path=task_root,
                    include_private_design=True,
                )
                if not source_kind:
                    continue
                profile = self.policy.source_profiles[source_kind]
                if profile["default_evidence_class"] not in allowed:
                    continue
                if mode == "SOLVER_VISIBLE_ONLY" and profile["default_solver_visible"] is not True:
                    continue
                stages = set(indexer._stage_applicability(source_kind))
                if ALL_STAGES not in stages and stage_id not in stages:
                    continue
                roles = set(indexer._role_applicability(source_kind))
                if ALL_ROLES not in roles and role_id not in roles:
                    continue
                data = self._git_bytes(task_commit, relative)
                self._write(workspace, relative, data)
                entries.append((relative, hashlib.sha256(data).hexdigest()))

        for item in invocation.get("retrieval", {}).get("retrieved_context", []):
            if not isinstance(item, Mapping):
                continue
            path = item.get("source_path")
            content = item.get("content")
            if isinstance(path, str) and isinstance(content, str):
                target = workspace / PurePosixPath(path)
                if not target.exists():
                    data = content.encode("utf-8")
                    self._write(workspace, path, data)
                    entries.append((path, hashlib.sha256(data).hexdigest()))

        return sorted(set(entries))

    def _find_task_root(self, commit: str, task_id: str) -> str | None:
        candidates: set[str] = set()
        for relative in self._tracked_paths(commit):
            path = PurePosixPath(relative)
            if path.name == "instruction.md" and path.parent.name == task_id:
                candidates.add(path.parent.as_posix())
        if len(candidates) > 1:
            raise ValueError(f"multiple task roots found for {task_id}: {sorted(candidates)}")
        return next(iter(candidates)) if candidates else None

    def _bubblewrap_argv(
        self,
        bwrap: str,
        workspace: Path,
        argv: Sequence[str],
    ) -> list[str]:
        if not argv:
            raise ValueError("LOCAL_COMMAND requires non-empty argv")
        executable = self._resolve_executable(argv[0])
        normalized = [str(executable), *argv[1:]]
        for item in normalized[1:]:
            if not isinstance(item, str) or not item:
                raise ValueError("LOCAL_COMMAND argv entries must be non-empty strings")
            candidate = Path(item)
            if candidate.is_absolute():
                resolved = candidate.resolve()
                if resolved.is_relative_to(self.root):
                    raise ValueError(
                        "LOCAL_COMMAND arguments may not reference the authoritative repository"
                    )
                if not self._under_runtime_root(resolved):
                    raise ValueError(
                        "LOCAL_COMMAND absolute argument paths must be inside the projected workspace or system runtime roots"
                    )

        command = [
            bwrap,
            "--die-with-parent",
            "--new-session",
            "--unshare-all",
        ]
        for runtime_root in _RUNTIME_ROOTS:
            if runtime_root.exists():
                command += ["--ro-bind", str(runtime_root), str(runtime_root)]
        command += [
            "--dir",
            "/workspace",
            "--ro-bind",
            str(workspace),
            "/workspace",
            "--tmpfs",
            "/tmp",
            "--chdir",
            "/workspace",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--",
            *normalized,
        ]
        return command

    def _resolve_executable(self, value: str) -> Path:
        if not isinstance(value, str) or not value:
            raise ValueError("LOCAL_COMMAND executable must be a non-empty string")
        raw = Path(value)
        resolved_value = shutil.which(value) if not raw.is_absolute() else value
        if not resolved_value:
            raise ValueError(f"LOCAL_COMMAND executable not found: {value}")
        resolved = Path(resolved_value).resolve()
        if not self._under_runtime_root(resolved):
            raise ValueError(
                "LOCAL_COMMAND executable must resolve under /usr, /bin, /lib, /lib64, or /usr/local"
            )
        return resolved

    @staticmethod
    def _under_runtime_root(path: Path) -> bool:
        return any(path == root or path.is_relative_to(root) for root in _RUNTIME_ROOTS if root.exists())

    def _tracked_paths(self, commit: str) -> list[str]:
        return subprocess.run(
            ["git", "-C", str(self.root), "ls-tree", "-r", "--name-only", commit],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()

    def _git_bytes(self, commit: str, relative: str) -> bytes:
        return subprocess.run(
            ["git", "-C", str(self.root), "show", f"{commit}:{relative}"],
            check=True,
            capture_output=True,
        ).stdout

    @staticmethod
    def _write(workspace: Path, relative: str, data: bytes) -> None:
        target = (workspace / PurePosixPath(relative)).resolve()
        if not target.is_relative_to(workspace):
            raise ValueError(f"workspace path escapes projection: {relative}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        os.chmod(target, 0o444)
