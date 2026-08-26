"""Verifier for the EKS add-on trust rollout lab.

Replans submitted Terraform with trusted inventories, applies submitted
Kubernetes manifests through the upgrade lab, and checks READY status,
compatibility order, IRSA bindings, PDB-respecting drains, regulated
placement, fail-closed partial progress, and idempotent digests.
"""
from __future__ import annotations

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


def _graph(plan: dict) -> dict:
    return upgrade_lab.normalize_plan(plan)


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


def test_f2p_plan_policy_enforces_required_addons(baseline: tuple[dict, dict]) -> None:
    """Submitted plan must include every add-on named in the compatibility matrix."""
    plan, report = baseline
    assert report["status"] == "READY", report
    graph = _graph(plan)
    matrix = _load_base("compatibility_matrix.json")
    for name in matrix["addons"]:
        assert name in graph["addons"], f"missing addon {name}"


def test_f2p_addon_versions_match_compatibility_matrix(
    baseline: tuple[dict, dict],
) -> None:
    """Each planned add-on version must equal the matrix target."""
    plan, report = baseline
    assert report["status"] == "READY", report
    graph = _graph(plan)
    matrix = _load_base("compatibility_matrix.json")
    for name, meta in matrix["addons"].items():
        assert graph["addons"][name]["addon_version"] == meta["target"]


def test_f2p_resolve_conflicts_must_be_preserve(baseline: tuple[dict, dict]) -> None:
    """EKS add-ons must plan resolve_conflicts_on_update=PRESERVE."""
    plan, report = baseline
    assert report["status"] == "READY", report
    graph = _graph(plan)
    matrix = _load_base("compatibility_matrix.json")
    defaults = _load_base("defaults.json")
    for name, meta in matrix["addons"].items():
        if meta.get("kind") != "eks_addon":
            continue
        assert (
            graph["addons"][name]["resolve_conflicts_on_update"]
            == defaults["resolve_conflicts_on_update"]
        )


def test_f2p_ssm_parameter_tags_supply_controller_versions(
    baseline: tuple[dict, dict],
) -> None:
    """Controller add-ons must be represented via SSM tags with version and conflict mode."""
    plan, report = baseline
    assert report["status"] == "READY", report
    graph = _graph(plan)
    matrix = _load_base("compatibility_matrix.json")
    for name, meta in matrix["addons"].items():
        if meta.get("kind") != "controller":
            continue
        planned = graph["addons"][name]
        assert planned["addon_version"] == meta["target"]
        assert planned["tags"].get("ControllerAddon") == name
        assert planned["tags"].get("AddonVersion") == meta["target"]
        assert planned["tags"].get("ResolveConflicts") == "PRESERVE"


def test_f2p_irsa_assume_role_policy_condition_parsing(
    baseline: tuple[dict, dict],
) -> None:
    """Assume-role policy documents must parse into concrete service-account subjects."""
    plan, report = baseline
    assert report["status"] == "READY", report
    graph = _graph(plan)
    for role in graph["roles"].values():
        if role["tags"].get("AddonTrust"):
            assert role["subjects"], f"unparsed subjects for {role.get('name')}"


def test_f2p_irsa_role_trusts_exact_single_service_account(
    baseline: tuple[dict, dict],
) -> None:
    """Each IRSA role must trust exactly one required service-account subject."""
    _plan, report = baseline
    assert report["status"] == "READY", report
    trust = _load_base("trust_observations.json")
    for key, subject in trust["required_subjects"].items():
        binding = report["irsa_bindings"][key]
        assert binding["ok"] is True
        assert binding["subject"] == subject


def test_f2p_forbidden_subjects_like_system_nodes_rejected(
    baseline: tuple[dict, dict],
) -> None:
    """Submitted IRSA roles must not trust forbidden subjects such as system:nodes."""
    plan, report = baseline
    assert report["status"] == "READY", report
    graph = _graph(plan)
    forbidden = set(_load_base("trust_observations.json")["forbidden_subjects"])
    for role in graph["roles"].values():
        if not role["tags"].get("AddonTrust"):
            continue
        assert not (set(role["subjects"]) & forbidden)


