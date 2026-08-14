"""Normalize one or more feedback events into an owned canonical finding."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

from execution.authority import ExecutionAuthority
from retrieval.policy import RetrievalPolicy

from .model import FindingState, Severity, finding_identity
from .registry import LearningStore
from .schema_validation import LearningSchemaValidator

_SEVERITY_ORDER = {
    Severity.INFO.value: 0,
    Severity.LOW.value: 1,
    Severity.MEDIUM.value: 2,
    Severity.HIGH.value: 3,
    Severity.CRITICAL.value: 4,
}
_TRUSTED_POLICY_RESOLVERS = frozenset({"ADJUDICATOR", "CI_ORCHESTRATOR"})
_AUTHORITATIVE_PREFIXES = (
    "TERMINUS_3_AI_INSTRUCTIONS.md",
    ".terminus/AGENT_SYSTEM.md",
    ".terminus/agents/",
    ".terminus/reviewers/",
)


class FindingNormalizer:
    def __init__(self, root: Path, *, store: LearningStore | None = None):
        self.root = root.resolve()
        self.store = store or LearningStore(self.root)
        self.schemas = LearningSchemaValidator(self.root)
        self.policy = RetrievalPolicy(self.root)
        self.authority = ExecutionAuthority(self.policy)

    def normalize(
        self,
        events: Iterable[Mapping[str, Any]],
        *,
        generalized_problem: str,
        root_cause_class: str,
        repair_stages: list[str] | None = None,
        should_have_been_caught_by: list[str] | None = None,
        closure_conditions: list[str] | None = None,
        verification_owner: str = "CI_ORCHESTRATOR",
    ) -> dict[str, Any]:
        values = [dict(event) for event in events]
        if not values:
            raise ValueError("at least one feedback event is required")
        for event in values:
            self.schemas.validate("feedback", event)
        task_ids = {event["task"]["task_id"] for event in values}
        commits = {event["task"]["task_commit"] for event in values}
        if len(task_ids) != 1 or len(commits) != 1:
            raise ValueError("one finding cannot combine feedback from different task snapshots")

        categories = {
            str(event["observation"].get("category"))
            for event in values
            if event["observation"].get("category")
        }
        state = FindingState.OPEN.value
        if "POLICY_CONFLICT" in categories:
            if categories != {"POLICY_CONFLICT"}:
                raise ValueError("policy-conflict feedback cannot be mixed with ordinary categories")
            self._validate_policy_conflict(values)
            state = FindingState.POLICY_CONFLICT.value
            category = "POLICY_CONFLICT"
        elif len(categories) > 1:
            state = FindingState.FEEDBACK_CONFLICT.value
            category = "FEEDBACK_CONFLICT"
        else:
            category = next(iter(categories), "UNCLASSIFIED")

        stage_hints = self._unique(
            str(event["observation"]["stage_hint"])
            for event in values
            if event["observation"].get("stage_hint")
        )
        stages = self._unique(repair_stages or stage_hints)
        if not stages:
            stages = ["RULE_RESOLUTION"]
        for stage_id in stages:
            if stage_id not in self.policy.stages:
                raise ValueError(f"unknown repair stage: {stage_id}")
        roles = self._unique(
            self.authority.primary_role_for_stage(stage_id) for stage_id in stages
        )
        introduced_stage = stage_hints[0] if len(stage_hints) == 1 else None
        severity = max(
            (event["observation"]["severity"] for event in values),
            key=lambda item: _SEVERITY_ORDER[str(item)],
        )
        finding: dict[str, Any] = {
            "schema_version": "1.0",
            "task_id": next(iter(task_ids)),
            "task_commit": next(iter(commits)),
            "category": category,
            "severity": severity,
            "state": state,
            "signals": self._unique(event["feedback_id"] for event in values),
            "ownership": {
                "introduced_stage": introduced_stage,
                "should_have_been_caught_by": self._unique(should_have_been_caught_by or []),
                "repair_stages": stages,
                "repair_roles": roles,
                "detected_by": self._unique(event["source"]["type"] for event in values),
            },
            "problem": {
                "task_specific": "\n".join(
                    f"[{event['source']['type']}] {event['observation']['message']}"
                    for event in values
                ),
                "generalized": generalized_problem.strip(),
                "root_cause_class": root_cause_class.strip(),
                "escape_depth": len(self._unique(should_have_been_caught_by or [])),
            },
            "closure": {
                "conditions": closure_conditions
                or ["The repaired task independently passes the detector that exposed this finding."],
                "verification_owner": verification_owner,
                "verified_by_feedback": [],
            },
        }
        if not generalized_problem.strip() or not root_cause_class.strip():
            raise ValueError("generalized_problem and root_cause_class are required")
        finding["finding_id"] = finding_identity(finding)
        self.schemas.validate("finding", finding)
        self.store.findings.append(finding)
        return finding

    def _validate_policy_conflict(self, events: list[Mapping[str, Any]]) -> None:
        """Require trusted, structured authoritative-source conflict semantics."""
        for event in events:
            provenance = event["provenance"]
            source = event["source"]
            trusted = (
                source["type"] == "HUMAN_REVIEW"
                and provenance["trust_status"] == "HUMAN_ASSERTED"
            ) or (
                source["producer"] in _TRUSTED_POLICY_RESOLVERS
                and provenance["trust_status"] == "REPOSITORY_RESOLVED"
            )
            if not trusted:
                raise ValueError(
                    "POLICY_CONFLICT requires trusted human or adjudicator/orchestrator provenance"
                )
            detail = event["observation"].get("value")
            if not isinstance(detail, Mapping):
                raise ValueError("POLICY_CONFLICT requires structured observation.value")
            sources = detail.get("conflicting_sources")
            gate = detail.get("affected_gate")
            if not isinstance(sources, list) or len(set(map(str, sources))) < 2:
                raise ValueError("POLICY_CONFLICT requires at least two conflicting authoritative sources")
            for source_path in sources:
                if not isinstance(source_path, str) or not self._authoritative_source(source_path):
                    raise ValueError(
                        f"POLICY_CONFLICT source is not an authoritative repository rule: {source_path}"
                    )
            if not isinstance(gate, str) or gate not in self.policy.stages:
                raise ValueError("POLICY_CONFLICT affected_gate must be a registered lifecycle stage")

    def _authoritative_source(self, value: str) -> bool:
        path = PurePosixPath(value)
        if value.startswith("/") or "\\" in value or ".." in path.parts:
            return False
        allowed = value == _AUTHORITATIVE_PREFIXES[0] or any(
            value.startswith(prefix) for prefix in _AUTHORITATIVE_PREFIXES[1:]
        )
        return allowed and (self.root / value).is_file()

    @staticmethod
    def _unique(values: Iterable[str]) -> list[str]:
        return list(dict.fromkeys(str(value) for value in values if str(value)))
