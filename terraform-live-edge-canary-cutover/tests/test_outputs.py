"""Verify live edge canary cutover seal and interacting posture."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

EDGE = Path("/app/var/edge")
SEAL = EDGE / "cutover-seal.json"
SNAPSHOT = EDGE / "snapshot.json"
TF = Path("/app/environment/terraform")
INVENTORY = TF / "inventory" / "edge-fleet.auto.tfvars.json"
CONTRACT = Path("/app/environment/docs/cutover-contract.md")


@pytest.fixture(scope="module")
def inventory() -> dict:
    """Load the authoritative edge inventory."""
    assert INVENTORY.is_file(), "missing inventory artifact"
    return json.loads(INVENTORY.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def seal() -> dict:
    """Load the cutover seal produced by apply."""
    assert SEAL.is_file(), "missing cutover-seal.json"
    return json.loads(SEAL.read_text(encoding="utf-8"))


def test_contract_and_terraform_tree_present():
    """Contract doc and terraform root must be present in artifacts."""
    assert CONTRACT.is_file()
    assert (TF / "main.tf").is_file()
    assert (TF / "modules" / "canary_route").is_dir()
    assert (TF / "modules" / "dns_cutover").is_dir()


def test_seal_matches_inventory_contract(seal: dict, inventory: dict):
    """Seal fields must satisfy cutover-contract section 5 against inventory."""
    assert seal["status"] == "ok"
    assert seal["engagement"] == inventory["engagement"]
    assert seal["hostname"] == inventory["edge_hostname"]
    assert seal["canary_weight_green"] == 100
    assert seal["dns_target_pool"] == inventory["green_pool"]["id"]
    assert seal["waf_mode"] == "enforce"
    assert seal["error_rate_pct"] <= float(inventory["error_budget_pct"])
    assert seal["blue_healthy"] is True
    assert seal["green_healthy"] is True
    assert seal["tls_fingerprint"] == inventory["tls_fingerprint"]
    assert seal["steps_applied"] == inventory["canary_steps"]
    assert seal["networks_ready"] >= len(inventory["networks"])


def test_snapshot_agrees_with_seal(seal: dict, inventory: dict):
    """Persisted snapshot must agree with seal on canary, waf, dns and tls."""
    assert SNAPSHOT.is_file(), "missing snapshot.json"
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    route = inventory["canary_route_id"]
    canary = (snap.get("canaries") or {}).get(route) or {}
    assert int(canary.get("weight_green", -1)) == 100
    waf = (snap.get("wafs") or {}).get(inventory["waf"]["id"]) or {}
    assert waf.get("mode") == "enforce"
    tls = (snap.get("tls") or {}).get(inventory["tls_id"]) or {}
    assert tls.get("fingerprint") == inventory["tls_fingerprint"]
    assert tls.get("hostname") == inventory["edge_hostname"]

    dns_map = snap.get("dns") or {}
    dns = None
    for rec in dns_map.values():
        if rec.get("zone") == inventory["dns_zone"] and rec.get("name") == inventory["dns_name"]:
            dns = rec
            break
    assert dns is not None, "dns record missing from snapshot"
    assert dns.get("target_pool") == inventory["green_pool"]["id"]


def test_metamorphic_second_apply_keeps_seal(seal: dict, inventory: dict):
    """Re-running edge-cutover-apply must keep a contract-satisfying seal."""
    before = SEAL.read_text(encoding="utf-8")
    env = os.environ.copy()
    env["TF_CLI_CONFIG_FILE"] = "/app/environment/terraform.tfrc"
    completed = subprocess.run(
        ["/app/bin/edge-cutover-apply"],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
    after = json.loads(SEAL.read_text(encoding="utf-8"))
    assert after["status"] == "ok"
    assert after["canary_weight_green"] == 100
    assert after["waf_mode"] == "enforce"
    assert after["dns_target_pool"] == inventory["green_pool"]["id"]
    assert after["tls_fingerprint"] == inventory["tls_fingerprint"]
    assert json.loads(before)["steps_applied"] == after["steps_applied"]