def test_f2p_wildcard_iam_policy_actions_rejected(baseline: tuple[dict, dict]) -> None:
    """IRSA inline policies must reject wildcard and admin-style actions."""
    plan, report = baseline
    assert report["status"] == "READY", report
    graph = _graph(plan)
    forbidden = set(_load_base("defaults.json")["forbidden_policy_actions"])
    for role in graph["roles"].values():
        if not role["tags"].get("AddonTrust"):
            continue
        for act in role.get("policy_actions") or []:
            assert act not in forbidden
            if role["tags"].get("AddonTrust") == "ebs_csi":
                assert not str(act).endswith(":*")


def test_f2p_irsa_role_names_match_expected_naming(baseline: tuple[dict, dict]) -> None:
    """IRSA role names must match the naming contract in trust observations."""
    plan, report = baseline
    assert report["status"] == "READY", report
    graph = _graph(plan)
    trust = _load_base("trust_observations.json")
    by_trust = {
        role["tags"].get("AddonTrust"): role
        for role in graph["roles"].values()
        if role["tags"].get("AddonTrust")
    }
    for key, expected in trust["role_names"].items():
        assert by_trust[key]["name"] == expected


def test_f2p_pdbs_match_required_names_namespaces_selectors(
    baseline: tuple[dict, dict],
) -> None:
    """Submitted manifests must supply PDBs with required names and namespaces."""
    _plan, report = baseline
    assert report["status"] == "READY", report
    state = upgrade_lab.apply_k8s_manifests(VERIFIER_K8S)
    required = _load_base("pdbs.json")["required"]
    have = {(p["namespace"], p["name"]): p for p in state["pdbs"]}
    for req in required:
        assert (req["namespace"], req["name"]) in have


def test_f2p_pdb_min_available_thresholds_enforced(baseline: tuple[dict, dict]) -> None:
    """PDB minAvailable values must match the required disruption budgets."""
    _plan, report = baseline
    assert report["status"] == "READY", report
    state = upgrade_lab.apply_k8s_manifests(VERIFIER_K8S)
    required = _load_base("pdbs.json")["required"]
    have = {(p["namespace"], p["name"]): p for p in state["pdbs"]}
    for req in required:
        got = have[(req["namespace"], req["name"])]
        assert got["min_available"] == req["min_available"]


def test_f2p_system_node_group_taints_and_labels_validated(
    baseline: tuple[dict, dict],
) -> None:
    """System node group must carry CriticalAddonsOnly taint and nodepool label."""
    plan, report = baseline
    assert report["status"] == "READY", report
    graph = _graph(plan)
    system = graph["node_groups"]["system"]
    defaults = _load_base("defaults.json")
    taint_cfg = defaults["system_taint"]
    found = False
    for t in system.get("taints") or []:
        if (
            t.get("key") == taint_cfg["key"]
            and str(t.get("value")) == str(taint_cfg["value"])
        ):
            found = True
    assert found
    assert system["labels"].get("nodepool") == "system"


def test_f2p_drain_simulation_respects_pdb_availability(
    baseline: tuple[dict, dict],
) -> None:
    """System-node drain must respect PDBs and keep core services available."""
    _plan, report = baseline
    assert report["status"] == "READY", report
    assert report["drain_result"]["core_available"] is True
    assert report["pdb_respected"] is True
    assert all(report["availability"].values())


def test_f2p_system_node_group_labels_verified(baseline: tuple[dict, dict]) -> None:
    """System and companion node groups must keep UpgradeProtected labels."""
    plan, report = baseline
    assert report["status"] == "READY", report
    graph = _graph(plan)
    for pool in ("system", "apps", "batch"):
        assert graph["node_groups"][pool]["tags"].get("UpgradeProtected") == "true"
        assert graph["node_groups"][pool]["labels"].get("nodepool") == pool


