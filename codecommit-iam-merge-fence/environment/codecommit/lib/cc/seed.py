from __future__ import annotations

import json
from pathlib import Path

from cc import home
from cc.repo_lifecycle import create_repo, seed_readme
from cc.util import dump_json


ARN = "arn:local:codecommit:local:000000000000:ledger"
SANDBOX = "arn:local:codecommit:local:000000000000:sandbox"


def _policy(statements: list[dict]) -> dict:
    return {"Version": "2012-10-17", "Statement": statements}


def write_policies() -> None:
    home.ensure_layout()
    policies = {
        "developer": _policy(
            [
                {
                    "Sid": "DevPull",
                    "Effect": "Allow",
                    "Action": "codecommit:GitPull",
                    "Resource": ARN,
                },
                {
                    "Sid": "DevPushMain",
                    "Effect": "Allow",
                    "Action": "codecommit:GitPush",
                    "Resource": ARN,
                    "Condition": {
                        "StringEquals": {"codecommit:References": "refs/heads/main"},
                        "Bool": {"aws:MultiFactorAuthPresent": "true"},
                        "IpAddress": {"aws:SourceIp": "10.8.0.0/16"},
                    },
                },
                {
                    "Sid": "ReleaseAllow",
                    "Effect": "Allow",
                    "Action": "codecommit:GitPush",
                    "Resource": ARN,
                    "Condition": {"StringEquals": {"codecommit:References": "refs/heads/release"}},
                },
                {
                    "Sid": "ReleaseDeny",
                    "Effect": "Deny",
                    "Action": "codecommit:GitPush",
                    "Resource": ARN,
                    "Condition": {"StringEquals": {"codecommit:References": "refs/heads/release"}},
                },
            ]
        ),
        "alice-dev": _policy(
            [
                {
                    "Sid": "AliceFeature",
                    "Effect": "Allow",
                    "Action": "codecommit:GitPush",
                    "Resource": ARN,
                    "Condition": {
                        "StringEquals": {
                            "codecommit:References": ["refs/heads/dev/alice"]
                        }
                    },
                }
            ]
        ),
        "ben-dev": _policy(
            [
                {
                    "Sid": "BenFeature",
                    "Effect": "Allow",
                    "Action": "codecommit:GitPush",
                    "Resource": ARN,
                    "Condition": {
                        "StringEquals": {
                            "codecommit:References": ["refs/heads/dev/ben"]
                        }
                    },
                }
            ]
        ),
        "reviewer": _policy(
            [
                {
                    "Sid": "RevPull",
                    "Effect": "Allow",
                    "Action": "codecommit:GitPull",
                    "Resource": ARN,
                },
                {
                    "Sid": "RevMerge",
                    "Effect": "Allow",
                    "Action": "codecommit:MergePullRequestByFastForward",
                    "Resource": ARN,
                    "Condition": {"IpAddress": {"aws:SourceIp": "10.8.0.0/16"}},
                },
            ]
        ),
        "pull-only": _policy(
            [
                {
                    "Sid": "InternPull",
                    "Effect": "Allow",
                    "Action": "codecommit:GitPull",
                    "Resource": ARN,
                }
            ]
        ),
        "pipeline": _policy(
            [
                {
                    "Sid": "PipePull",
                    "Effect": "Allow",
                    "Action": "codecommit:GitPull",
                    "Resource": ARN,
                }
            ]
        ),
        "sandbox-star": _policy(
            [
                {
                    "Sid": "SandboxStar",
                    "Effect": "Allow",
                    "Action": "*",
                    "Resource": SANDBOX,
                }
            ]
        ),
    }
    # Expand with a few differentiated multi-repo policy fragments
    for i, team in enumerate(("payments", "ledger-aux", "risk-ops", "treasury"), start=1):
        policies[f"team-fragment-{i:02d}"] = _policy(
            [
                {
                    "Sid": f"FragPull{i:02d}",
                    "Effect": "Allow",
                    "Action": "codecommit:GitPull",
                    "Resource": f"arn:local:codecommit:local:000000000000:team{i:02d}",
                },
                {
                    "Sid": f"FragPush{i:02d}",
                    "Effect": "Allow",
                    "Action": "codecommit:GitPush",
                    "Resource": f"arn:local:codecommit:local:000000000000:team{i:02d}",
                    "Condition": {
                        "StringEquals": {
                            "codecommit:References": f"refs/heads/dev/{team}"
                        },
                    },
                },
            ]
        )
    for name, doc in policies.items():
        dump_json(home.policies_dir() / f"{name}.json", doc)


