from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".terminus"))

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


def _invocation(stage_id: str) -> dict[str, object]:
    policy = RetrievalPolicy(ROOT)
    role_id = ExecutionAuthority(policy).primary_role_for_stage(stage_id)
    stage = policy.stages[stage_id]
    inputs = {
        str(field): {"ref": f"test:{field}"}
        for field in stage["input_contract"]["required_fields"]
    }
    return StageInvocationBuilder(ROOT, policy).build(
        InvocationContext(
            stage_id=stage_id,
            role_id=role_id,
            control_plane_commit=_head(),
        ),
        inputs,
    )


def _full_outputs(invocation: dict[str, object]) -> dict[str, object]:
    contract = invocation["output_contract"]
    assert isinstance(contract, dict)
    return {
        str(field): {"value": str(field)}
        for field in contract["required_fields"]
    }


def _result(
    invocation: dict[str, object],
    status: str,
    *,
    outputs: dict[str, object] | None = None,
    route_key: str | None = None,
    blocking_reason: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema_version": "1.0",
        "invocation_id": invocation["invocation_id"],
        "status": status,
        "outputs": outputs if outputs is not None else {},
        "evidence_refs": [],
    }
    if route_key is not None:
        payload["route_key"] = route_key
    if blocking_reason is not None:
        payload["blocking_reason"] = blocking_reason
    return payload


def test_deterministic_pass_targets_frozen_state_with_validation_required() -> None:
    invocation = _invocation("DETERMINISTIC_VALIDATION")
    record = ExecutionRecordBuilder(ROOT).build(
        invocation,
        _result(invocation, "PASS", outputs=_full_outputs(invocation)),
    )
    assert record["disposition"] == "ADVANCE"
    assert record["transition"] == {
        "action": "ADVANCE",
        "target": "FROZEN_CANDIDATE",
        "target_kind": "STATE",
        "requires_state_validation": True,
    }
    assert record["validation"]["required_outputs_satisfied"] is True


def test_format_fixed_retries_until_format_pass() -> None:
    invocation = _invocation("FORMAT_GATE")
    record = ExecutionRecordBuilder(ROOT).build(
        invocation,
        _result(invocation, "FIXED", outputs=_full_outputs(invocation)),
    )
    assert record["disposition"] == "RETRY"
    assert record["transition"]["target"] == "FORMAT_GATE"
    assert record["transition"]["target_kind"] == "STAGE"


def test_model_diagnostic_unavailable_advances_without_fabricated_official_evidence() -> None:
    invocation = _invocation("MODEL_DIAGNOSTIC")
    record = ExecutionRecordBuilder(ROOT).build(
        invocation,
        _result(
            invocation,
            "SIMULATION_NOT_EXECUTED",
            outputs=_full_outputs(invocation),
        ),
    )
    assert record["disposition"] == "ADVANCE"
    assert record["transition"]["target"] == "OFFICIAL_MODEL_TRIALS"


def test_unambiguous_route_uses_declared_default_key() -> None:
    invocation = _invocation("COMPLEXITY_GATE")
    record = ExecutionRecordBuilder(ROOT).build(
        invocation,
        _result(invocation, "REVISE", outputs=_full_outputs(invocation)),
    )
    assert record["disposition"] == "ROUTE"
    assert record["route_key"] == "REVISE"
    assert record["transition"]["route_instruction"] == "smallest responsible producer"


def test_ambiguous_route_requires_explicit_failure_class() -> None:
    invocation = _invocation("INSTRUCTION_DRAFT")
    builder = ExecutionRecordBuilder(ROOT)
    with pytest.raises(ValueError, match="requires an explicit route_key"):
        builder.build(
            invocation,
            _result(invocation, "REWRITE_REQUIRED", outputs=_full_outputs(invocation)),
        )
    record = builder.build(
        invocation,
        _result(
            invocation,
            "REWRITE_REQUIRED",
            outputs=_full_outputs(invocation),
            route_key="MISSING_REQUIREMENT",
        ),
    )
    assert record["transition"]["action"] == "ROUTE"
    assert record["transition"]["route_key"] == "MISSING_REQUIREMENT"


