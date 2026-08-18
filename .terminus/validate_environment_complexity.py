#!/usr/bin/env python3
"""Pre-verifier complexity checks for ENVIRONMENT_BUILD.

This validator covers only evidence legal before VERIFIER_BUILD: solver-visible
environment scale, anti-padding checks, approved defect topology structure, causal
coupling, and infrastructure resource scale. It never reads verifier tests or the
private test map. The full validate_task_complexity.py gate remains mandatory at
VERIFIER_BUILD and COMPLEXITY_GATE.
"""

from __future__ import annotations

import sys
from pathlib import Path

CONTROL_PLANE = Path(__file__).resolve().parent
if str(CONTROL_PLANE) not in sys.path:
    sys.path.insert(0, str(CONTROL_PLANE))

import validate_defect_topology as topology_gate  # noqa: E402
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


def validate(task_name: str) -> int:
    # Keep ROOT patchable in tests while reusing canonical measurement/topology helpers.
    full_gate.ROOT = ROOT
    topology_gate.ROOT = ROOT
    task_dir = ROOT / task_name
    if not (task_dir / "task.toml").is_file():
        full_gate.die(f"task not found: {task_name}")

    manifest = full_gate.load_manifest(task_name)
    profile = str(manifest.get("profile", ""))
    if profile not in PROFILES:
        print(f"profile={profile!r}; no large-system environment complexity policy applies")
        return 0
    strict = profile == STRICT_PROFILE

    errors, warnings, metrics = topology_gate.inspect_topology(manifest, strict)

    loc, loc_detail = full_gate.substantive_loc(task_dir)
    add_scale_finding(
        strict,
        errors,
        warnings,
        loc >= 3000,
        f"substantive solver-visible LOC {loc} is below required 3000",
    )
    for group in full_gate.duplicated_environment_files(task_dir):
        errors.append(
            "environment files are equivalent after comment/whitespace normalization, "
            f"which inflates scale without adding behavior: {', '.join(group)}"
        )

    kind = str(manifest.get("task_kind", "software")).lower()
    resource_count = 0
    if kind == "infrastructure":
        declared = manifest.get("resource_count")
        discovered = (
            full_gate.terraform_resource_count(task_dir)
            + full_gate.kubernetes_resource_count(task_dir)
        )
        resource_count = int(declared) if isinstance(declared, int) else discovered
        add_scale_finding(
            strict,
            errors,
            warnings,
            30 <= resource_count <= 50,
            f"infrastructure resource count {resource_count} is outside required 30-50",
        )
        if isinstance(declared, int) and discovered and abs(declared - discovered) > 5:
            warnings.append(
                f"declared resource_count={declared} differs materially from discovered "
                f"Terraform/Kubernetes count={discovered}"
            )

    print(f"task={task_name}")
    print(f"profile={profile} strict={str(strict).lower()} phase=environment-build")
    print(f"substantive_loc={loc}")
    print(
        f"defects={metrics['defects']} root_causes={metrics['root_causes']} "
        f"interrelated={metrics['interrelated']} edges={metrics['edges']}"
    )
    print(
        f"cross_cluster_pairs={metrics['cross_cluster_pairs']} "
        f"components={metrics['components']}"
    )
    if kind == "infrastructure":
        print(f"resources={resource_count}")
    print("largest_environment_files=")
    for path, count in sorted(loc_detail, key=lambda item: item[1], reverse=True)[:12]:
        print(f"  {count:5d}  {path}")
    print("verifier_scope=DEFERRED_TO_VERIFIER_BUILD_AND_COMPLEXITY_GATE")

    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print("environment complexity gate: FAIL")
        return 1

    print(
        "environment complexity gate: PASS. Pre-verifier scale/topology authenticity "
        "is enforced; the full test-map/F2P/P2P gate remains mandatory downstream."
    )
    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"Usage: {argv[0]} <top-level-task-directory>", file=sys.stderr)
        return 2
    return validate(argv[1])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
