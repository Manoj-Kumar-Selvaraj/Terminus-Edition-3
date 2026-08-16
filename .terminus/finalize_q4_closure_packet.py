#!/usr/bin/env python3
"""One-shot installer for structural Q4-closure packet bindings."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    generator = ROOT / ".terminus/new_q4_closure_packet.py"
    text = generator.read_text(encoding="utf-8")
    anchor = '    packet["question"] = (\n'
    addition = (
        '    packet["closure_policy_version"] = "1.0"\n'
        '    packet["boundary_adjudication"] = boundary_rel\n'
        '    packet["final_q4_result"] = q4_rel\n'
        '    packet["repair_base_task_commit"] = args.repair_base\n'
        '    packet["final_task_commit"] = final_commit\n'
        '    packet["finding_fingerprints"] = {}\n\n'
    )
    if text.count(anchor) != 1:
        raise SystemExit("generator structural-binding anchor mismatch")
    text = text.replace(anchor, addition + anchor, 1)
    old_fp = (
        '        packet["evidence_allowed"].append(\n'
        '            f"q4_finding:{finding_id}:{finding_fingerprint(finding)}"\n'
        '        )\n'
    )
    new_fp = (
        '        fingerprint = finding_fingerprint(finding)\n'
        '        packet["finding_fingerprints"][finding_id] = fingerprint\n'
        '        packet["evidence_allowed"].append(\n'
        '            f"q4_finding:{finding_id}:{fingerprint}"\n'
        '        )\n'
    )
    if text.count(old_fp) != 1:
        raise SystemExit("generator fingerprint anchor mismatch")
    generator.write_text(text.replace(old_fp, new_fp, 1), encoding="utf-8")

    schema_path = ROOT / ".terminus/agents/schemas/context_packet.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    props = schema["properties"]
    props["closure_policy_version"] = {"type": "string", "minLength": 1}
    props["boundary_adjudication"] = {"type": "string", "minLength": 1}
    props["final_q4_result"] = {"type": "string", "minLength": 1}
    props["repair_base_task_commit"] = {"type": "string", "minLength": 40}
    props["final_task_commit"] = {"type": "string", "minLength": 40}
    props["finding_fingerprints"] = {"type": "object"}
    closure_required = [
        "closure_policy_version",
        "boundary_adjudication",
        "final_q4_result",
        "repair_base_task_commit",
        "final_task_commit",
        "finding_fingerprints",
    ]
    schema["allOf"] = [
        item
        for item in schema.get("allOf", [])
        if item.get("if", {}).get("properties", {}).get("role", {}).get("const")
        != "Q4 Closure Adjudicator"
    ]
    schema["allOf"].append(
        {
            "if": {"properties": {"role": {"const": "Q4 Closure Adjudicator"}}},
            "then": {"required": closure_required},
        }
    )
    schema_path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")

    closure_path = ROOT / ".terminus/q4_closure.py"
    ctext = closure_path.read_text(encoding="utf-8")
    boundary_anchor = "    boundary = None\n    q4 = None\n"
    boundary_checks = (
        '    if packet.get("closure_policy_version") != "1.0":\n'
        '        errors.append("closure packet policy version must be 1.0")\n'
        '    if packet.get("boundary_adjudication") != boundary_rel:\n'
        '        errors.append("closure packet top-level boundary binding mismatch")\n'
        '    if packet.get("final_q4_result") != final_q4_rel:\n'
        '        errors.append("closure packet top-level final-Q4 binding mismatch")\n'
        '    if packet.get("repair_base_task_commit") != repair_base:\n'
        '        errors.append("closure packet top-level repair-base binding mismatch")\n'
        '    if packet.get("final_task_commit") != final_commit:\n'
        '        errors.append("closure packet top-level final-task binding mismatch")\n\n'
    )
    if ctext.count(boundary_anchor) != 1:
        raise SystemExit("closure validator boundary anchor mismatch")
    ctext = ctext.replace(boundary_anchor, boundary_checks + boundary_anchor, 1)
    fp_anchor = "    packet_fps: dict[str, str] = {}\n"
    fp_check = (
        '    top_level_fps = packet.get("finding_fingerprints")\n'
        '    if not isinstance(top_level_fps, dict) or top_level_fps != expected_fps:\n'
        '        errors.append("closure packet top-level finding fingerprints do not exactly bind final Q4")\n\n'
    )
    if ctext.count(fp_anchor) != 1:
        raise SystemExit("closure validator fingerprint anchor mismatch")
    closure_path.write_text(ctext.replace(fp_anchor, fp_check + fp_anchor, 1), encoding="utf-8")

    test_path = ROOT / ".terminus/tests/test_q4_closure.py"
    ttext = test_path.read_text(encoding="utf-8")
    fixture_anchor = (
        '    closure_packet["evidence_allowed"] = [\n'
        '        f"boundary_adjudication:{boundary_rel}",\n'
        '        f"final_q4_result:{q4_rel}",\n'
        '        f"repair_diff:{base}..{final}:{task}",\n'
        '        f"q4_finding:Q4-001:{fp}",\n'
        '    ]\n'
    )
    fixture_new = fixture_anchor + (
        '    closure_packet["closure_policy_version"] = "1.0"\n'
        '    closure_packet["boundary_adjudication"] = boundary_rel\n'
        '    closure_packet["final_q4_result"] = q4_rel\n'
        '    closure_packet["repair_base_task_commit"] = base\n'
        '    closure_packet["final_task_commit"] = final\n'
        '    closure_packet["finding_fingerprints"] = {"Q4-001": fp}\n'
    )
    if ttext.count(fixture_anchor) != 1:
        raise SystemExit("closure test fixture anchor mismatch")
    ttext = ttext.replace(fixture_anchor, fixture_new, 1)
    extra = '''


def test_ready_closure_rejects_top_level_chain_drift(tmp_path: Path) -> None:
    root, rel = _fixture(tmp_path)
    result = json.loads((root / rel).read_text())
    packet_path = root / result["context_packet"]
    packet = json.loads(packet_path.read_text())
    packet["final_task_commit"] = "0" * 40
    packet_path.write_text(json.dumps(packet))
    errors, _ = q4_closure.validate_ready_closure(root, rel)
    assert any("top-level final-task binding mismatch" in error for error in errors)


def test_ready_closure_rejects_top_level_fingerprint_drift(tmp_path: Path) -> None:
    root, rel = _fixture(tmp_path)
    result = json.loads((root / rel).read_text())
    packet_path = root / result["context_packet"]
    packet = json.loads(packet_path.read_text())
    packet["finding_fingerprints"]["Q4-001"] = "0" * 64
    packet_path.write_text(json.dumps(packet))
    errors, _ = q4_closure.validate_ready_closure(root, rel)
    assert any("top-level finding fingerprints" in error for error in errors)
'''
    if "test_ready_closure_rejects_top_level_chain_drift" in ttext:
        raise SystemExit("closure top-level regression tests already exist")
    test_path.write_text((ttext.rstrip() + extra).rstrip() + "\n", encoding="utf-8")

    print("Q4 closure packet structural bindings installed in working tree")


if __name__ == "__main__":
    main()
