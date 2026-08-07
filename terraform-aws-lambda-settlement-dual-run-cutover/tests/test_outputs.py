"""Verifier for Lambda settlement dual-run cutover.

Replans submitted Terraform, rebuilds settlementctl against a verifier-owned
sealed runtime, and checks generation pinning, exactly-once effects, poison
DLQ isolation, Jenkins shadow read-only behavior, restart/reconcile, hidden
batch variants, and anti-cheat mismatches.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"
INTERNAL = Path("/app/internal")
TERRAFORM = Path("/app/terraform")
CMD = Path("/app/cmd")
OUTPUT = Path("/app/output")
VAR = Path("/app/var/settlement")
BIN = Path("/app/bin/settlement-dual-run")
GO_MOD = Path("/app/go.mod")
WORKSPACE = TERRAFORM / "workspaces" / "settlement"
RUNTIME = Path("/opt/settlement-runtime")
EXPECTED_HASH = Path("/opt/settlement-runtime.sha256")

ENV = {
    **os.environ,
    "TF_CLI_CONFIG_FILE": "/app/terraform.tfrc",
    "TF_IN_AUTOMATION": "1",
    "CHECKPOINT_DISABLE": "1",
    "AWS_ACCESS_KEY_ID": "test",
    "AWS_SECRET_ACCESS_KEY": "test",
    "AWS_DEFAULT_REGION": "us-east-1",
}

STAGES = [
    "intake",
    "verify_manifest",
    "acquire_lock",
    "fetch_inputs",
    "validate_inputs",
    "transform_records",
    "precheck_ledger",
    "write_ledger",
    "build_report",
    "notify_partner",
    "archive_batch",
    "release_lock",
]


def _run(cmd, cwd=None, check=False, input_text=None):
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=ENV,
        text=True,
        capture_output=True,
        check=check,
        input=input_text,
    )


def _ensure_sources():
    assert INTERNAL.exists(), "internal artifact missing"
    assert TERRAFORM.exists(), "terraform artifact missing"
    assert (CMD / "settlementctl" / "main.go").exists(), "settlementctl source missing"
    assert GO_MOD.exists(), "go.mod missing"
    assert BIN.exists(), "operator binary missing"
    assert WORKSPACE.exists(), "settlement workspace missing"


def _verify_runtime_hash():
    digest = hashlib.sha256(RUNTIME.read_bytes()).hexdigest()
    expected = EXPECTED_HASH.read_text(encoding="utf-8").strip().split()[0]
    assert digest == expected, "sealed runtime hash mismatch"


def _reset_runtime():
    proc = _run([str(RUNTIME), "reset"])
    assert proc.returncode == 0, proc.stderr


def _runtime(args, stdin=None):
    payload = None if stdin is None else json.dumps(stdin)
    proc = _run([str(RUNTIME), *args], input_text=payload)
    assert proc.returncode == 0, proc.stderr or proc.stdout
    text = (proc.stdout or "").strip()
    if not text:
        return {}
    return json.loads(text.splitlines()[-1])


def _build_ctl():
    out = Path("/tmp/settlementctl-verifier")
    proc = _run(["go", "build", "-o", str(out), "./cmd/settlementctl"], cwd=Path("/app"))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return out


def _ctl(ctl, args, check=True):
    proc = _run([str(ctl), *args])
    data = {}
    text = (proc.stdout or "").strip()
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line.startswith("{") or line.startswith("["):
            data = json.loads(line)
            break
    if check:
        assert proc.returncode == 0, proc.stdout + proc.stderr
    return data, proc.returncode


def _reset_workspace():
    if VAR.exists():
        shutil.rmtree(VAR)
    VAR.mkdir(parents=True, exist_ok=True)
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for path in (Path("/app/data"), Path("/app/config")):
        if path.exists():
            shutil.rmtree(path)
    shutil.copytree(FIXTURES / "data", Path("/app/data"))
    shutil.copytree(FIXTURES / "config", Path("/app/config"))
    _reset_runtime()


def _load_stages():
    return json.loads((WORKSPACE / "stages.json").read_text(encoding="utf-8"))


def _write_stages(doc):
    (WORKSPACE / "stages.json").write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")


def _write_request(name: str, payload: dict) -> Path:
    path = VAR / name
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _base_request(**overrides):
    req = {
        "protocol_version": 2,
        "execution_id": "exec-verifier-001",
        "batch_id": "batch-verifier-001",
        "artifact_digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "owner": "lambda-pod-verifier",
        "items": [
            {"id": "item-a", "amount": 100, "tenant": "t1"},
            {"id": "item-b", "amount": 200, "tenant": "t1"},
        ],
        "metadata": {"source": "verifier", "partner": "bank-a"},
    }
    req.update(overrides)
    return req


def _effects():
    raw = _runtime(["inspect", "effects"])
    return raw if isinstance(raw, list) else []


def _effect_keys():
    return [e.get("logical_key") for e in _effects()]


def _unique_effect_counts():
    counts = {"ledger": 0, "report": 0, "notify": 0, "archive": 0}
    seen = set()
    for effect in _effects():
        key = effect.get("logical_key", "")
        if key in seen:
            continue
        seen.add(key)
        if "/ledger/" in key:
            counts["ledger"] += 1
        elif key.endswith("/report"):
            counts["report"] += 1
        elif key.endswith("/notify"):
            counts["notify"] += 1
        elif key.endswith("/archive"):
            counts["archive"] += 1
    return counts


def _plan_json():
    plan_path = VAR / "tfplan"
    _run(["terraform", "init", "-backend=false", "-input=false"], cwd=WORKSPACE, check=True)
    proc = _run(
        ["terraform", "plan", "-refresh=false", "-input=false", f"-out={plan_path}"],
        cwd=WORKSPACE,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    show = _run(["terraform", "show", "-json", str(plan_path)], cwd=WORKSPACE, check=True)
    return json.loads(show.stdout)


def _lambda_plan_graph(plan):
    functions = []
    aliases = []
    for change in plan.get("resource_changes") or []:
        values = (change.get("change") or {}).get("after") or {}
        if change.get("type") == "aws_lambda_function":
            functions.append(values)
        elif change.get("type") == "aws_lambda_alias":
            aliases.append(values)
    return functions, aliases


@pytest.fixture()
def ctl():
    _ensure_sources()
    _verify_runtime_hash()
    _reset_workspace()
    binary = _build_ctl()
    yield binary
    _reset_runtime()


def test_artifacts_and_runtime_integrity(ctl):
    """Submitted sources exist and the sealed runtime hash is intact."""
    assert (WORKSPACE / "main.tf").exists()
    assert (WORKSPACE / "stages.json").exists()
    assert (WORKSPACE / "deployment.json").exists()
    _verify_runtime_hash()


def test_public_operator_ready(ctl):
    """Public operator command produces READY cutover report with stable digest."""
    proc = _run([str(BIN)])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads((OUTPUT / "cutover-report.json").read_text(encoding="utf-8"))
    assert report["status"] == "READY"
    assert report["writer"] == "lambda"
    assert report["runtime_writer"] == "lambda"
    assert report["shadow_wrote"] is False
    assert report["plan_lambda_functions"] >= 12
    assert report["plan_lambda_aliases"] >= 12
    first = report["report_digest"]
    proc = _run([str(BIN)])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    second = json.loads((OUTPUT / "cutover-report.json").read_text(encoding="utf-8"))
    assert second["report_digest"] == first


def test_terraform_plan_has_live_stage_fleet(ctl):
    """Planned Lambda functions and live aliases cover all twelve stages."""
    plan = _plan_json()
    functions, aliases = _lambda_plan_graph(plan)
    names = sorted(f.get("function_name") for f in functions)
    assert names == sorted(f"settlement-pipeline-{s}" for s in STAGES)
    for fn in functions:
        assert fn.get("runtime") == "provided.al2023"
        assert fn.get("handler") == "bootstrap"
        assert fn.get("publish") is True
    assert len(aliases) >= 12
    assert all(a.get("name") == "live" for a in aliases)


def test_deploy_rejects_shared_package_and_wildcard(ctl):
    """Unsafe stage inventory is rejected before runtime registration."""
    doc = _load_stages()
    original = copy.deepcopy(doc)
    doc["stages"][0]["package_hash"] = doc["stages"][1]["package_hash"]
    _write_stages(doc)
    _, code = _ctl(ctl, ["deploy", "--infra", str(WORKSPACE)], check=False)
    assert code != 0
    _write_stages(original)
    doc = _load_stages()
    doc["stages"][5]["permissions"] = list(doc["stages"][5]["permissions"]) + ["*"]
    _write_stages(doc)
    _, code = _ctl(ctl, ["deploy", "--infra", str(WORKSPACE)], check=False)
    assert code != 0
    _write_stages(original)


def test_happy_path_exactly_once_effects(ctl):
    """A clean batch writes one ledger row per item and one batch effect each."""
    deploy, _ = _ctl(ctl, ["deploy", "--infra", str(WORKSPACE)])
    _ctl(ctl, ["cutover", "--generation", str(deploy["generation"]), "--writer", "lambda"])
    req = _base_request()
    path = _write_request("happy.json", req)
    cp, code = _ctl(ctl, ["run", "--request", str(path)], check=False)
    assert code == 0
    assert cp["status"] == "SUCCEEDED"
    assert cp["generation"] == deploy["generation"]
    counts = _unique_effect_counts()
    assert counts == {"ledger": 2, "report": 1, "notify": 1, "archive": 1}
    # Rerun completed execution is a no-op on effects.
    before = len(_effects())
    cp2, code = _ctl(ctl, ["run", "--request", str(path)], check=False)
    assert code == 0
    assert cp2["status"] == "SUCCEEDED"
    assert len(_effects()) == before


def test_transient_retry_and_lost_effect_idempotency(ctl):
    """Transient failures retry without duplicating committed external effects."""
    deploy, _ = _ctl(ctl, ["deploy", "--infra", str(WORKSPACE)])
    _ctl(ctl, ["cutover", "--generation", str(deploy["generation"]), "--writer", "lambda"])
    _runtime(["inject", "BEFORE_STAGE:intake", "2"])
    req = _base_request(execution_id="exec-retry-1", batch_id="batch-retry-1")
    path = _write_request("retry.json", req)
    cp, code = _ctl(ctl, ["run", "--request", str(path)], check=False)
    assert code == 0
    assert cp["status"] == "SUCCEEDED"
    assert cp.get("attempts", {}).get("intake", 0) >= 1
    _runtime(["clear-failures"])
    _runtime(["inject", "AFTER_EFFECT:write_ledger", "1"])
    req2 = _base_request(
        execution_id="exec-lost-1",
        batch_id="batch-lost-1",
        items=[{"id": "only", "amount": 1, "tenant": "t1"}],
    )
    path2 = _write_request("lost.json", req2)
    cp2, code = _ctl(ctl, ["run", "--request", str(path2)], check=False)
    if cp2.get("status") == "RETRY_PENDING":
        cp2, code = _ctl(ctl, ["resume", "--execution", "exec-lost-1"], check=False)
    assert code == 0
    assert cp2["status"] == "SUCCEEDED"
    keys = [k for k in _effect_keys() if k == "batch-lost-1/ledger/only"]
    assert len(keys) == 1


def test_poison_isolation_partial_batch(ctl):
    """Poison items go to DLQ after three validates while siblings finish."""
    deploy, _ = _ctl(ctl, ["deploy", "--infra", str(WORKSPACE)])
    _ctl(ctl, ["cutover", "--generation", str(deploy["generation"]), "--writer", "lambda"])
    req = _base_request(
        execution_id="exec-poison-1",
        batch_id="batch-poison-1",
        items=[
            {"id": "ok-1", "amount": 10, "tenant": "t1"},
            {"id": "bad-1", "amount": 11, "tenant": "t1", "poison": True},
            {"id": "ok-2", "amount": 12, "tenant": "t1"},
        ],
    )
    path = _write_request("poison.json", req)
    cp, code = _ctl(ctl, ["run", "--request", str(path)], check=False)
    assert code == 0
    assert cp["status"] == "PARTIAL"
    dlq = _runtime(["inspect", "dlq"])
    assert "bad-1" in dlq.get("batch-poison-1", [])
    keys = _effect_keys()
    assert "batch-poison-1/ledger/ok-1" in keys
    assert "batch-poison-1/ledger/ok-2" in keys
    assert "batch-poison-1/ledger/bad-1" not in keys
    assert "batch-poison-1/report" in keys
    attempts = cp.get("attempts", {})
    assert attempts.get("validate_inputs/bad-1", 0) == 3


def test_batch_lock_fencing_and_independent_batches(ctl):
    """One execution owns a batch; unrelated batches still complete."""
    deploy, _ = _ctl(ctl, ["deploy", "--infra", str(WORKSPACE)])
    _ctl(ctl, ["cutover", "--generation", str(deploy["generation"]), "--writer", "lambda"])
    req_a = _base_request(execution_id="exec-lock-a", batch_id="batch-lock-shared")
    path_a = _write_request("lock-a.json", req_a)
    # Force pause after acquire by exhausting retries on fetch_inputs.
    _runtime(["inject", "BEFORE_STAGE:fetch_inputs", "3"])
    cp_a, code = _ctl(ctl, ["run", "--request", str(path_a)], check=False)
    assert cp_a["status"] == "RETRY_PENDING"
    assert code != 0
    req_b = _base_request(
        execution_id="exec-lock-b",
        batch_id="batch-lock-shared",
        owner="other-owner",
    )
    path_b = _write_request("lock-b.json", req_b)
    _runtime(["clear-failures"])
    cp_b, code_b = _ctl(ctl, ["run", "--request", str(path_b)], check=False)
    assert code_b != 0
    req_c = _base_request(execution_id="exec-lock-c", batch_id="batch-lock-other")
    path_c = _write_request("lock-c.json", req_c)
    cp_c, code_c = _ctl(ctl, ["run", "--request", str(path_c)], check=False)
    assert code_c == 0
    assert cp_c["status"] == "SUCCEEDED"


def test_cutover_pins_inflight_and_shadow_readonly(ctl):
    """Cutover affects only new work; Jenkins shadow stays read-only under Lambda."""
    deploy, _ = _ctl(ctl, ["deploy", "--infra", str(WORKSPACE)])
    _ctl(ctl, ["cutover", "--generation", str(deploy["generation"]), "--writer", "lambda"])
    # Start an in-flight execution paused before write_ledger.
    _runtime(["inject", "BEFORE_STAGE:write_ledger", "3"])
    inflight = _base_request(execution_id="exec-inflight", batch_id="batch-inflight")
    path_i = _write_request("inflight.json", inflight)
    cp_i, code = _ctl(ctl, ["run", "--request", str(path_i)], check=False)
    assert cp_i["status"] == "RETRY_PENDING"
    assert code != 0
    pinned_gen = cp_i["generation"]
    # Bump deployment generation and cut over.
    dep = json.loads((WORKSPACE / "deployment.json").read_text(encoding="utf-8"))
    dep["generation"] = pinned_gen + 1
    (WORKSPACE / "deployment.json").write_text(json.dumps(dep) + "\n", encoding="utf-8")
    deploy2, _ = _ctl(ctl, ["deploy", "--infra", str(WORKSPACE)])
    cut, _ = _ctl(
        ctl,
        ["cutover", "--generation", str(deploy2["generation"]), "--writer", "lambda"],
    )
    assert cut["active_generation"] == deploy2["generation"]
    _runtime(["clear-failures"])
    cp_resume, code = _ctl(ctl, ["resume", "--execution", "exec-inflight"], check=False)
    assert code == 0
    assert cp_resume["generation"] == pinned_gen
    new_req = _base_request(execution_id="exec-newgen", batch_id="batch-newgen")
    path_n = _write_request("newgen.json", new_req)
    cp_n, code = _ctl(ctl, ["run", "--request", str(path_n)], check=False)
    assert code == 0
    assert cp_n["generation"] == deploy2["generation"]
    shadow, _ = _ctl(ctl, ["jenkins-shadow", "--request", str(path_n)], check=False)
    assert shadow.get("wrote") is False
    state = _runtime(["inspect", "state"])
    assert state.get("writer") == "lambda"
    assert state.get("jenkins_writes", 0) == 0


def test_lost_alias_shift_reconciles_from_runtime(ctl):
    """Lost cutover replies adopt the committed runtime generation/epoch."""
    deploy, _ = _ctl(ctl, ["deploy", "--infra", str(WORKSPACE)])
    _ctl(ctl, ["cutover", "--generation", str(deploy["generation"]), "--writer", "lambda"])
    dep = json.loads((WORKSPACE / "deployment.json").read_text(encoding="utf-8"))
    dep["generation"] = deploy["generation"] + 1
    (WORKSPACE / "deployment.json").write_text(json.dumps(dep) + "\n", encoding="utf-8")
    deploy2, _ = _ctl(ctl, ["deploy", "--infra", str(WORKSPACE)])
    _runtime(["inject", "AFTER_ALIAS_SHIFT", "1"])
    cut, code = _ctl(
        ctl,
        ["cutover", "--generation", str(deploy2["generation"]), "--writer", "lambda"],
        check=False,
    )
    assert code == 0
    assert cut["active_generation"] == deploy2["generation"]
    assert cut["writer"] == "lambda"
    state = _runtime(["inspect", "state"])
    assert state["active_generation"] == deploy2["generation"]


def test_protocol_variants_and_conflicts(ctl):
    """v1 derives legacy owner; v2 requires owner; conflicting reuse is rejected."""
    deploy, _ = _ctl(ctl, ["deploy", "--infra", str(WORKSPACE)])
    _ctl(ctl, ["cutover", "--generation", str(deploy["generation"]), "--writer", "lambda"])
    v1 = _base_request(
        protocol_version=1,
        execution_id="exec-v1",
        batch_id="batch-v1",
        owner="",
    )
    path = _write_request("v1.json", v1)
    cp, code = _ctl(ctl, ["run", "--request", str(path)], check=False)
    assert code == 0
    assert cp["owner"] == "legacy-jenkins/batch-v1"
    bad = _base_request(protocol_version=2, execution_id="exec-v2-bad", owner="")
    path_bad = _write_request("v2bad.json", bad)
    _, code = _ctl(ctl, ["run", "--request", str(path_bad)], check=False)
    assert code != 0
    ok = _base_request(execution_id="exec-conflict", batch_id="batch-conflict")
    path_ok = _write_request("conflict-ok.json", ok)
    _ctl(ctl, ["run", "--request", str(path_ok)], check=False)
    clash = _base_request(
        execution_id="exec-conflict",
        batch_id="batch-conflict-other",
        owner="lambda-pod-verifier",
    )
    path_clash = _write_request("conflict-bad.json", clash)
    data, code = _ctl(ctl, ["run", "--request", str(path_clash)], check=False)
    assert code != 0
    blob = json.dumps(data) + str(data)
    # stderr may hold the message; re-run capture
    proc = _run([str(ctl), "run", "--request", str(path_clash)])
    assert "conflicting" in (proc.stdout + proc.stderr).lower()


def test_reconcile_torn_journal_and_pending_resume(ctl):
    """Reconcile repairs a torn journal tail and resumes pending work."""
    deploy, _ = _ctl(ctl, ["deploy", "--infra", str(WORKSPACE)])
    _ctl(ctl, ["cutover", "--generation", str(deploy["generation"]), "--writer", "lambda"])
    _runtime(["inject", "BEFORE_STAGE:build_report", "3"])
    req = _base_request(execution_id="exec-recon", batch_id="batch-recon")
    path = _write_request("recon.json", req)
    cp, code = _ctl(ctl, ["run", "--request", str(path)], check=False)
    assert cp["status"] == "RETRY_PENDING"
    assert code != 0
    journal = VAR / "operations.journal.jsonl"
    assert journal.exists()
    with journal.open("a", encoding="utf-8") as handle:
        handle.write("{not-json\n")
    _runtime(["clear-failures"])
    summary, code = _ctl(ctl, ["reconcile"], check=False)
    assert code == 0
    assert summary.get("journal_repaired") is True
    assert "exec-recon" in summary.get("resumed", [])
    cp2, _ = _ctl(ctl, ["inspect", "--what", "execution", "--execution", "exec-recon"])
    assert cp2["status"] in {"SUCCEEDED", "PARTIAL"}
    summary2, _ = _ctl(ctl, ["reconcile"])
    assert summary2.get("journal_repaired") is False


def test_hidden_batch_size_and_stage_inventory_noop_reorder(ctl):
    """Larger batches still isolate poison; map reorder of equal stages is invalid only if order breaks."""
    deploy, _ = _ctl(ctl, ["deploy", "--infra", str(WORKSPACE)])
    _ctl(ctl, ["cutover", "--generation", str(deploy["generation"]), "--writer", "lambda"])
    items = [{"id": f"i-{i}", "amount": i, "tenant": "t"} for i in range(8)]
    items[2]["poison"] = True
    items[5]["poison"] = True
    req = _base_request(
        execution_id="exec-large",
        batch_id="batch-large",
        items=items,
    )
    path = _write_request("large.json", req)
    cp, code = _ctl(ctl, ["run", "--request", str(path)], check=False)
    assert code == 0
    assert cp["status"] == "PARTIAL"
    counts = _unique_effect_counts()
    assert counts["ledger"] == 6
    assert counts["report"] == 1
    # Reordering stages must be rejected.
    doc = _load_stages()
    original = copy.deepcopy(doc)
    doc["stages"][3], doc["stages"][4] = doc["stages"][4], doc["stages"][3]
    _write_stages(doc)
    _, code = _ctl(ctl, ["deploy", "--infra", str(WORKSPACE)], check=False)
    assert code != 0
    _write_stages(original)


def test_anti_cheat_forged_report_rejected_by_operator(ctl):
    """A static forged READY report is overwritten only after a real dual-run."""
    forged = {
        "status": "READY",
        "report_digest": "0" * 64,
        "writer": "lambda",
        "runtime_writer": "lambda",
        "effect_counts": {"ledger": 2, "report": 1, "notify": 1, "archive": 1},
        "plan_lambda_functions": 12,
        "plan_lambda_aliases": 12,
        "active_generation": 1,
        "execution_status": "SUCCEEDED",
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "cutover-report.json").write_text(json.dumps(forged) + "\n", encoding="utf-8")
    proc = _run([str(BIN)])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    report = json.loads((OUTPUT / "cutover-report.json").read_text(encoding="utf-8"))
    assert report["status"] == "READY"
    assert report["report_digest"] != forged["report_digest"]
    assert len(report["report_digest"]) == 64
