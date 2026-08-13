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
from retrieval.policy import RetrievalPolicy  # noqa: E402
from retrieval.store import RetrievalStore  # noqa: E402

REQUIRED = [
    T / "agents" / "RETRIEVAL_ENGINE.md",
    T / "agents" / "RETRIEVAL_METADATA.md",
    T / "agents" / "STAGE_CONTRACTS.md",
    T / "retrieval" / "__init__.py",
    T / "retrieval" / "models.py",
    T / "retrieval" / "policy.py",
    T / "retrieval" / "chunking.py",
    T / "retrieval" / "store.py",
    T / "retrieval" / "embeddings.py",
    T / "retrieval" / "indexer.py",
    T / "retrieval" / "engine.py",
    T / "retrieval" / "cli.py",
    T / "tests" / "test_retrieval_engine.py",
    T / "tests" / "test_retrieval_cache.py",
]

POLICY_MARKERS = [
    "Retrieval engine policy version: `1.0`",
    "Mandatory exact reads",
    "Commit-bound indexing",
    "Authorization and freshness",
    "EXACT_ONLY",
    "FILTERED_HYBRID",
    "SOLVER_VISIBLE_ONLY",
    "EXTERNAL_BOUND",
    "Caching",
    "Normal ChatGPT portability",
    "Agent integration",
]

STAGE_MARKERS = [
    "Retrieval adapter contract",
    "mandatory_exact_reads",
    "optional projection adapter",
    "direct exact repository/GitHub reads",
    "RETRIEVAL_ENGINE.md",
]

METADATA_MARKERS = [
    "Implemented caching contract",
    "parse/chunk cache",
    "embedding cache",
    "retrieval-result cache",
    "Reference retrieval engine",
    "Dynamic evidence boundary",
]


def _require_markers(
    errors: list[str], text: str, label: str, markers: list[str]
) -> None:
    lower = text.lower()
    for marker in markers:
        if marker.lower() not in lower:
            errors.append(f"{label} missing marker: {marker}")


def main() -> int:
    errors: list[str] = []
    for path in REQUIRED:
        if not path.is_file():
            errors.append(f"missing required file: {path.relative_to(ROOT)}")

    policy_text = (T / "agents" / "RETRIEVAL_ENGINE.md").read_text(encoding="utf-8")
    _require_markers(errors, policy_text, "RETRIEVAL_ENGINE.md", POLICY_MARKERS)

    stage_text = (T / "agents" / "STAGE_CONTRACTS.md").read_text(encoding="utf-8")
    _require_markers(errors, stage_text, "STAGE_CONTRACTS.md", STAGE_MARKERS)

    metadata_text = (T / "agents" / "RETRIEVAL_METADATA.md").read_text(encoding="utf-8")
    _require_markers(errors, metadata_text, "RETRIEVAL_METADATA.md", METADATA_MARKERS)
    stale_future_marker = "What this step intentionally does not implement"
    if stale_future_marker.lower() in metadata_text.lower():
        errors.append("RETRIEVAL_METADATA.md still describes the retrieval engine as unimplemented")

    policy = RetrievalPolicy(ROOT)
    if len(policy.stages) != 23:
        errors.append(f"expected 23 registered stages, found {len(policy.stages)}")
    if len(policy.role_ids) != 34:
        errors.append(f"expected 34 canonical roles, found {len(policy.role_ids)}")
    if policy.retrieval_mode("RULE_RESOLUTION") != "EXACT_ONLY":
        errors.append("RULE_RESOLUTION must remain EXACT_ONLY")
    if policy.retrieval_mode("MODEL_DIAGNOSTIC") != "SOLVER_VISIBLE_ONLY":
        errors.append("MODEL_DIAGNOSTIC must remain SOLVER_VISIBLE_ONLY")
    instruction_paths = policy.mandatory_exact_paths("INSTRUCTION_DRAFT")
    if ".terminus/agents/INSTRUCTION_POLICY.md" not in instruction_paths:
        errors.append("INSTRUCTION_DRAFT must exact-read INSTRUCTION_POLICY.md")

    vector = HashingEmbedder().embed(["replay recovery"])[0]
    if len(vector) != 384:
        errors.append("default hashing embedder must emit 384 dimensions")
    if not any(vector):
        errors.append("default hashing embedder emitted an empty vector")

    with tempfile.TemporaryDirectory() as directory:
        with RetrievalStore(Path(directory) / "retrieval.sqlite3") as store:
            stats = store.stats()
            if stats["documents"] != 0 or stats["chunks"] != 0:
                errors.append("fresh retrieval store is not empty")
            if stats.get("parse_cache_entries") != 0:
                errors.append("fresh retrieval parse cache is not empty")
            if "fts5" not in stats:
                errors.append("retrieval store must report lexical backend availability")

    if errors:
        print("Terminus retrieval-engine validation FAILED:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Terminus retrieval-engine validation PASS")
    print(
        "engine=1.0 stages=23 canonical_roles=34 "
        "exact_reads=mandatory lexical=fts5_or_bm25 vector=pluggable "
        "hybrid=rrf caches=parse_embedding_result authorization=pre_rank "
        "integration=stage_adapter portability=direct_read_fallback"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
