"""IAM, fast-forward merge, and exactly-once pipeline trigger checks."""

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
    bare = home / "var" / "repos" / "ledger.git"
    _git(["init", "--bare", str(bare)])
    _git(["--git-dir", str(bare), "symbolic-ref", "HEAD", "refs/heads/main"])
    wt = home / "bootstrap"
    _git(["clone", str(bare), str(wt)])
    (wt / "README").write_text("ledger mainline\n", encoding="utf-8")
    _git(["add", "README"], cwd=wt)
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
            "initial ledger",
        ],
        cwd=wt,
    )
    _git(["push", "origin", "HEAD:refs/heads/main"], cwd=wt)


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
        raise AssertionError(
            f"ccctl {args} rc={cp.returncode}\nstdout={cp.stdout}\nstderr={cp.stderr}"
        )
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


def test_p2p_ccctl_and_contract_present() -> None:
    """Operator binary, contract, policies, and principal catalog are present."""
    assert BIN.is_file()
    if os.name != "nt":
        assert bool(BIN.stat().st_mode & stat.S_IXUSR)
    assert (APP / "docs" / "iam-git-contract.md").is_file()
    principals = json.loads((APP / "ops" / "principals.json").read_text(encoding="utf-8"))
    assert "dev-alice" in principals and "rev-a" in principals


def test_p2p_clone_roundtrip(home: Path, tmp_path: Path) -> None:
    """A developer can clone ledger and read the seeded README."""
    dest = tmp_path / "wt-clone"
    _run(home, ["clone", "ledger", str(dest)], principal="dev-alice")
    assert (dest / "README").read_text(encoding="utf-8").startswith("ledger")


def test_f2p_push_main_requires_mfa(home: Path, tmp_path: Path) -> None:
    """GitPush to main without MFA is denied even from the office CIDR."""
    dest = tmp_path / "wt-mfa"
    _run(home, ["clone", "ledger", str(dest)], principal="dev-alice")
    _commit(dest, "no-mfa-main", "a.txt")
    cp = _run(
        home,
        ["push", "ledger", str(dest), "main"],
        principal="dev-alice",
        mfa=False,
        ip=OFFICE,
        check=False,
    )
    assert cp.returncode != 0
    assert _err(cp)["error"] == "AccessDenied"


def test_f2p_same_commit_clone_ok_after_denied_push(home: Path, tmp_path: Path) -> None:
    """GitPull remains allowed for a commit whose main push was denied."""
    dest = tmp_path / "wt-pull"
    _run(home, ["clone", "ledger", str(dest)], principal="dev-alice")
    _commit(dest, "still-cloneable", "b.txt")
    denied = _run(
        home,
        ["push", "ledger", str(dest), "main"],
        principal="dev-alice",
        mfa=False,
        check=False,
    )
    assert denied.returncode != 0
    other = tmp_path / "wt-other"
    _run(home, ["clone", "ledger", str(other)], principal="intern")
    assert (other / "README").is_file()


def test_f2p_push_main_mfa_wrong_ip_denied(home: Path, tmp_path: Path) -> None:
    """MFA does not waive the office IpAddress condition on main."""
    dest = tmp_path / "wt-ip"
    _run(home, ["clone", "ledger", str(dest)], principal="dev-alice")
    _commit(dest, "remote-mfa", "c.txt")
    cp = _run(
        home,
        ["push", "ledger", str(dest), "main"],
        principal="dev-alice",
        mfa=True,
        ip=REMOTE,
        check=False,
    )
    assert cp.returncode != 0
    assert _err(cp)["error"] == "AccessDenied"


def test_p2p_push_main_mfa_office_allowed(home: Path, tmp_path: Path) -> None:
    """GitPush to main succeeds with MFA from an address inside 10.8.0.0/16."""
    dest = tmp_path / "wt-ok"
    _run(home, ["clone", "ledger", str(dest)], principal="dev-alice")
    _commit(dest, "ok-main", "d.txt")
    cp = _run(
        home,
        ["push", "ledger", str(dest), "main"],
        principal="dev-alice",
        mfa=True,
        ip=OFFICE,
    )
    body = _json(cp)
    assert body["ok"] is True
    assert body["ref"] == "refs/heads/main"
    assert len(body["commit"]) >= 7


