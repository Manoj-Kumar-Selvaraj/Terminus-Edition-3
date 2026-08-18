#!/usr/bin/env python3
"""Phase-scoped structural complexity checks for DEFECT_TOPOLOGY.

This validator checks only private creation-design evidence that legally exists at A3.
It does not inspect solver environment material, verifier tests, or the private test map.
Those scopes are enforced by later validators without weakening any final threshold.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

CONTROL_PLANE = Path(__file__).resolve().parent
if str(CONTROL_PLANE) not in sys.path:
    sys.path.insert(0, str(CONTROL_PLANE))

import validate_task_complexity as full_gate  # noqa: E402

ROOT = full_gate.ROOT
PROFILES = full_gate.PROFILES
STRICT_PROFILE = full_gate.STRICT_PROFILE


def add_scale_finding(
    strict: bool, errors: list[str], warnings: list[str], condition: bool, message: str
) -> None:
    if condition:
        return
    (errors if strict else warnings).append(message)


def inspect_topology(manifest: dict, strict: bool) -> tuple[list[str], list[str], dict[str, int]]:
    errors: list[str] = []
    warnings: list[str] = []

    defects = manifest.get("defects", [])
    if not isinstance(defects, list):
        errors.append("manifest defects must be an array")
        defects = []
    add_scale_finding(
        strict,
        errors,
        warnings,
        20 <= len(defects) <= 30,
        f"defect manifestation count {len(defects)} is outside required 20-30",
    )

    clusters = manifest.get("root_cause_clusters", {})
    if not isinstance(clusters, dict) or not clusters:
        errors.append("manifest root_cause_clusters must be a non-empty object")
        clusters = {}

    valid_ids: set[str] = set()
    defect_cluster: dict[str, str] = {}
    normalized_failures: dict[str, str] = {}
    components: Counter[str] = Counter()
    for defect in defects:
        if not isinstance(defect, dict):
            errors.append("each defect must be an object")
            continue
        identifier = str(defect.get("id", ""))
        for field in ("id", "component", "observable_failure", "root_cause"):
            if not defect.get(field):
                errors.append(f"defect {identifier or '<unnamed>'} is missing required field {field!r}")
        if identifier:
            if identifier in valid_ids:
                errors.append(f"duplicate defect id: {identifier}")
            valid_ids.add(identifier)
        cluster = str(defect.get("root_cause", ""))
        if cluster and cluster not in clusters:
            errors.append(f"defect {identifier} names undeclared root cause {cluster!r}")
        if identifier and cluster:
            defect_cluster[identifier] = cluster
        failure = str(defect.get("observable_failure", ""))
        if failure:
            normalized = " ".join(failure.lower().split())
            if normalized in normalized_failures:
                errors.append(
                    f"defects {normalized_failures[normalized]} and {identifier} declare the same "
                    "observable failure; duplicate manifestations are padding"
                )
            normalized_failures[normalized] = identifier
        component = str(defect.get("component", ""))
        if component:
            components[component] += 1
        if not defect.get("partial_fix_trap"):
            warnings.append(f"defect {identifier or '<unnamed>'} has no partial_fix_trap")

    used_clusters = set(defect_cluster.values())
    for cluster in clusters:
        if cluster not in used_clusters:
            errors.append(f"root-cause cluster {cluster!r} has no defect manifestation")
    if used_clusters and not 4 <= len(used_clusters) <= 8:
        warnings.append(f"root-cause cluster count {len(used_clusters)} is outside normal 4-8 target")
    if components:
        component, count = components.most_common(1)[0]
        if count > len(defects) / 2:
            warnings.append(
                f"{count} of {len(defects)} defects live in {component}; inspect for single-file inflation"
            )

    edges = manifest.get("causal_edges", [])
    if not isinstance(edges, list):
        errors.append("manifest causal_edges must be an array")
        edges = []
    connected_ids: set[str] = set()
    cross_cluster_pairs: set[tuple[str, str]] = set()
    seen_edges: set[tuple[str, str]] = set()
    for edge in edges:
        if not isinstance(edge, dict):
            errors.append("each causal edge must be an object")
            continue
        src = str(edge.get("from", ""))
        dst = str(edge.get("to", ""))
        if src not in valid_ids or dst not in valid_ids:
            errors.append(f"causal edge references unknown defect: {src!r}->{dst!r}")
            continue
        if src == dst:
            errors.append(f"self-edge is not meaningful: {src}")
            continue
        pair = (src, dst)
        if pair in seen_edges:
            errors.append(f"duplicate causal edge: {src}->{dst}")
            continue
        seen_edges.add(pair)
        connected_ids.update({src, dst})
        src_cluster = defect_cluster.get(src, "")
        dst_cluster = defect_cluster.get(dst, "")
        if src_cluster and dst_cluster and src_cluster != dst_cluster:
            cross_cluster_pairs.add(tuple(sorted((src_cluster, dst_cluster))))

    if not connected_ids:
        errors.append("no defect participates in a causal edge; topology is a flat bug list")
    if connected_ids and not cross_cluster_pairs:
        errors.append("causal graph has no edge between different root-cause clusters")
    add_scale_finding(
        strict,
        errors,
        warnings,
        len(connected_ids) >= 15,
        f"only {len(connected_ids)} defect manifestations are interrelated; require at least 15",
    )
    if 0 < len(cross_cluster_pairs) < 3:
        warnings.append(
            f"only {len(cross_cluster_pairs)} root-cause cluster pair(s) interact; coupled reasoning is thin"
        )

    if any(isinstance(defect, dict) and defect.get("filler_justification") for defect in defects):
        errors.append("defect manifest contains filler_justification; numeric padding is prohibited")

    metrics = {
        "defects": len(defects),
        "root_causes": len(used_clusters),
        "interrelated": len(connected_ids),
        "edges": len(seen_edges),
        "cross_cluster_pairs": len(cross_cluster_pairs),
        "components": len(components),
    }
    return errors, warnings, metrics


def validate(task_name: str) -> int:
    full_gate.ROOT = ROOT
    manifest = full_gate.load_manifest(task_name)
    profile = str(manifest.get("profile", ""))
    if profile not in PROFILES:
        print(f"profile={profile!r}; no large-system topology policy applies")
        return 0
    strict = profile == STRICT_PROFILE
    errors, warnings, metrics = inspect_topology(manifest, strict)

    print(f"task={task_name}")
    print(f"profile={profile} strict={str(strict).lower()} phase=defect-topology")
    print(
        f"defects={metrics['defects']} root_causes={metrics['root_causes']} "
        f"interrelated={metrics['interrelated']} edges={metrics['edges']}"
    )
    print(
        f"cross_cluster_pairs={metrics['cross_cluster_pairs']} components={metrics['components']}"
    )
    print("environment_scope=DEFERRED_TO_ENVIRONMENT_BUILD")
    print("verifier_scope=DEFERRED_TO_VERIFIER_BUILD_AND_COMPLEXITY_GATE")

    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print("defect topology complexity gate: FAIL")
        return 1

    print("defect topology complexity gate: PASS")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"Usage: {argv[0]} <top-level-task-directory>", file=sys.stderr)
        return 2
    return validate(argv[1])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
