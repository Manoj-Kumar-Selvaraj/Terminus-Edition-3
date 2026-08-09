#!/usr/bin/env python3
"""Reject copied business-module portfolios that inflate production complexity.

Per-file size/decision thresholds are not enough: an author could copy one large
COBOL template many times and change only PROGRAM-ID, literals or field names.
This gate compares the business programs as a portfolio and blocks byte/logic
clones and overwhelming structural-template reuse.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CONTROL_WORDS = (
    "ACCEPT",
    "CALL",
    "CLOSE",
    "COMPUTE",
    "EVALUATE",
    "IF",
    "INSPECT",
    "OPEN",
    "PERFORM",
    "READ",
    "SEARCH",
    "STRING",
    "UNSTRING",
    "WHEN",
    "WRITE",
)

DIVISION_OR_SECTION = {
    "IDENTIFICATION DIVISION.",
    "ENVIRONMENT DIVISION.",
    "DATA DIVISION.",
    "PROCEDURE DIVISION.",
    "WORKING-STORAGE SECTION.",
    "FILE SECTION.",
    "LINKAGE SECTION.",
}


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"cannot read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"{path} must contain a JSON object")
    return data


def substantive_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("*>") or stripped.startswith("*"):
            continue
        lines.append(" ".join(stripped.upper().split()))
    return lines


def canonical_logic(text: str) -> str:
    """Canonicalize only identity/noise; preserve business logic and paragraph names."""
    lines = substantive_lines(text)
    normalized: list[str] = []
    for line in lines:
        line = re.sub(r"^PROGRAM-ID\.\s+[A-Z0-9-]+\.$", "PROGRAM-ID. <PROGRAM>.", line)
        line = re.sub(r"\b20\d{2}-\d{2}-\d{2}\b", "<DATE>", line)
        normalized.append(line)
    return "\n".join(normalized)


def paragraph_names(text: str) -> tuple[str, ...]:
    names: list[str] = []
    for line in substantive_lines(text):
        if line in DIVISION_OR_SECTION:
            continue
        if re.fullmatch(r"[A-Z0-9][A-Z0-9-]+\.", line):
            names.append(line[:-1])
    return tuple(names)


def control_signature(text: str) -> tuple[str, ...]:
    signature: list[str] = []
    for line in substantive_lines(text):
        for word in CONTROL_WORDS:
            if re.match(rf"^{word}\b", line):
                signature.append(word)
                break
    return tuple(signature)


def structural_signature(text: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    return paragraph_names(text), control_signature(text)


def program_metrics(directory: Path) -> dict[str, dict[str, object]]:
    metrics: dict[str, dict[str, object]] = {}
    for path in sorted([*directory.glob("*.cob"), *directory.glob("*.cbl")]):
        text = path.read_text(encoding="utf-8")
        canonical = canonical_logic(text)
        metrics[path.name] = {
            "canonical_hash": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            "structural_signature": structural_signature(text),
        }
    return metrics


def validate_directory(directory: Path, *, max_structural_clone_fraction: float = 0.75) -> list[str]:
    errors: list[str] = []
    metrics = program_metrics(directory)
    if len(metrics) < 2:
        return errors

    exact_groups: dict[str, list[str]] = defaultdict(list)
    structural_groups: dict[tuple[tuple[str, ...], tuple[str, ...]], list[str]] = defaultdict(list)
    for name, item in metrics.items():
        exact_groups[str(item["canonical_hash"])].append(name)
        structural_groups[item["structural_signature"]].append(name)  # type: ignore[index]

    for names in exact_groups.values():
        if len(names) > 1:
            errors.append(
                "business modules are logic-equivalent after identity/noise normalization: "
                + ", ".join(sorted(names))
            )

    largest = max(structural_groups.values(), key=len)
    limit = max(3, math.ceil(len(metrics) * max_structural_clone_fraction))
    if len(largest) >= limit:
        errors.append(
            f"{len(largest)} of {len(metrics)} business modules share the same paragraph/control-flow "
            f"signature (limit before rejection: {limit - 1}); copied thick templates are scale padding: "
            + ", ".join(sorted(largest))
        )
    return errors


def validate(task_name: str) -> int:
    task_dir = ROOT / task_name
    production_manifest = ROOT / ".terminus" / "designs" / f"{task_name}-production.json"
    if not production_manifest.is_file():
        print("business_module_diversity=not-declared; no production portfolio check applies")
        return 0
    data = load_json(production_manifest)
    cfg = data.get("production_authenticity", {})
    if not isinstance(cfg, dict):
        raise SystemExit("production_authenticity must be an object")
    cobol = cfg.get("cobol_depth")
    if not isinstance(cobol, dict):
        print("business_module_diversity=no-cobol-profile")
        return 0
    directory = task_dir / str(cobol.get("directory", "environment/eod/cobol"))
    if not directory.is_dir():
        print(f"ERROR: business-module directory missing: {directory}", file=sys.stderr)
        return 1
    fraction = float(cobol.get("max_structural_clone_fraction", 0.75))
    if not 0.5 <= fraction <= 0.9:
        print("ERROR: max_structural_clone_fraction must be between 0.5 and 0.9", file=sys.stderr)
        return 1
    errors = validate_directory(directory, max_structural_clone_fraction=fraction)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"business-module diversity gate: FAIL ({len(errors)} finding(s))", file=sys.stderr)
        return 1
    print(f"business-module diversity gate: PASS (programs={len(program_metrics(directory))})")
    return 0


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: validate_business_module_diversity.py TASK", file=sys.stderr)
        return 2
    return validate(sys.argv[1])


if __name__ == "__main__":
    raise SystemExit(main())
