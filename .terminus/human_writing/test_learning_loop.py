"""Regression tests for the human-writing retrieval/evaluation/learning loop."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from contamination import analyze_contamination
from corpus_cache import CorpusCacheError, HumanWritingCorpusCache
from evaluation import aggregate_ab_results, prepare_blind_ab, score_blind_ab
from learning_loop import HumanWritingLearningStore
from preference_store import TerminusPreferenceStore


ROOT = Path(__file__).resolve().parents[2]


class HumanWritingLearningLoopTests(unittest.TestCase):
    def test_cache_enforces_dataset_and_attribution_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = HumanWritingCorpusCache(ROOT, Path(tmp) / "cache.sqlite3")
            with self.assertRaises(CorpusCacheError):
                cache.upsert(
                    {
                        "dataset_id": "github-human-codereview",
                        "source_id": "x",
                        "domain": "python",
                        "artifact_type": "review",
                        "role_signal": "reviewer",
                        "structural_summary": "specific review",
                    }
                )
            with self.assertRaises(CorpusCacheError):
                cache.upsert(
                    {
                        "dataset_id": "h4-stack-exchange-preferences",
                        "source_id": "q1",
                        "source_url": "https://example.invalid/q1",
                        "domain": "kubernetes recovery",
                        "artifact_type": "incident",
                        "role_signal": "writer",
                        "structural_summary": "restart symptom and expected state",
                        "text": "A retained source text requiring attribution.",
                    }
                )

    def test_cache_search_prefers_domain_match_and_hides_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache = HumanWritingCorpusCache(ROOT, Path(tmp) / "cache.sqlite3")
            cache.upsert(
                {
                    "dataset_id": "h4-stack-exchange-preferences",
                    "source_id": "q1",
                    "source_url": "https://example.invalid/q1",
                    "author": "A",
                    "author_url": "https://example.invalid/a",
                    "domain": "kubernetes recovery",
                    "artifact_type": "incident",
                    "role_signal": "writer",
                    "structural_summary": "restart failure after partial recovery",
                    "text": "The service restarts after partial recovery but repeats the same work.",
                }
            )
            cache.upsert(
                {
                    "dataset_id": "tulu3-constraint-preferences",
                    "source_id": "c1",
                    "source_url": "https://example.invalid/c1",
                    "domain": "python constraints",
                    "artifact_type": "preference_pair",
                    "role_signal": "writer",
                    "structural_summary": "one relaxed constraint invalidates the response",
                }
            )
            results = cache.search(
                "kubernetes restart recovery",
                role_signal="writer",
                artifact_types=["incident"],
            )
            self.assertEqual(results[0]["source_id"], "q1")
            self.assertNotIn("retained_text", results[0])

    def test_contamination_detects_near_copy_without_echoing_phrase(self) -> None:
        source = (
            "The controller retries completed operations after restart and publishes "
            "a second result even though the first result was already committed."
        )
        result = analyze_contamination(
            source,
            [{"source_key": "h4:q1", "text": source}],
        )
        self.assertEqual(result["status"], "REWRITE_REQUIRED")
        self.assertEqual(result["findings"][0]["source_key"], "h4:q1")
        self.assertNotIn(source, json.dumps(result))

    def test_blind_ab_completeness_is_hard_gate(self) -> None:
        prepared = prepare_blind_ab(
            task_id="demo",
            baseline_text="Complete but formal instruction.",
            calibrated_text="Natural instruction.",
            requirement_contract_sha256="a" * 64,
        )
        labels = prepared["public_packet"]["variants"]
        mapping = prepared["sealed_mapping"]["mapping"]
        scores = {}
        for label in labels:
            origin = mapping[label]
            scores[label] = {
                "requirement_completeness": 5 if origin == "baseline" else 4,
                "technical_precision": 5,
                "human_information_selection": 3 if origin == "baseline" else 5,
                "natural_grouping": 3 if origin == "baseline" else 5,
                "implementation_distance": 4,
                "verbosity_fit": 4,
                "ai_template_signal": 2 if origin == "baseline" else 0,
                "synthetic_completeness": 2 if origin == "baseline" else 0,
                "rubric_mirroring": 1,
                "implementation_leakage": 0,
            }
        result = score_blind_ab(
            public_packet=prepared["public_packet"],
            sealed_mapping=prepared["sealed_mapping"],
            scores=scores,
        )
        self.assertEqual(result["preferred_origin"], "baseline")
        self.assertFalse(result["calibrated_wins"])

    def test_ab_aggregate(self) -> None:
        summary = aggregate_ab_results(
            [
                {"preferred_origin": "calibrated"},
                {"preferred_origin": "baseline"},
                {"preferred_origin": "calibrated"},
                {"preferred_origin": "tie"},
            ]
        )
        self.assertEqual(summary["decided_results"], 3)
        self.assertAlmostEqual(summary["calibrated_win_rate"], 2 / 3)

    def test_learning_metrics_track_reviewer_disagreement(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "outcomes.jsonl"
            store = HumanWritingLearningStore(ROOT, state)
            base = {
                "task_id": "t1",
                "task_commit": "1" * 40,
                "calibration_pair_id": "pair",
                "writer_calibration_id": "writer",
                "reviewer_calibration_id": "reviewer",
                "draft_sha256": "a" * 64,
                "accepted_sha256": "b" * 64,
                "requirement_count": 8,
                "revision_count": 1,
                "dataset_usage": {
                    "h4-stack-exchange-preferences": {"sample_count": 6},
                    "tulu3-constraint-preferences": {"sample_count": 2},
                },
                "reviewer_results": {
                    "instruction_reviewer": "PASS",
                    "human_quality_reviewer": "REVISE",
                },
                "final_instruction_status": "PASS",
                "requirement_completeness": "SUFFICIENT",
                "human_signal": "HIGH",
                "llmaj_writing_finding": False,
                "holdout_eligible": True,
            }
            store.append(base)
            metrics = store.metrics()
            self.assertEqual(metrics["reviewer_disagreement_count"], 1)
            self.assertEqual(metrics["task_count"], 1)
            self.assertEqual(
                store.recommend_weights("writer")["status"], "INSUFFICIENT_DATA"
            )

    def test_native_preference_store_keeps_hashes_not_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = TerminusPreferenceStore(ROOT, Path(tmp) / "prefs.jsonl")
            rejected = "This is a verbose synthetic draft."
            chosen = "Fix the restart path without duplicating committed work."
            record = store.append(
                task_id="t1",
                task_commit="1" * 40,
                rejected_text=rejected,
                chosen_text=chosen,
                label_source="human_review",
                reason_codes=["natural_grouping", "requirements_preserved"],
                calibration_pair_id="pair",
                holdout_eligible=True,
            )
            rendered = json.dumps(record)
            self.assertNotIn(rejected, rendered)
            self.assertNotIn(chosen, rendered)
            self.assertEqual(store.summary()["preference_count"], 1)

    def test_adapter_training_is_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            store = HumanWritingLearningStore(ROOT, Path(tmp) / "outcomes.jsonl")
            readiness = store.adapter_readiness()
            self.assertEqual(readiness["status"], "NOT_READY")
            self.assertFalse(readiness["enabled"])


if __name__ == "__main__":
    unittest.main()
