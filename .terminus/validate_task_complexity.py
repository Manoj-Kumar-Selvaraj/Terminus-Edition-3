#!/usr/bin/env python3
"""Authoring-time authenticity checks for Terminus large-system tasks.

Two profiles are supported:

* ``large_system_strict`` keeps the project owner's scale requirements as hard
  authoring constraints and also requires structural authenticity.
* ``large_system`` uses the same scale numbers as diagnostics while still
  blocking padding, flat defect graphs and dishonest test maps.

Behavioral classification is owned by the private test map. Historical
``test_f2p_*``/``test_p2p_*`` names remain supported as an optional consistency
signal, but neutral pytest names are valid. A test-map entry may also provide a
fourth behavioral-case id so several independent probes of one shared invariant or
boundary count as one behavioral case without discarding coverage.

This validator is control-plane logic only and never enters a submission ZIP.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
PROFILES = {"large_system", "large_system_strict"}
STRICT_PROFILE = "large_system_strict"

CODE_SUFFIXES = {
    ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".go", ".java", ".kt", ".kts",
    ".rs", ".py", ".rb", ".php", ".js", ".jsx", ".ts", ".tsx", ".cs", ".fs",
    ".fsx", ".scala", ".swift", ".sh", ".bash", ".zsh", ".sql", ".tf", ".tfvars",
    ".hcl", ".yaml", ".yml", ".json", ".xml", ".toml", ".ini", ".cfg", ".conf",
    ".cob", ".cbl", ".cpy", ".jcl",
}
DOC_NAMES = {"readme", "readme.md", "readme.txt", "license", "license.md", "copying"}
GENERATED_DIR_NAMES = {
    "node_modules", "vendor", "dist", "build", "target", "__pycache__", ".terraform"
}


def die(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(1)


def iter_environment_files(task_dir: Path) -> Iterable[Path]:
    env = task_dir / "environment"
    if not env.is_dir():
        return
    for path in env.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(env)
        if any(part in GENERATED_DIR_NAMES for part in rel.parts):
            continue
        if path.name.lower() in DOC_NAMES:
            continue
        if "docs" in {part.lower() for part in rel.parts[:-1]}:
            continue
        if path.suffix.lower() not in CODE_SUFFIXES and path.name != "Dockerfile":
            continue
        yield path


def is_comment_only(line: str, suffix: str, filename: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if filename.lower() == "dockerfile":
        return stripped.startswith("#")
    if suffix in {
        ".sh", ".bash", ".zsh", ".py", ".rb", ".yaml", ".yml", ".tf", ".tfvars",
        ".hcl", ".ini", ".cfg", ".conf",
    }:
        return stripped.startswith("#")
    if suffix in {
        ".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".kts", ".go", ".rs", ".c",
        ".cc", ".cpp", ".cxx", ".h", ".hpp", ".cs", ".swift", ".scala",
    }:
        return (
            stripped.startswith("//")
            or stripped.startswith("/*")
            or stripped.startswith("*")
            or stripped.startswith("*/")
        )
    if suffix == ".sql":
        return stripped.startswith("--")
    if suffix in {".cob", ".cbl", ".cpy"}:
        return stripped.startswith("*>") or stripped.startswith("*")
    if suffix == ".xml":
        return stripped.startswith("<!--") and stripped.endswith("-->")
    return False


def substantive_loc(task_dir: Path) -> tuple[int, list[tuple[str, int]]]:
    total = 0
    detail: list[tuple[str, int]] = []
    for path in iter_environment_files(task_dir):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        suffix = path.suffix.lower()
        count = sum(
            1 for line in text.splitlines() if not is_comment_only(line, suffix, path.name)
        )
        detail.append((str(path.relative_to(task_dir)), count))
        total += count
    return total, sorted(detail)


def content_fingerprint(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""
    suffix = path.suffix.lower()
    body = [
        " ".join(line.split())
        for line in text.splitlines()
        if not is_comment_only(line, suffix, path.name)
    ]
    if len(body) < 25:
        return ""
    return hashlib.sha256("\n".join(body).encode("utf-8")).hexdigest()


def duplicated_environment_files(task_dir: Path) -> list[list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for path in iter_environment_files(task_dir):
        digest = content_fingerprint(path)
        if digest:
            groups[digest].append(str(path.relative_to(task_dir)))
    return [sorted(paths) for paths in groups.values() if len(paths) > 1]


def python_test_names(tests_dir: Path) -> list[str]:
    names: list[str] = []
    for path in sorted(tests_dir.glob("test_*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            die(f"cannot parse {path}: {exc}")
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                names.append(node.name)
    return names


def terraform_resource_count(task_dir: Path) -> int:
    pattern = re.compile(
        r'^\s*(?:resource|data)\s+"[^"\n]+"\s+"[^"\n]+"\s*\{', re.MULTILINE
    )
    return sum(
        len(pattern.findall(path.read_text(encoding="utf-8")))
        for path in (task_dir / "environment").rglob("*.tf")
    )


def kubernetes_resource_count(task_dir: Path) -> int:
    total = 0
    for suffix in ("*.yaml", "*.yml"):
        for path in (task_dir / "environment").rglob(suffix):
            total += len(
                re.findall(r"(?m)^kind:\s*[^\s#]+\s*$", path.read_text(encoding="utf-8"))
            )
    return total


def load_json(path: Path, description: str) -> dict:
    if not path.is_file():
        die(f"missing {description}: {path.relative_to(ROOT)}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        die(f"invalid {description} JSON: {exc}")
    if not isinstance(data, dict):
        die(f"{description} must be a JSON object")
    return data


def load_manifest(task_name: str) -> dict:
    return load_json(ROOT / ".terminus" / "designs" / f"{task_name}.json", "design manifest")


def load_test_map(task_name: str) -> dict:
    return load_json(
        ROOT / ".terminus" / "designs" / f"{task_name}-test-map.json", "private test map"
    )


def add_scale_finding(
    strict: bool, errors: list[str], warnings: list[str], condition: bool, message: str
) -> None:
    if condition:
        return
    (errors if strict else warnings).append(message)


def expected_test_class(name: str) -> str:
    if name.startswith("test_f2p_"):
        return "F2P"
    if name.startswith("test_p2p_"):
        return "P2P"
    return ""


def name_family(test_name: str) -> str:
    trimmed = re.sub(r"^test_(f2p|p2p)_", "", test_name)
    trimmed = re.sub(r"\d+", "", trimmed)
    return "_".join(trimmed.split("_")[:3])


def validate(task_name: str) -> int:
    task_dir = ROOT / task_name
    if not (task_dir / "task.toml").is_file():
        die(f"task not found: {task_name}")

    manifest = load_manifest(task_name)
    profile = str(manifest.get("profile", ""))
    if profile not in PROFILES:
        print(f"profile={profile!r}; no large-system complexity policy applies")
        return 0
    strict = profile == STRICT_PROFILE

    errors: list[str] = []
    warnings: list[str] = []

    loc, loc_detail = substantive_loc(task_dir)
    add_scale_finding(
        strict,
        errors,
        warnings,
        loc >= 3000,
        f"substantive solver-visible LOC {loc} is below required 3000",
    )
    for group in duplicated_environment_files(task_dir):
        errors.append(
            "environment files are equivalent after comment/whitespace normalization, "
            f"which inflates scale without adding behavior: {', '.join(group)}"
        )

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

    defect_cluster: dict[str, str] = {}
    normalized_failures: dict[str, str] = {}
    components: Counter[str] = Counter()
    valid_ids: set[str] = set()
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

    tests = python_test_names(task_dir / "tests")
    if len(tests) != len(set(tests)):
        errors.append("duplicate pytest function names were discovered")

    test_map = load_test_map(task_name)
    requirements = test_map.get("requirements", {})
    if not isinstance(requirements, dict) or not requirements:
        errors.append("test map declares no requirements")
        requirements = {}
    entries = test_map.get("tests", [])
    if not isinstance(entries, list):
        errors.append("test map tests must be an array")
        entries = []

    mapped: dict[str, str] = {}
    mapped_class: dict[str, str] = {}
    mapped_case: dict[str, str] = {}
    case_contract: dict[str, tuple[str, str]] = {}
    per_requirement_cases: dict[str, set[str]] = defaultdict(set)
    for entry in entries:
        if not isinstance(entry, list) or len(entry) not in {3, 4}:
            errors.append(
                f"test-map entry must be [name, class, requirement] or [name, class, requirement, case_id]: {entry!r}"
            )
            continue
        name, classification, requirement = (str(item) for item in entry[:3])
        classification = classification.upper()
        case_id = str(entry[3]) if len(entry) == 4 else name
        if name in mapped:
            errors.append(f"test map contains duplicate test entry: {name}")
            continue
        if classification not in {"F2P", "P2P"}:
            errors.append(f"test {name} has invalid classification {classification!r}")
        actual_class = expected_test_class(name)
        if actual_class and classification != actual_class:
            errors.append(
                f"test {name} is named {actual_class} but test map class is {classification}; classification drift can hide suite inflation"
            )
        if requirement not in requirements:
            errors.append(f"test {name} maps to undeclared requirement {requirement!r}")
        if not case_id:
            errors.append(f"test {name} has an empty behavioral case id")
        previous = case_contract.get(case_id)
        current = (classification, requirement)
        if previous is not None and previous != current:
            errors.append(
                f"behavioral case {case_id!r} mixes classification/requirements: {previous!r} vs {current!r}"
            )
        else:
            case_contract[case_id] = current
        mapped[name] = requirement
        mapped_class[name] = classification
        mapped_case[name] = case_id
        if classification == "F2P":
            per_requirement_cases[requirement].add(case_id)

    missing_from_map = sorted(set(tests) - set(mapped))
    absent_tests = sorted(set(mapped) - set(tests))
    if missing_from_map:
        errors.append(f"tests present in tests/ but absent from test map: {', '.join(missing_from_map)}")
    if absent_tests:
        errors.append(f"test map references tests that do not exist: {', '.join(absent_tests)}")
    mapped_requirements = set(mapped.values())
    for requirement in requirements:
        if requirement not in mapped_requirements:
            errors.append(f"requirement {requirement} has no test and cannot be verified")

    f2p = [name for name in tests if mapped_class.get(name) == "F2P"]
    p2p = [name for name in tests if mapped_class.get(name) == "P2P"]
    neutral_names = [name for name in tests if not expected_test_class(name)]
    f2p_cases = {
        mapped_case[name]
        for name in f2p
        if name in mapped_case
    }
    p2p_cases = {
        mapped_case[name]
        for name in p2p
        if name in mapped_case
    }
    add_scale_finding(
        strict,
        errors,
        warnings,
        25 <= len(f2p_cases) <= 30,
        f"F2P behavioral case count {len(f2p_cases)} is outside required 25-30",
    )
    if neutral_names:
        warnings.append(
            f"{len(neutral_names)} tests use neutral names; private test-map classification is authoritative"
        )

    if per_requirement_cases and f2p_cases:
        requirement, cases = max(
            per_requirement_cases.items(), key=lambda item: len(item[1])
        )
        count = len(cases)
        share = count / len(f2p_cases)
        if share > 0.40:
            errors.append(
                f"{count} of {len(f2p_cases)} F2P behavioral cases ({share:.0%}) verify {requirement}; one requirement dominates the suite"
            )
        elif share > 0.30:
            warnings.append(
                f"{requirement} accounts for {share:.0%} of F2P behavioral cases; inspect distinctness"
            )

    families = Counter(name_family(name) for name in f2p)
    for family, count in families.most_common(3):
        if count > 4:
            warnings.append(f"{count} F2P probes share name family {family!r}; inspect for fixture renames")

    groups = test_map.get("behavioral_case_groups", {})
    if groups is not None and not isinstance(groups, dict):
        errors.append("behavioral_case_groups must be an object when present")
        groups = {}
    if isinstance(groups, dict):
        for case_id, group in groups.items():
            if not isinstance(group, dict):
                errors.append(f"behavioral case group {case_id!r} must be an object")
                continue
            members = group.get("tests", [])
            rationale = str(group.get("rationale", "")).strip()
            if not isinstance(members, list) or len(members) < 2:
                errors.append(f"behavioral case group {case_id!r} must declare at least two tests")
                continue
            declared = {str(name) for name in members}
            actual = {name for name, mapped_id in mapped_case.items() if mapped_id == case_id}
            if declared != actual:
                errors.append(
                    f"behavioral case group {case_id!r} membership mismatch: declared={sorted(declared)} actual={sorted(actual)}"
                )
            if not rationale:
                errors.append(f"behavioral case group {case_id!r} requires a non-empty rationale")

    kind = str(manifest.get("task_kind", "software")).lower()
    resource_count = 0
    if kind == "infrastructure":
        declared = manifest.get("resource_count")
        discovered = terraform_resource_count(task_dir) + kubernetes_resource_count(task_dir)
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
                f"declared resource_count={declared} differs materially from discovered Terraform/Kubernetes count={discovered}"
            )

    if any(
        isinstance(defect, dict) and defect.get("filler_justification") for defect in defects
    ):
        errors.append("defect manifest contains filler_justification; numeric padding is prohibited")

    print(f"task={task_name}")
    print(f"profile={profile} strict={str(strict).lower()}")
    print(f"substantive_loc={loc}")
    print(
        f"defects={len(defects)} root_causes={len(used_clusters)} "
        f"interrelated={len(connected_ids)} edges={len(seen_edges)}"
    )
    print(f"cross_cluster_pairs={len(cross_cluster_pairs)} components={len(components)}")
    print(
        f"tests_total={len(tests)} f2p_probes={len(f2p)} p2p_probes={len(p2p)} "
        f"f2p_cases={len(f2p_cases)} p2p_cases={len(p2p_cases)} "
        f"neutral_names={len(neutral_names)} requirements={len(requirements)}"
    )
    if kind == "infrastructure":
        print(f"resources={resource_count}")
    print("largest_environment_files=")
    for path, count in sorted(loc_detail, key=lambda item: item[1], reverse=True)[:12]:
        print(f"  {count:5d}  {path}")
    print("f2p_cases_per_requirement=")
    for requirement, cases in sorted(
        per_requirement_cases.items(), key=lambda item: (-len(item[1]), item[0])
    ):
        print(f"  {len(cases):3d}  {requirement}")

    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print("large-system complexity gate: FAIL")
        return 1

    print(
        "large-system complexity gate: PASS. Numeric scale and structural authenticity "
        "are enforced on behavioral cases; private test-map classification is authoritative."
    )
    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"Usage: {argv[0]} <top-level-task-directory>", file=sys.stderr)
        return 2
    return validate(argv[1])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
