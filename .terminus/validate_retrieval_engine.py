#!/usr/bin/env python3
"""Validate the local Terminus retrieval engine contract and wiring."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / ".terminus"
sys.path.insert(0, str(T))

from retrieval.embeddings import HashingEmbedder  # noqa: E402
from retrieval.models import InvocationContext  # noqa: E402
from retrieval.policy import RetrievalPolicy  # noqa: E402
from retrieval.store import RetrievalStore  # noqa: E402


def main() -> int:
    errors: list[str] = []
    required = [
        ROOT / ".gitignore", T / "agents" / "RETRIEVAL_ENGINE.md",
        T / "agents" / "RETRIEVAL_METADATA.md", T / "agents" / "DYNAMIC_EVIDENCE_INGESTION.md",
        T / "agents" / "STAGE_CONTRACTS.md", T / "retrieval" / "models.py",
        T / "retrieval" / "policy.py", T / "retrieval" / "chunking.py",
        T / "retrieval" / "store.py", T / "retrieval" / "embeddings.py",
        T / "retrieval" / "indexer.py", T / "retrieval" / "ingestion.py",
        T / "retrieval" / "engine.py", T / "retrieval" / "cli.py",
    ]
    for path in required:
        if not path.is_file():
            errors.append(f"missing required file: {path.relative_to(ROOT)}")
    if ".terminus/cache/" not in (ROOT / ".gitignore").read_text(encoding="utf-8"):
        errors.append(".gitignore must exclude .terminus/cache/")

    engine_policy = (T / "agents" / "RETRIEVAL_ENGINE.md").read_text(encoding="utf-8")
    for marker in ["Retrieval engine policy version: `1.0`","Mandatory exact reads","Commit-bound indexing","Authorization and freshness","EXACT_ONLY","FILTERED_HYBRID","SOLVER_VISIBLE_ONLY","EXTERNAL_BOUND","Caching","Normal ChatGPT portability"]:
        if marker.lower() not in engine_policy.lower():
            errors.append(f"RETRIEVAL_ENGINE.md missing marker: {marker}")
    indexer = (T / "retrieval" / "indexer.py").read_text(encoding="utf-8")
    for marker in ["control_plane_commit","task_commit","source_commit","structural-v2","PRIVATE_WORK_PACKAGE_DESIGN","PRIVATE_SYSTEM_ARCHITECTURE","PRIVATE_DEFECT_TOPOLOGY","PRIVATE_TEST_MAP"]:
        if marker not in indexer:
            errors.append(f"indexer.py missing marker: {marker}")
    ingestion = (T / "retrieval" / "ingestion.py").read_text(encoding="utf-8")
    for marker in ["DynamicEvidenceIngestor","REVIEW_PACKET","REVIEW_RESULT","SESSION_STATE","CI_RUNTIME","MODEL_TRIAL","FINAL_PACKAGE","PUBLIC_REFERENCE","_validate_projection"]:
        if marker not in ingestion:
            errors.append(f"ingestion.py missing marker: {marker}")

    policy = RetrievalPolicy(ROOT)
    if policy.retrieval_mode("RULE_RESOLUTION") != "EXACT_ONLY":
        errors.append("RULE_RESOLUTION must remain EXACT_ONLY")
    for stage_id in ("MODEL_DIAGNOSTIC_GPT","MODEL_DIAGNOSTIC_CLAUDE"):
        if policy.retrieval_mode(stage_id) != "SOLVER_VISIBLE_ONLY":
            errors.append(f"{stage_id} must remain SOLVER_VISIBLE_ONLY")
        authorized = policy.authorized_evidence_classes(
            InvocationContext(stage_id=stage_id, role_id="Q8_MODEL_PERSPECTIVE_DIFFICULTY_SIMULATOR")
        )
        if authorized != frozenset({"CONTROL_PLANE_POLICY","SOLVER_VISIBLE_TASK"}):
            errors.append(f"{stage_id} must expose only control policy + solver-visible task")
    if policy.retrieval_mode("HARBOR_LLMAJ") != "EXTERNAL_BOUND":
        errors.append("HARBOR_LLMAJ must use EXTERNAL_BOUND")
    if policy.retrieval_mode("OFFICIAL_MODEL_TRIALS") != "EXTERNAL_BOUND":
        errors.append("OFFICIAL_MODEL_TRIALS must use EXTERNAL_BOUND")
    if ".terminus/agents/INSTRUCTION_POLICY.md" not in policy.mandatory_exact_paths("INSTRUCTION_DRAFT"):
        errors.append("INSTRUCTION_DRAFT must exact-read INSTRUCTION_POLICY.md")

    for stage_id in sorted(policy.stages):
        try:
            roles = policy.allowed_roles_for_stage(stage_id)
        except ValueError as exc:
            errors.append(f"stage-role binding {stage_id}: {exc}")
            continue
        if not roles or set(roles) - policy.role_ids:
            errors.append(f"stage-role binding {stage_id} is invalid")
    if "Q8_MODEL_PERSPECTIVE_DIFFICULTY_SIMULATOR" in policy.allowed_roles_for_stage("DETERMINISTIC_VALIDATION"):
        errors.append("Q8 must not borrow deterministic-validation authority")
    if not {"Q4_SPEC_TEST_CONTRACT_REVIEWER","Q6_PRODUCTION_LOGIC_AUDITOR"} <= set(policy.allowed_roles_for_stage("QUALITY_INTERLOCK")):
        errors.append("QUALITY_INTERLOCK must retain Q4/Q6 review visibility")
    if "HARBOR_LLMAJ_GATE" not in policy.allowed_roles_for_stage("HARBOR_LLMAJ"):
        errors.append("Harbor role must be authorized for Harbor stage")

    dynamic = {"REVIEW_PACKET","REVIEW_RESULT","SESSION_STATE","CI_RUNTIME","MODEL_TRIAL","FINAL_PACKAGE","PUBLIC_REFERENCE"}
    if not dynamic <= policy.source_kinds:
        errors.append("dynamic ingestion source kinds are incomplete")
    if policy.source_profiles.get("REVIEW_RESULT", {}).get("default_evidence_class") != "CURRENT_REVIEW_PACKET":
        errors.append("REVIEW_RESULT must be current freshness-bound review evidence")

    vector = HashingEmbedder().embed(["replay recovery"])[0]
    if len(vector) != 384 or not any(vector):
        errors.append("default hashing embedder must emit non-empty 384 dimensions")
    with tempfile.TemporaryDirectory() as directory:
        with RetrievalStore(Path(directory) / "retrieval.sqlite3") as store:
            stats = store.stats()
            if stats["documents"] or stats["chunks"] or stats.get("parse_cache_entries"):
                errors.append("fresh retrieval store is not empty")
            if "fts5" not in stats:
                errors.append("retrieval store must report lexical backend availability")

    if errors:
        print("Terminus retrieval-engine validation FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Terminus retrieval-engine validation PASS")
    print(f"engine=1.0 stages={len(policy.stages)} canonical_roles={len(policy.role_ids)} exact_reads=mandatory lexical=fts5_or_bm25 vector=pluggable hybrid=rrf caches=parse_embedding_result authorization=pre_rank_stage_role q8=dual_solver_visible_only harbor=external_bound dynamic_ingestion=explicit_provenance portability=direct_read_fallback")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
