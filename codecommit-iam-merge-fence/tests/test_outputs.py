"""Behavioral checks for CodeCommit IAM merge fence control plane."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

APP = Path(os.environ.get("CC_ARTIFACT", "/app/codecommit"))
BIN = APP / "bin" / "ccctl"
OFFICE = "10.8.12.4"
REMOTE = "203.0.113.9"
GIT_ENV = {
    "GIT_AUTHOR_NAME": "CodeCommit Lab",
    "GIT_AUTHOR_EMAIL": "lab@local",
    "GIT_COMMITTER_NAME": "CodeCommit Lab",
    "GIT_COMMITTER_EMAIL": "lab@local",
    "GIT_AUTHOR_DATE": "2026-04-01T12:00:00+0000",
    "GIT_COMMITTER_DATE": "2026-04-01T12:00:00+0000",
    "GIT_TERMINAL_PROMPT": "0",
}


def _git(args: list[str], cwd: Path | None = None) -> str:
    env = os.environ.copy()
    env.update(GIT_ENV)
    cp = subprocess.run(
        ["git", *args],
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    if cp.returncode != 0:
        raise AssertionError(f"git {args} failed: {cp.stderr or cp.stdout}")
    return cp.stdout.strip()


def _reset(home: Path) -> None:
    if home.exists():
        shutil.rmtree(home)
    home.mkdir(parents=True)
    shutil.copytree(APP / "ops", home / "ops")
    shutil.copytree(APP / "policies", home / "policies")
    (home / "var" / "repos").mkdir(parents=True)
    env = os.environ.copy()
    env["CC_ROOT"] = str(home)
    env["PYTHONPATH"] = str(APP / "lib")
    subprocess.run([sys.executable, str(APP / "lib" / "cc" / "seed.py")], check=True, env=env)


def _run(
    home: Path,
    args: list[str],
    *,
    principal: str,
    mfa: bool = False,
    ip: str = OFFICE,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(BIN), "--principal", principal, "--source-ip", ip]
    if mfa:
        cmd.append("--mfa")
    cmd.extend(args)
    env = os.environ.copy()
    env.update(GIT_ENV)
    env["CC_ROOT"] = str(home)
    env["PYTHONPATH"] = str(APP / "lib")
    cp = subprocess.run(cmd, capture_output=True, text=True, check=False, env=env)
    if check and cp.returncode != 0:
        raise AssertionError(f"ccctl {args} rc={cp.returncode}\n{cp.stdout}\n{cp.stderr}")
    return cp


def _json(cp: subprocess.CompletedProcess[str]) -> dict:
    lines = [ln for ln in cp.stdout.splitlines() if ln.strip().startswith("{")]
    return json.loads(lines[-1])


def _err(cp: subprocess.CompletedProcess[str]) -> dict:
    return json.loads(cp.stderr.strip().splitlines()[-1])


def _commit(work: Path, message: str, name: str) -> None:
    (work / name).write_text(message + "\n", encoding="utf-8")
    _git(["add", name], cwd=work)
    _git(
        [
            "-c",
            "user.name=CodeCommit Lab",
            "-c",
            "user.email=lab@local",
            "-c",
            "commit.gpgsign=false",
            "commit",
            "-m",
            message,
        ],
        cwd=work,
    )


def _parents(home: Path, rev: str) -> list[str]:
    bare = home / "var" / "repos" / "ledger.git"
    out = _git(["--git-dir", str(bare), "rev-list", "--parents", "-n", "1", rev])
    return out.split()[1:]


@pytest.fixture
def home(tmp_path: Path) -> Path:
    dest = tmp_path / "cc"
    _reset(dest)
    return dest


def _open_pr(home: Path, tmp_path: Path, name: str = "p.txt") -> tuple[int, Path]:
    dest = tmp_path / f"wt-{name}"
    _run(home, ["clone", "ledger", str(dest)], principal="dev-alice")
    _git(["checkout", "-b", "dev/alice"], cwd=dest)
    _commit(dest, f"work-{name}", name)
    _run(home, ["push", "ledger", str(dest), "dev/alice"], principal="dev-alice")
    pr = _json(
        _run(home, ["pr", "ledger", "--source", "dev/alice", "--dest", "main"], principal="dev-alice")
    )
    return int(pr["pr_id"]), dest


def test_p2p_ccctl_and_contract_present() -> None:
    """Operator binary and binding contract are present."""
    assert BIN.is_file()
    if os.name != "nt":
        assert bool(BIN.stat().st_mode & stat.S_IXUSR)
    assert (APP / "docs" / "control-plane-contract.md").is_file()
    principals = json.loads((APP / "ops" / "principals.json").read_text(encoding="utf-8"))
    assert "dev-alice" in principals and "rev-a" in principals


def test_p2p_clone_roundtrip(home: Path, tmp_path: Path) -> None:
    """Developer can clone ledger and read seeded README."""
    dest = tmp_path / "wt-clone"
    _run(home, ["clone", "ledger", str(dest)], principal="dev-alice")
    assert (dest / "README").read_text(encoding="utf-8").startswith("ledger")


def test_f2p_push_main_requires_mfa(home: Path, tmp_path: Path) -> None:
    """GitPush to main without MFA is denied from the office CIDR."""
    dest = tmp_path / "wt-mfa"
    _run(home, ["clone", "ledger", str(dest)], principal="dev-alice")
    _commit(dest, "no-mfa-main", "a.txt")
    cp = _run(
        home, ["push", "ledger", str(dest), "main"], principal="dev-alice", mfa=False, ip=OFFICE, check=False
    )
    assert cp.returncode != 0
    assert _err(cp)["error"] == "AccessDenied"


def test_f2p_same_commit_clone_ok_after_denied_push(home: Path, tmp_path: Path) -> None:
    """GitPull remains allowed after a denied main push attempt."""
    dest = tmp_path / "wt-pull"
    _run(home, ["clone", "ledger", str(dest)], principal="dev-alice")
    _commit(dest, "still-cloneable", "b.txt")
    denied = _run(home, ["push", "ledger", str(dest), "main"], principal="dev-alice", mfa=False, check=False)
    assert denied.returncode != 0
    other = tmp_path / "wt-other"
    _run(home, ["clone", "ledger", str(other)], principal="intern")
    assert (other / "README").is_file()


def test_f2p_push_main_mfa_wrong_ip_denied(home: Path, tmp_path: Path) -> None:
    """MFA does not waive office IpAddress on main."""
    dest = tmp_path / "wt-ip"
    _run(home, ["clone", "ledger", str(dest)], principal="dev-alice")
    _commit(dest, "remote-mfa", "c.txt")
    cp = _run(
        home, ["push", "ledger", str(dest), "main"], principal="dev-alice", mfa=True, ip=REMOTE, check=False
    )
    assert cp.returncode != 0
    assert _err(cp)["error"] == "AccessDenied"


def test_p2p_push_main_mfa_office_allowed(home: Path, tmp_path: Path) -> None:
    """GitPush to main succeeds with MFA from office CIDR."""
    dest = tmp_path / "wt-ok"
    _run(home, ["clone", "ledger", str(dest)], principal="dev-alice")
    _commit(dest, "ok-main", "d.txt")
    body = _json(
        _run(home, ["push", "ledger", str(dest), "main"], principal="dev-alice", mfa=True, ip=OFFICE)
    )
    assert body["ok"] is True
    assert body["ref"] == "refs/heads/main"
    assert len(body["commit"]) >= 7


def test_p2p_push_dev_branch_without_mfa(home: Path, tmp_path: Path) -> None:
    """Feature-branch StringEquals allows push without MFA."""
    dest = tmp_path / "wt-dev"
    _run(home, ["clone", "ledger", str(dest)], principal="dev-alice")
    _git(["checkout", "-b", "dev/alice"], cwd=dest)
    _commit(dest, "feature", "f.txt")
    body = _json(
        _run(home, ["push", "ledger", str(dest), "dev/alice"], principal="dev-alice", mfa=False, ip=OFFICE)
    )
    assert body["ref"] == "refs/heads/dev/alice"


def test_f2p_branch_condition_is_exact(home: Path, tmp_path: Path) -> None:
    """dev-ben may not push alice's listed branch."""
    dest = tmp_path / "wt-ben"
    _run(home, ["clone", "ledger", str(dest)], principal="dev-ben")
    _git(["checkout", "-b", "dev/alice"], cwd=dest)
    _commit(dest, "not-bens", "nb.txt")
    cp = _run(
        home, ["push", "ledger", str(dest), "dev/alice"], principal="dev-ben", mfa=True, ip=OFFICE, check=False
    )
    assert cp.returncode != 0
    assert _err(cp)["error"] == "AccessDenied"