def test_p2p_push_dev_branch_without_mfa(home: Path, tmp_path: Path) -> None:
    """Feature-branch StringEquals allows a dev push without MFA."""
    dest = tmp_path / "wt-dev"
    _run(home, ["clone", "ledger", str(dest)], principal="dev-alice")
    _git(["checkout", "-b", "dev/alice"], cwd=dest)
    _commit(dest, "feature", "f.txt")
    cp = _run(
        home,
        ["push", "ledger", str(dest), "dev/alice"],
        principal="dev-alice",
        mfa=False,
        ip=OFFICE,
    )
    assert _json(cp)["ref"] == "refs/heads/dev/alice"


def test_f2p_explicit_deny_beats_allow(home: Path, tmp_path: Path) -> None:
    """An explicit Deny on refs/heads/release wins over the matching Allow."""
    dest = tmp_path / "wt-rel"
    _run(home, ["clone", "ledger", str(dest)], principal="dev-alice")
    _git(["checkout", "-b", "release"], cwd=dest)
    _commit(dest, "rel", "r.txt")
    cp = _run(
        home,
        ["push", "ledger", str(dest), "release"],
        principal="dev-alice",
        mfa=True,
        ip=OFFICE,
        check=False,
    )
    assert cp.returncode != 0
    assert _err(cp)["error"] == "AccessDenied"


def test_f2p_intern_cannot_push(home: Path, tmp_path: Path) -> None:
    """pull-only attachments do not authorize GitPush."""
    dest = tmp_path / "wt-int"
    _run(home, ["clone", "ledger", str(dest)], principal="intern")
    _commit(dest, "intern-try", "i.txt")
    cp = _run(
        home,
        ["push", "ledger", str(dest), "main"],
        principal="intern",
        mfa=True,
        ip=OFFICE,
        check=False,
    )
    assert cp.returncode != 0
    assert _err(cp)["error"] == "AccessDenied"


def test_f2p_star_action_stays_on_sandbox_resource(home: Path, tmp_path: Path) -> None:
    """Action * on sandbox does not grant MergePullRequestByFastForward on ledger."""
    dest = tmp_path / "wt-star"
    _run(home, ["clone", "ledger", str(dest)], principal="dev-alice")
    _git(["checkout", "-b", "dev/alice"], cwd=dest)
    _commit(dest, "pr-body", "p.txt")
    _run(home, ["push", "ledger", str(dest), "dev/alice"], principal="dev-alice")
    pr = _json(_run(home, ["pr", "ledger", "--source", "dev/alice", "--dest", "main"], principal="dev-alice"))
    _run(home, ["approve", "ledger", str(pr["pr_id"])], principal="rev-a", ip=OFFICE)
    _run(home, ["approve", "ledger", str(pr["pr_id"])], principal="rev-b", ip=OFFICE)
    cp = _run(
        home,
        ["merge", "ledger", str(pr["pr_id"])],
        principal="dev-alice",
        ip=OFFICE,
        check=False,
    )
    assert cp.returncode != 0
    assert _err(cp)["error"] == "AccessDenied"


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


def test_p2p_merge_requires_quorum(home: Path, tmp_path: Path) -> None:
    """Merge fails until two distinct pool reviewers have approved."""
    pr_id, _dest = _open_pr(home, tmp_path, "q.txt")
    _run(home, ["approve", "ledger", str(pr_id)], principal="rev-a", ip=OFFICE)
    cp = _run(
        home,
        ["merge", "ledger", str(pr_id)],
        principal="rev-a",
        ip=OFFICE,
        check=False,
    )
    assert cp.returncode != 0
    assert _err(cp).get("code") == "APPROVAL_QUORUM"