def test_block_requires_reason_and_never_advances() -> None:
    invocation = _invocation("RULE_RESOLUTION")
    builder = ExecutionRecordBuilder(ROOT)
    with pytest.raises(ValueError, match="requires blocking_reason"):
        builder.build(invocation, _result(invocation, "BLOCKED"))
    record = builder.build(
        invocation,
        _result(invocation, "BLOCKED", blocking_reason="rule source unavailable"),
    )
    assert record["disposition"] == "BLOCK"
    assert record["transition"]["target"] is None
    assert record["transition"]["target_kind"] == "NONE"


def test_illegal_status_and_undeclared_outputs_fail_closed() -> None:
    invocation = _invocation("RULE_RESOLUTION")
    builder = ExecutionRecordBuilder(ROOT)
    with pytest.raises(ValueError, match="exactly one execution disposition|illegal stage status"):
        builder.build(
            invocation,
            _result(invocation, "TOTALLY_GREEN", outputs=_full_outputs(invocation)),
        )
    bad = _full_outputs(invocation)
    bad["PRIVATE_SECRET"] = "no"
    with pytest.raises(ValueError, match="undeclared output fields"):
        builder.build(invocation, _result(invocation, "RULES_RESOLVED", outputs=bad))


def test_full_output_status_cannot_omit_required_field() -> None:
    invocation = _invocation("RULE_RESOLUTION")
    outputs = _full_outputs(invocation)
    outputs.pop(next(iter(outputs)))
    with pytest.raises(ValueError, match="missing required stage outputs"):
        ExecutionRecordBuilder(ROOT).build(
            invocation,
            _result(invocation, "RULES_RESOLVED", outputs=outputs),
        )


def test_result_must_bind_exact_invocation_id() -> None:
    invocation = _invocation("RULE_RESOLUTION")
    result = _result(invocation, "RULES_RESOLVED", outputs=_full_outputs(invocation))
    result["invocation_id"] = "inv_" + ("0" * 64)
    with pytest.raises(ValueError, match="does not match invocation"):
        ExecutionRecordBuilder(ROOT).build(invocation, result)


def test_self_consistent_but_forged_routing_is_rejected() -> None:
    invocation = _invocation("RULE_RESOLUTION")
    forged = json.loads(json.dumps(invocation))
    forged["routing"]["success_transition"] = "END"
    identity_payload = dict(forged)
    identity_payload.pop("invocation_id")
    forged["invocation_id"] = StageInvocationBuilder._invocation_id(identity_payload)
    result = _result(forged, "RULES_RESOLVED", outputs=_full_outputs(forged))
    with pytest.raises(ValueError, match="routing does not match canonical stage contract"):
        ExecutionRecordBuilder(ROOT).build(forged, result)


def test_observer_role_cannot_be_forged_into_executable_invocation_record() -> None:
    invocation = _invocation("WORK_PACKAGE_RESEARCH")
    forged = json.loads(json.dumps(invocation))
    forged["stage"]["role_id"] = "CI_ORCHESTRATOR"
    identity_payload = dict(forged)
    identity_payload.pop("invocation_id")
    forged["invocation_id"] = StageInvocationBuilder._invocation_id(identity_payload)
    result = _result(
        forged,
        "CANDIDATES_READY",
        outputs=_full_outputs(forged),
    )
    with pytest.raises(ValueError, match="not authorized to execute stage WORK_PACKAGE_RESEARCH"):
        ExecutionRecordBuilder(ROOT).build(forged, result)


def test_record_identity_is_deterministic_and_evidence_bound() -> None:
    invocation = _invocation("RULE_RESOLUTION")
    result = _result(invocation, "RULES_RESOLVED", outputs=_full_outputs(invocation))
    builder = ExecutionRecordBuilder(ROOT)
    first = builder.build(invocation, result)
    second = builder.build(invocation, result)
    assert first["record_id"] == second["record_id"]

    changed = json.loads(json.dumps(result))
    changed["evidence_refs"] = [
        {"kind": "RUN", "ref": "github-actions://run/123", "content_hash": "sha256:" + ("1" * 64)}
    ]
    third = builder.build(invocation, changed)
    assert third["record_id"] != first["record_id"]
