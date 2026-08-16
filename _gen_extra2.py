from pathlib import Path

lib = Path("codecommit-iam-merge-fence/environment/codecommit/lib/cc")

# Large but reachable admin/reporting modules
(lib / "iam_report.py").write_text(
    '''from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from cc.iam import actions, policy
from cc.iam.eval import explain
from cc.policy_admin import list_policies, principals, read_policy
from cc.util import full_ref


def statement_index() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pid in list_policies():
        doc = read_policy(pid)
        for i, stmt in enumerate(doc.get("Statement") or []):
            rows.append(
                {
                    "policy": pid,
                    "index": i,
                    "sid": stmt.get("Sid"),
                    "effect": stmt.get("Effect"),
                    "action": stmt.get("Action"),
                    "resource": stmt.get("Resource"),
                    "has_condition": bool(stmt.get("Condition")),
                    "condition_ops": sorted((stmt.get("Condition") or {}).keys()),
                }
            )
    return rows


def action_coverage() -> dict[str, list[str]]:
    cov: dict[str, list[str]] = defaultdict(list)
    for row in statement_index():
        act = str(row.get("action"))
        if act in ("*", "codecommit:*"):
            for a in actions.ALL_ACTIONS:
                cov[a].append(str(row["policy"]))
        else:
            cov[act].append(str(row["policy"]))
    return {k: sorted(set(v)) for k, v in cov.items()}


def principals_by_action(action: str) -> list[str]:
    out: list[str] = []
    data = principals()
    for name, entry in data.items():
        for pid in entry.get("policies") or []:
            doc = read_policy(pid)
            for stmt in doc.get("Statement") or []:
                sa = str(stmt.get("Action"))
                if sa in (action, "*", "codecommit:*"):
                    out.append(name)
                    break
    return sorted(set(out))


def simulate_grid(
    principal: str,
    repo: str,
    refs: list[str],
    *,
    mfa: bool,
    source_ip: str,
    fixed: bool = False,
) -> dict[str, Any]:
    cells: list[dict[str, Any]] = []
    for ref in refs:
        for action in actions.ALL_ACTIONS:
            cells.append(
                explain(
                    principal,
                    action,
                    repo,
                    full_ref(ref),
                    mfa=mfa,
                    source_ip=source_ip,
                    fixed=fixed,
                )
            )
    allowed = sum(1 for c in cells if c.get("allowed"))
    return {"cells": cells, "allowed": allowed, "denied": len(cells) - allowed}


def effect_histogram() -> dict[str, int]:
    return dict(Counter(str(r.get("effect")) for r in statement_index()))


def condition_histogram() -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in statement_index():
        for op in row.get("condition_ops") or []:
            counts[str(op)] += 1
    return dict(counts)


def orphan_policies() -> list[str]:
    attached: set[str] = set()
    for entry in principals().values():
        attached.update(entry.get("policies") or [])
    return [p for p in list_policies() if p not in attached]


def duplicate_sids() -> list[dict[str, Any]]:
    seen: dict[str, list[str]] = defaultdict(list)
    for row in statement_index():
        sid = row.get("sid")
        if sid:
            seen[str(sid)].append(str(row["policy"]))
    return [{"sid": k, "policies": v} for k, v in seen.items() if len(v) > 1]


def resource_patterns() -> list[str]:
    return sorted({str(r.get("resource")) for r in statement_index()})


def attachment_matrix() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, entry in sorted(principals().items()):
        rows.append({"principal": name, "policies": list(entry.get("policies") or []), "count": len(entry.get("policies") or [])})
    return rows


def full_iam_report(principal: str, repo: str) -> dict[str, Any]:
    return {
        "statements": statement_index(),
        "coverage": action_coverage(),
        "effects": effect_histogram(),
        "conditions": condition_histogram(),
        "orphans": orphan_policies(),
        "resources": resource_patterns(),
        "attachments": attachment_matrix(),
        "grid_mfa_office": simulate_grid(principal, repo, ["main", "dev/alice", "release"], mfa=True, source_ip="10.8.12.4", fixed=True),
        "grid_no_mfa": simulate_grid(principal, repo, ["main"], mfa=False, source_ip="10.8.12.4", fixed=True),
    }
'''.lstrip(),
    encoding="utf-8",
)

