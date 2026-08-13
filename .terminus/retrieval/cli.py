#!/usr/bin/env python3
"""CLI for building and querying the local Terminus retrieval index."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from retrieval.embeddings import HashingEmbedder, SentenceTransformerEmbedder
    from retrieval.engine import RetrievalEngine
    from retrieval.indexer import RepositoryIndexer
    from retrieval.models import InvocationContext, RetrievalQuery
    from retrieval.policy import RetrievalPolicy
    from retrieval.store import RetrievalStore
else:
    from .embeddings import HashingEmbedder, SentenceTransformerEmbedder
    from .engine import RetrievalEngine
    from .indexer import RepositoryIndexer
    from .models import InvocationContext, RetrievalQuery
    from .policy import RetrievalPolicy
    from .store import RetrievalStore


def _head(root: Path) -> str:
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _root(value: str) -> Path:
    return Path(value).resolve()


def _db(root: Path, value: str | None) -> Path:
    return Path(value).resolve() if value else root / ".terminus" / "cache" / "retrieval.sqlite3"


def _embedder(value: str):
    if value == "hashing":
        return HashingEmbedder()
    prefix = "sentence-transformers:"
    if value.startswith(prefix):
        return SentenceTransformerEmbedder(value[len(prefix) :])
    raise ValueError(f"unknown embedder: {value}")


def _context(args: argparse.Namespace, root: Path) -> InvocationContext:
    control_plane_commit = args.control_plane_commit or _head(root)
    task_commit = args.task_commit or (control_plane_commit if args.task_id else None)
    return InvocationContext(
        stage_id=args.stage,
        role_id=args.role,
        task_id=args.task_id,
        task_commit=task_commit,
        control_plane_commit=control_plane_commit,
        role_contract_hash=args.role_contract_hash,
        packet_binding=args.packet_binding,
        review_scope_hash=args.review_scope_hash,
        ci_run_id=args.ci_run_id,
        policy_versions=_key_values(args.policy_version),
        allowed_evidence_classes=(
            frozenset(args.allow_evidence) if args.allow_evidence else None
        ),
        excluded_evidence_classes=frozenset(args.exclude_evidence),
        allowed_sensitivities=(
            frozenset(args.allow_sensitivity) if args.allow_sensitivity else None
        ),
    )


def _query(args: argparse.Namespace) -> RetrievalQuery:
    return RetrievalQuery(
        text=args.query or "",
        mode=args.mode,
        limit=args.limit,
        source_kinds=tuple(args.source_kind),
        evidence_classes=tuple(args.evidence_class),
        source_paths=tuple(args.source_path),
        symbols=tuple(args.symbol),
        section_terms=tuple(args.section),
        exact_phrase=args.exact_phrase,
    )


def _key_values(values: list[str]) -> dict[str, str]:
    output: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"expected NAME=VALUE: {value}")
        key, item = value.split("=", 1)
        output[key] = item
    return output


def _common_retrieval_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--stage", required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--task-id")
    parser.add_argument("--task-commit")
    parser.add_argument("--control-plane-commit")
    parser.add_argument("--role-contract-hash")
    parser.add_argument("--packet-binding")
    parser.add_argument("--review-scope-hash")
    parser.add_argument("--ci-run-id")
    parser.add_argument("--policy-version", action="append", default=[])
    parser.add_argument("--allow-evidence", action="append", default=[])
    parser.add_argument("--exclude-evidence", action="append", default=[])
    parser.add_argument("--allow-sensitivity", action="append", default=[])
    parser.add_argument("--query", default="")
    parser.add_argument(
        "--mode", choices=["auto", "exact", "lexical", "vector", "hybrid"], default="auto"
    )
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--source-kind", action="append", default=[])
    parser.add_argument("--evidence-class", action="append", default=[])
    parser.add_argument("--source-path", action="append", default=[])
    parser.add_argument("--symbol", action="append", default=[])
    parser.add_argument("--section", action="append", default=[])
    parser.add_argument("--exact-phrase")
    parser.add_argument("--embedder", default="hashing")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".")
    parser.add_argument("--db")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="build/update the commit-bound index")
    build.add_argument("--task-path")
    build.add_argument("--task-id")
    build.add_argument("--commit")
    build.add_argument("--include-private-design", action="store_true")

    retrieve = subparsers.add_parser("retrieve", help="retrieve authorized chunks")
    _common_retrieval_arguments(retrieve)

    context = subparsers.add_parser(
        "context", help="emit exact-read requirements plus bounded retrieved context"
    )
    _common_retrieval_arguments(context)
    context.add_argument("--max-chars", type=int, default=30000)

    subparsers.add_parser("stats", help="show local index/cache statistics")
    subparsers.add_parser("manifest", help="show the latest index manifest")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = _root(args.root)
    db_path = _db(root, args.db)
    policy = RetrievalPolicy(root)

    with RetrievalStore(db_path) as store:
        if args.command == "build":
            manifest = RepositoryIndexer(root, store, policy).build(
                task_path=args.task_path,
                task_id=args.task_id,
                commit=args.commit,
                include_private_design=args.include_private_design,
            )
            print(json.dumps(manifest, indent=2, sort_keys=True))
            return 0
        if args.command == "stats":
            print(json.dumps(store.stats(), indent=2, sort_keys=True))
            return 0
        if args.command == "manifest":
            print(json.dumps(store.latest_manifest(), indent=2, sort_keys=True))
            return 0

        engine = RetrievalEngine(
            root,
            store,
            policy=policy,
            embedder=_embedder(args.embedder),
        )
        invocation = _context(args, root)
        query = _query(args)
        if args.command == "context":
            payload = engine.context_bundle(
                invocation,
                query,
                max_chars=args.max_chars,
            )
        else:
            payload = [
                {
                    "chunk_id": result.chunk_id,
                    "document_id": result.document_id,
                    "source_path": result.metadata.get("source_path"),
                    "source_kind": result.metadata.get("source_kind"),
                    "evidence_class": result.metadata.get("evidence_class"),
                    "structural_locator": result.metadata.get("structural_locator"),
                    "exact_score": result.exact_score,
                    "lexical_score": result.lexical_score,
                    "vector_score": result.vector_score,
                    "fused_score": result.fused_score,
                    "content": result.content,
                }
                for result in engine.retrieve(invocation, query)
            ]
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
