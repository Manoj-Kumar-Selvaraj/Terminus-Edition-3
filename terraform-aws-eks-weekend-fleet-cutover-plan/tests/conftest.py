"""Shared fixtures and plan-document helpers for the weekend fleet verifier."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

PLAN_PATH = Path("/app/output/eks_weekend_fleet_plan.json")
MODULE_DIR = Path("/app/environment/terraform/modules/eks_weekend_fleet")
INVENTORY_PATH = Path(__file__).parent / "fixtures" / "weekend-fleet.auto.tfvars.json"


@pytest.fixture(scope="session")
def plan():
    """The rendered `terraform show -json` document the review board reads."""
    assert PLAN_PATH.is_file(), f"{PLAN_PATH} was not produced"
    with PLAN_PATH.open(encoding="utf-8") as handle:
        document = json.load(handle)
    assert isinstance(document, dict), "plan document must be a JSON object"
    return document


@pytest.fixture(scope="session")
def inventory():
    """Sealed copy of the inventory the plan is supposed to be rendered from."""
    with INVENTORY_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="session")
def module_source():
    """Every `.tf` file of the delivered module, concatenated."""
    assert MODULE_DIR.is_dir(), f"{MODULE_DIR} is missing"
    files = sorted(MODULE_DIR.rglob("*.tf"))
    assert files, f"{MODULE_DIR} contains no Terraform files"
    return "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in files)


def changes(plan, resource_type):
    """Every planned resource change of one Terraform resource type."""
    return [c for c in plan.get("resource_changes", []) if c.get("type") == resource_type]


def after(change):
    """The planned end state of a single resource change."""
    value = change.get("change", {}).get("after")
    assert value is not None, f"{change.get('address')} has no planned end state"
    return value


def afters(plan, resource_type):
    """Planned end states of every resource of one type."""
    return [after(change) for change in changes(plan, resource_type)]


def keyed(values, field):
    """Index a list of planned end states by one of their scalar fields."""
    return {value[field]: value for value in values}


def only(values, description):
    """Assert exactly one planned resource and return it."""
    assert len(values) == 1, f"expected exactly one {description}, found {len(values)}"
    return values[0]


def block(value, name):
    """Unwrap a single-instance nested block from an SDK-style end state."""
    nested = value.get(name)
    assert isinstance(nested, list) and len(nested) == 1, (
        f"expected exactly one {name!r} block, found {nested!r}"
    )
    return nested[0]


def statements(policy_json):
    """Parse an IAM policy document and index its statements by Sid."""
    document = json.loads(policy_json)
    assert document.get("Version") == "2012-10-17", "IAM policies must be 2012-10-17"
    found = document["Statement"]
    assert isinstance(found, list), "Statement must be a list"
    indexed = {}
    for entry in found:
        sid = entry.get("Sid")
        assert sid, f"every statement needs a Sid, got {entry!r}"
        indexed[sid] = entry
    assert len(indexed) == len(found), "statement Sids must be unique"
    return indexed


def as_set(value):
    """Normalise an IAM Action/Resource field to a set of strings."""
    if isinstance(value, str):
        return {value}
    return set(value)
