"""Fail-closed provenance validation for feedback and closure authority."""

from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any, Mapping
from urllib.parse import unquote

from authority.receipts import AuthorityReceiptValidator
from execution.evidence_refs import EvidenceReferenceVerifier
from execution.ledger import ExecutionLedger
from retrieval.policy import RetrievalPolicy
from review_contract import (
    ROLE_POLICY_VERSIONS,
    policy_versions,
    role_contract_hash,
    validate_schema,
)

from .model import content_hash, feedback_identity

_PASSING = frozenset({"PASS", "APPROVE", "APPROVE_WITH_NOTE"})
_ROLE_BY_PRODUCER = {
    "Q4_SPEC_TEST_CONTRACT_REVIEWER": "Spec-Test Contract Reviewer",
    "Q6_PRODUCTION_LOGIC_AUDITOR": "Production Logic Auditor",
    "ADJUDICATOR": "Adjudicator",
}
_REVIEW_FEEDBACK_SOURCES = frozenset(
    {"INDEPENDENT_REVIEW", "REVIEWER_REVIEW", "FINAL_REVIEW"}
)
_SOURCE_NAMESPACE = ".terminus/feedback/source_evidence/"
_REVIEW_NAMESPACE = ".terminus/reviews/"
_REVIEW_EXECUTION_BINDINGS = {
    "Spec-Test Contract Reviewer": ("QUALITY_INTERLOCK", "Q4_RESULT"),
    "Production Logic Auditor": ("QUALITY_INTERLOCK", "Q6_RESULT"),
    "Compliance Auditor": ("FINAL_REVIEW", "FINAL_COMPLIANCE"),
    "Human Quality Reviewer": ("FINAL_REVIEW", "FINAL_HUMAN_QUALITY"),
}
_AUTOMATED_SOURCE_STAGES = {
    "PORTAL_CI": frozenset({"DETERMINISTIC_VALIDATION"}),
    "REPOSITORY_CI": frozenset({"DETERMINISTIC_VALIDATION"}),
    "LLMAJ": frozenset({"HARBOR_LLMAJ"}),
    "MODEL_DIAGNOSTIC": frozenset(
        {
            "MODEL_DIAGNOSTIC_GPT",
            "MODEL_DIAGNOSTIC_CLAUDE",
            "MODEL_DIAGNOSTIC_AGGREGATE",
        }
    ),
    "MODEL_TRIAL": frozenset({"OFFICIAL_MODEL_TRIALS"}),
    "DIFFICULTY": frozenset({"DIFFICULTY_ASSESSMENT"}),
    "SUBMISSION_RESULT": frozenset({"SUBMISSION_READY"}),
    "RUNTIME": frozenset({"RUNTIME_AUTHENTICITY"}),
}


