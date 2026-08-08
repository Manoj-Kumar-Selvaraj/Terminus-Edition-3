#!/usr/bin/env python3
"""Authoring-time complexity checks for Terminus Edition 3 large-system tasks.

This is a control-plane validator, not a submission verifier. It never becomes part
of the packaged task and may inspect private .terminus design metadata.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]

CODE_SUFFIXES = {
    ".c",
    ".cc",
    ".cpp",
    ".cxx",
    ".h",
    ".hpp",
    ".go",
    ".java",
    ".kt",
    ".kts",
    ".rs",
    ".py",
    ".rb",
    ".php",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".cs",
    ".fs",
    ".fsx",
    ".scala",
    ".swift",
    ".sh",
    ".bash",
    ".zsh",
    ".sql",
    ".tf",
    ".tfvars",
    ".hcl",
    ".yaml",
    ".yml",
    ".json",
    ".xml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".cob",
    ".cbl",
    ".cpy",
    ".jcl",
}

DOC_NAMES = {
    "readme",
    "readme.md",
    "readme.txt",
    "license",
    "license.md",
    "copying",
}

GENERATED_DIR_NAMES = {
    "node_modules",
    "vendor",
    "dist",
    "build",
    "target",
    "__pycache__",
    ".terraform",
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
        if "docs" in {p.lower() for p in rel.parts[:-1]}:
            continue
        if path.suffix.lower() not in CODE_SUFFIXES and path.name != "Dockerfile":
            continue
        yield path


def is_comment_only(line: str, suffix: str, filename: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True

    lower = filename.lower()
    if lower == "dockerfile":
        return stripped.startswith("#")
    if suffix in {".sh", ".bash", ".zsh", ".py", ".rb", ".yaml", ".yml", ".tf", ".tfvars", ".hcl", ".ini", ".cfg", ".conf"}:
        return stripped.startswith("#")
    if suffix in {".js", ".jsx", ".ts", ".tsx", ".java", ".kt", ".kts", ".go", ".rs", ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".cs", ".swift", ".scala"}:
        return stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*") or stripped.startswith("*/")
    if suffix in {".sql"}:
        return stripped.startswith("--")
    if suffix in {".cob", ".cbl", ".cpy"}:
        # Free-format and fixed-format common comment forms.
        return stripped.startswith("*>") or stripped.startswith("*")
    if suffix in {".xml"}:
        return stripped.startswith("<!--") and stripped.endswith("-->")
    return False


def substantive_loc(task_dir: Path) -> tuple[int, list[tuple[str, int]]]:
    total = 0
    detail: list[tuple[str, int]] = []
    for path in iter_environment_files(task_dir):
        count = 0
        suffix = path.suffix.lower()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line in text.splitlines():
            if not is_comment_only(line, suffix, path.name):
                count += 1
        detail.append((str(path.relative_to(task_dir)), count))
        total += count
    return total, sorted(detail)


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
    pattern = re.compile(r'^\s*(?:resource|data)\s+"[^"\n]+"\s+"[^"\n]+"\s*\{', re.MULTILINE)
    total = 0
    for path in (task_dir / "environment").rglob("*.tf"):
        total += len(pattern.findall(path.read_text(encoding="utf-8")))
    return total


def kubernetes_resource_count(task_dir: Path) -> int:
    total = 0
    for suffix in ("*.yaml", "*.yml"):
        for path in (task_dir / "environment").rglob(suffix):
            text = path.read_text(encoding="utf-8")
            total += len(re.findall(r"(?m)^kind:\s*[^\s#]+\s*$", text))
    return total


def load_manifest(task_name: str) -> dict:
    path = ROOT / ".terminus" / "designs" / f"{task_name}.json"
    if not path.is_file():
        die(f"missing private design manifest: {path.relative_to(ROOT)}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        die(f"invalid design manifest JSON: {exc}")
    if not isinstance(data, dict):
        die("design manifest must be a JSON object")
    return data


def validate(task_name: str) -> int:
    task_dir = ROOT / task_name
    if not (task_dir / "task.toml").is_file():
        die(f"task not found: {task_name}")

    manifest = load_manifest(task_name)
    profile = manifest.get("profile")
    if profile != "large_system":
        print(f"profile={profile!r}; large-system numeric floors are not enforced")
        return 0

    errors: list[str] = []
    warnings: list[str] = []

    loc, loc_detail = substantive_loc(task_dir)
    if loc < 3000:
        errors.append(f"substantive solver-visible LOC {loc} < required 3000")

    defects = manifest.get("defects", [])
    if not isinstance(defects, list):
        errors.append("manifest defects must be an array")
        defects = []
    if not 20 <= len(defects) <= 30:
        errors.append(f"defect manifestation count {len(defects)} is outside required 20-30")

    root_causes = {d.get("root_cause") for d in defects if isinstance(d, dict) and d.get("root_cause")}
    if root_causes and not 4 <= len(root_causes) <= 8:
        warnings.append(f"root-cause cluster count {len(root_causes)} is outside normal 4-8 target")

    edges = manifest.get("causal_edges", [])
    if not isinstance(edges, list):
        errors.append("manifest causal_edges must be an array")
        edges = []
    connected_ids: set[str] = set()
    valid_ids = {d.get("id") for d in defects if isinstance(d, dict) and d.get("id")}
    for edge in edges:
        if not isinstance(edge, dict):
            errors.append("each causal edge must be an object")
            continue
        src = edge.get("from")
        dst = edge.get("to")
        if src not in valid_ids or dst not in valid_ids:
            errors.append(f"causal edge references unknown defect: {src!r}->{dst!r}")
            continue
        if src == dst:
            errors.append(f"self-edge is not meaningful: {src}")
            continue
        connected_ids.update({src, dst})
    if len(connected_ids) < 10:
        errors.append(f"only {len(connected_ids)} defect manifestations participate in causal edges; require >=10")
    if len(connected_ids) < 15:
        warnings.append(f"interrelated defect count {len(connected_ids)} is below preferred 15")

    tests = python_test_names(task_dir / "tests")
    f2p = [name for name in tests if name.startswith("test_f2p_")]
    p2p = [name for name in tests if name.startswith("test_p2p_")]
    unclassified = [name for name in tests if name not in f2p and name not in p2p]
    if not 25 <= len(f2p) <= 30:
        errors.append(f"F2P test count {len(f2p)} is outside required 25-30")
    if unclassified:
        warnings.append(f"{len(unclassified)} tests are not named as F2P/P2P: {', '.join(unclassified[:5])}")

    kind = str(manifest.get("task_kind", "software")).lower()
    resource_count = 0
    if kind == "infrastructure":
        declared = manifest.get("resource_count")
        discovered = terraform_resource_count(task_dir) + kubernetes_resource_count(task_dir)
        resource_count = int(declared) if isinstance(declared, int) else discovered
        if not 30 <= resource_count <= 50:
            errors.append(f"infrastructure resource count {resource_count} is outside required 30-50")
        if declared is not None and discovered and abs(resource_count - discovered) > 5:
            warnings.append(
                f"declared resource_count={resource_count} differs materially from simple discovered count={discovered}; review manually"
            )

    forbidden_notes = [
        d.get("filler_justification")
        for d in defects
        if isinstance(d, dict) and d.get("filler_justification")
    ]
    if forbidden_notes:
        errors.append("defect manifest contains filler_justification entries; numeric padding is prohibited")

    print(f"task={task_name}")
    print(f"profile={profile}")
    print(f"substantive_loc={loc}")
    print(f"defects={len(defects)} root_causes={len(root_causes)} interrelated={len(connected_ids)} edges={len(edges)}")
    print(f"tests_total={len(tests)} f2p={len(f2p)} p2p={len(p2p)} unclassified={len(unclassified)}")
    if kind == "infrastructure":
        print(f"resources={resource_count}")

    print("largest_environment_files=")
    for path, count in sorted(loc_detail, key=lambda item: item[1], reverse=True)[:12]:
        print(f"  {count:5d}  {path}")

    for warning in warnings:
        print(f"WARNING: {warning}")
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("large-system complexity gate: PASS")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"Usage: {argv[0]} <top-level-task-directory>", file=sys.stderr)
        return 2
    return validate(argv[1])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