def write_ops() -> None:
    dump_json(
        home.principals_path(),
        {
            "dev-alice": {"policies": ["developer", "alice-dev", "sandbox-star"], "roles": ["developer"]},
            "dev-ben": {"policies": ["developer", "ben-dev"], "roles": ["developer"]},
            "rev-a": {"policies": ["reviewer"], "roles": ["reviewer"]},
            "rev-b": {"policies": ["reviewer"], "roles": ["reviewer"]},
            "intern": {"policies": ["pull-only"], "roles": ["intern"]},
            "pipeline-bot": {"policies": ["pipeline"], "roles": ["automation"]},
        },
    )
    dump_json(
        home.approval_rules_path(),
        {
            "rules": [
                {
                    "repo": "ledger",
                    "destination": "refs/heads/main",
                    "required": 2,
                    "pool": ["rev-a", "rev-b"],
                }
            ]
        },
    )
    dump_json(
        home.pipelines_path(),
        {"bindings": [{"repo": "ledger", "ref": "refs/heads/main", "pipeline": "settle-prod"}]},
    )
    dump_json(
        home.webhooks_path(),
        {
            "webhooks": [
                {
                    "id": "wh-settle",
                    "url": "http://127.0.0.1:9/hooks/settle",
                    "pipeline": "settle-prod",
                    "secret": "settle",
                }
            ]
        },
    )
    from cc.branch_protection import DEFAULT_RULES, save_rules

    save_rules(DEFAULT_RULES)
    (home.ops_dir() / "handoff.md").write_text(
        "Platform security, Monday.\n\n"
        "CodeCommit IAM in the lab stand-in is not the same evaluator we run in prod. "
        "Alice can clone ledger, then land that commit on main from the office range without MFA. "
        "One reviewer stamp plus a merge commit still ships when main has moved. "
        "Two deliver calls on the same head both hit the pipeline journal, and the webhook outbox "
        "is not getting rows.\n\n"
        "Policies under policies/ and attachments in ops/principals.json are the evaluated source of truth. "
        "I dumped last night's decisions under log/. Repos stay bare under var/repos.\n",
        encoding="utf-8",
    )


def write_log_sample() -> None:
    home.log_dir().mkdir(parents=True, exist_ok=True)
    rows = [
        {"principal": "dev-alice", "action": "codecommit:GitPush", "allowed": True, "note": "suspicious no-mfa"},
        {"principal": "dev-alice", "action": "codecommit:GitPull", "allowed": True, "note": "clone ok"},
        {"principal": "pipeline-bot", "action": "deliver", "allowed": True, "note": "duplicate fire"},
    ]
    path = home.log_dir() / "authz.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def seed_repos() -> None:
    create_repo("ledger", description="settlement ledger")
    create_repo("sandbox", description="playground")
    for i in range(1, 16):
        create_repo(f"team{i:02d}", description=f"team {i:02d} service")
    seed_readme("ledger")
    seed_readme("sandbox", "sandbox\n")


def main() -> None:
    home.ensure_layout()
    write_policies()
    write_ops()
    write_log_sample()
    seed_repos()
    print(json.dumps({"ok": True, "repos": ["ledger", "sandbox"], "policies": len(list(home.policies_dir().glob('*.json')))}))


if __name__ == "__main__":
    main()