(lib / "pipeline_admin.py").write_text(
    '''from __future__ import annotations

from typing import Any

from cc import home
from cc.pipelines import event_id as eid_mod
from cc.services.validators import validate_pipeline_binding
from cc.util import dump_json, full_ref, load_json


def load_bindings() -> list[dict[str, Any]]:
    return list(load_json(home.pipelines_path(), {"bindings": []}).get("bindings") or [])


def save_bindings(bindings: list[dict[str, Any]]) -> None:
    cleaned = [validate_pipeline_binding(b) for b in bindings]
    dump_json(home.pipelines_path(), {"bindings": cleaned})


def upsert_binding(binding: dict[str, Any]) -> dict[str, Any]:
    binding = validate_pipeline_binding(binding)
    rows = load_bindings()
    out: list[dict[str, Any]] = []
    replaced = False
    for row in rows:
        if row.get("repo") == binding["repo"] and full_ref(str(row.get("ref"))) == binding["ref"]:
            out.append(binding)
            replaced = True
        else:
            out.append(row)
    if not replaced:
        out.append(binding)
    save_bindings(out)
    return binding


def remove_binding(repo: str, ref: str) -> int:
    ref = full_ref(ref)
    before = load_bindings()
    after = [b for b in before if not (b.get("repo") == repo and full_ref(str(b.get("ref"))) == ref)]
    save_bindings(after)
    return len(before) - len(after)


def bindings_for_repo(repo: str) -> list[dict[str, Any]]:
    return [b for b in load_bindings() if b.get("repo") == repo]


def journal_for(repo: str, ref: str | None = None) -> list[dict[str, Any]]:
    rows = eid_mod.journal_rows()
    out = [r for r in rows if r.get("repo") == repo]
    if ref is not None:
        ref = full_ref(ref)
        out = [r for r in out if full_ref(str(r.get("ref"))) == ref]
    return out


def unique_event_ids() -> list[str]:
    return sorted({str(r.get("event_id")) for r in eid_mod.journal_rows()})


def detect_duplicate_event_ids() -> list[str]:
    seen: set[str] = set()
    dups: set[str] = set()
    for row in eid_mod.journal_rows():
        eid = str(row.get("event_id"))
        if eid in seen:
            dups.add(eid)
        seen.add(eid)
    return sorted(dups)


def pipeline_names() -> list[str]:
    return sorted({str(b.get("pipeline")) for b in load_bindings()})


def binding_conflicts() -> list[dict[str, Any]]:
    """Same repo/ref mapped to multiple pipelines is allowed; report multiplicity."""
    counts: dict[tuple[str, str], list[str]] = {}
    for b in load_bindings():
        key = (str(b.get("repo")), full_ref(str(b.get("ref"))))
        counts.setdefault(key, []).append(str(b.get("pipeline")))
    return [
        {"repo": k[0], "ref": k[1], "pipelines": v}
        for k, v in counts.items()
        if len(v) > 1
    ]
'''.lstrip(),
    encoding="utf-8",
)

