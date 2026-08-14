"""Canonical models and deterministic identities for Terminus feedback learning."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum
from typing import Any, Mapping


class FeedbackSource(StrEnum):
    HUMAN_REVIEW = "HUMAN_REVIEW"
    INDEPENDENT_REVIEW = "INDEPENDENT_REVIEW"
    REVIEWER_REVIEW = "REVIEWER_REVIEW"
    PORTAL_CI = "PORTAL_CI"
    REPOSITORY_CI = "REPOSITORY_CI"
    LLMAJ = "LLMAJ"
    MODEL_DIAGNOSTIC = "MODEL_DIAGNOSTIC"
    MODEL_TRIAL = "MODEL_TRIAL"
    DIFFICULTY = "DIFFICULTY"
    FINAL_REVIEW = "FINAL_REVIEW"
    SUBMISSION_RESULT = "SUBMISSION_RESULT"
    RUNTIME = "RUNTIME"


class Severity(StrEnum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FindingState(StrEnum):
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    REPAIRED = "REPAIRED"
    VERIFIED = "VERIFIED"
    CLOSED = "CLOSED"
    WONT_FIX = "WONT_FIX"
    FEEDBACK_CONFLICT = "FEEDBACK_CONFLICT"
    POLICY_CONFLICT = "POLICY_CONFLICT"


class LessonState(StrEnum):
    CANDIDATE = "CANDIDATE"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def stable_id(prefix: str, payload: Mapping[str, Any]) -> str:
    digest = hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()
    return f"{prefix}_{digest}"


def content_hash(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def feedback_identity(payload: Mapping[str, Any]) -> str:
    identity = {key: value for key, value in payload.items() if key != "feedback_id"}
    return stable_id("feedback", identity)


def finding_identity(payload: Mapping[str, Any]) -> str:
    identity = {
        key: value
        for key, value in payload.items()
        if key not in {"finding_id", "state"}
    }
    closure = dict(identity.get("closure", {}))
    closure.pop("verified_by_feedback", None)
    closure.pop("repaired_task_commit", None)
    identity["closure"] = closure
    return stable_id("finding", identity)


def lesson_identity(payload: Mapping[str, Any]) -> str:
    identity = {
        key: value
        for key, value in payload.items()
        if key not in {"lesson_id", "state", "promotion", "sources"}
    }
    return stable_id("lesson", identity)


def pattern_identity(payload: Mapping[str, Any]) -> str:
    identity = {
        "category": payload.get("category"),
        "root_cause_class": payload.get("root_cause_class"),
    }
    return stable_id("pattern", identity)
