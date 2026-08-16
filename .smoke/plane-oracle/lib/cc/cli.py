"""Operator command line.

Every subcommand prints exactly one JSON object on stdout when it succeeds and
one JSON error envelope on stderr with exit status 1 when it fails.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from cc import VERSION
from cc.audit import query as audit_query
from cc.errors import CcError, as_cc_error
from cc.home import bare_repo_path, ensure_layout
from cc.iam.actions import GET_REPOSITORY, GIT_PULL, GIT_PUSH, QUERY_AUTHZ_LOG
from cc.iam.actions import CREATE_PULL_REQUEST, UPDATE_APPROVAL_STATE
from cc.iam.eval import authorize
from cc.iam.policy import describe_attachments
from cc.pipelines import bindings, deliver as delivery
from cc.prs import approvals, merge as merge_fence, store
from cc.repos import catalog, refs
from cc.repos.gitops import clone as git_clone, push_head
from cc.seed import bootstrap
from cc.webhooks import dispatch as drain


def _emit(payload: dict[str, Any], pretty: bool = False) -> int:
    if pretty:
        sys.stdout.write(json.dumps(payload, indent=2, sort_keys=False) + "\n")
    else:
        sys.stdout.write(json.dumps(payload, separators=(",", ":"), sort_keys=False) + "\n")
    return 0


def _mfa_flag(args: argparse.Namespace) -> bool | None:
    if getattr(args, "mfa", False):
        return True
    if getattr(args, "no_mfa", False):
        return False
    return None


def cmd_init(args: argparse.Namespace) -> dict[str, Any]:
    """Bootstrap repositories and mutable state for this root."""
    return bootstrap(force=bool(args.force))


def cmd_whoami(args: argparse.Namespace) -> dict[str, Any]:
    """Report the calling principal's policy attachments."""
    return {"ok": True, "version": VERSION, **describe_attachments(args.principal)}


def cmd_repos_list(args: argparse.Namespace) -> dict[str, Any]:
    """List the repositories whose metadata the caller may read."""
    visible = catalog.visible_to(args.principal, args.source_ip)
    return {"ok": True, "count": len(visible), "repos": visible}


def cmd_repos_refs(args: argparse.Namespace) -> dict[str, Any]:
    """Show branch state for one repository."""
    catalog.get(args.repo)
    authorize(
        args.principal,
        GET_REPOSITORY,
        args.repo,
        mfa=_mfa_flag(args),
        source_ip=args.source_ip,
    )
    return {"ok": True, **refs.describe(args.repo)}


def cmd_clone(args: argparse.Namespace) -> dict[str, Any]:
    """Clone one repository into a new working tree."""
    entry = catalog.get(args.repo)
    authorize(
        args.principal,
        GIT_PULL,
        args.repo,
        ref=entry.default_branch,
        mfa=_mfa_flag(args),
        source_ip=args.source_ip,
    )
    commit = git_clone(bare_repo_path(args.repo), Path(args.dest))
    return {
        "ok": True,
        "repo": args.repo,
        "dest": str(Path(args.dest)),
        "ref": entry.default_branch,
        "commit": commit,
    }


def cmd_push(args: argparse.Namespace) -> dict[str, Any]:
    """Update one branch of a repository from a working tree."""
    catalog.get(args.repo)
    target = refs.full_ref(args.branch)
    authorize(
        args.principal,
        GIT_PUSH,
        args.repo,
        ref=target,
        mfa=_mfa_flag(args),
        source_ip=args.source_ip,
    )
    refs.assert_push_allowed(args.repo, target)
    commit = push_head(Path(args.worktree), bare_repo_path(args.repo), target)
    return {"ok": True, "repo": args.repo, "ref": target, "commit": commit}


def cmd_pr(args: argparse.Namespace) -> dict[str, Any]:
    """Open a pull request between two refs."""
    catalog.get(args.repo)
    dest = refs.full_ref(args.dest)
    authorize(
        args.principal,
        CREATE_PULL_REQUEST,
        args.repo,
        ref=dest,
        mfa=_mfa_flag(args),
        source_ip=args.source_ip,
    )
    request = store.create(args.repo, args.source, args.dest, args.principal)
    return {"ok": True, "pr_id": request.pr_id, "pr": request.as_dict()}


