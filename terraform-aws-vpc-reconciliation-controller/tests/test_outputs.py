"""Verifier for the VPC reconciliation controller.

Rebuilds the submitted Go controller, starts a trusted control-plane with
seeded observed state, drives plan/apply/resume/verify, re-plans Terraform,
and checks routing, endpoint association, import moves, audit drift, journal
fencing, and the READY reconciliation report.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parent / "fixtures"
sys.path.insert(0, str(FIXTURES))

CMD_ARTIFACT = Path("/app/cmd")
TF_ARTIFACT = Path("/app/terraform")
BIN_ARTIFACT = Path("/app/bin")
VAR_ARTIFACT = Path("/app/var/reconcile")
OUTPUT_ARTIFACT = Path("/app/output")
SEED = FIXTURES / "seed"
DESIRED = FIXTURES / "desired.json"

CP_URL = os.environ.get("VPC_CONTROLPLANE_URL", "http://127.0.0.1:7432")
WORK = Path("/tmp/vpc-reconcile-work")
ENV = {
    **os.environ,
    "TF_CLI_CONFIG_FILE": "/app/terraform.tfrc",
    "TF_IN_AUTOMATION": "1",
    "CHECKPOINT_DISABLE": "1",
    "AWS_ACCESS_KEY_ID": "test",
    "AWS_SECRET_ACCESS_KEY": "test",
    "AWS_DEFAULT_REGION": "us-east-1",
    "CGO_ENABLED": "0",
    "VPC_CONTROLPLANE_URL": CP_URL,
    "VPC_CP_SEED": str(SEED),
    "PYTHONPATH": "/app",
    "PATH": "/usr/local/go/bin:" + os.environ.get("PATH", ""),
}


def _run(cmd: list[str], cwd: Path | None = None, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=ENV,
        text=True,
        capture_output=True,
        check=check,
    )


def _digest(obj: object) -> str:
    raw = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def _http_json(method: str, path: str, body: dict | None = None) -> dict:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        CP_URL.rstrip("/") + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"} if data is not None else {},
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode())


def _cp_healthy() -> bool:
    try:
        with urllib.request.urlopen(CP_URL.rstrip("/") + "/health", timeout=1) as resp:
            return resp.status == 200
    except Exception:  # noqa: BLE001
        return False


_cp_proc: subprocess.Popen | None = None


def _start_cp() -> None:
    global _cp_proc
    if _cp_healthy():
        try:
            _http_json("POST", "/v1/reset", {})
        except Exception:  # noqa: BLE001
            pass
        return
    log = open("/tmp/cp-verifier.log", "w", encoding="utf-8")
    _cp_proc = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "from controlplane import main; raise SystemExit(main())",
        ],
        env=ENV,
        stdout=log,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    for _ in range(80):
        if _cp_healthy():
            return
        time.sleep(0.1)
    log_tail = ""
    try:
        log_tail = Path("/tmp/cp-verifier.log").read_text(encoding="utf-8")[-2000:]
    except OSError:
        pass
    raise RuntimeError(f"control-plane failed to start\n{log_tail}")


def _stop_cp() -> None:
    global _cp_proc
    if _cp_proc is not None:
        _cp_proc.terminate()
        try:
            _cp_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            _cp_proc.kill()
        _cp_proc = None


def _prepare_root(overrides: dict | None = None) -> Path:
    if WORK.exists():
        shutil.rmtree(WORK)
    root = WORK / "incident"
    root.mkdir(parents=True)
    (root / "data").mkdir()
    desired = json.loads(DESIRED.read_text(encoding="utf-8"))
    if overrides and "desired" in overrides:
        desired = overrides["desired"]
    (root / "data" / "desired.json").write_text(json.dumps(desired, indent=2), encoding="utf-8")
    (root / "var" / "reconcile").mkdir(parents=True)
    (root / "output").mkdir(parents=True)
    # Point binary workspace desired path used by terraform separately.
    return root


def _build_controller(dest_bin: Path) -> None:
    build_dir = WORK / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(parents=True)
    shutil.copytree(CMD_ARTIFACT, build_dir / "cmd")
    gom = Path("/app/go.mod")
    if not gom.exists():
        # Fall back to solution-compatible module file next to cmd artifact parents.
        (build_dir / "go.mod").write_text(
            "module vpc-reconcile\n\ngo 1.24\n\nrequire modernc.org/sqlite v1.34.5\n",
            encoding="utf-8",
        )
    else:
        shutil.copy2(gom, build_dir / "go.mod")
    tidy = _run(["go", "mod", "tidy"], cwd=build_dir)
    assert tidy.returncode == 0, tidy.stdout + tidy.stderr
    build = _run(["go", "build", "-o", str(dest_bin), "./cmd/vpcreconcile"], cwd=build_dir)
    assert build.returncode == 0, build.stdout + build.stderr


def _reconcile(bin_path: Path, root: Path, cmd: str, owner: str | None = None, fail_after: str | None = None):
    args = [str(bin_path), cmd, "--root", str(root), "--json"]
    if owner:
        args += ["--owner", owner]
    if fail_after:
        args += ["--fail-after", fail_after]
    proc = _run(args)
    try:
        out = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        out = {"stdout": proc.stdout, "stderr": proc.stderr}
    return proc, out


def _load_state(root: Path) -> dict | None:
    db = root / "var" / "reconcile" / "state.db"
    if not db.exists():
        return None
    con = sqlite3.connect(db)
    try:
        row = con.execute("SELECT state_json FROM recovered WHERE id = 1").fetchone()
    except sqlite3.Error:
        return None
    finally:
        con.close()
    if not row:
        return None
    return json.loads(row[0])


def _journal(root: Path) -> list[dict]:
    db = root / "var" / "reconcile" / "state.db"
    if not db.exists():
        return []
    con = sqlite3.connect(db)
    try:
        rows = con.execute(
            "SELECT payload_json, row_checksum FROM journal ORDER BY seq ASC"
        ).fetchall()
    finally:
        con.close()
    out = []
    for payload, checksum in rows:
        digest = hashlib.sha256(payload.encode()).hexdigest()
        if digest != checksum:
            break
        out.append(json.loads(payload))
    return out


def _default_target(rt: dict) -> str | None:
    for route in rt.get("routes", []):
        if route.get("destination") == "0.0.0.0/0":
            return route.get("target")
    return None


def _plan_workspace(workspace: Path) -> tuple[dict | None, subprocess.CompletedProcess]:
    # Ensure desired.json visible at the path referenced by workspace.
    data_dir = Path("/app/data")
    data_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(DESIRED, data_dir / "desired.json")
    init = _run(["terraform", "init", "-backend=false", "-input=false"], cwd=workspace)
    if init.returncode != 0:
        return None, init
    plan = _run(
        [
            "terraform",
            "plan",
            "-refresh=false",
            "-input=false",
            "-out=tfplan",
            "-no-color",
        ],
        cwd=workspace,
    )
    if plan.returncode != 0:
        return None, plan
    show = _run(["terraform", "show", "-json", "tfplan"], cwd=workspace)
    if show.returncode != 0:
        return None, show
    return json.loads(show.stdout), show


@pytest.fixture(scope="session", autouse=True)
def _session_cp():
    _start_cp()
    yield
    _stop_cp()


@pytest.fixture(autouse=True)
def _reset_each():
    _start_cp()
    if WORK.exists():
        shutil.rmtree(WORK)
    yield


@pytest.fixture(scope="session")
def controller_bin(tmp_path_factory: pytest.TempPathFactory) -> Path:
    dest = tmp_path_factory.mktemp("bin") / "vpc-reconcile"
    # Session-level build uses /tmp work dir carefully.
    global WORK
    WORK = Path("/tmp/vpc-reconcile-build")
    _build_controller(dest)
    WORK = Path("/tmp/vpc-reconcile-work")
    return dest


@pytest.fixture(scope="session")
def agent_report() -> dict:
    path = OUTPUT_ARTIFACT / "reconciliation-report.json"
    assert path.is_file(), "missing /app/output/reconciliation-report.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_agent_report_ready(agent_report: dict):
    """Public operator report must be READY with required digest fields."""
    assert agent_report["schema_version"] == "vpc-reconcile-report.1"
    assert agent_report["status"] == "READY"
    assert agent_report.get("report_digest")
    assert agent_report.get("config_digest")
    assert agent_report.get("plan_digest")
    assert agent_report.get("state_digest")
    assert agent_report.get("controlplane_token_route")
    assert agent_report.get("controlplane_token_endpoint")
    assert agent_report.get("outputs", {}).get("private_app_route_table_ids")


def test_submitted_controller_source_present():
    """Verifier receives controller source under the declared artifact path."""
    assert (CMD_ARTIFACT / "vpcreconcile").exists()
    mains = list(CMD_ARTIFACT.rglob("*.go"))
    assert mains, "no Go sources under /app/cmd"


def test_happy_path_routing_endpoints_imports(controller_bin: Path):
    """Apply recovers same-AZ NAT routes, app-only endpoints, and import moves."""
    root = _prepare_root()
    proc, _ = _reconcile(controller_bin, root, "apply", owner="owner-a")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    st = _load_state(root)
    assert st is not None
    assert st["schema_version"] == "vpc-reconcile.aws.1"

    for rt in st["route_tables"]:
        if rt["tier"] == "app":
            assert _default_target(rt) == f"nat-prod-{rt['az'][-1]}"
        if rt["tier"] == "data":
            assert _default_target(rt) is None

    app_ids = set(st["outputs"]["private_app_route_table_ids"])
    assert app_ids == {"rtb-import-app-a", "rtb-import-app-b", "rtb-import-app-c"}
    for ep in st["gateway_endpoints"]:
        assert set(ep["route_table_ids"]) == app_ids
        acct = ep["policy"]["Statement"][0]["Condition"]["StringEquals"]["aws:PrincipalAccount"]
        assert acct == "111122223333"

    moved_from = sorted(m["from"] for m in st["moved"])
    assert moved_from == [
        "module.vpc.aws_subnet.private[0]",
        "module.vpc.aws_subnet.private[1]",
        "module.vpc.aws_subnet.private[2]",
    ]

    committed = _http_json("GET", "/v1/committed")
    assert committed["tokens"]["route"]
    assert committed["tokens"]["endpoint"]
    assert len(committed["route_tables"]) >= 1
    assert len(committed["endpoints"]) >= 1


def test_manual_routes_and_resolver_drift_preserved(controller_bin: Path):
    """Manual routes stay on tables and resolver drift is report_only."""
    root = _prepare_root()
    _reconcile(controller_bin, root, "apply", owner="owner-a")
    st = _load_state(root)
    assert st is not None
    app_a = next(rt for rt in st["route_tables"] if rt["tier"] == "app" and rt["az"].endswith("a"))
    assert any(r.get("owner") == "manual" for r in app_a["routes"])
    drift = st["drift_report"]
    assert any(
        d.get("action") == "report_only" and d.get("resource") == "resolver_security_group"
        for d in drift
    )
    fl = st["flow_log"]
    assert set(fl["subnet_ids"]) == {s["id"] for s in st["subnets"]}
    actions = set(fl["iam_policy"]["Action"])
    assert "logs:CreateLogStream" in actions and "logs:PutLogEvents" in actions
    assert "logs:*" not in actions
    assert str(fl["iam_policy"]["Resource"]).endswith(":*")


def test_plan_is_read_only(controller_bin: Path):
    """plan must not create the SQLite database."""
    root = _prepare_root()
    db = root / "var" / "reconcile" / "state.db"
    assert not db.exists()
    proc, out = _reconcile(controller_bin, root, "plan")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert out.get("schema_version") == "vpc-reconcile.aws.1"
    assert not db.exists()


def test_verify_ready_only_after_apply(controller_bin: Path):
    """verify reports READY only after controller-generated recovered state exists."""
    root = _prepare_root()
    proc, out = _reconcile(controller_bin, root, "verify")
    assert out.get("valid") is not True
    assert out.get("phase") != "READY"
    _reconcile(controller_bin, root, "apply", owner="owner-a")
    proc2, out2 = _reconcile(controller_bin, root, "verify")
    assert proc2.returncode == 0
    assert out2["valid"] is True and out2["phase"] == "READY"


def test_fail_after_route_commit_resume(controller_bin: Path):
    """Lost response after route_commit resumes without duplicate journal commits."""
    root = _prepare_root()
    proc, _ = _reconcile(controller_bin, root, "apply", owner="owner-a", fail_after="route_commit")
    assert proc.returncode != 0
    proc2, _ = _reconcile(controller_bin, root, "resume", owner="owner-a")
    assert proc2.returncode == 0, proc2.stdout + proc2.stderr
    st = _load_state(root)
    assert st is not None
    commits = [j for j in _journal(root) if j.get("event") == "apply_committed"]
    assert len(commits) == 1


def test_fail_after_endpoint_commit_resume(controller_bin: Path):
    """Lost response after endpoint_commit resumes without duplicating associations."""
    root = _prepare_root()
    proc, _ = _reconcile(
        controller_bin, root, "apply", owner="owner-a", fail_after="endpoint_commit"
    )
    assert proc.returncode != 0
    _reconcile(controller_bin, root, "resume", owner="owner-a")
    st = _load_state(root)
    assert st is not None
    for ep in st["gateway_endpoints"]:
        assert len(ep["route_table_ids"]) == len(set(ep["route_table_ids"]))


def test_stale_owner_and_config_digest(controller_bin: Path):
    """Active journal fences other owners and changed config digests."""
    root = _prepare_root()
    proc, _ = _reconcile(controller_bin, root, "apply", owner="owner-a", fail_after="route_commit")
    assert proc.returncode != 0
    proc_b, out_b = _reconcile(controller_bin, root, "resume", owner="owner-b")
    assert proc_b.returncode != 0
    assert "stale owner" in str(out_b.get("error", "")).lower() or "stale owner" in str(
        out_b.get("error", "")
    )

    root2 = _prepare_root()
    _reconcile(controller_bin, root2, "apply", owner="owner-a", fail_after="route_commit")
    desired = json.loads((root2 / "data" / "desired.json").read_text(encoding="utf-8"))
    desired["subnets"][3]["cidr"] = "10.42.99.0/24"
    (root2 / "data" / "desired.json").write_text(json.dumps(desired, indent=2), encoding="utf-8")
    proc_c, out_c = _reconcile(controller_bin, root2, "resume", owner="owner-a")
    assert proc_c.returncode != 0
    assert "config digest changed" in str(out_c.get("error", "")).lower()


def test_journal_corruption_and_torn_tail(controller_bin: Path):
    """Interior corruption fails closed; torn final row is repairable on resume."""
    root = _prepare_root()
    _reconcile(controller_bin, root, "plan")
    db = root / "var" / "reconcile" / "state.db"
    # Force DB + a valid then corrupt middle row via SQL after a partial apply.
    _reconcile(controller_bin, root, "apply", owner="owner-a", fail_after="route_commit")
    con = sqlite3.connect(db)
    con.execute(
        "INSERT INTO journal(event, owner, config_digest, stage, state_digest, token, payload_json, row_checksum) VALUES(?,?,?,?,?,?,?,?)",
        (
            "bogus",
            "owner-a",
            "x",
            "x",
            "",
            "",
            "{not-json",
            "deadbeef",
        ),
    )
    # Add a later valid-looking row so corruption is not at the tail.
    payload = json.dumps({"event": "apply_committed", "owner": "owner-a", "config_digest": "x"})
    con.execute(
        "INSERT INTO journal(event, owner, config_digest, stage, state_digest, token, payload_json, row_checksum) VALUES(?,?,?,?,?,?,?,?)",
        (
            "apply_committed",
            "owner-a",
            "x",
            "",
            "",
            "",
            payload,
            hashlib.sha256(payload.encode()).hexdigest(),
        ),
    )
    con.commit()
    con.close()
    proc, out = _reconcile(controller_bin, root, "resume", owner="owner-a")
    assert proc.returncode != 0
    assert "journal corruption" in str(out.get("error", "")).lower()

    root2 = _prepare_root()
    _reconcile(controller_bin, root2, "apply", owner="owner-a", fail_after="route_commit")
    con = sqlite3.connect(root2 / "var" / "reconcile" / "state.db")
    # Corrupt only the newest row checksum to simulate a torn tail.
    last = con.execute("SELECT seq FROM journal ORDER BY seq DESC LIMIT 1").fetchone()[0]
    con.execute("UPDATE journal SET row_checksum=? WHERE seq=?", ("00" * 32, last))
    con.commit()
    con.close()
    proc2, _ = _reconcile(controller_bin, root2, "resume", owner="owner-a")
    assert proc2.returncode == 0, proc2.stdout + proc2.stderr


def test_idempotent_repeated_apply(controller_bin: Path):
    """Second successful apply does not duplicate moved actions or commit events."""
    root = _prepare_root()
    _reconcile(controller_bin, root, "apply", owner="owner-a")
    first = _load_state(root)
    first_journal = _journal(root)
    _reconcile(controller_bin, root, "apply", owner="owner-a")
    second = _load_state(root)
    second_journal = _journal(root)
    assert first is not None and second is not None
    assert first["moved"] == second["moved"]
    assert first["gateway_endpoints"] == second["gateway_endpoints"]
    assert first["route_tables"] == second["route_tables"]
    assert len([j for j in second_journal if j.get("event") == "apply_committed"]) == len(
        [j for j in first_journal if j.get("event") == "apply_committed"]
    )


def test_missing_nat_and_overlap_fail_closed(controller_bin: Path):
    """Unsafe NAT and CIDR inputs fail before control-plane mutation."""
    desired = json.loads(DESIRED.read_text(encoding="utf-8"))
    bad_nat = copy.deepcopy(desired)
    # Remove health by using an AZ with no available NAT in seed: mark via desired AZ orphan.
    bad_nat["subnets"].append(
        {"name": "prod-app-z", "tier": "app", "az": "us-east-1z", "cidr": "10.42.90.0/24"}
    )
    root = _prepare_root({"desired": bad_nat})
    # Patch seed NAT indirectly: controller reads NAT from control-plane, which has no 1z.
    before = _http_json("GET", "/v1/committed")
    proc, out = _reconcile(controller_bin, root, "apply", owner="owner-a")
    assert proc.returncode != 0
    assert "missing nat gateway" in str(out.get("error", "")).lower()
    after = _http_json("GET", "/v1/committed")
    assert after == before

    bad_cidr = copy.deepcopy(desired)
    bad_cidr["subnets"][3]["cidr"] = "10.42.0.0/24"  # overlaps public-a
    root2 = _prepare_root({"desired": bad_cidr})
    _http_json("POST", "/v1/reset", {})
    before2 = _http_json("GET", "/v1/committed")
    proc2, out2 = _reconcile(controller_bin, root2, "apply", owner="owner-a")
    assert proc2.returncode != 0
    assert "overlaps" in str(out2.get("error", "")).lower()
    after2 = _http_json("GET", "/v1/committed")
    assert after2 == before2


def test_unsupported_endpoint_and_account_mismatch(controller_bin: Path):
    """Unsupported services and policy account mismatches fail closed."""
    desired = json.loads(DESIRED.read_text(encoding="utf-8"))
    bad = copy.deepcopy(desired)
    bad["gateway_endpoints"] = [{"service": "s3"}, {"service": "sqs"}]
    root = _prepare_root({"desired": bad})
    proc, out = _reconcile(controller_bin, root, "apply", owner="owner-a")
    assert proc.returncode != 0
    assert "unsupported" in str(out.get("error", "")).lower()

    # Account mismatch via control-plane observed policy mutation.
    _http_json("POST", "/v1/reset", {})
    observed = _http_json("GET", "/v1/observed")
    for ep in observed["endpoints"]:
        ep["policy"]["Statement"][0]["Condition"]["StringEquals"]["aws:PrincipalAccount"] = (
            "999988887777"
        )
    # Re-seed by writing fixture override file and resetting CP with env is heavy;
    # instead commit is blocked at validate using observed fetch — poke seed file copy.
    seed_eps = json.loads((SEED / "endpoints.json").read_text(encoding="utf-8"))
    for ep in seed_eps["endpoints"]:
        ep["policy"]["Statement"][0]["Condition"]["StringEquals"]["aws:PrincipalAccount"] = (
            "999988887777"
        )
    tmp_seed = WORK / "seed-mismatch"
    if tmp_seed.exists():
        shutil.rmtree(tmp_seed)
    shutil.copytree(SEED, tmp_seed)
    (tmp_seed / "endpoints.json").write_text(json.dumps(seed_eps, indent=2), encoding="utf-8")
    # Restart CP against mismatched seed.
    _stop_cp()
    os.environ["VPC_CP_SEED"] = str(tmp_seed)
    ENV["VPC_CP_SEED"] = str(tmp_seed)
    _start_cp()
    root2 = _prepare_root()
    proc2, out2 = _reconcile(controller_bin, root2, "apply", owner="owner-a")
    assert proc2.returncode != 0
    assert "account mismatch" in str(out2.get("error", "")).lower()
    # Restore default seed CP for later tests.
    _stop_cp()
    os.environ["VPC_CP_SEED"] = str(SEED)
    ENV["VPC_CP_SEED"] = str(SEED)
    _start_cp()


def test_terraform_plan_semantics():
    """Submitted Terraform plans app-only gateway endpoints and no data default route."""
    ws_src = TF_ARTIFACT / "workspaces" / "reconcile"
    assert ws_src.is_dir()
    workspace = WORK / "tf"
    if workspace.exists():
        shutil.rmtree(workspace)
    shutil.copytree(
        TF_ARTIFACT,
        workspace,
        ignore=shutil.ignore_patterns(
            ".terraform", ".terraform.lock.hcl", "*.tfstate*", "tfplan"
        ),
    )
    plan, proc = _plan_workspace(workspace / "workspaces" / "reconcile")
    assert plan is not None, proc.stdout + proc.stderr

    changes = plan.get("resource_changes") or []
    route_changes = [c for c in changes if c.get("type") == "aws_route"]
    data_defaults = [
        c
        for c in route_changes
        if "data" in str(c.get("address", ""))
        and (c.get("change", {}).get("after") or {}).get("destination_cidr_block")
        == "0.0.0.0/0"
    ]
    assert data_defaults == [], "data tier must not plan a default internet route"

    endpoint_changes = [c for c in changes if c.get("type") == "aws_vpc_endpoint"]
    assert endpoint_changes, "expected gateway endpoints in plan"
    desired = json.loads(DESIRED.read_text(encoding="utf-8"))
    app_count = sum(1 for s in desired["subnets"] if s["tier"] == "app")
    for ep in endpoint_changes:
        after = ep.get("change", {}).get("after") or {}
        rt_ids = after.get("route_table_ids")
        # IDs may be unknown-after-apply; configuration must still target app tables only.
        if isinstance(rt_ids, list) and rt_ids and all(isinstance(x, str) for x in rt_ids):
            assert len(rt_ids) == app_count
        cfg = ep.get("change", {}).get("after_unknown") or {}
        # Soft check: endpoint resource is present and not destroyed.
        assert "delete" not in (ep.get("change", {}).get("actions") or [])
        _ = cfg

    sgs = [c for c in changes if c.get("type") == "aws_security_group"]
    assert sgs
    for sg in sgs:
        after = sg.get("change", {}).get("after") or {}
        for rule in after.get("ingress") or []:
            assert "0.0.0.0/0" not in (rule.get("cidr_blocks") or [])


def test_az_expansion_preserves_import_ids(controller_bin: Path):
    """Adding an AZ changes only the new closure and keeps imported app IDs."""
    desired = json.loads(DESIRED.read_text(encoding="utf-8"))
    expanded = copy.deepcopy(desired)
    expanded["availability_zones"].append("us-east-1d")
    expanded["subnets"].extend(
        [
            {"name": "prod-public-d", "tier": "public", "az": "us-east-1d", "cidr": "10.42.3.0/24"},
            {"name": "prod-app-d", "tier": "app", "az": "us-east-1d", "cidr": "10.42.13.0/24"},
            {"name": "prod-data-d", "tier": "data", "az": "us-east-1d", "cidr": "10.42.23.0/24"},
        ]
    )
    expanded["nat_gateways"].append({"id": "nat-prod-d", "az": "us-east-1d"})
    # Expand control-plane NAT health.
    seed = WORK / "seed-expand"
    if seed.exists():
        shutil.rmtree(seed)
    shutil.copytree(SEED, seed)
    nat = json.loads((seed / "nat_health.json").read_text(encoding="utf-8"))
    nat["nat_gateways"].append({"id": "nat-prod-d", "az": "us-east-1d", "state": "available"})
    (seed / "nat_health.json").write_text(json.dumps(nat, indent=2), encoding="utf-8")
    _stop_cp()
    ENV["VPC_CP_SEED"] = str(seed)
    os.environ["VPC_CP_SEED"] = str(seed)
    _start_cp()
    root = _prepare_root({"desired": expanded})
    proc, _ = _reconcile(controller_bin, root, "apply", owner="owner-a")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    st = _load_state(root)
    assert st is not None
    app_ids = set(st["outputs"]["private_app_route_table_ids"])
    assert {"rtb-import-app-a", "rtb-import-app-b", "rtb-import-app-c"} <= app_ids
    assert any(rt["az"] == "us-east-1d" and rt["tier"] == "app" for rt in st["route_tables"])
    _stop_cp()
    ENV["VPC_CP_SEED"] = str(SEED)
    os.environ["VPC_CP_SEED"] = str(SEED)
    _start_cp()


def test_report_digest_matches_agent_artifact(agent_report: dict):
    """Agent report_digest must match a recomputation over report fields."""
    fields = {k: v for k, v in agent_report.items() if k != "report_digest"}
    assert agent_report["report_digest"] == _digest(fields)
