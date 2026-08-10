from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cc.errors import CcError
from cc.gitops import clone, push
from cc.home import full_ref
from cc.iam import authorize
from cc.prs import approve, create, merge
from cc.trigger import deliver


def _out(payload: dict) -> int:
    sys.stdout.write(json.dumps(payload, separators=(",", ":")) + "\n")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ccctl")
    parser.add_argument("--principal", required=True)
    parser.add_argument("--mfa", action="store_true")
    parser.add_argument("--source-ip", default="127.0.0.1")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_clone = sub.add_parser("clone")
    p_clone.add_argument("repo")
    p_clone.add_argument("dest")

    p_push = sub.add_parser("push")
    p_push.add_argument("repo")
    p_push.add_argument("worktree")
    p_push.add_argument("branch")

    p_pr = sub.add_parser("pr")
    p_pr.add_argument("repo")
    p_pr.add_argument("--source", required=True)
    p_pr.add_argument("--dest", required=True)

    p_ap = sub.add_parser("approve")
    p_ap.add_argument("repo")
    p_ap.add_argument("pr_id", type=int)

    p_mg = sub.add_parser("merge")
    p_mg.add_argument("repo")
    p_mg.add_argument("pr_id", type=int)

    p_del = sub.add_parser("deliver")
    p_del.add_argument("repo")
    p_del.add_argument("ref")

    args = parser.parse_args(argv)
    try:
        p, mfa, ip = args.principal, bool(args.mfa), args.source_ip
        if args.cmd == "clone":
            authorize(p, "codecommit:GitPull", args.repo, "refs/heads/main", mfa, ip)
            clone(args.repo, Path(args.dest))
            return _out({"ok": True, "repo": args.repo, "dest": str(Path(args.dest))})
        if args.cmd == "push":
            ref = full_ref(args.branch)
            authorize(p, "codecommit:GitPush", args.repo, ref, mfa, ip)
            commit = push(args.repo, Path(args.worktree), args.branch)
            return _out({"ok": True, "repo": args.repo, "ref": ref, "commit": commit})
        if args.cmd == "pr":
            authorize(p, "codecommit:GitPull", args.repo, full_ref(args.source), mfa, ip)
            item = create(args.repo, args.source, args.dest, p)
            return _out(
                {
                    "ok": True,
                    "pr_id": item["pr_id"],
                    "source": item["source"],
                    "dest": item["dest"],
                    "source_commit": item["source_commit"],
                }
            )
        if args.cmd == "approve":
            item = approve(args.repo, args.pr_id, p)
            return _out({"ok": True, "pr_id": item["pr_id"], "approvals": list(item["approvals"])})
        if args.cmd == "merge":
            # peek dest from store after authorize using dest main default if missing
            from cc.prs import get

            item = get(args.repo, args.pr_id)
            authorize(p, "codecommit:MergePullRequestByFastForward", args.repo, item["dest"], mfa, ip)
            merged = merge(args.repo, args.pr_id)
            return _out(
                {
                    "ok": True,
                    "pr_id": merged["pr_id"],
                    "commit": merged["merged_commit"],
                    "fast_forward": True,
                }
            )
        if args.cmd == "deliver":
            return _out(deliver(args.repo, args.ref))
        raise CcError("ValidationException")
    except CcError as exc:
        sys.stderr.write(exc.to_json() + "\n")
        return 1
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(json.dumps({"error": "InternalError", "message": str(exc)}) + "\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
