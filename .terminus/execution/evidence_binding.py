"""Fail-closed evidence binding for acceptance-sensitive stage results."""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from typing import Any, Mapping

_SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")

_REQUIREMENTS: dict[tuple[str, str], dict[str, Any]] = {
    ("RUNTIME_AUTHENTICITY", "PASS"): {"min": 1, "kinds": {"RUN", "ARTIFACT", "RESULT", "FILE"}},
    ("DETERMINISTIC_VALIDATION", "PASS"): {"min": 1, "kinds": {"RUN", "ARTIFACT", "RESULT"}},
    ("QUALITY_INTERLOCK", "QUALITY_INTERLOCK_PASS"): {"min": 2, "kinds": {"RESULT"}, "ids": ["Q4_RESULT.review_id", "Q6_RESULT.review_id"]},
    ("PRE_LLMAJ", "PASS"): {"min": 1, "kinds": {"RESULT", "ARTIFACT"}},
    ("MODEL_DIAGNOSTIC_AGGREGATE", "COMPLETE"): {"min": 2, "kinds": {"RESULT"}, "ids": ["GPT_PERSPECTIVE_RESULT.result_id", "CLAUDE_PERSPECTIVE_RESULT.result_id"]},
    ("HARBOR_LLMAJ", "PASS"): {"min": 1, "kinds": {"RUN", "RESULT", "EXTERNAL", "ARTIFACT"}, "ids": ["HARBOR_RUN_ID"]},
    ("OFFICIAL_MODEL_TRIALS", "COMPLETE"): {"min": 10, "kinds": {"RUN", "RESULT", "EXTERNAL"}},
    ("TRIAL_ANALYSIS", "COMPLETE"): {"min": 1, "kinds": {"RESULT", "ARTIFACT"}},
    ("DIFFICULTY_ASSESSMENT", "PASS"): {"min": 2, "kinds": {"RESULT", "ARTIFACT"}},
    ("FINAL_REVIEW", "PASS"): {"min": 3, "kinds": {"RESULT", "ARTIFACT"}, "counts": {"RESULT": 2, "ARTIFACT": 1}, "ids": ["FINAL_COMPLIANCE.review_id", "FINAL_HUMAN_QUALITY.review_id"]},
    ("SUBMISSION_READY", "SUBMISSION_READY"): {"min": 1, "kinds": {"RESULT", "ARTIFACT"}},
}


def _resolve(outputs: Mapping[str, Any], path: str) -> Any:
    current: Any = outputs
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            raise ValueError(f"evidence identity path is missing: {path}")
        current = current[part]
    return current


def validate_evidence_binding(stage_id: str, status: str, outputs: Mapping[str, Any], refs: list[dict[str, Any]]) -> None:
    requirement = _REQUIREMENTS.get((stage_id, status))
    if requirement is None:
        return
    qualifying = [ref for ref in refs if ref.get("kind") in requirement["kinds"]]
    if len(qualifying) < requirement["min"]:
        raise ValueError(f"{stage_id}/{status} requires at least {requirement['min']} immutable evidence refs")
    if len({str(ref.get("ref")) for ref in qualifying}) != len(qualifying):
        raise ValueError(f"{stage_id}/{status} evidence refs must be unique")
    for ref in qualifying:
        if not isinstance(ref.get("content_hash"), str) or not _SHA256.fullmatch(ref["content_hash"]):
            raise ValueError(f"{stage_id}/{status} evidence refs require sha256 content_hash")
    counts = Counter(str(ref.get("kind")) for ref in qualifying)
    for kind, minimum in requirement.get("counts", {}).items():
        if counts[kind] < minimum:
            raise ValueError(f"{stage_id}/{status} requires at least {minimum} {kind} evidence refs")
    for path in requirement.get("ids", []):
        identity = str(_resolve(outputs, path)).strip()
        if not identity or not any(identity in str(ref.get("ref", "")) for ref in qualifying):
            raise ValueError(f"{stage_id}/{status} evidence refs do not bind output identity {path}")
    if stage_id == "OFFICIAL_MODEL_TRIALS" and status == "COMPLETE":
        identities: list[str] = []
        for path in ("GPT_5_5_TRIALS", "CLAUDE_OPUS_4_8_TRIALS"):
            trials = _resolve(outputs, path)
            if not isinstance(trials, list) or len(trials) != 5:
                raise ValueError(f"{path} must contain exactly five trials")
            for trial in trials:
                if not isinstance(trial, Mapping) or not str(trial.get("run_id", "")).strip():
                    raise ValueError(f"{path} trials require immutable run_id")
                identities.append(str(trial["run_id"]).strip())
        if len(set(identities)) != 10:
            raise ValueError("official trial run_id values must be unique")
        for identity in identities:
            if not any(identity in str(ref.get("ref", "")) for ref in qualifying):
                raise ValueError(f"official trial run_id is not bound to evidence ref: {identity}")
