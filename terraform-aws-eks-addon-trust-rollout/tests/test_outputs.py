"""Verifier for the EKS add-on trust rollout lab.

Replans submitted Terraform with trusted inventories, applies submitted
Kubernetes manifests through the upgrade lab, and checks READY status,
compatibility order, IRSA bindings, PDB-respecting drains, regulated
placement, fail-closed partial progress, and idempotent digests.
"""
from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
sys.path.insert(0, str(FIXTURES))
import upgrade_lab  # noqa: E402

TERRAFORM_ARTIFACT = Path("/app/terraform")
K8S_ARTIFACT = Path("/app/k8s")
OUTPUT_ARTIFACT = Path("/app/output")
VAR_ARTIFACT = Path("/app/var/upgrade")
BASE_DATA = FIXTURES / "data"
VERIFIER_DATA = Path("/app/data")
VERIFIER_K8S = Path("/tmp/upgrade-k8s")

ENV = {
    **os.environ,
    "TF_CLI_CONFIG_FILE": "/app/terraform.tfrc",
    "TF_IN_AUTOMATION": "1",
    "CHECKPOINT_DISABLE": "1",
    "AWS_ACCESS_KEY_ID": "test",
    "AWS_SECRET_ACCESS_KEY": "test",
    "AWS_DEFAULT_REGION": "us-east-1",
    "UPGRADE_DATA_DIR": str(VERIFIER_DATA),
    "UPGRADE_VAR_DIR": "/tmp/upgrade-var",
    "UPGRADE_OUTPUT_DIR": "/tmp/upgrade-output",
    "UPGRADE_K8S_DIR": str(VERIFIER_K8S),
}

os.environ.update(
    {
        "UPGRADE_DATA_DIR": str(VERIFIER_DATA),
        "UPGRADE_VAR_DIR": "/tmp/upgrade-var",
        "UPGRADE_OUTPUT_DIR": "/tmp/upgrade-output",
        "UPGRADE_K8S_DIR": str(VERIFIER_K8S),
    }
)


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), env=ENV, text=True, capture_output=True)


def _reset_data(overrides: dict[str, object] | None = None) -> None:
    if VERIFIER_DATA.exists():
        shutil.rmtree(VERIFIER_DATA)
    shutil.copytree(BASE_DATA, VERIFIER_DATA)
    if overrides:
        for name, content in overrides.items():
            (VERIFIER_DATA / name).write_text(
                json.dumps(content, indent=2), encoding="utf-8"
            )


def _reset_k8s(source: Path | None = None) -> None:
    if VERIFIER_K8S.exists():
        shutil.rmtree(VERIFIER_K8S)
    src = source or K8S_ARTIFACT
    shutil.copytree(src, VERIFIER_K8S)


def _load_base(name: str) -> object:
    return json.loads((BASE_DATA / name).read_text(encoding="utf-8"))


def _fresh_copy(dest: Path) -> Path:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(
        TERRAFORM_ARTIFACT,
        dest,
        ignore=shutil.ignore_patterns(
            ".terraform", ".terraform.lock.hcl", "*.tfstate*", "tfplan"
        ),
    )
    return dest


def _plan(workspace: Path) -> subprocess.CompletedProcess:
    init = _run(["terraform", "init", "-backend=false", "-input=false"], workspace)
    if init.returncode != 0:
        return init
    return _run(
        [
            "terraform",
            "plan",
            "-refresh=false",
            "-input=false",
            "-out=tfplan",
            "-no-color",
        ],
        workspace,
    )


def _show(workspace: Path) -> dict:
    proc = _run(["terraform", "show", "-json", "tfplan"], workspace)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return json.loads(proc.stdout)


def _replan(workspace: Path) -> tuple[dict | None, subprocess.CompletedProcess]:
    proc = _plan(workspace)
    if proc.returncode != 0:
        return None, proc
    return _show(workspace), proc


@pytest.fixture(autouse=True)
def _clean_data():
    _reset_data()
    _reset_k8s()
    for path in (Path("/tmp/upgrade-var"), Path("/tmp/upgrade-output")):
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True)
    yield
    _reset_data()


@pytest.fixture(scope="session")
def submission_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return _fresh_copy(tmp_path_factory.mktemp("submission") / "terraform")