def cmd_approve(args: argparse.Namespace) -> dict[str, Any]:
    """Stamp one open pull request."""
    request = store.require_open(args.pr_id)
    authorize(
        args.principal,
        UPDATE_APPROVAL_STATE,
        request.repo,
        ref=request.dest,
        mfa=_mfa_flag(args),
        source_ip=args.source_ip,
    )
    updated = store.add_approval(args.pr_id, args.principal)
    return {
        "ok": True,
        "pr_id": updated.pr_id,
        "approvals": sorted(updated.approvals),
        "quorum": approvals.status(updated),
    }


def cmd_merge(args: argparse.Namespace) -> dict[str, Any]:
    """Land one pull request onto its destination ref."""
    return merge_fence.merge_pull_request(
        args.principal,
        args.repo,
        args.pr_id,
        mfa=_mfa_flag(args),
        source_ip=args.source_ip,
    )


def cmd_pr_status(args: argparse.Namespace) -> dict[str, Any]:
    """Report what a merge of this pull request would do."""
    catalog.get(args.repo)
    return {"ok": True, **merge_fence.preview(args.repo, args.pr_id)}


def cmd_deliver(args: argparse.Namespace) -> dict[str, Any]:
    """Start every enabled pipeline bound to a repository ref."""
    return delivery.deliver(
        args.principal,
        args.repo,
        args.ref,
        mfa=_mfa_flag(args),
        source_ip=args.source_ip,
    )


def cmd_journal(args: argparse.Namespace) -> dict[str, Any]:
    """Read the trigger journal."""
    rows = delivery.journal()
    if args.repo:
        catalog.get(args.repo)
        rows = [row for row in rows if row.get("repo") == args.repo]
    return {"ok": True, "count": len(rows), "rows": rows}


def cmd_pipelines(args: argparse.Namespace) -> dict[str, Any]:
    """Show pipeline bindings for one repository."""
    catalog.get(args.repo)
    return {"ok": True, **bindings.describe(args.repo)}


def cmd_webhook_outbox(args: argparse.Namespace) -> dict[str, Any]:
    """Read the webhook outbox."""
    return drain.list_outbox(
        args.principal,
        event=args.event,
        mfa=_mfa_flag(args),
        source_ip=args.source_ip,
    )


def cmd_webhook_dispatch(args: argparse.Namespace) -> dict[str, Any]:
    """Attempt every due outbox row once at this tick."""
    return drain.dispatch_once(
        args.principal,
        args.tick,
        mfa=_mfa_flag(args),
        source_ip=args.source_ip,
    )


def cmd_audit_query(args: argparse.Namespace) -> dict[str, Any]:
    """Read recorded authorization decisions."""
    authorize(
        args.principal,
        QUERY_AUTHZ_LOG,
        "*",
        mfa=_mfa_flag(args),
        source_ip=args.source_ip,
    )
    return audit_query.query(
        principal=args.for_principal,
        action=args.action,
        repo=args.repo,
        decision=args.decision,
        limit=args.limit,
    )