def test_f2p_explicit_deny_beats_allow(home: Path, tmp_path: Path) -> None:
    """Explicit Deny on release wins over Allow."""
    dest = tmp_path / "wt-rel"
    _run(home, ["clone", "ledger", str(dest)], principal="dev-alice")
    _git(["checkout", "-b", "release"], cwd=dest)
    _commit(dest, "rel", "r.txt")
    cp = _run(
        home, ["push", "ledger", str(dest), "release"], principal="dev-alice", mfa=True, ip=OFFICE, check=False
    )
    assert cp.returncode != 0
    assert _err(cp)["error"] == "AccessDenied"


def test_f2p_intern_cannot_push(home: Path, tmp_path: Path) -> None:
    """pull-only principal cannot GitPush."""
    dest = tmp_path / "wt-int"
    _run(home, ["clone", "ledger", str(dest)], principal="intern")
    _commit(dest, "intern-try", "i.txt")
    cp = _run(
        home, ["push", "ledger", str(dest), "main"], principal="intern", mfa=True, ip=OFFICE, check=False
    )
    assert cp.returncode != 0
    assert _err(cp)["error"] == "AccessDenied"


def test_f2p_star_action_stays_on_sandbox_resource(home: Path, tmp_path: Path) -> None:
    """Action * on sandbox does not grant ledger merge."""
    pr_id, _ = _open_pr(home, tmp_path, "star.txt")
    _run(home, ["approve", "ledger", str(pr_id)], principal="rev-a", ip=OFFICE)
    _run(home, ["approve", "ledger", str(pr_id)], principal="rev-b", ip=OFFICE)
    cp = _run(home, ["merge", "ledger", str(pr_id)], principal="dev-alice", ip=OFFICE, check=False)
    assert cp.returncode != 0
    assert _err(cp)["error"] == "AccessDenied"