def test_f2p_regulated_workloads_require_explicit_nodepools(
    baseline: tuple[dict, dict],
) -> None:
    """Regulated workloads must declare an explicit approved nodepool selector."""
    _plan, report = baseline
    assert report["status"] == "READY", report
    for _name, placement in report["regulated_placement"].items():
        assert placement["ok"] is True
        assert placement["nodepool"] == "regulated-on-demand"


def test_f2p_regulated_capacity_types_enforce_ondemand(
    baseline: tuple[dict, dict],
) -> None:
    """Regulated placement must enforce on-demand capacity only."""
    plan, report = baseline
    assert report["status"] == "READY", report
    graph = _graph(plan)
    assert set(graph["regulated"]["capacity_types"]) == {"on-demand"}
    for placement in report["regulated_placement"].values():
        assert placement["capacity_type"] == "on-demand"


def test_f2p_regulated_node_pools_restricted_to_private_subnets(
    baseline: tuple[dict, dict],
) -> None:
    """Regulated node pool fencing must require private-subnet-only placement."""
    plan, report = baseline
    assert report["status"] == "READY", report
    graph = _graph(plan)
    assert graph["regulated"]["private_only"] is True


def test_f2p_karpenter_nodepool_crd_capacity_enforced(
    baseline: tuple[dict, dict],
) -> None:
    """Karpenter NodePool CRD must allow only on-demand capacity types."""
    _plan, report = baseline
    assert report["status"] == "READY", report
    state = upgrade_lab.apply_k8s_manifests(VERIFIER_K8S)
    found = False
    for np in state["nodepools"]:
        if (np.get("metadata") or {}).get("name") != "regulated-on-demand":
            continue
        if np.get("kind") != "NodePool":
            continue
        reqs = (
            ((np.get("spec") or {}).get("template") or {}).get("spec") or {}
        ).get("requirements") or []
        for req in reqs:
            if req.get("key") == "karpenter.sh/capacity-type":
                assert list(req.get("values") or []) == ["on-demand"]
                found = True
    assert found


def test_f2p_interruption_simulation_preserves_ondemand(
    baseline: tuple[dict, dict],
) -> None:
    """Interruption handling must keep regulated workloads on on-demand capacity."""
    _plan, report = baseline
    assert report["status"] == "READY", report
    assert report["interruption"]["handled"] is True
    assert report["interruption"]["regulated_still_on_demand"] is True


def test_f2p_rollout_prerequisites_validated_before_step(
    submission_dir: Path, baseline: tuple[dict, dict]
) -> None:
    """Injected readiness failure must stop later add-ons from advancing."""
    _plan, ready_report = baseline
    assert ready_report["status"] == "READY"
    _reset_data()
    _reset_k8s(K8S_ARTIFACT)
    workspace = submission_dir / "workspaces" / "upgrade"
    plan, proc = _replan(workspace)
    assert plan is not None, proc.stdout + proc.stderr
    report = upgrade_lab.run_rollout(plan, fail_addon="coredns", k8s_dir=VERIFIER_K8S)
    assert report["status"] == "FAILED"
    assert report["reason"] == "readiness_failed:coredns"
    assert "aws-ebs-csi-driver" not in report["upgrade_order"]
    assert "karpenter" not in report["upgrade_order"]
    assert "coredns" not in report["upgrade_order"]


def test_f2p_addons_rollout_in_matrix_specified_order(
    baseline: tuple[dict, dict],
) -> None:
    """Dependent add-ons must advance only after prerequisites in the matrix."""
    _plan, report = baseline
    assert report["status"] == "READY", report
    order = report["upgrade_order"]
    assert order.index("vpc-cni") < order.index("kube-proxy")
    assert order.index("kube-proxy") < order.index("coredns")
    assert order.index("coredns") < order.index("aws-ebs-csi-driver")
    assert order.index("aws-ebs-csi-driver") < order.index("karpenter")
    assert order.index("coredns") < order.index("aws-load-balancer-controller")


