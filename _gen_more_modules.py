from pathlib import Path

lib = Path("codecommit-iam-merge-fence/environment/codecommit/lib/cc")

MODULES = {
    "policy_admin.py": r'''
from __future__ import annotations

import json
from typing import Any

from cc import home
from cc.services.validators import validate_principal
from cc.util import dump_json, load_json


def list_policies() -> list[str]:
    return sorted(p.stem for p in home.policies_dir().glob("*.json"))


def read_policy(policy_id: str) -> dict[str, Any]:
    path = home.policies_dir() / f"{policy_id}.json"
    if not path.exists():
        raise FileNotFoundError(policy_id)
    return json.loads(path.read_text(encoding="utf-8"))


def write_policy(policy_id: str, document: dict[str, Any]) -> None:
    if "Statement" not in document or not isinstance(document["Statement"], list):
        raise ValueError("policy requires Statement list")
    for stmt in document["Statement"]:
        for key in ("Effect", "Action", "Resource"):
            if key not in stmt:
                raise ValueError(f"statement missing {key}")
    path = home.policies_dir() / f"{policy_id}.json"
    dump_json(path, document)


def attach_policy(principal: str, policy_id: str) -> dict[str, Any]:
    validate_principal(principal)
    data = load_json(home.principals_path(), {})
    entry = data.setdefault(principal, {"policies": [], "roles": []})
    pols = list(entry.get("policies") or [])
    if policy_id not in pols:
        pols.append(policy_id)
    entry["policies"] = pols
    data[principal] = entry
    dump_json(home.principals_path(), data)
    return entry


def detach_policy(principal: str, policy_id: str) -> dict[str, Any]:
    validate_principal(principal)
    data = load_json(home.principals_path(), {})
    entry = data.get(principal) or {"policies": [], "roles": []}
    entry["policies"] = [p for p in (entry.get("policies") or []) if p != policy_id]
    data[principal] = entry
    dump_json(home.principals_path(), data)
    return entry


def principals() -> dict[str, Any]:
    return load_json(home.principals_path(), {})


def diff_attachments(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    added = {k: after[k] for k in after.keys() - before.keys()}
    removed = {k: before[k] for k in before.keys() - after.keys()}
    changed = {}
    for k in before.keys() & after.keys():
        if before[k] != after[k]:
            changed[k] = {"before": before[k], "after": after[k]}
    return {"added": added, "removed": removed, "changed": changed}
''',
    "repo_lifecycle.py": r'''
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

from cc.repos import catalog, gitops
from cc.services.validators import validate_repo_name
from cc.util import run_git


def create_repo(name: str, *, description: str = "", default_branch: str = "main") -> dict[str, Any]:
    validate_repo_name(name)
    entry = catalog.upsert_repo(name, default_branch=default_branch, description=description)
    gitops.ensure_bare(name)
    return entry


def seed_readme(name: str, text: str = "ledger mainline\n") -> str:
    gitops.ensure_bare(name)
    with tempfile.TemporaryDirectory() as td:
        wt = Path(td) / "wt"
        gitops.clone(name, wt)
        (wt / "README").write_text(text, encoding="utf-8")
        run_git(["add", "README"], cwd=wt)
        run_git(["-c", "commit.gpgsign=false", "commit", "-m", "initial"], cwd=wt)
        return gitops.push(name, wt, "main")


def delete_repo_files(name: str) -> None:
    bare = gitops.ensure_bare(name)
    if bare.exists():
        shutil.rmtree(bare)
    data = catalog.store().read()
    data.get("repos", {}).pop(name, None)
    catalog.store().write(data)


def repo_status(name: str) -> dict[str, Any]:
    entry = catalog.require_repo(name)
    tip = None
    err = None
    try:
        tip = gitops.ref_commit(name, entry.get("default_branch") or "main")
    except Exception as exc:  # noqa: BLE001
        err = str(exc)
    return {"repo": entry, "tip": tip, "error": err}


def list_detailed() -> list[dict[str, Any]]:
    return [repo_status(n) for n in catalog.list_repos()]
''',
    "approval_engine.py": r'''
from __future__ import annotations

from typing import Any

from cc import home
from cc.prs import approvals, store as pr_store
from cc.services.validators import validate_approval_rule
from cc.util import dump_json, full_ref, load_json


def load_all_rules() -> list[dict[str, Any]]:
    return list(load_json(home.approval_rules_path(), {"rules": []}).get("rules") or [])


def save_rules(rules: list[dict[str, Any]]) -> None:
    cleaned = [validate_approval_rule(r) for r in rules]
    dump_json(home.approval_rules_path(), {"rules": cleaned})


def upsert_rule(rule: dict[str, Any]) -> dict[str, Any]:
    rule = validate_approval_rule(rule)
    rules = load_all_rules()
    out: list[dict[str, Any]] = []
    replaced = False
    for r in rules:
        if r.get("repo") == rule["repo"] and full_ref(str(r.get("destination"))) == rule["destination"]:
            out.append(rule)
            replaced = True
        else:
            out.append(r)
    if not replaced:
        out.append(rule)
    save_rules(out)
    return rule


def evaluate_pr(pr_id: int, *, fixed: bool = False) -> dict[str, Any]:
    pr = pr_store.get(pr_id)
    rule = approvals.rule_for(pr.repo, pr.dest)
    distinct = approvals.distinct_pool_approvals(pr_id) if fixed else list(pr.approvals)
    required = int(rule.get("required") or 1) if fixed else 1
    return {
        "pr_id": pr_id,
        "author": pr.author,
        "approvals": list(pr.approvals),
        "distinct_pool": distinct,
        "required": required,
        "pool": list(rule.get("pool") or []),
        "satisfied": approvals.quorum_satisfied(pr_id, fixed=fixed),
    }


def missing_approvers(pr_id: int) -> list[str]:
    pr = pr_store.get(pr_id)
    rule = approvals.rule_for(pr.repo, pr.dest)
    pool = list(rule.get("pool") or [])
    have = set(approvals.distinct_pool_approvals(pr_id))
    return [p for p in pool if p not in have and p != pr.author]
''',
    "ref_guard.py": r'''
from __future__ import annotations

from typing import Any

from cc.util import full_ref, short_ref

PROTECTED = {"refs/heads/main", "refs/heads/release"}


def is_protected(ref: str) -> bool:
    return full_ref(ref) in PROTECTED


def classify_ref(ref: str) -> dict[str, Any]:
    r = full_ref(ref)
    kind = "branch"
    if r.startswith("refs/tags/"):
        kind = "tag"
    elif r.startswith("refs/heads/dev/"):
        kind = "feature"
    elif r in PROTECTED:
        kind = "protected"
    return {"ref": r, "short": short_ref(r), "kind": kind, "protected": is_protected(r)}


def assert_feature_owner(ref: str, principal: str) -> None:
    r = full_ref(ref)
    if not r.startswith("refs/heads/dev/"):
        return
    # naming convention only; IAM remains authoritative
    _ = (r, principal)


def batch_classify(refs: list[str]) -> list[dict[str, Any]]:
    return [classify_ref(r) for r in refs]
''',
    "state_recovery.py": r'''
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from cc import home
from cc.util import dump_json, load_json, read_jsonl


def check_paths() -> dict[str, Any]:
    paths = {
        "principals": home.principals_path(),
        "approval_rules": home.approval_rules_path(),
        "pipelines": home.pipelines_path(),
        "webhooks": home.webhooks_path(),
        "catalog": home.catalog_path(),
        "prs": home.prs_path(),
        "triggers": home.triggers_path(),
        "audit": home.audit_path(),
        "outbox": home.outbox_path(),
    }
    return {k: {"path": str(v), "exists": v.exists()} for k, v in paths.items()}


def rebuild_catalog_from_repos() -> dict[str, Any]:
    repos: dict[str, Any] = {}
    for bare in home.repos_dir().glob("*.git"):
        name = bare.name[:-4] if bare.name.endswith(".git") else bare.name
        repos[name] = {
            "name": name,
            "default_branch": "main",
            "description": "recovered",
            "arn": f"arn:local:codecommit:local:000000000000:{name}",
        }
    dump_json(home.catalog_path(), {"repos": repos})
    return {"repos": sorted(repos)}


def compact_jsonl(path: Path) -> int:
    rows = read_jsonl(path)
    seen: set[Any] = set()
    out: list[dict[str, Any]] = []
    for row in reversed(rows):
        key = row.get("event_id") or id(row)
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
    out.reverse()
    path.write_text(
        "".join(json.dumps(r, separators=(",", ":")) + "\n" for r in out),
        encoding="utf-8",
    )
    return len(out)


def health() -> dict[str, Any]:
    home.ensure_layout()
    return {"layout": True, "paths": check_paths(), "catalog": load_json(home.catalog_path(), {"repos": {}})}
''',
    "config_schema.py": r'''
from __future__ import annotations

from typing import Any

RULE_REQUIRED = ["repo", "destination", "required", "pool"]
BINDING_REQUIRED = ["repo", "ref", "pipeline"]
WEBHOOK_REQUIRED = ["id", "url"]


def validate_object(obj: dict[str, Any], required: list[str]) -> list[str]:
    return [k for k in required if k not in obj]


def validate_principals_doc(doc: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    for name, entry in doc.items():
        if not isinstance(entry, dict):
            errs.append(f"{name}: not an object")
            continue
        errs.extend(f"{name}.{e}" for e in validate_object(entry, ["policies"]))
    return errs


def validate_rules_doc(doc: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    for i, rule in enumerate(doc.get("rules") or []):
        missing = validate_object(rule, RULE_REQUIRED)
        errs.extend(f"rules[{i}].{m}" for m in missing)
    return errs


def validate_pipelines_doc(doc: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    for i, b in enumerate(doc.get("bindings") or []):
        missing = validate_object(b, BINDING_REQUIRED)
        errs.extend(f"bindings[{i}].{m}" for m in missing)
    return errs


def validate_webhooks_doc(doc: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    for i, w in enumerate(doc.get("webhooks") or []):
        missing = validate_object(w, WEBHOOK_REQUIRED)
        errs.extend(f"webhooks[{i}].{m}" for m in missing)
    return errs


def validate_all(
    principals: dict[str, Any],
    rules: dict[str, Any],
    pipelines: dict[str, Any],
    webhooks: dict[str, Any],
) -> dict[str, list[str]]:
    return {
        "principals": validate_principals_doc(principals),
        "rules": validate_rules_doc(rules),
        "pipelines": validate_pipelines_doc(pipelines),
        "webhooks": validate_webhooks_doc(webhooks),
    }
''',
    "batch_ops.py": r'''
from __future__ import annotations

from typing import Any

from cc.iam import actions as iam_actions
from cc.iam.eval import explain
from cc.services import authz_gateway

DEFAULT_ACTIONS = [iam_actions.GIT_PULL, iam_actions.GIT_PUSH, iam_actions.MERGE_FF]


def explain_matrix(
    principal: str,
    repo: str,
    refs: list[str],
    actions: list[str],
    *,
    mfa: bool = False,
    source_ip: str = "127.0.0.1",
    fixed: bool = False,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for ref in refs:
        for action in actions:
            out.append(
                explain(
                    principal,
                    action,
                    repo,
                    ref,
                    mfa=mfa,
                    source_ip=source_ip,
                    fixed=fixed,
                )
            )
    return out


def try_authorize_many(requests: list[dict[str, Any]], *, fixed: bool = False) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for req in requests:
        try:
            ctx = authz_gateway.gated_authorize(
                req["principal"],
                req["action"],
                req["repo"],
                req["reference"],
                mfa=bool(req.get("mfa")),
                source_ip=str(req.get("source_ip") or "127.0.0.1"),
                fixed=fixed,
            )
            results.append({"ok": True, "resource": ctx.resource_arn})
        except Exception as exc:  # noqa: BLE001
            results.append({"ok": False, "error": str(exc)})
    return results
''',
}

for name, body in MODULES.items():
    (lib / name).write_text(body.lstrip("\n"), encoding="utf-8")
print("wrote", len(MODULES))