(lib / "webhook_admin.py").write_text(
    '''from __future__ import annotations

from typing import Any

from cc import home
from cc.services.validators import validate_webhook
from cc.util import dump_json, load_json
from cc.webhooks import outbox, retry


def load_webhooks() -> list[dict[str, Any]]:
    return list(load_json(home.webhooks_path(), {"webhooks": []}).get("webhooks") or [])


def save_webhooks(rows: list[dict[str, Any]]) -> None:
    cleaned = [validate_webhook(w) for w in rows]
    dump_json(home.webhooks_path(), {"webhooks": cleaned})


def upsert_webhook(webhook: dict[str, Any]) -> dict[str, Any]:
    webhook = validate_webhook(webhook)
    rows = load_webhooks()
    out: list[dict[str, Any]] = []
    replaced = False
    for row in rows:
        if row.get("id") == webhook["id"]:
            out.append(webhook)
            replaced = True
        else:
            out.append(row)
    if not replaced:
        out.append(webhook)
    save_webhooks(out)
    return webhook


def remove_webhook(webhook_id: str) -> bool:
    rows = load_webhooks()
    after = [w for w in rows if w.get("id") != webhook_id]
    save_webhooks(after)
    return len(after) != len(rows)


def outbox_for_webhook(webhook_id: str) -> list[dict[str, Any]]:
    return [r for r in outbox.all_rows() if r.get("webhook_id") == webhook_id]


def requeue_failed(*, fixed: bool = True) -> int:
    rows = outbox.all_rows()
    n = 0
    for row in rows:
        if row.get("status") == "failed" and retry.should_retry(row, fixed=fixed):
            row["status"] = "pending"
            n += 1
    from cc.webhooks.retry import rewrite_outbox

    rewrite_outbox(rows)
    return n


def delivery_stats() -> dict[str, Any]:
    rows = outbox.all_rows()
    by_status: dict[str, int] = {}
    for row in rows:
        st = str(row.get("status"))
        by_status[st] = by_status.get(st, 0) + 1
    return {"total": len(rows), "by_status": by_status, "webhooks": [w.get("id") for w in load_webhooks()]}
'''.lstrip(),
    encoding="utf-8",
)

(lib / "integration_facade.py").write_text(
    '''from __future__ import annotations

from pathlib import Path
from typing import Any

from cc.iam import actions as iam_actions
from cc.pipelines.deliver import deliver
from cc.prs import approvals, merge, store as pr_store
from cc.repos import catalog, gitops
from cc.services import authz_gateway, serializers
from cc.util import full_ref
from cc.webhooks.dispatch import dispatch_pending


class ControlPlane:
    """High-level facade used by CLI/API and operator scripts."""

    def __init__(self, *, fixed: bool = False) -> None:
        self.fixed = fixed

    def ensure_repo(self, name: str) -> dict[str, Any]:
        catalog.upsert_repo(name)
        gitops.ensure_bare(name)
        return catalog.require_repo(name)

    def clone(self, principal: str, repo: str, dest: Path, *, mfa: bool = False, source_ip: str = "127.0.0.1") -> None:
        authz_gateway.gated_authorize(
            principal, iam_actions.GIT_PULL, repo, "main", mfa=mfa, source_ip=source_ip, fixed=self.fixed
        )
        gitops.clone(repo, dest)

    def push(
        self,
        principal: str,
        repo: str,
        worktree: Path,
        branch: str,
        *,
        mfa: bool = False,
        source_ip: str = "127.0.0.1",
    ) -> dict[str, Any]:
        ref = full_ref(branch)
        authz_gateway.gated_authorize(
            principal, iam_actions.GIT_PUSH, repo, ref, mfa=mfa, source_ip=source_ip, fixed=self.fixed
        )
        commit = gitops.push(repo, worktree, branch)
        return serializers.push_success(repo, ref, commit)

    def open_pr(self, principal: str, repo: str, source: str, dest: str, *, mfa: bool = False, source_ip: str = "127.0.0.1") -> dict[str, Any]:
        authz_gateway.gated_authorize(
            principal, iam_actions.GIT_PULL, repo, source, mfa=mfa, source_ip=source_ip, fixed=self.fixed
        )
        src = gitops.ref_commit(repo, source)
        pr = pr_store.create(repo, source, dest, src, principal)
        return serializers.pr_success(pr.pr_id, pr.source, pr.dest, pr.source_commit)

    def approve(self, principal: str, pr_id: int) -> dict[str, Any]:
        return approvals.approve(pr_id, principal, fixed=self.fixed)

    def merge(self, principal: str, pr_id: int, *, mfa: bool = False, source_ip: str = "127.0.0.1") -> dict[str, Any]:
        return merge.merge(pr_id, principal, mfa=mfa, source_ip=source_ip, fixed=self.fixed)

    def deliver(self, repo: str, ref: str) -> dict[str, Any]:
        return deliver(repo, ref, fixed=self.fixed)

    def dispatch(self) -> list[dict[str, Any]]:
        sink: list[dict[str, Any]] = []
        return dispatch_pending(fixed=self.fixed, sink=sink)
'''.lstrip(),
    encoding="utf-8",
)

print("extra modules ok")