def test_f2p_addon_readiness_verified_before_step_completion(
    baseline: tuple[dict, dict],
) -> None:
    """Every completed rollout step must record ok=true with target versions."""
    _plan, report = baseline
    assert report["status"] == "READY", report
    assert report["steps"]
    assert all(step.get("ok") is True for step in report["steps"])
    matrix = _load_base("compatibility_matrix.json")
    for step in report["steps"]:
        assert step["to_version"] == matrix["addons"][step["addon"]]["target"]


def test_f2p_cross_service_trust_denies_shared_role_arns(
    baseline: tuple[dict, dict],
) -> None:
    """Distinct add-ons must not share IRSA role ARNs."""
    _plan, report = baseline
    assert report["status"] == "READY", report
    assert report["cross_service_denied"] is True
    arns = [v.get("role_arn") for v in report["irsa_bindings"].values()]
    assert len(arns) == len(set(arns)) == len(report["irsa_bindings"])


def test_f2p_plan_normalizer_merges_inline_and_attached_policies(
    baseline: tuple[dict, dict],
) -> None:
    """Plan normalization must surface non-empty merged IAM policy actions per IRSA role."""
    plan, report = baseline
    assert report["status"] == "READY", report
    graph = _graph(plan)
    trust_keys = set(_load_base("trust_observations.json")["required_subjects"])
    found = 0
    for role in graph["roles"].values():
        key = role["tags"].get("AddonTrust")
        if key in trust_keys:
            assert role.get("policy_actions")
            found += 1
    assert found == len(trust_keys)


def test_f2p_upgrade_protected_resources_guarded_against_deletion(
    baseline: tuple[dict, dict],
) -> None:
    """UpgradeProtected resources must not appear as delete/replace actions."""
    plan, report = baseline
    assert report["status"] == "READY", report
    graph = _graph(plan)
    assert graph["protected_actions"] == []
    for role in graph["roles"].values():
        if role["tags"].get("AddonTrust"):
            assert role["tags"].get("UpgradeProtected") == "true"


def test_f2p_rollout_state_checkpointing_enables_restart(
    submission_dir: Path, baseline: tuple[dict, dict]
) -> None:
    """Interrupted rollouts must leave a checkpoint that resumes without redoing finished steps."""
    _plan, ready_report = baseline
    assert ready_report["status"] == "READY"
    _reset_data()
    _reset_k8s(K8S_ARTIFACT)
    for path in (Path("/tmp/upgrade-var"), Path("/tmp/upgrade-output")):
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True)
    workspace = submission_dir / "workspaces" / "upgrade"
    plan, proc = _replan(workspace)
    assert plan is not None, proc.stdout + proc.stderr
    failed = upgrade_lab.run_rollout(plan, fail_addon="coredns", k8s_dir=VERIFIER_K8S)
    assert failed["status"] == "FAILED"
    ckpt = Path("/tmp/upgrade-var/checkpoint.json")
    assert ckpt.is_file()
    prior = json.loads(ckpt.read_text(encoding="utf-8"))
    assert "vpc-cni" in prior.get("ready") or "vpc-cni" in prior.get("upgrade_order")
    resumed = upgrade_lab.run_rollout(plan, k8s_dir=VERIFIER_K8S)
    assert resumed["status"] == "READY", resumed
    assert not ckpt.is_file()
    assert resumed["upgrade_order"].index("vpc-cni") < resumed["upgrade_order"].index(
        "coredns"
    )


def test_f2p_report_formatting_is_canonical_and_complete(
    agent_report: dict, baseline: tuple[dict, dict]
) -> None:
    """Upgrade reports must include the full documented schema with stable fields."""
    _plan, report = baseline
    assert report["status"] == "READY", report
    assert agent_report["status"] == "READY"
    required = {
        "status",
        "reason",
        "policy_errors",
        "upgrade_order",
        "steps",
        "availability",
        "pdb_respected",
        "drain_result",
        "irsa_bindings",
        "cross_service_denied",
        "regulated_placement",
        "interruption",
        "report_digest",
    }
    assert required.issubset(report.keys())
    assert required.issubset(agent_report.keys())


