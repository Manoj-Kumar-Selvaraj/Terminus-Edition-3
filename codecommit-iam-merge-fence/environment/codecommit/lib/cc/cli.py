from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cc.errors import CcError
from cc.iam import actions as iam_actions
from cc.pipelines.deliver import deliver
from cc.prs import approvals, merge, store as pr_store
from cc.repos import catalog, gitops
from cc.services import authz_gateway, metrics, policy_sim, serializers
from cc.util import full_ref
from cc.webhooks.dispatch import dispatch_pending


def _out(obj: object) -> None:
    print(json.dumps(obj, separators=(",", ":")))


def _err(exc: CcError) -> None:
    print(exc.to_json(), file=sys.stderr)


def cmd_clone(ns: argparse.Namespace) -> int:
    catalog.require_repo(ns.repo)
    authz_gateway.gated_authorize(
        ns.principal,
        iam_actions.GIT_PULL,
        ns.repo,
        "main",
        mfa=ns.mfa,
        source_ip=ns.source_ip,
        fixed=ns.fixed,
    )
    gitops.clone(ns.repo, Path(ns.dest))
    return 0


def cmd_push(ns: argparse.Namespace) -> int:
    catalog.require_repo(ns.repo)
    ref = full_ref(ns.branch)
    authz_gateway.gated_authorize(
        ns.principal,
        iam_actions.GIT_PUSH,
        ns.repo,
        ref,
        mfa=ns.mfa,
        source_ip=ns.source_ip,
        fixed=ns.fixed,
    )
    commit = gitops.push(ns.repo, Path(ns.worktree), ns.branch)
    _out(serializers.push_success(ns.repo, ref, commit))
    return 0


def cmd_pr(ns: argparse.Namespace) -> int:
    catalog.require_repo(ns.repo)
    authz_gateway.gated_authorize(
        ns.principal,
        iam_actions.GIT_PULL,
        ns.repo,
        ns.source,
        mfa=ns.mfa,
        source_ip=ns.source_ip,
        fixed=ns.fixed,
    )
    src_commit = gitops.ref_commit(ns.repo, ns.source)
    pr = pr_store.create(ns.repo, ns.source, ns.dest, src_commit, ns.principal)
    _out(serializers.pr_success(pr.pr_id, pr.source, pr.dest, pr.source_commit))
    return 0


def cmd_approve(ns: argparse.Namespace) -> int:
    body = approvals.approve(int(ns.pr_id), ns.principal, fixed=ns.fixed)
    _out(body)
    return 0


def cmd_merge(ns: argparse.Namespace) -> int:
    body = merge.merge(
        int(ns.pr_id),
        ns.principal,
        mfa=ns.mfa,
        source_ip=ns.source_ip,
        fixed=ns.fixed,
    )
    _out(body)
    return 0


def cmd_deliver(ns: argparse.Namespace) -> int:
    body = deliver(ns.repo, ns.ref, fixed=ns.fixed)
    _out(body)
    return 0


def cmd_simulate(ns: argparse.Namespace) -> int:
    _out(
        policy_sim.simulate(
            ns.principal,
            ns.action,
            ns.repo,
            ns.ref,
            mfa=ns.mfa,
            source_ip=ns.source_ip,
            fixed=ns.fixed,
        )
    )
    return 0


def cmd_metrics(ns: argparse.Namespace) -> int:
    _out(metrics.snapshot())
    return 0


def cmd_dispatch(ns: argparse.Namespace) -> int:
    sink: list = []
    _out({"ok": True, "results": dispatch_pending(fixed=ns.fixed, sink=sink), "sink": sink})
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ccctl")
    p.add_argument("--principal", required=True)
    p.add_argument("--source-ip", default="127.0.0.1")
    p.add_argument("--mfa", action="store_true")
    p.add_argument("--fixed", action="store_true", help=argparse.SUPPRESS)
    sp = p.add_subparsers(dest="cmd", required=True)

    c = sp.add_parser("clone")
    c.add_argument("repo")
    c.add_argument("dest")
    c.set_defaults(func=cmd_clone)

    c = sp.add_parser("push")
    c.add_argument("repo")
    c.add_argument("worktree")
    c.add_argument("branch")
    c.set_defaults(func=cmd_push)

    c = sp.add_parser("pr")
    c.add_argument("repo")
    c.add_argument("--source", required=True)
    c.add_argument("--dest", required=True)
    c.set_defaults(func=cmd_pr)

    c = sp.add_parser("approve")
    c.add_argument("repo")
    c.add_argument("pr_id")
    c.set_defaults(func=cmd_approve)

    c = sp.add_parser("merge")
    c.add_argument("repo")
    c.add_argument("pr_id")
    c.set_defaults(func=cmd_merge)

    c = sp.add_parser("deliver")
    c.add_argument("repo")
    c.add_argument("ref")
    c.set_defaults(func=cmd_deliver)

    c = sp.add_parser("simulate")
    c.add_argument("repo")
    c.add_argument("action")
    c.add_argument("ref")
    c.set_defaults(func=cmd_simulate)

    c = sp.add_parser("metrics")
    c.set_defaults(func=cmd_metrics)

    c = sp.add_parser("dispatch-webhooks")
    c.set_defaults(func=cmd_dispatch)

    c = sp.add_parser("platform-job")
    c.set_defaults(func=cmd_platform_job)
    return p


def cmd_platform_job(ns: argparse.Namespace) -> int:
    from cc.platform_jobs import nightly

    _out(nightly())
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    ns = parser.parse_args(argv)
    try:
        return int(ns.func(ns))
    except CcError as exc:
        _err(exc)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"error": "InternalError", "message": str(exc)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
