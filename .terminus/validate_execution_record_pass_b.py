#!/usr/bin/env python3
"""Registry-driven execution-record validation for the Pass-B lifecycle."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from urllib.parse import quote
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / ".terminus"
sys.path.insert(0, str(T))

_RECORD_REFERENCE_FIXTURE = ".terminus/tests/fixtures/record_reference_ids.json"

from execution.authority import ExecutionAuthority  # noqa: E402
from execution.invocation import StageInvocationBuilder  # noqa: E402
from execution.record import ExecutionRecordBuilder  # noqa: E402
from retrieval.models import InvocationContext  # noqa: E402
from retrieval.policy import RetrievalPolicy  # noqa: E402


def _head() -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain an object")
    return value


def _review_pass(review_id: str = "review-result") -> dict[str, object]:
    return {
        "review_id": review_id,
        "verdict": "PASS",
        "confidence": "MEDIUM",
        "evidence_status": "SUFFICIENT",
        "missing_evidence": [],
    }


def _resolved_ref(kind: str, identity: str) -> dict[str, str]:
    commit = _head()
    raw = subprocess.run(
        ["git", "-C", str(ROOT), "show", f"{commit}:{_RECORD_REFERENCE_FIXTURE}"],
        check=True,
        capture_output=True,
    ).stdout
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    return {
        "kind": kind,
        "ref": f"git:{commit}:{_RECORD_REFERENCE_FIXTURE}#{quote(identity, safe='')}",
        "content_hash": digest,
    }


def _accepted_outputs(invocation: dict[str, Any]) -> dict[str, Any]:
    outputs: dict[str, Any] = {
        str(field): "ok" for field in invocation["output_contract"]["required_fields"]
    }
    stage = str(invocation["stage"]["stage_id"])
    if stage == "RULE_RESOLUTION":
        outputs["KNOWN_POLICY_CONFLICTS"] = []
    elif stage == "SPEC_ALIGNMENT":
        outputs.update(Q1_STATUS="NO_GAP", Q2_STATUS="COVERED", Q3_STATUS="CLEAR")
    elif stage == "RUNTIME_AUTHENTICITY":
        outputs["RUNTIME_AUTHENTICITY_STATUS"] = "PASS"
    elif stage == "DETERMINISTIC_VALIDATION":
        outputs.update(
            ORACLE_REWARD=1,
            NOP_REWARD=0,
            F2P_EMPIRICAL_MATRIX=[{"case": "f2p", "pass": True}],
            P2P_EMPIRICAL_MATRIX=[{"case": "p2p", "pass": True}],
        )
    elif stage == "QUALITY_INTERLOCK":
        outputs.update(
            Q4_RESULT=_review_pass("q4-review"),
            Q4_SATISFACTION="DIRECT_PASS",
            Q6_RESULT=_review_pass("q6-review"),
            EVIDENCE_SUFFICIENCY="SUFFICIENT",
        )
    elif stage == "PRE_LLMAJ":
        outputs.update({f"STAGE_{letter}": "PASS" for letter in "ABCDEF"})
    elif stage == "MODEL_DIAGNOSTIC_GPT":
        outputs.update(
            PERSPECTIVE="GPT_PERSPECTIVE",
            EXECUTION="EXECUTED",
            DIAGNOSTIC_SUMMARY="diagnostic",
            PREDICTED_OFFICIAL_SIGNAL="non-authoritative",
        )
    elif stage == "MODEL_DIAGNOSTIC_CLAUDE":
        outputs.update(
            PERSPECTIVE="CLAUDE_PERSPECTIVE",
            EXECUTION="EXECUTED",
            DIAGNOSTIC_SUMMARY="diagnostic",
            PREDICTED_OFFICIAL_SIGNAL="non-authoritative",
        )
    elif stage == "MODEL_DIAGNOSTIC_AGGREGATE":
        outputs.update(
            GPT_PERSPECTIVE_RESULT={"EXECUTION": "EXECUTED"},
            CLAUDE_PERSPECTIVE_RESULT={"EXECUTION": "EXECUTED"},
            ISOLATION_CHECK="PASS",
            COMPARATIVE_DIAGNOSTIC="complete",
        )
    elif stage == "HARBOR_LLMAJ":
        outputs.update(
            HARBOR_RUN_ID="harbor-run-1",
            HARBOR_RESULT="PASS",
            HARBOR_EVIDENCE={"artifact": "harbor://run-1"},
        )
    elif stage == "OFFICIAL_MODEL_TRIALS":
        outputs.update(
            EXTERNAL_RUN_ID="official-batch-validator",
            GPT_5_5_TRIALS=[{"trial": i, "run_id": f"gpt-run-{i}"} for i in range(5)],
            CLAUDE_OPUS_4_8_TRIALS=[{"trial": i, "run_id": f"claude-run-{i}"} for i in range(5)],
            COMBINED_SUCCESS_RATE=0.5,
            PER_TEST_SOLVABILITY={"case-a": 1, "case-b": 3},
        )
    elif stage == "TRIAL_ANALYSIS":
        outputs.update(
            FAILURE_CLASSIFICATION={},
            ZERO_OF_TEN_DISPOSITION="NONE",
            REMEDIATION_OWNER="NONE",
        )
    elif stage == "DIFFICULTY_ASSESSMENT":
        outputs.update(
            EMPIRICAL_TIER="advanced",
            DECLARED_TIER="advanced",
            COMBINED_SUCCESS_RATE=0.5,
            PER_TEST_SOLVABILITY={"case-a": 1, "case-b": 3},
            ZERO_OF_TEN_TESTS=[],
            TRAJECTORY_ANALYSIS_RESULT={"status": "COMPLETE", "record_id": "trajectory-result"},
        )
    elif stage == "FINAL_REVIEW":
        outputs.update(
            FINAL_COMPLIANCE=_review_pass("final-compliance"),
            FINAL_HUMAN_QUALITY=_review_pass("final-human-quality"),
            FINAL_PACKAGE_EVIDENCE={"manifest": "ok"},
        )
    elif stage == "SUBMISSION_READY":
        outputs.update(
            READINESS_STATUS="SUBMISSION_READY",
            GATE_EVIDENCE={"all": "current"},
        )
    return outputs


def _evidence(stage: str, outputs: dict[str, Any]) -> list[dict[str, str]]:
    if stage == "QUALITY_INTERLOCK":
        refs = [_resolved_ref("RESULT", "q4-review"), _resolved_ref("RESULT", "q6-review")]
        if outputs.get("Q4_SATISFACTION") == "ADJUDICATED_CLOSURE_PASS":
            refs.append(_resolved_ref("RESULT", "q4-closure-review"))
        return refs
    if stage == "PRE_LLMAJ":
        return [_resolved_ref("RESULT", f"prellmaj-{i}") for i in range(6)]
    if stage == "MODEL_DIAGNOSTIC_AGGREGATE":
        return [_resolved_ref("RESULT", "q8-gpt"), _resolved_ref("RESULT", "q8-claude")]
    if stage == "HARBOR_LLMAJ":
        return [_resolved_ref("RUN", str(outputs["HARBOR_RUN_ID"]))]
    if stage in {"OFFICIAL_MODEL_TRIALS", "TRIAL_ANALYSIS", "DIFFICULTY_ASSESSMENT"}:
        refs = (
            [_resolved_ref("RUN", f"gpt-run-{i}") for i in range(5)]
            + [_resolved_ref("RUN", f"claude-run-{i}") for i in range(5)]
        )
        if stage == "DIFFICULTY_ASSESSMENT":
            refs.append(_resolved_ref("RESULT", "trajectory-result"))
        return refs
    if stage == "FINAL_REVIEW":
        return [
            _resolved_ref("RESULT", "final-compliance"),
            _resolved_ref("RESULT", "final-human-quality"),
            _resolved_ref("ARTIFACT", "final-package"),
        ]
    if stage == "SUBMISSION_READY":
        return [
            _resolved_ref("RESULT", "final-review"),
            _resolved_ref("ARTIFACT", "submission-package"),
        ]
    return []


def main() -> int:
    errors: list[str] = []
    policy = RetrievalPolicy(ROOT)
    authority = ExecutionAuthority(policy)
    outcomes = _load(T / "agents" / "execution_outcomes.json")
    predicates = _load(T / "agents" / "stage_acceptance_predicates.json")

    if set(outcomes.get("stages", {})) != set(policy.stages):
        errors.append("execution outcomes must cover registered stages exactly")
    for stage_id, stage in policy.stages.items():
        semantics = outcomes.get("stages", {}).get(stage_id, {})
        legal = set(stage.get("output_contract", {}).get("status_values", []))
        partition = (
            set(semantics.get("advance_statuses", []))
            | set(semantics.get("retry_statuses", []))
            | set(semantics.get("block_statuses", []))
            | set(semantics.get("route_statuses", {}))
        )
        if partition != legal:
            errors.append(f"{stage_id}: status partition drift")
        if not set(semantics.get("advance_statuses", [])) <= set(
            semantics.get("full_output_statuses", [])
        ):
            errors.append(f"{stage_id}: advancing statuses must require full outputs")

    required_pass_b = {
        "MODEL_DIAGNOSTIC_GPT",
        "MODEL_DIAGNOSTIC_CLAUDE",
        "MODEL_DIAGNOSTIC_AGGREGATE",
        "HARBOR_LLMAJ",
        "OFFICIAL_MODEL_TRIALS",
        "TRIAL_ANALYSIS",
        "DIFFICULTY_ASSESSMENT",
    }
    if not required_pass_b <= set(predicates.get("stages", {})):
        errors.append("Pass B acceptance predicates are incomplete")

    commit = _head()
    invocation_builder = StageInvocationBuilder(ROOT, policy)
    record_builder = ExecutionRecordBuilder(ROOT, policy)
    record_ids: set[str] = set()
    for stage_id, stage in policy.stages.items():
        advance = outcomes["stages"][stage_id].get("advance_statuses", [])
        if not advance:
            errors.append(f"{stage_id}: no ADVANCE status")
            continue
        role_id = authority.primary_role_for_stage(stage_id)
        inputs = {
            str(field): {"validator": str(field)}
            for field in stage["input_contract"]["required_fields"]
        }
        try:
            invocation = invocation_builder.build(
                InvocationContext(
                    stage_id=stage_id,
                    role_id=role_id,
                    task_id="execution-validator",
                    task_commit=commit,
                    control_plane_commit=commit,
                ),
                inputs,
            )
            outputs = _accepted_outputs(invocation)
            record = record_builder.build(
                invocation,
                {
                    "schema_version": "1.0",
                    "invocation_id": invocation["invocation_id"],
                    "output_task_commit": commit,
                    "status": advance[0],
                    "outputs": outputs,
                    "evidence_refs": _evidence(stage_id, outputs),
                },
            )
        except Exception as exc:
            errors.append(f"{stage_id}: canonical record failed: {exc}")
            continue
        if record.get("disposition") != "ADVANCE":
            errors.append(f"{stage_id}: canonical record did not ADVANCE")
        if record.get("transition", {}).get("target") != stage.get("success_transition"):
            errors.append(f"{stage_id}: canonical transition drift")
        record_ids.add(str(record.get("record_id")))
    if len(record_ids) != len(policy.stages):
        errors.append("per-stage record identities are not unique")

    qi_stage = policy.stages["QUALITY_INTERLOCK"]
    qi_invocation = invocation_builder.build(
        InvocationContext(
            stage_id="QUALITY_INTERLOCK",
            role_id="CI_ORCHESTRATOR",
            task_id="execution-validator",
            task_commit=commit,
            control_plane_commit=commit,
        ),
        {str(field): "ok" for field in qi_stage["input_contract"]["required_fields"]},
    )
    bad_qi = _accepted_outputs(qi_invocation)
    assert isinstance(bad_qi["Q4_RESULT"], dict)
    bad_qi["Q4_RESULT"]["verdict"] = "REVISE"
    try:
        record_builder.build(
            qi_invocation,
            {
                "schema_version": "1.0",
                "invocation_id": qi_invocation["invocation_id"],
                "output_task_commit": commit,
                "status": "QUALITY_INTERLOCK_PASS",
                "outputs": bad_qi,
                "evidence_refs": _evidence("QUALITY_INTERLOCK", bad_qi),
            },
        )
        errors.append("invalid Q4 value incorrectly satisfied QUALITY_INTERLOCK_PASS")
    except ValueError as exc:
        if "acceptance predicate failed" not in str(exc):
            errors.append(f"unexpected aggregate rejection: {exc}")

    closure_qi = _accepted_outputs(qi_invocation)
    assert isinstance(closure_qi["Q4_RESULT"], dict)
    closure_qi["Q4_RESULT"]["verdict"] = "REVISE"
    closure_qi["Q4_SATISFACTION"] = "ADJUDICATED_CLOSURE_PASS"
    closure_qi["Q4_CLOSURE_RESULT"] = {
        "review_id": "q4-closure-review",
        "role": "Q4 Closure Adjudicator",
        "verdict": "PASS",
        "confidence": "HIGH",
        "evidence_status": "SUFFICIENT",
        "missing_evidence": [],
        "role_output": {"CLOSURE_OUTCOME": "PASS"},
    }
    try:
        closure_record = record_builder.build(
            qi_invocation,
            {
                "schema_version": "1.0",
                "invocation_id": qi_invocation["invocation_id"],
                "output_task_commit": commit,
                "status": "QUALITY_INTERLOCK_PASS",
                "outputs": closure_qi,
                "evidence_refs": _evidence("QUALITY_INTERLOCK", closure_qi),
            },
        )
        if closure_record.get("disposition") != "ADVANCE":
            errors.append("coherent adjudicated Q4 closure did not advance")
    except ValueError as exc:
        errors.append(f"coherent adjudicated Q4 closure was rejected: {exc}")

    try:
        record_builder.build(
            qi_invocation,
            {
                "schema_version": "1.0",
                "invocation_id": qi_invocation["invocation_id"],
                "output_task_commit": commit,
                "status": "QUALITY_INTERLOCK_PASS",
                "outputs": closure_qi,
                "evidence_refs": [
                    _resolved_ref("RESULT", "q4-review"),
                    _resolved_ref("RESULT", "q6-review"),
                ],
            },
        )
        errors.append("adjudicated Q4 closure advanced without bound closure-result evidence")
    except ValueError as exc:
        if "Q4_CLOSURE_RESULT evidence ref" not in str(exc):
            errors.append(f"unexpected unbound closure rejection: {exc}")

    diff_stage = policy.stages["DIFFICULTY_ASSESSMENT"]
    diff_invocation = invocation_builder.build(
        InvocationContext(
            stage_id="DIFFICULTY_ASSESSMENT",
            role_id="DIFFICULTY_REVIEWER",
            task_id="execution-validator",
            task_commit=commit,
            control_plane_commit=commit,
        ),
        {str(field): "ok" for field in diff_stage["input_contract"]["required_fields"]},
    )
    for mutation in ("perfect", "zero-test", "tier"):
        outputs = json.loads(json.dumps(_accepted_outputs(diff_invocation)))
        if mutation == "perfect":
            outputs["COMBINED_SUCCESS_RATE"] = 1.0
        elif mutation == "zero-test":
            outputs["PER_TEST_SOLVABILITY"] = {"case-a": 0}
            outputs["ZERO_OF_TEN_TESTS"] = ["case-a"]
        else:
            outputs["DECLARED_TIER"] = "hard"
        try:
            record_builder.build(
                diff_invocation,
                {
                    "schema_version": "1.0",
                    "invocation_id": diff_invocation["invocation_id"],
                    "output_task_commit": commit,
                    "status": "PASS",
                    "outputs": outputs,
                    "evidence_refs": _evidence("DIFFICULTY_ASSESSMENT", outputs),
                },
            )
            errors.append(f"difficulty mutation {mutation} incorrectly advanced")
        except ValueError:
            pass

    if errors:
        print("Terminus execution-record validation FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Terminus execution-record validation PASS")
    print(
        f"execution_record=1.0 outcomes=1.0 predicates=1.0 stages={len(policy.stages)} "
        "result_binding=invocation_exact task_lineage=input_output_descendant "
        "acceptance_predicates=value_enforced q8=dual_isolated harbor=mandatory "
        "difficulty=empirical record_identity=deterministic reasoning=not_persisted"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
