"""Fail-closed provenance validation for feedback and closure authority."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path, PurePosixPath
from typing import Any, Mapping
from urllib.parse import unquote

from execution.evidence_refs import EvidenceReferenceVerifier
from execution.ledger import ExecutionLedger
from retrieval.policy import RetrievalPolicy
from review_contract import (
    ROLE_POLICY_VERSIONS,
    policy_versions,
    role_contract_hash,
    validate_schema,
)

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
            # External pointers are content-addressed provenance only. They are
            # deliberately not upgraded to repository-authenticated authority.
            return validated
        evidence_commit, path, fragment = self._git_location(ref)

        if source_type in _REVIEW_FEEDBACK_SOURCES and path.startswith(
            f"{_REVIEW_NAMESPACE}{task_id}/"
        ):
            # Historical canonical reviewer results remain useful feedback, but
            # are deliberately not granted current closure authority here.
            return self.validate_review_result(
                binding=validated,
                producer=producer,
                task_id=task_id,
                task_commit=task_commit,
                require_passing=False,
                require_sufficient=False,
                require_confidence=False,
                require_current_contract=False,
            )

        if not path.startswith(_SOURCE_NAMESPACE):
            raise ValueError(
                "repository-resolved automated feedback must use a canonical review RESULT or the controlled source-evidence namespace"
            )
        if run_id is None or not str(run_id).strip():
            raise ValueError(
                "repository-resolved automated feedback requires an immutable run_id"
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
            run_id=accepted_identity,
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
        require_sufficient: bool = True,
        require_confidence: bool = True,
        require_current_contract: bool = True,
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
            "CONFLICTING_CATEGORIES": conflict_binding.get(
                "conflicting_categories"
            ),
        }
        if conflict_binding.get("affected_gate") is not None:
            expected["AFFECTED_GATE"] = conflict_binding.get("affected_gate")
            expected["POLICY_RULE_HASHES"] = conflict_binding.get(
                "policy_rule_hashes"
            )
        for key, value in expected.items():
            if role_output.get(key) != value:
                raise ValueError(
                    f"Adjudicator conflict RESULT is not bound to exact conflict field {key}"
                )
        if payload.get("verdict") not in _PASSING:
            raise ValueError(
                "Adjudicator conflict RESULT lacks a successful verdict"
            )

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
        packet = self._git_json(
            evidence_commit, packet_path, "trusted review packet"
        )
        packet_schema = self._working_json(
            ".terminus/agents/schemas/context_packet.schema.json"
        )
        packet_errors: list[str] = []
        validate_schema(packet, packet_schema, "context_packet", packet_errors)
        if packet_errors:
            raise ValueError(
                "trusted review packet is not canonical: "
                + "; ".join(packet_errors[:5])
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
                raise ValueError(
                    f"trusted review packet/result mismatch for {key}"
                )
        if packet.get("review_id") != review_id:
            raise ValueError("trusted review packet does not bind review_id")
        if packet.get("review_output_path") != result_path:
            raise ValueError(
                "trusted review packet does not bind the RESULT output path"
            )
        if (
            packet.get("output_schema")
            != ".terminus/agents/schemas/review_result.schema.json"
        ):
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
        """Require a canonical controller execution to consume the review RESULT.

        Git reachability and a mutually consistent packet/result are not enough:
        current closure authority exists only when the immutable RESULT was also
        consumed by a canonical StageInvocation/ExecutionRecord under the exact
        task/control-plane snapshot.
        """
        ledger = ExecutionLedger(self.root, task_id)
        events = ledger.load(validate_record_files=True)
        expected_control = str(payload["control_plane_commit"])
        if conflict_resolution and role == "Adjudicator":
            for event in events:
                record = self._record_for_event(event)
                stage = self.policy.stages.get(str(record.get("stage_id")), {})
                if stage.get("role_class") != "CONTROLLER":
                    continue
                if not self._record_matches_review(
                    record,
                    task_commit=task_commit,
                    control_plane_commit=expected_control,
                    binding=binding,
                ):
                    continue
                return
            raise ValueError(
                "Adjudicator conflict RESULT is not consumed by a canonical controller execution"
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
            if not isinstance(outputs, Mapping):
                continue
            if outputs.get(output_field) != payload:
                continue
            return
        raise ValueError(
            "trusted review RESULT is not consumed by its canonical controller execution"
        )

    def _validate_automated_execution_authority(
        self,
        *,
        source_type: str,
        task_id: str,
        task_commit: str,
        run_id: str,
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
            if not isinstance(refs, list) or not any(
                isinstance(item, Mapping) and dict(item) == dict(binding)
                for item in refs
            ):
                continue
            if not self._contains_scalar(record.get("outputs"), run_id):
                continue
            return
        raise ValueError(
            "automated feedback attestation is not rooted in a canonical source-specific execution/run"
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
        path = (self.root / str(event["record_path"])).resolve()
        if self.root not in path.parents:
            raise ValueError("execution record path escapes repository root")
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError("execution record must be a JSON object")
        return value

    @staticmethod
    def _contains_scalar(value: Any, expected: str) -> bool:
        if isinstance(value, Mapping):
            return any(
                ProvenanceValidator._contains_scalar(item, expected)
                for item in value.values()
            )
        if isinstance(value, list):
            return any(
                ProvenanceValidator._contains_scalar(item, expected)
                for item in value
            )
        return str(value) == expected

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
            raise ValueError(
                f"{label} is not on the authorized repository lineage"
            )
