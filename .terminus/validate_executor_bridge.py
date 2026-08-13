#!/usr/bin/env python3
"""Validate executor handoff/runner boundaries and API-neutral execution surfaces."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / ".terminus"
sys.path.insert(0, str(T))

from execution.executor import ExecutorMode  # noqa: E402
from execution.handoff import ExecutorHandoffBuilder  # noqa: E402
from execution.invocation import StageInvocationBuilder  # noqa: E402
from execution.runner import ExecutorRunner  # noqa: E402

FILES = [
    T / "execution" / "executor.py",
    T / "execution" / "handoff.py",
    T / "execution" / "runner.py",
    T / "execution" / "runner_cli.py",
    T / "agents" / "schemas" / "executor_handoff.schema.json",
    T / "tests" / "test_executor_bridge.py",
]
FORBIDDEN_EXECUTION_IMPORTS = (
    "ExecutionRecordBuilder",
    "ExecutionLedger",
    "WorkflowStateResolver",
)


def _invocation() -> dict[str, object]:
    packet: dict[str, object] = {
        "schema_version": "1.0",
        "readiness": "READY",
        "stage": {
            "stage_id": "RULE_RESOLUTION",
            "role_id": "CREATION_CONTROLLER",
            "owner": "Creation Controller",
            "role_class": "CONTROLLER",
            "lifecycle": "creation",
        },
        "authority": {
            "control_plane_commit": "a" * 40,
            "task_id": "bridge-validator",
            "task_commit": "b" * 40,
            "policy_versions": {},
        },
        "inputs": {"required": {"CREATION_REQUEST": "validator"}, "optional": {}},
        "missing_required_inputs": [],
        "ignored_input_count": 0,
        "evidence": {
            "retrieval_mode": "EXACT_ONLY",
            "mandatory_exact_reads": [".terminus/AGENT_SYSTEM.md"],
            "authorized_evidence_classes": ["CONTROL_PLANE_POLICY"],
            "excluded_evidence_classes": [],
            "evidence_required": ["rules"],
        },
        "retrieval": {
            "status": "NOT_REQUESTED",
            "query": None,
            "retrieved_context": [],
            "retrieved_chars": 0,
        },
        "output_contract": {
            "allowed_status_values": ["RULES_RESOLVED", "BLOCKED"],
            "required_fields": ["CONTROL_PLANE_COMMIT"],
            "optional_fields": [],
            "persisted_artifacts": [],
            "deterministic_validators": [],
            "semantic_reviewers": [],
        },
        "acceptance_predicates": {},
        "routing": {
            "failure_routes": {},
            "success_transition": "WORK_PACKAGE_RESEARCH",
            "stale_on": [],
        },
    }
    packet["invocation_id"] = StageInvocationBuilder._invocation_id(packet)
    return packet


def main() -> int:
    errors: list[str] = []
    for path in FILES:
        if not path.is_file():
            errors.append(f"missing executor bridge file: {path.relative_to(ROOT)}")

    schema_path = T / "agents" / "schemas" / "executor_handoff.schema.json"
    if schema_path.is_file():
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        if schema.get("$id") != "terminus-executor-handoff-v1":
            errors.append("executor handoff schema ID drift")
        if schema.get("additionalProperties") is not False:
            errors.append("executor handoff schema must fail closed at top level")
        mode_enum = (
            schema.get("properties", {})
            .get("executor_mode", {})
            .get("enum", [])
        )
        if set(mode_enum) != {"MANUAL_CHAT", "LOCAL_COMMAND"}:
            errors.append("executor modes must be exactly MANUAL_CHAT and LOCAL_COMMAND")

    runtime_files = [
        T / "execution" / "executor.py",
        T / "execution" / "handoff.py",
        T / "execution" / "runner.py",
        T / "execution" / "runner_cli.py",
    ]
    for path in runtime_files:
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        for name in FORBIDDEN_EXECUTION_IMPORTS:
            if name in text:
                errors.append(
                    f"{path.relative_to(ROOT)} must not own workflow mutation via {name}"
                )
    runner_text = (T / "execution" / "runner.py").read_text(encoding="utf-8")
    for marker in ("shell=False", "recorded\": False", "workflow_state_mutated\": False"):
        if marker not in runner_text:
            errors.append(f"runner.py missing invariant marker: {marker}")

    invocation = _invocation()
    try:
        manual = ExecutorHandoffBuilder().build(
            invocation,
            executor_mode=ExecutorMode.MANUAL_CHAT,
        )
        local = ExecutorHandoffBuilder().build(
            invocation,
            executor_mode=ExecutorMode.LOCAL_COMMAND,
        )
    except Exception as exc:
        errors.append(f"canonical handoff build failed: {exc}")
        manual = {}
        local = {}
    if manual:
        if manual.get("handoff_id") != ExecutorHandoffBuilder().build(
            invocation,
            executor_mode=ExecutorMode.MANUAL_CHAT,
        ).get("handoff_id"):
            errors.append("MANUAL_CHAT handoff identity is not deterministic")
        if not manual.get("handoff_text"):
            errors.append("MANUAL_CHAT must include paste-ready handoff_text")
        if manual.get("invocation_id") != invocation["invocation_id"]:
            errors.append("handoff invocation identity drift")
    if local and "handoff_text" in local:
        errors.append("LOCAL_COMMAND must not add manual handoff text")

    with tempfile.TemporaryDirectory() as directory:
        script = Path(directory) / "executor.py"
        script.write_text(
            """import json, sys
handoff = json.load(sys.stdin)
json.dump({'schema_version':'1.0','invocation_id':handoff['invocation_id'],'output_task_commit':'b'*40,'status':'RULES_RESOLVED','outputs':{'CONTROL_PLANE_COMMIT':'a'*40},'evidence_refs':[]}, sys.stdout)
""",
            encoding="utf-8",
        )
        response = ExecutorRunner(ROOT).run_local(
            invocation,
            [sys.executable, str(script)],
            timeout_seconds=10,
        )
        if response.get("status") != "EXECUTED":
            errors.append(f"LOCAL_COMMAND canonical round trip failed: {response}")
        if response.get("recorded") is not False:
            errors.append("executor runner must never claim result was recorded")
        if response.get("workflow_state_mutated") is not False:
            errors.append("executor runner must never claim workflow state mutation")
        if response.get("command", {}).get("shell") is not False:
            errors.append("LOCAL_COMMAND must remain shell-free")

    if errors:
        print("Terminus executor-bridge validation FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Terminus executor-bridge validation PASS")
    print(
        "executor_bridge=1.0 modes=MANUAL_CHAT,LOCAL_COMMAND "
        "invocation_binding=exact handoff_identity=deterministic shell=false "
        "stage_result=transport_only record_authority=external_to_executor "
        "ledger_mutation=forbidden workflow_state_mutation=forbidden api_dependency=none"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
