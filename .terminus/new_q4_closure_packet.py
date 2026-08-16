#!/usr/bin/env python3
"""Generate an immutable packet for post-circuit-breaker Q4 closure adjudication."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import new_review_packet
from q4_closure import finding_fingerprint, validate_frozen_pair
from review_contract import current_task_commit, governing_policy_dirty, task_tree_dirty, validate_schema

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / ".terminus"


def _rel(path_text: str) -> str:
    path = Path(path_text)
    path = path if path.is_absolute() else ROOT / path
    resolved = path.resolve()
    resolved.relative_to(ROOT.resolve())
    return resolved.relative_to(ROOT.resolve()).as_posix()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task")
    parser.add_argument("--boundary-adjudication", required=True)
    parser.add_argument("--final-q4", required=True)
    parser.add_argument("--repair-base", required=True)
    args = parser.parse_args(argv)

    if not (ROOT / args.task / "task.toml").is_file():
        print(f"error: no task at {args.task}/task.toml")
        return 2
    final_commit = current_task_commit(ROOT, args.task)
    if not final_commit:
        print(f"error: cannot resolve task commit for {args.task}")
        return 2
    if task_tree_dirty(ROOT, args.task):
        print("refused: task tree is dirty")
        return 1
    if governing_policy_dirty(ROOT, "Q4 Closure Adjudicator"):
        print("refused: Q4 Closure Adjudicator governing policy is dirty")
        return 1

    boundary_rel = _rel(args.boundary_adjudication)
    q4_rel = _rel(args.final_q4)
    boundary, _, errors = validate_frozen_pair(
        ROOT, boundary_rel, "Adjudicator", args.task, args.repair_base
    )
    q4, _, q4_errors = validate_frozen_pair(
        ROOT, q4_rel, "Spec-Test Contract Reviewer", args.task, final_commit
    )
    errors.extend(q4_errors)
    if errors:
        for error in errors:
            print(f"error: {error}")
        return 1
    assert boundary is not None and q4 is not None
    if q4.get("verdict") != "REVISE":
        print("error: closure adjudication requires final frozen Q4 REVISE")
        return 1
    if boundary.get("evidence_status") != "SUFFICIENT" or boundary.get("confidence") == "LOW":
        print("error: boundary adjudication is not sufficient")
        return 1
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", args.repair_base, final_commit],
        cwd=ROOT,
        check=False,
    )
    if ancestor.returncode != 0:
        print("error: repair-base commit is not an ancestor of final task commit")
        return 1

    packet = new_review_packet.build(
        args.task,
        "q4-closure-adjudication",
        "Q4_CLOSURE_ADJUDICATION",
        (
            "Post-circuit-breaker Q4 closure reconciliation. This packet does not authorize task edits "
            "or another exhaustive Q4. Reconcile every final-Q4 finding against the frozen boundary "
            "and exact boundary-to-final task diff under Q4_CLOSURE_POLICY.md."
        ),
        final_commit,
    )
    packet["question"] = (
        "Does the final frozen Q4 leave any legitimately controlling blocker after applying the "
        "frozen adjudicated closure boundary and exact final-repair provenance?"
    )
    packet["authoritative_rules"] = [
        "TERMINUS_3_AI_INSTRUCTIONS.md",
        ".terminus/AGENT_SYSTEM.md",
        ".terminus/agents/PROTOCOL.md",
        ".terminus/agents/Q4_CLOSURE_POLICY.md",
        ".terminus/agents/PROMPTS.md",
    ]
    packet["evidence_allowed"] = [
        f"boundary_adjudication:{boundary_rel}",
        f"final_q4_result:{q4_rel}",
        f"repair_diff:{args.repair_base}..{final_commit}:{args.task}",
        "current authoritative rules",
    ]
    for finding in q4.get("findings", []):
        finding_id = str(finding.get("id", ""))
        if not finding_id:
            print("error: final Q4 contains finding with empty ID")
            return 1
        packet["evidence_allowed"].append(
            f"q4_finding:{finding_id}:{finding_fingerprint(finding)}"
        )
    packet["evidence_excluded"] = [
        "desired closure outcome",
        "task edits or proposed fixes",
        "unfrozen reviewer opinions",
        "unrelated historical reviews outside the frozen boundary chain",
    ]
    packet["prior_verdicts_visible"] = True

    schema = json.loads((T / "agents/schemas/context_packet.schema.json").read_text(encoding="utf-8"))
    problems: list[str] = []
    validate_schema(packet, schema, "packet", problems)
    if problems:
        print("refused: generated closure packet fails context schema")
        for problem in problems:
            print(f"- {problem}")
        return 1
    review_path = ROOT / packet["review_output_path"]
    packet_path = review_path.with_suffix(".packet.json")
    packet_path.parent.mkdir(parents=True, exist_ok=True)
    if packet_path.exists() or review_path.exists():
        print(f"refused: immutable review ID already exists: {packet['review_id']}")
        return 1
    packet_path.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {packet_path.relative_to(ROOT)}")
    print(f"review_output={review_path.relative_to(ROOT)}")
    print(f"review_id={packet['review_id']}")
    print(f"task_commit={final_commit}")
    print(f"role_contract={packet['role_contract_hash']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
