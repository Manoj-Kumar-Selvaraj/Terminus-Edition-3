"""Regression tests for adjudicated post-circuit-breaker Q4 closure."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
T = ROOT / ".terminus"
sys.path.insert(0, str(T))
import q4_closure


def _write(root: Path, rel: str, value: dict) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _pair(root: Path, rel: str, *, role: str, task: str, commit: str, verdict: str, findings=None, role_output=None):
    packet_rel = rel.replace(".json", ".packet.json")
    review_id = Path(rel).stem
    packet = {
        "schema_version": "3.0",
        "review_id": review_id,
        "protocol_policy_version": "2.2",
        "prompt_policy_version": "2.2",
        "role_policy_version": "1.0",
        "control_plane_commit": "c" * 40,
        "role_contract_hash": "d" * 64,
        "task": task,
        "task_commit": commit,
        "state": "FROZEN_CANDIDATE",
        "role": role,
        "question": "q",
        "authoritative_rules": ["rule"],
        "evidence_allowed": [],
        "evidence_excluded": [],
        "prior_verdicts_visible": False,
        "isolation_mode": "PROCEDURAL",
        "change_since_last_review": "",
        "output_schema": ".terminus/agents/schemas/review_result.schema.json",
        "review_output_path": rel,
    }
    result = {
        "schema_version": "3.0",
        "role": role,
        "review_id": review_id,
        "task": task,
        "task_commit": commit,
        "control_plane_commit": packet["control_plane_commit"],
        "protocol_policy_version": packet["protocol_policy_version"],
        "prompt_policy_version": packet["prompt_policy_version"],
        "role_policy_version": packet["role_policy_version"],
        "role_contract_hash": packet["role_contract_hash"],
        "context_packet": packet_rel,
        "verdict": verdict,
        "confidence": "HIGH",
        "evidence_status": "SUFFICIENT",
        "summary": "s",
        "evidence": [],
        "findings": findings or [],
        "missing_evidence": [],
        "change_scope": [],
        "do_not_change": [],
        "next_gate": "n",
        "role_output": role_output or {},
    }
    _write(root, packet_rel, packet)
    _write(root, rel, result)
    return packet, result


def _fixture(tmp_path: Path):
    root = tmp_path
    task = "t"
    base = "a" * 40
    final = "b" * 40
    boundary_rel = ".terminus/reviews/t/aaaaaaaa/t-aaaaaaaa-adjudication-boundary.json"
    q4_rel = ".terminus/reviews/t/bbbbbbbb/t-bbbbbbbb-spec-test-contract-final.json"
    closure_rel = ".terminus/reviews/t/bbbbbbbb/t-bbbbbbbb-q4-closure.json"
    _pair(
        root,
        boundary_rel,
        role="Adjudicator",
        task=task,
        commit=base,
        verdict="REQUEST_CHANGES",
        role_output={
            "DECISION": "BOTH_PARTLY",
            "CONTROLLING_RULE_OR_EVIDENCE": "r",
            "SCOPE_RECONCILIATION": "s",
            "REASON": "r",
            "REQUIRED_ACTION": "a",
            "RECHECK": "r",
        },
    )
    finding = {
        "id": "Q4-001",
        "severity": "HIGH",
        "status": "OBSERVED",
        "criterion": "contract",
        "evidence_refs": ["t/tests/x.py"],
        "why_it_matters": "material",
        "minimal_remediation": "m",
        "regression_risk": "r",
    }
    q4_output = {
        "BLOCKING_FINDING_IDS": ["Q4-001"],
        "ADVISORY_FINDING_IDS": [],
        "EXHAUSTIVENESS": {
            "REQUIREMENTS_ENUMERATED": "COMPLETE",
            "VERIFIER_BEHAVIORS_ENUMERATED": "COMPLETE",
            "FORWARD_MATRIX_COMPLETE": "YES",
            "REVERSE_MATRIX_COMPLETE": "YES",
            "DELEGATED_CONTRACTS_COMPLETE": "YES",
            "P2P_BOUNDARIES_COMPLETE": "YES",
            "F2P_BOUNDARIES_COMPLETE": "YES",
            "OUTPUT_INTERFACES_COMPLETE": "YES",
            "SECOND_PASS_OMISSION_SWEEP": "PASS",
            "UNINSPECTED_SCOPE": [],
        },
    }
    _pair(
        root,
        q4_rel,
        role="Spec-Test Contract Reviewer",
        task=task,
        commit=final,
        verdict="REVISE",
        findings=[finding],
        role_output=q4_output,
    )
    fp = q4_closure.finding_fingerprint(finding)
    closure_packet, closure = _pair(
        root,
        closure_rel,
        role="Q4 Closure Adjudicator",
        task=task,
        commit=final,
        verdict="PASS",
        role_output={
            "DECISION": "BOTH_PARTLY",
            "CONTROLLING_RULE_OR_EVIDENCE": "r",
            "SCOPE_RECONCILIATION": "s",
            "REASON": "r",
            "REQUIRED_ACTION": "advance",
            "RECHECK": "none",
            "CLOSURE_OUTCOME": "PASS",
            "BOUNDARY_ADJUDICATION": boundary_rel,
            "FINAL_Q4_RESULT": q4_rel,
            "REPAIR_BASE_TASK_COMMIT": base,
            "FINAL_TASK_COMMIT": final,
            "FINDING_DISPOSITIONS": [
                {
                    "finding_id": "Q4-001",
                    "semantic_fingerprint": fp,
                    "disposition": "REJECTED_SCOPE_REOPEN",
                    "controlling_boundary_ref": "ADJ-Q4-001",
                    "reason": "boundary rejected scope",
                }
            ],
        },
    )
    closure_packet["state"] = "Q4_CLOSURE_ADJUDICATION"
    closure_packet["prior_verdicts_visible"] = True
    closure_packet["evidence_allowed"] = [
        f"boundary_adjudication:{boundary_rel}",
        f"final_q4_result:{q4_rel}",
        f"repair_diff:{base}..{final}:{task}",
        f"q4_finding:Q4-001:{fp}",
    ]
    closure_packet["closure_policy_version"] = "1.0"
    closure_packet["boundary_adjudication"] = boundary_rel
    closure_packet["final_q4_result"] = q4_rel
    closure_packet["repair_base_task_commit"] = base
    closure_packet["final_task_commit"] = final
    closure_packet["finding_fingerprints"] = {"Q4-001": fp}
    _write(root, closure["context_packet"], closure_packet)
    return root, closure_rel


def test_ready_closure_requires_exact_finding_reconciliation(tmp_path: Path) -> None:
    root, rel = _fixture(tmp_path)
    errors, metadata = q4_closure.validate_ready_closure(root, rel)
    assert errors == []
    assert metadata["final_q4_result"].endswith("spec-test-contract-final.json")


def test_ready_closure_rejects_blocking_disposition(tmp_path: Path) -> None:
    root, rel = _fixture(tmp_path)
    path = root / rel
    data = json.loads(path.read_text())
    data["role_output"]["FINDING_DISPOSITIONS"][0]["disposition"] = "SURVIVING_BOUND_BLOCKER"
    path.write_text(json.dumps(data))
    errors, _ = q4_closure.validate_ready_closure(root, rel)
    assert any("blocking dispositions" in error for error in errors)


def test_ready_closure_rejects_fingerprint_drift(tmp_path: Path) -> None:
    root, rel = _fixture(tmp_path)
    path = root / rel
    data = json.loads(path.read_text())
    data["role_output"]["FINDING_DISPOSITIONS"][0]["semantic_fingerprint"] = "0" * 64
    path.write_text(json.dumps(data))
    errors, _ = q4_closure.validate_ready_closure(root, rel)
    assert any("fingerprint mismatch" in error for error in errors)


def test_stage_acceptance_distinguishes_direct_and_closure_modes() -> None:
    from execution.acceptance import StageAcceptancePredicates

    direct = {
        "Q4_SATISFACTION": "DIRECT_PASS",
        "Q4_RESULT": {"verdict": "PASS", "confidence": "HIGH", "evidence_status": "SUFFICIENT", "missing_evidence": []},
    }
    assert StageAcceptancePredicates._q4_satisfied(direct)
    direct["Q4_RESULT"]["verdict"] = "REVISE"
    assert not StageAcceptancePredicates._q4_satisfied(direct)
    closure = {
        "Q4_SATISFACTION": "ADJUDICATED_CLOSURE_PASS",
        "Q4_RESULT": {"verdict": "REVISE", "confidence": "HIGH", "evidence_status": "SUFFICIENT", "missing_evidence": []},
        "Q4_CLOSURE_RESULT": {
            "role": "Q4 Closure Adjudicator",
            "verdict": "PASS",
            "confidence": "MEDIUM",
            "evidence_status": "SUFFICIENT",
            "missing_evidence": [],
            "role_output": {"CLOSURE_OUTCOME": "PASS"},
        },
    }
    assert StageAcceptancePredicates._q4_satisfied(closure)
    closure["Q4_CLOSURE_RESULT"]["role_output"]["CLOSURE_OUTCOME"] = "BLOCKED"
    assert not StageAcceptancePredicates._q4_satisfied(closure)


def test_ready_closure_rejects_top_level_chain_drift(tmp_path: Path) -> None:
    root, rel = _fixture(tmp_path)
    result = json.loads((root / rel).read_text())
    packet_path = root / result["context_packet"]
    packet = json.loads(packet_path.read_text())
    packet["final_task_commit"] = "0" * 40
    packet_path.write_text(json.dumps(packet))
    errors, _ = q4_closure.validate_ready_closure(root, rel)
    assert any("top-level final-task binding mismatch" in error for error in errors)


def test_ready_closure_rejects_top_level_fingerprint_drift(tmp_path: Path) -> None:
    root, rel = _fixture(tmp_path)
    result = json.loads((root / rel).read_text())
    packet_path = root / result["context_packet"]
    packet = json.loads(packet_path.read_text())
    packet["finding_fingerprints"]["Q4-001"] = "0" * 64
    packet_path.write_text(json.dumps(packet))
    errors, _ = q4_closure.validate_ready_closure(root, rel)
    assert any("top-level finding fingerprints" in error for error in errors)