def test_f2p_report_digest_computed_over_stable_fields(
    agent_report: dict, baseline: tuple[dict, dict]
) -> None:
    """Report digests must be SHA-256 over the stable semantic subset."""
    _plan, report = baseline
    assert report["status"] == "READY", report
    assert len(report["report_digest"]) == 64
    assert int(report["report_digest"], 16) >= 0
    assert report["report_digest"] == agent_report["report_digest"]


def test_f2p_readiness_status_ready_when_all_checks_pass(
    agent_report: dict, baseline: tuple[dict, dict]
) -> None:
    """Agent and verifier rollouts must both publish READY when all gates pass."""
    _plan, report = baseline
    assert report["status"] == "READY", report
    assert agent_report["status"] == "READY"
    assert not report.get("policy_errors")
    assert report.get("pdb_respected") is True
    assert report.get("cross_service_denied") is True


def test_f2p_identical_runs_produce_identical_digests(
    submission_dir: Path, baseline: tuple[dict, dict]
) -> None:
    """Two clean verifier rollouts with the same inputs must share one digest."""
    _plan, first = baseline
    assert first["status"] == "READY"
    _reset_data()
    _reset_k8s(K8S_ARTIFACT)
    for path in (Path("/tmp/upgrade-var"), Path("/tmp/upgrade-output")):
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True)
    workspace = submission_dir / "workspaces" / "upgrade"
    plan, proc = _replan(workspace)
    assert plan is not None, proc.stdout + proc.stderr
    second = upgrade_lab.run_rollout(plan, k8s_dir=VERIFIER_K8S)
    assert second["status"] == "READY"
    assert first["report_digest"] == second["report_digest"]


def test_p2p_cli_entrypoint_and_api_signatures_compatible() -> None:
    """Public CLI entrypoint and lab API surface remain importable offline."""
    assert callable(upgrade_lab.run_rollout)
    assert callable(upgrade_lab.plan_policy_errors)
    assert callable(upgrade_lab.normalize_plan)


def test_p2p_report_schema_and_plan_paths_preserved() -> None:
    """Documented plan and report artifact paths remain the grading contract."""
    assert str(OUTPUT_ARTIFACT) == "/app/output"
    assert str(VAR_ARTIFACT) == "/app/var/upgrade"
    schema_keys = {
        "status",
        "reason",
        "policy_errors",
        "upgrade_order",
        "steps",
        "availability",
        "pdb_respected",
        "drain_result",
        "irsa_bindings",
        "cross_service_denied",
        "regulated_placement",
        "interruption",
        "report_digest",
    }
    assert "status" in schema_keys


def test_p2p_offline_lab_execution_requires_no_external_aws() -> None:
    """Lab policy evaluation must run from local fixtures without live AWS."""
    _reset_data()
    trust = _load_base("trust_observations.json")
    errors = upgrade_lab.plan_policy_errors(
        {
            "addons": {},
            "roles": {},
            "node_groups": {},
            "regulated": {},
            "protected_actions": [],
        },
        _load_base("compatibility_matrix.json"),
        trust,
        _load_base("defaults.json"),
        _load_base("regulated_policy.json"),
        _load_base("cluster_snapshot.json"),
    )
    assert isinstance(errors, list)
    assert errors


def test_p2p_policy_violations_fail_closed_without_corruption() -> None:
    """Unsafe plans must fail closed with plan_policy reason and no READY status."""
    _reset_data()
    _reset_k8s(K8S_ARTIFACT)
    bad_plan = {"resource_changes": [], "format_version": "1.2"}
    report = upgrade_lab.run_rollout(bad_plan, k8s_dir=VERIFIER_K8S)
    assert report["status"] == "FAILED"
    assert report["reason"] == "plan_policy"
    assert report.get("policy_errors")
    assert report["upgrade_order"] == []
