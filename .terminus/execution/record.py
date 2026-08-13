"""Validate one stage result and compile its deterministic transition record."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Mapping

from retrieval.policy import RetrievalPolicy

from .acceptance import StageAcceptancePredicates
from .authority import ExecutionAuthority
from .invocation import StageInvocationBuilder

_SHA = re.compile(r"^[0-9a-f]{40,64}$")
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_EVIDENCE_KINDS = frozenset(
    {"ARTIFACT", "RUN", "PACKET", "RESULT", "COMMIT", "FILE", "EXTERNAL", "OTHER"}
)
_TASK_MUTATING_ROLE_CLASSES = frozenset({"PRODUCER", "FIXER"})
_OUTCOME_SNAPSHOT_PATHS = (
    ".terminus/agents/execution_outcomes.json",
    ".terminus/agents/stage_acceptance_predicates.json",
    ".terminus/agents/schemas/stage_acceptance_predicates.schema.json",
    ".terminus/agents/EXECUTION_RECORD.md",
    ".terminus/agents/stage_contract_completion.json",
)


class ExecutionRecordBuilder:
    """Bind an executor result to one READY invocation and derive its transition."""

    schema_version = "1.0"

    def __init__(self, root: Path, policy: RetrievalPolicy | None = None):
        self.root = root.resolve()
        self.policy = policy or RetrievalPolicy(self.root)
        self.execution_authority = ExecutionAuthority(self.policy)
        self.invocation_builder = StageInvocationBuilder(self.root, self.policy)
        self.outcomes = self._load_json(".terminus/agents/execution_outcomes.json")
        self.completion = self._load_json(".terminus/agents/stage_contract_completion.json")
        self.acceptance = StageAcceptancePredicates(self.root)

    def build(
        self,
        invocation: Mapping[str, Any],
        result: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Return a validated immutable execution record or fail closed."""
        invocation_dict = self._validate_invocation(invocation)
        result_dict = self._validate_result_shape(result)
        if result_dict["invocation_id"] != invocation_dict["invocation_id"]:
            raise ValueError("stage result invocation_id does not match invocation")

        stage_id = str(invocation_dict["stage"]["stage_id"])
        role_id = str(invocation_dict["stage"]["role_id"])
        stage_outcome = self.outcomes["stages"].get(stage_id)
        if not isinstance(stage_outcome, dict):
            raise ValueError(f"no execution outcome contract for stage {stage_id}")

        status = str(result_dict["status"])
        disposition = self._disposition(stage_outcome, status)
        outputs = dict(result_dict["outputs"])
        self._validate_outputs(invocation_dict, stage_outcome, status, outputs)
        task_lineage = self._validate_task_lineage(
            invocation_dict, str(result_dict["output_task_commit"])
        )
        if disposition == "ADVANCE":
            self.acceptance.validate(stage_id, status, outputs)
        evidence_refs = self._validate_evidence_refs(result_dict["evidence_refs"])

        route_key: str | None = None
        blocking_reason: str | None = None
        if disposition == "ADVANCE":
            if "route_key" in result_dict or "blocking_reason" in result_dict:
                raise ValueError("ADVANCE result must not carry route_key or blocking_reason")
            transition = self._advance_transition(invocation_dict)
        elif disposition == "RETRY":
            if "route_key" in result_dict or "blocking_reason" in result_dict:
                raise ValueError("RETRY result must not carry route_key or blocking_reason")
            transition = {
                "action": "RETRY",
                "target": stage_id,
                "target_kind": "STAGE",
                "requires_state_validation": False,
            }
        elif disposition == "ROUTE":
            if "blocking_reason" in result_dict:
                raise ValueError("ROUTE result must not carry blocking_reason")
            route_key = self._resolve_route_key(
                invocation_dict,
                stage_outcome,
                status,
                result_dict.get("route_key"),
            )
            transition = {
                "action": "ROUTE",
                "target": None,
                "target_kind": "ROUTE",
                "route_key": route_key,
                "route_instruction": invocation_dict["routing"]["failure_routes"][route_key],
                "requires_state_validation": False,
            }
        else:
            if "route_key" in result_dict:
                raise ValueError("BLOCK result must not carry route_key")
            blocking_reason = result_dict.get("blocking_reason")
            if not isinstance(blocking_reason, str) or not blocking_reason.strip():
                raise ValueError("BLOCK result requires blocking_reason")
            blocking_reason = blocking_reason.strip()
            transition = {
                "action": "BLOCK",
                "target": None,
                "target_kind": "NONE",
                "requires_state_validation": False,
            }

        required_fields = set(invocation_dict["output_contract"]["required_fields"])
        required_satisfied = all(
            key in outputs and outputs[key] is not None for key in required_fields
        )
        record: dict[str, Any] = {
            "schema_version": self.schema_version,
            "invocation_id": invocation_dict["invocation_id"],
            "stage_id": stage_id,
            "role_id": role_id,
            "authority": invocation_dict["authority"],
            "task_lineage": task_lineage,
            "status": status,
            "disposition": disposition,
            "outputs": outputs,
            "evidence_refs": evidence_refs,
            "transition": transition,
            "validation": {
                "invocation_identity_valid": True,
                "status_legal": True,
                "output_keys_valid": True,
                "required_outputs_satisfied": required_satisfied,
                "task_lineage_valid": True,
                "task_commit_change_authorized": True,
                "acceptance_predicates_satisfied": True,
                "evidence_refs_count": len(evidence_refs),
            },
        }
        if route_key is not None:
            record["route_key"] = route_key
        if blocking_reason is not None:
            record["blocking_reason"] = blocking_reason
        record["record_id"] = self._record_id(record)
        return self._ordered_record(record)

    def _validate_invocation(self, invocation: Mapping[str, Any]) -> dict[str, Any]:
        try:
            packet = json.loads(
                json.dumps(invocation, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("invocation must be JSON-compatible") from exc
        if not isinstance(packet, dict):
            raise ValueError("invocation must be one JSON object")
        if packet.get("readiness") != "READY":
            raise ValueError("execution record requires a READY invocation")
        invocation_id = packet.get("invocation_id")
        if not isinstance(invocation_id, str):
            raise ValueError("invocation missing invocation_id")
        identity_payload = dict(packet)
        identity_payload.pop("invocation_id", None)
        if invocation_id != self.invocation_builder._invocation_id(identity_payload):
            raise ValueError("invocation_id does not match invocation content")

        stage = packet.get("stage")
        authority = packet.get("authority")
        if not isinstance(stage, dict) or not isinstance(authority, dict):
            raise ValueError("invocation stage/authority envelope is invalid")
        stage_id = stage.get("stage_id")
        role_id = stage.get("role_id")
        if not isinstance(stage_id, str) or stage_id not in self.policy.stages:
            raise ValueError("invocation stage_id is not registered")
        if not isinstance(role_id, str):
            raise ValueError("invocation role_id is invalid")
        if role_id not in self.execution_authority.roles_for_stage(stage_id):
            raise ValueError(f"role {role_id} is not authorized to execute stage {stage_id}")

        task_id = authority.get("task_id")
        task_commit = authority.get("task_commit")
        if not isinstance(task_id, str) or not task_id.strip():
            raise ValueError("durable execution requires a reserved task_id before RULE_RESOLUTION")
        if not isinstance(task_commit, str) or not _SHA.fullmatch(task_commit):
            raise ValueError("durable execution requires an exact input task_commit before RULE_RESOLUTION")
        self.invocation_builder._require_git_commit(task_commit, "task_commit")

        control_commit = authority.get("control_plane_commit")
        if not isinstance(control_commit, str):
            raise ValueError("invocation authority missing control_plane_commit")
        self.invocation_builder._require_git_commit(control_commit, "control_plane_commit")
        self.invocation_builder._require_loaded_contract_snapshot(control_commit)
        self._require_outcome_snapshot(control_commit)
        self._validate_canonical_stage_projection(packet)
        return packet

    def _validate_canonical_stage_projection(self, packet: Mapping[str, Any]) -> None:
        stage_id = str(packet["stage"]["stage_id"])
        stage = self.policy.stages[stage_id]
        projected_stage = packet["stage"]
        expected_stage = {
            "stage_id": stage_id,
            "role_id": projected_stage["role_id"],
            "owner": str(stage.get("owner", "")),
            "role_class": str(stage.get("role_class", "")),
            "lifecycle": str(stage.get("lifecycle", "")),
        }
        if projected_stage != expected_stage:
            raise ValueError("invocation stage projection does not match canonical stage contract")
        output = stage.get("output_contract", {})
        expected_output = {
            "allowed_status_values": [str(value) for value in output.get("status_values", [])],
            "required_fields": [str(value) for value in output.get("required_fields", [])],
            "optional_fields": [str(value) for value in output.get("optional_fields", [])],
            "persisted_artifacts": [str(value) for value in output.get("persisted_artifacts", [])],
            "deterministic_validators": [str(value) for value in stage.get("deterministic_validators", [])],
            "semantic_reviewers": [str(value) for value in stage.get("semantic_reviewers", [])],
        }
        if packet.get("output_contract") != expected_output:
            raise ValueError("invocation output contract does not match canonical stage contract")
        expected_routing = {
            "failure_routes": {str(key): str(value) for key, value in stage.get("failure_routes", {}).items()},
            "success_transition": str(stage.get("success_transition", "")),
            "stale_on": [str(value) for value in stage.get("stale_on", [])],
        }
        if packet.get("routing") != expected_routing:
            raise ValueError("invocation routing does not match canonical stage contract")
        exact_reads = list(self.policy.mandatory_exact_paths(stage_id))
        if packet.get("evidence", {}).get("mandatory_exact_reads") != exact_reads:
            raise ValueError("invocation exact-read projection does not match canonical stage contract")

    def _validate_result_shape(self, result: Mapping[str, Any]) -> dict[str, Any]:
        try:
            payload = json.loads(
                json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("stage result must be JSON-compatible") from exc
        if not isinstance(payload, dict):
            raise ValueError("stage result must be one JSON object")
        allowed = {
            "schema_version", "invocation_id", "output_task_commit", "status",
            "outputs", "evidence_refs", "route_key", "blocking_reason",
        }
        unknown = set(payload) - allowed
        if unknown:
            raise ValueError(f"stage result has unknown fields: {sorted(unknown)}")
        required = {
            "schema_version", "invocation_id", "output_task_commit", "status",
            "outputs", "evidence_refs",
        }
        missing = required - set(payload)
        if missing:
            raise ValueError(f"stage result missing fields: {sorted(missing)}")
        if payload["schema_version"] != "1.0":
            raise ValueError("unsupported stage result schema_version")
        if not isinstance(payload["invocation_id"], str):
            raise ValueError("stage result invocation_id must be a string")
        if not isinstance(payload["output_task_commit"], str) or not _SHA.fullmatch(payload["output_task_commit"]):
            raise ValueError("stage result output_task_commit must be a full Git commit")
        if not isinstance(payload["status"], str) or not payload["status"]:
            raise ValueError("stage result status must be a non-empty string")
        if not isinstance(payload["outputs"], dict):
            raise ValueError("stage result outputs must be an object")
        if not isinstance(payload["evidence_refs"], list):
            raise ValueError("stage result evidence_refs must be an array")
        return payload

    def _validate_outputs(
        self,
        invocation: Mapping[str, Any],
        stage_outcome: Mapping[str, Any],
        status: str,
        outputs: Mapping[str, Any],
    ) -> None:
        legal_statuses = set(invocation["output_contract"]["allowed_status_values"])
        if status not in legal_statuses:
            raise ValueError(f"illegal stage status {status}")
        declared = set(invocation["output_contract"]["required_fields"]) | set(
            invocation["output_contract"]["optional_fields"]
        )
        unknown = set(outputs) - declared
        if unknown:
            raise ValueError(f"stage result has undeclared output fields: {sorted(unknown)}")
        if status in set(stage_outcome.get("full_output_statuses", [])):
            missing = [
                name for name in invocation["output_contract"]["required_fields"]
                if name not in outputs or outputs[name] is None
            ]
            if missing:
                raise ValueError(f"status {status} missing required stage outputs: {sorted(missing)}")

    def _validate_task_lineage(self, invocation: Mapping[str, Any], output_task_commit: str) -> dict[str, Any]:
        input_task_commit = str(invocation["authority"]["task_commit"])
        self.invocation_builder._require_git_commit(output_task_commit, "output_task_commit")
        ancestry = subprocess.run(
            ["git", "-C", str(self.root), "merge-base", "--is-ancestor", input_task_commit, output_task_commit],
            capture_output=True,
        )
        if ancestry.returncode != 0:
            raise ValueError("output_task_commit must equal or descend from the invocation task_commit")
        changed = output_task_commit != input_task_commit
        role_class = str(invocation["stage"]["role_class"])
        if changed and role_class not in _TASK_MUTATING_ROLE_CLASSES:
            raise ValueError(f"stage role_class {role_class} may not change the task commit")
        return {
            "input_task_commit": input_task_commit,
            "output_task_commit": output_task_commit,
            "task_changed": changed,
        }

    def _validate_evidence_refs(self, values: list[Any]) -> list[dict[str, Any]]:
        refs: list[dict[str, Any]] = []
        for index, value in enumerate(values):
            if not isinstance(value, dict):
                raise ValueError(f"evidence_refs[{index}] must be an object")
            unknown = set(value) - {"kind", "ref", "content_hash"}
            if unknown:
                raise ValueError(f"evidence_refs[{index}] has unknown fields: {sorted(unknown)}")
            kind = value.get("kind")
            ref = value.get("ref")
            if kind not in _EVIDENCE_KINDS:
                raise ValueError(f"evidence_refs[{index}] has invalid kind")
            if not isinstance(ref, str) or not ref.strip():
                raise ValueError(f"evidence_refs[{index}] has invalid ref")
            item: dict[str, Any] = {"kind": kind, "ref": ref.strip()}
            content_hash = value.get("content_hash")
            if content_hash is not None:
                if not isinstance(content_hash, str) or not _SHA256.fullmatch(content_hash):
                    raise ValueError(f"evidence_refs[{index}] has invalid content_hash")
                item["content_hash"] = content_hash
            refs.append(item)
        return refs

    @staticmethod
    def _disposition(stage_outcome: Mapping[str, Any], status: str) -> str:
        memberships: list[str] = []
        if status in stage_outcome.get("advance_statuses", []):
            memberships.append("ADVANCE")
        if status in stage_outcome.get("route_statuses", {}):
            memberships.append("ROUTE")
        if status in stage_outcome.get("retry_statuses", []):
            memberships.append("RETRY")
        if status in stage_outcome.get("block_statuses", []):
            memberships.append("BLOCK")
        if len(memberships) != 1:
            raise ValueError(f"status {status} must have exactly one execution disposition; found {memberships}")
        return memberships[0]

    def _resolve_route_key(
        self,
        invocation: Mapping[str, Any],
        stage_outcome: Mapping[str, Any],
        status: str,
        supplied: Any,
    ) -> str:
        semantics = stage_outcome.get("route_statuses", {}).get(status)
        if not isinstance(semantics, dict):
            raise ValueError(f"status {status} has no route semantics")
        allowed = set(semantics.get("allowed_route_keys", []))
        route_key = supplied if supplied is not None else semantics.get("default_route_key")
        if not isinstance(route_key, str) or not route_key:
            raise ValueError(f"status {status} requires an explicit route_key")
        if route_key not in allowed:
            raise ValueError(f"route_key {route_key} is not allowed for status {status}: {sorted(allowed)}")
        if route_key not in invocation["routing"]["failure_routes"]:
            raise ValueError(f"route_key {route_key} is not declared by the stage failure_routes")
        return route_key

    def _advance_transition(self, invocation: Mapping[str, Any]) -> dict[str, Any]:
        target = str(invocation["routing"]["success_transition"])
        if target == "END":
            kind = "END"
            requires_state_validation = False
        elif target in self.policy.stages:
            kind = "STAGE"
            requires_state_validation = False
        elif target in self.completion.get("state_contracts", {}):
            kind = "STATE"
            requires_state_validation = True
        else:
            raise ValueError(f"success transition target is not registered: {target}")
        return {
            "action": "ADVANCE",
            "target": target,
            "target_kind": kind,
            "requires_state_validation": requires_state_validation,
        }

    def _require_outcome_snapshot(self, commit: str) -> None:
        for relative in _OUTCOME_SNAPSHOT_PATHS:
            current = (self.root / relative).read_bytes()
            committed = subprocess.run(
                ["git", "-C", str(self.root), "show", f"{commit}:{relative}"],
                check=True,
                capture_output=True,
            ).stdout
            if current != committed:
                raise ValueError(
                    "control_plane_commit does not match loaded execution-record contracts: " + relative
                )

    def _load_json(self, relative: str) -> dict[str, Any]:
        payload = json.loads((self.root / relative).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"{relative} must contain one JSON object")
        return payload

    @staticmethod
    def _record_id(record: Mapping[str, Any]) -> str:
        payload = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return "rec_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _ordered_record(record: Mapping[str, Any]) -> dict[str, Any]:
        ordered = {
            "schema_version": record["schema_version"],
            "record_id": record["record_id"],
            "invocation_id": record["invocation_id"],
            "stage_id": record["stage_id"],
            "role_id": record["role_id"],
            "authority": record["authority"],
            "task_lineage": record["task_lineage"],
            "status": record["status"],
            "disposition": record["disposition"],
            "outputs": record["outputs"],
            "evidence_refs": record["evidence_refs"],
        }
        if "route_key" in record:
            ordered["route_key"] = record["route_key"]
        if "blocking_reason" in record:
            ordered["blocking_reason"] = record["blocking_reason"]
        ordered["transition"] = record["transition"]
        ordered["validation"] = record["validation"]
        return ordered
