"""Blind A/B evaluation for human-writing calibration effectiveness."""

from __future__ import annotations

import hashlib
import json
from typing import Any


GOOD_HIGH = (
    "requirement_completeness",
    "technical_precision",
    "human_information_selection",
    "natural_grouping",
    "implementation_distance",
    "verbosity_fit",
)
GOOD_LOW = (
    "ai_template_signal",
    "synthetic_completeness",
    "rubric_mirroring",
    "implementation_leakage",
)
_ALLOWED_EVALUATOR_ROLES = {
    "Instruction Reviewer",
    "Human Quality Reviewer",
    "Blind A/B Evaluator",
}


class EvaluationError(ValueError):
    """Raised for malformed blind-evaluation packets or results."""


def prepare_blind_ab(
    *,
    task_id: str,
    baseline_text: str,
    calibrated_text: str,
    requirement_contract_sha256: str,
    writer_actor_id: str,
) -> dict[str, Any]:
    """Create an anonymized A/B packet plus a sealed origin/author mapping."""
    if not baseline_text.strip() or not calibrated_text.strip():
        raise EvaluationError("both variants must be non-empty")
    if not writer_actor_id.strip():
        raise EvaluationError("writer_actor_id is required")
    identity = {
        "task_id": task_id,
        "baseline_sha256": _sha(baseline_text),
        "calibrated_sha256": _sha(calibrated_text),
        "requirement_contract_sha256": requirement_contract_sha256,
    }
    swap = int(_hash(identity)[0], 16) % 2 == 1
    ordered = (
        [("baseline", baseline_text), ("calibrated", calibrated_text)]
        if not swap
        else [("calibrated", calibrated_text), ("baseline", baseline_text)]
    )
    public = {
        "eval_id": "hwab-" + _hash(identity)[:20],
        "task_id": task_id,
        "requirement_contract_sha256": requirement_contract_sha256,
        "variants": {"A": ordered[0][1], "B": ordered[1][1]},
        "dimensions": {
            "higher_is_better": list(GOOD_HIGH),
            "lower_is_better": list(GOOD_LOW),
        },
        "eligibility_gates": {
            "requirement_completeness": 5,
            "technical_precision_minimum": 4,
            "rubric_mirroring_maximum": 1,
            "implementation_leakage_maximum": 1,
            "ai_template_signal_maximum": 2,
        },
        "review_instruction": (
            "Score both variants independently. Completeness/precision are hard gates; "
            "material rubric mirroring or implementation leakage also disqualifies a variant."
        ),
    }
    sealed_mapping = {
        "eval_id": public["eval_id"],
        "mapping": {"A": ordered[0][0], "B": ordered[1][0]},
        "variant_sha256": {"A": _sha(ordered[0][1]), "B": _sha(ordered[1][1])},
        "writer_actor_hash": _sha(writer_actor_id),
    }
    return {"public_packet": public, "sealed_mapping": sealed_mapping}


def score_blind_ab(
    *,
    public_packet: dict[str, Any],
    sealed_mapping: dict[str, Any],
    scores: dict[str, dict[str, int]],
    evaluator_actor_id: str,
    evaluator_role: str,
) -> dict[str, Any]:
    """Validate independent scores and reveal preference only after they are fixed."""
    if public_packet.get("eval_id") != sealed_mapping.get("eval_id"):
        raise EvaluationError("public/sealed eval ids differ")
    if evaluator_role not in _ALLOWED_EVALUATOR_ROLES:
        raise EvaluationError(f"unauthorized evaluator role: {evaluator_role}")
    if not evaluator_actor_id.strip():
        raise EvaluationError("evaluator_actor_id is required")
    evaluator_hash = _sha(evaluator_actor_id)
    if evaluator_hash == sealed_mapping.get("writer_actor_hash"):
        raise EvaluationError("blind evaluator must be independent from the writer")

    for label in ("A", "B"):
        dimensions = scores.get(label)
        if not isinstance(dimensions, dict):
            raise EvaluationError(f"missing score block for {label}")
        expected = set(GOOD_HIGH) | set(GOOD_LOW)
        if set(dimensions) != expected:
            raise EvaluationError(f"{label} dimensions must exactly match evaluation schema")
        for name, value in dimensions.items():
            if not isinstance(value, int) or not 0 <= value <= 5:
                raise EvaluationError(f"{label}.{name} must be integer 0..5")

    eligible = {
        label: (
            scores[label]["requirement_completeness"] == 5
            and scores[label]["technical_precision"] >= 4
            and scores[label]["rubric_mirroring"] <= 1
            and scores[label]["implementation_leakage"] <= 1
            and scores[label]["ai_template_signal"] <= 2
        )
        for label in ("A", "B")
    }
    utility = {
        label: sum(scores[label][name] for name in GOOD_HIGH)
        - sum(scores[label][name] for name in GOOD_LOW)
        for label in ("A", "B")
    }
    if eligible["A"] and not eligible["B"]:
        preferred = "A"
    elif eligible["B"] and not eligible["A"]:
        preferred = "B"
    elif not eligible["A"] and not eligible["B"]:
        preferred = "NEITHER"
    elif utility["A"] > utility["B"]:
        preferred = "A"
    elif utility["B"] > utility["A"]:
        preferred = "B"
    else:
        preferred = "TIE"

    mapped = (
        sealed_mapping["mapping"].get(preferred)
        if preferred in {"A", "B"}
        else preferred.lower()
    )
    return {
        "eval_id": public_packet["eval_id"],
        "preferred_blind_label": preferred,
        "preferred_origin": mapped,
        "calibrated_wins": mapped == "calibrated",
        "eligibility": eligible,
        "utility": utility,
        "scores": scores,
        "evaluator_binding": {
            "actor_hash": evaluator_hash,
            "role": evaluator_role,
            "independent_from_writer": True,
        },
    }


def aggregate_ab_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate blind A/B results without instruction text."""
    decided = [
        result
        for result in results
        if result.get("preferred_origin") in {"baseline", "calibrated"}
        and result.get("evaluator_binding", {}).get("independent_from_writer") is True
    ]
    calibrated_wins = sum(
        result.get("preferred_origin") == "calibrated" for result in decided
    )
    baseline_wins = sum(
        result.get("preferred_origin") == "baseline" for result in decided
    )
    return {
        "total_results": len(results),
        "decided_results": len(decided),
        "calibrated_wins": calibrated_wins,
        "baseline_wins": baseline_wins,
        "calibrated_win_rate": calibrated_wins / len(decided) if decided else None,
    }


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
