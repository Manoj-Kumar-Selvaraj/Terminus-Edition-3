#!/usr/bin/env python3
"""Validate executor authorization, transport, schema, sandbox and Q boundaries."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / ".terminus"
sys.path.insert(0, str(T))

from execution.authority import ExecutionAuthority  # noqa: E402
from execution.executor import ExecutorMode  # noqa: E402
from execution.handoff import ExecutorHandoffBuilder  # noqa: E402
from execution.invocation import StageInvocationBuilder  # noqa: E402
from execution.schema_validation import ExecutorSchemaValidator  # noqa: E402
from retrieval.models import InvocationContext  # noqa: E402
from retrieval.policy import RetrievalPolicy  # noqa: E402

FILES = [
    T / "execution" / "executor.py",
    T / "execution" / "handoff.py",
    T / "execution" / "invocation_guard.py",
    T / "execution" / "sandbox.py",
    T / "execution" / "schema_validation.py",
    T / "execution" / "runner.py",
    T / "execution" / "runner_cli.py",
    T / "execution" / "controller_cli.py",
    T / "execution" / "quality_executor.py",
    T / "execution" / "quality_executor_cli.py",
    T / "execution" / "quality_backend.py",
    T / "execution" / "quality_budget.py",
    T / "execution" / "quality_dispatch_cli.py",
    T / "execution" / "quality_lifecycle_record.py",
    T / "agents" / "schemas" / "executor_handoff.schema.json",
    T / "agents" / "schemas" / "stage_result.schema.json",
    T / "tests" / "test_executor_bridge.py",
    T / "tests" / "test_quality_executor.py",
    T / "tests" / "test_quality_lifecycle_record.py",
    ROOT / ".github" / "workflows" / "terminus-quality-executor.yml",
    ROOT / ".github" / "workflows" / "terminus-quality-lifecycle.yml",
    ROOT / ".github" / "workflows" / "terminus-quality-lifecycle-collect.yml",
]


def _head() -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _invocation(stage_id: str = "RULE_RESOLUTION") -> dict[str, object]:
    commit = _head()
    policy = RetrievalPolicy(ROOT)
    role = ExecutionAuthority(policy).primary_role_for_stage(stage_id)
    fields = policy.stages[stage_id]["input_contract"]["required_fields"]
    return StageInvocationBuilder(ROOT, policy).build(
        InvocationContext(
            stage_id=stage_id,
            role_id=role,
            task_id="bridge-validator",
            task_commit=commit,
            control_plane_commit=commit,
        ),
        {str(field): {"validator": str(field)} for field in fields},
    )


def main() -> int:
    errors: list[str] = []
    for path in FILES:
        if not path.is_file():
            errors.append(f"missing executor bridge file: {path.relative_to(ROOT)}")

    handoff_schema_path = T / "agents" / "schemas" / "executor_handoff.schema.json"
    schema = json.loads(handoff_schema_path.read_text(encoding="utf-8"))
    if schema.get("$id") != "terminus-executor-handoff-v1":
        errors.append("executor handoff schema ID drift")
    if schema.get("additionalProperties") is not False:
        errors.append("executor handoff schema must fail closed at top level")

    handoff_text = (T / "execution" / "handoff.py").read_text(encoding="utf-8")
    runner_text = (T / "execution" / "runner.py").read_text(encoding="utf-8")
    sandbox_text = (T / "execution" / "sandbox.py").read_text(encoding="utf-8")
    guard_text = (T / "execution" / "invocation_guard.py").read_text(encoding="utf-8")
    controller_text = (T / "execution" / "controller_cli.py").read_text(encoding="utf-8")
    quality_text = (T / "execution" / "quality_executor.py").read_text(encoding="utf-8")
    backend_text = (T / "execution" / "quality_backend.py").read_text(encoding="utf-8")
    budget_text = (T / "execution" / "quality_budget.py").read_text(encoding="utf-8")
    lifecycle_record_text = (T / "execution" / "quality_lifecycle_record.py").read_text(
        encoding="utf-8"
    )
    quality_workflow = (
        ROOT / ".github" / "workflows" / "terminus-quality-executor.yml"
    ).read_text(encoding="utf-8")
    lifecycle_workflow = (
        ROOT / ".github" / "workflows" / "terminus-quality-lifecycle.yml"
    ).read_text(encoding="utf-8")
    q8_collector = (
        ROOT / ".github" / "workflows" / "terminus-quality-lifecycle-collect.yml"
    ).read_text(encoding="utf-8")

    for marker in ("CanonicalInvocationGuard", "handoff_id", "validate_handoff"):
        if marker not in handoff_text:
            errors.append(f"handoff.py missing hardened marker: {marker}")
    for marker in (
        "shell=False",
        "OUTPUT_LIMIT_EXCEEDED",
        "validate_stage_result",
        '"recorded": False',
        '"workflow_state_mutated": False',
    ):
        if marker not in runner_text:
            errors.append(f"runner.py missing invariant marker: {marker}")
    for marker in ("--unshare-all", "--ro-bind", "--tmpfs", "bwrap"):
        if marker not in sandbox_text:
            errors.append(f"sandbox.py missing isolation marker: {marker}")
    if "ExecutionRecordBuilder" not in guard_text or "_validate_invocation" not in guard_text:
        errors.append("pre-execution guard must reuse canonical recorder invocation validation")

    quality_markers = (
        "select_backend",
        "materialize_projection",
        "validate_review_result",
        "CURSOR_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        'prompt_cache_key=cache_key(packet)',
        '"fallback_attempted": False',
        '"prior_review_projected": False',
        '"git_history_projected": False',
        "difficulty simulation is API-key-only",
    )
    for marker in quality_markers:
        if marker not in quality_text:
            errors.append(f"quality_executor.py missing invariant marker: {marker}")

    for marker in (
        "Q_CURSOR_ENABLED",
        "Q_OPENAI_ENABLED",
        "Q_CLAUDE_ENABLED",
        "Q_STB_AI_ENABLED",
        "STB_AI_API_KEY",
        "https://api.portkey.ai/v1",
        "exactly one Q backend flag",
        'result["selected_backend"]',
    ):
        if marker not in backend_text and marker not in quality_workflow:
            errors.append(f"Q backend routing missing invariant marker: {marker}")

    for marker in (
        'Q_ROLE_LIMITS["Spec-Test Contract Reviewer"] = 3',
        'Q_ROLE_LIMITS["Production Logic Auditor"] = 2',
        'STATE_DIR = "q-runs"',
        'return "q8-gpt"',
        'return "q8-claude"',
        "execution budget exhausted",
    ):
        if marker not in budget_text:
            errors.append(f"quality budget missing invariant marker: {marker}")

    lifecycle_record_markers = (
        "StageInvocationBuilder",
        "QUALITY_INTERLOCK_PASS",
        'result["route_key"] = "Q4_REVISE"',
        'result["route_key"] = "Q6_REVISE"',
        "MODEL_DIAGNOSTIC_GPT",
        "MODEL_DIAGNOSTIC_CLAUDE",
        "controller_cli.py record",
    )
    for marker in lifecycle_record_markers:
        if marker not in lifecycle_record_text and marker not in lifecycle_workflow and marker not in q8_collector:
            errors.append(f"quality lifecycle record bridge missing marker: {marker}")

    lifecycle_markers = (
        "QUALITY_INTERLOCK",
        "MODEL_DIAGNOSTIC_GPT",
        "MODEL_DIAGNOSTIC_CLAUDE",
        "spec-test-contract",
        "production-logic",
        "difficulty-sim-gpt",
        "difficulty-sim-claude",
        "uses: ./.github/workflows/terminus-quality-executor.yml",
        "validate_quality_interlock.py",
        "terminus-quality-lifecycle-collect.yml",
        "quality_lifecycle_record.py",
        "controller_cli.py record",
    )
    for marker in lifecycle_markers:
        if marker not in lifecycle_workflow:
            errors.append(f"quality lifecycle workflow missing marker: {marker}")

    controller_markers = (
        "QUALITY_LIFECYCLE_WORKFLOW",
        "QUALITY_INTERLOCK",
        "MODEL_DIAGNOSTIC_GPT",
        "MODEL_DIAGNOSTIC_CLAUDE",
        '"quality_lifecycle": True',
        '"credential_policy": "existing selected secret only; login/refresh/fallback forbidden"',
    )
    for marker in controller_markers:
        if marker not in controller_text:
            errors.append(f"controller quality routing missing marker: {marker}")

    for marker in (
        "GPT diagnostic received non-GPT Q8 packet",
        "Claude diagnostic received non-Claude Q8 packet",
        "Q8 packet is stale for task tree",
        "quality_lifecycle_record.py",
        "controller_cli.py record",
    ):
        if marker not in q8_collector:
            errors.append(f"Q8 lifecycle isolation/recording missing marker: {marker}")

    if "--resume" in quality_text or "--resume" in quality_workflow:
        errors.append("packet-bound quality executor must always start a fresh Cursor session")
    for secret in ("CURSOR_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "STB_AI_API_KEY"):
        if secret not in quality_workflow:
            errors.append(f"quality workflow missing secret boundary: {secret}")
    for flag in ("Q_CURSOR_ENABLED", "Q_OPENAI_ENABLED", "Q_CLAUDE_ENABLED", "Q_STB_AI_ENABLED"):
        if flag not in quality_workflow:
            errors.append(f"quality workflow missing repository backend flag: {flag}")
    for text, label in (
        (quality_workflow, "quality workflow"),
        (lifecycle_workflow, "quality lifecycle"),
        (q8_collector, "Q8 collector"),
        (controller_text, "controller quality routing"),
    ):
        for forbidden in ("keys-refresh", "SNORKEL_API_KEY"):
            if forbidden in text:
                errors.append(f"{label} contains forbidden credential refresh/login marker: {forbidden}")
    for marker in ("terminus-quality-budget", "quality_budget.py", "quality_dispatch_cli.py"):
        if marker not in quality_workflow:
            errors.append(f"quality workflow missing durable execution-budget marker: {marker}")
    for marker in ("Resolve or generate exact review packet", ".terminus/new_review_packet.py"):
        if marker not in quality_workflow:
            errors.append(f"quality workflow missing lifecycle packet-generation marker: {marker}")

    invocation = _invocation()
    builder = ExecutorHandoffBuilder(ROOT)
    schemas = ExecutorSchemaValidator(ROOT)
    try:
        manual = builder.build(invocation, executor_mode=ExecutorMode.MANUAL_CHAT)
        local = builder.build(invocation, executor_mode=ExecutorMode.LOCAL_COMMAND)
        schemas.validate_handoff(manual)
        schemas.validate_handoff(local)
    except Exception as exc:
        errors.append(f"canonical handoff build/schema validation failed: {exc}")
        manual = {}
        local = {}

    if manual:
        repeated = builder.build(invocation, executor_mode=ExecutorMode.MANUAL_CHAT)
        if manual.get("handoff_id") != repeated.get("handoff_id"):
            errors.append("MANUAL_CHAT handoff identity is not deterministic")
        if "handoff_id" not in manual.get("result_contract", {}).get(
            "required_top_level_fields", []
        ):
            errors.append("executor StageResult contract must require handoff_id")
    if local and "handoff_text" in local:
        errors.append("LOCAL_COMMAND must not add manual handoff text")

    try:
        builder.build(
            _invocation("WORK_PACKAGE_RESEARCH"),
            executor_mode=ExecutorMode.LOCAL_COMMAND,
        )
        errors.append("LOCAL_COMMAND incorrectly accepted a mutating producer stage")
    except ValueError:
        pass

    if errors:
        print("Terminus executor-bridge validation FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Terminus executor-bridge validation PASS")
    print(
        "executor_bridge=1.5 modes=MANUAL_CHAT,LOCAL_COMMAND "
        "quality_modes=CURSOR_AUTO,DIRECT_OPENAI,DIRECT_CLAUDE,STB_AI_GATEWAY "
        "q_selection=exactly_one_global_flag q_isolation=packet_bound_git_history_free "
        "q_fallback=forbidden q_validation=deterministic_schema_and_binding "
        "q_budget=Q4x3,Q6x2,OTHERx1,Q8_GPTx1,Q8_CLAUDEx1 "
        "q_lifecycle=QUALITY_INTERLOCK,Q8_GPT,Q8_CLAUDE "
        "q_lifecycle_record=canonical_stage_invocation_result_ledger "
        "credential_refresh=forbidden difficulty=api_key_only "
        "record_authority=canonical_controller ledger_mutation=controller_record_only"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
