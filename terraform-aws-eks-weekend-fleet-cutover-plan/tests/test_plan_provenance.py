"""The document has to be a genuine plan of the shipped, offline configuration."""

from __future__ import annotations

import re

BANNED_SOURCE_PATTERNS = {
    "data source": r'(?m)^\s*data\s+"',
    "import block": r"(?m)^\s*import\s*\{",
    "remote state": r'"terraform_remote_state"',
    "chart repository": r"(?m)^\s*repository\s*=",
    "local file writer": r'resource\s+"local_(file|sensitive_file)"',
}


def test_document_is_a_completed_terraform_plan(plan):
    """The artifact carries plan-document metadata and reports a clean render."""
    assert plan.get("format_version", "").startswith("1."), plan.get("format_version")
    assert plan.get("terraform_version"), "plan document must record a Terraform version"
    assert plan.get("errored") is False, "the plan reported errors"
    assert plan.get("complete") is True, "the plan is incomplete"
    assert plan.get("resource_changes"), "the plan proposes no resources at all"


def test_everything_is_a_fresh_create_inside_the_fleet_module(plan):
    """Nothing was imported or refreshed, and no resource escaped the module."""
    for change in plan["resource_changes"]:
        assert change["change"]["actions"] == ["create"], change["address"]
        assert change.get("importing") is None, f"{change['address']} was imported"
        assert change["address"].startswith("module.eks_weekend_fleet."), change["address"]

    module_calls = plan["configuration"]["root_module"]["module_calls"]
    assert set(module_calls) == {"eks_weekend_fleet"}, sorted(module_calls)


def test_plan_was_rendered_against_the_shipped_inventory(plan, inventory):
    """Every root variable in the plan still matches the delivered inventory."""
    rendered = {name: body.get("value") for name, body in plan["variables"].items()}
    assert rendered == inventory


def test_planned_resources_are_backed_by_real_configuration_blocks(plan):
    """Each planned resource type traces back to a managed block in the config."""
    configured = plan["configuration"]["root_module"]["module_calls"]["eks_weekend_fleet"]
    blocks = configured["module"]["resources"]

    modes = {entry.get("mode") for entry in blocks}
    assert modes == {"managed"}, f"configuration contains non-managed blocks: {modes}"

    planned_types = {change["type"] for change in plan["resource_changes"]}
    configured_types = {entry["type"] for entry in blocks}
    assert planned_types == configured_types, (
        f"planned but unconfigured: {sorted(planned_types - configured_types)}; "
        f"configured but unplanned: {sorted(configured_types - planned_types)}"
    )


def test_module_source_avoids_the_forbidden_lookup_and_authoring_shortcuts(module_source):
    """No data sources, imports, remote state, chart repositories or file writers."""
    for label, pattern in BANNED_SOURCE_PATTERNS.items():
        match = re.search(pattern, module_source)
        assert match is None, f"module uses a forbidden {label}: {match.group(0)!r}"
