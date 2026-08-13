"""Derive current Terminus workflow state from immutable execution records."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from retrieval.policy import RetrievalPolicy

from .ledger import ExecutionLedger
from .record import ExecutionRecordBuilder

_SHA = re.compile(r"^[0-9a-f]{40,64}$")
_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
_STATE_SNAPSHOT_PATHS = (
    ".terminus/agents/stage_contracts.json",
    ".terminus/agents/stage_contract_completion.json",
    ".terminus/agents/execution_outcomes.json",
    ".terminus/agents/workflow_state_contract.json",
    ".terminus/agents/WORKFLOW_STATE.md",
)


class WorkflowStateResolver:
    """Materialize CURRENT/STALE/MISSING/BLOCKED nodes and the next action."""

    schema_version = "1.0"

    def __init__(self, root: Path, policy: RetrievalPolicy | None = None):
        self.root = root.resolve()
        self.policy = policy or RetrievalPolicy(self.root)
        self.completion = self._load_json(
            ".terminus/agents/stage_contract_completion.json"
        )
        self.outcomes = self._load_json(".terminus/agents/execution_outcomes.json")
        self.state_contract = self._load_json(
            ".terminus/agents/workflow_state_contract.json"
        )
        self.record_builder = ExecutionRecordBuilder(self.root, self.policy)
        self.chain = self._canonical_chain()

    def resolve(
        self,
        *,
        task_id: str,
        task_commit: str,
        control_plane_commit: str,
        freshness_overlay: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return one deterministic derived workflow-state snapshot."""
        ledger = ExecutionLedger(self.root, task_id)
        self._require_commit(task_commit, "task_commit")
        self._require_commit(control_plane_commit, "control_plane_commit")
        self._require_contract_snapshot(control_plane_commit)
        overlay, overlay_hash = self._normalize_freshness_overlay(freshness_overlay)

        events = ledger.load(validate_record_files=True)
        latest_by_stage: dict[str, dict[str, Any]] = {}
        event_records: dict[str, dict[str, Any]] = {}
        for event in events:
            record = self._read_record(event["record_path"])
            event_records[event["event_id"]] = record
            latest_by_stage[event["stage_id"]] = event

        nodes: list[dict[str, Any]] = []
        selected_records: dict[str, dict[str, Any]] = {}
        upstream_current = True
        first_non_current: dict[str, Any] | None = None
        previous_node_id: str | None = None
        last_current_stage_sequence = 0

        for index, descriptor in enumerate(self.chain):
            node_id = descriptor["node_id"]
            node_kind = descriptor["node_kind"]
            expected_next = (
                self.chain[index + 1]["node_id"]
                if index + 1 < len(self.chain)
                else "END"
            )
            event: dict[str, Any] | None = None

            if node_kind == "STATE":
                node = self._state_node(
                    node_id,
                    upstream_current=upstream_current,
                    selected_records=selected_records,
                )
            else:
                event = latest_by_stage.get(node_id)
                if not upstream_current:
                    node = {
                        "node_id": node_id,
                        "node_kind": "STAGE",
                        "status": "STALE" if event is not None else "MISSING",
                        "reason": (
                            f"upstream node {previous_node_id} is not current; later historical evidence cannot advance"
                        ),
                    }
                    if event is not None:
                        self._attach_event_identity(node, event)
                elif event is None:
                    node = {
                        "node_id": node_id,
                        "node_kind": "STAGE",
                        "status": "MISSING",
                        "reason": "no execution-ledger event exists for this stage",
                    }
                elif int(event["sequence"]) <= last_current_stage_sequence:
                    node = {
                        "node_id": node_id,
                        "node_kind": "STAGE",
                        "status": "STALE",
                        "reason": (
                            "latest execution record predates the latest current predecessor execution; "
                            "the downstream stage must be rerun even when task/control commits are unchanged"
                        ),
                    }
                    self._attach_event_identity(node, event)
                else:
                    record = event_records[event["event_id"]]
                    node = self._evaluate_stage_record(
                        node_id,
                        expected_next,
                        event,
                        record,
                        task_id=task_id,
                        task_commit=task_commit,
                        control_plane_commit=control_plane_commit,
                        freshness_overlay=overlay,
                    )
                    selected_records[node_id] = record

            nodes.append(node)
            if node["status"] != "CURRENT":
                upstream_current = False
                if first_non_current is None:
                    first_non_current = node
            elif event is not None:
                last_current_stage_sequence = int(event["sequence"])
            previous_node_id = node_id

        next_action = self._next_action(
            first_non_current,
            selected_records=selected_records,
        )
        summary_counter = Counter(node["status"] for node in nodes)
        summary = {
            key: int(summary_counter.get(key, 0))
            for key in ("CURRENT", "STALE", "MISSING", "BLOCKED")
        }
        selected_ids = sorted(
            {
                str(record["record_id"])
                for record in selected_records.values()
                if isinstance(record.get("record_id"), str)
            }
        )
        snapshot: dict[str, Any] = {
            "schema_version": self.schema_version,
            "task_id": task_id,
            "task_commit": task_commit,
            "control_plane_commit": control_plane_commit,
            "ledger_head_event_id": events[-1]["event_id"] if events else None,
            "ledger_event_count": len(events),
            "nodes": nodes,
            "summary": summary,
            "next": next_action,
            "derived_from": {
                "record_ids": selected_ids,
                "freshness_overlay_hash": overlay_hash,
            },
        }
        snapshot["state_snapshot_id"] = self._snapshot_id(snapshot)
        return self._ordered_snapshot(snapshot)

    def materialize(self, snapshot: Mapping[str, Any]) -> Path:
        task_id = snapshot.get("task_id")
        if not isinstance(task_id, str):
            raise ValueError("workflow snapshot is missing task_id")
        ExecutionLedger._validate_task_id(task_id)
        path = self.root / ".terminus" / "workflows" / task_id / "state.json"
        rendered = (
            json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        ).encode("utf-8")
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_bytes() == rendered:
            return path
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_bytes(rendered)
        os.replace(tmp, path)
        return path

    def _canonical_chain(self) -> list[dict[str, str]]:
        states = self.completion.get("state_contracts", {})
        if not isinstance(states, dict):
            raise ValueError("stage completion state_contracts must be an object")
        chain: list[dict[str, str]] = []
        seen_stages: set[str] = set()
        seen_states: set[str] = set()
        current = "RULE_RESOLUTION"
        while True:
            if current in seen_stages:
                raise ValueError(f"workflow success-transition cycle at {current}")
            stage = self.policy.stages.get(current)
            if stage is None:
                raise ValueError(f"workflow references unknown stage {current}")
            seen_stages.add(current)
            chain.append({"node_id": current, "node_kind": "STAGE"})
            target = str(stage.get("success_transition", ""))
            if target == "END":
                break
            if target in states:
                if target in seen_states:
                    raise ValueError(f"workflow state cycle at {target}")
                seen_states.add(target)
                chain.append({"node_id": target, "node_kind": "STATE"})
                state = states[target]
                if not isinstance(state, dict):
                    raise ValueError(f"invalid state contract {target}")
                if state.get("entry_from") != current:
                    raise ValueError(
                        f"state {target} entry_from does not match predecessor {current}"
                    )
                target = str(state.get("exit_to", ""))
            if target not in self.policy.stages:
                raise ValueError(f"workflow transition target is not registered: {target}")
            current = target

        if seen_stages != set(self.policy.stages):
            missing = sorted(set(self.policy.stages) - seen_stages)
            extra = sorted(seen_stages - set(self.policy.stages))
            raise ValueError(
                f"workflow chain does not cover registered stages exactly: missing={missing} extra={extra}"
            )
        return chain

    def _evaluate_stage_record(
        self,
        stage_id: str,
        expected_next: str,
        event: Mapping[str, Any],
        record: Mapping[str, Any],
        *,
        task_id: str,
        task_commit: str,
        control_plane_commit: str,
        freshness_overlay: Mapping[str, Any],
    ) -> dict[str, Any]:
        node: dict[str, Any] = {
            "node_id": stage_id,
            "node_kind": "STAGE",
            "status": "BLOCKED",
            "reason": "execution record has not been validated",
        }
        self._attach_event_identity(node, event)

        authority = record.get("authority")
        if not isinstance(authority, dict):
            node["reason"] = "latest execution record has invalid authority"
            return node
        if authority.get("task_id") != task_id:
            node["status"] = "STALE"
            node["reason"] = "latest execution record belongs to a different task_id"
            return node
        if authority.get("task_commit") != task_commit:
            node["status"] = "STALE"
            node["reason"] = "latest execution record is bound to a different task commit"
            return node
        if authority.get("control_plane_commit") != control_plane_commit:
            node["status"] = "STALE"
            node["reason"] = "latest execution record is bound to a different control-plane commit"
            return node

        semantic_error = self._current_record_error(record, stage_id, expected_next)
        if semantic_error is not None:
            node["reason"] = semantic_error
            return node
        evidence_error = self._freshness_error(record, freshness_overlay)
        if evidence_error is not None:
            node["status"] = "STALE"
            node["reason"] = evidence_error
            return node

        disposition = str(record["disposition"])
        node["disposition"] = disposition
        if disposition == "ADVANCE":
            node["status"] = "CURRENT"
            node["reason"] = f"validated ADVANCE record reaches {expected_next}"
        elif disposition == "ROUTE":
            node["status"] = "BLOCKED"
            node["reason"] = "latest current execution result requires a registered failure route"
            node["route_key"] = str(record["route_key"])
        elif disposition == "RETRY":
            node["status"] = "BLOCKED"
            node["reason"] = "latest current execution result requires this stage to retry"
        else:
            node["status"] = "BLOCKED"
            node["reason"] = "latest current execution result explicitly blocks advancement"
            node["blocking_reason"] = str(record["blocking_reason"])
        return node

    def _current_record_error(
        self,
        record: Mapping[str, Any],
        stage_id: str,
        expected_next: str,
    ) -> str | None:
        try:
            payload = json.loads(
                json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            )
        except (TypeError, ValueError):
            return "latest execution record is not JSON-compatible"
        if not isinstance(payload, dict):
            return "latest execution record is not an object"
        record_id = payload.get("record_id")
        if not isinstance(record_id, str):
            return "latest execution record is missing record_id"
        identity = dict(payload)
        identity.pop("record_id", None)
        if record_id != self.record_builder._record_id(identity):
            return "latest execution record record_id hash is invalid"
        if payload.get("stage_id") != stage_id:
            return "latest execution record stage_id does not match ledger stage"
        role_id = payload.get("role_id")
        if not isinstance(role_id, str) or role_id not in self.policy.allowed_roles_for_stage(stage_id):
            return "latest execution record role is not authorized for this stage"

        stage = self.policy.stages[stage_id]
        output_contract = stage.get("output_contract", {})
        legal_statuses = set(output_contract.get("status_values", []))
        status = payload.get("status")
        if status not in legal_statuses:
            return "latest execution record uses an illegal stage status"
        outcome = self.outcomes.get("stages", {}).get(stage_id)
        if not isinstance(outcome, dict):
            return "stage has no execution outcome contract"
        try:
            expected_disposition = self.record_builder._disposition(outcome, str(status))
        except ValueError as exc:
            return str(exc)
        if payload.get("disposition") != expected_disposition:
            return "latest execution record disposition does not match outcome contract"

        outputs = payload.get("outputs")
        if not isinstance(outputs, dict):
            return "latest execution record outputs are invalid"
        declared = set(output_contract.get("required_fields", [])) | set(
            output_contract.get("optional_fields", [])
        )
        if set(outputs) - declared:
            return "latest execution record contains undeclared output fields"
        if status in set(outcome.get("full_output_statuses", [])):
            missing = [
                name
                for name in output_contract.get("required_fields", [])
                if name not in outputs or outputs[name] is None
            ]
            if missing:
                return f"latest execution record is missing required outputs: {sorted(missing)}"

        transition = payload.get("transition")
        if not isinstance(transition, dict):
            return "latest execution record transition is invalid"
        if expected_disposition == "ADVANCE":
            if transition.get("action") != "ADVANCE" or transition.get("target") != expected_next:
                return "latest ADVANCE transition does not reach the canonical next node"
            expected_kind = (
                "END"
                if expected_next == "END"
                else "STATE"
                if expected_next in self.completion.get("state_contracts", {})
                else "STAGE"
            )
            if transition.get("target_kind") != expected_kind:
                return "latest ADVANCE transition target_kind is invalid"
        elif expected_disposition == "RETRY":
            if transition.get("action") != "RETRY" or transition.get("target") != stage_id:
                return "latest RETRY transition does not target the same stage"
        elif expected_disposition == "ROUTE":
            route_key = payload.get("route_key")
            failure_routes = stage.get("failure_routes", {})
            if (
                transition.get("action") != "ROUTE"
                or not isinstance(route_key, str)
                or route_key not in failure_routes
                or transition.get("route_key") != route_key
                or transition.get("route_instruction") != failure_routes[route_key]
            ):
                return "latest ROUTE transition does not match registered failure routing"
        else:
            if transition.get("action") != "BLOCK":
                return "latest BLOCK transition is invalid"
            reason = payload.get("blocking_reason")
            if not isinstance(reason, str) or not reason.strip():
                return "latest BLOCK record is missing blocking_reason"
        return None

    @staticmethod
    def _freshness_error(
        record: Mapping[str, Any], freshness_overlay: Mapping[str, Any]
    ) -> str | None:
        bindings = freshness_overlay.get("bindings", {})
        if not isinstance(bindings, dict):
            return "freshness overlay bindings are invalid"
        refs = record.get("evidence_refs", [])
        if not isinstance(refs, list):
            return "execution record evidence_refs are invalid"
        for ref in refs:
            if not isinstance(ref, dict):
                return "execution record evidence_ref is invalid"
            name = ref.get("ref")
            if not isinstance(name, str):
                return "execution record evidence_ref has invalid ref"
            current = bindings.get(name)
            if current is None:
                continue
            if not isinstance(current, dict):
                return f"freshness overlay binding for {name} is invalid"
            status = current.get("status")
            if status in {"STALE", "MISSING"}:
                reason = current.get("reason")
                suffix = f": {reason}" if isinstance(reason, str) and reason else ""
                return f"evidence reference {name} is explicitly {status}{suffix}"
            if status != "CURRENT":
                return f"freshness overlay binding for {name} has invalid status"
            prior_hash = ref.get("content_hash")
            current_hash = current.get("content_hash")
            if prior_hash is not None and current_hash is not None and prior_hash != current_hash:
                return f"evidence reference {name} content hash changed"
        return None

    def _state_node(
        self,
        state_id: str,
        *,
        upstream_current: bool,
        selected_records: Mapping[str, Mapping[str, Any]],
    ) -> dict[str, Any]:
        if not upstream_current:
            return {
                "node_id": state_id,
                "node_kind": "STATE",
                "status": "MISSING",
                "reason": "state cannot be current while its predecessor chain is non-current",
            }
        if state_id != "FROZEN_CANDIDATE":
            return {
                "node_id": state_id,
                "node_kind": "STATE",
                "status": "BLOCKED",
                "reason": "no executable state validator is implemented for this registered state",
            }
        passed, checks, reason = self._validate_frozen_candidate(selected_records)
        return {
            "node_id": state_id,
            "node_kind": "STATE",
            "status": "CURRENT" if passed else "BLOCKED",
            "reason": reason,
            "entry_requirements": checks,
        }

    @staticmethod
    def _validate_frozen_candidate(
        records: Mapping[str, Mapping[str, Any]],
    ) -> tuple[bool, list[str], str]:
        checks: list[str] = []

        def require_status(stage: str, status: str) -> bool:
            record = records.get(stage)
            ok = isinstance(record, Mapping) and record.get("status") == status
            checks.append(f"{stage} status == {status}: {'PASS' if ok else 'FAIL'}")
            return ok

        ok = True
        ok &= require_status("FORMAT_GATE", "FORMAT_PASS")
        ok &= require_status("COMPLEXITY_GATE", "PASS")
        ok &= require_status("RUNTIME_AUTHENTICITY", "PASS")
        ok &= require_status("DETERMINISTIC_VALIDATION", "PASS")

        deterministic = records.get("DETERMINISTIC_VALIDATION", {})
        outputs = deterministic.get("outputs", {}) if isinstance(deterministic, Mapping) else {}
        oracle_ok = isinstance(outputs, Mapping) and outputs.get("ORACLE_REWARD") == 1
        nop_ok = isinstance(outputs, Mapping) and outputs.get("NOP_REWARD") == 0
        f2p_ok = isinstance(outputs, Mapping) and outputs.get("F2P_EMPIRICAL_MATRIX") not in (None, [], {})
        p2p_ok = isinstance(outputs, Mapping) and outputs.get("P2P_EMPIRICAL_MATRIX") not in (None, [], {})
        checks.extend(
            [
                f"ORACLE_REWARD == 1: {'PASS' if oracle_ok else 'FAIL'}",
                f"NOP_REWARD == 0: {'PASS' if nop_ok else 'FAIL'}",
                f"F2P empirical matrix present: {'PASS' if f2p_ok else 'FAIL'}",
                f"P2P empirical matrix present: {'PASS' if p2p_ok else 'FAIL'}",
            ]
        )
        ok &= oracle_ok and nop_ok and f2p_ok and p2p_ok

        rules = records.get("RULE_RESOLUTION", {})
        rule_outputs = rules.get("outputs", {}) if isinstance(rules, Mapping) else {}
        conflicts = (
            rule_outputs.get("KNOWN_POLICY_CONFLICTS")
            if isinstance(rule_outputs, Mapping)
            else None
        )
        conflict_free = conflicts in (None, False, "", [], {})
        checks.append(
            f"no unresolved policy conflicts: {'PASS' if conflict_free else 'FAIL'}"
        )
        ok &= conflict_free

        return (
            bool(ok),
            checks,
            "FROZEN_CANDIDATE entry requirements are current"
            if ok
            else "FROZEN_CANDIDATE entry requirements are not all satisfied",
        )

    def _next_action(
        self,
        node: Mapping[str, Any] | None,
        *,
        selected_records: Mapping[str, Mapping[str, Any]],
    ) -> dict[str, Any]:
        if node is None:
            return {"action": "END"}
        node_id = str(node["node_id"])
        if node["node_kind"] == "STATE":
            if node["status"] == "BLOCKED":
                return {
                    "action": "BLOCKED",
                    "state_id": node_id,
                    "owner": str(
                        self.completion["state_contracts"][node_id].get(
                            "owner", "Creation Controller"
                        )
                    ),
                    "blocking_reason": str(node["reason"]),
                }
            return {
                "action": "VALIDATE_STATE",
                "state_id": node_id,
                "owner": str(
                    self.completion["state_contracts"][node_id].get(
                        "owner", "Creation Controller"
                    )
                ),
            }

        stage = self.policy.stages[node_id]
        owner = str(stage.get("owner", ""))
        role_id = self._primary_role_for_stage(node_id)
        inputs = stage.get("input_contract", {})
        base = {
            "stage_id": node_id,
            "owner": owner,
            "primary_role_id": role_id,
            "required_inputs": [str(value) for value in inputs.get("required_fields", [])],
            "optional_inputs": [str(value) for value in inputs.get("optional_fields", [])],
        }
        if node["status"] in {"MISSING", "STALE"}:
            return {"action": "INVOKE_STAGE", **base}

        record = selected_records.get(node_id)
        if not isinstance(record, Mapping):
            return {
                "action": "BLOCKED",
                **base,
                "blocking_reason": "blocked stage has no selected execution record",
            }
        disposition = record.get("disposition")
        if disposition == "RETRY":
            return {"action": "RETRY_STAGE", **base}
        if disposition == "ROUTE":
            transition = record.get("transition", {})
            return {
                "action": "ROUTE",
                **base,
                "route_key": str(record.get("route_key", "")),
                "route_instruction": str(
                    transition.get("route_instruction", "")
                    if isinstance(transition, Mapping)
                    else ""
                ),
            }
        return {
            "action": "BLOCKED",
            **base,
            "blocking_reason": str(
                record.get("blocking_reason")
                or node.get("reason")
                or "stage blocks forward progress"
            ),
        }

    def _primary_role_for_stage(self, stage_id: str) -> str:
        if stage_id == "SYSTEM_ARCHITECTURE":
            return "A2_SYSTEM_ARCHITECT"
        if stage_id == "ENVIRONMENT_BUILD":
            return "A2_ENVIRONMENT_BUILDER"
        stage = self.policy.stages[stage_id]
        owner = stage.get("owner")
        if not isinstance(owner, str) or not owner.strip():
            raise ValueError(f"stage {stage_id} has no primary owner")
        return self.policy._canonical_stage_participant(owner)

    @staticmethod
    def _attach_event_identity(node: dict[str, Any], event: Mapping[str, Any]) -> None:
        node["record_id"] = str(event["record_id"])
        node["invocation_id"] = str(event["invocation_id"])
        node["ledger_event_id"] = str(event["event_id"])

    def _normalize_freshness_overlay(
        self, value: Mapping[str, Any] | None
    ) -> tuple[dict[str, Any], str | None]:
        if value is None:
            return {"schema_version": "1.0", "bindings": {}}, None
        try:
            payload = json.loads(
                json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("freshness overlay must be JSON-compatible") from exc
        if not isinstance(payload, dict) or set(payload) != {"schema_version", "bindings"}:
            raise ValueError("freshness overlay must contain schema_version and bindings only")
        if payload["schema_version"] != "1.0" or not isinstance(payload["bindings"], dict):
            raise ValueError("invalid freshness overlay envelope")
        for ref, binding in payload["bindings"].items():
            if not isinstance(ref, str) or not ref:
                raise ValueError("freshness overlay refs must be non-empty strings")
            if not isinstance(binding, dict):
                raise ValueError(f"freshness overlay binding {ref} must be an object")
            if set(binding) - {"status", "content_hash", "reason"}:
                raise ValueError(f"freshness overlay binding {ref} has unknown fields")
            if binding.get("status") not in {"CURRENT", "STALE", "MISSING"}:
                raise ValueError(f"freshness overlay binding {ref} has invalid status")
            content_hash = binding.get("content_hash")
            if content_hash is not None and (
                not isinstance(content_hash, str) or not _SHA256.fullmatch(content_hash)
            ):
                raise ValueError(f"freshness overlay binding {ref} has invalid content_hash")
            reason = binding.get("reason")
            if reason is not None and (not isinstance(reason, str) or not reason.strip()):
                raise ValueError(f"freshness overlay binding {ref} has invalid reason")
        rendered = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")
        return payload, "sha256:" + hashlib.sha256(rendered).hexdigest()

    def _require_contract_snapshot(self, commit: str) -> None:
        for relative in _STATE_SNAPSHOT_PATHS:
            current = (self.root / relative).read_bytes()
            committed = subprocess.run(
                ["git", "-C", str(self.root), "show", f"{commit}:{relative}"],
                check=True,
                capture_output=True,
            ).stdout
            if current != committed:
                raise ValueError(
                    "control_plane_commit does not match loaded workflow-state contracts: "
                    f"{relative}"
                )

    def _require_commit(self, commit: str, label: str) -> None:
        if not isinstance(commit, str) or not _SHA.fullmatch(commit):
            raise ValueError(f"{label} must be a full hexadecimal Git commit")
        result = subprocess.run(
            ["git", "-C", str(self.root), "cat-file", "-e", f"{commit}^{{commit}}"],
            capture_output=True,
        )
        if result.returncode != 0:
            raise ValueError(f"{label} is not available in repository history: {commit}")

    def _read_record(self, relative: str) -> dict[str, Any]:
        path = (self.root / relative).resolve()
        if self.root not in path.parents:
            raise ValueError("execution record path escapes repository root")
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError(f"execution record {relative} must be an object")
        return value

    def _load_json(self, relative: str) -> dict[str, Any]:
        value = json.loads((self.root / relative).read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError(f"{relative} must contain one JSON object")
        return value

    @staticmethod
    def _snapshot_id(snapshot: Mapping[str, Any]) -> str:
        payload = json.loads(
            json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        )
        payload.pop("state_snapshot_id", None)
        rendered = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return "state_" + hashlib.sha256(rendered.encode("utf-8")).hexdigest()

    @staticmethod
    def _ordered_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "schema_version": snapshot["schema_version"],
            "state_snapshot_id": snapshot["state_snapshot_id"],
            "task_id": snapshot["task_id"],
            "task_commit": snapshot["task_commit"],
            "control_plane_commit": snapshot["control_plane_commit"],
            "ledger_head_event_id": snapshot["ledger_head_event_id"],
            "ledger_event_count": snapshot["ledger_event_count"],
            "nodes": snapshot["nodes"],
            "summary": snapshot["summary"],
            "next": snapshot["next"],
            "derived_from": snapshot["derived_from"],
        }
