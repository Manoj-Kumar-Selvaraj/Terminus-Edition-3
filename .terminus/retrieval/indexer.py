"""Commit-bound repository indexing for the Terminus retrieval engine."""

from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from .chunking import chunk_text
from .policy import ALL_ROLES, ALL_STAGES, RetrievalPolicy
from .store import RetrievalStore

_CODE_SUFFIXES = {
    ".py", ".sh", ".bash", ".go", ".java", ".js", ".ts", ".tsx", ".jsx",
    ".rb", ".rs", ".c", ".cc", ".cpp", ".h", ".hpp", ".cs", ".kt", ".kts",
    ".scala", ".php", ".pl", ".ps1", ".groovy", ".cob", ".cbl",
}
_DOC_SUFFIXES = {".md", ".rst", ".adoc", ".txt"}


class RepositoryIndexer:
    """Build a local index from immutable Git blobs, never dirty working-tree text."""

    def __init__(
        self,
        root: Path,
        store: RetrievalStore,
        policy: RetrievalPolicy | None = None,
    ):
        self.root = root.resolve()
        self.store = store
        self.policy = policy or RetrievalPolicy(self.root)

    def build(
        self,
        *,
        task_path: str | None = None,
        task_id: str | None = None,
        commit: str | None = None,
        include_private_design: bool = False,
    ) -> dict[str, Any]:
        control_plane_commit = commit or self._git("rev-parse", "HEAD").strip()
        task_commit = control_plane_commit if task_path else None
        if task_path and not task_id:
            task_id = PurePosixPath(task_path.rstrip("/")).name

        tracked = self._git("ls-tree", "-r", "--name-only", control_plane_commit).splitlines()
        selected: list[tuple[str, str]] = []
        for relative in tracked:
            source_kind = self.classify_path(
                relative,
                task_path=task_path,
                include_private_design=include_private_design,
            )
            if source_kind:
                selected.append((relative, source_kind))

        document_summaries: list[tuple[str, str, str]] = []
        source_kind_counts: Counter[str] = Counter()
        evidence_class_counts: Counter[str] = Counter()
        chunk_count = 0

        for relative, source_kind in selected:
            result = self.index_git_file(
                relative,
                source_kind,
                control_plane_commit=control_plane_commit,
                task_id=task_id,
                task_commit=task_commit,
            )
            if result is None:
                continue
            document_id, document_hash, chunks = result
            document_summaries.append((relative, document_id, document_hash))
            source_kind_counts[source_kind] += len(chunks)
            evidence_class = self.policy.source_profiles[source_kind][
                "default_evidence_class"
            ]
            evidence_class_counts[evidence_class] += len(chunks)
            chunk_count += len(chunks)

        source_set_hash = self._hash_json(sorted(document_summaries))
        manifest: dict[str, Any] = {
            "manifest_version": "1.0",
            "metadata_contract_version": self.policy.metadata_registry[
                "metadata_contract_version"
            ],
            "evidence_visibility_version": self.policy.visibility_registry[
                "visibility_version"
            ],
            "control_plane_commit": control_plane_commit,
            "source_set_hash": f"sha256:{source_set_hash}",
            "index_scope": "MIXED_AUTHORIZED" if task_path else "CONTROL_PLANE",
            "chunk_count": chunk_count,
            "document_count": len(document_summaries),
            "source_kind_counts": dict(sorted(source_kind_counts.items())),
            "evidence_class_counts": dict(sorted(evidence_class_counts.items())),
            "backend": "sqlite",
            "embedding_model": "pluggable:hashing-default",
            "lexical_index_version": "fts5-or-python-bm25-v1",
        }
        if task_path:
            manifest["task_id"] = task_id
            manifest["task_commit"] = task_commit
        manifest_id = f"manifest_{self._hash_json(manifest)}"
        self.store.put_manifest(manifest_id, manifest)
        return manifest

    def index_git_file(
        self,
        relative: str,
        source_kind: str,
        *,
        control_plane_commit: str,
        task_id: str | None,
        task_commit: str | None,
    ) -> tuple[str, str, list[tuple[dict[str, Any], str]]] | None:
        profile = self.policy.source_profiles[source_kind]
        blob_sha = self._git(
            "rev-parse", f"{control_plane_commit}:{relative}"
        ).strip()
        raw = subprocess.run(
            ["git", "-C", str(self.root), "show", f"{control_plane_commit}:{relative}"],
            check=True,
            capture_output=True,
        ).stdout
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            return None

        full_content_hash = hashlib.sha256(raw).hexdigest()
        source_uri = f"git://repository/{relative}"
        document_id = "doc_" + hashlib.sha256(
            f"{source_uri}\0{blob_sha}".encode()
        ).hexdigest()

        base: dict[str, Any] = {
            "metadata_contract_version": self.policy.metadata_registry[
                "metadata_contract_version"
            ],
            "document_id": document_id,
            "source_uri": source_uri,
            "source_path": relative,
            "source_kind": source_kind,
            "source_version": blob_sha,
            "git_blob_sha": blob_sha,
            "evidence_class": profile["default_evidence_class"],
            "sensitivity": profile["default_sensitivity"],
            "solver_visible": profile["default_solver_visible"],
            "stage_applicability": self._stage_applicability(source_kind),
            "role_applicability": self._role_applicability(source_kind),
            "freshness_scope": list(profile["required_freshness"]),
            "control_plane_commit": control_plane_commit,
        }
        if profile.get("task_scoped"):
            if not task_id or not task_commit:
                return None
            base["task_id"] = task_id
            base["task_commit"] = task_commit

        missing = [field for field in profile["required_bindings"] if not base.get(field)]
        if missing:
            return None

        document_meta = dict(base)
        document_meta["content_hash"] = f"sha256:{full_content_hash}"
        self.store.upsert_document(document_meta)

        strategy = profile["chunk_strategy"]
        raw_chunks = chunk_text(Path(relative), text, strategy)
        chunks: list[tuple[dict[str, Any], str]] = []
        for raw_chunk in raw_chunks:
            chunk_hash = hashlib.sha256(raw_chunk.content.encode("utf-8")).hexdigest()
            chunk_id = "chk_" + hashlib.sha256(
                f"{document_id}\0{raw_chunk.structural_locator}\0{chunk_hash}".encode()
            ).hexdigest()
            metadata = dict(base)
            metadata.update(
                {
                    "chunk_id": chunk_id,
                    "content_hash": f"sha256:{chunk_hash}",
                    "chunk_type": raw_chunk.chunk_type,
                    "structural_locator": raw_chunk.structural_locator,
                    "ordinal": raw_chunk.ordinal,
                }
            )
            if raw_chunk.section_path:
                metadata["section_path"] = list(raw_chunk.section_path)
            if raw_chunk.symbol:
                metadata["symbol"] = raw_chunk.symbol
            if raw_chunk.line_start is not None:
                metadata["line_start"] = raw_chunk.line_start
            if raw_chunk.line_end is not None:
                metadata["line_end"] = raw_chunk.line_end
            chunks.append((metadata, raw_chunk.content))
        self.store.replace_document_chunks(document_id, chunks)
        return document_id, full_content_hash, chunks

    def classify_path(
        self,
        relative: str,
        *,
        task_path: str | None,
        include_private_design: bool,
    ) -> str | None:
        path = PurePosixPath(relative)
        value = path.as_posix()
        selected_task = (
            PurePosixPath(task_path.rstrip("/")).name if task_path else None
        )

        if value.startswith(".terminus/cache/") or value.startswith(".terminus/retrieval/"):
            return None
        if value.startswith(".terminus/contracts/") and value.endswith(
            "/solver-visible-requirements.json"
        ):
            parts = path.parts
            if selected_task and len(parts) >= 4 and parts[2] == selected_task:
                return "SOLVER_VISIBLE_REQUIREMENT_CONTRACT"
            return None
        if include_private_design and value.startswith(".terminus/designs/"):
            if selected_task and path.name.startswith(selected_task):
                return "PRIVATE_DESIGN"
            return None
        if value.startswith(".terminus/reviews/") or value.startswith(
            ".terminus/sessions/"
        ):
            return None

        if self._is_control_plane(value):
            if path.suffix == ".md":
                return "CONTROL_PLANE_MARKDOWN"
            if path.suffix == ".json":
                return "CONTROL_PLANE_JSON"
            if path.suffix == ".py":
                return "CONTROL_PLANE_CODE"
            return None

        if task_path:
            task_prefix = task_path.rstrip("/") + "/"
            if value == task_path.rstrip("/") + "/instruction.md":
                return "TASK_INSTRUCTION"
            if value.startswith(task_prefix):
                inside = value[len(task_prefix) :]
                if inside.startswith("solution/"):
                    return "SOLUTION_ORACLE"
                if inside.startswith("tests/"):
                    return "VERIFIER_PRIVATE"
                if inside.startswith("environment/"):
                    if path.suffix in _DOC_SUFFIXES:
                        return "TASK_DOCUMENTATION"
                    if path.suffix in _CODE_SUFFIXES:
                        return "TASK_CODE"
                    return "TASK_CONFIGURATION"
                if path.name == "task.toml":
                    return "TASK_CONFIGURATION"
                if path.suffix in _DOC_SUFFIXES:
                    return "TASK_DOCUMENTATION"
        return None

    @staticmethod
    def _is_control_plane(value: str) -> bool:
        if value == "TERMINUS_3_AI_INSTRUCTIONS.md":
            return True
        if value == ".terminus/AGENT_SYSTEM.md":
            return True
        if value.startswith(".terminus/agents/"):
            return True
        if value.startswith(".terminus/reviewers/"):
            return True
        if value.startswith(".terminus/") and "/" not in value[len(".terminus/") :]:
            return value.endswith((".md", ".py", ".json"))
        return False

    @staticmethod
    def _stage_applicability(source_kind: str) -> list[str]:
        if source_kind == "SOLVER_VISIBLE_REQUIREMENT_CONTRACT":
            return ["INSTRUCTION_DRAFT", "SPEC_ALIGNMENT"]
        return [ALL_STAGES]

    @staticmethod
    def _role_applicability(source_kind: str) -> list[str]:
        if source_kind == "SOLVER_VISIBLE_REQUIREMENT_CONTRACT":
            return [
                "A7_INSTRUCTION_WRITER",
                "Q1_SPEC_GAP_REPAIRER",
                "Q3_SPEC_AMBIGUITY_REPAIRER",
                "CREATION_CONTROLLER",
            ]
        return [ALL_ROLES]

    def _git(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.root), *args],
            check=True,
            capture_output=True,
            text=True,
        ).stdout

    @staticmethod
    def _hash_json(value: Any) -> str:
        encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


def iter_text_files(paths: Iterable[Path]) -> Iterable[Path]:
    """Small utility retained for adapters that ingest non-Git evidence explicitly."""
    for path in paths:
        if path.is_file():
            yield path