def test_f2p_author_approval_does_not_count(home: Path, tmp_path: Path) -> None:
    """The PR author cannot satisfy quorum even if they stamp the request."""
    pr_id, _dest = _open_pr(home, tmp_path, "auth.txt")
    _run(home, ["approve", "ledger", str(pr_id)], principal="dev-alice")
    _run(home, ["approve", "ledger", str(pr_id)], principal="rev-a", ip=OFFICE)
    cp = _run(
        home,
        ["merge", "ledger", str(pr_id)],
        principal="rev-a",
        ip=OFFICE,
        check=False,
    )
    assert cp.returncode != 0
    assert _err(cp).get("code") == "APPROVAL_QUORUM"


def test_f2p_duplicate_approval_does_not_count(home: Path, tmp_path: Path) -> None:
    """Two stamps from the same reviewer are one vote."""
    pr_id, _dest = _open_pr(home, tmp_path, "dup.txt")
    _run(home, ["approve", "ledger", str(pr_id)], principal="rev-a", ip=OFFICE)
    _run(home, ["approve", "ledger", str(pr_id)], principal="rev-a", ip=OFFICE)
    cp = _run(
        home,
        ["merge", "ledger", str(pr_id)],
        principal="rev-a",
        ip=OFFICE,
        check=False,
    )
    assert cp.returncode != 0
    assert _err(cp).get("code") == "APPROVAL_QUORUM"


def test_f2p_outside_pool_approval_ignored(home: Path, tmp_path: Path) -> None:
    """Approvals from principals outside the rule pool do not count toward quorum."""
    pr_id, _dest = _open_pr(home, tmp_path, "pool.txt")
    _run(home, ["approve", "ledger", str(pr_id)], principal="rev-a", ip=OFFICE)
    _run(home, ["approve", "ledger", str(pr_id)], principal="pipeline-bot", ip=OFFICE)
    cp = _run(
        home,
        ["merge", "ledger", str(pr_id)],
        principal="rev-a",
        ip=OFFICE,
        check=False,
    )
    assert cp.returncode != 0
    assert _err(cp).get("code") == "APPROVAL_QUORUM"


def test_f2p_merge_is_fast_forward_only(home: Path, tmp_path: Path) -> None:
    """A destination that advanced after the PR source branched cannot merge."""
    pr_id, dest = _open_pr(home, tmp_path, "ff.txt")
    _run(home, ["approve", "ledger", str(pr_id)], principal="rev-a", ip=OFFICE)
    _run(home, ["approve", "ledger", str(pr_id)], principal="rev-b", ip=OFFICE)
    main_wt = tmp_path / "wt-main-move"
    _run(home, ["clone", "ledger", str(main_wt)], principal="dev-alice")
    _commit(main_wt, "main moved", "moved.txt")
    _run(home, ["push", "ledger", str(main_wt), "main"], principal="dev-alice", mfa=True, ip=OFFICE)
    cp = _run(
        home,
        ["merge", "ledger", str(pr_id)],
        principal="rev-a",
        ip=OFFICE,
        check=False,
    )
    assert cp.returncode != 0
    assert _err(cp).get("code") == "NOT_FAST_FORWARD"
    _ = dest


def test_f2p_merge_fast_forward_updates_dest(home: Path, tmp_path: Path) -> None:
    """After quorum, dest HEAD equals the source commit and is not a merge commit."""
    pr_id, dest = _open_pr(home, tmp_path, "okff.txt")
    src = _git(["rev-parse", "HEAD"], cwd=dest)
    _run(home, ["approve", "ledger", str(pr_id)], principal="rev-a", ip=OFFICE)
    _run(home, ["approve", "ledger", str(pr_id)], principal="rev-b", ip=OFFICE)
    body = _json(_run(home, ["merge", "ledger", str(pr_id)], principal="rev-a", ip=OFFICE))
    assert body["fast_forward"] is True
    assert body["commit"] == src
    assert _parents(home, body["commit"])  # has a parent
    assert len(_parents(home, body["commit"])) == 1


