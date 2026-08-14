"""Fail-closed provenance validation for feedback and closure authority."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any, Mapping
from urllib.parse import unquote

from execution.evidence_refs import EvidenceReferenceVerifier
from review_contract import ROLE_POLICY_VERSIONS, policy_versions, role_contract_hash, validate_schema

_PASSING = frozenset({"PASS", "APPROVE", "APPROVE_WITH_NOTE"})
_ROLE_BY_PRODUCER = {
    "Q4_SPEC_TEST_CONTRACT_REVIEWER": "Spec-Test Contract Reviewer",
    "Q6_PRODUCTION_LOGIC_AUDITOR": "Production Logic Auditor",
    "ADJUDICATOR": "Adjudicator",
}
_SOURCE_NAMESPACE = ".terminus/feedback/source_evidence/"
_REVIEW_NAMESPACE = ".terminus/reviews/"


class ProvenanceValidator:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.evidence = EvidenceReferenceVerifier(self.root)

    def validate_source_binding(
        self,
        *,
        source_type: str,
        producer: str,
        task_id: str,
        task_commit: str,
        run_id: str | int | None,
        binding: Mapping[str, Any],
    ) -> dict[str, Any]:
        validated = self.evidence.validate(binding, 0)
        ref = validated.get("ref")
        if not isinstance(ref, str) or not ref.startswith("git:"):
            # External pointers are intentionally non-authenticating. They remain
            # usable as signals but never become REPOSITORY_RESOLVED authority.
            return validated
        commit, path, _fragment = self._git_location(ref)
        if not path.startswith(_SOURCE_NAMESPACE):
            raise ValueError(
                "repository-resolved automated feedback must use the controlled source-evidence namespace"
            )
        self._require_reachable(commit)
        payload = self._git_json(commit, path, "automated feedback source artifact")
        required = {
            "schema_version": "1.0",
            "artifact_type": "FEEDBACK_SOURCE_EVENT",
            "source_type": source_type,
            "producer": producer,
            "task_id": task_id,
            "task_commit": task_commit,
        }
        for key, expected in required.items():
            if payload.get(key) != expected:
                raise ValueError(
                    f"automated feedback source artifact {key} does not match captured event"
                )
        artifact_run = payload.get("run_id")
        if run_id is None:
            if artifact_run not in {None, ""}:
                raise ValueError("automated feedback source artifact carries an unexpected run_id")
        elif str(artifact_run) != str(run_id):
            raise ValueError("automated feedback source artifact run_id does not match captured event")
        identity = self.evidence.identity(validated)
        if identity is not None and identity not in {producer, str(run_id) if run_id is not None else producer}:
            raise ValueError("automated feedback source artifact fragment identity is inconsistent")
        return validated

    def validate_review_result(
        self,
        *,
        binding: Mapping[str, Any],
        producer: str,
        task_id: str,
        task_commit: str,
        require_passing: bool,
        conflict_resolution: bool = False,
    ) -> dict[str, Any]:
        validated = self.evidence.validate(binding, 0)
        ref = validated.get("ref")
        if validated.get("kind") != "RESULT" or not isinstance(ref, str) or not ref.startswith("git:"):
            raise ValueError("trusted review authority requires repository-resolved kind RESULT evidence")
        commit, path, _fragment = self._git_location(ref)
        expected_prefix = f"{_REVIEW_NAMESPACE}{task_id}/"
        if not path.startswith(expected_prefix):
            raise ValueError("trusted review RESULT must come from the task review namespace")
        self._require_reachable(commit)
        payload = self._git_json(commit, path, "trusted review RESULT")

        role = _ROLE_BY_PRODUCER.get(producer)
        if role is None:
            if producer != "CI_ORCHESTRATOR":
                raise ValueError(f"no canonical review role is registered for {producer}")
            self._validate_orchestrator_result(
                payload,
                producer=producer,
                task_id=task_id,
                task_commit=task_commit,
                require_passing=require_passing,
                conflict_resolution=conflict_resolution,
            )
            return validated

        schema = self._working_json(".terminus/agents/schemas/review_result.schema.json")
        errors: list[str] = []
        validate_schema(payload, schema, "review_result", errors)
        if errors:
            raise ValueError("trusted review RESULT is not canonical: " + "; ".join(errors[:5]))
        if payload.get("role") != role:
            raise ValueError("trusted review RESULT role does not match verification owner")
        if payload.get("task") != task_id or payload.get("task_commit") != task_commit:
            raise ValueError("trusted review RESULT is not bound to the exact verification task commit")
        if payload.get("evidence_status") != "SUFFICIENT":
            raise ValueError("trusted review RESULT has insufficient evidence")
        if payload.get("confidence") not in {"MEDIUM", "HIGH"}:
            raise ValueError("trusted review RESULT confidence is insufficient for closure")
        if require_passing and payload.get("verdict") not in _PASSING:
            raise ValueError("trusted review RESULT does not carry a passing outcome")
        if conflict_resolution and payload.get("verdict") not in _PASSING:
            raise ValueError("conflict-resolution RESULT does not carry a successful disposition")
        if payload.get("role_policy_version") != ROLE_POLICY_VERSIONS.get(role):
            raise ValueError("trusted review RESULT role policy version is stale")
        versions = policy_versions(self.root)
        if payload.get("protocol_policy_version") != versions.get("protocol"):
            raise ValueError("trusted review RESULT protocol policy version is stale")
        if payload.get("prompt_policy_version") != versions.get("prompts"):
            raise ValueError("trusted review RESULT prompt policy version is stale")
        if payload.get("role_contract_hash") != role_contract_hash(self.root, role):
            raise ValueError("trusted review RESULT role contract hash is stale")
        control_plane = payload.get("control_plane_commit")
        if not isinstance(control_plane, str) or not control_plane:
            raise ValueError("trusted review RESULT is missing control_plane_commit")
        self._require_ancestor(control_plane, commit, "review control-plane commit")
        self._validate_packet(payload, evidence_commit=commit, result_path=path)
        return validated

    def _validate_packet(
        self, payload: Mapping[str, Any], *, evidence_commit: str, result_path: str
    ) -> None:
        packet_path = payload.get("context_packet")
        review_id = payload.get("review_id")
        if not isinstance(packet_path, str) or not packet_path.startswith(".terminus/reviews/"):
            raise ValueError("trusted review RESULT has invalid context_packet")
        if PurePosixPath(packet_path).parent != PurePosixPath(result_path).parent:
            raise ValueError("trusted review RESULT and packet must share the controlled review directory")
        packet = self._git_json(evidence_commit, packet_path, "trusted review packet")
        for key in (
            "review_id",
            "task",
            "task_commit",
            "control_plane_commit",
            "protocol_policy_version",
            "prompt_policy_version",
            "role_policy_version",
            "role_contract_hash",
            "role",
        ):
            if packet.get(key) != payload.get(key):
                raise ValueError(f"trusted review packet/result mismatch for {key}")
        if packet.get("review_id") != review_id:
            raise ValueError("trusted review packet does not bind review_id")
        output_path = packet.get("review_output_path")
        if output_path != result_path:
            raise ValueError("trusted review packet does not bind the RESULT output path")
        if packet.get("output_schema") != ".terminus/agents/schemas/review_result.schema.json":
            raise ValueError("trusted review packet does not bind the canonical review-result schema")

    def _validate_orchestrator_result(
        self,
        payload: Mapping[str, Any],
        *,
        producer: str,
        task_id: str,
        task_commit: str,
        require_passing: bool,
        conflict_resolution: bool,
    ) -> None:
        required = {
            "schema_version": "1.0",
            "artifact_type": "CI_ORCHESTRATOR_RESULT",
            "producer": producer,
            "task_id": task_id,
            "task_commit": task_commit,
        }
        for key, expected in required.items():
            if payload.get(key) != expected:
                raise ValueError(f"orchestrator RESULT {key} is missing or mismatched")
        if payload.get("evidence_status") != "SUFFICIENT":
            raise ValueError("orchestrator RESULT has insufficient evidence")
        if require_passing and payload.get("result") != "PASS":
            raise ValueError("orchestrator RESULT does not carry PASS")
        if conflict_resolution:
            if payload.get("result") != "PASS" or payload.get("resolution") != "CONFLICT_RESOLVED":
                raise ValueError("orchestrator conflict RESULT lacks explicit successful resolution")
        control_plane = payload.get("control_plane_commit")
        if not isinstance(control_plane, str) or not control_plane:
            raise ValueError("orchestrator RESULT is missing control_plane_commit")
        current = subprocess.run(
            ["git", "-C", str(self.root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if control_plane != current:
            raise ValueError("orchestrator RESULT is not bound to the current control plane")

    def _git_location(self, ref: str) -> tuple[str, str, str | None]:
        body = ref[len("git:") :]
        location, marker, fragment = body.partition("#")
        commit, separator, encoded_path = location.partition(":")
        if not separator:
            raise ValueError("invalid git evidence location")
        return commit, unquote(encoded_path), unquote(fragment).strip() if marker else None

    def _git_json(self, commit: str, path: str, label: str) -> dict[str, Any]:
        raw = subprocess.run(
            ["git", "-C", str(self.root), "show", f"{commit}:{path}"],
            check=False,
            capture_output=True,
        )
        if raw.returncode != 0:
            raise ValueError(f"{label} is unavailable")
        try:
            value = json.loads(raw.stdout.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"{label} must be JSON") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{label} must be a JSON object")
        return value

    def _working_json(self, path: str) -> dict[str, Any]:
        value = json.loads((self.root / path).read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError(f"{path} must contain a JSON object")
        return value

    def _require_reachable(self, commit: str) -> None:
        head = subprocess.run(
            ["git", "-C", str(self.root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        self._require_ancestor(commit, head, "evidence commit")

    def _require_ancestor(self, ancestor: str, descendant: str, label: str) -> None:
        result = subprocess.run(
            ["git", "-C", str(self.root), "merge-base", "--is-ancestor", ancestor, descendant],
            capture_output=True,
        )
        if result.returncode != 0:
            raise ValueError(f"{label} is not on the authorized repository lineage")


def file_content_hash(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