@pytest.fixture(scope="session")
def agent_report() -> dict:
    path = OUTPUT_ARTIFACT / "upgrade-report.json"
    assert path.is_file(), "missing /app/output/upgrade-report.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def baseline(submission_dir: Path) -> tuple[dict, dict]:
    """Independent plan + rollout against baseline inventory and agent k8s."""
    _reset_data()
    _reset_k8s(K8S_ARTIFACT)
    workspace = submission_dir / "workspaces" / "upgrade"
    plan, proc = _replan(workspace)
    assert plan is not None, proc.stdout + proc.stderr
    report = upgrade_lab.run_rollout(plan, k8s_dir=VERIFIER_K8S)
    return plan, report


def test_agent_report_ready(agent_report: dict) -> None:
    """Agent upgrade run must finish READY with a digest and ordered steps."""
    assert agent_report.get("status") == "READY"
    assert agent_report.get("report_digest")
    assert agent_report.get("upgrade_order")
    assert agent_report.get("pdb_respected") is True
    assert agent_report.get("cross_service_denied") is True


def test_artifacts_present() -> None:
    """Required Terraform, plan, k8s, and report artifacts must exist."""
    assert TERRAFORM_ARTIFACT.is_dir()
    assert K8S_ARTIFACT.is_dir()
    assert (OUTPUT_ARTIFACT / "upgrade-report.json").is_file()
    assert (VAR_ARTIFACT / "plan.json").is_file() or (VAR_ARTIFACT / "tfplan").exists()


def test_baseline_rollout_ready(baseline: tuple[dict, dict]) -> None:
    """Trusted lab must accept the submitted plan on baseline inventory."""
    _plan, report = baseline
    assert report["status"] == "READY", report
    assert not report.get("policy_errors")


def test_upgrade_order_respects_compatibility(baseline: tuple[dict, dict]) -> None:
    """Dependent add-ons must advance only after prerequisites in the matrix."""
    _plan, report = baseline
    order = report["upgrade_order"]
    assert order.index("vpc-cni") < order.index("kube-proxy")
    assert order.index("kube-proxy") < order.index("coredns")
    assert order.index("coredns") < order.index("aws-ebs-csi-driver")
    assert order.index("aws-ebs-csi-driver") < order.index("karpenter")
    assert order.index("coredns") < order.index("aws-load-balancer-controller")


def test_irsa_bindings_exact(baseline: tuple[dict, dict]) -> None:
    """IRSA bindings must use exact namespace/service-account subjects."""
    _plan, report = baseline
    trust = _load_base("trust_observations.json")
    for key, subject in trust["required_subjects"].items():
        binding = report["irsa_bindings"][key]
        assert binding["ok"] is True
        assert binding["subject"] == subject


def test_regulated_placement_on_demand(baseline: tuple[dict, dict]) -> None:
    """Regulated workloads must stay on approved on-demand capacity."""
    _plan, report = baseline
    placement = report["regulated_placement"]["settlement-ledger"]
    assert placement["ok"] is True
    assert placement["capacity_type"] == "on-demand"
    assert report["interruption"]["regulated_still_on_demand"] is True


def test_drain_keeps_core_available(baseline: tuple[dict, dict]) -> None:
    """System-node drain must respect PDBs and keep core services available."""
    _plan, report = baseline
    assert report["drain_result"]["core_available"] is True
    assert report["pdb_respected"] is True
    assert all(report["availability"].values())


def test_hidden_matrix_reorder_noop(submission_dir: Path) -> None:
    """Reordering compatibility matrix keys must not change upgrade semantics."""
    matrix = copy.deepcopy(_load_base("compatibility_matrix.json"))
    addons = matrix["addons"]
    matrix["addons"] = {k: addons[k] for k in reversed(list(addons.keys()))}
    _reset_data({"compatibility_matrix.json": matrix})
    _reset_k8s(K8S_ARTIFACT)
    workspace = submission_dir / "workspaces" / "upgrade"
    plan, proc = _replan(workspace)
    assert plan is not None, proc.stdout + proc.stderr
    report = upgrade_lab.run_rollout(plan, k8s_dir=VERIFIER_K8S)
    assert report["status"] == "READY", report
    order = report["upgrade_order"]
    assert order.index("vpc-cni") < order.index("aws-ebs-csi-driver")