def test_f2p_merge_requires_quorum(home: Path, tmp_path: Path) -> None:
    """Merge fails until two distinct pool reviewers approve."""
    pr_id, _ = _open_pr(home, tmp_path, "q.txt")
    _run(home, ["approve", "ledger", str(pr_id)], principal="rev-a", ip=OFFICE)
    cp = _run(home, ["merge", "ledger", str(pr_id)], principal="rev-a", ip=OFFICE, check=False)
    assert cp.returncode != 0
    assert _err(cp).get("code") == "APPROVAL_QUORUM"


def test_f2p_author_approval_does_not_count(home: Path, tmp_path: Path) -> None:
    """PR author stamp does not satisfy quorum."""
    pr_id, _ = _open_pr(home, tmp_path, "auth.txt")
    _run(home, ["approve", "ledger", str(pr_id)], principal="dev-alice")
    _run(home, ["approve", "ledger", str(pr_id)], principal="rev-a", ip=OFFICE)
    cp = _run(home, ["merge", "ledger", str(pr_id)], principal="rev-a", ip=OFFICE, check=False)
    assert cp.returncode != 0
    assert _err(cp).get("code") == "APPROVAL_QUORUM"


def test_f2p_duplicate_approval_does_not_count(home: Path, tmp_path: Path) -> None:
    """Two stamps from one reviewer are one vote."""
    pr_id, _ = _open_pr(home, tmp_path, "dup.txt")
    _run(home, ["approve", "ledger", str(pr_id)], principal="rev-a", ip=OFFICE)
    _run(home, ["approve", "ledger", str(pr_id)], principal="rev-a", ip=OFFICE)
    cp = _run(home, ["merge", "ledger", str(pr_id)], principal="rev-a", ip=OFFICE, check=False)
    assert cp.returncode != 0
    assert _err(cp).get("code") == "APPROVAL_QUORUM"


def test_f2p_outside_pool_approval_ignored(home: Path, tmp_path: Path) -> None:
    """Approvals outside the rule pool do not count."""
    pr_id, _ = _open_pr(home, tmp_path, "pool.txt")
    _run(home, ["approve", "ledger", str(pr_id)], principal="rev-a", ip=OFFICE)
    _run(home, ["approve", "ledger", str(pr_id)], principal="pipeline-bot", ip=OFFICE)
    cp = _run(home, ["merge", "ledger", str(pr_id)], principal="rev-a", ip=OFFICE, check=False)
    assert cp.returncode != 0
    assert _err(cp).get("code") == "APPROVAL_QUORUM"


def test_f2p_duplicate_approve_stored_once(home: Path, tmp_path: Path) -> None:
    """approve stores a principal at most once."""
    pr_id, _ = _open_pr(home, tmp_path, "once.txt")
    _run(home, ["approve", "ledger", str(pr_id)], principal="rev-a", ip=OFFICE)
    body = _json(_run(home, ["approve", "ledger", str(pr_id)], principal="rev-a", ip=OFFICE))
    assert body["approvals"].count("rev-a") == 1


