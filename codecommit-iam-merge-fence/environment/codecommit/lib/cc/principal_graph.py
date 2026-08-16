"""Build principal / policy / resource graphs for access reviews."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from cc.iam_report import statement_index
from cc.policy_admin import list_policies, principals, read_policy
from cc.repos import catalog


def policy_to_principals() -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = defaultdict(list)
    for name, body in principals().items():
        for pid in body.get("policies") or []:
            mapping[str(pid)].append(name)
    return {k: sorted(v) for k, v in mapping.items()}


def principal_edges() -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for name, body in principals().items():
        for pid in body.get("policies") or []:
            edges.append({"from": name, "to": pid, "kind": "attach"})
    return edges


def policy_action_edges() -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []
    for pid in list_policies():
        for stmt in read_policy(pid).get("Statement") or []:
            edges.append(
                {
                    "from": pid,
                    "to": stmt.get("Action"),
                    "effect": stmt.get("Effect"),
                    "resource": stmt.get("Resource"),
                    "kind": "grant",
                }
            )
    return edges


def repo_resource_nodes() -> list[dict[str, Any]]:
    return [{"id": name, "kind": "repo"} for name in catalog.list_repos()]


def bipartite_summary() -> dict[str, Any]:
    p2p = policy_to_principals()
    return {
        "principals": sorted(principals()),
        "policies": list_policies(),
        "orphan_policies": [p for p in list_policies() if p not in p2p],
        "shared_policies": {k: v for k, v in p2p.items() if len(v) > 1},
        "edges_attach": principal_edges(),
        "edges_grant": policy_action_edges(),
        "repos": repo_resource_nodes(),
        "statement_count": len(statement_index()),
    }


def who_can_touch_repo(repo: str) -> dict[str, list[str]]:
    by_action: dict[str, list[str]] = defaultdict(list)
    p2p = policy_to_principals()
    for row in statement_index():
        resource = str(row.get("resource") or "")
        if repo not in resource and not resource.endswith("*") and resource != "*":
            continue
        action = str(row.get("action") or "")
        for principal in p2p.get(str(row.get("policy"))) or []:
            if principal not in by_action[action]:
                by_action[action].append(principal)
    return {k: sorted(v) for k, v in by_action.items()}


def compare_access(a: str, b: str) -> dict[str, Any]:
    pa = set((principals().get(a) or {}).get("policies") or [])
    pb = set((principals().get(b) or {}).get("policies") or [])
    return {
        "a": a,
        "b": b,
        "only_a": sorted(pa - pb),
        "only_b": sorted(pb - pa),
        "shared": sorted(pa & pb),
    }


def graph_export() -> dict[str, Any]:
    return {
        "summary": bipartite_summary(),
        "ledger_touch": who_can_touch_repo("ledger"),
        "alice_vs_ben": compare_access("dev-alice", "dev-ben"),
    }
