"""Kubernetes manifest loader and cluster state modeler."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore


def load_yaml_documents(path: Path) -> List[Dict[str, Any]]:
    """Load multiple YAML documents from a manifest file."""
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    if yaml is None:
        raise RuntimeError("PyYAML is required for manifest parsing")
    docs = list(yaml.safe_load_all(text))
    return [d for d in docs if isinstance(d, dict)]


def record_regulated_workload(
    state: Dict[str, Any], kind: str, meta: Dict[str, Any], spec: Dict[str, Any]
) -> None:
    """Record workload placement attributes if workload is in regulated scope."""
    labels = meta.get("labels") or {}
    if meta.get("namespace") != "regulated" and labels.get("workload-class") != "regulated":
        return
    template = spec.get("template") or {}
    pod_spec = template.get("spec") or {}
    node_selector = pod_spec.get("nodeSelector") or {}
    state["workloads"].append(
        {
            "name": meta.get("name"),
            "namespace": meta.get("namespace"),
            "nodepool": node_selector.get("nodepool") or node_selector.get("karpenter.sh/nodepool"),
            "capacity_type": node_selector.get("karpenter.sh/capacity-type"),
            "replicas": spec.get("replicas", 1),
            "kind": kind,
        }
    )


def apply_k8s_manifests(k8s_dir: Path) -> Dict[str, Any]:
    """Load submitted YAML manifests into structured cluster state dict."""
    state: Dict[str, Any] = {
        "pdbs": [],
        "service_accounts": [],
        "deployments": [],
        "nodepools": [],
        "workloads": [],
    }
    if not k8s_dir.is_dir():
        return state

    for path in sorted(k8s_dir.glob("*.yaml")) + sorted(k8s_dir.glob("*.yml")):
        for doc in load_yaml_documents(path):
            kind = doc.get("kind")
            meta = doc.get("metadata") or {}
            if kind == "PodDisruptionBudget":
                spec = doc.get("spec") or {}
                state["pdbs"].append(
                    {
                        "name": meta.get("name"),
                        "namespace": meta.get("namespace", "default"),
                        "min_available": spec.get("minAvailable"),
                        "selector": ((spec.get("selector") or {}).get("matchLabels") or {}),
                    }
                )
            elif kind == "ServiceAccount":
                ann = meta.get("annotations") or {}
                state["service_accounts"].append(
                    {
                        "name": meta.get("name"),
                        "namespace": meta.get("namespace", "default"),
                        "role_arn": ann.get("eks.amazonaws.com/role-arn", ""),
                    }
                )
            elif kind == "Deployment":
                spec = doc.get("spec") or {}
                template = (spec.get("template") or {}).get("metadata") or {}
                state["deployments"].append(
                    {
                        "name": meta.get("name"),
                        "namespace": meta.get("namespace", "default"),
                        "replicas": spec.get("replicas", 1),
                        "labels": (template.get("labels") or {}),
                    }
                )
                record_regulated_workload(state, kind, meta, spec)
            elif kind == "StatefulSet":
                spec = doc.get("spec") or {}
                record_regulated_workload(state, kind, meta, spec)
            elif kind in {"NodePool", "EC2NodeClass"}:
                state["nodepools"].append(doc)

    return state