def build_parser() -> argparse.ArgumentParser:
    """Assemble the operator command surface."""
    parser = argparse.ArgumentParser(prog="ccctl", description="CodeCommit control plane operator")
    parser.add_argument("--principal", default="", help="calling principal id")
    parser.add_argument("--mfa", action="store_true", help="assert that MFA is present")
    parser.add_argument("--no-mfa", action="store_true", help="assert that MFA is absent")
    parser.add_argument("--source-ip", default=None, help="source address of the caller")
    parser.add_argument("--pretty", action="store_true", help="indent the JSON result")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="bootstrap repositories and state")
    init.add_argument("--force", action="store_true", help="re-seed repositories that exist")
    init.set_defaults(handler=cmd_init)

    whoami = sub.add_parser("whoami", help="show policy attachments")
    whoami.set_defaults(handler=cmd_whoami)

    repos = sub.add_parser("repos", help="repository catalog")
    repos_sub = repos.add_subparsers(dest="repos_command", required=True)
    repos_list = repos_sub.add_parser("list", help="list readable repositories")
    repos_list.set_defaults(handler=cmd_repos_list)
    repos_refs = repos_sub.add_parser("refs", help="show branch state")
    repos_refs.add_argument("repo")
    repos_refs.set_defaults(handler=cmd_repos_refs)

    clone = sub.add_parser("clone", help="clone a repository")
    clone.add_argument("repo")
    clone.add_argument("dest")
    clone.set_defaults(handler=cmd_clone)

    push = sub.add_parser("push", help="update a branch from a working tree")
    push.add_argument("repo")
    push.add_argument("worktree")
    push.add_argument("branch")
    push.set_defaults(handler=cmd_push)

    pull_request = sub.add_parser("pr", help="open a pull request")
    pull_request.add_argument("repo")
    pull_request.add_argument("--source", required=True)
    pull_request.add_argument("--dest", required=True)
    pull_request.set_defaults(handler=cmd_pr)

    approve = sub.add_parser("approve", help="stamp a pull request")
    approve.add_argument("repo")
    approve.add_argument("pr_id", type=int)
    approve.set_defaults(handler=cmd_approve)

    merge = sub.add_parser("merge", help="land a pull request")
    merge.add_argument("repo")
    merge.add_argument("pr_id", type=int)
    merge.set_defaults(handler=cmd_merge)

    status = sub.add_parser("pr-status", help="preview a merge")
    status.add_argument("repo")
    status.add_argument("pr_id", type=int)
    status.set_defaults(handler=cmd_pr_status)

    deliver = sub.add_parser("deliver", help="start bound pipelines for a ref")
    deliver.add_argument("repo")
    deliver.add_argument("ref")
    deliver.set_defaults(handler=cmd_deliver)

    journal = sub.add_parser("journal", help="read the trigger journal")
    journal.add_argument("--repo", default=None)
    journal.set_defaults(handler=cmd_journal)

    pipelines = sub.add_parser("pipelines", help="show pipeline bindings")
    pipelines.add_argument("repo")
    pipelines.set_defaults(handler=cmd_pipelines)

    webhook = sub.add_parser("webhook", help="webhook outbox")
    webhook_sub = webhook.add_subparsers(dest="webhook_command", required=True)
    webhook_list = webhook_sub.add_parser("outbox", help="read outbox rows")
    webhook_list.add_argument("--event", default=None)
    webhook_list.set_defaults(handler=cmd_webhook_outbox)
    webhook_run = webhook_sub.add_parser("dispatch", help="drain due outbox rows")
    webhook_run.add_argument("--tick", type=int, required=True)
    webhook_run.set_defaults(handler=cmd_webhook_dispatch)

    audit = sub.add_parser("audit", help="recorded authorization decisions")
    audit_sub = audit.add_subparsers(dest="audit_command", required=True)
    audit_read = audit_sub.add_parser("query", help="filter recorded decisions")
    audit_read.add_argument("--for-principal", dest="for_principal", default=None)
    audit_read.add_argument("--action", default=None)
    audit_read.add_argument("--repo", default=None)
    audit_read.add_argument("--decision", default=None, choices=["allow", "deny"])
    audit_read.add_argument("--limit", type=int, default=0)
    audit_read.set_defaults(handler=cmd_audit_query)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run one operator command."""
    parser = build_parser()
    args = parser.parse_args(argv)
    ensure_layout()
    try:
        payload = args.handler(args)
    except CcError as exc:
        sys.stderr.write(json.dumps(exc.payload(), separators=(",", ":")) + "\n")
        return 1
    except Exception as exc:  # noqa: BLE001 - report unexpected faults as JSON too
        sys.stderr.write(json.dumps(as_cc_error(exc).payload(), separators=(",", ":")) + "\n")
        return 1
    return _emit(payload, pretty=bool(args.pretty))
