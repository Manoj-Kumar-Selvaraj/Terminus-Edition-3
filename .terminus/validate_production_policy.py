#!/usr/bin/env python3
"""Guard the local production-authenticity creator/reviewer policy against drift."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / ".terminus"

REQUIRED = {
    T / "agents/PRODUCTION_AUTHENTICITY.md": ["Production evidence surface", "10,000–20,000", "Business-logic depth", "incident evidence test", "thin business logic", "Reviewer obligations"],
    T / "agents/CREATION_PIPELINE.md": ["PRODUCTION_AUTHENTICITY.md", "validate_runtime_authenticity.py", "production evidence surface", "10,000–20,000", "thin business logic"],
    T / "agents/CREATION_CONTROLLER.md": ["PRODUCTION_AUTHENTICITY.md", "RUNTIME_AUTHENTICITY", "10,000–20,000", "one IF = one program"],
    T / "agents/CREATOR_AGENT_REGISTRY.md": ["PRODUCTION_AUTHENTICITY.md", "10,000–20,000", "micro-program", "validate_runtime_authenticity.py"],
    T / "agents/INVOKE.md": ["PRODUCTION_AUTHENTICITY.md", "production evidence surface", "micro-program/module inflation", "toy production data", "unsupported incident backstory"],
    T / "review_contract.py": ["PRODUCTION_AUTHENTICITY.md", "role_contract_inputs"],
    T / "validate_runtime_authenticity.py": ["SYNTHETIC_README_PHRASES", "min_substantive_lines_per_program", "min_decision_points_per_program", "min_records", "10000", "20000", "random()"],
    ROOT / ".github/workflows/terminus-production-authenticity.yml": ["instruction.md", "README.md", "validate_runtime_authenticity.py", "test_runtime_authenticity.py"],
}


def main() -> int:
    errors: list[str] = []
    for path, markers in REQUIRED.items():
        if not path.is_file():
            errors.append(f"missing required production-authenticity file: {path.relative_to(ROOT)}")
            continue
        text = path.read_text(encoding="utf-8").lower()
        for marker in markers:
            if marker.lower() not in text:
                errors.append(f"{path.relative_to(ROOT)} missing marker: {marker}")
    if errors:
        print("Terminus production-authenticity policy validation FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Terminus production-authenticity policy validation PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
