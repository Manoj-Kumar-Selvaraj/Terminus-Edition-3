#!/usr/bin/env python3
"""Deterministic chain validation for post-circuit-breaker Q4 closure evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

NONBLOCKING_DISPOSITIONS = frozenset(
    {"CLOSED_BOUND_FINDING", "REJECTED_SCOPE_REOPEN", "LATENT_AFTER_BOUNDARY"}
)
BLOCKING_DISPOSITIONS = frozenset(
    {
        "SURVIVING_BOUND_BLOCKER",
        "REPAIR_REGRESSION",
        "NEW_EVIDENCE",
        "AUTHORITATIVE_RULE_CONFLICT",
    }
)
ALL_DISPOSITIONS = NONBLOCKING_DISPOSITIONS | BLOCKING_DISPOSITIONS
_FP = re.compile(r"^[0-9a-f]{64}$")


def finding_fingerprint(finding: dict[str, Any]) -> str:
    payload = {
        "version": "q4-finding-v1",
        "criterion": str(finding.get("criterion", "")).strip(),
        "evidence_refs": sorted(str(ref).strip() for ref in finding.get("evidence_refs", [])),
        "why_it_matters": str(finding.get("why_it_matters", "")).strip(),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _safe(root: Path, rel: str, errors: list[str], label: str) -> Path | None:
    candidate = (root / rel).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        errors.append(f"{label}: path escapes repository: {rel}")
        return None
    return candidate


def _load(path: Path, errors: list[str], label: str) -> dict[str, Any] | None:
    if not path.is_file():
        errors.append(f"{label}: missing file {path}")
        return None
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"{label}: invalid JSON ({exc})")
        return None
    if not isinstance(value, dict):
        errors.append(f"{label}: expected JSON object")
        return None
    return value


def validate_frozen_pair(
    root: Path,
    result_rel: str,
    expected_role: str,
    expected_task: str,
    expected_commit: str | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    result_path = _safe(root, result_rel, errors, "frozen result")
    if result_path is None:
        return None, None, errors
    result = _load(result_path, errors, result_rel)
    if result is None:
        return None, None, errors
    if result.get("schema_version") != "3.0":
        errors.append(f"{result_rel}: closure requires frozen schema-v3 review evidence")
    if result.get("role") != expected_role:
        errors.append(f"{result_rel}: role must be {expected_role!r}")
    if result.get("task") != expected_task:
        errors.append(f"{result_rel}: task mismatch")
    if expected_commit and result.get("task_commit") != expected_commit:
        errors.append(f"{result_rel}: task_commit mismatch")
    packet_rel = str(result.get("context_packet", ""))
    packet_path = _safe(root, packet_rel, errors, result_rel)
    packet = _load(packet_path, errors, packet_rel) if packet_path else None
    if packet is None:
        return result, None, errors
    for key in (
        "review_id",
        "task",
        "task_commit",
        "role",
        "protocol_policy_version",
        "prompt_policy_version",
        "role_policy_version",
        "control_plane_commit",
        "role_contract_hash",
    ):
        if result.get(key) != packet.get(key):
            errors.append(f"{result_rel}: {key} does not match frozen packet")
    if packet.get("review_output_path") != result_rel:
        errors.append(f"{packet_rel}: review_output_path does not bind {result_rel}")
    return result, packet, errors


def _single_token(packet: dict[str, Any], prefix: str, errors: list[str]) -> str:
    matches = [
        str(item)[len(prefix) :]
        for item in packet.get("evidence_allowed", [])
        if str(item).startswith(prefix)
    ]
    if len(matches) != 1:
        errors.append(f"closure packet requires exactly one {prefix.rstrip(':')} binding")
        return ""
    return matches[0]


def _q4_exhaustive(q4: dict[str, Any]) -> bool:
    ex = q4.get("role_output", {}).get("EXHAUSTIVENESS", {})
    expected = {
        "REQUIREMENTS_ENUMERATED": "COMPLETE",
        "VERIFIER_BEHAVIORS_ENUMERATED": "COMPLETE",
        "FORWARD_MATRIX_COMPLETE": "YES",
        "REVERSE_MATRIX_COMPLETE": "YES",
        "DELEGATED_CONTRACTS_COMPLETE": "YES",
        "P2P_BOUNDARIES_COMPLETE": "YES",
        "F2P_BOUNDARIES_COMPLETE": "YES",
        "OUTPUT_INTERFACES_COMPLETE": "YES",
        "SECOND_PASS_OMISSION_SWEEP": "PASS",
    }
    return all(ex.get(key) == value for key, value in expected.items()) and not ex.get(
        "UNINSPECTED_SCOPE"
    )


def validate_ready_closure(
    root: Path, closure_result_rel: str
) -> tuple[list[str], dict[str, str]]:
    root = root.resolve()
    errors: list[str] = []
    metadata: dict[str, str] = {}
    closure_path = _safe(root, closure_result_rel, errors, "closure result")
    if closure_path is None:
        return errors, metadata
    closure = _load(closure_path, errors, closure_result_rel)
    if closure is None:
        return errors, metadata
    if closure.get("role") != "Q4 Closure Adjudicator":
        errors.append("closure result role must be 'Q4 Closure Adjudicator'")
    if closure.get("verdict") != "PASS":
        errors.append("ready Q4 closure requires verdict PASS")
    if closure.get("confidence") not in {"HIGH", "MEDIUM"}:
        errors.append("ready Q4 closure requires HIGH or MEDIUM confidence")
    if closure.get("evidence_status") != "SUFFICIENT":
        errors.append("ready Q4 closure requires SUFFICIENT evidence")
    if closure.get("missing_evidence"):
        errors.append("ready Q4 closure cannot have missing_evidence")

    packet_rel = str(closure.get("context_packet", ""))
    packet_path = _safe(root, packet_rel, errors, "closure packet")
    packet = _load(packet_path, errors, packet_rel) if packet_path else None
    if packet is None:
        return errors, metadata
    if packet.get("state") != "Q4_CLOSURE_ADJUDICATION":
        errors.append("closure packet state must be Q4_CLOSURE_ADJUDICATION")
    if packet.get("role") != "Q4 Closure Adjudicator":
        errors.append("closure packet role mismatch")
    if packet.get("prior_verdicts_visible") is not True:
        errors.append("closure packet must explicitly expose its frozen prior verdicts")
    if packet.get("review_output_path") != closure_result_rel:
        errors.append("closure packet review_output_path mismatch")
    for key in (
        "review_id",
        "task",
        "task_commit",
        "role",
        "protocol_policy_version",
        "prompt_policy_version",
        "role_policy_version",
        "control_plane_commit",
        "role_contract_hash",
    ):
        if closure.get(key) != packet.get(key):
            errors.append(f"closure result {key} does not match packet")

    task = str(closure.get("task", ""))
    final_commit = str(closure.get("task_commit", ""))
    boundary_rel = _single_token(packet, "boundary_adjudication:", errors)
    final_q4_rel = _single_token(packet, "final_q4_result:", errors)
    diff_token = _single_token(packet, "repair_diff:", errors)
    repair_base = ""
    if diff_token:
        match = re.fullmatch(r"([0-9a-f]{40})\.\.([0-9a-f]{40}):(.+)", diff_token)
        if not match:
            errors.append("closure repair_diff binding is malformed")
        else:
            repair_base, diff_final, diff_task = match.groups()
            if diff_final != final_commit:
                errors.append("repair_diff final commit does not match closure task_commit")
            if diff_task != task:
                errors.append("repair_diff task does not match closure task")

    boundary = None
    q4 = None
    if boundary_rel:
        boundary, _, pair_errors = validate_frozen_pair(
            root, boundary_rel, "Adjudicator", task, repair_base or None
        )
        errors.extend(pair_errors)
    if final_q4_rel:
        q4, _, pair_errors = validate_frozen_pair(
            root, final_q4_rel, "Spec-Test Contract Reviewer", task, final_commit
        )
        errors.extend(pair_errors)
    if q4 is None or boundary is None:
        return errors, metadata

    metadata.update(
        final_q4_result=final_q4_rel,
        boundary_adjudication=boundary_rel,
        repair_base_task_commit=repair_base,
        final_task_commit=final_commit,
    )
    if q4.get("verdict") != "REVISE":
        errors.append("adjudicated closure path requires a final frozen Q4 REVISE")
    if q4.get("confidence") == "LOW" or q4.get("evidence_status") != "SUFFICIENT":
        errors.append("final Q4 must have non-LOW confidence and SUFFICIENT evidence")
    if not _q4_exhaustive(q4):
        errors.append("final Q4 must be exhaustive before closure adjudication")
    if boundary.get("confidence") == "LOW" or boundary.get("evidence_status") != "SUFFICIENT":
        errors.append("boundary Adjudicator evidence is not sufficient for closure")

    expected_fps = {
        str(finding.get("id", "")): finding_fingerprint(finding)
        for finding in q4.get("findings", [])
        if str(finding.get("id", ""))
    }
    packet_fps: dict[str, str] = {}
    for item in packet.get("evidence_allowed", []):
        text = str(item)
        if not text.startswith("q4_finding:"):
            continue
        parts = text.split(":", 2)
        if len(parts) != 3 or not parts[1] or not _FP.fullmatch(parts[2]):
            errors.append(f"malformed q4_finding packet binding: {text}")
            continue
        if parts[1] in packet_fps:
            errors.append(f"duplicate q4_finding packet binding: {parts[1]}")
        packet_fps[parts[1]] = parts[2]
    if packet_fps != expected_fps:
        errors.append("closure packet finding fingerprints do not exactly bind final Q4")

    role_output = closure.get("role_output", {})
    required = {
        "DECISION",
        "CONTROLLING_RULE_OR_EVIDENCE",
        "SCOPE_RECONCILIATION",
        "REASON",
        "REQUIRED_ACTION",
        "RECHECK",
        "CLOSURE_OUTCOME",
        "BOUNDARY_ADJUDICATION",
        "FINAL_Q4_RESULT",
        "REPAIR_BASE_TASK_COMMIT",
        "FINAL_TASK_COMMIT",
        "FINDING_DISPOSITIONS",
    }
    missing = sorted(required - set(role_output)) if isinstance(role_output, dict) else sorted(required)
    if missing:
        errors.append("closure role_output missing: " + ", ".join(missing))
        return errors, metadata
    if role_output.get("CLOSURE_OUTCOME") != "PASS":
        errors.append("ready closure requires role_output.CLOSURE_OUTCOME=PASS")
    if role_output.get("BOUNDARY_ADJUDICATION") != boundary_rel:
        errors.append("closure role_output boundary path mismatch")
    if role_output.get("FINAL_Q4_RESULT") != final_q4_rel:
        errors.append("closure role_output final Q4 path mismatch")
    if role_output.get("REPAIR_BASE_TASK_COMMIT") != repair_base:
        errors.append("closure role_output repair-base commit mismatch")
    if role_output.get("FINAL_TASK_COMMIT") != final_commit:
        errors.append("closure role_output final task commit mismatch")

    dispositions = role_output.get("FINDING_DISPOSITIONS")
    if not isinstance(dispositions, list):
        errors.append("closure FINDING_DISPOSITIONS must be an array")
        return errors, metadata
    seen: dict[str, str] = {}
    required_item = {
        "finding_id",
        "semantic_fingerprint",
        "disposition",
        "controlling_boundary_ref",
        "reason",
    }
    for index, item in enumerate(dispositions):
        if not isinstance(item, dict):
            errors.append(f"closure disposition[{index}] must be an object")
            continue
        if set(item) != required_item:
            errors.append(
                f"closure disposition[{index}] must contain exactly {sorted(required_item)}"
            )
            continue
        finding_id = str(item["finding_id"])
        fingerprint = str(item["semantic_fingerprint"])
        disposition = str(item["disposition"])
        if finding_id in seen:
            errors.append(f"duplicate closure disposition for {finding_id}")
        seen[finding_id] = disposition
        if expected_fps.get(finding_id) != fingerprint:
            errors.append(f"closure fingerprint mismatch for {finding_id}")
        if disposition not in ALL_DISPOSITIONS:
            errors.append(f"invalid closure disposition for {finding_id}: {disposition}")
        if not str(item["controlling_boundary_ref"]).strip():
            errors.append(f"closure disposition {finding_id} lacks controlling_boundary_ref")
        if not str(item["reason"]).strip():
            errors.append(f"closure disposition {finding_id} lacks reason")
    if set(seen) != set(expected_fps):
        errors.append("closure must reconcile every final-Q4 finding exactly once")
    blocking = sorted(fid for fid, disposition in seen.items() if disposition in BLOCKING_DISPOSITIONS)
    if blocking:
        errors.append("closure PASS contains blocking dispositions: " + ", ".join(blocking))
    return errors, metadata


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", nargs="?", help="repository-relative Q4 Closure Adjudicator result")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--fingerprints", help="print finding fingerprints for one final Q4 result")
    args = parser.parse_args(argv)
    if args.fingerprints:
        errors: list[str] = []
        path = _safe(args.root.resolve(), args.fingerprints, errors, "Q4 result")
        data = _load(path, errors, args.fingerprints) if path else None
        if errors or data is None:
            for error in errors:
                print(f"error: {error}")
            return 1
        for finding in data.get("findings", []):
            print(f"{finding.get('id')} {finding_fingerprint(finding)}")
        return 0
    if not args.result:
        parser.error("result is required unless --fingerprints is used")
    errors, metadata = validate_ready_closure(args.root, args.result)
    if errors:
        for error in errors:
            print(f"error: {error}")
        print(f"Q4 adjudicated closure validation FAILED ({len(errors)} error(s))")
        return 1
    print("Q4 adjudicated closure validation PASS")
    for key, value in metadata.items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
