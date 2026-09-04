"""Kubernetes manifest loader and cluster state modeler."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

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


def _node_selector(pod_spec: Dict[str, Any]) -> Dict[str, Any]:
    selector = pod_spec.get("nodeSelector") or {}
    return selector if isinstance(selector, dict) else {}


def _extract_nodepool(selector: Dict[str, Any]) -> Optional[str]:
    for key in ("nodepool", "karpenter.sh/nodepool", "karpenter.sh/nodepool-name"):
        if selector.get(key):
            return str(selector.get(key))
    return None


def _extract_capacity_type(selector: Dict[str, Any]) -> Optional[str]:
    for key in ("karpenter.sh/capacity-type", "capacity-type", "node.kubernetes.io/capacity-type"):
        if selector.get(key):
            return str(selector.get(key))
    return None


def record_regulated_workload(
    state: Dict[str, Any],
    kind: str,
    meta: Dict[str, Any],
    spec: Dict[str, Any],
) -> None:
    """Record workload placement attributes if workload is in regulated scope."""
    labels = meta.get("labels") or {}
    namespace = meta.get("namespace")
    if namespace != "regulated" and labels.get("workload-class") != "regulated":
        return
    template = spec.get("template") or {}
    pod_spec = template.get("spec") or {}
    node_selector = _node_selector(pod_spec)
    tolerations = pod_spec.get("tolerations") or []
    state["workloads"].append(
        {
            "name": meta.get("name"),
            "namespace": namespace,
            "nodepool": _extract_nodepool(node_selector),
            "capacity_type": _extract_capacity_type(node_selector),
            "replicas": spec.get("replicas", 1),
            "kind": kind,
            "toleration_count": len(tolerations) if isinstance(tolerations, list) else 0,
            "labels": dict(labels),
        }
    )


def _parse_pdb(doc: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
    spec = doc.get("spec") or {}
    selector = ((spec.get("selector") or {}).get("matchLabels") or {})
    return {
        "name": meta.get("name"),
        "namespace": meta.get("namespace", "default"),
        "min_available": spec.get("minAvailable"),
        "max_unavailable": spec.get("maxUnavailable"),
        "selector": dict(selector) if isinstance(selector, dict) else {},
    }


def _parse_service_account(meta: Dict[str, Any]) -> Dict[str, Any]:
    ann = meta.get("annotations") or {}
    return {
        "name": meta.get("name"),
        "namespace": meta.get("namespace", "default"),
        "role_arn": ann.get("eks.amazonaws.com/role-arn", ""),
        "annotations": dict(ann) if isinstance(ann, dict) else {},
    }


def _parse_deployment(doc: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
    spec = doc.get("spec") or {}
    template_meta = ((spec.get("template") or {}).get("metadata") or {})
    template_labels = template_meta.get("labels") or {}
    return {
        "name": meta.get("name"),
        "namespace": meta.get("namespace", "default"),
        "replicas": spec.get("replicas", 1),
        "labels": dict(template_labels) if isinstance(template_labels, dict) else {},
        "selector": ((spec.get("selector") or {}).get("matchLabels") or {}),
    }


def apply_k8s_manifests(k8s_dir: Path) -> Dict[str, Any]:
    """Load submitted YAML manifests into structured cluster state dict."""
    state: Dict[str, Any] = {
        "pdbs": [],
        "service_accounts": [],
        "deployments": [],
        "nodepools": [],
        "workloads": [],
        "namespaces": [],
        "files_loaded": [],
    }
    if not k8s_dir.is_dir():
        return state

    paths = sorted(k8s_dir.glob("*.yaml")) + sorted(k8s_dir.glob("*.yml"))
    for path in paths:
        state["files_loaded"].append(path.name)
        for doc in load_yaml_documents(path):
            kind = doc.get("kind")
            meta = doc.get("metadata") or {}
            if kind == "Namespace":
                state["namespaces"].append(meta.get("name"))
            elif kind == "PodDisruptionBudget":
                state["pdbs"].append(_parse_pdb(doc, meta))
            elif kind == "ServiceAccount":
                state["service_accounts"].append(_parse_service_account(meta))
            elif kind == "Deployment":
                state["deployments"].append(_parse_deployment(doc, meta))
                record_regulated_workload(state, kind, meta, doc.get("spec") or {})
            elif kind == "StatefulSet":
                record_regulated_workload(state, kind, meta, doc.get("spec") or {})
            elif kind in {"NodePool", "EC2NodeClass"}:
                state["nodepools"].append(doc)
            elif kind == "DaemonSet":
                # Track daemonsets as deployments-like replica sources when labeled.
                spec = doc.get("spec") or {}
                template_meta = ((spec.get("template") or {}).get("metadata") or {})
                labels = template_meta.get("labels") or {}
                state["deployments"].append(
                    {
                        "name": meta.get("name"),
                        "namespace": meta.get("namespace", "default"),
                        "replicas": spec.get("replicas", 1),
                        "labels": dict(labels) if isinstance(labels, dict) else {},
                        "selector": ((spec.get("selector") or {}).get("matchLabels") or {}),
                        "kind": "DaemonSet",
                    }
                )

    return state