class ProvenanceValidator:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.evidence = EvidenceReferenceVerifier(self.root)
        self.policy = RetrievalPolicy(self.root)
        self.semantic_authority = AuthorityReceiptValidator(self.root)

    def validate_feedback_event(self, event: Mapping[str, Any]) -> bool:
        """Replay event identity/provenance and return whether it is authoritative."""
        value = self._json_copy(event, "feedback event")
        feedback_id = value.get("feedback_id")
        provenance = value.get("provenance")
        source = value.get("source")
        task = value.get("task")
        observation = value.get("observation")
        if not isinstance(provenance, Mapping):
            raise ValueError("feedback event provenance is invalid")
        if not isinstance(source, Mapping) or not isinstance(task, Mapping):
            raise ValueError("feedback event source/task is invalid")
        if not isinstance(observation, Mapping):
            raise ValueError("feedback event observation is invalid")
        hash_payload = copy.deepcopy(value)
        hash_payload.pop("feedback_id", None)
        hash_payload["provenance"].pop("content_hash", None)
        if provenance.get("content_hash") != content_hash(hash_payload):
            raise ValueError("feedback event content_hash does not match event content")
        if feedback_identity(value) != feedback_id:
            raise ValueError("feedback_id does not match canonical feedback identity")

        source_type = str(source.get("type"))
        producer = str(source.get("producer"))
        task_id = str(task.get("task_id"))
        task_commit = str(task.get("task_commit"))
        binding = provenance.get("source_binding")
        receipt = provenance.get("authority_receipt")
        claim = self._feedback_authority_claim(value)
        trust = str(provenance.get("trust_status"))

        if trust == "HUMAN_AUTHENTICATED":
            if source_type != "HUMAN_REVIEW":
                raise ValueError("HUMAN_AUTHENTICATED trust requires HUMAN_REVIEW")
            self.semantic_authority.verify(
                receipt if isinstance(receipt, Mapping) else None,
                action="HUMAN_FEEDBACK",
                principal=f"human:{producer}",
                claim=claim,
            )
            return True
        if trust in {"UNAUTHENTICATED", "HUMAN_ASSERTED", "EXTERNAL_POINTER_ONLY"}:
            return False
        if trust != "REPOSITORY_RESOLVED":
            raise ValueError("feedback event has unknown trust status")
        if not isinstance(binding, Mapping):
            raise ValueError("repository-resolved feedback requires source_binding")
        if source_type in _REVIEW_FEEDBACK_SOURCES:
            self.validate_review_result(
                binding=binding,
                producer=producer,
                task_id=task_id,
                task_commit=task_commit,
                require_passing=False,
                require_sufficient=False,
                require_confidence=False,
                require_current_contract=False,
                require_authority=True,
            )
            return True
        self.validate_source_binding(
            source_type=source_type,
            producer=producer,
            task_id=task_id,
            task_commit=task_commit,
            run_id=source.get("run_id"),
            binding=binding,
            authority_receipt=receipt if isinstance(receipt, Mapping) else None,
            authority_claim=claim,
        )
        return True

    def validate_source_binding(
        self,
        *,
        source_type: str,
        producer: str,
        task_id: str,
        task_commit: str,
        run_id: str | int | None,
        binding: Mapping[str, Any],
        authority_receipt: Mapping[str, Any] | None = None,
        authority_claim: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        validated = self.evidence.validate(binding, 0)
        ref = validated.get("ref")
        if not isinstance(ref, str) or not ref.startswith("git:"):
            return validated
        evidence_commit, path, fragment = self._git_location(ref)

        if source_type in _REVIEW_FEEDBACK_SOURCES and path.startswith(
            f"{_REVIEW_NAMESPACE}{task_id}/"
        ):
            return self.validate_review_result(
                binding=validated,
                producer=producer,
                task_id=task_id,
                task_commit=task_commit,
                require_passing=False,
                require_sufficient=False,
                require_confidence=False,
                require_current_contract=False,
                require_authority=False,
            )

        if not path.startswith(_SOURCE_NAMESPACE):
            raise ValueError(
                "repository-resolved automated feedback must use a canonical review RESULT or the controlled source-evidence namespace"
            )
        if run_id is None or not str(run_id).strip():
            raise ValueError(
                "repository-resolved automated feedback requires an immutable run_id"
            )
        if authority_claim is None:
            raise ValueError(
                "repository-resolved automated feedback requires an exact signed authority claim"
            )
        self.semantic_authority.verify(
            authority_receipt,
            action="AUTOMATED_SOURCE",
            principal=f"automation:{source_type}:{producer}",
            claim=authority_claim,
        )
        self._require_reachable(evidence_commit)
        payload = self._git_json(
            evidence_commit, path, "automated feedback source artifact"
        )
        event = self._select_source_event(
            payload,
            source_type=source_type,
            producer=producer,
            task_id=task_id,
            task_commit=task_commit,
            run_id=run_id,
            evidence_commit=evidence_commit,
        )
        accepted_identity = str(event["run_id"])
        if fragment is not None and fragment != accepted_identity:
            raise ValueError(
                "automated feedback source artifact fragment must bind run_id"
            )
        self._validate_automated_execution_authority(
            source_type=source_type,
            task_id=task_id,
            task_commit=task_commit,
            binding=validated,
        )
        return validated

    def _select_source_event(
        self,
        payload: Mapping[str, Any],
        *,
        source_type: str,
        producer: str,
        task_id: str,
        task_commit: str,
        run_id: str | int | None,
        evidence_commit: str,
    ) -> Mapping[str, Any]:
        artifact_type = payload.get("artifact_type")
        if artifact_type == "FEEDBACK_SOURCE_EVENT":
            candidates = [payload]
        elif artifact_type == "FEEDBACK_SOURCE_EVENT_SET":
            if payload.get("schema_version") != "1.0" or not isinstance(
                payload.get("events"), list
            ):
                raise ValueError(
                    "automated feedback source event set has invalid schema"
                )
            candidates = [
                item for item in payload["events"] if isinstance(item, Mapping)
            ]
        else:
            raise ValueError(
                "automated feedback source artifact has unsupported artifact_type"
            )

        matches: list[Mapping[str, Any]] = []
        for candidate in candidates:
            if candidate.get("source_type") != source_type:
                continue
            if candidate.get("producer") != producer:
                continue
            if candidate.get("task_id") != task_id:
                continue
            attested_commit = candidate.get("task_commit")
            if attested_commit == "$EVIDENCE_COMMIT":
                attested_commit = evidence_commit
            if attested_commit != task_commit:
                continue
            artifact_run = candidate.get("run_id")
            if str(artifact_run) != str(run_id):
                continue
            matches.append(candidate)
        if len(matches) != 1:
            raise ValueError(
                "automated feedback source artifact must contain exactly one event attestation matching source, producer, task and run"
            )
        return matches[0]

    def validate_review_result(
        self,
        *,
        binding: Mapping[str, Any],
        producer: str,
        task_id: str,
        task_commit: str,
        require_passing: bool,
        conflict_resolution: bool = False,
        conflict_binding: Mapping[str, Any] | None = None,
        verification_binding: Mapping[str, Any] | None = None,
        require_sufficient: bool = True,
        require_confidence: bool = True,
        require_current_contract: bool = True,
        require_authority: bool = True,
    ) -> dict[str, Any]:
        validated = self.evidence.validate(binding, 0)
        ref = validated.get("ref")
        if (
            validated.get("kind") != "RESULT"
            or not isinstance(ref, str)
            or not ref.startswith("git:")
        ):
            raise ValueError(
                "trusted review authority requires repository-resolved kind RESULT evidence"
            )
        evidence_commit, path, _fragment = self._git_location(ref)
        expected_prefix = f"{_REVIEW_NAMESPACE}{task_id}/"
        if not path.startswith(expected_prefix):
            raise ValueError(
                "trusted review RESULT must come from the task review namespace"
            )
        self._require_reachable(evidence_commit)
        payload = self._git_json(evidence_commit, path, "trusted review RESULT")

        role = self._canonical_role(producer)
        if role is None:
            raise ValueError(f"no canonical review role is registered for {producer}")
        schema = self._working_json(
            ".terminus/agents/schemas/review_result.schema.json"
        )
        errors: list[str] = []
        validate_schema(payload, schema, "review_result", errors)
        if errors:
            raise ValueError(
                "trusted review RESULT is not canonical: " + "; ".join(errors[:5])
            )
        if payload.get("role") != role:
            raise ValueError(
                "trusted review RESULT role does not match verification owner"
            )
        if payload.get("task") != task_id or payload.get("task_commit") != task_commit:
            raise ValueError(
                "trusted review RESULT is not bound to the exact verification task commit"
            )
        if require_sufficient and payload.get("evidence_status") != "SUFFICIENT":
            raise ValueError("trusted review RESULT has insufficient evidence")
        if require_confidence and payload.get("confidence") not in {"MEDIUM", "HIGH"}:
            raise ValueError(
                "trusted review RESULT confidence is insufficient for closure"
            )
        if require_passing and payload.get("verdict") not in _PASSING:
            raise ValueError(
                "trusted review RESULT does not carry a passing outcome"
            )
        role_output = payload.get("role_output")
        if not isinstance(role_output, Mapping):
            raise ValueError("trusted review RESULT role_output is invalid")
        if require_authority:
            receipt = role_output.get("AUTHORITY_RECEIPT")
            self.semantic_authority.verify(
                receipt if isinstance(receipt, Mapping) else None,
                action="REVIEW_RESULT",
                principal=f"reviewer:{role}",
                claim=self.review_authority_claim(payload),
            )
        if verification_binding is not None:
            if role_output.get("FINDING_VERIFICATION") != dict(verification_binding):
                raise ValueError(
                    "trusted review RESULT is not bound to the exact finding remediation verification"
                )
        if conflict_resolution:
            self._validate_conflict_result(
                payload,
                role=role,
                conflict_binding=conflict_binding,
            )
        if require_current_contract:
            if payload.get("role_policy_version") != ROLE_POLICY_VERSIONS.get(role):
                raise ValueError(
                    "trusted review RESULT role policy version is stale"
                )
            versions = policy_versions(self.root)
            if payload.get("protocol_policy_version") != versions.get("protocol"):
                raise ValueError(
                    "trusted review RESULT protocol policy version is stale"
                )
            if payload.get("prompt_policy_version") != versions.get("prompts"):
                raise ValueError(
                    "trusted review RESULT prompt policy version is stale"
                )
            if payload.get("role_contract_hash") != role_contract_hash(
                self.root, role
            ):
                raise ValueError(
                    "trusted review RESULT role contract hash is stale"
                )
        control_plane = payload.get("control_plane_commit")
        if not isinstance(control_plane, str) or not control_plane:
            raise ValueError(
                "trusted review RESULT is missing control_plane_commit"
            )
        self._require_ancestor(
            control_plane, evidence_commit, "review control-plane commit"
        )
        self._validate_packet(
            payload, evidence_commit=evidence_commit, result_path=path
        )
        if require_current_contract:
            self._validate_review_execution_authority(
                role=role,
                payload=payload,
                task_id=task_id,
                task_commit=task_commit,
                binding=validated,
                conflict_resolution=conflict_resolution,
            )
        return validated

    def validate_policy_conflict_authority(
        self,
        *,
        binding: Mapping[str, Any],
        task_id: str,
        task_commit: str,
    ) -> dict[str, Any]:
        validated = self.validate_review_result(
            binding=binding,
            producer="ADJUDICATOR",
            task_id=task_id,
            task_commit=task_commit,
            require_passing=False,
            require_sufficient=True,
            require_confidence=True,
            require_current_contract=False,
            require_authority=True,
        )
        ref = str(validated["ref"])
        evidence_commit, path, _fragment = self._git_location(ref)
        payload = self._git_json(evidence_commit, path, "policy-conflict Adjudicator RESULT")
        if payload.get("verdict") != "POLICY_CONFLICT":
            raise ValueError("POLICY_CONFLICT authority requires Adjudicator POLICY_CONFLICT verdict")
        self._validate_review_execution_authority(
            role="Adjudicator",
            payload=payload,
            task_id=task_id,
            task_commit=task_commit,
            binding=validated,
            conflict_resolution=True,
        )
        return payload

    @staticmethod
    def review_authority_claim(payload: Mapping[str, Any]) -> dict[str, Any]:
        value = json.loads(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
        role_output = value.get("role_output")
        if isinstance(role_output, dict):
            role_output.pop("AUTHORITY_RECEIPT", None)
        return value

    def _validate_conflict_result(
        self,
        payload: Mapping[str, Any],
        *,
        role: str,
        conflict_binding: Mapping[str, Any] | None,
    ) -> None:
        if role != "Adjudicator":
            raise ValueError(
                "canonical reviewer conflict resolution requires the Adjudicator role"
            )
        if conflict_binding is None:
            raise ValueError(
                "Adjudicator conflict RESULT requires an exact conflict binding"
            )
        role_output = payload.get("role_output")
        if not isinstance(role_output, Mapping):
            raise ValueError("Adjudicator conflict RESULT lacks role_output")
        expected = {
            "CONFLICT_RESOLUTION": "RESOLVED",
            "CONFLICT_FINDING_ID": conflict_binding.get("finding_id"),
            "CONFLICT_TYPE": conflict_binding.get("conflict_type"),
            "CONFLICT_SIGNAL_IDS": conflict_binding.get("signal_ids"),
            "CONFLICT_SIGNAL_CLAIMS": conflict_binding.get("signal_claims"),
            "CONFLICTING_CATEGORIES": conflict_binding.get("conflicting_categories"),
        }
        if conflict_binding.get("affected_gate") is not None:
            expected["AFFECTED_GATE"] = conflict_binding.get("affected_gate")
            expected["POLICY_RULE_HASHES"] = conflict_binding.get("policy_rule_hashes")
        if conflict_binding.get("policy_decision_key") is not None:
            expected["POLICY_DECISION_KEY"] = conflict_binding.get("policy_decision_key")
            expected["POLICY_REQUIRED_VALUES"] = conflict_binding.get("policy_required_values")
        for key, value in expected.items():
            if role_output.get(key) != value:
                raise ValueError(
                    f"Adjudicator conflict RESULT is not bound to exact conflict field {key}"
                )
        if payload.get("verdict") not in _PASSING:
            raise ValueError("Adjudicator conflict RESULT lacks a successful verdict")

    def _canonical_role(self, producer: str) -> str | None:
        mapped = _ROLE_BY_PRODUCER.get(producer)
        if mapped is not None:
            return mapped
        return producer if producer in ROLE_POLICY_VERSIONS else None

    def _validate_packet(
        self,
        payload: Mapping[str, Any],
        *,
        evidence_commit: str,
        result_path: str,
    ) -> None:
        packet_path = payload.get("context_packet")
        review_id = payload.get("review_id")
        if not isinstance(packet_path, str) or not packet_path.startswith(
            ".terminus/reviews/"
        ):
            raise ValueError("trusted review RESULT has invalid context_packet")
        if PurePosixPath(packet_path).parent != PurePosixPath(result_path).parent:
            raise ValueError(
                "trusted review RESULT and packet must share the controlled review directory"
            )
        packet = self._git_json(evidence_commit, packet_path, "trusted review packet")
        packet_schema = self._working_json(
            ".terminus/agents/schemas/context_packet.schema.json"
        )
        packet_errors: list[str] = []
        validate_schema(packet, packet_schema, "context_packet", packet_errors)
        if packet_errors:
            raise ValueError(
                "trusted review packet is not canonical: " + "; ".join(packet_errors[:5])
            )
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
        if packet.get("review_output_path") != result_path:
            raise ValueError("trusted review packet does not bind the RESULT output path")
        if packet.get("output_schema") != ".terminus/agents/schemas/review_result.schema.json":
            raise ValueError(
                "trusted review packet does not bind the canonical review-result schema"
            )

    def _validate_review_execution_authority(
        self,
        *,
        role: str,
        payload: Mapping[str, Any],
        task_id: str,
        task_commit: str,
        binding: Mapping[str, Any],
        conflict_resolution: bool,
    ) -> None:
        ledger = ExecutionLedger(self.root, task_id)
        events = ledger.load(validate_record_files=True)
        expected_control = str(payload["control_plane_commit"])
        if conflict_resolution and role == "Adjudicator":
            for event in events:
                record = self._record_for_event(event)
                stage = self.policy.stages.get(str(record.get("stage_id")), {})
                if stage.get("role_class") != "CONTROLLER":
                    continue
                if self._record_matches_review(
                    record,
                    task_commit=task_commit,
                    control_plane_commit=expected_control,
                    binding=binding,
                ):
                    return
            raise ValueError(
                "Adjudicator RESULT is not consumed by an authenticated canonical controller execution"
            )

        expected = _REVIEW_EXECUTION_BINDINGS.get(role)
        if expected is None:
            raise ValueError(
                f"current closure authority has no canonical execution binding for review role {role}"
            )
        stage_id, output_field = expected
        for event in events:
            if event.get("stage_id") != stage_id:
                continue
            record = self._record_for_event(event)
            if not self._record_matches_review(
                record,
                task_commit=task_commit,
                control_plane_commit=expected_control,
                binding=binding,
            ):
                continue
            outputs = record.get("outputs")
            if isinstance(outputs, Mapping) and outputs.get(output_field) == payload:
                return
        raise ValueError(
            "trusted review RESULT is not consumed by its authenticated canonical controller execution"
        )

    def _validate_automated_execution_authority(
        self,
        *,
        source_type: str,
        task_id: str,
        task_commit: str,
        binding: Mapping[str, Any],
    ) -> None:
        allowed_stages = _AUTOMATED_SOURCE_STAGES.get(source_type)
        if not allowed_stages:
            raise ValueError(
                f"no canonical execution provenance contract exists for {source_type}"
            )
        ledger = ExecutionLedger(self.root, task_id)
        events = ledger.load(validate_record_files=True)
        for event in events:
            if event.get("stage_id") not in allowed_stages:
                continue
            record = self._record_for_event(event)
            lineage = record.get("task_lineage")
            if not isinstance(lineage, Mapping):
                continue
            if task_commit not in {
                lineage.get("input_task_commit"),
                lineage.get("output_task_commit"),
            }:
                continue
            refs = record.get("evidence_refs")
            if isinstance(refs, list) and any(
                isinstance(item, Mapping) and dict(item) == dict(binding)
                for item in refs
            ):
                return
        raise ValueError(
            "automated feedback attestation is not rooted in an authenticated source-specific execution"
        )

    def _record_matches_review(
        self,
        record: Mapping[str, Any],
        *,
        task_commit: str,
        control_plane_commit: str,
        binding: Mapping[str, Any],
    ) -> bool:
        if record.get("disposition") != "ADVANCE":
            return False
        authority = record.get("authority")
        lineage = record.get("task_lineage")
        if not isinstance(authority, Mapping) or not isinstance(lineage, Mapping):
            return False
        if authority.get("control_plane_commit") != control_plane_commit:
            return False
        if lineage.get("input_task_commit") != task_commit:
            return False
        if lineage.get("output_task_commit") != task_commit:
            return False
        refs = record.get("evidence_refs")
        return isinstance(refs, list) and any(
            isinstance(item, Mapping) and dict(item) == dict(binding) for item in refs
        )

    def _record_for_event(self, event: Mapping[str, Any]) -> dict[str, Any]:
        from execution.record import ExecutionRecordBuilder

        path = (self.root / str(event["record_path"])).resolve()
        if self.root not in path.parents:
            raise ValueError("execution record path escapes repository root")
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("execution record must be a JSON object")
        return ExecutionRecordBuilder(self.root).validate_execution_authority(value)

    @staticmethod
    def _feedback_authority_claim(event: Mapping[str, Any]) -> dict[str, Any]:
        provenance = event["provenance"]
        return {
            "source": copy.deepcopy(dict(event["source"])),
            "task": copy.deepcopy(dict(event["task"])),
            "observation": copy.deepcopy(dict(event["observation"])),
            "captured_at": provenance["captured_at"],
            "source_binding": copy.deepcopy(dict(provenance["source_binding"]))
            if isinstance(provenance.get("source_binding"), Mapping)
            else None,
        }

    @staticmethod
    def _json_copy(value: Mapping[str, Any], label: str) -> dict[str, Any]:
        try:
            copied = json.loads(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label} must be JSON-compatible") from exc
        if not isinstance(copied, dict):
            raise ValueError(f"{label} must be one JSON object")
        return copied

    def _git_location(self, ref: str) -> tuple[str, str, str | None]:
        body = ref[len("git:") :]
        location, marker, fragment = body.partition("#")
        commit, separator, encoded_path = location.partition(":")
        if not separator:
            raise ValueError("invalid git evidence location")
        return (
            commit,
            unquote(encoded_path),
            unquote(fragment).strip() if marker else None,
        )

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
            [
                "git",
                "-C",
                str(self.root),
                "merge-base",
                "--is-ancestor",
                ancestor,
                descendant,
            ],
            capture_output=True,
        )
        if result.returncode != 0:
            raise ValueError(f"{label} is not on the authorized repository lineage")