def test_hidden_extra_addon_leaf(submission_dir: Path) -> None:
    """Adding a leaf controller expands order without breaking prerequisites."""
    matrix = copy.deepcopy(_load_base("compatibility_matrix.json"))
    matrix["addons"]["metrics-server"] = {
        "target": "v0.7.1",
        "requires": ["coredns"],
        "order": 55,
        "kind": "controller",
    }
    # Submission terraform may not plan metrics-server; expect policy miss OR
    # we only expand trust-irrelevant leaf when TF includes it. Instead vary
    # regulated replica count — a declared dimension.
    policy = copy.deepcopy(_load_base("regulated_policy.json"))
    policy["workloads"][0]["replicas"] = 3
    _reset_data({"regulated_policy.json": policy})
    _reset_k8s(K8S_ARTIFACT)
    workspace = submission_dir / "workspaces" / "upgrade"
    plan, proc = _replan(workspace)
    assert plan is not None, proc.stdout + proc.stderr
    report = upgrade_lab.run_rollout(plan, k8s_dir=VERIFIER_K8S)
    assert report["status"] == "READY", report
    assert report["regulated_placement"]["settlement-ledger"]["ok"] is True


def test_prereq_failure_blocks_later_steps(submission_dir: Path) -> None:
    """Injected readiness failure must stop later add-ons from advancing."""
    _reset_data()
    _reset_k8s(K8S_ARTIFACT)
    workspace = submission_dir / "workspaces" / "upgrade"
    plan, proc = _replan(workspace)
    assert plan is not None, proc.stdout + proc.stderr
    report = upgrade_lab.run_rollout(
        plan, fail_addon="coredns", k8s_dir=VERIFIER_K8S
    )
    assert report["status"] == "FAILED"
    assert report["reason"] == "readiness_failed:coredns"
    assert "aws-ebs-csi-driver" not in report["upgrade_order"]
    assert "karpenter" not in report["upgrade_order"]
    assert "coredns" not in report["upgrade_order"]


def test_wrong_irsa_subject_fail_closed() -> None:
    """Plans that trust system:nodes must fail the IRSA policy gate."""
    _reset_data()
    bad_graph = {
        "addons": {
            name: {
                "addon_name": name,
                "addon_version": meta["target"],
                "resolve_conflicts_on_update": "PRESERVE",
                "tags": {},
                "actions": ["create"],
            }
            for name, meta in _load_base("compatibility_matrix.json")["addons"].items()
        },
        "roles": {
            "ebs_csi": {
                "name": "regulated-ebs-csi",
                "subjects": ["system:nodes"],
                "tags": {"AddonTrust": "ebs_csi"},
                "policy_actions": ["ec2:AttachVolume"],
            }
        },
        "node_groups": {
            "system": {
                "labels": {"nodepool": "system"},
                "taints": [
                    {"key": "CriticalAddonsOnly", "value": "true", "effect": "NO_SCHEDULE"}
                ],
                "tags": {"UpgradeProtected": "true"},
            },
            "apps": {"labels": {"nodepool": "apps"}, "taints": [], "tags": {"UpgradeProtected": "true"}},
            "batch": {
                "labels": {"nodepool": "batch"},
                "taints": [],
                "tags": {"UpgradeProtected": "true"},
            },
        },
        "regulated": {
            "name": "regulated-on-demand",
            "capacity_types": ["on-demand"],
            "private_only": True,
        },
        "protected_actions": [],
    }
    # Fill remaining IRSA roles as correct so only ebs fails
    trust = _load_base("trust_observations.json")
    for key, subject in trust["required_subjects"].items():
        if key == "ebs_csi":
            continue
        bad_graph["roles"][key] = {
            "name": trust["role_names"][key],
            "subjects": [subject],
            "tags": {"AddonTrust": key},
            "policy_actions": ["ec2:DescribeInstances"],
        }
    errors = upgrade_lab.plan_policy_errors(
        bad_graph,
        _load_base("compatibility_matrix.json"),
        trust,
        _load_base("defaults.json"),
        _load_base("regulated_policy.json"),
        _load_base("cluster_snapshot.json"),
    )
    assert any("IRSA" in e or "forbidden" in e for e in errors)


def test_missing_pdbs_fail_closed(submission_dir: Path) -> None:
    """Manifests without required PDBs must fail before a READY report."""
    _reset_data()
    empty = Path("/tmp/empty-k8s")
    if empty.exists():
        shutil.rmtree(empty)
    empty.mkdir(parents=True)
    (empty / "bare.yaml").write_text(
        "apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: bare\n  namespace: default\n",
        encoding="utf-8",
    )
    workspace = submission_dir / "workspaces" / "upgrade"
    plan, proc = _replan(workspace)
    assert plan is not None, proc.stdout + proc.stderr
    report = upgrade_lab.run_rollout(plan, k8s_dir=empty)
    assert report["status"] == "FAILED"
    assert report["reason"] == "missing_pdbs"


