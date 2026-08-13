"""Explicit provenance-aware ingestion for dynamic retrieval evidence."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from .chunking import chunk_text
from .models import InvocationContext
from .policy import RetrievalPolicy
from .store import RetrievalStore

_REPOSITORY_DYNAMIC = frozenset({"REVIEW_PACKET", "REVIEW_RESULT", "SESSION_STATE"})
_EXTERNAL_DYNAMIC = frozenset({"CI_RUNTIME", "MODEL_TRIAL", "FINAL_PACKAGE", "PUBLIC_REFERENCE"})
_PRODUCER_ROLE_ALIASES = {
    "Spec-Test Contract Reviewer": "Q4_SPEC_TEST_CONTRACT_REVIEWER",
    "Production Logic Auditor": "Q6_PRODUCTION_LOGIC_AUDITOR",
}
_SESSION_POLICY_FIELDS = {
    "Agent-system policy": "agent_system",
    "Specialist prompt policy": "specialist_prompt",
    "Specialist protocol policy": "specialist_protocol",
    "Pre-LLMaJ panel policy": "pre_llmaj_panel",
    "Comprehensive reviewer policy": "comprehensive_reviewer",
}


class DynamicEvidenceIngestor:
    """Ingest only explicitly supplied dynamic evidence with truthful provenance."""

    def __init__(
        self,
        root: Path,
        store: RetrievalStore,
        policy: RetrievalPolicy | None = None,
    ):
        self.root = root.resolve()
        self.store = store
        self.policy = policy or RetrievalPolicy(self.root)

    def ingest_review_packet(
        self,
        *,
        source_path: str,
        source_commit: str,
        stage_id: str,
        role_ids: Sequence[str],
    ) -> dict[str, Any]:
        """Ingest one packet from an immutable Git blob and verify embedded bindings."""
        raw, blob_sha = self._read_git_blob(source_commit, source_path)
        payload = self._json_object(raw, "review packet")
        task_id = self._required_text(payload, "task")
        task_commit = self._required_sha(payload, "task_commit")
        control_plane_commit = self._required_sha(payload, "control_plane_commit")
        role_contract_hash = self._required_text(payload, "role_contract_hash")
        packet_binding = self._required_text(payload, "review_id")
        producer_role = self._producer_role(self._required_text(payload, "role"))

        expected_path = PurePosixPath(".terminus") / "reviews" / task_id
        path = PurePosixPath(source_path)
        if expected_path.as_posix() not in path.as_posix():
            raise ValueError("review packet path does not match embedded task")
        if path.name != f"{packet_binding}.packet.json":
            raise ValueError("review packet filename does not match review_id")

        roles = self._projection_roles(stage_id, role_ids)
        packet_consumers = {producer_role, "CI_ORCHESTRATOR"}
        if not set(roles).issubset(packet_consumers):
            raise ValueError(
                "review packet may be projected only to its reviewer role or CI_ORCHESTRATOR"
            )

        review_scope_hash = self._optional_text(payload, "review_scope_hash")
        return self._ingest(
            source_kind="REVIEW_PACKET",
            content=raw.decode("utf-8"),
            origin_source_uri=f"git://repository/{source_path}",
            source_version=blob_sha,
            source_path=source_path,
            git_blob_sha=blob_sha,
            stage_id=stage_id,
            role_ids=roles,
            task_id=task_id,
            task_commit=task_commit,
            control_plane_commit=control_plane_commit,
            role_contract_hash=role_contract_hash,
            packet_binding=packet_binding,
            review_scope_hash=review_scope_hash,
        )

    def ingest_review_result(
        self,
        *,
        source_path: str,
        source_commit: str,
        stage_id: str,
        role_ids: Sequence[str],
    ) -> dict[str, Any]:
        """Ingest one frozen review result while preserving its producer provenance."""
        raw, blob_sha = self._read_git_blob(source_commit, source_path)
        payload = self._json_object(raw, "review result")
        task_id = self._required_text(payload, "task")
        task_commit = self._required_sha(payload, "task_commit")
        control_plane_commit = self._required_sha(payload, "control_plane_commit")
        role_contract_hash = self._required_text(payload, "role_contract_hash")
        packet_binding = self._required_text(payload, "review_id")
        self._producer_role(self._required_text(payload, "role"))

        path = PurePosixPath(source_path)
        expected_path = PurePosixPath(".terminus") / "reviews" / task_id
        if expected_path.as_posix() not in path.as_posix():
            raise ValueError("review result path does not match embedded task")
        if path.name != f"{packet_binding}.json":
            raise ValueError("review result filename does not match review_id")
        if path.name.endswith(".packet.json"):
            raise ValueError("review result adapter cannot ingest a packet")
        context_packet = self._required_text(payload, "context_packet")
        if PurePosixPath(context_packet).name != f"{packet_binding}.packet.json":
            raise ValueError("review result context_packet does not match review_id")

        roles = self._projection_roles(stage_id, role_ids)
        review_scope_hash = self._optional_text(payload, "review_scope_hash")
        return self._ingest(
            source_kind="REVIEW_RESULT",
            content=raw.decode("utf-8"),
            origin_source_uri=f"git://repository/{source_path}",
            source_version=blob_sha,
            source_path=source_path,
            git_blob_sha=blob_sha,
            stage_id=stage_id,
            role_ids=roles,
            task_id=task_id,
            task_commit=task_commit,
            control_plane_commit=control_plane_commit,
            role_contract_hash=role_contract_hash,
            packet_binding=packet_binding,
            review_scope_hash=review_scope_hash,
        )

    def ingest_session_state(
        self,
        *,
        source_path: str,
        source_commit: str,
        stage_id: str,
        role_ids: Sequence[str],
    ) -> dict[str, Any]:
        """Ingest a durable session snapshot and derive identity/policy bindings from it."""
        raw, blob_sha = self._read_git_blob(source_commit, source_path)
        text = raw.decode("utf-8")
        task_id = self._session_value(text, "Task")
        task_commit = self._session_sha(text, "Current task commit")
        policy_versions = {
            key: self._session_value(text, label)
            for label, key in _SESSION_POLICY_FIELDS.items()
        }
        expected = f".terminus/sessions/{task_id}.md"
        if PurePosixPath(source_path).as_posix() != expected:
            raise ValueError("session path does not match embedded task")

        roles = self._projection_roles(stage_id, role_ids)
        return self._ingest(
            source_kind="SESSION_STATE",
            content=text,
            origin_source_uri=f"git://repository/{source_path}",
            source_version=blob_sha,
            source_path=source_path,
            git_blob_sha=blob_sha,
            stage_id=stage_id,
            role_ids=roles,
            task_id=task_id,
            task_commit=task_commit,
            control_plane_commit=source_commit,
            policy_versions=policy_versions,
        )

    def ingest_external(
        self,
        *,
        source_kind: str,
        content: str,
        source_uri: str,
        stage_id: str,
        role_ids: Sequence[str],
        task_id: str | None = None,
        task_commit: str | None = None,
        ci_run_id: str | int | None = None,
    ) -> dict[str, Any]:
        """Ingest explicit non-Git evidence using content-addressed immutable identity."""
        if source_kind not in _EXTERNAL_DYNAMIC:
            raise ValueError(f"unsupported external dynamic source kind: {source_kind}")
        if not content:
            raise ValueError("dynamic evidence content must not be empty")
        if not source_uri.strip():
            raise ValueError("dynamic evidence source_uri must not be empty")

        roles = self._projection_roles(stage_id, role_ids)
        content_digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        source_version = f"sha256:{content_digest}"
        return self._ingest(
            source_kind=source_kind,
            content=content,
            origin_source_uri=source_uri,
            source_version=source_version,
            stage_id=stage_id,
            role_ids=roles,
            task_id=task_id,
            task_commit=task_commit,
            ci_run_id=ci_run_id,
        )

    def _ingest(
        self,
        *,
        source_kind: str,
        content: str,
        origin_source_uri: str,
        source_version: str,
        stage_id: str,
        role_ids: Sequence[str],
        source_path: str | None = None,
        git_blob_sha: str | None = None,
        task_id: str | None = None,
        task_commit: str | None = None,
        control_plane_commit: str | None = None,
        policy_versions: Mapping[str, str] | None = None,
        role_contract_hash: str | None = None,
        packet_binding: str | None = None,
        review_scope_hash: str | None = None,
        ci_run_id: str | int | None = None,
    ) -> dict[str, Any]:
        if source_kind not in _REPOSITORY_DYNAMIC | _EXTERNAL_DYNAMIC:
            raise ValueError(f"source kind is not dynamic-ingestion eligible: {source_kind}")
        profile = self.policy.source_profiles.get(source_kind)
        if not isinstance(profile, dict):
            raise ValueError(f"unknown source kind: {source_kind}")

        projection_uri = self._projection_uri(origin_source_uri, stage_id, role_ids)
        document_id = "doc_" + self._sha(projection_uri, source_version)
        full_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        freshness = list(profile["required_freshness"])
        if review_scope_hash and "REVIEW_SCOPE_HASH" not in freshness:
            freshness.append("REVIEW_SCOPE_HASH")

        base: dict[str, Any] = {
            "metadata_contract_version": self.policy.metadata_registry[
                "metadata_contract_version"
            ],
            "document_id": document_id,
            "source_uri": projection_uri,
            "source_kind": source_kind,
            "source_version": source_version,
            "evidence_class": profile["default_evidence_class"],
            "sensitivity": profile["default_sensitivity"],
            "solver_visible": profile["default_solver_visible"],
            "stage_applicability": [stage_id],
            "role_applicability": list(role_ids),
            "freshness_scope": freshness,
        }
        optional = {
            "source_path": source_path,
            "git_blob_sha": git_blob_sha,
            "task_id": task_id,
            "task_commit": task_commit,
            "control_plane_commit": control_plane_commit,
            "policy_versions": dict(policy_versions) if policy_versions else None,
            "role_contract_hash": role_contract_hash,
            "packet_binding": packet_binding,
            "review_scope_hash": review_scope_hash,
            "ci_run_id": ci_run_id,
        }
        base.update({key: value for key, value in optional.items() if value is not None})
        missing = [field for field in profile["required_bindings"] if not base.get(field)]
        if missing:
            raise ValueError(
                f"{source_kind} missing required provenance bindings: {sorted(missing)}"
            )

        raw_chunks = chunk_text(
            Path(source_path or "dynamic-evidence.txt"),
            content,
            str(profile["chunk_strategy"]),
        )
        chunks: list[tuple[dict[str, Any], str]] = []
        for raw_chunk in raw_chunks:
            chunk_hash = hashlib.sha256(raw_chunk.content.encode("utf-8")).hexdigest()
            chunk_id = "chk_" + self._sha(
                document_id,
                raw_chunk.structural_locator,
                chunk_hash,
            )
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

        if not chunks:
            raise ValueError("dynamic evidence produced no chunks")
        self._validate_projection(chunks[0][0], role_ids)

        document_meta = dict(base)
        document_meta["content_hash"] = f"sha256:{full_hash}"
        self.store.upsert_document(document_meta)
        self.store.replace_document_chunks(document_id, chunks)
        return {
            "document_id": document_id,
            "source_kind": source_kind,
            "source_uri": projection_uri,
            "source_version": source_version,
            "content_hash": f"sha256:{full_hash}",
            "stage_id": stage_id,
            "role_ids": list(role_ids),
            "task_id": task_id,
            "task_commit": task_commit,
            "control_plane_commit": control_plane_commit,
            "packet_binding": packet_binding,
            "review_scope_hash": review_scope_hash,
            "ci_run_id": ci_run_id,
            "chunk_count": len(chunks),
        }

    def _validate_projection(
        self,
        metadata: Mapping[str, Any],
        role_ids: Sequence[str],
    ) -> None:
        for role_id in role_ids:
            context = InvocationContext(
                stage_id=str(metadata["stage_applicability"][0]),
                role_id=role_id,
                task_id=metadata.get("task_id"),
                task_commit=metadata.get("task_commit"),
                control_plane_commit=metadata.get("control_plane_commit"),
                role_contract_hash=metadata.get("role_contract_hash"),
                packet_binding=metadata.get("packet_binding"),
                review_scope_hash=metadata.get("review_scope_hash"),
                ci_run_id=metadata.get("ci_run_id"),
                policy_versions=metadata.get("policy_versions", {}),
            )
            decision = self.policy.authorize_chunk(metadata, context)
            if not decision.allowed:
                raise ValueError(
                    f"dynamic evidence projection denied for {role_id}: {decision.reason}"
                )

    def _projection_roles(self, stage_id: str, role_ids: Sequence[str]) -> tuple[str, ...]:
        if not role_ids:
            raise ValueError("dynamic evidence projection requires at least one role")
        allowed = self.policy.allowed_roles_for_stage(stage_id)
        canonical = tuple(
            dict.fromkeys(self.policy.canonical_role(role_id) for role_id in role_ids)
        )
        invalid = set(canonical) - allowed
        if invalid:
            raise ValueError(
                f"dynamic evidence roles are not authorized for stage {stage_id}: {sorted(invalid)}"
            )
        return canonical

    def _producer_role(self, value: str) -> str:
        return self.policy.canonical_role(_PRODUCER_ROLE_ALIASES.get(value, value))

    def _read_git_blob(self, source_commit: str, source_path: str) -> tuple[bytes, str]:
        if not re.fullmatch(r"[0-9a-f]{40,64}", source_commit):
            raise ValueError("source_commit must be a full hexadecimal Git commit")
        blob_sha = self._git_text("rev-parse", f"{source_commit}:{source_path}").strip()
        raw = subprocess.run(
            ["git", "-C", str(self.root), "show", f"{source_commit}:{source_path}"],
            check=True,
            capture_output=True,
        ).stdout
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("dynamic repository evidence must be UTF-8 text") from exc
        return raw, blob_sha

    def _git_text(self, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(self.root), *args],
            check=True,
            capture_output=True,
            text=True,
        ).stdout

    @staticmethod
    def _json_object(raw: bytes, label: str) -> dict[str, Any]:
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{label} is not valid JSON") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{label} must be a JSON object")
        return value

    @staticmethod
    def _required_text(payload: Mapping[str, Any], field: str) -> str:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"missing/invalid embedded provenance field: {field}")
        return value.strip()

    @staticmethod
    def _optional_text(payload: Mapping[str, Any], field: str) -> str | None:
        value = payload.get(field)
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"invalid embedded provenance field: {field}")
        return value.strip()

    @classmethod
    def _required_sha(cls, payload: Mapping[str, Any], field: str) -> str:
        value = cls._required_text(payload, field)
        if not re.fullmatch(r"[0-9a-f]{40,64}", value):
            raise ValueError(f"embedded {field} is not a full hexadecimal commit/hash")
        return value

    @staticmethod
    def _session_value(text: str, label: str) -> str:
        match = re.search(
            rf"^- {re.escape(label)}:\s*`([^`]+)`\s*$",
            text,
            flags=re.MULTILINE,
        )
        if not match:
            raise ValueError(f"session missing canonical {label} binding")
        return match.group(1).strip()

    @classmethod
    def _session_sha(cls, text: str, label: str) -> str:
        value = cls._session_value(text, label)
        if not re.fullmatch(r"[0-9a-f]{40,64}", value):
            raise ValueError(f"session {label} is not a full hexadecimal commit")
        return value

    @staticmethod
    def _projection_uri(origin: str, stage_id: str, role_ids: Sequence[str]) -> str:
        payload = json.dumps(
            {"stage": stage_id, "roles": sorted(role_ids)},
            sort_keys=True,
            separators=(",", ":"),
        )
        projection = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
        separator = "&" if "#" in origin else "#"
        return f"{origin}{separator}terminus-projection={projection}"

    @staticmethod
    def _sha(*parts: str) -> str:
        digest = hashlib.sha256()
        for part in parts:
            digest.update(part.encode("utf-8"))
            digest.update(b"\0")
        return digest.hexdigest()