def test_f2p_merge_requires_office_ip(home: Path, tmp_path: Path) -> None:
    """Reviewer merge from outside the office CIDR is denied."""
    pr_id, _dest = _open_pr(home, tmp_path, "mip.txt")
    _run(home, ["approve", "ledger", str(pr_id)], principal="rev-a", ip=OFFICE)
    _run(home, ["approve", "ledger", str(pr_id)], principal="rev-b", ip=OFFICE)
    cp = _run(
        home,
        ["merge", "ledger", str(pr_id)],
        principal="rev-a",
        ip=REMOTE,
        check=False,
    )
    assert cp.returncode != 0
    assert _err(cp)["error"] == "AccessDenied"


def test_f2p_deliver_exactly_once(home: Path, tmp_path: Path) -> None:
    """A second deliver of the same repo/ref/commit/pipeline does not append a journal line."""
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
    assert row["status"] == "delivered"
    assert row["event_id"] == first["delivered"][0]["event_id"] == second["delivered"][0]["event_id"]


def test_f2p_event_id_is_sha256_preimage(home: Path, tmp_path: Path) -> None:
    """event_id is sha256(repo|ref|commit|pipeline) hex, not a random token."""
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
    """deliver on a ref with no pipeline binding writes no journal rows."""
    dest = tmp_path / "wt-feat"
    _run(home, ["clone", "ledger", str(dest)], principal="dev-alice")
    _git(["checkout", "-b", "dev/alice"], cwd=dest)
    _commit(dest, "no-pipe", "np.txt")
    _run(home, ["push", "ledger", str(dest), "dev/alice"], principal="dev-alice")
    body = _json(_run(home, ["deliver", "ledger", "refs/heads/dev/alice"], principal="pipeline-bot"))
    assert body["delivered"] == []
    assert body["duplicate"] is False
    path = home / "var" / "triggers.jsonl"
    assert not path.exists() or path.read_text(encoding="utf-8").strip() == ""


def test_p2p_unknown_principal_denied(home: Path, tmp_path: Path) -> None:
    """Unknown --principal fails closed before touching git."""
    dest = tmp_path / "nope"
    cp = _run(home, ["clone", "ledger", str(dest)], principal="not-a-user", check=False)
    assert cp.returncode != 0
    err = _err(cp)
    assert err["error"] == "AccessDenied"
    assert err.get("code") == "UNKNOWN_PRINCIPAL"


def test_f2p_branch_condition_is_exact(home: Path, tmp_path: Path) -> None:
    """dev-ben may not GitPush alice's listed branch even with MFA."""
    dest = tmp_path / "wt-ben"
    _run(home, ["clone", "ledger", str(dest)], principal="dev-ben")
    _git(["checkout", "-b", "dev/alice"], cwd=dest)
    _commit(dest, "not-bens", "nb.txt")
    cp = _run(
        home,
        ["push", "ledger", str(dest), "dev/alice"],
        principal="dev-ben",
        mfa=True,
        ip=OFFICE,
        check=False,
    )
    assert cp.returncode != 0
    assert _err(cp)["error"] == "AccessDenied"


def test_f2p_duplicate_approve_stored_once(home: Path, tmp_path: Path) -> None:
    """approve records a principal at most once in /var/prs.json."""
    pr_id, _dest = _open_pr(home, tmp_path, "once.txt")
    _run(home, ["approve", "ledger", str(pr_id)], principal="rev-a", ip=OFFICE)
    body = _json(_run(home, ["approve", "ledger", str(pr_id)], principal="rev-a", ip=OFFICE))
    assert body["approvals"].count("rev-a") == 1
    store = json.loads((home / "var" / "prs.json").read_text(encoding="utf-8"))
    assert store["items"][str(pr_id)]["approvals"].count("rev-a") == 1


def test_p2p_pr_store_written(home: Path, tmp_path: Path) -> None:
    """Opening a PR persists an open record under the contracted PR store path."""
    pr_id, _dest = _open_pr(home, tmp_path, "store.txt")
    store = json.loads((home / "var" / "prs.json").read_text(encoding="utf-8"))
    item = store["items"][str(pr_id)]
    assert item["status"] == "open"
    assert item["dest"] == "refs/heads/main"
    assert item["author"] == "dev-alice"
