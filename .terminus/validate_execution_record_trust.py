#!/usr/bin/env python3
"""Validate canonical invocation and evidence-backed execution-record trust boundaries."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / ".terminus"
sys.path.insert(0, str(T))

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


def _eref(kind: str, ref: str) -> dict[str, str]:
    return {
        "kind": kind,
        "ref": ref,
        "content_hash": "sha256:" + hashlib.sha256(ref.encode()).hexdigest(),
    }


def _review(review_id: str) -> dict[str, object]:
    return {
        "review_id": review_id,
        "verdict": "PASS",
        "confidence": "MEDIUM",
        "evidence_status": "SUFFICIENT",
        "missing_evidence": [],
    }


def _outputs(invocation: dict[str, Any]) -> dict[str, Any]:
    stage = str(invocation["stage"]["stage_id"])
    values = {
        str(field): "ok" for field in invocation["output_contract"]["required_fields"]
    }
    if stage == "RULE_RESOLUTION":
        values["KNOWN_POLICY_CONFLICTS"] = []
    elif stage == "SPEC_ALIGNMENT":
        values.update(Q1_STATUS="NO_GAP", Q2_STATUS="COVERED", Q3_STATUS="CLEAR")
    elif stage == "RUNTIME_AUTHENTICITY":
        values["RUNTIME_AUTHENTICITY_STATUS"] = "PASS"
    elif stage == "DETERMINISTIC_VALIDATION":
        values.update(
            ORACLE_REWARD=1,
            NOP_REWARD=0,
            F2P_EMPIRICAL_MATRIX=[{"case": "f2p", "pass": True}],
            P2P_EMPIRICAL_MATRIX=[{"case": "p2p", "pass": True}],
        )
    elif stage == "QUALITY_INTERLOCK":
        values.update(
            Q4_RESULT=_review("q4-review"),
            Q6_RESULT=_review("q6-review"),
            EVIDENCE_SUFFICIENCY="SUFFICIENT",
        )
    elif stage == "PRE_LLMAJ":
        values.update({f"STAGE_{letter}": "PASS" for letter in "ABCDEF"})
    elif stage == "MODEL_DIAGNOSTIC_GPT":
        values.update(
            PERSPECTIVE="GPT_PERSPECTIVE",
            EXECUTION="EXECUTED",
            DIAGNOSTIC_SUMMARY="diagnostic",
            PREDICTED_OFFICIAL_SIGNAL="non-authoritative",
        )
    elif stage == "MODEL_DIAGNOSTIC_CLAUDE":
        values.update(
            PERSPECTIVE="CLAUDE_PERSPECTIVE",
            EXECUTION="EXECUTED",
            DIAGNOSTIC_SUMMARY="diagnostic",
            PREDICTED_OFFICIAL_SIGNAL="non-authoritative",
        )
    elif stage == "MODEL_DIAGNOSTIC_AGGREGATE":
        values.update(
            GPT_PERSPECTIVE_RESULT={"EXECUTION": "EXECUTED"},
            CLAUDE_PERSPECTIVE_RESULT={"EXECUTION": "EXECUTED"},
            ISOLATION_CHECK="PASS",
            COMPARATIVE_DIAGNOSTIC="complete",
        )
    elif stage == "HARBOR_LLMAJ":
        values.update(
            HARBOR_RUN_ID="harbor-run-1",
            HARBOR_RESULT="PASS",
            HARBOR_EVIDENCE={"artifact": "harbor-run-1"},
        )
    elif stage == "OFFICIAL_MODEL_TRIALS":
        values.update(
            GPT_5_5_TRIALS=[
                {"trial": index, "run_id": f"gpt-run-{index}"} for index in range(5)
            ],
            CLAUDE_OPUS_4_8_TRIALS=[
                {"trial": index, "run_id": f"claude-run-{index}"}
                for index in range(5)
            ],
            COMBINED_SUCCESS_RATE=0.5,
            PER_TEST_SOLVABILITY={"case-a": 1, "case-b": 2},
        )
    elif stage == "TRIAL_ANALYSIS":
        values.update(
            FAILURE_CLASSIFICATION={},
            ZERO_OF_TEN_DISPOSITION="NONE",
            REMEDIATION_OWNER="NONE",
        )
    elif stage == "DIFFICULTY_ASSESSMENT":
        values.update(
            EMPIRICAL_TIER="advanced",
            DECLARED_TIER="advanced",
            COMBINED_SUCCESS_RATE=0.5,
            PER_TEST_SOLVABILITY={"case-a": 1, "case-b": 2},
            ZERO_OF_TEN_TESTS=[],
            TRAJECTORY_ANALYSIS_RESULT={
                "status": "COMPLETE",
                "record_id": "trajectory-result",
            },
        )
    elif stage == "FINAL_REVIEW":
        values.update(
            FINAL_COMPLIANCE=_review("final-compliance"),
            FINAL_HUMAN_QUALITY=_review("final-human-quality"),
            FINAL_PACKAGE_EVIDENCE={"manifest": "ok"},
        )
    elif stage == "SUBMISSION_READY":
        values.update(
            READINESS_STATUS="SUBMISSION_READY",
            GATE_EVIDENCE={"all": "current"},
        )
    return values


def _evidence(stage: str, outputs: dict[str, Any]) -> list[dict[str, str]]:
    if stage == "QUALITY_INTERLOCK":
        return [_eref("RESULT", "q4-review"), _eref("RESULT", "q6-review")]
    if stage == "PRE_LLMAJ":
        return [_eref("RESULT", f"prellmaj-{index}") for index in range(6)]
    if stage == "MODEL_DIAGNOSTIC_AGGREGATE":
        return [_eref("RESULT", "q8-gpt"), _eref("RESULT", "q8-claude")]
    if stage == "HARBOR_LLMAJ":
        return [_eref("RUN", str(outputs["HARBOR_RUN_ID"]))]
    if stage in {"OFFICIAL_MODEL_TRIALS", "TRIAL_ANALYSIS", "DIFFICULTY_ASSESSMENT"}:
        refs = [
            _eref("RUN", f"gpt-run-{index}") for index in range(5)
        ] + [_eref("RUN", f"claude-run-{index}") for index in range(5)]
        if stage == "DIFFICULTY_ASSESSMENT":
            refs.append(_eref("RESULT", "trajectory-result"))
        return refs
    if stage == "FINAL_REVIEW":
        return [
            _eref("RESULT", "final-compliance"),
            _eref("RESULT", "final-human-quality"),
            _eref("ARTIFACT", "final-package"),
        ]
    if stage == "SUBMISSION_READY":
        return [_eref("RESULT", "final-review"), _eref("ARTIFACT", "submission-package")]
    return []


def _result(
    invocation: dict[str, Any],
    status: str,
    outputs: dict[str, Any],
    commit: str,
    *,
    evidence: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    stage = str(invocation["stage"]["stage_id"])
    return {
        "schema_version": "1.0",
        "invocation_id": invocation["invocation_id"],
        "output_task_commit": commit,
        "status": status,
        "outputs": outputs,
        "evidence_refs": _evidence(stage, outputs) if evidence is None else evidence,
    }


def _rehash(invocation: dict[str, Any]) -> None:
    identity = dict(invocation)
    identity.pop("invocation_id", None)
    invocation["invocation_id"] = StageInvocationBuilder._invocation_id(identity)


def main() -> int:
    errors: list[str] = []
    policy = RetrievalPolicy(ROOT)
    authority = ExecutionAuthority(policy)
    outcomes = _load(T / "agents" / "execution_outcomes.json")
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
            outputs = _outputs(invocation)
            record = record_builder.build(
                invocation,
                _result(invocation, advance[0], outputs, commit),
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

    harbor = policy.stages["HARBOR_LLMAJ"]
    harbor_invocation = invocation_builder.build(
        InvocationContext(
            stage_id="HARBOR_LLMAJ",
            role_id="HARBOR_LLMAJ_GATE",
            task_id="execution-validator",
            task_commit=commit,
            control_plane_commit=commit,
        ),
        {str(field): "ok" for field in harbor["input_contract"]["required_fields"]},
    )
    harbor_outputs = _outputs(harbor_invocation)
    try:
        record_builder.build(
            harbor_invocation,
            _result(harbor_invocation, "PASS", harbor_outputs, commit, evidence=[]),
        )
        errors.append("Harbor PASS accepted empty evidence_refs")
    except ValueError as exc:
        if "requires immutable hashed evidence_refs" not in str(exc):
            errors.append(f"unexpected Harbor rejection: {exc}")

    q8 = policy.stages["MODEL_DIAGNOSTIC_GPT"]
    q8_invocation = invocation_builder.build(
        InvocationContext(
            stage_id="MODEL_DIAGNOSTIC_GPT",
            role_id="Q8_MODEL_PERSPECTIVE_DIFFICULTY_SIMULATOR",
            task_id="execution-validator",
            task_commit=commit,
            control_plane_commit=commit,
        ),
        {str(field): "ok" for field in q8["input_contract"]["required_fields"]},
    )
    forged = json.loads(json.dumps(q8_invocation))
    forged["evidence"]["authorized_evidence_classes"].append("SOLUTION_ORACLE")
    forged["evidence"]["excluded_evidence_classes"].remove("SOLUTION_ORACLE")
    _rehash(forged)
    try:
        record_builder.build(
            forged,
            _result(forged, "EXECUTED", _outputs(forged), commit),
        )
        errors.append("rehashed Q8 invocation widened evidence authority")
    except ValueError as exc:
        if "authorized evidence classes" not in str(exc):
            errors.append(f"unexpected Q8 rejection: {exc}")

    if errors:
        print("Terminus execution-record validation FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Terminus execution-record validation PASS")
    print(
        f"execution_record=1.0 stages={len(policy.stages)} "
        "invocation_policy=revalidated evidence_binding=immutable "
        "external_validation=canonical q8=adversarial_checked"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
