from __future__ import annotations

from typing import Any

RULE_REQUIRED = ["repo", "destination", "required", "pool"]
BINDING_REQUIRED = ["repo", "ref", "pipeline"]
WEBHOOK_REQUIRED = ["id", "url"]


def validate_object(obj: dict[str, Any], required: list[str]) -> list[str]:
    return [k for k in required if k not in obj]


def validate_principals_doc(doc: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    for name, entry in doc.items():
        if not isinstance(entry, dict):
            errs.append(f"{name}: not an object")
            continue
        errs.extend(f"{name}.{e}" for e in validate_object(entry, ["policies"]))
    return errs


def validate_rules_doc(doc: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    for i, rule in enumerate(doc.get("rules") or []):
        missing = validate_object(rule, RULE_REQUIRED)
        errs.extend(f"rules[{i}].{m}" for m in missing)
    return errs


def validate_pipelines_doc(doc: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    for i, b in enumerate(doc.get("bindings") or []):
        missing = validate_object(b, BINDING_REQUIRED)
        errs.extend(f"bindings[{i}].{m}" for m in missing)
    return errs


def validate_webhooks_doc(doc: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    for i, w in enumerate(doc.get("webhooks") or []):
        missing = validate_object(w, WEBHOOK_REQUIRED)
        errs.extend(f"webhooks[{i}].{m}" for m in missing)
    return errs


def validate_all(
    principals: dict[str, Any],
    rules: dict[str, Any],
    pipelines: dict[str, Any],
    webhooks: dict[str, Any],
) -> dict[str, list[str]]:
    return {
        "principals": validate_principals_doc(principals),
        "rules": validate_rules_doc(rules),
        "pipelines": validate_pipelines_doc(pipelines),
        "webhooks": validate_webhooks_doc(webhooks),
    }
