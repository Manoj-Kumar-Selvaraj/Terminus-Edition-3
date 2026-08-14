"""Pure deterministic executor handoff projection shared by builder and recorder."""

from __future__ import annotations

import json
from typing import Any, Mapping

from .executor import ExecutorMode, stable_id

_MUTATING_ROLE_CLASSES = frozenset({"PRODUCER", "FIXER"})

_BASE_DO = (
    "Act only as the role and stage named in this invocation.",
    "Read every mandatory_exact_reads path exactly at the bound control-plane commit before deciding the result.",
    "Use only the invocation inputs and evidence authorized by the invocation; do not broaden scope from chat memory.",
    "Return one StageResult JSON object whose handoff_id and invocation_id exactly match this handoff.",
    "Use only legal status values and declared output fields.",
    "Preserve immutable evidence references for every acceptance-sensitive claim.",
    "If authorized MANUAL_CHAT work changes task files, commit them and return the descendant output_task_commit; otherwise return the bound task commit.",
)
_BASE_DO_NOT = (
    "Do not decide or write the next workflow stage; the controller derives transitions.",
    "Do not write execution records, ledgers, materialized workflow state, or submission readiness directly.",
    "Do not claim PASS merely because required output keys exist; acceptance predicates still apply.",
    "Do not weaken, remove, or reinterpret evidence restrictions, acceptance predicates, routing, or policy bindings.",
    "Do not expose chain-of-thought, private reasoning, scratchpad content, hidden tests, or unauthorized evidence.",
    "Do not fabricate evidence references, reviewer verdicts, external run results, task commits, or policy versions.",
)


def executor_mode_allowed(invocation: Mapping[str, Any], mode: ExecutorMode) -> bool:
    if mode is not ExecutorMode.LOCAL_COMMAND:
        return True
    return str(invocation["stage"].get("role_class")) not in _MUTATING_ROLE_CLASSES


def identity_packet(
    invocation: Mapping[str, Any],
    mode: ExecutorMode,
) -> dict[str, Any]:
    """Build the exact deterministic handoff body before handoff_id is attached."""

    if not executor_mode_allowed(invocation, mode):
        raise ValueError(
            "LOCAL_COMMAND is read-only and unavailable for PRODUCER/FIXER stages; use MANUAL_CHAT"
        )
    stage = invocation["stage"]
    authority = invocation["authority"]
    output_contract = invocation["output_contract"]
    result_contract = {
        "schema_version": "1.0",
        "invocation_id": invocation["invocation_id"],
        "required_top_level_fields": [
            "schema_version",
            "handoff_id",
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
    do = list(_BASE_DO)
    do_not = list(_BASE_DO_NOT)
    if mode is ExecutorMode.LOCAL_COMMAND:
        do.append(
            "Treat the projected workspace as read-only and return the bound input task commit unchanged."
        )
        do_not.append(
            "Do not mutate task files; LOCAL_COMMAND is a read-only sandbox in this version."
        )
    packet: dict[str, Any] = {
        "schema_version": "1.0",
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
    if mode is ExecutorMode.MANUAL_CHAT:
        packet["handoff_text"] = manual_chat_text(packet)
    return packet


def handoff_id(invocation: Mapping[str, Any], mode: ExecutorMode) -> str:
    return stable_id("handoff", identity_packet(invocation, mode))


def accepted_handoff_ids(invocation: Mapping[str, Any]) -> frozenset[str]:
    values = {handoff_id(invocation, ExecutorMode.MANUAL_CHAT)}
    if executor_mode_allowed(invocation, ExecutorMode.LOCAL_COMMAND):
        values.add(handoff_id(invocation, ExecutorMode.LOCAL_COMMAND))
    return frozenset(values)


def manual_chat_text(packet: Mapping[str, Any]) -> str:
    invocation = packet["invocation"]
    result_contract = packet["result_contract"]
    lines = [
        "Execute the following Terminus stage invocation.",
        "",
        f"Stage: {packet['stage']['stage_id']}",
        f"Role: {packet['stage']['role_id']}",
        f"Invocation ID: {packet['invocation_id']}",
        "The transport wrapper will provide the exact Handoff ID; echo it in the StageResult.",
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
