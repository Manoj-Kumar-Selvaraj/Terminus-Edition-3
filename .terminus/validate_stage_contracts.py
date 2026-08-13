#!/usr/bin/env python3
"""Validate structured stage contracts and lifecycle invariants."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / ".terminus"
AGENTS = T / "agents"


def load(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.is_file():
        errors.append(f"missing required file: {path.relative_to(ROOT)}")
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON in {path.relative_to(ROOT)}: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{path.relative_to(ROOT)} must contain one object")
        return {}
    return value


def sset(value: Any) -> set[str]:
    return {item for item in value if isinstance(item, str)} if isinstance(value, list) else set()


def main() -> int:
    errors: list[str] = []
    registry = load(AGENTS / "stage_contracts.json", errors)
    visibility = load(AGENTS / "evidence_visibility.json", errors)
    completion = load(AGENTS / "stage_contract_completion.json", errors)
    schema = load(AGENTS / "schemas" / "stage_contracts.schema.json", errors)
    outcomes = load(AGENTS / "execution_outcomes.json", errors)
    predicates = load(AGENTS / "stage_acceptance_predicates.json", errors)
    raw_stages = registry.get("stages", [])
    stages = {item.get("id"): item for item in raw_stages if isinstance(item, dict) and isinstance(item.get("id"), str)} if isinstance(raw_stages, list) else {}
    stage_ids = set(stages)
    if registry.get("contract_version") != "1.0" or not stage_ids or len(stages) != len(raw_stages):
        errors.append("stage registry identity/version is invalid")
    visibility_ids = {item.get("stage_id") for item in visibility.get("stages", []) if isinstance(item, dict) and isinstance(item.get("stage_id"), str)}
    if visibility_ids != stage_ids:
        errors.append(f"stage/visibility coverage mismatch missing={sorted(stage_ids-visibility_ids)} extra={sorted(visibility_ids-stage_ids)}")
    if set(outcomes.get("stages", {})) != stage_ids:
        errors.append("execution outcomes must cover registered stages exactly")
    required_keys = {"id","lifecycle","owner","role_class","policy_files","prompt_files","input_contract","output_contract","evidence_required","deterministic_validators","semantic_reviewers","failure_routes","success_transition","stale_on"}
    for stage_id, stage in stages.items():
        if set(stage) != required_keys:
            errors.append(f"{stage_id}: stage key set drift")
        statuses = sset(stage.get("output_contract", {}).get("status_values", []))
        outcome = outcomes.get("stages", {}).get(stage_id, {})
        partition = list(outcome.get("advance_statuses", [])) + list(outcome.get("retry_statuses", [])) + list(outcome.get("block_statuses", [])) + list(outcome.get("route_statuses", {}).keys())
        if set(partition) != statuses or len(partition) != len(set(partition)):
            errors.append(f"{stage_id}: outcome partition must cover legal statuses exactly once")

    instruction_required = sset(stages.get("INSTRUCTION_DRAFT", {}).get("input_contract", {}).get("required_fields", []))
    if instruction_required != {"CREATION_RULE_CONTEXT","APPROVED_SOLVER_VISIBLE_REQUIREMENT_CONTRACT","TASK_WRITING_PROFILE"}:
        errors.append("INSTRUCTION_DRAFT must consume the approved solver-visible requirement projection")
    if ".terminus/agents/A2_PHASE_PROMPTS.md" not in stages.get("SYSTEM_ARCHITECTURE", {}).get("prompt_files", []):
        errors.append("SYSTEM_ARCHITECTURE must bind A2 phase prompt")
    environment = stages.get("ENVIRONMENT_BUILD", {})
    if ".terminus/agents/A2_PHASE_PROMPTS.md" not in environment.get("prompt_files", []) or "SOLVER_VISIBLE_DOC_PLAN" not in environment.get("input_contract", {}).get("required_fields", []) or "ARCHITECTURE_GAP" not in environment.get("output_contract", {}).get("status_values", []):
        errors.append("ENVIRONMENT_BUILD A2 phase contract drift")
    assembly = stages.get("ASSEMBLY", {})
    if assembly.get("success_transition") != "COMPLEXITY_GATE" or "FROZEN_CANDIDATE" in assembly.get("output_contract", {}).get("status_values", []) or ".terminus/agents/A9_ASSEMBLY_PROMPT.md" not in assembly.get("prompt_files", []):
        errors.append("ASSEMBLY must remain assembly-only and advance to complexity")
    for stage_id, stage in stages.items():
        if stage.get("lifecycle") == "creation" and {"Q4 Spec-Test Contract Reviewer","Q6 Production Logic Auditor"} & set(stage.get("semantic_reviewers", [])):
            errors.append(f"{stage_id}: Q4/Q6 must remain post-freeze independent")
    frozen = completion.get("state_contracts", {}).get("FROZEN_CANDIDATE", {})
    if frozen.get("owner") != "Creation Controller" or frozen.get("entry_from") != "DETERMINISTIC_VALIDATION" or frozen.get("exit_to") != "QUALITY_INTERLOCK" or stages.get("DETERMINISTIC_VALIDATION", {}).get("success_transition") != "FROZEN_CANDIDATE":
        errors.append("FROZEN_CANDIDATE boundary drift")

    for source, target in [("PRE_LLMAJ","MODEL_DIAGNOSTIC_GPT"),("MODEL_DIAGNOSTIC_GPT","MODEL_DIAGNOSTIC_CLAUDE"),("MODEL_DIAGNOSTIC_CLAUDE","MODEL_DIAGNOSTIC_AGGREGATE"),("MODEL_DIAGNOSTIC_AGGREGATE","HARBOR_LLMAJ"),("HARBOR_LLMAJ","OFFICIAL_MODEL_TRIALS"),("OFFICIAL_MODEL_TRIALS","TRIAL_ANALYSIS"),("TRIAL_ANALYSIS","DIFFICULTY_ASSESSMENT"),("DIFFICULTY_ASSESSMENT","FINAL_REVIEW"),("FINAL_REVIEW","SUBMISSION_READY"),("SUBMISSION_READY","END")]:
        if stages.get(source, {}).get("success_transition") != target:
            errors.append(f"{source} must advance to {target}")

    vis_by_stage = {item.get("stage_id"): item for item in visibility.get("stages", []) if isinstance(item, dict)}
    q8_exclusions = {"PRIVATE_CREATION_DESIGN","SOLUTION_ORACLE","VERIFIER_PRIVATE","CURRENT_REVIEW_PACKET","PRIOR_REVIEW_RESULTS","CI_RUNTIME_EVIDENCE","DURABLE_SESSION_STATE","MODEL_TRIAL_EVIDENCE","FINAL_PACKAGE_EVIDENCE"}
    for stage_id, perspective in (("MODEL_DIAGNOSTIC_GPT","GPT_PERSPECTIVE"),("MODEL_DIAGNOSTIC_CLAUDE","CLAUDE_PERSPECTIVE")):
        stage = stages.get(stage_id, {})
        if stage.get("role_class") != "SIMULATOR" or set(stage.get("input_contract", {}).get("required_fields", [])) != {"PRE_LLMAJ_PASS","SOLVER_VISIBLE_TASK"}:
            errors.append(f"{stage_id}: simulator/input isolation drift")
        vis = vis_by_stage.get(stage_id, {})
        if vis.get("retrieval_mode") != "SOLVER_VISIBLE_ONLY" or not q8_exclusions <= set(vis.get("excluded_evidence_classes", [])):
            errors.append(f"{stage_id}: evidence isolation drift")
        pred = predicates.get("stages", {}).get(stage_id, {})
        if not any(p.get("path") == "PERSPECTIVE" and p.get("value") == perspective for plist in pred.values() if isinstance(plist, list) for p in plist if isinstance(p, dict)):
            errors.append(f"{stage_id}: perspective predicate missing")
    if "GPT_PERSPECTIVE_RESULT" in stages.get("MODEL_DIAGNOSTIC_CLAUDE", {}).get("input_contract", {}).get("required_fields", []):
        errors.append("Claude Q8 perspective must not receive GPT result")
    aggregate = stages.get("MODEL_DIAGNOSTIC_AGGREGATE", {})
    if aggregate.get("role_class") != "CONTROLLER" or set(aggregate.get("input_contract", {}).get("required_fields", [])) != {"GPT_PERSPECTIVE_RESULT","CLAUDE_PERSPECTIVE_RESULT"}:
        errors.append("Q8 aggregate contract drift")
    harbor = stages.get("HARBOR_LLMAJ", {})
    if harbor.get("role_class") != "EXTERNAL_GATE" or "DISPATCHED" not in harbor.get("output_contract", {}).get("status_values", []) or not {"HARBOR_RUN_ID","HARBOR_RESULT","HARBOR_EVIDENCE"} <= set(harbor.get("output_contract", {}).get("required_fields", [])):
        errors.append("Harbor must be a first-class pending external gate")
    official = stages.get("OFFICIAL_MODEL_TRIALS", {})
    if official.get("role_class") != "EXTERNAL_GATE" or "DISPATCHED" not in official.get("output_contract", {}).get("status_values", []) or "HARBOR_LLMAJ_PASS" not in official.get("input_contract", {}).get("required_fields", []):
        errors.append("official trials external-gate contract drift")
    difficulty = stages.get("DIFFICULTY_ASSESSMENT", {})
    required_difficulty = {"EMPIRICAL_TIER","DECLARED_TIER","COMBINED_SUCCESS_RATE","PER_TEST_SOLVABILITY","ZERO_OF_TEN_TESTS","TRAJECTORY_ANALYSIS_RESULT"}
    if difficulty.get("owner") != "Difficulty Reviewer" or difficulty.get("role_class") != "REVIEWER" or not required_difficulty <= set(difficulty.get("output_contract", {}).get("required_fields", [])) or ".terminus/analyze_difficulty.py" not in difficulty.get("deterministic_validators", []):
        errors.append("DIFFICULTY_ASSESSMENT contract drift")
    if "DIFFICULTY_ASSESSMENT_PASS" not in stages.get("FINAL_REVIEW", {}).get("input_contract", {}).get("required_fields", []):
        errors.append("FINAL_REVIEW must require DIFFICULTY_ASSESSMENT_PASS")
    if schema.get("$id") != "terminus-stage-contracts-v1":
        errors.append("stage contract schema ID drift")

    if errors:
        print("Terminus stage-contract validation FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Terminus stage-contract validation PASS")
    print(f"contract_version=1.0 visibility_version={visibility.get('visibility_version')} completion_version={completion.get('completion_version')} stages={len(stage_ids)} visibility_stages={len(visibility_ids)} evidence_classes={len(visibility.get('evidence_classes', {}))} structured_bindings=present retrieval_boundaries=classified lifecycle_completion=explicit freeze_state=controller_only prefreeze_independence=preserved requirement_projection=bound q8=dual_isolated harbor=mandatory_external difficulty=empirical_gate")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