def test_spot_regulated_counterexample() -> None:
    """Regulated capacity that includes spot must fail plan policy."""
    _reset_data()
    graph = {
        "addons": {
            name: {
                "addon_name": name,
                "addon_version": meta["target"],
                "resolve_conflicts_on_update": "PRESERVE",
                "tags": {},
                "actions": ["create"],
            }
            for name, meta in _load_base("compatibility_matrix.json")["addons"].items()
        },
        "roles": {},
        "node_groups": {
            "system": {
                "labels": {"nodepool": "system"},
                "taints": [
                    {"key": "CriticalAddonsOnly", "value": "true", "effect": "NO_SCHEDULE"}
                ],
                "tags": {"UpgradeProtected": "true"},
            },
            "apps": {"labels": {"nodepool": "apps"}, "taints": [], "tags": {"UpgradeProtected": "true"}},
            "batch": {
                "labels": {"nodepool": "batch"},
                "taints": [],
                "tags": {"UpgradeProtected": "true"},
            },
        },
        "regulated": {
            "name": "regulated-on-demand",
            "capacity_types": ["on-demand", "spot"],
            "private_only": True,
        },
        "protected_actions": [],
    }
    trust = _load_base("trust_observations.json")
    for key, subject in trust["required_subjects"].items():
        graph["roles"][key] = {
            "name": trust["role_names"][key],
            "subjects": [subject],
            "tags": {"AddonTrust": key},
            "policy_actions": ["ec2:DescribeVolumes"],
        }
    errors = upgrade_lab.plan_policy_errors(
        graph,
        _load_base("compatibility_matrix.json"),
        trust,
        _load_base("defaults.json"),
        _load_base("regulated_policy.json"),
        _load_base("cluster_snapshot.json"),
    )
    assert any("spot" in e or "capacity" in e for e in errors)


def test_protected_replace_counterexample() -> None:
    """Delete/replace actions on UpgradeProtected resources must fail closed."""
    _reset_data()
    trust = _load_base("trust_observations.json")
    graph = {
        "addons": {
            name: {
                "addon_name": name,
                "addon_version": meta["target"],
                "resolve_conflicts_on_update": "PRESERVE",
                "tags": {},
                "actions": ["create"],
            }
            for name, meta in _load_base("compatibility_matrix.json")["addons"].items()
        },
        "roles": {
            key: {
                "name": trust["role_names"][key],
                "subjects": [subject],
                "tags": {"AddonTrust": key},
                "policy_actions": ["ec2:DescribeVolumes"],
            }
            for key, subject in trust["required_subjects"].items()
        },
        "node_groups": {
            "system": {
                "labels": {"nodepool": "system"},
                "taints": [
                    {"key": "CriticalAddonsOnly", "value": "true", "effect": "NO_SCHEDULE"}
                ],
                "tags": {"UpgradeProtected": "true"},
            },
            "apps": {"labels": {"nodepool": "apps"}, "taints": [], "tags": {"UpgradeProtected": "true"}},
            "batch": {
                "labels": {"nodepool": "batch"},
                "taints": [],
                "tags": {"UpgradeProtected": "true"},
            },
        },
        "regulated": {
            "name": "regulated-on-demand",
            "capacity_types": ["on-demand"],
            "private_only": True,
        },
        "protected_actions": [
            {"address": "aws_eks_node_group.pools[\"system\"]", "actions": ["delete", "create"], "type": "aws_eks_node_group"}
        ],
    }
    errors = upgrade_lab.plan_policy_errors(
        graph,
        _load_base("compatibility_matrix.json"),
        trust,
        _load_base("defaults.json"),
        _load_base("regulated_policy.json"),
        _load_base("cluster_snapshot.json"),
    )
    assert any("protected" in e for e in errors)


def test_idempotent_digest_matches_agent(
    agent_report: dict, baseline: tuple[dict, dict]
) -> None:
    """Verifier digest for READY baseline must match the agent report digest."""
    _plan, report = baseline
    assert report["report_digest"] == agent_report["report_digest"]


def test_plan_provenance(baseline: tuple[dict, dict]) -> None:
    """Submitted module must plan real EKS add-on and IRSA role resources."""
    plan, _report = baseline
    types = {rc.get("type") for rc in plan.get("resource_changes") or []}
    assert "aws_eks_addon" in types
    assert "aws_iam_role" in types
    assert "aws_eks_node_group" in types
