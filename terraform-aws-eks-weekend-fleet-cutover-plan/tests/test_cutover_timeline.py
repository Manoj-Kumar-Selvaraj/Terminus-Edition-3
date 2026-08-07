"""Weekend cutover timeline produced by the offline fleet simulator."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

TIMELINE_PATH = Path("/app/output/eks_weekend_cutover_timeline.json")


@pytest.fixture(scope="session")
def timeline():
    """The cutover transcript the simulator wrote from the rendered plan."""
    assert TIMELINE_PATH.is_file(), f"{TIMELINE_PATH} was not produced"
    with TIMELINE_PATH.open(encoding="utf-8") as handle:
        document = json.load(handle)
    assert isinstance(document, dict), "timeline must be a JSON object"
    return document


def test_cutover_timeline_reports_success(timeline):
    """Simulator must finish with ok=true and no error string."""
    assert timeline.get("ok") is True
    assert not timeline.get("error")


def test_cutover_runs_friday_then_monday(timeline, inventory):
    """The transcript steps Friday scale-down before Monday scale-up."""
    steps = timeline["steps"]
    assert [step["at"] for step in steps] == ["friday-scale-down", "monday-scale-up"]
    assert steps[0]["action"] == "scale-down"
    assert steps[1]["action"] == "scale-up"
    assert timeline["timezone"] == inventory["weekend_schedule"]["timezone"]
    assert (
        timeline["flexible_window_minutes"]
        == inventory["weekend_schedule"]["flexible_window_minutes"]
    )


def test_cutover_parks_only_weekend_groups_then_restores_them(timeline, inventory):
    """Parked groups hit zero on Friday and return to inventory sizes on Monday."""
    parked = {
        name for name, spec in inventory["node_groups"].items() if spec["weekend_parked"]
    }
    non_parked = set(inventory["node_groups"]) - parked
    assert set(timeline["parked_node_groups"]) == parked

    down, up = timeline["steps"]
    assert set(down["payload_node_groups"]) == parked
    assert set(up["payload_node_groups"]) == parked

    for name in parked:
        assert down["after"][name]["min_size"] == 0
        assert down["after"][name]["desired_size"] == 0
        assert up["after"][name]["min_size"] == inventory["node_groups"][name]["min_size"]
        assert (
            up["after"][name]["desired_size"]
            == inventory["node_groups"][name]["desired_size"]
        )

    for name in non_parked:
        assert down["after"][name] == down["before"][name]
        assert up["after"][name] == down["before"][name]


def test_cutover_invariants_all_hold(timeline):
    """Every named cutover invariant in the transcript must be true."""
    required = {
        "scale_down_before_scale_up",
        "flexible_window_does_not_invert_order",
        "payload_keys_exact",
        "parked_hit_zero",
        "parked_restored",
        "non_parked_unchanged",
    }
    invariants = timeline["invariants"]
    assert required <= set(invariants)
    assert all(invariants[name] is True for name in required)
