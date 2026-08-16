from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cc.errors import CcError
from cc.integration_facade import ControlPlane
from cc.ops_console import access_preview, platform_report, write_report
from cc.pipeline_admin import journal_for, load_bindings, pipeline_names
from cc.repo_lifecycle import list_detailed
from cc.services import metrics, policy_sim
from cc.state_recovery import health, rebuild_catalog_from_repos
from cc.webhook_admin import delivery_stats, load_webhooks


def _out(obj: object) -> None:
    print(json.dumps(obj, separators=(",", ":")))


def _err(exc: CcError) -> None:
    print(exc.to_json(), file=sys.stderr)


def _plane(ns: argparse.Namespace) -> ControlPlane:
    return ControlPlane(fixed=bool(ns.fixed))


def cmd_clone(ns: argparse.Namespace) -> int:
    _plane(ns).clone(ns.principal, ns.repo, Path(ns.dest), mfa=ns.mfa, source_ip=ns.source_ip)
    return 0


def cmd_push(ns: argparse.Namespace) -> int:
    _out(
        _plane(ns).push(
            ns.principal,
            ns.repo,
            Path(ns.worktree),
            ns.branch,
            mfa=ns.mfa,
            source_ip=ns.source_ip,
        )
    )
    return 0


def cmd_pr(ns: argparse.Namespace) -> int:
    _out(
        _plane(ns).open_pr(
            ns.principal,
            ns.repo,
            ns.source,
            ns.dest,
            mfa=ns.mfa,
            source_ip=ns.source_ip,
        )
    )
    return 0


def cmd_approve(ns: argparse.Namespace) -> int:
    _out(_plane(ns).approve(ns.principal, int(ns.pr_id)))
    return 0


def cmd_merge(ns: argparse.Namespace) -> int:
    _out(
        _plane(ns).merge(
            ns.principal,
            int(ns.pr_id),
            mfa=ns.mfa,
            source_ip=ns.source_ip,
        )
    )
    return 0


def cmd_deliver(ns: argparse.Namespace) -> int:
    _out(_plane(ns).deliver(ns.repo, ns.ref))
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
    _out({"ok": True, "results": _plane(ns).dispatch()})
    return 0


def cmd_report(ns: argparse.Namespace) -> int:
    if ns.output:
        path = write_report(Path(ns.output))
        _out({"ok": True, "path": str(path)})
    else:
        _out(platform_report())
    return 0


def cmd_ops_health(ns: argparse.Namespace) -> int:
    _out(health())
    return 0


def cmd_access_preview(ns: argparse.Namespace) -> int:
    refs = [ns.ref] if ns.ref else ["refs/heads/main", "refs/heads/dev/alice"]
    _out(
        access_preview(
            ns.principal,
            ns.repo,
            refs,
            mfa=ns.mfa,
            source_ip=ns.source_ip,
        )
    )
    return 0


def cmd_recover_catalog(ns: argparse.Namespace) -> int:
    _out(
        {
            "ok": True,
            "rebuild": rebuild_catalog_from_repos(),
            "repos": list_detailed(),
        }
    )
    return 0


def cmd_webhooks(ns: argparse.Namespace) -> int:
    _out({"webhooks": load_webhooks(), "stats": delivery_stats()})
    return 0


def cmd_pipelines(ns: argparse.Namespace) -> int:
    _out(
        {
            "bindings": load_bindings(),
            "pipelines": pipeline_names(),
            "ledger_journal": journal_for("ledger"),
        }
    )
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

    c = sp.add_parser("report")
    c.add_argument("--output", default="")
    c.set_defaults(func=cmd_report)

    c = sp.add_parser("ops-health")
    c.set_defaults(func=cmd_ops_health)

    c = sp.add_parser("access-preview")
    c.add_argument("repo")
    c.add_argument("--ref", default="")
    c.set_defaults(func=cmd_access_preview)

    c = sp.add_parser("recover-catalog")
    c.set_defaults(func=cmd_recover_catalog)

    c = sp.add_parser("webhooks")
    c.set_defaults(func=cmd_webhooks)

    c = sp.add_parser("pipelines")
    c.set_defaults(func=cmd_pipelines)
    return p


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
