"""Build deterministic executor handoffs from READY stage invocations."""

from __future__ import annotations

import json
from typing import Any, Mapping

from .executor import ExecutorMode, canonical_json, stable_id, validate_executable_invocation


class ExecutorHandoffBuilder:
    """Project an invocation into a bounded executor-neutral handoff packet."""

    schema_version = "1.0"

    def build(
        self,
        invocation: Mapping[str, Any],
        *,
        executor_mode: ExecutorMode | str,
    ) -> dict[str, Any]:
        validate_executable_invocation(invocation)
        mode = ExecutorMode(executor_mode)
        stage = invocation["stage"]
        authority = invocation["authority"]
        output_contract = invocation["output_contract"]

        result_contract = {
            "schema_version": "1.0",
            "invocation_id": invocation["invocation_id"],
            "required_top_level_fields": [
                "schema_version",
                "invocation_id",
                "output_task_commit",
                "status",
                "outputs",
                "evidence_refs",
            ],
            "optional_top_level_fields": ["route_key", "blocking_reason"],
            "allowed_status_values": list(output_contract["allowed_status_values"]),
            "required_output_fields": list(output_contract["required_fields"]),
            "optional_output_fields": list(output_contract["optional_fields"]),
        }

        do = [
            "Act only as the role and stage named in this invocation.",
            "Read every mandatory_exact_reads path exactly at the bound control-plane commit before deciding the result.",
            "Use only the invocation inputs and evidence authorized by the invocation; do not broaden scope from chat memory.",
            "Return one StageResult JSON object whose invocation_id exactly matches this handoff.",
            "Use only legal status values and declared output fields.",
            "Preserve immutable evidence references for every acceptance-sensitive claim.",
            "If authorized work changes task files, commit them and return the descendant output_task_commit; otherwise return the bound task commit.",
        ]
        do_not = [
            "Do not decide or write the next workflow stage; the controller derives transitions.",
            "Do not write execution records, ledgers, materialized workflow state, or submission readiness directly.",
            "Do not claim PASS merely because required output keys exist; acceptance predicates still apply.",
            "Do not weaken, remove, or reinterpret evidence restrictions, acceptance predicates, routing, or policy bindings.",
            "Do not expose chain-of-thought, private reasoning, scratchpad content, hidden tests, or unauthorized evidence.",
            "Do not fabricate evidence references, reviewer verdicts, external run results, task commits, or policy versions.",
        ]

        packet: dict[str, Any] = {
            "schema_version": self.schema_version,
            "executor_mode": mode.value,
            "invocation_id": invocation["invocation_id"],
            "stage": {
                "stage_id": stage["stage_id"],
                "role_id": stage["role_id"],
                "owner": stage["owner"],
                "role_class": stage["role_class"],
            },
            "authority": dict(authority),
            "do": do,
            "do_not": do_not,
            "result_contract": result_contract,
            "invocation": dict(invocation),
        }
        packet["handoff_id"] = stable_id("handoff", packet)
        if mode is ExecutorMode.MANUAL_CHAT:
            packet["handoff_text"] = self._manual_chat_text(packet)
        return packet

    @staticmethod
    def _manual_chat_text(packet: Mapping[str, Any]) -> str:
        invocation = packet["invocation"]
        result_contract = packet["result_contract"]
        lines = [
            "Execute the following Terminus stage invocation.",
            "",
            f"Stage: {packet['stage']['stage_id']}",
            f"Role: {packet['stage']['role_id']}",
            f"Invocation ID: {packet['invocation_id']}",
            "",
            "DO:",
        ]
        lines.extend(f"- {item}" for item in packet["do"])
        lines.extend(["", "DO NOT:"])
        lines.extend(f"- {item}" for item in packet["do_not"])
        lines.extend(
            [
                "",
                "Return format:",
                "- Return exactly one JSON object and no surrounding prose.",
                "- The object must satisfy the StageResult contract summarized below.",
                "",
                "StageResult contract:",
                json.dumps(result_contract, indent=2, sort_keys=True, ensure_ascii=False),
                "",
                "Authoritative invocation packet:",
                json.dumps(invocation, indent=2, sort_keys=True, ensure_ascii=False),
            ]
        )
        return "\n".join(lines) + "\n"

    @staticmethod
    def identity_payload(packet: Mapping[str, Any]) -> str:
        """Expose deterministic transport identity for validators/tests."""

        copy = dict(packet)
        copy.pop("handoff_id", None)
        return canonical_json(copy)
