"""Policy attachment loading, validation, and resource matching."""

from __future__ import annotations

from typing import Any

from cc.errors import ValidationException
from cc.home import attached_policies, policy_document, principal, repo_arn
from cc.iam.actions import service_of
from cc.models import Statement
from cc.util import glob_match

KNOWN_SERVICES = frozenset({"codecommit", "pipeline", "audit", "webhook"})
VALID_EFFECTS = frozenset({"Allow", "Deny"})


def validate_document(policy_id: str, body: dict[str, Any]) -> None:
    """Reject a policy document the evaluator cannot interpret."""
    statements = body.get("Statement")
    if not isinstance(statements, list) or not statements:
        raise ValidationException(
            "POLICY_MALFORMED", f"policy {policy_id!r} has no Statement array"
        )
    for index, entry in enumerate(statements):
        if not isinstance(entry, dict):
            raise ValidationException(
                "POLICY_MALFORMED", f"policy {policy_id!r} statement {index} is not an object"
            )
        effect = str(entry.get("Effect") or "Allow")
        if effect not in VALID_EFFECTS:
            raise ValidationException(
                "POLICY_MALFORMED", f"policy {policy_id!r} has unknown Effect {effect!r}"
            )


def statements_of(policy_id: str) -> list[Statement]:
    """Parse one attached policy document into statements."""
    body = policy_document(policy_id)
    if not body:
        raise ValidationException("POLICY_NOT_FOUND", f"no policy document {policy_id!r}")
    validate_document(policy_id, body)
    parsed: list[Statement] = []
    for index, entry in enumerate(body.get("Statement") or []):
        parsed.append(Statement.from_dict(entry, policy_id, index))
    return parsed


def statements_for(name: str) -> list[Statement]:
    """Every statement reachable from a principal's attachments, in order."""
    if principal(name) is None:
        return []
    collected: list[Statement] = []
    for policy_id in attached_policies(name):
        collected.extend(statements_of(policy_id))
    return collected


def unknown_services(statements: list[Statement]) -> list[str]:
    """Services named by statements that this control plane does not implement."""
    found: list[str] = []
    for statement in statements:
        for action in statement.actions:
            if action == "*":
                continue
            service = service_of(action)
            if service and service not in KNOWN_SERVICES and service not in found:
                found.append(service)
    return found


def resource_matches(pattern: str, arn: str) -> bool:
    """Test one Resource entry against the target ARN."""
    if pattern == "*":
        return True
    return glob_match(pattern, arn)


def any_resource_matches(patterns: tuple[str, ...], arn: str) -> bool:
    """True when at least one Resource entry of a statement covers the ARN."""
    return any(resource_matches(pattern, arn) for pattern in patterns)


def target_arn(repo: str) -> str:
    """ARN a request is evaluated against."""
    return repo_arn(repo)


def describe_attachments(name: str) -> dict[str, Any]:
    """Attachment summary used by operator listings."""
    entry = principal(name) or {}
    statements = statements_for(name)
    return {
        "principal": name,
        "type": str(entry.get("type") or "unknown"),
        "policies": attached_policies(name),
        "statements": len(statements),
        "deny_statements": sum(1 for item in statements if item.is_deny),
    }