def test_f2p_merge_is_fast_forward_only(home: Path, tmp_path: Path) -> None:
    """Divergent destination cannot merge."""
    pr_id, _ = _open_pr(home, tmp_path, "ff.txt")
    _run(home, ["approve", "ledger", str(pr_id)], principal="rev-a", ip=OFFICE)
    _run(home, ["approve", "ledger", str(pr_id)], principal="rev-b", ip=OFFICE)
    main_wt = tmp_path / "wt-main-move"
    _run(home, ["clone", "ledger", str(main_wt)], principal="dev-alice")
    _commit(main_wt, "main moved", "moved.txt")
    _run(home, ["push", "ledger", str(main_wt), "main"], principal="dev-alice", mfa=True, ip=OFFICE)
    cp = _run(home, ["merge", "ledger", str(pr_id)], principal="rev-a", ip=OFFICE, check=False)
    assert cp.returncode != 0
    assert _err(cp).get("code") == "NOT_FAST_FORWARD"


def test_f2p_merge_fast_forward_updates_dest(home: Path, tmp_path: Path) -> None:
    """After quorum, dest HEAD equals source commit with one parent."""
    pr_id, dest = _open_pr(home, tmp_path, "okff.txt")
    src = _git(["rev-parse", "HEAD"], cwd=dest)
    _run(home, ["approve", "ledger", str(pr_id)], principal="rev-a", ip=OFFICE)
    _run(home, ["approve", "ledger", str(pr_id)], principal="rev-b", ip=OFFICE)
    body = _json(_run(home, ["merge", "ledger", str(pr_id)], principal="rev-a", ip=OFFICE))
    assert body["fast_forward"] is True
    assert body["commit"] == src
    assert len(_parents(home, body["commit"])) == 1


def test_f2p_merge_requires_office_ip(home: Path, tmp_path: Path) -> None:
    """Reviewer merge from outside office CIDR is denied."""
    pr_id, _ = _open_pr(home, tmp_path, "mip.txt")
    _run(home, ["approve", "ledger", str(pr_id)], principal="rev-a", ip=OFFICE)
    _run(home, ["approve", "ledger", str(pr_id)], principal="rev-b", ip=OFFICE)
    cp = _run(home, ["merge", "ledger", str(pr_id)], principal="rev-a", ip=REMOTE, check=False)
    assert cp.returncode != 0
    assert _err(cp)["error"] == "AccessDenied"


