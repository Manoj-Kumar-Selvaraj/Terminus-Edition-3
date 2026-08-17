#!/usr/bin/env python3
"""CLI for the measured human-writing learning loop."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from contamination import analyze_contamination
from corpus_cache import HumanWritingCorpusCache
from evaluation import prepare_blind_ab, score_blind_ab
from learning_loop import HumanWritingLearningStore
from preference_store import TerminusPreferenceStore


def _json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(value: Any, output: str | None) -> None:
    rendered = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if output:
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("cache-ingest")
    ingest.add_argument("--input", required=True)
    ingest.add_argument("--cache")

    search = sub.add_parser("cache-search")
    search.add_argument("--query", required=True)
    search.add_argument("--role-signal", choices=["writer", "reviewer"])
    search.add_argument("--artifact-type", action="append", default=[])
    search.add_argument("--exclude", action="append", default=[])
    search.add_argument("--limit", type=int, default=12)
    search.add_argument("--min-score", type=float)
    search.add_argument("--cache")
    search.add_argument("--output")

    contam = sub.add_parser("contamination-check")
    contam.add_argument("--draft", required=True)
    contam.add_argument("--profile")
    contam.add_argument("--source-key", action="append", default=[])
    contam.add_argument("--cache")
    contam.add_argument("--output")

    ab = sub.add_parser("ab-prepare")
    ab.add_argument("--task-id", required=True)
    ab.add_argument("--baseline", required=True)
    ab.add_argument("--calibrated", required=True)
    ab.add_argument("--requirement-contract-sha256", required=True)
    ab.add_argument("--writer-actor-id", required=True)
    ab.add_argument("--output", required=True)
    ab.add_argument("--sealed-mapping-output", required=True)

    ab_score = sub.add_parser("ab-score")
    ab_score.add_argument("--public", required=True)
    ab_score.add_argument("--sealed-mapping", required=True)
    ab_score.add_argument("--scores", required=True)
    ab_score.add_argument("--evaluator-actor-id", required=True)
    ab_score.add_argument(
        "--evaluator-role",
        choices=["Instruction Reviewer", "Human Quality Reviewer", "Blind A/B Evaluator"],
        required=True,
    )
    ab_score.add_argument("--output")

    outcome = sub.add_parser("record-outcome")
    outcome.add_argument("--input", required=True)
    outcome.add_argument("--state")

    metrics = sub.add_parser("metrics")
    metrics.add_argument("--state")
    metrics.add_argument("--output")

    recommend = sub.add_parser("recommend-weights")
    recommend.add_argument("--role", choices=["writer", "reviewer"], required=True)
    recommend.add_argument("--state")
    recommend.add_argument("--output")

    readiness = sub.add_parser("adapter-readiness")
    readiness.add_argument("--state")
    readiness.add_argument("--output")

    pref_add = sub.add_parser("preference-add")
    pref_add.add_argument("--task-id", required=True)
    pref_add.add_argument("--task-commit", required=True)
    pref_add.add_argument("--rejected", required=True)
    pref_add.add_argument("--chosen", required=True)
    pref_add.add_argument("--label-source", required=True)
    pref_add.add_argument("--reason-code", action="append", default=[])
    pref_add.add_argument("--calibration-pair-id", required=True)
    pref_add.add_argument("--holdout-eligible", action="store_true")
    pref_add.add_argument("--preference-state")

    pref_summary = sub.add_parser("preference-summary")
    pref_summary.add_argument("--preference-state")
    pref_summary.add_argument("--output")

    args = parser.parse_args()
    root = Path(args.root).resolve()
    state_path = Path(args.state).resolve() if getattr(args, "state", None) else None
    cache_path = Path(args.cache).resolve() if getattr(args, "cache", None) else None
    preference_path = (
        Path(args.preference_state).resolve()
        if getattr(args, "preference_state", None)
        else None
    )

    if args.command == "cache-ingest":
        cache = HumanWritingCorpusCache(root, cache_path)
        count = 0
        for line in Path(args.input).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            cache.upsert(json.loads(line))
            count += 1
        _write_json({"status": "INGESTED", "count": count, "stats": cache.stats()}, None)
        return 0

    if args.command == "cache-search":
        cache = HumanWritingCorpusCache(root, cache_path)
        result = cache.search(
            args.query,
            role_signal=args.role_signal,
            artifact_types=args.artifact_type,
            exclude_source_keys=args.exclude,
            limit=args.limit,
            min_score=args.min_score,
        )
        _write_json(result, args.output)
        return 0

    if args.command == "contamination-check":
        cache = HumanWritingCorpusCache(root, cache_path)
        source_keys = set(args.source_key)
        if args.profile:
            profile = _json_file(Path(args.profile))
            cache_keys = set(profile.get("CACHE_SOURCE_KEYS_USED", []))
            source_keys.update(cache.retained_source_keys(cache_keys))
        references = cache.retained_texts(sorted(source_keys))
        if not references:
            result = {
                "status": "SKIPPED_NO_RAW_TEXT",
                "finding_count": 0,
                "findings": [],
                "source_keys_checked": [],
            }
            _write_json(result, args.output)
            return 0
        result = analyze_contamination(
            Path(args.draft).read_text(encoding="utf-8"), references
        )
        result["source_keys_checked"] = sorted(source_keys)
        _write_json(result, args.output)
        return 0 if result["status"] == "PASS" else 2

    if args.command == "ab-prepare":
        prepared = prepare_blind_ab(
            task_id=args.task_id,
            baseline_text=Path(args.baseline).read_text(encoding="utf-8"),
            calibrated_text=Path(args.calibrated).read_text(encoding="utf-8"),
            requirement_contract_sha256=args.requirement_contract_sha256,
            writer_actor_id=args.writer_actor_id,
        )
        _write_json(prepared["public_packet"], args.output)
        _write_json(prepared["sealed_mapping"], args.sealed_mapping_output)
        return 0

    if args.command == "ab-score":
        result = score_blind_ab(
            public_packet=_json_file(Path(args.public)),
            sealed_mapping=_json_file(Path(args.sealed_mapping)),
            scores=_json_file(Path(args.scores)),
            evaluator_actor_id=args.evaluator_actor_id,
            evaluator_role=args.evaluator_role,
        )
        _write_json(result, args.output)
        return 0

    if args.command in {"preference-add", "preference-summary"}:
        store = TerminusPreferenceStore(root, preference_path)
        if args.command == "preference-add":
            record = store.append(
                task_id=args.task_id,
                task_commit=args.task_commit,
                rejected_text=Path(args.rejected).read_text(encoding="utf-8"),
                chosen_text=Path(args.chosen).read_text(encoding="utf-8"),
                label_source=args.label_source,
                reason_codes=args.reason_code,
                calibration_pair_id=args.calibration_pair_id,
                holdout_eligible=args.holdout_eligible,
            )
            _write_json(
                {"status": "RECORDED", "preference_id": record["preference_id"]},
                None,
            )
            return 0
        _write_json(store.summary(), args.output)
        return 0

    store = HumanWritingLearningStore(root, state_path)
    if args.command == "record-outcome":
        record = store.append(_json_file(Path(args.input)))
        _write_json({"status": "RECORDED", "record_id": record["record_id"]}, None)
        return 0
    if args.command == "metrics":
        _write_json(store.metrics(), args.output)
        return 0
    if args.command == "recommend-weights":
        _write_json(store.recommend_weights(args.role), args.output)
        return 0
    if args.command == "adapter-readiness":
        _write_json(store.adapter_readiness(), args.output)
        return 0
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