def test_f2p_deliver_exactly_once(home: Path, tmp_path: Path) -> None:
    """Second deliver of same tip is duplicate with one journal line."""
    dest = tmp_path / "wt-del"
    _run(home, ["clone", "ledger", str(dest)], principal="dev-alice")
    _commit(dest, "for-pipe", "pipe.txt")
    _run(home, ["push", "ledger", str(dest), "main"], principal="dev-alice", mfa=True, ip=OFFICE)
    first = _json(_run(home, ["deliver", "ledger", "refs/heads/main"], principal="pipeline-bot"))
    second = _json(_run(home, ["deliver", "ledger", "main"], principal="pipeline-bot"))
    assert first["duplicate"] is False
    assert second["duplicate"] is True
    journal = (home / "var" / "triggers.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(journal) == 1
    row = json.loads(journal[0])
    assert list(row.keys()) == ["event_id", "repo", "ref", "commit", "pipeline", "status"]
    assert row["pipeline"] == "settle-prod"


def test_f2p_event_id_is_sha256_preimage(home: Path, tmp_path: Path) -> None:
    """event_id is sha256(repo|ref|commit|pipeline)."""
    dest = tmp_path / "wt-eid"
    _run(home, ["clone", "ledger", str(dest)], principal="dev-alice")
    _commit(dest, "eid", "e.txt")
    pushed = _json(
        _run(home, ["push", "ledger", str(dest), "main"], principal="dev-alice", mfa=True, ip=OFFICE)
    )
    body = _json(_run(home, ["deliver", "ledger", "refs/heads/main"], principal="pipeline-bot"))
    expect = hashlib.sha256(
        f"ledger|refs/heads/main|{pushed['commit']}|settle-prod".encode()
    ).hexdigest()
    assert body["delivered"][0]["event_id"] == expect


def test_p2p_deliver_unbound_ref_writes_nothing(home: Path, tmp_path: Path) -> None:
    """deliver on unbound ref writes no journal rows."""
    dest = tmp_path / "wt-feat"
    _run(home, ["clone", "ledger", str(dest)], principal="dev-alice")
    _git(["checkout", "-b", "dev/alice"], cwd=dest)
    _commit(dest, "no-pipe", "np.txt")
    _run(home, ["push", "ledger", str(dest), "dev/alice"], principal="dev-alice")
    body = _json(_run(home, ["deliver", "ledger", "refs/heads/dev/alice"], principal="pipeline-bot"))
    assert body["delivered"] == []
    path = home / "var" / "triggers.jsonl"
    assert not path.exists() or path.read_text(encoding="utf-8").strip() == ""


def test_p2p_unknown_principal_denied(home: Path, tmp_path: Path) -> None:
    """Unknown principal fails closed."""
    dest = tmp_path / "nope"
    cp = _run(home, ["clone", "ledger", str(dest)], principal="not-a-user", check=False)
    assert cp.returncode != 0
    err = _err(cp)
    assert err["error"] == "AccessDenied"
    assert err.get("code") == "UNKNOWN_PRINCIPAL"


def test_p2p_pr_store_written(home: Path, tmp_path: Path) -> None:
    """Opening a PR persists an open record."""
    pr_id, _ = _open_pr(home, tmp_path, "store.txt")
    store = json.loads((home / "var" / "prs.json").read_text(encoding="utf-8"))
    item = store["items"][str(pr_id)]
    assert item["status"] == "open"
    assert item["author"] == "dev-alice"


def test_f2p_audit_records_denied_push(home: Path, tmp_path: Path) -> None:
    """Denied authorize decisions are appended to the audit log."""
    dest = tmp_path / "wt-aud"
    _run(home, ["clone", "ledger", str(dest)], principal="dev-alice")
    _commit(dest, "deny-me", "x.txt")
    _run(home, ["push", "ledger", str(dest), "main"], principal="dev-alice", mfa=False, check=False)
    rows = [
        json.loads(ln)
        for ln in (home / "var" / "audit.jsonl").read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    denied = [r for r in rows if r.get("allowed") is False and r.get("action") == "codecommit:GitPush"]
    assert denied, "expected denied push audit row"


def test_f2p_deliver_enqueues_outbox(home: Path, tmp_path: Path) -> None:
    """First deliver enqueues a webhook outbox row for settle-prod."""
    dest = tmp_path / "wt-ob"
    _run(home, ["clone", "ledger", str(dest)], principal="dev-alice")
    _commit(dest, "ob", "o.txt")
    _run(home, ["push", "ledger", str(dest), "main"], principal="dev-alice", mfa=True, ip=OFFICE)
    _run(home, ["deliver", "ledger", "refs/heads/main"], principal="pipeline-bot")
    rows = [
        json.loads(ln)
        for ln in (home / "var" / "outbox.jsonl").read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    assert rows
    assert rows[0]["pipeline"] == "settle-prod"
    assert rows[0]["webhook_id"] == "wh-settle"
    assert rows[0]["status"] == "pending"


def test_f2p_dispatch_marks_outbox_attempt(home: Path, tmp_path: Path) -> None:
    """dispatch-webhooks records an attempt against pending outbox rows."""
    dest = tmp_path / "wt-disp"
    _run(home, ["clone", "ledger", str(dest)], principal="dev-alice")
    _commit(dest, "disp", "z.txt")
    _run(home, ["push", "ledger", str(dest), "main"], principal="dev-alice", mfa=True, ip=OFFICE)
    _run(home, ["deliver", "ledger", "main"], principal="pipeline-bot")
    body = _json(_run(home, ["dispatch-webhooks"], principal="pipeline-bot"))
    assert body["ok"] is True
    assert body["sink"]
    rows = [
        json.loads(ln)
        for ln in (home / "var" / "outbox.jsonl").read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    assert rows[0]["attempts"] >= 1
    assert rows[0]["status"] == "delivered"


def test_f2p_api_merge_requires_iam(home: Path, tmp_path: Path) -> None:
    """Developer merge cannot bypass MergePullRequestByFastForward IAM."""
    pr_id, _ = _open_pr(home, tmp_path, "api.txt")
    _run(home, ["approve", "ledger", str(pr_id)], principal="rev-a", ip=OFFICE)
    _run(home, ["approve", "ledger", str(pr_id)], principal="rev-b", ip=OFFICE)
    cp = _run(home, ["merge", "ledger", str(pr_id)], principal="dev-alice", ip=OFFICE, check=False)
    assert cp.returncode != 0
    assert _err(cp)["error"] == "AccessDenied"


def test_f2p_absent_mfa_not_treated_as_true(home: Path, tmp_path: Path) -> None:
    """Missing MFA context fails Bool MFA true conditions."""
    dest = tmp_path / "wt-mfa2"
    _run(home, ["clone", "ledger", str(dest)], principal="dev-alice")
    _commit(dest, "mfa2", "m2.txt")
    cp = _run(
        home, ["push", "ledger", str(dest), "main"], principal="dev-alice", mfa=False, ip=OFFICE, check=False
    )
    assert cp.returncode != 0


def test_p2p_metrics_command(home: Path) -> None:
    """metrics command returns structured snapshot JSON."""
    body = _json(_run(home, ["metrics"], principal="pipeline-bot"))
    assert "audit" in body
    assert "journal_lines" in body


def test_f2p_second_deliver_does_not_duplicate_outbox(home: Path, tmp_path: Path) -> None:
    """Duplicate deliver does not append a second outbox row for the same event."""
    dest = tmp_path / "wt-ob2"
    _run(home, ["clone", "ledger", str(dest)], principal="dev-alice")
    _commit(dest, "ob2", "o2.txt")
    _run(home, ["push", "ledger", str(dest), "main"], principal="dev-alice", mfa=True, ip=OFFICE)
    _run(home, ["deliver", "ledger", "main"], principal="pipeline-bot")
    _run(home, ["deliver", "ledger", "refs/heads/main"], principal="pipeline-bot")
    rows = [
        json.loads(ln)
        for ln in (home / "var" / "outbox.jsonl").read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    assert len(rows) == 1


def test_f2p_journal_key_order(home: Path, tmp_path: Path) -> None:
    """Trigger journal objects use the contracted key order."""
    dest = tmp_path / "wt-keys"
    _run(home, ["clone", "ledger", str(dest)], principal="dev-alice")
    _commit(dest, "keys", "k.txt")
    _run(home, ["push", "ledger", str(dest), "main"], principal="dev-alice", mfa=True, ip=OFFICE)
    _run(home, ["deliver", "ledger", "main"], principal="pipeline-bot")
    row = json.loads((home / "var" / "triggers.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert list(row.keys()) == ["event_id", "repo", "ref", "commit", "pipeline", "status"]


def test_f2p_merge_commit_not_created_on_success(home: Path, tmp_path: Path) -> None:
    """Successful merge is not a two-parent merge commit."""
    pr_id, dest = _open_pr(home, tmp_path, "noparent.txt")
    _run(home, ["approve", "ledger", str(pr_id)], principal="rev-a", ip=OFFICE)
    _run(home, ["approve", "ledger", str(pr_id)], principal="rev-b", ip=OFFICE)
    body = _json(_run(home, ["merge", "ledger", str(pr_id)], principal="rev-a", ip=OFFICE))
    assert len(_parents(home, body["commit"])) == 1
    assert body["commit"] == _git(["rev-parse", "HEAD"], cwd=dest)


def test_f2p_release_deny_audited(home: Path, tmp_path: Path) -> None:
    """Denied release push is present in audit with allowed false."""
    dest = tmp_path / "wt-reld"
    _run(home, ["clone", "ledger", str(dest)], principal="dev-alice")
    _git(["checkout", "-b", "release"], cwd=dest)
    _commit(dest, "rel2", "r2.txt")
    _run(
        home, ["push", "ledger", str(dest), "release"], principal="dev-alice", mfa=True, ip=OFFICE, check=False
    )
    rows = [
        json.loads(ln)
        for ln in (home / "var" / "audit.jsonl").read_text(encoding="utf-8").splitlines()
        if ln.strip()
    ]
    assert any(r.get("allowed") is False for r in rows)


def test_f2p_required_quorum_from_config(home: Path, tmp_path: Path) -> None:
    """Configured required=2 is enforced (one approval is not enough)."""
    pr_id, _ = _open_pr(home, tmp_path, "req.txt")
    _run(home, ["approve", "ledger", str(pr_id)], principal="rev-b", ip=OFFICE)
    cp = _run(home, ["merge", "ledger", str(pr_id)], principal="rev-b", ip=OFFICE, check=False)
    assert _err(cp).get("code") == "APPROVAL_QUORUM"
